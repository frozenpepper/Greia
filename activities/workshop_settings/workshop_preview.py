"""Live miniature of the child's Greia Home.

The preview redraws the real Collection Home composition at a small size:
the room colour behind the storybook meadow (or the chosen picture), the six
hue-coded Collection portals with their captions (letters at the chosen
size), the profile badge with the chosen avatar, the achievement star box in
the sparkle colour, and the child's cast friend greeting from the meadow.

The static part is composed once per look and size into a bounded cache; per
frame only the friend (``CastFeedback`` hop/sway offsets) and a short sparkle
burst are blitted on top. Geometry comes from ``workshop_content`` (measured
from the Shell's 1024x600 Home layout).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path
import time

import pygame

from greia_platform.activity_controls import ControlKit, mix
from greia_platform.activity_feedback import CastFeedback
from greia_platform.typography import FontRole
from greia_platform.ui_core import BoundedCache
from greia_platform.ui_preferences import InterfaceSize

if not __package__:
    __package__ = "activities.workshop_settings"  # type: ignore[assignment]

try:
    from .workshop_art import MyGreiaArt, caption_pill, rounded
    from .workshop_content import (
        AVATAR_CAST_CHARACTER,
        CAPTION_INK,
        DEFAULT_GREETER,
        HOME_BADGE,
        HOME_FOCUSED_PORTAL,
        HOME_GREETER,
        HOME_LABEL_FONT_PX,
        HOME_LABEL_SLOTS,
        HOME_PORTALS,
        HOME_STAR,
        MAX_PREVIEW_CACHE,
        PORTAL_ICON_FRACTION,
        PORTAL_WINDOW_CENTER,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        SPARKLE_SECONDS,
    )
    from .workshop_model import ChoiceKind, Look
    from .workshop_services import MyGreiaChoices
except ImportError:
    from workshop_art import MyGreiaArt, caption_pill, rounded  # type: ignore[no-redef]
    from workshop_content import (  # type: ignore[no-redef]
        AVATAR_CAST_CHARACTER,
        CAPTION_INK,
        DEFAULT_GREETER,
        HOME_BADGE,
        HOME_FOCUSED_PORTAL,
        HOME_GREETER,
        HOME_LABEL_FONT_PX,
        HOME_LABEL_SLOTS,
        HOME_PORTALS,
        HOME_STAR,
        MAX_PREVIEW_CACHE,
        PORTAL_ICON_FRACTION,
        PORTAL_WINDOW_CENTER,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        SPARKLE_SECONDS,
    )
    from workshop_model import ChoiceKind, Look  # type: ignore[no-redef]
    from workshop_services import MyGreiaChoices  # type: ignore[no-redef]

# Where a change shows on Home (reference coordinates), for the sparkle burst.
_ANCHORS: dict[ChoiceKind, tuple[tuple[int, int], ...]] = {
    ChoiceKind.AVATAR: ((56, 52), (190, 420)),
    ChoiceKind.BACKGROUND: ((150, 150), (880, 210)),
    ChoiceKind.ACCENT: ((972, 48),),
    ChoiceKind.WALLPAPER: ((140, 200), (900, 300), (512, 560)),
    ChoiceKind.SIZE: ((304, 269), (720, 500)),
}


def greeter_for(avatar_id: str) -> str:
    """The canonical cast friend that greets a profile with ``avatar_id``."""

    return AVATAR_CAST_CHARACTER.get(avatar_id, DEFAULT_GREETER)


class HomePreview:
    """Compose and animate the miniature Home for the current look."""

    def __init__(
        self,
        kit: ControlKit,
        art: MyGreiaArt,
        typography,
        labels: Mapping[str, str],
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._kit = kit
        self._art = art
        self._typography = typography
        self._labels = dict(labels)
        self._clock = clock
        self._static: BoundedCache[tuple, pygame.Surface] = BoundedCache(MAX_PREVIEW_CACHE)
        self._friends: BoundedCache[tuple[str, int], CastFeedback] = BoundedCache(6)
        self._sparkles: list[tuple[tuple[int, int], float]] = []
        self.size: tuple[int, int] = (1, 1)
        self.build_count = 0
        self._character = DEFAULT_GREETER

    # -- geometry -----------------------------------------------------------------

    def resize(self, size: tuple[int, int]) -> None:
        size = (max(16, int(size[0])), max(16, int(size[1])))
        if size != self.size:
            self.size = size
            self._static.clear()
            self._friends.clear()

    @property
    def scale(self) -> float:
        return self.size[0] / REFERENCE_WIDTH

    def _rect(self, box: tuple[int, int, int, int]) -> pygame.Rect:
        s = self.scale
        sy = self.size[1] / REFERENCE_HEIGHT
        x, y, w, h = box
        return pygame.Rect(round(x * s), round(y * sy), max(1, round(w * s)), max(1, round(h * sy)))

    def _point(self, point: tuple[int, int]) -> tuple[int, int]:
        return (round(point[0] * self.scale), round(point[1] * self.size[1] / REFERENCE_HEIGHT))

    # -- friend + feedback -----------------------------------------------------------

    def friend(self, avatar_id: str) -> CastFeedback:
        character = greeter_for(avatar_id)
        height = self._rect(HOME_GREETER).height
        key = (character, height)
        friend = self._friends.get(key)
        if friend is None:
            friend = CastFeedback(
                character,
                height=max(16, height),
                art=self._kit.art,
                idle_variant="pose_wave",
                hold_seconds=1.4,
                clock=self._clock,
            )
            self._friends[key] = friend
        self._character = character
        return friend

    def celebrate(self, look: Look, kinds: tuple[ChoiceKind, ...]) -> None:
        """Friend cheers and the changed part of Home sparkles."""

        self.friend(look.avatar).correct()
        now = self._clock()
        points: list[tuple[int, int]] = []
        for kind in kinds:
            points.extend(_ANCHORS.get(kind, ()))
        self._sparkles = [(point, now + index * 0.08) for index, point in enumerate(points[:4])]

    def think(self, look: Look) -> None:
        self.friend(look.avatar).try_again()

    @property
    def animating(self) -> bool:
        now = self._clock()
        if any(now - start < SPARKLE_SECONDS for _, start in self._sparkles):
            return True
        friend = self._friends.get((self._character, self._rect(HOME_GREETER).height))
        return bool(friend is not None and friend.animating)

    def update(self, look: Look) -> bool:
        changed = self.friend(look.avatar).update()
        now = self._clock()
        before = len(self._sparkles)
        self._sparkles = [(p, start) for p, start in self._sparkles if now - start < SPARKLE_SECONDS]
        return changed or bool(self._sparkles) or before != len(self._sparkles)

    # -- drawing ----------------------------------------------------------------------

    def draw(
        self,
        target: pygame.Surface,
        topleft: tuple[int, int],
        look: Look,
        choices: MyGreiaChoices,
        *,
        custom: Path | None = None,
    ) -> None:
        static = self.static(look, choices, custom=custom)
        x, y = topleft
        target.blit(static, (x, y))
        previous_clip = target.get_clip()
        target.set_clip(pygame.Rect(x, y, *self.size))
        try:
            greeter = self._rect(HOME_GREETER)
            self.friend(look.avatar).draw(target, (x + greeter.centerx, y + greeter.bottom))
            self._draw_sparkles(target, (x, y))
        finally:
            target.set_clip(previous_clip)

    def _draw_sparkles(self, target: pygame.Surface, origin: tuple[int, int]) -> None:
        now = self._clock()
        size = max(28, round(140 * self.scale))
        for point, start in self._sparkles:
            age = now - start
            if age < 0 or age >= SPARKLE_SECONDS:
                continue
            variant = "default" if int(age / 0.15) % 2 == 0 else "frame_2"
            image = self._kit.art.image("fx.sparkle", size, variant=variant)
            if image is None:
                continue
            px, py = self._point(point)
            target.blit(image, image.get_rect(center=(origin[0] + px, origin[1] + py)))

    def static(self, look: Look, choices: MyGreiaChoices, *, custom: Path | None = None) -> pygame.Surface:
        key = (look, self.size, str(custom) if custom else None)
        cached = self._static.get(key)
        if cached is not None:
            return cached
        surface = self._compose(look, choices, custom)
        self._static[key] = surface
        self.build_count += 1
        return surface

    def _compose(self, look: Look, choices: MyGreiaChoices, custom: Path | None) -> pygame.Surface:
        width, height = self.size
        room = choices.background(look.background)
        accent = choices.accent(look.accent)
        panel = mix(room, (255, 255, 255), 0.78)
        surface = self._art.home_backdrop(look.wallpaper, room, (width, height), custom=custom)
        self._draw_portals(surface, look)
        self._draw_badge(surface, look, panel, accent)
        self._draw_star(surface, panel, accent)
        return rounded(surface, max(8, round(22 * self.scale)), outline=None)

    def _draw_portals(self, surface: pygame.Surface, look: Look) -> None:
        try:
            scale = InterfaceSize(look.size).scale
        except ValueError:
            scale = 1.0
        font_px = max(7, round(HOME_LABEL_FONT_PX * self.scale * scale))
        for (collection, hue, icon_id, box), slot_box in zip(HOME_PORTALS, HOME_LABEL_SLOTS):
            portal = self._rect(box)
            tile = self._kit.art.image("ui.portal.collection", portal.size, variant=hue)
            if tile is not None:
                surface.blit(tile, portal)
                if collection == HOME_FOCUSED_PORTAL:
                    ring = self._kit.art.image("ui.portal.collection_focus", portal.size)
                    if ring is not None:
                        surface.blit(ring, portal)
            else:
                pygame.draw.rect(surface, (148, 100, 201), portal.inflate(-portal.width // 6, -portal.height // 6), border_radius=portal.width // 5)
            icon_size = max(8, round(portal.width * PORTAL_ICON_FRACTION))
            icon = self._art.icon(icon_id, icon_size)
            if icon is not None:
                center = (
                    portal.x + round(portal.width * PORTAL_WINDOW_CENTER[0]),
                    portal.y + round(portal.height * PORTAL_WINDOW_CENTER[1]),
                )
                surface.blit(icon, icon.get_rect(center=center))
            text = self._labels.get(collection, "")
            if not text:
                continue
            slot = self._rect(slot_box)
            label = self._typography.render(text, FontRole.BODY, font_px, CAPTION_INK)
            max_text = max(12, slot.width - slot.height)
            if label.get_width() > max_text:
                label = pygame.transform.smoothscale(
                    label, (max_text, max(1, round(label.get_height() * max_text / label.get_width())))
                )
            pill_w = min(slot.width, label.get_width() + max(8, slot.height))
            pill = caption_pill(label, (pill_w, slot.height), focused=collection == HOME_FOCUSED_PORTAL)
            surface.blit(pill, pill.get_rect(midtop=(slot.centerx, slot.y)))

    def _draw_badge(self, surface: pygame.Surface, look: Look, panel, accent) -> None:
        badge = self._rect(HOME_BADGE)
        side = min(badge.width, badge.height)
        frame = self._kit.art.image("ui.avatar.frame", side)
        if frame is not None:
            rect = frame.get_rect(center=badge.center)
            surface.blit(frame, rect)
            center = (rect.centerx, rect.top + round(rect.height * 123 / 260))
            avatar_size = max(8, round(side * 0.51))
        else:
            pygame.draw.rect(surface, panel, badge, border_radius=max(4, side // 4))
            pygame.draw.rect(surface, accent, badge, width=max(2, side // 16), border_radius=max(4, side // 4))
            center = badge.center
            avatar_size = max(8, side - 8)
        avatar = self._art.icon(look.avatar, avatar_size)
        if avatar is not None:
            surface.blit(avatar, avatar.get_rect(center=center))

    def _draw_star(self, surface: pygame.Surface, panel, accent) -> None:
        box = self._rect(HOME_STAR)
        radius = max(4, round(20 * self.scale))
        pygame.draw.rect(surface, panel, box, border_radius=radius)
        pygame.draw.rect(surface, accent, box, width=max(2, round(4 * self.scale)), border_radius=radius)
        star = self._art.icon("yellow_star", max(10, box.width - round(24 * self.scale)))
        if star is not None:
            surface.blit(star, star.get_rect(center=(box.centerx, box.centery - round(4 * self.scale))))
        pill_h = max(6, round(20 * self.scale))
        pill = pygame.Rect(0, 0, max(pill_h, round(24 * self.scale)), pill_h)
        pill.bottomright = (box.right + 1, box.bottom + 1)
        pygame.draw.rect(surface, accent, pill, border_radius=pill_h // 2)


__all__ = ["HomePreview", "greeter_for"]
