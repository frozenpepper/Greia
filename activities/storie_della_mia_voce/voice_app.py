"""Storie della Mia Voce — Activity lifecycle and input.

The lifecycle layer is the only place that owns the Activity
state machine, the input dispatch, the platform API access, and
the recorder/playback wiring. State transitions are:

  SCENE_PICKER -> RECORDING -> REPLAY -> SCENE_PICKER
                          -> SCENE_PICKER (back)
  SCENE_PICKER -> LIBRARY (browse) -> SCENE_PICKER (back)
  SCENE_PICKER -> MIC_REQUIRED (no audio.basic granted) -> SCENE_PICKER (back)
  any -> Greia platform Home/Back -> Shell
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
    get_creations,
    get_sdl_capture_device,
    get_theme,
    mark_activity_ready,
)
from greia_platform.activity_ui import ChildUiMetrics
from greia_platform.localization import LocalizedResources, activity_resources
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
from voice_services import DeleteConfirmation, SavedStory, VoiceEvents, VoiceStorage, VoiceStorageError


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
    creations: object | None = None
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
    library_page: int = 0
    shared_scene_keys: set[tuple[str, str]] = field(default_factory=set)
    share_feedback: tuple[str, str, str] | None = None
    share_feedback_until: float = 0.0
    save_error_until: float = 0.0
    delete_confirm: DeleteConfirmation | None = None

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
                    if self.delete_confirm is not None:
                        self._handle_delete_key(event.key)
                    elif event.key == pygame.K_ESCAPE:
                        running = False
                elif event.type == pygame.VIDEORESIZE:
                    self.metrics = ChildUiMetrics.for_size(
                        *self.screen.get_size()
                    )
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
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

    # -- deliberate delete ----------------------------------------------------

    def _request_delete(self, story: SavedStory) -> None:
        """Open the confirmation dialog; nothing is removed by this call."""
        self.delete_confirm = DeleteConfirmation(story.story_id, time.monotonic())

    def _resolve_delete(self, choice: str) -> None:
        """Apply the child's choice in the dialog (keep is always safe)."""
        confirm = self.delete_confirm
        if confirm is None:
            return
        outcome = confirm.resolve(choice, time.monotonic())
        if outcome is None:
            return  # delete pressed before the dialog armed: ignore
        self.delete_confirm = None
        if outcome != DeleteConfirmation.DELETE:
            return
        if self.storage.delete_story(confirm.target_id):
            self.shared_scene_keys = {
                key for key in self.shared_scene_keys if key[0] != confirm.target_id
            }
            max_page = max(0, (self.storage._library.count - 1) // 4)
            self.library_page = min(self.library_page, max_page)

    def _handle_delete_key(self, key: int) -> None:
        """Arrows/D-pad move between the two buttons; Space/Enter/south
        activate the focused one (initially keep); Escape keeps the story."""
        confirm = self.delete_confirm
        if confirm is None:
            return
        if key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN, pygame.K_TAB):
            confirm.move_focus()
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self._resolve_delete(confirm.focus)
        elif key == pygame.K_ESCAPE:
            self._resolve_delete(DeleteConfirmation.KEEP)

    def _handle_delete_click(self, pos: tuple[int, int]) -> None:
        layout = self.renderer.delete_dialog_layout()
        if layout["delete"].collidepoint(pos):
            self._resolve_delete(DeleteConfirmation.DELETE)
        elif layout["keep"].collidepoint(pos) or not layout["box"].collidepoint(pos):
            # Tapping outside the dialog also keeps the story.
            self._resolve_delete(DeleteConfirmation.KEEP)

    def _handle_click(self, pos: tuple[int, int]) -> None:
        if self.delete_confirm is not None:
            self._handle_delete_click(pos)
            return
        x, y = pos
        if self.phase == Phase.SCENE_PICKER:
            # Library pill (top left)
            if self.renderer.library_btn_rect.collidepoint(x, y):
                self.library_page = 0
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
                self.library_page = 0
                self.phase = Phase.LIBRARY
                self.last_saved_story = None
                return
            # New story button
            if REFERENCE_WIDTH - 420 <= x <= REFERENCE_WIDTH - 140 and 460 <= y <= 540:
                self._start_new_story()
                return
        elif self.phase == Phase.LIBRARY:
            if self.renderer.back_btn_rect.collidepoint(x, y):
                self.phase = Phase.SCENE_PICKER
                return

            stories = self.storage._library.stories
            max_page = max(0, (len(stories) - 1) // 4)
            if (
                self.renderer.library_prev_rect().collidepoint(x, y)
                and self.library_page > 0
            ):
                self.library_page -= 1
                return
            if (
                self.renderer.library_next_rect().collidepoint(x, y)
                and self.library_page < max_page
            ):
                self.library_page += 1
                return
            if self.renderer.library_new_rect().collidepoint(x, y):
                self._start_new_story()
                return

            start = self.library_page * 4
            visible = stories[start : start + 4]
            for local_index, story in enumerate(visible):
                if self.creations is not None:
                    for scene_index, scene in enumerate(SCENES):
                        share_rect = self.renderer.library_scene_share_rect(
                            local_index, scene_index
                        )
                        if (
                            share_rect.collidepoint(x, y)
                            and scene.scene_id in story.scene_recordings
                        ):
                            self._share_scene(story, scene)
                            return

                if self.renderer.library_play_rect(local_index).collidepoint(x, y):
                    self._play_story(story)
                    return
                if self.renderer.library_delete_rect(local_index).collidepoint(x, y):
                    self._request_delete(story)
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

    def _share_scene(self, story: SavedStory, scene: Scene) -> None:
        if self.creations is None:
            return
        scene_id = str(scene.scene_id)
        key = (story.story_id, scene_id)
        if key in self.shared_scene_keys:
            self.share_feedback = (story.story_id, scene_id, "saved")
            self.share_feedback_until = time.monotonic() + 2.0
            return
        try:
            filename = self.storage.private_scene_wav_name(
                story, scene_id
            )
            story_label = self.resources.text("ui.story")
            scene_label = self.resources.text(scene.label_key)
            self.creations.publish_private_file(
                filename,
                media_type="audio/wav",
                role="narration",
                title=f"{story_label} — {scene_label}"[:100],
            )
        except (RuntimeError, ValueError, OSError):
            self.share_feedback = (story.story_id, scene_id, "error")
            self.share_feedback_until = time.monotonic() + 2.0
            return
        self.shared_scene_keys.add(key)
        self.share_feedback = (story.story_id, scene_id, "saved")
        self.share_feedback_until = time.monotonic() + 2.0

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
        try:
            story = self.storage.save_story(
                self.pending_recordings, self.pending_durations
            )
        except (VoiceStorageError, ValueError, OSError):
            self.save_error_until = time.monotonic() + 2.5
            self.phase = Phase.REPLAY
            return
        if story is None:
            self.save_error_until = time.monotonic() + 2.5
            self.phase = Phase.REPLAY
            return
        self.save_error_until = 0.0
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
        now = time.monotonic()
        if (
            self.share_feedback is not None
            and now >= self.share_feedback_until
        ):
            self.share_feedback = None
        if self.phase == Phase.RECORDING:
            elapsed = now - self.recording_start
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
                self.current_scene,
                duration,
                text_fn,
                save_error=time.monotonic() < self.save_error_until,
            )
        elif self.phase == Phase.SAVED and self.last_saved_story is not None:
            self.renderer.draw_saved(self.last_saved_story, text_fn)
        elif self.phase == Phase.LIBRARY:
            self.renderer.draw_library(
                self.storage._library,
                text_fn,
                page=self.library_page,
                share_feedback=self.share_feedback,
                share_enabled=self.creations is not None,
            )
        elif self.phase == Phase.MIC_REQUIRED:
            self.renderer.draw_mic_required(text_fn)
        confirm = self.delete_confirm
        if confirm is not None:
            self.renderer.draw_delete_dialog(
                self.storage._library.get(confirm.target_id),
                armed=confirm.armed(time.monotonic()),
                focus=confirm.focus,
                text_fn=text_fn,
            )

    def _make_text_fn(self) -> "LocalizedTextSurfaces":
        """Return the app's single cached text callable (built lazily once).

        The renderer passes either a semantic key (``"ui.scene_forest"``,
        resolved once through the Activity's ``LocalizedResources``) or a
        neutral literal such as a duration or arrow glyph. Surfaces are cached
        so unchanged copy is never re-rasterized per frame.
        """
        text_fn = self.__dict__.get("_text_fn")
        if text_fn is None:
            text_fn = LocalizedTextSurfaces(self.typography, self.resources)
            self.__dict__["_text_fn"] = text_fn
        return text_fn


