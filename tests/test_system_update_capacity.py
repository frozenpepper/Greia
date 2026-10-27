from __future__ import annotations

import errno
import struct
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from greia_platform.system_updates import (
    _BLKGETSIZE64_IOCTL_32BIT,
    _BLKGETSIZE64_IOCTL_64BIT,
    UpdateBackendUnavailable,
    _blkgetsize64_ioctl_requests,
    _block_node_size_bytes,
)

_MIB = 1024 * 1024


class _Result:
    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class _Runner:
    def __init__(self, *, result: _Result | None = None, error: Exception | None = None) -> None:
        self._result = result if result is not None else _Result()
        self._error = error
        self.commands: list[list[str]] = []

    def run(self, command: object, *, check: bool = True) -> _Result:
        self.commands.append(list(command))  # type: ignore[arg-type]
        if self._error is not None:
            raise self._error
        return self._result


def _node(root: Path, name: str = "sda2") -> Path:
    path = root / name
    path.write_bytes(b"")
    return path


def _sysfs_root(root: Path, name: str, raw: str) -> Path:
    sysfs = root / "sysfs"
    directory = sysfs / name
    directory.mkdir(parents=True)
    (directory / "size").write_text(raw, encoding="ascii")
    return sysfs


class BlkGetsizeRequestTests(unittest.TestCase):
    def test_i386_and_x86_64_encodings_are_distinct(self) -> None:
        self.assertEqual(_BLKGETSIZE64_IOCTL_32BIT, 0x80041272)
        self.assertEqual(_BLKGETSIZE64_IOCTL_64BIT, 0x80081272)

    def test_native_request_precedes_the_alternate_encoding(self) -> None:
        self.assertEqual(
            _blkgetsize64_ioctl_requests(4),
            (_BLKGETSIZE64_IOCTL_32BIT, _BLKGETSIZE64_IOCTL_64BIT),
        )
        self.assertEqual(
            _blkgetsize64_ioctl_requests(8),
            (_BLKGETSIZE64_IOCTL_64BIT, _BLKGETSIZE64_IOCTL_32BIT),
        )


