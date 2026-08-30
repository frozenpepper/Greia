from __future__ import annotations

import io
import math
import random
import struct
import time
from pathlib import Path
import wave

import pygame

from greia_platform.activity_api import (
    activity_stop_requested,
    emit_activity_event,
    get_profile_locale,
    get_storage,
    get_theme,
    mark_activity_ready,
)
from greia_platform.activity_ui import ChildUiMetrics
from greia_platform.child_text import display_text
from greia_platform.localization import (
    ActivityLocaleSupport,
    LocalizedResources,
    resolve_activity_locale,
)
from greia_platform.pygame_canvas import PygameReferenceCanvas, activity_viewport_for_surface
from greia_platform.typography import GreiaTypography

if __package__:
    from .pasticceria_content import CAKE_SLOTS, GOLD, REFERENCE_HEIGHT, REFERENCE_WIDTH, STORAGE_KEY, TOPPINGS
    from .pasticceria_model import PasticceriaModel
    from .pasticceria_renderer import PasticceriaRenderer
else:
    from pasticceria_content import CAKE_SLOTS, GOLD, REFERENCE_HEIGHT, REFERENCE_WIDTH, STORAGE_KEY, TOPPINGS
    from pasticceria_model import PasticceriaModel
    from pasticceria_renderer import PasticceriaRenderer


def _synth_wav(samples: list[int], rate: int = 22050) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        raw = b"".join(struct.pack("<h", max(-32767, min(32767, s))) for s in samples)
        w.writeframes(raw)
    return buf.getvalue()


class SoundManager:
    """Bounded prebuilt procedural sound bank for the bakery."""

    def __init__(self) -> None:
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        self._enabled = False
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(22050, -16, 1, 512)
            self._init_sounds()
            self._enabled = True
        except Exception:
            self._enabled = False

    def _init_sounds(self) -> None:
        drop_samples = [
            int(math.sin(2 * math.pi * (450 + (900 - i) * 0.8) * (i / 22050.0)) * max(0.0, 1.0 - (i / 22050.0) / 0.06) * 14000)
            for i in range(1300)
        ]
        self._sounds["drop"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(drop_samples)))

        chime_samples: list[int] = []
        for i in range(6000):
            t = i / 22050.0
            f = 587.33 if t < 0.09 else (880.0 if t < 0.18 else 1174.66)
            env = max(0.0, 1.0 - t / 0.27)
            chime_samples.append(int(math.sin(2 * math.pi * f * t) * env * 12000))
        self._sounds["chime"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(chime_samples)))

        ding_samples: list[int] = []
        for i in range(8000):
            t = i / 22050.0
            f = 1046.50
            env = math.exp(-6.0 * t)
            harm = math.sin(2 * math.pi * f * t) * 0.7 + math.sin(2 * math.pi * f * 2.75 * t) * 0.3
            ding_samples.append(int(harm * env * 15000))
        self._sounds["ding"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(ding_samples)))

        fanfare_samples: list[int] = []
        notes = [523.25, 659.25, 783.99, 1046.50, 1318.51]
        for i in range(12000):
            t = i / 22050.0
            idx = min(len(notes) - 1, int(t / 0.08))
            env = max(0.0, 1.0 - t / 0.54)
            fanfare_samples.append(int(math.sin(2 * math.pi * notes[idx] * t) * env * 14000))
        self._sounds["fanfare"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(fanfare_samples)))

    def play(self, name: str) -> None:
        if self._enabled and name in self._sounds:
            try:
                self._sounds[name].play()
            except Exception:
                pass


def _is_safe_point(surface: pygame.Surface, position: tuple[int, int]) -> bool:
    vp = activity_viewport_for_surface(surface)
    x, y = position
    if not (0 <= x < vp.surface.width and 0 <= y < vp.surface.height):
        return False
    for protected in vp.protected_regions:
        if protected.x <= x < protected.right and protected.y <= y < protected.bottom:
            return False
    return True


