from __future__ import annotations

import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class LiveHardwareFirmwareBuildScriptTests(unittest.TestCase):
    def test_live_firmware_is_verified_and_uses_only_local_repository(self) -> None:
        source = (PROJECT_ROOT / "build/install-live-hardware-firmware.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("verify_hardware_support_pool.py", source)
        self.assertIn("--list firmware", source)
        self.assertIn("file:/opt/greia-hardware-support", source)
        self.assertIn("Dir::Etc::sourcelist=/run/greia-hardware-support.list", source)
        self.assertIn("Dir::Etc::sourceparts=-", source)
        self.assertIn("--no-install-recommends", source)

    def test_live_firmware_does_not_install_microcode_or_use_network_downloaders(self) -> None:
        source = (PROJECT_ROOT / "build/install-live-hardware-firmware.sh").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("--list microcode", source)
        self.assertNotIn("curl ", source)
        self.assertNotIn("wget ", source)


if __name__ == "__main__":
    unittest.main()
