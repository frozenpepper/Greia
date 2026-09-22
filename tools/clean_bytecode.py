#!/usr/bin/env python3
"""Remove generated Python bytecode from Greia source-owned trees.

Release/build evidence under ignored paths may be root-owned and must remain
untouched. This helper deliberately cleans only the repository's Python source
roots plus bytecode directly at the repository root. Any deletion failure is
fatal so `make verify` cannot report success after an incomplete cleanup.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOTS = ("src", "tests", "tools", "activities")
BYTECODE_SUFFIXES = {".pyc", ".pyo"}


def _raise_walk_error(error: OSError) -> None:
    raise error


def _clean_tree(root: Path) -> int:
    if not root.is_dir():
        return 0

    removed = 0
    for current, directory_names, file_names in os.walk(
        root,
        topdown=True,
        onerror=_raise_walk_error,
        followlinks=False,
    ):
        current_path = Path(current)

        cache_names = [name for name in directory_names if name == "__pycache__"]
        for name in cache_names:
            shutil.rmtree(current_path / name)
            removed += 1
        directory_names[:] = [
            name
            for name in directory_names
            if name != "__pycache__" and not (current_path / name).is_symlink()
        ]

        for name in file_names:
            path = current_path / name
            if path.suffix in BYTECODE_SUFFIXES:
                path.unlink()
                removed += 1

    return removed


def clean_repository_bytecode(project_root: Path = PROJECT_ROOT) -> int:
    root = project_root.resolve()
    removed = sum(_clean_tree(root / name) for name in SOURCE_ROOTS)

    root_cache = root / "__pycache__"
    if root_cache.exists():
        if root_cache.is_symlink():
            root_cache.unlink()
        else:
            shutil.rmtree(root_cache)
        removed += 1

    for path in root.iterdir():
        if path.is_file() and path.suffix in BYTECODE_SUFFIXES:
            path.unlink()
            removed += 1

    return removed


def main() -> int:
    removed = clean_repository_bytecode()
    print(f"Removed {removed} Python bytecode artifact(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
