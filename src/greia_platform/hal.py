from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .hardware import DisplayMode


@dataclass(frozen=True, slots=True)
class DisplayState:
    available: bool
    modes: tuple[DisplayMode, ...] = ()
    backend: str = "unknown"


@dataclass(frozen=True, slots=True)
class InputState:
    pointer: bool
    keyboard: bool
    touch: bool = False
    backend: str = "unknown"


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
    Activity, storage, session, or progression contracts.
    """

    display: DisplayHAL
    input: InputHAL
    audio: AudioHAL
    removable_media: RemovableMediaHAL
    network: NetworkHAL
    power: PowerHAL


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
