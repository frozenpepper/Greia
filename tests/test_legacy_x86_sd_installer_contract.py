from __future__ import annotations

import tomllib
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class LegacyX86SdInstallerContractTests(unittest.TestCase):
    def test_generic_legacy_profile_does_not_require_target_machine_probe(self) -> None:
        profile_path = PROJECT_ROOT / "build/profiles/legacy-x86-i686.toml"
        profile = tomllib.loads(profile_path.read_text(encoding="utf-8"))
        self.assertEqual(profile["profile"]["id"], "legacy-x86-i686")
        self.assertEqual(profile["platform"]["family"], "legacy-x86")
        self.assertEqual(profile["base"]["architecture"], "i386")
        self.assertEqual(profile["base"]["kernel_package"], "linux-image-686")
        self.assertNotIn("acer", profile["profile"]["id"].lower())

    def test_turnkey_sd_builder_uses_generic_profile_and_embeds_sd_helpers(self) -> None:
        source = (
            PROJECT_ROOT / "build/build-legacy-x86-sd-installer.sh"
        ).read_text(encoding="utf-8")
        self.assertIn('PROFILE="legacy-x86-i686"', source)
        self.assertIn('build-installer-image.sh" "$PROFILE"', source)
        self.assertIn("collect-linux-hardware-evidence.sh", source)
        self.assertIn("prepare-antix-sd-boot.sh", source)
        self.assertIn("$MOUNT/greia-tools", source)
        self.assertIn("$MOUNT/greia-evidence", source)
        self.assertIn('sha256sum "$IMAGE"', source)
        self.assertNotIn("lscpu", source)
        self.assertNotIn("/proc/cpuinfo", source)

    def test_optional_evidence_collector_writes_a_file_and_avoids_serial_inventory(self) -> None:
        source = (
            PROJECT_ROOT / "tools/collect-linux-hardware-evidence.sh"
        ).read_text(encoding="utf-8")
        self.assertIn("OUTPUT_DIRECTORY", source)
        self.assertIn("greia-hardware-evidence-", source)
        self.assertIn("lspci -nnk", source)
        self.assertIn("lsusb", source)
        self.assertIn("lsblk -o", source)
        self.assertNotIn("dmidecode", source)
        self.assertNotIn("SERIAL,", source)
        self.assertIn("not-installer-selection", source)

    def test_antix_helper_infers_its_media_and_never_selects_installer_profile(self) -> None:
        source = (
            PROJECT_ROOT / "tools/prepare-antix-sd-boot.sh"
        ).read_text(encoding="utf-8")
        self.assertIn('MEDIA_ROOT="$(dirname "$TOOLS_DIR")"', source)
        self.assertIn('findmnt -n -o SOURCE --target "$MEDIA_ROOT"', source)
        self.assertIn("collect-linux-hardware-evidence.sh", source)
        self.assertIn("update-grub", source)
        self.assertIn("Greia installer from SD", source)
        self.assertIn("pip.live_media_id=", source)
        self.assertNotIn("linux-image-686-pae", source)
        self.assertNotIn("PROFILE=", source)


if __name__ == "__main__":
    unittest.main()
