from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from greia_platform.hardware_enablement import (
    CommandResult,
    CompositeHardwareSupportResolver,
    HardwareDevice,
    HardwareInventory,
    IsenkramHardwareSupportResolver,
    LinuxSysfsHardwareInventory,
    SupportDisposition,
    SupportKind,
    X86MicrocodeResolver,
)


class FakeRunner:
    def __init__(self, results: dict[tuple[str, ...], CommandResult]) -> None:
        self.results = results
        self.commands: list[tuple[str, ...]] = []

    def run(self, command, *, timeout_seconds: float) -> CommandResult:
        key = tuple(command)
        self.commands.append(key)
        if key not in self.results:
            raise FileNotFoundError(key[0])
        return self.results[key]


def inventory(*, truncated: bool = False, scan_errors: int = 0) -> HardwareInventory:
    return HardwareInventory(
        (
            HardwareDevice(
                "/pci0000:00/0000:00:1f.6",
                "pci",
                "pci:v00008086d000015BEsv00001028sd000007D0bc02sc00i00",
                "e1000e",
            ),
        ),
        truncated=truncated,
        scan_errors=scan_errors,
    )


class HardwareInventoryTests(unittest.TestCase):
    def test_sysfs_inventory_reads_modalias_subsystem_and_driver_only(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            device = root / "pci0000:00" / "0000:00:02.0"
            device.mkdir(parents=True)
            (device / "modalias").write_text("pci:v00008086d00000112", encoding="utf-8")
            # Deliberately sensitive-looking data must not enter the inventory.
            (device / "serial").write_text("PRIVATE-SERIAL", encoding="utf-8")
            subsystem_target = root / "bus" / "pci"
            driver_target = root / "drivers" / "i915"
            subsystem_target.mkdir(parents=True)
            driver_target.mkdir(parents=True)
            os.symlink(subsystem_target, device / "subsystem")
            os.symlink(driver_target, device / "driver")

            snapshot = LinuxSysfsHardwareInventory(root).snapshot()
            self.assertEqual(len(snapshot.devices), 1)
            observed = snapshot.devices[0]
            self.assertEqual(observed.subsystem, "pci")
            self.assertEqual(observed.driver, "i915")
            self.assertEqual(observed.modalias, "pci:v00008086d00000112")
            self.assertNotIn("PRIVATE-SERIAL", repr(snapshot))
            self.assertFalse(snapshot.truncated)
            self.assertEqual(snapshot.scan_errors, 0)

    def test_inventory_is_bounded_and_marks_truncation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for index in range(3):
                device = root / f"device{index}"
                device.mkdir()
                (device / "modalias").write_text(f"usb:v1234p{index:04X}", encoding="utf-8")
            snapshot = LinuxSysfsHardwareInventory(root, max_devices=2).snapshot()
            self.assertEqual(len(snapshot.devices), 2)
            self.assertTrue(snapshot.truncated)

    def test_inventory_token_is_stable_for_same_observation(self) -> None:
        first = inventory()
        second = inventory()
        self.assertEqual(first.token, second.token)
        self.assertEqual(first.modaliases, second.modaliases)


class HardwareResolverTests(unittest.TestCase):
    def make_resolver(self, firmware: CommandResult, lookup: CommandResult):
        firmware_command = "/firmware"
        lookup_command = "/lookup"
        runner = FakeRunner(
            {
                (firmware_command, "-l"): firmware,
                (lookup_command, "-l"): lookup,
            }
        )
        return (
            IsenkramHardwareSupportResolver(
                runner=runner,
                firmware_command=firmware_command,
                lookup_command=lookup_command,
            ),
            runner,
        )

    def test_firmware_is_auto_eligible_but_general_hardware_packages_are_advisory(self) -> None:
        resolver, _ = self.make_resolver(
            CommandResult(0, "firmware-iwlwifi\nfirmware-realtek\n", ""),
            CommandResult(0, "cheese\nfirmware-iwlwifi\ntlp\n", ""),
        )
        plan = resolver.resolve(inventory())
        self.assertTrue(plan.complete)
        self.assertEqual(set(plan.automatic_packages), {"firmware-iwlwifi", "firmware-realtek"})
        self.assertEqual(set(plan.advisory_packages), {"cheese", "tlp"})
        by_package = {item.package: item for item in plan.recommendations}
        self.assertEqual(by_package["firmware-iwlwifi"].kind, SupportKind.FIRMWARE)
        self.assertEqual(
            by_package["firmware-iwlwifi"].disposition,
            SupportDisposition.AUTO_ELIGIBLE,
        )

    def test_non_package_diagnostics_are_not_interpreted_as_packages(self) -> None:
        resolver, _ = self.make_resolver(
            CommandResult(
                0,
                "info: did not find any requested firmware\nfirmware-realtek\nnot a package\n",
                "",
            ),
            CommandResult(0, "hardware utility recommendation\nbluez\n", ""),
        )
        plan = resolver.resolve(inventory())
        self.assertEqual(plan.automatic_packages, ("firmware-realtek",))
        self.assertEqual(plan.advisory_packages, ("bluez",))

    def test_firmware_tool_failure_is_diagnostic_and_prevents_auto_packages(self) -> None:
        resolver, _ = self.make_resolver(
            CommandResult(2, "", "failed"),
            CommandResult(0, "bluez\n", ""),
        )
        plan = resolver.resolve(inventory())
        self.assertFalse(plan.complete)
        self.assertEqual(plan.automatic_packages, ())
        self.assertIn("firmware failed with exit 2", plan.diagnostics)

    def test_firmware_tool_no_needed_firmware_exit_is_not_a_failure(self) -> None:
        # isenkram-autoinstall-firmware -l exits 1 when no kernel driver
        # requested missing firmware; that is the healthy outcome and must not
        # block hardware resolution.
        resolver, _ = self.make_resolver(
            CommandResult(1, "", "info: did not find any firmware files requested"),
            CommandResult(0, "bluez\n", ""),
        )
        plan = resolver.resolve(inventory())
        self.assertTrue(plan.complete)
        self.assertEqual(plan.automatic_packages, ())
        self.assertEqual(plan.advisory_packages, ("bluez",))
        self.assertFalse(
            any("firmware failed" in diagnostic for diagnostic in plan.diagnostics)
        )

    def test_advisory_lookup_failure_does_not_invalidate_complete_firmware_plan(self) -> None:
        resolver, _ = self.make_resolver(
            CommandResult(0, "firmware-realtek\n", ""),
            CommandResult(4, "", "failed"),
        )
        plan = resolver.resolve(inventory())
        self.assertTrue(plan.complete)
        self.assertEqual(plan.automatic_packages, ("firmware-realtek",))
        self.assertEqual(plan.advisory_packages, ())
        self.assertIn("hardware lookup failed with exit 4", plan.diagnostics)

    def test_incomplete_inventory_suppresses_auto_packages_without_hiding_diagnostics(self) -> None:
        resolver, _ = self.make_resolver(
            CommandResult(0, "firmware-realtek\n", ""),
            CommandResult(0, "tlp\n", ""),
        )
        plan = resolver.resolve(inventory(truncated=True))
        self.assertFalse(plan.complete)
        self.assertEqual(plan.automatic_packages, ())
        self.assertEqual(plan.advisory_packages, ("tlp",))
        self.assertIn("hardware inventory was truncated", plan.diagnostics)
        self.assertTrue(
            any(item.package == "firmware-realtek" for item in plan.recommendations)
        )

    def test_x86_microcode_policy_is_architecture_level_and_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            cpuinfo = Path(temporary) / "cpuinfo"
            cpuinfo.write_text("processor: 0\nvendor_id\t: GenuineIntel\n", encoding="utf-8")
            plan = X86MicrocodeResolver(cpuinfo).resolve(inventory())
            self.assertEqual(plan.automatic_packages, ("intel-microcode",))
            recommendation = plan.recommendations[0]
            self.assertEqual(recommendation.kind, SupportKind.MICROCODE)
            self.assertEqual(recommendation.source, "x86-cpu-vendor")

    def test_composite_resolver_preserves_stronger_auto_eligible_result(self) -> None:
        isenkram, _ = self.make_resolver(
            CommandResult(0, "firmware-realtek\n", ""),
            CommandResult(0, "firmware-realtek\nbluez\n", ""),
        )
        with tempfile.TemporaryDirectory() as temporary:
            cpuinfo = Path(temporary) / "cpuinfo"
            cpuinfo.write_text("vendor_id: AuthenticAMD\n", encoding="utf-8")
            resolver = CompositeHardwareSupportResolver(
                (isenkram, X86MicrocodeResolver(cpuinfo))
            )
            plan = resolver.resolve(inventory())
        self.assertEqual(
            set(plan.automatic_packages),
            {"firmware-realtek", "amd64-microcode"},
        )
        self.assertEqual(plan.advisory_packages, ("bluez",))


if __name__ == "__main__":
    unittest.main()
