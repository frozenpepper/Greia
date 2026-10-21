"""Lifecycle, timing and shared-kit input for Woodland Hide & Seek.

A round happens in one season of Lilli's woodland (meadow, pond, autumn,
snow, in turn). Friends hide behind, under and in things and peek out. The
request banner shows the friend to find (picture + name; the name is spoken
when an approved recording exists) and Lilli points. The child taps a hiding
place:

* right friend -> it pops out and hops over to Lilli, Lilli cheers, and the
  banner shows where it was ("BEHIND THE BUSH");
* someone else -> that friend shows itself and wiggles ("not me"), Lilli
  thinks, and the right place rustles; after a second miss it glows too;
* idle ~6 s -> Lilli points and the right place rustles; later it glows.

After every find everybody hides again in new places, so each request is a
fresh search. Four finds end the round on the shared cast completion scene;
the next round moves to the next season, and the ladder (more places, smaller
and shorter peeks) adapts from the misses of the round.
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
    ControlArt,
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
    from .woodland_art import WoodlandArt
    from .woodland_audio import WoodlandAudio
    from .woodland_content import FINDS_PER_ROUND, FRIEND_IDS, FRIENDS_BY_ID, REFERENCE_HEIGHT, REFERENCE_WIDTH, SEASONS
    from .woodland_controls import ICON_SIZE, WoodlandControls
    from .woodland_layout import FRIEND_SLOTS, LILLI_HEIGHT, SpotGeometry
    from .woodland_model import HideRound, Pick, PickOutcome, adapt_level
    from .woodland_renderer import (
        DUCK_SECONDS,
        HIDDEN_SECONDS,
        HIDE_TOTAL,
        HINT_RISE,
        REVEAL_RISE,
        SHUFFLE_AT,
        Hop,
        LilliCast,
        SceneMotion,
        WoodlandRenderer,
    )
    from .woodland_services import EventPort, ProgressPort, WoodlandProgress
else:
    from woodland_art import WoodlandArt
    from woodland_audio import WoodlandAudio
    from woodland_content import FINDS_PER_ROUND, FRIEND_IDS, FRIENDS_BY_ID, REFERENCE_HEIGHT, REFERENCE_WIDTH, SEASONS
    from woodland_controls import ICON_SIZE, WoodlandControls
    from woodland_layout import FRIEND_SLOTS, LILLI_HEIGHT, SpotGeometry
    from woodland_model import HideRound, Pick, PickOutcome, adapt_level
    from woodland_renderer import (
        DUCK_SECONDS,
        HIDDEN_SECONDS,
        HIDE_TOTAL,
        HINT_RISE,
        REVEAL_RISE,
        SHUFFLE_AT,
        Hop,
        LilliCast,
        SceneMotion,
        WoodlandRenderer,
    )
    from woodland_services import EventPort, ProgressPort, WoodlandProgress

FOUND_PAUSE = 2.0
COMPLETE_DELAY = 0.5
DEMO_DELAY = 0.6
NAME_DELAY = 1.3
REVEAL_SECONDS = 1.1
HINT_SECONDS = 1.5
GLOW_SECONDS = 2.4
MAX_SCHEDULED = 32
FOREST = (40, 81, 58)  # theme text-ink token "forest"


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

    def clear(self) -> None:
        self._entries.clear()


class WoodlandApp:
    """Coordinate the round model, kit controls, art, audio and lifecycle."""

    def __init__(
        self,
        *,
        screen: pygame.Surface,
        canvas: PygameReferenceCanvas,
        typography: GreiaTypography,
        resources: LocalizedResources | None,
        audio: WoodlandAudio,
        progress: ProgressPort,
        events: EventPort,
        rng: random.Random | None = None,
        clock: Callable[[], float] = time.monotonic,
        kit: ControlKit | None = None,
        art: WoodlandArt | None = None,
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
        self._rounds_played = 0

        saved = progress.load()
        self.level = saved.level
        self.season_index = saved.season
        self.stars = saved.stars
        self.friends_met: set[str] = set(saved.friends)

        # Shared control kit (ADR 0037): explore Collection -> leaf accent.
        self.kit = kit if kit is not None else ControlKit(typography, ControlTheme.for_accent("leaf"))
        self.art = art if art is not None else WoodlandArt(art=ControlArt(max_entries=64))
        feedback = CastFeedback("lilli", height=LILLI_HEIGHT, art=self.art.loader, clock=clock)
        self.cast = LilliCast(feedback, self.art, clock)
        self.renderer = WoodlandRenderer(self.art, self.cast)
        self.motion = SceneMotion()
        self.timeline = Timeline(clock)
        self.controls = WoodlandControls(self.kit, on_spot=self._on_spot, on_listen=self._on_listen)
        self._surfaces = SurfaceNavigator(self.controls.layer)
        self._input = PygameControlInput(to_logical=canvas.pointer, is_safe=lambda pos: _safe_point(self.screen, pos))
        self.controls.place_bar(ControlLayout.for_canvas(canvas, screen.get_size()))
        self.audio.prepare_names(friend for friend in FRIEND_IDS if self.audio.has_name(friend))

        self.round: HideRound | None = None
        self.geometry: tuple[SpotGeometry, ...] = ()
        self.completion: PygameCompletionScreen | None = None
        self.state = AppState.PLAYING
        self.session_id = ""
        self._running = True
        self.ready_published = False
        self._dirty = True
        self._activated = False
        self._busy = False
        self._last_activity = clock()
        self._hints = IdleHintScheduler(now=self._last_activity)
        self.start_round()

    # -- main loop ----------------------------------------------------------------

    def run(self) -> int:
        frames = FrameGovernor()
        try:
            while self._running and not activity_stop_requested():
                for event in frames.events():
                    self.handle_event(event)
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
                    if not self.ready_published:
                        mark_activity_ready()
                        self.ready_published = True
                elif frame is FrameKind.POINTER:
                    self.canvas.present_pointer()
                frames.wait(polling=self._input.repeating)
        finally:
            self.persist()
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
        if self.state is not AppState.PLAYING or self.round is None:
            return False
        return self.motion.active(now, self.round.ladder) or self.cast.animating

    def render(self) -> None:
        surface = self.canvas.surface
        if self.state is AppState.PLAYING and self.round is not None:
            self.renderer.draw(
                surface,
                self.round.season,
                self.round.ladder,
                self.geometry,
                self.round.hiding,
                self.round.found,
                self.motion,
                self.clock(),
            )
        self._surfaces.draw(surface)

    def persist(self) -> None:
        self.progress.save(
            WoodlandProgress(
                level=self.level,
                season=self.season_index,
                stars=self.stars,
                friends=tuple(friend for friend in FRIEND_IDS if friend in self.friends_met),
            )
        )

    # -- input --------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self._running = False
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._running = False
            return
        if event.type == pygame.VIDEORESIZE:
            self._resize()
            return
        if event.type in (pygame.MOUSEMOTION, pygame.FINGERMOTION):
            self._dirty = True  # keep the platform pointer live
        translated = self._input.translate(event)
        if translated is not None:
            self._dispatch(translated)

    def _resize(self) -> None:
        self.screen = pygame.display.get_surface() or self.screen
        self.canvas = PygameReferenceCanvas(self.screen, hires=True)
        self._input = PygameControlInput(to_logical=self.canvas.pointer, is_safe=lambda pos: _safe_point(self.screen, pos))
        self.controls.place_bar(ControlLayout.for_canvas(self.canvas, self.screen.get_size()))
        self._dirty = True

    def _dispatch(self, kit_input) -> bool:
        if not isinstance(kit_input, KitPointer) or kit_input.phase is not PointerPhase.MOVE:
            self._note_activity()
        result = self._surfaces.dispatch(kit_input)
        if self.controls.layer.invalidation.should_draw:
            self._dirty = True
        return result is not UiEventResult.IGNORED

    def tap(self, logical: tuple[int, int]) -> bool:
        """Deliver one complete tap at a logical position (tests/tools)."""

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

    # -- round flow -----------------------------------------------------------------

    def start_round(self) -> None:
        now = self.clock()
        self.timeline.clear()
        self.cast.reset()
        season = SEASONS[self.season_index % len(SEASONS)]
        self.round = HideRound(season, self.level, self.rng)
        self.geometry = tuple(SpotGeometry.build(anchor) for anchor in self.round.spots)
        self.motion.reset(len(self.geometry), seed=self.rng.random() * 10.0)
        # Open on the second half of the hide transition: friends rise into view.
        self.motion.hide_everyone(now - DUCK_SECONDS - HIDDEN_SECONDS)
        self.controls.show_round(self.geometry)
        self.controls.set_progress(0)
        self.state = AppState.PLAYING
        self._rounds_played += 1
        self.session_id = f"{self._session_prefix}-{self._rounds_played}-{self.rng.randrange(1_000_000):06d}"
        self._ask()
        self._busy = True
        self.timeline.after(HIDE_TOTAL - DUCK_SECONDS - HIDDEN_SECONDS, self._end_busy)
        self.audio.lilli("ready.go")
        self.timeline.after(NAME_DELAY, self._say_target)
        self.cast.point(1.8)
        self._note_activity()
        self._dirty = True

    def _ask(self) -> None:
        round_ = self.round
        if round_ is None or round_.target is None:
            self.controls.hide_request()
            return
        target = round_.target
        self.controls.ask(
            self.art.full(target, ICON_SIZE),
            self._text(FRIENDS_BY_ID[target].name_key, target),
            voiced=self.audio.has_name(target),
        )

    def _say_target(self) -> None:
        if self.round is not None and self.round.target is not None:
            self.audio.ask_where(self.round.target)  # "Where is the...?" + name

    def _end_busy(self) -> None:
        self._busy = False
        self._note_activity()
        self._dirty = True

    def _on_listen(self) -> None:
        self._activated = True
        self._say_target()
        self.cast.point(1.2)
        self._dirty = True

    def _on_spot(self, index: int) -> None:
        round_ = self.round
        if round_ is None or self.state is not AppState.PLAYING or self._busy:
            return
        outcome = round_.choose(index)
        if outcome.pick is Pick.IGNORED:
            return
        self._activated = True
        if outcome.pick is Pick.FOUND:
            self._found(outcome)
        else:
            self._wrong(outcome)
        self._dirty = True

    def _found(self, outcome: PickOutcome) -> None:
        round_ = self.round
        assert round_ is not None and outcome.friend_id is not None
        now = self.clock()
        geom = self.geometry[outcome.spot]
        friend = outcome.friend_id
        slot = FRIEND_SLOTS[min(len(round_.found), len(FRIEND_SLOTS)) - 1]
        self.motion.add_hop(Hop(friend, now, (geom.center_x, geom.top_y), geom.friend_size, slot))
        self.motion.add_fx("star_burst", geom.peek_point, now)
        self.motion.add_fx("sparkle", (geom.center_x + geom.friend_size // 3, geom.top_y - geom.friend_size // 2), now + 0.15)
        self.audio.play("found")
        self.audio.play("pop")
        if not self.audio.say_name(friend):
            self.audio.lilli("praise.general")
        self.audio.say_place(geom.anchor.kind.kind_id)  # "Behind the bush!" after the name
        self.cast.correct()
        self.controls.tell(self.art.full(friend, ICON_SIZE), self._text(geom.anchor.kind.place_key, ""))
        self.controls.set_progress(len(round_.found))
        self.stars = min(1_000_000, self.stars + 1)
        self.friends_met.add(friend)
        self.persist()
        self.events.friend_found(
            self.session_id,
            {
                "animal": friend,
                "place": geom.anchor.kind.kind_id,
                "relation": geom.anchor.kind.relation.value,
                "season": round_.season.season_id,
                "level": round_.level + 1,
                "found": len(round_.found),
                "total": round_.finds_needed,
                "first_try": outcome.task_misses == 0,
            },
        )
        self._busy = True
        self.timeline.after(FOUND_PAUSE, self._after_found)

    def _after_found(self) -> None:
        round_ = self.round
        if round_ is None:
            return
        if round_.complete:
            self.timeline.after(COMPLETE_DELAY, self._complete)
            return
        now = self.clock()
        self.motion.hide_everyone(now)
        self.audio.play("hide")
        self.timeline.after(SHUFFLE_AT, self._shuffle)
        self.timeline.after(HIDE_TOTAL, self._end_hide)
        self._dirty = True

    def _shuffle(self) -> None:
        round_ = self.round
        if round_ is None:
            return
        now = self.clock()
        round_.hide_again()
        for geom in self.geometry:
            self.motion.add_fx(geom.anchor.kind.rustle_fx, geom.peek_point, now)
        self.audio.play("rustle")
        self._ask()
        self._dirty = True

    def _end_hide(self) -> None:
        self._end_busy()
        self._say_target()
        self.cast.point(1.4)

    def _wrong(self, outcome: PickOutcome) -> None:
        now = self.clock()
        self.motion.reveal(outcome.spot, now, REVEAL_SECONDS, REVEAL_RISE, wobble=True)
        self.audio.play("boing")
        self.cast.try_again()
        if outcome.task_misses % 3 == 0:
            self.audio.lilli("encourage.retry")
        misses = outcome.task_misses
        self.timeline.after(DEMO_DELAY, lambda: self._demonstrate(misses))

    def _demonstrate(self, misses: int) -> None:
        """Show where to look: the right place rustles; after two misses it glows."""

        round_ = self.round
        if round_ is None or self.state is not AppState.PLAYING:
            return
        target = round_.target_spot
        if target is None:
            return
        now = self.clock()
        self.motion.shake(target, now)
        self.audio.play("rustle")
        if misses >= 2:
            self.motion.glow(target, now, GLOW_SECONDS)
            self.motion.reveal(target, now, HINT_SECONDS, HINT_RISE)
            self.timeline.after(1.0, lambda: self.cast.point(1.6))
        self._dirty = True

    def _complete(self) -> None:
        round_ = self.round
        if round_ is None or self.state is not AppState.PLAYING:
            return
        played_level = round_.level
        self.level = adapt_level(round_.level, round_.misses)
        self.season_index = (self.season_index + 1) % len(SEASONS)
        self.persist()
        self.events.round_completed(
            self.session_id,
            {
                "season": round_.season.season_id,
                "level": played_level + 1,
                "found": len(round_.found),
                "misses": round_.misses,
                "first_try": round_.first_try_finds,
            },
        )
        self.audio.play("fanfare")
        self.audio.lilli("celebrate.success")
        self.cast.correct()
        self.completion = PygameCompletionScreen(
            self.typography,
            width=REFERENCE_WIDTH,
            height=REFERENCE_HEIGHT,
            palette=CompletionPalette(background=FOREST),
            scene=CompletionScene(self.kit, character="lilli", star_total=FINDS_PER_ROUND),
        )
        self.completion.prepare(
            CompletionContent(
                title=self._text("victory.title", "★"),
                primary_label=self._text("btn.play_again", "↻"),
                body_lines=(self._text("victory.subtitle", "★"),),
                achievement_count=len(round_.found),
            )
        )
        self._surfaces.push_overlay(CompletionOverlay(self.completion, on_primary=self._restart))
        self.timeline.clear()
        self.state = AppState.TERMINAL
        self._busy = False
        self._dirty = True

    def _restart(self) -> None:
        self._activated = True
        if self.completion is not None:
            self._surfaces.pop_overlay()
            self.completion.clear()
            self.completion = None
        self.start_round()

    # -- hints ----------------------------------------------------------------------

    def _maybe_hint(self, now: float) -> None:
        round_ = self.round
        if round_ is None or self._busy or round_.target_spot is None:
            return
        step = self._hints.poll(now, self._last_activity)
        if not step:
            return
        target = round_.target_spot
        self.cast.point(self._hints.animation_seconds(1.8))
        self.motion.shake(target, now)
        self.motion.reveal(target, now, HINT_SECONDS, HINT_RISE)
        self.audio.play("rustle")
        if step == 1:
            self._say_target()
        else:
            self.motion.glow(target, now, GLOW_SECONDS)
        self._dirty = True

    # -- helpers --------------------------------------------------------------------

    def _text(self, key: str, default: str) -> str:
        if self.resources is None:
            return default
        try:
            return self.resources.text(key) or default
        except Exception:
            return default


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


__all__ = ["AppState", "Timeline", "WoodlandApp"]
