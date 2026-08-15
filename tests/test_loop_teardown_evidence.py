from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class LoopTeardownEvidenceTests(unittest.TestCase):
    def test_partition_children_are_verified_before_parent_detach(self) -> None:
        helper = (ROOT / "build/lib/safe-cleanup.sh").read_text(encoding="utf-8")
        remove_call = helper.index('safe_remove_loop_partitions "$loop_device"')
        flush = helper.index('blockdev --flushbufs "$loop_device"')
        detach = helper.index('losetup -d "$loop_device"')
        self.assertLess(remove_call, flush)
        self.assertLess(flush, detach)
        self.assertIn('/sys/class/block/${loop_name}p[0-9]*', helper)
        self.assertIn('loop partition mappings remain after bounded partx teardown', helper)
        self.assertNotIn("losetup -D", helper)

    def test_loop_association_probe_does_not_reopen_block_device(self) -> None:
        helper = (ROOT / "build/lib/safe-cleanup.sh").read_text(encoding="utf-8")
        self.assertIn('/sys/class/block/$loop_name/loop/backing_file', helper)
        self.assertIn('safe_loop_is_associated "$loop_device"', helper)
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
            self.assertIn("if (( original_status == 0 )); then", cleanup)
            self.assertIn("return 1", cleanup)


if __name__ == "__main__":
    unittest.main()
