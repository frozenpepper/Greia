"""Application coordinator, lifecycle and input loop for Il Viaggio del Delfino.

One experience, finite journeys: the child picks a course on the journey map
(a sunny bay, a coral reef, a golden lagoon; each opens after the one before
it), steers the dolphin to the finish arch collecting pearls, meets two sea
friends who unlock one of Tito's recorded dolphin facts each, bumps gently
off jellyfish (never a fail), and at the finish watches the pearls counted
into a tray before the shared cast completion scene.

The app owns composition, phases and input routing only: simulation lives in
``delfino_model``, presentation in ``delfino_renderer`` / ``delfino_art``,
controls in ``delfino_controls`` (shared kit, ADR 0037), Tito in
``delfino_cast``, audio in ``delfino_audio`` and platform seams in
``delfino_services``. Collaborators are injectable so the loop runs headless
in tests.
"""

from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum
from pathlib import Path
import random
import time
from typing import Any

import pygame

from greia_platform.activity_api import (
    activity_stop_requested,
    get_profile_locale,
    get_theme,
    mark_activity_ready,
)
from greia_platform.activity_controls import (
    ControlKit,
    ControlLayout,
    ControlTheme,
    KitPointer,
    PointerPhase,
    PygameControlInput,
)
from greia_platform.activity_feedback import IdleHintScheduler
from greia_platform.localization import (
    ActivityLocaleSupport,
    LocalizedResources,
    resolve_activity_locale,
)
from greia_platform.pygame_canvas import (
    PygameReferenceCanvas,
    activity_viewport_for_surface,
)
from greia_platform.pygame_completion import (
    CompletionContent,
    CompletionOverlay,
    CompletionPalette,
    CompletionScene,
    PygameCompletionScreen,
)
from greia_platform.typography import GreiaTypography
from greia_platform.ui_core import SurfaceNavigator, UiEventResult
from greia_platform.frame_governor import FrameGovernor, FrameKind

try:
    from delfino_art import DelfinoArt
    from delfino_audio import PygameDelfinoAudio
    from delfino_cast import DelfinoCast
    from delfino_content import (
        FACT_IDS,
        JOURNEY_IDS,
        JOURNEYS,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        SURFACE_Y,
        WELCOME_CUE_ID,
        JourneySpec,
        journey,
        stars_for,
    )
    from delfino_controls import CONTROL_ACCENT, THUMB_SIZE, PickerControls, SwimHud
    from delfino_input import DolphinSteering, SwimInput
    from delfino_model import EventKind, JourneyEvent, JourneyRun
    from delfino_renderer import SWIM_FX, CountView, DelfinoRenderer, Effect, SwimView
    from delfino_services import GreiaDelfinoEvents, GreiaDelfinoStorage
except ImportError:  # repository/package import context
    from .delfino_art import DelfinoArt
    from .delfino_audio import PygameDelfinoAudio
    from .delfino_cast import DelfinoCast
    from .delfino_content import (
        FACT_IDS,
        JOURNEY_IDS,
        JOURNEYS,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        SURFACE_Y,
        WELCOME_CUE_ID,
        JourneySpec,
        journey,
        stars_for,
    )
    from .delfino_controls import CONTROL_ACCENT, THUMB_SIZE, PickerControls, SwimHud
    from .delfino_input import DolphinSteering, SwimInput
    from .delfino_model import EventKind, JourneyEvent, JourneyRun
    from .delfino_renderer import SWIM_FX, CountView, DelfinoRenderer, Effect, SwimView
    from .delfino_services import GreiaDelfinoEvents, GreiaDelfinoStorage


class Phase(StrEnum):
    PICKER = "picker"
    SWIM = "swim"
    COUNT = "count"
    DONE = "done"


CAST_HEIGHT = 150
CAST_MIDBOTTOM = (76, REFERENCE_HEIGHT)
PICKER_CAST_HEIGHT = 170
#: Graduated help: idle this long → Tito points and the next target pulses.
HINT_SHOW_SECONDS = 2.6
HINT_COOLDOWN_SECONDS = 10.0
#: The wordless steering card stays at least this long with the welcome.
WELCOME_HINT_SECONDS = 6.0
#: The leap card appears when an arc is this close and no leap happened yet.
LEAP_HINT_DISTANCE = 760.0
FINISH_PAUSE_SECONDS = 1.3
KEY_HINT_START_SECONDS = 8.0  # keyboard hint shown at the start of a journey (ADR 0037 §4b)
COUNT_SETTLE_SECONDS = 0.9
TAP_LEAP_SECONDS = 0.3
_MAX_EFFECTS = 12
_COMPLETION_PALETTE = CompletionPalette(background=(26, 74, 120))


