"""X8-QEMU-HARNESS source-scope contract: disposable SeaBIOS procedure + runner.

No QEMU, loop, mount, or valued-device contact here: every test runs on
disposable tmpdirs through the shared production seams
(``LegacyBiosAbAdapter``, ``SlotWriter``/``SlotFinalizer`` bounds,
``render/validate_grub_ab_*``, the real ``GrubEnvBackend`` grubenv
one-shot path, and the signed ``.greiaupdate`` v2 bundle path). Live
SeaBIOS execution stays RED/deferred per the source-first amendment.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from greia_platform.boot_transaction import BootTransactionError
from greia_platform.grub_ab import (
    GRUBENV_FILE_NAME,
    GrubEnvBackend,
)
from greia_platform.slot_writer import SLOT_WRITE_CHUNK_BYTES
from greia_platform.system_updates import (
    build_update_bundle,
    load_installed_layout_record,
)
from tools.x8_qemu.runner import (
    BOOT_BACKEND_ID,
    LAYOUT_ADAPTER_ID,
    PROFILE_ID,
    PROFILE_PERSIST_MINIMUM_BYTES,
    PROFILE_SLOT_BYTES,
    RUN_SEQUENCE,
    HarnessConfig,
    X8QemuError,
    X8QemuHarness,
    adapter_roles,
    footprint_report,
    initialize_guest_boot_state,
    layout_plan_for_device,
    observe_guest_boot_state,
    procedure_spec,
    release_identity,
    render_guest_grub_config,
    staging_memory_report,
    validate_guest_grub_config,
)

_UUID_A = "11111111-2222-3333-4444-555555555555"
_UUID_A_FS = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
_UUID_B = "22222222-3333-4444-5555-666666666666"
_UUID_B_FS = "bbbbbbbb-cccc-dddd-eeee-ffffffffffff"
_UUID_P = "33333333-4444-5555-6666-777777777777"
_UUID_P_FS = "cccccccc-dddd-eeee-ffff-000000000000"
_INSTALL_SHA = "ab" * 32
_PASSWORD_HASH = "grub.pbkdf2.sha512.10000.ABCDEF0123456789"


def _record_dict(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "accepted_release_id": "greia-x8qemu-0.20.0",
        "accepted_slot": "A",
        "boot_backend": BOOT_BACKEND_ID,
        "boot_control": {"active_slot": "A", "kind": "grub-env-v1"},
        "install_profile": PROFILE_ID,
        "install_target_sha256": _INSTALL_SHA,
        "installed_at_unix": 1757000000,
        "layout_id": LAYOUT_ADAPTER_ID,
        "persist": {"filesystem_uuid": _UUID_P_FS, "partuuid": _UUID_P},
        "platform_family": "legacy-x86",
        "schema_version": 1,
        "slot_bytes": PROFILE_SLOT_BYTES,
        "system_a": {"filesystem_uuid": _UUID_A_FS, "partuuid": _UUID_A},
        "system_b": {"filesystem_uuid": _UUID_B_FS, "partuuid": _UUID_B},
    }
    base.update(overrides)
    return base


def _write_record(root: Path, **overrides: object) -> Path:
    path = root / "installed-layout.json"
    path.write_bytes(
        (json.dumps(_record_dict(**overrides), sort_keys=True) + "\n").encode()
    )
    return path


def _load_record(path: Path):
    record = load_installed_layout_record(path)
    assert record is not None, "layout record must load authoritatively"
    return record


def _payload(size: int, tag: bytes) -> bytes:
    body = bytes((index * 31 + 7) % 256 for index in range(size))
    raw = tag + body[len(tag):]
    fixed = bytearray(raw)
    if fixed[510:512] == b"\x55\xaa":
        fixed[510:512] = b"\x00\x00"
    if fixed[512:520] == b"EFI PART":
        fixed[512:520] = b"\x00" * 8
    return bytes(fixed)


class ProcedureSpecTests(unittest.TestCase):
    def test_declares_exact_layout_profile_release_and_prereqs(self) -> None:
        spec = procedure_spec()
        self.assertEqual(spec["layout_adapter"], "legacy-bios-ab-v1")
        self.assertEqual(spec["boot_backend"], "grub-ab-v1")
        self.assertEqual(spec["reference_profile"], "legacy-x86-i686")
        sizing = spec["profile_sizing"]
        assert isinstance(sizing, dict)
        self.assertEqual(sizing["system_slot_bytes"], 1073741824)
        self.assertIn("800", json.dumps(spec))
        for prerequisite in (
            "Linux x86_64",
            "qemu-system-x86_64",
            "SeaBIOS",
            "loopback",
        ):
            self.assertIn(prerequisite, json.dumps(spec))
        self.assertIn("no profile-bounds conformance", str(spec["profile_conformance_note"]))
        self.assertIs(spec["valued_device_contact"], False)
        self.assertEqual(list(spec["run_sequence"]), list(RUN_SEQUENCE))
        for required in (
            "cold-boot-A",
            "arm-B-one-shot",
            "boot-B-commit",
            "fallback-A",
            "persist-verify-ABA",
        ):
            self.assertIn(required, list(spec["run_sequence"]))

    def test_plan_is_non_mutating_and_disposable_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            harness = X8QemuHarness(HarnessConfig(output_dir=Path(tmp) / "out"))
            plan = harness.plan()
            self.assertIs(plan["disposable_image_only"], True)
            self.assertIs(plan["source_tree_mutated"], False)
            self.assertIn("SeaBIOS", str(plan["firmware"]))
            self.assertEqual(plan["procedure"]["layout_adapter"], LAYOUT_ADAPTER_ID)


class QemuArgvTests(unittest.TestCase):
    def _harness(self, root: Path) -> X8QemuHarness:
        return X8QemuHarness(HarnessConfig(output_dir=root / "out"))

    def test_seabios_legacy_pc_and_preserved_guest_disk(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            harness = self._harness(Path(tmp))
            image = Path(tmp) / "out" / "test.img"
            argv = harness.qemu_argv(image)
            self.assertEqual(argv[0], "qemu-system-x86_64")
            self.assertEqual(argv[argv.index("-machine") + 1], "pc,accel=tcg")
            self.assertEqual(argv[argv.index("-display") + 1], "none")
            self.assertEqual(argv[argv.index("-nic") + 1], "none")
            self.assertIn("-no-reboot", argv)
            self.assertEqual(argv[argv.index("-boot") + 1], "order=c,strict=on")
            drive = argv[argv.index("-drive") + 1]
            self.assertIn(f"file={image}", drive)
            self.assertIn("format=raw", drive)
            self.assertIn("if=ide", drive)
            self.assertNotIn("snapshot=on", drive)
            self.assertNotIn("-snapshot", argv)

    def test_explicit_seabios_firmware_path_is_honored(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            harness = X8QemuHarness(
                HarnessConfig(output_dir=root / "out", seabios_path=Path("/fw/bios.bin"))
            )
            argv = harness.qemu_argv(root / "img.raw")
            self.assertEqual(argv[argv.index("-bios") + 1], "/fw/bios.bin")


class LayoutAndGrubTests(unittest.TestCase):
    def test_layout_plan_uses_executable_legacy_adapter_with_profile_sizing(self) -> None:
        plan = layout_plan_for_device(3072 * 1024 * 1024)
        self.assertEqual(plan.adapter_id, "legacy-bios-ab-v1")
        self.assertEqual(plan.label_type, "msdos")
        self.assertEqual(plan.boot_backend, "grub-ab-v1")
        self.assertEqual(
            [part.role for part in sorted(plan.partitions, key=lambda p: p.number)],
            ["boot-control", "system-a", "system-b", "persist"],
        )
        self.assertEqual(
            plan.by_role("system-a").size_bytes, PROFILE_SLOT_BYTES
        )
        self.assertEqual(plan.by_role("system-b").size_bytes, PROFILE_SLOT_BYTES)
        self.assertIsNone(plan.by_role("persist").size_bytes)
        self.assertEqual(tuple(adapter_roles()), ("boot-control", "system-a", "system-b", "persist"))

    def test_grub_config_round_trip_through_shared_renderer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            record = _load_record(_write_record(Path(tmp)))
            text = render_guest_grub_config(record, password_hash=_PASSWORD_HASH)
            validate_guest_grub_config(text)
            self.assertIn("greia-a", text)
            self.assertIn("greia-b", text)
            self.assertIn(_UUID_A, text)
            self.assertIn(_UUID_B, text)
            self.assertNotIn("/dev/", text)

    def test_negative_single_root_layout_has_no_grub_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = _record_dict()
            del raw["system_b"]
            path = root / "installed-layout.json"
            path.write_bytes((json.dumps(raw, sort_keys=True) + "\n").encode())
            with self.assertRaises(Exception):
                load_installed_layout_record(path)
            with self.assertRaises(Exception):
                render_guest_grub_config(object(), password_hash=_PASSWORD_HASH)


class RealOneShotPathTests(unittest.TestCase):
    """Production-proof: the real grubenv one-shot path, never a test hook."""

    def test_arm_inspect_reconcile_commit_through_real_grubenv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "boot"
            initialize_guest_boot_state(state, default_slot="A")
            observed = observe_guest_boot_state(state)
            self.assertEqual(observed["default_slot"], "A")
            self.assertIsNone(observed["one_shot_slot"])

            backend = GrubEnvBackend.attach(state)
            backend.arm_one_shot("B")
            observed = observe_guest_boot_state(state)
            # Candidate-only: the persistent default is untouched by arming.
            self.assertEqual(observed["default_slot"], "A")
            self.assertEqual(observed["one_shot_slot"], "B")

            backend.reconcile("B")
            observed = observe_guest_boot_state(state)
            self.assertIsNone(observed["one_shot_slot"])
            self.assertEqual(observed["last_booted_slot"], "B")
            self.assertEqual(observed["default_slot"], "A")

            backend.commit_accepted("B")
            observed = observe_guest_boot_state(state)
            self.assertEqual(observed["default_slot"], "B")
            self.assertEqual(observed["last_booted_slot"], "B")

    def test_negative_arm_of_persistent_default_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "boot"
            backend = initialize_guest_boot_state(state, default_slot="A")
            with self.assertRaises(BootTransactionError):
                backend.arm_one_shot("A")
            self.assertIsNone(observe_guest_boot_state(state)["one_shot_slot"])

    def test_positive_control_tampered_one_shot_goes_red_then_green(self) -> None:
        """Break -> RED -> restore -> GREEN on the real one-shot invariant.

        Proves the runner's observation path reads the real grubenv bytes:
        a one-shot aliasing the persistent default (forbidden
        candidate-only violation) must fail inspection, and restoring the
        exact intended state must pass again. A stub returning canned state
        could not go RED here.
        """
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "boot"
            initialize_guest_boot_state(state, default_slot="A")
            GrubEnvBackend.attach(state).arm_one_shot("B")
            env_path = state / GRUBENV_FILE_NAME
            intact = env_path.read_bytes()
            self.assertEqual(len(intact), 1024)

            # BREAK: alias the one-shot to the persistent default.
            env_path.write_bytes(intact.replace(b"next_entry=greia-b", b"next_entry=greia-a"))
            with self.assertRaises(BootTransactionError):
                observe_guest_boot_state(state)

            # RESTORE the exact intended bytes and re-prove GREEN.
            env_path.write_bytes(intact)
            observed = observe_guest_boot_state(state)
            self.assertEqual(observed["default_slot"], "A")
            self.assertEqual(observed["one_shot_slot"], "B")

    def test_positive_control_tampered_grub_cfg_root_goes_red(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            record = _load_record(_write_record(Path(tmp)))
            text = render_guest_grub_config(record, password_hash=_PASSWORD_HASH)
            validate_guest_grub_config(text)
            tampered = text.replace(_UUID_B, _UUID_A)
            with self.assertRaises(Exception):
                validate_guest_grub_config(tampered)


class HarnessBoundaryTests(unittest.TestCase):
    def test_negative_output_inside_source_tree_is_refused(self) -> None:
        from tools.x8_qemu.runner import PROJECT_ROOT

        with self.assertRaises(X8QemuError):
            HarnessConfig(output_dir=PROJECT_ROOT / "build" / "x8-test").validate()
        with self.assertRaises(X8QemuError):
            HarnessConfig(output_dir=Path("relative/out")).validate()

    def test_negative_unknown_run_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            harness = X8QemuHarness(HarnessConfig(output_dir=root / "out"))
            image = harness.image_path
            image.parent.mkdir(parents=True, exist_ok=True)
            image.write_bytes(b"x8-image-bytes")
            state = root / "boot"
            initialize_guest_boot_state(state, default_slot="A")
            with self.assertRaises(X8QemuError):
                harness.collect_run_evidence(
                    run="not-a-run",
                    boot_state_dir=state,
                    bundle_path=None,
                    persist_markers={},
                )

    def test_runner_reuses_shared_libs_and_has_no_parallel_mechanisms(self) -> None:
        from tools.x8_qemu import runner as module

        text = Path(module.__file__).read_text(encoding="utf-8")
        self.assertNotIn("simulate_reboot(", text)
        self.assertNotIn("FakeGrubBackend", text)
        self.assertNotIn("class SlotWriter", text)
        self.assertNotIn("class SlotFinalizer", text)
        self.assertNotIn("def render_grub_ab_config", text)
        self.assertNotIn("def build_update_bundle", text)
        # v3: no key material or signature verification in the harness.
        for banned in (
            "generate_ed25519_keypair",
            "private_key",
            "trusted_key_dir",
            "verify_update_signature",
        ):
            self.assertNotIn(banned, text)
        for required in (
            "from greia_installer.layout import",
            "from greia_platform.grub_ab import",
            "from greia_platform.slot_writer import",
            "from greia_platform.system_updates import",
            "GrubEnvBackend",
            "adapter_for",
        ):
            self.assertIn(required, text)

    def test_require_host_fails_closed_without_capable_host(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            harness = X8QemuHarness(HarnessConfig(output_dir=Path(tmp) / "out"))
            with self.assertRaises(X8QemuError):
                harness.require_host()

    def test_missing_qemu_tool_is_reported_when_root(self) -> None:
        from tools.x8_qemu.runner import CommandRunner

        class _NoTools(CommandRunner):
            def which(self, command: str) -> str | None:
                return None

        with tempfile.TemporaryDirectory() as tmp:
            harness = X8QemuHarness(
                HarnessConfig(output_dir=Path(tmp) / "out"), runner=_NoTools()
            )
            with patch("os.geteuid", return_value=0):
                with self.assertRaises(X8QemuError) as ctx:
                    harness.require_host()
            self.assertIn("missing host tools", str(ctx.exception))


class FootprintTests(unittest.TestCase):
    def test_footprint_compares_bounds_without_conformance_claim(self) -> None:
        report = footprint_report(
            image_bytes=3072 * 1024 * 1024,
            base_bytes=220 * 1024,
            minimum_slot_bytes=220 * 1024,
            support_installed_bytes=0,
        )
        self.assertEqual(report["conformance_claim"], "none: comparison only")
        self.assertIs(report["below_review_mib"], False)
        small = footprint_report(
            image_bytes=100 * 1024 * 1024,
            base_bytes=220 * 1024,
            minimum_slot_bytes=220 * 1024,
            support_installed_bytes=0,
        )
        self.assertIs(small["below_preferred_mib"], True)

    def test_staging_memory_is_bounded_by_one_chunk(self) -> None:
        report = staging_memory_report(payload_size=240 * 1024)
        self.assertEqual(report["chunk_bytes"], SLOT_WRITE_CHUNK_BYTES)
        self.assertEqual(report["peak_staging_bytes_bound"], SLOT_WRITE_CHUNK_BYTES)
        self.assertLessEqual(SLOT_WRITE_CHUNK_BYTES, 240 * 1024)
        with self.assertRaises(X8QemuError):
            staging_memory_report(payload_size=0)


class RunEvidenceTests(unittest.TestCase):
    def _bundle(self, root: Path, name: str, release_id: str) -> Path:
        import zstandard

        work = root / "releases" / name
        work.mkdir(parents=True, exist_ok=True)
        raw = _payload(64 * 1024, f"x8q-{name}:".encode())
        payload = work / "payload.ext4.zst"
        payload.write_bytes(zstandard.ZstdCompressor(level=3).compress(raw))
        hardware = work / "hardware-support.tar.zst"
        hardware.write_bytes(zstandard.ZstdCompressor(level=3).compress(b"x8q-hw" * 64))
        bundle = work / f"{name}.greiaupdate"
        build_update_bundle(
            payload_path=payload,
            hardware_support_path=hardware,
            output_path=bundle,
            version=release_id.split("-", 1)[1],
            release_id=release_id,
            platform_family="legacy-x86",
            architecture="x86-64",
            profile="legacy-x86-i686",
            payload_uncompressed_bytes=len(raw),
            persist_read_schema_min=1,
            persist_read_schema_max=1,
            persist_write_schema=1,
            release_notes=f"X8-QEMU test release {name}.",
        )
        return bundle

    def test_collect_run_evidence_records_hashes_identity_and_backend_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            harness = X8QemuHarness(HarnessConfig(output_dir=root / "out"))
            harness.image_path.parent.mkdir(parents=True, exist_ok=True)
            harness.image_path.write_bytes(b"x8-disposable-image" * 1024)
            expected_image_sha = hashlib.sha256(
                harness.image_path.read_bytes()
            ).hexdigest()

            state = root / "boot"
            backend = initialize_guest_boot_state(state, default_slot="A")
            backend.arm_one_shot("B")
            backend.reconcile("B")

            markers_dir = harness.staging_dir / "persist-markers"
            markers_dir.mkdir(parents=True, exist_ok=True)
            (markers_dir / "profile.json").write_bytes(b'{"schema":1}\n')

            bundle = self._bundle(root, "r21", "greia-x8qemu-0.21.0")
            identity = release_identity(bundle)
            self.assertEqual(identity["release_id"], "greia-x8qemu-0.21.0")
            self.assertIn("payload_sha256", identity)

            evidence = harness.collect_run_evidence(
                run="boot-B-commit",
                boot_state_dir=state,
                bundle_path=bundle,
                persist_markers={"profile.json": hashlib.sha256(b'{"schema":1}\n').hexdigest()},
            )
            self.assertEqual(evidence["run"], "boot-B-commit")
            self.assertEqual(evidence["boot_backend"], "grub-ab-v1")
            backend_state = evidence["boot_backend_state"]
            assert isinstance(backend_state, dict)
            self.assertEqual(backend_state["backend_id"], "grub-ab-v1")
            self.assertEqual(backend_state["default_slot"], "A")
            self.assertEqual(backend_state["last_booted_slot"], "B")
            self.assertEqual(evidence["image_sha256"], expected_image_sha)
            release = evidence["release"]
            assert isinstance(release, dict)
            self.assertEqual(release["release_id"], "greia-x8qemu-0.21.0")
            self.assertEqual(release["bundle_sha256"], identity["bundle_sha256"])

    def test_stage_source_scope_proves_plan_identities_and_grub(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            harness = X8QemuHarness(HarnessConfig(output_dir=root / "out"))
            record_path = _write_record(root)
            manifest = harness.stage_source_scope(
                device_size_bytes=3072 * 1024 * 1024,
                password_hash=_PASSWORD_HASH,
                layout_record_path=record_path,
            )
            self.assertEqual(manifest["adapter"], "legacy-bios-ab-v1")
            roles = [part["role"] for part in manifest["partitions"]]
            self.assertEqual(roles, ["boot-control", "system-a", "system-b", "persist"])
            self.assertEqual(
                manifest["fresh_identities_minted"], ["persist", "system-a", "system-b"]
            )
            self.assertGreater(manifest["grub_cfg_bytes"], 0)


if __name__ == "__main__":
    unittest.main()
