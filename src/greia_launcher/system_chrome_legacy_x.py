from __future__ import annotations

import ctypes
import ctypes.util
from typing import Any, Protocol

from greia_platform.display_metrics import DisplayMetrics
from greia_platform.system_chrome import (
    ActivitySystemChromeLayout,
    SystemNavigationAction,
    UiRect,
)

from .system_chrome import resolve_trusted_action_minimum_px


def layout_for_surface_with_metrics(
    width: int,
    height: int,
    *,
    back_available: bool = False,
    metrics: Any = None,
) -> ActivitySystemChromeLayout:
    """Build trusted chrome geometry enforcing the shared physical floor.

    The base geometry comes from :meth:`ActivitySystemChromeLayout.for_surface`
    and is returned unchanged when ``metrics`` is missing, unknown, or
    low-density. Trustworthy high-density metrics grow the Home/Back hitboxes
    in place: Home keeps its exact origin (it never moves for high DPI), the
    Back hitbox keeps its gap, and the protected region expands to cover both.
    Visual size, margins, and gaps are decorative and never scaled. When the
    surface cannot host the enlarged chrome, the base layout is returned so
    geometry fails soft instead of escaping the surface. ``metrics`` is
    injected by the composition owner; nothing here probes hardware.
    """
    base = ActivitySystemChromeLayout.for_surface(
        width,
        height,
        back_available=back_available,
    )
    floor_px = resolve_trusted_action_minimum_px(
        metrics, fallback_px=base.home_hitbox.width
    )
    if floor_px <= base.home_hitbox.width:
        return base
    margin = base.home_hitbox.x
    gap = base.back_hitbox.x - base.home_hitbox.right
    if width < margin * 2 + floor_px * 2 + gap:
        return base
    if height < margin * 2 + floor_px:
        return base
    home = UiRect(margin, margin, floor_px, floor_px)
    back = UiRect(home.right + gap, margin, floor_px, floor_px)
    protected = UiRect(0, 0, back.right + margin, floor_px + margin * 2)
    return ActivitySystemChromeLayout(
        surface_width=base.surface_width,
        surface_height=base.surface_height,
        home_hitbox=home,
        back_hitbox=back,
        protected_region=protected,
        visual_size=base.visual_size,
        back_available=base.back_available,
    )


class LegacyXChromeBridge(Protocol):
    """Native X11 mechanics required by the provisional trusted chrome host."""

    def prepare(
        self,
        *,
        back_available: bool,
        metrics: DisplayMetrics | None = None,
    ) -> ActivitySystemChromeLayout: ...

    def show(self) -> None: ...

    def poll_pointer_release(self) -> tuple[int, int] | None: ...

    def hide(self) -> None: ...


class _XButtonEvent(ctypes.Structure):
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
        ("button", ctypes.c_uint),
        ("same_screen", ctypes.c_int),
    ]


class _XEvent(ctypes.Union):
    # Xlib guarantees XEvent is large enough for 24 longs on every supported
    # ABI. Keeping the native union shape matters on Greia's 32-bit Acer floor.
    _fields_ = [
        ("type", ctypes.c_int),
        ("xbutton", _XButtonEvent),
        ("pad", ctypes.c_long * 24),
    ]


