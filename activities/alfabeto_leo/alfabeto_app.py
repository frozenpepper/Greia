"""Main application loop and input handling for L'Alfabeto di Leo."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Final

import pygame

from greia_platform.activity_api import activity_stop_requested, mark_activity_ready
from greia_platform.activity_ui import ChildUiMetrics
from greia_platform.localization import LocalizedResources
from greia_platform.pygame_canvas import PygameReferenceCanvas
from greia_platform.typography import GreiaTypography

if __package__:
    from .alfabeto_audio import AlfabetoAudio
    from .alfabeto_model import (
        AlfabetoModel,
        GameMode,
        LETTERS_CATALOGUE,
        LetterItem,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
    )
    from .alfabeto_renderer import AlfabetoRenderer
    from .alfabeto_services import AlfabetoServices, AlfabetoStorageState
else:
    from alfabeto_audio import AlfabetoAudio
    from alfabeto_model import (
        AlfabetoModel,
        GameMode,
        LETTERS_CATALOGUE,
        LetterItem,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
    )
    from alfabeto_renderer import AlfabetoRenderer
    from alfabeto_services import AlfabetoServices, AlfabetoStorageState


@dataclass
class AlfabetoApp:
    """Toddler alphabet exploration with Leo."""

    screen: pygame.Surface
    canvas: PygameReferenceCanvas
    renderer: AlfabetoRenderer
    audio: AlfabetoAudio
    services: AlfabetoServices
    resources: LocalizedResources
    typography: GreiaTypography
    model: AlfabetoModel = field(default_factory=AlfabetoModel)
    metrics: ChildUiMetrics = field(init=False)
    ready_published: bool = False
    anim_time: float = 0.0

    def __post_init__(self) -> None:
        self.metrics = ChildUiMetrics.for_size(*self.screen.get_size())
        saved = self.services.load_state()
        self.model.discovered_letters = set(saved.discovered_letters)

    def run(self) -> int:
        clock = pygame.time.Clock()
        running = True
        last_frame = time.monotonic()

        while running and not activity_stop_requested():
            now = time.monotonic()
            dt = min(0.05, now - last_frame)
            last_frame = now
            self.anim_time += dt

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif pygame.K_a <= event.key <= pygame.K_z:
                        char = chr(event.key - pygame.K_a + ord("A"))
                        self._handle_letter_key(char)
                    elif event.key == pygame.K_LEFT:
                        self._handle_step(-1)
                    elif event.key == pygame.K_RIGHT:
                        self._handle_step(1)
                    elif event.key in (pygame.K_SPACE, pygame.K_RETURN):
                        self._handle_space()
                elif event.type == pygame.VIDEORESIZE:
                    self.metrics = ChildUiMetrics.for_size(*self.screen.get_size())
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    ref_pos = self._screen_to_reference(event.pos)
                    self._handle_click(ref_pos)

            events = self.model.update(dt)
            for ev in events:
                self.services.emit_event(ev)
                if ev == "alphabet.parade_completed":
                    self.audio.play("celebrate")
                self.services.save_state(
                    AlfabetoStorageState(
                        discovered_letters=sorted(list(self.model.discovered_letters)),
                        rounds_completed=len(self.model.discovered_letters),
                    )
                )

            self.renderer.render(self.model, self.anim_time)
            self.canvas.present()
            pygame.display.flip()

            if not self.ready_published:
                mark_activity_ready()
                self.ready_published = True

            clock.tick(30)

        self.services.save_state(
            AlfabetoStorageState(
                discovered_letters=sorted(list(self.model.discovered_letters)),
                rounds_completed=len(self.model.discovered_letters),
            )
        )
        self.typography.clear()
        return 0

    def _screen_to_reference(self, pos: tuple[int, int]) -> tuple[float, float]:
        sw, sh = self.screen.get_size()
        scale_x = REFERENCE_WIDTH / max(1, sw)
        scale_y = REFERENCE_HEIGHT / max(1, sh)
        return (pos[0] * scale_x, pos[1] * scale_y)

    def _handle_click(self, ref_pos: tuple[float, float]) -> None:
        rx, ry = ref_pos
        # Protect top-left reserved system chrome area (80x80)
        if rx <= 88 and ry <= 88:
            return

        # Check Mode switch button
        btn_w, btn_h = 170, 48
        btn_x = REFERENCE_WIDTH - btn_w - 30
        btn_y = 22
        if btn_x <= rx <= btn_x + btn_w and btn_y <= ry <= btn_y + btn_h:
            new_mode = GameMode.GUESS if self.model.mode == GameMode.EXPLORE else GameMode.EXPLORE
            self.model.switch_mode(new_mode)
            self.audio.play("pop")
            return

        if self.model.mode == GameMode.EXPLORE:
            self._handle_explore_click(rx, ry)
        else:
            self._handle_guess_click(rx, ry)

    def _handle_explore_click(self, rx: float, ry: float) -> None:
        # Check Central Card
        cx, cy = REFERENCE_WIDTH // 2, 240
        if (cx - 160) <= rx <= (cx + 160) and (cy - 155) <= ry <= (cy + 155):
            self.model.revealed = True
            self.model.reveal_timer = 0.5
            self.audio.play_letter(self.model.active_letter.char)
            return

        # Check Letter Strip buttons (y: 500 to 564)
        if 490 <= ry <= 575:
            # Prev button
            if 135 <= rx <= 195:
                self._handle_step(-1)
                return
            # Next button
            start_x = 210
            visible_count = 7
            btn_size = 64
            spacing = 16
            next_x = start_x + visible_count * (btn_size + spacing)
            if next_x <= rx <= next_x + 55:
                self._handle_step(1)
                return

            # Check each of the 7 buttons
            half = visible_count // 2
            total = len(LETTERS_CATALOGUE)
            for i in range(visible_count):
                bx = start_x + i * (btn_size + spacing)
                if bx <= rx <= bx + btn_size:
                    offset = i - half
                    idx = (self.model.current_index + offset) % total
                    target_char = LETTERS_CATALOGUE[idx].char
                    self.model.select_letter(target_char)
                    self.audio.play_letter(target_char)
                    return

    def _handle_guess_click(self, rx: float, ry: float) -> None:
        # Check 3 Big Choice Cards (y: 350 to 510)
        card_w, card_h = 140, 160
        spacing = 40
        total_w = 3 * card_w + 2 * spacing
        start_x = (REFERENCE_WIDTH - total_w) // 2
        card_y = 350

        if card_y <= ry <= card_y + card_h:
            for i, choice in enumerate(self.model.guess_choices):
                cx = start_x + i * (card_w + spacing)
                if cx <= rx <= cx + card_w:
                    res, letter = self.model.handle_guess_choice(choice.char)
                    if res == "correct":
                        self.audio.play_celebration()
                        self.audio.play_letter(letter.char)
                    elif res == "wobble":
                        self.audio.play_wobble()
                    elif res == "next":
                        self.audio.play("pop")
                    return

    def _handle_letter_key(self, char: str) -> None:
        if self.model.mode == GameMode.EXPLORE:
            if self.model.select_letter(char):
                self.audio.play_letter(char)
        else:
            res, letter = self.model.handle_guess_choice(char)
            if res == "correct":
                self.audio.play("celebrate")
                self.audio.play_letter(letter.char)
            elif res == "wobble":
                self.audio.play("wobble")

    def _handle_step(self, direction: int) -> None:
        total = len(LETTERS_CATALOGUE)
        new_idx = (self.model.current_index + direction) % total
        target_char = LETTERS_CATALOGUE[new_idx].char
        self.model.select_letter(target_char)
        self.audio.play_letter(target_char)

    def _handle_space(self) -> None:
        if self.model.mode == GameMode.EXPLORE:
            self.audio.play_letter(self.model.active_letter.char)
        elif self.model.guess_solved:
            self.model.setup_guess_round()
            self.audio.play("pop")
