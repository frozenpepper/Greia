"""P5.2 install leg through the official image + shipped installer socket.

Covers the brief's install acceptance without QEMU/loop/mount contact:

- the guest runner embeds the exact P5.1 §4 install invocations
  (InstallTransactionClient/socket_transport + prepare/execute with the
  observed identity, profile and nonce/digest), triggers/acks only;
- fail-closed negatives refuse before any slot payload write (missing
  bundle, missing key, profile mismatch, identity changed, no
  legacy/single-root fallback) with a recording-runner positive control
  proving no boot/mutation follows a refusal;
- QEMU argv keeps read-only installer media + disposable writable target
  (+ control disk), refuses /dev, and selects the i386-capable binary;
- host-side inspection uses production parsers (SYSTEM_A, grub.cfg,
  grubenv default A, FIRST_INSTALL_PENDING, observed MBR identities);
- the phased leg drives prepare→execute in order and closes through
  assert_lifecycle_transitions; run_product keeps BLOCKED only for a
  named missing facility/artifact.
"""

from __future__ import annotations

import hashlib as _hashlib
import shutil as _shutil
import struct
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace as _SimpleNamespace
from unittest import mock as _mock

from tools.x8_qemu import product as _product
from tools.x8_qemu.lifecycle import LifecycleConfig, LifecycleHarnessError
from tools.x8_qemu import lifecycle as _lifecycle
from tools.x8_qemu.product import (
    CONTROL_PHASE_FILE,
    DISPOSABLE_TARGET_BYTES,
    INSTALL_LEG_PHASES,
    INSTALL_PROFILE_ID,
    TARGET_DISK_SERIAL,
    TARGET_DISK_TRANSPORT,
    ProductHarness,
    _copy_phase_into_control_image,
    _rebuild_live_squashfs,
    build_install_lifecycle_report,
    control_runner_text,
    create_disposable_target,
    disposable_target_observation,
    gather_installed_target_observation,
    inject_live_clone,
    inspect_installed_roots,
    materialize_control_disk,
    observe_disk_identities_from_mbr,
    preflight_install_composition,
    product_installer_qemu_argv,
    record_live_squashfs_mutation,
    record_shipped_installer_units,
    run_install_leg,
    select_install_qemu_binary,
    write_control_phase,
)


def _hex_identity(seed: str) -> str:
    import hashlib as _hashlib

    return _hashlib.sha256(seed.encode()).hexdigest()


def _valid_fixtures(tmp: Path) -> dict[str, object]:
    bundle = tmp / "greia-release.greiaupdate"
    bundle.write_bytes(b"signed-release" * 64)
    key_dir = tmp / "keys"
    key_dir.mkdir(parents=True, exist_ok=True)
    (key_dir / "release.pem").write_text("public-key\n", encoding="utf-8")
    identity = _hex_identity("disposable-target")
    return {
        "bundle": bundle,
        "key_dir": key_dir,
        "identity": identity,
    }


class RunnerExactInvocationTests(unittest.TestCase):
    def test_runner_embeds_exact_install_invocations(self) -> None:
        text = control_runner_text()
        for required in (
            "InstallTransactionClient",
            "socket_transport",
            ".prepare(",
            "expected_target_identity",
            "compatible_profile_id",
            "settings_snapshot",
            ".execute(",
            "transaction_nonce",
            "plan_digest",
            "read_compatible_profile_id",
        ):
            self.assertIn(required, text)
        # Control still triggers/acks only: ack carries phase/socket, never
        # a boot/disk/identity outcome.
        self.assertIn("poweroff", text)
        self.assertNotIn("grubenv", text)
        self.assertNotIn("last_booted", text)

    def test_runner_positive_control_break_is_red_then_green(self) -> None:
        # Detector: the exact-invocation set above. Break it (socket-only
        # runner without the client calls) -> RED; restore -> GREEN.
        broken = "#!/bin/bash\ntest -S \"$SOCK\" || exit 1\nsystemctl poweroff\n"
        for required in ("InstallTransactionClient", ".prepare(", ".execute("):
            self.assertNotIn(required, broken, f"broken runner unexpectedly has {required}")
        green = control_runner_text()
        for required in ("InstallTransactionClient", ".prepare(", ".execute("):
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


