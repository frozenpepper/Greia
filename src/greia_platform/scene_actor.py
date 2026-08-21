"""Renderer-neutral scene actor sampling for Greia characters.

This layer deliberately stays smaller than a generic entity/component system.
It provides only the reusable character facts Greia currently needs inside
layered storybook scenes: semantic visual state, deterministic blink timing,
cheap whole-character idle motion, shared contact-shadow grounding and scene
z/parallax placement.

The output is ordinary ``SceneNode`` data, so Pygame and future Web renderers
consume the same semantics through the existing scene pipeline.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .scene import SceneDefinition, SceneError, SceneFit, SceneNode


@dataclass(frozen=True, slots=True)
class SceneActorDefinition:
    """One bounded Greia character placement inside a scene.

    ``rect`` and ``shadow_rect`` are authored in the parent scene reference
    canvas. Character animation intentionally changes state/position rather than
    requiring skeletal rigs or continuously varying raster sizes.
    """

    actor_id: str
    asset_id: str
    rect: tuple[float, float, float, float]
    shadow_asset_id: str
    shadow_rect: tuple[float, float, float, float]
    z: int = 75
    parallax: float = 0.30
    neutral_variant: str = "default"
    blink_variant: str = "blink"
    idle_amplitude: float = 3.0
    idle_period_seconds: float = 2.4
    idle_phase: float = 0.0
    blink_period_seconds: float = 4.8
    blink_duration_seconds: float = 0.18
    blink_phase: float = 0.0
    shadow_alpha: float = 0.42

    def __post_init__(self) -> None:
        actor_id = self.actor_id.strip()
        asset_id = self.asset_id.strip()
        shadow_asset_id = self.shadow_asset_id.strip()
        neutral_variant = self.neutral_variant.strip()
        blink_variant = self.blink_variant.strip()
        if not actor_id:
            raise SceneError("scene actor_id must not be empty")
        if not asset_id:
            raise SceneError(f"scene actor {actor_id!r} asset_id must not be empty")
        if not shadow_asset_id:
            raise SceneError(
                f"scene actor {actor_id!r} shadow_asset_id must not be empty"
            )
        if not neutral_variant or not blink_variant:
            raise SceneError("scene actor variants must not be empty")

        rect = _rect(self.rect, "rect")
        shadow_rect = _rect(self.shadow_rect, "shadow_rect")
        parallax = _finite(self.parallax, "parallax")
        if not 0.0 <= parallax <= 1.0:
            raise SceneError("scene actor parallax must be between 0 and 1")

        idle_amplitude = _finite(self.idle_amplitude, "idle_amplitude")
        if not 0.0 <= idle_amplitude <= 24.0:
            raise SceneError("scene actor idle_amplitude must be between 0 and 24")
        idle_period = _finite(self.idle_period_seconds, "idle_period_seconds")
        if not 0.5 <= idle_period <= 30.0:
            raise SceneError("scene actor idle period must be between 0.5 and 30 seconds")
        idle_phase = _finite(self.idle_phase, "idle_phase")

        blink_period = _finite(self.blink_period_seconds, "blink_period_seconds")
        blink_duration = _finite(self.blink_duration_seconds, "blink_duration_seconds")
        blink_phase = _finite(self.blink_phase, "blink_phase")
        if not 1.0 <= blink_period <= 30.0:
            raise SceneError("scene actor blink period must be between 1 and 30 seconds")
        if not 0.05 <= blink_duration <= 0.6:
            raise SceneError("scene actor blink duration must be between 0.05 and 0.6 seconds")
        if blink_duration >= blink_period:
            raise SceneError("scene actor blink duration must be shorter than its period")

        shadow_alpha = _finite(self.shadow_alpha, "shadow_alpha")
        if not 0.0 <= shadow_alpha <= 1.0:
            raise SceneError("scene actor shadow_alpha must be between 0 and 1")

        object.__setattr__(self, "actor_id", actor_id)
        object.__setattr__(self, "asset_id", asset_id)
        object.__setattr__(self, "shadow_asset_id", shadow_asset_id)
        object.__setattr__(self, "neutral_variant", neutral_variant)
        object.__setattr__(self, "blink_variant", blink_variant)
        object.__setattr__(self, "rect", rect)
        object.__setattr__(self, "shadow_rect", shadow_rect)
        object.__setattr__(self, "z", int(self.z))
        object.__setattr__(self, "parallax", parallax)
        object.__setattr__(self, "idle_amplitude", idle_amplitude)
        object.__setattr__(self, "idle_period_seconds", idle_period)
        object.__setattr__(self, "idle_phase", idle_phase)
        object.__setattr__(self, "blink_period_seconds", blink_period)
        object.__setattr__(self, "blink_duration_seconds", blink_duration)
        object.__setattr__(self, "blink_phase", blink_phase)
        object.__setattr__(self, "shadow_alpha", shadow_alpha)


@dataclass(frozen=True, slots=True)
class SceneActorSample:
    actor_id: str
    state: str
    nodes: tuple[SceneNode, SceneNode]


def sample_scene_actor(
    actor: SceneActorDefinition,
    *,
    elapsed_seconds: float,
    motion_enabled: bool = True,
) -> SceneActorSample:
    """Sample one actor as contact-shadow + body scene nodes.

    The contact shadow remains grounded while the body performs a very small
    vertical idle. Blink is a bounded semantic variant swap and therefore warms
    at most one additional cached surface size; it does not create per-frame
    raster variants.
    """

    elapsed = _finite(elapsed_seconds, "elapsed_seconds")
    idle_offset = 0.0
    if motion_enabled and actor.idle_amplitude:
        idle_angle = math.tau * (
            elapsed / actor.idle_period_seconds + actor.idle_phase
        )
        idle_offset = math.sin(idle_angle) * actor.idle_amplitude

    state = actor.neutral_variant
    if motion_enabled:
        blink_clock = (
            elapsed + actor.blink_phase * actor.blink_period_seconds
        ) % actor.blink_period_seconds
        if blink_clock < actor.blink_duration_seconds:
            state = actor.blink_variant

    x, y, width, height = actor.rect
    body = SceneNode(
        node_id=f"{actor.actor_id}.body",
        asset_id=actor.asset_id,
        variant=state,
        rect=(x, y + idle_offset, width, height),
        z=actor.z,
        parallax=actor.parallax,
    )

    shadow_alpha = actor.shadow_alpha
    if motion_enabled and actor.idle_amplitude:
        # A tiny inverse opacity change reinforces lift without changing shadow
        # geometry or creating continuously varying cached sizes.
        normalized_lift = max(0.0, idle_offset / max(actor.idle_amplitude, 1e-9))
        shadow_alpha *= 1.0 - 0.12 * normalized_lift

    shadow = SceneNode(
        node_id=f"{actor.actor_id}.shadow",
        asset_id=actor.shadow_asset_id,
        rect=actor.shadow_rect,
        z=actor.z - 1,
        parallax=actor.parallax,
        alpha=shadow_alpha,
        optional=True,
    )
    return SceneActorSample(actor.actor_id, state, (shadow, body))


def actor_scene_sample(
    actor: SceneActorDefinition,
    *,
    canvas_size: tuple[int, int],
    elapsed_seconds: float,
    fit: SceneFit = SceneFit.COVER,
    motion_enabled: bool = True,
) -> SceneDefinition:
    """Return a tiny scene suitable for ``PygameSceneRenderer.draw(clear=False)``.

    This keeps actor rendering on the same scene/cache path instead of creating
    another Pygame character renderer. Future renderers may consume the sampled
    nodes directly.
    """

    sample = sample_scene_actor(
        actor,
        elapsed_seconds=elapsed_seconds,
        motion_enabled=motion_enabled,
    )
    return SceneDefinition(
        scene_id=f"actor.{actor.actor_id}.sample",
        canvas_size=canvas_size,
        background=(0, 0, 0),
        nodes=sample.nodes,
        fit=fit,
    )


def _rect(
    value: tuple[float, float, float, float], label: str
) -> tuple[float, float, float, float]:
    if len(value) != 4:
        raise SceneError(f"scene actor {label} must contain x/y/w/h")
    result = tuple(_finite(item, label) for item in value)
    if result[2] <= 0.0 or result[3] <= 0.0:
        raise SceneError(f"scene actor {label} width/height must be positive")
    return result  # type: ignore[return-value]


def _finite(value: float, label: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise SceneError(f"scene actor {label} must be finite")
    return result


__all__ = [
    "SceneActorDefinition",
    "SceneActorSample",
    "actor_scene_sample",
    "sample_scene_actor",
]
