"""Shape Garden lifecycle coordinator with persistent creative projects."""
from __future__ import annotations

import hashlib
import math
import random
import time

import pygame

from greia_platform.activity_api import activity_stop_requested, emit_activity_event, get_theme, mark_activity_ready
from greia_platform.activity_ui import ChildUiMetrics
from greia_platform.pygame_canvas import PygameReferenceCanvas, activity_viewport_for_surface
from greia_platform.pygame_png import PygamePngError, decode_png_surface, encode_surface_png

if __package__:
    from .garden_content import COLORS, REFERENCE_HEIGHT, REFERENCE_WIDTH, SOIL_TOP
    from .garden_model import GardenModel, Particle, PlacedShape
    from .garden_project_model import GardenProject
    from .garden_project_repository import GardenProjectError, GardenProjectRepository
    from .garden_renderer import GardenRenderer, draw_shape, draw_sprout_stem
else:  # pragma: no cover - direct script fallback
    from garden_content import COLORS, REFERENCE_HEIGHT, REFERENCE_WIDTH, SOIL_TOP
    from garden_model import GardenModel, Particle, PlacedShape
    from garden_project_model import GardenProject
    from garden_project_repository import GardenProjectError, GardenProjectRepository
    from garden_renderer import GardenRenderer, draw_shape, draw_sprout_stem


def _safe_point(surface: pygame.Surface, position: tuple[int, int]) -> bool:
    viewport = activity_viewport_for_surface(surface)
    x, y = position
    if not (0 <= x < viewport.surface.width and 0 <= y < viewport.surface.height):
        return False
    for protected in viewport.protected_regions:
        if protected.x <= x < protected.right and protected.y <= y < protected.bottom:
            return False
    safe = viewport.safe_ui_rect()
    return safe.x <= x < safe.right and safe.y <= y < safe.bottom


