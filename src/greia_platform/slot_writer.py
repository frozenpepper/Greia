"""Common streamed slot writer, verified base-slot capability and finalizer seam.

L7-SLOTS (R0/R1 source scope): files and fakes only. No partition, mount,
filesystem, boot or physical-slot writes live here; production block/mount
backends are injected later through the narrow protocols below
(``SlotStorage``, ``SlotFilesystem``, ``SlotPackageInstaller``).

Staging order (strict, ADR 0036 §4 v3):

.. code-block:: text

    stream zstd decompression of payload.ext4.zst -> write raw bytes
    -> flush -> read back the exact uncompressed range
    -> require the uncompressed raw byte count -> only then bind
    the destination role's stable filesystem UUID, expand, and run
    the finalizer.

The compressed member digest/size are bundle-transport facts verified at
inspection (``inspect_update_bundle``); the writer proves the uncompressed
raw byte count against the manifest's ``payload_uncompressed_bytes`` with
no full uncompressed temp file (bounded streaming chunks only).

Both the updater (``greia_platform.system_updates``) and the installer
(``greia_installer``) import and call this same implementation; the installer
adapts its already-verified hardware logic (``TargetHardwareSupportInstaller``)
to the shared ``SlotPackageInstaller`` protocol instead of copying it (see
``greia_installer.slots``).

Destination roles resolve only from trusted layout state
(``InstalledLayoutRecord``), never from Parent/UI paths. ``A`` maps to the
``system-a`` partition role and ``B`` to ``system-b``; the destination must be
neither the active nor the accepted slot. A/B filesystem UUIDs are
role-stable: finalization restores the destination role's recorded UUID onto
the staged filesystem (overwriting the release-builder template UUID), so
role identities stay distinct and are never cloned from the template, and
the layout record stays authoritative across updates with no rewrite path.

Capacity proof (checked at write time and re-checked at finalization)::

    max(uncompressed bytes, manifest minimum) + support installed-size bound
        + initramfs/boot growth bound + metadata/reserve <= slot capacity
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import uuid
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO, Mapping, Protocol

from . import session04_serial_diag
from .hardware_enablement import (
    HardwareSupportPlan,
    SupportDisposition,
    SupportKind,
)
from .fstab import (
    FSTAB_FILE_MODE,
    FSTAB_REL_PATH,
    PERSIST_BOOT_MOUNTPOINT,
    render_fstab,
)
from .persistent_layout import (
    InstalledLayoutRecord,
    PersistentLayoutError,
    present_canonical_mount_targets,
)

try:
    from .system_updates import UpdateManifest
except ImportError:  # pragma: no cover - system_updates is always present
    UpdateManifest = None  # type: ignore[assignment]


class SlotWriteError(RuntimeError):
    """Base-slot streaming, readback or destination proof failed."""


class SlotFinalizeError(RuntimeError):
    """Slot binding, expansion, support install or receipt failed."""


#: Finalizer contract version bound into every finalization receipt.
FINALIZER_VERSION = "slot-finalizer-v1"

#: Bounded streaming buffer: payload bytes are never held whole in memory.
SLOT_WRITE_CHUNK_BYTES = 64 * 1024

#: Upper bound for initramfs/boot-artifact growth during finalization.
#: R0 source bound; tightened by on-device measurement later, never loosened
#: by guessing.
FINALIZATION_GROWTH_BYTES = 64 * 1024 * 1024

#: Upper bound for slot-local metadata (receipts, identity, profile config).
SLOT_METADATA_RESERVE_BYTES = 16 * 1024 * 1024

#: Receipt schema version.
FINALIZATION_RECEIPT_SCHEMA_VERSION = 1

#: Slot-local receipt path inside the finalized slot filesystem.
RECEIPT_REL_PATH = "etc/greia-os/finalization-receipt.json"

#: Slot-local release/slot identity path inside the finalized slot.
RELEASE_IDENTITY_REL_PATH = "etc/greia-os/release-identity.json"

#: Slot-local profile-configuration path inside the finalized slot.
SLOT_PROFILE_REL_PATH = "etc/greia-os/slot-profile.json"

#: Candidate-local generic/host artifact manifest inside the finalized slot.
FINALIZED_GENERIC_REL_PATH = "boot/finalized-generic.json"

#: Payload-carried generic boot files and the adapter-owned slot aliases the
#: installed GRUB A/B entries boot.  The finalizer publishes the aliases so a
#: finalized slot never references a kernel/initramfs name that does not exist.
SLOT_GENERIC_KERNEL_REL_PATH = "boot/vmlinuz-generic"
SLOT_GENERIC_INITRAMFS_REL_PATH = "boot/initrd-generic"
SLOT_KERNEL_REL_PATH = "boot/vmlinuz-greia"
SLOT_INITRAMFS_REL_PATH = "boot/initramfs-greia.img"

#: Files the finalizer must prove present before writing the receipt.
#: ``etc/fstab`` carries the single-owner canonical policy specialized to
#: the destination role UUID (same renderer as fresh target assembly).
REQUIRED_FINALIZED_FILES = (
    FINALIZED_GENERIC_REL_PATH,
    SLOT_KERNEL_REL_PATH,
    SLOT_INITRAMFS_REL_PATH,
    RELEASE_IDENTITY_REL_PATH,
    SLOT_PROFILE_REL_PATH,
    FSTAB_REL_PATH,
)

#: Bounded slot-completeness smoke: directories proving a staged slot carries
#: real Greia userspace (not a payload-only skeleton). Checked with a fixed
#: list of ``is_dir()`` probes only — no traversal, no whole-image hashing.
#: ``bin`` is accepted as a directory or a usrmerge symlink-to-directory
#: (``is_dir()`` follows symlinks). Deliberately free of build-only
#: knowledge (no ``boot/vmlinuz-generic``): the build-time producer (T04)
#: calls this identical implementation on a staging dir, and the shared
#: :class:`SlotFinalizer` calls it on the mounted slot before boot assets
#: are accepted. Usable from a plain directory tree (no privileged mounts).
REQUIRED_SLOT_COMPLETENESS_DIRS = (
    "usr",
    "bin",
    "etc",
    "var",
    "opt/greia-os",
    "etc/greia-os",
)

#: Bounded slot-completeness smoke: regular files proving the finalizer's
#: ``chroot <slot>`` APT needs. Each must be a real regular file
#: (a symlink leaf is invalid) — ``is_file()`` plus an ``is_symlink()``
#: refusal, no traversal, no hashing. ``usr/bin/env`` is required because
#: the hardware-support install runs under ``/usr/bin/env``.
REQUIRED_SLOT_COMPLETENESS_FILES = (
    "usr/bin/apt-get",
    "usr/bin/dpkg",
    "usr/bin/env",
)

#: Documented required-path set for the slot-completeness smoke, in
#: check order: directories first, then command files.
REQUIRED_SLOT_COMPLETENESS_PATHS = (
    *REQUIRED_SLOT_COMPLETENESS_DIRS,
    *REQUIRED_SLOT_COMPLETENESS_FILES,
)


def slot_completeness_missing(slot_root: Path) -> tuple[str, ...]:
    """Return the missing/invalid completeness paths under ``slot_root``.

    Bounded to ``len(REQUIRED_SLOT_COMPLETENESS_PATHS)`` stat probes.
    An empty tuple means the slot carries the required Greia userspace
    including usable ``apt-get``/``dpkg`` presence. Directory entries
    must satisfy ``is_dir()``; file entries must be non-symlink regular
    files. Raises :class:`SlotFinalizeError` only when ``slot_root``
    itself is not a usable directory probe point (fail closed).
    """
    if not isinstance(slot_root, Path):
        raise SlotFinalizeError("slot completeness probe requires a path")
    try:
        if not slot_root.is_dir():
            raise SlotFinalizeError("slot completeness probe requires a slot directory")
    except SlotFinalizeError:
        raise
    except Exception as exc:
        raise SlotFinalizeError(
            f"slot completeness probe failed: {exc}"
        ) from exc
    missing: list[str] = []
    for rel_path in REQUIRED_SLOT_COMPLETENESS_DIRS:
        try:
            if not (slot_root / rel_path).is_dir():
                missing.append(rel_path)
        except Exception:
            missing.append(rel_path)
    for rel_path in REQUIRED_SLOT_COMPLETENESS_FILES:
        try:
            candidate = slot_root / rel_path
            if candidate.is_symlink() or not candidate.is_file():
                missing.append(rel_path)
        except Exception:
            missing.append(rel_path)
    return tuple(missing)


def check_slot_completeness(slot_root: Path) -> None:
    """Fail closed when ``slot_root`` lacks required Greia userspace.

    Shared implementation for the build-time staging check (T04) and the
    runtime finalization smoke. Raises :class:`SlotFinalizeError` naming
    every missing/invalid path; no boot/QEMU step is involved.
    """
    missing = slot_completeness_missing(slot_root)
    if missing:
        raise SlotFinalizeError(
            "slot completeness smoke failed: missing " + ", ".join(missing)
        )

_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_SLOT_ROLE_RE = re.compile(r"^system-[ab]$")
_RELEASE_FACT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_MAX_SLOT_CONFIG_ENTRIES = 32
_MAX_SLOT_CONFIG_VALUE_BYTES = 256

#: Bounds for the unsigned-v3 release-identity facts the finalizer may state.
#: They mirror the ``load_installed_release_identity`` acceptance bounds in
#: ``greia_platform.system_updates`` so every written document reloads there.
_MAX_RELEASE_ARCHITECTURE = 32
_MAX_RELEASE_PLATFORM_FAMILY = 64
_MAX_RELEASE_PROFILE = 96
_MAX_RELEASE_VERSION = 64

#: Capability tokens issued by :class:`SlotWriter.write`, keyed by token.
#: :class:`SlotFinalizer` consumes the token for exactly one finalization,
#: so a forged, guessed or stale ``VerifiedBaseSlotWrite`` can never enter
#: (or re-enter) binding/finalization. Explicitly bounded (one entry per
#: staged slot in practice); evicting the oldest token only invalidates a
#: stale unfinalized write fail-closed.
_ISSUED_WRITE_TOKENS: deque[str] = deque(maxlen=1024)


def _require_hex64(value: object, *, field_name: str) -> str:
    if not isinstance(value, str) or not _HEX64_RE.fullmatch(value):
        raise SlotWriteError(f"{field_name} must be lowercase SHA-256 hex")
    return value


def _require_count(value: object, *, field_name: str, minimum: int = 1) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise SlotWriteError(f"{field_name} is outside Greia bounds")
    return value


def _require_canonical_uuid(value: object, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise SlotWriteError(f"{field_name} must be text")
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError) as exc:
        raise SlotWriteError(f"{field_name} is not a valid UUID") from exc
    if str(parsed) != value.lower():
        raise SlotWriteError(f"{field_name} must be canonical lowercase UUID text")
    return str(parsed)


def _canonical_bytes(value: Mapping[str, object]) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


# ---------------------------------------------------------------------------
# Verified release member (previously verified trust boundary input)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class VerifiedReleaseMember:
    """One previously verified v3 release payload (ADR 0036 §3, no provenance).

    Construct only from an ``InspectedUpdateBundle`` *after* structure,
    integrity and compatibility verification (``SystemUpdateService``).
    ``payload_sha256``/``payload_size`` are the compressed transport facts
    (already digest-verified at inspection); the writer proves the
    decompressed raw byte count against ``payload_uncompressed_bytes``.
    There is no signer, key id or anti-rollback sequence. ``hardware_*``
    are None together when the optional member is absent.
    """

    release_id: str
    payload_sha256: str
    payload_size: int
    payload_uncompressed_bytes: int
    minimum_slot_bytes: int
    hardware_support_sha256: str | None
    hardware_support_size: int | None

    def __post_init__(self) -> None:
        if not self.release_id or len(self.release_id) > 96:
            raise SlotWriteError("release_id is outside Greia bounds")
        _require_hex64(self.payload_sha256, field_name="payload_sha256")
        _require_count(self.payload_size, field_name="payload_size")
        _require_count(
            self.payload_uncompressed_bytes,
            field_name="payload_uncompressed_bytes",
        )
        _require_count(
            self.minimum_slot_bytes, field_name="minimum_slot_bytes"
        )
        if self.minimum_slot_bytes < self.payload_uncompressed_bytes:
            raise SlotWriteError("minimum_slot_bytes must cover the uncompressed payload")
        hw_sha = self.hardware_support_sha256
        hw_size = self.hardware_support_size
        if (hw_sha is None) != (hw_size is None):
            raise SlotWriteError(
                "hardware-support sha256/size must be present together or absent together"
            )
        if hw_sha is not None and hw_size is not None:
            _require_hex64(hw_sha, field_name="hardware_support_sha256")
            _require_count(hw_size, field_name="hardware_support_size")

    @classmethod
    def from_manifest(cls, manifest: "UpdateManifest") -> "VerifiedReleaseMember":
        """Bind the v3 manifest facts after the caller verified compatibility."""
        return cls(
            release_id=manifest.release_id,
            payload_sha256=manifest.payload_sha256,
            payload_size=manifest.payload_size,
            payload_uncompressed_bytes=manifest.payload_uncompressed_bytes,
            minimum_slot_bytes=manifest.payload_minimum_slot_bytes,
            hardware_support_sha256=manifest.hardware_support_sha256,
            hardware_support_size=manifest.hardware_support_size,
        )


# ---------------------------------------------------------------------------
# Layout-resolved destination role
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DestinationSlot:
    """A layout-resolved destination role: semantic slot plus capacity proof.

    Resolved only from the trusted ``InstalledLayoutRecord``. ``semantic_slot``
    ``"A"``/``"B"`` maps to partition role ``"system-a"``/``"system-b"``.
    ``role_filesystem_uuid`` is the role's stable filesystem UUID recorded by
    layout authority: finalization restores exactly this UUID onto the staged
    filesystem (it is never minted fresh and never cloned from the template).
    """

    semantic_slot: str
    role: str
    slot_capacity_bytes: int
    active_slot: str | None
    accepted_slot: str | None
    layout_id: str
    role_filesystem_uuid: str
    other_role_filesystem_uuid: str

    def __post_init__(self) -> None:
        if self.semantic_slot not in ("A", "B"):
            raise SlotWriteError("destination semantic slot must be A or B")
        if self.role != f"system-{self.semantic_slot.lower()}":
            raise SlotWriteError("destination role does not match the semantic slot")
        _require_count(
            self.slot_capacity_bytes, field_name="slot_capacity_bytes"
        )
        _require_canonical_uuid(
            self.role_filesystem_uuid, field_name="role filesystem UUID"
        )
        _require_canonical_uuid(
            self.other_role_filesystem_uuid, field_name="other role filesystem UUID"
        )
        if (
            self.role_filesystem_uuid == self.other_role_filesystem_uuid
        ):
            raise SlotWriteError("A/B role filesystem UUIDs must be distinct")

    @classmethod
    def resolve_from_layout(
        cls, record: InstalledLayoutRecord, semantic_slot: str
    ) -> "DestinationSlot":
        """Prove the requested semantic slot is writable and not live.

        Fails closed when the layout is single-root, the semantic slot is
        unknown, or the destination is the active or accepted slot.
        """
        if semantic_slot not in ("A", "B"):
            raise SlotWriteError("destination semantic slot must be A or B")
        if record.system_b is None:
            raise SlotWriteError("single-root layouts carry no writable A/B slot")
        if semantic_slot == record.boot_control.active_slot:
            raise SlotWriteError("refusing to stage into the active slot")
        if semantic_slot == record.accepted_slot:
            raise SlotWriteError("refusing to stage into the accepted slot")
        if semantic_slot == "A":
            own = record.system_a
            other = record.system_b
        else:
            if record.system_b is None:  # pragma: no cover - guarded above
                raise SlotWriteError("A/B layout requires system_b")
            own = record.system_b
            other = record.system_a
        return cls(
            semantic_slot=semantic_slot,
            role=f"system-{semantic_slot.lower()}",
            slot_capacity_bytes=record.slot_bytes,
            active_slot=record.boot_control.active_slot,
            accepted_slot=record.accepted_slot,
            layout_id=record.layout_id,
            role_filesystem_uuid=own.filesystem_uuid,
            other_role_filesystem_uuid=other.filesystem_uuid,
        )


# ---------------------------------------------------------------------------
# Storage / filesystem / package-installer seams (loopback files and fakes)
# ---------------------------------------------------------------------------


class SlotStorage(Protocol):
    """Bounded random-access byte store for one destination slot (R0: files)."""

    @property
    def capacity_bytes(self) -> int: ...

    def write_at(self, offset: int, data: bytes) -> None: ...

    def read_at(self, offset: int, length: int) -> bytes: ...

    def flush(self) -> None: ...


class LoopbackSlotFile:
    """File-backed slot store: the R0/R1 loopback stand-in for a partition.

    The file must already exist at exactly ``capacity_bytes`` (sparse files
    created with truncate are fine). Offsets are bounds-checked; no shell,
    no ``dd`` arguments, no device paths cross this API.
    """

    def __init__(self, path: Path, capacity_bytes: int) -> None:
        location = Path(path)
        if location.is_symlink() or not location.is_file():
            raise SlotWriteError("slot store must be a regular file")
        _require_count(capacity_bytes, field_name="slot capacity")
        if location.stat().st_size != capacity_bytes:
            raise SlotWriteError("slot store size does not match the slot capacity")
        self._path = location
        self._capacity = capacity_bytes
        self._handle = location.open("r+b")
        self._closed = False

    @classmethod
    def create(cls, path: Path, capacity_bytes: int) -> "LoopbackSlotFile":
        """Create a sparse pre-sized slot file, failing if it exists."""
        location = Path(path)
        _require_count(capacity_bytes, field_name="slot capacity")
        if location.exists() or location.is_symlink():
            raise SlotWriteError("slot store output already exists")
        location.parent.mkdir(parents=True, exist_ok=True)
        with location.open("wb") as handle:
            handle.truncate(capacity_bytes)
        os.chmod(location, 0o600)
        return cls(location, capacity_bytes)

    @property
    def capacity_bytes(self) -> int:
        return self._capacity

    def _require_open(self) -> None:
        if self._closed:
            raise SlotWriteError("slot store is closed")

    def write_at(self, offset: int, data: bytes) -> None:
        self._require_open()
        if (
            isinstance(offset, bool)
            or not isinstance(offset, int)
            or offset < 0
            or offset + len(data) > self._capacity
        ):
            raise SlotWriteError("slot store write is outside the slot range")
        if not data:
            raise SlotWriteError("slot store write must carry bytes")
        self._handle.seek(offset)
        self._handle.write(data)

    def read_at(self, offset: int, length: int) -> bytes:
        self._require_open()
        if (
            isinstance(offset, bool)
            or not isinstance(offset, int)
            or isinstance(length, bool)
            or not isinstance(length, int)
            or offset < 0
            or length <= 0
            or offset + length > self._capacity
        ):
            raise SlotWriteError("slot store read is outside the slot range")
        self._handle.seek(offset)
        data = self._handle.read(length)
        if len(data) != length:
            raise SlotWriteError("slot store read is short")
        return data

    def flush(self) -> None:
        self._require_open()
        self._handle.flush()
        os.fsync(self._handle.fileno())

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            self._handle.close()

    def __enter__(self) -> "LoopbackSlotFile":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


class SlotFilesystem(Protocol):
    """Bounded mutation seam for one destination slot (R0: fakes).

    Implementations own only the destination slot: binding its filesystem
    UUID, expanding it, mounting it, proving slot completeness
    (``check_completeness`` via :func:`check_slot_completeness`), writing
    slot-local files, checking health, then unmounting and syncing. The
    active/accepted slot is never addressable through this seam.
    ``check_completeness`` and ``check_health`` are distinct gates of the
    same finalization framework (A23): completeness proves real Greia
    userspace including ``apt-get``/``dpkg`` presence, health re-proves
    the filesystem UUID binding.
    """

    def bind_filesystem_uuid(self, filesystem_uuid: str) -> None: ...

    def expand_to_capacity(self) -> None: ...

    def mount(self) -> Path: ...

    def unmount(self) -> None: ...

    def sync(self) -> None: ...

    def write_file(self, relative_path: str, data: bytes) -> None: ...

    def link_file(
        self, source_relative_path: str, target_relative_path: str
    ) -> None: ...

    def missing_files(self, required: tuple[str, ...]) -> tuple[str, ...]: ...

    def check_completeness(self) -> None: ...

    def check_health(self) -> None: ...


@dataclass(frozen=True, slots=True)
class InstalledPackage:
    """One support package installed from the release-bound support set."""

    name: str
    version: str
    architecture: str
    sha256: str
    kind: str

    def __post_init__(self) -> None:
        if self.kind not in ("firmware", "microcode"):
            raise SlotFinalizeError("installed package kind must be firmware/microcode")
        _require_hex64(self.sha256, field_name="installed package digest")
        if not self.name or not self.version or not self.architecture:
            raise SlotFinalizeError("installed package identity is incomplete")


class SlotPackageInstaller(Protocol):
    """Install approved firmware/microcode into the mounted destination slot."""

    def install(
        self,
        firmware: tuple[str, ...],
        microcode: tuple[str, ...],
    ) -> tuple[InstalledPackage, ...]: ...


# ---------------------------------------------------------------------------
# Verified base-slot write capability
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class VerifiedBaseSlotWrite:
    """Capability proving a streamed v3 payload passed readback verification.

    Only :class:`SlotWriter.write` issues registered instances, and each
    instance is single-use: :class:`SlotFinalizer` consumes the issuance
    token for exactly one finalization. A stale write can therefore never
    replay against another role (or the same one). The capability carries
    no byte content, only the proven facts: the decompressed raw byte
    count equals the manifest's uncompressed bytes and the readback hash
    matches the streamed hash (write integrity). ``slot_digest`` is the
    uncompressed image hash bound into the receipt/boot artifacts; it is
    not compared to the compressed transport digest.
    """

    member: VerifiedReleaseMember
    destination: DestinationSlot
    bytes_written: int
    slot_digest: str
    write_token: str = field(compare=False)

    def __post_init__(self) -> None:
        _require_hex64(self.slot_digest, field_name="slot digest")
        if self.bytes_written != self.member.payload_uncompressed_bytes:
            raise SlotWriteError(
                "written byte count does not match the uncompressed payload bytes"
            )
        if not self.write_token:
            raise SlotWriteError("base-slot write carries no issuance token")


# ---------------------------------------------------------------------------
# Streaming zstd decompression (ADR 0036 §4, no uncompressed temp file)
# ---------------------------------------------------------------------------


def open_zstd_decompressed_stream(source: BinaryIO) -> BinaryIO:
    """Wrap a compressed ``payload.ext4.zst`` stream as a decompressed reader.

    Bounded streaming only: bytes are decompressed on ``read()`` with no
    full uncompressed temp file and no whole-payload RAM allocation. The
    caller keeps ``source`` open until the returned reader is closed; closing
    the reader does not close ``source`` (the ZIP archive lifetime stays with
    the caller). Corrupt frames and a missing zstd backend fail closed via
    :class:`SlotWriteError`.
    """
    if not hasattr(source, "read"):
        raise SlotWriteError("compressed payload source must be a binary stream")
    try:
        import zstandard
    except ImportError as exc:
        raise SlotWriteError(
            "zstd decompression backend is unavailable; refusing staging"
        ) from exc
    try:
        reader = zstandard.ZstdDecompressor().stream_reader(source)
    except Exception as exc:
        raise SlotWriteError(f"zstd decompression refused: {exc}") from exc
    return reader  # type: ignore[no-any-return]


def _read_exact(stream: BinaryIO, size: int) -> bytes:
    """Read exactly ``size`` decompressed bytes or fail closed (bounded)."""
    if size == 0:
        return b""
    try:
        data = stream.read(size)
    except Exception as exc:
        raise SlotWriteError(f"payload decompression failed: {exc}") from exc
    if data is None:
        return b""
    if not isinstance(data, (bytes, bytearray)):
        raise SlotWriteError("decompressed payload stream must yield bytes")
    return bytes(data)


def _consume_write_token(write: VerifiedBaseSlotWrite) -> None:
    """Consume a verified-write capability for exactly one finalization.

    Raises :class:`SlotFinalizeError` when the token is unknown, forged or
    already consumed. The caller invokes this only after every validation
    gate and before the first destination mutation, so a refusal — for any
    reason — always leaves the destination seam untouched and a stale write
    can never replay.
    """
    try:
        _ISSUED_WRITE_TOKENS.remove(write.write_token)
    except ValueError as exc:
        raise SlotFinalizeError(
            "base-slot write is not a registered verified write; "
            "refusing finalization"
        ) from exc


def _required_slot_bytes(
    *,
    base_bytes: int,
    minimum_slot_bytes: int,
    support_installed_bytes: int,
    growth_bytes: int,
    metadata_reserve_bytes: int,
) -> int:
    """Capacity a destination must prove: base + support + growth + reserve."""
    _require_count(
        support_installed_bytes,
        field_name="support installed-size bound",
        minimum=0,
    )
    return (
        max(base_bytes, minimum_slot_bytes)
        + support_installed_bytes
        + growth_bytes
        + metadata_reserve_bytes
    )


# ---------------------------------------------------------------------------
# Common streamed SlotWriter
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SlotWriter:
    """Stream a verified v3 release payload into a destination slot store.

    Public API takes only typed values: the previously verified release
    member, the layout-resolved destination role, a binary **decompressed**
    source stream (wrap the ``payload.ext4.zst`` ZIP member with
    :func:`open_zstd_decompressed_stream`), the destination store, and the
    release-bound support installed-size bound. No shell strings, arbitrary
    paths, or ``dd`` arguments cross this API. The writer proves the
    uncompressed raw byte count, fsyncs, reads back the exact uncompressed
    range and requires stream/readback hash agreement.
    """

    chunk_bytes: int = SLOT_WRITE_CHUNK_BYTES
    growth_bytes: int = FINALIZATION_GROWTH_BYTES
    metadata_reserve_bytes: int = SLOT_METADATA_RESERVE_BYTES

    def __post_init__(self) -> None:
        if (
            isinstance(self.chunk_bytes, bool)
            or not isinstance(self.chunk_bytes, int)
            or not 4096 <= self.chunk_bytes <= 4 * 1024 * 1024
        ):
            raise SlotWriteError("writer chunk size is outside Greia bounds")

    def required_slot_bytes(
        self, member: VerifiedReleaseMember, support_installed_bytes: int
    ) -> int:
        """Capacity the destination must prove: base + support + growth + reserve."""
        return _required_slot_bytes(
            base_bytes=member.payload_uncompressed_bytes,
            minimum_slot_bytes=member.minimum_slot_bytes,
            support_installed_bytes=support_installed_bytes,
            growth_bytes=self.growth_bytes,
            metadata_reserve_bytes=self.metadata_reserve_bytes,
        )

    def write(
        self,
        *,
        member: VerifiedReleaseMember,
        destination: DestinationSlot,
        source: BinaryIO,
        storage: SlotStorage,
        support_installed_bytes: int,
    ) -> VerifiedBaseSlotWrite:
        """Stream decompressed bytes, flush, read back and prove the raw count."""
        if destination.semantic_slot == destination.active_slot:
            raise SlotWriteError("refusing to stage into the active slot")
        if destination.semantic_slot == destination.accepted_slot:
            raise SlotWriteError("refusing to stage into the accepted slot")
        if storage.capacity_bytes != destination.slot_capacity_bytes:
            raise SlotWriteError("slot store capacity does not match the layout slot")
        required = self.required_slot_bytes(member, support_installed_bytes)
        if required > destination.slot_capacity_bytes:
            raise SlotWriteError(
                "base payload plus finalization headroom exceeds the slot capacity"
            )
        if not hasattr(source, "read"):
            raise SlotWriteError("release member source must be a binary stream")

        digest = hashlib.sha256()
        offset = 0
        remaining = member.payload_uncompressed_bytes
        while remaining > 0:
            chunk = _read_exact(source, min(self.chunk_bytes, remaining))
            if not chunk:
                raise SlotWriteError(
                    "decompressed payload stream ended before the uncompressed size"
                )
            if len(chunk) > remaining:
                raise SlotWriteError(
                    "decompressed payload stream exceeds the uncompressed size"
                )
            storage.write_at(offset, chunk)
            digest.update(chunk)
            offset += len(chunk)
            remaining -= len(chunk)
        try:
            trailing = source.read(1)
        except Exception as exc:
            raise SlotWriteError(f"payload decompression failed: {exc}") from exc
        if trailing:
            raise SlotWriteError(
                "decompressed payload stream is longer than the uncompressed size"
            )
        storage.flush()

        # Read back exactly the uncompressed range and require stream/readback
        # hash agreement with a constant-time comparison (write integrity;
        # the compressed transport digest was already proven at inspection).
        readback = hashlib.sha256()
        read_offset = 0
        read_remaining = member.payload_uncompressed_bytes
        while read_remaining > 0:
            piece = storage.read_at(
                read_offset, min(self.chunk_bytes, read_remaining)
            )
            readback.update(piece)
            read_offset += len(piece)
            read_remaining -= len(piece)
        streamed_hex = digest.hexdigest()
        readback_hex = readback.hexdigest()
        if not hmac.compare_digest(readback_hex, streamed_hex):
            raise SlotWriteError("slot readback digest does not match the streamed digest")

        token = secrets.token_hex(16)
        _ISSUED_WRITE_TOKENS.append(token)
        return VerifiedBaseSlotWrite(
            member=member,
            destination=destination,
            bytes_written=member.payload_uncompressed_bytes,
            slot_digest=readback_hex,
            write_token=token,
        )


# ---------------------------------------------------------------------------
# Finalizer inputs: inventory attestation, support set, profile policy
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class HardwareInventoryAttestation:
    """The hardware-inventory token the finalizer binds into the receipt."""

    token: str
    complete: bool = True

    def __post_init__(self) -> None:
        _require_hex64(self.token, field_name="hardware inventory token")
        if self.complete is not True:
            raise SlotFinalizeError(
                "hardware inventory is incomplete; refusing finalization"
            )

    @classmethod
    def from_inventory(cls, inventory: object) -> "HardwareInventoryAttestation":
        """Attest a platform hardware inventory snapshot (must be complete)."""
        token = getattr(inventory, "token", "")
        truncated = bool(getattr(inventory, "truncated", True))
        scan_errors = getattr(inventory, "scan_errors", 1)
        if truncated or scan_errors != 0:
            raise SlotFinalizeError(
                "hardware inventory is incomplete; refusing finalization"
            )
        return cls(token=str(token))


@dataclass(frozen=True, slots=True)
class ReleaseSupportSet:
    """The release-bound support set the finalizer may install from.

    ``support_digest``/``support_size`` bind the v3 hardware-support member
    from the release manifest (None together when the optional member is
    absent); ``installed_size_bound`` is the installed-size upper bound used
    by the capacity proof. Requested packages must be release-approved
    firmware/microcode classes; anything else fails closed. Installer pools
    convert via ``greia_installer.slots``.
    """

    support_digest: str | None
    support_size: int | None
    installed_size_bound: int
    provided_firmware: frozenset[str]
    provided_microcode: frozenset[str]
    packages: tuple[InstalledPackage, ...]

    def __post_init__(self) -> None:
        if (self.support_digest is None) != (self.support_size is None):
            raise SlotFinalizeError(
                "support digest/size must be present together or absent together"
            )
        if self.support_digest is not None and self.support_size is not None:
            _require_hex64(self.support_digest, field_name="support digest")
            _require_count(self.support_size, field_name="support size")
        _require_count(
            self.installed_size_bound,
            field_name="support installed-size bound",
            minimum=0,
        )
        if self.provided_firmware & self.provided_microcode:
            raise SlotFinalizeError("support firmware/microcode classes overlap")
        known = {package.name for package in self.packages}
        if not (self.provided_firmware | self.provided_microcode) <= known:
            raise SlotFinalizeError("support classes reference unmanifested packages")

    def require_firmware(self, packages: tuple[str, ...]) -> tuple[str, ...]:
        requested = tuple(dict.fromkeys(packages))
        for name in requested:
            if name not in self.provided_firmware:
                raise SlotFinalizeError(
                    f"support package is not approved firmware: {name}"
                )
        return requested

    def require_microcode(self, packages: tuple[str, ...]) -> tuple[str, ...]:
        requested = tuple(dict.fromkeys(packages))
        for name in requested:
            if name not in self.provided_microcode:
                raise SlotFinalizeError(
                    f"support package is not approved microcode: {name}"
                )
        return requested

    def record_for(self, name: str) -> InstalledPackage:
        for package in self.packages:
            if package.name == name:
                return package
        raise SlotFinalizeError(f"support package has no installed record: {name}")


@dataclass(frozen=True, slots=True)
class SlotProfilePolicy:
    """Validated profile policy the finalizer writes slot-locally.

    The four optional release facts (``architecture``, ``platform_family``,
    ``profile``, ``version``) are the v3 release's compatibility
    identity. They are stated into the slot-owned
    ``etc/greia-os/release-identity.json`` authority only when the caller
    supplies an authoritative (non-``unknown``) value; ``None`` means the
    fact is not authoritatively known and the key is omitted so downstream
    resolution keeps falling back instead of recording a guess.
    """

    layout_id: str
    system_slot_bytes: int
    boot_backend: str
    architecture: str | None = None
    platform_family: str | None = None
    profile: str | None = None
    version: str | None = None
    persist_filesystem_uuid: str | None = None
    boot_control_filesystem_uuid: str | None = None

    def __post_init__(self) -> None:
        if not self.layout_id or len(self.layout_id) > 64:
            raise SlotFinalizeError("profile layout_id is invalid")
        _require_count(self.system_slot_bytes, field_name="profile slot bytes")
        if not self.boot_backend or len(self.boot_backend) > 64:
            raise SlotFinalizeError("profile boot_backend is invalid")
        for field_name, value, maximum in (
            ("profile architecture", self.architecture, _MAX_RELEASE_ARCHITECTURE),
            (
                "profile platform_family",
                self.platform_family,
                _MAX_RELEASE_PLATFORM_FAMILY,
            ),
            ("profile profile", self.profile, _MAX_RELEASE_PROFILE),
        ):
            if value is None:
                continue
            if (
                not isinstance(value, str)
                or not value
                or len(value) > maximum
                or not _RELEASE_FACT_RE.fullmatch(value)
            ):
                raise SlotFinalizeError(f"{field_name} is invalid")
        if self.version is not None:
            if (
                not isinstance(self.version, str)
                or not self.version
                or len(self.version) > _MAX_RELEASE_VERSION
                or any(ord(character) < 32 for character in self.version)
            ):
                raise SlotFinalizeError("profile version is invalid")
        for field_name in (
            "persist_filesystem_uuid",
            "boot_control_filesystem_uuid",
        ):
            value = getattr(self, field_name)
            if value is None:
                continue
            if not isinstance(value, str):
                raise SlotFinalizeError(f"profile {field_name} is invalid")
            try:
                normalized = str(uuid.UUID(value))
            except (ValueError, AttributeError) as exc:
                raise SlotFinalizeError(f"profile {field_name} is invalid") from exc
            object.__setattr__(self, field_name, normalized)

    def release_identity_facts(self) -> dict[str, str]:
        """Return the authoritative release facts to state in the identity.

        ``None``, empty and ``"unknown"`` values are unstated (omitted):
        the finalizer must never record a host guess or an ``unknown``
        placeholder as an authoritative fact.
        """
        facts: dict[str, str] = {}
        for key, value in (
            ("architecture", self.architecture),
            ("platform_family", self.platform_family),
            ("profile", self.profile),
            ("version", self.version),
        ):
            if isinstance(value, str) and value and value != "unknown":
                facts[key] = value
        return facts


# ---------------------------------------------------------------------------
# Release-bound hardware selection (Step 8A.4 glue)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ResolvedHardwareSelection:
    """Deterministic inventory-bound package selection for one finalization.

    Binds a resolver plan's inventory token to the exact approved
    firmware/microcode sets the finalizer must install. Construct only via
    :func:`resolve_hardware_selection`; :class:`SlotFinalizer` requires the
    attested inventory token and the installed package set to match this
    selection exactly.
    """

    inventory_token: str
    firmware: tuple[str, ...]
    microcode: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_hex64(self.inventory_token, field_name="hardware inventory token")
        if tuple(sorted(self.firmware)) != tuple(self.firmware) or len(
            set(self.firmware)
        ) != len(self.firmware):
            raise SlotFinalizeError("selected firmware set is not deterministic")
        if tuple(sorted(self.microcode)) != tuple(self.microcode) or len(
            set(self.microcode)
        ) != len(self.microcode):
            raise SlotFinalizeError("selected microcode set is not deterministic")


def resolve_hardware_selection(
    *,
    plan: HardwareSupportPlan,
    support: ReleaseSupportSet,
) -> ResolvedHardwareSelection:
    """Resolve one deterministic release-bound selection from a resolver plan.

    Only ``AUTO_ELIGIBLE`` firmware/microcode recommendations are selected;
    advisory entries stay diagnostic. Every selected package must belong to
    the release support set's approved classes — a resolver recommendation
    with no release provider (missing provider) fails closed. The plan must
    be complete; an incomplete plan selects nothing.
    """
    if not plan.complete:
        raise SlotFinalizeError(
            "hardware resolution is incomplete; refusing release selection"
        )
    firmware: list[str] = []
    microcode: list[str] = []
    for recommendation in plan.recommendations:
        if recommendation.disposition is not SupportDisposition.AUTO_ELIGIBLE:
            continue
        if recommendation.kind is SupportKind.FIRMWARE:
            if recommendation.package not in support.provided_firmware:
                raise SlotFinalizeError(
                    "hardware selection has no release provider: "
                    f"{recommendation.package}"
                )
            firmware.append(recommendation.package)
        elif recommendation.kind is SupportKind.MICROCODE:
            if recommendation.package not in support.provided_microcode:
                raise SlotFinalizeError(
                    "hardware selection has no release provider: "
                    f"{recommendation.package}"
                )
            microcode.append(recommendation.package)
        else:
            raise SlotFinalizeError(
                "hardware selection ignores non-firmware automatic "
                f"recommendation: {recommendation.package}"
            )
    return ResolvedHardwareSelection(
        inventory_token=plan.inventory_token,
        firmware=tuple(sorted(set(firmware))),
        microcode=tuple(sorted(set(microcode))),
    )


# ---------------------------------------------------------------------------
# Boot artifacts: generic kernel identity plus host-bound initramfs identity
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SlotBootArtifacts:
    """Per-slot generic-boot artifacts (x86 stable generic-boot ABI shape)."""

    generic_kernel_sha256: str
    host_initramfs_sha256: str

    def __post_init__(self) -> None:
        try:
            _require_hex64(
                self.generic_kernel_sha256, field_name="generic kernel digest"
            )
            _require_hex64(
                self.host_initramfs_sha256, field_name="host initramfs digest"
            )
        except SlotWriteError as exc:
            raise SlotFinalizeError(
                f"boot artifact identity is invalid: {exc}"
            ) from exc

    def as_dict(self) -> dict[str, str]:
        return {
            "generic_kernel_sha256": self.generic_kernel_sha256,
            "host_initramfs_sha256": self.host_initramfs_sha256,
        }


class SlotBootArtifactBuilder(Protocol):
    """Build the per-slot boot artifacts during finalization.

    The default (:class:`DeterministicBootArtifactBuilder`) derives the
    identities deterministically without host tooling; backends that run a
    real initramfs rebuild implement this protocol instead. Any build
    failure fails the finalization closed.
    """

    def build(
        self,
        *,
        base_sha256: str,
        inventory_token: str,
        packages_digest: str,
    ) -> SlotBootArtifacts: ...


@dataclass(frozen=True, slots=True)
class DeterministicBootArtifactBuilder:
    """Derive boot-artifact identities without host tooling or network.

    The generic kernel identity is the verified base digest itself (the
    payload carries the generic kernel); the host initramfs identity binds
    base + inventory + installed packages so it is unique to this machine
    and this candidate. Recomputed deterministically for verification.
    """

    def build(
        self,
        *,
        base_sha256: str,
        inventory_token: str,
        packages_digest: str,
    ) -> SlotBootArtifacts:
        host = hashlib.sha256(
            f"{base_sha256}:{inventory_token}:{packages_digest}\n".encode("utf-8")
        ).hexdigest()
        return SlotBootArtifacts(
            generic_kernel_sha256=base_sha256,
            host_initramfs_sha256=host,
        )


# ---------------------------------------------------------------------------
# Finalization receipt
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FinalizationReceipt:
    """Bounded finalization facts written slot-locally and returned.

    ``support_*`` are None together when
    the optional hardware-support member was absent. ``base_*`` bind the
    uncompressed staged image (raw byte count + readback hash).
    """

    schema_version: int
    finalizer_version: str
    release_id: str
    slot: str
    role: str
    base_sha256: str
    base_bytes: int
    support_sha256: str | None
    support_size: int | None
    inventory_token: str
    packages: tuple[InstalledPackage, ...]
    packages_digest: str
    generic_kernel_sha256: str
    host_initramfs_sha256: str
    filesystem_uuid: str
    layout_id: str
    slot_capacity_bytes: int

    def as_dict(self) -> dict[str, object]:
        return {
            "artifact_digests": {
                "generic_kernel_sha256": self.generic_kernel_sha256,
                "host_initramfs_sha256": self.host_initramfs_sha256,
            },
            "base_bytes": self.base_bytes,
            "base_sha256": self.base_sha256,
            "filesystem_uuid": self.filesystem_uuid,
            "finalizer_version": self.finalizer_version,
            "inventory_token": self.inventory_token,
            "layout_id": self.layout_id,
            "packages": [
                {
                    "architecture": package.architecture,
                    "kind": package.kind,
                    "name": package.name,
                    "sha256": package.sha256,
                    "version": package.version,
                }
                for package in self.packages
            ],
            "packages_digest": self.packages_digest,
            "release_id": self.release_id,
            "role": self.role,
            "schema_version": self.schema_version,
            "slot": self.slot,
            "slot_capacity_bytes": self.slot_capacity_bytes,
            "support_sha256": self.support_sha256,
            "support_size": self.support_size,
        }

    def canonical_bytes(self) -> bytes:
        return _canonical_bytes(self.as_dict())


# ---------------------------------------------------------------------------
# Shared SlotFinalizer
# ---------------------------------------------------------------------------


def _check_relative_path(value: str) -> str:
    if not isinstance(value, str) or not value or value.startswith("/") or "*" in value:
        raise SlotFinalizeError(f"slot file path is not a bounded relative path")
    normalized = os.path.normpath(value)
    if normalized != value or value.startswith("..") or "/../" in value:
        raise SlotFinalizeError(f"slot file path escapes its canonical form: {value}")
    if len(value.encode("utf-8")) > 256:
        raise SlotFinalizeError("slot file path is too long")
    return value


def _check_slot_config(config: Mapping[str, str]) -> dict[str, str]:
    if len(config) > _MAX_SLOT_CONFIG_ENTRIES:
        raise SlotFinalizeError("slot profile configuration exceeds Greia bounds")
    checked: dict[str, str] = {}
    for key, value in config.items():
        if not isinstance(key, str) or not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", key):
            raise SlotFinalizeError(f"slot profile key is not a safe identifier: {key!r}")
        if not isinstance(value, str) or len(value.encode("utf-8")) > _MAX_SLOT_CONFIG_VALUE_BYTES:
            raise SlotFinalizeError(f"slot profile value exceeds Greia bounds: {key!r}")
        checked[key] = value
    return checked


def _s04_diag_stage(name: str) -> None:
    """TEMPORARY Session-04 diagnostic; removed before Session 04 closure.

    Delegates to :mod:`greia_platform.session04_serial_diag`, which owns the
    marker-gated serial emit, so this module carries no device surface.
    """
    session04_serial_diag.emit_stage(f"finalize-{name}")


@dataclass(frozen=True, slots=True)
class SlotFinalizer:
    """Bind, expand, mount, support-install and receipt one verified slot.

    Consumes only a registered :class:`VerifiedBaseSlotWrite` plus the
    validated role, hardware-inventory attestation, release-bound support set
    and profile policy. An optional :class:`ResolvedHardwareSelection` pins
    the attested inventory and the installed package set to one deterministic
    resolver outcome; an optional :class:`SlotBootArtifactBuilder` owns the
    per-slot boot-artifact build (its failure fails closed). Performs only
    bounded mutations on the destination slot; the active/accepted slot is
    never addressable here.
    """

    chunk_bytes: int = SLOT_WRITE_CHUNK_BYTES
    growth_bytes: int = FINALIZATION_GROWTH_BYTES
    metadata_reserve_bytes: int = SLOT_METADATA_RESERVE_BYTES

    def finalize(
        self,
        *,
        write: VerifiedBaseSlotWrite,
        destination: DestinationSlot,
        filesystem: SlotFilesystem,
        package_installer: SlotPackageInstaller,
        inventory: HardwareInventoryAttestation,
        support: ReleaseSupportSet,
        profile_policy: SlotProfilePolicy,
        firmware_packages: tuple[str, ...] = (),
        microcode_packages: tuple[str, ...] = (),
        slot_config: Mapping[str, str] | None = None,
        selection: ResolvedHardwareSelection | None = None,
        artifact_builder: SlotBootArtifactBuilder | None = None,
        support_installed_bytes: int | None = None,
    ) -> FinalizationReceipt:
        """Run the bounded destination-only finalization transaction."""
        if destination != write.destination:
            raise SlotFinalizeError("finalization role does not match the verified write")
        if destination.semantic_slot == destination.active_slot:
            raise SlotFinalizeError("refusing to finalize the active slot")
        if destination.semantic_slot == destination.accepted_slot:
            raise SlotFinalizeError("refusing to finalize the accepted slot")
        if profile_policy.system_slot_bytes != destination.slot_capacity_bytes:
            raise SlotFinalizeError("profile slot bytes do not match the layout slot")
        if profile_policy.layout_id != destination.layout_id:
            raise SlotFinalizeError("profile layout does not match the layout record")
        if profile_policy.boot_backend == "grub-ab-v1" and (
            profile_policy.persist_filesystem_uuid is None
            or profile_policy.boot_control_filesystem_uuid is None
        ):
            raise SlotFinalizeError(
                "A/B finalization requires verified PERSIST and boot-control UUIDs"
            )
        if support.support_digest != write.member.hardware_support_sha256:
            raise SlotFinalizeError("support set is not the release-bound support member")
        if support.support_size != write.member.hardware_support_size:
            raise SlotFinalizeError("support set size is not the release-bound member size")
        # Headroom re-check uses the caller-provided selected-set bound when
        # given (the exact firmware/microcode being installed); otherwise it
        # falls back to the release set's whole-pool bound. Callers proving
        # capacity pre-write must pass the same selected number they proved.
        selected_bound = (
            support.installed_size_bound
            if support_installed_bytes is None
            else support_installed_bytes
        )
        if (
            isinstance(selected_bound, bool)
            or not isinstance(selected_bound, int)
            or selected_bound < 0
        ):
            raise SlotFinalizeError("support installed-size bound is not authoritative")
        required = _required_slot_bytes(
            base_bytes=write.member.payload_uncompressed_bytes,
            minimum_slot_bytes=write.member.minimum_slot_bytes,
            support_installed_bytes=selected_bound,
            growth_bytes=self.growth_bytes,
            metadata_reserve_bytes=self.metadata_reserve_bytes,
        )
        if required > destination.slot_capacity_bytes:
            raise SlotFinalizeError(
                "finalization headroom exceeds the slot capacity"
            )
        firmware = support.require_firmware(tuple(firmware_packages))
        microcode = support.require_microcode(tuple(microcode_packages))
        if selection is not None:
            if selection.inventory_token != inventory.token:
                raise SlotFinalizeError(
                    "hardware selection inventory does not match "
                    "the attested inventory"
                )
            if (
                tuple(firmware) != selection.firmware
                or tuple(microcode) != selection.microcode
            ):
                raise SlotFinalizeError(
                    "finalization package set does not match "
                    "the resolved hardware selection"
                )
        config = _check_slot_config(dict(slot_config or {}))
        for rel_path in (
            FINALIZED_GENERIC_REL_PATH,
            RELEASE_IDENTITY_REL_PATH,
            SLOT_PROFILE_REL_PATH,
            RECEIPT_REL_PATH,
            FSTAB_REL_PATH,
        ):
            _check_relative_path(rel_path)

        # Consume the verified-write capability for exactly one
        # finalization. Every gate above runs before the first destination
        # mutation, so any refusal — unknown/forged/stale token included —
        # leaves the destination seam untouched, and a stale write can never
        # replay against another role (or the same one).
        _consume_write_token(write)

        # Restore the destination role's stable filesystem UUID recorded in
        # layout authority, overwriting the release-builder template UUID
        # carried by the staged payload. The role UUID is distinct from the
        # other role's UUID by construction (DestinationSlot); it is never
        # cloned from the template, and the layout record stays authoritative
        # with no rewrite path.
        filesystem_uuid = destination.role_filesystem_uuid

        mounted = False
        try:
            # Check/expand first: a payload copied from a packaged fixture may
            # carry a journal that needs replay, and tune2fs refuses a UUID
            # change until that check has run. Expansion does not consume the
            # role UUID; binding it immediately afterwards keeps the mount
            # identity check below authoritative.
            filesystem.expand_to_capacity()
            filesystem.bind_filesystem_uuid(filesystem_uuid)
            mountpoint = filesystem.mount()
            mounted = True
            if not isinstance(mountpoint, Path):
                raise SlotFinalizeError("slot mount did not return a path")

            try:
                present_canonical_mount_targets(mountpoint)
                if profile_policy.persist_filesystem_uuid is not None:
                    persist_target = Path(mountpoint) / PERSIST_BOOT_MOUNTPOINT.lstrip("/")
                    run_directory = persist_target.parent
                    if run_directory.is_symlink():
                        raise PersistentLayoutError(
                            "PERSIST mountpoint path passes a symbolic link"
                        )
                    run_directory.mkdir(mode=0o755, parents=True, exist_ok=True)
                    if not run_directory.is_dir() or run_directory.is_symlink():
                        raise PersistentLayoutError(
                            "PERSIST mountpoint parent is not a real directory"
                        )
                    if persist_target.is_symlink():
                        raise PersistentLayoutError(
                            "PERSIST mountpoint may not be a symbolic link"
                        )
                    persist_target.mkdir(mode=0o700, exist_ok=True)
                    if not persist_target.is_dir() or persist_target.is_symlink():
                        raise PersistentLayoutError(
                            "PERSIST mountpoint is not a real directory"
                        )
                    os.chmod(persist_target, 0o700)
            except PersistentLayoutError as exc:
                raise SlotFinalizeError(
                    f"canonical persistent bind targets refused: {exc}"
                ) from exc

            # Destination fstab specialization (Repair C): render the
            # single-owner canonical policy for the bound role UUID right
            # after mount, before completeness/health acceptance, so an
            # updated slot carries the same policy as a fresh install and
            # no release-builder template UUID can survive.
            try:
                fstab_text = render_fstab(
                    filesystem_uuid,
                    persist_filesystem_uuid=profile_policy.persist_filesystem_uuid,
                    boot_control_filesystem_uuid=(
                        profile_policy.boot_control_filesystem_uuid
                    ),
                )
            except ValueError as exc:
                raise SlotFinalizeError(
                    f"destination fstab refused: {exc}"
                ) from exc
            try:
                filesystem.write_file(
                    FSTAB_REL_PATH, fstab_text.encode("ascii")
                )
            except SlotFinalizeError:
                raise
            except Exception as exc:
                raise SlotFinalizeError(
                    f"destination fstab write failed: {exc}"
                ) from exc
            # Canonical fstab mode (Repair T16): the shared block seam
            # forces ``0o600`` on every finalized file; fstab carries no
            # secrets and must match fresh assembly at ``FSTAB_FILE_MODE``
            # (``0o644``). Re-chmod only this path via the mounted
            # mountpoint already in hand; the block seam keeps its
            # ``0o600`` default for every other finalized file and gains
            # no per-file mode parameter. Dict-recording fake seams that
            # never persist the file carry no on-disk mode and are
            # skipped; any real on-disk failure fails closed.
            try:
                fstab_on_disk = mountpoint / FSTAB_REL_PATH
                if os.path.islink(fstab_on_disk):
                    raise SlotFinalizeError(
                        "destination fstab target may not be a symbolic link"
                    )
                if fstab_on_disk.is_file():
                    os.chmod(fstab_on_disk, FSTAB_FILE_MODE)
            except SlotFinalizeError:
                raise
            except OSError as exc:
                raise SlotFinalizeError(
                    f"destination fstab mode refused: {exc}"
                ) from exc
            _s04_diag_stage("fstab")

            # Shared post-write completeness smoke (A4/A11): prove the
            # staged slot carries real Greia userspace including the
            # finalizer's apt-get/dpkg needs before any support install
            # or boot-asset write. An incomplete or V12G-like slot fails
            # closed here and can never become bootable.
            try:
                filesystem.check_completeness()
            except SlotFinalizeError:
                raise
            except Exception as exc:
                raise SlotFinalizeError(
                    f"slot completeness smoke failed: {exc}"
                ) from exc
            _s04_diag_stage("completeness")

            installed = package_installer.install(firmware, microcode)
            expected = {*(firmware), *(microcode)}
            if {package.name for package in installed} != expected or len(installed) != len(expected):
                raise SlotFinalizeError("installed support set does not match approval")
            for package in installed:
                recorded = support.record_for(package.name)
                if (
                    package.version != recorded.version
                    or package.sha256 != recorded.sha256
                    or package.architecture != recorded.architecture
                ):
                    raise SlotFinalizeError(
                        f"installed support record changed: {package.name}"
                    )

            _s04_diag_stage("hw-installed")
            packages_digest = self._packages_digest(installed)
            builder = artifact_builder or DeterministicBootArtifactBuilder()
            try:
                artifacts = builder.build(
                    base_sha256=write.slot_digest,
                    inventory_token=inventory.token,
                    packages_digest=packages_digest,
                )
            except SlotFinalizeError:
                raise
            except Exception as exc:
                raise SlotFinalizeError(
                    "boot artifact build failed; refusing finalization"
                ) from exc
            if not isinstance(artifacts, SlotBootArtifacts):
                raise SlotFinalizeError(
                    "boot artifact builder returned an invalid result"
                )
            _s04_diag_stage("artifacts")
            # The installed GRUB A/B entries use adapter-owned stable names.
            # The payload carries the generic names; publish the aliases from
            # the mounted slot after hardware support so the finalized slot
            # is actually bootable.  Fail closed if the payload is incomplete.
            link_file = getattr(filesystem, "link_file", None)
            if callable(link_file):
                for source_rel, target_rel in (
                    (SLOT_GENERIC_KERNEL_REL_PATH, SLOT_KERNEL_REL_PATH),
                    (SLOT_GENERIC_INITRAMFS_REL_PATH, SLOT_INITRAMFS_REL_PATH),
                ):
                    source = Path(mountpoint) / source_rel
                    if source.is_symlink() or not source.is_file():
                        raise SlotFinalizeError(
                            f"payload boot artifact is missing: {source_rel}"
                        )
                    link_file(source_rel, target_rel)
            # A test-only SlotFilesystem double without the link seam keeps
            # the historical metadata contract; production block slots always
            # implement link_file and must publish the boot aliases.
            required_finalized = (
                REQUIRED_FINALIZED_FILES
                if callable(link_file)
                else tuple(
                    name
                    for name in REQUIRED_FINALIZED_FILES
                    if name not in (SLOT_KERNEL_REL_PATH, SLOT_INITRAMFS_REL_PATH)
                )
            )
            filesystem.write_file(
                FINALIZED_GENERIC_REL_PATH,
                _canonical_bytes(artifacts.as_dict()),
            )
            filesystem.write_file(
                RELEASE_IDENTITY_REL_PATH,
                _canonical_bytes(
                    {
                        "boot_backend": profile_policy.boot_backend,
                        "layout_id": destination.layout_id,
                        "release_id": write.member.release_id,
                        "role": destination.role,
                        "slot": destination.semantic_slot,
                        **profile_policy.release_identity_facts(),
                    }
                ),
            )
            filesystem.write_file(
                SLOT_PROFILE_REL_PATH,
                _canonical_bytes(
                    {
                        "boot_backend": profile_policy.boot_backend,
                        "layout_id": destination.layout_id,
                        "slot": destination.semantic_slot,
                        "values": config,
                    }
                ),
            )

            receipt = FinalizationReceipt(
                schema_version=FINALIZATION_RECEIPT_SCHEMA_VERSION,
                finalizer_version=FINALIZER_VERSION,
                release_id=write.member.release_id,
                slot=destination.semantic_slot,
                role=destination.role,
                base_sha256=write.slot_digest,
                base_bytes=write.bytes_written,
                support_sha256=support.support_digest,
                support_size=support.support_size,
                inventory_token=inventory.token,
                packages=tuple(sorted(installed, key=lambda item: item.name)),
                packages_digest=packages_digest,
                generic_kernel_sha256=artifacts.generic_kernel_sha256,
                host_initramfs_sha256=artifacts.host_initramfs_sha256,
                filesystem_uuid=filesystem_uuid,
                layout_id=destination.layout_id,
                slot_capacity_bytes=destination.slot_capacity_bytes,
            )
            filesystem.write_file(RECEIPT_REL_PATH, receipt.canonical_bytes())
            _s04_diag_stage("receipt")

            missing = filesystem.missing_files(
                (*required_finalized, RECEIPT_REL_PATH)
            )
            if missing:
                raise SlotFinalizeError(
                    "finalized slot is missing files: " + ", ".join(missing)
                )
            filesystem.check_health()
            _s04_diag_stage("health")
            return receipt
        finally:
            if mounted:
                try:
                    filesystem.unmount()
                finally:
                    filesystem.sync()
            else:
                filesystem.sync()

    @staticmethod
    def _packages_digest(installed: tuple[InstalledPackage, ...]) -> str:
        lines = "\n".join(
            f"{package.name}:{package.version}:{package.sha256}"
            for package in sorted(installed, key=lambda item: item.name)
        )
        return hashlib.sha256((lines + "\n").encode("utf-8")).hexdigest()
