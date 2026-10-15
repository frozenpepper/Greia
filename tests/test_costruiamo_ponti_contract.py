from __future__ import annotations

from pathlib import Path
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]
ACTIVITY = ROOT / "activities" / "costruiamo_ponti"


class CostruiamoPontiContractTests(unittest.TestCase):
    def test_manifest_declares_interaction_without_extra_authority(self) -> None:
        with (ACTIVITY / "activity.toml").open("rb") as handle:
            raw = tomllib.load(handle)
        self.assertEqual(raw["activity"]["id"], "org.greia.costruiamo-ponti")
        self.assertEqual(raw["input"]["profile"], "hybrid")
        self.assertEqual(raw["requirements"]["required_capabilities"], ["display", "pointer", "audio.basic"])
        self.assertEqual(raw["permissions"]["requested"], [])
        self.assertNotIn("adaptive_difficulty", raw["education"])
        self.assertNotIn("difficulty_max", raw["education"])

    def test_activity_uses_shared_logical_canvas_and_platform_navigation(self) -> None:
        combined = "\n".join(p.read_text(encoding="utf-8") for p in sorted(ACTIVITY.glob("*.py")))
        self.assertIn("PygameReferenceCanvas", combined)
        self.assertIn("activity_viewport_for_surface", combined)
        self.assertIn("canvas.pointer(event.pos)", combined)
        self.assertIn("ChildUiMetrics.for_size", combined)
        self.assertIn("get_theme()", combined)
        self.assertIn("activity_stop_requested()", combined)

    def test_genuine_new_block_placement_not_repeat_click(self) -> None:
        from activities.costruiamo_ponti.ponti_model import PontiModel
        model = PontiModel()
        self.assertTrue(model.place_block(0))
        self.assertFalse(model.place_block(0))
        other = next(x for x in ("wood", "stone", "rainbow", "shroom") if x != model.selected_block_id)
        model.select_block(other)
        self.assertTrue(model.place_block(0))
        self.assertEqual(model.slots[0], other)

    def test_materials_and_runtime_assets_exist(self) -> None:
        runtime_dir = ACTIVITY / "assets" / "runtime"
        self.assertTrue((runtime_dir / "block_wood.png").is_file())
        self.assertTrue((runtime_dir / "block_stone.png").is_file())
        self.assertTrue((runtime_dir / "block_shroom.png").is_file())
        self.assertTrue((runtime_dir / "block_rainbow.png").is_file())
        self.assertTrue((runtime_dir / "trampoline.png").is_file())
        self.assertTrue((runtime_dir / "goal_flag.png").is_file())
        self.assertTrue((runtime_dir / "bank_river.png").is_file())
        self.assertTrue((runtime_dir / "bank_canyon.png").is_file())
        self.assertTrue((runtime_dir / "bank_space.png").is_file())

    def test_reference_geometry_is_semantic_and_bounded(self) -> None:
        combined = "\n".join(p.read_text(encoding="utf-8") for p in sorted(ACTIVITY.glob("*.py")))
        self.assertIn("REFERENCE_WIDTH = 1024", combined)
        self.assertIn("REFERENCE_HEIGHT = 600", combined)
        self.assertIn("SceneActorDefinition", combined)
        self.assertIn("character.flash", combined)

    def test_crossing_reaches_right_cliff_and_celebrates(self) -> None:
        combined = "\n".join(p.read_text(encoding="utf-8") for p in sorted(ACTIVITY.glob("*.py")))
        self.assertIn("target_x = bridge_end_x + 50", combined)
        self.assertIn("flash_motion = \"celebrate_pop\"", combined)
        self.assertIn("flash_anim_timer = 0.0", combined)


