from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from greia_installer.hardware_enablement import (
    FALLBACK_NETWORK_FIRMWARE,
    InstallerHardwareEnablementPlan,
    InstallerHardwareEnablementPlanner,
    merge_hardware_enablement_plans,
)
from greia_installer.hardware_id_rules import (
    DEFAULT_DEVICE_ID_RULES,
    REASON_B43_FIRMWARE,
    REASON_NO_OPEN_DRIVER,
    DeviceIdRule,
    evaluate_device_id_rules,
    parse_modalias,
)
from greia_installer.hardware_support import VerifiedHardwareSupportPool
from greia_platform.hardware_enablement import (
    HardwareDevice,
    HardwareInventory,
    HardwareSupportPlan,
)
from tools.build_hardware_support_pool_manifest import (
    FORCED_FIRMWARE_PACKAGES,
    build_manifest,
)

ROOT = Path(__file__).resolve().parents[1]


def pci(vendor: int, device: int, cls: int) -> HardwareDevice:
    modalias = f"pci:v{vendor:08X}d{device:08X}sv00001028sd00000010bc{cls:02X}sc80i00"
    return HardwareDevice(f"/pci/{vendor:04x}{device:04x}", "pci", modalias)


def inventory(*devices: HardwareDevice) -> HardwareInventory:
    return HardwareInventory(tuple(devices))


def pool(*names: str) -> VerifiedHardwareSupportPool:
    firmware = frozenset(names)
    return VerifiedHardwareSupportPool(
        Path("/verified-pool"), "bookworm", "i386", (), firmware, firmware,
        frozenset(), 0, 0, (),
    )


class Resolver:
    def resolve(self, inv: HardwareInventory) -> HardwareSupportPlan:
        return HardwareSupportPlan(inv.token, (), True)


class Provider:
    def __init__(self, inv: HardwareInventory) -> None:
        self.inv = inv

    def snapshot(self) -> HardwareInventory:
        return self.inv


def plan_for(inv: HardwareInventory, *names: str) -> InstallerHardwareEnablementPlan:
    return InstallerHardwareEnablementPlanner(
        inventory_provider=Provider(inv), resolver=Resolver(), pool=pool(*names)
    ).plan()


class ModaliasParsingTests(unittest.TestCase):
    def test_pci_and_usb_modaliases_parse(self) -> None:
        self.assertEqual(
            parse_modalias("pci:v000014E4d00004727sv00001028sd00000010bc02sc80i00"),
            ("pci", 0x14E4, 0x4727, 0x02),
        )
        self.assertEqual(
            parse_modalias("usb:v0CF3p9271d0108dc00dsc00dp00icFFisc00ip00in00"),
            ("usb", 0x0CF3, 0x9271, None),
        )
        self.assertIsNone(parse_modalias("acpi:PNP0C0A:"))
        self.assertIsNone(parse_modalias("pci:v1234d5678"))


