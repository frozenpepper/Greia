#!/usr/bin/env python3
"""Finalize a downloaded Greia hardware-support pool as a flat local APT repo."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import subprocess
from pathlib import Path


_PACKAGE_RE = re.compile(r"^[a-z0-9][a-z0-9+.-]*$")
_MAX_DEBS = 1024
_DEFAULT_MAX_BYTES = 2 * 1024 * 1024 * 1024


class PoolFinalizeError(RuntimeError):
    pass


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pool-root", type=Path, required=True)
    parser.add_argument("--candidate-manifest", type=Path, required=True)
    parser.add_argument("--max-bytes", type=int, default=_DEFAULT_MAX_BYTES)
    return parser


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _control(path: Path) -> str:
    completed = subprocess.run(
        ["dpkg-deb", "-f", str(path)],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
        shell=False,
    )
    if completed.returncode != 0:
        raise PoolFinalizeError(f"cannot inspect Debian package: {path.name}")
    control = completed.stdout.strip()
    if not control.startswith("Package:"):
        raise PoolFinalizeError(f"Debian package metadata is malformed: {path.name}")
    return control


def _field(control: str, name: str) -> str:
    prefix = f"{name}:"
    for line in control.splitlines():
        if line.startswith(prefix):
            return line[len(prefix) :].strip()
    return ""


def finalize_pool(pool_root: Path, candidate_manifest: Path, max_bytes: int) -> dict[str, object]:
    if max_bytes <= 0:
        raise PoolFinalizeError("pool byte bound must be positive")
    try:
        candidates = json.loads(candidate_manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PoolFinalizeError("candidate manifest is unreadable") from exc
    candidate_packages = candidates.get("candidate_packages")
    if not isinstance(candidate_packages, list) or not all(
        isinstance(item, str) and _PACKAGE_RE.fullmatch(item) for item in candidate_packages
    ):
        raise PoolFinalizeError("candidate manifest package list is invalid")

    deb_dir = pool_root / "pool"
    if not deb_dir.is_dir():
        raise PoolFinalizeError(f"hardware-support pool directory is missing: {deb_dir}")
    debs = tuple(sorted(path for path in deb_dir.glob("*.deb") if path.is_file() and not path.is_symlink()))
    if len(debs) > _MAX_DEBS:
        raise PoolFinalizeError("hardware-support pool contains too many Debian packages")

    total_bytes = sum(path.stat().st_size for path in debs)
    if total_bytes > max_bytes:
        raise PoolFinalizeError(
            f"hardware-support pool is {total_bytes} bytes, above bound {max_bytes}"
        )

    packages: list[dict[str, object]] = []
    repository_stanzas: list[str] = []
    seen_identity: set[tuple[str, str]] = set()
    provided_names: set[str] = set()
    for path in debs:
        control = _control(path)
        package = _field(control, "Package")
        version = _field(control, "Version")
        architecture = _field(control, "Architecture")
        if not _PACKAGE_RE.fullmatch(package) or not version or not architecture:
            raise PoolFinalizeError(f"Debian package identity is invalid: {path.name}")
        identity = (package, architecture)
        if identity in seen_identity:
            raise PoolFinalizeError(
                f"multiple versions for {package}:{architecture} are not allowed in one pool"
            )
        seen_identity.add(identity)
        provided_names.add(package)
        size = path.stat().st_size
        digest = _sha256(path)
        packages.append(
            {
                "package": package,
                "version": version,
                "architecture": architecture,
                "filename": f"pool/{path.name}",
                "size": size,
                "sha256": digest,
                "candidate": package in candidate_packages,
            }
        )
        repository_stanzas.append(
            control.rstrip()
            + f"\nFilename: pool/{path.name}\nSize: {size}\nSHA256: {digest}\n"
        )

    provided_candidates = sorted(set(candidate_packages) & provided_names)
    unavailable_candidates = sorted(set(candidate_packages) - provided_names)
    manifest = {
        "schema_version": 1,
        "suite": candidates.get("suite", "unknown"),
        "architecture": candidates.get("architecture", "unknown"),
        "candidate_manifest": candidate_manifest.name,
        "package_count": len(packages),
        "total_bytes": total_bytes,
        "provided_candidate_packages": provided_candidates,
        "unavailable_candidate_packages": unavailable_candidates,
        "packages": packages,
        "trust": {
            "source": "Debian packages downloaded by the Greia image builder",
            "runtime_hash_verification_required": True,
            "local_apt_repository_may_be_trusted_only_after_hash_verification": True,
        },
    }

    packages_text = "\n".join(repository_stanzas)
    (pool_root / "Packages").write_text(packages_text, encoding="utf-8")
    with (pool_root / "Packages.gz").open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", compresslevel=9, mtime=0) as handle:
            handle.write(packages_text.encode("utf-8"))
    (pool_root / "manifest.json").write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> int:
    args = _parser().parse_args()
    finalize_pool(args.pool_root, args.candidate_manifest, args.max_bytes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