class CostruiamoPontiInputAndPointerTests(unittest.TestCase):
    """Real app: keyboard/controller path and the platform pointer."""

    @classmethod
    def setUpClass(cls) -> None:
        import os
        import sys

        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
        for path in (ROOT / "src", ROOT):
            if str(path) not in sys.path:
                sys.path.insert(0, str(path))
        import pygame

        pygame.init()
        cls.screen = pygame.display.set_mode((1024, 600))

    def _app(self):
        from activities.costruiamo_ponti.ponti_app import PontiApp

        return PontiApp(screen=self.screen)

    def _key(self, app, key: int) -> None:
        import pygame

        app._handle_event(pygame.event.Event(pygame.KEYDOWN, key=key))

    def test_keyboard_selects_material_places_blocks_and_crosses(self) -> None:
        import pygame

        app = self._app()
        model = app._model
        # First arrow reveals the cursor on the selected material (wood).
        self._key(app, pygame.K_RIGHT)
        self.assertTrue(app._focus.active)
        self._key(app, pygame.K_RIGHT)  # stone
        self._key(app, pygame.K_SPACE)
        self.assertEqual(model.selected_block_id, "stone")
        # Up from the palette lands on the bridge slots; Space places the block.
        self._key(app, pygame.K_UP)
        self.assertEqual(app._focus.target(model.num_slots).kind, "slot")
        self._key(app, pygame.K_SPACE)
        placed = [slot for slot in model.slots if slot == "stone"]
        self.assertEqual(len(placed), 1)
        # Up again reaches the Clear/Go row; Clear empties the bridge.
        self._key(app, pygame.K_UP)
        self.assertIn(app._focus.target(model.num_slots).kind, {"clear", "go"})
        while app._focus.target(model.num_slots).kind != "clear":
            self._key(app, pygame.K_LEFT)
        self._key(app, pygame.K_SPACE)
        self.assertEqual(model.slots, [None] * model.num_slots)
        # Go starts the crossing.
        self._key(app, pygame.K_RIGHT)
        self.assertEqual(app._focus.target(model.num_slots).kind, "go")
        self._key(app, pygame.K_RETURN)
        self.assertEqual(model.flash_state, "happy")

    def test_controller_dpad_and_south_button_drive_the_same_path(self) -> None:
        import pygame
        from greia_platform.pygame_input import (
            CONTROLLER_BUTTON_A,
            CONTROLLER_BUTTON_DPAD_RIGHT,
            CONTROLLER_BUTTON_DPAD_UP,
        )

        app = self._app()
        pad = lambda b: app._handle_event(pygame.event.Event(pygame.CONTROLLERBUTTONDOWN, button=b))
        pad(CONTROLLER_BUTTON_DPAD_RIGHT)  # reveal
        pad(CONTROLLER_BUTTON_DPAD_RIGHT)  # stone
        pad(CONTROLLER_BUTTON_A)
        self.assertEqual(app._model.selected_block_id, "stone")
        pad(CONTROLLER_BUTTON_DPAD_UP)
        pad(CONTROLLER_BUTTON_A)
        self.assertIn("stone", app._model.slots)

    def test_focus_ring_is_drawn_and_hidden_by_the_pointer(self) -> None:
        import pygame

        app = self._app()
        self._key(app, pygame.K_LEFT)
        app._draw(0.0, 0.0)
        rect = app._renderer.focus_rect("block", 0, app._model.num_slots)
        ring_pixel = app._canvas.surface.get_at((rect.left - 5, rect.centery))[:3]
        self.assertEqual(ring_pixel, (14, 116, 144))
        app._handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(500, 20)))
        self.assertFalse(app._focus.active)

    def test_platform_pointer_is_drawn_during_play_and_on_the_completion_screen(self) -> None:
        import pygame
        from unittest import mock

        app = self._app()
        target = app._canvas.target
        color = (254, 202, 87)  # draw_activity_pointer default body colour
        position = (300, 200)
        with mock.patch("pygame.mouse.get_focused", return_value=True), mock.patch(
            "pygame.mouse.get_pos", return_value=position
        ):
            app._draw(0.0, 0.0)
            app._canvas.present()
            self.assertEqual(tuple(target.get_at((position[0] + 8, position[1])))[:3], color)
            # Completion screen: the pointer must keep following the mouse.
            app._model.is_victory = True
            app._present_completion()
        for next_position in ((600, 300), (200, 450)):
            with mock.patch("pygame.mouse.get_focused", return_value=True), mock.patch(
                "pygame.mouse.get_pos", return_value=next_position
            ):
                app._present_completion()
                self.assertEqual(
                    tuple(target.get_at((next_position[0] + 8, next_position[1])))[:3], color
                )


if __name__ == "__main__":
    unittest.main()
