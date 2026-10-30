"""Single-root disk layouts and EFI boot for the whole-disk installer.

Status: UNPROVEN / LAB. No Intel Mac (or any EFI machine) has booted this code
path; it implements the documented theory in
``2026-10-21_PRE_M1_MAC_HARDWARE_SUPPORT.md`` (archived; see git history) and
``docs/engineering/boot/INSTALLER_IMAGE_CREATION_AND_BOOT.md`` ("Intel Mac / UEFI boot").

Two substitutable layouts share one small contract (:class:`SingleRootLayout`):

* :class:`BiosSingleExt4Layout` - the historical MBR + one ext4 partition.
  Its command list is byte-for-byte what the engine ran before this module
  existed, so every BIOS machine (the Acer reference included) is unchanged.
* :class:`UefiOrBiosGptExt4Layout` (``uefi-or-bios-gpt-ext4``) - GPT with a
  1 MiB ``bios_grub`` partition, a 256 MiB FAT32 ESP and the root ext4. It is
  selected only when the live installer itself booted through EFI.

Everything here is pure planning: argument arrays only (never a shell string),
no I/O except reading sysfs/cpuinfo/profile files through injectable paths.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

from .disk import partition_number_path

MIB = 1024 * 1024

BIOS_LAYOUT_ID = "bios-single-ext4"
UEFI_OR_BIOS_LAYOUT_ID = "uefi-or-bios-gpt-ext4"

#: Package set (ADR 0013) that makes a target image EFI-bootable. The installer
#: only selects the EFI layout when the target profile composed this set.
EFI_PACKAGE_SET = "boot-grub-efi"

ESP_LABEL = "GREIA_EFI"
ESP_MOUNT_IN_TARGET = "/boot/efi"
ESP_SIZE_MIB = 256
BIOS_GRUB_SIZE_MIB = 1
NVRAM_LABEL = "Greia OS"
BOOTLOADER_ID = "greia"


class EfiBootError(RuntimeError):
    """Firmware/layout planning failed closed."""


# ---------------------------------------------------------------------------
# Firmware detection
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class FirmwareInterface:
    """How the *live installer* was booted (not what the disk supports)."""

    uefi: bool
    #: EFI word size (32 or 64); ``None`` when ``uefi`` is false.
    efi_bits: int | None = None

    def __post_init__(self) -> None:
        if self.uefi and self.efi_bits not in (32, 64):
            raise EfiBootError("EFI firmware must report 32 or 64 bits")
        if not self.uefi and self.efi_bits is not None:
            raise EfiBootError("BIOS firmware cannot carry an EFI word size")

    @property
    def grub_efi_target(self) -> str:
        if not self.uefi:
            raise EfiBootError("BIOS firmware has no GRUB EFI target")
        return "i386-efi" if self.efi_bits == 32 else "x86_64-efi"

    @property
    def native_loader(self) -> str:
        """Filename of the GRUB image grub-install writes for this firmware."""
        return "grubia32.efi" if self.efi_bits == 32 else "grubx64.efi"


@dataclass(frozen=True, slots=True)
class SysfsFirmwareProbe:
    """Detect EFI and its bitness from ``/sys/firmware/efi``.

    ``fw_platform_size`` appeared in Linux 4.0. A missing file on an EFI boot
    (older kernels) is treated as 64-bit unless ``/proc/cpuinfo`` lacks the
    ``lm`` flag, in which case the machine cannot be 64-bit EFI.
    """

    efi_root: Path = Path("/sys/firmware/efi")
    cpuinfo: Path = Path("/proc/cpuinfo")

    def probe(self) -> FirmwareInterface:
        try:
            if not self.efi_root.is_dir():
                return FirmwareInterface(uefi=False)
        except OSError:
            return FirmwareInterface(uefi=False)
        try:
            text = (self.efi_root / "fw_platform_size").read_text(encoding="ascii").strip()
        except (OSError, UnicodeDecodeError):
            text = ""
        if text == "32":
            return FirmwareInterface(uefi=True, efi_bits=32)
        if text == "64":
            return FirmwareInterface(uefi=True, efi_bits=64)
        # Unreadable or unexpected value: fall back to the documented rule.
        return FirmwareInterface(
            uefi=True, efi_bits=64 if self._cpu_has_long_mode() else 32
        )

    def _cpu_has_long_mode(self) -> bool:
        try:
            for line in self.cpuinfo.read_text(encoding="utf-8", errors="replace").splitlines():
                if line.startswith("flags"):
                    return "lm" in line.split(":", 1)[-1].split()
        except OSError:
            pass
        # Unknown CPU: assume the common modern case.
        return True


def target_profile_supports_efi(profile_manifest: Path) -> bool:
    """True when the target image profile composed the EFI package set."""
    try:
        data = json.loads(profile_manifest.read_text(encoding="utf-8"))
        sets = data["package_sets"]["target"]
    except (OSError, ValueError, KeyError, TypeError):
        return False
    return isinstance(sets, list) and EFI_PACKAGE_SET in sets


# ---------------------------------------------------------------------------
# Layouts
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class SingleRootPartition:
    number: int
    role: str
    filesystem: str  # "ext4" | "fat32" | "none"
    start_mib: int
    end_mib: int | None  # None = to the end of the disk
    flags: tuple[str, ...] = ()
    name: str = ""


class SingleRootLayout(ABC):
    """Whole-disk layout with exactly one Greia root filesystem."""

    @property
    @abstractmethod
    def adapter_id(self) -> str: ...

    @property
    @abstractmethod
    def partitions(self) -> tuple[SingleRootPartition, ...]: ...

    @property
    def uses_efi(self) -> bool:
        return False

    def root_partition(self, device: Path) -> Path:
        return partition_number_path(device, self.number_of("root"))

    def esp_partition(self, device: Path) -> Path:
        raise EfiBootError(f"layout {self.adapter_id} has no EFI System Partition")

    def number_of(self, role: str) -> int:
        for part in self.partitions:
            if part.role == role:
                return part.number
        raise EfiBootError(f"layout {self.adapter_id} has no {role} partition")

    @abstractmethod
    def partition_commands(self, device: Path) -> list[list[str]]:
        """Label + partition commands (after ``wipefs``, before ``partprobe``)."""

    def format_commands(self, device: Path) -> list[list[str]]:
        """Commands formatting every non-root filesystem (root is formatted by the engine)."""
        return []


class BiosSingleExt4Layout(SingleRootLayout):
    """MBR + one ext4 partition; identical to the pre-EFI installer."""

    adapter_id = BIOS_LAYOUT_ID
    partitions = (
        SingleRootPartition(1, "root", "ext4", 1, None, ("boot",)),
    )

    def partition_commands(self, device: Path) -> list[list[str]]:
        dev = str(device)
        return [
            ["parted", "--script", dev, "mklabel", "msdos"],
            ["parted", "--script", dev, "mkpart", "primary", "ext4", "1MiB", "100%"],
            ["parted", "--script", dev, "set", "1", "boot", "on"],
        ]


class UefiOrBiosGptExt4Layout(SingleRootLayout):
    """GPT: 1 MiB bios_grub + 256 MiB FAT32 ESP + root ext4 (UNPROVEN / LAB).

    The bios_grub partition lets the same disk also boot through a BIOS/CSM
    path (Boot Camp style legacy boot); the ESP carries the removable-path
    GRUB images so firmware that ignores NVRAM (Apple) still finds them.
    """

    adapter_id = UEFI_OR_BIOS_LAYOUT_ID
    uses_efi = True
    partitions = (
        SingleRootPartition(1, "bios-boot", "none", 1, 1 + BIOS_GRUB_SIZE_MIB,
                            ("bios_grub",), "bios-boot"),
        SingleRootPartition(2, "esp", "fat32", 1 + BIOS_GRUB_SIZE_MIB,
                            1 + BIOS_GRUB_SIZE_MIB + ESP_SIZE_MIB, ("esp",), "esp"),
        SingleRootPartition(3, "root", "ext4", 1 + BIOS_GRUB_SIZE_MIB + ESP_SIZE_MIB,
                            None, ("legacy_boot",), "greia-root"),
    )

    def esp_partition(self, device: Path) -> Path:
        return partition_number_path(device, self.number_of("esp"))

    def partition_commands(self, device: Path) -> list[list[str]]:
        dev = str(device)
        commands: list[list[str]] = [["parted", "--script", dev, "mklabel", "gpt"]]
        for part in self.partitions:
            end = "100%" if part.end_mib is None else f"{part.end_mib}MiB"
            fs = {"ext4": "ext4", "fat32": "fat32", "none": ""}[part.filesystem]
            mkpart = ["parted", "--script", dev, "mkpart", part.name]
            if fs:
                mkpart.append(fs)
            mkpart += [f"{part.start_mib}MiB", end]
            commands.append(mkpart)
            for flag in part.flags:
                commands.append(
                    ["parted", "--script", dev, "set", str(part.number), flag, "on"]
                )
        return commands

    def format_commands(self, device: Path) -> list[list[str]]:
        return [["mkfs.vfat", "-F", "32", "-n", ESP_LABEL, str(self.esp_partition(device))]]


@dataclass(frozen=True, slots=True)
class SingleRootLayoutSelector:
    """Choose the layout from the live firmware and target capability."""

    def select(self, firmware: FirmwareInterface, *, target_supports_efi: bool) -> SingleRootLayout:
        if firmware.uefi and target_supports_efi:
            return UefiOrBiosGptExt4Layout()
        return BiosSingleExt4Layout()


# ---------------------------------------------------------------------------
# Boot loader commands (run inside the target chroot)
# ---------------------------------------------------------------------------

def bios_grub_install_command(
    device: Path, *, boot_directory: Path | None = None
) -> list[str]:
    """Build the BIOS GRUB install argv for a whole disk.

    The historical single-root path calls this without ``boot_directory``
    and retains its chroot command byte-for-byte. Fresh A/B installs pass the
    currently mounted, verified boot-control filesystem path so GRUB's core
    image and modules land beside the shared ``grub.cfg`` and ``grubenv``.
    """
    if boot_directory is None:
        return [
            "chroot", "{root}", "grub-install", "--target=i386-pc",
            "--boot-directory=/boot", "--recheck", str(device),
        ]
    if not isinstance(device, Path) or not device.is_absolute():
        raise EfiBootError("BIOS GRUB target must be an absolute whole-disk path")
    if not isinstance(boot_directory, Path) or not boot_directory.is_absolute():
        raise EfiBootError("BIOS GRUB boot directory must be an absolute mounted path")
    return [
        "grub-install", "--target=i386-pc", "--boot-directory",
        str(boot_directory), "--recheck", str(device),
    ]


def _efi_install(target: str, extra: tuple[str, ...]) -> list[str]:
    return [
        "chroot", "{root}", "grub-install", f"--target={target}",
        f"--efi-directory={ESP_MOUNT_IN_TARGET}", "--boot-directory=/boot",
        "--no-nvram", *extra,
    ]


@dataclass(frozen=True, slots=True)
class EfiBootPlan:
    """Ordered GRUB/NVRAM commands for one EFI install.

    ``{root}`` in a command is replaced with the mounted target path by the
    engine (kept symbolic so the plan is testable without a temp mount).
    Fatal commands abort the install; ``best_effort`` ones never do, because
    some Macs ignore NVRAM entries and some early Apple EFI refuse efibootmgr.
    """

    fatal: tuple[tuple[str, ...], ...]
    best_effort: tuple[tuple[str, ...], ...] = field(default=())


def plan_efi_boot(firmware: FirmwareInterface, device: Path, esp_number: int) -> EfiBootPlan:
    """Native GRUB, then both removable-path fallbacks, then NVRAM (optional).

    The removable images (``EFI/BOOT/BOOTIA32.EFI`` and ``BOOTX64.EFI``) are
    both written regardless of the firmware width, so a disk moved between
    Macs of either EFI width still boots. Whether x64 EFI GRUB can start the
    i686 kernel on 2008+ 64-bit-EFI Macs is an open LAB question.
    """
    native = firmware.grub_efi_target
    fatal = [
        _efi_install(native, ("--bootloader-id=" + BOOTLOADER_ID, "--recheck")),
        _efi_install("i386-efi", ("--removable",)),
        _efi_install("x86_64-efi", ("--removable",)),
    ]
    loader = "\\EFI\\" + BOOTLOADER_ID + "\\" + firmware.native_loader
    nvram = (
        "chroot", "{root}", "efibootmgr", "--create", "--disk", str(device),
        "--part", str(esp_number), "--label", NVRAM_LABEL, "--loader", loader,
    )
    # Bonus BIOS/CSM path through the bios_grub partition; never fatal.
    legacy = tuple(bios_grub_install_command(device))
    return EfiBootPlan(
        fatal=tuple(tuple(c) for c in fatal),
        best_effort=(nvram, legacy),
    )


def required_efi_binaries(firmware: FirmwareInterface) -> tuple[str, ...]:
    """Paths (relative to the ESP) that must exist after a successful install."""
    return (
        "EFI/BOOT/BOOTIA32.EFI",
        "EFI/BOOT/BOOTX64.EFI",
        "EFI/" + BOOTLOADER_ID + "/" + firmware.native_loader,
    )
