"""Raspberry Pi native A/B firmware boot-asset staging.

Board-specific FAT boot files are composed offline from the *finalized* Greia
system-slot and a pinned firmware/DTB asset directory. No block device is
addressed here. A production installer must verify the staged content, write
the correct FAT partition, flush it and mount/re-read before authorizing boot.

This source module deliberately refuses missing, mismatched or symlinked
inputs instead of silently substituting another Pi model.
"""

from __future__ import annotations

import hashlib
import os
import shutil
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from .boot_transaction import BootArtifactSet
from .persistent_layout import split_mbr_partuuid

MIB = 1024 * 1024
PI_BOOT_PARTITION_BYTES = 256 * MIB
PI_BOOT_REQUIRED_FREE_BYTES = 32 * MIB
PI_BOOT_MAX_USED_BYTES = PI_BOOT_PARTITION_BYTES - PI_BOOT_REQUIRED_FREE_BYTES


class PiBootAssetError(RuntimeError):
    """Board boot assets are absent, ambiguous or not bound to a release."""


class PiBoard(StrEnum):
    PI_400 = "pi-400-v1"
    PI_500 = "pi-500-v1"

    @property
    def firmware_filter(self) -> str:
        return "[pi400]" if self is PiBoard.PI_400 else "[pi500]"

    @property
    def kernel_filename(self) -> str:
        return "kernel8.img" if self is PiBoard.PI_400 else "kernel_2712.img"

    @property
    def dtb_filename(self) -> str:
        return (
            "bcm2711-rpi-400.dtb"
            if self is PiBoard.PI_400 else "bcm2712-rpi-500.dtb"
        )

    @property
    def kms_overlay(self) -> str:
        return "vc4-kms-v3d" if self is PiBoard.PI_400 else "vc4-kms-v3d-pi5"


@dataclass(frozen=True, slots=True)
class PiBootAssetReceipt:
    board: PiBoard
    slot: str
    root_partuuid: str
    boot_partition: int
    files: tuple[tuple[str, str], ...]
    total_bytes: int


def _require_regular(path: Path) -> Path:
    if path.is_symlink() or not path.is_file():
        raise PiBootAssetError(f"boot source must be a regular, non-symlink file: {path}")
    if path.stat().st_size <= 0:
        raise PiBootAssetError(f"boot source is empty: {path}")
    return path


