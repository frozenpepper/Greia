"""Read-only, image-owned Python bytecode prefix for Greia processes.

Why this exists: the appliance image deliberately deletes every in-tree
``__pycache__`` (Activity folders must stay bytecode-free, see
``runtime/child-runtime.toml``) and Greia processes run with
``PYTHONDONTWRITEBYTECODE=1``. Without precompiled bytecode every Shell start
and every Activity launch recompiled ~200+ platform modules from source -
measured at ~3.2 s per Activity launch on the Atom N270 reference device.

Design (CPython ``sys.pycache_prefix`` / ``PYTHONPYCACHEPREFIX``):

* image composition precompiles the curated trees (Greia ``src``, installed
  built-in Activities, the stdlib and the curated dist-packages) **with the
  target interpreter** into one root-owned prefix, e.g.
  ``/usr/lib/greia/pycache/opt/greia-os/src/greia_platform/x.cpython-311.pyc``;
* bytecode is ``checked-hash``: the interpreter verifies a source hash on
  import, so a changed source file (developer redeploy, A/B update) simply
  compiles in memory instead of running stale code, independent of mtimes;
* the prefix is mirrored outside every source tree, so Activity folders never
  contain bytecode and package validation is unchanged;
* runtime processes only *read* it: the prefix is root-owned and not
  group/world writable, processes keep ``PYTHONDONTWRITEBYTECODE=1`` and the
  Activity sandbox binds ``/`` read-only. Nothing writable is shared between
  Activities, so one Activity cannot poison another's bytecode;
* a developer-deployed Activity without precompiled bytecode still works, it
  just compiles from source as before.

:class:`TrustedBytecodePrefix` is the runtime trust gate; :class:
`BytecodePrecompiler` is the build/deploy side used by
``tools/precompile_greia_bytecode.py``.
"""

from __future__ import annotations

import importlib.util
import os
import py_compile
import stat
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final, Iterable, Iterator

#: Image-owned bytecode prefix (FHS: private, architecture-specific library data).
TRUSTED_BYTECODE_PREFIX: Final = Path("/usr/lib/greia/pycache")

#: Environment name CPython reads at start-up for ``sys.pycache_prefix``.
PYCACHE_PREFIX_ENVIRONMENT: Final = "PYTHONPYCACHEPREFIX"

#: Greia trees compile everything except in-tree bytecode directories.
GREIA_EXCLUDED_DIRECTORY_NAMES: Final = frozenset({"__pycache__"})

#: Distribution (stdlib/dist-packages) directories Greia never imports at
#: runtime: test suites, GUI/IDE tooling, packaging machinery (blocked at
#: start-up, see ``python_startup``) and large unused frameworks. Excluding
#: them bounds the image footprint; a module missed here still imports
#: correctly, it is merely compiled in memory.
DISTRIBUTION_EXCLUDED_DIRECTORY_NAMES: Final = frozenset(
    {
        "__pycache__",
        "_distutils_hack",
        "asyncio",
        "curses",
        "dist-packages",
        "distutils",
        "ensurepip",
        "idle_test",
        "idlelib",
        "lib2to3",
        "multiprocessing",
        "pip",
        "pkg_resources",
        "pydoc_data",
        "setuptools",
        "site-packages",
        "test",
        "tests",
        "tkinter",
        "turtledemo",
        "unittest",
        "venv",
        "xmlrpc",
    }
)


class TrustedBytecodePrefix:
    """Decide whether a bytecode prefix may be handed to a Greia process.

    A prefix is trusted only when it is an existing real directory owned by
    root and not writable by group/other or by the calling process. Anything
    else is ignored (the process then compiles from source), so a missing or
    tampered prefix degrades speed, never correctness or isolation.
    """

    def __init__(self, *, required_owner_uid: int = 0) -> None:
        self._required_owner_uid = required_owner_uid

    def resolve(self, candidate: str | os.PathLike[str] | None) -> Path | None:
        if not candidate:
            return None
        path = Path(candidate)
        if not path.is_absolute():
            return None
        try:
            status = path.lstat()
        except OSError:
            return None
        if not stat.S_ISDIR(status.st_mode):
            return None
        if status.st_uid != self._required_owner_uid:
            return None
        if status.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
            return None
        if os.geteuid() != 0 and os.access(path, os.W_OK):
            return None
        return path

    def for_current_process(self) -> Path | None:
        """The trusted prefix this interpreter is already using, if any."""

        return self.resolve(sys.pycache_prefix)


