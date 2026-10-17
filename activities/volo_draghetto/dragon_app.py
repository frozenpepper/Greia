"""Lifecycle, input and feedback for Il Volo del Draghetto.

The child first sees the sky map: the little dragon on its island, one big
picture card per course (locked ones faded, earned stars underneath) and a
row of looks to wear. Tapping a course starts a finite 1-minute flight:

* arrows / D-pad / left stick steer up and down (left/right: slower/faster),
  Space / south button flap; pointer and touch: tap to flap, hold and drag to
  steer. Hover alone never moves the dragon, and the Home/Back corner is
  never gameplay;
* stars and gems are collected by flying into them; clouds only bounce;
* each rainbow ring is a checkpoint (progress dots). Through it: Flash cheers
  (``pose_cheer`` + an approved praise line) and the ring bursts; past it:
  Flash thinks (``pose_think`` + an approved retry line) and the ring hops
  ahead, nearer and wider, with a star trail and guide dots showing the way;
* hints are graduated: at the start and after ~6 s without input the matching
  control glyph pulses by the dragon and the next ring sparkles; after ~12 s
  Flash points and guide dots lead to the ring;
* a child who stops playing is not chased by an endless flight: after
  ``REST_AFTER_SECONDS`` without input (nothing held) the dragon slows to a
  hover over ``REST_EASE_SECONDS`` and the scene comes to rest with the keycap
  hint showing, so the frame governor can freeze it (and release the audio
  device); any key, tap, drag or stick move flies on at once;
* the keycap hint lights only keys that are really held: idle hints reveal
  it without "demonstrating" keys nobody pressed;
* the finish rainbow ends the course on the shared cast completion scene
  (1-3 stars). Finishing unlocks the next course and a new look.
"""

from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum
import random
import time

import pygame

from greia_platform.activity_api import activity_stop_requested, mark_activity_ready
from greia_platform.frame_governor import FrameGovernor, FrameKind
from greia_platform.activity_controls import (
    ControlKit,
    ControlLayout,
    ControlTheme,
    KitPointer,
    PointerPhase,
    PygameControlInput,
)
from greia_platform.activity_feedback import CastFeedback, IdleHintScheduler
from greia_platform.input_core import (
    DEFAULT_INPUT_POLICY,
    ControllerAxis,
    InputEdge,
    InputSource,
    InteractionProfile,
    SemanticAction,
    normalize_stick,
)
from greia_platform.localization import LocalizedResources
from greia_platform.pygame_canvas import PygameReferenceCanvas, activity_viewport_for_surface
from greia_platform.pygame_completion import (
    CompletionContent,
    CompletionOverlay,
    CompletionPalette,
    CompletionScene,
    PygameCompletionScreen,
)
from greia_platform.pygame_input import PygameInputTranslator
from greia_platform.typography import GreiaTypography
from greia_platform.ui_core import SurfaceNavigator

try:
    from dragon_art import NAVY, DragonArt
    from dragon_audio import DragonAudio
    from dragon_controls import MAP_PREVIEW_CENTER, FlightHud, MapControls
    from dragon_courses import COURSES
    from dragon_model import (
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        CourseBuilder,
        FlightEvent,
        FlightEventKind,
        FlightInput,
        FlightPhase,
        FlightRun,
    )
    from dragon_renderer import CAST_HEIGHT, FlashCast, FlightMotion, FlightRenderer, MapRenderer
    from dragon_services import EventPort, FlightProgress, ProgressPort
except ImportError:  # pragma: no cover - package import path
    from .dragon_art import NAVY, DragonArt
    from .dragon_audio import DragonAudio
    from .dragon_controls import MAP_PREVIEW_CENTER, FlightHud, MapControls
    from .dragon_courses import COURSES
    from .dragon_model import (
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        CourseBuilder,
        FlightEvent,
        FlightEventKind,
        FlightInput,
        FlightPhase,
        FlightRun,
    )
    from .dragon_renderer import CAST_HEIGHT, FlashCast, FlightMotion, FlightRenderer, MapRenderer
    from .dragon_services import EventPort, FlightProgress, ProgressPort

