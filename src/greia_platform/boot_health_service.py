"""Root-owned semantic CONFIRM_BOOT_HEALTH service (P4.2).

The single root-owned boot-health endpoint owns all privileged
health-commit mutation for both the first-install pending journal
(``GREIA_BOOT_JOURNAL_DIR``, default ``/var/lib/greia-os/boot-journal``)
and the update pending journal (``<update-state>/system-updates/journal``),
so the unprivileged launcher never writes ``/boot``, ``/etc/greia-os`` or
root update state (``POSTR1-P4-HEALTH-PROOF`` removes the launcher-side
mutation; this service is its replacement owner).

The endpoint exposes exactly one semantic operation,
``CONFIRM_BOOT_HEALTH``, over the ``greia-boot-health`` socket. It takes
no selectors: no slot, journal name, path, device, command or arbitrary
journal operation is accepted and raw-authority params fail closed. The
service selects the pending journal internally from Greia-owned state and
refuses when both journals are pending rather than guessing.

Mutation ownership per journal kind:

- update journal: delegated to the existing ``system_updates`` mutation
  path (``SystemUpdateServiceAuthority.confirm_boot_health`` over
  ``SlotBackedSystemUpdateBackend``: reconcile, ``commit_accepted``,
  ``write_accepted_sequence``, journal ``ACCEPTED``, layout-authority
  advancement). This module adds no second writer or health state machine.
- first-install journal: composed from the same reused primitives the
  update backend is built on (``BootTransactionCoordinator.resume`` +
  ``observe_boot`` + ``commit`` over the attached ``GrubEnvBackend``,
  ``write_accepted_sequence``, layout-authority convergence check,
  ``BootHistory``). There is no pre-existing first-install service path;
  the primitives are shared, not reimplemented.

Both paths finish with one bounded boot-history terminal record
(``committed`` milestone, ``confirmed`` health result, ``accepted``
terminal state) through the reused ``BootHistory`` ring.

The one-use capability is mandatory: it is supplied through the narrow
injected :class:`BootHealthCapabilityVerifier` protocol implemented by
``POSTR1-P4-CAPABILITY-LIFECYCLE`` and consumed before any commit. A
missing or invalid (including replayed) capability fails closed. No
launcher-writable vault is implemented here.

Transport reuses ``greia_platform.privileged_channel`` (kernel-attested
peers, bounded framing, interactive-boot gating, raw-authority rejection)
and ``greia_platform.system_updates.attest_peer_from_connection`` for
socket peer attestation. No sockets are opened here; ``main`` serves the
socket-activated file descriptor only.
"""

from __future__ import annotations

import os
import socket
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Protocol

from .boot_transaction import (
    BootArtifactSet,
    BootHistory,
    BootJournalError,
    BootTransactionCoordinator,
    BootTransactionError,
    BootTransactionJournal,
    BootTransactionState,
)
from .grub_ab import GrubEnvBackend
from .privileged_channel import (
    MAX_MESSAGE_BYTES,
    PeerCredential,
    PrivilegedChannelError,
    authorize_peer,
    decode_request,
    encode_request,
    encode_response,
    format_log_record,
    new_transaction_id,
    reject_raw_authority,
    require_interactive_boot,
)
from .system_updates import (
    UPDATE_STATE_DIR_DEFAULT,
    UPDATE_STATE_DIR_ENV,
    SystemUpdateError,
    UpdateBackendUnavailable,
    installed_layout_record_path,
    load_installed_layout_record,
    resolve_grubenv_dir,
    write_accepted_sequence,
)


class BootHealthServiceError(RuntimeError):
    """Boot-health semantic operation failed fail-closed."""


#: The only semantic operation of the boot-health service. No raw
#: selectors exist: the pending journal is resolved internally.
BOOT_HEALTH_OPS = ("CONFIRM_BOOT_HEALTH",)

#: Peer UIDs authorized by default. Root owns the privileged unit; the
#: numeric caller UID (the unprivileged launcher identity) is injected by
#: the service composition (tests inject small synthetic UIDs instead of
#: hardcoding production IDs).
BOOT_HEALTH_ALLOWED_UIDS = (0,)

