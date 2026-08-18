from __future__ import annotations

import hmac
import json
import socket
from http import cookies
from http.server import HTTPServer
from urllib.parse import parse_qs, urlparse

from greia_parent.credentials import ParentCredentialError, ParentDeviceCredentialStore
from greia_parent.protocol import (
    API_BASE,
    API_VERSION,
    SERVICE_PORT,
    SERVICE_TYPE,
    api_index_payload,
)
from greia_parent.server import (
    ParentHTTPServer,
    ParentRequestHandler,
    ParentStatusApplication,
    parse_args,
    render_status_page,
)
from greia_parent.static_client import ParentStaticClient, StaticClientAsset
from greia_parent.web_client import render_parent_web_app
from greia_platform.hardware import HardwareSettingsError
from greia_platform.main_credential import MainCredentialError, MainCredentialStore
from greia_platform.profiles import ProfileError


MAX_JSON_BODY_BYTES = 16 * 1024
DEVICE_COOKIE = "greia_parent_device"
_STATIC_PREFIXES = ("/src/", "/styles/", "/assets/")


class ParentApiApplication(ParentStatusApplication):
    """API-first parent application shared by HTML and future native clients."""

    def __init__(self, *args: object, **kwargs: object):
        super().__init__(*args, **kwargs)
        self.device_credentials = ParentDeviceCredentialStore(self.state_dir)
        self.main_credential = MainCredentialStore(self.state_dir / "main-credential.json")
        self.main_credential.ensure_initialized()

    def authorized(
        self,
        handler: ParentRequestHandler,
        query: dict[str, list[str]],
        *,
        allow_query_token: bool = False,
    ) -> bool:
        token = self._device_token_from_request(handler)
        if token and self.device_credentials.authenticate(token) is not None:
            return True
        # Transitional compatibility only. The legacy shared token remains a
        # bootstrap path while the Greia-screen challenge/confirmation UI is
        # implemented; new API clients should use per-device credentials.
        return super().authorized(handler, query, allow_query_token=allow_query_token)

    def bootstrap_device(self, pairing_token: str, display_name: str) -> dict[str, object]:
        if not isinstance(pairing_token, str) or not hmac.compare_digest(
            pairing_token, self.token
        ):
            raise PermissionError("pairing token rejected")
        issued = self.device_credentials.issue(display_name)
        return {
            "device": issued.device.public_dict(),
            "credential": issued.token,
        }

    def devices_payload(self) -> list[dict[str, str]]:
        return [device.public_dict() for device in self.device_credentials.list_devices()]

    def parent_password_payload(self) -> dict[str, object]:
        """Public parent-password facts; never returns stored material."""
        return {
            "configured": True,
            "username": "greia",
            "changeable": True,
        }

    def change_parent_password(self, current: str, new: str) -> dict[str, object]:
        self.main_credential.change(current, new)
        return {"changed": True}

    def activities_payload(self) -> list[dict[str, object]]:
        return [
            {
                "activity_id": manifest.activity_id,
                "version": manifest.version,
                "title_key": manifest.title_key,
                "icon_id": manifest.icon_id,
                "categories": list(manifest.categories),
                "difficulty": manifest.difficulty,
                "languages": list(manifest.languages),
                "input_profile": manifest.input_profile,
            }
            for manifest in self.registry.discover()
        ]

    def api_meta_payload(self) -> dict[str, object]:
        return {
            "product": "Greia",
            "service": "Greia Parents",
            "device_name": socket.gethostname(),
            "api_version": API_VERSION,
            "api_base": API_BASE,
            "service_type": SERVICE_TYPE,
            "port": SERVICE_PORT,
            "pairing_required": True,
            "transport_security": "provisional-http",
        }

    @staticmethod
    def _device_token_from_request(handler: ParentRequestHandler) -> str:
        authorization = handler.headers.get("Authorization", "")
        if authorization.startswith("Bearer "):
            return authorization.removeprefix("Bearer ").strip()

        raw_cookie = handler.headers.get("Cookie")
        if not raw_cookie:
            return ""
        try:
            jar = cookies.SimpleCookie()
            jar.load(raw_cookie)
        except cookies.CookieError:
            return ""
        morsel = jar.get(DEVICE_COOKIE)
        return morsel.value if morsel is not None else ""


