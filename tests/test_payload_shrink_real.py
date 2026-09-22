"""Real e2fsprogs payload-shrink behavior (Linux build hosts only).

Proves the production shrink flow against real binaries instead of the
runner-seam fake: a populated image in the size class where a default
flex_bg layout packs every block group into one flex group (and
``resize2fs -M`` refuses any shrink) shrinks to its minimum when created
with ``-O ^flex_bg``; the container file then matches the filesystem
extent and ``e2fsck`` passes. A second test runs
``build_release_payload`` end to end through the real subprocess runner.

Skipped wherever e2fsprogs/zstd/debugfs are unavailable (for example
macOS workstations). The core shrink behavior is never faked here.
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


spec = importlib.util.spec_from_file_location(
    "build_release_tool",
    Path(__file__).resolve().parents[1] / "tools" / "build_release.py",
)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)

sys.modules[spec.name] = module
spec.loader.exec_module(module)


_REQUIRED_BINARIES = (
    "mkfs.ext4",
    "e2fsck",
    "resize2fs",
    "dumpe2fs",
    "zstd",
    "debugfs",
)

HAVE_E2FSPROGS = all(shutil.which(name) for name in _REQUIRED_BINARIES)


def _run(argv: list[str], *, timeout: float) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        argv,
        check=False,
        shell=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )


def _geometry_blocks(image: Path) -> tuple[int, int]:
    completed = _run(["dumpe2fs", "-h", "--", str(image)], timeout=120)
    assert completed.returncode == 0, completed.stderr.decode("utf-8", "replace")
    report = completed.stdout.decode("utf-8")
    blocks = module._parse_dumpe2fs_field(report, "Block count")
    size = module._parse_dumpe2fs_field(report, "Block size")
    return blocks, size


def _seed_staging(staging: Path, payload_bytes: int) -> None:
    (staging / "etc" / "greia-os").mkdir(parents=True)
    (staging / "etc" / "greia-os" / "build-info").write_text(
        "GREIA_OS_VERSION=0.15.0\n", encoding="utf-8"
    )
    (staging / "etc" / "machine-id").write_text("", encoding="utf-8")
    (staging / "opt" / "greia-os" / "src").mkdir(parents=True)
    (staging / "opt" / "greia-os" / "src" / "placeholder.py").write_text(
        "# placeholder\n", encoding="utf-8"
    )
    (staging / "usr" / "bin").mkdir(parents=True)
    for name in ("apt-get", "dpkg", "env"):
        tool = staging / "usr" / "bin" / name
        tool.write_bytes(b"#!/bin/sh\nexit 0\n")
        tool.chmod(0o755)
    for name in ("bin", "var", "run"):
        (staging / name).mkdir(exist_ok=True)
    # Compressible content keeps the zstd step fast while still allocating
    # real data blocks that the shrink must account for.
    chunk = b"greia-payload-shrink-content-line-0123456789\n" * 1024
    written = 0
    index = 0
    while written < payload_bytes:
        target = staging / f"payload-fill-{index:03d}.bin"
        with target.open("wb") as handle:
            todo = min(len(chunk) * 64, payload_bytes - written)
            step = 0
            while step < todo:
                piece = chunk[: min(len(chunk), todo - step)]
                handle.write(piece)
                step += len(piece)
        written += target.stat().st_size
        index += 1


@unittest.skipUnless(HAVE_E2FSPROGS, "requires e2fsprogs, zstd and debugfs")
class PayloadShrinkRealTests(unittest.TestCase):
    def test_slot_sized_image_shrinks_with_real_e2fsprogs(self) -> None:
        """1 GiB populated image shrinks below its created size for real."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            staging = root / "staging"
            _seed_staging(staging, 700 * 1024 * 1024)
            image = root / "slot.ext4"
            created_bytes = 1024 * 1024 * 1024
            completed = _run(
                [
                    "mkfs.ext4",
                    "-q",
                    "-d",
                    str(staging),
                    "-O",
                    "^flex_bg",
                    "-L",
                    "greia-slot",
                    str(image),
                    f"{created_bytes // 1024}K",
                ],
                timeout=300,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr.decode())
            for command in (
                ["e2fsck", "-f", "-y", "--", str(image)],
                ["resize2fs", "-M", "--", str(image)],
                ["e2fsck", "-f", "-y", "--", str(image)],
            ):
                completed = _run(command, timeout=300)
                self.assertEqual(completed.returncode, 0, completed.stderr.decode())
            blocks, size = _geometry_blocks(image)
            shrunk_bytes = blocks * size
            self.assertLess(shrunk_bytes, created_bytes)
            self.assertEqual(image.stat().st_size, shrunk_bytes)
            completed = _run(["e2fsck", "-f", "-n", "--", str(image)], timeout=300)
            self.assertEqual(completed.returncode, 0, completed.stderr.decode())

    def test_build_release_payload_shrinks_through_real_runner(self) -> None:
        """Production producer shrinks a real image via the real runner."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            staging = root / "staging"
            _seed_staging(staging, 150 * 1024 * 1024)
            kernel = root / "vmlinuz"
            kernel.write_bytes(b"generic-kernel" * 4096)
            initramfs = root / "initrd"
            initramfs.write_bytes(b"generic-initramfs" * 4096)
            output = root / "payload.ext4.zst"
            filesystem_bytes = 256 * 1024 * 1024
            result = module.build_release_payload(
                staging_dir=staging,
                kernel_path=kernel,
                initramfs_path=initramfs,
                output=output,
                profile_id="legacy-x86-i686",
                release_id="greia-0.15.0",
                filesystem_bytes=filesystem_bytes,
                minimum_slot_bytes=None,
                runner=None,
            )
            shrunk = int(result["uncompressed_bytes"])
            self.assertLess(shrunk, filesystem_bytes)
            self.assertGreater(shrunk, 0)
            self.assertEqual(
                int(result["minimum_slot_bytes"]),
                shrunk + module.PAYLOAD_MIN_HEADROOM,
            )
            report = module.verify_release_payload(output, runner=None)
            self.assertEqual(int(report["uncompressed_bytes"]), shrunk)
            self.assertGreater(int(report["checked_paths"]), 0)


if __name__ == "__main__":
    unittest.main()
