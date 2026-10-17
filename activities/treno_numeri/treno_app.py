"""Lifecycle, timeline and shared-kit input for Treno Numeri (Number Express).

One journey is five stations. At each station Dani's train pulls in, the
order board shows how many cargo to load (numeral + dot card, then numeral
alone; at the compare stages the first wagon itself is the order) and the
board "plays" the number as that many chimes. The child loads cargo one at a
time (each landing counts with a chime and a badge), can send cargo back by
tapping its wagon, and decides when to press GO. Right amount: Dani cheers,
the load is counted out and the train departs. Not right: Dani thinks, the
load is recounted and the extra or missing places are shown, then the child
tries again (unlimited, kind). Feedback follows ADR 0037 and the journey ends
on the shared cast completion scene.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from enum import StrEnum
import random
import time
from uuid import uuid4

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
    from .treno_art import TrainArt
    from .treno_audio import TrainAudio
    from .treno_content import (
        ARRIVE_FROM,
        DANI_HEIGHT,
        DEPART_TO,
        GO_CENTER,
        LOCO_TOP,
        LOCO_X,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        WAGON_WELLS,
        slot_position,
    )
    from .treno_controls import TrainControls
    from .treno_model import Cargo, GoResult, Journey, MoveResult, Phase, Station, TaskKind
    from .treno_renderer import HOP_SECONDS, Hop, SceneMotion, TrainCast, TrainRenderer, chimney_position
    from .treno_services import EventPort, ProgressPort
else:
    from treno_art import TrainArt
    from treno_audio import TrainAudio
    from treno_content import (
        ARRIVE_FROM,
        DANI_HEIGHT,
        DEPART_TO,
        GO_CENTER,
        LOCO_TOP,
        LOCO_X,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        WAGON_WELLS,
        slot_position,
    )
    from treno_controls import TrainControls
    from treno_model import Cargo, GoResult, Journey, MoveResult, Phase, Station, TaskKind
    from treno_renderer import HOP_SECONDS, Hop, SceneMotion, TrainCast, TrainRenderer, chimney_position
    from treno_services import EventPort, ProgressPort

ARRIVE_SECONDS = 1.7
DEPART_SECONDS = 1.6
PUFF_EVERY = 0.24
ORDER_BEAT_SECONDS = 0.34
RECOUNT_STEP_SECONDS = 0.55
CLOSE_STEP_SECONDS = 0.26
RETRY_LEAD_SECONDS = 1.3
MARK_HOLD_SECONDS = 1.4
MAX_SCHEDULED = 40
PRAISE_CUES = ("praise", "celebrate")
STATION_NIGHT = (37, 59, 89)  # theme token "navy" behind the completion card


class AppState(StrEnum):
    PLAYING = "playing"
    TERMINAL = "terminal"


class Drive(StrEnum):
    STOPPED = "stopped"
    ARRIVING = "arriving"
    DEPARTING = "departing"


class Timeline:
    """Tiny bounded scheduler for the scripted moments (order, recount, close)."""

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


class TrenoApp:
    """Coordinate the station model, shared-kit controls, art and lifecycle."""

    def __init__(
        self,
        *,
        screen: pygame.Surface,
        canvas: PygameReferenceCanvas,
        journey: Journey,
        typography: GreiaTypography,
        resources: LocalizedResources,
        audio: TrainAudio,
        progress: ProgressPort,
        events: EventPort,
        rng: random.Random | None = None,
        clock: Callable[[], float] = time.monotonic,
        kit: ControlKit | None = None,
        art: TrainArt | None = None,
    ) -> None:
        self.screen = screen
        self.canvas = canvas
        self.journey = journey
        self.typography = typography
        self.resources = resources
        self.audio = audio
        self.progress = progress
        self.events = events
        self.rng = rng if rng is not None else random.Random()
        self.clock = clock
        self._journey_id = uuid4().hex

        # Shared control kit (ADR 0037): learn Collection -> orange accent.
        self.kit = kit if kit is not None else ControlKit(typography, ControlTheme.for_accent("orange"))
        self.art = art if art is not None else TrainArt(self.kit.painter)
        feedback = CastFeedback("dani", height=DANI_HEIGHT, art=self.kit.art, clock=clock)
        self.cast = TrainCast(feedback, self.art.cast_pose("dani", "pose_point", DANI_HEIGHT), clock)
        self.renderer = TrainRenderer(self.art, self.cast, clock=clock)
        self.motion = SceneMotion()
        self.timeline = Timeline(clock)
        self.controls = TrainControls(
            self.kit,
            ControlLayout.for_canvas(canvas, screen.get_size()),
            journey.total_stations,
            on_cargo=self._on_cargo,
            on_wagon=self._on_wagon,
            on_go=self._on_go,
            on_sign=self._on_sign,
        )
        self._surfaces = SurfaceNavigator(self.controls.layer)
        self._input = PygameControlInput(to_logical=canvas.pointer, is_safe=lambda pos: _safe_point(self.screen, pos))
        self.completion = PygameCompletionScreen(
            typography,
            width=REFERENCE_WIDTH,
            height=REFERENCE_HEIGHT,
            palette=CompletionPalette(background=STATION_NIGHT),
            scene=CompletionScene(self.kit, character="dani", star_total=journey.total_stations),
        )
        self.state = AppState.PLAYING
        self._running = True
        self._ready_published = False
        self._dirty = True
        self._activated = False
        self._first_station = True
        self._praise_index = 0
        self._drive = Drive.STOPPED
        self._drive_started = 0.0
        self._next_puff = 0.0
        self._last_activity = clock()
        self._hints = IdleHintScheduler(now=self._last_activity)
        self._order_until = 0.0
        self._start_station()

    @property
    def station(self) -> Station:
        return self.journey.current

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
            self.progress.save(self.journey.progress)
            self.typography.clear()
        return 0

    def step(self) -> bool:
        """Advance timers and the train; return True while something moves."""

        now = self.clock()
        if self.timeline.run_due():
            self._dirty = True
        if self.cast.update():
            self._dirty = True
        moving = self._advance_train(now)
        self.motion.prune(now)
        if self.state is AppState.PLAYING:
            self._maybe_hint(now)
        if self.controls.layer.invalidation.should_draw:
            self._dirty = True
        return moving or self.motion.active(now) or self.cast.animating

    def render(self) -> None:
        surface = self.canvas.surface
        if self.state is AppState.PLAYING:
            self.renderer.draw(surface, self.station, self.motion)
        self._surfaces.draw(surface)

    # -- train drive ------------------------------------------------------------

    def _advance_train(self, now: float) -> bool:
        if self._drive is Drive.STOPPED:
            return False
        t = (now - self._drive_started) / (ARRIVE_SECONDS if self._drive is Drive.ARRIVING else DEPART_SECONDS)
        t = max(0.0, min(1.0, t))
        if self._drive is Drive.ARRIVING:
            offset = ARRIVE_FROM * (1.0 - t) ** 3  # brakes into the station
        else:
            offset = DEPART_TO * t**2  # pulls away slowly, then speeds up
        self.motion.train_offset = offset
        self.motion.wheel_frame = int(abs(offset) / 10.0)
        if now >= self._next_puff:
            self._next_puff = now + PUFF_EVERY
            x, y = chimney_position(offset)
            self.motion.add_puff(now, x, y)
            self.audio.play("chug")
        self._dirty = True
        if t >= 1.0:
            arriving = self._drive is Drive.ARRIVING
            self._drive = Drive.STOPPED
            self.motion.train_offset = 0.0 if arriving else DEPART_TO
            if arriving:
                self._arrived()
            else:
                self._finish_station()
        return True

    def _set_drive(self, drive: Drive) -> None:
        self._drive = drive
        self._drive_started = self.clock()
        self._next_puff = self._drive_started

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
        if not isinstance(kit_input, KitPointer) or kit_input.phase is not PointerPhase.MOVE:
            self._note_activity()
        result = self._surfaces.dispatch(kit_input)
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

    # -- station flow -------------------------------------------------------------

    def _start_station(self) -> None:
        station = self.station
        now = self.clock()
        self.timeline.clear()
        self.motion.clear(now)
        self.motion.train_offset = ARRIVE_FROM
        self.art.preload(station.kind)
        self.controls.bind_station(station)
        self.controls.set_progress(self.journey.completed)
        self.cast.reset()
        self._set_drive(Drive.ARRIVING)
        self.audio.play("whistle")
        if self._first_station:
            self.audio.say("toot")  # "Toot toot!" as the journey's train rolls in
        self._note_activity()
        self._dirty = True

    def _arrived(self) -> None:
        station = self.station
        station.arrived()
        self.controls.sync(station, refocus=True)
        if self._first_station:
            self.audio.say("go")
            self._first_station = False
        self._present_order()
        self._note_activity()

    def _present_order(self) -> None:
        """The board "says" the order: N chimes (or the order wagon counted)."""

        station = self.station
        self._order_until = self.clock() + 0.25 + ORDER_BEAT_SECONDS * station.order
        self.cast.point(1.6 + ORDER_BEAT_SECONDS * station.order)
        if station.task is TaskKind.SAME:
            self.audio.then("make_same")  # "Make this wagon the same!" after "go"
        if station.task is TaskKind.COUNT_OUT:
            for beat in range(station.order):
                self.timeline.after(0.25 + ORDER_BEAT_SECONDS * beat, lambda n=beat + 1: self._order_beat(n))
        else:
            for beat, slot in enumerate(station.sample_slots()):
                self.timeline.after(
                    0.25 + ORDER_BEAT_SECONDS * beat, lambda n=beat + 1, s=slot: self._sample_beat(n, s)
                )
        self._dirty = True

    def _order_beat(self, number: int) -> None:
        self.motion.sign_hop = self.clock()
        self.audio.chime(number)
        self._dirty = True

    def _sample_beat(self, number: int, slot: int) -> None:
        item = self.station.item_in_slot(slot)
        if item is not None:
            self.motion.pops[item.item_id] = self.clock()
        self.motion.sign_hop = self.clock()
        self.audio.chime(number)
        self._dirty = True

    def _on_cargo(self, item_id: int) -> None:
        station = self.station
        item = station.item(item_id)
        origin = (item.x, item.y)
        outcome = station.load(item_id)
        if outcome.result is MoveResult.FULL:
            self._activated = True
            self.motion.wobble = (1, self.clock())
            self.audio.play("creak")
            self._dirty = True
            return
        if outcome.result is not MoveResult.MOVED:
            return
        self._activated = True
        now = self.clock()
        self.motion.clear_marks()
        self.motion.hops[item_id] = Hop(now, origin, outcome.slot, True)
        self.motion.add_fx("sparkle", (int(origin[0]), int(origin[1])), now)
        self.timeline.after(HOP_SECONDS, lambda i=item_id, s=outcome.slot, n=outcome.count: self._landed(i, s, n))
        self.audio.play("pop")
        self.controls.sync(station)
        self._dirty = True

    def _landed(self, item_id: int, slot: int, count: int) -> None:
        if self.station.item(item_id).slot != slot:
            return  # sent back before it landed
        now = self.clock()
        self.motion.pops[item_id] = now
        self.motion.badges[slot] = (now, count)
        self.audio.chime(count)
        self.audio.say_number(count)
        self._dirty = True

    def _on_wagon(self, wagon: int) -> None:
        station = self.station
        outcome = station.unload(wagon)
        if outcome.result is not MoveResult.MOVED:
            return
        self._activated = True
        now = self.clock()
        item = station.item(outcome.item_id)
        self.motion.clear_marks()
        self.motion.badges.pop(outcome.slot, None)
        self.motion.hops[item.item_id] = Hop(now, (item.x, item.y), outcome.slot, False)
        self.timeline.after(HOP_SECONDS, lambda i=item.item_id: self._settled(i))
        self.audio.play("unload")
        self.controls.sync(station)
        self._dirty = True

    def _settled(self, item_id: int) -> None:
        self.motion.pops[item_id] = self.clock()
        self._dirty = True

    def _on_sign(self) -> None:
        """Tapping the board replays the order (once at a time)."""

        if self.station.phase is not Phase.LOADING or self.clock() < self._order_until:
            return
        self._activated = True
        self._present_order()

    def _on_go(self) -> None:
        station = self.station
        result = station.go()
        if result is GoResult.IGNORED:
            return
        self._activated = True
        self.timeline.clear()
        self.controls.sync(station)
        self.motion.clear_marks()
        if result is GoResult.CORRECT:
            self._celebrate()
        else:
            self._demonstrate(result)
        self._dirty = True

    def _celebrate(self) -> None:
        """Right load: cheer, count the load out once more, then depart."""

        station = self.station
        now = self.clock()
        self.cast.correct()
        self.motion.add_fx("check_pop", GO_CENTER, now)
        # Celebrate around the train, never over the numeral being taught.
        self.motion.add_fx("star_burst", (LOCO_X + 110, LOCO_TOP + 60), now)
        for wagon in station.child_wagons:
            x, y = slot_position(wagon * WAGON_WELLS + 2)
            self.motion.add_fx("confetti", (x, y - 150), now)
        cue = PRAISE_CUES[self._praise_index % len(PRAISE_CUES)]
        self._praise_index += 1
        self.audio.say(cue)
        filled = station.filled_slots()
        for position, slot in enumerate(filled):
            self.timeline.after(
                0.2 + CLOSE_STEP_SECONDS * position, lambda s=slot, n=position + 1: self._pulse_slot(s, n)
            )
        self.timeline.after(0.5 + CLOSE_STEP_SECONDS * len(filled), self._depart)

    def _depart(self) -> None:
        self.audio.play("whistle")
        self.audio.then("all_aboard")  # after the praise
        self._set_drive(Drive.DEPARTING)
        self._dirty = True

    def _demonstrate(self, result: GoResult) -> None:
        """Try again: think pose, recount the load, show extra or missing places."""

        station = self.station
        child_wagon = 1 if station.task is TaskKind.SAME else (station.filled_slots()[-1] // WAGON_WELLS)
        self.motion.wobble = (child_wagon, self.clock())
        self.cast.try_again()
        self.audio.play("creak")
        reason = "too_many" if result is GoResult.TOO_MANY else "not_enough"
        lead = RETRY_LEAD_SECONDS
        if self.audio.has_speech(reason):
            # The reason, then "let's count again"; the recount waits for both.
            self.audio.say(reason, then="count_again")
            lead = max(lead, self.audio.length(reason) + self.audio.length("count_again") + 0.15)
        else:
            self.audio.say("retry")
        if station.task is TaskKind.SAME:
            # One-to-one: each order cargo is matched with one of the child's.
            pairs = min(station.order, station.loaded)
            for index in range(pairs):
                self.timeline.after(lead + RECOUNT_STEP_SECONDS * index, lambda i=index: self._pulse_pair(i))
            total = lead + RECOUNT_STEP_SECONDS * pairs
        else:
            filled = station.filled_slots()
            for position, slot in enumerate(filled):
                self.timeline.after(
                    lead + RECOUNT_STEP_SECONDS * position,
                    lambda s=slot, n=position + 1: self._pulse_slot(s, n, voiced=True),
                )
            total = lead + RECOUNT_STEP_SECONDS * len(filled)
        self.timeline.after(total + 0.15, self._show_marks)
        self.timeline.after(total + 0.15 + MARK_HOLD_SECONDS, self._finish_demo)

    def _pulse_slot(self, slot: int, number: int, *, voiced: bool = False) -> None:
        item = self.station.item_in_slot(slot)
        now = self.clock()
        if item is not None:
            self.motion.pops[item.item_id] = now
        self.motion.badges[slot] = (now, number)
        self.audio.chime(number)
        if voiced:
            self.audio.say_number(number)
        self._dirty = True

    def _pulse_pair(self, index: int) -> None:
        now = self.clock()
        self.motion.pairs = index + 1
        self.motion.marks_started = now
        for slot in (index, WAGON_WELLS + index):
            item = self.station.item_in_slot(slot)
            if item is not None:
                self.motion.pops[item.item_id] = now
        self.audio.chime(index + 1)
        self._dirty = True

    def _show_marks(self) -> None:
        station = self.station
        self.motion.extra_slots = tuple(station.extra_slots())
        self.motion.missing_slots = tuple(station.missing_slots())
        if station.task is TaskKind.SAME:
            self.motion.pairs = min(station.order, station.loaded)
        self.motion.marks_started = self.clock()
        self.motion.sign_hop = self.clock()
        self.audio.play("boop")
        self._dirty = True

    def _finish_demo(self) -> None:
        station = self.station
        station.finish_demonstration()
        # Marks stay a moment longer (they fade on their own) while play resumes.
        self.controls.sync(station, refocus=True)
        self._note_activity()
        self._dirty = True

    def _finish_station(self) -> None:
        index = self.journey.completed + 1
        summary = self.journey.finish_station()
        self.events.station_completed(self._journey_id, index, summary)
        self.progress.save(self.journey.progress)
        self.controls.set_progress(self.journey.completed)
        if self.journey.complete:
            self._complete_journey()
            return
        self.journey.next_station()
        self._start_station()

    def _complete_journey(self) -> None:
        self.journey.progress.journeys_completed += 1
        self.progress.save(self.journey.progress)
        self.events.journey_completed(self._journey_id, self.journey.completed, self.journey.stage)
        self.timeline.clear()
        self.audio.play("fanfare")
        self.audio.say("celebrate")
        self.completion.prepare(
            CompletionContent(
                title=self.resources.text("victory.title"),
                primary_label=self.resources.text("button.play_again"),
                achievement_count=self.journey.total_stations,
            )
        )
        self._surfaces.push_overlay(CompletionOverlay(self.completion, on_primary=self._restart))
        self.state = AppState.TERMINAL
        self._dirty = True

    def _restart(self) -> None:
        """One restart transaction regardless of keyboard/controller/pointer input."""

        self._activated = True
        self._surfaces.pop_overlay()
        self.completion.clear()
        self._journey_id = uuid4().hex
        self.journey.restart()
        self.state = AppState.PLAYING
        self._first_station = True
        self._start_station()

    # -- hints ------------------------------------------------------------------------

    def _maybe_hint(self, now: float) -> None:
        station = self.station
        if station.phase is not Phase.LOADING or self.timeline.busy or self._drive is not Drive.STOPPED:
            return
        step = self._hints.poll(now, self._last_activity)
        if not step:
            return
        if step == 1:
            station.note_hint()
            self._present_order()
        else:
            self.cast.point(self._hints.animation_seconds(1.8))
            waiting = station.next_platform_item()
            if station.loaded == 0 and waiting is not None:
                for beat in range(3):
                    self.timeline.after(beat * 0.5, lambda item=waiting: self._hint_pulse(item))
            else:
                # When to send the train is the child's decision: the cue is the
                # same whether the load is right or not.
                for beat in range(2):
                    self.timeline.after(beat * 0.5, lambda: self.motion.add_fx("sparkle", GO_CENTER, self.clock()))
        self._dirty = True

    def _hint_pulse(self, item: Cargo) -> None:
        if not item.on_platform:
            return
        now = self.clock()
        self.motion.pops[item.item_id] = now
        self.motion.add_fx("sparkle", (int(item.x), int(item.y)), now)
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


__all__ = ["AppState", "Drive", "Timeline", "TrenoApp"]
