"""Domain model and physical simulation for Mondo Contrari (Opposites)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import math
import random
from typing import Final

REFERENCE_WIDTH: Final[int] = 1024
REFERENCE_HEIGHT: Final[int] = 600


class OppositeCategory(StrEnum):
    UP_DOWN = "up_down"
    BIG_SMALL = "big_small"
    IN_OUT = "in_out"
    OPEN_CLOSED = "open_closed"
    FAST_SLOW = "fast_slow"


@dataclass
class ContrariParticle:
    x: float
    y: float
    vx: float
    vy: float
    kind: str  # "sparkle", "star", "confetti", "speedline"
    color: tuple[int, int, int]
    size: float
    life: float = 1.0


class ContrariModel:
    """Simulate the 5 interactive opposite scenes with fluid physics."""

    def __init__(self) -> None:
        self.category: OppositeCategory = OppositeCategory.UP_DOWN
        self.discovered_categories: set[OppositeCategory] = {OppositeCategory.UP_DOWN}
        self.completed_all: bool = False

        # States for each opposite scene
        # 1. UP / DOWN (balloon height: 120 up, 400 down)
        self.is_up: bool = False
        self.target_balloon_y: float = 410.0
        self.balloon_y: float = 410.0

        # 2. BIG / SMALL (bubble scale: 0.35 small, 1.25 big)
        self.is_big: bool = False
        self.target_bubble_scale: float = 0.4
        self.bubble_scale: float = 0.4

        # 3. IN / OUT (box: inside y=380, outside y=240)
        self.is_in: bool = True
        self.target_box_y: float = 370.0
        self.box_rabbit_y: float = 370.0

        # 4. OPEN / CLOSED (window shutter angle: 0.0 closed, 1.0 open)
        self.is_open: bool = False
        self.target_shutter: float = 0.0
        self.shutter_open_ratio: float = 0.0

        # 5. FAST / SLOW (Flash & snail racing)
        self.is_fast: bool = False
        self.runner_x: float = 240.0
        self.snail_x: float = 200.0

        # Animation timers and particles
        self.anim_timer: float = 0.0
        self.particles: list[ContrariParticle] = []

    def set_category(self, cat: OppositeCategory) -> None:
        self.category = cat
        self.discovered_categories.add(cat)
        if len(self.discovered_categories) == len(OppositeCategory):
            self.completed_all = True
        self.particles.clear()

    def toggle_up_down(self) -> bool:
        self.is_up = not self.is_up
        self.target_balloon_y = 130.0 if self.is_up else 410.0
        self._spawn_sparkles(512, int(self.balloon_y))
        return self.is_up

    def toggle_big_small(self) -> bool:
        self.is_big = not self.is_big
        self.target_bubble_scale = 1.25 if self.is_big else 0.4
        self._spawn_sparkles(512, 300)
        return self.is_big

    def toggle_in_out(self) -> bool:
        self.is_in = not self.is_in
        self.target_box_y = 370.0 if self.is_in else 230.0
        self._spawn_sparkles(512, 350)
        return not self.is_in

    def toggle_open_closed(self) -> bool:
        self.is_open = not self.is_open
        self.target_shutter = 1.0 if self.is_open else 0.0
        self._spawn_sparkles(512, 300)
        return self.is_open

    def toggle_fast_slow(self) -> bool:
        self.is_fast = not self.is_fast
        if self.is_fast:
            self._spawn_speedlines()
        else:
            self._spawn_sparkles(int(self.snail_x), 380)
        return self.is_fast

    def _spawn_sparkles(self, cx: int, cy: int) -> None:
        for _ in range(12):
            self.particles.append(
                ContrariParticle(
                    x=cx + random.uniform(-40, 40),
                    y=cy + random.uniform(-40, 40),
                    vx=random.uniform(-60, 60),
                    vy=random.uniform(-70, 20),
                    kind="sparkle",
                    color=random.choice([(255, 215, 0), (0, 229, 255), (255, 64, 129)]),
                    size=random.uniform(5, 10),
                    life=1.0,
                )
            )

    def _spawn_speedlines(self) -> None:
        for _ in range(8):
            self.particles.append(
                ContrariParticle(
                    x=self.runner_x + random.uniform(-60, 20),
                    y=340 + random.uniform(-20, 20),
                    vx=-random.uniform(150, 300),
                    vy=0.0,
                    kind="speedline",
                    color=(255, 235, 59),
                    size=random.uniform(20, 45),
                    life=0.6,
                )
            )

    def update(self, dt: float) -> None:
        self.anim_timer += dt

        # Smooth transitions
        # Balloon Y
        step_balloon = dt * 260.0
        if abs(self.balloon_y - self.target_balloon_y) > 1.0:
            if self.balloon_y < self.target_balloon_y:
                self.balloon_y = min(self.target_balloon_y, self.balloon_y + step_balloon)
            else:
                self.balloon_y = max(self.target_balloon_y, self.balloon_y - step_balloon)

        # Bubble Scale
        step_scale = dt * 1.8
        if abs(self.bubble_scale - self.target_bubble_scale) > 0.01:
            if self.bubble_scale < self.target_bubble_scale:
                self.bubble_scale = min(self.target_bubble_scale, self.bubble_scale + step_scale)
            else:
                self.bubble_scale = max(self.target_bubble_scale, self.bubble_scale - step_scale)

        # Box Rabbit Y
        step_box = dt * 320.0
        if abs(self.box_rabbit_y - self.target_box_y) > 1.0:
            if self.box_rabbit_y < self.target_box_y:
                self.box_rabbit_y = min(self.target_box_y, self.box_rabbit_y + step_box)
            else:
                self.box_rabbit_y = max(self.target_box_y, self.box_rabbit_y - step_box)

        # Shutter ratio
        step_shutter = dt * 3.5
        if abs(self.shutter_open_ratio - self.target_shutter) > 0.01:
            if self.shutter_open_ratio < self.target_shutter:
                self.shutter_open_ratio = min(self.target_shutter, self.shutter_open_ratio + step_shutter)
            else:
                self.shutter_open_ratio = max(self.target_shutter, self.shutter_open_ratio - step_shutter)

        # Fast / Slow runners
        if self.category == OppositeCategory.FAST_SLOW:
            if self.is_fast:
                self.runner_x += dt * 320.0
                if self.runner_x > 750.0:
                    self.runner_x = 240.0
                if random.random() < 0.2:
                    self._spawn_speedlines()
            else:
                # Snail crawls very slowly
                self.snail_x += dt * 18.0
                if self.snail_x > 700.0:
                    self.snail_x = 200.0

        # Update particles
        surviving = []
        for p in self.particles:
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.life -= dt
            if p.life > 0:
                surviving.append(p)
        self.particles = surviving
