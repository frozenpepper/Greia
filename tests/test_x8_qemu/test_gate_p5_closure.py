"""Gate P5 `LEGACY_PRODUCT_PATH_GREEN` closure composite tests (V5).

Proves the ``tools/x8_qemu/gate_p5.py`` fold composes the frozen legs
without redefining them:

- GREEN: ``build_gate_p5_record()`` binds install-leg + boot-health-leg
  P5.3 identity records (re-asserted at evidence time), the recovery
  stage facts, the live strictly-GREEN P5.4 record, the DEVICE-scope
  768 MiB envelope and the source HEAD, and closes the combined 8-step
  report through ``assert_lifecycle_transitions``.
- The live entry ``run_gate_p5_closure_product()`` runs legs in order
  install -> boot-health -> unhealthy build/verify -> recovery (with an
  explicit ``d31_fn``) -> boot-perf -> device budget, and refuses a
  missing ``d31_fn`` as ``BLOCKED`` naming the unpinned persist mapping
  (the V5 obligation: an unexecuted/BLOCKED recovery leg never closes).
- RED (never a partial green): non-green/missing boot-perf, a
  source-scope (non-device-measured) envelope, a mutated source image, a
  missing recovery stage, or a FAILED note that does not bind the pinned
  class all refuse; break->RED->restore->GREEN positive control proves
  sensitivity.
- The on-image D31 seed handle (``prepare_on_image_d31_seed``) pins the
  persist namespace mapping and its ``d31_fn`` satisfies the real
  ``run_recovery_d31_reverse_leg`` contract.
- The real entry without fakes stays ``BLOCKED`` naming the facility on
  this host (darwin, no Linux/QEMU facility) with nothing fabricated.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock as _mock

from tools.x8_qemu import gate_p5
from tools.x8_qemu import preintro_timing
from tools.x8_qemu import product as _product
from tools.x8_qemu.boot_perf import build_boot_perf_record
from tools.x8_qemu.devproof import (
    read_d31_representative_state,
    write_d31_representative_state,
)
from tools.x8_qemu.gate_p5 import (
    GATE_P5_ID,
    GATE_P5_PREDICATES,
    GATE_P5_TRANSITION_UNITS,
    build_gate_p5_record,
    prepare_on_image_d31_seed,
    run_gate_p5_closure_product,
)
from tools.x8_qemu.lifecycle import LifecycleConfig, LifecycleHarnessError
from tools.x8_qemu.product import (
    build_boot_health_lifecycle_report,
    build_install_lifecycle_report,
    build_product_identity_record,
    build_recovery_d31_reverse_lifecycle_report,
    record_live_squashfs_mutation,
    record_slot_injection_mutation,
    run_recovery_d31_reverse_leg,
    sha256_file,
)

import hermetic_volume


def setUpModule() -> None:
    hermetic_volume.install_for_module()

HEAD_40 = "a" * 40


def _write(base: Path, name: str, tag: bytes) -> Path:
    path = base / name
    path.write_bytes(tag * 64)
    return path


def _measurement(**overrides):
    base = {
        "label": "test",
        "qemu_start_monotonic": 100.0,
        "first_intro_frame": 110.0,
        "intro_end": 117.0,
        "interactive_ready": 120.0,
        "update_service_started": None,
        "timed_out": False,
    }
    base.update(overrides)
    return preintro_timing.BootMeasurement(**base)


def _serial() -> str:
    return (
        "GREIA_BOOT event=intro_first_frame_flipped monotonic_ns=1\n"
        "GREIA_BOOT event=intro_end monotonic_ns=2\n"
        "GREIA_BOOT event=launcher_interactive_ready monotonic_ns=3\n"
    )


def _green_perf(installed_sha: str, source_sha: str) -> dict[str, object]:
    return dict(
        build_boot_perf_record(
            baseline=_measurement(),
            activated=_measurement(),
            serial_text=_serial(),
            installed_image_sha256=installed_sha,
            source_sha256=source_sha,
        )
    )


def _slot_mutation(pre: str, post: str) -> dict[str, object]:
    return dict(
        record_slot_injection_mutation(
            pre_sha256=pre,
            post_sha256=post,
            injected_files=[
                "etc/systemd/system/greia-x8-control.service",
                "usr/local/sbin/greia-x8-control",
                "etc/systemd/system/multi-user.target.wants/greia-x8-control.service",
            ],
        )
    )


def _green_observation() -> dict[str, object]:
    return {
        "disk_identities": {
            "disk_signature": "1a2b3c4d",
            "system_a_partuuid": "1a2b3c4d-02",
            "system_b_partuuid": "1a2b3c4d-03",
            "persist_partuuid": "1a2b3c4d-04",
        },
        "observed_identities": {
            "system-a": {
                "partuuid": "1a2b3c4d-02",
                "filesystem_uuid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            },
            "system-b": {
                "partuuid": "1a2b3c4d-03",
                "filesystem_uuid": "bbbbbbbb-cccc-dddd-eeee-ffffffffffff",
            },
            "persist": {
                "partuuid": "1a2b3c4d-04",
                "filesystem_uuid": "cccccccc-dddd-eeee-ffff-000000000000",
            },
        },
        "default_slot": "B",
        "accepted_release_id": "greia-0.21.0",
        "committed_slot": "B",
        "last_booted": "B",
        "journal_state": "accepted",
    }


def _green_digests() -> dict[str, object]:
    return {
        "active_before": "aa" * 32,
        "active_after": "aa" * 32,
        "inactive_before": "bb" * 32,
        "inactive_after": "cc" * 32,
    }


def _green_isolation() -> dict[str, object]:
    return {
        "active_slot": "A",
        "active_unchanged": True,
        "inactive_changed": True,
    }


def _install_leg(base: Path) -> dict[str, object]:
    installer = _write(base, "installer.img", b"installer-image")
    bundle = _write(base, "greia-0.20.0.greiaupdate", b"release-bundle")
    target = _write(base, "disposable-target.img", b"installed-system-a")
    mutation = record_live_squashfs_mutation(
        pre_sha256="aa" * 32,
        post_sha256="bb" * 32,
        injected_files=[
            "etc/systemd/system/greia-x8-control.service",
            "usr/local/sbin/greia-x8-control",
            "etc/systemd/system/multi-user.target.wants/greia-x8-control.service",
            "etc/systemd/system/graphical.target.wants/greia-graphical-installer.service.mask",
        ],
    )
    identity = build_product_identity_record(
        installer_image=installer,
        release_bundles=[bundle],
        squashfs_mutation=dict(mutation),
    )
    return {
        "ok": True,
        "installer_image": str(installer.resolve()),
        "installer_image_sha256": sha256_file(installer),
        "release_bundle": str(bundle),
        "release_bundle_sha256": sha256_file(bundle),
        "disposable_target": {"target": str(target.resolve()), "size_bytes": target.stat().st_size},
        "lifecycle_report": build_install_lifecycle_report(observed_default="A"),
        "unit_identity": identity,
        "source_image_mutated": False,
    }


def _boot_health_leg(base: Path, installed: Path, bundle: Path) -> dict[str, object]:
    committed = _write(base, "installed-clone.img", b"health-committed-b")
    identity = build_product_identity_record(
        installed_image=installed,
        release_bundles=[bundle],
        slot_a_mutation=_slot_mutation("aa" * 32, "bb" * 32),
        slot_b_mutation=_slot_mutation("cc" * 32, "dd" * 32),
        slot_digests=_green_digests(),
        slot_isolation=_green_isolation(),
        boot_observation=_green_observation(),
    )
    return {
        "ok": True,
        "installed_image": str(installed.resolve()),
        "installed_image_sha256": sha256_file(installed),
        "release_bundle": str(bundle),
        "release_bundle_sha256": sha256_file(bundle),
        "clone": {"clone": str(committed.resolve()), "source_sha256": sha256_file(installed)},
        "lifecycle_report": build_boot_health_lifecycle_report(observed_default="B"),
        "unit_identity": identity,
        "observed": _green_observation(),
        "source_image_mutated": False,
    }


def _recovery_stages() -> dict[str, dict[str, object]]:
    return {
        "stage-broken-candidate": {
            "journal_state": "one_shot_armed",
            "candidate_slot": "A",
        },
        "boot-broken-candidate": {
            "last_booted": "A",
            "journal_state": "candidate_booting",
            "default_slot": "B",
        },
        "recovery-boot-accepted": {
            "journal_state": "failed",
            "journal_note": "recovery:health-service-failure:automatic-reboot:t",
            "last_booted": "B",
            "default_slot": "B",
        },
        "reverse-update-accepted": {
            "journal_state": "accepted",
            "default_slot": "A",
            "accepted_release_id": "greia-0.22.0",
            "committed_slot": "A",
            "last_booted": "A",
        },
    }


def _recovery_leg(base: Path, committed: Path) -> dict[str, object]:
    unhealthy = _write(base, "unhealthy.greiaupdate", b"unhealthy-bundle")
    reverse = _write(base, "reverse.greiaupdate", b"reverse-bundle")
    return {
        "ok": True,
        "installed_image": str(committed.resolve()),
        "installed_image_sha256": sha256_file(committed),
        "unhealthy_bundle": str(unhealthy.resolve()),
        "unhealthy_bundle_sha256": sha256_file(unhealthy),
        "reverse_bundle": str(reverse.resolve()),
        "reverse_bundle_sha256": sha256_file(reverse),
        "stages": _recovery_stages(),
        "lifecycle_report": build_recovery_d31_reverse_lifecycle_report(
            observed_default="A"
        ),
        "source_image_mutated": False,
    }


def _device_envelope() -> dict[str, object]:
    return {
        "classification": "DEVICE_T7_DEVPROOF",
        "device_scope": {"executed": True},
        "cgroup_gate": {
            "verdict": {
                "green": True,
                "diagnostic_only": False,
                "payload_bytes": 64 * 1024 * 1024,
                "peak_bytes": 100 * 1024 * 1024,
                "ceiling_bytes": 768 * 1024 * 1024,
            }
        },
    }


def _green_inputs(base: Path) -> dict[str, object]:
    install = _install_leg(base)
    bundle = Path(str(install["release_bundle"]))
    boot_health = _boot_health_leg(
        base, Path(str(install["disposable_target"]["target"])), bundle  # type: ignore[index]
    )
    committed = Path(str(boot_health["clone"]["clone"]))  # type: ignore[index]
    recovery = _recovery_leg(base, committed)
    perf = _green_perf(
        str(boot_health["installed_image_sha256"]),
        str(boot_health["release_bundle_sha256"]),
    )
    return {
        "install": install,
        "boot_health": boot_health,
        "recovery": recovery,
        "perf": perf,
        "envelope": _device_envelope(),
    }


class GatePredicatesFrozenTests(unittest.TestCase):
    def test_predicate_set_is_pinned(self) -> None:
        self.assertEqual(
            tuple(GATE_P5_PREDICATES),
            (
                "full_lifecycle_green",
                "broken_candidate_recovers",
                "d31_survives",
                "budget_768_green",
                "no_harness_substitution",
                "sha_bound",
                "boot_perf_green",
                "provenance_refusal_green",
                "rc4_checkable",
            ),
        )
        self.assertEqual(GATE_P5_ID, "LEGACY_PRODUCT_PATH_GREEN")

    def test_transition_units_cover_all_eight_steps(self) -> None:
        from tools.x8_qemu.lifecycle import LIFECYCLE_SEQUENCE

        self.assertEqual(set(GATE_P5_TRANSITION_UNITS), set(LIFECYCLE_SEQUENCE))
        for step, binding in GATE_P5_TRANSITION_UNITS.items():
            self.assertTrue(binding["units"], step)
            self.assertTrue(binding["entrypoint"], step)
            self.assertTrue(binding["evidence"], step)


class GateGreenTests(unittest.TestCase):
    def test_full_green_record_closes_all_predicates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            inputs = _green_inputs(base)
            record = build_gate_p5_record(
                install_result=inputs["install"],  # type: ignore[arg-type]
                boot_health_result=inputs["boot_health"],  # type: ignore[arg-type]
                recovery_result=inputs["recovery"],  # type: ignore[arg-type]
                boot_perf_record=inputs["perf"],  # type: ignore[arg-type]
                device_envelope=inputs["envelope"],  # type: ignore[arg-type]
                source_head=HEAD_40,
            )
        self.assertEqual(record["overall"], "GREEN")
        self.assertEqual(record["gate"], GATE_P5_ID)
        predicates = record["predicates"]
        assert isinstance(predicates, dict)
        for name in GATE_P5_PREDICATES:
            self.assertEqual(predicates.get(name), "GREEN", name)
        evidence = record["evidence"]
        assert isinstance(evidence, dict)
        for key in (
            "install_image_sha256",
            "install_bundle_sha256",
            "boot_health_image_sha256",
            "boot_health_bundle_sha256",
            "recovery_installed_sha256",
            "unhealthy_bundle_sha256",
            "reverse_bundle_sha256",
        ):
            value = evidence[key]
            self.assertRegex(str(value), r"^[0-9a-f]{64}$", key)
        self.assertEqual(evidence["source_head"], HEAD_40)
        self.assertEqual(
            set(evidence["transition_units"]), set(GATE_P5_TRANSITION_UNITS)  # type: ignore[arg-type]
        )

    def test_entry_orders_legs_and_supplies_explicit_d31(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            out = base / "out"
            out.mkdir()
            inputs = _green_inputs(base)
            order: list[str] = []
            seen: dict[str, object] = {}

            def _install(harness):
                order.append("install")
                return dict(inputs["install"])

            def _boot_health(harness, installed):
                order.append("boot-health")
                seen["boot_health_input"] = str(installed)
                return dict(inputs["boot_health"])

            def _build_unhealthy():
                order.append("unhealthy-build")
                bundle = base / "unhealthy.greiaupdate"
                return {"bundle": str(bundle), "ok": True}

            def _verify_unhealthy(bundle):
                order.append("unhealthy-verify")
                seen["verified"] = str(bundle)
                return {"ok": True}

            def _recovery(harness, committed, unhealthy, d31):
                order.append("recovery")
                seen["d31_supplied"] = d31 is not None
                seen["recovery_d31"] = dict(d31())
                return dict(inputs["recovery"])

            def _perf(committed):
                order.append("boot-perf")
                return {"record": dict(inputs["perf"]), "ok": True}

            def _budget():
                order.append("budget")
                return dict(inputs["envelope"])

            d31_state = {"calls": 0}

            def _d31():
                d31_state["calls"] += 1
                return {"pinned": True}

            config = LifecycleConfig(output_dir=out)
            with _mock.patch.object(
                _product, "require_product_host", return_value=None
            ), _mock.patch.object(
                _product, "assert_control_absent_from_production", return_value=None
            ):
                result = run_gate_p5_closure_product(
                    config=config,
                    official_installer_image=base / "installer.img",
                    release_bundle=base / "greia-0.20.0.greiaupdate",
                    reverse_bundle=base / "reverse.greiaupdate",
                    unhealthy_release={"release_id": "x"},
                    d31_fn=_d31,
                    install_fn=_install,
                    boot_health_fn=_boot_health,
                    unhealthy_build_fn=_build_unhealthy,
                    unhealthy_verify_fn=_verify_unhealthy,
                    recovery_fn=_recovery,
                    boot_perf_fn=_perf,
                    budget_fn=_budget,
                    source_head_fn=lambda: HEAD_40,
                )
            self.assertEqual(
                order,
                [
                    "install",
                    "boot-health",
                    "unhealthy-build",
                    "unhealthy-verify",
                    "recovery",
                    "boot-perf",
                    "budget",
                ],
            )
            self.assertTrue(seen["d31_supplied"])
            self.assertEqual(seen["recovery_d31"], {"pinned": True})
            self.assertEqual(d31_state["calls"], 1)
            self.assertEqual(result["overall"], "GREEN")
            self.assertEqual(result["gate"], GATE_P5_ID)
            record = result["record"]
            assert isinstance(record, dict)
            self.assertEqual(record["overall"], "GREEN")

    def test_real_entry_is_blocked_on_this_host(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            out = base / "out"
            out.mkdir()
            installer = _write(base, "installer.img", b"installer-image")
            bundle = _write(base, "bundle.greiaupdate", b"bundle")
            config = LifecycleConfig(output_dir=out)
            with self.assertRaises(LifecycleHarnessError) as ctx:
                run_gate_p5_closure_product(
                    config=config,
                    official_installer_image=installer,
                    release_bundle=bundle,
                    reverse_bundle=bundle,
                    unhealthy_release={"release_id": "x"},
                    d31_fn=lambda: {},
                )
            self.assertIn("BLOCKED", str(ctx.exception))


class GateRedTests(unittest.TestCase):
    def test_missing_d31_fn_is_blocked_naming_mapping(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            out = base / "out"
            out.mkdir()
            config = LifecycleConfig(output_dir=out)
            with _mock.patch.object(
                _product, "require_product_host", return_value=None
            ), _mock.patch.object(
                _product, "assert_control_absent_from_production", return_value=None
            ):
                with self.assertRaises(LifecycleHarnessError) as ctx:
                    run_gate_p5_closure_product(
                        config=config,
                        official_installer_image=base / "installer.img",
                        release_bundle=base / "b.greiaupdate",
                        reverse_bundle=base / "r.greiaupdate",
                        unhealthy_release={},
                        d31_fn=None,
                    )
            self.assertIn("BLOCKED", str(ctx.exception))
            self.assertIn("persist mapping", str(ctx.exception))

    def test_non_green_boot_perf_keeps_gate_open(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            inputs = _green_inputs(base)
            bad = dict(inputs["perf"])  # type: ignore[arg-type]
            bad["overall"] = "FAIL"
            with self.assertRaises(LifecycleHarnessError) as ctx:
                build_gate_p5_record(
                    install_result=inputs["install"],  # type: ignore[arg-type]
                    boot_health_result=inputs["boot_health"],  # type: ignore[arg-type]
                    recovery_result=inputs["recovery"],  # type: ignore[arg-type]
                    boot_perf_record=bad,
                    device_envelope=inputs["envelope"],  # type: ignore[arg-type]
                    source_head=HEAD_40,
                )
            self.assertIn("boot-performance", str(ctx.exception))

    def test_not_ready_boot_perf_keeps_gate_open(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            inputs = _green_inputs(base)
            bad = dict(inputs["perf"])  # type: ignore[arg-type]
            bad["overall"] = "NOT_READY"
            with self.assertRaises(LifecycleHarnessError):
                build_gate_p5_record(
                    install_result=inputs["install"],  # type: ignore[arg-type]
                    boot_health_result=inputs["boot_health"],  # type: ignore[arg-type]
                    recovery_result=inputs["recovery"],  # type: ignore[arg-type]
                    boot_perf_record=bad,
                    device_envelope=inputs["envelope"],  # type: ignore[arg-type]
                    source_head=HEAD_40,
                )

    def test_source_scope_envelope_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            inputs = _green_inputs(base)
            envelope = dict(inputs["envelope"])  # type: ignore[arg-type]
            envelope["classification"] = "SOURCE_SCOPE_T7_DEVPROOF"
            envelope["device_scope"] = {"executed": False}
            with self.assertRaises(LifecycleHarnessError) as ctx:
                build_gate_p5_record(
                    install_result=inputs["install"],  # type: ignore[arg-type]
                    boot_health_result=inputs["boot_health"],  # type: ignore[arg-type]
                    recovery_result=inputs["recovery"],  # type: ignore[arg-type]
                    boot_perf_record=inputs["perf"],  # type: ignore[arg-type]
                    device_envelope=envelope,
                    source_head=HEAD_40,
                )
            self.assertIn("device-measured", str(ctx.exception))

    def test_mutated_source_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            inputs = _green_inputs(base)
            install = dict(inputs["install"])  # type: ignore[arg-type]
            install["source_image_mutated"] = True
            with self.assertRaises(LifecycleHarnessError) as ctx:
                build_gate_p5_record(
                    install_result=install,
                    boot_health_result=inputs["boot_health"],  # type: ignore[arg-type]
                    recovery_result=inputs["recovery"],  # type: ignore[arg-type]
                    boot_perf_record=inputs["perf"],  # type: ignore[arg-type]
                    device_envelope=inputs["envelope"],  # type: ignore[arg-type]
                    source_head=HEAD_40,
                )
            self.assertIn("mutated source image", str(ctx.exception))

    def test_missing_recovery_stage_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            inputs = _green_inputs(base)
            recovery = dict(inputs["recovery"])  # type: ignore[arg-type]
            stages = dict(recovery["stages"])  # type: ignore[index]
            del stages["reverse-update-accepted"]
            recovery["stages"] = stages
            with self.assertRaises(LifecycleHarnessError) as ctx:
                build_gate_p5_record(
                    install_result=inputs["install"],  # type: ignore[arg-type]
                    boot_health_result=inputs["boot_health"],  # type: ignore[arg-type]
                    recovery_result=recovery,
                    boot_perf_record=inputs["perf"],  # type: ignore[arg-type]
                    device_envelope=inputs["envelope"],  # type: ignore[arg-type]
                    source_head=HEAD_40,
                )
            self.assertIn("reverse-update-accepted", str(ctx.exception))

    def test_failed_note_without_pinned_class_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            inputs = _green_inputs(base)
            recovery = dict(inputs["recovery"])  # type: ignore[arg-type]
            stages = {k: dict(v) for k, v in recovery["stages"].items()}  # type: ignore[union-attr]
            stages["recovery-boot-accepted"]["journal_note"] = "recovery:launcher-exit:automatic-reboot:t"
            recovery["stages"] = stages
            with self.assertRaises(LifecycleHarnessError) as ctx:
                build_gate_p5_record(
                    install_result=inputs["install"],  # type: ignore[arg-type]
                    boot_health_result=inputs["boot_health"],  # type: ignore[arg-type]
                    recovery_result=recovery,
                    boot_perf_record=inputs["perf"],  # type: ignore[arg-type]
                    device_envelope=inputs["envelope"],  # type: ignore[arg-type]
                    source_head=HEAD_40,
                )
            self.assertIn("pinned class", str(ctx.exception))

    def test_substituted_recovery_sha_refused(self) -> None:
        """A well-formed but substituted bundle SHA stays RED (re-hashed)."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            inputs = _green_inputs(base)
            recovery = dict(inputs["recovery"])  # type: ignore[arg-type]
            recovery["unhealthy_bundle_sha256"] = "00" * 32
            with self.assertRaises(LifecycleHarnessError) as ctx:
                build_gate_p5_record(
                    install_result=inputs["install"],  # type: ignore[arg-type]
                    boot_health_result=inputs["boot_health"],  # type: ignore[arg-type]
                    recovery_result=recovery,
                    boot_perf_record=inputs["perf"],  # type: ignore[arg-type]
                    device_envelope=inputs["envelope"],  # type: ignore[arg-type]
                    source_head=HEAD_40,
                )
            self.assertIn("does not match", str(ctx.exception))

    def test_unbound_recovery_sha_refused(self) -> None:
        """A SHA without a bound file is not evidence."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            inputs = _green_inputs(base)
            recovery = dict(inputs["recovery"])  # type: ignore[arg-type]
            del recovery["unhealthy_bundle"]
            with self.assertRaises(LifecycleHarnessError) as ctx:
                build_gate_p5_record(
                    install_result=inputs["install"],  # type: ignore[arg-type]
                    boot_health_result=inputs["boot_health"],  # type: ignore[arg-type]
                    recovery_result=recovery,
                    boot_perf_record=inputs["perf"],  # type: ignore[arg-type]
                    device_envelope=inputs["envelope"],  # type: ignore[arg-type]
                    source_head=HEAD_40,
                )
            self.assertIn("not bound", str(ctx.exception))

    def test_spliced_legs_refused(self) -> None:
        """Recovery on a foreign image never composes into the closure."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            inputs = _green_inputs(base)
            foreign = _write(base, "foreign.img", b"foreign-image")
            recovery = dict(inputs["recovery"])  # type: ignore[arg-type]
            recovery["installed_image"] = str(foreign.resolve())
            recovery["installed_image_sha256"] = sha256_file(foreign)
            with self.assertRaises(LifecycleHarnessError) as ctx:
                build_gate_p5_record(
                    install_result=inputs["install"],  # type: ignore[arg-type]
                    boot_health_result=inputs["boot_health"],  # type: ignore[arg-type]
                    recovery_result=recovery,
                    boot_perf_record=inputs["perf"],  # type: ignore[arg-type]
                    device_envelope=inputs["envelope"],  # type: ignore[arg-type]
                    source_head=HEAD_40,
                )
            self.assertIn("different runs", str(ctx.exception))

    def test_positive_control_break_restore(self) -> None:
        """Sensitivity: break -> RED -> restore -> GREEN on the same record."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            inputs = _green_inputs(base)
            green = build_gate_p5_record(
                install_result=inputs["install"],  # type: ignore[arg-type]
                boot_health_result=inputs["boot_health"],  # type: ignore[arg-type]
                recovery_result=inputs["recovery"],  # type: ignore[arg-type]
                boot_perf_record=inputs["perf"],  # type: ignore[arg-type]
                device_envelope=inputs["envelope"],  # type: ignore[arg-type]
                source_head=HEAD_40,
            )
            self.assertEqual(green["overall"], "GREEN")
            broken = dict(inputs["perf"])  # type: ignore[arg-type]
            broken["overall"] = "FAIL"
            with self.assertRaises(LifecycleHarnessError):
                build_gate_p5_record(
                    install_result=inputs["install"],  # type: ignore[arg-type]
                    boot_health_result=inputs["boot_health"],  # type: ignore[arg-type]
                    recovery_result=inputs["recovery"],  # type: ignore[arg-type]
                    boot_perf_record=broken,
                    device_envelope=inputs["envelope"],  # type: ignore[arg-type]
                    source_head=HEAD_40,
                )
            restored = build_gate_p5_record(
                install_result=inputs["install"],  # type: ignore[arg-type]
                boot_health_result=inputs["boot_health"],  # type: ignore[arg-type]
                recovery_result=inputs["recovery"],  # type: ignore[arg-type]
                boot_perf_record=inputs["perf"],  # type: ignore[arg-type]
                device_envelope=inputs["envelope"],  # type: ignore[arg-type]
                source_head=HEAD_40,
            )
            self.assertEqual(restored["overall"], "GREEN")


class GateD31SeedTests(unittest.TestCase):
    def test_seed_handle_pins_mapping_and_drives_real_leg(self) -> None:
        """The seeded handle satisfies the real recovery-leg contract."""
        import hashlib as _hashlib

        from tools.x8_qemu.product import snapshot_persist_tree

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            installed = _write(base, "installed.img", b"health-committed-b")
            clone = _write(base, "recovery-clone.img", b"health-committed-b")
            mounts: list[str] = []

            def _mount(image, mnt, partition):
                mounts.append(f"mount:{Path(image).name}:{partition}")
                Path(mnt).mkdir(parents=True, exist_ok=True)

            def _unmount(mnt):
                mounts.append(f"unmount:{Path(mnt).name}")

            roots: dict[str, Path] = {}

            def _seed(mnt):
                root = Path(mnt) / "seed-state"
                roots["seed"] = root
                return dict(write_d31_representative_state(root))

            def _read(mnt):
                if Path(mnt).name == "d31-seed-mnt":
                    return dict(read_d31_representative_state(roots["seed"]))
                # Post-recovery persist survived byte-identical: carry the
                # seeded bytes forward, then read through the real store
                # parse paths (mirrors the clone inheriting the seed).
                import shutil as _shutil

                after = Path(mnt) / "after-state"
                if after.exists():
                    _shutil.rmtree(after)
                _shutil.copytree(roots["seed"], after)
                roots["after"] = after
                return dict(read_d31_representative_state(after))

            def _snapshot(mnt):
                key = "seed" if Path(mnt).name == "d31-seed-mnt" else "after"
                return dict(snapshot_persist_tree(roots[key]))

            handle = prepare_on_image_d31_seed(
                installed_image=installed,
                recovery_clone=clone,
                work_dir=base / "work",
                seed_fn=_seed,
                read_fn=_read,
                snapshot_fn=_snapshot,
                mount_fn=_mount,
                unmount_fn=_unmount,
            )
            mapping = handle["persist_mapping"]
            assert isinstance(mapping, dict)
            self.assertEqual(mapping["persist_partition"], 4)
            self.assertIn("device-settings", mapping["persist_namespaces"])  # type: ignore[union-attr]
            self.assertIn("devproof", str(mapping["store_parse_paths"]))
            d31_fn = handle["d31_fn"]
            assert callable(d31_fn)

            observations = _recovery_stages()
            digests = {
                ("B", "before"): _hashlib.sha256(b"b-before").hexdigest(),
                ("A", "before"): _hashlib.sha256(b"a-before").hexdigest(),
                ("B", "after"): _hashlib.sha256(b"b-before").hexdigest(),
                ("A", "after"): _hashlib.sha256(b"a-after").hexdigest(),
            }
            leg = run_recovery_d31_reverse_leg(
                accepted_slot="B",
                candidate_slot="A",
                accepted_release_id="greia-0.21.0",
                candidate_release_id="greia-0.21.1",
                reverse_release_id="greia-0.22.0",
                boot_fn=lambda phase: None,
                observe_fn=lambda stage: dict(observations[stage]),
                d31_fn=d31_fn,  # type: ignore[arg-type]
                slot_digest_fn=lambda slot, when: digests[(slot, when)],
            )
            self.assertTrue(leg["d31_semantic_preserved"])
            self.assertTrue(leg["d31_byte_identical"])
            self.assertTrue(any(m.startswith("mount:") for m in mounts))


if __name__ == "__main__":
    unittest.main()
