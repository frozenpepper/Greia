"""Baia delle Orche — scene drawing.

:class:`OrcaRenderer` draws the bay content: the baked fjord (day or aurora
night), the sea bells, toys, the three orcas with their moods, food, library
FX, name tags, craving bubbles, hint ripples and Tito's picture bubble for the
fact he is telling. The shared control kit draws every control on top; the app
draws Tito.

Drawing rules (Acer floor):

- the day/night scene is baked once by :class:`OrcaAssetCache`;
- every sprite comes pre-scaled (and pre-rotated, in quantized steps) from the
  bounded asset cache, so ``draw_*`` only blits;
- composed pictures (bells, bubbles, name tags, fact pictures) are built once
  per content key and kept in small fixed-size dictionaries.
"""

from __future__ import annotations

import math
import time
from typing import Optional

import pygame

from greia_platform.activity_controls import BodyShape, ControlKit
from greia_platform.localization import LocalizationError, LocalizedResources
from greia_platform.pygame_blit import PreparedSurfaces
from greia_platform.typography import GreiaTypography

try:
    from orca_assets import OrcaAssetCache
    from orca_content import (
        BELL_CENTERS,
        BELL_COLORS,
        BELL_LABELS,
        BELL_SIZE,
        HOOP_SIZE,
        NAME_TAG_SECONDS,
        ORCA_LOOKS,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        WATER_SURFACE_Y,
        ArtRef,
        Tool,
    )
    from orca_model import FoodEntity, OrcaEntity, OrcaPod, OrcaState, ToyEntity
except ImportError:
    from .orca_assets import OrcaAssetCache
    from .orca_content import (
        BELL_CENTERS,
        BELL_COLORS,
        BELL_LABELS,
        BELL_SIZE,
        HOOP_SIZE,
        NAME_TAG_SECONDS,
        ORCA_LOOKS,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        WATER_SURFACE_Y,
        ArtRef,
        Tool,
    )
    from .orca_model import FoodEntity, OrcaEntity, OrcaPod, OrcaState, ToyEntity

# Library FX: semantic id -> frame variants, and the drawn box (logical px).
_FX_FRAMES: dict[str, tuple[str, ...]] = {
    "bubble_pop": ("default", "frame_2", "frame_3"),
    "sparkle": ("default", "frame_2"),
    "star_burst": ("default", "frame_2", "frame_3"),
    "heart_pop": ("default", "frame_2", "frame_3"),
    "splash": ("default", "frame_2", "frame_3"),
    "confetti": ("default", "frame_2", "frame_3"),
    "note_burst": ("default",),
}
_FX_BOX = {
    "bubble_pop": 54,
    "sparkle": 72,
    "star_burst": 120,
    "heart_pop": 80,
    "splash": 96,
    "confetti": 190,
    "note_burst": 84,
}

_BALL = ArtRef(shared="prop.everyday.ball")
_HOOP = ArtRef(private="hoop")
_FACT_PICTURE = (150, 92)


def now_seconds() -> float:
    """Single source of monotonic seconds for animation phases."""

    return time.monotonic()


