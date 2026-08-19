"""Typed synthetic-device facts for the Greia Activity Simulator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


# This is a HAL implementation map, not an independent allowed-capability
# vocabulary. The control plane derives its choices from RuntimeCatalogue and
# refuses to start when canonical Greia gains a capability this HAL cannot map.
HAL_SIMULATABLE_CAPABILITIES = frozenset(
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

# Geometry conveniences only. They deliberately do not claim machine model,
# architecture, touch hardware or performance/resource emulation.
VIEWPORT_PRESETS: dict[str, tuple[int, int]] = {
    "Reference 1024x600": (1024, 600),
    "1280x720": (1280, 720),
    "1280x800": (1280, 800),
    "1366x768": (1366, 768),
    "1920x1080": (1920, 1080),
}


def canonical_capability_choices(allowed_capabilities: Iterable[str]) -> tuple[str, ...]:
    """Return the canonical runtime vocabulary after checking HAL coverage."""

    allowed = frozenset(allowed_capabilities)
    unsupported = allowed - HAL_SIMULATABLE_CAPABILITIES
    if unsupported:
        raise ValueError(
            "simulator HAL does not map canonical Greia capabilities: "
            + ", ".join(sorted(unsupported))
        )
    if "display" not in allowed:
        raise ValueError("canonical Greia runtime must expose the display capability")
    return tuple(sorted(allowed))


@dataclass(frozen=True, slots=True)
class SimulatedDeviceProfile:
    """One synthetic device observation supplied through the normal Greia HAL."""

    width: int = 1024
    height: int = 600
    capabilities: frozenset[str] = DEFAULT_CAPABILITIES

    def __post_init__(self) -> None:
        if not 320 <= int(self.width) <= 7680:
            raise ValueError("simulated display width must be within 320..7680")
        if not 240 <= int(self.height) <= 4320:
            raise ValueError("simulated display height must be within 240..4320")
        capabilities = frozenset(self.capabilities)
        unsupported = capabilities - HAL_SIMULATABLE_CAPABILITIES
        if unsupported:
            raise ValueError(
                "simulator HAL cannot represent capabilities: "
                + ", ".join(sorted(unsupported))
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
    "HAL_SIMULATABLE_CAPABILITIES",
    "VIEWPORT_PRESETS",
    "SimulatedDeviceProfile",
    "canonical_capability_choices",
    "parse_viewport",
]
