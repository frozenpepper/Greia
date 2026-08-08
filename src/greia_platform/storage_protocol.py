from __future__ import annotations

import json
import socket
import struct


PROTOCOL_VERSION = 1
MAX_HEADER_BYTES = 65_536
_HEADER = struct.Struct("!I")


class StorageProtocolError(RuntimeError):
    pass


def send_frame(sock: socket.socket, header: dict[str, object], payload: bytes = b"") -> None:
    document = dict(header)
    document["protocol_version"] = PROTOCOL_VERSION
    document["payload_bytes"] = len(payload)
    encoded = json.dumps(
        document,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    if len(encoded) > MAX_HEADER_BYTES:
        raise StorageProtocolError("storage protocol header exceeds limit")
    sock.sendall(_HEADER.pack(len(encoded)))
    sock.sendall(encoded)
    if payload:
        sock.sendall(payload)


def receive_frame(
    sock: socket.socket,
    *,
    max_payload_bytes: int,
) -> tuple[dict[str, object], bytes]:
    header_length = _HEADER.unpack(_recv_exact(sock, _HEADER.size))[0]
    if header_length <= 0 or header_length > MAX_HEADER_BYTES:
        raise StorageProtocolError("invalid storage protocol header length")
    try:
        raw = json.loads(_recv_exact(sock, header_length).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StorageProtocolError("invalid storage protocol JSON header") from exc
    if not isinstance(raw, dict):
        raise StorageProtocolError("storage protocol header must be an object")
    if raw.get("protocol_version") != PROTOCOL_VERSION:
        raise StorageProtocolError("unsupported storage protocol version")
    payload_length = raw.get("payload_bytes")
    if not isinstance(payload_length, int) or isinstance(payload_length, bool):
        raise StorageProtocolError("storage protocol payload length is invalid")
    if payload_length < 0 or payload_length > max_payload_bytes:
        raise StorageProtocolError("storage protocol payload exceeds limit")
    payload = _recv_exact(sock, payload_length) if payload_length else b""
    return raw, payload


def _recv_exact(sock: socket.socket, size: int) -> bytes:
    chunks: list[bytes] = []
    remaining = size
    while remaining:
        chunk = sock.recv(remaining)
        if not chunk:
            raise StorageProtocolError("storage protocol connection closed early")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)
