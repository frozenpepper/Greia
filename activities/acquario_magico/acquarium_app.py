"""Acquario Magico — Activity lifecycle and event loop.

The :class:`AquariumApp` owns:

- a Pygame screen / canvas pair
- the rendered tool layout (shared with input hit-testing)
- a session (model), an audio owner, a renderer, an asset cache
- the persistent counters / chest state (via the session)
- the platform-authority event loop

The class is intentionally the only place that touches
Pygame events, the platform APIs, the asset cache and the
renderer in one place. The session, renderer and audio are
all injected so the lifecycle can be unit-tested in
isolation once the platform inputs are faked.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import pygame

from greia_platform.activity_api import (
    activity_stop_requested,
    emit_activity_event,
    get_storage,
    mark_activity_ready,
)
from greia_platform.activity_ui import ChildUiMetrics
from greia_platform.localization import LocalizedResources
from greia_platform.pygame_canvas import PygameReferenceCanvas, activity_viewport_for_surface

if __package__:
    from .acquarium_assets import AquariumAssetCache
    from .acquarium_audio import AquariumAudio
    from .acquarium_content import (
        AUTOSAVE_INTERVAL_SECONDS,
    MAX_PERSISTED_CREATURES,
    REFERENCE_HEIGHT,
    REFERENCE_WIDTH,
    STORAGE_KEY,
        ToolIndex,
    )
    from .acquarium_model import AquariumSession
    from .acquarium_renderer import AquariumRenderer, now_seconds
else:
    from acquarium_assets import AquariumAssetCache
    from acquarium_audio import AquariumAudio
    from acquarium_content import (
        AUTOSAVE_INTERVAL_SECONDS,
        MAX_PERSISTED_CREATURES,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        STORAGE_KEY,
        ToolIndex,
    )
    from acquarium_model import AquariumSession
    from acquarium_renderer import AquariumRenderer, now_seconds


# Treasure chest is a static layout element; expose as a constant
# so both the input dispatch and the renderer read the same rect.
CHEST_RECT = pygame.Rect(460, REFERENCE_HEIGHT - 165, 112, 88)


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
    runtime context and enters the loop.
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
    _running: bool = True
    _renderer: Optional[AquariumRenderer] = None

    def __post_init__(self) -> None:
        self._renderer = AquariumRenderer(
            assets=self.assets,
            typography=self.typography,
            label_text={
                "add_fish": self.resources.text("tool.add_fish"),
                "feed": self.resources.text("tool.feed"),
                "bubbles": self.resources.text("tool.bubbles"),
                "day": self.resources.text("tool.day"),
                "night": self.resources.text("tool.night"),
            },
        )
        self._restore_saved_state()
        if not self.session.creatures:
            self.session.seed_default_population()

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
        self.session.total_fed = int(saved.get("total_fed", 0))
        self.session.total_popped = int(saved.get("total_popped", 0))
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
        if event.type == pygame.KEYDOWN:
            self._handle_keydown(event.key)
            return
        if event.type == pygame.VIDEORESIZE:
            self._handle_resize()
            return
        if event.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
            self._handle_pointer(event)

    def _handle_keydown(self, key: int) -> None:
        if key == pygame.K_ESCAPE:
            self._running = False
        elif key == pygame.K_SPACE:
            self._toggle_glow_mode()
        elif key == pygame.K_1:
            self.session.active_tool = ToolIndex.SPAWN
            self.audio.play("bubble")
        elif key == pygame.K_2:
            self.session.active_tool = ToolIndex.FEED
            self.audio.play("bubble")
        elif key == pygame.K_3:
            self.session.active_tool = ToolIndex.BUBBLES
            self.audio.play("bubble")

    def _handle_resize(self) -> None:
        new_screen = pygame.display.get_surface()
        if new_screen is None:
            return
        self.screen = new_screen
        self.metrics = ChildUiMetrics.for_size(*new_screen.get_size())
        self.canvas = PygameReferenceCanvas(new_screen)
        # Drop the cached pre-baked background so the next frame
        # re-bakes it at the new resolution. Asset cache keys on
        # the size for backgrounds, so the change is automatic
        # if the size really changed; the explicit clear is a
        # safety net for reparenting on a same-size surface.
        self.assets.invalidate_background()

    def _handle_pointer(self, event: pygame.event.Event) -> None:
        position = getattr(event, "pos", None)
        if position is None and hasattr(event, "x") and hasattr(event, "y"):
            width, height = self.screen.get_size()
            position = (int(event.x * width), int(event.y * height))
        if position is None:
            return

        if not _is_safe_point(self.screen, position):
            return
        pointer = self.canvas.pointer(position)
        if pointer is None:
            return
        mx, my = int(pointer[0]), int(pointer[1])
        assert self._renderer is not None

        if self._handle_toolbar_click(mx, my):
            return
        if CHEST_RECT.collidepoint(mx, my):
            self._open_chest()
            return
        if self._handle_creature_touch(mx, my):
            return
        if my < self._renderer.tool_layout.tool_y:
            self._handle_water_canvas_click(mx, my)

    def _handle_toolbar_click(self, mx: int, my: int) -> bool:
        assert self._renderer is not None
        for rect, tool_index, _ in self._renderer.tool_layout.rects:
            if rect.collidepoint(mx, my):
                self._activate_tool(tool_index, rect)
                return True
        return False

    def _activate_tool(self, tool_index: int, button_rect: pygame.Rect) -> None:
        if tool_index == ToolIndex.DAY_NIGHT:
            self._toggle_glow_mode()
        elif tool_index == ToolIndex.FEED:
            self._scatter_food(6)
            self.audio.play("nibble")
            self.session.emit_sparkles(
                8, float(button_rect.centerx), float(button_rect.top - 10), (253, 224, 71)
            )
        elif tool_index == ToolIndex.SPAWN:
            self.session.spawn_creature(
                random.uniform(200, REFERENCE_WIDTH - 200),
                random.uniform(150, self._renderer.tool_layout.tool_y - 120),
                self.session.spawn_selector_idx,
                1 if random.random() < 0.5 else -1,
            )
            self.session.spawn_selector_idx = (self.session.spawn_selector_idx + 1) % 8
            self.audio.play("splash")
        elif tool_index == ToolIndex.BUBBLES:
            self.session.emit_bubble_storm(
                16,
                100,
                REFERENCE_WIDTH - 100,
                self._renderer.tool_layout.tool_y - 50,
                self._renderer.tool_layout.tool_y + 10,
            )
            self.audio.play("bubble")
        self.session.active_tool = tool_index

    def _toggle_glow_mode(self) -> None:
        self.session.glow_mode = not self.session.glow_mode
        self.audio.play("glow")
        emit_activity_event(
            "aquarium.glow_mode_toggled",
            {"glow_mode": self.session.glow_mode},
        )

    def _scatter_food(self, count: int) -> None:
        for _ in range(count):
            self.session.food_pellets.append(
                {
                    "x": float(random.uniform(160, REFERENCE_WIDTH - 160)),
                    "y": float(random.uniform(60, 130)),
                    "vx": random.uniform(-0.4, 0.4),
                    "vy": random.uniform(0.9, 1.5),
                    "size": random.uniform(5.5, 8.0),
                    "color": (245, 158, 11),
                }
            )

    def _open_chest(self) -> None:
        self.session.chest_open_timer = 2.5
        self.audio.play("chest")
        self.session.emit_bubble_storm(
            12,
            CHEST_RECT.centerx - 25,
            CHEST_RECT.centerx + 25,
            CHEST_RECT.top - 10,
            CHEST_RECT.top - 10,
        )
        for _ in range(10):
            color = random.choice([(250, 204, 21), (253, 224, 71), (56, 189, 248)])
            self.session.particles.append(
                {
                    "x": float(CHEST_RECT.centerx + random.uniform(-20, 20)),
                    "y": float(CHEST_RECT.top - 15),
                    "vx": random.uniform(-2.5, 2.5),
                    "vy": random.uniform(-2.5, -5.0),
                    "color": color,
                    "size": random.uniform(5, 9),
                    "life": 1.0,
                    "decay": 0.03,
                }
            )

    def _handle_creature_touch(self, mx: int, my: int) -> bool:
        for creature in reversed(self.session.creatures):
            species = creature["spec"]
            cw = species.get("w", 72)
            ch = species.get("h", 54)
            creature_rect = pygame.Rect(
                int(creature["x"] - cw / 2), int(creature["y"] - ch / 2), cw, ch
            )
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
                        "vx": random.uniform(-2, 2),
                        "vy": random.uniform(-2, 2),
                        "color": (88, 28, 135) if self.session.glow_mode else (30, 41, 59),
                        "size": random.uniform(6, 12),
                        "life": 1.0,
                        "decay": 0.04,
                    }
                )
        elif species_id == "dolphin":
            creature["spin_t"] = 1.5
            creature["vx"] *= 1.8
        else:
            creature["happy_t"] = 1.5
            creature["vy"] = -2.0
        self.session.emit_sparkles(6, float(mx), float(my), (253, 224, 71))

    def _handle_water_canvas_click(self, mx: int, my: int) -> None:
        tool = self.session.active_tool
        if tool == ToolIndex.SPAWN:
            self.session.spawn_creature(
                mx, my, self.session.spawn_selector_idx, 1 if mx < REFERENCE_WIDTH / 2 else -1
            )
            self.session.spawn_selector_idx = (self.session.spawn_selector_idx + 1) % 8
            self.audio.play("splash")
            self.session.emit_sparkles(10, float(mx), float(my), (56, 189, 248))
        elif tool == ToolIndex.FEED:
            self.session.drop_food_at(mx, my)
            self.audio.play("nibble")
        elif tool == ToolIndex.BUBBLES:
            self.session.emit_bubble_storm(8, mx - 25, mx + 25, my - 15, my + 15)
            self.audio.play("bubble")

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
        previously_fed = self.session.total_fed
        self.session.update(dt)
        newly_fed = self.session.total_fed - previously_fed
        if newly_fed > 0:
            emit_activity_event(
                "aquarium.fish_fed",
                {"count": newly_fed, "total_fed": self.session.total_fed},
            )
        if (
            self.storage is not None
            and time.monotonic() - self.last_save_time > AUTOSAVE_INTERVAL_SECONDS
        ):
            self.last_save_time = time.monotonic()
            self._autosave()
        self._draw()
        if not self.ready_published:
            mark_activity_ready()
            self.ready_published = True
        self.clock.tick(30)

    def _draw(self) -> None:
        assert self._renderer is not None
        surf = self.canvas.surface
        t_now = now_seconds()
        self._renderer.draw_background(surf, self.session.glow_mode, t_now)
        self._renderer.draw_chest(surf, CHEST_RECT, self.session.chest_open_timer)
        self._renderer.draw_food(surf, self.session.food_pellets)
        self._renderer.draw_creatures(surf, self.session.creatures)
        self._renderer.draw_bubbles(surf, self.session.bubbles)
        self._renderer.draw_particles(surf, self.session.particles)
        self._renderer.draw_hud(surf, len(self.session.creatures))
        self._renderer.draw_toolbar(
            surf,
            self.session.active_tool,
            self.session.glow_mode,
            self.session.spawn_selector_idx,
        )
        self.canvas.present()
        pygame.display.flip()


def build_app(
    screen: pygame.Surface,
    resources: LocalizedResources,
    *,
    storage: Any = None,
) -> AquariumApp:
    """Composition helper used by the thin main entry point.

    Builds the renderer and audio owner with a fresh asset cache
    so each Activity instance has its own bounded cache. Storage
    is injected from the platform; pass ``None`` to disable
    persistence (used by the headless harness).
    """

    metrics = ChildUiMetrics.for_size(*screen.get_size())
    canvas = PygameReferenceCanvas(screen)
    from greia_platform.typography import GreiaTypography

    return AquariumApp(
        screen=screen,
        canvas=canvas,
        metrics=metrics,
        typography=GreiaTypography(),
        resources=resources,
        audio=AquariumAudio(),
        storage=storage,
    )


__all__ = [
    "AquariumApp",
    "CHEST_RECT",
    "build_app",
]
