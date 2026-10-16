from __future__ import annotations

import os
import socket
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

from .event_protocol import EventProtocolError, receive_message, send_message


class ActivityEventClientError(RuntimeError):
    pass


class ActivityEventServiceUnavailable(ActivityEventClientError):
    """The Activity was started without a Greia event service (desktop/dev run).

    This is an expected, deliberate no-op condition rather than a rejection, so
    it is not reported as a diagnostic.
    """


class EventFailureReporter:
    """Report rejected/failed Activity events on stderr, once per distinct reason.

    Activity event emission is fail-soft: a failure must never interrupt play.
    Failing silently, however, hid a real defect (an over-long idempotency key
    made every completion event vanish). Each distinct ``(event_id, reason)`` is
    written once to the Activity process's stderr; the set of remembered
    reasons is bounded so a misbehaving Activity cannot spam logs or leak memory.
    """

    MAX_DISTINCT = 32

    def __init__(self, stream: TextIO | None = None) -> None:
        self._stream = stream
        self._seen: set[tuple[str, str]] = set()
        self._overflow_reported = False

    def report(self, event_id: str, idempotency_key: object, error: BaseException) -> bool:
        """Write one diagnostic line unless this reason was already reported."""

        if isinstance(error, ActivityEventServiceUnavailable):
            return False
        reason = str(error) or type(error).__name__
        marker = (str(event_id)[:80], reason[:160])
        if marker in self._seen:
            return False
        stream = self._stream if self._stream is not None else sys.stderr
        if len(self._seen) >= self.MAX_DISTINCT:
            if self._overflow_reported:
                return False
            self._overflow_reported = True
            text = "[greia] further distinct Activity event failures suppressed"
        else:
            self._seen.add(marker)
            key_bytes = (
                len(idempotency_key.encode("utf-8", "replace"))
                if isinstance(idempotency_key, str)
                else -1
            )
            text = (
                f"[greia] Activity event {marker[0]!r} was not recorded: {marker[1]} "
                f"(idempotency_key={key_bytes} bytes)"
            )
        try:
            print(text, file=stream, flush=True)
        except Exception:
            return False
        return True


@dataclass(frozen=True, slots=True)
class ActivityEventReceipt:
    event_record_id: int
    duplicate: bool
    reward_deltas: tuple[tuple[str, int], ...]
    achievement_unlocks: tuple[str, ...] = ()


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
            raise ActivityEventServiceUnavailable(
                "Activity was not launched with Greia event service"
            )
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
        achievements_raw = response.get("achievement_unlocks", [])
        if not isinstance(record_id, int) or isinstance(record_id, bool) or record_id < 1:
            raise ActivityEventClientError("event broker returned invalid event record ID")
        if not isinstance(duplicate, bool):
            raise ActivityEventClientError("event broker returned invalid duplicate flag")
        if not isinstance(rewards_raw, list):
            raise ActivityEventClientError("event broker returned invalid reward deltas")
        if not isinstance(achievements_raw, list):
            raise ActivityEventClientError("event broker returned invalid achievement unlocks")
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
        achievement_unlocks: list[str] = []
        for item in achievements_raw:
            if not isinstance(item, str) or not item:
                raise ActivityEventClientError(
                    "event broker returned invalid achievement unlock ID"
                )
            achievement_unlocks.append(item)
        return ActivityEventReceipt(
            record_id,
            duplicate,
            tuple(rewards),
            tuple(achievement_unlocks),
        )
