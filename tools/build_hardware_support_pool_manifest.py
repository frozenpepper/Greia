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
_MAX_FIRMWARE_PROVIDERS = 65536
_MAX_FIRMWARE_PATH_BYTES = 1024
_X86_MICROCODE_PACKAGES = ("amd64-microcode", "intel-microcode")
_FIRMWARE_PREFIXES = ("lib/firmware/", "usr/lib/firmware/")

#: Firmware packages that are ALWAYS pool candidates, even when isenkram's
#: Contents metadata misses them (2026-10-21 legacy-hardware reviews:
#: ``2026-10-21_LEGACY_X86_NETBOOK_HARDWARE_RISKS.md`` (archived; see git history) section 5.1
#: and ``..._PRE_M1_MAC_HARDWARE_SUPPORT.md`` section 3).  This is only a
#: candidate list: ``populate-hardware-support-pool.sh`` still drops any name
#: that APT cannot resolve in ``main non-free-firmware`` for the target suite,
#: and the pool finalizer verifies what remains.  Nothing here is installed on
#: a machine unless detection (or the fallback / ID rules) selects it.
#:
#: Deliberately absent: ``firmware-b43-installer`` / ``firmware-b43legacy-installer``
#: and ``broadcom-sta-dkms`` (contrib/non-free, download or compile at install
#: time, not redistributable); ``firmware-intel-sound`` / ``firmware-sof-signed``
#: (Haswell/Bay Trail and newer audio DSPs: 64-bit platforms that are not in the
#: i686 / pre-2015 Mac target list, and HDA needs no firmware).
FORCED_FIRMWARE_PACKAGES: tuple[str, ...] = (
    "firmware-amd-graphics",  # Radeon R600+ and 2011+ AMD Mac GPUs
    "firmware-atheros",  # ath9k_htc / AR3011 USB dongles
    "firmware-brcm80211",  # BCM4313 / BCM43224 / BCM43225 (brcmsmac)
    "firmware-iwlwifi",  # Intel 3945 / 4965 / 5xxx / 6xxx
    "firmware-libertas",  # Marvell 8xxx
    "firmware-misc-nonfree",  # Ralink RT2800/3090, some nouveau, a few tg3
    "firmware-realtek",  # RTL81xx Wi-Fi and r8169 NIC microcode
    # Best effort: Debian ships it in ``non-free`` (not ``non-free-firmware``)
    # for bookworm, so it is normally dropped as unavailable.  Kept so a suite
    # that moves it into non-free-firmware picks it up with no code change.
    "firmware-ipw2x00",
)


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


def _firmware_metadata(
    files: tuple[Path, ...],
) -> tuple[tuple[str, ...], dict[str, list[str]]]:
    packages: set[str] = set()
    providers: dict[str, set[str]] = {}
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
                try:
                    file_path, locations = line.rsplit(None, 1)
                except ValueError:
                    continue
                firmware_name = _firmware_name(file_path)
                if firmware_name is None:
                    continue
                provider_packages: set[str] = set()
                for location in locations.split(","):
                    package = location.rsplit("/", 1)[-1]
                    if _PACKAGE_RE.fullmatch(package):
                        packages.add(package)
                        provider_packages.add(package)
                if provider_packages:
                    providers.setdefault(firmware_name, set()).update(provider_packages)
                if len(packages) > _MAX_PACKAGES:
                    raise PoolManifestError("firmware package candidate count exceeds the bound")
                if len(providers) > _MAX_FIRMWARE_PROVIDERS:
                    raise PoolManifestError("firmware provider mapping exceeds the entry bound")
    return (
        tuple(sorted(packages)),
        {name: sorted(values) for name, values in sorted(providers.items())},
    )


def _firmware_name(file_path: str) -> str | None:
    for prefix in _FIRMWARE_PREFIXES:
        if file_path.startswith(prefix):
            name = file_path[len(prefix) :]
            encoded = name.encode("utf-8")
            if (
                name
                and len(encoded) <= _MAX_FIRMWARE_PATH_BYTES
                and "\x00" not in name
                and not name.startswith("/")
                and ".." not in Path(name).parts
            ):
                return name
            return None
    return None


def build_manifest(
    root: Path,
    suite: str,
    architecture: str,
    forced_firmware: tuple[str, ...] = (),
) -> dict[str, object]:
    files = _metadata_files(root, suite)
    firmware_packages, providers = _firmware_metadata(files)
    for name in forced_firmware:
        if not _PACKAGE_RE.fullmatch(name):
            raise PoolManifestError(f"forced firmware package name is invalid: {name!r}")
    firmware_packages = tuple(sorted(set(firmware_packages) | set(forced_firmware)))
    if len(firmware_packages) > _MAX_PACKAGES:
        raise PoolManifestError("firmware package candidate count exceeds the bound")
    microcode_packages: tuple[str, ...] = ()
    if architecture in {"i386", "amd64"}:
        microcode_packages = _X86_MICROCODE_PACKAGES
    return {
        "schema_version": 1,
        "suite": suite,
        "architecture": architecture,
        "metadata_files": [path.name for path in files],
        "metadata_suite_fallback": not any(suite in path.name for path in files),
        "forced_firmware_packages": sorted(set(forced_firmware)),
        "firmware_packages": list(firmware_packages),
        "microcode_packages": list(microcode_packages),
        "candidate_packages": list(sorted(set(firmware_packages) | set(microcode_packages))),
        "firmware_providers": providers,
        "policy": {
            "general_isenkram_lookup_is_advisory_only": True,
            "package_availability_must_be_verified_by_apt": True,
            "package_payloads_must_remain_debian_signature_chain_verified": True,
        },
    }


def main() -> int:
    args = _parser().parse_args()
    manifest = build_manifest(
        args.isenkram_dir,
        args.suite,
        args.architecture,
        forced_firmware=FORCED_FIRMWARE_PACKAGES,
    )
    encoded = json.dumps(manifest, sort_keys=True, indent=2) + "\n"
    if args.output is None:
        print(encoded, end="")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
