from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol, Sequence


_PACKAGE_RE = re.compile(r"^[a-z0-9][a-z0-9+.-]*$")
_MAX_MODALIAS_BYTES = 1024
_MAX_SYSFS_PATH_CHARACTERS = 512
_MAX_SUBSYSTEM_CHARACTERS = 64
_MAX_DRIVER_CHARACTERS = 128


class HardwareEnablementError(RuntimeError):
    """Raised when trusted hardware-enablement state cannot be represented safely."""


@dataclass(frozen=True, slots=True)
class HardwareDevice:
    """Bounded vendor-neutral Linux device observation.

    Human-readable product names and serial numbers are intentionally absent.
    Package resolution should use the kernel modalias rather than a Greia-owned
    PCI/USB product database.
    """

    sysfs_path: str
    subsystem: str
    modalias: str
    driver: str = ""

    def __post_init__(self) -> None:
        if not self.sysfs_path or len(self.sysfs_path) > _MAX_SYSFS_PATH_CHARACTERS:
            raise HardwareEnablementError("hardware sysfs path is missing or too long")
        if len(self.subsystem) > _MAX_SUBSYSTEM_CHARACTERS:
            raise HardwareEnablementError("hardware subsystem name is too long")
        encoded = self.modalias.encode("utf-8")
        if not encoded or len(encoded) > _MAX_MODALIAS_BYTES or "\x00" in self.modalias:
            raise HardwareEnablementError("hardware modalias is missing or too long")
        if len(self.driver) > _MAX_DRIVER_CHARACTERS:
            raise HardwareEnablementError("hardware driver name is too long")