class GardenApp:
    """Preserve tap-to-grow play while adding one durable editable composition."""

    IMPORT_POLL_SECONDS = 0.12
    AUTOSAVE_SECONDS = 0.40

    def __init__(
        self,
        screen: pygame.Surface | None = None,
        *,
        repository: GardenProjectRepository | None = None,
        creations=None,
    ) -> None:
        pygame.init()
        if screen is None:
            screen = pygame.display.get_surface()
            if screen is None:
                screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        pygame.mouse.set_visible(False)
        self.screen: pygame.Surface = screen
        self.theme = get_theme()
        self.metrics = ChildUiMetrics.for_size(*self.screen.get_size())
        self.canvas = PygameReferenceCanvas(self.screen)
        self.renderer = GardenRenderer()
        self.model = GardenModel()
        self.repository = repository
        self.creations = creations
        self.clock = pygame.time.Clock()
        self.running = True
        self._ready_published = False
        self.start_time = time.monotonic()

        self.project = GardenProject()
        self.background_surface: pygame.Surface | None = None
        self.project_dirty = False
        self.project_save_due = 0.0
        self.project_error = False
        self.import_request: str | None = None
        self.import_next_poll = 0.0
        self.import_state = ""
        self.import_feedback_until = 0.0
        self.publish_state = ""
        self.publish_feedback_until = 0.0
        self._last_published_digest: str | None = None
        self._load_project()

    def _load_project(self) -> None:
        if self.repository is None:
            return
        try:
            project = self.repository.load()
            payload = self.repository.load_background(project)
            background = (
                decode_png_surface(payload, (REFERENCE_WIDTH, SOIL_TOP))
                if payload is not None
                else None
            )
            project.restore_model(self.model, self.start_time)
        except (GardenProjectError, PygamePngError, RuntimeError, ValueError, OSError):
            self.project_error = True
            return
        self.project = project
        self.background_surface = background

    # -- input ------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.running = False
        elif event.type == pygame.VIDEORESIZE:
            self.screen = pygame.display.get_surface() or self.screen
            self.metrics = ChildUiMetrics.for_size(*self.screen.get_size())
            self.canvas = PygameReferenceCanvas(self.screen)
            self.renderer.invalidate()
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._handle_pointer(event.pos)

    def _import_button(self) -> pygame.Rect:
        return self.metrics.activity_toolbar_button(0, side="right")

    def _publish_button(self) -> pygame.Rect:
        return self.metrics.activity_toolbar_button(1, side="right")

    def _handle_pointer(self, screen_pos: tuple[int, int]) -> None:
        if self.repository is not None and self.creations is not None:
            if self._import_button().collidepoint(screen_pos):
                self._request_background()
                return
            if self._publish_button().collidepoint(screen_pos):
                self._publish_project()
                return
        if not _safe_point(self.screen, screen_pos):
            return
        logical = self.canvas.pointer(screen_pos)
        if logical is None:
            return
        x, y = (int(round(logical[0])), int(round(logical[1])))
        if 0 <= x < REFERENCE_WIDTH and 0 <= y < SOIL_TOP:
            now = time.monotonic()
            color_idx = random.randrange(len(COLORS))
            self.model.add_shape(
                PlacedShape(
                    x=x,
                    y=y,
                    size=random.randint(22, 46),
                    kind=random.randrange(3),
                    color_index=color_idx,
                    spawn_time=now,
                )
            )
            self.model.trigger_reaction(now)
            self.project_dirty = True
            self.project_save_due = now + self.AUTOSAVE_SECONDS
            c = COLORS[color_idx]
            particles: list[Particle] = []
            for _ in range(5):
                angle = random.uniform(0, math.tau)
                speed = random.uniform(20.0, 60.0)
                particles.append(
                    Particle(
                        x=float(x),
                        y=float(y),
                        vx=math.cos(angle) * speed,
                        vy=math.sin(angle) * speed - 30.0,
                        color=c,
                        birth_time=now,
                        lifetime=random.uniform(0.35, 0.65),
                    )
                )
            self.model.add_particles(particles)

    # -- project / creations ---------------------------------------

    def _save_project(self) -> bool:
        if not self.project_dirty:
            return True
        if self.repository is None:
            self.project_dirty = False
            return True
        candidate = GardenProject.from_model(
            self.model, self.project.background_sha256
        )
        try:
            self.project = self.repository.save(candidate)
        except (GardenProjectError, RuntimeError, ValueError, OSError):
            self.project_error = True
            return False
        self.project_dirty = False
        self.project_error = False
        return True

    def _request_background(self) -> None:
        if (
            self.creations is None
            or self.repository is None
            or self.import_request is not None
        ):
            return
        if not self._save_project():
            self.import_state = "error"
            self.import_feedback_until = time.monotonic() + 2.0
            return
        try:
            request_id = self.creations.request_selection(
                media_types=("image/png",)
            )
        except (RuntimeError, ValueError, OSError):
            self.import_state = "error"
            self.import_feedback_until = time.monotonic() + 2.0
            return
        self.import_request = request_id
        self.import_state = "pending"
        self.import_next_poll = time.monotonic() + self.IMPORT_POLL_SECONDS

    def _poll_background(self, now: float) -> None:
        request_id = self.import_request
        if (
            request_id is None
            or self.creations is None
            or now < self.import_next_poll
        ):
            return
        self.import_next_poll = now + self.IMPORT_POLL_SECONDS
        try:
            result = self.creations.poll_selection(request_id)
        except (RuntimeError, ValueError, OSError):
            self.import_request = None
            self.import_state = "error"
            self.import_feedback_until = now + 2.0
            return
        if result.state == "pending":
            return
        self.import_request = None
        if result.state == "cancelled":
            self.import_state = ""
            return
        token = result.selection_token
        if result.state != "ready" or not isinstance(token, str) or not token:
            self.import_state = "error"
            self.import_feedback_until = now + 2.0
            return
        self.import_state = "imported" if self._accept_background(token) else "error"
        self.import_feedback_until = now + 2.0

    def _accept_background(self, selection_token: str) -> bool:
        if self.creations is None or self.repository is None:
            return False
        try:
            transfer = self.creations.import_selected(selection_token)
            payload = transfer.payload
            if (
                transfer.record.get("media_type") != "image/png"
                or not isinstance(payload, bytes)
                or transfer.record.get("sha256")
                != hashlib.sha256(payload).hexdigest()
            ):
                raise ValueError("selected backdrop failed integrity validation")
            background = decode_png_surface(
                payload, (REFERENCE_WIDTH, SOIL_TOP)
            )
            candidate = GardenProject.from_model(
                self.model, self.project.background_sha256
            )
            committed = self.repository.save(
                candidate, replacement_background_png=payload
            )
        except (
            GardenProjectError,
            PygamePngError,
            RuntimeError,
            ValueError,
            OSError,
        ):
            return False
        self.project = committed
        self.background_surface = background
        self.project_dirty = False
        self.project_error = False
        return True

    def _render_project_snapshot(self) -> pygame.Surface:
        target = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT))
        if self.background_surface is not None:
            target.blit(self.background_surface, (0, 0))
        else:
            self.renderer.draw_sky(target)
            self.renderer.draw_backdrop(target, 0.0, "neutral", "idle_bounce")
        self.renderer.draw_soil(target, self.theme.accent)
        for shape in self.model.active_shapes():
            draw_sprout_stem(target, shape.x, shape.y, shape.size)
            self.renderer.draw_shape_shadow(target, shape.x, shape.y, shape.size)
            draw_shape(
                target,
                shape.x,
                shape.y,
                shape.size,
                shape.kind,
                COLORS[shape.color_index],
                scale=1.0,
            )
        return target

    def _publish_project(self) -> None:
        if self.creations is None or self.repository is None:
            return
        if not self._save_project():
            self.publish_state = "error"
            self.publish_feedback_until = time.monotonic() + 2.0
            return
        try:
            payload = encode_surface_png(self._render_project_snapshot())
            digest = hashlib.sha256(payload).hexdigest()
            if digest != self._last_published_digest:
                name = self.repository.save_export(payload)
                self.creations.publish_private_file(
                    name, media_type="image/png", role="composition"
                )
                self._last_published_digest = digest
                try:
                    emit_activity_event(
                        "creation.completed",
                        idempotency_key=f"composition-{digest}",
                        payload={
                            "media_type": "image/png",
                            "shape_count": len(self.model.active_shapes()),
                        },
                    )
                except Exception:
                    # Progress telemetry must never make a successful child
                    # creation publication fail or duplicate the Creation.
                    pass
            self.publish_state = "saved"
        except (
            GardenProjectError,
            PygamePngError,
            RuntimeError,
            ValueError,
            OSError,
        ):
            self.publish_state = "error"
        self.publish_feedback_until = time.monotonic() + 2.0

    # -- per-frame --------------------------------------------------

    def _step_frame(self, now: float) -> None:
        self.model.update_particles(now)
        if self.project_dirty and now >= self.project_save_due:
            self._save_project()
        self._poll_background(now)
        if (
            self.import_state
            and self.import_state != "pending"
            and now >= self.import_feedback_until
        ):
            self.import_state = ""
        if self.publish_state and now >= self.publish_feedback_until:
            self.publish_state = ""

    def _draw(self, now: float, elapsed: float) -> None:
        if self.model.is_reacting(now):
            companion_state, companion_motion = "happy", "happy_hop"
        else:
            companion_state, companion_motion = "neutral", "idle_bounce"

        if self.background_surface is not None:
            self.canvas.surface.blit(self.background_surface, (0, 0))
        else:
            self.renderer.draw_sky(self.canvas.surface)
            self.renderer.draw_backdrop(
                self.canvas.surface, elapsed, companion_state, companion_motion
            )
        self.renderer.draw_soil(self.canvas.surface, self.theme.accent)

        active_shapes = self.model.active_shapes()
        for shape in active_shapes:
            draw_sprout_stem(self.canvas.surface, shape.x, shape.y, shape.size)
        for shape in active_shapes:
            self.renderer.draw_shape_shadow(
                self.canvas.surface, shape.x, shape.y, shape.size
            )
        for shape in active_shapes:
            age = now - shape.spawn_time
            scale = 1.0
            if age < 0.15:
                phase = age / 0.15
                scale = 0.5 + 0.65 * math.sin(phase * math.pi * 0.8)
            draw_shape(
                self.canvas.surface,
                shape.x,
                shape.y,
                shape.size,
                shape.kind,
                COLORS[shape.color_index],
                scale=scale,
            )

        for particle in self.model.particles:
            age = now - particle.birth_time
            fade = (
                max(0.0, 1.0 - age / particle.lifetime)
                if particle.lifetime > 0
                else 0.0
            )
            pygame.draw.circle(
                self.canvas.surface,
                particle.color,
                (int(round(particle.x)), int(round(particle.y))),
                max(2, int(round(4 * fade))),
            )

        self.canvas.present(clear=self.theme.background)
        self._draw_creation_controls()

    def _draw_creation_controls(self) -> None:
        if self.repository is None or self.creations is None:
            return
        for rect, direction, state in (
            (self._import_button(), "down", self.import_state),
            (self._publish_button(), "up", self.publish_state),
        ):
            fill = (218, 237, 252) if direction == "down" else (220, 244, 226)
            if state in {"pending", "saved", "imported"}:
                fill = (166, 217, 244) if direction == "down" else (166, 226, 181)
            pygame.draw.rect(self.screen, fill, rect, border_radius=self.metrics.radius)
            border = (200, 55, 62) if state == "error" else (61, 75, 98)
            pygame.draw.rect(
                self.screen,
                border,
                rect,
                width=max(2, self.metrics.px(2)),
                border_radius=self.metrics.radius,
            )
            cx, cy = rect.center
            icon_w = self.metrics.px(25)
            icon_h = self.metrics.px(16)
            pygame.draw.rect(
                self.screen,
                (61, 75, 98),
                (cx - icon_w // 2, cy, icon_w, icon_h),
                width=max(2, self.metrics.px(2)),
                border_radius=self.metrics.px(3),
            )
            arrow = -1 if direction == "up" else 1
            pygame.draw.line(
                self.screen,
                (61, 75, 98),
                (cx, cy - arrow * self.metrics.px(15)),
                (cx, cy + arrow * self.metrics.px(3)),
                max(3, self.metrics.px(3)),
            )
            tip_y = cy + arrow * self.metrics.px(4)
            pygame.draw.lines(
                self.screen,
                (61, 75, 98),
                False,
                [
                    (cx - self.metrics.px(7), tip_y - arrow * self.metrics.px(7)),
                    (cx, tip_y),
                    (cx + self.metrics.px(7), tip_y - arrow * self.metrics.px(7)),
                ],
                max(3, self.metrics.px(3)),
            )

    # -- main loop --------------------------------------------------

    def run(self) -> int:
        try:
            while self.running and not activity_stop_requested():
                now = time.monotonic()
                elapsed = now - self.start_time
                for event in pygame.event.get():
                    self.handle_event(event)
                self._step_frame(now)
                self._draw(now, elapsed)
                pygame.display.flip()
                if not self._ready_published:
                    mark_activity_ready()
                    self._ready_published = True
                self.clock.tick(30)
        finally:
            self._save_project()
        return 0


__all__ = ["GardenApp"]