class PasticceriaApp:
    """Lifecycle owner for the Magic Bakery Activity.

    Owns screen/canvas/metrics/typography, model, renderer and input
    routing. Delegates rules to the pure model and presentation to the
    renderer. Publishes READY after the first flip in the same loop.
    """

    def __init__(
        self,
        screen: pygame.Surface,
        canvas: PygameReferenceCanvas,
        metrics: ChildUiMetrics,
        typography: GreiaTypography,
        model: PasticceriaModel,
        renderer: PasticceriaRenderer,
        resources,
        active_locale: str,
    ) -> None:
        self._screen = screen
        self._canvas = canvas
        self._metrics = metrics
        self._typography = typography
        self._model = model
        self._renderer = renderer
        self._resources = resources
        self._active_locale = active_locale
        self._theme = get_theme()
        self._sounds = SoundManager()
        try:
            self._storage = get_storage()
        except Exception:
            self._storage = None
        self._running = True
        self._ready_published = False

    # -- public lifecycle --
    def run(self) -> int:
        clock = pygame.time.Clock()
        while self._running and not activity_stop_requested():
            for event in pygame.event.get():
                self.handle_event(event)
            self._step_frame()
            self._draw()
            self._canvas.present(clear=self._theme.background)
            pygame.display.flip()
            if not self._ready_published:
                mark_activity_ready()
                self._ready_published = True
            clock.tick(30)
        self._save_storage()
        return 0

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self._running = False
        elif event.type == pygame.KEYDOWN:
            self.handle_key(event)
        elif event.type == pygame.VIDEORESIZE:
            self.handle_resize(event)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.handle_pointer(event.pos)

    def handle_key(self, event: pygame.event.Event) -> None:
        if event.key == pygame.K_ESCAPE:
            self._running = False
        elif event.key == pygame.K_1:
            self._model.switch_mode("orders")
            self._sounds.play("drop")
        elif event.key == pygame.K_2:
            self._model.switch_mode("patterns")
            self._sounds.play("drop")
        elif event.key == pygame.K_3:
            self._model.switch_mode("free")
            self._sounds.play("drop")

    def handle_resize(self, event: pygame.event.Event) -> None:
        # Reacquire the display surface and rebuild canvas/metrics; renderer invalidates converts.
        self._screen = pygame.display.get_surface() or self._screen
        self._metrics = ChildUiMetrics.for_size(*self._screen.get_size())
        self._canvas = PygameReferenceCanvas(self._screen)
        self._renderer.on_resize()

    def handle_pointer(self, screen_pos: tuple[int, int]) -> None:
        if not _is_safe_point(self._screen, screen_pos):
            return
        logical = self._canvas.pointer(screen_pos)
        if logical is None:
            return
        lx, ly = logical

        # 1. Mode Switcher (Header tabs)
        if 230 <= lx <= 390 and 10 <= ly <= 68:
            self._model.switch_mode("orders")
            self._sounds.play("drop")
            return
        elif 405 <= lx <= 565 and 10 <= ly <= 68:
            self._model.switch_mode("patterns")
            self._sounds.play("drop")
            return
        elif 580 <= lx <= 740 and 10 <= ly <= 68:
            self._model.switch_mode("free")
            self._sounds.play("drop")
            return

        if self._model.mode in {"orders", "free"}:
            # Check if child clicked an existing topping on the cake to REMOVE it
            removed = self._model.remove_at((int(lx), int(ly)))
            if removed is not None:
                tx, ty = removed
                self._sounds.play("drop")
                self._renderer.spawn_at(tx, ty, "✨", GOLD, 8)
                return

            # Check Pantry Shelf clicks
            for idx, (t_id, t_icon, _) in enumerate(TOPPINGS):
                col_idx = idx % 2
                row_idx = idx // 2
                bx = 720 + col_idx * 135
                by = 140 + row_idx * 95
                if bx <= lx <= bx + 125 and by <= ly <= by + 85:
                    placed = self._model.place_topping(t_id)
                    if placed is not None:
                        _, _, px, py = placed
                        self._sounds.play("drop")
                        self._renderer.spawn_at(px, py, "✨", GOLD, 1)
                    break

            # 🧹 Pulisci (Clean) Button
            if 710 <= lx <= 840 and 455 <= ly <= 565:
                self._model.clear_toppings()
                self._sounds.play("drop")
                self._model.feedback_text = ""
                self._model.feedback_timer = 0
                return

            # 🔔 SERVI! Button
            if 850 <= lx <= 1000 and 455 <= ly <= 565:
                self._handle_serve()
                return

        elif self._model.mode == "patterns":
            _, correct_sym, candidates = self._model.current_pattern
            for c_idx, cand_sym in enumerate(candidates):
                cx = 330 + c_idx * 135
                cy = 380
                if cx <= lx <= cx + 110 and cy <= ly <= cy + 110:
                    if cand_sym == correct_sym:
                        self._sounds.play("chime")
                        self._model.apply_correct_pattern()
                        self._renderer.spawn_at(cx + 55, cy + 55, "🌟", GOLD, 20)
                        self._model.feedback_text = self._localized_text("feedback.pattern_correct", "Sequenza completata! 🌟", "Pattern completed! 🌟")
                        self._model.feedback_timer = 2.5
                        self._safe_emit("pattern.solved", f"pat-{time.time()}")
                    else:
                        self._sounds.play("drop")
                        self._model.feedback_text = self._localized_text("feedback.try_again", "Riprova 💕", "Try again 💕")
                        self._model.feedback_timer = 1.5
                    break

    def _localized_text(self, key: str, fallback_it: str, fallback_en: str) -> str:
        if self._resources is not None:
            try:
                return self._resources.text(key)
            except Exception:
                pass
        raw = fallback_it if self._active_locale == "it" else fallback_en
        return display_text(raw)

    def _handle_serve(self) -> None:
        self._sounds.play("ding")
        if self._model.mode == "orders":
            is_correct = self._model.check_order_correct()
            if is_correct:
                self._sounds.play("fanfare")
                # capture before mutate for particle origin consistent
                self._model.apply_correct_order()
                self._renderer.spawn_random_center(["🍰", "✨", "🍓", "💖"], GOLD, 30)
                self._model.feedback_text = self._localized_text("feedback.perfect", "Perfetto! Delizioso! ✨🍰", "Perfect! Delicious! ✨🍰")
                self._model.feedback_timer = 3.0
                self._safe_emit("recipe.completed", f"recipe-{time.time()}")
            else:
                self._sounds.play("drop")
                self._model.feedback_text = self._localized_text("feedback.try_again", "Controlla la ricetta 💕", "Check the recipe 💕")
                self._model.feedback_timer = 2.5
        else:
            self._sounds.play("fanfare")
            self._renderer.spawn_random_center(["✨"], GOLD, 25)
            self._model.feedback_text = self._localized_text("feedback.perfect", "Che capolavoro! ✨", "What a masterpiece! ✨")
            self._model.feedback_timer = 2.5

    def _step_frame(self) -> None:
        # Model feedback tick and renderer particles.
        self._model.tick(0.035)
        self._renderer.update()

    def _draw(self) -> None:
        surf = self._canvas.surface
        self._renderer.render(surf, self._model)

    def _safe_emit(self, ev_id: str, ikey: str, payload: object = None) -> None:
        try:
            emit_activity_event(ev_id, idempotency_key=ikey, payload=payload)
        except Exception:
            pass

    def _save_storage(self) -> None:
        if self._storage is None:
            return
        try:
            data = self._model.to_save_dict()
            data["timestamp"] = time.time()
            self._storage.kv_set(STORAGE_KEY, data)
        except Exception:
            pass


__all__ = ["PasticceriaApp", "SoundManager"]
