"""Piccola Serra — pure domain state (no pygame, no rendering).

Owns the greenhouse pot invariants, harvest progression and particle
simulation. Storage, audio and Greia event publication live outside this
module. The model never auto-arms a child choice; ``active_tool`` is
managed by the app layer, and this model only decides whether the
attempted tool matches the pot's needs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

if __package__:
    from .serra_content import PLANTS, TARGET_HARVEST
else:
    from serra_content import PLANTS, TARGET_HARVEST


def _needed_tool_for_stage(stage: int) -> int:
    """Return the tool index required for a given pot stage."""
    if stage == 0:
        return 0
    if stage == 1:
        return 1
    if stage == 2:
        return 2
    if stage == 3:
        return 1
    return 3


@dataclass(slots=True)
class SerraModel:
    """Deterministic greenhouse state.

    Pots are list of 4 dicts with ``plant``, ``stage``, ``growth``,
    ``water_level``. ``stage`` progression is 0 empty →1 seeded →2
    sprout →3 bud →4 bloom → harvest resets to 0.
    """

    target_harvest: int = TARGET_HARVEST
    harvest_count: int = 0
    is_victory: bool = False
    pots: list[dict[str, Any]] = field(default_factory=list)
    particles: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.pots:
            self.pots = [
                {"plant": None, "stage": 0, "growth": 0.0, "water_level": 0.0}
                for _ in range(4)
            ]
        if self.harvest_count < 0:
            self.harvest_count = 0

    # -- stage helpers --------------------------------------------------

    @staticmethod
    def needed_tool(stage: int) -> int:
        return _needed_tool_for_stage(stage)

    def pot_needed(self, idx: int) -> int:
        return _needed_tool_for_stage(self.pots[idx]["stage"])

    def can_apply(self, idx: int, tool: int) -> bool:
        return self.pot_needed(idx) == tool

    # -- transitions ----------------------------------------------------

    def apply_tool(
        self, idx: int, tool: int, selected_plant_type: int
    ) -> dict[str, Any] | None:
        """Attempt to apply ``tool`` to pot ``idx``.

        Returns a result dict describing the transition (sound/event/victory)
        or ``None`` when the tool does not match.
        """

        pot = self.pots[idx]
        stage = int(pot["stage"])
        needed = _needed_tool_for_stage(stage)
        if tool != needed:
            return None

        if stage == 0:
            plant = PLANTS[selected_plant_type % len(PLANTS)]
            pot["plant"] = plant
            pot["stage"] = 1
            return {"stage": 1, "sound": "sprout", "plant_id": plant["id"]}
        if stage == 1:
            pot["stage"] = 2
            return {"stage": 2, "sound": "water"}
        if stage == 2:
            pot["stage"] = 3
            return {"stage": 3, "sound": "sprout"}
        if stage == 3:
            pot["stage"] = 4
            plant_id = pot["plant"]["id"] if pot["plant"] else "unknown"
            return {"stage": 4, "sound": "bloom", "plant_id": plant_id}
        if stage == 4:
            pot["stage"] = 0
            pot["plant"] = None
            self.harvest_count += 1
            if self.harvest_count >= self.target_harvest:
                self.is_victory = True
                return {
                    "stage": 0,
                    "sound": "harvest",
                    "win_sound": "win",
                    "victory": True,
                }
            return {"stage": 0, "sound": "harvest"}
        return None

    def reset(self) -> None:
        """Clear greenhouse after victory or for replay."""
        self.harvest_count = 0
        self.is_victory = False
        for pot in self.pots:
            pot["plant"] = None
            pot["stage"] = 0
            pot["growth"] = 0.0
            pot["water_level"] = 0.0
        self.particles.clear()

    # -- particles ------------------------------------------------------

    def update_particles(self) -> None:
        """Advance particle simulation (no-op when victory is active)."""
        if self.is_victory:
            return
        surviving: list[dict[str, Any]] = []
        for p in self.particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["life"] -= p["decay"]
            if p["life"] > 0:
                surviving.append(p)
        self.particles = surviving


__all__ = ["SerraModel"]
