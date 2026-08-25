"""Installed/runtime cleanup of regenerable development-noise from Activity trees.

Greia Activities are curated, validated packages. Host tooling can inject metadata,
cache and editor files that are not part of an Activity and may cause an otherwise
healthy package to fail validation. The installed OS removes only this explicit,
versioned noise set before launcher discovery.

This module is deliberately *not* an Activity repair mechanism:

* real Activity files are never rewritten, synthesized or restored;
* broken packages remain broken and are isolated by Activity discovery;
* cleanup is bounded to configured Activity roots and never follows directory
  symlinks outside them;
* cleanup failure itself must never become a launcher boot failure.

The canonical installed launcher runs cleanup from a privileged ``ExecStartPre``
helper so read-only/root-owned Activity roots can actually be sanitized while the
launcher process itself remains unprivileged.
"""

from __future__ import annotations

import argparse
import logging
import os
import shutil
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

_INSTALLED_OS_ROOT = Path("/opt/greia-os")
_JUNK_EXACT: frozenset[str] = frozenset({".ds_store", "thumbs.db", "desktop.ini"})
_JUNK_SUFFIX: tuple[str, ...] = ("~", ".swp", ".swx", ".tmp", ".pyc")
_JUNK_DIR: frozenset[str] = frozenset({"__macosx"})


@dataclass(frozen=True, slots=True)
class ScrubResult:
    """Summary of one or more Activity-tree cleanup attempts."""

    removed_files: int
    removed_dirs: int
    roots_scrubbed: int
    failed_removals: int = 0

    def plus(self, other: "ScrubResult") -> "ScrubResult":
        return ScrubResult(
            self.removed_files + other.removed_files,
            self.removed_dirs + other.removed_dirs,
            self.roots_scrubbed + other.roots_scrubbed,
            self.failed_removals + other.failed_removals,
        )


def installed_activity_roots(
    environ: Mapping[str, str] | None = None,
) -> tuple[Path, ...]:
    """Return the Activity roots the installed launcher may discover.

    Defaults mirror the installed launcher/developer/package-service source
    owners. Environment overrides are honored so test/developer images do not
    require a second cleanup implementation.
    """

    env = os.environ if environ is None else environ
    os_root = Path(env.get("GREIA_OS_ROOT", str(_INSTALLED_OS_ROOT)))
    built_in = os_root / "activities"
    developer = Path(
        env.get("GREIA_DEVELOPER_ACTIVITY_ROOT", "/var/lib/greia-developer/activities")
    )
    parent_override = env.get("GREIA_PARENT_ACTIVITY_ROOT")
    if parent_override:
        parent = Path(parent_override)
    else:
        parent_state = Path(
            env.get(
                "GREIA_PARENT_ACTIVITY_PACKAGE_ROOT",
                "/var/lib/greia-os/activity-packages",
            )
        )
        parent = parent_state / "active"

    result: list[Path] = []
    seen: set[str] = set()
    for root in (built_in, developer, parent):
        key = os.path.abspath(os.fspath(root))
        if key in seen:
            continue
        seen.add(key)
        result.append(root)
    return tuple(result)


def _is_unprivileged_installed_built_in(root: Path) -> bool:
    """Whether cleanup of ``root`` belongs to the privileged pre-start helper.

    Only the canonical installed `/opt/greia-os` composition delegates here.
    Source checkouts and Simulator roots may also set `GREIA_OS_ROOT`; those do
    not have the installed systemd pre-start helper and must retain in-process
    cleanup.
    """

    if os.geteuid() == 0:
        return False
    configured_os_root = Path(os.environ.get("GREIA_OS_ROOT", str(_INSTALLED_OS_ROOT)))
    try:
        if configured_os_root.resolve(strict=False) != _INSTALLED_OS_ROOT:
            return False
    except (OSError, RuntimeError, ValueError):
        return False
    return os.path.abspath(os.fspath(root)) == os.path.abspath(
        os.fspath(_INSTALLED_OS_ROOT / "activities")
    )


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
    return any(lowered.endswith(suffix) for suffix in _JUNK_SUFFIX)


def _under(root: Path, candidate: Path) -> bool:
    """Return whether ``candidate`` resolves below ``root`` without raising."""

    try:
        resolved = candidate.resolve(strict=False)
        return resolved == root or root in resolved.parents
    except (OSError, RuntimeError, ValueError):
        return False


def _remove_path(path: Path) -> bool:
    """Remove one already-approved junk path; return whether cleanup succeeded."""

    try:
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        else:
            path.unlink()
        return True
    except FileNotFoundError:
        return True
    except OSError as exc:
        logger.warning("Activity tree scrub: could not remove %s: %s", path, exc)
        return False


