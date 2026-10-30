from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, replace
from enum import StrEnum
from pathlib import Path
from typing import Callable, IO, Protocol

try:
    import fcntl
except ImportError:  # pragma: no cover - non-POSIX developer hosts
    fcntl = None  # type: ignore[assignment]


class SystemControlError(ValueError):
    """Raised when a requested Greia system control is outside policy."""


class SystemControlAction(StrEnum):
    """Small platform-only vocabulary for physical system controls."""

    VOLUME_UP = "volume_up"
    VOLUME_DOWN = "volume_down"
    VOLUME_MUTE = "volume_mute"
    BRIGHTNESS_UP = "brightness_up"
    BRIGHTNESS_DOWN = "brightness_down"


@dataclass(frozen=True, slots=True)
class SystemControlSettings:
    schema_version: int = 1
    volume_percent: int = 70
    muted: bool = False
    brightness_percent: int = 100

    def as_json_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SystemControlApplyResult:
    applied: bool
    volume_available: bool
    brightness_available: bool
    brightness_backend: str | None
    messages: tuple[str, ...] = ()

    def as_json_dict(self) -> dict[str, object]:
        return {
            "applied": self.applied,
            "volume_available": self.volume_available,
            "brightness_available": self.brightness_available,
            "brightness_backend": self.brightness_backend,
            "messages": list(self.messages),
        }


class SystemControlBackend(Protocol):
    """Concrete host mechanics for Greia-owned output/backlight controls."""

    def apply(self, settings: SystemControlSettings) -> SystemControlApplyResult: ...