#: Environment carrying the optional extra caller UID(s) for the live
#: composition (comma-separated integers, e.g. the greiakid launcher UID
#: provisioned by the image build). Absent means root-only.
BOOT_HEALTH_CALLER_UID_ENV = "GREIA_BOOT_HEALTH_CALLER_UID"

#: Environment carrying the image-owned launcher identity name (e.g.
#: ``greiakid``) provisioned by the shipped service unit. Resolved to a
#: UID by name at composition time; absent means no name-provisioned
#: caller. An unresolvable name fails closed.
BOOT_HEALTH_CALLER_ENV = "GREIA_BOOT_HEALTH_CALLER"

#: AF_UNIX listener node owned by the socket unit (mirrors the
#: system-update socket naming).
BOOT_HEALTH_SOCKET_PATH = "/run/greia-os/boot-health.sock"

#: First-install boot journal directory (image-integration parameter).
BOOT_JOURNAL_DIR_ENV = "GREIA_BOOT_JOURNAL_DIR"
BOOT_JOURNAL_DIR_DEFAULT = "/var/lib/greia-os/boot-journal"

#: Bounded boot-history ring directory (PERSIST bind-visible alias).
BOOT_HISTORY_DIR_ENV = "GREIA_BOOT_HISTORY_DIR"
BOOT_HISTORY_DIR_DEFAULT = "/var/lib/greia-os/diagnostics"

#: Slot-local finalization receipt visible on the running system.
FINALIZATION_RECEIPT_ENV = "GREIA_FINALIZATION_RECEIPT_PATH"
FINALIZATION_RECEIPT_DEFAULT = "/etc/greia-os/finalization-receipt.json"

#: The single request param: the one-use capability token. It is
#: authentication, never a selector: no slot, journal, path, device,
#: command or journal operation may appear beside it.
CAPABILITY_PARAM = "capability"

#: Upper bound for the capability token text (the verifier owns semantics;
#: over-long tokens fail closed here before verifier contact).
MAX_CAPABILITY_CHARS = 512


class BootHealthCapabilityVerifier(Protocol):
    """Narrow one-use capability seam owned by CAPABILITY-LIFECYCLE.

    Implementations verify the token and consume it (one use: a replayed
    token must raise). Any refusal raises; the service maps every
    verifier exception to a fail-closed refusal before any mutation.
    """

    def verify_and_consume(self, *, token: str) -> Mapping[str, object]: ...


class BootHealthArtifactResolver(Protocol):
    """Resolve coordinator artifact sets for a first-install journal.

    Sources are Greia-owned state only (layout record, finalization
    receipt), never request bytes. The update journal needs no resolver:
    its mutation path reuses the ``system_updates`` backend directly.
    """

    def resolve(
        self, journal: BootTransactionJournal
    ) -> tuple[BootArtifactSet, BootArtifactSet]: ...


def _require_capability_token(params: Mapping[str, object]) -> str:
    """Extract the single capability token; refuse selectors/raw authority."""
    if not isinstance(params, dict) or set(params) != {CAPABILITY_PARAM}:
        raise BootHealthServiceError(
            "CONFIRM_BOOT_HEALTH takes no selectors; it carries only "
            "the one-use capability token"
        )
    token = params[CAPABILITY_PARAM]
    if (
        not isinstance(token, str)
        or not token
        or len(token.encode("utf-8")) > MAX_CAPABILITY_CHARS
    ):
        raise BootHealthServiceError("capability token is outside Greia bounds")
    return token


def resolve_allowed_uids(
    *, extra: str | None = None, caller: str | None = None
) -> tuple[int, ...]:
    """Compose the peer allowlist: root plus optional provisioned callers.

    The extra caller UIDs come from ``GREIA_BOOT_HEALTH_CALLER_UID``
    (comma-separated integers); unparseable values fail closed. The
    image-owned launcher identity name comes from
    ``GREIA_BOOT_HEALTH_CALLER`` (e.g. ``greiakid``) and is resolved to
    its UID by name; an unresolvable name fails closed. Absent means
    root-only.
    """
    raw = extra if extra is not None else os.environ.get(
        BOOT_HEALTH_CALLER_UID_ENV, ""
    )
    allowed: list[int] = [0]
    for piece in str(raw).split(","):
        piece = piece.strip()
        if not piece:
            continue
        try:
            uid = int(piece, 10)
        except ValueError as exc:
            raise BootHealthServiceError(
                "provisioned boot-health caller UID is not an integer"
            ) from exc
        if isinstance(uid, bool) or uid < 0 or uid > 2**32 - 1:
            raise BootHealthServiceError(
                "provisioned boot-health caller UID is outside Greia bounds"
            )
        if uid not in allowed:
            allowed.append(uid)
    raw_caller = caller if caller is not None else os.environ.get(
        BOOT_HEALTH_CALLER_ENV, ""
    )
    name = str(raw_caller).strip()
    if name:
        import pwd

        try:
            caller_uid = pwd.getpwnam(name).pw_uid
        except KeyError as exc:
            raise BootHealthServiceError(
                f"provisioned boot-health caller {name!r} is not resolvable"
            ) from exc
        if caller_uid not in allowed:
            allowed.append(caller_uid)
    return tuple(allowed)


