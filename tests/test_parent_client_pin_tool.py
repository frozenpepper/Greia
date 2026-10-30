from __future__ import annotations

import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.update_parent_client_pin import PinError, update_pin

HAS_GIT = shutil.which("git") is not None
NEEDS_GIT = "device-deferred: git not installed on this host; needs recorded authority amendment per T01-FIX-ENV"


class ParentClientPinToolSafetyTests(unittest.TestCase):
    """Safety properties of the repin tool beyond the happy-path transaction."""

    def _git(self, root: Path, *args: str) -> None:
        subprocess.run(["git", "-C", str(root), *args], check=True, stdout=subprocess.PIPE)

    def _fixture(self, root: Path) -> Path:
        greia = root / "greia"
        parent = greia / "parent-app"
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
            'schema_version = 1\nrepository = "old"\nrevision = "' + "0" * 40 + '"\n',
            encoding="utf-8",
        )
        (greia / "runtime" / "parent-app-client.manifest.json").write_text(
            '{"files": {"index.html": {"bytes": 0, "sha256": "old"}},'
            ' "repository": "old", "revision": "' + "0" * 40 + '", "schema_version": 1}',
            encoding="utf-8",
        )
        self._git(root, "init", "-q", str(greia))
        self._git(greia, "config", "user.email", "test@example.invalid")
        self._git(greia, "config", "user.name", "Greia Test")
        self._commit(greia, "fixture")
        return greia

    def _commit(self, greia: Path, message: str) -> None:
        self._git(greia, "add", ".")
        self._git(greia, "commit", "-q", "-m", message)

    def test_pinned_overlay_remains_readable_under_restrictive_umask(self) -> None:
        if not HAS_GIT:
            self.skipTest(NEEDS_GIT)
        with tempfile.TemporaryDirectory() as temporary:
            greia = self._fixture(Path(temporary))
            previous = os.umask(0o077)
            try:
                update_pin(greia)
            finally:
                os.umask(previous)
            root = greia / "build/overlay/usr/share/greia-parent-app"
            for directory in (root, *(p for p in root.rglob("*") if p.is_dir())):
                self.assertEqual(stat.S_IMODE(directory.stat().st_mode), 0o755)
            for file in (p for p in root.rglob("*") if p.is_file()):
                self.assertEqual(stat.S_IMODE(file.stat().st_mode), 0o644)

    def test_remote_runtime_dependency_is_rejected(self) -> None:
        if not HAS_GIT:
            self.skipTest(NEEDS_GIT)
        with tempfile.TemporaryDirectory() as temporary:
            greia = self._fixture(Path(temporary))
            (greia / "parent-app" / "src" / "app.js").write_text(
                'import "https://example.invalid/remote.js";\n', encoding="utf-8"
            )
            self._commit(greia, "remote")
            with self.assertRaisesRegex(PinError, "remote Parent runtime dependency"):
                update_pin(greia)

    def test_root_relative_and_escaping_references_are_rejected(self) -> None:
        if not HAS_GIT:
            self.skipTest(NEEDS_GIT)
        for source in ('import "/etc/passwd";\n', 'import "../../outside.js";\n'):
            with self.subTest(source=source), tempfile.TemporaryDirectory() as temporary:
                greia = self._fixture(Path(temporary))
                (greia / "parent-app" / "src" / "app.js").write_text(source, encoding="utf-8")
                self._commit(greia, "bad reference")
                with self.assertRaisesRegex(PinError, "package-relative|escapes"):
                    update_pin(greia)

    def test_missing_referenced_file_is_rejected(self) -> None:
        if not HAS_GIT:
            self.skipTest(NEEDS_GIT)
        with tempfile.TemporaryDirectory() as temporary:
            greia = self._fixture(Path(temporary))
            (greia / "parent-app" / "src" / "feature.js").unlink()
            self._commit(greia, "drop dependency")
            with self.assertRaisesRegex(PinError, "missing"):
                update_pin(greia)

    def test_committed_symlink_in_runtime_closure_is_rejected(self) -> None:
        if not HAS_GIT:
            self.skipTest(NEEDS_GIT)
        with tempfile.TemporaryDirectory() as temporary:
            greia = self._fixture(Path(temporary))
            feature = greia / "parent-app" / "src" / "feature.js"
            feature.unlink()
            feature.symlink_to("../../runtime/parent-app-client.toml")
            self._commit(greia, "symlink")
            with self.assertRaisesRegex(PinError, "not a regular file"):
                update_pin(greia)

    def test_repository_without_parent_app_is_refused(self) -> None:
        if not HAS_GIT:
            self.skipTest(NEEDS_GIT)
        with tempfile.TemporaryDirectory() as temporary:
            greia = self._fixture(Path(temporary))
            shutil.rmtree(greia / "parent-app")
            self._commit(greia, "remove parent-app")
            with self.assertRaisesRegex(PinError, "could not inspect"):
                update_pin(greia)


if __name__ == "__main__":
    unittest.main()
