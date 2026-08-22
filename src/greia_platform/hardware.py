from __future__ import annotations

import json
import os
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


class HardwareSettingsError(ValueError):
    """Raised when a requested hardware preference is outside platform policy."""


@dataclass(frozen=True, slots=True)
class DisplayMode:
    width: int
    height: int
    refresh_hz: float | None = None
    preferred: bool = False
    current: bool = False

    @property
    def mode_id(self) -> str:
        return f"{self.width}x{self.height}"

    def as_json_dict(self) -> dict[str, object]:
        return {
            "id": self.mode_id,
            "width": self.width,
            "height": self.height,
            "refresh_hz": self.refresh_hz,
            "preferred": self.preferred,
            "current": self.current,
        }


@dataclass(frozen=True, slots=True)
class HardwareDefaults:
    schema_version: int
    touchpad_tap: bool
    touchpad_speed: float
    mouse_speed: float
    natural_scrolling: bool
    resolution: str
    keyboard_layout: str
    minimum_speed: float
    maximum_speed: float
    mic_gain: float = 2.0
    minimum_mic_gain: float = 0.5
    maximum_mic_gain: float = 4.0

    @classmethod
    def default_safe(cls) -> "HardwareDefaults":
        """Built-in immutable fallback policy for hardware settings."""
        return cls(
            schema_version=1,
            touchpad_tap=True,
            touchpad_speed=0.35,
            mouse_speed=0.0,
            natural_scrolling=False,
            resolution="auto",
            keyboard_layout="us",
            minimum_speed=-1.0,
            maximum_speed=1.0,
            mic_gain=2.0,
            minimum_mic_gain=0.5,
            maximum_mic_gain=4.0,
        )

    @classmethod
    def load(cls, path: Path) -> "HardwareDefaults":
        if not path.is_file() or path.stat().st_size == 0:
            return cls.default_safe()
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError):
            return cls.default_safe()
        defaults = data.get("defaults")
        limits = data.get("limits")
        if not isinstance(defaults, dict) or not isinstance(limits, dict):
            return cls.default_safe()
        try:
            loaded = cls(
                schema_version=int(data.get("schema_version", 1)),
                touchpad_tap=_strict_bool(defaults.get("touchpad_tap", True), "touchpad_tap"),
                touchpad_speed=float(defaults.get("touchpad_speed", 0.35)),
                mouse_speed=float(defaults.get("mouse_speed", 0.0)),
                natural_scrolling=_strict_bool(
                    defaults.get("natural_scrolling", False), "natural_scrolling"
                ),
                resolution=str(defaults.get("resolution", "auto")),
                # Older target payloads predate the keyboard_layout setting;
                # default it to "us" so installs still work against them.
                keyboard_layout=str(defaults.get("keyboard_layout", "us")),
                minimum_speed=float(limits.get("minimum_speed", -1.0)),
                maximum_speed=float(limits.get("maximum_speed", 1.0)),
                mic_gain=float(defaults.get("mic_gain", 2.0)),
                minimum_mic_gain=float(limits.get("minimum_mic_gain", 0.5)),
                maximum_mic_gain=float(limits.get("maximum_mic_gain", 4.0)),
            )
        except (KeyError, TypeError, ValueError):
            return cls.default_safe()
        if loaded.schema_version != 1:
            return cls.default_safe()
        try:
            loaded.validate_keyboard_layout(loaded.keyboard_layout)
        except HardwareSettingsError:
            loaded = cls(
                schema_version=loaded.schema_version,
                touchpad_tap=loaded.touchpad_tap,
                touchpad_speed=loaded.touchpad_speed,
                mouse_speed=loaded.mouse_speed,
                natural_scrolling=loaded.natural_scrolling,
                resolution=loaded.resolution,
                keyboard_layout="us",
                minimum_speed=loaded.minimum_speed,
                maximum_speed=loaded.maximum_speed,
                mic_gain=loaded.mic_gain,
                minimum_mic_gain=loaded.minimum_mic_gain,
                maximum_mic_gain=loaded.maximum_mic_gain,
            )
        if loaded.minimum_speed < -1.0 or loaded.maximum_speed > 1.0 or loaded.minimum_speed >= loaded.maximum_speed:
            return cls.default_safe()
        if loaded.minimum_mic_gain <= 0.0 or loaded.minimum_mic_gain >= loaded.maximum_mic_gain:
            return cls.default_safe()
        return loaded

    def validate_speed(self, value: float, name: str) -> float:
        value = round(float(value), 2)
        if not self.minimum_speed <= value <= self.maximum_speed:
            raise HardwareSettingsError(
                f"{name} must be between {self.minimum_speed} and {self.maximum_speed}"
            )
        return value

    def validate_mic_gain(self, value: float) -> float:
        value = round(float(value), 2)
        if not self.minimum_mic_gain <= value <= self.maximum_mic_gain:
            raise HardwareSettingsError(
                f"mic_gain must be between {self.minimum_mic_gain} and {self.maximum_mic_gain}"
            )
        return value

    def validate_keyboard_layout(self, value: str) -> str:
        from .keyboard_layout import layout_by_id

        try:
            layout_by_id(value)
        except LookupError as exc:
            raise HardwareSettingsError(f"unsupported keyboard layout: {value}") from exc
        return value


