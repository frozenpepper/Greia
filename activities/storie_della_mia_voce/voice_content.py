"""Storie della Mia Voce — scene catalogue + activity content.

The Activity is built around four scene cards. Each card is a
real Greia scene illustration (palette + colour cue) that the
child picks to record a story for. The catalogue is small on
purpose so the pre-reader can scan it without text.

A scene has no embedded content; the child's recording is the
content. The metadata is the scene's identity (so the library
can label each saved story by its four scene ids) and its
primary colour (so the renderer can show a colourful chip
without depending on bitmap art).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final


REFERENCE_WIDTH: Final = 1024
REFERENCE_HEIGHT: Final = 600

# Layout
SCENE_CARD_SIZE: Final = 180
SCENE_CARD_GAP: Final = 22
SCENE_CARDS_TOP: Final = 200
SCENE_CARDS_LEFT: Final = (
    REFERENCE_WIDTH - (4 * SCENE_CARD_SIZE + 3 * SCENE_CARD_GAP)
) // 2

# Recording limits
MAX_RECORDING_SECONDS: Final = 30.0
MIN_RECORDING_SECONDS: Final = 0.4
MAX_SAVED_STORIES: Final = 12


class SceneId(StrEnum):
    FOREST = "forest"
    SEA = "sea"
    SKY = "sky"
    FRIENDS = "friends"


@dataclass(frozen=True, slots=True)
class Scene:
    """A scene card the child can pick to record their story for."""

    scene_id: SceneId
    title_key: str
    label_key: str
    primary_color: tuple[int, int, int]
    secondary_color: tuple[int, int, int]


SCENES: Final[tuple[Scene, ...]] = (
    Scene(
        scene_id=SceneId.FOREST,
        title_key="ui.scene_forest",
        label_key="ui.scene_forest",
        primary_color=(34, 197, 94),
        secondary_color=(132, 204, 22),
    ),
    Scene(
        scene_id=SceneId.SEA,
        title_key="ui.scene_sea",
        label_key="ui.scene_sea",
        primary_color=(56, 189, 248),
        secondary_color=(14, 165, 233),
    ),
    Scene(
        scene_id=SceneId.SKY,
        title_key="ui.scene_sky",
        label_key="ui.scene_sky",
        primary_color=(250, 204, 21),
        secondary_color=(245, 158, 11),
    ),
    Scene(
        scene_id=SceneId.FRIENDS,
        title_key="ui.scene_friends",
        label_key="ui.scene_friends",
        primary_color=(236, 72, 153),
        secondary_color=(217, 70, 239),
    ),
)


SCENES_BY_ID: Final[dict[SceneId, Scene]] = {s.scene_id: s for s in SCENES}
SCENE_IDS: Final[tuple[SceneId, ...]] = tuple(s.scene_id for s in SCENES)
