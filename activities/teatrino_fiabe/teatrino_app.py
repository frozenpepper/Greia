"""Application coordinator for Teatrino delle Fiabe.

Owns Pygame screen/canvas, model session, audio owners, renderer helpers
and bounded asset caches. This is the only place that touches Pygame
events + platform APIs together.
"""

from __future__ import annotations

import hashlib
import io
import json
import math
import random
import time
from pathlib import Path

import pygame

from greia_platform.activity_api import (
    activity_stop_requested,
    emit_activity_event,
    get_creations,
    get_profile_locale,
    get_storage,
    get_theme,
    mark_activity_ready,
)
from greia_platform.activity_ui import ChildUiMetrics
from greia_platform.child_text import display_text
from greia_platform.localization import (
    ActivityLocaleSupport,
    resolve_activity_locale,
)
from greia_platform.pygame_canvas import PygameReferenceCanvas, activity_viewport_for_surface
from greia_platform.pygame_png import PygamePngError, decode_png_surface
from greia_platform.typography import FontRole, GreiaTypography

if __package__:
    from .teatrino_assets import clear_all_caches, render_backdrop_surface
    from .teatrino_audio import ImportedNarrationTrack, MicrophoneRecorder, SoundManager
    from .teatrino_content import (
        BG_CONFIGS,
        DARK_TEXT,
        FX_BUTTONS,
        MAX_RECORDING_SECONDS,
        PUPPET_ROSTER,
        REC_RED,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        STAGE_CURTAIN,
        STAGE_CURTAIN_DARK,
        STAGE_CURTAIN_LIGHT,
        STAGE_GOLD,
        MIC_GREEN,
        WHITE,
    )
    from .teatrino_model import AmbientSpark, Puppet, ShowRepository, ShowStorageError
    from .teatrino_renderer import (
        draw_ambient_spark,
        draw_puppet,
        draw_stage_curtains_and_valance,
        get_library_modal_layout,
    )
else:
    from teatrino_assets import clear_all_caches, render_backdrop_surface
    from teatrino_audio import ImportedNarrationTrack, MicrophoneRecorder, SoundManager
    from teatrino_content import (
        BG_CONFIGS,
        DARK_TEXT,
        FX_BUTTONS,
        MAX_RECORDING_SECONDS,
        PUPPET_ROSTER,
        REC_RED,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        STAGE_CURTAIN,
        STAGE_CURTAIN_DARK,
        STAGE_CURTAIN_LIGHT,
        STAGE_GOLD,
        MIC_GREEN,
        WHITE,
    )
    from teatrino_model import AmbientSpark, Puppet, ShowRepository, ShowStorageError
    from teatrino_renderer import (
        draw_ambient_spark,
        draw_puppet,
        draw_stage_curtains_and_valance,
        get_library_modal_layout,
    )


