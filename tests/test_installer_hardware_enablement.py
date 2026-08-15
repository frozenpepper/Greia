from __future__ import annotations

import unittest
from pathlib import Path

from greia_installer.hardware_enablement import InstallerHardwareEnablementPlanner
from greia_installer.hardware_support import VerifiedHardwareSupportPool
from greia_platform.hardware_enablement import (
    HardwareDevice,
    HardwareInventory,
    HardwareSupportPlan,
    HardwareSupportRecommendation,
    SupportDisposition,
    SupportKind,
)


class StaticInventory:
    def snapshot(self) -> HardwareInventory:
        return HardwareInventory(
            (
                HardwareDevice(
                    "/pci0000:00/device",
                    "pci",
                    "pci:v00001234d00005678",
                    "example",
                ),
            )
        )


class StaticResolver:
    def __init__(self, plan: HardwareSupportPlan) -> None:
        self.plan_value = plan

    def resolve(self, inventory: HardwareInventory) -> HardwareSupportPlan:
        return self.plan_value


def pool(
    *,
    firmware: frozenset[str] = frozenset({"firmware-realtek"}),
    microcode: frozenset[str] = frozenset({"intel-microcode"}),
) -> VerifiedHardwareSupportPool:
    return VerifiedHardwareSupportPool(
        Path("/verified-pool"),
        "trixie",
        "amd64",
        (),
        firmware | microcode,
        firmware,
        microcode,
        0,
    )


def plan(*recommendations: HardwareSupportRecommendation, complete: bool = True) -> HardwareSupportPlan:
    return HardwareSupportPlan("token", tuple(recommendations), complete)


class InstallerHardwareEnablementPlannerTests(unittest.TestCase):
    def test_complete_firmware_and_microcode_plan_becomes_target_package_list(self) -> None:
        resolver = StaticResolver(
            plan(
                HardwareSupportRecommendation(
                    "firmware-realtek",
                    SupportKind.FIRMWARE,
                    SupportDisposition.AUTO_ELIGIBLE,
                    "test",
                ),
                HardwareSupportRecommendation(
                    "intel-microcode",
                    SupportKind.MICROCODE,
                    SupportDisposition.AUTO_ELIGIBLE,
                    "test",
                ),
            )
        )
        result = InstallerHardwareEnablementPlanner(
            inventory_provider=StaticInventory(), resolver=resolver, pool=pool()
        ).plan()
        self.assertTrue(result.complete)
        self.assertEqual(result.required_firmware, ("firmware-realtek",))
        self.assertEqual(result.required_microcode, ("intel-microcode",))
        self.assertEqual(
            result.target_packages,
            ("firmware-realtek", "intel-microcode"),
        )

    def test_advisory_package_never_enters_target_installation(self) -> None:
        resolver = StaticResolver(
            plan(
                HardwareSupportRecommendation(
                    "tlp",
                    SupportKind.HARDWARE_PACKAGE,
                    SupportDisposition.ADVISORY,
                    "isenkram-lookup",
                )
            )
        )
        result = InstallerHardwareEnablementPlanner(
            inventory_provider=StaticInventory(), resolver=resolver, pool=pool()
        ).plan()
        self.assertTrue(result.complete)
        self.assertEqual(result.target_packages, ())

    def test_missing_required_firmware_degrades_and_suppresses_all_target_packages(self) -> None:
        resolver = StaticResolver(
            plan(
                HardwareSupportRecommendation(
                    "firmware-iwlwifi",
                    SupportKind.FIRMWARE,
                    SupportDisposition.AUTO_ELIGIBLE,
                    "test",
                ),
                HardwareSupportRecommendation(
                    "intel-microcode",
                    SupportKind.MICROCODE,
                    SupportDisposition.AUTO_ELIGIBLE,
                    "test",
                ),
            )
        )
        result = InstallerHardwareEnablementPlanner(
            inventory_provider=StaticInventory(), resolver=resolver, pool=pool()
        ).plan()
        self.assertFalse(result.complete)
        self.assertEqual(result.missing_packages, ("firmware-iwlwifi",))
        self.assertEqual(result.target_packages, ())
        self.assertTrue(any("absent" in item for item in result.diagnostics))

    def test_incomplete_resolver_plan_suppresses_packages_even_if_pool_contains_them(self) -> None:
        resolver = StaticResolver(
            plan(
                HardwareSupportRecommendation(
                    "firmware-realtek",
                    SupportKind.FIRMWARE,
                    SupportDisposition.AUTO_ELIGIBLE,
                    "test",
                ),
                complete=False,
            )
        )
        result = InstallerHardwareEnablementPlanner(
            inventory_provider=StaticInventory(), resolver=resolver, pool=pool()
        ).plan()
        self.assertFalse(result.complete)
        self.assertEqual(result.target_packages, ())
        self.assertTrue(any("suppressed" in item for item in result.diagnostics))


if __name__ == "__main__":
    unittest.main()
