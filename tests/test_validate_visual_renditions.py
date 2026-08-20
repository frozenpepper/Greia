from __future__ import annotations

import hashlib
import importlib.util
import struct
import sys
import tempfile
import unittest
from pathlib import Path

TOOL_PATH = (
    Path(__file__).resolve().parents[1] / "tools" / "validate_visual_renditions.py"
)
spec = importlib.util.spec_from_file_location("validate_visual_renditions", TOOL_PATH)
assert spec is not None and spec.loader is not None
validator = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = validator
spec.loader.exec_module(validator)


class VisualRenditionValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.assets = Path(self.temporary.name) / "assets"
        self.catalog = self.assets / "catalog"
        self.runtime = self.assets / "visual" / "runtime"
        self.catalog.mkdir(parents=True)
        self.runtime.mkdir(parents=True)
        self.source = self.catalog / "source.toml"
        self.source.write_text(
            """
catalog_id = "greia.test"
catalog_version = "1"

[[visuals]]
id = "ui.shadow.soft"
kind = "shadow"
role = "grounding"

[[visuals.variants]]
name = "default"
source = "visual/source/shadow.svg"
output = "visual/runtime/shadow.png"
width = 64
height = 32
""".lstrip(),
            encoding="utf-8",
        )
        self.runtime_catalog = self.catalog / "runtime.toml"
        self.write_png(self.runtime / "shadow.png", 64, 32)
        self.write_runtime_catalog()

    def write_png(self, path: Path, width: int, height: int) -> None:
        path.write_bytes(
            b"\x89PNG\r\n\x1a\n"
            + struct.pack(">I", 13)
            + b"IHDR"
            + struct.pack(">II", width, height)
            + b"\x08\x06\x00\x00\x00"
        )

    def write_runtime_catalog(
        self,
        *,
        digest: str | None = None,
        output: str = "visual/runtime/shadow.png",
        kind: str = "shadow",
        role: str = "grounding",
    ) -> None:
        source_digest = digest or hashlib.sha256(self.source.read_bytes()).hexdigest()
        self.runtime_catalog.write_text(
            f"""
catalog_id = "greia.test"
catalog_version = "1"
source_sha256 = "{source_digest}"

[[visuals]]
id = "ui.shadow.soft"
kind = "{kind}"
role = "{role}"

[visuals.variants]
default = "{output}"
""".lstrip(),
            encoding="utf-8",
        )

    def test_valid_runtime_catalogue_and_png_pass(self) -> None:
        validator.validate(self.assets, self.source, self.runtime_catalog)

    def test_stale_source_digest_fails(self) -> None:
        self.write_runtime_catalog(digest="0" * 64)
        with self.assertRaisesRegex(
            validator.VisualRenditionValidationError,
            "stale",
        ):
            validator.validate(self.assets, self.source, self.runtime_catalog)

    def test_variant_mapping_mismatch_fails(self) -> None:
        wrong = self.runtime / "other.png"
        self.write_png(wrong, 64, 32)
        self.write_runtime_catalog(output="visual/runtime/other.png")
        with self.assertRaisesRegex(
            validator.VisualRenditionValidationError,
            "variant mapping mismatch",
        ):
            validator.validate(self.assets, self.source, self.runtime_catalog)

    def test_wrong_png_dimensions_fail(self) -> None:
        self.write_png(self.runtime / "shadow.png", 32, 32)
        with self.assertRaisesRegex(
            validator.VisualRenditionValidationError,
            "dimensions mismatch",
        ):
            validator.validate(self.assets, self.source, self.runtime_catalog)

    def test_non_png_fails(self) -> None:
        (self.runtime / "shadow.png").write_bytes(b"not-png")
        with self.assertRaisesRegex(
            validator.VisualRenditionValidationError,
            "not a PNG",
        ):
            validator.validate(self.assets, self.source, self.runtime_catalog)

    def test_kind_or_role_drift_fails(self) -> None:
        self.write_runtime_catalog(kind="ui")
        with self.assertRaisesRegex(
            validator.VisualRenditionValidationError,
            "kind mismatch",
        ):
            validator.validate(self.assets, self.source, self.runtime_catalog)
        self.write_runtime_catalog(role="panel")
        with self.assertRaisesRegex(
            validator.VisualRenditionValidationError,
            "role mismatch",
        ):
            validator.validate(self.assets, self.source, self.runtime_catalog)


if __name__ == "__main__":
    unittest.main()
