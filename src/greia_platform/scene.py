"""Renderer-neutral Greia scene composition primitives.

Greia scenes are intentionally smaller than a general-purpose scene graph. They
provide exactly the reusable concepts the child OS and Activities need for
layered storybook composition: a fixed authoring canvas, explicit semantic
visual assets, z ordering, bounded parallax, simple ambient motion, alpha, and
responsive cover/contain mapping.

The module has no Pygame dependency and performs no file discovery. Runtime
renderers consume semantic asset IDs through the existing AssetCatalogue path.
"""

from __future__ import annotations

import math
import tomllib
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Mapping


class SceneError(ValueError):
    """Invalid scene definition or manifest."""


class SceneFit(str, Enum):
    COVER = "cover"
    CONTAIN = "contain"


class SceneMotionKind(str, Enum):
    NONE = "none"
    DRIFT_X = "drift_x"
    DRIFT_Y = "drift_y"
    FLOAT = "float"
    SWAY_X = "sway_x"
    BREATHE_ALPHA = "breathe_alpha"


@dataclass(frozen=True, slots=True)
class SceneMotion:
    """One cheap, deterministic ambient-motion primitive.

    ``amplitude`` is authored in scene-canvas pixels except for
    ``BREATHE_ALPHA``, where it is the maximum fractional alpha reduction.
    ``phase`` is expressed in cycles and therefore remains easy to stagger.
    """

    kind: SceneMotionKind = SceneMotionKind.NONE
    amplitude: float = 0.0
    period_seconds: float = 8.0
    phase: float = 0.0

    def __post_init__(self) -> None:
        amplitude = float(self.amplitude)
        period = float(self.period_seconds)
        phase = float(self.phase)
        if not math.isfinite(amplitude) or amplitude < 0.0:
            raise SceneError("motion amplitude must be a finite non-negative number")
        if not math.isfinite(period) or not 0.25 <= period <= 120.0:
            raise SceneError("motion period_seconds must be between 0.25 and 120")
        if not math.isfinite(phase):
            raise SceneError("motion phase must be finite")
        if self.kind is SceneMotionKind.BREATHE_ALPHA:
            if amplitude > 0.75:
                raise SceneError("alpha-breathe amplitude must be <= 0.75")
        elif amplitude > 128.0:
            raise SceneError("motion amplitude must be <= 128 design pixels")
        object.__setattr__(self, "amplitude", amplitude)
        object.__setattr__(self, "period_seconds", period)
        object.__setattr__(self, "phase", phase)


@dataclass(frozen=True, slots=True)
class SceneNode:
    """One semantic visual instance inside a Greia scene."""

    node_id: str
    asset_id: str
    rect: tuple[float, float, float, float]
    z: int = 0
    variant: str = "default"
    fallback_variant: str | None = None
    parallax: float = 0.0
    alpha: float = 1.0
    motion: SceneMotion = SceneMotion()
    optional: bool = False

    def __post_init__(self) -> None:
        node_id = self.node_id.strip()
        asset_id = self.asset_id.strip()
        variant = self.variant.strip()
        fallback_variant = (
            self.fallback_variant.strip()
            if self.fallback_variant is not None
            else None
        )
        if not node_id:
            raise SceneError("scene node_id must not be empty")
        if not asset_id:
            raise SceneError(f"scene node {node_id!r} asset_id must not be empty")
        if not variant:
            raise SceneError(f"scene node {node_id!r} variant must not be empty")
        if fallback_variant == "":
            fallback_variant = None
        if len(self.rect) != 4:
            raise SceneError(f"scene node {node_id!r} rect must contain x/y/w/h")
        x, y, width, height = (float(value) for value in self.rect)
        if not all(math.isfinite(value) for value in (x, y, width, height)):
            raise SceneError(f"scene node {node_id!r} rect values must be finite")
        if width <= 0.0 or height <= 0.0:
            raise SceneError(f"scene node {node_id!r} rect width/height must be positive")
        parallax = float(self.parallax)
        alpha = float(self.alpha)
        if not math.isfinite(parallax) or not 0.0 <= parallax <= 1.0:
            raise SceneError(f"scene node {node_id!r} parallax must be between 0 and 1")
        if not math.isfinite(alpha) or not 0.0 <= alpha <= 1.0:
            raise SceneError(f"scene node {node_id!r} alpha must be between 0 and 1")
        object.__setattr__(self, "node_id", node_id)
        object.__setattr__(self, "asset_id", asset_id)
        object.__setattr__(self, "variant", variant)
        object.__setattr__(self, "fallback_variant", fallback_variant)
        object.__setattr__(self, "rect", (x, y, width, height))
        object.__setattr__(self, "z", int(self.z))
        object.__setattr__(self, "parallax", parallax)
        object.__setattr__(self, "alpha", alpha)
        object.__setattr__(self, "optional", bool(self.optional))


