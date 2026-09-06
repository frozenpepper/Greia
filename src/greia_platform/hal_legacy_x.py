from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from typing import Protocol, Sequence

from .display_metrics import DisplayMetricsSource, metrics_for_output
from .hal import (
    ControllerPresenceProbe,
    DisplayState,
    InputState,
    LinuxControllerPresenceProbe,
)
from .hardware import HardwareSettings
from .hardware_session import (
    ApplyResult,
    DisplayProbe,
    PointerCapabilities,
    PointerDeviceInfo,
    PointerKind,
)

# This module is the only R7 module that knows XRandR/XInput vocabulary.
# Backend property names and output-parsing patterns live here and never
# leave this adapter; callers only see semantic DisplayProbe/pointer facts.

_TAPPING_PROP = "libinput Tapping Enabled"
_NATURAL_SCROLL_PROP = "libinput Natural Scrolling Enabled"
_DISABLE_WHILE_TYPING_PROP = "libinput Disable While Typing Enabled"
_ACCEL_SPEED_PROP = "libinput Accel Speed"
_CALIBRATION_PROP = "libinput Calibration Matrix"

# Physical panel size on a connected-output header line, e.g.
# "eDP-1 connected primary 1920x1080+0+0 (...) 309mm x 174mm".
_PHYSICAL_MM_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*mm\s*x\s*(\d+(?:\.\d+)?)\s*mm"
)

_KIND_LABELS = {
    PointerKind.TOUCHPAD: "Touchpad",
    PointerKind.MOUSE: "Mouse",
    PointerKind.OTHER_RELATIVE: "Pointer",
    PointerKind.TOUCHSCREEN: "Touchscreen",
}


