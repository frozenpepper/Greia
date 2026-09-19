"""Shared hardware-support archive parser (Repair R4-D-PARSER).

Single owner for the ``hardware-support.tar.zst`` format contract used by
both the build/release side (``greia_installer.hardware_support``) and the
runtime staging side (``greia_platform.candidate_support``).

Both wrappers delegate here; no parser logic lives in the wrappers.

Design notes:

- Streaming only. Inspection hashes/counts compressed bytes, decompresses
  through a bounded zstd stream reader, and walks the tar with
  ``tarfile`` streaming mode (``r|``). Only ``manifest.json`` (<=8 MiB)
  is buffered; ``Packages``/``Packages.gz`` (<=32 MiB each) and every
  ``pool/*.deb`` are hashed in bounded chunks and discarded (inspect) or
  written straight to disk (extract). The full archive never resides in
  RAM and no intermediate compressed temp file is created.
- One production compressed bound (512 MiB) for ``.greiaupdate``
  members. The historical build-side 2 GiB outer bound is retired; both
  sides alias this module's canonical constants.
- Full manifest semantics mirror
  ``VerifiedHardwareSupportPool.load``: schema, suite/architecture,
  per-package metadata (Debian ``Installed-Size`` accounting),
  ``sum(installed_bytes) == total_installed_bytes``,
  ``sum(size) == total_bytes``, package digests/sizes, repository index
  digests/sizes, candidate/firmware/microcode sets, firmware-provider map
  and broad-firmware coverage. Compressed ``.deb`` bytes never substitute
  for the installed bound.
- Fail-closed tar shape: exactly ``manifest.json``, ``Packages``,
  ``Packages.gz`` and ``pool/*.deb`` (single level). Absolute paths,
  backslashes, ``..``/``.`` segments, symlinks, hardlinks, device nodes,
  FIFOs, unexpected directories/files, duplicate members, missing
  manifest/packages, unmanifested payloads and every size/count overflow
  are rejected with the same verdict on both paths.

This module never imports update-service composition
(``system_updates``) or the installer pool loader; both wrappers import
from here in one direction only.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat as _stat
import tarfile
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO


class HardwareSupportArchiveError(RuntimeError):
    """The hardware-support archive is missing, malformed or unsafe."""


#: Single production compressed member bound for ``.greiaupdate``
#: ``hardware-support.tar.zst``. Canonical owner for
#: ``system_updates.MAX_HARDWARE_SUPPORT_BYTES``,
#: ``candidate_support.MAX_CANDIDATE_SUPPORT_COMPRESSED_BYTES`` and the
#: retired build-side ``_MAX_SUPPORT_ARCHIVE_BYTES`` (all 512 MiB).
MAX_ARCHIVE_COMPRESSED_BYTES = 512 * 1024 * 1024

#: Single production uncompressed-tar bound (payloads do not compress
#: further inside the tar; twice the compressed bound leaves header
#: headroom without opening a decompression-bomb surface).
MAX_ARCHIVE_UNCOMPRESSED_BYTES = 1024 * 1024 * 1024

#: Single per-file bound inside the tar.
MAX_ARCHIVE_FILE_BYTES = 512 * 1024 * 1024

#: Single member-count bound: at most 1024 pool payloads plus the three
#: top-level release files, with headroom for directory entries.
MAX_ARCHIVE_MEMBERS = 2048

#: Single embedded manifest bound.
MAX_ARCHIVE_MANIFEST_BYTES = 8 * 1024 * 1024

#: Pool/package accounting bounds (mirror the installer pool loader).
MAX_ARCHIVE_POOL_PACKAGES = 1024
MAX_ARCHIVE_POOL_BYTES = 2 * 1024 * 1024 * 1024
MAX_ARCHIVE_INDEX_BYTES = 32 * 1024 * 1024
MAX_ARCHIVE_FIRMWARE_PROVIDERS = 65536
MAX_ARCHIVE_FIRMWARE_PATH_BYTES = 1024

#: zstd framing every built archive must carry.
ARCHIVE_ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"

#: Exact expected top-level release files.
TOP_FILES = frozenset({"manifest.json", "Packages", "Packages.gz"})
POOL_DIR = "pool"

_CHUNK_BYTES = 1024 * 1024

#: Conservative extracted-size allocation model (Repair R4-EF-STAGE).
#:
#: PERSIST staging preflight must reserve real filesystem blocks, not bare
#: byte sums. Every extracted regular file costs
#: ``ceil(size / EXTRACTED_BLOCK_BYTES) * EXTRACTED_BLOCK_BYTES`` (one
#: 4096-byte block granularity, the conservative fixed-block reading of
#: ``statvfs.f_frsize``-style accounting), every tar member costs one
#: 512-byte header block, and a bounded metadata allowance covers directory
#: entries, PAX extended headers and pool-load bookkeeping. The builder
#: declares this bound from the exact archived files
#: (:func:`extracted_bytes_bound_for_members`) and the runtime recomputes
#: it from the observed stream; bare ``sum(sizes) + 512/member`` must never
#: be used as a staging bound.
EXTRACTED_BLOCK_BYTES = 4096
EXTRACTED_TAR_HEADER_BYTES = 512
EXTRACTED_METADATA_ALLOWANCE_BYTES = 64 * 1024


def extracted_bytes_bound_for_members(
    sizes: object, *, member_count: int | None = None
) -> int:
    """Return the conservative extracted-bytes bound for archived files.

    ``sizes`` is the exact per-file member sizes (directory entries carry
    no bytes and must not be included). The bound is deterministic so the
    builder declaration and the runtime observation agree byte-for-byte on
    identical archives. Refuses non-integer/negative sizes and totals
    beyond :data:`MAX_ARCHIVE_UNCOMPRESSED_BYTES`.
    """
    if isinstance(sizes, (bytes, str, dict)):
        raise HardwareSupportArchiveError(
            "hardware-support extracted bound sizes are invalid"
        )
    try:
        size_list = list(sizes)  # type: ignore[arg-type]
    except TypeError as exc:
        raise HardwareSupportArchiveError(
            "hardware-support extracted bound sizes are invalid"
        ) from exc
    blocks_total = 0
    for size in size_list:
        if isinstance(size, bool) or not isinstance(size, int) or size < 0:
            raise HardwareSupportArchiveError(
                "hardware-support extracted bound size is invalid"
            )
        if size > MAX_ARCHIVE_FILE_BYTES:
            raise HardwareSupportArchiveError(
                "hardware-support archive file is outside Greia bounds"
            )
        blocks_total += (size + EXTRACTED_BLOCK_BYTES - 1) // EXTRACTED_BLOCK_BYTES
    count = len(size_list) if member_count is None else member_count
    if isinstance(count, bool) or not isinstance(count, int) or count < len(size_list):
        raise HardwareSupportArchiveError(
            "hardware-support extracted bound member count is invalid"
        )
    if count > MAX_ARCHIVE_MEMBERS:
        raise HardwareSupportArchiveError(
            "hardware-support archive member count is outside Greia bounds"
        )
    bound = (
        blocks_total * EXTRACTED_BLOCK_BYTES
        + count * EXTRACTED_TAR_HEADER_BYTES
        + EXTRACTED_METADATA_ALLOWANCE_BYTES
    )
    if bound > MAX_ARCHIVE_UNCOMPRESSED_BYTES:
        raise HardwareSupportArchiveError(
            "hardware-support archive decompresses beyond Greia bounds"
        )
    return bound

_PACKAGE_RE = re.compile(r"^[a-z0-9][a-z0-9+.-]*$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _safe_firmware_name(value: object) -> bool:
    if not isinstance(value, str) or not value or "\x00" in value:
        return False
    try:
        encoded = value.encode("utf-8")
    except UnicodeError:
        return False
    if len(encoded) > MAX_ARCHIVE_FIRMWARE_PATH_BYTES or value.startswith("/"):
        return False
    return ".." not in Path(value).parts


@dataclass(frozen=True, slots=True)
class ArchivePackage:
    """Validated per-package metadata (mirrors HardwareSupportPoolPackage)."""

    package: str
    version: str
    architecture: str
    filename: str
    size: int
    sha256: str
    candidate: bool
    installed_bytes: int

    def __post_init__(self) -> None:
        validate_package_fields(
            package=self.package,
            version=self.version,
            architecture=self.architecture,
            filename=self.filename,
            size=self.size,
            sha256=self.sha256,
            candidate=self.candidate,
            installed_bytes=self.installed_bytes,
        )


def validate_package_fields(
    *,
    package: object,
    version: object,
    architecture: object,
    filename: object,
    size: object,
    sha256: object,
    candidate: object,
    installed_bytes: object,
) -> None:
    """Single owner for per-package field validation."""
    if not isinstance(package, str) or not _PACKAGE_RE.fullmatch(package):
        raise HardwareSupportArchiveError("hardware-support package name is invalid")
    if not isinstance(filename, str):
        raise HardwareSupportArchiveError("hardware-support package filename is unsafe")
    path = Path(filename)
    if path.is_absolute() or ".." in path.parts or path.parts[:1] != ("pool",):
        raise HardwareSupportArchiveError("hardware-support package filename is unsafe")
    if path.name != str(filename).split("/")[-1] or not path.name.endswith(".deb"):
        raise HardwareSupportArchiveError("hardware-support package filename is invalid")
    if (
        not isinstance(version, str)
        or not version
        or len(version) > 256
    ):
        raise HardwareSupportArchiveError("hardware-support package version is invalid")
    if (
        not isinstance(architecture, str)
        or not architecture
        or len(architecture) > 32
    ):
        raise HardwareSupportArchiveError(
            "hardware-support package architecture is invalid"
        )
    if isinstance(size, bool) or not isinstance(size, int) or not 0 <= size <= MAX_ARCHIVE_POOL_BYTES:
        raise HardwareSupportArchiveError("hardware-support package size is invalid")
    if not isinstance(sha256, str) or not _SHA256_RE.fullmatch(sha256):
        raise HardwareSupportArchiveError("hardware-support package digest is invalid")
    if not isinstance(candidate, bool):
        raise HardwareSupportArchiveError("hardware-support candidate flag is invalid")
    if (
        isinstance(installed_bytes, bool)
        or not isinstance(installed_bytes, int)
        or not 0 <= installed_bytes <= MAX_ARCHIVE_POOL_BYTES
    ):
        raise HardwareSupportArchiveError(
            "hardware-support package installed size is invalid"
        )


@dataclass(frozen=True, slots=True)
class ValidatedManifest:
    packages: tuple[ArchivePackage, ...]
    total_bytes: int
    total_installed_bytes: int
    provided_candidates: frozenset[str]
    provided_firmware: frozenset[str]
    provided_microcode: frozenset[str]
    broad_firmware: frozenset[str]
    firmware_providers: tuple[tuple[str, tuple[str, ...]], ...]
    repository_indexes: dict[str, dict[str, object]]
    installed_overhead: int | None
    #: Builder-declared conservative extracted-bytes bound
    #: (``extracted_bytes_bound`` inner-manifest field, Repair R4-EF-STAGE).
    #: ``None`` when the archive predates the field; the streaming finish
    #: still computes and caps the observed bound, but no declared-vs-
    #: observed comparison applies. Present builders must derive it with
    #: :func:`extracted_bytes_bound_for_members` from the exact archived
    #: files; R4-G-RECEIPT-era release flows read the same field name.
    extracted_bound: int | None = None


def _validated_package_set(raw: dict[str, object], field: str) -> frozenset[str]:
    value = raw.get(field)
    if not isinstance(value, list) or not all(
        isinstance(item, str) and _PACKAGE_RE.fullmatch(item) for item in value
    ):
        raise HardwareSupportArchiveError(f"hardware-support {field} is invalid")
    if len(value) != len(set(value)):
        raise HardwareSupportArchiveError(f"hardware-support {field} contains duplicates")
    return frozenset(value)


def _validated_firmware_providers(
    raw: dict[str, object], firmware_packages: frozenset[str]
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    value = raw.get("firmware_providers")
    if not isinstance(value, dict) or len(value) > MAX_ARCHIVE_FIRMWARE_PROVIDERS:
        raise HardwareSupportArchiveError("hardware-support firmware provider map is invalid")
    result: list[tuple[str, tuple[str, ...]]] = []
    for firmware_name, package_names in value.items():
        if not _safe_firmware_name(firmware_name):
            raise HardwareSupportArchiveError(
                "hardware-support firmware provider path is invalid"
            )
        if not isinstance(package_names, list) or not package_names or not all(
            isinstance(item, str) and _PACKAGE_RE.fullmatch(item) for item in package_names
        ):
            raise HardwareSupportArchiveError(
                "hardware-support firmware provider packages are invalid"
            )
        unique = tuple(dict.fromkeys(package_names))
        if len(unique) != len(package_names):
            raise HardwareSupportArchiveError(
                "hardware-support firmware provider packages contain duplicates"
            )
        if any(package not in firmware_packages for package in unique):
            raise HardwareSupportArchiveError(
                "hardware-support firmware provider references non-firmware package"
            )
        result.append((firmware_name, unique))
    return tuple(sorted(result))


def parse_manifest_dict(raw: object) -> ValidatedManifest:
    """Validate one decoded manifest dict; single manifest-semantics owner."""
    if not isinstance(raw, dict) or raw.get("schema_version") != 1:
        raise HardwareSupportArchiveError(
            "unsupported hardware-support archive manifest schema"
        )
    suite = raw.get("suite")
    architecture = raw.get("architecture")
    if not isinstance(suite, str) or not suite or len(suite) > 64:
        raise HardwareSupportArchiveError("hardware-support suite is invalid")
    if not isinstance(architecture, str) or not architecture or len(architecture) > 32:
        raise HardwareSupportArchiveError("hardware-support architecture is invalid")
    entries = raw.get("packages")
    if not isinstance(entries, list) or len(entries) > MAX_ARCHIVE_POOL_PACKAGES:
        raise HardwareSupportArchiveError("hardware-support archive package list is invalid")
    packages: list[ArchivePackage] = []
    seen_identity: set[tuple[str, str]] = set()
    for entry in entries:
        if not isinstance(entry, dict) or "installed_bytes" not in entry:
            raise HardwareSupportArchiveError(
                "hardware-support archive package installed size is missing"
            )
        try:
            package = ArchivePackage(
                package=entry["package"],
                version=entry["version"],
                architecture=entry["architecture"],
                filename=entry["filename"],
                size=entry["size"],
                sha256=entry["sha256"],
                candidate=entry["candidate"],
                installed_bytes=entry["installed_bytes"],
            )
        except (KeyError, TypeError) as exc:
            raise HardwareSupportArchiveError(
                "hardware-support archive package entry is incomplete"
            ) from exc
        identity = (package.package, package.architecture)
        if identity in seen_identity:
            raise HardwareSupportArchiveError(
                "hardware-support archive package identity is duplicated"
            )
        seen_identity.add(identity)
        packages.append(package)
    total = sum(item.size for item in packages)
    total_installed = sum(item.installed_bytes for item in packages)
    manifest_total = raw.get("total_bytes")
    if (
        not isinstance(manifest_total, int)
        or isinstance(manifest_total, bool)
        or manifest_total != total
    ):
        raise HardwareSupportArchiveError(
            "hardware-support archive total size does not match manifest"
        )
    manifest_installed = raw.get("total_installed_bytes")
    if (
        not isinstance(manifest_installed, int)
        or isinstance(manifest_installed, bool)
        or manifest_installed != total_installed
    ):
        raise HardwareSupportArchiveError(
            "hardware-support archive installed total does not match manifest"
        )
    if not 0 <= total <= MAX_ARCHIVE_POOL_BYTES:
        raise HardwareSupportArchiveError(
            "hardware-support archive total size is outside Greia bounds"
        )
    if not 0 <= total_installed <= MAX_ARCHIVE_POOL_BYTES:
        raise HardwareSupportArchiveError(
            "hardware-support archive installed total is outside Greia bounds"
        )
    indexes = raw.get("repository_indexes")
    if not isinstance(indexes, dict) or set(indexes) != {"Packages", "Packages.gz"}:
        raise HardwareSupportArchiveError(
            "hardware-support repository index manifest is invalid"
        )
    for index_name in ("Packages", "Packages.gz"):
        metadata = indexes.get(index_name)
        if not isinstance(metadata, dict):
            raise HardwareSupportArchiveError(
                "hardware-support repository index metadata is invalid"
            )
        size = metadata.get("size")
        digest = metadata.get("sha256")
        if not isinstance(size, int) or isinstance(size, bool) or not 0 <= size <= MAX_ARCHIVE_INDEX_BYTES:
            raise HardwareSupportArchiveError(
                "hardware-support repository index size is invalid"
            )
        if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
            raise HardwareSupportArchiveError(
                "hardware-support repository index digest is invalid"
            )
    provided = _validated_package_set(raw, "provided_candidate_packages")
    firmware = _validated_package_set(raw, "provided_firmware_packages")
    microcode = _validated_package_set(raw, "provided_microcode_packages")
    broad = _validated_package_set(raw, "broad_firmware_packages")
    providers = _validated_firmware_providers(raw, firmware)
    if not firmware.isdisjoint(microcode):
        raise HardwareSupportArchiveError(
            "hardware-support firmware/microcode classes overlap"
        )
    if firmware | microcode != provided:
        raise HardwareSupportArchiveError(
            "hardware-support candidate classes do not match candidate set"
        )
    if not broad <= firmware:
        raise HardwareSupportArchiveError(
            "broad live firmware references non-firmware package"
        )
    if any(not (set(provider_packages) & broad) for _, provider_packages in providers):
        raise HardwareSupportArchiveError(
            "broad live firmware does not cover every mapped firmware file"
        )
    manifest_candidates = {item.package for item in packages if item.candidate}
    if not provided <= manifest_candidates:
        raise HardwareSupportArchiveError(
            "hardware-support candidate list references non-candidate payloads"
        )
    overhead = raw.get("installed_bytes_overhead_per_package")
    if overhead is not None and (
        isinstance(overhead, bool)
        or not isinstance(overhead, int)
        or not 0 <= overhead <= MAX_ARCHIVE_POOL_BYTES
    ):
        raise HardwareSupportArchiveError(
            "hardware-support installed overhead allowance is invalid"
        )
    declared_bound = raw.get("extracted_bytes_bound")
    if declared_bound is not None and (
        isinstance(declared_bound, bool)
        or not isinstance(declared_bound, int)
        or not 0 <= declared_bound <= MAX_ARCHIVE_UNCOMPRESSED_BYTES
    ):
        raise HardwareSupportArchiveError(
            "hardware-support extracted bound declaration is invalid"
        )
    return ValidatedManifest(
        packages=tuple(packages),
        total_bytes=total,
        total_installed_bytes=total_installed,
        provided_candidates=provided,
        provided_firmware=firmware,
        provided_microcode=microcode,
        broad_firmware=broad,
        firmware_providers=providers,
        repository_indexes={k: dict(v) for k, v in indexes.items()},  # type: ignore[union-attr]
        installed_overhead=overhead,  # type: ignore[arg-type]
        extracted_bound=declared_bound,  # type: ignore[arg-type]
    )


def parse_manifest_bytes(payload: bytes) -> ValidatedManifest:
    try:
        raw = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HardwareSupportArchiveError(
            "hardware-support archive manifest is not valid JSON"
        ) from exc
    return parse_manifest_dict(raw)


def normalize_archive_name(name: str) -> str:
    text = name.strip()
    while text.startswith("./"):
        text = text[2:]
    return text


def reject_unsafe_name(name: str) -> str:
    """Return the normalized name or raise for traversal/absolute shapes."""
    if not name or name.startswith("/") or "\\" in name:
        raise HardwareSupportArchiveError(
            "hardware-support archive contains an unsafe member"
        )
    normalized = normalize_archive_name(name)
    if not normalized or normalized in (".", "/"):
        raise HardwareSupportArchiveError(
            "hardware-support archive contains an unsafe member"
        )
    parts = Path(normalized).parts
    if not parts or ".." in parts or "." in parts:
        raise HardwareSupportArchiveError(
            "hardware-support archive contains an unsafe member"
        )
    if normalized.startswith("/") or "\\" in normalized:
        raise HardwareSupportArchiveError(
            "hardware-support archive contains an unsafe member"
        )
    return normalized


def validate_member_header(member: tarfile.TarInfo) -> tuple[str, str]:
    """Validate one tar header; return (normalized_name, kind).

    Kind is ``"dir"`` for the allowed ``pool/`` directory entry or
    ``"file"`` for an allowed regular file. Every other shape raises
    with the same verdict on both build and runtime paths.
    """
    raw_name = member.name
    normalized = reject_unsafe_name(raw_name)
    if member.issym() or member.islnk():
        raise HardwareSupportArchiveError(
            f"hardware-support archive member is a link (refused): {normalized!r}"
        )
    if member.isdev() or member.isfifo():
        raise HardwareSupportArchiveError(
            f"hardware-support archive member is a special file (refused): {normalized!r}"
        )
    if member.isdir():
        if normalized.rstrip("/") not in ("", ".", POOL_DIR):
            raise HardwareSupportArchiveError(
                f"hardware-support archive has an unexpected directory: {normalized!r}"
            )
        return normalized, "dir"
    if not member.isfile():
        raise HardwareSupportArchiveError(
            f"hardware-support archive member is not a regular file: {normalized!r}"
        )
    if normalized in TOP_FILES:
        if member.size < 0 or member.size > MAX_ARCHIVE_FILE_BYTES:
            raise HardwareSupportArchiveError(
                f"hardware-support archive file is outside Greia bounds: {normalized!r}"
            )
        if normalized == "manifest.json" and not 1 <= member.size <= MAX_ARCHIVE_MANIFEST_BYTES:
            raise HardwareSupportArchiveError(
                "hardware-support archive manifest size is outside Greia bounds"
            )
        return normalized, "file"
    parts = Path(normalized).parts
    if (
        len(parts) == 2
        and parts[0] == POOL_DIR
        and parts[1].endswith(".deb")
        and parts[1] not in (".deb",)
    ):
        if member.size < 0 or member.size > MAX_ARCHIVE_FILE_BYTES:
            raise HardwareSupportArchiveError(
                f"hardware-support archive file is outside Greia bounds: {normalized!r}"
            )
        return normalized, "file"
    raise HardwareSupportArchiveError(
        f"hardware-support archive carries an unexpected member: {normalized!r}"
    )


@dataclass(frozen=True, slots=True)
class HardwareSupportArchiveMetadata:
    """Digest-verified facts for one hardware-support archive.

    Stable typed shape consumed by release capacity proof (R4-C-PERSIST)
    and staging (R4-EF-STAGE): ``total_bytes`` is the compressed transfer
    bound, ``total_installed_bytes`` is the installed-capacity bound,
    ``extracted_size_bound`` is the deterministic PERSIST staging bound.
    """

    support_sha256: str
    support_size: int
    total_bytes: int
    total_installed_bytes: int
    uncompressed_bytes: int
    member_count: int
    extracted_size_bound: int
    packages: tuple[ArchivePackage, ...]
    package_digests: tuple[tuple[str, str], ...]


class _HashingCountingReader:
    """Bounded hashing/counting adapter over a compressed byte stream.

    Repair R4-EF-STAGE streaming discipline: every read carries an
    explicit positive size and no read exceeds ``_CHUNK_BYTES`` in normal
    operation. Unbounded ``read(-1)``/``read(None)`` is refused outright
    (the old whole-stream ``b"".join`` buffering path is gone) so a
    regression that tries to hold the whole archive in RAM fails closed
    here instead of exhausting the Acer floor. ``max_read_size`` records
    the largest single read served, letting tests prove chunked hashing.
    """

    def __init__(self, source: BinaryIO, *, expected_size: int) -> None:
        self._source = source
        self._expected_size = expected_size
        self._read_bytes = 0
        self._digest = hashlib.sha256()
        self.max_read_size = 0

    @property
    def read_bytes(self) -> int:
        return self._read_bytes

    def digest_hex(self) -> str:
        return self._digest.hexdigest()

    def readable(self) -> bool:
        return True

    def read(self, size: int = -1) -> bytes:
        if size is None or size < 0:
            raise HardwareSupportArchiveError(
                "hardware-support archive stream refused an unbounded read"
            )
        if size == 0:
            return b""
        if size > self.max_read_size:
            self.max_read_size = size
        try:
            chunk = self._source.read(size)
        except OSError as exc:
            raise HardwareSupportArchiveError(
                "hardware-support archive stream failed"
            ) from exc
        if not chunk:
            return b""
        self._read_bytes += len(chunk)
        if self._read_bytes > self._expected_size:
            raise HardwareSupportArchiveError(
                "hardware-support archive grew during inspection"
            )
        self._digest.update(chunk)
        return chunk


def _zstd_stream(source: BinaryIO):
    try:
        import zstandard
    except ImportError as exc:
        raise HardwareSupportArchiveError(
            "zstd decompression backend is unavailable; refusing support inspection"
        ) from exc
    try:
        return zstandard.ZstdDecompressor().stream_reader(source)
    except Exception as exc:
        raise HardwareSupportArchiveError(
            f"hardware-support archive is not a safe Greia tree: {exc}"
        ) from exc


def _close_stream(stream: object) -> None:
    closer = getattr(stream, "close", None)
    if callable(closer):
        try:
            closer()
        except Exception:
            pass


def _check_expected_facts(expected_size: int, expected_sha256: str | None) -> None:
    if (
        isinstance(expected_size, bool)
        or not isinstance(expected_size, int)
        or not 1 <= expected_size <= MAX_ARCHIVE_COMPRESSED_BYTES
    ):
        raise HardwareSupportArchiveError(
            "hardware-support archive size is outside Greia bounds"
        )
    if expected_sha256 is not None and (
        not isinstance(expected_sha256, str) or not _SHA256_RE.fullmatch(expected_sha256)
    ):
        raise HardwareSupportArchiveError("hardware-support archive digest is invalid")


#: Public alias so runtime wrappers reuse the same bounded
#: hashing/counting reader instead of copying it.
HashingCountingReader = _HashingCountingReader


def finish_streamed_inspection(
    *,
    expected_compressed_bytes: int,
    expected_sha256: str,
    counted_bytes: int,
    counted_digest: str,
    manifest_raw: bytes | None,
    member_sizes: dict[str, int],
    member_digests: dict[str, str],
    seen: set[str],
    uncompressed_bytes: int,
    member_count: int,
) -> HardwareSupportArchiveMetadata:
    """Bind streamed observations to digest-verified metadata.

    Single owner for the post-stream verdict: compressed size/digest
    match, manifest presence/semantics, per-package size/digest match,
    unmanifested-payload refusal and repository-index verification plus
    the deterministic extracted-size bound
    (:func:`extracted_bytes_bound_for_members` recomputed from the exact
    observed file sizes, never a bare byte sum). When the inner manifest
    carries the builder-declared ``extracted_bytes_bound`` field, the
    observed bound must equal it byte-for-byte, otherwise the archive is
    refused as an observed-vs-declared bound mismatch. Both the inspect
    path (discarding bodies) and the extract path (writing bodies to
    disk) call here with identical semantics, so their verdicts agree.
    """
    if counted_bytes != expected_compressed_bytes:
        raise HardwareSupportArchiveError(
            "hardware-support archive size does not match manifest"
        )
    if counted_digest != expected_sha256:
        raise HardwareSupportArchiveError(
            "hardware-support archive digest does not match manifest"
        )
    if manifest_raw is None:
        raise HardwareSupportArchiveError(
            "hardware-support archive carries no manifest.json"
        )
    validated = parse_manifest_bytes(manifest_raw)
    expected = {normalize_archive_name(item.filename) for item in validated.packages}
    for item in validated.packages:
        name = normalize_archive_name(item.filename)
        if name not in seen:
            raise HardwareSupportArchiveError(
                f"hardware-support archive package is missing: {item.package}"
            )
        if member_sizes.get(name) != item.size:
            raise HardwareSupportArchiveError(
                f"hardware-support archive package size changed: {item.package}"
            )
        if member_digests.get(name) != item.sha256:
            raise HardwareSupportArchiveError(
                f"hardware-support archive package digest changed: {item.package}"
            )
    for name in seen:
        if name.rstrip("/") in ("", ".", POOL_DIR):
            continue
        if name in TOP_FILES or name in expected:
            continue
        if name.startswith("pool/") and name.endswith(".deb"):
            raise HardwareSupportArchiveError(
                "hardware-support archive contains unmanifested package payloads"
            )
        raise HardwareSupportArchiveError(
            f"hardware-support archive carries an unexpected member: {name!r}"
        )
    for index_name in ("Packages", "Packages.gz"):
        wanted = validated.repository_indexes[index_name]
        if index_name not in seen:
            raise HardwareSupportArchiveError(
                f"hardware-support repository index is missing: {index_name}"
            )
        if member_sizes.get(index_name) != wanted["size"]:
            raise HardwareSupportArchiveError(
                f"hardware-support repository index changed: {index_name}"
            )
        if member_digests.get(index_name) != wanted["sha256"]:
            raise HardwareSupportArchiveError(
                f"hardware-support repository index changed: {index_name}"
            )
    extracted_bound = extracted_bytes_bound_for_members(
        list(member_sizes.values()),
        member_count=member_count,
    )
    # The streamed uncompressed total also covers trailing decompressed
    # bytes past the tar end-of-archive markers (counted by the pass
    # toward the decompression-bomb cap but never extracted to disk, so
    # correctly excluded from the staging bound above). It must never be
    # smaller than the accounted file bytes; anything else is an internal
    # accounting defect refused here rather than staged.
    if uncompressed_bytes < sum(member_sizes.values()):
        raise HardwareSupportArchiveError(
            "hardware-support archive stream accounting is inconsistent"
        )
    if validated.extracted_bound is not None and (
        validated.extracted_bound != extracted_bound
    ):
        raise HardwareSupportArchiveError(
            "hardware-support archive observed-vs-declared extracted bound mismatch"
        )
    return HardwareSupportArchiveMetadata(
        support_sha256=expected_sha256,
        support_size=expected_compressed_bytes,
        total_bytes=validated.total_bytes,
        total_installed_bytes=validated.total_installed_bytes,
        uncompressed_bytes=uncompressed_bytes,
        member_count=member_count,
        extracted_size_bound=extracted_bound,
        packages=validated.packages,
        package_digests=tuple(sorted(member_digests.items())),
    )


def _drain_and_hash(
    source: BinaryIO, size: int, *, label: str, cap: int = MAX_ARCHIVE_FILE_BYTES
) -> str:
    """Hash exactly ``size`` streamed bytes; return the hex digest."""
    if size < 0 or size > cap:
        raise HardwareSupportArchiveError(
            f"hardware-support archive file is outside Greia bounds: {label!r}"
        )
    digest = hashlib.sha256()
    remaining = size
    while remaining > 0:
        chunk = source.read(min(_CHUNK_BYTES, remaining))
        if not chunk:
            raise HardwareSupportArchiveError(
                f"hardware-support archive member is truncated: {label!r}"
            )
        remaining -= len(chunk)
        digest.update(chunk)
    return digest.hexdigest()


def hash_and_copy_streamed_body(
    source: BinaryIO, dest: BinaryIO, size: int, *, label: str
) -> str:
    """Stream exactly ``size`` bytes from ``source`` to ``dest``; return hex digest.

    Single owner for bounded chunked body streaming shared by the inspect
    discard path (:func:`_drain_and_hash`), the standalone extract path
    (:func:`extract_compressed_stream`) and the runtime staging path
    (``candidate_support._extract_one`` with an already-open body). Every
    read carries an explicit positive bound (``min(_CHUNK_BYTES,
    remaining)``); truncation refuses fail-closed. Callers own file
    open/close, directory ownership and permission bits.
    """
    if size < 0 or size > MAX_ARCHIVE_FILE_BYTES:
        raise HardwareSupportArchiveError(
            f"hardware-support archive file is outside Greia bounds: {label!r}"
        )
    digest = hashlib.sha256()
    remaining = size
    while remaining > 0:
        chunk = source.read(min(_CHUNK_BYTES, remaining))
        if not chunk:
            raise HardwareSupportArchiveError(
                f"hardware-support archive member is truncated: {label!r}"
            )
        remaining -= len(chunk)
        digest.update(chunk)
        dest.write(chunk)
    return digest.hexdigest()


def inspect_compressed_stream(
    source: BinaryIO,
    *,
    expected_compressed_bytes: int,
    expected_sha256: str,
) -> HardwareSupportArchiveMetadata:
    """Inspect one compressed archive stream (no filesystem writes).

    ``source`` yields compressed ``hardware-support.tar.zst`` bytes. Every
    byte is hashed/counted against the expected facts while the tar shape,
    manifest semantics, per-member sizes/digests and repository indexes
    are validated in bounded streaming chunks.
    """
    _check_expected_facts(expected_compressed_bytes, expected_sha256)
    counted = _HashingCountingReader(source, expected_size=expected_compressed_bytes)
    reader = _zstd_stream(counted)
    manifest_raw: bytes | None = None
    member_sizes: dict[str, int] = {}
    member_digests: dict[str, str] = {}
    seen: set[str] = set()
    uncompressed_bytes = 0
    member_count = 0
    try:
        try:
            with tarfile.open(fileobj=reader, mode="r|") as tar:
                for member in tar:
                    member_count += 1
                    if member_count > MAX_ARCHIVE_MEMBERS:
                        raise HardwareSupportArchiveError(
                            "hardware-support archive member count is outside Greia bounds"
                        )
                    normalized, kind = validate_member_header(member)
                    if normalized in seen:
                        raise HardwareSupportArchiveError(
                            f"hardware-support archive carries a duplicate member: {normalized!r}"
                        )
                    seen.add(normalized)
                    if kind == "dir":
                        continue
                    uncompressed_bytes += member.size
                    if uncompressed_bytes > MAX_ARCHIVE_UNCOMPRESSED_BYTES:
                        raise HardwareSupportArchiveError(
                            "hardware-support archive decompresses beyond Greia bounds"
                        )
                    body = tar.extractfile(member)
                    if body is None:
                        raise HardwareSupportArchiveError(
                            f"hardware-support archive member is unreadable: {normalized!r}"
                        )
                    with body:
                        if normalized == "manifest.json":
                            pieces: list[bytes] = []
                            remaining = member.size
                            while remaining > 0:
                                chunk = body.read(min(_CHUNK_BYTES, remaining))
                                if not chunk:
                                    raise HardwareSupportArchiveError(
                                        "hardware-support archive member is truncated: "
                                        f"{normalized!r}"
                                    )
                                remaining -= len(chunk)
                                pieces.append(chunk)
                            manifest_raw = b"".join(pieces)
                            member_sizes[normalized] = member.size
                            member_digests[normalized] = hashlib.sha256(
                                manifest_raw
                            ).hexdigest()
                        else:
                            digest = _drain_and_hash(body, member.size, label=normalized)
                            member_sizes[normalized] = member.size
                            member_digests[normalized] = digest
                drained = reader.read(_CHUNK_BYTES)
                while drained:
                    uncompressed_bytes += len(drained)
                    if uncompressed_bytes > MAX_ARCHIVE_UNCOMPRESSED_BYTES:
                        raise HardwareSupportArchiveError(
                            "hardware-support archive decompresses beyond Greia bounds"
                        )
                    drained = reader.read(_CHUNK_BYTES)
        except HardwareSupportArchiveError:
            raise
        except Exception as exc:
            raise HardwareSupportArchiveError(
                f"hardware-support archive is not a safe Greia tree: {exc}"
            ) from exc
    finally:
        _close_stream(reader)
    return finish_streamed_inspection(
        expected_compressed_bytes=expected_compressed_bytes,
        expected_sha256=expected_sha256,
        counted_bytes=counted.read_bytes,
        counted_digest=counted.digest_hex(),
        manifest_raw=manifest_raw,
        member_sizes=member_sizes,
        member_digests=member_digests,
        seen=seen,
        uncompressed_bytes=uncompressed_bytes,
        member_count=member_count,
    )


def inspect_archive_file(
    path: Path,
    *,
    expected_compressed_bytes: int | None = None,
    expected_sha256: str | None = None,
) -> HardwareSupportArchiveMetadata:
    """Inspect one standalone ``hardware-support.tar.zst`` file (streaming).

    When the expected facts are omitted they are derived from the file
    itself (size + streamed SHA-256); when supplied they are enforced.
    """
    location = Path(path)
    try:
        file_stat = location.lstat()
    except OSError as exc:
        raise HardwareSupportArchiveError(
            f"hardware-support archive is unreadable: {exc}"
        ) from exc
    if not _stat.S_ISREG(file_stat.st_mode):
        raise HardwareSupportArchiveError(
            "hardware-support archive is not a regular file"
        )
    archive_size = file_stat.st_size
    if expected_compressed_bytes is not None:
        _check_expected_facts(expected_compressed_bytes, expected_sha256 or "ab" * 32)
        if archive_size != expected_compressed_bytes:
            raise HardwareSupportArchiveError(
                "hardware-support archive size does not match manifest"
            )
    if not 1 <= archive_size <= MAX_ARCHIVE_COMPRESSED_BYTES:
        raise HardwareSupportArchiveError(
            "hardware-support archive size is outside Greia bounds"
        )
    try:
        with location.open("rb") as handle:
            magic = handle.read(4)
    except OSError as exc:
        raise HardwareSupportArchiveError(
            f"hardware-support archive is unreadable: {exc}"
        ) from exc
    if magic != ARCHIVE_ZSTD_MAGIC:
        raise HardwareSupportArchiveError("hardware-support archive is not zstd-framed")
    if expected_sha256 is None:
        digest = hashlib.sha256()
        try:
            with location.open("rb") as handle:
                for chunk in iter(lambda: handle.read(_CHUNK_BYTES), b""):
                    digest.update(chunk)
        except OSError as exc:
            raise HardwareSupportArchiveError(
                f"hardware-support archive is unreadable: {exc}"
            ) from exc
        expected_sha256 = digest.hexdigest()
        expected_compressed_bytes = archive_size
    assert expected_sha256 is not None and expected_compressed_bytes is not None
    try:
        with location.open("rb") as handle:
            return inspect_compressed_stream(
                handle,
                expected_compressed_bytes=expected_compressed_bytes,
                expected_sha256=expected_sha256,
            )
    except HardwareSupportArchiveError:
        raise
    except Exception as exc:
        raise HardwareSupportArchiveError(
            f"hardware-support archive inspection refused: {exc}"
        ) from exc


def extract_compressed_stream(
    source: BinaryIO,
    *,
    expected_compressed_bytes: int,
    expected_sha256: str,
    destination: Path,
) -> HardwareSupportArchiveMetadata:
    """Extract one compressed stream into ``destination`` (single pass).

    Reuses :func:`validate_member_header` and the same manifest/member
    semantics as :func:`inspect_compressed_stream`: headers, traversal,
    links/specials, allowed tree, per-file/total/member-count bounds,
    digests, sizes, indexes and installed accounting share one verdict.
    Bodies stream straight to disk in bounded chunks.
    """
    _check_expected_facts(expected_compressed_bytes, expected_sha256)
    target_dir = Path(destination)
    counted = _HashingCountingReader(source, expected_size=expected_compressed_bytes)
    reader = _zstd_stream(counted)
    member_sizes: dict[str, int] = {}
    member_digests: dict[str, str] = {}
    seen: set[str] = set()
    uncompressed_bytes = 0
    member_count = 0
    try:
        try:
            with tarfile.open(fileobj=reader, mode="r|") as tar:
                for member in tar:
                    member_count += 1
                    if member_count > MAX_ARCHIVE_MEMBERS:
                        raise HardwareSupportArchiveError(
                            "hardware-support archive member count is outside Greia bounds"
                        )
                    normalized, kind = validate_member_header(member)
                    if normalized in seen:
                        raise HardwareSupportArchiveError(
                            f"hardware-support archive carries a duplicate member: {normalized!r}"
                        )
                    seen.add(normalized)
                    if kind == "dir":
                        continue
                    uncompressed_bytes += member.size
                    if uncompressed_bytes > MAX_ARCHIVE_UNCOMPRESSED_BYTES:
                        raise HardwareSupportArchiveError(
                            "hardware-support archive decompresses beyond Greia bounds"
                        )
                    body = tar.extractfile(member)
                    if body is None:
                        raise HardwareSupportArchiveError(
                            f"hardware-support archive member is unreadable: {normalized!r}"
                        )
                    target = target_dir / normalized
                    if target.is_symlink():
                        raise HardwareSupportArchiveError(
                            f"hardware-support archive target is unsafe: {normalized!r}"
                        )
                    try:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        os.chmod(target.parent, 0o700)
                    except OSError as exc:
                        raise HardwareSupportArchiveError(
                            f"hardware-support archive directory is not ownable: {normalized!r}"
                        ) from exc
                    digest = ""
                    try:
                        with body, target.open("wb") as handle:
                            digest = hash_and_copy_streamed_body(
                                body, handle, member.size, label=normalized
                            )
                        os.chmod(target, 0o600)
                    except HardwareSupportArchiveError:
                        raise
                    except OSError as exc:
                        raise HardwareSupportArchiveError(
                            f"hardware-support archive extraction failed: {normalized!r}"
                        ) from exc
                    member_sizes[normalized] = member.size
                    member_digests[normalized] = digest
                drained = reader.read(_CHUNK_BYTES)
                while drained:
                    uncompressed_bytes += len(drained)
                    if uncompressed_bytes > MAX_ARCHIVE_UNCOMPRESSED_BYTES:
                        raise HardwareSupportArchiveError(
                            "hardware-support archive decompresses beyond Greia bounds"
                        )
                    drained = reader.read(_CHUNK_BYTES)
        except HardwareSupportArchiveError:
            raise
        except Exception as exc:
            raise HardwareSupportArchiveError(
                f"hardware-support archive is not a safe Greia tree: {exc}"
            ) from exc
    finally:
        _close_stream(reader)
    manifest_path = target_dir / "manifest.json"
    try:
        manifest_raw = manifest_path.read_bytes()
    except OSError as exc:
        raise HardwareSupportArchiveError(
            "hardware-support archive carries no manifest.json"
        ) from exc
    if len(manifest_raw) > MAX_ARCHIVE_MANIFEST_BYTES:
        raise HardwareSupportArchiveError(
            "hardware-support archive manifest size is outside Greia bounds"
        )
    if member_sizes.get("manifest.json") != len(manifest_raw):
        raise HardwareSupportArchiveError(
            "hardware-support archive manifest size does not match stream"
        )
    return finish_streamed_inspection(
        expected_compressed_bytes=expected_compressed_bytes,
        expected_sha256=expected_sha256,
        counted_bytes=counted.read_bytes,
        counted_digest=counted.digest_hex(),
        manifest_raw=manifest_raw,
        member_sizes=member_sizes,
        member_digests=member_digests,
        seen=seen,
        uncompressed_bytes=uncompressed_bytes,
        member_count=member_count,
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(_CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _open_reader(path: Path) -> tuple[BinaryIO, int]:
    """Open a compressed file for streaming; return (handle, size)."""
    location = Path(path)
    size = location.stat().st_size
    return location.open("rb"), size