@dataclass(frozen=True, slots=True)
class HardwareSettings:
    schema_version: int
    touchpad_tap: bool
    touchpad_speed: float
    mouse_speed: float
    natural_scrolling: bool
    resolution: str
    keyboard_layout: str
    mic_gain: float = 2.0

    def as_json_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class HardwareApplyStatus:
    settings: HardwareSettings
    applied: bool
    display_output: str | None
    display_modes: tuple[DisplayMode, ...]
    message: str

    def as_json_dict(self) -> dict[str, object]:
        return {
            "settings": self.settings.as_json_dict(),
            "applied": self.applied,
            "display_output": self.display_output,
            "display_modes": [mode.as_json_dict() for mode in self.display_modes],
            "message": self.message,
        }


class HardwareSettingsStore:
    """Bounded parent-owned desired state for input and display behavior."""

    SETTINGS_NAME = "settings.json"

    def __init__(self, defaults: HardwareDefaults, state_dir: Path):
        self.defaults = defaults
        self.state_dir = state_dir.resolve()

    @classmethod
    def load(cls, defaults_path: Path, state_dir: Path) -> "HardwareSettingsStore":
        return cls(HardwareDefaults.load(defaults_path), state_dir)

    @property
    def settings_path(self) -> Path:
        return self.state_dir / self.SETTINGS_NAME

    def default_settings(self) -> HardwareSettings:
        return HardwareSettings(
            schema_version=self.defaults.schema_version,
            touchpad_tap=self.defaults.touchpad_tap,
            touchpad_speed=self.defaults.touchpad_speed,
            mouse_speed=self.defaults.mouse_speed,
            natural_scrolling=self.defaults.natural_scrolling,
            resolution=self.defaults.resolution,
            keyboard_layout=self.defaults.keyboard_layout,
            mic_gain=self.defaults.mic_gain,
        )

    def read(self) -> HardwareSettings:
        default = self.default_settings()
        try:
            raw = json.loads(self.settings_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return default
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return default
        if not isinstance(raw, dict):
            return default
        try:
            settings = HardwareSettings(
                schema_version=_strict_int(
                    raw.get("schema_version", self.defaults.schema_version),
                    "schema_version",
                ),
                touchpad_tap=_strict_bool(
                    raw.get("touchpad_tap", default.touchpad_tap), "touchpad_tap"
                ),
                touchpad_speed=self.defaults.validate_speed(
                    float(raw.get("touchpad_speed", default.touchpad_speed)),
                    "touchpad_speed",
                ),
                mouse_speed=self.defaults.validate_speed(
                    float(raw.get("mouse_speed", default.mouse_speed)), "mouse_speed"
                ),
                natural_scrolling=_strict_bool(
                    raw.get("natural_scrolling", default.natural_scrolling),
                    "natural_scrolling",
                ),
                resolution=str(raw.get("resolution", default.resolution)),
                keyboard_layout=str(
                    raw.get("keyboard_layout", default.keyboard_layout)
                ),
                mic_gain=self.defaults.validate_mic_gain(
                    float(raw.get("mic_gain", default.mic_gain))
                ),
            )
            self.validate(settings)
            return settings
        except (HardwareSettingsError, TypeError, ValueError):
            return default

    def update(
        self,
        *,
        touchpad_tap: bool | None = None,
        touchpad_speed: float | None = None,
        mouse_speed: float | None = None,
        natural_scrolling: bool | None = None,
        resolution: str | None = None,
        keyboard_layout: str | None = None,
        mic_gain: float | None = None,
        allowed_resolutions: Iterable[str] | None = None,
    ) -> HardwareSettings:
        current = self.read()
        updated = HardwareSettings(
            schema_version=self.defaults.schema_version,
            touchpad_tap=current.touchpad_tap if touchpad_tap is None else touchpad_tap,
            touchpad_speed=(
                current.touchpad_speed
                if touchpad_speed is None
                else self.defaults.validate_speed(touchpad_speed, "touchpad_speed")
            ),
            mouse_speed=(
                current.mouse_speed
                if mouse_speed is None
                else self.defaults.validate_speed(mouse_speed, "mouse_speed")
            ),
            natural_scrolling=(
                current.natural_scrolling
                if natural_scrolling is None
                else natural_scrolling
            ),
            resolution=current.resolution if resolution is None else resolution,
            keyboard_layout=(
                current.keyboard_layout
                if keyboard_layout is None
                else self.defaults.validate_keyboard_layout(keyboard_layout)
            ),
            mic_gain=(
                current.mic_gain
                if mic_gain is None
                else self.defaults.validate_mic_gain(mic_gain)
            ),
        )
        self.validate(updated, allowed_resolutions=allowed_resolutions)
        self._write(updated)
        return updated

    def replace(
        self,
        settings: HardwareSettings,
        *,
        allowed_resolutions: Iterable[str] | None = None,
    ) -> HardwareSettings:
        self.validate(settings, allowed_resolutions=allowed_resolutions)
        self._write(settings)
        return settings

    def reset(self) -> HardwareSettings:
        try:
            self.settings_path.unlink()
        except FileNotFoundError:
            pass
        return self.default_settings()

    def validate(
        self,
        settings: HardwareSettings,
        *,
        allowed_resolutions: Iterable[str] | None = None,
    ) -> None:
        if settings.schema_version != self.defaults.schema_version:
            raise HardwareSettingsError("hardware settings schema does not match platform")
        if not isinstance(settings.touchpad_tap, bool):
            raise HardwareSettingsError("touchpad_tap must be boolean")
        if not isinstance(settings.natural_scrolling, bool):
            raise HardwareSettingsError("natural_scrolling must be boolean")
        self.defaults.validate_speed(settings.touchpad_speed, "touchpad_speed")
        self.defaults.validate_speed(settings.mouse_speed, "mouse_speed")
        _validate_resolution_id(settings.resolution)
        self.defaults.validate_keyboard_layout(settings.keyboard_layout)
        self.defaults.validate_mic_gain(settings.mic_gain)
        if allowed_resolutions is not None:
            allowed = {"auto", *allowed_resolutions}
            if settings.resolution not in allowed:
                raise HardwareSettingsError("requested resolution is not supported by this display")

    def version_token(self) -> int:
        try:
            return self.settings_path.stat().st_mtime_ns
        except FileNotFoundError:
            return 0

    def _write(self, settings: HardwareSettings) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(
            settings.as_json_dict(), sort_keys=True, separators=(",", ":")
        ) + "\n"
        _atomic_write_text(self.settings_path, payload, mode=0o640)


def read_apply_status(path: Path, fallback: HardwareSettings) -> HardwareApplyStatus:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, UnicodeDecodeError, json.JSONDecodeError):
        return HardwareApplyStatus(
            settings=fallback,
            applied=False,
            display_output=None,
            display_modes=(),
            message="Hardware session has not reported yet.",
        )
    if not isinstance(raw, dict):
        raise HardwareSettingsError("hardware status must be an object")
    modes: list[DisplayMode] = []
    raw_modes = raw.get("display_modes", [])
    if isinstance(raw_modes, list):
        for raw_mode in raw_modes:
            if not isinstance(raw_mode, dict):
                continue
            try:
                modes.append(
                    DisplayMode(
                        width=int(raw_mode["width"]),
                        height=int(raw_mode["height"]),
                        refresh_hz=(
                            None
                            if raw_mode.get("refresh_hz") is None
                            else float(raw_mode["refresh_hz"])
                        ),
                        preferred=bool(raw_mode.get("preferred", False)),
                        current=bool(raw_mode.get("current", False)),
                    )
                )
            except (KeyError, TypeError, ValueError):
                continue
    return HardwareApplyStatus(
        settings=fallback,
        applied=bool(raw.get("applied", False)),
        display_output=(
            str(raw["display_output"]) if raw.get("display_output") else None
        ),
        display_modes=tuple(modes),
        message=str(raw.get("message", "")),
    )


def _strict_bool(value: object, name: str) -> bool:
    if not isinstance(value, bool):
        raise HardwareSettingsError(f"{name} must be boolean")
    return value


def _strict_int(value: object, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise HardwareSettingsError(f"{name} must be integer")
    return value


def _validate_resolution_id(value: str) -> None:
    if value == "auto":
        return
    parts = value.lower().split("x")
    if len(parts) != 2 or not all(part.isdigit() for part in parts):
        raise HardwareSettingsError("resolution must be 'auto' or WIDTHxHEIGHT")
    width, height = (int(part) for part in parts)
    if width < 320 or height < 240 or width > 7680 or height > 4320:
        raise HardwareSettingsError("resolution is outside the supported safety range")


def _atomic_write_text(path: Path, payload: str, *, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, mode)
        temporary.replace(path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
