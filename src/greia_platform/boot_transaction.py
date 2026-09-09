"""Boot artifact sets, boot-transaction backends, journal and initramfs roles.

L7-BOOT (R0/R1 source scope): files and fakes only. No physical
boot-control writes, no bootloader-default changes, no EEPROM access and no
Pi target writes live here. Production firmware/GRUB adapters are injected
later through the narrow :class:`BootTransactionBackend` protocol; the fake
backends below persist their state to regular files so reboot/reconcile
semantics are provable without hardware.

Common lifecycle code (installer first-boot, updater health commit) sees one
backend interface — ``inspect``, ``arm_one_shot``, ``observe_booted_slot``,
``commit_accepted``, ``verify_rollback_ready``, ``reconcile`` — driven
polymorphically by :class:`BootTransactionCoordinator`. No platform
conditionals are scattered through the coordinator: x86 uses stable per-slot
GRUB entries referencing adapter-owned generic paths, Pi uses native
tryboot/``autoboot.txt`` semantics behind the same protocol.

The journal lives root-owned on PERSIST (write-temp/fsync/rename/dir-sync,
owner-only mode). It is status/evidence authority, not a Parent-writable
command queue: transitions accept only platform-observed facts, the actor is
always ``"platform"``, and no backend method accepts a Parent-provided boot
entry or partition path — only semantic slots ``"A"``/``"B"`` resolved from
the trusted layout record.

Initramfs roles: ``BASE`` is deterministic build input bound by the signed
release; ``FINALIZED_GENERIC`` is the required SlotFinalizer-generated
artifact every accepted slot keeps; ``HOST_FAST`` is an optional later
derivative generated on accepted actual hardware and never the sole
recovery path.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import uuid
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Mapping, Protocol


class BootTransactionError(RuntimeError):
    """Boot artifact, backend or coordinator state is invalid."""


class BootJournalError(BootTransactionError):
    """Transaction journal is missing, corrupt or refuses a transition."""


class BootArtifactError(BootTransactionError):
    """Boot artifact set or initramfs role binding is invalid."""


# ---------------------------------------------------------------------------
# Small helpers (canonical JSON, bounded identifiers, atomic durable writes)
# ---------------------------------------------------------------------------


#: Schema version of every boot-transaction record in this module.
BOOT_RECORD_SCHEMA_VERSION = 1

#: Journal file name inside the caller-provided PERSIST-side directory.
JOURNAL_FILE_NAME = "boot-journal.json"

#: Journal files are readable only by their owner (root on device).
JOURNAL_FILE_MODE = 0o600

#: Upper bound for stored journal bytes (journals are small by construction).
MAX_JOURNAL_BYTES = 32 * 1024

#: Upper bound for journal transition evidence (one entry per state change).
MAX_JOURNAL_TRANSITIONS = 32

#: Upper bound for a single transition note.
MAX_TRANSITION_NOTE_BYTES = 512

_HEX64_RE = "0123456789abcdef"


def _canonical_bytes(value: Mapping[str, object]) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _require_slot(value: object, *, field_name: str = "slot") -> str:
    if value not in ("A", "B"):
        raise BootTransactionError(f"{field_name} must be the semantic slot A or B")
    return str(value)


def _require_hex64(value: object, *, field_name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(char not in _HEX64_RE for char in value)
    ):
        raise BootTransactionError(f"{field_name} must be lowercase SHA-256 hex")
    return value


def _require_canonical_uuid(value: object, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise BootTransactionError(f"{field_name} must be text")
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError) as exc:
        raise BootTransactionError(f"{field_name} is not a valid UUID") from exc
    if str(parsed) != value.lower():
        raise BootTransactionError(
            f"{field_name} must be canonical lowercase UUID text"
        )
    return str(parsed)


def _require_root_partuuid(value: object, *, field_name: str) -> str:
    """Observed ``root=PARTUUID=`` value: GPT GUID or MBR ``<sig>-<NN>``.

    T1-IDENT observed record (TAKEOVER-1 T1.1): GPT layouts carry a
    canonical lowercase GUID; MBR layouts carry the Linux
    ``<disk-signature>-<partition-number>`` form, never a minted UUID4.
    Canonicalization matches ``persistent_layout.normalize_mbr_partuuid``.
    """
    if not isinstance(value, str):
        raise BootTransactionError(f"{field_name} must be text")
    try:
        return _require_canonical_uuid(value, field_name=field_name)
    except BootTransactionError:
        pass
    import re as _re

    text = value.strip()
    if "-" not in text:
        raise BootTransactionError(
            f"{field_name} is neither a canonical UUID nor an MBR PARTUUID"
        )
    signature_text, _, number_text = text.rpartition("-")
    signature = signature_text.lower()
    if signature.startswith("0x"):
        signature = signature[2:]
    if not _re.fullmatch(r"[0-9a-f]{8}", signature):
        raise BootTransactionError(
            f"{field_name} is neither a canonical UUID nor an MBR PARTUUID"
        )
    if not number_text.isascii() or not number_text.isdigit():
        raise BootTransactionError(
            f"{field_name} carries an invalid MBR partition number"
        )
    number = int(number_text, 10)
    if not 1 <= number <= 128:
        raise BootTransactionError(
            f"{field_name} carries an MBR partition number outside Greia bounds"
        )
    return f"{signature}-{number:02d}"


def _require_identifier(value: object, *, field_name: str, maximum: int) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > maximum
        or not value[0].isalnum()
        or any(char not in "abcdefghijklmnopqrstuvwxyz0123456789._-" for char in value)
    ):
        raise BootTransactionError(f"{field_name} is not a bounded safe identifier")
    return value


def _fsync_directory(directory: Path) -> None:
    try:
        directory_fd = os.open(directory, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def _atomic_write_file(path: Path, payload: bytes, *, mode: int) -> None:
    """Write-temp/fsync/rename/dir-sync durable write of one small record."""
    location = Path(path)
    location.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{location.name}.", dir=location.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, location)
        _fsync_directory(location.parent)
    finally:
        temporary.unlink(missing_ok=True)


def _durable_write_text(path: Path, text: str, *, mode: int) -> str:
    """Layered FAT-style durable write: new file + fsync + rename + dir-sync.

    Production Pi boot control additionally issues ``syncfs`` on the
    boot-control filesystem; the fake backends call :func:`os.sync` as the
    R0 file-scope equivalent and then re-read and verify the exact bytes.
    Returns the verified text.
    """
    location = Path(path)
    location.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{location.name}.", dir=location.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, location)
        _fsync_directory(location.parent)
        os.sync()
    finally:
        temporary.unlink(missing_ok=True)
    try:
        observed = location.read_text(encoding="utf-8")
    except OSError as exc:
        raise BootTransactionError(
            f"boot-control re-read failed after durable write: {exc}"
        ) from exc
    if observed != text:
        raise BootTransactionError("boot-control re-read does not match written bytes")
    return observed


def _read_canonical_record(
    path: Path, *, expected_schema: int, context: str
) -> dict[str, object]:
    """Fail-closed read of one canonical-JSON boot record."""
    location = Path(path)
    try:
        if location.is_symlink():
            raise BootTransactionError(f"{context} may not be a symbolic link")
        status = location.stat()
    except OSError as exc:
        raise BootTransactionError(f"{context} is not accessible: {exc}") from exc
    import stat as _stat

    if not _stat.S_ISREG(status.st_mode):
        raise BootTransactionError(f"{context} must be a regular file")
    if status.st_size <= 0 or status.st_size > MAX_JOURNAL_BYTES:
        raise BootTransactionError(f"{context} size is outside Greia bounds")
    if _stat.S_IMODE(status.st_mode) != JOURNAL_FILE_MODE:
        raise BootTransactionError(f"{context} must be owner-only mode 0600")
    if status.st_uid != os.geteuid():
        raise BootTransactionError(f"{context} ownership is not authoritative")
    try:
        raw_bytes = location.read_bytes()
    except OSError as exc:
        raise BootTransactionError(f"{context} is unreadable") from exc
    try:
        raw = json.loads(raw_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BootTransactionError(f"{context} is not valid JSON") from exc
    if not isinstance(raw, dict):
        raise BootTransactionError(f"{context} must be a JSON object")
    if raw.get("schema_version") != expected_schema:
        raise BootTransactionError(f"{context} schema is unsupported")
    return raw


# ---------------------------------------------------------------------------
# BootArtifactSet: semantic boot roles bound to layout + finalizer receipt
# ---------------------------------------------------------------------------


class BootArtifactRole(StrEnum):
    GENERIC_KERNEL = "generic-kernel"
    GENERIC_INITRAMFS = "generic-initramfs"


#: Boot backends carrying A/B transaction semantics.
AB_BOOT_BACKENDS = frozenset({"grub-ab-v1", "pi-tryboot-ab-v1"})

#: Stable per-slot GRUB entries owned by the x86 adapter (never Parent input).
GRUB_ENTRY_NAMES = {"A": "greia-a", "B": "greia-b"}

#: Adapter-owned generic kernel/initramfs paths inside a system slot.
SLOT_KERNEL_PATH = "boot/vmlinuz-greia"
SLOT_INITRAMFS_PATH = "boot/initramfs-greia.img"

#: Pi BOOT partition roles owned by the Pi adapter (never Parent input).
PI_BOOT_ROLES = {"A": "BOOT_A", "B": "BOOT_B"}

#: Pi boot-control partition numbers for BOOT_A/BOOT_B (MBR first candidate).
PI_BOOT_PARTITIONS = {"A": 2, "B": 3}


@dataclass(frozen=True, slots=True)
class BootArtifactSet:
    """Semantic boot facts for one slot: roles plus root/release identity.

    Construct only from a trusted :class:`InstalledLayoutRecord` plus the
    slot's :class:`FinalizationReceipt` (see :meth:`from_finalization`).
    There is deliberately no constructor taking a boot entry name, a kernel
    path or a partition path: backends resolve adapter-owned locations from
    the semantic slot alone.
    """

    slot: str
    layout_id: str
    boot_backend: str
    generic_kernel_sha256: str
    generic_initramfs_sha256: str
    root_partuuid: str
    root_filesystem_uuid: str
    release_id: str
    release_sequence: int

    def __post_init__(self) -> None:
        _require_slot(self.slot)
        _require_identifier(self.layout_id, field_name="layout_id", maximum=64)
        if self.boot_backend not in AB_BOOT_BACKENDS:
            raise BootArtifactError(
                f"boot_backend carries no A/B transaction semantics: {self.boot_backend!r}"
            )
        _require_hex64(self.generic_kernel_sha256, field_name="generic_kernel_sha256")
        _require_hex64(
            self.generic_initramfs_sha256, field_name="generic_initramfs_sha256"
        )
        # root_partuuid is the observed kernel identity: GPT GUID or MBR
        # <sig>-<NN> (T1-IDENT). Filesystem UUIDs stay canonical UUIDs.
        object.__setattr__(
            self, "root_partuuid",
            _require_root_partuuid(self.root_partuuid, field_name="root_partuuid"),
        )
        _require_canonical_uuid(
            self.root_filesystem_uuid, field_name="root_filesystem_uuid"
        )
        _require_identifier(self.release_id, field_name="release_id", maximum=96)
        if (
            isinstance(self.release_sequence, bool)
            or not isinstance(self.release_sequence, int)
            or not 0 <= self.release_sequence <= 2_147_483_647
        ):
            raise BootArtifactError("release_sequence is outside Greia bounds")

    @classmethod
    def from_finalization(cls, *, receipt: object, record: object) -> "BootArtifactSet":
        """Bind the slot's finalizer receipt to its layout root identity."""
        slot = getattr(receipt, "slot", None)
        _require_slot(slot, field_name="receipt slot")
        layout_id = getattr(receipt, "layout_id", None)
        if getattr(record, "layout_id", None) != layout_id:
            raise BootArtifactError("receipt layout does not match the layout record")
        system_b = getattr(record, "system_b", None)
        if system_b is None:
            raise BootArtifactError("single-root layouts carry no boot artifact set")
        boot_backend = getattr(record, "boot_backend", None)
        if boot_backend not in AB_BOOT_BACKENDS:
            raise BootArtifactError("layout boot backend carries no A/B semantics")
        if slot == "A":
            root = getattr(record, "system_a")
        else:
            root = system_b
        return cls(
            slot=str(slot),
            layout_id=str(layout_id),
            boot_backend=str(boot_backend),
            generic_kernel_sha256=getattr(receipt, "generic_kernel_sha256"),
            generic_initramfs_sha256=getattr(receipt, "host_initramfs_sha256"),
            root_partuuid=root.partuuid,
            root_filesystem_uuid=root.filesystem_uuid,
            release_id=getattr(receipt, "release_id"),
            release_sequence=getattr(receipt, "release_sequence"),
        )

    @property
    def role_digests(self) -> dict[str, str]:
        """Semantic role -> digest map consumed by boot staging verification."""
        return {
            BootArtifactRole.GENERIC_KERNEL.value: self.generic_kernel_sha256,
            BootArtifactRole.GENERIC_INITRAMFS.value: self.generic_initramfs_sha256,
        }

    @property
    def grub_entry_name(self) -> str:
        """Stable per-slot GRUB entry owned by the x86 adapter."""
        if self.boot_backend != "grub-ab-v1":
            raise BootArtifactError("GRUB entry names exist only on the GRUB backend")
        return GRUB_ENTRY_NAMES[self.slot]

    @property
    def pi_boot_role(self) -> str:
        """Pi BOOT partition role owned by the Pi adapter."""
        if self.boot_backend != "pi-tryboot-ab-v1":
            raise BootArtifactError("Pi BOOT roles exist only on the Pi backend")
        return PI_BOOT_ROLES[self.slot]

    @property
    def kernel_path(self) -> str:
        """Adapter-owned slot-local kernel path (identical for every slot)."""
        return SLOT_KERNEL_PATH

    @property
    def initramfs_path(self) -> str:
        """Adapter-owned slot-local initramfs path (identical for every slot)."""
        return SLOT_INITRAMFS_PATH

    def kernel_cmdline_root(self) -> str:
        """Adapter-owned root binding derived from the layout PARTUUID."""
        return f"root=PARTUUID={self.root_partuuid}"

    def as_dict(self) -> dict[str, object]:
        return {
            "boot_backend": self.boot_backend,
            "generic_initramfs_sha256": self.generic_initramfs_sha256,
            "generic_kernel_sha256": self.generic_kernel_sha256,
            "layout_id": self.layout_id,
            "release_id": self.release_id,
            "release_sequence": self.release_sequence,
            "root_filesystem_uuid": self.root_filesystem_uuid,
            "root_partuuid": self.root_partuuid,
            "slot": self.slot,
        }


