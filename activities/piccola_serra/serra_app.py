"""Lifecycle, input and the moment-by-moment timeline of Piccola Serra.

One visit is three plants. For each plant:

1. **Choose** -- four seed packets (bean, sunflower, strawberry, carrot) each
   show the grown plant; Tito says "ready, go". The chosen seed drops into
   the pot.
2. **Grow** -- every stage shows one need and the child picks the care:
   dry cracked soil + droopy dull plant -> water; shade cloth down + pale
   plant leaning to the window -> sun (the cloth rolls up); water standing
   on the soil -> wait (the clock ticks, it dries); fruit/seeds/root ready
   -> harvest. Nothing names the answer. A care that does not help is shown
   honestly (the can pours, the sun already shines ...), then Tito thinks
   and the real cue glows (demonstrate); after a second miss the right tool
   glows too. Right care: the cue clears, the plant grows to its next stage
   (seed -> sprout -> young -> flower -> fruit), Tito cheers.
3. **Order** -- after the harvest flies into the basket, the plant's stage
   pictures are shuffled in the bottom row; the child taps the one that
   comes next (3, 4 or 5 cards by rung). A card that is not next: Tito
   thinks and the next empty slot glows; after two, the right card glows.

Idle ~6 s: Tito points and the cue glows; later the tool/card glows. After
three plants the shared cast completion scene appears; the rung for the next
visit adapts from this visit's misses. Nothing is timed.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from enum import StrEnum
import math
import time
from uuid import uuid4

import pygame

from greia_platform.activity_api import activity_stop_requested, mark_activity_ready
from greia_platform.frame_governor import FrameGovernor, FrameKind
from greia_platform.activity_controls import ControlKit, ControlLayout, ControlTheme, PygameControlInput
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
from greia_platform.ui_core import SurfaceNavigator

if __package__:
    from .serra_art import SerraArt, variant_for
    from .serra_audio import SerraAudio
    from .serra_content import CURE, TITO, Care, Need, Stage
    from .serra_controls import SerraControls
    from .serra_layout import (
        BASKET_MIDBOTTOM,
        FRUIT_SPOT,
        PLANT_BASE,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        SOIL_CENTER,
        TITO_HEIGHT,
    )
    from .serra_model import CareResult, Phase, Place, Verdict, Visit
    from .serra_renderer import Flight, PlantView, SceneView, SerraMotion, SerraRenderer, TitoCast
    from .serra_services import EventPort, ProgressPort
else:
    from serra_art import SerraArt, variant_for
    from serra_audio import SerraAudio
    from serra_content import CURE, TITO, Care, Need, Stage
    from serra_controls import SerraControls
    from serra_layout import (
        BASKET_MIDBOTTOM,
        FRUIT_SPOT,
        PLANT_BASE,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        SOIL_CENTER,
        TITO_HEIGHT,
    )
    from serra_model import CareResult, Phase, Place, Verdict, Visit
    from serra_renderer import Flight, PlantView, SceneView, SerraMotion, SerraRenderer, TitoCast
    from serra_services import EventPort, ProgressPort

IDLE_HINT_SECONDS = 6.0
MAX_IDLE_HINTS = 4
RETRY_VOICE_GAP = 8.0
MAX_SCHEDULED = 32
NEED_SETTLE = 0.6
GROW_SETTLE = 0.8
TRY_SECONDS = 0.8
PLANT_DONE_SECONDS = 2.2
CHEER_SECONDS = 1.1
DIGIT_KEYS = (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5)
COMPLETION_DUSK = (40, 84, 60)


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
        for entry in due:
            self._entries.remove(entry)
        for _, action in sorted(due, key=lambda entry: entry[0]):
            action()
        return bool(due)

    @property
    def busy(self) -> bool:
        return bool(self._entries)

    def clear(self) -> None:
        self._entries.clear()


class SerraActivity:
    """Coordinate the greenhouse model, kit controls, art, voice and lifecycle."""

    def __init__(
        self,
        *,
        screen: pygame.Surface,
        canvas: PygameReferenceCanvas,
        visit: Visit,
        typography: GreiaTypography,
        resources: LocalizedResources | None,
        audio: SerraAudio,
        progress: ProgressPort,
        events: EventPort,
        clock: Callable[[], float] = time.monotonic,
        kit: ControlKit | None = None,
        art: SerraArt | None = None,
    ) -> None:
        self.screen = screen
        self.canvas = canvas
        self.visit = visit
        self.typography = typography
        self.resources = resources
        self.audio = audio
        self.progress = progress
        self.events = events
        self.clock = clock
        self._visit_id = uuid4().hex

        # Shared control kit (ADR 0037): explore Collection -> leaf accent.
        self.kit = kit if kit is not None else ControlKit(typography, ControlTheme.for_accent("leaf"))
        self.art = art if art is not None else SerraArt(self.kit)
        self.controls = SerraControls(
            self.kit,
            self.art,
            ControlLayout.for_canvas(canvas, screen.get_size()),
            visit.total,
            on_hint=self._on_hint,
            on_seed=self._on_seed,
            on_care=self._on_care,
            on_card=self._on_card,
        )
        self._surfaces = SurfaceNavigator(self.controls.layer)
        self._input = self._make_input()
        self.timeline = Timeline(clock)
        self.motion = SerraMotion()
        self.view = SceneView()
        feedback = CastFeedback(TITO, height=TITO_HEIGHT, art=self.art.art, idle_variant="happy", hold_seconds=CHEER_SECONDS, clock=clock)
        self.cast = TitoCast(feedback, self.art.cast_pose("pose_point", TITO_HEIGHT), clock)
        self.renderer = SerraRenderer(self.art, self.cast)
        self.renderer.board_rect = self.controls.board
        self.completion: PygameCompletionScreen | None = None
        self.state = AppState.PLAYING
        self.busy = False
        self._running = True
        self._ready_published = False
        self._activated = False
        self._last_activity = clock()
        self._idle_hints = 0
        self._help_presses = 0
        self._last_retry_voice = -100.0
        self._start_choose()

    # -- main loop --------------------------------------------------------------

    def run(self) -> int:
        # Input redraws; timed greenhouse effects run as ambient motion.
        frames = FrameGovernor(redraw_on_input=True)
        try:
            while self._running and not activity_stop_requested():
                for event in frames.events():
                    self.handle_event(event)
                repeat = self._input.poll()
                if repeat is not None:
                    self._surfaces.dispatch(repeat)
                self.step()
                frame = frames.frame(animating=self.motion.busy(self.clock()), ambient=True)
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
            self.progress.save(self.visit.progress)
            self.typography.clear()
        return 0

    def step(self) -> None:
        now = self.clock()
        self.timeline.run_due()
        self.motion.land_due(now)
        self.cast.update()
        if self.state is AppState.PLAYING:
            self._maybe_hint(now)

    def render(self) -> None:
        surface = self.canvas.surface
        now = self.clock()
        if self.state is not AppState.TERMINAL:
            self.renderer.draw(surface, self.view, self.motion, now)
            self._tool_halo(surface, now)
        self._surfaces.draw(surface)

    def _tool_halo(self, surface: pygame.Surface, now: float) -> None:
        if self.motion.tool is None:
            return
        control_id, begin = self.motion.tool
        if not 0 <= now - begin < 2.6:
            return
        tile = self.controls.tile(control_id)
        if tile is None or not tile.visible:
            return
        rect = tile.rect
        halo = self.art.halo((rect.width + 34, rect.height + 34))
        pulse = 0.55 + 0.45 * math.sin((now - begin) * 2 * math.pi / 0.9)
        halo.set_alpha(int(255 * pulse))
        surface.blit(halo, halo.get_rect(center=rect.center))
        halo.set_alpha(255)

    # -- input --------------------------------------------------------------------

    def _make_input(self) -> PygameControlInput:
        return PygameControlInput(to_logical=self.canvas.pointer, is_safe=lambda pos: _safe_point(self.screen, pos))

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
        if event.type == pygame.KEYDOWN and event.key in DIGIT_KEYS and self.state is AppState.PLAYING:
            # Number keys pick the n-th tile of the row (a keyboard shortcut).
            ids = self.controls.row_ids()
            index = DIGIT_KEYS.index(event.key)
            if index < len(ids):
                tile = self.controls.tile(ids[index])
                if tile is not None and tile.visible:
                    self._note_activity()
                    self._activated = tile.activate() or self._activated
            return
        translated = self._input.translate(event)
        if translated is None:
            return
        if event.type != pygame.MOUSEMOTION:
            self._note_activity()
        self._surfaces.dispatch(translated)

    def tap(self, raw_pos: tuple[int, int]) -> bool:
        """Deliver one full tap at a physical position (tests/tools)."""

        self._activated = False
        for event_type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            self.handle_event(pygame.event.Event(event_type, pos=raw_pos, button=1))
        return self._activated

    def press(self, key: int) -> bool:
        """Deliver one key press + release (tests/tools); True when something acted."""

        self._activated = False
        for event_type in (pygame.KEYDOWN, pygame.KEYUP):
            self.handle_event(pygame.event.Event(event_type, key=key, mod=0, unicode="", scancode=0))
        return self._activated

    def physical_center(self, control_id: str) -> tuple[int, int] | None:
        """Screen position of a kit tile (tests/tools)."""

        tile = self.controls.tile(control_id)
        if tile is None:
            return None
        return self.canvas.mapper.point(*tile.rect.center)

    def _note_activity(self) -> None:
        self._last_activity = self.clock()
        self._idle_hints = 0

    def _relayout(self) -> None:
        self.screen = pygame.display.get_surface() or self.screen
        self.canvas = PygameReferenceCanvas(self.screen)
        self._input = self._make_input()
        self.controls.relayout(ControlLayout.for_canvas(self.canvas, self.screen.get_size()))
        self.renderer.board_rect = self.controls.board
        if self.completion is not None:
            self.completion.clear()
            self._prepare_completion()

    # -- choose -------------------------------------------------------------------------

    def _start_choose(self) -> None:
        now = self.clock()
        self.timeline.clear()
        self.motion.clear()
        view = self.view
        view.board = False
        view.previous = None
        view.plant = PlantView()
        view.overlay_previous = None
        view.cloth.to(0.0, now, 0.6)
        self.controls.show_seeds()
        self.controls.focus_first()
        self.controls.sync_progress(self.visit.completed)
        self.cast.point(1.6)
        self.audio.say("start")
        self.busy = False
        self._help_presses = 0
        self._note_activity()

    def _on_seed(self, plant_id: str) -> None:
        if self.busy or self.visit.phase is not Phase.CHOOSE:
            return
        cycle = self.visit.choose(plant_id)
        if cycle is None:
            return
        self._activated = True
        self.busy = True
        self.events.seed_planted(self._visit_id, self.visit.completed + 1, plant_id)
        self.audio.play("seed")
        now = self.clock()
        # The packet hops from its tile to the pot; the seed appears in the soil.
        packet = self.art.packet(plant_id, 96)
        start = self._tile_center(f"seed.{plant_id}")
        self.motion.fly(Flight(packet, start, (SOIL_CENTER[0], SOIL_CENTER[1] - 40), now, 0.6, 140, self._seed_landed))

    def _seed_landed(self) -> None:
        cycle = self.visit.cycle
        if cycle is None:
            return
        now = self.clock()
        self._swap_plant(PlantView(cycle.plant.plant_id, Stage.SEED), now)
        self.view.plant_hop = now
        self.motion.add_fx("dust_puff", SOIL_CENTER, now, 120)
        self.audio.play("seed")
        self.controls.show_cares(self.visit.rung.cares)
        self.controls.focus_first()
        self.timeline.after(0.45, self._present_need)

    # -- grow ---------------------------------------------------------------------------

    def _present_need(self) -> None:
        cycle = self.visit.cycle
        if cycle is None or cycle.need is None:
            return
        now = self.clock()
        need = cycle.need
        stage = cycle.stage
        look = PlantView(cycle.plant.plant_id, stage, variant_for(stage, need), need if need in (Need.THIRSTY, Need.SOGGY) else None)
        self._swap_plant(look, now)
        if need is Need.DARK:
            self.view.cloth.to(1.0, now, 0.8)
            self.audio.play("cloth")
        elif need is Need.SOGGY:
            self.audio.play("drip")
        elif need is Need.RIPE:
            self.motion.add_fx("sparkle", FRUIT_SPOT, now, 150)
        self.timeline.after(NEED_SETTLE, self._ready_for_care)

    def _ready_for_care(self) -> None:
        self.busy = False
        self._note_activity()

    def _on_care(self, care: Care) -> None:
        if self.busy or self.visit.phase is not Phase.GROW:
            return
        result = self.visit.care(care)
        if result is None:
            return
        self._activated = True
        self.busy = True
        self.motion.tool = None
        self.motion.symptom = None
        if result.verdict is Verdict.NOT_YET:
            self._try_again(result)
        elif result.verdict is Verdict.GREW:
            self._cure(result)
        elif result.verdict is Verdict.HARVESTED:
            self._harvest(result)
        else:
            self.busy = False

    def _show_care(self, care: Care, now: float, *, short: bool = False) -> float:
        """Play what a care does; returns how long the moment takes."""

        if care is Care.WATER:
            self.motion.pour = now
            self.motion.pour_seconds = 0.8 if short else 1.1
            self.audio.play("water")
            return self.motion.pour_seconds
        if care is Care.SUN:
            self.motion.sun = now
            self.audio.play("sun")
            return 0.8
        if care is Care.WAIT:
            self.motion.clock = now
            self.audio.play("wait")
            return 1.2
        self.motion.basket_shake = now
        self.audio.play("not_yet")
        return 0.6

    def _cure(self, result: CareResult) -> None:
        now = self.clock()
        cycle = self.visit.cycle
        assert cycle is not None
        seconds = self._show_care(result.care, now)
        if result.care is Care.SUN:
            self.view.cloth.to(0.0, now, 0.8)
            self.audio.play("cloth")
        plant_id = cycle.plant.plant_id
        healthy = PlantView(plant_id, result.previous, "default", None)
        self.timeline.after(seconds * 0.6, lambda: self._swap_plant(healthy, self.clock()))
        self.timeline.after(seconds + 0.35, lambda: self._grow(plant_id, result.stage))

    def _grow(self, plant_id: str, stage: Stage) -> None:
        now = self.clock()
        self._swap_plant(PlantView(plant_id, stage), now)
        self.view.plant_hop = now
        self.cast.correct()
        self.audio.play("grow")
        top = (PLANT_BASE[0], PLANT_BASE[1] - _plant_height(stage))
        self.motion.add_fx("bloom" if stage in (Stage.FLOWER, Stage.FRUIT) else "sparkle", top, now, 150)
        self.timeline.after(GROW_SETTLE, self._present_need)

    def _harvest(self, result: CareResult) -> None:
        now = self.clock()
        cycle = self.visit.cycle
        assert cycle is not None
        plant_id = cycle.plant.plant_id
        self.cast.correct()
        self.audio.play("harvest")
        self.motion.add_fx("sparkle", FRUIT_SPOT, now, 160)
        item = self.art.harvest(plant_id, 64)
        target = (BASKET_MIDBOTTOM[0], BASKET_MIDBOTTOM[1] - 60)
        if item is not None:
            self.motion.fly(Flight(item, FRUIT_SPOT, target, now + 0.1, 0.75, 110, lambda: self._basket_filled(plant_id)))
        else:
            self._basket_filled(plant_id)
        # The picked plant leaves the pot (it lives on as the stage cards).
        self.timeline.after(0.5, lambda: self._swap_plant(PlantView(), self.clock()))
        self.timeline.after(1.6, self._start_sequence)

    def _basket_filled(self, plant_id: str) -> None:
        now = self.clock()
        self.view.basket.append(plant_id)
        del self.view.basket[:-3]
        self.motion.basket_shake = now
        self.motion.add_fx("star_burst", (BASKET_MIDBOTTOM[0], BASKET_MIDBOTTOM[1] - 70), now, 150)
        self.audio.play("basket")
        self.audio.say("praise")

    def _try_again(self, result: CareResult) -> None:
        now = self.clock()
        seconds = self._show_care(result.care, now, short=True)
        need = result.need
        misses = result.misses

        def react() -> None:
            moment = self.clock()
            self.cast.try_again()
            self.audio.play("not_yet")
            if moment - self._last_retry_voice >= RETRY_VOICE_GAP:
                self._last_retry_voice = moment
                self.audio.say("retry")
            if need is not None:
                # Demonstrate: show where the plant's need really is.
                self.motion.symptom = (need, moment)
                if misses >= 2:
                    self.motion.tool = (f"care.{CURE[need].value}", moment + 0.6)
            self.busy = False
            self._note_activity()

        self.timeline.after(min(seconds, TRY_SECONDS), react)

    # -- order the pictures -------------------------------------------------------------

    def _start_sequence(self) -> None:
        sequence = self.visit.sequence
        cycle_plant = self.visit.harvested[-1] if self.visit.harvested else None
        if sequence is None or cycle_plant is None:
            return
        now = self.clock()
        view = self.view
        view.board = True
        view.order = sequence.order
        view.placed = 0
        view.plant = PlantView(cycle_plant, Stage.FRUIT)
        view.previous = None
        self.controls.show_cards(cycle_plant, sequence.deck)
        self.controls.focus_first()
        self.motion.slot_pulse = now
        self.cast.point(1.6)
        self.busy = False
        self._help_presses = 0
        self._note_activity()

    def _on_card(self, stage: Stage) -> None:
        if self.busy or self.visit.phase is not Phase.SEQUENCE:
            return
        result = self.visit.place(stage)
        if result is Place.IGNORED:
            return
        self._activated = True
        now = self.clock()
        self.motion.tool = None
        sequence = self.visit.sequence
        assert sequence is not None
        if result is Place.NOT_NEXT:
            self.cast.try_again()
            self.audio.play("not_yet")
            self.motion.slot_pulse = now
            if now - self._last_retry_voice >= RETRY_VOICE_GAP:
                self._last_retry_voice = now
                self.audio.say("retry")
            expected = sequence.expected
            if sequence.slot_misses >= 2 and expected is not None:
                self.motion.tool = (f"card.{expected.value}", now)
            return
        self.busy = True
        self.audio.play("card")
        slots = self.renderer.board_slots(self.controls.board, len(sequence.order))
        slot = slots[len(sequence.placed) - 1]
        start = self._tile_center(f"card.{stage.value}")
        self.controls.remove_card(stage)
        plant_id = self.view.plant.plant_id
        picture = self.art.stage_card(plant_id, stage, int(slot.width * 0.74)) if plant_id else None
        if picture is not None:
            self.motion.fly(Flight(picture, start, slot.center, now, 0.45, 60, lambda: self._card_landed(slot.center)))
        else:
            self._card_landed(slot.center)

    def _card_landed(self, center: tuple[int, int]) -> None:
        now = self.clock()
        sequence = self.visit.sequence
        if sequence is None:
            return
        self.view.placed = len(sequence.placed)
        self.motion.add_fx("sparkle", (center[0] + 30, center[1] - 40), now, 90)
        if sequence.complete:
            self._sequence_done()
            return
        self.motion.slot_pulse = now
        self.busy = False
        self._note_activity()

    def _sequence_done(self) -> None:
        now = self.clock()
        self.cast.correct()
        self.audio.play("basket")
        self.audio.say("praise")
        board = self.controls.board
        self.motion.add_fx("confetti", board.center, now, 320)
        index = self.visit.completed + 1
        summary = self.visit.finish_plant()
        if summary is not None:
            self.events.plant_finished(self._visit_id, index, summary)
        self.progress.save(self.visit.progress)
        self.controls.sync_progress(self.visit.completed)
        self.controls.hide_row()
        self.timeline.after(PLANT_DONE_SECONDS, self._after_plant)

    def _after_plant(self) -> None:
        if self.visit.complete:
            self._complete_visit()
            return
        self._start_choose()

    # -- completion -----------------------------------------------------------------------

    def _complete_visit(self) -> None:
        progress = self.visit.progress
        self.progress.save(progress)
        self.events.visit_completed(self._visit_id, self.visit.completed, progress.level)
        self.timeline.clear()
        self.motion.clear()
        self.audio.play("fanfare")
        self.audio.say("complete")
        self._prepare_completion()
        assert self.completion is not None
        self._surfaces.push_overlay(CompletionOverlay(self.completion, on_primary=self._restart))
        self.state = AppState.TERMINAL
        self.busy = False

    def _prepare_completion(self) -> None:
        self.completion = PygameCompletionScreen(
            self.typography,
            width=REFERENCE_WIDTH,
            height=REFERENCE_HEIGHT,
            palette=CompletionPalette(background=COMPLETION_DUSK),
            scene=CompletionScene(self.kit, character=TITO, star_total=self.visit.total),
        )
        self.completion.prepare(
            CompletionContent(
                title=self._text("victory.title", "★"),
                primary_label=self._text("btn.play_again", "↻"),
                achievement_count=self.visit.completed,
            )
        )

    def _restart(self) -> None:
        """One restart transaction regardless of keyboard/controller/pointer input."""

        self._activated = True
        self._surfaces.pop_overlay()
        if self.completion is not None:
            self.completion.clear()
            self.completion = None
        self._visit_id = uuid4().hex
        self.visit.restart()
        self.view.basket.clear()
        self.state = AppState.PLAYING
        self._start_choose()

    # -- hints ----------------------------------------------------------------------------------

    def _on_hint(self) -> None:
        """The help button: Tito points at the cue; pressed again, the right tile glows."""

        if self.busy or self.state is not AppState.PLAYING:
            return
        self._activated = True
        self._help_presses += 1
        self._show_hint(self._help_presses)

    def _maybe_hint(self, now: float) -> None:
        if self.busy or self.timeline.busy or self.motion.flights or self._idle_hints >= MAX_IDLE_HINTS:
            return
        if now - self._last_activity < IDLE_HINT_SECONDS * (self._idle_hints + 1):
            return
        self._idle_hints += 1
        if self._idle_hints == 1:
            self.audio.say("nudge")
        self._show_hint(self._idle_hints)

    def _show_hint(self, level: int) -> None:
        now = self.clock()
        self.cast.point(1.8)
        phase = self.visit.phase
        if phase is Phase.GROW and self.visit.cycle is not None and self.visit.cycle.need is not None:
            need = self.visit.cycle.need
            self.motion.symptom = (need, now)
            if level >= 2:
                self.motion.tool = (f"care.{CURE[need].value}", now + 0.5)
        elif phase is Phase.SEQUENCE and self.visit.sequence is not None:
            self.motion.slot_pulse = now
            expected = self.visit.sequence.expected
            if level >= 2 and expected is not None:
                self.motion.tool = (f"card.{expected.value}", now + 0.5)

    # -- helpers --------------------------------------------------------------------------------

    def _swap_plant(self, plant: PlantView, now: float) -> None:
        view = self.view
        if view.plant.overlay != plant.overlay:
            view.overlay_previous = view.plant.overlay
            view.overlay_fade_start = now
        if (view.plant.plant_id, view.plant.stage, view.plant.variant) != (plant.plant_id, plant.stage, plant.variant):
            view.previous = PlantView(**_plant_fields(view.plant)) if view.plant.plant_id else None
            view.plant_fade_start = now
        view.plant = plant

    def _tile_center(self, control_id: str) -> tuple[int, int]:
        tile = self.controls.tile(control_id)
        return tile.rect.center if tile is not None else (REFERENCE_WIDTH // 2, REFERENCE_HEIGHT - 60)

    def _text(self, key: str, default: str) -> str:
        if self.resources is None:
            return default
        try:
            return self.resources.text(key) or default
        except Exception:
            return default


def _plant_fields(plant: PlantView) -> dict:
    return {"plant_id": plant.plant_id, "stage": plant.stage, "variant": plant.variant, "overlay": plant.overlay}


def _plant_height(stage: Stage) -> int:
    """Rough height of the plant top above its base (for growth sparkles)."""

    return {Stage.SEED: 30, Stage.SPROUT: 90, Stage.YOUNG: 150, Stage.FLOWER: 200, Stage.FRUIT: 200}[stage]


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


__all__ = ["AppState", "SerraActivity", "Timeline"]
