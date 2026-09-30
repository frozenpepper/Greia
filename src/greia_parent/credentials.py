from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


SCHEMA_VERSION = 1
MAX_PAIRED_DEVICES = 16
MAX_DEVICE_NAME_LENGTH = 64
TOKEN_BYTES = 32
MAX_STATE_BYTES = 64 * 1024


class ParentCredentialError(ValueError):
    """Persistent parent-device credential state is invalid or cannot be changed."""


@dataclass(frozen=True, slots=True)
class PairedDevice:
    """Public metadata for one independently revocable parent client."""

    device_id: str
    display_name: str
    created_at: str

    def public_dict(self) -> dict[str, str]:
        return {
            "device_id": self.device_id,
            "display_name": self.display_name,
            "created_at": self.created_at,
        }


@dataclass(frozen=True, slots=True)
class IssuedParentCredential:
    """A newly issued bearer credential. The raw token is returned only once."""

    device: PairedDevice
    token: str


@dataclass(frozen=True, slots=True)
class _CredentialRecord:
    device: PairedDevice
    token_sha256: str


class ParentDeviceCredentialStore:
    """Own per-device parent credentials without persisting raw bearer tokens."""

    def __init__(self, state_dir: Path):
        self.state_dir = state_dir.resolve()
        self.path = self.state_dir / "parent-devices.json"

    def list_devices(self) -> tuple[PairedDevice, ...]:
        return tuple(record.device for record in self._load())

    def issue(self, display_name: str) -> IssuedParentCredential:
        name = self._validated_display_name(display_name)
        records = list(self._load())
        if len(records) >= MAX_PAIRED_DEVICES:
            raise ParentCredentialError("paired-device limit reached")

        # Re-pairing an existing client replaces its own old records instead of
        # consuming another slot. The on-device panel re-pairs on every launch, so
        # without this the store filled itself to MAX_PAIRED_DEVICES and then
        # refused every parent password with "paired-device limit reached" - which
        # the panel could only report as the password being unavailable.
        records = [r for r in records if r.device.display_name != display_name]
        if len(records) >= MAX_PAIRED_DEVICES:
            raise ParentCredentialError("paired-device limit reached")

        token = secrets.token_urlsafe(TOKEN_BYTES)
        device = PairedDevice(
            device_id=secrets.token_urlsafe(12),
            display_name=name,
            created_at=datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z"),
        )
        records.append(
            _CredentialRecord(
                device=device,
                token_sha256=self._digest(token),
            )
        )
        self._write(records)
        return IssuedParentCredential(device=device, token=token)

    def authenticate(self, token: str) -> PairedDevice | None:
        if not isinstance(token, str) or not token or len(token) > 256:
            return None
        candidate = self._digest(token)
        for record in self._load():
            if hmac.compare_digest(candidate, record.token_sha256):
                return record.device
        return None

    def revoke(self, device_id: str) -> PairedDevice:
        if not isinstance(device_id, str) or not device_id or len(device_id) > 128:
            raise ParentCredentialError("invalid paired-device id")
        records = list(self._load())
        retained: list[_CredentialRecord] = []
        removed: PairedDevice | None = None
        for record in records:
            if record.device.device_id == device_id:
                removed = record.device
            else:
                retained.append(record)
        if removed is None:
            raise ParentCredentialError("paired device not found")
        self._write(retained)
        return removed

    def _load(self) -> tuple[_CredentialRecord, ...]:
        if not self.path.exists():
            return ()
        if self.path.is_symlink():
            raise ParentCredentialError("paired-device state must not be a symlink")
        try:
            stat = self.path.stat()
            if not self.path.is_file() or stat.st_size > MAX_STATE_BYTES:
                raise ParentCredentialError("paired-device state has invalid size/type")
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except ParentCredentialError:
            raise
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ParentCredentialError("invalid paired-device state") from exc

        if not isinstance(raw, dict) or raw.get("schema_version") != SCHEMA_VERSION:
            raise ParentCredentialError("unsupported paired-device state schema")
        items = raw.get("devices")
        if not isinstance(items, list) or len(items) > MAX_PAIRED_DEVICES:
            raise ParentCredentialError("invalid paired-device list")

        records: list[_CredentialRecord] = []
        seen_ids: set[str] = set()
        for item in items:
            if not isinstance(item, dict):
                raise ParentCredentialError("invalid paired-device record")
            device_id = item.get("device_id")
            display_name = item.get("display_name")
            created_at = item.get("created_at")
            token_sha256 = item.get("token_sha256")
            if (
                not isinstance(device_id, str)
                or not device_id
                or len(device_id) > 128
                or device_id in seen_ids
            ):
                raise ParentCredentialError("invalid paired-device id")
            name = self._validated_display_name(display_name)
            if not isinstance(created_at, str) or not created_at or len(created_at) > 64:
                raise ParentCredentialError("invalid paired-device timestamp")
            if (
                not isinstance(token_sha256, str)
                or len(token_sha256) != 64
                or any(character not in "0123456789abcdef" for character in token_sha256)
            ):
                raise ParentCredentialError("invalid paired-device credential digest")
            seen_ids.add(device_id)
            records.append(
                _CredentialRecord(
                    device=PairedDevice(
                        device_id=device_id,
                        display_name=name,
                        created_at=created_at,
                    ),
                    token_sha256=token_sha256,
                )
            )
        return tuple(records)

    def _write(self, records: list[_CredentialRecord]) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": SCHEMA_VERSION,
            "devices": [
                {
                    **record.device.public_dict(),
                    "token_sha256": record.token_sha256,
                }
                for record in records
            ],
        }
        encoded = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        ) + "\n"
        if len(encoded.encode("utf-8")) > MAX_STATE_BYTES:
            raise ParentCredentialError("paired-device state exceeds size limit")
        temporary = self.path.with_name(
            f".{self.path.name}.{os.getpid()}.{secrets.token_hex(4)}.tmp"
        )
        try:
            temporary.write_text(encoded, encoding="utf-8")
            os.chmod(temporary, 0o600)
            temporary.replace(self.path)
            os.chmod(self.path, 0o600)
        finally:
            temporary.unlink(missing_ok=True)

    @staticmethod
    def _validated_display_name(value: object) -> str:
        if not isinstance(value, str):
            raise ParentCredentialError("paired-device name must be text")
        name = value.strip()
        if not name or len(name) > MAX_DEVICE_NAME_LENGTH:
            raise ParentCredentialError("paired-device name must be 1-64 characters")
        if any(ord(character) < 32 for character in name):
            raise ParentCredentialError("paired-device name contains control characters")
        return name

    @staticmethod
    def _digest(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()
