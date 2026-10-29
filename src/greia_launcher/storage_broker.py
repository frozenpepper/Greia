from __future__ import annotations

import json
import os
import secrets
import shutil
import socketserver
import tempfile
import threading
from dataclasses import asdict, dataclass
from pathlib import Path

from greia_platform.creation_access import CreationAccessDenied, CreationSessionAccess
from greia_platform.creation_capacity import CreationSpaceError
from greia_platform.creation_media import CreationMediaError
from greia_platform.creations import CreationLibraryError
from greia_platform.storage import ActivityStorage, StorageError, StorageQuotaExceeded
from greia_platform.storage_protocol import (
    StorageProtocolError,
    receive_frame,
    send_frame,
)

from .creation_selection import (
    CreationSelectionCoordinator,
    SelectionRequest,
)


SANDBOX_STORAGE_ROOT = Path("/run/greia-storage")
SANDBOX_STORAGE_SOCKET = SANDBOX_STORAGE_ROOT / "storage.sock"


class _StorageRequestHandler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        server = self.server
        assert isinstance(server, _StorageUnixServer)
        self.request.settimeout(server.request_timeout_seconds)
        try:
            request, payload = receive_frame(
                self.request,
                max_payload_bytes=server.max_payload_bytes,
            )
            if request.get("session_token") != server.session_token:
                raise _BrokerRequestError("unauthorized", "invalid storage session token")
            response, response_payload = server.dispatch(request, payload)
            send_frame(self.request, {"ok": True, **response}, response_payload)
        except _BrokerRequestError as exc:
            send_frame(
                self.request,
                {"ok": False, "error_code": exc.code, "message": exc.message},
            )
        except CreationAccessDenied:
            send_frame(self.request, {"ok": False, "error_code": "unauthorized", "message": "creation access denied"})
        except (StorageQuotaExceeded, CreationSpaceError) as exc:
            send_frame(
                self.request,
                {"ok": False, "error_code": "quota_exceeded", "message": str(exc)},
            )
        except CreationMediaError:
            send_frame(self.request, {"ok": False, "error_code": "invalid_media", "message": "creation media was rejected"})
        except CreationLibraryError:
            send_frame(self.request, {"ok": False, "error_code": "creation_error", "message": "creation operation failed"})
        except (StorageError, StorageProtocolError):
            send_frame(
                self.request,
                {
                    "ok": False,
                    "error_code": "storage_error",
                    "message": "storage operation was rejected",
                },
            )
        except Exception:
            send_frame(
                self.request,
                {
                    "ok": False,
                    "error_code": "internal_error",
                    "message": "storage broker operation failed",
                },
            )


