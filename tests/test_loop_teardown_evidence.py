from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class LoopTeardownEvidenceTests(unittest.TestCase):
    def test_partition_children_are_verified_before_parent_detach(self) -> None:
        helper = (ROOT / "build/lib/safe-cleanup.sh").read_text(encoding="utf-8")
        body = helper[helper.index("safe_detach_loop() {"):]
        # The parent detach is requested first (a --partscan child may remain
        # until then); partition bookkeeping removal is the post-detach
        # fallback, and success requires BOTH association and children gone.
        flush = body.index('blockdev --flushbufs "$loop_device"')
        detach = body.index('losetup -d "$loop_device"')
        fallback = body.index('safe_remove_loop_partitions_after_detach "$loop_device"')
        self.assertLess(flush, detach)
        self.assertLess(detach, fallback)
        self.assertIn('/sys/class/block/${loop_name}p[0-9]*', helper)
        self.assertIn("safe_loop_partition_children_present", body)
        self.assertIn("loop detach did not fully settle", body)
        self.assertIn("stale loop partition children remain", body)
        self.assertNotIn("losetup -D", helper)

    def test_loop_association_probe_does_not_reopen_block_device(self) -> None:
        helper = (ROOT / "build/lib/safe-cleanup.sh").read_text(encoding="utf-8")
        self.assertIn('/sys/class/block/$loop_name/loop/backing_file', helper)
        self.assertIn("safe_loop_is_associated() {", helper)
        self.assertNotIn('losetup "$loop_device" >/dev/null', helper)

    def test_both_builders_require_blockdev_explicitly(self) -> None:
        for relative in ("build/build-image.sh", "build/build-installer-image.sh"):
            text = (ROOT / relative).read_text(encoding="utf-8")
            command_line = next(
                line for line in text.splitlines()
                if line.startswith(("require_commands=(", "required=("))
            )
            words = command_line.replace("(", " ").replace(")", " ").split()
            self.assertIn("blockdev", words)
            self.assertIn("partx", words)
            self.assertIn("losetup", words)

    def test_cleanup_failure_is_not_hidden_as_build_success(self) -> None:
        for relative in ("build/build-image.sh", "build/build-installer-image.sh"):
            text = (ROOT / relative).read_text(encoding="utf-8")
            cleanup = text[text.index("cleanup() {"):text.index("trap cleanup EXIT")]
            self.assertIn(
                'safe_cleanup_exit "$original_status" "$cleanup_failed"', cleanup
            )
        shared = (ROOT / "build/lib/safe-cleanup.sh").read_text(encoding="utf-8")
        self.assertIn("final_status=1", shared[shared.index("safe_cleanup_exit() {"):])


if __name__ == "__main__":
    unittest.main()
