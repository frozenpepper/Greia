"""Storie della Mia Voce — pre-reader rendering layer.

The renderer draws four states driven by the lifecycle layer:
  * SCENE_PICKER:  four big colourful scene cards in a row
  * RECORDING:     scene-tinted background + huge red mic button
  * REPLAY:        the scene with PLAY / RE-RECORD / NEXT SCENE
  * LIBRARY:       list of saved stories with thumbnails
  * MIC_REQUIRED:  explain-the-problem card, no controls

The renderer is stateful but stateless about Activity semantics;
the lifecycle layer owns the model and passes text + per-frame
values. All UI is large, all icons are obvious, no instruction
depends on reading — see PRE_READER_UX.md.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Final

import pygame

from voice_content import (
    REFERENCE_HEIGHT,
    REFERENCE_WIDTH,
    SCENES,
    SCENE_CARDS_LEFT,
    SCENE_CARDS_TOP,
    SCENE_CARD_GAP,
    SCENE_CARD_SIZE,
    SCENE_IDS,
    SceneId,
)


PALETTE_TOP_Y: Final = 480
WINDOW_PADDING: Final = 28
BACKDROP_COLOR: Final = (252, 244, 220)
PLAYFIELD_COLOR: Final = (255, 252, 240)
TILE_BORDER: Final = (180, 83, 9)
TILE_BG: Final = (255, 255, 255)
WHITE: Final = (255, 255, 255)
DARK_TEXT: Final = (45, 25, 15)
MIC_RED: Final = (239, 68, 68)
MIC_DARK: Final = (127, 29, 29)
BUTTON_BG: Final = (255, 255, 255)
BUTTON_BORDER: Final = (148, 163, 184)
PLAY_GREEN: Final = (34, 197, 94)
PLAY_DARK: Final = (22, 101, 52)


@dataclass
class VoiceRenderer:
    surface: pygame.Surface
    backdrop_cache: pygame.Surface
    scene_cards: list[pygame.Rect]
    mic_btn_rect: pygame.Rect
    stop_btn_rect: pygame.Rect
    save_btn_rect: pygame.Rect
    library_btn_rect: pygame.Rect
    back_btn_rect: pygame.Rect
    next_btn_rect: pygame.Rect
    replay_btn_rect: pygame.Rect
    rerecord_btn_rect: pygame.Rect
    close_btn_rect: pygame.Rect

    @classmethod
    def build(cls, surface: pygame.Surface) -> "VoiceRenderer":
        # Four scene cards in a row
        scene_cards: list[pygame.Rect] = []
        for i, _ in enumerate(SCENES):
            x = SCENE_CARDS_LEFT + i * (SCENE_CARD_SIZE + SCENE_CARD_GAP)
            y = SCENE_CARDS_TOP
            scene_cards.append(
                pygame.Rect(x, y, SCENE_CARD_SIZE, SCENE_CARD_SIZE)
            )
        # Mic button (huge, dead center)
        mic = pygame.Rect(0, 0, 200, 200)
        mic.center = (REFERENCE_WIDTH // 2, REFERENCE_HEIGHT // 2)
        # Stop button (during recording, same area)
        stop = mic.copy()
        # Library + back + save buttons in the top bar
        library = pygame.Rect(80, 16, 160, 56)
        back = pygame.Rect(REFERENCE_WIDTH - 256, 16, 88, 44)
        next_btn = pygame.Rect(REFERENCE_WIDTH - 256, REFERENCE_HEIGHT - 84, 220, 64)
        save = pygame.Rect(REFERENCE_WIDTH // 2 - 110, REFERENCE_HEIGHT - 84, 220, 64)
        replay = pygame.Rect(REFERENCE_WIDTH // 2 - 200, REFERENCE_HEIGHT - 84, 120, 64)
        rerecord = pygame.Rect(REFERENCE_WIDTH // 2 + 80, REFERENCE_HEIGHT - 84, 120, 64)
        close = pygame.Rect(REFERENCE_WIDTH - 96, 16, 80, 44)
        return cls(
            surface=surface,
            backdrop_cache=cls._render_backdrop(),
            scene_cards=scene_cards,
            mic_btn_rect=mic,
            stop_btn_rect=stop,
            save_btn_rect=save,
            library_btn_rect=library,
            back_btn_rect=back,
            next_btn_rect=next_btn,
            replay_btn_rect=replay,
            rerecord_btn_rect=rerecord,
            close_btn_rect=close,
        )

    @staticmethod
    def _render_backdrop() -> pygame.Surface:
        surf = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT))
        for y in range(REFERENCE_HEIGHT):
            ratio = y / REFERENCE_HEIGHT
            r = int(252 * (1 - ratio) + 244 * ratio)
            g = int(244 * (1 - ratio) + 232 * ratio)
            b = int(220 * (1 - ratio) + 200 * ratio)
            pygame.draw.rect(surf, (r, g, b), (0, y, REFERENCE_WIDTH, 1))
        return surf

    # ------------------------------------------------------------------
    # Public draw entry
    # ------------------------------------------------------------------

    def draw_scene_picker(self, text_fn) -> None:
        surf = self.surface
        surf.blit(self.backdrop_cache, (0, 0))
        # Top bar
        library_btn = self.library_btn_rect
        pygame.draw.rect(surf, BUTTON_BG, library_btn, border_radius=20)
        pygame.draw.rect(surf, BUTTON_BORDER, library_btn, width=3, border_radius=20)
        library_label = text_fn("LE MIE STORIE", DARK_TEXT)
        surf.blit(
            library_label,
            library_label.get_rect(center=library_btn.center),
        )
        # Title
        title = text_fn("SCEGLI UNA SCENA!", DARK_TEXT)
        surf.blit(
            title, title.get_rect(center=(REFERENCE_WIDTH // 2, 100))
        )
        subtitle = text_fn("QUATRO SCHERMATE DA RIEMPIRE CON LA TUA VOCE", DARK_TEXT)
        surf.blit(
            subtitle, subtitle.get_rect(center=(REFERENCE_WIDTH // 2, 150))
        )
        # Scene cards
        for i, scene in enumerate(SCENES):
            rect = self.scene_cards[i]
            self._draw_scene_card(surf, scene, rect, text_fn)

    def _draw_scene_card(
        self, surf: pygame.Surface, scene, rect: pygame.Rect, text_fn,
    ) -> None:
        # Card body (rounded square tinted with the scene's primary colour)
        pygame.draw.rect(surf, scene.primary_color, rect, border_radius=24)
        pygame.draw.rect(surf, TILE_BORDER, rect, width=4, border_radius=24)
        # Inner area where the scene icon lives
        inner = rect.inflate(-24, -24)
        pygame.draw.rect(surf, WHITE, inner, border_radius=18)
        # Two stylized shape layers (a sky band + a ground band) so
        # the child has a recognizable visual without bitmap art.
        band_h = inner.height // 2
        sky = pygame.Rect(inner.left, inner.top, inner.width, band_h)
        ground = pygame.Rect(inner.left, inner.top + band_h, inner.width, band_h)
        pygame.draw.rect(surf, scene.secondary_color, sky, border_radius=18,
                           border_bottom_left_radius=0, border_bottom_right_radius=0)
        pygame.draw.rect(surf, (255, 252, 240), ground, border_radius=18,
                           border_top_left_radius=0, border_top_right_radius=0)
        # A few simple shapes (sun/cloud/tree) depending on scene id so
        # the child has an unambiguous visual cue without text.
        cx = inner.centerx
        cy = inner.centery
        if scene.scene_id == SceneId.FOREST:
            for tx, th in ((cx - 30, 22), (cx, 32), (cx + 30, 24)):
                pygame.draw.rect(surf, (120, 70, 30), (tx - 4, cy + 5, 8, th))
                pygame.draw.circle(surf, (34, 197, 94), (tx, cy - 2), 18)
        elif scene.scene_id == SceneId.SEA:
            for i in range(4):
                yy = cy - 10 + i * 8
                pygame.draw.arc(
                    surf, (12, 74, 110),
                    pygame.Rect(cx - 40, yy, 80, 12),
                    0, math.pi, 2,
                )
        elif scene.scene_id == SceneId.SKY:
            pygame.draw.circle(surf, (250, 204, 21), (cx, cy - 4), 16)
            for ang in (0, 60, 120, 180, 240, 300):
                rad = math.radians(ang)
                bx = cx + math.cos(rad) * 22
                by = cy - 4 + math.sin(rad) * 22
                pygame.draw.line(surf, (250, 204, 21), (cx, cy - 4), (int(bx), int(by)), 3)
            for wx, wy in ((cx - 50, cy + 14), (cx + 30, cy + 16)):
                pygame.draw.circle(surf, WHITE, (wx, wy), 10)
                pygame.draw.circle(surf, WHITE, (wx + 14, wy + 2), 12)
        else:  # FRIENDS
            for fx in (cx - 30, cx, cx + 30):
                pygame.draw.circle(surf, (251, 146, 60), (fx, cy + 4), 14)
                pygame.draw.circle(surf, (255, 255, 255), (fx - 4, cy - 2), 3)
                pygame.draw.circle(surf, (255, 255, 255), (fx + 4, cy - 2), 3)
        # Label
        label = text_fn(scene.label_key.upper(), DARK_TEXT)
        surf.blit(
            label, label.get_rect(center=(rect.centerx, rect.bottom + 24))
        )

    def draw_recording(
        self, scene, time_remaining: float, live_volume: float, text_fn,
    ) -> None:
        surf = self.surface
        # Scene-tinted background
        surf.fill(BACKDROP_COLOR)
        # Big top band in the scene's primary colour
        pygame.draw.rect(surf, scene.primary_color, (0, 0, REFERENCE_WIDTH, 220))
        pygame.draw.rect(surf, scene.secondary_color, (0, 220, REFERENCE_WIDTH, 12))
        # Title
        title = text_fn(scene.label_key.upper(), WHITE)
        surf.blit(title, title.get_rect(center=(REFERENCE_WIDTH // 2, 100)))
        # Mic button (huge red disc) with pulsing aura
        pulse = int(4 + abs(math.sin(time_remaining * 6)) * 6)
        aura = pygame.Surface(
            (200 + pulse * 4, 200 + pulse * 4), pygame.SRCALPHA
        )
        pygame.draw.circle(
            aura, (239, 68, 68, 80),
            (aura.get_width() // 2, aura.get_height() // 2),
            100 + pulse,
        )
        surf.blit(
            aura,
            (self.mic_btn_rect.centerx - aura.get_width() // 2,
             self.mic_btn_rect.centery - aura.get_height() // 2),
        )
        # Mic disc
        pygame.draw.circle(
            surf, MIC_RED, self.mic_btn_rect.center, 90
        )
        pygame.draw.circle(
            surf, MIC_DARK, self.mic_btn_rect.center, 90, 6
        )
        # Mic icon: a small pill + base
        mx, my = self.mic_btn_rect.center
        pygame.draw.rect(surf, WHITE, (mx - 18, my - 30, 36, 50), border_radius=18)
        pygame.draw.arc(
            surf, WHITE,
            pygame.Rect(mx - 28, my - 18, 56, 50),
            0, math.pi, 4,
        )
        pygame.draw.rect(surf, WHITE, (mx - 3, my + 18, 6, 20))
        pygame.draw.rect(surf, WHITE, (mx - 14, my + 36, 28, 5), border_radius=2)
        # Live level
        if live_volume > 0:
            bar_w = int(live_volume * 240)
            pygame.draw.rect(surf, (255, 255, 255), (REFERENCE_WIDTH // 2 - 120, 460, 240, 14), border_radius=7)
            pygame.draw.rect(surf, (34, 197, 94), (REFERENCE_WIDTH // 2 - 120, 460, bar_w, 14), border_radius=7)
        # Time remaining
        time_label = text_fn(f"{time_remaining:4.1f}s", WHITE)
        surf.blit(time_label, time_label.get_rect(center=(REFERENCE_WIDTH // 2, 430)))
        # Top right "indietro" pill
        self._draw_back_pill(surf, text_fn)
        # Bottom STOP label
        stop_label = text_fn("STOP", WHITE)
        surf.blit(
            stop_label, stop_label.get_rect(center=(mx, my + 130))
        )

    def draw_replay(
        self, scene, duration: float, text_fn, has_recording: bool = True,
    ) -> None:
        surf = self.surface
        surf.fill(BACKDROP_COLOR)
        pygame.draw.rect(surf, scene.primary_color, (0, 0, REFERENCE_WIDTH, 220))
        pygame.draw.rect(surf, scene.secondary_color, (0, 220, REFERENCE_WIDTH, 12))
        title = text_fn(scene.label_key.upper(), WHITE)
        surf.blit(title, title.get_rect(center=(REFERENCE_WIDTH // 2, 100)))
        # Big status area
        status = text_fn(
            "BELLA!" if has_recording else "RIPROVA!",
            DARK_TEXT,
        )
        surf.blit(status, status.get_rect(center=(REFERENCE_WIDTH // 2, 320)))
        dur = text_fn(f"{duration:4.1f}s", DARK_TEXT)
        surf.blit(dur, dur.get_rect(center=(REFERENCE_WIDTH // 2, 360)))
        # Buttons
        self._draw_tactile_button(
            surf, self.replay_btn_rect, "▶", text_fn,
            base=(PLAY_GREEN, PLAY_DARK),
        )
        self._draw_tactile_button(
            surf, self.rerecord_btn_rect, "↺", text_fn,
            base=((180, 83, 9), (120, 53, 9)),
        )
        # "PROSSIMA SCENA" button (top right)
        self._draw_back_pill(surf, text_fn)
        next_label = text_fn("PROSSIMA SCENA →", DARK_TEXT)
        surf.blit(next_label, next_label.get_rect(center=(REFERENCE_WIDTH // 2, REFERENCE_HEIGHT - 50)))

    def draw_saved(self, story, text_fn) -> None:
        surf = self.surface
        surf.fill(BACKDROP_COLOR)
        title = text_fn("STORIA SALVATA!", (22, 101, 52))
        surf.blit(title, title.get_rect(center=(REFERENCE_WIDTH // 2, 80)))
        # Four scene thumbnails
        for i, scene in enumerate(SCENES):
            x = 100 + i * 210
            y = 140
            rect = pygame.Rect(x, y, 180, 180)
            self._draw_scene_card(surf, scene, rect, text_fn)
            present = scene.scene_id in story.scene_recordings
            if present:
                dur = story.scene_durations.get(scene.scene_id, 0.0)
                tag = text_fn(f"{dur:3.1f}s", (22, 101, 52))
                surf.blit(
                    tag, tag.get_rect(center=(rect.centerx, rect.bottom + 38))
                )
        # Library + New buttons
        lib = pygame.Rect(140, 460, 280, 80)
        new = pygame.Rect(REFERENCE_WIDTH - 420, 460, 280, 80)
        self._draw_tactile_button(surf, lib, "LE MIE STORIE", text_fn,
                                  base=((56, 189, 248), (12, 74, 110)))
        self._draw_tactile_button(surf, new, "UN'ALTRA STORIA", text_fn,
                                  base=((34, 197, 94), (22, 101, 52)))

    def draw_library(self, library, text_fn) -> None:
        surf = self.surface
        surf.fill(BACKDROP_COLOR)
        title = text_fn("LE MIE STORIE", DARK_TEXT)
        surf.blit(title, title.get_rect(center=(REFERENCE_WIDTH // 2, 60)))
        if library.count == 0:
            empty = text_fn("ANCORA NESSUNA STORIA!", (148, 163, 184))
            surf.blit(empty, empty.get_rect(center=(REFERENCE_WIDTH // 2, 280)))
        else:
            # 2 columns × 2 rows
            for i, story in enumerate(library.stories[:6]):
                col, row = i % 2, i // 2
                x = 90 + col * 440
                y = 120 + row * 200
                rect = pygame.Rect(x, y, 380, 170)
                pygame.draw.rect(surf, WHITE, rect, border_radius=18)
                pygame.draw.rect(surf, BUTTON_BORDER, rect, width=2, border_radius=18)
                # Four scene dots
                for j, scene in enumerate(SCENES):
                    cx_dot = x + 60 + j * 32
                    pygame.draw.circle(
                        surf,
                        scene.primary_color if scene.scene_id in story.scene_recordings else (200, 200, 200),
                        (cx_dot, y + 30), 12,
                    )
                dur_label = text_fn(
                    f"{sum(story.scene_durations.values()):3.1f}s", DARK_TEXT
                )
                surf.blit(dur_label, dur_label.get_rect(center=(x + 280, y + 30)))
                # Play button
                play = pygame.Rect(x + 240, y + 70, 120, 60)
                self._draw_tactile_button(
                    surf, play, "▶", text_fn,
                    base=((PLAY_GREEN, PLAY_DARK)),
                )
                # Delete button
                delete = pygame.Rect(x + 60, y + 100, 80, 50)
                self._draw_tactile_button(
                    surf, delete, "X", text_fn,
                    base=((MIC_RED, MIC_DARK)),
                )
        # Back pill
        self._draw_back_pill(surf, text_fn)
        # New story button
        new = pygame.Rect(REFERENCE_WIDTH - 240, 510, 200, 70)
        self._draw_tactile_button(surf, new, "+ NUOVA", text_fn,
                                  base=((34, 197, 94), (22, 101, 52)))

    def draw_mic_required(self, text_fn) -> None:
        surf = self.surface
        surf.fill(BACKDROP_COLOR)
        title = text_fn("SERVE IL MICROFONO", (180, 83, 9))
        surf.blit(title, title.get_rect(center=(REFERENCE_WIDTH // 2, 200)))
        # Big mic icon
        pygame.draw.circle(surf, (200, 200, 200), (REFERENCE_WIDTH // 2, 320), 60)
        pygame.draw.rect(
            surf, (200, 200, 200),
            pygame.Rect(REFERENCE_WIDTH // 2 - 12, 290, 24, 40),
            border_radius=12,
        )
        body = text_fn(
            "PER REGISTRARE LA TUA VOCE, CHIEDI AD UN ADULTO DI ACCENDERE IL MICROFONO IN IMPOSTAZIONI.",
            (148, 163, 184),
        )
        # Word wrap (very simple)
        words = body.split(" ")
        lines: list[str] = []
        cur = ""
        for w in words:
            trial = (cur + " " + w).strip()
            if len(trial) > 50 and cur:
                lines.append(cur)
                cur = w
            else:
                cur = trial
        if cur:
            lines.append(cur)
        for i, line in enumerate(lines[:5]):
            surf.blit(
                text_fn(line, (148, 163, 184)),
                text_fn(line, (148, 163, 184)).get_rect(
                    center=(REFERENCE_WIDTH // 2, 420 + i * 26)
                ),
            )
        # Back to launcher
        back = pygame.Rect(REFERENCE_WIDTH // 2 - 120, REFERENCE_HEIGHT - 90, 240, 64)
        self._draw_tactile_button(surf, back, "← INDIETRO", text_fn,
                                  base=((148, 163, 184), (71, 85, 105)))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _draw_back_pill(self, surf: pygame.Surface, text_fn) -> None:
        pygame.draw.rect(surf, BUTTON_BG, self.back_btn_rect, border_radius=20)
        pygame.draw.rect(surf, BUTTON_BORDER, self.back_btn_rect, width=3, border_radius=20)
        surf.blit(
            text_fn("←", DARK_TEXT),
            text_fn("←", DARK_TEXT).get_rect(center=self.back_btn_rect.center),
        )

    def _draw_tactile_button(
        self, surf: pygame.Surface, rect: pygame.Rect, glyph: str,
        text_fn, base: tuple[tuple[int, int, int], tuple[int, int, int]],
    ) -> None:
        primary, dark = base
        shadow = rect.move(0, 4)
        pygame.draw.rect(surf, (180, 190, 210), shadow, border_radius=rect.height // 2)
        pygame.draw.rect(surf, primary, rect, border_radius=rect.height // 2)
        pygame.draw.rect(surf, dark, rect, width=3, border_radius=rect.height // 2)
        surf.blit(
            text_fn(glyph, WHITE),
            text_fn(glyph, WHITE).get_rect(center=rect.center),
        )
