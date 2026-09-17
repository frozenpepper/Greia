from __future__ import annotations

import importlib.util
import hashlib
import io
import json
import shutil
import struct
import subprocess
import sys
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "build_release_tool",
    Path(__file__).resolve().parents[1] / "tools" / "build_release.py",
)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)

sys.modules[spec.name] = module
spec.loader.exec_module(module)

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from greia_platform.system_updates import build_update_bundle, inspect_update_bundle  # noqa: E402


_MANIFEST_OFFSET = 2048


def _parse_size_arg(arg: str) -> int:
    if arg.endswith("K"):
        return int(arg[:-1]) * 1024
    if arg.endswith("M"):
        return int(arg[:-1]) * 1024 * 1024
    return int(arg)


def _read_manifest(image: Path) -> set[str]:
    raw = image.read_bytes()
    (length,) = struct.unpack_from(">I", raw, _MANIFEST_OFFSET)
    return set(json.loads(raw[_MANIFEST_OFFSET + 4 : _MANIFEST_OFFSET + 4 + length].decode("utf-8")))


def _make_hw_pool(root: Path, *, payload: bytes = b"firmware") -> Path:
    """Write a minimal verified hardware-support pool (pure file IO)."""
    pool = root / "hw-pool"
    deb_dir = pool / "pool"
    deb_dir.mkdir(parents=True)
    (deb_dir / "firmware-realtek_1_all.deb").write_bytes(payload)
    packages_payload = b"Package: firmware-realtek\n"
    packages_gzip_payload = b"gzip-placeholder"
    (pool / "Packages").write_bytes(packages_payload)
    (pool / "Packages.gz").write_bytes(packages_gzip_payload)

    def _sha(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    manifest = {
        "schema_version": 1,
        "suite": "trixie",
        "architecture": "amd64",
        "package_count": 1,
        "total_bytes": len(payload),
        "total_installed_bytes": len(payload) + 32 * 1024,
        "provided_candidate_packages": ["firmware-realtek"],
        "provided_firmware_packages": ["firmware-realtek"],
        "provided_microcode_packages": [],
        "broad_firmware_packages": ["firmware-realtek"],
        "firmware_providers": {"rtl.bin": ["firmware-realtek"]},
        "unavailable_candidate_packages": [],
        "packages": [
            {
                "package": "firmware-realtek",
                "version": "1",
                "architecture": "all",
                "filename": "pool/firmware-realtek_1_all.deb",
                "size": len(payload),
                "sha256": _sha(payload),
                "candidate": True,
                "installed_bytes": len(payload) + 32 * 1024,
            }
        ],
        "repository_indexes": {
            "Packages": {"size": len(packages_payload), "sha256": _sha(packages_payload)},
            "Packages.gz": {
                "size": len(packages_gzip_payload),
                "sha256": _sha(packages_gzip_payload),
            },
        },
    }
    (pool / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return pool


class FakeExt4Runner:
    """Seam fake: simulates e2fsprogs/debugfs, delegates zstd to the real binary.

    Small control commands go through ``run``; full-payload zstd transfers go
    through ``stream_to_file`` (stdout-to-file, bounded RAM), mirroring the
    production seam split. ``run`` retains a zstd branch only so a regression
    (payload capture reintroduced) surfaces as a routable assertion instead
    of a bare AttributeError.
    """

    def __init__(self) -> None:
        self.commands: list[list[str]] = []
        self.timeouts: list[float | None] = []
        self.streamed_commands: list[list[str]] = []
        self.streamed_timeouts: list[float | None] = []

    def run(self, command, *, timeout_seconds=None) -> object:
        argv = list(command)
        self.commands.append(argv)
        self.timeouts.append(timeout_seconds)
        prog = argv[0]
        if prog == "mkfs.ext4":
            staging = Path(argv[argv.index("-d") + 1])
            image = Path(argv[-2])
            total = _parse_size_arg(argv[-1])
            entries: set[str] = set()
            for path in sorted(staging.rglob("*"), key=lambda p: p.relative_to(staging).as_posix()):
                entries.add(path.relative_to(staging).as_posix())
            manifest = json.dumps(sorted(entries)).encode("utf-8")
            blob = bytearray(total)
            blob[1080:1082] = b"\x53\xef"
            struct.pack_into(">I", blob, _MANIFEST_OFFSET, len(manifest))
            blob[_MANIFEST_OFFSET + 4 : _MANIFEST_OFFSET + 4 + len(manifest)] = manifest
            image.parent.mkdir(parents=True, exist_ok=True)
            image.write_bytes(bytes(blob))
            return module.ReleaseCommandResult(stdout=b"", returncode=0)
        if prog == "e2fsck":
            image = Path(argv[-1])
            try:
                head = image.read_bytes()[:2048]
            except OSError:
                return module.ReleaseCommandResult(stdout=b"missing image", returncode=1)
            if head[1080:1082] != b"\x53\xef":
                return module.ReleaseCommandResult(stdout=b"bad superblock", returncode=1)
            return module.ReleaseCommandResult(stdout=b"", returncode=0)
        if prog == "resize2fs":
            image = Path(argv[-1])
            size = image.stat().st_size
            shrunk = max(65536, size // 2)
            with image.open("r+b") as handle:
                handle.truncate(shrunk)
            return module.ReleaseCommandResult(stdout=b"", returncode=0)
        if prog == "zstd":
            completed = subprocess.run(
                argv,
                check=False,
                capture_output=True,
                timeout=timeout_seconds if timeout_seconds is not None else 120,
                shell=False,
            )
            return module.ReleaseCommandResult(
                stdout=completed.stdout, returncode=completed.returncode
            )
        if prog == "debugfs":
            request = argv[argv.index("-R") + 1]
            rel = request.split("stat ", 1)[1].strip()
            image = Path(argv[-1])
            try:
                entries = _read_manifest(image)
            except (OSError, ValueError, json.JSONDecodeError, struct.error):
                return module.ReleaseCommandResult(stdout=b"unreadable image", returncode=1)
            if rel in entries:
                return module.ReleaseCommandResult(stdout=b"Inode: 42", returncode=0)
            return module.ReleaseCommandResult(
                stdout=f"stat: {rel} not found".encode(), returncode=1
            )
        raise AssertionError(f"unexpected command: {argv}")

    def stream_to_file(self, command, output_path, *, timeout_seconds=None) -> None:
        """Fake streaming seam: real zstd with stdout wired to the file."""
        argv = list(command)
        self.streamed_commands.append(argv)
        self.streamed_timeouts.append(timeout_seconds)
        prog = Path(argv[0]).name
        if prog != "zstd":
            raise AssertionError(f"unexpected streamed command: {argv}")
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("wb") as out_handle:
            completed = subprocess.run(
                argv,
                check=False,
                shell=False,
                stdin=subprocess.DEVNULL,
                stdout=out_handle,
                stderr=subprocess.PIPE,
                timeout=timeout_seconds if timeout_seconds is not None else 120,
            )
        if completed.returncode != 0:
            raise AssertionError(f"fake zstd streaming failed: {argv}")


class BuildReleaseTests(unittest.TestCase):
    def _staging(self, root: Path) -> Path:
        staging = root / "staging"
        (staging / "etc" / "greia-os").mkdir(parents=True)
        (staging / "etc" / "greia-os" / "build-info").write_text(
            "GREIA_OS_VERSION=0.15.0\n", encoding="utf-8"
        )
        # Clone-neutral identity state (composer-owned; the payload gate only
        # re-verifies): empty etc/machine-id, no dbus/random-seed/ssh_host_*.
        (staging / "etc" / "machine-id").write_text("", encoding="utf-8")
        (staging / "opt" / "greia-os" / "src").mkdir(parents=True)
        (staging / "opt" / "greia-os" / "src" / "placeholder.py").write_text(
            "# placeholder\n", encoding="utf-8"
        )
        (staging / "usr" / "bin").mkdir(parents=True)
        for name in ("apt-get", "dpkg", "env"):
            (staging / "usr" / "bin" / name).write_bytes(b"#!/bin/sh\nexit 0\n")
            (staging / "usr" / "bin" / name).chmod(0o755)
        (staging / "bin").mkdir(exist_ok=True)
        (staging / "var").mkdir(exist_ok=True)
        (staging / "run").mkdir(exist_ok=True)
        return staging

    def test_payload_builds_real_ext4_via_ordered_e2fsprogs_sequence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            staging = self._staging(root)
            kernel = root / "vmlinuz"
            kernel.write_bytes(b"generic-kernel" * 64)
            initramfs = root / "initrd"
            initramfs.write_bytes(b"generic-initramfs" * 64)
            output = root / "payload.ext4.zst"
            runner = FakeExt4Runner()
            filesystem_bytes = 4 * 1024 * 1024
            result = module.build_release_payload(
                staging_dir=staging,
                kernel_path=kernel,
                initramfs_path=initramfs,
                output=output,
                profile_id="legacy-x86-i686",
                release_id="greia-0.15.0",
                filesystem_bytes=filesystem_bytes,
                minimum_slot_bytes=5 * 1024 * 1024,
                runner=runner,
            )
            kinds = [cmd[0] for cmd in runner.commands]
            self.assertEqual(kinds, ["mkfs.ext4", "e2fsck", "resize2fs", "e2fsck"])
            # Payload compression streams through the file seam, never the
            # capture seam: exactly one streamed `zstd -19 -c`.
            streamed_kinds = [cmd[0] for cmd in runner.streamed_commands]
            self.assertEqual(streamed_kinds, ["zstd"])
            self.assertEqual(runner.streamed_commands[0][:3], ["zstd", "-19", "-c"])
            self.assertNotIn("-T", runner.streamed_commands[0])
            # Exact ordered commands: populate -> check -> shrink-min -> re-check.
            self.assertEqual(runner.commands[0][:2], ["mkfs.ext4", "-d"])
            self.assertEqual(runner.commands[1][:3], ["e2fsck", "-f", "-y"])
            self.assertNotIn("-n", runner.commands[1])
            self.assertEqual(runner.commands[2][:2], ["resize2fs", "-M"])
            self.assertEqual(runner.commands[3][:3], ["e2fsck", "-f", "-y"])
            for cmd in runner.commands:
                self.assertNotIn("shell", [str(c) for c in cmd])
            for cmd in runner.streamed_commands:
                self.assertNotIn("shell", [str(c) for c in cmd])
            # Shrink post-condition: reported size is the post-shrink image,
            # strictly smaller than the populated size, and covers headroom.
            shrunk = result["uncompressed_bytes"]
            self.assertLess(shrunk, filesystem_bytes)
            self.assertGreater(shrunk, 0)
            self.assertGreaterEqual(result["minimum_slot_bytes"], shrunk + 1024 * 1024)
            self.assertEqual(output.read_bytes()[:4], b"\x28\xb5\x2f\xfd")
            # Relocatable: decompressed head carries ext4 magic, no MBR/GPT.
            raw = subprocess.run(
                ["zstd", "-d", "-c", "--", str(output)],
                check=True,
                capture_output=True,
                shell=False,
            ).stdout
            self.assertEqual(len(raw), shrunk)
            self.assertEqual(raw[1080:1082], b"\x53\xef")
            self.assertNotEqual(raw[510:512], b"\x55\xaa")
            self.assertNotEqual(raw[512:520], b"EFI PART")

    def test_payload_compression_runs_with_intended_bound(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            staging = self._staging(root)
            kernel = root / "vmlinuz"
            kernel.write_bytes(b"generic-kernel" * 64)
            initramfs = root / "initrd"
            initramfs.write_bytes(b"generic-initramfs" * 64)
            output = root / "payload.ext4.zst"
            runner = FakeExt4Runner()
            module.build_release_payload(
                staging_dir=staging,
                kernel_path=kernel,
                initramfs_path=initramfs,
                output=output,
                profile_id="legacy-x86-i686",
                release_id="greia-0.15.0",
                filesystem_bytes=4 * 1024 * 1024,
                minimum_slot_bytes=5 * 1024 * 1024,
                runner=runner,
            )
            kinds = [cmd[0] for cmd in runner.commands]
            self.assertEqual(kinds, ["mkfs.ext4", "e2fsck", "resize2fs", "e2fsck"])
            # First four steps run under the default command bound; the
            # streamed zstd -19 step over the ~1 GiB-class image runs under
            # the larger compression bound with real headroom.
            self.assertEqual(
                runner.timeouts, [module.DEFAULT_COMMAND_TIMEOUT_SECONDS] * 4
            )
            self.assertEqual(
                runner.streamed_timeouts, [module.PAYLOAD_COMPRESSION_TIMEOUT_SECONDS]
            )
            self.assertGreaterEqual(module.DEFAULT_COMMAND_TIMEOUT_SECONDS, 600.0)
            self.assertGreaterEqual(module.PAYLOAD_COMPRESSION_TIMEOUT_SECONDS, 1800.0)
            self.assertEqual(runner.streamed_commands[0][:3], ["zstd", "-19", "-c"])
            # Custom overrides propagate through the same seam.
            runner2 = FakeExt4Runner()
            module.build_release_payload(
                staging_dir=staging,
                kernel_path=kernel,
                initramfs_path=initramfs,
                output=root / "payload2.ext4.zst",
                profile_id="legacy-x86-i686",
                release_id="greia-0.15.0",
                filesystem_bytes=4 * 1024 * 1024,
                minimum_slot_bytes=5 * 1024 * 1024,
                runner=runner2,
                command_timeout_seconds=11.0,
                compression_timeout_seconds=22.0,
            )
            self.assertEqual(runner2.timeouts, [11.0] * 4)
            self.assertEqual(runner2.streamed_timeouts, [22.0])
            # Production runner defaults stay finite and match the constants.
            self.assertEqual(
                module.SubprocessReleaseRunner().timeout_seconds,
                module.DEFAULT_COMMAND_TIMEOUT_SECONDS,
            )

    def test_payload_command_exceeding_bound_fails_closed(self) -> None:
        runner = module.SubprocessReleaseRunner(timeout_seconds=0.05)
        with self.assertRaises(module.ReleaseBuildError) as ctx:
            runner.run(["sleep", "5"], timeout_seconds=0.05)
        self.assertIn("unavailable", str(ctx.exception).lower())
        # A non-positive configured bound is refused before any image byte.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            staging = self._staging(root)
            kernel = root / "vmlinuz"
            kernel.write_bytes(b"k")
            initramfs = root / "initrd"
            initramfs.write_bytes(b"i")
            with self.assertRaises(module.ReleaseBuildError):
                module.build_release_payload(
                    staging_dir=staging,
                    kernel_path=kernel,
                    initramfs_path=initramfs,
                    output=root / "payload.ext4.zst",
                    profile_id="legacy-x86-i686",
                    release_id="greia-0.15.0",
                    filesystem_bytes=2 * 1024 * 1024,
                    minimum_slot_bytes=2 * 1024 * 1024,
                    runner=FakeExt4Runner(),
                    compression_timeout_seconds=0,
                )

    def test_hardware_support_timeout_contract_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pool = _make_hw_pool(root)
            # Non-positive/non-numeric bounds are refused before any output byte.
            for bad in (0, -1, 0.0, "600", None, True, False):
                target = root / f"hw-bad-{len(str(bad))}-{str(type(bad).__name__)}.tar.zst"
                with self.assertRaises(module.ReleaseBuildError):
                    module.build_hardware_support_set(
                        pool,
                        target,
                        command_timeout_seconds=bad,  # type: ignore[arg-type]
                    )
                self.assertFalse(target.exists())
            # Bound expiry fails closed through the production runner seam:
            # the hardware step routes its zstd command through the seam with
            # the configured bound, and the real SubprocessReleaseRunner wraps
            # the expiry into ReleaseBuildError (never raw TimeoutExpired).
            class RecordingExpiringRunner:
                def __init__(self) -> None:
                    self.commands: list[list[str]] = []
                    self.timeouts: list[float | None] = []

                def run(self, command, *, timeout_seconds=None) -> object:
                    argv = list(command)
                    self.commands.append(argv)
                    self.timeouts.append(timeout_seconds)
                    return module.SubprocessReleaseRunner().run(
                        ["sleep", "5"], timeout_seconds=0.05
                    )

            output = root / "hardware-support.tar.zst"
            runner = RecordingExpiringRunner()
            with self.assertRaises(module.ReleaseBuildError) as ctx:
                module.build_hardware_support_set(
                    pool,
                    output,
                    command_timeout_seconds=600.0,
                    runner=runner,  # type: ignore[arg-type]
                )
            self.assertNotIsInstance(ctx.exception, subprocess.TimeoutExpired)
            self.assertIn("unavailable", str(ctx.exception).lower())
            self.assertEqual(len(runner.commands), 1)
            self.assertEqual(Path(runner.commands[0][0]).name, "zstd")
            self.assertEqual(runner.commands[0][1:4], ["-19", "-c", "--rm"])
            self.assertEqual(runner.timeouts, [600.0])
            self.assertFalse(output.exists())
            # Positive path through the same seam preserves the contract.
            result = module.build_hardware_support_set(
                pool, output, command_timeout_seconds=600.0
            )
            self.assertEqual(output.read_bytes()[:4], b"\x28\xb5\x2f\xfd")
            self.assertEqual(result["sha256"], hashlib.sha256(output.read_bytes()).hexdigest())
            self.assertEqual(result["size"], output.stat().st_size)
            raw = subprocess.run(
                ["zstd", "-d", "-c", "--", str(output)],
                check=True,
                capture_output=True,
                shell=False,
            ).stdout
            with tarfile.open(fileobj=io.BytesIO(raw), mode="r") as tar:
                names = sorted(member.name for member in tar.getmembers())
            self.assertEqual(
                names,
                ["Packages", "Packages.gz", "manifest.json", "pool/firmware-realtek_1_all.deb"],
            )

    def test_payload_build_and_verify_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            staging = self._staging(root)
            kernel = root / "vmlinuz"
            kernel.write_bytes(b"generic-kernel" * 64)
            initramfs = root / "initrd"
            initramfs.write_bytes(b"generic-initramfs" * 64)
            output = root / "payload.ext4.zst"
            runner = FakeExt4Runner()
            result = module.build_release_payload(
                staging_dir=staging,
                kernel_path=kernel,
                initramfs_path=initramfs,
                output=output,
                profile_id="legacy-x86-i686",
                release_id="greia-0.15.0",
                filesystem_bytes=4 * 1024 * 1024,
                minimum_slot_bytes=5 * 1024 * 1024,
                runner=runner,
            )
            verify_runner = FakeExt4Runner()
            payload = module.verify_release_payload(output, runner=verify_runner)
            self.assertEqual(payload["uncompressed_bytes"], result["uncompressed_bytes"])
            verify_kinds = [cmd[0] for cmd in verify_runner.commands]
            verify_streamed = [cmd[0] for cmd in verify_runner.streamed_commands]
            # Decompression streams through the file seam (no capture).
            self.assertEqual(verify_streamed, ["zstd"])
            self.assertEqual(verify_runner.streamed_commands[0][:3], ["zstd", "-d", "-c"])
            self.assertNotIn("zstd", verify_kinds)
            self.assertIn("e2fsck", verify_kinds)
            self.assertIn("debugfs", verify_kinds)
            self.assertGreaterEqual(payload["checked_paths"], 10)
            # v3 bundle round-trip as ZIP_STORED payload.ext4.zst, no key material.
            bundle = root / "update.greiaupdate"
            manifest = build_update_bundle(
                payload_path=output,
                hardware_support_path=None,
                output_path=bundle,
                version="0.15.0",
                release_id="greia-0.15.0",
                platform_family="acer",
                architecture="i686",
                profile="legacy-x86-i686",
                payload_uncompressed_bytes=result["uncompressed_bytes"],
                minimum_slot_bytes=result["minimum_slot_bytes"],
                persist_read_schema_min=1,
                persist_read_schema_max=1,
                persist_write_schema=1,
            )
            self.assertEqual(manifest.payload_uncompressed_bytes, result["uncompressed_bytes"])
            with zipfile.ZipFile(bundle, "r") as archive:
                infos = {info.filename: info for info in archive.infolist()}
                self.assertEqual(infos["payload.ext4.zst"].compress_type, zipfile.ZIP_STORED)
            inspected = inspect_update_bundle(bundle)
            self.assertEqual(
                inspected.manifest.payload_uncompressed_bytes, result["uncompressed_bytes"]
            )
            for text in ("signer", "signature", "key", "sequence"):
                self.assertNotIn(text, json.dumps(manifest.as_json_dict()).lower())

    def _payload_kwargs(self, root: Path, staging: Path) -> dict:
        kernel = root / "vmlinuz"
        kernel.write_bytes(b"k")
        initramfs = root / "initrd"
        initramfs.write_bytes(b"i")
        return {
            "staging_dir": staging,
            "kernel_path": kernel,
            "initramfs_path": initramfs,
            "output": root / "payload.ext4.zst",
            "profile_id": "legacy-x86-i686",
            "release_id": "greia-0.15.0",
            "filesystem_bytes": 2 * 1024 * 1024,
            "minimum_slot_bytes": 2 * 1024 * 1024,
        }

    def _assert_gate_refusal(self, root: Path, staging: Path, needle: str) -> None:
        """The gate refuses before populate/compression: no runner call, no output."""
        runner = FakeExt4Runner()
        with self.assertRaises(module.ReleaseBuildError) as ctx:
            module.build_release_payload(runner=runner, **self._payload_kwargs(root, staging))
        self.assertIn(needle, str(ctx.exception).lower())
        self.assertFalse((root / "payload.ext4.zst").exists())
        self.assertEqual(runner.commands, [])
        self.assertEqual(runner.streamed_commands, [])

    def test_clone_neutral_gate_refuses_nonempty_machine_id(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            staging = self._staging(root)
            (staging / "etc" / "machine-id").write_text("9f1b2c\n", encoding="utf-8")
            self._assert_gate_refusal(root, staging, "machine-id")

    def test_clone_neutral_gate_refuses_missing_machine_id(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            staging = self._staging(root)
            (staging / "etc" / "machine-id").unlink()
            self._assert_gate_refusal(root, staging, "machine-id")

    def test_clone_neutral_gate_refuses_dbus_machine_id(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            staging = self._staging(root)
            dbus_id = staging / "var" / "lib" / "dbus" / "machine-id"
            dbus_id.parent.mkdir(parents=True, exist_ok=True)
            dbus_id.write_text("9f1b2c\n", encoding="utf-8")
            self._assert_gate_refusal(root, staging, "dbus")

    def test_clone_neutral_gate_refuses_random_seed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            staging = self._staging(root)
            seed = staging / "var" / "lib" / "systemd" / "random-seed"
            seed.parent.mkdir(parents=True, exist_ok=True)
            seed.write_bytes(b"\x00\x01\x02\x03" * 128)
            self._assert_gate_refusal(root, staging, "random-seed")

    def test_clone_neutral_gate_refuses_ssh_host_keys(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            staging = self._staging(root)
            ssh_dir = staging / "etc" / "ssh"
            ssh_dir.mkdir(parents=True, exist_ok=True)
            (ssh_dir / "ssh_host_ed25519_key").write_bytes(b"fake-host-key")
            (ssh_dir / "ssh_host_ed25519_key.pub").write_bytes(b"fake-host-key-pub")
            self._assert_gate_refusal(root, staging, "ssh_host")

    def test_clone_neutral_gate_clean_tree_still_builds(self) -> None:
        """Positive control: a clone-neutral tree builds through the real
        function seam (fake runner only stands in for e2fsprogs/zstd)."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            staging = self._staging(root)
            kernel = root / "vmlinuz"
            kernel.write_bytes(b"generic-kernel" * 64)
            initramfs = root / "initrd"
            initramfs.write_bytes(b"generic-initramfs" * 64)
            output = root / "payload.ext4.zst"
            runner = FakeExt4Runner()
            result = module.build_release_payload(
                staging_dir=staging,
                kernel_path=kernel,
                initramfs_path=initramfs,
                output=output,
                profile_id="legacy-x86-i686",
                release_id="greia-0.15.0",
                filesystem_bytes=4 * 1024 * 1024,
                minimum_slot_bytes=5 * 1024 * 1024,
                runner=runner,
            )
            self.assertTrue(output.exists())
            self.assertGreater(result["uncompressed_bytes"], 0)
            # Seeding writes are disjoint from the gate: boot assets and the
            # release identity exist on the consumed tree, and the gate still
            # holds on the seeded state.
            self.assertTrue((staging / "boot" / "vmlinuz-generic").is_file())
            self.assertTrue((staging / "boot" / "initrd-generic").is_file())
            self.assertTrue(
                (staging / "etc" / "greia-os" / "release-identity.json").is_file()
            )
            module._assert_clone_neutral_staging(staging)

    def test_clone_neutral_gate_never_repairs_dirty_tree(self) -> None:
        """The gate is verification, not cleanup: the dirty file survives refusal."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            staging = self._staging(root)
            (staging / "etc" / "machine-id").write_text("9f1b2c\n", encoding="utf-8")
            runner = FakeExt4Runner()
            with self.assertRaises(module.ReleaseBuildError):
                module.build_release_payload(runner=runner, **self._payload_kwargs(root, staging))
            self.assertEqual(
                (staging / "etc" / "machine-id").read_text(encoding="utf-8"), "9f1b2c\n"
            )

    def test_minimal_skeleton_root_is_refused_before_compression(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            staging = root / "staging"
            for name in ("etc", "lost+found", "run", "var"):
                (staging / name).mkdir(parents=True)
            kernel = root / "vmlinuz"
            kernel.write_bytes(b"k")
            initramfs = root / "initrd"
            initramfs.write_bytes(b"i")
            runner = FakeExt4Runner()
            with self.assertRaises(module.ReleaseBuildError):
                module.build_release_payload(
                    staging_dir=staging,
                    kernel_path=kernel,
                    initramfs_path=initramfs,
                    output=root / "payload.ext4.zst",
                    profile_id="legacy-x86-i686",
                    release_id="greia-0.15.0",
                    filesystem_bytes=2 * 1024 * 1024,
                    minimum_slot_bytes=2 * 1024 * 1024,
                    runner=runner,
                )
            self.assertFalse((root / "payload.ext4.zst").exists())
            self.assertNotIn("zstd", [cmd[0] for cmd in runner.commands])
            self.assertEqual(runner.streamed_commands, [])

    def test_missing_apt_get_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            staging = self._staging(root)
            (staging / "usr" / "bin" / "apt-get").unlink()
            kernel = root / "vmlinuz"
            kernel.write_bytes(b"k")
            initramfs = root / "initrd"
            initramfs.write_bytes(b"i")
            runner = FakeExt4Runner()
            with self.assertRaises(module.ReleaseBuildError) as ctx:
                module.build_release_payload(
                    staging_dir=staging,
                    kernel_path=kernel,
                    initramfs_path=initramfs,
                    output=root / "payload.ext4.zst",
                    profile_id="legacy-x86-i686",
                    release_id="greia-0.15.0",
                    filesystem_bytes=2 * 1024 * 1024,
                    minimum_slot_bytes=2 * 1024 * 1024,
                    runner=runner,
                )
            self.assertIn("apt-get", str(ctx.exception))

    def test_synthetic_tar_payload_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            buffer = io.BytesIO()
            with tarfile.open(fileobj=buffer, mode="w", format=tarfile.PAX_FORMAT) as tar:
                info = tarfile.TarInfo("etc/greia-os/build-info")
                data = b"GREIA_OS_VERSION=0.15.0\n"
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
            fake_image = b"GREIA-SLOT-V1\n" + buffer.getvalue()
            fake_image = fake_image.ljust(1024 * 1024, b"\x00")
            zstd = shutil.which("zstd")
            assert zstd is not None
            completed = subprocess.run(
                [zstd, "-19", "-c"], input=fake_image, capture_output=True, check=True,
                shell=False,
            )
            legacy = root / "legacy.zst"
            legacy.write_bytes(completed.stdout)
            with self.assertRaises(module.ReleaseBuildError) as ctx:
                module.verify_release_payload(legacy, runner=FakeExt4Runner())
            self.assertIn("real ext4", str(ctx.exception))

    def test_payload_streaming_never_holds_full_bytes_in_capture_seam(self) -> None:
        """Streaming regression: payload zstd must stream, never capture.

        Fails if unbounded ``.read()``/full-payload bytes retention is
        reintroduced: a strict runner refuses any payload ``zstd`` through
        the capture seam, the build→verify round trip must still produce
        byte-identical-valid results through the streaming seam, and the
        production source must contain no capture/whole-file read in the
        payload transfer path.
        """
        import inspect

        class StrictStreamingRunner(FakeExt4Runner):
            def run(self, command, *, timeout_seconds=None) -> object:
                if list(command)[0] == "zstd":
                    raise AssertionError(
                        "payload zstd must use stream_to_file, not run() capture"
                    )
                return super().run(command, timeout_seconds=timeout_seconds)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            staging = self._staging(root)
            kernel = root / "vmlinuz"
            kernel.write_bytes(b"generic-kernel" * 64)
            initramfs = root / "initrd"
            initramfs.write_bytes(b"generic-initramfs" * 64)
            output = root / "payload.ext4.zst"
            runner = StrictStreamingRunner()
            result = module.build_release_payload(
                staging_dir=staging,
                kernel_path=kernel,
                initramfs_path=initramfs,
                output=output,
                profile_id="legacy-x86-i686",
                release_id="greia-0.15.0",
                filesystem_bytes=4 * 1024 * 1024,
                minimum_slot_bytes=5 * 1024 * 1024,
                runner=runner,
            )
            # Compression streamed exactly once; capture seam never saw zstd.
            self.assertEqual(
                [cmd[:3] for cmd in runner.streamed_commands], [["zstd", "-19", "-c"]]
            )
            self.assertNotIn("zstd", [cmd[0] for cmd in runner.commands])
            verify_runner = StrictStreamingRunner()
            payload = module.verify_release_payload(output, runner=verify_runner)
            self.assertEqual(
                [cmd[:3] for cmd in verify_runner.streamed_commands],
                [["zstd", "-d", "-c"]],
            )
            self.assertNotIn("zstd", [cmd[0] for cmd in verify_runner.commands])
            # Byte-identical-valid results through the streaming path.
            self.assertEqual(payload["uncompressed_bytes"], result["uncompressed_bytes"])
            raw = subprocess.run(
                ["zstd", "-d", "-c", "--", str(output)],
                check=True,
                capture_output=True,
                shell=False,
            ).stdout
            self.assertEqual(len(raw), result["uncompressed_bytes"])
            self.assertEqual(raw[1080:1082], b"\x53\xef")
            # Static call-graph guard: the payload transfer path holds no
            # capture helper, whole-file read, unbounded read, or zstd call
            # through the capture seam. Bounded head reads (size argument)
            # and small debugfs control-probe stdout stay allowed.
            for fn in (module.build_release_payload, module.verify_release_payload):
                source = inspect.getsource(fn)
                self.assertNotIn("_run_capture", source)
                self.assertNotIn("read_bytes", source)
                self.assertNotIn(".read()", source)
                self.assertNotIn('run(["zstd"', source)
                self.assertNotIn("run(['zstd'", source)
                self.assertIn("stream", source)

    def test_streaming_primitive_holds_bounded_ram(self) -> None:
        """Production proof: the streaming primitive holds bounded RAM.

        Streams a 32 MiB payload through the real
        ``SubprocessReleaseRunner.stream_to_file`` (the exact production
        mechanism, child fd wired to the file) while tracing Python
        allocations: peak traced RAM must stay far below the payload size,
        which a capture-into-bytes implementation could never satisfy.
        """
        import tracemalloc

        payload_bytes = 32 * 1024 * 1024
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "input.bin"
            with source.open("wb") as handle:
                row = b"greia-streaming-proof-row-0123456789\n"
                remaining = payload_bytes
                while remaining > 0:
                    chunk = row * min(4096, (remaining + len(row) - 1) // len(row))
                    chunk = chunk[:remaining]
                    handle.write(chunk)
                    remaining -= len(chunk)
            self.assertEqual(source.stat().st_size, payload_bytes)
            streamed = root / "input.bin.zst"
            runner = module.SubprocessReleaseRunner()
            tracemalloc.start()
            try:
                runner.stream_to_file(
                    ["zstd", "-19", "-c", "--", str(source)],
                    streamed,
                    timeout_seconds=600.0,
                )
                _, peak = tracemalloc.get_traced_memory()
            finally:
                tracemalloc.stop()
            self.assertLess(
                peak,
                payload_bytes // 4,
                f"streaming held {peak} traced bytes for a {payload_bytes}-byte payload",
            )
            # Streamed bytes are valid: magic + round-trip to the input.
            self.assertEqual(streamed.read_bytes()[:4], b"\x28\xb5\x2f\xfd")
            recovered = subprocess.run(
                ["zstd", "-d", "-c", "--", str(streamed)],
                check=True,
                capture_output=True,
                shell=False,
            ).stdout
            self.assertEqual(recovered, source.read_bytes())

    def test_no_tar_magic_in_production_source(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        build_source = (repo / "tools" / "build_release.py").read_text(encoding="utf-8")
        self.assertNotIn("GREIA-SLOT-V1", build_source)
        self.assertNotIn("PAYLOAD_MAGIC", build_source)
        self.assertNotIn("_deterministic_tar_bytes", build_source)
        self.assertNotIn("_payload_header", build_source)
        for path in sorted((repo / "src").rglob("*.py")):
            self.assertNotIn("GREIA-SLOT-V1", path.read_text(encoding="utf-8"))

    def test_persistent_contract_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "a.json"
            second = root / "b.json"
            module.build_persistent_contract(first)
            module.build_persistent_contract(second)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            parsed = json.loads(first.read_text(encoding="utf-8"))
            self.assertEqual(parsed["schema_version"], 1)
            self.assertIn("child-profiles", parsed["namespaces"])

    def test_hardware_support_rejects_executable_hooks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pool = root / "pool-root"
            pool.mkdir()
            (pool / "pool").mkdir()
            (pool / "manifest.json").write_text("{}", encoding="utf-8")
            hook = pool / "evil.hook"
            hook.write_text("#!/bin/sh\n", encoding="utf-8")
            hook.chmod(0o755)
            with self.assertRaises(module.ReleaseBuildError):
                module._assert_no_hooks(pool)


if __name__ == "__main__":
    unittest.main()
