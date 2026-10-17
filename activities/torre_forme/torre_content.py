"""The build catalogue and the difficulty ladder of La Torre delle Forme.

Every build is authored in its own small grid (``(col, row)``, row 0 at the
top) from the six shared wooden block kinds (``prop.blocks.*``). A set is
five builds from the current rung's pool, easiest first:

=====  ==========  =================================================  ===========
rung   outline     kit                                                blocks
=====  ==========  =================================================  ===========
1      SLOTS       only the kinds the build needs, already turned      2-4
                   the right way
2      SLOTS       one kind starts turned the wrong way (turn it!)     3-5
3      SLOTS       kinds start turned at random + one extra kind that  4-6
                   belongs nowhere
4      SILHOUETTE  as rung 3; only the outer shape is drawn             4-6
5      SILHOUETTE  as rung 4 with two extra kinds                       5-8
=====  ==========  =================================================  ===========

The pictures are shared vocabulary props (the "picture on the box"), the
nouns are shared spoken-word clips; both are optional.
"""

from __future__ import annotations

import random
from typing import Final, Mapping, Sequence

if __package__:
    from .torre_model import (
        BUILDS_PER_SET,
        MAX_LEVEL,
        TURNS,
        Block,
        BlockKind,
        BuildPlan,
        OutlineStyle,
        Puzzle,
        place,
    )
else:
    from torre_model import (
        BUILDS_PER_SET,
        MAX_LEVEL,
        TURNS,
        Block,
        BlockKind,
        BuildPlan,
        OutlineStyle,
        Puzzle,
        place,
    )

SQ = BlockKind.SQUARE
RE = BlockKind.RECTANGLE
TR = BlockKind.TRIANGLE
HC = BlockKind.HALF_CIRCLE
AR = BlockKind.ARCH
CY = BlockKind.CYLINDER

# Rotation reminders: triangle 0 = point up, 3 = point left; half circle
# 0 = dome up, 2 = dome down; arch 0 = opening down; rectangle 1 = standing.
BUILDS: Final[Mapping[str, BuildPlan]] = {
    plan.build_id: plan
    for plan in (
        BuildPlan("igloo", (place(HC, 0, 0, 0), place(AR, 0, 0, 1)), noun="igloo", picture="prop.vocab.igloo"),
        BuildPlan(
            "table",
            (place(RE, 0, 0, 0), place(CY, 0, 0, 1), place(CY, 0, 1, 1)),
            noun="table",
            picture="prop.vocab.table",
        ),
        BuildPlan(
            "boat",
            (place(SQ, 0, 0, 0), place(TR, 0, 1, 0), place(HC, 2, 0, 1)),
            noun="boat",
            picture="prop.vocab.boat",
        ),
        BuildPlan(
            "lighthouse",
            (place(TR, 0, 0, 0), place(RE, 1, 0, 1), place(SQ, 0, 0, 3)),
            noun="lighthouse",
            picture="prop.vocab.lighthouse",
        ),
        BuildPlan(
            "house",
            (place(TR, 0, 0, 0), place(TR, 0, 1, 0), place(RE, 0, 0, 1), place(RE, 0, 0, 2)),
            noun="house",
            picture="prop.vocab.house",
        ),
        BuildPlan(
            "train",
            (place(CY, 0, 0, 0), place(SQ, 0, 2, 0), place(RE, 0, 0, 1), place(SQ, 0, 2, 1)),
            noun="train",
            picture="prop.vocab.train",
        ),
        BuildPlan(
            "rocket",
            (place(HC, 0, 0, 0), place(RE, 1, 0, 1), place(RE, 1, 1, 1), place(AR, 0, 0, 3)),
            noun="rocket",
            picture="prop.vocab.rocket",
        ),
        BuildPlan(
            "snail",
            (place(TR, 0, 0, 0), place(SQ, 0, 0, 1), place(HC, 0, 1, 0), place(RE, 0, 1, 1)),
            noun="snail",
            picture="prop.vocab.snail",
        ),
        BuildPlan(
            "house_door",
            (place(TR, 0, 0, 0), place(TR, 0, 1, 0), place(RE, 0, 0, 1), place(AR, 0, 0, 2)),
            noun="house",
            picture="prop.vocab.house",
        ),
        BuildPlan(
            "chair",
            (place(RE, 1, 0, 0), place(RE, 0, 0, 2), place(CY, 0, 0, 3), place(CY, 0, 1, 3)),
            noun="chair",
            picture="prop.vocab.chair",
        ),
        BuildPlan(
            "crown",
            (place(TR, 0, 0, 0), place(TR, 0, 1, 0), place(TR, 0, 2, 0), place(RE, 0, 0, 1), place(SQ, 0, 2, 1)),
            noun="crown",
            picture="prop.vocab.crown",
        ),
        BuildPlan(
            "car",
            (
                place(HC, 0, 1, 0),
                place(RE, 0, 0, 1),
                place(RE, 0, 2, 1),
                place(HC, 2, 0, 2),
                place(HC, 2, 2, 2),
            ),
            noun="car",
            picture="prop.vocab.car",
        ),
        BuildPlan(
            "cat",
            (place(TR, 0, 0, 0), place(TR, 0, 1, 0), place(RE, 0, 0, 1), place(AR, 0, 0, 2), place(RE, 1, 2, 1)),
            noun="cat",
            picture="prop.vocab.cat",
        ),
        BuildPlan(
            "fish",
            (place(HC, 0, 0, 0), place(HC, 2, 0, 1), place(TR, 3, 2, 0), place(TR, 3, 2, 1)),
            noun="fish",
            picture="prop.food.fish",
        ),
        BuildPlan(
            "turtle",
            (
                place(HC, 0, 1, 0),
                place(TR, 3, 0, 1),
                place(RE, 0, 1, 1),
                place(SQ, 0, 3, 1),
                place(CY, 0, 1, 2),
                place(CY, 0, 2, 2),
            ),
            noun="turtle",
            picture="prop.vocab.turtle",
        ),
        BuildPlan(
            "castle",
            (
                place(TR, 0, 0, 0),
                place(TR, 0, 3, 0),
                place(SQ, 0, 0, 1),
                place(RE, 0, 1, 1),
                place(SQ, 0, 3, 1),
                place(SQ, 0, 0, 2),
                place(AR, 0, 1, 2),
                place(SQ, 0, 3, 2),
            ),
        ),
        BuildPlan(
            "robot",
            (
                place(TR, 0, 1, 0),
                place(TR, 0, 2, 0),
                place(RE, 0, 1, 1),
                place(SQ, 0, 0, 2),
                place(RE, 0, 1, 2),
                place(SQ, 0, 3, 2),
                place(RE, 0, 1, 3),
                place(AR, 0, 1, 4),
            ),
        ),
    )
}


