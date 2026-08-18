"""Real Greia runtime composition for a synthetic simulator device."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping

from greia_launcher.child_shell import ProfileVisualActivitySupervisor
from greia_launcher.composition import LauncherRuntimeServices
from greia_launcher.runtime_adapter import (
    PythonRuntimeAdapter,
    PythonRuntimePolicy,
    RuntimeCommand,
    RuntimeManager,
)
from greia_platform.activities import ActivityManifest, RuntimeCatalogue
from greia_platform.device_capabilities import DeviceCapabilityService, HALDeviceCapabilityProbe
from greia_platform.history import PlatformHistoryService
from greia_platform.permissions import PermissionBroker
from greia_platform.storage import ActivityStorageService, StoragePolicy

from .device import SimulatedDeviceProfile


class SimulatorPythonRuntimeAdapter(PythonRuntimeAdapter):
    """Python runtime using the real adapter contract plus a simulator display shim."""

    def command_for(self, manifest: ActivityManifest) -> RuntimeCommand:
        return RuntimeCommand(
            command=(
                str(self.resolve_interpreter()),
                "-m",
                "greia_simulator.python_activity",
                str(manifest.launch_path),
            ),
            cwd=manifest.root,
            environment=(
                ("PYTHONNOUSERSITE", "1"),
                ("PYTHONDONTWRITEBYTECODE", "1"),
            ),
        )


class SimulatorActivitySupervisor(ProfileVisualActivitySupervisor):
    """Production-equivalent launch supervision with synthetic display context only."""

    @staticmethod
    def _sanitized_environment(
        manifest,
        profile,
        authority,
        session_id: str,
        *,
        sandboxed: bool = False,
        storage_broker=None,
        event_broker=None,
        runtime_environment: tuple[tuple[str, str], ...] = (),
        lifecycle_environment: tuple[tuple[str, str], ...] = (),
        display_environment: Mapping[str, str] | None = None,
    ) -> dict[str, str]:
        environment = ProfileVisualActivitySupervisor._sanitized_environment(
            manifest,
            profile,
            authority,
            session_id,
            sandboxed=sandboxed,
            storage_broker=storage_broker,
            event_broker=event_broker,
            runtime_environment=runtime_environment,
            lifecycle_environment=lifecycle_environment,
            display_environment=display_environment,
        )
        device = SimulatedDeviceProfile.from_environment()
        source_root = Path(
            os.environ.get(
                "GREIA_SIMULATOR_PYTHONPATH",
                str(Path(os.environ["GREIA_OS_ROOT"]) / "src"),
            )
        ).resolve(strict=True)
        environment["GREIA_SIMULATOR"] = "1"
        environment["GREIA_SIMULATOR_VIEWPORT"] = device.viewport
        environment["PYTHONPATH"] = str(source_root)
        return environment


def build_simulator_runtime_services(
    runtime: RuntimeCatalogue,
    activities: tuple[ActivityManifest, ...],
    *,
    runtime_policy_path: Path,
    permission_policy_path: Path,
    storage_policy_path: Path,
    history_policy_path: Path,
    progression_policy_path: Path,
    device: SimulatedDeviceProfile,
    python_executable: Path | None = None,
) -> LauncherRuntimeServices:
    """Compose normal Greia services over one explicit synthetic HAL.

    Nothing above the HAL/runtime-adapter seams is reimplemented here. This is
    the alignment invariant that makes simulator behavior useful to Activity
    authors instead of becoming an independently drifting mock OS.
    """

    device_capabilities = DeviceCapabilityService(HALDeviceCapabilityProbe(device.to_hal()))
    permission_broker = PermissionBroker.phase0(
        runtime,
        permission_policy_path,
        device_capabilities=device_capabilities,
    )
    runtime_manager = RuntimeManager(
        [
            SimulatorPythonRuntimeAdapter(
                python_executable,
                policy=PythonRuntimePolicy.load(runtime_policy_path),
            )
        ],
        device_capabilities,
    )
    storage_service = ActivityStorageService(StoragePolicy.load(storage_policy_path))
    history_service = PlatformHistoryService.load(
        history_policy_path,
        progression_policy_path,
        activities,
    )
    return LauncherRuntimeServices(
        device_capabilities=device_capabilities,
        permission_broker=permission_broker,
        runtime_manager=runtime_manager,
        storage_service=storage_service,
        history_service=history_service,
    )


__all__ = [
    "SimulatorActivitySupervisor",
    "SimulatorPythonRuntimeAdapter",
    "build_simulator_runtime_services",
]
