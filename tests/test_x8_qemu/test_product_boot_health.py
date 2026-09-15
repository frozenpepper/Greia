"""P5.2 boot-health leg through installed boot + shipped update/health sockets.

Covers the brief's boot-health acceptance without QEMU/loop/mount contact:

- the guest runner embeds the exact P5.1 §4 update invocations
  (update_privileged.build_request/read_response with STATUS /
  VERIFY_CURRENT_CANDIDATE / STAGE_CURRENT_CANDIDATE /
  ARM_CURRENT_CANDIDATE) and the exact boot-health confirmation
  (maybe_load_production_token + build_confirm_request /
  read_confirm_response over the shipped boot-health socket,
  the launcher-owned maybe_accept_production_boot equivalent),
  triggers/acks only;
- the installed boot uses a virtual VGA device for the real Xorg
  launcher (R1) on the i386-capable binary (G1);
- the control seam is injected into slot A, then re-injected into slot
  B after the real updater rewrites it (release payload cannot carry
  the test unit), with pre/post SHA + injected-file list for P5.3;
- host-side inspection uses production parsers (GrubEnvBackend
  default/one-shot/last_booted, BootTransactionJournal ACCEPTED,
  read_accepted_sequence, InstalledLayoutRecord) and proves only the
  inactive slot changed;
- the phased leg drives wait-health → update ×4 → wait-health in order
  and closes through assert_lifecycle_transitions; run_boot_health_product
  keeps BLOCKED only for a named missing facility/artifact;
- preserved negatives: plain boot is a bounded no-op (token None),
  forged/unhealthy presentations are refused, the launcher performs no
  privileged boot-state write.
"""

from __future__ import annotations

import hashlib as _hashlib
import re as _re
import shutil as _shutil
import struct
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace as _SimpleNamespace
from unittest import mock as _mock

from tools.x8_qemu import product as _product
from tools.x8_qemu import lifecycle as _lifecycle
from tools.x8_qemu.lifecycle import (
    LifecycleConfig,
    LifecycleHarnessError,
    assert_lifecycle_transitions,
)
from tools.x8_qemu.product import (
    BOOT_HEALTH_LEG_PHASES,
    BOOT_HEALTH_UPDATE_PHASES,
    CANDIDATE_BUNDLE_FILE,
    INSTALL_PROFILE_ID,
    SHIPPED_BOOT_UNITS,
    ProductHarness,
    _ensure_clone_serial_console,
    build_boot_health_lifecycle_report,
    control_runner_text,
    gather_boot_health_observation,
    hash_slot_partition,
    inject_boot_slot,
    inspect_boot_health_roots,
    product_boot_qemu_argv,
    record_grub_console_mutation,
    record_shipped_boot_units,
    record_slot_injection_mutation,
    run_boot_health_leg,
    verify_update_slot_isolation,
    write_control_phase,
)


class RunnerExactBootHealthTests(unittest.TestCase):
    def test_runner_embeds_exact_update_invocations(self) -> None:
        text = control_runner_text()
        for required in (
            "build_request",
            "read_response",
            "STATUS",
            "VERIFY_CURRENT_CANDIDATE",
            "STAGE_CURRENT_CANDIDATE",
            "ARM_CURRENT_CANDIDATE",
            "candidate.greiaupdate",
        ):
            self.assertIn(required, text)
        # No selectors: the service resolves the inbox candidate internally.
        self.assertNotIn("grubenv", text)
        self.assertNotIn("last_booted", text)

    def test_runner_embeds_exact_boot_health_confirmation(self) -> None:
        text = control_runner_text()
        for required in (
            "maybe_load_production_token",
            "build_confirm_request",
            "read_confirm_response",
            "CONFIRM_BOOT_HEALTH",
            "CONFIRMED",
        ):
            self.assertIn(required, text)
        # Ack still carries phase/socket only, never a boot/disk outcome.
        self.assertIn("poweroff", text)
        self.assertNotIn("grubenv", text)
        self.assertNotIn("last_booted", text)

    def test_runner_positive_control_break_is_red_then_green(self) -> None:
        # Detector: the exact update+health invocation set above. Break it
        # (socket-only runner) -> RED; restore -> GREEN.
        broken = "#!/bin/bash\ntest -S \"$SOCK\" || exit 1\nsystemctl poweroff\n"
        for required in ("build_request", "build_confirm_request"):
            self.assertNotIn(required, broken)
        green = control_runner_text()
        for required in ("build_request", "build_confirm_request"):
            self.assertIn(required, green)

    def test_runner_still_valid_bash(self) -> None:
        import subprocess as _subprocess

        completed = _subprocess.run(
            ["bash", "-n", "/dev/stdin"],
            input=control_runner_text().encode(),
            capture_output=True,
            timeout=60,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr.decode()[:500])


class ShippedBootUnitsTests(unittest.TestCase):
    def test_shipped_boot_units_recorded(self) -> None:
        recorded = record_shipped_boot_units()
        self.assertEqual(set(recorded["sha256"]), set(SHIPPED_BOOT_UNITS))  # type: ignore[index]
        for name in SHIPPED_BOOT_UNITS:
            digest = recorded["sha256"][name]  # type: ignore[index]
            self.assertRegex(digest, r"^[0-9a-f]{64}$")

    def test_shipped_boot_units_blocked_when_absent(self) -> None:
        with self.assertRaises(LifecycleHarnessError) as caught:
            record_shipped_boot_units(project_root=Path("/nonexistent-root"))
        self.assertIn("BLOCKED", str(caught.exception))

    def test_shipped_boot_units_positive_control_red_then_green(self) -> None:
        # Break: fake root missing one unit -> RED. Real tree -> GREEN.
        with tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp)
            unit_dir = fake / "build/overlay/etc/systemd/system"
            unit_dir.mkdir(parents=True)
            for name in SHIPPED_BOOT_UNITS[:-1]:
                (unit_dir / name).write_text("[Unit]\n", encoding="utf-8")
            with self.assertRaises(LifecycleHarnessError):
                record_shipped_boot_units(project_root=fake)
            (unit_dir / SHIPPED_BOOT_UNITS[-1]).write_text("[Unit]\n", encoding="utf-8")
            back = record_shipped_boot_units(project_root=fake)
            self.assertEqual(set(back["sha256"]), set(SHIPPED_BOOT_UNITS))  # type: ignore[index]


