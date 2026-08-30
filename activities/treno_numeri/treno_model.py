"""Treno Numeri — pure domain state (no pygame, no rendering).

Owns the station puzzle invariants: fruit selection, addition/count mode,
target/loaded counts and round/victory progression. Presentation timing,
train animation offsets and particle lists remain in the app/renderer.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

if __package__:
    from .treno_content import ADDITION_PAIRS, COUNT_CHOICES, FRUITS, TOTAL_STATIONS
else:
    from treno_content import ADDITION_PAIRS, COUNT_CHOICES, FRUITS, TOTAL_STATIONS


@dataclass(slots=True)
class TrainModel:
    """Deterministic puzzle state for one Treno Numeri journey.

    Storage, audio and Greia event publication live outside this class.
    The model never auto-arms a child choice; ``loaded_count`` only
    changes through explicit ``add_load`` calls.
    """

    rng: random.Random = field(default_factory=random.Random, repr=False)
    total_stations: int = TOTAL_STATIONS
    round_idx: int = 0
    is_victory: bool = False
    mode: str = "addition"
    val_a: int = 2
    val_b: int = 1
    target_count: int = 3
    loaded_count: int = 0
    current_fruit: dict[str, Any] = field(default_factory=lambda: FRUITS[0])
    total_stars: int = 0

    def __post_init__(self) -> None:
        if self.total_stars < 0:
            self.total_stars = 0
        # Initial station generation uses round 0; caller may override
        # with a dedicated setup after constructing with persisted stars.
        self.setup_station(self.round_idx)

    def setup_station(self, rnd: int) -> None:
        """Prepare puzzle data for station ``rnd`` without touching stars."""

        self.current_fruit = FRUITS[rnd % len(FRUITS)]
        self.loaded_count = 0
        if rnd % 2 == 0:
            self.mode = "addition"
            self.val_a, self.val_b = self.rng.choice(ADDITION_PAIRS)
            self.target_count = self.val_a + self.val_b
        else:
            self.mode = "count"
            self.target_count = self.rng.choice(COUNT_CHOICES)
            self.val_a = self.target_count
            self.val_b = 0

    def add_load(self, amount: int) -> int:
        """Apply ``amount`` fruits toward the current target; return loaded."""

        if amount <= 0 or self.is_victory:
            return 0
        needed = self.target_count - self.loaded_count
        if needed <= 0:
            return 0
        to_load = min(amount, needed)
        self.loaded_count += to_load
        return to_load

    @property
    def is_station_complete(self) -> bool:
        return self.loaded_count >= self.target_count

    @property
    def needed(self) -> int:
        return max(0, self.target_count - self.loaded_count)

    def complete_station(self) -> bool:
        """Record station completion, increment stars and advance or win.

        Returns True when the whole journey is now complete (victory).
        """

        self.total_stars += 1
        next_idx = self.round_idx + 1
        if next_idx >= self.total_stations:
            self.is_victory = True
            self.round_idx = next_idx
            return True
        self.round_idx = next_idx
        self.setup_station(self.round_idx)
        return False

    def mark_journey_complete(self) -> None:
        """Force victory after departing the last station."""

        self.is_victory = True

    def restart(self) -> None:
        """Start a new journey without discarding durable stars."""

        self.round_idx = 0
        self.is_victory = False
        self.setup_station(0)


__all__ = ["TrainModel"]
