"""La Memoria delle Meraviglie — Activity lifecycle and event loop.

This module owns the game state (cards, flips, moves, particles,
victory) and the event loop. The rendering and audio subsystems are
injected so this class can be unit-tested in isolation once the
Pygame surface and storage are faked.

The Activity does not own the real Greia Home/Back chrome: R7.3
migrated that authority to the trusted launcher chrome path.
Protected region geometry is preserved via the shared
``activity_viewport_for_surface`` helper so this Activity still
respects Greia's safe pointer zone.
"""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from typing import Any

import pygame

from greia_platform.activity_api import (
    emit_activity_event,
)
from greia_platform.activity_ui import ChildUiMetrics
from greia_platform.child_text import display_text
from greia_platform.localization import LocalizedResources
from greia_platform.pygame_canvas import (
    PygameReferenceCanvas,
    activity_viewport_for_surface,
)
from greia_platform.pygame_completion import CompletionContent, PygameCompletionScreen
from greia_platform.typography import FontRole, GreiaTypography

if __package__:
    from .memory_audio import MemoryAudio
    from .memory_content import (
        GRID_CONFIGS,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        STORAGE_KEY,
        THEMES,
    )
    from .memory_render import compute_grid_layout, draw_card_illustration
else:
    from memory_audio import MemoryAudio
    from memory_content import (
        GRID_CONFIGS,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        STORAGE_KEY,
        THEMES,
    )
    from memory_render import compute_grid_layout, draw_card_illustration


def _is_safe_point(surface: pygame.Surface, position: tuple[int, int]) -> bool:
    """True when the pointer sits inside the play surface and outside
    the Greia protected region(s). The real Greia Home/Back chrome
    is owned by the launcher; this gate keeps the Activity pointer
    out of any protected region the platform may still expose here.
    """
    vp = activity_viewport_for_surface(surface)
    x, y = position
    if not (0 <= x < vp.surface.width and 0 <= y < vp.surface.height):
        return False
    for protected in vp.protected_regions:
        if protected.x <= x < protected.right and protected.y <= y < protected.bottom:
            return False
    return True


