"""X8-GRUB source-scope tests: A/B entries, grubenv one-shot backend.

R0/R1 only: files and fakes. No physical boot-control writes, no
bootloader-default changes on valued disks, no device contact. The
grubenv backend persists to regular files in temporary directories so
one-shot consumption, failure fallback and crash reconcile are proven
without hardware. Failure-injection cases use disposable loop-style
observations (plain temporary paths), never a valued disk.
"""

from __future__ import annotations

import hashlib
import inspect
import re
import tempfile
import unittest
from pathlib import Path

from greia_platform import grub_ab as grub_ab_module
from greia_platform.boot_contract import GrubContractError
from greia_platform.boot_transaction import (
    BootArtifactSet,
    BootBackendState,
    BootTransactionBackend,
    BootTransactionCoordinator,
    BootTransactionError,
    BootTransactionState,
    coordinator_accepts_backend,
)
from greia_platform.grub_ab import (
    GRUBENV_FILE_NAME,
    GRUBENV_HEADER,
    GRUBENV_SIZE,
    GRUB_INITRAMFS_PATH,
    GRUB_KERNEL_PATH,
    GrubAbConfigError,
    GrubEnvBackend,
    render_grub_ab_config,
    render_grub_ab_config_from_record,
    validate_grub_ab_text,
)
from greia_platform.grub_security import GRUB_USER
from greia_platform.persistent_layout import InstalledLayoutRecord
from greia_platform.slot_writer import FINALIZER_VERSION, FinalizationReceipt

_UUID_A = "11111111-2222-3333-4444-555555555555"
_UUID_A_FS = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
_UUID_B = "22222222-3333-4444-5555-666666666666"
_UUID_B_FS = "bbbbbbbb-cccc-dddd-eeee-ffffffffffff"
_UUID_P = "33333333-4444-5555-6666-777777777777"
_UUID_P_FS = "cccccccc-dddd-eeee-ffff-000000000000"
_INSTALL_SHA = "ab" * 32
_KERNEL_A = hashlib.sha256(b"candidate-kernel-bytes").hexdigest()
_INITRAMFS_A = hashlib.sha256(b"candidate-initramfs-bytes").hexdigest()
_INVENTORY = "cd" * 32
_SUPPORT = "ef" * 32
_PASSWORD_HASH = "grub.pbkdf2.sha512.10000.ABCDEF0123456789"


def _record_dict(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "accepted_release_id": "greia-0.14.0",
        "accepted_slot": "A",
        "boot_backend": "grub-ab-v1",
        "boot_control": {"active_slot": "A", "kind": "grub-env-v1"},
        "install_profile": "modern-amd64",
        "install_target_sha256": _INSTALL_SHA,
        "installed_at_unix": 1757000000,
        "layout_id": "modern-gpt-ab-v1",
        "persist": {"filesystem_uuid": _UUID_P_FS, "partuuid": _UUID_P},
        "platform_family": "standard-x86-64",
        "schema_version": 1,
        "slot_bytes": 1024 * 1024 * 1024,
        "system_a": {"filesystem_uuid": _UUID_A_FS, "partuuid": _UUID_A},
        "system_b": {"filesystem_uuid": _UUID_B_FS, "partuuid": _UUID_B},
    }
    base.update(overrides)
    return base


def _receipt(slot: str, *, layout_id: str = "modern-gpt-ab-v1") -> FinalizationReceipt:
    return FinalizationReceipt(
        schema_version=1,
        finalizer_version=FINALIZER_VERSION,
        release_id="greia-0.15.0",
        slot=slot,
        role=f"system-{slot.lower()}",
        base_sha256=_KERNEL_A,
        base_bytes=200 * 1024,
        support_sha256=_SUPPORT,
        support_size=1024,
        inventory_token=_INVENTORY,
        packages=(),
        packages_digest=hashlib.sha256(b"\n").hexdigest(),
        generic_kernel_sha256=_KERNEL_A,
        host_initramfs_sha256=_INITRAMFS_A,
        filesystem_uuid=_UUID_B_FS if slot == "B" else _UUID_A_FS,
        layout_id=layout_id,
        slot_capacity_bytes=1024 * 1024 * 1024,
    )


