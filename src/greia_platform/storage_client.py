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
class ActivityStorageClient:
    """Runtime-neutral logical storage client for one Activity launch."""

    socket_path: Path
    session_token: str
    max_payload_bytes: int = 32 * 1024 * 1024

    @classmethod
    def from_environment(cls) -> "ActivityStorageClient":
        raw_socket = os.environ.get("GREIA_STORAGE_SOCKET", "").strip()
        token = os.environ.get("GREIA_STORAGE_TOKEN", "").strip()
        if not raw_socket or not token:
            raise StorageClientError("Activity was not launched with Greia storage")
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