def _digest(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            sha.update(chunk)
    return sha.hexdigest()


def render_pi_boot_config(board: PiBoard) -> str:
    """Use model-exclusive firmware filters and a full KMS display backend."""
    if not isinstance(board, PiBoard):
        raise PiBootAssetError("unsupported or unknown Raspberry Pi board")
    return (
        f"{board.firmware_filter}\n"
        "arm_64bit=1\n"
        f"kernel={board.kernel_filename}\n"
        "initramfs initramfs.img followkernel\n"
        f"dtoverlay={board.kms_overlay}\n"
        "[all]\n"
    )


def render_pi_cmdline(artifacts: BootArtifactSet) -> str:
    """Each BOOT partition must reference its own observed system PARTUUID."""
    if not isinstance(artifacts, BootArtifactSet):
        raise PiBootAssetError("boot config requires a finalized release artifact")
    if artifacts.boot_backend != "pi-tryboot-ab-v1":
        raise PiBootAssetError("x86 GRUB artifacts cannot produce Pi boot files")
    if artifacts.layout_id != "pi-mbr-tryboot-ab-v1":
        raise PiBootAssetError("Pi boot requires the native MBR slot layout")
    try:
        _, number = split_mbr_partuuid(artifacts.root_partuuid)
    except Exception as exc:
        raise PiBootAssetError("Pi root PARTUUID is not an observed DOS identity") from exc
    expected = 5 if artifacts.slot == "A" else 6
    if number != expected:
        raise PiBootAssetError("Pi boot slot does not match its system root partition")
    return (
        artifacts.kernel_cmdline_root()
        + " rootfstype=ext4 rootwait ro quiet loglevel=0 "
        "vt.global_cursor_default=0\n"
    )


def render_pi_autoboot(default_slot: str) -> str:
    """Actual Raspberry Pi firmware A/B map, NOT the old fake-backend format."""
    if default_slot not in ("A", "B"):
        raise PiBootAssetError("Pi default boot slot must be A or B")
    normal, trial = (2, 3) if default_slot == "A" else (3, 2)
    return (
        f"[all]\ntryboot_a_b=1\nboot_partition={normal}\n"
        f"[tryboot]\nboot_partition={trial}\n[all]\n"
    )


def parse_pi_autoboot(text: str) -> str:
    for slot in ("A", "B"):
        if text == render_pi_autoboot(slot):
            return slot
    raise PiBootAssetError("Pi autoboot.txt is not the canonical one-shot A/B mapping")


class PiBootAssetStager:
    """Prepare one release-bound slot in an empty, disposable staging folder.

    The caller supplies a finalized-slot root, already-selected Pi-specific
    firmware assets (including matching DTB and overlays), and an empty
    output folder. The stager never guesses firmware paths or downloads files.
    """

    def stage(
        self,
        *,
        board: PiBoard,
        artifacts: BootArtifactSet,
        system_root: Path,
        firmware_root: Path,
        destination: Path,
    ) -> PiBootAssetReceipt:
        config = render_pi_boot_config(board)
        cmdline = render_pi_cmdline(artifacts)
        system_root = Path(system_root)
        firmware_root = Path(firmware_root)
        destination = Path(destination)
        if destination.is_symlink() or not destination.is_dir():
            raise PiBootAssetError("destination must be a real, existing staging directory")
        if any(destination.iterdir()):
            raise PiBootAssetError("destination must be empty; refusing to overwrite boot files")
        if firmware_root.is_symlink() or not firmware_root.is_dir():
            raise PiBootAssetError("firmware asset root must be an ordinary directory")

        kernel = _require_regular(system_root / artifacts.kernel_path)
        initramfs = _require_regular(system_root / artifacts.initramfs_path)
        if _digest(kernel) != artifacts.generic_kernel_sha256:
            raise PiBootAssetError("kernel does not match finalized release receipt")
        if _digest(initramfs) != artifacts.generic_initramfs_sha256:
            raise PiBootAssetError("initramfs does not match finalized release receipt")

        board_files: dict[str, Path] = {
            board.dtb_filename: _require_regular(firmware_root / board.dtb_filename),
        }
        if board is PiBoard.PI_400:
            for name in ("start4.elf", "fixup4.dat"):
                board_files[name] = _require_regular(firmware_root / name)
        overlay_root = firmware_root / "overlays"
        overlay = f"{board.kms_overlay}.dtbo"
        if overlay_root.is_symlink() or not overlay_root.is_dir():
            raise PiBootAssetError("Pi KMS overlay directory is missing or symlinked")
        board_files[f"overlays/{overlay}"] = _require_regular(overlay_root / overlay)

        sources = {
            board.kernel_filename: kernel,
            "initramfs.img": initramfs,
            **board_files,
        }
        total_bytes = sum(source.stat().st_size for source in sources.values())
        total_bytes += len(config.encode("utf-8")) + len(cmdline.encode("utf-8"))
        if total_bytes > PI_BOOT_MAX_USED_BYTES:
            raise PiBootAssetError("Pi boot files exceed the 256 MiB FAT minus 32 MiB reserve")

        # All source validation and capacity accounting precedes the first
        # write. This only stages to a disposable directory, never to media.
        for relative, source in sources.items():
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        (destination / "config.txt").write_text(config, encoding="utf-8")
        (destination / "cmdline.txt").write_text(cmdline, encoding="utf-8")
        digests = tuple(
            (name, _digest(destination / name))
            for name in sorted((*sources, "config.txt", "cmdline.txt"))
        )
        for name, source in sources.items():
            if _digest(destination / name) != _digest(source):
                raise PiBootAssetError(f"staged boot file changed in transit: {name}")
        return PiBootAssetReceipt(
            board=board,
            slot=artifacts.slot,
            root_partuuid=artifacts.root_partuuid,
            boot_partition=2 if artifacts.slot == "A" else 3,
            files=digests,
            total_bytes=total_bytes,
        )
