"""Typed synthetic-device configuration for the Greia Activity Simulator."""

from __future__ import annotations

import os
from dataclasses import dataclass


SIMULATOR_CAPABILITIES = frozenset(
    {
        "audio.basic",
        "controller",
        "display",
        "keyboard",
        "network",
        "pointer",
        "power.controlled_shutdown",
        "removable_media",
        "touch",
    }
)

DEFAULT_CAPABILITIES = frozenset(
    {
        "audio.basic",
        "display",
        "keyboard",
        "network",
        "pointer",
        "power.controlled_shutdown",
        "removable_media",
    }
)

DEVICE_PRESETS: dict[str, tuple[int, int]] = {
    "Acer / low-resource 1024x600": (1024, 600),
    "HD 1280x720": (1280, 720),
    "Tablet 1280x800": (1280, 800),
    "Laptop 1366x768": (1366, 768),
    "Full HD 1920x1080": (1920, 1080),
}


@dataclass(frozen=True, slots=True)
class SimulatedDeviceProfile:
    """One synthetic Greia device seen through the normal HAL capability seam.

    Geometry is deliberately device/model agnostic: the simulator records an
    exact viewport plus semantic capabilities. Greia layout/runtime code then
    consumes those facts exactly as it consumes real HAL facts.
    """

    width: int = 1024
    height: int = 600
    capabilities: frozenset[str] = DEFAULT_CAPABILITIES

    def __post_init__(self) -> None:
        if not 320 <= int(self.width) <= 7680:
            raise ValueError("simulated display width must be within 320..7680")
        if not 240 <= int(self.height) <= 4320:
            raise ValueError("simulated display height must be within 240..4320")
        capabilities = frozenset(self.capabilities)
        unknown = capabilities - SIMULATOR_CAPABILITIES
        if unknown:
            raise ValueError(
                "unknown simulator capabilities: " + ", ".join(sorted(unknown))
            )
        if "display" not in capabilities:
            raise ValueError("the Activity Simulator requires the display capability")
        object.__setattr__(self, "capabilities", capabilities)

    @property
    def size(self) -> tuple[int, int]:
        return (int(self.width), int(self.height))

    @property
    def viewport(self) -> str:
        return f"{self.width}x{self.height}"

    @classmethod
    def from_environment(cls) -> "SimulatedDeviceProfile":
        width, height = parse_viewport(
            os.environ.get("GREIA_SIMULATOR_VIEWPORT", "1024x600")
        )
        raw = os.environ.get("GREIA_SIMULATOR_CAPABILITIES")
        if raw is None:
            capabilities = DEFAULT_CAPABILITIES
        else:
            capabilities = frozenset(
                item.strip() for item in raw.split(",") if item.strip()
            )
        return cls(width=width, height=height, capabilities=capabilities)

    def to_hal(self):
        """Build the real GreiaHAL interface from synthetic capability facts."""

        from greia_platform.hal import (
            AudioState,
            DisplayState,
            GreiaHAL,
            InputState,
            NetworkState,
            PowerState,
            RemovableMediaState,
            StaticAudioHAL,
            StaticDisplayHAL,
            StaticInputHAL,
            StaticNetworkHAL,
            StaticPowerHAL,
            StaticRemovableMediaHAL,
        )
        from greia_platform.hardware import DisplayMode

        capabilities = self.capabilities
        backend = "greia-simulator"
        return GreiaHAL(
            display=StaticDisplayHAL(
                DisplayState(
                    True,
                    modes=(
                        DisplayMode(
                            self.width,
                            self.height,
                            preferred=True,
                            current=True,
                        ),
                    ),
                    backend=backend,
                )
            ),
            input=StaticInputHAL(
                InputState(
                    pointer="pointer" in capabilities,
                    keyboard="keyboard" in capabilities,
                    touch="touch" in capabilities,
                    controller="controller" in capabilities,
                    backend=backend,
                )
            ),
            audio=StaticAudioHAL(
                AudioState("audio.basic" in capabilities, backend=backend)
            ),
            removable_media=StaticRemovableMediaHAL(
                RemovableMediaState("removable_media" in capabilities, backend=backend)
            ),
            network=StaticNetworkHAL(
                NetworkState("network" in capabilities, backend=backend)
            ),
            power=StaticPowerHAL(
                PowerState("power.controlled_shutdown" in capabilities, backend=backend)
            ),
        )


def parse_viewport(value: str) -> tuple[int, int]:
    """Parse a bounded ``WIDTHxHEIGHT`` simulator viewport."""

    if not isinstance(value, str):
        raise ValueError("simulator viewport must be text")
    left, separator, right = value.strip().lower().partition("x")
    if not separator or not left.isdigit() or not right.isdigit():
        raise ValueError("simulator viewport must use WIDTHxHEIGHT")
    width = int(left)
    height = int(right)
    if not 320 <= width <= 7680 or not 240 <= height <= 4320:
        raise ValueError("simulator viewport is outside supported development bounds")
    return width, height


__all__ = [
    "DEFAULT_CAPABILITIES",
    "DEVICE_PRESETS",
    "SIMULATOR_CAPABILITIES",
    "SimulatedDeviceProfile",
    "parse_viewport",
]
