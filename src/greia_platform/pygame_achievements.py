from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import pygame

from .achievements import AchievementEntry
from .ui_core import BoundedCache


class AchievementIconProvider(Protocol):
    def __call__(self, icon_id: str, size: int, pygame_module: Any) -> Any: ...


@dataclass(frozen=True, slots=True)
class AchievementBadgeStyle:
    bronze: tuple[int, int, int] = (202, 138, 74)
    silver: tuple[int, int, int] = (166, 179, 194)
    gold: tuple[int, int, int] = (234, 179, 8)
    special: tuple[int, int, int] = (168, 85, 247)
    locked: tuple[int, int, int] = (148, 163, 184)
    inner: tuple[int, int, int] = (255, 252, 245)
    shadow: tuple[int, int, int, int] = (30, 41, 59, 70)

    def tier_color(self, tier: str, *, unlocked: bool) -> tuple[int, int, int]:
        if not unlocked:
            return self.locked
        return {
            "bronze": self.bronze,
            "silver": self.silver,
            "gold": self.gold,
            "special": self.special,
        }.get(tier, self.bronze)


class PygameAchievementBadgeRenderer:
    """Render small cached badge medallions for Shell/library presentation.

    Alpha is intentionally confined to the badge-sized surface. The renderer
    never creates a full-screen overlay, and repeated renders of the same badge
    state/size are bounded cache hits.
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
        key = (
            definition.achievement_id,
            definition.tier,
            definition.icon_id,
            entry.unlocked,
            size,
        )
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        surface = pygame_module.Surface((size, size), pygame_module.SRCALPHA)
        center = (size // 2, size // 2 - max(1, size // 30))
        radius = int(size * 0.36)
        shadow_rect = pygame_module.Rect(0, 0, radius * 2 + 8, radius * 2 + 8)
        shadow_rect.center = (center[0] + max(2, size // 30), center[1] + max(3, size // 24))
        pygame_module.draw.ellipse(surface, self._style.shadow, shadow_rect)

        tier = self._style.tier_color(definition.tier, unlocked=entry.unlocked)
        pygame_module.draw.circle(surface, tier, center, radius + max(5, size // 22))
        pygame_module.draw.circle(surface, self._style.inner, center, radius)
        pygame_module.draw.circle(
            surface,
            tier,
            center,
            radius,
            width=max(3, size // 30),
        )

        if entry.unlocked:
            icon_size = max(24, int(radius * 1.12))
            try:
                icon = self._icon_provider(definition.icon_id, icon_size, pygame_module)
            except Exception:
                icon = self._icon_provider("yellow_star", icon_size, pygame_module)
            surface.blit(icon, icon.get_rect(center=center))
        else:
            # Locked badges use geometry rather than text/font work so the cache
            # is renderer-independent and cheap on the low-resource floor.
            lock_w = max(18, int(radius * 0.72))
            lock_h = max(17, int(radius * 0.62))
            body = pygame_module.Rect(0, 0, lock_w, lock_h)
            body.center = (center[0], center[1] + lock_h // 5)
            pygame_module.draw.rect(surface, tier, body, border_radius=max(4, lock_w // 6))
            arc = pygame_module.Rect(0, 0, int(lock_w * 0.72), int(lock_h * 1.05))
            arc.center = (center[0], body.top)
            pygame_module.draw.arc(
                surface,
                tier,
                arc,
                0.0,
                3.14159,
                width=max(3, size // 30),
            )

        ribbon_y = center[1] + radius + max(1, size // 60)
        ribbon_w = int(size * 0.38)
        ribbon_h = max(11, int(size * 0.12))
        points = (
            (center[0] - ribbon_w // 2, ribbon_y),
            (center[0] + ribbon_w // 2, ribbon_y),
            (center[0] + ribbon_w // 3, ribbon_y + ribbon_h),
            (center[0], ribbon_y + ribbon_h // 2),
            (center[0] - ribbon_w // 3, ribbon_y + ribbon_h),
        )
        pygame_module.draw.polygon(surface, tier, points)

        self._cache[key] = surface
        return surface


__all__ = [
    "AchievementBadgeStyle",
    "AchievementIconProvider",
    "PygameAchievementBadgeRenderer",
]
