from __future__ import annotations

import unittest
from pathlib import Path

from greia_installer.hardware_enablement import (
    BoundDriverFirmwareResolver,
    InstallerHardwareEnablementPlan,
    InstallerHardwareEnablementPlanner,
    merge_hardware_enablement_plans,
)
from greia_installer.hardware_support import VerifiedHardwareSupportPool
from greia_platform.hardware_enablement import (
    CommandResult,
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
                    "r8169",
                ),
            )
        )


class StaticResolver:
    def __init__(self, plan: HardwareSupportPlan) -> None:
        self.plan_value = plan

    def resolve(self, inventory: HardwareInventory) -> HardwareSupportPlan:
        return self.plan_value


class FakeRunner:
    def __init__(self, result: CommandResult) -> None:
        self.result = result
        self.commands: list[tuple[str, ...]] = []

    def run(self, command, *, timeout_seconds: float) -> CommandResult:
        self.commands.append(tuple(command))
        return self.result


def pool(
    *,
    firmware: frozenset[str] = frozenset({"firmware-realtek"}),
    microcode: frozenset[str] = frozenset({"intel-microcode"}),
    providers: tuple[tuple[str, tuple[str, ...]], ...] = (
        ("rtl_nic/rtl8106e-1.fw", ("firmware-realtek",)),
        ("rtl_nic/rtl8168g-2.fw", ("firmware-realtek",)),
    ),
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
        0,
        providers,
    )


def plan(*recommendations: HardwareSupportRecommendation, complete: bool = True) -> HardwareSupportPlan:
    return HardwareSupportPlan("token", tuple(recommendations), complete)


class BoundDriverFirmwareResolverTests(unittest.TestCase):
    def test_bound_driver_firmware_is_resolved_even_when_live_firmware_is_already_present(self) -> None:
        runner = FakeRunner(CommandResult(0, "rtl_nic/rtl8168g-2.fw\n", ""))
        resolver = BoundDriverFirmwareResolver(
            pool(), runner=runner, modinfo_command="/modinfo"
        )
        result = resolver.resolve(StaticInventory().snapshot())
        self.assertTrue(result.complete)
        self.assertEqual(
            tuple(item.package for item in result.recommendations),
            ("firmware-realtek",),
        )
        self.assertEqual(
            runner.commands,
            [("/modinfo", "-F", "firmware", "r8169")],
        )

    def test_bound_driver_wildcard_firmware_declaration_uses_frozen_provider_map(self) -> None:
        runner = FakeRunner(CommandResult(0, "rtl_nic/rtl*.fw\n", ""))
        result = BoundDriverFirmwareResolver(
            pool(), runner=runner, modinfo_command="/modinfo"
        ).resolve(StaticInventory().snapshot())
        self.assertEqual(
            tuple(item.package for item in result.recommendations),
            ("firmware-realtek",),
        )

    def test_unmapped_driver_firmware_is_diagnostic_not_a_guessed_package(self) -> None:
        runner = FakeRunner(CommandResult(0, "vendor/private.bin\n", ""))
        result = BoundDriverFirmwareResolver(
            pool(), runner=runner, modinfo_command="/modinfo"
        ).resolve(StaticInventory().snapshot())
        self.assertEqual(result.recommendations, ())
        self.assertTrue(any("no frozen Debian firmware provider" in item for item in result.diagnostics))

    def test_builtin_driver_modinfo_exit_one_is_benign_not_a_failure(self) -> None:
        # Built-in platform drivers are not loadable modules; modinfo exits 1
        # and that is expected, not a hardware-resolution failure.
        runner = FakeRunner(CommandResult(1, "modinfo: ERROR: Module acpi-wmi not found.\n", ""))
        result = BoundDriverFirmwareResolver(
            pool(), runner=runner, modinfo_command="/modinfo"
        ).resolve(StaticInventory().snapshot())
        self.assertTrue(result.complete)
        self.assertEqual(result.recommendations, ())
        self.assertFalse(
            any("metadata lookup failed" in item for item in result.diagnostics)
        )

    def test_other_modinfo_exit_codes_remain_diagnostic(self) -> None:
        runner = FakeRunner(CommandResult(2, "", "modinfo crashed"))
        result = BoundDriverFirmwareResolver(
            pool(), runner=runner, modinfo_command="/modinfo"
        ).resolve(StaticInventory().snapshot())
        self.assertTrue(any("exit 2" in item for item in result.diagnostics))


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

    def test_isenkram_advisory_is_promoted_only_when_pool_independently_classifies_firmware(self) -> None:
        resolver = StaticResolver(
            plan(
                HardwareSupportRecommendation(
                    "firmware-realtek",
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
        self.assertEqual(result.required_firmware, ("firmware-realtek",))
        self.assertEqual(result.target_packages, ("firmware-realtek",))

    def test_arbitrary_advisory_package_never_enters_target_installation(self) -> None:
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


def _enablement_plan(
    *,
    firmware: tuple[str, ...] = (),
    microcode: tuple[str, ...] = (),
    complete: bool = True,
) -> InstallerHardwareEnablementPlan:
    return InstallerHardwareEnablementPlan(
        inventory=StaticInventory().snapshot(),
        resolver_plan=HardwareSupportPlan("token", (), complete),
        required_firmware=firmware,
        required_microcode=microcode,
        missing_packages=(),
        diagnostics=(),
    )


class HardwarePlanRefreshTests(unittest.TestCase):
    def test_late_bound_firmware_is_merged_into_the_pre_erase_plan(self) -> None:
        initial = _enablement_plan(microcode=("intel-microcode",))
        refreshed = _enablement_plan(
            firmware=("firmware-iwlwifi",),
            microcode=("intel-microcode",),
        )
        merged = merge_hardware_enablement_plans(initial, refreshed)
        self.assertTrue(merged.complete)
        self.assertEqual(
            merged.target_packages,
            ("firmware-iwlwifi", "intel-microcode"),
        )

    def test_incomplete_refresh_never_weakens_the_initial_decision(self) -> None:
        initial = _enablement_plan(microcode=("intel-microcode",))
        refreshed = _enablement_plan(
            firmware=("firmware-iwlwifi",),
            complete=False,
        )
        self.assertIs(merge_hardware_enablement_plans(initial, refreshed), initial)

    def test_duplicate_packages_are_deduplicated_and_sorted(self) -> None:
        initial = _enablement_plan(firmware=("firmware-realtek",))
        refreshed = _enablement_plan(
            firmware=("firmware-realtek", "firmware-iwlwifi"),
        )
        merged = merge_hardware_enablement_plans(initial, refreshed)
        self.assertEqual(
            merged.target_packages,
            ("firmware-iwlwifi", "firmware-realtek"),
        )


if __name__ == "__main__":
    unittest.main()
