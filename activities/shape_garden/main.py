from __future__ import annotations

import math
import random

import pygame

from greia_platform.activity_api import activity_stop_requested, get_icon_path, mark_activity_ready


BACKGROUND = (239, 248, 218)
SOIL = (151, 104, 61)
COLORS = [
    (247, 93, 89),
    (255, 190, 46),
    (80, 188, 112),
    (67, 150, 222),
    (168, 105, 214),
]


def main() -> int:
    pygame.init()
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    pygame.mouse.set_visible(False)
    clock = pygame.time.Clock()
    shapes: list[tuple[int, int, int, int, int]] = []
    close_icon = pygame.image.load(str(get_icon_path("close_button", 64))).convert_alpha()
    cursor_icon = pygame.image.load(str(get_icon_path("yellow_star", 64))).convert_alpha()
    running = True
    mark_activity_ready()

    while running and not activity_stop_requested():
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN and event.key in {pygame.K_BACKSPACE, pygame.K_RETURN}:
                running = False
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                x, y = event.pos
                if (x - 48) ** 2 + (y - 48) ** 2 <= 42 ** 2:
                    running = False
                elif y < screen.get_height() - 70:
                    shapes.append((x, y, random.randint(18, 48), random.randrange(3), random.randrange(len(COLORS))))

        screen.fill(BACKGROUND)
        pygame.draw.rect(screen, SOIL, (0, screen.get_height() - 70, screen.get_width(), 70))
        for x, y, size, kind, color_index in shapes[-120:]:
            draw_shape(screen, x, y, size, kind, COLORS[color_index])

        screen.blit(close_icon, close_icon.get_rect(center=(48, 48)))
        if pygame.mouse.get_focused():
            screen.blit(cursor_icon, cursor_icon.get_rect(center=pygame.mouse.get_pos()))

        pygame.display.flip()
        clock.tick(30)

    pygame.quit()
    return 0


def draw_shape(surface: pygame.Surface, x: int, y: int, size: int, kind: int, color: tuple[int, int, int]) -> None:
    if kind == 0:
        pygame.draw.circle(surface, color, (x, y), size)
    elif kind == 1:
        pygame.draw.rect(surface, color, (x - size, y - size, size * 2, size * 2), border_radius=max(3, size // 5))
    else:
        points = []
        for index in range(5):
            angle = math.radians(-90 + index * 72)
            points.append((x + int(math.cos(angle) * size), y + int(math.sin(angle) * size)))
        pygame.draw.polygon(surface, color, points)


if __name__ == "__main__":
    raise SystemExit(main())
