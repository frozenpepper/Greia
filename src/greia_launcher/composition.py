from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from greia_platform.activities import RuntimeCatalogue
from greia_platform.device_capabilities import (
    DeviceCapabilityService,
    HALDeviceCapabilityProbe,
)
from greia_platform.hal import (
    GreiaHAL,
    LegacyXDisplayHAL,
    LegacyXInputHAL,
    LinuxAudioHAL,
    LinuxNetworkHAL,
    LinuxRemovableMediaHAL,
    SystemdPowerHAL,
)
from greia_platform.hardware_session import XSessionHardwareController
from greia_platform.permissions import PermissionBroker

from .runtime_adapter import PythonRuntimeAdapter, PythonRuntimePolicy, RuntimeManager


@dataclass(frozen=True, slots=True)
class LauncherRuntimeServices:
    """Trusted shared dependencies for Activity launch decisions."""

    device_capabilities: DeviceCapabilityService
    permission_broker: PermissionBroker
    runtime_manager: RuntimeManager


def provisional_installed_hal() -> GreiaHAL:
    """Compose the current installed R6 HAL without blessing legacy X as final.

    R7 replaces the display/input implementations below this semantic boundary.
    Keeping composition here prevents PermissionBroker or runtime code from
    probing hardware independently.
    """

    x_controller = XSessionHardwareController()
    return GreiaHAL(
        display=LegacyXDisplayHAL(x_controller),
        input=LegacyXInputHAL(x_controller),
        audio=LinuxAudioHAL(),
        removable_media=LinuxRemovableMediaHAL(),
        network=LinuxNetworkHAL(),
        power=SystemdPowerHAL(),
    )


def build_launcher_runtime_services(
    runtime: RuntimeCatalogue,
    *,
    runtime_policy_path: Path,
    permission_policy_path: Path,
    hal: GreiaHAL | None = None,
    python_executable: Path | None = None,
) -> LauncherRuntimeServices:
    """Build one shared device-authority path for permissions and runtimes."""

    device_capabilities = DeviceCapabilityService(
        HALDeviceCapabilityProbe(hal or provisional_installed_hal())
    )
    permission_broker = PermissionBroker.phase0(
        runtime,
        permission_policy_path,
        device_capabilities=device_capabilities,
    )
    runtime_manager = RuntimeManager(
        [
            PythonRuntimeAdapter(
                python_executable,
                policy=PythonRuntimePolicy.load(runtime_policy_path),
            )
        ],
        device_capabilities,
    )
    return LauncherRuntimeServices(
        device_capabilities=device_capabilities,
        permission_broker=permission_broker,
        runtime_manager=runtime_manager,
    )
