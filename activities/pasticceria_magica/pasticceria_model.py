from __future__ import annotations

from dataclasses import dataclass, field
import random

if __package__:
    from .pasticceria_content import CAKE_SLOTS, PATTERN_OPTIONS, TOPPINGS
else:
    from pasticceria_content import CAKE_SLOTS, PATTERN_OPTIONS, TOPPINGS


@dataclass(slots=True)
class PasticceriaModel:
    """Pure domain state for the Magic Bakery Activity.

    No Pygame, storage or Greia event IO. All randomness is injected so
    gameplay can be driven deterministically in tests. Renderer and app
    own presentation/audio/storage; this class owns rules and invariants.
    """

    mode: str = "orders"
    score: int = 0
    stars: int = 0
    recipes_served: int = 0
    current_order: list[tuple[str, int]] = field(default_factory=list)
    placed_toppings: list[tuple[str, str, int, int]] = field(default_factory=list)
    pattern_idx: int = 0
    feedback_text: str = ""
    feedback_timer: float = 0.0
    rng: random.Random = field(default_factory=random.Random, repr=False)

    def __post_init__(self) -> None:
        if not self.current_order:
            # Preserve original starter order.
            self.current_order = [("strawberry", 3), ("blueberry", 2)]
        if self.mode not in {"orders", "patterns", "free"}:
            self.mode = "orders"

    # -- mode --
    def switch_mode(self, mode: str) -> None:
        if mode in {"orders", "patterns", "free"}:
            self.mode = mode

    # -- orders/free: placement --
    def can_place(self) -> bool:
        return len(self.placed_toppings) < len(CAKE_SLOTS)

    def place_topping(self, topping_id: str) -> tuple[str, str, int, int] | None:
        """Place the next topping into the next free slot. Returns placed tuple or None."""
        if not self.can_place():
            return None
        icon = next((t[1] for t in TOPPINGS if t[0] == topping_id), None)
        if icon is None:
            return None
        px, py = CAKE_SLOTS[len(self.placed_toppings)]
        placed = (topping_id, icon, px, py)
        self.placed_toppings.append(placed)
        return placed

    def remove_at(self, logical: tuple[int, int]) -> tuple[int, int] | None:
        """Remove an existing topping whose halo contains logical point. Returns removed centre."""
        lx, ly = logical
        for idx, (t_id, t_icon, tx, ty) in enumerate(list(self.placed_toppings)):
            if (lx - tx) ** 2 + (ly - ty) ** 2 <= 28 ** 2:
                self.placed_toppings.pop(idx)
                return (tx, ty)
        return None

    def clear_toppings(self) -> None:
        self.placed_toppings.clear()

    # -- persistence helpers --
    def load_saved(self, saved: object) -> None:
        if not isinstance(saved, dict):
            return
        try:
            self.score = int(saved.get("score", self.score))
            self.stars = int(saved.get("stars", self.stars))
            self.recipes_served = int(saved.get("recipes_served", self.recipes_served))
        except Exception:
            pass
        if self.score < 0:
            self.score = 0
        if self.stars < 0:
            self.stars = 0
        if self.recipes_served < 0:
            self.recipes_served = 0

    def to_save_dict(self) -> dict[str, object]:
        # timestamp added by caller with time.time()
        return {
            "score": int(self.score),
            "stars": int(self.stars),
            "recipes_served": int(self.recipes_served),
        }

    # -- orders serve logic (pure) --
    def check_order_correct(self) -> bool:
        counts: dict[str, int] = {}
        for t_id, _, _, _ in self.placed_toppings:
            counts[t_id] = counts.get(t_id, 0) + 1
        is_correct = True
        for req_id, req_count in self.current_order:
            if counts.get(req_id, 0) != req_count:
                is_correct = False
                break
        if len(counts) != len(self.current_order):
            is_correct = False
        return is_correct

    def apply_correct_order(self) -> None:
        """Mutate score/stars/recipes and generate next order. Caller must have checked correctness."""
        self.score += 15
        self.stars += 1
        self.recipes_served += 1
        self.placed_toppings.clear()
        # Next recipe: two distinct toppings, random counts.
        t1 = self.rng.choice([t[0] for t in TOPPINGS])
        remaining = [t[0] for t in TOPPINGS if t[0] != t1]
        t2 = self.rng.choice(remaining) if remaining else t1
        self.current_order = [
            (t1, self.rng.randint(1, 4)),
            (t2, self.rng.randint(1, 3)),
        ]

    def apply_free_serve(self) -> None:
        # No scoring rule for free mode beyond visual feedback; score unchanged.
        # Keep parity with original which also did not change score except fanfare + feedback.
        pass

    # -- patterns logic --
    @property
    def current_pattern(self) -> tuple[list[str], str, list[str]]:
        return PATTERN_OPTIONS[self.pattern_idx % len(PATTERN_OPTIONS)]

    def check_pattern_candidate(self, candidate_sym: str) -> bool:
        _, correct_sym, _ = self.current_pattern
        return candidate_sym == correct_sym

    def apply_correct_pattern(self) -> None:
        self.score += 10
        self.stars += 1
        self.pattern_idx = (self.pattern_idx + 1) % len(PATTERN_OPTIONS)

    # -- feedback timer --
    def tick(self, dt: float = 0.035) -> None:
        if self.feedback_timer > 0:
            self.feedback_timer -= dt
            if self.feedback_timer <= 0:
                self.feedback_timer = 0
                self.feedback_text = ""


__all__ = ["PasticceriaModel"]
