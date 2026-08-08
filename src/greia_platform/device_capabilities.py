from __future__ import annotations

import hashlib
import json
import platform
from dataclasses import dataclass
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Mapping, Protocol

from .hal import GreiaHAL


class DeviceCapabilityError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class DeviceCapabilitySnapshot:
    """Immutable trusted semantic capability observation for one launch decision."""

    schema_version: int
    capabilities: frozenset[str]
    source_id: str
    machine: str
    observed_at: str
    details: Mapping[str, object]
    token: str

    def has(self, capability: str) -> bool:
        return capability in self.capabilities

    @classmethod
    def create(
        cls,
        capabilities: frozenset[str] | set[str],
        *,
        source_id: str,
        machine: str | None = None,
        details: Mapping[str, object] | None = None,
        observed_at: str | None = None,
    ) -> "DeviceCapabilitySnapshot":
        normalized = frozenset(capabilities)
        if not _source_id(source_id):
            raise DeviceCapabilityError("capability source_id must be a bounded token")
        for capability in normalized:
            if not _capability_id(capability):
                raise DeviceCapabilityError(f"invalid semantic capability: {capability!r}")
        safe_details = dict(details or {})
        try:
            encoded = json.dumps(
                {
                    "capabilities": sorted(normalized),
                    "source_id": source_id,
                    "machine": machine or platform.machine() or "unknown",
                    "details": safe_details,
                },
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise DeviceCapabilityError("capability details must be portable JSON") from exc
        token = hashlib.sha256(encoded).hexdigest()
        return cls(
            schema_version=1,
            capabilities=normalized,
            source_id=source_id,
            machine=machine or platform.machine() or "unknown",
            observed_at=observed_at or _utc_now(),
            details=_deep_freeze(safe_details),
            token=token,
        )


class DeviceCapabilityProbe(Protocol):
    def probe(self) -> DeviceCapabilitySnapshot: ...


class HALDeviceCapabilityProbe:
    """Map typed HAL observations into stable Greia semantic capabilities."""

    def __init__(self, hal: GreiaHAL, *, source_id: str = "greia-hal"):
        self._hal = hal
        self._source_id = source_id

    def probe(self) -> DeviceCapabilitySnapshot:
        display = self._hal.display.probe()
        input_state = self._hal.input.probe()
        audio = self._hal.audio.probe()
        removable = self._hal.removable_media.probe()
        network = self._hal.network.probe()
        power = self._hal.power.probe()
        capabilities: set[str] = set()
        if display.available:
            capabilities.add("display")
        if input_state.pointer:
            capabilities.add("pointer")
        if input_state.keyboard:
            capabilities.add("keyboard")
        if input_state.touch:
            capabilities.add("touch")
        if audio.basic_output:
            capabilities.add("audio.basic")
        if removable.service_available:
            capabilities.add("removable_media")
        if network.service_available:
            capabilities.add("network")
        if power.controlled_shutdown:
            capabilities.add("power.controlled_shutdown")
        return DeviceCapabilitySnapshot.create(
            capabilities,
            source_id=self._source_id,
            details={
                "display": {
                    "available": display.available,
                    "backend": display.backend,
                    "modes": [mode.as_json_dict() for mode in display.modes],
                },
                "input": {
                    "pointer": input_state.pointer,
                    "keyboard": input_state.keyboard,
                    "touch": input_state.touch,
                    "backend": input_state.backend,
                },
                "audio": {
                    "basic_output": audio.basic_output,
                    "backend": audio.backend,
                },
                "removable_media": {
                    "service_available": removable.service_available,
                    "backend": removable.backend,
                },
                "network": {
                    "service_available": network.service_available,
                    "backend": network.backend,
                },
                "power": {
                    "controlled_shutdown": power.controlled_shutdown,
                    "backend": power.backend,
                },
            },
        )


@dataclass(frozen=True, slots=True)
class StaticDeviceCapabilityProbe:
    snapshot: DeviceCapabilitySnapshot

    def probe(self) -> DeviceCapabilitySnapshot:
        return self.snapshot


class DeviceCapabilityService:
    """Platform authority for current semantic hardware/service availability."""

    def __init__(self, probe: DeviceCapabilityProbe):
        self._probe = probe
        self._cached: DeviceCapabilitySnapshot | None = None

    def snapshot(self, *, refresh: bool = False) -> DeviceCapabilitySnapshot:
        if refresh or self._cached is None:
            candidate = self._probe.probe()
            if not isinstance(candidate, DeviceCapabilitySnapshot):
                raise DeviceCapabilityError("capability probe returned an invalid snapshot")
            self._cached = candidate
        return self._cached

    @classmethod
    def static(
        cls,
        capabilities: frozenset[str] | set[str],
        *,
        source_id: str = "test-static",
    ) -> "DeviceCapabilityService":
        return cls(
            StaticDeviceCapabilityProbe(
                DeviceCapabilitySnapshot.create(
                    capabilities,
                    source_id=source_id,
                    machine="test",
                    observed_at="1970-01-01T00:00:00Z",
                )
            )
        )


def _source_id(value: str) -> bool:
    if not isinstance(value, str) or not value or len(value) > 64:
        return False
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")
    return value[0].isalnum() and value[-1].isalnum() and all(c in allowed for c in value)


def _deep_freeze(value: object) -> object:
    if isinstance(value, dict):
        return MappingProxyType({str(key): _deep_freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_deep_freeze(item) for item in value)
    return value


def _capability_id(value: str) -> bool:
    if not isinstance(value, str) or not value or len(value) > 128:
        return False
    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789._-")
    return value[0].isalnum() and value[-1].isalnum() and all(c in allowed for c in value)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
