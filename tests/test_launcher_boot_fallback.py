from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class LauncherBootFallbackTests(unittest.TestCase):
    def test_hardware_watcher_is_reaped_across_both_launcher_paths(self) -> None:
        session = (
            ROOT / "build/overlay/usr/local/lib/greia-os/greia-x-session"
        ).read_text(encoding="utf-8")
        self.assertIn("hardware_pid=$!", session)
        self.assertIn("trap cleanup EXIT INT TERM", session)
        self.assertIn('kill "$hardware_pid"', session)
        self.assertIn('wait "$hardware_pid"', session)

    def test_fallback_does_not_replace_proven_xorg_service_contract(self) -> None:
        unit = (
            ROOT / "build/overlay/etc/systemd/system/greia-launcher.service"
        ).read_text(encoding="utf-8")
        tmpfiles = (
            ROOT / "build/overlay/etc/tmpfiles.d/greia-runtime.conf"
        ).read_text(encoding="utf-8")
        self.assertIn("greia-os", tmpfiles)
        self.assertIn("StandardInput=null", unit)
        self.assertIn("/usr/bin/xinit", unit)
        self.assertIn(":0 vt1", unit)
        self.assertIn("-background none", unit)
        for forbidden in (
            "ProtectSystem=",
            "ProtectHome=",
            "PrivateTmp=",
            "ReadWritePaths=",
        ):
            self.assertNotIn(forbidden, unit)


if __name__ == "__main__":
    unittest.main()
