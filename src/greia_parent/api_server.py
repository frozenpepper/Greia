from __future__ import annotations

import hmac
import json
import socket
from http import cookies
from http.server import HTTPServer
from pathlib import Path
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
from greia_platform.activity_discovery import (
    ActivityDiscoveryError,
    ActivityDiscoveryPolicyStore,
    ActivityDiscoveryService,
    ActivityVisibilityMode,
    ActivityVisibilityOverride,
    ChallengePreference,
)
from greia_platform.hardware import HardwareSettingsError
from greia_platform.main_credential import MainCredentialError, MainCredentialStore
from greia_platform.profiles import ProfileError
from greia_platform.ssh_maintenance import SshMaintenanceService, SshStatus
from greia_platform.wifi import (
    DemoWifiBackend,
    IwdWifiBackend,
    WifiBackend,
    WifiError,
    WifiNetwork,
    WifiSecurity,
)


MAX_JSON_BODY_BYTES = 16 * 1024
DEVICE_COOKIE = "greia_parent_device"
_STATIC_PREFIXES = ("/src/", "/styles/", "/assets/")


class ParentApiApplication(ParentStatusApplication):
    """API-first parent application shared by HTML and future native clients."""

    def __init__(self, *args: object, **kwargs: object):
        wifi_backend = kwargs.pop("wifi_backend", None)
        ssh_service = kwargs.pop("ssh_service", None)
        super().__init__(*args, **kwargs)
        self.device_credentials = ParentDeviceCredentialStore(self.state_dir)
        self.main_credential = MainCredentialStore(self.state_dir / "main-credential.json")
        self.main_credential.ensure_initialized()
        self.wifi_backend: WifiBackend = wifi_backend or (
            IwdWifiBackend() if Path("/var/lib/iwd").exists() else DemoWifiBackend()
        )
        self.ssh_service: SshMaintenanceService = ssh_service or SshMaintenanceService()
        self.activity_discovery = ActivityDiscoveryService()

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

    def wifi_payload(self) -> dict[str, object]:
        return {
            "available": self.wifi_backend.available(),
            "networks": [
                {
                    "ssid": net.ssid,
                    "security": net.security.value,
                    "signal_dbm": net.signal_dbm,
                }
                for net in self.wifi_backend.scan()
            ],
        }

    def connect_wifi(self, ssid: str, passphrase: str = "") -> dict[str, object]:
        candidates = [net for net in self.wifi_backend.scan() if net.ssid == ssid]
        if candidates:
            network = candidates[0]
        else:
            security = WifiSecurity.PERSONAL if passphrase else WifiSecurity.OPEN
            network = WifiNetwork(ssid, security, -50.0, "/net/connman/iwd/manual")
        connection = self.wifi_backend.connect(network, passphrase)
        return {
            "connected": True,
            "ssid": connection.network.ssid,
        }

    def ssh_payload(self) -> dict[str, object]:
        return self.ssh_service.get_status().public_dict()

    def update_ssh(self, enabled: bool, public_key: str | None = None) -> dict[str, object]:
        if enabled:
            status = self.ssh_service.enable(public_key)
        else:
            status = self.ssh_service.disable()
        return status.public_dict()

    def activities_payload(self) -> list[dict[str, object]]:
        return [
            {
                "activity_id": manifest.activity_id,
                "version": manifest.version,
                "title_key": manifest.title_key,
                "icon_id": manifest.icon_id,
                "categories": list(manifest.categories),
                "presentation_categories": list(manifest.launcher_categories),
                "discovery_tags": list(manifest.discovery_tags),
                "difficulty": manifest.difficulty,
                "difficulty_min": manifest.difficulty_min,
                "difficulty_max": manifest.difficulty_max,
                "adaptive_difficulty": manifest.adaptive_difficulty,
                "recommended_age_min": manifest.recommended_age_min,
                "recommended_age_max": manifest.recommended_age_max,
                "languages": list(manifest.languages),
                "input_profile": manifest.input_profile,
            }
            for manifest in self.registry.discover()
        ]

    def activity_policy_payload(self, profile_id: str) -> dict[str, object]:
        context = self.profile_store.context(profile_id)
        store = ActivityDiscoveryPolicyStore(context.activity_discovery_policy_path)
        policy = store.read()
        activities = self.registry.discover()
        effective = self.activity_discovery.effective_activities(
            activities,
            approximate_age=context.profile.approximate_age,
            challenge_preference=context.profile.challenge_preference,
            policy=policy,
        )
        return {
            "profile_id": profile_id,
            "visibility_mode": policy.visibility_mode.value,
            "overrides": {
                activity_id: override.value
                for activity_id, override in policy.overrides
            },
            "effective_activity_ids": [item.activity_id for item in effective],
        }

    def update_activity_policy(
        self,
        profile_id: str,
        *,
        visibility_mode: object,
        overrides: object,
    ) -> dict[str, object]:
        context = self.profile_store.context(profile_id)
        store = ActivityDiscoveryPolicyStore(context.activity_discovery_policy_path)
        policy = store.read()
        try:
            mode = ActivityVisibilityMode(visibility_mode)
        except (TypeError, ValueError) as exc:
            raise ActivityDiscoveryError("invalid Activity visibility mode") from exc
        if not isinstance(overrides, dict):
            raise ActivityDiscoveryError("Activity visibility overrides must be an object")
        known_ids = {manifest.activity_id for manifest in self.registry.discover()}
        updated = policy.with_visibility_mode(mode)
        for activity_id, raw_value in overrides.items():
            if not isinstance(activity_id, str) or activity_id not in known_ids:
                raise ActivityDiscoveryError(
                    f"unknown Activity visibility override: {activity_id!r}"
                )
            if raw_value is None or raw_value == "default":
                value = None
            else:
                try:
                    value = ActivityVisibilityOverride(raw_value)
                except (TypeError, ValueError) as exc:
                    raise ActivityDiscoveryError(
                        f"invalid visibility override for {activity_id}"
                    ) from exc
            updated = updated.with_override(activity_id, value)
        store.write(updated)
        return self.activity_policy_payload(profile_id)

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
        policy_profile_id = self._profile_policy_id(parsed.path)
        if policy_profile_id is not None:
            if not self._require_api_authorization(query):
                return
            try:
                payload = self.app.activity_policy_payload(policy_profile_id)
            except ProfileError:
                self._send_api_error(404, "profile_not_found", "Profile not found")
                return
            except ActivityDiscoveryError as exc:
                self._send_api_error(400, "invalid_activity_policy", str(exc))
                return
            self._send_json(200, payload)
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
        if parsed.path == f"{API_BASE}/network/wifi":
            if not self._require_api_authorization(query):
                return
            self._send_json(200, self.app.wifi_payload())
            return
        if parsed.path == f"{API_BASE}/maintenance/ssh":
            if not self._require_api_authorization(query):
                return
            self._send_json(200, self.app.ssh_payload())
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
        if parsed.path == f"{API_BASE}/network/wifi/connect":
            if not self._require_api_authorization(query):
                return
            try:
                body = self._read_json_object()
                payload = self.app.connect_wifi(
                    self._json_text(body, "ssid"),
                    self._json_text(body, "passphrase", default=""),
                )
            except (WifiError, ValueError) as exc:
                self._send_api_error(400, "wifi_connection_failed", str(exc))
                return
            self._send_json(200, payload)
            return

        if parsed.path == f"{API_BASE}/profiles":
            if not self._require_api_authorization(query):
                return
            try:
                body = self._read_json_object()
                approximate_age = self._json_optional_int(body, "approximate_age")
                challenge = ChallengePreference(
                    body.get("challenge_preference", ChallengePreference.AUTOMATIC.value)
                )
                profile = self.app.profile_store.create(
                    self._json_text(body, "display_name"),
                    self._json_text(body, "avatar_id"),
                    secret=self._json_text(body, "secret", default=""),
                    mask_secret=bool(body.get("mask_secret", False)),
                    approximate_age=approximate_age,
                    challenge_preference=challenge,
                    uppercase_text=bool(body.get("uppercase_text", True)),
                )
                payload = profile.public_dict()
            except (ProfileError, TypeError, ValueError) as exc:
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
        policy_profile_id = self._profile_policy_id(parsed.path)
        if policy_profile_id is not None:
            if not self._require_api_authorization(query):
                return
            try:
                body = self._read_json_object()
                current = self.app.activity_policy_payload(policy_profile_id)
                payload = self.app.update_activity_policy(
                    policy_profile_id,
                    visibility_mode=body.get(
                        "visibility_mode", current["visibility_mode"]
                    ),
                    overrides=body.get("overrides", current["overrides"]),
                )
            except ProfileError:
                self._send_api_error(404, "profile_not_found", "Profile not found")
                return
            except (ActivityDiscoveryError, ValueError) as exc:
                self._send_api_error(400, "invalid_activity_policy", str(exc))
                return
            self._send_json(200, payload)
            return
        if parsed.path == f"{API_BASE}/maintenance/ssh":
            if not self._require_api_authorization(query):
                return
            try:
                body = self._read_json_object()
                payload = self.app.update_ssh(
                    bool(body.get("enabled", False)),
                    self._json_text(body, "public_key", default=None),
                )
            except Exception as exc:
                self._send_api_error(400, "ssh_update_failed", str(exc))
                return
            self._send_json(200, payload)
            return
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
                "mic_gain": [str(body.get("mic_gain", current["mic_gain"]))],
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
                profile
                for profile in self.app.profile_store.list_profiles()
                if profile.profile_id == profile_id
            )
            approximate_age_present = "approximate_age" in body
            approximate_age = (
                self._json_optional_int(body, "approximate_age")
                if approximate_age_present
                else None
            )
            raw_challenge = body.get(
                "challenge_preference", current.challenge_preference.value
            )
            challenge = ChallengePreference(raw_challenge)
            profile = self.app.profile_store.update(
                profile_id,
                display_name=str(body.get("display_name", current.display_name)),
                avatar_id=str(body.get("avatar_id", current.avatar_id)),
                secret_action=str(body.get("secret_action", "keep")),
                secret=self._json_text(body, "secret", default=""),
                mask_secret=bool(body.get("mask_secret", current.mask_secret)),
                approximate_age=approximate_age,
                clear_approximate_age=(
                    approximate_age_present and body.get("approximate_age") is None
                ),
                challenge_preference=challenge,
                uppercase_text=bool(body.get("uppercase_text", current.uppercase_text)),
            )
            payload = profile.public_dict()
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
    def _json_optional_int(body: dict[str, object], key: str) -> int | None:
        value = body.get(key)
        if value is None:
            return None
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError(f"{key} must be an integer or null")
        return value

    @staticmethod
    def _resource_id(path: str, prefix: str) -> str | None:
        if not path.startswith(prefix):
            return None
        value = path[len(prefix) :]
        if not value or "/" in value:
            return None
        return value

    @staticmethod
    def _profile_policy_id(path: str) -> str | None:
        prefix = f"{API_BASE}/profiles/"
        suffix = "/activity-policy"
        if not path.startswith(prefix) or not path.endswith(suffix):
            return None
        value = path[len(prefix) : -len(suffix)]
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
