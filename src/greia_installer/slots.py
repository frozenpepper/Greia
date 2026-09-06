"""Installer binding to the shared platform slot writer/finalizer seam.

L7-SLOTS: the updater and the installer call the same platform-owned
implementation (``greia_platform.slot_writer``). This module only adapts the
already-verified installer hardware logic to the shared protocols instead of
copying it: the release-bound support set converts from
``VerifiedHardwareSupportPool``, and package installation delegates to
``TargetHardwareSupportInstaller``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from greia_platform.slot_writer import (
    InstalledPackage,
    ReleaseSupportSet,
    SlotFinalizer,
    SlotWriter,
    VerifiedBaseSlotWrite,
)

from .hardware_support import VerifiedHardwareSupportPool
from .hardware_support_install import (
    HardwareSupportCommandRunner,
    TargetHardwareSupportInstaller,
)


__all__ = [
    "SlotWriter",
    "SlotFinalizer",
    "VerifiedBaseSlotWrite",
    "InstalledPackage",
    "pool_to_support_set",
    "InstallerSlotPackageInstaller",
]


def pool_to_support_set(
    pool: VerifiedHardwareSupportPool,
    *,
    support_digest: str,
    support_size: int,
) -> ReleaseSupportSet:
    """Convert an already-verified pool into the release-bound support set.

    ``support_digest``/``support_size`` are the signed hardware-support member
    facts from the release manifest; the pool itself was verified at load.
    Package classes come from the pool's own verified classification, so
    firmware can never be reclassified as microcode here.
    """
    records: list[InstalledPackage] = []
    for entry in pool.packages:
        if entry.package in pool.provided_firmware:
            kind = "firmware"
        elif entry.package in pool.provided_microcode:
            kind = "microcode"
        else:
            continue
        records.append(
            InstalledPackage(
                name=entry.package,
                version=entry.version,
                architecture=entry.architecture,
                sha256=entry.sha256,
                kind=kind,
            )
        )
    records.sort(key=lambda item: item.name)
    return ReleaseSupportSet(
        support_digest=support_digest,
        support_size=support_size,
        installed_size_bound=pool.total_bytes,
        provided_firmware=frozenset(pool.provided_firmware),
        provided_microcode=frozenset(pool.provided_microcode),
        packages=tuple(records),
    )


@dataclass(slots=True)
class InstallerSlotPackageInstaller:
    """Shared-protocol installer reusing ``TargetHardwareSupportInstaller``.

    The caller owns the target/chroot lifecycle (``target_root`` plus the
    shared ``mounted`` cleanup list); this adapter only routes the
    finalizer-approved firmware/microcode sets through the existing installer
    path. No support logic is copied here.
    """

    runner: HardwareSupportCommandRunner
    target_root: Path
    pool: VerifiedHardwareSupportPool
    mounted: list[Path]

    def install(
        self,
        firmware: tuple[str, ...],
        microcode: tuple[str, ...],
    ) -> tuple[InstalledPackage, ...]:
        wanted_firmware = self.pool.require_firmware(firmware)
        wanted_microcode = self.pool.require_microcode(microcode)
        requested = (*wanted_firmware, *wanted_microcode)
        if not requested:
            return ()
        installer = TargetHardwareSupportInstaller(self.runner)
        installed = installer.install(
            target_root=self.target_root,
            pool=self.pool,
            packages=requested,
            mounted=self.mounted,
        )
        support = pool_to_support_set(
            self.pool,
            support_digest="0" * 64,
            support_size=1,
        )
        return tuple(support.record_for(name) for name in installed)
