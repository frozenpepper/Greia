from __future__ import annotations

from dataclasses import dataclass


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
    ParentApiResource("profiles", f"{API_BASE}/profiles", ("GET", "POST")),
    ParentApiResource("activities", f"{API_BASE}/activities", ("GET",)),
    ParentApiResource(
        "hardware_settings",
        f"{API_BASE}/settings/hardware",
        ("GET", "PUT"),
    ),
    ParentApiResource("progress", f"{API_BASE}/progress", ("GET",)),
    ParentApiResource("paired_devices", f"{API_BASE}/devices", ("GET",)),
)

CAPABILITIES = {
    "profiles.manage": True,
    "activities.read": True,
    "progress.read": True,
    "settings.input": True,
    "settings.display": True,
    "paired_devices.manage": True,
    # These names intentionally exist now so the HTML client and a future phone
    # client can consume the same protocol while the typed platform services are
    # implemented. False means unavailable; it is never permission to emulate an
    # operation with shell commands.
    "activities.install": False,
    "backup.manage": False,
    "settings.audio": False,
    "network.manage": False,
    "maintenance.ssh": False,
}


def api_index_payload() -> dict[str, object]:
    """Return the versioned protocol index without leaking host implementation details."""

    return {
        "api_version": API_VERSION,
        "api_base": API_BASE,
        "service_type": SERVICE_TYPE,
        "resources": [resource.as_json_dict() for resource in RESOURCES],
        "capabilities": dict(CAPABILITIES),
    }
