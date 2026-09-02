"""Pure domain model for Il Bosco dei Numeri di Tito (no pygame dependencies)."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

if __package__:
    from .bosco_content import ForestItemKind, NUMBERS_1_TO_10
else:
    from bosco_content import ForestItemKind, NUMBERS_1_TO_10


@dataclass
class CountableForestItem:
    """An interactive item in the forest clearing."""

    item_id: int
    kind: ForestItemKind
    x: float
    y: float
    slot_x: float = 0.0
    slot_y: float = 0.0
    radius: float = 44.0
    counted: bool = False
    order_counted: int = 0
    pulse_timer: float = 0.0
    fly_progress: float = 0.0  # 0.0 in forest -> 1.0 in Ten-Frame
    giggle_timer: float = 0.0

    @property
    def current_pos(self) -> tuple[float, float]:
        if self.fly_progress <= 0.0:
            return (self.x, self.y)
        if self.fly_progress >= 1.0:
            return (self.slot_x, self.slot_y)
        t = self.fly_progress
        # Smooth ease-in-out curve with a gentle hop arc
        ease_t = 0.5 - 0.5 * math.cos(math.pi * t)
        cur_x = self.x + (self.slot_x - self.x) * ease_t
        cur_y = self.y + (self.slot_y - self.y) * ease_t - 50.0 * math.sin(math.pi * t)
        return (cur_x, cur_y)


@dataclass
class BoscoModel:
    """State machine for 1-to-10 counting and number recognition."""

    current_number: int = 1
    mode: str = "count"  # "count" | "guess"
    items: list[CountableForestItem] = field(default_factory=list)
    counted_count: int = 0
    celebrating: bool = False
    pending_celebration: bool = False
    celebration_delay: float = 0.0
    celebration_timer: float = 0.0
    total_completed: int = 0
    tito_mood: str = "neutral"
    tito_jump: float = 0.0

    # Guess challenge state
    guess_target: int = 1
    guess_options: list[int] = field(default_factory=list)
    guess_wobble_card: int | None = None
    guess_wobble_timer: float = 0.0
    guess_solved: bool = False
    guess_solved_timer: float = 0.0
    advance_guess_round: bool = False
    auto_advanced: bool = False

    ripple_effects: list[tuple[float, float, float]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.setup_number(self.current_number)

    def setup_number(self, num: int) -> None:
        """Populate the clearing with items for the selected number (1..10)."""
        self.current_number = max(1, min(10, num))
        self.counted_count = 0
        self.celebrating = False
        self.pending_celebration = False
        self.celebration_delay = 0.0
        self.celebration_timer = 0.0
        self.tito_mood = "neutral"
        self.tito_jump = 0.0
        self.ripple_effects.clear()

        num_def = NUMBERS_1_TO_10[self.current_number - 1]
        slot_positions = self._calculate_ten_frame_slots()
        forest_positions = self._generate_forest_positions(self.current_number)

        self.items = [
            CountableForestItem(
                item_id=i,
                kind=num_def.kind,
                x=forest_positions[i][0],
                y=forest_positions[i][1],
                slot_x=slot_positions[i][0],
                slot_y=slot_positions[i][1],
            )
            for i in range(self.current_number)
        ]

    def _calculate_ten_frame_slots(self) -> list[tuple[float, float]]:
        """Ten-frame: 2 rows of 5 slots located at the bottom-center."""
        slots = []
        # Center horizontally: frame width ~520px (5 columns of 95px, 2 rows of 60px)
        start_x = 240.0
        slot_spacing_x = 95.0
        row_y_top = 460.0
        row_y_bottom = 530.0

        for col in range(5):
            slots.append((start_x + col * slot_spacing_x, row_y_top))
        for col in range(5):
            slots.append((start_x + col * slot_spacing_x, row_y_bottom))
        return slots

    def _generate_forest_positions(self, count: int) -> list[tuple[float, float]]:
        """Generate safe, well-spaced coordinates in the open forest clearing."""
        # Safe clearing bounds: x in [140, 780], y in [180, 390]
        # Keep clear of Tito on the right (~890) and Home button on the top-left
        positions: list[tuple[float, float]] = []
        min_dist = 85.0 if count > 6 else 105.0

        for i in range(count):
            placed = False
            for _ in range(80):
                rx = random.uniform(140.0, 780.0)
                ry = random.uniform(180.0, 390.0)
                if all(math.hypot(rx - px, ry - py) >= min_dist for px, py in positions):
                    positions.append((rx, ry))
                    placed = True
                    break
            if not placed:
                # Fallback grid layout if random placement is crowded
                col = i % 5
                row = i // 5
                positions.append((180.0 + col * 130.0, 210.0 + row * 110.0))
        return positions

    def setup_guess_round(self, target: int | None = None) -> None:
        """Prepare a number recognition challenge."""
        prev_target = getattr(self, "guess_target", None)
        if target is not None:
            self.guess_target = max(1, min(10, target))
        else:
            candidates = [n for n in range(1, 11) if n != prev_target]
            self.guess_target = random.choice(candidates) if candidates else random.randint(1, 10)

        # 3 options including target
        pool = [n for n in range(1, 11) if n != self.guess_target]
        distractors = random.sample(pool, 2)
        options = [self.guess_target, distractors[0], distractors[1]]
        random.shuffle(options)
        self.guess_options = options
        self.guess_wobble_card = None
        self.guess_wobble_timer = 0.0
        self.guess_solved = False
        self.guess_solved_timer = 0.0
        self.advance_guess_round = False
        self.tito_mood = "neutral"
        self.mode = "guess"

    def handle_tap(self, x: float, y: float) -> tuple[str, int]:
        """Process tap on an item in count mode.

        Returns (outcome, count_number):
        - ("counted", N): item successfully counted as N
        - ("already_counted", 0): tapped an item already placed
        - ("miss", 0): empty space tapped
        """
        for item in reversed(self.items):
            cur_x, cur_y = item.current_pos
            if math.hypot(x - cur_x, y - cur_y) <= item.radius + 15.0:
                if not item.counted:
                    self.counted_count += 1
                    item.counted = True
                    item.order_counted = self.counted_count
                    item.pulse_timer = 0.5
                    self.tito_mood = "happy"
                    self.tito_jump = 0.35

                    if self.counted_count >= self.current_number:
                        self.pending_celebration = True
                        self.celebration_delay = 1.0  # 1.0s delay so number audio speaks fully

                    return ("counted", self.counted_count)
                else:
                    item.giggle_timer = 0.3
                    return ("already_counted", 0)

        self.ripple_effects.append((x, y, 0.0))
        return ("miss", 0)

    def handle_guess_tap(self, chosen_num: int) -> bool:
        """Process child choice in guess mode."""
        if self.guess_solved:
            return False
        if chosen_num == self.guess_target:
            self.guess_solved = True
            self.guess_solved_timer = 1.8
            self.tito_mood = "happy"
            self.tito_jump = 0.5
            self.total_completed += 1
            return True
        else:
            self.guess_wobble_card = chosen_num
            self.guess_wobble_timer = 0.4
            self.tito_mood = "surprised"
            return False

    def next_number(self) -> None:
        nxt = 1 if self.current_number >= 10 else self.current_number + 1
        self.setup_number(nxt)

    def prev_number(self) -> None:
        prv = 10 if self.current_number <= 1 else self.current_number - 1
        self.setup_number(prv)

    def update(self, dt: float) -> None:
        """Advance animations and celebration timers."""
        # Tito jump & mood
        if self.tito_jump > 0.0:
            self.tito_jump = max(0.0, self.tito_jump - dt)
            if self.tito_jump == 0.0 and not self.celebrating:
                self.tito_mood = "neutral"

        # Item pulse / fly physics
        for item in self.items:
            if item.pulse_timer > 0.0:
                item.pulse_timer = max(0.0, item.pulse_timer - dt)
            if item.giggle_timer > 0.0:
                item.giggle_timer = max(0.0, item.giggle_timer - dt)
            if item.counted and item.fly_progress < 1.0:
                item.fly_progress = min(1.0, item.fly_progress + dt * 2.2)

        # Pending celebration delay (so spoken number is never cut off)
        if self.pending_celebration:
            self.celebration_delay -= dt
            if self.celebration_delay <= 0.0:
                self.pending_celebration = False
                self.celebrating = True
                self.celebration_timer = 3.2
                self.tito_mood = "happy"
                self.tito_jump = 0.6
                self.total_completed += 1

        # Celebration timer (auto-advances to next number when finished)
        if self.celebrating:
            self.celebration_timer -= dt
            if self.celebration_timer <= 0.0:
                self.celebrating = False
                self.tito_mood = "neutral"
                if self.mode == "count":
                    self.next_number()
                    self.auto_advanced = True

        # Guess mode timers
        if self.guess_wobble_timer > 0.0:
            self.guess_wobble_timer = max(0.0, self.guess_wobble_timer - dt)
            if self.guess_wobble_timer == 0.0:
                self.guess_wobble_card = None
                self.tito_mood = "neutral"

        if self.guess_solved:
            self.guess_solved_timer = max(0.0, self.guess_solved_timer - dt)
            if self.guess_solved_timer == 0.0:
                # Advance to next challenge round in guess mode (no loop, no teleporting items!)
                self.setup_guess_round()
                self.advance_guess_round = True

        # Ripples
        new_ripples = []
        for x, y, age in self.ripple_effects:
            if age + dt < 0.4:
                new_ripples.append((x, y, age + dt))
        self.ripple_effects = new_ripples
