"""Small Pygame PCM helpers for bounded Activity-generated sound effects.

Greia Activities may synthesize tiny feedback cues, but raw PCM must match the
mixer that Pygame actually opened. These helpers deliberately cover only that
format boundary plus :class:`DeferredSoundBank`, which keeps that synthesis off
the launch path (and, through :class:`SynthesisPacer`, from starving the
Activity loop after it); prerecorded speech and broader audio policy remain owned by
their existing services.
"""

from __future__ import annotations

from array import array
from collections.abc import Callable, Iterable, Iterator, Mapping
from contextlib import contextmanager
import struct
import sys
import threading
import time

import pygame

from .first_frame_work import after_first_frame

_PCM16_LE = struct.Struct("<h")
_pack_pcm16 = _PCM16_LE.pack


def current_pcm16_mixer_spec() -> tuple[int, int] | None:
    """Return ``(sample_rate, channel_count)`` for a supported active mixer."""

    spec = pygame.mixer.get_init()
    if spec is None:
        return None
    sample_rate, sample_format, channel_count = spec
    if sample_rate <= 0 or sample_format != -16 or not 1 <= channel_count <= 8:
        return None
    return (sample_rate, channel_count)


def append_mono_pcm16(raw: bytearray, sample: int, channel_count: int) -> None:
    """Append one signed 16-bit mono sample in the mixer's channel layout."""

    # Called once per sample by Activity synthesis loops: written for the
    # Atom N270 (5.1 us/sample here against 7.5 us with max/min/range checks).
    value = int(sample)
    if value > 32767:
        value = 32767
    elif value < -32768:
        value = -32768
    if channel_count == 1:
        raw += _pack_pcm16(value)
    elif 1 < channel_count <= 8:
        raw += _pack_pcm16(value) * channel_count
    else:
        raise ValueError("Pygame PCM channel count must be between 1 and 8")
    # Cooperative yield point for the background warm-up worker (see
    # SynthesisPacer): Activity factories call this once per sample, so it is
    # the one place every synthesis loop passes through. A countdown keeps the
    # per-sample cost to one global decrement; the pacer itself checks the
    # thread and the clock only every PACE_CHECK_SAMPLES samples.
    global _pace_countdown
    _pace_countdown -= 1
    if _pace_countdown <= 0:
        _pace_countdown = PACE_CHECK_SAMPLES
        pacer = getattr(_worker_local, "pacer", None)
        if pacer is not None:
            pacer.checkpoint()


def mono_pcm16_bytes(samples: Iterable[float], channel_count: int, *, scale: float = 1.0) -> bytes:
    """Pack mono samples (``value * scale``, clamped) into mixer-layout PCM16.

    The faster alternative to calling :func:`append_mono_pcm16` per sample:
    compute the samples into a list (a comprehension is cheapest), then pack
    them in one call. Packing 22,050 samples for a stereo mixer takes ~70 ms
    on the Atom N270 against ~150 ms through per-sample appends; the bytes are
    identical. Channel duplication is done with C-level array slicing.
    """

    if not 1 <= channel_count <= 8:
        raise ValueError("Pygame PCM channel count must be between 1 and 8")
    if scale == 1.0:
        values = [int(value) for value in samples]
    else:
        values = [int(value * scale) for value in samples]
    mono = array("h", [32767 if v > 32767 else -32768 if v < -32768 else v for v in values])
    if channel_count == 1:
        packed = mono
    else:
        packed = array("h", bytes(2 * len(mono) * channel_count))
        for channel in range(channel_count):
            packed[channel::channel_count] = mono
    if sys.byteorder != "little":
        packed.byteswap()
    return packed.tobytes()


#: Samples between two pacing checks inside ``append_mono_pcm16`` (~5-10 ms of
#: pure-Python synthesis on the Atom N270, well under 1 ms on a desktop).
PACE_CHECK_SAMPLES = 128
_pace_countdown = PACE_CHECK_SAMPLES
_worker_local = threading.local()


