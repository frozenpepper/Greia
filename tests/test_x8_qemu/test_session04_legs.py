"""Session 04 real-lifecycle legs: source-scope contracts (offline).

Locks the new ProductHarness legs without QEMU: BLOCKED paths, phase
ordering through recording fakes, report-shape closure, the
expect-refused runner branch, and the nonbooting-candidate mutation
through the fake-mount fixture pattern (no loop contact).
"""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from support_artifacts import valid_hardware_support_archive_bytes
from tools.x8_qemu.lifecycle import LifecycleConfig
from tools.x8_qemu.product import (
    FIRST_BOOT_LEG_PHASES,
    NONBOOT_LEG_UPDATE_PHASES,
    PERSIST_REFUSAL_LEG_PHASES,
    USERSPACE_FAILURE_LEG_PHASES,
    ProductHarness,
    _remove_kernel_files,
    build_first_boot_lifecycle_report,
    build_nonboot_failure_lifecycle_report,
    build_nonbooting_candidate_bundle,
    build_persist_refusal_lifecycle_report,
    build_userspace_failure_lifecycle_report,
    verify_nonbooting_candidate_bundle,
)


def _harness(tmp: str) -> ProductHarness:
    return ProductHarness(LifecycleConfig(output_dir=Path(tmp) / "out"))


def _hex(seed: str) -> str:
    return hashlib.sha256(seed.encode()).hexdigest()


class RunnerRefusalTests(unittest.TestCase):
    def test_expect_refused_phase_is_bounded(self) -> None:
        from tools.x8_qemu import product as _product

        self.assertIn("update-stage-expect-refused", _product.CONTROL_PHASES)

    def test_runner_treats_settled_failed_journal_as_recovered(self) -> None:
        from tools.x8_qemu import product as _product

        text = _product.control_runner_text()
        self.assertIn("settled_states = ('accepted', 'failed', 'rolled_back')", text)
        self.assertIn("state() in settled_states", text)

    def test_runner_inverts_expectation_for_refused_stage(self) -> None:
        from tools.x8_qemu import product as _product

        text = _product.control_runner_text()
        self.assertIn("update-stage-expect-refused", text)
        self.assertIn("expected stage refusal", text)
        # Normal stages still require their positive ack.
        self.assertIn('"STAGE_CURRENT_CANDIDATE": "STAGED"', text)


class ExecuteSamplerTests(unittest.TestCase):
    """The install-execute diagnostic sampler is test-harness-only."""

    def test_sampler_present_in_runner(self) -> None:
        from tools.x8_qemu import product as _product

        text = _product.control_runner_text()
        for required in (
            "s04-diag-sampler",
            "TasksCurrent",
            "TasksMax",
            "install-transaction.service",
            "greia-slots",
            "S04_DIAG_PID",
        ):
            self.assertIn(required, text)

    def test_sampler_absent_from_production(self) -> None:
        project_root = Path(__file__).resolve().parents[2]
        offenders: list[str] = []
        for relative in ("src", "build/overlay", "build/installer-overlay"):
            root = project_root / relative
            if not root.is_dir():
                continue
            for path in sorted(root.rglob("*")):
                if not path.is_file() or path.is_symlink():
                    continue
                try:
                    text = path.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError):
                    continue
                if "s04-diag-sampler" in text:
                    offenders.append(str(path.relative_to(project_root)))
        self.assertEqual(offenders, [])


