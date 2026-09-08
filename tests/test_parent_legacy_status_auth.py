from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from greia_parent.server import ParentStatusApplication


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ParentLegacyStatusAuthTests(unittest.TestCase):
    def test_legacy_status_application_still_owns_its_compatibility_token(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state_dir = root / "parent"
            app = ParentStatusApplication(
                PROJECT_ROOT,
                state_dir,
                profiles_dir=root / "profiles",
                hardware_settings_dir=root / "hardware",
                hardware_status_path=root / "hardware-status.json",
                active_profile_status_path=root / "active-profile.json",
            )

            token_path = state_dir / "parent-pairing-token"
            self.assertTrue(app.token)
            self.assertTrue(token_path.is_file())
            self.assertEqual(token_path.read_text(encoding="ascii").strip(), app.token)


if __name__ == "__main__":
    unittest.main()
