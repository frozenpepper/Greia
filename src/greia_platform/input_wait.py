"""Wait for input on a static Activity screen without polling the loop.

A frame-governed Activity whose screen is static (nothing animating, nothing
due) has no reason to run its loop: ``events()``, ``step()``, ``frame()`` and
the lifecycle stop check together cost several ms per iteration on the Atom
N270 reference floor, and a 50 ms poll ran them 20 times a second (about 12%
CPU on a fully static screen, Acer sweep at 15212f44).  ``FrameGovernor``
therefore asks an :class:`InputWaiter` to block until input arrives or a
bounded timeout elapses.

Two implementations exist:

* :class:`SdlEventWaiter` blocks inside ``SDL_WaitEventTimeout`` on video
  drivers whose SDL backend has a real kernel wait (X11, Wayland, Cocoa,
  Windows).  The thread sleeps until the display connection has input or
  another thread/timer pushes an event, so input wakes it immediately.
  ``pygame.event.wait(timeout)`` is not used: Pygame 2.1.3+ reimplements it
  as a 1 ms poll loop.  The same 1 ms loop is what SDL itself falls back to
  when a joystick/sensor is open or the driver has no wait (dummy, KMSDRM),
  so the waiter declines in those cases.
* :class:`SlicedInputWaiter` is the portable fallback: short sleeps with a
  cheap queue peek between them.  The Activity loop still runs only once per
  timeout; input is noticed within one slice (the governor's
  ``idle_poll_seconds``, the previous worst-case latency).

:class:`PlatformInputWaiter` picks the SDL wait whenever it is usable and the
sliced wait otherwise, re-checking cheaply on every call (a controller can be
plugged in at any time).
"""

from __future__ import annotations

import ctypes
import glob
import os
import time
from typing import Callable, Protocol

import pygame

_SDL_INIT_JOYSTICK = 0x00000200
_SDL_INIT_VIDEO = 0x00000020
_SDL_INIT_SENSOR = 0x00008000
# SDL 2.0.18 is the first release whose SDL_WaitEventTimeout blocks in the
# video backend instead of polling every millisecond.
_MIN_SDL_VERSION = (2, 0, 18)
_BLOCKING_DRIVERS = frozenset({"x11", "wayland", "cocoa", "windows"})
# A sliced wait never issues a sub-0.1 ms tail sleep (float residue).
_SLICE_EPSILON = 1e-4


class InputWaiter(Protocol):
    """Blocks the Activity loop until input is queued or ``timeout`` elapses."""

    def wait(self, timeout: float) -> bool:
        """Return True as soon as an event is queued, False on timeout."""


def queue_has_events() -> bool:
    """Pump SDL and report whether any event is queued (False before video init)."""

    try:
        if not pygame.display.get_init():
            return False
        return bool(pygame.event.peek())
    except pygame.error:
        return False


class SlicedInputWaiter:
    """Portable wait: sleep in ``slice_seconds`` steps, peeking the queue between."""

    def __init__(
        self,
        slice_seconds: float,
        *,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
        has_events: Callable[[], bool] = queue_has_events,
    ) -> None:
        if slice_seconds <= 0.0:
            raise ValueError("slice_seconds must be positive")
        self._slice = float(slice_seconds)
        self._sleep = sleep
        self._clock = clock
        self._has_events = has_events

    def wait(self, timeout: float) -> bool:
        end = self._clock() + max(0.0, timeout)
        while True:
            if self._has_events():
                return True
            remaining = end - self._clock()
            if remaining <= _SLICE_EPSILON:
                return False
            self._sleep(min(self._slice, remaining))


def sdl_library_candidates() -> list[str]:
    """Paths/sonames that may name the SDL2 instance Pygame already loaded."""

    package = os.path.dirname(pygame.__file__)
    bundled = sorted(glob.glob(os.path.join(package, ".dylibs", "libSDL2-2*.dylib")))
    bundled += sorted(glob.glob(os.path.join(os.path.dirname(package), "pygame.libs", "libSDL2-2*")))
    return bundled + ["libSDL2-2.0.so.0", "libSDL2-2.0.0.dylib", "SDL2.dll"]


