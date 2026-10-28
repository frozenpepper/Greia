#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

from greia_launcher.runtime_adapter import (
    PythonRuntimeAdapter,
    PythonRuntimePolicy,
    RuntimeManager,
    WebRuntimeAdapter,
)
from greia_platform.activities import ActivityRegistry, RuntimeCatalogue
from greia_platform.activity_backend_policy import (
    assert_python_activity_backend_independent,
)
from greia_platform.assets import AssetCatalogue
from greia_platform.customization import ThemePalette
from greia_platform.device_capabilities import DeviceCapabilityService
from greia_platform.hardware import HardwareDefaults
from greia_platform.history import HistoryPolicy, ProgressionPolicy
from greia_platform.profiles import ProfilePolicy
from greia_platform.storage import StoragePolicy
from greia_platform.trust import ActivitySource, PackageTrust
from build_profile import BuildProfile, BuildProfileError


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    runtime_path = root / "runtime" / "child-runtime.toml"
    runtime = RuntimeCatalogue.load(runtime_path)
    runtime_manager = RuntimeManager(
        [
            PythonRuntimeAdapter(policy=PythonRuntimePolicy.load(runtime_path)),
            WebRuntimeAdapter(),
        ],
        # Project validation proves static/package compatibility, not physical
        # hardware. Installed launch composition injects the real HAL-backed
        # DeviceCapabilityService instead of this deterministic source-test view.
        DeviceCapabilityService.static(
            runtime.allowed_capabilities,
            source_id="project-validation-static",
        ),
    )
    activities = ActivityRegistry(
        [ActivitySource(root / "activities", PackageTrust.BUILT_IN, "greia-system")],
        runtime,
    ).discover()
    for activity in activities:
        runtime_manager.validate_package(activity)
        if activity.runtime_type == "python":
            assert_python_activity_backend_independent(activity.root)

    assets = AssetCatalogue.load(root / "assets" / "catalog" / "core_icons_v1.toml")
    palette = ThemePalette.load(root / "runtime" / "theme-defaults.toml")
    hardware = HardwareDefaults.load(root / "runtime" / "hardware-settings.toml")
    profiles = ProfilePolicy.load(root / "runtime" / "profile-defaults.toml")
    storage = StoragePolicy.load(root / "runtime" / "storage-policy.toml")
    history = HistoryPolicy.load(root / "runtime" / "history-policy.toml")
    progression = ProgressionPolicy.load(
        root / "runtime" / "progression-policy.toml", activities
    )
    from greia_platform.activity_assets import package_icon_path

    for activity in activities:
        if package_icon_path(activity) is None:
            assets.get(activity.icon_id)

    package_root = root / "build" / "package-sets"
    image_profiles = []
    required_runtime_families = {activity.runtime_type for activity in activities}
    for path in sorted((root / "build" / "profiles").glob("*.toml")):
        image_profile = BuildProfile.load(path)
        if image_profile.base.architecture == "arm64":
            # The schema accepts ARM64, but the Phase 0 builder deliberately
            # has no board boot adapter yet. Keep the declaration valid and
            # require the refusal instead of pretending ARM images build.
            for scope in ("target", "installer"):
                try:
                    image_profile.check_phase0_builder_support(scope)
                except BuildProfileError as exc:
                    if "does not implement architecture 'arm64'" not in str(exc):
                        raise
                else:
                    raise ValueError(
                        f"ARM64 profile {image_profile.identity.profile_id} was "
                        "unexpectedly accepted by the Phase 0 builder"
                    )
        else:
            image_profile.check_phase0_builder_support("target")
            image_profile.check_phase0_builder_support("installer")
        image_profile.resolve_packages(package_root, "target")
        image_profile.resolve_packages(package_root, "installer")
        missing = required_runtime_families - set(image_profile.runtimes.enabled)
        if missing:
            raise ValueError(
                f"image profile {image_profile.identity.profile_id} omits runtimes required by bundled Activities: "
                + ", ".join(sorted(missing))
            )
        image_profiles.append(image_profile)
    print(
        f"PASS runtime_api={runtime.api_version} activities={len(activities)} "
        f"icons={len(assets.all_icons())} backgrounds={len(palette.backgrounds)} "
        f"accents={len(palette.accents)} texts={len(palette.texts)} "
        f"tap_default={hardware.touchpad_tap} resolution_default={hardware.resolution} "
        f"profile_limit={profiles.max_profiles} avatars={len(profiles.avatars)} "
        f"storage_quota={storage.namespace_quota_bytes} "
        f"history_sessions={history.max_sessions_per_profile} "
        f"progression_rules={len(progression.rules)} "
        f"image_profiles={len(image_profiles)} runtimes={','.join(sorted(required_runtime_families))}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
