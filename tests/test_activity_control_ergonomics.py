"""Mouse-first control clusters and the keyboard hint (ADR 0037 §4a/§4b)."""

from __future__ import annotations

import os
from pathlib import Path
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from greia_platform.activity_controls import (
    ClusterAnchor,
    ClusterShape,
    ControlKit,
    ControlLayout,
    ControlTheme,
)
from greia_platform.activity_keyboard_hint import KeyboardHint, KeyCap
from greia_platform.input_core import (
    InputEdge,
    InputSource,
    PhysicalControl,
    SemanticAction,
    SemanticInputEvent,
)
from greia_platform.pygame_canvas import PygameReferenceCanvas

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "assets" / "visual" / "runtime" / "v1"
VIEWPORTS = ((1024, 600), (800, 480))
KEYCAPS = ("arrow_up", "arrow_down", "arrow_left", "arrow_right", "space", "enter")


class _Typography:
    def render(self, text, role, size, color):
        return pygame.Surface((max(1, len(str(text)) * size // 2), size + 4), pygame.SRCALPHA)


def _resolver(asset_id: str, variant: str) -> Path:
    if asset_id.startswith("ui.keycap."):
        name = asset_id.rsplit(".", 1)[1]
        return RUNTIME / "ui" / "keycaps" / (f"{name}_lit.png" if variant == "lit" else f"{name}.png")
    raise KeyError(asset_id)


class _Clock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


def _layouts():
    for width, height in VIEWPORTS:
        canvas = PygameReferenceCanvas(pygame.Surface((width, height)))
        yield (width, height), ControlLayout.for_canvas(canvas, (width, height))
        yield (width, height), ControlLayout.for_surface(width, height)


class ClusterLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((1024, 600))

    def _assert_cluster(self, layout: ControlLayout, cluster, count: int) -> None:
        area = pygame.Rect(0, 0, layout.width, layout.height)
        self.assertEqual(len(cluster.rects), count)
        for rect in cluster.rects + ((cluster.hint,) if cluster.hint is not None else ()):
            self.assertTrue(area.contains(rect), (rect, area))
            self.assertFalse(rect.colliderect(layout.protected), (rect, layout.protected))
            self.assertGreaterEqual(rect.left, layout.margin)
            self.assertLessEqual(rect.bottom, layout.height - layout.margin)
        for index, rect in enumerate(cluster.rects):
            for other in cluster.rects[index + 1:]:
                self.assertFalse(rect.colliderect(other), (rect, other))
            # touch is supported by size: the physical touch floor holds.
            self.assertGreaterEqual(min(rect.size) * layout.scale, ControlLayout.MIN_TOUCH_PHYSICAL - 1)
        if cluster.hint is not None:
            for rect in cluster.rects:
                self.assertFalse(rect.colliderect(cluster.hint))

    def test_row_cluster_is_compact_and_inside_bounds_at_both_resolutions(self) -> None:
        for viewport, layout in _layouts():
            for anchor in ClusterAnchor:
                with self.subTest(viewport=viewport, anchor=anchor, scale=layout.scale):
                    cluster = layout.cluster([(120, 120), (120, 120)], anchor=anchor, hint_size=(160, 96))
                    self._assert_cluster(layout, cluster, 2)
                    narrowest = min(rect.width for rect in cluster.rects)
                    # adjacent: edge gap at most one button width (rule: <= 1-2 widths)
                    self.assertLessEqual(cluster.max_gap, narrowest)
                    first, second = cluster.rects
                    self.assertEqual(first.centery, second.centery)
                    # the whole group sits in the bottom half, not split across the screen
                    self.assertGreater(cluster.bounds.top, layout.height // 2)
                    self.assertLess(cluster.bounds.width, layout.width // 2)
                    if anchor is ClusterAnchor.BOTTOM_RIGHT:
                        self.assertEqual(cluster.bounds.right, layout.width - layout.margin)
                        self.assertLess(cluster.hint.right, cluster.bounds.left)
                    else:
                        group = cluster.bounds.union(cluster.hint)
                        self.assertLessEqual(abs(group.centerx - layout.width // 2), 2)

    def test_cross_cluster_forms_a_dpad(self) -> None:
        for viewport, layout in _layouts():
            with self.subTest(viewport=viewport, scale=layout.scale):
                cluster = layout.cluster([(72, 72)] * 4, shape=ClusterShape.CROSS)
                self._assert_cluster(layout, cluster, 4)
                up, left, right, down = cluster.rects
                self.assertEqual(up.centerx, down.centerx)
                self.assertEqual(left.centery, right.centery)
                self.assertLess(up.bottom, left.top + 1)
                self.assertLessEqual(cluster.max_gap, cluster.rects[0].width * 2)

    def test_gap_is_clamped_to_one_button_width(self) -> None:
        layout = ControlLayout.for_surface(1024, 600)
        cluster = layout.cluster([(64, 64), (64, 64), (64, 64)], gap=400)
        self.assertLessEqual(cluster.gap, 64)
        self.assertLessEqual(cluster.max_gap, 64)

    def test_oversized_cluster_shrinks_but_keeps_touch_floor(self) -> None:
        layout = ControlLayout.for_surface(800, 480)
        cluster = layout.cluster([(300, 200)] * 4, hint_size=(200, 96))
        self._assert_cluster(layout, cluster, 4)

    def test_cross_rejects_wrong_count(self) -> None:
        with self.assertRaises(ValueError):
            ControlLayout.for_surface(1024, 600).cluster([(64, 64)] * 3, shape="cross")


class KeyboardHintTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((1024, 600))

    def setUp(self) -> None:
        self.clock = _Clock()
        self.kit = ControlKit(_Typography(), ControlTheme.for_accent("leaf"), resolver=_resolver)

    def _hint(self, active, size=None):
        size = size or KeyboardHint.preferred_size(active, key=44)
        return self.kit.keyboard_hint(
            "keys", pygame.Rect((600, 480), size), active=active, clock=self.clock, lit_hold=0.2, show_seconds=5.0
        )

    def test_keycap_art_is_catalogued_with_default_and_lit(self) -> None:
        import tomllib

        catalogue = tomllib.loads((ROOT / "assets" / "catalog" / "shared_visuals_v1.toml").read_text())
        visuals = {entry["id"]: entry for entry in catalogue["visuals"]}
        for name in KEYCAPS:
            entry = visuals[f"ui.keycap.{name}"]
            self.assertEqual(set(entry["variants"]), {"default", "lit"})
            for path in entry["variants"].values():
                self.assertTrue((ROOT / "assets" / path).is_file(), path)

    def test_arrow_cluster_is_drawn_whole_and_non_acting_arrows_dim(self) -> None:
        hint = self._hint({KeyCap.LEFT, KeyCap.RIGHT, KeyCap.SPACE})
        rects = hint.key_rects()
        self.assertEqual(set(rects), {KeyCap.UP, KeyCap.DOWN, KeyCap.LEFT, KeyCap.RIGHT, KeyCap.SPACE})
        area = pygame.Rect((0, 0), hint.rect.size)
        for cap, rect in rects.items():
            self.assertTrue(area.contains(rect), (cap, rect))
        self.assertLess(rects[KeyCap.UP].bottom, rects[KeyCap.DOWN].top + 1)
        self.assertEqual(rects[KeyCap.UP].centerx, rects[KeyCap.DOWN].centerx)
        self.assertGreater(rects[KeyCap.SPACE].width, rects[KeyCap.LEFT].width * 2)
        hint.show()
        surface = hint.render()
        up = rects[KeyCap.UP]
        left = rects[KeyCap.LEFT]
        dim_alpha = surface.get_at(up.center).a
        full_alpha = surface.get_at(left.center).a
        self.assertLess(dim_alpha, full_alpha)

    def test_space_only_hint_has_no_arrows(self) -> None:
        self.assertEqual(KeyboardHint.drawn_keys({KeyCap.SPACE}), (KeyCap.SPACE,))
        width, height = KeyboardHint.preferred_size({KeyCap.SPACE}, key=40)
        self.assertEqual(height, 40)
        self.assertEqual(width, 100)

    def test_real_key_lights_the_drawn_key_and_reveals_the_hint(self) -> None:
        hint = self._hint({KeyCap.LEFT, KeyCap.RIGHT, KeyCap.SPACE})
        self.assertFalse(hint.visible)
        down = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_LEFT)
        self.assertTrue(hint.observe_event(down))
        self.assertTrue(hint.visible)
        self.assertEqual(hint.lit, {KeyCap.LEFT})
        self.clock.now += 1.0
        self.assertEqual(hint.lit, {KeyCap.LEFT}, "held keys stay lit")
        self.assertTrue(hint.observe_event(pygame.event.Event(pygame.KEYUP, key=pygame.K_LEFT)))
        self.assertEqual(hint.lit, frozenset())

    def test_quick_tap_stays_lit_for_the_hold_time(self) -> None:
        hint = self._hint({KeyCap.SPACE})
        hint.observe(PhysicalControl.KEY_SPACE, InputEdge.PRESSED)
        hint.observe(PhysicalControl.KEY_SPACE, InputEdge.RELEASED)
        self.assertEqual(hint.lit, {KeyCap.SPACE})
        self.assertTrue(hint.animating)
        deadline = hint.deadline()
        self.assertAlmostEqual(deadline, self.clock.now + 0.2)
        self.clock.now = deadline + 0.01
        self.assertTrue(hint.update())
        self.assertEqual(hint.lit, frozenset())
        self.assertFalse(hint.animating)

    def test_non_acting_and_unrelated_keys_do_not_light(self) -> None:
        hint = self._hint({KeyCap.LEFT, KeyCap.RIGHT})
        self.assertFalse(hint.observe(PhysicalControl.KEY_UP, InputEdge.PRESSED))
        self.assertFalse(hint.observe_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a)))
        self.assertFalse(hint.observe_event(pygame.event.Event(pygame.MOUSEMOTION, pos=(1, 1), rel=(1, 1), buttons=(0, 0, 0))))
        self.assertEqual(hint.lit, frozenset())
        self.assertFalse(hint.visible)

    def test_controller_and_semantic_inputs_light_the_same_keys(self) -> None:
        hint = self._hint({KeyCap.UP, KeyCap.DOWN, KeyCap.LEFT, KeyCap.RIGHT, KeyCap.SPACE})
        hint.observe(PhysicalControl.CONTROLLER_DPAD_RIGHT, InputEdge.PRESSED)
        hint.observe(PhysicalControl.CONTROLLER_FACE_SOUTH, InputEdge.PRESSED)
        self.assertEqual(hint.lit, {KeyCap.RIGHT, KeyCap.SPACE})
        hint.observe_semantic(SemanticInputEvent(SemanticAction.MOVE_UP, InputEdge.PRESSED, InputSource.KEYBOARD))
        self.assertIn(KeyCap.UP, hint.lit)
        hint.observe_semantic(SemanticInputEvent(SemanticAction.ACTIVATE, InputEdge.PRESSED, InputSource.KEYBOARD))
        self.assertIn(KeyCap.SPACE, hint.lit)

    def test_show_times_out_and_pinned_show_stays(self) -> None:
        hint = self._hint({KeyCap.SPACE})
        hint.show(3.0)
        self.assertTrue(hint.visible)
        self.assertTrue(hint.update(), "showing is a visible change the loop must draw")
        self.assertAlmostEqual(hint.deadline(), self.clock.now + 3.0)
        self.clock.now += 3.01
        self.assertTrue(hint.update())
        self.assertFalse(hint.visible)
        hint.show()
        self.assertTrue(hint.update())
        self.clock.now += 100
        self.assertFalse(hint.update())
        self.assertTrue(hint.visible)
        hint.hide()
        self.assertFalse(hint.visible)

    def test_held_key_keeps_the_hint_up_without_a_spinning_deadline(self) -> None:
        hint = self._hint({KeyCap.RIGHT})
        hint.observe(PhysicalControl.KEY_RIGHT, InputEdge.PRESSED)
        self.clock.now += 30.0  # holding the arrow to steer
        hint.update()
        self.assertTrue(hint.visible)
        self.assertIsNone(hint.deadline(), "no past deadline while the key is held")
        hint.observe(PhysicalControl.KEY_RIGHT, InputEdge.RELEASED)
        self.assertGreaterEqual(hint.deadline(), self.clock.now)
        hint.update()
        self.assertFalse(hint.visible)

    def test_demonstration_lights_each_acting_key_in_turn(self) -> None:
        hint = self._hint({KeyCap.LEFT, KeyCap.RIGHT, KeyCap.SPACE})
        hint.demonstrate()
        self.assertTrue(hint.visible)
        seen = []
        for _ in range(3):
            seen.append(hint.lit)
            self.clock.now += hint.demo_step
            hint.update()
        self.assertEqual(seen, [{KeyCap.LEFT}, {KeyCap.RIGHT}, {KeyCap.SPACE}])
        self.assertEqual(hint.lit, frozenset())

    def test_draw_is_cached_blits_per_lit_state(self) -> None:
        hint = self._hint({KeyCap.LEFT, KeyCap.RIGHT, KeyCap.SPACE})
        hint.show()
        target = pygame.Surface((1024, 600), pygame.SRCALPHA)
        hint.draw(target)
        first = hint.render()
        hint.draw(target)
        self.assertIs(hint.render(), first, "same look -> same cached composite")
        hint.observe(PhysicalControl.KEY_LEFT, InputEdge.PRESSED)
        lit = hint.render()
        self.assertIsNot(lit, first)
        hint.observe(PhysicalControl.KEY_LEFT, InputEdge.RELEASED)
        self.clock.now += 1
        hint.update()
        self.assertIs(hint.render(), first)
        # the lit keycap differs visibly from the resting one at its centre
        left = hint.key_rects()[KeyCap.LEFT]
        self.assertNotEqual(lit.get_at((left.centerx, left.top + 8)), first.get_at((left.centerx, left.top + 8)))

    def test_missing_art_falls_back_to_vector_keycaps(self) -> None:
        def missing(asset_id: str, variant: str) -> Path:
            raise KeyError(asset_id)

        kit = ControlKit(_Typography(), ControlTheme(), resolver=missing)
        active = {KeyCap.UP, KeyCap.DOWN, KeyCap.LEFT, KeyCap.RIGHT, KeyCap.SPACE, KeyCap.ENTER}
        hint = kit.keyboard_hint("keys", pygame.Rect((0, 0), KeyboardHint.preferred_size(active, key=40)), active=active, visible=True)
        hint.observe(PhysicalControl.KEY_ENTER, InputEdge.PRESSED)
        surface = hint.render()
        self.assertEqual(surface.get_size(), hint.rect.size)

    def test_hint_requires_an_acting_key(self) -> None:
        with self.assertRaises(ValueError):
            self._hint(set(), size=(100, 40))


if __name__ == "__main__":
    unittest.main()
