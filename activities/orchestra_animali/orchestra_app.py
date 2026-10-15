"""Orchestra Animali — Activity lifecycle.

Owns screen/canvas/metrics/typography, the domain state (instruments,
particles, timers), the renderer, audio and platform input dispatch.
READY is published after the first ``_draw``/``flip`` in the same
presentation loop, matching the platform readiness invariant.
"""

from __future__ import annotations

import hashlib
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pygame

from greia_platform.activity_api import (
    activity_stop_requested,
    emit_activity_event,
    get_creations,
    get_storage,
    get_theme,
    mark_activity_ready,
)
from greia_platform.activity_ui import ChildUiMetrics
from greia_platform.localization import (
    LocalizationError,
    LocalizedResources,
    activity_resources,
)
from greia_platform.pygame_canvas import (
    PygameReferenceCanvas,
    activity_viewport_for_surface,
)
from greia_platform.typography import GreiaTypography

if __package__:
    from .orchestra_audio import BackingTrackPlayer, ImportedBackingTrack, SoundManager
    from .orchestra_backing import (
        SUPPORTED_BACKING_ROLES,
        BackingTrackRecord,
        BackingTrackRepository,
        BackingTrackStoreError,
    )
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
    from orchestra_audio import BackingTrackPlayer, ImportedBackingTrack, SoundManager
    from orchestra_backing import (
        SUPPORTED_BACKING_ROLES,
        BackingTrackRecord,
        BackingTrackRepository,
        BackingTrackStoreError,
    )
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


