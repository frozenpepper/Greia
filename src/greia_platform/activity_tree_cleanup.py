"""Boot-time cleanup of regenerable development-noise files from Activity trees.

Greia Activities are curated, validated packages. Their validator rejects
executable/sidecar files such as macOS AppleDouble metadata (``._*``), package
caches and editor droppings. During development these regenerate whenever a
host copies or touches the tree, and a single stray file can make an otherwise
healthy Activity fail registration.

This module removes only well-known, fully regenerable development noise before
Activities are loaded, so a dirty-but-healthy tree becomes valid again. It is
**not** an Activity repair mechanism:

* a genuinely broken or missing Activity file is deliberately left untouched and
  is simply not loaded (see the fail-soft progression boundary in ``history``);
* only the curated dev-noise patterns below are ever deleted.

The scrub operates strictly inside the configured Activity root: it never follows
symlinks out of the tree and never touches paths outside it.
"""

from __future__ import annotations

import logging
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

# Curated dev-environment noise that is safe to delete. This is an explicit,
# versioned list; adding a pattern is a review decision, not a habit. Exact
# names are matched case-insensitively to mirror the Activity validator.
_JUNK_EXACT: frozenset[str] = frozenset({".ds_store", "thumbs.db", "desktop.ini"})
_JUNK_SUFFIX: tuple[str, ...] = ("~", ".swp", ".swx", ".tmp", ".pyc")
_JUNK_DIR: frozenset[str] = frozenset({"__macosx"})


@dataclass(frozen=True, slots=True)
class ScrubResult:
    """Summary of what a single Activity-tree scrub removed."""

    removed_files: int
    removed_dirs: int
    roots_scrubbed: int


def _is_junk_name(name: str) -> bool:
    lowered = name.casefold()
    if lowered in _JUNK_EXACT:
        return True
    if name.startswith("._"):
        return True  # AppleDouble resource-fork sidecar
    if name.startswith("~$"):
        return True  # office/editor lock file
    if name.startswith(".nfs"):
        return True  # NFS leftover
    if lowered in _JUNK_DIR:
        return True
    if name.endswith("~"):
        return True
    return any(lowered.endswith(suffix) for suffix in _JUNK_SUFFIX)


def _is_bytecode_dir(name: str) -> bool:
    return name == "__pycache__"


def _under(root: Path, candidate: Path) -> bool:
    try:
        candidate.resolve().relative_to(root)
        return True
    except ValueError:
        return False


def scrub_activity_tree(root: Path) -> ScrubResult:
    """Remove development-noise files/dirs under ``root`` in place.

    ``root`` is resolved defensively: only paths whose resolved-parent chain stays
    under ``root`` are touched, and directory symlinks are never descended into,
    so the scrub cannot escape its root or follow a symlinked Activity dir out.
    Returns a count of what was removed and never raises for a missing root.
    """

    if not root.is_dir():
        logger.warning("Activity tree scrub: root not present, skipping: %s", root)
        return ScrubResult(0, 0, 0)

    root = root.resolve()
    removed_files = 0
    removed_dirs = 0
    roots_scrubbed = 0
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirpath = Path(dirpath)
        keep_dirs = []
        for name in dirnames:
            target = dirpath / name
            if name == "__pycache__" and _under(root, target):
                _remove_dir_tree(target)
                removed_dirs += 1
                continue
            if _is_junk_name(name):
                if target.is_symlink() or _under(root, target):
                    _remove_path(target)
                    removed_dirs += 1
                    continue
            if not target.is_symlink():
                keep_dirs.append(name)
        dirnames[:] = keep_dirs
        for name in filenames:
            target = dirpath / name
            if _is_junk_name(name) and _under(root, target):
                _remove_path(target)
                removed_files += 1
        roots_scrubbed += 1

    if removed_files or removed_dirs:
        logger.info(
            "Activity tree scrub removed %d file(s), %d dir(s) under %s",
            removed_files,
            removed_dirs,
            root,
        )
    return ScrubResult(removed_files, removed_dirs, roots_scrubbed)


def _remove_path(path: Path) -> None:
    try:
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        else:
            path.unlink()
    except OSError:
        logger.warning("Activity tree scrub: could not remove %s", path)


def _remove_dir_tree(path: Path) -> None:
    _remove_path(path)