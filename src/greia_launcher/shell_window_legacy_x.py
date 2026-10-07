from __future__ import annotations

import ctypes
import ctypes.util
from typing import Any, Callable, Mapping, Protocol

from .shell_window import ShellActivityModalLease


class X11FocusBridge(Protocol):
    """Small native seam used only by the Legacy-X Shell adapter."""

    def focus_window(self, window_id: int) -> bool: ...

    def focused_window_for_process(
        self, process_id: int, *, excluding_window_id: int
    ) -> int | None: ...

    def raise_and_focus_window(self, window_id: int) -> bool: ...


LibraryFinder = Callable[[str], str | None]
LibraryLoader = Callable[[str], Any]


class CtypesX11FocusBridge:
    """Bounded no-WM X11 focus/stacking operations through libX11.

    The trusted modal path deliberately reuses Greia's existing Shell SDL
    window. Before allowing a picker request, it proves that the currently
    focused non-Shell X11 window advertises the exact supervised Activity PID.
    If that proof is absent or ambiguous, modal preparation fails closed.
    """

    _NET_WM_PID = b"_NET_WM_PID"

    def __init__(
        self,
        *,
        library_finder: LibraryFinder = ctypes.util.find_library,
        library_loader: LibraryLoader = ctypes.CDLL,
    ) -> None:
        self._library_finder = library_finder
        self._library_loader = library_loader

    def _library(self) -> Any | None:
        library_name = self._library_finder("X11")
        if not library_name:
            return None
        x11 = self._library_loader(library_name)
        self._configure_signatures(x11)
        return x11

    def focus_window(self, window_id: int) -> bool:
        if not isinstance(window_id, int) or window_id <= 0:
            return False
        try:
            x11 = self._library()
            if x11 is None:
                return False
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
                    status = x11.XSetInputFocus(display, window_id, 1, 0)
                    if status == 0:
                        return False
                    x11.XFlush(display)
                return True
            finally:
                x11.XCloseDisplay(display)
        except Exception:
            return False

    def focused_window_for_process(
        self, process_id: int, *, excluding_window_id: int
    ) -> int | None:
        """Return focused X11 client only when its _NET_WM_PID matches exactly."""
        if (
            not isinstance(process_id, int)
            or process_id <= 0
            or not isinstance(excluding_window_id, int)
            or excluding_window_id <= 0
        ):
            return None
        try:
            x11 = self._library()
            if x11 is None:
                return None
            display = x11.XOpenDisplay(None)
            if not display:
                return None
            try:
                current = ctypes.c_ulong()
                revert = ctypes.c_int()
                if x11.XGetInputFocus(
                    display, ctypes.byref(current), ctypes.byref(revert)
                ) == 0:
                    return None
                window_id = int(current.value)
                # None/PointerRoot, the Shell itself, and malformed IDs never
                # become a modal restoration target.
                if window_id <= 1 or window_id == excluding_window_id:
                    return None
                atom = x11.XInternAtom(display, self._NET_WM_PID, 1)
                if not atom:
                    return None
                actual_type = ctypes.c_ulong()
                actual_format = ctypes.c_int()
                item_count = ctypes.c_ulong()
                bytes_after = ctypes.c_ulong()
                data = ctypes.POINTER(ctypes.c_ubyte)()
                status = x11.XGetWindowProperty(
                    display,
                    window_id,
                    atom,
                    0,
                    1,
                    0,
                    0,
                    ctypes.byref(actual_type),
                    ctypes.byref(actual_format),
                    ctypes.byref(item_count),
                    ctypes.byref(bytes_after),
                    ctypes.byref(data),
                )
                if status != 0 or actual_format.value != 32 or item_count.value < 1 or not data:
                    return None
                try:
                    advertised = int(
                        ctypes.cast(data, ctypes.POINTER(ctypes.c_ulong))[0]
                    )
                finally:
                    x11.XFree(data)
                return window_id if advertised == process_id else None
            finally:
                x11.XCloseDisplay(display)
        except Exception:
            return None

    def raise_and_focus_window(self, window_id: int) -> bool:
        if not isinstance(window_id, int) or window_id <= 0:
            return False
        try:
            x11 = self._library()
            if x11 is None:
                return False
            display = x11.XOpenDisplay(None)
            if not display:
                return False
            try:
                if x11.XRaiseWindow(display, window_id) == 0:
                    return False
                if x11.XSetInputFocus(display, window_id, 1, 0) == 0:
                    return False
                x11.XFlush(display)
                x11.XSync(display, 0)
                return True
            finally:
                x11.XCloseDisplay(display)
        except Exception:
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
        x11.XRaiseWindow.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        x11.XRaiseWindow.restype = ctypes.c_int
        x11.XFlush.argtypes = [ctypes.c_void_p]
        x11.XFlush.restype = ctypes.c_int
        x11.XSync.argtypes = [ctypes.c_void_p, ctypes.c_int]
        x11.XSync.restype = ctypes.c_int
        x11.XInternAtom.argtypes = [
            ctypes.c_void_p,
            ctypes.c_char_p,
            ctypes.c_int,
        ]
        x11.XInternAtom.restype = ctypes.c_ulong
        x11.XGetWindowProperty.argtypes = [
            ctypes.c_void_p,
            ctypes.c_ulong,
            ctypes.c_ulong,
            ctypes.c_long,
            ctypes.c_long,
            ctypes.c_int,
            ctypes.c_ulong,
            ctypes.POINTER(ctypes.c_ulong),
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_ulong),
            ctypes.POINTER(ctypes.c_ulong),
            ctypes.POINTER(ctypes.POINTER(ctypes.c_ubyte)),
        ]
        x11.XGetWindowProperty.restype = ctypes.c_int
        x11.XFree.argtypes = [ctypes.c_void_p]
        x11.XFree.restype = ctypes.c_int
        x11.XCloseDisplay.argtypes = [ctypes.c_void_p]
        x11.XCloseDisplay.restype = ctypes.c_int


