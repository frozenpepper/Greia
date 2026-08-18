from __future__ import annotations

import struct
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EARLY_SOURCE = ROOT / "build" / "early-boot" / "greia-fb-splash.c"
EARLY_README = ROOT / "build" / "early-boot" / "README.md"
BOOT_DESIGN = ROOT / "docs" / "design" / "GREIA_BOOT_EXPERIENCE.md"
BOOT_CHIME = ROOT / "assets" / "audio" / "system" / "greia-boot-chime.wav"


class EarlyBootArchitectureScaffoldTests(unittest.TestCase):
    """Guard the hardware-neutral boot scaffold before Linux integration lands.

    The local hardware agent must extend this suite while migrating active build
    profiles/builders off Plymouth. These checks intentionally do not require
    that migration yet: current main must not point at a backend that has never
    been built on the owner-controlled target toolchain.
    """

    def test_early_renderer_queries_runtime_framebuffer_geometry(self) -> None:
        source = EARLY_SOURCE.read_text(encoding="utf-8")
        self.assertIn("FBIOGET_FSCREENINFO", source)
        self.assertIn("FBIOGET_VSCREENINFO", source)
        self.assertIn('"/dev/fb0"', source)
        self.assertIn('"/etc/greia-boot/boot-logo.ppm"', source)
        self.assertIn("var.bits_per_pixel != 16", source)
        self.assertIn("var.bits_per_pixel != 24", source)
        self.assertIn("var.bits_per_pixel != 32", source)
        self.assertIn("pack_pixel(&var, 255, 255, 255)", source)

    def test_early_renderer_has_no_reference_hardware_geometry(self) -> None:
        source = EARLY_SOURCE.read_text(encoding="utf-8")
        # The renderer must query fbdev geometry at runtime. Guard against
        # reference-hardware geometry being baked in: a literal 1024x600 display
        # resolution, Acer model names, or a fixed framebuffer width/height
        # constant. (Byte-size bounds such as `64 * 1024 * 1024` are resource
        # limits, not display geometry, so the bare integer is not banned.)
        for forbidden in ("Acer", "Aspire"):
            self.assertNotIn(forbidden, source)
        self.assertNotIn("var.xres =", source)
        self.assertNotIn("var.yres =", source)
        # No fixed display-resolution literal (1024x600 etc.) may be encoded.
        self.assertNotRegex(source, r"\b1024\s*[xX*]\s*600\b")

    def test_early_renderer_remains_nonblocking_and_console_silent(self) -> None:
        source = EARLY_SOURCE.read_text(encoding="utf-8")
        for forbidden in (
            "sleep(",
            "usleep(",
            "nanosleep(",
            "system(",
            "popen(",
            "printf(",
            "fprintf(",
            "puts(",
            "perror(",
            "SDL_",
            "pygame",
            "python",
        ):
            self.assertNotIn(forbidden, source)

    def test_early_renderer_build_contract_is_target_architecture_first(self) -> None:
        text = EARLY_README.read_text(encoding="utf-8")
        self.assertIn("target-architecture", text)
        self.assertIn("klcc", text)
        self.assertIn("no sleeps/retry loops", text)
        self.assertIn("fail-soft", text)
        self.assertIn("Do **not** silently copy a host binary", text)

    def test_boot_design_owns_animation_in_launcher_not_initramfs(self) -> None:
        text = BOOT_DESIGN.read_text(encoding="utf-8")
        self.assertIn("Plymouth is not part of the target Greia architecture", text)
        self.assertIn("The launcher owns the actual intro animation", text)
        self.assertIn("0.75–0.95 seconds", text)
        self.assertIn("never exceed **1.0 second**", text)
        self.assertIn("Audio also starts here, never in initramfs", text)

    def test_boot_design_requires_continuous_white_consoleless_handoff(self) -> None:
        text = BOOT_DESIGN.read_text(encoding="utf-8")
        self.assertIn("white with the Greia logo/artwork", text)
        self.assertIn("There must be no intentional child-visible Linux console", text)
        self.assertIn("Invisible is not the same as unavailable", text)
        self.assertIn("developer SSH", text)

    def test_provisional_chime_is_bounded_if_present(self) -> None:
        """A later binary asset may land independently; validate it if present."""

        if not BOOT_CHIME.exists():
            self.skipTest("provisional Greia boot chime has not been committed yet")
        data = BOOT_CHIME.read_bytes()
        self.assertGreaterEqual(len(data), 44)
        self.assertEqual(data[:4], b"RIFF")
        self.assertEqual(data[8:12], b"WAVE")

        # The committed provisional asset is expected to be canonical PCM WAV.
        # Parse the fmt/data chunks instead of assuming a fixed 44-byte header.
        offset = 12
        sample_rate = None
        channels = None
        bits_per_sample = None
        byte_rate = None
        data_bytes = None
        while offset + 8 <= len(data):
            chunk_id = data[offset : offset + 4]
            chunk_size = struct.unpack_from("<I", data, offset + 4)[0]
            payload = offset + 8
            end = payload + chunk_size
            self.assertLessEqual(end, len(data))
            if chunk_id == b"fmt " and chunk_size >= 16:
                audio_format, channels, sample_rate, byte_rate, _, bits_per_sample = (
                    struct.unpack_from("<HHIIHH", data, payload)
                )
                self.assertEqual(audio_format, 1)
            elif chunk_id == b"data":
                data_bytes = chunk_size
            offset = end + (chunk_size & 1)

        self.assertIsNotNone(sample_rate)
        self.assertIsNotNone(channels)
        self.assertIsNotNone(bits_per_sample)
        self.assertIsNotNone(byte_rate)
        self.assertIsNotNone(data_bytes)
        assert byte_rate is not None and data_bytes is not None
        duration_seconds = data_bytes / byte_rate
        self.assertGreater(duration_seconds, 0.15)
        self.assertLessEqual(duration_seconds, 1.2)


if __name__ == "__main__":
    unittest.main()
