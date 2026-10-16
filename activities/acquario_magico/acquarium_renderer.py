"""Acquario Magico — scene drawing.

:class:`AquariumRenderer` draws the tank content (scene, chest, food,
creatures, bubbles, particles, library FX, name tags and mission cues). The
shared control kit draws every control on top; the app draws Tito.

Drawing rules (Acer floor):

- the day/night scene is a pre-baked background owned by
  :class:`AquariumAssetCache`; the renderer never regenerates it
- every sprite comes pre-scaled from the bounded asset cache; ``draw_*``
  only blits (name-tag text is rendered once per species and cached)
- the dolphin's spin is a bounded ±30° wobble, the only per-frame transform
- every cached sprite is blitted through a bounded ``PreparedSurfaces``
  cache (SDL RLE copies, identical pixels): on the Acer a plain
  per-pixel-alpha blit costs ~0.22 us/px, which held the tank to 9-23 fps
"""

from __future__ import annotations

import math
import time
from typing import Any, Callable, Optional

import pygame

from greia_platform.pygame_blit import PreparedSurfaces

if __package__:
    from .acquarium_assets import AquariumAssetCache
    from .acquarium_content import NAME_TAG_SECONDS
else:
    from acquarium_assets import AquariumAssetCache
    from acquarium_content import NAME_TAG_SECONDS

# Library FX: semantic id -> frame variants, and the drawn box (logical px).
_FX_FRAMES: dict[str, tuple[str, ...]] = {
    "bubble_pop": ("default", "frame_2", "frame_3"),
    "sparkle": ("default", "frame_2"),
    "star_burst": ("default", "frame_2", "frame_3"),
    "heart_pop": ("default", "frame_2", "frame_3"),
    "splash": ("default", "frame_2", "frame_3"),
    "confetti": ("default", "frame_2", "frame_3"),
}
_FX_BOX = {"bubble_pop": 54, "sparkle": 72, "star_burst": 120, "heart_pop": 80, "splash": 90, "confetti": 170}

NameTagFactory = Callable[[str], Optional[pygame.Surface]]
HintRingFactory = Callable[[tuple[int, int]], pygame.Surface]