def _artifacts() -> tuple[BootArtifactSet, BootArtifactSet]:
    record = InstalledLayoutRecord.from_dict(_record_dict())
    return (
        BootArtifactSet.from_finalization(receipt=_receipt("A"), record=record),
        BootArtifactSet.from_finalization(receipt=_receipt("B"), record=record),
    )


def _config(*, developer: bool = False) -> str:
    artifact_a, artifact_b = _artifacts()
    return render_grub_ab_config(
        artifact_a=artifact_a, artifact_b=artifact_b,
        password_hash=_PASSWORD_HASH, developer=developer,
    )


class ConfigGenerationTests(unittest.TestCase):
    def test_fixed_entries_bind_adapter_paths_and_layout_roots(self) -> None:
        text = _config()
        self.assertIn("--id greia-a", text)
        self.assertIn("--id greia-b", text)
        self.assertIn(f"linux {GRUB_KERNEL_PATH} ", text)
        self.assertIn(f"initrd {GRUB_INITRAMFS_PATH}", text)
        # Kernel ABI keeps the observed PARTUUID per slot ...
        self.assertIn(f"root=PARTUUID={_UUID_A}", text)
        self.assertIn(f"root=PARTUUID={_UUID_B}", text)
        # ... while GRUB locates each slot by the documented fs-uuid primitive.
        self.assertIn(f"search --no-floppy --fs-uuid --set=root {_UUID_A_FS}", text)
        self.assertIn(f"search --no-floppy --fs-uuid --set=root {_UUID_B_FS}", text)
        self.assertNotIn("--part-uuid", text)
        self.assertIn(f"password_pbkdf2 {GRUB_USER} {_PASSWORD_HASH}", text)
        self.assertIn("${next_entry}", text)
        self.assertIn("${saved_entry}", text)

    def test_release_quiet_precedes_loglevel_and_brands_the_menu(self) -> None:
        text = _config()
        # Kernel parameters are applied in order; ``quiet`` sets loglevel 4,
        # so it must precede the explicit loglevel=0.
        for line in text.splitlines():
            if line.strip().startswith("linux "):
                arguments = line.split()
                self.assertLess(
                    arguments.index("quiet"), arguments.index("loglevel=0")
                )
        self.assertIn("insmod gfxterm", text)
        self.assertIn("set theme=$prefix/greia-theme.txt", text)
        self.assertIn("set gfxpayload=keep", text)
        validate_grub_ab_text(text)

    def test_generation_is_deterministic(self) -> None:
        self.assertEqual(_config(), _config())

    def test_record_render_matches_artifact_render(self) -> None:
        artifact_a, artifact_b = _artifacts()
        record = InstalledLayoutRecord.from_dict(_record_dict())
        from_record = render_grub_ab_config_from_record(
            record=record, password_hash=_PASSWORD_HASH,
        )
        from_artifacts = render_grub_ab_config(
            artifact_a=artifact_a, artifact_b=artifact_b,
            password_hash=_PASSWORD_HASH,
        )
        self.assertEqual(from_record, from_artifacts)
        validate_grub_ab_text(
            from_record, artifact_a=artifact_a, artifact_b=artifact_b,
        )
        render_params = list(
            inspect.signature(render_grub_ab_config_from_record).parameters
        )
        self.assertEqual(render_params, ["record", "password_hash", "developer", "console_policy"])

    def test_record_render_rejects_single_root_and_foreign_backends(self) -> None:
        single = InstalledLayoutRecord.from_dict(
            _record_dict(
                layout_id="bios-single-ext4",
                boot_backend="none-v1",
                boot_control={"active_slot": None, "kind": "none-v1"},
                accepted_slot=None,
                system_b=None,
                platform_family="legacy-x86",
            )
        )
        with self.assertRaises(GrubAbConfigError):
            render_grub_ab_config_from_record(
                record=single, password_hash=_PASSWORD_HASH,
            )
        with self.assertRaises(GrubAbConfigError):
            render_grub_ab_config_from_record(
                record="modern-gpt-ab-v1",  # type: ignore[arg-type]
                password_hash=_PASSWORD_HASH,
            )

    def test_developer_mode_keeps_boot_observable(self) -> None:
        release = _config()
        developer = _config(developer=True)
        self.assertIn("console=tty1", release)
        self.assertNotIn("console=null", release)
        self.assertIn("console=tty1", developer)
        self.assertNotIn("console=null", developer)
        validate_grub_ab_text(release)
        validate_grub_ab_text(developer, developer=True)
        with self.assertRaises((GrubAbConfigError, GrubContractError)):
            validate_grub_ab_text(release, developer=True)
        with self.assertRaises((GrubAbConfigError, GrubContractError)):
            validate_grub_ab_text(developer)

    def test_quiet_developer_policy_is_decoupled_from_ssh(self) -> None:
        # The developer RC keeps SSH (developer=True) but boots quietly.
        artifact_a, artifact_b = _artifacts()
        quiet_dev = render_grub_ab_config(
            artifact_a=artifact_a, artifact_b=artifact_b,
            password_hash=_PASSWORD_HASH, developer=True, console_policy="quiet",
        )
        self.assertEqual(quiet_dev, _config())
        validate_grub_ab_text(quiet_dev, developer=True, console_policy="quiet")
        with self.assertRaises((GrubAbConfigError, GrubContractError)):
            validate_grub_ab_text(quiet_dev, developer=True)
        with self.assertRaises(GrubAbConfigError):
            render_grub_ab_config(
                artifact_a=artifact_a, artifact_b=artifact_b,
                password_hash=_PASSWORD_HASH, developer=False,
                console_policy="diagnostic",
            )

    def test_rejects_mismatched_or_foreign_artifact_sets(self) -> None:
        artifact_a, artifact_b = _artifacts()
        with self.assertRaises(GrubAbConfigError):
            render_grub_ab_config(
                artifact_a=artifact_b, artifact_b=artifact_a,
                password_hash=_PASSWORD_HASH,
            )
        other_record = InstalledLayoutRecord.from_dict(
            _record_dict(layout_id="legacy-bios-ab-v1")
        )
        foreign = BootArtifactSet.from_finalization(
            receipt=_receipt("B", layout_id="legacy-bios-ab-v1"), record=other_record,
        )
        with self.assertRaises(GrubAbConfigError):
            render_grub_ab_config(
                artifact_a=artifact_a, artifact_b=foreign,
                password_hash=_PASSWORD_HASH,
            )
        with self.assertRaises(GrubAbConfigError):
            render_grub_ab_config(
                artifact_a="A", artifact_b=artifact_b,  # type: ignore[arg-type]
                password_hash=_PASSWORD_HASH,
            )

    def test_rejects_bad_hashes_and_modes(self) -> None:
        artifact_a, artifact_b = _artifacts()
        for bad_hash in ("", "plaintext", "md5.hash.value", "grub.pbkdf2.bad\nline"):
            with self.assertRaises(GrubAbConfigError, msg=bad_hash):
                render_grub_ab_config(
                    artifact_a=artifact_a, artifact_b=artifact_b,
                    password_hash=bad_hash,
                )
        with self.assertRaises(GrubAbConfigError):
            render_grub_ab_config(
                artifact_a=artifact_a, artifact_b=artifact_b,
                password_hash=_PASSWORD_HASH, developer="yes",  # type: ignore[arg-type]
            )