class RuleTableTests(unittest.TestCase):
    def test_known_ids_select_packages_only_when_the_pool_provides_them(self) -> None:
        cases = {
            "firmware-brcm80211": pci(0x14E4, 0x4727, 0x02),  # BCM4313
            "firmware-amd-graphics": pci(0x1002, 0x9553, 0x03),  # Radeon
            "firmware-misc-nonfree": pci(0x10DE, 0x0866, 0x03),  # GeForce 9400M
            "firmware-realtek": pci(0x10EC, 0x8168, 0x02),
            "firmware-iwlwifi": pci(0x8086, 0x4222, 0x02),  # 3945
        }
        for package, device in cases.items():
            with self.subTest(package=package):
                inv = inventory(device)
                self.assertEqual(
                    evaluate_device_id_rules(inv, {package}).packages, (package,)
                )
                self.assertEqual(evaluate_device_id_rules(inv, set()).packages, ())

    def test_class_gates_vendor_wide_rules(self) -> None:
        # A Radeon-vendor non-display device (class 04 audio) selects nothing.
        result = evaluate_device_id_rules(
            inventory(pci(0x1002, 0xAA01, 0x04)), {"firmware-amd-graphics"}
        )
        self.assertEqual(result.packages, ())

    def test_usb_rule(self) -> None:
        usb = HardwareDevice(
            "/usb/1", "usb", "usb:v0CF3p9271d0108dc00dsc00dp00icFFisc00ip00in00"
        )
        self.assertEqual(
            evaluate_device_id_rules(inventory(usb), {"firmware-atheros"}).packages,
            ("firmware-atheros",),
        )

    def test_b43_and_wl_only_chips_are_flagged_regardless_of_pool(self) -> None:
        for device_id, reason in (
            (0x4312, REASON_B43_FIRMWARE),
            (0x4315, REASON_B43_FIRMWARE),
            (0x432B, REASON_B43_FIRMWARE),
            (0x4331, REASON_B43_FIRMWARE),
            (0x43A0, REASON_NO_OPEN_DRIVER),
            (0x4360, REASON_NO_OPEN_DRIVER),
        ):
            with self.subTest(device=hex(device_id)):
                result = evaluate_device_id_rules(
                    inventory(pci(0x14E4, device_id, 0x02)), set()
                )
                self.assertTrue(result.wifi_firmware_unavailable)
                self.assertEqual(result.unsupported[0].reason, reason)
                self.assertEqual(result.packages, ())

    def test_brcmsmac_chips_are_not_flagged(self) -> None:
        for device_id in (0x0576, 0x4353, 0x4357, 0x4727):
            result = evaluate_device_id_rules(
                inventory(pci(0x14E4, device_id, 0x02)), {"firmware-brcm80211"}
            )
            self.assertFalse(result.wifi_firmware_unavailable)

    def test_no_rule_installs_non_redistributable_firmware(self) -> None:
        for rule in DEFAULT_DEVICE_ID_RULES:
            for name in rule.packages:
                self.assertNotIn("b43", name)
                self.assertTrue(name.startswith("firmware-"), name)

    def test_rule_must_choose_packages_or_unsupported(self) -> None:
        with self.assertRaises(ValueError):
            DeviceIdRule("pci", 1)
        with self.assertRaises(ValueError):
            DeviceIdRule("isa", 1, packages=("x",))


class PlannerIntegrationTests(unittest.TestCase):
    def test_rule_package_joins_required_firmware_without_marking_incomplete(self) -> None:
        result = plan_for(
            inventory(pci(0x14E4, 0x4727, 0x02)), "firmware-brcm80211"
        )
        self.assertEqual(result.required_firmware, ("firmware-brcm80211",))
        self.assertTrue(result.complete)
        self.assertFalse(result.detection_incomplete)
        self.assertEqual(result.missing_packages, ())

    def test_rule_package_absent_from_pool_is_skipped_silently(self) -> None:
        result = plan_for(inventory(pci(0x1002, 0x9553, 0x03)), "firmware-realtek")
        self.assertEqual(result.required_firmware, ())
        self.assertEqual(result.missing_packages, ())
        self.assertFalse(result.detection_incomplete)

    def test_b43_chip_sets_the_diagnostic_flag_and_leads_the_record(self) -> None:
        result = plan_for(inventory(pci(0x14E4, 0x4312, 0x02)), "firmware-realtek")
        self.assertTrue(result.wifi_firmware_unavailable)
        self.assertTrue(result.detection_incomplete)
        self.assertIn("Ethernet or a USB Wi-Fi adapter", result.recorded_diagnostics[0])
        self.assertEqual(result.required_firmware, ())

    def test_merge_keeps_the_flag(self) -> None:
        initial = plan_for(inventory(pci(0x14E4, 0x4312, 0x02)))
        refreshed = plan_for(inventory(pci(0x14E4, 0x4312, 0x02)), "firmware-realtek")
        merged = merge_hardware_enablement_plans(initial, refreshed)
        self.assertTrue(merged.wifi_firmware_unavailable)


