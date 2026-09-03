from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .display_metrics import DisplayMetrics
from .hardware import DisplayMode


@dataclass(frozen=True, slots=True)
class DisplayState:
    """Backend-neutral display presence plus bounded physical facts.

    ``metrics`` carries the current-mode pixel/physical facts (or ``None``
    when there is nothing to describe). Product suitability
    (:class:`DisplayPolicy` / ``DisplaySuitability``) is deliberately *not*
    part of this state: policy thresholds live above HAL so product floors
    can vary without changing the hardware boundary. Likewise, detailed
    pointer capabilities live in the status layer via
    ``PointerSettingsController``; :class:`InputState` stays presence-only.
    ``metrics`` defaults to ``None`` so older constructors and backends
    that have not been migrated (e.g. the provisional legacy-X adapter,
    owned by another task) keep working unchanged.
    """

    available: bool
    modes: tuple[DisplayMode, ...] = ()
    backend: str = "unknown"
    metrics: DisplayMetrics | None = None


@dataclass(frozen=True, slots=True)
class InputState:
    pointer: bool
    keyboard: bool
    touch: bool = False
    backend: str = "unknown"
    controller: bool = False


@dataclass(frozen=True, slots=True)
class AudioState:
    basic_output: bool
    backend: str = "unknown"


@dataclass(frozen=True, slots=True)
class RemovableMediaState:
    service_available: bool
    backend: str = "unknown"


@dataclass(frozen=True, slots=True)
class NetworkState:
    service_available: bool
    backend: str = "unknown"


@dataclass(frozen=True, slots=True)
class PowerState:
    controlled_shutdown: bool
    backend: str = "unknown"


class DisplayHAL(Protocol):
    def probe(self) -> DisplayState: ...


class InputHAL(Protocol):
    def probe(self) -> InputState: ...


class ControllerPresenceProbe(Protocol):
    """Narrow host-side probe for controller/joystick presence."""

    def available(self) -> bool: ...


class AudioHAL(Protocol):
    def probe(self) -> AudioState: ...


class RemovableMediaHAL(Protocol):
    def probe(self) -> RemovableMediaState: ...


class NetworkHAL(Protocol):
    def probe(self) -> NetworkState: ...


class PowerHAL(Protocol):
    def probe(self) -> PowerState: ...


@dataclass(frozen=True, slots=True)
class GreiaHAL:
    """Typed hardware boundary below Greia semantic capabilities.

    Current backends are intentionally provisional. R7 replaces the legacy-X
    display/input implementations and R8 adds Pi board adapters without changing
    Activity, storage, session, progression, or semantic input contracts.
    """

    display: DisplayHAL
    input: InputHAL
    audio: AudioHAL
    removable_media: RemovableMediaHAL
    network: NetworkHAL
    power: PowerHAL


@dataclass(frozen=True, slots=True)
class LinuxControllerPresenceProbe:
    """Conservative Linux presence probe without opening controller devices.

    This establishes only that the host exposes a conventional joystick/gamepad
    node. Runtime/session input authority remains a separate R7 concern; this
    class never grants an Activity raw `/dev/input` access.
    """

    input_root: Path = Path("/dev/input")

    def available(self) -> bool:
        try:
            entries = tuple(self.input_root.iterdir())
        except OSError:
            return False
        for entry in entries:
            name = entry.name
            if name.startswith("js") and name[2:].isdigit():
                return True
        by_id = self.input_root / "by-id"
        try:
            return any(
                item.name.endswith("-event-joystick")
                for item in by_id.iterdir()
            )
        except OSError:
            return False


@dataclass(frozen=True, slots=True)
class LinuxAudioHAL:
    device_root: Path = Path("/dev/snd")

    def probe(self) -> AudioState:
        return AudioState(self.device_root.is_dir(), backend="linux-alsa-device")


@dataclass(frozen=True, slots=True)
class LinuxRemovableMediaHAL:
    media_root: Path = Path("/media/greia")

    def probe(self) -> RemovableMediaState:
        # This capability means the Greia removable-media service/mount root is
        # available, not that media happens to be inserted at this instant.
        return RemovableMediaState(self.media_root.is_dir(), backend="greia-media-root")


@dataclass(frozen=True, slots=True)
class LinuxNetworkHAL:
    sys_class_net: Path = Path("/sys/class/net")

    def probe(self) -> NetworkState:
        try:
            interfaces = tuple(
                entry.name
                for entry in self.sys_class_net.iterdir()
                if entry.name != "lo"
            )
        except OSError:
            interfaces = ()
        return NetworkState(bool(interfaces), backend="linux-netdev")


@dataclass(frozen=True, slots=True)
class SystemdPowerHAL:
    systemd_runtime: Path = Path("/run/systemd/system")

    def probe(self) -> PowerState:
        return PowerState(self.systemd_runtime.is_dir(), backend="systemd")


@dataclass(frozen=True, slots=True)
class StaticDisplayHAL:
    state: DisplayState

    def probe(self) -> DisplayState:
        return self.state


@dataclass(frozen=True, slots=True)
class StaticInputHAL:
    state: InputState

    def probe(self) -> InputState:
        return self.state


@dataclass(frozen=True, slots=True)
class StaticAudioHAL:
    state: AudioState

    def probe(self) -> AudioState:
        return self.state


@dataclass(frozen=True, slots=True)
class StaticRemovableMediaHAL:
    state: RemovableMediaState

    def probe(self) -> RemovableMediaState:
        return self.state


@dataclass(frozen=True, slots=True)
class StaticNetworkHAL:
    state: NetworkState

    def probe(self) -> NetworkState:
        return self.state


@dataclass(frozen=True, slots=True)
class StaticPowerHAL:
    state: PowerState

    def probe(self) -> PowerState:
        return self.state