class ReportShapeTests(unittest.TestCase):
    def test_first_boot_observes_acceptance(self) -> None:
        report = build_first_boot_lifecycle_report(observed_default="A")
        self.assertIn("boot-A-accepted", report["observed_steps"])
        with self.assertRaises(Exception):
            build_first_boot_lifecycle_report(observed_default="B")

    def test_userspace_failure_stays_on_accepted(self) -> None:
        report = build_userspace_failure_lifecycle_report(observed_default="B")
        self.assertIn("recovery-boot-B", report["observed_steps"])
        with self.assertRaises(Exception):
            build_userspace_failure_lifecycle_report(observed_default="A")
        a_start = build_userspace_failure_lifecycle_report(
            observed_default="A", accepted_slot="A"
        )
        self.assertEqual(a_start["accepted_slot"], "A")
        self.assertIn("recovery-boot-A", a_start["observed_steps"])

    def test_nonboot_failure_lands_on_accepted(self) -> None:
        report = build_nonboot_failure_lifecycle_report(observed_default="B")
        self.assertIn("recovery-boot-B", report["observed_steps"])
        with self.assertRaises(Exception):
            build_nonboot_failure_lifecycle_report(observed_default="A")

    def test_persist_refusal_claims_no_transition(self) -> None:
        report = build_persist_refusal_lifecycle_report(observed_default="B")
        self.assertEqual([], report["observed_steps"])
        self.assertEqual("STAGE_CURRENT_CANDIDATE", report["refused_op"])
        with self.assertRaises(Exception):
            build_persist_refusal_lifecycle_report(observed_default="A")

    def test_leg_phase_constants(self) -> None:
        self.assertEqual(("wait-health-poweroff",), FIRST_BOOT_LEG_PHASES)
        self.assertEqual(6, len(USERSPACE_FAILURE_LEG_PHASES))
        self.assertEqual(4, len(NONBOOT_LEG_UPDATE_PHASES))
        self.assertIn("update-stage-expect-refused", PERSIST_REFUSAL_LEG_PHASES)


