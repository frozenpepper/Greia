from __future__ import annotations

import tomllib
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from greia_platform.assets import AssetCatalogue
from greia_platform.pygame_scene import PygameSceneRenderer, SceneRenderError
from greia_platform.scene import SceneDefinition, SceneFit, SceneNode
from greia_platform.scene_actor import (
    CharacterMotion,
    CharacterState,
    SceneActorDefinition,
    actor_scene_sample,
    sample_scene_actor,
)


class SceneActorTests(unittest.TestCase):
    def actor(self, **kwargs) -> SceneActorDefinition:
        defaults = dict(
            actor_id="lilli",
            asset_id="character.lilli",
            rect=(100, 200, 160, 160),
            shadow_asset_id="shadow.contact.small.01",
            shadow_rect=(126, 328, 108, 28),
            idle_amplitude=4,
            idle_period_seconds=2,
            blink_period_seconds=5,
            blink_duration_seconds=0.2,
        )
        defaults.update(kwargs)
        return SceneActorDefinition(**defaults)

    def test_neutral_static_sample_is_grounded(self) -> None:
        sample = sample_scene_actor(
            self.actor(), elapsed_seconds=1.0, motion_enabled=False
        )
        shadow, body = sample.nodes
        self.assertEqual(sample.state, "neutral")
        self.assertEqual(body.variant, "default")
        self.assertEqual(body.fallback_variant, "default")
        self.assertEqual(body.rect, (100.0, 200.0, 160.0, 160.0))
        self.assertEqual(shadow.rect, (126.0, 328.0, 108.0, 28.0))
        self.assertEqual(shadow.z, body.z - 1)
        self.assertTrue(shadow.optional)

    def test_idle_motion_moves_body_without_moving_shadow(self) -> None:
        actor = self.actor()
        sample = sample_scene_actor(actor, elapsed_seconds=0.5)
        shadow, body = sample.nodes
        self.assertGreater(body.rect[1], actor.rect[1])
        self.assertEqual(shadow.rect, actor.shadow_rect)

    def test_blink_is_variant_swap_not_new_asset(self) -> None:
        actor = self.actor()
        sample = sample_scene_actor(actor, elapsed_seconds=0.05)
        _, body = sample.nodes
        self.assertEqual(sample.state, "blink")
        self.assertEqual(body.asset_id, "character.lilli")
        self.assertEqual(body.variant, "blink")
        self.assertEqual(body.fallback_variant, "default")

    def test_all_semantic_states_map_to_expected_variants(self) -> None:
        actor = self.actor()
        states_expected = [
            (CharacterState.NEUTRAL, "default"),
            (CharacterState.BLINK, "blink"),
            (CharacterState.HAPPY, "happy"),
            (CharacterState.SURPRISED, "surprised"),
            (CharacterState.SLEEPY, "sleepy"),
            ("neutral", "default"),
            ("blink", "blink"),
            ("happy", "happy"),
            ("surprised", "surprised"),
            ("sleepy", "sleepy"),
        ]
        for st, expected_variant in states_expected:
            sample = sample_scene_actor(actor, elapsed_seconds=1.0, motion_enabled=False, state=st)
            _, body = sample.nodes
            self.assertEqual(body.variant, expected_variant, f"State {st!r} did not map to {expected_variant!r}")

    def test_all_semantic_motions_move_body_deterministically(self) -> None:
        actor = self.actor()
        motions = [
            CharacterMotion.IDLE_BOUNCE,
            CharacterMotion.BLINK,
            CharacterMotion.HAPPY_HOP,
            CharacterMotion.CELEBRATE_POP,
            CharacterMotion.SURPRISED_WOBBLE,
            CharacterMotion.SLEEPY_SWAY,
        ]
        for m in motions:
            sample1 = sample_scene_actor(actor, elapsed_seconds=0.25, motion=m)
            sample2 = sample_scene_actor(actor, elapsed_seconds=0.25, motion=m)
            shadow1, body1 = sample1.nodes
            shadow2, body2 = sample2.nodes
            self.assertEqual(body1.rect, body2.rect, f"Motion {m} non-deterministic")
            self.assertEqual(shadow1.rect, actor.shadow_rect, f"Motion {m} moved shadow rect")
            # Width and height never change or become negative/zero
            self.assertEqual(body1.rect[2], actor.rect[2])
            self.assertEqual(body1.rect[3], actor.rect[3])
            self.assertGreater(body1.rect[2], 0)
            self.assertGreater(body1.rect[3], 0)

    def test_invalid_state_and_motion_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.actor(state="hyper_excited")
        with self.assertRaises(ValueError):
            self.actor(motion="teleport_spin")
        with self.assertRaises(ValueError):
            sample_scene_actor(self.actor(), elapsed_seconds=0, state="invalid_state")
        with self.assertRaises(ValueError):
            sample_scene_actor(self.actor(), elapsed_seconds=0, motion="invalid_motion")

    def test_actor_scene_reuses_scene_contract(self) -> None:
        scene = actor_scene_sample(
            self.actor(),
            canvas_size=(1024, 600),
            elapsed_seconds=1.0,
            fit=SceneFit.COVER,
        )
        self.assertEqual(scene.canvas_size, (1024, 600))
        self.assertEqual(scene.fit, SceneFit.COVER)
        self.assertEqual([node.node_id for node in scene.nodes], [
            "lilli.shadow",
            "lilli.body",
        ])

    def test_invalid_blink_duration_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            SceneActorDefinition(
                actor_id="bad",
                asset_id="character.lilli",
                rect=(0, 0, 100, 100),
                shadow_asset_id="shadow.contact.small.01",
                shadow_rect=(10, 80, 80, 20),
                blink_period_seconds=1,
                blink_duration_seconds=1,
            )

    def test_canonical_source_catalogue_no_duplicates_no_current_nino(self) -> None:
        cat_path = Path("assets/visual/characters/canonical/v0.1/catalog.toml")
        self.assertTrue(cat_path.exists())
        data = tomllib.loads(cat_path.read_text())
        chars = data.get("characters", [])
        self.assertEqual(len(chars), 6)
        ids = [c["id"] for c in chars]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertNotIn("character.nino", ids)
        self.assertIn("character.leo", ids)
        self.assertIn("character.flash", ids)
        self.assertIn("character.dani", ids)
        self.assertIn("character.lilli", ids)
        self.assertIn("character.tito", ids)
        self.assertIn("character.momo", ids)

    def test_shared_visuals_v1_renditions_exist_for_all_six_characters(self) -> None:
        cat_path = Path("assets/catalog/shared_visuals_v1_source.toml")
        data = tomllib.loads(cat_path.read_text())
        visuals = {v["id"]: v for v in data.get("visuals", [])}
        expected_chars = [
            "character.lilli",
            "character.leo",
            "character.flash",
            "character.dani",
            "character.tito",
            "character.momo",
        ]
        expected_variants = {
            "default",
            "blink",
            "happy",
            "surprised",
            "sleepy",
            "pose_cheer",
            "pose_point",
            "pose_think",
            "sad",
            "angry",
            "silly",
            "pose_wave",
            "pose_play",
        }
        for cid in expected_chars:
            self.assertIn(cid, visuals, f"Missing character visual {cid}")
            variants = {v["name"]: v for v in visuals[cid]["variants"]}
            self.assertEqual(set(variants.keys()), expected_variants, f"Missing variants in {cid}")
            for vname, vdata in variants.items():
                out_path = Path("assets") / vdata["output"]
                self.assertTrue(out_path.exists(), f"Rendition file missing: {out_path}")

    def test_renderer_fallback_variant_resolves_and_does_not_retry_failed_variant(self) -> None:
        # Mock visual cache where 'happy' fails but 'default' succeeds
        mock_cache = MagicMock()
        mock_surface_default = MagicMock()

        happy_attempts = 0
        default_attempts = 0

        def mock_get(asset_id, variant="default", size=(100, 100)):
            nonlocal happy_attempts, default_attempts
            if variant == "happy":
                happy_attempts += 1
                raise KeyError("happy variant missing")
            if variant == "default":
                default_attempts += 1
                return mock_surface_default
            raise KeyError(variant)

        mock_cache.get.side_effect = mock_get

        mock_pygame = MagicMock()
        mock_target = MagicMock()
        mock_target.get_size.return_value = (1024, 600)
        mock_target.get_rect.return_value = MagicMock(colliderect=lambda r: True)
        mock_pygame.Rect.return_value = MagicMock(
            colliderect=lambda r: True, width=100, height=100, size=(100, 100)
        )

        renderer = PygameSceneRenderer(mock_cache, max_failed_entries=64, pygame_module=mock_pygame)

        scene = SceneDefinition(
            scene_id="test_fallback",
            canvas_size=(1024, 600),
            background=(0, 0, 0),
            nodes=(
                SceneNode(
                    node_id="flash.body",
                    asset_id="character.flash",
                    variant="happy",
                    fallback_variant="default",
                    rect=(100, 100, 100, 100),
                ),
            ),
        )

        # Draw 3 times consecutively
        for i in range(3):
            stats = renderer.draw(scene, mock_target, clear=False)
            self.assertEqual(stats.drawn_nodes, 1)
            self.assertEqual(stats.fallback_nodes, 1)

        # 'happy' must be attempted exactly ONCE across all 3 frames!
        self.assertEqual(happy_attempts, 1)
        # 'default' is used on all 3 frames
        self.assertEqual(default_attempts, 3)

        # Now clear renderer and draw again -> failure memory is reset, so happy is attempted once more
        renderer.clear()
        stats = renderer.draw(scene, mock_target, clear=False)
        self.assertEqual(stats.drawn_nodes, 1)
        self.assertEqual(stats.fallback_nodes, 1)
        self.assertEqual(happy_attempts, 2)
        self.assertEqual(default_attempts, 4)

    def test_required_default_failure_avoids_repeated_decode_work(self) -> None:
        # Mock visual cache where required 'default' fails
        mock_cache = MagicMock()
        default_attempts = 0

        def mock_get(asset_id, variant="default", size=(100, 100)):
            nonlocal default_attempts
            default_attempts += 1
            raise KeyError("dani default missing")

        mock_cache.get.side_effect = mock_get

        mock_pygame = MagicMock()
        mock_target = MagicMock()
        mock_target.get_size.return_value = (1024, 600)
        mock_target.get_rect.return_value = MagicMock(colliderect=lambda r: True)
        mock_pygame.Rect.return_value = MagicMock(
            colliderect=lambda r: True, width=100, height=100, size=(100, 100)
        )

        renderer = PygameSceneRenderer(mock_cache, max_failed_entries=64, pygame_module=mock_pygame)

        scene = SceneDefinition(
            scene_id="test_default_failure",
            canvas_size=(1024, 600),
            background=(0, 0, 0),
            nodes=(
                SceneNode(
                    node_id="dani.body",
                    asset_id="character.dani",
                    variant="default",
                    rect=(100, 100, 100, 100),
                ),
            ),
        )

        # Draw 1: raises SceneRenderError and records failure
        with self.assertRaises(SceneRenderError):
            renderer.draw(scene, mock_target, clear=False)
        self.assertEqual(default_attempts, 1)

        # Draw 2: raises SceneRenderError immediately without calling mock_cache.get!
        with self.assertRaises(SceneRenderError):
            renderer.draw(scene, mock_target, clear=False)
        self.assertEqual(default_attempts, 1)


if __name__ == "__main__":
    unittest.main()
