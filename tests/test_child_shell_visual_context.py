from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest import mock

from greia_launcher.child_shell import ProfileVisualActivitySupervisor
from greia_platform.customization import ThemeStore
from greia_platform.theme_snapshot import decode_theme_snapshot
from greia_platform.trust import PackageTrust
from greia_platform.ui_preferences import UiPreferencesStore


ROOT = Path(__file__).resolve().parents[1]


class _Profile:
    def __init__(self, root: Path):
        self.root = root
        self.customization_dir = root / "customization"
        self.customization_dir.mkdir(parents=True)
        self.profile = SimpleNamespace(
            profile_id="0123456789abcdef0123456789abcdef",
            display_name="Mia",
            avatar_id="unicorn",
        )

    def activity_data_dir(self, activity_id: str) -> Path:
        target = self.root / "activities" / activity_id
        target.mkdir(parents=True, exist_ok=True)
        return target


class _Authority:
    package_trust = PackageTrust.BUILT_IN
    sdk_features = frozenset({"display", "pointer"})

    def has_permission(self, permission: str) -> bool:
        return False


class ChildShellVisualContextTests(unittest.TestCase):
    def test_ordinary_activity_gets_resolved_visual_snapshot_without_profile_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            profile = _Profile(Path(temporary) / "profile")
            store = ThemeStore.load(
                ROOT / "runtime" / "theme-defaults.toml",
                profile.customization_dir,
            )
            store.set_colors(background="lavender", accent="grape", text="plum")
            UiPreferencesStore(profile.customization_dir).set_interface_size("large")
            manifest = SimpleNamespace(
                activity_id="org.greia.test",
                root=Path(temporary) / "activity",
                input_profile="pointer",
                api_version="0.1",
            )
            manifest.root.mkdir()

            with mock.patch.dict(
                os.environ,
                {"GREIA_OS_ROOT": str(ROOT)},
                clear=False,
            ):
                environment = ProfileVisualActivitySupervisor._sanitized_environment(
                    manifest,
                    profile,
                    _Authority(),
                    "visual-context-test",
                )

        self.assertNotIn("GREIA_CUSTOMIZATION_DIR", environment)
        self.assertEqual(environment["GREIA_INTERFACE_SIZE"], "large")
        snapshot = decode_theme_snapshot(environment["GREIA_THEME_SNAPSHOT"])
        self.assertEqual(snapshot.preferences.background, "lavender")
        self.assertEqual(snapshot.preferences.accent, "grape")
        self.assertEqual(snapshot.preferences.text, "plum")
        self.assertIsNone(snapshot.wallpaper_path)
        self.assertNotIn(str(profile.customization_dir), environment["GREIA_THEME_SNAPSHOT"])


if __name__ == "__main__":
    unittest.main()
