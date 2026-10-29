from __future__ import annotations

import hashlib
import json
import os
import stat
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.update_parent_client_pin import PinError, update_pin

HAS_GIT = shutil.which("git") is not None
NEEDS_GIT = "device-deferred: git not installed on this host; needs recorded authority amendment per T01-FIX-ENV"


class ParentClientPinToolTests(unittest.TestCase):
    def _fixture(self, root: Path) -> tuple[Path, Path, str]:
        greia = root / "greia"
        parent = root / "parent"
        (greia / "runtime").mkdir(parents=True)
        (parent / "src").mkdir(parents=True)
        (parent / "styles").mkdir(parents=True)
        (parent / "index.html").write_text(
            '<html><head><link rel="stylesheet" href="./styles/app.css"></head>'
            '<body><script type="module" src="./src/app.js"></script></body></html>\n',
            encoding="utf-8",
        )
        (parent / "src" / "app.js").write_text(
            'import { value } from "./feature.js";\nexport const ok = value;\n',
            encoding="utf-8",
        )
        (parent / "src" / "feature.js").write_text("export const value = true;\n", encoding="utf-8")
        (parent / "styles" / "app.css").write_text("body { color: black; }\n", encoding="utf-8")
        (parent / "not-runtime.md").write_text("must not be pinned\n", encoding="utf-8")
        (greia / "runtime" / "parent-app-client.toml").write_text(
            'schema_version = 1\nrevision = "' + "0" * 40 + '"\n',
            encoding="utf-8",
        )
        # Deliberately stale old file inventory: update_pin must derive the new
        # runtime graph from index.html instead of preserving this list.
        (greia / "runtime" / "parent-app-client.manifest.json").write_text(
            json.dumps(
                {
                    "files": {"index.html": {"bytes": 0, "sha256": "old"}},
                    "repository": "frozenpepper/Greia-Parent-App-Html",
                    "revision": "0" * 40,
                    "schema_version": 1,
                }
            ),
            encoding="utf-8",
        )
        subprocess.run(["git", "init", "-q", str(parent)], check=True)
        subprocess.run(["git", "-C", str(parent), "config", "user.email", "test@example.invalid"], check=True)
        subprocess.run(["git", "-C", str(parent), "config", "user.name", "Greia Test"], check=True)
        subprocess.run(["git", "-C", str(parent), "add", "."], check=True)
        subprocess.run(["git", "-C", str(parent), "commit", "-q", "-m", "fixture"], check=True)
        revision = subprocess.check_output(
            ["git", "-C", str(parent), "rev-parse", "HEAD"], text=True
        ).strip()
        return greia, parent, revision

    def test_exact_clean_parent_checkout_discovers_runtime_graph_and_hashes(self) -> None:
        if not HAS_GIT:
            self.skipTest(NEEDS_GIT)
        with tempfile.TemporaryDirectory() as temporary:
            greia, parent, revision = self._fixture(Path(temporary))
            update_pin(greia, parent, revision)
            config = (greia / "runtime" / "parent-app-client.toml").read_text(encoding="utf-8")
            self.assertIn(f'revision = "{revision}"', config)
            manifest = json.loads(
                (greia / "runtime" / "parent-app-client.manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["revision"], revision)
            expected = {"index.html", "src/app.js", "src/feature.js", "styles/app.css"}
            self.assertEqual(set(manifest["files"]), expected)
            self.assertNotIn("not-runtime.md", manifest["files"])
            for relative in expected:
                data = (parent / relative).read_bytes()
                self.assertEqual(manifest["files"][relative]["bytes"], len(data))
                self.assertEqual(
                    manifest["files"][relative]["sha256"], hashlib.sha256(data).hexdigest()
                )

    def test_pinned_trees_remain_readable_under_restrictive_umask(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            greia, parent, revision = self._fixture(Path(temporary))
            previous = os.umask(0o077)
            try:
                update_pin(greia, parent, revision)
            finally:
                os.umask(previous)
            for root in (greia / "vendor/parent-app", greia / "build/overlay/usr/share/greia-parent-app"):
                for directory in (root, *(p for p in root.rglob("*") if p.is_dir())):
                    self.assertEqual(stat.S_IMODE(directory.stat().st_mode), 0o755)
                for file in (p for p in root.rglob("*") if p.is_file()):
                    self.assertEqual(stat.S_IMODE(file.stat().st_mode), 0o644)

    def test_remote_runtime_dependency_is_rejected(self) -> None:
        if not HAS_GIT:
            self.skipTest(NEEDS_GIT)
        with tempfile.TemporaryDirectory() as temporary:
            greia, parent, _ = self._fixture(Path(temporary))
            (parent / "src" / "app.js").write_text(
                'import "https://example.invalid/remote.js";\n', encoding="utf-8"
            )
            subprocess.run(["git", "-C", str(parent), "add", "."], check=True)
            subprocess.run(["git", "-C", str(parent), "commit", "-q", "-m", "remote"], check=True)
            revision = subprocess.check_output(
                ["git", "-C", str(parent), "rev-parse", "HEAD"], text=True
            ).strip()
            with self.assertRaisesRegex(PinError, "remote Parent runtime dependency"):
                update_pin(greia, parent, revision)

    def test_dirty_parent_checkout_is_rejected(self) -> None:
        if not HAS_GIT:
            self.skipTest(NEEDS_GIT)
        with tempfile.TemporaryDirectory() as temporary:
            greia, parent, revision = self._fixture(Path(temporary))
            (parent / "index.html").write_text("dirty\n", encoding="utf-8")
            with self.assertRaisesRegex(PinError, "dirty"):
                update_pin(greia, parent, revision)

    def test_revision_mismatch_is_rejected(self) -> None:
        if not HAS_GIT:
            self.skipTest(NEEDS_GIT)
        with tempfile.TemporaryDirectory() as temporary:
            greia, parent, _ = self._fixture(Path(temporary))
            with self.assertRaisesRegex(PinError, "expected"):
                update_pin(greia, parent, "f" * 40)


if __name__ == "__main__":
    unittest.main()
