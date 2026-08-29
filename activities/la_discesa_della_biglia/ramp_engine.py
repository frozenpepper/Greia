"""La Discesa della Biglia — deterministic physics engine.

The engine owns one marble and a set of placed tools. It integrates
with sub-steps so fast-moving objects never tunnel through tools
on the reference floor. All units are reference pixels and seconds
so the engine is fully unit-testable without Pygame.

The engine does not know about rendering, audio, or Greia
services. That separation is required by the engineering skill so
the physics semantics can be covered by deterministic contract
tests independently from the visual layer.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Final

if __package__:
    from .ramp_content import (
        FAN_WIND,
        FRICTION_PER_SECOND,
        GRAVITY,
        MARBLE_RADIUS,
        MARBLE_START,
        PHYSICS_SUBSTEPS,
        PLAYFIELD_BOTTOM,
        PLAYFIELD_LEFT,
        PLAYFIELD_RIGHT,
        PLAYFIELD_TOP,
        RESTITUTION,
        SPRING_IMPULSE,
        SPRING_RADIUS,
        TOOL_BUMPER_RADIUS,
        TOOL_RADIUS,
        Level,
        PlacedTool,
        ToolKind,
    )
else:
    from ramp_content import (
        FAN_WIND,
        FRICTION_PER_SECOND,
        GRAVITY,
        MARBLE_RADIUS,
        MARBLE_START,
        PHYSICS_SUBSTEPS,
        PLAYFIELD_BOTTOM,
        PLAYFIELD_LEFT,
        PLAYFIELD_RIGHT,
        PLAYFIELD_TOP,
        RESTITUTION,
        SPRING_IMPULSE,
        SPRING_RADIUS,
        TOOL_BUMPER_RADIUS,
        TOOL_RADIUS,
        Level,
        PlacedTool,
        ToolKind,
    )


@dataclass
class Marble:
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    on_tool: bool = False  # set per sub-step; used for restitution


@dataclass(frozen=True, slots=True)
class CollisionEvent:
    """A semantic collision reported by the engine for this sub-step.

    The engine reports a basket hit, a tool hit, a missed-marble (left
    the playfield without touching the basket) or a settled (stopped
    in the basket). The Activity turn layer translates these into
    the right Greia event.
    """

    kind: str  # "basket_hit" | "tool_hit" | "missed" | "settled"
    tool_kind: str | None = None
    position: tuple[float, float] = (0.0, 0.0)


@dataclass
class RampEngine:
    """Deterministic physics state for one running play attempt."""

    level: Level
    tools: list[PlacedTool] = field(default_factory=list)
    marble: Marble = field(
        default_factory=lambda: Marble(MARBLE_START[0], MARBLE_START[1])
    )
    elapsed: float = 0.0
    finished: bool = False
    outcome: str | None = None  # "hit" | "missed" | None
    spent_tools: set[int] = field(default_factory=set)

    def reset_marble(self) -> None:
        self.marble = Marble(MARBLE_START[0], MARBLE_START[1])
        self.elapsed = 0.0
        self.finished = False
        self.outcome = None
        self.spent_tools = set()

    def add_tool(self, tool: PlacedTool) -> bool:
        if self.finished:
            return False
        # Tool placement is a normal additive semantic; the engine
        # does not enforce a maximum count because that is a balance
        # decision owned by the level, not the engine.
        self.tools.append(tool)
        return True

    def basket_position(self) -> tuple[float, float]:
        if not self.level.basket_moves:
            return self.level.basket_x, self.level.basket_y
        if self.level.basket_period <= 0:
            return self.level.basket_x, self.level.basket_y
        phase = (self.elapsed / self.level.basket_period) * 2.0 * math.pi
        return (
            self.level.basket_x
            + self.level.basket_amplitude * math.sin(phase),
            self.level.basket_y,
        )

    def step(self, frame_dt: float) -> list[CollisionEvent]:
        """Advance the simulation by `frame_dt` seconds.

        Returns a list of semantic events emitted during the step.
        The caller decides how to render / score / persist them.
        """
        if self.finished:
            return []
        events: list[CollisionEvent] = []
        # Clamp dt so a paused tab cannot make the marble teleport
        dt = min(frame_dt, 1.0 / 15.0)
        sub_dt = dt / float(PHYSICS_SUBSTEPS)
        for _ in range(PHYSICS_SUBSTEPS):
            if self.finished:
                break
            self.elapsed += sub_dt
            sub_events = self._substep(sub_dt)
            events.extend(sub_events)
        return events

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _substep(self, sub_dt: float) -> list[CollisionEvent]:
        marble = self.marble
        # Gravity
        marble.vy += GRAVITY * sub_dt
        # Linear damping (approximation of rolling/air drag)
        damp = max(0.0, 1.0 - FRICTION_PER_SECOND * sub_dt)
        marble.vx *= damp
        marble.vy *= damp
        # Integrate
        marble.x += marble.vx * sub_dt
        marble.y += marble.vy * sub_dt
        # Wall collisions
        events: list[CollisionEvent] = []
        if marble.x - MARBLE_RADIUS < PLAYFIELD_LEFT:
            marble.x = PLAYFIELD_LEFT + MARBLE_RADIUS
            marble.vx = -marble.vx * RESTITUTION
        elif marble.x + MARBLE_RADIUS > PLAYFIELD_RIGHT:
            marble.x = PLAYFIELD_RIGHT - MARBLE_RADIUS
            marble.vx = -marble.vx * RESTITUTION
        if marble.y - MARBLE_RADIUS < PLAYFIELD_TOP:
            marble.y = PLAYFIELD_TOP + MARBLE_RADIUS
            marble.vy = -marble.vy * RESTITUTION
        if marble.y - MARBLE_RADIUS > PLAYFIELD_BOTTOM:
            self.finished = True
            self.outcome = "missed"
            events.append(
                CollisionEvent("missed", position=(marble.x, marble.y))
            )
            return events
        # Tool collisions
        for tool_index, tool in enumerate(self.tools):
            sub = self._collide_tool(marble, tool_index, tool, sub_dt)
            if sub is not None:
                events.append(sub)
        # Obstacles (level geometry)
        for ox, oy, orad in self.level.obstacles:
            sub = self._collide_circle(
                marble, ox, oy, orad + MARBLE_RADIUS, restitution=RESTITUTION
            )
            if sub is not None:
                events.append(
                    CollisionEvent(
                        "tool_hit", tool_kind="obstacle",
                        position=(ox, oy),
                    )
                )
        # Basket
        bx, by = self.basket_position()
        in_basket = self._collide_basket(marble, bx, by, self.level.basket_radius)
        if in_basket:
            self.finished = True
            self.outcome = "hit"
            events.append(CollisionEvent("basket_hit", position=(bx, by)))
        return events

    def _collide_tool(
        self, marble: Marble, tool_index: int, tool: PlacedTool, sub_dt: float
    ) -> CollisionEvent | None:
        kind = tool.spec.kind
        if kind == ToolKind.SLOPE:
            return self._collide_slope(marble, tool, sub_dt)
        if kind == ToolKind.BUMPER:
            return self._collide_bumper(marble, tool)
        if kind == ToolKind.FAN:
            return self._collide_fan(marble, tool, sub_dt)
        if kind == ToolKind.SPRING:
            return self._collide_spring(marble, tool_index, tool)
        return None

    def _collide_slope(
        self, marble: Marble, tool: PlacedTool, sub_dt: float
    ) -> CollisionEvent | None:
        """Slope = upper face of a thick line segment + two endpoint
        hemispheres.

        The slope's *upper* face is the only solid side. The lower
        face and the side walls are open so the marble can fall
        under or past the slope when the child places it
        poorly. The two endpoints are full hemispheres (rounded
        corners), so the marble cannot tunnel through the corners.
        """
        ang = tool.angle
        half_len = 38.0
        thickness = 8.0
        # Surface direction (along the segment) and upward normal
        sx, sy = math.cos(ang), math.sin(ang)
        # Two perpendicular normals: "up" (perpendicular rotated 90
        # CCW) and "down" (CW). The slope's upper face uses "up".
        up_nx, up_ny = -sy, sx
        down_nx, down_ny = sy, -sx
        rel_mx = marble.x - tool.x
        rel_my = marble.y - tool.y
        # Project onto the slope's surface axis to find the closest
        # point on the (infinite) line.
        proj_along = rel_mx * sx + rel_my * sy
        # Distance from the marble to the slope line (signed: positive
        # = above the upper face, negative = below the lower face).
        perp_dist = rel_mx * up_nx + rel_my * up_ny
        # Decide contact geometry
        endpoint_hit = abs(proj_along) > half_len
        if endpoint_hit:
            # Endpoint: full hemisphere of radius (thickness + marble_r)
            end_sign = 1.0 if proj_along > 0 else -1.0
            end_cx = tool.x + end_sign * half_len * sx
            end_cy = tool.y + end_sign * half_len * sy
            dx = marble.x - end_cx
            dy = marble.y - end_cy
            dist = math.hypot(dx, dy)
            contact_radius = thickness + MARBLE_RADIUS
            if dist >= contact_radius:
                return None
            if dist < 1e-6:
                push_nx, push_ny = 0.0, -1.0
            else:
                push_nx = dx / dist
                push_ny = dy / dist
            overlap = contact_radius - dist
            marble.x += push_nx * overlap
            marble.y += push_ny * overlap
            v_dot_n = marble.vx * push_nx + marble.vy * push_ny
            if v_dot_n < 0:
                marble.vx -= (1.0 + RESTITUTION) * v_dot_n * push_nx
                marble.vy -= (1.0 + RESTITUTION) * v_dot_n * push_ny
            return CollisionEvent(
                "tool_hit", tool_kind=ToolKind.SLOPE.value,
                position=(end_cx, end_cy),
            )
        # On the segment: only the upper face is solid
        if perp_dist >= 0:
            # Marble is above the slope's upper face: solid collision
            target_perp = -(thickness + MARBLE_RADIUS)
            dx = -perp_dist - (thickness + MARBLE_RADIUS)
            # actually target perp is the marble center's distance from
            # the slope center; we want the marble to sit at
            # perp_dist = -(thickness + MARBLE_RADIUS)
            correction = target_perp - perp_dist  # negative number
            marble.x += up_nx * correction
            marble.y += up_ny * correction
            v_dot_n = marble.vx * up_nx + marble.vy * up_ny
            if v_dot_n < 0:
                marble.vx -= (1.0 + RESTITUTION) * v_dot_n * up_nx
                marble.vy -= (1.0 + RESTITUTION) * v_dot_n * up_ny
            return CollisionEvent(
                "tool_hit", tool_kind=ToolKind.SLOPE.value,
                position=(tool.x + proj_along * sx, tool.y + proj_along * sy),
            )
        # Marble is below the upper face. If it is also above the
        # lower face (perp_dist > -thickness - MARBLE_RADIUS) it has
        # tunnelled through the slope from above; resolve by pushing
        # it back to the upper side.
        if perp_dist > -(thickness + MARBLE_RADIUS):
            # Tunneled through: push back to the upper face
            target_perp = -(thickness + MARBLE_RADIUS)
            correction = target_perp - perp_dist
            marble.x += up_nx * correction
            marble.y += up_ny * correction
            v_dot_n = marble.vx * up_nx + marble.vy * up_ny
            if v_dot_n < 0:
                marble.vx -= (1.0 + RESTITUTION) * v_dot_n * up_nx
                marble.vy -= (1.0 + RESTITUTION) * v_dot_n * up_ny
            return CollisionEvent(
                "tool_hit", tool_kind=ToolKind.SLOPE.value,
                position=(tool.x + proj_along * sx, tool.y + proj_along * sy),
            )
        # Marble is below the lower face: no collision
        return None

    def _collide_bumper(
        self, marble: Marble, tool: PlacedTool
    ) -> CollisionEvent | None:
        event = self._collide_circle(
            marble, tool.x, tool.y, TOOL_BUMPER_RADIUS + MARBLE_RADIUS,
            restitution=1.05,
        )
        if event is not None:
            return CollisionEvent(
                "tool_hit", tool_kind=ToolKind.BUMPER.value,
                position=(tool.x, tool.y),
            )
        return None

    def _collide_fan(
        self, marble: Marble, tool: PlacedTool, sub_dt: float
    ) -> CollisionEvent | None:
        # Fan is a no-contact wind zone in a small radius. Push the
        # marble horizontally (right) while it is in range, falloff
        # linearly with distance.
        dx = marble.x - tool.x
        dy = marble.y - tool.y
        radius = 70.0
        d2 = dx * dx + dy * dy
        if d2 > radius * radius:
            return None
        falloff = 1.0 - math.sqrt(d2) / radius
        marble.vx += FAN_WIND * falloff * sub_dt
        return CollisionEvent(
            "tool_hit", tool_kind=ToolKind.FAN.value,
            position=(tool.x, tool.y),
        )

    def _collide_spring(
        self, marble: Marble, tool_index: int, tool: PlacedTool
    ) -> CollisionEvent | None:
        # Spring triggers once on contact, fires an outward impulse
        # from its center, then becomes inert for the rest of the run
        # so the marble can fly away cleanly.
        if tool_index in self.spent_tools:
            return None
        event = self._collide_circle(
            marble, tool.x, tool.y, SPRING_RADIUS + MARBLE_RADIUS,
            restitution=RESTITUTION,
        )
        if event is None:
            return None
        # Outward impulse
        dx = marble.x - tool.x
        dy = marble.y - tool.y
        mag = math.hypot(dx, dy) or 1.0
        marble.vx += (dx / mag) * SPRING_IMPULSE
        marble.vy += (dy / mag) * SPRING_IMPULSE - 40.0
        self.spent_tools.add(tool_index)
        return CollisionEvent(
            "tool_hit", tool_kind=ToolKind.SPRING.value,
            position=(tool.x, tool.y),
        )

    def _collide_circle(
        self,
        marble: Marble,
        cx: float,
        cy: float,
        radius: float,
        restitution: float,
    ) -> CollisionEvent | None:
        dx = marble.x - cx
        dy = marble.y - cy
        d2 = dx * dx + dy * dy
        if d2 >= radius * radius:
            return None
        if d2 < 1e-6:
            # Marble is exactly at the circle centre: push down so
            # the marble drops out of the bottom and the reflection
            # reverses any downward velocity.
            nx, ny = 0.0, 1.0
            d = 0.0
        else:
            d = math.sqrt(d2)
            nx = dx / d
            ny = dy / d
        # Push out
        overlap = radius - d
        marble.x += nx * overlap
        marble.y += ny * overlap
        # Reflect velocity along the contact normal
        v_dot_n = marble.vx * nx + marble.vy * ny
        if v_dot_n < 0:
            marble.vx -= (1.0 + restitution) * v_dot_n * nx
            marble.vy -= (1.0 + restitution) * v_dot_n * ny
        return CollisionEvent(
            "tool_hit", tool_kind=None, position=(cx, cy)
        )

    def _collide_basket(
        self, marble: Marble, bx: float, by: float, radius: float
    ) -> bool:
        # The basket is "open" from above: the marble enters when its
        # centre drops below the basket lip and is within the
        # horizontal radius, with a small velocity check to avoid
        # catching the marble on the basket's top arc.
        if marble.y < by - radius * 0.4:
            return False
        if marble.y > by + radius * 0.9:
            return False
        dx = marble.x - bx
        if abs(dx) > radius * 0.7:
            return False
        return marble.vy >= 0  # only on the way down
