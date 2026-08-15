from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.build_hardware_support_pool_manifest import PoolManifestError, build_manifest


class HardwareSupportPoolManifestTests(unittest.TestCase):
    def test_extracts_only_firmware_provider_packages_from_matching_suite_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "Fw-Contents-all-bookworm-non-free-firmware").write_text(
                "lib/firmware/iwlwifi.ucode non-free-firmware/kernel/firmware-iwlwifi\n"
                "lib/firmware/rtl.bin non-free-firmware/kernel/firmware-realtek\n"
                "malformed-line\n",
                encoding="utf-8",
            )
            (root / "Fw-Contents-all-trixie-non-free-firmware").write_text(
                "lib/firmware/amd.bin non-free-firmware/kernel/firmware-amd-graphics\n"
                "lib/firmware/rtl.bin non-free-firmware/kernel/firmware-realtek\n",
                encoding="utf-8",
            )
            manifest = build_manifest(root, "trixie", "amd64")

        self.assertEqual(
            manifest["firmware_packages"],
            ["firmware-amd-graphics", "firmware-realtek"],
        )
        self.assertEqual(
            manifest["microcode_packages"],
            ["amd64-microcode", "intel-microcode"],
        )
        self.assertEqual(
            manifest["metadata_files"],
            ["Fw-Contents-all-trixie-non-free-firmware"],
        )
        self.assertTrue(manifest["policy"]["general_isenkram_lookup_is_advisory_only"])

    def test_falls_back_to_available_firmware_metadata_when_suite_named_file_is_absent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "Fw-Contents-all-bookworm-main").write_text(
                "lib/firmware/example.bin main/kernel/firmware-linux-free\n",
                encoding="utf-8",
            )
            manifest = build_manifest(root, "trixie", "arm64")
        self.assertEqual(manifest["firmware_packages"], ["firmware-linux-free"])
        self.assertEqual(manifest["microcode_packages"], [])

    def test_package_path_is_reduced_to_safe_debian_package_basename(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "Fw-Contents-test").write_text(
                "lib/firmware/a.bin section/kernel/firmware-atheros\n"
                "lib/firmware/b.bin ../../unsafe/package name\n"
                "lib/firmware/c.bin section/kernel/firmware-realtek\n",
                encoding="utf-8",
            )
            manifest = build_manifest(root, "test", "i386")
        self.assertEqual(
            manifest["firmware_packages"],
            ["firmware-atheros", "firmware-realtek"],
        )

    def test_missing_metadata_directory_is_a_hard_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(PoolManifestError):
                build_manifest(Path(temporary) / "missing", "bookworm", "i386")

    def test_manifest_is_portable_json(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "Fw-Contents-bookworm").write_text(
                "lib/firmware/a.bin non-free-firmware/kernel/firmware-realtek\n",
                encoding="utf-8",
            )
            manifest = build_manifest(root, "bookworm", "i386")
        encoded = json.dumps(manifest, sort_keys=True, allow_nan=False)
        self.assertIn("firmware-realtek", encoded)


if __name__ == "__main__":
    unittest.main()
