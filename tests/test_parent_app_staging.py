from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
import unittest
from pathlib import Path

from tools.stage_parent_app import (
    ParentAppManifest,
    ParentAppPin,
    ParentAppStageError,
    ParentAppStager,
)


class ParentAppStagingTests(unittest.TestCase):
    def _fixture(self, root: Path) -> tuple[Path, Path, Path]:
        source = root / "client"
        (source / "src").mkdir(parents=True)
        (source / "styles").mkdir()
        (source / "index.html").write_text("<html>Greia</html>", encoding="utf-8")
        (source / "src" / "app.js").write_text("export const x = 1;", encoding="utf-8")
        (source / "styles" / "app.css").write_text("body{}", encoding="utf-8")

        revision = "a" * 40
        pin_path = root / "pin.toml"
        pin_path.write_text(
            "\n".join(
                [
                    "schema_version = 1",
                    "api_version = 1",
                    'repository = "frozenpepper/Greia-Parent-App-Html"',
                    f'revision = "{revision}"',
                    'runtime_root = "/usr/share/greia-parent-app"',
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        files: dict[str, dict[str, object]] = {}
        for relative in ("index.html", "src/app.js", "styles/app.css"):
            payload = (source / relative).read_bytes()
            files[relative] = {
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        manifest_path = root / "manifest.json"
        manifest_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "repository": "frozenpepper/Greia-Parent-App-Html",
                    "revision": revision,
                    "files": files,
                }
            ),
            encoding="utf-8",
        )
        return source, pin_path, manifest_path

    def test_exact_pinned_runtime_files_stage_without_repository_docs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, pin_path, manifest_path = self._fixture(root)
            (source / "README.md").write_text("not runtime", encoding="utf-8")
            pin = ParentAppPin.load(pin_path)
            manifest = ParentAppManifest.load(manifest_path, pin)
            target = root / "rootfs" / "usr" / "share" / "greia-parent-app"

            ParentAppStager(pin, manifest).stage(source, target)

            self.assertEqual((target / "src" / "app.js").read_text(), "export const x = 1;")
            self.assertFalse((target / "README.md").exists())

    def test_stage_is_traversable_under_restrictive_umask(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, pin_path, manifest_path = self._fixture(root)
            pin = ParentAppPin.load(pin_path)
            target = root / "target"
            previous = os.umask(0o077)
            try:
                ParentAppStager(pin, ParentAppManifest.load(manifest_path, pin)).stage(source, target)
            finally:
                os.umask(previous)
            for directory in (target, *(p for p in target.rglob("*") if p.is_dir())):
                self.assertEqual(stat.S_IMODE(directory.stat().st_mode), 0o755)
            self.assertEqual(stat.S_IMODE((target / "src/app.js").stat().st_mode), 0o644)

    def test_modified_runtime_asset_fails_before_target_creation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, pin_path, manifest_path = self._fixture(root)
            pin = ParentAppPin.load(pin_path)
            manifest = ParentAppManifest.load(manifest_path, pin)
            target = root / "target"
            (source / "src" / "app.js").write_text("tampered", encoding="utf-8")

            with self.assertRaisesRegex(ParentAppStageError, "mismatch"):
                ParentAppStager(pin, manifest).stage(source, target)
            self.assertFalse(target.exists())

    def test_manifest_revision_must_match_pin(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _source, pin_path, manifest_path = self._fixture(root)
            document = json.loads(manifest_path.read_text(encoding="utf-8"))
            document["revision"] = "b" * 40
            manifest_path.write_text(json.dumps(document), encoding="utf-8")
            pin = ParentAppPin.load(pin_path)

            with self.assertRaisesRegex(ParentAppStageError, "revision pin"):
                ParentAppManifest.load(manifest_path, pin)

    def test_unsafe_manifest_path_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _source, pin_path, manifest_path = self._fixture(root)
            document = json.loads(manifest_path.read_text(encoding="utf-8"))
            document["files"]["../escape.js"] = {
                "bytes": 0,
                "sha256": hashlib.sha256(b"").hexdigest(),
            }
            manifest_path.write_text(json.dumps(document), encoding="utf-8")
            pin = ParentAppPin.load(pin_path)

            with self.assertRaisesRegex(ParentAppStageError, "unsafe"):
                ParentAppManifest.load(manifest_path, pin)


if __name__ == "__main__":
    unittest.main()
