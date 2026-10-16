"""Offline tests for tools/dev_source_deploy.py (stage filter, remote commands)."""

from __future__ import annotations

import io
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path, PurePosixPath

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

import dev_source_deploy as deploy  # noqa: E402


class FakeRunner:
    def __init__(self, codes: tuple[int, ...] = ()) -> None:
        self.calls: list[tuple[list[str], Path | None]] = []
        self._codes = list(codes)

    def run(self, argv, stdin_path=None) -> int:
        self.calls.append((list(argv), stdin_path))
        return self._codes.pop(0) if self._codes else 0


class BundleFilterTests(unittest.TestCase):
    def test_destinations(self) -> None:
        dest = deploy.bundle_destination
        self.assertEqual(dest("src/greia_platform/x.py"), PurePosixPath("bundle/opt/greia-os/src/greia_platform/x.py"))
        self.assertEqual(dest("assets/fonts/a.ttf"), PurePosixPath("bundle/opt/greia-os/assets/fonts/a.ttf"))
        self.assertEqual(dest("assets/catalog/core_icons_v1.toml"), PurePosixPath("bundle/opt/greia-os/assets/catalog/core_icons_v1.toml"))
        self.assertEqual(dest("assets/visual/runtime/a.png"), PurePosixPath("bundle/opt/greia-os/assets/visual/runtime/a.png"))
        self.assertEqual(dest("tools/precompile_greia_bytecode.py"), PurePosixPath("bundle/tools/precompile_greia_bytecode.py"))
        self.assertEqual(dest("build/overlay/etc/systemd/system/greia-parent.service"), PurePosixPath("bundle/units/greia-parent.service"))

    def test_dropped(self) -> None:
        dest = deploy.bundle_destination
        for name in (
            "assets/source/x.svg", "assets/icons/source/y.svg", "assets/README.md",
            "assets/visual/source/a.svg", "assets/visual/candidates/a.png",
            "assets/catalog/shared_visuals_v1.json", "assets/boot/logo_contact_sheet.png",
            "src/__pycache__/x.cpython-311.pyc", "src/pkg/._x.py", "activities/a/.DS_Store",
            "activities/a/mod.pyc", "docs/x.md", "tools/other.py", "../escape", "/abs/path",
        ):
            self.assertIsNone(dest(name), name)

    def test_target_validation(self) -> None:
        self.assertEqual(deploy.validate_target("op@device.local"), "op@device.local")
        for bad in ("", "host", "-oProxyCommand=x@y", "a b@c", "op@host;rm", "op@-host", "op@host$(x)"):
            with self.assertRaises(deploy.DeployError, msg=bad):
                deploy.validate_target(bad)


class StageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.work = Path(tempfile.mkdtemp(prefix="greia-dev-deploy-test."))
        cls.bundle = cls.work / "bundle.tar.gz"
        stager = deploy.BundleStager(PROJECT_ROOT)
        cls.sha = stager.stage(cls.bundle, cls.work)
        with tarfile.open(cls.bundle) as tar:
            cls.members = tar.getmembers()
            cls.deployed = tar.extractfile("opt/greia-os/.deployed-sha").read().decode()
        cls.names = [m.name for m in cls.members]

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.work, ignore_errors=True)

    def test_sha_matches_head(self) -> None:
        head = subprocess.run(["git", "-C", str(PROJECT_ROOT), "rev-parse", "HEAD"],
                              check=True, capture_output=True, text=True).stdout.strip()
        self.assertEqual(self.sha, head)
        self.assertEqual(self.deployed.strip(), head)

    def test_no_noise(self) -> None:
        for name in self.names:
            parts = PurePosixPath(name).parts
            self.assertNotIn("__pycache__", parts, name)
            if name.startswith("opt/greia-os/assets/"):
                self.assertNotIn("source", parts, name)
            self.assertFalse(any(p.startswith("._") or p == ".DS_Store" for p in parts), name)
            self.assertFalse(name.endswith((".pyc", ".pyo")), name)

    def test_only_expected_roots_and_asset_subset(self) -> None:
        roots = {PurePosixPath(n).parts[0] for n in self.names}
        self.assertEqual(roots, {"opt", "usr", "units", "tools"})
        allowed = {"audio", "boot", "catalog", "fonts", "icons", "scenes", "visual"}
        top_assets = {PurePosixPath(n).parts[3] for n in self.names
                      if n.startswith("opt/greia-os/assets/") and len(PurePosixPath(n).parts) > 4}
        self.assertTrue(top_assets <= allowed, top_assets)
        for name in self.names:
            if name.startswith("opt/greia-os/assets/visual/") and not name.endswith("/visual"):
                self.assertTrue(name.startswith("opt/greia-os/assets/visual/runtime"), name)
            if name.startswith("opt/greia-os/assets/catalog/") and not name.endswith("/catalog"):
                self.assertTrue(name.endswith(".toml"), name)
        for required in ("opt/greia-os/src", "opt/greia-os/runtime/child-runtime.toml",
                         "opt/greia-os/activities", "tools/precompile_greia_bytecode.py",
                         "units/greia-launcher.service", "units/greia-parent.service"):
            self.assertIn(required, self.names)

    def test_index_present(self) -> None:
        self.assertIn("usr/share/greia/activity-index-v1.json", self.names)

    def test_headers_are_clean(self) -> None:
        for member in self.members:
            self.assertEqual((member.uid, member.gid, member.uname, member.gname), (0, 0, "", ""))
            self.assertFalse(member.pax_headers)
            self.assertIn(member.mode, (0o755, 0o644))


