"""Source-only contract tests for the one-phase A/B stage diagnostic."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.x8_qemu import stage_diagnostic as _stage
from tools.x8_qemu.lifecycle import LifecycleHarnessError


def _collector_fixture() -> dict[str, object]:
    return {
        "schema_version": 1,
        "classification": "DIAGNOSTIC_COLLECTION_ONLY",
        "health_acceptance": "NOT_EVALUATED",
        "partitions": {
            "PERSIST": {
                "mount": "ok",
                "files": {
                "phase-result.json": {
                    "status": "ok",
                    "path": "greia/namespaces/parent-credentials/x8-control/phase-result.json",
                    "json": {
                        "phase": "update-stage",
                        "operation": "STAGE_CURRENT_CANDIDATE",
                        "status": "FAILED",
                        "error": "UpdatePrivilegedError: staging refused",
                        "cause_chain": ["OSError: write failed"],
                        "response": {"status": "REFUSED", "reason": "fixture refusal"},
                    },
                },
                "service-diagnostics.txt": {
                    "status": "ok",
                    "path": "greia/namespaces/parent-credentials/x8-control/service-diagnostics.txt",
                    "text": "greia-system-update.service: Result=exit-code",
                },
                },
            }
        },
        "errors": [],
        "cleanup": {"attempted": True, "status": "ok"},
    }


class StageDiagnosticTests(unittest.TestCase):
    def _inputs(self, root: Path) -> tuple[Path, Path, Path]:
        source = root / "accepted-A.img"
        bundle = root / "next.greiaupdate"
        output = root / "diagnostic-output"
        source.write_bytes(b"accepted-A-image" * 16)
        bundle.write_bytes(b"verified-next-bundle" * 16)
        return source, bundle, output

    def _patch_common(self):
        return (
            mock.patch.object(_stage, "require_product_host"),
            mock.patch.object(_stage, "select_install_qemu_binary", return_value="qemu-system-i386"),
            mock.patch.object(
                _stage,
                "product_boot_qemu_argv",
                side_effect=lambda **kw: (
                    ["qemu-system-i386", "-m", str(kw["memory_mib"])],
                    Path(kw["output_dir"]) / "generated.serial.log",
                    Path(kw["output_dir"]) / "generated.host.log",
                ),
            ),
        )

    def test_one_stage_boot_then_offline_collects_failure_response_and_cause(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, bundle, output = self._inputs(root)
            original_sha = hashlib.sha256(source.read_bytes()).hexdigest()
            events: list[str] = []
            clone = output / "stage-diagnostic-clone.img"

            def clone_fn(origin: Path, target: Path) -> dict[str, object]:
                events.append("clone")
                target.write_bytes(b"fresh-disposable-clone")
                return {"source_sha256": original_sha, "clone": str(target)}

            def candidate_fn(image: Path, candidate: Path) -> dict[str, object]:
                events.append("candidate-injection")
                self.assertEqual(image, clone)
                self.assertEqual(candidate, bundle)
                return {"candidate_bytes": candidate.stat().st_size}

            def slot_fn(image: Path, slot: str) -> dict[str, object]:
                events.append("slot-injection")
                self.assertEqual(slot, "A")
                return {"slot": slot, "source_image_mutated": False}

            def materialize_fn(control_dir: Path, control_image: Path) -> dict[str, object]:
                events.append("materialize")
                phase = json.loads((control_dir / "phase.json").read_text())
                self.assertEqual(phase["phase"], "update-stage")
                self.assertEqual(phase.get("inputs", {}), {})
                control_image.write_bytes(b"phase-only-control-disk")
                return {"phase": phase["phase"], "bytes": control_image.stat().st_size}

            def boot_fn(phase: str, argv: list[str], serial: Path, host: Path) -> None:
                events.append("boot:" + phase)
                self.assertEqual(phase, "update-stage")
                self.assertEqual(argv, ["qemu-system-i386", "-m", "1024"])
                self.assertEqual(serial.name, "generated.serial.log")
                self.assertEqual(host.name, "generated.host.log")
                raise LifecycleHarnessError("phase update-stage failed (exit 1): fixture")

            def collect_fn(image: Path) -> dict[str, object]:
                events.append("collect")
                self.assertEqual(image, clone)
                return _collector_fixture()

            common = self._patch_common()
            with common[0], common[1], common[2]:
                result = _stage.run_stage_diagnostic(
                    installed_image=source,
                    release_bundle=bundle,
                    output_dir=output,
                    clone_fn=clone_fn,
                    candidate_inject_fn=candidate_fn,
                    slot_inject_fn=slot_fn,
                    materialize_fn=materialize_fn,
                    boot_fn=boot_fn,
                    collect_fn=collect_fn,
                )

            self.assertEqual(
                events,
                ["clone", "candidate-injection", "slot-injection", "materialize", "boot:update-stage", "collect"],
            )
            self.assertEqual(result["classification"], "STAGE_DIAGNOSTIC_ONLY")
            self.assertEqual(result["health_acceptance"], "NOT_EVALUATED")
            self.assertEqual(result["stage_outcome"], "FAILED_OR_NOT_COMPLETED")
            self.assertTrue(result["stage_attempted"])
            self.assertFalse(result["boot_returned"])
            self.assertEqual(result["collector_outcome"], "COLLECTED")
            self.assertTrue(result["source_image_unchanged"])
            self.assertEqual(
                result["control_evidence"]["phase-result.json"]["json"]["response"]["status"],
                "REFUSED",
            )
            self.assertEqual(
                result["control_evidence"]["phase-result.json"]["json"]["cause_chain"],
                ["OSError: write failed"],
            )
            self.assertNotIn("ok", result)
            self.assertEqual(_stage._result_exit_code(result), 1)
            self.assertEqual(json.loads((output / "result.json").read_text())["stage_phase"], "update-stage")
            self.assertTrue((output / "offline-collector" / "diagnostics.json").is_file())
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), original_sha)

    def test_collector_runs_after_candidate_preparation_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, bundle, output = self._inputs(root)
            events: list[str] = []

            def clone_fn(_origin: Path, target: Path) -> dict[str, object]:
                target.write_bytes(b"clone")
                return {"clone": str(target)}

            def candidate_fn(_image: Path, _bundle: Path) -> dict[str, object]:
                events.append("candidate-injection")
                raise LifecycleHarnessError("fixture injection failure")

            def collect_fn(_image: Path) -> dict[str, object]:
                events.append("collect")
                return _collector_fixture()

            common = self._patch_common()
            with common[0], common[1], common[2]:
                result = _stage.run_stage_diagnostic(
                    installed_image=source,
                    release_bundle=bundle,
                    output_dir=output,
                    clone_fn=clone_fn,
                    candidate_inject_fn=candidate_fn,
                    collect_fn=collect_fn,
                )

            self.assertEqual(events, ["candidate-injection", "collect"])
            self.assertEqual(result["stage_outcome"], "FAILED_OR_NOT_COMPLETED")
            self.assertEqual(result["collector_outcome"], "COLLECTED")

    def test_default_product_boot_entry_uses_2400s_config_and_neutral_outcome(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, bundle, output = self._inputs(root)
            calls: list[tuple[str, int, list[str]]] = []
            common = self._patch_common()

            def boot(self, *, phase, argv, serial_log, host_log):
                calls.append((phase, self.config.timeout_seconds, argv))

            with common[0], common[1], common[2], mock.patch.object(
                _stage.ProductHarness, "_boot_installed_phase", boot
            ):
                result = _stage.run_stage_diagnostic(
                    installed_image=source,
                    release_bundle=bundle,
                    output_dir=output,
                    clone_fn=lambda _src, dst: {"clone": str(dst)} if dst.write_bytes(b"clone") else {},
                    candidate_inject_fn=lambda *_: {"injected": True},
                    slot_inject_fn=lambda *_: {"slot": "A"},
                    materialize_fn=lambda _control, image: {"bytes": image.write_bytes(b"ctl")},
                    collect_fn=lambda _image: _collector_fixture(),
                )
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0][0], "update-stage")
            self.assertEqual(calls[0][1], 2400)
            self.assertTrue(result["stage_attempted"])
            self.assertTrue(result["boot_returned"])
            self.assertEqual(result["stage_outcome"], "BOOT_CALL_RETURNED_NO_CAPTURED_FAILURE")
            self.assertNotIn("PASS", result["stage_outcome"])
            self.assertTrue(result["source_image_unchanged"])
            self.assertTrue(result["release_bundle_unchanged"])
            self.assertEqual(_stage._result_exit_code(result), 0)

    def test_collector_errors_or_cleanup_failure_make_result_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, bundle, output = self._inputs(root)
            clone = output / "stage-diagnostic-clone.img"
            diagnostics = _collector_fixture()
            diagnostics["errors"] = [{"stage": "mount", "error": "fixture"}]
            diagnostics["cleanup"] = {"attempted": True, "status": "failed"}
            common = self._patch_common()
            with common[0], common[1], common[2]:
                result = _stage.run_stage_diagnostic(
                    installed_image=source,
                    release_bundle=bundle,
                    output_dir=output,
                    clone_fn=lambda _src, dst: dst.write_bytes(b"clone") or {"clone": str(dst)},
                    candidate_inject_fn=lambda *_: {"injected": True},
                    slot_inject_fn=lambda *_: {"slot": "A"},
                    materialize_fn=lambda _control, image: image.write_bytes(b"ctl") or {"ok": True},
                    boot_fn=lambda *_: None,
                    collect_fn=lambda _image: diagnostics,
                )
            self.assertEqual(result["collector_outcome"], "COLLECTED_WITH_ERRORS")
            self.assertTrue(result["collector_error_present"])
            self.assertEqual(_stage._result_exit_code(result), 1)

    def test_source_mutation_is_recorded_and_makes_result_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, bundle, output = self._inputs(root)
            common = self._patch_common()

            def boot_mutates_source(*_args) -> None:
                source.write_bytes(b"unexpected source mutation")

            with common[0], common[1], common[2]:
                result = _stage.run_stage_diagnostic(
                    installed_image=source,
                    release_bundle=bundle,
                    output_dir=output,
                    clone_fn=lambda _src, dst: dst.write_bytes(b"clone") or {"clone": str(dst)},
                    candidate_inject_fn=lambda *_: {"injected": True},
                    slot_inject_fn=lambda *_: {"slot": "A"},
                    materialize_fn=lambda _control, image: image.write_bytes(b"ctl") or {"ok": True},
                    boot_fn=boot_mutates_source,
                    collect_fn=lambda _image: _collector_fixture(),
                )
            self.assertFalse(result["source_image_unchanged"])
            self.assertEqual(_stage._result_exit_code(result), 1)

    def test_bundle_mutation_is_recorded_and_makes_result_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, bundle, output = self._inputs(root)
            common = self._patch_common()

            def boot_mutates_bundle(*_args) -> None:
                bundle.write_bytes(b"unexpected bundle mutation")

            with common[0], common[1], common[2]:
                result = _stage.run_stage_diagnostic(
                    installed_image=source,
                    release_bundle=bundle,
                    output_dir=output,
                    clone_fn=lambda _src, dst: {"clone": str(dst)} if dst.write_bytes(b"clone") else {},
                    candidate_inject_fn=lambda *_: {"injected": True},
                    slot_inject_fn=lambda *_: {"slot": "A"},
                    materialize_fn=lambda _control, image: {"bytes": image.write_bytes(b"ctl")},
                    boot_fn=boot_mutates_bundle,
                    collect_fn=lambda _image: _collector_fixture(),
                )
            self.assertTrue(result["source_image_unchanged"])
            self.assertFalse(result["release_bundle_unchanged"])
            self.assertEqual(_stage._result_exit_code(result), 1)

    def test_existing_output_refuses_before_host_operations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, bundle, output = self._inputs(root)
            output.mkdir()
            with mock.patch.object(_stage, "require_product_host") as host:
                with self.assertRaises(LifecycleHarnessError):
                    _stage.run_stage_diagnostic(
                        installed_image=source,
                        release_bundle=bundle,
                        output_dir=output,
                    )
            host.assert_not_called()
            self.assertEqual(source.read_bytes(), b"accepted-A-image" * 16)

    def test_missing_bundle_does_not_create_output_or_clone(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, bundle, output = self._inputs(root)
            bundle.unlink()
            with mock.patch.object(_stage, "require_product_host") as host:
                with self.assertRaises(LifecycleHarnessError):
                    _stage.run_stage_diagnostic(
                        installed_image=source,
                        release_bundle=bundle,
                        output_dir=output,
                    )
            host.assert_not_called()
            self.assertFalse(output.exists())
            self.assertEqual(source.read_bytes(), b"accepted-A-image" * 16)


if __name__ == "__main__":
    unittest.main()
