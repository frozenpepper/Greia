from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BootProgressContractTests(unittest.TestCase):
    def read(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_framebuffer_renderer_accepts_explicit_progress_only(self) -> None:
        source = self.read("build/early-boot/greia-fb-splash.c")
        self.assertIn('strcmp(argv[i], "--progress")', source)
        self.assertIn("value > 100u", source)
        self.assertIn("draw_progress_bar", source)
        self.assertIn("progress >= 0", source)
        # The raw renderer must never fabricate motion/progress on its own.
        for forbidden in ("sleep(", "usleep(", "nanosleep(", "time(", "system(", "popen("):
            self.assertNotIn(forbidden, source)

    def test_target_initramfs_uses_real_milestones(self) -> None:
        stages = {
            "init-top": 15,
            "local-premount": 30,
            "init-bottom": 45,
        }
        for stage, progress in stages.items():
            with self.subTest(stage=stage):
                text = self.read(
                    f"build/overlay/etc/initramfs-tools/scripts/{stage}/greia-early-framebuffer"
                )
                self.assertIn(f"--progress {progress}", text)
                self.assertIn("|| true", text)

    def test_installer_initramfs_uses_same_early_milestones(self) -> None:
        stages = {
            "init-top": 15,
            "local-premount": 30,
            "init-bottom": 45,
        }
        for stage, progress in stages.items():
            with self.subTest(stage=stage):
                text = self.read(
                    "build/installer-overlay/etc/initramfs-tools/scripts/"
                    f"{stage}/greia-early-framebuffer"
                )
                self.assertIn(f"--progress {progress}", text)
                self.assertIn("|| true", text)

    def test_first_boot_advances_only_on_state_boundaries(self) -> None:
        text = self.read("build/overlay/usr/local/lib/greia-os/first-boot")
        self.assertIn("boot_progress 55", text)
        self.assertIn("boot_progress 65", text)
        self.assertLess(text.index("boot_progress 55"), text.index("initialized"))
        self.assertGreater(text.rindex("boot_progress 65"), text.index("initialized"))

    def test_launcher_retries_do_not_fabricate_progress(self) -> None:
        text = self.read("build/overlay/usr/local/lib/greia-os/prepare-launcher-vt")
        self.assertIn("--progress 78", text)
        self.assertIn("a retry is recovery, not progress", text)
        self.assertNotIn("--progress 79", text)
        self.assertNotIn("--progress 80", text)

    def test_installer_preflight_uses_same_truthful_handoff_milestone(self) -> None:
        text = self.read("build/installer-overlay/usr/local/lib/greia-os/prepare-installer-vt")
        self.assertIn("--progress 78", text)
        self.assertIn("retries are recovery, not forward progress", text)

    def test_launcher_handoff_can_render_near_complete_progress(self) -> None:
        intro = self.read("src/greia_launcher/boot_intro.py")
        self.assertIn("def draw_boot_handoff_frame", intro)
        self.assertIn("progress: int = 92", intro)
        self.assertIn("_draw_progress_bar", intro)
        self.assertIn("_background_rgb", intro)
        self.assertNotIn("screen.fill((255, 255, 255))", intro)

    def test_design_contract_rejects_timer_and_retry_progress(self) -> None:
        text = self.read("docs/design/GREIA_BOOT_PROGRESS.md")
        self.assertIn("milestone-based, never timer-based", text)
        self.assertIn("a service crashed and restarted", text)
        self.assertIn("Every restart remains 78%", text)
        self.assertIn("retry storm", text)
        self.assertIn("physical", text.lower())


if __name__ == "__main__":
    unittest.main()