class ConfigValidatorTests(unittest.TestCase):
    def test_accepts_generated_release_and_developer_configs(self) -> None:
        entries = validate_grub_ab_text(_config())
        self.assertEqual(len(entries), 2)
        self.assertEqual(
            {entry.kernel_path for entry in entries}, {GRUB_KERNEL_PATH}
        )
        developer_entries = validate_grub_ab_text(_config(developer=True), developer=True)
        self.assertEqual(len(developer_entries), 2)

    def test_binds_entry_roots_to_layout_identities(self) -> None:
        artifact_a, artifact_b = _artifacts()
        validate_grub_ab_text(_config(), artifact_a=artifact_a, artifact_b=artifact_b)
        swapped = _config().replace(_UUID_A, "0" * 36).replace(_UUID_B, _UUID_A)
        with self.assertRaises(GrubAbConfigError):
            validate_grub_ab_text(swapped, artifact_a=artifact_a, artifact_b=artifact_b)

    def test_rejects_single_entry_legacy_config(self) -> None:
        single = (
            f'set superusers="{GRUB_USER}"\nexport superusers\n'
            f"password_pbkdf2 {GRUB_USER} {_PASSWORD_HASH}\n"
            "menuentry 'Greia OS' --unrestricted --id greia-os {\n"
            f"  search --no-floppy --fs-uuid --set=root {_UUID_A_FS}\n"
            f"  linux {GRUB_KERNEL_PATH} root=PARTUUID={_UUID_A} ro quiet\n"
            f"  initrd {GRUB_INITRAMFS_PATH}\n}}\n"
        )
        with self.assertRaises(GrubAbConfigError):
            validate_grub_ab_text(single)

    def test_rejects_wrong_ids_missing_auth_and_submenus(self) -> None:
        good = _config()
        renamed = good.replace("--id greia-b", "--id greia-c")
        with self.assertRaises(GrubAbConfigError):
            validate_grub_ab_text(renamed)
        locked = good.replace("--unrestricted", "")
        with self.assertRaises(GrubAbConfigError):
            validate_grub_ab_text(locked)
        no_auth = good.replace(f'set superusers="{GRUB_USER}"\n', "")
        with self.assertRaises(GrubAbConfigError):
            validate_grub_ab_text(no_auth)
        submenu = good.replace("menuentry", "submenu", 1)
        with self.assertRaises(GrubAbConfigError):
            validate_grub_ab_text(submenu)
        recovery = good.replace("Greia Slot B", "Recovery mode")
        with self.assertRaises(GrubAbConfigError):
            validate_grub_ab_text(recovery)

    def test_rejects_discovery_and_foreign_root_surface(self) -> None:
        good = _config()
        for injected in (
            "os-prober", "configfile /boot/other.cfg", "chainloader +1",
            "root=/dev/sda2", "root=UUID=12345678-1234-5678-9abc-def012345678",
        ):
            with self.subTest(injected=injected):
                poisoned = good.replace(
                    f"initrd {GRUB_INITRAMFS_PATH}",
                    f"initrd {GRUB_INITRAMFS_PATH} #{injected}",
                    1,
                )
                if injected.startswith("root="):
                    poisoned = good.replace(
                        f"root=PARTUUID={_UUID_B}",
                        f"root=PARTUUID={_UUID_B} {injected}",
                        1,
                    )
                elif injected in ("os-prober", "configfile /boot/other.cfg", "chainloader +1"):
                    poisoned = good + f"\n# {injected}\n"
                with self.assertRaises(GrubAbConfigError):
                    validate_grub_ab_text(poisoned)

    def test_rejects_wrong_adapter_paths_and_cross_root_search(self) -> None:
        good = _config()
        wrong_kernel = good.replace(GRUB_KERNEL_PATH, "/vmlinuz")
        with self.assertRaises(GrubAbConfigError):
            validate_grub_ab_text(wrong_kernel)
        wrong_initrd = good.replace(GRUB_INITRAMFS_PATH, "/initrd.img")
        with self.assertRaises(GrubAbConfigError):
            validate_grub_ab_text(wrong_initrd)
        cross_root = good.replace(
            f"search --no-floppy --fs-uuid --set=root {_UUID_B_FS}",
            f"search --no-floppy --fs-uuid --set=root {_UUID_A_FS}",
        )
        with self.assertRaises(GrubAbConfigError):
            validate_grub_ab_text(cross_root)

    def test_rejects_unproven_partuuid_search_primitive(self) -> None:
        good = _config()
        regressed = good.replace(
            "--fs-uuid", "--part-uuid",
        )
        with self.assertRaises(GrubAbConfigError):
            validate_grub_ab_text(regressed)

    def test_rejects_parent_boot_entry_injection(self) -> None:
        good = _config()
        injected = good + (
            "menuentry 'Parent Game' --unrestricted --id parent-game {\n"
            f"  search --no-floppy --fs-uuid --set=root {_UUID_A_FS}\n"
            f"  linux {GRUB_KERNEL_PATH} root=PARTUUID={_UUID_A} ro quiet\n"
            f"  initrd {GRUB_INITRAMFS_PATH}\n}}\n"
        )
        with self.assertRaises(GrubAbConfigError):
            validate_grub_ab_text(injected)


