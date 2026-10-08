"""Source-level product organization for Greia Create and My Creations.

The release roster stays draft. These checks read the actual candidate
Activity declarations; no hard-coded runtime catalogue or new taxonomy.
"""
from __future__ import annotations

import tomllib
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from greia_launcher.child_shell import GreiaChildShell
from greia_launcher.collection_home_presentation import CollectionFirstHomeMixin
from greia_platform.ui_core import Collection


ROOT = Path(__file__).resolve().parents[1]
RELEASE_POLICY = ROOT / "build" / "first-party-release-activities.toml"

# Six existing, real creation workflows. Exploration, caregiving, spatial
# puzzles and stacking stay accessible under their honest child intents.
CREATE_ANCHORS = frozenset({
    "painting",
    "shape_garden",
    "posta_di_leo",
    "writing",
    "storie_della_mia_voce",
    "teatrino_fiabe",
})
INTENT_REPAIRS = {
    "acquario_magico": ("explore",),
    "cucciolo_mio": ("play",),
    "specchi_magici": ("learn",),
    "torre_forme": ("play",),
}


class ChildHomeCreationOrganizationTests(unittest.TestCase):
    def test_draft_release_candidates_present_six_genuine_creators(self) -> None:
        with RELEASE_POLICY.open("rb") as stream:
            release = tomllib.load(stream)
        self.assertEqual(release["release"]["status"], "draft")
        packages = [entry["package"] for entry in release["activities"]]
        self.assertEqual(len(packages), 32)
        self.assertEqual(len(set(packages)), len(packages))

        actual_create = set()
        for name in packages:
            with (ROOT / "activities" / name / "activity.toml").open("rb") as stream:
                activity = tomllib.load(stream)
            cats = tuple(activity["presentation"]["categories"])
            self.assertTrue(cats, name)
            if "create" in cats:
                actual_create.add(name)
            if name in INTENT_REPAIRS:
                self.assertEqual(cats, INTENT_REPAIRS[name])
        self.assertEqual(actual_create, CREATE_ANCHORS)

    def test_my_creations_always_follows_create_with_distinct_core_icon(self) -> None:
        shell = object.__new__(GreiaChildShell)
        shell._active_profile = object()
        root = (
            Collection("create", (object(),), icon_id="palette"),
            Collection("play", (object(),), icon_id="puzzle_pieces"),
            Collection("learn", (object(),), icon_id="book"),
        )
        with patch.object(CollectionFirstHomeMixin, "_home_collections", return_value=root):
            home = shell._home_collections()
        self.assertEqual(
            [item.collection_id for item in home],
            ["create", "my_creations", "play", "learn"],
        )
        self.assertEqual(home[1].icon_id, "backpack")
        self.assertNotEqual(home[0].icon_id, home[1].icon_id)
        self.assertEqual(home[1].items, ())

    def test_compact_landscape_home_avoids_six_vertical_rows(self) -> None:
        shell = object.__new__(GreiaChildShell)
        for size, columns in (
            ((480, 320), 3),
            ((640, 360), 3),
            ((800, 480), 2),
            ((1024, 600), 3),
        ):
            with self.subTest(size=size):
                surface = SimpleNamespace(
                    get_width=lambda: size[0],
                    get_height=lambda: size[1],
                )
                pygame = SimpleNamespace(
                    display=SimpleNamespace(get_surface=lambda: surface),
                )
                self.assertEqual(shell._home_columns(pygame), columns)
                rows = (6 + columns - 1) // columns
                self.assertLessEqual(rows, 3)

    def test_saved_work_stays_visible_when_parent_hides_all_create_apps(self) -> None:
        shell = object.__new__(GreiaChildShell)
        shell._active_profile = object()
        root = (Collection("play", (object(),), icon_id="puzzle_pieces"),)
        with patch.object(CollectionFirstHomeMixin, "_home_collections", return_value=root):
            home = shell._home_collections()
        self.assertEqual([item.collection_id for item in home], ["my_creations", "play"])
        shell._active_profile = None
        with patch.object(CollectionFirstHomeMixin, "_home_collections", return_value=root):
            self.assertEqual(shell._home_collections(), root)


if __name__ == "__main__":
    unittest.main()
