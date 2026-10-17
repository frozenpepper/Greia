"""Stories of My Voice — scene drawing for every screen.

The renderer composes prepared art (``StoryArt``) and reads state handed to
it by the app; it owns no rules. Screens: story picker, order the cards,
tell each card, watch the slideshow and the My-stories shelf (plus the
backdrops of the two modal sheets). Kit controls are drawn afterwards by the
app's ``ControlLayer``. Per-frame work is blits plus a couple of cheap
primitive arcs for the live recording ring.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
import math
from typing import Final

import pygame

from greia_platform.activity_feedback import CastFeedback

if __package__:
    from .voice_art import INK, REC_RED, StoryArt
    from .voice_content import (
        LEGACY_SCENES,
        MAX_SAVED_STORIES,
        MEADOW,
        BEDROOM,
        CardArt,
        StoryTemplate,
        story_by_id,
    )
    from .voice_layout import (
        HOST_HEIGHT,
        HOST_MIDBOTTOM,
        OrderLayout,
        PickerLayout,
        SheetLayout,
        ShelfLayout,
        TellLayout,
        WatchLayout,
    )
    from .voice_model import OrderingBoard
else:
    from voice_art import INK, REC_RED, StoryArt
    from voice_content import (
        LEGACY_SCENES,
        MAX_SAVED_STORIES,
        MEADOW,
        BEDROOM,
        CardArt,
        StoryTemplate,
        story_by_id,
    )
    from voice_layout import (
        HOST_HEIGHT,
        HOST_MIDBOTTOM,
        OrderLayout,
        PickerLayout,
        SheetLayout,
        ShelfLayout,
        TellLayout,
        WatchLayout,
    )
    from voice_model import OrderingBoard

FX_SECONDS: Final = 0.7
FLIGHT_SECONDS: Final = 0.32
SLIDE_IN_SECONDS: Final = 0.35
GUIDE_SECONDS: Final = 1.6
MAX_FX: Final = 16
MAX_FLIGHTS: Final = 8
CREAM: Final = (255, 249, 236)
FALLBACK_ART: Final = CardArt(MEADOW, ())


def card_art(template_id: str, card_id: str) -> CardArt:
    """Art for a saved card; unknown cards fall back to a quiet meadow."""

    template = story_by_id(template_id)
    card = template.card(card_id) if template is not None else None
    if card is None:
        card = LEGACY_SCENES.card(card_id)
    return card.art if card is not None else FALLBACK_ART


@dataclass(slots=True)
class Flight:
    card_id: str
    start: pygame.Rect
    end: pygame.Rect
    started: float
    duration: float = FLIGHT_SECONDS


@dataclass
class Motion:
    """Short-lived presentation state (bounded)."""

    flights: deque = field(default_factory=lambda: deque(maxlen=MAX_FLIGHTS))
    fx: deque = field(default_factory=lambda: deque(maxlen=MAX_FX))
    halos: dict[str, float] = field(default_factory=dict)  # "slot.N" / "card.X" -> until
    wobble: dict[str, float] = field(default_factory=dict)  # card id -> started
    slide_started: float = -10.0
    # A generic "move a card up" finger gesture (never points at the answer).
    guide: tuple[pygame.Rect, pygame.Rect, float] | None = None

    def clear(self) -> None:
        self.guide = None
        self.flights.clear()
        self.fx.clear()
        self.halos.clear()
        self.wobble.clear()

    def fly(self, flight: Flight) -> None:
        self.flights.append(flight)

    def add_fx(self, name: str, position: tuple[int, int], start: float) -> None:
        self.fx.append((name, position, start))

    def flying(self, card_id: str, now: float) -> bool:
        return any(f.card_id == card_id and now < f.started + f.duration for f in self.flights)

    def active(self, now: float) -> bool:
        return (
            any(now < f.started + f.duration for f in self.flights)
            or any(now - start < FX_SECONDS for _, _, start in self.fx)
            or any(now < until for until in self.halos.values())
            or any(now - started < 0.45 for started in self.wobble.values())
            or now - self.slide_started < SLIDE_IN_SECONDS
            or (self.guide is not None and now < self.guide[2] + GUIDE_SECONDS)
        )

    def prune(self, now: float) -> None:
        while self.flights and now >= self.flights[0].started + self.flights[0].duration:
            self.flights.popleft()
        while self.fx and now - self.fx[0][2] >= FX_SECONDS:
            self.fx.popleft()
        for key in [key for key, until in self.halos.items() if now >= until]:
            del self.halos[key]
        for key in [key for key, started in self.wobble.items() if now - started >= 0.45]:
            del self.wobble[key]


class HostCast:
    """Leo: cheers and thinks through ``CastFeedback``; also points and waves."""

    def __init__(self, feedback: CastFeedback, art: StoryArt, clock: Callable[[], float]) -> None:
        self.feedback = feedback
        self._clock = clock
        self._point = art.host("pose_point", HOST_HEIGHT)
        self._wave = art.host("pose_wave", HOST_HEIGHT)
        self._loader = art.loader
        self._point_until = 0.0
        self.waving = False

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

    def draw(self, target: pygame.Surface, midbottom: tuple[int, int] = HOST_MIDBOTTOM) -> None:
        if self.pointing and self._point is not None:
            target.blit(self._loader.presentable(self._point, target), self._point.get_rect(midbottom=midbottom))
            return
        if self.waving and not self.feedback.animating and self._wave is not None:
            target.blit(self._loader.presentable(self._wave, target), self._wave.get_rect(midbottom=midbottom))
            return
        self.feedback.draw(target, midbottom)


@dataclass(slots=True)
class DragState:
    card_id: str
    origin: pygame.Rect
    position: tuple[int, int]
    grab: tuple[int, int]
    moved: bool = False

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(self.position[0] - self.grab[0], self.position[1] - self.grab[1], self.origin.width, self.origin.height)


@dataclass(slots=True)
class RecordingView:
    counting: bool = False
    countdown_progress: float = 0.0
    recording: bool = False
    elapsed: float = 0.0
    limit: float = 30.0
    level: float = 0.0


class StoryRenderer:
    """Draw each screen from prepared art and app-provided state."""

    def __init__(self, art: StoryArt, cast: HostCast, clock: Callable[[], float]) -> None:
        self.art = art
        self.cast = cast
        self._clock = clock

    # -- picker -----------------------------------------------------------------

    def draw_picker(self, surface: pygame.Surface, layout: PickerLayout, *, mic_ok: bool) -> None:
        surface.blit(self.art.background(MEADOW + ("bg.meadow_day.foreground",), veil=40), (0, 0))
        self.cast.draw(surface)
        if not mic_ok:
            self._no_mic(surface, layout.top.right(0, layout.top.bar.height))

    # -- order ------------------------------------------------------------------

    def draw_order(
        self,
        surface: pygame.Surface,
        template: StoryTemplate,
        board: OrderingBoard,
        layout: OrderLayout,
        motion: Motion,
        drag: DragState | None,
    ) -> None:
        now = self._clock()
        surface.blit(self.art.background(template.cards[0].art.layers, veil=90), (0, 0))
        surface.blit(self.art.panel(layout.board.size), layout.board.topleft)
        size = layout.slots[0].size
        for index, rect in enumerate(layout.slots):
            card = board.slots[index]
            hidden = card is not None and (motion.flying(card, now) or (drag is not None and drag.card_id == card))
            if card is None or hidden:
                surface.blit(self.art.slot(size, index + 1, active=f"slot.{index}" in motion.halos), rect)
            else:
                self._card(surface, template, card, rect, motion, now)
                badge = self.art.number(index + 1, max(30, rect.height // 4), accent=(108, 190, 120) if index in board.locked else None)
                surface.blit(badge, badge.get_rect(center=(rect.left + 6, rect.top + 6)))
            self._halo(surface, f"slot.{index}", rect, motion, now)
        for index, rect in enumerate(layout.tray):
            card = board.tray[index]
            if card is None:
                surface.blit(self.art.home(size), rect)
                continue
            if motion.flying(card, now) or (drag is not None and drag.card_id == card):
                continue
            self._card(surface, template, card, rect, motion, now)
        for flight in motion.flights:
            progress = (now - flight.started) / flight.duration
            if 0 <= progress < 1:
                eased = 1 - (1 - progress) ** 3
                x = flight.start.x + (flight.end.x - flight.start.x) * eased
                y = flight.start.y + (flight.end.y - flight.start.y) * eased - math.sin(math.pi * progress) * 26
                art = template.card(flight.card_id)
                if art is not None:
                    surface.blit(self.art.card(art.art, size, key=flight.card_id), (round(x), round(y)))
        if drag is not None:
            art = template.card(drag.card_id)
            if art is not None:
                rect = drag.rect
                surface.blit(self.art.shadow(size), rect.move(6, 10))
                surface.blit(self.art.card(art.art, size, key=drag.card_id), rect)
        self._guide(surface, motion, now)
        self._fx(surface, motion, now)
        self.cast.draw(surface)

    def _guide(self, surface: pygame.Surface, motion: Motion, now: float) -> None:
        if motion.guide is None:
            return
        start, end, started = motion.guide
        progress = (now - started) / GUIDE_SECONDS
        if not 0 <= progress < 1:
            return
        eased = min(1.0, progress / 0.8)
        eased = 1 - (1 - eased) ** 2
        finger = self.art.loader.image("icon.hud.drag_hint", 84)
        if finger is None:
            return
        x = start.centerx + (end.centerx - start.centerx) * eased
        y = start.centery + (end.centery - start.centery) * eased
        surface.blit(finger, finger.get_rect(topleft=(round(x) - 20, round(y) - 6)))

    def _card(self, surface, template: StoryTemplate, card_id: str, rect: pygame.Rect, motion: Motion, now: float) -> None:
        card = template.card(card_id)
        art = card.art if card is not None else FALLBACK_ART
        dx = 0
        started = motion.wobble.get(card_id)
        if started is not None and now - started < 0.45:
            elapsed = now - started
            dx = int(8 * (1 - elapsed / 0.45) * math.sin(elapsed * 40))
        surface.blit(self.art.card(art, rect.size, key=card_id), rect.move(dx, 0))
        self._halo(surface, f"card.{card_id}", rect, motion, now)

    def _halo(self, surface: pygame.Surface, key: str, rect: pygame.Rect, motion: Motion, now: float) -> None:
        until = motion.halos.get(key)
        if until is None or now >= until:
            return
        if int(now * 4) % 2 == 0:
            halo = self.art.halo(rect.size)
            surface.blit(halo, halo.get_rect(center=rect.center))

    # -- tell -------------------------------------------------------------------

    def draw_tell(
        self,
        surface: pygame.Surface,
        template: StoryTemplate,
        card_id: str,
        number: int,
        layout: TellLayout,
        view: RecordingView,
        *,
        has_voice: bool,
        motion: Motion,
        invite: bool = False,
    ) -> None:
        now = self._clock()
        card = template.card(card_id)
        art = card.art if card is not None else FALLBACK_ART
        surface.blit(self.art.background(art.layers, veil=110), (0, 0))
        rect = layout.card
        offset = self._slide_offset(motion, now)
        surface.blit(self.art.shadow(rect.size), rect.move(8 + offset, 12))
        surface.blit(self.art.card(art, rect.size, key=card_id), rect.move(offset, 0))
        badge = self.art.number(number, 58)
        surface.blit(badge, badge.get_rect(center=(rect.left + 10 + offset, rect.top + 10)))
        if has_voice and not view.recording:
            listen = self.art.loader.image("icon.hud.listen", 52)
            if listen is not None:
                surface.blit(listen, listen.get_rect(center=(rect.right - 36 + offset, rect.top + 36)))
        mic = layout.mic
        centre = (mic.centerx, mic.top + (mic.height - 6) // 2)
        radius = min(mic.width, mic.height) // 2
        if view.recording:
            pulse = 0.5 + 0.5 * math.sin(now * 6)
            aura = radius + 10 + int(10 * view.level) + int(4 * pulse)
            disc = self.art.disc(aura, REC_RED, 70)
            surface.blit(disc, disc.get_rect(center=centre))
            ring_rect = pygame.Rect(0, 0, (radius + 22) * 2, (radius + 22) * 2)
            ring_rect.center = centre
            ring = self.art.ring(radius + 22, 8, CREAM, 230)
            surface.blit(ring, ring.get_rect(center=centre))
            share = max(0.0, 1.0 - view.elapsed / max(0.1, view.limit))
            if share > 0.01:
                start = math.pi / 2
                pygame.draw.arc(surface, REC_RED, ring_rect, start, start + 2 * math.pi * share, 8)
            if int(now * 2) % 2 == 0:
                dot = self.art.disc(13, REC_RED, 255)
                surface.blit(dot, dot.get_rect(center=(rect.right - 30 + offset, rect.top + 30)))
                pygame.draw.circle(surface, INK, (rect.right - 30 + offset, rect.top + 30), 13, 3)
        if invite and int(now * 2.5) % 2 == 0:
            glow = self.art.ring(radius + 16, 10, (255, 214, 102), 210)
            surface.blit(glow, glow.get_rect(center=centre))
        if view.counting:
            pips = 3
            lit = min(pips, int(view.countdown_progress * pips) + 1)
            for index in range(pips):
                x = centre[0] + (index - 1) * 34
                y = mic.top - 26
                color = (255, 196, 70) if index < lit else (226, 216, 200)
                pygame.draw.circle(surface, color, (x, y), 12)
                pygame.draw.circle(surface, INK, (x, y), 12, 3)
        self._fx(surface, motion, now)
        self.cast.draw(surface)

    def _slide_offset(self, motion: Motion, now: float) -> int:
        progress = (now - motion.slide_started) / SLIDE_IN_SECONDS
        if progress >= 1 or progress < 0:
            return 0
        return int(90 * (1 - progress) ** 2)

    # -- watch ------------------------------------------------------------------

    def draw_watch(
        self,
        surface: pygame.Surface,
        art: CardArt,
        card_key: str,
        number: int,
        layout: WatchLayout,
        motion: Motion,
        *,
        voiced: bool,
        playing: bool,
        mic_ok: bool,
    ) -> None:
        now = self._clock()
        surface.blit(self.art.background(art.layers, veil=110), (0, 0))
        rect = layout.card
        offset = self._slide_offset(motion, now)
        surface.blit(self.art.shadow(rect.size), rect.move(8 + offset, 12))
        surface.blit(self.art.card(art, rect.size, key=card_key), rect.move(offset, 0))
        badge = self.art.number(number, 60)
        surface.blit(badge, badge.get_rect(center=(rect.left + 10 + offset, rect.top + 10)))
        if voiced and playing:
            size = 54 + int(6 * (0.5 + 0.5 * math.sin(now * 7)))
            listen = self.art.loader.image("icon.hud.listen", size)
            if listen is not None:
                surface.blit(listen, listen.get_rect(center=(rect.right - 40 + offset, rect.top + 40)))
        if not mic_ok:
            self._no_mic(surface, layout.top.right(1, layout.top.bar.height))
        self._fx(surface, motion, now)
        self.cast.draw(surface)

    # -- shelf ------------------------------------------------------------------

    def draw_shelf(
        self,
        surface: pygame.Surface,
        layout: ShelfLayout,
        stories: list,
        cards: list[pygame.Rect],
        *,
        used: int,
        motion: Motion,
    ) -> None:
        now = self._clock()
        surface.blit(self.art.background(BEDROOM, veil=70), (0, 0))
        surface.blit(self.art.meter(layout.meter.size, used, MAX_SAVED_STORIES), layout.meter)
        if not stories:
            basket = self.art.loader.image("ui.empty.basket", 200)
            if basket is not None:
                surface.blit(basket, basket.get_rect(center=layout.empty.center))
        for story, rect in zip(stories, cards):
            art = card_art(story.template_id, story.cover_card)
            surface.blit(self.art.shadow(rect.size), rect.move(6, 8))
            surface.blit(self.art.card(art, rect.size, key=f"{story.template_id}.{story.cover_card}"), rect)
            self._story_dots(surface, rect, len(story.order), len(story.recordings))
            if story.shared:
                check = self.art.loader.image("icon.hud.check", 40)
                if check is not None:
                    surface.blit(check, check.get_rect(bottomright=(rect.right - 8, rect.bottom - 6)))
            self._halo(surface, f"story.{story.story_id}", rect, motion, now)
        self._fx(surface, motion, now)
        self.cast.draw(surface)

    def _story_dots(self, surface: pygame.Surface, rect: pygame.Rect, count: int, voiced: int) -> None:
        size = 16
        spacing = 22
        start = rect.centerx - spacing * (count - 1) // 2
        y = rect.bottom - 16
        for index in range(count):
            color = REC_RED if index < voiced else CREAM
            pygame.draw.circle(surface, color, (start + index * spacing, y), size // 2)
            pygame.draw.circle(surface, INK, (start + index * spacing, y), size // 2, 2)

    # -- sheets -----------------------------------------------------------------

    def draw_sheet(self, surface: pygame.Surface, layout: SheetLayout, preview: pygame.Surface | None, *, accent: tuple[int, int, int], symbol: pygame.Surface | None) -> None:
        surface.blit(self.art.dim(surface.get_size()), (0, 0))
        surface.blit(self.art.panel(layout.panel.size, alpha=255), layout.panel.topleft)
        pygame.draw.rect(surface, accent, layout.panel.inflate(-10, -10), width=4, border_radius=22)
        if preview is not None:
            surface.blit(preview, preview.get_rect(center=layout.preview.center))
        if symbol is not None:
            surface.blit(symbol, symbol.get_rect(center=(layout.preview.right + 6, layout.preview.top + 10)))

    # -- shared ------------------------------------------------------------------

    def _no_mic(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        """Friendly "no microphone" pictogram (display only)."""

        icon = self.art.loader.image("icon.hud.mic_off", min(rect.width, rect.height) - 8)
        if icon is None:
            return
        disc = self.art.disc(min(rect.width, rect.height) // 2, CREAM, 235)
        surface.blit(disc, disc.get_rect(center=rect.center))
        surface.blit(icon, icon.get_rect(center=rect.center))

    def _fx(self, surface: pygame.Surface, motion: Motion, now: float) -> None:
        for name, position, start in motion.fx:
            elapsed = now - start
            if elapsed < 0 or elapsed >= FX_SECONDS:
                continue
            frames = self.art.fx_frames(name)
            if not frames:
                continue
            frame = frames[min(len(frames) - 1, int(elapsed / FX_SECONDS * len(frames)))]
            surface.blit(frame, frame.get_rect(center=position))


__all__ = [
    "DragState",
    "Flight",
    "HostCast",
    "Motion",
    "RecordingView",
    "StoryRenderer",
    "card_art",
]
