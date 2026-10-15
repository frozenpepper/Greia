"""Real draft-roster checks for Greia's pre-reader Play/Learn organization.

Keep the existing direct catalogue when a truthful five-group partition
cannot cover it; never hide Activities merely to manufacture a submenu.
"""
from __future__ import annotations

import tomllib
import unittest
from pathlib import Path

from greia_launcher.catalogue_view import (
    ActivityCatalogue, ActivityFolder, DISCOVERY_GROUP_IDS, FOLDER_THEME_IDS,
    _CATEGORY_ICONS, _DISCOVERY_ICONS, _DISCOVERY_TRANSLATIONS,
)
from greia_launcher.presentation import _launch_status_label
from greia_platform.activities import ActivityManifest
from greia_platform.activity_discovery import (
    ActivityDiscoveryPolicy, ActivityDiscoveryService, ActivityVisibilityMode,
    ChallengePreference,
)

ROOT = Path(__file__).resolve().parents[1]


def _draft_activities() -> tuple[ActivityManifest, ...]:
    with (ROOT / "build" / "first-party-release-activities.toml").open("rb") as stream:
        release = tomllib.load(stream)
    assert release["release"]["status"] == "draft"
    activities = []
    for item in release["activities"]:
        package = ROOT / "activities" / item["package"]
        with (package / "activity.toml").open("rb") as stream:
            metadata = tomllib.load(stream)
        entry = metadata["activity"]
        presentation = metadata["presentation"]
        education = metadata["education"]
        assert item["activity_id"] == entry["id"]
        activities.append(ActivityManifest(
            activity_id=entry["id"],
            legacy_ids=tuple(entry.get("legacy_ids", ())),
            title_key=entry["title_key"],
            version=entry["version"],
            runtime_type="python",
            api_version="0.1",
            entrypoint=Path("main.py"),
            icon_id="robot",
            categories=tuple(education["categories"]),
            skills=(),
            events=(),
            difficulty=education["difficulty"],
            languages=("it", "en"),
            required_capabilities=(),
            optional_capabilities=(),
            requested_permissions=(),
            storage_schema_version=1,
            root=package,
            launcher_categories=tuple(presentation["categories"]),
            discovery_tags=tuple(presentation["discovery_tags"]),
            recommended_age_min=education.get("recommended_age_min"),
            recommended_age_max=education.get("recommended_age_max"),
        ))
    return tuple(activities)