# ---------------------------------------------------------------------------
# Initramfs roles: BASE / FINALIZED_GENERIC / HOST_FAST
# ---------------------------------------------------------------------------


class InitramfsRole(StrEnum):
    BASE = "base"
    FINALIZED_GENERIC = "finalized-generic"
    HOST_FAST = "host-fast"


#: Producer binding the deterministic BASE initramfs (signed release input).
BASE_INITRAMFS_PRODUCER = "release-builder-v1"

#: Producer binding the required FINALIZED_GENERIC artifact (SlotFinalizer).
FINALIZED_GENERIC_PRODUCER = "slot-finalizer-v1"

#: Producer binding the optional HOST_FAST derivative (accepted hardware only).
HOST_FAST_PRODUCER = "host-derivative-v1"


@dataclass(frozen=True, slots=True)
class InitramfsArtifact:
    """One initramfs artifact bound to its role, producer and release.

    ``BASE`` is deterministic build input (slot-independent). Every accepted
    slot keeps its ``FINALIZED_GENERIC`` artifact generated by the
    SlotFinalizer. ``HOST_FAST`` is an optional later derivative generated on
    accepted actual hardware: it records the ``FINALIZED_GENERIC`` digest it
    was derived from and is never the sole recovery path (see
    :func:`require_recovery_path`).
    """

    role: InitramfsRole
    sha256: str
    producer: str
    release_id: str
    release_sequence: int
    derived_from_sha256: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.role, InitramfsRole):
            raise BootArtifactError(f"initramfs role is unknown: {self.role!r}")
        _require_hex64(self.sha256, field_name="initramfs sha256")
        expected_producer = {
            InitramfsRole.BASE: BASE_INITRAMFS_PRODUCER,
            InitramfsRole.FINALIZED_GENERIC: FINALIZED_GENERIC_PRODUCER,
            InitramfsRole.HOST_FAST: HOST_FAST_PRODUCER,
        }[self.role]
        if self.producer != expected_producer:
            raise BootArtifactError(
                f"initramfs producer {self.producer!r} does not own role {self.role.value!r}"
            )
        _require_identifier(self.release_id, field_name="release_id", maximum=96)
        if (
            isinstance(self.release_sequence, bool)
            or not isinstance(self.release_sequence, int)
            or not 0 <= self.release_sequence <= 2_147_483_647
        ):
            raise BootArtifactError("release_sequence is outside Greia bounds")
        if self.role is InitramfsRole.HOST_FAST:
            if self.derived_from_sha256 is None:
                raise BootArtifactError(
                    "HOST_FAST must record the FINALIZED_GENERIC digest it derives from"
                )
            _require_hex64(
                self.derived_from_sha256, field_name="host-fast derived_from_sha256"
            )
        elif self.derived_from_sha256 is not None:
            raise BootArtifactError(
                "only HOST_FAST may record a derivation source digest"
            )

    @classmethod
    def finalized_generic_from_receipt(cls, *, receipt: object) -> "InitramfsArtifact":
        """Bind the required per-slot artifact from the finalizer receipt."""
        return cls(
            role=InitramfsRole.FINALIZED_GENERIC,
            sha256=getattr(receipt, "host_initramfs_sha256"),
            producer=FINALIZED_GENERIC_PRODUCER,
            release_id=getattr(receipt, "release_id"),
            release_sequence=getattr(receipt, "release_sequence"),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "derived_from_sha256": self.derived_from_sha256,
            "producer": self.producer,
            "release_id": self.release_id,
            "release_sequence": self.release_sequence,
            "role": self.role.value,
            "sha256": self.sha256,
        }


def require_recovery_path(artifacts: object) -> InitramfsArtifact:
    """Prove a recovery path exists that does not depend on HOST_FAST.

    Returns the ``FINALIZED_GENERIC`` artifact. A set holding only
    ``HOST_FAST`` (or nothing) fails closed: the optional derivative is
    never the sole recovery path.
    """
    candidates = list(artifacts)  # type: ignore[arg-type]
    for artifact in candidates:
        if getattr(artifact, "role", None) is InitramfsRole.FINALIZED_GENERIC:
            return artifact
    raise BootArtifactError(
        "no FINALIZED_GENERIC artifact: HOST_FAST alone is never a recovery path"
    )


# ---------------------------------------------------------------------------
# BootTransactionBackend protocol (one interface for x86 GRUB and Pi tryboot)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class BootBackendState:
    """Observable backend snapshot: default, one-shot and last booted slot."""

    backend_id: str
    default_slot: str
    one_shot_slot: str | None
    last_booted_slot: str | None

    def __post_init__(self) -> None:
        if self.backend_id not in AB_BOOT_BACKENDS:
            raise BootTransactionError(
                f"backend carries no A/B transaction semantics: {self.backend_id!r}"
            )
        _require_slot(self.default_slot, field_name="default_slot")
        if self.one_shot_slot is not None:
            _require_slot(self.one_shot_slot, field_name="one_shot_slot")
            if self.one_shot_slot == self.default_slot:
                raise BootTransactionError("one-shot state must be candidate-only")
        if self.last_booted_slot is not None:
            _require_slot(self.last_booted_slot, field_name="last_booted_slot")

    def as_dict(self) -> dict[str, object]:
        return {
            "backend_id": self.backend_id,
            "default_slot": self.default_slot,
            "last_booted_slot": self.last_booted_slot,
            "one_shot_slot": self.one_shot_slot,
        }


@dataclass(frozen=True, slots=True)
class RollbackReadiness:
    """Whether a failed candidate provably returns to the accepted default."""

    ready: bool
    accepted_slot: str
    reason: str


class BootTransactionBackend(Protocol):
    """Privileged A/B boot-selection boundary behind one semantic interface."""

    @property
    def backend_id(self) -> str: ...

    def inspect(self) -> BootBackendState: ...

    def arm_one_shot(self, candidate: str) -> BootBackendState: ...

    def observe_booted_slot(self) -> str: ...

    def commit_accepted(self, slot: str) -> BootBackendState: ...

    def verify_rollback_ready(self) -> RollbackReadiness: ...

    def reconcile(self, observed_booted: str) -> BootBackendState: ...


# ---------------------------------------------------------------------------
# Fake GRUB backend (x86): stable A/B entries, candidate-only one-shot
# ---------------------------------------------------------------------------


_GRUB_STATE_NAME = "grub-boot-state.json"


