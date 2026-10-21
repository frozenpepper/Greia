"""Installer-image consumers must not assume the ext4 root is partition 1.

The 2026-10-21 EFI media work made p1 the FAT32 ESP and p2 the ext4 live root.
The live-USB writer, SD finalizer and both read-only verifiers therefore locate
the root by filesystem type through the shared helper.
"""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "build/lib/installer-image-root.sh"
CONSUMERS = (
    "build/build-legacy-x86-sd-installer.sh",
    "tools/build-live-usb.sh",
    "tools/verify-development-installer.sh",
    "tools/verify-live-usb.sh",
)


class InstallerImageRootPartitionTests(unittest.TestCase):
    def test_helper_selects_the_ext4_partition(self) -> None:
        text = HELPER.read_text(encoding="utf-8")
        self.assertIn("greia_installer_root_partition()", text)
        self.assertIn("blkid -o value -s TYPE", text)
        self.assertIn('"$fstype" == "ext4"', text)

    def test_consumers_use_the_shared_helper_not_partition_one(self) -> None:
        for relative in CONSUMERS:
            with self.subTest(path=relative):
                text = (ROOT / relative).read_text(encoding="utf-8")
                self.assertIn("installer-image-root.sh", text)
                self.assertIn("greia_installer_root_partition", text)
                self.assertIn("blkid", text)
                self.assertNotIn('PART="${LOOP}p1"', text)
                self.assertNotIn('IMG_PART="${IMG_LOOP}p1"', text)


if __name__ == "__main__":
    unittest.main()