@dataclass(frozen=True, slots=True)
class SceneDefinition:
    scene_id: str
    canvas_size: tuple[int, int]
    background: tuple[int, int, int]
    nodes: tuple[SceneNode, ...]
    fit: SceneFit = SceneFit.COVER

    def __post_init__(self) -> None:
        scene_id = self.scene_id.strip()
        if not scene_id:
            raise SceneError("scene_id must not be empty")
        if len(self.canvas_size) != 2:
            raise SceneError("scene canvas_size must contain width/height")
        width, height = self.canvas_size
        if not isinstance(width, int) or not isinstance(height, int):
            raise SceneError("scene canvas dimensions must be integers")
        if not 64 <= width <= 4096 or not 64 <= height <= 4096:
            raise SceneError("scene canvas dimensions must be between 64 and 4096")
        if len(self.background) != 3 or any(
            not isinstance(channel, int) or not 0 <= channel <= 255
            for channel in self.background
        ):
            raise SceneError("scene background must be an RGB integer triplet")
        seen: set[str] = set()
        for node in self.nodes:
            if node.node_id in seen:
                raise SceneError(f"duplicate scene node id: {node.node_id}")
            seen.add(node.node_id)
        # Stable sort preserves author order for equal-z nodes.
        ordered = tuple(sorted(self.nodes, key=lambda node: node.z))
        object.__setattr__(self, "scene_id", scene_id)
        object.__setattr__(self, "nodes", ordered)


@dataclass(frozen=True, slots=True)
class SceneCamera:
    """Camera offset in authoring-canvas pixels."""

    x: float = 0.0
    y: float = 0.0

    def __post_init__(self) -> None:
        if not math.isfinite(self.x) or not math.isfinite(self.y):
            raise SceneError("scene camera coordinates must be finite")

    @classmethod
    def from_pointer(
        cls,
        position: tuple[float, float],
        viewport_size: tuple[int, int],
        *,
        amplitude: tuple[float, float] = (18.0, 10.0),
    ) -> "SceneCamera":
        """Map pointer position to a tiny centered camera offset.

        This is optional enrichment only. Callers without a pointer can keep the
        neutral ``SceneCamera()`` and receive a complete static scene.
        """

        width, height = viewport_size
        if width <= 0 or height <= 0:
            return cls()
        px, py = position
        ax, ay = amplitude
        nx = max(-1.0, min(1.0, (float(px) / width - 0.5) * 2.0))
        ny = max(-1.0, min(1.0, (float(py) / height - 0.5) * 2.0))
        return cls(nx * float(ax), ny * float(ay))


@dataclass(frozen=True, slots=True)
class SceneViewportTransform:
    canvas_size: tuple[int, int]
    viewport_size: tuple[int, int]
    scale: float
    origin: tuple[float, float]

    @classmethod
    def create(
        cls,
        canvas_size: tuple[int, int],
        viewport_size: tuple[int, int],
        fit: SceneFit,
    ) -> "SceneViewportTransform":
        cw, ch = canvas_size
        vw, vh = viewport_size
        if vw <= 0 or vh <= 0:
            raise SceneError("scene viewport dimensions must be positive")
        sx = vw / cw
        sy = vh / ch
        scale = max(sx, sy) if fit is SceneFit.COVER else min(sx, sy)
        rendered_w = cw * scale
        rendered_h = ch * scale
        return cls(
            canvas_size=canvas_size,
            viewport_size=viewport_size,
            scale=scale,
            origin=((vw - rendered_w) / 2.0, (vh - rendered_h) / 2.0),
        )

    def map_rect(
        self,
        rect: tuple[float, float, float, float],
        *,
        offset: tuple[float, float] = (0.0, 0.0),
    ) -> tuple[int, int, int, int]:
        x, y, width, height = rect
        ox, oy = offset
        return (
            int(round(self.origin[0] + (x + ox) * self.scale)),
            int(round(self.origin[1] + (y + oy) * self.scale)),
            max(1, int(round(width * self.scale))),
            max(1, int(round(height * self.scale))),
        )


@dataclass(frozen=True, slots=True)
class SceneNodeSample:
    rect: tuple[int, int, int, int]
    alpha: float


