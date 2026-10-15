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
from greia_platform.activity_controls import (
    ControlKit,
    ControlLayout,
    ControlTheme,
    KitPointer,
    PointerPhase,
    PygameControlInput,
)
from greia_platform.activity_feedback import CastFeedback
from greia_platform.activity_ui import ChildUiMetrics
from greia_platform.ui_core import SurfaceNavigator, UiEventResult
from greia_platform.localization import (
    ActivityLocaleSupport,
    LocalizationError,
    LocalizedResources,
    resolve_activity_locale,
)
from greia_platform.pygame_canvas import PygameReferenceCanvas, activity_viewport_for_surface
from greia_platform.typography import GreiaTypography

if __package__:
    from .pasticceria_content import CAKE_SLOTS, GOLD, REFERENCE_HEIGHT, REFERENCE_WIDTH, STORAGE_KEY, TOPPINGS
    from .pasticceria_controls import CANDIDATE_RECTS, CAST_HEIGHT, CAST_MIDBOTTOM, PasticceriaControls
    from .pasticceria_model import PasticceriaModel
    from .pasticceria_renderer import PasticceriaRenderer
else:
    from pasticceria_content import CAKE_SLOTS, GOLD, REFERENCE_HEIGHT, REFERENCE_WIDTH, STORAGE_KEY, TOPPINGS
    from pasticceria_controls import CANDIDATE_RECTS, CAST_HEIGHT, CAST_MIDBOTTOM, PasticceriaControls
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
    routing. Delegates rules to the pure model, scene presentation to the
    renderer and every interactive control to the shared control kit
    (ADR 0037), so tabs, pantry, Clear/Serve and pattern answers work with
    pointer, touch, keyboard and controller alike. Publishes READY after
    the first flip in the same loop.
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
        *,
        kit: ControlKit | None = None,
        clock=time.monotonic,
    ) -> None:
        self._screen = screen
        self._canvas = canvas
        self._metrics = metrics
        self._typography = typography
        self._model = model
        self._renderer = renderer
        self._resources = resources
        self._theme = get_theme()
        self._sounds = SoundManager()
        try:
            self._storage = get_storage()
        except Exception:
            self._storage = None
        self._running = True
        self._ready_published = False

        # Shared control kit: primary Collection "learn" -> orange accent.
        self._kit = kit if kit is not None else ControlKit(typography, ControlTheme.for_accent("orange"))
        self._cast = CastFeedback("momo", height=CAST_HEIGHT, art=self._kit.art, clock=clock)
        self._controls = PasticceriaControls(
            self._kit,
            resources,
            ControlLayout.for_canvas(canvas, screen.get_size()),
            mode=model.mode,
            on_mode=self._select_mode,
            on_topping=self._place_topping,
            on_candidate=self._choose_candidate,
            on_clear=self._clear_cake,
            on_serve=self._handle_serve,
        )
        self._surfaces = SurfaceNavigator(self._controls.layer)
        self._input = PygameControlInput(
            to_logical=self._canvas_pointer,
            is_safe=lambda pos: _is_safe_point(self._screen, pos),
        )

    @property
    def controls(self) -> PasticceriaControls:
        return self._controls

    # -- public lifecycle --
    def run(self) -> int:
        clock = pygame.time.Clock()
        while self._running and not activity_stop_requested():
            for event in pygame.event.get():
                self.handle_event(event)
            repeat = self._input.poll()
            if repeat is not None:
                self._surfaces.dispatch(repeat)
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
            return
        if event.type == pygame.KEYDOWN and self.handle_key(event):
            return
        if event.type == pygame.VIDEORESIZE:
            self.handle_resize(event)
            return
        translated = self._input.translate(event)
        if translated is None:
            return
        result = self._surfaces.dispatch(translated)
        if (
            result is UiEventResult.IGNORED
            and isinstance(translated, KitPointer)
            and translated.phase is PointerPhase.UP
        ):
            self._cake_tap(translated.position)

    def handle_key(self, event: pygame.event.Event) -> bool:
        """Handle Activity shortcut keys; True when consumed."""
        if event.key == pygame.K_ESCAPE:
            self._running = False
            return True
        shortcuts = {pygame.K_1: "orders", pygame.K_2: "patterns", pygame.K_3: "free"}
        mode = shortcuts.get(event.key)
        if mode is not None:
            self._select_mode(mode)
            return True
        return False

    def handle_resize(self, event: pygame.event.Event) -> None:
        # Reacquire the display surface and rebuild canvas/metrics; renderer invalidates converts.
        self._screen = pygame.display.get_surface() or self._screen
        self._metrics = ChildUiMetrics.for_size(*self._screen.get_size())
        self._canvas = PygameReferenceCanvas(self._screen)
        self._renderer.on_resize()
        self._controls.relayout(ControlLayout.for_canvas(self._canvas, self._screen.get_size()))

    def handle_pointer(self, screen_pos: tuple[int, int]) -> None:
        """Deliver one complete tap at a physical position (tests/tools)."""
        if not _is_safe_point(self._screen, screen_pos):
            return
        logical = self._canvas.pointer(screen_pos)
        if logical is None:
            return
        point = (int(logical[0]), int(logical[1]))
        if not self._controls.layer.tap(point):
            self._cake_tap(point)

    def _canvas_pointer(self, position: tuple[int, int]) -> tuple[float, float] | None:
        return self._canvas.pointer(position)

    # -- control callbacks --
    def _select_mode(self, mode: str) -> None:
        self._model.switch_mode(mode)
        self._controls.sync_mode(self._model.mode)
        self._sounds.play("drop")

    def _place_topping(self, topping_id: str) -> None:
        placed = self._model.place_topping(topping_id)
        if placed is not None:
            _, _, px, py = placed
            self._sounds.play("drop")
            self._renderer.spawn_at(px, py, "✨", GOLD, 1)

    def _clear_cake(self) -> None:
        self._model.clear_toppings()
        self._sounds.play("drop")
        self._model.feedback_text = ""
        self._model.feedback_timer = 0

    def _choose_candidate(self, index: int) -> None:
        if self._model.mode != "patterns":
            return
        _, correct_sym, candidates = self._model.current_pattern
        if not 0 <= index < len(candidates):
            return
        rect = CANDIDATE_RECTS[index]
        if candidates[index] == correct_sym:
            self._sounds.play("chime")
            self._model.apply_correct_pattern()
            self._renderer.spawn_at(rect.centerx, rect.centery, "🌟", GOLD, 20)
            self._model.feedback_text = self._localized_text("feedback.pattern_correct", "🌟")
            self._model.feedback_timer = 2.5
            self._cast.correct()
            self._safe_emit("pattern.solved", f"pat-{time.time()}")
        else:
            self._sounds.play("drop")
            self._model.feedback_text = self._localized_text("feedback.try_again", "💕")
            self._model.feedback_timer = 1.5
            self._cast.try_again()

    def _cake_tap(self, logical: tuple[int, int]) -> None:
        """Tap on a placed topping removes it (orders/free modes only)."""
        if self._model.mode not in {"orders", "free"}:
            return
        removed = self._model.remove_at((int(logical[0]), int(logical[1])))
        if removed is not None:
            tx, ty = removed
            self._sounds.play("drop")
            self._renderer.spawn_at(tx, ty, "✨", GOLD, 8)

    def _localized_text(self, key: str, neutral: str) -> str:
        """Resolve feedback copy; without it only the pictogram is shown."""
        if self._resources is not None:
            try:
                return self._resources.text(key)
            except LocalizationError:
                pass
        return neutral

    def _handle_serve(self) -> None:
        self._sounds.play("ding")
        if self._model.mode == "orders":
            is_correct = self._model.check_order_correct()
            if is_correct:
                self._sounds.play("fanfare")
                # capture before mutate for particle origin consistent
                self._model.apply_correct_order()
                self._renderer.spawn_random_center(["🍰", "✨", "🍓", "💖"], GOLD, 30)
                self._model.feedback_text = self._localized_text("feedback.perfect", "✨🍰")
                self._model.feedback_timer = 3.0
                self._cast.correct()
                self._safe_emit("recipe.completed", f"recipe-{time.time()}")
            else:
                self._sounds.play("drop")
                self._model.feedback_text = self._localized_text("feedback.try_again", "💕")
                self._model.feedback_timer = 2.5
                self._cast.try_again()
        else:
            self._sounds.play("fanfare")
            self._renderer.spawn_random_center(["✨"], GOLD, 25)
            self._model.feedback_text = self._localized_text("feedback.masterpiece", "✨")
            self._model.feedback_timer = 2.5
            self._cast.correct()

    def _step_frame(self) -> None:
        # Model feedback tick, cast reaction and renderer particles.
        self._model.tick(0.035)
        self._cast.update()
        self._renderer.update()

    def _draw(self) -> None:
        surf = self._canvas.surface
        self._renderer.render(surf, self._model)
        self._controls.sync(self._model)
        self._cast.draw(surf, CAST_MIDBOTTOM)
        self._surfaces.draw(surf)
        self._renderer.render_effects(surf)

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
