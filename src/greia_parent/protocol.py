from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


API_VERSION = 1
API_BASE = "/api/v1"
SERVICE_TYPE = "_greia-parent._tcp"
SERVICE_PORT = 8766
# Separate local-only HTTP for the built-in Parent panel.
LOCAL_PARENT_PORT = 8767


@dataclass(frozen=True, slots=True)
class ParentApiResource:
    """One stable client-facing API resource advertised by Greia Parents."""

    name: str
    path: str
    methods: tuple[str, ...]

    def as_json_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "path": self.path,
            "methods": list(self.methods),
        }


RESOURCES = (
    ParentApiResource("system", f"{API_BASE}/system", ("GET",)),
    ParentApiResource("system_update", f"{API_BASE}/system/update", ("GET",)),
    ParentApiResource(
        "system_update_bundle",
        f"{API_BASE}/system/update/bundle",
        ("POST",),
    ),
    ParentApiResource("profiles", f"{API_BASE}/profiles", ("GET", "POST")),
    ParentApiResource(
        "profile_activity_policy",
        f"{API_BASE}/profiles/{{profile_id}}/activity-policy",
        ("GET", "PUT"),
    ),
    ParentApiResource(
        "profile_usage_limit",
        f"{API_BASE}/profiles/{{profile_id}}/usage-limit",
        ("GET", "PUT"),
    ),
    ParentApiResource(
        "profile_presentation",
        f"{API_BASE}/profiles/{{profile_id}}/presentation",
        ("GET", "PUT"),
    ),
    ParentApiResource("usage_limits", f"{API_BASE}/usage-limits", ("GET", "PUT")),
    ParentApiResource("activities", f"{API_BASE}/activities", ("GET",)),
    ParentApiResource(
        "activity_install",
        f"{API_BASE}/activities/install",
        ("POST",),
    ),
    ParentApiResource(
        "activity_package",
        f"{API_BASE}/activities/{{activity_id}}",
        ("DELETE",),
    ),
    ParentApiResource(
        "hardware_settings",
        f"{API_BASE}/settings/hardware",
        ("GET", "PUT"),
    ),
    ParentApiResource(
        "hardware_settings_reset",
        f"{API_BASE}/settings/hardware/reset",
        ("POST",),
    ),
    ParentApiResource(
        "system_controls",
        f"{API_BASE}/settings/system-controls",
        ("GET", "PUT"),
    ),
    ParentApiResource(
        "audio_settings",
        f"{API_BASE}/settings/audio",
        ("GET", "PUT"),
    ),
    ParentApiResource(
        "audio_settings_reset",
        f"{API_BASE}/settings/audio/reset",
        ("POST",),
    ),
    ParentApiResource(
        "language_settings",
        f"{API_BASE}/settings/language",
        ("GET", "PUT"),
    ),
    ParentApiResource("progress", f"{API_BASE}/progress", ("GET",)),
    ParentApiResource("paired_devices", f"{API_BASE}/devices", ("GET",)),
    ParentApiResource(
        "parent_password",
        f"{API_BASE}/parent-password",
        ("GET", "PUT"),
    ),
    ParentApiResource("wifi", f"{API_BASE}/network/wifi", ("GET", "POST")),
    ParentApiResource(
        "ssh_maintenance",
        f"{API_BASE}/maintenance/ssh",
        ("GET", "PUT"),
    ),
)

CAPABILITIES = {
    "profiles.manage": True,
    "profiles.presentation": False,
    "usage_limits.manage": True,
    "activities.read": True,
    "activities.policy": True,
    "progress.read": True,
    "settings.input": True,
    "settings.display": True,
    "settings.system_controls": False,
    "settings.language": True,
    "paired_devices.manage": True,
    "system.update.read": True,
    "system.update.upload": False,
    "system.update.activate": False,
    # Package code mutation remains fail-closed on normal/release images while
    # Parent transport is provisional HTTP. Package-aware compositions enable
    # install/remove together only in an explicit developer/owner-approved lane.
    "activities.install": False,
    "activities.remove": False,
    "backup.manage": False,
    "settings.audio": False,
    "network.manage": True,
    "maintenance.ssh": True,
    "parent.password": True,
}


def api_index_payload(
    capability_overrides: Mapping[str, bool] | None = None,
) -> dict[str, object]:
    """Return the versioned protocol index without leaking host implementation details.

    While Parent package mutation still sits behind the same explicit
    owner/developer enablement lane, install and removal are one capability
    family. A wrapper composition that overrides installation therefore inherits
    the same value for removal unless it explicitly supplies a removal override.
    This prevents top-level API compositions from accidentally exposing only
    half of the package-management surface.
    """

    capabilities = dict(CAPABILITIES)
    if capability_overrides:
        unknown = set(capability_overrides) - set(capabilities)
        if unknown:
            raise ValueError(
                "unknown Parent API capability override: " + ", ".join(sorted(unknown))
            )
        normalized = {name: bool(enabled) for name, enabled in capability_overrides.items()}
        if "activities.install" in normalized and "activities.remove" not in normalized:
            normalized["activities.remove"] = normalized["activities.install"]
        capabilities.update(normalized)
    return {
        "api_version": API_VERSION,
        "api_base": API_BASE,
        "service_type": SERVICE_TYPE,
        "resources": [resource.as_json_dict() for resource in RESOURCES],
        "capabilities": capabilities,
    }
