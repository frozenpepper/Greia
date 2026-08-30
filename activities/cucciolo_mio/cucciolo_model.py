"""Pure domain state for Cucciolo Mio.

No pygame, no Greia IO. Pet and particle logic stays deterministic
and testable without a display.
"""

from __future__ import annotations

import math
import random

if __package__:
    from .cucciolo_content import VALID_ACCESSORIES, VALID_SPECIES
else:
    from cucciolo_content import VALID_ACCESSORIES, VALID_SPECIES  # type: ignore[import-not-found,no-redef]


class Particle:
    """Transient emoji particle with simple physics."""

    def __init__(self, x: float, y: float, symbol: str, color: tuple[int, int, int]) -> None:
        self.x = x
        self.y = y
        self.symbol = symbol
        self.color = color
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(2.0, 5.5)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life = 1.0
        self.decay = random.uniform(0.03, 0.05)

    def update(self) -> bool:
        self.x += self.vx
        self.y += self.vy
        self.life -= self.decay
        return self.life > 0


class PetEntity:
    """Owns pet state and animation timers without any rendering."""

    def __init__(self, x: float, y: float, species: str = "cat") -> None:
        self.x = x
        self.y = y
        self.target_x = x
        self.species = species if species in VALID_SPECIES else "cat"
        self.accessory = "bow"
        self.is_sleeping = False
        self.blink_timer = random.uniform(2.0, 4.5)
        self.chew_timer = 0.0
        self.wag_angle = 0.0
        self.bubble_count = 0

    def set_species(self, species: str) -> None:
        if species in VALID_SPECIES:
            self.species = species

    def set_accessory(self, accessory: str) -> None:
        if accessory in VALID_ACCESSORIES:
            self.accessory = accessory

    def cycle_accessory(self) -> str:
        order = ["bow", "crown", "glasses", "party_hat", "none"]
        cur = self.accessory if self.accessory in order else "bow"
        nxt = order[(order.index(cur) + 1) % len(order)]
        self.accessory = nxt
        return nxt

    def update(self) -> None:
        dx = self.target_x - self.x
        self.x += dx * 0.12
        self.wag_angle += 0.15
        self.blink_timer -= 0.03
        if self.blink_timer <= 0:
            self.blink_timer = random.uniform(2.5, 5.0)
        if self.chew_timer > 0:
            self.chew_timer -= 0.04


__all__ = ["Particle", "PetEntity"]
