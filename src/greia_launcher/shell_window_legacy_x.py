from __future__ import annotations

import ctypes
import ctypes.util
from typing import Any, Callable, Mapping, Protocol


class X11FocusBridge(Protocol):
    """Small native seam used only by the Legacy-X Shell adapter."""

    def focus_window(self, window_id: int) -> bool: ...


LibraryFinder = Callable[[str], str | None]
LibraryLoader = Callable[[str], Any]


class CtypesX11FocusBridge:
    """Perform the current no-WM X11 focus fix through libX11.

    Greia's compatibility xinit session has no window manager, so the Shell's
    SDL window may otherwise never receive keyboard focus. This object owns the
    native Xlib detail so generic launcher code does not.

    The operation is one-shot after window creation. There is no polling,
    background worker or frame-loop cost.
    """

    def __init__(
        self,
        *,
        library_finder: LibraryFinder = ctypes.util.find_library,
        library_loader: LibraryLoader = ctypes.CDLL,
    ) -> None:
        self._library_finder = library_finder
        self._library_loader = library_loader

    def focus_window(self, window_id: int) -> bool:
        if not isinstance(window_id, int) or window_id <= 0:
            return False
        try:
            library_name = self._library_finder("X11")
            if not library_name:
                return False
            x11 = self._library_loader(library_name)
            self._configure_signatures(x11)
            display = x11.XOpenDisplay(None)
            if not display:
                return False
            try:
                current = ctypes.c_ulong()
                revert = ctypes.c_int()
                status = x11.XGetInputFocus(
                    display,
                    ctypes.byref(current),
                    ctypes.byref(revert),
                )
                if status == 0:
                    return False
                if current.value != window_id:
                    # RevertToParent = 1, CurrentTime = 0.
                    status = x11.XSetInputFocus(display, window_id, 1, 0)
                    if status == 0:
                        return False
                return True
            finally:
                x11.XCloseDisplay(display)
        except Exception:
            # This compatibility repair has historically been best-effort. A
            # missing/broken Xlib must not crash the child-facing Shell.
            return False

    @staticmethod
    def _configure_signatures(x11: Any) -> None:
        """Declare pointer-width-safe Xlib signatures before the first call."""

        x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
        x11.XOpenDisplay.restype = ctypes.c_void_p
        x11.XGetInputFocus.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_ulong),
            ctypes.POINTER(ctypes.c_int),
        ]
        x11.XGetInputFocus.restype = ctypes.c_int
        x11.XSetInputFocus.argtypes = [
            ctypes.c_void_p,
            ctypes.c_ulong,
            ctypes.c_int,
            ctypes.c_ulong,
        ]
        x11.XSetInputFocus.restype = ctypes.c_int
        x11.XCloseDisplay.argtypes = [ctypes.c_void_p]
        x11.XCloseDisplay.restype = ctypes.c_int


class LegacyXShellWindowController:
    """Legacy-X implementation of Greia's one-shot Shell window setup.

    This class is instantiated only by the trusted Legacy-X composition path.
    It therefore never chooses or detects the active display backend itself.
    """

    backend_id = "legacy-x11-shell-window"

    def __init__(self, *, focus_bridge: X11FocusBridge | None = None) -> None:
        self._focus_bridge = focus_bridge or CtypesX11FocusBridge()

    def after_window_created(self, pygame: Any) -> bool:
        try:
            info = pygame.display.get_wm_info()
        except Exception:
            return False
        if not isinstance(info, Mapping):
            return False
        raw_window = info.get("window")
        if not isinstance(raw_window, int) or raw_window <= 0:
            return False
        try:
            return bool(self._focus_bridge.focus_window(raw_window))
        except Exception:
            return False


__all__ = [
    "CtypesX11FocusBridge",
    "LegacyXShellWindowController",
    "X11FocusBridge",
]