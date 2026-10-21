from __future__ import annotations

import os
import subprocess
import tempfile
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
    LinuxKernelModules,
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


def _sized_pool() -> VerifiedHardwareSupportPool:
    from greia_installer.hardware_support import HardwareSupportPoolPackage

    def entry(name: str, installed: int) -> HardwareSupportPoolPackage:
        return HardwareSupportPoolPackage(
            name, "1", "all", f"pool/{name}.deb", installed // 2, "0" * 64, True, installed
        )

    names = {"firmware-iwlwifi": 1000, "firmware-realtek": 2000}
    return VerifiedHardwareSupportPool(
        Path("/verified-pool"), "trixie", "amd64",
        tuple(entry(n, b) for n, b in names.items()),
        frozenset(names), frozenset(names), frozenset(),
        1500, 3000, (),
        dependency_closures=tuple((n, (n,)) for n in names),
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

    def test_missing_required_firmware_degrades_and_adds_pool_fallback(self) -> None:
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
        # Resolved microcode is kept; only pool-provided fallback firmware is added.
        self.assertEqual(result.fallback_firmware, ("firmware-realtek",))
        self.assertEqual(result.target_packages, ("intel-microcode", "firmware-realtek"))
        self.assertTrue(result.detection_incomplete)
        self.assertTrue(any("absent" in item for item in result.diagnostics))

    def test_incomplete_resolver_plan_still_installs_fallback_from_pool(self) -> None:
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
        self.assertEqual(result.target_packages, ("firmware-realtek",))
        self.assertTrue(any("fallback" in item for item in result.diagnostics))

    def test_fallback_contains_only_pool_provided_network_firmware(self) -> None:
        wide = pool(
            firmware=frozenset(
                {"firmware-iwlwifi", "firmware-atheros", "firmware-linux-free", "firmware-misc-nonfree"}
            ),
            microcode=frozenset(),
        )
        result = InstallerHardwareEnablementPlanner(
            inventory_provider=StaticInventory(),
            resolver=StaticResolver(plan(complete=False)),
            pool=wide,
        ).plan()
        self.assertEqual(
            result.fallback_firmware,
            ("firmware-iwlwifi", "firmware-atheros", "firmware-misc-nonfree"),
        )
        self.assertEqual(result.target_packages, result.fallback_firmware)

    def test_complete_plan_adds_no_fallback(self) -> None:
        result = InstallerHardwareEnablementPlanner(
            inventory_provider=StaticInventory(),
            resolver=StaticResolver(plan()),
            pool=pool(),
        ).plan()
        self.assertTrue(result.complete)
        self.assertEqual(result.fallback_firmware, ())
        self.assertFalse(result.detection_incomplete)
        self.assertEqual(result.target_packages, ())

    def test_fallback_size_is_covered_by_selected_installed_bytes(self) -> None:
        sized = _sized_pool()
        result = InstallerHardwareEnablementPlanner(
            inventory_provider=StaticInventory(),
            resolver=StaticResolver(plan(complete=False)),
            pool=sized,
        ).plan()
        self.assertEqual(result.fallback_firmware, ("firmware-iwlwifi", "firmware-realtek"))
        self.assertEqual(
            sized.selected_installed_bytes(result.fallback_firmware, ()), 3000
        )


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


def aspire_inventory() -> HardwareInventory:
    return HardwareInventory(
        (
            HardwareDevice(
                "/pci0000:00/0000:00:1c.1/0000:03:00.0",
                "pci",
                "pci:v00008086d00004222",
                "iwl3945",
            ),
        )
    )


def kernel_tree(root: Path, *, readable: bool = True) -> LinuxKernelModules:
    modules = root / "lib" / "modules"
    if readable:
        (modules / "6.1.0-test").mkdir(parents=True)
        (modules / "6.1.0-test" / "modules.dep").write_text("", encoding="utf-8")
    return LinuxKernelModules(
        sysfs_root=root / "sys", modules_root=modules, release="6.1.0-test"
    )


def bind(root: Path, subsystem: str, driver: str, module: str) -> None:
    driver_dir = root / "sys" / "bus" / subsystem / "drivers" / driver
    driver_dir.mkdir(parents=True)
    (root / "sys" / "module" / module).mkdir(parents=True)
    (root / "sys" / "module" / module / "initstate").write_text("live\n", encoding="utf-8")
    os.symlink(f"../../../../module/{module}", driver_dir / "module")


def iwlwifi_pool() -> VerifiedHardwareSupportPool:
    return pool(
        firmware=frozenset({"firmware-iwlwifi"}),
        providers=(("iwlwifi-3945-2.ucode", ("firmware-iwlwifi",)),),
    )


class RaisingRunner:
    def __init__(self, exc: BaseException) -> None:
        self.exc = exc

    def run(self, command, *, timeout_seconds: float) -> CommandResult:
        raise self.exc


class BoundDriverModuleMetadataTests(unittest.TestCase):
    """Driver firmware must never resolve to "none" because metadata was unreadable."""

    def test_hidden_module_tree_is_incomplete_not_empty(self) -> None:
        # The installed reference Aspire lost firmware-iwlwifi exactly this way:
        # ProtectKernelModules=yes hid /usr/lib/modules from the install service.
        runner = FakeRunner(CommandResult(1, "modinfo: ERROR: Module iwl3945 not found.\n", ""))
        with tempfile.TemporaryDirectory() as raw:
            result = BoundDriverFirmwareResolver(
                iwlwifi_pool(),
                runner=runner,
                modinfo_command="/modinfo",
                kernel_modules=kernel_tree(Path(raw), readable=False),
            ).resolve(aspire_inventory())
        self.assertFalse(result.complete)
        self.assertEqual(runner.commands, [])
        self.assertIn("kernel module metadata is unreadable", result.diagnostics[0])

    def test_hidden_module_tree_falls_back_to_common_firmware(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            resolver = BoundDriverFirmwareResolver(
                iwlwifi_pool(),
                runner=FakeRunner(CommandResult(1, "", "")),
                kernel_modules=kernel_tree(Path(raw), readable=False),
            )
            decision = InstallerHardwareEnablementPlanner(
                inventory_provider=StaticInventory(),
                resolver=resolver,
                pool=iwlwifi_pool(),
            ).plan()
        self.assertFalse(decision.complete)
        # Never stops the install: the verified common firmware is added instead.
        self.assertEqual(decision.target_packages, ("firmware-iwlwifi",))
        self.assertTrue(any("unreadable" in item for item in decision.diagnostics))

    def test_loaded_module_firmware_is_selected(self) -> None:
        runner = FakeRunner(CommandResult(0, "iwlwifi-3945-2.ucode\n", ""))
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            bind(root, "pci", "iwl3945", "iwl3945")
            result = BoundDriverFirmwareResolver(
                iwlwifi_pool(),
                runner=runner,
                modinfo_command="/modinfo",
                kernel_modules=kernel_tree(root),
            ).resolve(aspire_inventory())
        self.assertTrue(result.complete)
        self.assertEqual(
            tuple(item.package for item in result.recommendations),
            ("firmware-iwlwifi",),
        )

    def test_loaded_module_unknown_to_modinfo_fails_loudly(self) -> None:
        runner = FakeRunner(CommandResult(1, "modinfo: ERROR: Module iwl3945 not found.\n", ""))
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            bind(root, "pci", "iwl3945", "iwl3945")
            result = BoundDriverFirmwareResolver(
                iwlwifi_pool(),
                runner=runner,
                modinfo_command="/modinfo",
                kernel_modules=kernel_tree(root),
            ).resolve(aspire_inventory())
        self.assertFalse(result.complete)
        self.assertTrue(
            any("lookup failed for bound driver iwl3945: exit 1" in item for item in result.diagnostics)
        )

    def test_modinfo_is_asked_for_the_module_behind_the_driver(self) -> None:
        inventory = HardwareInventory(
            (HardwareDevice("/pci0000:00/wifi", "pci", "pci:v000010ECd0000C822", "rtw_8822ce"),)
        )
        runner = FakeRunner(CommandResult(0, "", ""))
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            bind(root, "pci", "rtw_8822ce", "rtw88_8822ce")
            result = BoundDriverFirmwareResolver(
                pool(),
                runner=runner,
                modinfo_command="/modinfo",
                kernel_modules=kernel_tree(root),
            ).resolve(inventory)
        self.assertTrue(result.complete)
        self.assertEqual(runner.commands, [("/modinfo", "-F", "firmware", "rtw88_8822ce")])

    def test_builtin_driver_exit_one_stays_benign_with_module_metadata(self) -> None:
        runner = FakeRunner(CommandResult(1, "modinfo: ERROR: Module ec not found.\n", ""))
        inventory = HardwareInventory((HardwareDevice("/LNXSYSTM:00/ec", "acpi", "acpi:PNP0C09:", "ec"),))
        with tempfile.TemporaryDirectory() as raw:
            result = BoundDriverFirmwareResolver(
                pool(),
                runner=runner,
                modinfo_command="/modinfo",
                kernel_modules=kernel_tree(Path(raw)),
            ).resolve(inventory)
        self.assertTrue(result.complete)
        self.assertEqual(result.diagnostics, ())

    def test_missing_or_hung_modinfo_is_incomplete(self) -> None:
        for exc in (FileNotFoundError("/modinfo"), subprocess.TimeoutExpired("/modinfo", 5)):
            with self.subTest(exc=exc.__class__.__name__):
                result = BoundDriverFirmwareResolver(
                    pool(), runner=RaisingRunner(exc), modinfo_command="/modinfo"
                ).resolve(StaticInventory().snapshot())
                self.assertFalse(result.complete)

    def test_production_planner_wires_module_metadata_into_both_resolvers(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            planner = InstallerHardwareEnablementPlanner.linux_default(
                pool=pool(), machine="aarch64", sysfs_devices=Path(raw) / "sys" / "devices"
            )
        resolvers = planner._resolver.resolvers
        self.assertTrue(all(getattr(item, "kernel_modules", None) is not None for item in resolvers))
        self.assertEqual(resolvers[0].kernel_modules.sysfs_root, Path(raw) / "sys")


if __name__ == "__main__":
    unittest.main()
