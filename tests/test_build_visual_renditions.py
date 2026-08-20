from __future__ import annotations

import importlib.util
import stat
import struct
import sys
import tempfile
import unittest
from pathlib import Path

TOOL_PATH = (
    Path(__file__).resolve().parents[1] / "tools" / "build_visual_renditions.py"
)
spec = importlib.util.spec_from_file_location("build_visual_renditions", TOOL_PATH)
assert spec is not None and spec.loader is not None
builder = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = builder
spec.loader.exec_module(builder)


class VisualRenditionBuilderTests(unittest.TestCase):
    def make_spec(
        self,
    ) -> tuple[
        tempfile.TemporaryDirectory[str],
        Path,
        Path,
        tuple[object, ...],
    ]:
        temporary = tempfile.TemporaryDirectory()
        assets = Path(temporary.name) / "assets"
        catalog = assets / "catalog"
        source_dir = assets / "visual" / "source"
        catalog.mkdir(parents=True)
        source_dir.mkdir(parents=True)
        (source_dir / "panel.svg").write_text("<svg/>", encoding="utf-8")
        source_spec = catalog / "source.toml"
        source_spec.write_text(
            """
catalog_id = "greia.test"
catalog_version = "1"

[[visuals]]
id = "ui.panel"
kind = "ui"
role = "panel"

[[visuals.variants]]
name = "default"
source = "visual/source/panel.svg"
output = "visual/runtime/panel.png"
width = 64
height = 32
""".lstrip(),
            encoding="utf-8",
        )
        metadata, visuals = builder.load_source_spec(source_spec, assets)
        self.assertEqual(metadata["catalog_id"], "greia.test")
        return temporary, assets, source_spec, visuals

    def make_rasterizer(self, root: Path, *, fail: bool = False) -> Path:
        script = root / "fake-rsvg"
        script.write_text(
            f'''#!/usr/bin/env python3
import struct
import sys
if {fail!r}:
    raise SystemExit(7)
args = sys.argv[1:]
width = int(args[args.index("--width") + 1])
height = int(args[args.index("--height") + 1])
output = args[args.index("--output") + 1]
data = (
    b"\\x89PNG\\r\\n\\x1a\\n"
    + struct.pack(">I", 13)
    + b"IHDR"
    + struct.pack(">II", width, height)
    + b"\\x08\\x06\\x00\\x00\\x00"
)
open(output, "wb").write(data)
''',
            encoding="utf-8",
        )
        script.chmod(script.stat().st_mode | stat.S_IXUSR)
        return script

    def test_render_all_uses_verified_atomic_output(self) -> None:
        temporary, assets, _source_spec, visuals = self.make_spec()
        self.addCleanup(temporary.cleanup)
        rasterizer = self.make_rasterizer(Path(temporary.name))

        builder.render_all(visuals, rasterizer)

        output = assets / "visual" / "runtime" / "panel.png"
        self.assertTrue(output.is_file())
        data = output.read_bytes()
        self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(struct.unpack(">II", data[16:24]), (64, 32))
        self.assertFalse(any(output.parent.glob(".*.tmp-*")))

    def test_failed_rasterizer_preserves_previous_output(self) -> None:
        temporary, assets, _source_spec, visuals = self.make_spec()
        self.addCleanup(temporary.cleanup)
        output = assets / "visual" / "runtime" / "panel.png"
        output.parent.mkdir(parents=True)
        output.write_bytes(b"previous-good-output")
        rasterizer = self.make_rasterizer(Path(temporary.name), fail=True)

        with self.assertRaisesRegex(builder.VisualRenditionError, "rasterizer failed"):
            builder.render_all(visuals, rasterizer)

        self.assertEqual(output.read_bytes(), b"previous-good-output")
        self.assertFalse(any(output.parent.glob(".*.tmp-*")))

    def test_runtime_catalog_is_atomic_and_contains_source_digest(self) -> None:
        temporary, assets, source_spec, visuals = self.make_spec()
        self.addCleanup(temporary.cleanup)
        metadata, _ = builder.load_source_spec(source_spec, assets)
        output = assets / "catalog" / "runtime.toml"

        builder.write_runtime_catalog(output, source_spec, metadata, visuals)

        text = output.read_text(encoding="utf-8")
        self.assertIn('catalog_id = "greia.test"', text)
        self.assertIn('default = "visual/runtime/panel.png"', text)
        self.assertIn("source_sha256 = ", text)
        self.assertFalse(any(output.parent.glob(".*.tmp-*")))


if __name__ == "__main__":
    unittest.main()
