"""Storie della Mia Voce — Activity lifecycle and input.

The lifecycle layer is the only place that owns the Activity
state machine, the input dispatch, the platform API access, and
the recorder/playback wiring. State transitions are:

  SCENE_PICKER -> RECORDING -> REPLAY -> SCENE_PICKER
                          -> SCENE_PICKER (back)
  SCENE_PICKER -> LIBRARY (browse) -> SCENE_PICKER (back)
  SCENE_PICKER -> MIC_REQUIRED (no audio.basic granted) -> SCENE_PICKER (back)
  any -> (Back key on system chrome) -> Shell
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Final

import pygame

from greia_platform.activity_api import (
    activity_stop_requested,
    get_audio_capture_device,
    get_sdl_capture_device,
    get_theme,
    mark_activity_ready,
)
from greia_platform.activity_ui import (
    ChildUiMetrics,
    draw_system_chrome_overlay,
    is_home_clicked,
)
from greia_platform.child_text import display_text
from greia_platform.localization import (
    ActivityLocaleSupport,
    LocalizedResources,
    resolve_activity_locale,
)
from greia_platform.typography import FontRole, GreiaTypography

from voice_audio import VoicePlayback
from voice_content import (
    MAX_RECORDING_SECONDS,
    MIN_RECORDING_SECONDS,
    REFERENCE_HEIGHT,
    REFERENCE_WIDTH,
    SCENES,
    SCENE_IDS,
    Scene,
    SceneId,
)
from voice_microphone import VoiceRecorder
from voice_renderer import VoiceRenderer
from voice_services import SavedStory, VoiceEvents, VoiceStorage


class Phase(StrEnum):
    SCENE_PICKER = "scene_picker"
    RECORDING = "recording"
    REPLAY = "replay"
    SAVED = "saved"
    LIBRARY = "library"
    MIC_REQUIRED = "mic_required"


@dataclass
class VoiceApp:
    screen: pygame.Surface
    metrics: ChildUiMetrics
    typography: GreiaTypography
    resources: LocalizedResources
    recorder: VoiceRecorder
    playback: VoicePlayback
    storage: VoiceStorage
    events: VoiceEvents
    renderer: VoiceRenderer
    phase: Phase = Phase.SCENE_PICKER
    current_scene: Scene | None = None
    pending_recordings: dict[str, bytes] = field(default_factory=dict)
    pending_durations: dict[str, float] = field(default_factory=dict)
    recording_start: float = 0.0
    first_story_emitted: bool = False
    ready_published: bool = False
    last_saved_story: SavedStory | None = None
    current_sound: pygame.mixer.Sound | None = None
    current_channel: pygame.mixer.Channel | None = None

    def run(self) -> int:
        clock = pygame.time.Clock()
        running = True
        last_frame = time.monotonic()
        # Decide initial phase based on whether the platform reports a mic
        if not self._has_microphone():
            self.phase = Phase.MIC_REQUIRED
        while running and not activity_stop_requested():
            now = time.monotonic()
            dt = min(0.05, now - last_frame)
            last_frame = now
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                elif event.type == pygame.VIDEORESIZE:
                    self.metrics = ChildUiMetrics.for_size(
                        *self.screen.get_size()
                    )
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if is_home_clicked(self.screen, event.pos):
                        running = False
                        continue
                    self._handle_click(event.pos)
            self._update(dt)
            self._draw()
            pygame.display.flip()
            if not self.ready_published:
                mark_activity_ready()
                self.ready_published = True
            clock.tick(30)
        self._stop_playback()
        self.recorder.stop()  # ensure any in-flight capture is closed
        self.typography.clear()
        pygame.quit()
        return 0

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _has_microphone(self) -> bool:
        if get_sdl_capture_device() is not None:
            return True
        if get_audio_capture_device() is not None:
            return True
        # The recorder also reports available; the development
        # fallback (SDL2 default) is considered a usable mic.
        return self.recorder.available

    def _stop_playback(self) -> None:
        if self.current_channel is not None:
            try:
                self.current_channel.stop()
            except Exception:
                pass
            self.current_channel = None
        self.current_sound = None

    def _handle_click(self, pos: tuple[int, int]) -> None:
        x, y = pos
        if self.phase == Phase.SCENE_PICKER:
            # Library pill (top left)
            if self.renderer.library_btn_rect.collidepoint(x, y):
                self.phase = Phase.LIBRARY
                return
            # Back pill (when in sub-page)
            if self.renderer.back_btn_rect.collidepoint(x, y):
                if self.phase != Phase.SCENE_PICKER:
                    self.phase = Phase.SCENE_PICKER
                return
            # Scene cards
            for i, rect in enumerate(self.renderer.scene_cards):
                if rect.collidepoint(x, y):
                    self.current_scene = SCENES[i]
                    self.phase = Phase.RECORDING
                    self.recorder.start()
                    self.recording_start = time.monotonic()
                    self.events.recording_started(self.current_scene.scene_id)
                    return
        elif self.phase == Phase.RECORDING:
            # Stop is the entire mic area while recording (any tap ends
            # the recording so the child never has to aim for a small
            # button while excited).
            self._stop_recording()
        elif self.phase == Phase.REPLAY:
            # Replay (▶) button
            if self.renderer.replay_btn_rect.collidepoint(x, y):
                self._play_current()
                return
            # Re-record (↺) button
            if self.renderer.rerecord_btn_rect.collidepoint(x, y):
                self._rerecord_current()
                return
            # Back pill (top right)
            if self.renderer.back_btn_rect.collidepoint(x, y):
                self._back_to_picker()
                return
            # "PROSSIMA SCENA" arrow
            if y > REFERENCE_HEIGHT - 90:
                self._next_scene()
                return
        elif self.phase == Phase.SAVED:
            # Library button
            if 140 <= x <= 420 and 460 <= y <= 540:
                self.phase = Phase.LIBRARY
                self.last_saved_story = None
                return
            # New story button
            if REFERENCE_WIDTH - 420 <= x <= REFERENCE_WIDTH - 140 and 460 <= y <= 540:
                self._start_new_story()
                return
        elif self.phase == Phase.LIBRARY:
            # Back pill
            if self.renderer.back_btn_rect.collidepoint(x, y):
                self.phase = Phase.SCENE_PICKER
                return
            # New story button
            if REFERENCE_WIDTH - 240 <= x <= REFERENCE_WIDTH - 40 and 510 <= y <= 580:
                self._start_new_story()
                return
            # Per-story play/delete
            for i, story in enumerate(self.storage._library.stories[:6]):
                col, row = i % 2, i // 2
                rx = 90 + col * 440
                ry = 120 + row * 200
                play_btn = pygame.Rect(rx + 240, ry + 70, 120, 60)
                del_btn = pygame.Rect(rx + 60, ry + 100, 80, 50)
                if play_btn.collidepoint(x, y):
                    self._play_story(story)
                    return
                if del_btn.collidepoint(x, y):
                    self.storage.delete_story(story.story_id)
                    return
        elif self.phase == Phase.MIC_REQUIRED:
            if self.renderer.back_btn_rect.collidepoint(x, y):
                self.phase = Phase.SCENE_PICKER
                return

    def _stop_recording(self) -> None:
        if self.current_scene is None:
            return
        elapsed = time.monotonic() - self.recording_start
        if elapsed < MIN_RECORDING_SECONDS:
            # Too short — discard and re-arm.
            self.recorder.stop()
            self.events.recording_stopped(self.current_scene.scene_id, 0.0)
            return
        wav = self.recorder.stop(gain=1.6)
        if wav is None:
            self.phase = Phase.SCENE_PICKER
            return
        self.pending_recordings[self.current_scene.scene_id] = wav
        self.pending_durations[self.current_scene.scene_id] = elapsed
        self.events.recording_stopped(self.current_scene.scene_id, elapsed)
        self.phase = Phase.REPLAY

    def _rerecord_current(self) -> None:
        if self.current_scene is None:
            return
        sid = self.current_scene.scene_id
        self.pending_recordings.pop(sid, None)
        self.pending_durations.pop(sid, None)
        self._stop_playback()
        self.phase = Phase.RECORDING
        self.recorder.start()
        self.recording_start = time.monotonic()
        self.events.recording_started(sid)

    def _play_current(self) -> None:
        if self.current_scene is None:
            return
        wav = self.pending_recordings.get(self.current_scene.scene_id)
        if not wav:
            return
        self._stop_playback()
        ok = self.playback.play(wav)
        if ok:
            self.events.recording_replayed(self.current_scene.scene_id)

    def _play_story(self, story: SavedStory) -> None:
        self._stop_playback()
        # Play the first scene of the story; the rest is queueable in
        # a later iteration. For now, play one scene at a time on tap.
        first_scene = next(
            (scene for scene in SCENES if scene.scene_id in story.scene_recordings),
            None,
        )
        if first_scene is None:
            return
        wav = story.scene_recordings[first_scene.scene_id]
        if self.playback.play(wav):
            self.events.recording_replayed(first_scene.scene_id)

    def _back_to_picker(self) -> None:
        self._stop_playback()
        self.current_scene = None
        self.phase = Phase.SCENE_PICKER

    def _next_scene(self) -> None:
        self._stop_playback()
        # Save the current story if all 4 scenes recorded; otherwise
        # stay in the picker so the child can come back to finish.
        if len(self.pending_recordings) >= len(SCENES):
            self._save_story()
            return
        # Move to the next unrecorded scene automatically
        recorded = set(self.pending_recordings)
        for scene in SCENES:
            if scene.scene_id not in recorded:
                self.current_scene = scene
                self.phase = Phase.RECORDING
                self.recorder.start()
                self.recording_start = time.monotonic()
                self.events.recording_started(scene.scene_id)
                return
        # All recorded but the user backed out; show saved.
        self._save_story()

    def _save_story(self) -> None:
        story = self.storage.save_story(
            self.pending_recordings, self.pending_durations
        )
        if story is None:
            self.phase = Phase.SCENE_PICKER
            return
        self.events.story_saved(story.story_id, len(story.scene_recordings))
        if not self.first_story_emitted:
            self.first_story_emitted = True
            self.events.first_story_recorded(story.story_id)
        self.last_saved_story = story
        self.pending_recordings = {}
        self.pending_durations = {}
        self.current_scene = None
        self.phase = Phase.SAVED

    def _start_new_story(self) -> None:
        self._stop_playback()
        self.pending_recordings = {}
        self.pending_durations = {}
        self.current_scene = None
        self.last_saved_story = None
        self.phase = Phase.SCENE_PICKER

    # ------------------------------------------------------------------
    # Update + draw
    # ------------------------------------------------------------------

    def _update(self, dt: float) -> None:
        if self.phase == Phase.RECORDING:
            elapsed = time.monotonic() - self.recording_start
            if elapsed >= MAX_RECORDING_SECONDS:
                self._stop_recording()

    def _draw(self) -> None:
        text_fn = self._make_text_fn()
        if self.phase == Phase.SCENE_PICKER:
            self.renderer.draw_scene_picker(text_fn)
        elif self.phase == Phase.RECORDING and self.current_scene is not None:
            remaining = max(
                0.0,
                MAX_RECORDING_SECONDS - (time.monotonic() - self.recording_start),
            )
            self.renderer.draw_recording(
                self.current_scene,
                remaining,
                self.recorder.live_volume,
                text_fn,
            )
        elif self.phase == Phase.REPLAY and self.current_scene is not None:
            duration = self.pending_durations.get(self.current_scene.scene_id, 0.0)
            self.renderer.draw_replay(
                self.current_scene, duration, text_fn,
            )
        elif self.phase == Phase.SAVED and self.last_saved_story is not None:
            self.renderer.draw_saved(self.last_saved_story, text_fn)
        elif self.phase == Phase.LIBRARY:
            self.renderer.draw_library(self.storage._library, text_fn)
        elif self.phase == Phase.MIC_REQUIRED:
            self.renderer.draw_mic_required(text_fn)
        draw_system_chrome_overlay(self.screen)

    def _make_text_fn(self):
        """Return a callable that turns a semantic string into a
        rendered pygame.Surface.

        The caller may pass either a literal string (rendered
        verbatim with the ADR 0034 capitals policy) or a
        semantic key like ``"ui.scene_forest"`` (resolved through
        the localized resources before rendering).
        """
        typography = self.typography
        resources = self.resources

        def _resolve(text: str) -> str:
            if not isinstance(text, str) or not text:
                return text
            # Resolve a semantic key if the resources have it. The
            # key may have been upper-cased by a renderer so always
            # look it up case-insensitively: the resource keys are
            # lower-case semantic ids and the lookup fails otherwise.
            lowered = text.lower()
            if lowered.startswith("ui.") or lowered.startswith("activity."):
                try:
                    return resources.text(lowered)
                except Exception:
                    return text
            return text

        def fn(text: str, color: tuple[int, int, int]) -> pygame.Surface:
            return typography.render(
                display_text(_resolve(text)), FontRole.DISPLAY, 18, color
            )

        return fn


def build_app(
    screen: pygame.Surface,
    locale: str = "it",
    package_root: "Path | None" = None,
) -> VoiceApp:
    """Composition root for the headless launch / simulator gate."""
    pygame.init()
    pygame.display.set_caption("Storie della Mia Voce")
    metrics = ChildUiMetrics.for_size(*screen.get_size())
    theme = get_theme()
    typography = GreiaTypography()
    support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it")
    context = resolve_activity_locale(locale, support)
    if context is None:
        context = resolve_activity_locale("it", support)
    assert context is not None
    from pathlib import Path
    root = package_root or Path(__file__).resolve().parent
    resources = LocalizedResources(root, context)
    recorder = VoiceRecorder()
    playback = VoicePlayback()
    storage = VoiceStorage.load()
    events = VoiceEvents()
    renderer = VoiceRenderer.build(screen)
    return VoiceApp(
        screen=screen,
        metrics=metrics,
        typography=typography,
        resources=resources,
        recorder=recorder,
        playback=playback,
        storage=storage,
        events=events,
        renderer=renderer,
    )
