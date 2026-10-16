"""Lifecycle, timing and shared-kit input for Magic Bakery (Pasticceria Magica).

One round is five cast customers. Each one walks to the counter and shows an
order bubble:

* a counting order - a numeral with that many pictures of a topping (lower
  rungs) or the numeral and one picture (upper rungs), one or two toppings;
* a pattern order - the start of a repeating row (strawberry, blueberry,
  strawberry ...) with ``?`` places the child completes on the cake.

The child decorates from a small picture pantry; every topping counts aloud
with a rising tone and a numeral badge (and the spoken number once the shared
numbers bank exists). Tapping a topping on the cake (or the take-one-off
button) removes it. The bell serves:

* right -> the customer cheers (``pose_cheer`` + their approved praise
  take), confetti, the cake slides off to be boxed and the customer leaves;
* not yet -> the customer thinks (``pose_think``), then the shop counts the
  cake together (badges + tones, the matching card row glows) and the extra
  or wrong toppings wobble; from the second miss faint ghosts show where a
  topping still belongs. Retries are unlimited and nothing is lost.

Idle ~6 s -> the customer points at the bubble and it glows; later the next
needed pantry tile glows. After five customers the shared completion scene
offers another round or "my cake": free decorating with the whole pantry,
kept as a draft and saved as a picture to My Creations on request. The next
round's rung adapts from this round's misses.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
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
from greia_platform.localization import LocalizedResources
from greia_platform.pygame_canvas import PygameReferenceCanvas, activity_viewport_for_surface
from greia_platform.pygame_completion import (
    CompletionContent,
    CompletionOverlay,
    CompletionPalette,
    CompletionScene,
    PygameCompletionScreen,
)
from greia_platform.pygame_png import PygamePngError, encode_surface_png
from greia_platform.typography import GreiaTypography
from greia_platform.ui_core import SurfaceNavigator, UiEventResult

if __package__:
    from .pasticceria_art import BakeryArt, bakery_visual_resolver
    from .pasticceria_audio import BakeryAudio
    from .pasticceria_content import BAKER, COUNT, ORDERS_PER_ROUND, REFERENCE_HEIGHT, REFERENCE_WIDTH, TOPPING_IDS
    from .pasticceria_controls import BakeryControls
    from .pasticceria_layout import (
        BUBBLE_RECT,
        CUSTOMER_MIDBOTTOM,
        FREE_POINTS,
        FROSTING_CENTER,
        TOPPING_SIZE,
        WALK_DISTANCE,
        from_frosting,
        on_frosting,
        place_point,
        sprite_rect,
        to_frosting,
    )
    from .pasticceria_model import BakeryRound, DemoStep, FreeCake, Verdict, adapt_level
    from .pasticceria_renderer import (
        CAKE_EXIT,
        CAKE_SLIDE_SECONDS,
        WALK_SECONDS,
        BakeryRenderer,
        CounterCast,
        SceneMotion,
        SceneView,
        Screen,
    )
    from .pasticceria_services import BakeryProgress, EventPort, PicturePort, ProgressPort, picture_digest
else:
    from pasticceria_art import BakeryArt, bakery_visual_resolver
    from pasticceria_audio import BakeryAudio
    from pasticceria_content import BAKER, COUNT, ORDERS_PER_ROUND, REFERENCE_HEIGHT, REFERENCE_WIDTH, TOPPING_IDS
    from pasticceria_controls import BakeryControls
    from pasticceria_layout import (
        BUBBLE_RECT,
        CUSTOMER_MIDBOTTOM,
        FREE_POINTS,
        FROSTING_CENTER,
        TOPPING_SIZE,
        WALK_DISTANCE,
        from_frosting,
        on_frosting,
        place_point,
        sprite_rect,
        to_frosting,
    )
    from pasticceria_model import BakeryRound, DemoStep, FreeCake, Verdict, adapt_level
    from pasticceria_renderer import (
        CAKE_EXIT,
        CAKE_SLIDE_SECONDS,
        WALK_SECONDS,
        BakeryRenderer,
        CounterCast,
        SceneMotion,
        SceneView,
        Screen,
    )
    from pasticceria_services import BakeryProgress, EventPort, PicturePort, ProgressPort, picture_digest

IDLE_HINT_SECONDS = 6.0
MAX_IDLE_HINTS = 4
ARRIVE_POINT_SECONDS = 1.8
HAPPY_HOLD = 1.4
DEMO_STEP = 0.42
DEMO_LEAD = 0.55
WOBBLE_HOLD = 0.6
DRAFT_SAVE_SECONDS = 2.0
MAX_SCHEDULED = 48
PLUM = (86, 58, 100)  # theme ink "plum"


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


@dataclass(frozen=True, slots=True)
class ServeResult:
    """What one press of the bell did (for tests and tools)."""

    verdict: Verdict
    customer: str


class PasticceriaApp:
    """Coordinate rounds, the free cake, kit controls, art, audio and lifecycle."""

    def __init__(
        self,
        *,
        screen: pygame.Surface,
        canvas: PygameReferenceCanvas,
        typography: GreiaTypography,
        resources: LocalizedResources | None,
        audio: BakeryAudio,
        progress: ProgressPort,
        events: EventPort,
        pictures: PicturePort,
        rng: random.Random | None = None,
        clock: Callable[[], float] = time.monotonic,
        kit: ControlKit | None = None,
        art: BakeryArt | None = None,
        session_prefix: str | None = None,
    ) -> None:
        self.screen = screen
        self.canvas = canvas
        self.typography = typography
        self.resources = resources
        self.audio = audio
        self.progress_port = progress
        self.events = events
        self.pictures = pictures
        self.rng = rng if rng is not None else random.Random()
        self.clock = clock
        self._session_prefix = session_prefix or f"{int(time.time())}"
        self._rounds_played = 0

        self.progress: BakeryProgress = progress.load()
        self.free_cake: FreeCake = self.progress.free_cake
        self._saved_signature: tuple | None = None
        self.selected_topping: str = TOPPING_IDS[0]

        # Shared control kit (ADR 0037): primary Collection "learn" -> orange.
        self.kit = kit if kit is not None else ControlKit(
            typography, ControlTheme.for_accent("orange"), art=ControlArt(bakery_visual_resolver)
        )
        self.art = art if art is not None else BakeryArt(self.kit.painter, art=ControlArt(max_entries=64))
        self.cast = CounterCast(self.art, clock)
        self.renderer = BakeryRenderer(self.art, self.cast)
        self.motion = SceneMotion()
        self.timeline = Timeline(clock)
        self.controls = BakeryControls(
            self.kit,
            self.art,
            text=lambda key: self._text(key, ""),
            on_topping=self._on_topping,
            on_undo=self._on_undo,
            on_serve=self._on_serve,
            on_save=self._on_save,
            on_new_cake=self._on_new_cake,
            on_new_round=self._on_new_round,
        )
        self._surfaces = SurfaceNavigator(self.controls.layer)
        self._input = PygameControlInput(to_logical=canvas.pointer, is_safe=lambda pos: _safe_point(self.screen, pos))
        self.controls.relayout(ControlLayout.for_canvas(canvas, screen.get_size()))

        self.screen_id = Screen.ROUND
        self.round: BakeryRound | None = None
        self.show_card = False
        self.completion: PygameCompletionScreen | None = None
        self.session_id = ""
        self.last_serve: ServeResult | None = None
        self._running = True
        self.ready_published = False
        self._dirty = True
        self._activated = False
        self._busy = False
        self._draft_dirty_since: float | None = None
        self._last_activity = clock()
        self._idle_hints = 0
        self.start_round()

    # -- main loop --------------------------------------------------------------------

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
        self.audio.update()
        self.motion.prune(now)
        if self.screen_id is Screen.ROUND:
            self._maybe_hint(now)
        if self._draft_dirty_since is not None and now - self._draft_dirty_since >= DRAFT_SAVE_SECONDS:
            self.persist()
        if self.controls.layer.invalidation.should_draw:
            self._dirty = True
        if self.screen_id is Screen.END:
            return False
        return self.motion.active(now) or self.cast.animating

    def render(self) -> None:
        surface = self.canvas.surface
        if self.screen_id is not Screen.END:
            self.renderer.draw(surface, self.view(), self.motion, self.clock(), tile_rect=self.controls.tile_rect)
        self._surfaces.draw(surface)

    def view(self) -> SceneView:
        if self.screen_id is Screen.FREE:
            return SceneView(Screen.FREE, free_cake=self.free_cake)
        game = self.round
        if game is None or self.screen_id is Screen.END:
            return SceneView(self.screen_id)
        return SceneView(Screen.ROUND, order=game.order, cake=game.cake, show_card=self.show_card)

    def persist(self) -> None:
        self.progress.free_cake = self.free_cake
        self.progress_port.save(self.progress)
        self._draft_dirty_since = None

    # -- input ------------------------------------------------------------------------

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
        self.canvas = PygameReferenceCanvas(self.screen)
        self._input = PygameControlInput(to_logical=self.canvas.pointer, is_safe=lambda pos: _safe_point(self.screen, pos))
        self.controls.relayout(ControlLayout.for_canvas(self.canvas, self.screen.get_size()))
        self._dirty = True

    def _dispatch(self, kit_input) -> bool:
        if not isinstance(kit_input, KitPointer) or kit_input.phase is not PointerPhase.MOVE:
            self._note_activity()
        result = self._surfaces.dispatch(kit_input)
        if (
            result is UiEventResult.IGNORED
            and isinstance(kit_input, KitPointer)
            and kit_input.phase is PointerPhase.UP
            and self.completion is None
        ):
            self._cake_tap(kit_input.position)
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
        self._idle_hints = 0

    # -- a round of customers ------------------------------------------------------------

    def start_round(self) -> None:
        self.timeline.clear()
        self.motion.reset()
        self._close_completion()
        self.round = BakeryRound.planned(self.progress.level, self.rng)
        self._rounds_played += 1
        self.session_id = f"{self._session_prefix}-{self._rounds_played}-{self.rng.randrange(1_000_000):06d}"
        self.screen_id = Screen.ROUND
        self.controls.set_progress(0)
        self._arrive(first=True)

    def _arrive(self, *, first: bool = False) -> None:
        game = self.round
        if game is None:
            return
        now = self.clock()
        self.show_card = False
        self.motion.ghosts = ()
        self.motion.nudge = ()
        self.cast.set_character(game.customer)
        self.cast.reset()
        self.motion.walk(now, -WALK_DISTANCE, 0)
        self.motion.drop_cake(now)
        self.controls.show_round(game.order.pantry)
        self._set_busy(True)
        self.audio.play("door")
        if first:
            self.audio.cast(game.customer, "ready.go")
        self.timeline.after(WALK_SECONDS, self._greet)
        self._dirty = True

    def _greet(self) -> None:
        game = self.round
        if game is None or self.screen_id is not Screen.ROUND:
            return
        now = self.clock()
        self.show_card = True
        self.motion.show_card(now)
        self.motion.add_fx("sparkle", (BUBBLE_RECT.right - 30, BUBBLE_RECT.top + 20), now)
        self.cast.point(ARRIVE_POINT_SECONDS)
        self._say_order()
        self._set_busy(False)
        self._sync_cake_controls()
        self._note_activity()
        self._dirty = True

    def _say_order(self) -> None:
        game = self.round
        if game is None:
            return
        order = game.order
        if order.kind == COUNT:
            self.audio.say_order(tuple((item.amount, item.topping_id) for item in order.items))

    def _on_topping(self, topping_id: str) -> None:
        if self.screen_id is Screen.FREE:
            self._free_place(topping_id)
            return
        game = self.round
        if game is None or self.screen_id is not Screen.ROUND or self._busy:
            return
        placement = game.place(topping_id)
        self._activated = True
        now = self.clock()
        if placement is None:
            self.audio.play("nope")
            return
        self._hint_marks_changed(placement.index, placed=True)
        base, size = place_point(game.order.kind, placement.index)
        self.audio.play("pop")
        if game.order.counts_aloud:
            # Count aloud: a rising tone, the numeral badge, the spoken number.
            self.audio.count_tone(placement.ordinal)
            self.motion.badge(placement.index, placement.ordinal, now)
            self.audio.say_number(placement.ordinal)
        self.motion.add_fx("sparkle", (base[0], base[1] - size // 2), now)
        self._sync_cake_controls()
        self._dirty = True

    def _on_undo(self) -> None:
        if self.screen_id is Screen.FREE:
            if self.free_cake.undo() is not None:
                self._activated = True
                self.audio.play("unpop")
                self._free_changed()
            return
        game = self.round
        if game is None or self._busy:
            return
        removed = game.cake.undo()
        if removed is not None:
            self._activated = True
            self._hint_marks_changed(removed, placed=False)
            self.audio.play("unpop")
            self._sync_cake_controls()
            self._dirty = True

    def _cake_tap(self, point: tuple[int, int]) -> None:
        """A tap on the cake: take that topping off (or, when free, put one there)."""

        if self.screen_id is Screen.FREE:
            self._free_tap(point)
            return
        game = self.round
        if game is None or self.screen_id is not Screen.ROUND or self._busy:
            return
        places = [(index, *place_point(game.order.kind, index)) for index, _ in game.cake.placements()]
        for index, base, size in sorted(places, key=lambda item: -item[1][1]):  # front-most first
            if sprite_rect(base, size).inflate(-size // 5, -size // 5).collidepoint(point):
                if game.cake.remove(index):
                    self._activated = True
                    self._hint_marks_changed(index, placed=False)
                    self.audio.play("unpop")
                    self.motion.add_fx("sparkle", (base[0], base[1] - size // 2), self.clock())
                    self._sync_cake_controls()
                    self._dirty = True
                return

    def _on_serve(self) -> None:
        game = self.round
        if game is None or self.screen_id is not Screen.ROUND or self._busy:
            return
        verdict = game.serve()
        if verdict is None:
            return
        self._activated = True
        self.last_serve = ServeResult(verdict, game.customer)
        self.audio.play("bell")
        self._note_activity()
        if verdict.correct:
            self._celebrate(game)
        else:
            self._not_yet(game, verdict)
        self._dirty = True

    def _celebrate(self, game: BakeryRound) -> None:
        now = self.clock()
        customer = game.customer
        self.cast.correct()
        self.audio.play("yum")
        self.audio.cast(customer, "praise.general" if game.misses == 0 else "celebrate.success")
        self.motion.add_fx("confetti", (FROSTING_CENTER[0], FROSTING_CENTER[1] - 40), now)
        self.motion.add_fx("heart_pop", (CUSTOMER_MIDBOTTOM[0], CUSTOMER_MIDBOTTOM[1] - 220), now)
        self.controls.set_progress(game.served)
        self._set_busy(True)
        order = game.order
        self.progress.orders_served += 1
        self.events.order_served(
            "recipe.completed" if order.kind == COUNT else "pattern.solved",
            self.session_id,
            {"order": game.index + 1, "kind": order.kind, "level": game.level, "misses": game.misses},
        )
        self.timeline.after(HAPPY_HOLD, self._leave)

    def _leave(self) -> None:
        game = self.round
        if game is None:
            return
        now = self.clock()
        self.show_card = False
        self.motion.walk(now, 0, -WALK_DISTANCE)
        self.motion.slide_cake(now, 0, CAKE_EXIT)
        self.audio.play("swoosh")
        nxt = game.customers[game.index + 1] if game.index + 1 < game.total else None
        if nxt is not None:
            self.audio.prepare_cast(nxt)
        self.timeline.after(max(WALK_SECONDS, CAKE_SLIDE_SECONDS) + 0.1, self._after_leave)
        self._dirty = True

    def _after_leave(self) -> None:
        game = self.round
        if game is None:
            return
        if game.next_customer():
            self._arrive()
        else:
            self._finish_round()

    def _not_yet(self, game: BakeryRound, verdict: Verdict) -> None:
        """Gentle try-again: think, count the cake together, show what is off."""

        self.cast.try_again()
        self.audio.play("hmm")
        if game.misses == 1:
            self.audio.cast(game.customer, "encourage.retry")
        self._set_busy(True)
        now = self.clock()
        self.motion.glow_card(now, DEMO_LEAD)
        steps = game.order.demonstration(game.cake)
        for number, step in enumerate(steps):
            self.timeline.after(DEMO_LEAD + number * DEMO_STEP, lambda st=step: self._demo_step(st))
        end = DEMO_LEAD + len(steps) * DEMO_STEP
        misses = game.misses
        self.timeline.after(end, lambda: self._demo_finish(verdict, misses))

    def _demo_step(self, step: DemoStep) -> None:
        if self.screen_id is not Screen.ROUND:
            return
        now = self.clock()
        if step.number > 0:
            self.motion.badge(step.index, step.number, now)
            self.audio.count_tone(step.number)
            self.audio.say_number(step.number)
        else:
            self.motion.shake((step.index,), now)
            if step.tone:
                self.audio.count_tone(step.tone)
            else:
                self.audio.play("pop")
        self.motion.highlight_row(step.row, now + DEMO_STEP + 0.05)
        self._dirty = True

    def _demo_finish(self, verdict: Verdict, misses: int) -> None:
        game = self.round
        if game is None or self.screen_id is not Screen.ROUND:
            return
        now = self.clock()
        self.motion.shake(verdict.wrong, now)
        if misses >= 2:
            self.motion.ghosts = game.order.ghosts(game.cake, verdict)
            self.motion.nudge = verdict.wrong
        if verdict.wrong:
            self.audio.play("nope")
        self.timeline.after(WOBBLE_HOLD, self._unlock)
        self._dirty = True

    def _unlock(self) -> None:
        if self.screen_id is not Screen.ROUND:
            return
        self._set_busy(False)
        self._sync_cake_controls()
        self._note_activity()
        self._dirty = True

    def _finish_round(self) -> None:
        game = self.round
        if game is None:
            return
        old_level = self.progress.level
        self.progress.level = adapt_level(old_level, game.total_misses)
        self.progress.rounds += 1
        self.persist()
        self.events.round_completed(
            self.session_id,
            {
                "orders": game.total,
                "first_try": game.first_try,
                "misses": game.total_misses,
                "level": old_level,
                "next_level": self.progress.level,
            },
        )
        self.timeline.clear()
        self.cast.reset()
        self.show_card = False
        self.completion = PygameCompletionScreen(
            self.typography,
            width=REFERENCE_WIDTH,
            height=REFERENCE_HEIGHT,
            palette=CompletionPalette(background=PLUM),
            scene=CompletionScene(
                self.kit, character=BAKER, star_total=ORDERS_PER_ROUND, secondary_glyph="cupcake"
            ),
        )
        self.completion.prepare(
            CompletionContent(
                title=self._text("victory.title", "★"),
                primary_label=self._text("btn.play_again", "↻"),
                body_lines=(self._text("victory.subtitle", ""),) if self._text("victory.subtitle", "") else (),
                achievement_count=game.served,
                secondary_label=self._text("btn.own_cake", "+"),
            )
        )
        self._surfaces.push_overlay(
            CompletionOverlay(self.completion, on_primary=self.start_round, on_secondary=self.start_free)
        )
        self.controls.show_none()
        self.screen_id = Screen.END
        self.audio.cast(BAKER, "celebrate.success")
        self._busy = False
        self._dirty = True

    def _close_completion(self) -> None:
        if self.completion is not None:
            self._surfaces.pop_overlay()
            self.completion.clear()
            self.completion = None

    # -- my own cake ---------------------------------------------------------------------

    def start_free(self) -> None:
        self.timeline.clear()
        self.motion.reset()
        self._close_completion()
        self.round = None
        self.screen_id = Screen.FREE
        self.show_card = False
        self.cast.set_character(BAKER)
        self.cast.reset()
        self.cast.wave(1.6)
        self.motion.drop_cake(self.clock())
        self.controls.show_free()
        self.controls.save.visible = self.pictures.available
        self._busy = False
        self.audio.cast(BAKER, "ready.go")
        self._sync_free_controls()
        self._note_activity()
        self._dirty = True

    def _free_place(self, topping_id: str) -> None:
        self._activated = True
        self.selected_topping = topping_id
        taken = [(t.u, t.v) for t in self.free_cake.toppings]
        spot = next(
            (p for p in FREE_POINTS if all((p[0] - u) ** 2 + (p[1] - v) ** 2 > 0.02 for u, v in taken)),
            None,
        )
        if spot is None:
            spot = (self.rng.uniform(-0.75, 0.75), self.rng.uniform(-0.55, 0.65))
        self._free_put(topping_id, spot)

    def _free_tap(self, point: tuple[int, int]) -> None:
        toppings = self.free_cake.toppings
        for index in sorted(range(len(toppings)), key=lambda i: -toppings[i].v):
            base = from_frosting(toppings[index].u, toppings[index].v)
            if sprite_rect(base, TOPPING_SIZE).inflate(-12, -12).collidepoint(point):
                self.free_cake.remove(index)
                self._activated = True
                self.audio.play("unpop")
                self._free_changed()
                return
        if on_frosting(point):
            self._activated = True
            self._free_put(self.selected_topping, to_frosting(point))

    def _free_put(self, topping_id: str, spot: tuple[float, float]) -> None:
        placed = self.free_cake.place(topping_id, spot[0], spot[1])
        if placed is None:
            self.audio.play("nope")
            self._sync_free_controls()
            return
        base = from_frosting(placed.u, placed.v)
        self.audio.play("pop")
        self.motion.add_fx("sparkle", (base[0], base[1] - TOPPING_SIZE // 2), self.clock())
        self._free_changed()

    def _free_changed(self) -> None:
        if self._draft_dirty_since is None:
            self._draft_dirty_since = self.clock()
        self._sync_free_controls()
        self._dirty = True

    def _on_save(self) -> None:
        if self.screen_id is not Screen.FREE or self.free_cake.empty or not self.pictures.available:
            return
        self._activated = True
        now = self.clock()
        try:
            payload = encode_surface_png(self.renderer.picture(self.free_cake))
        except (PygamePngError, pygame.error, ValueError):
            payload = b""
        digest = picture_digest(payload) if payload else ""
        ok = bool(payload) and (digest == self.progress.shared_digest or self.pictures.publish(payload))
        if not ok:
            self.cast.try_again()
            self.audio.play("nope")
            self._dirty = True
            return
        if digest != self.progress.shared_digest:
            self.progress.shared_digest = digest
            self.events.picture_shared(digest, {"media_type": "image/png", "toppings": len(self.free_cake.toppings)})
        self._saved_signature = self.free_cake.signature()
        self.persist()
        self.cast.correct()
        self.audio.play("save")
        self.audio.cast(BAKER, "praise.general")
        self.motion.add_fx("star_burst", self.controls.save.rect.center, now)
        self._sync_free_controls()
        self._dirty = True

    def _on_new_cake(self) -> None:
        if self.screen_id is not Screen.FREE or not self._can_start_new_cake():
            return
        self._activated = True
        self.free_cake.clear()
        self._saved_signature = None
        self.audio.play("swoosh")
        self.motion.drop_cake(self.clock())
        self._free_changed()
        self.persist()

    def _on_new_round(self) -> None:
        if self.screen_id is not Screen.FREE:
            return
        self._activated = True
        self.persist()
        self.start_round()

    def _can_start_new_cake(self) -> bool:
        return not self.free_cake.empty and self.free_cake.signature() == self._saved_signature

    # -- hints ----------------------------------------------------------------------------

    def _maybe_hint(self, now: float) -> None:
        game = self.round
        if game is None or self._busy or not self.show_card or self._idle_hints >= MAX_IDLE_HINTS:
            return
        if now - self._last_activity < IDLE_HINT_SECONDS * (self._idle_hints + 1):
            return
        self._idle_hints += 1
        self.cast.point(2.0)
        if self._idle_hints == 1:
            self.motion.glow_card(now, 2.4)
            self._say_order()
        else:
            self.motion.glow_tile(game.order.next_needed(game.cake), now, 3.0)
        self._dirty = True

    # -- helpers ----------------------------------------------------------------------------

    def _hint_marks_changed(self, index: int, *, placed: bool) -> None:
        """A place changed: its nudge is done; its ghost goes once something is put there."""

        if placed:
            self.motion.ghosts = tuple(ghost for ghost in self.motion.ghosts if ghost[0] != index)
        self.motion.nudge = tuple(place for place in self.motion.nudge if place != index)

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.controls.set_busy(busy)

    def _sync_cake_controls(self) -> None:
        game = self.round
        if game is None:
            return
        self.controls.set_cake_state(can_undo=not game.cake.empty, can_serve=game.order.ready(game.cake))

    def _sync_free_controls(self) -> None:
        self.controls.set_free_state(
            can_undo=not self.free_cake.empty,
            can_save=not self.free_cake.empty,
            can_new=self._can_start_new_cake(),
            selected=self.selected_topping,
        )

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


__all__ = ["PasticceriaApp", "ServeResult", "Timeline"]
