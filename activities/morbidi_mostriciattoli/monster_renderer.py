"""Presentation for Fluffy Monsters: scenes, the living friend and FX.

The renderer only blits prepared surfaces: the studio paper and the playroom
stage (shared ``bg.indoor_room`` layers) are composed once per layout; the
friend comes from ``MonsterArt``'s bounded caches; text (the friend's name)
comes from the kit painter's bounded label cache. ``FriendMotion`` turns the
friend's reactions (boing when a part pops on, giggle when tickled, hops when
saved, an occasional blink) into a cached frame choice plus a blit offset —
never a per-frame scale, decode or font construction.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
import math
import random
import time
from typing import Final

import pygame

from greia_platform.activity_controls import ControlArt, ControlPainter, mix
from greia_platform.activity_feedback import CastFeedback
from greia_platform.child_text import display_text
from greia_platform.ui_core import BoundedCache

if __package__:
    from .monster_art import BOX_H, BOX_W, MonsterArt
    from .monster_content import REFERENCE_HEIGHT, REFERENCE_WIDTH, SYLLABLE_COLORS
    from .monster_layout import FriendLayout, GalleryLayout, SheetLayout, StudioLayout
else:
    from monster_art import BOX_H, BOX_W, MonsterArt
    from monster_content import REFERENCE_HEIGHT, REFERENCE_WIDTH, SYLLABLE_COLORS
    from monster_layout import FriendLayout, GalleryLayout, SheetLayout, StudioLayout

INK: Final = (75, 55, 47)
COCOA: Final = (61, 44, 31)
CREAM: Final = (255, 249, 236)
PAPER_TOP: Final = (252, 246, 232)
PAPER_BOTTOM: Final = (244, 232, 208)
HALO: Final = (255, 214, 102)
FX_SIZES: Final[dict[str, int]] = {"sparkle": 120, "heart_pop": 120, "confetti": 300, "star_burst": 170}
PICTURE_SIZE: Final = (800, 600)

BOING_SECONDS: Final = 0.42
GIGGLE_SECONDS: Final = 0.9
HOP_SECONDS: Final = 1.6
BLINK_SECONDS: Final = 0.14


def monster_rect(midbottom: tuple[int, int], height: int) -> pygame.Rect:
    """Where the friend's composition box is drawn."""

    width = round(BOX_W * height / BOX_H)
    rect = pygame.Rect(0, 0, width, height)
    rect.midbottom = midbottom
    return rect


def body_rect(midbottom: tuple[int, int], height: int) -> pygame.Rect:
    """The friend's tickle target (body area inside the box)."""

    box = monster_rect(midbottom, height)
    return pygame.Rect(box.left + round(box.width * 0.2), box.top + round(box.height * 0.18), round(box.width * 0.6), round(box.height * 0.72))


@dataclass(slots=True)
class FriendFrame:
    blink: bool = False
    laugh: bool = False
    squash: str | None = None  # "squash" | "stretch"
    offset: tuple[int, int] = (0, 0)


