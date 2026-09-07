"""Shared narrow transport for the L7 privileged semantic services.

L7-PROTOCOLS (R0/R1 source scope): message framing, peer validation, schema
bounds and logging discipline shared by the two socket-activated services
(``greia-install-transaction`` and ``greia-system-update``). No sockets are
opened here; each service's endpoint validates one length-prefixed JSON
request against these bounds and returns one bounded response.

Both services share narrow platform libraries (``SlotWriter``,
``SlotFinalizer``, release verification, layout authority, boot
transactions). Neither service is a generic command runner: requests can
never carry raw paths, device names, commands, URLs, mountpoints, partition
numbers or bootloader arguments (see :data:`FORBIDDEN_REQUEST_KEYS` and
:func:`reject_raw_authority`). Both sockets validate peer credentials,
enforce bounded message sizes/timeouts, log only bounded transaction IDs
(never secrets), and stay inactive during ordinary pre-intro boot
(see :func:`require_interactive_boot`).
"""

from __future__ import annotations

import json
import re
import secrets
from dataclasses import dataclass
from typing import Mapping


#: Version of every privileged semantic message in this module.
PROTOCOL_VERSION = 1

#: Upper bound for one framed request or response (small by construction:
#: semantic selectors and digests only, never payloads or file contents).
MAX_MESSAGE_BYTES = 16 * 1024

#: Upper bound for a single framed length prefix (struct ``!I``).
MAX_FRAME_BYTES = MAX_MESSAGE_BYTES

#: Per-connection idle timeout in seconds for the socket-activated services.
SOCKET_TIMEOUT_SECONDS = 5.0

#: Per-request handler deadline in seconds (semantic validation only).
REQUEST_TIMEOUT_SECONDS = 10.0

#: Transaction IDs are 8 random bytes rendered as 16 hex characters.
TRANSACTION_ID_BYTES = 8
_TRANSACTION_ID_RE = re.compile(r"^[0-9a-f]{16}$")

#: Operation names are short uppercase identifiers (no paths or commands).
_OP_RE = re.compile(r"^[A-Z][A-Z0-9_]{0,31}$")

#: Request keys that would smuggle raw authority. Any present key — at any
#: nesting depth — fails the request closed. Matching is case-insensitive.
FORBIDDEN_REQUEST_KEYS = frozenset(
    {
        "path",
        "paths",
        "pathname",
        "device",
        "devices",
        "device_path",
        "block",
        "block_device",
        "command",
        "commands",
        "argv",
        "shell",
        "script",
        "url",
        "urls",
        "href",
        "mountpoint",
        "mountpoints",
        "mount",
        "partition",
        "partitions",
        "partition_number",
        "boot_args",
        "bootargs",
        "bootloader_args",
        "kernel_args",
        "extra_args",
    }
)

#: Boot states in which the privileged services may answer. Ordinary
#: pre-intro boot (``pre_intro`` and anything unrecognized) stays inactive:
#: the socket units are not part of the pre-intro boot transaction and the
#: endpoints refuse requests fail-closed until the platform reports an
#: interactive/boot-ready state.
ACTIVE_BOOT_STATES = frozenset(
    {
        "interactive_ready",
        "installer_ready",
        "update_ready",
    }
)


class PrivilegedChannelError(RuntimeError):
    """Peer, schema, bound or boot-state check failed fail-closed."""


@dataclass(frozen=True, slots=True)
class PeerCredential:
    """Validated Unix peer identity for one socket-activated connection.

    The production transport fills this from ``SO_PEERCRED`` (never from
    request bytes). R0/R1 endpoints take it as an injected typed value so
    peer authorization is provable without sockets.
    """

    uid: int
    pid: int | None = None

    def __post_init__(self) -> None:
        if isinstance(self.uid, bool) or not isinstance(self.uid, int):
            raise PrivilegedChannelError("peer UID must be an integer")
        if self.uid < 0 or self.uid > 2**32 - 1:
            raise PrivilegedChannelError("peer UID is outside Greia bounds")
        if self.pid is not None and (
            isinstance(self.pid, bool) or not isinstance(self.pid, int) or self.pid <= 0
        ):
            raise PrivilegedChannelError("peer PID is outside Greia bounds")