def resolve_boot_journal_dir() -> Path:
    """Resolve the first-install boot journal directory (env or system bind)."""
    override = os.environ.get(BOOT_JOURNAL_DIR_ENV, "").strip()
    return Path(override) if override else Path(BOOT_JOURNAL_DIR_DEFAULT)


def resolve_update_state_dir() -> Path:
    """Resolve the update state root (env or system bind)."""
    override = os.environ.get(UPDATE_STATE_DIR_ENV, "").strip()
    return Path(override) if override else Path(UPDATE_STATE_DIR_DEFAULT)


def resolve_history_dir() -> Path:
    """Resolve the boot-history ring directory (env or system bind)."""
    override = os.environ.get(BOOT_HISTORY_DIR_ENV, "").strip()
    return Path(override) if override else Path(BOOT_HISTORY_DIR_DEFAULT)


def resolve_receipt_path() -> Path:
    """Resolve the booted-slot finalization receipt path (env or bind)."""
    override = os.environ.get(FINALIZATION_RECEIPT_ENV, "").strip()
    return Path(override) if override else Path(FINALIZATION_RECEIPT_DEFAULT)


def _load_non_terminal_journal(
    journal_dir: Path,
) -> BootTransactionJournal | None:
    """Return the journal at ``journal_dir``, or None when absent/terminal.

    Read-only: loading never writes. A corrupt journal raises
    fail-closed; a missing journal file is the normal plain-boot case.
    """
    from .boot_transaction import JOURNAL_FILE_NAME

    candidate = Path(journal_dir) / JOURNAL_FILE_NAME
    if candidate.is_symlink():
        raise BootHealthServiceError("boot journal must not be a symlink")
    if not candidate.is_file():
        return None
    try:
        journal = BootTransactionJournal.load(Path(journal_dir))
    except BootJournalError as exc:
        raise BootHealthServiceError(
            f"boot journal is not authoritative: {exc}"
        ) from exc
    except OSError as exc:
        raise BootHealthServiceError(f"boot journal is unreadable: {exc}") from exc
    if journal.is_terminal:
        return None
    return journal


