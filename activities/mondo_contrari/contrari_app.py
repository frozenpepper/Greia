"""Interactive game loop and event processing for Mondo Contrari."""

from __future__ import annotations

import random
import time

import pygame

from .contrari_audio import ContrariAudio, ContrariSpeechQueue
from .contrari_model import (
    REFERENCE_HEIGHT,
    REFERENCE_WIDTH,
    ContrariModel,
    OppositeCategory,
)
from .contrari_renderer import ContrariRenderer


class ContrariActivity:
    """Greia Activity controller for Mondo Contrari."""

    def __init__(
        self,
        screen: pygame.Surface,
        renderer: ContrariRenderer,
        audio: ContrariAudio,
        model: ContrariModel,
    ) -> None:
        self.screen = screen
        self.renderer = renderer
        self.audio = audio
        self.model = model
        self.speech_queue = ContrariSpeechQueue(self.audio)
        self.clock = pygame.time.Clock()
        self.running = True

        self._interactions_count = 0

        # Welcome prompt from Flash
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

            # Update physics & speech
            self.model.update(dt)
            self.speech_queue.update(dt)

            # Render scene
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

        # 1. Check Top Category Toolbar
        for cat, rect in self.renderer.category_buttons.items():
            if rect.collidepoint(ref_x, ref_y):
                self.model.set_category(cat)
                self.audio.play_sfx("pop")
                self._announce_current_state()
                return

        # 2. Check Central Play Area tap
        if self.renderer.play_surface_rect.collidepoint(ref_x, ref_y):
            self._trigger_current_opposite()

    def _announce_current_state(self) -> None:
        cat = self.model.category
        if cat == OppositeCategory.UP_DOWN:
            cue = "up" if self.model.is_up else "down"
        elif cat == OppositeCategory.BIG_SMALL:
            cue = "big" if self.model.is_big else "small"
        elif cat == OppositeCategory.IN_OUT:
            cue = "in" if self.model.is_in else "out"
        elif cat == OppositeCategory.OPEN_CLOSED:
            cue = "open" if self.model.is_open else "closed"
        elif cat == OppositeCategory.FAST_SLOW:
            cue = "fast" if self.model.is_fast else "slow"
        else:
            return
        self.speech_queue.enqueue(cue, delay_after=0.3)

    def _trigger_current_opposite(self) -> None:
        cat = self.model.category
        self._interactions_count += 1

        if cat == OppositeCategory.UP_DOWN:
            is_up = self.model.toggle_up_down()
            self.audio.play_sfx("whoosh")
            self.speech_queue.enqueue("up" if is_up else "down", delay_after=0.3)

        elif cat == OppositeCategory.BIG_SMALL:
            is_big = self.model.toggle_big_small()
            self.audio.play_sfx("ding" if is_big else "pop")
            self.speech_queue.enqueue("big" if is_big else "small", delay_after=0.3)

        elif cat == OppositeCategory.IN_OUT:
            is_out = self.model.toggle_in_out()
            self.audio.play_sfx("boing")
            self.speech_queue.enqueue("out" if is_out else "in", delay_after=0.3)

        elif cat == OppositeCategory.OPEN_CLOSED:
            is_open = self.model.toggle_open_closed()
            self.audio.play_sfx("creak")
            self.speech_queue.enqueue("open" if is_open else "closed", delay_after=0.3)

        elif cat == OppositeCategory.FAST_SLOW:
            is_fast = self.model.toggle_fast_slow()
            self.audio.play_sfx("whoosh" if is_fast else "pop")
            self.speech_queue.enqueue("fast" if is_fast else "slow", delay_after=0.3)

        # Occasional praise from Flash
        if self._interactions_count % 4 == 0:
            praise = random.choice(["praise_1", "praise_2", "praise_3"])
            self.speech_queue.enqueue(praise, delay_after=0.4)
