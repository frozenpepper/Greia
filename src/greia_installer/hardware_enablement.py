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
    LinuxKernelModules,
    LinuxSysfsHardwareInventory,
    LoadedModuleIdentity,
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
    #: Production compositions wire this so a hidden module tree, and a
    #: loaded module that ``modinfo`` cannot describe, make the resolution
    #: incomplete instead of silently "no firmware needed".
    kernel_modules: LinuxKernelModules | None = None

    def __post_init__(self) -> None:
        if not 1.0 <= self.timeout_seconds <= 30.0:
            raise ValueError("modinfo timeout must be in [1, 30] seconds")

    def resolve(self, inventory: HardwareInventory) -> HardwareSupportPlan:
        diagnostics: list[str] = []
        recommendations: dict[str, HardwareSupportRecommendation] = {}
        complete = not inventory.truncated and inventory.scan_errors == 0
        if self.kernel_modules is not None:
            problem = self.kernel_modules.metadata_problem()
            if problem is not None:
                return HardwareSupportPlan(inventory.token, (), False, (problem,))

        bound = sorted(
            {
                (device.subsystem, device.driver)
                for device in inventory.devices
                if device.driver and _DRIVER_RE.fullmatch(device.driver)
            }
        )
        if len(bound) > _MAX_BOUND_DRIVERS:
            diagnostics.append("bound driver inventory exceeded firmware resolver bound")
            bound = bound[:_MAX_BOUND_DRIVERS]
        modules: dict[str, tuple[str, bool]] = {}
        for subsystem, driver in bound:
            if self.kernel_modules is None or not subsystem:
                identity = LoadedModuleIdentity(driver, False)
            else:
                identity = self.kernel_modules.module_for_driver(subsystem, driver)
            known = modules.get(identity.name)
            modules[identity.name] = (
                known[0] if known else driver,
                identity.loadable or (known[1] if known else False),
            )

        for module, (driver, loadable) in modules.items():
            label = driver if module == driver else f"{driver} (module {module})"
            try:
                result = self.runner.run(
                    (self.modinfo_command, "-F", "firmware", module),
                    timeout_seconds=self.timeout_seconds,
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                complete = False
                diagnostics.append(
                    f"firmware metadata unavailable for bound driver {label}: {exc.__class__.__name__}"
                )
                continue
            if result.returncode != 0:
                # Built-in platform drivers (acpi-wmi, ec, serial8250, ...) are
                # not loadable modules, so modinfo may not know them. That is
                # expected. A *loaded* module that modinfo cannot describe is
                # not: its firmware would silently be left out of the target.
                if result.returncode == 1 and not loadable:
                    continue
                complete = False
                diagnostics.append(
                    f"firmware metadata lookup failed for bound driver {label}: exit {result.returncode}"
                )
                continue
            declarations = _firmware_declarations(result.stdout)
            for declaration in declarations:
                try:
                    providers = self.pool.packages_for_firmware(declaration)
                except HardwareSupportPoolError:
                    diagnostics.append(
                        f"bound driver {label} exposed an invalid firmware declaration"
                    )
                    continue
                if not providers:
                    diagnostics.append(
                        f"no frozen Debian firmware provider matched {label}:{declaration}"
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
            complete=complete,
            diagnostics=tuple(diagnostics),
        )


@dataclass(frozen=True, slots=True)
class _FixedInventoryProvider:
    """Replay one already-taken inventory snapshot (single-snapshot authority).

    Lets callers that already attested a snapshot (fresh-install seams)
    resolve hardware selection against that exact snapshot instead of
    taking a second racy one.
    """

    snapshot_value: HardwareInventory

    def snapshot(self) -> HardwareInventory:
        return self.snapshot_value


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
                "required hardware packages are absent from this installer media: "
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
        inventory_snapshot: HardwareInventory | None = None,
    ) -> "InstallerHardwareEnablementPlanner":
        machine_id = (machine or platform.machine() or "unknown").lower()
        kernel_modules = LinuxKernelModules(sysfs_root=sysfs_devices.parent)
        resolvers: list[HardwareSupportResolver] = [
            BoundDriverFirmwareResolver(pool, kernel_modules=kernel_modules),
            IsenkramHardwareSupportResolver(kernel_modules=kernel_modules),
        ]
        if machine_id in {"i386", "i486", "i586", "i686", "x86_64", "amd64"}:
            resolvers.append(X86MicrocodeResolver(cpuinfo))
        if inventory_snapshot is not None:
            provider: HardwareInventoryProvider = _FixedInventoryProvider(
                inventory_snapshot
            )
        else:
            provider = LinuxSysfsHardwareInventory(sysfs_devices)
        return cls(
            inventory_provider=provider,
            resolver=CompositeHardwareSupportResolver(tuple(resolvers)),
            pool=pool,
        )


def merge_hardware_enablement_plans(
    initial: InstallerHardwareEnablementPlan,
    refreshed: InstallerHardwareEnablementPlan,
) -> InstallerHardwareEnablementPlan:
    """Add late-discovered support to a complete pre-erase hardware plan.

    The pre-erase plan remains the safety authority.  A second inventory taken
    just before target configuration may see a driver that bound later (for
    example a wireless module whose firmware/interface was still coming up
    while the installer copied the payload).  Its extra verified packages are
    merged into the initial list; an incomplete refresh can only leave the
    initial decision unchanged.
    """

    if not refreshed.complete:
        return initial
    return InstallerHardwareEnablementPlan(
        inventory=refreshed.inventory,
        resolver_plan=refreshed.resolver_plan,
        required_firmware=tuple(
            sorted(set(initial.required_firmware) | set(refreshed.required_firmware))
        ),
        required_microcode=tuple(
            sorted(set(initial.required_microcode) | set(refreshed.required_microcode))
        ),
        missing_packages=tuple(
            sorted(set(initial.missing_packages) | set(refreshed.missing_packages))
        ),
        diagnostics=tuple(
            dict.fromkeys((*initial.diagnostics, *refreshed.diagnostics))
        ),
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
