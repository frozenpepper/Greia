from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from tools.x8_qemu.diagnostics import _write_result, collect_image_diagnostics
from tools.x8_qemu.lifecycle import LifecycleHarnessError


def _tree(root: Path, files: dict[str, bytes]) -> Path:
    for relative, raw in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    return root


class OfflineImageDiagnosticsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.image = self.root / "failed-clone.img"
        self.image.write_bytes(b"stopped image fixture")
        self.a = _tree(self.root / "a", {
            "etc/greia-os/release-identity.json": b'{"slot":"A","release_id":"base"}\n',
        })
        self.b = _tree(self.root / "b", {
            "etc/greia-os/release-identity.json": b'{"slot":"B","release_id":"candidate"}\n',
        })
        self.persist = _tree(self.root / "persist", {
            "greia/namespaces/layout-authority/installed-layout.json": b'{"accepted_slot":"A"}\n',
            "greia/boot-journal/boot-journal.json": b'{"state":"update_staged"}\n',
            "greia/namespaces/parent-credentials/system-updates/status.json": b'{"phase":"staging"}\n',
            "greia/namespaces/parent-credentials/x8-control/phase-result.json": b'{"operation":"STAGE_CURRENT_CANDIDATE","status":"FAILED"}\n',
            "greia/namespaces/parent-credentials/x8-control/service-diagnostics.txt": b"stage service diagnostics\n",
        })
        self.calls: list[list[str]] = []
        self.cleanup_calls: list[tuple[tuple[Path, ...], str]] = []

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _runner(self, *, fail_partition: str | None = None):
        roots = {
            "/dev/loop7p2": self.a,
            "/dev/loop7p3": self.b,
            "/dev/loop7p4": self.persist,
        }

        def run(argv, **_kwargs):
            argv = [str(part) for part in argv]
            self.calls.append(argv)
            if argv[0].endswith("losetup"):
                return SimpleNamespace(returncode=0, stdout="/dev/loop7\n", stderr="")
            if argv[0].endswith("mount"):
                source, target = argv[-2], Path(argv[-1])
                if source == fail_partition:
                    return SimpleNamespace(returncode=32, stdout="", stderr="bad superblock")
                shutil.copytree(roots[source], target, dirs_exist_ok=True, symlinks=True)
                return SimpleNamespace(returncode=0, stdout="", stderr="")
            raise AssertionError(f"unexpected host command: {argv!r}")

        return run

    def _cleanup(self, mountpoints, loopdev):
        self.cleanup_calls.append((mountpoints, loopdev))
        for mountpoint in mountpoints:
            shutil.rmtree(mountpoint, ignore_errors=True)

    def _collect(self, *, runner=None, **kwargs):
        return collect_image_diagnostics(
            self.image,
            runner=runner or self._runner(),
            which=lambda name: f"/sbin/{name}",
            cleanup_fn=self._cleanup,
            temp_parent=self.root,
            **kwargs,
        )

    def test_reads_only_allowlisted_files_from_ro_ext4_partitions_and_cleans_owned_loop(self) -> None:
        result = self._collect()

        self.assertEqual(result["classification"], "DIAGNOSTIC_COLLECTION_ONLY")
        self.assertEqual(result["health_acceptance"], "NOT_EVALUATED")
        self.assertEqual(result["partitions"]["A"]["files"]["release_identity.json"]["json"]["slot"], "A")
        self.assertEqual(result["partitions"]["B"]["files"]["release_identity.json"]["json"]["release_id"], "candidate")
        persist_files = result["partitions"]["PERSIST"]["files"]
        self.assertEqual(persist_files["boot-journal.json"]["json"]["state"], "update_staged")
        self.assertEqual(persist_files["phase-result.json"]["json"]["status"], "FAILED")
        self.assertEqual(persist_files["service-diagnostics.txt"]["text"], "stage service diagnostics\n")
        self.assertEqual(
            {name: value["path"] for name, value in persist_files.items()},
            {
                "installed-layout.json": "greia/namespaces/layout-authority/installed-layout.json",
                "boot-journal.json": "greia/boot-journal/boot-journal.json",
                "status.json": "greia/namespaces/parent-credentials/system-updates/status.json",
                "phase-result.json": "greia/namespaces/parent-credentials/x8-control/phase-result.json",
                "service-diagnostics.txt": "greia/namespaces/parent-credentials/x8-control/service-diagnostics.txt",
            },
        )
        self.assertEqual(
            result["partitions"]["A"]["files"]["release_identity.json"]["path"],
            "etc/greia-os/release-identity.json",
        )

        attach = self.calls[0]
        self.assertEqual(attach[1:6], ["--read-only", "--partscan", "--show", "--find", str(self.image.resolve())])
        mounts = [argv for argv in self.calls if argv[0].endswith("mount")]
        self.assertEqual(len(mounts), 3)
        self.assertEqual({argv[-2] for argv in mounts}, {"/dev/loop7p2", "/dev/loop7p3", "/dev/loop7p4"})
        self.assertTrue(all(argv[argv.index("-o") + 1] == "ro,noload" for argv in mounts))
        self.assertEqual(self.cleanup_calls[0][1], "/dev/loop7")
        self.assertEqual(len(self.cleanup_calls[0][0]), 3)

    def test_b_mount_failure_does_not_skip_persist_and_reports_corrupt_filesystem(self) -> None:
        result = self._collect(runner=self._runner(fail_partition="/dev/loop7p3"))

        self.assertEqual(result["partitions"]["A"]["mount"], "ok")
        self.assertEqual(result["partitions"]["B"]["mount"], "failed")
        self.assertIn("bad superblock", result["partitions"]["B"]["mount_error"])
        self.assertEqual(result["partitions"]["PERSIST"]["mount"], "ok")
        self.assertEqual(len([call for call in self.calls if call[0].endswith("mount")]), 3)
        self.assertEqual(self.cleanup_calls[0][1], "/dev/loop7")

    def test_missing_b_identity_and_corrupt_journal_are_explicit_file_facts(self) -> None:
        (self.b / "etc/greia-os/release-identity.json").unlink()
        journal = self.persist / "greia/boot-journal/boot-journal.json"
        journal.write_bytes(b"not-json\n")

        result = self._collect()

        self.assertEqual(
            result["partitions"]["B"]["files"]["release_identity.json"]["status"],
            "missing",
        )
        self.assertEqual(
            result["partitions"]["PERSIST"]["files"]["boot-journal.json"]["status"],
            "invalid_json",
        )
        self.assertEqual(result["health_acceptance"], "NOT_EVALUATED")

    def test_symlinked_allowlisted_file_is_refused_without_reading_target(self) -> None:
        outside = self.root / "outside.json"
        outside.write_text('{"secret":"must not be read"}', encoding="utf-8")
        path = self.persist / "greia/boot-journal/boot-journal.json"
        path.unlink()
        path.symlink_to(outside)

        result = self._collect()

        journal = result["partitions"]["PERSIST"]["files"]["boot-journal.json"]
        self.assertEqual(journal["status"], "refused")
        self.assertNotIn("secret", json.dumps(journal))

    def test_image_must_be_regular_and_not_a_symlink(self) -> None:
        symlink = self.root / "image-link.img"
        symlink.symlink_to(self.image)
        with self.assertRaisesRegex(LifecycleHarnessError, "regular non-symlink"):
            collect_image_diagnostics(symlink)
        with self.assertRaisesRegex(LifecycleHarnessError, "regular non-symlink"):
            collect_image_diagnostics(self.root)

    def test_cleanup_is_attempted_after_mount_failure(self) -> None:
        self._collect(runner=self._runner(fail_partition="/dev/loop7p2"))
        self.assertEqual(len(self.cleanup_calls), 1)
        self.assertEqual(self.cleanup_calls[0][1], "/dev/loop7")

    def test_diagnostic_log_read_is_bounded_and_marks_oversized_file(self) -> None:
        log = self.persist / "greia/namespaces/parent-credentials/x8-control/service-diagnostics.txt"
        log.write_bytes(b"x" * (64 * 1024 + 1))

        result = self._collect()

        fact = result["partitions"]["PERSIST"]["files"]["service-diagnostics.txt"]
        self.assertEqual(fact["status"], "oversized")
        self.assertEqual(fact["limit_bytes"], 64 * 1024)
        self.assertNotIn("text", fact)

    def test_output_is_new_atomic_json_and_refuses_overwrite(self) -> None:
        output = self.root / "diagnostic-output"
        path = _write_result(output, {"classification": "DIAGNOSTIC_COLLECTION_ONLY"})

        self.assertEqual(path.name, "diagnostics.json")
        self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["classification"], "DIAGNOSTIC_COLLECTION_ONLY")
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        with self.assertRaisesRegex(LifecycleHarnessError, "refusing to overwrite"):
            _write_result(output, {"classification": "DIAGNOSTIC_COLLECTION_ONLY"})


if __name__ == "__main__":
    unittest.main()
