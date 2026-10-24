"""Parent clients get localized Activity titles and the installed OS identity."""
import tempfile
import json
import unittest
from pathlib import Path

from greia_platform import localization
from greia_platform.health import installed_os_identity
from greia_platform.localization import activity_titles

REPO = Path(__file__).resolve().parents[1]


class ActivityTitlesTests(unittest.TestCase):
    def setUp(self):
        localization._activity_titles_cache.clear()

    def test_titles_come_from_each_declared_bundle(self):
        root = REPO / "activities" / "baia_delle_orche"
        titles = activity_titles(root, "activity.baia_delle_orche.title", ("it", "en"))
        self.assertEqual(titles["it"], "Baia delle Orche")
        self.assertEqual(titles["en"], "Orca Bay")

    def test_missing_bundle_is_skipped_not_fatal(self):
        root = REPO / "activities" / "baia_delle_orche"
        titles = activity_titles(root, "activity.baia_delle_orche.title", ("it", "xx"))
        self.assertEqual(set(titles), {"it"})


class OsIdentityTests(unittest.TestCase):
    def test_reads_build_info_and_image_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            info = Path(tmp) / "build-info"
            info.write_text("GREIA_OS_VERSION=0.13.0-phase0-dev\nPIP_BUILD_PROFILE=legacy-x86-i686-dev\nPIP_PLATFORM_FAMILY=legacy-x86\n")
            profile = Path(tmp) / "image-profile.json"
            profile.write_text('{"base": {"architecture": "i386"}}')
            identity = installed_os_identity(info, profile)
        self.assertEqual(identity["version"], "0.13.0-phase0-dev")
        self.assertEqual(identity["profile"], "legacy-x86-i686-dev")
        self.assertEqual(identity["architecture"], "i386")

    def test_absent_records_are_none(self):
        identity = installed_os_identity(Path("/nonexistent/a"), Path("/nonexistent/b"))
        self.assertIsNone(identity["version"])

    def test_finalized_release_identity_is_projected_for_parent_clients(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            release = root / "release-identity.json"
            release.write_text(
                json.dumps(
                    {
                        "architecture": "i386",
                        "board": "acer",
                        "platform_family": "legacy-x86",
                        "profile": "legacy-x86-i686-ab",
                        "release_id": "greia-0.14.0",
                        "role": "system",
                        "slot": "B",
                        "version": "0.14.0",
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n",
                encoding="utf-8",
            )
            identity = installed_os_identity(
                root / "build-info",
                root / "image-profile.json",
                release,
            )
        self.assertEqual(identity["version"], "0.14.0")
        self.assertEqual(identity["release_id"], "greia-0.14.0")
        self.assertEqual(identity["profile"], "legacy-x86-i686-ab")
        self.assertEqual(identity["platform_family"], "legacy-x86")
        self.assertEqual(identity["architecture"], "i386")
        self.assertEqual(identity["board"], "acer")
        self.assertEqual(identity["channel"], "stable")
        self.assertEqual(identity["current_slot"], "B")

    def test_single_root_build_info_remains_the_identity_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            info = root / "build-info"
            info.write_text(
                "GREIA_OS_VERSION=0.13.0\n"
                "PIP_BUILD_PROFILE=legacy-x86-i686\n"
                "PIP_PLATFORM_FAMILY=legacy-x86\n",
                encoding="utf-8",
            )
            profile = root / "image-profile.json"
            profile.write_text('{"base":{"architecture":"i386"}}', encoding="utf-8")
            identity = installed_os_identity(info, profile, root / "missing-release.json")
        self.assertEqual(identity["version"], "0.13.0")
        self.assertEqual(identity["profile"], "legacy-x86-i686")
        self.assertEqual(identity["platform_family"], "legacy-x86")
        self.assertEqual(identity["architecture"], "i386")
        self.assertIsNone(identity["release_id"])

    def test_invalid_finalized_identity_does_not_fall_back_to_stale_build_info(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            info = root / "build-info"
            info.write_text(
                "GREIA_OS_VERSION=0.12.0\n"
                "GREIA_RELEASE_ID=greia-0.12.0\n"
                "GREIA_SYSTEM_BOARD=acer\n",
                encoding="utf-8",
            )
            profile = root / "image-profile.json"
            profile.write_text('{"base":{"architecture":"i386"}}', encoding="utf-8")
            release = root / "release-identity.json"
            release.write_text("{invalid", encoding="utf-8")
            identity = installed_os_identity(info, profile, release)
        self.assertIsNone(identity["version"])
        self.assertIsNone(identity["release_id"])
        self.assertIsNone(identity["board"])
        self.assertIsNotNone(identity["identity_error"])


if __name__ == "__main__":
    unittest.main()
