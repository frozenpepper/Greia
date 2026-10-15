"""Regression locks for loop-device lifecycle in build and verifier shell code.

The build host proved two important Linux lifecycle facts:

* a --partscan child may remain until parent loop detach is requested, so
  partx -d cannot be a prerequisite for losetup -d;
* returning non-zero from a Bash EXIT-trap function does not reliably turn an
  otherwise successful process into failure.

These tests lock the shared cleanup semantics and every first-party shell owner.
"""

from __future__ import annotations

import shlex
import subprocess
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAFE_CLEANUP = PROJECT_ROOT / "build" / "lib" / "safe-cleanup.sh"
# The checkout path may contain spaces; quote it for the bash -c scripts below.
SAFE_CLEANUP_SHELL = shlex.quote(str(SAFE_CLEANUP))
FRONT_DOOR = PROJECT_ROOT / "tools" / "build-and-flash-development-usb.sh"
DELETED_BACKING_FIXTURE = PROJECT_ROOT / "tools" / "test-loop-cleanup-deleted-backing.sh"
PARTSCAN_OWNERS = (
    PROJECT_ROOT / "build" / "build-image.sh",
    PROJECT_ROOT / "build" / "build-installer-image.sh",
    PROJECT_ROOT / "build" / "build-legacy-x86-sd-installer.sh",
    PROJECT_ROOT / "tools" / "build-live-usb.sh",
    PROJECT_ROOT / "tools" / "verify-development-installer.sh",
    PROJECT_ROOT / "tools" / "verify-development-target-image.sh",
    PROJECT_ROOT / "tools" / "verify-live-usb.sh",
    DELETED_BACKING_FIXTURE,
)


