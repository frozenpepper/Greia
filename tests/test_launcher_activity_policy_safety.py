from __future__ import annotations

import inspect
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from greia_launcher.activity_policy_presentation import (
    ActivityPolicyEnforcementMixin,
    DirectActivityPolicyDiscoveryMixin,
    PolicyEnforcedAdaptiveActivityDiscoveryMixin,
)
from greia_launcher.adaptive_discovery_presentation import AdaptiveActivityDiscoveryMixin
from greia_launcher.catalogue_view import ALL_ACTIVITIES_ID, ActivityCatalogue
from greia_launcher.child_shell import GreiaChildShell
from greia_launcher.trusted_presentation import TrustedGreiaLauncherPresentation
from greia_platform.activities import ActivityManifest
from greia_platform.activity_discovery import (
    ActivityDiscoveryPolicy,
    ActivityDiscoveryPolicyStore,
    ActivityVisibilityMode,
    ActivityVisibilityOverride,
    ChallengePreference,
)


def _activity(
    index: int,
    *,
    difficulty: int = 3,
    age_min: int | None = None,
    age_max: int | None = None,
    tags: tuple[str, ...] = (),
) -> ActivityManifest:
    return ActivityManifest(
        activity_id=f"org.greia.policy-safety-{index}",
        legacy_ids=(),
        title_key=f"activity.policy_safety_{index}.title",
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
        launcher_categories=("create",),
        discovery_tags=tags,
        recommended_age_min=age_min,
        recommended_age_max=age_max,
    )


def _profile_context(policy_path: Path, *, age: int | None = 3):
    return SimpleNamespace(
        activity_discovery_policy_path=policy_path,
        profile=SimpleNamespace(
            profile_id="child-policy-safety",
            approximate_age=age,
            challenge_preference=ChallengePreference.AUTOMATIC,
        ),
    )


class _HarnessBase:
    def __init__(self, activities: tuple[ActivityManifest, ...]) -> None:
        self._activities = activities
        self._active_profile = None
        self._active_locale = "en"
        self._catalogue = ActivityCatalogue.from_activities(activities)
        self._category_id = ALL_ACTIVITIES_ID
        self._selected = 0
        self._activity_scroll_start = 0
        self._cached_activities_key = None
        self._cached_activities_surface = None
        self._cached_activities_targets: list[object] = []
        self._tile_surface_cache: dict[object, object] = {}
        self._backdrop_cache: dict[object, object] = {}
        self._catalogue_error = False

    def _activate_profile(self, profile, pygame) -> None:
        self._active_profile = profile

    def _logout(self, pygame) -> None:
        self._active_profile = None

    def _rescan_if_due(self) -> bool:
        return False

    def _rescan_activities(self) -> bool:
        return False

    def _rescan_profiles(self) -> bool:
        return False


class _AdaptiveHarness(
    PolicyEnforcedAdaptiveActivityDiscoveryMixin,
    _HarnessBase,
):
    pass


class _DirectHarness(
    DirectActivityPolicyDiscoveryMixin,
    _HarnessBase,
):
    pass


def _visible_ids(harness) -> tuple[str, ...]:
    return tuple(
        item.activity_id
        for item in harness._catalogue.collection(ALL_ACTIVITIES_ID).items
    )