def authorize_peer(credential: PeerCredential, allowed_uids: tuple[int, ...]) -> PeerCredential:
    """Require the peer UID to be one of the service's allowed UIDs."""
    if not isinstance(credential, PeerCredential):
        raise PrivilegedChannelError("peer credential must be attested, never asserted")
    if not allowed_uids:
        raise PrivilegedChannelError("privileged service has no authorized peer")
    for allowed in allowed_uids:
        if isinstance(allowed, bool) or not isinstance(allowed, int) or allowed < 0:
            raise PrivilegedChannelError("allowed peer UID is outside Greia bounds")
    if credential.uid not in allowed_uids:
        raise PrivilegedChannelError("peer UID is not authorized for this service")
    return credential


def new_transaction_id() -> str:
    """Mint one bounded log correlation ID (never a secret or capability)."""
    return secrets.token_hex(TRANSACTION_ID_BYTES)


def require_transaction_id(value: object) -> str:
    """Validate a transaction ID received back from a response."""
    if not isinstance(value, str) or not _TRANSACTION_ID_RE.fullmatch(value):
        raise PrivilegedChannelError("transaction ID is outside Greia bounds")
    return value


def format_log_record(transaction_id: str, op: str, status: str) -> str:
    """Format the single log line per request: ID + op + status only.

    Secrets (nonces, digests, tokens, settings values) must never reach this
    helper: only the already-bounded transaction ID, op and status strings
    are formatted, each re-validated here.
    """
    require_transaction_id(transaction_id)
    require_op(op)
    if not isinstance(status, str) or not _OP_RE.fullmatch(status):
        raise PrivilegedChannelError("log status is outside Greia bounds")
    record = f"tx={transaction_id} op={op} status={status}"
    if len(record.encode("utf-8")) > 256:
        raise PrivilegedChannelError("log record exceeds Greia bound")
    return record


def require_op(value: object) -> str:
    """Validate a semantic operation name (never a command or path)."""
    if not isinstance(value, str) or not _OP_RE.fullmatch(value):
        raise PrivilegedChannelError("operation is outside Greia bounds")
    return value


def reject_raw_authority(params: Mapping[str, object]) -> None:
    """Reject any raw path/device/command/URL authority in request params.

    Scans keys recursively (case-insensitive) against
    :data:`FORBIDDEN_REQUEST_KEYS` and rejects string values shaped like
    absolute paths (``/...``), device nodes (``/dev/...``) or URLs
    (``scheme://...``). Semantic identifiers, digests, nonces and bounded
    settings scalars never take those shapes, so legitimate requests are
    unaffected.
    """
    _scan_value(params, "$")


def _scan_value(value: object, where: str) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise PrivilegedChannelError(
                    f"request key at {where} must be text"
                )
            if key.lower() in FORBIDDEN_REQUEST_KEYS:
                raise PrivilegedChannelError(
                    f"request carries raw authority field: {key}"
                )
            if len(key.encode("utf-8")) > 128:
                raise PrivilegedChannelError(
                    f"request key at {where} exceeds Greia bound"
                )
            _scan_value(item, f"{where}.{key}")
    elif isinstance(value, (list, tuple)):
        if len(value) > 64:
            raise PrivilegedChannelError(f"request list at {where} exceeds Greia bound")
        for index, item in enumerate(value):
            _scan_value(item, f"{where}[{index}]")
    elif isinstance(value, str):
        if len(value.encode("utf-8")) > 4096:
            raise PrivilegedChannelError(
                f"request text at {where} exceeds Greia bound"
            )
        lowered = value.strip().lower()
        if value.startswith("/") or lowered.startswith("file://"):
            raise PrivilegedChannelError(
                f"request carries raw path authority at {where}"
            )
        if "://" in value:
            raise PrivilegedChannelError(
                f"request carries raw URL authority at {where}"
            )
        if lowered.startswith("/dev/") or value.startswith("/dev/"):
            raise PrivilegedChannelError(
                f"request carries raw device authority at {where}"
            )
    elif isinstance(value, bool) or value is None or isinstance(value, (int, float)):
        if isinstance(value, float):
            raise PrivilegedChannelError(
                f"request number at {where} must be an integer"
            )
        if isinstance(value, int) and not isinstance(value, bool):
            if abs(value) > 2**63 - 1:
                raise PrivilegedChannelError(
                    f"request integer at {where} exceeds Greia bound"
                )
    else:
        raise PrivilegedChannelError(
            f"request value at {where} is not portable JSON"
        )


