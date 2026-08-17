from __future__ import annotations

import json
import platform
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from greia_platform.hardware_enablement import (
    CommandRunner,
    CompositeHardwareSupportResolver,
    HardwareInventory,
    HardwareInventoryProvider,
    HardwareSupportPlan,
    HardwareSupportRecommendation,
    HardwareSupportResolver,
    IsenkramHardwareSupportResolver,
    LinuxSysfsHardwareInventory,
    SubprocessCommandRunner,
    SupportDisposition,
    SupportKind,
    X86MicrocodeResolver,
)

from .hardware_support import HardwareSupportPoolError, VerifiedHardwareSupportPool


_DRIVER_RE = re.compile(r"^[A-Za-z0-9_.+-]{1,128}$")
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
_MAX_BOUND_DRIVERS = 256
_MAX_FIRMWARE_DECLARATIONS_PER_DRIVER = 256
_MAX_FIRMWARE_DECLARATION_BYTES = 1024


class HardwareEnablementPlanError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class TargetImageHardwareIdentity:
    """The target payload's distro identity relevant to local package selection."""

    suite: str
    architecture: str

    def __post_init__(self) -> None:
        if not _ID_RE.fullmatch(self.suite):
            raise HardwareEnablementPlanError("target image suite is invalid")
        if not _ID_RE.fullmatch(self.architecture):
            raise HardwareEnablementPlanError("target image architecture is invalid")

    @classmethod
    def load(cls, path: Path) -> "TargetImageHardwareIdentity":
        if path.is_symlink() or not path.is_file():
            raise HardwareEnablementPlanError("target image profile is missing or unsafe")
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise HardwareEnablementPlanError("target image profile is unreadable") from exc
        try:
            base = raw["base"]
            suite = base["suite"]
            architecture = base["architecture"]
        except (KeyError, TypeError) as exc:
            raise HardwareEnablementPlanError("target image profile has no base identity") from exc
        if not isinstance(suite, str) or not isinstance(architecture, str):
            raise HardwareEnablementPlanError("target image profile base identity is invalid")
        return cls(suite, architecture)


@dataclass(frozen=True, slots=True)
class InstallerHardwareEnablementPlan:
    """One fail-closed installer decision derived from current hardware and media."""

    inventory: HardwareInventory
    resolver_plan: HardwareSupportPlan
    required_firmware: tuple[str, ...]
    required_microcode: tuple[str, ...]
    missing_packages: tuple[str, ...]
    diagnostics: tuple[str, ...]

    @property
    def complete(self) -> bool:
        return self.resolver_plan.complete and not self.missing_packages

    @property
    def target_packages(self) -> tuple[str, ...]:
        if not self.complete:
            return ()
        return tuple(dict.fromkeys((*self.required_firmware, *self.required_microcode)))

    @property
    def degraded(self) -> bool:
        return not self.complete


