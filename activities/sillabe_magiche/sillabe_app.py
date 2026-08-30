from __future__ import annotations

"""Lifecycle coordinator for Sillabe Magiche — screen/canvas/metrics/typography, model, audio, renderer.

Owns the event loop, safe-input gating, audio state machines, and the
READY contract (publish exactly once after first flip in the same loop
iteration). Resize invalidates metrics/canvas; no per-frame decode/scale.
"""

import random
import time

import pygame

from greia_platform.activity_api import activity_stop_requested, emit_activity_event, mark_activity_ready
from greia_platform.activity_ui import ChildUiMetrics
from greia_platform.child_text import display_text
from greia_platform.pygame_canvas import PygameReferenceCanvas, activity_viewport_for_surface
from greia_platform.typography import FontRole

if __package__:
    from .sillabe_audio import SoundManager
    from .sillabe_content import (
        BG_SKY_BOTTOM,
        BG_SKY_TOP,
        CARD_BG,
        CARD_BORDER,
        CONSONANTS_IT,
        CORAL,
        DARK_TEXT,
        GOLD,
        GOLD_BORDER,
        LIGHT_TEXT,
        MINT_GREEN,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        SHADOW_COLOR,
        SKY_BLUE,
        STORAGE_KEY,
        VOWELS_IT,
        WORDS_DATA_EN,
        WORDS_DATA_IT,
    )
    from .sillabe_model import SillabeSession
    from .sillabe_renderer import FloatingOrb, LeoCompanion, Particle, SillabeRenderer, SyllableCard, WordTile
else:
    from sillabe_audio import SoundManager
    from sillabe_content import (
        BG_SKY_BOTTOM,
        BG_SKY_TOP,
        CARD_BG,
        CARD_BORDER,
        CONSONANTS_IT,
        CORAL,
        DARK_TEXT,
        GOLD,
        GOLD_BORDER,
        LIGHT_TEXT,
        MINT_GREEN,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        SHADOW_COLOR,
        SKY_BLUE,
        STORAGE_KEY,
        VOWELS_IT,
        WORDS_DATA_EN,
        WORDS_DATA_IT,
    )
    from sillabe_model import SillabeSession
    from sillabe_renderer import FloatingOrb, LeoCompanion, Particle, SillabeRenderer, SyllableCard, WordTile


def _is_safe_point(surface: pygame.Surface, position: tuple[int, int]) -> bool:
    vp = activity_viewport_for_surface(surface)
    x, y = position
    if not (0 <= x < vp.surface.width and 0 <= y < vp.surface.height):
        return False
    for protected in vp.protected_regions:
        if protected.x <= x < protected.right and protected.y <= y < protected.bottom:
            return False
    return True