class ReceiptBackedArtifactResolver:
    """Production first-install artifact source: layout record + receipt.

    Binds the booted slot's finalizer receipt (digests, slot, release,
    layout) to the trusted layout record's root identity through the
    shared :meth:`BootArtifactSet.from_finalization` constructor. The
    receipt must agree with the pending journal on slot, release,
    sequence and layout, otherwise confirmation fails closed. Only
    first-install journals resolve here: update journals confirm through
    the ``system_updates`` backend, which needs no artifact sets.
    """

    def __init__(
        self,
        *,
        layout_record_path: Path | None = None,
        receipt_path: Path | None = None,
    ) -> None:
        self._layout_record_path = (
            Path(layout_record_path)
            if layout_record_path is not None
            else installed_layout_record_path()
        )
        self._receipt_path = (
            Path(receipt_path)
            if receipt_path is not None
            else resolve_receipt_path()
        )

    def resolve(
        self, journal: BootTransactionJournal
    ) -> tuple[BootArtifactSet, BootArtifactSet]:
        from .boot_transaction import BootArtifactError
        from .system_updates import UpdateLayoutError

        if not journal.first_install:
            raise BootHealthServiceError(
                "receipt artifact resolution serves first-install journals only"
            )
        try:
            record = load_installed_layout_record(self._layout_record_path)
        except UpdateLayoutError as exc:
            raise BootHealthServiceError(
                f"layout authority is not authoritative: {exc}"
            ) from exc
        if record is None or record.system_b is None:
            raise BootHealthServiceError(
                "first-install confirmation requires an A/B layout authority"
            )
        receipt = self._read_receipt()
        for field_name, receipt_value, journal_value in (
            ("slot", receipt.slot, journal.candidate_slot),
            ("release_id", receipt.release_id, journal.release_id),
            ("release_sequence", receipt.release_sequence, journal.release_sequence),
            ("layout_id", receipt.layout_id, journal.layout_id),
        ):
            if receipt_value != journal_value:
                raise BootHealthServiceError(
                    "finalization receipt is not the pending "
                    f"first-install {field_name}"
                )
        try:
            candidate = BootArtifactSet.from_finalization(
                receipt=receipt, record=record
            )
        except BootArtifactError as exc:
            raise BootHealthServiceError(
                f"finalization receipt does not bind the layout: {exc}"
            ) from exc
        return candidate, candidate

    def _read_receipt(self) -> "_ReceiptView":
        import json as _json

        path = self._receipt_path
        if path.is_symlink():
            raise BootHealthServiceError("finalization receipt must not be a symlink")
        try:
            raw_bytes = path.read_bytes()
        except OSError as exc:
            raise BootHealthServiceError(
                f"finalization receipt is unreadable: {exc}"
            ) from exc
        if len(raw_bytes) > 32 * 1024:
            raise BootHealthServiceError("finalization receipt exceeds Greia bounds")
        try:
            raw = _json.loads(raw_bytes.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as exc:
            raise BootHealthServiceError(
                f"finalization receipt is not valid JSON: {exc}"
            ) from exc
        if not isinstance(raw, dict):
            raise BootHealthServiceError("finalization receipt must be a JSON object")
        digests = raw.get("artifact_digests")
        if not isinstance(digests, dict):
            raise BootHealthServiceError(
                "finalization receipt carries no artifact digests"
            )
        for key in ("generic_kernel_sha256", "host_initramfs_sha256"):
            value = digests.get(key)
            if (
                not isinstance(value, str)
                or len(value) != 64
                or any(char not in "0123456789abcdef" for char in value)
            ):
                raise BootHealthServiceError(
                    f"finalization receipt digest {key} is not authoritative"
                )
        for key in ("release_id", "release_sequence", "slot", "layout_id"):
            if raw.get(key) is None:
                raise BootHealthServiceError(
                    f"finalization receipt is missing authoritative field {key}"
                )
        sequence = raw["release_sequence"]
        if (
            isinstance(sequence, bool)
            or not isinstance(sequence, int)
            or not 0 <= sequence <= 2_147_483_647
        ):
            raise BootHealthServiceError(
                "finalization receipt release_sequence is outside Greia bounds"
            )
        return _ReceiptView(
            slot=str(raw["slot"]),
            layout_id=str(raw["layout_id"]),
            release_id=str(raw["release_id"]),
            release_sequence=int(sequence),
            generic_kernel_sha256=str(digests["generic_kernel_sha256"]),
            host_initramfs_sha256=str(digests["host_initramfs_sha256"]),
        )


@dataclass(frozen=True, slots=True)
class _ReceiptView:
    """Attribute-shaped receipt view for ``BootArtifactSet.from_finalization``."""

    slot: str
    layout_id: str
    release_id: str
    release_sequence: int
    generic_kernel_sha256: str
    host_initramfs_sha256: str


@dataclass
class BootHealthService:
    """Privileged health-commit owner behind the socket-activated endpoint.

    Resolves the pending journal internally (first-install and update),
    consumes the one-use capability before any mutation, then commits
    through the reused ``system_updates`` path (update) or the shared
    coordinator/backend primitives (first install), finishing with one
    bounded boot-history terminal record.
    """

    boot_journal_dir: Path
    update_state_dir: Path
    history_dir: Path
    update_authority: object
    capability_verifier: BootHealthCapabilityVerifier
    artifact_resolver: BootHealthArtifactResolver | None = None
    boot_backend_factory: Callable[[], object] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "boot_journal_dir", Path(self.boot_journal_dir))
        object.__setattr__(self, "update_state_dir", Path(self.update_state_dir))
        object.__setattr__(self, "history_dir", Path(self.history_dir))
        if not callable(
            getattr(self.update_authority, "confirm_boot_health", None)
        ):
            raise BootHealthServiceError(
                "boot-health service requires the system_updates confirm path"
            )
        if not callable(
            getattr(self.capability_verifier, "verify_and_consume", None)
        ):
            raise BootHealthServiceError(
                "boot-health service requires a one-use capability verifier"
            )

    @property
    def update_journal_dir(self) -> Path:
        """The update pending journal resolved internally (never a selector)."""
        from .system_updates import UPDATE_JOURNAL_DIR_NAME

        return self.update_state_dir / "system-updates" / UPDATE_JOURNAL_DIR_NAME

    def confirm(self, *, token: str) -> dict[str, object]:
        """Consume the capability, then commit the single pending journal.

        Read-only journal selection happens first (both-pending refuses
        without guessing); the capability is consumed before any journal,
        GRUB, sequence, layout or history mutation.
        """
        update_journal = _load_non_terminal_journal(self.update_journal_dir)
        install_journal = _load_non_terminal_journal(self.boot_journal_dir)
        pending: list[tuple[str, Path, BootTransactionJournal]] = []
        if update_journal is not None:
            pending.append(("update", self.update_journal_dir, update_journal))
        if install_journal is not None:
            pending.append(("first-install", self.boot_journal_dir, install_journal))
        if len(pending) > 1:
            raise BootHealthServiceError(
                "ambiguous boot authority: update and first-install journals "
                "are both pending; refusing to guess"
            )
        if not pending:
            raise BootHealthServiceError("no pending boot-health transaction")
        kind, journal_dir, journal = pending[0]
        try:
            consumed = self.capability_verifier.verify_and_consume(token=token)
        except BootHealthServiceError:
            raise
        except Exception as exc:
            raise BootHealthServiceError(
                f"boot-health capability refused: {exc}"
            ) from exc
        _ = consumed
        if kind == "update":
            detail = self._confirm_update(journal)
        else:
            detail = self._confirm_first_install(journal_dir, journal)
        return detail

    def _confirm_update(
        self, journal: BootTransactionJournal
    ) -> dict[str, object]:
        """Commit the update journal through the reused system_updates path."""
        try:
            detail = dict(self.update_authority.confirm_boot_health())  # type: ignore[union-attr]
        except (SystemUpdateError, UpdateBackendUnavailable) as exc:
            raise BootHealthServiceError(
                f"update health commit refused: {exc}"
            ) from exc
        self._record_history_committed(journal, transaction_type="update")
        detail["journal"] = "update"
        # Carry the committed identity for unprivileged consumers (the
        # launcher maps the CONFIRMED detail to its outcome without ever
        # reading journals itself): the delegated backend detail owns only
        # confirmed/state/booted_slot.
        detail.setdefault("accepted_slot", journal.candidate_slot)
        detail.setdefault("release_id", journal.release_id)
        detail.setdefault("release_sequence", journal.release_sequence)
        detail.setdefault("first_install", False)
        return detail

    def _confirm_first_install(
        self, journal_dir: Path, journal: BootTransactionJournal
    ) -> dict[str, object]:
        """Commit the first-install journal through shared coordinator primitives."""
        resolver = self.artifact_resolver
        if resolver is None:
            raise BootHealthServiceError(
                "first-install confirmation requires an artifact resolver"
            )
        candidate, accepted = resolver.resolve(journal)
        # Read-only authority check first: a drifted layout record refuses
        # before the journal, GRUB or sequence state is touched.
        self._converge_first_install_layout(journal)
        try:
            backend = self._attach_boot_backend()
        except (BootTransactionError, OSError, ValueError) as exc:
            raise BootHealthServiceError(
                f"boot backend is unavailable: {exc}"
            ) from exc
        try:
            coordinator = BootTransactionCoordinator.resume(
                journal_dir=journal_dir,
                backend=backend,  # type: ignore[arg-type]
                candidate_artifacts=candidate,
                accepted_artifacts=accepted,
            )
            coordinator.observe_boot()
            committed = coordinator.commit()
        except BootTransactionError as exc:
            raise BootHealthServiceError(
                f"first-install health commit refused: {exc}"
            ) from exc
        try:
            write_accepted_sequence(self.update_state_dir, journal.release_sequence)
        except (SystemUpdateError, OSError, ValueError) as exc:
            raise BootHealthServiceError(
                f"accepted-sequence update refused: {exc}"
            ) from exc
        self._record_history_committed(journal, transaction_type="first-install")
        return {
            "journal": "first-install",
            "first_install": True,
            "confirmed": True,
            "state": BootTransactionState.ACCEPTED.value,
            "accepted_slot": committed.default_slot,
            "release_id": journal.release_id,
            "release_sequence": journal.release_sequence,
        }

    def _attach_boot_backend(self) -> object:
        if self.boot_backend_factory is not None:
            return self.boot_backend_factory()
        return GrubEnvBackend.attach(resolve_grubenv_dir())

    def _converge_first_install_layout(
        self, journal: BootTransactionJournal
    ) -> None:
        """Verify the layout authority already accepts the installed release.

        The installer authors the A/B record accepting slot A; the service
        owns this step by refusing authority drift fail-closed rather than
        authoring layout itself. The shared
        ``advance_layout_authority_for_acceptance`` serves update commits
        (candidate distinct from accepted); a first-install journal always
        carries candidate == accepted == A, so advancement is a verified
        convergence, never a rewrite.
        """
        from .system_updates import UpdateLayoutError

        try:
            record = load_installed_layout_record(
                self.update_authority_layout_path()
            )
        except UpdateLayoutError as exc:
            raise BootHealthServiceError(
                f"layout authority is not authoritative: {exc}"
            ) from exc
        if record is None or record.system_b is None:
            raise BootHealthServiceError(
                "first-install confirmation requires an A/B layout authority"
            )
        if (
            record.accepted_slot != journal.candidate_slot
            or record.accepted_release_id != journal.release_id
            or record.accepted_release_sequence != journal.release_sequence
            or record.boot_control.active_slot != journal.candidate_slot
        ):
            raise BootHealthServiceError(
                "layout authority moved under the first-install transaction; "
                "refusing to confirm"
            )

    def update_authority_layout_path(self) -> Path | None:
        """Layout record path owned by the delegated update authority."""
        path = getattr(self.update_authority, "backend", None)
        path = getattr(path, "layout_record_path", None)
        if path is not None:
            return Path(path)
        return installed_layout_record_path()

    def _record_history_committed(
        self, journal: BootTransactionJournal, *, transaction_type: str
    ) -> None:
        """Append the single bounded boot-history terminal record."""
        try:
            history = BootHistory.load(self.history_dir)
        except BootTransactionError:
            history = BootHistory.empty(self.history_dir)
        except OSError as exc:
            raise BootHealthServiceError(
                f"boot-history is not accessible: {exc}"
            ) from exc
        try:
            backend_default = self._committed_default(journal)
            current = history.current
            if current is None or current.transaction_id != journal.transaction_id:
                history.begin_boot(
                    boot_id=str(uuid.uuid4()),
                    started_at_unix=int(time.time()),
                    slot=journal.candidate_slot,
                    release_id=journal.release_id,
                    release_sequence=journal.release_sequence,
                    transaction_id=journal.transaction_id,
                    transaction_type=transaction_type,
                    backend_default=backend_default,
                )
            history.record_milestone(
                "committed",
                health_result="confirmed",
                backend_default=backend_default,
                backend_one_shot="",
                terminal_state=BootTransactionState.ACCEPTED.value,
            )
        except BootTransactionError as exc:
            raise BootHealthServiceError(
                f"boot-history terminal record refused: {exc}"
            ) from exc

    def _committed_default(self, journal: BootTransactionJournal) -> str:
        return journal.candidate_slot


