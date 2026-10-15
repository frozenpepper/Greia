"""Presentation for Leo's Post: composer, flight, delivery, postbox, card view.

The renderer only blits prepared surfaces from :class:`PostcardArt` and the
kit layer (drawn by the app's ``SurfaceNavigator``); it owns the small moving
parts — Leo the host (cheer / think / point), the receiving friend, FX bursts,
hint halos — and the message layout on the back of a card. Child-authored
text is rendered exactly as typed (no case policy), wrapped on grapheme
boundaries inside the message lane.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
import math
import time
from typing import Final

import pygame

from greia_platform.activity_controls import BodyShape
from greia_platform.activity_feedback import CastFeedback
from greia_platform.typography import FontRole, GreiaTypography, grapheme_boundaries

if __package__:
    from .postcard_art import INK, PostcardArt, lane_rect
    from .postcard_content import HOST, MAX_SAVED_CARDS, REFERENCE_HEIGHT, REFERENCE_WIDTH
    from .postcard_layout import CardViewLayout, ComposerLayout, DeliveredLayout, PostboxLayout, SheetLayout
else:
    from postcard_art import INK, PostcardArt, lane_rect
    from postcard_content import HOST, MAX_SAVED_CARDS, REFERENCE_HEIGHT, REFERENCE_WIDTH
    from postcard_layout import CardViewLayout, ComposerLayout, DeliveredLayout, PostboxLayout, SheetLayout

# Historical message-lane bounds (also used by the shared text-consistency
# test): a message never runs past this width at 32 px, in at most 7 lines.
MESSAGE_LANE_WIDTH: Final = 330
MAX_MESSAGE_LINES: Final = 7
MESSAGE_SIZES: Final = (34, 30, 26, 22)
TEXT_COLOR: Final = (40, 44, 66)
CARET: Final = (2, 132, 199)

FOLD_SECONDS: Final = 0.45
FLY_SECONDS: Final = 0.8
DROP_SECONDS: Final = 0.5
SEND_SECONDS: Final = FOLD_SECONDS + FLY_SECONDS + DROP_SECONDS
FLIP_SECONDS: Final = 0.28


class CastActor:
    """A cast friend: cheers and thinks through ``CastFeedback``; also points."""

    def __init__(
        self,
        character: str,
        art: PostcardArt,
        clock: Callable[[], float],
        *,
        height: int,
        point_left: bool = False,
        hold_seconds: float = 1.6,
    ) -> None:
        self.character = character
        self.height = height
        self.feedback = CastFeedback(character, height=height, art=art.loader, clock=clock, hold_seconds=hold_seconds)
        self._clock = clock
        point = art.cast(character, "pose_point", height)
        self._point = pygame.transform.flip(point, True, False) if (point is not None and point_left) else point
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

    def reset(self) -> None:
        self._point_until = 0.0
        self.feedback.reset()

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
    """One short shared-library FX animation (frames scaled once)."""

    DURATION = 0.8

    def __init__(self, frames: tuple[pygame.Surface, ...], center: tuple[int, int], *, clock=time.monotonic) -> None:
        self._frames = frames
        self._center = center
        self._clock = clock
        self._start = clock()

    @property
    def done(self) -> bool:
        return self._clock() - self._start >= self.DURATION

    def draw(self, target: pygame.Surface) -> None:
        if not self._frames or self.done:
            return
        progress = (self._clock() - self._start) / self.DURATION
        frame = self._frames[min(len(self._frames) - 1, int(progress * len(self._frames) * 2) % len(self._frames))]
        target.blit(frame, frame.get_rect(center=self._center))


@dataclass(slots=True)
class Motion:
    """Short-lived presentation state: hint halos, bursts, flip and flight."""

    halos: dict[str, float] = field(default_factory=dict)
    bursts: list[FxBurst] = field(default_factory=list)
    flip_frames: tuple[pygame.Surface, ...] = ()
    flip_start: float = 0.0
    send_frames: tuple[pygame.Surface, ...] = ()
    send_start: float = 0.0

    def prune(self, now: float) -> None:
        self.halos = {key: until for key, until in self.halos.items() if until > now}
        self.bursts = [burst for burst in self.bursts if not burst.done]
        if self.flip_frames and now - self.flip_start >= FLIP_SECONDS:
            self.flip_frames = ()

    def active(self, now: float) -> bool:
        return bool(self.halos or self.bursts or self.flip_frames or self.send_frames)

    def add_burst(self, burst: FxBurst) -> None:
        self.bursts = [*self.bursts[-3:], burst]


@dataclass(frozen=True, slots=True)
class MessageView:
    """Prepared lines of one message at one size (+ caret geometry)."""

    lines: tuple[tuple[pygame.Surface, int], ...]
    pitch: int
    size: int
    spans: tuple[tuple[int, int], ...]


class PostcardRenderer:
    """Draw every screen from prepared art; owns the message layout cache."""

    def __init__(self, art: PostcardArt, typography: GreiaTypography, clock: Callable[[], float] = time.monotonic) -> None:
        self.art = art
        self._typography = typography
        self._clock = clock
        # One-entry wrap cache: the draft changes at most once per keystroke,
        # not once per frame, so re-measuring every frame would be waste.
        self._wrap_key: tuple[str, FontRole, int, int] | None = None
        self._wrap_value: tuple[tuple[int, int], ...] = ()
        self._message_key: tuple | None = None
        self._message: MessageView | None = None
        self._tilted: dict[tuple, pygame.Surface] = {}
        self._tray_rects: dict[str, pygame.Rect] = {}
        self._pending_badge: tuple[pygame.Surface, tuple[int, int]] | None = None
        self._pending_checks: list[pygame.Rect] = []

    # -- message layout ---------------------------------------------------------

    def _wrapped_spans(self, text: str, role: FontRole, size: int, max_width: int) -> tuple[tuple[int, int], ...]:
        """Split ``text`` into ``(start, end)`` line spans that fit ``max_width``.

        Breaks prefer the last space; a word wider than the lane is broken at
        a grapheme boundary so emoji/accent clusters are never split.
        """

        key = (text, role, size, max_width)
        if key == self._wrap_key:
            return self._wrap_value
        bounds = grapheme_boundaries(text)
        spans: list[tuple[int, int]] = []
        start = 0
        last_space = -1
        previous = 0
        for bound in bounds[1:]:
            if self._typography.measure(text[start:bound].rstrip(), role, size).width > max_width and previous > start:
                end = last_space + 1 if last_space > start else previous
                spans.append((start, end))
                start = end
                last_space = -1
            if text[bound - 1] == " ":
                last_space = bound - 1
            previous = bound
        if start < len(text) or not spans:
            spans.append((start, len(text)))
        self._wrap_key = key
        self._wrap_value = tuple(spans)
        return self._wrap_value

    def message_view(self, text: str, lane: pygame.Rect) -> MessageView:
        """Largest size whose wrapped lines fit the lane (one-entry cache)."""

        key = (text, lane.size)
        if key == self._message_key and self._message is not None:
            return self._message
        scale = lane.height / 255
        chosen: MessageView | None = None
        for base in MESSAGE_SIZES:
            size = max(12, round(base * scale))
            pitch = round(size * 1.32)
            spans = self._wrapped_spans(text, FontRole.DISPLAY, size, lane.width)
            if len(spans) * pitch <= lane.height or base == MESSAGE_SIZES[-1]:
                lines = tuple(
                    (self._typography.render(text[a:b].rstrip(), FontRole.DISPLAY, size, TEXT_COLOR), a)
                    for a, b in spans[: max(1, lane.height // pitch)]
                    if text[a:b].strip()
                )
                chosen = MessageView(lines, pitch, size, spans)
                break
        assert chosen is not None
        self._message_key = key
        self._message = chosen
        return chosen

    def draw_message(self, target: pygame.Surface, text: str, lane: pygame.Rect, *, cursor: int | None = None) -> None:
        if not text:
            if cursor is not None:
                size = max(12, round(MESSAGE_SIZES[0] * lane.height / 255))
                pygame.draw.line(target, CARET, (lane.left + 2, lane.top + 4), (lane.left + 2, lane.top + 4 + size), 3)
            return
        view = self.message_view(text, lane)
        index_of_line = {start: row for row, (start, _end) in enumerate(view.spans)}
        for surface, start in view.lines:
            row = index_of_line.get(start, 0)
            target.blit(surface, (lane.left, lane.top + row * view.pitch))
        if cursor is not None:
            row = 0
            for index, (start, end) in enumerate(view.spans):
                if start <= cursor <= end:
                    row = index
            start = view.spans[row][0]
            before = text[start:cursor]
            x = self._typography.measure(before, FontRole.DISPLAY, view.size).width if before else 0
            y = lane.top + row * view.pitch
            if y + view.size <= lane.bottom + view.pitch:
                pygame.draw.line(target, CARET, (lane.left + x + 1, y + 2), (lane.left + x + 1, y + view.size + 4), 3)

    # -- composer -------------------------------------------------------------------

    def draw_composer(
        self,
        target: pygame.Surface,
        layout: ComposerLayout,
        *,
        face: pygame.Surface,
        back: pygame.Surface | None,
        showing_back: bool,
        text: str,
        cursor: int | None,
        motion: Motion,
        host: CastActor,
        drag: tuple[pygame.Surface, tuple[int, int]] | None,
        done_steps: set[str],
        postbox_count: int,
        hide_card: bool = False,
    ) -> None:
        target.blit(self.art.background(), (0, 0))
        tray = layout.tray
        target.blit(self.art.panel((tray.width, tray.height)), tray.topleft)
        card = layout.card
        if not hide_card:
            target.blit(self.art.shadow(card.size), card.move(0, 6))
            if motion.flip_frames:
                progress = (self._clock() - motion.flip_start) / FLIP_SECONDS
                frame = motion.flip_frames[min(len(motion.flip_frames) - 1, int(progress * len(motion.flip_frames)))]
                target.blit(frame, frame.get_rect(center=card.center))
            elif showing_back and back is not None:
                target.blit(back, card.topleft)
                self.draw_message(target, text, lane_rect(card), cursor=cursor)
            else:
                target.blit(face, card.topleft)
                if drag is not None:
                    image, center = drag
                    target.blit(image, image.get_rect(center=center))
        host.draw(target, layout.host_midbottom)
        self._draw_halos(target, motion, layout)
        # Badges sit on top of kit tiles, so ``draw_composer_overlays`` blits
        # them after the control layer.
        mailbox = layout.mailbox
        self._pending_badge = (
            (self.art.badge(postbox_count, 40), (mailbox.right - 6, mailbox.top + 6)) if postbox_count else None
        )
        self._pending_checks = [
            layout.steps[index]
            for index, step in enumerate(("friend", "picture", "stickers", "message"))
            if step in done_steps
        ]

    def draw_composer_overlays(self, target: pygame.Surface) -> None:
        """Small badges on top of kit tiles (step done ticks, postbox count)."""

        check = self.art.tick(30)
        for rect in self._pending_checks:
            target.blit(check, check.get_rect(center=(rect.right - 6, rect.top + 6)))
        if self._pending_badge is not None:
            badge, center = self._pending_badge
            target.blit(badge, badge.get_rect(center=center))

    def _draw_halos(self, target: pygame.Surface, motion: Motion, layout: ComposerLayout) -> None:
        now = self._clock()
        alpha = round(150 + 105 * math.sin(now * 7.0))
        for key, until in motion.halos.items():
            rect = self._halo_rect(key, layout)
            if rect is None or until <= now:
                continue
            halo = self.art.halo(rect.size)
            halo.set_alpha(alpha)
            target.blit(halo, halo.get_rect(center=rect.center))
            halo.set_alpha(None)

    def _halo_rect(self, key: str, layout: ComposerLayout) -> pygame.Rect | None:
        if key == "send":
            return layout.send
        if key == "card":
            return layout.card
        if key == "tray":
            return layout.tray.inflate(-16, -16)
        if key.startswith("step."):
            steps = {"friend": 0, "picture": 1, "stickers": 2, "message": 3}
            index = steps.get(key.split(".", 1)[1])
            return layout.steps[index] if index is not None else None
        if key.startswith("tray:"):
            return self._tray_rects.get(key[5:])
        return None

    def remember_tray(self, rects: dict[str, pygame.Rect]) -> None:
        self._tray_rects = dict(rects)

    def flip_frames(self, start: pygame.Surface, end: pygame.Surface) -> tuple[pygame.Surface, ...]:
        """A squash-and-turn: start narrows to an edge, end widens back (built once)."""

        width, height = start.get_size()
        frames = []
        for scale in (0.7, 0.35, 0.08):
            frames.append(pygame.transform.smoothscale(start, (max(2, round(width * scale)), height)))
        for scale in (0.08, 0.35, 0.7, 1.0):
            frames.append(end if scale == 1.0 else pygame.transform.smoothscale(end, (max(2, round(width * scale)), height)))
        return tuple(frames)

    # -- sending ---------------------------------------------------------------------

    def send_frames(self, face: pygame.Surface) -> tuple[pygame.Surface, ...]:
        width, height = face.get_size()
        return tuple(
            pygame.transform.smoothscale(face, (max(4, round(width * scale)), max(4, round(height * scale))))
            for scale in (0.82, 0.62, 0.44, 0.28, 0.16)
        )

    def draw_sending(
        self,
        target: pygame.Surface,
        layout: ComposerLayout,
        motion: Motion,
        host: CastActor,
        postbox_count: int,
        blank_face: pygame.Surface | None = None,
    ) -> int:
        """Fold the card, fly the paper plane into the mailbox; return mailbox lift."""

        elapsed = self._clock() - motion.send_start
        target.blit(self.art.background(), (0, 0))
        tray = layout.tray
        target.blit(self.art.panel((tray.width, tray.height)), tray.topleft)
        host.draw(target, layout.host_midbottom)
        card = layout.card
        mailbox = layout.mailbox
        lift = 0
        landed = elapsed >= FOLD_SECONDS + FLY_SECONDS
        if landed:
            t = min(1.0, (elapsed - FOLD_SECONDS - FLY_SECONDS) / DROP_SECONDS)
            lift = -round(math.sin(math.pi * t) * 16)
        self._draw_mailbox(target, mailbox.move(0, lift), postbox_count if landed else max(0, postbox_count - 1))
        if elapsed < FOLD_SECONDS and motion.send_frames:
            frame = motion.send_frames[min(len(motion.send_frames) - 1, int(elapsed / FOLD_SECONDS * len(motion.send_frames)))]
            target.blit(frame, frame.get_rect(center=card.center))
        elif blank_face is not None:
            # The next postcard is already waiting.
            target.blit(self.art.shadow(card.size), card.move(0, 6))
            target.blit(blank_face, card.topleft)
        return lift

    def draw_flight(self, target: pygame.Surface, layout: ComposerLayout, motion: Motion) -> None:
        """The paper plane, above every control, on its arc into the mailbox."""

        elapsed = self._clock() - motion.send_start
        card = layout.card
        mailbox = layout.mailbox
        if FOLD_SECONDS <= elapsed < FOLD_SECONDS + FLY_SECONDS:
            t = (elapsed - FOLD_SECONDS) / FLY_SECONDS
            start = pygame.Vector2(card.center)
            end = pygame.Vector2(mailbox.center)
            control = pygame.Vector2((start.x + end.x) / 2, min(start.y, end.y) - 220)
            point = (1 - t) ** 2 * start + 2 * (1 - t) * t * control + t ** 2 * end
            # Three prepared sizes (cached by the loader), never a per-frame scale.
            plane = self.art.loader.image("icon.hud.send", (96, 80, 64)[min(2, int(t * 3))])
            if plane is not None:
                target.blit(plane, plane.get_rect(center=(round(point.x), round(point.y))))

    def _draw_mailbox(self, target: pygame.Surface, rect: pygame.Rect, count: int) -> None:
        """Leo's mailbox while the controls are away (same look as its tile)."""

        painter = self.art.painter
        body = painter.body(BodyShape.TILE, rect.size, painter.theme.surface, lip=max(2, round(rect.height * 0.07)))
        target.blit(body, rect.topleft)
        icon = self.art.loader.image("icon.hud.mailbox", 80)
        if icon is not None:
            target.blit(icon, icon.get_rect(center=(rect.centerx, rect.centery - 3)))
        if count:
            badge = self.art.badge(count, 40)
            target.blit(badge, badge.get_rect(center=(rect.right - 6, rect.top + 6)))

    # -- delivered -----------------------------------------------------------------------

    def draw_delivered(
        self,
        target: pygame.Surface,
        layout: DeliveredLayout,
        *,
        face: pygame.Surface,
        face_key: object,
        friend: CastActor,
        motion: Motion,
    ) -> None:
        target.blit(self.art.delivered_backdrop(), (0, 0))
        key = (face_key, face.get_size())
        tilted = self._tilted.get(key)
        if tilted is None:
            # Card + its shadow, turned once (never per frame).
            width, height = face.get_size()
            board = pygame.Surface((width + 12, height + 14), pygame.SRCALPHA)
            board.blit(self.art.shadow(face.get_size()), (8, 12))
            board.blit(face, (0, 0))
            tilted = pygame.transform.rotozoom(board, 4, 1.0)
            self._tilted.clear()
            self._tilted[key] = tilted
        target.blit(tilted, tilted.get_rect(center=layout.card.center))
        friend.draw(target, layout.friend_midbottom)
        for burst in motion.bursts:
            burst.draw(target)

    # -- postbox ----------------------------------------------------------------------------

    def draw_postbox(
        self,
        target: pygame.Surface,
        layout: PostboxLayout,
        faces: list[tuple[pygame.Rect, pygame.Surface, str, bool]],
        *,
        page: int,
        page_count: int,
        focus_slot: int | None,
        full: bool,
        empty_icon: pygame.Surface | None,
    ) -> None:
        target.blit(self.art.background(), (0, 0))
        if not faces:
            area = pygame.Rect(0, 0, 420, 250)
            area.center = (REFERENCE_WIDTH // 2, (layout.cards[0].top + layout.cards[-1].bottom) // 2)
            target.blit(self.art.panel(area.size), area.topleft)
            mailbox = self.art.loader.image("icon.hud.mailbox", 120)
            host = self.art.cast(HOST, "happy", 170)
            if host is not None:
                target.blit(host, host.get_rect(midbottom=(area.centerx - 70, area.bottom - 12)))
            if mailbox is not None:
                target.blit(mailbox, mailbox.get_rect(midbottom=(area.centerx + 90, area.bottom - 30)))
        for slot, (rect, face, friend_id, has_text) in enumerate(faces):
            if slot == focus_slot:
                halo = self.art.halo(rect.size)
                target.blit(halo, halo.get_rect(center=rect.center))
            target.blit(self.art.shadow(rect.size), rect.move(0, 5))
            target.blit(face, rect.topleft)
            portrait = self.art.cast(friend_id, "happy", 74)
            if portrait is not None:
                target.blit(portrait, portrait.get_rect(midbottom=(rect.left + 34, rect.bottom + 10)))
            if has_text:
                page_icon = self.art.loader.image("icon.hud.page", 34)
                if page_icon is not None:
                    target.blit(page_icon, page_icon.get_rect(bottomright=(rect.right - 8, rect.bottom - 6)))
        self._draw_page_dots(target, layout, page, page_count)
        if full:
            meter = self.art.meter((150, 30), MAX_SAVED_CARDS, MAX_SAVED_CARDS)
            target.blit(meter, meter.get_rect(midleft=(layout.chip.right + 18, layout.chip.centery)))

    def _draw_page_dots(self, target: pygame.Surface, layout: PostboxLayout, page: int, page_count: int) -> None:
        if page_count <= 1:
            return
        dot, gap = 9, 12
        total = page_count * dot * 2 + (page_count - 1) * gap
        x = layout.dots_centre[0] - total // 2 + dot
        theme = self.art.painter.theme
        for index in range(page_count):
            current = index == page
            radius = dot if current else dot - 2
            pygame.draw.circle(target, INK, (x, layout.dots_centre[1]), radius)
            pygame.draw.circle(target, theme.accent if current else (236, 224, 200), (x, layout.dots_centre[1]), radius - 2)
            x += dot * 2 + gap

    # -- one card ------------------------------------------------------------------------------

    def draw_card_view(
        self,
        target: pygame.Surface,
        layout: CardViewLayout,
        *,
        face: pygame.Surface,
        back: pygame.Surface,
        showing_back: bool,
        text: str,
        friend: CastActor,
        motion: Motion,
    ) -> None:
        target.blit(self.art.background(), (0, 0))
        card = layout.card
        target.blit(self.art.shadow(card.size), card.move(0, 6))
        if motion.flip_frames:
            progress = (self._clock() - motion.flip_start) / FLIP_SECONDS
            frame = motion.flip_frames[min(len(motion.flip_frames) - 1, int(progress * len(motion.flip_frames)))]
            target.blit(frame, frame.get_rect(center=card.center))
        elif showing_back:
            target.blit(back, card.topleft)
            self.draw_message(target, text, lane_rect(card))
        else:
            target.blit(face, card.topleft)
        friend.draw(target, layout.friend_midbottom)
        for burst in motion.bursts:
            burst.draw(target)

    # -- sheets ------------------------------------------------------------------------------------

    def draw_sheet(
        self,
        target: pygame.Surface,
        layout: SheetLayout,
        preview: pygame.Surface,
        *,
        symbol: pygame.Surface | None,
    ) -> None:
        target.blit(self.art.dim((REFERENCE_WIDTH, REFERENCE_HEIGHT)), (0, 0))
        target.blit(self.art.panel(layout.panel.size, alpha=255), layout.panel.topleft)
        target.blit(preview, preview.get_rect(center=layout.preview.center))
        if symbol is not None:
            target.blit(symbol, symbol.get_rect(center=layout.symbol))


__all__ = [
    "CastActor",
    "FLIP_SECONDS",
    "FxBurst",
    "MAX_MESSAGE_LINES",
    "MESSAGE_LANE_WIDTH",
    "MessageView",
    "Motion",
    "PostcardRenderer",
    "SEND_SECONDS",
]
