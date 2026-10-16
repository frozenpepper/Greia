"""Rules of one bedtime night (no Pygame): who dreams of what, and offers.

A ``BedtimeNight`` owns the three ``SleepyCloud`` friends and the quilt tray.
The child offers a tray quilt to a cloud: the dreamed quilt is kept (the cloud
starts to yawn, the tray slot empties); any other quilt is declined and stays
in the tray (it may be exactly what another cloud dreams of). Misses are
counted per cloud (hints grow with them) and per night (the ladder adapts).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Final

if __package__:
    from .cloud_content import CLOUDS_PER_NIGHT, MAX_LEVEL, LEVELS, NightLevel, NightPlan, Quilt
else:
    from cloud_content import CLOUDS_PER_NIGHT, MAX_LEVEL, LEVELS, NightLevel, NightPlan, Quilt

# A night with this many misses (or more) steps one rung down the ladder.
STEP_DOWN_MISSES: Final = 3


class CloudState(StrEnum):
    AWAKE = "awake"
    YAWNING = "yawning"
    ASLEEP = "asleep"


@dataclass(slots=True)
class SleepyCloud:
    """One little cloud: its dream, its quilt once tucked in, and its misses."""

    index: int
    dream: Quilt
    state: CloudState = CloudState.AWAKE
    quilt: Quilt | None = None
    misses: int = 0

    @property
    def awake(self) -> bool:
        return self.state is CloudState.AWAKE

    @property
    def asleep(self) -> bool:
        return self.state is CloudState.ASLEEP


class Offer(StrEnum):
    RIGHT = "right"
    WRONG = "wrong"
    IGNORED = "ignored"


@dataclass(frozen=True, slots=True)
class OfferOutcome:
    offer: Offer
    cloud_misses: int = 0


@dataclass(slots=True)
class BedtimeNight:
    """Three dreaming clouds and one tray of quilts for one finite night."""

    level: int
    plan: NightPlan
    clouds: list[SleepyCloud] = field(init=False)
    tray: list[Quilt | None] = field(init=False)
    misses: int = field(init=False, default=0)

    def __post_init__(self) -> None:
        if len(self.plan.dreams) != CLOUDS_PER_NIGHT:
            raise ValueError("a night has exactly three clouds")
        self.level = max(0, min(MAX_LEVEL, int(self.level)))
        self.clouds = [SleepyCloud(index, dream) for index, dream in enumerate(self.plan.dreams)]
        self.tray = list(self.plan.tray)

    @property
    def rung(self) -> NightLevel:
        return LEVELS[self.level]

    @property
    def asleep_count(self) -> int:
        return sum(1 for cloud in self.clouds if cloud.asleep)

    @property
    def tucked_count(self) -> int:
        return sum(1 for cloud in self.clouds if cloud.quilt is not None)

    @property
    def complete(self) -> bool:
        return all(cloud.asleep for cloud in self.clouds)

    @property
    def first_try(self) -> int:
        return sum(1 for cloud in self.clouds if cloud.quilt is not None and cloud.misses == 0)

    @property
    def stars_given(self) -> int:
        return sum(cloud.quilt.stars for cloud in self.clouds if cloud.quilt is not None)

    def offer(self, tray_index: int, cloud_index: int) -> OfferOutcome:
        """The child gives tray quilt ``tray_index`` to cloud ``cloud_index``."""

        if not (0 <= tray_index < len(self.tray) and 0 <= cloud_index < len(self.clouds)):
            return OfferOutcome(Offer.IGNORED)
        quilt = self.tray[tray_index]
        cloud = self.clouds[cloud_index]
        if quilt is None or not cloud.awake:
            return OfferOutcome(Offer.IGNORED)
        if quilt == cloud.dream:
            cloud.quilt = quilt
            cloud.state = CloudState.YAWNING
            self.tray[tray_index] = None
            return OfferOutcome(Offer.RIGHT, cloud.misses)
        cloud.misses += 1
        self.misses += 1
        return OfferOutcome(Offer.WRONG, cloud.misses)

    def fall_asleep(self, cloud_index: int) -> bool:
        """A yawning cloud closes its eyes; True when this changed the state."""

        if not 0 <= cloud_index < len(self.clouds):
            return False
        cloud = self.clouds[cloud_index]
        if cloud.state is not CloudState.YAWNING:
            return False
        cloud.state = CloudState.ASLEEP
        return True

    def answer_for(self, cloud_index: int) -> int | None:
        """Tray index of the quilt this cloud dreams of (hints only)."""

        if not 0 <= cloud_index < len(self.clouds):
            return None
        dream = self.clouds[cloud_index].dream
        for index, quilt in enumerate(self.tray):
            if quilt == dream:
                return index
        return None

    def next_awake(self) -> int | None:
        for cloud in self.clouds:
            if cloud.awake:
                return cloud.index
        return None


def adapt_level(level: int, misses: int) -> int:
    """A clean night climbs a rung; a hard night (3+ misses) steps down one."""

    if misses == 0:
        return min(MAX_LEVEL, level + 1)
    if misses >= STEP_DOWN_MISSES:
        return max(0, level - 1)
    return max(0, min(MAX_LEVEL, level))


__all__ = [
    "BedtimeNight",
    "CloudState",
    "Offer",
    "OfferOutcome",
    "STEP_DOWN_MISSES",
    "SleepyCloud",
    "adapt_level",
]