class BootHealthEndpoint:
    """Answer one framed request for the boot-health service.

    Pure over bytes with injected peer/boot-state/service: peer UID must
    be authorized, boot must be interactive-ready, params must carry only
    the one-use capability token, and the single semantic op resolves the
    pending journal internally.
    """

    def __init__(
        self,
        service: BootHealthService,
        *,
        allowed_uids: tuple[int, ...] = BOOT_HEALTH_ALLOWED_UIDS,
    ) -> None:
        self.service = service
        self.allowed_uids = allowed_uids

    def handle_request(
        self, raw: bytes, *, peer: PeerCredential, boot_state: str
    ) -> bytes:
        try:
            authorize_peer(peer, self.allowed_uids)
        except PrivilegedChannelError as exc:
            raise BootHealthServiceError(str(exc)) from exc
        try:
            require_interactive_boot(boot_state)
        except PrivilegedChannelError as exc:
            raise BootHealthServiceError(str(exc)) from exc
        try:
            op, params = decode_request(raw)
        except PrivilegedChannelError as exc:
            raise BootHealthServiceError(str(exc)) from exc
        if op not in BOOT_HEALTH_OPS:
            raise BootHealthServiceError(f"unknown boot-health op: {op}")
        reject_raw_authority(params)
        token = _require_capability_token(params)
        transaction_id = new_transaction_id()
        try:
            detail = self.service.confirm(token=token)
        except (SystemUpdateError, BootTransactionError, BootJournalError) as exc:
            raise BootHealthServiceError(str(exc)) from exc
        payload: dict[str, object] = {"status": "CONFIRMED", "detail": detail}
        received = format_log_record(transaction_id, op, str(payload["status"]))
        _ = received
        return encode_response(transaction_id, op, payload)