class LauncherCollectionVisualCurationTests(unittest.TestCase):
    def test_existing_discovery_portals_have_distinct_real_core_illustrations(self) -> None:
        with (ROOT / "assets/catalog/core_icons_v1.toml").open("rb") as stream:
            icons = {item["id"] for item in tomllib.load(stream)["icons"]}
        self.assertEqual(set(_DISCOVERY_ICONS), set(DISCOVERY_GROUP_IDS))
        self.assertEqual(len(set(_DISCOVERY_ICONS.values())), len(DISCOVERY_GROUP_IDS))
        self.assertFalse(set(_DISCOVERY_ICONS.values()) - icons)
        self.assertEqual(set(_DISCOVERY_TRANSLATIONS), set(DISCOVERY_GROUP_IDS))
        self.assertTrue(all(
            _DISCOVERY_TRANSLATIONS[kind].get("it") and
            _DISCOVERY_TRANSLATIONS[kind].get("en")
            for kind in DISCOVERY_GROUP_IDS
        ))
        self.assertNotEqual(_CATEGORY_ICONS["create"], _CATEGORY_ICONS["my_creations"])

    def test_actual_32_candidate_roster_is_honestly_organized_and_not_hidden(self) -> None:
        activities = _draft_activities()
        self.assertEqual(len(activities), 32)
        self.assertEqual(len({a.activity_id for a in activities}), 32)
        catalogue = ActivityCatalogue.from_activities(activities)
        expected = {
            "play": 21,
            "learn": 22,
            "create": 6,
        }
        for collection_id, count in expected.items():
            with self.subTest(collection=collection_id):
                collection = catalogue.collection(collection_id)
                self.assertEqual(len(collection.items), count)
                self.assertEqual(
                    len({item.activity_id for item in collection.items}), count
                )
        # A singleton music destination and unique making/writing activities
        # cannot be meaningfully forced into the current five-group vocabulary.
        self.assertEqual(catalogue.subcollections_for("play"), ())
        self.assertEqual(catalogue.subcollections_for("learn"), ())
        self.assertIn(
            "org.greia.orchestra-animali",
            {item.activity_id for item in catalogue.collection("play").items},
        )
        self.assertNotIn(
            "org.greia.storie-della-mia-voce",
            {item.activity_id for item in catalogue.collection("play").items},
        )
        self.assertNotIn(
            "org.greia.quattro-stagioni",
            {item.activity_id for item in catalogue.collection("play").items},
        )

    def test_filtered_ages_never_lose_or_repeat_a_child_visible_activity(self) -> None:
        source = _draft_activities()
        for age in (3, 4, 5):
            with self.subTest(age=age):
                visible = ActivityDiscoveryService().effective_activities(
                    source,
                    approximate_age=age,
                    challenge_preference=ChallengePreference.AUTOMATIC,
                    policy=ActivityDiscoveryPolicy(
                        visibility_mode=ActivityVisibilityMode.RECOMMENDED_ONLY
                    ),
                )
                catalogue = ActivityCatalogue.from_activities(visible)
                for collection_id in ("play", "learn"):
                    items = catalogue.collection(collection_id).items
                    groups = catalogue.subcollections_for(collection_id)
                    if not groups:
                        continue
                    members = [
                        member.activity_id
                        for group in groups for member in group.items
                    ]
                    self.assertEqual(len(members), len(set(members)))
                    self.assertEqual(
                        set(members), {item.activity_id for item in items}
                    )
                    self.assertTrue(all(len(group.items) >= 2 for group in groups))

    def test_sea_theme_folder_is_mixed_honest_and_one_level(self) -> None:
        """Owner-approved mixed page (2026-10-15): theme folders beside cards."""

        source = _draft_activities()
        sea = {a.activity_id for a in source if "sea" in a.discovery_tags}
        projections = [ActivityCatalogue.from_activities(source)]
        for age in (3, 4, 5):
            visible = ActivityDiscoveryService().effective_activities(
                source,
                approximate_age=age,
                challenge_preference=ChallengePreference.AUTOMATIC,
                policy=ActivityDiscoveryPolicy(
                    visibility_mode=ActivityVisibilityMode.RECOMMENDED_ONLY
                ),
            )
            projections.append(ActivityCatalogue.from_activities(visible))
        for index, catalogue in enumerate(projections):
            for collection in catalogue.home_collections:
                with self.subTest(projection=index, collection=collection.collection_id):
                    entries = catalogue.page_entries(collection.collection_id)
                    reachable: list[str] = []
                    for entry in entries:
                        if isinstance(entry, ActivityFolder):
                            self.assertIn(entry.folder_id, FOLDER_THEME_IDS)
                            self.assertGreaterEqual(len(entry.items), 3)
                            self.assertFalse(any(isinstance(i, ActivityFolder) for i in entry.items))
                            reachable.extend(item.activity_id for item in entry.items)
                        else:
                            reachable.append(entry.activity_id)
                    self.assertEqual(len(reachable), len(set(reachable)))
                    self.assertEqual(
                        set(reachable), {item.activity_id for item in collection.items}
                    )
        unfiltered = projections[0]
        for collection_id in ("play", "explore"):
            members = {a.activity_id for a in unfiltered.collection(collection_id).items} & sea
            if len(members) >= 3:
                folders = unfiltered.folders_for(collection_id)
                self.assertEqual([f.collection_id for f in folders], ["sea"])
                self.assertEqual({a.activity_id for a in folders[0].items}, members)
        self.assertEqual(_DISCOVERY_ICONS["sea"], "sea")

    def test_launch_status_speaks_the_current_ui_language_in_both_art_paths(self) -> None:
        self.assertEqual(_launch_status_label("it"), "Avvio...")
        self.assertEqual(_launch_status_label("it-IT"), "Avvio...")
        self.assertEqual(_launch_status_label("en"), "Starting...")
        self.assertEqual(_launch_status_label("en-US"), "Starting...")


if __name__ == "__main__":
    unittest.main()