@dataclass(frozen=True, slots=True)
class HardwareInventory:
    """Immutable bounded hardware snapshot suitable for diagnostics and comparison."""

    devices: tuple[HardwareDevice, ...]
    truncated: bool = False
    scan_errors: int = 0

    def __post_init__(self) -> None:
        if self.scan_errors < 0:
            raise HardwareEnablementError("hardware inventory error count cannot be negative")

    @property
    def modaliases(self) -> tuple[str, ...]:
        return tuple(sorted({device.modalias for device in self.devices}))

    @property
    def token(self) -> str:
        encoded = json.dumps(
            {
                "devices": [
                    {
                        "path": device.sysfs_path,
                        "subsystem": device.subsystem,
                        "modalias": device.modalias,
                        "driver": device.driver,
                    }
                    for device in self.devices
                ],
                "truncated": self.truncated,
                "scan_errors": self.scan_errors,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


class HardwareInventoryProvider(Protocol):
    def snapshot(self) -> HardwareInventory: ...


@dataclass(frozen=True, slots=True)
class LinuxSysfsHardwareInventory:
    """Read a bounded modalias inventory from sysfs without following symlinks."""

    sysfs_devices: Path = Path("/sys/devices")
    max_devices: int = 512
    max_directories: int = 8192

    def __post_init__(self) -> None:
        if not 1 <= self.max_devices <= 4096:
            raise ValueError("max_devices must be in [1, 4096]")
        if not 1 <= self.max_directories <= 65536:
            raise ValueError("max_directories must be in [1, 65536]")

    def snapshot(self) -> HardwareInventory:
        devices: list[HardwareDevice] = []
        scan_errors = 0
        directory_count = 0
        truncated = False

        def record_walk_error(_: OSError) -> None:
            nonlocal scan_errors
            scan_errors += 1

        walker = os.walk(
            self.sysfs_devices,
            topdown=True,
            onerror=record_walk_error,
            followlinks=False,
        )
        for current, directories, files in walker:
            directory_count += 1
            if directory_count > self.max_directories:
                truncated = True
                break
            directories.sort()
            files.sort()
            if "modalias" not in files:
                continue
            if len(devices) >= self.max_devices:
                truncated = True
                break
            current_path = Path(current)
            try:
                modalias = _read_bounded_text(current_path / "modalias", _MAX_MODALIAS_BYTES)
                if not modalias:
                    continue
                relative = current_path.relative_to(self.sysfs_devices)
                path_text = "/" if str(relative) == "." else "/" + str(relative)
                devices.append(
                    HardwareDevice(
                        sysfs_path=path_text,
                        subsystem=_symlink_basename(current_path / "subsystem"),
                        modalias=modalias,
                        driver=_symlink_basename(current_path / "driver"),
                    )
                )
            except (OSError, UnicodeError, ValueError, HardwareEnablementError):
                scan_errors += 1

        devices.sort(key=lambda item: (item.subsystem, item.modalias, item.sysfs_path))
        return HardwareInventory(tuple(devices), truncated=truncated, scan_errors=scan_errors)


class SupportKind(StrEnum):
    FIRMWARE = "firmware"
    MICROCODE = "microcode"
    HARDWARE_PACKAGE = "hardware-package"


class SupportDisposition(StrEnum):
    AUTO_ELIGIBLE = "auto-eligible"
    ADVISORY = "advisory"


@dataclass(frozen=True, slots=True)
class HardwareSupportRecommendation:
    package: str
    kind: SupportKind
    disposition: SupportDisposition
    source: str

    def __post_init__(self) -> None:
        if not _PACKAGE_RE.fullmatch(self.package):
            raise HardwareEnablementError(f"invalid Debian package recommendation: {self.package!r}")
        if not self.source or len(self.source) > 64:
            raise HardwareEnablementError("hardware recommendation source is invalid")


@dataclass(frozen=True, slots=True)
class HardwareSupportPlan:
    inventory_token: str
    recommendations: tuple[HardwareSupportRecommendation, ...]
    complete: bool
    diagnostics: tuple[str, ...] = ()

    @property
    def automatic_packages(self) -> tuple[str, ...]:
        if not self.complete:
            return ()
        return tuple(
            recommendation.package
            for recommendation in self.recommendations
            if recommendation.disposition is SupportDisposition.AUTO_ELIGIBLE
        )

    @property
    def advisory_packages(self) -> tuple[str, ...]:
        return tuple(
            recommendation.package
            for recommendation in self.recommendations
            if recommendation.disposition is SupportDisposition.ADVISORY
        )


class HardwareSupportResolver(Protocol):
    def resolve(self, inventory: HardwareInventory) -> HardwareSupportPlan: ...


@dataclass(frozen=True, slots=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


class CommandRunner(Protocol):
    def run(self, command: Sequence[str], *, timeout_seconds: float) -> CommandResult: ...


@dataclass(frozen=True, slots=True)
class SubprocessCommandRunner:
    """Bounded shell-free command execution for trusted platform tools."""

    def run(self, command: Sequence[str], *, timeout_seconds: float) -> CommandResult:
        completed = subprocess.run(
            list(command),
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            shell=False,
        )
        return CommandResult(completed.returncode, completed.stdout, completed.stderr)


_MODULE_NAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


@dataclass(frozen=True, slots=True)
class LoadedModuleIdentity:
    """Kernel module that backs one bound driver, as sysfs reports it."""

    name: str
    loadable: bool


@dataclass(frozen=True, slots=True)
class LinuxKernelModules:
    """Read-only view of the running kernel's module metadata.

    Firmware resolution asks ``modinfo`` (directly, or through isenkram) which
    firmware files each bound module declares.  Both read
    ``/lib/modules/<release>``.  When that tree is hidden — systemd's
    ``ProtectKernelModules=yes`` does exactly that — ``modinfo`` reports
    "module not found", which is indistinguishable from a built-in driver and
    used to resolve to "no firmware needed".  Callers therefore check
    :meth:`metadata_problem` first and treat a problem as an incomplete
    resolution, never as an empty one.
    """

    sysfs_root: Path = Path("/sys")
    modules_root: Path = Path("/lib/modules")
    release: str | None = None

    def metadata_problem(self) -> str | None:
        """Return why module metadata is unreadable, or None when it is usable."""

        release = self.release or os.uname().release
        index = self.modules_root / release / "modules.dep"
        try:
            with index.open("rb") as handle:
                handle.read(1)
        except OSError as exc:
            return (
                f"kernel module metadata is unreadable ({index}: "
                f"{exc.__class__.__name__}); driver firmware cannot be resolved"
            )
        return None

    def module_for_driver(self, subsystem: str, driver: str) -> LoadedModuleIdentity:
        """Name the module behind ``driver`` and whether it is a loadable module.

        The driver name is not always the module name (``rtw_8822ce`` is
        provided by ``rtw88_8822ce``), so sysfs' ``module`` link wins.  Only
        loadable modules have ``/sys/module/<name>/initstate``; built-in
        drivers may legitimately be unknown to ``modinfo``.
        """

        link = self.sysfs_root / "bus" / subsystem / "drivers" / driver / "module"
        try:
            name = os.path.basename(os.readlink(link))
        except (OSError, ValueError):
            return LoadedModuleIdentity(driver, False)
        if not _MODULE_NAME_RE.fullmatch(name):
            return LoadedModuleIdentity(driver, False)
        loadable = (self.sysfs_root / "module" / name / "initstate").is_file()
        return LoadedModuleIdentity(name, loadable)


@dataclass(frozen=True, slots=True)
class IsenkramHardwareSupportResolver:
    """Use Debian's hardware metadata without granting it package-install authority.

    ``isenkram-autoinstall-firmware -l`` is treated as the automatic firmware
    source. General ``isenkram-lookup -l`` results are diagnostic/advisory only
    because that command can recommend unrelated user-space hardware utilities.

    ``kernel_modules`` is wired by production compositions: isenkram reads
    module metadata through ``modinfo`` and its "found nothing" exit is
    otherwise indistinguishable from a sandbox that hides the module tree.
    """

    runner: CommandRunner = SubprocessCommandRunner()
    lookup_command: str = "/usr/bin/isenkram-lookup"
    firmware_command: str = "/usr/sbin/isenkram-autoinstall-firmware"
    timeout_seconds: float = 12.0
    max_recommendations: int = 128
    kernel_modules: LinuxKernelModules | None = None

    def __post_init__(self) -> None:
        if not 1.0 <= self.timeout_seconds <= 60.0:
            raise ValueError("hardware resolver timeout must be in [1, 60] seconds")
        if not 1 <= self.max_recommendations <= 1024:
            raise ValueError("max_recommendations must be in [1, 1024]")

    def resolve(self, inventory: HardwareInventory) -> HardwareSupportPlan:
        diagnostics: list[str] = []
        recommendations: dict[str, HardwareSupportRecommendation] = {}
        complete = not inventory.truncated and inventory.scan_errors == 0

        problem = (
            self.kernel_modules.metadata_problem()
            if self.kernel_modules is not None
            else None
        )
        if problem is not None:
            return HardwareSupportPlan(inventory.token, (), False, (problem,))

        firmware_result = self._run(
            (self.firmware_command, "-l"),
            "firmware",
            diagnostics,
            benign_exit_codes=(1,),
        )
        if firmware_result is None:
            complete = False
        else:
            for package in _package_lines(firmware_result.stdout, self.max_recommendations):
                recommendations[package] = HardwareSupportRecommendation(
                    package,
                    SupportKind.FIRMWARE,
                    SupportDisposition.AUTO_ELIGIBLE,
                    "isenkram-firmware",
                )

        lookup_result = self._run((self.lookup_command, "-l"), "hardware lookup", diagnostics)
        if lookup_result is not None:
            for package in _package_lines(lookup_result.stdout, self.max_recommendations):
                recommendations.setdefault(
                    package,
                    HardwareSupportRecommendation(
                        package,
                        SupportKind.HARDWARE_PACKAGE,
                        SupportDisposition.ADVISORY,
                        "isenkram-lookup",
                    ),
                )

        if inventory.truncated:
            diagnostics.append("hardware inventory was truncated")
        if inventory.scan_errors:
            diagnostics.append(f"hardware inventory scan errors: {inventory.scan_errors}")

        ordered = tuple(
            sorted(
                recommendations.values(),
                key=_recommendation_sort_key,
            )[: self.max_recommendations]
        )
        return HardwareSupportPlan(inventory.token, ordered, complete, tuple(diagnostics))

    def _run(
        self,
        command: Sequence[str],
        label: str,
        diagnostics: list[str],
        *,
        benign_exit_codes: tuple[int, ...] = (),
    ) -> CommandResult | None:
        try:
            result = self.runner.run(command, timeout_seconds=self.timeout_seconds)
        except (OSError, subprocess.TimeoutExpired) as exc:
            diagnostics.append(f"{label} unavailable: {exc.__class__.__name__}")
            return None
        if result.returncode != 0:
            # ``isenkram-autoinstall-firmware -l`` exits 1 when it found no
            # firmware files requested by loaded kernel modules. On a healthy
            # machine that is the expected outcome, not a resolution failure.
            if result.returncode in benign_exit_codes:
                return result
            diagnostics.append(f"{label} failed with exit {result.returncode}")
            return None
        return result


@dataclass(frozen=True, slots=True)
class X86MicrocodeResolver:
    """Small architecture-level policy for signed Debian CPU microcode packages."""

    cpuinfo: Path = Path("/proc/cpuinfo")

    def resolve(self, inventory: HardwareInventory) -> HardwareSupportPlan:
        package = self._package()
        recommendations: tuple[HardwareSupportRecommendation, ...] = ()
        diagnostics: tuple[str, ...] = ()
        complete = True
        if package:
            recommendations = (
                HardwareSupportRecommendation(
                    package,
                    SupportKind.MICROCODE,
                    SupportDisposition.AUTO_ELIGIBLE,
                    "x86-cpu-vendor",
                ),
            )
        elif self.cpuinfo.exists():
            diagnostics = ("CPU vendor has no Greia x86 microcode package policy",)
        else:
            complete = False
            diagnostics = ("CPU information is unavailable",)
        return HardwareSupportPlan(inventory.token, recommendations, complete, diagnostics)

    def _package(self) -> str:
        try:
            text = _read_text_prefix(self.cpuinfo, 64 * 1024)
        except (OSError, UnicodeError):
            return ""
        vendors = {
            line.split(":", 1)[1].strip()
            for line in text.splitlines()
            if line.startswith("vendor_id") and ":" in line
        }
        if "GenuineIntel" in vendors:
            return "intel-microcode"
        if "AuthenticAMD" in vendors:
            return "amd64-microcode"
        return ""


@dataclass(frozen=True, slots=True)
class CompositeHardwareSupportResolver:
    resolvers: tuple[HardwareSupportResolver, ...]
    max_recommendations: int = 256

    def resolve(self, inventory: HardwareInventory) -> HardwareSupportPlan:
        recommendations: dict[str, HardwareSupportRecommendation] = {}
        diagnostics: list[str] = []
        complete = True
        for resolver in self.resolvers:
            plan = resolver.resolve(inventory)
            complete = complete and plan.complete
            diagnostics.extend(plan.diagnostics)
            for item in plan.recommendations:
                existing = recommendations.get(item.package)
                if existing is None or (
                    existing.disposition is SupportDisposition.ADVISORY
                    and item.disposition is SupportDisposition.AUTO_ELIGIBLE
                ):
                    recommendations[item.package] = item
        ordered = tuple(
            sorted(recommendations.values(), key=_recommendation_sort_key)[: self.max_recommendations]
        )
        return HardwareSupportPlan(inventory.token, ordered, complete, tuple(diagnostics))


def _recommendation_sort_key(item: HardwareSupportRecommendation) -> tuple[int, str, str]:
    priority = 0 if item.disposition is SupportDisposition.AUTO_ELIGIBLE else 1
    return (priority, item.kind.value, item.package)


def _package_lines(output: str, limit: int) -> tuple[str, ...]:
    packages: list[str] = []
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not _PACKAGE_RE.fullmatch(line):
            continue
        if line not in packages:
            packages.append(line)
        if len(packages) >= limit:
            break
    return tuple(packages)


def _read_bounded_text(path: Path, max_bytes: int) -> str:
    with path.open("rb") as handle:
        payload = handle.read(max_bytes + 1)
    if len(payload) > max_bytes:
        raise ValueError(f"bounded hardware file exceeds {max_bytes} bytes")
    return payload.decode("utf-8").strip()


def _read_text_prefix(path: Path, max_bytes: int) -> str:
    with path.open("rb") as handle:
        payload = handle.read(max_bytes)
    return payload.decode("utf-8", errors="strict")


def _symlink_basename(path: Path) -> str:
    try:
        target = os.readlink(path)
    except OSError:
        return ""
    return Path(target).name
