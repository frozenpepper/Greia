"""Semantic spoken guidance for the My Time incubator.

No audio device, pygame or provider is imported here. One injectable transport
owns playback; this coordinator owns the bounded educational cue sequence.
"""
from __future__ import annotations

from typing import Protocol

if __package__:
    from .time_model import TimeMode
else:
    from time_model import TimeMode


SPEECH_CUES = (
    "presenter.welcome",
    "instruction.clock",
    "instruction.practice",
    "instruction.stopwatch",
    "instruction.timer",
    "instruction.real_time",
    "feedback.timer_finished",
)


class SpeechTransport(Protocol):
    """A single-voice, already-prepared, non-streaming output."""

    def has_clip(self, cue: str) -> bool: ...
    def play(self, cue: str) -> bool: ...
    def busy(self) -> bool: ...
    def stop(self) -> None: ...


class TimeSpeech:
    """Coordinate first-use instructions, replay, and one terminal cue.

    The pending sequence has capacity one, intentionally: obsolete guidance
    must never outlive a mode change. The renderer can query can_repeat
    without knowing whether a mixer exists.
    """

    def __init__(self, transport: SpeechTransport) -> None:
        self.transport = transport
        self._started = False
        self._instruction = "instruction.clock"
        self._introduced: set[str] = set()
        self._pending: str | None = None

    @staticmethod
    def instruction_for(mode: TimeMode, practice: bool) -> str:
        if mode is TimeMode.CLOCK:
            return "instruction.practice" if practice else "instruction.clock"
        if mode is TimeMode.STOPWATCH:
            return "instruction.stopwatch"
        return "instruction.timer"

    @property
    def can_repeat(self) -> bool:
        return self.transport.has_clip(self._instruction)

    def start(self, mode: TimeMode, practice: bool) -> None:
        """Begin only after the first usable frame has been presented."""
        if self._started:
            return
        self._started = True
        target = self.instruction_for(mode, practice)
        self._instruction = target
        self._introduced.add(target)
        if self.transport.has_clip("presenter.welcome"):
            self._replace("presenter.welcome")
            self._pending = target if self.transport.has_clip(target) else None
        else:
            self._replace(target)

    def on_context(self, mode: TimeMode, practice: bool) -> None:
        """An actual mode/practice transition invalidates stale speech."""
        target = self.instruction_for(mode, practice)
        if target == self._instruction:
            return
        previous = self._instruction
        self._instruction = target
        self._pending = None
        if self.transport.busy():
            self.transport.stop()
        if target not in self._introduced:
            self._introduced.add(target)
            self._replace(target)
        elif previous == "instruction.practice" and target == "instruction.clock":
            self._replace("instruction.real_time")

    def replay(self) -> bool:
        """Replay the relevant short instruction, replacing stale narration."""
        if not self.can_repeat:
            return False
        self._replace(self._instruction)
        return True

    def timer_finished(self) -> None:
        """Completion outranks intro/help and must not queue repeatedly."""
        self._replace("feedback.timer_finished")

    def update(self) -> None:
        """Advance a single deferred first-use instruction without blocking."""
        if self._pending is None or self.transport.busy():
            return
        cue, self._pending = self._pending, None
        if self.transport.has_clip(cue):
            self.transport.play(cue)

    def close(self) -> None:
        """Terminate only this Activity process's speech on Home/exit."""
        self._pending = None
        self.transport.stop()

    def _replace(self, cue: str) -> None:
        self._pending = None
        if self.transport.busy():
            self.transport.stop()
        if self.transport.has_clip(cue):
            self.transport.play(cue)


__all__ = ["SpeechTransport", "TimeSpeech", "SPEECH_CUES"]
