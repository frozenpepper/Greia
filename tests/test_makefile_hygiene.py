from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "greia_clean_bytecode_test_module",
    PROJECT_ROOT / "tools" / "clean_bytecode.py",
)
assert SPEC is not None and SPEC.loader is not None
clean_bytecode = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(clean_bytecode)


class MakefileHygieneTests(unittest.TestCase):
    def test_makefile_delegates_bytecode_cleanup_without_shell_traversal(self) -> None:
        makefile = (PROJECT_ROOT / "Makefile").read_text(encoding="utf-8")
        self.assertEqual(
            clean_bytecode.SOURCE_ROOTS,
            ("src", "tests", "tools", "activities"),
        )

        start = makefile.index("clean-bytecode:")
        end = makefile.index("\ntest:", start)
        clean_block = makefile[start:end]

        self.assertEqual(
            clean_block.strip(),
            "clean-bytecode:\n\t$(PYTHON) tools/clean_bytecode.py",
        )

    def test_clean_bytecode_helper_stays_inside_source_owned_trees(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            source_cache = root / "src" / "pkg" / "__pycache__"
            source_cache.mkdir(parents=True)
            (source_cache / "module.cpython-312.pyc").write_bytes(b"bytecode")

            tools_root = root / "tools"
            tools_root.mkdir()
            loose_bytecode = tools_root / "loose.pyc"
            loose_bytecode.write_bytes(b"bytecode")

            root_cache = root / "__pycache__"
            root_cache.mkdir()
            (root_cache / "root.cpython-312.pyc").write_bytes(b"bytecode")

            ignored_cache = root / "tmp" / "preserved" / "__pycache__"
            ignored_cache.mkdir(parents=True)
            ignored_bytecode = ignored_cache / "evidence.cpython-312.pyc"
            ignored_bytecode.write_bytes(b"preserved")

            removed = clean_bytecode.clean_repository_bytecode(root)

            self.assertGreaterEqual(removed, 3)
            self.assertFalse(source_cache.exists())
            self.assertFalse(loose_bytecode.exists())
            self.assertFalse(root_cache.exists())
            self.assertTrue(ignored_bytecode.is_file())
            self.assertEqual(ignored_bytecode.read_bytes(), b"preserved")

    def test_clean_bytecode_helper_fails_closed_on_walk_errors(self) -> None:
        error = PermissionError("simulated walk denial")
        with self.assertRaises(PermissionError):
            clean_bytecode._raise_walk_error(error)

    def test_clean_bytecode_helper_propagates_deletion_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_cache = root / "src" / "pkg" / "__pycache__"
            source_cache.mkdir(parents=True)
            (source_cache / "module.pyc").write_bytes(b"bytecode")

            with mock.patch.object(
                clean_bytecode.shutil,
                "rmtree",
                side_effect=PermissionError("simulated cleanup denial"),
            ):
                with self.assertRaises(PermissionError):
                    clean_bytecode.clean_repository_bytecode(root)

    def test_source_footprint_ignores_ignored_build_evidence_in_git_checkouts(self) -> None:
        script = (PROJECT_ROOT / "build/footprint-source.sh").read_text(encoding="utf-8")
        self.assertIn('git -C "$root" rev-parse --is-inside-work-tree', script)
        self.assertIn('["git", "-C", str(root), "ls-files", "-z"]', script)
        self.assertIn("tracked source files", script)
        self.assertNotIn('echo "Source archive-relevant footprint:"\ndu -sh "$root"', script)


if __name__ == "__main__":
    unittest.main()
