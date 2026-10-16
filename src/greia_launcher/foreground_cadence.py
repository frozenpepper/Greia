"""How often the Shell services a launched Activity from its foreground loop.

While an Activity owns the screen, the Shell's only jobs are lifecycle polling
(READY/exit/stop deadlines), protected Home/Back chrome, the controller Guide
button and, when visible, a trusted Shell modal (the Creations picker). It
used to do all of that at a fixed 50 Hz, which cost the Atom N270 reference
9-14 % CPU for the whole session, and it repainted the full-screen launch wait
screen at 10 fps while the starting Activity competed for the same core.

The cadence is a small state-dependent policy:

* STARTING: poll at 20 Hz (READY is noticed within 50 ms; a poll is only a
  waitpid + marker stat) but repaint the wait screen at 4 fps;
* RUNNING: 10 Hz. Home acts on the pointer *release* queued in the chrome
  window, so it is never lost, only answered within <= 100 ms;
* STOPPING: 20 Hz so a graceful exit returns to the Shell promptly;
* trusted modal visible/preparing: 50 Hz, it is interactive Shell UI.
"""

from __future__ import annotations

from dataclasses import dataclass

from .lifecycle import ActivitySessionState


@dataclass(frozen=True, slots=True)
class ActivityForegroundCadence:
    starting_poll_seconds: float = 0.05
    wait_screen_frame_seconds: float = 0.25
    running_poll_seconds: float = 0.10
    stopping_poll_seconds: float = 0.05
    modal_poll_seconds: float = 0.02

    def poll_interval(self, state: ActivitySessionState, *, modal_active: bool) -> float:
        """Seconds to sleep before the next foreground service pass."""

        if modal_active:
            return self.modal_poll_seconds
        if state is ActivitySessionState.RUNNING:
            return self.running_poll_seconds
        if state is ActivitySessionState.STOPPING:
            return self.stopping_poll_seconds
        return self.starting_poll_seconds

    def wait_screen_due(self, now: float, last_frame_at: float) -> bool:
        """Whether the pre-READY wait screen should present another frame."""

        return now - last_frame_at >= self.wait_screen_frame_seconds


__all__ = ["ActivityForegroundCadence"]