@dataclass(slots=True)
class BytecodeCompileReport:
    compiled: int = 0
    failed: list[tuple[Path, str]] = field(default_factory=list)
    skipped_symlinks: int = 0


class BytecodePrecompiler:
    """Compile source trees into a mirrored ``sys.pycache_prefix`` layout.

    Must run under the **target** interpreter (inside the image chroot or on
    the device): ``.pyc`` files are interpreter-version specific and their
    location is derived from each source's absolute runtime path.
    """

    def __init__(
        self,
        prefix: Path,
        *,
        excluded_directory_names: Iterable[str] = GREIA_EXCLUDED_DIRECTORY_NAMES,
    ) -> None:
        if not prefix.is_absolute():
            raise ValueError("bytecode prefix must be absolute")
        self.prefix = prefix
        self._excluded = frozenset(excluded_directory_names)

    def cache_path_for(self, source: Path) -> Path:
        """Return where the interpreter will look for ``source``'s bytecode."""

        previous = sys.pycache_prefix
        sys.pycache_prefix = str(self.prefix)
        try:
            return Path(importlib.util.cache_from_source(str(source)))
        finally:
            sys.pycache_prefix = previous

    def iter_sources(self, root: Path) -> Iterator[Path]:
        """Yield ``*.py`` files below ``root`` in deterministic order.

        Symlinked directories are not followed so a tree cannot pull foreign
        sources into the image prefix.
        """

        for directory, names, files in os.walk(root, followlinks=False):
            names[:] = sorted(
                name for name in names if name not in self._excluded
            )
            for name in sorted(files):
                if name.endswith(".py"):
                    yield Path(directory) / name

    def compile_tree(
        self, root: Path, report: BytecodeCompileReport | None = None
    ) -> BytecodeCompileReport:
        report = report if report is not None else BytecodeCompileReport()
        # Keep the caller's absolute spelling (not resolve()): the interpreter
        # derives the cache path from the module path exactly as sys.path
        # spells it at runtime, e.g. /opt/greia-os/src from PYTHONPATH.
        root = Path(os.path.abspath(root))
        if not root.is_dir():
            return report
        for source in self.iter_sources(root):
            if source.is_symlink():
                report.skipped_symlinks += 1
                continue
            target = self.cache_path_for(source)
            try:
                py_compile.compile(
                    str(source),
                    cfile=str(target),
                    doraise=True,
                    invalidation_mode=py_compile.PycInvalidationMode.CHECKED_HASH,
                )
            except (py_compile.PyCompileError, OSError, ValueError) as exc:
                report.failed.append((source, str(exc).splitlines()[-1][:200]))
                continue
            report.compiled += 1
        return report

    def seal(self, *, owner_uid: int = 0, owner_gid: int = 0) -> None:
        """Make the prefix root-owned and read-only for everyone else."""

        for directory, names, files in os.walk(self.prefix, followlinks=False):
            entries = [(Path(directory), 0o755)]
            entries.extend((Path(directory) / name, 0o644) for name in files)
            for path, mode in entries:
                if os.geteuid() == 0:
                    os.lchown(path, owner_uid, owner_gid)
                os.chmod(path, mode)


__all__ = [
    "BytecodeCompileReport",
    "BytecodePrecompiler",
    "DISTRIBUTION_EXCLUDED_DIRECTORY_NAMES",
    "GREIA_EXCLUDED_DIRECTORY_NAMES",
    "PYCACHE_PREFIX_ENVIRONMENT",
    "TRUSTED_BYTECODE_PREFIX",
    "TrustedBytecodePrefix",
]
