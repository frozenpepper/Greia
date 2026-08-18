"""Profile-scoped, renderer-neutral child interface preferences.

Greia deliberately exposes a tiny semantic choice instead of arbitrary pixel
font sizes. Renderers combine this preference with live responsive geometry;
Activity authors do not maintain alternate layouts for the three choices.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import json
import os
from pathlib import Path
import tempfile


class UiPreferencesError(ValueError):
    """Raised when a child UI preference is outside Greia's bounded contract."""


class InterfaceSize(StrEnum):
    COMPACT = "compact"
    NORMAL = "normal"
    LARGE = "large"

    @property
    def scale(self) -> float:
        return {
            InterfaceSize.COMPACT: 0.90,
            InterfaceSize.NORMAL: 1.00,
            InterfaceSize.LARGE: 1.18,
        }[self]


@dataclass(frozen=True, slots=True)
class UiPreferences:
    schema_version: int = 1
    interface_size: InterfaceSize = InterfaceSize.NORMAL

    @property
    def scale(self) -> float:
        return self.interface_size.scale

    def scale_px(
        self,
        value: int | float,
        *,
        minimum: int = 1,
        maximum: int = 4096,
    ) -> int:
        if minimum < 1 or maximum < minimum:
            raise ValueError("invalid UI pixel bounds")
        scaled = int(round(float(value) * self.scale))
        return min(maximum, max(minimum, scaled))


class UiPreferencesStore:
    """Atomic bounded store colocated with a child profile's customization data."""

    FILE_NAME = "ui.json"
    MAX_FILE_BYTES = 4096

    def __init__(self, state_dir: Path):
        self.state_dir = state_dir.resolve()
        self.path = self.state_dir / self.FILE_NAME

    def read(self) -> UiPreferences:
        try:
            if self.path.stat().st_size > self.MAX_FILE_BYTES:
                return UiPreferences()
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, UnicodeDecodeError, json.JSONDecodeError):
            return UiPreferences()
        if not isinstance(raw, dict):
            return UiPreferences()
        try:
            schema_version = raw.get("schema_version", 1)
            size = raw.get("interface_size", InterfaceSize.NORMAL.value)
            if schema_version != 1:
                raise UiPreferencesError("unsupported UI preference schema")
            if not isinstance(size, str):
                raise UiPreferencesError("interface size must be text")
            return UiPreferences(1, InterfaceSize(size))
        except (UiPreferencesError, ValueError):
            return UiPreferences()

    def set_interface_size(self, value: str | InterfaceSize) -> UiPreferences:
        try:
            size = value if isinstance(value, InterfaceSize) else InterfaceSize(str(value))
        except ValueError as exc:
            raise UiPreferencesError("unsupported interface size") from exc
        preferences = UiPreferences(1, size)
        self._write(preferences)
        return preferences

    def reset(self) -> None:
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass

    def version_token(self) -> int:
        try:
            return self.path.stat().st_mtime_ns
        except OSError:
            return 0

    def _write(self, preferences: UiPreferences) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(
            {
                "schema_version": preferences.schema_version,
                "interface_size": preferences.interface_size.value,
            },
            sort_keys=True,
            separators=(",", ":"),
        ) + "\n"
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{self.path.name}.", dir=self.state_dir
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temporary, 0o660)
            temporary.replace(self.path)
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise


__all__ = [
    "InterfaceSize",
    "UiPreferences",
    "UiPreferencesError",
    "UiPreferencesStore",
]