class FriendMotion:
    """The friend's little life: reactions + idle blinks (clock-driven)."""

    def __init__(self, clock: Callable[[], float], rng: random.Random) -> None:
        self._clock = clock
        self._rng = rng
        self.kind = ""
        self.since = 0.0
        self.next_blink = clock() + 2.5
        self._last: tuple = ()

    def react(self, kind: str) -> None:
        self.kind = kind
        self.since = self._clock()

    def stop(self) -> None:
        self.kind = ""

    @property
    def reacting(self) -> bool:
        if not self.kind:
            return False
        limit = {"boing": BOING_SECONDS, "giggle": GIGGLE_SECONDS, "hop": HOP_SECONDS}.get(self.kind, 0.5)
        return self._clock() - self.since < limit

    def frame(self) -> FriendFrame:
        now = self._clock()
        if self.reacting:
            t = now - self.since
            if self.kind == "boing":
                if t < 0.09:
                    return FriendFrame(laugh=True, squash="squash")
                if t < 0.22:
                    return FriendFrame(laugh=True, squash="stretch", offset=(0, -14))
                return FriendFrame(laugh=True, offset=(0, -round(10 * (BOING_SECONDS - t) / BOING_SECONDS)))
            if self.kind == "giggle":
                phase = int(t / 0.1) % 2
                shake = round(5 * math.sin(t * 40))
                return FriendFrame(blink=True, laugh=True, squash="squash" if phase else "stretch", offset=(shake, -4 * phase))
            if self.kind == "hop":
                cycle = (t % 0.53) / 0.53
                height = round(26 * math.sin(math.pi * cycle))
                squash = "squash" if cycle < 0.12 or cycle > 0.9 else ("stretch" if cycle < 0.4 else None)
                return FriendFrame(laugh=True, squash=squash, offset=(0, -height))
        if self.kind and not self.reacting:
            self.kind = ""
        if now >= self.next_blink:
            if now - self.next_blink < BLINK_SECONDS:
                return FriendFrame(blink=True)
            self.next_blink = now + self._rng.uniform(2.4, 5.0)
        return FriendFrame()

    def changed(self) -> bool:
        """True when the drawn frame differs from the last call (event-driven redraw)."""

        frame = self.frame()
        key = (frame.blink, frame.laugh, frame.squash, frame.offset)
        if key != self._last:
            self._last = key
            return True
        return False


class CastActor:
    """Momo the host: cheers and thinks through ``CastFeedback``; also points."""

    def __init__(self, character: str, art: ControlArt, clock: Callable[[], float], *, height: int) -> None:
        self.height = height
        self.feedback = CastFeedback(character, height=height, art=art, clock=clock, hold_seconds=1.6)
        self._clock = clock
        self._point = art.image(f"character.{character}", height, variant="pose_point")
        self._point_until = 0.0

    def point(self, seconds: float) -> None:
        self.feedback.reset()
        self._point_until = self._clock() + seconds

    def correct(self) -> None:
        self._point_until = 0.0
        self.feedback.correct()

    def try_again(self) -> None:
        self._point_until = 0.0
        self.feedback.try_again()

    @property
    def pointing(self) -> bool:
        return self._clock() < self._point_until

    @property
    def animating(self) -> bool:
        return self.feedback.animating or self.pointing

    def update(self) -> bool:
        changed = self.feedback.update()
        if self._point_until and self._clock() >= self._point_until:
            self._point_until = 0.0
            changed = True
        return changed

    def draw(self, target: pygame.Surface, midbottom: tuple[int, int]) -> None:
        if self.pointing and self._point is not None:
            target.blit(self._point, self._point.get_rect(midbottom=midbottom))
            return
        self.feedback.draw(target, midbottom)


class FxBurst:
    """One short shared-library FX animation (scaled once)."""

    DURATION = 0.8

    def __init__(self, image: pygame.Surface | None, center: tuple[int, int], *, clock=time.monotonic) -> None:
        self._image = image
        self._center = center
        self._clock = clock
        self._start = clock()

    @property
    def done(self) -> bool:
        return self._clock() - self._start >= self.DURATION

    def draw(self, target: pygame.Surface) -> None:
        if self._image is None or self.done:
            return
        progress = (self._clock() - self._start) / self.DURATION
        target.blit(self._image, self._image.get_rect(center=(self._center[0], self._center[1] - round(18 * progress))))


@dataclass(slots=True)
class Effects:
    bursts: list[FxBurst] = field(default_factory=list)
    halos: dict[str, float] = field(default_factory=dict)

    def prune(self, now: float) -> None:
        self.bursts = [burst for burst in self.bursts if not burst.done][-6:]
        self.halos = {key: until for key, until in self.halos.items() if until > now}

    def active(self, now: float) -> bool:
        return bool(self.bursts) or any(until > now for until in self.halos.values())


