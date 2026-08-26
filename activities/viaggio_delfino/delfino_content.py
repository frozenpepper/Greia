"""Static journey content for Il Viaggio del Delfino.

This module owns the *semantic* journey definition: chapter identity/order and
the curiosity-fact catalogue. It contains no simulation and no rendering so
both can be contract-tested independently (see tests/test_activity_viaggio_delfino.py).

All child-facing wording lives in locales/<lang>.json under stable semantic IDs;
runtime code only references the keys declared here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

#: Ordered chapters of one full journey. ``length_x`` is world-space distance;
#: at the accepted base cruise speed (~180 px/s) each chapter is roughly one
#: minute of gentle play, which matches the Phase-0 attention budget for age 4-8.
@dataclass(frozen=True, slots=True)
class Chapter:
    chapter_id: str
    name_key: str
    length_x: float


CHAPTERS: Final[tuple[Chapter, ...]] = (
    Chapter("coral_bay", "chapter.coral_bay.name", 10000.0),
    Chapter("kelp_forest", "chapter.kelp_forest.name", 10000.0),
    Chapter("open_sea", "chapter.open_sea.name", 10000.0),
)

TOTAL_JOURNEY_X: Final = sum(chapter.length_x for chapter in CHAPTERS)


def chapter_index_for_x(world_x: float) -> int:
    """Return the index of the chapter containing ``world_x``.

    The value is clamped to the last chapter so the celebration/finish logic
    never runs past the end of the defined journey.
    """

    travelled = 0.0
    for index, chapter in enumerate(CHAPTERS):
        travelled += chapter.length_x
        if world_x < travelled:
            return index
    return len(CHAPTERS) - 1


def chapter_start_x(index: int) -> float:
    """World x where the given chapter begins."""

    return float(sum(chapter.length_x for chapter in CHAPTERS[:index]))


#: Curiosity facts spoken by Tito. Order defines the shuffle-bag seed order.
#: Provenance for every fact lives in research/facts.md; wording lives only in
#: the locale bundles. Presentation-only: facts never affect score or progress.
FACT_IDS: Final[tuple[str, ...]] = (
    "curiosity.delfino.breaching",
    "curiosity.delfino.echolocation",
    "curiosity.delfino.blowhole",
    "curiosity.delfino.pods",
    "curiosity.delfino.teeth",
    "curiosity.delfino.whistle",
)


def caption_key(fact_id: str) -> str:
    """Semantic caption key for a fact ID."""

    return f"{fact_id}.caption"


def audio_key(fact_id: str) -> str:
    """Semantic voice-cue key for a fact ID."""

    return f"{fact_id}.voice"