@dataclass(frozen=True, slots=True)
class FakeGrubBackend:
    """File-backed GRUB A/B stand-in: stable entries, consumed one-shot.

    ``grub-boot-state.json`` carries ``default_slot`` (persistent default,
    stays accepted until health commit), ``next_entry`` (candidate-only
    one-shot) and ``last_booted``. :meth:`simulate_reboot` stands in for
    firmware: a set one-shot boots the candidate exactly once and is then
    consumed, so an unhealthy candidate provably falls back to the default.
    """

    state_dir: Path

    @property
    def backend_id(self) -> str:
        return "grub-ab-v1"

    @classmethod
    def initialize(cls, state_dir: Path, *, default_slot: str) -> "FakeGrubBackend":
        """Create backend state with the accepted slot as persistent default."""
        backend = cls(state_dir=Path(state_dir))
        _require_slot(default_slot, field_name="default_slot")
        backend._write_state(
            {"default_slot": default_slot, "last_booted": None, "next_entry": None}
        )
        return backend

    @classmethod
    def attach(cls, state_dir: Path) -> "FakeGrubBackend":
        """Re-attach to existing backend state (reboot/crash survival)."""
        backend = cls(state_dir=Path(state_dir))
        backend.inspect()
        return backend

    def entry_name(self, slot: str) -> str:
        """Stable adapter-owned GRUB entry for a semantic slot."""
        _require_slot(slot)
        return GRUB_ENTRY_NAMES[slot]

    def inspect(self) -> BootBackendState:
        raw = _read_canonical_record(
            self._state_path, expected_schema=BOOT_RECORD_SCHEMA_VERSION,
            context="GRUB boot state",
        )
        if set(raw) != {"default_slot", "last_booted", "next_entry", "schema_version"}:
            raise BootTransactionError("GRUB boot state fields are invalid")
        default = raw["default_slot"]
        one_shot = raw["next_entry"]
        last_booted = raw["last_booted"]
        if one_shot is not None and not isinstance(one_shot, str):
            raise BootTransactionError("GRUB one-shot entry is invalid")
        if last_booted is not None and not isinstance(last_booted, str):
            raise BootTransactionError("GRUB last-booted entry is invalid")
        return BootBackendState(
            backend_id=self.backend_id,
            default_slot=_require_slot(default, field_name="default_slot"),
            one_shot_slot=one_shot,
            last_booted_slot=last_booted,
        )

    def arm_one_shot(self, candidate: str) -> BootBackendState:
        """Arm a candidate-only one-shot; the persistent default is untouched."""
        _require_slot(candidate, field_name="candidate")
        state = self.inspect()
        if candidate == state.default_slot:
            raise BootTransactionError(
                "refusing to one-shot the persistent default: "
                "one-shot state is candidate-only"
            )
        if state.one_shot_slot is not None:
            raise BootTransactionError(
                "a one-shot is already armed; reconcile before re-arming"
            )
        self._write_state(
            {
                "default_slot": state.default_slot,
                "last_booted": state.last_booted_slot,
                "next_entry": candidate,
            }
        )
        return self.inspect()

    def observe_booted_slot(self) -> str:
        state = self.inspect()
        if state.last_booted_slot is None:
            raise BootTransactionError("no authoritative boot observation yet")
        return state.last_booted_slot

    def commit_accepted(self, slot: str) -> BootBackendState:
        """Persist a new default only for the slot that actually booted."""
        _require_slot(slot)
        state = self.inspect()
        if state.last_booted_slot != slot:
            raise BootTransactionError(
                "refusing to commit a default that never booted: "
                "health commit requires the candidate to have booted"
            )
        self._write_state(
            {"default_slot": slot, "last_booted": state.last_booted_slot,
             "next_entry": None}
        )
        return self.inspect()

    def verify_rollback_ready(self) -> RollbackReadiness:
        state = self.inspect()
        if state.one_shot_slot is not None:
            return RollbackReadiness(
                ready=False,
                accepted_slot=state.default_slot,
                reason="a one-shot is still armed; reconcile first",
            )
        if state.last_booted_slot != state.default_slot:
            return RollbackReadiness(
                ready=False,
                accepted_slot=state.default_slot,
                reason="machine is not running its persistent default",
            )
        return RollbackReadiness(
            ready=True,
            accepted_slot=state.default_slot,
            reason="persistent default is booted and no one-shot is armed",
        )

    def reconcile(self, observed_booted: str) -> BootBackendState:
        """Fold an authoritative boot observation: the one-shot is consumed."""
        _require_slot(observed_booted, field_name="observed_booted")
        state = self.inspect()
        self._write_state(
            {
                "default_slot": state.default_slot,
                "last_booted": observed_booted,
                "next_entry": None,
            }
        )
        return self.inspect()

    def simulate_reboot(self) -> str:
        """R0/R1 test hook standing in for firmware boot selection.

        A set one-shot boots the candidate exactly once and is consumed; an
        unhealthy candidate therefore falls back to the persistent default
        on the following boot without any backend mutation.
        """
        state = self.inspect()
        booted = state.one_shot_slot if state.one_shot_slot is not None else state.default_slot
        self._write_state(
            {
                "default_slot": state.default_slot,
                "last_booted": booted,
                "next_entry": None,
            }
        )
        return booted

    @property
    def _state_path(self) -> Path:
        return Path(self.state_dir) / _GRUB_STATE_NAME

    def _write_state(self, record: dict[str, object]) -> None:
        payload = {"schema_version": BOOT_RECORD_SCHEMA_VERSION, **record}
        _atomic_write_file(self._state_path, _canonical_bytes(payload), mode=JOURNAL_FILE_MODE)


# ---------------------------------------------------------------------------
# Fake Pi tryboot backend: BOOT_A/BOOT_B pairs, durable autoboot discipline
# ---------------------------------------------------------------------------


_PI_CONTROL_DIRNAME = "boot_control"
_PI_AUTOBOOT_NAME = "autoboot.txt"
_PI_TRYBOOT_NAME = "tryboot.json"
_PI_LAST_BOOTED_NAME = "last_booted"
_PI_MANIFEST_NAME = "boot-manifest.json"
_PI_KERNEL_NAME = "kernel.img"
_PI_INITRAMFS_NAME = "initramfs.img"


def _pi_autoboot_text(default_slot: str) -> str:
    _require_slot(default_slot, field_name="default_slot")
    return f"boot_partition={PI_BOOT_PARTITIONS[default_slot]}\n"


def _parse_pi_autoboot(text: str) -> str:
    for partition, slot in (("2", "A"), ("3", "B")):
        if text == f"boot_partition={partition}\n":
            return slot
    raise BootTransactionError(
        "Pi boot control is corrupt: autoboot.txt must map exactly one boot partition"
    )


