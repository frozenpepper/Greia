"""Lifecycle owner for Teatrino delle Fiabe (Fairy Tale Puppet Theatre).

The child stages a show with no words on screen: pick friends from the tray
(they pop up on their rods), pick a scene, then press the big record button.
The curtain closes, Lilli says "Come on, let's go!", three gold lamps go out
one by one and the curtain opens: the child moves the puppets and tells the
story while the microphone (or a voice chosen from My Creations) records.
The held puppet's mouth moves with the child's voice. Stop closes the
curtain and saves the show; a curtain call shows its poster, Lilli cheers,
and the show can be watched, shared as a picture to My Creations, or left.

This class coordinates; the work lives in focused collaborators:
``Stage``/``ShowRecorder``/``ShowPlayback`` (pure model), ``VoiceSource``
(microphone / narration capture), ``CreationsBridge`` (picker + publish),
``ShowLibrary`` (shelf, paging, deliberate delete), ``TheatreControls`` (kit
controls) and ``TheatreRenderer``/``PosterStudio`` (drawing).

Coordinates are 1024x600 logical pixels (``PygameReferenceCanvas``); every
control is a shared kit control (ADR 0037) usable with pointer, touch,
keyboard and controller; puppets are dragged with the pointer or picked up,
moved and put down with the keyboard / D-pad.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
import hashlib
import io
import time

import pygame

from greia_platform.activity_api import (
    activity_stop_requested,
    emit_activity_event,
    mark_activity_ready,
)
from greia_platform.activity_controls import (
    ButtonRole,
    ControlKit,
    ControlLayout,
    ControlTheme,
    KitPointer,
    PointerPhase,
    PygameControlInput,
)
from greia_platform.activity_feedback import CastFeedback, IdleHintScheduler
from greia_platform.frame_governor import FrameGovernor, FrameKind
from greia_platform.input_core import InputEdge, InputSource, SemanticAction, SemanticInputEvent
from greia_platform.pygame_canvas import PygameReferenceCanvas, activity_viewport_for_surface
from greia_platform.pygame_png import PygamePngError, encode_surface_png
from greia_platform.typography import GreiaTypography
from greia_platform.ui_core import SurfaceNavigator, UiEventResult

if __package__:
    from .teatrino_art import FxPlayer, TeatrinoArt
    from .teatrino_audio import VOICE_THRESHOLD, HostVoice, ImportedNarrationTrack, MicrophoneRecorder, SoundManager
    from .teatrino_content import (
        DEFAULT_SCENE,
        FX_BY_SOUND,
        HOST,
        OPENING_CAST,
        PUPPET_IDS,
        PUPPETS_BY_ID,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        SCENE_IDS,
        VOICE_READY,
        VOICE_SAVED,
        VOICE_WATCHED,
        ArtSource,
    )
    from .teatrino_controls import StageMode, TheatreControls, TheatreSheet, dialog_layer, scene_sheet_layer
    from .teatrino_creations import CreationsBridge
    from .teatrino_layout import DialogLayout, GridLayout, TheatreLayout
    from .teatrino_library import ShowLibrary
    from .teatrino_model import (
        Puppet,
        ShowLibraryFullError,
        ShowPlayback,
        ShowRecorder,
        ShowRepository,
        ShowStorageError,
        Stage,
    )
    from .teatrino_renderer import POSTER_ASPECT, PosterStudio, TheatreRenderer, decode_backdrop, picture_size, rounded
    from .teatrino_voice import VoiceSource
else:
    from teatrino_art import FxPlayer, TeatrinoArt
    from teatrino_audio import VOICE_THRESHOLD, HostVoice, ImportedNarrationTrack, MicrophoneRecorder, SoundManager
    from teatrino_content import (
        DEFAULT_SCENE,
        FX_BY_SOUND,
        HOST,
        OPENING_CAST,
        PUPPET_IDS,
        PUPPETS_BY_ID,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        SCENE_IDS,
        VOICE_READY,
        VOICE_SAVED,
        VOICE_WATCHED,
        ArtSource,
    )
    from teatrino_controls import StageMode, TheatreControls, TheatreSheet, dialog_layer, scene_sheet_layer
    from teatrino_creations import CreationsBridge
    from teatrino_layout import DialogLayout, GridLayout, TheatreLayout
    from teatrino_library import ShowLibrary
    from teatrino_model import (
        Puppet,
        ShowLibraryFullError,
        ShowPlayback,
        ShowRecorder,
        ShowRepository,
        ShowStorageError,
        Stage,
    )
    from teatrino_renderer import POSTER_ASPECT, PosterStudio, TheatreRenderer, decode_backdrop, picture_size, rounded
    from teatrino_voice import VoiceSource

STAGE_STATE_KEY = "teatrino.stage.v1"
CURTAIN_SECONDS = 0.5
COUNTDOWN_BEAT = 0.6
# The theatre waits longer than other Activities before its first nudge, then
# backs off like the rest: 8 s, +12 s, +24 s, silent until the next input.
HINT_GAPS = (8.0, 12.0, 24.0)
HINT_GLOW_SECONDS = 3.0
DRAG_SLOP = 10
KEY_STEP = 28
SCENE_COLUMNS, SCENE_ROWS = 4, 2
MAX_SCHEDULED = 16
HOST_CUES = (VOICE_READY, VOICE_SAVED, VOICE_WATCHED)
COUNTDOWN_LINE = "three_two_one"  # Lilli's owner-approved package line
KNOWN_PUPPETS = frozenset(PUPPET_IDS)
SCENES_ID = "teatrino.scenes"
VOICE_ID = "teatrino.voice"
CALL_ID = "teatrino.call"


def _is_safe_point(surface: pygame.Surface, position: tuple[int, int]) -> bool:
    vp = activity_viewport_for_surface(surface)
    x, y = position
    if not (0 <= x < vp.surface.width and 0 <= y < vp.surface.height):
        return False
    for protected in vp.protected_regions:
        if protected.x <= x < protected.right and protected.y <= y < protected.bottom:
            return False
    return True


class Timeline:
    """Tiny bounded scheduler for the curtain / countdown moments."""

    def __init__(self, clock: Callable[[], float]) -> None:
        self._clock = clock
        self._entries: deque[tuple[float, Callable[[], object]]] = deque(maxlen=MAX_SCHEDULED)

    def after(self, delay: float, action: Callable[[], object]) -> None:
        self._entries.append((self._clock() + delay, action))

    def run_due(self) -> bool:
        now = self._clock()
        due = sorted((entry for entry in self._entries if entry[0] <= now), key=lambda entry: entry[0])
        for entry in due:
            if entry in self._entries:
                self._entries.remove(entry)
            entry[1]()
        return bool(due)

    @property
    def busy(self) -> bool:
        return bool(self._entries)

    def clear(self) -> None:
        self._entries.clear()


class Curtain:
    """Main stage curtain: 0 = open, 1 = closed, eased over ``CURTAIN_SECONDS``."""

    def __init__(self, clock: Callable[[], float], value: float = 0.0) -> None:
        self._clock = clock
        self._from = value
        self._to = value
        self._start = 0.0

    def move(self, target: float) -> None:
        self._from = self.value
        self._to = float(target)
        self._start = self._clock()

    def set(self, value: float) -> None:
        self._from = self._to = float(value)

    @property
    def value(self) -> float:
        if self._from == self._to:
            return self._to
        progress = min(1.0, (self._clock() - self._start) / CURTAIN_SECONDS)
        if progress >= 1.0:
            self._from = self._to
        return self._from + (self._to - self._from) * progress

    @property
    def moving(self) -> bool:
        return self.value != self._to


class TeatrinoApp:
    """Coordinate the puppet theatre: stage, recording, shows, sheets, input."""

    _hinting = False  # idle hint glow active (ambient motion), set by step()

    def __init__(
        self,
        screen: pygame.Surface | None = None,
        *,
        storage=None,
        creations=None,
        locale: str = "it",
        clock: Callable[[], float] = time.monotonic,
        sounds: SoundManager | None = None,
        microphone: MicrophoneRecorder | None = None,
        host_voice: HostVoice | None = None,
        art: TeatrinoArt | None = None,
        typography: GreiaTypography | None = None,
        emit_event: Callable[..., object] | None = None,
    ) -> None:
        pygame.font.init()
        if screen is None:
            screen = pygame.display.get_surface()
            if screen is None:
                screen = pygame.display.set_mode((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.RESIZABLE)
        self.screen = screen
        self.canvas = PygameReferenceCanvas(screen, hires=True)
        self.clock = clock
        self.storage = storage
        self._emit = emit_event if emit_event is not None else emit_activity_event
        self.show_repo = ShowRepository(storage)
        self.typography = typography if typography is not None else GreiaTypography()
        # Create Collection hue (coral) as the kit accent: one family with Painting.
        self.kit = ControlKit(self.typography, ControlTheme.for_accent("coral"))
        self.art = art if art is not None else TeatrinoArt()
        self.layout = TheatreLayout.build(ControlLayout.for_canvas(self.canvas, screen.get_size()))
        self.renderer = TheatreRenderer(self.art, self.kit, self.layout, clock=clock)
        self.posters = PosterStudio(self.art, self.renderer, self.show_repo)
        self.sound_mgr = sounds if sounds is not None else SoundManager()
        self.voice = VoiceSource(microphone if microphone is not None else MicrophoneRecorder())
        self.host = host_voice if host_voice is not None else HostVoice(HOST, HOST_CUES, locale)
        try:
            self.cast: CastFeedback | None = CastFeedback(HOST, height=170, art=self.kit.art, clock=clock, hold_seconds=2.2)
            # A smaller Lilli for the shows shelf header ("hmm, it's full").
            self.shelf_cast: CastFeedback | None = CastFeedback(
                HOST, height=96, art=self.kit.art, clock=clock, hold_seconds=3.0
            )
        except ValueError:
            self.cast = self.shelf_cast = None
        self.bridge = CreationsBridge(
            creations,
            clock=clock,
            on_backdrop=self._set_custom_backdrop,
            on_narration=self._set_narration,
            on_error=self._oops,
        )
        self.fx = FxPlayer(self.art, clock)
        self.timeline = Timeline(clock)
        self.curtain = Curtain(clock)

        self.stage = Stage(self.layout.bounds)
        self.scene_id = DEFAULT_SCENE
        self.custom_backdrop_png: bytes | None = None
        self.custom_backdrop_surface: pygame.Surface | None = None
        self._custom_key = ""
        self.mode = StageMode.EDIT
        self.recorder = ShowRecorder()
        self.rec_started = 0.0
        self.last_recorded_wav: bytes | None = None
        self.save_error = False
        self.saved_meta: dict | None = None
        self.countdown_started = 0.0
        self._countdown_lamps = 3
        self._countdown_beat_at = 0.0

        self.playback: ShowPlayback | None = None
        self.playback_show_meta: dict | None = None
        self.playback_audio_channel = None
        self.playback_wav: bytes | None = None
        self.play_start_time = 0.0
        self._watch_restore: tuple | None = None
        self._dialog: DialogLayout | None = None

        self.held: Puppet | None = None
        self.key_grab = False
        self._drag_from: tuple[int, int] | None = None
        self._drag_offset = (0.0, 0.0)
        self._dragged = False
        self.speaker_id: str | None = None
        self._last_activity = clock()
        self._hints = IdleHintScheduler(HINT_GAPS, now=self._last_activity)
        self._hint_until = 0.0
        self._last_frame = clock()
        self._dirty = True
        self.running = True

        self.controls = TheatreControls(
            self.kit,
            self.art,
            self.layout,
            on_shows=self._open_library,
            on_scene=self._open_scene_sheet,
            on_clear=self._clear_stage,
            on_mic=self._open_voice_sheet,
            on_rec=self._press_rec,
            on_fx=self._play_fx,
            on_card=self._tray_card,
            on_page=self._tray_page,
            on_puppet=self._keyboard_grab,
        )
        self.surfaces = SurfaceNavigator(self.controls.layer)
        self.library = ShowLibrary(
            self.show_repo,
            kit=self.kit,
            renderer=self.renderer,
            posters=self.posters,
            surfaces=self.surfaces,
            layout=lambda: self.layout,
            clock=clock,
            play=self.sound_mgr.play,
            on_watch=self._watch_show,
            on_record=self._start_recording,
            draw_host=self._draw_shelf_host,
        )
        self._input = self._make_input()
        self._restore_stage()
        self._sync_all()

    # ------------------------------------------------------------------
    # read-only views used by tests/tools
    # ------------------------------------------------------------------

    @property
    def creations(self):
        return self.bridge.creations

    @property
    def mic_recorder(self) -> MicrophoneRecorder:
        return self.voice.microphone

    @property
    def imported_narration(self) -> ImportedNarrationTrack | None:
        return self.voice.imported

    @property
    def library_shows(self) -> list[dict]:
        return self.library.shows

    @property
    def delete_confirm(self):
        return self.library.confirm

    @property
    def puppets_on_stage(self) -> list[Puppet]:
        return self.stage.puppets

    @property
    def is_recording(self) -> bool:
        return self.mode == StageMode.RECORDING

    @property
    def top_sheet(self) -> str:
        """Id of the open sheet ('' on the stage)."""

        overlays = self.surfaces.overlays
        return overlays[-1].surface_id if overlays else ""

    # ------------------------------------------------------------------
    # staging persistence (where friends stand; not a saved show)
    # ------------------------------------------------------------------

    def _make_input(self) -> PygameControlInput:
        return PygameControlInput(to_logical=self.canvas.pointer, is_safe=lambda pos: _is_safe_point(self.screen, pos))

    def _restore_stage(self) -> None:
        state = None
        if self.storage is not None:
            try:
                state = self.storage.kv_get(STAGE_STATE_KEY, None)
            except Exception:
                state = None
        if isinstance(state, dict) and isinstance(state.get("puppets"), list):
            scene = state.get("scene")
            self.scene_id = scene if scene in SCENE_IDS else DEFAULT_SCENE
            self.stage.restore(state["puppets"], KNOWN_PUPPETS)
            return
        bounds = self.stage.bounds
        for index, puppet_id in enumerate(OPENING_CAST):
            self.stage.add(puppet_id, x=bounds.left + (bounds.right - bounds.left) * (0.3 + 0.4 * index))

    def _remember_stage(self) -> None:
        if self.storage is None or self.mode == StageMode.WATCHING:
            return
        try:
            self.storage.kv_set(STAGE_STATE_KEY, {"scene": self.scene_id, "puppets": self.stage.snapshot()})
        except Exception:
            pass

    # ------------------------------------------------------------------
    # main loop
    # ------------------------------------------------------------------

    def run(self) -> int:
        ready_published = False
        frames = FrameGovernor()
        self.running = True
        try:
            while self.running and not activity_stop_requested():
                for event in frames.events():
                    self.handle_event(event)
                repeat = self._input.poll()
                if repeat is not None:
                    self._dispatch(repeat)
                animating = self.step()
                frame = frames.frame(dirty=self._dirty, animating=animating, ambient=self._hinting)
                if frame is FrameKind.FULL:
                    self.render()
                    self._dirty = False
                    self.canvas.present(clear=(0, 0, 0))
                    pygame.display.flip()
                    if not ready_published:
                        mark_activity_ready()
                        ready_published = True
                elif frame is FrameKind.POINTER:
                    # Only the platform pointer moved: no scene re-render.
                    self.canvas.present_pointer()
                frames.wait(polling=self._input.repeating)
        finally:
            self.shutdown()
        return 0

    def shutdown(self) -> None:
        """Stop capture/playback and keep the staging; never saves a show."""

        if self.mode in (StageMode.RECORDING, StageMode.COUNTDOWN):
            self.recorder.stop()
            self.voice.abort()
            self.mode = StageMode.EDIT
        self._stop_playback_audio()
        if self.mode == StageMode.WATCHING:
            self._restore_after_watching()
        self._remember_stage()
        self.host.stop()

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self.running = False
            return
        if event.type == pygame.VIDEORESIZE:
            self._on_resize()
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._escape()
            return
        translated = self._input.translate(event)
        if translated is not None:
            self._dispatch(translated)

    def _escape(self) -> None:
        if self.surfaces.overlays:
            self._dispatch(SemanticInputEvent(SemanticAction.CANCEL, InputEdge.PRESSED, InputSource.KEYBOARD))
        elif self.key_grab and self.held is not None:
            self._drop_held()
        elif self.mode == StageMode.RECORDING:
            self._press_rec()
        elif self.mode == StageMode.WATCHING:
            self._stop_watching()
        elif self.mode == StageMode.EDIT:
            self.running = False

    def _on_resize(self) -> None:
        self.screen = pygame.display.get_surface() or self.screen
        self.canvas = PygameReferenceCanvas(self.screen, hires=True)
        self._input = self._make_input()
        self.layout = TheatreLayout.build(ControlLayout.for_canvas(self.canvas, self.screen.get_size()))
        self.renderer.relayout(self.layout)
        self.controls.relayout(self.layout)
        self._close_sheets()
        self._sync_all()

    # ------------------------------------------------------------------
    # per frame
    # ------------------------------------------------------------------

    def step(self) -> bool:
        """Advance time; return True while something on screen moves."""

        now = self.clock()
        dt = min(0.1, max(0.0, now - self._last_frame))
        self._last_frame = now
        if self.timeline.run_due():
            self._dirty = True
        self.bridge.poll(now)
        if self.mode == StageMode.RECORDING:
            self._step_recording(now)
        elif self.mode == StageMode.WATCHING and self.playback is not None:
            self._step_playback(now)
        self.stage.update(dt)
        for friend in (self.cast, self.shelf_cast):
            if friend is not None and friend.update():
                self._dirty = True
        self.fx.prune()
        if self.library.sync_arming(now):
            self._dirty = True
        overlays = self.surfaces.overlays
        if overlays and getattr(overlays[-1], "layer", None) is not None and overlays[-1].layer.invalidation.should_draw:
            self._dirty = True
        if self.controls.layer.invalidation.should_draw:
            self._dirty = True
        # The idle hint glow is a short, bounded invitation (ambient motion at
        # the reduced frame rate once the child is idle), never a permanent one.
        self._advance_hint(now)
        self._hinting = self._hint_target(now) is not None
        return (
            self.mode != StageMode.EDIT
            or self.stage.animating
            or self.curtain.moving
            or self.fx.active
            or any(f is not None and f.animating for f in (self.cast, self.shelf_cast))
            or self.timeline.busy
        )

    def _step_recording(self, now: float) -> None:
        elapsed = now - self.rec_started
        level = self.voice.level(elapsed)
        speaker = self.stage.find(self.speaker_id) if self.speaker_id else None
        for puppet in self.stage.puppets:
            puppet.voice_talking = puppet is speaker and level > VOICE_THRESHOLD
        self.recorder.sample(now, self.stage)
        limit = self.voice.limit
        if elapsed >= limit:
            self._finish_recording(min(elapsed, limit))
            self._after_recording()

    def _step_playback(self, now: float) -> None:
        playback = self.playback
        assert playback is not None
        t = now - self.play_start_time
        if t < 0:
            return
        for sound in playback.drive(self.stage, t, KNOWN_PUPPETS):
            self._perform_fx(sound, record=False)
        if playback.finished(t):
            self._playback_finished()

    # ------------------------------------------------------------------
    # input routing
    # ------------------------------------------------------------------

    def _dispatch(self, kit_input) -> UiEventResult:
        is_pointer = isinstance(kit_input, KitPointer)
        if not is_pointer or kit_input.phase is not PointerPhase.MOVE:
            self._last_activity = self.clock()
            self._hints.reset(self._last_activity)
            self._hint_until = 0.0
        self._dirty = True
        if self.surfaces.overlays:
            result = self.surfaces.dispatch(kit_input)
            self.library.after_input()
            return result
        if is_pointer and self._drag_input(kit_input):
            return UiEventResult.HANDLED
        if not is_pointer and self.key_grab and self.held is not None and self._key_grab_input(kit_input):
            return UiEventResult.HANDLED
        result = self.surfaces.dispatch(kit_input)
        if result is UiEventResult.IGNORED and is_pointer and kit_input.phase is PointerPhase.DOWN:
            self._maybe_pick(kit_input.position)
        return result

    def tap(self, point: tuple[int, int]) -> None:
        """Deliver one logical tap (tests/tools)."""

        self._dispatch(KitPointer(PointerPhase.DOWN, (int(point[0]), int(point[1]))))
        self._dispatch(KitPointer(PointerPhase.UP, (int(point[0]), int(point[1]))))

    def drag(self, start: tuple[int, int], end: tuple[int, int], steps: int = 6) -> None:
        """Deliver one logical drag (tests/tools)."""

        self._dispatch(KitPointer(PointerPhase.DOWN, start))
        for index in range(1, steps + 1):
            x = start[0] + (end[0] - start[0]) * index // steps
            y = start[1] + (end[1] - start[1]) * index // steps
            self._dispatch(KitPointer(PointerPhase.MOVE, (x, y)))
        self._dispatch(KitPointer(PointerPhase.UP, end))

    def press(self, key: int) -> None:
        """Deliver one key press through the shared navigation mapping."""

        if key == pygame.K_ESCAPE:
            self._escape()
            return
        translated = self._input.translate(pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode=""))
        if translated is not None:
            self._dispatch(translated)

    # -- puppets: pointer drag ----------------------------------------------------

    def _maybe_pick(self, point: tuple[int, int]) -> None:
        if self.mode not in (StageMode.EDIT, StageMode.RECORDING):
            return
        puppet = self.stage.hit(*point)
        if puppet is None:
            return
        if self.held is not None:
            self._drop_held()
        self.held = puppet
        self.key_grab = False
        puppet.held = True
        self.stage.raise_to_front(puppet)
        self.speaker_id = puppet.puppet_id
        self._drag_from = point
        self._drag_offset = (puppet.x - point[0], puppet.y - point[1])
        self._dragged = False
        self.sound_mgr.play("pop")

    def _drag_input(self, pointer: KitPointer) -> bool:
        if self._drag_from is None or self.held is None or self.key_grab:
            return False
        puppet = self.held
        if pointer.phase is PointerPhase.MOVE:
            dx = pointer.position[0] - self._drag_from[0]
            dy = pointer.position[1] - self._drag_from[1]
            if not self._dragged and dx * dx + dy * dy >= DRAG_SLOP * DRAG_SLOP:
                self._dragged = True
            if self._dragged:
                self.stage.move(
                    puppet,
                    pointer.position[0] + self._drag_offset[0],
                    pointer.position[1] + self._drag_offset[1],
                    allow_remove=True,
                )
            return True
        if pointer.phase is PointerPhase.DOWN:
            return True
        dragged = self._dragged
        self._drag_from = None
        self._dragged = False
        if not dragged and pointer.phase is PointerPhase.UP:
            # A tap on a puppet: it bows and says hello.
            puppet.held = False
            self.held = None
            puppet.bow()
            puppet.speak()
            self.sound_mgr.play("giggle")
            return True
        self._drop_held()
        return True

    def _drop_held(self) -> None:
        puppet = self.held
        if puppet is None:
            return
        puppet.held = False
        self.held = None
        self.key_grab = False
        if self.stage.in_remove_zone(puppet):
            self._take_off(puppet)
        else:
            self.stage.move(puppet, puppet.x, puppet.y)
        self._sync_puppet_targets()
        self._remember_stage()

    def _take_off(self, puppet: Puppet) -> None:
        """Back into the box: a dust puff where it went down."""

        self.stage.remove(puppet.puppet_id)
        self.fx.burst("dust_puff", (int(puppet.x), int(self.layout.tray.top - 10)))
        self.sound_mgr.play("poof")
        if self.speaker_id == puppet.puppet_id:
            self.speaker_id = None
        self.controls.sync_cards(self.stage.ids())

    # -- puppets: keyboard / controller ------------------------------------------------

    def _keyboard_grab(self, puppet_id: str) -> None:
        """ACTIVATE on a focused puppet picks it up (again: puts it down)."""

        if self.mode not in (StageMode.EDIT, StageMode.RECORDING):
            return
        puppet = self.stage.find(puppet_id)
        if puppet is None:
            return
        if self.held is puppet:
            self._drop_held()
            return
        if self.held is not None:
            self._drop_held()
        self.held = puppet
        self.key_grab = True
        puppet.held = True
        self.speaker_id = puppet_id
        self.sound_mgr.play("pop")

    def _key_grab_input(self, event) -> bool:
        if not isinstance(event, SemanticInputEvent) or event.edge is not InputEdge.PRESSED:
            return False
        puppet = self.held
        assert puppet is not None
        moves = {
            SemanticAction.NAV_LEFT: (-KEY_STEP, 0),
            SemanticAction.NAV_RIGHT: (KEY_STEP, 0),
            SemanticAction.NAV_UP: (0, -KEY_STEP),
            SemanticAction.NAV_DOWN: (0, KEY_STEP),
            SemanticAction.MOVE_LEFT: (-KEY_STEP, 0),
            SemanticAction.MOVE_RIGHT: (KEY_STEP, 0),
            SemanticAction.MOVE_UP: (0, -KEY_STEP),
            SemanticAction.MOVE_DOWN: (0, KEY_STEP),
        }
        if event.action in moves:
            dx, dy = moves[event.action]
            self.stage.move(puppet, puppet.x + dx, puppet.y + dy, allow_remove=True)
            self._sync_puppet_targets()
            return True
        if event.action in (SemanticAction.ACTIVATE, SemanticAction.PRIMARY, SemanticAction.CANCEL):
            removed = self.stage.in_remove_zone(puppet)
            self._drop_held()
            if not removed:
                self.controls.layer.focus(f"puppet.{puppet.puppet_id}", visible=True)
            return True
        return False

    # -- tray ------------------------------------------------------------------------

    def _tray_card(self, puppet_id: str) -> None:
        if self.mode not in (StageMode.EDIT, StageMode.RECORDING):
            return
        existing = self.stage.find(puppet_id)
        if existing is not None:
            # Already on stage: it waves hello (a tap never removes a friend).
            cast = PUPPETS_BY_ID[puppet_id].source == ArtSource.CAST
            existing.react("pose_wave" if cast else None)
            existing.speak()
            self.speaker_id = puppet_id
            self.sound_mgr.play("pop")
            return
        if self.stage.full:
            # No more room: the friends on stage wobble "we're full!".
            self.sound_mgr.play("full")
            self.host.say_if_quiet("stage_full")  # "The stage is full!" (never restarted by mashing)
            card = self.controls.card_for(puppet_id)
            if card is not None:
                self.fx.burst("dust_puff", card.rect.midtop)
            for puppet in self.stage.puppets:
                puppet.speak(0.4)
            return
        puppet = self.stage.add(puppet_id)
        if puppet is None:
            return
        puppet.jump()
        puppet.speak()
        self.speaker_id = puppet_id
        self.sound_mgr.play("pop")
        self.fx.burst("sparkle", (int(puppet.x), int(puppet.y)))
        self._sync_puppet_targets()
        self.controls.sync_cards(self.stage.ids())
        self._remember_stage()

    def _tray_page(self, direction: int) -> None:
        self.controls.set_page(self.controls.page + direction, self.stage.ids())
        self.sound_mgr.play("pop")

    def _clear_stage(self) -> None:
        if self.mode != StageMode.EDIT or not self.stage.puppets:
            return
        for puppet in self.stage.puppets:
            self.fx.burst("dust_puff", (int(puppet.x), int(puppet.y)))
        self.stage.clear()
        self.held = None
        self.key_grab = False
        self.speaker_id = None
        self.sound_mgr.play("poof")
        self._sync_puppet_targets()
        self.controls.sync_cards(())
        self._remember_stage()

    # -- sound stickers ------------------------------------------------------------------

    def _play_fx(self, sound: str) -> None:
        if self.mode in (StageMode.EDIT, StageMode.RECORDING):
            self._perform_fx(sound, record=True)

    def _perform_fx(self, sound: str, *, record: bool) -> None:
        spec = FX_BY_SOUND.get(sound)
        self.sound_mgr.play(sound)
        for puppet in self.stage.puppets:
            source = PUPPETS_BY_ID.get(puppet.puppet_id)
            cast = spec is not None and source is not None and source.source == ArtSource.CAST
            puppet.react(spec.reaction if cast else None)
        if spec is not None:
            bounds = self.stage.bounds
            self.fx.burst(spec.burst, (int((bounds.left + bounds.right) / 2), int(bounds.top + 40)))
        if record and self.mode == StageMode.RECORDING:
            self.recorder.note_sfx(self.clock(), sound)

    # -- voice choice ---------------------------------------------------------------------

    def _open_voice_sheet(self) -> None:
        """Choose the show's voice: my microphone, no voice, or a saved voice."""

        if self.mode != StageMode.EDIT:
            return
        options: list[tuple[str, str, ButtonRole, Callable[[], object]]] = [
            ("voice.on", "mic", ButtonRole.NEUTRAL, lambda: self._choose_voice(VoiceSource.ON)),
            ("voice.off", "mic_off", ButtonRole.NEUTRAL, lambda: self._choose_voice(VoiceSource.OFF)),
        ]
        if self.bridge.available:
            options.append(("voice.imported", "", ButtonRole.NEUTRAL, lambda: self._choose_voice("mine")))
        dialog = DialogLayout.build(self.layout, buttons=len(options), width=560, height=240, picture=False)
        current = f"voice.{self.voice.state}"
        layer = dialog_layer(self.kit, dialog, options, layer_id="teatrino.voice.controls", focus=current)
        if self.bridge.available:
            mine = layer.target("voice.imported")
            mine.icon = self.art.icon("ui.pictogram.creation", int(dialog.buttons[-1].height * 0.62), variant="audio")
        if current in {t.control_id for t in layer.targets}:
            layer.target(current).selected = True
        self._push_sheet(
            TheatreSheet(
                VOICE_ID,
                layer,
                dialog.panel,
                on_dismiss=self._close_sheets,
                draw_backdrop=lambda target: self._draw_dialog(target, dialog, None),
            )
        )
        self.sound_mgr.play("pop")

    def _choose_voice(self, choice: str) -> None:
        self._close_sheets()
        if choice == "mine":
            self.bridge.request_narration()
            return
        self.voice.choose(choice)
        self.sound_mgr.play("pop")
        self._sync_mic()

    def _set_narration(self, track: ImportedNarrationTrack) -> None:
        self.voice.use_narration(track)
        self._sync_mic()
        self.sound_mgr.play("magic")

    def _sync_mic(self) -> None:
        self.controls.set_mic_state(self.voice.state)

    # ------------------------------------------------------------------
    # recording
    # ------------------------------------------------------------------

    def _press_rec(self) -> None:
        if self.mode == StageMode.EDIT:
            self._start_recording()
        elif self.mode == StageMode.RECORDING:
            self._finish_recording(max(0.05, self.clock() - self.rec_started))
            self._after_recording()
        elif self.mode == StageMode.WATCHING:
            self._stop_watching()

    def _show_shelf_full(self) -> None:
        """Friendly full-shelf state: the shows open, Lilli thinks, nothing goes.

        The child removes a show on purpose (with confirmation) before another
        can be saved.
        """

        self.sound_mgr.play("full")
        self._close_sheets()
        self.library.open(full=True)
        if self.shelf_cast is not None:
            self.shelf_cast.try_again()

    def _start_recording(self) -> bool:
        """Start the curtain ritual; capture begins when the curtain opens."""

        if self.mode != StageMode.EDIT:
            return False
        if self.show_repo.is_full():
            # Refuse *before* a 45 s performance is recorded and lost.
            self._show_shelf_full()
            return False
        if self.held is not None:
            self._drop_held()
        self.save_error = False
        self.mode = StageMode.COUNTDOWN
        self._sync_mode()
        self.curtain.move(1.0)
        self.sound_mgr.play("curtain")
        self.countdown_started = self.clock()
        self._countdown_beat_at = self.countdown_started
        self._countdown_lamps = 3
        countdown = self.host.say(COUNTDOWN_LINE)  # "Three, two, one... action!"
        if countdown > 0.0:
            # The lamps tick through the end of the line, and the curtain (and
            # microphone) opens only once "action!" is over: the host's voice
            # never lands inside the child's recording.
            lead = max(CURTAIN_SECONDS + 0.2, countdown + 0.15 - 3 * COUNTDOWN_BEAT)
        else:
            lead = max(CURTAIN_SECONDS + 0.2, min(1.6, self.host.say(VOICE_READY)))
        for index in range(3):
            self.timeline.after(lead + index * COUNTDOWN_BEAT, self._countdown_tick)
        self.timeline.after(lead + 3 * COUNTDOWN_BEAT, self._open_for_recording)
        return True

    def _countdown_tick(self) -> None:
        self._countdown_lamps = max(0, self._countdown_lamps - 1)
        self._countdown_beat_at = self.clock()
        self.sound_mgr.play("go" if self._countdown_lamps == 0 else "pip")

    def _open_for_recording(self) -> None:
        if self.mode != StageMode.COUNTDOWN:
            return
        self.curtain.move(0.0)
        self.sound_mgr.play("curtain")
        self.host.stop()  # nothing of the host may reach the microphone
        if not self._begin_capture():
            self.mode = StageMode.EDIT
            self._sync_mode()

    def _begin_capture(self) -> bool:
        """Open the voice source and start sampling the stage."""

        if not self.voice.start():
            self._oops()
            return False
        now = self.clock()
        self.rec_started = now
        self.recorder.start(now)
        self.recorder.sample(now, self.stage, force=True)
        self.mode = StageMode.RECORDING
        self._sync_mode()
        return True

    def _finish_recording(self, elapsed: float) -> dict | None:
        """Stop capture and save the show; returns the saved metadata or None."""

        if self.mode != StageMode.RECORDING:
            return None
        self.recorder.sample(self.clock(), self.stage, force=True)
        self.recorder.stop()
        self.mode = StageMode.EDIT
        for puppet in self.stage.puppets:
            puppet.voice_talking = False
        elapsed = max(0.05, float(elapsed))
        try:
            wav_bytes = self.voice.finish(elapsed)
        except ValueError:
            self._oops()
            self._sync_mode()
            return None
        self.last_recorded_wav = wav_bytes
        saved = self._persist_recorded_show(self.scene_id, elapsed, wav_bytes)
        self._sync_mode()
        return saved

    def _after_recording(self) -> None:
        """Close the curtain; the curtain call follows a saved show."""

        self.curtain.move(1.0)
        self.sound_mgr.play("curtain")
        meta = self.saved_meta
        if meta is not None:
            self.timeline.after(CURTAIN_SECONDS + 0.05, lambda: self._curtain_call(meta, watched=False))
        else:
            self.timeline.after(CURTAIN_SECONDS + 0.4, lambda: self.curtain.move(0.0))

    def _persist_recorded_show(self, scene_id: str, elapsed: float, wav_bytes: bytes | None) -> dict | None:
        self.saved_meta = None
        try:
            saved_meta = self.show_repo.save_show(
                scene_id,
                [{"id": puppet_id} for puppet_id in self._show_cast()],
                self.recorder.frames,
                self.recorder.sfx,
                elapsed,
                wav_bytes,
                self.custom_backdrop_png,
                poster=self.stage.snapshot(),
            )
        except ShowLibraryFullError:
            self._show_shelf_full()
            return None
        except (ShowStorageError, ValueError, OSError):
            self.library.refresh()
            self._oops()
            return None
        self.library.refresh()
        self.saved_meta = saved_meta
        try:
            self._emit(
                "story.recorded",
                idempotency_key=f"rec-{saved_meta['id']}",
                payload={"duration": round(elapsed, 1), "id": saved_meta["id"]},
            )
        except Exception:
            pass
        self.sound_mgr.play("applause")
        return saved_meta

    def _show_cast(self) -> list[str]:
        """Every puppet that appeared during the recording, in order."""

        seen: list[str] = []
        for frame in self.recorder.frames:
            for item in frame.get("puppets", []):
                if item.get("id") not in seen:
                    seen.append(item["id"])
        for puppet_id in self.stage.ids():
            if puppet_id not in seen:
                seen.append(puppet_id)
        return seen

    def _oops(self) -> None:
        """A save/voice/picker problem: Lilli thinks, a soft boing; nothing is lost."""

        self.save_error = True
        self.sound_mgr.play("boing")
        if self.cast is not None:
            self.cast.try_again()

    # ------------------------------------------------------------------
    # watching a show
    # ------------------------------------------------------------------

    def _watch_show(self, show_item: dict) -> bool:
        show_data, wav_bytes = self.show_repo.load_show(show_item["id"])
        if not show_data:
            self._oops()
            return False
        if self.mode == StageMode.EDIT and self._watch_restore is None:
            self._watch_restore = (
                self.scene_id,
                self.custom_backdrop_png,
                self.custom_backdrop_surface,
                self._custom_key,
                self.stage.snapshot(),
            )
        self._close_sheets()
        saved_scene = show_item.get("backdrop")
        self.scene_id = saved_scene if saved_scene in SCENE_IDS else DEFAULT_SCENE
        payload = self.show_repo.load_show_backdrop(show_item["id"])
        surface = decode_backdrop(payload)
        self._apply_backdrop(payload if surface is not None else None, surface, str(show_item.get("backdrop_sha256") or ""))
        frames = show_data.get("frames")
        sfx = show_data.get("sfx_events")
        self.playback = ShowPlayback(
            frames if isinstance(frames, list) else [],
            sfx if isinstance(sfx, list) else [],
            float(show_item.get("duration", 5.0) or 5.0),
        )
        self.playback_show_meta = show_item
        self.playback_wav = wav_bytes
        self.stage.puppets = []
        self.held = None
        self.key_grab = False
        self.mode = StageMode.WATCHING
        self._sync_all()
        # Curtain closed -> opens, then the show (and its voice) begins.
        self.curtain.set(1.0)
        self.timeline.clear()
        self.timeline.after(0.15, self._begin_playback)
        self.play_start_time = float("inf")  # nothing moves before the curtain opens
        self.sound_mgr.play("trumpet")
        return True

    def _begin_playback(self) -> None:
        if self.mode != StageMode.WATCHING or self.playback is None:
            return
        self.curtain.move(0.0)
        self.playback.rewind()
        self.play_start_time = self.clock() + CURTAIN_SECONDS * 0.6
        self.timeline.after(CURTAIN_SECONDS * 0.6, self._start_playback_audio)

    def _start_playback_audio(self) -> None:
        self._stop_playback_audio()
        wav = self.playback_wav
        if wav and len(wav) > 44:
            try:
                self.playback_audio_channel = pygame.mixer.Sound(io.BytesIO(wav)).play()
            except Exception:
                self.playback_audio_channel = None

    def _stop_playback_audio(self) -> None:
        if self.playback_audio_channel is not None:
            try:
                self.playback_audio_channel.stop()
            except Exception:
                pass
            self.playback_audio_channel = None

    def _playback_finished(self) -> None:
        meta = self.playback_show_meta
        self.playback = None
        self._stop_playback_audio()
        self.curtain.move(1.0)
        self.sound_mgr.play("applause")
        self._emit_saved_story_played()
        if meta is not None:
            self.timeline.after(CURTAIN_SECONDS + 0.05, lambda: self._curtain_call(meta, watched=True))

    def _emit_saved_story_played(self) -> None:
        meta = self.playback_show_meta
        if not isinstance(meta, dict):
            return
        show_id = meta.get("id")
        if not isinstance(show_id, str) or not show_id:
            return
        try:
            self._emit(
                "story.played",
                idempotency_key=f"play-{show_id}-{int(self.play_start_time * 1000)}",
                payload={"id": show_id},
            )
        except Exception:
            pass

    def _stop_watching(self) -> None:
        self.playback = None
        self._stop_playback_audio()
        self.timeline.clear()
        self._restore_after_watching()
        self.curtain.set(1.0)
        self.curtain.move(0.0)

    def _restore_after_watching(self) -> None:
        self.playback = None
        self.playback_show_meta = None
        self.playback_wav = None
        restore = self._watch_restore
        self._watch_restore = None
        self.mode = StageMode.EDIT
        if restore is not None:
            self.scene_id, png, surface, key, line_up = restore
            self._apply_backdrop(png, surface, key)
            self.stage.restore(line_up, KNOWN_PUPPETS)
        self._sync_all()

    # ------------------------------------------------------------------
    # pictures from / to My Creations
    # ------------------------------------------------------------------

    def _apply_backdrop(self, png: bytes | None, surface: pygame.Surface | None, key: str) -> None:
        self.custom_backdrop_png = png if surface is not None else None
        self.custom_backdrop_surface = surface
        self._custom_key = key if surface is not None else ""

    def _set_custom_backdrop(self, payload: bytes, surface: pygame.Surface) -> None:
        self._apply_backdrop(payload, surface, hashlib.sha256(payload).hexdigest())
        self._close_sheets()
        self._sync_all()
        self.sound_mgr.play("magic")
        self.fx.burst("sparkle", (REFERENCE_WIDTH // 2, 260))

    def _share_poster(self, show_item: dict) -> bool:
        """Publish this show's poster as a picture (Posta, Painting, Theatre...)."""

        if not self.bridge.available:
            return False
        try:
            picture = self.posters.for_show(show_item, (REFERENCE_WIDTH, REFERENCE_HEIGHT), cache=False, crop=False)
            payload = encode_surface_png(picture)
        except (PygamePngError, RuntimeError, ValueError, OSError):
            self._oops()
            return False
        if not self.bridge.publish_poster(payload, self.show_repo.write_private_file):
            self._oops()
            return False
        self.sound_mgr.play("magic")
        if self.cast is not None:
            self.cast.correct()
        if self._dialog is not None:
            self.fx.burst("sparkle", self._dialog.picture.center)
        return True

    # ------------------------------------------------------------------
    # sheets: library (delegated), scenes, curtain call
    # ------------------------------------------------------------------

    def _push_sheet(self, sheet: TheatreSheet) -> None:
        self._close_sheets()
        self.surfaces.push_overlay(sheet)
        self._dirty = True

    def _close_sheets(self) -> None:
        self.library.close()
        while self.surfaces.overlays:
            self.surfaces.pop_overlay()
        self._dialog = None
        self._dirty = True

    def _open_library(self) -> None:
        if self.mode != StageMode.EDIT:
            return
        if self.held is not None:
            self._drop_held()
        self._close_sheets()
        self.library.open()
        self.sound_mgr.play("pop")

    def _open_scene_sheet(self) -> None:
        if self.mode != StageMode.EDIT:
            return
        if self.held is not None:
            self._drop_held()
        grid = GridLayout.build(self.layout, columns=SCENE_COLUMNS, rows=SCENE_ROWS, aspect=POSTER_ASPECT * 1.04)
        size = picture_size(grid.cards[0])
        own = self.custom_backdrop_surface is not None
        thumbs: list[tuple[str, pygame.Surface | None, bool]] = [
            (scene_id, rounded(self.art.scene_thumbnail(scene_id, size)), scene_id == self.scene_id and not own)
            for scene_id in SCENE_IDS
        ]
        if self.bridge.available:
            icon = self.art.icon("ui.pictogram.creation", int(size[1] * 0.8), variant="image")
            thumbs.append(("mine", icon, own))
        layer = scene_sheet_layer(self.kit, grid, thumbs, on_choose=self._choose_scene, on_close=self._close_sheets)
        self._push_sheet(
            TheatreSheet(
                SCENES_ID,
                layer,
                grid.panel,
                on_dismiss=self._close_sheets,
                draw_backdrop=lambda target: self._draw_panel(target, grid.panel),
            )
        )
        self.sound_mgr.play("pop")

    def _choose_scene(self, scene_id: str) -> None:
        if scene_id == "mine":
            self.bridge.request_backdrop()
            return
        if scene_id not in SCENE_IDS:
            return
        self.scene_id = scene_id
        self._apply_backdrop(None, None, "")
        self._close_sheets()
        self._sync_all()
        self.sound_mgr.play("magic")
        self.fx.burst("sparkle", (REFERENCE_WIDTH // 2, 240))
        self._remember_stage()

    def _curtain_call(self, show_item: dict, *, watched: bool) -> None:
        """Poster + cheering host + watch (again) / share / done."""

        buttons: list[tuple[str, str, ButtonRole, Callable[[], object]]] = [
            ("call.watch", "replay" if watched else "play", ButtonRole.PRIMARY, lambda: self._watch_show(show_item)),
        ]
        if self.bridge.available:
            buttons.append(("call.share", "share", ButtonRole.NEUTRAL, lambda: self._share_poster(show_item)))
        buttons.append(("call.done", "check", ButtonRole.NEUTRAL, self._end_curtain_call))
        dialog = DialogLayout.build(self.layout, buttons=len(buttons))
        picture = self.posters.for_show(show_item, dialog.picture.size)
        layer = dialog_layer(self.kit, dialog, buttons, layer_id="teatrino.call.controls", focus="call.watch")
        self._push_sheet(
            TheatreSheet(
                CALL_ID,
                layer,
                dialog.panel,
                on_dismiss=self._end_curtain_call,
                draw_backdrop=lambda target: self._draw_dialog(target, dialog, picture),
                draw_front=lambda target: self._draw_host(target, dialog.host_midbottom),
            )
        )
        self._dialog = dialog
        self.host.say(VOICE_WATCHED if watched else VOICE_SAVED)
        if self.cast is not None:
            self.cast.correct()
        self.fx.burst("confetti", dialog.picture.midtop)

    def _end_curtain_call(self) -> None:
        self._close_sheets()
        if self.mode == StageMode.WATCHING:
            self._restore_after_watching()
        self.curtain.move(0.0)
        self.sound_mgr.play("curtain")

    # ------------------------------------------------------------------
    # hints
    # ------------------------------------------------------------------

    def _advance_hint(self, now: float) -> None:
        """Open the next back-off glow window, or close an expired one."""

        if self._hint_until and now >= self._hint_until:
            self._hint_until = 0.0
            self._dirty = True
        if self.mode != StageMode.EDIT or self.surfaces.overlays or self.curtain.value > 0.0:
            return
        if not self._hint_until and self._hints.is_due(now, self._last_activity):
            self._hints.fire(now)
            self._hint_until = now + self._hints.animation_seconds(HINT_GLOW_SECONDS)
            self._dirty = True

    def _hint_target(self, now: float) -> pygame.Rect | None:
        """After a quiet moment, glow the next useful thing (never an answer)."""

        if self.mode != StageMode.EDIT or self.surfaces.overlays or self.curtain.value > 0.0:
            return None
        if now >= self._hint_until:
            return None
        if not self.stage.puppets:
            cards = [card.rect for card in self.controls.cards if card.visible]
            return cards[0].unionall(cards[1:]) if cards else None
        return self.layout.rec

    # ------------------------------------------------------------------
    # syncing controls
    # ------------------------------------------------------------------

    def _sync_mode(self) -> None:
        self.controls.set_mode(self.mode)
        self._dirty = True

    def _sync_puppet_targets(self) -> None:
        rects = []
        for puppet in self.stage.puppets:
            look = self.art.look(puppet.puppet_id)
            if look is not None:
                puppet.half_width, puppet.half_height = look.half_width, look.half_height
            rects.append((puppet.puppet_id, pygame.Rect(puppet.rect_tuple())))
        self.controls.set_puppets(rects)

    def _sync_all(self) -> None:
        self.stage.bounds = self.layout.bounds
        icon_h = int(self.layout.control * 0.74)
        size = (int(icon_h * POSTER_ASPECT), icon_h)
        if self.custom_backdrop_surface is not None:
            scene_icon = pygame.transform.smoothscale(self.custom_backdrop_surface, size)
        else:
            scene_icon = self.art.scene_thumbnail(self.scene_id, size)
        self.controls.set_scene_icon(rounded(scene_icon))
        self._sync_mic()
        self._sync_puppet_targets()
        self.controls.sync_cards(self.stage.ids())
        self._sync_mode()

    # ------------------------------------------------------------------
    # drawing
    # ------------------------------------------------------------------

    def background(self) -> pygame.Surface:
        return self.art.stage_background(
            self.scene_id,
            self.custom_backdrop_surface,
            custom_key=self._custom_key,
            floor_dy=self.layout.floor_dy,
        )

    def render(self) -> None:
        surface = self.canvas.surface
        renderer = self.renderer
        now = self.clock()
        renderer.draw_stage(surface, self.background(), self.stage, curtain=self.curtain.value)
        if self.mode == StageMode.COUNTDOWN and self.curtain.value >= 0.99:
            renderer.draw_countdown(surface, self._countdown_lamps, (now - self._countdown_beat_at) / COUNTDOWN_BEAT)
        hint = self._hint_target(now)
        if hint is not None:
            renderer.draw_hint(surface, hint)
        self.surfaces.screen.draw(surface)
        if self.mode == StageMode.RECORDING:
            elapsed = now - self.rec_started
            renderer.draw_rec_ring(surface, self.layout.rec, elapsed / max(0.1, self.voice.limit), self.voice.level(elapsed))
        elif self.mode == StageMode.WATCHING and self.playback is not None:
            t = max(0.0, now - self.play_start_time)
            renderer.draw_rec_ring(surface, self.layout.rec, t / max(0.1, self.playback.duration), 0.0)
        for overlay in self.surfaces.overlays:
            overlay.draw(surface)
        self.fx.draw(surface)
        if not self.surfaces.overlays and self.save_error and self.cast is not None and self.cast.animating:
            self.cast.draw(surface, (self.layout.bounds.right + 30, self.layout.tray.top + 8))

    def _draw_shelf_host(self, target: pygame.Surface, midbottom: tuple[int, int]) -> None:
        if self.shelf_cast is not None:
            self.shelf_cast.draw(target, midbottom)

    def _draw_host(self, target: pygame.Surface, midbottom: tuple[int, int]) -> None:
        if self.cast is not None:
            self.cast.draw(target, midbottom)

    def _draw_panel(self, target: pygame.Surface, panel: pygame.Rect) -> None:
        self.renderer.draw_dim(target)
        self.renderer.draw_panel(target, panel)

    def _draw_dialog(self, target: pygame.Surface, dialog: DialogLayout, picture: pygame.Surface | None) -> None:
        self._draw_panel(target, dialog.panel)
        if dialog.picture.width > 0:
            self.renderer.draw_picture(target, picture, dialog.picture)


__all__ = ["Curtain", "TeatrinoApp", "Timeline"]
