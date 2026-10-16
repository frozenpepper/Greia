"""Baia delle Orche — Activity lifecycle, input routing and simulation clock.

:class:`OrcaBayActivity` owns:

- the Pygame screen / reference canvas pair;
- the shared control kit (modes, food tray, sea bells, day/night, Tito,
  invitation banner, counters, focus) and its input translator, so pointer,
  touch, keyboard and controller all reach the same actions;
- the pod (model), the optional invitation director, Tito (cast), audio,
  renderer and persistence of the child's bay.

The bay is a free toy: every mode works at any time, the orcas can always be
fed, cuddled, made to jump and sung to, and the optional invitations never
interrupt play. Collaborators are injected so the loop can be tested headlessly.
"""

from __future__ import annotations

from collections.abc import Callable
import random
import time
from typing import Any

import pygame

from greia_platform.activity_api import (
    activity_stop_requested,
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
from greia_platform.input_core import InputEdge, SemanticAction, SemanticInputEvent
from greia_platform.pygame_blit import HudOverlay
from greia_platform.pygame_canvas import PygameReferenceCanvas, activity_viewport_for_surface
from greia_platform.ui_core import SurfaceNavigator, UiEventResult
from greia_platform.frame_governor import FrameGovernor, FrameKind

try:
    from orca_audio import OrcaAudio
    from orca_cast import OrcaCast
    from orca_content import (
        AUTOSAVE_INTERVAL_SECONDS,
        CONTROL_ACCENT,
        FACT_SECONDS,
        HOOP_SIZE,
        MAX_SAVED_STARS,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        WATER_SURFACE_Y,
        FoodType,
        Tool,
    )
    from orca_controls import BAY_ID, CAST_HEIGHT, CAST_MIDBOTTOM, OrcaControls
    from orca_missions import MissionDirector, MissionKind, MissionOutcome
    from orca_model import OrcaEntity, OrcaPod, OrcaState
    from orca_renderer import OrcaRenderer, now_seconds
    from orca_services import GreiaOrcaEvents, GreiaOrcaProgress
except ImportError:
    from .orca_audio import OrcaAudio
    from .orca_cast import OrcaCast
    from .orca_content import (
        AUTOSAVE_INTERVAL_SECONDS,
        CONTROL_ACCENT,
        FACT_SECONDS,
        HOOP_SIZE,
        MAX_SAVED_STARS,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        WATER_SURFACE_Y,
        FoodType,
        Tool,
    )
    from .orca_controls import BAY_ID, CAST_HEIGHT, CAST_MIDBOTTOM, OrcaControls
    from .orca_missions import MissionDirector, MissionKind, MissionOutcome
    from .orca_model import OrcaEntity, OrcaPod, OrcaState
    from .orca_renderer import OrcaRenderer, now_seconds
    from .orca_services import GreiaOrcaEvents, GreiaOrcaProgress

# Keyboard/controller cursor bounds in the bay (logical px).
CURSOR_MIN = (60, 190)
CURSOR_STEP = 48
KEY_HINT_START_SECONDS = 8.0  # keyboard hint shown at start (ADR 0037 §4b)
_DIRECTIONS = {
    SemanticAction.NAV_LEFT: (-1, 0),
    SemanticAction.NAV_RIGHT: (1, 0),
    SemanticAction.NAV_UP: (0, -1),
    SemanticAction.NAV_DOWN: (0, 1),
    SemanticAction.MOVE_LEFT: (-1, 0),
    SemanticAction.MOVE_RIGHT: (1, 0),
    SemanticAction.MOVE_UP: (0, -1),
    SemanticAction.MOVE_DOWN: (0, 1),
}
# Direct keyboard shortcuts (arrows/Space/Enter belong to the kit).
_TOOL_KEYS = {
    pygame.K_1: Tool.FEED,
    pygame.K_2: Tool.CUDDLE,
    pygame.K_3: Tool.PLAY,
    pygame.K_4: Tool.SONG,
    pygame.K_5: Tool.DAY_NIGHT,
    pygame.K_6: Tool.TITO,
    pygame.K_n: Tool.DAY_NIGHT,
    pygame.K_t: Tool.TITO,
}
_BELL_LIT_SECONDS = 0.25


class OrcaBayActivity:
    """Lifecycle owner for Baia delle Orche (one free-play bay, no rounds)."""

    def __init__(
        self,
        screen: pygame.Surface,
        canvas: PygameReferenceCanvas,
        pod: OrcaPod,
        renderer: OrcaRenderer,
        audio: OrcaAudio,
        progress: GreiaOrcaProgress,
        events: GreiaOrcaEvents,
        *,
        missions_enabled: bool = True,
        rng: random.Random | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.screen = screen
        self.canvas = canvas
        self.pod = pod
        self.renderer = renderer
        self.audio = audio
        self.progress = progress
        self.events = events
        self._clock = clock

        self._frame_clock = pygame.time.Clock()
        self._running = True
        self._ready_published = False
        self._last_save_time = clock()
        # One reward per orca per contact gesture, not per rendered frame.
        self._gesture_cuddled_ids: set[str] = set()
        self._pointer_down = False
        self._bells_rung: dict[int, float] = {}
        self._hinted = False
        self.keyboard_cursor: tuple[int, int] = (REFERENCE_WIDTH // 2, int(WATER_SURFACE_Y) + 100)

        self._kit = ControlKit(renderer.typography, ControlTheme.for_accent(CONTROL_ACCENT))
        renderer.bind_kit(self._kit)
        self._controls = OrcaControls(
            self._kit,
            renderer.resources,
            ControlLayout.for_canvas(canvas, screen.get_size()),
            renderer.assets,
            cursor=lambda: self.keyboard_cursor,
            on_mode=self.handle_tool_click,
            on_food=self._choose_food,
            on_bell=self._ring_bell,
            on_day_night=lambda: self.handle_tool_click(Tool.DAY_NIGHT),
            on_tito=lambda: self.handle_tool_click(Tool.TITO),
            on_bay=self._act_at_cursor,
            on_hint=self._request_hint,
            clock=clock,
        )
        # Keyboard hint (ADR 0037 §4b): shown for a few seconds at start.
        self._controls.keys.show(KEY_HINT_START_SECONDS)
        self._keys_changed = False
        self._surfaces = SurfaceNavigator(self._controls.layer)
        # The kit controls are composed once into an RLE overlay and re-composed
        # only when the layer is invalidated (greia_platform.pygame_blit).
        self._hud = HudOverlay()
        self._input = self._make_input()
        self._missions = MissionDirector(rng=rng, enabled=missions_enabled)
        self._cast = OrcaCast(self._kit.art, height=CAST_HEIGHT, clock=clock)
        self._sync_controls()

    # ------------------------------------------------------------------
    # Pointer safety
    # ------------------------------------------------------------------

    def _safe_pointer(self, position: tuple[int, int]) -> bool:
        """Reject coordinates outside the Activity or inside trusted Home/Back."""

        viewport = activity_viewport_for_surface(self.screen)
        x, y = position
        return (
            0 <= x < viewport.surface.width
            and 0 <= y < viewport.surface.height
            and not any(
                region.x <= x < region.right and region.y <= y < region.bottom
                for region in viewport.protected_regions
            )
        )

    def _make_input(self) -> PygameControlInput:
        return PygameControlInput(to_logical=self.canvas.pointer, is_safe=self._safe_pointer)

    # ------------------------------------------------------------------
    # Tools and actions
    # ------------------------------------------------------------------

    def handle_tool_click(self, tool_idx: int) -> None:
        """One toolbar press: choose the mode and give an immediate response."""

        if tool_idx == Tool.DAY_NIGHT:
            self._toggle_night()
            return
        if tool_idx == Tool.TITO:
            self._tell_fact()
            return
        if tool_idx not in (Tool.FEED, Tool.CUDDLE, Tool.PLAY, Tool.SONG):
            return
        self.pod.active_tool = tool_idx
        if tool_idx == Tool.FEED:
            self.pod.spawn_food(REFERENCE_WIDTH / 2, WATER_SURFACE_Y - 40.0)
            self.audio.play("splash")
        elif tool_idx == Tool.CUDDLE:
            self.audio.play("purr")
        elif tool_idx == Tool.PLAY:
            self._pod_breach(height_bonus=25.0)
            self.audio.play("splash")
            self.events.record_acrobatics("all", "pod_breach")
        elif tool_idx == Tool.SONG:
            self.audio.play("bell_0")
        self._sync_controls()

    def _toggle_night(self) -> None:
        self.pod.night_mode = not self.pod.night_mode
        self.audio.play("aurora")
        self.pod.emit_effect("sparkle", REFERENCE_WIDTH / 2, WATER_SURFACE_Y - 30.0, 1.2)
        self._sync_controls()

    def _choose_food(self, food: FoodType, drop_at: tuple[int, int]) -> None:
        """Food tray: pick a food and drop one straight into the bay."""

        self.pod.selected_food = food
        self.pod.active_tool = Tool.FEED
        self.pod.spawn_food(float(drop_at[0]), float(drop_at[1]))
        self.audio.play("splash")
        self._sync_controls()

    def _ring_bell(self, index: int) -> None:
        if not 0 <= index < 4:
            return
        from_x, bell_y = self._controls.bells[index].rect.center
        self._bells_rung[index] = now_seconds() + _BELL_LIT_SECONDS
        self.audio.play(f"bell_{index}")
        self.pod.emit_effect("note_burst", from_x, bell_y - 46, 0.9)
        self.pod.total_songs += 1
        self.events.record_song_completed(1)
        # The nearest orca answers the bell in song.
        singer = self.pod.nearest_orca(from_x)
        if not singer.airborne:
            singer.trigger_sing(index)
            singer.cheer()
        self.audio.play("clicks")

    def _pod_breach(self, *, height_bonus: float = 0.0) -> None:
        for orca in self.pod.orcas:
            if not orca.airborne:
                orca.trigger_breach(orca.x + orca.facing * 120.0, height_bonus=height_bonus)
                self._on_jump(orca)

    def _on_jump(self, orca: OrcaEntity) -> None:
        self._on_mission_outcome(self._missions.orca_jumped(orca.id), orca)

    def _play_fact(self) -> None:
        """Tito speaks the next approved fact (recorded audio only)."""

        fact_key = self.pod.trigger_fact()
        self.audio.play("aurora")
        # LocalizedResources has .context.selected, not .locale.
        selected_locale = self.renderer.resources.context.selected.value
        self.audio.play_voice(fact_key, selected_locale)
        self.events.record_fact_discovered(fact_key)

    def _tell_fact(self) -> None:
        """Toolbar/keyboard/Tito tap: next fact, with Tito and a little show."""

        self._play_fact()
        fact = self.pod.active_fact
        self._cast.talk(FACT_SECONDS)
        if fact == "fact_breach":
            luna = self.pod.orca("luna")
            if luna is not None and not luna.airborne:
                luna.trigger_breach(luna.x + luna.facing * 140.0, height_bonus=20.0)
                self._on_jump(luna)
        elif fact == "fact_song":
            for orca in self.pod.orcas:
                if not orca.airborne:
                    orca.trigger_sing(0)
            self.audio.play("whistle")

    def _cuddle_once(self, orca: OrcaEntity, *, drag: bool = False) -> bool:
        """Prevent repeated sounds/rewards while one finger stays down."""

        if orca.id in self._gesture_cuddled_ids:
            return False
        self._gesture_cuddled_ids.add(orca.id)
        orca.trigger_cuddle()
        self.audio.play("purr")
        if not drag:
            self.audio.play("whistle")
        self.pod.emit_effect("heart_pop", orca.x, orca.y - 30.0, 0.8 if drag else 1.0)
        self.pod.total_cuddled += 1
        self.events.record_cuddled(orca.id, "belly_rub")
        return True

    # ------------------------------------------------------------------
    # Gameplay at a logical point (pointer, touch, keyboard cursor)
    # ------------------------------------------------------------------

    def _act_at_cursor(self) -> None:
        self.handle_pointer_down(*self.keyboard_cursor)

    def handle_pointer_down(self, mx: float, my: float) -> None:
        """Activate one logical location in the bay, independent of input device."""

        self._gesture_cuddled_ids.clear()
        point = (int(mx), int(my))
        if self.pod.active_fact is not None and self.renderer.fact_banner_rect.collidepoint(point):
            self._tell_fact()
            return
        if self._cast.visible and self._tito_rect().collidepoint(point):
            self._tell_fact()
            return

        hits = [orca for orca in self.pod.orcas if orca.hit_test(mx, my)]
        if hits:
            # Overlapping orcas: the one whose body centre is nearest wins, so
            # little Kiko can still be reached when big Oskar swims past.
            touched = min(hits, key=lambda o: ((o.x - mx) / o.width) ** 2 + ((o.y - my) / o.height) ** 2)
            self._touch_orca(touched, mx)
            return

        hoop = self._hoop_rect()
        if hoop is not None and hoop.collidepoint(point):
            jumper = self.pod.nearest_orca(hoop.centerx)
            if not jumper.airborne:
                jumper.trigger_ring_jump(hoop.centerx, hoop.centery)
                self.audio.play("splash")
                self.events.record_acrobatics(jumper.id, "ring_leap")
                self._on_jump(jumper)
            return

        for toy in self.pod.toys:
            if toy.kind == "ball" and (toy.x - mx) ** 2 + (toy.y - 10 - my) ** 2 < 40.0 ** 2:
                toy.vx = (toy.x - mx) * 0.35
                toy.vy = -7.5
                self.audio.play("bounce")
                self.pod.emit_effect("splash", toy.x, toy.y, 0.6)
                return

        if not self._controls.bay_bounds.collidepoint(point):
            return
        tool = self.pod.active_tool
        if tool == Tool.FEED:
            self.pod.spawn_food(mx, my)
            self.audio.play("splash")
        elif tool == Tool.CUDDLE:
            self.pod.emit_effect("heart_pop", mx, my, 0.6)
            self.audio.play("bubble")
        elif tool == Tool.PLAY:
            jumper = self.pod.nearest_orca(mx)
            if not jumper.airborne:
                jumper.trigger_breach(mx)
                self.audio.play("splash")
                self.events.record_acrobatics(jumper.id, "target_leap")
                self._on_jump(jumper)
        elif tool == Tool.SONG:
            self.audio.play("whistle")
            self.pod.emit_effect("note_burst", mx, my, 0.7)

    def _touch_orca(self, orca: OrcaEntity, mx: float) -> None:
        orca.show_name()
        if self.pod.active_tool == Tool.PLAY and not orca.airborne:
            orca.trigger_breach(mx + orca.facing * 100.0)
            self.audio.play("splash")
            self.events.record_acrobatics(orca.id, "solo_breach")
            self._on_jump(orca)
        elif not orca.airborne:
            if self._cuddle_once(orca):
                orca.cheer()
        self._on_mission_outcome(self._missions.orca_touched(orca.id), orca)

    def _drag_cuddle(self, mx: float, my: float) -> None:
        if self.pod.active_tool != Tool.CUDDLE:
            return
        for orca in self.pod.orcas:
            if orca.hit_test(mx, my) and orca.state in (OrcaState.SWIMMING, OrcaState.SLEEPING):
                if self._cuddle_once(orca, drag=True):
                    orca.cheer()

    def _hoop_rect(self) -> pygame.Rect | None:
        for toy in self.pod.toys:
            if toy.kind == "ring":
                rect = pygame.Rect(0, 0, HOOP_SIZE[0] + 16, HOOP_SIZE[1] + 8)
                rect.center = (int(toy.x), int(toy.y))
                return rect
        return None

    @staticmethod
    def _tito_rect() -> pygame.Rect:
        return pygame.Rect(CAST_MIDBOTTOM[0] - 64, CAST_MIDBOTTOM[1] - CAST_HEIGHT, 128, CAST_HEIGHT)

    # ------------------------------------------------------------------
    # Invitations
    # ------------------------------------------------------------------

    def _request_hint(self) -> None:
        if self._missions.request_hint():
            self._show_hint()

    def _show_hint(self) -> None:
        """Graduated help: Tito points and the invited orca gets a ripple."""

        self._hinted = True
        mission = self._missions.current
        self._cast.point(mission.hints.animation_seconds(self._cast.POINT_SECONDS) if mission is not None else None)

    def _advance_missions(self, dt: float) -> None:
        meals = list(self.pod.meals)
        self.pod.meals.clear()
        for orca_id, food, _craved in meals:
            self._on_mission_outcome(self._missions.orca_ate(orca_id, food), self.pod.orca(orca_id))
        mission = self._missions.current
        if mission is not None and mission.kind is MissionKind.FEED and mission.food is not None:
            # The invited orca keeps asking for the invited food.
            target = self.pod.orca(mission.orca_id)
            if target is not None:
                target.craved_food = mission.food
        self._on_mission_outcome(self._missions.update(dt, daytime=not self.pod.night_mode), None)

    def _on_mission_outcome(self, outcome: MissionOutcome, orca: OrcaEntity | None) -> None:
        if outcome is MissionOutcome.NONE:
            return
        if outcome is MissionOutcome.HINT:
            self._show_hint()
            self._controls.keys.demonstrate()
        elif outcome is MissionOutcome.NOT_YET:
            # Kind try-again: the orca still enjoyed it; Tito thinks gently.
            self._cast.think()
        elif outcome in (MissionOutcome.STARTED, MissionOutcome.RETIRED):
            self._hinted = False
            if outcome is MissionOutcome.STARTED:
                self.audio.play("bubble")
                mission = self._missions.current
                if mission is not None and mission.food is not None:
                    target = self.pod.orca(mission.orca_id)
                    if target is not None:
                        target.craved_food = mission.food
        elif outcome in (MissionOutcome.COMPLETED, MissionOutcome.STAR):
            self._hinted = False
            if orca is not None:
                orca.cheer(2.0)
                self.pod.emit_effect("star_burst", orca.x, orca.y - 20.0)
            self._cast.cheer()
            star = outcome is MissionOutcome.STAR
            completed = self._missions.last_completed
            kind = completed.kind.value if completed is not None else "mission"
            self.events.record_mission_completed(kind, star=star)
            if star:
                self.pod.stars = min(MAX_SAVED_STARS, self.pod.stars + 1)
                self._celebrate_pod()
                self.audio.say("praise.general")
            else:
                self.audio.say("celebrate.success")
        self._sync_controls()

    def _celebrate_pod(self) -> None:
        """Every third invitation: the whole pod leaps together."""

        for orca in self.pod.orcas:
            if not orca.airborne:
                orca.trigger_breach(orca.x + orca.facing * 120.0, height_bonus=35.0)
            orca.cheer(2.4)
        self.pod.emit_effect("confetti", REFERENCE_WIDTH / 2, WATER_SURFACE_Y - 110.0, 1.0, life=1.1)
        self.audio.play("splash")

    @property
    def mission_hint_orca(self) -> str | None:
        mission = self._missions.current
        if mission is None or not self._hinted:
            return None
        return mission.orca_id

    @property
    def mission_wanted(self) -> tuple[str, str] | None:
        mission = self._missions.current
        if mission is None or mission.kind is not MissionKind.FEED or mission.food is None:
            return None
        return (mission.orca_id, mission.food.value)

    def _sync_controls(self) -> None:
        controls = self._controls
        controls.sync_mode(self.pod.active_tool)
        controls.sync_food(self.pod.selected_food)
        controls.sync_day_night(self.pod.night_mode)
        mission = self._missions.current
        if mission is None:
            controls.set_mission(None, None, None, self._missions.done_in_set)
        else:
            controls.set_mission(
                mission.kind.value,
                mission.orca_id,
                mission.food.value if mission.food is not None else None,
                self._missions.done_in_set,
            )
        controls.set_counters(self.pod.total_fed, self.pod.total_cuddled, self.pod.stars)
        self._cast.present(mission is not None)

    # ------------------------------------------------------------------
    # Event routing
    # ------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self._running = False
            return
        self._controls.keys.observe_event(event)  # its look keys the cached HUD
        if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION) and getattr(event, "touch", False):
            # SDL duplicates touch as synthetic mouse input on some devices;
            # the FINGER* event is the one acted on.
            return
        if event.type == pygame.KEYDOWN:
            self._handle_keydown(event)
            return
        if event.type == pygame.VIDEORESIZE:
            self._handle_resize()
            return
        if event.type in (pygame.FINGERDOWN, pygame.FINGERUP, pygame.FINGERMOTION):
            width, height = self.screen.get_size()
            position = (int(event.x * width), int(event.y * height))
            phase = {
                pygame.FINGERDOWN: PointerPhase.DOWN,
                pygame.FINGERUP: PointerPhase.UP,
                pygame.FINGERMOTION: PointerPhase.MOVE,
            }[event.type]
            self._handle_pointer_phase(phase, position)
            return
        translated = self._input.translate(event)
        if translated is not None:
            self._route(translated)

    def _handle_keydown(self, event: pygame.event.Event) -> None:
        if event.key == pygame.K_ESCAPE:
            self._running = False
            return
        tool = _TOOL_KEYS.get(event.key)
        if tool is not None:
            self.handle_tool_click(tool)
            return
        translated = self._input.translate(event)
        if translated is not None:
            self._route(translated)

    def _handle_resize(self) -> None:
        new_screen = pygame.display.get_surface()
        if new_screen is None:
            return
        self.screen = new_screen
        self.canvas = PygameReferenceCanvas(new_screen)
        self._input = self._make_input()
        self._controls.relayout(ControlLayout.for_canvas(self.canvas, new_screen.get_size()))

    def tap(self, position: tuple[int, int]) -> None:
        """Deliver one complete tap at a physical position (touch, tools, tests)."""

        self._handle_pointer_phase(PointerPhase.DOWN, position)
        self._handle_pointer_phase(PointerPhase.UP, position)

    def _handle_pointer_phase(self, phase: PointerPhase, position: tuple[int, int]) -> None:
        if not self._safe_pointer(position):
            if phase is PointerPhase.UP:
                self._route(KitPointer(PointerPhase.CANCEL, (-1, -1)))
            return
        logical = self.canvas.pointer(position)
        if logical is None:
            if phase is PointerPhase.UP:
                self._route(KitPointer(PointerPhase.CANCEL, (-1, -1)))
            return
        self._route(KitPointer(phase, (int(logical[0]), int(logical[1]))))

    def _route(self, kit_input: Any) -> None:
        """Send one kit input to the controls; unconsumed taps are gameplay."""

        if isinstance(kit_input, SemanticInputEvent) and self._route_bay_navigation(kit_input):
            return
        if isinstance(kit_input, KitPointer):
            if kit_input.phase in (PointerPhase.UP, PointerPhase.CANCEL):
                self._pointer_down = False
                self._gesture_cuddled_ids.clear()
            elif kit_input.phase is PointerPhase.MOVE and self._pointer_down:
                self._drag_cuddle(*kit_input.position)
        result = self._surfaces.dispatch(kit_input)
        if (
            result is UiEventResult.IGNORED
            and isinstance(kit_input, KitPointer)
            and kit_input.phase is PointerPhase.DOWN
        ):
            point = kit_input.position
            if self._controls.blocks_play(point):
                return
            # Pointer use hides the keyboard/controller cursor ring.
            self._controls.layer.focus_visible = False
            self._pointer_down = True
            self.keyboard_cursor = self._clamp_cursor(point)
            self.handle_pointer_down(*point)

    def _route_bay_navigation(self, event: SemanticInputEvent) -> bool:
        """Arrow/D-pad/stick steer the water cursor while the bay has focus."""

        if event.edge is not InputEdge.PRESSED:
            return False
        direction = _DIRECTIONS.get(event.action)
        layer = self._controls.layer
        if direction is None or layer.focused_id != BAY_ID:
            return False
        if not layer.focus_visible:
            layer.focus(BAY_ID, visible=True)
            return True
        dx, dy = direction
        x, y = self.keyboard_cursor
        max_x, max_y = self._cursor_max()
        if (dy > 0 and y >= max_y) or (dy < 0 and y <= CURSOR_MIN[1]):
            # Leave the water towards the toolbar / food tray / banner.
            layer.navigate(event.action)
            return True
        self.keyboard_cursor = self._clamp_cursor((x + dx * CURSOR_STEP, y + dy * CURSOR_STEP))
        layer.invalidation.invalidate()
        return True

    def _cursor_max(self) -> tuple[int, int]:
        return (REFERENCE_WIDTH - 60, self._controls.toolbar_top - 30)

    def _clamp_cursor(self, point: tuple[int, int]) -> tuple[int, int]:
        max_x, max_y = self._cursor_max()
        return (
            max(CURSOR_MIN[0], min(max_x, int(point[0]))),
            max(CURSOR_MIN[1], min(max_y, int(point[1]))),
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def advance(self, dt: float) -> None:
        """Simulate one frame: held-stick repeat, the pod, invitations, Tito, autosave."""

        repeat = self._input.poll()
        if repeat is not None:
            self._route(repeat)
        previously_fed = self.pod.total_fed
        cues = self.pod.update(dt)
        newly_fed = self.pod.total_fed - previously_fed
        if newly_fed > 0:
            self.events.record_feeding(newly_fed)
        for cue in cues:
            if cue in ("splash", "whistle", "clicks", "nibble", "purr", "bubble", "bounce"):
                self.audio.play(cue)
        self._advance_missions(dt)
        if self._controls.keys.update():
            self._keys_changed = True
        self._cast.update(dt)
        self._controls.set_counters(self.pod.total_fed, self.pod.total_cuddled, self.pod.stars)
        now = self._clock()
        if now - self._last_save_time >= AUTOSAVE_INTERVAL_SECONDS:
            self._last_save_time = now
            self._save()

    def draw(self) -> None:
        surface = self.canvas.surface
        t_now = now_seconds()
        renderer = self.renderer
        renderer.draw_background(surface, self.pod.night_mode)
        renderer.draw_toys(surface, self.pod.toys)
        renderer.draw_effects(surface, self.pod.effects, surface_layer=True)
        renderer.draw_orcas(
            surface,
            self.pod,
            t_now,
            show_cravings=self.pod.active_tool == Tool.FEED,
            hint_orca=self.mission_hint_orca,
            wanted=self.mission_wanted,
        )
        if self.pod.active_tool == Tool.SONG:
            renderer.draw_bells(surface, t_now, self._bells_rung)
        renderer.draw_foods(surface, self.pod.foods)
        renderer.draw_effects(surface, self.pod.effects)
        self._cast.draw(surface, CAST_MIDBOTTOM)
        if self.pod.active_fact is not None and self._cast.visible:
            renderer.draw_fact_bubble(
                surface,
                self.pod.active_fact,
                self._cast.head_anchor(CAST_MIDBOTTOM),
                self._controls.toolbar_top - 10,
            )
        else:
            renderer.draw_fact_bubble(surface, None, (0, 0), 0)
        if self._surfaces.overlays:
            self._surfaces.draw(surface)
        else:
            self._hud.draw(
                surface,
                self._controls.keys_look,
                self._draw_hud,
                stale=self._controls.layer.invalidation.should_draw,
            )
        self.canvas.present()

    def _draw_hud(self, surface: pygame.Surface) -> None:
        """Everything the cached HUD overlay holds: the keyboard hint, then the kit layer."""

        self._controls.keys.draw(surface)
        self._surfaces.draw(surface)

    def _save(self) -> None:
        try:
            self.progress.save_progress(self.pod.export_progress())
        except Exception:
            # Storage may refuse writes (e.g. low disk); play must go on.
            pass

    def run(self) -> int:
        """Main activity execution loop."""

        # The bay simulates at a fixed 30 Hz step; the swimming pod is
        # ambient, so it is presented at a reduced rate once the child idles.
        frames = FrameGovernor(redraw_on_input=True)
        while self._running and not activity_stop_requested():
            for event in frames.events():
                self.handle_event(event)
                if not self._running:
                    break
            if not self._running:
                break
            self.advance(0.033)
            if self._keys_changed:
                frames.invalidate()  # a lit key went out or the hint hid
                self._keys_changed = False
            deadline = self._controls.keys.deadline()
            if deadline is not None:
                frames.wake_at(deadline)
            frame = frames.frame(ambient=True)
            if frame is FrameKind.FULL:
                self.draw()
                pygame.display.flip()
                if not self._ready_published:
                    mark_activity_ready()
                    self._ready_published = True
            elif frame is FrameKind.POINTER:
                self.canvas.present_pointer()
            frames.wait(polling=True)  # keep the fixed simulation cadence
        self.audio.stop_voice()
        self._save()
        return 0


__all__ = ["OrcaBayActivity"]