class SillabeApp:
    """Coordinate Sillabe Magiche lifecycle without owning domain or rendering details.

    Dependencies are injected so the thin bootstrap can supply Greia context
    (screen/canvas/metrics/typography/resources/locale/theme/storage) while
    the session owns progression invariants and the renderer owns presentation
    caches. The app only sequences input → model → audio → renderer → present.
    """

    def __init__(
        self,
        screen: pygame.Surface,
        canvas: PygameReferenceCanvas,
        metrics: ChildUiMetrics,
        typography,
        resources,
        active_locale: str,
        theme,
        storage,
    ) -> None:
        self._screen = screen
        self._canvas = canvas
        self._metrics = metrics
        self._typography = typography
        self._resources = resources
        self._active_locale = active_locale
        self._theme = theme
        self._storage = storage

        self._sounds = SoundManager()
        self._renderer = SillabeRenderer(typography)

        words_pool = WORDS_DATA_IT if active_locale == "it" else WORDS_DATA_EN
        self._session = SillabeSession(
            words_pool=words_pool,
            consonants_pool=list(CONSONANTS_IT),
            vowels_pool=list(VOWELS_IT),
        )
        # Load persistent progression
        if storage is not None:
            try:
                saved = storage.kv_get(STORAGE_KEY, {})
                self._session.load_progress(saved)
            except Exception:
                pass

        # Geometry (reference space)
        self._tabs = [
            ("explorer", "📖 " + ("Sillabario" if active_locale == "it" else "Syllabary"), pygame.Rect(180, 16, 175, 58)),
            ("catcher", "🎯 " + ("Acchiappa" if active_locale == "it" else "Catch"), pygame.Rect(370, 16, 175, 58)),
            ("builder", "🧩 " + ("Crea Parole" if active_locale == "it" else "Words"), pygame.Rect(560, 16, 175, 58)),
        ]
        self._audio_btn_rect = pygame.Rect(755, 14, 68, 62)
        self._star_jar_rect = pygame.Rect(835, 14, 130, 62)
        self._btn_whole_word_rect = pygame.Rect(385, 208, 110, 58)
        self._btn_split_syllables_rect = pygame.Rect(525, 208, 110, 58)

        self._mascot = LeoCompanion(935, 480)
        self._particles: list[Particle] = []

        # Station 1
        self._cards_station1: list[SyllableCard] = []
        self._refresh_station1_cards()

        # Station 2
        self._catcher_orbs: list[FloatingOrb] = []
        self._start_catcher_round(play_audio=False)

        # Station 3
        self._word_tiles: list[WordTile] = []
        self._start_word_round(play_audio=False)

        self._initial_prompt_timer = 0.45
        self._running = True
        self._ready_published = False
        self._virtual_pointer = (512.0, 300.0)
        self._pointer_down = False

    # ------------------------------------------------------------------ #
    # Persistence helper
    # ------------------------------------------------------------------ #
    def _save_progress(self) -> None:
        if self._storage is None:
            return
        try:
            self._storage.kv_set(STORAGE_KEY, self._session.save_progress())
        except Exception:
            pass

    def _safe_emit(self, ev_id: str, ikey: str, payload: object = None) -> None:
        try:
            emit_activity_event(ev_id, idempotency_key=ikey, payload=payload)
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    # Station factories (presentation lists derived from model logical state)
    # ------------------------------------------------------------------ #
    def _refresh_station1_cards(self) -> None:
        self._cards_station1.clear()
        base_x = 230
        card_w = 118
        gap = 20
        syllables = self._session.explorer_syllables()
        for i, syl in enumerate(syllables):
            cx = base_x + i * (card_w + gap)
            cy = 280
            self._cards_station1.append(SyllableCard(syl, cx, cy, w=card_w, h=136, color_idx=i))

    def _start_catcher_round(self, play_audio: bool = True) -> None:
        target, orb_syls = self._session.start_catcher_round()
        # Presentation placement — keep exact original slots/offsets
        slots = [
            (240, 230),
            (430, 200),
            (620, 230),
            (800, 210),
            (320, 390),
            (530, 410),
            (730, 390),
        ]
        # Use a fresh shuffle via session rng for determinism
        try:
            self._session.rng.shuffle(slots)  # type: ignore[attr-defined]
        except Exception:
            random.shuffle(slots)
        self._catcher_orbs.clear()
        for i, s in enumerate(orb_syls):
            sx, sy = slots[i % len(slots)]
            # Keep original jitter bounds
            jx = self._session.rng.uniform(-15, 15) if hasattr(self._session.rng, "uniform") else random.uniform(-15, 15)  # type: ignore[union-attr]
            jy = self._session.rng.uniform(-10, 10) if hasattr(self._session.rng, "uniform") else random.uniform(-10, 10)  # type: ignore[union-attr]
            self._catcher_orbs.append(FloatingOrb(s, sx + jx, sy + jy, is_target=(s == target), color_idx=i))
        if play_audio:
            self._sounds.play_prompt(target, self._active_locale)

    def _start_word_round(self, play_audio: bool = True) -> None:
        word_tuple, choices = self._session.start_word_round()
        # word_tuple already synced into session fields
        self._word_tiles.clear()
        base_x = 240
        tile_w = 120
        gap = 26
        for i, s in enumerate(choices):
            tx = base_x + i * (tile_w + gap)
            ty = 440
            self._word_tiles.append(WordTile(s, tx, ty, w=tile_w, h=98, color_idx=i))
        if play_audio:
            self._sounds.play_word(self._session.cur_stem, self._active_locale)

    # ------------------------------------------------------------------ #
    # Main loop
    # ------------------------------------------------------------------ #
    def run(self) -> int:
        clock = pygame.time.Clock()

        while self._running and not activity_stop_requested():
            dt = clock.tick(60) / 1000.0

            if self._initial_prompt_timer > 0:
                self._initial_prompt_timer -= dt
                if self._initial_prompt_timer <= 0:
                    self._sounds.play_consonant(self._session.active_consonant, self._active_locale)

            # Audio state machines (timers owned by session logical state but driven here)
            if self._session.catcher_state == "praise_pending":
                self._session.catcher_timer -= dt
                if self._session.catcher_timer <= 0:
                    self._sounds.play_praise(self._active_locale)
                    self._session.catcher_state = "next_round_pending"
                    self._session.catcher_timer = 1.15
            elif self._session.catcher_state == "next_round_pending":
                self._session.catcher_timer -= dt
                if self._session.catcher_timer <= 0:
                    self._start_catcher_round(play_audio=True)

            if self._session.syllable_speech_step == 1:
                self._session.syllable_speech_timer -= dt
                if self._session.syllable_speech_timer <= 0:
                    self._sounds.play_syllable(self._session.cur_s2, self._active_locale)
                    self._session.syllable_speech_step = 0

            if self._session.word_completion_step == 1:
                self._session.word_completion_timer -= dt
                if self._session.word_completion_timer <= 0:
                    self._sounds.play_word(self._session.cur_stem, self._active_locale)
                    self._session.word_completion_step = 2
                    self._session.word_completion_timer = 0.90
            elif self._session.word_completion_step == 2:
                self._session.word_completion_timer -= dt
                if self._session.word_completion_timer <= 0:
                    self._sounds.play_praise(self._active_locale)
                    self._session.word_completion_step = 3
                    self._session.word_completion_timer = 1.40
            elif self._session.word_completion_step == 3:
                self._session.word_completion_timer -= dt
                if self._session.word_completion_timer <= 0:
                    self._session.word_completion_step = 0
                    self._session.word_index += 1
                    self._start_word_round(play_audio=True)

            # Events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self._running = False
                    elif event.key == pygame.K_SPACE:
                        if self._session.current_mode == "explorer":
                            self._sounds.play_consonant(self._session.active_consonant, self._active_locale)
                        elif self._session.current_mode == "catcher":
                            self._sounds.play_prompt(self._session.target_syl, self._active_locale)
                        elif self._session.current_mode == "builder":
                            self._sounds.play_word(self._session.cur_stem, self._active_locale)
                elif event.type == pygame.VIDEORESIZE:
                    self._screen = pygame.display.get_surface() or self._screen
                    self._metrics = ChildUiMetrics.for_size(*self._screen.get_size())
                    self._canvas = PygameReferenceCanvas(self._screen)
                    self._renderer.invalidate()
                elif event.type == pygame.MOUSEMOTION:
                    logical = self._canvas.pointer(event.pos)
                    if logical is not None:
                        self._virtual_pointer = logical
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    self._pointer_down = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self._pointer_down = True
                    logical = self._canvas.pointer(event.pos)
                    if logical is None:
                        continue
                    lx, ly = logical
                    if not _is_safe_point(self._screen, event.pos):
                        continue

                    # 1. Top Mode Tabs
                    mode_changed = False
                    for m_id, _m_label, r in self._tabs:
                        if r.collidepoint(lx, ly) and self._session.current_mode != m_id:
                            self._session.set_mode(m_id)
                            mode_changed = True
                            if self._session.current_mode == "explorer":
                                self._sounds.play_consonant(self._session.active_consonant, self._active_locale)
                            elif self._session.current_mode == "catcher":
                                self._start_catcher_round(play_audio=True)
                            elif self._session.current_mode == "builder":
                                self._start_word_round(play_audio=True)
                            break
                    if mode_changed:
                        continue

                    # 2. Main Audio Replay Button
                    if self._audio_btn_rect.collidepoint(lx, ly):
                        if self._session.current_mode == "explorer":
                            self._sounds.play_consonant(self._session.active_consonant, self._active_locale)
                        elif self._session.current_mode == "catcher":
                            self._sounds.play_prompt(self._session.target_syl, self._active_locale)
                        elif self._session.current_mode == "builder":
                            self._sounds.play_word(self._session.cur_stem, self._active_locale)
                        continue

                    # 3. Mascot Tap
                    if self._mascot.contains(lx, ly):
                        self._mascot.wiggle()
                        self._sounds.play("pop")
                        continue

                    # 4. Mode Interactions
                    if self._session.current_mode == "explorer":
                        # Consonant Palette Buttons
                        pal_w = 68
                        pal_h = 56
                        for i, c in enumerate(CONSONANTS_IT):
                            row = i % 7
                            col = i // 7
                            bx = 40 + col * 76
                            by = 136 + row * 62
                            btn_rect = pygame.Rect(bx, by, pal_w, pal_h)
                            if btn_rect.collidepoint(lx, ly):
                                self._session.set_active_consonant(c)
                                self._sounds.play_consonant(c, self._active_locale)
                                self._refresh_station1_cards()
                                self._mascot.wiggle()
                                break

                        for card in self._cards_station1:
                            if card.contains(lx, ly):
                                card.bounce()
                                self._sounds.play_syllable(card.syl, self._active_locale)
                                self._mascot.cheer()
                                for _ in range(16):
                                    self._particles.append(Particle(card.rect.centerx, card.rect.centery, card.color_pair[0]))
                                self._safe_emit("syllable.explored", f"syl_{card.syl}_{time.time()}")
                                self._session.on_explore(card.syl)

                    elif self._session.current_mode == "catcher":
                        if self._session.catcher_state == "idle":
                            for orb in self._catcher_orbs:
                                if orb.contains(lx, ly):
                                    if orb.syl == self._session.target_syl:
                                        self._sounds.play_syllable(orb.syl, self._active_locale)
                                        self._mascot.cheer()
                                        # Score via session triggers state/timers
                                        self._session.on_catcher_tap(orb.syl)
                                        self._save_progress()
                                        self._safe_emit("syllable.matched", f"match_{self._session.target_syl}_{time.time()}")
                                        for _ in range(24):
                                            self._particles.append(Particle(orb.x, orb.y, GOLD))
                                    else:
                                        orb.wobble()
                                        self._sounds.play_syllable(orb.syl, self._active_locale)
                                    break

                    elif self._session.current_mode == "builder":
                        if self._btn_whole_word_rect.collidepoint(lx, ly):
                            self._sounds.play_word(self._session.cur_stem, self._active_locale)
                            self._mascot.wiggle()
                            continue
                        if self._btn_split_syllables_rect.collidepoint(lx, ly):
                            self._sounds.play_syllable(self._session.cur_s1, self._active_locale)
                            self._session.start_syllable_breakdown()
                            self._mascot.wiggle()
                            continue

                        if not self._session.word_completed:
                            for tile in self._word_tiles:
                                if tile.contains(lx, ly):
                                    result = self._session.on_builder_tile(tile.syl)
                                    if result == "slot1_ok":
                                        tile.used = True
                                        self._sounds.play_syllable(self._session.cur_s1, self._active_locale)
                                        for _ in range(12):
                                            self._particles.append(Particle(tile.rect.centerx, tile.rect.centery, MINT_GREEN))
                                    elif result == "wrong_slot1":
                                        tile.wobble()
                                        self._sounds.play_syllable(tile.syl, self._active_locale)
                                    elif result == "word_done":
                                        tile.used = True
                                        self._sounds.play_syllable(self._session.cur_s2, self._active_locale)
                                        self._mascot.cheer()
                                        self._save_progress()
                                        self._safe_emit("word.completed", f"word_{self._session.cur_stem}_{time.time()}")
                                        for _ in range(30):
                                            self._particles.append(Particle(512, 170, GOLD))
                                    elif result in ("wrong_slot2",):
                                        tile.wobble()
                                        self._sounds.play_syllable(tile.syl, self._active_locale)
                                    break
                        else:
                            self._session.word_index += 1
                            self._start_word_round(play_audio=True)

                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    self._pointer_down = False

            # Update Scene Entities
            self._mascot.update()
            self._particles = [p for p in self._particles if p.update()]

            if self._session.current_mode == "explorer":
                for c in self._cards_station1:
                    c.update()
            elif self._session.current_mode == "catcher":
                for orb in self._catcher_orbs:
                    orb.update()
            elif self._session.current_mode == "builder":
                for tile in self._word_tiles:
                    tile.update()

            # Draw — every frame for this animated Activity (no dirty gate complexity)
            self._draw()

            # READY contract: exactly once, after first flip in the same loop iteration
            if not self._ready_published:
                mark_activity_ready()
                self._ready_published = True

        # Final persistence (also handled incrementally)
        self._save_progress()
        return 0

    # ------------------------------------------------------------------ #
    # Rendering composition (delegates entity draws to renderer-owned objects)
    # ------------------------------------------------------------------ #
    def _draw(self) -> None:
        logical_surf = self._canvas.surface
        # 1. Background Meadow (prebaked)
        logical_surf.blit(self._renderer.backdrop(), (0, 0))

        # 2. Top Navigation Bar
        for m_id, m_label, r in self._tabs:
            is_active = self._session.current_mode == m_id
            tab_bg = GOLD if is_active else CARD_BG
            tab_border = GOLD_BORDER if is_active else CARD_BORDER
            pygame.draw.rect(logical_surf, (0, 0, 0, 30), (r.x + 2, r.y + 4, r.w, r.h), border_radius=16)
            pygame.draw.rect(logical_surf, tab_bg, r, border_radius=16)
            pygame.draw.rect(logical_surf, tab_border, r, width=3 if is_active else 2, border_radius=16)
            tab_text = self._typography.render(m_label, FontRole.CONTROL, 20, DARK_TEXT)
            logical_surf.blit(tab_text, (r.x + (r.w - tab_text.get_width()) // 2, r.y + (r.h - tab_text.get_height()) // 2))

        # Audio Button
        pygame.draw.rect(logical_surf, (0, 0, 0, 30), (self._audio_btn_rect.x + 2, self._audio_btn_rect.y + 4, self._audio_btn_rect.w, self._audio_btn_rect.h), border_radius=16)
        pygame.draw.rect(logical_surf, SKY_BLUE, self._audio_btn_rect, border_radius=16)
        pygame.draw.rect(logical_surf, CARD_BORDER, self._audio_btn_rect, width=2, border_radius=16)
        speaker_icon = self._typography.render("🔊", FontRole.DISPLAY, 26, (255, 255, 255))
        logical_surf.blit(speaker_icon, (self._audio_btn_rect.x + (self._audio_btn_rect.w - speaker_icon.get_width()) // 2, self._audio_btn_rect.y + (self._audio_btn_rect.h - speaker_icon.get_height()) // 2))

        # Star Jar Counter — bounded renderer cache
        pygame.draw.rect(logical_surf, (0, 0, 0, 30), (self._star_jar_rect.x + 2, self._star_jar_rect.y + 4, self._star_jar_rect.w, self._star_jar_rect.h), border_radius=16)
        pygame.draw.rect(logical_surf, CARD_BG, self._star_jar_rect, border_radius=16)
        pygame.draw.rect(logical_surf, GOLD_BORDER, self._star_jar_rect, width=2, border_radius=16)
        star_icon = self._renderer.star_surface(self._session.stars)
        logical_surf.blit(star_icon, (self._star_jar_rect.x + (self._star_jar_rect.w - star_icon.get_width()) // 2, self._star_jar_rect.y + (self._star_jar_rect.h - star_icon.get_height()) // 2))

        # 3. Mode Content
        if self._session.current_mode == "explorer":
            # Consonant Toy Box Shelf
            shelf_rect = pygame.Rect(28, 92, 172, 490)
            pygame.draw.rect(logical_surf, (0, 0, 0, 25), (shelf_rect.x + 3, shelf_rect.y + 4, shelf_rect.w, shelf_rect.h), border_radius=18)
            pygame.draw.rect(logical_surf, (248, 242, 230), shelf_rect, border_radius=18)
            pygame.draw.rect(logical_surf, (215, 195, 170), shelf_rect, width=3, border_radius=18)

            pal_title = self._typography.render(display_text("Consonanti"), FontRole.TITLE, 18, DARK_TEXT)
            logical_surf.blit(pal_title, (shelf_rect.centerx - pal_title.get_width() // 2, 104))

            pal_w = 68
            pal_h = 56
            for i, c in enumerate(CONSONANTS_IT):
                row = i % 7
                col = i // 7
                bx = 38 + col * 78
                by = 136 + row * 62
                btn_rect = pygame.Rect(bx, by, pal_w, pal_h)
                is_sel = c == self._session.active_consonant
                pygame.draw.rect(logical_surf, (0, 0, 0, 30), (bx + 2, by + 4, pal_w, pal_h), border_radius=14)
                c_bg = GOLD if is_sel else (255, 255, 255)
                c_border = GOLD_BORDER if is_sel else CARD_BORDER
                pygame.draw.rect(logical_surf, c_bg, btn_rect, border_radius=14)
                pygame.draw.rect(logical_surf, c_border, btn_rect, width=3 if is_sel else 2, border_radius=14)
                c_text = self._typography.render(c, FontRole.DISPLAY, 30, DARK_TEXT)
                logical_surf.blit(c_text, (bx + (pal_w - c_text.get_width()) // 2, by + (pal_h - c_text.get_height()) // 2 - 2))
                if is_sel:
                    pygame.draw.circle(logical_surf, (255, 255, 255), (bx + pal_w - 6, by + 6), 6)
                    pygame.draw.circle(logical_surf, CORAL, (bx + pal_w - 6, by + 6), 4)

            # Central Workshop Header Card
            top_card = pygame.Rect(226, 92, 670, 140)
            pygame.draw.rect(logical_surf, (0, 0, 0, 25), (top_card.x + 3, top_card.y + 4, top_card.w, top_card.h), border_radius=22)
            pygame.draw.rect(logical_surf, CARD_BG, top_card, border_radius=22)
            pygame.draw.rect(logical_surf, CARD_BORDER, top_card, width=3, border_radius=22)
            formula_surf = self._typography.render(display_text(f"Fabbrica delle Sillabe:   [ {self._session.active_consonant} ]  ➕  Vocali ( A , E , I , O , U )"), FontRole.TITLE, 22, DARK_TEXT)
            logical_surf.blit(formula_surf, (top_card.centerx - formula_surf.get_width() // 2, top_card.y + 20))
            instruct_surf = self._typography.render(display_text("Tocca ogni tessera per ascoltare e imparare la sillaba!"), FontRole.BODY, 18, (100, 85, 115))
            logical_surf.blit(instruct_surf, (top_card.centerx - instruct_surf.get_width() // 2, top_card.y + 72))
            for card in self._cards_station1:
                card.draw(logical_surf, self._typography)

        elif self._session.current_mode == "catcher":
            banner_rect = pygame.Rect(260, 95, 504, 76)
            pygame.draw.rect(logical_surf, (0, 0, 0, 25), (banner_rect.x + 3, banner_rect.y + 4, banner_rect.w, banner_rect.h), border_radius=18)
            pygame.draw.rect(logical_surf, CARD_BG, banner_rect, border_radius=18)
            pygame.draw.rect(logical_surf, GOLD_BORDER, banner_rect, width=3, border_radius=18)
            p_txt = display_text("Ascolta e tocca:  ")
            p_surf = self._typography.render(p_txt, FontRole.TITLE, 28, DARK_TEXT)
            target_surf = self._typography.render(self._session.target_syl, FontRole.DISPLAY, 40, CORAL)
            total_w = p_surf.get_width() + target_surf.get_width()
            sx = banner_rect.centerx - total_w // 2
            logical_surf.blit(p_surf, (sx, banner_rect.centery - p_surf.get_height() // 2))
            logical_surf.blit(target_surf, (sx + p_surf.get_width(), banner_rect.centery - target_surf.get_height() // 2))
            for orb in self._catcher_orbs:
                orb.draw(logical_surf, self._typography)

        elif self._session.current_mode == "builder":
            center_card = pygame.Rect(240, 86, 544, 320)
            pygame.draw.rect(logical_surf, (0, 0, 0, 25), (center_card.x + 4, center_card.y + 5, center_card.w, center_card.h), border_radius=24)
            pygame.draw.rect(logical_surf, CARD_BG, center_card, border_radius=24)
            pygame.draw.rect(logical_surf, CARD_BORDER, center_card, width=3, border_radius=24)
            emoji_surf = self._typography.render(self._session.cur_emoji, FontRole.DISPLAY, 80, DARK_TEXT)
            logical_surf.blit(emoji_surf, (center_card.centerx - emoji_surf.get_width() // 2, center_card.y + 12))
            if self._session.word_completed:
                comp_txt = self._typography.render(f"✨ {self._session.cur_word_display} ✨", FontRole.TITLE, 32, (220, 130, 20))
                logical_surf.blit(comp_txt, (center_card.centerx - comp_txt.get_width() // 2, center_card.y + 104))
            # Icon-only audio buttons (no text spoilers)
            pygame.draw.rect(logical_surf, (0, 0, 0, 25), (self._btn_whole_word_rect.x + 2, self._btn_whole_word_rect.y + 4, self._btn_whole_word_rect.w, self._btn_whole_word_rect.h), border_radius=18)
            pygame.draw.rect(logical_surf, GOLD, self._btn_whole_word_rect, border_radius=18)
            pygame.draw.rect(logical_surf, GOLD_BORDER, self._btn_whole_word_rect, width=3, border_radius=18)
            btn1_icon = self._typography.render("🔊", FontRole.DISPLAY, 32, DARK_TEXT)
            logical_surf.blit(btn1_icon, (self._btn_whole_word_rect.centerx - btn1_icon.get_width() // 2, self._btn_whole_word_rect.centery - btn1_icon.get_height() // 2))
            pygame.draw.rect(logical_surf, (0, 0, 0, 25), (self._btn_split_syllables_rect.x + 2, self._btn_split_syllables_rect.y + 4, self._btn_split_syllables_rect.w, self._btn_split_syllables_rect.h), border_radius=18)
            is_speaking_split = self._session.syllable_speech_step > 0
            pygame.draw.rect(logical_surf, SKY_BLUE if not is_speaking_split else MINT_GREEN, self._btn_split_syllables_rect, border_radius=18)
            pygame.draw.rect(logical_surf, CARD_BORDER, self._btn_split_syllables_rect, width=3, border_radius=18)
            btn2_icon = self._typography.render("🗣️", FontRole.DISPLAY, 32, DARK_TEXT if is_speaking_split else LIGHT_TEXT)
            logical_surf.blit(btn2_icon, (self._btn_split_syllables_rect.centerx - btn2_icon.get_width() // 2, self._btn_split_syllables_rect.centery - btn2_icon.get_height() // 2))

            # Syllable slots
            slot_w, slot_h = 135, 96
            slot1_rect = pygame.Rect(center_card.centerx - slot_w - 18, center_card.y + 195, slot_w, slot_h)
            slot2_rect = pygame.Rect(center_card.centerx + 18, center_card.y + 195, slot_w, slot_h)
            if self._session.slot1_filled:
                pygame.draw.rect(logical_surf, MINT_GREEN, slot1_rect, border_radius=18)
                pygame.draw.rect(logical_surf, CARD_BORDER, slot1_rect, width=3, border_radius=18)
                s1_txt = self._typography.render(self._session.cur_s1, FontRole.DISPLAY, 46, (255, 255, 255))
                logical_surf.blit(s1_txt, (slot1_rect.centerx - s1_txt.get_width() // 2, slot1_rect.centery - s1_txt.get_height() // 2))
            else:
                pygame.draw.rect(logical_surf, (244, 244, 244), slot1_rect, border_radius=18)
                pygame.draw.rect(logical_surf, (160, 160, 175), slot1_rect, width=3, border_radius=18)
                q1_txt = self._typography.render(display_text("1° Sillaba"), FontRole.TITLE, 20, (160, 160, 175))
                logical_surf.blit(q1_txt, (slot1_rect.centerx - q1_txt.get_width() // 2, slot1_rect.centery - q1_txt.get_height() // 2))
            if self._session.slot2_filled:
                pygame.draw.rect(logical_surf, MINT_GREEN, slot2_rect, border_radius=18)
                pygame.draw.rect(logical_surf, CARD_BORDER, slot2_rect, width=3, border_radius=18)
                s2_txt = self._typography.render(self._session.cur_s2, FontRole.DISPLAY, 46, (255, 255, 255))
                logical_surf.blit(s2_txt, (slot2_rect.centerx - s2_txt.get_width() // 2, slot2_rect.centery - s2_txt.get_height() // 2))
            else:
                pygame.draw.rect(logical_surf, (244, 244, 244), slot2_rect, border_radius=18)
                pygame.draw.rect(logical_surf, (160, 160, 175), slot2_rect, width=3, border_radius=18)
                q2_txt = self._typography.render(display_text("2° Sillaba"), FontRole.TITLE, 20, (160, 160, 175))
                logical_surf.blit(q2_txt, (slot2_rect.centerx - q2_txt.get_width() // 2, slot2_rect.centery - q2_txt.get_height() // 2))
            for tile in self._word_tiles:
                tile.draw(logical_surf, self._typography)

        # 4. Companion Leo
        self._mascot.draw(logical_surf)

        # 5. Confetti & Star Particles
        for p in self._particles:
            p.draw(logical_surf)

        # 6. Virtual Cursor
        cx, cy = self._virtual_pointer
        pygame.draw.circle(logical_surf, (255, 255, 255), (int(cx), int(cy)), 10)
        pygame.draw.circle(logical_surf, CORAL if self._pointer_down else SKY_BLUE, (int(cx), int(cy)), 7)
        pygame.draw.circle(logical_surf, CARD_BORDER, (int(cx), int(cy)), 10, width=2)

        self._canvas.present(clear=self._theme.background)
        pygame.display.flip()


__all__ = ["SillabeApp"]
