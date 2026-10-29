"""Offline installers and system-slot updates need readable module metadata.

Both one-time privileged workers must run actual Debian package maintainer
scripts; they rely on local semantic sockets rather than a capability whitelist
that previously broke real installer operations on the Acer.
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

    def test_offline_workers_do_not_reintroduce_package_script_sandbox(self) -> None:
        for unit in FIRMWARE_RESOLVING_UNITS:
            with self.subTest(unit=unit.name):
                keys = {name for name, _ in _directives(unit)}
                self.assertNotIn("SystemCallFilter", keys)
                self.assertNotIn("CapabilityBoundingSet", keys)
                self.assertNotIn("ProtectKernelModules", keys)
                self.assertNotIn("RestrictSUIDSGID", keys)


if __name__ == "__main__":
    unittest.main()