def build_confirm_request(token: str) -> bytes:
    """Build one selector-free confirm request carrying only the capability."""
    if (
        not isinstance(token, str)
        or not token
        or len(token.encode("utf-8")) > MAX_CAPABILITY_CHARS
    ):
        raise BootHealthServiceError("capability token is outside Greia bounds")
    try:
        return encode_request("CONFIRM_BOOT_HEALTH", {CAPABILITY_PARAM: token})
    except PrivilegedChannelError as exc:
        raise BootHealthServiceError(str(exc)) from exc


def read_confirm_response(raw: bytes) -> tuple[str, str, dict[str, object]]:
    """Decode one confirm response frame."""
    from .privileged_channel import decode_response

    try:
        return decode_response(raw)
    except PrivilegedChannelError as exc:
        raise BootHealthServiceError(str(exc)) from exc


def _refused_frame(reason: object) -> bytes:
    return encode_response(
        new_transaction_id(), "ERROR", {"status": "REFUSED", "reason": str(reason)[:256]}
    )


def handle_boot_health_connection(
    connection: socket.socket,
    *,
    endpoint: BootHealthEndpoint,
    peer: object,
    boot_state: str = "interactive_ready",
) -> None:
    """Answer exactly one framed health request on an accepted connection.

    The kernel-attested peer is authorized before any request byte is
    read: forged (non-attested) or unauthorized peers are refused without
    touching the socket's byte stream. Any later refusal — boot, schema,
    capability, journal — is answered as a bounded REFUSED frame.
    """
    if not isinstance(peer, PeerCredential):
        try:
            connection.sendall(
                _refused_frame("peer credential must be attested, never asserted")
            )
        finally:
            try:
                connection.close()
            except OSError:
                pass
        return
    try:
        authorize_peer(peer, endpoint.allowed_uids)
    except PrivilegedChannelError as exc:
        try:
            connection.sendall(_refused_frame(exc))
        finally:
            try:
                connection.close()
            except OSError:
                pass
        return
    try:
        connection.settimeout(10.0)
        chunks: list[bytes] = []
        received = 0
        while True:
            chunk = connection.recv(4096)
            if not chunk:
                break
            received += len(chunk)
            if received > MAX_MESSAGE_BYTES:
                raise BootHealthServiceError("request exceeds Greia bound")
            chunks.append(chunk)
            if chunk.endswith(b"\n"):
                break
        raw = b"".join(chunks)
        response = endpoint.handle_request(raw, peer=peer, boot_state=boot_state)
    except (
        BootHealthServiceError,
        SystemUpdateError,
        UpdateBackendUnavailable,
        PrivilegedChannelError,
        BootTransactionError,
        BootJournalError,
    ) as exc:
        response = _refused_frame(exc)
    try:
        connection.sendall(response)
    finally:
        try:
            connection.close()
        except OSError:
            pass