class CtypesLegacyXChromeBridge:
    """One tiny X11 window containing only Greia's protected Home/Back region.

    The current compatibility session has no window manager. The bridge opens a
    second trusted X connection from the launcher process, creates a window only
    as large as the renderer-neutral protected region, maps it above the
    Activity after READY, and consumes pointer releases delivered to that
    window. It never copies Activity pixels and does no idle redraw/polling of
    the framebuffer.

    This is intentionally a Legacy-X migration adapter. Shared X11 still cannot
    provide the final malicious-client isolation required by ADR 0014/0019; the
    target direct/compositor backend must replace it without changing the
    SystemChromeCoordinator contract.
    """

    _EXPOSURE_MASK = 1 << 15
    _BUTTON_PRESS_MASK = 1 << 2
    _BUTTON_RELEASE_MASK = 1 << 3
    _EXPOSE = 12
    _BUTTON_RELEASE = 5
    _LEFT_BUTTON = 1

    def __init__(self) -> None:
        self._x11: object | None = None
        self._display: int | None = None
        self._window: int | None = None
        self._gc: int | None = None
        self._black_pixel: int = 0
        self._layout: ActivitySystemChromeLayout | None = None

    def prepare(
        self,
        *,
        back_available: bool,
        metrics: Any = None,
    ) -> ActivitySystemChromeLayout:
        if self._display is not None:
            raise RuntimeError("Legacy-X system chrome is already prepared")

        library_name = ctypes.util.find_library("X11")
        if not library_name:
            raise RuntimeError("libX11 is unavailable")
        x11 = ctypes.CDLL(library_name)
        self._configure_signatures(x11)
        display = x11.XOpenDisplay(None)
        if not display:
            raise RuntimeError("cannot open the Legacy-X display")

        self._x11 = x11
        self._display = int(display)
        try:
            screen = int(x11.XDefaultScreen(display))
            width = int(x11.XDisplayWidth(display, screen))
            height = int(x11.XDisplayHeight(display, screen))
            layout = layout_for_surface_with_metrics(
                width,
                height,
                back_available=back_available,
                metrics=metrics,
            )
            root = int(x11.XDefaultRootWindow(display))
            black = int(x11.XBlackPixel(display, screen))
            white = int(x11.XWhitePixel(display, screen))
            protected = layout.protected_region
            window = int(
                x11.XCreateSimpleWindow(
                    display,
                    root,
                    protected.x,
                    protected.y,
                    protected.width,
                    protected.height,
                    0,
                    black,
                    white,
                )
            )
            if not window:
                raise RuntimeError("cannot create the Legacy-X system chrome window")
            event_mask = (
                self._EXPOSURE_MASK
                | self._BUTTON_PRESS_MASK
                | self._BUTTON_RELEASE_MASK
            )
            x11.XSelectInput(display, window, event_mask)
            gc = x11.XCreateGC(display, window, 0, None)
            if not gc:
                x11.XDestroyWindow(display, window)
                raise RuntimeError("cannot create the Legacy-X system chrome graphics context")
            self._window = window
            self._gc = int(gc)
            self._black_pixel = black
            self._layout = layout
            return layout
        except Exception:
            self._close_native()
            raise

    def show(self) -> None:
        x11, display, window, _gc, _layout = self._require_prepared()
        x11.XMapRaised(display, window)
        x11.XSync(display, 0)
        self._draw()

    def poll_pointer_release(self) -> tuple[int, int] | None:
        x11, display, _window, _gc, layout = self._require_prepared()
        event = _XEvent()
        selected: tuple[int, int] | None = None
        while x11.XPending(display) > 0:
            x11.XNextEvent(display, ctypes.byref(event))
            if event.type == self._EXPOSE:
                self._draw()
                continue
            if (
                event.type == self._BUTTON_RELEASE
                and event.xbutton.button == self._LEFT_BUTTON
                and selected is None
            ):
                protected = layout.protected_region
                selected = (
                    protected.x + int(event.xbutton.x),
                    protected.y + int(event.xbutton.y),
                )
        return selected

    def hide(self) -> None:
        if self._display is None:
            return
        self._close_native()

    def _draw(self) -> None:
        x11, display, window, gc, layout = self._require_prepared()
        x11.XClearWindow(display, window)
        x11.XSetForeground(display, gc, self._black_pixel)
        protected = layout.protected_region
        self._draw_button(x11, display, window, gc, layout.home_hitbox, protected)
        self._draw_home_glyph(x11, display, window, gc, layout.home_hitbox, protected)
        if layout.back_available:
            self._draw_button(x11, display, window, gc, layout.back_hitbox, protected)
            self._draw_back_glyph(x11, display, window, gc, layout.back_hitbox, protected)
        x11.XFlush(display)

    @staticmethod
    def _local_origin(rect, protected) -> tuple[int, int]:
        return rect.x - protected.x, rect.y - protected.y

    @classmethod
    def _draw_button(cls, x11, display: int, window: int, gc: int, rect, protected) -> None:
        local_x, local_y = cls._local_origin(rect, protected)
        inset = max(5, rect.width // 10)
        x = local_x + inset
        y = local_y + inset
        width = max(1, rect.width - inset * 2)
        height = max(1, rect.height - inset * 2)
        x11.XDrawArc(display, window, gc, x, y, width, height, 0, 360 * 64)

    @classmethod
    def _draw_home_glyph(cls, x11, display: int, window: int, gc: int, rect, protected) -> None:
        local_x, local_y = cls._local_origin(rect, protected)
        cx, cy = local_x + rect.width // 2, local_y + rect.height // 2
        span = max(8, rect.width // 5)
        roof_y = cy - span
        wall_y = cy + span
        left = cx - span
        right = cx + span
        x11.XDrawLine(display, window, gc, left, cy - 2, cx, roof_y)
        x11.XDrawLine(display, window, gc, cx, roof_y, right, cy - 2)
        x11.XDrawLine(display, window, gc, left, cy - 2, left, wall_y)
        x11.XDrawLine(display, window, gc, right, cy - 2, right, wall_y)
        x11.XDrawLine(display, window, gc, left, wall_y, right, wall_y)

    @classmethod
    def _draw_back_glyph(cls, x11, display: int, window: int, gc: int, rect, protected) -> None:
        local_x, local_y = cls._local_origin(rect, protected)
        cx, cy = local_x + rect.width // 2, local_y + rect.height // 2
        span = max(8, rect.width // 5)
        x11.XDrawLine(display, window, gc, cx + span, cy, cx - span, cy)
        x11.XDrawLine(display, window, gc, cx - span, cy, cx, cy - span)
        x11.XDrawLine(display, window, gc, cx - span, cy, cx, cy + span)

    def _require_prepared(self):
        if (
            self._x11 is None
            or self._display is None
            or self._window is None
            or self._gc is None
            or self._layout is None
        ):
            raise RuntimeError("Legacy-X system chrome is not prepared")
        return self._x11, self._display, self._window, self._gc, self._layout

    def _close_native(self) -> None:
        x11 = self._x11
        display = self._display
        window = self._window
        gc = self._gc
        self._x11 = None
        self._display = None
        self._window = None
        self._gc = None
        self._layout = None
        if x11 is None or display is None:
            return
        try:
            if gc is not None:
                x11.XFreeGC(display, gc)
            if window is not None:
                x11.XDestroyWindow(display, window)
            x11.XSync(display, 0)
        finally:
            x11.XCloseDisplay(display)

    @staticmethod
    def _configure_signatures(x11) -> None:
        x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
        x11.XOpenDisplay.restype = ctypes.c_void_p
        x11.XDefaultScreen.argtypes = [ctypes.c_void_p]
        x11.XDefaultScreen.restype = ctypes.c_int
        x11.XDisplayWidth.argtypes = [ctypes.c_void_p, ctypes.c_int]
        x11.XDisplayWidth.restype = ctypes.c_int
        x11.XDisplayHeight.argtypes = [ctypes.c_void_p, ctypes.c_int]
        x11.XDisplayHeight.restype = ctypes.c_int
        x11.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
        x11.XDefaultRootWindow.restype = ctypes.c_ulong
        x11.XBlackPixel.argtypes = [ctypes.c_void_p, ctypes.c_int]
        x11.XBlackPixel.restype = ctypes.c_ulong
        x11.XWhitePixel.argtypes = [ctypes.c_void_p, ctypes.c_int]
        x11.XWhitePixel.restype = ctypes.c_ulong
        x11.XCreateSimpleWindow.argtypes = [
            ctypes.c_void_p,
            ctypes.c_ulong,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_uint,
            ctypes.c_uint,
            ctypes.c_uint,
            ctypes.c_ulong,
            ctypes.c_ulong,
        ]
        x11.XCreateSimpleWindow.restype = ctypes.c_ulong
        x11.XSelectInput.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_long]
        x11.XSelectInput.restype = ctypes.c_int
        x11.XCreateGC.argtypes = [
            ctypes.c_void_p,
            ctypes.c_ulong,
            ctypes.c_ulong,
            ctypes.c_void_p,
        ]
        x11.XCreateGC.restype = ctypes.c_void_p
        x11.XFreeGC.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        x11.XFreeGC.restype = ctypes.c_int
        x11.XMapRaised.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        x11.XMapRaised.restype = ctypes.c_int
        x11.XDestroyWindow.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        x11.XDestroyWindow.restype = ctypes.c_int
        x11.XClearWindow.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        x11.XClearWindow.restype = ctypes.c_int
        x11.XSetForeground.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong]
        x11.XSetForeground.restype = ctypes.c_int
        x11.XDrawArc.argtypes = [
            ctypes.c_void_p,
            ctypes.c_ulong,
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_uint,
            ctypes.c_uint,
            ctypes.c_int,
            ctypes.c_int,
        ]
        x11.XDrawArc.restype = ctypes.c_int
        x11.XDrawLine.argtypes = [
            ctypes.c_void_p,
            ctypes.c_ulong,
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
        ]
        x11.XDrawLine.restype = ctypes.c_int
        x11.XPending.argtypes = [ctypes.c_void_p]
        x11.XPending.restype = ctypes.c_int
        x11.XNextEvent.argtypes = [ctypes.c_void_p, ctypes.POINTER(_XEvent)]
        x11.XNextEvent.restype = ctypes.c_int
        x11.XFlush.argtypes = [ctypes.c_void_p]
        x11.XFlush.restype = ctypes.c_int
        x11.XSync.argtypes = [ctypes.c_void_p, ctypes.c_int]
        x11.XSync.restype = ctypes.c_int
        x11.XCloseDisplay.argtypes = [ctypes.c_void_p]
        x11.XCloseDisplay.restype = ctypes.c_int


class LegacyXSystemChromeBackend:
    """SystemChromeBackend implementation for Greia's provisional X session."""

    backend_id = "legacy-x11-system-chrome"

    def __init__(self, *, bridge: LegacyXChromeBridge | None = None) -> None:
        self._bridge = bridge or CtypesLegacyXChromeBridge()
        self._session_id: str | None = None
        self._layout: ActivitySystemChromeLayout | None = None
        self._visible = False

    def prepare(
        self,
        session_id: str,
        *,
        back_available: bool,
        metrics: Any = None,
    ) -> None:
        if self._session_id is not None:
            raise RuntimeError("Legacy-X system chrome already owns a session")
        # Bridges predating the metrics seam keep working unchanged: the
        # metrics keyword crosses the bridge boundary only when the
        # composition owner actually injected metrics.
        if metrics is None:
            layout = self._bridge.prepare(back_available=bool(back_available))
        else:
            layout = self._bridge.prepare(
                back_available=bool(back_available), metrics=metrics
            )
        self._session_id = session_id
        self._layout = layout
        self._visible = False

    def show(self, session_id: str) -> None:
        self._require_session(session_id)
        if self._visible:
            raise RuntimeError("Legacy-X system chrome is already visible")
        self._bridge.show()
        self._visible = True

    def poll_action(self, session_id: str) -> SystemNavigationAction | None:
        self._require_session(session_id)
        if not self._visible:
            return None
        layout = self._layout
        if layout is None:
            raise RuntimeError("Legacy-X system chrome has no layout")
        point = self._bridge.poll_pointer_release()
        if point is None:
            return None
        return layout.action_at(*point)

    def hide(self, session_id: str) -> None:
        # Coordinator recovery may call hide twice after a show failure: once as
        # the immediate best-effort rollback and once while aborting the failed
        # lease. No active window means cleanup already succeeded.
        if self._session_id is None:
            return
        self._require_session(session_id)
        try:
            self._bridge.hide()
        finally:
            self._session_id = None
            self._layout = None
            self._visible = False

    def _require_session(self, session_id: str) -> None:
        if self._session_id != session_id:
            raise RuntimeError("Legacy-X system chrome session mismatch")


__all__ = [
    "CtypesLegacyXChromeBridge",
    "LegacyXChromeBridge",
    "LegacyXSystemChromeBackend",
    "layout_for_surface_with_metrics",
]
