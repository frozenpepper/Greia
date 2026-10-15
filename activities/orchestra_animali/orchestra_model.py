"""Orchestra Animali — domain state.

Pure gameplay state with no rendering, IO or platform side effects.
``Particle`` and ``InstrumentCard`` own only timers, geometry and
mutation rules so they can be unit-tested without a display.
"""

from __future__ import annotations

import math
import random


class Particle:
    """One transient musical sparkle."""

    def __init__(self, x: float, y: float, symbol: str, color: tuple[int, int, int]) -> None:
        self.x = x
        self.y = y
        self.symbol = symbol
        self.color = color
        angle = random.uniform(-math.pi * 0.8, -math.pi * 0.2)
        speed = random.uniform(3.0, 7.0)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life = 1.0
        self.decay = random.uniform(0.035, 0.06)
        self.size = random.randint(22, 32)

    def update(self) -> bool:
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.12
        self.life -= self.decay
        return self.life > 0


class InstrumentCard:
    """State for one of the five stage instruments."""

    def __init__(
        self,
        inst_id: str,
        icon: str,
        sound_name: str,
        x: float,
        y: float,
        color: tuple[int, int, int],
        label: str = "",
    ) -> None:
        self.inst_id = inst_id
        self.icon = icon
        # Localized, case-policy-resolved caption; empty means pictogram only.
        self.label = label
        self.sound_name = sound_name
        self.x = x
        self.y = y
        self.radius = 54.0
        self.jump_timer = 0.0
        self.phase = random.uniform(0, 2 * math.pi)
        self.color = color

    def trigger(self) -> None:
        self.jump_timer = 1.0

    def update(self) -> None:
        self.phase += 0.04
        if self.jump_timer > 0:
            self.jump_timer -= 0.05

    def contains(self, px: float, py: float) -> bool:
        return (self.x - px) ** 2 + (self.y - py) ** 2 <= (self.radius + 14) ** 2


__all__ = ["InstrumentCard", "Particle"]
