"""Lifecycle, timing and input for Colline Allegre (Bumpy Hills).

Tito drives his little buggy over five finite courses, each ending at a
picnic where a friend waits (Leo, Lilli, Momo, Dani, Flash):

* hold GO (right arrow / Space / D-pad right / south button / the green
  pedal) to drive and BRAKE (left arrow / D-pad left / east button / the
  coral pedal) to slow down; in the air, right and left lean the buggy;
* stars float over the course (three per course) and fill the star slots;
  flags along the way are checkpoints;
* a tumble is never "game over": the buggy lands on its roof, Tito thinks,
  and after a moment it is back upright on the last flag. On the snowy and
  sky courses a snail sign marks a steep drop: too fast over the edge and
  the buggy goes head over heels. After such a tumble the sign glows and the
  BRAKE pedal pulses when the buggy comes back (demonstration); after two
  tumbles on one course the buggy slows itself at the signs (assist);
* the pedals sit side by side at the bottom-right with a keyboard hint
  (arrows + Space keycaps) beside them: shown at the start of a set, lit
  while a real key is held, and its keys light one after another with each
  idle hint (ADR 0037 §4a/§4b);
* idle ~6 s: Tito points ahead and the GO pedal pulses;
* at the finish arch the friend cheers, the course's stars pop in over the
  picnic, and the next course starts. After five courses the shared cast
  completion scene appears ("drive again"); the rung (hill size) adapts.

Physics runs in fixed 1/120 s steps (``FIXED_DT``) whatever the frame rate.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from enum import StrEnum
import math
import random
import time

import pygame

from greia_platform.activity_api import activity_stop_requested, mark_activity_ready
from greia_platform.frame_governor import FrameGovernor, FrameKind
from greia_platform.activity_controls import (
    ControlArt,
    ControlKit,
    ControlLayout,
    ControlTheme,
    KitPointer,
    PointerPhase,
    PygameControlInput,
)
from greia_platform.activity_feedback import CastFeedback, IdleHintScheduler
from greia_platform.input_core import SemanticAction
from greia_platform.localization import LocalizedResources
from greia_platform.pygame_canvas import PygameReferenceCanvas, activity_viewport_for_surface
from greia_platform.pygame_completion import (
    CompletionContent,
    CompletionOverlay,
    CompletionPalette,
    CompletionScene,
    PygameCompletionScreen,
)
from greia_platform.typography import GreiaTypography
from greia_platform.ui_core import SurfaceNavigator, UiEventResult

if __package__:
    from .colline_art import CollineArt
    from .colline_audio import CollineAudio
    from .colline_content import (
        COURSES_PER_SET,
        FIXED_DT,
        MAX_STEPS_PER_FRAME,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
    )
    from .colline_controls import CollineControls
    from .colline_input import DriveInput
    from .colline_layout import FRIEND_OFFSET, pedal_at
    from .colline_model import Controls, CourseRun, CourseSet, RunEvent, adapt_rung, bounded_history
    from .colline_renderer import CELEBRATE_SECONDS, FLAG_BEHIND, Camera, CollineRenderer, DriverCast, SceneMotion, SceneView
    from .colline_services import CollineProgress, EventPort, ProgressPort
else:
    from colline_art import CollineArt
    from colline_audio import CollineAudio
    from colline_content import (
        COURSES_PER_SET,
        FIXED_DT,
        MAX_STEPS_PER_FRAME,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
    )
    from colline_controls import CollineControls
    from colline_input import DriveInput
    from colline_layout import FRIEND_OFFSET, pedal_at
    from colline_model import Controls, CourseRun, CourseSet, RunEvent, adapt_rung, bounded_history
    from colline_renderer import CELEBRATE_SECONDS, FLAG_BEHIND, Camera, CollineRenderer, DriverCast, SceneMotion, SceneView
    from colline_services import CollineProgress, EventPort, ProgressPort

TUMBLE_SECONDS = 1.4
NEXT_COURSE_SECONDS = CELEBRATE_SECONDS + 0.6
SIGN_HINT_SECONDS = 7.0
SPEECH_GAP_SECONDS = 4.0
KEY_HINT_START_SECONDS = 8.0  # keyboard hint shown at the start of a set (ADR 0037 §4b)
MAX_FRAME_SECONDS = 0.1
# The child let go of the pedals this long ago: the buggy is parked (rolls to
# a stop). Once it has stood still for REST_HOLD_SECONDS the drive is no
# longer essential motion and the frame governor can freeze the scene.
PARK_AFTER_SECONDS = 3.0
REST_SPEED = 1.5  # px/s
REST_SPIN = 0.02  # rad/s
REST_HOLD_SECONDS = 0.5
MAX_SCHEDULED = 32
MEADOW_DUSK = (58, 92, 128)  # deep ocean ("play" Collection hue, darkened)


class AppState(StrEnum):
    READY = "ready"  # buggy at the start flag, waiting for GO
    DRIVING = "driving"
    TUMBLE = "tumble"
    FINISH = "finish"  # celebrating at the picnic
    TERMINAL = "terminal"  # shared completion scene


class Timeline:
    """Tiny bounded scheduler for the scripted moments."""

    def __init__(self, clock: Callable[[], float]) -> None:
        self._clock = clock
        self._entries: deque[tuple[float, Callable[[], object]]] = deque(maxlen=MAX_SCHEDULED)

    def after(self, delay: float, action: Callable[[], object]) -> None:
        self._entries.append((self._clock() + delay, action))

    def run_due(self) -> bool:
        now = self._clock()
        due = [entry for entry in self._entries if entry[0] <= now]
        if not due:
            return False
        for entry in due:
            self._entries.remove(entry)
        for _, action in sorted(due, key=lambda entry: entry[0]):
            action()
        return True

    def clear(self) -> None:
        self._entries.clear()


class CollineActivity:
    """Coordinate the course set, physics clock, input, art, audio and lifecycle."""

    def __init__(
        self,
        *,
        screen: pygame.Surface,
        canvas: PygameReferenceCanvas,
        typography: GreiaTypography,
        resources: LocalizedResources | None,
        audio: CollineAudio,
        progress: ProgressPort,
        events: EventPort,
        rng: random.Random | None = None,
        clock: Callable[[], float] = time.monotonic,
        kit: ControlKit | None = None,
        art: CollineArt | None = None,
        session_prefix: str | None = None,
    ) -> None:
        self.screen = screen
        self.canvas = canvas
        self.typography = typography
        self.resources = resources
        self.audio = audio
        self.progress = progress
        self.events = events
        self.rng = rng if rng is not None else random.Random()
        self.clock = clock
        self._session_prefix = session_prefix or f"{int(time.time())}"
        self._sets_played = 0

        saved = progress.load()
        self.saved = saved
        self.rung = saved.rung
        self._history = saved.history

        # Shared control kit (ADR 0037): play Collection -> ocean accent.
        self.kit = kit if kit is not None else ControlKit(typography, ControlTheme.for_accent("ocean"))
        self.art = art if art is not None else CollineArt(loader=ControlArt(max_entries=64))
        feedback = CastFeedback("tito", height=96, art=self.art.loader, idle_variant="happy", hold_seconds=1.5, clock=clock)
        self.driver = DriverCast(feedback, clock)
        self.renderer = CollineRenderer(self.art, self.driver)
        self.camera = Camera()
        self.motion = SceneMotion()
        self.timeline = Timeline(clock)
        self.drive = DriveInput()
        self.controls = CollineControls(self.kit, self.art, typography, on_listen=self._listen, clock=clock)
        self._keys_changed = False
        self._surfaces = SurfaceNavigator(self.controls.layer)
        self._input = PygameControlInput(to_logical=canvas.pointer, is_safe=lambda pos: _safe_point(self.screen, pos))
        self.controls.place(ControlLayout.for_canvas(canvas, screen.get_size()))

        self.course_set: CourseSet | None = None
        self.ride: CourseRun | None = None
        self.completion: PygameCompletionScreen | None = None
        self.state = AppState.READY
        self.session_id = ""
        self._running = True
        self.ready_published = False
        self._welcomed = False
        self._last_tick = clock()
        self._accumulator = 0.0
        self._last_input = clock()
        self._still_since: float | None = None
        self._hint_schedule = IdleHintScheduler(now=self._last_input)
        self._last_speech = -SPEECH_GAP_SECONDS
        self._hinted_drop: int | None = None
        self.start_set()

    # -- main loop --------------------------------------------------------------------

    def run(self) -> int:
        # The ride animates; waiting at the start flag is ambient.
        frames = FrameGovernor(redraw_on_input=True)
        try:
            while self._running and not activity_stop_requested():
                for event in frames.events():
                    self.handle_event(event)
                repeat = self._input.poll()
                if repeat is not None and self.state is AppState.TERMINAL:
                    self._surfaces.dispatch(repeat)
                self.step()
                riding = self.riding
                key_deadline = self.controls.keys.deadline()
                if key_deadline is not None:
                    frames.wake_at(key_deadline)
                frame = frames.frame(dirty=self._keys_changed, animating=riding, ambient=True)
                self._keys_changed = False
                if frame is FrameKind.FULL:
                    self.render()
                    self.canvas.present()
                    pygame.display.flip()
                    if not self.ready_published:
                        mark_activity_ready()
                        self.ready_published = True
                        self._welcome()
                elif frame is FrameKind.POINTER:
                    self.canvas.present_pointer()
                frames.wait(polling=self._input.repeating)
        finally:
            self.persist()
            self.audio.stop_all()
            self.typography.clear()
        return 0

    def step(self) -> None:
        """Advance timers, hints and the fixed-step physics to the clock."""

        now = self.clock()
        dt = max(0.0, min(MAX_FRAME_SECONDS, now - self._last_tick))
        self._last_tick = now
        self.timeline.run_due()
        if self.controls.keys.update():
            self._keys_changed = True
        self.driver.update()
        self.motion.prune(now)
        ride = self.ride
        if ride is None or self.state is AppState.TERMINAL:
            return
        self._accumulator += dt
        steps = 0
        parked = self.state is AppState.DRIVING and self._parked(now)
        while self._accumulator >= FIXED_DT and steps < MAX_STEPS_PER_FRAME:
            if self.state is not AppState.DRIVING:
                controls = _NO_INPUT
            else:
                controls = _PARKED if parked else self.drive.controls()
            for event in ride.step(controls):
                self._on_run_event(event, now)
            self._accumulator -= FIXED_DT
            steps += 1
            if self.ride is not ride:
                break
        if steps >= MAX_STEPS_PER_FRAME:
            self._accumulator = 0.0
        if self.ride is ride:
            self.camera.follow(ride, dt)
            self.controls.road.progress = ride.progress
        self._track_rest(now)
        self._hints(now)

    # -- rest (calm idle) -------------------------------------------------------------

    @property
    def riding(self) -> bool:
        """Essential motion for the frame governor.

        The buggy moving, tumbling or celebrating. A parked buggy that has
        stood still (no pedal, no feedback playing) is a still picture: the
        loop stops presenting and, 30 s later, releases the audio device.
        """

        if self.state in (AppState.TUMBLE, AppState.FINISH):
            return True
        return self.state is AppState.DRIVING and not self.at_rest

    @property
    def at_rest(self) -> bool:
        """True while a parked buggy has stood still for ``REST_HOLD_SECONDS``."""

        now = self.clock()
        return (
            self._still_since is not None
            and now - self._still_since >= REST_HOLD_SECONDS
            and self._parked(now)
            and not self.motion.active(now)
            and not self.driver.animating
        )

    def _parked(self, now: float) -> bool:
        return not (self.drive.go or self.drive.brake) and now - self._last_input >= PARK_AFTER_SECONDS

    def _track_rest(self, now: float) -> None:
        run = self.ride
        still = (
            run is not None
            and self.state is AppState.DRIVING
            and self._parked(now)
            and not run.vehicle.airborne
            and run.vehicle.speed < REST_SPEED
            and abs(run.vehicle.angular_velocity) < REST_SPIN
            and self.camera.settled(run)
        )
        if not still:
            self._still_since = None
        elif self._still_since is None:
            self._still_since = now

    def render(self) -> None:
        surface = self.canvas.surface
        run = self.ride
        if self.state is not AppState.TERMINAL and run is not None and self.course_set is not None:
            now = self.clock()
            view = SceneView(run, run.layout.spec.friend, self.camera.x, self.camera.y)
            self.renderer.draw(surface, view, self.motion, now)
            self.controls.draw_hud(
                surface,
                self._surfaces.draw,
                go=self.drive.go and self.state is AppState.DRIVING,
                brake=self.drive.brake and self.state is AppState.DRIVING,
                go_hint=self._go_hint(now),
                brake_hint=self._brake_hint(now),
            )
            return
        self._surfaces.draw(surface)

    def persist(self) -> None:
        self.progress.save(
            CollineProgress(
                self.rung,
                self._history,
                self.saved.sets,
                self.saved.courses,
                self.saved.total_stars,
                self.saved.best_distance,
            )
        )

    # -- input --------------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self._running = False
            return
        if event.type == pygame.VIDEORESIZE:
            self._resize()
            return
        if event.type == pygame.WINDOWFOCUSLOST:
            self.drive.release_all()
            return
        if self.state is not AppState.TERMINAL and self.controls.keys.observe_event(event):
            self._keys_changed = True
        if self.state is AppState.TERMINAL:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self._running = False
                return
            translated = self._input.translate(event)
            if translated is not None:
                self._surfaces.dispatch(translated)
            return
        if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            translated = self._input.translate(event)
            if translated is not None:
                self._pointer(translated)
            return
        action = self.drive.handle(event)
        if action is None:
            return
        self._note_input()
        if action == "listen":
            self._listen()
        elif action is SemanticAction.CANCEL:
            self._running = False
        elif self.drive.go and self.state is AppState.READY:
            self._start_driving()

    def _pointer(self, sample: KitPointer) -> None:
        if sample.phase is PointerPhase.CANCEL:
            self.drive.touch_go = self.drive.touch_brake = False
            self.controls.layer.handle_event(sample)
            return
        if sample.phase is PointerPhase.UP:
            self.drive.touch_go = self.drive.touch_brake = False
            self._surfaces.dispatch(sample)
            return
        result = self._surfaces.dispatch(sample)
        if sample.phase is not PointerPhase.DOWN or result is not UiEventResult.IGNORED:
            return
        self._note_input()
        pedal = pedal_at(sample.position, self.controls.go.rect, self.controls.brake.rect)
        if pedal == "go":
            self.drive.touch_go = True
            if self.state is AppState.READY:
                self._start_driving()
        elif pedal == "brake":
            self.drive.touch_brake = True

    def _resize(self) -> None:
        self.screen = pygame.display.get_surface() or self.screen
        self.canvas = PygameReferenceCanvas(self.screen, hires=True)
        self._input = PygameControlInput(to_logical=self.canvas.pointer, is_safe=lambda pos: _safe_point(self.screen, pos))
        self.controls.place(ControlLayout.for_canvas(self.canvas, self.screen.get_size()))

    def _note_input(self) -> None:
        self._last_input = self.clock()
        self._hint_schedule.reset(self._last_input)

    # -- set / course flow ----------------------------------------------------------------

    def start_set(self) -> None:
        self.timeline.clear()
        self.course_set = CourseSet(self.rung)
        self._sets_played += 1
        self.session_id = f"{self._session_prefix}-{self._sets_played}-{self.rng.randrange(1_000_000):06d}"
        self.controls.set_playing(True)
        self.controls.keys.show(KEY_HINT_START_SECONDS)
        self._keys_changed = True
        self._begin_course()

    def _begin_course(self) -> None:
        course_set = self.course_set
        assert course_set is not None
        self.ride = course_set.build_run()
        self.art.begin_course(self.ride.layout)
        self.camera.snap(self.ride)
        self.motion.reset()
        self.driver.reset()
        self.drive.release_all()
        self._accumulator = 0.0
        self._hinted_drop = None
        self.controls.set_course(course_set.index, course_set.current.friend)
        self.state = AppState.READY
        self._note_input()
        if self._welcomed:
            self._say("ready.go")

    def _start_driving(self) -> None:
        if self.state is AppState.READY:
            self.state = AppState.DRIVING
            self._note_input()

    def _welcome(self) -> None:
        if not self._welcomed:
            self._welcomed = True
            self._say("ready.go", force=True)

    def _on_run_event(self, event: RunEvent, now: float) -> None:
        run = self.ride
        assert run is not None
        veh = run.vehicle
        if event is RunEvent.STAR:
            self.audio.play("star")
            star = min((s for s in run.stars if s.collected), key=lambda s: abs(s.x - veh.x))
            self.motion.add_fx("star_burst", (star.x, star.y), now)
            self.controls.set_stars(run.stars_collected)
            self.driver.correct()
        elif event is RunEvent.CHECKPOINT:
            flag = run.checkpoint_x
            self.audio.play("flag")
            self.motion.flag_pops[flag] = now
            pole = flag - FLAG_BEHIND
            self.motion.add_fx("sparkle", (pole + 24, run.layout.height(pole) - 92), now)
        elif event is RunEvent.PERFECT_LANDING:
            self.audio.play("sparkle")
            self.motion.add_fx("sparkle", (veh.x, veh.y - 40), now)
            self.driver.correct()
        elif event is RunEvent.LANDING:
            self.audio.play("thump")
            self.motion.add_fx("dust_puff", (veh.x, run.layout.height(veh.x) - 18), now)
        elif event is RunEvent.BOUNCE:
            self.audio.play("whoosh")
            pads = run.layout.pads
            if pads:
                pad = min(pads, key=lambda x: abs(x - veh.x))
                self.motion.squashes[pad] = now
        elif event is RunEvent.DROP_SAFE:
            self.driver.correct()
            self.audio.play("sparkle")
            if self._hinted_drop is not None:
                self._say("praise.general", force=True)
                self._hinted_drop = None
                self.motion.sign_hint = None
        elif event is RunEvent.DROP_TOO_FAST:
            self.audio.play("whoosh")
        elif event is RunEvent.TUMBLE:
            self._tumble(now)
        elif event is RunEvent.FINISH:
            self._finish_course(now)

    def _tumble(self, now: float) -> None:
        run = self.ride
        assert run is not None
        self.state = AppState.TUMBLE
        self.audio.play("boing")
        self.motion.add_fx("dust_puff", (run.vehicle.x, run.vehicle.y), now)
        self.driver.try_again()
        self._say("encourage.retry")
        self.timeline.after(TUMBLE_SECONDS, self._respawn)

    def _respawn(self) -> None:
        run = self.ride
        if run is None or self.state is not AppState.TUMBLE:
            return
        now = self.clock()
        run.respawn()
        self.camera.snap(run)
        self.motion.add_fx("dust_puff", (run.vehicle.x, run.vehicle.y + 10), now)
        self.drive.release_all()
        self.state = AppState.DRIVING
        self._note_input()
        # Demonstrate after an error at a drop: the sign glows and BRAKE pulses.
        upcoming = run.upcoming_drop(lookahead=1600.0)
        if upcoming is not None and upcoming in run.drop_hints and not run.drop_assist:
            self._hinted_drop = upcoming
            self.motion.sign_hint = (upcoming, now + SIGN_HINT_SECONDS)
            self.driver.point(1.6)
            self._say("slow_down", force=True)  # "Slow down!" with the glowing sign

    def _finish_course(self, now: float) -> None:
        run = self.ride
        course_set = self.course_set
        assert run is not None and course_set is not None
        self.state = AppState.FINISH
        self.drive.release_all()
        self.motion.celebrate = now
        self.motion.result_stars = run.stars_collected
        layout = run.layout
        friend_x = layout.finish_x + FRIEND_OFFSET
        self.motion.add_fx("confetti", (friend_x - 120, layout.height(friend_x) - 160), now + 0.1)
        self.motion.add_fx("star_burst", (layout.finish_x, layout.height(layout.finish_x) - 200), now)
        self.audio.play("fanfare")
        self.driver.correct()
        index = course_set.index
        result = course_set.record(run)
        self.controls.progress.set_progress(course_set.index)
        self.saved = CollineProgress(
            self.rung,
            self._history,
            self.saved.sets,
            self.saved.courses + 1,
            self.saved.total_stars + result.stars,
            self.saved.best_distance,
        )
        self.persist()
        self.events.course_finished(
            self.session_id,
            {"course": index + 1, "stars": result.stars, "tumbles": result.tumbles, "rung": self.rung},
        )
        if course_set.complete:
            self._say("celebrate.success", force=True)
            self.timeline.after(NEXT_COURSE_SECONDS, self._finish_set)
        else:
            self._say("made_it_picnic", force=True)  # "You made it to the picnic!"
            self.timeline.after(NEXT_COURSE_SECONDS, self._next_course)

    def _next_course(self) -> None:
        if self.state is AppState.FINISH and self.course_set is not None and not self.course_set.complete:
            self._begin_course()

    def _finish_set(self) -> None:
        course_set = self.course_set
        if course_set is None or self.state is not AppState.FINISH:
            return
        tumbles = course_set.total_tumbles
        self._history = bounded_history(self._history, tumbles)
        played_rung = self.rung
        self.rung = adapt_rung(self.rung, tumbles)
        self.saved = CollineProgress(
            self.rung, self._history, self.saved.sets + 1, self.saved.courses, self.saved.total_stars, self.saved.best_distance
        )
        self.persist()
        self.events.set_completed(
            self.session_id,
            {"courses": course_set.total, "stars": course_set.total_stars, "tumbles": tumbles, "rung": played_rung},
        )
        self.completion = PygameCompletionScreen(
            self.typography,
            width=REFERENCE_WIDTH,
            height=REFERENCE_HEIGHT,
            palette=CompletionPalette(background=MEADOW_DUSK),
            scene=CompletionScene(self.kit, character="tito", star_total=COURSES_PER_SET),
        )
        self.completion.prepare(
            CompletionContent(
                title=self._text("victory.title", "★"),
                primary_label=self._text("button.play_again", "↻"),
                body_lines=(self._text("victory.subtitle", ""),),
                achievement_count=course_set.total,
            )
        )
        self.controls.set_playing(False)
        self.controls.keys.hide()
        self._surfaces.push_overlay(CompletionOverlay(self.completion, on_primary=self._restart))
        self.timeline.clear()
        self.drive.release_all()
        self.state = AppState.TERMINAL

    def _restart(self) -> None:
        if self.completion is not None:
            self._surfaces.pop_overlay()
            self.completion.clear()
            self.completion = None
        self.start_set()

    def _listen(self) -> None:
        """Say the goal again (listen button / Enter / north button): Tito points ahead."""

        if self.state is AppState.TERMINAL:
            return
        self._say("ready.go", force=True)
        self.driver.point(1.6)

    # -- hints ----------------------------------------------------------------------------

    def _hints(self, now: float) -> None:
        run = self.ride
        if run is None or self.state not in (AppState.READY, AppState.DRIVING):
            return
        if self.drive.go or self.drive.brake:
            self._last_input = now
            return
        step = self._hint_schedule.poll(now, self._last_input)
        if step:
            self.driver.point(self._hint_schedule.animation_seconds(1.8))
            self.controls.keys.demonstrate()
            self._keys_changed = True
            if step == 1 or self.state is AppState.READY:
                self._say("ready.go")

    def _go_hint(self, now: float) -> float:
        if self.state is AppState.READY:
            strength = 0.6 if self._hint_schedule.count else 0.35
            return strength + strength * 0.8 * abs(_wave(now, 2.0))
        if self.state is AppState.DRIVING and self._hint_schedule.count and not self.drive.go:
            return 0.5 + 0.5 * abs(_wave(now, 2.5))
        return 0.0

    def _brake_hint(self, now: float) -> float:
        run = self.ride
        if run is None or self._hinted_drop is None or self.state is not AppState.DRIVING:
            return 0.0
        if run.upcoming_drop() != self._hinted_drop or self.drive.brake:
            return 0.0
        return 0.5 + 0.5 * abs(_wave(now, 3.0))

    # -- helpers ----------------------------------------------------------------------------

    def _say(self, cue: str, *, force: bool = False) -> None:
        now = self.clock()
        if not force and now - self._last_speech < SPEECH_GAP_SECONDS:
            return
        self._last_speech = now
        self.audio.say(cue)

    def _text(self, key: str, default: str) -> str:
        if self.resources is None:
            return default
        try:
            return self.resources.text(key) or default
        except Exception:
            return default

    # -- test / tooling helpers -------------------------------------------------------------

    def hold(self, *, go: bool = False, brake: bool = False) -> None:
        """Hold the pedals as a touch would (used by tests and scripted reviews)."""

        self.drive.touch_go = go
        self.drive.touch_brake = brake
        if go:
            self._note_input()
            self._start_driving()


_NO_INPUT = Controls()
_PARKED = Controls(park=True)


def _wave(now: float, hz: float) -> float:
    return math.sin(now * hz * math.pi)


def _safe_point(surface: pygame.Surface, position: tuple[int, int]) -> bool:
    """True inside the play surface and outside the Greia protected region(s)."""

    viewport = activity_viewport_for_surface(surface)
    x, y = position
    if not (0 <= x < viewport.surface.width and 0 <= y < viewport.surface.height):
        return False
    for protected in viewport.protected_regions:
        if protected.x <= x < protected.right and protected.y <= y < protected.bottom:
            return False
    return True


__all__ = ["AppState", "CollineActivity", "Timeline"]
