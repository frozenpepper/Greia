from __future__ import annotations

import unittest

from greia_platform.pygame_scene import PygameSceneRenderer, SceneRenderError
from greia_platform.scene import (
    SceneCamera,
    SceneDefinition,
    SceneFit,
    SceneMotion,
    SceneMotionKind,
    SceneNode,
    SceneViewportTransform,
    parse_scene,
    sample_scene_node,
)


class SceneModelTests(unittest.TestCase):
    def test_cover_transform_preserves_canvas_aspect_and_crops_edges(self) -> None:
        transform = SceneViewportTransform.create((1024, 600), (800, 600), SceneFit.COVER)
        self.assertAlmostEqual(transform.scale, 1.0)
        self.assertEqual(transform.map_rect((112, 0, 800, 600)), (0, 0, 800, 600))

    def test_contain_transform_centers_scene(self) -> None:
        transform = SceneViewportTransform.create((1024, 600), (1920, 1080), SceneFit.CONTAIN)
        self.assertAlmostEqual(transform.scale, 1.8)
        x, y, width, height = transform.map_rect((0, 0, 1024, 600))
        self.assertEqual((width, height), (1843, 1080))
        self.assertEqual(y, 0)
        self.assertGreater(x, 0)

    def test_parallax_and_motion_are_deterministic_and_static_can_disable_motion(self) -> None:
        node = SceneNode(
            "cloud",
            "cloud.large.01",
            (100, 40, 320, 128),
            parallax=0.5,
            motion=SceneMotion(SceneMotionKind.DRIFT_X, 20, 10, 0.0),
        )
        transform = SceneViewportTransform.create((1024, 600), (1024, 600), SceneFit.COVER)
        static = sample_scene_node(
            node,
            transform,
            camera=SceneCamera(10, 0),
            elapsed_seconds=2.5,
            motion_enabled=False,
        )
        animated = sample_scene_node(
            node,
            transform,
            camera=SceneCamera(10, 0),
            elapsed_seconds=2.5,
            motion_enabled=True,
        )
        self.assertEqual(static.rect[0], 95)
        self.assertEqual(animated.rect[0], 115)
        self.assertEqual(static.rect[1:], animated.rect[1:])

    def test_alpha_breathe_never_exceeds_authored_alpha(self) -> None:
        node = SceneNode(
            "light",
            "atmosphere.sunlight_rays.01",
            (0, 0, 1024, 512),
            alpha=0.4,
            motion=SceneMotion(SceneMotionKind.BREATHE_ALPHA, 0.25, 8.0, 0.0),
        )
        transform = SceneViewportTransform.create((1024, 600), (1024, 600), SceneFit.COVER)
        samples = [
            sample_scene_node(node, transform, elapsed_seconds=value).alpha
            for value in (0.0, 2.0, 4.0, 6.0)
        ]
        self.assertTrue(all(0.3 <= value <= 0.4 for value in samples))

    def test_parser_sorts_by_z_but_preserves_equal_z_author_order(self) -> None:
        scene = parse_scene(
            {
                "scene_id": "test",
                "canvas": [1024, 600],
                "fit": "cover",
                "background": [1, 2, 3],
                "nodes": [
                    {"id": "b", "asset": "b", "rect": [0, 0, 10, 10], "z": 20},
                    {"id": "a", "asset": "a", "rect": [0, 0, 10, 10], "z": 10},
                    {"id": "c", "asset": "c", "rect": [0, 0, 10, 10], "z": 20},
                ],
            }
        )
        self.assertEqual(tuple(node.node_id for node in scene.nodes), ("a", "b", "c"))

    def test_duplicate_node_ids_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicate scene node"):
            SceneDefinition(
                "test",
                (1024, 600),
                (0, 0, 0),
                (
                    SceneNode("same", "a", (0, 0, 10, 10)),
                    SceneNode("same", "b", (0, 0, 10, 10)),
                ),
            )

    def test_pointer_camera_is_center_neutral_and_bounded(self) -> None:
        self.assertEqual(SceneCamera.from_pointer((500, 300), (1000, 600)), SceneCamera())
        camera = SceneCamera.from_pointer((1000, 600), (1000, 600), amplitude=(20, 12))
        self.assertEqual(camera, SceneCamera(20, 12))


