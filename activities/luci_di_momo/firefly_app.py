"""Lifecycle, scripted moments and shared-kit input for Luci di Momo.

One visit is six glimpses. In each, Momo points at the night air ("watch!"),
a few fireflies glow all at once for about 1.5 s and go dark, and the child
says how many they saw by choosing one of three number cards (near misses
only). There is no Play button between rounds and nothing on screen reveals
the amount while the cards are open.

Feedback follows ADR 0037: correct = Momo ``pose_cheer``, "three fireflies!"
(or praise above five), sparkles, then the fireflies glide into Momo's jar
and one more light glows there; try again = Momo ``pose_think`` + a kind line,
the fireflies come back and stay, and Momo counts them together (a whole
group or row at once, then counting on), with unlimited retries. Hints are
graduated (~6 s idle -> Momo points and "look again" glows; again -> the
question replays). "Look again" re-shows the glimpse once per round and
counts as a hint. A full jar ends the visit with fireworks and the shared
cast completion scene.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from enum import StrEnum
import random
import time

import pygame

from greia_platform.activity_api import activity_stop_requested, mark_activity_ready
from greia_platform.activity_controls import (
    ControlKit,
    ControlLayout,
    ControlTheme,
    KitPointer,
    PointerPhase,
    PygameControlInput,
)
from greia_platform.activity_feedback import CastFeedback, CastPose
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
    from .firefly_art import FireflyArt
    from .firefly_audio import FireflyAudio
    from .firefly_controls import FireflyControls
    from .firefly_layout import JAR_MOUTH, JAR_SLOTS, MOMO_HEIGHT, MOMO_MIDBOTTOM
    from .firefly_model import (
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        ROUND_COUNT,
        FIELD_CENTER,
        FireflyRound,
        FireflyRoundFactory,
        FireflySession,
        adapt_level,
    )
    from .firefly_renderer import Badge, FieldMotion, FireflyRenderer, Flight, MomoCast
    from .firefly_services import EventPort, ProgressPort
else:
    from firefly_art import FireflyArt
    from firefly_audio import FireflyAudio
    from firefly_controls import FireflyControls
    from firefly_layout import JAR_MOUTH, JAR_SLOTS, MOMO_HEIGHT, MOMO_MIDBOTTOM
    from firefly_model import (
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        ROUND_COUNT,
        FIELD_CENTER,
        FireflyRound,
        FireflyRoundFactory,
        FireflySession,
        adapt_level,
    )
    from firefly_renderer import Badge, FieldMotion, FireflyRenderer, Flight, MomoCast
    from firefly_services import EventPort, ProgressPort

IDLE_HINT_SECONDS = 6.0
FIRST_LEAD_MAX = 7.5
ROUND_LEAD = 0.5
CUE = 0.9
REPLAY_CUE = 0.5
ASK_AFTER_BLINK = 0.25
SPOKEN_PROMPT_ROUNDS = 2
THINK_SECONDS = 1.4
COUNT_STEP = 0.45
CELEBRATE_HOLD = 1.3
FLIGHT_STAGGER = 0.06
FLIGHT = 0.7
NEXT_AFTER_LIGHT = 0.7
FINALE_SECONDS = 2.6
MAX_SCHEDULED = 48
NIGHT = (37, 59, 89)  # theme token "navy" behind the completion card
MOMO_TAP_RECT = pygame.Rect(MOMO_MIDBOTTOM[0] - 70, MOMO_MIDBOTTOM[1] - MOMO_HEIGHT + 30, 140, MOMO_HEIGHT - 40)
FIREWORKS = ((480, 120), (720, 90), (900, 150))


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


class FireflyActivity:
    """Coordinate the subitizing model, shared-kit controls, art and lifecycle."""

    def __init__(
        self,
        *,
        screen: pygame.Surface,
        canvas: PygameReferenceCanvas,
        session: FireflySession,
        factory: FireflyRoundFactory,
        typography: GreiaTypography,
        resources: LocalizedResources,
        progress: ProgressPort,
        events: EventPort,
        audio: FireflyAudio,
        rng: random.Random,
        session_id: str,
        clock: Callable[[], float] = time.monotonic,
        kit: ControlKit | None = None,
        art: FireflyArt | None = None,
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
        self.art = art if art is not None else FireflyArt(self.kit.painter)
        feedback = CastFeedback("momo", height=MOMO_HEIGHT, art=self.kit.art, clock=clock)
        self.cast = MomoCast(feedback, self.art.cast_pose("momo", "pose_point", MOMO_HEIGHT), clock)
        self.renderer = FireflyRenderer(self.art, self.cast, clock=clock)
        self.motion = FieldMotion()
        self.timeline = Timeline(clock)
        self.controls = FireflyControls(
            self.kit,
            self.art,
            ControlLayout.for_canvas(canvas, screen.get_size()),
            on_choice=self._on_choice,
            on_replay=self._on_replay,
            on_listen=self._on_listen,
        )
        self._surfaces = SurfaceNavigator(self.controls.layer)
        self._input = PygameControlInput(to_logical=canvas.pointer, is_safe=lambda pos: _safe_point(self.screen, pos))
        self.completion = PygameCompletionScreen(
            typography,
            width=REFERENCE_WIDTH,
            height=REFERENCE_HEIGHT,
            palette=CompletionPalette(background=NIGHT),
            scene=CompletionScene(self.kit, character="momo", star_total=ROUND_COUNT),
        )
        self.state = AppState.PLAYING
        self.asking = False
        self._busy = False
        self._running = True
        self._ready_published = False
        self._dirty = True
        self._activated = False
        self._last_activity = clock()
        self._idle_hints = 0
        # The first glimpse waits for Momo's welcome ("look closely ...").
        self.audio.play_welcome()
        welcome = min(FIRST_LEAD_MAX, self.audio.speech_seconds("welcome") + 0.3)
        self._start_round(lead=welcome)
        if welcome > ROUND_LEAD:
            self.cast.point(welcome)

    # -- main loop --------------------------------------------------------------

    def run(self) -> int:
        ticker = pygame.time.Clock()
        try:
            while self._running and not activity_stop_requested():
                for event in pygame.event.get():
                    self._handle_event(event)
                repeat = self._input.poll()
                if repeat is not None:
                    self._dispatch(repeat)
                animating = self.step()
                if self._dirty or animating:
                    self.render()
                    self.canvas.present()
                    pygame.display.flip()
                    self._dirty = False
                    if not self._ready_published:
                        mark_activity_ready()
                        self._ready_published = True
                ticker.tick(30 if animating else 15)
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
        # Momo's still pointing pose needs no redraws; its end is reported by update().
        return self.motion.active(now) or self.cast.feedback.animating

    def render(self) -> None:
        surface = self.canvas.surface
        if self.state is AppState.PLAYING:
            self.renderer.draw(surface, self.session.current_round, self.motion)
            self.renderer.draw_replay_pulse(surface, self.controls.replay.rect, self.motion)
            self._draw_controls(surface)
        else:
            self._surfaces.draw(surface)

    def _draw_controls(self, surface: pygame.Surface) -> None:
        """Draw kit controls; a declined answer shakes briefly."""

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
        is_pointer = isinstance(kit_input, KitPointer)
        if not is_pointer or kit_input.phase is not PointerPhase.MOVE:
            self._note_activity()
        result = self._surfaces.dispatch(kit_input)
        if (
            result is UiEventResult.IGNORED
            and is_pointer
            and kit_input.phase is PointerPhase.DOWN
            and self.state is AppState.PLAYING
            and MOMO_TAP_RECT.collidepoint(kit_input.position)
        ):
            # Tapping Momo repeats what she asked (pre-reader friendly).
            self._on_listen()
            result = UiEventResult.HANDLED
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
        self._idle_hints = 0

    # -- round flow ---------------------------------------------------------------

    def _start_round(self, *, lead: float = ROUND_LEAD) -> None:
        current = self.session.current_round
        assert current is not None
        self.timeline.clear()
        self.motion.clear_round()
        self.cast.reset()
        self.asking = False
        self._set_busy(True)
        self._glimpse(lead, CUE)
        self._dirty = True

    def _glimpse(self, lead: float, cue: float) -> None:
        """Momo points, the meadow glows "watch here", then the fireflies flash."""

        current = self.session.current_round
        assert current is not None
        now = self.clock()
        self.timeline.after(lead, lambda: self._cue(cue))
        flash = lead + cue
        reveal = current.reveal_ms / 1000.0
        self.motion.show(now + flash, now + flash + reveal)
        self.timeline.after(flash, lambda: self.audio.play("reveal"))
        self.timeline.after(flash + reveal + ASK_AFTER_BLINK, self._begin_asking)

    def _cue(self, seconds: float) -> None:
        self.motion.cue_start = self.clock()
        self.cast.point(seconds + 0.6)
        self._dirty = True

    def _begin_asking(self) -> None:
        self.asking = True
        self._set_busy(False, refocus=True)
        if self.session.round_index < SPOKEN_PROMPT_ROUNDS and not self.session.replay_used:
            self.audio.play_prompt_choose()
        self._note_activity()
        self._dirty = True

    def _set_busy(self, busy: bool, *, refocus: bool = False) -> None:
        self._busy = busy
        self._sync(refocus=refocus)

    def _sync(self, *, refocus: bool = False) -> None:
        self.controls.sync(self.session, asking=self.asking, busy=self._busy, refocus=refocus)

    # -- gameplay callbacks ----------------------------------------------------------

    def _on_choice(self, index: int) -> None:
        if self._busy or not self.asking or self.state is not AppState.PLAYING:
            return
        current = self.session.current_round
        value = self.controls.choice_value(index)
        if current is None or value is None or value in self.session.rejected:
            return
        self._activated = True
        result = self.session.choose(value)
        if result.correct:
            self._celebrate(index, current)
        else:
            self._try_again(self.controls.choices[index].control_id)

    def _on_replay(self) -> None:
        """"Look again": one more glimpse of the same fireflies (a hint)."""

        session = self.session
        if self._busy or not self.asking or session.missed or session.replay_used:
            return
        self._activated = True
        session.mark_replay()
        self.asking = False
        self._set_busy(True)
        self._glimpse(0.15, REPLAY_CUE)
        self._dirty = True

    def _on_listen(self) -> None:
        self._activated = True
        if self.asking:
            self.audio.play_prompt_choose()
        else:
            self.audio.play_welcome()
        if self.cast.pose is CastPose.IDLE:
            self.cast.point(1.4)
        self._dirty = True

    # -- try again: Momo thinks, then counts with the child ------------------------

    def _try_again(self, control_id: str) -> None:
        now = self.clock()
        current = self.session.current_round
        assert current is not None
        self.motion.wobble_id = control_id
        self.motion.wobble_started = now
        self.cast.try_again()
        self.audio.play("retry")
        self.audio.encourage()
        # The fireflies come back and stay while Momo counts them.
        self.motion.show(now + 0.25, None)
        self._set_busy(True)
        self.timeline.after(THINK_SECONDS, self._demonstrate)
        self._dirty = True

    def _demonstrate(self) -> None:
        """Count together: a whole group/row at once, then count on one by one."""

        current = self.session.current_round
        assert current is not None
        self.motion.badges.clear()
        self.motion.halos.clear()
        lead_group = current.lead_group
        steps: list[tuple[int, tuple[int, ...]]] = []
        if lead_group:
            steps.append((lead_group, tuple(range(lead_group))))
        for index in range(lead_group, current.quantity):
            steps.append((index + 1, (index,)))
        duration = 0.2 + COUNT_STEP * len(steps)
        self.cast.point(duration + 0.6)
        for order, (number, members) in enumerate(steps):
            delay = 0.2 + COUNT_STEP * order
            self.timeline.after(delay, lambda n=number, m=members: self._count_step(n, m))
        self.timeline.after(duration + 0.3, self._end_demonstration)

    def _count_step(self, number: int, members: tuple[int, ...]) -> None:
        current = self.session.current_round
        if current is None:
            return
        now = self.clock()
        points = [current.positions[index] for index in members]
        for index in members:
            self.motion.halos[index] = now
        if len(members) > 1:
            x = sum(p[0] for p in points) // len(points)
            y = min(p[1] for p in points) - 20
            self.motion.badge(Badge(now, number, (x, y), group=True))
        else:
            self.motion.badge(Badge(now, number, _badge_anchor(current, members[0])))
        self.audio.chime(number)
        self._dirty = True

    def _end_demonstration(self) -> None:
        self._set_busy(False, refocus=True)
        self._note_activity()
        self._dirty = True

    # -- success: cheer, then the fireflies glide into Momo's jar -------------------

    def _celebrate(self, index: int, solved: FireflyRound) -> None:
        now = self.clock()
        self._busy = True
        self.controls.show_solo(index)
        card = self.controls.choices[index].rect
        self.motion.add_fx("star_burst", card.center, now)
        self.cast.correct()
        self.audio.play("correct")
        if not self.audio.play_count(solved.quantity):
            self.audio.praise()
        if self.motion.shown_from is None or self.motion.hide_at is not None:
            self.motion.show(now, None)
        for order, position in enumerate(solved.positions):
            self.motion.add_fx("sparkle", position, now + 0.1 + 0.05 * order)
        self.timeline.after(CELEBRATE_HOLD, lambda: self._fly_home(solved))
        self._dirty = True

    def _fly_home(self, solved: FireflyRound) -> None:
        now = self.clock()
        self.motion.shown_from = None
        self.motion.hide_at = None
        self.motion.badges.clear()
        self.motion.halos.clear()
        for order, position in enumerate(solved.positions):
            self.motion.fly(Flight(now + FLIGHT_STAGGER * order, position, JAR_MOUTH, duration=FLIGHT))
        landed = FLIGHT_STAGGER * max(0, solved.quantity - 1) + FLIGHT
        self.timeline.after(landed, self._light_up)
        self._dirty = True

    def _light_up(self) -> None:
        now = self.clock()
        self.motion.add_light(now)
        slot = JAR_SLOTS[min(len(JAR_SLOTS), self.motion.jar_lights) - 1]
        self.motion.add_fx("sparkle", slot, now)
        self.audio.play("light")
        self.controls.set_progress(self.session.round_index)
        if self.session.is_complete:
            self.timeline.after(NEXT_AFTER_LIGHT, self._finale)
        else:
            self.timeline.after(NEXT_AFTER_LIGHT, self._start_round)
        self._dirty = True

    def _finale(self) -> None:
        """A full jar lights the valley: fireworks, a cheer, then the card."""

        now = self.clock()
        payload = self.session.consume_completion()
        if payload is not None:
            next_level = adapt_level(self.session.level, self.session.history)
            self.progress.save(next_level, self.session.history)
            self.events.garden_completed(self.session_id, payload)
        self.cast.correct()
        self.controls.show_solo(-1)
        self.audio.play_garden_complete()
        for order, position in enumerate(FIREWORKS):
            self.motion.add_fx("firework", position, now + 0.35 * order)
        self.motion.add_fx("star_burst", JAR_MOUTH, now)
        self.timeline.after(FINALE_SECONDS, self._show_completion)
        self._dirty = True

    def _show_completion(self) -> None:
        self.timeline.clear()
        self.completion.prepare(
            CompletionContent(
                title=self.resources.text("victory.title"),
                primary_label=self.resources.text("button.play_again"),
                body_lines=(self.resources.text("victory.subtitle"),),
                achievement_count=ROUND_COUNT,
            )
        )
        self._surfaces.push_overlay(CompletionOverlay(self.completion, on_primary=self._restart))
        self.controls.set_progress(ROUND_COUNT)
        self.state = AppState.TERMINAL
        self._dirty = True

    def _restart(self) -> None:
        self._activated = True
        next_level = adapt_level(self.session.level, self.session.history)
        self.session = FireflySession(
            self.factory.build_set(next_level), level=next_level, history=self.session.history
        )
        self.session_id = f"{self.session_id.rsplit('-', 1)[0]}-{self.rng.randrange(1_000_000):06d}"
        self._surfaces.pop_overlay()
        self.completion.clear()
        self.motion.jar_lights = 0
        self.state = AppState.PLAYING
        self._start_round(lead=ROUND_LEAD + 0.4)

    # -- hints ------------------------------------------------------------------------

    def _maybe_hint(self, now: float) -> None:
        if self._busy or not self.asking or self.timeline.busy:
            return
        if now - self._last_activity < IDLE_HINT_SECONDS * (self._idle_hints + 1):
            return
        self._idle_hints += 1
        if self._idle_hints == 1:
            self.session.note_hint()
        self.cast.point(1.8)
        if self.controls.replay.enabled:
            self.motion.replay_pulse = now
        elif self.session.missed:
            current = self.session.current_round
            if current is not None:
                for index in range(current.quantity):
                    self.motion.halos[index] = now + 0.15 * index
        if self._idle_hints >= 2:
            self.audio.play_prompt_choose()
        self._dirty = True


def _badge_anchor(round_: FireflyRound, index: int) -> tuple[int, int]:
    """Where a count badge goes: above a firefly, else below, else beside it.

    The anchor is the badge's bottom edge before it rises (see ``Badge``).
    """

    x, y = round_.positions[index]
    others = [point for other, point in enumerate(round_.positions) if other != index]
    above = any(abs(ox - x) < 56 and 0 < y - oy < 130 for ox, oy in others)
    below = any(abs(ox - x) < 56 and 0 < oy - y < 130 for ox, oy in others)
    if not above:
        return (x, y - 34)
    if not below:
        return (x, y + 84)
    side = 1 if x >= FIELD_CENTER[0] else -1
    return (x + side * 70, y + 35)


def _safe_point(surface: pygame.Surface, position: tuple[int, int]) -> bool:
    viewport = activity_viewport_for_surface(surface)
    x, y = position
    if not (0 <= x < viewport.surface.width and 0 <= y < viewport.surface.height):
        return False
    for protected in viewport.protected_regions:
        if protected.x <= x < protected.right and protected.y <= y < protected.bottom:
            return False
    return True


__all__ = ["AppState", "FireflyActivity", "Timeline"]
