"""Prepared, bounded art for My Cute Pet.

* Rooms are shared ``bg.indoor_room`` wall + floor layers composed once per
  room into one opaque surface (a small bounded cache: a slide between two
  rooms needs two of them).
* The pet is shared ``creature.pet.<species>`` art; its need is shown by the
  library's need-state variants (``hungry``, ``dirty`` ...). The bath fades
  the ``dirty`` variant away over ``default`` through two pre-made alpha
  copies, never per frame.
* Care props are shared library props (food, sponge, ball, hearts) or this
  package's own props (``assets/source/*.svg`` -> ``assets/runtime/*.png``:
  pet bowl and pet bed in back/front layers, plaster).
* Lilli's poses and FX come from the shared library.

Every surface is scaled once per size and kept in a hard-bounded cache;
drawing only blits. Missing art degrades to simple fallbacks, never a crash.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

import pygame

from greia_platform.activity_controls import ControlArt
from greia_platform.ui_core import BoundedCache

if __package__:
    from .cucciolo_content import REFERENCE_HEIGHT, REFERENCE_WIDTH, ROOMS, SPECIES_BY_ID, Care, Room
else:
    from cucciolo_content import REFERENCE_HEIGHT, REFERENCE_WIDTH, ROOMS, SPECIES_BY_ID, Care, Room

PACKAGE_ROOT: Final[Path] = Path(__file__).resolve().parent
RUNTIME_DIR: Final[Path] = PACKAGE_ROOT / "assets" / "runtime"
HOST: Final = "lilli"
HALO: Final = (255, 226, 138)
NIGHT: Final = (37, 59, 89)  # theme ink "navy"
NIGHT_ALPHA: Final = 120
FX_SIZES: Final[dict[str, int]] = {
    "sparkle": 120,
    "star_burst": 170,
    "heart_pop": 150,
    "bubble_pop": 120,
    "dust_puff": 120,
    "confetti": 200,
}
PRIVATE_FILES: Final[tuple[str, ...]] = ("bowl_back.png", "bowl_front.png", "bed_back.png", "bed_front.png", "plaster.png")
FADE_LEVELS: Final[tuple[int, ...]] = (170, 85)
_ROOM_FALLBACK: Final[dict[Room, tuple[int, int, int]]] = {
    Room.PLAYROOM: (214, 234, 247),
    Room.KITCHEN: (248, 216, 189),
    Room.BATHROOM: (207, 237, 231),
    Room.BEDROOM: (232, 221, 247),
}


class CuccioloArt:
    """Own every prepared surface the renderer and controls blit."""

    def __init__(self, *, art: ControlArt | None = None, runtime_dir: Path = RUNTIME_DIR) -> None:
        # Content art gets its own bounded loader so it never evicts kit glyphs.
        self._art = art if art is not None else ControlArt(max_entries=72)
        self._runtime_dir = runtime_dir
        self._rooms: BoundedCache[Room, pygame.Surface] = BoundedCache(3)
        self._private: BoundedCache[str, pygame.Surface | None] = BoundedCache(len(PRIVATE_FILES))
        self._scaled: BoundedCache[tuple, pygame.Surface | None] = BoundedCache(24)
        self._fades: BoundedCache[tuple[str, int, int], pygame.Surface | None] = BoundedCache(4)
        self._misc: BoundedCache[tuple, pygame.Surface] = BoundedCache(16)
        self._fx: dict[str, tuple[pygame.Surface, ...]] = {}

    @property
    def loader(self) -> ControlArt:
        return self._art

    # -- rooms ------------------------------------------------------------------

    def room(self, room: Room) -> pygame.Surface:
        """The room's wall + floor composed once (opaque, 1024x600)."""

        cached = self._rooms.get(room)
        if cached is not None:
            return cached
        surface = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT))
        surface.fill(_ROOM_FALLBACK[room])
        loader = ControlArt(max_entries=2)
        for asset_id in ROOMS[room].layers:
            image = loader.image(asset_id, (REFERENCE_WIDTH, REFERENCE_HEIGHT))
            if image is not None:
                surface.blit(image, (0, 0))
        loader.clear()
        if pygame.display.get_surface() is not None:
            surface = surface.convert()
        self._rooms[room] = surface
        return surface

    def night(self) -> pygame.Surface:
        """Lights-off veil for bedtime (built once)."""

        key = ("night",)
        cached = self._misc.get(key)
        if cached is None:
            cached = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.SRCALPHA)
            cached.fill((*NIGHT, NIGHT_ALPHA))
            self._misc[key] = cached
        return cached

    # -- pets -------------------------------------------------------------------

    def pet(self, species: str, variant: str, size: int) -> pygame.Surface | None:
        """Library pet art (``default`` / ``happy`` / a need variant)."""

        asset = SPECIES_BY_ID[species].asset_id
        return self._art.image(asset, int(size), variant=variant)

    def pet_fading(self, species: str, variant: str, size: int, level: int) -> pygame.Surface | None:
        """``variant`` art at one of the pre-made fade levels (bath)."""

        key = (f"{species}.{variant}", int(size), int(level))
        if key in self._fades:
            return self._fades[key]
        base = self.pet(species, variant, size)
        faded: pygame.Surface | None = None
        if base is not None:
            faded = base.copy()
            faded.fill((255, 255, 255, int(level)), special_flags=pygame.BLEND_RGBA_MULT)
        self._fades[key] = faded
        return faded

    # -- props ------------------------------------------------------------------

    def shared(self, asset_id: str, size: int | tuple[int, int]) -> pygame.Surface | None:
        return self._art.image(asset_id, size)

    def private(self, name: str, size: tuple[int, int]) -> pygame.Surface | None:
        """Package-private prop scaled once to ``size``."""

        key = (name, int(size[0]), int(size[1]))
        if key in self._scaled:
            return self._scaled[key]
        source = self._private_source(name)
        image = None
        if source is not None:
            image = pygame.transform.smoothscale(source, (int(size[0]), int(size[1])))
        self._scaled[key] = image
        return image

    def food(self, species: str, size: int) -> pygame.Surface | None:
        return self.shared(SPECIES_BY_ID[species].food_asset, size)

    def care_icon(self, care: Care, species: str, size: int) -> pygame.Surface | None:
        """Picture for one tray tile (no words)."""

        if care is Care.FOOD:
            return self._bowl_icon(species, size)
        if care is Care.BATH:
            return self.shared("prop.everyday.sponge", size)
        if care is Care.BALL:
            return self.shared("prop.everyday.ball", size)
        if care is Care.PLASTER:
            return self.private("plaster.png", (size, size))
        return self._bed_icon(size)

    def _bowl_icon(self, species: str, size: int) -> pygame.Surface | None:
        key = ("bowl_icon", species, size)
        cached = self._misc.get(key)
        if cached is not None:
            return cached
        surface = pygame.Surface((size, size), pygame.SRCALPHA)
        self.draw_bowl(surface, pygame.Rect(0, 0, size, size), species, 1.0)
        self._misc[key] = surface
        return surface

    def _bed_icon(self, size: int) -> pygame.Surface | None:
        key = ("bed_icon", size)
        cached = self._misc.get(key)
        if cached is not None:
            return cached
        surface = pygame.Surface((size, size), pygame.SRCALPHA)
        width, height = size, size // 2
        top = size - height - size // 8
        for layer in ("bed_back.png", "bed_front.png"):
            image = self.private(layer, (width, height))
            if image is not None:
                surface.blit(image, (0, top))
        moon = self.shared("prop.vocab.moon", size // 2)
        if moon is not None:
            surface.blit(moon, moon.get_rect(midbottom=(size // 2, top + height // 3)))
        self._misc[key] = surface
        return surface

    def draw_bowl(self, surface: pygame.Surface, rect: pygame.Rect, species: str, amount: float) -> None:
        """Bowl back -> food (shrinking with ``amount``) -> bowl front."""

        back = self.private("bowl_back.png", rect.size)
        front = self.private("bowl_front.png", rect.size)
        if back is not None:
            surface.blit(back, rect)
        if amount > 0.05:
            # Three fixed sizes (full / two bites / one bite) are cached once.
            level = 1.0 if amount > 0.75 else (0.72 if amount > 0.4 else 0.45)
            size = max(8, int(rect.width * 0.58 * level))
            food = self.food(species, size)
            if food is not None:
                surface.blit(food, food.get_rect(midbottom=(rect.centerx, rect.top + int(rect.height * 0.66))))
        if front is not None:
            surface.blit(front, rect)

    def _private_source(self, name: str) -> pygame.Surface | None:
        if name in self._private:
            return self._private[name]
        image: pygame.Surface | None
        try:
            image = pygame.image.load(str(self._runtime_dir / name))
            if pygame.display.get_surface() is not None:
                image = image.convert_alpha()
        except (OSError, pygame.error):
            image = None
        self._private[name] = image
        return image

    # -- cast / FX / glow -------------------------------------------------------

    def cast_pose(self, variant: str, height: int) -> pygame.Surface | None:
        return self._art.image(f"character.{HOST}", height, variant=variant)

    def fx_frames(self, name: str) -> tuple[pygame.Surface, ...]:
        cached = self._fx.get(name)
        if cached is not None:
            return cached
        size = FX_SIZES.get(name, 120)
        frames = []
        for variant in ("default", "frame_2", "frame_3"):
            image = self._art.image(f"fx.{name}", size, variant=variant)
            if image is not None:
                frames.append(image)
        self._fx[name] = tuple(frames)
        return self._fx[name]

    def glow(self, size: tuple[int, int]) -> pygame.Surface:
        """Warm hint ring drawn behind a tile or around the pet."""

        key = ("glow", int(size[0]), int(size[1]))
        cached = self._misc.get(key)
        if cached is None:
            width, height = int(size[0]), int(size[1])
            cached = pygame.Surface((width, height), pygame.SRCALPHA)
            for inset, alpha in ((0, 70), (7, 120), (14, 190)):
                rect = pygame.Rect(inset, inset, width - 2 * inset, height - 2 * inset)
                if rect.width > 0 and rect.height > 0:
                    pygame.draw.rect(cached, (*HALO, alpha), rect, width=7, border_radius=max(8, min(rect.size) // 4))
            self._misc[key] = cached
        return cached

    def clear(self) -> None:
        self._rooms.clear()
        self._private.clear()
        self._scaled.clear()
        self._fades.clear()
        self._misc.clear()
        self._fx.clear()


__all__ = ["CuccioloArt", "FADE_LEVELS", "HOST", "PRIVATE_FILES"]