class CompletionNoteStringsTests(unittest.TestCase):
    def test_note_is_translated_into_it_es_fr(self) -> None:
        from greia_installer import i18n, i18n_es_fr
        from greia_installer.main import WIFI_FIRMWARE_UNAVAILABLE_NOTE

        sources = [Path(i18n.__file__).read_text(), Path(i18n_es_fr.__file__).read_text()]
        joined = "\n".join(sources)
        self.assertEqual(joined.count(f'"{WIFI_FIRMWARE_UNAVAILABLE_NOTE}": '), 3)

    def test_install_result_subclass_carries_the_flag(self) -> None:
        from greia_installer.engine import InstallResult
        from greia_installer.main import WifiAwareInstallResult

        result = WifiAwareInstallResult(wifi_firmware_unavailable=True)
        self.assertIsInstance(result, InstallResult)
        self.assertTrue(result.wifi_firmware_unavailable)


class ForcedPoolListTests(unittest.TestCase):
    REVIEW_NAMES = {
        "firmware-brcm80211", "firmware-amd-graphics", "firmware-realtek",
        "firmware-atheros", "firmware-iwlwifi", "firmware-libertas",
        "firmware-misc-nonfree",
    }

    def test_forced_list_covers_review_packages_and_fallback_set(self) -> None:
        self.assertTrue(self.REVIEW_NAMES <= set(FORCED_FIRMWARE_PACKAGES))
        self.assertTrue(set(FALLBACK_NETWORK_FIRMWARE) <= set(FORCED_FIRMWARE_PACKAGES))

    def test_forced_list_never_names_non_redistributable_packages(self) -> None:
        for name in FORCED_FIRMWARE_PACKAGES:
            self.assertNotIn("b43", name)
            self.assertNotIn("broadcom-sta", name)
            self.assertNotIn("dkms", name)
            self.assertNotIn("sof", name)

    def test_manifest_includes_forced_packages_even_without_isenkram_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "Fw-Contents-bookworm").write_text(
                "lib/firmware/x.bin non-free-firmware/kernel/firmware-other\n"
            )
            manifest = build_manifest(
                root, "bookworm", "i386", forced_firmware=FORCED_FIRMWARE_PACKAGES
            )
        self.assertTrue(set(FORCED_FIRMWARE_PACKAGES) <= set(manifest["firmware_packages"]))
        self.assertIn("firmware-other", manifest["firmware_packages"])
        self.assertEqual(
            set(manifest["candidate_packages"]),
            set(manifest["firmware_packages"]) | set(manifest["microcode_packages"]),
        )

    def test_default_manifest_has_no_forced_packages(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "Fw-Contents-bookworm").write_text(
                "lib/firmware/x.bin non-free-firmware/kernel/firmware-other\n"
            )
            self.assertEqual(
                build_manifest(root, "bookworm", "i386")["firmware_packages"],
                ["firmware-other"],
            )


class LegacyOverlayTests(unittest.TestCase):
    def test_module_policy_file(self) -> None:
        text = (ROOT / "build/overlay/etc/modprobe.d/greia-legacy-hardware.conf").read_text()
        lines = [l.strip() for l in text.splitlines() if l.strip() and not l.startswith("#")]
        self.assertIn("options hid_apple fnmode=1", lines)
        self.assertIn("blacklist b43", lines)
        self.assertNotIn("blacklist brcmsmac", lines)
        self.assertNotIn("blacklist bcma", lines)

    def test_resume_hook_lists_netbook_review_drivers(self) -> None:
        text = (ROOT / "build/overlay/usr/lib/systemd/system-sleep/greia-wifi-resume").read_text()
        line = next(l for l in text.splitlines() if l.startswith("WIFI_RESUME_DRIVERS="))
        drivers = set(line.split('"')[1].split())
        self.assertTrue(
            {"iwl3945", "iwl4965", "iwlwifi", "b43", "b43legacy", "brcmsmac", "ath5k",
             "ath9k", "rt2800pci", "rtl8192ce", "rtl8180", "rtl8187", "ipw2100",
             "ipw2200"} <= drivers
        )


if __name__ == "__main__":
    unittest.main()
