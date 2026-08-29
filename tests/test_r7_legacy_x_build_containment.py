from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
X_SESSION = ROOT / "build" / "overlay" / "usr" / "local" / "lib" / "greia-os" / "greia-x-session"
LAUNCHER_SERVICE = ROOT / "build" / "overlay" / "etc" / "systemd" / "system" / "greia-launcher.service"
GENERIC_HARDWARE_SESSION = ROOT / "src" / "greia_platform" / "hardware_session.py"
LEGACY_HARDWARE_ENTRYPOINT = ROOT / "src" / "greia_platform" / "hardware_session_legacy_x.py"


class LegacyXBuildContainmentTests(unittest.TestCase):
    def test_x_session_selects_explicit_legacy_hardware_entrypoint(self) -> None:
        source = X_SESSION.read_text(encoding="utf-8")
        self.assertIn("greia_platform.hardware_session_legacy_x", source)
        legacy_generic_invocation = any(
            line.strip().startswith("/usr/bin/python3 -m greia_platform.hardware_session ")
            for line in source.splitlines()
        )
        self.assertFalse(legacy_generic_invocation)

    def test_generic_hardware_watcher_has_no_legacy_backend_selection(self) -> None:
        source = GENERIC_HARDWARE_SESSION.read_text(encoding="utf-8")
        self.assertNotIn("LegacyXHardwareSessionController", source)
        self.assertNotIn("hal_legacy_x", source)
        self.assertNotIn('"xrandr"', source)
        self.assertNotIn('"xinput"', source)

    def test_legacy_entrypoint_is_the_backend_selection_edge(self) -> None:
        source = LEGACY_HARDWARE_ENTRYPOINT.read_text(encoding="utf-8")
        self.assertIn("LegacyXHardwareSessionController", source)
        self.assertIn("run_watcher", source)

    def test_current_installed_service_remains_explicitly_provisional_xorg(self) -> None:
        source = LAUNCHER_SERVICE.read_text(encoding="utf-8")
        self.assertIn("/usr/bin/xinit", source)
        self.assertIn("greia-x-session", source)
        self.assertIn("provisional Xorg display server", source)


if __name__ == "__main__":
    unittest.main()
