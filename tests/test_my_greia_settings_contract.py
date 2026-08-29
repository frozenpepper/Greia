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


if __name__ == "__main__":
    unittest.main()