class ParentApiRequestHandler(ParentRequestHandler):
    """Versioned JSON API layered over the existing parent domain application."""

    @property
    def app(self) -> ParentApiApplication:
        return self.server.app  # type: ignore[attr-defined,return-value]

    @property
    def static_client(self) -> ParentStaticClient:
        return self.server.static_client  # type: ignore[attr-defined,return-value]

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)

        # The client shell is intentionally public: an unpaired browser needs
        # the HTML/JS pairing UI before it can hold a Parent API credential.
        # All management data and mutations remain protected by /api/v1 auth.
        if parsed.path == "/" or parsed.path.startswith(_STATIC_PREFIXES):
            asset = self.static_client.read(parsed.path)
            if asset is not None:
                self._send_static_asset(asset)
                return
            if parsed.path == "/":
                # Transitional fallback until the separately maintained client
                # is vendored into release images. It contains no server secret.
                self._send_html(200, render_parent_web_app())
                return
            self._send_static_not_found()
            return
        if parsed.path == "/legacy":
            if not self._require_api_authorization(query):
                return
            self._send_html(200, render_status_page(self.app.health_payload()))
            return
        if parsed.path == f"{API_BASE}/meta":
            self._send_json(200, self.app.api_meta_payload())
            return
        if parsed.path == API_BASE:
            if not self._require_api_authorization(query):
                return
            self._send_json(200, api_index_payload())
            return
        if parsed.path == f"{API_BASE}/system":
            if not self._require_api_authorization(query):
                return
            self._send_json(200, self.app.health_payload())
            return
        if parsed.path == f"{API_BASE}/profiles":
            if not self._require_api_authorization(query):
                return
            self._send_json(200, self.app.profiles_payload())
            return
        if parsed.path == f"{API_BASE}/activities":
            if not self._require_api_authorization(query):
                return
            self._send_json(200, self.app.activities_payload())
            return
        if parsed.path == f"{API_BASE}/settings/hardware":
            if not self._require_api_authorization(query):
                return
            self._send_json(200, self.app.hardware_payload())
            return
        if parsed.path == f"{API_BASE}/progress":
            if not self._require_api_authorization(query):
                return
            requested_profile = query.get("profile_id", [""])[0] or None
            try:
                payload = self.app.progress_payload(requested_profile)
            except ProfileError:
                self._send_api_error(404, "profile_not_found", "Profile not found")
                return
            self._send_json(200, payload)
            return
        if parsed.path == f"{API_BASE}/devices":
            if not self._require_api_authorization(query):
                return
            self._send_json(200, self.app.devices_payload())
            return
        if parsed.path == f"{API_BASE}/parent-password":
            if not self._require_api_authorization(query):
                return
            self._send_json(200, self.app.parent_password_payload())
            return
        if parsed.path.startswith(f"{API_BASE}/"):
            self._send_api_error(404, "not_found", "Not found")
            return

        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == f"{API_BASE}/pairing/bootstrap":
            try:
                body = self._read_json_object()
                payload = self.app.bootstrap_device(
                    self._json_text(body, "pairing_token"),
                    self._json_text(body, "device_name"),
                )
            except PermissionError as exc:
                self._send_api_error(403, "pairing_rejected", str(exc))
                return
            except (ParentCredentialError, ValueError) as exc:
                self._send_api_error(400, "invalid_request", str(exc))
                return
            self._send_json(201, payload)
            return

        query = parse_qs(parsed.query)
        if parsed.path == f"{API_BASE}/profiles":
            if not self._require_api_authorization(query):
                return
            try:
                body = self._read_json_object()
                form = {
                    "display_name": [self._json_text(body, "display_name")],
                    "avatar_id": [self._json_text(body, "avatar_id")],
                    "secret": [self._json_text(body, "secret", default="")],
                }
                if bool(body.get("mask_secret", False)):
                    form["mask_secret"] = ["on"]
                payload = self.app.create_profile(form)
            except (ProfileError, ValueError) as exc:
                self._send_api_error(400, "invalid_profile", str(exc))
                return
            self._send_json(201, payload)
            return

        if parsed.path == f"{API_BASE}/settings/hardware/reset":
            if not self._require_api_authorization(query):
                return
            self._send_json(200, self.app.reset_hardware())
            return
        if parsed.path.startswith(f"{API_BASE}/"):
            self._send_api_error(404, "not_found", "Not found")
            return

        super().do_POST()

    def do_PUT(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        if parsed.path == f"{API_BASE}/parent-password":
            if not self._require_api_authorization(query):
                return
            try:
                body = self._read_json_object()
                payload = self.app.change_parent_password(
                    self._json_text(body, "current_password"),
                    self._json_text(body, "new_password"),
                )
            except (MainCredentialError, ValueError) as exc:
                self._send_api_error(400, "parent_password_rejected", str(exc))
                return
            self._send_json(200, payload)
            return
        if parsed.path != f"{API_BASE}/settings/hardware":
            self._send_api_error(404, "not_found", "Not found")
            return
        if not self._require_api_authorization(query):
            return
        try:
            body = self._read_json_object()
            current = self.app.hardware_store.read().as_json_dict()
            form = {
                "mouse_speed": [str(body.get("mouse_speed", current["mouse_speed"]))],
                "touchpad_speed": [
                    str(body.get("touchpad_speed", current["touchpad_speed"]))
                ],
                "resolution": [str(body.get("resolution", current["resolution"]))],
            }
            if bool(body.get("touchpad_tap", current["touchpad_tap"])):
                form["touchpad_tap"] = ["on"]
            if bool(body.get("natural_scrolling", current["natural_scrolling"])):
                form["natural_scrolling"] = ["on"]
            payload = self.app.update_hardware(form)
        except (HardwareSettingsError, KeyError, TypeError, ValueError) as exc:
            self._send_api_error(400, "invalid_hardware_settings", str(exc))
            return
        self._send_json(200, payload)

    def do_PATCH(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        profile_id = self._resource_id(parsed.path, f"{API_BASE}/profiles/")
        if profile_id is None:
            self._send_api_error(404, "not_found", "Not found")
            return
        if not self._require_api_authorization(query):
            return
        try:
            body = self._read_json_object()
            current = next(
                item
                for item in self.app.profiles_payload()
                if item.get("profile_id") == profile_id
            )
            form = {
                "profile_id": [profile_id],
                "display_name": [str(body.get("display_name", current["display_name"]))],
                "avatar_id": [str(body.get("avatar_id", current["avatar_id"]))],
                "secret_action": [str(body.get("secret_action", "keep"))],
                "secret": [self._json_text(body, "secret", default="")],
            }
            mask_secret = body.get("mask_secret", current.get("mask_secret", False))
            if bool(mask_secret):
                form["mask_secret"] = ["on"]
            payload = self.app.update_profile(form)
        except StopIteration:
            self._send_api_error(404, "profile_not_found", "Profile not found")
            return
        except (ProfileError, KeyError, TypeError, ValueError) as exc:
            self._send_api_error(400, "invalid_profile", str(exc))
            return
        self._send_json(200, payload)

    def do_DELETE(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        if not self._require_api_authorization(query):
            return

        profile_id = self._resource_id(parsed.path, f"{API_BASE}/profiles/")
        if profile_id is not None:
            try:
                payload = self.app.delete_profile(
                    {"profile_id": [profile_id], "confirm": ["delete"]}
                )
            except ProfileError as exc:
                self._send_api_error(400, "profile_delete_rejected", str(exc))
                return
            self._send_json(200, payload)
            return

        device_id = self._resource_id(parsed.path, f"{API_BASE}/devices/")
        if device_id is not None:
            try:
                removed = self.app.device_credentials.revoke(device_id)
            except ParentCredentialError as exc:
                self._send_api_error(404, "device_not_found", str(exc))
                return
            self._send_json(200, {"revoked": removed.public_dict()})
            return

        self._send_api_error(404, "not_found", "Not found")

    def _require_api_authorization(self, query: dict[str, list[str]]) -> bool:
        if self.app.authorized(self, query):
            return True
        self._send_api_error(401, "pairing_required", "Pair this parent client first")
        return False

    def _read_json_object(self) -> dict[str, object]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ValueError("invalid Content-Length") from exc
        if length < 0 or length > MAX_JSON_BODY_BYTES:
            raise ValueError("JSON request exceeds size limit")
        raw = self.rfile.read(length) if length else b"{}"
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("request body must be valid JSON") from exc
        if not isinstance(value, dict):
            raise ValueError("request body must be a JSON object")
        return value

    @staticmethod
    def _json_text(
        body: dict[str, object],
        key: str,
        *,
        default: str | None = None,
    ) -> str:
        value = body.get(key, default)
        if not isinstance(value, str):
            raise ValueError(f"{key} must be text")
        return value

    @staticmethod
    def _resource_id(path: str, prefix: str) -> str | None:
        if not path.startswith(prefix):
            return None
        value = path[len(prefix) :]
        if not value or "/" in value:
            return None
        return value

    def _send_static_asset(self, asset: StaticClientAsset) -> None:
        self.send_response(200)
        self.send_header("Content-Type", asset.content_type)
        self.send_header("Content-Length", str(len(asset.body)))
        self.send_header("Cache-Control", asset.cache_control)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; connect-src 'self'; object-src 'none'; "
            "base-uri 'none'; frame-ancestors 'none'; form-action 'self'",
        )
        self.end_headers()
        self.wfile.write(asset.body)

    def _send_static_not_found(self) -> None:
        body = b"Not found\n"
        self.send_response(404)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _send_api_error(self, status: int, code: str, message: str) -> None:
        self._send_json(status, {"error": {"code": code, "message": message}})


class ParentApiHTTPServer(ParentHTTPServer):
    """Use API-v1 handling while retaining the existing low-RAM server policy."""

    def __init__(
        self,
        address: tuple[str, int],
        app: ParentApiApplication,
        *,
        static_client: ParentStaticClient | None = None,
    ):
        self.app = app
        self.static_client = static_client or ParentStaticClient.from_environment()
        HTTPServer.__init__(self, address, ParentApiRequestHandler)


def main() -> int:
    args = parse_args()
    app = ParentApiApplication(
        args.root,
        args.state_dir,
        hardware_settings_dir=args.hardware_settings_dir,
        hardware_status_path=args.hardware_status_path,
        profiles_dir=args.profiles_dir,
        active_profile_status_path=args.active_profile_status_path,
    )
    ParentApiHTTPServer((args.bind, args.port), app).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
