"""G1 — genuine GRUB one-shot consumption wiring (source scope).

Pins the G1 device-flow fix at source scope (no QEMU, loop, mount, GRUB
tooling, or Acer execution):

- prefix-drift falsification: the pinned ``(,msdos1)/`` root prefix
  resolves to the exact root paths the frozen seam inspects;
- genuine-size install + explicit rebind + gap/device-gate green
  through the real helpers (production-proof, not name inspection);
- capable-host ``maybe_install_genuine_grub_core`` wiring with only the
  mkimage binary stubbed (real pad/install/rebind/guard execute);
- fail-closed stub default off a capable host (no consumption claim);
- sensitivity controls: stub armed leg REDs armed-but-unconsumed,
  corrupted gap/descriptor REDs, unclean exit REDs.

Live Acer re-execution belongs to B3-DEVRUN-RERUN, not this scope.
"""

from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest import mock as _mock


def _synthetic_core(sectors: int) -> bytes:
    """Deterministic NON-GRUB core exerciser (never claimed as GRUB)."""
    return bytes((index * 31 + 7) % 256 for index in range(sectors * 512))


class PrefixDriftFalsificationTests(unittest.TestCase):
    """Falsify the prefix/path-drift alternative before wiring claims."""

    def test_root_prefix_binds_boot_and_seam_to_same_paths(self) -> None:
        from tools.x8_qemu import bootchain as bc
        from tools.x8_qemu import payload as pl

        with tempfile.TemporaryDirectory() as tmp:
            argv = bc.grub_mkimage_argv(output=Path(tmp) / "core.img")
        self.assertEqual(argv[argv.index("-p") + 1], "(,msdos1)/")
        # The genuine prefix resolves at the partition ROOT ...
        self.assertTrue(argv[argv.index("-p") + 1].endswith("/"))
        # ... exactly where the frozen seam reads consumption ...
        self.assertEqual(pl.GUEST_GRUB_CFG_PATH, "/grub.cfg")
        self.assertEqual(pl.GUEST_GRUBENV_PATH, "/grubenv")
        # ... and exactly where the install path places the files
        # (single root placement, no mirror copy to drift).
        self.assertEqual(pl.STAGED_GRUB_CFG_NAME, "grub.cfg")
        self.assertEqual(pl.STAGED_GRUBENV_NAME, "grubenv")
        self.assertEqual(
            pl.STAGED_GRUBENV_NAME, pl.GUEST_GRUBENV_PATH.lstrip("/")
        )
        self.assertEqual(
            pl.STAGED_GRUB_CFG_NAME, pl.GUEST_GRUB_CFG_PATH.lstrip("/")
        )
        # The production consumer block is $prefix-relative (byte-verbatim
        # under either prefix) and owns the one-shot clear.
        from greia_platform.grub_ab import render_grub_ab_config_from_record
        from greia_platform.system_updates import load_installed_layout_record
        from tools.x8_qemu.lifecycle import _PASSWORD_HASH, fresh_machine_state

        with tempfile.TemporaryDirectory() as tmp2:
            machine = fresh_machine_state(Path(tmp2) / "machine")
            record = load_installed_layout_record(Path(machine["layout"]))
            assert record is not None
            text = render_grub_ab_config_from_record(
                record=record, password_hash=_PASSWORD_HASH
            )
        self.assertIn("$prefix/grubenv", text)
        self.assertIn("save_env next_entry", text)
        self.assertIn('if [ -n "${next_entry}" ]; then', text)
        # A /boot/grub-suffixed prefix would strand consumption on a
        # mirror copy the seam never reads; the pinned root prefix
        # cannot do that by construction (falsified, not merely kept).


