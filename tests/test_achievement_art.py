from __future__ import annotations

import shutil
import struct
import tempfile
import unittest
from pathlib import Path

from greia_platform.achievement_art import (
    ActivityAchievementArtError,
    load_activity_achievement_emblems,
)
from greia_platform.achievements import AchievementPolicy, AchievementPolicyError
from greia_platform.activities import ActivityRegistry, RuntimeCatalogue
from greia_platform.trust import ActivitySource, PackageTrust


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_PATH = PROJECT_ROOT / "runtime" / "child-runtime.toml"
ACHIEVEMENT_POLICY = PROJECT_ROOT / "runtime" / "achievement-policy.toml"


def _fake_png_header(width: int, height: int) -> bytes:
    return (
        b"\x89PNG\r\n\x1a\n"
        + b"\x00\x00\x00\x0d"
        + b"IHDR"
        + struct.pack(">II", width, height)
    )


class AchievementArtContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runtime = RuntimeCatalogue.load(RUNTIME_PATH)
        source = ActivitySource(
            PROJECT_ROOT / "activities",
            trust=PackageTrust.BUILT_IN,
            source_id="builtin",
        )
        self.activities = ActivityRegistry([source], self.runtime).discover()
        self.by_id = {item.activity_id: item for item in self.activities}

    def test_current_themed_activities_contribute_one_safe_emblem(self) -> None:
        for activity_id in (
            "org.greia.clinica-cuccioli",
            "org.greia.memory-meraviglie",
            "org.greia.costruiamo-ponti",
        ):
            emblems = load_activity_achievement_emblems(self.by_id[activity_id])
            self.assertEqual(len(emblems), 1)
            self.assertEqual(emblems[0].emblem_id, "activity")
            self.assertEqual(emblems[0].asset_path.name, "icon.png")
            self.assertEqual(emblems[0].width, emblems[0].height)
            self.assertLessEqual(emblems[0].byte_size, 512 * 1024)

    def test_platform_policy_explicitly_admits_activity_art(self) -> None:
        policy = AchievementPolicy.load(ACHIEVEMENT_POLICY, self.activities)

        clinic = policy.get("greia.care.first-friend")
        memory = policy.get("greia.memory.first-finish")
        bridges = policy.get("greia.building.bridge-builder")
        global_star = policy.get("greia.stars.handful")

        self.assertIsNotNone(clinic.activity_emblem)
        self.assertIsNotNone(memory.activity_emblem)
        self.assertIsNotNone(bridges.activity_emblem)
        assert clinic.activity_emblem is not None
        assert memory.activity_emblem is not None
        assert bridges.activity_emblem is not None
        self.assertEqual(
            clinic.activity_emblem.activity_id,
            "org.greia.clinica-cuccioli",
        )
        self.assertEqual(
            memory.activity_emblem.activity_id,
            "org.greia.memory-meraviglie",
        )
        self.assertEqual(
            bridges.activity_emblem.activity_id,
            "org.greia.costruiamo-ponti",
        )
        self.assertIsNone(global_star.activity_emblem)

    def test_policy_catalogue_is_fifteen_existing_event_badges(self) -> None:
        # Loading validates every event_count/best_score criterion against the
        # Activity's own declared events, so no badge depends on a new event.
        policy = AchievementPolicy.load(ACHIEVEMENT_POLICY, self.activities)
        definitions = policy.achievements
        self.assertEqual(len(definitions), 15)
        self.assertEqual(len({item.achievement_id for item in definitions}), 15)
        self.assertEqual([item.achievement_id for item in definitions if item.secret], [
            "greia.stars.constellation"
        ])
        new_badges = {
            "greia.creation.first-garden": ("org.greia.shape-garden", "creation.completed", "event_count", 1),
            "greia.creation.first-postcard": ("org.greia.posta-di-leo", "postcard.created", "event_count", 1),
            "greia.creation.my-voice": ("org.greia.storie-della-mia-voce", "voice.story_saved", "event_count", 1),
            "greia.music.first-concert": ("org.greia.orchestra-animali", "band.concert_completed", "event_count", 1),
            "greia.maze.first-maze": ("org.greia.labirinto-magico", "maze.completed", "event_count", 1),
            "greia.maze.star-hunter": ("org.greia.labirinto-magico", "maze.star_collected", "event_count", 15),
            "greia.flight.first-course": ("org.greia.volo-draghetto", "flight.course_completed", "event_count", 1),
            "greia.sea.dolphin-explorer": ("org.greia.viaggio-delfino", "dolphin.journey_score", "best_score", 15),
        }
        for achievement_id, (activity_id, event_id, kind, threshold) in new_badges.items():
            with self.subTest(achievement_id):
                definition = policy.get(achievement_id)
                (criterion,) = definition.criteria
                self.assertEqual(
                    (criterion.activity_id, criterion.event_id, criterion.kind, criterion.threshold),
                    (activity_id, event_id, kind, threshold),
                )
                declared = {event.event_id for event in self.by_id[activity_id].events}
                self.assertIn(event_id, declared)
        for definition in definitions:
            with self.subTest(definition.achievement_id):
                # Bronze always means "the first time" so the first badge can
                # arrive in a child's first session.
                if definition.tier == "bronze" and definition.criteria[0].kind == "event_count":
                    self.assertEqual(definition.criteria[0].threshold, 1)
                for text in (definition.title, definition.description, definition.locked_hint):
                    locales = dict(text.values)
                    self.assertLessEqual({"en", "it", "es", "fr"}, set(locales))
                    self.assertNotIn("/", locales["en"])

    def test_voice_badge_admits_the_declared_voice_emblem(self) -> None:
        policy = AchievementPolicy.load(ACHIEVEMENT_POLICY, self.activities)
        voice = policy.get("greia.creation.my-voice")
        assert voice.activity_emblem is not None
        self.assertEqual(voice.activity_emblem.emblem_id, "voice")

    def test_activity_emblem_path_escape_is_rejected_at_art_boundary(self) -> None:
        with self._copy_clinic() as root:
            manifest_path = root / "activity.toml"
            text = manifest_path.read_text(encoding="utf-8").replace(
                'asset = "assets/icon.png"',
                'asset = "../icon.png"',
            )
            manifest_path.write_text(text, encoding="utf-8")

            manifest = ActivityRegistry([root.parent], self.runtime).validate_package(root)
            with self.assertRaisesRegex(
                ActivityAchievementArtError,
                "safe relative path",
            ):
                load_activity_achievement_emblems(manifest)

    def test_activity_emblem_must_be_png_by_extension(self) -> None:
        with self._copy_clinic() as root:
            manifest_path = root / "activity.toml"
            manifest_path.write_text(
                manifest_path.read_text(encoding="utf-8").replace(
                    'asset = "assets/icon.png"',
                    'asset = "assets/emblem.jpg"',
                ),
                encoding="utf-8",
            )
            (root / "assets" / "emblem.jpg").write_bytes(b"not an image")
            manifest = ActivityRegistry([root.parent], self.runtime).validate_package(root)
            with self.assertRaisesRegex(ActivityAchievementArtError, "PNG file"):
                load_activity_achievement_emblems(manifest)

    def test_activity_emblem_png_signature_is_validated(self) -> None:
        with self._copy_clinic() as root:
            manifest_path = root / "activity.toml"
            manifest_path.write_text(
                manifest_path.read_text(encoding="utf-8").replace(
                    'asset = "assets/icon.png"',
                    'asset = "assets/broken.png"',
                ),
                encoding="utf-8",
            )
            (root / "assets" / "broken.png").write_bytes(b"definitely not png")
            manifest = ActivityRegistry([root.parent], self.runtime).validate_package(root)
            with self.assertRaisesRegex(ActivityAchievementArtError, "valid PNG"):
                load_activity_achievement_emblems(manifest)

    def test_activity_emblem_dimensions_are_bounded(self) -> None:
        with self._copy_clinic() as root:
            manifest_path = root / "activity.toml"
            manifest_path.write_text(
                manifest_path.read_text(encoding="utf-8").replace(
                    'asset = "assets/icon.png"',
                    'asset = "assets/tiny.png"',
                ),
                encoding="utf-8",
            )
            (root / "assets" / "tiny.png").write_bytes(_fake_png_header(16, 16))
            manifest = ActivityRegistry([root.parent], self.runtime).validate_package(root)
            with self.assertRaisesRegex(ActivityAchievementArtError, "dimensions"):
                load_activity_achievement_emblems(manifest)

    def test_activity_emblem_must_be_square(self) -> None:
        with self._copy_clinic() as root:
            manifest_path = root / "activity.toml"
            manifest_path.write_text(
                manifest_path.read_text(encoding="utf-8").replace(
                    'asset = "assets/icon.png"',
                    'asset = "assets/wide.png"',
                ),
                encoding="utf-8",
            )
            (root / "assets" / "wide.png").write_bytes(_fake_png_header(64, 48))
            manifest = ActivityRegistry([root.parent], self.runtime).validate_package(root)
            with self.assertRaisesRegex(ActivityAchievementArtError, "square"):
                load_activity_achievement_emblems(manifest)

    def test_duplicate_activity_emblem_ids_are_rejected(self) -> None:
        with self._copy_clinic() as root:
            manifest_path = root / "activity.toml"
            text = manifest_path.read_text(encoding="utf-8").replace(
                'emblems = [\n  { id = "activity", asset = "assets/icon.png" },\n]',
                'emblems = [\n'
                '  { id = "activity", asset = "assets/icon.png" },\n'
                '  { id = "activity", asset = "assets/icon.png" },\n'
                ']',
            )
            manifest_path.write_text(text, encoding="utf-8")
            manifest = ActivityRegistry([root.parent], self.runtime).validate_package(root)
            with self.assertRaisesRegex(ActivityAchievementArtError, "duplicate"):
                load_activity_achievement_emblems(manifest)

    def test_activity_emblem_symlink_is_rejected_by_art_boundary(self) -> None:
        with self._copy_clinic() as root:
            # Obtain a valid issued manifest before adding the symlink so this
            # test exercises achievement_art independently of the registry's
            # broader package-wide symlink rejection.
            manifest = ActivityRegistry([root.parent], self.runtime).validate_package(root)
            link = root / "assets" / "linked-emblem.png"
            try:
                link.symlink_to(root / "assets" / "icon.png")
            except OSError:
                self.skipTest("symlinks unavailable")
            manifest_path = root / "activity.toml"
            manifest_path.write_text(
                manifest_path.read_text(encoding="utf-8").replace(
                    'asset = "assets/icon.png"',
                    'asset = "assets/linked-emblem.png"',
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ActivityAchievementArtError, "symlink"):
                load_activity_achievement_emblems(manifest)

    def test_platform_policy_cannot_reference_undeclared_activity_emblem(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "achievement-policy.toml"
            path.write_text(
                "schema_version = 1\n"
                "default_locale = \"en\"\n\n"
                "[[achievements]]\n"
                "id = \"greia.test.bad-art\"\n"
                "category = \"test\"\n"
                "tier = \"bronze\"\n"
                "icon_id = \"yellow_star\"\n"
                "secret = false\n"
                "art = { activity_id = \"org.greia.clinica-cuccioli\", emblem_id = \"missing\" }\n"
                "title = { en = \"Test\" }\n"
                "description = { en = \"Test\" }\n"
                "locked_hint = { en = \"Test\" }\n\n"
                "[[achievements.criteria]]\n"
                "type = \"event_count\"\n"
                "activity_id = \"org.greia.clinica-cuccioli\"\n"
                "event_id = \"vet.patient_healed\"\n"
                "threshold = 1\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                AchievementPolicyError,
                "undeclared Activity emblem",
            ):
                AchievementPolicy.load(path, self.activities)

    def _copy_clinic(self):
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name) / "clinica_cuccioli"
        shutil.copytree(PROJECT_ROOT / "activities" / "clinica_cuccioli", root)

        class Context:
            def __enter__(self_nonlocal):
                return root

            def __exit__(self_nonlocal, *args: object):
                temporary.cleanup()

        return Context()


if __name__ == "__main__":
    unittest.main()
