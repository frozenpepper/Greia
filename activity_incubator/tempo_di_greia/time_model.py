"""Pure, injected time models for My Time; no device-clock mutation or pygame.

Wall time is for *display*. All elapsed measurements use one monotonic provider.
Counters are session-scoped: closing the Activity cancels them. Background
alarms require a separately authorized platform lifecycle design.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
import math
import time
from typing import Callable


MAX_COUNTDOWN_SECONDS = 60 * 60
PRESET_MINUTES = (1, 3, 5, 10)


class TimeMode(StrEnum):
    CLOCK = "clock"
    STOPWATCH = "stopwatch"
    TIMER = "timer"


@dataclass(slots=True)
class ElapsedStopwatch:
    """Pause/resume without counting time while paused."""

    monotonic: Callable[[], float] = time.monotonic
    _stored: float = 0.0
    _began: float | None = None

    @property
    def running(self) -> bool:
        return self._began is not None

    def seconds(self) -> float:
        if self._began is None:
            return self._stored
        return self._stored + max(0.0, self.monotonic() - self._began)

    def start(self) -> None:
        if self._began is None:
            self._began = self.monotonic()

    def pause(self) -> None:
        if self._began is not None:
            self._stored = self.seconds()
            self._began = None

    def reset(self) -> None:
        self._stored = 0.0
        self._began = None


@dataclass(slots=True)
class CountdownTimer:
    """One bounded visual countdown; completion is observable exactly once."""

    monotonic: Callable[[], float] = time.monotonic
    duration_seconds: int = 180
    _remaining: float = field(init=False)
    _began: float | None = None
    _completed_consumed: bool = False

    def __post_init__(self) -> None:
        self.set_duration(self.duration_seconds)

    @property
    def running(self) -> bool:
        return self._began is not None and self.remaining() > 0

    def set_duration(self, seconds: int) -> None:
        if isinstance(seconds, bool) or not isinstance(seconds, int) or not (1 <= seconds <= MAX_COUNTDOWN_SECONDS):
            raise ValueError("timer duration must be between 1 second and 60 minutes")
        self.duration_seconds = seconds
        self._remaining = float(seconds)
        self._began = None
        self._completed_consumed = False

    def remaining(self) -> float:
        if self._began is None:
            return self._remaining
        return max(0.0, self._remaining - max(0.0, self.monotonic() - self._began))

    def start(self) -> None:
        if self._began is None and self._remaining > 0:
            self._began = self.monotonic()

    def pause(self) -> None:
        if self._began is not None:
            self._remaining = self.remaining()
            self._began = None

    def reset(self) -> None:
        self.set_duration(self.duration_seconds)

    def consume_completion(self) -> bool:
        if self._completed_consumed or self._began is None or self.remaining() > 0:
            return False
        self._remaining = 0.0
        self._began = None
        self._completed_consumed = True
        return True

    @property
    def completion_pending(self) -> bool:
        return self._began is not None and self.remaining() == 0 and not self._completed_consumed


@dataclass(slots=True)
class TimeExperience:
    """Three related child tools sharing semantics but not parent screen-time."""

    wall_now: Callable[[], datetime] = lambda: datetime.now().astimezone()
    monotonic: Callable[[], float] = time.monotonic
    mode: TimeMode = TimeMode.CLOCK
    practice: bool = False
    _practice_hour: int = 9
    _practice_minute: int = 0
    stopwatch: ElapsedStopwatch = field(init=False)
    timer: CountdownTimer = field(init=False)

    def __post_init__(self) -> None:
        self.stopwatch = ElapsedStopwatch(self.monotonic)
        self.timer = CountdownTimer(self.monotonic)

    def shown_time(self) -> datetime:
        current = self.wall_now()
        if not self.practice:
            return current
        return current.replace(hour=self._practice_hour, minute=self._practice_minute, second=0, microsecond=0)

    def set_practice(self, enabled: bool) -> None:
        if enabled and not self.practice:
            current = self.wall_now()
            self._practice_hour, self._practice_minute = current.hour, current.minute
        self.practice = bool(enabled)

    def nudge_practice(self, minutes: int) -> None:
        if not self.practice:
            return
        total = (self._practice_hour * 60 + self._practice_minute + minutes) % (24 * 60)
        self._practice_hour, self._practice_minute = divmod(total, 60)

    def set_practice_minute(self, minute: int) -> None:
        """Turn only the imagined minute hand to a quarter-hour point.

        Setting an illustrated minute hand has no authority over wall time,
        profile schedules or any running stopwatch/countdown.
        """
        if not self.practice:
            return
        if isinstance(minute, bool) or minute not in (0, 15, 30, 45):
            raise ValueError("practice minute must be a quarter hour")
        self._practice_minute = minute


def analog_hand_angles(shown: datetime) -> tuple[float, float, float]:
    """Clockwise degrees from twelve for hour, minute and seconds."""
    second = shown.second + shown.microsecond / 1_000_000
    minute = shown.minute + second / 60
    hour = (shown.hour % 12) + minute / 60
    return (hour * 30, minute * 6, second * 6)


def display_duration(seconds: float, *, round_up: bool = False) -> str:
    """MM:SS for child visual counters. Avoid negative and infinity."""
    if not math.isfinite(seconds):
        raise ValueError("non-finite elapsed time")
    total = max(0, math.ceil(seconds) if round_up else math.floor(seconds))
    minutes, remaining = divmod(total, 60)
    return f"{minutes:02d}:{remaining:02d}"


__all__ = [
    "TimeMode", "TimeExperience", "ElapsedStopwatch", "CountdownTimer",
    "PRESET_MINUTES", "analog_hand_angles", "display_duration",
]
