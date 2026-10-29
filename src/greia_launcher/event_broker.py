from __future__ import annotations

import os
import secrets
import shutil
import socketserver
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path

from greia_platform.achievements import AchievementError, ProfileAchievementService
from greia_platform.activities import ActivityManifest
from greia_platform.event_protocol import EventProtocolError, receive_message, send_message
from greia_platform.history import (
    EventIdempotencyConflict,
    EventValidationError,
    HistoryCapacityError,
    HistoryError,
    ProgressionPolicy,
    SessionHistoryRecorder,
)


SANDBOX_EVENT_ROOT = Path("/run/greia-events")
SANDBOX_EVENT_SOCKET = SANDBOX_EVENT_ROOT / "events.sock"


class _EventRequestError(RuntimeError):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class _EventRequestHandler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        server = self.server
        assert isinstance(server, _EventUnixServer)
        self.request.settimeout(server.request_timeout_seconds)
        try:
            request = receive_message(
                self.request,
                max_message_bytes=server.max_message_bytes,
            )
            if request.get("session_token") != server.session_token:
                raise _EventRequestError("unauthorized", "invalid event session token")
            response = server.dispatch(request)
            send_message(self.request, {"ok": True, **response})
        except _EventRequestError as exc:
            send_message(
                self.request,
                {"ok": False, "error_code": exc.code, "message": exc.message},
            )
        except EventIdempotencyConflict:
            send_message(
                self.request,
                {
                    "ok": False,
                    "error_code": "idempotency_conflict",
                    "message": "event idempotency key conflicts with prior content",
                },
            )
        except EventValidationError:
            send_message(
                self.request,
                {
                    "ok": False,
                    "error_code": "invalid_event",
                    "message": "event was rejected by Greia policy",
                },
            )
        except HistoryCapacityError:
            send_message(
                self.request,
                {
                    "ok": False,
                    "error_code": "history_unavailable",
                    "message": "event was not recorded because storage headroom is exhausted",
                },
            )
        except (HistoryError, EventProtocolError):
            send_message(
                self.request,
                {
                    "ok": False,
                    "error_code": "event_error",
                    "message": "event operation was rejected",
                },
            )
        except Exception:
            send_message(
                self.request,
                {
                    "ok": False,
                    "error_code": "internal_error",
                    "message": "event broker operation failed",
                },
            )