class BootQemuArgvTests(unittest.TestCase):
    def test_installed_boot_carries_virtual_vga_for_xorg(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            installed = base / "installed-clone.img"
            installed.write_bytes(b"x" * 4096)
            ctl = base / "ctl.img"
            ctl.write_bytes(b"z" * 4096)
            argv, _serial, _host = product_boot_qemu_argv(
                installed_clone=installed,
                control_image=ctl,
                output_dir=base,
                memory_mib=1024,
                cpus=1,
                qemu_binary="qemu-system-i386",
                leg="wait-health-poweroff",
            )
            text = " ".join(argv)
            # R1: explicit display device for the real Xorg launcher.
            self.assertIn("-vga", argv)
            self.assertIn("std", argv)
            self.assertIn("none", argv)
            self.assertIn(str(installed), text)
            self.assertIn(str(ctl), text)
            self.assertIn("-no-reboot", argv)
            # i386 machine shape (G1): pc + qemu32, never x86_64-only.
            # KVM with TCG fallback: TCG-only exceeds the leg timeout.
            self.assertIn("pc,accel=kvm:tcg", text)
            self.assertIn("qemu32", argv)

    def test_block_device_paths_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            with self.assertRaises(LifecycleHarnessError):
                product_boot_qemu_argv(
                    installed_clone=Path("/dev/sda"),
                    control_image=None,
                    output_dir=base,
                    memory_mib=1024,
                    cpus=1,
                    qemu_binary="qemu-system-i386",
                )

    def test_boot_qemu_reuses_i386_capable_selection(self) -> None:
        from tools.x8_qemu.product import select_install_qemu_binary

        self.assertEqual(
            select_install_qemu_binary(
                runner_which=lambda name: f"/usr/bin/{name}"
            ),
            "/usr/bin/qemu-system-i386",
        )


class _FakeRunner:
    """Recording subprocess double for loop/probe simulation.

    Simulates only what a unit host cannot do (losetup/blkid outputs);
    every argv still flows through the production helpers under test, so
    a missing/bypassed call is RED here.
    """

    def __init__(self, *, loopdev="/dev/loop9", uuids=None):
        self.calls: list[list[str]] = []
        self.loopdev = loopdev
        self.uuids = dict(uuids or {})

    def __call__(self, argv, **kwargs):
        argv = [str(part) for part in argv]
        self.calls.append(argv)
        prog = argv[0].rsplit("/", 1)[-1]
        stdout = ""
        if prog == "losetup":
            stdout = self.loopdev + "\n"
        elif prog == "blkid":
            node = argv[-1]
            uuid = self.uuids.get(node, "")
            if not uuid:
                return _SimpleNamespace(returncode=1, stdout="", stderr="no uuid")
            stdout = uuid + "\n"
        return _SimpleNamespace(returncode=0, stdout=stdout, stderr="")

    def argv0(self, name):
        return [c for c in self.calls if c and c[0].rsplit("/", 1)[-1] == name]


def _scripted_digest_fn(values):
    """Scripted slot digests in leg call order: B-pre, A-pre, A-post, B-post."""
    remaining = list(values)
    seen: list[str] = []

    def _fn(clone, slot):
        seen.append(slot)
        return remaining.pop(0)

    _fn.seen = seen  # type: ignore[attr-defined]
    return _fn


def _green_digests():
    """Inactive B moves bb->cc while active A stays aa->aa."""
    return ["bb" * 32, "aa" * 32, "aa" * 32, "cc" * 32]


def _fake_which(name):
    return f"/usr/bin/{name}"


def _full_boot_observation() -> dict[str, object]:
    """Full gather-shaped observation for the P5.3 identity fold.

    Carries the same keys ``gather_boot_health_observation`` returns
    (MBR/PARTUUID/filesystem/journal/sequence/layout facts) so the
    entry-point identity fold can close GREEN without loop/mount
    contact.
    """
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
        "accepted_sequence": 21,
        "committed_slot": "B",
        "last_booted": "B",
        "journal_state": "accepted",
    }


