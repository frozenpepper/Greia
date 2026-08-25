from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from greia_platform.activities import ActivityManifest, RuntimeCatalogue
from greia_platform.achievements import ProfileAchievementService
from greia_platform.device_capabilities import (
    DeviceCapabilityService,
    HALDeviceCapabilityProbe,
)
from greia_platform.hal import (
    GreiaHAL,
    LinuxAudioHAL,
    LinuxNetworkHAL,
    LinuxRemovableMediaHAL,
    SystemdPowerHAL,
)
from greia_platform.hal_legacy_x import (
    LegacyXDisplayHAL,
    LegacyXHardwareSessionController,
    LegacyXInputHAL,
)
from greia_platform.history import (
    HistoryPolicy,
    HistoryPolicyError,
    PlatformHistoryService,
    ProgressionPolicy,
)
from greia_platform.permissions import PermissionBroker
from greia_platform.storage import ActivityStorageService, StoragePolicy

from .display_session import DisplaySessionCoordinator
from .display_session_legacy_x import LegacyXDisplaySessionBackend
from .runtime_adapter import (
    PythonRuntimeAdapter,
    PythonRuntimePolicy,
    RuntimeLaunchAdapter,
    RuntimeManager,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class LauncherRuntimeServices:
    """Trusted shared dependencies for Activity launch decisions."""

    device_capabilities: DeviceCapabilityService
    permission_broker: PermissionBroker
    runtime_manager: RuntimeManager
    storage_service: ActivityStorageService
    history_service: PlatformHistoryService
    achievement_service: ProfileAchievementService | None = None


def provisional_installed_hal() -> GreiaHAL:
    """Compose the current installed R6 HAL without blessing legacy X as final.

    R7 replaces the display/input implementations below this semantic boundary.
    Keeping composition here prevents PermissionBroker or runtime code from
    probing hardware independently.
    """

    x_controller = LegacyXHardwareSessionController()
    return GreiaHAL(
        display=LegacyXDisplayHAL(x_controller),
        input=LegacyXInputHAL(x_controller),
        audio=LinuxAudioHAL(),
        removable_media=LinuxRemovableMediaHAL(),
        network=LinuxNetworkHAL(),
        power=SystemdPowerHAL(),
    )


def provisional_installed_display_session() -> DisplaySessionCoordinator:
    """Compose the current X11 compatibility session behind the R7 contract.

    This deliberately preserves the existing production Xorg/xinit mechanism.
    Replacing this factory with a measured direct/compositor backend must not
    require changes to ActivitySupervisor or Activity runtime APIs.
    """

    return DisplaySessionCoordinator(LegacyXDisplaySessionBackend())


def default_runtime_adapters(
    runtime_policy_path: Path,
    *,
    python_executable: Path | None = None,
) -> tuple[RuntimeLaunchAdapter, ...]:
    """Return the canonical runtime-adapter set for ordinary Greia composition.

    Synthetic/development compositions may inject another adapter set into
    ``build_launcher_runtime_services``. Permission, storage, history and
    device-authority composition stay here regardless of that variation.
    """

    return (
        PythonRuntimeAdapter(
            python_executable,
            policy=PythonRuntimePolicy.load(runtime_policy_path),
        ),
    )


def load_runtime_progression_policy(
    progression_policy_path: Path,
    activities: tuple[ActivityManifest, ...],
) -> ProgressionPolicy:
    """Load optional progression enrichment without making it boot authority.

    Source/build validation should continue to call ``ProgressionPolicy.load``
    directly and fail loudly on malformed policy or undeclared events. The
    installed launcher has a different availability requirement: if progression
    policy is stale/corrupt, child Activity launch and history must remain
    available. In that case progression is disabled for this launcher instance
    and the defect is left visible in the journal.
    """

    try:
        return ProgressionPolicy.load(progression_policy_path, activities)
    except HistoryPolicyError as exc:
        logger.error(
            "Progression policy is invalid at runtime; disabling progression "
            "for this launcher instance: %s",
            exc,
        )
        return ProgressionPolicy(schema_version=1, rules=())


def build_launcher_runtime_services(
    runtime: RuntimeCatalogue,
    activities: tuple[ActivityManifest, ...],
    *,
    runtime_policy_path: Path,
    permission_policy_path: Path,
    storage_policy_path: Path,
    history_policy_path: Path,
    progression_policy_path: Path,
    achievement_policy_path: Path | None = None,
    hal: GreiaHAL | None = None,
    python_executable: Path | None = None,
    runtime_adapters: (
        Sequence[RuntimeLaunchAdapter] | Mapping[str, RuntimeLaunchAdapter] | None
    ) = None,
) -> LauncherRuntimeServices:
    """Build the shared device/runtime/permission/history/achievement authorities.

    ``hal`` and ``runtime_adapters`` are deliberate variation seams. Callers
    must inject only those missing-machine/runtime facts; they must not rebuild
    PermissionBroker, storage, history or achievement composition in parallel.

    History storage bounds remain startup/safety authority and fail closed.
    Progression and achievements are child-facing enrichment: malformed or stale
    enrichment is disabled with diagnostics rather than taking down Greia Shell.
    """

    device_capabilities = DeviceCapabilityService(
        HALDeviceCapabilityProbe(hal or provisional_installed_hal())
    )
    permission_broker = PermissionBroker.phase0(
        runtime,
        permission_policy_path,
        device_capabilities=device_capabilities,
    )
    adapters = (
        runtime_adapters
        if runtime_adapters is not None
        else default_runtime_adapters(
            runtime_policy_path,
            python_executable=python_executable,
        )
    )
    runtime_manager = RuntimeManager(adapters, device_capabilities)
    storage_service = ActivityStorageService(StoragePolicy.load(storage_policy_path))
    history_service = PlatformHistoryService(
        HistoryPolicy.load(history_policy_path),
        load_runtime_progression_policy(progression_policy_path, activities),
    )

    resolved_achievement_policy = (
        achievement_policy_path
        if achievement_policy_path is not None
        else history_policy_path.parent / "achievement-policy.toml"
    )
    achievement_service: ProfileAchievementService | None = None
    try:
        achievement_service = ProfileAchievementService.load(
            resolved_achievement_policy,
            activities,
            history_service,
        )
    except (OSError, RuntimeError, ValueError):
        # Achievements are child-facing enrichment, not a launch/safety authority.
        # Disable badge presentation without taking down the launcher.
        achievement_service = None

    return LauncherRuntimeServices(
        device_capabilities=device_capabilities,
        permission_broker=permission_broker,
        runtime_manager=runtime_manager,
        storage_service=storage_service,
        history_service=history_service,
        achievement_service=achievement_service,
    )