def load_production_capability_verifier() -> BootHealthCapabilityVerifier:
    """Load the one-use verifier shipped by POSTR1-P4-HEALTH-PROOF2.

    Returns the narrow production verifier from
    :mod:`greia_platform.boot_capability`: on every call it resolves the
    single pending transaction, the current kernel boot ID and the
    trusted launcher bootstrap path from Greia-owned state and consumes
    the capability through the root authority exactly once. No
    launcher-writable vault is constructed here as a substitute; a
    missing module still fails closed.
    """
    try:
        from .boot_capability import build_production_verifier  # type: ignore[import-not-found]
    except ImportError as exc:
        raise BootHealthServiceError(
            "no boot-health capability verifier is wired; refusing "
            "(owner: POSTR1-P4-CAPABILITY-LIFECYCLE)"
        ) from exc
    verifier = build_production_verifier()
    if not callable(getattr(verifier, "verify_and_consume", None)):
        raise BootHealthServiceError(
            "production capability verifier owns no verify_and_consume seam"
        )
    return verifier  # type: ignore[no-any-return]


def build_live_boot_health_service(
    *,
    capability_verifier: BootHealthCapabilityVerifier | None = None,
    update_authority: object | None = None,
    artifact_resolver: BootHealthArtifactResolver | None = None,
    boot_journal_dir: Path | None = None,
    update_state_dir: Path | None = None,
    history_dir: Path | None = None,
) -> tuple[BootHealthService, BootHealthEndpoint]:
    """Compose the production service and endpoint from Greia-owned state.

    Trust, layout, journals and boot facts resolve from Greia-owned state
    on every composition; the update mutation path reuses
    ``build_live_update_service``. The capability verifier must be
    injected (tests) or provided by the CAPABILITY-LIFECYCLE module;
    without one the composition fails closed.
    """
    from .system_updates import build_live_update_service

    boot_dir = Path(boot_journal_dir) if boot_journal_dir is not None else resolve_boot_journal_dir()
    state_dir = Path(update_state_dir) if update_state_dir is not None else resolve_update_state_dir()
    ring_dir = Path(history_dir) if history_dir is not None else resolve_history_dir()
    verifier = (
        capability_verifier
        if capability_verifier is not None
        else load_production_capability_verifier()
    )
    authority = (
        update_authority
        if update_authority is not None
        else build_live_update_service(state_dir=state_dir)
    )
    resolver = (
        artifact_resolver
        if artifact_resolver is not None
        else ReceiptBackedArtifactResolver()
    )
    service = BootHealthService(
        boot_journal_dir=boot_dir,
        update_state_dir=state_dir,
        history_dir=ring_dir,
        update_authority=authority,
        capability_verifier=verifier,
        artifact_resolver=resolver,
    )
    return service, BootHealthEndpoint(service, allowed_uids=resolve_allowed_uids())