def encode_request(op: str, params: Mapping[str, object]) -> bytes:
    """Encode one outbound request (client side / test harness)."""
    require_op(op)
    if not isinstance(params, Mapping):
        raise PrivilegedChannelError("request params must be an object")
    reject_raw_authority(params)
    document = {
        "protocol_version": PROTOCOL_VERSION,
        "op": op,
        "params": dict(params),
    }
    try:
        encoded = (
            json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise PrivilegedChannelError("request is not portable JSON") from exc
    if len(encoded) > MAX_MESSAGE_BYTES:
        raise PrivilegedChannelError("request exceeds Greia bound")
    return encoded


def decode_request(raw: bytes) -> tuple[str, dict[str, object]]:
    """Decode and schema-validate one inbound framed request."""
    if not isinstance(raw, (bytes, bytearray)) or not raw:
        raise PrivilegedChannelError("request frame is empty")
    if len(raw) > MAX_MESSAGE_BYTES:
        raise PrivilegedChannelError("request exceeds Greia bound")
    try:
        value = json.loads(bytes(raw).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PrivilegedChannelError("request is not valid JSON") from exc
    if not isinstance(value, dict) or set(value) != {"protocol_version", "op", "params"}:
        raise PrivilegedChannelError("request fields are invalid")
    if value.get("protocol_version") != PROTOCOL_VERSION:
        raise PrivilegedChannelError("unsupported privileged protocol version")
    op = require_op(value.get("op"))
    params = value.get("params")
    if not isinstance(params, dict):
        raise PrivilegedChannelError("request params must be an object")
    if len(params) > 16:
        raise PrivilegedChannelError("request params exceed Greia bound")
    reject_raw_authority(params)
    return op, dict(params)


def encode_response(transaction_id: str, op: str, payload: Mapping[str, object]) -> bytes:
    """Encode one bounded response (service side)."""
    require_transaction_id(transaction_id)
    require_op(op)
    if not isinstance(payload, Mapping):
        raise PrivilegedChannelError("response payload must be an object")
    document = {
        "protocol_version": PROTOCOL_VERSION,
        "transaction_id": transaction_id,
        "op": op,
        "payload": dict(payload),
    }
    try:
        encoded = (
            json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise PrivilegedChannelError("response is not portable JSON") from exc
    if len(encoded) > MAX_MESSAGE_BYTES:
        raise PrivilegedChannelError("response exceeds Greia bound")
    return encoded


def decode_response(raw: bytes) -> tuple[str, str, dict[str, object]]:
    """Decode one response frame: (transaction_id, op, payload)."""
    if not isinstance(raw, (bytes, bytearray)) or not raw:
        raise PrivilegedChannelError("response frame is empty")
    if len(raw) > MAX_MESSAGE_BYTES:
        raise PrivilegedChannelError("response exceeds Greia bound")
    try:
        value = json.loads(bytes(raw).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PrivilegedChannelError("response is not valid JSON") from exc
    if (
        not isinstance(value, dict)
        or set(value) != {"protocol_version", "transaction_id", "op", "payload"}
    ):
        raise PrivilegedChannelError("response fields are invalid")
    if value.get("protocol_version") != PROTOCOL_VERSION:
        raise PrivilegedChannelError("unsupported privileged protocol version")
    transaction_id = require_transaction_id(value.get("transaction_id"))
    op = require_op(value.get("op"))
    payload = value.get("payload")
    if not isinstance(payload, dict):
        raise PrivilegedChannelError("response payload must be an object")
    return transaction_id, op, dict(payload)


def require_interactive_boot(boot_state: object) -> str:
    """Require a boot-ready state; ordinary pre-intro boot stays inactive."""
    if not isinstance(boot_state, str) or boot_state not in ACTIVE_BOOT_STATES:
        raise PrivilegedChannelError(
            "privileged service is inactive during ordinary pre-intro boot"
        )
    return boot_state
