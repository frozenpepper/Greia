from __future__ import annotations

import os
from typing import Mapping

from .display_session import DisplayTransport, DisplayTransportKind


class LegacyXDisplaySessionBackend:
    """Compatibility display/session mechanics for Greia's current xinit path.

    The current Xorg session already keeps Greia Shell and the child Activity in
    the same X server. This backend therefore does not create a second window
    manager/session mechanism: prepare describes the exact child transport,
    present preserves the existing "shell stops repainting while child runs"
    behavior, and restore returns ownership semantically to the Shell.

    It is intentionally provisional. A future direct/compositor backend must
    replace this class beneath DisplaySessionCoordinator without changing the
    Activity lifecycle contract.
    """

    backend_id = "legacy-x11-session"
    transport_kind = DisplayTransportKind.LEGACY_X11

    def __init__(self, environment: Mapping[str, str] | None = None):
        self._environment = os.environ if environment is None else environment

    def prepare_activity(self, session_id: str) -> DisplayTransport:
        del session_id  # identity is validated/owned by DisplaySessionCoordinator
        display = self._environment.get("DISPLAY")
        if not display:
            raise RuntimeError("legacy X11 session has no DISPLAY endpoint")
        if self._environment.get("WAYLAND_DISPLAY"):
            raise RuntimeError("legacy X11 session refuses simultaneous Wayland transport")

        selected = self._environment.get("SDL_VIDEODRIVER")
        if selected and selected != "x11":
            raise RuntimeError(
                f"legacy X11 session has conflicting SDL_VIDEODRIVER {selected!r}"
            )

        xauthority = self._environment.get("XAUTHORITY") or None
        return DisplayTransport(
            kind=DisplayTransportKind.LEGACY_X11,
            sdl_video_driver="x11",
            display=display,
            xauthority=xauthority,
        )

    def present_activity(self, session_id: str) -> None:
        del session_id
        # Existing X compatibility semantics require no display-server switch.
        # LauncherApplication already stops repainting while the Activity runs.

    def restore_shell(self, session_id: str) -> None:
        del session_id
        # Existing X compatibility semantics require no display-server switch.
        # The Shell repaints on the next launcher frame after Activity cleanup.