def load_initialized_sdl() -> ctypes.CDLL | None:
    """Return the SDL2 library Pygame initialized, or None.

    A candidate is accepted only when its ``SDL_WasInit`` reports the video
    subsystem: a second, uninitialized copy of SDL (another soname on disk)
    is never used.
    """

    for candidate in sdl_library_candidates():
        try:
            library = ctypes.CDLL(candidate)
            was_init = library.SDL_WasInit
            was_init.argtypes = [ctypes.c_uint32]
            was_init.restype = ctypes.c_uint32
            if not was_init(_SDL_INIT_VIDEO):
                continue
            library.SDL_WaitEventTimeout.argtypes = [ctypes.c_void_p, ctypes.c_int]
            library.SDL_WaitEventTimeout.restype = ctypes.c_int
            library.SDL_NumJoysticks.argtypes = []
            library.SDL_NumJoysticks.restype = ctypes.c_int
            library.SDL_NumSensors.argtypes = []
            library.SDL_NumSensors.restype = ctypes.c_int
            return library
        except (OSError, AttributeError):
            continue
    return None


class SdlEventWaiter:
    """Block in ``SDL_WaitEventTimeout(NULL, ms)``; the event stays queued.

    ``usable()`` is checked before every wait.  It declines (and the caller
    falls back) before a window exists, on drivers without a blocking wait,
    on SDL older than 2.0.18, and while a joystick or sensor is open, because
    SDL then polls every millisecond internally.
    """

    def __init__(self, loader: Callable[[], ctypes.CDLL | None] = load_initialized_sdl) -> None:
        self._loader = loader
        self._library: ctypes.CDLL | None = None
        self._resolved = False

    def usable(self) -> bool:
        try:
            if pygame.display.get_surface() is None:
                return False
            if pygame.display.get_driver() not in _BLOCKING_DRIVERS:
                return False
            if tuple(pygame.get_sdl_version()) < _MIN_SDL_VERSION:
                return False
        except pygame.error:
            return False
        if not self._resolved:
            self._resolved = True
            self._library = self._loader()
        library = self._library
        if library is None:
            return False
        if library.SDL_WasInit(_SDL_INIT_JOYSTICK) and library.SDL_NumJoysticks() > 0:
            return False
        if library.SDL_WasInit(_SDL_INIT_SENSOR) and library.SDL_NumSensors() > 0:
            return False
        return True

    def wait(self, timeout: float) -> bool:
        library = self._library
        if library is None:
            raise RuntimeError("SdlEventWaiter.wait() called while not usable")
        # ctypes releases the GIL for the call, so audio/worker threads run.
        return library.SDL_WaitEventTimeout(None, max(1, int(timeout * 1000.0))) == 1


class PlatformInputWaiter:
    """Default waiter: the SDL blocking wait when usable, else sliced sleeps."""

    def __init__(
        self,
        slice_seconds: float,
        *,
        sdl: SdlEventWaiter | None = None,
        fallback: SlicedInputWaiter | None = None,
    ) -> None:
        self._sdl = sdl if sdl is not None else SdlEventWaiter()
        self._fallback = fallback if fallback is not None else SlicedInputWaiter(slice_seconds)

    def wait(self, timeout: float) -> bool:
        if self._sdl.usable():
            return self._sdl.wait(timeout)
        return self._fallback.wait(timeout)


def audio_playing() -> bool:
    """True while the Activity's Pygame mixer is audible (speech, effects, music).

    Activities typically detect "speech finished" by polling a channel in
    ``step()``; while audio plays the governor keeps the short poll so that
    completion is noticed as promptly as before.
    """

    try:
        if not pygame.mixer.get_init():
            return False
        return bool(pygame.mixer.get_busy() or pygame.mixer.music.get_busy())
    except (pygame.error, AttributeError, NotImplementedError):
        return False


__all__ = [
    "InputWaiter",
    "PlatformInputWaiter",
    "SdlEventWaiter",
    "SlicedInputWaiter",
    "audio_playing",
    "load_initialized_sdl",
    "queue_has_events",
    "sdl_library_candidates",
]
