from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Sequence

from .hardware import (
    DisplayMode,
    HardwareSettings,
    HardwareSettingsStore,
)


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


@dataclass(frozen=True, slots=True)
class DisplayProbe:
    output_name: str | None
    modes: tuple[DisplayMode, ...]

    @property
    def allowed_mode_ids(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(mode.mode_id for mode in self.modes))


@dataclass(frozen=True, slots=True)
class ApplyResult:
    applied: bool
    display: DisplayProbe
    messages: tuple[str, ...]


class HardwareSessionController(Protocol):
    """Backend-neutral display/input settings controller used by the watcher."""

    def topology_token(self) -> tuple[str, ...]: ...

    def probe_display(self) -> DisplayProbe: ...

    def apply(self, settings: HardwareSettings) -> ApplyResult: ...


class XSessionHardwareController:
    """Applies validated preferences inside the active child X session.

    The controller is deliberately declarative: the parent service can only
    write bounded settings, while this process maps them to known xinput/xrandr
    properties. It never accepts arbitrary commands or device property names.
    """

    def __init__(self, runner: CommandRunner | None = None):
        self.runner = runner or SubprocessRunner()

    def topology_token(self) -> tuple[str, str]:
        """Return a cheap token for display/pointer hot-plug changes."""

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
        modes: list[DisplayMode] = []
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
                        device_id, properties, "libinput Tapping Enabled",
                        "1" if settings.touchpad_tap else "0",
                    ),
                    self._set_if_available(
                        device_id, properties, "libinput Natural Scrolling Enabled",
                        "1" if settings.natural_scrolling else "0",
                    ),
                    self._set_if_available(
                        device_id, properties, "libinput Accel Speed",
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
                    device_id, properties, "libinput Accel Speed",
                    f"{settings.mouse_speed:.2f}",
                )
                success = success and outcome is not False
                messages.append("Mouse preferences applied." if outcome is not False else "Mouse speed failed.")
        return tuple(messages), success

    def pointer_available(self) -> bool:
        """Return whether the provisional X backend currently exposes a pointer."""

        return bool(self._list_pointer_devices())

    def keyboard_available(self) -> bool:
        """Return whether XInput exposes a real keyboard on the active seat."""

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


def run_watcher(
    store: HardwareSettingsStore,
    status_path: Path,
    *,
    interval_seconds: float = 0.5,
    once: bool = False,
    controller: HardwareSessionController | None = None,
) -> int:
    controller = controller or XSessionHardwareController()
    last_settings_token: int | None = None
    last_topology_token: tuple[str, ...] | None = None
    next_topology_probe = 0.0
    retry_at = 0.0
    last_apply_succeeded = False
    while True:
        now = time.monotonic()
        settings_token = store.version_token()
        topology_token = last_topology_token
        if topology_token is None or now >= next_topology_probe:
            topology_token = controller.topology_token()
            next_topology_probe = now + 2.0
        should_apply = (
            settings_token != last_settings_token
            or topology_token != last_topology_token
            or (not last_apply_succeeded and now >= retry_at)
        )
        if should_apply:
            last_settings_token = settings_token
            last_topology_token = topology_token
            settings = store.read()
            display = controller.probe_display()
            try:
                store.validate(settings, allowed_resolutions=display.allowed_mode_ids)
                result = controller.apply(settings)
                last_apply_succeeded = result.applied
                retry_at = now + 2.0
                message = " ".join(result.messages)
                _write_status(status_path, settings, result, message)
            except Exception as exc:  # keep the child session alive on driver errors
                last_apply_succeeded = False
                retry_at = now + 2.0
                failed = ApplyResult(False, display, (str(exc),))
                _write_status(status_path, settings, failed, str(exc))
        if once:
            return 0
        time.sleep(interval_seconds)


def _write_status(
    path: Path,
    settings: HardwareSettings,
    result: ApplyResult,
    message: str,
) -> None:
    payload = {
        "settings": settings.as_json_dict(),
        "applied": result.applied,
        "display_output": result.display.output_name,
        "display_modes": [mode.as_json_dict() for mode in result.display.modes],
        "message": message,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    os.chmod(temporary, 0o640)
    temporary.replace(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(os.environ.get("GREIA_OS_ROOT", "/opt/greia-os")),
    )
    parser.add_argument(
        "--state-dir",
        type=Path,
        default=Path(
            os.environ.get("GREIA_SYSTEM_SETTINGS_DIR", "/var/lib/greia-system-settings")
        ),
    )
    parser.add_argument(
        "--status-path",
        type=Path,
        default=Path("/run/greia-hardware/status.json"),
    )
    parser.add_argument("--once", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = HardwareSettingsStore.load(
        args.root / "runtime" / "hardware-settings.toml",
        args.state_dir,
    )
    return run_watcher(store, args.status_path, once=args.once)


if __name__ == "__main__":
    raise SystemExit(main())
