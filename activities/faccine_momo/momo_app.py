"""Interactive game loop and touch handler for Le Faccine di Momo."""

from __future__ import annotations

import random
import time

import pygame

if __package__:
    from .momo_audio import MomoAudio, MomoSpeechQueue
    from .momo_model import (
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        Emotion,
        GameMode,
        MomoModel,
        MomoParticle,
    )
    from .momo_renderer import MomoRenderer
else:
    from momo_audio import MomoAudio, MomoSpeechQueue
    from momo_model import (
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        Emotion,
        GameMode,
        MomoModel,
        MomoParticle,
    )
    from momo_renderer import MomoRenderer


class MomoActivity:
    """Greia Activity controller for Le Faccine di Momo."""

    def __init__(
        self,
        screen: pygame.Surface,
        renderer: MomoRenderer,
        audio: MomoAudio,
        model: MomoModel,
    ) -> None:
        self.screen = screen
        self.renderer = renderer
        self.audio = audio
        self.model = model
        self.speech_queue = MomoSpeechQueue(self.audio)
        self.clock = pygame.time.Clock()
        self.running = True

        # Quiz advance timer after correct answer
        self._quiz_advance_timer: float = 0.0

        # Welcome greeting from Momo
        self.speech_queue.enqueue("welcome", delay_after=0.4)

    def run(self) -> int:
        last_time = time.perf_counter()

        while self.running:
            now = time.perf_counter()
            dt = min(0.1, now - last_time)
            last_time = now

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self._handle_pointer_down(event.pos)

            # Quiz advance transition
            if self._quiz_advance_timer > 0.0:
                self._quiz_advance_timer -= dt
                if self._quiz_advance_timer <= 0.0 and self.model.mode == GameMode.GUESS_EMOTION:
                    self.model.start_quiz_round()
                    self.speech_queue.enqueue(self.model.quiz_target.value, delay_after=0.3)

            # Update simulation & speech
            self.model.update(dt)
            self.speech_queue.update(dt)

            # Render frame
            self.renderer.render(self.screen, self.model)
            pygame.display.flip()
            self.clock.tick(60)

        pygame.quit()
        return 0

    def _to_reference_pos(self, physical_pos: tuple[int, int]) -> tuple[int, int]:
        sw, sh = self.screen.get_size()
        if (sw, sh) == (REFERENCE_WIDTH, REFERENCE_HEIGHT):
            return physical_pos
        rx = int(physical_pos[0] * (REFERENCE_WIDTH / max(1, sw)))
        ry = int(physical_pos[1] * (REFERENCE_HEIGHT / max(1, sh)))
        return (rx, ry)

    def _handle_pointer_down(self, physical_pos: tuple[int, int]) -> None:
        ref_x, ref_y = self._to_reference_pos(physical_pos)

        # 1. Check Mode Toggle Button
        if self.renderer.mode_button_rect.collidepoint(ref_x, ref_y):
            self.audio.play_sfx("pop")
            new_mode = self.model.toggle_mode()
            if new_mode == GameMode.GUESS_EMOTION:
                self.speech_queue.enqueue("game_prompt", delay_after=0.5)
                self.speech_queue.enqueue(self.model.quiz_target.value, delay_after=0.3)
            else:
                self.speech_queue.enqueue("welcome", delay_after=0.3)
            return

        # 2. Free Mirror Mode Interactions
        if self.model.mode == GameMode.FREE_MIRROR:
            # Check Emotion circular buttons (left & right)
            for emo, rect in self.renderer.left_buttons + self.renderer.right_buttons:
                if rect.collidepoint(ref_x, ref_y):
                    self.model.set_emotion(emo)
                    self.audio.play_sfx("pop")
                    self.speech_queue.enqueue(emo.value, delay_after=0.3)
                    return

            # Check Cheeks: stroking/cuddling Momo!
            if self.renderer.momo_left_cheek.collidepoint(ref_x, ref_y) or self.renderer.momo_right_cheek.collidepoint(ref_x, ref_y):
                if self.model.comfort_momo():
                    self.audio.play_sfx("heart")
                    self.speech_queue.enqueue("comfort", delay_after=0.4)
                else:
                    self.audio.play_sfx("giggle")
                    self.model.hop_offset = 15.0
                return

            # Check Momo's Face center (tickling/cycling emotion)
            if self.renderer.momo_face_rect.collidepoint(ref_x, ref_y):
                # Cycle to next emotion
                all_emo = list(Emotion)
                cur_idx = all_emo.index(self.model.emotion)
                next_emo = all_emo[(cur_idx + 1) % len(all_emo)]
                self.model.set_emotion(next_emo)
                self.audio.play_sfx("giggle")
                self.speech_queue.enqueue(next_emo.value, delay_after=0.3)
                return

        # 3. Quiz Mode Interactions
        else:
            for idx, choice_emo in enumerate(self.model.quiz_choices):
                rect = self.renderer.quiz_choice_rects[idx]
                if rect.collidepoint(ref_x, ref_y):
                    if self.model.answer_quiz(choice_emo):
                        self.audio.play_sfx("boing")
                        praise = random.choice(["praise_1", "praise_2", "praise_3"])
                        self.speech_queue.enqueue(praise, delay_after=0.5)
                        self._quiz_advance_timer = 1.8
                    else:
                        self.audio.play_sfx("wobble")
                    return

        # 4. Ambient tap sparkle
        self.audio.play_sfx("pop")
        for _ in range(4):
            self.model.particles.append(
                MomoParticle(
                    x=ref_x + random.uniform(-10, 10),
                    y=ref_y + random.uniform(-10, 10),
                    vx=random.uniform(-30, 30),
                    vy=random.uniform(-50, -10),
                    kind="sparkle",
                    color=(255, 235, 120),
                    size=random.uniform(4, 8),
                    life=0.8,
                )
            )