_NOTE_STEPS = ("c", "d", "e", "f", "g", "a", "b", "c_high")


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
    creations: Any | None = None
    backing_store: BackingTrackRepository | None = None
    backing_player: BackingTrackPlayer = field(default_factory=BackingTrackPlayer)
    backing_record: BackingTrackRecord | None = None
    backing_request: str | None = None
    backing_next_poll: float = 0.0
    backing_import_state: str = ""
    backing_feedback_until: float = 0.0
    backing_notes_played: int = 0
    resources: LocalizedResources | None = None
    is_it: bool = True
    title: str = ""
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
            self.note_labels = self._resolve_note_labels()
        if not self.instruments:
            self.instruments = [
                InstrumentCard("piano", "🎹", "piano", 150, 230, (59, 130, 246), self._label("inst.piano")),
                InstrumentCard("drums", "🥁", "drums", 330, 210, (239, 68, 68), self._label("inst.drums")),
                InstrumentCard("trumpet", "🎺", "trumpet", 512, 230, (234, 179, 8), self._label("inst.trumpet")),
                InstrumentCard("guitar", "🎸", "guitar", 694, 210, (249, 115, 22), self._label("inst.guitar")),
                InstrumentCard("maracas", "🪇", "maracas", 874, 230, (34, 197, 94), self._label("inst.maracas")),
            ]
        if not self.title:
            self.title = self._label("hud.title")
        if self.storage is None:
            try:
                self.storage = get_storage()
            except Exception:
                self.storage = None
        if self.creations is None:
            try:
                self.creations = get_creations()
            except RuntimeError:
                self.creations = None
        if self.backing_store is None and self.storage is not None:
            self.backing_store = BackingTrackRepository(self.storage)
        try:
            self._load_stars()
        except Exception:
            pass
        self._load_backing_track()

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

    def _load_backing_track(self) -> None:
        store = self.backing_store
        if store is None:
            return
        try:
            loaded = store.load()
        except BackingTrackStoreError:
            return
        if loaded is None:
            return
        record, payload = loaded
        try:
            track = ImportedBackingTrack.from_wav(payload)
        except ValueError:
            return
        if abs(track.duration_seconds - record.duration_seconds) > 0.05:
            return
        self.backing_record = record
        self.backing_player.load(track)

    def _request_backing_track(self) -> None:
        if (
            self.creations is None
            or self.backing_store is None
            or self.backing_request is not None
        ):
            return
        # The trusted picker owns audio preview while visible. Never let an
        # Orchestra backing track compete with Play/Pause/Replay in the picker.
        self.backing_player.stop()
        self.backing_notes_played = 0
        try:
            request_id = self.creations.request_selection(
                media_types=("audio/wav",),
                roles=("narration", "song", "music"),
            )
        except (RuntimeError, ValueError, OSError):
            self.backing_import_state = "error"
            self.backing_feedback_until = time.monotonic() + 2.0
            return
        self.backing_request = request_id
        self.backing_import_state = "pending"
        self.backing_next_poll = time.monotonic() + 0.12

    def _poll_backing_track(self, now: float) -> None:
        request_id = self.backing_request
        if (
            request_id is None
            or self.creations is None
            or now < self.backing_next_poll
        ):
            return
        self.backing_next_poll = now + 0.12
        try:
            result = self.creations.poll_selection(request_id)
        except (RuntimeError, ValueError, OSError):
            self.backing_request = None
            self.backing_import_state = "error"
            self.backing_feedback_until = now + 2.0
            return
        if result.state == "pending":
            return
        self.backing_request = None
        if result.state == "cancelled":
            self.backing_import_state = ""
            return
        token = result.selection_token
        if (
            result.state != "ready"
            or not isinstance(token, str)
            or not token
            or not self._accept_backing_track(token)
        ):
            self.backing_import_state = "error"
            self.backing_feedback_until = now + 2.0
            return
        self.backing_import_state = "imported"
        self.backing_feedback_until = now + 2.0

    def _accept_backing_track(self, selection_token: str) -> bool:
        if self.creations is None or self.backing_store is None:
            return False
        try:
            transfer = self.creations.import_selected(selection_token)
            payload = transfer.payload
            role = transfer.record.get("role")
            if (
                transfer.record.get("media_type") != "audio/wav"
                or role not in SUPPORTED_BACKING_ROLES
                or not isinstance(payload, bytes)
                or transfer.record.get("sha256")
                != hashlib.sha256(payload).hexdigest()
            ):
                raise ValueError("selected backing track failed integrity validation")
            track = ImportedBackingTrack.from_wav(payload)
            title_raw = transfer.record.get("title", "")
            title = title_raw if isinstance(title_raw, str) else ""
            record = self.backing_store.save(
                track.wav_bytes,
                role=role,
                title=title,
                duration_seconds=track.duration_seconds,
            )
        except (
            BackingTrackStoreError,
            RuntimeError,
            ValueError,
            OSError,
        ):
            return False
        self.backing_record = record
        self.backing_player.load(track)
        self.backing_notes_played = 0
        return True

    def _toggle_backing_track(self) -> None:
        previous = self.backing_player.state
        state = self.backing_player.toggle()
        if state == "playing" and previous == "ready":
            self.backing_notes_played = 0
        elif state == "error":
            self.backing_import_state = "error"
            self.backing_feedback_until = time.monotonic() + 2.0

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
            point = (int(lx), int(ly))
            assert self.renderer is not None
            if (
                self.creations is not None
                and self.backing_store is not None
                and self.renderer.backing_import_contains(point)
            ):
                self._request_backing_track()
                return
            if self.renderer.backing_play_contains(point):
                self._toggle_backing_track()
                return
            for inst in self.instruments:
                if inst.contains(lx, ly):
                    inst.trigger()
                    self.audio.play_inst(inst.sound_name)
                    self.stars += 2
                    for _ in range(12):
                        self.particles.append(
                            Particle(inst.x, inst.y - 20, random.choice(["🎵", "🎶", "✨", "⭐"]), STAGE_GOLD)
                        )
                    if self.backing_player.state == "playing":
                        self.backing_notes_played += 1
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
            if self.backing_player.state == "playing":
                self.backing_notes_played += 1
            self._safe_emit("instrument.played", f"note-{time.time()}", payload={"note": k_idx})

    def _safe_emit(self, ev_id: str, ikey: str, payload: object = None) -> None:
        try:
            emit_activity_event(ev_id, idempotency_key=ikey, payload=payload)
        except Exception:
            pass

    def _label(self, key: str) -> str:
        """Resolve one caption once at construction; empty means pictogram only."""
        if self.resources is None:
            return ""
        try:
            return self.resources.text(key).strip()
        except LocalizationError:
            return ""

    def _resolve_note_labels(self) -> list[str]:
        """Note names come from the locale bundle (letters vs solfege)."""
        fallback = NOTE_NAMES_IT if self.is_it else NOTE_NAMES_EN
        labels = [self._label(f"note.{step}") for step in _NOTE_STEPS]
        return labels if all(labels) else list(fallback)

    # ------------------------------------------------------------------
    # Per-frame update
    # ------------------------------------------------------------------

    def _update_state(self) -> None:
        now = time.monotonic()
        self._poll_backing_track(now)
        if (
            self.backing_import_state
            and self.backing_import_state != "pending"
            and now >= self.backing_feedback_until
        ):
            self.backing_import_state = ""
        if self.backing_player.refresh():
            if self.backing_notes_played > 0:
                self._safe_emit(
                    "concert.performed",
                    f"concert-{time.time()}",
                    payload={"live_inputs": self.backing_notes_played},
                )
            self.backing_notes_played = 0
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
        self.renderer.draw_instruments(surf, self.instruments)
        self.renderer.draw_particles(surf, self.particles)
        self.renderer.draw_piano_keys(surf, self.key_highlight_timers, self.note_labels)
        self.renderer.draw_hud(
            surf,
            self.stars,
            title=self.title,
            backing_enabled=self.backing_player.track is not None,
            backing_state=self.backing_player.state,
            backing_import_enabled=(
                self.creations is not None and self.backing_store is not None
            ),
            backing_import_state=self.backing_import_state,
        )
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
        try:
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
        finally:
            self.backing_player.stop()
            self._autosave()
        return 0


def build_app(
    screen: pygame.Surface,
    *,
    storage: Any | None = None,
    creations: Any | None = None,
    is_it: bool | None = None,
) -> OrchestraApp:
    """Composition helper for the thin bootstrap and tests."""
    metrics = ChildUiMetrics.for_size(*screen.get_size())
    canvas = PygameReferenceCanvas(screen)
    typography = GreiaTypography()
    renderer = OrchestraRenderer(typography)
    audio = SoundManager()
    resources: LocalizedResources | None
    try:
        resources = activity_resources(Path(__file__).resolve().parent)
    except (LocalizationError, OSError):
        resources = None
    if is_it is None:
        is_it = resources is None or resources.context.selected.language == "it"
    if storage is None:
        try:
            storage = get_storage()
        except Exception:
            storage = None
    if creations is None:
        try:
            creations = get_creations()
        except RuntimeError:
            creations = None
    return OrchestraApp(
        screen=screen,
        canvas=canvas,
        metrics=metrics,
        typography=typography,
        audio=audio,
        renderer=renderer,
        storage=storage,
        creations=creations,
        resources=resources,
        is_it=is_it,
    )


__all__ = ["OrchestraApp", "_is_safe_point", "build_app"]
