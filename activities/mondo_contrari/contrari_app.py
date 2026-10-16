"""Lifecycle, scripted moments and shared-kit input for Mondo Contrari.

"Flash's Opposite Game": one visit is four or five opposite pairs (one
progress dot each). For every pair Flash says a concept word ("UP! High up in
the clouds!"), the child makes it happen (taps the cloud or the flowers, drags
the balloon; puts the kitten in the box or out by its ball) or finds it (the
BIG elephant, the OPEN gift, the FAST lane), and then Flash points and says
the opposite word for the child to act on. Level 3 adds a surprise third word
so the answer is never just "the other one". There is no text to read and
no answer-revealing highlight: the word caption appears only afterwards.

Feedback follows ADR 0037: correct = the concept happens + Flash
``pose_cheer`` + library FX + an approved praise line; try again = Flash
``pose_think`` + "let's try again" + the scene demonstrates the asked word
while it is repeated, with unlimited retries. Hints are graduated (~6 s idle
-> Flash points and BOTH choices glow; again -> the word replays). The visit
ends on the shared cast completion scene.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from enum import StrEnum
import random
import time

import pygame

from greia_platform.activity_api import activity_stop_requested, mark_activity_ready
from greia_platform.frame_governor import FrameGovernor, FrameKind
from greia_platform.activity_controls import (
    BodyShape,
    ControlKit,
    ControlLayout,
    ControlTheme,
    KitPointer,
    PointerPhase,
    PygameControlInput,
    mix,
)
from greia_platform.activity_feedback import CastFeedback
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
    from .contrari_art import ContrariArt
    from .contrari_audio import ContrariAudio
    from .contrari_controls import ContrariControls
    from .contrari_layout import FLASH_HEIGHT, LANE_RECTS
    from .contrari_model import (
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        ContrariRoundFactory,
        ContrariSession,
        Phase,
        Pole,
        adapt_level,
    )
    from .contrari_renderer import ContrariCast, ContrariRenderer, FxPlayer
    from .contrari_scenes import MakeScene, PairScene, build_scenes
    from .contrari_services import EventPort, ProgressPort
else:
    from contrari_art import ContrariArt
    from contrari_audio import ContrariAudio
    from contrari_controls import ContrariControls
    from contrari_layout import FLASH_HEIGHT, LANE_RECTS
    from contrari_model import (
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        ContrariRoundFactory,
        ContrariSession,
        Phase,
        Pole,
        adapt_level,
    )
    from contrari_renderer import ContrariCast, ContrariRenderer, FxPlayer
    from contrari_scenes import MakeScene, PairScene, build_scenes
    from contrari_services import EventPort, ProgressPort

IDLE_HINT_SECONDS = 6.0
WELCOME_LEAD = 0.3
WELCOME_MAX = 4.0
POINT_SECONDS = 1.8
THINK_SECONDS = 1.3
CELEBRATE_HOLD = 1.9
PAIR_DONE_HOLD = 1.0
DRAG_START = 12
MAX_SCHEDULED = 32
NAVY = (37, 59, 89)  # theme token "navy" behind the completion card
SAND = (238, 221, 186)  # theme token "sand" for the race lanes

# Library FX and procedural effect per concept (presentation only).
_PERFORM_FX = {
    Pole.UP: ("star_burst", "rise"),
    Pole.DOWN: ("sparkle", "fall"),
    Pole.BIG: ("star_burst", "ding"),
    Pole.SMALL: ("sparkle", "pop"),
    Pole.IN: ("sparkle", "boing"),
    Pole.OUT: ("star_burst", "boing"),
    Pole.OPEN: ("heart_pop", "ding"),
    Pole.CLOSED: ("sparkle", "pop"),
    Pole.FAST: ("star_burst", "whoosh"),
    Pole.SLOW: ("sparkle", "pop"),
}


class AppState(StrEnum):
    PLAYING = "playing"
    TERMINAL = "terminal"


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

    @property
    def busy(self) -> bool:
        return bool(self._entries)

    def clear(self) -> None:
        self._entries.clear()


class ContrariActivity:
    """Coordinate the opposite session, pair scenes, shared-kit controls and lifecycle."""

    def __init__(
        self,
        *,
        screen: pygame.Surface,
        canvas: PygameReferenceCanvas,
        session: ContrariSession,
        factory: ContrariRoundFactory,
        typography: GreiaTypography,
        resources: LocalizedResources,
        progress: ProgressPort,
        events: EventPort,
        audio: ContrariAudio,
        rng: random.Random,
        session_id: str,
        clock: Callable[[], float] = time.monotonic,
        kit: ControlKit | None = None,
        art: ContrariArt | None = None,
    ) -> None:
        self.screen = screen
        self.canvas = canvas
        self.session = session
        self.factory = factory
        self.typography = typography
        self.resources = resources
        self.progress = progress
        self.events = events
        self.audio = audio
        self.rng = rng
        self.session_id = session_id
        self.clock = clock

        # Shared control kit (ADR 0037): play Collection -> ocean accent.
        self.kit = kit if kit is not None else ControlKit(typography, ControlTheme.for_accent("ocean"))
        self.art = art if art is not None else ContrariArt()
        self.scenes: dict = build_scenes(self.art, self._lane_strips())
        feedback = CastFeedback("flash", height=FLASH_HEIGHT, art=self.kit.art, clock=clock)
        self.cast = ContrariCast(feedback, self.art.cast_pose("flash", "pose_point", FLASH_HEIGHT), clock)
        self.fx = FxPlayer(self.art, clock)
        self.renderer = ContrariRenderer(self.art, self.cast, self.fx, clock=clock)
        self.timeline = Timeline(clock)
        self.controls = ContrariControls(
            self.kit,
            ControlLayout.for_canvas(canvas, screen.get_size()),
            total=len(session.rounds),
            on_choice=self._on_choice,
            on_listen=self._on_listen,
        )
        self._surfaces = SurfaceNavigator(self.controls.layer)
        self._input = PygameControlInput(to_logical=canvas.pointer, is_safe=lambda pos: _safe_point(self.screen, pos))
        self.completion: PygameCompletionScreen | None = None
        self.scene: PairScene | None = None
        self.state = AppState.PLAYING
        self._running = True
        self._ready_published = False
        self._dirty = True
        self._activated = False
        self._busy = True
        self._drag_from: tuple[int, int] | None = None
        self._dragging = False
        self._last_activity = clock()
        self._idle_hints = 0
        self.audio.say("welcome")
        self._start_round(lead=min(WELCOME_MAX, self.audio.length("welcome") + WELCOME_LEAD))

    # -- main loop --------------------------------------------------------------

    def run(self) -> int:
        frames = FrameGovernor()
        try:
            while self._running and not activity_stop_requested():
                for event in frames.events():
                    self._handle_event(event)
                repeat = self._input.poll()
                if repeat is not None:
                    self._dispatch(repeat)
                animating = self.step()
                frame = frames.frame(dirty=self._dirty, animating=animating)
                if frame is FrameKind.FULL:
                    self.render()
                    self.canvas.present()
                    pygame.display.flip()
                    self._dirty = False
                    if not self._ready_published:
                        mark_activity_ready()
                        self._ready_published = True
                elif frame is FrameKind.POINTER:
                    self.canvas.present_pointer()
                frames.wait(polling=self._input.repeating)
        finally:
            if self.state is AppState.PLAYING:
                self.progress.save(self.session.level, self.session.history)
            self.audio.stop_speech()
            self.typography.clear()
        return 0

    def step(self) -> bool:
        """Advance timers; return True while something on screen is moving."""

        now = self.clock()
        self.audio.update()
        if self.timeline.run_due():
            self._dirty = True
        if self.cast.update():
            self._dirty = True
        self.fx.prune(now)
        if self.state is AppState.PLAYING:
            self._maybe_hint(now)
        if self.controls.layer.invalidation.should_draw:
            self._dirty = True
        scene_moving = self.state is AppState.PLAYING and self.scene is not None and self.scene.animating(now)
        return scene_moving or self.fx.active(now) or self.cast.animating

    def render(self) -> None:
        surface = self.canvas.surface
        if self.state is AppState.PLAYING:
            self.renderer.draw(surface, self.scene)
        self._surfaces.draw(surface)

    # -- input --------------------------------------------------------------------

    def _handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self._running = False
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._running = False
            return
        if event.type == pygame.VIDEORESIZE:
            self.screen = pygame.display.get_surface() or self.screen
            self.canvas = PygameReferenceCanvas(self.screen)
            self._input = PygameControlInput(
                to_logical=self.canvas.pointer, is_safe=lambda pos: _safe_point(self.screen, pos)
            )
            self.controls.relayout(ControlLayout.for_canvas(self.canvas, self.screen.get_size()))
            self._dirty = True
            return
        translated = self._input.translate(event)
        if translated is not None:
            self._dispatch(translated)

    def _dispatch(self, kit_input) -> bool:
        is_pointer = isinstance(kit_input, KitPointer)
        if not is_pointer or kit_input.phase is not PointerPhase.MOVE:
            self._note_activity()
        if is_pointer and self._drag_input(kit_input):
            return True
        result = self._surfaces.dispatch(kit_input)
        if result is UiEventResult.IGNORED and is_pointer:
            self._maybe_start_drag(kit_input)
        if self.controls.layer.invalidation.should_draw:
            self._dirty = True
        return result is not UiEventResult.IGNORED

    def tap(self, raw_pos: tuple[int, int]) -> bool:
        """Deliver one complete tap at a physical position (tests/tools)."""

        if not _safe_point(self.screen, raw_pos):
            return False
        logical = self.canvas.pointer(raw_pos)
        if logical is None:
            return False
        point = (int(logical[0]), int(logical[1]))
        self._activated = False
        self._dispatch(KitPointer(PointerPhase.DOWN, point))
        self._dispatch(KitPointer(PointerPhase.UP, point))
        return self._activated

    def drag(self, start: tuple[int, int], end: tuple[int, int], steps: int = 6) -> bool:
        """Deliver one pointer drag in logical coordinates (tests/tools)."""

        self._activated = False
        self._dispatch(KitPointer(PointerPhase.DOWN, start))
        for index in range(1, steps + 1):
            x = start[0] + (end[0] - start[0]) * index // steps
            y = start[1] + (end[1] - start[1]) * index // steps
            self._dispatch(KitPointer(PointerPhase.MOVE, (x, y)))
        self._dispatch(KitPointer(PointerPhase.UP, end))
        return self._activated

    def press(self, key: int) -> bool:
        """Deliver one key press through the shared navigation mapping."""

        self._activated = False
        translated = self._input.translate(pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode=""))
        if translated is not None:
            self._dispatch(translated)
        return self._activated

    def _note_activity(self) -> None:
        self._last_activity = self.clock()
        self._idle_hints = 0

    # -- drag (make pairs) ------------------------------------------------------------

    def _maybe_start_drag(self, pointer: KitPointer) -> None:
        scene = self.scene
        if (
            pointer.phase is not PointerPhase.DOWN
            or self._busy
            or self.state is not AppState.PLAYING
            or not isinstance(scene, MakeScene)
        ):
            return
        handle = scene.drag_handle()
        if handle is not None and handle.collidepoint(pointer.position):
            self._drag_from = pointer.position
            self._dragging = False

    def _drag_input(self, pointer: KitPointer) -> bool:
        """Own pointer input while a draggable thing is held; True when consumed."""

        if self._drag_from is None:
            return False
        scene = self.scene
        if not isinstance(scene, MakeScene):
            self._drag_from = None
            return False
        if pointer.phase is PointerPhase.MOVE:
            dx = pointer.position[0] - self._drag_from[0]
            dy = pointer.position[1] - self._drag_from[1]
            if not self._dragging and dx * dx + dy * dy >= DRAG_START * DRAG_START:
                self._dragging = True
                scene.drag_to(self._drag_from)
            if self._dragging:
                scene.drag_to(pointer.position)
                self._dirty = True
            return True
        if pointer.phase is PointerPhase.DOWN:
            return True
        # UP or CANCEL ends the gesture.
        dragging = self._dragging
        self._drag_from = None
        self._dragging = False
        if not dragging:
            return True  # a tap on the thing itself: nothing to decide
        pole = scene.drop(pointer.position) if pointer.phase is PointerPhase.UP else None
        scene.release(self.clock())
        self._dirty = True
        if pole is not None and scene.sides is not None:
            self._on_choice(scene.index_of(pole))
        return True

    # -- round flow -----------------------------------------------------------------

    def _start_round(self, lead: float = 0.0) -> None:
        current = self.session.current_round
        assert current is not None
        now = self.clock()
        self.scene = self.scenes[current.category]
        self.scene.begin_round(current, now)
        self.controls.set_total(len(self.session.rounds))
        self.controls.progress.set_progress(self.session.completed_rounds)
        self.controls.set_scene_targets(self.scene.target_rects())
        self.controls.show_caption(None)
        self.cast.reset()
        self._lock()
        self.timeline.after(lead, self._present_ask)
        self._dirty = True

    def _present_ask(self) -> None:
        ask = self.session.current_ask
        scene = self.scene
        if ask is None or scene is None:
            return
        now = self.clock()
        transition = scene.present_ask(ask, self.session.ask_index, now)
        self.controls.set_scene_targets(scene.target_rects())
        self.controls.show_caption(None)
        self.timeline.after(transition, self._ask_word)
        self._dirty = True

    def _ask_word(self) -> None:
        ask = self.session.current_ask
        if ask is None:
            return
        self.audio.queue(ask.pole.value)
        self.cast.point(POINT_SECONDS)
        self._unlock(refocus=True)

    def _lock(self) -> None:
        self._busy = True
        self.controls.set_answering(False)

    def _unlock(self, *, refocus: bool = False) -> None:
        self._busy = False
        self.controls.set_answering(True)
        if refocus:
            self.controls.focus_default()
        self._note_activity()
        self._dirty = True

    # -- gameplay callbacks --------------------------------------------------------------

    def _on_choice(self, index: int) -> None:
        scene = self.scene
        if self._busy or scene is None or self.session.phase is not Phase.ASKING:
            return
        pole = scene.pole_at(index)
        if pole is None:
            return
        self._activated = True
        result = self.session.choose(pole)
        if result.correct:
            self._celebrate(pole, round_done=result.round_complete)
        else:
            self._try_again(index)

    def _celebrate(self, pole: Pole, *, round_done: bool) -> None:
        scene = self.scene
        assert scene is not None
        now = self.clock()
        self._lock()
        duration = scene.perform(pole, now)
        fx_name, sound = _PERFORM_FX[pole]
        self.audio.play(sound)
        self.fx.add(fx_name, scene.fx_point(pole, now + duration * 0.8), delay=duration * 0.8)
        self.timeline.after(duration * 0.8, lambda: self._cheer(pole))
        hold = duration * 0.8 + CELEBRATE_HOLD
        if round_done:
            self.timeline.after(hold, self._finish_pair)
        else:
            self.timeline.after(hold, self._next_ask)
        self._dirty = True

    def _cheer(self, pole: Pole) -> None:
        self.cast.correct()
        self.audio.praise()
        # The written word is the taught object: it appears only after the act.
        self.controls.show_caption(self.resources.text(pole.text_key))
        self._dirty = True

    def _next_ask(self) -> None:
        self.session.advance()
        self._present_ask()

    def _finish_pair(self) -> None:
        milestone = self.session.consume_milestone()
        if milestone is not None:
            self.events.opposite_explored(self.session_id, milestone)
        self.controls.progress.set_progress(self.session.completed_rounds)
        self.controls.layer.invalidation.invalidate()
        self.fx.add("confetti", (self.controls.progress.rect.centerx, self.controls.progress.rect.bottom + 60))
        self.audio.play("fanfare")
        if not self.session.advance():
            self.timeline.after(PAIR_DONE_HOLD, self._complete_session)
            return
        self.timeline.after(PAIR_DONE_HOLD, self._start_round)
        self._dirty = True

    def _try_again(self, index: int) -> None:
        scene = self.scene
        assert scene is not None
        now = self.clock()
        self._lock()
        scene.wrong(index, now)
        self.cast.try_again()
        self.audio.play("boop")
        self.audio.encourage()
        self.timeline.after(THINK_SECONDS, self._demonstrate)
        self._dirty = True

    def _demonstrate(self) -> None:
        scene = self.scene
        ask = self.session.current_ask
        if scene is None or ask is None:
            return
        duration = scene.demonstrate(ask.pole, self.clock())
        self.audio.queue(ask.pole.value)
        self.cast.point(duration)
        self.timeline.after(duration + 0.2, self._unlock)
        self._dirty = True

    # -- completion ---------------------------------------------------------------------

    def _complete_session(self) -> None:
        payload = self.session.consume_completion()
        next_level = adapt_level(self.session.level, self.session.history)
        if payload is not None:
            self.progress.save(next_level, self.session.history)
            self.events.all_opposites_completed(self.session_id, payload)
        self.timeline.clear()
        self.audio.celebrate()
        pairs = len(self.session.rounds)
        self.completion = PygameCompletionScreen(
            self.typography,
            width=REFERENCE_WIDTH,
            height=REFERENCE_HEIGHT,
            palette=CompletionPalette(background=NAVY),
            scene=CompletionScene(self.kit, character="flash", star_total=pairs),
        )
        self.completion.prepare(
            CompletionContent(
                title=self.resources.text("victory.title"),
                primary_label=self.resources.text("button.play_again"),
                body_lines=(self.resources.text("victory.subtitle"),),
                achievement_count=pairs,
            )
        )
        self._surfaces.push_overlay(CompletionOverlay(self.completion, on_primary=self._restart))
        self.controls.progress.set_progress(pairs)
        self.state = AppState.TERMINAL
        self._dirty = True

    def _restart(self) -> None:
        self._activated = True
        next_level = adapt_level(self.session.level, self.session.history)
        self.session = ContrariSession(
            self.factory.build_visit(next_level), level=next_level, history=self.session.history
        )
        self.session_id = f"{self.session_id.rsplit('-', 1)[0]}-{self.rng.randrange(1_000_000):06d}"
        self._surfaces.pop_overlay()
        if self.completion is not None:
            self.completion.clear()
        self.completion = None
        self.state = AppState.PLAYING
        self.fx.clear()
        self._start_round(lead=0.4)

    # -- hints --------------------------------------------------------------------------

    def _maybe_hint(self, now: float) -> None:
        if self._busy or self.timeline.busy or self.session.phase is not Phase.ASKING:
            return
        if now - self._last_activity < IDLE_HINT_SECONDS * (self._idle_hints + 1):
            return
        self._idle_hints += 1
        if self._idle_hints == 1:
            self.session.note_hint()
        self.cast.point(POINT_SECONDS)
        if self.scene is not None:
            self.scene.pulse(now)
        if self._idle_hints >= 2:
            ask = self.session.current_ask
            if ask is not None:
                self.audio.say(ask.pole.value)
        self._dirty = True

    def _on_listen(self) -> None:
        self._activated = True
        ask = self.session.current_ask
        if ask is not None and self.session.phase is Phase.ASKING:
            self.audio.say(ask.pole.value)
            self.cast.point(1.4)
        self._dirty = True

    # -- art helpers ---------------------------------------------------------------------

    def _lane_strips(self) -> tuple[pygame.Surface | None, pygame.Surface | None]:
        """Two soft sand race lanes painted with the kit recipe (built once)."""

        painter = self.kit.painter
        strips = []
        for rect in LANE_RECTS:
            body = painter.body(
                BodyShape.PILL,
                (rect.width, rect.height - 18),
                SAND,
                contour=mix(SAND, painter.theme.ink, 0.35),
                contour_width=3,
                highlight=False,
            ).copy()
            body.set_alpha(150)
            strips.append(body)
        return (strips[0], strips[1])


def _safe_point(surface: pygame.Surface, position: tuple[int, int]) -> bool:
    viewport = activity_viewport_for_surface(surface)
    x, y = position
    if not (0 <= x < viewport.surface.width and 0 <= y < viewport.surface.height):
        return False
    for protected in viewport.protected_regions:
        if protected.x <= x < protected.right and protected.y <= y < protected.bottom:
            return False
    return True


__all__ = ["AppState", "ContrariActivity", "Timeline"]
