from __future__ import annotations

import hashlib
import hmac
import json
import os
import string
import subprocess
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Protocol, Sequence

from greia_platform.boot_contract import GrubContractError, validate_grub_config
from greia_platform.fstab import FSTAB_FILE_MODE, render_fstab
from greia_platform.grub_security import (
    GrubPasswordHasher,
    GrubRecoveryCredential,
    provision_recovery_material,
)
from greia_platform.hardware import HardwareSettings, HardwareSettingsStore

from .disk import (
    BlockDevice,
    DeviceIdentity,
    DiskInventory,
    InstallTargetPolicy,
    LiveMediaResolver,
    LsblkDiskProbe,
    default_install_target_policy,
    partition_one_path,
)
from .hardware_enablement import (
    HardwareEnablementPlanError,
    InstallerHardwareEnablementPlan,
    InstallerHardwareEnablementPlanner,
    TargetImageHardwareIdentity,
)
from .hardware_support import HardwareSupportPoolError, VerifiedHardwareSupportPool
from .hardware_support_install import TargetHardwareSupportInstaller
from .power import PowerSupplyProbe
from .wifi import IwdNetworkProfile


class InstallationError(RuntimeError):
    pass


def _optional_path_from_environment(name: str) -> Path | None:
    value = os.environ.get(name, "").strip()
    return Path(value) if value else None


@dataclass(frozen=True, slots=True)
class InstallRequest:
    target: BlockDevice
    payload: Path
    hardware_settings: HardwareSettings
    locale: str = "en"
    payload_digest: Path | None = None
    wifi_profile: IwdNetworkProfile | None = None
    hardware_support_pool: Path | None = field(
        default_factory=lambda: _optional_path_from_environment(
            "GREIA_HARDWARE_SUPPORT_POOL"
        )
    )
    target_profile: Path | None = field(
        default_factory=lambda: _optional_path_from_environment(
            "GREIA_TARGET_IMAGE_PROFILE"
        )
    )


@dataclass(frozen=True, slots=True)
class InstallProgress:
    fraction: float
    stage: str
    detail: str


@dataclass(frozen=True, slots=True)
class InstallResult:
    """Completion facts for the installed system.

    The end-install screen no longer asks the parent to preserve a generated
    random credential. The initial Parent/admin identity is the simple,
    predictable ``greia`` / ``greia`` pair defined by the active owner policy and
    can be changed from Greia Parents after first boot.
    """

    parent_username: str = "greia"
    parent_password: str = "greia"


@dataclass(frozen=True, slots=True)
class PreparedHardwareSupport:
    identity: TargetImageHardwareIdentity
    plan: InstallerHardwareEnablementPlan


class InstallationPowerProbe(Protocol):
    def installation_block_reason(self) -> str | None: ...


class CommandRunner(Protocol):
    def run(self, command: Sequence[str], *, check: bool = True) -> subprocess.CompletedProcess[str]: ...


class SubprocessRunner:
    def run(
        self, command: Sequence[str], *, check: bool = True
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            list(command),
            check=check,
            shell=False,
            text=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )


def _exception_is_active() -> bool:
    import sys

    return sys.exc_info()[0] is not None


