"""Application event loop for L'Alfabeto di Leo."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import pygame

from greia_platform.activity_api import activity_stop_requested, mark_activity_ready
from greia_platform.localization import LocalizedResources
from greia_platform.pygame_canvas import PygameReferenceCanvas
from greia_platform.typography import GreiaTypography

if __package__:
    from .alfabeto_audio import AlfabetoAudio
    from .alfabeto_model import (
        LETTERS_CATALOGUE,
        REFERENCE_WIDTH,
        AlfabetoModel,
        GameMode,
    )
    from .alfabeto_renderer import AlfabetoRenderer
    from .alfabeto_services import AlfabetoServices, AlfabetoStorageState
else:
    from alfabeto_audio import AlfabetoAudio
    from alfabeto_model import (
        LETTERS_CATALOGUE,
        REFERENCE_WIDTH,
        AlfabetoModel,
        GameMode,
    )
    from alfabeto_renderer import AlfabetoRenderer
    from alfabeto_services import AlfabetoServices, AlfabetoStorageState


@dataclass
class AlfabetoApp:
    """Toddler capital letter discovery and peek-a-boo guessing game."""

    screen: pygame.Surface
    canvas: PygameReferenceCanvas
    renderer: AlfabetoRenderer
    audio: AlfabetoAudio
    services: AlfabetoServices
    resources: LocalizedResources
    typography: GreiaTypography
    model: AlfabetoModel = field(default_factory=AlfabetoModel)
    ready_published: bool = False
    anim_time: float = 0.0

    def __post_init__(self) -> None:
        saved = self.services.load_state()
        if saved.discovered_letters:
            self.model.discovered_letters.update(saved.discovered_letters)

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
                    elif event.key == pygame.K_SPACE:
                        self._handle_space()
                    elif event.key == pygame.K_LEFT:
                        self._handle_step(-1)
                    elif event.key == pygame.K_RIGHT:
                        self._handle_step(1)
                    elif pygame.K_a <= event.key <= pygame.K_z:
                        char = chr(ord("A") + (event.key - pygame.K_a))
                        self._handle_key_letter(char)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    ref_pos = self.canvas.pointer(event.pos)
                    if ref_pos is not None:
                        self._handle_click(ref_pos)

            events = self.model.update(dt)
            for ev in events:
                self.services.emit_event(ev)
                if ev == "letter.discovered" and self.model.mode == GameMode.GUESS:
                    self.audio.play_question(self.model.target_letter.char)
                elif ev == "alphabet.parade_completed":
                    self.audio.play_celebration()

                self.services.save_state(
                    AlfabetoStorageState(
                        discovered_letters=sorted(self.model.discovered_letters),
                        rounds_completed=len(self.model.discovered_letters),
                    )
                )

            self.renderer.render(self.model, self.anim_time)
            self.canvas.present()
            pygame.display.flip()

            if not self.ready_published:
                mark_activity_ready()
                self.ready_published = True
                self.audio.play_intro()

            clock.tick(30)

        self.services.save_state(
            AlfabetoStorageState(
                discovered_letters=sorted(self.model.discovered_letters),
                rounds_completed=len(self.model.discovered_letters),
            )
        )
        self.typography.clear()
        return 0

    def _handle_click(self, ref_pos: tuple[float, float]) -> None:
        rx, ry = ref_pos
        # Greia consumes protected Home/Back input before Activity delivery.

        btn_w, btn_h = 175, 48
        btn_x = REFERENCE_WIDTH - btn_w - 30
        btn_y = 20
        if btn_x <= rx <= btn_x + btn_w and btn_y <= ry <= btn_y + btn_h:
            new_mode = (
                GameMode.GUESS
                if self.model.mode == GameMode.EXPLORE
                else GameMode.EXPLORE
            )
            self.model.switch_mode(new_mode)
            if new_mode == GameMode.GUESS:
                self.audio.play_question(self.model.target_letter.char)
            else:
                self.audio.play_letter(self.model.active_letter.char)
            return

        if self.model.mode == GameMode.EXPLORE:
            self._handle_explore_click(rx, ry)
        else:
            self._handle_guess_click(rx, ry)

    def _handle_explore_click(self, rx: float, ry: float) -> None:
        cx, cy = REFERENCE_WIDTH // 2, 240
        if (cx - 160) <= rx <= (cx + 160) and (cy - 155) <= ry <= (cy + 155):
            self.model.revealed = True
            self.model.reveal_timer = 0.5
            self.audio.play_letter(self.model.active_letter.char)
            return

        if 495 <= ry <= 580:
            if 130 <= rx <= 195:
                self._handle_step(-1)
                return

            start_x = 205
            visible_count = 7
            btn_size = 64
            spacing = 16
            next_x = start_x + visible_count * (btn_size + spacing)
            if next_x <= rx <= next_x + 60:
                self._handle_step(1)
                return

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
        t_w, t_h = 240, 180
        tx = (REFERENCE_WIDTH - t_w) // 2
        ty = 110
        if tx <= rx <= tx + t_w and ty <= ry <= ty + t_h:
            self.audio.play_question(self.model.target_letter.char)
            return

        card_w, card_h = 145, 165
        spacing = 40
        total_w = 3 * card_w + 2 * spacing
        start_x = (REFERENCE_WIDTH - total_w) // 2
        card_y = 330

        if card_y <= ry <= card_y + card_h:
            for i, choice in enumerate(self.model.guess_choices):
                cx = start_x + i * (card_w + spacing)
                if cx <= rx <= cx + card_w:
                    res, letter = self.model.handle_guess_choice(choice.char)
                    if res == "correct":
                        self.audio.play_letter(letter.char)
                        self.audio.play_celebration()
                    elif res == "wobble":
                        self.audio.play_wobble()
                    elif res == "next":
                        self.audio.play("pop")
                    return

    def _handle_step(self, delta: int) -> None:
        item = self.model.step(delta)
        self.audio.play_letter(item.char)

    def _handle_key_letter(self, char: str) -> None:
        if self.model.mode == GameMode.EXPLORE:
            if self.model.select_letter(char):
                self.audio.play_letter(char)
        else:
            res, letter = self.model.handle_guess_choice(char)
            if res == "correct":
                self.audio.play_letter(letter.char)
                self.audio.play_celebration()
            elif res == "wobble":
                self.audio.play_wobble()

    def _handle_space(self) -> None:
        if self.model.mode == GameMode.EXPLORE:
            self.audio.play_letter(self.model.active_letter.char)
        else:
            self.audio.play_question(self.model.target_letter.char)