@dataclass(frozen=True, slots=True)
class FakePiTrybootBackend:
    """File-backed Pi tryboot stand-in: BOOT_A/BOOT_B pairs, tryboot one-shot.

    ``boot_control/autoboot.txt`` is the durable default mapping written with
    the layered discipline (new file + fsync + rename + dir-sync + sync +
    re-read verify); ``tryboot.json`` is the candidate-only one-shot. Staged
    BOOT pairs carry a manifest binding kernel/initramfs digests to the
    release so a failed candidate never mutates the accepted pair. There is
    deliberately no EEPROM surface anywhere in this backend: routine
    operation cannot rewrite EEPROM by construction.
    """

    state_dir: Path

    @property
    def backend_id(self) -> str:
        return "pi-tryboot-ab-v1"

    @classmethod
    def initialize(cls, state_dir: Path, *, default_slot: str) -> "FakePiTrybootBackend":
        """Create backend state with the accepted slot as durable default."""
        backend = cls(state_dir=Path(state_dir))
        _require_slot(default_slot, field_name="default_slot")
        control = backend._control_dir
        control.mkdir(parents=True, exist_ok=True)
        _durable_write_text(
            control / _PI_AUTOBOOT_NAME, _pi_autoboot_text(default_slot),
            mode=JOURNAL_FILE_MODE,
        )
        return backend

    @classmethod
    def attach(cls, state_dir: Path) -> "FakePiTrybootBackend":
        """Re-attach to existing backend state (reboot/crash survival)."""
        backend = cls(state_dir=Path(state_dir))
        backend.inspect()
        return backend

    def boot_role(self, slot: str) -> str:
        """Adapter-owned BOOT partition role for a semantic slot."""
        _require_slot(slot)
        return PI_BOOT_ROLES[slot]

    def inspect(self) -> BootBackendState:
        try:
            text = (self._control_dir / _PI_AUTOBOOT_NAME).read_text(encoding="utf-8")
        except OSError as exc:
            raise BootTransactionError(
                f"Pi boot control is missing: autoboot.txt unreadable: {exc}"
            ) from exc
        default = _parse_pi_autoboot(text)
        one_shot: str | None = None
        tryboot_path = self._control_dir / _PI_TRYBOOT_NAME
        if tryboot_path.is_symlink():
            raise BootTransactionError("Pi tryboot flag may not be a symbolic link")
        if tryboot_path.exists():
            try:
                raw = json.loads(tryboot_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise BootTransactionError("Pi tryboot flag is corrupt") from exc
            if not isinstance(raw, dict) or set(raw) != {"candidate", "schema_version"}:
                raise BootTransactionError("Pi tryboot flag fields are invalid")
            if raw.get("schema_version") != BOOT_RECORD_SCHEMA_VERSION:
                raise BootTransactionError("Pi tryboot flag schema is unsupported")
            one_shot = _require_slot(raw.get("candidate"), field_name="candidate")
            if one_shot == default:
                raise BootTransactionError("Pi one-shot state must be candidate-only")
        last_booted: str | None = None
        last_path = self._control_dir / _PI_LAST_BOOTED_NAME
        if last_path.exists():
            if last_path.is_symlink():
                raise BootTransactionError("Pi last-booted marker may not be a symlink")
            try:
                marker = last_path.read_text(encoding="utf-8")
            except OSError as exc:
                raise BootTransactionError("Pi last-booted marker is unreadable") from exc
            last_booted = _require_slot(marker.strip(), field_name="last_booted")
        return BootBackendState(
            backend_id=self.backend_id,
            default_slot=default,
            one_shot_slot=one_shot,
            last_booted_slot=last_booted,
        )

    def stage_candidate_boot(
        self,
        slot: str,
        *,
        kernel_bytes: bytes,
        initramfs_bytes: bytes,
        artifacts: BootArtifactSet,
    ) -> dict[str, str]:
        """Stage and verify the inactive BOOT pair against the artifact set.

        Digests must match the release-bound :class:`BootArtifactSet`; the
        accepted pair is never addressable here. Returns the staged manifest.
        """
        _require_slot(slot, field_name="candidate")
        if not isinstance(artifacts, BootArtifactSet):
            raise BootTransactionError("candidate boot staging requires an artifact set")
        if artifacts.slot != slot:
            raise BootArtifactError("artifact set slot does not match the staged pair")
        state = self.inspect()
        if slot == state.default_slot:
            raise BootTransactionError("refusing to stage the accepted BOOT pair")
        if not kernel_bytes or not initramfs_bytes:
            raise BootTransactionError("candidate boot bytes are empty")
        if len(kernel_bytes) > 64 * 1024 * 1024 or len(initramfs_bytes) > 128 * 1024 * 1024:
            raise BootTransactionError("candidate boot bytes exceed Greia bounds")
        if hashlib.sha256(kernel_bytes).hexdigest() != artifacts.generic_kernel_sha256:
            raise BootTransactionError("candidate kernel does not match the artifact set")
        if (
            hashlib.sha256(initramfs_bytes).hexdigest()
            != artifacts.generic_initramfs_sha256
        ):
            raise BootTransactionError("candidate initramfs does not match the artifact set")
        pair_dir = self._pair_dir(slot)
        pair_dir.mkdir(parents=True, exist_ok=True)
        _durable_write_bytes(pair_dir / _PI_KERNEL_NAME, kernel_bytes)
        _durable_write_bytes(pair_dir / _PI_INITRAMFS_NAME, initramfs_bytes)
        manifest = {
            "boot_role": PI_BOOT_ROLES[slot],
            "generic_initramfs_sha256": artifacts.generic_initramfs_sha256,
            "generic_kernel_sha256": artifacts.generic_kernel_sha256,
            "release_id": artifacts.release_id,
            "release_sequence": artifacts.release_sequence,
            "schema_version": BOOT_RECORD_SCHEMA_VERSION,
            "slot": slot,
        }
        _durable_write_text(
            pair_dir / _PI_MANIFEST_NAME,
            json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n",
            mode=JOURNAL_FILE_MODE,
        )
        return manifest

    def verify_boot_pair(self, slot: str, artifacts: BootArtifactSet) -> None:
        """Re-read a staged BOOT pair and require artifact-set agreement."""
        _require_slot(slot)
        if not isinstance(artifacts, BootArtifactSet) or artifacts.slot != slot:
            raise BootArtifactError("artifact set slot does not match the BOOT pair")
        pair_dir = self._pair_dir(slot)
        try:
            manifest_raw = (pair_dir / _PI_MANIFEST_NAME).read_text(encoding="utf-8")
            manifest = json.loads(manifest_raw)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise BootTransactionError(f"BOOT_{slot} manifest is missing or corrupt") from exc
        for key in ("generic_kernel_sha256", "generic_initramfs_sha256"):
            role = (
                BootArtifactRole.GENERIC_KERNEL.value
                if key == "generic_kernel_sha256"
                else BootArtifactRole.GENERIC_INITRAMFS.value
            )
            if manifest.get(key) != artifacts.role_digests[role]:
                raise BootTransactionError(f"BOOT_{slot} manifest disagrees with artifacts")
        for name, digest in (
            (_PI_KERNEL_NAME, artifacts.generic_kernel_sha256),
            (_PI_INITRAMFS_NAME, artifacts.generic_initramfs_sha256),
        ):
            try:
                content = (pair_dir / name).read_bytes()
            except OSError as exc:
                raise BootTransactionError(f"BOOT_{slot}/{name} is unreadable") from exc
            if hashlib.sha256(content).hexdigest() != digest:
                raise BootTransactionError(f"BOOT_{slot}/{name} digest mismatch")

    def arm_one_shot(self, candidate: str) -> BootBackendState:
        """Arm a candidate-only tryboot; the durable default is untouched."""
        _require_slot(candidate, field_name="candidate")
        state = self.inspect()
        if candidate == state.default_slot:
            raise BootTransactionError(
                "refusing to tryboot the durable default: "
                "one-shot state is candidate-only"
            )
        if state.one_shot_slot is not None:
            raise BootTransactionError(
                "a tryboot is already armed; reconcile before re-arming"
            )
        manifest_path = self._pair_dir(candidate) / _PI_MANIFEST_NAME
        if not manifest_path.is_file() or manifest_path.is_symlink():
            raise BootTransactionError(
                "refusing to tryboot an unstaged BOOT pair: "
                "stage and verify the candidate first"
            )
        _durable_write_text(
            self._control_dir / _PI_TRYBOOT_NAME,
            json.dumps(
                {"candidate": candidate, "schema_version": BOOT_RECORD_SCHEMA_VERSION},
                sort_keys=True,
            )
            + "\n",
            mode=JOURNAL_FILE_MODE,
        )
        return self.inspect()

    def observe_booted_slot(self) -> str:
        state = self.inspect()
        if state.last_booted_slot is None:
            raise BootTransactionError("no authoritative boot observation yet")
        return state.last_booted_slot

    def commit_accepted(self, slot: str) -> BootBackendState:
        """Durable-write a new autoboot mapping only for the slot that booted."""
        _require_slot(slot)
        state = self.inspect()
        if state.last_booted_slot != slot:
            raise BootTransactionError(
                "refusing to commit a default that never booted: "
                "health commit requires the candidate to have booted"
            )
        _durable_write_text(
            self._control_dir / _PI_AUTOBOOT_NAME, _pi_autoboot_text(slot),
            mode=JOURNAL_FILE_MODE,
        )
        tryboot_path = self._control_dir / _PI_TRYBOOT_NAME
        tryboot_path.unlink(missing_ok=True)
        _fsync_directory(self._control_dir)
        return self.inspect()

    def verify_rollback_ready(self) -> RollbackReadiness:
        state = self.inspect()
        if state.one_shot_slot is not None:
            return RollbackReadiness(
                ready=False,
                accepted_slot=state.default_slot,
                reason="a tryboot is still armed; reconcile first",
            )
        if state.last_booted_slot != state.default_slot:
            return RollbackReadiness(
                ready=False,
                accepted_slot=state.default_slot,
                reason="machine is not running its durable default",
            )
        return RollbackReadiness(
            ready=True,
            accepted_slot=state.default_slot,
            reason="durable default is booted and no tryboot is armed",
        )

    def reconcile(self, observed_booted: str) -> BootBackendState:
        """Fold an authoritative boot observation: the tryboot is consumed."""
        _require_slot(observed_booted, field_name="observed_booted")
        self.inspect()
        tryboot_path = self._control_dir / _PI_TRYBOOT_NAME
        tryboot_path.unlink(missing_ok=True)
        _durable_write_text(
            self._control_dir / _PI_LAST_BOOTED_NAME, f"{observed_booted}\n",
            mode=JOURNAL_FILE_MODE,
        )
        return self.inspect()

    def simulate_reboot(self) -> str:
        """R0/R1 test hook standing in for Pi firmware boot selection.

        An armed tryboot boots the candidate exactly once and the one-shot
        state clears, so normal boot returns to the accepted default unless
        the candidate is committed.
        """
        state = self.inspect()
        booted = state.one_shot_slot if state.one_shot_slot is not None else state.default_slot
        tryboot_path = self._control_dir / _PI_TRYBOOT_NAME
        tryboot_path.unlink(missing_ok=True)
        _durable_write_text(
            self._control_dir / _PI_LAST_BOOTED_NAME, f"{booted}\n",
            mode=JOURNAL_FILE_MODE,
        )
        return booted

    @property
    def _control_dir(self) -> Path:
        return Path(self.state_dir) / _PI_CONTROL_DIRNAME

    def _pair_dir(self, slot: str) -> Path:
        return Path(self.state_dir) / f"boot_{slot.lower()}"


def _durable_write_bytes(path: Path, payload: bytes) -> None:
    """Layered binary durable write with re-read verification."""
    location = Path(path)
    location.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{location.name}.", dir=location.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, JOURNAL_FILE_MODE)
        os.replace(temporary, location)
        _fsync_directory(location.parent)
        os.sync()
    finally:
        temporary.unlink(missing_ok=True)
    try:
        observed = location.read_bytes()
    except OSError as exc:
        raise BootTransactionError(
            f"staged boot bytes re-read failed: {exc}"
        ) from exc
    if observed != payload:
        raise BootTransactionError("staged boot bytes re-read mismatch")


# ---------------------------------------------------------------------------
# Crash-reconcilable transaction journal (PERSIST-side, root-owned)
# ---------------------------------------------------------------------------


class BootTransactionState(StrEnum):
    FIRST_INSTALL_PENDING = "first_install_pending"
    UPDATE_STAGED = "update_staged"
    ONE_SHOT_ARMED = "one_shot_armed"
    CANDIDATE_BOOTING = "candidate_booting"
    ACCEPTED = "accepted"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


_TERMINAL_STATES = frozenset(
    {
        BootTransactionState.ACCEPTED,
        BootTransactionState.ROLLED_BACK,
        BootTransactionState.FAILED,
    }
)

_ALLOWED_JOURNAL_TRANSITIONS: dict[BootTransactionState, frozenset[BootTransactionState]] = {
    BootTransactionState.FIRST_INSTALL_PENDING: frozenset(
        {
            BootTransactionState.CANDIDATE_BOOTING,
            BootTransactionState.FAILED,
        }
    ),
    BootTransactionState.UPDATE_STAGED: frozenset(
        {
            BootTransactionState.ONE_SHOT_ARMED,
            BootTransactionState.CANDIDATE_BOOTING,
            BootTransactionState.FAILED,
        }
    ),
    BootTransactionState.ONE_SHOT_ARMED: frozenset(
        {
            BootTransactionState.CANDIDATE_BOOTING,
            BootTransactionState.ROLLED_BACK,
            BootTransactionState.FAILED,
        }
    ),
    BootTransactionState.CANDIDATE_BOOTING: frozenset(
        {
            BootTransactionState.ACCEPTED,
            BootTransactionState.ROLLED_BACK,
            BootTransactionState.FAILED,
        }
    ),
    BootTransactionState.ACCEPTED: frozenset(),
    BootTransactionState.ROLLED_BACK: frozenset(),
    BootTransactionState.FAILED: frozenset(),
}


@dataclass(frozen=True, slots=True)
class JournalTransition:
    seq: int
    state: BootTransactionState
    note: str
    actor: str

    def as_dict(self) -> dict[str, object]:
        return {
            "actor": self.actor,
            "note": self.note,
            "seq": self.seq,
            "state": self.state.value,
        }


@dataclass(frozen=True, slots=True)
class ReconcileDecision:
    """Crash-reconcile outcome: a transition to record, or None when steady."""

    transition: BootTransactionState | None
    explanation: str


@dataclass
class BootTransactionJournal:
    """One crash-reconcilable boot transaction bound to release and slots.

    The journal file is rewritten atomically on every transition (bounded
    evidence, at most ``MAX_JOURNAL_TRANSITIONS`` entries). Only
    ``actor="platform"`` is accepted: Parent, Activity or installer-UI input
    can never write transaction state.
    """

    journal_dir: Path
    transaction_id: str
    first_install: bool
    layout_id: str
    boot_backend: str
    release_id: str
    release_sequence: int
    candidate_slot: str
    accepted_slot: str
    state: BootTransactionState = BootTransactionState.UPDATE_STAGED
    transitions: tuple[JournalTransition, ...] = ()

    def __post_init__(self) -> None:
        _require_identifier(
            self.transaction_id, field_name="transaction_id", maximum=64
        )
        _require_identifier(self.layout_id, field_name="layout_id", maximum=64)
        if self.boot_backend not in AB_BOOT_BACKENDS:
            raise BootJournalError("journal boot backend carries no A/B semantics")
        _require_identifier(self.release_id, field_name="release_id", maximum=96)
        if (
            isinstance(self.release_sequence, bool)
            or not isinstance(self.release_sequence, int)
            or not 0 <= self.release_sequence <= 2_147_483_647
        ):
            raise BootJournalError("release_sequence is outside Greia bounds")
        _require_slot(self.candidate_slot, field_name="candidate_slot")
        _require_slot(self.accepted_slot, field_name="accepted_slot")
        if not self.first_install and self.candidate_slot == self.accepted_slot:
            raise BootJournalError("an update candidate must differ from the accepted slot")
        if self.first_install and (
            self.candidate_slot != "A" or self.accepted_slot != "A"
        ):
            raise BootJournalError("first install always installs and boots slot A")
        if not isinstance(self.state, BootTransactionState):
            raise BootJournalError("journal state is unknown")
        if len(self.transitions) > MAX_JOURNAL_TRANSITIONS:
            raise BootJournalError("journal transition evidence exceeds Greia bounds")

    @classmethod
    def begin_update(
        cls,
        journal_dir: Path,
        *,
        layout_id: str,
        boot_backend: str,
        release_id: str,
        release_sequence: int,
        candidate_slot: str,
        accepted_slot: str,
    ) -> "BootTransactionJournal":
        """Open an update transaction; fails when one is already active."""
        journal = cls(
            journal_dir=Path(journal_dir),
            transaction_id=uuid.uuid4().hex,
            first_install=False,
            layout_id=layout_id,
            boot_backend=boot_backend,
            release_id=release_id,
            release_sequence=release_sequence,
            candidate_slot=candidate_slot,
            accepted_slot=accepted_slot,
            state=BootTransactionState.UPDATE_STAGED,
            transitions=(
                JournalTransition(
                    seq=0, state=BootTransactionState.UPDATE_STAGED,
                    note="candidate staged and verified", actor="platform",
                ),
            ),
        )
        journal._claim_active()
        journal.save()
        return journal

    @classmethod
    def begin_first_install(
        cls,
        journal_dir: Path,
        *,
        layout_id: str,
        boot_backend: str,
        release_id: str,
        release_sequence: int,
    ) -> "BootTransactionJournal":
        """Open the first-install transaction (SYSTEM_A, default A)."""
        journal = cls(
            journal_dir=Path(journal_dir),
            transaction_id=uuid.uuid4().hex,
            first_install=True,
            layout_id=layout_id,
            boot_backend=boot_backend,
            release_id=release_id,
            release_sequence=release_sequence,
            candidate_slot="A",
            accepted_slot="A",
            state=BootTransactionState.FIRST_INSTALL_PENDING,
            transitions=(
                JournalTransition(
                    seq=0, state=BootTransactionState.FIRST_INSTALL_PENDING,
                    note="SYSTEM_A installed with A as default", actor="platform",
                ),
            ),
        )
        journal._claim_active()
        journal.save()
        return journal

    @classmethod
    def load(cls, journal_dir: Path) -> "BootTransactionJournal":
        """Fail-closed load: corrupt journals raise, they never parse leniently."""
        try:
            raw = _read_canonical_record(
                Path(journal_dir) / JOURNAL_FILE_NAME,
                expected_schema=BOOT_RECORD_SCHEMA_VERSION,
                context="boot transaction journal",
            )
        except BootTransactionError as exc:
            raise BootJournalError(
                f"boot transaction journal is not authoritative: {exc}"
            ) from exc
        expected = {
            "accepted_slot", "boot_backend", "candidate_slot", "first_install",
            "layout_id", "release_id", "release_sequence", "schema_version",
            "state", "transaction_id", "transitions",
        }
        if set(raw) != expected:
            raise BootJournalError("journal fields are invalid")
        try:
            state = BootTransactionState(raw["state"])
        except ValueError as exc:
            raise BootJournalError("journal state is unknown") from exc
        transitions_raw = raw["transitions"]
        if not isinstance(transitions_raw, list) or not transitions_raw:
            raise BootJournalError("journal transition evidence is invalid")
        transitions: list[JournalTransition] = []
        for index, entry in enumerate(transitions_raw):
            if not isinstance(entry, dict) or set(entry) != {"actor", "note", "seq", "state"}:
                raise BootJournalError("journal transition entry is invalid")
            try:
                entry_state = BootTransactionState(entry["state"])
            except ValueError as exc:
                raise BootJournalError("journal transition state is unknown") from exc
            note = entry["note"]
            if (
                not isinstance(note, str) or not note
                or len(note.encode("utf-8")) > MAX_TRANSITION_NOTE_BYTES
            ):
                raise BootJournalError("journal transition note exceeds Greia bounds")
            if entry["actor"] != "platform":
                raise BootJournalError("journal carries a non-platform actor")
            if entry["seq"] != index:
                raise BootJournalError("journal transition sequence is not dense")
            transitions.append(
                JournalTransition(seq=index, state=entry_state, note=note, actor="platform")
            )
        first_install = raw["first_install"]
        if not isinstance(first_install, bool):
            raise BootJournalError("journal first_install flag is invalid")
        journal = cls(
            journal_dir=Path(journal_dir),
            transaction_id=raw["transaction_id"],
            first_install=first_install,
            layout_id=raw["layout_id"],
            boot_backend=raw["boot_backend"],
            release_id=raw["release_id"],
            release_sequence=raw["release_sequence"],
            candidate_slot=raw["candidate_slot"],
            accepted_slot=raw["accepted_slot"],
            state=state,
            transitions=tuple(transitions),
        )
        if journal.transitions[-1].state is not state:
            raise BootJournalError("journal head does not match transition evidence")
        if stored_bytes_are_not_canonical(journal):
            raise BootJournalError("journal is not canonical JSON")
        return journal

    @property
    def journal_path(self) -> Path:
        return Path(self.journal_dir) / JOURNAL_FILE_NAME

    @property
    def is_terminal(self) -> bool:
        return self.state in _TERMINAL_STATES

    def record(self, state: BootTransactionState, note: str) -> None:
        """Append one platform-observed transition and persist it."""
        if not isinstance(state, BootTransactionState):
            raise BootJournalError("journal state is unknown")
        if state not in _ALLOWED_JOURNAL_TRANSITIONS[self.state]:
            raise BootJournalError(
                f"journal transition {self.state.value} -> {state.value} is not allowed"
            )
        if (
            not isinstance(note, str) or not note
            or len(note.encode("utf-8")) > MAX_TRANSITION_NOTE_BYTES
        ):
            raise BootJournalError("journal transition note exceeds Greia bounds")
        if len(self.transitions) >= MAX_JOURNAL_TRANSITIONS:
            raise BootJournalError("journal transition evidence exceeds Greia bounds")
        object.__setattr__(
            self, "transitions",
            self.transitions
            + (
                JournalTransition(
                    seq=len(self.transitions), state=state,
                    note=note, actor="platform",
                ),
            ),
        )
        object.__setattr__(self, "state", state)
        self.save()

    def reconcile(self, observed_booted: str | None) -> ReconcileDecision:
        """Decide the crash-recovery transition from an authoritative observation.

        Returns a transition to record, or ``None`` when the journal is
        already consistent with the observation. A missing/unknown
        observation never produces a transition: without authoritative boot
        evidence the journal refuses to guess.
        """
        if self.is_terminal:
            return ReconcileDecision(
                transition=None,
                explanation=f"journal is already terminal ({self.state.value})",
            )
        if observed_booted not in ("A", "B"):
            return ReconcileDecision(
                transition=None,
                explanation="no authoritative boot observation; refusing to guess",
            )
        observed = observed_booted
        if observed == self.candidate_slot:
            if self.state is BootTransactionState.CANDIDATE_BOOTING:
                return ReconcileDecision(
                    transition=None,
                    explanation="candidate booted; health commit owns acceptance",
                )
            return ReconcileDecision(
                transition=BootTransactionState.CANDIDATE_BOOTING,
                explanation=(
                    "authoritative boot of the candidate; "
                    "one-shot consumed, awaiting health commit"
                ),
            )
        if observed == self.accepted_slot and self.candidate_slot != self.accepted_slot:
            if self.state in (
                BootTransactionState.ONE_SHOT_ARMED,
                BootTransactionState.CANDIDATE_BOOTING,
            ):
                return ReconcileDecision(
                    transition=BootTransactionState.ROLLED_BACK,
                    explanation=(
                        "machine is on the accepted slot after a candidate "
                        "attempt; one-shot consumed, candidate abandoned"
                    ),
                )
            return ReconcileDecision(
                transition=None,
                explanation="still on the accepted slot; no candidate boot attempted",
            )
        if self.state in (
            BootTransactionState.ONE_SHOT_ARMED,
            BootTransactionState.CANDIDATE_BOOTING,
        ):
            return ReconcileDecision(
                transition=BootTransactionState.FAILED,
                explanation=(
                    "machine booted a slot that is neither candidate nor "
                    "accepted; failing closed for operator recovery"
                ),
            )
        return ReconcileDecision(
            transition=None,
            explanation="no candidate boot evidence; journal stays",
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "accepted_slot": self.accepted_slot,
            "boot_backend": self.boot_backend,
            "candidate_slot": self.candidate_slot,
            "first_install": self.first_install,
            "layout_id": self.layout_id,
            "release_id": self.release_id,
            "release_sequence": self.release_sequence,
            "schema_version": BOOT_RECORD_SCHEMA_VERSION,
            "state": self.state.value,
            "transaction_id": self.transaction_id,
            "transitions": [entry.as_dict() for entry in self.transitions],
        }

    def canonical_bytes(self) -> bytes:
        return _canonical_bytes(self.as_dict())

    def save(self) -> None:
        _atomic_write_file(self.journal_path, self.canonical_bytes(), mode=JOURNAL_FILE_MODE)

    def _claim_active(self) -> None:
        if self.journal_path.exists() and not self.journal_path.is_symlink():
            try:
                active = BootTransactionJournal.load(self.journal_dir)
            except BootJournalError:
                raise BootJournalError(
                    "a previous journal exists but is unreadable; "
                    "refusing to overwrite crash evidence"
                )
            if not active.is_terminal:
                raise BootJournalError(
                    "a boot transaction is already active; reconcile it first"
                )


def stored_bytes_are_not_canonical(journal: BootTransactionJournal) -> bool:
    """True when stored bytes are not this journal's canonical encoding."""
    try:
        stored = journal.journal_path.read_bytes()
    except OSError:
        return True
    return stored != journal.canonical_bytes()


# ---------------------------------------------------------------------------
# Coordinator: one backend interface, no platform conditionals
# ---------------------------------------------------------------------------


@dataclass
class BootTransactionCoordinator:
    """Drive journal + backend through the single backend protocol.

    All branching is on journal/backend state, never on platform identity:
    the same coordinator serves GRUB x86 and Pi tryboot backends
    polymorphically. Construction binds the candidate/accepted artifact
    sets; every transition is recorded with platform-observed evidence.
    """

    journal: BootTransactionJournal
    backend: BootTransactionBackend
    candidate_artifacts: BootArtifactSet
    accepted_artifacts: BootArtifactSet

    def __post_init__(self) -> None:
        if not isinstance(self.candidate_artifacts, BootArtifactSet):
            raise BootTransactionError("coordinator requires a candidate artifact set")
        if not isinstance(self.accepted_artifacts, BootArtifactSet):
            raise BootTransactionError("coordinator requires an accepted artifact set")
        journal = self.journal
        if self.candidate_artifacts.slot != journal.candidate_slot:
            raise BootTransactionError("candidate artifact slot does not match the journal")
        if self.accepted_artifacts.slot != journal.accepted_slot:
            raise BootTransactionError("accepted artifact slot does not match the journal")
        for artifacts in (self.candidate_artifacts, self.accepted_artifacts):
            if artifacts.layout_id != journal.layout_id:
                raise BootTransactionError("artifact layout does not match the journal")
            if artifacts.boot_backend != journal.boot_backend:
                raise BootTransactionError("artifact backend does not match the journal")
        if self.backend.backend_id != journal.boot_backend:
            raise BootTransactionError("backend does not match the journal backend")

    @classmethod
    def begin_update(
        cls,
        *,
        journal_dir: Path,
        backend: BootTransactionBackend,
        candidate_artifacts: BootArtifactSet,
        accepted_artifacts: BootArtifactSet,
        release_id: str,
        release_sequence: int,
    ) -> "BootTransactionCoordinator":
        """Open an update transaction bound to both artifact sets."""
        if candidate_artifacts.slot == accepted_artifacts.slot:
            raise BootTransactionError("an update candidate must differ from the accepted slot")
        if candidate_artifacts.layout_id != accepted_artifacts.layout_id:
            raise BootTransactionError("candidate and accepted layouts differ")
        journal = BootTransactionJournal.begin_update(
            journal_dir,
            layout_id=candidate_artifacts.layout_id,
            boot_backend=candidate_artifacts.boot_backend,
            release_id=release_id,
            release_sequence=release_sequence,
            candidate_slot=candidate_artifacts.slot,
            accepted_slot=accepted_artifacts.slot,
        )
        return cls(
            journal=journal, backend=backend,
            candidate_artifacts=candidate_artifacts,
            accepted_artifacts=accepted_artifacts,
        )

    @classmethod
    def begin_first_install(
        cls,
        *,
        journal_dir: Path,
        backend: BootTransactionBackend,
        artifact_a: BootArtifactSet,
    ) -> "BootTransactionCoordinator":
        """Open the first-install transaction (SYSTEM_A, default A)."""
        if artifact_a.slot != "A":
            raise BootTransactionError("first install always installs slot A")
        journal = BootTransactionJournal.begin_first_install(
            journal_dir,
            layout_id=artifact_a.layout_id,
            boot_backend=artifact_a.boot_backend,
            release_id=artifact_a.release_id,
            release_sequence=artifact_a.release_sequence,
        )
        return cls(
            journal=journal, backend=backend,
            candidate_artifacts=artifact_a, accepted_artifacts=artifact_a,
        )

    @classmethod
    def resume(
        cls,
        *,
        journal_dir: Path,
        backend: BootTransactionBackend,
        candidate_artifacts: BootArtifactSet,
        accepted_artifacts: BootArtifactSet,
    ) -> "BootTransactionCoordinator":
        """Re-attach to a persisted journal after reboot or crash."""
        return cls(
            journal=BootTransactionJournal.load(journal_dir),
            backend=backend,
            candidate_artifacts=candidate_artifacts,
            accepted_artifacts=accepted_artifacts,
        )

    def arm(self) -> BootBackendState:
        """Arm the candidate one-shot; first-install (default A) needs none."""
        state = self.backend.inspect()
        if self.journal.candidate_slot == state.default_slot:
            raise BootTransactionError(
                "candidate is already the persistent default; no one-shot required"
            )
        armed = self.backend.arm_one_shot(self.journal.candidate_slot)
        if self.journal.state is BootTransactionState.UPDATE_STAGED:
            self.journal.record(
                BootTransactionState.ONE_SHOT_ARMED,
                f"one-shot armed for slot {self.journal.candidate_slot}",
            )
        return armed

    def observe_boot(self) -> tuple[str, ReconcileDecision]:
        """Fold the authoritative booted slot into backend and journal."""
        observed = self.backend.observe_booted_slot()
        self.backend.reconcile(observed)
        decision = self.journal.reconcile(observed)
        if decision.transition is not None:
            self.journal.record(decision.transition, decision.explanation)
        return observed, decision

    def commit(self) -> BootBackendState:
        """Health-commit the booted candidate as the new persistent default."""
        if self.journal.state is not BootTransactionState.CANDIDATE_BOOTING:
            raise BootTransactionError(
                "commit requires an observed candidate boot; "
                "health acceptance owns this transition"
            )
        observed = self.backend.observe_booted_slot()
        if observed != self.journal.candidate_slot:
            raise BootTransactionError(
                "refusing to commit: machine is not running the candidate"
            )
        committed = self.backend.commit_accepted(self.journal.candidate_slot)
        self.journal.record(
            BootTransactionState.ACCEPTED,
            f"slot {self.journal.candidate_slot} health-committed as default",
        )
        return committed

    def mark_failed(self, reason: str) -> None:
        """Record a failed candidate with bounded operator evidence."""
        if self.journal.is_terminal:
            raise BootJournalError("journal is already terminal")
        self.journal.record(BootTransactionState.FAILED, reason)

    def reconcile_after_crash(self) -> tuple[str | None, ReconcileDecision]:
        """Crash recovery: observe, fold into backend, reconcile journal."""
        try:
            observed: str | None = self.backend.observe_booted_slot()
        except BootTransactionError:
            observed = None
        if observed is not None:
            self.backend.reconcile(observed)
        decision = self.journal.reconcile(observed)
        if decision.transition is not None:
            self.journal.record(decision.transition, decision.explanation)
        return observed, decision


def coordinator_accepts_backend(backend: object) -> bool:
    """Prove a backend speaks the single coordinator interface (no branches)."""
    backend_id = getattr(backend, "backend_id", None)
    if backend_id not in AB_BOOT_BACKENDS:
        return False
    required = (
        "inspect", "arm_one_shot", "observe_booted_slot",
        "commit_accepted", "verify_rollback_ready", "reconcile",
    )
    return all(callable(getattr(backend, name, None)) for name in required)


# ---------------------------------------------------------------------------
# Bounded reboot-surviving boot/lifecycle history (T5-EVID, TAKEOVER-5, D56)
# ---------------------------------------------------------------------------
#
# Journald stays volatile (``Storage=volatile`` in the installed overlays)
# and ``/run`` markers do not survive reboot. This ring is the only PERSIST
# previous-boot record: a tiny structured current/previous summary rotated
# at boot with coarse milestone/terminal updates only. Never animation
# frames, input events, or verbose journal text.
#
# File location on a mounted PERSIST tree is
# ``<persist-root>/greia/boot-history.json`` (sibling of
# ``installed-layout.json`` and the ``boot-journal/`` transaction root).
# The running-system bind-visible alias is
# ``/var/lib/greia-os/diagnostics/boot-history.json`` (``bounded-logs``
# namespace, see ``persistent_layout.DURABLE_PATH_AUDIT``). T6/T7 harnesses
# read the PERSIST-side file directly from the guest disk.
#

#: PERSIST-side file name of the bounded boot-history ring.
BOOT_HISTORY_FILE_NAME = "boot-history.json"

#: Running-system bind-visible alias (audit classification only).
BOOT_HISTORY_RUNTIME_PATH = "/var/lib/greia-os/diagnostics/boot-history.json"

#: Schema version of the boot-history record.
BOOT_HISTORY_SCHEMA_VERSION = 1

#: History files are readable only by their owner (root on device).
BOOT_HISTORY_FILE_MODE = 0o600

#: Initial hard cap: 64 KiB total for the structured ring, source-enforced.
MAX_BOOT_HISTORY_BYTES = 64 * 1024

#: Ring bound: at most this many boot entries are retained. Rotation
#: (`current -> previous` at boot) truncates the oldest entry first; the
#: total-bytes cap is enforced independently on every save.
MAX_BOOT_HISTORY_ENTRIES = 8

#: Upper bound for short free-text fields (recovery reason/note).
MAX_BOOT_HISTORY_NOTE_BYTES = 256

#: Coarse lifecycle boundaries only. Anything finer (animation frames,
#: input events, verbose journal lines) is rejected here by construction.
BOOT_HISTORY_MILESTONES = frozenset(
    {
        "boot-started",
        "slot-observed",
        "launcher-started",
        "interactive-ready",
        "health-confirmed",
        "committed",
        "rolled-back",
        "failed",
        "recovery-entered",
    }
)

#: Transaction types shared with the boot journal / T4-RECOVER trigger.
BOOT_HISTORY_TRANSACTION_TYPES = frozenset({"first-install", "update", "none"})

#: Bounded launcher outcomes (no free-form process output).
BOOT_HISTORY_LAUNCHER_RESULTS = frozenset({"pending", "not-run", "ok", "failed"})

#: Bounded health confirm/finalize outcomes.
BOOT_HISTORY_HEALTH_RESULTS = frozenset(
    {"pending", "not-run", "confirmed", "failed", "rolled-back"}
)

#: Terminal states share the journal's vocabulary (plus explicit pending).
BOOT_HISTORY_TERMINAL_STATES = frozenset(
    {state.value for state in BootTransactionState} | {"pending"}
)


def boot_history_path(persist_root: Path) -> Path:
    """Return the PERSIST-side boot-history path for a mounted PERSIST tree."""
    return Path(persist_root) / "greia" / BOOT_HISTORY_FILE_NAME


def _require_boot_history_identifier(
    value: object, *, field_name: str, maximum: int
) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > maximum
        or not value[0].isalnum()
        or any(char not in "abcdefghijklmnopqrstuvwxyz0123456789._-" for char in value)
    ):
        raise BootTransactionError(f"{field_name} is not a bounded safe identifier")
    return value


