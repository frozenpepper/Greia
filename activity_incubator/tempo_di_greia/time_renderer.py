"""Greia My Time: quiet, large-target reference-canvas presentation.

No raw system Home/Back, no Activity clock setting, no per-frame font loading.
Responsive placement is delegated to PygameReferenceCanvas.
"""
from __future__ import annotations

import math
from typing import Mapping

import pygame

from greia_platform.typography import FontRole, GreiaTypography

if __package__:
    from .time_model import TimeExperience, TimeMode, analog_hand_angles, display_duration, PRESET_MINUTES
else:
    from time_model import TimeExperience, TimeMode, analog_hand_angles, display_duration, PRESET_MINUTES


REFERENCE_SIZE = (1024, 600)
INK = (61, 60, 85)
BG = (247, 241, 226)
PAPER = (255, 253, 244)
CORAL = (230, 120, 101)
SEA = (49, 144, 159)
SUN = (246, 185, 73)
PURPLE = (126, 94, 166)

MODE_BUTTONS = {
    TimeMode.CLOCK: pygame.Rect(398, 30, 170, 65),
    TimeMode.STOPWATCH: pygame.Rect(597, 30, 170, 65),
    TimeMode.TIMER: pygame.Rect(796, 30, 170, 65),
}
ACTION_BUTTONS = {
    "primary": pygame.Rect(542, 362, 210, 85),
    "reset": pygame.Rect(774, 362, 190, 85),
    "practice": pygame.Rect(557, 475, 390, 76),
    "minus": pygame.Rect(551, 365, 100, 88),
    "plus": pygame.Rect(843, 365, 100, 88),
}
PRESET_BUTTONS = tuple(
    pygame.Rect(542 + index * 109, 477, 95, 67)
    for index in range(len(PRESET_MINUTES))
)
# This region exists only while the localized cue is actually available.
REPLAY_BUTTON = pygame.Rect(868, 117, 88, 72)

WORD_KEYS = (
    "title", "clock", "stopwatch", "timer", "real", "practice",
    "back_real", "today", "start", "pause", "reset", "ready",
    "done", "plus", "minus", "minutes",
) + tuple(f"weekday.{index}" for index in range(7))


