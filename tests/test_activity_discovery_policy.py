from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from greia_launcher.catalogue_view import ActivityCatalogue
from greia_platform.activities import ActivityManifest
from greia_platform.activity_discovery import (
    ActivityDiscoveryPolicy,
    ActivityDiscoveryPolicyStore,
    ActivityDiscoveryService,
    ActivityVisibilityMode,
    ActivityVisibilityOverride,
    AdaptiveCollectionPlanner,
    ChallengePreference,
)


def _activity(
    index: int,
    *,
    difficulty: int = 3,
    age_min: int | None = None,
    age_max: int | None = None,
    tags: tuple[str, ...] = (),
    categories: tuple[str, ...] = ("create",),
) -> ActivityManifest:
    return ActivityManifest(
        activity_id=f"org.greia.test-{index}",
        legacy_ids=(),
        title_key=f"activity.test_{index}.title",
        version="0.1.0",
        runtime_type="python",
        api_version="0.1",
        entrypoint=Path("main.py"),
        icon_id="robot",
        categories=("test",),
        skills=(),
        events=(),
        difficulty=difficulty,
        languages=("it",),
        required_capabilities=(),
        optional_capabilities=(),
        requested_permissions=(),
        storage_schema_version=1,
        root=Path("/tmp"),
        launcher_categories=categories,
        discovery_tags=tags,
        recommended_age_min=age_min,
        recommended_age_max=age_max,
    )


class ActivityDiscoveryPolicyTests(unittest.TestCase):
    def test_missing_age_metadata_fails_open_and_parent_override_wins(self) -> None:
        unknown = _activity(1)
        too_simple = _activity(2, age_min=3, age_max=5)
        recommended = _activity(3, age_min=6, age_max=9)
        service = ActivityDiscoveryService()
        policy = ActivityDiscoveryPolicy(
            visibility_mode=ActivityVisibilityMode.RECOMMENDED_ONLY,
            overrides=((too_simple.activity_id, ActivityVisibilityOverride.ALWAYS_SHOW),),
        )
        result = service.effective_activities(
            (unknown, too_simple, recommended),
            approximate_age=7,
            challenge_preference=ChallengePreference.AUTOMATIC,
            policy=policy,
        )
        self.assertEqual(
            {item.activity_id for item in result},
            {unknown.activity_id, too_simple.activity_id, recommended.activity_id},
        )

        hidden = policy.with_override(
            recommended.activity_id, ActivityVisibilityOverride.ALWAYS_HIDE
        )
        result = service.effective_activities(
            (unknown, too_simple, recommended),
            approximate_age=7,
            challenge_preference=ChallengePreference.AUTOMATIC,
            policy=hidden,
        )
        self.assertNotIn(recommended.activity_id, {item.activity_id for item in result})

    def test_hide_too_simple_only_uses_declared_upper_age_bound(self) -> None:
        general = _activity(1, difficulty=1)
        young = _activity(2, difficulty=8, age_min=3, age_max=5)
        service = ActivityDiscoveryService()
        policy = ActivityDiscoveryPolicy(
            visibility_mode=ActivityVisibilityMode.HIDE_TOO_SIMPLE
        )
        result = service.effective_activities(
            (general, young),
            approximate_age=8,
            challenge_preference=ChallengePreference.STANDARD,
            policy=policy,
        )
        self.assertEqual(tuple(item.activity_id for item in result), (general.activity_id,))

    def test_challenge_preference_ranks_without_hiding(self) -> None:
        easy = _activity(1, difficulty=1, age_min=4, age_max=8)
        hard = _activity(2, difficulty=8, age_min=4, age_max=8)
        service = ActivityDiscoveryService()
        policy = ActivityDiscoveryPolicy()
        easier = service.effective_activities(
            (hard, easy),
            approximate_age=6,
            challenge_preference=ChallengePreference.EASIER,
            policy=policy,
        )
        harder = service.effective_activities(
            (easy, hard),
            approximate_age=6,
            challenge_preference=ChallengePreference.HARDER,
            policy=policy,
        )
        self.assertEqual(easier, (easy, hard))
        self.assertEqual(harder, (hard, easy))

    def test_policy_store_roundtrip_preserves_parent_and_hysteresis_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = ActivityDiscoveryPolicyStore(Path(temporary) / "policy.json")
            policy = ActivityDiscoveryPolicy(
                visibility_mode=ActivityVisibilityMode.CUSTOM,
                overrides=(("org.greia.example", ActivityVisibilityOverride.ALWAYS_HIDE),),
                subdivided_collections=("learn",),
            )
            store.write(policy)
            self.assertEqual(store.read(), policy)

    def test_adaptive_thresholds_and_hysteresis(self) -> None:
        planner = AdaptiveCollectionPlanner()
        ten = tuple(
            _activity(i, tags=("drawing",) if i < 5 else ("writing",))
            for i in range(10)
        )
        eleven = ten + (_activity(10, tags=("writing",)),)
        eight = ten[:8]

        self.assertFalse(
            planner.plan(
                "create", ten, allowed_group_ids=("drawing", "writing")
            ).subdivided
        )
        self.assertTrue(
            planner.plan(
                "create", eleven, allowed_group_ids=("drawing", "writing")
            ).subdivided
        )
        self.assertTrue(
            planner.plan(
                "create",
                ten,
                allowed_group_ids=("drawing", "writing"),
                previously_subdivided=True,
            ).subdivided
        )
        self.assertFalse(
            planner.plan(
                "create",
                eight,
                allowed_group_ids=("drawing", "writing"),
                previously_subdivided=True,
            ).subdivided
        )

    def test_incoherent_large_collection_stays_direct(self) -> None:
        planner = AdaptiveCollectionPlanner()
        activities = tuple(
            _activity(
                i,
                tags=("drawing",) if i < 6 else (() if i == 6 else ("writing",)),
            )
            for i in range(11)
        )
        plan = planner.plan(
            "create", activities, allowed_group_ids=("drawing", "writing")
        )
        self.assertFalse(plan.subdivided)
        self.assertEqual(plan.activities, activities)

    def test_catalogue_exposes_only_one_optional_subcollection_layer(self) -> None:
        activities = tuple(
            _activity(i, tags=("drawing",) if i < 6 else ("writing",))
            for i in range(12)
        )
        catalogue = ActivityCatalogue.from_activities(activities)
        groups = catalogue.subcollections_for("create")
        self.assertEqual({group.collection_id for group in groups}, {"drawing", "writing"})
        self.assertEqual(sum(len(group.items) for group in groups), 12)
        self.assertIn("create", catalogue.subdivided_collection_ids)


if __name__ == "__main__":
    unittest.main()
