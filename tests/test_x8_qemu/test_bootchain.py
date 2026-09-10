"""GUEST-BOOT-CHAIN guest boot-chain contract.

Pins the disposable-image boot chain at source scope (no QEMU, loop,
mount, GRUB tooling, or valued-device contact): deterministic MBR stub +
stub core bytes, MBR table preservation, the relocated descriptor
binding, the guest grub.cfg composition through the production seam,
the progress-aware bounded wait policy, and the fail-closed genuine-GRUB
seam. Live SeaBIOS execution stays owned by B3-DEVRUN-RERUN and is never
claimed here.
"""

from __future__ import annotations

import hashlib
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.x8_qemu import bootchain as module
from tools.x8_qemu.bootchain import (
    BootchainError,
    CORE_FIRST_SECTOR,
    CORE_LAST_SECTOR,
    GUEST_SERIAL_PREAMBLE,
    MBR_BOOT_CODE_SIZE,
    STUB_CORE_SECTORS,
    compose_guest_grub_cfg,
    grub_mkimage_argv,
    guest_exit_fallback,
    install_boot_chain,
    install_genuine_grub_chain,
    install_grub_core_bytes,
    install_mbr_boot_code,
    mbr_boot_stub_bytes,
    stub_core_bytes,
    stub_core_sha256,
    verify_boot_chain_present,
    verify_mbr_boot_code,
    wait_for_clean_exit,
)
from tools.x8_qemu.lifecycle import (
    LifecycleHarnessError,
    assemble_disposable_image,
    check_boot_exit,
    device_gate_for_image,
    fresh_machine_state,
)
from tools.x8_qemu.payload import (
    DESCRIPTOR_OFFSET,
    DESCRIPTOR_SECTOR,
    PAYLOAD_MAGIC,
    PAYLOAD_VERSION,
    PayloadError,
    read_payload_descriptor,
    verify_sector_gap_reserved,
    verify_staged_payload,
)


class StubByteTests(unittest.TestCase):
    def test_mbr_stub_is_deterministic_440_bytes(self) -> None:
        first = mbr_boot_stub_bytes()
        self.assertEqual(len(first), MBR_BOOT_CODE_SIZE)
        self.assertEqual(first, mbr_boot_stub_bytes())
        self.assertTrue(any(first))
        # cli entry (SeaBIOS loads sector 0 to 0x7C00 and executes it).
        self.assertEqual(first[0], 0xFA)

    def test_mbr_stub_carries_serial_init_and_progress(self) -> None:
        code = mbr_boot_stub_bytes()
        # COM1 LCR DLAB=1 sequence: mov dx,0x3FB / mov al,0x80 / out dx,al.
        self.assertIn(bytes((0xBA, 0xFB, 0x03, 0xB0, 0x80, 0xEE)), code)
        # 115200 divisor: mov dx,0x3F8 / mov al,0x01 / out dx,al.
        self.assertIn(bytes((0xBA, 0xF8, 0x03, 0xB0, 0x01, 0xEE)), code)
        self.assertIn(b"GREIA-BOOT v1", code)
        self.assertIn(b"GREIA-COREDISK-ERR", code)
        # INT 13h disk read present (core load), never a disk write
        # (AH=03): the stub cannot stamp guest state by construction.
        self.assertIn(bytes((0xCD, 0x13)), code)
        self.assertNotIn(bytes((0xB8, 0x03, 0x01)), code)
        # Far jump into the loaded core at segment 0 (stock entry CS).
        self.assertIn(bytes((0xEA, 0x00, 0x80, 0x00, 0x00)), code)
        # Bounded exit: i8042 reset pulse + triple-fault fallback.
        self.assertIn(bytes((0xB0, 0xFE, 0xE6, 0x64)), code)
        self.assertIn(bytes((0x0F, 0x01, 0x1E)), code)

    def test_stub_core_is_deterministic_and_sector_sized(self) -> None:
        core = stub_core_bytes()
        self.assertEqual(len(core), STUB_CORE_SECTORS * 512)
        self.assertEqual(core, stub_core_bytes())
        self.assertEqual(core[0], 0xFA)
        self.assertIn(b"GREIA-CORE v1", core)
        self.assertIn(b"GREIA-EXIT reboot", core)
        self.assertIn(bytes((0xB0, 0xFE, 0xE6, 0x64)), core)
        self.assertEqual(stub_core_sha256(), hashlib.sha256(core).hexdigest())

    def test_assembler_rejects_branch_overflow(self) -> None:
        asm = module._Asm(org=0x7C00)
        asm.rel8(0xEB, "far")
        asm.zeros(300)
        asm.label("far")
        with self.assertRaises(BootchainError):
            asm.build()


