from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.update_parent_client_pin import PinError, update_pin


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

    def test_remote_runtime_dependency_is_rejected(self) -> None:
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
        with tempfile.TemporaryDirectory() as temporary:
            greia, parent, revision = self._fixture(Path(temporary))
            (parent / "index.html").write_text("dirty\n", encoding="utf-8")
            with self.assertRaisesRegex(PinError, "dirty"):
                update_pin(greia, parent, revision)

    def test_revision_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            greia, parent, _ = self._fixture(Path(temporary))
            with self.assertRaisesRegex(PinError, "expected"):
                update_pin(greia, parent, "f" * 40)


if __name__ == "__main__":
    unittest.main()
