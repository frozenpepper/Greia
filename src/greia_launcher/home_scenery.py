"""Renderer-free geometry for the interactive Home meadow scenery.

The Home backdrop is the 1024x600 ``bg.meadow_day.home`` rendition, COVER
fitted to the screen (see ``SharedUiShellPanelMixin._shell_scene_layer``).
This module owns the *scene-space* facts the Home animator needs — where the
sun, the apple tree, its apples and the two drifting sky clouds are in that
artwork — and maps them to screen pixels with the exact same cover transform.

It also decides which pieces of scenery may be interactive on a given screen:
scenery is decoration, so any piece whose animation would touch a Collection
portal, the protected corner controls or the top HUD row is simply switched
off (targets and system chrome always win over decoration).

Pure data and arithmetic only: no pygame import, no IO.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable, Sequence

from greia_platform.responsive_layout import UiRect


SCENE_SOURCE_SIZE = (1024, 600)

# Scene-space facts read from
# assets/visual/environments/meadow_day/v0.1/home_landscape.svg (keep in sync
# with that artwork; the tree group is translated by -34 px there).
SUN_CENTER = (902, 206)
SUN_RADIUS = 32
SUN_HIT_RADIUS = 48
TREE_CROWN = UiRect(840, 290, 176, 142)
TREE_APPLE_SPOTS = ((894, 378), (944, 344), (966, 390))
TREE_GROUND_Y = 486
APPLE_SIZE = 28
SPARKLE_SIZE = 44
DUST_SIZE = 46


@dataclass(frozen=True, slots=True)
class CloudSpec:
    """One drifting sky cloud, in scene space.

    The cloud rests at ``center`` and drifts horizontally on a slow sine of
    ``amplitude`` pixels whose peak speed is ``speed`` px/s, so it reads as a
    lazy drift that never leaves its patch of free sky.
    """

    asset_id: str
    center: tuple[int, int]
    size: tuple[int, int]
    amplitude: int
    speed: float
    phase: float = 0.0

    @property
    def period(self) -> float:
        return 2.0 * math.pi * self.amplitude / self.speed

    def offset_at(self, drift_seconds: float) -> float:
        """Horizontal scene offset after ``drift_seconds`` of awake drift."""

        return self.amplitude * math.sin(
            2.0 * math.pi * (drift_seconds / self.period + self.phase)
        )


# Two depths: a larger, slower cloud in the free left sky (above the
# greeter, below the profile badge) and a small, quicker one drifting past the
# sun on the right (below the achievement star / HUD row).
CLOUDS = (
    CloudSpec("cloud.large.01", center=(110, 228), size=(130, 52), amplitude=22, speed=6.0),
    CloudSpec(
        "cloud.small.01", center=(916, 134), size=(100, 43), amplitude=22, speed=10.0, phase=0.3
    ),
)
# A tapped cloud puffs up by this factor for a moment.
CLOUD_PUFF_SCALE = 1.1


@dataclass(frozen=True, slots=True)
class SceneCover:
    """Scene-space -> screen-space mapping for the COVER-fitted backdrop.

    Mirrors the crop used when the backdrop is composed: scale to cover the
    screen, centre horizontally, anchor to the bottom (the ground stays
    visible on very wide screens).
    """

    width: int
    height: int
    crop: UiRect

    @classmethod
    def fit(
        cls, size: tuple[int, int], source: tuple[int, int] = SCENE_SOURCE_SIZE
    ) -> "SceneCover":
        width, height = size
        source_w, source_h = source
        scale = max(width / source_w, height / source_h)
        crop_w = max(1, min(source_w, int(round(width / scale))))
        crop_h = max(1, min(source_h, int(round(height / scale))))
        crop = UiRect((source_w - crop_w) // 2, source_h - crop_h, crop_w, crop_h)
        return cls(width, height, crop)

    @property
    def scale(self) -> float:
        return self.width / self.crop.width

    def point(self, x: float, y: float) -> tuple[int, int]:
        return (
            int(round((x - self.crop.x) * self.width / self.crop.width)),
            int(round((y - self.crop.y) * self.height / self.crop.height)),
        )

    def length(self, value: float) -> int:
        return max(1, int(round(value * self.scale)))

    def rect(self, rect: UiRect) -> UiRect:
        x, y = self.point(rect.x, rect.y)
        right, bottom = self.point(rect.x + rect.width, rect.y + rect.height)
        return UiRect(x, y, max(1, right - x), max(1, bottom - y))

    def centered(self, center: tuple[float, float], size: tuple[float, float]) -> UiRect:
        cx, cy = self.point(*center)
        w, h = self.length(size[0]), self.length(size[1])
        return UiRect(cx - w // 2, cy - h // 2, w, h)


def _intersects(a: UiRect, b: UiRect) -> bool:
    return a.x < b.x + b.width and b.x < a.x + a.width and a.y < b.y + b.height and b.y < a.y + a.height


def _clear(area: UiRect, blocked: Iterable[UiRect], screen: UiRect) -> bool:
    if not screen.contains(area):
        return False
    return not any(_intersects(area, block) for block in blocked)


@dataclass(frozen=True, slots=True)
class HomeSceneryLayout:
    """Which scenery is interactive on this screen, and where (screen px).

    ``None`` fields mean that piece of scenery stays decoration only because
    its animation would collide with a target, protected chrome or the HUD.
    """

    cover: SceneCover
    sun_center: tuple[int, int] | None
    sun_hit_radius: int
    sun_area: UiRect | None
    tree_hit: UiRect | None
    tree_area: UiRect | None
    apple_spots: tuple[tuple[int, int], ...]
    apple_ground_y: int
    clouds: tuple[tuple[CloudSpec, UiRect], ...]

    @classmethod
    def compute(
        cls,
        size: tuple[int, int],
        blocked: Sequence[UiRect],
    ) -> "HomeSceneryLayout":
        """Resolve scenery for ``size``; ``blocked`` are screen rects to avoid."""

        cover = SceneCover.fit(size)
        screen = UiRect(0, 0, size[0], size[1])
        margin = cover.length(8)
        blocked = tuple(
            UiRect(b.x - margin, b.y - margin, b.width + 2 * margin, b.height + 2 * margin)
            for b in blocked
        )

        # Sun: sparkles burst within ~1.6 sun radii of the centre.
        reach = SUN_RADIUS * 1.6 + SPARKLE_SIZE / 2
        sun_area = cover.centered(SUN_CENTER, (2 * reach, 2 * reach))
        sun_ok = _clear(sun_area, blocked, screen)

        # Tree: apples fall from the crown to the ground; dust and sparkles
        # stay inside the crown's horizontal span.
        tree_area = cover.rect(
            UiRect(
                TREE_CROWN.x,
                min(y for _, y in TREE_APPLE_SPOTS) - APPLE_SIZE,
                TREE_CROWN.width,
                TREE_GROUND_Y + DUST_SIZE // 2 - (min(y for _, y in TREE_APPLE_SPOTS) - APPLE_SIZE),
            )
        )
        tree_ok = _clear(tree_area, blocked, screen) and _clear(
            cover.rect(TREE_CROWN), blocked, screen
        )

        clouds: list[tuple[CloudSpec, UiRect]] = []
        for spec in CLOUDS:
            sweep = cover.centered(
                spec.center,
                (
                    spec.size[0] * CLOUD_PUFF_SCALE + 2 * spec.amplitude,
                    spec.size[1] * CLOUD_PUFF_SCALE,
                ),
            )
            if _clear(sweep, blocked, screen):
                clouds.append((spec, sweep))

        return cls(
            cover=cover,
            sun_center=cover.point(*SUN_CENTER) if sun_ok else None,
            sun_hit_radius=cover.length(SUN_HIT_RADIUS),
            sun_area=sun_area if sun_ok else None,
            tree_hit=cover.rect(TREE_CROWN) if tree_ok else None,
            tree_area=tree_area if tree_ok else None,
            apple_spots=tuple(cover.point(*spot) for spot in TREE_APPLE_SPOTS) if tree_ok else (),
            apple_ground_y=cover.point(0, TREE_GROUND_Y)[1],
            clouds=tuple(clouds),
        )
