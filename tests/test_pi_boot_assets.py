"""Pure Pi 400/500 boot-asset staging tests; no block devices or network."""

from __future__ import annotations

import hashlib
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from greia_platform.boot_transaction import BootArtifactSet
from greia_platform.pi_boot_assets import (
    PiBoard,
    PiBootAssetError,
    PiBootAssetStager,
    parse_pi_autoboot,
    render_pi_autoboot,
    render_pi_boot_config,
    render_pi_cmdline,
)


def write(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def raw_arm64_kernel() -> bytes:
    header = bytearray(1024 * 1024)
    header[0x38:0x3c] = b"ARM" + bytes((0x64,))
    return bytes(header)


def artifacts(slot: str = "A") -> BootArtifactSet:
    return BootArtifactSet(
        slot=slot,
        layout_id="pi-mbr-tryboot-ab-v1",
        boot_backend="pi-tryboot-ab-v1",
        generic_kernel_sha256=digest(raw_arm64_kernel()),
        generic_initramfs_sha256=digest(b"greia-initrd"),
        root_partuuid="a123bcde-05" if slot == "A" else "a123bcde-06",
        root_filesystem_uuid="00000000-0000-4000-8000-000000000001",
        release_id="greia-test-release",
    )


class NativePiBootAssetTests(unittest.TestCase):
    def test_real_firmware_autoboot_roundtrip_both_slots(self) -> None:
        for slot in ("A", "B"):
            text = render_pi_autoboot(slot)
            self.assertIn("[all]\ntryboot_a_b=1\n", text)
            self.assertEqual(slot, parse_pi_autoboot(text))
            self.assertIn("[tryboot]\n", text)
        with self.assertRaisesRegex(PiBootAssetError, "canonical"):
            parse_pi_autoboot("boot_partition=2\n")

    def test_board_kernel_and_dtb_arenot_interchangeable(self) -> None:
        self.assertIn("[pi400]", render_pi_boot_config(PiBoard.PI_400))
        self.assertIn("kernel=kernel8.img", render_pi_boot_config(PiBoard.PI_400))
        self.assertIn("[pi500]", render_pi_boot_config(PiBoard.PI_500))
        self.assertIn("kernel=kernel_2712.img", render_pi_boot_config(PiBoard.PI_500))
        with self.assertRaises(PiBootAssetError):
            render_pi_boot_config("pi-500-v1")  # type: ignore[arg-type]

    def test_boot_cmdline_requires_corresponding_observed_system_root(self) -> None:
        self.assertIn("root=PARTUUID=a123bcde-05", render_pi_cmdline(artifacts("A")))
        self.assertIn("root=PARTUUID=a123bcde-06", render_pi_cmdline(artifacts("B")))
        with self.assertRaisesRegex(PiBootAssetError, "does not match"):
            render_pi_cmdline(replace(artifacts("A"), root_partuuid="a123bcde-06"))

    def test_stage_from_finalized_release_and_board_firmware(self) -> None:
        for board in PiBoard:
            for slot in ("A", "B"):
                with self.subTest(board=board, slot=slot), tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    write(root / "system/boot/vmlinuz-greia", raw_arm64_kernel())
                    write(root / "system/boot/initramfs-greia.img", b"greia-initrd")
                    write(root / "firmware" / board.dtb_filename, b"dtb")
                    write(root / "firmware/overlays" / (board.kms_overlay + ".dtbo"), b"kms")
                    if board == PiBoard.PI_400:
                        write(root / "firmware/start4.elf", b"firmware")
                        write(root / "firmware/fixup4.dat", b"fixup")
                    (root / "stage").mkdir()
                    receipt = PiBootAssetStager().stage(
                        board=board,
                        artifacts=artifacts(slot),
                        system_root=root / "system",
                        firmware_root=root / "firmware",
                        destination=root / "stage",
                    )
                    self.assertEqual(slot, receipt.slot)
                    self.assertEqual(2 if slot == "A" else 3, receipt.boot_partition)
                    self.assertTrue((root / "stage" / board.kernel_filename).is_file())
                    self.assertTrue((root / "stage" / board.dtb_filename).is_file())
                    self.assertIn(f"root=PARTUUID={receipt.root_partuuid}",
                                  (root / "stage/cmdline.txt").read_text())
                    self.assertTrue(any(name == "config.txt" for name, _ in receipt.files))
                    with self.assertRaisesRegex(PiBootAssetError, "empty"):
                        PiBootAssetStager().stage(
                            board=board, artifacts=artifacts(slot),
                            system_root=root / "system",
                            firmware_root=root / "firmware",
                            destination=root / "stage",
                        )

    def test_missing_pi500_specific_dtb_refuses_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root / "system/boot/vmlinuz-greia", raw_arm64_kernel())
            write(root / "system/boot/initramfs-greia.img", b"greia-initrd")
            write(root / "firmware/bcm2711-rpi-400.dtb", b"wrong-board")
            (root / "firmware/overlays").mkdir()
            (root / "stage").mkdir()
            with self.assertRaisesRegex(PiBootAssetError, "boot source"):
                PiBootAssetStager().stage(
                    board=PiBoard.PI_500, artifacts=artifacts(),
                    system_root=root / "system",
                    firmware_root=root / "firmware",
                    destination=root / "stage",
                )
            self.assertEqual([], list((root / "stage").iterdir()))

    def test_digest_equal_but_compressed_kernel_refuses_native_boot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            compressed = bytes((0x1f, 0x8b)) + bytes(1024 * 1024)
            write(root / "system/boot/vmlinuz-greia", compressed)
            write(root / "system/boot/initramfs-greia.img", b"greia-initrd")
            (root / "firmware").mkdir()
            (root / "stage").mkdir()
            candidate = replace(
                artifacts(), generic_kernel_sha256=digest(compressed)
            )
            with self.assertRaisesRegex(PiBootAssetError, "uncompressed AArch64"):
                PiBootAssetStager().stage(
                    board=PiBoard.PI_400, artifacts=candidate,
                    system_root=root / "system",
                    firmware_root=root / "firmware",
                    destination=root / "stage",
                )
            self.assertEqual([], list((root / "stage").iterdir()))

    def test_kernel_receipt_mismatch_refuses_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root / "system/boot/vmlinuz-greia", b"tampered-kernel")
            write(root / "system/boot/initramfs-greia.img", b"greia-initrd")
            (root / "firmware").mkdir()
            (root / "stage").mkdir()
            with self.assertRaisesRegex(PiBootAssetError, "finalized release"):
                PiBootAssetStager().stage(
                    board=PiBoard.PI_400, artifacts=artifacts(),
                    system_root=root / "system",
                    firmware_root=root / "firmware",
                    destination=root / "stage",
                )
            self.assertEqual([], list((root / "stage").iterdir()))


if __name__ == "__main__":
    unittest.main()