class MbrPreservationTests(unittest.TestCase):
    @staticmethod
    def _read_prefix(path: Path, size: int) -> bytes:
        """Bounded head read: never materialize a multi-GB image in RAM.

        The disposable images are gigabytes (sparse); a whole-file
        ``read_bytes()`` OOM-kills the low-resource reference host, so
        sector-scoped tests read only the bytes they assert.
        """
        with open(path, "rb") as handle:
            return handle.read(size)

    def test_chain_install_preserves_table_and_signature(self) -> None:
        from greia_installer.layout import parse_dos_partition_table
        from tools.x8_qemu.lifecycle import write_mbr_table_for_plan
        from tools.x8_qemu.runner import layout_plan_for_device

        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "disk.img"
            device_bytes = 3072 * 1024 * 1024
            with open(image, "wb") as handle:
                handle.truncate(device_bytes)
            plan = layout_plan_for_device(device_bytes)
            write_mbr_table_for_plan(image, plan=plan)
            before = self._read_prefix(image, 512)
            install_mbr_boot_code(image)
            after = self._read_prefix(image, 512)
            # Boot code installed, everything else byte-identical.
            self.assertNotEqual(after[:MBR_BOOT_CODE_SIZE], before[:MBR_BOOT_CODE_SIZE])
            self.assertEqual(after[MBR_BOOT_CODE_SIZE:], before[MBR_BOOT_CODE_SIZE:])
            self.assertEqual((after[510], after[511]), (0x55, 0xAA))
            parse_dos_partition_table(after)
            verify_mbr_boot_code(image)

    def test_chain_less_mbr_is_red_break_restore_green(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest = assemble_disposable_image(Path(tmp) / "out")
            image = Path(manifest["image"])
            verify_mbr_boot_code(image)
            intact = self._read_prefix(image, MBR_BOOT_CODE_SIZE)
            # BREAK: wipe the MBR boot code (chain-less image).
            with open(image, "r+b") as handle:
                handle.seek(0)
                handle.write(b"\x00" * MBR_BOOT_CODE_SIZE)
            with self.assertRaises(BootchainError):
                verify_mbr_boot_code(image)
            with self.assertRaises(BootchainError):
                verify_boot_chain_present(image)
            # The device gate bites before any boot is claimed.
            with self.assertRaises((BootchainError, PayloadError)):
                device_gate_for_image(image)
            # RESTORE the exact stub bytes and re-prove GREEN.
            with open(image, "r+b") as handle:
                handle.seek(0)
                handle.write(intact)
            verify_mbr_boot_code(image)
            device_gate_for_image(image)


class RelocationMigrationTests(unittest.TestCase):
    def test_old_sector_1_layout_is_red(self) -> None:
        """Relocation omission: v1 descriptor at sector 1 REDs the guard."""
        with tempfile.TemporaryDirectory() as tmp:
            manifest = assemble_disposable_image(Path(tmp) / "out")
            image = Path(manifest["image"])
            # Forge the pre-migration layout: zero MBR code, v1-style
            # descriptor bytes at sector 1, zeroed sector 2047.
            with open(image, "r+b") as handle:
                handle.seek(0)
                handle.write(b"\x00" * MBR_BOOT_CODE_SIZE)
                handle.seek(512)
                v1 = (
                    PAYLOAD_MAGIC
                    + b"\x01"
                    + b"ab" * 32
                    + b"cd" * 32
                )
                handle.write(v1 + b"\x00" * (512 - len(v1)))
                handle.seek(DESCRIPTOR_OFFSET)
                handle.write(b"\x00" * 512)
            with self.assertRaises(PayloadError):
                read_payload_descriptor(image)
            with self.assertRaises(PayloadError):
                verify_sector_gap_reserved(image)
            with self.assertRaises((BootchainError, PayloadError)):
                device_gate_for_image(image)

    def test_descriptor_version_is_pinned_v2_at_2047(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest = assemble_disposable_image(Path(tmp) / "out")
            image = Path(manifest["image"])
            descriptor = read_payload_descriptor(image)
            self.assertEqual(descriptor["version"], PAYLOAD_VERSION)
            self.assertEqual(PAYLOAD_VERSION, 2)
            self.assertEqual(descriptor["descriptor_sector"], DESCRIPTOR_SECTOR)
            self.assertEqual(DESCRIPTOR_SECTOR, 2047)
            self.assertEqual(descriptor["core_sectors"], STUB_CORE_SECTORS)
            self.assertEqual(descriptor["core_sha256"], stub_core_sha256())
            self.assertEqual(CORE_FIRST_SECTOR, 1)
            self.assertEqual(CORE_LAST_SECTOR, 127)


class GuestGrubCfgTests(unittest.TestCase):
    def _production_base(self, root: Path) -> str:
        from greia_platform.grub_ab import render_grub_ab_config_from_record
        from greia_platform.system_updates import load_installed_layout_record
        from tools.x8_qemu.lifecycle import _PASSWORD_HASH

        machine = fresh_machine_state(root / "machine")
        record = load_installed_layout_record(Path(machine["layout"]))
        assert record is not None
        return render_grub_ab_config_from_record(
            record=record, password_hash=_PASSWORD_HASH
        )

    def test_composition_keeps_consumer_verbatim_with_serial_and_exit(self) -> None:
        from greia_platform.grub_ab import validate_grub_ab_text

        with tempfile.TemporaryDirectory() as tmp:
            base = self._production_base(Path(tmp))
            composed = compose_guest_grub_cfg(base)
            # Production consumer block byte-verbatim inside the guest text.
            self.assertIn(base, composed)
            self.assertTrue(composed.startswith(GUEST_SERIAL_PREAMBLE))
            self.assertIn("serial --unit=0 --speed=115200", composed)
            self.assertIn("terminal_output serial console", composed)
            self.assertIn("if [ ! -e /boot/vmlinuz-greia ]; then", composed)
            self.assertIn("\n  reboot\n", composed)
            # Exactly the two appliance entries: no parallel boot surface.
            self.assertEqual(composed.count("menuentry "), 2)
            # The composed artifact validates through the production seam.
            validate_grub_ab_text(composed)
            self.assertIn(guest_exit_fallback(), composed)

    def test_staged_payload_carries_the_composed_config(self) -> None:
        from greia_platform.grub_ab import validate_grub_ab_text

        with tempfile.TemporaryDirectory() as tmp:
            manifest = assemble_disposable_image(Path(tmp) / "out")
            staged = (Path(tmp) / "out" / "guest-payload" / "grub.cfg").read_text(
                encoding="utf-8"
            )
            validate_grub_ab_text(staged)
            self.assertIn("serial --unit=0", staged)
            self.assertIn("save_env next_entry", staged)
            self.assertIn("reboot", staged)
            reproven = verify_staged_payload(Path(tmp) / "out" / "guest-payload")
            self.assertEqual(
                reproven.grub_cfg_sha256, manifest["payload_grub_cfg_sha256"]
            )

    def test_validator_still_bites_on_composed_text(self) -> None:
        """Sensitivity: the guest stanza does not weaken validation."""
        from greia_platform.grub_ab import GrubAbConfigError, validate_grub_ab_text

        with tempfile.TemporaryDirectory() as tmp:
            base = self._production_base(Path(tmp))
            composed = compose_guest_grub_cfg(base)
            # A third entry smuggled into the guest text must RED.
            smuggled = composed + "\nmenuentry 'Extra' --id extra {\n}\n"
            with self.assertRaises(GrubAbConfigError):
                validate_grub_ab_text(smuggled)
            # An extra linux line must RED.
            smuggled_linux = composed + "\nlinux /boot/evil ro\n"
            with self.assertRaises(GrubAbConfigError):
                validate_grub_ab_text(smuggled_linux)


class _FakeProcess:
    """Minimal Popen stand-in for the wait-policy pins (no QEMU)."""

    def __init__(self, script: list[str]) -> None:
        self._script = list(script)
        self.pid = 99999999  # nonexistent: killpg fails closed immediately
        self.calls = 0

    def wait(self, timeout: float | None = None) -> int | None:
        self.calls += 1
        action = self._script[min(self.calls - 1, len(self._script) - 1)]
        if action == "timeout":
            raise subprocess.TimeoutExpired("qemu", timeout or 0)
        if action.startswith("grow:"):
            Path(action[5:]).write_bytes(b"x" * self.calls)
            raise subprocess.TimeoutExpired("qemu", timeout or 0)
        return int(action)


class BootWaitPolicyTests(unittest.TestCase):
    def test_clean_exit_zero_passes_with_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            serial = Path(tmp) / "serial.log"
            serial.write_bytes(b"GREIA-BOOT\r\n")
            image = Path(tmp) / "disk.img"
            image.write_bytes(b"\x00" * 65536)
            proc = _FakeProcess(["0"])
            result = wait_for_clean_exit(
                proc,
                leg="boot-B-commit",
                qemu_log=Path(tmp) / "qemu.log",
                serial_log=serial,
                image=image,
                timeout_seconds=30,
            )
            self.assertEqual(result["returncode"], 0)
            self.assertEqual(result["serial_bytes"], len(b"GREIA-BOOT\r\n"))
            check_boot_exit(int(result["returncode"]), leg="boot-B-commit",
                            qemu_log=Path(tmp) / "qemu.log")

    def test_no_progress_timeout_is_red(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            serial = Path(tmp) / "serial.log"
            serial.write_bytes(b"")
            image = Path(tmp) / "disk.img"
            image.write_bytes(b"\x00" * 65536)
            proc = _FakeProcess(["timeout"] * 50)
            with self.assertRaises(BootchainError) as ctx:
                wait_for_clean_exit(
                    proc,
                    leg="boot-B-commit",
                    qemu_log=Path(tmp) / "qemu.log",
                    serial_log=serial,
                    image=image,
                    timeout_seconds=30,
                    poll_seconds=0.005,
                    no_progress_timeout=0.02,
                    stall_timeout=10,
                )
            self.assertIn("no progress", str(ctx.exception))

    def test_progress_then_stall_is_red(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            serial = Path(tmp) / "serial.log"
            serial.write_bytes(b"")
            image = Path(tmp) / "disk.img"
            image.write_bytes(b"\x00" * 65536)
            proc = _FakeProcess(["grow:" + str(serial)] * 3 + ["timeout"] * 100)
            with self.assertRaises(BootchainError) as ctx:
                wait_for_clean_exit(
                    proc,
                    leg="boot-B-commit",
                    qemu_log=Path(tmp) / "qemu.log",
                    serial_log=serial,
                    image=image,
                    timeout_seconds=30,
                    poll_seconds=0.005,
                    no_progress_timeout=10,
                    stall_timeout=0.02,
                )
            self.assertIn("stalled", str(ctx.exception))

    def test_serial_growth_counts_as_progress_on_clean_exit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            serial = Path(tmp) / "serial.log"
            serial.write_bytes(b"")
            image = Path(tmp) / "disk.img"
            image.write_bytes(b"\x00" * 65536)
            proc = _FakeProcess(["grow:" + str(serial), "0"])
            result = wait_for_clean_exit(
                proc,
                leg="boot-A-accepted",
                qemu_log=Path(tmp) / "qemu.log",
                serial_log=serial,
                image=image,
                timeout_seconds=30,
                poll_seconds=0.005,
            )
            self.assertEqual(result["returncode"], 0)
            self.assertTrue(result["progress_observed"])
            self.assertGreater(int(result["serial_growth_bytes"]), 0)

    def test_image_sha_delta_counts_as_progress(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            serial = Path(tmp) / "serial.log"
            serial.write_bytes(b"")
            image = Path(tmp) / "disk.img"
            image.write_bytes(b"\x00" * 65536)

            class _Mutating(_FakeProcess):
                def wait(self, timeout: float | None = None) -> int | None:
                    self.calls += 1
                    if self.calls == 1:
                        with open(image, "r+b") as handle:
                            handle.seek(0)
                            handle.write(b"GUEST-WROTE")
                        raise subprocess.TimeoutExpired("qemu", timeout or 0)
                    return 0

            result = wait_for_clean_exit(
                _Mutating(["timeout", "0"]),
                leg="boot-A-accepted",
                qemu_log=Path(tmp) / "qemu.log",
                serial_log=serial,
                image=image,
                timeout_seconds=30,
                poll_seconds=0.005,
            )
            self.assertEqual(result["returncode"], 0)
            self.assertTrue(result["progress_observed"])

    def test_hard_ceiling_is_red(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            serial = Path(tmp) / "serial.log"
            serial.write_bytes(b"")
            proc = _FakeProcess(["timeout"] * 1000)
            with self.assertRaises(BootchainError) as ctx:
                wait_for_clean_exit(
                    proc,
                    leg="boot-B-commit",
                    qemu_log=Path(tmp) / "qemu.log",
                    serial_log=serial,
                    image=None,
                    timeout_seconds=0.03,
                    poll_seconds=0.005,
                    no_progress_timeout=60,
                    stall_timeout=60,
                )
            self.assertIn("hard", str(ctx.exception))

    def test_nonzero_exit_flows_to_the_clean_exit_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            serial = Path(tmp) / "serial.log"
            serial.write_bytes(b"")
            result = wait_for_clean_exit(
                _FakeProcess(["1"]),
                leg="boot-B-commit",
                qemu_log=Path(tmp) / "qemu.log",
                serial_log=serial,
                image=None,
                timeout_seconds=30,
            )
            self.assertEqual(result["returncode"], 1)
            # The gate (not the waiter) owns the RED verdict on exit status.
            with self.assertRaises(LifecycleHarnessError):
                check_boot_exit(int(result["returncode"]), leg="boot-B-commit",
                                qemu_log=Path(tmp) / "qemu.log")


class GenuineGrubSeamTests(unittest.TestCase):
    def test_mkimage_argv_carries_the_required_modules(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            argv = grub_mkimage_argv(output=Path(tmp) / "core.img")
            self.assertEqual(argv[:3], ["grub-mkimage", "-O", "i386-pc"])
            # ``loadenv`` is the module file providing the load_env/save_env
            # commands (there are no load_env.mod/save_env.mod files).
            for required in ("serial", "loadenv", "reboot", "halt"):
                self.assertIn(required, argv)
            self.assertNotIn(";", " ".join(argv))

    def test_mkimage_argv_prefix_names_boot_partition(self) -> None:
        """The embedded prefix must carry the partition hint AND the root.

        A bare ``/boot/grub`` resolves on the raw drive (no
        filesystem) and drops the core into a serial-blind rescue
        with no consumption; a ``/boot/grub``-suffixed prefix works
        but strands consumption on a mirror the frozen seam never
        reads — live-observed on the Acer (prefix copy consumed while
        root stayed armed). The root prefix keeps consumption on the
        exact paths the seam inspects. The empty drive slot (``,``)
        takes the BIOS boot drive from DL.
        """
        with tempfile.TemporaryDirectory() as tmp:
            argv = grub_mkimage_argv(output=Path(tmp) / "core.img")
            at = argv.index("-p") + 1
            self.assertEqual(argv[at], "(,msdos1)/")

    def test_mkimage_argv_carries_disk_access_and_prefix_modules(self) -> None:
        """Genuine core must reach the MBR-partitioned image filesystem.

        ``biosdisk`` + ``part_msdos`` own BIOS disk + MBR table access:
        without them the core drops to rescue with no consumption delta.
        ``ext2`` is the GRUB 2.06 i386-pc ext2/3/4 driver (no ``ext4.mod``
        ships, so that name would fail mkimage). Split-core: ``normal``
        is deliberately NOT embedded (115 KiB alone exceeds the 64 KiB
        reservation) — it loads from ``$prefix/i386-pc/`` on partition 1.
        All pinned by the Acer-verified module inventory.
        """
        with tempfile.TemporaryDirectory() as tmp:
            argv = grub_mkimage_argv(output=Path(tmp) / "core.img")
            for required in (
                "biosdisk",
                "part_msdos",
                "ext2",
                "terminal",
                "loadenv",
            ):
                self.assertIn(required, argv)
            self.assertNotIn("ext4", argv)
            self.assertNotIn("normal", argv)

    def test_mkimage_argv_embeds_early_serial_config(self) -> None:
        from tools.x8_qemu.bootchain import (
            EARLY_CONFIG_FILE_NAME,
            GUEST_EARLY_CONFIG,
        )

        with tempfile.TemporaryDirectory() as tmp:
            argv = grub_mkimage_argv(output=Path(tmp) / "core.img")
            self.assertIn("-c", argv)
            self.assertIn(EARLY_CONFIG_FILE_NAME, argv[argv.index("-c") + 1])
            self.assertIn("terminal_output serial", GUEST_EARLY_CONFIG)
            self.assertIn("Greia core: early serial ready", GUEST_EARLY_CONFIG)

    def test_pad_core_bytes_to_sectors_rounds_up(self) -> None:
        from tools.x8_qemu.bootchain import pad_core_bytes_to_sectors

        padded = pad_core_bytes_to_sectors(b"G" * 57870)
        self.assertEqual(len(padded), 114 * 512)
        self.assertTrue(padded.startswith(b"G" * 57870))
        self.assertEqual(padded[57870:], b"\x00" * (114 * 512 - 57870))
        aligned = pad_core_bytes_to_sectors(b"G" * 1024)
        self.assertEqual(aligned, b"G" * 1024)
        with self.assertRaises(BootchainError):
            pad_core_bytes_to_sectors(b"")

    def test_genuine_core_build_fails_closed_without_tooling(self) -> None:
        if module.grub_mkimage_available():
            self.skipTest("grub-mkimage exists on this host; gate is green there")
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(BootchainError):
                module.build_grub_core_via_mkimage(output=Path(tmp) / "core.img")

    def test_install_grub_core_bytes_bounds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "disk.img"
            image.write_bytes(b"\x00" * ((CORE_LAST_SECTOR + 1) * 512))
            with self.assertRaises(BootchainError):
                install_grub_core_bytes(image, b"\x01" * 100)
            with self.assertRaises(BootchainError):
                install_grub_core_bytes(image, b"\x00" * ((CORE_LAST_SECTOR + 1) * 512))
            proof = install_grub_core_bytes(image, b"G" * 1024)
            self.assertEqual(proof["core_sectors"], 2)
            self.assertEqual(len(proof["core_sha256"]), 64)


class ManifestBudgetTests(unittest.TestCase):
    def test_manifest_records_guest_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest = assemble_disposable_image(Path(tmp) / "out")
            self.assertEqual(
                manifest["guest_chain_bytes"],
                MBR_BOOT_CODE_SIZE + STUB_CORE_SECTORS * 512 + 512,
            )
            self.assertEqual(manifest["guest_core_sectors"], STUB_CORE_SECTORS)
            self.assertEqual(manifest["guest_core_sha256"], stub_core_sha256())
            self.assertEqual(len(str(manifest["guest_mbr_stub_sha256"])), 64)
            self.assertTrue(callable(install_boot_chain))


def _synthetic_core_bytes(sectors: int) -> bytes:
    """Deterministic NON-GRUB core exerciser (never claimed as GRUB bytes).

    Exercises the install/rebind/guard mechanism (sector math, MBR load
    count, descriptor binding) at genuine-core sizes without fabricating
    GRUB module bytes. Only a capable-host ``grub-mkimage`` run produces
    real core bytes; the live Acer SeaBIOS boot owns proving those.
    """
    return bytes((index * 31 + 7) % 256 for index in range(sectors * 512))


def _mbr_load_count(code: bytes) -> int:
    """Read the LBA-loop sector bound (CX after ``BB 01 00``) from MBR code.

    The stub emits ``mov bx, 1`` immediately followed by ``mov cx, N``
    (``BB 01 00 B9 lo hi``); only this site carries that adjacency, so
    the bound reads back deterministically at every count.
    """
    marker = bytes((0xBB, 0x01, 0x00, 0xB9))
    at = code.index(marker) + len(marker)
    return code[at] | (code[at + 1] << 8)


class GenuineChainPairingTests(unittest.TestCase):
    """The MBR load count always matches the installed core region."""

    def test_default_mbr_bytes_length_and_count_pinned(self) -> None:
        default = mbr_boot_stub_bytes()
        self.assertEqual(len(default), MBR_BOOT_CODE_SIZE)
        self.assertEqual(default, mbr_boot_stub_bytes(sectors=STUB_CORE_SECTORS))
        self.assertEqual(STUB_CORE_SECTORS, 15)
        self.assertEqual(_mbr_load_count(default), 15)
        # EDD LBA loop markers (not a single CHS call): extension probe,
        # LBA packet call, loop-back branch, and the DAP template.
        self.assertIn(bytes((0xBB, 0xAA, 0x55)), default)  # mov bx, 0x55AA
        self.assertIn(bytes((0xB4, 0x42)), default)  # mov ah, 0x42
        self.assertIn(b"GREIA-BOOT v1", default)
        self.assertIn(bytes((0xEA, 0x00, 0x80, 0x00, 0x00)), default)

    def test_parameterized_counts_differ_only_in_count_word(self) -> None:
        default = mbr_boot_stub_bytes()
        marker_at = default.index(bytes((0xBB, 0x01, 0x00, 0xB9))) + 4
        for count in (1, 2, 63, 114, 127):
            code = mbr_boot_stub_bytes(sectors=count)
            self.assertEqual(len(code), MBR_BOOT_CODE_SIZE)
            self.assertEqual(code[0], 0xFA)
            self.assertEqual(code[marker_at] | (code[marker_at + 1] << 8), count)
            masked = bytearray(code)
            masked[marker_at] = default[marker_at]
            masked[marker_at + 1] = default[marker_at + 1]
            self.assertEqual(bytes(masked), default)
            # Branch targets re-resolve identically at every count.
            self.assertIn(b"GREIA-BOOT v1", code)
            self.assertIn(bytes((0xEA, 0x00, 0x80, 0x00, 0x00)), code)

    def test_out_of_reservation_counts_are_red(self) -> None:
        for bad in (0, -1, 128, 1000, "15", 15.0, True, None):
            with self.assertRaises(BootchainError):
                mbr_boot_stub_bytes(sectors=bad)  # type: ignore[arg-type]

    def test_entry_sector_selects_far_jump_and_is_bounded(self) -> None:
        default = mbr_boot_stub_bytes()
        self.assertIn(bytes((0xEA, 0x00, 0x80, 0x00, 0x00)), default)
        kernel_entry = mbr_boot_stub_bytes(sectors=114, entry_sector=1)
        self.assertEqual(len(kernel_entry), MBR_BOOT_CODE_SIZE)
        self.assertIn(bytes((0xEA, 0x00, 0x82, 0x00, 0x00)), kernel_entry)
        self.assertNotIn(bytes((0xEA, 0x00, 0x80, 0x00, 0x00)), kernel_entry)
        for bad_entry in (-1, 114, 127, "1", 1.0, True, None):
            with self.assertRaises(BootchainError):
                mbr_boot_stub_bytes(sectors=114, entry_sector=bad_entry)  # type: ignore[arg-type]

    def test_genuine_chain_install_rebind_gate_green(self) -> None:
        from tools.x8_qemu.payload import rebind_payload_descriptor

        with tempfile.TemporaryDirectory() as tmp:
            manifest = assemble_disposable_image(Path(tmp) / "out")
            image = Path(manifest["image"])
            device_gate_for_image(image)
            genuine = _synthetic_core_bytes(63)
            proof = install_genuine_grub_chain(image, genuine)
            self.assertEqual(proof["core_sectors"], 63)
            self.assertEqual(proof["mbr_load_sectors"], 63)
            self.assertEqual(
                proof["core_sha256"], hashlib.sha256(genuine).hexdigest()
            )
            # The installed MBR loads exactly the installed core region and
            # jumps past diskboot to the kernel entry.
            with open(image, "rb") as handle:
                installed_mbr = handle.read(512)[:MBR_BOOT_CODE_SIZE]
            self.assertEqual(_mbr_load_count(installed_mbr), 63)
            self.assertIn(bytes((0xEA, 0x00, 0x82, 0x00, 0x00)), installed_mbr)
            self.assertEqual(proof["mbr_entry_sector"], 1)
            # Rebind the descriptor from the stub binding to the new one.
            staged = verify_staged_payload(Path(tmp) / "out" / "guest-payload")
            rebind = rebind_payload_descriptor(
                image,
                staged,
                core_sha256=str(proof["core_sha256"]),
                core_sectors=int(proof["core_sectors"]),
            )
            self.assertEqual(rebind["previous"]["core_sectors"], STUB_CORE_SECTORS)
            self.assertEqual(rebind["descriptor"]["core_sectors"], 63)
            # Full device gate green on the genuine-sized binding.
            gate = device_gate_for_image(image)
            self.assertEqual(gate["descriptor"]["core_sectors"], 63)
            self.assertEqual(gate["gap"]["core_sectors"], 63)

    def test_genuine_chain_rejects_bad_sizes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest = assemble_disposable_image(Path(tmp) / "out")
            image = Path(manifest["image"])
            with self.assertRaises(BootchainError):
                install_genuine_grub_chain(image, b"\x01" * 100)
            with self.assertRaises(BootchainError):
                install_genuine_grub_chain(image, b"")
            with self.assertRaises(BootchainError):
                install_genuine_grub_chain(image, b"\x00" * (128 * 512))
            # Refused installs leave the stub chain intact and green.
            device_gate_for_image(image)

    def test_swapped_genuine_byte_reds_gap_restore_green(self) -> None:
        from tools.x8_qemu.payload import rebind_payload_descriptor

        with tempfile.TemporaryDirectory() as tmp:
            manifest = assemble_disposable_image(Path(tmp) / "out")
            image = Path(manifest["image"])
            genuine = _synthetic_core_bytes(63)
            proof = install_genuine_grub_chain(image, genuine)
            staged = verify_staged_payload(Path(tmp) / "out" / "guest-payload")
            rebind_payload_descriptor(
                image,
                staged,
                core_sha256=str(proof["core_sha256"]),
                core_sectors=int(proof["core_sectors"]),
            )
            device_gate_for_image(image)
            # BREAK: one flipped byte inside the bound genuine region.
            with open(image, "r+b") as handle:
                handle.seek(2 * 512)
                before = handle.read(1)
                handle.seek(2 * 512)
                handle.write(b"\x07" if before != b"\x07" else b"\x08")
            with self.assertRaises(PayloadError):
                verify_sector_gap_reserved(image)
            with self.assertRaises((BootchainError, PayloadError)):
                device_gate_for_image(image)
            # RESTORE the exact genuine byte and re-prove GREEN.
            with open(image, "r+b") as handle:
                handle.seek(2 * 512)
                handle.write(before)
            device_gate_for_image(image)

    def test_smaller_genuine_zeroes_stub_tail(self) -> None:
        from tools.x8_qemu.payload import rebind_payload_descriptor

        with tempfile.TemporaryDirectory() as tmp:
            manifest = assemble_disposable_image(Path(tmp) / "out")
            image = Path(manifest["image"])
            genuine = _synthetic_core_bytes(5)
            proof = install_genuine_grub_chain(image, genuine)
            self.assertEqual(proof["core_sectors"], 5)
            staged = verify_staged_payload(Path(tmp) / "out" / "guest-payload")
            rebind_payload_descriptor(
                image,
                staged,
                core_sha256=str(proof["core_sha256"]),
                core_sectors=int(proof["core_sectors"]),
            )
            # The stale stub tail (sectors 6-15) is zeroed: gap green.
            gate = device_gate_for_image(image)
            self.assertEqual(gate["gap"]["core_sectors"], 5)
            with open(image, "rb") as handle:
                handle.seek(10 * 512)
                self.assertEqual(handle.read(512), b"\x00" * 512)


class NoParallelMechanismTests(unittest.TestCase):
    def test_bootchain_has_no_attestation_or_agent_surface(self) -> None:
        text = Path(module.__file__).read_text(encoding="utf-8")
        for forbidden in (
            "simulate_reboot(",
            "FakeGrubBackend",
            "last_booted",
            "reconcile(",
            "shell=True",
        ):
            self.assertNotIn(forbidden, text)
        for required in (
            "wait_for_clean_exit",
            "compose_guest_grub_cfg",
            "install_boot_chain",
            "verify_boot_chain_present",
            "grub-mkimage",
        ):
            self.assertIn(required, text)


if __name__ == "__main__":
    unittest.main()
