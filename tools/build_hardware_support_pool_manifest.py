#!/usr/bin/env python3
"""Build a deterministic candidate manifest for Greia's offline hardware pool.

The input is Debian's isenkram firmware Contents metadata already shipped in the
live installer. This tool does not download or install anything. It extracts
only Debian package names that actually provide firmware files, keeping general
isenkram hardware-utility recommendations out of the automatic pool.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


_PACKAGE_RE = re.compile(r"^[a-z0-9][a-z0-9+.-]*$")
_MAX_METADATA_FILES = 64
_MAX_METADATA_BYTES = 64 * 1024 * 1024
_MAX_PACKAGES = 512
_X86_MICROCODE_PACKAGES = ("amd64-microcode", "intel-microcode")


class PoolManifestError(RuntimeError):
    pass


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--isenkram-dir", type=Path, required=True)
    parser.add_argument("--suite", required=True)
    parser.add_argument("--architecture", required=True)
    parser.add_argument("--output", type=Path)
    return parser


def _metadata_files(root: Path, suite: str) -> tuple[Path, ...]:
    if not root.is_dir():
        raise PoolManifestError(f"isenkram metadata directory is missing: {root}")
    files = tuple(sorted(path for path in root.glob("Fw-Contents-*") if path.is_file()))
    if len(files) > _MAX_METADATA_FILES:
        raise PoolManifestError("too many isenkram firmware metadata files")
    preferred = tuple(path for path in files if suite in path.name)
    return preferred or files


def _packages(files: tuple[Path, ...]) -> tuple[str, ...]:
    packages: set[str] = set()
    total_bytes = 0
    for path in files:
        size = path.stat().st_size
        total_bytes += size
        if total_bytes > _MAX_METADATA_BYTES:
            raise PoolManifestError("isenkram firmware metadata exceeds the bounded input size")
        with path.open("r", encoding="utf-8", errors="strict") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                fields = line.split()
                if len(fields) < 2:
                    continue
                package = fields[-1].rsplit("/", 1)[-1]
                if _PACKAGE_RE.fullmatch(package):
                    packages.add(package)
                if len(packages) > _MAX_PACKAGES:
                    raise PoolManifestError("firmware package candidate count exceeds the bound")
    return tuple(sorted(packages))


def build_manifest(root: Path, suite: str, architecture: str) -> dict[str, object]:
    files = _metadata_files(root, suite)
    firmware_packages = _packages(files)
    microcode_packages: tuple[str, ...] = ()
    if architecture in {"i386", "amd64"}:
        microcode_packages = _X86_MICROCODE_PACKAGES
    return {
        "schema_version": 1,
        "suite": suite,
        "architecture": architecture,
        "metadata_files": [path.name for path in files],
        "firmware_packages": list(firmware_packages),
        "microcode_packages": list(microcode_packages),
        "candidate_packages": list(sorted(set(firmware_packages) | set(microcode_packages))),
        "policy": {
            "general_isenkram_lookup_is_advisory_only": True,
            "package_availability_must_be_verified_by_apt": True,
            "package_payloads_must_remain_debian_signature_chain_verified": True,
        },
    }


def main() -> int:
    args = _parser().parse_args()
    manifest = build_manifest(args.isenkram_dir, args.suite, args.architecture)
    encoded = json.dumps(manifest, sort_keys=True, indent=2) + "\n"
    if args.output is None:
        print(encoded, end="")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
