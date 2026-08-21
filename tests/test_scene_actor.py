from __future__ import annotations

import unittest

from greia_platform.scene import SceneFit
from greia_platform.scene_actor import (
    SceneActorDefinition,
    actor_scene_sample,
    sample_scene_actor,
)


class SceneActorTests(unittest.TestCase):
    def actor(self) -> SceneActorDefinition:
        return SceneActorDefinition(
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

    def test_neutral_static_sample_is_grounded(self) -> None:
        sample = sample_scene_actor(
            self.actor(), elapsed_seconds=1.0, motion_enabled=False
        )
        shadow, body = sample.nodes
        self.assertEqual(sample.state, "default")
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


if __name__ == "__main__":
    unittest.main()
