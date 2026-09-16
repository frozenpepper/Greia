from __future__ import annotations
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class BuildReliabilityTests(unittest.TestCase):
    # T02: live-installer APT composition lives in the shared engine; the thin
    # installer consumer delegates via compose_install_packages instead of
    # carrying its own retry invariant copy.
    def test_apt_network_failures_have_bounded_native_retries(self) -> None:
        text = (ROOT / "build/lib/compose.sh").read_text(encoding="utf-8")
        self.assertIn("Acquire::Retries=3", text)
        self.assertIn("Acquire::http::Timeout=20", text)
        self.assertIn("Acquire::https::Timeout=20", text)
        self.assertGreaterEqual(text.count('"${APT_ACQUIRE_OPTIONS[@]}"'), 2)
        self.assertIn("Dpkg::Options::=--force-confold", text)
        self.assertIn("udevadm", text)
        installer = (ROOT / "build/build-installer-image.sh").read_text(encoding="utf-8")
        self.assertIn('compose_install_packages "$LIVE_ROOT" "live-installer"', installer)
        self.assertNotIn("Acquire::Retries=3", installer)
        self.assertNotIn("Dpkg::Options::=--force-confold", installer)

    def test_cleanup_never_uses_lazy_unmount_for_build_loop_trees(self) -> None:
        helper = (ROOT / "build/lib/safe-cleanup.sh").read_text(encoding="utf-8")
        self.assertNotIn("umount -l", helper)
        self.assertIn("for attempt in {1..20}", helper)
        self.assertIn("mount remains busy after bounded normal-unmount retries", helper)
        self.assertIn("udevadm settle --timeout=5", helper)
        self.assertIn("losetup -d", helper)
        self.assertIn("safe_udev_settle", helper)

    def test_cleanup_still_refuses_paths_outside_requested_tree(self) -> None:
        helper = (ROOT / "build/lib/safe-cleanup.sh").read_text(encoding="utf-8")
        self.assertIn('"$path"|"$path"/*', helper)
        self.assertIn("refusing cleanup target outside requested mount tree", helper)
        self.assertIn("refusing to remove build tree with live mounts", helper)

if __name__ == "__main__":
    unittest.main()
