from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from greia_launcher.catalogue_view import ActivityCatalogue
from greia_platform.activities import ActivityManifest
from greia_platform.activity_discovery import (
    ActivityDiscoveryError,
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
    adaptive: bool = False,
    difficulty_min: int | None = None,
    difficulty_max: int | None = None,
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
        adaptive_difficulty=adaptive,
        difficulty_min=difficulty_min,
        difficulty_max=difficulty_max,
    )


class ActivityDiscoveryPolicyTests(unittest.TestCase):
    def test_unknown_age_is_excluded_by_restrictive_mode_and_parent_override_wins(self) -> None:
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
            {too_simple.activity_id, recommended.activity_id},
        )

        explicit = policy.with_override(
            recommended.activity_id, ActivityVisibilityOverride.ALWAYS_HIDE
        ).with_override(
            unknown.activity_id, ActivityVisibilityOverride.ALWAYS_SHOW
        )
        result = service.effective_activities(
            (unknown, too_simple, recommended),
            approximate_age=7,
            challenge_preference=ChallengePreference.AUTOMATIC,
            policy=explicit,
        )
        self.assertEqual(
            {item.activity_id for item in result},
            {unknown.activity_id, too_simple.activity_id},
        )

    def test_recommended_only_means_declared_range_contains_child_age(self) -> None:
        younger_only = _activity(1, age_min=1, age_max=2)
        exact = _activity(2, age_min=3, age_max=3)
        spanning = _activity(3, age_min=2, age_max=5)
        open_ended = _activity(4, age_min=3)
        older = _activity(5, age_min=4, age_max=8)
        unknown = _activity(6)
        result = ActivityDiscoveryService().effective_activities(
            (younger_only, exact, spanning, open_ended, older, unknown),
            approximate_age=3,
            challenge_preference=ChallengePreference.AUTOMATIC,
            policy=ActivityDiscoveryPolicy(
                visibility_mode=ActivityVisibilityMode.RECOMMENDED_ONLY
            ),
        )
        self.assertEqual(
            {item.activity_id for item in result},
            {exact.activity_id, spanning.activity_id, open_ended.activity_id},
        )

    def test_age_and_easier_never_includes_older_or_unknown_activity(self) -> None:
        younger = _activity(1, age_min=1, age_max=2)
        exact = _activity(2, age_min=3, age_max=3)
        spanning = _activity(3, age_min=2, age_max=5)
        open_ended = _activity(4, age_min=3)
        older = _activity(5, age_min=4, age_max=8)
        unknown = _activity(6)
        result = ActivityDiscoveryService().effective_activities(
            (younger, exact, spanning, open_ended, older, unknown),
            approximate_age=3,
            challenge_preference=ChallengePreference.AUTOMATIC,
            policy=ActivityDiscoveryPolicy(
                visibility_mode=ActivityVisibilityMode.AGE_AND_EASIER
            ),
        )
        self.assertEqual(
            {item.activity_id for item in result},
            {younger.activity_id, exact.activity_id, spanning.activity_id, open_ended.activity_id},
        )
        visible_ids = {item.activity_id for item in result}
        self.assertNotIn(older.activity_id, visible_ids)
        self.assertNotIn(unknown.activity_id, visible_ids)

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

    def test_difficulty_range_filters_fixed_and_adaptive_activities(self) -> None:
        easy = _activity(1, difficulty=2)
        hard = _activity(2, difficulty=9)
        adaptive = _activity(
            3,
            difficulty=5,
            adaptive=True,
            difficulty_min=3,
            difficulty_max=7,
        )
        service = ActivityDiscoveryService()
        policy = ActivityDiscoveryPolicy(difficulty_min=4, difficulty_max=6)
        result = service.effective_activities(
            (easy, hard, adaptive),
            approximate_age=None,
            challenge_preference=ChallengePreference.AUTOMATIC,
            policy=policy,
        )
        self.assertEqual(tuple(item.activity_id for item in result), (adaptive.activity_id,))

    def test_explicit_override_wins_over_difficulty_range(self) -> None:
        outside = _activity(1, difficulty=10)
        inside = _activity(2, difficulty=4)
        policy = ActivityDiscoveryPolicy(
            difficulty_min=3,
            difficulty_max=5,
            overrides=(
                (outside.activity_id, ActivityVisibilityOverride.ALWAYS_SHOW),
                (inside.activity_id, ActivityVisibilityOverride.ALWAYS_HIDE),
            ),
        )
        result = ActivityDiscoveryService().effective_activities(
            (outside, inside),
            approximate_age=None,
            challenge_preference=ChallengePreference.AUTOMATIC,
            policy=policy,
        )
        self.assertEqual(tuple(item.activity_id for item in result), (outside.activity_id,))

    def test_open_ended_difficulty_ranges_are_supported(self) -> None:
        activities = tuple(_activity(i, difficulty=i) for i in range(1, 7))
        service = ActivityDiscoveryService()
        lower = service.effective_activities(
            activities,
            approximate_age=None,
            challenge_preference=ChallengePreference.AUTOMATIC,
            policy=ActivityDiscoveryPolicy(difficulty_min=4),
        )
        upper = service.effective_activities(
            activities,
            approximate_age=None,
            challenge_preference=ChallengePreference.AUTOMATIC,
            policy=ActivityDiscoveryPolicy(difficulty_max=2),
        )
        self.assertEqual([item.difficulty for item in lower], [4, 5, 6])
        self.assertEqual([item.difficulty for item in upper], [1, 2])

    def test_policy_rejects_invalid_difficulty_range(self) -> None:
        for minimum, maximum in ((0, None), (None, 11), (7, 3), (True, 5)):
            with self.subTest(minimum=minimum, maximum=maximum):
                with self.assertRaises(ActivityDiscoveryError):
                    ActivityDiscoveryPolicy(  # type: ignore[arg-type]
                        difficulty_min=minimum,
                        difficulty_max=maximum,
                    )

    def test_policy_store_roundtrip_preserves_parent_and_hysteresis_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = ActivityDiscoveryPolicyStore(Path(temporary) / "policy.json")
            policy = ActivityDiscoveryPolicy(
                visibility_mode=ActivityVisibilityMode.CUSTOM,
                difficulty_min=2,
                difficulty_max=7,
                overrides=(("org.greia.example", ActivityVisibilityOverride.ALWAYS_HIDE),),
                subdivided_collections=("learn",),
            )
            store.write(policy)
            self.assertEqual(store.read(), policy)

    def test_policy_store_rejects_symlink_at_open_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "real-policy.json"
            ActivityDiscoveryPolicyStore(target).write(ActivityDiscoveryPolicy())
            link = root / "policy.json"
            try:
                link.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unavailable on this platform")
            with self.assertRaisesRegex(ActivityDiscoveryError, "symlink"):
                ActivityDiscoveryPolicyStore(link).read()

    def test_policy_store_rejects_regular_file_replacement_between_lstat_and_open(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "policy.json"
            store = ActivityDiscoveryPolicyStore(path)
            store.write(ActivityDiscoveryPolicy())
            replacement = root / "replacement.json"
            ActivityDiscoveryPolicyStore(replacement).write(
                ActivityDiscoveryPolicy(
                    visibility_mode=ActivityVisibilityMode.CUSTOM
                )
            )
            original_open = os.open
            swapped = False

            def swapping_open(candidate, flags, *args, **kwargs):
                nonlocal swapped
                if not swapped and Path(candidate) == path:
                    os.replace(replacement, path)
                    swapped = True
                return original_open(candidate, flags, *args, **kwargs)

            with patch(
                "greia_platform.activity_discovery.os.open",
                side_effect=swapping_open,
            ):
                with self.assertRaisesRegex(ActivityDiscoveryError, "changed while being read"):
                    store.read()
            self.assertTrue(swapped)

    def test_policy_store_rejects_non_regular_file_and_oversized_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaisesRegex(ActivityDiscoveryError, "regular file"):
                ActivityDiscoveryPolicyStore(root).read()

            oversized = root / "oversized.json"
            oversized.write_bytes(b"x" * (ActivityDiscoveryPolicyStore.MAX_BYTES + 1))
            with self.assertRaisesRegex(ActivityDiscoveryError, "size bound"):
                ActivityDiscoveryPolicyStore(oversized).read()

    def test_old_policy_without_difficulty_fields_remains_compatible(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "policy.json"
            path.write_text(
                '{"schema_version":1,"visibility_mode":"show_all","overrides":{},"subdivided_collections":[]}',
                encoding="utf-8",
            )
            policy = ActivityDiscoveryPolicyStore(path).read()
            self.assertIsNone(policy.difficulty_min)
            self.assertIsNone(policy.difficulty_max)

    def test_legacy_hide_too_simple_policy_migrates_to_age_and_easier(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "policy.json"
            path.write_text(
                '{"schema_version":1,"visibility_mode":"hide_too_simple","overrides":{},"subdivided_collections":[]}',
                encoding="utf-8",
            )
            store = ActivityDiscoveryPolicyStore(path)
            policy = store.read()
            self.assertIs(policy.visibility_mode, ActivityVisibilityMode.AGE_AND_EASIER)
            store.write(policy)
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["visibility_mode"], "age_and_easier")

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