@dataclass(frozen=True, slots=True)
class _LocalPointer:
    """Backend-local pointer record. Numeric XInput ids stay here."""

    device_id: str
    kind: PointerKind
    capabilities: PointerCapabilities
    properties: frozenset[str]


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

    Natural-scrolling semantics (explicit, no silent guess): Greia's single
    ``natural_scrolling`` setting is shared by every pointer kind wherever
    the backend reports natural-scrolling support — touchpads and relative
    pointers alike, plus touchscreens when the property exists. Touchscreens
    otherwise expose no tap-to-click, disable-while-typing or speed
    semantics; those controls are not-applicable for them and are skipped
    without failure.
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
        selected_header: str | None = None
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
                        selected_header = line
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
        physical = _parse_physical_mm(selected_header)
        metrics = metrics_for_output(
            selected_output,
            modes,
            physical_width_mm=physical[0] if physical else None,
            physical_height_mm=physical[1] if physical else None,
            source=DisplayMetricsSource.XRANDR_PHYSICAL_SIZE,
        )
        # metrics_for_output returns None when no output is connected or no
        # mode is flagged current (nothing to describe); otherwise it carries
        # the "*" current-mode pixel size with unknown physical size when the
        # header carried absent/malformed mm (never a 96 DPI assumption).
        return DisplayProbe(selected_output, tuple(modes), metrics)

    def apply(self, settings: HardwareSettings) -> ApplyResult:
        messages: list[str] = []
        success = True

        keyboard_messages, keyboard_success = self._apply_keyboard(settings)
        success = success and keyboard_success
        if keyboard_messages:
            messages.extend(keyboard_messages)

        audio_messages, audio_success = self._apply_audio(settings)
        success = success and audio_success
        if audio_messages:
            messages.extend(audio_messages)

        input_messages, input_success = self._apply_pointers(settings)
        success = success and input_success
        if input_messages:
            messages.extend(input_messages)
        else:
            messages.append("No pointer devices were detected.")

        mode_result = self.apply_display_mode(settings)
        success = success and mode_result.applied
        messages.extend(mode_result.messages)

        return ApplyResult(success, mode_result.display, tuple(messages))

    def apply_display_mode(self, settings: HardwareSettings) -> ApplyResult:
        """Apply only the display-mode subset of settings (preframe seam).

        Runs the preceding ``xrandr --query`` probe plus the single mode-set
        command and nothing else (no keyboard/audio/pointer commands), so the
        boot path can establish display correctness synchronously before the
        first frame while all nonvisual work waits behind first-frame
        readiness. Failure stays soft: an unavailable output or rejected
        mode-set reports ``applied=False`` without raising.
        """
        messages: list[str] = []
        success = True
        display = self.probe_display()
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

    def probe_pointers(self) -> tuple[PointerDeviceInfo, ...]:
        """List attached pointers in backend-neutral terms (preview seam)."""
        infos: list[PointerDeviceInfo] = []
        counters: dict[PointerKind, int] = {}
        for record in self._enumerate_pointers():
            counters[record.kind] = counters.get(record.kind, 0) + 1
            infos.append(
                PointerDeviceInfo(
                    kind=record.kind,
                    label=_kind_label(record.kind, counters[record.kind]),
                    capabilities=record.capabilities,
                )
            )
        return tuple(infos)

    def apply_pointer_settings(self, settings: HardwareSettings) -> ApplyResult:
        """Apply only the pointer subset of settings (preview seam).

        Runs no display/keyboard/audio commands so installer/parent UI can
        preview pointer behavior without changing the screen mode.
        """
        messages, success = self._apply_pointers(settings)
        if not messages:
            messages = ("No pointer devices were detected.",)
        return ApplyResult(success, self.probe_display(), tuple(messages))

    def _apply_keyboard(
        self, settings: HardwareSettings
    ) -> tuple[tuple[str, ...], bool]:
        from .keyboard_layout import layout_by_id

        try:
            layout_by_id(settings.keyboard_layout)
        except LookupError:
            return (f"Unsupported keyboard layout: {settings.keyboard_layout}",), False
        completed = self.runner.run(["setxkbmap", settings.keyboard_layout])
        if completed.returncode != 0:
            return (f"Keyboard layout could not be applied ({settings.keyboard_layout}).",), False
        return (f"Keyboard layout set to {settings.keyboard_layout}.",), True

    def _apply_audio(
        self, settings: HardwareSettings
    ) -> tuple[tuple[str, ...], bool]:
        pct = min(100, max(0, int((settings.mic_gain / 2.0) * 100)))
        commands = [
            ["amixer", "-q", "set", "Capture", f"{pct}%", "unmute"],
            ["amixer", "-q", "set", "Mic", f"{pct}%", "unmute"],
            ["amixer", "-q", "set", "Internal Mic", f"{pct}%", "unmute"],
        ]
        for cmd in commands:
            self.runner.run(cmd)
        return (f"Microphone gain set to {int(settings.mic_gain * 100)}%.",), True

    def _apply_input(self, settings: HardwareSettings) -> tuple[tuple[str, ...], bool]:
        # Kept for backward compatibility with existing callers/tests that
        # drive the private input path; delegates to the semantic applier so
        # there is exactly one pointer-apply implementation.
        return self._apply_pointers(settings)

    def _apply_pointers(
        self, settings: HardwareSettings
    ) -> tuple[tuple[str, ...], bool]:
        records = self._enumerate_pointers()
        messages: list[str] = []
        success = True
        for record in records:
            outcomes: list[bool | None] = []
            if record.kind is PointerKind.TOUCHPAD:
                if record.capabilities.supports_tap:
                    outcomes.append(
                        self._set_if_available(
                            record.device_id,
                            record.properties,
                            _TAPPING_PROP,
                            "1" if settings.touchpad_tap else "0",
                        )
                    )
                if record.capabilities.supports_disable_while_typing:
                    outcomes.append(
                        self._set_if_available(
                            record.device_id,
                            record.properties,
                            _DISABLE_WHILE_TYPING_PROP,
                            "1" if settings.disable_while_typing else "0",
                        )
                    )
                if record.capabilities.supports_natural_scrolling:
                    outcomes.append(
                        self._set_if_available(
                            record.device_id,
                            record.properties,
                            _NATURAL_SCROLL_PROP,
                            "1" if settings.natural_scrolling else "0",
                        )
                    )
                if record.capabilities.supports_speed:
                    outcomes.append(
                        self._set_if_available(
                            record.device_id,
                            record.properties,
                            _ACCEL_SPEED_PROP,
                            f"{settings.touchpad_speed:.2f}",
                        )
                    )
                device_success = all(outcome is not False for outcome in outcomes)
                success = success and device_success
                messages.append(
                    "Touchpad preferences applied."
                    if device_success
                    else "A touchpad preference failed."
                )
            elif record.kind is PointerKind.TOUCHSCREEN:
                if record.capabilities.supports_natural_scrolling:
                    outcome = self._set_if_available(
                        record.device_id,
                        record.properties,
                        _NATURAL_SCROLL_PROP,
                        "1" if settings.natural_scrolling else "0",
                    )
                    device_success = outcome is not False
                    success = success and device_success
                    messages.append(
                        "Touchscreen preferences applied."
                        if device_success
                        else "A touchscreen preference failed."
                    )
                else:
                    messages.append("Touchscreen needs no pointer settings.")
            else:
                if record.capabilities.supports_natural_scrolling:
                    outcomes.append(
                        self._set_if_available(
                            record.device_id,
                            record.properties,
                            _NATURAL_SCROLL_PROP,
                            "1" if settings.natural_scrolling else "0",
                        )
                    )
                if record.capabilities.supports_speed:
                    outcomes.append(
                        self._set_if_available(
                            record.device_id,
                            record.properties,
                            _ACCEL_SPEED_PROP,
                            f"{settings.mouse_speed:.2f}",
                        )
                    )
                device_success = all(outcome is not False for outcome in outcomes)
                success = success and device_success
                messages.append(
                    "Mouse preferences applied."
                    if device_success
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

    def _enumerate_pointers(self) -> tuple[_LocalPointer, ...]:
        """Enumerate pointers with capabilities; numeric ids stay local."""
        completed = self.runner.run(["xinput", "--list", "--short"])
        if completed.returncode != 0:
            return ()
        records: list[_LocalPointer] = []
        for line in completed.stdout.splitlines():
            lowered = line.casefold()
            if "id=" not in line or "slave  pointer" not in lowered:
                continue
            suffix = line.split("id=", 1)[1]
            device_id = suffix.split()[0]
            if not device_id.isdigit():
                continue
            properties = self._properties(device_id)
            kind = _classify_pointer(lowered, properties)
            records.append(
                _LocalPointer(
                    device_id=device_id,
                    kind=kind,
                    capabilities=_capabilities_for(properties),
                    properties=properties,
                )
            )
        return tuple(records)

    def _list_pointer_devices(self) -> tuple[tuple[str, bool], ...]:
        # Lightweight presence probe (no per-device property round-trips).
        # Kept for pointer_available(); classification lives in
        # _enumerate_pointers() so exact names are never required.
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


def _parse_physical_mm(header: str | None) -> tuple[float, float] | None:
    """Extract connected-output physical mm from one xrandr header line.

    Returns ``None`` when the header is missing/malformed so the caller
    reports unknown physical size instead of assuming a density.
    """
    if not header:
        return None
    match = _PHYSICAL_MM_RE.search(header)
    if not match:
        return None
    try:
        width_mm = float(match.group(1))
        height_mm = float(match.group(2))
    except ValueError:
        return None
    return (width_mm, height_mm)


def _capabilities_for(properties: frozenset[str]) -> PointerCapabilities:
    return PointerCapabilities(
        supports_tap=_TAPPING_PROP in properties,
        supports_natural_scrolling=_NATURAL_SCROLL_PROP in properties,
        supports_disable_while_typing=_DISABLE_WHILE_TYPING_PROP in properties,
        supports_speed=_ACCEL_SPEED_PROP in properties,
    )


def _classify_pointer(name_lowered: str, properties: frozenset[str]) -> PointerKind:
    """Classify one pointer: properties/capabilities primary, name fallback.

    The tapping property identifies touchpads and the calibration-matrix
    property identifies touchscreens regardless of device name, so no
    exact device name is ever required. Name substrings are only a
    fallback hint (e.g. when list-props is unavailable) and for the
    mouse-vs-other-relative distinction, which shares the same
    capabilities.
    """
    if _TAPPING_PROP in properties:
        return PointerKind.TOUCHPAD
    if _CALIBRATION_PROP in properties:
        return PointerKind.TOUCHSCREEN
    if "touchpad" in name_lowered or "trackpad" in name_lowered:
        return PointerKind.TOUCHPAD
    if "touchscreen" in name_lowered or "touch digitizer" in name_lowered:
        return PointerKind.TOUCHSCREEN
    if "mouse" in name_lowered:
        return PointerKind.MOUSE
    if _ACCEL_SPEED_PROP in properties:
        return PointerKind.MOUSE
    if properties:
        return PointerKind.OTHER_RELATIVE
    return PointerKind.OTHER_RELATIVE


def _kind_label(kind: PointerKind, occurrence: int) -> str:
    base = _KIND_LABELS[kind]
    if occurrence <= 1:
        return base
    return f"{base} {occurrence}"


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