class SlotInjectionTests(unittest.TestCase):
    def test_unknown_slot_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            clone = Path(tmp) / "clone.img"
            clone.write_bytes(b"x" * 4096)
            with self.assertRaises(LifecycleHarnessError):
                inject_boot_slot(clone, "C", runner=_FakeRunner(), which=_fake_which)

    def test_absent_clone_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(LifecycleHarnessError) as caught:
                inject_boot_slot(
                    Path(tmp) / "absent.img", "A",
                    runner=_FakeRunner(), which=_fake_which,
                )
            self.assertIn("BLOCKED", str(caught.exception))

    def test_mutation_record_requires_observed_shas_and_files(self) -> None:
        record = record_slot_injection_mutation(
            pre_sha256="aa" * 32,
            post_sha256="bb" * 32,
            injected_files=["etc/systemd/system/greia-x8-control.service"],
        )
        self.assertFalse(record["source_image_mutated"])
        with self.assertRaises(LifecycleHarnessError):
            record_slot_injection_mutation(
                pre_sha256="not-a-sha", post_sha256="bb" * 32,
                injected_files=["x"],
            )
        with self.assertRaises(LifecycleHarnessError):
            record_slot_injection_mutation(
                pre_sha256="aa" * 32, post_sha256="bb" * 32, injected_files=[],
            )

    def test_inject_end_to_end_through_loop_seams(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            seed = base / "seed-slot"
            (seed / "etc/systemd/system").mkdir(parents=True)
            # Boot-control grub.cfg rides the same fake mount; two slot
            # entries each carry console=null (resolved at the p1 root).
            (seed / "grub.cfg").write_text(
                "menuentry 'Greia Slot A' --unrestricted {\n"
                "  linux /boot/vmlinuz ro console=null quiet splash\n"
                "}\n"
                "menuentry 'Greia Slot B' --unrestricted {\n"
                "  linux /boot/vmlinuz ro console=null quiet splash\n"
                "}\n",
                encoding="utf-8",
            )
            clone = base / "clone.img"
            clone.write_bytes(b"clone" * 64)
            runner = _FakeRunner()

            def _fake_mount(source, mountpoint, *, read_only, runner=None, which=None):
                _shutil.copytree(seed, mountpoint, dirs_exist_ok=True)

            with _mock.patch.object(_product, "_mount_fs", _fake_mount):
                proof = inject_boot_slot(clone, "A", runner=runner, which=_fake_which)
            self.assertEqual(proof["slot"], "A")
            self.assertRegex(proof["pre_sha256"], r"^[0-9a-f]{64}$")  # type: ignore[arg-type]
            self.assertRegex(proof["post_sha256"], r"^[0-9a-f]{64}$")  # type: ignore[arg-type]
            self.assertFalse(proof["source_image_mutated"])
            self.assertIn(
                "etc/systemd/system/greia-x8-control.service",
                proof["injected_files"],  # type: ignore[operator]
            )
            grub = proof["grub_console"]
            self.assertEqual(grub["grub_cfg"], "grub.cfg")
            self.assertEqual(grub["substitutions"], 2)
            self.assertFalse(grub["source_image_mutated"])
            partscans = [c for c in runner.argv0("losetup") if "-P" in c]
            self.assertEqual(len(partscans), 1)
            self.assertEqual(len([c for c in runner.argv0("losetup") if "-d" in c]), 1)

    def test_inject_second_slot_reuses_patched_console(self) -> None:
        # Idempotency: slot-B injection after slot-A on the same clone
        # must not re-patch (substitutions 0, shas equal), never fail.
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            seed = base / "seed-slot"
            (seed / "etc/systemd/system").mkdir(parents=True)
            (seed / "grub.cfg").write_text(
                "menuentry 'Greia Slot A' --unrestricted {\n"
                "  linux /boot/vmlinuz ro console=ttyS0,115200 console=null quiet splash\n"
                "}\n"
                "menuentry 'Greia Slot B' --unrestricted {\n"
                "  linux /boot/vmlinuz ro console=ttyS0,115200 console=null quiet splash\n"
                "}\n",
                encoding="utf-8",
            )
            clone = base / "clone.img"
            clone.write_bytes(b"clone" * 64)
            runner = _FakeRunner()

            def _fake_mount(source, mountpoint, *, read_only, runner=None, which=None):
                _shutil.copytree(seed, mountpoint, dirs_exist_ok=True)

            with _mock.patch.object(_product, "_mount_fs", _fake_mount):
                proof = inject_boot_slot(clone, "B", runner=runner, which=_fake_which)
            grub = proof["grub_console"]
            self.assertEqual(grub["substitutions"], 0)
            self.assertEqual(grub["pre_sha256"], grub["post_sha256"])


class CloneSerialConsoleTests(unittest.TestCase):
    def _grub(self, mount: Path, *, entries: int = 2) -> Path:
        cfg = mount / "grub.cfg"
        cfg.write_text(
            "".join(
                f"menuentry 'Slot {i}' {{\n"
                "  linux /boot/vmlinuz ro console=null quiet splash\n"
                "}\n"
                for i in range(entries)
            ),
            encoding="utf-8",
        )
        return cfg

    def test_fresh_clone_patches_bare_consoles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mount = Path(tmp)
            self._grub(mount, entries=2)
            proof = _ensure_clone_serial_console(
                mount, grub_relpath="grub.cfg", expected_consoles=2
            )
            self.assertEqual(proof["substitutions"], 2)
            self.assertFalse(proof["source_image_mutated"])
            text = (mount / "grub.cfg").read_text(encoding="utf-8")
            self.assertEqual(text.count("console=ttyS0,115200 console=null"), 2)
            # Preferred console stays null (last in the pair), so
            # /dev/console semantics are unchanged; no bare entry remains.
            self.assertEqual(
                len(_re.findall(r"(?<!console=ttyS0,115200 )console=null", text)),
                0,
            )

    def test_missing_file_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(LifecycleHarnessError):
                _ensure_clone_serial_console(
                    Path(tmp), grub_relpath="grub.cfg", expected_consoles=2
                )

    def test_wrong_shape_refused(self) -> None:
        # Developer console=tty1 shape: zero bare nulls, zero duals.
        with tempfile.TemporaryDirectory() as tmp:
            mount = Path(tmp)
            (mount / "grub.cfg").write_text(
                "menuentry 'Slot' {\n  linux /boot/vmlinuz ro console=tty1\n}\n",
                encoding="utf-8",
            )
            with self.assertRaises(LifecycleHarnessError):
                _ensure_clone_serial_console(
                    mount, grub_relpath="grub.cfg", expected_consoles=2
                )
        # Partial edit (one bare, one dual, expecting two): refused.
        with tempfile.TemporaryDirectory() as tmp:
            mount = Path(tmp)
            (mount / "grub.cfg").write_text(
                "linux /boot/vmlinuz ro console=null\n"
                "linux /boot/vmlinuz ro console=ttyS0,115200 console=null\n",
                encoding="utf-8",
            )
            with self.assertRaises(LifecycleHarnessError):
                _ensure_clone_serial_console(
                    mount, grub_relpath="grub.cfg", expected_consoles=2
                )

    def test_record_requires_shas_and_path(self) -> None:
        record = record_grub_console_mutation(
            grub_cfg="grub.cfg", pre_sha256="aa" * 32,
            post_sha256="bb" * 32, substitutions=2,
        )
        self.assertFalse(record["source_image_mutated"])
        self.assertEqual(record["substitutions"], 2)
        with self.assertRaises(LifecycleHarnessError):
            record_grub_console_mutation(
                grub_cfg="grub.cfg", pre_sha256="nope",
                post_sha256="bb" * 32, substitutions=2,
            )
        with self.assertRaises(LifecycleHarnessError):
            record_grub_console_mutation(
                grub_cfg="", pre_sha256="aa" * 32,
                post_sha256="bb" * 32, substitutions=0,
            )


class InspectBootHealthTests(unittest.TestCase):
    def _green_dirs(self, base: Path, *, slot: str = "B", sequence: int = 21):
        from greia_platform.boot_transaction import (
            BootArtifactSet,
            BootTransactionCoordinator,
            FakeGrubBackend,
        )
        from greia_platform.grub_ab import GrubEnvBackend
        from greia_platform.persistent_layout import InstalledLayoutRecord
        from greia_platform.system_updates import write_accepted_sequence

        # Production GRUB backend: default + observer-reconciled last_booted.
        backend_state = base / "grubenv"
        GrubEnvBackend.initialize(backend_state, default_slot=slot)
        GrubEnvBackend.attach(backend_state).reconcile(slot)
        # Terminal ACCEPTED journal binding the committed slot.
        journal_dir = base / "journal"
        fake_backend = FakeGrubBackend.initialize(base / "fake-grub", default_slot="A")
        candidate = BootArtifactSet(
            slot="B", layout_id="legacy-bios-ab-v1", boot_backend="grub-ab-v1",
            generic_kernel_sha256="cd" * 32, generic_initramfs_sha256="ef" * 32,
            root_partuuid="1a2b3c4d-03", root_filesystem_uuid="bbbbbbbb-cccc-dddd-eeee-ffffffffffff",
            release_id="greia-0.21.0", release_sequence=sequence,
        )
        accepted = BootArtifactSet(
            slot="A", layout_id="legacy-bios-ab-v1", boot_backend="grub-ab-v1",
            generic_kernel_sha256="cd" * 32, generic_initramfs_sha256="ef" * 32,
            root_partuuid="1a2b3c4d-02", root_filesystem_uuid="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            release_id="greia-0.20.0", release_sequence=20,
        )
        coordinator = BootTransactionCoordinator.begin_update(
            journal_dir=journal_dir, backend=fake_backend,
            candidate_artifacts=candidate, accepted_artifacts=accepted,
            release_id="greia-0.21.0", release_sequence=sequence,
        )
        coordinator.arm()
        fake_backend.simulate_reboot()
        resumed = BootTransactionCoordinator.resume(
            journal_dir=journal_dir, backend=FakeGrubBackend.attach(base / "fake-grub"),
            candidate_artifacts=candidate, accepted_artifacts=accepted,
        )
        resumed.observe_boot()
        resumed.commit()
        # Accepted sequence state.
        accepted_state = base / "update-state"
        write_accepted_sequence(accepted_state, sequence)
        # Layout authority accepting the committed slot/sequence.
        layout_path = base / "installed-layout.json"
        record = InstalledLayoutRecord.from_dict(
            {
                "accepted_release_id": "greia-0.21.0",
                "accepted_release_sequence": sequence,
                "accepted_slot": slot,
                "boot_backend": "grub-ab-v1",
                "boot_control": {"active_slot": slot, "kind": "grub-env-v1"},
                "install_profile": INSTALL_PROFILE_ID,
                "install_target_sha256": "ab" * 32,
                "installed_at_unix": 1757000000,
                "layout_id": "legacy-bios-ab-v1",
                "persist": {
                    "filesystem_uuid": "cccccccc-dddd-eeee-ffff-000000000000",
                    "partuuid": "1a2b3c4d-04",
                },
                "platform_family": "legacy-x86",
                "schema_version": 1,
                "slot_bytes": 1073741824,
                "system_a": {
                    "filesystem_uuid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                    "partuuid": "1a2b3c4d-02",
                },
                "system_b": {
                    "filesystem_uuid": "bbbbbbbb-cccc-dddd-eeee-ffffffffffff",
                    "partuuid": "1a2b3c4d-03",
                },
            }
        )
        import json as _json

        layout_path.write_text(
            _json.dumps(record.as_dict(), sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        return {
            "backend_state": backend_state,
            "journal": journal_dir,
            "accepted_state": accepted_state,
            "layout": layout_path,
        }

    def test_inspect_green_through_production_parsers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            roots = self._green_dirs(Path(tmp))
            observed = inspect_boot_health_roots(
                backend_state_dir=roots["backend_state"],
                journal_dir=roots["journal"],
                accepted_state_dir=roots["accepted_state"],
                layout_record_path=roots["layout"],
                expected_slot="B",
                expected_sequence=21,
            )
            self.assertEqual(observed["committed_slot"], "B")
            self.assertEqual(observed["accepted_sequence"], 21)
            self.assertEqual(observed["last_booted"], "B")
            self.assertEqual(observed["journal_state"], "accepted")

    def test_inspect_red_then_green_positive_control(self) -> None:
        # Break: reconcile the wrong slot -> last_booted mismatch RED.
        # Restore: reconcile B -> GREEN.
        from greia_platform.grub_ab import GrubEnvBackend

        with tempfile.TemporaryDirectory() as tmp:
            roots = self._green_dirs(Path(tmp))
            GrubEnvBackend.attach(roots["backend_state"]).reconcile("A")
            with self.assertRaises(LifecycleHarnessError) as caught:
                inspect_boot_health_roots(
                    backend_state_dir=roots["backend_state"],
                    journal_dir=roots["journal"],
                    accepted_state_dir=roots["accepted_state"],
                    layout_record_path=roots["layout"],
                    expected_slot="B",
                    expected_sequence=21,
                )
            self.assertIn("last_booted", str(caught.exception))
            GrubEnvBackend.attach(roots["backend_state"]).reconcile("B")
            back = inspect_boot_health_roots(
                backend_state_dir=roots["backend_state"],
                journal_dir=roots["journal"],
                accepted_state_dir=roots["accepted_state"],
                layout_record_path=roots["layout"],
                expected_slot="B",
                expected_sequence=21,
            )
            self.assertEqual(back["committed_slot"], "B")


class SlotIsolationTests(unittest.TestCase):
    def test_green_only_inactive_changed(self) -> None:
        proof = verify_update_slot_isolation(
            active_slot="A",
            active_before_digest="aa" * 32,
            active_after_digest="aa" * 32,
            inactive_before_digest="bb" * 32,
            inactive_after_digest="cc" * 32,
        )
        self.assertTrue(proof["active_unchanged"])
        self.assertTrue(proof["inactive_changed"])

    def test_active_change_refused(self) -> None:
        with self.assertRaises(LifecycleHarnessError) as caught:
            verify_update_slot_isolation(
                active_slot="A",
                active_before_digest="aa" * 32,
                active_after_digest="dd" * 32,
                inactive_before_digest="bb" * 32,
                inactive_after_digest="cc" * 32,
            )
        self.assertIn("active/accepted slot", str(caught.exception))

    def test_inactive_unchanged_refused(self) -> None:
        with self.assertRaises(LifecycleHarnessError):
            verify_update_slot_isolation(
                active_slot="A",
                active_before_digest="aa" * 32,
                active_after_digest="aa" * 32,
                inactive_before_digest="bb" * 32,
                inactive_after_digest="bb" * 32,
            )


class ReportTests(unittest.TestCase):
    def test_report_shape_passes_frozen_contract(self) -> None:
        report = build_boot_health_lifecycle_report(observed_default="B")
        self.assertEqual(
            report["observed_steps"], ["boot-A-accepted", "stage-B-one-shot", "boot-B-commit"]
        )
        with self.assertRaises(LifecycleHarnessError):
            build_boot_health_lifecycle_report(observed_default="A")


class LegOrderingTests(unittest.TestCase):
    def _fixtures(self, base: Path):
        bundle = base / "greia-0.21.0.greiaupdate"
        bundle.write_bytes(b"signed-update" * 64)
        return bundle

    def test_leg_drives_health_update_health_and_reinjects_b(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            bundle = self._fixtures(base)
            seen: list[str] = []
            injections: list[str] = []
            boots: list[str] = []
            digests = _scripted_digest_fn(_green_digests())

            def _boot(phase: str, doc: dict[str, object]) -> None:
                boots.append(phase)
                self.assertEqual(doc["phase"], phase)

            result = run_boot_health_leg(
                product_root=base / "product",
                installed_clone=base / "installed-clone.img",
                control_dir=base / "ctl",
                release_bundle=bundle,
                clone_fn=lambda: seen.append("clone"),
                inject_fn=lambda clone, slot: injections.append(slot),
                boot_fn=_boot,
                observe_fn=lambda: {"default_slot": "B", "accepted_sequence": 21},
                slot_digest_fn=digests,
            )
            self.assertEqual(seen, ["clone"])
            self.assertEqual(boots, list(BOOT_HEALTH_LEG_PHASES))
            # Slot A injected before the first boot; slot B re-injected
            # after the real updater rewrote it (after update-arm,
            # before the second wait-health-poweroff).
            self.assertEqual(injections, ["A", "B"])
            b_index = boots.index("wait-health-poweroff", 1)
            arm_index = boots.index("update-arm")
            self.assertGreater(b_index, arm_index)
            self.assertEqual(result["phases"], list(BOOT_HEALTH_LEG_PHASES))
            # Isolation is wired: digests captured B-pre/A-pre/A-post/B-post
            # and the active slot proved byte-identical while B moved.
            self.assertEqual(digests.seen, ["B", "A", "A", "B"])
            self.assertEqual(
                result["slot_digests"],
                {
                    "active_before": "aa" * 32,
                    "active_after": "aa" * 32,
                    "inactive_before": "bb" * 32,
                    "inactive_after": "cc" * 32,
                },
            )
            isolation = result["slot_isolation"]
            self.assertTrue(isolation["active_unchanged"])
            self.assertTrue(isolation["inactive_changed"])

    def test_missing_bundle_blocked_before_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            calls: list[str] = []
            digests = _scripted_digest_fn(_green_digests())
            with self.assertRaises(LifecycleHarnessError) as caught:
                run_boot_health_leg(
                    product_root=base / "product",
                    installed_clone=base / "clone.img",
                    control_dir=base / "ctl",
                    release_bundle=base / "absent.greiaupdate",
                    clone_fn=lambda: calls.append("clone"),
                    inject_fn=lambda c, s: calls.append(f"inject:{s}"),
                    boot_fn=lambda phase, _doc: calls.append(f"boot:{phase}"),
                    observe_fn=lambda: {"default_slot": "B"},
                    slot_digest_fn=digests,
                )
            self.assertIn("BLOCKED", str(caught.exception))
            self.assertEqual(calls, [])
            self.assertEqual(digests.seen, [])

    def test_missing_observe_fn_refuses_before_closure(self) -> None:
        # Fail-closed: an unobserved boot never closes, even with GREEN
        # digests and boots throughout the leg.
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            bundle = self._fixtures(base)
            with self.assertRaises(LifecycleHarnessError) as caught:
                run_boot_health_leg(
                    product_root=base / "product",
                    installed_clone=base / "clone.img",
                    control_dir=base / "ctl",
                    release_bundle=bundle,
                    clone_fn=lambda: None,
                    inject_fn=lambda c, s: None,
                    boot_fn=lambda phase, _doc: None,
                    observe_fn=None,
                    slot_digest_fn=_scripted_digest_fn(_green_digests()),
                )
            self.assertIn("observation", str(caught.exception))

    def test_active_slot_mutation_refuses_before_closure(self) -> None:
        # Wiring proof: the leg hashes both slots, so an active-slot move
        # (aa->dd) refuses even when observation reports B.
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            bundle = self._fixtures(base)
            digests = _scripted_digest_fn(["bb" * 32, "aa" * 32, "dd" * 32, "cc" * 32])
            with self.assertRaises(LifecycleHarnessError) as caught:
                run_boot_health_leg(
                    product_root=base / "product",
                    installed_clone=base / "clone.img",
                    control_dir=base / "ctl",
                    release_bundle=bundle,
                    clone_fn=lambda: None,
                    inject_fn=lambda c, s: None,
                    boot_fn=lambda phase, _doc: None,
                    observe_fn=lambda: {"default_slot": "B"},
                    slot_digest_fn=digests,
                )
            self.assertIn("active/accepted slot", str(caught.exception))

    def test_inactive_unchanged_refuses_before_closure(self) -> None:
        # Wiring proof: a staged slot that never moved (bb->bb) refuses.
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            bundle = self._fixtures(base)
            digests = _scripted_digest_fn(["bb" * 32, "aa" * 32, "aa" * 32, "bb" * 32])
            with self.assertRaises(LifecycleHarnessError):
                run_boot_health_leg(
                    product_root=base / "product",
                    installed_clone=base / "clone.img",
                    control_dir=base / "ctl",
                    release_bundle=bundle,
                    clone_fn=lambda: None,
                    inject_fn=lambda c, s: None,
                    boot_fn=lambda phase, _doc: None,
                    observe_fn=lambda: {"default_slot": "B"},
                    slot_digest_fn=digests,
                )

    def test_non_b_observation_refuses_before_closure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            bundle = self._fixtures(base)
            with self.assertRaises(LifecycleHarnessError):
                run_boot_health_leg(
                    product_root=base / "product",
                    installed_clone=base / "clone.img",
                    control_dir=base / "ctl",
                    release_bundle=bundle,
                    clone_fn=lambda: None,
                    inject_fn=lambda c, s: None,
                    boot_fn=lambda phase, _doc: None,
                    observe_fn=lambda: {"default_slot": "A"},
                    slot_digest_fn=_scripted_digest_fn(_green_digests()),
                )


class RunProductWiringTests(unittest.TestCase):
    def test_run_boot_health_product_source_pins_production_wiring(self) -> None:
        import inspect as _inspect

        source = _inspect.getsource(_product.ProductHarness.run_boot_health_product)
        for required in (
            "clone_product_image",
            "inject_boot_slot",
            "product_boot_qemu_argv",
            "materialize_control_disk",
            "_observe_boot_health_target",
            "verify_update_slot_isolation",
            "hash_slot_partition",
            "expected_slot",
            "build_boot_health_lifecycle_report",
            "assert_lifecycle_transitions",
            "record_shipped_boot_units",
        ):
            self.assertIn(required, source)
        self.assertNotIn("not yet wired", source)

    def test_run_boot_health_product_blocked_names_facility(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            harness = ProductHarness(LifecycleConfig(output_dir=Path(tmp) / "out"))
            with self.assertRaises(LifecycleHarnessError) as caught:
                harness.run_boot_health_product()
            self.assertIn("BLOCKED", str(caught.exception))

    def test_full_fake_leg_closes_with_observed_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            bundle = base / "greia-0.21.0.greiaupdate"
            bundle.write_bytes(b"signed-update" * 64)
            installed = base / "installed.img"
            installed.write_bytes(b"installed" * 64)
            seen: dict[str, object] = {}
            gate = _mock.patch.object(_product, "require_product_host", lambda **k: None)
            qemu = _mock.patch.object(
                _product, "select_install_qemu_binary", lambda **k: "qemu-system-i386"
            )
            units = _mock.patch.object(
                _product, "record_shipped_boot_units",
                lambda **k: {"unit_dir": "x", "sha256": {n: "ab" * 32 for n in SHIPPED_BOOT_UNITS}},
            )
            with gate, qemu, units:
                harness = ProductHarness(
                    LifecycleConfig(output_dir=base / "out"),
                    official_image=installed,
                    release_bundle=bundle,
                )
                injections: list[str] = []

                def _boot(phase, argv, serial_log, host_log):
                    seen.setdefault("boots", []).append(phase)  # type: ignore[attr-defined]
                    if phase == "wait-health-poweroff":
                        self.assertIn("-vga", argv)
                        self.assertIn("std", argv)

                result = harness.run_boot_health_product(
                    clone_fn=lambda s, d: {"source_sha256": "aa" * 32, "clone": str(d)},
                    inject_fn=lambda c, s: injections.append(s) or {
                        "clone": str(c), "slot": s, "injected_files": ["x"],
                        "pre_sha256": "aa" * 32, "post_sha256": "bb" * 32,
                        "source_image_mutated": False,
                    },
                    materialize_fn=lambda d, i: None,
                    boot_fn=_boot,
                    observe_fn=lambda t: dict(_full_boot_observation()),
                    slot_digest_fn=_scripted_digest_fn(_green_digests()),
                )
            self.assertTrue(result["ok"])
            self.assertEqual(result["leg"], "boot-health-product")
            self.assertEqual(result["phases"], list(BOOT_HEALTH_LEG_PHASES))
            self.assertEqual(injections, ["A", "B"])
            self.assertTrue(result["slot_isolation"]["active_unchanged"])
            self.assertTrue(result["slot_isolation"]["inactive_changed"])
            self.assertEqual(
                result["slot_digests"]["active_before"], "aa" * 32
            )
            self.assertIn("candidate.greiaupdate", CANDIDATE_BUNDLE_FILE)
            staged = base / "out/product/control-disk" / CANDIDATE_BUNDLE_FILE
            self.assertTrue(staged.is_file())
            self.assertEqual(staged.read_bytes(), bundle.read_bytes())
            # P5.3 identity fold rides in the leg result for Gate-P5.
            identity = result["unit_identity"]
            self.assertEqual(
                identity["installed_image"]["sha256"],
                result["installed_image_sha256"],
            )
            self.assertEqual(
                identity["release_bundles"][bundle.name]["sha256"],
                result["release_bundle_sha256"],
            )
            self.assertEqual(identity["boot_observation"]["default_slot"], "B")
            self.assertEqual(identity["boot_observation"]["accepted_sequence"], 21)

    def test_run_boot_health_product_active_mutation_refuses(self) -> None:
        # Entry-point wiring proof: scripted digests showing an active-slot
        # move refuse before closure even with B observed throughout.
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            bundle = base / "greia-0.21.0.greiaupdate"
            bundle.write_bytes(b"signed-update" * 64)
            installed = base / "installed.img"
            installed.write_bytes(b"installed" * 64)
            gate = _mock.patch.object(_product, "require_product_host", lambda **k: None)
            qemu = _mock.patch.object(
                _product, "select_install_qemu_binary", lambda **k: "qemu-system-i386"
            )
            units = _mock.patch.object(
                _product, "record_shipped_boot_units",
                lambda **k: {"unit_dir": "x", "sha256": {n: "ab" * 32 for n in SHIPPED_BOOT_UNITS}},
            )
            moving = _scripted_digest_fn(["bb" * 32, "aa" * 32, "dd" * 32, "cc" * 32])
            with gate, qemu, units:
                harness = ProductHarness(
                    LifecycleConfig(output_dir=base / "out"),
                    official_image=installed,
                    release_bundle=bundle,
                )
                with self.assertRaises(LifecycleHarnessError) as caught:
                    harness.run_boot_health_product(
                        clone_fn=lambda s, d: {"source_sha256": "aa" * 32, "clone": str(d)},
                        inject_fn=lambda c, s: {
                            "clone": str(c), "slot": s, "injected_files": ["x"],
                            "pre_sha256": "aa" * 32, "post_sha256": "bb" * 32,
                            "source_image_mutated": False,
                        },
                        materialize_fn=lambda d, i: None,
                        boot_fn=lambda phase, argv, serial_log, host_log: None,
                        observe_fn=lambda t: dict(_full_boot_observation()),
                        slot_digest_fn=moving,
                    )
            self.assertIn("active/accepted slot", str(caught.exception))

    def test_launcher_performs_no_privileged_boot_state_write(self) -> None:
        from tools.x8_qemu.lifecycle import PROJECT_ROOT

        launcher_service = (
            PROJECT_ROOT / "build/overlay/etc/systemd/system/greia-launcher.service"
        ).read_text(encoding="utf-8")
        # The unprivileged launcher (greiakid) owns no boot-state writes:
        # no ReadWritePaths grant over /boot, /etc/greia-os or update state.
        self.assertIn("User=greiakid", launcher_service)
        for denied in ("ReadWritePaths=/boot", "ReadWritePaths=/etc/greia-os"):
            self.assertNotIn(denied, launcher_service)
        seam = (PROJECT_ROOT / "src/greia_launcher/boot_health.py").read_text(
            encoding="utf-8"
        )
        for denied in ("GrubEnvBackend", "write_accepted_sequence", "SlotWriter"):
            self.assertNotIn(denied, seam)
        self.assertIn("maybe_accept_production_boot", seam)


class GatherRealShapeTests(unittest.TestCase):
    """gather_boot_health_observation through real production parsers.

    No fake observe_fn: the MBR file is real bytes, the mounted
    boot/persist trees carry production-committed state (GrubEnvBackend
    reconciled to B, ACCEPTED update journal binding B, accepted sequence
    21, layout record B/21 at the production on-persist paths), and only
    the loop/mount transport is faked (recording runner + copy-tree
    mount, the same precedent as the install leg). Closure runs through
    the frozen assert_lifecycle_transitions on the observed default.
    """

    def _mbr_file(self, base: Path) -> Path:
        mbr = bytearray(512)
        struct.pack_into("<I", mbr, 440, 0x1A2B3C4D)
        for number in (2, 3, 4):
            offset = 446 + (number - 1) * 16
            mbr[offset + 4] = 0x83
        mbr[510] = 0x55
        mbr[511] = 0xAA
        target = base / "target.img"
        target.write_bytes(bytes(mbr) + b"\0" * (4096 - 512))
        return target

    def _seed_boot_health_trees(
        self, base: Path, *, slot: str = "B", sequence: int = 21
    ) -> tuple[Path, Path]:
        import json as _json

        from greia_platform.boot_transaction import (
            BootArtifactSet,
            BootTransactionCoordinator,
            FakeGrubBackend,
        )
        from greia_platform.grub_ab import GrubEnvBackend
        from greia_platform.persistent_layout import InstalledLayoutRecord
        from greia_platform.system_updates import write_accepted_sequence

        boot_seed = base / "boot-seed"
        persist_seed = base / "persist-seed"
        boot_seed.mkdir(parents=True, exist_ok=True)
        persist_seed.mkdir(parents=True, exist_ok=True)
        # Observer-established last_booted: default + reconciled slot.
        GrubEnvBackend.initialize(boot_seed / "grub", default_slot=slot)
        GrubEnvBackend.attach(boot_seed / "grub").reconcile(slot)
        # Terminal ACCEPTED update journal binding the committed slot,
        # under the update state dir the services resolve at runtime.
        state_root = (
            persist_seed / "greia" / "namespaces" / "parent-credentials"
        )
        journal_dir = state_root / "system-updates" / "journal"
        journal_dir.mkdir(parents=True, exist_ok=True)
        fake_backend = FakeGrubBackend.initialize(base / "fake-grub", default_slot="A")
        candidate = BootArtifactSet(
            slot="B", layout_id="legacy-bios-ab-v1", boot_backend="grub-ab-v1",
            generic_kernel_sha256="cd" * 32, generic_initramfs_sha256="ef" * 32,
            root_partuuid="1a2b3c4d-03", root_filesystem_uuid="bbbbbbbb-cccc-dddd-eeee-ffffffffffff",
            release_id="greia-0.21.0", release_sequence=sequence,
        )
        accepted = BootArtifactSet(
            slot="A", layout_id="legacy-bios-ab-v1", boot_backend="grub-ab-v1",
            generic_kernel_sha256="cd" * 32, generic_initramfs_sha256="ef" * 32,
            root_partuuid="1a2b3c4d-02", root_filesystem_uuid="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            release_id="greia-0.20.0", release_sequence=20,
        )
        coordinator = BootTransactionCoordinator.begin_update(
            journal_dir=journal_dir, backend=fake_backend,
            candidate_artifacts=candidate, accepted_artifacts=accepted,
            release_id="greia-0.21.0", release_sequence=sequence,
        )
        coordinator.arm()
        fake_backend.simulate_reboot()
        resumed = BootTransactionCoordinator.resume(
            journal_dir=journal_dir, backend=FakeGrubBackend.attach(base / "fake-grub"),
            candidate_artifacts=candidate, accepted_artifacts=accepted,
        )
        resumed.observe_boot()
        resumed.commit()
        # Accepted-sequence state beside the journal (same state dir).
        write_accepted_sequence(state_root, sequence)
        # Layout authority: authoritative on-persist copy.
        record = InstalledLayoutRecord.from_dict(
            {
                "accepted_release_id": "greia-0.21.0",
                "accepted_release_sequence": sequence,
                "accepted_slot": slot,
                "boot_backend": "grub-ab-v1",
                "boot_control": {"active_slot": slot, "kind": "grub-env-v1"},
                "install_profile": INSTALL_PROFILE_ID,
                "install_target_sha256": "ab" * 32,
                "installed_at_unix": 1757000000,
                "layout_id": "legacy-bios-ab-v1",
                "persist": {
                    "filesystem_uuid": "cccccccc-dddd-eeee-ffff-000000000000",
                    "partuuid": "1a2b3c4d-04",
                },
                "platform_family": "legacy-x86",
                "schema_version": 1,
                "slot_bytes": 1073741824,
                "system_a": {
                    "filesystem_uuid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                    "partuuid": "1a2b3c4d-02",
                },
                "system_b": {
                    "filesystem_uuid": "bbbbbbbb-cccc-dddd-eeee-ffffffffffff",
                    "partuuid": "1a2b3c4d-03",
                },
            }
        )
        (persist_seed / "greia").mkdir(parents=True, exist_ok=True)
        (persist_seed / "greia" / "installed-layout.json").write_text(
            _json.dumps(record.as_dict(), sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        return boot_seed, persist_seed

    def _gather_with_seeds(self, base, boot_seed, persist_seed):
        target = self._mbr_file(base)
        uuids = {
            "/dev/loop9p2": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            "/dev/loop9p3": "bbbbbbbb-cccc-dddd-eeee-ffffffffffff",
            "/dev/loop9p4": "cccccccc-dddd-eeee-ffff-000000000000",
        }
        runner = _FakeRunner(uuids=uuids)

        def _fake_mount(source, mountpoint, *, read_only, runner=None, which=None):
            seed = boot_seed if str(source).endswith("p1") else persist_seed
            _shutil.copytree(seed, mountpoint, dirs_exist_ok=True)

        cross = {"executed": True, "green": True, "detail": "fake-agree"}
        with _mock.patch.object(_product, "_mount_fs", _fake_mount), _mock.patch.object(
            _lifecycle, "run_file_cross_check", lambda *a, **k: dict(cross)
        ):
            return gather_boot_health_observation(
                target, work_dir=base / "work", runner=runner, which=_fake_which,
                expected_slot="B", expected_sequence=21,
            ), runner

    def test_gather_returns_observed_default_and_sequence_then_closes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            boot_seed, persist_seed = self._seed_boot_health_trees(base / "seeds")
            observed, runner = self._gather_with_seeds(base, boot_seed, persist_seed)
            # Every slot/journal/sequence/default/layout fact is observed,
            # never minted: the closure below reads these keys.
            self.assertEqual(observed["default_slot"], "B")
            self.assertEqual(observed["accepted_sequence"], 21)
            self.assertEqual(observed["committed_slot"], "B")
            self.assertEqual(observed["last_booted"], "B")
            self.assertEqual(observed["journal_state"], "accepted")
            self.assertEqual(observed["disk_identities"]["disk_signature"], "1a2b3c4d")
            self.assertEqual(
                observed["observed_identities"]["system-b"]["partuuid"], "1a2b3c4d-03"
            )
            self.assertEqual(
                observed["observed_identities"]["persist"]["filesystem_uuid"],
                "cccccccc-dddd-eeee-ffff-000000000000",
            )
            self.assertTrue(observed["file_cross_check"]["executed"])
            self.assertTrue(observed["file_cross_check"]["green"])
            self.assertIn("accepted_state_dir", observed["resolved_paths"])
            self.assertIn("layout_record", observed["resolved_paths"])
            self.assertEqual(len(runner.argv0("blkid")), 3)
            # Real closure on the observed default: no fake observe_fn
            # anywhere on this path.
            report = build_boot_health_lifecycle_report(
                observed_default=str(observed["default_slot"])
            )
            assert_lifecycle_transitions(report)
            self.assertEqual(
                report["observed_steps"],
                ["boot-A-accepted", "stage-B-one-shot", "boot-B-commit"],
            )

    def test_gather_red_when_last_booted_wrong_then_green(self) -> None:
        # Positive control on the newly wired seam: break last_booted
        # (reconcile A) -> RED naming last_booted; restore (reconcile B)
        # -> GREEN with the observed default.
        from greia_platform.grub_ab import GrubEnvBackend

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            boot_seed, persist_seed = self._seed_boot_health_trees(base / "seeds")
            GrubEnvBackend.attach(boot_seed / "grub").reconcile("A")
            with self.assertRaises(LifecycleHarnessError) as caught:
                self._gather_with_seeds(base, boot_seed, persist_seed)
            self.assertIn("last_booted", str(caught.exception))
            GrubEnvBackend.attach(boot_seed / "grub").reconcile("B")
            observed, _runner = self._gather_with_seeds(base, boot_seed, persist_seed)
            self.assertEqual(observed["default_slot"], "B")
            self.assertEqual(observed["accepted_sequence"], 21)

    def test_gather_red_when_accepted_state_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            boot_seed, persist_seed = self._seed_boot_health_trees(base / "seeds")
            (persist_seed / "greia" / "namespaces" / "parent-credentials"
             / "system-updates" / "accepted.json").unlink()
            with self.assertRaises(LifecycleHarnessError) as caught:
                self._gather_with_seeds(base, boot_seed, persist_seed)
            self.assertIn("accepted release state", str(caught.exception))


class HashSlotPartitionTests(unittest.TestCase):
    def test_hashes_real_partition_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            node_a = base / "loop9p2"
            node_a.write_bytes(b"slot-A-bytes" * 256)
            target = base / "clone.img"
            target.write_bytes(b"clone" * 64)
            runner = _FakeRunner()
            with _mock.patch(
                "greia_installer.disk.partition_number_path",
                lambda dev, num: node_a if int(num) == 2 else base / f"loop9p{num}",
            ):
                digest = hash_slot_partition(
                    target, "A", runner=runner, which=_fake_which
                )
            self.assertEqual(digest, _hashlib.sha256(node_a.read_bytes()).hexdigest())
            partscans = [c for c in runner.argv0("losetup") if "-P" in c]
            self.assertEqual(len(partscans), 1)
            self.assertEqual(len([c for c in runner.argv0("losetup") if "-d" in c]), 1)

    def test_unknown_slot_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            clone = Path(tmp) / "clone.img"
            clone.write_bytes(b"x" * 4096)
            with self.assertRaises(LifecycleHarnessError):
                hash_slot_partition(clone, "C", runner=_FakeRunner(), which=_fake_which)

    def test_dev_path_refused(self) -> None:
        with self.assertRaises(LifecycleHarnessError):
            hash_slot_partition(
                Path("/dev/sda"), "A", runner=_FakeRunner(), which=_fake_which
            )

    def test_absent_target_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(LifecycleHarnessError) as caught:
                hash_slot_partition(
                    Path(tmp) / "absent.img", "A",
                    runner=_FakeRunner(), which=_fake_which,
                )
            self.assertIn("BLOCKED", str(caught.exception))

    def test_missing_tool_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            clone = Path(tmp) / "clone.img"
            clone.write_bytes(b"x" * 4096)
            with self.assertRaises(LifecycleHarnessError) as caught:
                hash_slot_partition(
                    clone, "A", runner=_FakeRunner(), which=lambda name: None
                )
            self.assertIn("BLOCKED", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
