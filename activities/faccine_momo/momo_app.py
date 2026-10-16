"""Lifecycle, scripted moments and shared-kit input for Momo's Happy Faces.

A session opens with the free **mirror** warm-up (Momo copies any face the
child picks; a cuddle comforts sad Momo; after a few faces a big "let's play"
button appears). Then one *visit* is six tasks in three stages of one loop:

* **recognise** - Momo shows a feeling and asks "How is Momo feeling?"; the
  child picks the friend who feels the same (other cast faces);
* **explain** - a picture story slides in next to Momo's ``?`` silhouette;
  the child picks the face that fits, and Momo appears feeling it;
* **help** - Momo feels something in a story; the child picks the kind thing
  that helps; it flies to Momo and Momo feels better.

Feedback follows ADR 0037 with Flash as the guide friend: correct = Flash
``pose_cheer`` + Momo acting the feeling + library FX + Momo's approved line;
try again = Flash ``pose_think``, the pick is set aside (unlimited kind
retries) and the feeling is demonstrated (Momo acts and says it; for helps
the kind choice glows). Idle ~6 s -> Flash points and the cue moves; again ->
the question replays. The prompt never speaks or shows the answer. The visit
ends on the shared cast completion scene and the ladder adapts.
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
    from .momo_art import MomoArt
    from .momo_audio import MomoAudio
    from .momo_content import (
        GUIDE_CHARACTER,
        MIRROR_ORDER,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        STORIES_BY_ID,
        TASKS_PER_VISIT,
        Emotion,
        HELP_PLANS,
        Stage,
    )
    from .momo_controls import MomoControls, choice_id
    from .momo_layout import (
        GUIDE_HEIGHT,
        HELP_ICON,
        MIRROR_ICON,
        MOMO_HEIGHT,
        MOMO_SIDE,
        MOMO_STAGE,
        MOMO_WARMUP,
        MOMO_WARMUP_HEIGHT,
        TILE_ICON,
        momo_chest,
        momo_head,
    )
    from .momo_model import FeelingsLog, MirrorWarmup, MomoVisit, Outcome, Task, TaskFactory, adapt_level
    from .momo_renderer import Flight, FrameView, GuideCast, MomoRenderer, SceneMotion
    from .momo_services import MomoEventPort, MomoProgress, NullMomoEvents, NullMomoProgress, ProgressPort
else:
    from momo_art import MomoArt
    from momo_audio import MomoAudio
    from momo_content import (
        GUIDE_CHARACTER,
        MIRROR_ORDER,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        STORIES_BY_ID,
        TASKS_PER_VISIT,
        Emotion,
        HELP_PLANS,
        Stage,
    )
    from momo_controls import MomoControls, choice_id
    from momo_layout import (
        GUIDE_HEIGHT,
        HELP_ICON,
        MIRROR_ICON,
        MOMO_HEIGHT,
        MOMO_SIDE,
        MOMO_STAGE,
        MOMO_WARMUP,
        MOMO_WARMUP_HEIGHT,
        TILE_ICON,
        momo_chest,
        momo_head,
    )
    from momo_model import FeelingsLog, MirrorWarmup, MomoVisit, Outcome, Task, TaskFactory, adapt_level
    from momo_renderer import Flight, FrameView, GuideCast, MomoRenderer, SceneMotion
    from momo_services import MomoEventPort, MomoProgress, NullMomoEvents, NullMomoProgress, ProgressPort

IDLE_HINT_SECONDS = 6.0
INTRO_LOCK = 0.45
PROMPT_DELAY = 0.5
THINK_SECONDS = 1.6
DEMO_DELAY = 0.55
FLIGHT_SECONDS = 0.7
NEXT_MIN = 2.2
NEXT_MAX = 6.0
GLOW_SECONDS = 2.4
MAX_SCHEDULED = 32
LAVENDER = (232, 221, 247)  # theme background token "lavender" behind the completion card
THANKS = {plan.helper: plan.thanks for plan in HELP_PLANS}


class AppState(StrEnum):
    WARMUP = "warmup"
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


class MomoActivity:
    """Coordinate the visit model, kit controls, art, voice and lifecycle."""

    def __init__(
        self,
        *,
        screen: pygame.Surface,
        canvas: PygameReferenceCanvas,
        typography: GreiaTypography,
        resources: LocalizedResources,
        audio: MomoAudio,
        progress: ProgressPort | None = None,
        events: MomoEventPort | None = None,
        rng: random.Random | None = None,
        session_id: str = "preview",
        clock: Callable[[], float] = time.monotonic,
        warmup: bool = True,
        kit: ControlKit | None = None,
        art: MomoArt | None = None,
    ) -> None:
        self.screen = screen
        self.canvas = canvas
        self.typography = typography
        self.resources = resources
        self.audio = audio
        self.progress = progress if progress is not None else NullMomoProgress()
        self.events = events if events is not None else NullMomoEvents()
        self.rng = rng if rng is not None else random.Random()
        self.session_id = session_id
        self.clock = clock

        saved = self.progress.load()
        self.level = saved.level
        self.feelings = FeelingsLog({Emotion(name) for name in saved.known})
        self.factory = TaskFactory(self.rng)
        self.visit = MomoVisit(self.factory.build_visit(self.level), level=self.level)
        self.warm = MirrorWarmup()

        # Shared control kit (ADR 0037): play Collection -> ocean accent.
        self.kit = kit if kit is not None else ControlKit(typography, ControlTheme.for_accent("ocean"))
        self.art = art if art is not None else MomoArt(self.kit.painter)
        self.motion = SceneMotion(clock)
        feedback = CastFeedback(GUIDE_CHARACTER, height=GUIDE_HEIGHT, art=self.kit.art, clock=clock)
        self.guide = GuideCast(feedback, self.art.cast(GUIDE_CHARACTER, "pose_point", GUIDE_HEIGHT), clock)
        self.renderer = MomoRenderer(self.art, self.guide, self.motion, clock)
        self.timeline = Timeline(clock)
        self.controls = MomoControls(
            self.kit,
            ControlLayout.for_canvas(canvas, screen.get_size()),
            on_choice=self._on_choice,
            on_momo=self._on_momo,
            on_go=self._on_go,
            on_listen=self._on_listen,
        )
        self._surfaces = SurfaceNavigator(self.controls.layer)
        self._input = PygameControlInput(to_logical=canvas.pointer, is_safe=lambda pos: _safe_point(self.screen, pos))
        self.completion = PygameCompletionScreen(
            typography,
            width=REFERENCE_WIDTH,
            height=REFERENCE_HEIGHT,
            palette=CompletionPalette(background=LAVENDER),
            scene=CompletionScene(self.kit, character="momo", star_total=TASKS_PER_VISIT),
        )
        self.state = AppState.WARMUP
        self._running = True
        self._ready_published = False
        self._dirty = True
        self._busy = False
        self._activated = False
        self._revealed = False
        self._helped = False
        self._next_window: tuple[float, float] | None = None
        self._last_activity = clock()
        self._idle_hints = 0
        if warmup:
            self._enter_warmup()
        else:
            self._begin_visit()

    # -- main loop ----------------------------------------------------------------

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
            self._save(self.level)
            self.typography.clear()
        return 0

    def step(self) -> bool:
        """Advance timers; return True while something on screen is moving."""

        now = self.clock()
        if self.timeline.run_due():
            self._dirty = True
        if self.guide.update():
            self._dirty = True
        self.motion.prune()
        if self._next_window is not None:
            earliest, latest = self._next_window
            if now >= earliest and (now >= latest or not self.audio.is_speech_playing()):
                self._next_window = None
                self._next_task()
        if self.state is not AppState.TERMINAL:
            self._maybe_hint(now)
        if self.controls.layer.invalidation.should_draw:
            self._dirty = True
        return self.motion.active() or self.guide.animating

    def render(self) -> None:
        surface = self.canvas.surface
        if self.state is AppState.TERMINAL:
            self._surfaces.draw(surface)
            return
        self.renderer.draw(surface, self.frame_view())
        self._draw_controls(surface)

    def frame_view(self) -> FrameView:
        if self.state is AppState.WARMUP:
            return FrameView(self.warm.emotion.value, MOMO_WARMUP, MOMO_WARMUP_HEIGHT, None, show_guide=False)
        task = self.visit.task
        if task.stage is Stage.RECOGNISE:
            return FrameView(task.feeling.value, MOMO_STAGE, MOMO_HEIGHT)
        if task.stage is Stage.EXPLAIN:
            face = task.feeling.value if self._revealed else "silhouette"
            return FrameView(face, MOMO_SIDE, MOMO_HEIGHT, task.story_id)
        face = Emotion.HAPPY.value if self._helped else task.feeling.value
        return FrameView(face, MOMO_SIDE, MOMO_HEIGHT, task.story_id)

    def _draw_controls(self, surface: pygame.Surface) -> None:
        """Draw kit controls; a set-aside pick shakes briefly; hints glow."""

        shaking = None
        for button in self.controls.choices:
            if self.motion.wobble_offset(button.control_id):
                shaking = button
        if shaking is None:
            self._surfaces.draw(surface)
        else:
            base = shaking.rect
            shaking.rect = base.move(self.motion.wobble_offset(shaking.control_id), 0)
            self._surfaces.draw(surface)
            shaking.rect = base
        for button in (*self.controls.choices, self.controls.go):
            if button.visible:
                self.renderer.draw_glow(surface, button.control_id, button.rect)
        self.renderer.draw_overlay(surface)

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
        self._idle_hints = 0

    # -- warm-up mirror ------------------------------------------------------------

    def _enter_warmup(self) -> None:
        self.state = AppState.WARMUP
        self.warm = MirrorWarmup()
        faces = [
            (self.art.face("momo", emotion, MIRROR_ICON), self._feeling_word(emotion))
            for emotion in MIRROR_ORDER
        ]
        self.controls.show_warmup(faces)
        self.controls.select_mirror(MIRROR_ORDER.index(self.warm.emotion))
        self.motion.act("appear", momo_head(MOMO_WARMUP, MOMO_WARMUP_HEIGHT))
        self.timeline.after(0.3, lambda: self.audio.say("welcome"))
        self._note_activity()
        self._dirty = True

    def _mirror(self, index: int) -> None:
        emotion = MIRROR_ORDER[index]
        self.warm.show(emotion)
        self.controls.select_mirror(index)
        self.motion.act(emotion.value, momo_head(MOMO_WARMUP, MOMO_WARMUP_HEIGHT))
        self.audio.play_sfx("pop")
        self.audio.say(emotion.value)
        self.controls.set_ready(self.warm.ready)
        self._dirty = True

    def _on_momo(self) -> None:
        if self.state is not AppState.WARMUP:
            return
        self._activated = True
        head = momo_head(MOMO_WARMUP, MOMO_WARMUP_HEIGHT)
        if self.warm.comfort():
            for order, dx in enumerate((-80, 0, 80)):
                self.motion.add_fx("heart_pop", (head[0] + dx, head[1] - 20 - (order % 2) * 30), 96, delay=order * 0.12)
            self.controls.select_mirror(MIRROR_ORDER.index(Emotion.HAPPY))
            self.motion.act(Emotion.HAPPY.value, head)
            self.audio.play_sfx("heart")
            self.audio.say("comfort")
        else:
            self.motion.act("appear", head)
            self.audio.play_sfx("giggle")
        self._dirty = True

    def _on_go(self) -> None:
        if self.state is not AppState.WARMUP or not self.warm.ready:
            return
        self._activated = True
        self.audio.play_sfx("pop")
        self.audio.stop_speech()
        self._begin_visit()

    # -- visit flow -----------------------------------------------------------------

    def _begin_visit(self) -> None:
        self.state = AppState.PLAYING
        self._start_task()

    def _start_task(self) -> None:
        task = self.visit.task
        self.timeline.clear()
        self.motion.clear()
        self.guide.reset()
        self._revealed = False
        self._helped = False
        self._next_window = None
        self.controls.show_task(self._tiles(task), completed=self.visit.completed_count)
        self._busy = True
        self._sync(refocus=True)
        if task.stage is Stage.RECOGNISE:
            self.motion.act("appear", momo_head(MOMO_STAGE, MOMO_HEIGHT))
            self.timeline.after(PROMPT_DELAY, self._ask)
        else:
            self.motion.card_start = self.clock()
            self.timeline.after(PROMPT_DELAY, self._ask)
        self.timeline.after(INTRO_LOCK, self._unlock)
        self._note_activity()
        self._dirty = True

    def _tiles(self, task: Task) -> list[tuple[pygame.Surface | None, str]]:
        if task.stage is Stage.HELP:
            return [(self.art.item(choice.key, HELP_ICON), "") for choice in task.choices]
        return [
            (self.art.face(choice.character or "momo", choice.key, TILE_ICON), self._feeling_word(Emotion(choice.key)))
            for choice in task.choices
        ]

    def _feeling_word(self, emotion: Emotion) -> str:
        return self.resources.text(f"emotion.{emotion.value}")

    def _ask(self) -> None:
        """Pose the question: voice only where an approved line asks it.

        Recognise asks "How is Momo feeling now?" (never the feeling itself).
        Explain and help have no approved question yet, so the picture story
        arrives with its sound and Flash points at it.
        """

        task = self.visit.task
        if task.stage is Stage.RECOGNISE:
            self.audio.say("game_prompt")
        else:
            story = STORIES_BY_ID.get(task.story_id or "")
            self.audio.play_sfx(story.sound if story else None)
            if task.stage is Stage.HELP:
                self.motion.act(task.feeling.value, momo_head(MOMO_SIDE, MOMO_HEIGHT))
        self.guide.point(1.8)
        self._dirty = True

    def _unlock(self) -> None:
        self._busy = False
        self._note_activity()
        self._sync()
        self._dirty = True

    def _sync(self, *, refocus: bool = False, solved_index: int | None = None) -> None:
        self.controls.sync(
            busy=self._busy,
            rejected=self.visit.rejected,
            solved_index=solved_index,
            refocus=refocus,
        )

    def _on_choice(self, index: int) -> None:
        if self.state is AppState.WARMUP:
            if 0 <= index < len(MIRROR_ORDER):
                self._activated = True
                self._mirror(index)
            return
        if self.state is not AppState.PLAYING or self._busy:
            return
        outcome = self.visit.choose(index)
        if outcome is Outcome.IGNORED:
            return
        self._activated = True
        if outcome is Outcome.CORRECT:
            self._celebrate(index)
        else:
            self._try_again(index)

    def _celebrate(self, index: int) -> None:
        task = self.visit.task
        self._busy = True
        self._sync(solved_index=index)
        self.controls.set_progress(self.visit.completed_count)
        self.guide.correct()
        self.audio.play_sfx("boing")
        tile = self.controls.tile(index).rect
        self.motion.add_fx("sparkle", (tile.left + 14, tile.top + 6), 84)
        self.motion.add_fx("sparkle", (tile.right - 14, tile.top + 6), 84, delay=0.12)
        if task.stage is Stage.HELP:
            item = self.art.item(task.answer, HELP_ICON)
            target = momo_chest(MOMO_SIDE, MOMO_HEIGHT)
            if item is not None:
                self.motion.fly(Flight(item, tile.center, target, self.clock(), FLIGHT_SECONDS))
            self.timeline.after(FLIGHT_SECONDS, self._helped_momo)
            self._next_window = (self.clock() + NEXT_MIN + FLIGHT_SECONDS, self.clock() + NEXT_MAX + FLIGHT_SECONDS)
        else:
            feeling = task.feeling
            self._revealed = True
            midbottom = MOMO_STAGE if task.stage is Stage.RECOGNISE else MOMO_SIDE
            self.motion.act(feeling.value, momo_head(midbottom, MOMO_HEIGHT))
            self.audio.say(feeling.value)
            if self.feelings.learn(feeling):
                self.events.emotion_discovered(feeling.value)
            self._next_window = (self.clock() + NEXT_MIN, self.clock() + NEXT_MAX)
        self._dirty = True

    def _helped_momo(self) -> None:
        task = self.visit.task
        self._helped = True
        head = momo_head(MOMO_SIDE, MOMO_HEIGHT)
        self.motion.act(Emotion.HAPPY.value, head, fx=False)
        self.motion.add_fx("heart_pop", (head[0] - 70, head[1] - 30), 96)
        self.motion.add_fx("heart_pop", (head[0] + 70, head[1] - 50), 84, delay=0.15)
        self.audio.play_sfx("heart")
        if THANKS.get(task.answer) == "comfort":
            self.audio.say("comfort")
        else:
            self.audio.praise()
        self._dirty = True

    def _try_again(self, index: int) -> None:
        self.motion.wobble(choice_id(index))
        self.guide.try_again()
        self.audio.play_sfx("wobble")
        self._sync()
        self._busy = True
        self.timeline.after(DEMO_DELAY, self._demonstrate)
        self.timeline.after(DEMO_DELAY + 0.2, self._unlock)
        self.timeline.after(THINK_SECONDS, lambda: self.guide.point(2.2))
        self._dirty = True

    def _demonstrate(self) -> None:
        """Show the feeling (or the kind help) after a set-aside pick."""

        task = self.visit.task
        if task.stage is Stage.HELP:
            self.motion.glow(choice_id(task.answer_index), GLOW_SECONDS)
            self.motion.momo_pulse = self.clock()
        elif task.stage is Stage.RECOGNISE:
            self.motion.act(task.feeling.value, momo_head(MOMO_STAGE, MOMO_HEIGHT))
            self.audio.say(task.feeling.value)
        else:
            self.motion.card_pulse = self.clock()
            self.audio.say(task.feeling.value)
        self._dirty = True

    def _next_task(self) -> None:
        if self.visit.advance():
            self._start_task()
        else:
            self._complete_visit()

    def _complete_visit(self) -> None:
        first_try = self.visit.first_try_count
        next_level = adapt_level(self.level, first_try, len(self.visit.tasks))
        self.events.visit_completed(
            self.session_id,
            {"level": self.level, "first_try": first_try, "tasks": len(self.visit.tasks)},
        )
        self.level = next_level
        self._save(next_level)
        self.timeline.clear()
        self.audio.say(Emotion.HAPPY.value)
        self.completion.prepare(
            CompletionContent(
                title=self.resources.text("complete.title"),
                primary_label=self.resources.text("button.play_again"),
                body_lines=(self.resources.text("complete.body"),),
                achievement_count=TASKS_PER_VISIT,
            )
        )
        self._surfaces.push_overlay(CompletionOverlay(self.completion, on_primary=self._restart))
        self.state = AppState.TERMINAL
        self._dirty = True

    def _restart(self) -> None:
        self._activated = True
        self.visit = MomoVisit(self.factory.build_visit(self.level), level=self.level)
        self.session_id = f"{self.session_id.rsplit('-', 1)[0]}-{self.rng.randrange(1_000_000):06d}"
        self._surfaces.pop_overlay()
        self.completion.clear()
        self.audio.stop_speech()
        self._begin_visit()

    def _save(self, level: int) -> None:
        self.progress.save(MomoProgress(level=level, known=self.feelings.ordered()))

    # -- hints ------------------------------------------------------------------------

    def _maybe_hint(self, now: float) -> None:
        if self._busy or self.timeline.busy or self._next_window is not None:
            return
        if now - self._last_activity < IDLE_HINT_SECONDS * (self._idle_hints + 1):
            return
        self._idle_hints += 1
        if self.state is AppState.WARMUP:
            if self.warm.ready:
                self.motion.glow("go", GLOW_SECONDS)
            else:
                untried = [i for i, emotion in enumerate(MIRROR_ORDER) if emotion not in self.warm.tried]
                if untried:
                    self.motion.glow(choice_id(untried[0]), GLOW_SECONDS)
            self._dirty = True
            return
        if self.visit.solved:
            return
        if self._idle_hints == 1:
            self.visit.note_hint()
        self._cue(replay=self._idle_hints >= 2)

    def _cue(self, *, replay: bool) -> None:
        """Draw attention to the cue (never to the answer)."""

        task = self.visit.task
        self.guide.point(1.8)
        if task.stage is Stage.RECOGNISE:
            self.motion.act(task.feeling.value if not replay else "appear", momo_head(MOMO_STAGE, MOMO_HEIGHT))
            if replay:
                self.audio.say("game_prompt")
        else:
            self.motion.card_pulse = self.clock()
            if task.stage is Stage.HELP:
                self.motion.act(task.feeling.value, momo_head(MOMO_SIDE, MOMO_HEIGHT))
            if replay:
                story = STORIES_BY_ID.get(task.story_id or "")
                self.audio.play_sfx(story.sound if story else None)
        self._dirty = True

    def _on_listen(self) -> None:
        self._activated = True
        if self.state is AppState.WARMUP:
            self.audio.say("welcome")
            self.motion.act("appear", momo_head(MOMO_WARMUP, MOMO_WARMUP_HEIGHT))
            self._dirty = True
            return
        if self.state is AppState.PLAYING and not self.visit.solved:
            self._cue(replay=True)


def _safe_point(surface: pygame.Surface, position: tuple[int, int]) -> bool:
    viewport = activity_viewport_for_surface(surface)
    x, y = position
    if not (0 <= x < viewport.surface.width and 0 <= y < viewport.surface.height):
        return False
    for protected in viewport.protected_regions:
        if protected.x <= x < protected.right and protected.y <= y < protected.bottom:
            return False
    return True


__all__ = ["AppState", "MomoActivity", "Timeline"]
