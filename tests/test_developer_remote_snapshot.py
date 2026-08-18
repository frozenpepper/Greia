from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS = PROJECT_ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from greia_remote import GreiaRemote, RemoteError, build_parser  # noqa: E402


PNG = b"\x89PNG\r\n\x1a\nagent-snapshot"


class DeveloperRemoteSnapshotTests(unittest.TestCase):
    def _remote(self, root: Path) -> GreiaRemote:
        key = root / "key"
        key.write_text("private\n", encoding="utf-8")
        return GreiaRemote(
            host="greia-dev.local",
            user="greia",
            key=key,
            known_hosts=root / "known_hosts",
        )

    def test_snapshot_collects_png_status_logs_and_local_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            remote = self._remote(root)
            output = root / "evidence"

            def devctl(*args: str, binary: bool = False, check: bool = True):
                del check
                if args == ("screenshot",):
                    self.assertTrue(binary)
                    return subprocess.CompletedProcess([], 0, PNG, b"")
                if args == ("status",):
                    return subprocess.CompletedProcess([], 0, '{"developer_remote": true}\n', "")
                if args == ("logs", "--service", "launcher", "--lines", "42"):
                    return subprocess.CompletedProcess([], 0, "launcher log\n", "")
                raise AssertionError(args)

            with mock.patch.object(remote, "devctl", side_effect=devctl):
                result = remote.snapshot(output, service="launcher", lines=42)

            self.assertEqual(result, output.resolve())
            self.assertEqual((output / "screen.png").read_bytes(), PNG)
            self.assertEqual(
                json.loads((output / "status.json").read_text(encoding="utf-8")),
                {"developer_remote": True},
            )
            self.assertEqual(
                (output / "logs.txt").read_text(encoding="utf-8"),
                "launcher log\n",
            )
            manifest = json.loads(
                (output / "snapshot.json").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["host"], "greia-dev.local")
            self.assertEqual(manifest["log_service"], "launcher")
            self.assertEqual(manifest["log_lines"], 42)
            self.assertEqual(
                manifest["files"], ["screen.png", "status.json", "logs.txt"]
            )

    def test_snapshot_rejects_unbounded_log_request_before_remote_access(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            remote = self._remote(root)
            with mock.patch.object(remote, "devctl") as devctl:
                with self.assertRaises(RemoteError):
                    remote.snapshot(root / "evidence", lines=5001)
                devctl.assert_not_called()

    def test_snapshot_cli_is_explicit_and_bounded(self) -> None:
        args = build_parser().parse_args(
            ["snapshot", "out/acer-observation", "--service", "launcher", "--lines", "250"]
        )
        self.assertEqual(args.command, "snapshot")
        self.assertEqual(args.output_dir, Path("out/acer-observation"))
        self.assertEqual(args.service, "launcher")
        self.assertEqual(args.lines, 250)


if __name__ == "__main__":
    unittest.main()
