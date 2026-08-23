from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Protocol

import pygame

from .achievements import AchievementEntry
from .ui_core import BoundedCache


class AchievementIconProvider(Protocol):
    def __call__(self, icon_id: str, size: int, pygame_module: Any) -> Any: ...


@dataclass(frozen=True, slots=True)
class AchievementBadgeStyle:
    """Greia award materials for small cached achievement artwork."""

    bronze: tuple[int, int, int] = (202, 123, 62)
    bronze_light: tuple[int, int, int] = (244, 177, 102)
    silver: tuple[int, int, int] = (174, 188, 207)
    silver_light: tuple[int, int, int] = (238, 244, 252)
    gold: tuple[int, int, int] = (238, 177, 18)
    gold_light: tuple[int, int, int] = (255, 224, 88)
    special: tuple[int, int, int] = (123, 84, 218)
    special_blue: tuple[int, int, int] = (58, 139, 239)
    ribbon_blue: tuple[int, int, int] = (53, 132, 229)
    ribbon_light: tuple[int, int, int] = (100, 190, 255)
    locked: tuple[int, int, int] = (145, 157, 176)
    locked_light: tuple[int, int, int] = (205, 214, 226)
    inner: tuple[int, int, int] = (255, 251, 240)
    outline: tuple[int, int, int] = (100, 68, 38)
    shadow: tuple[int, int, int, int] = (30, 41, 59, 72)

    def tier_color(self, tier: str, *, unlocked: bool) -> tuple[int, int, int]:
        if not unlocked:
            return self.locked
        return {
            "bronze": self.bronze,
            "silver": self.silver,
            "gold": self.gold,
            "special": self.special,
        }.get(tier, self.bronze)

    def tier_highlight(self, tier: str, *, unlocked: bool) -> tuple[int, int, int]:
        if not unlocked:
            return self.locked_light
        return {
            "bronze": self.bronze_light,
            "silver": self.silver_light,
            "gold": self.gold_light,
            "special": self.special_blue,
        }.get(tier, self.bronze_light)


