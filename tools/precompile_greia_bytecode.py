#!/usr/bin/env python3
"""Precompile Greia's read-only bytecode prefix with the TARGET interpreter.

Bytecode is CPython-version specific, so this must run with the interpreter
that will execute Greia: inside the image chroot during composition
(``build/lib/compose.sh``) or on the device itself after a direct developer
deploy, for example::

    sudo /usr/bin/python3 -I -B precompile_greia_bytecode.py --greia-root /opt/greia-os

(``-B`` because ``-I`` ignores ``PYTHONDONTWRITEBYTECODE``.) The launcher and
Parent units must carry ``PYTHONPYCACHEPREFIX=/usr/lib/greia/pycache`` for the
prefix to be used; Activities inherit it from the launcher.

Never run it on a build/development host for a different Python and copy the
result. The prefix is rebuilt from scratch (unless ``--no-clean``), sealed
root-owned/read-only, and contains ``checked-hash`` bytecode for:

* ``<greia-root>/src`` and the installed built-in ``<greia-root>/activities``
  (Activity folders themselves stay free of bytecode);
* the interpreter's stdlib and the system ``dist-packages`` (minus test suites,
  GUI tooling and setuptools/pkg_resources, which Greia never imports).

Exit status is non-zero when a Greia source file fails to compile; failures in
distribution trees are reported but tolerated (that code never compiled for
Greia either).
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import sysconfig
from pathlib import Path


def _import_bytecode_cache(greia_root: Path):
    """Import the platform owner from the tree being compiled.

    ``-I`` (isolated mode) is recommended, so the source tree is added
    explicitly instead of relying on PYTHONPATH or ``.pth`` files.
    """

    candidates = [greia_root / "src"]
    script = globals().get("__file__")  # absent when composition pipes via stdin
    if script:
        candidates.append(Path(script).resolve().parents[1] / "src")
    for candidate in candidates:
        if (candidate / "greia_platform" / "bytecode_cache.py").is_file():
            sys.path.insert(0, str(candidate))
            break
    from greia_platform import bytecode_cache

    return bytecode_cache


def _default_distribution_roots() -> list[Path]:
    roots = [Path(sysconfig.get_paths()["stdlib"])]
    debian_dist = Path("/usr/lib/python3/dist-packages")
    if debian_dist.is_dir():
        roots.append(debian_dist)
    return roots


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--greia-root", type=Path, default=Path("/opt/greia-os"))
    parser.add_argument("--prefix", type=Path, default=None,
                        help="bytecode prefix (default: the platform's trusted prefix)")
    parser.add_argument("--no-distribution", action="store_true",
                        help="compile only Greia src/activities, not stdlib/dist-packages")
    parser.add_argument("--no-clean", action="store_true",
                        help="keep existing prefix content instead of rebuilding it")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    sys.dont_write_bytecode = True
    args = parse_args(argv)
    greia_root = Path(os.path.abspath(args.greia_root))
    bytecode_cache = _import_bytecode_cache(greia_root)
    prefix = Path(os.path.abspath(args.prefix or bytecode_cache.TRUSTED_BYTECODE_PREFIX))
    if prefix == Path("/") or greia_root in (prefix, *prefix.parents):
        print(f"refusing unsafe bytecode prefix {prefix}", file=sys.stderr)
        return 2

    if not args.no_clean and prefix.exists():
        shutil.rmtree(prefix)
    prefix.mkdir(parents=True, exist_ok=True)

    compiler = bytecode_cache.BytecodePrecompiler(prefix)
    greia_report = bytecode_cache.BytecodeCompileReport()
    for root in (greia_root / "src", greia_root / "activities"):
        compiler.compile_tree(root, greia_report)
    distribution_report = bytecode_cache.BytecodeCompileReport()
    if not args.no_distribution:
        distribution = bytecode_cache.BytecodePrecompiler(
            prefix,
            excluded_directory_names=bytecode_cache.DISTRIBUTION_EXCLUDED_DIRECTORY_NAMES,
        )
        for root in _default_distribution_roots():
            distribution.compile_tree(root, distribution_report)
    compiler.seal()

    total_bytes = sum(
        path.stat().st_size for path in prefix.rglob("*.pyc") if path.is_file()
    )
    print(
        f"bytecode prefix {prefix} ({sys.implementation.cache_tag}): "
        f"greia={greia_report.compiled} distribution={distribution_report.compiled} "
        f"size={total_bytes / (1024 * 1024):.1f} MiB"
    )
    for source, reason in distribution_report.failed[:20]:
        print(f"warning: not compiled {source}: {reason}", file=sys.stderr)
    for source, reason in greia_report.failed:
        print(f"error: Greia source failed to compile {source}: {reason}", file=sys.stderr)
    return 1 if greia_report.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
