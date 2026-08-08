from __future__ import annotations

from .hal import DisplayState, InputState
from .hardware_session import XSessionHardwareController


class LegacyXDisplayHAL:
    """Compatibility DisplayHAL backed by the provisional X session."""

    def __init__(self, controller: XSessionHardwareController | None = None):
        self._controller = controller or XSessionHardwareController()

    def probe(self) -> DisplayState:
        display = self._controller.probe_display()
        return DisplayState(
            available=display.output_name is not None,
            modes=display.modes,
            backend="legacy-x11",
        )


class LegacyXInputHAL:
    """Compatibility InputHAL backed by XInput during the R7 migration."""

    def __init__(self, controller: XSessionHardwareController | None = None):
        self._controller = controller or XSessionHardwareController()

    def probe(self) -> InputState:
        return InputState(
            pointer=self._controller.pointer_available(),
            keyboard=self._controller.keyboard_available(),
            backend="legacy-x11",
        )
