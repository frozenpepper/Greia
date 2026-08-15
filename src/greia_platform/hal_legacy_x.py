from __future__ import annotations

import subprocess
from typing import Protocol, Sequence

from .hal import (
    ControllerPresenceProbe,
    DisplayState,
    InputState,
    LinuxControllerPresenceProbe,
)
from .hardware import HardwareSettings
from .hardware_session import ApplyResult, DisplayProbe


class CommandRunner(Protocol):
    def run(self, command: Sequence[str]) -> subprocess.CompletedProcess[str]: ...


class SubprocessRunner:
    def run(self, command: Sequence[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            list(command),
            check=False,
            shell=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )


class LegacyXHardwareSessionController:
    """Compatibility settings adapter for the current installed X session.

    This is the only R7 module that maps Greia's semantic HardwareSettings to
    xrandr/xinput commands. The generic watcher and HAL contracts stay backend
    neutral so a future direct/Wayland settings adapter can replace this class
    without changing parent policy or persisted settings.
    """

    backend_id = "legacy-x11"

    def __init__(self, runner: CommandRunner | None = None):
        self.runner = runner or SubprocessRunner()

    def topology_token(self) -> tuple[str, str]:
        display = self.runner.run(["xrandr", "--query"])
        pointers = self.runner.run(["xinput", "--list", "--short"])
        return (
            f"{display.returncode}:{display.stdout}",
            f"{pointers.returncode}:{pointers.stdout}",
        )

    def probe_display(self) -> DisplayProbe:
        completed = self.runner.run(["xrandr", "--query"])
        if completed.returncode != 0:
            return DisplayProbe(None, ())
        selected_output: str | None = None
        current_output: str | None = None
        modes = []
        for line in completed.stdout.splitlines():
            if line and not line[0].isspace():
                fields = line.split()
                if len(fields) >= 2 and fields[1] == "connected":
                    current_output = fields[0]
                    is_primary = "primary" in fields
                    if selected_output is None or is_primary:
                        selected_output = current_output
                        modes = []
                else:
                    current_output = None
                continue
            if selected_output is None or current_output != selected_output:
                continue
            stripped = line.strip()
            if not stripped:
                continue
            fields = stripped.split()
            dimensions = fields[0].split("x")
            if len(dimensions) != 2 or not all(part.isdigit() for part in dimensions):
                continue
            width, height = (int(part) for part in dimensions)
            refresh_hz: float | None = None
            preferred = False
            current = False
            for token in fields[1:]:
                marker_free = token.replace("*", "").replace("+", "")
                try:
                    refresh_hz = float(marker_free)
                except ValueError:
                    continue
                preferred = preferred or "+" in token
                current = current or "*" in token
                break
            from .hardware import DisplayMode

            modes.append(
                DisplayMode(
                    width=width,
                    height=height,
                    refresh_hz=refresh_hz,
                    preferred=preferred,
                    current=current,
                )
            )
        return DisplayProbe(selected_output, tuple(modes))

    def apply(self, settings: HardwareSettings) -> ApplyResult:
        messages: list[str] = []
        success = True
        display = self.probe_display()

        input_messages, input_success = self._apply_input(settings)
        success = success and input_success
        if input_messages:
            messages.extend(input_messages)
        else:
            messages.append("No libinput pointer properties were available.")

        if display.output_name:
            if settings.resolution == "auto":
                command = ["xrandr", "--output", display.output_name, "--auto"]
            elif settings.resolution in display.allowed_mode_ids:
                command = [
                    "xrandr",
                    "--output",
                    display.output_name,
                    "--mode",
                    settings.resolution,
                ]
            else:
                command = []
                success = False
                messages.append("Requested screen resolution is no longer available.")
            if command:
                completed = self.runner.run(command)
                if completed.returncode != 0:
                    success = False
                    messages.append("Screen resolution could not be applied.")
                else:
                    messages.append("Screen resolution applied.")
        else:
            success = False
            messages.append("No connected display output was detected.")

        return ApplyResult(success, self.probe_display(), tuple(messages))

    def _apply_input(self, settings: HardwareSettings) -> tuple[tuple[str, ...], bool]:
        devices = self._list_pointer_devices()
        messages: list[str] = []
        success = True
        for device_id, named_touchpad in devices:
            properties = self._properties(device_id)
            is_touchpad = named_touchpad or "libinput Tapping Enabled" in properties
            device_success = True
            if is_touchpad:
                outcomes = (
                    self._set_if_available(
                        device_id,
                        properties,
                        "libinput Tapping Enabled",
                        "1" if settings.touchpad_tap else "0",
                    ),
                    self._set_if_available(
                        device_id,
                        properties,
                        "libinput Natural Scrolling Enabled",
                        "1" if settings.natural_scrolling else "0",
                    ),
                    self._set_if_available(
                        device_id,
                        properties,
                        "libinput Accel Speed",
                        f"{settings.touchpad_speed:.2f}",
                    ),
                )
                device_success = all(outcome is not False for outcome in outcomes)
                success = success and device_success
                messages.append(
                    "Touchpad preferences applied."
                    if device_success
                    else "A touchpad preference failed."
                )
            else:
                outcome = self._set_if_available(
                    device_id,
                    properties,
                    "libinput Accel Speed",
                    f"{settings.mouse_speed:.2f}",
                )
                success = success and outcome is not False
                messages.append(
                    "Mouse preferences applied."
                    if outcome is not False
                    else "Mouse speed failed."
                )
        return tuple(messages), success

    def pointer_available(self) -> bool:
        return bool(self._list_pointer_devices())

    def keyboard_available(self) -> bool:
        completed = self.runner.run(["xinput", "--list", "--short"])
        if completed.returncode != 0:
            return False
        return any(
            "id=" in line and "slave  keyboard" in line.casefold()
            for line in completed.stdout.splitlines()
        )

    def _list_pointer_devices(self) -> tuple[tuple[str, bool], ...]:
        completed = self.runner.run(["xinput", "--list", "--short"])
        if completed.returncode != 0:
            return ()
        devices: list[tuple[str, bool]] = []
        for line in completed.stdout.splitlines():
            lowered = line.casefold()
            if "id=" not in line or "slave  pointer" not in lowered:
                continue
            suffix = line.split("id=", 1)[1]
            device_id = suffix.split()[0]
            if not device_id.isdigit():
                continue
            devices.append((device_id, "touchpad" in lowered or "trackpad" in lowered))
        return tuple(devices)

    def _properties(self, device_id: str) -> frozenset[str]:
        completed = self.runner.run(["xinput", "list-props", device_id])
        if completed.returncode != 0:
            return frozenset()
        properties: set[str] = set()
        for line in completed.stdout.splitlines():
            stripped = line.strip()
            if not stripped or "(" not in stripped or "):" not in stripped:
                continue
            properties.add(stripped.split(" (", 1)[0])
        return frozenset(properties)

    def _set_if_available(
        self,
        device_id: str,
        properties: frozenset[str],
        property_name: str,
        value: str,
    ) -> bool | None:
        if property_name not in properties:
            return None
        completed = self.runner.run(
            ["xinput", "set-prop", device_id, property_name, value]
        )
        return completed.returncode == 0


class LegacyXDisplayHAL:
    """Compatibility DisplayHAL backed by the provisional X session."""

    def __init__(self, controller: LegacyXHardwareSessionController | None = None):
        self._controller = controller or LegacyXHardwareSessionController()

    def probe(self) -> DisplayState:
        display = self._controller.probe_display()
        return DisplayState(
            available=display.output_name is not None,
            modes=display.modes,
            backend="legacy-x11",
        )


class LegacyXInputHAL:
    """Compatibility InputHAL during the R7 migration.

    XInput remains responsible only for the current pointer/keyboard view.
    Controller presence is deliberately probed below X11 because controller
    support is a Greia input capability, not an X-specific concept.
    """

    def __init__(
        self,
        controller: LegacyXHardwareSessionController | None = None,
        controller_probe: ControllerPresenceProbe | None = None,
    ):
        self._controller = controller or LegacyXHardwareSessionController()
        self._controller_probe = controller_probe or LinuxControllerPresenceProbe()

    def probe(self) -> InputState:
        return InputState(
            pointer=self._controller.pointer_available(),
            keyboard=self._controller.keyboard_available(),
            controller=self._controller_probe.available(),
            backend="legacy-x11",
        )