class OrcaRenderer:
    """Owner of the per-frame draw routines for the bay content."""

    def __init__(
        self,
        typography: GreiaTypography,
        resources: LocalizedResources,
        assets: OrcaAssetCache | None = None,
    ) -> None:
        self.typography = typography
        self.resources = resources
        self.assets = assets if assets is not None else OrcaAssetCache()
        self._kit: ControlKit | None = None
        self._bells: dict[tuple[int, bool], pygame.Surface] = {}
        self._cravings: dict[str, Optional[pygame.Surface]] = {}
        self._name_tags: dict[str, Optional[pygame.Surface]] = {}
        self._fact_bubbles: dict[str, Optional[pygame.Surface]] = {}
        self._glow: dict[int, pygame.Surface] = {}
        # RLE copies of every sprite blitted per frame (greia_platform.pygame_blit):
        # un-encoded per-pixel-alpha blits cost ~0.22 us/pixel on the Atom.
        self._fast = PreparedSurfaces(max_entries=96)
        # Last drawn fact bubble (tap it to hear the next fact).
        self.fact_banner_rect = pygame.Rect(0, 0, 0, 0)

    def bind_kit(self, kit: ControlKit) -> None:
        """Use the Activity's control kit for name tags, bubbles and rings."""

        self._kit = kit

    # ------------------------------------------------------------------
    # Scene
    # ------------------------------------------------------------------

    def draw_background(self, surface: pygame.Surface, night: bool) -> None:
        surface.blit(self.assets.background(night), (0, 0))

    def draw_bells(self, surface: pygame.Surface, t_now: float, rung: dict[int, float]) -> None:
        """Four floating sea bells; a rung bell dips and brightens briefly."""

        for index, (cx, cy) in enumerate(BELL_CENTERS):
            lit = rung.get(index, 0.0) > t_now
            bob = int(math.sin(t_now * 2.0 + index) * 3) + (5 if lit else 0)
            bell = self._bell(index, lit)
            surface.blit(self._fast(bell), bell.get_rect(center=(cx, cy + bob)))

    def _bell(self, index: int, lit: bool) -> pygame.Surface:
        key = (index, lit)
        cached = self._bells.get(key)
        if cached is not None:
            return cached
        color = BELL_COLORS[index]
        if lit:
            color = tuple(min(255, int(c + (255 - c) * 0.35)) for c in color)
        size = BELL_SIZE
        surface = pygame.Surface((size, size + 6), pygame.SRCALPHA)
        if self._kit is not None:
            painter = self._kit.painter
            body = painter.body(BodyShape.ROUND, (size, size + 6), color, lip=6)
            surface.blit(body, (0, 0))
            label = painter.label(BELL_LABELS[index], 20, (255, 255, 255), max_width=size - 12)
            surface.blit(label, label.get_rect(center=(size // 2, size // 2)))
            if index == len(BELL_LABELS) - 1:
                # The upper DO is marked by a small drawn tick above the name.
                tip = (size // 2, 9)
                pygame.draw.polygon(surface, (255, 255, 255), [tip, (tip[0] - 5, tip[1] + 7), (tip[0] + 5, tip[1] + 7)])
        else:
            pygame.draw.circle(surface, color, (size // 2, size // 2), size // 2)
        self._bells[key] = surface
        return surface

    def draw_toys(self, surface: pygame.Surface, toys: list[ToyEntity]) -> None:
        for toy in toys:
            if toy.kind == "ball":
                ball = self.assets.rotated(_BALL, (54, 54), int(toy.rotation))
                if ball is not None:
                    surface.blit(self._fast(ball), ball.get_rect(center=(int(toy.x), int(toy.y) - 10)))
                else:
                    pygame.draw.circle(surface, (244, 111, 97), (int(toy.x), int(toy.y)), 24)
            elif toy.kind == "ring":
                hoop = self.assets.fitted(_HOOP, HOOP_SIZE)
                if hoop is not None:
                    surface.blit(self._fast(hoop), hoop.get_rect(center=(int(toy.x), int(toy.y))))

    # ------------------------------------------------------------------
    # Orcas
    # ------------------------------------------------------------------

    def draw_orcas(
        self,
        surface: pygame.Surface,
        pod: OrcaPod,
        t_now: float,
        *,
        show_cravings: bool = False,
        hint_orca: str | None = None,
        wanted: tuple[str, str] | None = None,
    ) -> None:
        """Draw the pod back to front (small calf first, big Oskar last)."""

        ordered = sorted(pod.orcas, key=lambda o: o.scale)
        for orca in ordered:
            look = ORCA_LOOKS[orca.id]
            center = (int(orca.x), int(orca.y))
            if pod.night_mode:
                glow = self._night_glow(max(look.box) // 2 // 8 * 8 + 16)
                surface.blit(self._fast(glow), glow.get_rect(center=center))
            if orca.id == hint_orca:
                self._draw_hint_ripple(surface, center, look.box, t_now)
            variant = "default"
            if orca.is_happy:
                variant = "happy"
            elif orca.state == OrcaState.SLEEPING:
                variant = "asleep"
            angle = self._sprite_angle(orca)
            sprite = self.assets.orca(orca.id, variant, orca.facing > 0, angle)
            if sprite is not None:
                surface.blit(self._fast(sprite), sprite.get_rect(center=center))
            else:
                w, h = look.box
                pygame.draw.ellipse(surface, (44, 59, 85), (center[0] - w // 2, center[1] - h // 3, w, h * 2 // 3))
        # Bubbles and name tags go on top of every orca so none is hidden.
        for orca in ordered:
            craving = None
            if wanted is not None and wanted[0] == orca.id:
                craving = wanted[1]
            elif show_cravings and orca.state == OrcaState.SWIMMING and not pod.night_mode:
                craving = orca.craved_food.value
            if craving is not None and not orca.airborne:
                self._draw_craving(surface, orca, craving, t_now)
            if orca.name_t > 0:
                self._draw_name_tag(surface, orca)

    @staticmethod
    def _sprite_angle(orca: OrcaEntity) -> float:
        """Counter-clockwise sprite rotation from the orca's pitch."""

        if orca.state == OrcaState.CUDDLE_BELLY:
            return math.sin(orca.swim_phase * 2.0) * 6.0
        pitch = -orca.angle if orca.facing > 0 else orca.angle
        return max(-30.0, min(30.0, pitch))

    def _night_glow(self, radius: int) -> pygame.Surface:
        """Soft moonlight under each orca so the pod stays readable at night."""

        cached = self._glow.get(radius)
        if cached is not None:
            return cached
        surface = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        steps = 9
        for step in range(steps, 0, -1):
            ring = radius * step / steps
            alpha = int(46 * (1.0 - step / steps) ** 1.3) + 4
            pygame.draw.circle(surface, (176, 214, 255, alpha), (radius, radius), int(ring))
        if len(self._glow) > 6:
            self._glow.clear()
        self._glow[radius] = surface
        return surface

    def _draw_hint_ripple(self, surface: pygame.Surface, center: tuple[int, int], box: tuple[int, int], t_now: float) -> None:
        """Pulse the kit's focus ring around the invited orca ("this one!")."""

        step = (0, 8, 16, 8)[int(t_now * 5.0) % 4]
        width = int(box[0] * 0.9) // 8 * 8 + step
        height = int(box[1] * 0.9) // 8 * 8 + step
        if self._kit is not None:
            ring = self._kit.painter.focus_ring((width, height), min(width, height) // 2)
            surface.blit(self._fast(ring), ring.get_rect(center=center))
        else:
            pygame.draw.ellipse(surface, (255, 194, 52), pygame.Rect(0, 0, width, height).move(center[0] - width // 2, center[1] - height // 2), 5)

    def _draw_craving(self, surface: pygame.Surface, orca: OrcaEntity, food: str, t_now: float) -> None:
        bubble = self._craving_bubble(food)
        if bubble is None:
            return
        look = ORCA_LOOKS[orca.id]
        side = 1 if orca.facing > 0 else -1
        bob = int(math.sin(t_now * 3.0 + orca.swim_phase) * 3)
        cx = int(orca.x) + side * (look.box[0] // 3)
        bottom = int(orca.y) - look.box[1] // 2 + 6 + bob
        rect = bubble.get_rect(midbottom=(cx, bottom))
        rect.clamp_ip(pygame.Rect(0, 80, REFERENCE_WIDTH, REFERENCE_HEIGHT - 80))
        surface.blit(self._fast(bubble), rect)

    def _craving_bubble(self, food: str) -> Optional[pygame.Surface]:
        if food in self._cravings:
            return self._cravings[food]
        icon = self.assets.food(food, 34)
        bubble: Optional[pygame.Surface] = None
        if icon is not None and self._kit is not None:
            painter = self._kit.painter
            size = 52
            bubble = pygame.Surface((size + 4, size + 20), pygame.SRCALPHA)
            body = painter.body(BodyShape.ROUND, (size, size), painter.theme.surface, contour_width=2)
            bubble.blit(body, (2, 0))
            bubble.blit(icon, icon.get_rect(center=(size // 2 + 2, size // 2)))
            for radius, (x, y) in ((6, (size // 2 - 4, size + 6)), (4, (size // 2 - 10, size + 15))):
                pygame.draw.circle(bubble, painter.theme.ink, (x, y), radius)
                pygame.draw.circle(bubble, painter.theme.surface, (x, y), radius - 2)
        self._cravings[food] = bubble
        return bubble

    def _draw_name_tag(self, surface: pygame.Surface, orca: OrcaEntity) -> None:
        if orca.id not in self._name_tags:
            self._name_tags[orca.id] = self._build_name_tag(orca.name_key)
        tag = self._name_tags[orca.id]
        if tag is None:
            return
        look = ORCA_LOOKS[orca.id]
        rise = int(min(1.0, (NAME_TAG_SECONDS - orca.name_t) * 6.0) * 6)
        rect = tag.get_rect(midbottom=(int(orca.x), int(orca.y) - look.box[1] // 2 - rise))
        rect.clamp_ip(surface.get_rect().inflate(-8, -8))
        surface.blit(self._fast(tag), rect)

    def _build_name_tag(self, name_key: str) -> Optional[pygame.Surface]:
        if self._kit is None:
            return None
        try:
            text = self.resources.text(name_key).strip()
        except LocalizationError:
            return None
        if not text:
            return None
        painter = self._kit.painter
        label = painter.label(text, 22, painter.theme.text, max_width=300)
        size = (label.get_width() + 32, label.get_height() + 14)
        tag = painter.body(BodyShape.PILL, size, painter.theme.surface, contour_width=2).copy()
        tag.blit(label, label.get_rect(center=(size[0] // 2, size[1] // 2)))
        return tag

    # ------------------------------------------------------------------
    # Food and FX
    # ------------------------------------------------------------------

    def draw_foods(self, surface: pygame.Surface, foods: list[FoodEntity]) -> None:
        for food in foods:
            sprite = self.assets.food(food.kind, 42)
            if sprite is not None:
                surface.blit(self._fast(sprite), sprite.get_rect(center=(int(food.x), int(food.y))))
            else:
                pygame.draw.circle(surface, (243, 154, 56), (int(food.x), int(food.y)), 10)

    def draw_effects(self, surface: pygame.Surface, effects: list[dict], *, surface_layer: bool = False) -> None:
        """Draw library FX; water splashes belong under the orcas (``surface_layer``)."""

        for effect in effects:
            if (effect["kind"] == "splash") != surface_layer:
                continue
            frames = _FX_FRAMES.get(effect["kind"])
            if not frames:
                continue
            progress = effect["age"] / max(0.01, effect["life"])
            frame = frames[min(len(frames) - 1, int(progress * len(frames)))]
            size = int(_FX_BOX.get(effect["kind"], 80) * effect.get("scale", 1.0)) // 8 * 8
            image = self.assets.shared_fit(f"fx.{effect['kind']}", (max(16, size), max(16, size)), frame)
            if image is not None:
                surface.blit(self._fast(image), image.get_rect(center=(int(effect["x"]), int(effect["y"]))))

    # ------------------------------------------------------------------
    # Tito's fact bubble
    # ------------------------------------------------------------------

    def draw_fact_bubble(self, surface: pygame.Surface, fact_key: str | None, anchor: tuple[int, int], bottom: int) -> None:
        """Picture bubble for the fact Tito is telling (tail towards his head)."""

        if fact_key is None:
            self.fact_banner_rect = pygame.Rect(0, 0, 0, 0)
            return
        if fact_key not in self._fact_bubbles:
            if len(self._fact_bubbles) > 8:
                self._fact_bubbles.clear()
            self._fact_bubbles[fact_key] = self._build_fact_bubble(fact_key)
        bubble = self._fact_bubbles[fact_key]
        if bubble is None:
            self.fact_banner_rect = pygame.Rect(0, 0, 0, 0)
            return
        rect = bubble.get_rect(bottomleft=(anchor[0] + 18, bottom))
        rect.top = min(rect.top, anchor[1] - 40)
        surface.blit(self._fast(bubble), rect)
        if self._kit is not None:
            painter = self._kit.painter
            tail = [(rect.left + 2, rect.bottom - 46), (anchor[0] + 2, anchor[1]), (rect.left + 2, rect.bottom - 22)]
            pygame.draw.polygon(surface, painter.theme.surface, tail)
            pygame.draw.line(surface, painter.theme.ink, tail[0], tail[1], 3)
            pygame.draw.line(surface, painter.theme.ink, tail[1], tail[2], 3)
        self.fact_banner_rect = rect

    def _build_fact_bubble(self, fact_key: str) -> Optional[pygame.Surface]:
        if self._kit is None:
            return None
        painter = self._kit.painter
        picture = self._fact_picture(fact_key)
        try:
            title = self.resources.text(f"fact.{fact_key}.title").strip()
        except LocalizationError:
            title = ""
        label = painter.label(title, 20, painter.theme.text, max_width=250) if title else None
        width = max(_FACT_PICTURE[0], label.get_width() if label is not None else 0) + 36
        height = _FACT_PICTURE[1] + (label.get_height() + 6 if label is not None else 0) + 28
        bubble = painter.body(BodyShape.PANEL, (width, height), painter.theme.surface, contour_width=3).copy()
        y = 12
        bubble.blit(picture, picture.get_rect(midtop=(width // 2, y)))
        if label is not None:
            bubble.blit(label, label.get_rect(midtop=(width // 2, y + _FACT_PICTURE[1] + 4)))
        return bubble

    def _fact_picture(self, fact_key: str) -> pygame.Surface:
        """Compose the fact's picture once from library art (no text)."""

        w, h = _FACT_PICTURE
        canvas = pygame.Surface((w, h), pygame.SRCALPHA)
        assets = self.assets
        adult = ORCA_LOOKS["luna"].art
        calf = ORCA_LOOKS["kiko"].art
        elder = ORCA_LOOKS["oskar"].art

        def put(image: Optional[pygame.Surface], center: tuple[int, int]) -> None:
            if image is not None:
                canvas.blit(image, image.get_rect(center=center))

        if fact_key == "fact_breach":
            orca = assets.fitted(adult, (112, 70), "happy")
            put(assets.shared_fit("fx.splash", (64, 64)), (w // 2 + 6, h - 22))
            if orca is not None:
                put(pygame.transform.rotozoom(orca, 24, 1.0), (w // 2, h // 2 - 8))
        elif fact_key == "fact_swallow":
            put(assets.fitted(adult, (104, 66), "happy"), (w // 2 - 18, h // 2 + 6))
            put(assets.food("salmon", 40), (w - 26, h // 2 + 14))
        elif fact_key == "fact_sleep":
            put(assets.shared_fit("prop.vocab.moon", (40, 40)), (w - 24, 22))
            put(assets.fitted(adult, (112, 70), "asleep"), (w // 2 - 10, h // 2 + 12))
        elif fact_key == "fact_song":
            put(assets.fitted(adult, (104, 66), "happy"), (w // 2 - 18, h // 2 + 12))
            put(assets.shared_fit("fx.note_burst", (56, 56)), (w - 30, 28))
        elif fact_key == "fact_pod":
            put(assets.fitted(adult, (104, 66)), (w // 2 - 16, h // 2 - 4))
            put(assets.fitted(calf, (66, 42), "happy"), (w // 2 + 34, h // 2 + 24))
        else:
            put(assets.fitted(elder, (130, 84)), (w // 2, h // 2 + 4))
            put(assets.shared_fit("fx.sparkle", (38, 38)), (w // 2 - 10, 12))
        return canvas


__all__ = ["OrcaRenderer", "now_seconds"]
