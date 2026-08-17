from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from greia_parent.static_client import MAX_STATIC_ASSET_BYTES, ParentStaticClient


class ParentStaticClientTests(unittest.TestCase):
    def test_serves_only_bounded_parent_app_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "src").mkdir()
            (root / "styles").mkdir()
            (root / "index.html").write_text("<html>Greia</html>", encoding="utf-8")
            (root / "src" / "app.js").write_text("export {};", encoding="utf-8")
            (root / "styles" / "app.css").write_text("body{}", encoding="utf-8")
            (root / "package.json").write_text("{}", encoding="utf-8")
            client = ParentStaticClient(root)

            self.assertEqual(client.read("/").content_type, "text/html; charset=utf-8")
            self.assertEqual(client.read("/src/app.js").content_type, "text/javascript; charset=utf-8")
            self.assertEqual(client.read("/styles/app.css").content_type, "text/css; charset=utf-8")
            self.assertIsNone(client.read("/package.json"))
            self.assertIsNone(client.read("/docs/ARCHITECTURE.md"))

    def test_rejects_traversal_hidden_files_symlinks_and_oversized_assets(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            outside = root.parent / f"{root.name}-outside.js"
            outside.write_text("secret", encoding="utf-8")
            try:
                (root / "src").mkdir()
                (root / "real").mkdir()
                (root / "real" / "inside.js").write_text("inside", encoding="utf-8")
                (root / "src" / ".hidden.js").write_text("hidden", encoding="utf-8")
                (root / "src" / "too-large.js").write_bytes(b"x" * (MAX_STATIC_ASSET_BYTES + 1))
                (root / "src" / "escape.js").symlink_to(outside)
                (root / "src" / "inside.js").symlink_to(root / "real" / "inside.js")
                client = ParentStaticClient(root)

                self.assertIsNone(client.read("/../etc/passwd"))
                self.assertIsNone(client.read("/src/%2e%2e/index.html"))
                self.assertIsNone(client.read("/src/.hidden.js"))
                self.assertIsNone(client.read("/src/escape.js"))
                self.assertIsNone(client.read("/src/inside.js"))
                self.assertIsNone(client.read("/src/too-large.js"))
            finally:
                outside.unlink(missing_ok=True)

    def test_rejects_symlinked_web_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            real = parent / "real"
            real.mkdir()
            (real / "index.html").write_text("<html>Greia</html>", encoding="utf-8")
            link = parent / "client"
            link.symlink_to(real, target_is_directory=True)

            self.assertIsNone(ParentStaticClient(link).read("/"))

    def test_missing_web_root_is_a_clean_miss(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            missing = Path(temporary) / "not-present"
            self.assertIsNone(ParentStaticClient(missing).read("/"))


if __name__ == "__main__":
    unittest.main()
