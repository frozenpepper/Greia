"""Simulator implementation of Greia's runtime-neutral Shell modal backend."""
from __future__ import annotations

from typing import Any

from greia_launcher.shell_window import ShellActivityModalLease


class SimulatorShellWindowController:
    """Use the existing remote display transport as trusted modal authority.

    No native X11/AppKit window IDs are involved. The exact Activity session/PID
    still comes from the real supervisor; the remote bridge controls whether
    ordinary synthetic-device input/frame delivery belongs to Activity or Shell.
    """

    backend_id = "simulator-shell-window"

    def __init__(self, bridge: Any | None) -> None:
        self._bridge = bridge
        self._generation = 0
        self._lease: ShellActivityModalLease | None = None
        self._visible = False

    def after_window_created(self, pygame: Any) -> bool:
        del pygame
        return True

    def after_activity_return(self, pygame: Any) -> bool:
        del pygame
        if self._lease is not None:
            self.abandon_activity_modal(self._lease)
        return True

    def prepare_activity_modal(
        self,
        pygame: Any,
        *,
        session_id: str,
        activity_pid: int,
    ) -> ShellActivityModalLease | None:
        del pygame
        if self._bridge is None or self._lease is not None:
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
        # System chrome proves the remote bridge owns this exact live Activity
        # session before a Shell modal can be prepared.
        active = getattr(self._bridge, "_system_chrome_session_id", None)
        if active != session_id:
            return None
        self._generation += 1
        lease = ShellActivityModalLease(session_id, self._generation, activity_pid)
        self._lease = lease
        self._visible = False
        return lease

    def _owns(self, lease: ShellActivityModalLease) -> bool:
        return lease is self._lease

    def show_activity_modal(self, lease: ShellActivityModalLease) -> bool:
        if not self._owns(lease) or self._visible or self._bridge is None:
            return False
        try:
            self._bridge.activate_shell_modal(lease.session_id)
        except Exception:
            return False
        self._visible = True
        return True

    def dismiss_activity_modal(self, lease: ShellActivityModalLease) -> bool:
        if not self._owns(lease) or self._bridge is None:
            return False
        if not self._visible:
            return True
        try:
            self._bridge.deactivate_shell_modal(lease.session_id)
        except Exception:
            return False
        self._visible = False
        return True

    def abandon_activity_modal(self, lease: ShellActivityModalLease) -> None:
        if not self._owns(lease):
            return
        if self._visible and self._bridge is not None:
            try:
                self._bridge.deactivate_shell_modal(lease.session_id)
            except Exception:
                pass
        self._visible = False
        self._lease = None


__all__ = ["SimulatorShellWindowController"]