class LegacyXShellWindowController:
    """Legacy-X Shell focus plus exact-session trusted modal stacking.

    The Activity stays alive while the existing Shell window is temporarily
    raised for a platform-owned modal. No second file-picker renderer/window
    is introduced. Restoration targets only the exact focused X11 window whose
    PID matched the supervised Activity when the lease was prepared.
    """

    backend_id = "legacy-x11-shell-window"

    def __init__(self, *, focus_bridge: X11FocusBridge | None = None) -> None:
        self._focus_bridge = focus_bridge or CtypesX11FocusBridge()
        self._modal_generation = 0
        self._modal_lease: ShellActivityModalLease | None = None
        self._modal_shell_window: int | None = None
        self._modal_activity_window: int | None = None
        self._modal_visible = False

    def after_window_created(self, pygame: Any) -> bool:
        return self._focus_shell_window(pygame)

    def after_activity_return(self, pygame: Any) -> bool:
        if self._modal_lease is not None:
            self.abandon_activity_modal(self._modal_lease)
        return self._focus_shell_window(pygame)

    @staticmethod
    def _shell_window_id(pygame: Any) -> int | None:
        try:
            info = pygame.display.get_wm_info()
        except Exception:
            return None
        if not isinstance(info, Mapping):
            return None
        raw_window = info.get("window")
        return raw_window if isinstance(raw_window, int) and raw_window > 0 else None

    def _focus_shell_window(self, pygame: Any) -> bool:
        window_id = self._shell_window_id(pygame)
        if window_id is None:
            return False
        try:
            return bool(self._focus_bridge.focus_window(window_id))
        except Exception:
            return False

    def prepare_activity_modal(
        self,
        pygame: Any,
        *,
        session_id: str,
        activity_pid: int,
    ) -> ShellActivityModalLease | None:
        if self._modal_lease is not None:
            return None
        if (
            not isinstance(session_id, str)
            or not session_id
            or len(session_id) > 128
            or any(ch.isspace() or ch == "\x00" for ch in session_id)
            or not isinstance(activity_pid, int)
            or activity_pid <= 0
        ):
            return None
        shell_window = self._shell_window_id(pygame)
        if shell_window is None:
            return None
        self._modal_generation += 1
        lease = ShellActivityModalLease(
            session_id=session_id,
            generation=self._modal_generation,
            activity_pid=activity_pid,
        )
        self._modal_lease = lease
        self._modal_shell_window = shell_window
        # The Activity's native window is deliberately *not* trusted yet.
        # show_activity_modal() proves the currently focused window advertises
        # this exact supervised PID immediately before covering it.
        self._modal_activity_window = None
        self._modal_visible = False
        return lease

    def _owns(self, lease: ShellActivityModalLease) -> bool:
        return lease is self._modal_lease

    def show_activity_modal(self, lease: ShellActivityModalLease) -> bool:
        if not self._owns(lease) or self._modal_visible:
            return False
        shell_window = self._modal_shell_window
        if shell_window is None:
            return False
        try:
            # READY-time ownership proof can go stale if SDL recreates the
            # Activity window (resize/backend reset). Re-prove the *currently
            # focused* foreground belongs to the exact supervised PID before
            # covering it and update the private restoration target.
            current_activity = self._focus_bridge.focused_window_for_process(
                lease.activity_pid,
                excluding_window_id=shell_window,
            )
            if not isinstance(current_activity, int) or current_activity <= 0:
                return False
            self._modal_activity_window = current_activity
            shown = self._focus_bridge.raise_and_focus_window(shell_window)
        except Exception:
            shown = False
        if shown:
            self._modal_visible = True
        return bool(shown)

    def dismiss_activity_modal(self, lease: ShellActivityModalLease) -> bool:
        if not self._owns(lease):
            return False
        if not self._modal_visible:
            return True
        try:
            restored = (
                self._modal_activity_window is not None
                and self._focus_bridge.raise_and_focus_window(
                    self._modal_activity_window
                )
            )
        except Exception:
            restored = False
        if restored:
            self._modal_visible = False
        return bool(restored)

    def abandon_activity_modal(self, lease: ShellActivityModalLease) -> None:
        if not self._owns(lease):
            return
        self._modal_visible = False
        self._modal_lease = None
        self._modal_shell_window = None
        self._modal_activity_window = None


__all__ = [
    "CtypesX11FocusBridge",
    "LegacyXShellWindowController",
    "X11FocusBridge",
]
