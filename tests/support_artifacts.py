"""Shared test-only Greia update/support artifact fixtures.

These helpers deliberately live under tests/. Production bundle construction
must stay fail-closed. Tests that merely need hardware support use a genuinely
valid minimal hardware-support archive. Tests that need to prove runtime
rejection of malformed support may construct the outer .greiaupdate directly
through build_unchecked_support_bundle(); that helper is never imported by
production code.
"""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import tarfile
import zipfile
from pathlib import Path

import zstandard

from greia_platform.system_updates import (
    HARDWARE_SUPPORT_NAME,
    MANIFEST_NAME,
    PAYLOAD_NAME,
    UpdateManifest,
)


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def valid_hardware_support_archive_bytes(
    *,
    architecture: str = "i386",
    suite: str = "trixie",
) -> bytes:
    """Return a small but structurally valid hardware-support.tar.zst."""

    package_name = "firmware-test"
    package_filename = "pool/firmware-test_1_all.deb"
    package_payload = b"greia-test-deb-payload"
    installed_bytes = len(package_payload) + 32 * 1024

    packages_payload = (
        f"Package: {package_name}\n"
        "Version: 1\n"
        "Architecture: all\n"
        f"Filename: {package_filename}\n"
        f"Size: {len(package_payload)}\n"
        f"SHA256: {_sha256(package_payload)}\n\n"
    ).encode("utf-8")
    packages_gzip_payload = gzip.compress(packages_payload, mtime=0)

    manifest = {
        "schema_version": 1,
        "suite": suite,
        "architecture": architecture,
        "package_count": 1,
        "total_bytes": len(package_payload),
        "total_installed_bytes": installed_bytes,
        "provided_candidate_packages": [package_name],
        "provided_firmware_packages": [package_name],
        "provided_microcode_packages": [],
        "broad_firmware_packages": [],
        "firmware_providers": {},
        "unavailable_candidate_packages": [],
        "packages": [
            {
                "package": package_name,
                "version": "1",
                "architecture": "all",
                "filename": package_filename,
                "size": len(package_payload),
                "sha256": _sha256(package_payload),
                "candidate": True,
                "installed_bytes": installed_bytes,
            }
        ],
        "repository_indexes": {
            "Packages": {
                "size": len(packages_payload),
                "sha256": _sha256(packages_payload),
            },
            "Packages.gz": {
                "size": len(packages_gzip_payload),
                "sha256": _sha256(packages_gzip_payload),
            },
        },
    }
    members = (
        ("manifest.json", (json.dumps(manifest, sort_keys=True) + "\n").encode("utf-8")),
        ("Packages", packages_payload),
        ("Packages.gz", packages_gzip_payload),
        (package_filename, package_payload),
    )

    raw_tar = io.BytesIO()
    with tarfile.open(fileobj=raw_tar, mode="w", format=tarfile.PAX_FORMAT) as archive:
        for name, payload in members:
            info = tarfile.TarInfo(name=name)
            info.size = len(payload)
            info.mode = 0o644
            info.uid = 0
            info.gid = 0
            info.uname = ""
            info.gname = ""
            info.mtime = 0
            archive.addfile(info, io.BytesIO(payload))

    return zstandard.ZstdCompressor(level=3).compress(raw_tar.getvalue())


def write_valid_hardware_support_archive(
    path: Path,
    *,
    architecture: str = "i386",
    suite: str = "trixie",
) -> bytes:
    payload = valid_hardware_support_archive_bytes(
        architecture=architecture,
        suite=suite,
    )
    Path(path).write_bytes(payload)
    return payload


def build_unchecked_support_bundle(
    *,
    output_path: Path,
    raw_payload: bytes,
    raw_support: bytes,
    version: str,
    release_id: str,
    platform_family: str,
    architecture: str,
    profile: str,
    minimum_slot_bytes: int | None = None,
    persist_read_schema_min: int = 1,
    persist_read_schema_max: int = 1,
    persist_write_schema: int = 1,
    release_notes: str = "test-only malformed support bundle",
) -> Path:
    """Build an outer v3 bundle without validating the support tar.

    This is intentionally a tests-only escape hatch for runtime refusal tests.
    It models an already-existing/legacy/tampered candidate that passed only
    the outer container integrity facts. Production code must never call it.
    """

    compressed_payload = zstandard.ZstdCompressor(level=3).compress(raw_payload)
    minimum = len(raw_payload) if minimum_slot_bytes is None else minimum_slot_bytes
    manifest = UpdateManifest(
        schema_version=3,
        release_id=release_id,
        version=version,
        platform_family=platform_family,
        architecture=architecture,
        profile=profile,
        board=None,
        payload_sha256=_sha256(compressed_payload),
        payload_size=len(compressed_payload),
        payload_uncompressed_bytes=len(raw_payload),
        payload_minimum_slot_bytes=minimum,
        hardware_support_sha256=_sha256(raw_support),
        hardware_support_size=len(raw_support),
        hardware_support_extracted_bytes_bound=None,
        persist_read_schema_min=persist_read_schema_min,
        persist_read_schema_max=persist_read_schema_max,
        persist_write_schema=persist_write_schema,
        release_notes=release_notes,
    )

    output = Path(output_path)
    if output.exists():
        output.unlink()
    with zipfile.ZipFile(output, "w") as archive:
        manifest_info = zipfile.ZipInfo(
            MANIFEST_NAME,
            date_time=(1980, 1, 1, 0, 0, 0),
        )
        manifest_info.create_system = 3
        manifest_info.external_attr = (0o644 << 16) | 0x20
        manifest_info.compress_type = zipfile.ZIP_DEFLATED
        archive.writestr(manifest_info, manifest.canonical_bytes())

        for name, payload in (
            (PAYLOAD_NAME, compressed_payload),
            (HARDWARE_SUPPORT_NAME, raw_support),
        ):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (0o644 << 16) | 0x20
            info.compress_type = zipfile.ZIP_STORED
            archive.writestr(info, payload)
    return output
