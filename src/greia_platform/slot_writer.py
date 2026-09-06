"""Common streamed slot writer, verified base-slot capability and finalizer seam.

L7-SLOTS (R0/R1 source scope): files and fakes only. No partition, mount,
filesystem, boot or physical-slot writes live here; production block/mount
backends are injected later through the narrow protocols below
(``SlotStorage``, ``SlotFilesystem``, ``SlotPackageInstaller``).

Staging order (strict):

.. code-block:: text

    stream signed base payload -> flush -> read back the exact signed range
    -> require the signed digest -> only then bind the destination role's
    stable filesystem UUID, expand, and run the finalizer.

Both the updater (``greia_platform.system_updates``) and the installer
(``greia_installer``) import and call this same implementation; the installer
adapts its already-verified hardware logic (``TargetHardwareSupportInstaller``)
to the shared ``SlotPackageInstaller`` protocol instead of copying it (see
``greia_installer.slots``).

Destination roles resolve only from trusted layout state
(``InstalledLayoutRecord``), never from Parent/UI paths. ``A`` maps to the
``system-a`` partition role and ``B`` to ``system-b``; the destination must be
neither the active nor the accepted slot. Fresh filesystem UUIDs are minted
with ``uuid4`` at finalization: A/B role UUIDs stay distinct and are never
cloned from the release-builder template (the deterministic payload header
carries only profile/release identity, no UUIDs).

Capacity proof (checked at write time and re-checked at finalization)::

    max(base bytes, manifest minimum) + support installed-size bound
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

from .persistent_layout import InstalledLayoutRecord

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

#: Files the finalizer must prove present before writing the receipt.
REQUIRED_FINALIZED_FILES = (
    FINALIZED_GENERIC_REL_PATH,
    RELEASE_IDENTITY_REL_PATH,
    SLOT_PROFILE_REL_PATH,
)

_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_SLOT_ROLE_RE = re.compile(r"^system-[ab]$")
_MAX_SLOT_CONFIG_ENTRIES = 32
_MAX_SLOT_CONFIG_VALUE_BYTES = 256

#: Capability tokens issued by :class:`SlotWriter.write`, keyed by token.
#: :class:`SlotFinalizer` accepts only registered tokens, so a forged or
#: guessed ``VerifiedBaseSlotWrite`` can never enter binding/finalization.
#: Explicitly bounded (one entry per staged slot in practice); evicting the
#: oldest token only invalidates a stale unfinalized write fail-closed.
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
    """One previously verified release payload bound to its signed digest.

    Construct only from an ``InspectedUpdateBundle`` *after* signature,
    compatibility and anti-rollback verification (``SystemUpdateService``).
    The writer re-proves the digest against the streamed bytes; it does not
    re-prove signatures.
    """

    release_id: str
    release_sequence: int
    payload_sha256: str
    payload_size: int
    minimum_slot_bytes: int
    hardware_support_sha256: str
    hardware_support_size: int

    def __post_init__(self) -> None:
        if not self.release_id or len(self.release_id) > 96:
            raise SlotWriteError("release_id is outside Greia bounds")
        _require_count(self.release_sequence, field_name="release_sequence", minimum=0)
        _require_hex64(self.payload_sha256, field_name="payload_sha256")
        _require_count(self.payload_size, field_name="payload_size")
        _require_count(
            self.minimum_slot_bytes, field_name="minimum_slot_bytes"
        )
        if self.minimum_slot_bytes < self.payload_size:
            raise SlotWriteError("minimum_slot_bytes must cover the base payload")
        _require_hex64(
            self.hardware_support_sha256, field_name="hardware_support_sha256"
        )
        _require_count(
            self.hardware_support_size, field_name="hardware_support_size"
        )

    @classmethod
    def from_manifest(cls, manifest: "UpdateManifest") -> "VerifiedReleaseMember":
        """Bind the signed manifest facts after the caller verified trust."""
        return cls(
            release_id=manifest.release_id,
            release_sequence=manifest.release_sequence,
            payload_sha256=manifest.payload_sha256,
            payload_size=manifest.payload_size,
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
    """

    semantic_slot: str
    role: str
    slot_capacity_bytes: int
    active_slot: str | None
    accepted_slot: str | None
    layout_id: str
    previous_filesystem_uuid: str
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
            self.previous_filesystem_uuid, field_name="previous filesystem UUID"
        )
        _require_canonical_uuid(
            self.other_role_filesystem_uuid, field_name="other role filesystem UUID"
        )
        if (
            self.previous_filesystem_uuid == self.other_role_filesystem_uuid
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
            previous_filesystem_uuid=own.filesystem_uuid,
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
    UUID, expanding it, mounting it, writing slot-local files, checking
    health, then unmounting and syncing. The active/accepted slot is never
    addressable through this seam.
    """

    def bind_filesystem_uuid(self, filesystem_uuid: str) -> None: ...

    def expand_to_capacity(self) -> None: ...

    def mount(self) -> Path: ...

    def unmount(self) -> None: ...

    def sync(self) -> None: ...

    def write_file(self, relative_path: str, data: bytes) -> None: ...

    def missing_files(self, required: tuple[str, ...]) -> tuple[str, ...]: ...

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
    """Capability proving a streamed base payload passed readback verification.

    Only :class:`SlotWriter.write` issues registered instances; only a
    registered instance may enter binding/finalization. The capability carries
    no byte content, only the proven facts.
    """

    member: VerifiedReleaseMember
    destination: DestinationSlot
    bytes_written: int
    slot_digest: str
    write_token: str = field(compare=False)

    def __post_init__(self) -> None:
        _require_hex64(self.slot_digest, field_name="slot digest")
        if self.slot_digest != self.member.payload_sha256:
            raise SlotWriteError("slot digest does not match the signed release digest")
        if self.bytes_written != self.member.payload_size:
            raise SlotWriteError("written byte count does not match the signed size")
        if not self.write_token:
            raise SlotWriteError("base-slot write carries no issuance token")


def _is_issued(write: VerifiedBaseSlotWrite) -> bool:
    return write.write_token in _ISSUED_WRITE_TOKENS


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
    """Stream a verified release payload into a destination slot store.

    Public API takes only typed values: the previously verified release
    member, the layout-resolved destination role, a binary source stream, the
    destination store, and the release-bound support installed-size bound. No
    shell strings, arbitrary paths, or ``dd`` arguments cross this API.
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
            base_bytes=member.payload_size,
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
        """Stream, flush, read back and digest-verify the signed payload range."""
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
        remaining = member.payload_size
        while remaining > 0:
            chunk = source.read(min(self.chunk_bytes, remaining))
            if not chunk:
                raise SlotWriteError("release member stream ended before the signed size")
            if not isinstance(chunk, (bytes, bytearray)):
                raise SlotWriteError("release member stream must yield bytes")
            storage.write_at(offset, bytes(chunk))
            digest.update(chunk)
            offset += len(chunk)
            remaining -= len(chunk)
        if source.read(1):
            raise SlotWriteError("release member stream is longer than the signed size")
        storage.flush()

        # Read back exactly the signed range and require the signed digest
        # with a constant-time comparison.
        readback = hashlib.sha256()
        read_offset = 0
        read_remaining = member.payload_size
        while read_remaining > 0:
            piece = storage.read_at(
                read_offset, min(self.chunk_bytes, read_remaining)
            )
            readback.update(piece)
            read_offset += len(piece)
            read_remaining -= len(piece)
        if not hmac.compare_digest(readback.hexdigest(), member.payload_sha256):
            raise SlotWriteError("slot readback digest does not match the signed digest")
        if not hmac.compare_digest(digest.hexdigest(), member.payload_sha256):
            raise SlotWriteError("streamed digest does not match the signed digest")

        token = secrets.token_hex(16)
        _ISSUED_WRITE_TOKENS.append(token)
        return VerifiedBaseSlotWrite(
            member=member,
            destination=destination,
            bytes_written=member.payload_size,
            slot_digest=member.payload_sha256,
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

    ``support_digest``/``support_size`` bind the signed hardware-support
    member from the release manifest; ``installed_size_bound`` is the
    installed-size upper bound used by the capacity proof. Requested packages
    must be release-approved firmware/microcode classes; anything else fails
    closed. Installer pools convert via ``greia_installer.slots``.
    """

    support_digest: str
    support_size: int
    installed_size_bound: int
    provided_firmware: frozenset[str]
    provided_microcode: frozenset[str]
    packages: tuple[InstalledPackage, ...]

    def __post_init__(self) -> None:
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
    """Validated profile policy the finalizer writes slot-locally."""

    layout_id: str
    system_slot_bytes: int
    boot_backend: str

    def __post_init__(self) -> None:
        if not self.layout_id or len(self.layout_id) > 64:
            raise SlotFinalizeError("profile layout_id is invalid")
        _require_count(self.system_slot_bytes, field_name="profile slot bytes")
        if not self.boot_backend or len(self.boot_backend) > 64:
            raise SlotFinalizeError("profile boot_backend is invalid")


# ---------------------------------------------------------------------------
# Finalization receipt
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FinalizationReceipt:
    """Bounded finalization facts written slot-locally and returned."""

    schema_version: int
    finalizer_version: str
    release_id: str
    release_sequence: int
    slot: str
    role: str
    base_sha256: str
    base_bytes: int
    support_sha256: str
    support_size: int
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
            "release_sequence": self.release_sequence,
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


@dataclass(frozen=True, slots=True)
class SlotFinalizer:
    """Bind, expand, mount, support-install and receipt one verified slot.

    Consumes only a registered :class:`VerifiedBaseSlotWrite` plus the
    validated role, hardware-inventory attestation, release-bound support set
    and profile policy. Performs only bounded mutations on the destination
    slot; the active/accepted slot is never addressable here.
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
    ) -> FinalizationReceipt:
        """Run the bounded destination-only finalization transaction."""
        if not _is_issued(write):
            raise SlotFinalizeError(
                "base-slot write is not a registered verified write; "
                "refusing finalization"
            )
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
        if support.support_digest != write.member.hardware_support_sha256:
            raise SlotFinalizeError("support set is not the release-bound support member")
        required = _required_slot_bytes(
            base_bytes=write.member.payload_size,
            minimum_slot_bytes=write.member.minimum_slot_bytes,
            support_installed_bytes=support.installed_size_bound,
            growth_bytes=self.growth_bytes,
            metadata_reserve_bytes=self.metadata_reserve_bytes,
        )
        if required > destination.slot_capacity_bytes:
            raise SlotFinalizeError(
                "finalization headroom exceeds the slot capacity"
            )
        firmware = support.require_firmware(tuple(firmware_packages))
        microcode = support.require_microcode(tuple(microcode_packages))
        config = _check_slot_config(dict(slot_config or {}))
        for rel_path in (
            FINALIZED_GENERIC_REL_PATH,
            RELEASE_IDENTITY_REL_PATH,
            SLOT_PROFILE_REL_PATH,
            RECEIPT_REL_PATH,
        ):
            _check_relative_path(rel_path)

        # Mint the destination role's stable filesystem UUID: fresh random v4,
        # distinct from both the previous destination UUID and the other
        # role's UUID. Never cloned from the release-builder template.
        filesystem_uuid = self._mint_role_uuid(destination)

        mounted = False
        try:
            filesystem.bind_filesystem_uuid(filesystem_uuid)
            filesystem.expand_to_capacity()
            mountpoint = filesystem.mount()
            mounted = True
            if not isinstance(mountpoint, Path):
                raise SlotFinalizeError("slot mount did not return a path")

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

            packages_digest = self._packages_digest(installed)
            artifacts = self._finalized_generic_artifacts(
                base_sha256=write.slot_digest,
                inventory_token=inventory.token,
                packages_digest=packages_digest,
            )
            filesystem.write_file(
                FINALIZED_GENERIC_REL_PATH,
                _canonical_bytes(artifacts),
            )
            filesystem.write_file(
                RELEASE_IDENTITY_REL_PATH,
                _canonical_bytes(
                    {
                        "boot_backend": profile_policy.boot_backend,
                        "layout_id": destination.layout_id,
                        "release_id": write.member.release_id,
                        "release_sequence": write.member.release_sequence,
                        "role": destination.role,
                        "slot": destination.semantic_slot,
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
                release_sequence=write.member.release_sequence,
                slot=destination.semantic_slot,
                role=destination.role,
                base_sha256=write.slot_digest,
                base_bytes=write.bytes_written,
                support_sha256=support.support_digest,
                support_size=support.support_size,
                inventory_token=inventory.token,
                packages=tuple(sorted(installed, key=lambda item: item.name)),
                packages_digest=packages_digest,
                generic_kernel_sha256=artifacts["generic_kernel_sha256"],
                host_initramfs_sha256=artifacts["host_initramfs_sha256"],
                filesystem_uuid=filesystem_uuid,
                layout_id=destination.layout_id,
                slot_capacity_bytes=destination.slot_capacity_bytes,
            )
            filesystem.write_file(RECEIPT_REL_PATH, receipt.canonical_bytes())

            missing = filesystem.missing_files(
                (*REQUIRED_FINALIZED_FILES, RECEIPT_REL_PATH)
            )
            if missing:
                raise SlotFinalizeError(
                    "finalized slot is missing files: " + ", ".join(missing)
                )
            filesystem.check_health()
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
    def _mint_role_uuid(destination: DestinationSlot) -> str:
        for _ in range(10):
            candidate = str(uuid.uuid4())
            if (
                candidate != destination.other_role_filesystem_uuid
                and candidate != destination.previous_filesystem_uuid
            ):
                return candidate
        raise SlotFinalizeError("could not mint a distinct role filesystem UUID")

    @staticmethod
    def _packages_digest(installed: tuple[InstalledPackage, ...]) -> str:
        lines = "\n".join(
            f"{package.name}:{package.version}:{package.sha256}"
            for package in sorted(installed, key=lambda item: item.name)
        )
        return hashlib.sha256((lines + "\n").encode("utf-8")).hexdigest()

    @staticmethod
    def _finalized_generic_artifacts(
        *,
        base_sha256: str,
        inventory_token: str,
        packages_digest: str,
    ) -> dict[str, str]:
        """Derive candidate-local generic/host artifact identities.

        The generic kernel identity is the verified base digest itself (the
        payload carries the generic kernel); the host initramfs identity binds
        base + inventory + installed packages so it is unique to this machine
        and this candidate. Recomputed deterministically for verification.
        """
        host = hashlib.sha256(
            f"{base_sha256}:{inventory_token}:{packages_digest}\n".encode("utf-8")
        ).hexdigest()
        return {
            "generic_kernel_sha256": base_sha256,
            "host_initramfs_sha256": host,
        }
