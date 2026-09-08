from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.update_parent_client_pin import PinError, _commit_replacements, update_pin


class ParentClientPinUpdateTests(unittest.TestCase):
    def _git(self, root: Path, *args: str) -> str:
        completed = subprocess.run(
            ["git", "-C", str(root), *args],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return completed.stdout.strip()

    def _parent_checkout(self, root: Path) -> tuple[Path, str]:
        parent = root / "parent"
        (parent / "src").mkdir(parents=True)
        (parent / "styles").mkdir()
        (parent / "assets").mkdir()
        (parent / "index.html").write_text(
            "<link rel=\"stylesheet\" href=\"./styles/app.css\">"
            "<script type=\"module\" src=\"./src/app.js\"></script>",
            encoding="utf-8",
        )
        (parent / "src" / "app.js").write_text('import "./extra.js";\n', encoding="utf-8")
        (parent / "src" / "extra.js").write_text("export const value = 1;\n", encoding="utf-8")
        (parent / "styles" / "app.css").write_text(
            'body { background-image: url("../assets/icon.svg"); }\n',
            encoding="utf-8",
        )
        (parent / "assets" / "icon.svg").write_text("<svg></svg>\n", encoding="utf-8")
        (parent / "README.md").write_text("not runtime\n", encoding="utf-8")

        self._git(parent, "init", "-q")
        self._git(parent, "config", "user.email", "tests@greia.invalid")
        self._git(parent, "config", "user.name", "Greia Tests")
        self._git(parent, "add", ".")
        self._git(parent, "commit", "-q", "-m", "fixture")
        return parent, self._git(parent, "rev-parse", "HEAD")

    def _greia_checkout(self, root: Path) -> Path:
        greia = root / "greia"
        (greia / "runtime").mkdir(parents=True)
        vendor = greia / "vendor" / "parent-app"
        overlay = greia / "build" / "overlay" / "usr" / "share" / "greia-parent-app"
        vendor.mkdir(parents=True)
        overlay.mkdir(parents=True)

        old_revision = "0" * 40
        (greia / "runtime" / "parent-app-client.toml").write_text(
            "\n".join(
                [
                    "schema_version = 1",
                    "api_version = 1",
                    'repository = "frozenpepper/Greia-Parent-App-Html"',
                    f'revision = "{old_revision}"',
                    'runtime_root = "/usr/share/greia-parent-app"',
                    'integration_state = "vendored-image-integrity-enforced"',
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        (greia / "runtime" / "parent-app-client.manifest.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "repository": "frozenpepper/Greia-Parent-App-Html",
                    "revision": old_revision,
                    "files": {"index.html": {"bytes": 3, "sha256": hashlib.sha256(b"old").hexdigest()}},
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (vendor / "stale.js").write_text("stale vendor\n", encoding="utf-8")
        (overlay / "stale.js").write_text("stale overlay\n", encoding="utf-8")
        return greia

    @staticmethod
    def _file_map(root: Path) -> dict[str, bytes]:
        return {
            path.relative_to(root).as_posix(): path.read_bytes()
            for path in sorted(root.rglob("*"))
            if path.is_file()
        }

    def test_repin_updates_contract_vendor_and_image_overlay_from_same_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            parent, revision = self._parent_checkout(root)
            greia = self._greia_checkout(root)

            config, manifest_path, vendor, overlay = update_pin(greia, parent, revision)

            self.assertIn(f'revision = "{revision}"', config.read_text(encoding="utf-8"))
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["revision"], revision)
            self.assertEqual(
                set(manifest["files"]),
                {"assets/icon.svg", "index.html", "src/app.js", "src/extra.js", "styles/app.css"},
            )

            vendor_files = self._file_map(vendor)
            overlay_files = self._file_map(overlay)
            self.assertEqual(vendor_files, overlay_files)
            self.assertNotIn("stale.js", vendor_files)
            self.assertNotIn("README.md", vendor_files)
            self.assertEqual(set(vendor_files), set(manifest["files"]))

            for relative, data in vendor_files.items():
                record = manifest["files"][relative]
                self.assertEqual(record["bytes"], len(data))
                self.assertEqual(record["sha256"], hashlib.sha256(data).hexdigest())
                self.assertEqual(data, (parent / relative).read_bytes())

    def test_dirty_parent_checkout_refuses_before_mutating_greia(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            parent, revision = self._parent_checkout(root)
            greia = self._greia_checkout(root)
            before = self._file_map(greia)
            (parent / "untracked.txt").write_text("dirty\n", encoding="utf-8")

            with self.assertRaisesRegex(PinError, "dirty"):
                update_pin(greia, parent, revision)

            self.assertEqual(self._file_map(greia), before)

    def test_failed_multi_path_swap_restores_previous_targets(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = root / "first.txt"
            second = root / "second.txt"
            first.write_text("old first", encoding="utf-8")
            second.write_text("old second", encoding="utf-8")
            first_staged = root / "first.new"
            first_staged.write_text("new first", encoding="utf-8")
            missing_second_staged = root / "missing-second.new"

            with self.assertRaisesRegex(PinError, "could not synchronize"):
                _commit_replacements(
                    [
                        (first, first_staged),
                        (second, missing_second_staged),
                    ]
                )

            self.assertEqual(first.read_text(encoding="utf-8"), "old first")
            self.assertEqual(second.read_text(encoding="utf-8"), "old second")
            self.assertFalse(any("backup-" in path.name for path in root.iterdir()))


if __name__ == "__main__":
    unittest.main()
