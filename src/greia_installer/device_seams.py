"""Production installer seam factory for the shipped A/B path (POSTR1-P2).

Binds a freshly rematerialized whole-disk target into fully typed
:class:`greia_installer.fresh_ab_install.FreshAbInstallSeams` using only the
shared primitives: device-backed slot storage/filesystem
(:class:`greia_platform.block_slots.BlockSlotStorage` /
:class:`greia_platform.block_slots.BlockSlotFilesystem`), the reusing package
installer (:class:`greia_platform.block_slots.SharedSlotPackageInstaller` over
:class:`greia_installer.slots.InstallerSlotPackageInstaller`), the fixed
PERSIST boundary (:class:`greia_installer.persist.SubprocessPersistRunner`,
read-only consume — this module never edits ``persist.py``), and the shared
:class:`greia_platform.slot_writer.SlotWriter` / ``SlotFinalizer`` owned by
the orchestrator (never reimplemented here).

Every device address derives from the rematerialized ``target`` plus the
layout authority (``plan_for_profile`` + ``partition_number_path``), never
from request bytes. Factory construction (``config_from_facts_and_state`` +
``build_production_seam_pair``) performs no disk probe, no slot write and no
partition/runner execution — it only binds closures. All block probing
(``blkid``), inventory snapshots, bundle-manifest reads and pool loads happen
inside the returned ``seams_factory(target)`` at EXECUTE time, before the
first destructive partition command, so a wrong/moved target is refused
before destructive work.

An empty/absent configuration raises :class:`AbInstallCompositionError`
fail-closed (degraded construction) and is never the installed A/B default:
:func:`greia_installer.transaction_service.build_live_service` builds the
real configuration from ``AbExecutorFacts`` + service state, or fails closed
instead of routing an A/B profile to the legacy engine.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Sequence

from greia_platform.block_slots import (
    BlockSlotError,
    BlockSlotFilesystem,
    BlockSlotStorage,
    ResolvedSlotDevice,
    SharedSlotPackageInstaller,
    SubprocessBlockFilesystemRunner,
)
from greia_platform.hardware_enablement import LinuxSysfsHardwareInventory
from greia_platform.slot_writer import HardwareInventoryAttestation

from .composition import AbInstallCompositionError
from .disk import (
    DeviceObservation,
    DiskInventory,
    DiskProbeError,
    IdentityProvenance,
    LsblkDiskProbe,
    partition_number_path,
)
from .fresh_ab_install import AbExecutorFacts, FreshAbInstallError, FreshAbInstallSeams
from .layout import (
    LayoutError,
    LayoutPlan,
    ProfileSizing,
    plan_for_profile,
)

#: Platform-owned staging defaults for the shipped installer path. Tests bind
#: disposable tmpdirs instead; production never derives these from request bytes.
DEFAULT_PERSIST_STAGE_DIR = Path("/run/greia-install/persist")
DEFAULT_BOOT_CONTROL_DIR = Path("/run/greia-install/boot-control")
DEFAULT_MOUNT_ROOT = Path("/run/greia-slots")

_SHELL_METACHARACTERS = (";", "&", "|", "$", "`", "(", ")", "<", ">", "\n")


_COMMAND_FAILURE_DETAIL_BYTES = 240


def _bounded_command_failure_detail(value: str | None) -> str:
    """Keep both the start and end of bounded child-process diagnostics.

    Apt/dpkg frequently emits warnings before the fatal reason. Keeping only
    the prefix can therefore misidentify a warning as the root cause. The
    returned text is deliberately small enough to survive the privileged
    channel's bounded refusal reason while preserving the final diagnostic.
    """
    detail = (value or "").strip()
    if not detail:
        return "command failed"
    if len(detail) <= _COMMAND_FAILURE_DETAIL_BYTES:
        return detail
    marker = "\n...\n"
    head = 80
    tail = _COMMAND_FAILURE_DETAIL_BYTES - head - len(marker)
    return detail[:head] + marker + detail[-tail:]


# apt-get sends the actual dpkg/postinst errors to stdout on many Debian
# versions, while harmless debconf notices go to stderr. Reporting only
# stderr produced the physical Acer 2026-10-29 false diagnostic:
# "debconf: delaying package configuration ... E: dpkg returned code (1)".
# Select the concrete failing package / command from BOTH streams.
_APT_FAILURE_MARKERS = (
    "dpkg: error processing package",
    "dpkg: dependency problems",
    "errors were encountered while processing:",
    "post-installation script",
    "pre-installation script",
    "update-initramfs:",
    "run-parts:",
    "no space left on device",
    "operation not permitted",
    "permission denied",
    "fatal error",
    "failed to",
    "cannot ",
    "unable to",
)


def _apt_failure_detail(stdout: str | None, stderr: str | None) -> str:
    """Report the package and failure, not the harmless debconf preamble."""
    out_lines = (stdout or "").splitlines()
    err_lines = (stderr or "").splitlines()
    lines = [line.strip() for line in (*out_lines, *err_lines) if line.strip()]
    # dpkg's named-package error is the most useful part of an apt failure.
    named = [line for line in lines if "dpkg: error processing package" in line.lower()]
    if named:
        names: list[str] = []
        for stream in (out_lines, err_lines):
            for i, line in enumerate(stream[:-1]):
                if "errors were encountered while processing:" in line.lower():
                    names.extend(
                        follow.strip() for follow in stream[i + 1 : i + 5]
                        if follow.strip()
                    )
        reasons = [
            line for line in lines
            if any(token in line.lower() for token in (
                "post-installation script",
                "pre-installation script",
                "no space left on device",
                "operation not permitted",
                "permission denied",
                "returned error exit status",
            ))
        ]
        return _bounded_command_failure_detail(
            "\n".join((named[-1], *reasons[-2:], *names[-2:]))
        )
    meaningful = [
        line for line in lines
        if any(token in line.lower() for token in _APT_FAILURE_MARKERS)
    ]
    if meaningful:
        return _bounded_command_failure_detail("\n".join(meaningful[-5:]))
    # stderr may contain only a debconf advisory; retain apt's own stdout
    # rather than hiding it. The complete tails also go into the journal.
    return _bounded_command_failure_detail((stdout or "") or (stderr or ""))


def _check_arg_array(command: Sequence[str], *, owner: str) -> list[str]:
    """Reject shell-string-shaped commands; return a plain argument list."""
    if not isinstance(command, (list, tuple)) or not command:
        raise FreshAbInstallError(f"{owner} commands must be non-empty text arrays")
    argv = list(command)
    for word in argv:
        if not isinstance(word, str) or not word:
            raise FreshAbInstallError(f"{owner} commands must be non-empty text arrays")
        for marker in _SHELL_METACHARACTERS:
            if marker in word:
                raise FreshAbInstallError(
                    f"{owner} commands must not carry shell metacharacters"
                )
    return argv


def build_bios_bootloader_installer(
    runner: object,
    *,
    target_probe: object | None = None,
) -> Callable[[DeviceObservation, Path], None]:
    """Build the final BIOS GRUB adapter for the verified boot-control volume."""
    from .efi_boot import EfiBootError, bios_grub_install_command

    probe = target_probe if target_probe is not None else LsblkDiskProbe()
    if not callable(getattr(probe, "probe", None)):
        raise AbInstallCompositionError("BIOS GRUB adapter requires a disk identity probe")
    if not callable(getattr(runner, "run", None)):
        raise AbInstallCompositionError("BIOS GRUB adapter requires the shared command runner")

    def _install(target: DeviceObservation, boot_directory: Path) -> None:
        if not isinstance(target, DeviceObservation) or target.device_type != "disk":
            raise FreshAbInstallError("BIOS GRUB target is not the verified whole disk")
        if not target.path.is_absolute():
            raise FreshAbInstallError("BIOS GRUB target path is not absolute")
        if not isinstance(boot_directory, Path) or not boot_directory.is_absolute():
            raise FreshAbInstallError("BIOS GRUB boot directory is not an absolute mount path")
        identity = target.device_identity()
        if identity.provenance is not IdentityProvenance.STRONG_STABLE:
            raise FreshAbInstallError(
                "BIOS GRUB target has no strong stable identity; refusing the disk write"
            )
        try:
            inventory = probe.probe()
        except Exception as exc:
            raise FreshAbInstallError(
                f"BIOS GRUB target identity could not be rechecked: {exc}"
            ) from exc
        if not isinstance(inventory, DiskInventory):
            raise FreshAbInstallError("BIOS GRUB target probe returned no typed inventory")
        current = inventory.by_identity(identity)
        if (
            current is None
            or current.device_type != "disk"
            or current.path != target.path
        ):
            raise FreshAbInstallError(
                "BIOS GRUB target identity or locator changed before installation"
            )
        try:
            command = bios_grub_install_command(
                current.path, boot_directory=boot_directory
            )
            argv = _check_arg_array(command, owner="BIOS bootloader")
            result = runner.run(argv)  # type: ignore[attr-defined]
        except EfiBootError as exc:
            raise FreshAbInstallError(f"BIOS GRUB command is invalid: {exc}") from exc
        except Exception as exc:
            raise FreshAbInstallError(f"BIOS GRUB installation failed: {exc}") from exc
        returncode = getattr(result, "returncode", None)
        if isinstance(returncode, bool) or not isinstance(returncode, int) or returncode != 0:
            raise FreshAbInstallError("BIOS GRUB installation command failed")

    return _install


class SubprocessPartitionRunner:
    """Production partition runner: argument arrays only, ``shell=False``.

    Satisfies both the layout ``PartitionCommandRunner`` protocol and the
    fresh-install ``PartitionRunner`` seam (structurally identical
    single-``run`` seams). Non-zero tool exits raise :class:`LayoutError` so
    the layout adapter fails closed with context; the orchestrator wraps the
    failure before any slot write.
    """

    def run(self, command: Sequence[str]) -> None:
        argv = _check_arg_array(command, owner="partition")
        try:
            completed = subprocess.run(
                argv,
                check=False,
                capture_output=True,
                text=True,
                timeout=300,
                shell=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise LayoutError(f"partition command failed to execute: {exc}") from exc
        if completed.returncode != 0:
            detail = (completed.stderr or "").strip()[:256] or "command failed"
            raise LayoutError(f"partition command failed: {detail}")


class SubprocessHardwareSupportRunner:
    """Production package-command runner for the installer support path.

    Implements the :class:`greia_installer.hardware_support_install`
    ``HardwareSupportCommandRunner`` protocol (``run(command, *, check=True)``)
    with argument arrays and ``shell=False``. Delegated to by
    :class:`SharedSlotPackageInstaller` / ``InstallerSlotPackageInstaller``;
    no package logic lives here.
    """

    def run(self, command: Sequence[str], *, check: bool = True):  # type: ignore[no-untyped-def]
        argv = _check_arg_array(command, owner="hardware-support")
        try:
            completed = subprocess.run(
                argv,
                check=False,
                capture_output=True,
                text=True,
                timeout=600,
                shell=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise FreshAbInstallError(
                f"hardware-support command failed to execute: {exc}"
            ) from exc
        if check and completed.returncode != 0:
            # Preserve bounded real output in the transaction service journal
            # before the UI's small refusal message truncates it. This is a
            # failed installer, not an authentication-sensitive command.
            import sys

            print(
                "greia-hardware-support: command failed "
                f"(exit={completed.returncode}; argv={argv!r})",
                file=sys.stderr,
                flush=True,
            )
            for stream_name, value in (("stdout", completed.stdout), ("stderr", completed.stderr)):
                if value:
                    print(
                        f"greia-hardware-support: {stream_name} tail:\n{value[-12000:]}",
                        file=sys.stderr,
                        flush=True,
                    )
            detail = _apt_failure_detail(completed.stdout, completed.stderr)
            raise FreshAbInstallError(f"hardware-support command failed: {detail}")
        return completed


@dataclass(frozen=True, slots=True)
class ProductionAbSeamsConfig:
    """Typed production seam configuration (Greia-owned facts only).

    ``bundle_path``/``support_installed_bound``/``sizing``
    come from :class:`AbExecutorFacts`; ``hardware_support_pool`` comes from
    service state; staging/mount dirs are platform-owned paths (disposable
    tmpdirs in tests). Support digests, inventory attestation and pool
    contents are derived at EXECUTE time from the bundle manifest, a sysfs
    snapshot and the verified pool — never stored here — so construction
    needs no bundle inspection, no sysfs probe and no pool load.
    """

    bundle_path: Path
    support_installed_bound: int
    sizing: ProfileSizing
    hardware_support_pool: Path | None
    persist_stage_dir: Path = DEFAULT_PERSIST_STAGE_DIR
    boot_control_dir: Path = DEFAULT_BOOT_CONTROL_DIR
    mount_root: Path = DEFAULT_MOUNT_ROOT

    def __post_init__(self) -> None:
        if not isinstance(self.bundle_path, Path) or not self.bundle_path.is_absolute():
            raise AbInstallCompositionError(
                "production seam configuration carries no absolute release bundle"
            )
        if self.bundle_path.is_symlink() or not self.bundle_path.is_file():
            raise AbInstallCompositionError(
                "production seam configuration release bundle is not a regular file"
            )
        if (
            isinstance(self.support_installed_bound, bool)
            or not isinstance(self.support_installed_bound, int)
            or self.support_installed_bound < 0
        ):
            raise AbInstallCompositionError(
                "production seam configuration support bound must be a non-negative integer"
            )
        if not isinstance(self.sizing, ProfileSizing):
            raise AbInstallCompositionError(
                "production seam configuration carries no profile-owned sizing facts"
            )
        if self.hardware_support_pool is not None and (
            not isinstance(self.hardware_support_pool, Path)
            or not self.hardware_support_pool.is_absolute()
        ):
            raise AbInstallCompositionError(
                "production seam configuration pool must be an absolute path or None"
            )
        for field_name in (
            "persist_stage_dir",
            "boot_control_dir",
            "mount_root",
        ):
            location = getattr(self, field_name)
            if not isinstance(location, Path) or not location.is_absolute() or not str(location).strip():
                raise AbInstallCompositionError(
                    f"production seam configuration {field_name} must be an absolute path"
                )


def config_from_facts_and_state(
    *,
    facts: AbExecutorFacts,
    hardware_support_pool: Path | str | None = None,
    persist_stage_dir: Path | str | None = None,
    boot_control_dir: Path | str | None = None,
    mount_root: Path | str | None = None,
) -> ProductionAbSeamsConfig:
    """Build the production seam configuration from executor facts + state.

    Raises :class:`AbInstallCompositionError` for an empty/absent
    configuration — never a degraded silent default.
    """
    if not isinstance(facts, AbExecutorFacts):
        raise AbInstallCompositionError(
            "production seam configuration requires typed executor facts"
        )

    def _as_path(value: Path | str | None, default: Path) -> Path:
        if value is None:
            return default
        location = Path(value) if isinstance(value, (Path, str)) and value else None
        if location is None:
            raise AbInstallCompositionError(
                "production seam configuration staging path is empty"
            )
        return location

    pool: Path | None = None
    if hardware_support_pool is not None:
        pool = Path(hardware_support_pool) if isinstance(hardware_support_pool, (Path, str)) else None
        if pool is None or not str(pool):
            raise AbInstallCompositionError(
                "production seam configuration pool path is empty"
            )
    return ProductionAbSeamsConfig(
        bundle_path=Path(facts.bundle_path),
        support_installed_bound=int(facts.support_installed_bytes),
        sizing=facts.sizing,
        hardware_support_pool=pool,
        persist_stage_dir=_as_path(persist_stage_dir, DEFAULT_PERSIST_STAGE_DIR),
        boot_control_dir=_as_path(boot_control_dir, DEFAULT_BOOT_CONTROL_DIR),
        mount_root=_as_path(mount_root, DEFAULT_MOUNT_ROOT),
    )


def build_production_seam_pair(
    config: ProductionAbSeamsConfig,
) -> tuple[
    Callable[[DeviceObservation], FreshAbInstallSeams],
    Callable[[DeviceObservation, LayoutPlan], Mapping[str, Mapping[str, str]]],
]:
    """Build the paired production (seams, identities) factories.

    The pair shares one per-service observation holder: the identities
    factory (production ``blkid`` observer) records the post-layout
    identities the orchestrator observes after partitioning, and the slot
    filesystem closure (invoked later, after the SYSTEM_A stream) binds the
    shared :class:`BlockSlotFilesystem` to exactly those observed identities.
    Construction binds closures only — no probe, no slot write, no runner
    execution. All block reads (bundle manifest, sysfs inventory, pool load,
    staging mkdir) happen inside ``seams_factory(target)`` at EXECUTE time,
    after the whole-disk target check, and still before the first
    destructive partition command.
    """
    if not isinstance(config, ProductionAbSeamsConfig):
        raise AbInstallCompositionError(
            "production seam construction requires a typed seam configuration; "
            "refusing a degraded half-wired default"
        )
    observed_holder: dict[str, object] = {}

    def _seams_factory(target: DeviceObservation) -> FreshAbInstallSeams:
        if not isinstance(target, DeviceObservation):
            raise FreshAbInstallError(
                "production seams require a rematerialized whole-disk target"
            )
        if target.device_type != "disk":
            raise FreshAbInstallError(
                "fresh install requires a whole-disk target; "
                f"refusing a moved/non-disk target ({target.device_type!r})"
            )
        try:
            plan = plan_for_profile(
                config.sizing, device_size_bytes=int(target.size_bytes)
            )
        except (LayoutError, TypeError, ValueError) as exc:
            raise FreshAbInstallError(
                f"release layout does not fit the rematerialized target: {exc}"
            ) from exc

        # Release-bound support facts from the bundle manifest (read-only).
        try:
            from greia_platform.system_updates import inspect_update_bundle
        except ImportError as exc:
            raise FreshAbInstallError(
                f"release bundle inspection is unavailable: {exc}"
            ) from exc
        try:
            inspected = inspect_update_bundle(Path(config.bundle_path))
        except Exception as exc:
            raise FreshAbInstallError(
                f"release bundle is not a verified Greia release: {exc}"
            ) from exc
        manifest = inspected.manifest
        support_digest = manifest.hardware_support_sha256
        support_size = manifest.hardware_support_size

        # Hardware inventory attestation from a fresh sysfs snapshot.
        try:
            snapshot = LinuxSysfsHardwareInventory().snapshot()
        except Exception as exc:
            raise FreshAbInstallError(
                f"hardware inventory observation failed: {exc}"
            ) from exc
        try:
            attestation = HardwareInventoryAttestation.from_inventory(snapshot)
            inventory_token = attestation.token
            inventory_complete = True
        except Exception:
            # Incomplete inventory stays fail-closed: carry the observed token
            # with complete=False so the orchestrator refuses finalization.
            inventory_token = snapshot.token
            inventory_complete = False

        # Verified support pool (already-verified Debian payloads + indexes).
        if config.hardware_support_pool is None:
            raise FreshAbInstallError(
                "hardware support pool is missing for release installation"
            )
        try:
            from .hardware_support import VerifiedHardwareSupportPool

            pool = VerifiedHardwareSupportPool.load(Path(config.hardware_support_pool))
        except Exception as exc:
            raise FreshAbInstallError(
                f"hardware support pool is not authoritative: {exc}"
            ) from exc
        # Machine-specific selection from the same attested snapshot: the
        # finalizer installs exactly these sets, so the capacity bound below
        # covers their verified dependency closures instead of the whole
        # pool the release merely carries. Planner infrastructure failure
        # refuses fail-closed here; unattestable inventory is still gated
        # at finalization, and pool-missing wants stay diagnostic-only as
        # before (they were never installable).
        detection_incomplete = False
        wifi_firmware_unavailable = False
        try:
            from .hardware_enablement import InstallerHardwareEnablementPlanner

            enablement = InstallerHardwareEnablementPlanner.linux_default(
                pool=pool,
                inventory_snapshot=snapshot,
            ).plan()
            if enablement.detection_incomplete:
                # Owner decision 2026-10-21: incomplete detection never stops
                # the install; the verified common network firmware is added.
                detection_incomplete = True
                import sys

                print(
                    "greia-install-tx: hardware detection incomplete; installing fallback "
                    "network firmware: "
                    + ",".join(enablement.fallback_firmware)
                    + " diagnostics="
                    + " | ".join(enablement.recorded_diagnostics),
                    file=sys.stderr,
                    flush=True,
                )
            wifi_firmware_unavailable = enablement.wifi_firmware_unavailable
            firmware_packages = tuple(
                dict.fromkeys((*enablement.required_firmware, *enablement.fallback_firmware))
            )
            microcode_packages = tuple(enablement.required_microcode)
            selected_installed_bound = pool.selected_installed_bytes(
                firmware_packages, microcode_packages
            )
        except FreshAbInstallError:
            raise
        except Exception as exc:
            raise FreshAbInstallError(
                f"machine hardware selection is not authoritative: {exc}"
            ) from exc
        # The support-set classes cover exactly the machine-selected
        # packages (never the whole pool): the finalizer installs the
        # selected sets, and the release-support record must describe the
        # installed reality so unselected pool members (for example
        # dependency-only packages) cannot fail the class binding.
        provided = frozenset(firmware_packages) | frozenset(microcode_packages)
        support_classes = tuple(
            sorted(
                (
                    (entry.package, entry.version, entry.architecture, entry.sha256)
                    for entry in pool.packages
                    if entry.package in provided
                ),
                key=lambda item: item[0],
            )
        )

        # Staging roots exist before the orchestrator needs them (EXECUTE-time
        # staging writes, never valued-disk destruction). Symlinks refused.
        for field_name in (
            "persist_stage_dir",
            "mount_root",
        ):
            location = Path(getattr(config, field_name))
            if os.path.islink(location):
                raise FreshAbInstallError(
                    f"production staging path may not be a symbolic link: {field_name}"
                )
            try:
                location.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                raise FreshAbInstallError(
                    f"production staging path is not writable: {field_name}: {exc}"
                ) from exc
            if os.path.islink(location) or not location.is_dir():
                raise FreshAbInstallError(
                    f"production staging path is not a real directory: {field_name}"
                )

        slot_bytes = int(config.sizing.slot_bytes)
        mount_root = Path(config.mount_root)
        package_runner = SubprocessHardwareSupportRunner()

        def _slot_storage_factory(role: str) -> BlockSlotStorage:
            if role != "A":
                raise FreshAbInstallError(
                    "fresh install addresses SYSTEM_A only; "
                    f"refusing second-slot storage ({role!r})"
                )
            try:
                part = plan.by_role("system-a")
                node = partition_number_path(target.path, part.number)
            except (LayoutError, DiskProbeError) as exc:
                raise FreshAbInstallError(
                    f"SYSTEM_A device address is not authoritative: {exc}"
                ) from exc
            try:
                return BlockSlotStorage(node, slot_bytes)
            except BlockSlotError as exc:
                raise FreshAbInstallError(
                    f"SYSTEM_A slot store is not authoritative: {exc}"
                ) from exc
            except Exception as exc:
                raise FreshAbInstallError(
                    f"SYSTEM_A slot store is not authoritative: {exc}"
                ) from exc

        def _slot_filesystem_factory() -> BlockSlotFilesystem:
            observed = observed_holder.get("observed")
            if not isinstance(observed, dict):
                raise FreshAbInstallError(
                    "post-layout identities are not yet observed; "
                    "refusing slot finalization before authoritative observation"
                )
            try:
                sys_a = dict(observed["system-a"])  # type: ignore[index]
                filesystem_uuid = sys_a["filesystem_uuid"]
                partuuid = sys_a["partuuid"]
            except (KeyError, TypeError, AttributeError) as exc:
                raise FreshAbInstallError(
                    f"observed SYSTEM_A identity is not authoritative: {exc}"
                ) from exc
            try:
                part = plan.by_role("system-a")
                node = partition_number_path(target.path, part.number)
            except (LayoutError, DiskProbeError) as exc:
                raise FreshAbInstallError(
                    f"SYSTEM_A device address is not authoritative: {exc}"
                ) from exc
            try:
                resolved = ResolvedSlotDevice(
                    semantic_slot="A",
                    role="system-a",
                    device_node=node,
                    partuuid=partuuid,
                    filesystem_uuid=filesystem_uuid,
                    capacity_bytes=slot_bytes,
                    disk_id=str(target.path),
                    layout_id=plan.adapter_id,
                )
                return BlockSlotFilesystem(
                    resolved, SubprocessBlockFilesystemRunner(), mount_root
                )
            except BlockSlotError as exc:
                raise FreshAbInstallError(
                    f"SYSTEM_A slot filesystem is not authoritative: {exc}"
                ) from exc
            except Exception as exc:
                raise FreshAbInstallError(
                    f"SYSTEM_A slot filesystem is not authoritative: {exc}"
                ) from exc

        def _package_installer_factory() -> object:
            # Must match BlockSlotFilesystem.mount()'s deterministic path
            # (mount_root / f"slot-a-{pid}") in the same EXECUTE process: the
            # finalizer mounts before installing, so by install() time this
            # path is the mounted destination slot.
            #
            # The per-EXECUTE ``mounted`` list is owned here (one list per
            # factory call, i.e. one EXECUTE) and threaded through the shared
            # ``SharedSlotPackageInstaller`` over
            # ``InstallerSlotPackageInstaller``. The cleanup wrapper detaches
            # every bind mount the install records (pool bind at
            # ``target_root/run/greia-hardware-support`` plus any nested
            # ones) in reverse order via ``umount`` argv arrays before
            # returning, so ``BlockSlotFilesystem.unmount()`` never sees a
            # busy target — the same shape as the updater
            # ``_LazyTargetPackageInstaller`` path.
            from .slots import InstallerPoolBindCleanupPackageInstaller

            mountpoint = mount_root / f"slot-a-{os.getpid()}"
            mounted: list[Path] = []
            shared = SharedSlotPackageInstaller(
                runner=package_runner,
                target_root=mountpoint,
                pool=pool,
                mounted=mounted,
            )
            # ``SharedSlotPackageInstaller`` delegates to the existing
            # ``InstallerSlotPackageInstaller`` / ``TargetHardwareSupportInstaller``
            # path with the already-verified pool; no package logic lives here.
            return InstallerPoolBindCleanupPackageInstaller(
                inner=shared,
                runner=package_runner,
                mounted=mounted,
            )

        # PERSIST uses the fixed exactly-once boundary (read-only consume of
        # persist.py): production runner + staging dir; the UUID factory stays
        # None so the orchestrator binds the observed PERSIST filesystem UUID.
        from .persist import SubprocessPersistRunner
        persist_runner = SubprocessPersistRunner()

        return FreshAbInstallSeams(
            partition_runner=SubprocessPartitionRunner(),  # type: ignore[arg-type]
            slot_storage_factory=_slot_storage_factory,
            slot_filesystem_factory=_slot_filesystem_factory,
            package_installer_factory=_package_installer_factory,
            inventory_token=inventory_token,
            support_digest=support_digest,
            support_size=support_size,
            support_installed_bound=selected_installed_bound,
            support_classes=support_classes,
            persist_runner=persist_runner,
            persist_stage_dir=Path(config.persist_stage_dir),
            persist_uuid_factory=None,
            boot_control_dir=Path(config.boot_control_dir),
            boot_branding_dir=Path("/boot/grub"),
            firmware_packages=firmware_packages,
            microcode_packages=microcode_packages,
            payload_stream_factory=None,
            inventory_complete=inventory_complete,
            hardware_detection_incomplete=detection_incomplete,
            wifi_firmware_unavailable=wifi_firmware_unavailable,
            post_layout_identity_observer=None,
            bios_bootloader_installer=build_bios_bootloader_installer(
                persist_runner
            ),
        )

    def _identities_factory(
        target: DeviceObservation, plan: LayoutPlan
    ) -> dict[str, dict[str, str]]:
        if not isinstance(target, DeviceObservation):
            raise FreshAbInstallError(
                "post-layout observation requires a rematerialized whole-disk target"
            )
        from .layout import build_post_layout_mbr_observer, SubprocessMbrProbeRunner

        observer = build_post_layout_mbr_observer(SubprocessMbrProbeRunner())
        observed = observer(target, plan)
        if not isinstance(observed, dict):
            raise FreshAbInstallError(
                "post-layout identity observation is not authoritative"
            )
        observed_holder["observed"] = observed
        observed_holder["target_path"] = str(target.path)
        return observed

    return (_seams_factory, _identities_factory)


__all__ = [
    "DEFAULT_BOOT_CONTROL_DIR",
    "DEFAULT_MOUNT_ROOT",
    "DEFAULT_PERSIST_STAGE_DIR",
    "ProductionAbSeamsConfig",
    "SubprocessHardwareSupportRunner",
    "SubprocessPartitionRunner",
    "build_bios_bootloader_installer",
    "build_production_seam_pair",
    "config_from_facts_and_state",
]
