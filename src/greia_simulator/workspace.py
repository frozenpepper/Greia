"""Isolated, portable simulator workspace built from real Greia state services."""

from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

from greia_platform.activities import ActivityRegistry, RuntimeCatalogue
from greia_platform.activity_packages import ActivityInstallReceipt, ActivityPackageService
from greia_platform.profiles import ProfileStore
from greia_platform.trust import ActivitySource, PackageTrust
from greia_platform.ui_preferences import InterfaceSize, UiPreferencesStore

from .device import SimulatedDeviceProfile


_IGNORED_DEVELOPMENT_NAMES = frozenset(
    {".git", ".hg", ".svn", "__pycache__", ".pytest_cache", ".mypy_cache"}
)


@dataclass(frozen=True, slots=True)
class SimulatorWorkspace:
    """Own all synthetic-device state without mutating the Greia checkout."""

    repo_root: Path
    state_root: Path

    def __post_init__(self) -> None:
        repo_root = self.repo_root.resolve(strict=True)
        state_root = self.state_root.expanduser().resolve(strict=False)
        if not (repo_root / "runtime" / "child-runtime.toml").is_file():
            raise ValueError("repo_root is not a Greia source checkout")
        if state_root == repo_root or repo_root in state_root.parents:
            raise ValueError("simulator state must live outside the Greia source tree")
        object.__setattr__(self, "repo_root", repo_root)
        object.__setattr__(self, "state_root", state_root)

    @property
    def profiles_root(self) -> Path:
        return self.state_root / "profiles"

    @property
    def run_root(self) -> Path:
        return self.state_root / "run"

    @property
    def developer_root(self) -> Path:
        return self.state_root / "developer-activities"

    @property
    def package_root(self) -> Path:
        return self.state_root / "activity-packages"

    @property
    def media_root(self) -> Path:
        return self.state_root / "media"

    def ensure(self) -> None:
        for path in (
            self.state_root,
            self.profiles_root,
            self.run_root,
            self.developer_root,
            self.package_root,
            self.media_root,
        ):
            path.mkdir(parents=True, exist_ok=True)

    def environment(
        self,
        device: SimulatedDeviceProfile,
        *,
        interface_size: str | InterfaceSize = InterfaceSize.NORMAL,
    ) -> dict[str, str]:
        """Return an isolated environment suitable for the real child shell."""

        self.ensure()
        self.set_default_interface_size(interface_size)
        capabilities = ",".join(sorted(device.capabilities))
        return {
            "GREIA_OS_ROOT": str(self.repo_root),
            "GREIA_PROFILES_DIR": str(self.profiles_root),
            "GREIA_ACTIVE_PROFILE_STATUS": str(self.run_root / "active-profile.json"),
            "GREIA_DEVELOPER_ACTIVITY_ROOT": str(self.developer_root),
            "GREIA_PARENT_ACTIVITY_ROOT": str(self.package_root / "active"),
            "GREIA_PARENT_ACTIVITY_PACKAGE_ROOT": str(self.package_root),
            "GREIA_MEDIA_ROOT": str(self.media_root),
            "GREIA_SKIP_BOOT_HANDOFF": "1",
            "GREIA_SIMULATOR": "1",
            "GREIA_SIMULATOR_VIEWPORT": device.viewport,
            "GREIA_SIMULATOR_CAPABILITIES": capabilities,
            "GREIA_SIMULATOR_PYTHONPATH": str(self.repo_root / "src"),
        }

    def set_default_interface_size(
        self, value: str | InterfaceSize
    ) -> InterfaceSize:
        """Use the real profile/UI preference store for simulator user settings."""

        self.ensure()
        store = ProfileStore.load(
            self.repo_root / "runtime" / "profile-defaults.toml",
            self.profiles_root,
        )
        profiles = store.ensure_initialized()
        context = store.context(profiles[0].profile_id)
        preferences = UiPreferencesStore(context.customization_dir).set_interface_size(value)
        return preferences.interface_size

    def load_activity(self, source: Path):
        """Stage a developer folder, then validate it with the real ActivityRegistry."""

        self.ensure()
        source = source.expanduser().resolve(strict=True)
        if not source.is_dir():
            raise ValueError("Activity source must be a directory")
        runtime = RuntimeCatalogue.load(self.repo_root / "runtime" / "child-runtime.toml")

        staging_parent = Path(
            tempfile.mkdtemp(prefix="greia-simulator-load-", dir=str(self.state_root))
        )
        staged = staging_parent / "activity"
        try:
            shutil.copytree(
                source,
                staged,
                ignore=shutil.ignore_patterns(*_IGNORED_DEVELOPMENT_NAMES),
            )
            staging_source = ActivitySource(
                staging_parent,
                trust=PackageTrust.DEVELOPER_UNSIGNED,
                source_id="greia-simulator-staging",
            )
            built_in_source = ActivitySource(
                self.repo_root / "activities",
                trust=PackageTrust.BUILT_IN,
                source_id="greia-system",
            )
            staging_registry = ActivityRegistry((built_in_source, staging_source), runtime)
            registrations = staging_registry.discover_registrations()
            registration = next(
                (
                    item
                    for item in registrations
                    if item.manifest.root == staged.resolve()
                ),
                None,
            )
            if registration is None:
                raise ValueError("staged Activity did not validate as one Greia package")

            destination = self.developer_root / registration.manifest.activity_id
            prepared = self.developer_root / (
                f".{registration.manifest.activity_id}.simulator-staging"
            )
            if prepared.exists():
                shutil.rmtree(prepared)
            shutil.copytree(staged, prepared)
            if destination.exists():
                shutil.rmtree(destination)
            os.replace(prepared, destination)

            final_source = ActivitySource(
                self.developer_root,
                trust=PackageTrust.DEVELOPER_UNSIGNED,
                source_id="greia-developer-remote",
            )
            final_registry = ActivityRegistry((built_in_source, final_source), runtime)
            final_registrations = final_registry.discover_registrations()
            final = next(
                (
                    item
                    for item in final_registrations
                    if item.manifest.root == destination.resolve()
                ),
                None,
            )
            if final is None:
                raise ValueError("loaded Activity was not discoverable by Greia")
            return final
        finally:
            shutil.rmtree(staging_parent, ignore_errors=True)

    def install_activity_package(self, archive: Path) -> ActivityInstallReceipt:
        """Exercise the canonical Parent-approved package transaction locally."""

        self.ensure()
        service = ActivityPackageService(
            state_root=self.package_root,
            runtime_catalogue=self.repo_root / "runtime" / "child-runtime.toml",
            built_in_root=self.repo_root / "activities",
        )
        return service.install_archive(archive.expanduser())


__all__ = ["SimulatorWorkspace"]