class PygameAchievementBadgeRenderer:
    """Render distinctive, tiny cached Greia award artwork.

    Bronze/silver milestones use a medal-and-ribbon silhouette, ordinary gold
    milestones use a trophy cup, and special/secret achievements use a richer
    rosette/constellation treatment. When platform policy admits an optional
    Activity-owned PNG emblem, that emblem becomes the centre artwork; otherwise
    the platform semantic icon remains the fallback.

    Alpha is intentionally confined to the badge-sized surface. Activity emblem
    files are bounded during policy loading and decoded only while preparing a
    new cached badge surface. Repeated draws are cache hits; content fingerprints
    invalidate the cache when an Activity updates art in place. No runtime SVG
    rasterization or fullscreen translucent surface is introduced on the
    low-resource hardware floor.
    """

    def __init__(
        self,
        icon_provider: AchievementIconProvider,
        *,
        max_entries: int = 64,
        style: AchievementBadgeStyle = AchievementBadgeStyle(),
    ) -> None:
        self._icon_provider = icon_provider
        self._cache: BoundedCache[tuple[object, ...], Any] = BoundedCache(max_entries)
        self._style = style

    def clear(self) -> None:
        self._cache.clear()

    def render(
        self,
        entry: AchievementEntry,
        size: int,
        pygame_module: Any = pygame,
    ) -> Any:
        size = max(48, min(220, int(size)))
        definition = entry.definition
        activity_emblem = definition.activity_emblem
        key = (
            definition.achievement_id,
            definition.tier,
            definition.icon_id,
            None
            if activity_emblem is None
            else (
                str(activity_emblem.asset_path),
                activity_emblem.content_digest,
            ),
            definition.secret,
            entry.unlocked,
            size,
        )
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        surface = pygame_module.Surface((size, size), pygame_module.SRCALPHA)
        if not entry.unlocked:
            self._draw_medal(surface, entry, size, pygame_module, locked=True)
        elif definition.secret or definition.tier == "special":
            self._draw_special(surface, entry, size, pygame_module)
        elif definition.tier == "gold":
            self._draw_trophy(surface, entry, size, pygame_module)
        else:
            self._draw_medal(surface, entry, size, pygame_module, locked=False)

        self._cache[key] = surface
        return surface

    def _draw_medal(
        self,
        surface: Any,
        entry: AchievementEntry,
        size: int,
        pygame_module: Any,
        *,
        locked: bool,
    ) -> None:
        definition = entry.definition
        tier = self._style.tier_color(definition.tier, unlocked=not locked)
        highlight = self._style.tier_highlight(definition.tier, unlocked=not locked)
        cx = size // 2
        cy = int(size * 0.40)
        radius = int(size * 0.29)

        ribbon_top = cy + int(radius * 0.60)
        ribbon_bottom = min(size - 3, int(size * 0.94))
        half_gap = max(2, size // 36)
        tail_w = max(12, int(size * 0.20))
        for direction in (-1, 1):
            inner_x = cx + direction * half_gap
            outer_x = cx + direction * (half_gap + tail_w)
            tip_inner = cx + direction * int(tail_w * 0.46)
            tip_outer = cx + direction * int(tail_w * 1.10)
            points = (
                (inner_x, ribbon_top),
                (outer_x, ribbon_top + size // 40),
                (tip_outer, ribbon_bottom),
                (cx + direction * int(tail_w * 0.58), ribbon_bottom - size // 16),
                (tip_inner, ribbon_bottom),
            )
            pygame_module.draw.polygon(
                surface,
                self._style.ribbon_blue if not locked else tier,
                points,
            )
            stripe = (
                (cx + direction * int(tail_w * 0.30), ribbon_top + size // 20),
                (cx + direction * int(tail_w * 0.55), ribbon_top + size // 18),
                (cx + direction * int(tail_w * 0.72), ribbon_bottom - size // 12),
                (cx + direction * int(tail_w * 0.50), ribbon_bottom - size // 10),
            )
            pygame_module.draw.polygon(
                surface,
                highlight if locked else self._style.ribbon_light,
                stripe,
            )

        shadow_rect = pygame_module.Rect(0, 0, radius * 2 + 10, radius * 2 + 10)
        shadow_rect.center = (cx + max(2, size // 34), cy + max(3, size // 27))
        pygame_module.draw.ellipse(surface, self._style.shadow, shadow_rect)

        scallop_radius = radius + max(5, size // 22)
        for index in range(12):
            angle = index * math.tau / 12.0
            px = cx + int(math.cos(angle) * scallop_radius * 0.83)
            py = cy + int(math.sin(angle) * scallop_radius * 0.83)
            pygame_module.draw.circle(surface, tier, (px, py), max(5, size // 15))
        pygame_module.draw.circle(surface, tier, (cx, cy), scallop_radius)
        pygame_module.draw.circle(
            surface,
            highlight,
            (cx, cy),
            radius + max(1, size // 70),
        )
        pygame_module.draw.circle(surface, self._style.inner, (cx, cy), int(radius * 0.82))
        pygame_module.draw.circle(
            surface,
            tier,
            (cx, cy),
            int(radius * 0.82),
            width=max(2, size // 34),
        )

        pygame_module.draw.arc(
            surface,
            highlight,
            pygame_module.Rect(
                cx - radius,
                cy - radius,
                radius * 2,
                radius * 2,
            ),
            math.pi * 0.80,
            math.pi * 1.35,
            width=max(2, size // 42),
        )

        if locked:
            self._draw_lock(surface, (cx, cy), radius, tier, size, pygame_module)
        else:
            self._draw_semantic_icon(
                surface,
                entry,
                (cx, cy),
                int(radius * 1.16),
                pygame_module,
            )

    def _draw_trophy(
        self,
        surface: Any,
        entry: AchievementEntry,
        size: int,
        pygame_module: Any,
    ) -> None:
        gold = self._style.gold
        light = self._style.gold_light
        cx = size // 2
        top = int(size * 0.16)
        cup_w = int(size * 0.56)
        cup_h = int(size * 0.43)
        left = cx - cup_w // 2
        right = cx + cup_w // 2
        bottom = top + cup_h

        shadow = pygame_module.Rect(left + size // 35, top + size // 30, cup_w, cup_h)
        pygame_module.draw.ellipse(surface, self._style.shadow, shadow)

        handle_r = max(8, int(size * 0.16))
        handle_width = max(4, size // 22)
        pygame_module.draw.arc(
            surface,
            gold,
            pygame_module.Rect(
                left - handle_r,
                top + size // 18,
                handle_r * 2,
                handle_r * 2,
            ),
            math.pi * 0.42,
            math.pi * 1.58,
            width=handle_width,
        )
        pygame_module.draw.arc(
            surface,
            gold,
            pygame_module.Rect(
                right - handle_r,
                top + size // 18,
                handle_r * 2,
                handle_r * 2,
            ),
            -math.pi * 0.58,
            math.pi * 0.58,
            width=handle_width,
        )

        cup = (
            (left, top),
            (right, top),
            (right - int(cup_w * 0.12), bottom - int(cup_h * 0.18)),
            (cx + int(cup_w * 0.15), bottom),
            (cx - int(cup_w * 0.15), bottom),
            (left + int(cup_w * 0.12), bottom - int(cup_h * 0.18)),
        )
        pygame_module.draw.polygon(surface, gold, cup)
        pygame_module.draw.line(
            surface,
            light,
            (left + size // 24, top + size // 35),
            (right - size // 24, top + size // 35),
            width=max(3, size // 28),
        )
        pygame_module.draw.arc(
            surface,
            light,
            pygame_module.Rect(
                left + size // 20,
                top + size // 18,
                cup_w // 3,
                cup_h // 2,
            ),
            math.pi * 0.55,
            math.pi * 1.15,
            width=max(2, size // 34),
        )

        stem_top = bottom - size // 50
        stem_bottom = int(size * 0.77)
        pygame_module.draw.polygon(
            surface,
            gold,
            (
                (cx - size // 16, stem_top),
                (cx + size // 16, stem_top),
                (cx + size // 12, stem_bottom),
                (cx - size // 12, stem_bottom),
            ),
        )
        base = pygame_module.Rect(0, 0, int(size * 0.46), max(9, int(size * 0.11)))
        base.center = (cx, int(size * 0.84))
        pygame_module.draw.ellipse(surface, gold, base)
        inner_base = base.inflate(-max(4, size // 20), -max(3, size // 35))
        pygame_module.draw.ellipse(surface, light, inner_base)

        self._draw_semantic_icon(
            surface,
            entry,
            (cx, top + int(cup_h * 0.48)),
            max(22, int(size * 0.26)),
            pygame_module,
        )

    def _draw_special(
        self,
        surface: Any,
        entry: AchievementEntry,
        size: int,
        pygame_module: Any,
    ) -> None:
        cx = cy = size // 2
        outer = int(size * 0.37)
        petal_radius = max(7, int(size * 0.10))
        petal_distance = int(size * 0.31)
        colors = (self._style.special_blue, self._style.special, self._style.gold)

        for index in range(12):
            angle = index * math.tau / 12.0
            point = (
                cx + int(math.cos(angle) * petal_distance),
                cy + int(math.sin(angle) * petal_distance),
            )
            pygame_module.draw.circle(
                surface,
                colors[index % len(colors)],
                point,
                petal_radius,
            )

        pygame_module.draw.circle(surface, self._style.gold, (cx, cy), outer)
        pygame_module.draw.circle(
            surface,
            self._style.special_blue,
            (cx, cy),
            int(outer * 0.84),
        )
        pygame_module.draw.circle(
            surface,
            self._style.inner,
            (cx, cy),
            int(outer * 0.66),
        )
        pygame_module.draw.circle(
            surface,
            self._style.gold_light,
            (cx, cy),
            int(outer * 0.66),
            width=max(2, size // 32),
        )

        if entry.definition.secret:
            orbit = int(size * 0.43)
            for index in range(5):
                angle = index * math.tau / 5.0 - math.pi / 2.0
                px = cx + int(math.cos(angle) * orbit)
                py = cy + int(math.sin(angle) * orbit)
                pygame_module.draw.circle(
                    surface,
                    self._style.gold_light,
                    (px, py),
                    max(2, size // 38),
                )

        self._draw_semantic_icon(
            surface,
            entry,
            (cx, cy),
            max(24, int(size * 0.34)),
            pygame_module,
        )

    def _draw_semantic_icon(
        self,
        surface: Any,
        entry: AchievementEntry,
        center: tuple[int, int],
        icon_size: int,
        pygame_module: Any,
    ) -> None:
        emblem = entry.definition.activity_emblem
        if emblem is not None:
            try:
                loaded = pygame_module.image.load(str(emblem.asset_path))
                icon = pygame_module.transform.smoothscale(
                    loaded,
                    (icon_size, icon_size),
                )
                surface.blit(icon, icon.get_rect(center=center))
                return
            except Exception:
                # Decorative Activity art is fail-soft. The platform-owned icon
                # remains a complete semantic fallback and badge authority is
                # unaffected by presentation failures.
                pass

        try:
            icon = self._icon_provider(
                entry.definition.icon_id,
                icon_size,
                pygame_module,
            )
        except Exception:
            icon = self._icon_provider("yellow_star", icon_size, pygame_module)
        surface.blit(icon, icon.get_rect(center=center))

    @staticmethod
    def _draw_lock(
        surface: Any,
        center: tuple[int, int],
        radius: int,
        color: tuple[int, int, int],
        size: int,
        pygame_module: Any,
    ) -> None:
        lock_w = max(18, int(radius * 0.76))
        lock_h = max(17, int(radius * 0.64))
        body = pygame_module.Rect(0, 0, lock_w, lock_h)
        body.center = (center[0], center[1] + lock_h // 5)
        pygame_module.draw.rect(
            surface,
            color,
            body,
            border_radius=max(4, lock_w // 6),
        )
        arc = pygame_module.Rect(
            0,
            0,
            int(lock_w * 0.74),
            int(lock_h * 1.08),
        )
        arc.center = (center[0], body.top)
        pygame_module.draw.arc(
            surface,
            color,
            arc,
            0.0,
            math.pi,
            width=max(3, size // 30),
        )


__all__ = [
    "AchievementBadgeStyle",
    "AchievementIconProvider",
    "PygameAchievementBadgeRenderer",
]
