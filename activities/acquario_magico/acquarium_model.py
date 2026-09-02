"""Acquario Magico — domain state and per-frame simulation.

The session owns:

- the list of creatures (with their per-creature timers)
- the falling food pellets
- the rising bubbles
- the transient particles
- the treasure chest state
- the day/night ``glow_mode`` flag
- the persistent counters (creatures fed, bubbles popped)

Update rules (creature physics, food falling, bubble rise,
particle life decay, chest-open timer) live here as plain
methods so they can be unit-tested without Pygame event
plumbing or rendering.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Any

if __package__:
    from .acquarium_content import (
        MAX_CREATURES,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        SPECIES,
        ToolIndex,
    )
else:
    from acquarium_content import (
        MAX_CREATURES,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        SPECIES,
        ToolIndex,
    )


def default_creature_factory() -> list[dict[str, Any]]:
    """Balanced starter tank used when no saved creatures exist.

    Eight creatures, one per species, with simple positions and
    alternate facings. Kept as a factory so the application can
    ignore return ordering when persistence is loaded.
    """

    return []


@dataclass
class AquariumSession:
    """Owns the runtime state of the aquarium.

    The class deliberately uses ``dict`` records rather than
    dataclasses for the per-creature / per-particle / per-pellet
    state because the runtime mutates many fields every frame
    and the readability cost of nested dataclasses outweighs the
    type-safety gain for these short-lived records.
    """

    glow_mode: bool = False
    active_tool: int = ToolIndex.SPAWN
    spawn_selector_idx: int = 0
    total_fed: int = 0
    total_popped: int = 0
    chest_open_timer: float = 0.0
    creatures: list[dict[str, Any]] = field(default_factory=list)
    food_pellets: list[dict[str, Any]] = field(default_factory=list)
    bubbles: list[dict[str, Any]] = field(default_factory=list)
    particles: list[dict[str, Any]] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Spawning and population management
    # ------------------------------------------------------------------

    def spawn_creature(
        self,
        x: float,
        y: float,
        spec_idx: int | None = None,
        facing: int = 1,
    ) -> dict[str, Any] | None:
        """Append a new creature to the tank.

        Returns the new creature record, or ``None`` if the tank
        is already full. The oldest creature is evicted when the
        cap is reached so the tank never grows unbounded.
        """

        if len(self.creatures) >= MAX_CREATURES:
            self.creatures.pop(0)
        idx = spec_idx if spec_idx is not None else random.randint(0, len(SPECIES) - 1)
        species = SPECIES[idx % len(SPECIES)]
        speed = species.get("speed", 1.2)
        vx = (1.0 if facing > 0 else -1.0) * speed * random.uniform(0.8, 1.2)

        if species["behavior"] == "floor":
            y = float(REFERENCE_HEIGHT - 110)
            vy = 0.0
        else:
            vy = random.uniform(-0.3, 0.3)

        creature = {
            "spec": species,
            "x": float(x),
            "y": float(y),
            "vx": vx,
            "vy": vy,
            "target_vx": vx,
            "target_vy": vy,
            "facing": 1 if vx >= 0 else -1,
            "swim_t": random.random() * 6.28,
            "puffed_t": 0.0,
            "spin_t": 0.0,
            "happy_t": 0.0,
        }
        self.creatures.append(creature)
        return creature

    def seed_default_population(self) -> None:
        """Spawn the canonical eight-species starter tank."""

        self.spawn_creature(240, 220, 0, 1)   # Clownfish
        self.spawn_creature(500, 180, 1, -1)  # Turtle
        self.spawn_creature(740, 280, 2, -1)  # Octopus
        self.spawn_creature(360, 140, 3, 1)   # Dolphin
        self.spawn_creature(620, 360, 4, 1)   # Puffer
        self.spawn_creature(180, 320, 5, 1)   # Seahorse
        self.spawn_creature(820, 200, 6, -1)  # Jellyfish
        self.spawn_creature(320, REFERENCE_HEIGHT - 110, 7, 1)  # Starfish

    def restore_saved_population(self, saved_creatures: list[dict[str, Any]]) -> None:
        """Rebuild creatures from a saved snapshot.

        Unknown species fall back to the clownfish (index 0) so
        the tank can never be left empty by a stale save file.
        """

        for saved in saved_creatures[:16]:
            spec_id = saved.get("id")
            try:
                s_idx = next(
                    i for i, species in enumerate(SPECIES) if species["id"] == spec_id
                )
            except StopIteration:
                s_idx = 0
            self.spawn_creature(
                saved.get("x", random.uniform(100, 900)),
                saved.get("y", random.uniform(120, 440)),
                s_idx,
                saved.get("facing", 1),
            )

    # ------------------------------------------------------------------
    # Tool-side effect helpers
    # ------------------------------------------------------------------

    def drop_food_at(self, mx: int, my: int, count: int = 3) -> None:
        """Drop a small cluster of food pellets around a target point."""

        for offset in [-14, 0, 14][:count]:
            self.food_pellets.append(
                {
                    "x": float(mx + offset + random.uniform(-4, 4)),
                    "y": float(my + random.uniform(-5, 5)),
                    "vx": random.uniform(-0.3, 0.3),
                    "vy": random.uniform(0.9, 1.5),
                    "size": random.uniform(5.0, 7.5),
                    "color": (245, 158, 11),
                }
            )

    def emit_bubble_storm(self, count: int, x_low: int, x_high: int, y_low: int, y_high: int) -> None:
        for _ in range(count):
            self.bubbles.append(
                {
                    "x": float(random.uniform(x_low, x_high)),
                    "y": float(random.uniform(y_low, y_high)),
                    "vx": random.uniform(-0.8, 0.8),
                    "vy": random.uniform(-2.5, -5.5),
                    "size": random.uniform(8, 26),
                }
            )

    def emit_sparkles(self, count: int, cx: float, cy: float, color: tuple[int, int, int] = (253, 224, 71)) -> None:
        for _ in range(count):
            self.particles.append(
                {
                    "x": float(cx + random.uniform(-20, 20)),
                    "y": float(cy + random.uniform(-20, 20)),
                    "vx": random.uniform(-2.5, 2.5),
                    "vy": random.uniform(-3.5, -1.5),
                    "color": color,
                    "size": random.uniform(4, 9),
                    "life": 1.0,
                    "decay": random.uniform(0.03, 0.05),
                }
            )

    # ------------------------------------------------------------------
    # Per-frame simulation
    # ------------------------------------------------------------------

    def update(self, dt: float) -> None:
        """Advance every simulated state by ``dt`` seconds."""

        if self.chest_open_timer > 0:
            self.chest_open_timer = max(0.0, self.chest_open_timer - dt)

        for creature in self.creatures:
            self._update_creature(creature, dt)

        self.food_pellets = self._update_food_pellets()
        self.bubbles = self._update_bubbles()
        self.particles = self._update_particles()

    def _update_creature(self, creature: dict[str, Any], dt: float) -> None:
        species = creature["spec"]
        creature["swim_t"] += 0.06
        speed = species.get("speed", 1.2)

        for timer_key in ("puffed_t", "spin_t", "happy_t"):
            if creature[timer_key] > 0:
                creature[timer_key] = max(0.0, creature[timer_key] - dt)

        behavior = species["behavior"]
        if behavior == "floor":
            self._step_floor_creature(creature)
            return

        # Swimming creatures: food seeking vs cruising
        seeking_food = False
        if self.food_pellets and behavior != "jellyfish":
            closest = min(
                self.food_pellets,
                key=lambda pellet: (pellet["x"] - creature["x"]) ** 2 + (pellet["y"] - creature["y"]) ** 2,
            )
            dx = closest["x"] - creature["x"]
            dy = closest["y"] - creature["y"]
            distance = math.hypot(dx, dy)
            if distance < 280.0:
                seeking_food = True
                if distance > 1.0:
                    ndx, ndy = dx / distance, dy / distance
                else:
                    ndx, ndy = 0.0, 0.0
                creature["vx"] += (ndx * speed * 1.5 - creature["vx"]) * 0.12
                creature["vy"] += (ndy * speed * 1.5 - creature["vy"]) * 0.12
                if distance < 32.0:
                    if closest in self.food_pellets:
                        self.food_pellets.remove(closest)
                    self.total_fed += 1
                    creature["happy_t"] = 1.2
                    if species["id"] == "puffer":
                        creature["puffed_t"] = 1.5
                    self._emit_nibble_particles(creature)

        if not seeking_food:
            creature["vx"] += (creature["target_vx"] - creature["vx"]) * 0.05
            creature["vy"] += (creature["target_vy"] - creature["vy"]) * 0.05
            if random.random() < 0.02:
                creature["target_vy"] = random.uniform(-0.4, 0.4)
            if random.random() < 0.005:
                creature["target_vx"] = -creature["target_vx"]

        self._step_swim(creature)

    def _step_floor_creature(self, creature: dict[str, Any]) -> None:
        """Starfish-style floor walker: stays on the sand, walks left/right."""

        creature["x"] += creature["vx"]
        creature["y"] = float(REFERENCE_HEIGHT - 110)
        if creature["x"] < 80:
            creature["x"] = 80
            creature["vx"] = abs(creature["vx"])
            creature["facing"] = 1
        elif creature["x"] > REFERENCE_WIDTH - 80:
            creature["x"] = REFERENCE_WIDTH - 80
            creature["vx"] = -abs(creature["vx"])
            creature["facing"] = -1

    def _step_swim(self, creature: dict[str, Any]) -> None:
        """Swim motion + boundary clamp + facing hysteresis."""

        creature["x"] += creature["vx"]
        behavior = creature["spec"]["behavior"]
        swim_t = creature["swim_t"]
        if behavior == "pulse":
            pulse_wave = math.sin(swim_t * 3.0)
            creature["y"] += creature["vy"] + (pulse_wave * 1.2 if pulse_wave > 0 else 0.2)
        elif behavior == "leap":
            creature["y"] += creature["vy"] + math.sin(swim_t * 2.5) * 1.4
        elif behavior == "float":
            creature["y"] += creature["vy"] + math.sin(swim_t * 1.8) * 0.8
        else:
            creature["y"] += creature["vy"] + math.sin(swim_t * 2.0) * 0.6

        if creature["vx"] > 0.35:
            creature["facing"] = 1
        elif creature["vx"] < -0.35:
            creature["facing"] = -1

        min_y = 90
        max_y = REFERENCE_HEIGHT - 130
        if creature["x"] < 60:
            creature["x"] = 60
            creature["vx"] = abs(creature["vx"])
            creature["target_vx"] = abs(creature["target_vx"])
            creature["facing"] = 1
        elif creature["x"] > REFERENCE_WIDTH - 60:
            creature["x"] = REFERENCE_WIDTH - 60
            creature["vx"] = -abs(creature["vx"])
            creature["target_vx"] = -abs(creature["target_vx"])
            creature["facing"] = -1

        if creature["y"] < min_y:
            creature["y"] = min_y
            creature["vy"] = abs(creature["vy"])
        elif creature["y"] > max_y:
            creature["y"] = max_y
            creature["vy"] = -abs(creature["vy"])

    def _update_food_pellets(self) -> list[dict[str, Any]]:
        surviving: list[dict[str, Any]] = []
        for pellet in self.food_pellets:
            pellet["x"] += pellet["vx"]
            pellet["y"] += pellet["vy"]
            if pellet["y"] < REFERENCE_HEIGHT - 90:
                surviving.append(pellet)
            else:
                for _ in range(2):
                    self.particles.append(
                        {
                            "x": pellet["x"],
                            "y": pellet["y"],
                            "vx": random.uniform(-0.5, 0.5),
                            "vy": random.uniform(-0.5, -1.0),
                            "color": (217, 119, 6),
                            "size": 3.0,
                            "life": 0.6,
                            "decay": 0.08,
                        }
                    )
        return surviving

    def _update_bubbles(self) -> list[dict[str, Any]]:
        surviving: list[dict[str, Any]] = []
        for bubble in self.bubbles:
            bubble["x"] += bubble["vx"]
            bubble["y"] += bubble["vy"]
            if bubble["y"] > 65:
                surviving.append(bubble)
            else:
                self.total_popped += 1
        return surviving

    def _update_particles(self) -> list[dict[str, Any]]:
        surviving: list[dict[str, Any]] = []
        for particle in self.particles:
            particle["x"] += particle["vx"]
            particle["y"] += particle["vy"]
            particle["life"] -= particle["decay"]
            if particle["life"] > 0:
                surviving.append(particle)
        return surviving

    def _emit_nibble_particles(self, creature: dict[str, Any]) -> None:
        for _ in range(6):
            self.particles.append(
                {
                    "x": creature["x"],
                    "y": creature["y"],
                    "vx": random.uniform(-1.5, 1.5),
                    "vy": random.uniform(-1.5, 1.5),
                    "color": (253, 224, 71),
                    "size": random.uniform(3, 6),
                    "life": 1.0,
                    "decay": 0.06,
                }
            )
