"""Acquario Magico — gentle, optional observation missions.

The aquarium is a free toy first. Missions are light invitations layered on
top ("find the turtle", "feed the hungry clownfish"): they appear only after a
stretch of free play, never block any tool, never fail, and quietly retire if
the child keeps playing something else. Three completed missions earn a pearl
star from the treasure chest.

``MissionDirector`` is pure domain logic (no Pygame): it reads the session's
creatures and reports transitions to the app, which owns presentation, sound
and Activity events.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import random
from typing import Any, Callable, Sequence

from greia_platform.activity_feedback import IdleHintScheduler

if __package__:
    from .acquarium_content import (
        FIRST_MISSION_DELAY_SECONDS,
        MISSION_IDLE_RETIRE_SECONDS,
        MISSIONS_PER_PEARL,
        NEXT_MISSION_DELAY_SECONDS,
    )
else:
    from acquarium_content import (
        FIRST_MISSION_DELAY_SECONDS,
        MISSION_IDLE_RETIRE_SECONDS,
        MISSIONS_PER_PEARL,
        NEXT_MISSION_DELAY_SECONDS,
    )


class MissionKind(StrEnum):
    FIND = "find"
    FEED = "feed"


@dataclass(slots=True)
class Mission:
    """One active invitation targeting one creature in the tank."""

    kind: MissionKind
    species_id: str
    target_uid: int
    age: float = 0.0
    # Back-off nudges measured on the mission's own age (ADR 0037 section 6b).
    hints: IdleHintScheduler = field(default_factory=IdleHintScheduler)

    @property
    def text_key(self) -> str:
        return f"mission.{self.kind.value}.{self.species_id}"


class MissionOutcome(StrEnum):
    NONE = "none"
    STARTED = "started"
    HINT = "hint"
    COMPLETED = "completed"
    PEARL = "pearl"
    RETIRED = "retired"


class MissionDirector:
    """Schedule, track and complete optional missions.

    ``update`` returns at most one outcome per call so the app can react to
    each transition (show the banner, point, cheer, open the chest). Missions
    are only offered for creatures that are actually in the tank, so spawning
    or evicting creatures can never strand the child with an impossible task.
    """

    def __init__(
        self,
        *,
        rng: random.Random | None = None,
        first_delay: float = FIRST_MISSION_DELAY_SECONDS,
        enabled: bool = True,
    ) -> None:
        self._rng = rng or random.Random()
        self.enabled = enabled
        self.current: Mission | None = None
        self.done_in_set = 0
        self._cooldown = float(first_delay)
        self._last_species: str | None = None
        self._recent_kinds: list[MissionKind] = []

    # -- queries ---------------------------------------------------------

    @property
    def active(self) -> bool:
        return self.current is not None

    # -- time --------------------------------------------------------------

    def update(self, dt: float, creatures: Sequence[dict[str, Any]]) -> MissionOutcome:
        if not self.enabled:
            return MissionOutcome.NONE
        mission = self.current
        if mission is None:
            self._cooldown -= dt
            if self._cooldown > 0:
                return MissionOutcome.NONE
            if self._start(creatures):
                return MissionOutcome.STARTED
            self._cooldown = 2.0
            return MissionOutcome.NONE
        if not any(c["uid"] == mission.target_uid for c in creatures):
            replacement = _first(creatures, lambda c: c["spec"]["id"] == mission.species_id and _eligible(mission.kind, c))
            if replacement is None:
                return self._retire()
            mission.target_uid = replacement["uid"]
        mission.age += dt
        if mission.age >= MISSION_IDLE_RETIRE_SECONDS:
            return self._retire()
        if mission.hints.poll(mission.age):
            return MissionOutcome.HINT
        return MissionOutcome.NONE

    # -- child actions -----------------------------------------------------

    def creature_touched(self, creature: dict[str, Any]) -> MissionOutcome:
        mission = self.current
        if mission is None or mission.kind is not MissionKind.FIND:
            return MissionOutcome.NONE
        if creature["spec"]["id"] != mission.species_id:
            return MissionOutcome.NONE
        return self._complete()

    def creature_ate(self, uid: int) -> MissionOutcome:
        mission = self.current
        if mission is None or mission.kind is not MissionKind.FEED or uid != mission.target_uid:
            return MissionOutcome.NONE
        return self._complete()

    def request_hint(self) -> bool:
        """Child asked for help (hint button): hint now, reset the repeat timer."""

        if self.current is None:
            return False
        self.current.hints.reset(self.current.age)
        return True

    # -- internals ---------------------------------------------------------

    def _start(self, creatures: Sequence[dict[str, Any]]) -> bool:
        kinds = [MissionKind.FIND, MissionKind.FEED]
        # Alternate kinds so the invitations stay varied.
        if self._recent_kinds:
            kinds.sort(key=lambda kind: self._recent_kinds[-1] is kind)
        for kind in kinds:
            candidates = [c for c in creatures if _eligible(kind, c)]
            fresh = [c for c in candidates if c["spec"]["id"] != self._last_species]
            pool = fresh or candidates
            if not pool:
                continue
            target = self._rng.choice(pool)
            self.current = Mission(kind, target["spec"]["id"], target["uid"])
            self._last_species = target["spec"]["id"]
            self._recent_kinds = (self._recent_kinds + [kind])[-2:]
            return True
        return False

    def _complete(self) -> MissionOutcome:
        self.current = None
        self._cooldown = NEXT_MISSION_DELAY_SECONDS
        self.done_in_set += 1
        if self.done_in_set >= MISSIONS_PER_PEARL:
            self.done_in_set = 0
            return MissionOutcome.PEARL
        return MissionOutcome.COMPLETED

    def _retire(self) -> MissionOutcome:
        self.current = None
        self._cooldown = NEXT_MISSION_DELAY_SECONDS * 2
        return MissionOutcome.RETIRED


def _eligible(kind: MissionKind, creature: dict[str, Any]) -> bool:
    if kind is MissionKind.FEED:
        return bool(creature["spec"].get("eats", True))
    return True


def _first(items: Sequence[dict[str, Any]], predicate: Callable[[dict[str, Any]], bool]) -> dict[str, Any] | None:
    for item in items:
        if predicate(item):
            return item
    return None


__all__ = ["Mission", "MissionDirector", "MissionKind", "MissionOutcome"]
