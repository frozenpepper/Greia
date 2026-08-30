"""Orchestra Animali — Activity lifecycle.

Owns screen/canvas/metrics/typography, the domain state (instruments,
particles, timers), the renderer, audio and platform input dispatch.
READY is published after the first ``_draw``/``flip`` in the same
presentation loop, matching the platform readiness invariant.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

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
from greia_platform.localization import (
    ActivityLocaleSupport,
    LocalizedResources,
    resolve_activity_locale,
)
from greia_platform.pygame_canvas import (
    PygameReferenceCanvas,
    activity_viewport_for_surface,
)
from greia_platform.typography import GreiaTypography

if __package__:
    from .orchestra_audio import SoundManager
    from .orchestra_content import (
        NOTE_NAMES_EN,
        NOTE_NAMES_IT,
        RAINBOW_COLORS,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        STAGE_GOLD,
        STORAGE_KEY,
    )
    from .orchestra_model import InstrumentCard, Particle
    from .orchestra_renderer import OrchestraRenderer
else:  # pragma: no cover - runtime/script fallback
    from orchestra_audio import SoundManager
    from orchestra_content import (
        NOTE_NAMES_EN,
        NOTE_NAMES_IT,
        RAINBOW_COLORS,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        STAGE_GOLD,
        STORAGE_KEY,
    )
    from orchestra_model import InstrumentCard, Particle
    from orchestra_renderer import OrchestraRenderer


def _is_safe_point(surface: pygame.Surface, position: tuple[int, int]) -> bool:
    vp = activity_viewport_for_surface(surface)
    x, y = position
    if not (0 <= x < vp.surface.width and 0 <= y < vp.surface.height):
        return False
    for protected in vp.protected_regions:
        if protected.x <= x < protected.right and protected.y <= y < protected.bottom:
            return False
    return True


@dataclass
class OrchestraApp:
    """Lifecycle owner for orchestra_animali."""

    screen: pygame.Surface
    canvas: PygameReferenceCanvas
    metrics: ChildUiMetrics
    typography: GreiaTypography
    audio: SoundManager = field(default_factory=SoundManager)
    renderer: OrchestraRenderer | None = None
    storage: Any | None = None
    is_it: bool = True
    note_labels: list[str] = field(default_factory=list)
    instruments: list[InstrumentCard] = field(default_factory=list)
    particles: list[Particle] = field(default_factory=list)
    key_highlight_timers: list[float] = field(default_factory=lambda: [0.0] * 8)
    stars: int = 0
    ready_published: bool = False
    clock: pygame.time.Clock = field(default_factory=pygame.time.Clock)
    _running: bool = True

    def __post_init__(self) -> None:
        if self.renderer is None:
            self.renderer = OrchestraRenderer(self.typography)
        if not self.note_labels:
            self.note_labels = NOTE_NAMES_IT if self.is_it else NOTE_NAMES_EN
        if not self.instruments:
            self.instruments = [
                InstrumentCard("piano", "🎹", "Pianoforte", "Piano", "piano", 150, 230, (59, 130, 246)),
                InstrumentCard("drums", "🥁", "Batteria", "Drums", "drums", 330, 210, (239, 68, 68)),
                InstrumentCard("trumpet", "🎺", "Tromba", "Trumpet", "trumpet", 512, 230, (234, 179, 8)),
                InstrumentCard("guitar", "🎸", "Chitarra", "Guitar", "guitar", 694, 210, (249, 115, 22)),
                InstrumentCard("maracas", "🪇", "Maracas", "Maracas", "maracas", 874, 230, (34, 197, 94)),
            ]
        if self.storage is None:
            try:
                self.storage = get_storage()
            except Exception:
                self.storage = None
        try:
            self._load_stars()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load_stars(self) -> None:
        if self.storage is None:
            return
        try:
            saved = self.storage.kv_get(STORAGE_KEY, {})
        except Exception:
            return
        if isinstance(saved, dict):
            try:
                self.stars = int(saved.get("stars", 0))
            except Exception:
                pass

    def _autosave(self) -> None:
        if self.storage is None:
            return
        try:
            self.storage.kv_set(STORAGE_KEY, {"stars": self.stars})
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Event dispatch
    # ------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self._running = False
        elif event.type == pygame.KEYDOWN:
            self._handle_keydown(event.key)
        elif event.type == pygame.VIDEORESIZE:
            self._handle_resize()
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if not _is_safe_point(self.screen, event.pos):
                return
            logical = self.canvas.pointer(event.pos)
            if logical is None:
                return
            lx, ly = logical
            for inst in self.instruments:
                if inst.contains(lx, ly):
                    inst.trigger()
                    self.audio.play_inst(inst.sound_name)
                    self.stars += 2
                    for _ in range(12):
                        self.particles.append(
                            Particle(inst.x, inst.y - 20, random.choice(["🎵", "🎶", "✨", "⭐"]), STAGE_GOLD)
                        )
                    self._safe_emit("instrument.played", f"inst-{time.time()}", payload={"instrument": inst.inst_id})
            for k_i in range(8):
                kx = 64 + k_i * 112
                if kx <= lx <= kx + 104 and 440 <= ly <= 570:
                    self._trigger_piano_key(k_i)

    def _handle_keydown(self, key: int) -> None:
        if key == pygame.K_ESCAPE:
            self._running = False
            return
        key_map = {
            pygame.K_1: 0,
            pygame.K_2: 1,
            pygame.K_3: 2,
            pygame.K_4: 3,
            pygame.K_5: 4,
            pygame.K_6: 5,
            pygame.K_7: 6,
            pygame.K_8: 7,
            pygame.K_a: 0,
            pygame.K_s: 1,
            pygame.K_d: 2,
            pygame.K_f: 3,
            pygame.K_g: 4,
            pygame.K_h: 5,
            pygame.K_j: 6,
            pygame.K_k: 7,
        }
        if key in key_map:
            self._trigger_piano_key(key_map[key])

    def _handle_resize(self) -> None:
        new_screen = pygame.display.get_surface() or self.screen
        self.screen = new_screen
        self.metrics = ChildUiMetrics.for_size(*new_screen.get_size())
        self.canvas = PygameReferenceCanvas(new_screen)
        if self.renderer is not None:
            self.renderer.invalidate_background()

    def _trigger_piano_key(self, k_idx: int) -> None:
        if 0 <= k_idx < 8:
            self.audio.play_note(k_idx)
            self.key_highlight_timers[k_idx] = 1.0
            self.stars += 1
            kx = 64 + k_idx * 112
            for _ in range(8):
                self.particles.append(
                    Particle(kx + 52, 460, random.choice(["🎵", "🎶", "♪", "♫"]), RAINBOW_COLORS[k_idx])
                )
            self._safe_emit("instrument.played", f"note-{time.time()}", payload={"note": k_idx})

    def _safe_emit(self, ev_id: str, ikey: str, payload: object = None) -> None:
        try:
            emit_activity_event(ev_id, idempotency_key=ikey, payload=payload)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Per-frame update
    # ------------------------------------------------------------------

    def _update_state(self) -> None:
        for inst in self.instruments:
            inst.update()
        for i in range(8):
            if self.key_highlight_timers[i] > 0:
                self.key_highlight_timers[i] -= 0.05
        self.particles = [p for p in self.particles if p.update()]

    # ------------------------------------------------------------------
    # Rendering — one present + one flip per frame
    # ------------------------------------------------------------------

    def _draw(self) -> None:
        assert self.renderer is not None
        surf = self.canvas.surface
        self.renderer.draw_background(surf)
        self.renderer.draw_instruments(surf, self.instruments, self.is_it)
        self.renderer.draw_particles(surf, self.particles)
        self.renderer.draw_piano_keys(surf, self.key_highlight_timers, self.note_labels)
        self.renderer.draw_hud(surf, self.stars, self.is_it)
        theme = get_theme()
        try:
            bg = theme.background
        except Exception:
            bg = (10, 10, 20)
        self.canvas.present(clear=bg)
        pygame.display.flip()

    def _step_frame(self) -> None:
        """Advance one frame without lifecycle signalling.

        The platform READY is published by :meth:`run` after the first
        ``_draw``/``flip`` in the same presentation loop, so this helper
        stays free of lifecycle authority and remains usable from tests.
        """

        self._update_state()
        self._draw()
        self.clock.tick(60)

    def run(self) -> int:
        while self._running and not activity_stop_requested():
            for event in pygame.event.get():
                self.handle_event(event)
                if not self._running:
                    break
            if not self._running:
                break
            self._update_state()
            self._draw()
            if not self.ready_published:
                mark_activity_ready()
                self.ready_published = True
            self.clock.tick(60)
        self._autosave()
        return 0


def build_app(
    screen: pygame.Surface,
    *,
    storage: Any | None = None,
    is_it: bool | None = None,
) -> OrchestraApp:
    """Composition helper for the thin bootstrap and tests."""
    metrics = ChildUiMetrics.for_size(*screen.get_size())
    canvas = PygameReferenceCanvas(screen)
    typography = GreiaTypography()
    renderer = OrchestraRenderer(typography)
    audio = SoundManager()
    if is_it is None:
        try:
            support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it")
            ctx = resolve_activity_locale(get_profile_locale(), support)
            is_it = (ctx.selected.language == "it") if ctx else True
        except Exception:
            is_it = True
    if storage is None:
        try:
            storage = get_storage()
        except Exception:
            storage = None
    return OrchestraApp(
        screen=screen,
        canvas=canvas,
        metrics=metrics,
        typography=typography,
        audio=audio,
        renderer=renderer,
        storage=storage,
        is_it=is_it,
    )


__all__ = ["OrchestraApp", "_is_safe_point", "build_app"]
