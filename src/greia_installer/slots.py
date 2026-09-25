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
from typing import Protocol

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
    HardwareSupportInstallError,
    TargetHardwareSupportInstaller,
    detach_recorded_mounts,
)


__all__ = [
    "SlotWriter",
    "SlotFinalizer",
    "VerifiedBaseSlotWrite",
    "InstalledPackage",
    "pool_to_support_set",
    "InstallerSlotPackageInstaller",
    "InstallerPoolBindCleanupPackageInstaller",
]


class SlotPackageInstallInner(Protocol):
    """Narrow install protocol wrapped by the pool-bind cleanup wrapper.

    Satisfied structurally by both ``InstallerSlotPackageInstaller`` and
    the shared ``SharedSlotPackageInstaller`` (identical ``install``
    shape); kept local so this module never imports the platform package
    at top level (platform imports this module for the shared installer).
    """

    def install(
        self,
        firmware: tuple[str, ...],
        microcode: tuple[str, ...],
    ) -> tuple[InstalledPackage, ...]: ...


def pool_to_support_set(
    pool: VerifiedHardwareSupportPool,
    *,
    support_digest: str,
    support_size: int,
) -> ReleaseSupportSet:
    """Convert an already-verified pool into the release-bound support set.

    ``support_digest``/``support_size`` are the release-bound hardware-support member
    facts from the release manifest; the pool itself was verified at load.
    Package classes come from the pool's own verified classification, so
    firmware can never be reclassified as microcode here.
    The capacity bound is the pool's verified installed-size total
    (`total_installed_bytes` from Debian `Installed-Size` plus overhead),
    never the compressed archive total (`total_bytes`, kept only for
    transfer/storage bounds).
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
        installed_size_bound=pool.total_installed_bytes,
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


@dataclass(slots=True)
class InstallerPoolBindCleanupPackageInstaller:
    """Installer-side bind-mount cleanup wrapper (P2 production seam).

    Wraps the shared install path (``SharedSlotPackageInstaller`` over
    ``InstallerSlotPackageInstaller`` / ``TargetHardwareSupportInstaller``;
    no package logic is copied here) and detaches every bind mount the
    install records in ``mounted`` before returning, so the slot ``unmount``
    never sees a busy target. Mirrors the updater
    ``_LazyTargetPackageInstaller._detach_added_mounts`` invariant: "Bind
    mounts the installer records are detached before returning so the slot
    unmount never sees a busy target."

    The caller owns ``mounted`` (one per-EXECUTE list threaded through the
    installer seam); this wrapper only detaches the slice it adds
    (``mounted[before:]``) in reverse order via ``umount`` argv arrays
    (the runner enforces ``shell=False``). Recursive bind trees are detached
    recursively on their exact recorded target; successful entries are removed
    from tracking while failed entries remain recorded and fail closed. An
    install failure remains primary and receives cleanup context rather than
    being replaced by a cleanup exception.
    """

    inner: SlotPackageInstallInner
    runner: HardwareSupportCommandRunner
    mounted: list[Path]

    def install(
        self,
        firmware: tuple[str, ...],
        microcode: tuple[str, ...],
    ) -> tuple[InstalledPackage, ...]:
        before = len(self.mounted)
        try:
            result = self.inner.install(tuple(firmware), tuple(microcode))
        except BaseException as exc:
            failed = detach_recorded_mounts(
                self.runner, self.mounted, before=before
            )
            if failed:
                exc.add_note(
                    "installer mount cleanup also failed: "
                    + ", ".join(str(path) for path in failed)
                )
            raise
        failed = detach_recorded_mounts(self.runner, self.mounted, before=before)
        if failed:
            raise HardwareSupportInstallError(
                "installer mount cleanup could not detach: "
                + ", ".join(str(path) for path in failed)
            )
        return result

    def detach_added_mounts(self, before: int) -> None:
        failed = detach_recorded_mounts(self.runner, self.mounted, before=before)
        if failed:
            raise HardwareSupportInstallError(
                "installer mount cleanup could not detach: "
                + ", ".join(str(path) for path in failed)
            )
