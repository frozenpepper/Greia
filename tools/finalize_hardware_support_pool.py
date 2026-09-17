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
_MAX_FIRMWARE_PROVIDERS = 65536
_MAX_FIRMWARE_PATH_BYTES = 1024
_DEFAULT_MAX_BYTES = 2 * 1024 * 1024 * 1024
#: Debian `Installed-Size` is expressed in KiB (1024-byte units).
_INSTALLED_SIZE_SCALE_BYTES = 1024
#: Deterministic per-package metadata overhead added to every
#: `installed_bytes = Installed-Size * 1024 + overhead`.
#:
#: `Installed-Size` counts only the unpacked payload files. The allowance
#: covers dpkg bookkeeping (`/var/lib/dpkg/status` entry plus per-package
#: info files such as `.list`/`.md5sums`), amortised `Packages` index cost
#: and 4 KiB-block rounding, without depending on target filesystem
#: geometry. 32 KiB is modest against typical firmware/microcode payloads
#: (MiBs) yet keeps the capacity bound conservative (fail-closed: the slot
#: gate must see *at least* the real installed footprint).
_INSTALLED_BYTES_OVERHEAD_PER_PACKAGE = 32 * 1024
#: Fail-closed hard cap for the pool-level installed bound. Compressed
#: archive bytes stay bounded by the caller-supplied `max_bytes`; the
#: installed bound is bounded by this fixed cap so a corrupt/huge
#: `Installed-Size` cannot produce an unbounded capacity claim.
_MAX_INSTALLED_BYTES = 2 * 1024 * 1024 * 1024


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


def _package_list(raw: dict[str, object], field: str) -> tuple[str, ...]:
    value = raw.get(field)
    if not isinstance(value, list) or not all(
        isinstance(item, str) and _PACKAGE_RE.fullmatch(item) for item in value
    ):
        raise PoolFinalizeError(f"candidate manifest {field} is invalid")
    return tuple(dict.fromkeys(value))


def _firmware_providers(raw: dict[str, object]) -> dict[str, tuple[str, ...]]:
    value = raw.get("firmware_providers")
    if not isinstance(value, dict) or len(value) > _MAX_FIRMWARE_PROVIDERS:
        raise PoolFinalizeError("candidate manifest firmware provider map is invalid")
    providers: dict[str, tuple[str, ...]] = {}
    for firmware_name, package_names in value.items():
        if (
            not isinstance(firmware_name, str)
            or not firmware_name
            or len(firmware_name.encode("utf-8")) > _MAX_FIRMWARE_PATH_BYTES
            or "\x00" in firmware_name
            or firmware_name.startswith("/")
            or ".." in Path(firmware_name).parts
        ):
            raise PoolFinalizeError("candidate manifest firmware path is invalid")
        if not isinstance(package_names, list) or not all(
            isinstance(item, str) and _PACKAGE_RE.fullmatch(item) for item in package_names
        ):
            raise PoolFinalizeError("candidate manifest firmware provider list is invalid")
        providers[firmware_name] = tuple(dict.fromkeys(package_names))
    return providers


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


def _installed_bytes(control: str, deb_name: str) -> int:
    """Normalize one package's installed footprint from its control data.

    Reads the Debian `Installed-Size` (KiB) field and returns
    `Installed-Size * 1024 + _INSTALLED_BYTES_OVERHEAD_PER_PACKAGE`.
    Compressed `.deb` bytes are never used here: they measure transfer
    size, not the unpacked slot footprint. A missing/malformed/negative
    or absurdly large field is a hard failure (fail-closed).
    """
    raw = _field(control, "Installed-Size")
    if not raw:
        raise PoolFinalizeError(
            f"Debian package Installed-Size is missing: {deb_name}"
        )
    try:
        kib = int(raw, 10)
    except ValueError as exc:
        raise PoolFinalizeError(
            f"Debian package Installed-Size is malformed: {deb_name}"
        ) from exc
    if kib < 0 or kib > _MAX_INSTALLED_BYTES // _INSTALLED_SIZE_SCALE_BYTES:
        raise PoolFinalizeError(
            f"Debian package Installed-Size is out of bounds: {deb_name}"
        )
    installed = kib * _INSTALLED_SIZE_SCALE_BYTES + _INSTALLED_BYTES_OVERHEAD_PER_PACKAGE
    if not 0 <= installed <= _MAX_INSTALLED_BYTES:
        raise PoolFinalizeError(
            f"Debian package installed size is out of bounds: {deb_name}"
        )
    return installed


