from __future__ import annotations

import math
import random

import pygame

from greia_platform.activity_api import (
    activity_stop_requested,
    get_icon_path,
    get_theme,
    mark_activity_ready,
)
from greia_platform.activity_ui import ChildUiMetrics, load_icon, mix
from greia_platform.pygame_canvas import (
    PygameReferenceCanvas,
    activity_viewport_for_surface,
)


REFERENCE_WIDTH = 1024
REFERENCE_HEIGHT = 600
SOIL_TOP = 530
BASE_BACKGROUND = (239, 248, 218)
BASE_SOIL = (151, 104, 61)
COLORS = (
    (247, 93, 89),
    (255, 190, 46),
    (80, 188, 112),
    (67, 150, 222),
    (168, 105, 214),
)


def _safe_point(surface: pygame.Surface, position: tuple[int, int]) -> bool:
    safe = activity_viewport_for_surface(surface).safe_ui_rect()
    x, y = position
    return safe.x <= x < safe.right and safe.y <= y < safe.bottom


def main() -> int:
    pygame.init()
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    pygame.mouse.set_visible(False)
    clock = pygame.time.Clock()
    theme = get_theme()
    metrics = ChildUiMetrics.for_size(*screen.get_size())
    canvas = PygameReferenceCanvas(screen)
    cursor_icon = load_icon(
        get_icon_path("yellow_star", 64),
        metrics.px(44),
    )
    shapes: list[tuple[int, int, int, int, int]] = []
    running = True
    ready_published = False

    while running and not activity_stop_requested():
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.get_surface() or screen
                metrics = ChildUiMetrics.for_size(*screen.get_size())
                canvas = PygameReferenceCanvas(screen)
                cursor_icon = load_icon(
                    get_icon_path("yellow_star", 64),
                    metrics.px(44),
                )
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if not _safe_point(screen, event.pos):
                    continue
                logical = canvas.pointer(event.pos)
                if logical is None:
                    continue
                x, y = (int(round(logical[0])), int(round(logical[1])))
                if 0 <= x < REFERENCE_WIDTH and 0 <= y < SOIL_TOP:
                    shapes.append(
                        (
                            x,
                            y,
                            random.randint(18, 48),
                            random.randrange(3),
                            random.randrange(len(COLORS)),
                        )
                    )

        garden_background = mix(theme.background, BASE_BACKGROUND, 0.58)
        soil = mix(BASE_SOIL, theme.accent, 0.10)
        canvas.surface.fill(garden_background)
        pygame.draw.rect(
            canvas.surface,
            soil,
            (0, SOIL_TOP, REFERENCE_WIDTH, REFERENCE_HEIGHT - SOIL_TOP),
        )
        for x, y, size, kind, color_index in shapes[-120:]:
            draw_shape(canvas.surface, x, y, size, kind, COLORS[color_index])

        canvas.present(clear=theme.background, smooth=True)
        if pygame.mouse.get_focused():
            screen.blit(cursor_icon, cursor_icon.get_rect(center=pygame.mouse.get_pos()))

        pygame.display.flip()
        if not ready_published:
            mark_activity_ready()
            ready_published = True
        clock.tick(30)

    pygame.quit()
    return 0


def draw_shape(
    surface: pygame.Surface,
    x: int,
    y: int,
    size: int,
    kind: int,
    color: tuple[int, int, int],
) -> None:
    if kind == 0:
        pygame.draw.circle(surface, color, (x, y), size)
    elif kind == 1:
        pygame.draw.rect(
            surface,
            color,
            (x - size, y - size, size * 2, size * 2),
            border_radius=max(3, size // 5),
        )
    else:
        points = []
        for index in range(5):
            angle = math.radians(-90 + index * 72)
            points.append(
                (
                    x + int(math.cos(angle) * size),
                    y + int(math.sin(angle) * size),
                )
            )
        pygame.draw.polygon(surface, color, points)


if __name__ == "__main__":
    raise SystemExit(main())