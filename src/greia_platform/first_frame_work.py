"""Deferred Activity start-up work released by the first presented frame.

Launch latency on the reference Atom N270 is dominated by work an Activity does
before its first frame even though the first screen does not need it (the
2026-10-16 Acer re-sweep measured 2-9 s of "content build", most of it
synthesising sound effects in pure Python). Such work may register here and
starts only once the Activity reports READY through
:func:`greia_platform.activity_api.mark_activity_ready`, which every Activity
calls immediately after its first ``display.flip``.

The queue holds weak references only, so an owner that is discarded before
READY (for example in unit tests) is never kept alive or started. Work
registered after READY starts immediately. Nothing here creates threads; an
owner decides how its own work runs (see
:class:`greia_platform.pygame_audio.DeferredSoundBank`).
"""

from __future__ import annotations

import threading
import weakref
from typing import Callable


class FirstFrameWork:
    """One process's bounded list of callbacks waiting for the first frame."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._pending: list[weakref.WeakMethod[Callable[[], None]]] = []
        self._released = False

    @property
    def released(self) -> bool:
        return self._released

    def after_first_frame(self, callback: Callable[[], None]) -> None:
        """Run the bound method ``callback`` at READY (now, if already READY)."""

        with self._lock:
            if not self._released:
                self._pending = [ref for ref in self._pending if ref() is not None]
                self._pending.append(weakref.WeakMethod(callback))
                return
        callback()

    def release(self) -> None:
        """Mark the first frame presented and run every live pending callback."""

        with self._lock:
            pending, self._pending = self._pending, []
            self._released = True
        for ref in pending:
            callback = ref()
            if callback is not None:
                callback()


#: The Activity process's queue. One Activity runs per process, so READY is a
#: process-wide fact; tests may construct their own :class:`FirstFrameWork`.
FIRST_FRAME_WORK = FirstFrameWork()


def after_first_frame(callback: Callable[[], None]) -> None:
    FIRST_FRAME_WORK.after_first_frame(callback)


def release_first_frame_work() -> None:
    FIRST_FRAME_WORK.release()
