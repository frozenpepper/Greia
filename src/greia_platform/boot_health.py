"""Trusted one-use post-intro interactive BOOT_HEALTHY protocol.

L7-HEALTH (R0/R1 source scope): files and fakes only. No slot/boot writes,
no bootloader-default changes, no firmware-variable contact, no
subprocess/shell and no device-node surface live here. The production firmware/GRUB adapters stay behind
the L7-BOOT :class:`BootTransactionBackend` protocol; the production
credential transport is a systemd service credential
(``$CREDENTIALS_DIRECTORY``) with this module's owner-only file vault as the
equivalently narrow R0/R1 mechanism.

Protocol shape (trusted one-use ``BOOT_HEALTHY`` after the 7-second intro):

- Provision: once the journal has observed the candidate boot
  (``CANDIDATE_BOOTING``), the trusted launcher bootstrap path provisions a
  single one-use credential bound to ``(transaction_id, boot_attempt)``. The
  credential is never handed to Parent or Activity code.
- Confirm (phase 1 of the two-phase acceptance): the presenter must show the
  credential token *and* arrive from the trusted launcher bootstrap path *and*
  present this boot attempt *and* prove the full post-intro evidence —
  actual booted slot == pending candidate, actual root PARTUUID/release
  identity == pending candidate identity (re-observed by the platform
  itself, never asserted by the caller), first frame occurred, the full
  7-second intro completed, ``INTERACTIVE_READY`` reached, and no untrusted
  Activity launched yet. UID alone never authorizes: Activities share the
  child OS identity, so the peer bootstrap path is always required beside
  the token. Success consumes (deletes) the credential and enters the
  ``HEALTHY_COMMITTING`` phase recorded in a sidecar bound to the
  transaction. The credential is therefore always invalidated before
  untrusted Activity launch is enabled.
- Finalize (phase 2): re-observes identity and journal state, then commits
  through :class:`BootTransactionCoordinator.commit` (journal ``ACCEPTED``)
  and opens the untrusted-launch gate.

First-install semantics: a fresh install boots ``SYSTEM_A`` under
``FIRST_INSTALL_PENDING`` and uses the same predicate. A first-install
failure is Setup-medium recovery, never described as A/B rollback: outcome
records carry ``"setup-medium"`` for first install and ``"accepted-slot"``
for updates).

Intro boundary: this module never touches intro timing. It only consumes
intro evidence supplied by the launcher seam. ``FIRST_FRAME_VISIBLE``
(Phase-6 ``READY=1``) alone never suffices: confirmation additionally
requires the full intro completion flag and ``INTERACTIVE_READY``.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import stat
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Protocol


class BootHealthError(RuntimeError):
    """Post-intro BOOT_HEALTHY evidence, credential or phase is invalid."""


#: Schema version of every BOOT_HEALTHY record in this module.
BOOT_HEALTH_SCHEMA_VERSION = 1

#: Single active credential file inside the caller-provided vault directory.
CREDENTIAL_FILE_NAME = "boot-healthy-credential.json"

#: HEALTHY_COMMITTING sidecar inside the caller-provided vault directory.
COMMITTING_FILE_NAME = "healthy-committing.json"

#: Credential, ticket and sidecar files are readable only by their owner.
BOOT_HEALTH_FILE_MODE = 0o600

#: Upper bound for stored credential/sidecar bytes (small by construction).
MAX_BOOT_HEALTH_BYTES = 4 * 1024

#: Lifecycle value the launcher guard must report for confirmation.
INTERACTIVE_READY_VALUE = "interactive_ready"

#: Lifecycle value proving only the first frame (never sufficient alone).
FIRST_FRAME_VISIBLE_VALUE = "first_frame_visible"

#: Recovery medium recorded for a failed first install (never "rollback").
SETUP_MEDIUM = "setup-medium"

#: Recovery medium recorded for a failed update candidate.
ACCEPTED_SLOT_MEDIUM = "accepted-slot"

_HEX_LOWER = frozenset("0123456789abcdef")


def _canonical_bytes(value: Mapping[str, object]) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _fsync_directory(directory: Path) -> None:
    try:
        descriptor = os.open(os.fspath(directory), os.O_RDONLY)
    except OSError as exc:
        raise BootHealthError(f"health directory is not fsyncable: {exc}") from exc
    try:
        os.fsync(descriptor)
    except OSError as exc:
        raise BootHealthError(f"health directory fsync failed: {exc}") from exc
    finally:
        os.close(descriptor)


def _atomic_write_0600(path: Path, payload: bytes) -> None:
    if len(payload) > MAX_BOOT_HEALTH_BYTES:
        raise BootHealthError("health record exceeds Greia bounds")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / f".{path.name}.{os.getpid()}.tmp"
    try:
        with open(temporary, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, BOOT_HEALTH_FILE_MODE)
        os.replace(temporary, path)
    finally:
        try:
            if temporary.exists() and not temporary.is_symlink():
                temporary.unlink()
        except OSError:
            pass
    _fsync_directory(path.parent)


def _read_canonical_record(path: Path, *, context: str) -> dict[str, object]:
    try:
        if path.is_symlink():
            raise BootHealthError(f"{context} must not be a symlink")
        raw_bytes = path.read_bytes()
    except BootHealthError:
        raise
    except OSError as exc:
        raise BootHealthError(f"{context} is unreadable: {exc}") from exc
    if len(raw_bytes) > MAX_BOOT_HEALTH_BYTES:
        raise BootHealthError(f"{context} exceeds Greia bounds")
    try:
        mode = stat.S_IMODE(os.stat(path).st_mode)
    except OSError as exc:
        raise BootHealthError(f"{context} is not statable: {exc}") from exc
    if mode != BOOT_HEALTH_FILE_MODE:
        raise BootHealthError(f"{context} must be owner-only (0600)")
    try:
        raw = json.loads(raw_bytes.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise BootHealthError(f"{context} is not valid JSON: {exc}") from exc
    if not isinstance(raw, dict):
        raise BootHealthError(f"{context} must be a JSON object")
    if raw.get("schema_version") != BOOT_HEALTH_SCHEMA_VERSION:
        raise BootHealthError(f"{context} schema is unknown")
    if _canonical_bytes(raw) != raw_bytes:
        raise BootHealthError(f"{context} is not canonical JSON")
    return raw


def _require_root_partuuid(value: object, *, field_name: str) -> str:
    """Observed ``root=PARTUUID=``: GPT GUID or MBR ``<sig>-<NN>`` (T1-IDENT)."""
    import re as _re

    if not isinstance(value, str):
        raise BootHealthError(f"{field_name} must be text")
    try:
        parsed = uuid.UUID(str(value))
    except (ValueError, AttributeError):
        pass
    else:
        if str(parsed) == str(value).lower():
            return str(parsed)
    text = str(value).strip()
    if "-" not in text:
        raise BootHealthError(f"{field_name} is not a PARTUUID")
    signature_text, _, number_text = text.rpartition("-")
    signature = signature_text.lower()
    if signature.startswith("0x"):
        signature = signature[2:]
    if not _re.fullmatch(r"[0-9a-f]{8}", signature):
        raise BootHealthError(f"{field_name} is not a PARTUUID")
    if not number_text.isascii() or not number_text.isdigit():
        raise BootHealthError(f"{field_name} carries an invalid MBR partition number")
    number = int(number_text, 10)
    if not 1 <= number <= 128:
        raise BootHealthError(
            f"{field_name} carries an MBR partition number outside Greia bounds"
        )
    return f"{signature}-{number:02d}"


def _require_token(value: object, *, field_name: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise BootHealthError(f"{field_name} must be 256-bit hex")
    if any(char not in _HEX_LOWER for char in value):
        raise BootHealthError(f"{field_name} must be lowercase hex")
    return value


def _require_nonempty_text(value: object, *, field_name: str, maximum: int) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise BootHealthError(f"{field_name} is outside Greia bounds")
    return value


def _require_identifier(value: object, *, field_name: str, maximum: int) -> str:
    text = _require_nonempty_text(value, field_name=field_name, maximum=maximum)
    if any(char.isspace() for char in text):
        raise BootHealthError(f"{field_name} must be a whitespace-free token")
    return text


def systemd_vault_dir() -> Path | None:
    """Return the production systemd-credential vault dir, or None outside it.

    Systemd exposes each ``LoadCredential=`` entry as a file inside
    ``$CREDENTIALS_DIRECTORY``. Production images provision the BOOT_HEALTHY
    credential there; R0/R1 callers pass an explicit run directory instead.
    """
    raw = os.environ.get("CREDENTIALS_DIRECTORY")
    if not raw:
        return None
    return Path(raw) / "greia-boot-health"


# ---------------------------------------------------------------------------
# Platform-observed actual boot identity (revalidated by the service itself)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ActualBootIdentity:
    """Authoritative actual boot facts, observed by the platform itself.

    Callers never assert these: confirmation takes them from an
    :class:`ActualBootObserver` the platform owns, so a malicious peer
    cannot talk itself into the candidate slot or release.
    """

    booted_slot: str
    root_partuuid: str
    release_id: str
    release_sequence: int

    def __post_init__(self) -> None:
        if self.booted_slot not in ("A", "B"):
            raise BootHealthError("observed booted slot must be A or B")
        object.__setattr__(
            self, "root_partuuid",
            _require_root_partuuid(self.root_partuuid, field_name="observed root PARTUUID"),
        )
        _require_identifier(self.release_id, field_name="release_id", maximum=96)
        if (
            isinstance(self.release_sequence, bool)
            or not isinstance(self.release_sequence, int)
            or not 0 <= self.release_sequence <= 2_147_483_647
        ):
            raise BootHealthError("observed release_sequence is outside Greia bounds")


class ActualBootObserver(Protocol):
    """Platform-owned actual-identity source (never caller assertions)."""

    def observe(self) -> ActualBootIdentity: ...


class FakeActualBootIdentity:
    """R0/R1 file-free fake observer: fixed identity set by the test.

    File-free stand-in for :class:`ProductionActualBootObserver`. Tests
    drive wrong slot/release negatives by constructing fakes that report
    them.
    """

    def __init__(self, identity: ActualBootIdentity) -> None:
        self._identity = identity

    @property
    def identity(self) -> ActualBootIdentity:
        return self._identity

    def observe(self) -> ActualBootIdentity:
        return self._identity


# ---------------------------------------------------------------------------
# Production actual-identity observer (on-device, never caller assertions)
# ---------------------------------------------------------------------------

#: Kernel command line path carrying the observed ``root=PARTUUID=`` fact.
PRODUCTION_CMDLINE_ENV = "GREIA_BOOT_CMDLINE"
PRODUCTION_CMDLINE_DEFAULT = "/proc/cmdline"

#: Slot-local release identity written by ``SlotFinalizer`` into the booted
#: slot filesystem (``etc/greia-os/release-identity.json``), hence visible on
#: the running system at this path. Platform-owned, never caller-supplied.
PRODUCTION_RELEASE_IDENTITY_ENV = "GREIA_RELEASE_IDENTITY_PATH"
PRODUCTION_RELEASE_IDENTITY_DEFAULT = "/etc/greia-os/release-identity.json"

#: Trusted installed-layout record binding PARTUUIDs to semantic slots.
PRODUCTION_LAYOUT_RECORD_ENV = "GREIA_INSTALLED_LAYOUT_RECORD"
PRODUCTION_LAYOUT_RECORD_DEFAULT = "/etc/greia-os/installed-layout.json"

#: Upper bound for the kernel command line read (small by construction).
MAX_CMDLINE_BYTES = 64 * 1024


def production_cmdline_path() -> Path:
    """Resolve the kernel command line path (explicit env or /proc/cmdline)."""
    override = os.environ.get(PRODUCTION_CMDLINE_ENV, "").strip()
    return Path(override) if override else Path(PRODUCTION_CMDLINE_DEFAULT)


def production_release_identity_path() -> Path:
    """Resolve the booted-slot release-identity path (env or system bind)."""
    override = os.environ.get(PRODUCTION_RELEASE_IDENTITY_ENV, "").strip()
    return Path(override) if override else Path(PRODUCTION_RELEASE_IDENTITY_DEFAULT)


def production_layout_record_path() -> Path:
    """Resolve the trusted layout-record path (env or system bind)."""
    override = os.environ.get(PRODUCTION_LAYOUT_RECORD_ENV, "").strip()
    return Path(override) if override else Path(PRODUCTION_LAYOUT_RECORD_DEFAULT)


def read_kernel_root_partuuid(cmdline_path: Path | None = None) -> str:
    """Return the single observed ``root=PARTUUID=`` value from the kernel cmdline.

    Reads the platform's own kernel fact (``/proc/cmdline`` on device);
    zero or several ``root=PARTUUID=`` tokens fail closed.
    """
    path = Path(cmdline_path) if cmdline_path is not None else production_cmdline_path()
    if path.is_symlink():
        raise BootHealthError("kernel command line must not be a symlink")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise BootHealthError(f"kernel command line is unreadable: {exc}") from exc
    if len(raw) > MAX_CMDLINE_BYTES:
        raise BootHealthError("kernel command line exceeds Greia bounds")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise BootHealthError("kernel command line is not valid text") from exc
    roots = [
        token.split("root=PARTUUID=", 1)[1]
        for token in text.split()
        if token.startswith("root=PARTUUID=")
    ]
    if len(roots) != 1 or not roots[0]:
        raise BootHealthError("kernel command line carries no single root PARTUUID")
    return _require_root_partuuid(roots[0], field_name="observed root PARTUUID")


def read_booted_release_identity(
    identity_path: Path | None = None,
) -> tuple[str, str, int]:
    """Return ``(slot, release_id, release_sequence)`` from the booted slot.

    Reads the ``release-identity.json`` the ``SlotFinalizer`` wrote into the
    booted slot filesystem. The record must be a canonical-JSON regular file
    (never a symlink); its slot must later match the PARTUUID-resolved slot.
    """
    path = (
        Path(identity_path)
        if identity_path is not None
        else production_release_identity_path()
    )
    if path.is_symlink():
        raise BootHealthError("booted release identity must not be a symlink")
    try:
        raw_bytes = path.read_bytes()
    except OSError as exc:
        raise BootHealthError(f"booted release identity is unreadable: {exc}") from exc
    if len(raw_bytes) > MAX_BOOT_HEALTH_BYTES:
        raise BootHealthError("booted release identity exceeds Greia bounds")
    try:
        raw = json.loads(raw_bytes.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise BootHealthError(f"booted release identity is not valid JSON: {exc}") from exc
    if not isinstance(raw, dict):
        raise BootHealthError("booted release identity must be a JSON object")
    slot = raw.get("slot")
    if slot not in ("A", "B"):
        raise BootHealthError("booted release identity slot must be A or B")
    release_id = _require_identifier(
        raw.get("release_id"), field_name="release_id", maximum=96
    )
    release_sequence = raw.get("release_sequence")
    if (
        isinstance(release_sequence, bool)
        or not isinstance(release_sequence, int)
        or not 0 <= release_sequence <= 2_147_483_647
    ):
        raise BootHealthError("booted release_sequence is outside Greia bounds")
    if _canonical_bytes(raw) != raw_bytes:
        raise BootHealthError("booted release identity is not canonical JSON")
    return str(slot), release_id, release_sequence


class ProductionActualBootObserver:
    """On-device actual-identity source: kernel cmdline + layout + identity.

    Re-observes the platform facts on every :meth:`observe` call (both
    confirm phases revalidate, so a mid-commit reboot can never be talked
    into the wrong slot): the kernel ``root=PARTUUID=`` fact resolves the
    booted slot through the trusted installed-layout record, and the
    slot-local release identity must agree on that same slot. First install
    uses the same predicate: the machine boots ``SYSTEM_A`` under
    ``FIRST_INSTALL_PENDING`` and this observer simply reports slot ``A``.
    """

    def __init__(
        self,
        *,
        cmdline_path: Path | None = None,
        layout_record_path: Path | None = None,
        release_identity_path: Path | None = None,
    ) -> None:
        self._cmdline_path = (
            Path(cmdline_path) if cmdline_path is not None else production_cmdline_path()
        )
        self._layout_record_path = (
            Path(layout_record_path)
            if layout_record_path is not None
            else production_layout_record_path()
        )
        self._release_identity_path = (
            Path(release_identity_path)
            if release_identity_path is not None
            else production_release_identity_path()
        )

    def observe(self) -> ActualBootIdentity:
        from .persistent_layout import PersistentLayoutError

        root_partuuid = read_kernel_root_partuuid(self._cmdline_path)
        if self._layout_record_path.is_symlink():
            raise BootHealthError("installed layout record must not be a symlink")
        try:
            layout_raw = self._layout_record_path.read_bytes()
        except FileNotFoundError as exc:
            raise BootHealthError(
                "no trusted layout authority: single-root layouts resolve "
                "no A/B actual identity"
            ) from exc
        except OSError as exc:
            raise BootHealthError(
                f"installed layout record is unreadable: {exc}"
            ) from exc
        try:
            document = json.loads(layout_raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as exc:
            raise BootHealthError(
                "installed layout record is not valid JSON"
            ) from exc
        try:
            from .persistent_layout import InstalledLayoutRecord

            record = InstalledLayoutRecord.from_dict(document)
        except PersistentLayoutError as exc:
            raise BootHealthError(
                f"installed layout record is not authoritative: {exc}"
            ) from exc
        candidates = {"A": record.system_a.partuuid}
        if record.system_b is not None:
            candidates["B"] = record.system_b.partuuid
        booted_slot: str | None = None
        for slot, partuuid in candidates.items():
            if partuuid == root_partuuid:
                booted_slot = slot
                break
        if booted_slot is None:
            raise BootHealthError(
                "observed root PARTUUID matches no layout slot: "
                "machine is not running an installed Greia slot"
            )
        identity_slot, release_id, release_sequence = read_booted_release_identity(
            self._release_identity_path
        )
        if identity_slot != booted_slot:
            raise BootHealthError(
                "booted release identity is not the PARTUUID-resolved slot"
            )
        return ActualBootIdentity(
            booted_slot=booted_slot,
            root_partuuid=root_partuuid,
            release_id=release_id,
            release_sequence=release_sequence,
        )


# ---------------------------------------------------------------------------
# Post-intro evidence supplied by the trusted launcher path
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class IntroEvidence:
    """Post-intro interactive evidence for one BOOT_HEALTHY confirmation.

    ``first_frame_visible`` alone (Phase-6 ``READY=1``) never suffices:
    confirmation additionally requires ``intro_completed`` (the full
    7-second intro ran to ``intro_end``) and ``lifecycle_state`` exactly
    ``"interactive_ready"``. ``untrusted_activity_launched`` must be False:
    no untrusted Activity may have launched before health acceptance.
    """

    first_frame_visible: bool
    intro_completed: bool
    lifecycle_state: str
    untrusted_activity_launched: bool

    def __post_init__(self) -> None:
        for field_name in ("first_frame_visible", "intro_completed",
                           "untrusted_activity_launched"):
            if getattr(self, field_name) not in (True, False):
                raise BootHealthError(f"intro evidence {field_name} must be a bool")
        _require_nonempty_text(
            self.lifecycle_state, field_name="lifecycle_state", maximum=64
        )

    @property
    def is_post_intro_interactive(self) -> bool:
        return (
            self.first_frame_visible
            and self.intro_completed
            and self.lifecycle_state == INTERACTIVE_READY_VALUE
            and not self.untrusted_activity_launched
        )


# ---------------------------------------------------------------------------
# One-use credential vault (systemd credentials or equivalently narrow)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class BootHealthCredentialRecord:
    """One live credential bound to a transaction and a boot attempt."""

    transaction_id: str
    boot_attempt: str
    peer_bootstrap_path: str
    peer_uid: int
    token: str

    def as_dict(self) -> dict[str, object]:
        return {
            "boot_attempt": self.boot_attempt,
            "peer_bootstrap_path": self.peer_bootstrap_path,
            "peer_uid": self.peer_uid,
            "schema_version": BOOT_HEALTH_SCHEMA_VERSION,
            "token": self.token,
            "transaction_id": self.transaction_id,
        }


class BootHealthCredentialVault:
    """Owner-only one-use credential store for a single boot attempt.

    Production binds ``vault_dir`` under ``$CREDENTIALS_DIRECTORY`` (see
    :func:`systemd_vault_dir`); R0/R1 tests pass an explicit run directory.
    Files are 0600, canonical JSON, atomically written, and never symlinks.
    Consuming deletes the credential, so a token cannot be replayed.
    """

    def __init__(self, vault_dir: Path) -> None:
        self._vault_dir = Path(vault_dir)

    @property
    def vault_dir(self) -> Path:
        return self._vault_dir

    @property
    def credential_path(self) -> Path:
        return self._vault_dir / CREDENTIAL_FILE_NAME

    @property
    def committing_path(self) -> Path:
        return self._vault_dir / COMMITTING_FILE_NAME

    def provision(
        self,
        *,
        transaction_id: str,
        boot_attempt: str,
        peer_bootstrap_path: str,
        peer_uid: int,
    ) -> BootHealthCredentialRecord:
        """Issue the one-use credential for this transaction/boot attempt."""
        _require_identifier(transaction_id, field_name="transaction_id", maximum=64)
        _require_identifier(boot_attempt, field_name="boot_attempt", maximum=128)
        _require_nonempty_text(
            peer_bootstrap_path, field_name="peer_bootstrap_path", maximum=256
        )
        if isinstance(peer_uid, bool) or not isinstance(peer_uid, int) or peer_uid < 0:
            raise BootHealthError("peer_uid is outside Greia bounds")
        if self.credential_path.exists() and not self.credential_path.is_symlink():
            try:
                live = self._load_live()
            except BootHealthError:
                live = None
            if (
                live is not None
                and live.transaction_id == transaction_id
                and live.boot_attempt == boot_attempt
            ):
                raise BootHealthError(
                    "a live BOOT_HEALTHY credential already exists for this boot attempt"
                )
        record = BootHealthCredentialRecord(
            transaction_id=transaction_id,
            boot_attempt=boot_attempt,
            peer_bootstrap_path=peer_bootstrap_path,
            peer_uid=peer_uid,
            token=secrets.token_hex(32),
        )
        _atomic_write_0600(self.credential_path, _canonical_bytes(record.as_dict()))
        return record

    def consume(
        self,
        *,
        token: str,
        transaction_id: str,
        boot_attempt: str,
        peer_bootstrap_path: str,
    ) -> BootHealthCredentialRecord:
        """Validate and delete the credential (one use); fail closed."""
        _require_token(token, field_name="credential token")
        record = self._load_live()
        if (
            record.token != token
            or record.transaction_id != transaction_id
            or record.boot_attempt != boot_attempt
            or record.peer_bootstrap_path != peer_bootstrap_path
        ):
            raise BootHealthError(
                "BOOT_HEALTHY credential does not match this "
                "transaction, boot attempt and launcher path"
            )
        try:
            self.credential_path.unlink()
        except OSError as exc:
            raise BootHealthError(
                f"BOOT_HEALTHY credential cannot be invalidated: {exc}"
            ) from exc
        try:
            _fsync_directory(self._vault_dir)
        except BootHealthError:
            pass
        return record

    def credential_live(self) -> bool:
        """True when an unread-consumed credential file is present."""
        return self.credential_path.exists() and not self.credential_path.is_symlink()

    def _load_live(self) -> BootHealthCredentialRecord:
        raw = _read_canonical_record(
            self.credential_path, context="BOOT_HEALTHY credential"
        )
        expected = {
            "boot_attempt", "peer_bootstrap_path", "peer_uid",
            "schema_version", "token", "transaction_id",
        }
        if set(raw) != expected:
            raise BootHealthError("BOOT_HEALTHY credential fields are invalid")
        peer_uid = raw["peer_uid"]
        if isinstance(peer_uid, bool) or not isinstance(peer_uid, int) or peer_uid < 0:
            raise BootHealthError("BOOT_HEALTHY credential peer_uid is invalid")
        return BootHealthCredentialRecord(
            transaction_id=_require_identifier(
                raw["transaction_id"], field_name="transaction_id", maximum=64
            ),
            boot_attempt=_require_identifier(
                raw["boot_attempt"], field_name="boot_attempt", maximum=128
            ),
            peer_bootstrap_path=_require_nonempty_text(
                raw["peer_bootstrap_path"],
                field_name="peer_bootstrap_path",
                maximum=256,
            ),
            peer_uid=peer_uid,
            token=_require_token(raw["token"], field_name="credential token"),
        )


# ---------------------------------------------------------------------------
# BOOT_HEALTHY two-phase acceptance protocol
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class HealthyCommittingTicket:
    """Phase-1 success: HEALTHY_COMMITTING entered for one transaction."""

    transaction_id: str
    ticket: str
    first_install: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "first_install": self.first_install,
            "schema_version": BOOT_HEALTH_SCHEMA_VERSION,
            "ticket": self.ticket,
            "transaction_id": self.transaction_id,
        }


@dataclass(frozen=True, slots=True)
class BootHealthOutcome:
    """Phase-2 success: candidate health-committed as the new default."""

    accepted_slot: str
    release_id: str
    release_sequence: int
    first_install: bool
    recovery_medium_if_failed: str

    def as_dict(self) -> dict[str, object]:
        return {
            "accepted_slot": self.accepted_slot,
            "first_install": self.first_install,
            "recovery_medium_if_failed": self.recovery_medium_if_failed,
            "release_id": self.release_id,
            "release_sequence": self.release_sequence,
        }


class BootHealthyProtocol:
    """Trusted one-use post-intro BOOT_HEALTHY acceptance over a coordinator.

    Constructed beside the L7-BOOT :class:`BootTransactionCoordinator` after
    the candidate boot is observed (journal ``CANDIDATE_BOOTING``). The
    protocol owns the credential vault, the HEALTHY_COMMITTING sidecar and
    the untrusted-launch gate; the coordinator owns journal/backend state.
    Actual slot/release identity always comes from ``observer`` — the
    platform revalidates it itself on both phases.
    """

    def __init__(
        self,
        *,
        coordinator: object,
        candidate_root_partuuid: str,
        candidate_release_id: str,
        candidate_release_sequence: int,
        vault: BootHealthCredentialVault,
        observer: ActualBootObserver,
        trusted_bootstrap_path: str,
    ) -> None:
        from .boot_transaction import BootArtifactSet, BootTransactionCoordinator

        if not isinstance(coordinator, BootTransactionCoordinator):
            raise BootHealthError("BOOT_HEALTHY requires a boot transaction coordinator")
        if not isinstance(candidate_root_partuuid, str):
            raise BootHealthError("candidate root PARTUUID must be text")
        candidate_root_partuuid = _require_root_partuuid(
            candidate_root_partuuid, field_name="candidate root PARTUUID"
        )
        candidate_artifacts = coordinator.candidate_artifacts
        if not isinstance(candidate_artifacts, BootArtifactSet):
            raise BootHealthError("coordinator carries no candidate artifact set")
        if candidate_artifacts.root_partuuid != candidate_root_partuuid:
            raise BootHealthError("candidate root PARTUUID does not match the journal")
        if candidate_artifacts.release_id != candidate_release_id:
            raise BootHealthError("candidate release does not match the journal")
        if candidate_artifacts.release_sequence != candidate_release_sequence:
            raise BootHealthError("candidate release sequence does not match the journal")
        if not isinstance(vault, BootHealthCredentialVault):
            raise BootHealthError("BOOT_HEALTHY requires a credential vault")
        if not callable(getattr(observer, "observe", None)):
            raise BootHealthError("BOOT_HEALTHY requires an actual-identity observer")
        _require_nonempty_text(
            trusted_bootstrap_path,
            field_name="trusted_bootstrap_path",
            maximum=256,
        )
        self._coordinator = coordinator
        self._candidate_root_partuuid = candidate_root_partuuid
        self._candidate_release_id = candidate_release_id
        self._candidate_release_sequence = candidate_release_sequence
        self._vault = vault
        self._observer = observer
        self._trusted_bootstrap_path = trusted_bootstrap_path
        self._untrusted_launch_allowed = False

    @property
    def untrusted_launch_allowed(self) -> bool:
        """True only after phase-2 finalize accepted the candidate."""
        return self._untrusted_launch_allowed

    def check_untrusted_launch(self, trust_value: str) -> None:
        """Fail closed for untrusted Activity launch before acceptance."""
        from .trust import PackageTrust

        try:
            trust = PackageTrust(trust_value)
        except ValueError as exc:
            raise BootHealthError(
                f"unknown Activity trust {trust_value!r}; refusing launch"
            ) from exc
        if trust in (
            PackageTrust.BUILT_IN,
            PackageTrust.SIGNED_CURATED,
            PackageTrust.SIGNED_PUBLISHER,
        ):
            return
        if not self._untrusted_launch_allowed:
            raise BootHealthError(
                "untrusted Activity launch is barred until BOOT_HEALTHY acceptance"
            )

    def provision_for_boot_attempt(
        self, *, boot_attempt: str, peer_uid: int
    ) -> BootHealthCredentialRecord:
        """Provision the one-use credential to the trusted launcher path.

        Requires the journal to already hold the observed candidate boot
        (``CANDIDATE_BOOTING``): no credential exists before the machine
        provably runs the candidate.
        """
        from .boot_transaction import BootTransactionState

        journal = self._coordinator.journal
        if journal.state is not BootTransactionState.CANDIDATE_BOOTING:
            raise BootHealthError(
                "BOOT_HEALTHY provisioning requires an observed candidate boot"
            )
        return self._vault.provision(
            transaction_id=journal.transaction_id,
            boot_attempt=boot_attempt,
            peer_bootstrap_path=self._trusted_bootstrap_path,
            peer_uid=peer_uid,
        )

    def confirm(
        self,
        *,
        token: str,
        boot_attempt: str,
        peer_bootstrap_path: str,
        peer_uid: int,
        intro: IntroEvidence,
    ) -> HealthyCommittingTicket:
        """Phase 1: validate every predicate, consume the credential.

        On success the credential is deleted and the ``HEALTHY_COMMITTING``
        sidecar is recorded: the token can never be replayed, and untrusted
        launch stays barred until :meth:`finalize`.
        """
        from .boot_transaction import BootTransactionState

        if peer_bootstrap_path != self._trusted_bootstrap_path:
            raise BootHealthError(
                "BOOT_HEALTHY confirmation is owned by the trusted "
                "launcher bootstrap path"
            )
        if isinstance(peer_uid, bool) or not isinstance(peer_uid, int) or peer_uid < 0:
            raise BootHealthError("peer_uid is outside Greia bounds")
        journal = self._coordinator.journal
        if journal.is_terminal:
            raise BootHealthError(
                "BOOT_HEALTHY confirmation refuses a completed transaction"
            )
        if journal.state is not BootTransactionState.CANDIDATE_BOOTING:
            raise BootHealthError(
                "BOOT_HEALTHY confirmation requires an observed candidate boot"
            )
        if not intro.is_post_intro_interactive:
            raise BootHealthError(
                "BOOT_HEALTHY confirmation requires the completed 7-second "
                "intro, first frame, INTERACTIVE_READY and no untrusted "
                "Activity launched yet"
            )
        observed = self._observer.observe()
        if observed.booted_slot != journal.candidate_slot:
            raise BootHealthError(
                "BOOT_HEALTHY refuses: machine is not running the candidate slot"
            )
        self._require_candidate_identity(observed)
        if journal.release_id != observed.release_id:
            raise BootHealthError(
                "BOOT_HEALTHY refuses: actual release does not match the pending release"
            )
        if journal.release_sequence != observed.release_sequence:
            raise BootHealthError(
                "BOOT_HEALTHY refuses: actual release sequence is not pending"
            )
        self._vault.consume(
            token=token,
            transaction_id=journal.transaction_id,
            boot_attempt=boot_attempt,
            peer_bootstrap_path=self._trusted_bootstrap_path,
        )
        ticket = HealthyCommittingTicket(
            transaction_id=journal.transaction_id,
            ticket=secrets.token_hex(32),
            first_install=journal.first_install,
        )
        sidecar: dict[str, object] = {
            "boot_attempt": boot_attempt,
            "booted_slot": observed.booted_slot,
            "candidate_slot": journal.candidate_slot,
            "first_install": journal.first_install,
            "release_id": observed.release_id,
            "release_sequence": observed.release_sequence,
            "root_partuuid": observed.root_partuuid,
            "schema_version": BOOT_HEALTH_SCHEMA_VERSION,
            "ticket": ticket.ticket,
            "transaction_id": ticket.transaction_id,
        }
        _atomic_write_0600(self._vault.committing_path, _canonical_bytes(sidecar))
        return ticket

    def finalize(self, ticket: HealthyCommittingTicket) -> BootHealthOutcome:
        """Phase 2: revalidate, commit through the coordinator, open the gate."""
        from .boot_transaction import BootTransactionState

        if not isinstance(ticket, HealthyCommittingTicket):
            raise BootHealthError("BOOT_HEALTHY finalize requires a committing ticket")
        _require_token(ticket.ticket, field_name="committing ticket")
        sidecar = _read_canonical_record(
            self._vault.committing_path, context="HEALTHY_COMMITTING record"
        )
        expected_keys = {
            "boot_attempt", "booted_slot", "candidate_slot", "first_install",
            "release_id", "release_sequence", "root_partuuid", "schema_version",
            "ticket", "transaction_id",
        }
        if set(sidecar) != expected_keys:
            raise BootHealthError("HEALTHY_COMMITTING record fields are invalid")
        if sidecar["ticket"] != ticket.ticket:
            raise BootHealthError("HEALTHY_COMMITTING ticket does not match")
        journal = self._coordinator.journal
        if sidecar["transaction_id"] != ticket.transaction_id:
            raise BootHealthError("HEALTHY_COMMITTING transaction does not match")
        if sidecar["transaction_id"] != journal.transaction_id:
            raise BootHealthError(
                "HEALTHY_COMMITTING transaction is stale for this journal"
            )
        if journal.is_terminal:
            raise BootHealthError(
                "BOOT_HEALTHY finalize refuses a completed transaction"
            )
        if journal.state is not BootTransactionState.CANDIDATE_BOOTING:
            raise BootHealthError(
                "BOOT_HEALTHY finalize requires the candidate boot to still hold"
            )
        observed = self._observer.observe()
        if observed.booted_slot != journal.candidate_slot:
            raise BootHealthError(
                "BOOT_HEALTHY finalize refuses: machine left the candidate slot"
            )
        self._require_candidate_identity(observed)
        if (
            observed.release_id != journal.release_id
            or observed.release_sequence != journal.release_sequence
        ):
            raise BootHealthError(
                "BOOT_HEALTHY finalize refuses: actual release moved under commit"
            )
        committed = self._coordinator.commit()
        try:
            self._vault.committing_path.unlink()
        except OSError as exc:
            raise BootHealthError(
                f"HEALTHY_COMMITTING record cannot be retired: {exc}"
            ) from exc
        self._untrusted_launch_allowed = True
        first_install = bool(sidecar["first_install"])
        return BootHealthOutcome(
            accepted_slot=committed.default_slot,
            release_id=journal.release_id,
            release_sequence=journal.release_sequence,
            first_install=first_install,
            recovery_medium_if_failed=(
                SETUP_MEDIUM if first_install else ACCEPTED_SLOT_MEDIUM
            ),
        )

    def _require_candidate_identity(self, observed: ActualBootIdentity) -> None:
        if observed.root_partuuid != self._candidate_root_partuuid:
            raise BootHealthError(
                "BOOT_HEALTHY refuses: actual root PARTUUID is not the candidate root"
            )
        if observed.release_id != self._candidate_release_id:
            raise BootHealthError(
                "BOOT_HEALTHY refuses: actual release is not the pending release"
            )
        if observed.release_sequence != self._candidate_release_sequence:
            raise BootHealthError(
                "BOOT_HEALTHY refuses: actual release sequence is not pending"
            )


# ---------------------------------------------------------------------------
# Root-owned one-use capability authority (P4.3)
# ---------------------------------------------------------------------------
#
# P4.3 moves BOOT_HEALTHY capability generation to root. The launcher-side
# ``BootHealthCredentialVault`` above stays for the established in-process
# protocol path (owned by its existing tests); this authority is the
# production root side:
#
# - the root generator (``greia-boot-health-credential.service``) issues a
#   capability only when a real pending transaction exists (first-install or
#   update journal, non-terminal). A plain boot issues nothing and writes
#   nothing: a bounded no-op.
# - the authoritative record lives in a root-only directory and stores only
#   the SHA-256 digest of the token bound to
#   ``(transaction_id, boot_attempt, peer_bootstrap_path)``. The raw token
#   never rests on the root side outside the delivery file. The record also
#   carries ``peer_uid`` as provenance/audit metadata only: it is validated
#   for shape (non-negative int) but is NOT a consume-time binding —
#   ``verify_and_consume`` never gates on it. Activities share the launcher
#   UID, so UID gating is not an Activity-isolation boundary (isolation
#   rests on env/mount hiding); presenter-UID enforcement, if ever added,
#   is owned by the socket/verifier seam (POSTR1-P4-HEALTH-PROOF2).
# - delivery to the unprivileged launcher is the raw token in a separate
#   root-owned directory the launcher can only read. The launcher loader
#   (``greia_launcher.boot_health.maybe_load_production_token``) opens it
#   ``O_RDONLY`` and never writes: double provisioning, replay, copies and
#   stale boot attempts all fail closed at ``verify_and_consume``.
# - ``boot_attempt`` is the kernel boot ID (``/proc/sys/kernel/random/boot_id``),
#   a platform-owned per-boot fact: a token copied from an earlier boot never
#   matches the current attempt.
#
# Both directories live under ``/run`` (fresh tmpfs every boot), so a
# capability can never survive into a later boot: staleness across reboots
# is structurally impossible, not merely checked.

#: Environment override for the root-only authoritative record directory.
CAPABILITY_AUTHORITY_DIR_ENV = "GREIA_BOOT_HEALTH_AUTHORITY_DIR"

#: Production root-only authoritative record directory (0700 root).
CAPABILITY_AUTHORITY_DEFAULT = "/run/greia-boot-health-authority"

#: Environment override for the read-only delivery directory.
CAPABILITY_DELIVERY_DIR_ENV = "GREIA_BOOT_HEALTH_DELIVERY_DIR"

#: Production delivery directory (root-owned; readable, never writable, by
#: the launcher identity).
CAPABILITY_DELIVERY_DEFAULT = "/run/greia-os/boot-health"

#: Authoritative digest record inside the authority directory.
CAPABILITY_RECORD_FILE_NAME = "boot-healthy-capability.json"

#: Raw one-use token inside the delivery directory.
CAPABILITY_DELIVERY_FILE_NAME = "boot-healthy-token"

#: Authority directory and record modes: root only.
CAPABILITY_AUTHORITY_DIR_MODE = 0o700

#: Delivery directory mode: root-owned, launcher-readable, never writable
#: by the launcher (group ownership is set to the launcher identity by the
#: root generator; the mode alone already denies launcher writes).
CAPABILITY_DELIVERY_DIR_MODE = 0o750

#: Delivery token file mode: launcher-readable, launcher-unwritable.
CAPABILITY_DELIVERY_FILE_MODE = 0o640

#: Kernel boot-ID source carrying the platform-owned per-boot attempt fact.
BOOT_ID_PATH_ENV = "GREIA_BOOT_ID_PATH"
BOOT_ID_PATH_DEFAULT = "/proc/sys/kernel/random/boot_id"

#: Login name of the unprivileged launcher identity allowed to present.
LAUNCHER_USER_NAME = "greiakid"

#: Environment override for the presenting launcher UID (tests inject the
#: current UID; production resolves ``greiakid`` by name).
CAPABILITY_PEER_UID_ENV = "GREIA_BOOT_HEALTH_PEER_UID"

#: Environment override for the trusted launcher bootstrap path (the single
#: source of the identifier stays
#: ``greia_launcher.boot_health.TRUSTED_BOOTSTRAP_PATH``; the override
#: exists so tests and the generator unit name it explicitly).
CAPABILITY_PEER_PATH_ENV = "GREIA_BOOT_HEALTH_PEER_PATH"

#: Fallback trusted launcher bootstrap path when the environment names none.
#: Must equal ``greia_launcher.boot_health.TRUSTED_BOOTSTRAP_PATH``; the
#: capability test module asserts that equality.
CAPABILITY_PEER_PATH_DEFAULT = "greia_launcher.bootstrap:LauncherBootstrap"

#: Upper bound for the delivery token file bytes (small by construction).
MAX_CAPABILITY_DELIVERY_BYTES = 256


def capability_authority_dir() -> Path:
    """Resolve the root-only authoritative record directory."""
    override = os.environ.get(CAPABILITY_AUTHORITY_DIR_ENV, "").strip()
    return Path(override) if override else Path(CAPABILITY_AUTHORITY_DEFAULT)


def capability_delivery_dir() -> Path:
    """Resolve the read-only delivery directory for the launcher token."""
    override = os.environ.get(CAPABILITY_DELIVERY_DIR_ENV, "").strip()
    return Path(override) if override else Path(CAPABILITY_DELIVERY_DEFAULT)


def capability_peer_bootstrap_path() -> str:
    """Resolve the trusted launcher bootstrap path bound into capabilities."""
    override = os.environ.get(CAPABILITY_PEER_PATH_ENV, "").strip()
    return override if override else CAPABILITY_PEER_PATH_DEFAULT


def boot_id_path() -> Path:
    """Resolve the kernel boot-ID source (env override or the live file)."""
    override = os.environ.get(BOOT_ID_PATH_ENV, "").strip()
    return Path(override) if override else Path(BOOT_ID_PATH_DEFAULT)


def read_boot_id(path: Path | None = None) -> str:
    """Return the platform-owned per-boot attempt fact (kernel boot ID).

    Reads ``/proc/sys/kernel/random/boot_id`` on device (``O_RDONLY``: never
    written). The value is a fresh UUID every boot, so a capability bound to
    it cannot be replayed from an earlier boot.
    """
    source = Path(path) if path is not None else boot_id_path()
    if source.is_symlink():
        raise BootHealthError("kernel boot ID must not be a symlink")
    try:
        descriptor = os.open(os.fspath(source), os.O_RDONLY)
    except OSError as exc:
        raise BootHealthError(f"kernel boot ID is unreadable: {exc}") from exc
    try:
        with os.fdopen(descriptor, "rb") as handle:
            raw = handle.read(MAX_CAPABILITY_DELIVERY_BYTES + 1)
    except OSError as exc:
        raise BootHealthError(f"kernel boot ID read failed: {exc}") from exc
    if len(raw) > MAX_CAPABILITY_DELIVERY_BYTES:
        raise BootHealthError("kernel boot ID exceeds Greia bounds")
    try:
        text = raw.decode("utf-8").strip()
    except UnicodeDecodeError as exc:
        raise BootHealthError("kernel boot ID is not valid text") from exc
    try:
        parsed = uuid.UUID(text)
    except ValueError as exc:
        raise BootHealthError("kernel boot ID is not a UUID") from exc
    if str(parsed) != text.lower():
        raise BootHealthError("kernel boot ID is not a canonical UUID")
    return str(parsed)


def resolve_capability_peer_uid() -> int:
    """Return the UID authorized to present the capability (the launcher).

    Explicit ``GREIA_BOOT_HEALTH_PEER_UID`` wins (tests); otherwise the
    ``greiakid`` login is resolved by name so image-assigned dynamic system
    UIDs need no hardcoding. Unresolvable names fail closed.
    """
    override = os.environ.get(CAPABILITY_PEER_UID_ENV, "").strip()
    if override:
        try:
            uid = int(override, 10)
        except ValueError as exc:
            raise BootHealthError(
                "capability peer UID override is not an integer"
            ) from exc
        if isinstance(uid, bool) or uid < 0 or uid > 2**32 - 1:
            raise BootHealthError("capability peer UID is outside Greia bounds")
        return uid
    try:
        import pwd as _pwd
    except ImportError as exc:  # pragma: no cover - POSIX target always has pwd
        raise BootHealthError("capability peer identity is unresolvable") from exc
    try:
        return int(_pwd.getpwnam(LAUNCHER_USER_NAME).pw_uid)
    except KeyError as exc:
        raise BootHealthError(
            f"launcher identity {LAUNCHER_USER_NAME!r} is unknown; "
            "refusing to issue a capability"
        ) from exc


def _capability_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _ensure_root_dir(path: Path, mode: int) -> None:
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise BootHealthError(
            f"capability directory is not creatable: {exc}"
        ) from exc
    try:
        os.chmod(path, mode)
    except OSError as exc:
        raise BootHealthError(
            f"capability directory mode cannot be enforced: {exc}"
        ) from exc
    if path.is_symlink():
        raise BootHealthError("capability directory must not be a symlink")
    try:
        current = stat.S_IMODE(os.stat(path).st_mode)
    except OSError as exc:
        raise BootHealthError(f"capability directory is not statable: {exc}") from exc
    if current != mode:
        raise BootHealthError("capability directory mode is not authoritative")


def _chown_launcher_readable(path: Path) -> None:
    """Best-effort group grant so the launcher identity can read delivery.

    Production (root generator): sets group ``greiakid`` on the delivery
    directory/file, yielding 0750/0640 root:greiakid. Any failure (tests run
    unprivileged, unknown names) is ignored: the mode alone already denies
    launcher writes, and readability in production additionally follows from
    the root-owned generator running before the launcher unit.
    """
    try:
        import grp as _grp

        gid = _grp.getgrnam(LAUNCHER_USER_NAME).gr_gid
    except (ImportError, KeyError, OSError):
        return
    try:
        os.chown(path, 0, gid)
    except OSError:
        return


@dataclass(frozen=True, slots=True)
class BootHealthCapabilityRecord:
    """Authoritative root-side record: digest-only, never the raw token.

    ``peer_uid`` is provenance/audit metadata (shape-validated), not a
    consume-time binding enforced by ``verify_and_consume``.
    """

    transaction_id: str
    boot_attempt: str
    peer_bootstrap_path: str
    peer_uid: int
    token_digest: str

    def as_dict(self) -> dict[str, object]:
        return {
            "boot_attempt": self.boot_attempt,
            "peer_bootstrap_path": self.peer_bootstrap_path,
            "peer_uid": self.peer_uid,
            "schema_version": BOOT_HEALTH_SCHEMA_VERSION,
            "token_digest": self.token_digest,
            "transaction_id": self.transaction_id,
        }


@dataclass(frozen=True, slots=True)
class IssuedBootHealthCapability:
    """Generator-side issue result: the one raw token plus its bindings."""

    transaction_id: str
    boot_attempt: str
    token: str


class BootHealthCapabilityAuthority:
    """Root-owned one-use capability store: digest record plus delivery.

    ``authority_dir`` is root-only (0700): it holds the canonical digest
    record. ``delivery_dir`` is root-owned and launcher-readable (0750,
    token file 0640): it holds only the raw token. The launcher loader never
    touches the authority directory; verification compares the SHA-256 digest
    of the presented token with constant-time equality and deletes both files
    on success, so the token is one-use and a copied or stale token fails.
    """

    def __init__(self, authority_dir: Path, delivery_dir: Path) -> None:
        self._authority_dir = Path(authority_dir)
        self._delivery_dir = Path(delivery_dir)

    @property
    def authority_dir(self) -> Path:
        return self._authority_dir

    @property
    def delivery_dir(self) -> Path:
        return self._delivery_dir

    @property
    def record_path(self) -> Path:
        return self._authority_dir / CAPABILITY_RECORD_FILE_NAME

    @property
    def delivery_path(self) -> Path:
        return self._delivery_dir / CAPABILITY_DELIVERY_FILE_NAME

    def issue_for_pending_journal(
        self,
        journal: object,
        *,
        boot_attempt: str,
        peer_bootstrap_path: str,
        peer_uid: int,
    ) -> IssuedBootHealthCapability:
        """Issue the one-use capability for a real pending transaction.

        ``journal`` is the non-terminal first-install or update journal the
        generator loaded read-only: only its ``transaction_id`` and
        ``is_terminal`` are consulted (duck-typed, never asserted by the
        caller beyond the loaded journal object). A terminal journal fails
        closed; a missing journal never reaches this call (the generator
        returns its bounded no-op instead). Issuing twice for the same
        ``(transaction_id, boot_attempt)`` fails closed; a live record for a
        superseded transaction is replaced (it could never verify again).
        """
        transaction_id = _require_identifier(
            getattr(journal, "transaction_id", None),
            field_name="transaction_id",
            maximum=64,
        )
        if bool(getattr(journal, "is_terminal", True)):
            raise BootHealthError(
                "capability issue refuses a completed transaction"
            )
        _require_identifier(boot_attempt, field_name="boot_attempt", maximum=128)
        _require_nonempty_text(
            peer_bootstrap_path, field_name="peer_bootstrap_path", maximum=256
        )
        if isinstance(peer_uid, bool) or not isinstance(peer_uid, int) or peer_uid < 0:
            raise BootHealthError("peer_uid is outside Greia bounds")
        live = self._read_live_record()
        if (
            live is not None
            and live.transaction_id == transaction_id
            and live.boot_attempt == boot_attempt
        ):
            raise BootHealthError(
                "a live BOOT_HEALTHY capability already exists for this "
                "transaction and boot attempt"
            )
        token = secrets.token_hex(32)
        record = BootHealthCapabilityRecord(
            transaction_id=transaction_id,
            boot_attempt=boot_attempt,
            peer_bootstrap_path=peer_bootstrap_path,
            peer_uid=peer_uid,
            token_digest=_capability_digest(token),
        )
        _ensure_root_dir(self._authority_dir, CAPABILITY_AUTHORITY_DIR_MODE)
        _atomic_write_0600(self.record_path, _canonical_bytes(record.as_dict()))
        _ensure_root_dir(self._delivery_dir, CAPABILITY_DELIVERY_DIR_MODE)
        payload = (token + "\n").encode("utf-8")
        _atomic_write_0600(self.delivery_path, payload)
        try:
            os.chmod(self.delivery_path, CAPABILITY_DELIVERY_FILE_MODE)
        except OSError as exc:
            raise BootHealthError(
                f"delivery token mode cannot be enforced: {exc}"
            ) from exc
        _chown_launcher_readable(self._delivery_dir)
        _chown_launcher_readable(self.delivery_path)
        return IssuedBootHealthCapability(
            transaction_id=transaction_id,
            boot_attempt=boot_attempt,
            token=token,
        )

    def verify_and_consume(
        self,
        *,
        token: str,
        transaction_id: str,
        boot_attempt: str,
        peer_bootstrap_path: str,
    ) -> BootHealthCapabilityRecord:
        """Verify the bindings and consume the capability (exactly once).

        Enforced binding set: token digest + ``transaction_id`` +
        ``boot_attempt`` + ``peer_bootstrap_path``. ``peer_uid`` is
        explicitly NOT enforced here: the stored value is provenance/audit
        metadata (shape-validated on load) and presenter-UID attestation
        lives at the socket/verifier seam outside this authority.
        Any mismatch (unknown token, copied token on another transaction or
        boot attempt, stale boot ID, wrong presenter path) fails closed
        without deleting the live record, so a failed guess never burns the
        real capability. Success deletes both the authoritative record and
        the delivery token: a replay finds nothing live and fails.
        """
        _require_token(token, field_name="credential token")
        record = self._load_live()
        presented = _capability_digest(token)
        if (
            not hmac.compare_digest(presented, record.token_digest)
            or record.transaction_id != transaction_id
            or record.boot_attempt != boot_attempt
            or record.peer_bootstrap_path != peer_bootstrap_path
        ):
            raise BootHealthError(
                "BOOT_HEALTHY capability does not match this transaction, "
                "boot attempt and launcher path"
            )
        for path in (self.record_path, self.delivery_path):
            try:
                path.unlink()
            except FileNotFoundError:
                continue
            except OSError as exc:
                raise BootHealthError(
                    f"BOOT_HEALTHY capability cannot be invalidated: {exc}"
                ) from exc
        for directory in (self._authority_dir, self._delivery_dir):
            try:
                _fsync_directory(directory)
            except BootHealthError:
                pass
        return record

    def capability_live(self) -> bool:
        """True when an unconsumed authoritative record is present."""
        return self._read_live_record() is not None

    def _read_live_record(self) -> BootHealthCapabilityRecord | None:
        if self.record_path.is_symlink() or not self.record_path.is_file():
            return None
        try:
            return self._load_live()
        except BootHealthError:
            return None

    def _load_live(self) -> BootHealthCapabilityRecord:
        raw = _read_canonical_record(
            self.record_path, context="BOOT_HEALTHY capability"
        )
        expected = {
            "boot_attempt", "peer_bootstrap_path", "peer_uid",
            "schema_version", "token_digest", "transaction_id",
        }
        if set(raw) != expected:
            raise BootHealthError("BOOT_HEALTHY capability fields are invalid")
        peer_uid = raw["peer_uid"]
        if isinstance(peer_uid, bool) or not isinstance(peer_uid, int) or peer_uid < 0:
            raise BootHealthError("BOOT_HEALTHY capability peer_uid is invalid")
        digest = raw["token_digest"]
        if (
            not isinstance(digest, str)
            or len(digest) != 64
            or any(char not in _HEX_LOWER for char in digest)
        ):
            raise BootHealthError("BOOT_HEALTHY capability digest is invalid")
        return BootHealthCapabilityRecord(
            transaction_id=_require_identifier(
                raw["transaction_id"], field_name="transaction_id", maximum=64
            ),
            boot_attempt=_require_identifier(
                raw["boot_attempt"], field_name="boot_attempt", maximum=128
            ),
            peer_bootstrap_path=_require_nonempty_text(
                raw["peer_bootstrap_path"],
                field_name="peer_bootstrap_path",
                maximum=256,
            ),
            peer_uid=peer_uid,
            token_digest=digest,
        )


def default_capability_authority(
    authority_dir: Path | None = None,
    delivery_dir: Path | None = None,
) -> BootHealthCapabilityAuthority:
    """Compose the authority from explicit dirs or the production binds."""
    return BootHealthCapabilityAuthority(
        authority_dir=Path(authority_dir)
        if authority_dir is not None
        else capability_authority_dir(),
        delivery_dir=Path(delivery_dir)
        if delivery_dir is not None
        else capability_delivery_dir(),
    )


# ---------------------------------------------------------------------------
# Root generator entry (greia-boot-health-credential.service)
# ---------------------------------------------------------------------------


def load_pending_boot_journal(
    *,
    boot_journal_dir: Path | None = None,
    update_state_dir: Path | None = None,
) -> tuple[Path, object] | None:
    """Return ``(journal_dir, journal)`` for the single pending transaction.

    Read-only: loading never writes. ``None`` is the normal plain-boot case
    (no pending journal anywhere). Both-pending or corrupt journals fail
    closed rather than guessing.
    """
    from .boot_transaction import JOURNAL_FILE_NAME, BootJournalError

    try:
        from .system_updates import UPDATE_JOURNAL_DIR_NAME
    except ImportError as exc:
        raise BootHealthError(f"update journal layout is unavailable: {exc}") from exc

    candidates: list[tuple[Path, object]] = []
    update_root = (
        Path(update_state_dir)
        if update_state_dir is not None
        else Path("/var/lib/greia-os")
    )
    install_dir = (
        Path(boot_journal_dir)
        if boot_journal_dir is not None
        else Path("/var/lib/greia-os/boot-journal")
    )
    journal_dirs = [
        update_root / "system-updates" / UPDATE_JOURNAL_DIR_NAME,
        install_dir,
    ]
    for journal_dir in journal_dirs:
        candidate = journal_dir / JOURNAL_FILE_NAME
        if candidate.is_symlink():
            raise BootHealthError("boot journal must not be a symlink")
        if not candidate.is_file():
            continue
        try:
            from .boot_transaction import BootTransactionJournal

            journal = BootTransactionJournal.load(journal_dir)
        except BootJournalError as exc:
            raise BootHealthError(
                f"boot journal is not authoritative: {exc}"
            ) from exc
        except OSError as exc:
            raise BootHealthError(f"boot journal is unreadable: {exc}") from exc
        if journal.is_terminal:
            continue
        candidates.append((journal_dir, journal))
    if len(candidates) > 1:
        raise BootHealthError(
            "ambiguous boot authority: update and first-install journals "
            "are both pending; refusing to guess"
        )
    if not candidates:
        return None
    return candidates[0]


def maybe_issue_boot_capability(
    *,
    authority: BootHealthCapabilityAuthority | None = None,
    boot_journal_dir: Path | None = None,
    update_state_dir: Path | None = None,
    boot_id: str | None = None,
    peer_bootstrap_path: str | None = None,
    peer_uid: int | None = None,
) -> IssuedBootHealthCapability | None:
    """Issue the boot-attempt capability for the pending transaction, if any.

    Plain boots (no pending journal) return ``None`` and write nothing: a
    bounded no-op. A pending transaction yields exactly one capability bound
    to the kernel boot ID of this boot; double issuance for the same
    transaction and boot fails closed inside the authority.
    """
    pending = load_pending_boot_journal(
        boot_journal_dir=boot_journal_dir,
        update_state_dir=update_state_dir,
    )
    if pending is None:
        return None
    _, journal = pending
    owner = authority if authority is not None else default_capability_authority()
    attempt = boot_id if boot_id is not None else read_boot_id()
    return owner.issue_for_pending_journal(
        journal,
        boot_attempt=attempt,
        peer_bootstrap_path=peer_bootstrap_path
        if peer_bootstrap_path is not None
        else capability_peer_bootstrap_path(),
        peer_uid=peer_uid if peer_uid is not None else resolve_capability_peer_uid(),
    )


def main(argv: list[str] | None = None) -> int:
    """Root generator entry for ``greia-boot-health-credential.service``.

    ``--issue-for-pending`` issues the one-use capability when a pending
    transaction exists and exits ``0`` having printed ``ISSUED``; with no
    pending journal it prints ``NO_PENDING`` and exits ``0`` without writing
    anything. Any refusal exits ``1`` fail-closed (never a partial write:
    the authority writes the record before the delivery token, and a failed
    run leaves at most a live record the next verify still gates on).
    """
    import argparse as _argparse

    parser = _argparse.ArgumentParser(
        prog="greia_platform.boot_health",
        description="Root BOOT_HEALTHY capability generator (P4.3).",
    )
    parser.add_argument(
        "--issue-for-pending",
        action="store_true",
        help="issue the one-use capability for the pending transaction, if any",
    )
    parser.add_argument("--authority-dir", default=None)
    parser.add_argument("--delivery-dir", default=None)
    parser.add_argument("--boot-journal-dir", default=None)
    parser.add_argument("--update-state-dir", default=None)
    parser.add_argument("--boot-id-path", default=None)
    args = parser.parse_args(list(argv or []))
    if not args.issue_for_pending:
        parser.print_usage()
        return 2
    if args.boot_id_path is not None:
        os.environ[BOOT_ID_PATH_ENV] = args.boot_id_path
    authority = default_capability_authority(
        authority_dir=Path(args.authority_dir)
        if args.authority_dir is not None
        else None,
        delivery_dir=Path(args.delivery_dir)
        if args.delivery_dir is not None
        else None,
    )
    try:
        issued = maybe_issue_boot_capability(
            authority=authority,
            boot_journal_dir=Path(args.boot_journal_dir)
            if args.boot_journal_dir is not None
            else None,
            update_state_dir=Path(args.update_state_dir)
            if args.update_state_dir is not None
            else None,
        )
    except BootHealthError as exc:
        print(f"REFUSED: {exc}")
        return 1
    if issued is None:
        print("NO_PENDING")
        return 0
    print(f"ISSUED: {issued.transaction_id}")
    return 0


if __name__ == "__main__":  # pragma: no cover - service entry
    raise SystemExit(main())