class BlockNodeCapacityTests(unittest.TestCase):
    def test_ioctl_observes_capacity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            node = _node(root)
            requests: list[int] = []

            def fake_ioctl(fd: int, request: int, arg: bytes) -> bytes:
                requests.append(request)
                return struct.pack("Q", 8 * _MIB)

            with mock.patch("fcntl.ioctl", side_effect=fake_ioctl):
                size = _block_node_size_bytes(
                    node,
                    expected_bytes=8 * _MIB,
                    sysfs_root=root / "missing-sysfs",
                )
            self.assertEqual(size, 8 * _MIB)
            self.assertEqual(requests[0], _blkgetsize64_ioctl_requests()[0])

    def test_i386_request_is_used_first_on_32bit_pointer_width(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            node = _node(root)
            requests: list[int] = []

            def fake_ioctl(fd: int, request: int, arg: bytes) -> bytes:
                requests.append(request)
                if request != _BLKGETSIZE64_IOCTL_32BIT:
                    raise OSError(errno.ENOTTY, "inappropriate ioctl")
                return struct.pack("Q", 4 * _MIB)

            with mock.patch(
                "greia_platform.system_updates._blkgetsize64_ioctl_requests",
                return_value=(_BLKGETSIZE64_IOCTL_32BIT, _BLKGETSIZE64_IOCTL_64BIT),
            ), mock.patch("fcntl.ioctl", side_effect=fake_ioctl):
                size = _block_node_size_bytes(
                    node, sysfs_root=root / "missing-sysfs"
                )
            self.assertEqual(size, 4 * _MIB)
            self.assertEqual(requests, [_BLKGETSIZE64_IOCTL_32BIT])

    def test_x86_64_request_is_used_first_on_64bit_pointer_width(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            node = _node(root)
            requests: list[int] = []

            def fake_ioctl(fd: int, request: int, arg: bytes) -> bytes:
                requests.append(request)
                if request != _BLKGETSIZE64_IOCTL_64BIT:
                    raise OSError(errno.ENOTTY, "inappropriate ioctl")
                return struct.pack("Q", 6 * _MIB)

            with mock.patch(
                "greia_platform.system_updates._blkgetsize64_ioctl_requests",
                return_value=(_BLKGETSIZE64_IOCTL_64BIT, _BLKGETSIZE64_IOCTL_32BIT),
            ), mock.patch("fcntl.ioctl", side_effect=fake_ioctl):
                size = _block_node_size_bytes(
                    node, sysfs_root=root / "missing-sysfs"
                )
            self.assertEqual(size, 6 * _MIB)
            self.assertEqual(requests, [_BLKGETSIZE64_IOCTL_64BIT])

    def test_ioctl_failure_falls_back_to_sysfs_sectors(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            node = _node(root)
            sysfs = _sysfs_root(root, node.name, "4096\n")
            with mock.patch(
                "fcntl.ioctl", side_effect=OSError(errno.ENOTTY, "inappropriate ioctl")
            ):
                size = _block_node_size_bytes(
                    node,
                    expected_bytes=4096 * 512,
                    sysfs_root=sysfs,
                )
            self.assertEqual(size, 4096 * 512)

    def test_sysfs_handles_extra_whitespace(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            node = _node(root)
            sysfs = _sysfs_root(root, node.name, " 8192 \n")
            with mock.patch("fcntl.ioctl", side_effect=OSError(errno.ENOTTY, "no")):
                size = _block_node_size_bytes(node, sysfs_root=sysfs)
            self.assertEqual(size, 8192 * 512)

    def test_invalid_sysfs_values_fall_through_to_blockdev(self) -> None:
        for raw in ("", "not-a-number", "-1", "0", "1.5", str((1 << 48) // 512 + 1)):
            with self.subTest(raw=raw), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                node = _node(root)
                sysfs = _sysfs_root(root, node.name, raw)
                runner = _Runner(result=_Result(stdout="1048576\n"))
                with mock.patch(
                    "fcntl.ioctl",
                    side_effect=OSError(errno.ENOTTY, "inappropriate ioctl"),
                ):
                    size = _block_node_size_bytes(
                        node,
                        sysfs_root=sysfs,
                        command_runner=runner,
                    )
                self.assertEqual(size, _MIB)

    def test_malformed_blockdev_output_is_rejected_with_causes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            node = _node(root)
            runner = _Runner(result=_Result(stdout="12x\n"))
            with mock.patch(
                "fcntl.ioctl", side_effect=OSError(errno.ENOTTY, "no ioctl")
            ), self.assertRaises(UpdateBackendUnavailable) as ctx:
                _block_node_size_bytes(
                    node,
                    sysfs_root=root / "absent",
                    command_runner=runner,
                )
            message = str(ctx.exception)
            self.assertIn("capacity is unobservable", message)
            self.assertIn("ioctl", message)
            self.assertIn("sysfs", message)
            self.assertIn("blockdev capacity is not an integer", message)

    def test_missing_blockdev_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            node = _node(root)
            runner = _Runner(error=FileNotFoundError("blockdev"))
            with mock.patch(
                "fcntl.ioctl", side_effect=OSError(errno.ENOTTY, "no ioctl")
            ), self.assertRaises(UpdateBackendUnavailable) as ctx:
                _block_node_size_bytes(
                    node,
                    sysfs_root=root / "absent",
                    command_runner=runner,
                )
            message = str(ctx.exception)
            self.assertIn("blockdev", message)
            self.assertIn("blockdev: blockdev", message)

    def test_blockdev_nonzero_exit_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            node = _node(root)
            runner = _Runner(result=_Result(returncode=1, stderr="denied"))
            with mock.patch(
                "fcntl.ioctl", side_effect=OSError(errno.ENOTTY, "no ioctl")
            ), self.assertRaises(UpdateBackendUnavailable) as ctx:
                _block_node_size_bytes(
                    node,
                    sysfs_root=root / "absent",
                    command_runner=runner,
                )
            self.assertIn("blockdev exited 1", str(ctx.exception))

    def test_blockdev_success_is_accepted_when_other_methods_fail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            node = _node(root)
            runner = _Runner(result=_Result(stdout="2097152\n"))
            with mock.patch(
                "fcntl.ioctl", side_effect=OSError(errno.ENOTTY, "no ioctl")
            ):
                size = _block_node_size_bytes(
                    node,
                    sysfs_root=root / "absent",
                    command_runner=runner,
                )
            self.assertEqual(size, 2 * _MIB)
            self.assertEqual(runner.commands[0][0], "blockdev")

    def test_mismatched_ioctl_capacity_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            node = _node(root)
            with mock.patch(
                "fcntl.ioctl", return_value=struct.pack("Q", 8 * _MIB)
            ), self.assertRaises(UpdateBackendUnavailable) as ctx:
                _block_node_size_bytes(
                    node,
                    expected_bytes=16 * _MIB,
                    sysfs_root=root / "absent",
                )
            message = str(ctx.exception)
            self.assertIn("does not match the installed layout", message)
            self.assertIn("8388608", message)
            self.assertIn("16777216", message)

    def test_mismatched_sysfs_capacity_is_refused_without_blockdev_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            node = _node(root)
            sysfs = _sysfs_root(root, node.name, "8192")
            runner = _Runner(result=_Result(stdout=str(16 * _MIB)))
            with mock.patch(
                "fcntl.ioctl", side_effect=OSError(errno.ENOTTY, "no ioctl")
            ), self.assertRaises(UpdateBackendUnavailable) as ctx:
                _block_node_size_bytes(
                    node,
                    expected_bytes=16 * _MIB,
                    sysfs_root=sysfs,
                    command_runner=runner,
                )
            self.assertIn("does not match the installed layout", str(ctx.exception))
            self.assertEqual(runner.commands, [])

    def test_missing_sysfs_and_ioctl_uses_blockdev(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            node = _node(root)
            runner = _Runner(result=_Result(stdout="4194304\n"))
            with mock.patch(
                "fcntl.ioctl", side_effect=OSError(errno.ENOTTY, "no ioctl")
            ):
                size = _block_node_size_bytes(
                    node,
                    expected_bytes=4 * _MIB,
                    sysfs_root=root / "absent",
                    command_runner=runner,
                )
            self.assertEqual(size, 4 * _MIB)

    def test_invalid_device_name_cannot_escape_sysfs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            node = root / ".."
            runner = _Runner(error=FileNotFoundError("blockdev"))
            with mock.patch(
                "fcntl.ioctl", side_effect=OSError(errno.ENOTTY, "no ioctl")
            ), self.assertRaises(UpdateBackendUnavailable) as ctx:
                _block_node_size_bytes(
                    node,
                    sysfs_root=root,
                    command_runner=runner,
                )
            self.assertIn("sysfs block form", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