class MbrSlotBindingTests(unittest.TestCase):
    """T1-GRUB/T1-IDENT binding: MBR PARTUUID kernel roots + fs-uuid locators."""

    _SIG = "1a2b3c4d"
    _MBR_A = "1a2b3c4d-01"
    _MBR_B = "1a2b3c4d-02"
    _MBR_P = "1a2b3c4d-03"

    def _mbr_record_dict(self) -> dict[str, object]:
        return _record_dict(
            layout_id="legacy-bios-ab-v1",
            platform_family="legacy-x86",
            system_a={
                "scheme": "MBR_PARTUUID",
                "partuuid": self._MBR_A,
                "filesystem_uuid": _UUID_A_FS,
            },
            system_b={
                "scheme": "MBR_PARTUUID",
                "partuuid": self._MBR_B,
                "filesystem_uuid": _UUID_B_FS,
            },
            persist={
                "scheme": "MBR_PARTUUID",
                "partuuid": self._MBR_P,
                "filesystem_uuid": _UUID_P_FS,
            },
        )

    def test_mbr_record_renders_fs_uuid_locator_and_partuuid_root(self) -> None:
        record = InstalledLayoutRecord.from_dict(self._mbr_record_dict())
        text = render_grub_ab_config_from_record(
            record=record, password_hash=_PASSWORD_HASH,
        )
        self.assertIn(f"search --no-floppy --fs-uuid --set=root {_UUID_A_FS}", text)
        self.assertIn(f"search --no-floppy --fs-uuid --set=root {_UUID_B_FS}", text)
        self.assertIn(f"root=PARTUUID={self._MBR_A}", text)
        self.assertIn(f"root=PARTUUID={self._MBR_B}", text)
        self.assertNotIn("--part-uuid", text)
        validate_grub_ab_text(text, record=record)
        artifact_a = BootArtifactSet.from_finalization(
            receipt=_receipt("A", layout_id="legacy-bios-ab-v1"), record=record,
        )
        artifact_b = BootArtifactSet.from_finalization(
            receipt=_receipt("B", layout_id="legacy-bios-ab-v1"), record=record,
        )
        self.assertEqual(artifact_a.root_partuuid, self._MBR_A)
        from_artifacts = render_grub_ab_config(
            artifact_a=artifact_a, artifact_b=artifact_b,
            password_hash=_PASSWORD_HASH,
        )
        self.assertEqual(from_artifacts, text)
        validate_grub_ab_text(
            text, artifact_a=artifact_a, artifact_b=artifact_b, record=record,
        )

    def test_corrupted_slot_binding_fails_closed(self) -> None:
        """Positive control for slot binding: any cross-slot pairing is RED."""
        record = InstalledLayoutRecord.from_dict(self._mbr_record_dict())
        good = render_grub_ab_config_from_record(
            record=record, password_hash=_PASSWORD_HASH,
        )
        artifact_a = BootArtifactSet.from_finalization(
            receipt=_receipt("A", layout_id="legacy-bios-ab-v1"), record=record,
        )
        artifact_b = BootArtifactSet.from_finalization(
            receipt=_receipt("B", layout_id="legacy-bios-ab-v1"), record=record,
        )
        # Corruptions: locator from the other slot, root from the other
        # slot, and a foreign root. Each must fail against the record.
        swapped_locator = good.replace(_UUID_A_FS, _UUID_B_FS)
        with self.assertRaises(GrubAbConfigError, msg="swapped-locator"):
            validate_grub_ab_text(
                swapped_locator,
                artifact_a=artifact_a, artifact_b=artifact_b, record=record,
            )
        swapped_root = good.replace(self._MBR_A, self._MBR_B)
        with self.assertRaises(GrubAbConfigError, msg="swapped-root"):
            validate_grub_ab_text(
                swapped_root,
                artifact_a=artifact_a, artifact_b=artifact_b, record=record,
            )
        foreign = good.replace(self._MBR_B, _UUID_B, 1)
        with self.assertRaises(GrubAbConfigError, msg="foreign-root"):
            validate_grub_ab_text(
                foreign, artifact_a=artifact_a, artifact_b=artifact_b, record=record,
            )
        # Cross-pair: entry A keeps its locator but boots slot B's root.
        cross_pair = good.replace(
            f"root=PARTUUID={self._MBR_A}", f"root=PARTUUID={self._MBR_B}", 1,
        )
        with self.assertRaises(GrubAbConfigError, msg="cross-pair"):
            validate_grub_ab_text(
                cross_pair, artifact_a=artifact_a, artifact_b=artifact_b, record=record,
            )

    def test_mbr_normalization_accepts_unnpadded_partition_number(self) -> None:
        record = InstalledLayoutRecord.from_dict(
            _record_dict(
                layout_id="legacy-bios-ab-v1",
                platform_family="legacy-x86",
                system_a={
                    "scheme": "MBR_PARTUUID",
                    "partuuid": f"{self._SIG}-1",
                    "filesystem_uuid": _UUID_A_FS,
                },
                system_b={
                    "scheme": "MBR_PARTUUID",
                    "partuuid": f"{self._SIG}-2",
                    "filesystem_uuid": _UUID_B_FS,
                },
                persist={
                    "scheme": "MBR_PARTUUID",
                    "partuuid": f"{self._SIG}-3",
                    "filesystem_uuid": _UUID_P_FS,
                },
            )
        )
        text = render_grub_ab_config_from_record(
            record=record, password_hash=_PASSWORD_HASH,
        )
        self.assertIn(f"root=PARTUUID={self._MBR_A}", text)
        validate_grub_ab_text(text, record=record)


