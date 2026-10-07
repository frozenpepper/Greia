from __future__ import annotations

import queue
import threading
from typing import Any

from greia_platform.system_chrome import (
    ActivitySystemChromeLayout,
    SystemNavigationAction,
)

from .remote_bridge import SimulatorRemoteBridge


class SimulatorSystemChromeRemoteBridge(SimulatorRemoteBridge):
    """Remote bridge that separates Greia system input from Activity input.

    The ordinary Simulator bridge is the transport for both Shell and Activity
    input. During an active Activity, however, the protected Greia chrome region
    must be consumed before Activity delivery. This specialization keeps one
    tiny system-navigation queue beside the existing bounded Activity queue.

    Rendering remains in the Greia-owned Python display bootstrap, which draws
    the canonical overlay after Activity flip/update calls. This bridge owns the
    complementary input boundary: protected pointer events never enter the
    Activity event queue, even when an Activity refuses to call event.get().
    """

    _MAX_SYSTEM_ACTIONS = 1

    def __init__(self, port: int, host: str = "127.0.0.1") -> None:
        super().__init__(port=port, host=host)
        self._system_chrome_lock = threading.Lock()
        self._system_chrome_session_id: str | None = None
        self._system_chrome_layout: ActivitySystemChromeLayout | None = None
        self._system_navigation: queue.Queue[SystemNavigationAction] = queue.Queue(
            maxsize=self._MAX_SYSTEM_ACTIONS
        )
        self._shell_modal_session_id: str | None = None

    def activate_system_chrome(
        self,
        session_id: str,
        layout: ActivitySystemChromeLayout,
    ) -> None:
        with self._system_chrome_lock:
            if self._system_chrome_session_id is not None:
                raise RuntimeError("Simulator system chrome is already active")
            self._clear_system_navigation_locked()
            self._system_chrome_session_id = session_id
            self._system_chrome_layout = layout

    def activate_shell_modal(self, session_id: str) -> None:
        """Divert ordinary remote input/frame authority from Activity to Shell."""
        with self._system_chrome_lock:
            if self._system_chrome_session_id != session_id:
                raise RuntimeError("Simulator modal requires active matching system chrome")
            if self._shell_modal_session_id is not None:
                raise RuntimeError("Simulator Shell modal is already active")
            self._shell_modal_session_id = session_id

    def deactivate_shell_modal(self, session_id: str) -> None:
        with self._system_chrome_lock:
            if self._shell_modal_session_id is None:
                return
            if self._shell_modal_session_id != session_id:
                raise RuntimeError("Simulator Shell modal session mismatch")
            self._shell_modal_session_id = None

    def shell_modal_active(self, session_id: str | None = None) -> bool:
        with self._system_chrome_lock:
            if session_id is None:
                return self._shell_modal_session_id is not None
            return self._shell_modal_session_id == session_id

    def deactivate_system_chrome(self, session_id: str) -> None:
        with self._system_chrome_lock:
            if self._system_chrome_session_id is None:
                return
            if self._system_chrome_session_id != session_id:
                raise RuntimeError("Simulator system chrome session mismatch")
            self._shell_modal_session_id = None
            self._system_chrome_session_id = None
            self._system_chrome_layout = None
            self._clear_system_navigation_locked()

    def poll_system_navigation(
        self,
        session_id: str,
    ) -> SystemNavigationAction | None:
        with self._system_chrome_lock:
            if self._system_chrome_session_id != session_id:
                raise RuntimeError("Simulator system chrome session mismatch")
        try:
            return self._system_navigation.get_nowait()
        except queue.Empty:
            return None

    def queue_mouse(
        self,
        x: int,
        y: int,
        action: str = "click",
        button: int = 1,
    ) -> None:
        """Route protected pointer input to Greia before Activity delivery."""

        x = int(x)
        y = int(y)
        action = str(action).lower()
        button = int(button)

        with self._system_chrome_lock:
            layout = self._system_chrome_layout
            protected = (
                layout is not None and layout.protected_region.contains(x, y)
            )
            navigation = layout.action_at(x, y) if protected and layout is not None else None

        if protected:
            # Consume the complete protected region, not only the visible Home
            # glyph. This matches the platform layout contract and prevents
            # Activity drag/click state from receiving reserved-region input.
            if (
                navigation is not None
                and button == 1
                and action in {"up", "click"}
            ):
                try:
                    self._system_navigation.put_nowait(navigation)
                except queue.Full:
                    # Exactly one pending Greia navigation request is useful;
                    # repeated releases before the supervisor polls coalesce.
                    pass
            return

        super().queue_mouse(x, y, action=action, button=button)

    def drain_events(self) -> list[dict[str, Any]]:
        """Activity transport receives no ordinary input while Shell modal owns it."""
        with self._system_chrome_lock:
            if self._shell_modal_session_id is not None:
                return []
        return super().drain_events()

    def capture_frame(self, surface: Any, pygame: Any, mode: str = "profiles") -> None:
        # Shell modal frames are the authoritative synthetic display until
        # dismissal; Activity uploads are ignored by set_external_frame_png.
        if self.shell_modal_active():
            mode = "creations_picker"
        super().capture_frame(surface, pygame, mode=mode)

    def set_external_frame_png(self, png_bytes: bytes, mode: str = "activity") -> None:
        if self.shell_modal_active():
            return
        super().set_external_frame_png(png_bytes, mode=mode)

    def _clear_system_navigation_locked(self) -> None:
        while True:
            try:
                self._system_navigation.get_nowait()
            except queue.Empty:
                return


