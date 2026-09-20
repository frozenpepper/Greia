"""Session 03 owner-release CLI source-level contract tests.

These tests exercise orchestration through a fake process runner only. They do
not compose roots, build installers/images, run debootstrap, invoke QEMU,
mount/loop devices, or perform privileged work.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
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


if __name__ == "__main__":
    unittest.main()
