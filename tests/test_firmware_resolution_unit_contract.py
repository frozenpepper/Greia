"""Firmware resolvers must see module metadata.

The offline installation worker deliberately has no systemd capability or
syscall sandbox: it must run real Debian package maintainer scripts. The
long-lived update service still keeps module loading disabled.
"""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIRMWARE_RESOLVING_UNITS = (
    ROOT / "build/installer-overlay/etc/systemd/system/greia-install-transaction.service",
    ROOT / "build/overlay/etc/systemd/system/greia-system-update.service",
)


def _directives(path: Path) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", ";", "[")) or "=" not in line:
            continue
        key, value = line.split("=", 1)
        pairs.append((key.strip(), value.strip()))
    return pairs


class FirmwareResolvingUnitContractTests(unittest.TestCase):
    def test_module_tree_stays_readable(self) -> None:
        for unit in FIRMWARE_RESOLVING_UNITS:
            with self.subTest(unit=unit.name):
                values = [v for k, v in _directives(unit) if k == "ProtectKernelModules"]
                self.assertNotIn("yes", values)
                self.assertNotIn("true", values)
                inaccessible = " ".join(v for k, v in _directives(unit) if k == "InaccessiblePaths")
                self.assertNotIn("modules", inaccessible)

    def test_long_lived_update_service_keeps_module_loading_disabled(self) -> None:
        unit = FIRMWARE_RESOLVING_UNITS[1]
        directives = _directives(unit)
        self.assertIn(("SystemCallFilter", "~@module"), directives)
        bounding = " ".join(v for k, v in directives if k == "CapabilityBoundingSet")
        ambient = " ".join(v for k, v in directives if k == "AmbientCapabilities")
        self.assertTrue(bounding)
        self.assertNotIn("CAP_SYS_MODULE", bounding)
        self.assertNotIn("CAP_SYS_MODULE", ambient)

    def test_one_time_offline_installer_has_no_package_blocking_syscall_filter(self) -> None:
        directives = _directives(FIRMWARE_RESOLVING_UNITS[0])
        keys = {name for name, _ in directives}
        self.assertNotIn("SystemCallFilter", keys)
        self.assertNotIn("CapabilityBoundingSet", keys)
        self.assertNotIn("ProtectKernelModules", keys)


if __name__ == "__main__":
    unittest.main()
