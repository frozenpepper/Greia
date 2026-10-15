"""Festival scene presentation for Festa delle Rime.

Draw order: cached night-square backdrop + garland string → festival lanterns
(dark, or lit with the rhyme found) → big target lantern (word picture, or the
listening ear for odd-one-out) → Leo → speaking/hint glows → kit controls →
FX (sparkle, flight to the garland, star burst, finale fireworks).

All surfaces are pre-scaled through ``RhymeArt``; per-frame work is blits and
a few integer offsets. Nothing here renders text: the game is pictorial and
spoken.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Final, Sequence

import pygame

if __package__:
    from .rhyme_art import RhymeArt
    from .rhyme_content import RhymeItem, RhymeMode
    from .rhyme_controls import (
        LEO_HEIGHT,
        LEO_MIDBOTTOM,
        PICTURE_SIZE,
        TARGET_PICTURE,
        FestivalLayout,
    )
    from .rhyme_model import RhymeChallenge
else:
    from rhyme_art import RhymeArt
    from rhyme_content import RhymeItem, RhymeMode
    from rhyme_controls import (
        LEO_HEIGHT,
        LEO_MIDBOTTOM,
        PICTURE_SIZE,
        TARGET_PICTURE,
        FestivalLayout,
    )
    from rhyme_model import RhymeChallenge


INK: Final = (75, 55, 47)
FLIGHT_SIZE: Final = 64
SPEAKING_LIFT: Final = 10
SLOT_PICTURE_RATIO: Final = 0.46
# Lantern body centre in the 256-unit lantern master (y 138 of 256).
LANTERN_BODY_Y: Final = 138 / 256


@dataclass(frozen=True, slots=True)
class SceneState:
    """Everything the renderer needs for one frame (built by the app)."""

    challenge: RhymeChallenge | None
    found: Sequence[RhymeItem]
    speaking: str | None = None
    hint_target: str | None = None
    pulse_phase: int = 0
    shake: tuple[str, int] | None = None
    sparkle_at: tuple[tuple[int, int], float] | None = None
    flight: tuple[RhymeItem, tuple[int, int], tuple[int, int], float] | None = None
    burst_slot: tuple[int, float] | None = None
    fireworks: float | None = None
    leo_pointing: bool = False


class RhymeRenderer:
    """Render the festival square; geometry comes from ``FestivalLayout``."""

    def __init__(self, art: RhymeArt) -> None:
        self._art = art
        self.cast = None  # CastFeedback, injected by the app (shares the kit art cache)
        self._garland: pygame.Surface | None = None
        self._garland_key: tuple | None = None
        self._point = art.cast_pose("leo", "pose_point", LEO_HEIGHT)

    @property
    def art(self) -> RhymeArt:
        return self._art

    # -- caches -----------------------------------------------------------------
    def _garland_layer(self, geometry: FestivalLayout) -> pygame.Surface:
        """Backdrop + garland string + target cord, rebuilt only on relayout."""

        key = (geometry.garland_left, geometry.garland_right, geometry.garland_top, geometry.target.topleft)
        if self._garland is not None and self._garland_key == key:
            return self._garland
        surface = self._art.background.copy()
        points = [
            (x, geometry.string_y(x))
            for x in range(geometry.garland_left - 18, geometry.garland_right + 19, 12)
        ]
        pygame.draw.lines(surface, INK, False, points, 4)
        cord_x = geometry.target.centerx
        pygame.draw.line(surface, INK, (cord_x, geometry.string_y(cord_x)), (cord_x, geometry.target.top + 8), 4)
        self._garland = surface
        self._garland_key = key
        return surface

    # -- frame ----------------------------------------------------------------------
    def draw_scene(
        self,
        target: pygame.Surface,
        geometry: FestivalLayout,
        state: SceneState,
        *,
        draw_controls,
    ) -> None:
        target.blit(self._garland_layer(geometry), (0, 0))
        self._draw_garland(target, geometry, state)
        self._draw_target(target, geometry, state)
        self._draw_leo(target, state)
        self._draw_choice_glows(target, state)
        draw_controls(target, _control_offsets(state))
        self._draw_fx(target, geometry, state)

    def _draw_garland(self, target: pygame.Surface, geometry: FestivalLayout, state: SceneState) -> None:
        lit_count = len(state.found)
        for index, slot in enumerate(geometry.slots):
            lit = index < lit_count
            lantern = self._art.lantern(lit, slot.width)
            if lantern is None:
                continue
            if lit:
                glow = self._art.glow(int(slot.width * 1.5))
                target.blit(glow, glow.get_rect(center=(slot.centerx, slot.top + int(slot.height * LANTERN_BODY_Y))))
            target.blit(lantern, slot.topleft)
            if lit:
                picture = self._art.picture(state.found[index], int(slot.width * SLOT_PICTURE_RATIO))
                if picture is not None:
                    center = (slot.centerx, slot.top + int(slot.height * LANTERN_BODY_Y))
                    target.blit(picture, picture.get_rect(center=center))

    def _draw_target(self, target: pygame.Surface, geometry: FestivalLayout, state: SceneState) -> None:
        rect = geometry.target
        body_center = (rect.centerx, rect.top + int(rect.height * LANTERN_BODY_Y))
        glowing = state.speaking == "target" or (state.hint_target == "target" and state.pulse_phase % 2 == 0)
        glow = self._art.glow(int(rect.width * (1.32 if glowing else 1.12)))
        target.blit(glow, glow.get_rect(center=body_center))
        lantern = self._art.lantern(True, rect.width)
        if lantern is not None:
            target.blit(lantern, rect.topleft)
        challenge = state.challenge
        if challenge is None:
            return
        if challenge.mode is RhymeMode.RHYME_ODD or challenge.target_item is None:
            picture = self._art.ear(int(TARGET_PICTURE * 0.9))
        else:
            picture = self._art.picture(challenge.target_item, TARGET_PICTURE)
        if picture is not None:
            lift = -4 if state.speaking == "target" else 0
            target.blit(picture, picture.get_rect(center=(body_center[0], body_center[1] + lift)))

    def _draw_leo(self, target: pygame.Surface, state: SceneState) -> None:
        cast = self.cast
        if state.leo_pointing and self._point is not None and (cast is None or not cast.animating):
            target.blit(self._point, self._point.get_rect(midbottom=LEO_MIDBOTTOM))
            return
        if cast is not None:
            cast.draw(target, LEO_MIDBOTTOM)

    def _draw_choice_glows(self, target: pygame.Surface, state: SceneState) -> None:
        challenge = state.challenge
        if challenge is None:
            return
        count = len(challenge.choices)
        for index in range(count):
            tag = f"choice.{index}"
            speaking = state.speaking == tag
            hinted = state.hint_target == tag
            if not speaking and not hinted:
                continue
            big = speaking or state.pulse_phase % 2 == 0
            rect = FestivalLayout.choice_rect(count, index).move(0, -SPEAKING_LIFT if speaking else 0)
            glow = self._art.glow(int(rect.width * (1.62 if big else 1.4)))
            target.blit(glow, glow.get_rect(center=rect.center))

    def _draw_fx(self, target: pygame.Surface, geometry: FestivalLayout, state: SceneState) -> None:
        if state.sparkle_at is not None:
            (x, y), t = state.sparkle_at
            size = int(PICTURE_SIZE * (0.9 + 0.5 * min(1.0, t)))
            sparkle = self._art.fx("fx.sparkle", _bucket(size))
            if sparkle is not None:
                target.blit(sparkle, sparkle.get_rect(center=(x, y - int(18 * t))))
        if state.flight is not None:
            item, start, end, t = state.flight
            t = max(0.0, min(1.0, t))
            ease = 1 - (1 - t) ** 2
            control = ((start[0] + end[0]) / 2, min(start[1], end[1]) - 120)
            x = (1 - ease) ** 2 * start[0] + 2 * (1 - ease) * ease * control[0] + ease ** 2 * end[0]
            y = (1 - ease) ** 2 * start[1] + 2 * (1 - ease) * ease * control[1] + ease ** 2 * end[1]
            picture = self._art.picture(item, FLIGHT_SIZE)
            if picture is not None:
                target.blit(picture, picture.get_rect(center=(int(x), int(y))))
        if state.burst_slot is not None:
            index, t = state.burst_slot
            if 0 <= index < len(geometry.slots):
                slot = geometry.slots[index]
                burst = self._art.fx("fx.star_burst", _bucket(int(slot.width * (1.3 + 0.6 * min(1.0, t)))))
                if burst is not None:
                    center = (slot.centerx, slot.top + int(slot.height * LANTERN_BODY_Y))
                    target.blit(burst, burst.get_rect(center=center))
        if state.fireworks is not None:
            self._draw_fireworks(target, state.fireworks)

    def _draw_fireworks(self, target: pygame.Surface, elapsed: float) -> None:
        # Three staggered bursts over the square, each cycling the three frames.
        spots = ((300, 190, 0.0), (760, 150, 0.35), (520, 120, 0.7), (880, 260, 1.0), (240, 300, 1.25))
        for x, y, delay in spots:
            local = elapsed - delay
            if local < 0 or local >= 0.9:
                continue
            frame = ("default", "frame_2", "frame_3")[min(2, int(local / 0.3))]
            image = self._art.fx("fx.firework", 176, variant=frame)
            if image is not None:
                target.blit(image, image.get_rect(center=(x, y)))


def _control_offsets(state: SceneState) -> dict[str, tuple[int, int]]:
    """Per-control draw offsets: the spoken picture lifts, a wrong pick shakes."""

    offsets: dict[str, tuple[int, int]] = {}
    if state.speaking is not None and state.speaking.startswith("choice."):
        offsets[state.speaking] = (0, -SPEAKING_LIFT)
    if state.shake is not None:
        control_id, dx = state.shake
        offsets[control_id] = (dx, 0)
    return offsets


def _bucket(size: int) -> int:
    """Quantise animated FX sizes so only a few scaled copies are ever cached."""

    return max(16, int(math.ceil(size / 24.0) * 24))


__all__ = ["RhymeRenderer", "SceneState"]