def scrub_activity_tree(root: Path) -> ScrubResult:
    """Remove curated development noise below ``root`` without escaping it.

    Missing roots are normal because not every installation enables every
    Activity source. A symlink used *as the root itself* is deliberately not
    followed. Walk/delete errors are logged and counted rather than propagated:
    cleanup is resilience hygiene, never a reason to stop the child shell.
    """

    if _is_unprivileged_installed_built_in(root):
        # `/opt/greia-os` is intentionally root-owned/read-only on installed
        # images. The systemd ExecStartPre helper already scrubbed this root as
        # root; do not pay for a second full tree walk that cannot be authoritative.
        return ScrubResult(0, 0, 0, 0)

    try:
        if root.is_symlink():
            logger.warning("Activity tree scrub: refusing symlink root: %s", root)
            return ScrubResult(0, 0, 0, 1)
        if not root.is_dir():
            return ScrubResult(0, 0, 0, 0)
        resolved_root = root.resolve(strict=True)
    except (OSError, RuntimeError, ValueError) as exc:
        logger.warning("Activity tree scrub: cannot inspect root %s: %s", root, exc)
        return ScrubResult(0, 0, 0, 1)

    removed_files = 0
    removed_dirs = 0
    roots_scrubbed = 0
    failures = 0

    def walk_error(exc: OSError) -> None:
        nonlocal failures
        failures += 1
        logger.warning("Activity tree scrub: cannot walk %s: %s", resolved_root, exc)

    try:
        walker = os.walk(resolved_root, followlinks=False, onerror=walk_error)
        for dirpath_text, dirnames, filenames in walker:
            dirpath = Path(dirpath_text)
            roots_scrubbed += 1
            keep_dirs: list[str] = []
            for name in dirnames:
                target = dirpath / name
                try:
                    is_symlink = target.is_symlink()
                except OSError as exc:
                    failures += 1
                    logger.warning(
                        "Activity tree scrub: cannot inspect directory %s: %s",
                        target,
                        exc,
                    )
                    continue

                is_junk_dir = name == "__pycache__" or _is_junk_name(name)
                if is_junk_dir:
                    # A junk-named symlink may be unlinked safely without
                    # resolving its destination. Non-symlinks must resolve
                    # strictly below the trusted root.
                    safe = (
                        _under(resolved_root, target.parent)
                        if is_symlink
                        else _under(resolved_root, target)
                    )
                    if safe:
                        if _remove_path(target):
                            removed_dirs += 1
                        else:
                            failures += 1
                        continue

                if not is_symlink:
                    keep_dirs.append(name)
            dirnames[:] = keep_dirs

            for name in filenames:
                if not _is_junk_name(name):
                    continue
                target = dirpath / name
                try:
                    is_symlink = target.is_symlink()
                except OSError as exc:
                    failures += 1
                    logger.warning(
                        "Activity tree scrub: cannot inspect file %s: %s",
                        target,
                        exc,
                    )
                    continue
                safe = (
                    _under(resolved_root, target.parent)
                    if is_symlink
                    else _under(resolved_root, target)
                )
                if not safe:
                    failures += 1
                    logger.warning(
                        "Activity tree scrub: refusing path outside root: %s", target
                    )
                    continue
                if _remove_path(target):
                    removed_files += 1
                else:
                    failures += 1
    except (OSError, RuntimeError, ValueError) as exc:
        # ``os.walk`` is intentionally fail-soft, but retain a final defensive
        # boundary because this function executes in the boot path.
        failures += 1
        logger.warning("Activity tree scrub aborted early for %s: %s", resolved_root, exc)

    if removed_files or removed_dirs or failures:
        logger.info(
            "Activity tree scrub %s: removed_files=%d removed_dirs=%d "
            "walked_dirs=%d failures=%d",
            resolved_root,
            removed_files,
            removed_dirs,
            roots_scrubbed,
            failures,
        )
    return ScrubResult(removed_files, removed_dirs, roots_scrubbed, failures)


def scrub_installed_activity_trees(
    environ: Mapping[str, str] | None = None,
) -> ScrubResult:
    """Best-effort sanitize every Activity source used by the installed OS."""

    total = ScrubResult(0, 0, 0, 0)
    for root in installed_activity_roots(environ):
        total = total.plus(scrub_activity_tree(root))
    return total


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Remove curated regenerable host noise from Greia Activity trees"
    )
    parser.add_argument(
        "roots",
        nargs="*",
        type=Path,
        help="Explicit roots to scrub; omitted means all installed Activity roots.",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s greia-activity-tree-cleanup: %(message)s",
    )

    try:
        if args.roots:
            result = ScrubResult(0, 0, 0, 0)
            for root in args.roots:
                result = result.plus(scrub_activity_tree(root))
        else:
            result = scrub_installed_activity_trees()
        logger.info(
            "Activity tree cleanup complete: removed_files=%d removed_dirs=%d "
            "walked_dirs=%d failures=%d",
            result.removed_files,
            result.removed_dirs,
            result.roots_scrubbed,
            result.failed_removals,
        )
    except Exception:
        # Last-resort installed-boot boundary: malformed/unexpected cleanup state
        # must never prevent Greia Shell from starting.
        logger.exception("Unexpected Activity tree cleanup failure; continuing boot")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