class SimulatorSystemChromeBackend:
    """SystemChromeBackend for the synthetic Greia device.

    The backend uses the exact same SystemChromeCoordinator and lifecycle bridge
    as installed Greia. It does not terminate Activities directly. A Home action
    therefore requests graceful stop first and lets ActivitySupervisor perform
    its normal bounded forced-stop escalation for a non-cooperative Activity.
    """

    backend_id = "simulator-system-chrome"

    def __init__(
        self,
        bridge: SimulatorSystemChromeRemoteBridge,
        *,
        width: int,
        height: int,
    ) -> None:
        self._bridge = bridge
        self._width = int(width)
        self._height = int(height)
        self._session_id: str | None = None
        self._layout: ActivitySystemChromeLayout | None = None
        self._visible = False

    def prepare(self, session_id: str, *, back_available: bool) -> None:
        if self._session_id is not None:
            raise RuntimeError("Simulator system chrome already owns a session")
        self._layout = ActivitySystemChromeLayout.for_surface(
            self._width,
            self._height,
            back_available=bool(back_available),
        )
        self._session_id = session_id
        self._visible = False

    def show(self, session_id: str) -> None:
        self._require_session(session_id)
        if self._visible:
            raise RuntimeError("Simulator system chrome is already visible")
        layout = self._layout
        if layout is None:
            raise RuntimeError("Simulator system chrome has no layout")
        self._bridge.activate_system_chrome(session_id, layout)
        self._visible = True

    def ensure_visible(self, session_id: str) -> None:
        self._require_session(session_id)
        if not self._visible:
            raise RuntimeError("Simulator system chrome is not visible")
        # Protected input authority already lives in the remote bridge and
        # remains active while the Shell modal owns ordinary input.

    def poll_action(self, session_id: str) -> SystemNavigationAction | None:
        self._require_session(session_id)
        if not self._visible:
            return None
        return self._bridge.poll_system_navigation(session_id)

    def hide(self, session_id: str) -> None:
        if self._session_id is None:
            return
        self._require_session(session_id)
        try:
            if self._visible:
                self._bridge.deactivate_system_chrome(session_id)
        finally:
            self._session_id = None
            self._layout = None
            self._visible = False

    def _require_session(self, session_id: str) -> None:
        if self._session_id != session_id:
            raise RuntimeError("Simulator system chrome session mismatch")


__all__ = [
    "SimulatorSystemChromeBackend",
    "SimulatorSystemChromeRemoteBridge",
]
