"""Lifecycle, scripted moments and shared-kit input for La Casa del Dieci.

One visit is six challenges on Dani's ten-frame house. Every operation is
acted out on the house: the child lights rooms in ten-frame order, brings
guest fireflies in, watches fireflies fly home, or sends the number of
fireflies they think is missing. There is no lit/target counter and no
printed sum while a challenge is open; answers are near misses (+-1/+-2).

Feedback follows ADR 0037: correct = Dani ``pose_cheer`` + twinkling rooms,
a chimney heart and the number-bond strip ("5 + 2 = 7", coloured like the
rooms); try again = Dani ``pose_think`` + a kind line + a counting
demonstration on the house, with unlimited retries. Hints are graduated
(~6 s idle -> Dani points and the house pulses; again -> the prompt replays).
The visit ends on the shared cast completion scene.
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
    from .ten_house_art import TenHouseArt, Tone
    from .ten_house_audio import TenHouseAudio
    from .ten_house_controls import TenHouseControls
    from .ten_house_layout import (
        CHIMNEY_TOP,
        DANI_HEIGHT,
        FIREFLY_IN_ROOM,
        GUEST_SLOTS,
        OFFSTAGE_RIGHT,
        SIGN_RECT,
        SKY_SLOTS,
    )
    from .ten_house_model import (
        CHALLENGE_COUNT,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        ROOM_COUNT,
        OperationMode,
        Phase,
        RoomChange,
        RoomState,
        TenHouseRoundFactory,
        TenHouseSession,
        adapt_level,
    )
    from .ten_house_renderer import BADGE_HOLD_SECONDS, BondItem, Flight, HouseMotion, TenHouseCast, TenHouseRenderer
    from .ten_house_services import EventPort, ProgressPort
else:
    from ten_house_art import TenHouseArt, Tone
    from ten_house_audio import TenHouseAudio
    from ten_house_controls import TenHouseControls
    from ten_house_layout import (
        CHIMNEY_TOP,
        DANI_HEIGHT,
        FIREFLY_IN_ROOM,
        GUEST_SLOTS,
        OFFSTAGE_RIGHT,
        SIGN_RECT,
        SKY_SLOTS,
    )
    from ten_house_model import (
        CHALLENGE_COUNT,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        ROOM_COUNT,
        OperationMode,
        Phase,
        RoomChange,
        RoomState,
        TenHouseRoundFactory,
        TenHouseSession,
        adapt_level,
    )
    from ten_house_renderer import BADGE_HOLD_SECONDS, BondItem, Flight, HouseMotion, TenHouseCast, TenHouseRenderer
    from ten_house_services import EventPort, ProgressPort

POP_LEAD = 0.25
POP_STAGGER = 0.12
FLIGHT = 0.62
LEAVE_LEAD = 0.9
LEAVE_STAGGER = 0.8
TRIAL_STAGGER = 0.22
TRIAL_HOLD = 0.6
COUNT_LEAD = 0.9
COUNT_STEP = 0.42
THINK_SECONDS = 1.6
TWINKLE_STEP = 0.07
CELEBRATE_HOLD = 2.8
SWEEP_STEP = 0.22
MAX_SCHEDULED = 64
NIGHT = (37, 59, 89)  # theme token "navy" behind the completion card

_PROMPTS = {
    OperationMode.ADD: "prompt_add",
    OperationMode.TAKE_AWAY: "prompt_take_away",
    OperationMode.MISSING_PART: "prompt_missing_part",
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


class TenHouseActivity:
    """Coordinate the ten-frame model, shared-kit controls, art and lifecycle."""

    def __init__(
        self,
        *,
        screen: pygame.Surface,
        canvas: PygameReferenceCanvas,
        session: TenHouseSession,
        factory: TenHouseRoundFactory,
        typography: GreiaTypography,
        resources: LocalizedResources,
        progress: ProgressPort,
        events: EventPort,
        audio: TenHouseAudio,
        rng: random.Random,
        session_id: str,
        clock: Callable[[], float] = time.monotonic,
        kit: ControlKit | None = None,
        art: TenHouseArt | None = None,
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

        # Shared control kit (ADR 0037): learn Collection -> orange accent.
        self.kit = kit if kit is not None else ControlKit(typography, ControlTheme.for_accent("orange"))
        self.art = art if art is not None else TenHouseArt(self.kit.painter)
        feedback = CastFeedback("dani", height=DANI_HEIGHT, art=self.kit.art, clock=clock)
        self.cast = TenHouseCast(feedback, self.art.cast_pose("dani", "pose_point", DANI_HEIGHT), clock)
        self.renderer = TenHouseRenderer(self.art, self.cast, clock=clock)
        self.motion = HouseMotion()
        self.timeline = Timeline(clock)
        self.controls = TenHouseControls(
            self.kit,
            self.art,
            ControlLayout.for_canvas(canvas, screen.get_size()),
            on_room=self._on_room,
            on_guest=self._on_guest,
            on_choice=self._on_choice,
            on_confirm=self._on_confirm,
            on_replay=self._on_listen,
        )
        self._surfaces = SurfaceNavigator(self.controls.layer)
        self._input = PygameControlInput(to_logical=canvas.pointer, is_safe=lambda pos: _safe_point(self.screen, pos))
        self.completion = PygameCompletionScreen(
            typography,
            width=REFERENCE_WIDTH,
            height=REFERENCE_HEIGHT,
            palette=CompletionPalette(background=NIGHT),
            scene=CompletionScene(self.kit, character="dani", star_total=CHALLENGE_COUNT),
        )
        self.state = AppState.PLAYING
        self._running = True
        self._ready_published = False
        self._dirty = True
        self._activated = False
        self._busy = False
        self._last_activity = clock()
        self._hints = IdleHintScheduler(now=self._last_activity)
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
            if self.state is AppState.PLAYING:
                self.progress.save(self.session.level, self.session.history)
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
        return self.motion.active(now) or self.cast.animating

    def render(self) -> None:
        surface = self.canvas.surface
        if self.state is AppState.PLAYING:
            self.renderer.draw(surface, self.session, self.motion)
            self._draw_controls(surface)
        else:
            self._surfaces.draw(surface)

    def _draw_controls(self, surface: pygame.Surface) -> None:
        """Draw kit controls; a rejected answer shakes briefly."""

        started = self.motion.wobble_started
        shaking = self.controls.wobble_target(self.motion.wobble_id)
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

    # -- round flow ---------------------------------------------------------------

    def _start_round(self) -> None:
        challenge = self.session.current_challenge
        assert challenge is not None
        now = self.clock()
        self.timeline.clear()
        self.motion.clear()
        self.cast.reset()
        # The given part switches on room by room, in ten-frame order.
        for room in range(self.session.lit):
            delay = POP_LEAD + POP_STAGGER * room
            self.motion.arrivals[room] = now + delay
            self.motion.add_fx("sparkle", FIREFLY_IN_ROOM[room], now + delay)
            self.timeline.after(delay, lambda n=room + 1: self.audio.chime(n))
        intro = POP_LEAD + POP_STAGGER * self.session.lit + 0.25
        if challenge.mode is OperationMode.ADD:
            self.motion.waiting = list(range(challenge.delta))
            for slot in self.motion.waiting:
                self.motion.add_fx("sparkle", GUEST_SLOTS[slot], now + intro)
            self.timeline.after(intro, lambda: self._guest_cue())
        elif challenge.mode is OperationMode.TAKE_AWAY:
            # "Some fireflies are flying home!" ends before the question.
            self.timeline.after(intro, lambda: self.audio.say("fireflies_home"))
            for order in range(challenge.delta):
                self.timeline.after(intro + LEAVE_LEAD + LEAVE_STAGGER * order, self._depart)
            self.timeline.after(intro + LEAVE_LEAD + LEAVE_STAGGER * challenge.delta + 0.2, self._begin_asking)
        else:
            self.audio.say(self._prompt_cue())
            self.cast.point(1.8)
        if challenge.mode is OperationMode.TAKE_AWAY:
            self._set_busy(None)  # until the last firefly has flown home
        elif self.session.lit or challenge.mode is OperationMode.ADD:
            self._set_busy(intro)  # let the given part / the guests appear first
        else:
            self._busy = False
            self._sync(refocus=True)
        self._note_activity()
        self._dirty = True

    def _prompt_cue(self) -> str | None:
        challenge = self.session.current_challenge
        if challenge is None:
            return None
        if challenge.mode is OperationMode.COMPOSE:
            return f"prompt_compose_{challenge.target}"
        if challenge.mode is OperationMode.ADD and self.session.phase is Phase.ARRIVING:
            return "friends_coming"  # "Some friends are coming! Bring them in."
        return _PROMPTS.get(challenge.mode)

    def _guest_cue(self) -> None:
        self.cast.point(2.0)
        self.motion.guest_pulse = self.clock()
        cue = self._prompt_cue()
        if cue is not None:
            self.audio.say(cue)
        self.audio.play("pop")
        self._dirty = True

    def _set_busy(self, seconds: float | None) -> None:
        """Lock gameplay input for a scripted moment (``None``: until unlocked)."""

        self._busy = True
        self._sync()
        if seconds is not None:
            self.timeline.after(seconds, self._end_busy)

    def _end_busy(self) -> None:
        self._busy = False
        self._note_activity()
        self._sync(refocus=True)
        self._dirty = True

    def _sync(self, *, refocus: bool = False) -> None:
        self.controls.sync(self.session, waiting=self.motion.waiting, busy=self._busy, refocus=refocus)

    # -- gameplay callbacks ----------------------------------------------------------

    def _on_room(self, index: int) -> None:
        if self._busy:
            return
        if self.session.phase is Phase.ARRIVING:
            # A dark window calls the next guest in (the same flight as a guest tap).
            if index >= self.session.lit and self.motion.waiting:
                self._on_guest(self.motion.waiting[0])
            return
        change = self.session.tap_room(index)
        now = self.clock()
        if change is RoomChange.LIT:
            room = self.session.lit - 1
            self.motion.add_fx("sparkle", FIREFLY_IN_ROOM[room], now)
            self.audio.play("pop")
        elif change is RoomChange.UNLIT:
            room = self.session.lit
            self.motion.fly(Flight(now, FIREFLY_IN_ROOM[room], (FIREFLY_IN_ROOM[room][0], -40), duration=0.5, lift=0.0))
            self.audio.play("unpop")
        else:
            return
        self._activated = True
        self._sync()
        self._dirty = True

    def _on_guest(self, slot: int) -> None:
        if self._busy or slot not in self.motion.waiting:
            return
        if not self.session.invite_guest():
            return
        self._activated = True
        now = self.clock()
        self.motion.waiting.remove(slot)
        room = self.session.lit - 1
        self.motion.fly(Flight(now, GUEST_SLOTS[slot], FIREFLY_IN_ROOM[room]))
        self.motion.arrivals[room] = now + FLIGHT
        self.motion.add_fx("sparkle", FIREFLY_IN_ROOM[room], now + FLIGHT)
        self.audio.play("whoosh")
        self.timeline.after(FLIGHT, lambda: self.audio.play("pop"))
        if self.session.phase is Phase.ASKING:
            self._set_busy(None)
            self.timeline.after(FLIGHT + 0.45, self._begin_asking)
        else:
            self._sync()
        self._dirty = True

    def _depart(self) -> None:
        room = self.session.lit - 1
        if not self.session.depart_one():
            return
        now = self.clock()
        slot = min(self.motion.sky, len(SKY_SLOTS) - 1)
        self.motion.fly(Flight(now, FIREFLY_IN_ROOM[room], SKY_SLOTS[slot], duration=FLIGHT * 1.6, lift=110.0))
        self.motion.sky_since[self.motion.sky] = now + FLIGHT * 1.6
        self.motion.sky += 1
        self.audio.play("whoosh")
        self._dirty = True

    def _begin_asking(self) -> None:
        cue = self._prompt_cue()
        if cue is not None:
            self.audio.say(cue)
        self.cast.point(1.6)
        self._busy = False
        self._note_activity()
        self._sync(refocus=True)
        self._dirty = True

    def _on_confirm(self) -> None:
        if self._busy or self.session.phase is not Phase.BUILD:
            return
        self._activated = True
        result = self.session.confirm()
        if result.correct:
            self._celebrate(0.0)
            return
        self._try_again(self.controls.confirm.control_id)
        lit = self.session.lit
        rooms = [(room, room + 1, self._tone(room)) for room in range(lit)]
        duration = self._count(rooms, COUNT_LEAD)
        self.timeline.after(duration + 0.1, self._pulse_sign)
        self._set_busy(duration + 0.6)

    def _on_choice(self, index: int) -> None:
        if self._busy or self.session.phase is not Phase.ASKING:
            return
        value = self.controls.choice_value(index)
        challenge = self.session.current_challenge
        if value is None or challenge is None or value in self.session.rejected:
            return
        self._activated = True
        lit_before = self.session.lit
        result = self.session.choose(value)
        if challenge.mode is OperationMode.MISSING_PART:
            self._try_out(value, lit_before, result.correct, self.controls.choices[index].control_id)
            return
        if result.correct:
            self._celebrate(0.0)
            return
        self._try_again(self.controls.choices[index].control_id)
        self._set_busy(self._demonstrate(challenge.mode) + 0.5)

    def _try_out(self, value: int, lit_before: int, correct: bool, control_id: str) -> None:
        """"How many more?": the chosen number of fireflies try to move in."""

        now = self.clock()
        self._busy = True
        self._sync()
        for order in range(value):
            start = now + TRIAL_STAGGER * order
            room = lit_before + order
            if room < ROOM_COUNT:
                dest = FIREFLY_IN_ROOM[room]
                if correct:
                    self.motion.arrivals[room] = start + FLIGHT
                else:
                    self.motion.trial[room] = start + FLIGHT
            else:  # no room left in the house: it waits outside
                dest = GUEST_SLOTS[(room - ROOM_COUNT) % len(GUEST_SLOTS)]
                self.motion.outside.append((start + FLIGHT, dest))
            self.motion.fly(Flight(start, OFFSTAGE_RIGHT, dest))
            self.timeline.after(TRIAL_STAGGER * order + FLIGHT, lambda n=room + 1: self.audio.chime(min(n, 10)))
        landed = TRIAL_STAGGER * max(0, value - 1) + FLIGHT
        if correct:
            self._celebrate(landed)
            return
        self.timeline.after(landed + TRIAL_HOLD, lambda: self._end_try_out(control_id))
        self._dirty = True

    def _end_try_out(self, control_id: str) -> None:
        now = self.clock()
        self._try_again(control_id)
        for room in sorted(self.motion.trial):
            self.motion.fly(Flight(now, FIREFLY_IN_ROOM[room], OFFSTAGE_RIGHT, duration=FLIGHT * 1.2))
        for _, position in self.motion.outside:
            self.motion.fly(Flight(now, position, OFFSTAGE_RIGHT, duration=FLIGHT * 1.2))
        self.motion.trial.clear()
        self.motion.outside.clear()
        challenge = self.session.current_challenge
        assert challenge is not None
        self._set_busy(self._demonstrate(challenge.mode) + 0.5)

    def _try_again(self, control_id: str) -> None:
        self.motion.wobble_id = control_id
        self.motion.wobble_started = self.clock()
        self.cast.try_again()
        self.audio.play("boop")
        self.audio.encourage()
        # After thinking, Dani points at the house while the counting plays.
        self.timeline.after(THINK_SECONDS, lambda: self.cast.point(3.0))
        self._dirty = True

    def _demonstrate(self, mode: OperationMode) -> float:
        """Count with Dani on the house; returns the duration."""

        # Once the try-again line is over, Dani invites the child to count
        # along ("Count the lights with me!"); never spoken over another line.
        self.timeline.after(THINK_SECONDS, lambda: self.audio.say_if_quiet("count_lights"))
        session = self.session
        challenge = session.current_challenge
        assert challenge is not None
        if mode is OperationMode.ADD:
            # Count on: the first part at once, then each guest.
            given = session.given
            rooms = [(given - 1, given, Tone.HOME)] if given else []
            rooms += [(room, room + 1, Tone.GUEST) for room in range(given, session.lit)]
        elif mode is OperationMode.MISSING_PART:
            rooms = [(room, room - session.lit + 1, Tone.GUEST) for room in range(session.lit, challenge.target)]
            for order, (room, _, _) in enumerate(rooms):
                self.motion.halos[room] = self.clock() + COUNT_LEAD + COUNT_STEP * order
            self.timeline.after(COUNT_LEAD + COUNT_STEP * len(rooms), self._pulse_sign)
        else:
            rooms = [(room, room + 1, self._tone(room)) for room in range(session.lit)]
        return self._count(rooms, COUNT_LEAD)

    def _count(self, rooms: list[tuple[int, int, Tone]], lead: float) -> float:
        now = self.clock()
        total = lead + COUNT_STEP * len(rooms)
        for order, (room, number, tone) in enumerate(rooms):
            delay = lead + COUNT_STEP * order
            # Badges stay up until the count is complete, so 1..N read together.
            self.motion.badges[room] = (now + delay, now + total + BADGE_HOLD_SECONDS, number, tone)
            self.timeline.after(delay, lambda n=number: self.audio.chime(n))
        return total

    def _tone(self, room: int) -> Tone:
        return Tone.GUEST if self.session.room_state(room) is RoomState.GUEST else Tone.HOME

    def _pulse_sign(self) -> None:
        self.motion.sign_pulse = self.clock()
        self.motion.add_fx("sparkle", SIGN_RECT.center, self.clock())
        self._dirty = True

    # -- success ---------------------------------------------------------------------

    def _celebrate(self, lead: float) -> None:
        session = self.session
        challenge = session.current_challenge
        assert challenge is not None
        now = self.clock()
        self._busy = True
        self._sync()
        milestone = session.consume_milestone()
        if milestone is not None:
            self.events.room_completed(self.session_id, milestone)
        for room in range(session.lit):
            at = now + lead + 0.2 + TWINKLE_STEP * room
            self.motion.add_fx("sparkle", FIREFLY_IN_ROOM[room], at)
        self.timeline.after(lead + 0.2, lambda: self.audio.play("fanfare"))
        reveal = lead + 0.35 + TWINKLE_STEP * session.lit
        self.motion.sign_number = challenge.answer if challenge.mode is not OperationMode.MISSING_PART else challenge.target
        self.motion.sign_pulse = now + reveal
        self.motion.bond = _bond_items(challenge)
        self.motion.bond_started = now + reveal
        self.motion.add_fx("heart_pop", (CHIMNEY_TOP[0] - 4, CHIMNEY_TOP[1] + 30), now + reveal)
        self.motion.add_fx("star_burst", (SIGN_RECT.left - 70, SIGN_RECT.centery + 14), now + reveal)
        self.motion.add_fx("star_burst", (SIGN_RECT.right + 70, SIGN_RECT.centery + 14), now + reveal)
        self.timeline.after(lead, self._cheer)
        self.timeline.after(reveal + CELEBRATE_HOLD, self._finish_round)
        self._dirty = True

    def _cheer(self) -> None:
        self.cast.correct()
        self.audio.praise()
        self._sync()
        self._dirty = True

    def _finish_round(self) -> None:
        if self.session.challenge_index + 1 >= CHALLENGE_COUNT:
            self._complete_session()
            return
        self.session.advance()
        self._busy = False
        self._start_round()

    def _complete_session(self) -> None:
        payload = self.session.consume_completion()
        if payload is not None:
            next_level = adapt_level(self.session.level, self.session.history)
            self.progress.save(next_level, self.session.history)
            self.events.house_completed(self.session_id, payload)
        self.timeline.clear()
        self.audio.say("complete")
        self.completion.prepare(
            CompletionContent(
                title=self.resources.text("victory.title"),
                primary_label=self.resources.text("button.play_again"),
                body_lines=(self.resources.text("victory.subtitle"),),
                achievement_count=CHALLENGE_COUNT,
            )
        )
        self._surfaces.push_overlay(CompletionOverlay(self.completion, on_primary=self._restart))
        self.controls.progress.set_progress(CHALLENGE_COUNT)
        self.state = AppState.TERMINAL
        self._dirty = True

    def _restart(self) -> None:
        self._activated = True
        next_level = adapt_level(self.session.level, self.session.history)
        self.session = TenHouseSession(
            self.factory.build_set(next_level), level=next_level, history=self.session.history
        )
        self.session_id = f"{self.session_id.rsplit('-', 1)[0]}-{self.rng.randrange(1_000_000):06d}"
        self._surfaces.pop_overlay()
        self.completion.clear()
        self.state = AppState.PLAYING
        self._busy = False
        self._start_round()

    # -- hints ------------------------------------------------------------------------

    def _maybe_hint(self, now: float) -> None:
        phase = self.session.phase
        if self._busy or self.timeline.busy or phase in {Phase.SOLVED, Phase.LEAVING}:
            return
        step = self._hints.poll(now, self._last_activity)
        if not step:
            return
        if step == 1:
            self.session.note_hint()
        self.cast.point(self._hints.animation_seconds(1.8))
        challenge = self.session.current_challenge
        assert challenge is not None
        if phase is Phase.ARRIVING:
            self.motion.guest_pulse = now
        elif phase is Phase.BUILD:
            # Look at the sign, then at the house again (silent: no numbers).
            self.motion.sign_pulse = now
            self._sweep(range(max(1, self.session.lit)))
        elif challenge.mode is OperationMode.MISSING_PART:
            self._sweep(range(self.session.lit, challenge.target))
        else:
            self._sweep(range(self.session.lit))
        if step >= 2:
            cue = self._prompt_cue()
            if cue is not None:
                self.audio.say(cue)
        self._dirty = True

    def _sweep(self, rooms) -> None:
        now = self.clock()
        for order, room in enumerate(rooms):
            self.motion.halos[room] = now + SWEEP_STEP * order

    def _on_listen(self) -> None:
        self._activated = True
        cue = self._prompt_cue()
        if cue is not None:
            self.audio.say(cue)
        elif self.session.phase is Phase.ARRIVING:
            self.motion.guest_pulse = self.clock()
        self.cast.point(1.4)
        self._dirty = True


def _bond_items(challenge) -> tuple[BondItem, ...]:
    """Number-bond strip for a solved challenge, coloured like its rooms."""

    mode = challenge.mode
    if mode is OperationMode.COMPOSE and challenge.starting_lit == 0:
        return (BondItem(str(challenge.target), Tone.HOME),)
    if mode is OperationMode.TAKE_AWAY:
        return (
            BondItem(str(challenge.starting_lit), Tone.HOME),
            BondItem("-"),
            BondItem(str(challenge.delta), Tone.AWAY),
            BondItem("="),
            BondItem(str(challenge.answer), Tone.HOME),
        )
    first = challenge.starting_lit
    whole = challenge.target
    return (
        BondItem(str(first), Tone.HOME),
        BondItem("+"),
        BondItem(str(whole - first), Tone.GUEST),
        BondItem("="),
        BondItem(str(whole), Tone.WHOLE),
    )


def _safe_point(surface: pygame.Surface, position: tuple[int, int]) -> bool:
    viewport = activity_viewport_for_surface(surface)
    x, y = position
    if not (0 <= x < viewport.surface.width and 0 <= y < viewport.surface.height):
        return False
    for protected in viewport.protected_regions:
        if protected.x <= x < protected.right and protected.y <= y < protected.bottom:
            return False
    return True


__all__ = ["AppState", "TenHouseActivity", "Timeline"]
