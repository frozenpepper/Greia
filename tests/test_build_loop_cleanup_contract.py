"""Regression locks for loop-device lifecycle in build and verifier shell code.

A --partscan loop can survive a successful plain losetup -d as an AUTOCLEAR
device while a partition child remains open. If the build then deletes the
backing tree, the host is left with a loop mapped to a deleted image. Every
shell path that creates a partition-scanned loop must therefore use Greia's
shared verified teardown and must not directly detach/forget it.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAFE_CLEANUP = PROJECT_ROOT / "build" / "lib" / "safe-cleanup.sh"


class BuildLoopCleanupContractTests(unittest.TestCase):
    def test_every_partscan_shell_path_uses_shared_verified_detach(self) -> None:
        candidates = []
        for root_name in ("build", "tools"):
            for path in (PROJECT_ROOT / root_name).rglob("*.sh"):
                text = path.read_text(encoding="utf-8")
                if "losetup --find --show" in text and "--partscan" in text:
                    candidates.append((path, text))

        self.assertTrue(candidates, "expected at least one partition-scanned loop owner")
        for path, text in candidates:
            rel = path.relative_to(PROJECT_ROOT)
            with self.subTest(path=str(rel)):
                self.assertIn(
                    "safe_detach_loop",
                    text,
                    f"{rel} creates a --partscan loop but never uses verified detach",
                )
                self.assertIn(
                    "safe-cleanup.sh",
                    text,
                    f"{rel} must source the shared loop cleanup implementation",
                )
                self.assertIsNone(
                    re.search(r"(?m)^\s*losetup\s+-d\b", text),
                    f"{rel} directly calls losetup -d; this can leave AUTOCLEAR partition loops",
                )

    def test_installer_target_loop_is_not_forgotten_before_verified_detach(self) -> None:
        path = PROJECT_ROOT / "build" / "build-installer-image.sh"
        text = path.read_text(encoding="utf-8")
        detach = text.index('safe_detach_loop "$TARGET_LOOP"')
        clear = text.index('TARGET_LOOP=""', detach)
        self.assertLess(detach, clear)
        between = text[detach:clear]
        self.assertIn("exit 1", between)

    def test_shared_detach_verifies_children_and_parent_association(self) -> None:
        text = SAFE_CLEANUP.read_text(encoding="utf-8")
        body = text[text.index("safe_detach_loop() {") :]
        self.assertIn('safe_remove_loop_partitions "$loop_device" || return 1', body)
        self.assertIn('if ! safe_loop_is_associated "$loop_device"; then', body)
        self.assertIn('losetup -d "$loop_device"', body)
        self.assertIn(
            "loop backing file is still associated after detach and udev settle",
            body,
        )


if __name__ == "__main__":
    unittest.main()
