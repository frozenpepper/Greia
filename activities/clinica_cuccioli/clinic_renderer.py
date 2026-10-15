from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Final

import pygame

from greia_platform.localization import LocalizedResources
from greia_platform.pygame_completion import CompletionContent, PygameCompletionScreen
from greia_platform.system_chrome import ActivitySystemChromeLayout
from greia_platform.typography import FontRole, GreiaTypography

try:
    from clinic_art import draw_patient, draw_thought_bubble, draw_tool_icon
    from clinic_model import ClinicSession, TOOL_IDS
except ImportError:
    from .clinic_art import draw_patient, draw_thought_bubble, draw_tool_icon
    from .clinic_model import ClinicSession, TOOL_IDS


REFERENCE_WIDTH: Final = 1024
REFERENCE_HEIGHT: Final = 600
TABLE_RECT = pygame.Rect(REFERENCE_WIDTH // 2 - 250, 150, 500, 270)
PLAY_AGAIN_RECT = pygame.Rect(REFERENCE_WIDTH // 2 - 120, REFERENCE_HEIGHT // 2 + 70, 240, 60)
PALETTE_Y = 480
# The star pill starts clear of the trusted Home/Back region, which the
# platform reserves in full (both slots) so layout never jumps with context.
STAR_PILL_LEFT: Final = (
    ActivitySystemChromeLayout.for_surface(REFERENCE_WIDTH, REFERENCE_HEIGHT)
    .protected_region.right
    + 8
)
MAX_PARTICLES = 96

_TOOL_TEXT_KEYS = {
    "stethoscope": "tool.stethoscope.short",
    "bath": "tool.bath.short",
    "bandaid": "tool.bandaid.short",
    "food": "tool.food.short",
    "cuddle": "tool.cuddle.short",
}


@dataclass(slots=True)
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    color: tuple[int, int, int]
    size: float
    life: float = 1.0


class ClinicRenderer:
    """Own Clinic Pygame presentation, geometry and bounded transient effects.

    Active treatment and terminal completion are intentionally different render
    modes. The terminal mode uses Greia's shared opaque prepared completion screen:
    no live clinic scene is rendered underneath it, no full-screen alpha blend is
    performed, and repeated terminal draws are one opaque blit.
    """

    def __init__(self, typography: GreiaTypography, resources: LocalizedResources) -> None:
        self._typography = typography
        self._resources = resources
        self._backdrop = self._build_backdrop()
        self._tool_labels: dict[tuple[str, str], pygame.Surface] = {}
        self._star_value: int | None = None
        self._star_surface: pygame.Surface | None = None
        self._particles: list[Particle] = []
        self._completion = PygameCompletionScreen(
            typography,
            width=REFERENCE_WIDTH,
            height=REFERENCE_HEIGHT,
            primary_rect=PLAY_AGAIN_RECT,
        )
        self._completion_content = CompletionContent(
            title=self._resources.text("victory.all_patients"),
            primary_label=self._resources.text("btn.play_again"),
            achievement_count=5,
        )

    @property
    def has_active_animation(self) -> bool:
        return bool(self._particles)

    def reset_transients(self) -> None:
        self._particles.clear()
        self._completion.clear()

    def update(self, dt: float) -> None:
        if not self._particles:
            return
        surviving: list[Particle] = []
        for particle in self._particles:
            particle.x += particle.vx * dt
            particle.y += particle.vy * dt
            particle.life -= dt
            if particle.life > 0.0:
                surviving.append(particle)
        self._particles = surviving

    def celebrate(self, tool_id: str, origin: tuple[float, float]) -> None:
        """Spawn one bounded success burst around the treated patient."""

        ox, oy = origin
        color = (
            (239, 68, 68)
            if tool_id == "cuddle"
            else ((56, 189, 248) if tool_id == "bath" else (254, 240, 138))
        )
        burst = [
            Particle(
                x=ox + random.uniform(-30, 30),
                y=oy + random.uniform(-30, 30),
                vx=random.uniform(-75, 75),
                vy=random.uniform(-135, -30),
                color=color,
                size=random.uniform(6, 12),
            )
            for _ in range(16)
        ]
        self._particles.extend(burst)
        if len(self._particles) > MAX_PARTICLES:
            self._particles = self._particles[-MAX_PARTICLES:]

    def tool_at(self, point: tuple[int, int]) -> str | None:
        for index, tool_id in enumerate(TOOL_IDS):
            if self.tool_rect(index).collidepoint(point):
                return tool_id
        return None

    @staticmethod
    def tool_rect(index: int) -> pygame.Rect:
        return pygame.Rect(60 + index * 185, PALETTE_Y, 165, 96)

    @staticmethod
    def patient_contains(point: tuple[int, int]) -> bool:
        return TABLE_RECT.collidepoint(point)

    def play_again_contains(self, point: tuple[int, int]) -> bool:
        return self._completion.primary_contains(point)

    def render(self, surface: pygame.Surface, session: ClinicSession, now: float) -> None:
        if session.is_victory:
            self._completion.prepare(self._completion_content)
            self._completion.draw(surface)
            return

        surface.blit(self._backdrop, (0, 0))
        self._draw_patient(surface, session, now)
        self._draw_prescription(surface, session)
        self._draw_particles(surface)
        self._draw_palette(surface, session)
        self._draw_star_pill(surface, session.total_stars)

    def _build_backdrop(self) -> pygame.Surface:
        surface = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT))
        surface.fill((255, 247, 237))
        for x in range(0, REFERENCE_WIDTH, 48):
            pygame.draw.rect(surface, (254, 237, 222), (x, 0, 24, REFERENCE_HEIGHT))
        pygame.draw.rect(surface, (254, 215, 170), (0, 420, REFERENCE_WIDTH, 180))
        pygame.draw.line(surface, (217, 119, 6), (0, 420), (REFERENCE_WIDTH, 420), 4)
        pygame.draw.rect(surface, (255, 255, 255), TABLE_RECT, border_radius=28)
        pygame.draw.rect(surface, (203, 213, 225), TABLE_RECT, width=6, border_radius=28)
        pygame.draw.ellipse(
            surface,
            (241, 245, 249),
            pygame.Rect(
                TABLE_RECT.left + 20,
                TABLE_RECT.top + 20,
                TABLE_RECT.width - 40,
                TABLE_RECT.height - 40,
            ),
        )
        return surface

    def _draw_patient(
        self,
        surface: pygame.Surface,
        session: ClinicSession,
        now: float,
    ) -> None:
        draw_patient(
            surface,
            session.patient_id,
            TABLE_RECT.centerx,
            TABLE_RECT.centery + 15,
            180,
            has_mud=session.has_mud,
            has_scratch=session.has_scratch,
            completed_steps=session.completed_steps,
            is_happy=False,
        )
        draw_thought_bubble(
            surface,
            TABLE_RECT.centerx + 130,
            TABLE_RECT.centery - 85,
            session.next_needed,
            now,
        )

    def _draw_prescription(self, surface: pygame.Surface, session: ClinicSession) -> None:
        clip_width = max(260, len(session.required_steps) * 80 + 40)
        clip_rect = pygame.Rect(REFERENCE_WIDTH // 2 - clip_width // 2, 14, clip_width, 64)
        pygame.draw.rect(surface, (255, 255, 255), clip_rect, border_radius=20)
        pygame.draw.rect(surface, (234, 179, 8), clip_rect, width=3, border_radius=20)

        badge_start_x = clip_rect.left + 45
        for index, step_id in enumerate(session.required_steps):
            x = badge_start_x + index * 75
            y = clip_rect.centery
            is_done = step_id in session.completed_steps
            is_current = step_id == session.next_needed
            badge_color = (
                (34, 197, 94)
                if is_done
                else ((254, 240, 138) if is_current else (241, 245, 249))
            )
            border_color = (
                (22, 101, 52)
                if is_done
                else ((234, 179, 8) if is_current else (203, 213, 225))
            )
            pygame.draw.circle(surface, badge_color, (x, y), 24)
            pygame.draw.circle(surface, border_color, (x, y), 24, 3 if is_current else 2)
            if is_done:
                pygame.draw.circle(surface, (34, 197, 94), (x, y), 22)
                pygame.draw.lines(
                    surface,
                    (255, 255, 255),
                    False,
                    [(x - 8, y), (x - 2, y + 6), (x + 8, y - 6)],
                    3,
                )
            else:
                draw_tool_icon(surface, step_id, x, y, 30)

    def _draw_particles(self, surface: pygame.Surface) -> None:
        for particle in self._particles:
            pygame.draw.circle(
                surface,
                particle.color,
                (int(particle.x), int(particle.y)),
                max(1, int(particle.size)),
            )

    def _draw_palette(self, surface: pygame.Surface, session: ClinicSession) -> None:
        for index, tool_id in enumerate(TOOL_IDS):
            rect = self.tool_rect(index)
            is_selected = tool_id == session.selected_tool_id
            is_needed = tool_id == session.next_needed
            state = "selected" if is_selected else ("needed" if is_needed else "default")
            pygame.draw.rect(surface, (255, 255, 255), rect, border_radius=22)
            outline = (
                (234, 179, 8)
                if is_selected
                else ((34, 197, 94) if is_needed else (203, 213, 225))
            )
            pygame.draw.rect(
                surface,
                outline,
                rect,
                width=5 if (is_selected or is_needed) else 2,
                border_radius=22,
            )
            draw_tool_icon(surface, tool_id, rect.centerx, rect.top + 36, 52)
            label = self._tool_label(tool_id, state)
            surface.blit(label, (rect.centerx - label.get_width() // 2, rect.bottom - 26))

    def _tool_label(self, tool_id: str, state: str) -> pygame.Surface:
        key = (tool_id, state)
        cached = self._tool_labels.get(key)
        if cached is not None:
            return cached
        color = (
            (180, 83, 9)
            if state == "selected"
            else ((22, 101, 52) if state == "needed" else (71, 85, 105))
        )
        rendered = self._typography.render(
            self._resources.text(_TOOL_TEXT_KEYS[tool_id]),
            FontRole.DISPLAY,
            18,
            color,
        )
        self._tool_labels[key] = rendered
        return rendered

    def _draw_star_pill(self, surface: pygame.Surface, total_stars: int) -> None:
        rect = pygame.Rect(STAR_PILL_LEFT, 16, 130, 56)
        pygame.draw.rect(surface, (255, 255, 255), rect, border_radius=18)
        pygame.draw.rect(surface, (234, 179, 8), rect, width=3, border_radius=18)
        pygame.draw.circle(surface, (234, 179, 8), (rect.left + 30, rect.centery), 16)
        if self._star_value != total_stars or self._star_surface is None:
            self._star_value = total_stars
            self._star_surface = self._typography.render(
                str(total_stars), FontRole.DISPLAY, 28, (180, 83, 9)
            )
        surface.blit(
            self._star_surface,
            (rect.left + 58, rect.centery - self._star_surface.get_height() // 2),
        )
