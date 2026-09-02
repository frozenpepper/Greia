"""Domain model for Il Giardino dei Numeri (Toddler Counting Activity)."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Final

REFERENCE_WIDTH: Final[int] = 1024
REFERENCE_HEIGHT: Final[int] = 600

# Basket location in reference coordinates (grounded on right meadow)
BASKET_X: Final[float] = 780.0
BASKET_Y: Final[float] = 480.0
BASKET_RADIUS: Final[float] = 60.0


class ItemKind(StrEnum):
    APPLE = "apple"
    STRAWBERRY = "strawberry"
    FLOWER = "flower"
    BUTTERFLY = "butterfly"
    DUCKLING = "duckling"
    STAR = "star"

    @property
    def symbol(self) -> str:
        match self:
            case ItemKind.APPLE:
                return "🍎"
            case ItemKind.STRAWBERRY:
                return "🍓"
            case ItemKind.FLOWER:
                return "🌻"
            case ItemKind.BUTTERFLY:
                return "🦋"
            case ItemKind.DUCKLING:
                return "🐥"
            case ItemKind.STAR:
                return "⭐"


@dataclass
class GardenItem:
    """An interactive countable object in the garden."""

    item_id: int
    kind: ItemKind
    x: float
    y: float
    radius: float = 48.0
    counted: bool = False
    order_counted: int = 0
    pulse_timer: float = 0.0
    fly_progress: float = 0.0  # 0.0 (in field) -> 1.0 (in basket)
    giggle_timer: float = 0.0

    @property
    def symbol(self) -> str:
        return self.kind.symbol

    @property
    def current_pos(self) -> tuple[float, float]:
        if self.fly_progress <= 0.0:
            return (self.x, self.y)
        # Smooth arc into basket
        t = min(1.0, self.fly_progress)
        arc_y = -140.0 * math.sin(math.pi * t)
        curr_x = self.x + (BASKET_X - self.x) * t
        curr_y = self.y + (BASKET_Y - self.y) * t + arc_y
        return (curr_x, curr_y)

    def hit_test(self, px: float, py: float) -> bool:
        # Generous touch hit box for 2-3 year old fingers
        dist_sq = (px - self.x) ** 2 + (py - self.y) ** 2
        return dist_sq <= (self.radius * 1.35) ** 2


@dataclass
class GardenModel:
    """State machine and logic for early number discovery."""

    difficulty_level: int = 1  # 1: 1-3 items, 2: 2-4 items, 3: 3-5 items
    round_number: int = 0
    target_count: int = 2
    items: list[GardenItem] = field(default_factory=list)
    counted_count: int = 0
    celebrating: bool = False
    pending_celebration: bool = False
    celebration_delay: float = 0.0
    celebration_timer: float = 0.0
    baskets_filled: int = 0
    total_counted: int = 0
    dani_mood: str = "neutral"
    dani_jump: float = 0.0
    ripple_effects: list[tuple[float, float, float]] = field(default_factory=list)  # (x, y, age)

    def __post_init__(self) -> None:
        self.setup_round()

    def setup_round(self, count: int | None = None) -> None:
        """Initialize a new set of garden items to count."""
        self.round_number += 1
        self.celebrating = False
        self.pending_celebration = False
        self.celebration_delay = 0.0
        self.celebration_timer = 0.0
        self.counted_count = 0
        self.dani_mood = "neutral"
        self.dani_jump = 0.0
        self.ripple_effects.clear()

        # Decide count based on difficulty
        if count is not None:
            self.target_count = max(1, min(5, count))
        else:
            if self.difficulty_level == 1:
                # Early toddlers: 1, 2, or 3
                choices = [1, 2, 3] if self.round_number > 1 else [2]
            elif self.difficulty_level == 2:
                choices = [2, 3, 4]
            else:
                choices = [3, 4, 5]
            self.target_count = random.choice(choices)

        # Pick a friendly theme for this round
        theme_kind = random.choice(list(ItemKind))

        # Generate well-separated positions in the safe play area
        positions = self._generate_positions(self.target_count)
        self.items = [
            GardenItem(
                item_id=i,
                kind=theme_kind,
                x=pos[0],
                y=pos[1],
            )
            for i, pos in enumerate(positions)
        ]

    def _generate_positions(self, count: int) -> list[tuple[float, float]]:
        # Safe playground region: left meadow, avoiding Dani & Basket on right (x: 720..1024)
        left = 160.0
        right = 680.0
        top = 220.0
        bottom = 480.0

        positions: list[tuple[float, float]] = []
        min_dist = 110.0
        for _ in range(count):
            placed = False
            for _attempt in range(50):
                cand_x = random.uniform(left, right)
                cand_y = random.uniform(top, bottom)
                if all(
                    (cand_x - px) ** 2 + (cand_y - py) ** 2 >= min_dist**2
                    for px, py in positions
                ):
                    positions.append((cand_x, cand_y))
                    placed = True
                    break
            if not placed:
                # Fallback: evenly spaced horizontally
                t = (len(positions) + 1) / (count + 1)
                cand_x = left + (right - left) * t
                cand_y = (top + bottom) * 0.5
                positions.append((cand_x, cand_y))
        return positions

    def handle_tap(self, px: float, py: float) -> tuple[str, int]:
        """Process a tap/click at (px, py)."""
        if self.celebrating:
            # Tapping during celebration allows quick advance to next set
            self.next_round()
            return ("advance", 0)

        # Check items in reverse order (topmost first)
        for item in reversed(self.items):
            if item.hit_test(px, py):
                if not item.counted:
                    item.counted = True
                    self.counted_count += 1
                    item.order_counted = self.counted_count
                    item.pulse_timer = 0.5
                    self.total_counted += 1
                    self.dani_mood = "happy"
                    self.dani_jump = 0.35

                    if self.counted_count >= self.target_count:
                        # Queue celebration so the spoken number finishes playing first!
                        self.pending_celebration = True
                        self.celebration_delay = 1.0
                        self.baskets_filled += 1
                        self.dani_mood = "surprised"
                    return ("counted", item.order_counted)
                else:
                    item.giggle_timer = 0.3
                    self.dani_mood = "happy"
                    return ("giggle", item.order_counted)

        # Tapped ground: add soft pleasant ripple effect
        self.ripple_effects.append((px, py, 0.0))
        return ("miss", 0)

    def next_round(self) -> None:
        """Advance to the next round."""
        self.setup_round()

    def update(self, dt: float) -> list[str]:
        """Update animation clocks and return triggered events."""
        events: list[str] = []

        # Update items
        for item in self.items:
            if item.pulse_timer > 0.0:
                item.pulse_timer = max(0.0, item.pulse_timer - dt)
            if item.giggle_timer > 0.0:
                item.giggle_timer = max(0.0, item.giggle_timer - dt)
            if self.celebrating and item.counted:
                # Fly into Dani's basket
                if item.fly_progress < 1.0:
                    item.fly_progress = min(1.0, item.fly_progress + dt * 1.5)

        # Update Dani jump animation
        if self.dani_jump > 0.0:
            self.dani_jump = max(0.0, self.dani_jump - dt)

        # Update ripples
        active_ripples: list[tuple[float, float, float]] = []
        for rx, ry, rage in self.ripple_effects:
            new_age = rage + dt
            if new_age < 0.6:
                active_ripples.append((rx, ry, new_age))
        self.ripple_effects = active_ripples

        # Handle queued celebration after spoken number finishes
        if self.pending_celebration:
            self.celebration_delay -= dt
            if self.celebration_delay <= 0.0:
                self.pending_celebration = False
                self.celebrating = True
                self.celebration_timer = 0.0
                events.append("garden.set_counted")
                if self.baskets_filled % 3 == 0:
                    events.append("garden.basket_filled")

        # Celebration timer
        if self.celebrating:
            self.celebration_timer += dt
            # Auto-advance after 3.2s of celebration if not tapped
            if self.celebration_timer >= 3.2:
                self.next_round()

        return events