class _FakeRect:
    def __init__(self, value: tuple[int, int, int, int]) -> None:
        self.x, self.y, self.width, self.height = value

    @property
    def size(self) -> tuple[int, int]:
        return (self.width, self.height)

    def colliderect(self, other: "_FakeRect") -> bool:
        return not (
            self.x + self.width <= other.x
            or other.x + other.width <= self.x
            or self.y + self.height <= other.y
            or other.y + other.height <= self.y
        )


class _FakePygame:
    error = RuntimeError

    @staticmethod
    def Rect(value: tuple[int, int, int, int]) -> _FakeRect:
        return _FakeRect(value)


class _FakeSurface:
    def __init__(self) -> None:
        self.alpha = None

    def get_alpha(self):
        return self.alpha

    def set_alpha(self, value) -> None:
        self.alpha = value


class _FakeTarget:
    def __init__(self, size: tuple[int, int] = (1024, 600)) -> None:
        self.size = size
        self.fills: list[tuple[int, int, int]] = []
        self.blits: list[tuple[object, _FakeRect]] = []

    def fill(self, color: tuple[int, int, int]) -> None:
        self.fills.append(color)

    def get_size(self) -> tuple[int, int]:
        return self.size

    def get_rect(self) -> _FakeRect:
        return _FakeRect((0, 0, *self.size))

    def blit(self, surface: object, rect: _FakeRect) -> None:
        self.blits.append((surface, rect))


class _FakeCache:
    def __init__(self, failures: set[str] | None = None) -> None:
        self.failures = failures or set()
        self.calls: list[tuple[str, str, tuple[int, int]]] = []
        self.surface = _FakeSurface()
        self.clear_count = 0

    def get(self, asset_id: str, *, variant: str, size: tuple[int, int]):
        self.calls.append((asset_id, variant, size))
        if asset_id in self.failures:
            raise ValueError("broken")
        return self.surface

    def clear(self) -> None:
        self.clear_count += 1


class PygameSceneRendererTests(unittest.TestCase):
    def _scene(self, *, optional: bool = False) -> SceneDefinition:
        return SceneDefinition(
            "render",
            (1024, 600),
            (10, 20, 30),
            (
                SceneNode(
                    "node",
                    "asset",
                    (100, 100, 200, 100),
                    alpha=0.5,
                    optional=optional,
                ),
            ),
        )

    def test_renderer_uses_semantic_cache_and_restores_surface_alpha(self) -> None:
        cache = _FakeCache()
        target = _FakeTarget()
        renderer = PygameSceneRenderer(cache, pygame_module=_FakePygame)
        stats = renderer.draw(self._scene(), target)
        self.assertEqual(target.fills, [(10, 20, 30)])
        self.assertEqual(cache.calls, [("asset", "default", (200, 100))])
        self.assertEqual(len(target.blits), 1)
        self.assertIsNone(cache.surface.alpha)
        self.assertEqual(stats.drawn_nodes, 1)

    def test_optional_asset_failure_is_isolated_and_not_retried_every_frame(self) -> None:
        cache = _FakeCache({"asset"})
        renderer = PygameSceneRenderer(cache, pygame_module=_FakePygame)
        first = renderer.draw(self._scene(optional=True), _FakeTarget())
        second = renderer.draw(self._scene(optional=True), _FakeTarget())
        self.assertEqual(first.skipped_optional_nodes, 1)
        self.assertEqual(second.skipped_optional_nodes, 1)
        self.assertEqual(first.drawn_nodes, 0)
        self.assertEqual(second.drawn_nodes, 0)
        self.assertEqual(cache.calls, [("asset", "default", (200, 100))])

    def test_clear_allows_optional_asset_retry_after_explicit_invalidation(self) -> None:
        cache = _FakeCache({"asset"})
        renderer = PygameSceneRenderer(cache, pygame_module=_FakePygame)
        renderer.draw(self._scene(optional=True), _FakeTarget())
        renderer.clear()
        renderer.draw(self._scene(optional=True), _FakeTarget())
        self.assertEqual(len(cache.calls), 2)
        self.assertEqual(cache.clear_count, 1)

    def test_required_asset_failure_aborts_scene(self) -> None:
        renderer = PygameSceneRenderer(_FakeCache({"asset"}), pygame_module=_FakePygame)
        with self.assertRaises(SceneRenderError):
            renderer.draw(self._scene(optional=False), _FakeTarget())


if __name__ == "__main__":
    unittest.main()
