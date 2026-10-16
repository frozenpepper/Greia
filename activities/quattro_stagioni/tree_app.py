"""Lifecycle, timing and shared-kit input for The Big Seasons Tree.

Tito's big tree stands bare in a landscape. The child picks a season (four
picture tiles), Tito says what that season is like, and then the child
dresses the scene for it, one mission at a time: the tree (blossom, apples,
orange leaves or snow), the weather, something in the meadow, a woodland
friend (awake or fast asleep), Tito's clothes. Each mission shows picture
cards and exactly one belongs:

* the right card flies into the scene and becomes part of it (the canopy
  appears, rain starts, the snowman stands); Tito cheers, the name is shown
  (and spoken where an approved recording exists);
* a card that does not belong flies in, wiggles "not here" and comes back
  greyed; Tito thinks, and the right card hops (it glows after a second
  miss); retries are unlimited;
* idle ~6 s -> Tito points and the empty part of the scene glows; later the
  right card hops, then glows.

When the scene is dressed the weather plays for a moment, then the shared
cast completion scene appears; "play again" returns to the season picker
(the next season not yet dressed is focused). The ladder (more missions,
more cards) adapts from the misses of each round.
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
    ControlArt,
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
    from .tree_art import SeasonsArt
    from .tree_audio import TreeAudio
    from .tree_content import ITEMS, REFERENCE_HEIGHT, REFERENCE_WIDTH, SEASONS, Item, Season, Slot, Weather
    from .tree_controls import TreeControls
    from .tree_layout import (
        BANNER_ICON,
        CARD_ICON,
        CLOUDS,
        CROWN_CENTER,
        SLOT_SPOTS,
        SUN_CENTER,
        TILE_ICON,
        TITO_HEIGHT,
        TITO_TAP_RECT,
        TREE_TAP_RECT,
    )
    from .tree_model import DressRound, Pick, PickOutcome, adapt_level
    from .tree_renderer import FLY_SECONDS, TRY_HOLD_SECONDS, Flight, SceneMotion, SceneView, TitoCast, TreeRenderer
    from .tree_services import EventPort, ProgressPort, SeasonsProgress
else:
    from tree_art import SeasonsArt
    from tree_audio import TreeAudio
    from tree_content import ITEMS, REFERENCE_HEIGHT, REFERENCE_WIDTH, SEASONS, Item, Season, Slot, Weather
    from tree_controls import TreeControls
    from tree_layout import (
        BANNER_ICON,
        CARD_ICON,
        CLOUDS,
        CROWN_CENTER,
        SLOT_SPOTS,
        SUN_CENTER,
        TILE_ICON,
        TITO_HEIGHT,
        TITO_TAP_RECT,
        TREE_TAP_RECT,
    )
    from tree_model import DressRound, Pick, PickOutcome, adapt_level
    from tree_renderer import FLY_SECONDS, TRY_HOLD_SECONDS, Flight, SceneMotion, SceneView, TitoCast, TreeRenderer
    from tree_services import EventPort, ProgressPort, SeasonsProgress

IDLE_HINT_SECONDS = 6.0
FIRST_MISSION_DELAY = 0.6
PLACE_PAUSE = 1.5
FINALE_SECONDS = 2.8
GLOW_SECONDS = 2.4
MAX_SCHEDULED = 32
FOREST = (40, 81, 58)  # theme text-ink token "forest"
# What a tap on the dressed tree shakes loose (library FX).
TREE_FX = {"tree_blossom": "bloom", "tree_apples": "sparkle", "tree_orange": "leaf_drift", "tree_snowy": "snow"}
PLACE_FX = {Slot.TREE: "star_burst", Slot.SKY: "sparkle", Slot.GROUND: "star_burst", Slot.ANIMAL: "star_burst", Slot.CLOTHES: "sparkle"}


class AppState(StrEnum):
    PICK = "pick"
    PLAYING = "playing"
    FINALE = "finale"
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

    def __len__(self) -> int:
        return len(self._entries)


class TreeActivity:
    """Coordinate the round model, kit controls, art, audio and lifecycle."""

    def __init__(
        self,
        *,
        screen: pygame.Surface,
        canvas: PygameReferenceCanvas,
        typography: GreiaTypography,
        resources: LocalizedResources | None,
        audio: TreeAudio,
        progress: ProgressPort,
        events: EventPort,
        rng: random.Random | None = None,
        clock: Callable[[], float] = time.monotonic,
        kit: ControlKit | None = None,
        art: SeasonsArt | None = None,
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
        self.dressed: set[Season] = set(saved.dressed)
        self.last_season: Season | None = saved.last
        self.rounds = saved.rounds

        # Shared control kit (ADR 0037): explore Collection -> leaf accent.
        self.kit = kit if kit is not None else ControlKit(typography, ControlTheme.for_accent("leaf"))
        self.art = art if art is not None else SeasonsArt(art=ControlArt(max_entries=96))
        feedback = CastFeedback("tito", height=TITO_HEIGHT, art=self.art.loader, clock=clock)
        self.cast = TitoCast(feedback, self.art, clock)
        self.renderer = TreeRenderer(self.art, self.cast)
        self.motion = SceneMotion()
        self.timeline = Timeline(clock)
        self.controls = TreeControls(self.kit, on_card=self._on_card, on_season=self._on_season, on_listen=self._on_listen)
        self._surfaces = SurfaceNavigator(self.controls.layer)
        self._input = PygameControlInput(to_logical=canvas.pointer, is_safe=lambda pos: _safe_point(self.screen, pos))
        self.controls.place_bar(ControlLayout.for_canvas(canvas, screen.get_size()))

        self.round: DressRound | None = None
        self.scene_season: Season = Season.SPRING
        self.completion: PygameCompletionScreen | None = None
        self.state = AppState.PICK
        self.session_id = ""
        self._running = True
        self.ready_published = False
        self._dirty = True
        self._activated = False
        self._busy = False
        self._last_activity = clock()
        self._last_step = clock()
        self._idle_hints = 0
        self._welcomed = False
        self.enter_picker()

    # -- main loop ----------------------------------------------------------------

    def run(self) -> int:
        ticker = pygame.time.Clock()
        try:
            while self._running and not activity_stop_requested():
                for event in pygame.event.get():
                    self.handle_event(event)
                repeat = self._input.poll()
                if repeat is not None:
                    self._dispatch(repeat)
                animating = self.step()
                if self._dirty or animating:
                    self.render()
                    self.canvas.present()
                    pygame.display.flip()
                    self._dirty = False
                    if not self.ready_published:
                        mark_activity_ready()
                        self.ready_published = True
                ticker.tick(30 if animating else 15)
        finally:
            self.persist()
            self.typography.clear()
        return 0

    def step(self) -> bool:
        """Advance timers; return True while something on screen is moving."""

        now = self.clock()
        dt = now - self._last_step
        self._last_step = now
        if self.timeline.run_due():
            self._dirty = True
        if self.cast.update():
            self._dirty = True
        self.motion.prune(now)
        for index in range(self.controls.card_count):
            self.controls.nudge_card(index, self.motion.card_offset(index, now))
        if self.renderer.weather is not None and self.state is not AppState.TERMINAL:
            self.renderer.weather.update(dt)
        if self.state is AppState.PLAYING:
            self._maybe_hint(now)
        if self.controls.layer.invalidation.should_draw:
            self._dirty = True
        if self.state is AppState.TERMINAL:
            return False
        return (
            self.motion.active(now)
            or self.cast.animating
            or self.renderer.weather is not None
            or self._has_live_sky()
        )

    def _has_live_sky(self) -> bool:
        # A placed sun bobs gently; keep drawing while it is in the sky.
        round_ = self.round
        return round_ is not None and round_.placed.get(Slot.SKY) == "sun" and self.state is not AppState.PICK

    def render(self) -> None:
        surface = self.canvas.surface
        if self.state is not AppState.TERMINAL:
            now = self.clock()
            placed = self.round.placed if (self.round is not None and self.state is not AppState.PICK) else {}
            self.renderer.draw(surface, SceneView(self.scene_season, placed), self.motion, now)
            glow = self.motion.card_glow
            if glow is not None and glow[0] < self.controls.card_count:
                self.renderer.draw_card_glow(surface, self.controls.card_rect(glow[0]))
        self._surfaces.draw(surface)

    def persist(self) -> None:
        self.progress.save(
            SeasonsProgress(
                level=self.level,
                dressed=tuple(season for season in SEASONS if season in self.dressed),
                last=self.last_season,
                rounds=self.rounds,
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
        self.canvas = PygameReferenceCanvas(self.screen)
        self._input = PygameControlInput(to_logical=self.canvas.pointer, is_safe=lambda pos: _safe_point(self.screen, pos))
        self.controls.place_bar(ControlLayout.for_canvas(self.canvas, self.screen.get_size()))
        self._dirty = True

    def _dispatch(self, kit_input) -> bool:
        if not isinstance(kit_input, KitPointer) or kit_input.phase is not PointerPhase.MOVE:
            self._note_activity()
        result = self._surfaces.dispatch(kit_input)
        if (
            result is UiEventResult.IGNORED
            and isinstance(kit_input, KitPointer)
            and kit_input.phase is PointerPhase.DOWN
        ):
            self._ambient_tap(kit_input.position)
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

    def _ambient_tap(self, point: tuple[int, int]) -> None:
        """Free exploration: the tree rustles, Tito waves (never an answer)."""

        if self.state is AppState.TERMINAL:
            return
        now = self.clock()
        if TREE_TAP_RECT.collidepoint(point):
            self.motion.shake_tree(now)
            tree = self.round.placed.get(Slot.TREE) if (self.round is not None and self.state is not AppState.PICK) else None
            self.motion.add_fx(TREE_FX.get(tree or "", "dust_puff"), CROWN_CENTER if tree else point, now)
            self.audio.play("rustle")
            self._dirty = True
        elif TITO_TAP_RECT.collidepoint(point) and not self.cast.animating:
            self.cast.wave_for(1.2)
            self.audio.play("pop")
            self._dirty = True

    # -- season picker ------------------------------------------------------------

    def enter_picker(self) -> None:
        self.timeline.clear()
        self.motion.reset()
        self.cast.reset()
        self.cast.waving = True
        self.renderer.set_weather(None)
        self.round = None
        self.state = AppState.PICK
        self._busy = False
        self.scene_season = Season.SPRING
        focus = SeasonsProgress(dressed=tuple(self.dressed), last=self.last_season).next_season()
        emblems = {season: self.art.emblem(season, TILE_ICON, done=season in self.dressed) for season in SEASONS}
        names = {season: self._text(season.name_key, season.value) for season in SEASONS}
        self.controls.show_picker(emblems, names, focus, self._text("prompt.choose_season", "?"))
        if not self._welcomed:
            self._welcomed = True
            self.audio.say("welcome")
        self._note_activity()
        self._dirty = True

    def _on_season(self, season: Season) -> None:
        if self.state is not AppState.PICK:
            return
        self._activated = True
        self.audio.play("pop")
        self.start_round(season)

    # -- round flow -----------------------------------------------------------------

    def start_round(self, season: Season) -> None:
        self.timeline.clear()
        self.motion.reset()
        self.cast.reset()
        self.cast.waving = False
        self.renderer.set_weather(None)
        self.scene_season = season
        self.round = DressRound(season, self.level, self.rng)
        self.controls.start_round(self.round.total)
        self.controls.hide_cards()
        self.controls.tell(self._text(season.name_key, season.value), self.art.emblem(season, BANNER_ICON, done=False))
        self.state = AppState.PLAYING
        self._rounds_played += 1
        self.session_id = f"{self._session_prefix}-{self._rounds_played}-{self.rng.randrange(1_000_000):06d}"
        if not self.audio.say(season.value):
            self.audio.tito("ready.go")
        self.cast.point(1.6)
        self._busy = True
        self.timeline.after(FIRST_MISSION_DELAY, self._show_mission)
        self._note_activity()
        self._dirty = True

    def _show_mission(self) -> None:
        round_ = self.round
        if round_ is None or self.state is not AppState.PLAYING:
            return
        mission = round_.mission
        if mission is None:
            return
        now = self.clock()
        icons = [self.art.card_icon(ITEMS[item_id], CARD_ICON) for item_id in mission.options]
        prompt = self._text(mission.slot.prompt_key, "?", season=self._text(round_.season.name_key, round_.season.value))
        self.controls.show_cards(
            icons,
            prompt,
            self.art.slot_icon(mission.slot, BANNER_ICON),
            voiced=self.audio.has_clip(round_.season.value),
        )
        self.controls.set_progress(round_.index)
        self.motion.glow_slot(mission.slot, now + 1.4)
        self.cast.point(1.4)
        self._busy = False
        self._note_activity()
        self._dirty = True

    def _on_listen(self) -> None:
        self._activated = True
        round_ = self.round
        if round_ is not None:
            self.audio.say(round_.season.value)
            self.cast.point(1.2)
        self._dirty = True

    def _on_card(self, index: int) -> None:
        round_ = self.round
        if round_ is None or self.state is not AppState.PLAYING or self._busy:
            return
        mission = round_.mission
        if mission is None or not 0 <= index < len(mission.options):
            return
        item = ITEMS[mission.options[index]]
        outcome = round_.choose(item.item_id)
        if outcome.pick is Pick.IGNORED:
            return
        self._activated = True
        if outcome.pick is Pick.RIGHT:
            self._right(item, index)
        else:
            self._wrong(item, index, outcome)
        self._dirty = True

    def _flight(self, item: Item, index: int, slot: Slot, *, returning: bool) -> None:
        now = self.clock()
        origin = self.controls.card_rect(index).center
        target = SUN_CENTER if item.weather is Weather.SUN else SLOT_SPOTS[slot].point
        self.motion.fly(Flight(self.art.card_icon(item, CARD_ICON), origin, target, now, returning, item.item_id, slot))
        self.audio.play("whoosh")

    def _right(self, item: Item, index: int) -> None:
        self._busy = True
        self.motion.slot_glow = None
        self.motion.card_glow = None
        self._flight(item, index, item.slot, returning=False)
        self.controls.hide_cards()
        self.timeline.after(FLY_SECONDS, lambda: self._place(item))

    def _place(self, item: Item) -> None:
        round_ = self.round
        if round_ is None or self.state is not AppState.PLAYING:
            return
        now = self.clock()
        point = SLOT_SPOTS[item.slot].point
        if item.weather is Weather.SUN:
            point = SUN_CENTER
        if item.weather is not None and item.weather is not Weather.SUN:
            for index, (x, y, _width) in enumerate(CLOUDS):
                self.motion.add_fx(PLACE_FX[item.slot], (x, y), now + index * 0.15)
        else:
            self.motion.add_fx(PLACE_FX[item.slot], point, now)
            self.motion.add_fx("sparkle", (point[0] + 50, point[1] - 40), now + 0.15)
        if item.weather is not None:
            self.renderer.set_weather(item.weather, random.Random(self.rng.random()))
        self.audio.play("place")
        spoken = False
        if item.speech is not None:
            spoken = self.audio.say(item.speech)
        if not spoken and item.vocab is not None:
            spoken = self.audio.say_name(item.vocab)
        if not spoken:
            self.audio.praise()
        self.cast.correct()
        self.controls.tell(self._text(item.name_key, ""), self.art.card_icon(item, BANNER_ICON))
        self.controls.set_progress(round_.index)
        delay = PLACE_PAUSE + (0.8 if item.speech is not None else 0.0)
        self.timeline.after(delay, self._finale if round_.complete else self._show_mission)
        self._dirty = True

    def _wrong(self, item: Item, index: int, outcome: PickOutcome) -> None:
        self._busy = True
        self.controls.disable_card(index)
        self._flight(item, index, item.slot, returning=True)
        misses = outcome.task_misses
        self.timeline.after(FLY_SECONDS, lambda: self._not_here(item, misses))
        self.timeline.after(FLY_SECONDS * 2 + TRY_HOLD_SECONDS, lambda: self._demonstrate(misses))

    def _not_here(self, item: Item, misses: int) -> None:
        if self.state is not AppState.PLAYING:
            return
        if item.slot is Slot.TREE:
            self.motion.shake_tree(self.clock())
        self.audio.play("boing")
        self.cast.try_again()
        if misses % 2 == 0:
            self.audio.tito("encourage.retry")
        self._dirty = True

    def _demonstrate(self, misses: int) -> None:
        """Show the way: the right card hops; after two misses it glows too."""

        round_ = self.round
        self._busy = False
        if round_ is None or self.state is not AppState.PLAYING or round_.mission is None:
            return
        now = self.clock()
        answer = round_.mission.options.index(round_.mission.answer)
        self.motion.hop_card(answer, now)
        if misses >= 2:
            self.motion.glow_card(answer, now + GLOW_SECONDS)
            self.motion.glow_slot(round_.mission.slot, now + GLOW_SECONDS)
            self.cast.point(1.4)
        self._note_activity()
        self._dirty = True

    def _finale(self) -> None:
        round_ = self.round
        if round_ is None or self.state is not AppState.PLAYING:
            return
        now = self.clock()
        self.state = AppState.FINALE
        self.controls.hide_cards()
        self.controls.set_progress(round_.total)
        self.controls.tell(
            self._text(f"ready.{round_.season.value}", "★"),
            self.art.emblem(round_.season, BANNER_ICON, done=True),
        )
        self.audio.play("fanfare")
        self.audio.tito("celebrate.success")
        self.cast.correct()
        for offset, (dx, dy) in enumerate(((-160, -40), (0, -120), (170, -30), (-60, 60))):
            self.motion.add_fx("star_burst" if offset % 2 == 0 else "sparkle", (CROWN_CENTER[0] + dx, CROWN_CENTER[1] + dy), now + offset * 0.25)
        self.timeline.after(FINALE_SECONDS, self._complete)
        self._dirty = True

    def _complete(self) -> None:
        round_ = self.round
        if round_ is None or self.state is not AppState.FINALE:
            return
        played_level = round_.level
        newly_all = len(self.dressed) < len(SEASONS)
        self.level = adapt_level(round_.level, round_.misses)
        self.dressed.add(round_.season)
        self.last_season = round_.season
        self.rounds = min(1_000_000, self.rounds + 1)
        newly_all = newly_all and len(self.dressed) == len(SEASONS)
        self.persist()
        self.events.season_dressed(
            self.session_id,
            {
                "season": round_.season.value,
                "level": played_level + 1,
                "missions": round_.total,
                "misses": round_.misses,
                "first_try": round_.first_try,
            },
        )
        if newly_all:
            self.events.all_seasons_dressed(self.session_id, {"total": len(SEASONS)})
        self.completion = PygameCompletionScreen(
            self.typography,
            width=REFERENCE_WIDTH,
            height=REFERENCE_HEIGHT,
            palette=CompletionPalette(background=FOREST),
            scene=CompletionScene(self.kit, character="tito", star_total=round_.total),
        )
        self.completion.prepare(
            CompletionContent(
                title=self._text("victory.title", "★"),
                primary_label=self._text("btn.play_again", "↻"),
                body_lines=(self._text(f"ready.{round_.season.value}", "★"),),
                achievement_count=round_.total,
            )
        )
        self._surfaces.push_overlay(CompletionOverlay(self.completion, on_primary=self._restart))
        self.timeline.clear()
        self.renderer.set_weather(None)
        self.state = AppState.TERMINAL
        self._busy = False
        self._dirty = True

    def _restart(self) -> None:
        self._activated = True
        if self.completion is not None:
            self._surfaces.pop_overlay()
            self.completion.clear()
            self.completion = None
        self.enter_picker()

    # -- hints ----------------------------------------------------------------------

    def _maybe_hint(self, now: float) -> None:
        round_ = self.round
        if round_ is None or self._busy or round_.mission is None:
            return
        if now - self._last_activity < IDLE_HINT_SECONDS * (self._idle_hints + 1):
            return
        self._idle_hints += 1
        mission = round_.mission
        answer = mission.options.index(mission.answer)
        self.cast.point(1.8)
        self.motion.glow_slot(mission.slot, now + GLOW_SECONDS)
        if self._idle_hints == 1:
            self.audio.say(round_.season.value)
        elif self._idle_hints == 2:
            self.motion.hop_card(answer, now)
        else:
            self.motion.hop_card(answer, now)
            self.motion.glow_card(answer, now + GLOW_SECONDS)
        self._dirty = True

    # -- helpers --------------------------------------------------------------------

    def _text(self, key: str, default: str, **variables: object) -> str:
        if self.resources is None:
            return default
        try:
            return self.resources.text(key, variables or None) or default
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


__all__ = ["AppState", "Timeline", "TreeActivity"]