def _is_safe_point(surface: pygame.Surface, position: tuple[int, int]) -> bool:
    """Reject pointers outside the Activity or inside Greia's protected chrome."""

    vp = activity_viewport_for_surface(surface)
    x, y = position
    if not (0 <= x < vp.surface.width and 0 <= y < vp.surface.height):
        return False
    for protected in vp.protected_regions:
        if protected.x <= x < protected.right and protected.y <= y < protected.bottom:
            return False
    return True


class DelfinoJourneyApp:
    """Greia Activity application for Il Viaggio del Delfino."""

    # Class-level default so the frame governor's phase check is safe before
    # ``_enter_picker`` (and in partially built test doubles).
    phase: Phase = Phase.PICKER

    def __init__(
        self,
        *,
        rng: random.Random | None = None,
        clock: Callable[[], float] = time.monotonic,
        storage: GreiaDelfinoStorage | None = None,
        events: Any = None,
        audio: Any = None,
        art: DelfinoArt | None = None,
    ) -> None:
        screen = pygame.display.get_surface()
        if screen is None:
            pygame.init()
            screen = pygame.display.set_mode((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.FULLSCREEN)
        self.screen = screen
        self.canvas = PygameReferenceCanvas(screen)
        # The OS cursor is hidden; ``canvas.present()`` draws Greia's pointer.
        pygame.mouse.set_visible(False)
        self._clock = clock
        self._rng = rng if rng is not None else random.Random()

        self._resources: LocalizedResources | None = None
        self._init_localization()
        self.typography = GreiaTypography()
        self.kit = ControlKit(self.typography, ControlTheme.for_accent(CONTROL_ACCENT))
        self.art = art if art is not None else DelfinoArt()
        self.renderer = DelfinoRenderer(self.art, self.kit)

        self.audio = audio if audio is not None else PygameDelfinoAudio()
        if self._resources is not None and hasattr(self.audio, "bind_resources"):
            self.audio.bind_resources(self._resources)
        # Decode every voice cue before the first frame: a cold decode inside
        # the loop would hitch at exactly the celebration moment.
        if hasattr(self.audio, "preload_voice"):
            self.audio.preload_voice([WELCOME_CUE_ID, *FACT_IDS])
        if hasattr(self.audio, "preload_shared"):
            self.audio.preload_shared()
        self.events_service = events if events is not None else GreiaDelfinoEvents()
        self.storage = storage if storage is not None else GreiaDelfinoStorage(journey_ids=JOURNEY_IDS)
        self.progress = self.storage.load()

        self.art.warm_dolphin()
        self.art.warm_thumbnails(THUMB_SIZE)
        self.layout = ControlLayout.for_canvas(self.canvas, screen.get_size())
        self.picker = PickerControls(self.kit, self.art, self._text, self._pick)
        self.hud = SwimHud(self.kit, self.art, self.layout, JOURNEYS[0], clock=clock)
        self.completion = PygameCompletionScreen(
            self.typography,
            palette=_COMPLETION_PALETTE,
            scene=CompletionScene(self.kit, character="tito", star_total=3, primary_glyph="replay", secondary_glyph="go"),
        )
        self.cast = DelfinoCast(self.kit.art, height=CAST_HEIGHT, clock=clock)
        self.picker_cast = DelfinoCast(self.kit.art, height=PICKER_CAST_HEIGHT, clock=clock)
        self._surfaces = SurfaceNavigator(self.picker.layer)
        self._nav_input = self._make_nav_input()
        self.steering = DolphinSteering()

        self.phase = Phase.PICKER
        self.spec: JourneySpec = JOURNEYS[0]
        self.run_state: JourneyRun | None = None
        self._scene = None
        self._effects: list[Effect] = []
        self._running = True
        self._welcomed = False
        self._suggested = self._suggest()
        self._newly_unlocked: str | None = None
        now = clock()
        self._hints = IdleHintScheduler(now=now)
        self._hint_until = 0.0
        self._hint_cooldown = 0.0
        self._steer_hint_until = 0.0
        self._happy_until = 0.0
        self._talk_until = 0.0
        self._miss_streak = 0
        self._demo_pending = False
        self._finish_at = 0.0
        self._count_shown = 0
        self._count_flight = 0.0
        self._count_done_at = 0.0
        self._touch_start: tuple[float, tuple[int, int]] | None = None
        self._last_result: tuple[int, int] = (0, 0)
        self._sync_picker()

    # -------------------------------------------------------- localization

    def _init_localization(self) -> None:
        package_root = Path(__file__).parent
        support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it")
        try:
            context = resolve_activity_locale(get_profile_locale(), support)
            self._resources = LocalizedResources(package_root, context) if context else None
        except Exception:
            self._resources = None

    def _text(self, key: str, variables: dict[str, object] | None = None) -> str:
        if self._resources is not None:
            try:
                return self._resources.text(key, variables)
            except Exception:
                pass
        return ""

    # ------------------------------------------------------------- picker

    def _suggest(self) -> str:
        """The first open journey not yet finished (else the last open one)."""

        unlocked = self.progress.unlocked(JOURNEY_IDS)
        for journey_id in unlocked:
            if not self.progress.record(journey_id).done:
                return journey_id
        return unlocked[-1] if unlocked else JOURNEY_IDS[0]

    def _sync_picker(self) -> None:
        self.picker.sync(self.progress.unlocked(JOURNEY_IDS), self._suggested)

    def _enter_picker(self) -> None:
        self.phase = Phase.PICKER
        self._suggested = self._suggest()
        self._sync_picker()
        self._surfaces.replace(self.picker.layer)
        self.audio.stop_voice()
        self.picker_cast.present(True)
        self.cast.present(False)
        now = self._clock()
        self._hints.reset(now)
        if self._newly_unlocked is not None:
            # A new journey just opened: celebrate it on its card.
            rect = self.picker.rect(self._newly_unlocked)
            self._add_fx("star_burst", rect.center, 200, screen=True)
            self.picker_cast.cheer()
            self.audio.play("victory")
            self._newly_unlocked = None
        else:
            self.picker_cast.wave()

    def _pick(self, journey_id: str) -> None:
        if journey_id not in self.progress.unlocked(JOURNEY_IDS):
            self._locked_tap()
            return
        self.audio.play("pop")
        self.start_journey(journey_id)

    def _locked_tap(self) -> None:
        """Kind response to a closed card: Tito thinks, the open card sparkles."""

        self.picker_cast.think()
        self.audio.play("boing")
        self.picker.layer.focus(f"journey.{self._suggested}")

    # -------------------------------------------------------------- journey

    def start_journey(self, journey_id: str) -> None:
        self.spec = journey(journey_id)
        self.run_state = JourneyRun.start(self.spec, self._rng)
        self.art.warm_journey(self.spec, SWIM_FX)
        self._scene = self.art.scene(self.spec.look)
        self.hud.set_journey(self.spec)
        self.hud.relayout(self.layout)
        self.completion.clear()
        self._surfaces.replace(self.hud.layer)
        self.phase = Phase.SWIM
        self.hud.keys.show(KEY_HINT_START_SECONDS)
        self.steering.reset()
        self._effects.clear()
        self._miss_streak = 0
        self._demo_pending = False
        self._touch_start = None
        self.picker_cast.present(False)
        now = self._clock()
        self._hints.reset(now)
        self._hint_until = 0.0
        self._happy_until = 0.0
        if not self._welcomed:
            # Tito's spoken goal once per launch, with the wordless how-to.
            self._welcomed = True
            duration = self.audio.play_voice(WELCOME_CUE_ID)
            self._talk(duration)
            self._steer_hint_until = now + max(WELCOME_HINT_SECONDS, duration)
        else:
            self._talk(self.audio.say("ready.go"))
            self._steer_hint_until = now + 3.0

    def _talk(self, duration: float) -> None:
        seconds = max(1.2, float(duration))
        self.cast.talk(seconds)
        self._talk_until = self._clock() + seconds

    def leap(self) -> None:
        if self.run_state is not None and self.run_state.leap():
            self.audio.play("whoosh")

    def _handle_world_event(self, event: JourneyEvent) -> None:
        run = self.run_state
        assert run is not None
        now = self._clock()
        kind = event.kind
        if kind is EventKind.PEARL:
            self.audio.play("pearl")
            self._add_fx("sparkle", (event.x, event.y), 74)
            self._happy_until = max(self._happy_until, now + 0.5)
            self.hud.set_pearls(run.collected)
        elif kind is EventKind.GROUP_COMPLETE:
            self._miss_streak = 0
            self.audio.play("star")
            self._add_fx("star_burst", (run.dolphin.x + 40, run.dolphin.y - 30), 130)
            self._happy_until = now + 1.0
        elif kind is EventKind.GROUP_MISSED:
            self._miss_streak += 1
            self._after_miss(event, now)
        elif kind in (EventKind.SPLASH_OUT, EventKind.SPLASH_IN):
            self.audio.play("splash")
            self._add_fx("splash", (event.x + 30, SURFACE_Y - 26), 120)
        elif kind is EventKind.BUMP:
            self.audio.play("boing")
            self._add_fx("bubble_pop", (event.x, event.y), 100)
        elif kind is EventKind.FRIEND_WAITING:
            self.audio.play("pop")
        elif kind is EventKind.FRIEND_MET:
            self._meet_friend(event)
        elif kind is EventKind.STRETCH:
            self.hud.set_progress(run.stretches_passed)
        elif kind is EventKind.FINISHED:
            self.hud.set_progress(run.stretches_passed)
            self.audio.play("victory")
            self._add_fx("confetti", (run.dolphin.x + 60, run.dolphin.y - 60), 220)
            self.cast.cheer()
            self._finish_at = now
            self._happy_until = now + 30.0

    def _after_miss(self, event: JourneyEvent, now: float) -> None:
        """Graduated help after a missed group: demonstrate where to go."""

        if now < self._talk_until:
            return
        self.cast.think()
        self._talk_until = now + max(1.0, self.audio.say("encourage.retry"))
        # Demonstrate as soon as the next pearls come into view.
        self._demo_pending = True
        self._hint_cooldown = now + HINT_COOLDOWN_SECONDS

    def _meet_friend(self, event: JourneyEvent) -> None:
        run = self.run_state
        assert run is not None
        friend = next((f for f in run.course.friends if f.spec.friend_id == event.ref), None)
        if friend is None:
            return
        self.audio.play("star")
        self._add_fx("heart_pop", (event.x, event.y - 40), 130)
        self._happy_until = self._clock() + 1.5
        self._hint_until = 0.0
        duration = self.audio.play_voice(friend.spec.fact_id)
        self._talk(duration if duration > 0 else 4.0)
        self.events_service.fact_opened(friend.spec.fact_id)

    def _add_fx(self, fx_id: str, at: tuple[float, float], size: int, *, screen: bool = False) -> None:
        frames = self.art.fx_frames(fx_id, size)
        if not frames:
            return
        self._effects.append(Effect(frames, float(at[0]), float(at[1]), screen=screen))
        del self._effects[:-_MAX_EFFECTS]

    # ---------------------------------------------------------- per frame

    def advance(self, dt: float) -> None:
        now = self._clock()
        for effect in self._effects:
            effect.age += dt
        self._effects = [effect for effect in self._effects if not effect.done]
        repeat = self._nav_input.poll() if self.phase in (Phase.PICKER, Phase.DONE) else None
        if repeat is not None:
            self._surfaces.dispatch(repeat)
        if self.phase is Phase.PICKER:
            self._advance_picker(now)
        elif self.phase is Phase.SWIM:
            self._advance_swim(dt, now)
        elif self.phase is Phase.COUNT:
            self._advance_count(dt, now)
        self.cast.update(dt)
        self.picker_cast.update(dt)

    def _advance_picker(self, now: float) -> None:
        if self._hints.poll(now):
            self.picker_cast.point(self._hints.animation_seconds(self.picker_cast.POINT_SECONDS))

    def _advance_swim(self, dt: float, now: float) -> None:
        run = self.run_state
        assert run is not None
        self.hud.keys.update()  # swimming redraws every frame
        if self.steering.active:
            run.dolphin.steer(self.steering.step(dt))
            self._hints.reset(now)  # a held key or stick is input too
        for event in run.update(dt):
            self._handle_world_event(event)
        if run.finished:
            if now - self._finish_at >= FINISH_PAUSE_SECONDS:
                self._begin_count()
            return
        if self._demo_pending:
            self._maybe_demonstrate(run, now)
        self._maybe_idle_hint(run, now)

    def _maybe_demonstrate(self, run: JourneyRun, now: float) -> None:
        """After a miss: Tito points and the next pearls pulse once visible."""

        target = run.next_target()
        if target is None:
            self._demo_pending = False
            return
        if target[0] - run.camera_x > REFERENCE_WIDTH - 60:
            return
        self._demo_pending = False
        self.cast.point()
        self._hint_until = now + HINT_SHOW_SECONDS + 0.8

    def _maybe_idle_hint(self, run: JourneyRun, now: float) -> None:
        if now < self._hint_cooldown or now < self._talk_until:
            return
        if not self._hints.is_due(now):
            return
        target = run.next_target()
        if target is None or abs(target[0] - run.dolphin.x) > 760.0:
            return
        if abs(target[1] - run.dolphin.y) < 60.0:
            return
        self._hints.fire(now)
        self.hud.keys.demonstrate()
        show = self._hints.animation_seconds(HINT_SHOW_SECONDS)
        self.cast.point(self._hints.animation_seconds(self.cast.POINT_SECONDS))
        self._hint_until = now + show
        self._steer_hint_until = max(self._steer_hint_until, now + show + 0.6)

    def _leap_hint(self, run: JourneyRun) -> bool:
        if run.leaps > 0 or run.finished:
            return False
        x = run.dolphin.x
        return any(
            group.arc and not group.resolved and 0.0 <= group.start_x - x <= LEAP_HINT_DISTANCE
            for group in run.course.groups
        )

    # --------------------------------------------------------------- count

    def _begin_count(self) -> None:
        run = self.run_state
        assert run is not None
        self.phase = Phase.COUNT
        self.hud.keys.hide()
        self._count_shown = 0
        self._count_flight = 0.0
        self._count_done_at = 0.0
        self.hud.show_count(0)
        self._effects.clear()

    def _count_step_seconds(self) -> float:
        total = self.run_state.collected if self.run_state is not None else 0
        return max(0.13, min(0.26, 3.6 / max(1, total)))

    def _advance_count(self, dt: float, now: float) -> None:
        run = self.run_state
        assert run is not None
        run.update(dt)  # the finished world keeps breathing (bob, jellies, friend)
        total = run.collected
        if self._count_shown < total:
            self._count_flight += dt / self._count_step_seconds()
            if self._count_flight >= 1.0:
                self._count_flight = 0.0
                self._count_shown += 1
                self.audio.play_count((self._count_shown - 1) % 10)
                self.hud.show_count(self._count_shown)
            return
        if self._count_done_at == 0.0:
            self._count_done_at = now
            if total:
                self._add_fx("star_burst", self.hud.count.rect.center, 150, screen=True)
        elif now - self._count_done_at >= COUNT_SETTLE_SECONDS:
            self._complete()

    def _skip_count(self) -> None:
        run = self.run_state
        if run is None or self._count_shown >= run.collected:
            return
        self._count_shown = run.collected
        self._count_flight = 0.0
        self.hud.show_count(self._count_shown)

    def _complete(self) -> None:
        run = self.run_state
        assert run is not None
        pearls = run.collected
        stars = stars_for(pearls, run.course.total_pearls)
        before = self.progress.unlocked(JOURNEY_IDS)
        self.progress = self.progress.with_result(self.spec.journey_id, pearls, stars)
        after = self.progress.unlocked(JOURNEY_IDS)
        opened = [journey_id for journey_id in after if journey_id not in before]
        self._newly_unlocked = opened[0] if opened else None
        self.storage.save(self.progress)
        self._last_result = (pearls, stars)
        self.events_service.chapter_completed(JOURNEY_IDS.index(self.spec.journey_id) + 1)
        self.events_service.journey_score(pearls)
        self._prepare_completion(pearls, stars)
        self.audio.say("praise.general")
        self.phase = Phase.DONE
        self.hud.show_count(None)

    def _prepare_completion(self, pearls: int, stars: int) -> None:
        title = self._text("completion.title")
        replay = self._text("completion.replay")
        journeys = self._text("completion.journeys")
        body = self._text("completion.body", {"count": pearls})
        self.completion.prepare(
            CompletionContent(
                title=title or "★",
                primary_label=replay or "↻",
                body_lines=(body,) if body else (),
                achievement_count=stars,
                secondary_label=journeys or "→",
            )
        )
        self._surfaces.push_overlay(
            CompletionOverlay(self.completion, on_primary=self._replay, on_secondary=self._enter_picker)
        )

    def _replay(self) -> None:
        self.start_journey(self.spec.journey_id)

    # ---------------------------------------------------------------- draw

    def draw(self) -> None:
        surface = self.canvas.surface
        now = self._clock()
        if self.phase is Phase.PICKER:
            records = {journey_id: self.progress.record(journey_id).best_stars for journey_id in JOURNEY_IDS}
            self.renderer.draw_picker(
                surface, self.picker, records, self.progress.unlocked(JOURNEY_IDS), self._suggested, now
            )
            self._surfaces.draw(surface)
            for effect in self._effects:
                effect.draw(surface, 0.0)
            self.picker_cast.draw(surface, (96, REFERENCE_HEIGHT))
            return
        if self.phase is Phase.DONE:
            self._surfaces.draw(surface)
            return
        run = self.run_state
        assert run is not None and self._scene is not None
        view = SwimView(
            now=now,
            happy=now < self._happy_until,
            hint_target=run.next_target() if now < self._hint_until and self.phase is Phase.SWIM else None,
            steer_hint=self.phase is Phase.SWIM and now < self._steer_hint_until,
            leap_hint=self.phase is Phase.SWIM and self._leap_hint(run),
            effects=self._effects,
        )
        self.renderer.draw_swim(surface, run, self._scene, view)
        if self.phase is Phase.SWIM:
            self.hud.draw_keys(surface)
        if self.phase is Phase.COUNT:
            self.renderer.draw_count(
                surface,
                CountView(run.collected, self._count_shown, self._count_flight),
                self.hud.pearls.rect.center,
            )
        self._surfaces.draw(surface)
        self.cast.draw(surface, CAST_MIDBOTTOM)

    @staticmethod
    def _present_frame(canvas: PygameReferenceCanvas, theme) -> None:
        """Present one frame. The OS cursor is hidden, so the canvas draws Greia's
        platform pointer (``present(pointer=True)``); never pass ``pointer=False``."""
        canvas.present(clear=theme.background)
        pygame.display.flip()

    # ------------------------------------------------------------ lifecycle

    def run(self) -> int:
        # Swimming and counting animate; the picker and finale are ambient.
        frames = FrameGovernor(redraw_on_input=True)
        theme = get_theme()
        self._enter_picker()
        ready_published = False
        previous = time.monotonic()
        while self._running and not activity_stop_requested():
            now = time.monotonic()
            dt = min(0.1, max(0.001, now - previous))
            previous = now
            for event in frames.events():
                self.handle_event(event)
                if not self._running:
                    break
            if not self._running:
                break
            self.advance(dt)
            frame = frames.frame(animating=self.phase in (Phase.SWIM, Phase.COUNT), ambient=True)
            if frame is FrameKind.FULL:
                self.draw()
                # VIDEORESIZE replaces self.canvas inside the event owner; always
                # present the current canvas, never a stale local.
                self._present_frame(self.canvas, theme)
                if not ready_published:
                    mark_activity_ready()
                    ready_published = True
            elif frame is FrameKind.POINTER:
                self.canvas.present_pointer()
            frames.wait()
        self.shutdown()
        pygame.quit()
        return 0

    def shutdown(self) -> None:
        self.events_service.close()
        self.audio.shutdown()

    # ------------------------------------------------------------------ input

    def _make_nav_input(self) -> PygameControlInput:
        return PygameControlInput(to_logical=self.canvas.pointer, is_safe=lambda p: _is_safe_point(self.screen, p))

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self._running = False
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._running = False
            return
        if event.type == pygame.VIDEORESIZE:
            self._handle_resize()
            return
        if event.type == getattr(pygame, "WINDOWFOCUSLOST", -1):
            self.steering.reset()
            return
        if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION) and getattr(event, "touch", False):
            # SDL mirrors touch as synthetic mouse input; the FINGER* event is used.
            return
        if self.phase is Phase.SWIM:
            self._handle_swim_event(event)
        elif self.phase is Phase.COUNT:
            self._handle_count_event(event)
        else:
            self._handle_nav_event(event)

    def _handle_resize(self) -> None:
        new_screen = pygame.display.get_surface()
        if new_screen is None:
            return
        self.screen = new_screen
        self.canvas = PygameReferenceCanvas(new_screen)
        self._nav_input = self._make_nav_input()
        self.layout = ControlLayout.for_canvas(self.canvas, new_screen.get_size())
        self.hud.relayout(self.layout)
        self.steering.reset()

    def _logical(self, position: tuple[int, int]) -> tuple[int, int] | None:
        if not _is_safe_point(self.screen, position):
            return None
        logical = self.canvas.pointer(position)
        if logical is None:
            return None
        return (int(logical[0]), int(logical[1]))

    def _finger_position(self, event: pygame.event.Event) -> tuple[int, int]:
        width, height = self.screen.get_size()
        return (int(event.x * width), int(event.y * height))

    def _handle_swim_event(self, event: pygame.event.Event) -> None:
        run = self.run_state
        if run is None:
            return
        self.hud.keys.observe_event(event)
        meaning = self.steering.handle(event)
        if meaning is SwimInput.LEAP:
            self._hints.reset(self._clock())
            self.leap()
            return
        if meaning is SwimInput.STEER:
            self._hints.reset(self._clock())
            return
        if event.type == pygame.MOUSEMOTION:
            logical = self._logical(event.pos)
            if logical is not None:
                run.dolphin.aim(logical[1])
                self._hints.reset(self._clock())
        elif event.type == pygame.MOUSEBUTTONDOWN and getattr(event, "button", 1) == 1:
            if self._logical(event.pos) is not None:
                self._hints.reset(self._clock())
                self.leap()
        elif event.type == pygame.FINGERDOWN:
            position = self._finger_position(event)
            logical = self._logical(position)
            if logical is not None:
                self._touch_start = (self._clock(), position)
                run.dolphin.aim(logical[1])
                self._hints.reset(self._clock())
        elif event.type == pygame.FINGERMOTION:
            logical = self._logical(self._finger_position(event))
            if logical is not None:
                run.dolphin.aim(logical[1])
                self._hints.reset(self._clock())
        elif event.type == pygame.FINGERUP:
            start, self._touch_start = self._touch_start, None
            if start is None:
                return
            began, origin = start
            position = self._finger_position(event)
            moved = abs(position[0] - origin[0]) + abs(position[1] - origin[1])
            if self._clock() - began <= TAP_LEAP_SECONDS and moved <= 24:
                self.leap()

    def _handle_count_event(self, event: pygame.event.Event) -> None:
        meaning = self.steering.handle(event)
        if meaning is SwimInput.LEAP or (
            event.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN)
        ):
            self._skip_count()

    def _handle_nav_event(self, event: pygame.event.Event) -> None:
        kit_input: Any = None
        if event.type in (pygame.FINGERDOWN, pygame.FINGERUP, pygame.FINGERMOTION):
            phase = {
                pygame.FINGERDOWN: PointerPhase.DOWN,
                pygame.FINGERUP: PointerPhase.UP,
                pygame.FINGERMOTION: PointerPhase.MOVE,
            }[event.type]
            logical = self._logical(self._finger_position(event))
            if logical is None:
                kit_input = KitPointer(PointerPhase.CANCEL, (-1, -1)) if phase is PointerPhase.UP else None
            else:
                kit_input = KitPointer(phase, logical)
        else:
            kit_input = self._nav_input.translate(event)
        if kit_input is None:
            return
        self._route(kit_input)

    def _route(self, kit_input: Any) -> None:
        if self.phase is Phase.PICKER and not (isinstance(kit_input, KitPointer) and kit_input.phase is PointerPhase.MOVE):
            self._hints.reset(self._clock())
        result = self._surfaces.dispatch(kit_input)
        if (
            self.phase is Phase.PICKER
            and result is UiEventResult.IGNORED
            and isinstance(kit_input, KitPointer)
            and kit_input.phase is PointerPhase.DOWN
        ):
            journey_id = self.picker.card_at(kit_input.position)
            if journey_id is not None and journey_id not in self.progress.unlocked(JOURNEY_IDS):
                self._locked_tap()

    def tap(self, position: tuple[int, int]) -> None:
        """Deliver one complete tap at a physical position (touch, tools, tests)."""

        for phase in (PointerPhase.DOWN, PointerPhase.UP):
            logical = self._logical(position)
            kit_input = KitPointer(phase, logical) if logical is not None else KitPointer(PointerPhase.CANCEL, (-1, -1))
            if self.phase is Phase.SWIM:
                if phase is PointerPhase.DOWN and logical is not None:
                    self.leap()
            elif self.phase is Phase.COUNT:
                if phase is PointerPhase.DOWN:
                    self._skip_count()
            else:
                self._route(kit_input)


def main() -> int:
    app = DelfinoJourneyApp()
    return app.run()


if __name__ == "__main__":
    raise SystemExit(main())