class SystemControlSettingsStore:
    """Atomic, inter-process-safe desired state shared by Parent and hotkeys."""

    SETTINGS_NAME = "system-controls.json"
    LOCK_NAME = ".system-controls.lock"

    def __init__(self, state_dir: Path):
        self.state_dir = state_dir.resolve()

    @property
    def settings_path(self) -> Path:
        return self.state_dir / self.SETTINGS_NAME

    @property
    def lock_path(self) -> Path:
        return self.state_dir / self.LOCK_NAME

    def read(self) -> SystemControlSettings:
        try:
            raw = json.loads(self.settings_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, UnicodeDecodeError, json.JSONDecodeError):
            return SystemControlSettings()
        if not isinstance(raw, dict):
            return SystemControlSettings()
        try:
            settings = SystemControlSettings(
                schema_version=_strict_int(raw.get("schema_version", 1), "schema_version"),
                volume_percent=_percent(raw.get("volume_percent", 70), "volume_percent"),
                muted=_strict_bool(raw.get("muted", False), "muted"),
                brightness_percent=_brightness_percent(
                    raw.get("brightness_percent", 100)
                ),
            )
            self.validate(settings)
            return settings
        except (SystemControlError, TypeError, ValueError):
            return SystemControlSettings()

    def mutate(
        self,
        mutation: Callable[[SystemControlSettings], SystemControlSettings],
    ) -> SystemControlSettings:
        """Apply one desired-state mutation under the shared writer lock."""

        self.state_dir.mkdir(parents=True, exist_ok=True)
        with self._open_lock() as lock_handle:
            self._lock(lock_handle)
            current = self.read()
            updated = mutation(current)
            if not isinstance(updated, SystemControlSettings):
                raise TypeError("system control mutation must return SystemControlSettings")
            self.validate(updated)
            self._write(updated)
            return updated

    def update(
        self,
        *,
        volume_percent: object | None = None,
        muted: object | None = None,
        brightness_percent: object | None = None,
    ) -> SystemControlSettings:
        def mutation(current: SystemControlSettings) -> SystemControlSettings:
            return SystemControlSettings(
                schema_version=1,
                volume_percent=(
                    current.volume_percent
                    if volume_percent is None
                    else _percent(volume_percent, "volume_percent")
                ),
                muted=(
                    current.muted if muted is None else _strict_bool(muted, "muted")
                ),
                brightness_percent=(
                    current.brightness_percent
                    if brightness_percent is None
                    else _brightness_percent(brightness_percent)
                ),
            )

        return self.mutate(mutation)

    def reset(self) -> SystemControlSettings:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        with self._open_lock() as lock_handle:
            self._lock(lock_handle)
            try:
                self.settings_path.unlink()
            except FileNotFoundError:
                pass
        return SystemControlSettings()

    @staticmethod
    def validate(settings: SystemControlSettings) -> None:
        if settings.schema_version != 1:
            raise SystemControlError("system control schema does not match platform")
        _percent(settings.volume_percent, "volume_percent")
        _strict_bool(settings.muted, "muted")
        _brightness_percent(settings.brightness_percent)

    def version_token(self) -> int:
        try:
            return self.settings_path.stat().st_mtime_ns
        except FileNotFoundError:
            return 0

    def _open_lock(self) -> IO[str]:
        # The release image creates this file as greiapanel:greiasettings 0660.
        # On developer/temp roots the first writer creates it; the setgid parent
        # directory supplies the shared group on the real appliance.
        fd = os.open(self.lock_path, os.O_RDWR | os.O_CREAT, 0o660)
        try:
            try:
                os.fchmod(fd, 0o660)
            except PermissionError:
                # A secondary writer need not own the already-correct shared lock.
                pass
            return os.fdopen(fd, "a+", encoding="utf-8")
        except Exception:
            os.close(fd)
            raise

    @staticmethod
    def _lock(lock_handle: IO[str]) -> None:
        if fcntl is None:
            return
        try:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
        except OSError as exc:
            raise SystemControlError("system control state lock failed") from exc

    def _write(self, settings: SystemControlSettings) -> None:
        payload = json.dumps(
            settings.as_json_dict(), sort_keys=True, separators=(",", ":")
        ) + "\n"
        temporary = self.settings_path.with_name(
            f".{self.settings_path.name}.{os.getpid()}.tmp"
        )
        try:
            with temporary.open("w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temporary, 0o664)
            temporary.replace(self.settings_path)
        finally:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass


class SystemControlService:
    """Single semantic authority used by Parent desired state and system keys."""

    VOLUME_STEP = 5
    BRIGHTNESS_STEP = 10

    def __init__(
        self,
        store: SystemControlSettingsStore,
        backend: SystemControlBackend,
    ) -> None:
        self.store = store
        self.backend = backend

    def apply_current(self) -> SystemControlApplyResult:
        return self.backend.apply(self.store.read())

    def handle_action(self, action: SystemControlAction) -> SystemControlApplyResult:
        def mutation(current: SystemControlSettings) -> SystemControlSettings:
            if action is SystemControlAction.VOLUME_UP:
                return replace(
                    current,
                    volume_percent=min(100, current.volume_percent + self.VOLUME_STEP),
                    muted=False,
                )
            if action is SystemControlAction.VOLUME_DOWN:
                return replace(
                    current,
                    volume_percent=max(0, current.volume_percent - self.VOLUME_STEP),
                    muted=False,
                )
            if action is SystemControlAction.VOLUME_MUTE:
                return replace(current, muted=not current.muted)
            if action is SystemControlAction.BRIGHTNESS_UP:
                return replace(
                    current,
                    brightness_percent=min(
                        100, current.brightness_percent + self.BRIGHTNESS_STEP
                    ),
                )
            if action is SystemControlAction.BRIGHTNESS_DOWN:
                return replace(
                    current,
                    brightness_percent=max(
                        5, current.brightness_percent - self.BRIGHTNESS_STEP
                    ),
                )
            raise SystemControlError(f"unsupported system control action: {action}")

        updated = self.store.mutate(mutation)
        return self.backend.apply(updated)


def _percent(value: object, name: str) -> int:
    value = _strict_int(value, name)
    if not 0 <= value <= 100:
        raise SystemControlError(f"{name} must be between 0 and 100")
    return value


def _brightness_percent(value: object) -> int:
    value = _strict_int(value, "brightness_percent")
    if not 5 <= value <= 100:
        raise SystemControlError("brightness_percent must be between 5 and 100")
    return value


def _strict_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise SystemControlError(f"{name} must be an integer")
    return value


def _strict_bool(value: object, name: str) -> bool:
    if not isinstance(value, bool):
        raise SystemControlError(f"{name} must be boolean")
    return value