def _require_boot_history_note(value: object, *, field_name: str) -> str:
    if not isinstance(value, str) or not value:
        raise BootTransactionError(f"{field_name} must be non-empty text")
    if len(value.encode("utf-8")) > MAX_BOOT_HISTORY_NOTE_BYTES:
        raise BootTransactionError(f"{field_name} exceeds Greia bounds")
    if "\x00" in value:
        raise BootTransactionError(f"{field_name} carries a NUL byte")
    return value


def _require_boot_history_unix_time(value: object, *, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise BootTransactionError(f"{field_name} is not a valid timestamp")
    if value < 0 or value > (1 << 40):
        raise BootTransactionError(f"{field_name} is not a valid timestamp")
    return value


@dataclass(frozen=True, slots=True)
class BootHistoryEntry:
    """One coarse boot summary: the only per-boot PERSIST evidence.

    ``launcher_result``/``health_result`` stay in their bounded vocabularies;
    ``recovery_reason`` is a bounded ``none``/trigger token shared with the
    T4-RECOVER trigger (never verbose journal text). ``terminal_state``
    mirrors :class:`BootTransactionState` values (or ``"pending"``).
    """

    boot_id: str
    started_at_unix: int
    slot: str
    release_id: str
    release_sequence: int
    transaction_id: str
    transaction_type: str
    milestone: str
    launcher_result: str
    health_result: str
    backend_default: str
    backend_one_shot: str | None
    recovery_reason: str
    terminal_state: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "boot_id",
            _require_canonical_uuid(self.boot_id, field_name="boot_id"),
        )
        object.__setattr__(
            self, "started_at_unix",
            _require_boot_history_unix_time(
                self.started_at_unix, field_name="started_at_unix"
            ),
        )
        _require_slot(self.slot, field_name="slot")
        _require_boot_history_identifier(
            self.release_id, field_name="release_id", maximum=96
        )
        if (
            isinstance(self.release_sequence, bool)
            or not isinstance(self.release_sequence, int)
            or not 0 <= self.release_sequence <= 2_147_483_647
        ):
            raise BootTransactionError("release_sequence is outside Greia bounds")
        _require_boot_history_identifier(
            self.transaction_id, field_name="transaction_id", maximum=64
        )
        if self.transaction_type not in BOOT_HISTORY_TRANSACTION_TYPES:
            raise BootTransactionError(
                f"transaction_type is unknown: {self.transaction_type!r}"
            )
        if self.milestone not in BOOT_HISTORY_MILESTONES:
            raise BootTransactionError(
                f"milestone is not a coarse lifecycle boundary: {self.milestone!r}"
            )
        if self.launcher_result not in BOOT_HISTORY_LAUNCHER_RESULTS:
            raise BootTransactionError(
                f"launcher_result is unknown: {self.launcher_result!r}"
            )
        if self.health_result not in BOOT_HISTORY_HEALTH_RESULTS:
            raise BootTransactionError(
                f"health_result is unknown: {self.health_result!r}"
            )
        _require_slot(self.backend_default, field_name="backend_default")
        if self.backend_one_shot is not None:
            _require_slot(self.backend_one_shot, field_name="backend_one_shot")
        _require_boot_history_identifier(
            self.recovery_reason, field_name="recovery_reason", maximum=64
        )
        if self.terminal_state not in BOOT_HISTORY_TERMINAL_STATES:
            raise BootTransactionError(
                f"terminal_state is unknown: {self.terminal_state!r}"
            )

    def as_dict(self) -> dict[str, object]:
        return {
            "backend_default": self.backend_default,
            "backend_one_shot": self.backend_one_shot,
            "boot_id": self.boot_id,
            "health_result": self.health_result,
            "launcher_result": self.launcher_result,
            "milestone": self.milestone,
            "recovery_reason": self.recovery_reason,
            "release_id": self.release_id,
            "release_sequence": self.release_sequence,
            "slot": self.slot,
            "started_at_unix": self.started_at_unix,
            "terminal_state": self.terminal_state,
            "transaction_id": self.transaction_id,
            "transaction_type": self.transaction_type,
        }

    @classmethod
    def from_dict(cls, raw: object) -> "BootHistoryEntry":
        if not isinstance(raw, dict):
            raise BootTransactionError("boot-history entry must be a JSON object")
        expected = {
            "backend_default", "backend_one_shot", "boot_id", "health_result",
            "launcher_result", "milestone", "recovery_reason", "release_id",
            "release_sequence", "slot", "started_at_unix", "terminal_state",
            "transaction_id", "transaction_type",
        }
        if set(raw) != expected:
            raise BootTransactionError("boot-history entry fields are invalid")
        return cls(
            boot_id=raw["boot_id"],
            started_at_unix=raw["started_at_unix"],
            slot=raw["slot"],
            release_id=raw["release_id"],
            release_sequence=raw["release_sequence"],
            transaction_id=raw["transaction_id"],
            transaction_type=raw["transaction_type"],
            milestone=raw["milestone"],
            launcher_result=raw["launcher_result"],
            health_result=raw["health_result"],
            backend_default=raw["backend_default"],
            backend_one_shot=raw["backend_one_shot"],
            recovery_reason=raw["recovery_reason"],
            terminal_state=raw["terminal_state"],
        )