class MonsterRenderer:
    """Draw every screen from prepared surfaces."""

    def __init__(self, art: MonsterArt, painter: ControlPainter, loader: ControlArt, clock: Callable[[], float] = time.monotonic) -> None:
        self.art = art
        self.painter = painter
        self.loader = loader
        self._clock = clock
        self._screens: BoundedCache[tuple, pygame.Surface] = BoundedCache(6)
        self._misc: BoundedCache[tuple, pygame.Surface] = BoundedCache(48)

    # -- prepared backgrounds ------------------------------------------------------------

    def paper(self) -> pygame.Surface:
        cached = self._screens.get(("paper",))
        if cached is not None:
            return cached
        surface = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT))
        span = REFERENCE_HEIGHT - 1
        for row in range(REFERENCE_HEIGHT):
            pygame.draw.line(surface, mix(PAPER_TOP, PAPER_BOTTOM, row / span), (0, row), (REFERENCE_WIDTH, row))
        if pygame.display.get_surface() is not None:
            surface = surface.convert()
        self._screens[("paper",)] = surface
        return surface

    def playroom(self, size: tuple[int, int]) -> pygame.Surface:
        """The shared playroom (wall + carpet) cover-cropped to ``size``."""

        key = ("playroom", size)
        cached = self._misc.get(key)
        if cached is not None:
            return cached
        width, height = size
        scale = max(width / REFERENCE_WIDTH, height / REFERENCE_HEIGHT)
        full = (round(REFERENCE_WIDTH * scale), round(REFERENCE_HEIGHT * scale))
        scene = pygame.Surface(full)
        scene.fill((207, 234, 247))
        for layer in ("bg.indoor_room.wall_playroom", "bg.indoor_room.floor_carpet"):
            image = self.loader.image(layer, full)
            if image is not None:
                scene.blit(image, (0, 0))
        surface = pygame.Surface(size)
        # Left-anchored: keeps the wall picture and never cuts the shelf in half.
        surface.blit(scene, (0, height - full[1]))
        self._misc[key] = surface
        return surface

    def stage(self, rect: pygame.Rect) -> pygame.Surface:
        """Rounded playroom stage with the ink frame (built once per rect)."""

        key = ("stage", rect.size)
        cached = self._screens.get(key)
        if cached is not None:
            return cached
        radius = 28
        surface = pygame.Surface(rect.size, pygame.SRCALPHA)
        inner = self.playroom(rect.size)
        mask = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=radius)
        clipped = pygame.Surface(rect.size, pygame.SRCALPHA)
        clipped.blit(inner, (0, 0))
        clipped.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        surface.blit(clipped, (0, 0))
        pygame.draw.rect(surface, INK, surface.get_rect(), width=4, border_radius=radius)
        self._screens[key] = surface
        return surface

    # -- the friend -----------------------------------------------------------------------------

    def draw_friend(self, target: pygame.Surface, recipe, midbottom: tuple[int, int], height: int, frame: FriendFrame) -> None:
        if frame.squash is not None:
            image = self.art.squashed(recipe, height, laugh=frame.laugh, stretch=frame.squash == "stretch")
        else:
            image = self.art.portrait(recipe, height, blink=frame.blink, laugh=frame.laugh)
        rect = image.get_rect(midbottom=(midbottom[0] + frame.offset[0], midbottom[1] + frame.offset[1]))
        target.blit(image, rect)

    def name_plate(self, target: pygame.Surface, rect: pygame.Rect, name: str, *, empty: bool = False) -> None:
        if not name and not empty:
            return
        key = ("plate", rect.size, name)
        plate = self._misc.get(key)
        if plate is None:
            plate = pygame.Surface(rect.size, pygame.SRCALPHA)
            radius = rect.height // 2
            pygame.draw.rect(plate, (*CREAM, 255), plate.get_rect(), border_radius=radius)
            pygame.draw.rect(plate, INK, plate.get_rect(), width=3, border_radius=radius)
            if name:
                label = self.painter.label(display_text(name), round(rect.height * 0.62), COCOA, max_width=rect.width - 28)
                plate.blit(label, label.get_rect(center=(rect.width // 2, rect.height // 2 + 1)))
            else:
                for index in range(3):
                    x = rect.width // 2 + (index - 1) * 34
                    pygame.draw.line(plate, (214, 196, 170), (x - 12, rect.height - 18), (x + 12, rect.height - 18), 4)
            self._misc[key] = plate
        target.blit(plate, rect)

    def syllable_icon(self, syllable: str, index: int, size: int) -> pygame.Surface:
        key = ("syllable", syllable, index, size)
        cached = self._misc.get(key)
        if cached is not None:
            return cached
        surface = pygame.Surface((size, size), pygame.SRCALPHA)
        base = SYLLABLE_COLORS[index % len(SYLLABLE_COLORS)]
        big = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
        pygame.draw.circle(big, mix(base, (255, 255, 255), 0.18), (size, size), size - 4)
        pygame.draw.circle(big, INK, (size, size), size - 4, width=5)
        pygame.draw.ellipse(big, (255, 255, 255, 150), pygame.Rect(round(size * 0.48), round(size * 0.36), round(size * 0.36), round(size * 0.2)))
        surface.blit(pygame.transform.smoothscale(big, (size, size)), (0, 0))
        label = self.painter.label(syllable, round(size * 0.44), (255, 255, 255) if sum(base) < 560 else COCOA)
        surface.blit(label, label.get_rect(center=(size // 2, size // 2 + 2)))
        self._misc[key] = surface
        return surface

    # -- screens ----------------------------------------------------------------------------------

    def draw_studio(
        self,
        target: pygame.Surface,
        layout: StudioLayout,
        recipe,
        frame: FriendFrame,
        host: CastActor,
        effects: Effects,
        *,
        name_drawer: bool,
    ) -> None:
        target.blit(self.paper(), (0, 0))
        target.blit(self.stage(layout.stage), layout.stage.topleft)
        host.draw(target, layout.host_midbottom)
        self.draw_friend(target, recipe, layout.monster_midbottom, layout.monster_height, frame)
        self.name_plate(target, layout.name_plate, recipe.name, empty=name_drawer)
        self._tray_panel(target, layout.tray)

    def _tray_panel(self, target: pygame.Surface, rect: pygame.Rect) -> None:
        key = ("tray", rect.size)
        panel = self._screens.get(key)
        if panel is None:
            panel = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(panel, (255, 252, 244, 255), panel.get_rect(), border_radius=26)
            pygame.draw.rect(panel, (222, 206, 182), panel.get_rect(), width=3, border_radius=26)
            self._screens[key] = panel
        target.blit(panel, rect)

    def draw_halos(self, target: pygame.Surface, effects: Effects, rects: dict[str, pygame.Rect]) -> None:
        now = self._clock()
        pulse = 0.5 + 0.5 * math.sin(now * 7)
        for key, until in effects.halos.items():
            rect = rects.get(key)
            if rect is None or until <= now:
                continue
            ring = rect.inflate(14 + round(8 * pulse), 14 + round(8 * pulse))
            pygame.draw.rect(target, HALO, ring, width=6, border_radius=26)

    def draw_gallery(
        self,
        target: pygame.Surface,
        layout: GalleryLayout,
        recipes: Sequence,
        *,
        page: int,
        page_count: int,
        focus_slot: int | None,
    ) -> None:
        target.blit(self.paper(), (0, 0))
        if not recipes:
            self._empty_gallery(target, layout.empty)
        for slot, (rect, recipe) in enumerate(zip(layout.cards, recipes)):
            target.blit(self._card_back(rect.size), rect)
            portrait = self.art.portrait(recipe, round(rect.height * 1.04))
            previous = target.get_clip()
            target.set_clip(rect)
            target.blit(portrait, portrait.get_rect(midbottom=(rect.centerx, rect.bottom + round(rect.height * 0.05))))
            target.set_clip(previous)
            pygame.draw.rect(target, INK, rect, width=4, border_radius=22)
            if recipe.name:
                plate = pygame.Rect(0, 0, min(rect.width - 30, 210), 40)
                plate.center = (rect.centerx, rect.top)
                self.name_plate(target, plate, recipe.name)
        self._page_dots(target, layout.dots_centre, page, page_count)

    def _card_back(self, size: tuple[int, int]) -> pygame.Surface:
        key = ("card", size)
        cached = self._misc.get(key)
        if cached is not None:
            return cached
        surface = pygame.Surface(size, pygame.SRCALPHA)
        surface.blit(self.playroom(size), (0, 0))
        mask = pygame.Surface(size, pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=22)
        surface.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        self._misc[key] = surface
        return surface

    def _empty_gallery(self, target: pygame.Surface, rect: pygame.Rect) -> None:
        pygame.draw.rect(target, (255, 252, 244), rect, border_radius=30)
        for x in range(rect.left + 20, rect.right - 20, 28):
            pygame.draw.line(target, (206, 190, 166), (x, rect.top + 14), (x + 14, rect.top + 14), 4)
            pygame.draw.line(target, (206, 190, 166), (x, rect.bottom - 14), (x + 14, rect.bottom - 14), 4)
        frame = self.art.ui("gallery", 150)
        if frame is not None:
            target.blit(frame, frame.get_rect(center=rect.center))

    def _page_dots(self, target: pygame.Surface, centre: tuple[int, int], page: int, page_count: int) -> None:
        if page_count <= 1:
            return
        gap = 30
        left = centre[0] - (page_count - 1) * gap // 2
        for index in range(page_count):
            point = (left + index * gap, centre[1])
            if index == page:
                pygame.draw.circle(target, (244, 111, 97), point, 11)
                pygame.draw.circle(target, INK, point, 11, width=3)
            else:
                pygame.draw.circle(target, (226, 214, 196), point, 8)
                pygame.draw.circle(target, INK, point, 8, width=2)

    def draw_friend_view(self, target: pygame.Surface, layout: FriendLayout, recipe, frame: FriendFrame, host: CastActor | None) -> None:
        target.blit(self.paper(), (0, 0))
        target.blit(self.stage(layout.stage), layout.stage.topleft)
        if host is not None:
            host.draw(target, layout.host_midbottom)
        self.draw_friend(target, recipe, layout.monster_midbottom, layout.monster_height, frame)
        self.name_plate(target, layout.name_plate, recipe.name)

    def draw_effects(self, target: pygame.Surface, effects: Effects) -> None:
        for burst in effects.bursts:
            burst.draw(target)

    def burst(self, name: str, center: tuple[int, int]) -> FxBurst:
        size = FX_SIZES.get(name, 120)
        return FxBurst(self.loader.image(f"fx.{name}", size), center, clock=self._clock)

    def draw_sheet(self, target: pygame.Surface, layout: SheetLayout, preview: pygame.Surface | None) -> None:
        veil = self._misc.get(("veil",))
        if veil is None:
            veil = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.SRCALPHA)
            veil.fill((61, 44, 31, 120))
            self._misc[("veil",)] = veil
        target.blit(veil, (0, 0))
        pygame.draw.rect(target, CREAM, layout.panel, border_radius=34)
        pygame.draw.rect(target, INK, layout.panel, width=4, border_radius=34)
        if preview is not None:
            target.blit(preview, preview.get_rect(center=layout.preview.center))

    # -- the shared picture ---------------------------------------------------------------------

    def picture(self, recipe) -> pygame.Surface:
        """An 800x600 picture of the friend in the playroom (for My Creations)."""

        surface = pygame.Surface(PICTURE_SIZE)
        surface.blit(self.playroom(PICTURE_SIZE), (0, 0))
        portrait = self.art.portrait(recipe, 480)
        surface.blit(portrait, portrait.get_rect(midbottom=(PICTURE_SIZE[0] // 2, PICTURE_SIZE[1] - 18)))
        if recipe.name:
            plate = pygame.Rect(0, 0, 300, 64)
            plate.midtop = (PICTURE_SIZE[0] // 2, 22)
            self.name_plate(surface, plate, recipe.name)
        return surface

    def clear(self) -> None:
        self._screens.clear()
        self._misc.clear()


__all__ = [
    "CastActor",
    "Effects",
    "FriendFrame",
    "FriendMotion",
    "FxBurst",
    "MonsterRenderer",
    "PICTURE_SIZE",
    "body_rect",
    "monster_rect",
]
