"""La Discesa della Biglia — Activity lifecycle and input.

The lifecycle layer is the only place that touches Pygame events,
the platform APIs, the engine, the renderer and the storage in
one place. It is the Activity's "app" class.

The class is intentionally small: one state machine (PALETTE,
DRAGGING, RUNNING, FINISHED) and one event loop. The presentation
sub-layer (renderer) and the semantic sub-layer (engine, services)
are all injected, so the lifecycle can be unit-tested in
isolation once the platform inputs are faked.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Final

import pygame

from greia_platform.activity_api import (
    activity_stop_requested,
    get_theme,
    mark_activity_ready,
)
from greia_platform.activity_ui import ChildUiMetrics
from greia_platform.child_text import display_text
from greia_platform.pygame_canvas import PygameReferenceCanvas, activity_viewport_for_surface
from greia_platform.localization import (
    ActivityLocaleSupport,
    LocalizedResources,
    resolve_activity_locale,
)
from greia_platform.typography import FontRole, GreiaTypography

if __package__:
    from .ramp_audio import RampAudio
    from .ramp_content import (
        LEVELS,
        PLAYFIELD_BOTTOM,
        PLAYFIELD_LEFT,
        PLAYFIELD_RIGHT,
        PLAYFIELD_TOP,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        TOOL_CATALOGUE,
        PlacedTool,
    )
    from .ramp_engine import RampEngine
    from .ramp_renderer import RampRenderer
    from .ramp_services import RampEvents, RampStorage
else:
    from ramp_audio import RampAudio
    from ramp_content import (
        LEVELS,
        PLAYFIELD_BOTTOM,
        PLAYFIELD_LEFT,
        PLAYFIELD_RIGHT,
        PLAYFIELD_TOP,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        TOOL_CATALOGUE,
        PlacedTool,
    )
    from ramp_engine import RampEngine
    from ramp_renderer import RampRenderer
    from ramp_services import RampEvents, RampStorage


PALETTE_TAPBOX_PADDING: Final = 8


class Phase(StrEnum):
    PALETTE = "palette"
    RUNNING = "running"
    FINISHED = "finished"


@dataclass
class RampApp:
    screen: pygame.Surface
    metrics: ChildUiMetrics
    theme: object
    typography: GreiaTypography
    resources: LocalizedResources
    audio: RampAudio
    storage: RampStorage
    events: RampEvents
    level_index: int = 0
    phase: Phase = Phase.PALETTE
    engine: RampEngine = field(init=False)
    renderer: RampRenderer = field(init=False)
    canvas: PygameReferenceCanvas = field(init=False)
    pre_drop_timer: float = 0.0
    ready_published: bool = False
    finished_banner_timer: float = 0.0
    last_outcome: str | None = None
    last_elapsed: float = 0.0
    last_improved: bool = False
    last_published_best: bool = False

    def __post_init__(self) -> None:
        self.engine = RampEngine(level=LEVELS[self.level_index])
        self.canvas = PygameReferenceCanvas(self.screen)
        self.renderer = RampRenderer.build(self.canvas.surface)
        self._refresh_palette()

    def _refresh_palette(self) -> None:
        # Pre-render the tool labels so the renderer doesn't pay for
        # per-frame typography when the palette is shown.
        self.renderer.palette_selected = 0

    def run(self) -> int:
        clock = pygame.time.Clock()
        running = True
        last_frame = time.monotonic()
        while running and not activity_stop_requested():
            now = time.monotonic()
            dt = min(0.05, now - last_frame)
            last_frame = now
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key in (pygame.K_SPACE, pygame.K_RETURN):
                        self._try_drop()
                    elif event.key == pygame.K_c:
                        self._clear_tools()
                elif event.type == pygame.VIDEORESIZE:
                    self.screen = pygame.display.get_surface() or self.screen
                    self.metrics = ChildUiMetrics.for_size(*self.screen.get_size())
                    self.canvas = PygameReferenceCanvas(self.screen)
                    self.renderer.surface = self.canvas.surface
                    self._cancel_drag()
                elif event.type == pygame.WINDOWFOCUSLOST:
                    self._cancel_drag()
                elif event.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
                    if event.type == pygame.FINGERDOWN or event.button == 1:
                        self._handle_click(self._event_position(event))
                elif event.type in (pygame.MOUSEBUTTONUP, pygame.FINGERUP):
                    if event.type == pygame.FINGERUP or event.button == 1:
                        self._handle_release(self._event_position(event))
                elif event.type == pygame.MOUSEMOTION:
                    self._handle_motion(event.pos)
            self._update(dt)
            self._draw()
            self.canvas.present()
            # Present the frame so the first usable frame is on the
            # display BEFORE we tell the Shell the Activity is ready.
            pygame.display.flip()
            if not self.ready_published:
                mark_activity_ready()
                self.ready_published = True
            clock.tick(30)
        self.typography.clear()
        pygame.quit()
        return 0

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------

    def _event_position(self, event: pygame.event.Event) -> tuple[int, int]:
        pos = getattr(event, "pos", None)
        if pos is not None:
            return (int(pos[0]), int(pos[1]))
        width, height = self.screen.get_size()
        return (int(event.x * width), int(event.y * height))

    def _reference_point(self, physical: tuple[int, int]) -> tuple[int, int] | None:
        vp = activity_viewport_for_surface(self.screen)
        px, py = physical
        if not (0 <= px < vp.surface.width and 0 <= py < vp.surface.height):
            return None
        if any(r.x <= px < r.right and r.y <= py < r.bottom for r in vp.protected_regions):
            return None
        logical = self.canvas.pointer(physical)
        if logical is None:
            return None
        return (int(logical[0]), int(logical[1]))

    def _cancel_drag(self) -> None:
        self.renderer.drag_kind = None
        self.renderer.drag_origin = None
        self.renderer.drag_pos = None

    def _handle_click(self, pos: tuple[int, int]) -> None:
        point = self._reference_point(pos)
        if point is None:
            return
        x, y = point
        # Top-bar buttons
        if 80 <= x <= 280 and 84 <= y <= 132:
            self._clear_tools()
            return
        if REFERENCE_WIDTH - 280 <= x <= REFERENCE_WIDTH - 80 and 84 <= y <= 132:
            self._try_drop()
            return
        # Palette selection
        for i, rect in enumerate(self.renderer.palette_buttons):
            expanded = rect.inflate(
                PALETTE_TAPBOX_PADDING * 2, PALETTE_TAPBOX_PADDING * 2
            )
            if expanded.collidepoint(x, y):
                self.renderer.palette_selected = i
                return
        # Drag start
        if self.phase != Phase.RUNNING and self._inside_playfield(x, y):
            spec = TOOL_CATALOGUE[self.renderer.palette_selected]
            self.renderer.drag_origin = (x, y)
            self.renderer.drag_kind = spec.kind
            self.renderer.drag_pos = (x, y)

    def _handle_release(self, pos: tuple[int, int]) -> None:
        kind = self.renderer.drag_kind
        if kind is None:
            return
        point = self._reference_point(pos)
        self._cancel_drag()
        if point is None:
            return
        x, y = point
        if not self._inside_playfield(x, y):
            return
        # Don't place on top of the marble spawn area or the basket area
        level = LEVELS[self.level_index]
        bx, by = level.basket_x, level.basket_y
        if math_hypot(x - bx, y - by) < level.basket_radius + 14:
            return
        if math_hypot(x - 160, y - 110) < 28:
            return
        spec = next(item for item in TOOL_CATALOGUE if item.kind == kind)
        tool = PlacedTool(spec, float(x), float(y))
        if self.engine.add_tool(tool):
            self.events.tool_placed(kind.value)
            self.audio.play("place")

    def _handle_motion(self, pos: tuple[int, int]) -> None:
        if self.renderer.drag_kind is None:
            return
        self.renderer.drag_pos = self._reference_point(pos)

    def _try_drop(self) -> None:
        if self.phase == Phase.RUNNING:
            return
        self.engine.reset_marble()
        self.phase = Phase.RUNNING
        self.pre_drop_timer = 0.45  # 450 ms breathing pause so the child sees the marble
        self.events.run_started(LEVELS[self.level_index].level_id)
        self.audio.play("place")

    def _clear_tools(self) -> None:
        if self.phase == Phase.RUNNING:
            return
        # Rebuild the engine with the same level so placed tools go away
        self.engine = RampEngine(level=LEVELS[self.level_index])

    def _inside_playfield(self, x: int, y: int) -> bool:
        return PLAYFIELD_LEFT <= x <= PLAYFIELD_RIGHT and PLAYFIELD_TOP <= y <= PLAYFIELD_BOTTOM

    # ------------------------------------------------------------------
    # Update + draw
    # ------------------------------------------------------------------

    def _update(self, dt: float) -> None:
        if self.phase != Phase.RUNNING:
            return
        if self.pre_drop_timer > 0:
            self.pre_drop_timer -= dt
            if self.pre_drop_timer <= 0:
                self.pre_drop_timer = 0
            return
        events = self.engine.step(dt)
        for ev in events:
            if ev.kind == "tool_hit":
                self.audio.play("bounce")
            elif ev.kind == "basket_hit":
                self._on_basket_hit()
            elif ev.kind == "missed":
                self._on_missed()
                self.audio.play("miss")

    def _on_basket_hit(self) -> None:
        elapsed = self.engine.elapsed
        level = LEVELS[self.level_index]
        self.events.basket_hit(level.level_id, elapsed)
        improved, new_best = self.storage.record_completion(level.level_id, elapsed)
        self.last_outcome = "hit"
        self.last_elapsed = elapsed
        self.last_improved = improved
        if improved and not self.last_published_best:
            self.last_published_best = True
            self.events.personal_best(level.level_id, elapsed)
        self.events.level_completed(level.level_id, elapsed, improved)
        self.phase = Phase.FINISHED
        self.finished_banner_timer = 1.6
        self.audio.play("win")

    def _on_missed(self) -> None:
        elapsed = self.engine.elapsed
        level = LEVELS[self.level_index]
        self.events.basket_missed(level.level_id, elapsed)
        self.last_outcome = "missed"
        self.last_elapsed = elapsed
        self.last_improved = False
        self.phase = Phase.FINISHED
        self.finished_banner_timer = 1.2

    def _draw(self) -> None:
        level = LEVELS[self.level_index]
        best_time = self.storage.best_time(level.level_id)
        text_fn = self._make_text_fn()
        marble = (
            self.engine.marble.x,
            self.engine.marble.y,
            self.engine.marble.vx,
            self.engine.marble.vy,
        )
        self.renderer.draw(
            level=level,
            level_index=self.level_index,
            tools=self.engine.tools,
            marble=marble,
            elapsed=self.engine.elapsed,
            finished=self.phase == Phase.FINISHED,
            outcome=self.last_outcome if self.phase == Phase.FINISHED else None,
            best_time=best_time,
            text_fn=text_fn,
        )
        # If the result banner has timed out, advance to the next level
        # automatically (or repeat the same level on miss).
        if (
            self.phase == Phase.FINISHED
            and self.finished_banner_timer > 0
        ):
            self.finished_banner_timer -= 1.0 / 30.0
        elif (
            self.phase == Phase.FINISHED
            and self.finished_banner_timer <= 0
        ):
            self._advance_after_banner()

    def _advance_after_banner(self) -> None:
        if self.last_outcome == "hit":
            self.level_index = min(self.level_index + 1, len(LEVELS) - 1)
            self.last_published_best = False
        # Reset for the next attempt
        self.engine = RampEngine(level=LEVELS[self.level_index])
        self.phase = Phase.PALETTE

    def _make_text_fn(self):
        # The renderer needs a callable that turns a string into a
        # pygame.Surface with the right color. We use GreiaTypography
        # so the ADR 0034 capitals policy is respected for every
        # child-facing string.
        typography = self.typography

        def fn(text: str, color: tuple[int, int, int]) -> pygame.Surface:
            return typography.render(
                display_text(text), FontRole.DISPLAY, 18, color
            )

        return fn


def math_hypot(x: float, y: float) -> float:
    return (x * x + y * y) ** 0.5


def build_app(
    screen: pygame.Surface,
    locale: str = "it",
    package_root: Path | None = None,
) -> RampApp:
    """Composition root for the headless launch / simulator gate."""
    pygame.init()
    pygame.display.set_caption("La Discesa della Biglia")
    metrics = ChildUiMetrics.for_size(*screen.get_size())
    theme = get_theme()
    typography = GreiaTypography()
    support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it")
    context = resolve_activity_locale(locale, support)
    if context is None:
        context = resolve_activity_locale("it", support)
    assert context is not None
    root = package_root or Path(__file__).resolve().parent
    resources = LocalizedResources(root, context)
    audio = RampAudio()
    storage = RampStorage.load()
    events = RampEvents()
    return RampApp(
        screen=screen,
        metrics=metrics,
        theme=theme,
        typography=typography,
        resources=resources,
        audio=audio,
        storage=storage,
        events=events,
    )


# Path import for the locale loader (kept local to avoid a top-level
# stdlib import in the package init).
from pathlib import Path  # noqa: E402
