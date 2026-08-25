from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from greia_platform.activity_tree_cleanup import scrub_activity_tree


class ActivityTreeCleanupTests(unittest.TestCase):
    def _tree(self, root: Path) -> None:
        (root / "activities").mkdir(parents=True)
        act = root / "activities" / "demo"
        (act / "assets").mkdir(parents=True)
        (act / "locales").mkdir(parents=True)
        (act / "assets" / "sub").mkdir(parents=True)
        (act / "main.py").write_text("print('x')\n", encoding="utf-8")
        (act / "activity.toml").write_text("x=1\n", encoding="utf-8")
        (act / "locales" / "it.json").write_text("{}", encoding="utf-8")
        # Development noise that must be removed.
        (act / "._assets").write_bytes(b"ab")
        (act / "assets" / ".DS_Store").write_bytes(b"")
        (act / "assets" / "sub" / "._sub").write_bytes(b"ab")
        (act / "Thumbs.db").write_bytes(b"")
        (act / "locales" / "it.json~").write_bytes(b"")
        (act / "main.pyc").write_bytes(b"")
        (act / "assets" / "__pycache__").mkdir()
        (act / "assets" / "__pycache__" / "main.cpython-311.pyc").write_bytes(b"")
        (act / "_junk.py").write_text("x\n", encoding="utf-8")  # not noise, keep

    def test_scrub_removes_dev_noise_and_keeps_real_files(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._tree(root)
            result = scrub_activity_tree(root / "activities")
            act = root / "activities" / "demo"
            self.assertFalse((act / "._assets").exists())
            self.assertFalse((act / "assets" / ".DS_Store").exists())
            self.assertFalse((act / "assets" / "sub" / "._sub").exists())
            self.assertFalse((act / "Thumbs.db").exists())
            self.assertFalse((act / "locales" / "it.json~").exists())
            self.assertFalse((act / "main.pyc").exists())
            self.assertFalse((act / "assets" / "__pycache__").exists())
            self.assertTrue((act / "main.py").exists())
            self.assertTrue((act / "activity.toml").exists())
            self.assertTrue((act / "locales" / "it.json").exists())
            self.assertTrue((act / "_junk.py").exists())
            self.assertGreater(result.removed_files, 0)
            self.assertGreater(result.removed_dirs, 0)

    def test_scrub_does_not_follow_symlink_out_of_root(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "activities").mkdir()
            outside = root / "outside"
            outside.mkdir()
            (outside / "keep.txt").write_text("x", encoding="utf-8")
            # A symlinked dir outside the tree must not be descended into.
            link = root / "activities" / "linked"
            link.symlink_to(outside)
            leak = outside / "._junk"
            leak.write_bytes(b"ab")
            scrub_activity_tree(root / "activities")
            self.assertTrue((outside / "keep.txt").exists())
            # The scrub does not descend into the symlink, so a junk file inside
            # the target is untouched.
            self.assertTrue(leak.exists())

    def test_scrub_missing_root_is_benign(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            result = scrub_activity_tree(root / "nope")
            self.assertEqual(result.removed_files, 0)
            self.assertEqual(result.removed_dirs, 0)

    def test_scrub_matches_case_insensitive_exact_names(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "activities"
            root.mkdir(parents=True)
            (root / ".Ds_StOrE").write_bytes(b"")
            (root / "ThUmBs.DB").write_bytes(b"")
            (root / "MAIN.PYC").write_bytes(b"")
            scrub_activity_tree(root)
            self.assertEqual(list(root.iterdir()), [])


if __name__ == "__main__":
    unittest.main()