def serve_boot_health_forever(
    listener: socket.socket,
    *,
    endpoint: BootHealthEndpoint,
) -> None:
    """Accept connections until the socket unit stops (systemd owns the fd).

    Every peer is attested from ``SO_PEERCRED`` before serving;
    connections whose kernel credential cannot be attested are closed
    unserved, before any request byte is read.
    """
    from .system_updates import attest_peer_from_connection

    while True:
        connection, _ = listener.accept()
        try:
            peer = attest_peer_from_connection(connection)
        except PrivilegedChannelError:
            try:
                connection.close()
            except OSError:
                pass
            continue
        handle_boot_health_connection(
            connection, endpoint=endpoint, peer=peer,
            boot_state="interactive_ready",
        )


def main(argv: list[str] | None = None) -> int:
    """Socket-activated entry for ``greia-boot-health.service``.

    With systemd socket activation (``LISTEN_FDS``) the passed file
    descriptor is the listening socket; without one the service exits
    fail-closed instead of opening any socket itself. Only
    ``AF_UNIX`` is ever served (see the unit's ``RestrictAddressFamilies``).
    """
    _ = list(argv or [])
    listen_fds = int(os.environ.get("LISTEN_FDS", "0"))
    if listen_fds < 1:
        raise SystemExit(
            "greia-boot-health: no socket-activated file descriptor; "
            "refusing to listen (see greia-boot-health.socket)"
        )
    _service, endpoint = build_live_boot_health_service()
    listener = socket.fromfd(3, socket.AF_UNIX, socket.SOCK_STREAM)
    serve_boot_health_forever(listener, endpoint=endpoint)
    return 0  # pragma: no cover - serve_forever never returns


if __name__ == "__main__":  # pragma: no cover - service entry
    raise SystemExit(main())