def sample_scene_node(
    node: SceneNode,
    transform: SceneViewportTransform,
    *,
    camera: SceneCamera = SceneCamera(),
    elapsed_seconds: float = 0.0,
    motion_enabled: bool = True,
) -> SceneNodeSample:
    """Resolve parallax + ambient motion for one node at one time sample."""

    if not math.isfinite(elapsed_seconds):
        raise SceneError("elapsed_seconds must be finite")

    dx = -camera.x * node.parallax
    dy = -camera.y * node.parallax
    alpha = node.alpha

    motion = node.motion
    if motion_enabled and motion.kind is not SceneMotionKind.NONE and motion.amplitude:
        angle = math.tau * (elapsed_seconds / motion.period_seconds + motion.phase)
        wave = math.sin(angle)
        if motion.kind in {SceneMotionKind.DRIFT_X, SceneMotionKind.SWAY_X}:
            dx += wave * motion.amplitude
        elif motion.kind is SceneMotionKind.DRIFT_Y:
            dy += wave * motion.amplitude
        elif motion.kind is SceneMotionKind.FLOAT:
            dx += math.cos(angle) * motion.amplitude * 0.35
            dy += wave * motion.amplitude
        elif motion.kind is SceneMotionKind.BREATHE_ALPHA:
            # Range: base_alpha * (1-amplitude) .. base_alpha.
            alpha *= 1.0 - motion.amplitude * (0.5 + 0.5 * wave)

    return SceneNodeSample(
        rect=transform.map_rect(node.rect, offset=(dx, dy)),
        alpha=max(0.0, min(1.0, alpha)),
    )


def load_scene(path: Path) -> SceneDefinition:
    """Load one explicit scene manifest; no directory discovery occurs."""

    with path.open("rb") as handle:
        raw = tomllib.load(handle)
    return parse_scene(raw)


def parse_scene(raw: Mapping[str, object]) -> SceneDefinition:
    scene_id = _text(raw, "scene_id")
    canvas_size = _int_pair(raw.get("canvas"), "canvas")
    fit_raw = raw.get("fit", SceneFit.COVER.value)
    if not isinstance(fit_raw, str):
        raise SceneError("fit must be a string")
    try:
        fit = SceneFit(fit_raw)
    except ValueError as exc:
        raise SceneError(f"unsupported scene fit: {fit_raw!r}") from exc
    background = _rgb(raw.get("background"))

    raw_nodes = raw.get("nodes")
    if not isinstance(raw_nodes, list) or not raw_nodes:
        raise SceneError("scene must define at least one node")
    nodes: list[SceneNode] = []
    for item in raw_nodes:
        if not isinstance(item, dict):
            raise SceneError("invalid scene node entry")
        motion_raw = item.get("motion", SceneMotionKind.NONE.value)
        if not isinstance(motion_raw, str):
            raise SceneError("scene node motion must be a string")
        try:
            motion_kind = SceneMotionKind(motion_raw)
        except ValueError as exc:
            raise SceneError(f"unsupported scene motion: {motion_raw!r}") from exc
        motion = SceneMotion(
            kind=motion_kind,
            amplitude=_number(item.get("motion_amplitude", 0.0), "motion_amplitude"),
            period_seconds=_number(item.get("motion_period", 8.0), "motion_period"),
            phase=_number(item.get("motion_phase", 0.0), "motion_phase"),
        )
        nodes.append(
            SceneNode(
                node_id=_text(item, "id"),
                asset_id=_text(item, "asset"),
                variant=_optional_text(item.get("variant"), "default"),
                rect=_number_quad(item.get("rect"), "rect"),
                z=_integer(item.get("z", 0), "z"),
                parallax=_number(item.get("parallax", 0.0), "parallax"),
                alpha=_number(item.get("alpha", 1.0), "alpha"),
                motion=motion,
                optional=_boolean(item.get("optional", False), "optional"),
            )
        )

    return SceneDefinition(
        scene_id=scene_id,
        canvas_size=canvas_size,
        background=background,
        nodes=tuple(nodes),
        fit=fit,
    )


def _text(raw: Mapping[str, object], key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise SceneError(f"{key} must be a non-empty string")
    return value.strip()


def _optional_text(value: object, default: str) -> str:
    if value is None:
        return default
    if not isinstance(value, str) or not value.strip():
        raise SceneError("optional text value must be a non-empty string")
    return value.strip()


def _integer(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise SceneError(f"{label} must be an integer")
    return value


def _number(value: object, label: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise SceneError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise SceneError(f"{label} must be finite")
    return result


def _boolean(value: object, label: str) -> bool:
    if not isinstance(value, bool):
        raise SceneError(f"{label} must be boolean")
    return value


def _int_pair(value: object, label: str) -> tuple[int, int]:
    if not isinstance(value, list) or len(value) != 2:
        raise SceneError(f"{label} must contain two integers")
    return (_integer(value[0], label), _integer(value[1], label))


def _number_quad(value: object, label: str) -> tuple[float, float, float, float]:
    if not isinstance(value, list) or len(value) != 4:
        raise SceneError(f"{label} must contain four numbers")
    return tuple(_number(item, label) for item in value)  # type: ignore[return-value]


def _rgb(value: object) -> tuple[int, int, int]:
    if not isinstance(value, list) or len(value) != 3:
        raise SceneError("background must contain three integers")
    result = tuple(_integer(item, "background") for item in value)
    if any(not 0 <= channel <= 255 for channel in result):
        raise SceneError("background channels must be between 0 and 255")
    return result  # type: ignore[return-value]
