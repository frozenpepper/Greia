"""Acquario Magico — Activity lifecycle and event loop.

The :class:`AquariumApp` owns:

- a Pygame screen / canvas pair
- the shared control kit (tools, day/night, mission banner, focus) and its
  input translator (pointer, touch, keyboard and controller alike)
- a session (model), an optional mission director, Tito, an audio owner,
  a renderer and an asset cache
- persistence of the child's tank (creatures, counters, stars)
- the platform-authority event loop

The aquarium is a free toy: every tool works at any time and the optional
missions never interrupt play. Collaborators are injected or built here so
the lifecycle can be unit-tested headlessly.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Any, Optional

import pygame

from greia_platform.activity_api import (
    activity_stop_requested,
    emit_activity_event,
    mark_activity_ready,
)
from greia_platform.activity_controls import (
    BodyShape,
    ControlKit,
    ControlLayout,
    ControlTheme,
    KitPointer,
    PointerPhase,
    PygameControlInput,
)
from greia_platform.activity_ui import ChildUiMetrics
from greia_platform.input_core import InputEdge, SemanticAction, SemanticInputEvent
from greia_platform.localization import LocalizationError, LocalizedResources
from greia_platform.pygame_canvas import PygameReferenceCanvas, activity_viewport_for_surface
from greia_platform.ui_core import SurfaceNavigator, UiEventResult

if __package__:
    from .acquarium_assets import AquariumAssetCache
    from .acquarium_audio import AquariumAudio
    from .acquarium_cast import AquariumCast
    from .acquarium_content import (
        AUTOSAVE_INTERVAL_SECONDS,
        CONTROL_ACCENT,
        MAX_PERSISTED_CREATURES,
        MAX_SAVED_STARS,
        NAME_TAG_SECONDS,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        SPECIES,
        STORAGE_KEY,
        ToolIndex,
    )
    from .acquarium_controls import CAST_HEIGHT, CAST_MIDBOTTOM, TANK_ID, AquariumControls
    from .acquarium_missions import MissionDirector, MissionKind, MissionOutcome
    from .acquarium_model import AquariumSession
    from .acquarium_renderer import AquariumRenderer, now_seconds
else:
    from acquarium_assets import AquariumAssetCache
    from acquarium_audio import AquariumAudio
    from acquarium_cast import AquariumCast
    from acquarium_content import (
        AUTOSAVE_INTERVAL_SECONDS,
        CONTROL_ACCENT,
        MAX_PERSISTED_CREATURES,
        MAX_SAVED_STARS,
        NAME_TAG_SECONDS,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        SPECIES,
        STORAGE_KEY,
        ToolIndex,
    )
    from acquarium_controls import CAST_HEIGHT, CAST_MIDBOTTOM, TANK_ID, AquariumControls
    from acquarium_missions import MissionDirector, MissionKind, MissionOutcome
    from acquarium_model import AquariumSession
    from acquarium_renderer import AquariumRenderer, now_seconds


# Treasure chest is a static layout element; expose as a constant
# so both the input dispatch and the renderer read the same rect.
CHEST_RECT = pygame.Rect(456, 402, 112, 88)

# Keyboard/controller cursor bounds inside the water (logical px).
CURSOR_MIN = (70, 85)
CURSOR_MAX = (REFERENCE_WIDTH - 70, REFERENCE_HEIGHT - 110)
CURSOR_STEP = 48

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

# Direct shortcuts kept for keyboards (Space/Enter/arrows belong to the kit).
_TOOL_KEYS = {pygame.K_1: ToolIndex.SPAWN, pygame.K_2: ToolIndex.FEED, pygame.K_3: ToolIndex.BUBBLES}
_DAY_NIGHT_KEYS = (pygame.K_4, pygame.K_n)


def _safe_saved_counter(value: Any, limit: int = 1_000_000_000) -> int:
    """Corrupt persisted counters must not crash first frame or grow unbounded."""
    try:
        parsed = int(value)
    except (TypeError, ValueError, OverflowError):
        return 0
    return max(0, min(parsed, limit))


def _is_safe_point(surface: pygame.Surface, position: tuple[int, int]) -> bool:
    """Reject coordinates outside the Activity or inside trusted Home/Back."""

    viewport = activity_viewport_for_surface(surface)
    x, y = position
    if not (0 <= x < viewport.surface.width and 0 <= y < viewport.surface.height):
        return False
    return not any(
        region.x <= x < region.right and region.y <= y < region.bottom
        for region in viewport.protected_regions
    )


@dataclass
class AquariumApp:
    """Lifecycle owner for acquario_magico.

    The class holds every collaborator it needs and exposes a
    single ``run`` entry point. All platform-side effects are
    called here, so the surrounding ``main.py`` only wires
    runtime context and enters the loop. Optional collaborators
    default to ``None`` and are skipped when absent.
    """

    screen: pygame.Surface
    canvas: PygameReferenceCanvas
    metrics: ChildUiMetrics
    typography: Any
    resources: LocalizedResources
    audio: AquariumAudio
    assets: AquariumAssetCache = field(default_factory=AquariumAssetCache)
    session: AquariumSession = field(default_factory=AquariumSession)
    storage: Any = None
    clock: pygame.time.Clock = field(default_factory=pygame.time.Clock)
    ready_published: bool = False
    last_save_time: float = field(default_factory=time.monotonic)
    missions_enabled: bool = True
    rng: random.Random = field(default_factory=random.Random)
    _running: bool = True
    _renderer: Optional[AquariumRenderer] = None
    _kit: Optional[ControlKit] = None
    _controls: Optional[AquariumControls] = None
    _surfaces: Optional[SurfaceNavigator] = None
    _input: Optional[PygameControlInput] = None
    _missions: Optional[MissionDirector] = None
    _cast: Optional[AquariumCast] = None
    _hinted_uid: Optional[int] = None
    keyboard_cursor: tuple[int, int] = (REFERENCE_WIDTH // 2, REFERENCE_HEIGHT // 2)

    def __post_init__(self) -> None:
        self._kit = ControlKit(self.typography, ControlTheme.for_accent(CONTROL_ACCENT))
        self._renderer = AquariumRenderer(
            assets=self.assets,
            name_tag=self._build_name_tag,
            hint_ring=lambda size: self._kit.painter.focus_ring(size, size[0] // 2),
        )
        self._controls = AquariumControls(
            self._kit,
            self.resources,
            ControlLayout.for_canvas(self.canvas, self.screen.get_size()),
            self.assets,
            cursor=lambda: self.keyboard_cursor,
            on_tool=self._activate_tool,
            on_day_night=self._toggle_glow_mode,
            on_tank=self._act_at_cursor,
            on_hint=self._request_hint,
        )
        self._surfaces = SurfaceNavigator(self._controls.layer)
        self._input = PygameControlInput(
            to_logical=self.canvas.pointer,
            is_safe=lambda position: _is_safe_point(self.screen, position),
        )
        self._missions = MissionDirector(rng=self.rng, enabled=self.missions_enabled)
        self._cast = AquariumCast(self._kit.art, height=CAST_HEIGHT)
        self._restore_saved_state()
        if not self.session.creatures:
            self.session.seed_default_population()
        self._sync_controls()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _restore_saved_state(self) -> None:
        if self.storage is None:
            return
        try:
            saved = self.storage.kv_get(STORAGE_KEY)
        except Exception:
            saved = None
        if not isinstance(saved, dict):
            return
        self.session.glow_mode = bool(saved.get("glow_mode", False))
        self.session.total_fed = _safe_saved_counter(saved.get("total_fed", 0))
        self.session.total_popped = _safe_saved_counter(saved.get("total_popped", 0))
        self.session.stars = _safe_saved_counter(saved.get("stars", 0), MAX_SAVED_STARS)
        saved_creatures = saved.get("creatures")
        if isinstance(saved_creatures, list) and saved_creatures:
            self.session.restore_saved_population(saved_creatures)

    def _serialize_creatures(self) -> list[dict[str, Any]]:
        return [
            {
                "id": c["spec"]["id"],
                "x": round(c["x"], 1),
                "y": round(c["y"], 1),
                "facing": c["facing"],
            }
            for c in self.session.creatures[:MAX_PERSISTED_CREATURES]
        ]

    def _autosave(self) -> None:
        if self.storage is None:
            return
        try:
            self.storage.kv_set(
                STORAGE_KEY,
                {
                    "glow_mode": self.session.glow_mode,
                    "total_fed": self.session.total_fed,
                    "total_popped": self.session.total_popped,
                    "stars": self.session.stars,
                    "creatures": self._serialize_creatures(),
                },
            )
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Input dispatch
    # ------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self._running = False
            return
        if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION) and getattr(event, "touch", False):
            # SDL synthesizes a mouse event for the same physical finger;
            # the FINGER* event is the one we act on.
            return
        if event.type == pygame.KEYDOWN:
            self._handle_keydown(event.key)
            return
        if event.type == pygame.VIDEORESIZE:
            self._handle_resize()
            return
        if event.type in (pygame.FINGERDOWN, pygame.FINGERUP):
            position = self._finger_position(event)
            phase = PointerPhase.DOWN if event.type == pygame.FINGERDOWN else PointerPhase.UP
            self._handle_pointer_phase(phase, position)
            return
        if self._input is None:
            return
        translated = self._input.translate(event)
        if translated is not None:
            self._route(translated)

    def _finger_position(self, event: pygame.event.Event) -> tuple[int, int]:
        width, height = self.screen.get_size()
        return (int(event.x * width), int(event.y * height))

    def _handle_keydown(self, key: int) -> None:
        if key == pygame.K_ESCAPE:
            self._running = False
            return
        if key in _TOOL_KEYS:
            self._select_tool(_TOOL_KEYS[key])
            return
        if key in _DAY_NIGHT_KEYS:
            self._toggle_glow_mode()
            return
        if key == pygame.K_c:
            self._open_chest()
            return
        if self._input is None:
            return
        translated = self._input.translate(pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode=""))
        if translated is not None:
            self._route(translated)

    def _handle_resize(self) -> None:
        new_screen = pygame.display.get_surface()
        if new_screen is None:
            return
        self.screen = new_screen
        self.metrics = ChildUiMetrics.for_size(*new_screen.get_size())
        self.canvas = PygameReferenceCanvas(new_screen)
        if self._input is not None:
            self._input = PygameControlInput(
                to_logical=self.canvas.pointer,
                is_safe=lambda position: _is_safe_point(self.screen, position),
            )
        if self._controls is not None:
            self._controls.relayout(ControlLayout.for_canvas(self.canvas, new_screen.get_size()))
        # Drop the cached pre-baked background so the next frame
        # re-bakes it; a safety net for reparenting on a same-size surface.
        self.assets.invalidate_background()

    def _handle_pointer(self, position: tuple[int, int]) -> None:
        """Deliver one complete tap at a physical position (touch, tools, tests)."""

        self._handle_pointer_phase(PointerPhase.DOWN, position)
        self._handle_pointer_phase(PointerPhase.UP, position)

    def _handle_pointer_phase(self, phase: PointerPhase, position: tuple[int, int]) -> None:
        if not _is_safe_point(self.screen, position):
            if phase is PointerPhase.UP:
                self._route(KitPointer(PointerPhase.CANCEL, (-1, -1)))
            return
        logical = self.canvas.pointer(position)
        if logical is None:
            return
        self._route(KitPointer(phase, (int(logical[0]), int(logical[1]))))

    def _route(self, kit_input: Any) -> None:
        """Send one kit input to the controls; unconsumed taps are gameplay."""

        if isinstance(kit_input, SemanticInputEvent) and self._route_tank_navigation(kit_input):
            return
        result = self._surfaces.dispatch(kit_input) if self._surfaces is not None else UiEventResult.IGNORED
        if (
            result is UiEventResult.IGNORED
            and isinstance(kit_input, KitPointer)
            and kit_input.phase is PointerPhase.DOWN
        ):
            point = kit_input.position
            if self._controls is not None:
                if self._controls.blocks_play(point):
                    return
                # Pointer use hides the keyboard/controller cursor ring.
                self._controls.layer.focus_visible = False
            self.keyboard_cursor = self._clamp_cursor(point)
            self._handle_action_at(*point)

    def _route_tank_navigation(self, event: SemanticInputEvent) -> bool:
        """Arrow/D-pad/stick steer the water cursor while the tank has focus."""

        if self._controls is None or event.edge is not InputEdge.PRESSED:
            return False
        direction = _DIRECTIONS.get(event.action)
        layer = self._controls.layer
        if direction is None or layer.focused_id != TANK_ID:
            return False
        if not layer.focus_visible:
            layer.focus(TANK_ID, visible=True)
            return True
        dx, dy = direction
        x, y = self.keyboard_cursor
        if (dy > 0 and y >= CURSOR_MAX[1]) or (dy < 0 and y <= CURSOR_MIN[1]):
            # Leave the water towards the toolbar / top bar.
            layer.navigate(event.action)
            return True
        self._move_cursor(dx, dy)
        return True

    def _move_cursor(self, dx: int, dy: int) -> None:
        x, y = self.keyboard_cursor
        self.keyboard_cursor = self._clamp_cursor((x + dx * CURSOR_STEP, y + dy * CURSOR_STEP))
        if self._controls is not None:
            self._controls.layer.invalidation.invalidate()

    @staticmethod
    def _clamp_cursor(point: tuple[int, int]) -> tuple[int, int]:
        return (
            max(CURSOR_MIN[0], min(CURSOR_MAX[0], int(point[0]))),
            max(CURSOR_MIN[1], min(CURSOR_MAX[1], int(point[1]))),
        )

    def _act_at_cursor(self) -> None:
        self._handle_action_at(*self.keyboard_cursor)

    def _handle_action_at(self, mx: int, my: int) -> None:
        """Activate one logical location in the tank, independent of input device."""

        if CHEST_RECT.collidepoint(mx, my):
            self._open_chest()
            return
        if self._handle_creature_touch(mx, my):
            return
        if self._controls is None or self._controls.tank_bounds.collidepoint(mx, my):
            self._handle_water_canvas_click(mx, my)

    # ------------------------------------------------------------------
    # Tools
    # ------------------------------------------------------------------

    def _select_tool(self, tool_index: int) -> None:
        """Keyboard shortcut (1/2/3): choose what a tap in the water does."""

        self.session.active_tool = tool_index
        self.audio.play("bubble")
        self._sync_controls()

    def _activate_tool(self, tool_index: int) -> None:
        bar_y = REFERENCE_HEIGHT - 100
        if tool_index == ToolIndex.DAY_NIGHT:
            self._toggle_glow_mode()
            return
        if tool_index == ToolIndex.FEED:
            self._scatter_food(6)
            self.audio.play("nibble")
        elif tool_index == ToolIndex.SPAWN:
            creature = self.session.spawn_creature(
                self.rng.uniform(200, REFERENCE_WIDTH - 200),
                self.rng.uniform(150, bar_y - 120),
                self.session.spawn_selector_idx,
                1 if self.rng.random() < 0.5 else -1,
            )
            self.session.spawn_selector_idx = (self.session.spawn_selector_idx + 1) % len(SPECIES)
            self.audio.play("splash")
            if creature is not None:
                self.session.emit_effect("splash", creature["x"], creature["y"])
                self.session.show_name(creature, NAME_TAG_SECONDS)
        elif tool_index == ToolIndex.BUBBLES:
            self.session.emit_bubble_storm(16, 100, REFERENCE_WIDTH - 100, bar_y - 50, bar_y + 10)
            self.audio.play("bubble")
        self.session.active_tool = tool_index
        self._sync_controls()

    def _toggle_glow_mode(self) -> None:
        self.session.glow_mode = not self.session.glow_mode
        self.audio.play("glow")
        emit_activity_event(
            "aquarium.glow_mode_toggled",
            {"glow_mode": self.session.glow_mode},
        )
        self._sync_controls()

    def _scatter_food(self, count: int) -> None:
        for _ in range(count):
            self.session.food_pellets.append(
                {
                    "x": float(self.rng.uniform(160, REFERENCE_WIDTH - 160)),
                    "y": float(self.rng.uniform(90, 140)),
                    "vx": self.rng.uniform(-0.4, 0.4),
                    "vy": self.rng.uniform(0.9, 1.5),
                    "size": self.rng.uniform(5.5, 8.0),
                    "color": (245, 158, 11),
                }
            )

    def _open_chest(self, *, pearl: bool = False) -> None:
        self.session.chest_open_timer = 2.5
        self.audio.play("chest")
        self.session.emit_bubble_storm(
            12,
            CHEST_RECT.centerx - 25,
            CHEST_RECT.centerx + 25,
            CHEST_RECT.top - 10,
            CHEST_RECT.top - 10,
        )
        self.session.emit_effect("sparkle", CHEST_RECT.centerx, CHEST_RECT.top - 4)
        if pearl:
            self.session.emit_effect("confetti", CHEST_RECT.centerx, CHEST_RECT.top - 40)
            self.session.emit_effect("star_burst", CHEST_RECT.centerx, CHEST_RECT.top + 10)

    def _handle_creature_touch(self, mx: int, my: int) -> bool:
        for creature in reversed(self.session.creatures):
            species = creature["spec"]
            cw = species.get("w", 72)
            ch = species.get("h", 54)
            creature_rect = pygame.Rect(
                int(creature["x"] - cw / 2), int(creature["y"] - ch / 2), cw, ch
            ).inflate(12, 12)
            if not creature_rect.collidepoint(mx, my):
                continue
            self._touch_creature(creature, mx, my)
            return True
        return False

    def _touch_creature(self, creature: dict[str, Any], mx: int, my: int) -> None:
        self.audio.play("bubble")
        species_id = creature["spec"]["id"]
        if species_id == "puffer":
            creature["puffed_t"] = 2.5
        elif species_id == "octopus":
            for _ in range(8):
                self.session.particles.append(
                    {
                        "x": creature["x"],
                        "y": creature["y"],
                        "vx": self.rng.uniform(-2, 2),
                        "vy": self.rng.uniform(-2, 2),
                        "color": (88, 28, 135) if self.session.glow_mode else (61, 52, 70),
                        "size": self.rng.uniform(6, 12),
                        "life": 1.0,
                        "decay": 0.04,
                    }
                )
            creature["happy_t"] = 1.0
        elif species_id == "dolphin":
            creature["spin_t"] = 1.5
            creature["vx"] *= 1.8
            creature["happy_t"] = 1.5
        else:
            creature["happy_t"] = 1.5
            if creature["spec"]["behavior"] != "floor":
                creature["vy"] = -2.0
        self.session.emit_effect("heart_pop", mx, my - 10, 0.8)
        self.session.show_name(creature, NAME_TAG_SECONDS)
        if self._missions is not None:
            self._on_mission_outcome(self._missions.creature_touched(creature), creature)

    def _handle_water_canvas_click(self, mx: int, my: int) -> None:
        tool = self.session.active_tool
        if tool == ToolIndex.SPAWN:
            creature = self.session.spawn_creature(
                mx, my, self.session.spawn_selector_idx, 1 if mx < REFERENCE_WIDTH / 2 else -1
            )
            self.session.spawn_selector_idx = (self.session.spawn_selector_idx + 1) % len(SPECIES)
            self.audio.play("splash")
            self.session.emit_effect("splash", mx, my)
            if creature is not None:
                self.session.show_name(creature, NAME_TAG_SECONDS)
            self._sync_controls()
        elif tool == ToolIndex.FEED:
            self.session.drop_food_at(mx, my)
            self.audio.play("nibble")
        elif tool == ToolIndex.BUBBLES:
            self.session.emit_bubble_storm(8, mx - 25, mx + 25, my - 15, my + 15)
            self.audio.play("bubble")

    # ------------------------------------------------------------------
    # Missions
    # ------------------------------------------------------------------

    def _request_hint(self) -> None:
        if self._missions is not None and self._missions.request_hint():
            self._show_hint()

    def _show_hint(self) -> None:
        """Graduated help: Tito points and the target creature gets a ripple."""

        mission = self._missions.current if self._missions is not None else None
        if mission is not None:
            self._hinted_uid = mission.target_uid
        if self._cast is not None:
            self._cast.point()

    def _advance_missions(self, dt: float) -> None:
        if self._missions is None:
            return
        for uid in self.session.meals:
            self._on_mission_outcome(self._missions.creature_ate(uid), self.session.creature_by_uid(uid))
        self.session.meals.clear()
        self._on_mission_outcome(self._missions.update(dt, self.session.creatures), None)

    def _on_mission_outcome(self, outcome: MissionOutcome, creature: dict[str, Any] | None) -> None:
        if outcome is MissionOutcome.NONE:
            return
        if outcome is MissionOutcome.HINT:
            self._show_hint()
        elif outcome in (MissionOutcome.STARTED, MissionOutcome.RETIRED):
            self._hinted_uid = None
            if outcome is MissionOutcome.STARTED:
                self.audio.play("bubble")
        elif outcome in (MissionOutcome.COMPLETED, MissionOutcome.PEARL):
            self._hinted_uid = None
            if creature is not None:
                creature["happy_t"] = max(creature["happy_t"], 1.6)
                self.session.emit_effect("star_burst", creature["x"], creature["y"])
            if self._cast is not None:
                self._cast.cheer()
            emit_activity_event("aquarium.mission_completed", {"pearl": outcome is MissionOutcome.PEARL})
            if outcome is MissionOutcome.PEARL:
                self.session.stars = min(MAX_SAVED_STARS, self.session.stars + 1)
                self._open_chest(pearl=True)
                self.audio.say("praise.general")
            else:
                self.audio.say("celebrate.success")
        self._sync_controls()

    @property
    def mission_hint_uid(self) -> int | None:
        """Target creature to ripple once a hint was given for this mission."""

        mission = self._missions.current if self._missions is not None else None
        if mission is None or self._hinted_uid is None:
            return None
        if self._hinted_uid != mission.target_uid:
            # The target was replaced (evicted creature): keep helping.
            self._hinted_uid = mission.target_uid
        return mission.target_uid

    @property
    def mission_hungry_uid(self) -> int | None:
        mission = self._missions.current if self._missions is not None else None
        if mission is None or mission.kind is not MissionKind.FEED:
            return None
        return mission.target_uid

    def _sync_controls(self) -> None:
        controls = self._controls
        if controls is None:
            return
        controls.sync_tool(self.session.active_tool)
        controls.sync_spawn_species(self.session.spawn_selector_idx)
        controls.sync_day_night(self.session.glow_mode)
        mission = self._missions.current if self._missions is not None else None
        done = self._missions.done_in_set if self._missions is not None else 0
        if mission is None:
            controls.set_mission(None, None, done)
        else:
            controls.set_mission(mission.kind.value, mission.species_id, done)
        controls.set_stars(self.session.stars)
        if self._cast is not None:
            self._cast.present(mission is not None)

    def _build_name_tag(self, species_id: str) -> pygame.Surface | None:
        """Cream pill with the creature's localized name (built once per species)."""

        if self._kit is None:
            return None
        species = next((s for s in SPECIES if s["id"] == species_id), None)
        if species is None:
            return None
        try:
            text = self.resources.text(species["name_key"]).strip()
        except LocalizationError:
            return None
        if not text:
            return None
        painter = self._kit.painter
        label = painter.label(text, 22, painter.theme.text, max_width=260)
        size = (label.get_width() + 32, label.get_height() + 14)
        tag = painter.body(BodyShape.PILL, size, painter.theme.surface, contour_width=2).copy()
        tag.blit(label, label.get_rect(center=(size[0] // 2, size[1] // 2)))
        return tag

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def run(self) -> int:
        while self._running and not activity_stop_requested():
            for event in pygame.event.get():
                self.handle_event(event)
                if not self._running:
                    break
            if not self._running:
                break
            self._step_frame(0.033)
        self._autosave()
        return 0

    def _step_frame(self, dt: float) -> None:
        self.advance(dt)
        self._draw()
        if not self.ready_published:
            mark_activity_ready()
            self.ready_published = True
        self.clock.tick(30)

    def advance(self, dt: float) -> None:
        """Simulate one frame: held-stick repeat, tank, missions, Tito, autosave."""

        if self._input is not None:
            repeat = self._input.poll()
            if repeat is not None:
                self._route(repeat)
        previously_fed = self.session.total_fed
        self.session.update(dt)
        newly_fed = self.session.total_fed - previously_fed
        if newly_fed > 0:
            emit_activity_event(
                "aquarium.fish_fed",
                {"count": newly_fed, "total_fed": self.session.total_fed},
            )
        self._advance_missions(dt)
        if self._cast is not None:
            self._cast.update(dt)
        if (
            self.storage is not None
            and time.monotonic() - self.last_save_time > AUTOSAVE_INTERVAL_SECONDS
        ):
            self.last_save_time = time.monotonic()
            self._autosave()

    def _draw(self) -> None:
        assert self._renderer is not None
        surf = self.canvas.surface
        t_now = now_seconds()
        renderer = self._renderer
        renderer.draw_background(surf, self.session.glow_mode, t_now)
        renderer.draw_chest(surf, CHEST_RECT, self.session.chest_open_timer)
        renderer.draw_food(surf, self.session.food_pellets)
        renderer.draw_creatures(
            surf,
            self.session.creatures,
            glow_mode=self.session.glow_mode,
            t_now=t_now,
            hint_uid=self.mission_hint_uid,
            hungry_uid=self.mission_hungry_uid,
        )
        renderer.draw_bubbles(surf, self.session.bubbles)
        renderer.draw_particles(surf, self.session.particles)
        renderer.draw_effects(surf, self.session.effects)
        if self._cast is not None:
            self._cast.draw(surf, CAST_MIDBOTTOM)
        if self._surfaces is not None:
            self._surfaces.draw(surf)
        self.canvas.present()
        pygame.display.flip()


def build_app(
    screen: pygame.Surface,
    resources: LocalizedResources,
    *,
    storage: Any = None,
    audio: AquariumAudio | None = None,
) -> AquariumApp:
    """Composition helper used by the thin main entry point and tests.

    Builds the renderer, kit and audio owner with a fresh asset cache
    so each Activity instance has its own bounded cache. Storage is
    injected from the platform; pass ``None`` to disable persistence.
    """

    from greia_platform.typography import GreiaTypography

    if audio is None:
        audio = AquariumAudio(locale=resources.context.selected.value)
    return AquariumApp(
        screen=screen,
        canvas=PygameReferenceCanvas(screen),
        metrics=ChildUiMetrics.for_size(*screen.get_size()),
        typography=GreiaTypography(),
        resources=resources,
        audio=audio,
        storage=storage,
    )


__all__ = [
    "AquariumApp",
    "CHEST_RECT",
    "build_app",
]
