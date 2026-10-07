"""Session 03 owner-release CLI source-level contract tests.

These tests exercise orchestration through a fake process runner only. They do
not compose roots, build installers/images, run debootstrap, invoke QEMU,
mount/loop devices, or perform privileged work.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "greia_release_tool_session03",
    ROOT / "tools" / "greia_release.py",
)
assert SPEC is not None and SPEC.loader is not None
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)

VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
PROFILE = "acer-aspire-one-i386-ab"
FULL_SHA = "ab" * 20


class FakeRunner:
    def __init__(self, *, fail_label: str | None = None) -> None:
        self.commands: list[list[str]] = []
        self.interactive: list[list[str]] = []
        self.fail_label = fail_label

    def run(
        self,
        command,
        *,
        cwd,
        env=None,
        log_path=None,
        capture=False,
        interactive=False,
    ):
        argv = [str(item) for item in command]
        self.commands.append(argv)
        if interactive:
            self.interactive.append(argv)
        if self.fail_label and self.fail_label in " ".join(argv):
            return module.CommandResult("", "forced failure", 9)

        if argv[:3] == ["git", "rev-parse", "HEAD"]:
            return module.CommandResult(FULL_SHA + "\n", "", 0)

        if len(argv) >= 2 and argv[0] == "bash" and argv[1].endswith(
            "compose-release-profile.sh"
        ):
            target = Path(argv[3])
            live = Path(argv[4])
            target.mkdir(parents=True, exist_ok=True)
            live.mkdir(parents=True, exist_ok=True)
            (target / "etc").mkdir(exist_ok=True)
            (target / "etc" / "target.txt").write_text("target", encoding="utf-8")
            boot = target / "boot"
            boot.mkdir(parents=True)
            (boot / "vmlinuz-6.1-greia").write_bytes(b"kernel")
            (boot / "initrd.img-6.1-greia").write_bytes(b"initramfs")
            status = target / "var" / "lib" / "dpkg"
            status.mkdir(parents=True)
            (status / "status").write_text("Package: base\n", encoding="utf-8")
            (live / "etc").mkdir(exist_ok=True)
            (live / "etc" / "live-installer.txt").write_text(
                "live-installer", encoding="utf-8"
            )
            pool = live / "opt" / "greia-hardware-support"
            (pool / "pool").mkdir(parents=True, exist_ok=True)
            (pool / "manifest.json").write_text("{}\n", encoding="utf-8")
            (pool / "Packages").write_bytes(b"")
            (pool / "Packages.gz").write_bytes(b"")
            if log_path is not None:
                Path(log_path).parent.mkdir(parents=True, exist_ok=True)
                Path(log_path).write_text("release roots ok\n", encoding="utf-8")
            return module.CommandResult("", "", 0)

        if any(part.endswith("build_release.py") for part in argv):
            subcommand = argv[argv.index(next(
                part for part in argv if part.endswith("build_release.py")
            )) + 1]
            if subcommand == "build-payload":
                output = Path(argv[argv.index("--output") + 1])
                receipt = Path(argv[argv.index("--receipt-output") + 1])
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(b"payload-zstd-fixture")
                payload_sha = hashlib.sha256(output.read_bytes()).hexdigest()
                receipt_doc = {
                    "schema_version": 1,
                    "payload_sha256": payload_sha,
                    "payload_compressed_bytes": output.stat().st_size,
                    "payload_uncompressed_bytes": 123456,
                    "minimum_slot_bytes": 123456 + 1024 * 1024,
                    "profile_id": PROFILE,
                    "release_id": f"greia-{VERSION}",
                }
                receipt.write_text(
                    json.dumps(receipt_doc, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                return module.CommandResult(
                    json.dumps(
                        {
                            "output": str(output),
                            "size": output.stat().st_size,
                            "uncompressed_bytes": 123456,
                            "minimum_slot_bytes": receipt_doc["minimum_slot_bytes"],
                            "receipt_output": str(receipt),
                            "receipt": receipt_doc,
                        }
                    ),
                    "",
                    0,
                )
            if subcommand == "verify-payload":
                return module.CommandResult(
                    json.dumps({"checked_paths": 13, "uncompressed_bytes": 123456}),
                    "",
                    0,
                )
            if subcommand == "build-hardware-support":
                output = Path(argv[argv.index("--output") + 1])
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(b"support-zstd-fixture")
                return module.CommandResult(
                    json.dumps(
                        {
                            "output": str(output),
                            "size": output.stat().st_size,
                            "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
                            "extracted_bytes_bound": 8192,
                        }
                    ),
                    "",
                    0,
                )

        if any(part.endswith("greia_update.py") for part in argv):
            subcommand = argv[argv.index(next(
                part for part in argv if part.endswith("greia_update.py")
            )) + 1]
            if subcommand == "build":
                output = Path(argv[argv.index("--output") + 1])
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(b"greiaupdate-fixture")
                return module.CommandResult(
                    json.dumps(
                        {
                            "schema_version": 3,
                            "release_id": f"greia-{VERSION}",
                            "version": VERSION,
                            "profile": PROFILE,
                            "output": str(output),
                        }
                    ),
                    "",
                    0,
                )
            if subcommand == "inspect":
                return module.CommandResult(
                    json.dumps({"schema_version": 3, "profile": PROFILE}),
                    "",
                    0,
                )

        if len(argv) >= 2 and argv[0] == "bash" and argv[1].endswith(
            "write-image.sh"
        ):
            return module.CommandResult("", "", 0)

        raise AssertionError(f"unexpected fake command: {argv}")


class ReleaseCliTests(unittest.TestCase):
    def _doctor_green(self):
        return {"schema_version": 1, "ok": True, "checks": [], "profiles": []}

    def test_paths_use_final_release_schema(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = module.ReleasePaths.for_release(Path(directory), VERSION)
            self.assertEqual(paths.output_parent, Path(directory).resolve())
            self.assertEqual(paths.release_root.name, f"greia-{VERSION}")
            self.assertEqual(paths.updates_dir, paths.release_root / "updates")
            self.assertEqual(
                paths.intermediate_dir, paths.release_root / "intermediate"
            )
            self.assertEqual(paths.cache_dir.name, ".greia-cache")
            self.assertEqual(paths.work_parent.name, ".greia-work")

    def test_release_environment_enables_curated_composition_and_disables_bytecode(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = module.ReleasePaths.for_release(Path(directory), VERSION)
            env = module._release_environment(paths)
            self.assertEqual(env["PIP_RELEASE_BUILD"], "1")
            self.assertEqual(env["PYTHONDONTWRITEBYTECODE"], "1")

    def test_privileged_cli_disables_bytecode_before_project_imports(self) -> None:
        source = (ROOT / "tools" / "greia_release.py").read_text(encoding="utf-8")
        env_assignment = 'os.environ["PYTHONDONTWRITEBYTECODE"] = "1"'
        interpreter_assignment = "sys.dont_write_bytecode = True"
        first_project_import = "from build_profile import BuildProfile"
        self.assertIn(env_assignment, source)
        self.assertIn(interpreter_assignment, source)
        self.assertLess(source.index(env_assignment), source.index(first_project_import))
        self.assertLess(
            source.index(interpreter_assignment),
            source.index(first_project_import),
        )

    def test_doctor_is_explicit_about_host_root_commands_and_profile(self) -> None:
        report = module._doctor(
            (PROFILE,),
            system_name="Linux",
            machine="x86_64",
            euid=0,
            which=lambda name: f"/usr/bin/{name}",
            disk_free_bytes=100 * 1024**3,
        )
        self.assertTrue(report["ok"])
        checks = {item["name"]: item for item in report["checks"]}
        self.assertTrue(checks["host-os"]["ok"])
        self.assertTrue(checks["host-architecture"]["ok"])
        self.assertTrue(checks["root"]["ok"])
        self.assertTrue(checks["commands"]["ok"])
        self.assertTrue(checks["profiles"]["ok"])
        self.assertEqual(report["profiles"][0]["profile_id"], PROFILE)
        self.assertEqual(
            report["profiles"][0]["system_slot_bytes"], 1536 * 1024 * 1024
        )
        self.assertEqual(
            report["profiles"][0]["persistent_minimum_bytes"], 1024 * 1024 * 1024
        )

    def test_doctor_refuses_insufficient_workspace_from_profile_facts(self) -> None:
        report = module._doctor(
            (PROFILE,),
            system_name="Linux",
            machine="x86_64",
            euid=0,
            which=lambda name: f"/usr/bin/{name}",
            disk_free_bytes=1,
        )
        self.assertFalse(report["ok"])
        workspace = next(
            item for item in report["checks"] if item["name"] == "workspace"
        )
        self.assertFalse(workspace["ok"])
        self.assertIn("required>=", workspace["detail"])

    def test_doctor_fails_closed_on_wrong_host_and_missing_tools(self) -> None:
        report = module._doctor(
            (PROFILE,),
            system_name="Darwin",
            machine="arm64",
            euid=501,
            which=lambda name: None if name == "debootstrap" else f"/bin/{name}",
            disk_free_bytes=100 * 1024**3,
        )
        self.assertFalse(report["ok"])
        failed = {item["name"] for item in report["checks"] if not item["ok"]}
        self.assertEqual(
            failed,
            {"host-os", "host-architecture", "root", "commands"},
        )

    def test_normal_build_orchestrates_existing_owners_and_atomically_publishes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "out"
            runner = FakeRunner()
            result = module._build_release(
                version=VERSION,
                output_parent=out,
                profile_ids=(PROFILE,),
                runner=runner,
                doctor_result=self._doctor_green(),
            )
            release_root = out / f"greia-{VERSION}"
            self.assertTrue(release_root.is_dir())
            self.assertEqual(Path(result["output"]), release_root.resolve())
            report = json.loads(
                (release_root / "release-report.json").read_text(encoding="utf-8")
            )
            self.assertEqual(report["schema_version"], module.REPORT_SCHEMA_VERSION)
            self.assertEqual(report["source_commit"], FULL_SHA)
            self.assertEqual(report["status"], "complete")
            self.assertEqual(
                report["public_artifacts"],
                [f"updates/{PROFILE}.greiaupdate"],
            )
            self.assertEqual(report["setup_image"]["status"], "deferred")
            self.assertEqual(report["setup_image"]["session"], 8)
            serialized = json.dumps(report, sort_keys=True)
            self.assertNotIn(".greia-work", serialized)
            self.assertNotIn('"output":', json.dumps(report["profiles"][0]["payload"]["producer"]))
            self.assertNotIn(
                '"output":',
                json.dumps(report["profiles"][0]["hardware_support"]["producer"]),
            )
            self.assertNotIn(
                '"output":', json.dumps(report["profiles"][0]["bundle"]["manifest"])
            )
            self.assertTrue(
                (release_root / "updates" / f"{PROFILE}.greiaupdate").is_file()
            )
            intermediate = release_root / "intermediate" / PROFILE
            self.assertTrue((intermediate / "payload.ext4.zst").is_file())
            self.assertTrue((intermediate / "payload-receipt.json").is_file())
            self.assertTrue((intermediate / "hardware-support.tar.zst").is_file())
            self.assertTrue((intermediate / "build.log").is_file())
            self.assertEqual(
                report["media_accounting"]["updates_total_bytes"],
                module._tree_bytes(release_root / "updates"),
            )
            self.assertEqual(
                report["media_accounting"]["intermediate_total_bytes"],
                module._tree_bytes(release_root / "intermediate"),
            )

            flat = [" ".join(command) for command in runner.commands]
            release_compose = [
                item for item in flat if "compose-release-profile.sh" in item
            ]
            self.assertEqual(len(release_compose), 1)
            self.assertNotIn("populate-hardware-support-pool.sh", " ".join(flat))
            payload_cmd = next(
                command
                for command in runner.commands
                if "build_release.py" in " ".join(command)
                and "build-payload" in command
            )
            self.assertIn("--filesystem-bytes", payload_cmd)
            self.assertEqual(
                payload_cmd[payload_cmd.index("--filesystem-bytes") + 1],
                str(1536 * 1024 * 1024),
            )
            self.assertNotIn("--minimum-slot-bytes", payload_cmd)
            bundle_cmd = next(
                command
                for command in runner.commands
                if "greia_update.py" in " ".join(command) and "build" in command
            )
            self.assertIn("--payload-receipt", bundle_cmd)
            self.assertIn("--profile-file", bundle_cmd)
            self.assertIn("--hardware-support", bundle_cmd)
            self.assertNotIn("--payload-uncompressed-bytes", bundle_cmd)
            self.assertNotIn("--minimum-slot-bytes", bundle_cmd)
            self.assertEqual(
                bundle_cmd[bundle_cmd.index("--persist-write") + 1],
                str(module.PERSIST_SCHEMA_CURRENT),
            )
            work_children = list((out / ".greia-work").iterdir())
            self.assertEqual(work_children, [])

    def test_failed_build_never_publishes_final_release_and_preserves_work(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "out"
            runner = FakeRunner(fail_label="compose-release-profile.sh")
            with self.assertRaises(module.ReleaseCliError) as raised:
                module._build_release(
                    version=VERSION,
                    output_parent=out,
                    profile_ids=(PROFILE,),
                    runner=runner,
                    doctor_result=self._doctor_green(),
                )
            self.assertIn("preserved work", str(raised.exception))
            self.assertFalse((out / f"greia-{VERSION}").exists())
            work_children = list((out / ".greia-work").iterdir())
            self.assertEqual(len(work_children), 1)

    def test_existing_release_output_refuses_before_runner_use(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "out"
            final = out / f"greia-{VERSION}"
            final.mkdir(parents=True)
            runner = FakeRunner()
            with self.assertRaises(module.ReleaseCliError):
                module._build_release(
                    version=VERSION,
                    output_parent=out,
                    profile_ids=(PROFILE,),
                    runner=runner,
                    doctor_result=self._doctor_green(),
                )
            self.assertEqual(runner.commands, [])

    def test_release_composition_adapter_and_direct_composer_own_cleanup(self) -> None:
        adapter = (ROOT / "build" / "compose-release-profile.sh").read_text(
            encoding="utf-8"
        )
        compose = (ROOT / "build" / "lib" / "compose.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn('safe_unmount_paths "${MOUNTS[@]}"', adapter)
        self.assertIn("trap cleanup EXIT", adapter)
        self.assertIn("populate-hardware-support-pool.sh", adapter)
        self.assertIn("mount_pool_cache", adapter)
        self.assertIn("_compose_direct_cleanup", compose)
        self.assertIn('safe_unmount_paths "${MOUNTS[@]}"', compose)

    def test_release_composer_uses_approved_activity_roster_and_indexes_installed_subset(self) -> None:
        compose = (ROOT / "build" / "lib" / "compose.sh").read_text(
            encoding="utf-8"
        )
        function = compose.split(
            "compose_install_target_content() {", 1
        )[1].split("compose_install_live_content() {", 1)[0]
        self.assertIn('if [[ "${PIP_RELEASE_BUILD:-0}" == "1" ]]', function)
        self.assertIn("tools/stage_release_activities.py", function)
        self.assertIn(
            'build/first-party-release-activities.toml',
            function,
        )
        self.assertIn(
            '--output "$installed_activity_root"',
            function,
        )
        self.assertIn(
            '--activities "$installed_activity_root"',
            function,
        )
        self.assertNotIn(
            '--activities "$project_root/activities"',
            function.split("# T33 built-in index:", 1)[1],
        )
        self.assertIn(
            '"$project_root/activities/" "$installed_activity_root/"',
            function,
        )

    def test_requested_version_must_match_repository_metadata(self) -> None:
        with self.assertRaises(module.ReleaseCliError) as raised:
            module._validate_version("99.99.99")
        self.assertIn("repository VERSION", str(raised.exception))

    def test_inspect_accepts_release_report_and_delegates_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = root / "release-report.json"
            report.write_text(
                json.dumps({"schema_version": 1, "status": "complete"}),
                encoding="utf-8",
            )
            runner = FakeRunner()
            self.assertEqual(module._inspect(report, runner)["status"], "complete")
            bundle = root / "one.greiaupdate"
            bundle.write_bytes(b"fixture")
            inspected = module._inspect(bundle, runner)
            self.assertEqual(inspected["schema_version"], 3)

    def test_write_media_requires_explicit_erase_and_keeps_confirmation_interactive(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "setup.img"
            image.write_bytes(b"image")
            runner = FakeRunner()
            with self.assertRaises(module.ReleaseCliError):
                module._write_media(
                    image=image,
                    device="/dev/sdz",
                    erase_device=False,
                    expand_root=False,
                    runner=runner,
                )
            self.assertEqual(runner.commands, [])
            module._write_media(
                image=image,
                device="/dev/sdz",
                erase_device=True,
                expand_root=False,
                runner=runner,
            )
            self.assertEqual(len(runner.interactive), 1)
            self.assertIn("--erase-device", runner.interactive[0])


class SafeMediaWriterTopologyTests(unittest.TestCase):
    """Narrow regression for the util-linux 2.39 flat-sibling safe-writer fix.

    util-linux 2.39 can return a disk and its partitions as flat siblings from
    ``lsblk --json <disk>`` instead of nested children. The pre-fix probe
    required exactly one entry, so every already-partitioned USB stick was
    refused as an "unexpected device tree". These tests pin the corrected
    rule only: direct ``part`` siblings of the confirmed whole disk are
    accepted, and an unrelated/mapper sibling is still refused.

    The probe is extracted from the shell script and executed against a
    stubbed ``lsblk``. Each fixture deliberately trips the *next* check after
    the topology gate so the assertion identifies the topology decision alone,
    without needing privileged devices, mounts or a real fingerprint.
    """

    PROBE_BEGIN = "python3 - \"$device\" \"$image\" \"$require_unmounted\" <<'PY'\n"
    PROBE_END = "\nPY\n"
    UNEXPECTED_TREE = "Target device inspection returned an unexpected device tree"

    @classmethod
    def setUpClass(cls) -> None:
        script = (ROOT / "build" / "write-image.sh").read_text(encoding="utf-8")
        begin = script.index(cls.PROBE_BEGIN) + len(cls.PROBE_BEGIN)
        cls.probe_source = script[begin : script.index(cls.PROBE_END, begin)]

    def _run_probe(self, tree: list[dict[str, object]]) -> str:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            stub_dir = workspace / "bin"
            stub_dir.mkdir()
            stub = stub_dir / "lsblk"
            stub.write_text(
                "#!/bin/sh\ncat <<'JSON'\n"
                + json.dumps({"blockdevices": tree})
                + "\nJSON\n",
                encoding="utf-8",
            )
            stub.chmod(0o755)
            image = workspace / "setup.img"
            # Deliberately larger than the target so the probe stops at the
            # size gate that immediately follows the topology gate.
            image.write_bytes(b"x" * 64)
            env = dict(os.environ)
            env["PATH"] = f"{stub_dir}{os.pathsep}{env['PATH']}"
            completed = subprocess.run(
                [sys.executable, "-c", self.probe_source, "/dev/sdz", str(image), "no"],
                capture_output=True,
                text=True,
                env=env,
                check=False,
            )
            return completed.stdout + completed.stderr

    @staticmethod
    def _disk(**overrides: object) -> dict[str, object]:
        node: dict[str, object] = {
            "path": "/dev/sdz",
            "type": "disk",
            "pkname": None,
            "size": 8086618112,
            "rm": True,
            "hotplug": False,
            "tran": "usb",
            "model": "iamaKey",
            "serial": "eca3505216d7d3",
            "wwn": None,
            "mountpoints": [],
        }
        node.update(overrides)
        return node

    @staticmethod
    def _part(index: int) -> dict[str, object]:
        return {
            "path": f"/dev/sdz{index}",
            "type": "part",
            "pkname": "sdz",
            "size": 3549184,
            "rm": True,
            "hotplug": False,
            "tran": None,
            "model": None,
            "serial": None,
            "wwn": None,
            "mountpoints": [],
        }

    def test_direct_partition_siblings_accepted_but_unrelated_sibling_refused(self) -> None:
        # A tiny target makes the 64-byte probe image larger than the disk, so
        # the run always stops at the size gate directly after the topology
        # gate. That keeps the test hermetic: findmnt/blkid are never reached,
        # so the result does not depend on the host's real block devices.
        partitioned = self._run_probe(
            [self._disk(size=8), self._part(1), self._part(2)]
        )
        self.assertNotIn(
            self.UNEXPECTED_TREE,
            partitioned,
            "a removable whole disk with its own partitions must pass the topology gate",
        )
        self.assertIn(
            "Image does not fit target",
            partitioned,
            "the probe must proceed past the topology gate to the size gate",
        )

        mapper_volume = self._run_probe(
            [
                self._disk(),
                self._part(1),
                {
                    "path": "/dev/mapper/greia-slot",
                    "type": "lvm",
                    "pkname": "sda2",
                    "size": 1073741824,
                    "rm": False,
                    "hotplug": False,
                    "tran": None,
                    "model": None,
                    "serial": None,
                    "wwn": None,
                    "mountpoints": [],
                },
            ]
        )
        self.assertIn(
            self.UNEXPECTED_TREE,
            mapper_volume,
            "an unrelated/mapper sibling must still be refused",
        )


if __name__ == "__main__":
    unittest.main()