class BuildLoopCleanupContractTests(unittest.TestCase):
    def test_every_partscan_shell_path_uses_shared_verified_detach(self) -> None:
        discovered = []
        for root_name in ("build", "tools"):
            for path in (PROJECT_ROOT / root_name).rglob("*.sh"):
                text = path.read_text(encoding="utf-8")
                if "losetup --find --show" in text and "--partscan" in text:
                    discovered.append(path)

        self.assertEqual(set(PARTSCAN_OWNERS), set(discovered))
        for path in discovered:
            text = path.read_text(encoding="utf-8")
            rel = path.relative_to(PROJECT_ROOT)
            with self.subTest(path=str(rel)):
                self.assertIn("safe_detach_loop", text)
                self.assertIn("safe-cleanup.sh", text)
                executable_direct_detach = [
                    line
                    for line in text.splitlines()
                    if line.lstrip().startswith("losetup -d ")
                ]
                self.assertEqual(
                    [],
                    executable_direct_detach,
                    f"{rel} bypasses the shared verified detach path",
                )

    def test_shared_detach_requests_parent_detach_before_waiting_for_children(self) -> None:
        script = f"""
set -Eeuo pipefail
source {SAFE_CLEANUP_SHELL}
ASSOCIATED=1
CHILDREN=1
DETACH_WITH_CHILD=0

safe_udev_settle() {{ :; }}
blockdev() {{ :; }}
safe_loop_backing_file() {{
  if (( ASSOCIATED )); then
    printf '%s\n' '/tmp/greia-probe.img'
  else
    return 1
  fi
}}
safe_loop_partition_children_present() {{
  (( CHILDREN ))
}}
losetup() {{
  if [[ "$1" == "-d" ]]; then
    if (( CHILDREN )); then
      DETACH_WITH_CHILD=1
    fi
    ASSOCIATED=0
    CHILDREN=0
    return 0
  fi
  return 99
}}

safe_detach_loop /dev/loop99
[[ "$DETACH_WITH_CHILD" == "1" ]]
[[ "$ASSOCIATED" == "0" ]]
[[ "$CHILDREN" == "0" ]]
"""
        result = subprocess.run(
            ["bash", "-c", script],
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr)

    def test_shared_detach_pins_backing_identity_and_interleaves_partx_after_detach(self) -> None:
        text = SAFE_CLEANUP.read_text(encoding="utf-8")
        body = text[text.index("safe_detach_loop() {") :]
        self.assertIn('expected_backing="$(safe_loop_backing_file', body)
        self.assertIn('current_backing" != "$expected_backing"', body)
        detach_at = body.index('losetup -d "$loop_device"')
        fallback_at = body.index('safe_remove_loop_partitions_after_detach "$loop_device"')
        self.assertLess(detach_at, fallback_at)
        self.assertIn('partx -d "$loop_device"', text)
        self.assertIn("safe_loop_debug_openers", body)

    def test_interleaved_detach_then_partx_clears_busy_partition_shape(self) -> None:
        script = f"""
set -Eeuo pipefail
source {SAFE_CLEANUP_SHELL}
ASSOCIATED=1
CHILDREN=1
DETACH_REQUESTED=0
PARTX_BEFORE_DETACH=0

safe_udev_settle() {{ :; }}
blockdev() {{ :; }}
safe_loop_backing_file() {{
  if (( ASSOCIATED )); then
    printf '%s\\n' '/tmp/greia-deleted-backing.img (deleted)'
  else
    return 1
  fi
}}
safe_loop_partition_children_present() {{
  (( CHILDREN ))
}}
losetup() {{
  if [[ "$1" == "-d" ]]; then
    DETACH_REQUESTED=1
    return 0
  fi
  return 99
}}
partx() {{
  if (( ! DETACH_REQUESTED )); then
    PARTX_BEFORE_DETACH=1
    return 16
  fi
  CHILDREN=0
  ASSOCIATED=0
  return 0
}}

safe_detach_loop /dev/loop99
[[ "$DETACH_REQUESTED" == "1" ]]
[[ "$PARTX_BEFORE_DETACH" == "0" ]]
[[ "$ASSOCIATED" == "0" ]]
[[ "$CHILDREN" == "0" ]]
"""
        result = subprocess.run(
            ["bash", "-c", script],
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr)

    def test_non_mount_cleanup_path_does_not_walk_containing_root_filesystem(self) -> None:
        script = f"""
set -Eeuo pipefail
source {SAFE_CLEANUP_SHELL}
MARKER="$(mktemp)"
rm -f "$MARKER"
mountpoint() {{ return 1; }}
findmnt() {{ printf '%s\n' called > "$MARKER"; return 0; }}
safe_unmount_path_tree /definitely-not-a-mount
[[ ! -e "$MARKER" ]]
"""
        result = subprocess.run(
            ["bash", "-c", script],
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr)

    def test_cleanup_failure_changes_successful_exit_status(self) -> None:
        script = f"""
set -Eeuo pipefail
source {SAFE_CLEANUP_SHELL}
cleanup() {{
  original_status=$?
  trap - EXIT INT TERM
  safe_cleanup_exit "$original_status" 1 "forced cleanup failure"
}}
trap cleanup EXIT
true
"""
        result = subprocess.run(
            ["bash", "-c", script],
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(1, result.returncode)
        self.assertIn("forced cleanup failure", result.stderr)

    def test_cleanup_preserves_original_nonzero_status(self) -> None:
        script = f"""
set -Eeuo pipefail
source {SAFE_CLEANUP_SHELL}
cleanup() {{
  original_status=$?
  trap - EXIT INT TERM
  safe_cleanup_exit "$original_status" 1 "cleanup also failed"
}}
trap cleanup EXIT
exit 7
"""
        result = subprocess.run(
            ["bash", "-c", script],
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(7, result.returncode)
        self.assertIn("cleanup also failed", result.stderr)

    def test_all_partscan_owners_declare_partx_dependency(self) -> None:
        for path in PARTSCAN_OWNERS:
            text = path.read_text(encoding="utf-8")
            rel = path.relative_to(PROJECT_ROOT)
            with self.subTest(path=str(rel)):
                dependency_lines = [
                    line
                    for line in text.splitlines()
                    if "required=(" in line
                    or "require_commands=(" in line
                    or "for command_name in " in line
                ]
                self.assertTrue(
                    any("partx" in line for line in dependency_lines),
                    f"{rel} uses shared cleanup but does not declare partx",
                )

    def test_deleted_backing_fixture_reproduces_field_shape(self) -> None:
        text = DELETED_BACKING_FIXTURE.read_text(encoding="utf-8")
        self.assertIn('losetup --find --show --partscan "$IMG"', text)
        self.assertIn('exec 9<"$1"', text)
        self.assertIn('rm -f "$IMG"', text)
        self.assertIn('"(deleted)"', text)
        self.assertIn('safe_detach_loop "$LOOP"', text)
        self.assertIn("DELETED_BACKING_LOOP_CLEANUP=PASS", text)

    def test_all_partscan_owners_use_authoritative_cleanup_exit(self) -> None:
        for path in PARTSCAN_OWNERS:
            text = path.read_text(encoding="utf-8")
            rel = path.relative_to(PROJECT_ROOT)
            with self.subTest(path=str(rel)):
                self.assertIn("safe_cleanup_exit", text)
                self.assertNotIn('return "$original_status"', text)
                self.assertNotIn("trap cleanup EXIT INT TERM", text)

    def test_front_door_refuses_preexisting_and_postrun_greia_loops(self) -> None:
        text = FRONT_DOOR.read_text(encoding="utf-8")
        self.assertIn("PREEXISTING_GREIA_LOOPS", text)
        self.assertIn("REMAINING_GREIA_LOOPS", text)
        self.assertIn("Refusing: pre-existing Greia build loop", text)
        self.assertIn("Build+flash failed loop-hygiene verification", text)
        self.assertIn("loop_hygiene_verification=PASS", text)


if __name__ == "__main__":
    unittest.main()
