"""Unprivileged installer UI client for the root install-transaction service (8A.5).

Step 8A.5 splits the installer in two: the graphical UI runs unprivileged
(``greia-installer-ui.service``) and talks to the root
``greia-install-transaction.service`` over a semantic local socket. This
module is the UI side of that split.

What the UI may do here:

- read safe inventory/display facts (identity digests, eligibility, display
  summaries) for the target page;
- ``PREPARE_PLAN`` with an identity digest + compatible profile id + bounded
  settings snapshot, receiving a single-use ``transaction_nonce``, a
  canonical human-reviewable plan and its ``plan_digest``;
- hold a :class:`PreparedConfirmation` for the graphical confirm page and
  discard it fail-closed whenever a fresh read-only inventory shows the
  target disappeared, turned ineligible, changed display facts, or the
  parent changed settings;
- ``EXECUTE`` with only ``nonce`` + ``digest``.

What the UI can never do through this module (proven by negative tests):

- open or write raw disks (no process spawning, no device nodes, no engine
  import — this module only frames semantic requests over an injected
  byte transport);
- smuggle arbitrary paths/commands/URLs/mount points/partition numbers/
  bootloader args (every request is built with
  :func:`greia_platform.privileged_channel.encode_request`, which rejects
  raw authority before framing);
- execute a stale confirmation after an inventory refresh (both
  :meth:`PreparedConfirmation.still_valid` and the root service's own
  inventory-token re-probe refuse it).

The production transport is one framed JSON request per ``AF_UNIX``
connection; tests inject a fake transport bound to
:meth:`greia_installer.transaction_service.InstallTransactionService.handle_request`.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import socket
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping

from greia_platform.privileged_channel import (
    MAX_MESSAGE_BYTES,
    PrivilegedChannelError,
    decode_response,
    encode_request,
    require_transaction_id,
)

from .install_transaction import canonical_plan_bytes


class TransactionClientError(RuntimeError):
    """UI-side transaction step failed fail-closed (never destructive)."""


#: Operation name the service uses when it refuses a request deliberately.
ERROR_OP = "ERROR"


def _refusal_reason(payload: Mapping[str, object]) -> str:
    """Render the service's own refusal reason for the installer error page.

    The privileged service answers a refused request with ``op="ERROR"`` and a
    bounded ``reason`` string. That reason is the only thing that tells a child
    (or an operator) *why* the install was refused, so it must survive the trip
    to the UI instead of being flattened into a generic op-mismatch message.
    """

    reason = payload.get("reason")
    if isinstance(reason, str) and reason.strip():
        return reason.strip()[:256]
    status = payload.get("status")
    if isinstance(status, str) and status.strip():
        return f"install transaction service refused the request ({status.strip()})"
    return "install transaction service refused the request"


#: Default production socket served by greia-install-transaction.socket.
DEFAULT_TRANSACTION_SOCKET_PATH = Path("/run/greia-os/install-transaction.sock")

#: Bounded connection/read budget for one short UI request (inventory-safe).
_SOCKET_TIMEOUT_SECONDS = 10.0

#: Bounded wait for one EXECUTE round-trip. The root service runs the
#: authorized install synchronously before answering INSTALLED, so the UI
#: must hold the connection open for a full slow-machine install instead
#: of timing out mid-transaction (the install itself is unaffected by the
#: UI wait; the timeout only bounds the UI's own patience).
_EXECUTE_TIMEOUT_SECONDS = 1800.0

#: Public alias for the UI's EXECUTE patience (same value, stable name).
EXECUTE_TIMEOUT_SECONDS = _EXECUTE_TIMEOUT_SECONDS


def socket_transport(
    socket_path: Path = DEFAULT_TRANSACTION_SOCKET_PATH,
    *,
    timeout: float = _SOCKET_TIMEOUT_SECONDS,
) -> Callable[[bytes], bytes]:
    """Return a one-request-per-connection ``AF_UNIX`` transport.

    The path itself is UI configuration, never request authority: it selects
    the platform-owned socket, while target selection still travels only as
    an identity digest inside the framed semantic request.
    """

    def send_receive(raw: bytes) -> bytes:
        if len(raw) > MAX_MESSAGE_BYTES:
            raise TransactionClientError("transaction request exceeds Greia bound")
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                client.settimeout(timeout)
                client.connect(str(socket_path))
                client.sendall(raw)
                try:
                    client.shutdown(socket.SHUT_WR)
                except OSError:
                    pass
                chunks: list[bytes] = []
                received = 0
                while True:
                    chunk = client.recv(4096)
                    if not chunk:
                        break
                    received += len(chunk)
                    if received > MAX_MESSAGE_BYTES:
                        raise TransactionClientError(
                            "transaction response exceeds Greia bound"
                        )
                    chunks.append(chunk)
        except (OSError, TimeoutError) as exc:
            raise TransactionClientError(
                "install transaction service is unreachable"
            ) from exc
        return b"".join(chunks)

    return send_receive


@dataclass(frozen=True, slots=True)
class PreparedPlan:
    """A prepared plan as observed by the unprivileged UI."""

    transaction_nonce: str
    plan: dict[str, object]
    plan_digest: str


@dataclass(frozen=True, slots=True)
class ExecuteReceipt:
    """The root service's authorization receipt echoed back to the UI."""

    transaction_nonce: str
    plan_digest: str
    target_identity: str


