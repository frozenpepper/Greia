"""Baia delle Orche — gentle, optional invitations from Tito.

The bay is a free toy first. Invitations are light suggestions layered on top
("Find Kiko", "Feed Oskar a squid", "Make Luna jump"): they appear only after a
stretch of free play and only in daylight (night is the pod's calm bedtime),
never block any tool, never fail, and quietly retire if the child keeps playing
something else. Three completed invitations earn a star and a pod celebration.

``MissionDirector`` is pure domain logic (no Pygame): the app reports what the
child did and reacts to the returned outcome (banner, Tito, sound, events).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import random
from typing import Sequence

try:
    from orca_content import (
        FIRST_MISSION_DELAY_SECONDS,
        MISSION_HINT_REPEAT_SECONDS,
        MISSION_HINT_SECONDS,
        MISSION_IDLE_RETIRE_SECONDS,
        MISSIONS_PER_STAR,
        NEXT_MISSION_DELAY_SECONDS,
        ORCA_IDS,
        FoodType,
    )
except ImportError:
    from .orca_content import (
        FIRST_MISSION_DELAY_SECONDS,
        MISSION_HINT_REPEAT_SECONDS,
        MISSION_HINT_SECONDS,
        MISSION_IDLE_RETIRE_SECONDS,
        MISSIONS_PER_STAR,
        NEXT_MISSION_DELAY_SECONDS,
        ORCA_IDS,
        FoodType,
    )


class MissionKind(StrEnum):
    FIND = "find"
    FEED = "feed"
    JUMP = "jump"


@dataclass(slots=True)
class Mission:
    """One open invitation about one orca (and, for FEED, the food it wants)."""

    kind: MissionKind
    orca_id: str
    food: FoodType | None = None
    age: float = 0.0
    next_hint_at: float = MISSION_HINT_SECONDS

    @property
    def text_key(self) -> str:
        return f"mission.{self.kind.value}.{self.orca_id}"


class MissionOutcome(StrEnum):
    NONE = "none"
    STARTED = "started"
    HINT = "hint"
    NOT_YET = "not_yet"
    COMPLETED = "completed"
    STAR = "star"
    RETIRED = "retired"


class MissionDirector:
    """Schedule, track and complete optional invitations.

    Each call returns at most one outcome so the app can react to every
    transition. ``NOT_YET`` is the gentle try-again signal (the right orca ate
    a different food): the invitation simply stays open.
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
        self.last_completed: Mission | None = None
        self.done_in_set = 0
        self._cooldown = float(first_delay)
        self._last_orca: str | None = None
        self._last_kind: MissionKind | None = None

    @property
    def active(self) -> bool:
        return self.current is not None

    # -- time --------------------------------------------------------------

    def update(self, dt: float, *, daytime: bool) -> MissionOutcome:
        if not self.enabled:
            return MissionOutcome.NONE
        mission = self.current
        if mission is None:
            if not daytime:
                return MissionOutcome.NONE
            self._cooldown -= dt
            if self._cooldown > 0:
                return MissionOutcome.NONE
            self._start()
            return MissionOutcome.STARTED
        if not daytime:
            # Bedtime for the pod: never leave an invitation hanging at night.
            return self._retire()
        mission.age += dt
        if mission.age >= MISSION_IDLE_RETIRE_SECONDS:
            return self._retire()
        if mission.age >= mission.next_hint_at:
            mission.next_hint_at = mission.age + MISSION_HINT_REPEAT_SECONDS
            return MissionOutcome.HINT
        return MissionOutcome.NONE

    # -- child actions -----------------------------------------------------

    def orca_touched(self, orca_id: str) -> MissionOutcome:
        mission = self.current
        if mission is None or mission.kind is not MissionKind.FIND or orca_id != mission.orca_id:
            return MissionOutcome.NONE
        return self._complete()

    def orca_jumped(self, orca_id: str) -> MissionOutcome:
        mission = self.current
        if mission is None or mission.kind is not MissionKind.JUMP or orca_id != mission.orca_id:
            return MissionOutcome.NONE
        return self._complete()

    def orca_ate(self, orca_id: str, food: str) -> MissionOutcome:
        mission = self.current
        if mission is None or mission.kind is not MissionKind.FEED or orca_id != mission.orca_id:
            return MissionOutcome.NONE
        if mission.food is not None and food != mission.food.value:
            return MissionOutcome.NOT_YET
        return self._complete()

    def request_hint(self) -> bool:
        """The child asked for help: hint now and reset the repeat timer."""

        if self.current is None:
            return False
        self.current.next_hint_at = self.current.age + MISSION_HINT_REPEAT_SECONDS
        return True

    # -- internals ---------------------------------------------------------

    def _start(self) -> None:
        kinds = [kind for kind in MissionKind if kind is not self._last_kind]
        kind = self._rng.choice(kinds)
        candidates = [orca_id for orca_id in ORCA_IDS if orca_id != self._last_orca]
        orca_id = self._rng.choice(candidates)
        food = self._rng.choice(list(FoodType)) if kind is MissionKind.FEED else None
        self.current = Mission(kind, orca_id, food)
        self._last_orca = orca_id
        self._last_kind = kind

    def _complete(self) -> MissionOutcome:
        self.last_completed = self.current
        self.current = None
        self._cooldown = NEXT_MISSION_DELAY_SECONDS
        self.done_in_set += 1
        if self.done_in_set >= MISSIONS_PER_STAR:
            self.done_in_set = 0
            return MissionOutcome.STAR
        return MissionOutcome.COMPLETED

    def _retire(self) -> MissionOutcome:
        self.current = None
        self._cooldown = NEXT_MISSION_DELAY_SECONDS * 2
        return MissionOutcome.RETIRED


__all__ = ["Mission", "MissionDirector", "MissionKind", "MissionOutcome"]
