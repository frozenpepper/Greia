"""Static journey content for Il Viaggio del Delfino.

This module owns the *semantic* journey definitions: the three finite courses
(a sunny bay, a coral reef and an evening lagoon), what each course contains
(pearl groups, leap arcs, friendly jellyfish, sea friends) and the curiosity
facts the friends unlock. It contains no simulation and no rendering so both
can be contract-tested independently (see tests/test_activity_viaggio_delfino.py).

All child-facing wording lives in locales/<lang>.json under stable semantic
IDs; runtime code only references the keys declared here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

#: Logical drawing space of the Activity (scaled by the platform canvas).
REFERENCE_WIDTH: Final = 1024
REFERENCE_HEIGHT: Final = 600

#: Water line in reference coordinates. Above it the dolphin leaps.
SURFACE_Y: Final = 175.0

#: Curiosity facts spoken by Tito (owner-approved recordings). Each one is
#: unlocked by meeting one sea friend; provenance lives in research/facts.md and
#: wording only in the locale bundles.
FACT_IDS: Final[tuple[str, ...]] = (
    "curiosity.delfino.breaching",
    "curiosity.delfino.blowhole",
    "curiosity.delfino.echolocation",
    "curiosity.delfino.whistle",
    "curiosity.delfino.teeth",
    "curiosity.delfino.pods",
)

#: Tito's welcome (spoken goal) played once per launch with the wordless
#: control hint.
WELCOME_CUE_ID: Final = "presenter.welcome"


def caption_key(fact_id: str) -> str:
    """Semantic caption key for a fact ID."""

    return f"{fact_id}.caption"


def audio_key(fact_id: str) -> str:
    """Semantic voice-cue key for a fact ID."""

    return f"{fact_id}.voice"


@dataclass(frozen=True, slots=True)
class FriendSpec:
    """One sea friend met on a course; meeting it plays one recorded fact.

    ``joins`` friends (the dolphin calf of the lagoon) swim along with the
    hero after the meeting instead of waving goodbye.
    """

    friend_id: str
    visual: str
    fact_id: str
    box: tuple[int, int]
    joins: bool = False


@dataclass(frozen=True, slots=True)
class JourneySpec:
    """One finite course with a finish.

    ``layout`` lists the course stretches in order: ``G`` a pearl group under
    water, ``A`` a pearl arc above the waves (rewards a well-timed leap) and
    ``F`` the next sea friend. ``look`` selects the baked scene treatment.
    """

    journey_id: str
    name_key: str
    length_x: float
    speed: float
    group_size: int
    layout: str
    jellies: int
    friends: tuple[FriendSpec, ...]
    landmark: str | None
    look: str

    @property
    def pearl_groups(self) -> int:
        return sum(1 for slot in self.layout if slot in "GA")

    @property
    def total_pearls(self) -> int:
        return self.pearl_groups * self.group_size

    @property
    def stretches(self) -> int:
        return len(self.layout)


JOURNEYS: Final[tuple[JourneySpec, ...]] = (
    JourneySpec(
        journey_id="bay",
        name_key="journey.bay.name",
        length_x=9000.0,
        speed=160.0,
        group_size=3,
        layout="GGFAGFG",
        jellies=3,
        friends=(
            FriendSpec("turtle", "creature.marine.turtle", "curiosity.delfino.breaching", (150, 112)),
            FriendSpec("whale", "creature.marine.whale", "curiosity.delfino.blowhole", (250, 126)),
        ),
        landmark="prop.vocab.lighthouse",
        look="bay",
    ),
    JourneySpec(
        journey_id="reef",
        name_key="journey.reef.name",
        length_x=10500.0,
        speed=172.0,
        group_size=4,
        layout="GAFGGFA",
        jellies=6,
        friends=(
            FriendSpec("octopus", "creature.marine.octopus", "curiosity.delfino.echolocation", (124, 124)),
            FriendSpec("seahorse", "creature.marine.seahorse", "curiosity.delfino.whistle", (96, 128)),
        ),
        landmark="prop.everyday.shell",
        look="reef",
    ),
    JourneySpec(
        journey_id="lagoon",
        name_key="journey.lagoon.name",
        length_x=12000.0,
        speed=184.0,
        group_size=5,
        layout="GAFGAGF",
        jellies=6,
        friends=(
            FriendSpec("manta", "creature.marine.manta", "curiosity.delfino.teeth", (170, 112)),
            FriendSpec("calf", "creature.marine.dolphin", "curiosity.delfino.pods", (150, 76), joins=True),
        ),
        landmark="prop.vocab.island",
        look="lagoon",
    ),
)

JOURNEY_IDS: Final[tuple[str, ...]] = tuple(spec.journey_id for spec in JOURNEYS)


def journey(journey_id: str) -> JourneySpec:
    """Return the journey spec for ``journey_id`` (``KeyError`` if unknown)."""

    for spec in JOURNEYS:
        if spec.journey_id == journey_id:
            return spec
    raise KeyError(journey_id)


def stars_for(collected: int, total: int) -> int:
    """Presentation stars for one finished journey (always at least one).

    Finishing is the achievement; more pearls earn more stars. Stars are
    presentation only (Greia owns rewards).
    """

    if total <= 0:
        return 1
    ratio = max(0, collected) / total
    if ratio >= 0.8:
        return 3
    if ratio >= 0.5:
        return 2
    return 1
