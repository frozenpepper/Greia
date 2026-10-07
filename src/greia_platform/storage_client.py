from __future__ import annotations

import json
import os
import socket
from dataclasses import dataclass
from pathlib import Path

from .storage_protocol import StorageProtocolError, receive_frame, send_frame


class StorageClientError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class StandaloneStorageClient:
    """Ephemeral file-backed storage client for standalone direct execution."""

    root: Path

    def __post_init__(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "files").mkdir(parents=True, exist_ok=True)

    @property
    def _kv_path(self) -> Path:
        return self.root / "kv.json"

    @property
    def _files_root(self) -> Path:
        return self.root / "files"

    def _read_kv(self) -> dict[str, object]:
        if not self._kv_path.is_file():
            return {}
        try:
            return json.loads(self._kv_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _write_kv(self, data: dict[str, object]) -> None:
        self._kv_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def kv_get(self, key: str, default: object = None) -> object:
        return self._read_kv().get(key, default)

    def kv_set(self, key: str, value: object) -> None:
        try:
            json.dumps(
                value,
                ensure_ascii=False,
                separators=(",", ":"),
                allow_nan=False,
            )
        except (TypeError, ValueError) as exc:
            raise StorageClientError("storage value is not portable JSON") from exc
        data = self._read_kv()
        data[key] = value
        self._write_kv(data)

    def kv_delete(self, key: str) -> bool:
        data = self._read_kv()
        if key in data:
            del data[key]
            self._write_kv(data)
            return True
        return False

    def kv_list(self, prefix: str | None = None) -> tuple[str, ...]:
        keys = list(self._read_kv().keys())
        if prefix:
            keys = [k for k in keys if k.startswith(prefix)]
        return tuple(sorted(keys))

    def file_read(self, name: str) -> bytes:
        path = self._files_root / name
        if not path.is_file():
            raise StorageClientError(f"file not found: {name}")
        return path.read_bytes()

    def file_write_atomic(self, name: str, payload: bytes) -> None:
        if not isinstance(payload, (bytes, bytearray, memoryview)):
            raise StorageClientError("private file payload must be bytes")
        path = self._files_root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_name(f".{path.name}.tmp")
        temp.write_bytes(bytes(payload))
        temp.replace(path)

    def file_delete(self, name: str) -> bool:
        path = self._files_root / name
        if path.is_file():
            path.unlink()
            return True
        return False

    def file_list(self, prefix: str | None = None) -> tuple[str, ...]:
        if not self._files_root.exists():
            return ()
        names = [p.name for p in self._files_root.iterdir() if p.is_file()]
        if prefix:
            names = [n for n in names if n.startswith(prefix)]
        return tuple(sorted(names))

    def info(self) -> dict[str, object]:
        return {"standalone": True, "root": str(self.root)}

    def checkpoint(self) -> str:
        return "standalone-checkpoint"


@dataclass(frozen=True, slots=True)
class ActivityStorageClient:
    """Runtime-neutral logical storage client for one Activity launch."""

    socket_path: Path
    session_token: str
    max_payload_bytes: int = 32 * 1024 * 1024

    @classmethod
    def from_environment(cls) -> "ActivityStorageClient | StandaloneStorageClient":
        raw_socket = os.environ.get("GREIA_STORAGE_SOCKET", "").strip()
        token = os.environ.get("GREIA_STORAGE_TOKEN", "").strip()
        if not raw_socket or not token:
            standalone_dir = os.environ.get(
                "GREIA_STANDALONE_STORAGE_DIR",
                str(Path.home() / ".greia-simulator" / "standalone-storage"),
            )
            return StandaloneStorageClient(Path(standalone_dir))
        return cls(Path(raw_socket), token)

    def kv_get(self, key: str, default: object = None) -> object:
        header, payload = self._request("kv.get", key=key)
        if header.get("found") is False:
            return default
        try:
            return json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise StorageClientError("storage broker returned invalid JSON value") from exc

    def kv_set(self, key: str, value: object) -> None:
        try:
            payload = json.dumps(
                value,
                ensure_ascii=False,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise StorageClientError("storage value is not portable JSON") from exc
        self._request("kv.set", payload=payload, key=key)

    def kv_delete(self, key: str) -> bool:
        header, _ = self._request("kv.delete", key=key)
        return bool(header.get("deleted"))

    def kv_list(self, prefix: str | None = None) -> tuple[str, ...]:
        _, payload = self._request("kv.list", prefix=prefix)
        return tuple(_decode_string_list(payload, "KV key list"))

    def file_read(self, name: str) -> bytes:
        _, payload = self._request("files.read", name=name)
        return payload

    def file_write_atomic(self, name: str, payload: bytes) -> None:
        if not isinstance(payload, (bytes, bytearray, memoryview)):
            raise StorageClientError("private file payload must be bytes")
        self._request("files.write", payload=bytes(payload), name=name)

    def file_delete(self, name: str) -> bool:
        header, _ = self._request("files.delete", name=name)
        return bool(header.get("deleted"))

    def file_list(self, prefix: str | None = None) -> tuple[str, ...]:
        _, payload = self._request("files.list", prefix=prefix)
        return tuple(_decode_string_list(payload, "private file list"))

    def info(self) -> dict[str, object]:
        _, payload = self._request("info")
        try:
            raw = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise StorageClientError("storage broker returned invalid info") from exc
        if not isinstance(raw, dict):
            raise StorageClientError("storage info must be an object")
        return raw

    def checkpoint(self) -> str:
        header, _ = self._request("checkpoint")
        token = header.get("checkpoint_token")
        if not isinstance(token, str) or not token:
            raise StorageClientError("storage broker returned invalid checkpoint token")
        return token

    def creation_exchange(
        self, operation: str, **fields: object
    ) -> tuple[dict[str, object], bytes]:
        """Bounded SDK transport for only the two child-accessible operations."""
        if operation not in {"creations.publish_private", "creations.import_selected"}:
            raise StorageClientError("unsupported creations transfer operation")
        return self._request(operation, **fields)

    def _request(
        self,
        operation: str,
        *,
        payload: bytes = b"",
        **fields: object,
    ) -> tuple[dict[str, object], bytes]:
        header: dict[str, object] = {
            "op": operation,
            "session_token": self.session_token,
            **fields,
        }
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
                connection.connect(str(self.socket_path))
                send_frame(connection, header, payload)
                response, response_payload = receive_frame(
                    connection, max_payload_bytes=self.max_payload_bytes
                )
        except (OSError, StorageProtocolError) as exc:
            raise StorageClientError("cannot communicate with Greia storage broker") from exc
        if response.get("ok") is not True:
            code = response.get("error_code", "storage_error")
            message = response.get("message", "storage operation failed")
            raise StorageClientError(f"{code}: {message}")
        return response, response_payload


def _decode_string_list(payload: bytes, description: str) -> list[str]:
    try:
        raw = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StorageClientError(f"storage broker returned invalid {description}") from exc
    if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
        raise StorageClientError(f"storage broker returned invalid {description}")
    return raw