class RemoteCommandTests(unittest.TestCase):
    def test_ssh_argv_is_batch_and_option_safe(self) -> None:
        device = deploy.RemoteDevice("op@dev", FakeRunner())
        argv = device.ssh_argv("true")
        self.assertEqual(argv[:5], ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15"])
        self.assertEqual(argv[-3:], ["--", "op@dev", "true"])

    def test_sudo_quoting_round_trips(self) -> None:
        tricky = "a b'c\"; rm -rf /; $(x)\n"
        command = deploy.RemoteDevice.sudo(["tar", tricky])
        self.assertEqual(shlex.split(command), ["sudo", "-n", "tar", tricky])
        script = deploy.RemoteDevice.sudo_script(tricky)
        self.assertEqual(shlex.split(script), ["sudo", "-n", "/bin/sh", "-c", tricky])

    def test_push_sequence(self) -> None:
        runner = FakeRunner()
        device = deploy.RemoteDevice("op@dev", runner)
        device.push(Path("/stage/bundle.tar.gz"))
        commands = [shlex.split(call[0][-1]) for call in runner.calls]
        self.assertTrue(all(c[:2] == ["sudo", "-n"] for c in commands))
        self.assertEqual(commands[0], ["sudo", "-n", "true"])
        self.assertIn("/var/lib/greia/deploy/new", commands[2])
        self.assertEqual(runner.calls[2][1], Path("/stage/bundle.tar.gz"))
        self.assertEqual(commands[3][2:6], ["python3", "-I", "-B", "-c"])
        self.assertEqual(len(commands), 4)

    def test_push_stops_when_sudo_unavailable(self) -> None:
        runner = FakeRunner(codes=(1,))
        with self.assertRaises(deploy.DeployError) as ctx:
            deploy.RemoteDevice("op@dev", runner).push(Path("/x"))
        self.assertIn("sudo -n", str(ctx.exception))
        self.assertEqual(len(runner.calls), 1)

    def test_parse_failure_stops(self) -> None:
        runner = FakeRunner(codes=(0, 0, 0, 1))
        with self.assertRaises(deploy.DeployError):
            deploy.RemoteDevice("op@dev", runner).push(Path("/x"))

    def test_swap_script_contents_and_quoting(self) -> None:
        paths = deploy.DevicePaths(deploy="/d ir/it's")
        script = deploy.RemoteScripts(paths).swap()
        self.assertIn("D=" + shlex.quote("/d ir/it's"), script)
        self.assertIn("systemctl stop $SERVICES", script)
        self.assertIn("chmod -R a-w", script)
        self.assertIn("precompile_greia_bytecode.py", script)
        self.assertIn("SERVICES='greia-launcher greia-parent'", script)

    def test_swap_runs_scripts_through_sudo_sh(self) -> None:
        runner = FakeRunner()
        deploy.RemoteDevice("op@dev", runner).swap()
        commands = [shlex.split(call[0][-1]) for call in runner.calls]
        self.assertEqual(commands[1][:5], ["sudo", "-n", "/bin/sh", "-c", deploy.RemoteScripts().swap()])
        self.assertIn("NRestarts", commands[3][-1])

    def test_cleanup_scope(self) -> None:
        script = deploy.RemoteScripts().cleanup()
        self.assertIn('rm -rf "$PREV" "$NEW"', script)
        self.assertNotIn("/opt/greia-os", script)

    def test_parse_gate_code_compiles(self) -> None:
        compile(deploy.PARSE_GATE_CODE, "<gate>", "exec")


if __name__ == "__main__":
    unittest.main()
