"""Lifecycle, timeline and shared-kit input for Stelle Incantate (Enchanted Stars).

One night is four figures. Each figure's stars twinkle in (in a scrambled
order), Leo points at the sky and the goal strip shows — and chimes — where
counting starts and which way it goes (1 2 3, "start at 4", "count back from
9", 10 11 12). Nothing marks the next star: the child decides. A right star
lights with its own chime and a line grows to it; a wrong star wobbles and Leo
thinks (the last lit star is shown again); a second mistake on the same step
gets a demonstration (a dotted trail to the right star). At the missing-number
stage the star without a numeral asks for its number on three cards. When the
last star lights, the figure's picture appears in the sky, Leo cheers, the
stars count once more, and the child may hear a voiced fact (real
constellations) before pressing on. The night ends on the shared cast
completion scene. Feedback follows ADR 0037.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from enum import StrEnum
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
    from .sky_art import SkyArt
    from .sky_audio import SkyAudio
    from .sky_content import LEO_HEIGHT, NEXT_CENTER, REFERENCE_HEIGHT, REFERENCE_WIDTH, sky_point
    from .sky_controls import SkyControls, card_rects
    from .sky_model import ChoiceResult, Night, Phase, SkyRound, TapResult, TaskKind
    from .sky_renderer import LINE_SECONDS, Band, SceneMotion, SkyCast, SkyRenderer
    from .sky_services import EventPort, ProgressPort
else:
    from sky_art import SkyArt
    from sky_audio import SkyAudio
    from sky_content import LEO_HEIGHT, NEXT_CENTER, REFERENCE_HEIGHT, REFERENCE_WIDTH, sky_point
    from sky_controls import SkyControls, card_rects
    from sky_model import ChoiceResult, Night, Phase, SkyRound, TapResult, TaskKind
    from sky_renderer import LINE_SECONDS, Band, SceneMotion, SkyCast, SkyRenderer
    from sky_services import EventPort, ProgressPort

GOAL_BEAT_SECONDS = 0.42
RECOUNT_STEP_SECONDS = 0.16
MAX_SCHEDULED = 48
PRAISE_CUES = ("praise", "celebrate")
NIGHT_NAVY = (37, 59, 89)  # theme token "navy" behind the completion card


class AppState(StrEnum):
    PLAYING = "playing"
    TERMINAL = "terminal"


class Timeline:
    """Tiny bounded scheduler for the scripted moments (goal, recount, hints)."""

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


def goal_numbers(round_: SkyRound) -> tuple[tuple[int, int, int], bool]:
    """The goal strip: three numbers from the start and whether the first is given."""

    first = round_.numbers[0]
    step = -1 if round_.descending else 1
    numbers = (first, first + step, first + 2 * step)
    return numbers, round_.given is not None


class SkyActivity:
    """Coordinate the night, shared-kit controls, art and lifecycle."""

    def __init__(
        self,
        *,
        screen: pygame.Surface,
        canvas: PygameReferenceCanvas,
        night: Night,
        typography: GreiaTypography,
        resources: LocalizedResources,
        audio: SkyAudio,
        progress: ProgressPort,
        events: EventPort,
        clock: Callable[[], float] = time.monotonic,
        kit: ControlKit | None = None,
        art: SkyArt | None = None,
    ) -> None:
        self.screen = screen
        self.canvas = canvas
        self.night = night
        self.typography = typography
        self.resources = resources
        self.audio = audio
        self.progress = progress
        self.events = events
        self.clock = clock
        self.night_id = uuid4().hex

        # Shared control kit (ADR 0037): learn Collection -> orange accent.
        self.kit = kit if kit is not None else ControlKit(typography, ControlTheme.for_accent("orange"))
        self.art = art if art is not None else SkyArt(self.kit.painter)
        feedback = CastFeedback("leo", height=LEO_HEIGHT, art=self.kit.art, clock=clock)
        self.cast = SkyCast(feedback, self.art.cast_pose("leo", "pose_point", LEO_HEIGHT), clock)
        self.renderer = SkyRenderer(self.art, self.cast, clock=clock)
        self.motion = SceneMotion()
        self.timeline = Timeline(clock)
        self.band = Band()
        self.controls = SkyControls(
            self.kit,
            self.art,
            ControlLayout.for_canvas(canvas, screen.get_size()),
            night.total,
            on_star=self._on_star,
            on_card=self._on_card,
            on_goal=self._on_goal,
            on_next=self._on_next,
            on_fact=self._on_fact,
        )
        self._surfaces = SurfaceNavigator(self.controls.layer)
        self._input = PygameControlInput(to_logical=canvas.pointer, is_safe=lambda pos: _safe_point(self.screen, pos))
        self.completion = PygameCompletionScreen(
            typography,
            width=REFERENCE_WIDTH,
            height=REFERENCE_HEIGHT,
            palette=CompletionPalette(background=NIGHT_NAVY),
            scene=CompletionScene(self.kit, character="leo", star_total=night.total),
        )
        self.state = AppState.PLAYING
        self._running = True
        self._ready_published = False
        self._dirty = True
        self._activated = False
        self._first_figure = True
        self._retry_said = False
        self._praise_index = 0
        self._fact_opened: set[str] = set()
        self._last_activity = clock()
        self._hints = IdleHintScheduler(now=self._last_activity)
        self._start_figure()

    @property
    def round(self) -> SkyRound:
        return self.night.round

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
            self.progress.save(self.night.progress)
            self.typography.clear()
        return 0

    def step(self) -> bool:
        """Advance timers and animation; return True while something moves."""

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
            self.renderer.draw(surface, self.round, self.motion, self.band)
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
            self.canvas = PygameReferenceCanvas(self.screen, hires=True)
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

    # -- figure flow ------------------------------------------------------------------

    def _start_figure(self) -> None:
        round_ = self.round
        now = self.clock()
        self.timeline.clear()
        self.motion.start_figure(now, round_.star_count, f"{self.night_id}:{self.night.completed}")
        self.art.preload(tuple(round_.label(index) for index in range(round_.star_count)))
        self.audio.prepare_numbers(round_.numbers)
        numbers, given = goal_numbers(round_)
        self.controls.bind_round(round_, self.art.goal_icon(numbers, given))
        self.controls.set_progress(self.night.completed)
        self.cast.reset()
        self.band = Band()
        self._retry_said = False
        if self._first_figure:
            self.audio.say("go")
            self._first_figure = False
        self.timeline.after(self.motion.appear_seconds(), self._present_goal)
        self._note_activity()
        self._dirty = True

    def _present_goal(self) -> None:
        """Leo points; the strip chimes where counting starts and which way it goes."""

        round_ = self.round
        if round_.phase is Phase.REVEALED:
            return
        self.cast.point(1.6 + GOAL_BEAT_SECONDS * 3)
        numbers, given = goal_numbers(round_)
        if given:
            # The given star is lit already: show it (never the next one).
            self.motion.pulses[0] = self.clock()
        for beat, number in enumerate(numbers):
            self.timeline.after(GOAL_BEAT_SECONDS * beat, lambda n=number: self.audio.chime(n))
        # Leo's goal line, queued after a "ready, go" that may still be playing;
        # the given star's number follows it.
        task = round_.task
        if task in (TaskKind.ORDER, TaskKind.MISSING):
            self.audio.then("connect_in_order")
        elif task is TaskKind.COUNT_BACK:
            self.audio.then("count_back")
            self.audio.say_number(numbers[0], after=True)
        elif task is TaskKind.COUNT_ON and numbers[0] == 4:
            self.audio.then("start_at_four")  # names the given 4 itself
        elif given:
            self.audio.say_number(numbers[0])
        self._dirty = True

    def _on_goal(self) -> None:
        if self.round.phase is Phase.REVEALED:
            return
        self._activated = True
        self._present_goal()

    def _on_star(self, index: int) -> None:
        round_ = self.round
        result = round_.tap(index)
        if result is TapResult.IGNORED:
            return
        self._activated = True
        now = self.clock()
        if result is TapResult.AGAIN:
            # A lit star simply says its number again (never a mistake).
            self.motion.pops[index] = now
            self.audio.chime(round_.numbers[index])
            self.audio.say_number(round_.numbers[index])
        elif result is TapResult.WRONG:
            self._mistake(index)
        elif result is TapResult.ASK:
            self.motion.pops[index] = now
            self.motion.trail = None
            self.audio.play("card")
            self.audio.say("which_missing")  # the number cards open
            self.cast.point(1.4)
            self.controls.sync(round_, refocus=True)
        else:
            self._lit(index)
        self._dirty = True

    def _on_card(self, card: int) -> None:
        round_ = self.round
        value = self.controls.choice_value(card)
        if value is None:
            return
        result = round_.choose(value)
        if result is ChoiceResult.IGNORED:
            return
        self._activated = True
        if result is ChoiceResult.WRONG:
            self._mistake(None)
            self.controls.sync(round_)
        else:
            self.cast.correct()
            self.motion.add_fx("check_pop", card_rects(len(round_.choices))[card].center, self.clock())
            self._lit(round_.last_lit if round_.last_lit is not None else 0, refocus=True)
        self._dirty = True

    def _lit(self, index: int, *, refocus: bool = False) -> None:
        round_ = self.round
        now = self.clock()
        self.motion.pops[index] = now
        self.motion.trail = None
        self.motion.pulses.clear()
        self.motion.line_from = {
            edge: (edge[1] if edge[0] == index else edge[0]) for edge in round_.edges_to(index)
        }
        self.motion.line_started = now
        x, y = sky_point(round_.figure.stars[index])
        self.motion.add_fx("sparkle", (x + 34, y - 30), now)  # beside the numeral, never over it
        number = round_.numbers[index]
        self.audio.chime(number)
        self.audio.say_number(number)
        self.controls.sync(round_, refocus=refocus)
        if round_.complete:
            self.timeline.after(LINE_SECONDS + 0.12, self._reveal)
        elif round_.star_count >= 9 and round_.lit_count == round_.star_count // 2 + 1:
            self.audio.say("progress")  # long figures: "keep going!" once, halfway

    def _mistake(self, index: int | None) -> None:
        """Try again: think pose, show where we are; demonstrate after two."""

        round_ = self.round
        now = self.clock()
        if index is not None:
            self.motion.wobble = (index, now)
        self.cast.try_again()
        self.audio.play("boop")
        if not self._retry_said:
            self.audio.say("retry")
            self._retry_said = True
        if round_.step_mistakes >= 2:
            self._demonstrate()
        else:
            self.timeline.after(0.6, self._show_anchor)

    def _show_anchor(self) -> None:
        """The last lit star says its number again ("we are here")."""

        round_ = self.round
        if round_.phase is Phase.REVEALED:
            return
        if round_.last_lit is None:
            self._present_goal()
            return
        self.motion.pulses[round_.last_lit] = self.clock()
        self.audio.chime(round_.numbers[round_.last_lit])
        self.audio.say_number(round_.numbers[round_.last_lit])
        self._dirty = True

    def _demonstrate(self, *, after_mistakes: bool = True) -> None:
        """Show the way: a dotted trail from the last lit star to the right one."""

        round_ = self.round
        target = round_.next_index
        if target is None:
            return
        if after_mistakes:
            round_.note_demonstration()
        now = self.clock()
        self.cast.point(2.0)
        if round_.phase is Phase.CHOOSING:
            card = card_rects(len(round_.choices))[round_.choices.index(round_.numbers[target])].center
            for beat in range(2):
                self.timeline.after(0.4 * beat, lambda: self.motion.add_fx("sparkle", card, self.clock()))
        elif round_.last_lit is not None:
            self.motion.trail = (round_.last_lit, target, now)
        else:
            self.motion.pulses[target] = now
        self.timeline.after(0.7, lambda: self.audio.chime(round_.numbers[target]))
        self._dirty = True

    def _reveal(self) -> None:
        """The figure's picture appears: Leo cheers, the stars count once more."""

        round_ = self.round
        if round_.phase is not Phase.REVEALED or self.motion.reveal_started is not None:
            return
        now = self.clock()
        summary = self.night.finish_figure()
        self.events.constellation_completed(self.night_id, self.night.completed, summary)
        self.progress.save(self.night.progress)
        self.motion.reveal_started = now
        self.cast.correct()
        self.audio.play("reveal")
        cue = PRAISE_CUES[self._praise_index % len(PRAISE_CUES)]
        self._praise_index += 1
        self.audio.say(cue)
        # Celebrate around the picture, never over it.
        centre = round_.figure.centre()
        xs = [sky_point(star)[0] for star in round_.figure.stars]
        self.motion.add_fx("firework", (max(110, min(xs) - 90), centre[1] - 90), now)
        self.motion.add_fx("firework", (min(960, max(xs) + 90), centre[1] - 70), now)
        if round_.figure.figure_id == "razzo":
            self.audio.play("whoosh")
            self.motion.add_fx("shooting_star", (max(xs) + 30, centre[1] + 30), now)
        for position in range(round_.star_count):
            self.timeline.after(0.5 + RECOUNT_STEP_SECONDS * position, lambda i=position: self._recount(i))
        try:
            self.band = Band(name=self.resources.text(round_.figure.name_key))
        except Exception:
            self.band = Band()
        self.controls.sync(round_, refocus=True, ready=True, fact=self._fact_text(round_) is not None)
        self.controls.set_progress(self.night.completed)
        self._dirty = True

    def _recount(self, index: int) -> None:
        round_ = self.round
        if index >= round_.star_count:
            return
        self.motion.pops[index] = self.clock()
        self.audio.chime(round_.numbers[index])
        self._dirty = True

    def _fact_text(self, round_: SkyRound) -> str | None:
        key = round_.figure.fact_key
        if key is None:
            return None
        try:
            text = self.resources.text(key)
        except Exception:
            return None
        return text or None

    def _on_fact(self) -> None:
        round_ = self.round
        text = self._fact_text(round_)
        if text is None or round_.phase is not Phase.REVEALED:
            return
        self._activated = True
        self.band = Band(name=self.band.name, fact=text)
        try:
            cue = self.resources.audio_cue(round_.figure.fact_key)
        except Exception:
            cue = None
        if cue is not None:
            self.audio.play_voice(cue.path)
        figure_id = round_.figure.figure_id
        if figure_id not in self._fact_opened:
            self._fact_opened.add(figure_id)
            self.events.fact_opened(self.night_id, figure_id)
        self._dirty = True

    def _on_next(self) -> None:
        if self.round.phase is not Phase.REVEALED or self.state is not AppState.PLAYING:
            return
        self._activated = True
        if self.night.complete:
            self._complete_night()
            return
        self.night.next_figure()
        self._start_figure()

    def _complete_night(self) -> None:
        self.timeline.clear()
        self.audio.play("fanfare")
        self.audio.say("celebrate")
        self.completion.prepare(
            CompletionContent(
                title=self.resources.text("victory.title"),
                primary_label=self.resources.text("button.play_again"),
                body_lines=(self.resources.text("victory.subtitle"),),
                achievement_count=self.night.total,
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
        self.night_id = uuid4().hex
        self._fact_opened.clear()
        self.night.restart()
        self.state = AppState.PLAYING
        self._first_figure = True
        self._start_figure()

    # -- hints ------------------------------------------------------------------------

    def _maybe_hint(self, now: float) -> None:
        round_ = self.round
        if self.timeline.busy:
            return
        step = self._hints.poll(now, self._last_activity)
        if not step:
            return
        if round_.phase is Phase.REVEALED:
            self.cast.point(self._hints.animation_seconds(1.6))
            self.motion.add_fx("sparkle", NEXT_CENTER, now)
        elif step == 1:
            # First hesitation: point and show where we are (not where to go).
            round_.note_hint()
            self._show_anchor()
            self.cast.point(self._hints.animation_seconds(1.8))
        else:
            round_.note_hint()
            self._demonstrate(after_mistakes=False)
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


__all__ = ["AppState", "SkyActivity", "Timeline", "goal_numbers"]
