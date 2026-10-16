"""Il Viaggio del Delfino — one-pass drawing of the swim, picker and finish.

The renderer owns presentation only. Every surface it blits comes prepared
from ``DelfinoArt`` (scene strips, creatures, pearls, flipbooks) or from the
shared control kit's painter (panels, labels, stars, focus rings); drawing
never decodes, scales, rotates or builds fonts. Localized text arrives already
resolved (and CAPITALISED by the platform case policy) from the app.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Final

import pygame

from greia_platform.activity_controls import BodyShape, ControlKit, mix
from greia_platform.pygame_blit import prepare_static

try:
    from delfino_art import ARCH_SIZE, DelfinoArt, SceneLayers
    from delfino_content import JOURNEYS, REFERENCE_HEIGHT, REFERENCE_WIDTH, SURFACE_Y, JourneySpec
    from delfino_controls import NAME_SIZE, STAR_SIZE, PickerControls
    from delfino_model import FriendState, JourneyRun
except ImportError:  # repository/package import context
    from .delfino_art import ARCH_SIZE, DelfinoArt, SceneLayers
    from .delfino_content import JOURNEYS, REFERENCE_HEIGHT, REFERENCE_WIDTH, SURFACE_Y, JourneySpec
    from .delfino_controls import NAME_SIZE, STAR_SIZE, PickerControls
    from .delfino_model import FriendState, JourneyRun

PEARL_SIZE: Final = 46
#: Every flipbook the swim uses (id, size), warmed at journey start.
SWIM_FX: Final = (
    ("sparkle", 74),
    ("sparkle", 64),
    ("star_burst", 130),
    ("star_burst", 150),
    ("splash", 120),
    ("bubble_pop", 100),
    ("heart_pop", 130),
    ("confetti", 220),
)
COUNT_PEARL: Final = 44
COUNT_GAP: Final = 14
COUNT_PER_ROW: Final = 5
#: Count tray: panel top, the count chip inside it, then the pearl grid.
COUNT_PANEL_TOP: Final = 128
COUNT_CHIP_TOP: Final = 146
COUNT_GRID_TOP: Final = 232
#: Where the finish props stand relative to the finish line (world px).
_LANDMARK_PLACES: Final = {
    "prop.vocab.lighthouse": ((150, 168), 330, int(SURFACE_Y) + 16),
    "prop.vocab.island": ((330, 230), 320, int(SURFACE_Y) + 40),
    "prop.everyday.shell": ((150, 130), 520, 586),
}
_INK: Final = (75, 55, 47)
_WAKE: Final = (236, 250, 255)


@dataclass(slots=True)
class Effect:
    """One shared ``fx.*`` flipbook at a world point (bounded list in the app)."""

    frames: list[pygame.Surface]
    x: float
    y: float
    duration: float = 0.6
    age: float = 0.0
    screen: bool = False

    @property
    def done(self) -> bool:
        return self.age >= self.duration or not self.frames

    def draw(self, surface: pygame.Surface, camera_x: float) -> None:
        if self.done:
            return
        index = min(len(self.frames) - 1, int(self.age / self.duration * len(self.frames)))
        frame = self.frames[index]
        x = self.x if self.screen else self.x - camera_x
        surface.blit(frame, frame.get_rect(center=(int(x), int(self.y))))


@dataclass(slots=True)
class SwimView:
    """Per-frame presentation hints decided by the app."""

    now: float
    happy: bool = False
    hint_target: tuple[float, float] | None = None
    steer_hint: bool = False
    leap_hint: bool = False
    effects: list[Effect] = field(default_factory=list)


@dataclass(slots=True)
class CountView:
    """Finish count-up: ``shown`` pearls already in the tray, one flying in."""

    total: int
    shown: int
    flight: float  # 0..1 progress of the pearl currently flying in


class DelfinoRenderer:
    """Composite the swim, the journey picker and the finish count-up."""

    def __init__(self, art: DelfinoArt, kit: ControlKit) -> None:
        self.art = art
        self.kit = kit
        self._faded: dict[tuple[str, int], pygame.Surface | None] = {}
        self._panels: dict[tuple[int, int], pygame.Surface] = {}
        self._picker_backdrop: pygame.Surface | None = None

    # -- helpers -------------------------------------------------------------

    def _glyph(self, glyph_id: str, size: int, *, faded: bool = False) -> pygame.Surface | None:
        key = (glyph_id, size if not faded else -size)
        if key in self._faded:
            return self._faded[key]
        image = self.kit.glyph(glyph_id, size)
        if image is not None and faded:
            image = image.copy()
            image.fill((255, 255, 255, 105), special_flags=pygame.BLEND_RGBA_MULT)
        if image is not None:
            image = prepare_static(image)
        self._faded[key] = image
        return image

    def _panel(self, size: tuple[int, int]) -> pygame.Surface:
        panel = self._panels.get(size)
        if panel is None:
            painter = self.kit.painter
            panel = prepare_static(
                painter.body(BodyShape.PANEL, size, painter.theme.surface, lip=6, contour_width=4, highlight=False)
            )
            if len(self._panels) > 8:
                self._panels.clear()
            self._panels[size] = panel
        return panel

    # -- swim ----------------------------------------------------------------

    def draw_swim(self, surface: pygame.Surface, run: JourneyRun, scene: SceneLayers, view: SwimView) -> None:
        art = self.art
        camera = run.camera_x
        scene.draw_back(surface, camera)
        self._draw_finish(surface, run.spec, run.course.finish_x - camera)

        jelly_idle = art.jelly(happy=False)
        jelly_happy = art.jelly(happy=True)
        for jelly in run.course.jellies:
            sx = jelly.x - camera
            if -80 <= sx <= REFERENCE_WIDTH + 80:
                sprite = jelly_happy if jelly.happy_timer > 0 else jelly_idle
                if sprite is not None:
                    surface.blit(sprite, sprite.get_rect(center=(int(sx), int(jelly.effective_y))))

        pearl = art.pearl(PEARL_SIZE)
        if pearl is not None:
            for item in run.course.pearls:
                sx = item.x - camera
                if not item.collected and -40 <= sx <= REFERENCE_WIDTH + 40:
                    surface.blit(pearl, pearl.get_rect(center=(int(sx), int(item.effective_y))))

        for friend in run.course.friends:
            if friend.state in (FriendState.AHEAD, FriendState.GONE):
                continue
            sx = friend.x - camera
            if not -260 <= sx <= REFERENCE_WIDTH + 260:
                continue
            sprite = art.creature(friend.spec.visual, friend.spec.box, happy=friend.happy, facing_right=friend.facing_right)
            if sprite is None:
                continue
            rect = sprite.get_rect(center=(int(sx), int(friend.draw_y)))
            surface.blit(sprite, rect)
            if friend.state is FriendState.WAITING:
                frames = art.fx_frames("sparkle", 64)
                if frames:
                    frame = frames[int(view.now * 5) % len(frames)]
                    surface.blit(frame, frame.get_rect(center=(rect.right - 6, rect.top + 4)))

        for x, y, age in run.wake:
            radius = 3 + int(age * 5)
            sx = int(x - camera)
            pygame.draw.circle(surface, _WAKE, (sx, int(y - age * 26)), radius, 2)

        dolphin = run.dolphin
        bob = 0 if dolphin.airborne else int(math.sin(dolphin.swim_phase) * 3)
        sprite = art.dolphin(dolphin.pitch, happy=view.happy)
        if sprite is not None:
            surface.blit(sprite, sprite.get_rect(center=(int(dolphin.x - camera), int(dolphin.y) + bob)))

        for effect in view.effects:
            effect.draw(surface, camera)

        if view.hint_target is not None:
            self._draw_hint_ring(surface, (view.hint_target[0] - camera, view.hint_target[1]), view.now)
        if view.steer_hint or view.leap_hint:
            self._draw_controls_hint(surface, view)

    def _draw_finish(self, surface: pygame.Surface, spec: JourneySpec, finish_sx: float) -> None:
        if finish_sx > REFERENCE_WIDTH + 700 or finish_sx < -900:
            return
        place = _LANDMARK_PLACES.get(spec.landmark or "")
        if place is not None and spec.landmark is not None:
            box, offset, bottom = place
            landmark = self.art.prop(spec.landmark, box)
            if landmark is not None:
                surface.blit(landmark, landmark.get_rect(midbottom=(int(finish_sx + offset), bottom)))
        arch = self.art.finish_arch()
        if arch is not None:
            surface.blit(arch, arch.get_rect(midbottom=(int(finish_sx), REFERENCE_HEIGHT - 6)))

    def _draw_hint_ring(self, surface: pygame.Surface, centre: tuple[float, float], now: float) -> None:
        # Two cached ring sizes alternate: a gentle pulse without scaling.
        size = 96 if int(now * 3) % 2 == 0 else 110
        ring = self.kit.painter.focus_ring((size, size), size // 2)
        surface.blit(ring, ring.get_rect(center=(int(centre[0]), int(centre[1]))))

    def _draw_controls_hint(self, surface: pygame.Surface, view: SwimView) -> None:
        """Wordless how-to cards.

        Steering (up / down with a bobbing mini dolphin) sits in the sky,
        above every underwater pearl group; the leap card (Space / A with a
        hopping mini dolphin) sits low over the sand, so it never covers the
        pearl arc it is announcing.
        """

        width, height = 236, 112
        mini = self.art.creature("creature.marine.dolphin", (76, 38))
        if view.steer_hint:
            x, y = REFERENCE_WIDTH // 2 - width // 2, 70
            surface.blit(self._panel((width, height)), (x, y))
            face = pygame.Rect(x, y, width, height - 6)
            phase = int(view.now / 0.6) % 2
            up = self._glyph("arrow_up", 44, faded=phase != 0)
            down = self._glyph("arrow_down", 44, faded=phase != 1)
            if up is not None:
                surface.blit(up, up.get_rect(center=(face.x + 44, face.centery - 23)))
            if down is not None:
                surface.blit(down, down.get_rect(center=(face.x + 44, face.centery + 23)))
            if mini is not None:
                dy = -18 if phase == 0 else 18
                surface.blit(mini, mini.get_rect(center=(face.x + 160, face.centery + dy)))
        if view.leap_hint:
            x, y = REFERENCE_WIDTH // 2 - width // 2 + 60, REFERENCE_HEIGHT - height - 10
            surface.blit(self._panel((width, height)), (x, y))
            face = pygame.Rect(x, y, width, height - 6)
            space = self._glyph("key_space", 54)
            button = self._glyph("button_a", 46)
            if space is not None:
                surface.blit(space, space.get_rect(center=(face.x + 42, face.centery)))
            if button is not None:
                surface.blit(button, button.get_rect(center=(face.x + 98, face.centery)))
            t = (view.now % 1.4) / 1.4
            hop = math.sin(t * math.pi)
            sprite = self.art.dolphin_mini(26 - 52 * t) or mini
            if sprite is not None:
                centre = (face.x + 140 + int(t * 64), face.bottom - 26 - int(hop * 46))
                surface.blit(sprite, sprite.get_rect(center=centre))

    # -- count-up ------------------------------------------------------------

    @staticmethod
    def count_rows(total: int) -> int:
        return max(1, math.ceil(total / COUNT_PER_ROW))

    def count_slot(self, index: int, total: int) -> tuple[int, int]:
        """Centre of pearl ``index`` in the count tray (rows of five)."""

        row, column = divmod(index, COUNT_PER_ROW)
        width = COUNT_PER_ROW * COUNT_PEARL + (COUNT_PER_ROW - 1) * COUNT_GAP
        left = REFERENCE_WIDTH // 2 - width // 2
        return (
            left + column * (COUNT_PEARL + COUNT_GAP) + COUNT_PEARL // 2,
            COUNT_GRID_TOP + row * (COUNT_PEARL + COUNT_GAP) + COUNT_PEARL // 2,
        )

    def draw_count(self, surface: pygame.Surface, view: CountView, origin: tuple[int, int]) -> None:
        rows = self.count_rows(view.total)
        grid_h = rows * COUNT_PEARL + (rows - 1) * COUNT_GAP
        panel = self._panel((400, COUNT_GRID_TOP - COUNT_PANEL_TOP + grid_h + 34))
        surface.blit(panel, panel.get_rect(midtop=(REFERENCE_WIDTH // 2, COUNT_PANEL_TOP)))
        pearl = self.art.pearl(COUNT_PEARL)
        if pearl is None:
            return
        for index in range(min(view.shown, view.total)):
            surface.blit(pearl, pearl.get_rect(center=self.count_slot(index, view.total)))
        if view.shown < view.total:
            tx, ty = self.count_slot(view.shown, view.total)
            t = max(0.0, min(1.0, view.flight))
            x = origin[0] + (tx - origin[0]) * t
            y = origin[1] + (ty - origin[1]) * t - math.sin(t * math.pi) * 60
            surface.blit(pearl, pearl.get_rect(center=(int(x), int(y))))

    # -- picker --------------------------------------------------------------

    def picker_backdrop(self) -> pygame.Surface:
        if self._picker_backdrop is None:
            self._picker_backdrop = self.art.picker_backdrop()
        return self._picker_backdrop

    def draw_picker(
        self,
        surface: pygame.Surface,
        picker: PickerControls,
        records: dict[str, int],
        unlocked: tuple[str, ...],
        suggested: str,
        now: float,
    ) -> None:
        surface.blit(self.picker_backdrop(), (0, 0))
        painter = self.kit.painter
        theme = painter.theme
        small_pearl = self.art.pearl(18)
        specs = list(JOURNEYS)
        for index, spec in enumerate(specs):
            rect = picker.rect(spec.journey_id)
            is_open = spec.journey_id in unlocked
            color = theme.text if is_open else mix(theme.text, theme.muted, 0.55)
            name = painter.label(picker.names.get(spec.journey_id, ""), NAME_SIZE, color, max_width=rect.width)
            plate = self._panel((rect.width, name.get_height() + 16))
            surface.blit(plate, (rect.x, rect.bottom + 8))
            surface.blit(name, name.get_rect(center=(rect.centerx, rect.bottom + 8 + (name.get_height() + 10) // 2)))
            earned = records.get(spec.journey_id, 0)
            star_y = rect.bottom + 8 + plate.get_height() + 6 + STAR_SIZE // 2
            for star_index in range(3):
                star = self.kit.star(STAR_SIZE, filled=star_index < earned)
                surface.blit(star, star.get_rect(center=(rect.centerx + (star_index - 1) * (STAR_SIZE + 6), star_y)))
            if index + 1 < len(specs) and small_pearl is not None:
                gap_left = rect.right
                gap_right = picker.rect(specs[index + 1].journey_id).left
                for step in range(3):
                    px = gap_left + (gap_right - gap_left) * (step + 1) // 4
                    surface.blit(small_pearl, small_pearl.get_rect(center=(px, rect.centery)))
        rect = picker.rect(suggested)
        frames = self.art.fx_frames("sparkle", 72)
        if frames:
            frame = frames[int(now * 4) % len(frames)]
            bob = int(math.sin(now * 3.0) * 4)
            surface.blit(frame, frame.get_rect(center=(rect.right - 10, rect.top + 6 + bob)))


__all__ = ["CountView", "DelfinoRenderer", "Effect", "PEARL_SIZE", "SWIM_FX", "SwimView", "ARCH_SIZE"]
