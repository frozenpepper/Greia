from __future__ import annotations

import struct
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
THEME_DIR = PROJECT_ROOT / "build" / "overlay" / "etc" / "plymouth" / "themes" / "greia"


def _read_png_ihdr(path: Path) -> tuple[int, int, int, int]:
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"{path} is not a valid PNG")
    if data[12:16] != b"IHDR":
        raise ValueError(f"{path} missing leading IHDR chunk")
    width, height, bit_depth, color_type = struct.unpack(">IIBB", data[16:26])
    return width, height, bit_depth, color_type


class BootAnimationContractTests(unittest.TestCase):
    def test_canonical_theme_directory_and_files_exist(self) -> None:
        self.assertTrue(THEME_DIR.is_dir(), f"Canonical theme directory missing: {THEME_DIR}")
        self.assertTrue((THEME_DIR / "greia.plymouth").is_file())
        self.assertTrue((THEME_DIR / "greia.script").is_file())

    def test_canonical_theme_contains_exactly_52_direct_runtime_png_frames(self) -> None:
        frames_dir = THEME_DIR / "frames"
        self.assertTrue(frames_dir.is_dir())
        frames = sorted(frames_dir.glob("frame_*.png"))
        self.assertEqual(len(frames), 52, f"Expected 52 frames, got {len(frames)}")

        for index, frame_path in enumerate(frames):
            expected_name = f"frame_{index:04d}.png"
            self.assertEqual(frame_path.name, expected_name)
            width, height, bit_depth, color_type = _read_png_ihdr(frame_path)
            self.assertEqual(
                (width, height, bit_depth, color_type),
                (222, 600, 8, 2),
                f"{frame_path.name} must be 222x600, 8-bit RGB (color_type=2)",
            )

    def test_greia_script_playback_contract(self) -> None:
        script = (THEME_DIR / "greia.script").read_text(encoding="utf-8")
        self.assertIn("Plymouth.SetRefreshRate(7)", script)
        self.assertIn("Plymouth.SetRefreshFunction", script)
        self.assertNotIn("SetBootProgressFunction", script)
        self.assertNotIn("Plymouth.GetTime", script)

    def test_no_reconstruction_hook_or_generator_in_repository(self) -> None:
        self.assertFalse((PROJECT_ROOT / "runtime" / "boot-animation").exists())
        self.assertFalse((PROJECT_ROOT / "build" / "boot-animation").exists())
        self.assertFalse(
            (
                PROJECT_ROOT
                / "build"
                / "overlay"
                / "etc"
                / "initramfs-tools"
                / "hooks"
                / "00-greia-boot-animation"
            ).exists()
        )
        self.assertFalse(
            (
                PROJECT_ROOT
                / "build"
                / "installer-overlay"
                / "etc"
                / "initramfs-tools"
                / "hooks"
                / "00-greia-boot-animation"
            ).exists()
        )
        self.assertFalse(
            (
                PROJECT_ROOT
                / "build"
                / "installer-overlay"
                / "etc"
                / "plymouth"
                / "themes"
                / "greia"
            ).exists()
        )

    def test_installer_builder_stages_canonical_theme_source(self) -> None:
        builder = (PROJECT_ROOT / "build" / "build-installer-image.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            'GREIA_PLYMOUTH_THEME="$PROJECT_ROOT/build/overlay/etc/plymouth/themes/greia"',
            builder,
        )
        self.assertIn('"$LIVE_ROOT/usr/share/plymouth/themes/greia/"', builder)
        self.assertIn("plymouth-set-default-theme greia", builder)
