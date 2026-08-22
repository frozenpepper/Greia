from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


API_VERSION = 1
API_BASE = "/api/v1"
SERVICE_TYPE = "_greia-parent._tcp"
SERVICE_PORT = 8766


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
    ParentApiResource("activities", f"{API_BASE}/activities", ("GET",)),
    ParentApiResource(
        "activity_install",
        f"{API_BASE}/activities/install",
        ("POST",),
    ),
    ParentApiResource(
        "hardware_settings",
        f"{API_BASE}/settings/hardware",
        ("GET", "PUT"),
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
    "activities.read": True,
    "activities.policy": True,
    "progress.read": True,
    "settings.input": True,
    "settings.display": True,
    "settings.language": True,
    "paired_devices.manage": True,
    # Update status is a semantic read surface even before a machine has a
    # production A/B activation backend. It may correctly report unavailable.
    "system.update.read": True,
    # Bundle upload is code/system-content delivery over the Parent transport.
    # Ordinary/release images keep it false while transport remains provisional
    # HTTP. Developer/owner-enabled images may accept a bounded bundle into the
    # unprivileged inbox; upload never grants slot-write/reboot authority.
    "system.update.upload": False,
    # Activation is intentionally false until the privileged R13B update service
    # and a proven rollback-capable backend are composed for the machine profile.
    "system.update.activate": False,
    # The package endpoint is protocol-defined, but ordinary/release images keep
    # it unavailable while Parent transport is still provisional HTTP. The
    # package-aware server may advertise it only in an explicit developer or
    # owner-enabled environment; clients must always honor this capability.
    "activities.install": False,
    "backup.manage": False,
    "settings.audio": False,
    "network.manage": True,
    "maintenance.ssh": True,
    # The main Parent password is a typed Greia-owned credential. It is
    # manageable from the HTML client whenever the Parent API is reachable; it
    # must never be confused with per-device bearer credentials.
    "parent.password": True,
}


def api_index_payload(
    capability_overrides: Mapping[str, bool] | None = None,
) -> dict[str, object]:
    """Return the versioned protocol index without leaking host implementation details."""

    capabilities = dict(CAPABILITIES)
    if capability_overrides:
        unknown = set(capability_overrides) - set(capabilities)
        if unknown:
            raise ValueError(
                "unknown Parent API capability override: " + ", ".join(sorted(unknown))
            )
        capabilities.update(
            {name: bool(enabled) for name, enabled in capability_overrides.items()}
        )
    return {
        "api_version": API_VERSION,
        "api_base": API_BASE,
        "service_type": SERVICE_TYPE,
        "resources": [resource.as_json_dict() for resource in RESOURCES],
        "capabilities": capabilities,
    }
