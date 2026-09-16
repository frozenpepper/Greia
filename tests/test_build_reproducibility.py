from __future__ import annotations

import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class BuildReproducibilityTests(unittest.TestCase):
    # T02: live-installer overlay/content composition lives in the shared
    # engine; the thin installer consumer delegates instead of duplicating.
    def test_checkout_ownership_cannot_leak_into_image_roots(self) -> None:
        target = (PROJECT_ROOT / "build/lib/compose.sh").read_text(encoding="utf-8")
        installer = (PROJECT_ROOT / "build/build-installer-image.sh").read_text(encoding="utf-8")
        self.assertIn("rsync -a --chown=root:root", target)
        self.assertIn("target root ownership away from root:root", target)
        self.assertIn("live root ownership away from root:root", target)
        self.assertIn('compose_apply_overlay "$LIVE_ROOT" "live-installer"', installer)
        self.assertNotIn("rsync -a --chown=root:root", installer)

    def test_product_conffiles_are_kept_without_dpkg_prompt(self) -> None:
        target = (PROJECT_ROOT / "build/lib/compose.sh").read_text(encoding="utf-8")
        installer = (PROJECT_ROOT / "build/build-installer-image.sh").read_text(encoding="utf-8")
        self.assertIn("DEBIAN_FRONTEND=noninteractive", target)
        self.assertIn("Dpkg::Options::=--force-confold", target)
        self.assertIn('compose_install_packages "$LIVE_ROOT" "live-installer"', installer)
        self.assertNotIn("Dpkg::Options::=--force-confold", installer)

    def test_cleanup_walks_bind_submounts_and_retries_loop_detach(self) -> None:
        helper = (PROJECT_ROOT / "build/lib/safe-cleanup.sh").read_text(encoding="utf-8")
        self.assertIn("safe_unmount_path_tree", helper)
        self.assertIn("findmnt -rn -R -o TARGET --target", helper)
        self.assertIn('"$path"|"$path"/*', helper)
        self.assertIn("mapfile -t targets", helper)
        self.assertIn("for attempt in {1..20}", helper)


if __name__ == "__main__":
    unittest.main()