def _require_mapping(value: object, *, field_name: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TransactionClientError(f"transaction {field_name} is not an object")
    return dict(value)


class InstallTransactionClient:
    """Semantic UI client: frames requests, verifies responses, holds no disk."""

    def __init__(
        self,
        transport: Callable[[bytes], bytes] | None = None,
        *,
        execute_transport: Callable[[bytes], bytes] | None = None,
    ) -> None:
        self._transport = transport or socket_transport()
        # EXECUTE waits out the synchronous authorized install; short
        # prepares must never inherit that patience, and the long wait must
        # never apply to anything but EXECUTE.
        self._execute_transport = execute_transport or self._transport

    def _round_trip(
        self,
        op: str,
        params: Mapping[str, object],
        transport: Callable[[bytes], bytes] | None = None,
    ) -> dict[str, object]:
        try:
            raw = encode_request(op, params)
        except PrivilegedChannelError as exc:
            raise TransactionClientError(str(exc)) from exc
        try:
            response = (transport or self._transport)(raw)
        except TransactionClientError:
            raise
        except Exception as exc:
            # Direct/in-process transports surface the service refusal
            # itself; preserve its fail-closed reason for the error page
            # instead of laundering every refusal into one generic message.
            raise TransactionClientError(
                str(exc) or "install transaction transport failed"
            ) from exc
        if not response or len(response) > MAX_MESSAGE_BYTES:
            raise TransactionClientError("transaction response is outside Greia bounds")
        try:
            transaction_id, returned_op, payload = decode_response(response)
        except PrivilegedChannelError as exc:
            raise TransactionClientError(str(exc)) from exc
        require_transaction_id(transaction_id)
        if returned_op == ERROR_OP:
            # The service refused deliberately and said why. Raising the op
            # mismatch here would discard that reason and show the child a
            # meaningless "answered the wrong op" instead of, for example,
            # "selected disk is unknown; installation stopped".
            raise TransactionClientError(_refusal_reason(payload))
        if returned_op != op:
            raise TransactionClientError("transaction service answered the wrong op")
        return payload

    def prepare(
        self,
        *,
        expected_target_identity: str,
        compatible_profile_id: str,
        settings_snapshot: Mapping[str, str],
    ) -> PreparedPlan:
        """Run ``PREPARE_PLAN``; verify the digest matches the canonical plan."""
        payload = self._round_trip(
            "PREPARE_PLAN",
            {
                "expected_target_identity": expected_target_identity,
                "compatible_profile_id": compatible_profile_id,
                "settings_snapshot": dict(settings_snapshot),
            },
        )
        if payload.get("status") != "PREPARED":
            raise TransactionClientError("prepare was refused by the install service")
        nonce = payload.get("transaction_nonce")
        plan = payload.get("plan")
        digest = payload.get("plan_digest")
        if not isinstance(nonce, str) or not isinstance(digest, str):
            raise TransactionClientError("prepare returned an unshaped plan")
        plan_dict = _require_mapping(plan, field_name="plan")
        expected = hashlib.sha256(canonical_plan_bytes(plan_dict)).hexdigest()
        if not hmac.compare_digest(expected, digest):
            raise TransactionClientError(
                "prepare digest does not match the canonical plan"
            )
        if plan_dict.get("target_identity_digest") != expected_target_identity:
            raise TransactionClientError(
                "prepare plan is not bound to the confirmed target"
            )
        return PreparedPlan(
            transaction_nonce=nonce, plan=plan_dict, plan_digest=digest
        )

    def execute(self, *, transaction_nonce: str, plan_digest: str) -> ExecuteReceipt:
        """Run ``EXECUTE`` with nonce + digest only.

        The root service revalidates the prepared plan and runs the
        authorized install synchronously before answering ``INSTALLED``;
        the UI never performs, observes, or steers any destructive step.
        """
        payload = self._round_trip(
            "EXECUTE",
            {"transaction_nonce": transaction_nonce, "plan_digest": plan_digest},
            self._execute_transport,
        )
        if payload.get("status") != "INSTALLED":
            raise TransactionClientError("execute was refused by the install service")
        receipt = ExecuteReceipt(
            transaction_nonce=str(payload.get("transaction_nonce")),
            plan_digest=str(payload.get("plan_digest")),
            target_identity=str(payload.get("target_identity")),
        )
        if receipt.transaction_nonce != transaction_nonce or not hmac.compare_digest(
            receipt.plan_digest, plan_digest
        ):
            raise TransactionClientError("execute receipt does not match the plan")
        return receipt


@dataclass(frozen=True, slots=True)
class PreparedConfirmation:
    """The graphical confirm page's pinned plan plus its freshness contract.

    The UI stores this after ``PREPARE_PLAN`` and must call
    :meth:`still_valid` against a fresh read-only inventory immediately
    before ``EXECUTE`` (and when the confirm page regains focus). Any
    inventory refresh or material target-state change invalidates the
    confirmation fail-closed: the parent returns to target selection and
    the stale nonce is never executed.
    """

    prepared: PreparedPlan
    expected_target_identity: str
    expected_display_summary: str
    settings_snapshot: dict[str, str]

    def still_valid(
        self,
        *,
        live_targets: Mapping[str, Mapping[str, object]],
        current_settings: Mapping[str, str],
    ) -> bool:
        """Return ``True`` only when the pinned plan still matches live facts.

        ``live_targets`` maps identity digest to safe display facts with at
        least ``eligible`` (bool) and ``display_summary`` (str). Anything
        missing, ineligible, changed, or settings-drifted invalidates.
        """
        facts = live_targets.get(self.expected_target_identity)
        if not isinstance(facts, Mapping):
            return False
        if facts.get("eligible") is not True:
            return False
        if facts.get("display_summary") != self.expected_display_summary:
            return False
        if dict(current_settings) != dict(self.settings_snapshot):
            return False
        plan = self.prepared.plan
        if plan.get("target_identity_digest") != self.expected_target_identity:
            return False
        expected = hashlib.sha256(canonical_plan_bytes(dict(plan))).hexdigest()
        if not hmac.compare_digest(expected, self.prepared.plan_digest):
            return False
        return True

    def to_json_dict(self) -> dict[str, object]:
        """Render the pinned plan for bounded logging/debugging (no secrets)."""
        return {
            "target_identity_digest": self.expected_target_identity,
            "target_display": self.expected_display_summary,
            "plan_digest": self.prepared.plan_digest,
            "settings_keys": sorted(self.settings_snapshot),
        }


def live_target_facts(    targets: tuple[object, ...],
) -> dict[str, dict[str, object]]:
    """Project installer target observations down to safe UI confirmation facts.

    Accepts objects exposing ``identity_digest``/``display_name`` plus an
    ``eligible`` flag ( duck-typed so the UI never imports policy internals
    for this projection). Only digests, booleans and display text survive;
    paths, locators and raw identity facts never reach the confirm page.
    """
    facts: dict[str, dict[str, object]] = {}
    for target in targets:
        digest = getattr(target, "identity_digest", "")
        display = getattr(target, "display_name", "")
        eligible = getattr(target, "eligible", None)
        if not isinstance(digest, str) or not digest:
            continue
        facts[digest] = {
            "eligible": eligible is True,
            "display_summary": str(display),
        }
    return facts


def canonical_settings_json(settings_snapshot: Mapping[str, str]) -> str:
    """Render a settings snapshot in canonical form for equality checks."""
    return (
        json.dumps(dict(settings_snapshot), sort_keys=True, separators=(",", ":"))
        + "\n"
    )


#: Default Greia-owned release manifest the UI reads its profile id from.
DEFAULT_TARGET_PROFILE_PATH = Path("/etc/greia-os/target-image-profile.json")


def read_compatible_profile_id(
    profile_path: Path = DEFAULT_TARGET_PROFILE_PATH,
) -> str:
    """Read the installer image's own compatible profile id (safe fact).

    Read-only, bounded, symlink-refusing: this is Greia-owned release state,
    not request authority. Any unreadable/invalid manifest fails closed so
    the UI can never prepare a plan against an unknown release.
    """
    if not isinstance(profile_path, Path):
        raise TransactionClientError("target profile path is outside Greia bounds")
    if profile_path.is_symlink() or not profile_path.is_file():
        raise TransactionClientError("target image profile is missing or unsafe")
    try:
        raw_text = profile_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise TransactionClientError("target image profile is unreadable") from exc
    if len(raw_text.encode("utf-8")) > 256 * 1024:
        raise TransactionClientError("target image profile exceeds Greia bound")
    try:
        raw = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise TransactionClientError("target image profile is not valid JSON") from exc
    try:
        profile_id = raw["profile"]["id"]
    except (KeyError, TypeError) as exc:
        raise TransactionClientError("target image profile has no profile id") from exc
    if not isinstance(profile_id, str) or not profile_id or len(profile_id) > 64:
        raise TransactionClientError("compatible profile id is outside Greia bounds")
    return profile_id


__all__ = [
    "DEFAULT_TARGET_PROFILE_PATH",
    "DEFAULT_TRANSACTION_SOCKET_PATH",
    "EXECUTE_TIMEOUT_SECONDS",
    "ExecuteReceipt",
    "InstallTransactionClient",
    "PreparedConfirmation",
    "PreparedPlan",
    "TransactionClientError",
    "canonical_settings_json",
    "live_target_facts",
    "read_compatible_profile_id",
    "socket_transport",
]
