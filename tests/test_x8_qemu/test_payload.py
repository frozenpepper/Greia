"""T7-PAYLOAD minimal-guest-payload contract.

Pins the disposable-image payload through the production seams only: no
stubbed health/launcher, no fabricated slot/journal/GRUB state, no QEMU,
loop, mount, or valued-device contact. Device copy stays fail-closed
behind ``require_device_host``.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.x8_qemu.lifecycle import (
    LifecycleConfig,
    LifecycleContractError,
    LifecycleHarness,
    LifecycleHarnessError,
    assemble_disposable_image,
    assert_lifecycle_transitions,
    fresh_machine_state,
    observe_file_backed_image,
    write_mbr_table_for_plan,
)
from tools.x8_qemu.payload import (
    PayloadError,
    assert_payload_present,
    compose_guest_payload,
    embed_payload_descriptor,
    payload_assembly_cost,
    read_attestation_signal,
    read_payload_descriptor,
    verify_staged_payload,
)
from tools.x8_qemu.runner import layout_plan_for_device

_PASSWORD_HASH = "grub.pbkdf2.sha512.10000.T7PAYLOADABCDEF0123456789"


class PayloadCompositionTests(unittest.TestCase):
    def test_payload_composes_via_production_grub_seams(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            machine = fresh_machine_state(Path(tmp) / "machine")
            manifest = compose_guest_payload(
                layout_record_path=machine["layout"],
                password_hash=_PASSWORD_HASH,
                output_dir=Path(tmp) / "guest-payload",
            )
            # Exact artifacts: validated grub.cfg + 1024-byte grubenv.
            self.assertGreater(manifest.grub_cfg_bytes, 0)
            self.assertEqual(manifest.grubenv_bytes, 1024)
            self.assertEqual(len(manifest.grub_cfg_sha256), 64)
            self.assertEqual(len(manifest.grubenv_sha256), 64)
            # Re-proof through the production seams (hash + validate + attach).
            reproven = verify_staged_payload(Path(tmp) / "guest-payload")
            self.assertEqual(reproven.grub_cfg_sha256, manifest.grub_cfg_sha256)
            self.assertEqual(reproven.grubenv_sha256, manifest.grubenv_sha256)

    def test_image_assembles_with_payload_bound_by_descriptor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest = assemble_disposable_image(Path(tmp) / "out")
            image = Path(manifest["image"])
            self.assertTrue(image.is_file())
            self.assertEqual(manifest["payload_magic"], "GREIAPY1")
            self.assertEqual(manifest["payload_descriptor"], "sector-1:512")
            self.assertFalse(manifest["payload_whole_ram_copy"])
            descriptor = read_payload_descriptor(image)
            self.assertEqual(
                descriptor["grub_cfg_sha256"], manifest["payload_grub_cfg_sha256"]
            )
            self.assertEqual(
                descriptor["grubenv_sha256"], manifest["payload_grubenv_sha256"]
            )
            self.assertEqual(
                descriptor["guest_paths"], manifest["payload_guest_paths"]
            )
            # Staging re-proves against the image-bound hashes.
            reproven = verify_staged_payload(Path(tmp) / "out" / "guest-payload")
            self.assertEqual(
                reproven.grub_cfg_sha256, manifest["payload_grub_cfg_sha256"]
            )
            cost = payload_assembly_cost(Path(tmp) / "out" / "guest-payload")
            self.assertEqual(cost["files_touched"], 3)
            self.assertIs(cost["whole_payload_ram_copy"], False)

    def test_attestation_signal_reads_through_production_seam(self) -> None:
        from greia_platform.grub_ab import GrubEnvBackend

        with tempfile.TemporaryDirectory() as tmp:
            machine = fresh_machine_state(Path(tmp) / "machine")
            compose_guest_payload(
                layout_record_path=machine["layout"],
                password_hash=_PASSWORD_HASH,
                output_dir=Path(tmp) / "guest-payload",
            )
            # Guest boots the armed candidate B: one-shot consumed, last
            # booted observed through the production attach seam.
            backend = GrubEnvBackend.attach(machine["boot_control"])
            backend.arm_one_shot("B")
            backend.reconcile("B")
            signal = read_attestation_signal(
                machine["boot_control"], expected_booted_slot="B"
            )
            self.assertTrue(signal["consumed"])
            self.assertEqual(signal["last_booted_slot"], "B")
            self.assertEqual(
                signal["seam"], "GrubEnvBackend.attach(mountpoint).inspect()"
            )


class PayloadRedControlTests(unittest.TestCase):
    """Each required RED condition fails for the right reason."""

    def test_missing_payload_fails_boot_gate_break_restore_green(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest = assemble_disposable_image(Path(tmp) / "out")
            image = Path(manifest["image"])
            # GREEN: payload present.
            assert_payload_present(image)
            # BREAK: wipe the descriptor sector (512 bounded bytes).
            with open(image, "r+b") as handle:
                handle.seek(512)
                handle.write(b"\x00" * 512)
            # RED: the boot gate fails closed, never false green.
            with self.assertRaises(PayloadError):
                assert_payload_present(image)
            with self.assertRaises(PayloadError):
                read_payload_descriptor(image)
            # RESTORE the exact payload binding and re-prove GREEN.
            payload_dir = Path(tmp) / "out" / "guest-payload"
            reproven = verify_staged_payload(payload_dir)
            embed_payload_descriptor(image, reproven)
            assert_payload_present(image)

    def test_corrupted_disk_binding_fails_observation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest = assemble_disposable_image(Path(tmp) / "out")
            image = Path(manifest["image"])
            plan = layout_plan_for_device(3072 * 1024 * 1024)
            # GREEN control: intact binding observes (record==topology).
            result = observe_file_backed_image(image, plan=plan)
            self.assertTrue(result.record_matches_topology)
            # BREAK the MBR disk signature (first production divergence).
            with open(image, "r+b") as handle:
                handle.seek(440)
                handle.write(b"\xde\xad\xbe\xef")
            # RED: binding refuses the corrupted disk.
            with self.assertRaises(LifecycleHarnessError):
                observe_file_backed_image(image, plan=plan)

    def test_same_disk_reboot_without_transitions_fails_attestation(self) -> None:
        from greia_platform.grub_ab import GrubEnvBackend

        with tempfile.TemporaryDirectory() as tmp:
            machine = fresh_machine_state(Path(tmp) / "machine")
            backend = GrubEnvBackend.attach(machine["boot_control"])
            # First boot consumes the armed one-shot for B: attests GREEN.
            backend.arm_one_shot("B")
            backend.reconcile("B")
            signal = read_attestation_signal(
                machine["boot_control"], expected_booted_slot="B"
            )
            self.assertTrue(signal["consumed"])
            # Same disk reboots with no new transition: firmware boots the
            # persistent default A (no one-shot armed). Claiming B again
            # must RED — no consumption delta exists.
            backend.reconcile("A")
            with self.assertRaises(PayloadError):
                read_attestation_signal(
                    machine["boot_control"], expected_booted_slot="B"
                )
            # The lifecycle contract agrees: movement-free reports are RED.
            no_movement = {
                "steps": [
                    {"step": name, "default_slot": "A"}
                    for name in (
                        "fresh-install-A",
                        "boot-A-accepted",
                        "stage-B-one-shot",
                        "boot-B-commit",
                        "stage-broken-candidate",
                        "boot-broken-candidate",
                        "recovery-boot-B",
                        "reverse-update-B-to-A",
                    )
                ],
                "shipped_update_legs": [
                    "stage-B-one-shot",
                    "boot-B-commit",
                    "reverse-update-B-to-A",
                ],
                "launcher_acceptance_legs": [
                    "boot-A-accepted",
                    "boot-B-commit",
                    "recovery-boot-B",
                    "reverse-update-B-to-A",
                ],
            }
            with self.assertRaises(LifecycleContractError):
                assert_lifecycle_transitions(no_movement)

    def test_armed_but_unconsumed_one_shot_must_not_attest(self) -> None:
        from greia_platform.grub_ab import GrubEnvBackend

        with tempfile.TemporaryDirectory() as tmp:
            machine = fresh_machine_state(Path(tmp) / "machine")
            GrubEnvBackend.attach(machine["boot_control"]).arm_one_shot("B")
            # N2: next_entry still present — no guest consumption happened.
            with self.assertRaises(PayloadError):
                read_attestation_signal(
                    machine["boot_control"], expected_booted_slot="B"
                )

    def test_tampered_grub_cfg_fails_staging_proof(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            machine = fresh_machine_state(Path(tmp) / "machine")
            payload_dir = Path(tmp) / "guest-payload"
            compose_guest_payload(
                layout_record_path=machine["layout"],
                password_hash=_PASSWORD_HASH,
                output_dir=payload_dir,
            )
            cfg = payload_dir / "grub.cfg"
            intact = cfg.read_bytes()
            cfg.write_bytes(intact.replace(b"greia-b", b"greia-a"))
            with self.assertRaises(Exception):
                verify_staged_payload(payload_dir)
            cfg.write_bytes(intact)
            verify_staged_payload(payload_dir)

    def test_device_install_fails_closed_off_capable_host(self) -> None:
        import sys as _sys

        if _sys.platform == "linux":
            self.skipTest("device-install gate is evaluated off Linux")
        with tempfile.TemporaryDirectory() as tmp:
            manifest = assemble_disposable_image(Path(tmp) / "out")
            from tools.x8_qemu.payload import install_payload_to_device

            with self.assertRaises(Exception):
                install_payload_to_device(
                    Path(manifest["image"]), Path(tmp) / "out" / "guest-payload"
                )


class PayloadDeviceCopyRegressionTests(unittest.TestCase):
    """B3-FIX-PAYLOAD pin: device-only grubenv destination cannot regress.

    The verification-2 ``NameError: STAGED_GRUBENV_PATH`` lived behind
    ``require_device_host`` + loop/mount, so the helper-green source
    suite never reached ``payload.py:474``. These two tests close that
    hole source-scope (tmp-only, no root/loop/Acer): a static pin that
    the install path references only defined names, plus a stubbed
    copy-mapping check that ``grub.cfg`` + ``grubenv`` land at the guest
    paths through the production copy + ``GrubEnvBackend`` inspect path.
    Both RED pre-fix (restored ``STAGED_GRUBENV_PATH``) and GREEN
    post-fix.
    """

    def test_install_path_references_only_defined_names(self) -> None:
        import inspect
        import subprocess as _subprocess
        import sys as _sys

        from tools.x8_qemu import payload as module

        text = Path(module.__file__).read_text(encoding="utf-8")
        self.assertNotIn(
            "STAGED_GRUBENV_PATH",
            text,
            "undefined grubenv destination name must not recur",
        )
        installer_source = inspect.getsource(module.install_payload_to_device)
        self.assertIn("STAGED_GRUBENV_NAME", installer_source)
        completed = _subprocess.run(
            [_sys.executable, "-m", "pyflakes", str(Path(module.__file__))],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if "No module named pyflakes" in completed.stderr:
            self.assertTrue(hasattr(module, "STAGED_GRUBENV_NAME"))
        else:
            self.assertEqual(
                completed.returncode,
                0,
                msg=completed.stdout + completed.stderr,
            )

    def test_install_copy_mapping_lands_at_guest_paths_stubbed(self) -> None:
        import shutil as _shutil
        from unittest import mock as _mock

        from tools.x8_qemu import payload as module

        with tempfile.TemporaryDirectory() as tmp:
            machine = fresh_machine_state(Path(tmp) / "machine")
            payload_dir = Path(tmp) / "guest-payload"
            compose_guest_payload(
                layout_record_path=machine["layout"],
                password_hash=_PASSWORD_HASH,
                output_dir=payload_dir,
            )
            image = Path(tmp) / "fake.img"
            image.write_bytes(b"\x00" * (1024 * 1024))

            copies: list[tuple[str, str]] = []
            real_copy2 = _shutil.copy2

            def _recording_copy2(src: object, dst: object, *args: object, **kwargs: object) -> object:
                copies.append((Path(str(src)).name, Path(str(dst)).name))
                return real_copy2(src, dst, *args, **kwargs)  # type: ignore[arg-type]

            with (
                _mock.patch(
                    "tools.x8_qemu.lifecycle.require_device_host", return_value=None
                ),
                _mock.patch.object(
                    module, "_loop_attach", return_value=Path("/dev/fake-loop0")
                ),
                _mock.patch.object(module, "_run", return_value=None),
                _mock.patch("subprocess.run") as fake_run,
                _mock.patch.object(module.shutil, "copy2", side_effect=_recording_copy2),
                _mock.patch.object(module.time, "sleep", return_value=None),
            ):
                fake_run.return_value = _mock.MagicMock(returncode=0)
                result = module.install_payload_to_device(image, payload_dir)

            self.assertTrue(result["installed"])
            self.assertEqual(
                copies,
                [
                    (module.STAGED_GRUB_CFG_NAME, module.STAGED_GRUB_CFG_NAME),
                    (module.STAGED_GRUBENV_NAME, module.STAGED_GRUBENV_NAME),
                ],
            )
            # Destination names equal the guest paths consumed by run_device.
            self.assertEqual(
                module.STAGED_GRUBENV_NAME, module.GUEST_GRUBENV_PATH.lstrip("/")
            )
            self.assertEqual(
                module.STAGED_GRUB_CFG_NAME, module.GUEST_GRUB_CFG_PATH.lstrip("/")
            )
            # The stubbed mountpoint keeps the installed files, proven via
            # the production inspect inside install (default A, no one-shot).
            mountpoint = payload_dir.parent / "payload-mnt"
            installed_env = mountpoint / module.STAGED_GRUBENV_NAME
            self.assertTrue(installed_env.is_file())
            self.assertEqual(installed_env.stat().st_size, 1024)


class PayloadBoundaryTests(unittest.TestCase):
    def test_payload_has_no_parallel_mechanisms(self) -> None:
        from tools.x8_qemu import payload as module

        text = Path(module.__file__).read_text(encoding="utf-8")
        for forbidden in (
            "simulate_reboot(",
            "FakeGrubBackend",
            "class SlotWriter",
            "class GrubEnvBackend",
            "def render_grub_ab_config",
            "def build_update_bundle",
        ):
            self.assertNotIn(forbidden, text)
        for required in (
            "render_grub_ab_config_from_record",
            "validate_grub_ab_text",
            "GrubEnvBackend",
            "require_device_host",
        ):
            self.assertIn(required, text)

    def test_full_lifecycle_still_green_with_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            harness = LifecycleHarness(
                LifecycleConfig(output_dir=Path(tmp) / "out")
            )
            report = harness.run_source_scope()
            self.assertTrue(report["ok"])
            assert_lifecycle_transitions(report)
            _ = write_mbr_table_for_plan


if __name__ == "__main__":
    unittest.main()
