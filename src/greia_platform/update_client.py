"""Small typed client for the installed Greia system-update socket.

The Parent process may request only selector-free semantic operations. The
client owns AF_UNIX framing and bounds; it never accepts paths, slots,
commands or caller-provided request parameters.
"""

from __future__ import annotations

import socket
from pathlib import Path
from typing import Callable

from .privileged_channel import MAX_MESSAGE_BYTES, PrivilegedChannelError
from .update_privileged import (
    UPDATE_PRIVILEGED_PANEL_OPS,
    UpdatePrivilegedError,
    build_request,
    read_response,
)


UPDATE_PRIVILEGED_SOCKET = "/run/greia-os/system-update.sock"
_OP_TIMEOUT_SECONDS = {
    "STATUS": 10.0,
    "VERIFY_CURRENT_CANDIDATE": 60.0,
    "STAGE_CURRENT_CANDIDATE": 1800.0,
    "RECONCILE": 30.0,
    "REQUEST_RESTART": 30.0,
}


class UpdatePrivilegedClientError(RuntimeError):
    """The privileged update socket did not return one valid bounded reply."""


class UpdatePrivilegedClient:
    """Issue one known Parent-authorized update operation over AF_UNIX."""

    def __init__(
        self,
        socket_path: str | Path = UPDATE_PRIVILEGED_SOCKET,
        *,
        socket_factory: Callable[..., socket.socket] = socket.socket,
    ) -> None:
        self.socket_path = str(socket_path)
        self._socket_factory = socket_factory

    def request(self, op: str) -> dict[str, object]:
        """Send one operation and return only its bounded payload object."""
        if op not in UPDATE_PRIVILEGED_PANEL_OPS:
            raise UpdatePrivilegedClientError(
                f"operation is outside the Parent update contract: {op!r}"
            )
        try:
            request = build_request(op)
        except UpdatePrivilegedError as exc:
            raise UpdatePrivilegedClientError(str(exc)) from exc

        try:
            with self._socket_factory(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
                connection.settimeout(_OP_TIMEOUT_SECONDS[op])
                connection.connect(self.socket_path)
                connection.sendall(request)
                connection.shutdown(socket.SHUT_WR)
                response = self._read_one_response(connection)
        except (OSError, TimeoutError) as exc:
            raise UpdatePrivilegedClientError(
                "Greia system-update service is unavailable"
            ) from exc

        try:
            _transaction_id, response_op, payload = read_response(response)
        except (UpdatePrivilegedError, PrivilegedChannelError) as exc:
            raise UpdatePrivilegedClientError(
                "Greia system-update response is invalid"
            ) from exc
        if response_op not in {op, "ERROR"}:
            raise UpdatePrivilegedClientError(
                "Greia system-update response operation does not match the request"
            )
        if response_op == "ERROR" and payload.get("status") != "REFUSED":
            raise UpdatePrivilegedClientError(
                "Greia system-update returned an invalid refusal"
            )
        return payload

    @staticmethod
    def _read_one_response(connection: socket.socket) -> bytes:
        chunks: list[bytes] = []
        received = 0
        while True:
            chunk = connection.recv(4096)
            if not chunk:
                break
            received += len(chunk)
            if received > MAX_MESSAGE_BYTES:
                raise UpdatePrivilegedClientError(
                    "Greia system-update response exceeds its bound"
                )
            chunks.append(chunk)
            if b"\n" in chunk:
                break
        raw = b"".join(chunks)
        if not raw.endswith(b"\n") or raw.count(b"\n") != 1:
            raise UpdatePrivilegedClientError(
                "Greia system-update response framing is invalid"
            )
        return raw
