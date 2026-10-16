"""Shared frame governance for Pygame Activities (ADR 0018 / ADR 0037).

Greia runs on a single-core Atom reference floor.  An Activity loop that
re-renders and flips the full 1024x600 frame 20-30 times a second while
nothing changes burns 60-130% CPU there (Acer sweep 2026-10-16), which costs
battery, heat, Shell responsiveness and the next Activity's launch time.

``FrameGovernor`` is the one platform-owned answer.  The Activity keeps its
own model and renderer and only *tells* the governor what happened:

* ``dirty=True`` / ``invalidate()`` — state changed, draw one frame;
* ``animating=True`` / ``animate_for(s)`` — essential motion (feedback,
  physics, a moving character the child is steering): full ``animation_fps``;
* ``ambient=True`` — decorative idle motion (bubbles, clouds, breathing
  characters): full rate for ``ambient_after_seconds`` after the last child
  input, then the reduced ``ambient_fps``.  On the reference floor
  ``ambient_fps`` is 0: decorative motion freezes on its last frame (a
  static screen, no presents) and resumes at full rate on the next input;
* pointer motion seen through ``events()`` — a cheap pointer-only refresh
  (``FrameKind.POINTER``) so Greia's platform pointer still follows promptly.

``frame()`` answers what to present this iteration (``SKIP``, ``POINTER`` or
``FULL``) and never exceeds ``animation_fps``.  ``wait()`` replaces
``Clock.tick``: it sleeps until the next frame is due while animating, and
otherwise sleeps a short ``idle_poll_seconds`` so timers in ``step()`` (voice
completion, hints, autosave) still run, without presenting anything.

``pygame.event.wait(timeout)`` is deliberately not used: Pygame 2.1.3+
implements it as a 1 ms poll loop, which costs more than a short sleep.

Typical loop::

    frames = FrameGovernor()
    while running and not activity_stop_requested():
        for event in frames.events():
            handle(event)
        animating = step()
        kind = frames.frame(dirty=dirty, animating=animating)
        if kind is FrameKind.FULL:
            render(); canvas.present(); pygame.display.flip(); dirty = False
        elif kind is FrameKind.POINTER:
            canvas.present_pointer()
        frames.wait()
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import os
import time
from typing import Callable, Mapping

import pygame

FRAME_PROFILE_ENV = "GREIA_FRAME_PROFILE"

# Floor for a sleep after an iteration that presented nothing (anti-spin).
_MIN_IDLE_SLEEP = 0.002

# Raw input that counts as "the child is here" for the ambient throttle.
_INPUT_EVENT_NAMES = (
    "KEYDOWN",
    "KEYUP",
    "TEXTINPUT",
    "MOUSEBUTTONDOWN",
    "MOUSEBUTTONUP",
    "MOUSEMOTION",
    "MOUSEWHEEL",
    "FINGERDOWN",
    "FINGERUP",
    "FINGERMOTION",
    "JOYAXISMOTION",
    "JOYBUTTONDOWN",
    "JOYBUTTONUP",
    "JOYHATMOTION",
    "CONTROLLERAXISMOTION",
    "CONTROLLERBUTTONDOWN",
    "CONTROLLERBUTTONUP",
)
_INPUT_EVENTS = frozenset(
    getattr(pygame, name) for name in _INPUT_EVENT_NAMES if hasattr(pygame, name)
)


class FrameKind(Enum):
    """What the Activity should present on this loop iteration."""

    SKIP = "skip"  # nothing changed: do not render, present or flip
    POINTER = "pointer"  # only the platform pointer moved
    FULL = "full"  # render the scene, present and flip


@dataclass(frozen=True, slots=True)
class FramePolicy:
    """Frame-rate budget for one hardware class.

    ``animation_fps`` caps every presented frame (dirty, animation or pointer).
    ``ambient_fps`` applies to decorative motion once no input arrived for
    ``ambient_after_seconds``; ``0`` means decorative motion stops entirely
    (the last frame stays on screen) until the next child input.  On the
    Atom N270 even a 10 fps full 1024x600 redraw costs tens of ms per frame,
    so the reference floor uses 0.  ``idle_poll_seconds`` bounds how long a static
    loop sleeps between event/timer polls (and so the worst-case extra input
    latency on a static screen).
    """

    animation_fps: float = 30.0
    ambient_fps: float = 12.0
    ambient_after_seconds: float = 8.0
    idle_poll_seconds: float = 0.05
    hint_animation_cap_seconds: float | None = None

    def __post_init__(self) -> None:
        if not 1.0 <= self.animation_fps <= 120.0:
            raise ValueError("animation_fps must be within 1..120")
        if self.ambient_fps != 0.0 and not 1.0 <= self.ambient_fps <= self.animation_fps:
            raise ValueError("ambient_fps must be 0 (static) or within 1..animation_fps")
        if self.ambient_after_seconds < 0.0:
            raise ValueError("ambient_after_seconds must not be negative")
        if not 0.005 <= self.idle_poll_seconds <= 0.25:
            raise ValueError("idle_poll_seconds must be within 0.005..0.25")
        if self.hint_animation_cap_seconds is not None and self.hint_animation_cap_seconds <= 0.0:
            raise ValueError("hint_animation_cap_seconds must be positive")

    @property
    def frame_period(self) -> float:
        return 1.0 / self.animation_fps

    @property
    def ambient_period(self) -> float:
        """Seconds between throttled ambient frames (``inf`` when static)."""

        return float("inf") if self.ambient_fps == 0.0 else 1.0 / self.ambient_fps

    @property
    def ambient_static(self) -> bool:
        """True when throttled decorative motion presents nothing at all."""

        return self.ambient_fps == 0.0

    def hint_animation_seconds(self, nominal: float) -> float:
        """Length of an idle-hint animation on this hardware class.

        A hint animation is essential motion at full ``animation_fps``; on the
        reference floor ``hint_animation_cap_seconds`` keeps it short so a hint
        cannot hold the CPU for several seconds (ADR 0037 section 6a).
        """

        cap = self.hint_animation_cap_seconds
        return nominal if cap is None else min(nominal, cap)

    @classmethod
    def standard(cls) -> "FramePolicy":
        return cls()

    @classmethod
    def reference_floor(cls) -> "FramePolicy":
        """Atom N270-class budget: fewer full frames; decoration stops when idle.

        A full-frame redraw + flip costs tens of ms on the Atom, so even a
        10 fps decorative loop kept Activities above 100% CPU (Acer re-sweep
        at 0f560c2e).  After ``ambient_after_seconds`` without input the
        decorative scene therefore freezes (``ambient_fps=0``) and resumes
        instantly on the next input.
        """

        return cls(
            animation_fps=24.0,
            ambient_fps=0.0,
            ambient_after_seconds=6.0,
            hint_animation_cap_seconds=1.5,
        )

    @classmethod
    def for_profile(cls, name: str) -> "FramePolicy":
        normalized = name.strip().lower().replace("_", "-")
        if normalized in {"reference-floor", "low"}:
            return cls.reference_floor()
        if normalized in {"standard", "default", ""}:
            return cls.standard()
        raise ValueError(f"unknown frame profile: {name!r}")

    @classmethod
    def from_environment(
        cls,
        environ: Mapping[str, str] | None = None,
        *,
        cpu_count: int | None = None,
    ) -> "FramePolicy":
        """Select the policy for this device.

        ``GREIA_FRAME_PROFILE`` (``standard`` / ``reference-floor``) wins when
        set and valid.  Otherwise a device with at most two logical CPUs (the
        Atom N270 reports 2 hyperthreads) gets the reference-floor budget.
        """

        env = os.environ if environ is None else environ
        requested = env.get(FRAME_PROFILE_ENV, "").strip()
        if requested:
            try:
                return cls.for_profile(requested)
            except ValueError:
                pass
        count = os.cpu_count() if cpu_count is None else cpu_count
        if count is not None and count <= 2:
            return cls.reference_floor()
        return cls.standard()


class FrameGovernor:
    """Decide when an Activity presents, and sleep the loop in between.

    One governor per Activity loop.  It owns only timing state (no surfaces),
    so it is cheap and safe to construct before the display exists.  Clock and
    sleep are injectable for deterministic tests.
    """

    def __init__(
        self,
        policy: FramePolicy | None = None,
        *,
        redraw_on_input: bool = False,
        keepalive_seconds: float | None = None,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if keepalive_seconds is not None and keepalive_seconds <= 0.0:
            raise ValueError("keepalive_seconds must be positive")
        self.policy = policy if policy is not None else FramePolicy.from_environment()
        self._clock = clock
        self._sleep = sleep
        # Migration aids for loops that historically redrew every frame and
        # have no complete dirty tracking: every non-motion input (and motion
        # with a button held, i.e. a drag) invalidates, and ``keepalive``
        # bounds how stale a state change missed by the Activity can get.
        self._redraw_on_input = bool(redraw_on_input)
        self._keepalive = keepalive_seconds
        now = clock()
        self._dirty = True  # the first frame is always presented
        self._pointer = False
        self._animate_until = now
        self._last_input = now
        self._last_present: float | None = None
        self._next_due: float | None = None  # when the loop should wake next
        self._last_wake: float | None = None
        self._last_kind = FrameKind.FULL
        self.frames_presented = 0

    # -- producers --------------------------------------------------------

    def invalidate(self) -> None:
        """Request one full frame (state changed outside the loop's dirty flag)."""

        self._dirty = True

    def animate_for(self, seconds: float) -> None:
        """Run at the full animation rate for ``seconds`` from now."""

        self._animate_until = max(self._animate_until, self._clock() + max(0.0, float(seconds)))

    def note_event(self, event: pygame.event.Event) -> None:
        """Record child input: resets the ambient timer; motion moves the pointer."""

        kind = getattr(event, "type", None)
        if kind in _INPUT_EVENTS:
            self._last_input = self._clock()
            if kind == pygame.MOUSEMOTION:
                self._pointer = True
                if self._redraw_on_input and any(getattr(event, "buttons", ()) or ()):
                    self._dirty = True
            elif self._redraw_on_input:
                self._dirty = True
        elif kind in (pygame.VIDEORESIZE, getattr(pygame, "VIDEOEXPOSE", -1), getattr(pygame, "WINDOWEXPOSED", -1)):
            self._dirty = True

    def note_input(self) -> None:
        """Record child input that did not arrive as a Pygame event."""

        self._last_input = self._clock()

    def events(self) -> list[pygame.event.Event]:
        """Drain the Pygame queue (looked up at call time) and note each event."""

        events = pygame.event.get()
        for event in events:
            self.note_event(event)
        return events

    # -- loop -------------------------------------------------------------

    @property
    def ambient_throttled(self) -> bool:
        """True once no input arrived for ``ambient_after_seconds``."""

        return self._clock() - self._last_input >= self.policy.ambient_after_seconds

    @property
    def ambient_frozen(self) -> bool:
        """True while decorative motion is stopped (static policy, child idle).

        Loops that pace decoration themselves (e.g. an 8 fps cloud drift sent
        as ``dirty``) or simulate purely decorative actors (wandering critters
        a resting player cannot meet) check this to stop that work as well, so
        the scene resumes where it froze instead of jumping on the next input.
        """

        return self.policy.ambient_static and self.ambient_throttled

    def frame(self, *, dirty: bool = False, animating: bool = False, ambient: bool = False) -> FrameKind:
        """Return what to present now; the caller must honour FULL/POINTER.

        ``dirty``/``animating`` (or ``invalidate``/``animate_for``) request
        full-rate frames; ``ambient`` alone drops to ``ambient_fps`` once the
        child has been idle; pointer motion alone yields ``POINTER``.  Every
        presented frame is capped at ``animation_fps``; a request that is not
        yet due stays pending and is answered by a later call.
        """

        now = self._clock()
        essential = dirty or self._dirty or animating or now < self._animate_until
        if (
            self._keepalive is not None
            and self._last_present is not None
            and now - self._last_present >= self._keepalive
        ):
            essential = True
        period = self.policy.frame_period
        if ambient and not essential and self.ambient_throttled:
            if self.policy.ambient_static:
                # Static decoration: the last frame stays; only the pointer
                # (and essential work) may still present.
                ambient = False
            else:
                period = self.policy.ambient_period
        if not (essential or ambient or self._pointer):
            self._next_due = None
            self._last_kind = FrameKind.SKIP
            return FrameKind.SKIP
        last = self._last_present
        # A 2 ms slack keeps a sleeping loop from missing its slot by jitter.
        if last is not None and now - last < period - 0.002:
            self._next_due = last + period
            self._last_kind = FrameKind.SKIP
            return FrameKind.SKIP
        kind = FrameKind.FULL if (essential or ambient) else FrameKind.POINTER
        self._last_kind = kind
        self._dirty = False
        self._pointer = False
        self._last_present = now
        # Wake at frame cadence once more: motion/input usually continues.
        self._next_due = now + period
        self.frames_presented += 1
        return kind

    def wait(self, *, polling: bool = False) -> float:
        """Sleep until the next frame or poll is due; return the seconds slept.

        Replaces ``Clock.tick``.  The sleep never exceeds
        ``idle_poll_seconds`` so input on a static or ambient-throttled screen
        is noticed within that bound.  ``polling=True`` keeps the loop at frame
        cadence without presenting, e.g. while a held stick generates
        navigation repeats.
        """

        now = self._clock()
        # ``frame()`` re-arms the wake time every iteration; consume it so a
        # loop that polls without presenting never sleeps on a stale value.
        due, self._next_due = self._next_due, None
        deadline = due if due is not None else now + self.policy.idle_poll_seconds
        if polling or self._dirty or self._pointer or now < self._animate_until:
            # Like Clock.tick: one period after the previous wake, so a
            # fixed-step simulation polled here keeps real-time cadence.
            cadence = (self._last_wake if self._last_wake is not None else now) + self.policy.frame_period
            deadline = min(deadline, max(now, cadence))
        delay = min(deadline - now, self.policy.idle_poll_seconds)
        if not polling and self._last_kind is FrameKind.SKIP:
            # Nothing was presented this iteration: never return without a
            # real sleep, so a loop that keeps asking for a frame that is not
            # due (or nothing at all) cannot spin the CPU.
            delay = max(delay, _MIN_IDLE_SLEEP)
        if delay > 0.0:
            self._sleep(delay)
        self._last_wake = self._clock()
        return max(0.0, delay)


__all__ = [
    "FRAME_PROFILE_ENV",
    "FrameGovernor",
    "FrameKind",
    "FramePolicy",
]
