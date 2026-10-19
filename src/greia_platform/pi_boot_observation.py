"""Read-only Raspberry Pi firmware boot evidence for native A/B acceptance.

This module does not switch slots or confirm that the mounted root belongs to
this disk. It decodes firmware device-tree properties and cross-checks the
boot partition, one-shot flag and Linux root= hint against an installed
layout's *observed* PARTUUIDs. A production health/commit backend must also
verify actual mounted root and boot-device ancestry before accepting.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .persistent_layout import normalize_mbr_partuuid, split_mbr_partuuid
from .pi_boot_assets import parse_pi_autoboot


class PiBootObservationError(RuntimeError):
    """Missing, malformed, or contradictory Pi firmware boot evidence."""


def _read_u32_be(path: Path) -> int:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise PiBootObservationError(f"cannot read firmware property {path.name}") from exc
    if len(data) != 4:
        raise PiBootObservationError(f"firmware property {path.name} must contain 4 binary bytes")
    return int.from_bytes(data, "big")


def _root_partuuid_from_cmdline(cmdline: str) -> str:
    roots = [word[5:] for word in cmdline.split() if word.startswith("root=")]
    if len(roots) != 1 or not roots[0].startswith("PARTUUID="):
        raise PiBootObservationError("cmdline must specify exactly one root=PARTUUID=")
    try:
        return normalize_mbr_partuuid(roots[0][9:], field="cmdline root")
    except Exception as exc:
        raise PiBootObservationError("cmdline root is not an MBR PARTUUID") from exc


@dataclass(frozen=True, slots=True)
class PiBootObservation:
    """Firmware's boot selection and the kernel root parameter, not health."""

    firmware_boot_partition: int
    firmware_tryboot: bool
    kernel_root_partuuid: str

    @classmethod
    def read(
        cls,
        *,
        bootloader_properties: Path = Path("/proc/device-tree/chosen/bootloader"),
        cmdline_file: Path = Path("/proc/cmdline"),
    ) -> "PiBootObservation":
        props = Path(bootloader_properties)
        part = _read_u32_be(props / "partition")
        trial = _read_u32_be(props / "tryboot")
        if part not in (2, 3):
            raise PiBootObservationError("firmware booted outside Pi A/B FAT partitions")
        if trial not in (0, 1):
            raise PiBootObservationError("firmware tryboot property is neither 0 nor 1")
        try:
            cmdline = Path(cmdline_file).read_text(encoding="ascii")
        except (OSError, UnicodeDecodeError) as exc:
            raise PiBootObservationError("cannot read kernel boot command line") from exc
        return cls(part, bool(trial), _root_partuuid_from_cmdline(cmdline))

    def checked_slot(
        self,
        *,
        autoboot_text: str,
        system_a_partuuid: str,
        system_b_partuuid: str,
    ) -> str:
        """Return observed selected slot only if firmware, config and root hint agree.

        The returned slot is NOT sufficient for a health-based commit: mount
        ancestry, accepted update receipt, boot file digests and Shell health
        must be checked separately by the future production transaction.
        """
        try:
            accepted = parse_pi_autoboot(autoboot_text)
            a = normalize_mbr_partuuid(system_a_partuuid, field="system A")
            b = normalize_mbr_partuuid(system_b_partuuid, field="system B")
            disk_a, part_a = split_mbr_partuuid(a)
            disk_b, part_b = split_mbr_partuuid(b)
        except Exception as exc:
            raise PiBootObservationError("installed boot control or system identities are invalid") from exc
        if disk_a != disk_b or part_a != 5 or part_b != 6:
            raise PiBootObservationError("system A/B roots are not P5/P6 on the same MBR disk")
        selected = ("B" if accepted == "A" else "A") if self.firmware_tryboot else accepted
        expected_boot = 2 if selected == "A" else 3
        expected_root = a if selected == "A" else b
        if self.firmware_boot_partition != expected_boot:
            raise PiBootObservationError("firmware boot partition contradicts one-shot A/B map")
        if self.kernel_root_partuuid != expected_root:
            raise PiBootObservationError("kernel root PARTUUID contradicts firmware boot slot")
        return selected
