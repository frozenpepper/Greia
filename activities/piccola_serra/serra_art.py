"""Prepared, bounded art for Piccola Serra.

* Package art (``assets/source/*.svg`` -> ``assets/runtime/*.png``, rendered
  1:1 for the 1024x600 reference scene): the greenhouse interior, sunbeams,
  shade cloth, terracotta pot (back/front halves), the plant-stage pictures
  ``plant_<plant>_<stage>[_droopy|_leaning]`` and the two soil overlays
  ``state_droopy`` (dry, cracked) / ``state_puddle`` (standing water), the
  watering can, the seed packet and the bean-pod harvest. These are
  Activity-private shared-library candidates (``prop.plant.*``,
  ``prop.garden.*``, ``prop.food.green_bean``).
* Shared library art by semantic id: Tito (``character.tito`` poses), the
  sun (``prop.nature.sun``), the clock (``prop.vocab.clock``), harvest food
  (``prop.food.*``), HUD glyphs (``icon.hud.*``) and FX (``fx.*``).

Both greenhouse moods (sunny with beams, shaded with the cloth down) are
composed once into opaque surfaces; plant pictures are loaded once per plant
and scaled versions live in hard-bounded caches, so drawing only blits.
Missing art degrades to simple shapes or nothing, never a crash.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

import pygame

from greia_platform.activity_controls import BodyShape, ControlArt, ControlKit
from greia_platform.ui_core import BoundedCache

if __package__:
    from .serra_content import PLANTS_BY_ID, Care, Need, Stage, SYMPTOM_STAGES, TITO
    from .serra_layout import CLOTH_POS, REFERENCE_HEIGHT, REFERENCE_WIDTH, ROLL_POS
else:
    from serra_content import PLANTS_BY_ID, Care, Need, Stage, SYMPTOM_STAGES, TITO
    from serra_layout import CLOTH_POS, REFERENCE_HEIGHT, REFERENCE_WIDTH, ROLL_POS

PACKAGE_ROOT: Final[Path] = Path(__file__).resolve().parent
RUNTIME_DIR: Final[Path] = PACKAGE_ROOT / "assets" / "runtime"
INK: Final = (75, 55, 47)
CREAM: Final = (255, 251, 235)
SKY: Final = (207, 234, 247)
SHADE_TINT: Final = (37, 59, 89, 72)   # navy, a gentle "dim" over the shaded room
HALO: Final = (255, 226, 138)
FX_VARIANTS: Final = ("default", "frame_2", "frame_3")
# Content window of the 256-unit plant-stage frame (x, y, w, h): the plant and
# its soil mound without the empty margins.
CARD_CROP: Final = (34, 6, 188, 228)
# The packet body inside the 256-unit seed-packet frame, and its picture window.
PACKET_BODY: Final = (58, 28, 140, 210)
PACKET_WINDOW: Final = (80, 70, 96, 100)
SHARED_CARE_ICONS: Final[dict[Care, str]] = {
    Care.SUN: "prop.nature.sun",
    Care.WAIT: "prop.vocab.clock",
    Care.HARVEST: "icon.hud.basket",
}


def plant_file(plant_id: str, stage: Stage, variant: str = "default") -> str:
    suffix = "" if variant == "default" else f"_{variant}"
    return f"plant_{plant_id}_{stage.value}{suffix}.png"


def variant_for(stage: Stage, need: Need | None) -> str:
    """Which picture shows a need on the plant itself (soil cues are overlays)."""

    if stage in SYMPTOM_STAGES:
        if need is Need.THIRSTY:
            return "droopy"
        if need is Need.DARK:
            return "leaning"
    return "default"


def overlay_for(need: Need | None) -> str | None:
    if need is Need.THIRSTY:
        return "state_droopy.png"
    if need is Need.SOGGY:
        return "state_puddle.png"
    return None


class SerraArt:
    """Own every prepared surface the renderer and controls blit."""

    def __init__(
        self,
        kit: ControlKit,
        *,
        art: ControlArt | None = None,
        runtime_dir: Path = RUNTIME_DIR,
    ) -> None:
        self._kit = kit
        # Content art gets its own bounded loader so it never evicts kit glyphs.
        self.art = art if art is not None else ControlArt(max_entries=48)
        self._runtime_dir = runtime_dir
        self._files: BoundedCache[str, pygame.Surface | None] = BoundedCache(24)
        self._scaled: BoundedCache[tuple, pygame.Surface | None] = BoundedCache(40)
        self._backdrops: BoundedCache[bool, pygame.Surface] = BoundedCache(2)
        self._fx: BoundedCache[tuple[str, int], tuple[pygame.Surface, ...]] = BoundedCache(12)

    # -- package files ----------------------------------------------------

    def file(self, name: str) -> pygame.Surface | None:
        if name in self._files:
            return self._files[name]
        image: pygame.Surface | None
        try:
            image = pygame.image.load(str(self._runtime_dir / name))
            if pygame.display.get_surface() is not None:
                image = image.convert_alpha()
        except (OSError, pygame.error):
            image = None
        self._files[name] = image
        return image

    def _scaled_file(self, name: str, size: tuple[int, int]) -> pygame.Surface | None:
        key = ("file", name, int(size[0]), int(size[1]))
        if key in self._scaled:
            return self._scaled[key]
        source = self.file(name)
        result = None
        if source is not None and size[0] > 0 and size[1] > 0:
            result = source if source.get_size() == size else pygame.transform.smoothscale(source, size)
        self._scaled[key] = result
        return result

    # -- the greenhouse -----------------------------------------------------

    def backdrop(self, sunny: bool) -> pygame.Surface:
        """Greenhouse composed once per mood (opaque, 1024x600).

        Sunny: beams fall on the pot and the cloth is rolled up. Shaded: no
        beams and a gentle dim (the cloth itself is drawn live so it can roll).
        """

        if sunny in self._backdrops:
            return self._backdrops[sunny]
        surface = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT))
        surface.fill(SKY)
        room = self.file("greenhouse.png")
        if room is not None:
            surface.blit(room, (0, 0))
        else:
            pygame.draw.rect(surface, (238, 221, 186), (0, 404, REFERENCE_WIDTH, 196))
            pygame.draw.rect(surface, (201, 142, 88), (86, 466, 852, 22), border_radius=8)
        if sunny:
            beams = self.file("sunbeam.png")
            if beams is not None:
                surface.blit(beams, (0, 0))
        else:
            dim = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.SRCALPHA)
            dim.fill(SHADE_TINT)
            surface.blit(dim, (0, 0))
        roll = self.file("shade_roll.png")
        if roll is not None:
            surface.blit(roll, ROLL_POS)
        if pygame.display.get_surface() is not None:
            surface = surface.convert()
        self._backdrops[sunny] = surface
        # The big room picture is only needed to compose the two moods.
        if len(self._backdrops) == 2:
            for name in ("greenhouse.png", "sunbeam.png"):
                self._files[name] = None
        return surface

    def cloth(self) -> pygame.Surface | None:
        return self.file("shade_cloth.png")

    @property
    def cloth_pos(self) -> tuple[int, int]:
        return CLOTH_POS

    def pot(self, front: bool) -> pygame.Surface | None:
        return self.file("pot_front.png" if front else "pot_back.png")

    # -- plants -------------------------------------------------------------

    def plant(self, plant_id: str, stage: Stage, variant: str = "default") -> pygame.Surface | None:
        image = self.file(plant_file(plant_id, stage, variant))
        if image is None and variant != "default":
            image = self.file(plant_file(plant_id, stage))
        return image

    def overlay(self, need: Need | None) -> pygame.Surface | None:
        name = overlay_for(need)
        return self.file(name) if name is not None else None

    def stage_card(self, plant_id: str, stage: Stage, size: int) -> pygame.Surface | None:
        """The plant picture cropped to its content window (``CARD_CROP``) and
        scaled once, so cards and slots show the plant big; every stage uses the
        same window, so the plant still visibly grows from card to card."""

        key = ("card", plant_id, stage, int(size))
        if key in self._scaled:
            return self._scaled[key]
        source = self.file(plant_file(plant_id, stage))
        result = None
        if source is not None and size > 0:
            factor = source.get_width() / 256
            crop = pygame.Rect(*(round(value * factor) for value in CARD_CROP))
            crop = crop.clip(source.get_rect())
            result = pygame.transform.smoothscale(source.subsurface(crop), (int(size), int(size * crop.height / crop.width)))
        self._scaled[key] = result
        return result

    def packet(self, plant_id: str, height: int) -> pygame.Surface:
        """Seed packet (cropped to the packet body) with the grown plant pictured in
        its window, as real seed packets show it. ``height`` is the packet height."""

        key = ("packet", plant_id, int(height))
        cached = self._scaled.get(key)
        if cached is not None:
            return cached
        factor = height / PACKET_BODY[3]
        frame = int(round(256 * factor))
        width = int(round(PACKET_BODY[2] * factor))
        surface = pygame.Surface((width, int(height)), pygame.SRCALPHA)
        paper = self._scaled_file("seed_packet.png", (frame, frame))
        if paper is not None:
            surface.blit(paper, (-round(PACKET_BODY[0] * factor), -round(PACKET_BODY[1] * factor)))
        else:
            pygame.draw.rect(surface, CREAM, surface.get_rect(), border_radius=8)
        window = pygame.Rect(
            round((PACKET_WINDOW[0] - PACKET_BODY[0]) * factor),
            round((PACKET_WINDOW[1] - PACKET_BODY[1]) * factor),
            round(PACKET_WINDOW[2] * factor),
            round(PACKET_WINDOW[3] * factor),
        )
        plant = PLANTS_BY_ID[plant_id]
        width = int((window.height - 4) * CARD_CROP[2] / CARD_CROP[3])
        picture = self.stage_card(plant_id, plant.packet_stage, width)
        if picture is not None:
            clip = surface.get_clip()
            surface.set_clip(window.inflate(-4, -4))
            surface.blit(picture, picture.get_rect(midbottom=(window.centerx, window.bottom - 1)))
            surface.set_clip(clip)
        self._scaled[key] = surface
        return surface

    def harvest(self, plant_id: str, size: int) -> pygame.Surface | None:
        plant = PLANTS_BY_ID[plant_id]
        if plant.harvest_asset is not None:
            return self.art.image(plant.harvest_asset, int(size))
        assert plant.harvest_file is not None
        return self._scaled_file(plant.harvest_file, (int(size), int(size)))

    # -- care tools -----------------------------------------------------------

    def care_icon(self, care: Care, size: int) -> pygame.Surface | None:
        if care is Care.WATER:
            return self._scaled_file("watering_can.png", (int(size), int(size)))
        return self.art.image(SHARED_CARE_ICONS[care], int(size))

    def tilted_can(self, size: int) -> pygame.Surface | None:
        """The watering can tipped to pour (rotated once per size)."""

        key = ("tilted_can", int(size))
        if key in self._scaled:
            return self._scaled[key]
        can = self._scaled_file("watering_can.png", (int(size), int(size)))
        result = None
        if can is not None:
            # Without its ground shadow (it is lifted), mirrored so the spout
            # faces the pot (the can stands to its right), smoothly tipped.
            body = can.subsurface(pygame.Rect(0, 0, can.get_width(), int(can.get_height() * 0.86)))
            result = pygame.transform.rotozoom(pygame.transform.flip(body, True, False), 30, 1.0)
        self._scaled[key] = result
        return result

    # -- cast and effects ---------------------------------------------------------

    def cast_pose(self, variant: str, height: int) -> pygame.Surface | None:
        return self.art.image(f"character.{TITO}", int(height), variant=variant)

    def fx_frames(self, name: str, size: int) -> tuple[pygame.Surface, ...]:
        key = (name, int(size))
        cached = self._fx.get(key)
        if cached is not None:
            return cached
        frames = tuple(
            image
            for variant in FX_VARIANTS
            if (image := self.art.image(f"fx.{name}", int(size), variant=variant)) is not None
        )
        self._fx[key] = frames
        return frames

    def drop(self, size: int) -> pygame.Surface | None:
        return self.art.image("prop.nature.raindrop", int(size))

    def halo(self, size: tuple[int, int]) -> pygame.Surface:
        """Warm hint glow (three flat alpha rings, no blur) for symptoms and tools."""

        width, height = int(size[0]), int(size[1])
        key = ("halo", width, height)
        cached = self._scaled.get(key)
        if cached is not None:
            return cached
        surface = pygame.Surface((width, height), pygame.SRCALPHA)
        for inset, alpha in ((0, 60), (8, 110), (16, 170)):
            rect = pygame.Rect(inset, inset, width - 2 * inset, height - 2 * inset)
            if rect.width > 4 and rect.height > 4:
                pygame.draw.ellipse(surface, (*HALO, alpha), rect, width=8)
        self._scaled[key] = surface
        return surface

    def slot(self, size: tuple[int, int], *, filled: bool) -> pygame.Surface:
        """A picture slot on the ordering board (cream card or a soft dashed place)."""

        key = ("slot", int(size[0]), int(size[1]), filled)
        cached = self._scaled.get(key)
        if cached is not None:
            return cached
        painter = self._kit.painter
        if filled:
            surface = painter.body(BodyShape.TILE, size, CREAM).copy()
        else:
            surface = pygame.Surface(size, pygame.SRCALPHA)
            rect = surface.get_rect().inflate(-6, -6)
            pygame.draw.rect(surface, (255, 251, 235, 150), rect, border_radius=22)
            # Dashed contour: short ink dashes along the rounded rect.
            step = 18
            for x in range(rect.left + 20, rect.right - 20, step):
                pygame.draw.line(surface, INK, (x, rect.top), (x + 8, rect.top), 3)
                pygame.draw.line(surface, INK, (x, rect.bottom - 1), (x + 8, rect.bottom - 1), 3)
            for y in range(rect.top + 20, rect.bottom - 20, step):
                pygame.draw.line(surface, INK, (rect.left, y), (rect.left, y + 8), 3)
                pygame.draw.line(surface, INK, (rect.right - 1, y), (rect.right - 1, y + 8), 3)
        self._scaled[key] = surface
        return surface

    def board(self, size: tuple[int, int]) -> pygame.Surface:
        key = ("board", int(size[0]), int(size[1]))
        cached = self._scaled.get(key)
        if cached is None:
            cached = self._kit.painter.body(BodyShape.PANEL, size, (247, 235, 203), contour_width=3, highlight=False)
            self._scaled[key] = cached
        return cached

    def arrow(self, size: int) -> pygame.Surface:
        """Small "then" chevron between slots (shape, not text)."""

        key = ("arrow", int(size))
        cached = self._scaled.get(key)
        if cached is None:
            cached = pygame.Surface((size, size), pygame.SRCALPHA)
            points = [(size * 0.25, size * 0.2), (size * 0.75, size * 0.5), (size * 0.25, size * 0.8)]
            pygame.draw.lines(cached, INK, False, points, max(4, size // 6))
            self._scaled[key] = cached
        return cached

    def clear(self) -> None:
        self._files.clear()
        self._scaled.clear()
        self._backdrops.clear()
        self._fx.clear()
        self.art.clear()


__all__ = [
    "RUNTIME_DIR",
    "SerraArt",
    "overlay_for",
    "plant_file",
    "variant_for",
]
