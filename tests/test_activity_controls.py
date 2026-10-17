"""Shared Activity control kit (ADR 0037): focus, hit-testing, caching, layout."""

from __future__ import annotations

import os
from pathlib import Path
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from greia_platform.activity_controls import (
    Align,
    BodyShape,
    ButtonRole,
    ControlArt,
    ControlKit,
    ControlLayout,
    ControlPainter,
    ControlTheme,
    ExternalTarget,
    KitPointer,
    PointerPhase,
    PygameControlInput,
    spatial_neighbour,
)
from greia_platform.activity_feedback import CastFeedback, CastPose
from greia_platform.input_core import InputEdge, InputSource, SemanticAction, SemanticInputEvent
from greia_platform.pygame_canvas import PygameReferenceCanvas
from greia_platform.pygame_completion import (
    CompletionAction,
    CompletionContent,
    CompletionOverlay,
    CompletionScene,
    PygameCompletionScreen,
)
from greia_platform.system_chrome import ActivitySystemChromeLayout
from greia_platform.ui_core import Screen, SurfaceNavigator, UiEventResult

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "assets" / "visual" / "runtime" / "v1"
VIEWPORTS = ((1024, 600), (800, 480), (480, 320), (1280, 800))


class CountingTypography:
    def __init__(self) -> None:
        self.calls = 0

    def render(self, text, role, size, color):
        self.calls += 1
        return pygame.Surface((max(1, len(str(text)) * size // 2), size + 4), pygame.SRCALPHA)


def _press(action: SemanticAction) -> SemanticInputEvent:
    return SemanticInputEvent(action, InputEdge.PRESSED, InputSource.KEYBOARD)


def _repo_resolver(asset_id: str, variant: str) -> Path:
    """Resolve kit art straight from generated renditions (no catalogue IO)."""

    if asset_id.startswith("character."):
        name = asset_id.split(".", 1)[1]
        stem = "neutral" if variant == "default" else variant
        return RUNTIME / "characters" / f"{name}_{stem}.png"
    if asset_id.startswith("icon.hud."):
        return RUNTIME / "ui" / "controls" / f"hud_{asset_id.rsplit('.', 1)[1]}.png"
    if asset_id == "ui.control.star":
        return RUNTIME / "ui" / "controls" / ("star.png" if variant == "default" else "star_off.png")
    if asset_id == "ui.completion.card":
        return RUNTIME / "ui" / "controls" / "completion_card.png"
    raise KeyError(asset_id)


class _KitTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((1024, 600))

    def setUp(self) -> None:
        self.typography = CountingTypography()
        self.kit = ControlKit(self.typography, ControlTheme.for_accent("orange"), resolver=_repo_resolver)
        self.activated: list[str] = []

    def _button(self, control_id: str, rect, **kwargs):
        return self.kit.pill_button(
            control_id,
            pygame.Rect(rect),
            label=control_id.upper(),
            on_activate=lambda cid=control_id: self.activated.append(cid),
            **kwargs,
        )


class SpatialFocusTests(_KitTestCase):
    def _grid_layer(self):
        buttons = [
            self._button(f"b{row}{col}", (100 + col * 200, 100 + row * 120, 160, 70))
            for row in range(2)
            for col in range(3)
        ]
        return self.kit.layer(buttons, initial_focus="b00"), buttons

    def test_arrows_move_to_nearest_aligned_neighbour_without_wrap(self) -> None:
        layer, _ = self._grid_layer()
        for action, expected in (
            (SemanticAction.NAV_RIGHT, "b01"),
            (SemanticAction.NAV_RIGHT, "b02"),
            (SemanticAction.NAV_RIGHT, "b02"),
            (SemanticAction.NAV_DOWN, "b12"),
            (SemanticAction.NAV_LEFT, "b11"),
            (SemanticAction.NAV_UP, "b01"),
            (SemanticAction.NAV_UP, "b01"),
        ):
            self.assertIs(layer.handle_event(_press(action)), UiEventResult.HANDLED)
            self.assertEqual(layer.focused_id, expected, action)
        self.assertTrue(layer.focus_visible)

    def test_disabled_invisible_and_display_only_targets_are_skipped(self) -> None:
        layer, buttons = self._grid_layer()
        buttons[1].enabled = False
        buttons[2].visible = False
        chip = self.kit.hud_chip("chip", pygame.Rect(700, 100, 120, 60), icon=None, value=3)
        layer.set_targets([*buttons, chip])
        layer.focus("b00")
        # Nothing focusable remains to the right in the row: the nearest
        # diagonal candidate in that direction is used instead of getting stuck.
        layer.handle_event(_press(SemanticAction.NAV_RIGHT))
        self.assertEqual(layer.focused_id, "b11")
        layer.handle_event(_press(SemanticAction.NAV_RIGHT))
        self.assertEqual(layer.focused_id, "b12")
        layer.handle_event(_press(SemanticAction.NAV_UP))
        self.assertEqual(layer.focused_id, "b00")
        self.assertFalse(layer.focus("chip"))
        self.assertFalse(layer.focus("b01"))

    def test_external_targets_join_traversal_and_activation(self) -> None:
        rooms = [
            ExternalTarget(f"room.{i}", pygame.Rect(100 + i * 110, 100, 98, 98), lambda i=i: self.activated.append(f"room{i}"))
            for i in range(3)
        ]
        ok = self._button("ok", (160, 260, 200, 80))
        layer = self.kit.layer([*rooms, ok], initial_focus="room.0")
        layer.handle_event(_press(SemanticAction.NAV_DOWN))
        self.assertEqual(layer.focused_id, "ok")
        layer.handle_event(_press(SemanticAction.NAV_UP))
        self.assertEqual(layer.focused_id, "room.1")
        layer.handle_event(_press(SemanticAction.ACTIVATE))
        self.assertEqual(self.activated, ["room1"])
        rooms[1].enabled = False
        layer.ensure_focus()
        self.assertNotEqual(layer.focused_id, "room.1")

    def test_spatial_neighbour_prefers_aligned_candidates(self) -> None:
        current = pygame.Rect(0, 0, 100, 50)
        candidates = [("diagonal", pygame.Rect(150, 200, 100, 50)), ("aligned", pygame.Rect(400, 10, 100, 50))]
        self.assertEqual(spatial_neighbour(current, candidates, (1, 0)), "aligned")
        self.assertIsNone(spatial_neighbour(current, candidates, (-1, 0)))


class PointerHitTests(_KitTestCase):
    def test_tap_activates_and_release_elsewhere_cancels(self) -> None:
        a = self._button("a", (100, 100, 200, 80))
        b = self._button("b", (500, 100, 200, 80))
        layer = self.kit.layer([a, b])
        self.assertTrue(layer.tap((150, 140)))
        self.assertEqual(self.activated, ["a"])
        self.assertIs(layer.handle_event(KitPointer(PointerPhase.DOWN, (150, 140))), UiEventResult.HANDLED)
        self.assertTrue(a.pressed)
        layer.handle_event(KitPointer(PointerPhase.UP, (600, 140)))
        self.assertEqual(self.activated, ["a"])
        self.assertFalse(a.pressed)
        # Small finger drift (inside the tap slop) still counts.
        layer.handle_event(KitPointer(PointerPhase.DOWN, (290, 140)))
        layer.handle_event(KitPointer(PointerPhase.UP, (305, 140)))
        self.assertEqual(self.activated, ["a", "a"])

    def test_misses_disabled_round_corners_and_displays_are_ignored(self) -> None:
        disabled = self._button("off", (100, 300, 200, 80), enabled=False)
        round_button = self.kit.icon_button("round", pygame.Rect(500, 300, 100, 100), icon=None, on_activate=lambda: self.activated.append("round"))
        chip = self.kit.hud_chip("chip", pygame.Rect(700, 300, 120, 60), icon=None, value=1)
        layer = self.kit.layer([disabled, round_button, chip])
        self.assertIs(layer.handle_event(KitPointer(PointerPhase.DOWN, (50, 50))), UiEventResult.IGNORED)
        self.assertFalse(layer.tap((150, 340)))
        self.assertFalse(layer.tap((501, 301)))
        self.assertFalse(layer.tap((760, 330)))
        self.assertTrue(layer.tap((550, 345)))
        self.assertEqual(self.activated, ["round"])

    def test_hover_moves_invalidate_once(self) -> None:
        a = self._button("a", (100, 100, 200, 80))
        layer = self.kit.layer([a])
        layer.invalidation.mark_drawn()
        self.assertIs(layer.handle_event(KitPointer(PointerPhase.MOVE, (150, 140))), UiEventResult.HANDLED)
        self.assertTrue(a.hovered)
        self.assertTrue(layer.invalidation.should_draw)
        layer.invalidation.mark_drawn()
        self.assertIs(layer.handle_event(KitPointer(PointerPhase.MOVE, (160, 140))), UiEventResult.IGNORED)
        self.assertFalse(layer.invalidation.should_draw)

    def test_tool_strip_keeps_exactly_one_selection(self) -> None:
        chosen: list[str] = []
        strip = self.kit.tool_strip(
            "mode",
            [("a", "A", None), ("b", "B", None), ("c", "C", None)],
            rects=[pygame.Rect(100 + i * 150, 20, 140, 60) for i in range(3)],
            on_select=chosen.append,
        )
        layer = self.kit.layer(strip.controls)
        self.assertEqual(strip.selected, "a")
        layer.tap((420, 50))
        self.assertEqual((strip.selected, chosen), ("c", ["c"]))
        self.assertEqual([slot.selected for slot in strip.slots], [False, False, True])
        with self.assertRaises(ValueError):
            strip.select("zzz")


class CachedRenderingTests(_KitTestCase):
    def test_repeated_draw_reuses_cached_surfaces_and_text(self) -> None:
        a = self._button("a", (100, 100, 200, 80), role=ButtonRole.PRIMARY)
        chip = self.kit.hud_chip("chip", pygame.Rect(400, 100, 140, 60), icon=self.kit.star(36), value=7)
        dots = self.kit.progress_dots("dots", pygame.Rect(600, 100, 200, 40), total=6, current=2)
        banner = self.kit.prompt_banner("banner", pygame.Rect(100, 300, 600, 60), text="HELLO", on_replay=lambda: None)
        layer = self.kit.layer([a, chip, dots, *banner.controls], initial_focus="a")
        layer.focus("a", visible=True)
        target = pygame.Surface((1024, 600))
        layer.draw(target)
        builds = self.kit.painter.build_count
        text_calls = self.typography.calls
        for _ in range(25):
            layer.draw(target)
        self.assertEqual(self.kit.painter.build_count, builds)
        self.assertEqual(self.typography.calls, text_calls)
        chip.value = 8
        layer.draw(target)
        self.assertGreater(self.kit.painter.build_count, builds)

    def test_each_state_renders_distinct_cached_body(self) -> None:
        a = self._button("a", (100, 100, 200, 80))
        normal = a.render()
        a.hovered = True
        hover = a.render()
        a.hovered, a.pressed = False, True
        pressed = a.render()
        a.pressed, a.enabled = False, False
        disabled = a.render()
        a.enabled, a.selected = True, True
        selected = a.render()
        surfaces = [normal, hover, pressed, disabled, selected]
        self.assertEqual(len({id(surface) for surface in surfaces}), 5)
        colours = {surface.get_at((100, 30))[:3] for surface in surfaces}
        self.assertGreaterEqual(len(colours), 4)
        a.selected = False
        self.assertIs(a.render(), normal)

    def test_controls_present_rle_copies_on_opaque_targets_only(self) -> None:
        # Acer 87322f0d: un-encoded kit composites cost 2 ms per button per
        # frame (6-10 ms of every frame in Labirinto/Corsa).
        from greia_platform.pygame_blit import is_rle

        a = self._button("a", (100, 100, 200, 80))
        layer = self.kit.layer([a])
        opaque = pygame.Surface((400, 300))
        opaque.fill((30, 90, 160))
        reference = opaque.copy()
        reference.blit(a.render(), (100, 100))
        layer.draw(opaque)
        painter = self.kit.painter
        presented = painter.presentable(a.render(), opaque)
        self.assertTrue(is_rle(presented))
        self.assertIs(painter.presentable(a.render(), opaque), presented, "made once")
        self.assertFalse(is_rle(a.render()), "the product itself stays composable")
        for point in ((110, 110), (200, 140), (295, 175), (101, 101)):
            got, want = opaque.get_at(point), reference.get_at(point)
            self.assertLessEqual(max(abs(got[i] - want[i]) for i in range(3)), 1, point)
        # Alpha targets (HUD overlays) get the plain product: RLE alpha blits
        # would write opaque destination alpha there.
        overlay = pygame.Surface((400, 300), pygame.SRCALPHA)
        self.assertIs(painter.presentable(a.render(), overlay), a.render())
        layer.draw(overlay)
        edge = overlay.get_at((100, 100))
        self.assertLess(edge[3], 255)
        painter.clear()
        self.assertIsNot(painter.presentable(a.render(), opaque), presented)

    def test_painter_cache_is_hard_bounded(self) -> None:
        painter = ControlPainter(self.typography, max_surfaces=8, max_labels=4)
        for width in range(40, 80):
            painter.body(BodyShape.PILL, (width, 40), (200, 100, 50))
            painter.label(f"L{width}", 20, (0, 0, 0))
        self.assertLessEqual(painter.cached_surface_count, 8)
        self.assertLessEqual(len(painter._labels), 4)


class LayoutTests(_KitTestCase):
    def test_surface_layout_keeps_bars_clear_of_chrome_at_all_viewports(self) -> None:
        for width, height in VIEWPORTS:
            with self.subTest(viewport=(width, height)):
                layout = ControlLayout.for_surface(width, height)
                chrome = ActivitySystemChromeLayout.for_surface(width, height).protected_region
                self.assertEqual(layout.protected, pygame.Rect(chrome.x, chrome.y, chrome.width, chrome.height))
                bar = layout.top_bar(layout.control_height(56, maximum=chrome.height))
                self.assertFalse(bar.colliderect(layout.protected))
                self.assertLessEqual(bar.right, width)
                bottom = layout.bottom_bar(64)
                self.assertFalse(bottom.colliderect(layout.protected))
                self.assertLessEqual(bottom.bottom, height)
                moved = layout.clear_of_chrome(pygame.Rect(0, 0, 200, 50))
                self.assertFalse(moved.colliderect(layout.protected))

    def test_reference_canvas_layout_maps_chrome_into_logical_space(self) -> None:
        for width, height in VIEWPORTS:
            with self.subTest(viewport=(width, height)):
                screen = pygame.Surface((width, height))
                canvas = PygameReferenceCanvas(screen)
                layout = ControlLayout.for_canvas(canvas, (width, height))
                chrome = ActivitySystemChromeLayout.for_surface(width, height).protected_region
                transform = canvas.mapper.transform
                for corner in ((chrome.right - 1, chrome.bottom - 1), (chrome.x + 1, chrome.y + 1)):
                    logical = transform.physical_to_logical(corner, reject_outside=False)
                    if 0 <= logical[0] < 1024 and 0 <= logical[1] < 600:
                        self.assertTrue(layout.protected.collidepoint(int(logical[0]), int(logical[1])))
                bar = layout.top_bar(layout.control_height(64, maximum=72))
                self.assertFalse(bar.colliderect(layout.protected))
                self.assertGreaterEqual(bar.height * transform.scale, min(40, 72 * transform.scale) - 1)
                widths, compact = layout.fit(bar.width, [260, 260, 260, 200], [80, 80, 80, 200], 10)
                self.assertLessEqual(sum(widths) + 30, bar.width)
                for rect in layout.row(bar, widths, align=Align.START, gap=10):
                    self.assertFalse(rect.colliderect(layout.protected))
                    self.assertLessEqual(rect.right, 1024)

    def test_fit_prefers_full_labels_then_compact(self) -> None:
        self.assertEqual(ControlLayout.fit(1000, [200, 200], [80, 80], 10), ([200, 200], False))
        widths, compact = ControlLayout.fit(380, [200, 200], [80, 80], 10)
        self.assertFalse(compact)
        self.assertLessEqual(sum(widths) + 10, 380)
        widths, compact = ControlLayout.fit(200, [200, 200], [80, 80], 10)
        self.assertTrue(compact)
        self.assertLessEqual(sum(widths) + 10, 200)


class InputAdapterTests(_KitTestCase):
    def test_keyboard_maps_to_shared_navigation_semantics(self) -> None:
        adapter = PygameControlInput()
        right = adapter.translate(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT))
        space = adapter.translate(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
        self.assertEqual((right.action, right.edge), (SemanticAction.NAV_RIGHT, InputEdge.PRESSED))
        self.assertEqual(space.action, SemanticAction.ACTIVATE)

    def test_controller_buttons_and_stick_repeat(self) -> None:
        from greia_platform import pygame_input

        if pygame_input.sdl_controller is None or pygame_input._CONTROLLER_BUTTON_DOWN < 0:
            self.skipTest("SDL controller events unavailable in this pygame build")
        now = [10.0]
        adapter = PygameControlInput(clock=lambda: now[0])
        dpad = adapter.translate(
            pygame.event.Event(pygame_input._CONTROLLER_BUTTON_DOWN, button=pygame_input.CONTROLLER_BUTTON_DPAD_LEFT)
        )
        south = adapter.translate(
            pygame.event.Event(pygame_input._CONTROLLER_BUTTON_DOWN, button=pygame_input.CONTROLLER_BUTTON_A)
        )
        self.assertEqual((dpad.action, dpad.source), (SemanticAction.NAV_LEFT, InputSource.CONTROLLER))
        self.assertEqual(south.action, SemanticAction.ACTIVATE)
        stick = adapter.translate(
            pygame.event.Event(pygame_input._CONTROLLER_AXIS_MOTION, axis=pygame_input.CONTROLLER_AXIS_LEFTX, value=32000)
        )
        self.assertEqual(stick.action, SemanticAction.NAV_RIGHT)
        self.assertIsNone(adapter.poll())
        now[0] += 0.5
        self.assertEqual(adapter.poll().action, SemanticAction.NAV_RIGHT)
        self.assertIsNone(adapter.poll())
        adapter.translate(
            pygame.event.Event(pygame_input._CONTROLLER_AXIS_MOTION, axis=pygame_input.CONTROLLER_AXIS_LEFTX, value=0)
        )
        now[0] += 1.0
        self.assertIsNone(adapter.poll())

    def test_pointer_mapping_and_protected_chrome_drop(self) -> None:
        adapter = PygameControlInput(
            to_logical=lambda pos: (pos[0] * 2, pos[1] * 2),
            is_safe=lambda pos: pos[0] > 100,
        )
        down = adapter.translate(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(150, 50)))
        self.assertEqual((down.phase, down.position), (PointerPhase.DOWN, (300, 100)))
        self.assertIsNone(adapter.translate(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(20, 20))))
        cancel = adapter.translate(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=(20, 20)))
        self.assertEqual(cancel.phase, PointerPhase.CANCEL)