class LocalizedTextSurfaces:
    """Resolve semantic UI keys once and cache rendered text surfaces.

    ``resolve(text)`` returns the display string (case policy is applied by
    ``LocalizedResources.text``; neutral literals such as times and arrows are used verbatim).
    A missing key renders nothing rather than showing a key or fixed-language
    sentence. The surface cache is bounded and cleared wholesale.
    """

    _MAX_SURFACES: Final = 128

    def __init__(self, typography: GreiaTypography, resources: LocalizedResources) -> None:
        self._typography = typography
        self._resources = resources
        self._strings: dict[str, str] = {}
        self._surfaces: dict[tuple[str, tuple[int, int, int], int, int | None], pygame.Surface] = {}

    def resolve(self, text: str) -> str:
        if not isinstance(text, str) or not text:
            return ""
        cached = self._strings.get(text)
        if cached is not None:
            return cached
        if text.startswith("ui.") or text.startswith("activity."):
            try:
                value = self._resources.text(text)
            except Exception:
                value = ""
        else:
            value = text  # neutral literal (number, unit, symbol): never re-cased
        if len(self._strings) >= self._MAX_SURFACES:
            self._strings.clear()
        self._strings[text] = value
        return value

    def __call__(
        self,
        text: str,
        color: tuple[int, int, int],
        size: int = 18,
        max_width: int | None = None,
    ) -> pygame.Surface:
        """Cached surface for ``text``; shrinks (to a floor) to fit ``max_width``."""
        key = (text, tuple(color), size, max_width)
        surface = self._surfaces.get(key)
        if surface is None:
            if len(self._surfaces) >= self._MAX_SURFACES:
                self._surfaces.clear()
            resolved = self.resolve(text)
            fitted = size
            if max_width is not None:
                while (
                    fitted > 10
                    and self._typography.measure(resolved, FontRole.DISPLAY, fitted).width
                    > max_width
                ):
                    fitted -= 1
            surface = self._typography.render(resolved, FontRole.DISPLAY, fitted, color)
            self._surfaces[key] = surface
        return surface


def build_app(
    screen: pygame.Surface,
    locale: str | None = None,
    package_root: "Path | None" = None,
) -> VoiceApp:
    """Composition root for the headless launch / simulator gate.

    ``locale`` is only for isolated embedders/tests; normal launches inherit
    the child's profile language through ``activity_resources``.
    """
    pygame.init()
    metrics = ChildUiMetrics.for_size(*screen.get_size())
    theme = get_theme()
    typography = GreiaTypography()
    from pathlib import Path
    root = package_root or Path(__file__).resolve().parent
    resources = activity_resources(root, requested_locale=locale)
    pygame.display.set_caption(resources.text("activity.title"))
    recorder = VoiceRecorder()
    playback = VoicePlayback()
    storage = VoiceStorage.load()
    events = VoiceEvents()
    renderer = VoiceRenderer.build(screen)
    try:
        creations = get_creations()
    except RuntimeError:
        creations = None
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
        creations=creations,
    )