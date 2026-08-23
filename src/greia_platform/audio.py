from __future__ import annotations

import json
import os
import tomllib
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol


class AudioSettingsError(ValueError):
    """Raised when a requested audio preference is outside Greia audio policy."""


class MicrophoneProcessingMode(StrEnum):
    OFF = "off"
    LIGHTWEIGHT = "lightweight"
    ADVANCED = "advanced"


@dataclass(frozen=True, slots=True)
class AudioDefaults:
    schema_version: int = 1
    microphone_processing_enabled: bool = True
    advanced_noise_reduction: bool = False

    @classmethod
    def load(cls, path: Path) -> "AudioDefaults":
        if not path.is_file() or path.stat().st_size == 0:
            return cls()
        try:
            document = tomllib.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
            return cls()
        defaults = document.get("defaults")
        if not isinstance(defaults, dict):
            return cls()
        try:
            loaded = cls(
                schema_version=_strict_int(document.get("schema_version", 1), "schema_version"),
                microphone_processing_enabled=_strict_bool(
                    defaults.get("microphone_processing_enabled", True),
                    "microphone_processing_enabled",
                ),
                advanced_noise_reduction=_strict_bool(
                    defaults.get("advanced_noise_reduction", False),
                    "advanced_noise_reduction",
                ),
            )
        except (AudioSettingsError, TypeError, ValueError):
            return cls()
        return loaded if loaded.schema_version == 1 else cls()


@dataclass(frozen=True, slots=True)
class AudioSettings:
    schema_version: int
    microphone_processing_enabled: bool
    advanced_noise_reduction: bool

    def as_json_dict(self) -> dict[str, object]:
        return asdict(self)


class AudioSettingsStore:
    """Persist the small parent-owned desired state for microphone processing."""

    SETTINGS_NAME = "audio-settings.json"

    def __init__(self, defaults: AudioDefaults, state_dir: Path):
        self.defaults = defaults
        self.state_dir = state_dir.resolve()

    @classmethod
    def load(cls, defaults_path: Path, state_dir: Path) -> "AudioSettingsStore":
        return cls(AudioDefaults.load(defaults_path), state_dir)

    @property
    def settings_path(self) -> Path:
        return self.state_dir / self.SETTINGS_NAME

    def default_settings(self) -> AudioSettings:
        return AudioSettings(
            schema_version=self.defaults.schema_version,
            microphone_processing_enabled=self.defaults.microphone_processing_enabled,
            advanced_noise_reduction=self.defaults.advanced_noise_reduction,
        )

    def read(self) -> AudioSettings:
        fallback = self.default_settings()
        try:
            raw = json.loads(self.settings_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, UnicodeDecodeError, json.JSONDecodeError):
            return fallback
        if not isinstance(raw, dict):
            return fallback
        try:
            settings = AudioSettings(
                schema_version=_strict_int(
                    raw.get("schema_version", self.defaults.schema_version),
                    "schema_version",
                ),
                microphone_processing_enabled=_strict_bool(
                    raw.get(
                        "microphone_processing_enabled",
                        fallback.microphone_processing_enabled,
                    ),
                    "microphone_processing_enabled",
                ),
                advanced_noise_reduction=_strict_bool(
                    raw.get(
                        "advanced_noise_reduction",
                        fallback.advanced_noise_reduction,
                    ),
                    "advanced_noise_reduction",
                ),
            )
            self.validate(settings)
            return settings
        except (AudioSettingsError, TypeError, ValueError):
            return fallback

    def update(
        self,
        *,
        microphone_processing_enabled: bool | None = None,
        advanced_noise_reduction: bool | None = None,
    ) -> AudioSettings:
        current = self.read()
        settings = AudioSettings(
            schema_version=self.defaults.schema_version,
            microphone_processing_enabled=(
                current.microphone_processing_enabled
                if microphone_processing_enabled is None
                else _strict_bool(
                    microphone_processing_enabled, "microphone_processing_enabled"
                )
            ),
            advanced_noise_reduction=(
                current.advanced_noise_reduction
                if advanced_noise_reduction is None
                else _strict_bool(
                    advanced_noise_reduction, "advanced_noise_reduction"
                )
            ),
        )
        self.validate(settings)
        self._write(settings)
        return settings

    def reset(self) -> AudioSettings:
        try:
            self.settings_path.unlink()
        except FileNotFoundError:
            pass
        return self.default_settings()

    def validate(self, settings: AudioSettings) -> None:
        if settings.schema_version != self.defaults.schema_version:
            raise AudioSettingsError("audio settings schema does not match platform")
        if not isinstance(settings.microphone_processing_enabled, bool):
            raise AudioSettingsError("microphone_processing_enabled must be boolean")
        if not isinstance(settings.advanced_noise_reduction, bool):
            raise AudioSettingsError("advanced_noise_reduction must be boolean")

    def _write(self, settings: AudioSettings) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(
            settings.as_json_dict(), sort_keys=True, separators=(",", ":")
        ) + "\n"
        _atomic_write_text(self.settings_path, payload, mode=0o664)


@dataclass(frozen=True, slots=True)
class AudioBackendStatus:
    """Facts exposed by a concrete host audio adapter.

    Availability describes installed backend support only. It is never a CPU
    benchmark result and never selects a mode on the parent's behalf.
    """

    backend_id: str
    raw_capture_device: str | None
    lightweight_capture_device: str | None
    advanced_capture_device: str | None = None

    @property
    def lightweight_available(self) -> bool:
        return bool(self.lightweight_capture_device)

    @property
    def advanced_available(self) -> bool:
        return bool(self.advanced_capture_device)