@dataclass
class MemoryApp:
    screen: pygame.Surface
    canvas: PygameReferenceCanvas
    metrics: ChildUiMetrics
    typography: GreiaTypography
    sounds: MemoryAudio
    resources: LocalizedResources | None
    active_locale: str
    storage: Any
    completion: PygameCompletionScreen
    completion_content: CompletionContent
    theme_idx: int = 0
    grid_idx: int = 1
    selected_card_index: int = 0
    cards: list[dict[str, Any]] = field(default_factory=list)
    flipped_indices: list[int] = field(default_factory=list)
    pairs_found: int = 0
    total_pairs: int = 3
    moves_count: int = 0
    unflip_timer: float = 0.0
    particles: list[dict[str, Any]] = field(default_factory=list)
    is_victory: bool = False
    completion_presented: bool = False
    ready_published: bool = False
    _running: bool = True

    def __post_init__(self) -> None:
        self._start_new_game()

    # ------------------------------------------------------------------
    # Domain state transitions
    # ------------------------------------------------------------------

    def _start_new_game(self) -> None:
        theme_cfg = THEMES[self.theme_idx]
        grid_cfg = GRID_CONFIGS[self.grid_idx]
        self.total_pairs = min(grid_cfg["pairs"], len(theme_cfg["items"]))
        self.pairs_found = 0
        self.moves_count = 0
        self.flipped_indices.clear()
        self.unflip_timer = 0.0
        self.particles.clear()
        self.is_victory = False
        self.completion.clear()
        self.completion_presented = False
        self.selected_card_index = 0

        selected_items = random.sample(theme_cfg["items"], self.total_pairs)
        deck_items = selected_items * 2
        random.shuffle(deck_items)

        self.cards.clear()
        for idx, item in enumerate(deck_items):
            self.cards.append(
                {
                    "id": item["id"],
                    "item": item,
                    "is_matched": False,
                    "is_revealed": False,
                    "flip_anim": 0.0,
                }
            )

    def _handle_card_click(self, idx: int) -> None:
        if self.is_victory or not 0 <= idx < len(self.cards):
            return
        card = self.cards[idx]
        if card["is_revealed"] or card["is_matched"]:
            return
        if self.unflip_timer > 0.0:
            return
        card["is_revealed"] = True
        self.sounds.play("flip")
        self.flipped_indices.append(idx)

        if len(self.flipped_indices) == 2:
            self.moves_count += 1
            idx1, idx2 = self.flipped_indices[0], self.flipped_indices[1]
            if self.cards[idx1]["id"] == self.cards[idx2]["id"]:
                self.cards[idx1]["is_matched"] = True
                self.cards[idx2]["is_matched"] = True
                self.pairs_found += 1
                self.sounds.play("match")
                try:
                    emit_activity_event("memory.pair_found", {"pairs": self.pairs_found})
                except Exception:
                    pass
                self._spawn_match_particles(idx1, idx2)
                self.flipped_indices.clear()
                if self.pairs_found >= self.total_pairs:
                    self.is_victory = True
                    self.completion_presented = False
                    self.sounds.play("win")
                    try:
                        emit_activity_event("memory.game_completed", {"moves": self.moves_count})
                    except Exception:
                        pass
            else:
                self.sounds.play("mismatch")
                self.unflip_timer = 0.9

    def _spawn_match_particles(self, idx1: int, idx2: int) -> None:
        _, _, card_rects = compute_grid_layout(
            GRID_CONFIGS[self.grid_idx], len(self.cards)
        )
        for cr in (card_rects[idx1], card_rects[idx2]):
            for _ in range(16):
                ang = random.uniform(0, 6.28)
                spd = random.uniform(2.0, 5.5)
                self.particles.append(
                    {
                        "x": cr.centerx,
                        "y": cr.centery,
                        "vx": math.cos(ang) * spd,
                        "vy": math.sin(ang) * spd,
                        "color": (254, 202, 87),
                        "size": random.uniform(4.0, 9.0),
                        "life": 1.0,
                        "decay": 0.03,
                    }
                )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def _update(self) -> None:
        if self.is_victory:
            return
        if self.unflip_timer > 0.0:
            self.unflip_timer -= 0.033
            if self.unflip_timer <= 0.0:
                self.unflip_timer = 0.0
                for idx in self.flipped_indices:
                    if not self.cards[idx]["is_matched"]:
                        self.cards[idx]["is_revealed"] = False
                self.flipped_indices.clear()

        for card in self.cards:
            target_flip = 1.0 if (card["is_revealed"] or card["is_matched"]) else 0.0
            diff = target_flip - card["flip_anim"]
            if abs(diff) > 0.01:
                card["flip_anim"] += diff * 0.28
            else:
                card["flip_anim"] = target_flip

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self._running = False
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._running = False
            return
        if event.type == pygame.VIDEORESIZE:
            self.screen = pygame.display.get_surface() or self.screen
            self.metrics = ChildUiMetrics.for_size(*self.screen.get_size())
            self.canvas = PygameReferenceCanvas(self.screen)
            self.completion_presented = False
            return
        if event.type == pygame.KEYDOWN:
            if self.is_victory:
                if event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_n):
                    self._start_new_game()
                return
            if event.key == pygame.K_n:
                self._start_new_game()
            elif event.key == pygame.K_t:
                self.theme_idx = (self.theme_idx + 1) % len(THEMES)
                self._start_new_game()
            elif event.key == pygame.K_g:
                self.grid_idx = (self.grid_idx + 1) % len(GRID_CONFIGS)
                self._start_new_game()
            elif event.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN):
                columns = GRID_CONFIGS[self.grid_idx]["cols"]
                step = {
                    pygame.K_LEFT: -1,
                    pygame.K_RIGHT: 1,
                    pygame.K_UP: -columns,
                    pygame.K_DOWN: columns,
                }[event.key]
                self._move_focus(step)
            elif event.key in (pygame.K_SPACE, pygame.K_RETURN):
                self._handle_card_click(self.selected_card_index)
            return
        if (event.type == pygame.MOUSEBUTTONUP and event.button == 1
                and not getattr(event, "touch", False)):
            self._handle_pointer(event.pos)
        elif event.type == pygame.FINGERDOWN:
            width, height = self.screen.get_size()
            self._handle_pointer((int(event.x * width), int(event.y * height)))

    def _move_focus(self, step: int) -> None:
        """Move through the current grid without focusing cleared pairs."""
        if not self.cards:
            return
        initial = self.selected_card_index
        for _ in range(len(self.cards)):
            self.selected_card_index = (self.selected_card_index + step) % len(self.cards)
            if not self.cards[self.selected_card_index]["is_matched"]:
                return
        # A vertical stride visits only one column; when that column has
        # already been cleared, find another remaining playable card.
        for distance in range(1, len(self.cards) + 1):
            index = (initial + distance) % len(self.cards)
            if not self.cards[index]["is_matched"]:
                self.selected_card_index = index
                return

    def _handle_pointer(self, raw_pos: tuple[int, int]) -> None:
        if not _is_safe_point(self.screen, raw_pos):
            return
        logical = self.canvas.pointer(raw_pos)
        if logical is None:
            return
        mx, my = logical

        if self.is_victory:
            if self.completion.primary_contains((int(mx), int(my))):
                self._start_new_game()
            return

        new_btn = pygame.Rect(REFERENCE_WIDTH - 170, 14, 150, 52)
        if new_btn.collidepoint(mx, my):
            self._start_new_game()
            return

        theme_btn = pygame.Rect(REFERENCE_WIDTH // 2 - 150, REFERENCE_HEIGHT - 52, 140, 44)
        if theme_btn.collidepoint(mx, my):
            self.theme_idx = (self.theme_idx + 1) % len(THEMES)
            self._start_new_game()
            return

        grid_btn = pygame.Rect(REFERENCE_WIDTH // 2 + 10, REFERENCE_HEIGHT - 52, 140, 44)
        if grid_btn.collidepoint(mx, my):
            self.grid_idx = (self.grid_idx + 1) % len(GRID_CONFIGS)
            self._start_new_game()
            return

        _, _, card_rects = compute_grid_layout(
            GRID_CONFIGS[self.grid_idx], len(self.cards)
        )
        for idx, rect in enumerate(card_rects):
            if rect.collidepoint(mx, my):
                self.selected_card_index = idx
                self._handle_card_click(idx)
                return

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------

    def _draw(self) -> None:
        if self.is_victory:
            if not self.completion_presented:
                self.completion.prepare(self.completion_content)
                self.completion.draw(self.canvas.surface)
                self.canvas.present(clear=THEMES[self.theme_idx]["bg"])
                pygame.display.flip()
                self.completion_presented = True
            return

        surviving: list[dict[str, Any]] = []
        for p in self.particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["life"] -= p["decay"]
            if p["life"] > 0:
                surviving.append(p)
        self.particles = surviving

        surf = self.canvas.surface
        surf.fill(THEMES[self.theme_idx]["bg"])
        theme_cfg = THEMES[self.theme_idx]
        grid_cfg = GRID_CONFIGS[self.grid_idx]
        card_w, card_h, card_rects = compute_grid_layout(grid_cfg, len(self.cards))

        for bx in range(30, REFERENCE_WIDTH, 80):
            for by in range(30, REFERENCE_HEIGHT, 80):
                pygame.draw.circle(surf, (226, 232, 240), (bx, by), 2)

        for idx, card in enumerate(self.cards):
            rect = card_rects[idx]
            flip = card["flip_anim"]
            cos_flip = abs(math.cos(flip * math.pi))
            cur_w = max(6, int(card_w * cos_flip))
            cur_rect = pygame.Rect(rect.centerx - cur_w // 2, rect.top, cur_w, card_h)
            pygame.draw.rect(surf, (203, 213, 225), cur_rect.move(3, 5), border_radius=16)

            is_front = flip >= 0.5
            if is_front:
                pygame.draw.rect(surf, (255, 255, 255), cur_rect, border_radius=16)
                border_col = (34, 197, 94) if card["is_matched"] else (203, 213, 225)
                border_w = 4 if card["is_matched"] else 2
                pygame.draw.rect(surf, border_col, cur_rect, width=border_w, border_radius=16)
                if cos_flip > 0.35:
                    item = card["item"]
                    emblem_r = int(min(cur_w, card_h) * 0.34)
                    emblem_cy = cur_rect.top + int(card_h * 0.42)
                    pygame.draw.circle(surf, item["color"], (cur_rect.centerx, emblem_cy), emblem_r)
                    pygame.draw.circle(surf, (30, 41, 59), (cur_rect.centerx, emblem_cy), emblem_r, 2)
                    draw_card_illustration(
                        surf,
                        item["id"],
                        cur_rect.centerx,
                        emblem_cy,
                        int(emblem_r * 1.5),
                    )
                    label = (
                        self.resources.text(f"item.{item['id']}")
                        if self.resources is not None
                        else "★"
                    )
                    lbl_text = display_text(label)
                    lbl_surf = self.typography.render(
                        lbl_text,
                        FontRole.DISPLAY,
                        max(12, min(16, card_h // 12)),
                        (30, 41, 59),
                    )
                    surf.blit(
                        lbl_surf,
                        (
                            cur_rect.centerx - lbl_surf.get_width() // 2,
                            cur_rect.bottom - lbl_surf.get_height() - 8,
                        ),
                    )
            else:
                pygame.draw.rect(surf, theme_cfg["card_back"], cur_rect, border_radius=16)
                pygame.draw.rect(surf, (255, 255, 255), cur_rect, width=3, border_radius=16)
                if cos_flip > 0.35:
                    back_r = int(min(cur_w, card_h) * 0.26)
                    pygame.draw.circle(surf, (255, 255, 255), cur_rect.center, back_r, 3)
                    pygame.draw.circle(
                        surf, theme_cfg["back_accent"], cur_rect.center, back_r - 4
                    )
                    draw_card_illustration(
                        surf,
                        "star",
                        cur_rect.centerx,
                        cur_rect.centery,
                        int(back_r * 1.2),
                    )

        if card_rects:
            focused = card_rects[self.selected_card_index % len(card_rects)].inflate(8, 8)
            pygame.draw.rect(surf, (15, 23, 42), focused, width=6, border_radius=20)
            pygame.draw.rect(surf, (56, 189, 248), focused, width=3, border_radius=20)

        for p in self.particles:
            cur_sz = max(2.0, p["size"] * max(0.0, min(1.0, p["life"])))
            pygame.draw.circle(surf, p["color"], (int(p["x"]), int(p["y"])), int(cur_sz))

        # Top star pill
        star_pill = pygame.Rect(80, 14, 150, 52)
        pygame.draw.rect(surf, (255, 255, 255), star_pill, border_radius=18)
        pygame.draw.rect(surf, (180, 83, 9), star_pill, width=3, border_radius=18)
        draw_card_illustration(surf, "star", star_pill.left + 28, star_pill.centery, 34)
        s_txt = self.typography.render(
            f"{self.pairs_found}/{self.total_pairs}", FontRole.DISPLAY, 24, (180, 83, 9)
        )
        surf.blit(
            s_txt,
            (star_pill.left + 54, star_pill.centery - s_txt.get_height() // 2),
        )

        # Top-right new button
        new_btn = pygame.Rect(REFERENCE_WIDTH - 170, 14, 150, 52)
        pygame.draw.rect(surf, (51, 65, 85), new_btn, border_radius=18)
        pygame.draw.rect(surf, (30, 41, 59), new_btn, width=2, border_radius=18)
        new_label = (
            self.resources.text("btn.new_game")
            if self.resources is not None
            else "🔄"
        )
        new_txt = self.typography.render(new_label, FontRole.DISPLAY, 18, (255, 255, 255))
        surf.blit(
            new_txt,
            (new_btn.centerx - new_txt.get_width() // 2, new_btn.centery - new_txt.get_height() // 2),
        )

        # Bottom theme button
        theme_btn = pygame.Rect(REFERENCE_WIDTH // 2 - 150, REFERENCE_HEIGHT - 52, 140, 44)
        pygame.draw.rect(surf, (51, 65, 85), theme_btn, border_radius=12)
        pygame.draw.rect(surf, (30, 41, 59), theme_btn, width=2, border_radius=12)
        t_name = (
            self.resources.text(f"theme.{theme_cfg['id']}")
            if self.resources is not None
            else "🎨"
        )
        theme_lbl = self.typography.render(t_name, FontRole.BODY, 15, (255, 255, 255))
        surf.blit(
            theme_lbl,
            (theme_btn.centerx - theme_lbl.get_width() // 2, theme_btn.centery - theme_lbl.get_height() // 2),
        )

        # Bottom grid button
        grid_btn = pygame.Rect(REFERENCE_WIDTH // 2 + 10, REFERENCE_HEIGHT - 52, 140, 44)
        pygame.draw.rect(surf, (51, 65, 85), grid_btn, border_radius=12)
        pygame.draw.rect(surf, (30, 41, 59), grid_btn, width=2, border_radius=12)
        grid_lbl = self.typography.render("📐 " + grid_cfg["label"], FontRole.BODY, 15, (255, 255, 255))
        surf.blit(
            grid_lbl,
            (grid_btn.centerx - grid_lbl.get_width() // 2, grid_btn.centery - grid_lbl.get_height() // 2),
        )

        self.canvas.present(clear=theme_cfg["bg"])
        pygame.display.flip()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _persist_progress(self) -> None:
        if self.storage is None:
            return
        try:
            self.storage.kv_set(
                STORAGE_KEY,
                {
                    "theme_idx": self.theme_idx,
                    "grid_idx": self.grid_idx,
                    "timestamp": time.time(),
                },
            )
        except Exception:
            pass
