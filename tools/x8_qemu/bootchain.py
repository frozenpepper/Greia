"""GUEST-BOOT-CHAIN guest boot chain for the disposable T7 image.

Closes the SeaBIOS -> serial -> exit chain that the T7-PAYLOAD image left
open: ``write_mbr_table_for_plan`` wrote a partition table with zero MBR
boot code, no ``core.img`` existed, and ``grub.cfg`` referenced a slot
kernel that is not installed, so every QEMU leg ended at the clean-exit
gate RED (timeout/nonzero, zero serial bytes).

What this module owns (guest + harness readiness only; the live verdict
stays with ``B3-DEVRUN-RERUN``):

- a deterministic two-stage boot chain assembled source-scope without
  privileged tools: a 440-byte MBR boot stub (sector 0, bytes 0-439; the
  partition table at 440-511 is preserved byte-for-byte) that initializes
  COM1 (115200 8N1), prints ``GREIA-BOOT`` progress bytes, loads the core
  region (sectors 1..N, N pinned to the installed core by
  ``install_genuine_grub_chain``; the source-scope default is sectors
  1-15) to ``0x0800:0x0000`` via INT 13h, and jumps to it;
  plus a stub core that prints ``GREIA-CORE`` / ``GREIA-EXIT`` progress
  and exits via guest reboot (QEMU ``-no-reboot`` turns guest reboot into
  process exit 0, which is exactly what the clean-exit gate needs);
- the sector-gap coordination for a future genuine GRUB ``core.img``:
  sectors 1-127 are the reserved core region, the payload descriptor was
  relocated to sector 2047 (see ``payload.py`` migration + ``LIFECYCLE.md``
  section 8), and the descriptor binds the installed core bytes
  (``core_sha256`` + ``core_sectors``) so the gap guard verifies the core
  instead of merely requiring nonzero bytes;
- the guest-only ``grub.cfg`` composition: the production-rendered
  one-shot consumer block stays byte-verbatim (rendered + validated
  through the production ``grub_ab`` seams in ``payload.py``); this module
  only prepends a COM1 serial stanza and appends a bounded
  post-consumption exit fallback (``[ -e kernel ]`` else ``reboot``) that
  the production validator provably still accepts;
- the progress-aware bounded boot wait: serial-byte growth and image SHA
  delta count as progress evidence with a hard ceiling; timeout without
  progress stays RED; progress without eventual clean exit stays RED;
- the capable-host seam for genuine GRUB module bytes
  (``grub-mkimage`` i386-pc with serial/load_env/save_env/reboot): gated,
  fail-closed, never claimed green here.

Honesty boundary (source scope, darwin host: no QEMU, no GRUB tooling):

- the assembled chain is structurally SeaBIOS-loadable (valid boot code +
  ``0x55AA`` + production-parsed partition table + hash-bound core +
  valid descriptor) and is pinned by exact-byte + structural tests, but
  live execution is NOT claimed here -- that belongs to ``B3-DEVRUN-RERUN``
  on a capable host;
- the stub core never touches ``grubenv`` or backend state: there is no
  guest agent, and stamping stays host-side via ``reconcile`` +
  ``read_attestation_signal``. Armed-leg consumption therefore stays RED
  until genuine GRUB (load_env/save_env) lands via the gated seam;
- genuine ``grub-mkimage`` module bytes are NOT embedded here: the tool is
  absent off a capable host and the seam fails closed RED (pinned).

Fake boundary: no stubbed health/launcher, no fabricated slot/journal/
GRUB state, no ``simulate_reboot``. Subprocess calls use argv arrays with
``shell=False``. Reads are bounded (sector multiples, 8 MiB streaming
hashes); no whole-image RAM copies.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import signal as _signal
import subprocess
import time
from pathlib import Path

from greia_platform.grub_ab import GRUB_KERNEL_PATH

#: MBR boot-code window: bytes 0-439. Bytes 440-443 carry the disk
#: signature, 446-509 the partition table, 510-511 the 0x55AA signature;
#: the chain installer never writes outside 0-439.
MBR_BOOT_CODE_SIZE = 440

#: MBR boot-signature offset (sector 0, last two bytes).
MBR_SIGNATURE_OFFSET = 510

#: First sector of the reserved core region (right after the MBR).
CORE_FIRST_SECTOR = 1

#: Last sector of the reserved core region. Genuine GRUB i386-pc cores
#: (serial + load_env/save_env + reboot/halt + normal + fs) fit well under
#: this 64 KiB reservation; the source-scope stub core uses only the first
#: ``STUB_CORE_SECTORS`` of it and the remainder stays zero.
CORE_LAST_SECTOR = 127

#: Sectors occupied by the source-scope stub core (15 x 512 = 7680 bytes).
STUB_CORE_SECTORS = 15

#: Guest serial line: COM1 at 115200 8N1 into the QEMU ``-serial file:`` log.
GUEST_SERIAL_UNIT = 0
GUEST_SERIAL_SPEED = 115200

#: Progress-aware wait defaults (seconds). Acer TCG context (Atom N270, no
#: KVM) boots slowly, so the no-progress ceiling is generous but still a
#: hard bound: a silent image never goes green, it just takes longer to
#: RED than on a fast host.
BOOT_WAIT_POLL_SECONDS = 1.0
BOOT_WAIT_NO_PROGRESS_SECONDS = 120.0
BOOT_WAIT_STALL_SECONDS = 120.0
BOOT_WAIT_KILL_GRACE_SECONDS = 5.0


class BootchainError(RuntimeError):
    """Guest boot chain missing, corrupt, or refused fail-closed."""


# ---------------------------------------------------------------------------
# Minimal 16-bit assembler (label-resolved, deterministic output)
# ---------------------------------------------------------------------------


class _Asm:
    """Tiny label-resolving emitter for the reviewed boot stubs below.

    Only the exact instruction forms used by the stubs are supported; every
    emitted byte is therefore reviewable against the Intel encoding. Jumps
    and calls resolve in a final pass and raise fail-closed when a rel8
    displacement overflows, so layout edits cannot silently corrupt a
    branch target.
    """

    def __init__(self, org: int) -> None:
        self._org = org
        self._buf = bytearray()
        self._labels: dict[str, int] = {}
        self._fixups: list[tuple[int, str, str]] = []

    def label(self, name: str) -> None:
        if name in self._labels:
            raise BootchainError(f"duplicate assembly label {name!r}")
        self._labels[name] = len(self._buf)

    def b(self, *values: int) -> None:
        self._buf.extend(values)

    def rel8(self, opcode: int, name: str) -> None:
        self._fixups.append((len(self._buf), "rel8", name))
        self._buf.extend((opcode, 0x00))

    def call(self, name: str) -> None:
        self._fixups.append((len(self._buf), "rel16", name))
        self._buf.extend((0xE8, 0x00, 0x00))

    def mov_si(self, name: str) -> None:
        self._fixups.append((len(self._buf), "abs16", name))
        self._buf.extend((0xBE, 0x00, 0x00))

    def lidt(self, name: str) -> None:
        self._fixups.append((len(self._buf), "lidt", name))
        self._buf.extend((0x0F, 0x01, 0x1E, 0x00, 0x00))

    def asciiz(self, text: str) -> None:
        raw = text.encode("ascii")
        if len(raw) + 1 > 64:
            raise BootchainError("boot message exceeds the 64-byte bound")
        self._buf.extend(raw + b"\x00")

    def zeros(self, count: int) -> None:
        self._buf.extend(b"\x00" * count)

    def pos(self) -> int:
        return len(self._buf)

    def build(self) -> bytes:
        for at, kind, name in self._fixups:
            if name not in self._labels:
                raise BootchainError(f"undefined assembly label {name!r}")
            target = self._labels[name]
            if kind == "rel8":
                disp = target - (at + 2)
                if not -128 <= disp <= 127:
                    raise BootchainError(
                        f"rel8 overflow for {name!r}: displacement {disp}"
                    )
                self._buf[at + 1] = disp & 0xFF
            elif kind == "rel16":
                disp = target - (at + 3)
                if not -32768 <= disp <= 32767:
                    raise BootchainError(
                        f"rel16 overflow for {name!r}: displacement {disp}"
                    )
                self._buf[at + 1 : at + 3] = (disp & 0xFFFF).to_bytes(2, "little")
            elif kind == "abs16":
                self._buf[at + 1 : at + 3] = (
                    (self._org + target) & 0xFFFF
                ).to_bytes(2, "little")
            elif kind == "lidt":
                self._buf[at + 3 : at + 5] = (
                    (self._org + target) & 0xFFFF
                ).to_bytes(2, "little")
            else:  # pragma: no cover - defensive
                raise BootchainError(f"unknown fixup kind {kind!r}")
        return bytes(self._buf)


def _emit_print_routine(asm: _Asm) -> None:
    """Append the shared COM1 print subroutine (SI = NUL-terminated)."""
    asm.label("print")
    asm.b(0xAC)  # lodsb
    asm.b(0x84, 0xC0)  # test al, al
    asm.rel8(0x74, "print_ret")  # jz print_ret
    asm.b(0x8A, 0xD8)  # mov bl, al
    asm.b(0xBA, 0xFD, 0x03)  # mov dx, 0x3FD (LSR)
    asm.label("print_wait")
    asm.b(0xEC)  # in al, dx
    asm.b(0xA8, 0x20)  # test al, 0x20 (THR empty)
    asm.rel8(0x74, "print_wait")  # jz print_wait
    asm.b(0x8A, 0xC3)  # mov al, bl
    asm.b(0xBA, 0xF8, 0x03)  # mov dx, 0x3F8 (THR)
    asm.b(0xEE)  # out dx, al
    asm.rel8(0xEB, "print")  # jmp print
    asm.label("print_ret")
    asm.b(0xC3)  # ret


def _emit_reboot(asm: _Asm) -> None:
    """Append the bounded guest exit: i8042 reset, triple-fault, halt."""
    asm.label("reboot")
    asm.label("kb_wait")
    asm.b(0xE4, 0x64)  # in al, 0x64
    asm.b(0xA8, 0x02)  # test al, 0x02 (input buffer full)
    asm.rel8(0x75, "kb_wait")  # jnz kb_wait
    asm.b(0xB0, 0xFE)  # mov al, 0xFE (reset pulse)
    asm.b(0xE6, 0x64)  # out 0x64, al
    # Fallback: broken IDT + fault forces a triple-fault reset when the
    # controller pulse is ignored. Under QEMU -no-reboot any guest reset
    # becomes process exit 0, which is what the clean-exit gate needs.
    asm.lidt("idt_zero")  # lidt [idt_zero]
    asm.b(0xCC)  # int3
    asm.b(0xFA)  # cli
    asm.b(0xF4)  # hlt
    asm.rel8(0xEB, "halted")  # jmp halted (never a silent fallthrough)
    asm.label("halted")
    asm.rel8(0xEB, "halted")  # jmp $ (fail-closed: QEMU timeout REDs)


def mbr_boot_stub_bytes(
    *, sectors: int = STUB_CORE_SECTORS, entry_sector: int = 0
) -> bytes:
    """Build the deterministic 440-byte MBR boot stub (ORG 0x7C00).

    SeaBIOS loads sector 0 to 0x7C00 with DL = boot drive: init segments,
    COM1 115200 8N1, print ``GREIA-BOOT``, load sectors 1..N to
    ``0x0800:0x0000`` via a SINGLE INT 13h EDD LBA call (``AH=42h``
    DAP, count patched at build, offset 0), then far-jump to the entry
    point. A single call (not a loop): live-measured on the Acer (RAM
    readback after multi-call loads showed only the first transfer ever
    landed while later calls kept succeeding), SeaBIOS on this target
    silently drops the payload of repeated EDD calls, so iterating is
    not just unnecessary — it cannot work. A single call is also free
    of CHS track limits (the original single-``AH=02h`` design failed
    past one track — proven RED as ``GREIA-COREDISK-ERR`` + error-path
    reboot). N ≤ 127 always fits one EDD call. A disk error prints
    ``GREIA-COREDISK-ERR`` and reboots instead of hanging; a missing
    EDD BIOS takes the same bounded exit.

    ``sectors`` is the call count (patched as ``CX`` at build) and MUST
    match the installed core region: the default is the source-scope
    stub core (``STUB_CORE_SECTORS``); genuine GRUB ``core.img`` bytes
    use the composed :func:`install_genuine_grub_chain` helper so the
    MBR load count always equals the descriptor-bound
    ``core_sectors``. Counts outside the ``1``-``CORE_LAST_SECTOR``
    reservation raise fail-closed (a single EDD call tops out at 127
    sectors per the EDD spec, which is exactly the reservation).

    ``entry_sector`` selects the far-jump target for linear
    ``0x8000 + entry_sector * 512``, always encoded as segment 0
    (``0x0000:0x8000`` for a stub core, ``0x0000:0x8200`` for the GRUB
    kernel): ``0`` runs a stub core at the load address, while genuine
    GRUB cores need ``1`` — ``core.img`` sector 0 is ``diskboot.img``,
    whose blocklist only ``grub-setup`` could patch (unpatched, it
    parks at its ``Read Error`` halt — live-observed as a static EIP
    in a ``jmp $`` with GRUB's ``loading`` strings on VGA), so the
    stub jumps past it straight to the kernel at core+512, exactly
    where ``diskboot`` would have placed it. The segment-0 encoding
    mirrors stock ``diskboot`` (whose kernel jump is ``ea 00 82 00
    00``). DL (BIOS boot drive) is preserved for the entry point.
    """
    if (
        not isinstance(sectors, int)
        or isinstance(sectors, bool)
        or sectors < CORE_FIRST_SECTOR
        or sectors > CORE_LAST_SECTOR
    ):
        raise BootchainError(
            f"MBR core-load count {sectors!r} escapes the "
            f"1-{CORE_LAST_SECTOR} reservation"
        )
    if (
        not isinstance(entry_sector, int)
        or isinstance(entry_sector, bool)
        or entry_sector < 0
        or entry_sector >= sectors
    ):
        raise BootchainError(
            f"MBR entry sector {entry_sector!r} is outside the loaded "
            f"0-{sectors - 1} region"
        )
    entry_offset = 0x8000 + entry_sector * 512
    if entry_offset > 0xFFFF:
        raise BootchainError(
            f"MBR entry linear {entry_offset:#x} escapes real-mode offset range"
        )
    asm = _Asm(org=0x7C00)
    asm.b(0xFA)  # cli
    asm.b(0x31, 0xC0)  # xor ax, ax
    asm.b(0x8E, 0xD0)  # mov ss, ax
    asm.b(0xBC, 0x00, 0x7C)  # mov sp, 0x7C00
    asm.b(0x8E, 0xD8)  # mov ds, ax
    asm.b(0x8E, 0xC0)  # mov es, ax
    asm.b(0x52)  # push dx (save BIOS boot drive)
    asm.b(0xFB)  # sti
    asm.b(0xFC)  # cld (BIOS may leave DF set; lodsb needs DF=0)
    # COM1 115200 8N1.
    asm.b(0xBA, 0xFB, 0x03)  # mov dx, 0x3FB (LCR)
    asm.b(0xB0, 0x80)  # mov al, 0x80 (DLAB=1)
    asm.b(0xEE)  # out dx, al
    asm.b(0xBA, 0xF8, 0x03)  # mov dx, 0x3F8 (DLL)
    asm.b(0xB0, 0x01)  # mov al, 0x01 (divisor 1 = 115200)
    asm.b(0xEE)  # out dx, al
    asm.b(0xBA, 0xF9, 0x03)  # mov dx, 0x3F9 (DLM)
    asm.b(0x30, 0xC0)  # xor al, al
    asm.b(0xEE)  # out dx, al
    asm.b(0xBA, 0xFB, 0x03)  # mov dx, 0x3FB
    asm.b(0xB0, 0x03)  # mov al, 0x03 (8N1, DLAB=0)
    asm.b(0xEE)  # out dx, al
    # Progress: the boot stub itself reached the serial stanza.
    asm.mov_si("msg_boot")
    asm.call("print")
    # EDD LBA support probe (AH=41h, BX=0x55AA); SeaBIOS always has it.
    asm.b(0x5A)  # pop dx (DL = boot drive)
    asm.b(0x52)  # push dx (keep saved for the core entry)
    asm.b(0xBB, 0xAA, 0x55)  # mov bx, 0x55AA
    asm.b(0xB4, 0x41)  # mov ah, 0x41
    asm.b(0xCD, 0x13)  # int 0x13
    asm.rel8(0x73, "edd_ok")  # jnc edd_ok
    asm.mov_si("msg_err")
    asm.call("print")
    asm.rel8(0xEB, "reboot")  # jmp reboot (bounded exit, never a hang)
    asm.label("edd_ok")
    # Load the core region with one EDD call: CX = sector count N,
    # BX = first LBA (1), ES = 0x0800, offset 0, SI = DAP address.
    # The drive word stays on the stack ([drive] invariant) and the
    # count is saved/restored around the call (INT 13h returns status
    # in AH). DL is reloaded from the stack for both the call and the
    # core entry, so a BIOS-clobbered DL can never corrupt either.
    asm.b(0xBB, 0x01, 0x00)  # mov bx, 1 (first core sector)
    asm.b(0xB9, sectors & 0xFF, (sectors >> 8) & 0xFF)  # mov cx, N
    asm.b(0xB8, 0x00, 0x08)  # mov ax, 0x0800
    asm.b(0x8E, 0xC0)  # mov es, ax
    asm.mov_si("dap")  # mov si, dap
    asm.b(0x5A)  # pop dx (DL = boot drive; stack [])
    asm.b(0x52)  # push dx (stack [drive])
    asm.b(0x89, 0xC8)  # mov ax, cx (count = N)
    asm.b(0x89, 0x44, 0x02)  # mov [si+2], ax (DAP count)
    asm.b(0xC7, 0x44, 0x04, 0x00, 0x00)  # mov [si+4], word 0 (offset)
    asm.b(0x8C, 0x44, 0x06)  # mov [si+6], es (segment)
    asm.b(0x89, 0x5C, 0x08)  # mov [si+8], bx (LBA low; high dword is zero)
    asm.b(0x50)  # push ax (save count: int 0x13 returns status in AH)
    asm.b(0xB4, 0x42)  # mov ah, 0x42
    asm.b(0xCD, 0x13)  # int 0x13
    asm.rel8(0x72, "disk_err")  # jc disk_err (stack dirty is fine: no return)
    asm.b(0x58)  # pop ax (drop count; stack [drive])
    asm.b(0x5A)  # pop dx (DL = boot drive for the core entry)
    # Settle delay so the progress bytes flush before the far jump.
    asm.b(0xB9, 0x00, 0x20)  # mov cx, 0x2000
    asm.label("settle")
    asm.b(0x49)  # dec cx
    asm.rel8(0x75, "settle")  # jnz settle
    asm.b(
        0xEA, entry_offset & 0xFF, (entry_offset >> 8) & 0xFF, 0x00, 0x00
    )  # jmp far 0x0000:entry (stub core at 0x8000, GRUB kernel past diskboot)
    asm.label("disk_err")
    asm.b(0x31, 0xC0)  # xor ax, ax
    asm.b(0x8E, 0xD8)  # mov ds, ax (INT 13h may have clobbered DS; the
    # error text must print from the right segment to be diagnostic)
    asm.mov_si("msg_err")
    asm.call("print")
    asm.rel8(0xEB, "reboot")  # jmp reboot (bounded exit, never a hang)
    _emit_reboot(asm)
    _emit_print_routine(asm)
    asm.label("msg_boot")
    asm.asciiz("GREIA-BOOT v1\r\n")
    asm.label("msg_err")
    asm.asciiz("GREIA-COREDISK-ERR\r\n")
    asm.label("idt_zero")
    asm.zeros(6)
    asm.label("dap")
    asm.b(0x10, 0x00)  # DAP size 16, reserved 0
    asm.zeros(14)  # count/offset/segment/LBA filled per iteration
    raw = asm.build()
    if len(raw) > MBR_BOOT_CODE_SIZE:
        raise BootchainError(
            f"MBR stub overflow: {len(raw)} bytes exceed {MBR_BOOT_CODE_SIZE}"
        )
    return raw + b"\x00" * (MBR_BOOT_CODE_SIZE - len(raw))


def stub_core_bytes() -> bytes:
    """Build the deterministic stub core (ORG 0, runs at 0x0800:0x0000).

    Prints ``GREIA-CORE`` + ``GREIA-EXIT`` progress to COM1 (inherited
    115200 8N1 configuration) and exits via guest reboot. Padded with
    zeros to exactly ``STUB_CORE_SECTORS`` sectors. Never touches disk or
    ``grubenv``: there is deliberately no guest agent here.
    """
    asm = _Asm(org=0x0000)
    asm.b(0xFA)  # cli
    asm.b(0x31, 0xC0)  # xor ax, ax
    asm.b(0x8E, 0xD0)  # mov ss, ax
    asm.b(0xBC, 0x00, 0x80)  # mov sp, 0x8000
    asm.b(0xB8, 0x00, 0x08)  # mov ax, 0x0800
    asm.b(0x8E, 0xD8)  # mov ds, ax
    asm.b(0x8E, 0xC0)  # mov es, ax
    asm.b(0xFB)  # sti
    asm.b(0xFC)  # cld
    asm.mov_si("msg_core")
    asm.call("print")
    asm.mov_si("msg_exit")
    asm.call("print")
    # Settle delay so the exit bytes flush before the reset pulse.
    asm.b(0xB9, 0x00, 0x40)  # mov cx, 0x4000
    asm.label("settle")
    asm.b(0x49)  # dec cx
    asm.rel8(0x75, "settle")  # jnz settle
    asm.rel8(0xEB, "reboot")  # jmp reboot
    _emit_reboot(asm)
    _emit_print_routine(asm)
    asm.label("msg_core")
    asm.asciiz("GREIA-CORE v1\r\n")
    asm.label("msg_exit")
    asm.asciiz("GREIA-EXIT reboot\r\n")
    asm.label("idt_zero")
    asm.zeros(6)
    raw = asm.build()
    total = STUB_CORE_SECTORS * 512
    if len(raw) > total:
        raise BootchainError(
            f"stub core overflow: {len(raw)} bytes exceed {total}"
        )
    return raw + b"\x00" * (total - len(raw))


def stub_core_sha256() -> str:
    """SHA-256 of the exact stub core bytes (gap-guard binding)."""
    return hashlib.sha256(stub_core_bytes()).hexdigest()


def mbr_stub_sha256() -> str:
    """SHA-256 of the exact 440-byte MBR stub (manifest evidence)."""
    return hashlib.sha256(mbr_boot_stub_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# Image installation (source-scope file offsets, no privilege needed)
# ---------------------------------------------------------------------------


def install_mbr_boot_code(image: Path, code: bytes | None = None) -> str:
    """Write the MBR boot stub into bytes 0-439, preserving 440-511.

    The partition table + disk signature written by
    ``write_mbr_table_for_plan`` are read back and spliced unchanged, then
    re-proven by parsing the table through the production seam. Returns
    the installed code SHA-256.
    """
    from greia_installer.layout import parse_dos_partition_table

    blob = bytes(code) if code is not None else mbr_boot_stub_bytes()
    if len(blob) != MBR_BOOT_CODE_SIZE:
        raise BootchainError(
            f"MBR boot code must be exactly {MBR_BOOT_CODE_SIZE} bytes, "
            f"got {len(blob)}"
        )
    path = Path(image)
    with open(path, "r+b") as handle:
        handle.seek(0)
        sector0 = handle.read(512)
        if len(sector0) != 512:
            raise BootchainError("image has no MBR sector to chain")
        if sector0[MBR_SIGNATURE_OFFSET] != 0x55 or sector0[511] != 0xAA:
            raise BootchainError(
                "refusing to chain an image without the MBR boot signature"
            )
        # The table must already parse: chaining never repairs geometry.
        parse_dos_partition_table(sector0)
        handle.seek(0)
        handle.write(blob + sector0[MBR_BOOT_CODE_SIZE:])
        handle.flush()
        os.fsync(handle.fileno())
    with open(path, "rb") as handle:
        check = handle.read(512)
    if check[:MBR_BOOT_CODE_SIZE] != blob or check[MBR_BOOT_CODE_SIZE:] != sector0[MBR_BOOT_CODE_SIZE:]:
        raise BootchainError("MBR chain write did not read back intact")
    parse_dos_partition_table(check)
    return hashlib.sha256(blob).hexdigest()


def install_core_region(
    image: Path, core: bytes | None = None, *, sectors: int = STUB_CORE_SECTORS
) -> str:
    """Write the core region (sectors 1..N) into the reserved gap window.

    Refuses when the requested sector count exceeds the ``CORE_LAST_SECTOR``
    reservation or is not sector-aligned. Returns the installed core
    SHA-256 for the descriptor binding.
    """
    blob = bytes(core) if core is not None else stub_core_bytes()
    if sectors < CORE_FIRST_SECTOR or sectors > CORE_LAST_SECTOR:
        raise BootchainError(
            f"core sector count {sectors} escapes the 1-{CORE_LAST_SECTOR} "
            "reservation"
        )
    if len(blob) != sectors * 512:
        raise BootchainError(
            f"core bytes {len(blob)} do not fill {sectors} sectors exactly"
        )
    path = Path(image)
    if path.stat().st_size < (CORE_LAST_SECTOR + 1) * 512:
        raise BootchainError("image is too small for the core reservation")
    with open(path, "r+b") as handle:
        handle.seek(CORE_FIRST_SECTOR * 512)
        handle.write(blob)
        handle.flush()
        os.fsync(handle.fileno())
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        handle.seek(CORE_FIRST_SECTOR * 512)
        remaining = len(blob)
        while remaining > 0:
            chunk = handle.read(min(8 * 1024 * 1024, remaining))
            if not chunk:
                raise BootchainError("core region re-read is short")
            digest.update(chunk)
            remaining -= len(chunk)
    if digest.hexdigest() != hashlib.sha256(blob).hexdigest():
        raise BootchainError("core region did not read back intact")
    return digest.hexdigest()


def install_boot_chain(image: Path) -> dict[str, object]:
    """Install the source-scope boot chain: MBR stub + stub core.

    Pure file-offset writes (no loop/mount, no privilege). The gap tail
    (sectors 16-2046) is left as the assembly-provided zeros that the gap
    guard verifies; the payload descriptor sector is written afterwards by
    ``embed_payload_descriptor`` with this core binding. Returns the chain
    evidence for the image manifest.
    """
    mbr_sha = install_mbr_boot_code(Path(image))
    core_sha = install_core_region(Path(image))
    chain_bytes = MBR_BOOT_CODE_SIZE + STUB_CORE_SECTORS * 512
    return {
        "mbr_stub_sha256": mbr_sha,
        "core_sha256": core_sha,
        "core_sectors": STUB_CORE_SECTORS,
        "core_first_sector": CORE_FIRST_SECTOR,
        "core_last_reserved_sector": CORE_LAST_SECTOR,
        "chain_bytes": chain_bytes,
    }


def _zero_core_reservation_tail(image: Path, *, installed_sectors: int) -> None:
    """Zero sectors N+1..CORE_LAST_SECTOR so the gap guard proves exact bytes.

    A genuine core smaller than a previously installed core would otherwise
    leave stale bytes inside the reservation, which the gap guard must RED.
    Bounded streaming write with a read-back proof; no whole-gap RAM copy.
    """
    path = Path(image)
    first = installed_sectors + 1
    if first > CORE_LAST_SECTOR:
        return
    length = (CORE_LAST_SECTOR - first + 1) * 512
    with open(path, "r+b") as handle:
        handle.seek(first * 512)
        remaining = length
        while remaining > 0:
            chunk = min(8 * 1024 * 1024, remaining)
            handle.write(b"\x00" * chunk)
            remaining -= chunk
        handle.flush()
        os.fsync(handle.fileno())
    with open(path, "rb") as handle:
        handle.seek(first * 512)
        remaining = length
        while remaining > 0:
            chunk = handle.read(min(8 * 1024 * 1024, remaining))
            if not chunk:
                raise BootchainError("core tail re-read is short")
            if any(chunk):
                raise BootchainError("core reservation tail did not zero")
            remaining -= len(chunk)


def install_genuine_grub_chain(image: Path, core: bytes) -> dict[str, object]:
    """Install genuine GRUB core bytes with matching MBR boot code.

    Capable-host companion to :func:`build_grub_core_via_mkimage`: derives
    the sector count from the supplied core length, builds the MBR stub
    with that exact loop bound aimed past ``diskboot`` at the kernel
    (entry sector 1), installs both, zeroes the
    reservation tail (sectors N+1..127) so the gap guard keeps proving
    exact bytes, and returns the ``core_sha256``/``core_sectors`` binding
    for the sector-2047 descriptor rebind (via
    ``embed_payload_descriptor``). Pure file-offset writes (no loop/mount,
    no privilege). Refuses non-sector-multiple, empty, or over-reservation
    cores fail-closed. Sector writes alone never claim a boot: the live
    Acer SeaBIOS run owns proving the genuine chain exits clean.
    """
    blob = bytes(core)
    if len(blob) % 512 or not blob:
        raise BootchainError("genuine core bytes must be a nonzero sector multiple")
    needed = len(blob) // 512
    if needed < CORE_FIRST_SECTOR or needed > CORE_LAST_SECTOR:
        raise BootchainError(
            f"genuine core ({needed} sectors) escapes the "
            f"1-{CORE_LAST_SECTOR} reservation"
        )
    mbr_sha = install_mbr_boot_code(
        Path(image), mbr_boot_stub_bytes(sectors=needed, entry_sector=1)
    )
    proof = install_grub_core_bytes(Path(image), blob)
    _zero_core_reservation_tail(Path(image), installed_sectors=needed)
    chain_bytes = MBR_BOOT_CODE_SIZE + needed * 512
    return {
        "mbr_stub_sha256": mbr_sha,
        "mbr_load_sectors": needed,
        "mbr_entry_sector": 1,
        "core_sha256": str(proof["core_sha256"]),
        "core_sectors": int(proof["core_sectors"]),
        "core_first_sector": CORE_FIRST_SECTOR,
        "core_last_reserved_sector": CORE_LAST_SECTOR,
        "chain_bytes": chain_bytes,
    }


def verify_mbr_boot_code(image: Path) -> dict[str, object]:
    """RED unless sector 0 carries real boot code + signature + table."""
    from greia_installer.layout import parse_dos_partition_table

    with open(Path(image), "rb") as handle:
        sector0 = handle.read(512)
    if len(sector0) != 512:
        raise BootchainError("image has no MBR sector to verify")
    code = sector0[:MBR_BOOT_CODE_SIZE]
    if not any(code):
        raise BootchainError(
            "MBR carries no boot code (chain-less image cannot produce a "
            "clean exit; refusing before any boot is claimed)"
        )
    if sector0[MBR_SIGNATURE_OFFSET] != 0x55 or sector0[511] != 0xAA:
        raise BootchainError("MBR boot signature is missing")
    parse_dos_partition_table(sector0)
    return {
        "present": True,
        "sha256": hashlib.sha256(code).hexdigest(),
        "bytes": MBR_BOOT_CODE_SIZE,
    }


def verify_boot_chain_present(image: Path) -> dict[str, object]:
    """RED unless the full chain is installed: MBR code + bound core.

    The MBR predicate is checked here; the core binding (installed core
    bytes hash to the relocated descriptor) and the gap-zero rule are
    checked through the payload gap guard, which owns gap semantics.
    """
    from tools.x8_qemu.payload import (
        read_payload_descriptor,
        verify_sector_gap_reserved,
    )

    mbr = verify_mbr_boot_code(Path(image))
    descriptor = read_payload_descriptor(Path(image))
    gap = verify_sector_gap_reserved(Path(image))
    return {"mbr": mbr, "descriptor": descriptor, "gap": gap}


# ---------------------------------------------------------------------------
# Guest grub.cfg composition (guest-only stanza, production seams untouched)
# ---------------------------------------------------------------------------

#: Guest-owned serial stanza, prepended before the production consumer
#: block. Emits COM1 progress bytes into the QEMU ``-serial file:`` log
#: as soon as genuine GRUB reads this config. Contains no menuentry, no
#: ``linux``/``initrd``/``search`` lines and none of the validator's
#: forbidden tokens, so the composed text still validates through the
#: production seam (pinned by test).
GUEST_SERIAL_PREAMBLE = (
    "# Greia guest serial stanza (tools/x8_qemu-owned; NOT production grub_ab).\n"
    "# Routes GRUB progress to COM1 so the per-leg QEMU -serial file: log\n"
    "# carries guest progress bytes for the progress-aware boot wait.\n"
    "serial --unit=0 --speed=115200 --word=8 --parity=no --stop=1\n"
    "terminal_output serial console\n"
    "echo 'Greia guest: serial console ready'\n"
)


def guest_exit_fallback(kernel_path: str = GRUB_KERNEL_PATH) -> str:
    """Bounded post-consumption exit stanza, appended after the entries.

    When the slot kernel is absent (disposable minimal image) there is
    nothing to boot: reboot instead of idling at a GRUB shell. QEMU
    ``-no-reboot`` turns guest reboot into process exit 0, which is what
    the clean-exit gate needs. The one-shot consumer block above still runs
    first, so genuine GRUB consumes ``next_entry`` before this fallback.
    """
    return (
        "\n# Greia guest exit stanza (tools/x8_qemu-owned; NOT production grub_ab).\n"
        "# Bounded fallback: without the slot kernel there is nothing to boot,\n"
        "# so reboot (QEMU -no-reboot turns this into process exit 0) instead\n"
        "# of idling at an interactive GRUB shell with no timeout.\n"
        f"if [ ! -e {kernel_path} ]; then\n"
        "  echo 'Greia guest: no slot kernel; rebooting'\n"
        "  reboot\n"
        "fi\n"
    )


def compose_guest_grub_cfg(production_text: str) -> str:
    """Prepend serial + append exit around the verbatim production block.

    ``production_text`` must be the exact ``render_grub_ab_config_from_record``
    output (validated by the caller through ``validate_grub_ab_text`` after
    composition). No ``src/greia_platform/grub_ab.py`` change is involved:
    guest-only bytes compose here in ``tools/x8_qemu`` per the brief.
    """
    if not isinstance(production_text, str) or not production_text:
        raise BootchainError("guest composition needs the production grub.cfg text")
    return GUEST_SERIAL_PREAMBLE + production_text + guest_exit_fallback()


# ---------------------------------------------------------------------------
# Progress-aware bounded boot wait
# ---------------------------------------------------------------------------


def _serial_bytes(path: Path) -> int:
    try:
        return int(Path(path).stat().st_size)
    except OSError:
        return 0


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(Path(path), "rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _terminate_process_tree(process: object) -> None:
    pid = int(getattr(process, "pid"))
    try:
        os.killpg(pid, _signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        return
    try:
        process.wait(timeout=BOOT_WAIT_KILL_GRACE_SECONDS)  # type: ignore[attr-defined]
    except Exception:
        try:
            os.killpg(pid, _signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
        try:
            process.wait()  # type: ignore[attr-defined]
        except Exception:
            pass


def wait_for_clean_exit(
    process: object,
    *,
    leg: str,
    qemu_log: Path,
    serial_log: Path | None = None,
    image: Path | None = None,
    image_sha_at_start: str | None = None,
    timeout_seconds: float,
    poll_seconds: float = BOOT_WAIT_POLL_SECONDS,
    no_progress_timeout: float = BOOT_WAIT_NO_PROGRESS_SECONDS,
    stall_timeout: float = BOOT_WAIT_STALL_SECONDS,
) -> dict[str, object]:
    """Wait for one QEMU boot with progress evidence and a hard ceiling.

    Progress evidence: growth of the per-leg ``-serial file:`` log
    (COM1 guest bytes) or a change of the disposable image SHA (guest disk
    writes; confirmed by full re-hash only when mtime/size moved, so polls
    stay cheap with no whole-image RAM copies held).

    Predicates (frozen, pinned by test):

    - the process exits 0 before the ceiling: PASS with the evidence;
    - the ceiling is reached first: RED (timeout);
    - ``no_progress_timeout`` passes with zero progress evidence: RED
      (silent images never go green, they just RED faster);
    - progress was observed but then stalls for ``stall_timeout``: RED
      (a guest that starts but never exits is not a clean boot).

    Fast capable-host behavior is unchanged: ``process.wait`` with the
    poll slice returns the moment the guest exits, so a quick clean boot
    costs no extra delay.
    """
    if timeout_seconds <= 0:
        raise BootchainError("boot wait needs a positive hard ceiling")
    serial_path = Path(serial_log) if serial_log is not None else None
    image_path = Path(image) if image is not None else None
    start = time.monotonic()
    deadline = start + float(timeout_seconds)
    last_progress = start
    progress_observed = False
    serial_start = _serial_bytes(serial_path) if serial_path is not None else 0
    serial_now = serial_start
    image_start_sha = image_sha_at_start
    image_stat: tuple[int, int] | None = None
    if image_path is not None and image_path.exists():
        st = image_path.stat()
        image_stat = (st.st_mtime_ns, st.st_size)
        if image_start_sha is None:
            image_start_sha = _sha256_file(image_path)
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            _terminate_process_tree(process)
            raise BootchainError(
                f"device boot leg {leg} exceeded the {timeout_seconds:g}s hard "
                f"ceiling; inspect {qemu_log} (unclean exit is RED)"
            )
        try:
            returncode = process.wait(timeout=min(poll_seconds, remaining))  # type: ignore[attr-defined]
        except Exception:
            returncode = None
        if returncode is not None:
            serial_end = _serial_bytes(serial_path) if serial_path is not None else 0
            sha_post: str | None = None
            if image_path is not None and image_path.exists():
                sha_post = _sha256_file(image_path)
                if image_start_sha is not None and sha_post != image_start_sha:
                    progress_observed = True
            if serial_end != serial_start:
                progress_observed = True
            return {
                "returncode": int(returncode),
                "serial_bytes": serial_end,
                "serial_growth_bytes": serial_end - serial_start,
                "progress_observed": progress_observed,
                "image_sha256_post": sha_post,
            }
        # Still running: sample progress evidence (cheap stats first).
        if serial_path is not None:
            grown = _serial_bytes(serial_path)
            if grown != serial_now:
                serial_now = grown
                last_progress = time.monotonic()
                progress_observed = True
        if image_path is not None and image_path.exists():
            st = image_path.stat()
            current = (st.st_mtime_ns, st.st_size)
            if image_stat is None or current != image_stat:
                image_stat = current
                if image_start_sha is not None:
                    if _sha256_file(image_path) != image_start_sha:
                        last_progress = time.monotonic()
                        progress_observed = True
                else:
                    last_progress = time.monotonic()
                    progress_observed = True
        idle = time.monotonic() - last_progress
        if not progress_observed and idle >= no_progress_timeout:
            _terminate_process_tree(process)
            raise BootchainError(
                f"device boot leg {leg} shows no progress evidence "
                f"({no_progress_timeout:g}s without serial-byte growth or "
                f"image change); inspect {qemu_log} (silent boot is RED)"
            )
        if progress_observed and idle >= stall_timeout:
            _terminate_process_tree(process)
            raise BootchainError(
                f"device boot leg {leg} stalled after progress "
                f"({stall_timeout:g}s without further serial bytes or image "
                f"change and no clean exit); inspect {qemu_log} "
                "(progress without exit is RED)"
            )


# ---------------------------------------------------------------------------
# Capable-host seam for genuine GRUB module bytes (gated, never green here)
# ---------------------------------------------------------------------------


def grub_mkimage_available(*, which=None) -> bool:
    """True only when genuine GRUB core tooling exists on this host."""
    finder = which or shutil.which
    return finder("grub-mkimage") is not None

#: File name of the embedded early config, written next to the mkimage
#: output and referenced via ``grub-mkimage -c``. Guest-owned bytes
#: (tools/x8_qemu), never production grub_ab.
EARLY_CONFIG_FILE_NAME = "early.cfg"

#: Embedded early config: brings COM1 up before normal mode loads, so
#: the per-leg serial log carries core progress (and any normal-load
#: failure lands on the serial console instead of a blind VGA rescue).
#: Runs before ``$prefix/grub.cfg``; the main config re-asserts the
#: serial stanza idempotently. Uses only embedded modules.
GUEST_EARLY_CONFIG = (
    "# Greia guest early config (tools/x8_qemu-owned; embedded via -c).\n"
    "serial --unit=0 --speed=115200 --word=8 --parity=no --stop=1\n"
    "terminal_output serial console\n"
    "echo 'Greia core: early serial ready'\n"
)


def grub_mkimage_argv(
    *, output: Path, prefix: str = "(,msdos1)/", modules: tuple[str, ...] = ()
) -> list[str]:
    """Pure argv for a genuine i386-pc core with the required modules.

    The default prefix names the boot device implicitly (``,`` = the
    BIOS boot drive in DL, preserved for the core entry by the MBR
    stub) and partition 1 explicitly (``msdos1``), resolved at the
    partition ROOT (``/``): genuine GRUB therefore consumes the ROOT
    ``grub.cfg``/``grubenv`` — the exact paths the frozen attestation
    seam (`GrubEnvBackend.attach(mountpoint).inspect()`) and the
    legacy stub-core layout already use, so no root/prefix split
    exists to drift. A bare ``/boot/grub`` prefix would resolve on the
    raw drive (no filesystem) and drop the core into a serial-blind
    rescue with no consumption; a ``/boot/grub``-suffixed prefix
    works but strands consumption on a mirror copy the seam never
    reads (live-observed: prefix copy consumed while root stayed
    armed). The production consumer block is ``$prefix``-relative, so
    it stays byte-verbatim under either prefix. Live-proven on the
    Acer with an armed-leg consumption delta at the root path.

    Split-core architecture (Acer-measured): ``normal.mod`` alone is
    ~115 KiB, so no normal-mode core fits the 127-sector (65024-byte)
    gap reservation. The embedded set is therefore the minimal
    disk-reaching core — serial progress (``serial``), one-shot
    consume/persist (``loadenv``, the module behind the
    ``load_env``/``save_env`` commands), bounded exit (``reboot``/``halt``),
    terminal for the serial stanza (``terminal``), disk access
    (``biosdisk`` + ``part_msdos``), the ext2/3/4 driver (``ext2`` —
    there is no ``ext4.mod``), and script builtins (``test`` for the
    ``[ -e ]`` fallback, ``echo``) — measured ~57 KiB / 114 sectors.
    ``normal`` and its dependency closure load from
    ``$prefix/i386-pc/`` on partition 1 at boot (standard GRUB
    behavior, proven by the live leg); the partition copy is placed by
    the install path alongside the ``/i386-pc`` module closure. An
    embedded early config (``-c``) brings COM1 up first so even a
    failed normal-load leaves serial diagnostics. No execution here:
    the caller gates on :func:`grub_mkimage_available`.
    """
    selected = modules or (
        "serial",
        "loadenv",
        "reboot",
        "halt",
        "terminal",
        "biosdisk",
        "part_msdos",
        "ext2",
        "test",
        "echo",
    )
    return [
        "grub-mkimage",
        "-O",
        "i386-pc",
        "-o",
        str(output),
        "-p",
        prefix,
        "-c",
        str(Path(str(output)).parent / EARLY_CONFIG_FILE_NAME),
        *selected,
    ]


def build_grub_core_via_mkimage(
    *, output: Path, prefix: str = "(,msdos1)/", modules: tuple[str, ...] = ()
) -> dict[str, object]:
    """Build a genuine GRUB core on a capable host (fail-closed elsewhere).

    Requires ``grub-mkimage`` (``grub-pc-bin`` per
    ``build/package-sets/boot-grub-pc.txt``) and refuses when the produced
    core exceeds the ``CORE_FIRST_SECTOR``-``CORE_LAST_SECTOR`` reservation
    or the tool is absent. Writes the embedded early config
    (``GUEST_EARLY_CONFIG``) next to the output before invoking mkimage.
    Source scope on this tool-less host REDs here by design; the stub
    core installed by :func:`install_boot_chain` remains the
    source-scope chain.
    """
    if not grub_mkimage_available():
        raise BootchainError(
            "genuine GRUB core needs grub-mkimage on a capable host "
            "(grub-pc-bin); source scope keeps the reviewed stub core"
        )
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    (Path(output).parent / EARLY_CONFIG_FILE_NAME).write_text(
        GUEST_EARLY_CONFIG, encoding="utf-8"
    )
    argv = grub_mkimage_argv(output=Path(output), prefix=prefix, modules=modules)
    completed = subprocess.run(argv, capture_output=True, text=True, timeout=120)
    if completed.returncode != 0:
        tail = (completed.stderr or "")[-1500:]
        raise BootchainError(
            f"grub-mkimage failed with status {completed.returncode}: {tail}"
        )
    size = Path(output).stat().st_size
    reservation = (CORE_LAST_SECTOR - CORE_FIRST_SECTOR + 1) * 512
    if size <= 0 or size > reservation:
        raise BootchainError(
            f"genuine GRUB core ({size} bytes) escapes the {reservation}-byte "
            "gap reservation"
        )
    return {
        "path": str(output),
        "bytes": size,
        "sha256": _sha256_file(Path(output)),
        "modules": list(modules) if modules else "default-set",
    }


def pad_core_bytes_to_sectors(core: bytes) -> bytes:
    """Pad raw ``grub-mkimage`` bytes up to a whole-sector multiple.

    mkimage output is not sector-aligned (e.g. 57870 bytes); the gap
    installers require exact sector multiples. Zero-pads up (never
    truncates); refuses empty input fail-closed. The padded length
    still must fit the ``CORE_FIRST_SECTOR``-``CORE_LAST_SECTOR``
    reservation — enforced by the installers, not here.
    """
    blob = bytes(core)
    if not blob:
        raise BootchainError("genuine core bytes must be nonzero")
    remainder = len(blob) % 512
    if remainder:
        blob = blob + b"\x00" * (512 - remainder)
    return blob


def install_grub_core_bytes(
    image: Path, core: bytes, *, sectors: int | None = None
) -> dict[str, object]:
    """Install caller-supplied (genuine) core bytes into the reservation.

    Capable-host companion to :func:`build_grub_core_via_mkimage`: writes
    sectors 1..N (N derived from the byte length unless ``sectors`` pins
    it), zeroes the remainder of the reservation so the gap guard keeps
    proving exact bytes, and returns the binding for the descriptor
    rebind. Must be paired with matching MBR boot code via
    :func:`install_mbr_boot_code`; sector writes alone never claim a boot.
    """
    blob = bytes(core)
    if len(blob) % 512 or not blob:
        raise BootchainError("genuine core bytes must be a nonzero sector multiple")
    needed = len(blob) // 512
    count = sectors if sectors is not None else needed
    if count < needed or count > CORE_LAST_SECTOR:
        raise BootchainError(
            f"core sector count {count} cannot hold {needed} sectors inside "
            f"the 1-{CORE_LAST_SECTOR} reservation"
        )
    padded = blob + b"\x00" * ((count - needed) * 512)
    digest = install_core_region(Path(image), padded, sectors=count)
    return {"core_sha256": digest, "core_sectors": count, "core_bytes": len(padded)}