@dataclass
class BootHistory:
    """Bounded ring of coarse boot summaries persisted on PERSIST.

    Rotation happens only at boot (``begin_boot`` moves current -> previous
    and truncates the oldest entry); afterwards only coarse
    milestone/terminal updates mutate the head entry. Total stored bytes
    never exceed ``MAX_BOOT_HISTORY_BYTES``: oversized saves fail closed
    and leave the existing file untouched.
    """

    history_dir: Path
    entries: tuple[BootHistoryEntry, ...] = ()

    def __post_init__(self) -> None:
        if len(self.entries) > MAX_BOOT_HISTORY_ENTRIES:
            raise BootTransactionError("boot-history ring exceeds Greia bounds")

    @classmethod
    def empty(cls, history_dir: Path) -> "BootHistory":
        """Empty history for a fresh PERSIST tree (no previous boot)."""
        return cls(history_dir=Path(history_dir), entries=())

    @property
    def history_path(self) -> Path:
        return Path(self.history_dir) / BOOT_HISTORY_FILE_NAME

    @property
    def current(self) -> BootHistoryEntry | None:
        """The current (head) boot entry, if any."""
        return self.entries[-1] if self.entries else None

    @property
    def previous(self) -> BootHistoryEntry | None:
        """The previous boot entry (the failed candidate after recovery)."""
        return self.entries[-2] if len(self.entries) >= 2 else None

    def as_dict(self) -> dict[str, object]:
        return {
            "entries": [entry.as_dict() for entry in self.entries],
            "schema_version": BOOT_HISTORY_SCHEMA_VERSION,
        }

    def canonical_bytes(self) -> bytes:
        return _canonical_bytes(self.as_dict())

    def _checked_bytes(self) -> bytes:
        payload = self.canonical_bytes()
        if len(payload) > MAX_BOOT_HISTORY_BYTES:
            raise BootTransactionError(
                "boot-history exceeds the 64 KiB Greia bound: "
                "refusing an unbounded persistent write"
            )
        return payload

    def save(self) -> None:
        """Atomically persist the ring; over-budget writes fail closed."""
        payload = self._checked_bytes()
        _atomic_write_file(self.history_path, payload, mode=BOOT_HISTORY_FILE_MODE)

    @classmethod
    def load(cls, history_dir: Path) -> "BootHistory":
        """Fail-closed load of the PERSIST ring (T6/T7 read this path)."""
        location = Path(history_dir) / BOOT_HISTORY_FILE_NAME
        try:
            if location.is_symlink():
                raise BootTransactionError("boot-history may not be a symbolic link")
            status = location.stat()
        except OSError as exc:
            raise BootTransactionError(
                f"boot-history is not accessible: {exc}"
            ) from exc
        import stat as _stat

        if not _stat.S_ISREG(status.st_mode):
            raise BootTransactionError("boot-history must be a regular file")
        if status.st_size <= 0 or status.st_size > MAX_BOOT_HISTORY_BYTES:
            raise BootTransactionError("boot-history size is outside Greia bounds")
        if _stat.S_IMODE(status.st_mode) != BOOT_HISTORY_FILE_MODE:
            raise BootTransactionError("boot-history must be owner-only mode 0600")
        if status.st_uid != os.geteuid():
            raise BootTransactionError("boot-history ownership is not authoritative")
        try:
            raw_bytes = location.read_bytes()
        except OSError as exc:
            raise BootTransactionError("boot-history is unreadable") from exc
        if len(raw_bytes) > MAX_BOOT_HISTORY_BYTES:
            raise BootTransactionError("boot-history size is outside Greia bounds")
        try:
            raw = json.loads(raw_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise BootTransactionError("boot-history is not valid JSON") from exc
        if not isinstance(raw, dict) or set(raw) != {"entries", "schema_version"}:
            raise BootTransactionError("boot-history fields are invalid")
        if raw.get("schema_version") != BOOT_HISTORY_SCHEMA_VERSION:
            raise BootTransactionError("boot-history schema is unsupported")
        entries_raw = raw.get("entries")
        if not isinstance(entries_raw, list):
            raise BootTransactionError("boot-history entries are invalid")
        if len(entries_raw) > MAX_BOOT_HISTORY_ENTRIES:
            raise BootTransactionError("boot-history ring exceeds Greia bounds")
        entries = tuple(BootHistoryEntry.from_dict(item) for item in entries_raw)
        history = cls(history_dir=Path(history_dir), entries=entries)
        if raw_bytes != history.canonical_bytes():
            raise BootTransactionError("boot-history is not canonical JSON")
        return history

    def begin_boot(
        self,
        *,
        boot_id: str,
        started_at_unix: int,
        slot: str,
        release_id: str,
        release_sequence: int,
        transaction_id: str,
        transaction_type: str,
        backend_default: str,
        backend_one_shot: str | None = None,
    ) -> "BootHistory":
        """Rotate current -> previous and start one coarse ``boot-started`` entry."""
        entry = BootHistoryEntry(
            boot_id=boot_id,
            started_at_unix=started_at_unix,
            slot=slot,
            release_id=release_id,
            release_sequence=release_sequence,
            transaction_id=transaction_id,
            transaction_type=transaction_type,
            milestone="boot-started",
            launcher_result="pending",
            health_result="pending",
            backend_default=backend_default,
            backend_one_shot=backend_one_shot,
            recovery_reason="none",
            terminal_state="pending",
        )
        rotated = (*self.entries, entry)[-MAX_BOOT_HISTORY_ENTRIES:]
        candidate = BootHistory(history_dir=Path(self.history_dir), entries=rotated)
        # Fail closed before and during the write: an over-budget rotation
        # never lands on disk or in memory.
        payload = candidate._checked_bytes()
        _atomic_write_file(candidate.history_path, payload, mode=BOOT_HISTORY_FILE_MODE)
        object.__setattr__(self, "entries", candidate.entries)
        return self

    def record_milestone(
        self,
        milestone: str,
        *,
        launcher_result: str | None = None,
        health_result: str | None = None,
        backend_default: str | None = None,
        backend_one_shot: str | None = None,
        recovery_reason: str | None = None,
        terminal_state: str | None = None,
    ) -> "BootHistory":
        """Update only the head entry with one coarse lifecycle boundary."""
        if not self.entries:
            raise BootTransactionError("no current boot to record a milestone for")
        if milestone not in BOOT_HISTORY_MILESTONES:
            raise BootTransactionError(
                f"milestone is not a coarse lifecycle boundary: {milestone!r}"
            )
        head = self.entries[-1]
        if backend_one_shot is None:
            new_one_shot = head.backend_one_shot
        elif backend_one_shot == "":
            # One-shot consumed/cleared (reconcile path): explicit empty
            # string clears to None; None alone keeps the head value.
            new_one_shot = None
        else:
            new_one_shot = backend_one_shot
        updated = BootHistoryEntry(
            boot_id=head.boot_id,
            started_at_unix=head.started_at_unix,
            slot=head.slot,
            release_id=head.release_id,
            release_sequence=head.release_sequence,
            transaction_id=head.transaction_id,
            transaction_type=head.transaction_type,
            milestone=milestone,
            launcher_result=launcher_result or head.launcher_result,
            health_result=health_result or head.health_result,
            backend_default=backend_default or head.backend_default,
            backend_one_shot=new_one_shot,
            recovery_reason=recovery_reason or head.recovery_reason,
            terminal_state=terminal_state or head.terminal_state,
        )
        candidate = BootHistory(
            history_dir=Path(self.history_dir), entries=(*self.entries[:-1], updated)
        )
        # Fail closed: check the bound, write the candidate bytes, and only
        # then fold the update into memory. A failed write leaves both the
        # existing file and this object untouched.
        payload = candidate._checked_bytes()
        _atomic_write_file(candidate.history_path, payload, mode=BOOT_HISTORY_FILE_MODE)
        object.__setattr__(self, "entries", candidate.entries)
        return self


def describe_previous_boot(history: BootHistory) -> dict[str, object] | None:
    """Explain the previous boot from the PERSIST ring only (T5 gate).

    Returns which slot/release attempted, its last durable milestone, the
    recovery reason and terminal state — without touching volatile ``/run``
    or any journal. ``None`` when no previous boot exists yet.
    """
    previous = history.previous
    if previous is None:
        return None
    return {
        "attempted_slot": previous.slot,
        "attempted_release_id": previous.release_id,
        "attempted_release_sequence": previous.release_sequence,
        "last_milestone": previous.milestone,
        "launcher_result": previous.launcher_result,
        "health_result": previous.health_result,
        "backend_default": previous.backend_default,
        "backend_one_shot": previous.backend_one_shot,
        "recovery_reason": previous.recovery_reason,
        "terminal_state": previous.terminal_state,
        "transaction_id": previous.transaction_id,
        "transaction_type": previous.transaction_type,
    }


# ---------------------------------------------------------------------------
# Failed-candidate recovery trigger (TAKEOVER-4 / D55, owner Decision A)
# ---------------------------------------------------------------------------
#
# One-shot selection defines *where* the next boot goes; this section defines
# *what causes* that next boot for recoverable failures. The boot transaction
# owns a candidate health deadline as a narrow lifecycle capability: a
# candidate that reaches the OS but never becomes healthy within the bounded
# deadline is marked failed in the existing transaction journal and the
# platform performs a controlled reboot while the previous accepted slot
# stays the persistent default. No generic looping supervisor is introduced:
# deadline expiry is owned by one systemd timer unit firing one oneshot
# recovery helper per boot (see the ``greia-candidate-recovery`` unit and
# helper under ``build/overlay``); this module owns only the journal
# decision, the failure-class contract and the exact reboot/panic/watchdog
# configuration facts the image must carry.
#
# Failure classes (TAKEOVER-4 T4.2):
#
# 1. launcher exits/crashes — the launcher unit keeps restarting under its
#    own restart bound while the deadline timer still fires, so the reboot
#    path is reached even across a crash loop;
# 2. userspace reaches emergency/failure state before health — the system
#    timer still fires independently of the launcher state;
# 3. health service fails (BOOT_HEALTHY never confirms) — the pending
#    journal stays non-terminal, so the helper marks it failed and reboots;
# 4. kernel panic — automatic panic reboot is configured (see
#    ``PANIC_REBOOT_SYSCTL`` and the sysctl drop-in under ``build/overlay``),
#    then the consumed one-shot returns the machine to the accepted default;
# 5. hard kernel/hardware hang — automatic recovery exists only where a
#    hardware watchdog is present *and* proven per platform (see
#    ``WATCHDOG_PROVEN_PLATFORMS``). No reference platform currently proves
#    one, so the contract guarantees previous-slot recovery on the next
#    physical power cycle and describes it honestly as manual recovery.
#
# The trigger itself terminally records journal ``FAILED`` (candidate
# abandoned with bounded operator evidence). ``reconcile()`` returns
# ``None`` on terminal journals, so no ``ROLLED_BACK`` transition ever
# follows a trigger-``FAILED``: the reboot after the trigger returns to
# the accepted default via the untouched backend default, and rollback
# readiness is proven from that backend fact, not from a later journal
# transition. ``ROLLED_BACK`` arises only on reconcile paths that never
# entered ``FAILED`` (a non-terminal ``ONE_SHOT_ARMED``/``CANDIDATE_BOOTING``
# journal observed back on the accepted slot). First-install failures use
# the same trigger; their outcome medium is setup-medium, never A/B rollback.
#
# Coordination with the T5 reboot-surviving record: this trigger consumes
# the transaction journal and writes nothing to any persistent boot-history
# namespace. The structured note produced by :func:`format_recovery_note`
# carries the ``recovery:<class>:<action>`` prefix with the field names
# (``recovery_class``, ``recovery_action``, ``accepted_slot``,
# ``candidate_slot``, ``transaction_id``) the T5 record reuses when it
# lands; T5 must reference this contract, not duplicate it.
#
# Cause-label decision (T4-RECOVER2 Option A): the production deadline
# helper preserves the per-class label for classes 1-3
# (``launcher-exit``, ``userspace-emergency``, ``health-service-failure``)
# in the journal note instead of converging them. Option B (converge on
# ``health-service-failure`` plus free-text detail in the T5 record) was
# rejected because ``BootHistoryEntry.recovery_reason`` is a bounded
# identifier (never verbose journal text) and no new PERSIST schema is
# allowed; the bounded per-class label round-trips into ``recovery_reason``
# unchanged, so cause distinction survives reboot without schema change.


#: Candidate health deadline in seconds, owned by the boot transaction and
#: enforced by the ``greia-candidate-recovery.timer`` unit (``OnBootSec``
#: matches this value). Covers the 7-second intro plus health acceptance
#: with margin for the low-resource reference floor, while staying short
#: enough for a child-visible recovery. Bounds: 60..600.
CANDIDATE_HEALTH_DEADLINE_SEC = 180

#: Systemd timer owning deadline expiry (single fire per boot).
CANDIDATE_RECOVERY_TIMER = "greia-candidate-recovery.timer"

#: Systemd oneshot service running the recovery helper (fired by the timer).
CANDIDATE_RECOVERY_SERVICE = "greia-candidate-recovery.service"

#: Absolute path of the privileged recovery helper in the image.
RECOVERY_HELPER_PATH = "/usr/local/lib/greia-os/greia-candidate-recovery"

#: Kernel panic-reboot configuration the image must carry so failure
#: class 4 reboots automatically. The sysctl drop-in under
#: ``build/overlay/etc/sysctl.d`` renders exactly this mapping:
#: reboot ~10s after a panic, including oops-induced panics.
PANIC_REBOOT_SYSCTL = {
    "kernel.panic": "10",
    "kernel.panic_on_oops": "1",
}

#: Platforms with a proven hardware watchdog capable of resetting a fully
#: hung machine. Empty: no reference platform currently proves one, so no
#: automatic hard-hang recovery may be claimed anywhere. A platform joins
#: this set only with per-board reset-capability evidence; until then the
#: contract guarantees previous-slot recovery on the next physical power
#: cycle (manual recovery).
WATCHDOG_PROVEN_PLATFORMS: frozenset[str] = frozenset()

#: Recovery medium recorded for a failed first install (never "rollback").
RECOVERY_SETUP_MEDIUM = "setup-medium"

#: Recovery medium recorded for a failed update candidate.
RECOVERY_ACCEPTED_SLOT_MEDIUM = "accepted-slot"

#: Structured journal-note prefix owned by this trigger contract.
RECOVERY_NOTE_PREFIX = "recovery:"


class RecoveryClass(StrEnum):
    """TAKEOVER-4 T4.2 failure classes, proven separately per the brief."""

    LAUNCHER_EXIT = "launcher-exit"
    USERSPACE_EMERGENCY = "userspace-emergency"
    HEALTH_SERVICE_FAILURE = "health-service-failure"
    KERNEL_PANIC = "kernel-panic"
    HARD_HANG = "hard-hang"


class RecoveryAction(StrEnum):
    """What the platform guarantees for a failure class (Decision A)."""

    AUTOMATIC_REBOOT = "automatic-reboot"
    MANUAL_POWER_CYCLE = "manual-power-cycle"


#: Failure classes whose reboot the OS can still trigger (1-4).
AUTOMATIC_RECOVERY_CLASSES = frozenset(
    {
        RecoveryClass.LAUNCHER_EXIT,
        RecoveryClass.USERSPACE_EMERGENCY,
        RecoveryClass.HEALTH_SERVICE_FAILURE,
        RecoveryClass.KERNEL_PANIC,
    }
)

#: Journal states in which the deadline trigger may mark a candidate failed.
RECOVERY_TRIGGER_STATES = frozenset(
    {
        BootTransactionState.FIRST_INSTALL_PENDING,
        BootTransactionState.UPDATE_STAGED,
        BootTransactionState.ONE_SHOT_ARMED,
        BootTransactionState.CANDIDATE_BOOTING,
    }
)


@dataclass(frozen=True, slots=True)
class RecoveryTriggerDecision:
    """Outcome of marking a candidate failed through the recovery trigger."""

    recovery_class: RecoveryClass
    action: RecoveryAction
    accepted_slot: str
    candidate_slot: str
    transaction_id: str
    journal_transition: BootTransactionState
    recovery_medium: str
    note: str


def recovery_action_for(recovery_class: RecoveryClass | str) -> RecoveryAction:
    """Return the guaranteed action for a failure class (Decision A).

    Classes 1-4 reboot automatically where the OS can still trigger a
    reboot (including configured panic recovery). A hard hang reboots
    automatically only on a platform with a proven watchdog; with the
    current empty :data:`WATCHDOG_PROVEN_PLATFORMS` set that is never, so
    a hard hang always resolves to manual power-cycle recovery.
    """
    resolved = _require_recovery_class(recovery_class)
    if resolved in AUTOMATIC_RECOVERY_CLASSES:
        return RecoveryAction.AUTOMATIC_REBOOT
    return RecoveryAction.MANUAL_POWER_CYCLE


def is_watchdog_proven(platform_id: object) -> bool:
    """True only for platforms with proven watchdog reset capability."""
    return isinstance(platform_id, str) and platform_id in WATCHDOG_PROVEN_PLATFORMS


def format_recovery_note(
    recovery_class: RecoveryClass | str, action: RecoveryAction | str, detail: str = ""
) -> str:
    """Format the bounded structured journal note for a recovery marking.

    Shape: ``recovery:<class>:<action>[:<detail>]``. Field names T5 reuses
    are ``recovery_class``, ``recovery_action``, ``accepted_slot``,
    ``candidate_slot`` and ``transaction_id``; the free-text detail stays
    inside the journal note bound.
    """
    resolved_class = _require_recovery_class(recovery_class)
    resolved_action = _require_recovery_action(action)
    text = str(detail) if detail else ""
    note = (
        f"{RECOVERY_NOTE_PREFIX}{resolved_class.value}:{resolved_action.value}"
        + (f":{text}" if text else "")
    )
    if not note or len(note.encode("utf-8")) > MAX_TRANSITION_NOTE_BYTES:
        raise BootJournalError("recovery note exceeds Greia bounds")
    return note


def parse_recovery_note(note: object) -> dict[str, str] | None:
    """Parse a trigger note, or None when the note is not a trigger note."""
    if not isinstance(note, str) or not note.startswith(RECOVERY_NOTE_PREFIX):
        return None
    body = note[len(RECOVERY_NOTE_PREFIX):]
    parts = body.split(":", 2)
    if len(parts) < 2:
        return None
    try:
        resolved_class = _require_recovery_class(parts[0])
        resolved_action = _require_recovery_action(parts[1])
    except BootJournalError:
        return None
    return {
        "recovery_class": resolved_class.value,
        "recovery_action": resolved_action.value,
        "detail": parts[2] if len(parts) > 2 else "",
    }


def describe_recovery_contract() -> dict[str, object]:
    """Return the honest per-class recovery contract (Decision A default).

    Used by the recovery helper text and tests from one source: classes
    1-4 map to automatic reboot, hard hang maps to manual power cycle
    while no watchdog platform is proven. The deadline helper operates
    x86 ``GrubEnvBackend``-only; a missing backend is a bounded
    ``backend-unavailable`` no-action, and Pi/tryboot deadline triggering
    is deferred to the PI8 tranche (DOWN-PI8).
    """
    return {
        "deadline_sec": CANDIDATE_HEALTH_DEADLINE_SEC,
        "timer": CANDIDATE_RECOVERY_TIMER,
        "service": CANDIDATE_RECOVERY_SERVICE,
        "helper": RECOVERY_HELPER_PATH,
        "boot_backend": "grub-ab-v1",
        "backend_scope": "x86 GrubEnvBackend only",
        "backend_unavailable": (
            "bounded no-action: no reboot, no journal/backend mutation"
        ),
        "pi_tryboot": "deferred to the PI8 tranche (DOWN-PI8)",
        "classes": {
            RecoveryClass.LAUNCHER_EXIT.value: RecoveryAction.AUTOMATIC_REBOOT.value,
            RecoveryClass.USERSPACE_EMERGENCY.value: RecoveryAction.AUTOMATIC_REBOOT.value,
            RecoveryClass.HEALTH_SERVICE_FAILURE.value: RecoveryAction.AUTOMATIC_REBOOT.value,
            RecoveryClass.KERNEL_PANIC.value: RecoveryAction.AUTOMATIC_REBOOT.value,
            RecoveryClass.HARD_HANG.value: RecoveryAction.MANUAL_POWER_CYCLE.value,
        },
        "panic_sysctl": dict(PANIC_REBOOT_SYSCTL),
        "watchdog_proven_platforms": sorted(WATCHDOG_PROVEN_PLATFORMS),
    }


def mark_candidate_unhealthy(
    coordinator: BootTransactionCoordinator,
    *,
    recovery_class: RecoveryClass | str,
    detail: str = "",
) -> RecoveryTriggerDecision:
    """Mark a non-healthy candidate failed through the recovery trigger.

    Records journal ``FAILED`` terminally with the structured trigger note;
    the backend persistent default is never mutated here, so the following
    controlled reboot (owned by systemd, not this module) returns to the
    previous accepted slot with the candidate abandoned. ``ROLLED_BACK``
    is deliberately not recorded here and never follows: ``reconcile()``
    returns ``None`` on terminal journals, so ``ROLLED_BACK`` arises only
    on reconcile paths that never entered ``FAILED``.
    """
    if not isinstance(coordinator, BootTransactionCoordinator):
        raise BootJournalError("recovery trigger requires a boot transaction coordinator")
    resolved = _require_recovery_class(recovery_class)
    action = recovery_action_for(resolved)
    if action is not RecoveryAction.AUTOMATIC_REBOOT:
        raise BootJournalError(
            "the deadline trigger never fires for a hard hang without a "
            "proven watchdog: recovery is manual power-cycle only"
        )
    journal = coordinator.journal
    if journal.is_terminal:
        raise BootJournalError("recovery trigger refuses a completed transaction")
    if journal.state not in RECOVERY_TRIGGER_STATES:
        raise BootJournalError(
            f"recovery trigger refuses journal state {journal.state.value}"
        )
    note = format_recovery_note(resolved, action, detail)
    journal.record(BootTransactionState.FAILED, note)
    medium = (
        RECOVERY_SETUP_MEDIUM if journal.first_install else RECOVERY_ACCEPTED_SLOT_MEDIUM
    )
    return RecoveryTriggerDecision(
        recovery_class=resolved,
        action=action,
        accepted_slot=journal.accepted_slot,
        candidate_slot=journal.candidate_slot,
        transaction_id=journal.transaction_id,
        journal_transition=BootTransactionState.FAILED,
        recovery_medium=medium,
        note=note,
    )


def _require_recovery_class(value: object) -> RecoveryClass:
    if isinstance(value, RecoveryClass):
        return value
    try:
        return RecoveryClass(str(value))
    except ValueError as exc:
        raise BootJournalError(f"unknown recovery class: {value!r}") from exc


def _require_recovery_action(value: object) -> RecoveryAction:
    if isinstance(value, RecoveryAction):
        return value
    try:
        return RecoveryAction(str(value))
    except ValueError as exc:
        raise BootJournalError(f"unknown recovery action: {value!r}") from exc
