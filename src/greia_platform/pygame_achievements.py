from __future__ import annotations

import hashlib
import io
import math
from dataclasses import dataclass
from typing import Any, Protocol

import pygame

from .achievements import AchievementEntry
from .ui_core import BoundedCache


class AchievementIconProvider(Protocol):
    def __call__(self, icon_id: str, size: int, pygame_module: Any) -> Any: ...


class AchievementFrameProvider(Protocol):
    """Return the pre-rendered award frame for ``family`` near ``size`` px.

    ``family`` is ``bronze``/``silver``/``gold``/``special``. The provider
    returns a square catalogue rendition (``ui.award.<family>``; the
    ``locked`` variants carry the grey silhouette and padlock) at one of its
    native sizes, or ``None`` when shared art is unavailable. It must not
    rasterize SVG; the renderer scales the returned surface once into its own
    bounded cache.
    """

    def __call__(
        self, family: str, locked: bool, size: int, pygame_module: Any
    ) -> Any | None: ...


# Centre emblem slot of each award master, in 256-unit master coordinates:
# (centre x, centre y, cream slot radius). Must match the SVG masters under
# assets/source/achievements/ (tests/test_pygame_achievements.py pins it).
AWARD_SLOTS: dict[str, tuple[float, float, float]] = {
    "bronze": (128.0, 100.0, 56.0),
    "silver": (128.0, 100.0, 56.0),
    "gold": (128.0, 98.0, 42.0),
    "special": (128.0, 100.0, 47.0),
}
AWARD_MASTER_SIZE = 256.0
MIN_BADGE_SIZE = 32
MAX_BADGE_SIZE = 220


def award_family(tier: str, *, secret: bool) -> str:
    """Return the award frame family for a tier (secret uses the rosette)."""

    if secret or tier == "special":
        return "special"
    return tier if tier in AWARD_SLOTS else "bronze"


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

    Bronze is a round copper medal, silver a scalloped medal with longer
    ribbons, gold a cup trophy and special/secret a purple rosette over a star
    burst. When a ``frame_provider`` is injected the frame is the reviewed
    shared rendition (``ui.award.<family>``, flat SVG masters rendered at build
    time); otherwise — or when that art fails to load — the original
    procedural geometry remains a complete fail-soft fallback. When platform
    policy admits an optional Activity-owned PNG emblem, that emblem becomes
    the centre artwork; otherwise the platform semantic icon is used. Locked
    badges show the grey tier silhouette with a padlock and never reveal
    Activity art.

    Alpha is intentionally confined to the badge-sized surface. Activity emblem
    files are bounded/fingerprinted during policy loading. The renderer verifies
    those exact bytes on first use, decodes one shared source surface per emblem,
    and prepares bounded final award surfaces from it. Repeated draws are cache
    hits; content fingerprints invalidate stale art. No runtime SVG rasterization
    or fullscreen translucent surface is introduced on the low-resource floor.
    """

    def __init__(
        self,
        icon_provider: AchievementIconProvider,
        *,
        max_entries: int = 64,
        style: AchievementBadgeStyle = AchievementBadgeStyle(),
        frame_provider: AchievementFrameProvider | None = None,
    ) -> None:
        self._icon_provider = icon_provider
        self._frame_provider = frame_provider
        self._cache: BoundedCache[tuple[object, ...], Any] = BoundedCache(max_entries)
        self._emblem_sources: BoundedCache[tuple[str, str], Any] = BoundedCache(
            max(4, min(24, max_entries))
        )
        self._style = style

    def clear(self) -> None:
        self._cache.clear()
        self._emblem_sources.clear()

    def __len__(self) -> int:
        return len(self._cache)

    @property
    def max_entries(self) -> int:
        return self._cache.max_entries

    def render(
        self,
        entry: AchievementEntry,
        size: int,
        pygame_module: Any = pygame,
    ) -> Any:
        size = max(MIN_BADGE_SIZE, min(MAX_BADGE_SIZE, int(size)))
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
        if self._compose_rendition(surface, entry, size, pygame_module):
            self._cache[key] = surface
            return surface
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

    def _compose_rendition(
        self, surface: Any, entry: AchievementEntry, size: int, pygame_module: Any
    ) -> bool:
        """Blit the shared award frame and centre artwork; False = fall back."""

        if self._frame_provider is None:
            return False
        definition = entry.definition
        family = award_family(definition.tier, secret=definition.secret)
        try:
            frame = self._frame_provider(
                family, not entry.unlocked, size, pygame_module
            )
            if frame is None:
                return False
            if frame.get_size() != (size, size):
                frame = pygame_module.transform.smoothscale(frame, (size, size))
            surface.blit(frame, (0, 0))
        except Exception:
            # Shared art is decorative: a missing/corrupt rendition must
            # never hide the award. The procedural frame takes over.
            surface.fill((0, 0, 0, 0))
            return False
        if entry.unlocked:
            cx, cy, radius = AWARD_SLOTS[family]
            scale = size / AWARD_MASTER_SIZE
            # A square emblem tile with rounded corners fits the round cream
            # slot at ~1.5x its radius; core icons are transparent anyway.
            icon_size = max(12, int(radius * 1.5 * scale))
            self._draw_semantic_icon(
                surface,
                entry,
                (int(round(cx * scale)), int(round(cy * scale))),
                icon_size,
                pygame_module,
            )
        return True

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
                loaded = self._load_activity_emblem(emblem, pygame_module)
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

    def _load_activity_emblem(self, emblem: Any, pygame_module: Any) -> Any:
        source_key = (str(emblem.asset_path), emblem.content_digest)
        cached = self._emblem_sources.get(source_key)
        if cached is not None:
            return cached

        # Read no more than the exact number of bytes admitted by policy. This
        # keeps the runtime bounded and detects an in-place package mutation
        # between policy loading and first presentation.
        with emblem.asset_path.open("rb") as handle:
            data = handle.read(emblem.byte_size + 1)
        if len(data) != emblem.byte_size:
            raise ValueError("Activity achievement emblem changed after policy admission")
        if emblem.content_digest:
            digest = hashlib.sha256(data).hexdigest()
            if digest != emblem.content_digest:
                raise ValueError("Activity achievement emblem fingerprint changed")

        loaded = pygame_module.image.load(
            io.BytesIO(data),
            emblem.asset_path.name,
        )
        self._emblem_sources[source_key] = loaded
        return loaded

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
    "AWARD_SLOTS",
    "AchievementBadgeStyle",
    "AchievementFrameProvider",
    "award_family",
    "AchievementIconProvider",
    "PygameAchievementBadgeRenderer",
]
