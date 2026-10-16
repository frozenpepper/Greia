"""Lifecycle, timing and input for Cloud Bedtime (Nanna delle Nuvolette).

Three little clouds are getting sleepy over the night hills. Each one dreams
of a quilt (the dream bubble shows its colour and, on later nights, a small
number of stars). The child tucks every cloud in with the quilt it dreams
of, picking a quilt from the tray and giving it to a cloud: tap the quilt,
then tap the cloud, or drag it there; keyboard, D-pad/stick and the south
button move the shared focus ring over the same quilts and clouds.

* the dreamed quilt flies onto the cloud; Momo cheers softly, the cloud
  yawns, closes its eyes and the sky darkens a little (a music-box note);
* any other quilt rests on the cloud for a moment while it slowly shakes its
  head, then floats back to the tray (it may suit another cloud); Momo
  thinks, the dream glows and the right quilt hops (and glows after a second
  miss); retries are unlimited and there is never a failure sound;
* idle ~6 s -> sleepy Momo points and the next dream glows; later the right
  quilt hops, then glows.

When all three are asleep the moon glows, a shooting star crosses the sky,
a tiny lullaby plays, and the shared cast completion scene appears
("another night"). The ladder (colour -> stars -> both) adapts per night.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
import math
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
from greia_platform.input_core import InputEdge, SemanticAction, SemanticInputEvent
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
    from .cloud_art import CloudArt
    from .cloud_audio import LULLABY, CloudAudio
    from .cloud_content import CLOUDS_PER_NIGHT, REFERENCE_HEIGHT, REFERENCE_WIDTH, plan_night
    from .cloud_controls import CloudControls
    from .cloud_layout import (
        MOMO_HEIGHT,
        MOMO_TAP_RECT,
        MOON_CENTER,
        MOON_TAP_RECT,
        cloud_box,
        cloud_hit,
        tile_rects,
    )
    from .cloud_model import BedtimeNight, Offer, adapt_level
    from .cloud_renderer import (
        FLY_SECONDS,
        TRY_HOLD_SECONDS,
        CloudRenderer,
        Flight,
        MomoCast,
        SceneMotion,
        SceneView,
        TrayTile,
    )
    from .cloud_services import BedtimeProgress, EventPort, ProgressPort
else:
    from cloud_art import CloudArt
    from cloud_audio import LULLABY, CloudAudio
    from cloud_content import CLOUDS_PER_NIGHT, REFERENCE_HEIGHT, REFERENCE_WIDTH, plan_night
    from cloud_controls import CloudControls
    from cloud_layout import (
        MOMO_HEIGHT,
        MOMO_TAP_RECT,
        MOON_CENTER,
        MOON_TAP_RECT,
        cloud_box,
        cloud_hit,
        tile_rects,
    )
    from cloud_model import BedtimeNight, Offer, adapt_level
    from cloud_renderer import (
        FLY_SECONDS,
        TRY_HOLD_SECONDS,
        CloudRenderer,
        Flight,
        MomoCast,
        SceneMotion,
        SceneView,
        TrayTile,
    )
    from cloud_services import BedtimeProgress, EventPort, ProgressPort

IDLE_HINT_SECONDS = 6.0
INTRO_SECONDS = 1.1
YAWN_SECONDS = 1.6
SETTLE_SECONDS = 1.2
FINALE_SECONDS = 4.4
GLOW_SECONDS = 2.4
MAX_SCHEDULED = 48
# A press that moves less than this (logical px) before release is a tap, not a
# drag: a tapped quilt stays in hand until a cloud is tapped (tap-then-tap).
DRAG_THRESHOLD_PX = 14
NIGHT_NAVY = (37, 59, 89)  # theme text-ink token "navy"


class AppState(StrEnum):
    INTRO = "intro"
    PLAYING = "playing"
    FINALE = "finale"
    TERMINAL = "terminal"


class Timeline:
    """Tiny bounded scheduler for the scripted bedtime moments."""

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


@dataclass(slots=True)
class _Press:
    kind: str  # "tile" | "cloud" | "other"
    index: int
    start: tuple[int, int]
    moved: bool = False


class CloudActivity:
    """Coordinate the night model, kit focus, art, audio and lifecycle."""

    def __init__(
        self,
        *,
        screen: pygame.Surface,
        canvas: PygameReferenceCanvas,
        typography: GreiaTypography,
        resources: LocalizedResources | None,
        audio: CloudAudio,
        progress: ProgressPort,
        events: EventPort,
        rng: random.Random | None = None,
        clock: Callable[[], float] = time.monotonic,
        kit: ControlKit | None = None,
        art: CloudArt | None = None,
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
        self._nights_played = 0

        saved = progress.load()
        self.level = saved.level
        self.nights = saved.nights

        # Shared control kit (ADR 0037): play Collection -> ocean accent.
        self.kit = kit if kit is not None else ControlKit(typography, ControlTheme.for_accent("ocean"))
        self.art = art if art is not None else CloudArt(loader=ControlArt(max_entries=64))
        feedback = CastFeedback("momo", height=MOMO_HEIGHT, art=self.art.loader, idle_variant="sleepy", clock=clock)
        self.cast = MomoCast(feedback, self.art, clock)
        self.renderer = CloudRenderer(self.art, self.cast)
        self.motion = SceneMotion()
        self.timeline = Timeline(clock)
        self.controls = CloudControls(self.kit, on_tile=self._on_tile_key, on_cloud=self._on_cloud_key)
        self._surfaces = SurfaceNavigator(self.controls.layer)
        self._input = PygameControlInput(to_logical=canvas.pointer, is_safe=lambda pos: _safe_point(self.screen, pos))
        self.controls.place_bar(ControlLayout.for_canvas(canvas, screen.get_size()))

        self.night: BedtimeNight | None = None
        self.tiles: tuple[TrayTile, ...] = ()
        self.completion: PygameCompletionScreen | None = None
        self.state = AppState.INTRO
        self.session_id = ""
        self.held: int | None = None
        self.dragging: tuple[int, int] | None = None
        self.hovered_tile: int | None = None
        self.hovered_cloud: int | None = None
        self.dim_step = 0
        self._press: _Press | None = None
        self._busy_until = 0.0
        self._intro_start = clock()
        self._finale_start = 0.0
        self._running = True
        self.ready_published = False
        self._dirty = True
        self._last_activity = clock()
        self._last_frame = clock()
        self._idle_hints = 0
        self.start_night()

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
                lively = self.step()
                if self._dirty or self._ambient_due():
                    self.render()
                    self.canvas.present()
                    pygame.display.flip()
                    self._dirty = False
                    self._last_frame = self.clock()
                    if not self.ready_published:
                        mark_activity_ready()
                        self.ready_published = True
                ticker.tick(30 if lively else 15)
        finally:
            self.persist()
            self.typography.clear()
        return 0

    def step(self) -> bool:
        """Advance timers; return True while something moves quickly on screen."""

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
        if self.state is AppState.TERMINAL:
            return False
        lively = (
            self.motion.active(now)
            or self.cast.animating
            or self.state in (AppState.INTRO, AppState.FINALE)
            or self.dragging is not None
        )
        if lively:
            self._dirty = True
        return lively

    def _ambient_due(self) -> bool:
        # The clouds float and breathe slowly: ~8 redraws a second is plenty.
        return self.state is not AppState.TERMINAL and self.clock() - self._last_frame >= 0.125

    def render(self) -> None:
        surface = self.canvas.surface
        if self.state is not AppState.TERMINAL and self.night is not None:
            now = self.clock()
            self.renderer.draw(surface, self._view(now), self.motion, now)
        self._surfaces.draw(surface)

    def _view(self, now: float) -> SceneView:
        assert self.night is not None
        intro = 1.0
        if self.state is AppState.INTRO:
            intro = max(0.0, min(1.0, (now - self._intro_start) / INTRO_SECONDS))
        glow = 0.0
        if self.state in (AppState.FINALE, AppState.TERMINAL):
            t = now - self._finale_start
            glow = min(1.0, t / 1.2) * (0.75 + 0.25 * math.sin(t * 2.2))
        return SceneView(
            clouds=self.night.clouds,
            tiles=self.tiles,
            dim_step=self.dim_step,
            held=self.held,
            dragging=self.dragging,
            hovered_tile=self.hovered_tile,
            hovered_cloud=self.hovered_cloud if self.held is not None else None,
            moon_glow=glow,
            show_dreams=self.state is not AppState.FINALE,
            intro=intro,
        )

    def persist(self) -> None:
        self.progress.save(BedtimeProgress(level=self.level, nights=self.nights))

    # -- input --------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self._running = False
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self.held is not None or self.dragging is not None:
                self._put_back()
            else:
                self._running = False
            return
        if event.type == pygame.VIDEORESIZE:
            self._resize()
            return
        if event.type == pygame.WINDOWFOCUSLOST:
            self._put_back()
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

    def _dispatch(self, kit_input) -> None:
        if isinstance(kit_input, KitPointer):
            if kit_input.phase is not PointerPhase.MOVE:
                self._note_activity()
            if self._surfaces.overlays:
                self._surfaces.dispatch(kit_input)
            else:
                self._pointer(kit_input)
        elif isinstance(kit_input, SemanticInputEvent):
            self._note_activity()
            if kit_input.action is SemanticAction.CANCEL and kit_input.edge is InputEdge.PRESSED and not self._surfaces.overlays:
                self._put_back()
            else:
                self._surfaces.dispatch(kit_input)
        if self.controls.layer.invalidation.should_draw:
            self._dirty = True

    def _pointer(self, sample: KitPointer) -> None:
        point = sample.position
        if sample.phase is PointerPhase.MOVE:
            self._hover(point)
            press = self._press
            if press is None:
                return
            if (
                press.kind == "tile"
                and not press.moved
                and math.hypot(point[0] - press.start[0], point[1] - press.start[1]) > DRAG_THRESHOLD_PX
            ):
                press.moved = True
                self.held = press.index
                self.audio.play("pick")
            if press.moved:
                self.dragging = point
                self._dirty = True
            return
        if sample.phase is PointerPhase.CANCEL:
            self._press = None
            self._put_back()
            return
        if sample.phase is PointerPhase.DOWN:
            self.controls.layer.focus_visible = False
            self._press = self._press_at(point)
            if self._press.kind == "other":
                self._ambient_tap(point)
            self._dirty = True
            return
        # UP
        press, self._press = self._press, None
        if press is None:
            return
        if press.moved:
            self.dragging = None
            cloud = self._cloud_at(point)
            if cloud is not None and self.held is not None:
                self._give(self.held, cloud, origin=point)
            else:
                self._put_back(origin=point)
        elif press.kind == "tile":
            self._pick(press.index)
        elif press.kind == "cloud":
            self._cloud_tapped(press.index)
        elif self.held is not None:
            self._put_back()
        self._dirty = True

    def _press_at(self, point: tuple[int, int]) -> _Press:
        if self.state is AppState.PLAYING:
            tile = self._tile_at(point)
            if tile is not None:
                return _Press("tile", tile, point)
            cloud = self._cloud_at(point)
            if cloud is not None:
                return _Press("cloud", cloud, point)
        return _Press("other", -1, point)

    def _hover(self, point: tuple[int, int]) -> None:
        tile = self._tile_at(point) if self.state is AppState.PLAYING else None
        cloud = self._cloud_at(point) if self.state is AppState.PLAYING else None
        if (tile, cloud) != (self.hovered_tile, self.hovered_cloud):
            self.hovered_tile, self.hovered_cloud = tile, cloud
            self._dirty = True

    def _tile_at(self, point: tuple[int, int]) -> int | None:
        flying = self.motion.flying_tiles(self.clock())
        for index, tile in enumerate(self.tiles):
            if tile.quilt is not None and index not in flying and tile.rect.collidepoint(point):
                return index
        return None

    def _cloud_at(self, point: tuple[int, int]) -> int | None:
        if self.night is None:
            return None
        for cloud in self.night.clouds:
            if cloud.awake and cloud_hit(cloud.index).collidepoint(point):
                return cloud.index
        return None

    def tap(self, logical: tuple[int, int]) -> None:
        """Deliver one complete tap at a logical position (tests/tools)."""

        point = (int(logical[0]), int(logical[1]))
        self._dispatch(KitPointer(PointerPhase.DOWN, point))
        self._dispatch(KitPointer(PointerPhase.UP, point))

    def drag(self, start: tuple[int, int], end: tuple[int, int], steps: int = 6) -> None:
        """Deliver one complete drag in logical coordinates (tests/tools)."""

        self._dispatch(KitPointer(PointerPhase.DOWN, start))
        for step in range(1, steps + 1):
            t = step / steps
            self._dispatch(KitPointer(PointerPhase.MOVE, (int(start[0] + (end[0] - start[0]) * t), int(start[1] + (end[1] - start[1]) * t))))
        self._dispatch(KitPointer(PointerPhase.UP, end))

    def press(self, key: int) -> None:
        """Deliver one key press through the shared navigation mapping."""

        self.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode=""))

    def _note_activity(self) -> None:
        self._last_activity = self.clock()
        self._idle_hints = 0

    def _ambient_tap(self, point: tuple[int, int]) -> None:
        """Free, wordless exploration: the moon twinkles, Momo murmurs."""

        if self.state is AppState.TERMINAL:
            return
        now = self.clock()
        if MOON_TAP_RECT.collidepoint(point):
            self.motion.add_fx("sparkle", MOON_CENTER, now)
            self.audio.play("twinkle")
        elif MOMO_TAP_RECT.collidepoint(point) and not self.cast.animating:
            self.audio.play("twinkle")
        if self.held is not None:
            self._put_back()

    # -- picking and giving -------------------------------------------------------

    def _on_tile_key(self, index: int) -> None:
        """Keyboard/controller: pick the focused quilt up, then go to the clouds."""

        if self._pick(index) and self.held == index and self.night is not None:
            target = self.night.next_awake()
            if target is not None:
                self.controls.focus_cloud(target)

    def _on_cloud_key(self, index: int) -> None:
        self._cloud_tapped(index)
        if self.held is None:
            self.controls.focus_first_tile()

    def _pick(self, index: int) -> bool:
        if self.state is not AppState.PLAYING or not 0 <= index < len(self.tiles):
            return False
        if self.tiles[index].quilt is None or index in self.motion.flying_tiles(self.clock()):
            return False
        if self.held == index:
            self.held = None  # tapping the quilt in hand puts it back
        else:
            self.held = index
            self.audio.play("pick")
        self._dirty = True
        return True

    def _cloud_tapped(self, cloud: int) -> None:
        if self.state is not AppState.PLAYING:
            return
        if self.held is not None:
            self._give(self.held, cloud, origin=self.tiles[self.held].rect.center)
        else:
            self._poke(cloud)

    def _poke(self, cloud: int) -> None:
        """An empty-handed tap: the cloud bobs and shows its dream again."""

        now = self.clock()
        self.motion.poke(cloud, now)
        self.motion.glow_bubble(cloud, now + 1.2)
        self.audio.play("twinkle")
        self._dirty = True

    def _put_back(self, origin: tuple[int, int] | None = None) -> None:
        held, self.held = self.held, None
        self.dragging = None
        self._press = None
        if held is not None and origin is not None and 0 <= held < len(self.tiles):
            quilt = self.tiles[held].quilt
            if quilt is not None:
                now = self.clock()
                self.motion.fly(Flight(quilt, self.art.tile_quilt(quilt), origin, self.tiles[held].rect.center, now, False, -1, held))
        self._dirty = True

    def _give(self, tray_index: int, cloud: int, *, origin: tuple[int, int]) -> None:
        night = self.night
        now = self.clock()
        if night is None or self.state is not AppState.PLAYING or now < self._busy_until:
            return
        quilt = self.tiles[tray_index].quilt if 0 <= tray_index < len(self.tiles) else None
        outcome = night.offer(tray_index, cloud)
        if outcome.offer is Offer.IGNORED or quilt is None:
            return
        self.held = None
        self.dragging = None
        image = self.art.tile_quilt(quilt)
        target = cloud_box(cloud).move(0, 40).center
        if outcome.offer is Offer.RIGHT:
            self.motion.fly(Flight(quilt, image, origin, target, now, False, cloud, tray_index))
            self._busy_until = now + FLY_SECONDS
            self.timeline.after(FLY_SECONDS, lambda: self._tucked(cloud, tray_index))
        else:
            self.motion.fly(Flight(quilt, image, origin, target, now, True, cloud, tray_index))
            self._busy_until = now + 2 * FLY_SECONDS + TRY_HOLD_SECONDS
            misses = outcome.cloud_misses
            self.timeline.after(FLY_SECONDS, lambda: self._declined(cloud, misses))
            self.timeline.after(2 * FLY_SECONDS + TRY_HOLD_SECONDS, lambda: self._demonstrate(cloud, misses))
        self.audio.play("pick")
        self._sync_controls()
        self._dirty = True

    def _tucked(self, cloud: int, tray_index: int) -> None:
        if self.state is not AppState.PLAYING or self.night is None:
            return
        now = self.clock()
        self.tiles = tuple(
            TrayTile(None, tile.rect) if index == tray_index else tile for index, tile in enumerate(self.tiles)
        )
        box = cloud_box(cloud)
        self.motion.add_fx("sparkle", (box.centerx - 104, box.y + 64), now)
        self.motion.add_fx("sparkle", (box.centerx + 100, box.y + 52), now + 0.25)
        self.audio.play("rustle")
        self.cast.correct()
        self.audio.momo("praise.general")
        self.timeline.after(0.5, lambda: self.audio.play("yawn"))
        self.timeline.after(YAWN_SECONDS, lambda: self._asleep(cloud))
        self._sync_controls()
        if self.controls.layer.focus_visible:
            self.controls.focus_first_tile()
        self._dirty = True

    def _asleep(self, cloud: int) -> None:
        night = self.night
        if night is None or self.state is not AppState.PLAYING or not night.fall_asleep(cloud):
            return
        now = self.clock()
        previous = self.dim_step
        self.dim_step = night.asleep_count
        self.motion.fade(previous, now)
        self.audio.play(f"sleep_{min(2, night.asleep_count - 1)}")
        self.controls.set_progress(night.asleep_count)
        if night.complete:
            self.timeline.after(SETTLE_SECONDS, self._finale)
        self._dirty = True

    def _declined(self, cloud: int, misses: int) -> None:
        if self.state is not AppState.PLAYING:
            return
        self.motion.shake(cloud, self.clock())
        self.audio.play("hush")
        self.cast.try_again()
        if misses % 2 == 0:
            self.audio.momo("encourage.retry")
        self._dirty = True

    def _demonstrate(self, cloud: int, misses: int) -> None:
        """Show the way: the dream glows and the right quilt hops (glows after two misses)."""

        night = self.night
        if night is None or self.state is not AppState.PLAYING:
            return
        now = self.clock()
        self.motion.glow_bubble(cloud, now + GLOW_SECONDS)
        answer = night.answer_for(cloud)
        if answer is not None:
            self.motion.hop_tile(answer, now)
            if misses >= 2:
                self.motion.glow_tile(answer, now + GLOW_SECONDS)
                self.cast.point(1.4)
        self._sync_controls()
        self._note_activity()
        self._dirty = True

    # -- night flow -----------------------------------------------------------------

    def start_night(self) -> None:
        now = self.clock()
        self.timeline.clear()
        self.motion.reset()
        self.cast.reset()
        plan = plan_night(self.level, self.rng)
        self.night = BedtimeNight(self.level, plan)
        rects = tile_rects(len(plan.tray))
        self.tiles = tuple(TrayTile(quilt, rect) for quilt, rect in zip(plan.tray, rects))
        self.controls.set_tray(rects)
        self.controls.set_progress(0)
        self.held = None
        self.dragging = None
        self._press = None
        self.dim_step = 0
        self._busy_until = 0.0
        self.state = AppState.INTRO
        self._intro_start = now
        self._nights_played += 1
        self.session_id = f"{self._session_prefix}-{self._nights_played}-{self.rng.randrange(1_000_000):06d}"
        self._sync_controls()
        self.timeline.after(INTRO_SECONDS, self._begin)
        self._note_activity()
        self._dirty = True

    def _begin(self) -> None:
        if self.state is not AppState.INTRO or self.night is None:
            return
        self.state = AppState.PLAYING
        now = self.clock()
        # Wordless start: each dream glows in turn while Momo points at them.
        self.cast.point(1.8)
        for index in range(CLOUDS_PER_NIGHT):
            self.timeline.after(0.45 * index, lambda i=index: self._show_dream(i))
        self.motion.glow_bubble(0, now + 0.5)
        self.audio.play("twinkle")
        self._sync_controls()
        self.controls.focus_first_tile()
        self._note_activity()
        self._dirty = True

    def _show_dream(self, cloud: int) -> None:
        if self.state is AppState.PLAYING:
            self.motion.glow_bubble(cloud, self.clock() + 0.6)
            self._dirty = True

    def _finale(self) -> None:
        if self.state is not AppState.PLAYING or self.night is None:
            return
        now = self.clock()
        self.state = AppState.FINALE
        self._finale_start = now
        self.held = None
        self.dragging = None
        self.cast.reset()
        self.motion.shooting = now + 0.9
        for delay, note in LULLABY:
            self.timeline.after(0.4 + delay, lambda n=note: self.audio.play(n))
        self.timeline.after(FINALE_SECONDS, self._complete)
        self._sync_controls()
        self._dirty = True

    def _complete(self) -> None:
        night = self.night
        if night is None or self.state is not AppState.FINALE:
            return
        played_level = night.level
        self.level = adapt_level(night.level, night.misses)
        self.nights = min(1_000_000, self.nights + 1)
        self.persist()
        self.events.rest_completed(
            self.session_id,
            {
                "night_id": self.session_id,
                "cloud_count": CLOUDS_PER_NIGHT,
                "star_count": night.stars_given,
                "level": played_level + 1,
                "misses": night.misses,
                "first_try": night.first_try,
            },
        )
        self.audio.momo("celebrate.success")
        self.completion = PygameCompletionScreen(
            self.typography,
            width=REFERENCE_WIDTH,
            height=REFERENCE_HEIGHT,
            palette=CompletionPalette(background=NIGHT_NAVY),
            scene=CompletionScene(self.kit, character="momo", star_total=CLOUDS_PER_NIGHT),
        )
        self.completion.prepare(
            CompletionContent(
                title=self._text("victory.title", "Zzz"),
                primary_label=self._text("btn.another_night", "↻"),
                body_lines=(self._text("victory.body", ""),),
                achievement_count=CLOUDS_PER_NIGHT,
            )
        )
        self._surfaces.push_overlay(CompletionOverlay(self.completion, on_primary=self._restart))
        self.timeline.clear()
        self.state = AppState.TERMINAL
        self._dirty = True

    def _restart(self) -> None:
        if self.completion is not None:
            self._surfaces.pop_overlay()
            self.completion.clear()
            self.completion = None
        self.start_night()

    # -- hints ----------------------------------------------------------------------

    def _maybe_hint(self, now: float) -> None:
        night = self.night
        if night is None or now < self._busy_until or self.dragging is not None:
            return
        if now - self._last_activity < IDLE_HINT_SECONDS * (self._idle_hints + 1):
            return
        cloud = night.next_awake()
        if cloud is None:
            return
        self._idle_hints += 1
        self.cast.point(1.8)
        self.motion.glow_bubble(cloud, now + GLOW_SECONDS)
        answer = night.answer_for(cloud)
        if answer is not None and self._idle_hints >= 2:
            self.motion.hop_tile(answer, now)
            if self._idle_hints >= 3:
                self.motion.glow_tile(answer, now + GLOW_SECONDS)
        self._dirty = True

    # -- helpers --------------------------------------------------------------------

    def _sync_controls(self) -> None:
        night = self.night
        playing = self.state is AppState.PLAYING
        self.controls.sync(
            tiles_present=[tile.quilt is not None for tile in self.tiles],
            clouds_awake=[cloud.awake for cloud in night.clouds] if night is not None else [False] * CLOUDS_PER_NIGHT,
            playing=playing,
        )

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


__all__ = ["AppState", "CloudActivity", "DRAG_THRESHOLD_PX", "Timeline"]
