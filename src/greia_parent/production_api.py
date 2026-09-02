from __future__ import annotations

import os
from pathlib import Path

from greia_parent.server import parse_args
from greia_parent.update_api import (
    UpdateParentApiApplication,
    UpdateParentApiHTTPServer,
)
from greia_platform.wifi import IwdWifiBackend, WifiBackend, WifiError


class ProductionParentApiApplication(UpdateParentApiApplication):
    """Installed Parent composition with real, fail-closed hardware policy.

    Lower layers retain injectable/demo backends for tests and development.
    The appliance entry point is explicit: real iwd is the default and an
    unavailable/unwritable backend is advertised as unavailable rather than
    replaced with sample networks or simulated connection success.
    """

    def __init__(
        self,
        *args: object,
        wifi_backend: WifiBackend | None = None,
        **kwargs: object,
    ) -> None:
        kwargs["wifi_backend"] = (
            wifi_backend if wifi_backend is not None else IwdWifiBackend()
        )
        super().__init__(*args, **kwargs)

    def _wifi_management_available(self) -> bool:
        if not self.wifi_backend.available():
            return False
        if isinstance(self.wifi_backend, IwdWifiBackend):
            state_dir = Path(self.wifi_backend.state_dir)
            # R12 owns the future typed privileged broker. Until that exists,
            # the unprivileged HTTP process must not advertise a write path it
            # cannot actually complete against root-owned iwd state.
            return state_dir.is_dir() and os.access(state_dir, os.W_OK)
        return True

    def index_payload(self) -> dict[str, object]:
        payload = super().index_payload()
        capabilities = dict(payload["capabilities"])
        capabilities["activities.remove"] = self.activity_remove_enabled
        capabilities["network.manage"] = self._wifi_management_available()
        payload["capabilities"] = capabilities
        return payload

    def wifi_payload(self) -> dict[str, object]:
        if not self._wifi_management_available():
            return {"available": False, "networks": []}
        return super().wifi_payload()

    def connect_wifi(self, ssid: str, passphrase: str = "") -> dict[str, object]:
        if not self._wifi_management_available():
            raise WifiError("Wi-Fi management is unavailable on this Greia")
        return super().connect_wifi(ssid, passphrase)


def main() -> int:
    args = parse_args()
    app = ProductionParentApiApplication(
        args.root,
        args.state_dir,
        hardware_settings_dir=args.hardware_settings_dir,
        hardware_status_path=args.hardware_status_path,
        profiles_dir=args.profiles_dir,
        active_profile_status_path=args.active_profile_status_path,
    )
    UpdateParentApiHTTPServer((args.bind, args.port), app).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
