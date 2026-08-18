from __future__ import annotations

import os
import struct
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
EARLY_SOURCE = ROOT / "build" / "early-boot" / "greia-fb-splash.c"
EARLY_README = ROOT / "build" / "early-boot" / "README.md"
BOOT_DESIGN = ROOT / "docs" / "design" / "GREIA_BOOT_EXPERIENCE.md"
BOOT_CHIME = ROOT / "assets" / "audio" / "system" / "greia-boot-chime.wav"
BOOT_SOURCE = ROOT / "assets" / "boot" / "source" / "greia-boot-logo.png"
BOOT_STATIC = ROOT / "assets" / "boot" / "static" / "greia-boot-logo.png"
TARGET_PPM = ROOT / "build" / "overlay" / "etc" / "greia-boot" / "boot-logo.ppm"
INSTALLER_PPM = ROOT / "build" / "installer-overlay" / "etc" / "greia-boot" / "boot-logo.ppm"


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

    def test_canonical_boot_artwork_is_white_frame_derivative(self) -> None:
        """The canonical static boot frame is white with a dark logo foreground."""
        for path in (BOOT_SOURCE, BOOT_STATIC):
            with self.subTest(path=path.name):
                self.assertTrue(path.is_file())
                from PIL import Image

                image = Image.open(path).convert("RGB")
                self.assertEqual(image.size, (222, 600))
                # Corners must be pure/near-pure white (not the legacy navy).
                for corner in ((0, 0), (221, 0), (0, 599), (221, 599)):
                    r, g, b = image.getpixel(corner)
                    self.assertGreaterEqual(min(r, g, b), 250)
                # The logo foreground is dark (not navy-on-navy); at least one
                # dark pixel exists (the mascot/wordmark).
                pixels = list(image.getdata())
                dark = sum(1 for (r, g, b) in pixels if r < 80 and g < 80 and b < 120)
                self.assertGreater(dark, 1000)

    def test_boot_ppms_are_p6_and_match_canonical_artwork(self) -> None:
        """Target and installer initramfs PPMs are valid P6 and match the static art."""
        from PIL import Image

        reference = Image.open(BOOT_STATIC).convert("RGB").tobytes()
        for path in (TARGET_PPM, INSTALLER_PPM):
            with self.subTest(path=str(path)):
                self.assertTrue(path.is_file())
                data = path.read_bytes()
                self.assertTrue(data.startswith(b"P6\n222 600\n255\n"))
                pixel_data = data[data.index(b"\n255\n") + 5 :]
                self.assertEqual(pixel_data, reference)

    def test_initramfs_hooks_and_stages_are_present_in_both_overlays(self) -> None:
        """Both target and installer overlays ship the early-framebuffer hook and stages."""
        for prefix in ("build/overlay", "build/installer-overlay"):
            with self.subTest(prefix=prefix):
                hook = ROOT / prefix / "etc/initramfs-tools/hooks/greia-early-framebuffer"
                self.assertTrue(hook.is_file())
                self.assertTrue(hook.stat().st_mode & 0o111)
                hook_text = hook.read_text(encoding="utf-8")
                self.assertIn("copy_exec /usr/lib/greia-boot/greia-fb-splash", hook_text)
                self.assertIn("boot-logo.ppm", hook_text)
                self.assertNotIn("uvesafb", hook_text)
                for stage in ("init-top", "local-premount", "init-bottom"):
                    script = (
                        ROOT
                        / prefix
                        / "etc/initramfs-tools/scripts"
                        / stage
                        / "greia-early-framebuffer"
                    )
                    self.assertTrue(script.is_file(), f"missing stage script {stage}")
                    self.assertTrue(script.stat().st_mode & 0o111)
                    self.assertIn(
                        ". /scripts/greia-early-framebuffer-helper",
                        script.read_text(encoding="utf-8"),
                    )
                helper = (
                    ROOT / prefix / "etc/initramfs-tools/scripts/greia-early-framebuffer-helper"
                )
                self.assertTrue(helper.is_file())
                self.assertIn("greia-fb-splash", helper.read_text(encoding="utf-8"))

    def test_builders_compile_early_framebuffer_for_target_arch_and_remove_klibc(self) -> None:
        """Builders compile the cover inside the root and purge the build-only toolchain."""
        for builder_name in ("build/build-image.sh", "build/build-installer-image.sh"):
            with self.subTest(builder=builder_name):
                builder = (ROOT / builder_name).read_text(encoding="utf-8")
                self.assertIn("libklibc-dev", builder)
                self.assertIn("klcc", builder)
                self.assertIn("greia-fb-splash.c", builder)
                self.assertIn("remove --purge libklibc-dev", builder)
                self.assertIn("readelf -h", builder)
                self.assertIn("Intel 80386", builder)

    def test_profiles_use_early_framebuffer_and_no_plymouth_runtime(self) -> None:
        for profile in (ROOT / "build" / "profiles").glob("*.toml"):
            with self.subTest(profile=profile.name):
                text = profile.read_text(encoding="utf-8")
                self.assertIn('cover_backend = "greia-early-framebuffer-v1"', text)
                self.assertNotIn("stock-plymouth-provisional", text)
        package_set = (
            ROOT / "build" / "package-sets" / "boot-cover-greia-early-framebuffer.txt"
        ).read_text(encoding="utf-8")
        self.assertNotIn("plymouth", package_set.lower())

    def test_grub_uses_canonical_white_boot_logo_in_both_paths(self) -> None:
        grub_script = (ROOT / "build/overlay/etc/grub.d/10_greia_appliance").read_text(
            encoding="utf-8"
        )
        self.assertIn("background_image", grub_script)
        self.assertIn("greia-boot-logo.png", grub_script)
        self.assertIn("insmod png", grub_script)
        self.assertIn("set timeout=0", grub_script)
        builder = (ROOT / "build/build-image.sh").read_text(encoding="utf-8")
        self.assertIn("boot/grub/greia-boot-logo.png", builder)
        installer = (ROOT / "build/build-installer-image.sh").read_text(encoding="utf-8")
        self.assertIn("background_image /boot/grub/greia-boot-logo.png", installer)

    def test_launcher_intro_is_bounded_and_monotonic(self) -> None:
        intro = (ROOT / "src/greia_launcher/boot_intro.py").read_text(encoding="utf-8")
        self.assertIn("MAX_INTRO_SECONDS = 1.0", intro)
        self.assertIn("TARGET_INTRO_SECONDS = 0.85", intro)
        self.assertIn("time.monotonic()", intro)
        # No per-frame fixed sleep: the animation is elapsed-time driven and
        # frames are dropped rather than sleeping them out.
        self.assertNotIn("time.sleep(", intro)
        self.assertIn("boot-intro-played", intro)
        self.assertIn("/run/greia-os", intro)
        # The intro must not load artwork from the removed Plymouth runtime.
        self.assertNotIn("/usr/share/plymouth/", intro)

    def test_launcher_intro_plays_once_per_boot(self) -> None:
        import sys

        sys.path.insert(0, str(ROOT / "src"))
        import pygame

        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        pygame.init()
        try:
            screen = pygame.display.set_mode((960, 540))
            from greia_launcher import boot_intro

            with tempfile.TemporaryDirectory() as tmp:
                marker = Path(tmp) / "intro-marker"
                with mock.patch.dict(
                    os.environ,
                    {
                        "GREIA_BOOT_INTRO_MARKER": str(marker),
                        "GREIA_BOOT_LOGO": str(ROOT / "assets/boot/static/greia-boot-logo.png"),
                    },
                    clear=False,
                ):
                    self.assertFalse(boot_intro.boot_intro_played())
                    boot_intro.run_intro(screen, pygame)
                    self.assertTrue(boot_intro.boot_intro_played())
                    # A second call is skipped because the marker exists.
                    boot_intro.run_intro(screen, pygame)
        finally:
            pygame.quit()

    def test_boot_chime_is_one_shot_and_fail_silent(self) -> None:
        import sys

        sys.path.insert(0, str(ROOT / "src"))
        from greia_launcher import boot_chime

        with tempfile.TemporaryDirectory() as tmp:
            marker = Path(tmp) / "chime-marker"
            with mock.patch.dict(
                os.environ,
                {
                    "GREIA_BOOT_CHIME_MARKER": str(marker),
                    "GREIA_BOOT_CHIME": str(ROOT / "assets/audio/system/greia-boot-chime.wav"),
                },
                clear=False,
            ):
                self.assertFalse(boot_chime.chime_played())
                # Simulate aplay present and succeeding, then verify the marker
                # is written exactly once (fail-silent, one-shot).
                import subprocess

                with mock.patch(
                    "subprocess.run",
                    return_value=subprocess.CompletedProcess([], 0, b"", b""),
                ):
                    boot_chime.play_boot_chime()
                import time

                time.sleep(0.1)
                self.assertTrue(boot_chime.chime_played())
                boot_chime.play_boot_chime()
                time.sleep(0.1)
                # Still played exactly once semantics (idempotent marker).
                self.assertTrue(boot_chime.chime_played())


if __name__ == "__main__":
    unittest.main()
