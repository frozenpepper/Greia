"""Bounded, in-memory reuse of launch-time runtime package validation.

Every launch runs the runtime adapter's package validation (for Python: the
source/import/path-safety policy of ``runtime/child-runtime.toml`` over every
``.py`` file). On the Atom N270 reference floor that costs 0.3-3 s per launch
even after the single-pass scan, and it repeats on every launch of the same
unchanged package.

``LaunchValidationCache`` remembers, per Shell process, that a package passed
validation together with a cheap stat fingerprint of its tree (every entry's
relative path, type, size, mtime_ns, ctime_ns and inode; no content is read).
A later launch whose fingerprint is identical skips re-validation; any
difference, or any error computing the fingerprint, runs the normal full
validation again. The fingerprint is only a cache key that decides whether
the existing validation must re-run: it is not an integrity or anti-tamper
mechanism, and an edited package that still passes validation launches
normally.

Scope (``read_only_built_in_package``): only ``BUILT_IN`` packages that sit in
a root-owned location this process cannot write (the installed
``/opt/greia-os/activities`` tree). Parent-installed, developer and any other
package in a writable location is fully validated on every launch. Failures
are never cached. The cache holds at most ``capacity`` entries of a 16-byte
digest each, lives only as long as its ``RuntimeManager`` (one Shell process)
and is never persisted.
"""

from __future__ import annotations

import hashlib
import logging
import os
import threading
import time
from collections import OrderedDict
from pathlib import Path
from typing import Callable, Protocol

from greia_platform.activities import ActivityManifest, package_tree_fingerprint
from greia_platform.trust import PackageTrust


logger = logging.getLogger(__name__)

DEFAULT_LAUNCH_VALIDATION_CACHE_CAPACITY = 64


class _PackageValidator(Protocol):
    runtime_type: str

    def validate_package(self, manifest: ActivityManifest) -> None: ...


CacheEligibility = Callable[[ActivityManifest, "PackageTrust | None"], bool]


def _read_only_root_owned(path: Path) -> bool:
    try:
        metadata = path.stat()
    except OSError:
        return False
    if metadata.st_uid != 0 or metadata.st_mode & 0o022:
        return False
    return not os.access(path, os.W_OK)


def read_only_built_in_package(
    manifest: ActivityManifest, package_trust: PackageTrust | None
) -> bool:
    """Default eligibility: a built-in package in a read-only root-owned tree.

    Both the package directory and its source directory must be owned by
    root, carry no group/other write bit and be unwritable for this process.
    A source checkout, a Parent generation or a developer drop therefore never
    qualifies and is validated on every launch.
    """

    if package_trust is not PackageTrust.BUILT_IN:
        return False
    root = manifest.root
    return _read_only_root_owned(root) and _read_only_root_owned(root.parent)


def tree_fingerprint_digest(root: Path) -> bytes:
    """16-byte digest of ``package_tree_fingerprint`` (stat data only)."""

    return hashlib.blake2b(
        repr(package_tree_fingerprint(root)).encode("utf-8"), digest_size=16
    ).digest()


class LaunchValidationCache:
    """Reuse a successful runtime package validation while the tree is unchanged.

    ``validate`` is the single entry point used by ``RuntimeManager``. It
    either proves the package unchanged since an earlier successful
    validation in this process (fingerprint match) or delegates to the
    adapter's full ``validate_package``; adapter errors propagate unchanged.
    """

    def __init__(
        self,
        *,
        capacity: int = DEFAULT_LAUNCH_VALIDATION_CACHE_CAPACITY,
        eligible: CacheEligibility = read_only_built_in_package,
        fingerprint: Callable[[Path], bytes] = tree_fingerprint_digest,
    ) -> None:
        if capacity < 0:
            raise ValueError("launch validation cache capacity cannot be negative")
        self._capacity = capacity
        self._eligible = eligible
        self._fingerprint = fingerprint
        self._entries: OrderedDict[tuple[str, str, str], bytes] = OrderedDict()
        self._lock = threading.Lock()

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def validate(
        self,
        adapter: _PackageValidator,
        manifest: ActivityManifest,
        package_trust: PackageTrust | None,
    ) -> bool:
        """Validate ``manifest`` through ``adapter`` unless provably unchanged.

        Returns ``True`` when a cached validation was reused, ``False`` when
        the full validation ran (and passed; failures raise).
        """

        started = time.monotonic()
        if self._capacity == 0 or not self._eligible(manifest, package_trust):
            adapter.validate_package(manifest)
            self._log(manifest, "full (not cacheable)", started)
            return False
        key = (adapter.runtime_type, str(manifest.root), str(manifest.launch_path))
        try:
            # Taken before validation: a change made while validating leaves a
            # stale key, so the next launch validates again (conservative).
            fingerprint: bytes | None = self._fingerprint(manifest.root)
        except (OSError, ValueError):
            fingerprint = None
        if fingerprint is not None:
            with self._lock:
                cached = self._entries.get(key)
                if cached == fingerprint:
                    self._entries.move_to_end(key)
                    hit = True
                else:
                    hit = False
            if hit:
                self._log(manifest, "reused (tree unchanged)", started)
                return True
        with self._lock:
            self._entries.pop(key, None)
        adapter.validate_package(manifest)
        if fingerprint is not None:
            with self._lock:
                self._entries[key] = fingerprint
                self._entries.move_to_end(key)
                while len(self._entries) > self._capacity:
                    self._entries.popitem(last=False)
        self._log(manifest, "full", started)
        return False

    @staticmethod
    def _log(manifest: ActivityManifest, outcome: str, started: float) -> None:
        logger.info(
            "Launch package validation for %s: %s in %.0f ms",
            manifest.activity_id,
            outcome,
            (time.monotonic() - started) * 1000.0,
        )


__all__ = [
    "DEFAULT_LAUNCH_VALIDATION_CACHE_CAPACITY",
    "LaunchValidationCache",
    "read_only_built_in_package",
    "tree_fingerprint_digest",
]
