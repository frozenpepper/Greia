"""Small visual/input helpers shared by multiple encyclopedia pages."""

from __future__ import annotations

import pygame

from greia_platform.typography import FontRole

if __package__ and "." in __package__:
    from ..enciclopedia_engine import PageCommand
else:
    from enciclopedia_engine import PageCommand


def draw_centered_text(
    surface: pygame.Surface,
    typography: object,
    text: str,
    *,
    center: tuple[int, int],
    size: int,
    color: tuple[int, int, int],
    role: FontRole = FontRole.TITLE,
) -> pygame.Rect:
    rendered = typography.render(text, role, size, color)
    rect = rendered.get_rect(center=center)
    surface.blit(rendered, rect)
    return rect


def draw_presenter(
    surface: pygame.Surface,
    visuals: object,
    character_id: str,
    *,
    position: tuple[int, int],
    height: int = 150,
    variant: str = "default",
    fallback_color: tuple[int, int, int] = (253, 200, 85),
) -> None:
    sprite = visuals.character(character_id, variant=variant, height=height)
    if sprite is not None:
        surface.blit(sprite, sprite.get_rect(midbottom=position))
        return
    pygame.draw.circle(surface, fallback_color, (position[0], position[1] - height // 2), height // 3)
    pygame.draw.circle(surface, (61, 44, 31), (position[0] - 14, position[1] - height // 2), 4)
    pygame.draw.circle(surface, (61, 44, 31), (position[0] + 14, position[1] - height // 2), 4)


def focus_ring(surface: pygame.Surface, rect: pygame.Rect, active: bool) -> None:
    if not active:
        return
    expanded = rect.inflate(10, 10)
    pygame.draw.rect(surface, (255, 214, 74), expanded, 5, border_radius=22)


def grid_step(index: int, command: PageCommand, *, columns: int, count: int) -> int:
    if count < 1:
        return 0
    row, col = divmod(index, columns)
    if command is PageCommand.LEFT:
        col = max(0, col - 1)
    elif command is PageCommand.RIGHT:
        col = min(columns - 1, col + 1)
    elif command is PageCommand.UP:
        row = max(0, row - 1)
    elif command is PageCommand.DOWN:
        row += 1
    candidate = row * columns + col
    return max(0, min(count - 1, candidate))