class GenuineWiringTests(unittest.TestCase):
    def test_genuine_size_install_rebind_gap_gate_green_real_helpers(self) -> None:
        """Production-proof: real install + rebind + guards, genuine size."""
        from tools.x8_qemu.bootchain import install_genuine_grub_chain
        from tools.x8_qemu.lifecycle import (
            assemble_disposable_image,
            device_gate_for_image,
        )
        from tools.x8_qemu.payload import (
            rebind_payload_descriptor,
            verify_staged_payload,
        )

        with tempfile.TemporaryDirectory() as tmp:
            manifest = assemble_disposable_image(Path(tmp) / "out")
            image = Path(manifest["image"])
            device_gate_for_image(image)  # stub baseline green
            genuine = _synthetic_core(40)
            proof = install_genuine_grub_chain(image, genuine)
            self.assertEqual(proof["core_sectors"], 40)
            self.assertEqual(proof["mbr_load_sectors"], 40)
            self.assertEqual(proof["mbr_entry_sector"], 1)
            staged = verify_staged_payload(Path(tmp) / "out" / "guest-payload")
            rebind = rebind_payload_descriptor(
                image,
                staged,
                core_sha256=str(proof["core_sha256"]),
                core_sectors=int(proof["core_sectors"]),
            )
            self.assertEqual(rebind["previous"]["core_sectors"], 15)
            self.assertEqual(rebind["descriptor"]["core_sectors"], 40)
            gate = device_gate_for_image(image)
            self.assertEqual(gate["descriptor"]["core_sectors"], 40)
            self.assertEqual(gate["gap"]["core_sectors"], 40)

    def test_capable_host_maybe_install_uses_real_helpers_only_mkimage_stubbed(
        self,
    ) -> None:
        """Only the mkimage binary is stubbed; pad/install/rebind are real."""
        from tools.x8_qemu import bootchain as bc
        from tools.x8_qemu.lifecycle import (
            assemble_disposable_image,
            device_gate_for_image,
            maybe_install_genuine_grub_core,
        )
        from tools.x8_qemu.payload import verify_staged_payload

        synthetic = _synthetic_core(21)

        def _fake_build(*, output: Path, prefix: str = "(,msdos1)/",
                        modules: tuple[str, ...] = ()) -> dict[str, object]:
            self.assertEqual(prefix, "(,msdos1)/")
            Path(output).parent.mkdir(parents=True, exist_ok=True)
            Path(output).write_bytes(synthetic)
            return {
                "path": str(output),
                "bytes": len(synthetic),
                "sha256": hashlib.sha256(synthetic).hexdigest(),
                "modules": "default-set",
            }

        with tempfile.TemporaryDirectory() as tmp:
            manifest = assemble_disposable_image(Path(tmp) / "out")
            image = Path(manifest["image"])
            staged = verify_staged_payload(Path(tmp) / "out" / "guest-payload")
            with (
                _mock.patch.object(bc, "grub_mkimage_available", return_value=True),
                _mock.patch.object(bc, "build_grub_core_via_mkimage",
                                   side_effect=_fake_build),
            ):
                result = maybe_install_genuine_grub_core(image, staged)
            self.assertTrue(result["installed"])
            self.assertEqual(result["chain"], "genuine")
            proof = result["proof"]
            assert isinstance(proof, dict)
            self.assertEqual(proof["core_sectors"], 21)
            previous = result["previous"]
            assert isinstance(previous, dict)
            self.assertEqual(previous["core_sectors"], 15)
            gate = device_gate_for_image(image)
            self.assertEqual(gate["descriptor"]["core_sectors"], 21)

    def test_off_capable_host_keeps_stub_and_no_consumption_claim(self) -> None:
        from tools.x8_qemu import bootchain as bc
        from tools.x8_qemu.lifecycle import (
            assemble_disposable_image,
            genuine_core_capability,
            maybe_install_genuine_grub_core,
        )
        from tools.x8_qemu.payload import verify_staged_payload

        with tempfile.TemporaryDirectory() as tmp:
            manifest = assemble_disposable_image(Path(tmp) / "out")
            self.assertEqual(manifest["guest_core_chain"], "stub")
            self.assertFalse(manifest["genuine_core_installed"])
            self.assertFalse(manifest["genuine_core_attempted"])
            self.assertEqual(manifest["guest_core_sectors"], 15)
            image = Path(manifest["image"])
            staged = verify_staged_payload(Path(tmp) / "out" / "guest-payload")
            with _mock.patch.object(
                bc, "grub_mkimage_available", return_value=False
            ):
                result = maybe_install_genuine_grub_core(image, staged)
                cap = genuine_core_capability()
            self.assertFalse(result["installed"])
            self.assertEqual(result["chain"], "stub")
            _ = cap


