"""Heart final-entry pilot: four chambers, circulation, heartbeat and exercise."""

from __future__ import annotations

from dataclasses import dataclass
import math

import pygame

from greia_platform.typography import FontRole

if __package__ and "." in __package__:
    from ..enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from ..enciclopedia_presentation import (
        announce_focus_name,
        draw_heart_button,
        draw_focus_patch,
        draw_navigation_arrows,
        draw_smoke_toggle,
        encyclopedia_focus_cue,
    )
    from ..enciclopedia_focus_audio import FocusAudioTracker
    from .common import draw_centered_text, draw_presenter, focus_ring, grid_step
else:
    from enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from enciclopedia_presentation import (
        announce_focus_name,
        draw_heart_button,
        draw_focus_patch,
        draw_navigation_arrows,
        draw_smoke_toggle,
        encyclopedia_focus_cue,
    )
    from enciclopedia_focus_audio import FocusAudioTracker
    from pages.common import draw_centered_text, draw_presenter, focus_ring, grid_step


@dataclass(frozen=True, slots=True)
class HeartDiscovery:
    discovery_id: str
    caption_key: str
    cue_id: str
    center: tuple[int, int]


DISCOVERIES = (
    HeartDiscovery("chambers", "heart.chambers", "encyclopedia.body.heart.chambers", (260, 205)),
    HeartDiscovery("circulation", "heart.circulation", "encyclopedia.body.heart.circulation", (745, 205)),
    HeartDiscovery("beat", "heart.beat", "encyclopedia.body.heart.beat", (260, 410)),
    HeartDiscovery("exercise", "heart.exercise", "encyclopedia.body.heart.exercise", (745, 410)),
)


class HeartModel:
    """Own animation timing and reveal state for the schematic circulation model."""

    def __init__(self) -> None:
        self.time = 0.0
        self.chambers_age = 0.0
        self.circulation_age = 0.0
        self.beat_age = 0.0
        self.exercise_age = 0.0

    @property
    def rate(self) -> float:
        return 1.75 if self.exercise_age > 0.0 else 1.0

    @property
    def beat_phase(self) -> float:
        return (self.time * 1.35 * self.rate) % 1.0

    def update(self, dt: float) -> None:
        self.time += dt
        self.chambers_age = max(0.0, self.chambers_age - dt)
        self.circulation_age = max(0.0, self.circulation_age - dt)
        self.beat_age = max(0.0, self.beat_age - dt)
        self.exercise_age = max(0.0, self.exercise_age - dt)

    def reveal_chambers(self) -> None:
        self.chambers_age = 3.5

    def reveal_circulation(self) -> None:
        self.circulation_age = 4.0

    def emphasize_beat(self) -> None:
        self.beat_age = 3.5

    def exercise(self) -> None:
        self.exercise_age = 4.0
        self.circulation_age = max(self.circulation_age, 4.0)