class PreflightNegativeTests(unittest.TestCase):
    def test_missing_bundle_blocked_before_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            fixtures = _valid_fixtures(base)
            calls: list[str] = []
            with self.assertRaises(LifecycleHarnessError) as caught:
                run_install_leg(
                    product_root=base / "product",
                    installer_clone=base / "clone.img",
                    target_image=base / "target.img",
                    control_dir=base / "ctl",
                    profile_id=INSTALL_PROFILE_ID,
                    expected_target_identity=str(fixtures["identity"]),
                    release_bundle=base / "absent.greiaupdate",
                    trusted_key_dir=Path(str(fixtures["key_dir"])),
                    clone_fn=lambda: calls.append("clone"),
                    boot_fn=lambda phase, _doc: calls.append(f"boot:{phase}"),
                    observe_fn=lambda: {"default_slot": "A"},
                )
            self.assertIn("BLOCKED", str(caught.exception))
            self.assertIn("release bundle", str(caught.exception))
            self.assertEqual(calls, [])

    def test_missing_key_blocked_before_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            fixtures = _valid_fixtures(base)
            calls: list[str] = []
            with self.assertRaises(LifecycleHarnessError) as caught:
                preflight_install_composition(
                    release_bundle=Path(str(fixtures["bundle"])),
                    trusted_key_dir=base / "absent-keys",
                    expected_profile_id=INSTALL_PROFILE_ID,
                    prepare_identity=str(fixtures["identity"]),
                    execute_identity=str(fixtures["identity"]),
                )
            self.assertIn("BLOCKED", str(caught.exception))
            self.assertIn("trusted key", str(caught.exception))
            self.assertEqual(calls, [])

    def test_empty_key_dir_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            fixtures = _valid_fixtures(base)
            empty = base / "empty-keys"
            empty.mkdir()
            with self.assertRaises(LifecycleHarnessError) as caught:
                preflight_install_composition(
                    release_bundle=Path(str(fixtures["bundle"])),
                    trusted_key_dir=empty,
                    expected_profile_id=INSTALL_PROFILE_ID,
                    prepare_identity=str(fixtures["identity"]),
                    execute_identity=str(fixtures["identity"]),
                )
            self.assertIn("trusted key", str(caught.exception))

    def test_profile_mismatch_refused_before_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            fixtures = _valid_fixtures(base)
            calls: list[str] = []
            with self.assertRaises(LifecycleHarnessError) as caught:
                run_install_leg(
                    product_root=base / "product",
                    installer_clone=base / "clone.img",
                    target_image=base / "target.img",
                    control_dir=base / "ctl",
                    profile_id="acer-aspire-one-i386",
                    expected_target_identity=str(fixtures["identity"]),
                    release_bundle=Path(str(fixtures["bundle"])),
                    trusted_key_dir=Path(str(fixtures["key_dir"])),
                    clone_fn=lambda: calls.append("clone"),
                    boot_fn=lambda phase, _doc: calls.append(f"boot:{phase}"),
                    observe_fn=lambda: {"default_slot": "A"},
                )
            self.assertIn("target-profile mismatch", str(caught.exception))
            self.assertEqual(calls, [])

    def test_identity_changed_between_prepare_and_execute_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            fixtures = _valid_fixtures(base)
            with self.assertRaises(LifecycleHarnessError) as caught:
                preflight_install_composition(
                    release_bundle=Path(str(fixtures["bundle"])),
                    trusted_key_dir=Path(str(fixtures["key_dir"])),
                    expected_profile_id=INSTALL_PROFILE_ID,
                    prepare_identity=str(fixtures["identity"]),
                    execute_identity=_hex_identity("different-target"),
                )
            self.assertIn("changed between PREPARE_PLAN", str(caught.exception))

    def test_no_legacy_single_root_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            fixtures = _valid_fixtures(base)
            with self.assertRaises(LifecycleHarnessError) as caught:
                preflight_install_composition(
                    release_bundle=Path(str(fixtures["bundle"])),
                    trusted_key_dir=Path(str(fixtures["key_dir"])),
                    expected_profile_id=INSTALL_PROFILE_ID,
                    prepare_identity=str(fixtures["identity"]),
                    execute_identity=str(fixtures["identity"]),
                    layout_adapter_id="legacy-bios-single-v1",
                    boot_backend="none-v1",
                )
            self.assertIn("fallback", str(caught.exception))

    def test_valid_preflight_is_green(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            fixtures = _valid_fixtures(base)
            proof = preflight_install_composition(
                release_bundle=Path(str(fixtures["bundle"])),
                trusted_key_dir=Path(str(fixtures["key_dir"])),
                expected_profile_id=INSTALL_PROFILE_ID,
                prepare_identity=str(fixtures["identity"]),
                execute_identity=str(fixtures["identity"]),
            )
            self.assertEqual(proof["install_mode"], "ab")


class QemuArgvTests(unittest.TestCase):
    def test_installer_snapshot_ide_target_writable_plus_control(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            installer = base / "installer-clone.img"
            installer.write_bytes(b"x" * 4096)
            target = base / "target.img"
            target.write_bytes(b"y" * 4096)
            ctl = base / "ctl.img"
            ctl.write_bytes(b"z" * 4096)
            argv, _serial, _host = product_installer_qemu_argv(
                installer_clone=installer,
                target_image=target,
                control_image=ctl,
                output_dir=base,
                memory_mib=1024,
                cpus=1,
                qemu_binary="qemu-system-i386",
                leg="install-execute",
            )
            text = " ".join(argv)
            self.assertIn(str(installer), text)
            self.assertIn(str(target), text)
            self.assertIn(str(ctl), text)
            # The installer clone rides snapshot-backed ide-hd (never USB:
            # SeaBIOS USB transfers stall on the capable host; QEMU 8.2
            # also refuses a readonly backend behind writable ide-hd).
            # The source image is not attached at all — only the clone.
            self.assertNotIn("usb-storage", text)
            self.assertNotIn("readonly=on", text)
            inst_drives = [a for a in argv if "id=installer" in a]
            self.assertEqual(len(inst_drives), 1)
            self.assertIn("snapshot=on", inst_drives[0])
            inst_devs = [a for a in argv if a.startswith("ide-hd,drive=installer")]
            self.assertEqual(len(inst_devs), 1)
            self.assertIn("bootindex=1", inst_devs[0])
            # The control disk must ride snapshot=on (QEMU 8.2 refuses a
            # readonly backend behind writable ide-hd).
            ctl_drives = [a for a in argv if "id=ctl" in a]
            self.assertEqual(len(ctl_drives), 1)
            self.assertIn("snapshot=on", ctl_drives[0])
            self.assertNotIn("readonly", ctl_drives[0])
            # Explicit IDE placement: three auto-placed ide-hd collide.
            self.assertIn("ide-hd,drive=target,bus=ide.0,unit=1", text)
            self.assertIn("ide-hd,drive=ctl,bus=ide.1,unit=0", text)
            # KVM with TCG fallback (never TCG-only on this lane).
            machine = argv[argv.index("-machine") + 1]
            self.assertEqual(machine, "pc,accel=kvm:tcg")
            self.assertIn("-no-reboot", argv)
            self.assertIn("none", argv)

    def test_block_device_paths_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            with self.assertRaises(LifecycleHarnessError):
                product_installer_qemu_argv(
                    installer_clone=Path("/dev/sda"),
                    target_image=base / "t.img",
                    control_image=None,
                    output_dir=base,
                    memory_mib=1024,
                    cpus=1,
                    qemu_binary="qemu-system-i386",
                )

    def test_qemu_binary_prefers_i386_then_falls_back(self) -> None:
        self.assertEqual(
            select_install_qemu_binary(
                runner_which=lambda name: f"/usr/bin/{name}"
            ),
            "/usr/bin/qemu-system-i386",
        )
        self.assertEqual(
            select_install_qemu_binary(
                runner_which=lambda name: (
                    None if name == "qemu-system-i386" else "/usr/bin/qemu-system-x86_64"
                )
            ),
            "/usr/bin/qemu-system-x86_64",
        )
        with self.assertRaises(LifecycleHarnessError) as caught:
            select_install_qemu_binary(runner_which=lambda _name: None)
        self.assertIn("BLOCKED", str(caught.exception))

    def test_create_disposable_target_refuses_dev_and_existing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            with self.assertRaises(LifecycleHarnessError):
                create_disposable_target(Path("/dev/sda"))
            existing = base / "t.img"
            existing.write_bytes(b"old")
            with self.assertRaises(LifecycleHarnessError):
                create_disposable_target(existing)
            fresh = base / "fresh.img"
            with _mock.patch(
                "tools.x8_qemu.product.subprocess.run"
            ) as run_mock:
                def _fake(argv: object, **kwargs: object):  # type: ignore[no-untyped-def]
                    fresh.write_bytes(b"\0" * 4096)
                    return _mock.Mock(returncode=0)

                run_mock.side_effect = _fake
                proof = create_disposable_target(fresh, size_bytes=4096)
            self.assertEqual(proof["size_bytes"], 4096)


class HostInspectionTests(unittest.TestCase):
    def _green_roots(self, base: Path) -> dict[str, Path]:
        from greia_platform.boot_transaction import BootTransactionJournal
        from greia_platform.grub_ab import GrubEnvBackend
        from greia_platform.persistent_layout import InstalledLayoutRecord
        from greia_platform.grub_ab import render_grub_ab_config_from_record

        record = InstalledLayoutRecord.from_dict(
            {
                "accepted_release_id": "greia-0.20.0",
                "accepted_release_sequence": 20,
                "accepted_slot": "A",
                "boot_backend": "grub-ab-v1",
                "boot_control": {"active_slot": "A", "kind": "grub-env-v1"},
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
        boot_control = base / "boot-control"
        backend_state = base / "backend-state"
        journal_dir = base / "journal"
        boot_control.mkdir(parents=True)
        backend_state.mkdir(parents=True)
        journal_dir.mkdir(parents=True)
        grub_text = render_grub_ab_config_from_record(
            record=record,
            password_hash="grub.pbkdf2.sha512.10000.ABCDEF0123456789",
            developer=False,
        )
        (boot_control / "grub.cfg").write_text(grub_text, encoding="utf-8")
        GrubEnvBackend.initialize(backend_state, default_slot="A")
        BootTransactionJournal.begin_first_install(
            journal_dir,
            layout_id="legacy-bios-ab-v1",
            boot_backend="grub-ab-v1",
            release_id="greia-0.20.0",
            release_sequence=20,
        )
        return {
            "boot_control": boot_control,
            "backend_state": backend_state,
            "journal": journal_dir,
        }

    def test_inspect_green_through_production_parsers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            roots = self._green_roots(base)
            observed = inspect_installed_roots(
                boot_control_dir=roots["boot_control"],
                backend_state_dir=roots["backend_state"],
                journal_dir=roots["journal"],
                observed_identities={
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
            )
            self.assertTrue(observed["system_a_present"])
            self.assertTrue(observed["grub_cfg_valid"])
            self.assertEqual(observed["grubenv_default"], "A")
            self.assertEqual(observed["journal_state"], "first_install_pending")

    def test_inspect_red_then_green_positive_control(self) -> None:
        # Break: remove grub.cfg -> RED. Restore -> GREEN.
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            roots = self._green_roots(base)
            identities = {
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
            }
            grub_cfg = roots["boot_control"] / "grub.cfg"
            saved = grub_cfg.read_bytes()
            grub_cfg.unlink()
            with self.assertRaises(LifecycleHarnessError):
                inspect_installed_roots(
                    boot_control_dir=roots["boot_control"],
                    backend_state_dir=roots["backend_state"],
                    journal_dir=roots["journal"],
                    observed_identities=identities,
                )
            grub_cfg.write_bytes(saved)
            back = inspect_installed_roots(
                boot_control_dir=roots["boot_control"],
                backend_state_dir=roots["backend_state"],
                journal_dir=roots["journal"],
                observed_identities=identities,
            )
            self.assertEqual(back["grubenv_default"], "A")

    def test_inspect_refuses_cloned_identities(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            roots = self._green_roots(base)
            with self.assertRaises(LifecycleHarnessError):
                inspect_installed_roots(
                    boot_control_dir=roots["boot_control"],
                    backend_state_dir=roots["backend_state"],
                    journal_dir=roots["journal"],
                    observed_identities={
                        "system-a": {
                            "partuuid": "1a2b3c4d-02",
                            "filesystem_uuid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                        },
                        "system-b": {
                            "partuuid": "1a2b3c4d-02",
                            "filesystem_uuid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                        },
                        "persist": {
                            "partuuid": "1a2b3c4d-04",
                            "filesystem_uuid": "cccccccc-dddd-eeee-ffff-000000000000",
                        },
                    },
                )

    def test_mbr_observation_reads_real_bytes_never_mints(self) -> None:
        mbr = bytearray(512)
        struct.pack_into("<I", mbr, 440, 0x1A2B3C4D)
        for number in (2, 3, 4):
            offset = 446 + (number - 1) * 16
            mbr[offset + 4] = 0x83
        mbr[510] = 0x55
        mbr[511] = 0xAA
        observed = observe_disk_identities_from_mbr(bytes(mbr))
        self.assertEqual(observed["disk_signature"], "1a2b3c4d")
        self.assertEqual(observed["system_a_partuuid"], "1a2b3c4d-02")
        self.assertEqual(observed["system_b_partuuid"], "1a2b3c4d-03")
        self.assertEqual(observed["persist_partuuid"], "1a2b3c4d-04")
        with self.assertRaises(LifecycleHarnessError):
            observe_disk_identities_from_mbr(b"short")

    def test_squashfs_mutation_record_names_clone_only_change(self) -> None:
        record = record_live_squashfs_mutation(
            pre_sha256="aa" * 32,
            post_sha256="bb" * 32,
            injected_files=["etc/systemd/system/greia-x8-control.service"],
        )
        self.assertFalse(record["source_image_mutated"])
        self.assertEqual(record["pre_sha256"], "aa" * 32)
        with self.assertRaises(LifecycleHarnessError):
            record_live_squashfs_mutation(
                pre_sha256="not-a-sha",
                post_sha256="bb" * 32,
                injected_files=["x"],
            )


class PhasedLegTests(unittest.TestCase):
    def test_leg_drives_prepare_then_execute_and_closes_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            fixtures = _valid_fixtures(base)
            seen: list[str] = []
            phases_seen: list[str] = []

            def _boot(phase: str, doc: dict[str, object]) -> None:
                phases_seen.append(phase)
                self.assertEqual(
                    doc["phase"], phase
                )
                inputs = dict(doc.get("inputs", {}))  # type: ignore[arg-type]
                self.assertEqual(
                    inputs["expected_target_identity"], str(fixtures["identity"])
                )
                self.assertEqual(inputs["compatible_profile_id"], INSTALL_PROFILE_ID)

            result = run_install_leg(
                product_root=base / "product",
                installer_clone=base / "clone.img",
                target_image=base / "target.img",
                control_dir=base / "ctl",
                profile_id=INSTALL_PROFILE_ID,
                expected_target_identity=str(fixtures["identity"]),
                release_bundle=Path(str(fixtures["bundle"])),
                trusted_key_dir=Path(str(fixtures["key_dir"])),
                clone_fn=lambda: seen.append("clone"),
                boot_fn=_boot,
                observe_fn=lambda: {
                    "default_slot": "A",
                    "target_identity": str(fixtures["identity"]),
                },
            )
            self.assertEqual(seen, ["clone"])
            self.assertEqual(phases_seen, list(INSTALL_LEG_PHASES))
            self.assertEqual(result["phases"], list(INSTALL_LEG_PHASES))
            self.assertEqual(result["install_mode"], "ab")

    def test_leg_report_shape_passes_frozen_contract(self) -> None:
        report = build_install_lifecycle_report(observed_default="A")
        self.assertEqual(report["observed_steps"], ["fresh-install-A", "boot-A-accepted"])
        with self.assertRaises(LifecycleHarnessError):
            build_install_lifecycle_report(observed_default="B")

    def test_run_product_blocked_names_facility_not_unconditional(self) -> None:
        import inspect as _inspect

        from tools.x8_qemu import product as _product

        source = _inspect.getsource(_product.ProductHarness.run_product)
        self.assertNotIn("not yet wired", source)
        self.assertIn("clone_product_image", source)
        self.assertIn("product_installer_qemu_argv", source)
        self.assertIn("assert_lifecycle_transitions", source)
        with tempfile.TemporaryDirectory() as tmp:
            harness = ProductHarness(
                LifecycleConfig(output_dir=Path(tmp) / "out")
            )
            with self.assertRaises(LifecycleHarnessError) as caught:
                harness.run_product()
            self.assertIn("BLOCKED", str(caught.exception))

    def test_disposable_target_size_matches_acer_floor(self) -> None:
        self.assertEqual(DISPOSABLE_TARGET_BYTES, 7 * 1024**3)


class _FakeRunner:
    """Recording subprocess double with loop/probe/fs-effect simulation.

    Simulates only what a unit host cannot do (losetup mount blkid
    squashfs tool outputs); every argv still flows through the production
    helpers under test, so a missing/bypassed call is RED here.
    """

    def __init__(self, *, loopdev="/dev/loop9", uuids=None, socket_unit=True):
        self.calls: list[list[str]] = []
        self.loopdev = loopdev
        self.uuids = dict(uuids or {})
        # The exploded live-system tree carries the shipped transaction
        # socket unit (production pull: graphical UI); opt out to prove
        # the clone refuses a missing unit instead of substituting one.
        self.socket_unit = bool(socket_unit)

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
        elif prog == "unsquashfs":
            dest = argv[argv.index("-d") + 1]
            unit_dir = Path(dest) / "etc/systemd/system"
            unit_dir.mkdir(parents=True, exist_ok=True)
            if self.socket_unit:
                (unit_dir / "greia-install-transaction.socket").write_text(
                    "[Unit]\nDescription=test socket\n\n"
                    "[Socket]\nListenStream=/run/greia-os/install-transaction.sock\n",
                    encoding="utf-8",
                )
        elif prog == "mksquashfs":
            src, dst = argv[1], argv[2]
            Path(dst).write_bytes(b"squashfs-rebuilt:" + Path(src).name.encode())
        return _SimpleNamespace(returncode=0, stdout=stdout, stderr="")

    def argv0(self, name):
        return [c for c in self.calls if c and c[0].rsplit("/", 1)[-1] == name]


def _capable_host():
    """Simulate a capable Linux/QEMU host around run_product wiring tests.

    Patches only the host gate + QEMU selection; loop/QEMU execution
    itself arrives through the tests' recording fakes. Never patches the
    preflight, parsers or lifecycle contract.
    """
    return (
        _mock.patch.object(
            _product, "require_product_host", lambda **kwargs: None
        ),
        _mock.patch.object(
            _product, "select_install_qemu_binary", lambda **kwargs: "qemu-system-i386"
        ),
    )


def _fake_which(name):
    """Pretend every named host tool resolves (execution stays faked)."""
    return f"/usr/bin/{name}"


class RunProductWiringTests(unittest.TestCase):
    def test_missing_bundle_refused_before_any_scratch_or_boot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            fixtures = _valid_fixtures(base)
            calls: list[str] = []
            gate, qemu = _capable_host()
            with gate, qemu:
                harness = ProductHarness(
                    LifecycleConfig(output_dir=base / "out"),
                    official_image=base / "installer.img",
                )
                (base / "installer.img").write_bytes(b"installer" * 64)
                with self.assertRaises(LifecycleHarnessError) as caught:
                    harness.run_product(
                        release_bundle=base / "absent.greiaupdate",
                        trusted_key_dir=Path(str(fixtures["key_dir"])),
                        target_fn=lambda p: calls.append("target") or {},
                        clone_fn=lambda s, d: calls.append("clone") or {},
                        inject_fn=lambda c: calls.append("inject") or {},
                        materialize_fn=lambda d, i: calls.append("materialize"),
                        boot_fn=lambda *a: calls.append("boot"),
                        observe_fn=lambda t: calls.append("observe") or {},
                    )
            self.assertIn("BLOCKED", str(caught.exception))
            self.assertIn("release bundle", str(caught.exception))
            self.assertEqual(calls, [])

    def test_missing_key_refused_before_any_scratch_or_boot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            fixtures = _valid_fixtures(base)
            calls: list[str] = []
            gate, qemu = _capable_host()
            with gate, qemu:
                harness = ProductHarness(
                    LifecycleConfig(output_dir=base / "out"),
                    official_image=base / "installer.img",
                )
                (base / "installer.img").write_bytes(b"installer" * 64)
                with self.assertRaises(LifecycleHarnessError) as caught:
                    harness.run_product(
                        release_bundle=Path(str(fixtures["bundle"])),
                        trusted_key_dir=base / "absent-keys",
                        target_fn=lambda p: calls.append("target") or {},
                        clone_fn=lambda s, d: calls.append("clone") or {},
                        inject_fn=lambda c: calls.append("inject") or {},
                        materialize_fn=lambda d, i: calls.append("materialize"),
                        boot_fn=lambda *a: calls.append("boot"),
                        observe_fn=lambda t: calls.append("observe") or {},
                    )
            self.assertIn("BLOCKED", str(caught.exception))
            self.assertIn("trusted key", str(caught.exception))
            self.assertEqual(calls, [])

    def test_non_a_observation_refuses_before_closure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            fixtures = _valid_fixtures(base)
            boots: list[str] = []
            gate, qemu = _capable_host()
            with gate, qemu:
                harness = ProductHarness(
                    LifecycleConfig(output_dir=base / "out"),
                    official_image=base / "installer.img",
                )
                (base / "installer.img").write_bytes(b"installer" * 64)
                with self.assertRaises(LifecycleHarnessError):
                    harness.run_product(
                        release_bundle=Path(str(fixtures["bundle"])),
                        trusted_key_dir=Path(str(fixtures["key_dir"])),
                        target_fn=lambda p: {
                            "target": str(p),
                            "size_bytes": DISPOSABLE_TARGET_BYTES,
                        },
                        clone_fn=lambda s, d: {"clone": str(d)},
                        inject_fn=lambda c: {"clone_injection": True},
                        materialize_fn=lambda d, i: None,
                        boot_fn=lambda phase, *a: boots.append(phase),
                        observe_fn=lambda t: {"default_slot": "B"},
                    )
            # Both guest phases ran, but the contract refused the
            # non-A observation: closure depends on observed facts.
            self.assertEqual(boots, list(INSTALL_LEG_PHASES))

    def test_full_fake_leg_closes_with_observed_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            fixtures = _valid_fixtures(base)
            seen: dict[str, object] = {}
            gate, qemu = _capable_host()
            with gate, qemu:
                harness = ProductHarness(
                    LifecycleConfig(output_dir=base / "out"),
                    official_image=base / "installer.img",
                )
                (base / "installer.img").write_bytes(b"installer" * 64)

                def _boot(phase, argv, serial_log, host_log):
                    seen.setdefault("boots", []).append(phase)  # type: ignore[attr-defined]
                    seen["argv"] = list(argv)

                result = harness.run_product(
                    release_bundle=Path(str(fixtures["bundle"])),
                    trusted_key_dir=Path(str(fixtures["key_dir"])),
                    target_fn=None,  # real sparse target via truncate
                    clone_fn=lambda s, d: {
                        "source_sha256": _product.sha256_file(Path(s)),
                        "clone": str(d),
                    },
                    inject_fn=lambda c: {
                        "clone": str(c),
                        "injected_files": ["x"],
                        "pre_sha256": "aa" * 32,
                        "post_sha256": "bb" * 32,
                        "source_image_mutated": False,
                    },
                    materialize_fn=lambda d, i: None,
                    boot_fn=_boot,
                    observe_fn=lambda t: {
                        "default_slot": "A",
                        "target_identity": "observed",
                    },
                )
            self.assertTrue(result["ok"])
            self.assertEqual(result["phases"], list(INSTALL_LEG_PHASES))
            self.assertEqual(result["preflight"]["install_mode"], "ab")
            identity = str(result["expected_target_identity"])
            self.assertRegex(identity, r"^[0-9a-f]{64}$")
            # Identity is the production DeviceObservation digest for the
            # real disposable target, never a hash of the clone.
            check = disposable_target_observation(
                base / "out/product/disposable-target.img",
                size_bytes=DISPOSABLE_TARGET_BYTES,
            )
            self.assertEqual(identity, check.identity_digest)
            self.assertEqual(check.serial, TARGET_DISK_SERIAL)
            # Shipped units are recorded from the repo tree by SHA.
            shipped = result["shipped_units"]
            self.assertIn("greia-install-transaction.service", shipped["sha256"])
            self.assertIn("greia-install-transaction.socket", shipped["sha256"])
            # The phase channel carried the observed identity + profile.
            import json as _json

            phase_doc = _json.loads(
                (base / "out/product/control-disk/phase.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(
                phase_doc["inputs"]["expected_target_identity"], identity
            )
            self.assertEqual(
                phase_doc["inputs"]["compatible_profile_id"], INSTALL_PROFILE_ID
            )
            # QEMU binds the same serial the host observation mirrors.
            self.assertIn(TARGET_DISK_SERIAL, " ".join(seen["argv"]))  # type: ignore[index]

    def test_run_product_source_pins_production_wiring(self) -> None:
        import inspect as _inspect

        source = _inspect.getsource(_product.ProductHarness.run_product)
        for required in (
            "preflight_install_composition",
            "disposable_target_observation",
            "inject_live_clone",
            "materialize_control_disk",
            "_observe_installed_target",
            "build_install_lifecycle_report",
            "assert_lifecycle_transitions",
            "_require_install_artifacts",
        ):
            self.assertIn(required, source)
        self.assertNotIn("disposable-target:", source)

    def test_shipped_units_recorded_or_blocked(self) -> None:
        recorded = record_shipped_installer_units()
        self.assertEqual(
            set(recorded["sha256"]),  # type: ignore[index]
            {
                "greia-install-transaction.service",
                "greia-install-transaction.socket",
            },
        )
        with self.assertRaises(LifecycleHarnessError) as caught:
            record_shipped_installer_units(project_root=Path("/nonexistent-root"))
        self.assertIn("BLOCKED", str(caught.exception))


class ControlDiskCopyTests(unittest.TestCase):
    def test_copy_drives_loop_mount_cp_umount_detach(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            control = base / "ctl"
            write_control_phase(
                control,
                phase="install-prepare",
                inputs={"expected_target_identity": "ab" * 32},
            )
            image = base / "ctl.img"
            image.write_bytes(b"\0" * 4096)
            runner = _FakeRunner()
            proof = _copy_phase_into_control_image(
                control, image, runner=runner, which=_fake_which
            )
            self.assertEqual(proof["copied"], [CONTROL_PHASE_FILE])
            self.assertEqual(proof["phase"], "install-prepare")
            self.assertEqual(proof["loop_device"], "/dev/loop9")
            kinds = [c[0].rsplit("/", 1)[-1] for c in runner.calls]
            self.assertIn("losetup", kinds)
            self.assertIn("mount", kinds)
            self.assertIn("umount", kinds)
            copies = runner.argv0("cp")
            self.assertEqual(len(copies), 1)
            self.assertTrue(copies[0][2].endswith(CONTROL_PHASE_FILE))
            self.assertTrue(copies[0][3].endswith(CONTROL_PHASE_FILE))
            detaches = [c for c in runner.argv0("losetup") if "-d" in c]
            self.assertEqual(len(detaches), 1)

    def test_copy_missing_tool_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            control = base / "ctl"
            write_control_phase(control, phase="install-prepare")
            with _mock.patch("shutil.which", return_value=None):
                with self.assertRaises(LifecycleHarnessError) as caught:
                    _copy_phase_into_control_image(
                        control, base / "ctl.img", which=lambda name: None
                    )
            self.assertIn("BLOCKED", str(caught.exception))

    def test_materialize_truncates_formats_then_copies(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            control = base / "ctl"
            write_control_phase(control, phase="install-execute")
            runner = _FakeRunner()
            proof = materialize_control_disk(
                control, base / "ctl.img", runner=runner, which=_fake_which
            )
            self.assertEqual(proof["phase"], "install-execute")
            self.assertEqual(proof["phase_copied"], [CONTROL_PHASE_FILE])
            kinds = [c[0].rsplit("/", 1)[-1] for c in runner.calls]
            self.assertIn("truncate", kinds)
            self.assertIn("mkfs.ext4", kinds)
            self.assertIn("mount", kinds)
            self.assertEqual(len(runner.argv0("cp")), 1)


class SquashfsRebuildTests(unittest.TestCase):
    def _live_tree(self, base: Path) -> Path:
        # Live-partition layer only (squashfs + grub.cfg). The shipped
        # transaction socket unit lives inside the squashfs payload and
        # arrives in the exploded tree via the unsquashfs fake.
        squashfs = base / "live" / "filesystem.squashfs"
        squashfs.parent.mkdir(parents=True, exist_ok=True)
        squashfs.write_bytes(b"live-original" * 64)
        grub = base / "boot" / "grub" / "grub.cfg"
        grub.parent.mkdir(parents=True, exist_ok=True)
        grub.write_text(
            "set timeout=0\n"
            "menuentry 'Install Greia OS' --unrestricted {\n"
            "  linux /live/vmlinuz boot=live console=null quiet splash\n"
            "  initrd /live/initrd.img\n"
            "}\n",
            encoding="utf-8",
        )
        return base

    def test_rebuild_hashes_injects_and_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            mountpoint = self._live_tree(base / "mnt")
            work = base / "work"
            work.mkdir()
            runner = _FakeRunner()
            rebuilt = _rebuild_live_squashfs(
                mountpoint, work, mask_service="greia-installer.service",
                runner=runner,
            )
            self.assertRegex(rebuilt["pre_sha256"], r"^[0-9a-f]{64}$")
            self.assertRegex(rebuilt["post_sha256"], r"^[0-9a-f]{64}$")
            self.assertNotEqual(rebuilt["pre_sha256"], rebuilt["post_sha256"])
            mutation = rebuilt["squashfs_mutation"]
            self.assertFalse(mutation["source_image_mutated"])
            self.assertEqual(
                rebuilt["injected_files"],
                [
                    "etc/systemd/system/greia-x8-control.service",
                    "usr/local/sbin/greia-x8-control",
                    "etc/systemd/system/multi-user.target.wants/greia-x8-control.service",
                    "etc/systemd/system/greia-installer.service -> /dev/null (masked in clone only)",
                ],
            )
            exploded = work / "squashfs-root"
            self.assertTrue(
                (exploded / "usr/local/sbin/greia-x8-control").is_file()
            )
            masked = exploded / "etc/systemd/system/greia-installer.service"
            self.assertTrue(masked.is_symlink())
            kinds = [c[0].rsplit("/", 1)[-1] for c in runner.calls]
            self.assertIn("unsquashfs", kinds)
            rebuilds = runner.argv0("mksquashfs")
            self.assertEqual(len(rebuilds), 1)
            self.assertIn("-comp", rebuilds[0])
            self.assertIn("xz", rebuilds[0])
            # Regression: the rebuilt image must land in the host work_dir,
            # never side-by-side on the ~90%-full live partition (ENOSPC).
            self.assertTrue(
                Path(rebuilds[0][2]).resolve().is_relative_to(work.resolve())
                if hasattr(Path("."), "is_relative_to")
                else str(work.resolve()) in str(Path(rebuilds[0][2]).resolve()),
                f"mksquashfs output escapes work_dir: {rebuilds[0][2]}",
            )
            self.assertNotIn(str(mountpoint.resolve()), str(Path(rebuilds[0][2]).resolve()))

    def test_rebuild_refuses_without_squashfs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            mountpoint = base / "mnt"
            mountpoint.mkdir()
            work = base / "work"
            work.mkdir()
            runner = _FakeRunner()
            with self.assertRaises(LifecycleHarnessError):
                _rebuild_live_squashfs(
                    mountpoint, work, mask_service="greia-installer.service",
                    runner=runner,
                )
            self.assertEqual(runner.argv0("unsquashfs"), [])

    def test_inject_end_to_end_through_loop_seams(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            seed = base / "seed"
            self._live_tree(seed)
            clone = base / "clone.img"
            clone.write_bytes(b"clone" * 64)
            runner = _FakeRunner()

            def _fake_mount(source, mountpoint, *, read_only, runner=None, which=None):
                _shutil.copytree(seed, mountpoint, dirs_exist_ok=True)

            with _mock.patch.object(_product, "_mount_fs", _fake_mount):
                proof = inject_live_clone(clone, runner=runner, which=_fake_which)
            self.assertEqual(proof["squashfs_path"], "live/filesystem.squashfs")
            self.assertRegex(proof["pre_sha256"], r"^[0-9a-f]{64}$")
            self.assertRegex(proof["post_sha256"], r"^[0-9a-f]{64}$")
            self.assertFalse(proof["source_image_mutated"])
            self.assertIn(
                "squashfs_mutation", proof
            )
            # Clone-only serial console: one installer entry patched.
            grub = proof["grub_console"]
            self.assertEqual(grub["grub_cfg"], "boot/grub/grub.cfg")
            self.assertEqual(grub["substitutions"], 1)
            self.assertFalse(grub["source_image_mutated"])
            self.assertRegex(grub["pre_sha256"], r"^[0-9a-f]{64}$")
            self.assertRegex(grub["post_sha256"], r"^[0-9a-f]{64}$")
            # Clone-only socket enablement: the shipped transaction
            # socket the masked graphical session would otherwise pull.
            sock = proof["socket_enabled"]
            self.assertEqual(sock["unit"], "greia-install-transaction.socket")
            self.assertEqual(
                sock["wants_link"],
                "etc/systemd/system/sockets.target.wants/greia-install-transaction.socket",
            )
            self.assertFalse(sock["source_image_mutated"])
            partscans = [
                c for c in runner.argv0("losetup") if "-P" in c
            ]
            self.assertEqual(len(partscans), 1)
            self.assertEqual(len(runner.argv0("unsquashfs")), 1)
            self.assertEqual(len(runner.argv0("mksquashfs")), 1)
            self.assertEqual(
                len([c for c in runner.argv0("losetup") if "-d" in c]), 1
            )

    def test_inject_refuses_without_shipped_socket_unit(self) -> None:
        # Fail-closed: an exploded tree without the shipped transaction
        # socket unit refuses instead of substituting a harness unit.
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            seed = base / "seed"
            self._live_tree(seed)
            clone = base / "clone.img"
            clone.write_bytes(b"clone" * 64)
            runner = _FakeRunner(socket_unit=False)

            def _fake_mount(source, mountpoint, *, read_only, runner=None, which=None):
                _shutil.copytree(seed, mountpoint, dirs_exist_ok=True)

            with _mock.patch.object(_product, "_mount_fs", _fake_mount):
                with self.assertRaises(LifecycleHarnessError):
                    inject_live_clone(clone, runner=runner, which=_fake_which)


class GatherObservationTests(unittest.TestCase):
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

    def _seed_installed_tree(self, base: Path) -> tuple[Path, Path]:
        from greia_platform.boot_transaction import BootTransactionJournal
        from greia_platform.grub_ab import GrubEnvBackend
        from greia_platform.persistent_layout import InstalledLayoutRecord
        from greia_platform.grub_ab import render_grub_ab_config_from_record

        record = InstalledLayoutRecord.from_dict(
            {
                "accepted_release_id": "greia-0.20.0",
                "accepted_release_sequence": 20,
                "accepted_slot": "A",
                "boot_backend": "grub-ab-v1",
                "boot_control": {"active_slot": "A", "kind": "grub-env-v1"},
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
        boot = base / "boot-seed"
        persist = base / "persist-seed"
        boot.mkdir(parents=True)
        persist.mkdir(parents=True)
        (boot / "grub.cfg").write_text(
            render_grub_ab_config_from_record(
                record=record,
                password_hash="grub.pbkdf2.sha512.10000.ABCDEF0123456789",
                developer=False,
            ),
            encoding="utf-8",
        )
        GrubEnvBackend.initialize(boot / "grub", default_slot="A")
        BootTransactionJournal.begin_first_install(
            persist,
            layout_id="legacy-bios-ab-v1",
            boot_backend="grub-ab-v1",
            release_id="greia-0.20.0",
            release_sequence=20,
        )
        return boot, persist

    def _gather(self, base, *, with_grub_cfg=True):
        boot_seed, persist_seed = self._seed_installed_tree(base / "seeds")
        if not with_grub_cfg:
            (boot_seed / "grub.cfg").unlink()
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
            return gather_installed_target_observation(
                target, work_dir=base / "work", runner=runner, which=_fake_which
            ), runner

    def test_gather_reads_real_mbr_and_parsers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            observed, runner = self._gather(Path(tmp))
            self.assertEqual(observed["default_slot"], "A")
            self.assertEqual(
                observed["disk_identities"]["disk_signature"], "1a2b3c4d"
            )
            self.assertEqual(
                observed["observed_identities"]["system-a"]["partuuid"],
                "1a2b3c4d-02",
            )
            self.assertEqual(
                observed["observed_identities"]["persist"]["filesystem_uuid"],
                "cccccccc-dddd-eeee-ffff-000000000000",
            )
            self.assertTrue(observed["file_cross_check"]["executed"])
            self.assertTrue(observed["file_cross_check"]["green"])
            inspection = observed["inspection"]
            self.assertTrue(inspection["system_a_present"])
            self.assertEqual(inspection["journal_state"], "first_install_pending")
            self.assertIn("boot_control_dir", observed["resolved_paths"])
            blkid_calls = runner.argv0("blkid")
            self.assertEqual(len(blkid_calls), 3)

    def test_gather_red_when_grub_cfg_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(LifecycleHarnessError):
                self._gather(Path(tmp), with_grub_cfg=False)


if __name__ == "__main__":
    unittest.main()