class SensitivityControlTests(unittest.TestCase):
    """Break -> RED -> restore -> GREEN through the real mechanism."""

    def test_stub_armed_leg_reds_and_gap_and_exit_controls(self) -> None:
        from tools.x8_qemu.bootchain import STUB_CORE_SECTORS
        from tools.x8_qemu.lifecycle import (
            assemble_disposable_image,
            check_boot_exit,
            decide_device_boot_observation,
            device_gate_for_image,
            LifecycleHarnessError,
        )
        from tools.x8_qemu.payload import (
            DESCRIPTOR_OFFSET,
            PayloadError,
            embed_payload_descriptor,
            read_attestation_signal,
            verify_staged_payload,
            verify_sector_gap_reserved,
        )

        with tempfile.TemporaryDirectory() as tmp:
            manifest = assemble_disposable_image(Path(tmp) / "out")
            image = Path(manifest["image"])
            self.assertEqual(manifest["guest_core_chain"], "stub")

            # 1. Stub-core armed leg still REDs armed-but-unconsumed
            # (sensitivity proof: the gate is not laundered).
            with self.assertRaises(LifecycleHarnessError) as ctx:
                decide_device_boot_observation(
                    leg="boot-B-commit",
                    pre={"default_slot": "A", "one_shot_slot": "B"},
                    post={"default_slot": "A", "one_shot_slot": "B"},
                )
            self.assertIn("armed-but-unconsumed", str(ctx.exception))
            # Consumed pre/post through the same decision stays GREEN.
            self.assertEqual(
                decide_device_boot_observation(
                    leg="boot-B-commit",
                    pre={"default_slot": "A", "one_shot_slot": "B"},
                    post={"default_slot": "A", "one_shot_slot": None},
                ),
                "B",
            )
            # The frozen seam itself REDs on an armed block (host dir).
            with tempfile.TemporaryDirectory() as tmp2:
                from tools.x8_qemu.lifecycle import fresh_machine_state
                from greia_platform.grub_ab import GrubEnvBackend

                machine = fresh_machine_state(Path(tmp2) / "machine")
                GrubEnvBackend.attach(machine["boot_control"]).arm_one_shot("B")
                with self.assertRaises(PayloadError):
                    read_attestation_signal(
                        machine["boot_control"], expected_booted_slot="B"
                    )

            # 2. Corrupted gap byte REDs the gap guard (restore -> GREEN).
            with open(image, "r+b") as handle:
                handle.seek(2 * 512)
                before = handle.read(1)
                handle.seek(2 * 512)
                handle.write(b"\x07" if before != b"\x07" else b"\x08")
            with self.assertRaises(PayloadError):
                verify_sector_gap_reserved(image)
            with self.assertRaises((PayloadError, Exception)):
                device_gate_for_image(image)
            with open(image, "r+b") as handle:
                handle.seek(2 * 512)
                handle.write(before)
            device_gate_for_image(image)

            # 3. Rebind-without-rebind (silent overwrite) is refused.
            staged = verify_staged_payload(Path(tmp) / "out" / "guest-payload")
            with self.assertRaises(PayloadError):
                embed_payload_descriptor(
                    image, staged,
                    core_sha256="ab" * 32, core_sectors=STUB_CORE_SECTORS,
                )
            device_gate_for_image(image)

            # 4. Foreign descriptor sector REDs (restore -> GREEN).
            with open(image, "rb") as handle:
                handle.seek(DESCRIPTOR_OFFSET)
                intact = handle.read(512)
            with open(image, "r+b") as handle:
                handle.seek(DESCRIPTOR_OFFSET)
                handle.write(b"COREIMGB" + b"\x01" * 504)
            with self.assertRaises(PayloadError):
                device_gate_for_image(image)
            with open(image, "r+b") as handle:
                handle.seek(DESCRIPTOR_OFFSET)
                handle.write(intact)
            device_gate_for_image(image)

            # 5. Unclean QEMU exit REDs the clean-exit gate.
            log = Path(tmp) / "qemu.log"
            log.write_text("fake\n", encoding="utf-8")
            check_boot_exit(0, leg="boot-B-commit", qemu_log=log)
            with self.assertRaises(LifecycleHarnessError):
                check_boot_exit(1, leg="boot-B-commit", qemu_log=log)


if __name__ == "__main__":
    unittest.main()