class _EventUnixServer(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    allow_reuse_address = False
    daemon_threads = True
    request_queue_size = 2
    max_active_requests = 2
    request_timeout_seconds = 2.0

    def __init__(
        self,
        socket_path: Path,
        store: SessionHistoryRecorder,
        manifest: ActivityManifest,
        progression: ProgressionPolicy,
        session_id: str,
        session_token: str,
        achievement_service: ProfileAchievementService | None = None,
    ):
        self.store = store
        self.manifest = manifest
        self.progression = progression
        self.session_id = session_id
        self.session_token = session_token
        self.achievement_service = achievement_service
        self.max_message_bytes = min(
            64 * 1024,
            store.policy.max_event_payload_bytes + 8 * 1024,
        )
        self._request_slots = threading.BoundedSemaphore(self.max_active_requests)
        super().__init__(str(socket_path), _EventRequestHandler)

    def process_request(self, request, client_address) -> None:
        if not self._request_slots.acquire(blocking=False):
            request.close()
            return
        try:
            super().process_request(request, client_address)
        except Exception:
            self._request_slots.release()
            raise

    def process_request_thread(self, request, client_address) -> None:
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._request_slots.release()

    def dispatch(self, request: dict[str, object]) -> dict[str, object]:
        if request.get("op") != "event.emit":
            raise _EventRequestError("unsupported_operation", "unknown event operation")
        event_id = _required_text(request, "event_id")
        idempotency_key = _required_text(request, "idempotency_key")
        score = request.get("score")
        payload = request.get("payload", {})
        receipt = self.store.emit_event(
            self.manifest,
            self.progression,
            session_id=self.session_id,
            event_id=event_id,
            idempotency_key=idempotency_key,
            score=score,
            payload=payload,
        )

        # Achievement evaluation is trusted platform work after the history fact
        # has been accepted. Failure is fail-soft: the event/reward receipt stays
        # valid and a later refresh can reconstruct missing unlock metadata from
        # authoritative history.
        achievement_unlocks: list[str] = []
        if self.achievement_service is not None:
            try:
                snapshot = self.achievement_service.refresh(self.store.profile)
                achievement_unlocks = [
                    entry.definition.achievement_id
                    for entry in snapshot.newly_unlocked
                ]
            except (AchievementError, OSError, ValueError):
                achievement_unlocks = []

        return {
            "event_record_id": receipt.event_record_id,
            "duplicate": receipt.duplicate,
            "reward_deltas": [list(item) for item in receipt.reward_deltas],
            "achievement_unlocks": achievement_unlocks,
        }


@dataclass(slots=True)
class ActivityEventBroker:
    """One-session broker bound to one trusted profile/session/Activity context."""

    host_root: Path
    host_socket: Path
    child_socket: Path
    session_token: str
    _server: _EventUnixServer
    _thread: threading.Thread
    _stopped: bool = False

    @classmethod
    def start(
        cls,
        store: SessionHistoryRecorder,
        manifest: ActivityManifest,
        progression: ProgressionPolicy,
        session_id: str,
        *,
        runtime_root: Path | None = None,
        sandboxed: bool,
        achievement_service: ProfileAchievementService | None = None,
    ) -> "ActivityEventBroker":
        base = (runtime_root or _default_runtime_root()).resolve(strict=False)
        if base.is_symlink():
            raise HistoryError("event broker runtime root may not be a symbolic link")
        host_root = base / session_id
        host_root.mkdir(parents=True, exist_ok=False)
        os.chmod(host_root, 0o700)
        host_socket = host_root / "events.sock"
        if len(os.fsencode(host_socket)) >= 100:
            shutil.rmtree(host_root, ignore_errors=True)
            raise HistoryError("event broker socket path is too long")
        token = secrets.token_urlsafe(32)
        try:
            server = _EventUnixServer(
                host_socket,
                store,
                manifest,
                progression,
                session_id,
                token,
                achievement_service,
            )
        except Exception:
            shutil.rmtree(host_root, ignore_errors=True)
            raise
        os.chmod(host_socket, 0o600)
        thread = threading.Thread(
            target=server.serve_forever,
            kwargs={"poll_interval": 0.05},
            name=f"greia-events-{session_id[:8]}",
            daemon=True,
        )
        thread.start()
        return cls(
            host_root=host_root,
            host_socket=host_socket,
            child_socket=(SANDBOX_EVENT_SOCKET if sandboxed else host_socket),
            session_token=token,
            _server=server,
            _thread=thread,
        )

    def stop(self) -> None:
        if self._stopped:
            return
        self._stopped = True
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=1.0)
        shutil.rmtree(self.host_root, ignore_errors=True)


def _required_text(container: dict[str, object], key: str) -> str:
    value = container.get(key)
    if not isinstance(value, str) or not value:
        raise _EventRequestError("invalid_request", f"{key} must be non-empty text")
    return value


def _default_runtime_root() -> Path:
    configured = os.environ.get("GREIA_EVENT_BROKER_ROOT")
    if configured:
        return Path(configured)
    os_root = Path(os.environ.get("GREIA_OS_ROOT", "/opt/greia-os")).resolve(strict=False)
    from .installed_root import INSTALLED_APPLICATION_ROOT, is_installed_root

    if is_installed_root(os_root) and INSTALLED_APPLICATION_ROOT.exists():
        return Path("/run/greia-os/events")
    base = Path(tempfile.gettempdir()) / f"greia-events-{os.getuid()}"
    if os.name == "posix" and len(os.fsencode(base / ("0" * 32) / "events.sock")) >= 100:
        return Path("/tmp") / f"g-e-{os.getuid()}"
    return base