@dataclass(frozen=True, slots=True)
class BoundDriverFirmwareResolver:
    """Resolve firmware declared by the drivers actually bound to this machine.

    Kernel modules describe firmware through modinfo metadata. The resulting
    firmware names/patterns are mapped only through the already-verified Debian
    provider map frozen into the Greia installer media; driver/vendor names do
    not become package-selection rules.
    """

    pool: VerifiedHardwareSupportPool
    runner: CommandRunner = SubprocessCommandRunner()
    modinfo_command: str = "/sbin/modinfo"
    timeout_seconds: float = 5.0

    def __post_init__(self) -> None:
        if not 1.0 <= self.timeout_seconds <= 30.0:
            raise ValueError("modinfo timeout must be in [1, 30] seconds")

    def resolve(self, inventory: HardwareInventory) -> HardwareSupportPlan:
        diagnostics: list[str] = []
        recommendations: dict[str, HardwareSupportRecommendation] = {}
        drivers = tuple(
            sorted(
                {
                    device.driver
                    for device in inventory.devices
                    if device.driver and _DRIVER_RE.fullmatch(device.driver)
                }
            )
        )
        if len(drivers) > _MAX_BOUND_DRIVERS:
            diagnostics.append("bound driver inventory exceeded firmware resolver bound")
            drivers = drivers[:_MAX_BOUND_DRIVERS]

        for driver in drivers:
            try:
                result = self.runner.run(
                    (self.modinfo_command, "-F", "firmware", driver),
                    timeout_seconds=self.timeout_seconds,
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                diagnostics.append(
                    f"firmware metadata unavailable for bound driver {driver}: {exc.__class__.__name__}"
                )
                continue
            if result.returncode != 0:
                # Built-in platform drivers (acpi-wmi, ec, serial8250, ...) are
                # not loadable modules, so modinfo cannot describe their
                # firmware. That is expected, not a resolution failure.
                if result.returncode != 1:
                    diagnostics.append(
                        f"firmware metadata lookup failed for bound driver {driver}: exit {result.returncode}"
                    )
                continue
            declarations = _firmware_declarations(result.stdout)
            for declaration in declarations:
                try:
                    providers = self.pool.packages_for_firmware(declaration)
                except HardwareSupportPoolError:
                    diagnostics.append(
                        f"bound driver {driver} exposed an invalid firmware declaration"
                    )
                    continue
                if not providers:
                    diagnostics.append(
                        f"no frozen Debian firmware provider matched {driver}:{declaration}"
                    )
                    continue
                for package in providers:
                    recommendations[package] = HardwareSupportRecommendation(
                        package,
                        SupportKind.FIRMWARE,
                        SupportDisposition.AUTO_ELIGIBLE,
                        "bound-driver-modinfo",
                    )

        return HardwareSupportPlan(
            inventory.token,
            tuple(sorted(recommendations.values(), key=lambda item: item.package)),
            complete=not inventory.truncated and inventory.scan_errors == 0,
            diagnostics=tuple(diagnostics),
        )


class InstallerHardwareEnablementPlanner:
    """Resolve the current machine against one already-verified support pool."""

    def __init__(
        self,
        *,
        inventory_provider: HardwareInventoryProvider,
        resolver: HardwareSupportResolver,
        pool: VerifiedHardwareSupportPool,
    ) -> None:
        self._inventory_provider = inventory_provider
        self._resolver = resolver
        self._pool = pool

    def plan(self) -> InstallerHardwareEnablementPlan:
        inventory = self._inventory_provider.snapshot()
        resolution = self._resolver.resolve(inventory)
        diagnostics = list(resolution.diagnostics)
        required_firmware: list[str] = []
        required_microcode: list[str] = []
        missing: list[str] = []

        if not resolution.complete:
            diagnostics.append(
                "automatic hardware enablement is incomplete; target package installation is suppressed"
            )
        else:
            for item in resolution.recommendations:
                # isenkram's broad modalias lookup is advisory because it can
                # suggest user-space utilities. A recommendation becomes safe
                # automatic firmware only when the independently verified pool
                # classifies that exact package as firmware.
                if (
                    item.disposition is SupportDisposition.ADVISORY
                    and item.kind is SupportKind.HARDWARE_PACKAGE
                    and item.package in self._pool.provided_firmware
                ):
                    required_firmware.append(item.package)
                    continue
                if item.disposition is not SupportDisposition.AUTO_ELIGIBLE:
                    continue
                if item.kind is SupportKind.FIRMWARE:
                    if item.package in self._pool.provided_firmware:
                        required_firmware.append(item.package)
                    else:
                        missing.append(item.package)
                elif item.kind is SupportKind.MICROCODE:
                    if item.package in self._pool.provided_microcode:
                        required_microcode.append(item.package)
                    else:
                        missing.append(item.package)
                else:
                    diagnostics.append(
                        f"ignored non-firmware automatic recommendation: {item.package}"
                    )

        if missing:
            diagnostics.append(
                "required signed hardware packages are absent from this installer media: "
                + ", ".join(sorted(set(missing)))
            )

        return InstallerHardwareEnablementPlan(
            inventory=inventory,
            resolver_plan=resolution,
            required_firmware=tuple(sorted(set(required_firmware))),
            required_microcode=tuple(sorted(set(required_microcode))),
            missing_packages=tuple(sorted(set(missing))),
            diagnostics=tuple(diagnostics),
        )

    @classmethod
    def linux_default(
        cls,
        *,
        pool: VerifiedHardwareSupportPool,
        machine: str | None = None,
        sysfs_devices: Path = Path("/sys/devices"),
        cpuinfo: Path = Path("/proc/cpuinfo"),
    ) -> "InstallerHardwareEnablementPlanner":
        machine_id = (machine or platform.machine() or "unknown").lower()
        resolvers: list[HardwareSupportResolver] = [
            BoundDriverFirmwareResolver(pool),
            IsenkramHardwareSupportResolver(),
        ]
        if machine_id in {"i386", "i486", "i586", "i686", "x86_64", "amd64"}:
            resolvers.append(X86MicrocodeResolver(cpuinfo))
        return cls(
            inventory_provider=LinuxSysfsHardwareInventory(sysfs_devices),
            resolver=CompositeHardwareSupportResolver(tuple(resolvers)),
            pool=pool,
        )


def _firmware_declarations(output: str) -> tuple[str, ...]:
    declarations: list[str] = []
    for raw_line in output.splitlines():
        value = raw_line.strip()
        if not value:
            continue
        try:
            encoded = value.encode("utf-8")
        except UnicodeError:
            continue
        if len(encoded) > _MAX_FIRMWARE_DECLARATION_BYTES:
            continue
        if value not in declarations:
            declarations.append(value)
        if len(declarations) >= _MAX_FIRMWARE_DECLARATIONS_PER_DRIVER:
            break
    return tuple(declarations)
