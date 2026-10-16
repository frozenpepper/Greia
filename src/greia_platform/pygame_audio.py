"""Small Pygame PCM helpers for bounded Activity-generated sound effects.

Greia Activities may synthesize tiny feedback cues, but raw PCM must match the
mixer that Pygame actually opened. These helpers deliberately cover only that
format boundary plus :class:`DeferredSoundBank`, which keeps that synthesis off
the launch path; prerecorded speech and broader audio policy remain owned by
their existing services.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
import struct
import threading

import pygame

from .first_frame_work import after_first_frame

_PCM16_LE = struct.Struct("<h")


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

    if not 1 <= channel_count <= 8:
        raise ValueError("Pygame PCM channel count must be between 1 and 8")
    clamped = max(-32768, min(32767, int(sample)))
    raw += _PCM16_LE.pack(clamped) * channel_count


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
    Audio stays fail-soft: a factory that raises leaves that cue silent
    (``get`` returns ``None``) instead of breaking the Activity.
    """

    def __init__(self, *, defer_until_first_frame: bool = True) -> None:
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
        while True:
            with self._condition:
                pending = self._pending_names()
                if self._closed or not pending:
                    return
            if pygame.mixer.get_init() is None:
                return
            self._resolve(pending[0])

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