class Rung:
    """How one difficulty rung offers a build (outline, kit turns, extras)."""

    def __init__(self, level: int, pool: Sequence[str], style: OutlineStyle, *, turned: str, extras: int) -> None:
        self.level = level
        self.pool = tuple(pool)
        self.style = style
        self.turned = turned  # "none" | "one" | "random"
        self.extras = extras

    def puzzle(self, plan: BuildPlan, rng: random.Random) -> Puzzle:
        used: dict[BlockKind, set[int]] = {}
        for item in plan.placements:
            used.setdefault(item.block.kind, set()).add(item.block.rotation)
        kit: dict[BlockKind, Block] = {
            kind: Block(kind, min(rotations)) for kind, rotations in used.items()
        }
        turnable = [kind for kind in used if len(used[kind]) < TURNS[kind]]
        if self.turned == "one" and turnable:
            kind = rng.choice(sorted(turnable))
            kit[kind] = Block(kind, rng.choice(sorted(set(range(TURNS[kind])) - used[kind])))
        elif self.turned == "random":
            for kind in used:
                kit[kind] = Block(kind, rng.randrange(TURNS[kind]))
            if turnable and all(kit[kind].rotation in used[kind] for kind in turnable):
                kind = rng.choice(sorted(turnable))
                kit[kind] = Block(kind, rng.choice(sorted(set(range(TURNS[kind])) - used[kind])))
        extras = rng.sample(distractor_kinds(plan), min(self.extras, len(distractor_kinds(plan))))
        for kind in extras:
            kit[kind] = Block(kind, rng.randrange(TURNS[kind]))
        blocks = list(kit.values())
        rng.shuffle(blocks)
        return Puzzle(plan, self.style, tuple(blocks))


def distractor_kinds(plan: BuildPlan) -> list[BlockKind]:
    """Kinds that cannot cover any part of ``plan`` in any orientation."""

    tokens = set(plan.fills.values())
    result = []
    for kind in BlockKind:
        own = {token for rotation in range(TURNS[kind]) for _, token in Block(kind, rotation).footprint()}
        if not own & tokens:
            result.append(kind)
    return result


RUNGS: Final[Mapping[int, Rung]] = {
    1: Rung(1, ("igloo", "table", "boat", "lighthouse", "house", "train"), OutlineStyle.SLOTS, turned="none", extras=0),
    2: Rung(2, ("rocket", "snail", "house_door", "chair", "crown", "train"), OutlineStyle.SLOTS, turned="one", extras=0),
    3: Rung(3, ("cat", "car", "fish", "chair", "crown", "snail", "rocket"), OutlineStyle.SLOTS, turned="random", extras=1),
    4: Rung(
        4,
        ("rocket", "cat", "car", "fish", "chair", "crown", "snail", "house_door", "turtle", "train"),
        OutlineStyle.SILHOUETTE,
        turned="random",
        extras=1,
    ),
    5: Rung(5, ("castle", "robot", "turtle", "car", "cat", "crown"), OutlineStyle.SILHOUETTE, turned="random", extras=2),
}


class TorreSetFactory:
    """Build the five puzzles of one set for a rung (seeded, reproducible)."""

    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng if rng is not None else random.Random()
        self._last: tuple[str, ...] = ()

    def build_set(self, level: int) -> tuple[Puzzle, ...]:
        if not 1 <= level <= MAX_LEVEL:
            raise ValueError(f"level must be in 1..{MAX_LEVEL}")
        rung = RUNGS[level]
        pool = list(rung.pool)
        # Prefer builds that were not in the previous set, so replays vary.
        fresh = [build for build in pool if build not in self._last]
        chosen = fresh[:] if len(fresh) >= BUILDS_PER_SET else pool[:]
        self._rng.shuffle(chosen)
        chosen = chosen[:BUILDS_PER_SET]
        chosen.sort(key=lambda build: BUILDS[build].block_count)
        self._last = tuple(chosen)
        return tuple(rung.puzzle(BUILDS[build], self._rng) for build in chosen)


__all__ = ["BUILDS", "RUNGS", "Rung", "TorreSetFactory", "distractor_kinds"]
