from __future__ import annotations

import platform
from dataclasses import dataclass
from pathlib import Path

from greia_platform.hardware_enablement import (
    CompositeHardwareSupportResolver,
    HardwareInventory,
    HardwareInventoryProvider,
    HardwareSupportPlan,
    HardwareSupportResolver,
    IsenkramHardwareSupportResolver,
    LinuxSysfsHardwareInventory,
    SupportDisposition,
    SupportKind,
    X86MicrocodeResolver,
)

from .hardware_support import VerifiedHardwareSupportPool


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
        resolvers: list[HardwareSupportResolver] = [IsenkramHardwareSupportResolver()]
        if machine_id in {"i386", "i486", "i586", "i686", "x86_64", "amd64"}:
            resolvers.append(X86MicrocodeResolver(cpuinfo))
        return cls(
            inventory_provider=LinuxSysfsHardwareInventory(sysfs_devices),
            resolver=CompositeHardwareSupportResolver(tuple(resolvers)),
            pool=pool,
        )