class AudioProcessingBackend(Protocol):
    def status(self) -> AudioBackendStatus: ...


@dataclass(frozen=True, slots=True)
class StaticAudioProcessingBackend:
    """Small injected backend for tests, simulators and explicit compositions."""

    state: AudioBackendStatus

    def status(self) -> AudioBackendStatus:
        return self.state


@dataclass(frozen=True, slots=True)
class AlsaAudioProcessingBackend:
    """Describe Greia-owned ALSA capture endpoints without benchmarking.

    Endpoint names are stable Greia logical PCMs. Whether they exist is a
    deployment/profile fact recorded by small marker files, not an automatic
    runtime performance decision.
    """

    status_dir: Path = Path("/run/greia-audio")
    raw_capture_device: str = "default"
    lightweight_capture_device: str = "greia_mic_light"
    advanced_capture_device: str = "greia_mic_advanced"

    def status(self) -> AudioBackendStatus:
        lightweight = (
            self.lightweight_capture_device
            if (self.status_dir / "lightweight-ready").is_file()
            else None
        )
        advanced = (
            self.advanced_capture_device
            if (self.status_dir / "advanced-ready").is_file()
            else None
        )
        return AudioBackendStatus(
            backend_id="alsa",
            raw_capture_device=self.raw_capture_device,
            lightweight_capture_device=lightweight,
            advanced_capture_device=advanced,
        )


@dataclass(frozen=True, slots=True)
class AudioSessionRoute:
    mode: MicrophoneProcessingMode
    capture_device: str | None
    fallback_reason: str | None = None

    def environment(self) -> tuple[tuple[str, str], ...]:
        values = [("GREIA_AUDIO_PROCESSING_MODE", self.mode.value)]
        if self.capture_device:
            values.append(("GREIA_AUDIO_CAPTURE_DEVICE", self.capture_device))
        return tuple(values)


class AudioService:
    """Resolve Parent audio policy into one runtime-neutral Activity mic route.

    Greia deliberately does not benchmark hardware or auto-promote processing.
    Lightweight processing is the desired default. Advanced processing is used
    only when a parent explicitly selects it and the injected backend advertises
    that concrete endpoint as available.
    """

    def __init__(
        self,
        store: AudioSettingsStore,
        backend: AudioProcessingBackend,
    ):
        self.store = store
        self.backend = backend

    @classmethod
    def load(
        cls,
        defaults_path: Path,
        state_dir: Path,
        *,
        backend: AudioProcessingBackend | None = None,
    ) -> "AudioService":
        return cls(
            AudioSettingsStore.load(defaults_path, state_dir),
            backend or AlsaAudioProcessingBackend(),
        )

    def settings(self) -> AudioSettings:
        return self.store.read()

    def route(self) -> AudioSessionRoute:
        settings = self.settings()
        status = self.backend.status()
        if not settings.microphone_processing_enabled:
            return AudioSessionRoute(
                MicrophoneProcessingMode.OFF,
                status.raw_capture_device,
            )
        if settings.advanced_noise_reduction:
            if status.advanced_available:
                return AudioSessionRoute(
                    MicrophoneProcessingMode.ADVANCED,
                    status.advanced_capture_device,
                )
            if status.lightweight_available:
                return AudioSessionRoute(
                    MicrophoneProcessingMode.LIGHTWEIGHT,
                    status.lightweight_capture_device,
                    fallback_reason="advanced_unavailable",
                )
        if status.lightweight_available:
            return AudioSessionRoute(
                MicrophoneProcessingMode.LIGHTWEIGHT,
                status.lightweight_capture_device,
            )
        return AudioSessionRoute(
            MicrophoneProcessingMode.OFF,
            status.raw_capture_device,
            fallback_reason="lightweight_unavailable",
        )

    def payload(self) -> dict[str, object]:
        settings = self.settings()
        status = self.backend.status()
        route = self.route()
        return {
            "desired": settings.as_json_dict(),
            "effective": {
                "microphone_processing_mode": route.mode.value,
                "capture_device": route.capture_device,
                "fallback_reason": route.fallback_reason,
            },
            "available": {
                "lightweight": status.lightweight_available,
                "advanced": status.advanced_available,
            },
            "backend": status.backend_id,
            "apply_scope": "next_microphone_open",
        }

    def update(
        self,
        *,
        microphone_processing_enabled: bool | None = None,
        advanced_noise_reduction: bool | None = None,
    ) -> dict[str, object]:
        if advanced_noise_reduction is True and not self.backend.status().advanced_available:
            raise AudioSettingsError(
                "advanced microphone noise reduction is not available on this Greia"
            )
        self.store.update(
            microphone_processing_enabled=microphone_processing_enabled,
            advanced_noise_reduction=advanced_noise_reduction,
        )
        return self.payload()

    def reset(self) -> dict[str, object]:
        self.store.reset()
        return self.payload()

    def session_environment(self) -> tuple[tuple[str, str], ...]:
        return self.route().environment()


def _strict_bool(value: object, name: str) -> bool:
    if not isinstance(value, bool):
        raise AudioSettingsError(f"{name} must be boolean")
    return value


def _strict_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise AudioSettingsError(f"{name} must be an integer")
    return value


def _atomic_write_text(path: Path, text: str, *, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_text(text, encoding="utf-8")
        os.chmod(temporary, mode)
        temporary.replace(path)
        os.chmod(path, mode)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
