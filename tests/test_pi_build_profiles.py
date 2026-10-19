"""Pi profile schema and package closure, intentionally NOT builder eligibility."""

from __future__ import annotations

import unittest
from pathlib import Path
from tools.build_profile import BuildProfile, BuildProfileError

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "build" / "package-sets"


class PiProfileTests(unittest.TestCase):
    def test_400_and_500_profiles_are_distinct_and_resolve_without_grub(self) -> None:
        for model in ("400", "500"):
            with self.subTest(board=model):
                profile = BuildProfile.load(
                    ROOT / "build" / "profiles" / f"raspberry-pi-{model}-arm64.toml"
                )
                self.assertEqual("arm64", profile.base.architecture)
                self.assertEqual("arm64", profile.platform.family)
                self.assertEqual(f"pi-{model}-v1", profile.platform.board)
                self.assertEqual("pi-mbr-tryboot-ab-v1", profile.storage.layout_adapter)
                self.assertEqual("pi-tryboot-ab-v1", profile.updates.boot_backend)
                self.assertEqual("pi-builtin-microsd-v1", profile.installer.target_policy)
                self.assertEqual("pi-live-usb-v1", profile.setup.live_boot_adapter)
                self.assertEqual("experimental", profile.identity.certification_state)
                for scope in ("target", "installer"):
                    packages = profile.resolve_packages(PKG, scope)
                    self.assertIn("dosfstools", packages)
                    self.assertNotIn("grub-pc", packages)
                    self.assertNotIn("grub-pc-bin", packages)
                    with self.assertRaisesRegex(BuildProfileError, "Phase 0"):
                        profile.check_phase0_builder_support(scope)


if __name__ == "__main__":
    unittest.main()
