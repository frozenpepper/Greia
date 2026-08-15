from __future__ import annotations

import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class HardwareEnablementInitramfsContractTests(unittest.TestCase):
    def test_live_and_target_initramfs_keep_broad_boot_critical_modules(self) -> None:
        paths = (
            PROJECT_ROOT / "build/installer-overlay/etc/initramfs-tools/conf.d/greia-hardware",
            PROJECT_ROOT / "build/overlay/etc/initramfs-tools/conf.d/greia-hardware",
        )
        for path in paths:
            self.assertTrue(path.is_file(), str(path))
            self.assertIn("MODULES=most", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