def _load_package_locale_tables(
    locales_dir: Path,
    requested_language: str,
) -> tuple[str, dict[str, str], dict[str, str], dict[str, str]]:
    """Load the Activity's ui/puppet/backdrop copy for one locale.

    The standard schema-v1 bundle namespaces these three families as
    ``ui.*``, ``puppet.*`` and ``backdrop.*``; the loader returns them as
    three small id -> text tables so call sites stay semantic.
    """
    language = requested_language if requested_language in {"it", "en"} else "it"
    locale_file = locales_dir / f"{language}.json"
    if not locale_file.is_file():
        language = "it"
        locale_file = locales_dir / "it.json"
    try:
        raw = json.loads(locale_file.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return language, {}, {}, {}
    strings = raw.get("strings", {}) if isinstance(raw, dict) else {}
    if not isinstance(strings, dict):
        return language, {}, {}, {}

    def table(prefix: str) -> dict[str, str]:
        return {
            key[len(prefix):]: item
            for key, item in strings.items()
            if isinstance(key, str) and isinstance(item, str) and key.startswith(prefix)
        }

    return language, table("ui."), table("puppet."), table("backdrop.")


def _is_safe_point(surface: pygame.Surface, position: tuple[int, int]) -> bool:
    vp = activity_viewport_for_surface(surface)
    x, y = position
    if not (0 <= x < vp.surface.width and 0 <= y < vp.surface.height):
        return False
    for protected in vp.protected_regions:
        if protected.x <= x < protected.right and protected.y <= y < protected.bottom:
            return False
    return True


class TeatrinoApp:
    """Lifecycle owner for the puppet theater.

    Composition root for screen, storage, audio, spark/puppet state,
    recording/playback engines and rendering.
    """

    def __init__(self, screen: pygame.Surface | None = None) -> None:
        pygame.font.init()
        if screen is None:
            screen = pygame.display.get_surface()
            if screen is None:
                # Match original monolith: fullscreen native display.
                try:
                    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                except Exception:
                    screen = pygame.display.set_mode((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.RESIZABLE)
        pygame.mouse.set_visible(False)
        self.screen = screen
        self.canvas = PygameReferenceCanvas(screen)
        self.metrics = ChildUiMetrics.for_size(*screen.get_size())
        self.clock = pygame.time.Clock()
        try:
            self.theme = get_theme()
        except Exception:

            class _FallbackTheme:
                background = (245, 240, 225)

            self.theme = _FallbackTheme()  # type: ignore
        self.typography = GreiaTypography()
        try:
            self.storage = get_storage()
        except Exception:
            self.storage = None
        self.show_repo = ShowRepository(self.storage)
        try:
            self.creations = get_creations()
        except RuntimeError:
            self.creations = None

        # Resolve the profile locale first, then load exactly that package
        # bundle once; never pre-load Italian and merely remember that English
        # was selected.
        self._active_locale = "it"
        locales_dir = Path(__file__).resolve().parent / "locales"
        try:
            support = ActivityLocaleSupport.localized(
                ("it", "en"), default_ui_locale="it"
            )
            ctx = resolve_activity_locale(get_profile_locale(), support)
            if ctx is not None:
                self._active_locale = ctx.selected.language
        except Exception:
            self._active_locale = "it"

        (
            self._active_locale,
            self.ui_strings,
            self.puppet_names,
            self.backdrop_names,
        ) = _load_package_locale_tables(locales_dir, self._active_locale)

        # Sprites — convert_alpha once, pre-scale thumbnails to eliminate
        # per-frame smoothscale (case-study performance pattern).
        runtime_dir = Path(__file__).resolve().parent / "assets" / "runtime"
        self.puppet_sprites: dict[str, pygame.Surface] = {}
        for p_id, p_name in PUPPET_ROSTER:
            png_path = runtime_dir / f"puppet_{p_id}.png"
            if png_path.is_file():
                try:
                    img = pygame.image.load(str(png_path)).convert_alpha()
                    self.puppet_sprites[p_id] = pygame.transform.smoothscale(img, (110, 110))
                except Exception:
                    pass
        if "lilli" not in self.puppet_sprites:
            fb_s = pygame.Surface((110, 110), pygame.SRCALPHA)
            pygame.draw.circle(fb_s, (244, 114, 182), (55, 55), 45)
            self.puppet_sprites["lilli"] = fb_s

        self.puppet_thumbs: dict[str, pygame.Surface] = {
            p_id: pygame.transform.smoothscale(spr, (52, 52)) for p_id, spr in self.puppet_sprites.items()
        }
        self.puppet_micro_thumbs: dict[str, pygame.Surface] = {
            p_id: pygame.transform.smoothscale(spr, (38, 38)) for p_id, spr in self.puppet_sprites.items()
        }

        # Text cache bounded with explicit invalidation.
        self.text_cache: dict[tuple, pygame.Surface] = {}

        # Pre-render & cache all 5 backdrops via bounded asset cache.
        self.cached_backdrops: dict[str, pygame.Surface] = {}
        for bg_id, _, _ in BG_CONFIGS:
            self.cached_backdrops[bg_id] = render_backdrop_surface(bg_id)

        self.custom_backdrop_png: bytes | None = None
        self.custom_backdrop_surface: pygame.Surface | None = None
        self.backdrop_import_request: str | None = None
        self.backdrop_import_next_poll = 0.0
        self.backdrop_import_state = ""
        self.backdrop_import_feedback_until = 0.0
        self.narration_import_request: str | None = None
        self.narration_import_next_poll = 0.0
        self.narration_import_state = ""
        self.narration_import_feedback_until = 0.0
        self.imported_narration: ImportedNarrationTrack | None = None

        self.sound_mgr = SoundManager()
        self.mic_recorder = MicrophoneRecorder()

        self.sparks = [AmbientSpark("cottage") for _ in range(16)]

        self.active_bg_idx = 0
        self.puppets_on_stage: list[Puppet] = [
            Puppet("lilli", self.puppet_names.get("lilli", "Lilli"), 380, 270),
            Puppet("draghetto", self.puppet_names.get("draghetto", "Draghetto"), 600, 270),
        ]
        self.puppets_on_stage[1].flip_x = True
        self.held_puppet: Puppet | None = None
        self.held_offset_x = 0.0
        self.held_offset_y = 0.0

        self.tray_page = 0
        self.puppets_per_page = 6
        self.max_tray_pages = (len(PUPPET_ROSTER) + self.puppets_per_page - 1) // self.puppets_per_page

        self.app_mode = "stage"
        self.is_recording = False
        self.rec_start_time = 0.0
        self.recorded_frames: list[dict] = []
        self.recorded_sfx: list[dict] = []
        self.last_recorded_wav: bytes | None = None
        self.recording_narration_track: ImportedNarrationTrack | None = None
        self.recording_narration_sound: pygame.mixer.Sound | None = None
        self.recording_narration_channel: pygame.mixer.Channel | None = None
        self.feedback_text = ""
        self.feedback_timer = 0.0

        self.is_playing_show = False
        self.play_start_time = 0.0
        self.playback_frames: list[dict] = []
        self.playback_sfx: list[dict] = []
        self.playback_audio_channel: pygame.mixer.Channel | None = None
        self.playback_duration = 0.0
        self.playback_show_meta: dict | None = None

        self.library_page = 0
        self.library_shows = self.show_repo.list_shows()

        self.running = True

    # -- text helper -------------------------------------------------------

    def _ui(self, key: str) -> str:
        """Localized UI copy from the selected bundle; empty when absent.

        There is deliberately no fixed-language fallback sentence: a missing
        key leaves only the control's pictogram.
        """
        return self.ui_strings.get(key, "")

    def get_text(self, text: str, role: FontRole, size: int, color: tuple) -> pygame.Surface:
        key = (text, role, size, color)
        res = self.text_cache.get(key)
        if res is None:
            res = self.typography.render(display_text(text), role, size, color)
            if len(self.text_cache) > 256:
                self.text_cache.clear()
            self.text_cache[key] = res
        return res

    # -- frame step ---------------------------------------------------------

    def _step_frame(self, dt: float) -> None:
        now = time.monotonic()
        self._poll_shared_backdrop(now)
        self._poll_shared_narration(now)
        if (
            self.backdrop_import_state
            and self.backdrop_import_state != "pending"
            and now >= self.backdrop_import_feedback_until
        ):
            self.backdrop_import_state = ""
        if (
            self.narration_import_state
            and self.narration_import_state != "pending"
            and now >= self.narration_import_feedback_until
        ):
            self.narration_import_state = ""
        if self.feedback_timer > 0.0:
            self.feedback_timer -= dt
            if self.feedback_timer <= 0.0:
                self.feedback_text = ""

        active_bg_id = BG_CONFIGS[self.active_bg_idx][0]
        for sp in self.sparks:
            sp.bg_id = active_bg_id
            sp.update()

        for p in self.puppets_on_stage:
            p.update()

        if self.is_recording:
            elapsed = time.time() - self.rec_start_time
            limit = (
                self.recording_narration_track.duration_seconds
                if self.recording_narration_track is not None
                else MAX_RECORDING_SECONDS
            )
            if elapsed >= limit:
                self._finish_recording(
                    min(elapsed, limit),
                    feedback_seconds=4.0,
                )
            else:
                frame_data = {
                    "t": round(elapsed, 2),
                    "puppets": [
                        {
                            "id": p.puppet_id,
                            "x": round(p.x, 1),
                            "y": round(p.y, 1),
                            "flip": p.flip_x,
                            "jumping": p.jump_timer > 0.0,
                            "talking": p.talk_timer > 0.0,
                        }
                        for p in self.puppets_on_stage
                    ],
                }
                self.recorded_frames.append(frame_data)

        if self.is_playing_show:
            play_elapsed = time.time() - self.play_start_time
            if play_elapsed >= self.playback_duration:
                self.is_playing_show = False
                if self.playback_audio_channel is not None:
                    try:
                        self.playback_audio_channel.stop()
                    except Exception:
                        pass
                    self.playback_audio_channel = None
                self.feedback_text = (
                    "👏 "
                    + self._ui("playback_complete")
                )
                self.feedback_timer = 3.0
                self.sound_mgr.play("applause")
                self._emit_saved_story_played()
            else:
                if self.playback_frames:
                    prev_f = self.playback_frames[0]
                    next_f = self.playback_frames[-1]
                    for f in self.playback_frames:
                        if f["t"] <= play_elapsed:
                            prev_f = f
                        else:
                            next_f = f
                            break
                    span = max(0.01, next_f["t"] - prev_f["t"])
                    ratio = min(1.0, max(0.0, (play_elapsed - prev_f["t"]) / span))
                    for p_data in prev_f["puppets"]:
                        for live_p in self.puppets_on_stage:
                            if live_p.puppet_id == p_data["id"]:
                                target_x = p_data["x"]
                                target_y = p_data["y"]
                                for np in next_f["puppets"]:
                                    if np["id"] == p_data["id"]:
                                        target_x = p_data["x"] + (np["x"] - p_data["x"]) * ratio
                                        target_y = p_data["y"] + (np["y"] - p_data["y"]) * ratio
                                        break
                                live_p.x = target_x
                                live_p.y = target_y
                                live_p.flip_x = p_data["flip"]
                                if p_data["jumping"] and live_p.jump_timer <= 0.0:
                                    live_p.jump()
                                if p_data["talking"] and live_p.talk_timer <= 0.0:
                                    live_p.speak()
                for sfx in list(self.playback_sfx):
                    if sfx["t"] <= play_elapsed:
                        self.sound_mgr.play(sfx["sound"])
                        self.playback_sfx.remove(sfx)

    def _emit_saved_story_played(self) -> None:
        meta = self.playback_show_meta
        if not isinstance(meta, dict):
            return
        show_id = meta.get("id")
        if not isinstance(show_id, str) or not show_id:
            return
        try:
            emit_activity_event(
                "story.played",
                idempotency_key=(
                    f"play-{show_id}-{int(self.play_start_time * 1000)}"
                ),
                payload={"id": show_id},
            )
        except Exception:
            pass

    # -- recording source / narration --------------------------------------

    def _start_recording(self) -> bool:
        if self.is_recording:
            return False
        self.recorded_frames = []
        self.recorded_sfx = []
        self.rec_start_time = time.time()
        self.recording_narration_track = self.imported_narration
        self.recording_narration_sound = None
        self.recording_narration_channel = None

        if self.recording_narration_track is not None:
            played = self.recording_narration_track.play()
            if played is None:
                self.recording_narration_track = None
                self.feedback_text = (
                    "⚠️ "
                    + self._ui("narration_play_failed")
                )
                self.feedback_timer = 2.5
                self.sound_mgr.play("boing")
                return False
            (
                self.recording_narration_sound,
                self.recording_narration_channel,
            ) = played
        else:
            self.mic_recorder.start_recording()

        self.is_recording = True
        self.feedback_text = (
            "🔴 "
            + self._ui("recording_active")
        )
        self.feedback_timer = 3.0
        if self.recording_narration_track is None:
            self.sound_mgr.play("trumpet")
        return True

    def _stop_recording_narration(self) -> None:
        if self.recording_narration_channel is not None:
            try:
                self.recording_narration_channel.stop()
            except Exception:
                pass
        self.recording_narration_channel = None
        self.recording_narration_sound = None

    def _finish_recording(
        self,
        elapsed: float,
        *,
        feedback_seconds: float,
    ) -> dict | None:
        if not self.is_recording:
            return None
        self.is_recording = False
        elapsed = max(0.05, float(elapsed))
        track = self.recording_narration_track
        self.recording_narration_track = None

        if track is not None:
            self._stop_recording_narration()
            try:
                wav_bytes = track.trimmed(elapsed)
            except ValueError:
                self.feedback_text = (
                    "⚠️ "
                    + self._ui("narration_play_failed")
                )
                self.feedback_timer = feedback_seconds
                self.sound_mgr.play("boing")
                return None
        else:
            wav_bytes = self.mic_recorder.stop_recording()

        self.last_recorded_wav = wav_bytes
        active_bg_id = BG_CONFIGS[self.active_bg_idx][0]
        return self._persist_recorded_show(
            active_bg_id,
            elapsed,
            wav_bytes,
            feedback_seconds=feedback_seconds,
        )

    def _request_shared_narration(self) -> None:
        if (
            self.creations is None
            or self.app_mode != "stage"
            or self.is_recording
            or self.narration_import_request is not None
            or self.backdrop_import_request is not None
        ):
            return
        try:
            request_id = self.creations.request_selection(
                media_types=("audio/wav",),
                roles=("narration",),
            )
        except (RuntimeError, ValueError, OSError):
            self.narration_import_state = "error"
            self.narration_import_feedback_until = time.monotonic() + 2.0
            return
        self.narration_import_request = request_id
        self.narration_import_state = "pending"
        self.narration_import_next_poll = time.monotonic() + 0.12

    def _poll_shared_narration(self, now: float) -> None:
        request_id = self.narration_import_request
        if (
            request_id is None
            or self.creations is None
            or now < self.narration_import_next_poll
        ):
            return
        self.narration_import_next_poll = now + 0.12
        try:
            result = self.creations.poll_selection(request_id)
        except (RuntimeError, ValueError, OSError):
            self.narration_import_request = None
            self.narration_import_state = "error"
            self.narration_import_feedback_until = now + 2.0
            return
        if result.state == "pending":
            return
        self.narration_import_request = None
        if result.state == "cancelled":
            self.narration_import_state = ""
            return
        token = result.selection_token
        if (
            result.state != "ready"
            or not isinstance(token, str)
            or not token
            or not self._accept_shared_narration(token)
        ):
            self.narration_import_state = "error"
            self.narration_import_feedback_until = now + 2.0
            return
        self.narration_import_state = "imported"
        self.narration_import_feedback_until = now + 2.0
        self.feedback_text = (
            "🎧 "
            + self._ui("narration_imported")
        )
        self.feedback_timer = 2.0

    def _accept_shared_narration(self, selection_token: str) -> bool:
        if self.creations is None:
            return False
        try:
            transfer = self.creations.import_selected(selection_token)
            payload = transfer.payload
            if (
                transfer.record.get("media_type") != "audio/wav"
                or transfer.record.get("role") != "narration"
                or not isinstance(payload, bytes)
                or transfer.record.get("sha256")
                != hashlib.sha256(payload).hexdigest()
            ):
                raise ValueError("selected narration failed integrity validation")
            track = ImportedNarrationTrack.from_wav(
                payload,
                max_duration_seconds=MAX_RECORDING_SECONDS,
            )
        except (RuntimeError, ValueError, OSError):
            return False
        self.imported_narration = track
        return True

    def _draw_narration_import_button(self, surf: pygame.Surface) -> None:
        if self.creations is None or self.app_mode != "stage":
            return
        rect = pygame.Rect(352, 16, 52, 52)
        pending = self.narration_import_state == "pending"
        active = self.imported_narration is not None
        fill = (
            (171, 219, 245)
            if pending
            else (198, 235, 211)
            if active
            else (236, 244, 252)
        )
        border = (
            (205, 55, 61)
            if self.narration_import_state == "error"
            else (39, 112, 168)
        )
        pygame.draw.rect(surf, fill, rect, border_radius=13)
        pygame.draw.rect(surf, border, rect, width=3, border_radius=13)
        cx, cy = rect.center
        # Music note + downward arrow: pre-reader "bring saved voice here".
        pygame.draw.circle(surf, DARK_TEXT, (cx - 9, cy + 8), 5)
        pygame.draw.line(
            surf,
            DARK_TEXT,
            (cx - 4, cy + 7),
            (cx - 4, cy - 12),
            3,
        )
        pygame.draw.line(
            surf,
            DARK_TEXT,
            (cx - 4, cy - 12),
            (cx + 5, cy - 9),
            3,
        )
        pygame.draw.line(surf, DARK_TEXT, (cx + 11, cy - 12), (cx + 11, cy + 5), 3)
        pygame.draw.lines(
            surf,
            DARK_TEXT,
            False,
            [(cx + 5, cy), (cx + 11, cy + 6), (cx + 17, cy)],
            3,
        )

    # -- recorded-show persistence ------------------------------------------

    def _persist_recorded_show(
        self,
        active_bg_id: str,
        elapsed: float,
        wav_bytes: bytes | None,
        *,
        feedback_seconds: float,
    ) -> dict | None:
        try:
            saved_meta = self.show_repo.save_show(
                active_bg_id,
                [
                    {"id": puppet.puppet_id, "name": puppet.name}
                    for puppet in self.puppets_on_stage
                ],
                self.recorded_frames,
                self.recorded_sfx,
                elapsed,
                wav_bytes,
                self.custom_backdrop_png,
            )
        except (ShowStorageError, ValueError, OSError):
            self.library_shows = self.show_repo.list_shows()
            self.feedback_text = (
                "⚠️ "
                + self._ui("recording_save_failed")
            )
            self.feedback_timer = feedback_seconds
            self.sound_mgr.play("boing")
            return None

        self.library_shows = self.show_repo.list_shows()
        self.feedback_text = (
            "🎉 "
            + self._ui("recording_saved")
        )
        self.feedback_timer = feedback_seconds
        try:
            emit_activity_event(
                "story.recorded",
                idempotency_key=f"rec-{saved_meta['id']}",
                payload={
                    "duration": round(elapsed, 1),
                    "id": saved_meta["id"],
                },
            )
        except Exception:
            pass
        self.sound_mgr.play("applause")
        return saved_meta

    # -- shared backdrop ----------------------------------------------------

    def _request_shared_backdrop(self) -> None:
        if (
            self.creations is None
            or self.app_mode != "stage"
            or self.is_recording
            or self.backdrop_import_request is not None
            or self.narration_import_request is not None
        ):
            return
        try:
            request_id = self.creations.request_selection(
                media_types=("image/png",)
            )
        except (RuntimeError, ValueError, OSError):
            self.backdrop_import_state = "error"
            self.backdrop_import_feedback_until = time.monotonic() + 2.0
            self.feedback_text = "⚠️"
            self.feedback_timer = 2.0
            return
        self.backdrop_import_request = request_id
        self.backdrop_import_state = "pending"
        self.backdrop_import_next_poll = (
            time.monotonic() + 0.12
        )

    def _poll_shared_backdrop(self, now: float) -> None:
        request_id = self.backdrop_import_request
        if (
            request_id is None
            or self.creations is None
            or now < self.backdrop_import_next_poll
        ):
            return
        self.backdrop_import_next_poll = now + 0.12
        try:
            result = self.creations.poll_selection(request_id)
        except (RuntimeError, ValueError, OSError):
            self.backdrop_import_request = None
            self.backdrop_import_state = "error"
            self.backdrop_import_feedback_until = now + 2.0
            return
        if result.state == "pending":
            return
        self.backdrop_import_request = None
        if result.state == "cancelled":
            self.backdrop_import_state = ""
            return
        token = result.selection_token
        if (
            result.state != "ready"
            or not isinstance(token, str)
            or not token
            or not self._accept_shared_backdrop(token)
        ):
            self.backdrop_import_state = "error"
            self.backdrop_import_feedback_until = now + 2.0
            return
        self.backdrop_import_state = "imported"
        self.backdrop_import_feedback_until = now + 2.0
        self.feedback_text = "🖼️"
        self.feedback_timer = 2.0

    def _accept_shared_backdrop(self, selection_token: str) -> bool:
        if self.creations is None:
            return False
        try:
            transfer = self.creations.import_selected(selection_token)
            payload = transfer.payload
            if (
                transfer.record.get("media_type") != "image/png"
                or not isinstance(payload, bytes)
                or transfer.record.get("sha256")
                != hashlib.sha256(payload).hexdigest()
            ):
                raise ValueError("selected backdrop failed integrity validation")
            surface = decode_png_surface(
                payload, (REFERENCE_WIDTH, REFERENCE_HEIGHT)
            )
        except (PygamePngError, RuntimeError, ValueError, OSError):
            return False
        self.custom_backdrop_png = payload
        self.custom_backdrop_surface = surface
        return True

    def _load_saved_backdrop(self, show_id: str) -> None:
        payload = self.show_repo.load_show_backdrop(show_id)
        if payload is None:
            self.custom_backdrop_png = None
            self.custom_backdrop_surface = None
            return
        try:
            surface = decode_png_surface(
                payload, (REFERENCE_WIDTH, REFERENCE_HEIGHT)
            )
        except (PygamePngError, RuntimeError, ValueError, OSError):
            self.custom_backdrop_png = None
            self.custom_backdrop_surface = None
            return
        self.custom_backdrop_png = payload
        self.custom_backdrop_surface = surface

    def _draw_backdrop_import_button(self, surf: pygame.Surface) -> None:
        if self.creations is None or self.app_mode != "stage":
            return
        rect = pygame.Rect(830, 24, 70, 54)
        pending = self.backdrop_import_state == "pending"
        fill = (178, 218, 246) if pending else (234, 244, 252)
        pygame.draw.rect(surf, fill, rect, border_radius=14)
        border = (
            (205, 55, 61)
            if self.backdrop_import_state == "error"
            else STAGE_GOLD
        )
        pygame.draw.rect(surf, border, rect, width=3, border_radius=14)
        cx, cy = rect.center
        pygame.draw.rect(
            surf, DARK_TEXT, (cx - 15, cy, 30, 18), width=3, border_radius=4
        )
        pygame.draw.circle(surf, DARK_TEXT, (cx + 8, cy + 5), 3)
        pygame.draw.line(surf, DARK_TEXT, (cx, cy - 17), (cx, cy + 1), 4)
        pygame.draw.lines(
            surf,
            DARK_TEXT,
            False,
            [(cx - 8, cy - 7), (cx, cy + 1), (cx + 8, cy - 7)],
            4,
        )

    # -- input dispatch -----------------------------------------------------

    def _handle_mouse_down(self, rx: int, ry: int) -> None:
        if self.app_mode == "library":
            modal_layout = get_library_modal_layout(self.library_page, len(self.library_shows))
            if modal_layout["close"].collidepoint(rx, ry):
                self.sound_mgr.play("pop")
                self.app_mode = "stage"
                return
            if modal_layout["prev_btn"].collidepoint(rx, ry) and self.library_page > 0:
                self.sound_mgr.play("pop")
                self.library_page -= 1
                return
            if modal_layout["next_btn"].collidepoint(rx, ry) and (self.library_page + 1) * modal_layout["cards_per_page"] < len(
                self.library_shows
            ):
                self.sound_mgr.play("pop")
                self.library_page += 1
                return
            for card_info in modal_layout["cards"]:
                s_idx = card_info["show_index"]
                if s_idx >= len(self.library_shows):
                    continue
                show_item = self.library_shows[s_idx]
                if card_info["play_btn"].collidepoint(rx, ry):
                    show_data, wav_bytes = self.show_repo.load_show(show_item["id"])
                    if show_data:
                        self.sound_mgr.play("trumpet")
                        self.app_mode = "viewer"
                        self.is_playing_show = True
                        self.play_start_time = time.time()
                        self.playback_show_meta = show_item
                        self.playback_frames = show_data.get("frames", [])
                        self.playback_sfx = list(show_data.get("sfx_events", []))
                        self.playback_duration = max(1.0, float(show_item.get("duration", 5.0)))
                        saved_bg = show_item.get("backdrop", "cottage")
                        for b_idx, (b_id, _, _) in enumerate(BG_CONFIGS):
                            if b_id == saved_bg:
                                self.active_bg_idx = b_idx
                                break
                        self._load_saved_backdrop(show_item["id"])
                        self.puppets_on_stage = []
                        for p_meta in show_data.get("puppets", []):
                            p_obj = Puppet(
                                p_meta["id"],
                                self.puppet_names.get(p_meta["id"], p_meta.get("name", "Puppet")),
                                512,
                                270,
                            )
                            self.puppets_on_stage.append(p_obj)
                        if self.playback_audio_channel:
                            try:
                                self.playback_audio_channel.stop()
                            except Exception:
                                pass
                            self.playback_audio_channel = None
                        if wav_bytes and len(wav_bytes) > 44:
                            try:
                                snd = pygame.mixer.Sound(io.BytesIO(wav_bytes))
                                self.playback_audio_channel = snd.play()
                            except Exception:
                                self.playback_audio_channel = None
                    break
                if card_info["del_btn"].collidepoint(rx, ry):
                    self.sound_mgr.play("boing")
                    self.show_repo.delete_show(show_item["id"])
                    self.library_shows = self.show_repo.list_shows()
                    if self.library_page * modal_layout["cards_per_page"] >= len(self.library_shows) and self.library_page > 0:
                        self.library_page -= 1
                    break
            return

        if self.app_mode == "viewer":
            if 140 <= rx <= 250 and 16 <= ry <= 68:
                self.sound_mgr.play("pop")
                if self.playback_audio_channel:
                    try:
                        self.playback_audio_channel.stop()
                    except Exception:
                        pass
                    self.playback_audio_channel = None
                self.is_playing_show = False
                self.playback_show_meta = None
                self.app_mode = "stage"
                return
            if 265 <= rx <= 385 and 16 <= ry <= 68:
                if self.playback_show_meta:
                    self.sound_mgr.play("trumpet")
                    if self.playback_audio_channel:
                        try:
                            self.playback_audio_channel.stop()
                        except Exception:
                            pass
                        self.playback_audio_channel = None
                    self.is_playing_show = True
                    self.play_start_time = time.time()
                    show_data, wav_bytes = self.show_repo.load_show(self.playback_show_meta["id"])
                    if show_data:
                        self.playback_frames = show_data.get("frames", [])
                        self.playback_sfx = list(show_data.get("sfx_events", []))
                        self.playback_duration = max(1.0, float(self.playback_show_meta.get("duration", 5.0)))
                        if wav_bytes and len(wav_bytes) > 44:
                            try:
                                snd = pygame.mixer.Sound(io.BytesIO(wav_bytes))
                                self.playback_audio_channel = snd.play()
                            except Exception:
                                self.playback_audio_channel = None
                return

        # MODE: STAGE EDITOR
        if 140 <= rx <= 215 and 16 <= ry <= 68:
            self.sound_mgr.play("pop")
            if self.imported_narration is not None:
                self.imported_narration = None
                self.narration_import_state = ""
                self.mic_recorder.enabled = True
                self.feedback_text = (
                    "🎙️ "
                    + self._ui("mic_source")
                )
            else:
                new_state = self.mic_recorder.toggle()
                self.feedback_text = (
                    "🎙️ "
                    + self._ui("mic_active_feedback")
                    if new_state
                    else "🔇 "
                    + self._ui("mic_inactive_feedback")
                )
            self.feedback_timer = 2.5
            return
        if 225 <= rx <= 345 and 16 <= ry <= 68:
            self.sound_mgr.play("pop")
            self.library_shows = self.show_repo.list_shows()
            self.app_mode = "library"
            return
        if 352 <= rx <= 404 and 16 <= ry <= 68:
            self._request_shared_narration()
            return
        if 415 <= rx <= 545 and 16 <= ry <= 68:
            if not self.is_recording:
                self._start_recording()
            else:
                elapsed = max(0.05, time.time() - self.rec_start_time)
                self._finish_recording(
                    elapsed,
                    feedback_seconds=3.5,
                )
            return
        if 560 <= rx <= 690 and 16 <= ry <= 68:
            self.playback_show_meta = None
            if self.recorded_frames:
                self.is_playing_show = True
                self.play_start_time = time.time()
                self.playback_frames = list(self.recorded_frames)
                self.playback_sfx = list(self.recorded_sfx)
                self.playback_duration = max(2.0, self.recorded_frames[-1]["t"])
                self.feedback_text = f"▶️ {self._ui('playing_show')}"
                self.feedback_timer = 3.0
                self.sound_mgr.play("trumpet")
                if self.playback_audio_channel:
                    try:
                        self.playback_audio_channel.stop()
                    except Exception:
                        pass
                    self.playback_audio_channel = None
                if self.last_recorded_wav and len(self.last_recorded_wav) > 44:
                    try:
                        snd = pygame.mixer.Sound(io.BytesIO(self.last_recorded_wav))
                        self.playback_audio_channel = snd.play()
                    except Exception:
                        self.playback_audio_channel = None
            else:
                self.is_playing_show = True
                self.play_start_time = time.time()
                self.playback_duration = 5.0
                for p in self.puppets_on_stage:
                    p.jump()
                    p.speak()
                self.sound_mgr.play("trumpet")
                self.feedback_text = (
                    "▶️ "
                    + self._ui("free_show_playing")
                )
                self.feedback_timer = 3.0
            return
        if 740 <= rx <= 805 and 16 <= ry <= 68:
            self.sound_mgr.play("boing")
            self.puppets_on_stage.clear()
            self.feedback_text = f"✨ {self._ui('stage_cleared')}"
            self.feedback_timer = 2.0
            return
        if 830 <= rx <= 900 and 24 <= ry <= 78:
            self._request_shared_backdrop()
            return
        if 915 <= rx <= 985 and 24 <= ry <= 78:
            self.sound_mgr.play("magic")
            self.custom_backdrop_png = None
            self.custom_backdrop_surface = None
            self.backdrop_import_state = ""
            self.active_bg_idx = (self.active_bg_idx + 1) % len(BG_CONFIGS)
            bg_id, _, fallback_name = BG_CONFIGS[self.active_bg_idx]
            scene_name = self.backdrop_names.get(bg_id, fallback_name)
            scene_template = self._ui("scene_changed")
            try:
                scene_feedback = scene_template.format(scene=scene_name) if scene_template else scene_name
            except (KeyError, ValueError):
                scene_feedback = scene_name
            self.feedback_text = f"✨ {scene_feedback}"
            self.feedback_timer = 2.0
            return
        fx_clicked = False
        for f_idx, (fx_id, _) in enumerate(FX_BUTTONS):
            fy = 88 + f_idx * 58
            if 915 <= rx <= 985 and fy <= ry <= fy + 52:
                self.sound_mgr.play(fx_id)
                for p in self.puppets_on_stage:
                    p.jump()
                if self.is_recording:
                    self.recorded_sfx.append({"t": round(time.time() - self.rec_start_time, 2), "sound": fx_id})
                fx_clicked = True
                break
        if fx_clicked:
            return
        if ry >= 500:
            if 40 <= rx <= 94 and 522 <= ry <= 576:
                self.sound_mgr.play("pop")
                self.tray_page = (self.tray_page - 1) % self.max_tray_pages
                return
            if 930 <= rx <= 984 and 522 <= ry <= 576:
                self.sound_mgr.play("pop")
                self.tray_page = (self.tray_page + 1) % self.max_tray_pages
                return
            page_puppets = PUPPET_ROSTER[self.tray_page * self.puppets_per_page : (self.tray_page + 1) * self.puppets_per_page]
            for p_idx, (p_id, p_name) in enumerate(page_puppets):
                card_x = 110 + p_idx * 135
                if card_x <= rx <= card_x + 120 and 508 <= ry <= 592:
                    self.sound_mgr.play("pop")
                    loc_name = self.puppet_names.get(p_id, p_name)
                    spawn_x = random.randint(300, 720)
                    new_puppet = Puppet(p_id, loc_name, spawn_x, 270)
                    new_puppet.jump()
                    self.puppets_on_stage.append(new_puppet)
                    break
            return
        for p in reversed(self.puppets_on_stage):
            if p.contains(rx, ry):
                self.held_puppet = p
                p.is_held = True
                p.speak()
                self.sound_mgr.play("pop")
                self.held_offset_x = p.x - rx
                self.held_offset_y = p.y - ry
                self.puppets_on_stage.remove(p)
                self.puppets_on_stage.append(p)
                break

    # -- drawing ------------------------------------------------------------

    def _draw(self) -> None:
        surf = self.canvas.surface
        active_bg_id = BG_CONFIGS[self.active_bg_idx][0]
        if self.custom_backdrop_surface is not None:
            surf.blit(self.custom_backdrop_surface, (0, 0))
        else:
            surf.blit(self.cached_backdrops[active_bg_id], (0, 0))
        for sp in self.sparks:
            draw_ambient_spark(surf, sp)
        for p in self.puppets_on_stage:
            spr = self.puppet_sprites.get(p.puppet_id, self.puppet_sprites["lilli"])
            draw_puppet(surf, p, spr, self.typography)
        draw_stage_curtains_and_valance(surf)

        if self.app_mode == "stage":
            mic_rect = pygame.Rect(140, 16, 75, 52)
            mic_bg = (220, 255, 225) if self.mic_recorder.enabled else (255, 230, 230)
            mic_border = MIC_GREEN if self.mic_recorder.enabled else (220, 38, 38)
            pygame.draw.rect(surf, mic_bg, mic_rect, border_radius=14)
            pygame.draw.rect(surf, mic_border, mic_rect, width=3, border_radius=14)
            mic_label = f"🎙️ {self._ui('mic_on')}" if self.mic_recorder.enabled else f"🔇 {self._ui('mic_off')}"
            mic_s = self.get_text(mic_label, FontRole.TITLE, 14, mic_border)
            surf.blit(mic_s, (mic_rect.centerx - mic_s.get_width() // 2, mic_rect.centery - mic_s.get_height() // 2))
            lib_rect = pygame.Rect(225, 16, 120, 52)
            pygame.draw.rect(surf, (255, 250, 240), lib_rect, border_radius=14)
            pygame.draw.rect(surf, (61, 44, 31), lib_rect, width=2, border_radius=14)
            num_saved = len(self.library_shows)
            lib_label = f"🎬 {self._ui('stories')} ({num_saved})"
            lib_s = self.get_text(lib_label, FontRole.TITLE, 14, DARK_TEXT)
            surf.blit(lib_s, (lib_rect.centerx - lib_s.get_width() // 2, lib_rect.centery - lib_s.get_height() // 2))
            self._draw_narration_import_button(surf)
            rec_rect = pygame.Rect(415, 16, 130, 52)
            if self.is_recording:
                pygame.draw.rect(surf, (255, 210, 210), rec_rect, border_radius=14)
                pygame.draw.rect(surf, REC_RED, rec_rect, width=3, border_radius=14)
                rec_label = f"⏹️ {self._ui('stop')}"
                rec_s = self.get_text(rec_label, FontRole.TITLE, 16, REC_RED)
                surf.blit(rec_s, (rec_rect.centerx - rec_s.get_width() // 2, rec_rect.centery - rec_s.get_height() // 2))
                meter_x = 425
                meter_y = 72
                vol = (
                    0.72
                    if self.recording_narration_track is not None
                    else self.mic_recorder.current_volume
                )
                for bar_idx in range(5):
                    bar_h = int(4 + math.sin(time.time() * 12 + bar_idx * 1.5) * 8 * vol + vol * 14)
                    pygame.draw.rect(surf, REC_RED, (meter_x + bar_idx * 6, meter_y + (20 - bar_h) // 2, 4, bar_h), border_radius=2)
                recording_limit = (
                    self.recording_narration_track.duration_seconds
                    if self.recording_narration_track is not None
                    else MAX_RECORDING_SECONDS
                )
                t_str = f"{int(time.time() - self.rec_start_time)}s / {int(recording_limit)}s"
                t_surf = self.get_text(t_str, FontRole.CONTROL, 11, REC_RED)
                surf.blit(t_surf, (meter_x + 36, meter_y + 3))
            else:
                pygame.draw.rect(surf, (255, 250, 240), rec_rect, border_radius=14)
                pygame.draw.rect(surf, (61, 44, 31), rec_rect, width=2, border_radius=14)
                rec_label = f"🔴 {self._ui('rec')}"
                rec_s = self.get_text(rec_label, FontRole.TITLE, 16, DARK_TEXT)
                surf.blit(rec_s, (rec_rect.centerx - rec_s.get_width() // 2, rec_rect.centery - rec_s.get_height() // 2))
            play_rect = pygame.Rect(560, 16, 130, 52)
            pygame.draw.rect(surf, (255, 250, 240), play_rect, border_radius=14)
            pygame.draw.rect(surf, (61, 44, 31), play_rect, width=2, border_radius=14)
            play_label = f"▶️ {self._ui('show')}"
            ply_s = self.get_text(play_label, FontRole.TITLE, 16, DARK_TEXT)
            surf.blit(ply_s, (play_rect.centerx - ply_s.get_width() // 2, play_rect.centery - ply_s.get_height() // 2))
            clear_rect = pygame.Rect(740, 16, 65, 52)
            pygame.draw.rect(surf, (255, 250, 240), clear_rect, border_radius=14)
            pygame.draw.rect(surf, (61, 44, 31), clear_rect, width=2, border_radius=14)
            clr_s = self.get_text("🗑️", FontRole.TITLE, 22, DARK_TEXT)
            surf.blit(clr_s, (clear_rect.centerx - clr_s.get_width() // 2, clear_rect.centery - clr_s.get_height() // 2))
        elif self.app_mode == "viewer":
            exit_rect = pygame.Rect(140, 16, 110, 52)
            pygame.draw.rect(surf, (255, 230, 230), exit_rect, border_radius=14)
            pygame.draw.rect(surf, (220, 38, 38), exit_rect, width=2, border_radius=14)
            exit_s = self.get_text(f"⏹️ {self._ui('exit_viewer')}", FontRole.TITLE, 15, (185, 28, 28))
            surf.blit(exit_s, (exit_rect.centerx - exit_s.get_width() // 2, exit_rect.centery - exit_s.get_height() // 2))
            rep_rect = pygame.Rect(265, 16, 120, 52)
            pygame.draw.rect(surf, (255, 250, 240), rep_rect, border_radius=14)
            pygame.draw.rect(surf, (61, 44, 31), rep_rect, width=2, border_radius=14)
            rep_s = self.get_text(f"🔁 {self._ui('replay_story')}", FontRole.TITLE, 15, DARK_TEXT)
            surf.blit(rep_s, (rep_rect.centerx - rep_s.get_width() // 2, rep_rect.centery - rep_s.get_height() // 2))
            prog_bg = pygame.Rect(410, 24, 360, 34)
            pygame.draw.rect(surf, (20, 16, 30), prog_bg, border_radius=10)
            pygame.draw.rect(surf, STAGE_GOLD, prog_bg, width=2, border_radius=10)
            play_elapsed = time.time() - self.play_start_time if self.is_playing_show else self.playback_duration
            ratio = min(1.0, max(0.0, play_elapsed / max(0.1, self.playback_duration)))
            if ratio > 0.0:
                prog_fill = pygame.Rect(prog_bg.x + 3, prog_bg.y + 3, int((prog_bg.width - 6) * ratio), prog_bg.height - 6)
                pygame.draw.rect(surf, STAGE_GOLD, prog_fill, border_radius=8)
            t_title = self._ui("story_generic") if self.playback_show_meta else self._ui("show_generic")
            time_str = f"🎬 {t_title} ({min(int(self.playback_duration), int(play_elapsed))}s / {int(self.playback_duration)}s)"
            t_s = self.get_text(time_str, FontRole.CONTROL, 12, (255, 250, 240))
            surf.blit(t_s, (prog_bg.centerx - t_s.get_width() // 2, prog_bg.centery - t_s.get_height() // 2))

        if self.app_mode == "stage":
            self._draw_backdrop_import_button(surf)
            sc_icon = BG_CONFIGS[self.active_bg_idx][1]
            sc_rect = pygame.Rect(915, 24, 70, 54)
            pygame.draw.rect(surf, (255, 250, 240), sc_rect, border_radius=14)
            pygame.draw.rect(surf, STAGE_GOLD, sc_rect, width=3, border_radius=14)
            sc_s = self.get_text(sc_icon, FontRole.DISPLAY, 26, DARK_TEXT)
            surf.blit(sc_s, (sc_rect.centerx - sc_s.get_width() // 2, sc_rect.centery - sc_s.get_height() // 2 - 4))
            sc_lbl = self.get_text(self._ui("scene"), FontRole.CONTROL, 12, DARK_TEXT)
            surf.blit(sc_lbl, (sc_rect.centerx - sc_lbl.get_width() // 2, sc_rect.bottom - 13))
            for f_idx, (fx_id, fx_sym) in enumerate(FX_BUTTONS):
                fy = 88 + f_idx * 58
                fx_rect = pygame.Rect(915, fy, 70, 50)
                pygame.draw.rect(surf, (255, 250, 240), fx_rect, border_radius=14)
                pygame.draw.rect(surf, STAGE_GOLD, fx_rect, width=2, border_radius=14)
                fx_s = self.get_text(fx_sym, FontRole.DISPLAY, 26, DARK_TEXT)
                surf.blit(fx_s, (fx_rect.centerx - fx_s.get_width() // 2, fx_rect.centery - fx_s.get_height() // 2))

        if self.app_mode == "stage":
            pygame.draw.rect(surf, (30, 24, 40), (0, 500, REFERENCE_WIDTH, 100))
            pygame.draw.rect(surf, STAGE_GOLD, (0, 500, REFERENCE_WIDTH, 4))
            tray_prev_rect = pygame.Rect(40, 522, 54, 54)
            pygame.draw.rect(surf, (255, 250, 240), tray_prev_rect, border_radius=12)
            pygame.draw.rect(surf, STAGE_GOLD, tray_prev_rect, width=2, border_radius=12)
            cx, cy = tray_prev_rect.center
            pygame.draw.polygon(surf, (61, 44, 31), [(cx - 8, cy), (cx + 6, cy - 10), (cx + 6, cy + 10)])
            tray_next_rect = pygame.Rect(930, 522, 54, 54)
            pygame.draw.rect(surf, (255, 250, 240), tray_next_rect, border_radius=12)
            pygame.draw.rect(surf, STAGE_GOLD, tray_next_rect, width=2, border_radius=12)
            cx, cy = tray_next_rect.center
            pygame.draw.polygon(surf, (61, 44, 31), [(cx + 8, cy), (cx - 6, cy - 10), (cx - 6, cy + 10)])
            page_puppets = PUPPET_ROSTER[self.tray_page * self.puppets_per_page : (self.tray_page + 1) * self.puppets_per_page]
            for p_idx, (p_id, p_name) in enumerate(page_puppets):
                card_x = 110 + p_idx * 135
                card_rect = pygame.Rect(card_x, 508, 120, 84)
                pygame.draw.rect(surf, (255, 250, 240), card_rect, border_radius=14)
                pygame.draw.rect(surf, (61, 44, 31), card_rect, width=2, border_radius=14)
                thumb = self.puppet_thumbs.get(p_id, self.puppet_thumbs.get("lilli"))
                if thumb is not None:
                    surf.blit(thumb, (card_rect.centerx - 26, card_rect.y + 6))
                loc_name = self.puppet_names.get(p_id, p_name)
                name_s = self.get_text(loc_name, FontRole.CONTROL, 11, DARK_TEXT)
                surf.blit(name_s, (card_rect.centerx - name_s.get_width() // 2, card_rect.y + 63))

        if self.app_mode == "library":
            modal_overlay = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.SRCALPHA)
            modal_overlay.fill((10, 8, 20, 220))
            surf.blit(modal_overlay, (0, 0))
            modal_layout = get_library_modal_layout(self.library_page, len(self.library_shows))
            box_rect = modal_layout["box"]
            pygame.draw.rect(surf, (255, 250, 240), box_rect, border_radius=20)
            pygame.draw.rect(surf, STAGE_GOLD, box_rect, width=4, border_radius=20)
            hdr_surf = self.get_text(f"🎬 {self._ui('stories')}", FontRole.DISPLAY, 26, DARK_TEXT)
            surf.blit(hdr_surf, (box_rect.centerx - hdr_surf.get_width() // 2, box_rect.y + 16))
            cls_rect = modal_layout["close"]
            pygame.draw.rect(surf, (254, 226, 226), cls_rect, border_radius=10)
            pygame.draw.rect(surf, (220, 38, 38), cls_rect, width=2, border_radius=10)
            cx, cy = cls_rect.center
            pygame.draw.line(surf, (185, 28, 28), (cx - 8, cy - 8), (cx + 8, cy + 8), 3)
            pygame.draw.line(surf, (185, 28, 28), (cx + 8, cy - 8), (cx - 8, cy + 8), 3)
            if not self.library_shows:
                empty_icon = self.get_text("🎬", FontRole.DISPLAY, 72, DARK_TEXT)
                surf.blit(empty_icon, (box_rect.centerx - empty_icon.get_width() // 2, box_rect.centery - 130))
                no_s = self.get_text(
                    self._ui("no_stories"),
                    FontRole.TITLE,
                    18,
                    (140, 100, 60),
                )
                surf.blit(no_s, (box_rect.centerx - no_s.get_width() // 2, box_rect.centery - 20))
            else:
                for card_info in modal_layout["cards"]:
                    s_idx = card_info["show_index"]
                    if s_idx >= len(self.library_shows):
                        continue
                    show_item = self.library_shows[s_idx]
                    c_rect = card_info["card_rect"]
                    ply_btn_rect = card_info["play_btn"]
                    del_btn_rect = card_info["del_btn"]
                    pygame.draw.rect(surf, (248, 240, 225), c_rect, border_radius=14)
                    pygame.draw.rect(surf, (180, 140, 90), c_rect, width=2, border_radius=14)
                    bg_sym = "🏡"
                    for b_id, b_sym, _ in BG_CONFIGS:
                        if b_id == show_item.get("backdrop"):
                            bg_sym = b_sym
                            break
                    bg_icon_s = self.get_text(bg_sym, FontRole.DISPLAY, 32, DARK_TEXT)
                    surf.blit(bg_icon_s, (c_rect.x + 18, c_rect.centery - bg_icon_s.get_height() // 2))
                    for a_idx, actor_id in enumerate(show_item.get("actors", [])[:3]):
                        micro = self.puppet_micro_thumbs.get(actor_id, self.puppet_micro_thumbs.get("lilli"))
                        if micro is not None:
                            surf.blit(micro, (c_rect.x + 70 + a_idx * 34, c_rect.centery - 19))
                    title_template = self._ui("story_number")
                    try:
                        title_text = title_template.format(number=s_idx + 1)
                    except (KeyError, ValueError):
                        title_text = f"{s_idx + 1}"
                    title_s = self.get_text(
                        title_text,
                        FontRole.TITLE,
                        18,
                        DARK_TEXT,
                    )
                    surf.blit(title_s, (c_rect.x + 190, c_rect.y + 16))
                    mic_indicator = "🎙️ " if show_item.get("has_audio") else ""
                    dur_text = f"{mic_indicator}{show_item.get('duration', 0)}s"
                    dur_s = self.get_text(dur_text, FontRole.CONTROL, 13, (120, 60, 20))
                    surf.blit(dur_s, (c_rect.x + 190, c_rect.y + 46))
                    pygame.draw.rect(surf, (220, 255, 225), ply_btn_rect, border_radius=12)
                    pygame.draw.rect(surf, MIC_GREEN, ply_btn_rect, width=2, border_radius=12)
                    ply_btn_s = self.get_text(f"▶️ {self._ui('play_story')}", FontRole.TITLE, 15, (20, 100, 40))
                    surf.blit(ply_btn_s, (ply_btn_rect.centerx - ply_btn_s.get_width() // 2, ply_btn_rect.centery - ply_btn_s.get_height() // 2))
                    pygame.draw.rect(surf, (255, 230, 230), del_btn_rect, border_radius=12)
                    pygame.draw.rect(surf, (220, 38, 38), del_btn_rect, width=2, border_radius=12)
                    del_btn_s = self.get_text("🗑️", FontRole.TITLE, 18, (185, 28, 28))
                    surf.blit(del_btn_s, (del_btn_rect.centerx - del_btn_s.get_width() // 2, del_btn_rect.centery - del_btn_s.get_height() // 2))
                if len(self.library_shows) > modal_layout["cards_per_page"]:
                    if self.library_page > 0:
                        prev_rect = modal_layout["prev_btn"]
                        pygame.draw.rect(surf, (255, 250, 240), prev_rect, border_radius=10)
                        pygame.draw.rect(surf, STAGE_GOLD, prev_rect, width=2, border_radius=10)
                        # Drawn arrow: language-neutral, no glyph-fallback risk.
                        pcx, pcy = prev_rect.center
                        pygame.draw.polygon(surf, DARK_TEXT, [(pcx + 6, pcy - 9), (pcx + 6, pcy + 9), (pcx - 8, pcy)])
                    if (self.library_page + 1) * modal_layout["cards_per_page"] < len(self.library_shows):
                        next_rect = modal_layout["next_btn"]
                        pygame.draw.rect(surf, (255, 250, 240), next_rect, border_radius=10)
                        pygame.draw.rect(surf, STAGE_GOLD, next_rect, width=2, border_radius=10)
                        ncx, ncy = next_rect.center
                        pygame.draw.polygon(surf, DARK_TEXT, [(ncx - 6, ncy - 9), (ncx - 6, ncy + 9), (ncx + 8, ncy)])

        if self.feedback_text and self.app_mode == "stage":
            fb_surf = self.get_text(self.feedback_text, FontRole.TITLE, 19, STAGE_GOLD)
            fb_bg = pygame.Rect(REFERENCE_WIDTH // 2 - fb_surf.get_width() // 2 - 20, 100, fb_surf.get_width() + 40, 42)
            pygame.draw.rect(surf, (20, 16, 32), fb_bg, border_radius=12)
            pygame.draw.rect(surf, STAGE_GOLD, fb_bg, width=2, border_radius=12)
            surf.blit(fb_surf, (REFERENCE_WIDTH // 2 - fb_surf.get_width() // 2, 108))

    # -- main loop --------------------------------------------------------

    def run(self) -> int:
        pygame.display.set_caption(self._ui("window_title") or "Greia")
        ready_published = False
        self.running = True
        try:
            while self.running and not activity_stop_requested():
                dt = self.clock.tick(30) / 1000.0
                self._step_frame(dt)

                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.running = False
                        break
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        if not _is_safe_point(self.screen, event.pos):
                            continue
                        logical = self.canvas.pointer(event.pos)
                        if logical is None:
                            continue
                        rx, ry = int(logical[0]), int(logical[1])
                        self._handle_mouse_down(rx, ry)
                    elif event.type == pygame.MOUSEMOTION:
                        if self.held_puppet is not None:
                            logical = self.canvas.pointer(event.pos)
                            if logical is not None:
                                rx, ry = int(logical[0]), int(logical[1])
                                self.held_puppet.x = max(
                                    180, min(840, rx + self.held_offset_x)
                                )
                                self.held_puppet.y = max(
                                    160, min(360, ry + self.held_offset_y)
                                )
                    elif (
                        event.type == pygame.MOUSEBUTTONUP
                        and event.button == 1
                    ):
                        if self.held_puppet is not None:
                            self.held_puppet.is_held = False
                            self.held_puppet = None
                    elif event.type == pygame.VIDEORESIZE:
                        self.screen = pygame.display.get_surface() or self.screen
                        self.metrics = ChildUiMetrics.for_size(
                            *self.screen.get_size()
                        )
                        self.canvas = PygameReferenceCanvas(self.screen)
                        clear_all_caches()
                        for bg_id, _, _ in BG_CONFIGS:
                            self.cached_backdrops[bg_id] = (
                                render_backdrop_surface(bg_id)
                            )

                self._draw()
                self.canvas.present(clear=self.theme.background)
                pygame.display.flip()
                if not ready_published:
                    mark_activity_ready()
                    ready_published = True
        finally:
            if self.is_recording:
                self.is_recording = False
                if self.recording_narration_track is not None:
                    self.recording_narration_track = None
                    self._stop_recording_narration()
                else:
                    try:
                        self.mic_recorder.stop_recording()
                    except Exception:
                        pass
            else:
                self._stop_recording_narration()
            if self.playback_audio_channel is not None:
                try:
                    self.playback_audio_channel.stop()
                except Exception:
                    pass
                self.playback_audio_channel = None
            pygame.quit()
        return 0

__all__ = ["TeatrinoApp"]