class SynthesisPacer:
    """Duty-cycle a background synthesis thread so the Activity loop keeps running.

    Pure-Python PCM synthesis holds the GIL. Measured on the reference Atom
    N270 (Acer, 2026-10-17, colline_allegre steered with arrow keys during the
    first 6 s after READY, 7 cues taking ~10 s to synthesize): with no warm-up
    at all the game presented 129 frames with 2 loop gaps over 100 ms; with
    the unpaced worker 91-95 frames and 20-23 such gaps (max ~250 ms), because
    every GIL-releasing call in the loop (each ``sleep``, ``flip`` and many
    blits) waited for the worker's next forced switch (5 ms by default);
    paced (4 ms work / 4 ms rest, 1 ms switch interval; six runs of the
    tuned variants) 109-125 frames and 3-6 gaps, while the warm-up takes
    ~17 s instead of ~10 s.

    The pacer is installed on the warm-up worker thread only. It lets the
    worker compute for ``work_seconds`` and then sleep ``rest_seconds``
    (releasing the GIL completely) at every checkpoint, and lowers the
    interpreter's switch interval to ``switch_interval`` while the worker
    runs, so a GIL hand-back to the Activity loop costs at most that long.
    Synthesis output is unchanged. A cue the Activity requests before the
    worker reaches it is built on the requesting thread at full speed (never
    paced); one the worker is building at that moment is finished without
    rests (:meth:`hurry`).
    """

    def __init__(
        self,
        *,
        work_seconds: float = 0.004,
        rest_seconds: float = 0.004,
        switch_interval: float | None = 0.001,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if work_seconds <= 0 or rest_seconds < 0:
            raise ValueError("pacer durations must be positive")
        if switch_interval is not None and switch_interval <= 0:
            raise ValueError("switch_interval must be positive")
        self.work_seconds = float(work_seconds)
        self.rest_seconds = float(rest_seconds)
        self.switch_interval = switch_interval
        self._clock = clock
        self._sleep = sleep
        self._slice_start = clock()
        self._hurry = False
        self.rests = 0

    def hurry(self) -> None:
        """Stop resting until the next cue boundary (someone awaits this cue)."""

        self._hurry = True

    def checkpoint(self) -> None:
        """Rest when the current work slice is used up (called by the worker)."""

        if self._hurry:
            return
        now = self._clock()
        if now - self._slice_start >= self.work_seconds:
            self.rest()

    def rest(self) -> None:
        """Release the GIL for ``rest_seconds`` and start a new work slice."""

        if self.rest_seconds > 0 and not self._hurry:
            self._sleep(self.rest_seconds)
            self.rests += 1
        self._slice_start = self._clock()

    def cue_finished(self) -> None:
        """A cue boundary: drop any hurry and yield once."""

        self._hurry = False
        self.rest()

    @contextmanager
    def installed(self) -> Iterator["SynthesisPacer"]:
        """Pace the calling thread (the worker) for the duration of the block."""

        _SWITCH_INTERVAL.acquire(self.switch_interval)
        _worker_local.pacer = self
        self._slice_start = self._clock()
        try:
            yield self
        finally:
            _worker_local.pacer = None
            _SWITCH_INTERVAL.release()


class _SwitchIntervalLease:
    """Process-wide, reference-counted lowering of ``sys.setswitchinterval``.

    Several banks (sound effects, speech) may warm at once; the interval is
    lowered while any paced worker runs and restored when the last one ends,
    unless someone else changed it meanwhile.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._users = 0
        self._saved: float | None = None
        self._applied: float | None = None

    def acquire(self, interval: float | None) -> None:
        with self._lock:
            self._users += 1
            current = sys.getswitchinterval()
            if interval is not None and interval < current:
                if self._saved is None:
                    self._saved = current
                sys.setswitchinterval(interval)
                self._applied = interval

    def release(self) -> None:
        with self._lock:
            self._users = max(0, self._users - 1)
            if self._users or self._saved is None:
                return
            if sys.getswitchinterval() == self._applied:
                sys.setswitchinterval(self._saved)
            self._saved = None
            self._applied = None


_SWITCH_INTERVAL = _SwitchIntervalLease()


SoundFactory = Callable[[], "pygame.mixer.Sound | None"]


class DeferredSoundBank(Mapping[str, pygame.mixer.Sound]):
    """Named, synthesized cues that are built after launch, never before it.

    Pure-Python PCM synthesis cost 2-7 s of launch time per Activity on the
    reference Atom N270 (Acer re-sweep 2026-10-16). An Activity *defines* each
    cue with a zero-argument factory; nothing is synthesized at construction.
    Once the first frame is presented (:mod:`greia_platform.first_frame_work`)
    one daemon worker builds the remaining cues in definition order while the
    child looks at the first screen. A cue requested before the worker reaches
    it is built on demand; one the worker is building is awaited, never built
    twice. Output is therefore identical to eager synthesis, only later.

    The bank is a read-only ``Mapping``: ``bank.get(name)``, ``name in bank``,
    ``len(bank)`` and iteration see every defined cue. It is bounded by the
    cues defined (each built at most once) and owns its single worker, which
    stops after the last cue, when the mixer closes, or on :meth:`close`.
    The worker is paced by a :class:`SynthesisPacer` (pass
    ``pacer_factory=None`` to disable) so it never starves the Activity loop.
    Audio stays fail-soft: a factory that raises leaves that cue silent
    (``get`` returns ``None``) instead of breaking the Activity.
    """

    def __init__(
        self,
        *,
        defer_until_first_frame: bool = True,
        pacer_factory: Callable[[], SynthesisPacer | None] | None = SynthesisPacer,
    ) -> None:
        self._pacer_factory = pacer_factory
        self._pacer: SynthesisPacer | None = None
        self._factories: dict[str, SoundFactory] = {}
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        self._building: set[str] = set()
        self._failed: set[str] = set()
        self._condition = threading.Condition()
        self._worker: threading.Thread | None = None
        self._closed = False
        self._first_frame_seen = False
        if defer_until_first_frame:
            after_first_frame(self._on_first_frame)

    def define(self, name: str, factory: SoundFactory) -> None:
        """Declare (or replace) cue ``name``; ``factory`` runs at most once."""

        with self._condition:
            while name in self._building:
                self._condition.wait()
            self._sounds.pop(name, None)
            self._failed.discard(name)
            self._factories[name] = factory
        if self._first_frame_seen:
            self.warm_in_background()

    def __getitem__(self, name: str) -> pygame.mixer.Sound:
        sound = self._resolve(name)
        if sound is None:
            raise KeyError(name)
        return sound

    def __contains__(self, name: object) -> bool:
        with self._condition:
            return name in self._factories and name not in self._failed

    def __iter__(self) -> Iterator[str]:
        with self._condition:
            names = [name for name in self._factories if name not in self._failed]
        return iter(names)

    def __len__(self) -> int:
        with self._condition:
            return len(self._factories) - len(self._failed & self._factories.keys())

    def built(self, name: str) -> bool:
        """Whether ``name`` is already synthesized (no work is triggered)."""

        with self._condition:
            return name in self._sounds

    def built_sounds(self) -> list[pygame.mixer.Sound]:
        """The cues synthesized so far (e.g. to stop them) without building more."""

        with self._condition:
            return list(self._sounds.values())

    def warm_all(self) -> None:
        """Build every pending cue on the calling thread."""

        for name in list(self._factories):
            self._resolve(name)

    def warm_in_background(self) -> None:
        """Start the single daemon worker if any cue is still pending."""

        with self._condition:
            busy = self._worker is not None and self._worker.is_alive()
            if self._closed or busy or not self._pending_names():
                return
            self._worker = threading.Thread(
                target=self._warm_worker, name="greia-sound-warmup", daemon=True
            )
        self._worker.start()

    def clear(self) -> None:
        """Forget every cue (fail-soft reset); a running build just finishes."""

        with self._condition:
            self._factories.clear()
            self._sounds.clear()
            self._failed.clear()

    def _on_first_frame(self) -> None:
        self._first_frame_seen = True
        self.warm_in_background()

    def close(self) -> None:
        """Stop background warming after the cue currently being built."""

        with self._condition:
            self._closed = True

    def _pending_names(self) -> list[str]:
        return [
            name
            for name in self._factories
            if name not in self._sounds
            and name not in self._failed
            and name not in self._building
        ]

    def _warm_worker(self) -> None:
        pacer = self._pacer_factory() if self._pacer_factory is not None else None
        if pacer is None:
            self._warm_pending(None)
            return
        self._pacer = pacer
        try:
            with pacer.installed():
                self._warm_pending(pacer)
        finally:
            self._pacer = None

    def _warm_pending(self, pacer: SynthesisPacer | None) -> None:
        while True:
            with self._condition:
                pending = self._pending_names()
                if self._closed or not pending:
                    return
            if pygame.mixer.get_init() is None:
                return
            self._resolve(pending[0])
            if pacer is not None:
                pacer.cue_finished()  # a cue boundary is always a yield point

    def _resolve(self, name: str) -> pygame.mixer.Sound | None:
        with self._condition:
            while True:
                sound = self._sounds.get(name)
                if sound is not None:
                    return sound
                factory = self._factories.get(name)
                if factory is None or name in self._failed:
                    return None
                if name not in self._building:
                    self._building.add(name)
                    break
                pacer = self._pacer
                if pacer is not None:
                    pacer.hurry()  # the paced worker builds it: let it run flat out
                self._condition.wait()
        try:
            sound = factory()
        except Exception:  # noqa: BLE001 - audio must never break the Activity
            sound = None
        with self._condition:
            self._building.discard(name)
            if self._factories.get(name) is factory:  # not cleared meanwhile
                if sound is None:
                    self._failed.add(name)
                else:
                    self._sounds[name] = sound
            self._condition.notify_all()
        return sound
