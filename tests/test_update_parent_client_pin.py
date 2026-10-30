from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.update_parent_client_pin import (
    PIN_REPOSITORY,
    PinError,
    _commit_replacements,
    check_pin,
    update_pin,
)

HAS_GIT = shutil.which("git") is not None
NEEDS_GIT = "device-deferred: git not installed on this host; needs recorded authority amendment per T01-FIX-ENV"


class ParentClientPinUpdateTests(unittest.TestCase):
    """The pin names the committed ``parent-app/`` tree and owns manifest + overlay."""

    def _git(self, root: Path, *args: str) -> str:
        completed = subprocess.run(
            ["git", "-C", str(root), *args],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return completed.stdout.strip()

    def _greia_checkout(self, root: Path) -> Path:
        """A temporary Greia git repo with committed parent-app/ and a stale pin."""

        greia = root / "greia"
        app = greia / "parent-app"
        (app / "src").mkdir(parents=True)
        (app / "styles").mkdir()
        (app / "assets").mkdir()
        (app / "tests").mkdir()
        (app / "index.html").write_text(
            "<link rel=\"stylesheet\" href=\"./styles/app.css\">"
            "<script type=\"module\" src=\"./src/app.js\"></script>",
            encoding="utf-8",
        )
        (app / "src" / "app.js").write_text('import "./extra.js";\n', encoding="utf-8")
        (app / "src" / "extra.js").write_text("export const value = 1;\n", encoding="utf-8")
        (app / "styles" / "app.css").write_text(
            'body { background-image: url("../assets/icon.svg"); }\n',
            encoding="utf-8",
        )
        (app / "assets" / "icon.svg").write_text("<svg></svg>\n", encoding="utf-8")
        (app / "assets" / "unused.png").write_bytes(b"\x89PNG not referenced")
        (app / "tests" / "app.test.js").write_text("// not runtime\n", encoding="utf-8")
        (app / "README.md").write_text("not runtime\n", encoding="utf-8")

        (greia / "runtime").mkdir()
        overlay = greia / "build" / "overlay" / "usr" / "share" / "greia-parent-app"
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
        (overlay / "stale.js").write_text("stale overlay\n", encoding="utf-8")

        self._git(greia, "init", "-q")
        self._git(greia, "config", "user.email", "tests@greia.invalid")
        self._git(greia, "config", "user.name", "Greia Tests")
        self._git(greia, "add", ".")
        self._git(greia, "commit", "-q", "-m", "fixture")
        return greia

    def _commit_all(self, greia: Path, message: str = "change") -> None:
        self._git(greia, "add", ".")
        self._git(greia, "commit", "-q", "-m", message)

    @staticmethod
    def _file_map(root: Path) -> dict[str, bytes]:
        return {
            path.relative_to(root).as_posix(): path.read_bytes()
            for path in sorted(root.rglob("*"))
            if path.is_file()
        }

    def test_repin_names_committed_tree_and_updates_contract_and_overlay(self) -> None:
        if not HAS_GIT:
            self.skipTest(NEEDS_GIT)
        with tempfile.TemporaryDirectory() as temporary:
            greia = self._greia_checkout(Path(temporary))
            tree = self._git(greia, "rev-parse", "HEAD:parent-app")

            config, manifest_path, overlay = update_pin(greia)

            text = config.read_text(encoding="utf-8")
            self.assertIn(f'revision = "{tree}"', text)
            self.assertIn(f'repository = "{PIN_REPOSITORY}"', text)
            self.assertIn('runtime_root = "/usr/share/greia-parent-app"', text)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["revision"], tree)
            self.assertEqual(manifest["repository"], PIN_REPOSITORY)
            self.assertEqual(
                set(manifest["files"]),
                {"assets/icon.svg", "index.html", "src/app.js", "src/extra.js", "styles/app.css"},
            )

            overlay_files = self._file_map(overlay)
            self.assertEqual(set(overlay_files), set(manifest["files"]))
            self.assertNotIn("stale.js", overlay_files)
            for relative, data in overlay_files.items():
                record = manifest["files"][relative]
                self.assertEqual(record["bytes"], len(data))
                self.assertEqual(record["sha256"], hashlib.sha256(data).hexdigest())
                self.assertEqual(data, (greia / "parent-app" / relative).read_bytes())

            self.assertEqual(check_pin(greia), [])

    def test_runtime_bytes_come_from_head_not_the_working_tree(self) -> None:
        if not HAS_GIT:
            self.skipTest(NEEDS_GIT)
        with tempfile.TemporaryDirectory() as temporary:
            greia = self._greia_checkout(Path(temporary))
            committed = (greia / "parent-app" / "src" / "extra.js").read_bytes()
            # A dirty tracked file is refused outright, so the only way to
            # observe the difference is to assume-unchanged it past git status.
            self._git(greia, "update-index", "--assume-unchanged", "parent-app/src/extra.js")
            (greia / "parent-app" / "src" / "extra.js").write_text("tampered\n", encoding="utf-8")

            _config, _manifest, overlay = update_pin(greia)

            self.assertEqual((overlay / "src" / "extra.js").read_bytes(), committed)

    def test_uncommitted_or_untracked_parent_app_changes_refuse_before_mutating(self) -> None:
        if not HAS_GIT:
            self.skipTest(NEEDS_GIT)
        for mutate in (
            lambda app: (app / "untracked.txt").write_text("dirty\n", encoding="utf-8"),
            lambda app: (app / "src" / "extra.js").write_text("dirty\n", encoding="utf-8"),
            lambda app: (app / "tests" / "app.test.js").write_text("dirty\n", encoding="utf-8"),
        ):
            with self.subTest(mutate=mutate), tempfile.TemporaryDirectory() as temporary:
                greia = self._greia_checkout(Path(temporary))
                mutate(greia / "parent-app")
                before = {
                    **self._file_map(greia / "runtime"),
                    **self._file_map(greia / "build"),
                }

                with self.assertRaisesRegex(PinError, "uncommitted or untracked"):
                    update_pin(greia)
                with self.assertRaisesRegex(PinError, "uncommitted or untracked"):
                    check_pin(greia)

                after = {
                    **self._file_map(greia / "runtime"),
                    **self._file_map(greia / "build"),
                }
                self.assertEqual(after, before)

    def test_changes_outside_parent_app_do_not_block_the_pin(self) -> None:
        if not HAS_GIT:
            self.skipTest(NEEDS_GIT)
        with tempfile.TemporaryDirectory() as temporary:
            greia = self._greia_checkout(Path(temporary))
            (greia / "unrelated.txt").write_text("other work\n", encoding="utf-8")
            update_pin(greia)

    def test_revision_follows_any_committed_parent_app_change(self) -> None:
        if not HAS_GIT:
            self.skipTest(NEEDS_GIT)
        with tempfile.TemporaryDirectory() as temporary:
            greia = self._greia_checkout(Path(temporary))
            update_pin(greia)
            self._commit_all(greia, "repin")
            self.assertEqual(check_pin(greia), [])

            (greia / "parent-app" / "tests" / "app.test.js").write_text("// edited\n", encoding="utf-8")
            self._commit_all(greia, "edit tests only")
            problems = check_pin(greia)
            self.assertTrue(any("parent-app-client.toml" in item for item in problems), problems)

            update_pin(greia)
            self.assertEqual(check_pin(greia), [])

    def test_check_reports_overlay_drift_without_writing(self) -> None:
        if not HAS_GIT:
            self.skipTest(NEEDS_GIT)
        with tempfile.TemporaryDirectory() as temporary:
            greia = self._greia_checkout(Path(temporary))
            _config, _manifest, overlay = update_pin(greia)
            (overlay / "src" / "app.js").write_text("tampered\n", encoding="utf-8")
            (overlay / "extra.js").write_text("extra\n", encoding="utf-8")
            (overlay / "assets" / "icon.svg").unlink()

            problems = check_pin(greia)

            self.assertIn("overlay differs from committed parent-app/src/app.js", problems)
            self.assertIn("overlay has unexpected file extra.js", problems)
            self.assertIn("overlay is missing assets/icon.svg", problems)
            self.assertEqual((overlay / "src" / "app.js").read_text(encoding="utf-8"), "tampered\n")

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