class InstallationEngine:
    """A narrow whole-disk installer with repeated identity verification."""

    def __init__(
        self,
        *,
        project_root: Path,
        runner: CommandRunner | None = None,
        probe: LsblkDiskProbe | None = None,
        grub_password_hasher: GrubPasswordHasher | None = None,
        power_probe: InstallationPowerProbe | None = None,
        target_policy: InstallTargetPolicy | None = None,
        live_resolver: LiveMediaResolver | None = None,
    ):
        self.project_root = project_root.resolve()
        self.runner = runner or SubprocessRunner()
        self.probe = probe or LsblkDiskProbe()
        self.grub_password_hasher = grub_password_hasher
        self.power_probe = power_probe or PowerSupplyProbe()
        self.target_policy = target_policy or default_install_target_policy()
        self.live_resolver = live_resolver or LiveMediaResolver()

    def install(
        self,
        request: InstallRequest,
        on_progress: Callable[[InstallProgress], None] | None = None,
    ) -> InstallResult:
        report = on_progress or (lambda progress: None)
        if os.geteuid() != 0:
            raise InstallationError("installation must run as root in the live installer")
        if not request.payload.is_file():
            raise InstallationError(f"installation payload not found: {request.payload}")
        report(InstallProgress(0.01, "payload", "Checking the installation files"))
        self._verify_payload(request.payload, request.payload_digest)
        self._verify_target(request.target)
        hardware_support = self._prepare_hardware_support(request, report)

        target_mount = Path(tempfile.mkdtemp(prefix="pip-install-target."))
        mounted: list[Path] = []
        partition = partition_one_path(request.target.path)
        try:
            report(InstallProgress(0.03, "prepare", "Checking the selected disk"))
            self._verify_target(request.target)
            # Payload hashing and hardware discovery can take significant time on
            # the reference Acer. Recheck AC/battery state immediately before the
            # first irreversible command instead of trusting the UI preflight.
            self._verify_pre_erase_power()
            self._verify_target(request.target)

            report(InstallProgress(0.10, "erase", "Preparing the internal disk"))
            self.runner.run(["wipefs", "--all", "--force", str(request.target.path)])
            self.runner.run(["parted", "--script", str(request.target.path), "mklabel", "msdos"])
            self.runner.run(
                [
                    "parted",
                    "--script",
                    str(request.target.path),
                    "mkpart",
                    "primary",
                    "ext4",
                    "1MiB",
                    "100%",
                ]
            )
            self.runner.run(
                ["parted", "--script", str(request.target.path), "set", "1", "boot", "on"]
            )
            self.runner.run(["partprobe", str(request.target.path)], check=False)
            self.runner.run(["udevadm", "settle"])
            self._wait_for_partition(partition)
            self._verify_target(request.target)

            report(InstallProgress(0.22, "format", "Creating the Greia OS filesystem"))
            self.runner.run(
                ["mkfs.ext4", "-F", "-m", "1", "-L", "PIP_ROOT", str(partition)]
            )
            filesystem_uuid = self._read_filesystem_uuid(partition)
            self.runner.run(["mount", str(partition), str(target_mount)])
            mounted.append(target_mount)

            report(InstallProgress(0.32, "copy", "Copying the system"))
            self.runner.run(
                [
                    "unsquashfs",
                    "-f",
                    "-no-progress",
                    "-strict-errors",
                    "-processors",
                    "1",
                    "-data-queue",
                    "32",
                    "-frag-queue",
                    "32",
                    "-d",
                    str(target_mount),
                    str(request.payload),
                ]
            )
            self._write_root_fstab(target_mount, filesystem_uuid)
            self._write_grub_root_uuid(target_mount, filesystem_uuid)

            report(InstallProgress(0.70, "configure", "Applying parent choices"))
            self._write_initial_configuration(
                target_mount,
                request,
                hardware_support.plan if hardware_support is not None else None,
            )
            self._mount_chroot_filesystems(target_mount, mounted)

            if hardware_support is not None and hardware_support.plan.target_packages:
                report(
                    InstallProgress(
                        0.74,
                        "hardware",
                        "Adding support for this computer",
                    )
                )
                # Re-read and re-hash the media pool at the point of use. The
                # earlier pre-erase verification is not treated as perpetual
                # authority across a long destructive installation transaction.
                pool = self._load_hardware_support_pool(
                    request, hardware_support.identity
                )
                TargetHardwareSupportInstaller(self.runner).install(
                    target_root=target_mount,
                    pool=pool,
                    packages=hardware_support.plan.target_packages,
                    mounted=mounted,
                )

            self._personalize_target(target_mount)

            report(InstallProgress(0.78, "bootloader", "Making the disk bootable"))
            self.runner.run(["chroot", str(target_mount), "update-initramfs", "-u", "-k", "all"])
            self.runner.run(["chroot", str(target_mount), "update-grub"])
            self.runner.run(
                ["chroot", str(target_mount), "grub-script-check", "/boot/grub/grub.cfg"]
            )
            try:
                developer = (target_mount / "etc/greia-os/developer-remote").is_file()
                validate_grub_config(
                    target_mount / "boot/grub/grub.cfg",
                    developer=developer,
                )
            except GrubContractError as exc:
                raise InstallationError(f"installed boot configuration is unsafe: {exc}") from exc
            # The target is mounted by us at this point, so eligibility would now
            # reject it. Identity must still be rechecked immediately before GRUB
            # writes to the whole disk.
            self._verify_target_identity(request.target)
            self.runner.run(
                [
                    "chroot",
                    str(target_mount),
                    "grub-install",
                    "--target=i386-pc",
                    "--boot-directory=/boot",
                    "--recheck",
                    str(request.target.path),
                ]
            )

            report(InstallProgress(0.94, "verify", "Checking the installed system"))
            required = (
                target_mount / "opt/greia-os/src/greia_launcher/main.py",
                target_mount / "etc/systemd/system/greia-launcher.service",
                target_mount / "boot/grub/grub.cfg",
            )
            missing = [str(path) for path in required if not path.exists()]
            if missing:
                raise InstallationError("installed system is incomplete: " + ", ".join(missing))
            self._verify_installed_boot_config(
                target_mount,
                filesystem_uuid,
                partition,
            )
            self.runner.run(["sync"])
            report(InstallProgress(1.0, "complete", "Installation complete"))
        except subprocess.CalledProcessError as exc:
            detail = exc.stderr.strip() if exc.stderr else str(exc)
            raise InstallationError(detail) from exc
        finally:
            cleanup_error = self._cleanup_mounts(mounted)
            try:
                # Never recursively remove this path: if a mount survived cleanup,
                # recursive deletion could cross into the target or live /dev,/sys,/run.
                target_mount.rmdir()
            except OSError:
                pass
            if cleanup_error is not None and not _exception_is_active():
                raise cleanup_error
        return InstallResult()

    def _prepare_hardware_support(
        self,
        request: InstallRequest,
        report: Callable[[InstallProgress], None],
    ) -> PreparedHardwareSupport | None:
        if request.hardware_support_pool is None and request.target_profile is None:
            return None
        if request.hardware_support_pool is None or request.target_profile is None:
            raise InstallationError(
                "hardware support requires both the media pool and target image profile"
            )
        report(InstallProgress(0.02, "hardware", "Checking hardware compatibility"))
        try:
            identity = TargetImageHardwareIdentity.load(request.target_profile)
            pool = self._load_hardware_support_pool(request, identity)
            plan = InstallerHardwareEnablementPlanner.linux_default(pool=pool).plan()
        except (HardwareEnablementPlanError, HardwareSupportPoolError) as exc:
            raise InstallationError(f"hardware support verification failed: {exc}") from exc
        if not plan.complete:
            detail = "; ".join(plan.diagnostics[:3]) or "hardware support resolution is incomplete"
            raise InstallationError(
                "hardware support could not be resolved safely before disk changes: " + detail
            )
        return PreparedHardwareSupport(identity, plan)

    @staticmethod
    def _load_hardware_support_pool(
        request: InstallRequest,
        identity: TargetImageHardwareIdentity,
    ) -> VerifiedHardwareSupportPool:
        if request.hardware_support_pool is None:
            raise InstallationError("hardware support pool is missing")
        try:
            return VerifiedHardwareSupportPool.load(
                request.hardware_support_pool,
                expected_suite=identity.suite,
                expected_architecture=identity.architecture,
            )
        except HardwareSupportPoolError as exc:
            raise InstallationError(f"hardware support media verification failed: {exc}") from exc

    def _find_target_identity(
        self, expected: BlockDevice, inventory: DiskInventory
    ) -> BlockDevice:
        expected_identity = DeviceIdentity.from_observation(
            expected,
            allow_legacy_ata_fallback=self.target_policy.permit_legacy_ata_fallback,
        )
        current = inventory.by_identity(expected_identity)
        if current is None:
            raise InstallationError("selected disk disappeared")
        # Identity is the authority, but the stored /dev path is still the
        # locator used for destructive commands below. If the locator moved
        # while the identity survived, fail closed instead of addressing a
        # re-enumerated path.
        if current.path != expected.path:
            raise InstallationError("selected disk identity changed; installation stopped")
        return current

    def _verify_target_identity(self, expected: BlockDevice) -> BlockDevice:
        return self._find_target_identity(expected, self.probe.probe())

    def _verify_target(self, expected: BlockDevice) -> None:
        inventory = self.probe.probe()
        current = self._find_target_identity(expected, inventory)
        ancestry = self.live_resolver.resolve(inventory)
        if ancestry.ambiguous:
            raise InstallationError(
                "setup-medium ancestry is ambiguous; installation stopped"
            )
        if current.name in ancestry.whole_disk_names:
            raise InstallationError(
                "selected disk is no longer an eligible unmounted internal disk"
            )
        if not self.target_policy.evaluate(current).eligible:
            raise InstallationError("selected disk is no longer an eligible unmounted internal disk")

    def _verify_pre_erase_power(self) -> None:
        reason = self.power_probe.installation_block_reason()
        if reason:
            raise InstallationError(reason)

    @staticmethod
    def _verify_payload(payload: Path, digest_path: Path | None = None) -> None:
        sidecar = digest_path or Path(f"{payload}.sha256")
        try:
            raw = sidecar.read_text(encoding="ascii").strip()
        except (FileNotFoundError, OSError, UnicodeDecodeError) as exc:
            raise InstallationError("installation payload integrity record is missing") from exc
        expected = raw.split()[0].lower() if raw else ""
        if len(expected) != 64 or any(character not in string.hexdigits for character in expected):
            raise InstallationError("installation payload integrity record is invalid")
        digest = hashlib.sha256()
        try:
            with payload.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
        except OSError as exc:
            raise InstallationError("installation payload could not be read") from exc
        if not hmac.compare_digest(digest.hexdigest(), expected):
            raise InstallationError("installation payload is damaged; the disk was not changed")

    def _read_filesystem_uuid(self, partition: Path) -> str:
        completed = self.runner.run(
            ["blkid", "-s", "UUID", "-o", "value", "--", str(partition)]
        )
        candidate = completed.stdout.strip()
        try:
            return str(uuid.UUID(candidate))
        except (ValueError, AttributeError) as exc:
            raise InstallationError("new filesystem has no valid UUID") from exc

    @staticmethod
    def _write_root_fstab(target_root: Path, filesystem_uuid: str) -> None:
        # Single-owner fstab policy: render through greia_platform.fstab so
        # fresh installs carry exactly the canonical policy the finalizer
        # specializes per destination role. Mode is the canonical
        # FSTAB_FILE_MODE (0o644) regardless of caller umask.
        try:
            text = render_fstab(filesystem_uuid)
        except ValueError as exc:
            raise InstallationError("refusing invalid root filesystem UUID") from exc
        fstab = target_root / "etc/fstab"
        fstab.parent.mkdir(parents=True, exist_ok=True)
        fstab.write_text(text, encoding="ascii")
        os.chmod(fstab, FSTAB_FILE_MODE)

    @staticmethod
    def _write_grub_root_uuid(target_root: Path, filesystem_uuid: str) -> None:
        try:
            normalized = str(uuid.UUID(filesystem_uuid))
        except ValueError as exc:
            raise InstallationError("refusing invalid GRUB root filesystem UUID") from exc
        state_dir = target_root / "etc/greia-os"
        state_dir.mkdir(parents=True, exist_ok=True)
        path = state_dir / "root-filesystem-uuid"
        path.write_text(normalized + "\n", encoding="ascii")
        os.chmod(path, 0o644)

    def _wait_for_partition(self, partition: Path) -> None:
        for _ in range(40):
            if partition.exists():
                return
            time.sleep(0.25)
        raise InstallationError(f"new partition did not appear: {partition}")

    @staticmethod
    def _verify_installed_boot_config(
        target_root: Path,
        filesystem_uuid: str,
        partition: Path,
    ) -> None:
        """Fail install if the generated boot config cannot boot this disk.

        Catches root-UUID mismatches and missing kernel/initrd before the
        machine is handed back, instead of boot-looping after 'GRUB loaded'.
        """
        normalized = str(uuid.UUID(filesystem_uuid))
        grub_cfg = target_root / "boot/grub/grub.cfg"
        if not grub_cfg.is_file():
            raise InstallationError("installed GRUB configuration is missing")
        cfg_text = grub_cfg.read_text(encoding="utf-8", errors="replace")
        if f"root=UUID={normalized}" not in cfg_text:
            raise InstallationError(
                "installed GRUB configuration does not reference the root filesystem UUID"
            )
        # The appliance entry loads /vmlinuz and /initrd.img symlinks; both must
        # resolve to existing kernel/initrd files.
        for link_name in ("vmlinuz", "initrd.img"):
            link = target_root / link_name
            if not link.exists():
                raise InstallationError(
                    f"installed boot entry is missing {link_name}"
                )
            target = link.resolve()
            if not target.is_file() or target_root.resolve() not in target.parents:
                raise InstallationError(
                    f"installed boot entry {link_name} does not resolve inside the system"
                )

    def _mount_chroot_filesystems(self, root: Path, mounted: list[Path]) -> None:
        for name in ("dev", "proc", "sys", "run"):
            target = root / name
            target.mkdir(parents=True, exist_ok=True)
            if name in {"dev", "sys", "run"}:
                self.runner.run(["mount", "--rbind", f"/{name}", str(target)])
                # Record immediately after mount succeeds. If propagation setup
                # fails, cleanup must still know about this live bind mount.
                mounted.append(target)
                self.runner.run(["mount", "--make-rslave", str(target)])
            else:
                self.runner.run(["mount", "-t", "proc", "proc", str(target)])
                mounted.append(target)

    def _cleanup_mounts(self, mounted: list[Path]) -> InstallationError | None:
        remaining: list[Path] = []
        for mountpoint in reversed(mounted):
            self.runner.run(["umount", str(mountpoint)], check=False)
            if self._is_mountpoint(mountpoint):
                self.runner.run(["umount", "-l", str(mountpoint)], check=False)
            if self._is_mountpoint(mountpoint):
                remaining.append(mountpoint)
        if remaining:
            return InstallationError(
                "installer cleanup could not detach: "
                + ", ".join(str(path) for path in remaining)
                + "; the temporary directory was preserved"
            )
        return None

    def _is_mountpoint(self, path: Path) -> bool:
        # os.path.ismount cannot reliably identify Linux bind mounts. The live
        # installer uses util-linux mountpoint, which checks mountinfo correctly.
        completed = self.runner.run(["mountpoint", "-q", str(path)], check=False)
        return completed.returncode == 0

    def _personalize_target(self, target_root: Path) -> GrubRecoveryCredential:
        # Keep cloned identity material empty. First boot creates the machine ID;
        # SSH host keys are generated only when a parent explicitly enables SSH.
        machine_id = target_root / "etc/machine-id"
        machine_id.parent.mkdir(parents=True, exist_ok=True)
        machine_id.write_text("", encoding="ascii")
        for path in (
            target_root / "var/lib/dbus/machine-id",
            target_root / "var/lib/systemd/random-seed",
        ):
            path.unlink(missing_ok=True)
        for host_key in (target_root / "etc/ssh").glob("ssh_host_*"):
            host_key.unlink()
        return provision_recovery_material(
            target_root,
            hasher=self.grub_password_hasher,
        )

    def _write_initial_configuration(
        self,
        target_root: Path,
        request: InstallRequest,
        hardware_plan: InstallerHardwareEnablementPlan | None = None,
    ) -> None:
        defaults = target_root / "opt/greia-os/runtime/hardware-settings.toml"
        state_dir = target_root / "var/lib/greia-system-settings"
        store = HardwareSettingsStore.load(defaults, state_dir)
        store.replace(request.hardware_settings)
        if request.wifi_profile is not None:
            try:
                request.wifi_profile.write_to(target_root)
            except OSError as exc:
                raise InstallationError("could not save the selected Wi-Fi network") from exc
        record_dir = target_root / "etc/greia-os"
        record_dir.mkdir(parents=True, exist_ok=True)
        record = {
            "schema_version": 1,
            "installed_at_unix": int(time.time()),
            "target_identity_sha256": request.target.identity_digest,
            "locale": request.locale,
            "hardware_settings": request.hardware_settings.as_json_dict(),
            # Never put SSIDs, profile contents or Wi-Fi credentials into the
            # ordinary installation record. This boolean is enough for support.
            "wifi_configured": request.wifi_profile is not None,
            # Package names are support-state metadata, not raw hardware
            # inventory. Do not persist modaliases, sysfs paths or driver/device
            # serial information in the ordinary installation record.
            "hardware_enablement_complete": (
                hardware_plan.complete if hardware_plan is not None else None
            ),
            "hardware_support_packages": (
                list(hardware_plan.target_packages) if hardware_plan is not None else []
            ),
        }
        (record_dir / "install-record.json").write_text(
            json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        self.runner.run(
            [
                "chroot",
                str(target_root),
                "chown",
                "-R",
                "greiapanel:pipsettings",
                "/var/lib/greia-system-settings",
            ]
        )
        self.runner.run(
            ["chroot", str(target_root), "chmod", "2750", "/var/lib/greia-system-settings"]
        )
        self.runner.run(
            [
                "chroot",
                str(target_root),
                "chmod",
                "0640",
                "/var/lib/greia-system-settings/settings.json",
            ]
        )
