from __future__ import annotations

import os
import runpy
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


class EarlyBootArchitectureScaffoldTests(unittest.TestCase):
    """Guard the hardware-neutral boot scaffold and physical build contracts."""

    def test_early_renderer_queries_runtime_framebuffer_geometry(self) -> None:
        source = EARLY_SOURCE.read_text(encoding="utf-8")
        self.assertIn("FBIOGET_FSCREENINFO", source)
        self.assertIn("FBIOGET_VSCREENINFO", source)
        self.assertIn('"/dev/fb0"', source)
        self.assertIn('"/etc/greia-boot/boot-logo.ppm"', source)
        self.assertIn("var.bits_per_pixel != 16", source)
        self.assertIn("var.bits_per_pixel != 24", source)
        self.assertIn("var.bits_per_pixel != 32", source)
        self.assertIn("background = pack_pixel", source)

    def test_early_renderer_preserves_canvas_aspect_ratio(self) -> None:
        source = EARLY_SOURCE.read_text(encoding="utf-8")
        self.assertIn("dest_w = visible_w", source)
        self.assertIn("dest_h > visible_h", source)
        self.assertIn("x0 = (visible_w - dest_w) / 2u", source)
        self.assertIn("y0 = (visible_h - dest_h) / 2u", source)
        # Visual safe margins belong to the generated landscape composition,
        # not a second runtime scaling rule tied to physical screen height.
        self.assertNotIn("visible_h / 12u", source)
        self.assertNotIn("max_h", source)
        self.assertNotIn("max_w", source)

    def test_early_renderer_has_no_reference_hardware_geometry(self) -> None:
        source = EARLY_SOURCE.read_text(encoding="utf-8")
        for forbidden in ("Acer", "Aspire"):
            self.assertNotIn(forbidden, source)
        self.assertNotIn("var.xres =", source)
        self.assertNotIn("var.yres =", source)
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

    def test_binary_ppm_separator_is_not_allowed_to_consume_raster(self) -> None:
        source = EARLY_SOURCE.read_text(encoding="utf-8")
        self.assertIn("file_data[offset] != '\\n'", source)
        self.assertNotIn(
            "while (offset < file_size && file_data[offset] <= ' ') offset++;",
            source,
        )

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

    def test_boot_design_preserves_diagnostic_recovery_channel(self) -> None:
        text = BOOT_DESIGN.read_text(encoding="utf-8")
        self.assertIn("There must be no intentional child-visible Linux console", text)
        self.assertIn("Invisible is not the same as unavailable", text)
        self.assertIn("developer SSH", text)

    def test_provisional_chime_is_bounded_if_present(self) -> None:
        if not BOOT_CHIME.exists():
            self.skipTest("provisional Greia boot chime has not been committed yet")
        data = BOOT_CHIME.read_bytes()
        self.assertGreaterEqual(len(data), 44)
        self.assertEqual(data[:4], b"RIFF")
        self.assertEqual(data[8:12], b"WAVE")

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

    def _boot_generator_namespace(self) -> dict[str, object]:
        return runpy.run_path(
            str(ROOT / "tools" / "generate_boot_artwork.py"),
            run_name="greia_boot_artwork_test",
        )

    def test_boot_generator_preserves_source_and_builds_landscape_canvas(self) -> None:
        namespace = self._boot_generator_namespace()
        source_path = namespace["SOURCE_FRAME"]
        source = namespace["canonical_full_color_frame"](source_path)
        canvas, background = namespace["compose_boot_canvas"](source)

        self.assertEqual(source.size, (222, 600))
        self.assertEqual(canvas.size, (1024, 600))
        self.assertGreaterEqual(len(set(source.getdata())), 128)
        self.assertEqual(canvas.getpixel((0, 0)), background)

        x = (canvas.width - source.width) // 2
        y = (canvas.height - source.height) // 2
        embedded = canvas.crop((x, y, x + source.width, y + source.height))
        self.assertEqual(embedded.tobytes(), source.tobytes())

    def test_generated_ppm_is_exact_canvas_encoding(self) -> None:
        namespace = self._boot_generator_namespace()
        source = namespace["canonical_full_color_frame"](namespace["SOURCE_FRAME"])
        canvas, _ = namespace["compose_boot_canvas"](source)
        with tempfile.TemporaryDirectory() as tmp:
            ppm = Path(tmp) / "boot.ppm"
            namespace["write_ppm"](canvas, ppm)
            data = ppm.read_bytes()
        header = b"P6\n1024 600\n255\n"
        self.assertTrue(data.startswith(header))
        self.assertEqual(data[len(header) :], canvas.tobytes())

    def test_initramfs_hooks_and_stages_are_present_in_both_overlays(self) -> None:
        for prefix in ("build/overlay", "build/installer-overlay"):
            with self.subTest(prefix=prefix):
                hook = ROOT / prefix / "etc/initramfs-tools/hooks/greia-early-framebuffer"
                self.assertTrue(hook.is_file())
                self.assertTrue(hook.stat().st_mode & 0o111)
                hook_text = hook.read_text(encoding="utf-8")
                self.assertIn("copy_exec /usr/lib/greia-boot/greia-fb-splash", hook_text)
                self.assertIn("[ -f /usr/lib/greia-boot/greia-fb-splash ]", hook_text)
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
                    script_text = script.read_text(encoding="utf-8")
                    self.assertIn("greia-fb-splash", script_text)
                    self.assertIn("[ -c /dev/fb0 ]", script_text)
                    self.assertIn("|| true", script_text)

    def test_builders_compile_early_framebuffer_for_target_arch_and_remove_klibc(self) -> None:
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

    def test_installed_grub_uses_proportional_theme_not_raw_background_stretch(self) -> None:
        grub_script = (ROOT / "build/overlay/etc/grub.d/10_greia_appliance").read_text(
            encoding="utf-8"
        )
        theme = (ROOT / "build/overlay/boot/grub/greia-theme.txt").read_text(
            encoding="utf-8"
        )
        self.assertIn('theme="/boot/grub/greia-theme.txt"', grub_script)
        self.assertIn("set theme=$theme", grub_script)
        self.assertNotRegex(grub_script, r"(?m)^\s*background_image\s")
        self.assertIn('desktop-image: "greia-boot-logo.png"', theme)
        self.assertIn('desktop-image-scale-method: "padding"', theme)
        self.assertIn('desktop-image-h-align: "center"', theme)
        self.assertIn('desktop-image-v-align: "center"', theme)
        builder = (ROOT / "build/build-image.sh").read_text(encoding="utf-8")
        self.assertIn("boot/grub/greia-boot-logo.png", builder)

    def test_legacy_builder_forces_fresh_boot_artwork_into_image(self) -> None:
        builder = (ROOT / "build/build-legacy-x86-sd-installer.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("generate_boot_artwork.py", builder)
        self.assertIn("BOOT_DERIVATIVES", builder)
        self.assertIn("full-color-landscape-canvas-v1", builder)
        self.assertIn("P6\\n1024 600\\n255\\n", builder)
        self.assertIn("restore_boot_derivatives", builder)
        # Firmware-sensitive removable-media writing remains elsewhere.
        self.assertNotIn("syslinux --install", builder)
        self.assertNotIn("mkfs.vfat", builder)

    def test_syslinux_live_usb_boots_straight_to_installer(self) -> None:
        cfg = (ROOT / "build/live-syslinux/syslinux.cfg.in").read_text(
            encoding="utf-8"
        )
        self.assertIn("DEFAULT live", cfg)
        self.assertNotIn("UI ", cfg)
        self.assertIn("TIMEOUT 0", cfg)
        self.assertIn("PROMPT 0", cfg)
        self.assertIn("LINUX /vmlinuz", cfg)
        self.assertIn("INITRD /initrd.img", cfg)
        self.assertIn("greia.live_media_id=LIVE_MEDIA_ID", cfg)
        self.assertIn("live-media-path=/", cfg)

    def test_live_usb_builder_is_removable_only_and_reproduces_media(self) -> None:
        builder = (ROOT / "tools/build-live-usb.sh").read_text(encoding="utf-8")
        self.assertIn("syslinux --install", builder)
        self.assertIn("mbr.bin", builder)
        self.assertIn("mkfs.vfat -F 32", builder)
        self.assertIn("live-uuid", builder)
        self.assertIn("LIVE_MEDIA_ID", builder)
        self.assertIn('"1"', builder)
        self.assertIn("disk", builder)
        self.assertIn('"$DEVICE"', builder)
        builder_path = ROOT / "tools/build-live-usb.sh"
        self.assertTrue(builder_path.stat().st_mode & 0o111)

    def test_launcher_intro_is_bounded_and_monotonic(self) -> None:
        intro = (ROOT / "src/greia_launcher/boot_intro.py").read_text(encoding="utf-8")
        self.assertIn("MAX_INTRO_SECONDS = 1.0", intro)
        self.assertIn("TARGET_INTRO_SECONDS = 0.85", intro)
        self.assertIn("time.monotonic()", intro)
        self.assertNotIn("time.sleep(", intro)
        self.assertIn("boot-intro-played", intro)
        self.assertIn("/run/greia-os", intro)
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
                self.assertTrue(boot_chime.chime_played())


if __name__ == "__main__":
    unittest.main()