class _BrokerRequestError(RuntimeError):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class _StorageUnixServer(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    allow_reuse_address = False
    daemon_threads = True
    request_queue_size = 2
    max_active_requests = 2
    request_timeout_seconds = 2.0

    def __init__(
        self,
        socket_path: Path,
        storage: ActivityStorage,
        session_token: str,
    ):
        self.storage = storage
        self.creation_access: CreationSessionAccess | None = None
        self.selection: CreationSelectionCoordinator | None = None
        self.session_token = session_token
        self.max_payload_bytes = max(
            storage.policy.max_file_bytes,
            storage.policy.max_kv_value_bytes,
        )
        self._request_slots = threading.BoundedSemaphore(self.max_active_requests)
        super().__init__(str(socket_path), _StorageRequestHandler)

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

    def dispatch(
        self,
        request: dict[str, object],
        payload: bytes,
    ) -> tuple[dict[str, object], bytes]:
        operation = request.get("op")
        if operation in (
            "creations.publish_private",
            "creations.import_selected",
            "creations.request_selection",
            "creations.poll_selection",
            "creations.cancel_selection",
        ):
            # The Activity can request a child-owned picker, but can NEVER
            # browse, delete, grant, or resolve a chosen library artifact.
            access = self.creation_access
            if access is None:
                raise _BrokerRequestError("unauthorized", "creations not enabled for Activity")
            if payload:
                raise _BrokerRequestError("invalid_request", "creation actions carry no raw payload")
            if operation == "creations.request_selection":
                chooser = self.selection
                if chooser is None:
                    raise _BrokerRequestError("unauthorized", "picker not bound")
                request = chooser.request(
                    media_types=request.get("media_types"),
                    roles=request.get("roles"),
                )
                return {"request_id": request.request_id}, b""
            if operation == "creations.poll_selection":
                chooser = self.selection
                if chooser is None:
                    raise _BrokerRequestError("unauthorized", "picker not bound")
                status = chooser.poll(_required_text(request, "request_id"))
                return {
                    "state": status.state.value,
                    "selection_token": status.selection_token,
                }, b""
            if operation == "creations.cancel_selection":
                chooser = self.selection
                if chooser is None:
                    raise _BrokerRequestError("unauthorized", "picker not bound")
                return {"cancelled": chooser.cancel(_required_text(request, "request_id"))}, b""
            if operation == "creations.publish_private":
                record = access.publish_private_file(
                    filename=_required_text(request, "filename"),
                    media_type=_required_text(request, "media_type"),
                    role=_required_text(request, "role"),
                    title=_optional_text(request, "title"),
                )
                return {"record": asdict(record)}, b""
            selected = access.import_selected(_required_text(request, "selection_token"))
            return {"record": asdict(selected.record)}, selected.payload
        if operation == "kv.get":
            key = _required_text(request, "key")
            sentinel = object()
            value = self.storage.kv_get(key, sentinel)
            if value is sentinel:
                return {"found": False}, b""
            return {"found": True}, _json_payload(value)
        if operation == "kv.set":
            key = _required_text(request, "key")
            if len(payload) > self.storage.policy.max_kv_value_bytes:
                raise StorageQuotaExceeded("KV value exceeds per-value limit")
            try:
                value = json.loads(payload.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise _BrokerRequestError("invalid_request", "KV value is not JSON") from exc
            self.storage.kv_set(key, value)
            return {}, b""
        if operation == "kv.delete":
            return {"deleted": self.storage.kv_delete(_required_text(request, "key"))}, b""
        if operation == "kv.list":
            prefix = request.get("prefix")
            if prefix is not None and not isinstance(prefix, str):
                raise _BrokerRequestError("invalid_request", "KV prefix must be text")
            return {}, _json_payload(list(self.storage.kv_list(prefix)))
        if operation == "files.read":
            return {}, self.storage.file_read(_required_text(request, "name"))
        if operation == "files.write":
            self.storage.file_write_atomic(_required_text(request, "name"), payload)
            return {}, b""
        if operation == "files.delete":
            return {
                "deleted": self.storage.file_delete(_required_text(request, "name"))
            }, b""
        if operation == "files.list":
            prefix = request.get("prefix")
            if prefix is not None and not isinstance(prefix, str):
                raise _BrokerRequestError("invalid_request", "file prefix must be text")
            return {}, _json_payload(list(self.storage.file_list(prefix)))
        if operation == "info":
            return {}, _json_payload(self.storage.info().as_dict())
        if operation == "checkpoint":
            return {"checkpoint_token": self.storage.checkpoint()}, b""
        raise _BrokerRequestError("unsupported_operation", "unknown storage operation")


@dataclass(slots=True)
class ActivityStorageBroker:
    """One-session Unix-socket broker for an Activity's logical storage."""

    host_root: Path
    host_socket: Path
    child_socket: Path
    session_token: str
    _server: _StorageUnixServer
    _thread: threading.Thread
    _stopped: bool = False

    @classmethod
    def start(
        cls,
        storage: ActivityStorage,
        session_id: str,
        *,
        runtime_root: Path | None = None,
        sandboxed: bool,
    ) -> "ActivityStorageBroker":
        base = runtime_root or _default_runtime_root()
        base = base.resolve(strict=False)
        if base.is_symlink():
            raise StorageError("storage broker runtime root may not be a symbolic link")
        host_root = base / session_id
        host_root.mkdir(parents=True, exist_ok=False)
        os.chmod(host_root, 0o700)
        host_socket = host_root / "storage.sock"
        if len(os.fsencode(host_socket)) >= 100:
            shutil.rmtree(host_root, ignore_errors=True)
            raise StorageError("storage broker socket path is too long")
        token = secrets.token_urlsafe(32)
        try:
            server = _StorageUnixServer(host_socket, storage, token)
        except Exception:
            shutil.rmtree(host_root, ignore_errors=True)
            raise
        os.chmod(host_socket, 0o600)
        thread = threading.Thread(
            target=server.serve_forever,
            kwargs={"poll_interval": 0.05},
            name=f"greia-storage-{session_id[:8]}",
            daemon=True,
        )
        thread.start()
        return cls(
            host_root=host_root,
            host_socket=host_socket,
            child_socket=(SANDBOX_STORAGE_SOCKET if sandboxed else host_socket),
            session_token=token,
            _server=server,
            _thread=thread,
        )

    def bind_creations(self, access: CreationSessionAccess) -> None:
        """Bind trusted producer/selection authority before Activity launch."""
        if self._stopped or self._server.creation_access is not None:
            raise StorageError("creations authority may be bound only once per live session")
        if access.session_id != self.host_root.name:
            raise StorageError("creations authority does not belong to this broker session")
        self._server.creation_access = access
        self._server.selection = CreationSelectionCoordinator(
            access, access.session_id
        )

    def enable_creation_picker(self) -> None:
        """Trusted display owner attests a real session modal is available.

        Never exposed as an Activity broker operation. Without this explicit
        activation the child client's picker requests fail closed.
        """
        selection = self._server.selection
        if self._stopped or selection is None:
            raise StorageError("creation picker session is unavailable")
        selection.enable_presenter()

    def disable_creation_picker(self) -> None:
        selection = self._server.selection
        if selection is not None and not self._stopped:
            selection.disable_presenter()

    def pending_creation_selection(self) -> SelectionRequest | None:
        """Trusted supervisor read; never routed over the Activity socket."""
        selection = self._server.selection
        return None if self._stopped or selection is None else selection.trusted_pending()

    def complete_creation_selection(self, request_id: str, creation_id: str) -> str:
        """Trusted viewer alone may complete a child's selected artifact."""
        selection = self._server.selection
        if self._stopped or selection is None:
            raise StorageError("creation picker session is unavailable")
        return selection.trusted_complete(request_id, creation_id)

    def cancel_creation_selection(self, request_id: str) -> None:
        selection = self._server.selection
        if self._stopped or selection is None:
            raise StorageError("creation picker session is unavailable")
        selection.trusted_cancel(request_id)

    def stop(self) -> None:
        if self._stopped:
            return
        self._stopped = True
        if self._server.selection is not None:
            self._server.selection.close()
        if self._server.creation_access is not None:
            self._server.creation_access.close()
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=1.0)
        shutil.rmtree(self.host_root, ignore_errors=True)


def _required_text(container: dict[str, object], key: str) -> str:
    value = container.get(key)
    if not isinstance(value, str) or not value:
        raise _BrokerRequestError("invalid_request", f"{key} must be non-empty text")
    return value


def _optional_text(container: dict[str, object], key: str) -> str:
    value = container.get(key, "")
    if not isinstance(value, str):
        raise _BrokerRequestError("invalid_request", f"{key} must be text")
    return value


def _json_payload(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _default_runtime_root() -> Path:
    configured = os.environ.get("GREIA_STORAGE_BROKER_ROOT")
    if configured:
        return Path(configured)
    os_root = Path(os.environ.get("GREIA_OS_ROOT", "/opt/greia-os")).resolve(strict=False)
    from .installed_root import INSTALLED_APPLICATION_ROOT, is_installed_root

    if is_installed_root(os_root) and INSTALLED_APPLICATION_ROOT.exists():
        return Path("/run/greia-os/storage")
    base = Path(tempfile.gettempdir()) / f"greia-storage-{os.getuid()}"
    if os.name == "posix" and len(os.fsencode(base / ("0" * 32) / "storage.sock")) >= 100:
        return Path("/tmp") / f"g-s-{os.getuid()}"
    return base
