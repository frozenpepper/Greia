"""Lifecycle, timeline and shared-kit input for Il Giardino dei Numeri.

One visit is five baskets. Each basket: Dani points at the garden and the
voice asks the child to touch and count; every touched object says its
number and hops into the crate. When all are counted, the last number tells
how many: at stage 1 the crate pulses and a big numeral + dot card closes the
set; from stage 2 the child first chooses the card that says how many.
Feedback follows ADR 0037 (Dani ``pose_cheer`` / ``pose_think``), hints are
graduated (idle -> point + pulse; wrong -> demonstrate the recount), and the
visit ends on the shared cast completion scene.
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
    ControlKit,
    ControlLayout,
    ControlTheme,
    KitPointer,
    PointerPhase,
    PygameControlInput,
)
from greia_platform.activity_feedback import CastFeedback, IdleHintScheduler
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
    from .giardino_art import GardenArt
    from .giardino_audio import GiardinoAudio
    from .giardino_controls import GardenControls
    from .giardino_model import (
        DANI_HEIGHT,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        ChoiceResult,
        GardenSession,
        Phase,
        TapResult,
    )
    from .giardino_renderer import (
        CLOSE_CARD_CENTER,
        HOP_SECONDS,
        GardenCast,
        GardenRenderer,
        SceneMotion,
    )
    from .giardino_services import EventPort, ProgressPort
else:
    from giardino_art import GardenArt
    from giardino_audio import GiardinoAudio
    from giardino_controls import GardenControls
    from giardino_model import (
        DANI_HEIGHT,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        ChoiceResult,
        GardenSession,
        Phase,
        TapResult,
    )
    from giardino_renderer import (
        CLOSE_CARD_CENTER,
        HOP_SECONDS,
        GardenCast,
        GardenRenderer,
        SceneMotion,
    )
    from giardino_services import EventPort, ProgressPort

SETTLE_SECONDS = 0.95
RETRY_LEAD_SECONDS = 1.4
RECOUNT_STEP_SECONDS = 0.62
CLOSE_PULSE_SECONDS = 0.24
CLOSE_HOLD_SECONDS = 2.5
MAX_SCHEDULED = 32
PRAISE_CUES = ("well_done", "praise_1", "praise_2")
GARDEN_NIGHT = (40, 81, 58)  # theme token "forest" behind the completion card


class AppState(StrEnum):
    PLAYING = "playing"
    TERMINAL = "terminal"


class Timeline:
    """Tiny bounded scheduler for the scripted moments (recount, close)."""

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


class GiardinoApp:
    """Coordinate the counting model, shared-kit controls, art and lifecycle."""

    def __init__(
        self,
        *,
        screen: pygame.Surface,
        canvas: PygameReferenceCanvas,
        session: GardenSession,
        typography: GreiaTypography,
        resources: LocalizedResources,
        audio: GiardinoAudio,
        progress: ProgressPort,
        events: EventPort,
        rng: random.Random | None = None,
        clock: Callable[[], float] = time.monotonic,
        kit: ControlKit | None = None,
        art: GardenArt | None = None,
    ) -> None:
        self.screen = screen
        self.canvas = canvas
        self.session = session
        self.typography = typography
        self.resources = resources
        self.audio = audio
        self.progress = progress
        self.events = events
        self.rng = rng if rng is not None else random.Random()
        self.clock = clock
        self.session_id = f"{int(time.time())}-{self.rng.randrange(1_000_000):06d}"

        # Shared control kit (ADR 0037): learn Collection -> orange accent.
        self.kit = kit if kit is not None else ControlKit(typography, ControlTheme.for_accent("orange"))
        self.art = art if art is not None else GardenArt(self.kit.painter)
        feedback = CastFeedback("dani", height=DANI_HEIGHT, art=self.kit.art, clock=clock)
        self.cast = GardenCast(feedback, self.art.cast_pose("dani", "pose_point", DANI_HEIGHT), clock)
        self.renderer = GardenRenderer(self.art, self.cast, clock=clock)
        self.motion = SceneMotion()
        self.timeline = Timeline(clock)
        self.controls = GardenControls(
            self.kit,
            self.art,
            ControlLayout.for_canvas(canvas, screen.get_size()),
            session.total_rounds,
            on_item=self._on_item,
            on_choice=self._on_choice,
            on_listen=self._on_listen,
        )
        self._surfaces = SurfaceNavigator(self.controls.layer)
        self._input = PygameControlInput(to_logical=canvas.pointer, is_safe=lambda pos: _safe_point(self.screen, pos))
        self.completion = PygameCompletionScreen(
            typography,
            width=REFERENCE_WIDTH,
            height=REFERENCE_HEIGHT,
            palette=CompletionPalette(background=GARDEN_NIGHT),
            scene=CompletionScene(self.kit, character="dani", star_total=session.total_rounds),
        )
        self.state = AppState.PLAYING
        self._running = True
        self._ready_published = False
        self._dirty = True
        self._activated = False
        self._first_round = True
        self._praise_index = 0
        self._last_activity = clock()
        self._hints = IdleHintScheduler(now=self._last_activity)
        self._wobble_id: str | None = None
        self._start_round()

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
            self.progress.save(self.session.progress)
            self.typography.clear()
        return 0

    def step(self) -> bool:
        """Advance timers; return True while something on screen is moving."""

        now = self.clock()
        if self.timeline.run_due():
            self._dirty = True
        if self.cast.update():
            self._dirty = True
        self.motion.prune(now)
        if self.state is AppState.PLAYING:
            self._maybe_hint(now)
        if self.controls.layer.invalidation.should_draw:
            self._dirty = True
        wobbling = self.motion.wobble_started is not None and now - self.motion.wobble_started < 0.4
        return self.motion.active(now) or self.cast.animating or wobbling

    def render(self) -> None:
        surface = self.canvas.surface
        if self.state is AppState.PLAYING:
            self.renderer.draw(surface, self.session.current, self.motion)
            self._draw_controls(surface)
        else:
            self._surfaces.draw(surface)

    def _draw_controls(self, surface: pygame.Surface) -> None:
        """Draw kit controls; a rejected answer card shakes briefly."""

        started = self.motion.wobble_started
        shaking = next((b for b in self.controls.choices if b.control_id == self._wobble_id), None)
        elapsed = self.clock() - started if started is not None else 1.0
        if shaking is None or elapsed >= 0.4:
            self._surfaces.draw(surface)
            return
        offset = int(9 * (1 - elapsed / 0.4) * (1 if int(elapsed * 40) % 2 else -1))
        base = shaking.rect
        shaking.rect = base.move(offset, 0)
        self._surfaces.draw(surface)
        shaking.rect = base

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
        """Route one kit input; IGNORED pointer-up on the grass is a soft miss."""

        if not isinstance(kit_input, KitPointer) or kit_input.phase is not PointerPhase.MOVE:
            self._note_activity()
        result = self._surfaces.dispatch(kit_input)
        if (
            result is UiEventResult.IGNORED
            and self.state is AppState.PLAYING
            and isinstance(kit_input, KitPointer)
            and kit_input.phase is PointerPhase.DOWN
        ):
            self._on_grass(kit_input.position)
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

    def press(self, key: int) -> bool:
        """Deliver one key press through the shared navigation mapping."""

        self._activated = False
        translated = self._input.translate(pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode=""))
        if translated is not None:
            self._dispatch(translated)
        return self._activated

    def _note_activity(self) -> None:
        self._last_activity = self.clock()
        self._hints.reset(self._last_activity)

    # -- round flow ---------------------------------------------------------------

    def _start_round(self) -> None:
        round_ = self.session.current
        self.timeline.clear()
        self.motion.clear(self.clock())
        self.art.preload(round_.kind)
        self.controls.bind_round(round_)
        self.controls.set_progress(self.session.completed_rounds)
        self.cast.reset()
        self.cast.point(1.8)
        self.audio.say("intro" if self._first_round else "prompt")
        self._first_round = False
        self._note_activity()
        self._dirty = True

    def _on_item(self, item_id: int) -> None:
        round_ = self.session.current
        outcome = round_.tap_item(item_id)
        if outcome.result is not TapResult.COUNTED:
            return
        self._activated = True
        now = self.clock()
        item = round_.item(item_id)
        self.motion.hops[item_id] = now
        self.motion.add_fx("sparkle", (int(item.x), int(item.y)), now)
        self.timeline.after(HOP_SECONDS, lambda i=item_id, n=outcome.number: self._landed(i, n))
        self.audio.chime(outcome.number)
        self.audio.say_number(outcome.number)
        self.controls.sync(round_)
        if outcome.finished_counting:
            self.timeline.after(SETTLE_SECONDS, self._after_counting)
        self._dirty = True

    def _landed(self, item_id: int, number: int) -> None:
        now = self.clock()
        self.motion.badges[item_id] = (now, number)
        self.motion.pops[item_id] = now
        self.audio.play("pop")

    def _after_counting(self) -> None:
        round_ = self.session.current
        round_.finish_counting()
        if round_.phase is Phase.ASKING:
            # "How many?": the crate glows in order (no numbers shown) while
            # Dani points at the answer cards.
            self.motion.badges.clear()
            self.controls.sync(round_, refocus=True)
            self.cast.point(2.0)
            self.audio.play("pop")
            self._recount(0.15, voiced=False, badges=False)
            if self.audio.has_speech("how_many"):
                self.audio.say("how_many")
            self._note_activity()
        else:
            self._begin_close()
        self._dirty = True

    def _on_choice(self, index: int) -> None:
        round_ = self.session.current
        value = self.controls.choice_value(index)
        if value is None:
            return
        result = round_.choose(value)
        if result is ChoiceResult.IGNORED:
            return
        self._activated = True
        self.timeline.clear()  # drop any pending "look at the crate" cue
        if result is ChoiceResult.CORRECT:
            self.controls.sync(round_)
            self._begin_close()
            return
        # Try again: gentle think pose, a kind retry line, then demonstrate the
        # recount (the last number said is the answer: cardinality).
        self._wobble_id = self.controls.choices[index].control_id
        self.motion.wobble_started = self.clock()
        self.cast.try_again()
        self.audio.play("boop")
        self.audio.say("retry")
        self.controls.sync(round_)
        self._recount(RETRY_LEAD_SECONDS, voiced=True, then=self._finish_demo)
        self._dirty = True

    def _finish_demo(self) -> None:
        round_ = self.session.current
        round_.finish_demonstration()
        self.controls.sync(round_, refocus=True)
        self._note_activity()
        self._dirty = True

    def _recount(
        self,
        lead: float,
        *,
        voiced: bool,
        badges: bool = True,
        then: Callable[[], object] | None = None,
    ) -> float:
        """Pulse crate objects in counting order; returns the total duration.

        Silent hint pulses pass ``badges=False`` so the cue never prints the
        answer; the voiced demonstration and the close show the numbers.
        """

        round_ = self.session.current
        ordered = sorted((item for item in round_.items if item.counted), key=lambda it: it.order)
        step = RECOUNT_STEP_SECONDS if voiced else CLOSE_PULSE_SECONDS
        for position, item in enumerate(ordered):
            self.timeline.after(
                lead + step * position,
                lambda i=item.item_id, n=item.order, v=voiced, b=badges: self._pulse(i, n, v, b),
            )
        total = lead + step * len(ordered)
        if then is not None:
            self.timeline.after(total + 0.2, then)
        return total

    def _pulse(self, item_id: int, number: int, voiced: bool, badges: bool = True) -> None:
        now = self.clock()
        self.motion.pops[item_id] = now
        if badges:
            self.motion.badges[item_id] = (now, number)
        self.audio.chime(number)
        if voiced:
            self.audio.say_number(number)
        self._dirty = True

    def _begin_close(self) -> None:
        """Cardinality close: pulse the set in order, then "that's N!"."""

        duration = self._recount(0.1, voiced=False)
        self.timeline.after(duration + 0.25, self._show_close)

    def _show_close(self) -> None:
        round_ = self.session.current
        now = self.clock()
        self.motion.close_number = round_.target
        self.motion.close_started = now
        # Celebrate around the card, never over the numeral being taught.
        cx, cy = CLOSE_CARD_CENTER
        self.motion.add_fx("confetti", (cx - 190, cy - 110), now)
        self.motion.add_fx("confetti", (cx + 190, cy - 110), now)
        self.motion.add_fx("star_burst", (cx - 175, cy + 60), now)
        self.motion.add_fx("star_burst", (cx + 175, cy + 60), now)
        self.cast.correct()
        praise = PRAISE_CUES[self._praise_index % len(PRAISE_CUES)]
        self._praise_index += 1
        self.audio.say_number(round_.target, then=praise)
        self.audio.play("pop")
        self.timeline.after(CLOSE_HOLD_SECONDS, self._finish_round)
        self._dirty = True

    def _finish_round(self) -> None:
        index = self.session.completed_rounds + 1
        summary = self.session.finish_round()
        self.events.set_counted(self.session_id, index, summary)
        self.progress.save(self.session.progress)
        self.controls.set_progress(self.session.completed_rounds)
        if self.session.complete:
            self._complete_session()
            return
        self.session.next_round()
        self._start_round()

    def _complete_session(self) -> None:
        self.session.progress.sessions_completed += 1
        self.progress.save(self.session.progress)
        self.events.basket_filled(self.session_id, self.session.completed_rounds, self.session.stage)
        self.timeline.clear()
        self.audio.play("fanfare")
        self.audio.say("basket_full")
        self.completion.prepare(
            CompletionContent(
                title=self.resources.text("victory.title"),
                primary_label=self.resources.text("button.play_again"),
                achievement_count=self.session.total_rounds,
            )
        )
        self._surfaces.push_overlay(CompletionOverlay(self.completion, on_primary=self._restart))
        self.state = AppState.TERMINAL
        self._dirty = True

    def _restart(self) -> None:
        self._activated = True
        self._surfaces.pop_overlay()
        self.completion.clear()
        self.session_id = f"{self.session_id.rsplit('-', 1)[0]}-{self.rng.randrange(1_000_000):06d}"
        self.session.restart()
        self.state = AppState.PLAYING
        self._start_round()

    # -- hints and soft feedback ----------------------------------------------------

    def _maybe_hint(self, now: float) -> None:
        round_ = self.session.current
        if round_.phase not in {Phase.COUNTING, Phase.ASKING} or self.timeline.busy:
            return
        step = self._hints.poll(now, self._last_activity)
        if not step:
            return
        if step == 1:
            round_.note_hint()
        self.cast.point(self._hints.animation_seconds(1.8))
        if round_.phase is Phase.COUNTING:
            waiting = round_.next_uncounted()
            if waiting is not None:
                for beat in range(3):
                    self.timeline.after(beat * 0.5, lambda item=waiting: self._hint_pulse(item))
            if step >= 2:
                self.audio.say("prompt")
        else:
            # Look at the crate again: a silent recount cue, never the answer.
            self._recount(0.0, voiced=False, badges=False)
        self._dirty = True

    def _hint_pulse(self, item) -> None:
        now = self.clock()
        if item.counted:
            return
        self.motion.pops[item.item_id] = now
        self.motion.add_fx("sparkle", (int(item.x), int(item.y)), now)
        self._dirty = True

    def _on_listen(self) -> None:
        self._activated = True
        self.audio.say("prompt")
        self.cast.point(1.4)
        self._dirty = True

    def _on_grass(self, position: tuple[int, int]) -> None:
        if self.session.current.phase is not Phase.COUNTING:
            return
        self.motion.add_fx("ripple", position, self.clock())
        self.audio.play("ripple")
        self._dirty = True

def _safe_point(surface: pygame.Surface, position: tuple[int, int]) -> bool:
    viewport = activity_viewport_for_surface(surface)
    x, y = position
    if not (0 <= x < viewport.surface.width and 0 <= y < viewport.surface.height):
        return False
    for protected in viewport.protected_regions:
        if protected.x <= x < protected.right and protected.y <= y < protected.bottom:
            return False
    return True


__all__ = ["AppState", "GiardinoApp", "Timeline"]