def finalize_pool(pool_root: Path, candidate_manifest: Path, max_bytes: int) -> dict[str, object]:
    if max_bytes <= 0:
        raise PoolFinalizeError("pool byte bound must be positive")
    try:
        candidates = json.loads(candidate_manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PoolFinalizeError("candidate manifest is unreadable") from exc
    if not isinstance(candidates, dict):
        raise PoolFinalizeError("candidate manifest root is invalid")
    candidate_packages = _package_list(candidates, "candidate_packages")
    firmware_packages = _package_list(candidates, "firmware_packages")
    microcode_packages = _package_list(candidates, "microcode_packages")
    firmware_providers = _firmware_providers(candidates)
    if not set(firmware_packages).isdisjoint(microcode_packages):
        raise PoolFinalizeError("firmware and microcode candidate classes overlap")
    if set(candidate_packages) != set(firmware_packages) | set(microcode_packages):
        raise PoolFinalizeError("candidate package union does not match firmware/microcode classes")
    firmware_set = set(firmware_packages)
    if any(not set(packages) <= firmware_set for packages in firmware_providers.values()):
        raise PoolFinalizeError("firmware provider map references non-firmware candidate package")

    deb_dir = pool_root / "pool"
    if not deb_dir.is_dir():
        raise PoolFinalizeError(f"hardware-support pool directory is missing: {deb_dir}")
    debs = tuple(sorted(deb_dir.glob("*.deb")))
    if len(debs) > _MAX_DEBS:
        raise PoolFinalizeError("hardware-support pool contains too many Debian packages")
    if any(path.is_symlink() or not path.is_file() for path in debs):
        raise PoolFinalizeError("hardware-support pool contains a symlinked or invalid Debian package")

    total_bytes = sum(path.stat().st_size for path in debs)
    if total_bytes > max_bytes:
        raise PoolFinalizeError(
            f"hardware-support pool is {total_bytes} bytes, above bound {max_bytes}"
        )

    packages: list[dict[str, object]] = []
    package_sizes: dict[str, int] = {}
    repository_stanzas: list[str] = []
    seen_identity: set[tuple[str, str]] = set()
    provided_names: set[str] = set()
    candidate_set = set(candidate_packages)
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
        installed_bytes = _installed_bytes(control, path.name)
        package_sizes[package] = min(size, package_sizes.get(package, size))
        digest = _sha256(path)
        packages.append(
            {
                "package": package,
                "version": version,
                "architecture": architecture,
                "filename": f"pool/{path.name}",
                "size": size,
                "sha256": digest,
                "candidate": package in candidate_set,
                "installed_bytes": installed_bytes,
            }
        )
        repository_stanzas.append(
            control.rstrip()
            + f"\nFilename: pool/{path.name}\nSize: {size}\nSHA256: {digest}\n"
        )

    packages_text = "\n".join(repository_stanzas)
    packages_path = pool_root / "Packages"
    packages_gzip_path = pool_root / "Packages.gz"
    packages_path.write_text(packages_text, encoding="utf-8")
    with packages_gzip_path.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", compresslevel=9, mtime=0) as handle:
            handle.write(packages_text.encode("utf-8"))

    provided_candidates = sorted(candidate_set & provided_names)
    provided_firmware = sorted(firmware_set & provided_names)
    provided_microcode = sorted(set(microcode_packages) & provided_names)
    provided_firmware_set = set(provided_firmware)
    filtered_providers = {
        firmware_name: sorted(set(package_names) & provided_firmware_set)
        for firmware_name, package_names in sorted(firmware_providers.items())
        if set(package_names) & provided_firmware_set
    }
    # Live media needs broad coldplug coverage, but Debian Contents can list
    # alternative packages for one firmware file. Pick one deterministic,
    # minimal verified provider for each concrete file; keep all alternatives
    # in the frozen pool for machine-specific target selection.
    broad_firmware = sorted(
        {
            min(
                providers,
                key=lambda package: (package_sizes.get(package, max_bytes + 1), package),
            )
            for providers in filtered_providers.values()
            if providers
        }
    )
    unavailable_candidates = sorted(candidate_set - provided_names)
    total_installed_bytes = sum(
        int(entry["installed_bytes"]) for entry in packages
    )
    if total_installed_bytes > _MAX_INSTALLED_BYTES:
        raise PoolFinalizeError(
            f"hardware-support pool installed size {total_installed_bytes} bytes "
            f"is above bound {_MAX_INSTALLED_BYTES}"
        )
    manifest = {
        "schema_version": 1,
        "suite": candidates.get("suite", "unknown"),
        "architecture": candidates.get("architecture", "unknown"),
        "candidate_manifest": candidate_manifest.name,
        "metadata_files": candidates.get("metadata_files", []),
        "metadata_suite_fallback": bool(candidates.get("metadata_suite_fallback", False)),
        "package_count": len(packages),
        "total_bytes": total_bytes,
        "total_installed_bytes": total_installed_bytes,
        "installed_bytes_overhead_per_package": _INSTALLED_BYTES_OVERHEAD_PER_PACKAGE,
        "provided_candidate_packages": provided_candidates,
        "provided_firmware_packages": provided_firmware,
        "provided_microcode_packages": provided_microcode,
        "broad_firmware_packages": broad_firmware,
        "firmware_providers": filtered_providers,
        "unavailable_candidate_packages": unavailable_candidates,
        "packages": packages,
        "repository_indexes": {
            "Packages": {
                "size": packages_path.stat().st_size,
                "sha256": _sha256(packages_path),
            },
            "Packages.gz": {
                "size": packages_gzip_path.stat().st_size,
                "sha256": _sha256(packages_gzip_path),
            },
        },
        "trust": {
            "source": "Debian packages downloaded by the Greia image builder",
            "runtime_hash_verification_required": True,
            "local_apt_repository_may_be_trusted_only_after_hash_verification": True,
        },
    }

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
