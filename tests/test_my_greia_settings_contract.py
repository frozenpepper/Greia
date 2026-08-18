from __future__ import annotations

from pathlib import Path
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]
ACTIVITY_ROOT = ROOT / "activities" / "workshop_settings"


class MyGreiaSettingsContractTests(unittest.TestCase):
    def test_manifest_keeps_stable_privileged_identity_and_child_safe_scope(self) -> None:
        with (ACTIVITY_ROOT / "activity.toml").open("rb") as handle:
            raw = tomllib.load(handle)
        self.assertEqual(raw["activity"]["id"], "org.greia.workshop-settings")
        self.assertEqual(raw["activity"]["title_key"], "My Greia")
        self.assertEqual(raw["presentation"]["categories"], ["my_greia"])
        self.assertEqual(raw["input"]["profile"], "pointer")
        self.assertEqual(
            set(raw["permissions"]["requested"]),
            {
                "customization.manage",
                "profile.manage_own",
                "removable_media.read",
            },
        )

    def test_activity_is_visual_first_and_uses_platform_lifecycle(self) -> None:
        source = (ACTIVITY_ROOT / "main.py").read_text(encoding="utf-8")
        for mode in ("colors", "wallpapers", "size", "avatar"):
            self.assertIn(f'"{mode}"', source)
        self.assertIn("AdaptiveGridPolicy", source)
        self.assertIn("mark_activity_ready()", source)
        self.assertIn("activity_stop_requested()", source)
        self.assertIn("set_interface_size", source)
        self.assertNotIn('"close_button"', source)
        self.assertNotIn("subprocess", source)
        self.assertNotIn("os.system", source)

    def test_installed_x_session_runs_profile_aware_child_shell(self) -> None:
        wrapper = (
            ROOT
            / "build"
            / "overlay"
            / "usr"
            / "local"
            / "lib"
            / "greia-os"
            / "greia-x-session"
        ).read_text(encoding="utf-8")
        self.assertIn("-m greia_launcher.child_shell", wrapper)
        self.assertNotIn("-m greia_launcher.presentation\n", wrapper)


if __name__ == "__main__":
    unittest.main()