class CastFeedbackTests(_KitTestCase):
    def test_correct_and_try_again_poses_hooks_and_timeout(self) -> None:
        now = [0.0]
        sounds: list[str] = []
        cast = CastFeedback(
            "dani",
            height=128,
            art=ControlArt(_repo_resolver),
            clock=lambda: now[0],
            on_correct=lambda: sounds.append("yay"),
            on_try_again=lambda: sounds.append("hmm"),
        )
        self.assertTrue(cast.available)
        cast.correct()
        self.assertEqual((cast.pose, sounds), (CastPose.CHEER, ["yay"]))
        target = pygame.Surface((300, 300), pygame.SRCALPHA)
        cast.draw(target, (150, 290))
        self.assertGreater(target.get_bounding_rect().height, 60)
        now[0] += 5
        self.assertTrue(cast.update())
        self.assertEqual(cast.pose, CastPose.IDLE)
        cast.try_again()
        self.assertEqual((cast.pose, sounds[-1]), (CastPose.THINK, "hmm"))

    def test_opaque_targets_get_an_rle_pose_with_identical_pixels(self) -> None:
        from greia_platform.pygame_blit import is_rle

        art = ControlArt(_repo_resolver)
        cast = CastFeedback("tito", height=96, art=art)
        pose = art.image("character.tito", 96, variant="happy")
        reference = pygame.Surface((200, 200))
        reference.fill((90, 160, 220))
        reference.blit(pose, pose.get_rect(midbottom=(100, 190)))
        target = pygame.Surface((200, 200))
        target.fill((90, 160, 220))
        blitted: list[pygame.Surface] = []

        class _Spy(pygame.Surface):
            def blit(self, source, *args, **kwargs):  # type: ignore[override]
                blitted.append(source)
                return super().blit(source, *args, **kwargs)

        spy = _Spy((200, 200))
        spy.fill((90, 160, 220))
        cast.draw(spy, (100, 190))
        cast.draw(target, (100, 190))
        self.assertTrue(is_rle(blitted[0]))
        self.assertIsNot(blitted[0], pose)
        self.assertFalse(is_rle(pose), "the shared loader image is never modified")
        for x in range(0, 200, 7):
            for y in range(0, 200, 7):
                a, b = reference.get_at((x, y)), target.get_at((x, y))
                self.assertLessEqual(max(abs(a[i] - b[i]) for i in range(3)), 1, (x, y))
        # Per-pixel-alpha targets keep the plain pose (RLE would turn edges opaque).
        alpha_spy = _Spy((200, 200), pygame.SRCALPHA)
        blitted.clear()
        cast.draw(alpha_spy, (100, 190))
        self.assertIs(blitted[0], pose)

    def test_control_art_presentable_is_bounded_and_target_aware(self) -> None:
        from greia_platform.pygame_blit import is_rle

        art = ControlArt(_repo_resolver, max_entries=2)
        poses = [art.image("character.leo", 40 + i, variant="pose_point") for i in range(3)]
        opaque = pygame.Surface((64, 64))
        prepared = [art.presentable(pose, opaque) for pose in poses]
        self.assertTrue(all(is_rle(p) for p in prepared))
        self.assertIs(art.presentable(poses[2], opaque), prepared[2])
        self.assertLessEqual(len(art._presentable), 2)
        self.assertIs(art.presentable(poses[0], pygame.Surface((8, 8), pygame.SRCALPHA)), poses[0])
        art.clear()
        self.assertEqual(len(art._presentable), 0)

    def test_every_cast_member_has_think_and_cheer_art(self) -> None:
        art = ControlArt(_repo_resolver)
        for name in ("lilli", "leo", "flash", "dani", "tito", "momo"):
            for variant in ("pose_cheer", "pose_think"):
                self.assertIsNotNone(art.image(f"character.{name}", 64, variant=variant), (name, variant))

    def test_missing_art_degrades_silently(self) -> None:
        cast = CastFeedback("momo", height=64, art=ControlArt(lambda *_: Path("/nonexistent.png")))
        self.assertFalse(cast.available)
        cast.correct()
        cast.draw(pygame.Surface((64, 64)), (32, 64))
        with self.assertRaises(ValueError):
            CastFeedback("nino", height=64, art=ControlArt(_repo_resolver))


