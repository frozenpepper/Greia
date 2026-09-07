"""Update semantic privileged protocol (L7-PROTOCOLS, R0/R1).

The ``greia-system-update`` socket-activated service exposes semantic
operations only::

    STATUS, VERIFY_CURRENT_CANDIDATE, STAGE_CURRENT_CANDIDATE,
    ARM_CURRENT_CANDIDATE, CONFIRM_BOOT_HEALTH, RECONCILE

Requests carry no selectors: the service resolves the inbox candidate,
layout, inactive slot, support set and boot backend internally through
the narrow authorities below (built on ``system_updates``,
``slot_writer``, ``persistent_layout`` and ``boot_transaction``). The
current single-root backend stays unavailable: staging/arming on a
single-root layout fails closed through
``UnavailableSystemUpdateBackend`` semantics.

R0/R1 bound: protocol definitions only. Staging/arming/commit authority
reuses the staged fakes and file-backed seams; no destructive backend is
wired here and nothing is destructively enabled. The socket unit stays
inactive during ordinary pre-intro boot.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol

from .privileged_channel import (
    PeerCredential,
    PrivilegedChannelError,
    authorize_peer,
    decode_request,
    decode_response,
    encode_request,
    encode_response,
    format_log_record,
    new_transaction_id,
    reject_raw_authority,
    require_interactive_boot,
)
from .system_updates import UpdateBackendUnavailable


class UpdatePrivilegedError(RuntimeError):
    """Update semantic operation failed fail-closed."""


#: Semantic operations of the system-update service. No raw selectors exist:
#: every op resolves the current inbox candidate internally.
UPDATE_PRIVILEGED_OPS = (
    "STATUS",
    "VERIFY_CURRENT_CANDIDATE",
    "STAGE_CURRENT_CANDIDATE",
    "ARM_CURRENT_CANDIDATE",
    "CONFIRM_BOOT_HEALTH",
    "RECONCILE",
)

#: Peer UIDs authorized for the update service. Root owns the privileged
#: unit; the numeric greiapanel UID is injected by the service composition
#: (tests inject small synthetic UIDs instead of hardcoding production IDs).
UPDATE_PRIVILEGED_ALLOWED_UIDS = (0,)


@dataclass(frozen=True, slots=True)
class CurrentCandidateSummary:
    """Bounded public facts for the internally resolved inbox candidate."""

    present: bool
    release_id: str = ""
    release_sequence: int = 0
    bundle_sha256: str = ""
    signature_verified: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.present, bool):
            raise UpdatePrivilegedError("candidate presence must be a boolean")
        if len(self.release_id) > 96:
            raise UpdatePrivilegedError("candidate release_id exceeds Greia bound")
        if (
            isinstance(self.release_sequence, bool)
            or not isinstance(self.release_sequence, int)
            or self.release_sequence < 0
        ):
            raise UpdatePrivilegedError("candidate release_sequence is outside Greia bounds")
        if self.bundle_sha256 and (
            len(self.bundle_sha256) != 64
            or any(c not in "0123456789abcdef" for c in self.bundle_sha256)
        ):
            raise UpdatePrivilegedError("candidate bundle digest is outside Greia bounds")


class UpdatePrivilegedAuthority(Protocol):
    """Narrow seam the update endpoint resolves internally per operation."""

    def candidate_summary(self) -> CurrentCandidateSummary: ...

    def layout_summary(self) -> Mapping[str, object]: ...

    def verify_current_candidate(self) -> CurrentCandidateSummary: ...

    def stage_current_candidate(self) -> Mapping[str, object]: ...

    def arm_current_candidate(self) -> Mapping[str, object]: ...

    def confirm_boot_health(self) -> Mapping[str, object]: ...

    def reconcile(self) -> Mapping[str, object]: ...


def _require_empty_params(op: str, params: Mapping[str, object]) -> None:
    if not isinstance(params, dict) or params:
        raise UpdatePrivilegedError(
            f"{op} takes no selectors; the service resolves the current candidate internally"
        )


class UpdatePrivilegedEndpoint:
    """Answer one framed request for the system-update service.

    Pure over bytes with injected peer/boot-state/authority: peer UID must
    be authorized, boot must be interactive-ready, params must be empty
    (semantic-only), and the single-root layout stays unavailable for
    staging/arming.
    """

    def __init__(
        self,
        authority: UpdatePrivilegedAuthority,
        *,
        allowed_uids: tuple[int, ...] = UPDATE_PRIVILEGED_ALLOWED_UIDS,
    ) -> None:
        self.authority = authority
        self.allowed_uids = allowed_uids

    def handle_request(
        self, raw: bytes, *, peer: PeerCredential, boot_state: str
    ) -> bytes:
        try:
            authorize_peer(peer, self.allowed_uids)
        except PrivilegedChannelError as exc:
            raise UpdatePrivilegedError(str(exc)) from exc
        try:
            require_interactive_boot(boot_state)
        except PrivilegedChannelError as exc:
            raise UpdatePrivilegedError(str(exc)) from exc
        try:
            op, params = decode_request(raw)
        except PrivilegedChannelError as exc:
            raise UpdatePrivilegedError(str(exc)) from exc
        if op not in UPDATE_PRIVILEGED_OPS:
            raise UpdatePrivilegedError(f"unknown system-update op: {op}")
        reject_raw_authority(params)
        _require_empty_params(op, params)
        transaction_id = new_transaction_id()
        try:
            if op == "STATUS":
                payload: dict[str, object] = {
                    "status": "OK",
                    "candidate": _summary_dict(self.authority.candidate_summary()),
                    "layout": dict(self.authority.layout_summary()),
                }
            elif op == "VERIFY_CURRENT_CANDIDATE":
                payload = {
                    "status": "VERIFIED",
                    "candidate": _summary_dict(
                        self.authority.verify_current_candidate()
                    ),
                }
            elif op == "STAGE_CURRENT_CANDIDATE":
                payload = {
                    "status": "STAGED",
                    "detail": dict(self.authority.stage_current_candidate()),
                }
            elif op == "ARM_CURRENT_CANDIDATE":
                payload = {
                    "status": "ARMED",
                    "detail": dict(self.authority.arm_current_candidate()),
                }
            elif op == "CONFIRM_BOOT_HEALTH":
                payload = {
                    "status": "CONFIRMED",
                    "detail": dict(self.authority.confirm_boot_health()),
                }
            else:
                payload = {
                    "status": "RECONCILED",
                    "detail": dict(self.authority.reconcile()),
                }
        except UpdateBackendUnavailable as exc:
            raise UpdatePrivilegedError(str(exc)) from exc
        received = format_log_record(transaction_id, op, str(payload["status"]))
        _ = received
        return encode_response(transaction_id, op, payload)


def _summary_dict(summary: CurrentCandidateSummary) -> dict[str, object]:
    return {
        "present": summary.present,
        "release_id": summary.release_id,
        "release_sequence": summary.release_sequence,
        "bundle_sha256": summary.bundle_sha256,
        "signature_verified": summary.signature_verified,
    }


def build_request(op: str) -> bytes:
    """Build one selector-free semantic request (client side / tests)."""
    if op not in UPDATE_PRIVILEGED_OPS:
        raise UpdatePrivilegedError(f"unknown system-update op: {op}")
    try:
        return encode_request(op, {})
    except PrivilegedChannelError as exc:
        raise UpdatePrivilegedError(str(exc)) from exc


def read_response(raw: bytes) -> tuple[str, str, dict[str, object]]:
    """Decode one semantic response frame."""
    try:
        return decode_response(raw)
    except PrivilegedChannelError as exc:
        raise UpdatePrivilegedError(str(exc)) from exc


def main(argv: list[str] | None = None) -> int:
    """Socket-service entry point (R0/R1: defined, never destructively enabled).

    The ``greia-system-update`` socket/service units reference this entry.
    It refuses to perform destructive work: with no socket-activated file
    descriptor and no destructive backend wired, it exits fail-closed.
    """
    _ = list(argv or [])
    raise SystemExit(
        "greia-system-update: destructive backend not wired at R0/R1; "
        "service defined but never enabled (see greia-system-update.service)"
    )


if __name__ == "__main__":
    raise SystemExit(main())
