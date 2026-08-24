from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BootProgressContractTests(unittest.TestCase):
    def read(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_framebuffer_progress_argument_is_compatibility_only(self) -> None:
        source = self.read("build/early-boot/greia-fb-splash.c")
        self.assertIn('strcmp(argv[i], "--progress")', source)
        self.assertIn("value > 100u", source)
        self.assertIn("static void draw_progress_bar", source)
        # Current product presentation has no visible loading bar. The retained
        # argument/hook is compatibility plumbing and the renderer deliberately
        # ignores all drawing inputs.
        for ignored in (
            "(void)memory;",
            "(void)fix;",
            "(void)var;",
            "(void)bytes_per_pixel;",
            "(void)progress;",
        ):
            self.assertIn(ignored, source)
        # The raw renderer must never fabricate motion/progress on its own.
        for forbidden in ("sleep(", "usleep(", "nanosleep(", "time(", "system(", "popen("):
            self.assertNotIn(forbidden, source)

    def test_target_initramfs_retains_compatibility_milestone_labels(self) -> None:
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

    def test_installer_initramfs_retains_same_compatibility_labels(self) -> None:
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

    def test_first_boot_uses_exact_idempotency_marker_and_retains_labels(self) -> None:
        text = self.read("build/overlay/usr/local/lib/greia-os/first-boot")
        self.assertIn("marker=/var/lib/greia-os/initialized", text)
        self.assertIn('[ ! -e "$marker" ] || exit 0', text)
        self.assertNotIn("marker=/var/lib/greia-os/init*", text)
        self.assertIn("boot_progress 55", text)
        self.assertIn("boot_progress 65", text)
        self.assertLess(text.index("boot_progress 55"), text.index("initialized"))
        self.assertGreater(text.rindex("boot_progress 65"), text.index("initialized"))

    def test_launcher_retries_do_not_change_compatibility_label(self) -> None:
        text = self.read("build/overlay/usr/local/lib/greia-os/prepare-launcher-vt")
        self.assertIn("--progress 78", text)
        self.assertIn("a retry is recovery, not progress", text)
        self.assertNotIn("--progress 79", text)
        self.assertNotIn("--progress 80", text)

    def test_installer_preflight_retains_same_handoff_label(self) -> None:
        text = self.read("build/installer-overlay/usr/local/lib/greia-os/prepare-installer-vt")
        self.assertIn("--progress 78", text)
        self.assertIn("retries are recovery, not forward progress", text)

    def test_launcher_handoff_does_not_draw_progress_bar(self) -> None:
        intro = self.read("src/greia_launcher/boot_intro.py")
        self.assertIn("def draw_boot_handoff_frame", intro)
        self.assertIn("progress: int = 92", intro)
        # The helper remains in source for historical compatibility, but there
        # must be no call site that paints it in the launcher path.
        self.assertEqual(intro.count("_draw_progress_bar("), 1)
        self.assertIn("_background_rgb", intro)

    def test_design_contract_records_visible_bar_retirement(self) -> None:
        text = self.read("docs/design/GREIA_BOOT_PROGRESS.md")
        self.assertIn("does **not** show a loading/progress bar", text)
        self.assertIn("compatibility labels", text)
        self.assertIn("5 seconds animation", text)
        self.assertIn("2 seconds final-frame hold", text)
        self.assertIn("retry storm", text)
        self.assertIn("physical", text.lower())


if __name__ == "__main__":
    unittest.main()
