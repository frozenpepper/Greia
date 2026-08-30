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

    def test_activity_uses_shared_logical_canvas_and_platform_navigation(self) -> None:
        combined = "\n".join(p.read_text(encoding="utf-8") for p in sorted(ACTIVITY.glob("*.py")))
        self.assertIn("PygameReferenceCanvas", combined)
        self.assertIn("activity_viewport_for_surface", combined)
        self.assertIn("canvas.pointer(event.pos)", combined)
        self.assertIn("ChildUiMetrics.for_size", combined)
        self.assertIn("get_theme()", combined)
        self.assertIn("activity_stop_requested()", combined)

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


if __name__ == "__main__":
    unittest.main()