class LegBlockedTests(unittest.TestCase):
    def test_first_boot_blocked_without_image(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(Exception) as caught:
                _harness(tmp).run_first_boot_product(
                    installed_image=Path(tmp) / "absent.img",
                    expected_release_id="greia-0.13.0-s04",
                )
            self.assertIn("BLOCKED", str(caught.exception))

    def test_userspace_failure_blocked_without_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "installed.img"
            image.write_bytes(b"installed")
            with self.assertRaises(Exception) as caught:
                _harness(tmp).run_userspace_failure_product(
                    installed_image=image,
                    unhealthy_bundle=Path(tmp) / "absent.greiaupdate",
                    accepted_release_id="greia-0.13.0-s04-b",
                    candidate_release_id="greia-0.13.0-s04-broken",
                )
            self.assertIn("BLOCKED", str(caught.exception))

    def test_userspace_failure_refuses_identical_releases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "installed.img"
            image.write_bytes(b"installed")
            bundle = Path(tmp) / "candidate.greiaupdate"
            bundle.write_bytes(b"bundle")
            from tools.x8_qemu import product as _product

            # The identical-release refusal is a product rule that must fire
            # even where the host gate would otherwise answer BLOCKED first.
            with mock.patch.object(
                _product, "require_product_host", lambda **kwargs: None
            ), self.assertRaises(Exception) as caught:
                _harness(tmp).run_userspace_failure_product(
                    installed_image=image,
                    unhealthy_bundle=bundle,
                    accepted_release_id="same",
                    candidate_release_id="same",
                )
            self.assertNotIn("BLOCKED", str(caught.exception))

    def test_nonboot_blocked_without_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "installed.img"
            image.write_bytes(b"installed")
            with self.assertRaises(Exception) as caught:
                _harness(tmp).run_nonboot_failure_product(
                    installed_image=image,
                    nonboot_bundle=Path(tmp) / "absent.greiaupdate",
                    accepted_release_id="greia-0.13.0-s04-b",
                    candidate_release_id="greia-0.13.0-s04-nonboot",
                )
            self.assertIn("BLOCKED", str(caught.exception))

    def test_persist_refusal_blocked_without_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "installed.img"
            image.write_bytes(b"installed")
            with self.assertRaises(Exception) as caught:
                _harness(tmp).run_persist_refusal_product(
                    installed_image=image,
                    refused_bundle=Path(tmp) / "absent.greiaupdate",
                    accepted_release_id="greia-0.13.0-s04-b",
                )
            self.assertIn("BLOCKED", str(caught.exception))


def _kernel_fixture_mount(calls: list[str], with_kernel: bool = True):
    """Fake mount materializing kernel images (mirrors the issuer fixture)."""
    state: dict[str, object] = {}

    def attach(image: Path) -> str:
        calls.append("attach")
        state["image"] = Path(image)
        return "/dev/fake-loop0"

    def mount(node: str, mnt: Path, read_only: bool = False) -> None:
        calls.append(f"mount:{node}:ro={read_only}")
        assert read_only is False
        state["mnt"] = Path(mnt)
        if with_kernel:
            boot = Path(mnt) / "boot"
            boot.mkdir(parents=True, exist_ok=True)
            (boot / "vmlinuz-6.1.0-53-686-pae").write_bytes(b"fake-kernel")
            (boot / "initrd.img-6.1.0-53-686-pae").write_bytes(b"fake-initrd")
            state["materialized"] = True

    def unmount(mnt: Path) -> None:
        calls.append("unmount")
        if state.get("materialized"):
            leftovers = [
                p
                for p in (Path(mnt) / "boot").iterdir()
                if p.name.startswith("vmlinuz")
            ]
            assert leftovers == [], f"kernel was not really deleted: {leftovers}"
            # Initrd must survive: the failure is kernel absence.
            assert (Path(mnt) / "boot" / "initrd.img-6.1.0-53-686-pae").is_file()
            image = state.get("image")
            assert isinstance(image, Path)
            with image.open("ab") as handle:
                handle.write(b"\n# fake-mount image-mutation stand-in\n")

    def detach(loopdev: str, runner=None) -> None:
        calls.append(f"detach:{loopdev}")

    return attach, mount, unmount, detach


def _payload_bytes(size: int, tag: bytes) -> bytes:
    body = bytes((index * 31 + 7) % 256 for index in range(size))
    raw = tag + body[len(tag):]
    fixed = bytearray(raw)
    if fixed[510:512] == b"\x55\xaa":
        fixed[510:512] = b"\x00\x00"
    if fixed[512:520] == b"EFI PART":
        fixed[512:520] = b"\x00" * 8
    return bytes(fixed)


def _nonboot_inputs(work: Path) -> dict[str, Path]:
    payload = work / "base-payload.img"
    payload.write_bytes(_payload_bytes(256 * 1024, b"s04-nonboot:"))
    hw = work / "hw.tar.zst"
    hw.write_bytes(valid_hardware_support_archive_bytes(architecture="x86-64"))
    return {"payload": payload, "hw": hw}


class NonbootBundleTests(unittest.TestCase):
    def test_remove_kernel_files_keeps_initrd(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            boot = root / "boot"
            boot.mkdir()
            (boot / "vmlinuz-6.1.0-53-686-pae").write_bytes(b"k")
            (boot / "vmlinuz-generic").write_bytes(b"k")
            (boot / "initrd.img-6.1.0-53-686-pae").write_bytes(b"i")
            (root / "vmlinuz").write_bytes(b"k")
            removed = _remove_kernel_files(root)
            self.assertEqual(3, len(removed))
            self.assertTrue((boot / "initrd.img-6.1.0-53-686-pae").is_file())
            self.assertEqual([], _remove_kernel_files(root))

    def test_build_orders_attach_mount_remove_unmount_detach(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            inputs = _nonboot_inputs(work)
            calls: list[str] = []
            attach, mount, unmount, detach = _kernel_fixture_mount(calls)
            before = hashlib.sha256(inputs["payload"].read_bytes()).hexdigest()
            built = build_nonbooting_candidate_bundle(
                base_payload=inputs["payload"],
                base_hardware_support=inputs["hw"],
                output_path=work / "nonboot.greiaupdate",
                work_dir=work / "candidate-work",
                release_id="greia-0.13.0-s04-nonboot",
                platform_family="legacy-x86",
                architecture="i386",
                profile="acer-aspire-one-i386-ab",
                attach_fn=attach,
                mount_fn=mount,
                unmount_fn=unmount,
                detach_fn=detach,
            )
            self.assertEqual("attach", calls[0])
            self.assertIn("unmount", calls)
            self.assertTrue(calls[-1].startswith("detach:"))
            self.assertLess(calls.index("attach"), calls.index("unmount"))
            self.assertIn("remove-slot-kernel", built["mechanism"])
            self.assertEqual(
                before, hashlib.sha256(inputs["payload"].read_bytes()).hexdigest()
            )
            verified = verify_nonbooting_candidate_bundle(
                Path(str(built["bundle"])),
                platform_family="legacy-x86",
                architecture="i386",
                profile="acer-aspire-one-i386-ab",
                expected_hardware_sha256=str(built["hardware_support_sha256"]),
            )
            self.assertEqual("greia-0.13.0-s04-nonboot", verified["release_id"])

    def test_base_without_kernel_is_red(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            inputs = _nonboot_inputs(work)
            calls: list[str] = []
            attach, mount, unmount, detach = _kernel_fixture_mount(
                calls, with_kernel=False
            )
            with self.assertRaises(Exception) as caught:
                build_nonbooting_candidate_bundle(
                    base_payload=inputs["payload"],
                    base_hardware_support=inputs["hw"],
                    output_path=work / "nonboot.greiaupdate",
                    work_dir=work / "candidate-work",
                    release_id="greia-0.13.0-s04-nonboot",
                    platform_family="legacy-x86",
                    architecture="i386",
                    profile="acer-aspire-one-i386-ab",
                    attach_fn=attach,
                    mount_fn=mount,
                    unmount_fn=unmount,
                    detach_fn=detach,
                )
            self.assertNotIn("BLOCKED", str(caught.exception))


class LegOrderingTests(unittest.TestCase):
    """Phase order + report closure through recording fakes (no QEMU).

    Every collaborator is a fake, so the fail-closed Linux/QEMU host gate is
    replaced here; its BLOCKED behaviour is covered by ``LegBlockedTests`` and
    the live legs themselves stay gated on a capable Linux host.
    """

    def setUp(self) -> None:
        from tools.x8_qemu import product as _product

        # Same "capable host" seam the other product tests use: only the host
        # gate and QEMU selection are replaced; execution stays in the fakes.
        for patcher in (
            mock.patch.object(_product, "require_product_host", lambda **kwargs: None),
            mock.patch.object(
                _product, "select_install_qemu_binary", lambda **kwargs: "qemu-system-i386"
            ),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def _fakes(self, calls: list[str], *, digest_b_after: str | None = None):
        digest_b = digest_b_after or _hex("slot-b")

        def clone_fn(src: Path, dst: Path) -> dict[str, str]:
            calls.append("clone")
            Path(dst).write_bytes(b"clone")
            return {"clone": str(dst)}

        def materialize_fn(control_dir: Path, image: Path) -> None:
            calls.append("materialize")
            Path(image).write_bytes(b"control")

        def boot_fn(phase: str, argv, serial_log, host_log) -> None:
            calls.append(f"boot:{phase}")

        def digest_fn(slot: str, when: str) -> str:
            if slot == "B" and when == "after" and digest_b_after is not None:
                return digest_b_after
            return _hex(f"slot-{slot}-{when}")

        return clone_fn, materialize_fn, boot_fn, digest_fn

    def test_first_boot_phases_and_closure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            calls: list[str] = []
            clone_fn, materialize_fn, boot_fn, digest_fn = self._fakes(calls)
            image = Path(tmp) / "installed.img"
            image.write_bytes(b"installed")
            bundle = Path(tmp) / "release.greiaupdate"
            bundle.write_bytes(b"bundle")
            observed = {
                "default_slot": "A",
                "accepted_release_id": "greia-0.13.0-s04",
            }
            digest_calls: list[str] = []

            def digest_with_boot_mutation(_image: Path, slot: str) -> str:
                digest_calls.append(slot)
                if slot == "B":
                    return _hex("slot-B-stable")
                return _hex("slot-A-before" if digest_calls.count("A") == 1 else "slot-A-after")

            with mock.patch.object(
                ProductHarness,
                "_observe_boot_health_target",
                return_value=dict(observed),
            ):
                result = _harness(tmp).run_first_boot_product(
                    installed_image=image,
                    release_bundle=bundle,
                    expected_release_id="greia-0.13.0-s04",
                    clone_fn=clone_fn,
                    inject_fn=lambda c, s: {
                        "clone": str(c),
                        "slot": s,
                        "injected_files": [
                            "etc/systemd/system/greia-x8-control.service"
                        ],
                        "pre_sha256": _hex("pre"),
                        "post_sha256": _hex("post"),
                        "source_image_mutated": False,
                    },
                    materialize_fn=materialize_fn,
                    boot_fn=boot_fn,
                    slot_digest_fn=digest_with_boot_mutation,
                )
            boots = [c for c in calls if c.startswith("boot:")]
            self.assertEqual(["boot:wait-health-poweroff"], boots)
            self.assertTrue(result["ok"])
            self.assertEqual(
                result["slot_hash_evidence"],
                {
                    "scope": "raw_hashes_observational_across_boots",
                    "booted_slots": ["A"],
                    "active_unchanged": None,
                    "inactive_unchanged": True,
                },
            )

    def test_first_boot_refuses_untouched_slot_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "installed.img"
            image.write_bytes(b"installed")
            bundle = Path(tmp) / "release.greiaupdate"
            bundle.write_bytes(b"bundle")
            digest_count = 0

            def changed_b(_image: Path, slot: str) -> str:
                nonlocal digest_count
                digest_count += 1
                return _hex(f"B-{digest_count}" if slot == "B" else "A-stable")

            with mock.patch.object(
                ProductHarness,
                "_observe_boot_health_target",
                return_value={"default_slot": "A", "accepted_release_id": "r1"},
            ):
                with self.assertRaisesRegex(Exception, "untouched slot B changed"):
                    _harness(tmp).run_first_boot_product(
                        installed_image=image,
                        release_bundle=bundle,
                        expected_release_id="r1",
                        clone_fn=lambda s, d: {"clone": str(d)},
                        inject_fn=lambda c, s: {"injected_files": []},
                        materialize_fn=lambda d, i: None,
                        boot_fn=lambda *args: None,
                        slot_digest_fn=changed_b,
                    )

    def test_userspace_failure_orders_update_then_health_waits(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            calls: list[str] = []
            clone_fn, materialize_fn, boot_fn, digest_fn = self._fakes(
                calls, digest_b_after=_hex("slot-B-before")
            )
            image = Path(tmp) / "committed.img"
            image.write_bytes(b"committed")
            bundle = Path(tmp) / "broken.greiaupdate"
            bundle.write_bytes(b"broken")
            stages = {
                "stage-broken-candidate": {"journal_state": "one_shot_armed"},
                "boot-broken-candidate": {"journal_state": "candidate_booting"},
                "recovery-boot-accepted": {
                    "default_slot": "B",
                    "journal_state": "failed",
                    "accepted_release_id": "greia-0.13.0-s04-b",
                },
            }

            def digest_moving(slot: str, when: str) -> str:
                if slot == "B":
                    return _hex("slot-B-stable")
                return _hex(f"slot-A-{when}")

            result = _harness(tmp).run_userspace_failure_product(
                installed_image=image,
                unhealthy_bundle=bundle,
                accepted_release_id="greia-0.13.0-s04-b",
                candidate_release_id="greia-0.13.0-s04-broken",
                clone_fn=clone_fn,
                materialize_fn=materialize_fn,
                boot_fn=boot_fn,
                observe_fn=lambda stage: dict(stages[stage]),
                slot_digest_fn=digest_moving,
                serial_fn=lambda c: {"serial": "fake"},
            )
            boots = [c for c in calls if c.startswith("boot:")]
            self.assertEqual(
                [
                    "boot:update-status",
                    "boot:update-verify",
                    "boot:update-stage",
                    "boot:update-arm",
                    "boot:wait-health-poweroff",
                    "boot:wait-health-poweroff",
                ],
                boots,
            )
            self.assertTrue(result["ok"])
            self.assertEqual("B", result["accepted_slot"])

    def test_failure_legs_place_the_candidate_before_verify(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            calls: list[str] = []
            clone_fn, _materialize, boot_fn, digest_fn = self._fakes(calls)
            seen: dict[str, bool] = {}

            def materialize_fn(control_dir: Path, image: Path) -> None:
                phase = json.loads(
                    (control_dir / "phase.json").read_text(encoding="utf-8")
                )["phase"]
                seen[phase] = (control_dir / "candidate.greiaupdate").is_file()
                Path(image).write_bytes(b"control")

            image = Path(tmp) / "committed.img"
            image.write_bytes(b"committed")
            bundle = Path(tmp) / "broken.greiaupdate"
            bundle.write_bytes(b"broken")
            stages = {
                "stage-broken-candidate": {"journal_state": "one_shot_armed"},
                "boot-broken-candidate": {"journal_state": "candidate_booting"},
                "recovery-boot-accepted": {
                    "default_slot": "B",
                    "journal_state": "failed",
                    "accepted_release_id": "greia-0.13.0-s04-b",
                },
            }
            _harness(tmp).run_userspace_failure_product(
                installed_image=image,
                unhealthy_bundle=bundle,
                accepted_release_id="greia-0.13.0-s04-b",
                candidate_release_id="greia-0.13.0-s04-broken",
                clone_fn=clone_fn,
                materialize_fn=materialize_fn,
                boot_fn=boot_fn,
                observe_fn=lambda stage: dict(stages[stage]),
                slot_digest_fn=digest_fn,
                serial_fn=lambda c: {"serial": "fake"},
            )
            self.assertTrue(seen["update-verify"])
            self.assertTrue(seen["update-stage"])

    def test_persist_refusal_leaves_journal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            calls: list[str] = []
            clone_fn, materialize_fn, boot_fn, digest_fn = self._fakes(calls)
            image = Path(tmp) / "accepted.img"
            image.write_bytes(b"accepted")
            bundle = Path(tmp) / "refused.greiaupdate"
            bundle.write_bytes(b"refused")
            journal = {
                "state": "accepted",
                "candidate_slot": "B",
                "accepted_slot": "B",
                "release_id": "greia-0.13.0-s04-b",
                "transitions": 4,
            }
            with mock.patch.object(
                ProductHarness, "_read_journal_state", return_value=dict(journal)
            ):
                result = _harness(tmp).run_persist_refusal_product(
                    installed_image=image,
                    refused_bundle=bundle,
                    accepted_release_id="greia-0.13.0-s04-b",
                    clone_fn=clone_fn,
                    materialize_fn=materialize_fn,
                    boot_fn=boot_fn,
                    observe_fn=lambda c: {
                        "default_slot": "B",
                        "accepted_release_id": "greia-0.13.0-s04-b",
                    },
                    slot_digest_fn=lambda s, w: _hex(f"slot-{s}-stable"),
                )
            boots = [c for c in calls if c.startswith("boot:")]
            self.assertIn("boot:update-stage-expect-refused", boots)
            self.assertTrue(result["inactive_unchanged"])
            self.assertTrue(result["ok"])


if __name__ == "__main__":
    unittest.main()
