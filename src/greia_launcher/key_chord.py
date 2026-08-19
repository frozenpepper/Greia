from __future__ import annotations

from typing import Iterable


class KeyChordTracker:
    """Tracks whether a specific combination of keys is held continuously.

    Designed for accidental-activation resistance. The target combination must
    be held simultaneously for the entire required duration. If any key in the
    combination is released, or if an untracked key breaks the chord (optional),
    the hold timer resets immediately.
    """

    DEFAULT_HOLD_DURATION = 5.0

    def __init__(
        self,
        target_keys: Iterable[int],
        *,
        hold_duration_seconds: float = DEFAULT_HOLD_DURATION,
    ) -> None:
        self._target_keys = frozenset(target_keys)
        if not self._target_keys:
            raise ValueError("target_keys must contain at least one key")
        if hold_duration_seconds <= 0.0:
            raise ValueError("hold_duration_seconds must be positive")
        self._hold_duration = hold_duration_seconds
        self._currently_pressed: set[int] = set()
        self._chord_started_at: float | None = None
        self._triggered = False

    @property
    def target_keys(self) -> frozenset[int]:
        return self._target_keys

    @property
    def is_holding(self) -> bool:
        return self._target_keys.issubset(self._currently_pressed)

    @property
    def is_triggered(self) -> bool:
        return self._triggered

    def progress(self, now: float) -> float:
        """Return 0.0 to 1.0 indicating hold progress towards activation."""
        if not self.is_holding or self._chord_started_at is None:
            return 0.0
        elapsed = now - self._chord_started_at
        if elapsed <= 0.0:
            return 0.0
        return min(1.0, elapsed / self._hold_duration)

    def handle_key_down(self, key: int, now: float) -> bool:
        """Update pressed keys. Returns True if activation threshold is reached."""
        self._currently_pressed.add(key)
        if self._target_keys.issubset(self._currently_pressed):
            if self._chord_started_at is None:
                self._chord_started_at = now
                self._triggered = False
            elif not self._triggered and (now - self._chord_started_at) >= self._hold_duration:
                self._triggered = True
                return True
        return False

    def handle_key_up(self, key: int) -> None:
        """Update released keys. Resets hold timer if chord is broken."""
        self._currently_pressed.discard(key)
        if not self._target_keys.issubset(self._currently_pressed):
            self._chord_started_at = None
            self._triggered = False

    def poll(self, now: float) -> bool:
        """Check current hold duration. Returns True once when threshold is reached."""
        if self._target_keys.issubset(self._currently_pressed):
            if self._chord_started_at is None:
                self._chord_started_at = now
                self._triggered = False
            elif not self._triggered and (now - self._chord_started_at) >= self._hold_duration:
                self._triggered = True
                return True
        return False

    def reset(self) -> None:
        self._currently_pressed.clear()
        self._chord_started_at = None
        self._triggered = False
