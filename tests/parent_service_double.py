"""In-process stand-in for the Parent service as the launcher panel sees it.

Production runs the panel as ``greiakid``, which cannot write the
``greiapel``-owned hardware settings, so every settings change goes through
``ParentCredentialClient`` to the Parent service. Panel tests therefore need a
client-shaped collaborator. This double has the same method names and result
shapes as the real client and the real service handlers
(``ParentStatusApplication.update_hardware`` / ``reset_hardware`` answer with
the flat ``HardwareSettings`` object) and applies changes to a real
``HardwareSettingsStore`` so tests can still assert persisted state.
"""

from __future__ import annotations

from typing import Any

from greia_launcher.parent_credential_client import ParentSession
from greia_platform.hardware import HardwareSettingsStore
from greia_platform.main_credential import MainCredentialStore


class ParentServiceDouble:
    """Client-shaped verifier backed by real credential and settings stores."""

    def __init__(
        self,
        credential_store: MainCredentialStore,
        hardware_store: HardwareSettingsStore,
    ) -> None:
        self._credentials = credential_store
        self._hardware = hardware_store
        self.session = ParentSession(token="test-token", device_id="test-device")

    # Authentication ---------------------------------------------------
    def verify(self, password: str) -> bool:
        return bool(self._credentials.verify(password))

    def authenticate(self, password: str) -> ParentSession:
        # A wrong password must stay a plain rejection for the panel, which
        # treats any exception as "check failed" rather than "incorrect".
        if not self.verify(password):
            raise PermissionError("rejected")
        return self.session

    # Child accounts (the panel only lists them when the tab is opened) -
    def list_child_accounts(self, session: ParentSession) -> list[Any]:
        return []

    # Hardware settings ----------------------------------------------------
    def get_hardware_settings(self, session: ParentSession) -> dict[str, Any]:
        return {"desired": self._hardware.read().as_json_dict()}

    def update_hardware_settings(
        self, session: ParentSession, changes: dict[str, Any]
    ) -> dict[str, Any]:
        return self._hardware.update(**changes).as_json_dict()

    def reset_hardware_settings(self, session: ParentSession) -> dict[str, Any]:
        return self._hardware.reset().as_json_dict()

    def get_audio_settings(self, session: ParentSession) -> dict[str, Any]:
        return {
            "microphone_processing_enabled": True,
            "advanced_noise_reduction": False,
            "advanced_available": False,
        }