class AquariumRenderer:
    """Owner of the per-frame draw routines for the tank content."""

    def __init__(
        self,
        assets: AquariumAssetCache,
        name_tag: NameTagFactory | None = None,
        hint_ring: HintRingFactory | None = None,
    ) -> None:
        self._assets = assets
        self._name_tag = name_tag
        self._hint_ring = hint_ring
        self._name_tags: dict[str, Optional[pygame.Surface]] = {}
        # RLE copies of the cached sprites (bounded LRU; sources stay drawable).
        self.fast = PreparedSurfaces(max_entries=96, max_pixels=1024 * 600)

    # ------------------------------------------------------------------
    # Scene
    # ------------------------------------------------------------------

    def draw_background(self, surface: pygame.Surface, glow_mode: bool, t_now: float) -> None:
        surface.blit(self._assets.background(glow_mode), (0, 0))

    def draw_chest(self, surface: pygame.Surface, chest_rect: pygame.Rect, open_timer: float) -> None:
        name = "chest_open.png" if open_timer > 0 else "chest.png"
        chest = self._assets.scaled(name, chest_rect.width, chest_rect.height)
        if chest is None:
            pygame.draw.rect(surface, (167, 110, 52), chest_rect, border_radius=10)
            return
        lift = int(math.sin(min(1.0, (2.5 - open_timer) * 3.0) * math.pi) * 4) if open_timer > 0 else 0
        surface.blit(self.fast.for_target(chest, surface), (chest_rect.left, chest_rect.top - lift))

    # ------------------------------------------------------------------
    # Dynamic content
    # ------------------------------------------------------------------

    def draw_food(self, surface: pygame.Surface, pellets: list[dict[str, Any]]) -> None:
        for pellet in pellets:
            diameter = 12 if pellet["size"] < 6.5 else 16
            sprite = self._assets.scaled("pellet.png", diameter, diameter)
            if sprite is not None:
                sprite = self.fast.for_target(sprite, surface)
            fx, fy = int(pellet["x"]), int(pellet["y"])
            if sprite is not None:
                surface.blit(sprite, (fx - diameter // 2, fy - diameter // 2))
            else:
                pygame.draw.circle(surface, (243, 154, 56), (fx, fy), diameter // 2)

    def draw_creatures(
        self,
        surface: pygame.Surface,
        creatures: list[dict[str, Any]],
        *,
        glow_mode: bool = False,
        t_now: float = 0.0,
        hint_uid: int | None = None,
        hungry_uid: int | None = None,
    ) -> None:
        for creature in creatures:
            species = creature["spec"]
            cx = int(creature["x"])
            cy = int(creature["y"])
            box = (species.get("w", 72), species.get("h", 54))
            if glow_mode and species.get("glows"):
                pulse = 0.5 + 0.5 * math.sin(t_now * 2.2 + creature["uid"])
                radius = int(max(box) * (0.78 + 0.08 * pulse)) // 4 * 4
                glow = self.fast.for_target(self._assets.glow(radius), surface)
                surface.blit(glow, glow.get_rect(center=(cx, cy)))
            if creature["uid"] == hint_uid:
                self._draw_hint_ripple(surface, (cx, cy), box, t_now)

            variant = "default"
            if creature["puffed_t"] > 0 and species["id"] == "puffer":
                variant = "puffed"
                box = (int(box[0] * 1.4), int(box[1] * 1.4))
            elif creature["happy_t"] > 0:
                variant = "happy"
            image = self._assets.creature(species, variant, box, creature["facing"] > 0)
            if image is None:
                self._draw_creature_vector_fallback(surface, creature, cx, cy, creature["facing"] > 0)
            else:
                if creature["spin_t"] > 0:
                    # Transient per-frame transform: never cached.
                    image = pygame.transform.rotate(image, int(math.sin(creature["spin_t"] * 8.0) * 30.0))
                else:
                    image = self.fast.for_target(image, surface)
                surface.blit(image, image.get_rect(center=(cx, cy)))

            if creature["uid"] == hungry_uid:
                side = 1 if creature["facing"] > 0 else -1
                self._draw_hungry_bubble(surface, cx + side * (box[0] // 2 + 10), cy - box[1] // 2, t_now)
            if creature.get("name_t", 0.0) > 0:
                self._draw_name_tag(surface, creature, cx, cy - box[1] // 2)

    def _draw_hint_ripple(self, surface: pygame.Surface, center: tuple[int, int], box: tuple[int, int], t_now: float) -> None:
        """Pulse the kit's focus ring around the mission target ("this one!")."""

        step = (0, 8, 16, 8)[int(t_now * 5.0) % 4]
        size = (int(max(box) * 1.2) // 8 * 8 + step,) * 2
        if self._hint_ring is not None:
            ring = self.fast.for_target(self._hint_ring(size), surface)
            surface.blit(ring, ring.get_rect(center=center))
        else:
            pygame.draw.circle(surface, (255, 194, 52), center, size[0] // 2, 5)

    def _draw_hungry_bubble(self, surface: pygame.Surface, cx: int, top: int, t_now: float) -> None:
        bob = int(math.sin(t_now * 3.0) * 3)
        bubble = self._assets.bubble(48)
        center = (cx, top + bob)
        if bubble is not None:
            bubble = self.fast.for_target(bubble, surface)
            surface.blit(bubble, bubble.get_rect(center=center))
        pellet = self._assets.scaled("pellet.png", 22, 22)
        if pellet is not None:
            pellet = self.fast.for_target(pellet, surface)
            surface.blit(pellet, pellet.get_rect(center=center))

    def _draw_name_tag(self, surface: pygame.Surface, creature: dict[str, Any], cx: int, top: int) -> None:
        species_id = creature["spec"]["id"]
        if species_id not in self._name_tags:
            self._name_tags[species_id] = self._name_tag(species_id) if self._name_tag is not None else None
        tag = self._name_tags[species_id]
        if tag is None:
            return
        remaining = creature["name_t"]
        rise = int(min(1.0, (NAME_TAG_SECONDS - remaining) * 6.0) * 6)
        rect = tag.get_rect(midbottom=(cx, top - 4 - rise))
        rect.clamp_ip(surface.get_rect().inflate(-8, -8))
        surface.blit(self.fast.for_target(tag, surface), rect)

    def _draw_creature_vector_fallback(
        self,
        surface: pygame.Surface,
        creature: dict[str, Any],
        cx: int,
        cy: int,
        facing_right: bool,
    ) -> None:
        species = creature["spec"]
        base_size = species["size"]
        pygame.draw.ellipse(
            surface, species["color"], (cx - base_size, cy - base_size // 2, base_size * 2, base_size)
        )
        eye_x = cx + (base_size // 2 if facing_right else -base_size // 2)
        pygame.draw.circle(surface, (255, 255, 255), (eye_x, cy - base_size // 6), 6)
        pygame.draw.circle(surface, (52, 44, 53), (eye_x, cy - base_size // 6), 3)

    def draw_bubbles(self, surface: pygame.Surface, bubbles: list[dict[str, Any]]) -> None:
        # Up to MAX_BUBBLES share a few quantized sprites: look each RLE copy up once.
        prepared: dict[int, pygame.Surface] = {}
        for bubble in bubbles:
            diameter = int(bubble["size"] * 1.4)
            sprite = self._assets.bubble(diameter)
            bx, by = int(bubble["x"]), int(bubble["y"])
            if sprite is not None:
                fast = prepared.get(id(sprite))
                if fast is None:
                    fast = prepared[id(sprite)] = self.fast.for_target(sprite, surface)
                sprite = fast
                surface.blit(sprite, sprite.get_rect(center=(bx, by)))
            else:
                pygame.draw.circle(surface, (230, 246, 253), (bx, by), diameter // 2, 2)

    def draw_particles(self, surface: pygame.Surface, particles: list[dict[str, Any]]) -> None:
        for particle in particles:
            current_size = max(1.5, particle["size"] * max(0.0, min(1.0, particle["life"])))
            pygame.draw.circle(
                surface, particle["color"], (int(particle["x"]), int(particle["y"])), int(current_size)
            )

    def draw_effects(self, surface: pygame.Surface, effects: list[dict[str, Any]]) -> None:
        for effect in effects:
            frames = _FX_FRAMES.get(effect["kind"])
            if not frames:
                continue
            progress = effect["age"] / max(0.01, effect["life"])
            frame = frames[min(len(frames) - 1, int(progress * len(frames)))]
            size = int(_FX_BOX.get(effect["kind"], 80) * effect.get("scale", 1.0)) // 8 * 8
            image = self._assets.shared_fit(f"fx.{effect['kind']}", (max(16, size), max(16, size)), frame)
            if image is not None:
                image = self.fast.for_target(image, surface)
                surface.blit(image, image.get_rect(center=(int(effect["x"]), int(effect["y"]))))


def now_seconds() -> float:
    """Single source of monotonic seconds for animation phases.

    Centralised so any future switch to a clamped monotonic
    clock (e.g. for pause/resume) only touches this one helper.
    """

    return time.monotonic()


__all__ = ["AquariumRenderer", "now_seconds"]