class LauncherActivityPolicySafetyTests(unittest.TestCase):
    def test_installed_normal_and_fallback_launchers_share_policy_boundary(self) -> None:
        self.assertTrue(issubclass(GreiaChildShell, ActivityPolicyEnforcementMixin))
        self.assertTrue(
            issubclass(TrustedGreiaLauncherPresentation, ActivityPolicyEnforcementMixin)
        )
        self.assertTrue(
            issubclass(
                GreiaChildShell,
                PolicyEnforcedAdaptiveActivityDiscoveryMixin,
            )
        )
        self.assertTrue(
            issubclass(
                TrustedGreiaLauncherPresentation,
                DirectActivityPolicyDiscoveryMixin,
            )
        )

    def test_adaptive_presentation_owns_no_parent_policy_authority(self) -> None:
        module = inspect.getmodule(AdaptiveActivityDiscoveryMixin)
        self.assertIsNotNone(module)
        assert module is not None
        for name in (
            "ActivityDiscoveryError",
            "ActivityDiscoveryPolicy",
            "ActivityDiscoveryPolicyStore",
            "ActivityDiscoveryService",
        ):
            with self.subTest(imported_authority=name):
                self.assertNotIn(name, vars(module))

        for method in (
            "_reload_effective_catalogue",
            "_policy_file_token",
            "_rescan_if_due",
            "_rescan_activities",
            "_rescan_profiles",
        ):
            with self.subTest(adaptive_method=method):
                self.assertNotIn(method, AdaptiveActivityDiscoveryMixin.__dict__)

        for method in (
            "_activate_profile",
            "_logout",
            "_rescan_if_due",
            "_rescan_activities",
            "_rescan_profiles",
        ):
            with self.subTest(policy_lifecycle=method):
                self.assertIn(method, ActivityPolicyEnforcementMixin.__dict__)

        for method in (
            "_activate_profile",
            "_logout",
            "_rescan_if_due",
            "_rescan_activities",
            "_rescan_profiles",
        ):
            with self.subTest(direct_duplicate=method):
                self.assertNotIn(method, DirectActivityPolicyDiscoveryMixin.__dict__)

    def test_parent_always_hide_filters_both_launcher_paths(self) -> None:
        first = _activity(1, age_min=3, age_max=8)
        hidden = _activity(2, age_min=3, age_max=8)
        activities = (first, hidden)
        with tempfile.TemporaryDirectory() as temporary:
            policy_path = Path(temporary) / "activity-discovery.json"
            ActivityDiscoveryPolicyStore(policy_path).write(
                ActivityDiscoveryPolicy(
                    overrides=(
                        (
                            hidden.activity_id,
                            ActivityVisibilityOverride.ALWAYS_HIDE,
                        ),
                    )
                )
            )
            context = _profile_context(policy_path)
            for harness_type in (_AdaptiveHarness, _DirectHarness):
                with self.subTest(harness=harness_type.__name__):
                    harness = harness_type(activities)
                    harness._activate_profile(context, None)
                    self.assertEqual(_visible_ids(harness), (first.activity_id,))

    def test_restrictive_age_policy_filters_trusted_fallback_too(self) -> None:
        suitable = _activity(1, age_min=3, age_max=5)
        older = _activity(2, age_min=6, age_max=9)
        activities = (suitable, older)
        with tempfile.TemporaryDirectory() as temporary:
            policy_path = Path(temporary) / "activity-discovery.json"
            ActivityDiscoveryPolicyStore(policy_path).write(
                ActivityDiscoveryPolicy(
                    visibility_mode=ActivityVisibilityMode.RECOMMENDED_ONLY
                )
            )
            harness = _DirectHarness(activities)
            harness._activate_profile(_profile_context(policy_path, age=3), None)
            self.assertEqual(_visible_ids(harness), (suitable.activity_id,))

    def test_missing_policy_file_remains_legitimate_show_all_default(self) -> None:
        activities = (
            _activity(1, age_min=3, age_max=8),
            _activity(2, age_min=6, age_max=9),
        )
        with tempfile.TemporaryDirectory() as temporary:
            policy_path = Path(temporary) / "missing-policy.json"
            context = _profile_context(policy_path)
            for harness_type in (_AdaptiveHarness, _DirectHarness):
                with self.subTest(harness=harness_type.__name__):
                    harness = harness_type(activities)
                    harness._activate_profile(context, None)
                    self.assertEqual(
                        set(_visible_ids(harness)),
                        {item.activity_id for item in activities},
                    )
                    self.assertFalse(harness._catalogue_error)

    def test_malformed_policy_exposes_no_activities_in_either_launcher(self) -> None:
        activities = (
            _activity(1, age_min=3, age_max=8),
            _activity(2, age_min=3, age_max=8),
        )
        with tempfile.TemporaryDirectory() as temporary:
            policy_path = Path(temporary) / "activity-discovery.json"
            policy_path.write_text("{this is not valid json", encoding="utf-8")
            context = _profile_context(policy_path)
            for harness_type in (_AdaptiveHarness, _DirectHarness):
                with self.subTest(harness=harness_type.__name__):
                    harness = harness_type(activities)
                    harness._activate_profile(context, None)
                    self.assertEqual(_visible_ids(harness), ())
                    self.assertTrue(harness._catalogue_error)
                    self.assertTrue(harness._activity_policy_error)

    def test_unsupported_policy_schema_exposes_no_activities(self) -> None:
        activities = (_activity(1, age_min=3, age_max=8),)
        with tempfile.TemporaryDirectory() as temporary:
            policy_path = Path(temporary) / "activity-discovery.json"
            policy_path.write_text(
                '{"schema_version":999,"visibility_mode":"show_all"}',
                encoding="utf-8",
            )
            context = _profile_context(policy_path)
            for harness_type in (_AdaptiveHarness, _DirectHarness):
                with self.subTest(harness=harness_type.__name__):
                    harness = harness_type(activities)
                    harness._activate_profile(context, None)
                    self.assertEqual(_visible_ids(harness), ())

    def test_symlink_policy_exposes_no_activities(self) -> None:
        activities = (_activity(1, age_min=3, age_max=8),)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "real-policy.json"
            ActivityDiscoveryPolicyStore(target).write(ActivityDiscoveryPolicy())
            policy_path = root / "activity-discovery.json"
            try:
                policy_path.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unavailable on this platform")
            context = _profile_context(policy_path)
            for harness_type in (_AdaptiveHarness, _DirectHarness):
                with self.subTest(harness=harness_type.__name__):
                    harness = harness_type(activities)
                    harness._activate_profile(context, None)
                    self.assertEqual(_visible_ids(harness), ())

    def test_repair_after_corruption_clears_policy_error_and_restores_projection(self) -> None:
        activities = (
            _activity(1, age_min=3, age_max=8),
            _activity(2, age_min=3, age_max=8),
        )
        with tempfile.TemporaryDirectory() as temporary:
            policy_path = Path(temporary) / "activity-discovery.json"
            context = _profile_context(policy_path)
            for harness_type in (_AdaptiveHarness, _DirectHarness):
                with self.subTest(harness=harness_type.__name__):
                    policy_path.write_text("broken", encoding="utf-8")
                    harness = harness_type(activities)
                    harness._activate_profile(context, None)
                    self.assertEqual(_visible_ids(harness), ())
                    self.assertTrue(harness._activity_policy_error)
                    rejected_token = harness._discovery_policy_token

                    ActivityDiscoveryPolicyStore(policy_path).write(
                        ActivityDiscoveryPolicy()
                    )
                    self.assertNotEqual(
                        harness._policy_file_token(),
                        rejected_token,
                    )
                    self.assertTrue(harness._rescan_if_due())
                    self.assertEqual(
                        set(_visible_ids(harness)),
                        {item.activity_id for item in activities},
                    )
                    self.assertFalse(harness._activity_policy_error)
                    self.assertFalse(harness._catalogue_error)

    def test_atomic_replacement_during_read_cannot_acknowledge_stale_policy(self) -> None:
        first = _activity(1, age_min=3, age_max=8)
        hidden = _activity(2, age_min=3, age_max=8)
        activities = (first, hidden)
        original_read = ActivityDiscoveryPolicyStore.read

        with tempfile.TemporaryDirectory() as temporary:
            policy_path = Path(temporary) / "activity-discovery.json"
            store = ActivityDiscoveryPolicyStore(policy_path)
            store.write(ActivityDiscoveryPolicy())
            replacement = ActivityDiscoveryPolicy(
                overrides=(
                    (hidden.activity_id, ActivityVisibilityOverride.ALWAYS_HIDE),
                )
            )
            calls = 0

            def racing_read(candidate_store: ActivityDiscoveryPolicyStore):
                nonlocal calls
                policy = original_read(candidate_store)
                calls += 1
                if calls == 1:
                    candidate_store.write(replacement)
                return policy

            for harness_type in (_AdaptiveHarness, _DirectHarness):
                with self.subTest(harness=harness_type.__name__):
                    calls = 0
                    store.write(ActivityDiscoveryPolicy())
                    harness = harness_type(activities)
                    with patch.object(
                        ActivityDiscoveryPolicyStore,
                        "read",
                        autospec=True,
                        side_effect=racing_read,
                    ):
                        harness._activate_profile(_profile_context(policy_path), None)
                    self.assertGreaterEqual(calls, 2)
                    self.assertEqual(_visible_ids(harness), (first.activity_id,))
                    self.assertEqual(
                        harness._discovery_policy_token,
                        harness._policy_file_token(),
                    )

    def test_adaptive_hysteresis_never_writes_parent_policy(self) -> None:
        activities = tuple(
            _activity(
                index,
                age_min=3,
                age_max=8,
                tags=("drawing",) if index < 6 else ("writing",),
            )
            for index in range(12)
        )
        with tempfile.TemporaryDirectory() as temporary:
            policy_path = Path(temporary) / "activity-discovery.json"
            store = ActivityDiscoveryPolicyStore(policy_path)
            store.write(ActivityDiscoveryPolicy())
            harness = _AdaptiveHarness(activities)

            with patch.object(
                ActivityDiscoveryPolicyStore,
                "write",
                autospec=True,
                side_effect=AssertionError(
                    "child Shell must not write presentation state into Parent policy"
                ),
            ) as policy_write:
                harness._activate_profile(_profile_context(policy_path), None)

            policy_write.assert_not_called()
            self.assertTrue(harness._catalogue.subdivided_collection_ids)
            self.assertTrue(harness._adaptive_subdivision_state)
            self.assertEqual(store.read().subdivided_collections, ())

    def test_parent_change_after_adaptive_projection_is_not_clobbered(self) -> None:
        first = _activity(1, age_min=3, age_max=8)
        hidden = _activity(2, age_min=3, age_max=8)
        activities = (first, hidden)
        with tempfile.TemporaryDirectory() as temporary:
            policy_path = Path(temporary) / "activity-discovery.json"
            store = ActivityDiscoveryPolicyStore(policy_path)
            store.write(ActivityDiscoveryPolicy())
            harness = _AdaptiveHarness(activities)
            harness._activate_profile(_profile_context(policy_path), None)
            original_token = harness._discovery_policy_token

            store.write(
                ActivityDiscoveryPolicy(
                    overrides=(
                        (hidden.activity_id, ActivityVisibilityOverride.ALWAYS_HIDE),
                    )
                )
            )
            self.assertNotEqual(harness._policy_file_token(), original_token)
            self.assertTrue(harness._rescan_if_due())
            self.assertEqual(_visible_ids(harness), (first.activity_id,))
            self.assertEqual(
                store.read().override_for(hidden.activity_id),
                ActivityVisibilityOverride.ALWAYS_HIDE,
            )

    def test_trusted_fallback_keeps_catalogue_direct_not_adaptive(self) -> None:
        activities = tuple(
            _activity(
                index,
                age_min=3,
                age_max=8,
                tags=("drawing",) if index < 6 else ("writing",),
            )
            for index in range(12)
        )
        with tempfile.TemporaryDirectory() as temporary:
            policy_path = Path(temporary) / "activity-discovery.json"
            ActivityDiscoveryPolicyStore(policy_path).write(ActivityDiscoveryPolicy())
            harness = _DirectHarness(activities)
            harness._activate_profile(_profile_context(policy_path), None)
            self.assertEqual(harness._catalogue.subcollections, ())
            self.assertEqual(len(_visible_ids(harness)), len(activities))


if __name__ == "__main__":
    unittest.main()
