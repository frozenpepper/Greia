from __future__ import annotations

"""Pure bridge-building domain state for Costruiamo Ponti.

No pygame, storage or audio imports. The model owns selection,
slot placement, traveler crossing physics and level progression.
Presentation and platform side-effects live in renderer/app owners.
"""

from dataclasses import dataclass, field
import math

if __package__:
    from .ponti_content import (
        BLOCKS,
        BRIDGE_END_X,
        BRIDGE_START_X,
        BRIDGE_Y,
        LEVELS,
    )
else:
    from ponti_content import (
        BLOCKS,
        BRIDGE_END_X,
        BRIDGE_START_X,
        BRIDGE_Y,
        LEVELS,
    )

VALID_BLOCK_IDS = frozenset(str(b["id"]) for b in BLOCKS)


@dataclass(frozen=True, slots=True)
class PontiStepOutcome:
    """Result of one physics tick for audio/effects/progression routing."""

    audio: tuple[str, ...] = ()
    level_completed: bool = False
    victory: bool = False
    stars: int | None = None
    fell: bool = False
    special: str | None = None  # "shroom" | "rainbow" when correct special placed
    celebration_tick: bool = False


@dataclass(slots=True)
class PontiModel:
    """Own deterministic bridge gameplay state.

    Traveler motion, slot correctness and level progression are pure
    calculations. Callers translate semantic outcomes into audio,
    particles or Greia event/storage actions.
    """

    total_stars: int = 0
    level_idx: int = 0
    selected_block_id: str = "wood"
    slots: list[str | None] = field(default_factory=list)
    flash_state: str = "neutral"
    flash_motion: str = "idle_bounce"
    flash_pos: list[float] = field(default_factory=lambda: [90.0, 260.0])
    flash_target_step: int = 0
    flash_anim_timer: float = 0.0
    is_victory: bool = False

    def __post_init__(self) -> None:
        if self.total_stars < 0:
            self.total_stars = 0
        if self.selected_block_id not in VALID_BLOCK_IDS:
            self.selected_block_id = "wood"
        # Initialise slots for the starting level when empty.
        if not self.slots:
            self.setup_level(self.level_idx if self.level_idx < len(LEVELS) else 0)
        elif len(self.slots) != len(self.required):
            # Repair inconsistent external state.
            self.setup_level(self.level_idx)

    @property
    def cur_level(self) -> dict[str, object]:
        return LEVELS[self.level_idx % len(LEVELS)]

    @property
    def required(self) -> list[str]:
        req = self.cur_level["required"]
        assert isinstance(req, list)
        return req  # type: ignore[return-value]

    @property
    def num_slots(self) -> int:
        return len(self.required)

    @property
    def slot_w(self) -> int:
        return (BRIDGE_END_X - BRIDGE_START_X) // max(1, self.num_slots)

    @property
    def can_start_crossing(self) -> bool:
        return self.flash_state in ("neutral", "blink") and not self.is_victory

    def setup_level(self, idx: int) -> None:
        """Reset traveler and slots for level ``idx`` while keeping durable stars."""
        # Keep idx in range via modulo for level data, but store raw idx for victory check.
        self.level_idx = idx
        cur = LEVELS[idx % len(LEVELS)]
        required = cur["required"]
        assert isinstance(required, list)
        self.slots = [None for _ in required]
        self.flash_state = "neutral"
        self.flash_motion = "idle_bounce"
        self.flash_pos = [90.0, 260.0]
        self.flash_target_step = 0
        self.flash_anim_timer = 0.0

    def select_block(self, block_id: str) -> None:
        if block_id not in VALID_BLOCK_IDS:
            raise ValueError(f"unknown ponti block: {block_id}")
        if self.is_victory:
            return
        if self.flash_state not in ("neutral", "blink"):
            return
        self.selected_block_id = block_id

    def place_block(self, slot_idx: int) -> bool:
        if self.is_victory:
            return False
        if self.flash_state not in ("neutral", "blink"):
            return False
        if not (0 <= slot_idx < self.num_slots):
            return False
        self.slots[slot_idx] = self.selected_block_id
        return True

    def clear(self) -> None:
        if self.is_victory:
            return
        if self.flash_state not in ("neutral", "blink"):
            return
        self.slots = [None for _ in self.required]

    def start_crossing(self) -> bool:
        if not self.can_start_crossing:
            return False
        self.flash_state = "happy"
        self.flash_motion = "happy_hop"
        self.flash_target_step = 0
        self.flash_anim_timer = 0.0
        return True

    def restart_after_victory(self) -> None:
        """Reset to level 0 after terminal victory; keeps durable stars."""
        self.is_victory = False
        self.level_idx = 0
        self.setup_level(0)

    def step(self) -> PontiStepOutcome:
        """Advance one fixed 0.04s tick. Mirrors original main loop physics."""
        if self.is_victory:
            return PontiStepOutcome()

        # Happy hop crossing the bridge gap slot by slot.
        # Keep historical variable naming for contract parity: bridge_end_x
        # target_x = bridge_end_x + 50
        if self.flash_motion == "happy_hop" and self.flash_state == "happy":
            self.flash_anim_timer += 0.04
            if self.flash_target_step < self.num_slots:
                target_x = BRIDGE_START_X + (self.flash_target_step + 0.5) * self.slot_w - 48
            else:
                bridge_end_x = BRIDGE_END_X
                target_x = bridge_end_x + 50
            dx = target_x - self.flash_pos[0]
            if dx > 4:
                self.flash_pos[0] += 6.0
                self.flash_pos[1] = 260.0 - abs(math.sin(self.flash_anim_timer * 8.0)) * 25.0
            else:
                if self.flash_target_step < self.num_slots:
                    placed = self.slots[self.flash_target_step]
                    expected = self.required[self.flash_target_step]
                    if placed != expected:
                        self.flash_state = "surprised"
                        self.flash_motion = "surprised_wobble"
                        self.flash_anim_timer = 0.0
                        return PontiStepOutcome(audio=("boing",), fell=True)
                    # Correct block – special audio/particles for shroom/rainbow.
                    if placed == "shroom":
                        self.flash_target_step += 1
                        return PontiStepOutcome(audio=("boing",), special="shroom")
                    if placed == "rainbow":
                        self.flash_target_step += 1
                        return PontiStepOutcome(special="rainbow")
                    self.flash_target_step += 1
                    return PontiStepOutcome()
                # Reached right cliff – celebrate and award.
                self.flash_state = "happy"
                self.flash_motion = "celebrate_pop"
                self.flash_anim_timer = 0.0
                self.total_stars += 1
                return PontiStepOutcome(audio=("win",), level_completed=True, stars=self.total_stars)

        elif self.flash_motion == "surprised_wobble" and self.flash_state == "surprised":
            self.flash_anim_timer += 0.04
            if self.flash_anim_timer < 0.45:
                self.flash_pos[1] += 9.0
            else:
                t = (self.flash_anim_timer - 0.45) / 0.85
                if t < 1.0:
                    self.flash_pos[0] = self.flash_pos[0] * (1 - 0.08) + 90.0 * 0.08
                    self.flash_pos[1] = 360.0 - math.sin(t * math.pi) * 140.0
                else:
                    self.flash_pos = [90.0, 260.0]
                    self.flash_state = "neutral"
                    self.flash_motion = "idle_bounce"
            return PontiStepOutcome()

        elif self.flash_motion == "celebrate_pop":
            self.flash_anim_timer += 0.04
            self.flash_pos[1] = 260.0 - abs(math.sin(self.flash_anim_timer * 6.0)) * 20.0
            celebration_tick = True
            if self.flash_anim_timer > 2.0:
                self.level_idx += 1
                if self.level_idx >= len(LEVELS):
                    self.is_victory = True
                    return PontiStepOutcome(victory=True, celebration_tick=celebration_tick)
                self.setup_level(self.level_idx)
                return PontiStepOutcome(celebration_tick=celebration_tick)
            return PontiStepOutcome(celebration_tick=celebration_tick)

        return PontiStepOutcome()

    def slot_rect(self, slot_idx: int) -> tuple[int, int, int, int]:
        """Return logical slot rect (x,y,w,h) for rendering hit parity."""
        # Rendering rect (x+6, w-12, h 64) matches original visual slot.
        sx = BRIDGE_START_X + slot_idx * self.slot_w
        return (sx + 6, BRIDGE_Y, self.slot_w - 12, 64)

    def slot_input_rect(self, slot_idx: int) -> tuple[int, int, int, int]:
        """Input hit rect slightly larger than visual slot (original behavior)."""
        sx = BRIDGE_START_X + slot_idx * self.slot_w
        return (sx + 4, BRIDGE_Y, self.slot_w - 8, 70)


__all__ = ["PontiModel", "PontiStepOutcome", "VALID_BLOCK_IDS"]
