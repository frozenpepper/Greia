from __future__ import annotations

import json
import socket
import struct


PROTOCOL_VERSION = 1
MAX_MESSAGE_BYTES = 64 * 1024
_LENGTH = struct.Struct("!I")


class EventProtocolError(RuntimeError):
    pass


def send_message(sock: socket.socket, message: dict[str, object]) -> None:
    document = dict(message)
    document["protocol_version"] = PROTOCOL_VERSION
    try:
        encoded = json.dumps(
            document,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise EventProtocolError("event protocol message is not portable JSON") from exc
    if not encoded or len(encoded) > MAX_MESSAGE_BYTES:
        raise EventProtocolError("event protocol message exceeds limit")
    sock.sendall(_LENGTH.pack(len(encoded)))
    sock.sendall(encoded)


def receive_message(
    sock: socket.socket,
    *,
    max_message_bytes: int = MAX_MESSAGE_BYTES,
) -> dict[str, object]:
    length = _LENGTH.unpack(_recv_exact(sock, _LENGTH.size))[0]
    if length <= 0 or length > min(max_message_bytes, MAX_MESSAGE_BYTES):
        raise EventProtocolError("invalid event protocol message length")
    try:
        raw = json.loads(_recv_exact(sock, length).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EventProtocolError("invalid event protocol JSON") from exc
    if not isinstance(raw, dict):
        raise EventProtocolError("event protocol message must be an object")
    if raw.get("protocol_version") != PROTOCOL_VERSION:
        raise EventProtocolError("unsupported event protocol version")
    return raw


def _recv_exact(sock: socket.socket, size: int) -> bytes:
    chunks: list[bytes] = []
    remaining = size
    while remaining:
        chunk = sock.recv(remaining)
        if not chunk:
            raise EventProtocolError("event protocol connection closed early")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)