class CompletionSceneTests(_KitTestCase):
    def _content(self, secondary: str | None = None) -> CompletionContent:
        return CompletionContent(
            title="HOUSE COMPLETED!",
            primary_label="PLAY AGAIN",
            body_lines=("YOU SOLVED ALL THE ROOMS WITH DANI!",),
            achievement_count=2,
            secondary_label=secondary,
        )

    def test_scene_frame_is_opaque_and_draw_is_cached(self) -> None:
        screen = PygameCompletionScreen(self.typography, scene=CompletionScene(self.kit, character="dani", star_total=3))
        screen.prepare(self._content())
        frame = screen.prepared_surface
        assert frame is not None
        self.assertEqual(frame.get_flags() & pygame.SRCALPHA, 0)
        target = pygame.Surface((1024, 600))
        screen.draw(target)
        calls, builds = self.typography.calls, self.kit.painter.build_count
        for _ in range(10):
            screen.draw(target)
        self.assertEqual((self.typography.calls, self.kit.painter.build_count), (calls, builds))
        self.assertTrue(screen.primary_contains(screen.primary_rect.center))
        self.assertIsNone(screen.secondary_rect)

    def test_keyboard_and_pointer_choose_actions(self) -> None:
        screen = PygameCompletionScreen(self.typography, scene=CompletionScene(self.kit, character="leo"))
        screen.prepare(self._content(secondary="NEXT"))
        self.assertIsNotNone(screen.secondary_rect)
        self.assertIsNone(screen.handle_input(_press(SemanticAction.NAV_RIGHT)))
        self.assertEqual(screen.focused_action, CompletionAction.SECONDARY)
        self.assertEqual(screen.handle_input(_press(SemanticAction.ACTIVATE)), CompletionAction.SECONDARY)
        screen.handle_input(_press(SemanticAction.NAV_LEFT))
        self.assertEqual(screen.handle_input(_press(SemanticAction.ACTIVATE)), CompletionAction.PRIMARY)
        centre = screen.primary_rect.center
        self.assertIsNone(screen.handle_input(KitPointer(PointerPhase.DOWN, centre)))
        self.assertEqual(screen.handle_input(KitPointer(PointerPhase.UP, centre)), CompletionAction.PRIMARY)

    def test_overlay_routes_through_surface_navigator(self) -> None:
        class Base(Screen):
            surface_id = "base"

            def handle_event(self, event):
                return UiEventResult.IGNORED

            def draw(self, target):
                pass

        restarted: list[str] = []
        screen = PygameCompletionScreen(self.typography, scene=CompletionScene(self.kit, character=None))
        screen.prepare(self._content())
        navigator = SurfaceNavigator(Base())
        navigator.push_overlay(CompletionOverlay(screen, on_primary=lambda: restarted.append("again")))
        navigator.dispatch(_press(SemanticAction.ACTIVATE))
        self.assertEqual(restarted, ["again"])

    def test_legacy_card_is_unchanged_without_scene(self) -> None:
        legacy = PygameCompletionScreen(self.typography)
        before = legacy.primary_rect
        legacy.prepare(CompletionContent(title="Done", primary_label="Again", achievement_count=3))
        self.assertEqual(legacy.primary_rect, before)
        self.assertFalse(legacy.has_scene)
        self.assertEqual(legacy.handle_input(_press(SemanticAction.ACTIVATE)), CompletionAction.PRIMARY)


class ThemeTests(unittest.TestCase):
    def test_accent_tokens_resolve_and_unknown_tokens_fail(self) -> None:
        self.assertEqual(ControlTheme.for_accent("ocean").accent, (74, 145, 216))
        self.assertEqual(ControlTheme.for_accent("ocean").accent_text, (255, 255, 255))
        self.assertEqual(ControlTheme.for_accent("sunshine").accent_text, ControlTheme().text)
        with self.assertRaises(ValueError):
            ControlTheme.for_accent("neon")


if __name__ == "__main__":
    unittest.main()