class TimeRenderer:
    def __init__(self, locale: str, words: Mapping[str, str]) -> None:
        self.locale = "it" if locale == "it" else "en"
        if set(words) != set(WORD_KEYS):
            raise ValueError("time Activity locale keys are incomplete or unexpected")
        self.words = dict(words)
        self.fonts = GreiaTypography()

    def _text(
        self, screen: pygame.Surface, content: str, pos: tuple[int, int],
        size: int, color: tuple[int, int, int] = INK, *,
        centered: bool = False,
    ) -> None:
        font = self.fonts.font(FontRole.CONTROL, size)
        rendered = self.fonts.surface(font, content, color)
        rect = rendered.get_rect(center=pos) if centered else rendered.get_rect(topleft=pos)
        screen.blit(rendered, rect)

    def _button(
        self, screen: pygame.Surface, rect: pygame.Rect, label: str,
        *, selected: bool = False, tint: tuple[int, int, int] = SEA,
        size: int = 23, icon: str | None = None,
    ) -> None:
        color = tint if selected else PAPER
        foreground = PAPER if selected else INK
        pygame.draw.rect(screen, (221, 211, 194), rect.move(0, 5), border_radius=23)
        pygame.draw.rect(screen, color, rect, border_radius=23)
        pygame.draw.rect(screen, (191, 179, 159), rect, 2, border_radius=23)
        # Pictures lead; readable labels remain as optional support.
        if icon is not None:
            self._symbol(screen, icon, (rect.x + 28, rect.centery), foreground)
        self._text(
            screen, label, (rect.centerx + (17 if icon is not None else 0), rect.centery),
            size, foreground, centered=True,
        )

    def _symbol(
        self, screen: pygame.Surface, name: str,
        center: tuple[int, int], color: tuple[int, int, int],
    ) -> None:
        """Four minimal icons made from bounded Pygame primitives (no assets)."""
        x, y = center
        if name in {"clock", "stopwatch"}:
            pygame.draw.circle(screen, color, center, 15, 3)
            pygame.draw.line(screen, color, center, (x, y - 10), 3)
            pygame.draw.line(screen, color, center, (x + 8, y + 5), 3)
            if name == "stopwatch":
                pygame.draw.rect(screen, color, pygame.Rect(x - 5, y - 23, 10, 5), border_radius=2)
        elif name == "timer":
            pygame.draw.line(screen, color, (x - 13, y - 17), (x + 13, y - 17), 4)
            pygame.draw.line(screen, color, (x - 13, y + 17), (x + 13, y + 17), 4)
            pygame.draw.polygon(screen, color, ((x - 10, y - 13), (x + 10, y - 13), (x, y)), 3)
            pygame.draw.polygon(screen, color, ((x, y), (x - 10, y + 13), (x + 10, y + 13)), 3)
        elif name == "play":
            pygame.draw.polygon(screen, color, (
                (x - 8, y - 12), (x + 13, y), (x - 8, y + 12),
            ))
        elif name == "pause":
            pygame.draw.rect(screen, color, pygame.Rect(x - 10, y - 12, 7, 24), border_radius=2)
            pygame.draw.rect(screen, color, pygame.Rect(x + 3, y - 12, 7, 24), border_radius=2)
        elif name == "reset":
            pygame.draw.arc(
                screen, color, pygame.Rect(x - 13, y - 13, 26, 26),
                0.35, 2 * math.pi - 0.35, 4,
            )
            pygame.draw.polygon(screen, color, (
                (x + 14, y + 3), (x + 15, y - 10), (x + 3, y - 7),
            ))
        elif name == "speaker":
            pygame.draw.polygon(screen, color, (
                (x - 19, y - 7), (x - 11, y - 7), (x - 2, y - 16),
                (x - 2, y + 16), (x - 11, y + 7), (x - 19, y + 7),
            ))
            pygame.draw.arc(screen, color, pygame.Rect(x - 7, y - 15, 35, 30),
                            -0.85, 0.85, 3)
        elif name == "hands":
            pygame.draw.circle(screen, color, center, 15, 3)
            pygame.draw.line(screen, color, center, (x - 4, y - 10), 3)
            pygame.draw.line(screen, color, center, (x + 11, y + 4), 3)
            pygame.draw.circle(screen, color, center, 3)

    def _dial(
        self, screen: pygame.Surface, *, angles: tuple[float, float, float] | None,
        fraction: float | None = None, practice: bool = False,
    ) -> None:
        x, y, radius = 286, 338, 180
        pygame.draw.circle(screen, (222, 202, 171), (x, y + 9), radius + 9)
        pygame.draw.circle(screen, (239, 177, 100), (x, y), radius + 9)
        pygame.draw.circle(screen, PAPER, (x, y), radius)
        pygame.draw.circle(screen, (174, 150, 126), (x, y), radius, 3)
        for tick in range(60):
            a = math.radians(tick * 6 - 90)
            outer = radius - 12
            inner = radius - (34 if tick % 5 == 0 else 21)
            color = INK if tick % 5 == 0 else (180, 169, 160)
            pygame.draw.line(
                screen, color,
                (round(x + inner * math.cos(a)), round(y + inner * math.sin(a))),
                (round(x + outer * math.cos(a)), round(y + outer * math.sin(a))),
                4 if tick % 5 == 0 else 2,
            )
        if angles is not None:
            for angle, length, thick, color in (
                (angles[0], 100, 12, INK),
                (angles[1], 138, 8, SEA),
                (angles[2], 151, 3, CORAL),
            ):
                radians = math.radians(angle - 90)
                pygame.draw.line(
                    screen, color, (x, y),
                    (round(x + length * math.cos(radians)), round(y + length * math.sin(radians))),
                    thick,
                )
            for number, degrees in ((12, -90), (3, 0), (6, 90), (9, 180)):
                radians = math.radians(degrees)
                self._text(
                    screen, str(number),
                    (round(x + 111 * math.cos(radians)), round(y + 111 * math.sin(radians))),
                    32, INK, centered=True,
                )
        else:
            clamped = max(0.0, min(1.0, fraction if fraction is not None else 0.0))
            if clamped > 0:
                pygame.draw.arc(
                    screen, SEA, pygame.Rect(x - 135, y - 135, 270, 270),
                    math.pi / 2 - (clamped * 2 * math.pi), math.pi / 2, 24,
                )
        if practice:
            # Two disjoint, touchable rings: 12 illustrated hours inside;
            # quarter-hour minutes on the outer rim.
            pygame.draw.circle(screen, (208, 187, 226), (x, y), 106, 2)
            for hour in range(1, 13):
                angle = math.radians(hour * 30 - 90)
                dot = (round(x + 87 * math.cos(angle)), round(y + 87 * math.sin(angle)))
                selected = angles is not None and int(angles[0] // 30) % 12 == hour % 12
                pygame.draw.circle(screen, PURPLE if selected else (205, 184, 221),
                                   dot, 9 if selected else 6)
                if selected:
                    pygame.draw.circle(screen, PAPER, dot, 3)
            for quarter, degrees in ((0, -90), (15, 0), (30, 90), (45, 180)):
                a = math.radians(degrees)
                dot = (round(x + 156 * math.cos(a)), round(y + 156 * math.sin(a)))
                selected = (
                    angles is not None and
                    abs((angles[1] / 6.0) % 60 - quarter) < 0.01
                )
                pygame.draw.circle(screen, SEA if selected else SUN, dot, 11 if selected else 8)
                pygame.draw.circle(screen, INK, dot, 2)
        pygame.draw.circle(screen, SUN, (x, y), 10)
        pygame.draw.circle(screen, INK, (x, y), 10, 2)

    def _celebrate(self, screen: pygame.Surface) -> None:
        """Quiet completion stars, deterministic and zero per-frame assets."""
        cx, cy = 286, 338
        for index in range(12):
            angle = index * math.pi / 6
            point = (
                round(cx + 199 * math.sin(angle)),
                round(cy - 199 * math.cos(angle)),
            )
            pygame.draw.circle(screen, CORAL if index % 2 else SUN, point, 8 if index % 3 else 11)
            pygame.draw.circle(screen, PAPER, point, 3)

    def draw(
        self, screen: pygame.Surface, model: TimeExperience, *,
        celebrate: bool = False, focus_rect: pygame.Rect | None = None,
        can_repeat: bool = False,
    ) -> None:
        screen.fill(BG)
        pygame.draw.rect(screen, (231, 225, 208), pygame.Rect(85, 113, 900, 463), border_radius=39)
        pygame.draw.rect(screen, PAPER, pygame.Rect(85, 107, 900, 458), border_radius=39)
        self._text(screen, self.words["title"], (112, 48), 29)
        if can_repeat:
            pygame.draw.rect(screen, (221, 211, 194), REPLAY_BUTTON.move(0, 4),
                             border_radius=22)
            pygame.draw.rect(screen, PAPER, REPLAY_BUTTON, border_radius=22)
            pygame.draw.rect(screen, SEA, REPLAY_BUTTON, width=3, border_radius=22)
            self._symbol(screen, "speaker", REPLAY_BUTTON.center, SEA)
        for mode, rect in MODE_BUTTONS.items():
            self._button(
                screen, rect, self.words[mode.value],
                selected=model.mode is mode, tint=PURPLE if mode is TimeMode.CLOCK else SEA,
                size=16 if mode is TimeMode.STOPWATCH else 18, icon=mode.value,
            )
        if model.mode is TimeMode.CLOCK:
            now = model.shown_time()
            self._dial(screen, angles=analog_hand_angles(now), practice=model.practice)
            self._text(screen, now.strftime("%H:%M"), (758, 223), 79, centered=True)
            if model.practice:
                # An imagined clock time is not a real calendar date. In
                # particular, nudging through midnight must not present
                # today's weekday as the illustrated tomorrow.
                self._text(screen, self.words["practice"], (758, 299),
                           23, PURPLE, centered=True)
            else:
                weekday = self.words[f"weekday.{now.weekday()}"]
                self._text(screen, f"{weekday} {now.day:02d}/{now.month:02d}",
                           (758, 299), 26, centered=True)
            if model.practice:
                self._button(screen, ACTION_BUTTONS["minus"], self.words["minus"], tint=CORAL, size=19)
                self._button(screen, ACTION_BUTTONS["plus"], self.words["plus"], tint=CORAL, size=19)
            else:
                self._text(screen, self.words["real"], (758, 411), 24, SEA, centered=True)
            self._button(
                screen, ACTION_BUTTONS["practice"],
                self.words["back_real"] if model.practice else self.words["practice"],
                tint=PURPLE, selected=model.practice, size=20, icon="hands",
            )
        else:
            if model.mode is TimeMode.STOPWATCH:
                seconds = model.stopwatch.seconds()
                running = model.stopwatch.running
                fraction = (seconds % 60) / 60
            else:
                seconds = model.timer.remaining()
                running = model.timer.running
                fraction = seconds / model.timer.duration_seconds
            self._dial(screen, angles=None, fraction=fraction)
            if celebrate and model.mode is TimeMode.TIMER:
                self._celebrate(screen)
            self._text(screen, display_duration(seconds, round_up=model.mode is TimeMode.TIMER),
                       (757, 235), 76, centered=True)
            self._text(screen, self.words["done"] if celebrate else
                       self.words["minutes"] if model.mode is TimeMode.TIMER else self.words["ready"],
                       (758, 319), 27, CORAL if celebrate else INK, centered=True)
            self._button(
                screen, ACTION_BUTTONS["primary"],
                self.words["pause"] if running else self.words["start"],
                selected=running, size=23, icon="pause" if running else "play",
            )
            self._button(screen, ACTION_BUTTONS["reset"], self.words["reset"], tint=CORAL, size=19, icon="reset")
            if model.mode is TimeMode.TIMER:
                for minutes, rect in zip(PRESET_MINUTES, PRESET_BUTTONS):
                    self._button(
                        screen, rect, f"{minutes} MIN",
                        selected=model.timer.duration_seconds == minutes * 60, size=17,
                    )
        if focus_rect is not None:
            pygame.draw.rect(
                screen, PURPLE, focus_rect.inflate(8, 8),
                width=4, border_radius=26,
            )


__all__ = ["TimeRenderer", "WORD_KEYS", "MODE_BUTTONS", "ACTION_BUTTONS", "PRESET_BUTTONS", "REPLAY_BUTTON", "REFERENCE_SIZE"]
