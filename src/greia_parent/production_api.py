from __future__ import annotations

from http.server import HTTPServer
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

    def _wifi_management_available(self) -> bool:
        # Joining a network no longer requires writing into iwd's root-owned
        # state directory: the passphrase is supplied over iwd's own agent API
        # and iwd persists the profile itself. This gate previously refused to
        # advertise network management unless that directory was writable,
        # which was honest for the old file-based design but would now hide a
        # capability that genuinely works unprivileged. The backend owns the
        # decision, so there is no second implementation of the requirement
        # here.
        return bool(self.wifi_backend.management_available())

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
    # Warm the Activity validation cache (ActivityRegistry._validated_tree_digest)
    # before accepting requests: a cold discovery of the built-in catalogue costs
    # ~20 s on the Atom reference floor and would block the first Parent client.
    try:
        app.registry.discover(fail_closed=False)
    except Exception:  # discovery problems are reported by the real requests
        pass
    ProductionParentApiHTTPServer((args.bind, args.port), app).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
