"""Pygame adapter for Greia's renderer-neutral scene composition model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .assets import AssetCatalogueError
from .pygame_visual_assets import PygameVisualSurfaceCache, VisualSurfaceCacheError
from .scene import (
    SceneCamera,
    SceneDefinition,
    SceneViewportTransform,
    sample_scene_node,
)


class SceneRenderError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class SceneRenderStats:
    drawn_nodes: int
    culled_nodes: int
    skipped_optional_nodes: int


class PygameSceneRenderer:
    """Draw explicit semantic scene nodes through the shared bounded cache.

    The renderer does not discover assets and does not rasterize source SVGs.
    Each scene node resolves through ``PygameVisualSurfaceCache``. Optional node
    failures are isolated and remembered for the renderer lifetime so a corrupt
    decorative PNG does not trigger repeated disk decode/exception work every
    frame. Required-node failures abort the scene draw so the Activity can retain
    its own deliberate static/private fallback.
    """

    def __init__(
        self,
        visual_cache: PygameVisualSurfaceCache[Any],
        *,
        pygame_module: Any | None = None,
    ) -> None:
        self.visual_cache = visual_cache
        if pygame_module is None:
            import pygame as pygame_module
        self._pygame = pygame_module
        self._failed_optional: set[tuple[str, str, int, int]] = set()

    @classmethod
    def for_activity(
        cls,
        *,
        max_entries: int = 24,
        max_surface_pixels: int = 1920 * 1080,
        pygame_module: Any | None = None,
    ) -> "PygameSceneRenderer":
        """Create one renderer against Greia's Activity-visible catalogue.

        This is an internal Pygame realization of the existing semantic Activity
        visual contract. Activities still request scene asset IDs; they do not
        scan source folders or supply host paths. The import is local to avoid a
        module-level cycle with ``activity_api``.
        """

        from .activity_api import _catalogue

        cache = PygameVisualSurfaceCache.for_pygame(
            _catalogue(),
            max_entries=max_entries,
            max_surface_pixels=max_surface_pixels,
        )
        return cls(cache, pygame_module=pygame_module)

    def clear(self) -> None:
        self.visual_cache.clear()
        self._failed_optional.clear()

    def draw(
        self,
        scene: SceneDefinition,
        target: Any,
        *,
        elapsed_seconds: float = 0.0,
        camera: SceneCamera = SceneCamera(),
        motion_enabled: bool = True,
        clear: bool = True,
        min_z: int | None = None,
        max_z: int | None = None,
    ) -> SceneRenderStats:
        if clear:
            target.fill(scene.background)

        transform = SceneViewportTransform.create(
            scene.canvas_size,
            target.get_size(),
            scene.fit,
        )
        target_rect = target.get_rect()
        drawn = 0
        culled = 0
        skipped = 0

        cache_error_types: list[type[BaseException]] = [
            VisualSurfaceCacheError,
            AssetCatalogueError,
            KeyError,
            FileNotFoundError,
            OSError,
            ValueError,
        ]
        if isinstance(getattr(self._pygame, "error", None), type) and issubclass(
            self._pygame.error, BaseException
        ):
            cache_error_types.append(self._pygame.error)
        cache_errors = tuple(cache_error_types)

        for node in scene.nodes:
            if min_z is not None and node.z < min_z:
                continue
            if max_z is not None and node.z > max_z:
                continue

            sample = sample_scene_node(
                node,
                transform,
                camera=camera,
                elapsed_seconds=elapsed_seconds,
                motion_enabled=motion_enabled,
            )
            rect = self._pygame.Rect(sample.rect)
            if not rect.colliderect(target_rect):
                culled += 1
                continue

            optional_failure_key = (
                node.asset_id,
                node.variant,
                rect.width,
                rect.height,
            )
            if node.optional and optional_failure_key in self._failed_optional:
                skipped += 1
                continue

            try:
                surface = self.visual_cache.get(
                    node.asset_id,
                    variant=node.variant,
                    size=rect.size,
                )
            except cache_errors as exc:
                surface = None
                fallback_variant = getattr(node, "fallback_variant", None)
                if fallback_variant and fallback_variant != node.variant:
                    try:
                        surface = self.visual_cache.get(
                            node.asset_id,
                            variant=fallback_variant,
                            size=rect.size,
                        )
                    except cache_errors:
                        surface = None

                if surface is None:
                    if node.optional:
                        self._failed_optional.add(optional_failure_key)
                        skipped += 1
                        continue
                    raise SceneRenderError(
                        f"required scene visual failed: {scene.scene_id}/{node.node_id} "
                        f"({node.asset_id}/{node.variant})"
                    ) from exc

            previous_alpha = None
            alpha_changed = sample.alpha < 0.999
            if alpha_changed:
                previous_alpha = surface.get_alpha()
                surface.set_alpha(max(0, min(255, int(round(sample.alpha * 255.0)))))
            try:
                target.blit(surface, rect)
            finally:
                if alpha_changed:
                    surface.set_alpha(previous_alpha)
            drawn += 1

        return SceneRenderStats(
            drawn_nodes=drawn,
            culled_nodes=culled,
            skipped_optional_nodes=skipped,
        )
