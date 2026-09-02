from __future__ import annotations

import ctypes
import ctypes.util
import select
import subprocess
from pathlib import Path
from threading import Event
from typing import Protocol, Sequence

from .system_controls import (
    SystemControlAction,
    SystemControlApplyResult,
    SystemControlService,
    SystemControlSettings,
    SystemControlSettingsStore,
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


class LegacyXSystemControlBackend:
    """Current installed-system adapter for output volume and panel brightness.

    ALSA is the current Greia output authority. Brightness prefers a writable
    kernel backlight endpoint; while Legacy-X remains the active display backend,
    xrandr gamma is an explicit compatibility fallback when the unprivileged
    child session cannot write the hardware backlight attribute.
    """

    def __init__(
        self,
        runner: CommandRunner | None = None,
        *,
        backlight_root: Path = Path("/sys/class/backlight"),
    ) -> None:
        self.runner = runner or SubprocessRunner()
        self.backlight_root = backlight_root

    def apply(self, settings: SystemControlSettings) -> SystemControlApplyResult:
        volume_ok, volume_message = self._apply_volume(settings)
        brightness_ok, brightness_backend, brightness_message = self._apply_brightness(
            settings.brightness_percent
        )
        return SystemControlApplyResult(
            applied=volume_ok and brightness_ok,
            volume_available=volume_ok,
            brightness_available=brightness_ok,
            brightness_backend=brightness_backend,
            messages=(volume_message, brightness_message),
        )

    def _apply_volume(self, settings: SystemControlSettings) -> tuple[bool, str]:
        switch = "mute" if settings.muted else "unmute"
        # Master is the intended path. Speaker/PCM are bounded compatibility
        # fallbacks for older ALSA cards; stop at the first real control.
        for control in ("Master", "Speaker", "PCM"):
            completed = self.runner.run(
                [
                    "amixer",
                    "-q",
                    "set",
                    control,
                    f"{settings.volume_percent}%",
                    switch,
                ]
            )
            if completed.returncode == 0:
                state = "muted" if settings.muted else f"{settings.volume_percent}%"
                return True, f"Output volume {state} via ALSA {control}."
        return False, "No supported ALSA output volume control was available."

    def _apply_brightness(self, percent: int) -> tuple[bool, str | None, str]:
        physical = self._physical_backlight()
        if physical is not None:
            brightness_path, max_brightness = physical
            raw = max(1, round(max_brightness * percent / 100.0))
            try:
                brightness_path.write_text(f"{raw}\n", encoding="ascii")
                return True, "sysfs", f"Panel brightness set to {percent}%."
            except OSError:
                # The current unprivileged Legacy-X image may expose the panel
                # read-only. Falling back here preserves working keys without
                # granting the launcher broad root or raw-device authority.
                pass

        output = self._connected_output()
        if output is None:
            return False, None, "No connected display was available for brightness."
        completed = self.runner.run(
            ["xrandr", "--output", output, "--brightness", f"{percent / 100.0:.2f}"]
        )
        if completed.returncode != 0:
            return False, None, "Display brightness could not be applied."
        return (
            True,
            "legacy-xrandr",
            f"Display brightness set to {percent}% through Legacy-X fallback.",
        )

    def _physical_backlight(self) -> tuple[Path, int] | None:
        try:
            candidates = sorted(self.backlight_root.iterdir())
        except OSError:
            return None
        for candidate in candidates:
            brightness = candidate / "brightness"
            maximum = candidate / "max_brightness"
            try:
                max_value = int(maximum.read_text(encoding="ascii").strip())
            except (OSError, ValueError):
                continue
            if max_value > 0 and brightness.exists():
                return brightness, max_value
        return None

    def _connected_output(self) -> str | None:
        completed = self.runner.run(["xrandr", "--query"])
        if completed.returncode != 0:
            return None
        first: str | None = None
        for line in completed.stdout.splitlines():
            if not line or line[0].isspace():
                continue
            fields = line.split()
            if len(fields) < 2 or fields[1] != "connected":
                continue
            if "primary" in fields:
                return fields[0]
            if first is None:
                first = fields[0]
        return first


class _XKeyEvent(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_int),
        ("serial", ctypes.c_ulong),
        ("send_event", ctypes.c_int),
        ("display", ctypes.c_void_p),
        ("window", ctypes.c_ulong),
        ("root", ctypes.c_ulong),
        ("subwindow", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("x", ctypes.c_int),
        ("y", ctypes.c_int),
        ("x_root", ctypes.c_int),
        ("y_root", ctypes.c_int),
        ("state", ctypes.c_uint),
        ("keycode", ctypes.c_uint),
        ("same_screen", ctypes.c_int),
    ]


class _XEvent(ctypes.Union):
    _fields_ = [
        ("type", ctypes.c_int),
        ("xkey", _XKeyEvent),
        ("pad", ctypes.c_long * 24),
    ]


class LegacyXMediaKeyListener:
    """Grab only Greia-owned XF86 system keys from the Legacy-X root window."""

    _KEY_PRESS = 2
    _ANY_MODIFIER = 1 << 15
    _GRAB_MODE_ASYNC = 1
    _KEYSYMS = {
        0x1008FF13: SystemControlAction.VOLUME_UP,        # XF86AudioRaiseVolume
        0x1008FF11: SystemControlAction.VOLUME_DOWN,      # XF86AudioLowerVolume
        0x1008FF12: SystemControlAction.VOLUME_MUTE,      # XF86AudioMute
        0x1008FF02: SystemControlAction.BRIGHTNESS_UP,    # XF86MonBrightnessUp
        0x1008FF03: SystemControlAction.BRIGHTNESS_DOWN,  # XF86MonBrightnessDown
    }

    def __init__(self) -> None:
        library_name = ctypes.util.find_library("X11")
        if not library_name:
            raise RuntimeError("libX11 is unavailable")
        x11 = ctypes.CDLL(library_name)
        self._configure_signatures(x11)
        display = x11.XOpenDisplay(None)
        if not display:
            raise RuntimeError("cannot open the Legacy-X display for system keys")
        self._x11 = x11
        self._display = int(display)
        self._root = int(x11.XDefaultRootWindow(display))
        self._actions_by_keycode: dict[int, SystemControlAction] = {}
        try:
            for keysym, action in self._KEYSYMS.items():
                keycode = int(x11.XKeysymToKeycode(display, keysym))
                if keycode <= 0:
                    continue
                x11.XGrabKey(
                    display,
                    keycode,
                    self._ANY_MODIFIER,
                    self._root,
                    0,
                    self._GRAB_MODE_ASYNC,
                    self._GRAB_MODE_ASYNC,
                )
                self._actions_by_keycode[keycode] = action
            x11.XSync(display, 0)
            self._fd = int(x11.XConnectionNumber(display))
        except Exception:
            x11.XCloseDisplay(display)
            raise
        if not self._actions_by_keycode:
            self.close()
            raise RuntimeError("no XF86 system key mappings are available")

    def wait_action(self, timeout_seconds: float) -> SystemControlAction | None:
        if self._display is None:
            return None
        ready, _, _ = select.select([self._fd], [], [], max(0.0, timeout_seconds))
        if not ready:
            return None
        event = _XEvent()
        while self._x11.XPending(self._display) > 0:
            self._x11.XNextEvent(self._display, ctypes.byref(event))
            if event.type != self._KEY_PRESS:
                continue
            action = self._actions_by_keycode.get(int(event.xkey.keycode))
            if action is not None:
                return action
        return None

    def close(self) -> None:
        display = getattr(self, "_display", None)
        if display is None:
            return
        self._display = None
        self._x11.XUngrabKey(
            display,
            0,
            self._ANY_MODIFIER,
            self._root,
        )
        self._x11.XSync(display, 0)
        self._x11.XCloseDisplay(display)

    @staticmethod
    def _configure_signatures(x11: object) -> None:
        x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
        x11.XOpenDisplay.restype = ctypes.c_void_p
        x11.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
        x11.XDefaultRootWindow.restype = ctypes.c_ulong
        x11.XKeysymToKeycode.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        x11.XKeysymToKeycode.restype = ctypes.c_ubyte
        x11.XGrabKey.argtypes = [
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.c_uint,
            ctypes.c_ulong,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
        ]
        x11.XGrabKey.restype = ctypes.c_int
        x11.XUngrabKey.argtypes = [
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.c_uint,
            ctypes.c_ulong,
        ]
        x11.XUngrabKey.restype = ctypes.c_int
        x11.XConnectionNumber.argtypes = [ctypes.c_void_p]
        x11.XConnectionNumber.restype = ctypes.c_int
        x11.XPending.argtypes = [ctypes.c_void_p]
        x11.XPending.restype = ctypes.c_int
        x11.XNextEvent.argtypes = [ctypes.c_void_p, ctypes.POINTER(_XEvent)]
        x11.XNextEvent.restype = ctypes.c_int
        x11.XSync.argtypes = [ctypes.c_void_p, ctypes.c_int]
        x11.XSync.restype = ctypes.c_int
        x11.XCloseDisplay.argtypes = [ctypes.c_void_p]
        x11.XCloseDisplay.restype = ctypes.c_int


def run_legacy_x_system_controls(
    store: SystemControlSettingsStore,
    *,
    backend: LegacyXSystemControlBackend | None = None,
    stop_event: Event | None = None,
    poll_seconds: float = 0.25,
    once: bool = False,
) -> int:
    """Apply Parent state and globally consume only the five system media keys."""

    controller = backend or LegacyXSystemControlBackend()
    service = SystemControlService(store, controller)
    stopper = stop_event or Event()
    service.apply_current()
    if once:
        return 0
    last_token = store.version_token()
    try:
        listener: LegacyXMediaKeyListener | None = LegacyXMediaKeyListener()
    except Exception:
        # Parent volume state must still work when a particular X keyboard map
        # cannot expose the XF86 keysyms. Physical acceptance reports this lane.
        listener = None

    try:
        while not stopper.is_set():
            if listener is None:
                stopper.wait(poll_seconds)
                action = None
            else:
                action = listener.wait_action(poll_seconds)
            if action is not None:
                service.handle_action(action)
                last_token = store.version_token()
                continue
            token = store.version_token()
            if token != last_token:
                last_token = token
                service.apply_current()
    finally:
        if listener is not None:
            listener.close()
    return 0