START_HINT_SECONDS = 4.5
GUIDE_SECONDS = 3.0
KEY_HINT_START_SECONDS = 8.0  # keyboard hint shown at the start of a flight (ADR 0037 §4b)
DRAG_SLOP = 14
# No child input for this long -> the dragon rests. Long enough for both idle
# hints (6 s and 18 s: keys + ring sparkle, then Flash points the way).
REST_AFTER_SECONDS = 20.0
REST_EASE_SECONDS = 1.6  # glide from full speed to a hover
COMPLETE_STARS = 3
MAP_DRAGON_HEIGHT = 210

_VERTICAL = {SemanticAction.MOVE_UP: -1, SemanticAction.MOVE_DOWN: 1}
_HORIZONTAL = {SemanticAction.MOVE_LEFT: -1, SemanticAction.MOVE_RIGHT: 1}


class AppState(StrEnum):
    MAP = "map"
    FLIGHT = "flight"
    COMPLETE = "complete"


class DragonFlightActivity:
    """Coordinate map, flight model, kit controls, art, audio and lifecycle."""

    def __init__(
        self,
        *,
        screen: pygame.Surface,
        canvas: PygameReferenceCanvas,
        typography: GreiaTypography,
        resources: LocalizedResources,
        progress: ProgressPort,
        events: EventPort,
        audio: DragonAudio,
        rng: random.Random,
        session_id: str,
        clock: Callable[[], float] = time.monotonic,
        kit: ControlKit | None = None,
        art: DragonArt | None = None,
    ) -> None:
        self.screen = screen
        self.canvas = canvas
        self.typography = typography
        self.resources = resources
        self.progress_port = progress
        self.events = events
        self.audio = audio
        self.rng = rng
        self.session_id = session_id
        self._rings_told = False
        self.clock = clock
        # Play Collection -> ocean accent (ADR 0037 / SVG rules tile hue).
        self.kit = kit if kit is not None else ControlKit(typography, ControlTheme.for_accent("ocean"))
        self.art = art if art is not None else DragonArt(self.kit.art)
        self.progress: FlightProgress = progress.load()
        self.builder = CourseBuilder(rng)
        feedback = CastFeedback("flash", height=CAST_HEIGHT, art=self.kit.art, clock=clock)
        point = self.kit.art.image("character.flash", CAST_HEIGHT, variant="pose_point")
        self.cast = FlashCast(feedback, point, clock)
        self.motion = FlightMotion()
        self.flight_renderer = FlightRenderer(self.art, self.cast, self.kit.glyph)
        self.map_renderer = MapRenderer(self.art, COURSES[0])
        self.map = MapControls(
            self.kit, self.art, self._layout(), on_course=self._on_course, on_look=self._on_look
        )
        self.completion = PygameCompletionScreen(
            typography,
            width=REFERENCE_WIDTH,
            height=REFERENCE_HEIGHT,
            palette=CompletionPalette(background=NAVY),
            scene=CompletionScene(self.kit, character="flash", star_total=COMPLETE_STARS, secondary_glyph="go"),
        )
        self._surfaces = SurfaceNavigator(self.map.layer)
        self._input = self._make_input()
        self._game_input = PygameInputTranslator(InteractionProfile.DIRECTIONAL)
        self.state = AppState.MAP
        self.course_index = 0
        self.run: FlightRun | None = None
        self.hud: FlightHud | None = None
        self._running = True
        self._ready_published = False
        self._activated = False
        self._keys_v: dict[SemanticAction, bool] = {}
        self._keys_h: dict[SemanticAction, bool] = {}
        self._stick = (0.0, 0.0)
        self._pointer_down = False
        self._press_y = 0.0
        self._drag_y: float | None = None
        self._last_input = clock()
        self._hints = IdleHintScheduler(now=self._last_input)
        self._last_source = InputSource.KEYBOARD
        self._flight_started = clock()
        self._last_step = clock()
        # Flight pace: 1 while flying, easing to 0 while the dragon settles.
        self._pace = 1.0
        self._frames: FrameGovernor | None = None
        self.map.sync(self.progress, refocus=self.progress.first_open_course())

    # -- main loop ------------------------------------------------------------

    def run_loop(self) -> int:
        # Flight animates (until the dragon rests); the map's flapping dragon is ambient.
        frames = FrameGovernor(redraw_on_input=True)
        self._frames = frames
        try:
            while self._running and not activity_stop_requested():
                for event in frames.events():
                    self.handle_event(event)
                if self.state is not AppState.FLIGHT:
                    repeat = self._input.poll()
                    if repeat is not None:
                        self._surfaces.dispatch(repeat)
                now = self.clock()
                self.step(min(0.05, max(0.0, now - self._last_step)))
                self._last_step = now
                frame = frames.frame(animating=self.flight_moving, ambient=self.state is not AppState.FLIGHT)
                if frame is FrameKind.FULL:
                    self.render()
                    self.canvas.present()
                    pygame.display.flip()
                    if not self._ready_published:
                        mark_activity_ready()
                        self._ready_published = True
                elif frame is FrameKind.POINTER:
                    self.canvas.present_pointer()
                frames.wait(polling=self._input.repeating)
        finally:
            self.progress_port.save(self.progress)
            self.typography.clear()
        return 0

    def step(self, dt: float) -> None:
        now = self.clock()
        self.cast.update()
        self.motion.prune(now)
        if self.state is not AppState.FLIGHT or self.run is None:
            return
        if self.hud is not None and self.hud.keys.update() and self._frames is not None:
            self._frames.invalidate()
        if self._steering_held():
            self._last_input = now  # holding a key/stick/drag is play, not idleness
            self._hints.reset(now)
        was_resting = self.resting
        self._pace = self._next_pace(now, dt)
        if self.resting:
            if not was_resting:
                self._settle()
            return
        for event in self.run.update(dt * self._pace, self._steer()):
            self._on_flight_event(event, now)
            if self.state is not AppState.FLIGHT:
                return
        if self.hud is not None:
            self.hud.sync(self.run)
        if self._pace >= 1.0:
            self._maybe_hint(now)

    # -- resting (calm idle) --------------------------------------------------

    @property
    def resting(self) -> bool:
        """True while a flight is paused because the child stopped playing."""

        return self.state is AppState.FLIGHT and self.run is not None and self._pace <= 0.0

    @property
    def flight_moving(self) -> bool:
        """Essential motion for the frame governor: flying, or feedback still playing."""

        if self.state is not AppState.FLIGHT:
            return False
        if not self.resting:
            return True
        now = self.clock()
        motion = self.motion
        return (
            motion.active(now)
            or self.cast.visible
            or now < motion.ring_pulse_until
            or now < motion.guide_until
        )

    def _next_pace(self, now: float, dt: float) -> float:
        run = self.run
        if run is None or run.phase is not FlightPhase.FLYING:
            return 1.0
        if now - self._last_input < REST_AFTER_SECONDS:
            return 1.0
        return max(0.0, self._pace - dt / REST_EASE_SECONDS)

    def _settle(self) -> None:
        """The dragon now hovers: show how to fly on, draw the still scene once."""

        if self.hud is not None:
            self.hud.keys.show(None)
        if self._frames is not None:
            self._frames.invalidate()

    def _wake(self) -> None:
        """Child input while resting: fly on at once."""

        if self._pace >= 1.0:
            return
        self._pace = 1.0
        if self.hud is not None:
            self.hud.keys.hide()
            self.hud.keys.show(KEY_HINT_START_SECONDS)

    def _steering_held(self) -> bool:
        if any(self._keys_v.values()) or any(self._keys_h.values()) or self._pointer_down:
            return True
        return normalize_stick(*self._stick, DEFAULT_INPUT_POLICY.stick_dead_zone).magnitude > 0.0

    def render(self) -> None:
        surface = self.canvas.surface
        now = self.clock()
        if self.state is AppState.MAP:
            frames = self.art.dragon_frames(self.progress.look, MAP_DRAGON_HEIGHT)
            self.map_renderer.draw(surface, frames, now, MAP_PREVIEW_CENTER)
        elif self.state is AppState.FLIGHT and self.run is not None:
            frames = self.art.dragon_frames(self.progress.look)
            self.flight_renderer.draw(surface, self.run, frames, self.motion, now)
            if self.hud is not None:
                self.hud.draw_keys(surface)
        self._surfaces.draw(surface)

    # -- input ----------------------------------------------------------------

    def _make_input(self) -> PygameControlInput:
        return PygameControlInput(to_logical=self.canvas.pointer, is_safe=lambda pos: _safe_point(self.screen, pos))

    def _layout(self) -> ControlLayout:
        return ControlLayout.for_canvas(self.canvas, self.screen.get_size())

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self._running = False
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._running = False
            return
        if event.type == pygame.VIDEORESIZE:
            self._relayout()
            return
        if event.type == getattr(pygame, "WINDOWFOCUSLOST", -1):
            self._release_all()
            return
        if self.state is not AppState.FLIGHT:
            translated = self._input.translate(event)
            if translated is not None:
                self._surfaces.dispatch(translated)
            return
        if event.type in {pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP}:
            translated = self._input.translate(event)
            if isinstance(translated, KitPointer):
                self._pointer(translated)
            return
        if self.hud is not None:
            self.hud.keys.observe_event(event)  # flight redraws every frame
        semantic = self._game_input.digital(event)
        if semantic is not None:
            self._last_source = semantic.source
            self._on_semantic(semantic.action, semantic.edge)
            return
        axis = self._game_input.controller_axis(event)
        if axis is not None:
            self._on_stick(axis.axis, axis.value)

    def _on_semantic(self, action: SemanticAction, edge: InputEdge) -> None:
        pressed = edge is InputEdge.PRESSED
        if action in _VERTICAL:
            self._keys_v[action] = pressed
        elif action in _HORIZONTAL:
            self._keys_h[action] = pressed
        elif action in (SemanticAction.PRIMARY, SemanticAction.ACTIVATE) and pressed:
            self._flap()
        if pressed:
            self._note_input()

    def _on_stick(self, axis: ControllerAxis, value: float) -> None:
        x, y = self._stick
        if axis is ControllerAxis.LEFT_X:
            x = value
        elif axis is ControllerAxis.LEFT_Y:
            y = value
        else:
            return
        self._stick = (x, y)
        vector = normalize_stick(x, y, DEFAULT_INPUT_POLICY.stick_dead_zone)
        if vector.magnitude > 0.0:
            self._last_source = InputSource.CONTROLLER
            self._note_input()

    def _pointer(self, pointer: KitPointer) -> None:
        if pointer.phase is PointerPhase.DOWN:
            self._pointer_down = True
            self._press_y = float(pointer.position[1])
            self._drag_y = None
            self._last_source = InputSource.POINTER
            self._flap()
            self._note_input()
        elif pointer.phase is PointerPhase.MOVE and self._pointer_down:
            y = float(pointer.position[1])
            if self._drag_y is not None or abs(y - self._press_y) > DRAG_SLOP:
                self._drag_y = y
                self._note_input()
        elif pointer.phase in (PointerPhase.UP, PointerPhase.CANCEL):
            self._pointer_down = False
            self._drag_y = None

    def _steer(self) -> FlightInput:
        vertical = sum(direction for action, direction in _VERTICAL.items() if self._keys_v.get(action))
        horizontal = sum(direction for action, direction in _HORIZONTAL.items() if self._keys_h.get(action))
        stick = normalize_stick(*self._stick, DEFAULT_INPUT_POLICY.stick_dead_zone)
        if vertical == 0 and abs(stick.y) > 0:
            vertical = stick.y
        if horizontal == 0 and abs(stick.x) > 0:
            horizontal = stick.x
        return FlightInput(vertical=float(vertical), horizontal=float(horizontal), drag_y=self._drag_y)

    def _flap(self) -> None:
        self._activated = True
        if self.run is not None and self.run.flap():
            self.audio.play("flap")

    def _release_all(self) -> None:
        self._keys_v.clear()
        self._keys_h.clear()
        self._stick = (0.0, 0.0)
        self._pointer_down = False
        self._drag_y = None

    def _note_input(self) -> None:
        self._last_input = self.clock()
        self._wake()
        if self._hints.count:
            self.motion.hint_glyphs = ()
            self.motion.ring_pulse_until = -1.0
        self._hints.reset(self._last_input)

    def _relayout(self) -> None:
        self.screen = pygame.display.get_surface() or self.screen
        self.canvas = PygameReferenceCanvas(self.screen)
        self._input = self._make_input()
        layout = self._layout()
        self.map.relayout(layout)
        self.map.sync(self.progress)
        if self.hud is not None:
            self.hud.relayout(layout)

    # -- tools/tests ------------------------------------------------------------

    def tap(self, raw_pos: tuple[int, int]) -> bool:
        """Deliver one complete tap at a physical position."""

        self._activated = False
        for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            self.handle_event(pygame.event.Event(kind, pos=raw_pos, button=1))
        return self._activated

    def press(self, key: int) -> bool:
        self._activated = False
        self.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode=""))
        self.handle_event(pygame.event.Event(pygame.KEYUP, key=key, mod=0, unicode=""))
        return self._activated

    # -- map ------------------------------------------------------------------------

    def _on_course(self, index: int) -> None:
        if not self.progress.is_unlocked(index):
            return
        self._activated = True
        self.audio.play("pop")
        self.start_course(index)

    def _on_look(self, look_id: str) -> None:
        if not self.progress.look_unlocked(look_id):
            return
        self._activated = True
        self.progress.look = look_id
        self.progress_port.save(self.progress)
        self.audio.play("pop")
        self.map.sync(self.progress)

    def show_map(self, focus: int | None = None) -> None:
        self.state = AppState.MAP
        self.run = None
        self.hud = None
        self.cast.hide()
        self.motion.clear()
        self.completion.clear()
        self._surfaces.replace(self.map.layer)
        self.map.sync(self.progress, refocus=self.progress.first_open_course() if focus is None else focus)

    # -- flight ---------------------------------------------------------------------

    def start_course(self, index: int) -> None:
        index = max(0, min(len(COURSES) - 1, index))
        spec = COURSES[index]
        self.course_index = index
        course = self.builder.build(spec, assist=self.progress.assist.get(spec.course_id, False))
        self.run = FlightRun(course)
        self.hud = FlightHud(self.kit, self._layout(), rings=spec.rings, gems=spec.gems, clock=self.clock)
        self.hud.keys.show(KEY_HINT_START_SECONDS)
        self.hud.sync(self.run)
        self.flight_renderer.prepare(spec)
        self._surfaces.replace(self.hud.layer)
        self.state = AppState.FLIGHT
        self.completion.clear()
        self.motion.clear()
        self._release_all()
        now = self.clock()
        self._flight_started = now
        self._last_input = now
        self._pace = 1.0
        self._hints.reset(now)
        self.session_id = f"{self.session_id.rsplit('-', 1)[0]}-{self.rng.randrange(1_000_000):06d}"
        self.motion.hint_glyphs = self._hint_glyphs()
        self.motion.hint_since = now
        self.cast.hide()
        self.audio.say("ready.go")
        if not self._rings_told:
            self._rings_told = True  # once per visit: the goal of every course
            self.audio.then("fly_rings")

    def _on_flight_event(self, event: FlightEvent, now: float) -> None:
        assert self.run is not None
        kind = event.kind
        if kind is FlightEventKind.STAR:
            self.motion.add("sparkle", event.x, event.y, now, 72)
            self.audio.play("star")
        elif kind is FlightEventKind.GEM:
            self.motion.add("star_burst", event.x, event.y, now, 110)
            self.audio.play("gem")
        elif kind is FlightEventKind.RING_PASSED:
            self.motion.add("star_burst", event.x, event.y - 60, now, 128)
            self.motion.add("star_burst", event.x, event.y + 60, now + 0.08, 112)
            self.motion.guide_until = -1.0
            self.audio.play("ring")
            self.cast.cheer()
            self.audio.say("praise.general")
            self.events.ring_passed(self.session_id, self.run.spec.course_id, event.index)
        elif kind is FlightEventKind.HALFWAY:
            self.audio.say("encourage.progress")
        elif kind is FlightEventKind.RING_MISSED:
            self.motion.add("dust_puff", event.x, event.y, now, 120)
            self.motion.guide_until = now + self._hints.animation_seconds(GUIDE_SECONDS)
            self.motion.ring_pulse_until = now + GUIDE_SECONDS
            self.audio.play("miss")
            self.cast.think()
            self.audio.say("encourage.retry")
        elif kind is FlightEventKind.BUMP:
            self.motion.add("dust_puff", self.run.distance + 40, self.run.flier.y, now, 96)
            self.audio.play("boing")
        elif kind is FlightEventKind.FINISH:
            for i, (dx, dy) in enumerate(((-120, 200), (0, 140), (140, 220), (60, 320), (-60, 300))):
                self.motion.add("confetti", event.x + dx, dy, now + i * 0.12, 150)
            self.motion.hint_glyphs = ()
            self.audio.play("finish")
            self.cast.cheer(2.6)
            self.audio.say("celebrate.success")
        elif kind is FlightEventKind.DONE:
            self._complete()

    def _complete(self) -> None:
        assert self.run is not None
        result = self.run.result
        unlocked_look = self.progress.record(result.course_id, result.earned, result.stars, result.misses)
        self.progress_port.save(self.progress)
        self.events.course_completed(
            self.session_id,
            result.course_id,
            {
                "stars": result.stars,
                "gems": result.gems,
                "rings": len(self.run.course.rings),
                "retries": result.misses,
                "earned": result.earned,
            },
        )
        body = "victory.new_look" if unlocked_look else "victory.subtitle"
        self.completion.prepare(
            CompletionContent(
                title=self.resources.text("victory.title"),
                primary_label=self.resources.text("button.fly_again"),
                body_lines=(self.resources.text(body),),
                achievement_count=result.earned,
                secondary_label=self.resources.text("button.next"),
            )
        )
        if self.hud is not None:
            self.hud.sync(self.run)
        self._surfaces.push_overlay(
            CompletionOverlay(self.completion, on_primary=self._fly_again, on_secondary=self._next)
        )
        self.cast.hide()
        self.state = AppState.COMPLETE

    def _fly_again(self) -> None:
        self._activated = True
        self.start_course(self.course_index)

    def _next(self) -> None:
        self._activated = True
        following = self.course_index + 1
        focus = following if following < len(COURSES) and self.progress.is_unlocked(following) else None
        self.show_map(focus)

    # -- hints ----------------------------------------------------------------------

    def _hint_glyphs(self) -> tuple[str, ...]:
        if self._last_source is InputSource.CONTROLLER:
            return ("button_a",)
        if self._last_source in (InputSource.POINTER, InputSource.TOUCH):
            return ("drag_hint",)
        return ("arrow_up", "key_space")

    def _maybe_hint(self, now: float) -> None:
        run = self.run
        if run is None or run.phase is not FlightPhase.FLYING:
            return
        if self._hints.count == 0 and self.motion.hint_glyphs and now - self._flight_started > START_HINT_SECONDS:
            if now - self._last_input < IdleHintScheduler.DEFAULT_GAPS[0]:
                self.motion.hint_glyphs = ()
        step = self._hints.poll(now, self._last_input)
        if not step:
            return
        self.motion.hint_glyphs = self._hint_glyphs()
        self.motion.hint_since = now
        self.motion.ring_pulse_until = now + self._hints.animation_seconds(3.0)
        if self.hud is not None:
            # Reveal the keycaps, but light only keys that are really held
            # (a "demonstration" lit Left/Right nobody pressed; Acer 2026-10-16).
            self.hud.keys.show(KEY_HINT_START_SECONDS)
        if step >= 2:
            self.cast.point(self._hints.animation_seconds(2.2))
            self.motion.guide_until = now + self._hints.animation_seconds(GUIDE_SECONDS)


def _safe_point(surface: pygame.Surface, position: tuple[int, int]) -> bool:
    viewport = activity_viewport_for_surface(surface)
    x, y = position
    if not (0 <= x < viewport.surface.width and 0 <= y < viewport.surface.height):
        return False
    for protected in viewport.protected_regions:
        if protected.x <= x < protected.right and protected.y <= y < protected.bottom:
            return False
    return True


__all__ = ["AppState", "DragonFlightActivity"]