class NoParentAuthorityTests(unittest.TestCase):
    def test_backend_takes_semantic_slots_only(self) -> None:
        arm_params = list(inspect.signature(GrubEnvBackend.arm_one_shot).parameters)
        self.assertEqual(arm_params, ["self", "candidate"])
        commit_params = list(
            inspect.signature(GrubEnvBackend.commit_accepted).parameters
        )
        self.assertEqual(commit_params, ["self", "slot"])
        render_params = list(inspect.signature(render_grub_ab_config).parameters)
        self.assertEqual(
            render_params,
            ["artifact_a", "artifact_b", "password_hash", "developer", "console_policy"],
        )
        with tempfile.TemporaryDirectory() as raw:
            backend = GrubEnvBackend.initialize(Path(raw) / "env", default_slot="A")
            for bad in ("C", "", "/dev/sda1", "greia-a", "BOOT_B", "../x", "a"):
                with self.assertRaises(BootTransactionError, msg=f"arm/{bad}"):
                    backend.arm_one_shot(bad)
                with self.assertRaises(BootTransactionError, msg=f"commit/{bad}"):
                    backend.commit_accepted(bad)
                with self.assertRaises(BootTransactionError, msg=f"reconcile/{bad}"):
                    backend.reconcile(bad)

    def test_module_has_no_privileged_or_manager_surface(self) -> None:
        source = Path(grub_ab_module.__file__).read_text(encoding="utf-8")
        for forbidden in (
            "import subprocess", "os.system", "shell=True", "shell=",
            "root=/dev", "/dev/sd", "/dev/mmc", "'/dev",
            "class .*Manager", "class .*Daemon", "class .*Parser",
        ):
            self.assertIsNone(
                re.search(forbidden, source), msg=f"forbidden surface: {forbidden}"
            )
        # The only bare `/dev/` occurrence is the validator's own
        # forbidden-token literal that rejects device-path boot targets.
        bare = [line for line in source.splitlines() if "/dev/" in line]
        self.assertEqual(len(bare), 1)
        self.assertIn('"os-prober"', bare[0])

    def test_backend_speaks_the_single_coordinator_interface(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            backend = GrubEnvBackend.initialize(Path(raw) / "env", default_slot="A")
            self.assertTrue(coordinator_accepts_backend(backend))
            protocol_methods = {
                name
                for name, member in inspect.getmembers(BootTransactionBackend)
                if callable(member) and not name.startswith("_")
            }
            for name in protocol_methods:
                self.assertTrue(
                    callable(getattr(backend, name, None)),
                    msg=f"GrubEnvBackend lacks {name}",
                )


class GrubEnvBackendTests(unittest.TestCase):
    def test_success_one_shot_and_commit(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            backend = GrubEnvBackend.initialize(root / "env", default_slot="A")
            state = backend.inspect()
            self.assertIsInstance(state, BootBackendState)
            self.assertEqual(state.default_slot, "A")
            self.assertIsNone(state.one_shot_slot)
            armed = backend.arm_one_shot("B")
            self.assertEqual(armed.one_shot_slot, "B")
            self.assertEqual(armed.default_slot, "A")
            self.assertTrue(backend.verify_rollback_ready().ready is False)
            self.assertEqual(backend.simulate_reboot(), "B")
            rebooted = GrubEnvBackend.attach(root / "env")
            self.assertEqual(rebooted.observe_booted_slot(), "B")
            committed = rebooted.commit_accepted("B")
            self.assertEqual(committed.default_slot, "B")
            self.assertIsNone(committed.one_shot_slot)
            self.assertTrue(rebooted.verify_rollback_ready().ready)

    def test_one_shot_consumption_falls_back_to_default(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            backend = GrubEnvBackend.initialize(root / "env", default_slot="A")
            backend.arm_one_shot("B")
            self.assertEqual(backend.simulate_reboot(), "B")
            # Unhealthy candidate is never committed: next boot returns to A.
            self.assertEqual(backend.simulate_reboot(), "A")
            self.assertEqual(backend.inspect().default_slot, "A")

    def test_arm_and_commit_guards(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            backend = GrubEnvBackend.initialize(Path(raw) / "env", default_slot="A")
            with self.assertRaises(BootTransactionError):
                backend.arm_one_shot("A")
            with self.assertRaises(BootTransactionError):
                backend.observe_booted_slot()
            with self.assertRaises(BootTransactionError):
                backend.commit_accepted("B")
            backend.arm_one_shot("B")
            with self.assertRaises(BootTransactionError):
                backend.arm_one_shot("B")
            readiness = backend.verify_rollback_ready()
            self.assertFalse(readiness.ready)

    def test_grubenv_block_shape_is_stable(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            backend = GrubEnvBackend.initialize(root / "env", default_slot="A")
            env_path = root / "env" / GRUBENV_FILE_NAME
            raw_bytes = env_path.read_bytes()
            self.assertEqual(len(raw_bytes), GRUBENV_SIZE)
            self.assertTrue(raw_bytes.startswith((GRUBENV_HEADER + "\n").encode()))
            self.assertIn(b"saved_entry=greia-a\n", raw_bytes)
            backend.arm_one_shot("B")
            self.assertIn(b"next_entry=greia-b\n", env_path.read_bytes())
            self.assertEqual(len(env_path.read_bytes()), GRUBENV_SIZE)

    def test_corrupt_environment_fails_closed(self) -> None:
        def _block(body: bytes) -> bytes:
            return body.ljust(GRUBENV_SIZE, b"#")

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            backend = GrubEnvBackend.initialize(root / "env", default_slot="A")
            env_path = root / "env" / GRUBENV_FILE_NAME
            corrupt_vectors = (
                b"{corrupt",
                _block(b"saved_entry=greia-a\n"),
                _block(b"# GRUB Environment Block\nsaved_entry=greia-c\n"),
                _block(
                    b"# GRUB Environment Block\nsaved_entry=greia-a\n"
                    b"saved_entry=greia-b\n"
                ),
                _block(
                    b"# GRUB Environment Block\nsaved_entry=greia-a\n"
                    b"next_entry=greia-a\n"
                ),
                _block(b"# GRUB Environment Block\nnext_entry=greia-b\n"),
            )
            for corrupt in corrupt_vectors:
                env_path.write_bytes(corrupt)
                with self.assertRaises(BootTransactionError, msg=repr(corrupt[:40])):
                    backend.inspect()
            env_path.unlink()
            with self.assertRaises(BootTransactionError):
                backend.inspect()

    def test_entry_names_are_adapter_owned(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            backend = GrubEnvBackend.initialize(Path(raw) / "env", default_slot="A")
            self.assertEqual(backend.entry_name("A"), "greia-a")
            self.assertEqual(backend.entry_name("B"), "greia-b")
            with self.assertRaises(BootTransactionError):
                backend.entry_name("greia-a")


class FailedHealthLeavesDefaultTests(unittest.TestCase):
    def test_failed_candidate_keeps_accepted_default(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            backend = GrubEnvBackend.initialize(root / "env", default_slot="A")
            accepted, candidate = _artifacts()
            coordinator = BootTransactionCoordinator.begin_update(
                journal_dir=root / "journal", backend=backend,
                candidate_artifacts=candidate, accepted_artifacts=accepted,
                release_id="greia-0.15.0",
            )
            coordinator.arm()
            # Candidate kernel fails: firmware boots the accepted default.
            backend.reconcile("A")
            observed, _ = coordinator.observe_boot()
            self.assertEqual(observed, "A")
            self.assertEqual(coordinator.journal.state, BootTransactionState.ROLLED_BACK)
            with self.assertRaises(BootTransactionError):
                coordinator.commit()
            self.assertEqual(backend.inspect().default_slot, "A")

    def test_missing_health_leaves_default_after_crash_reconcile(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            backend = GrubEnvBackend.initialize(root / "env", default_slot="A")
            accepted, candidate = _artifacts()
            coordinator = BootTransactionCoordinator.begin_update(
                journal_dir=root / "journal", backend=backend,
                candidate_artifacts=candidate, accepted_artifacts=accepted,
                release_id="greia-0.15.0",
            )
            coordinator.arm()
            self.assertEqual(backend.simulate_reboot(), "B")
            # Health never reports; the machine reboots back onto the default.
            self.assertEqual(backend.simulate_reboot(), "A")
            rebooted = GrubEnvBackend.attach(root / "env")
            resumed = BootTransactionCoordinator.resume(
                journal_dir=root / "journal", backend=rebooted,
                candidate_artifacts=candidate, accepted_artifacts=accepted,
            )
            observed, _ = resumed.observe_boot()
            self.assertEqual(observed, "A")
            self.assertEqual(resumed.journal.state, BootTransactionState.ROLLED_BACK)
            self.assertEqual(rebooted.inspect().default_slot, "A")

    def test_health_commit_persists_candidate_only_through_verified_path(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            backend = GrubEnvBackend.initialize(root / "env", default_slot="A")
            accepted, candidate = _artifacts()
            coordinator = BootTransactionCoordinator.begin_update(
                journal_dir=root / "journal", backend=backend,
                candidate_artifacts=candidate, accepted_artifacts=accepted,
                release_id="greia-0.15.0",
            )
            coordinator.arm()
            self.assertEqual(backend.simulate_reboot(), "B")
            rebooted = GrubEnvBackend.attach(root / "env")
            resumed = BootTransactionCoordinator.resume(
                journal_dir=root / "journal", backend=rebooted,
                candidate_artifacts=candidate, accepted_artifacts=accepted,
            )
            observed, _ = resumed.observe_boot()
            self.assertEqual(observed, "B")
            resumed.commit()
            self.assertEqual(resumed.journal.state, BootTransactionState.ACCEPTED)
            self.assertEqual(rebooted.inspect().default_slot, "B")
            # The committed journal is terminal: a second health commit
            # without a new observed candidate boot is refused, and the old
            # slot cannot be re-committed without booting it.
            with self.assertRaises(BootTransactionError):
                resumed.commit()
            with self.assertRaises(BootTransactionError):
                rebooted.commit_accepted("A")


class OverlayContractTests(unittest.TestCase):
    def test_installed_defaults_disable_cross_root_discovery(self) -> None:
        installed_grub = (
            Path(__file__).resolve().parents[1]
            / "build" / "overlay" / "etc" / "default" / "grub.d"
            / "10-greia-quiet.cfg"
        ).read_text(encoding="utf-8")
        self.assertIn("GRUB_DISABLE_OS_PROBER=true", installed_grub)


if __name__ == "__main__":
    unittest.main()