class HeartPage(EncyclopediaPage):
    page_id = "body.heart"

    def __init__(self, context) -> None:
        super().__init__(context)

        self._focus_audio = FocusAudioTracker()
        self._model = HeartModel()
        self._selected = 0
        self._hovered: int | None = None
        self._caption_key = "heart.intro"
        self._hotspots = tuple(
            pygame.Rect(cx - 43, cy - 43, 86, 86)
            for cx, cy in (item.center for item in DISCOVERIES)
        )
        self._time = 0.0
        self._arrow_left_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._arrow_right_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._heart_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.body.heart.intro")
        self._announce_selected()

    def _announce_selected(self) -> None:
        disc = DISCOVERIES[self._selected]
        cue = encyclopedia_focus_cue(disc.discovery_id, "name")
        # Use deduped announce for focus changes
        if not self._focus_audio.announce_once(self.context.audio, cue):
            # Fallback to disc.cue_id if focus cue not yet integrated (will fail silently until audio exists)
            self._focus_audio.announce_once(self.context.audio, disc.cue_id)

    def _set_selected(self, index: int) -> None:
        index = max(0, min(len(DISCOVERIES) - 1, index))
        if index == self._selected:
            return
        self._selected = index
        self._announce_selected()

    def update(self, dt: float) -> None:
        self._time += dt
        self._model.update(dt)

    def handle_input(self, event: PageInput) -> None:
        if event.position is not None and event.kind in {
            PageInputKind.POINTER_MOVE,
            PageInputKind.POINTER_PRESS,
        }:
            point = (int(event.position[0]), int(event.position[1]))
            if event.kind is PageInputKind.POINTER_PRESS:
                if self._heart_hit.collidepoint(point):
                    self._trigger_beat()
                    return
                if self._arrow_left_hit.collidepoint(point):
                    self._set_selected(self._selected - 1)
                    return
                if self._arrow_right_hit.collidepoint(point):
                    self._set_selected(self._selected + 1)
                    return
            hit = next(
                (index for index, rect in enumerate(self._hotspots) if rect.collidepoint(point)),
                None,
            )
            if event.kind is PageInputKind.POINTER_MOVE and hit is not None and hit != self._selected:
                disc = DISCOVERIES[hit]
                cue = encyclopedia_focus_cue("body", "heart", disc.discovery_id, "name")
                self._focus_audio.announce_once(self.context.audio, cue)
            self._hovered = hit
            if event.kind is PageInputKind.POINTER_PRESS and hit is not None:
                self._set_selected(hit)
                self._activate(hit)
            return
        if event.kind is not PageInputKind.COMMAND or event.command is None:
            return
        if event.command is PageCommand.ACTIVATE:
            # If next is beat, give big toy priority via keyboard
            if DISCOVERIES[self._selected].discovery_id == "beat":
                self._trigger_beat()
                return
            self._activate(self._selected)
            return
        prev = self._selected
        self._selected = grid_step(
            self._selected,
            event.command,
            columns=2,
            count=len(DISCOVERIES),
        )
        if self._selected != prev:
            self._announce_selected()

    def _trigger_beat(self) -> None:
        self._model.emphasize_beat()
        self._caption_key = "heart.beat"
        announce_focus_name(self.context.audio, encyclopedia_focus_cue("body", "heart", "beat", "name"))
        self.context.audio.play("encyclopedia.body.heart.beat")

    def _activate(self, index: int) -> None:
        discovery = DISCOVERIES[index]
        self._caption_key = discovery.caption_key
        if discovery.discovery_id == "chambers":
            self._model.reveal_chambers()
        elif discovery.discovery_id == "circulation":
            self._model.reveal_circulation()
        elif discovery.discovery_id == "beat":
            self._model.emphasize_beat()
        else:
            self._model.exercise()
        self.context.audio.play(discovery.cue_id)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((248, 230, 225))
        draw_centered_text(
            surface,
            self.context.typography,
            self.context.resources.text("heart.title"),
            center=(500, 92),
            size=40,
            color=self.context.palette.ink,
            role=FontRole.DISPLAY,
        )
        self._draw_body_and_heart(surface)
        self._draw_hotspots(surface)
        # Standard navigation for discovery
        can_left = self._selected > 0
        can_right = self._selected < len(DISCOVERIES) - 1
        self._arrow_left_hit, self._arrow_right_hit = draw_navigation_arrows(
            surface, time=self._time, can_go_left=can_left, can_go_right=can_right
        )
        # Main toy — big heart beat button at bottom center (above caption)
        beating = self._model.beat_age > 0 or self._model.exercise_age > 0
        self._heart_hit = draw_heart_button(
            surface, (512, 485), time=self._time, beating=beating
        )
        self._draw_caption(surface)
        draw_presenter(
            surface,
            self.context.visuals,
            "lilli",
            position=(925, 565),
            height=142,
            variant="happy",
            fallback_color=(229, 137, 183),
        )

    def _draw_body_and_heart(self, surface: pygame.Surface) -> None:
        skin = (235, 189, 160)
        pygame.draw.circle(surface, skin, (505, 184), 42)
        pygame.draw.rect(surface, skin, (445, 225, 120, 230), border_radius=48)
        pygame.draw.line(surface, skin, (455, 260), (390, 405), 24)
        pygame.draw.line(surface, skin, (555, 260), (620, 405), 24)
        pygame.draw.ellipse(surface, (224, 155, 163), (456, 266, 48, 82))
        pygame.draw.ellipse(surface, (224, 155, 163), (506, 266, 48, 82))

        beat = self._model.beat_phase
        double_pulse = max(0.0, math.sin(beat * math.pi * 2.0)) + 0.45 * max(
            0.0,
            math.sin((beat - 0.18) * math.pi * 2.0),
        )
        scale = 1.0 + (0.10 + (0.08 if self._model.beat_age > 0 else 0.0)) * min(1.0, double_pulse)
        self._draw_heart(surface, (505, 350), int(42 * scale))

        if self._model.chambers_age > 0:
            self._draw_chambers(surface, (505, 350))
        if self._model.circulation_age > 0 or self._model.exercise_age > 0:
            self._draw_circulation(surface)
        if self._model.exercise_age > 0:
            for index in range(4):
                y = 245 + index * 28
                pygame.draw.line(surface, (228, 104, 92), (585, y), (600 + index * 8, y), 5)

    @staticmethod
    def _draw_heart(surface: pygame.Surface, center: tuple[int, int], size: int) -> None:
        cx, cy = center
        color = (197, 63, 78)
        pygame.draw.circle(surface, color, (cx - size // 3, cy - size // 5), size // 2)
        pygame.draw.circle(surface, color, (cx + size // 3, cy - size // 5), size // 2)
        pygame.draw.polygon(
            surface,
            color,
            [(cx - size, cy), (cx + size, cy), (cx, cy + int(size * 1.55))],
        )
        pygame.draw.line(surface, (127, 45, 62), (cx, cy - 18), (cx, cy + 42), 3)

    @staticmethod
    def _draw_chambers(surface: pygame.Surface, center: tuple[int, int]) -> None:
        cx, cy = center
        colors = ((123, 68, 92), (183, 72, 87), (113, 60, 84), (214, 83, 88))
        rects = (
            pygame.Rect(cx - 36, cy - 29, 32, 28),
            pygame.Rect(cx + 4, cy - 29, 32, 28),
            pygame.Rect(cx - 36, cy + 5, 32, 34),
            pygame.Rect(cx + 4, cy + 5, 32, 34),
        )
        for color, rect in zip(colors, rects):
            pygame.draw.rect(surface, color, rect, border_radius=9)
            pygame.draw.rect(surface, (250, 218, 207), rect, 2, border_radius=9)

    def _draw_circulation(self, surface: pygame.Surface) -> None:
        # Dark red/purple denotes oxygen-poor blood; it is deliberately not blue.
        to_lungs = ((505, 350), (450, 328), (456, 295), (480, 300))
        to_body = ((505, 350), (560, 330), (620, 280), (655, 235))
        back_from_body = ((655, 235), (645, 390), (565, 420), (505, 350))
        back_from_lungs = ((530, 300), (555, 300), (560, 330), (505, 350))
        progress = (self._model.time * 0.55 * self._model.rate) % 1.0
        paths = (
            (to_lungs, (117, 61, 84), progress),
            (back_from_lungs, (218, 72, 78), (progress + 0.30) % 1.0),
            (to_body, (218, 72, 78), (progress + 0.52) % 1.0),
            (back_from_body, (117, 61, 84), (progress + 0.76) % 1.0),
        )
        for points, color, phase in paths:
            pygame.draw.lines(surface, color, False, points, 5)
            x, y = self._point_on_path(points, phase)
            pygame.draw.circle(surface, color, (int(x), int(y)), 9)
            pygame.draw.circle(surface, (252, 235, 226), (int(x), int(y)), 9, 2)

    @staticmethod
    def _point_on_path(
        points: tuple[tuple[int, int], ...],
        progress: float,
    ) -> tuple[float, float]:
        segment_count = len(points) - 1
        position = min(0.999999, max(0.0, progress)) * segment_count
        index = min(segment_count - 1, int(position))
        local = position - index
        x1, y1 = points[index]
        x2, y2 = points[index + 1]
        return x1 + (x2 - x1) * local, y1 + (y2 - y1) * local

    def _draw_hotspots(self, surface: pygame.Surface) -> None:
        for index, (item, rect) in enumerate(zip(DISCOVERIES, self._hotspots)):
            pygame.draw.circle(surface, (255, 248, 235), item.center, 37)
            pygame.draw.circle(surface, (85, 58, 59), item.center, 37, 3)
            cx, cy = item.center
            if item.discovery_id == "chambers":
                for dx, dy in ((-12, -12), (12, -12), (-12, 12), (12, 12)):
                    pygame.draw.rect(surface, (196, 72, 86), (cx + dx - 8, cy + dy - 8, 16, 16), border_radius=5)
            elif item.discovery_id == "circulation":
                pygame.draw.arc(surface, (211, 73, 79), (cx - 24, cy - 24, 48, 48), 0, math.pi * 1.4, 5)
                pygame.draw.polygon(surface, (211, 73, 79), [(cx + 22, cy - 10), (cx + 28, cy + 3), (cx + 14, cy + 2)])
            elif item.discovery_id == "beat":
                self._draw_heart(surface, (cx, cy - 2), 16)
            else:
                pygame.draw.circle(surface, (231, 108, 87), (cx - 12, cy - 2), 12)
                pygame.draw.line(surface, (83, 65, 62), (cx + 3, cy + 14), (cx + 16, cy - 14), 7)
                pygame.draw.line(surface, (83, 65, 62), (cx + 5, cy + 3), (cx + 22, cy + 13), 7)
            # Unified halo — pulse
            if index == self._selected or index == self._hovered:
                draw_focus_patch(surface, rect, active=True, radius=16, time=self._time)

    def _draw_caption(self, surface: pygame.Surface) -> None:
        panel = pygame.Rect(305, 510, 400, 68)
        pygame.draw.rect(surface, (255, 248, 235), panel, border_radius=22)
        pygame.draw.rect(surface, (85, 58, 59), panel, 3, border_radius=22)
        text = self.context.resources.text(self._caption_key)
        rendered = self.context.typography.render(text, FontRole.BODY, 18, (62, 49, 49))
        if rendered.get_width() > panel.width - 26:
            rendered = self.context.typography.render(text, FontRole.BODY, 15, (62, 49, 49))
        surface.blit(rendered, rendered.get_rect(center=panel.center))
