from __future__ import annotations

import os
from http.server import HTTPServer
from pathlib import Path
from urllib.parse import urlparse

from greia_parent.credentials import ParentCredentialError
from greia_parent.password_auth import ParentPasswordAttemptLimiter
from greia_parent.protocol import API_BASE
from greia_parent.server import parse_args
from greia_parent.static_client import ParentStaticClient
from greia_parent.update_api import (
    UpdateParentApiApplication,
    UpdateParentApiRequestHandler,
)
from greia_parent.web_client import render_parent_web_app
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
        self.password_attempts = ParentPasswordAttemptLimiter()

    def _load_or_create_token(self) -> str:
        """Retire the pre-password shared token during production startup.

        ``ParentStatusApplication`` still contains the old standalone-server
        compatibility hook. Dynamic dispatch reaches this override while the
        production API application is initialized, so installed Greia systems
        delete any migrated ``parent-pairing-token`` and never create another.
        API authentication is password bootstrap followed by revocable
        per-device credentials.
        """
        (self.state_dir / "parent-pairing-token").unlink(missing_ok=True)
        return ""

    def _wifi_management_available(self) -> bool:
        if not self.wifi_backend.available():
            return False
        if isinstance(self.wifi_backend, IwdWifiBackend):
            # R12 owns the future typed privileged broker. Until that exists,
            # the unprivileged HTTP process must not advertise a write path it
            # cannot actually complete against root-owned iwd state. Check the
            # effective mount namespace as well as Unix permission bits because
            # ProtectSystem=strict can make an otherwise writable path read-only.
            return _directory_is_effectively_writable(Path(self.wifi_backend.state_dir))
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
        candidates = tuple(network for network in self.wifi_backend.scan() if network.ssid == ssid)
        if not candidates:
            raise WifiError("Selected Wi-Fi network is no longer available; scan again")
        connection = self.wifi_backend.connect(candidates[0], passphrase)
        return {
            "connected": True,
            "ssid": connection.network.ssid,
        }


class ProductionParentApiRequestHandler(UpdateParentApiRequestHandler):
    """Installed HTTP surface with fail-closed static and auth policy."""

    @property
    def app(self) -> ProductionParentApiApplication:
        return self.server.app  # type: ignore[attr-defined,return-value]

    def do_GET(self) -> None:  # noqa: N802
        if urlparse(self.path).path == "/" and self.static_client.read("/") is None:
            self._send_html(503, render_parent_web_app())
            return
        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        if urlparse(self.path).path != f"{API_BASE}/pairing/bootstrap":
            super().do_POST()
            return

        client_address = self.client_address[0]
        if not self.app.password_attempts.allowed(client_address):
            self._send_api_error(
                429,
                "authentication_rate_limited",
                "Too many incorrect Greia password attempts; try again shortly",
            )
            return

        try:
            body = self._read_json_object()
            payload = self.app.bootstrap_device(
                self._json_text(body, "password"),
                self._json_text(body, "device_name"),
            )
        except PermissionError as exc:
            self.app.password_attempts.record_failure(client_address)
            self._send_api_error(403, "authentication_rejected", str(exc))
            return
        except (ParentCredentialError, ValueError) as exc:
            self._send_api_error(400, "invalid_request", str(exc))
            return

        self.app.password_attempts.clear(client_address)
        self._send_json(201, payload)


class ProductionParentApiHTTPServer(HTTPServer):
    """Bind the production request policy without changing reusable API servers."""

    def __init__(
        self,
        address: tuple[str, int],
        app: ProductionParentApiApplication,
        *,
        static_client: ParentStaticClient | None = None,
    ) -> None:
        self.app = app
        self.static_client = static_client or ParentStaticClient.from_environment()
        HTTPServer.__init__(self, address, ProductionParentApiRequestHandler)


def _directory_is_effectively_writable(path: Path) -> bool:
    """Return whether *path* is writable in the service's effective namespace."""

    try:
        if not path.is_dir():
            return False
        flags = os.statvfs(path).f_flag
        if hasattr(os, "ST_RDONLY") and flags & os.ST_RDONLY:
            return False
        return os.access(path, os.W_OK | os.X_OK)
    except OSError:
        return False


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
    ProductionParentApiHTTPServer((args.bind, args.port), app).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
