from __future__ import annotations

import os
import socket
from dataclasses import dataclass
from pathlib import Path

from .event_protocol import EventProtocolError, receive_message, send_message


class ActivityEventClientError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ActivityEventReceipt:
    event_record_id: int
    duplicate: bool
    reward_deltas: tuple[tuple[str, int], ...]


@dataclass(frozen=True, slots=True)
class ActivityEventClient:
    """Runtime-neutral client for one Activity session's validated event channel."""

    socket_path: Path
    session_token: str

    @classmethod
    def from_environment(cls) -> "ActivityEventClient":
        raw_socket = os.environ.get("GREIA_EVENT_SOCKET", "").strip()
        token = os.environ.get("GREIA_EVENT_TOKEN", "").strip()
        if not raw_socket or not token:
            raise ActivityEventClientError("Activity was not launched with Greia event service")
        return cls(Path(raw_socket), token)

    def emit(
        self,
        event_id: str,
        *,
        idempotency_key: str,
        score: float | int | None = None,
        payload: object = None,
    ) -> ActivityEventReceipt:
        request: dict[str, object] = {
            "op": "event.emit",
            "session_token": self.session_token,
            "event_id": event_id,
            "idempotency_key": idempotency_key,
            "score": score,
            "payload": {} if payload is None else payload,
        }
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
                connection.connect(str(self.socket_path))
                send_message(connection, request)
                response = receive_message(connection)
        except (OSError, EventProtocolError) as exc:
            raise ActivityEventClientError("cannot communicate with Greia event broker") from exc
        if response.get("ok") is not True:
            code = response.get("error_code", "event_error")
            message = response.get("message", "event operation failed")
            raise ActivityEventClientError(f"{code}: {message}")
        record_id = response.get("event_record_id")
        duplicate = response.get("duplicate")
        rewards_raw = response.get("reward_deltas", [])
        if not isinstance(record_id, int) or isinstance(record_id, bool) or record_id < 1:
            raise ActivityEventClientError("event broker returned invalid event record ID")
        if not isinstance(duplicate, bool):
            raise ActivityEventClientError("event broker returned invalid duplicate flag")
        if not isinstance(rewards_raw, list):
            raise ActivityEventClientError("event broker returned invalid reward deltas")
        rewards: list[tuple[str, int]] = []
        for item in rewards_raw:
            if (
                not isinstance(item, list)
                or len(item) != 2
                or not isinstance(item[0], str)
                or not isinstance(item[1], int)
                or isinstance(item[1], bool)
            ):
                raise ActivityEventClientError("event broker returned invalid reward delta")
            rewards.append((item[0], item[1]))
        return ActivityEventReceipt(record_id, duplicate, tuple(rewards))
