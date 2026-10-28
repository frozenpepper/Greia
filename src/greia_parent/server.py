from __future__ import annotations

import argparse
import hmac
import html
import json
import os
import secrets
from http import cookies
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from greia_platform.activities import ActivityRegistry, ActivityValidationError, RuntimeCatalogue
from greia_platform.assets import AssetCatalogue
from greia_platform.customization import ThemeStore
from greia_platform.hardware import (
    HardwareSettingsError,
    HardwareSettingsStore,
    read_apply_status,
)
from greia_platform.health import collect_health, installed_os_identity
from greia_platform.profiles import ActiveProfileSession, ProfileError, ProfileStore
from greia_platform.trust import ActivitySource, PackageTrust
from greia_parent.progress import ParentProgressReader


PAIRING_TOKEN_MINIMUM_LENGTH = 32
PAIRING_TOKEN_MAXIMUM_LENGTH = 128
PAIRING_TOKEN_CHARACTERS = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")


def _is_valid_pairing_token(token: str) -> bool:
    return (
        PAIRING_TOKEN_MINIMUM_LENGTH <= len(token) <= PAIRING_TOKEN_MAXIMUM_LENGTH
        and all(character in PAIRING_TOKEN_CHARACTERS for character in token)
    )


class ParentStatusApplication:
    def __init__(
        self,
        root: Path,
        state_dir: Path,
        customization_dir: Path | None = None,
        hardware_settings_dir: Path | None = None,
        hardware_status_path: Path | None = None,
        profiles_dir: Path | None = None,
        active_profile_status_path: Path | None = None,
    ):
        self.root = root.resolve()
        self.state_dir = state_dir.resolve()
        compatibility_profiles_dir = (
            customization_dir.parent / "greia-profiles"
            if customization_dir is not None
            else Path("/var/lib/greia-profiles")
        )
        self.profiles_dir = (
            profiles_dir
            or Path(
                os.environ.get(
                    "GREIA_PROFILES_DIR", str(compatibility_profiles_dir)
                )
            )
        ).resolve()
        self.hardware_settings_dir = (
            hardware_settings_dir
            or Path(
                os.environ.get(
                    "GREIA_SYSTEM_SETTINGS_DIR", "/var/lib/greia-system-settings"
                )
            )
        ).resolve()
        self.hardware_status_path = (
            hardware_status_path
            or Path(os.environ.get("GREIA_HARDWARE_STATUS", "/run/greia-hardware/status.json"))
        ).resolve()
        self.active_profile_status_path = (
            active_profile_status_path
            or Path(
                os.environ.get(
                    "GREIA_ACTIVE_PROFILE_STATUS", "/run/greia-os/active-profile.json"
                )
            )
        ).resolve()
        self.runtime = RuntimeCatalogue.load(self.root / "runtime" / "child-runtime.toml")
        self.registry = ActivityRegistry(
            [
                ActivitySource(
                    self.root / "activities",
                    trust=PackageTrust.BUILT_IN,
                    source_id="greia-system",
                )
            ],
            self.runtime,
        )
        self.assets = AssetCatalogue.load(
            self.root / "assets" / "catalog" / "core_icons_v1.toml"
        )
        self.profile_store = ProfileStore.load(
            self.root / "runtime" / "profile-defaults.toml", self.profiles_dir
        )
        profiles = self.profile_store.ensure_initialized()
        self.progress_reader = ParentProgressReader.load(self.root, self.profile_store)
        self.theme_store = self._theme_store(profiles[0].profile_id)  # compatibility/test helper
        self.active_session = ActiveProfileSession(self.active_profile_status_path)
        self.hardware_store = HardwareSettingsStore.load(
            self.root / "runtime" / "hardware-settings.toml",
            self.hardware_settings_dir,
        )
        self.token = self._load_or_create_token()

    def _load_or_create_token(self) -> str:
        """Return a strong token, rotating empty/corrupt legacy state atomically.

        An empty token must never be accepted: an absent cookie/header is also an
        empty string, so comparing two empty values would authorize every request.
        """

        self.state_dir.mkdir(parents=True, exist_ok=True)
        token_path = self.state_dir / "parent-pairing-token"
        try:
            existing = token_path.read_text(encoding="ascii").strip()
        except (FileNotFoundError, OSError, UnicodeDecodeError):
            existing = ""
        if _is_valid_pairing_token(existing):
            try:
                os.chmod(token_path, 0o600)
            except OSError:
                pass
            return existing

        token = secrets.token_urlsafe(32)
        if not _is_valid_pairing_token(token):  # defensive against API changes
            raise RuntimeError("generated parent pairing token is invalid")
        temporary = token_path.with_name(f".{token_path.name}.{os.getpid()}.tmp")
        try:
            temporary.write_text(token + "\n", encoding="ascii")
            os.chmod(temporary, 0o600)
            temporary.replace(token_path)
            os.chmod(token_path, 0o600)
        finally:
            temporary.unlink(missing_ok=True)
        return token

    def authorized(
        self,
        handler: BaseHTTPRequestHandler,
        query: dict[str, list[str]],
        *,
        allow_query_token: bool = False,
    ) -> bool:
        candidate = ""
        raw_cookie = handler.headers.get("Cookie")
        if raw_cookie:
            try:
                jar = cookies.SimpleCookie()
                jar.load(raw_cookie)
                if "greia_parent" in jar:
                    candidate = jar["greia_parent"].value
            except cookies.CookieError:
                candidate = ""
        if not candidate:
            candidate = handler.headers.get("X-Pip-Token", "")
        if not candidate and allow_query_token:
            candidate = query.get("token", [""])[0]
        return bool(
            _is_valid_pairing_token(candidate)
            and _is_valid_pairing_token(self.token)
            and hmac.compare_digest(candidate, self.token)
        )

    def _theme_store(self, profile_id: str) -> ThemeStore:
        context = self.profile_store.context(profile_id)
        return ThemeStore.load(
            self.root / "runtime" / "theme-defaults.toml",
            context.customization_dir,
        )

    def profiles_payload(self) -> list[dict[str, object]]:
        payload: list[dict[str, object]] = []
        for profile in self.profile_store.list_profiles():
            item = profile.public_dict()
            item["customization"] = self._theme_store(profile.profile_id).resolve().as_json_dict()
            payload.append(item)
        return payload

    def progress_payload(self, profile_id: str | None = None) -> dict[str, object]:
        if profile_id is None:
            active = self.active_session.read()
            profile_id = (
                str(active.get("profile_id"))
                if isinstance(active, dict) and active.get("profile_id")
                else None
            )
        if profile_id is None:
            return ParentProgressReader.unavailable_payload()
        # Validate caller-selected identity before the fail-soft history reader.
        self.profile_store.context(profile_id)
        return self.progress_reader.payload(profile_id)

    def hardware_payload(self) -> dict[str, object]:
        """Parent hardware resource: desired v2 settings + applied facts.

        Shape (keys stable; additive only)::

            {
              "desired": {...HardwareSettings v2...},
              "settings": {...fallback snapshot...},
              "applied": bool,
              "backend": str | None,          # watcher backend id, None when unknown
              "display_output": str | null,
              "display_modes": [...<=32...],
              "display_metrics": null | {pixel_width, pixel_height,
                physical_size_known, orientation, source,
                physical_width_mm?, physical_height_mm?},
              "pointer_devices": [...<=8, flat supports_*...],
              "pointer_capabilities": [...same as pointer_devices...],
              "message": str
            }

        ``display_metrics``/``pointer_devices`` reuse the T05 status shape
        (``read_apply_status(...).as_json_dict()``); ``pointer_capabilities``
        is the same list under the protocol-style alias so v1 clients and
        new clients agree. ``backend`` is read tolerantly from the raw
        status file because the typed reader drops it; old files without
        the new keys still parse (``None``/``()``/``None``). Payloads stay
        bounded for the Acer reference floor (modes <=32, devices <=8,
        message <=500 chars). No backend command vocabulary is stored or
        returned here.
        """
        desired = self.hardware_store.read()
        status = read_apply_status(self.hardware_status_path, desired).as_json_dict()
        raw_modes = status.get("display_modes")
        display_modes = (
            list(raw_modes[:32]) if isinstance(raw_modes, list) else []
        )
        raw_devices = status.get("pointer_devices")
        pointer_devices = (
            list(raw_devices[:8]) if isinstance(raw_devices, list) else []
        )
        message = status.get("message", "")
        if not isinstance(message, str):
            message = str(message)
        message = message[:500]
        return {
            "desired": desired.as_json_dict(),
            "settings": status.get("settings"),
            "applied": bool(status.get("applied", False)),
            "backend": _read_hardware_backend(self.hardware_status_path),
            "display_output": status.get("display_output"),
            "display_modes": display_modes,
            "display_metrics": status.get("display_metrics"),
            "pointer_devices": pointer_devices,
            "pointer_capabilities": list(pointer_devices),
            "message": message,
        }

    def health_payload(self) -> dict[str, object]:
        try:
            payload = collect_health(self.registry, self.runtime.api_version).as_json_dict()
            payload["activity_catalogue_error"] = None
        except ActivityValidationError as exc:
            # A single broken newly-copied activity must not take down the parent
            # controls needed to diagnose or remove it.
            payload = collect_health(None, self.runtime.api_version).as_json_dict()
            payload["activity_catalogue_error"] = str(exc)
        payload["os"] = installed_os_identity()
        profiles = self.profiles_payload()
        active = self.active_session.read()
        payload["profiles"] = profiles
        payload["active_profile"] = active
        active_id = active.get("profile_id") if isinstance(active, dict) else None
        active_item = next(
            (item for item in profiles if item.get("profile_id") == active_id),
            profiles[0] if profiles else None,
        )
        payload["customization"] = (
            active_item.get("customization", {}) if isinstance(active_item, dict) else {}
        )
        payload["profile_policy"] = {
            "max_profiles": self.profile_store.policy.max_profiles,
            "avatars": list(self.profile_store.policy.avatars),
            "default_mask_secret": self.profile_store.policy.default_mask_secret,
        }
        payload["hardware"] = self.hardware_payload()
        payload["progress"] = self.progress_payload(
            str(active_id) if isinstance(active_id, str) and active_id else None
        )
        return payload

    def reset_customization(self, profile_id: str | None = None) -> dict[str, object]:
        if profile_id is None:
            active = self.active_session.read()
            profile_id = str(active.get("profile_id")) if active and active.get("profile_id") else self.profile_store.list_profiles()[0].profile_id
        store = self._theme_store(profile_id)
        store.reset()
        return store.resolve().as_json_dict()

    def create_profile(self, form: dict[str, list[str]]) -> dict[str, object]:
        profile = self.profile_store.create(
            _form_text(form, "display_name"),
            _form_text(form, "avatar_id"),
            secret=_form_text(form, "secret", default=""),
            mask_secret=_form_checked(form, "mask_secret"),
            uppercase_text=_form_checked(form, "uppercase_text"),
        )
        return profile.public_dict()

    def update_profile(self, form: dict[str, list[str]]) -> dict[str, object]:
        profile = self.profile_store.update(
            _form_text(form, "profile_id"),
            display_name=_form_text(form, "display_name"),
            avatar_id=_form_text(form, "avatar_id"),
            secret_action=_form_text(form, "secret_action", default="keep"),
            secret=_form_text(form, "secret", default=""),
            mask_secret=_form_checked(form, "mask_secret"),
            uppercase_text=_form_checked(form, "uppercase_text"),
        )
        return profile.public_dict()

    def delete_profile(self, form: dict[str, list[str]]) -> dict[str, object]:
        if _form_text(form, "confirm", default="") != "delete":
            raise ProfileError("profile deletion was not confirmed")
        profile_id = _form_text(form, "profile_id")
        self.active_session.delete_inactive(self.profile_store, profile_id)
        return {"deleted": profile_id}

    def update_hardware(self, form: dict[str, list[str]]) -> dict[str, object]:
        status = self.hardware_payload()
        raw_modes = status.get("display_modes", [])
        allowed_modes = tuple(
            str(mode.get("id"))
            for mode in raw_modes
            if isinstance(mode, dict) and isinstance(mode.get("id"), str)
        )
        resolution = form.get("resolution", ["auto"])[0]
        current = self.hardware_store.read()
        if not allowed_modes and resolution not in {"auto", current.resolution}:
            raise HardwareSettingsError("display modes are not available yet")
        updated = self.hardware_store.update(
            touchpad_tap=_form_checked(form, "touchpad_tap"),
            touchpad_speed=_form_float(form, "touchpad_speed"),
            mouse_speed=_form_float(form, "mouse_speed"),
            natural_scrolling=_form_checked(form, "natural_scrolling"),
            disable_while_typing=_form_checked(form, "disable_while_typing"),
            resolution=resolution,
            keyboard_layout=(
                _form_text(form, "keyboard_layout")
                if "keyboard_layout" in form
                else None
            ),
            mic_gain=(
                _form_float(form, "mic_gain")
                if "mic_gain" in form
                else None
            ),
            allowed_resolutions=allowed_modes or None,
        )
        return updated.as_json_dict()

    def reset_hardware(self) -> dict[str, object]:
        return self.hardware_store.reset().as_json_dict()

    def avatar_path(self, avatar_id: str) -> Path:
        self.profile_store.policy.validate_avatar(avatar_id)
        return self.assets.get(avatar_id).path_128


class ParentRequestHandler(BaseHTTPRequestHandler):
    server_version = "PipParent/0.7"
    # ``handle_expect_100`` is only invoked for an HTTP/1.1 handler. The
    # response below still forces ``Connection: close`` so the low-resource
    # one-request-per-connection policy does not change.
    protocol_version = "HTTP/1.1"

    def send_response(self, code: int, message: str | None = None) -> None:
        self.close_connection = True
        super().send_response(code, message)
        self.send_header("Connection", "close")

    def handle_expect_100(self) -> bool:  # noqa: N802
        """Accept large browser uploads without waiting for the 120 s timeout.

        Browsers send ``Expect: 100-continue`` for a package body and wait for
        an interim response before transmitting it. The default handler emits
        that interim line using this server's HTTP/1.0 protocol version, which
        the browser does not accept as a valid continue; the request then
        stalls until the socket timeout. Keep final responses on the existing
        one-request-per-connection HTTP/1.0 policy, but acknowledge the
        continue explicitly as HTTP/1.1.
        """
        self.wfile.write(b"HTTP/1.1 100 Continue\r\n\r\n")
        self.wfile.flush()
        return True

    @property
    def app(self) -> ParentStatusApplication:
        return self.server.app  # type: ignore[attr-defined]

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        if parsed.path == "/pair":
            if not self.app.authorized(self, query, allow_query_token=True):
                self._send_text(403, "Pairing token rejected.")
                return
            self.send_response(302)
            self.send_header("Location", "/")
            self.send_header(
                "Set-Cookie",
                f"greia_parent={self.app.token}; HttpOnly; SameSite=Strict; Path=/",
            )
            self.send_header("Cache-Control", "no-store")
            self._send_security_headers()
            self.end_headers()
            return
        if parsed.path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return
        if parsed.path == "/healthz":
            self._send_json(200, {"status": "ok"})
            return
        if not self.app.authorized(self, query):
            self._send_text(401, "Pair this browser from the local parent area first.")
            return
        if parsed.path.startswith("/assets/avatar/") and parsed.path.endswith(".png"):
            avatar_id = parsed.path.removeprefix("/assets/avatar/").removesuffix(".png")
            try:
                self._send_file(200, self.app.avatar_path(avatar_id), "image/png")
            except (ProfileError, KeyError, OSError):
                self._send_text(404, "Avatar not found")
            return
        if parsed.path == "/api/status":
            self._send_json(200, self.app.health_payload())
            return
        if parsed.path == "/api/profiles":
            self._send_json(200, self.app.profiles_payload())
            return
        if parsed.path == "/api/hardware":
            self._send_json(200, self.app.hardware_payload())
            return
        if parsed.path == "/api/progress":
            requested_profile = query.get("profile_id", [""])[0] or None
            try:
                payload = self.app.progress_payload(requested_profile)
            except ProfileError:
                self._send_text(404, "Profile not found")
                return
            self._send_json(200, payload)
            return
        if parsed.path == "/":
            self._send_html(200, render_status_page(self.app.health_payload()))
            return
        self._send_text(404, "Not found")

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        if not self.app.authorized(self, query):
            self._send_text(401, "Pair this browser from the local parent area first.")
            return
        length = self._content_length()
        if length > 16384:
            self._send_text(413, "Request too large")
            return
        body = self.rfile.read(length) if length else b""
        try:
            form = parse_qs(body.decode("utf-8"), keep_blank_values=True)
            if parsed.path == "/api/customization/reset":
                payload = self.app.reset_customization(_form_text(form, "profile_id", default="") or None)
            elif parsed.path == "/api/profiles/create":
                payload = self.app.create_profile(form)
            elif parsed.path == "/api/profiles/update":
                payload = self.app.update_profile(form)
            elif parsed.path == "/api/profiles/delete":
                payload = self.app.delete_profile(form)
            elif parsed.path == "/api/hardware":
                payload = self.app.update_hardware(form)
            elif parsed.path == "/api/hardware/reset":
                payload = self.app.reset_hardware()
            else:
                self._send_text(404, "Not found")
                return
            self._post_success(payload)
        except (UnicodeDecodeError, ValueError, HardwareSettingsError, ProfileError) as exc:
            self._send_text(400, str(exc))

    def _post_success(self, payload: object) -> None:
        if self.headers.get("Accept", "").startswith("application/json"):
            self._send_json(200, payload)
        else:
            self.send_response(303)
            self.send_header("Location", "/")
            self._send_security_headers()
            self.send_header("Cache-Control", "no-store")
            self.end_headers()

    def _content_length(self) -> int:
        try:
            return max(0, int(self.headers.get("Content-Length", "0")))
        except ValueError:
            return 0

    def log_message(self, format: str, *args: object) -> None:
        # Pairing tokens may arrive once in /pair?token=...; never copy request
        # paths or secrets into the persistent journal.
        return

    def _send_json(self, status: int, payload: object) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self._send_bytes(status, body, "application/json")

    def _send_text(self, status: int, text: str) -> None:
        self._send_bytes(status, text.encode("utf-8"), "text/plain; charset=utf-8")

    def _send_html(self, status: int, body_text: str) -> None:
        self._send_bytes(status, body_text.encode("utf-8"), "text/html; charset=utf-8")

    def _send_file(self, status: int, path: Path, content_type: str) -> None:
        self._send_bytes(status, path.read_bytes(), content_type)

    def _send_bytes(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self._send_security_headers()
        self.end_headers()
        self.wfile.write(body)


    def _send_security_headers(self) -> None:
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
            "script-src 'self' 'unsafe-inline'; connect-src 'self'; "
            "form-action 'self'; frame-ancestors 'none'; base-uri 'none'",
        )


class ParentHTTPServer(HTTPServer):
    """Intentionally single-request-at-a-time for the 768 MB reference floor."""

    allow_reuse_address = True
    request_timeout_seconds = 10.0

    def __init__(self, address: tuple[str, int], app: ParentStatusApplication):
        self.app = app
        super().__init__(address, ParentRequestHandler)

    def get_request(self):  # type: ignore[no-untyped-def]
        request, client_address = super().get_request()
        request.settimeout(self.request_timeout_seconds)
        return request, client_address


def render_status_page(payload: dict[str, object]) -> str:
    activities = payload.get("activities", ())
    activity_items = "".join(f"<li>{html.escape(str(item))}</li>" for item in activities)
    hardware = payload.get("hardware", {})
    if not isinstance(hardware, dict):
        hardware = {}
    desired = hardware.get("desired", {})
    if not isinstance(desired, dict):
        desired = {}
    modes = hardware.get("display_modes", [])
    if not isinstance(modes, list):
        modes = []
    profiles = payload.get("profiles", [])
    if not isinstance(profiles, list):
        profiles = []
    policy = payload.get("profile_policy", {})
    if not isinstance(policy, dict):
        policy = {}
    avatars = policy.get("avatars", [])
    if not isinstance(avatars, list):
        avatars = []
    active = payload.get("active_profile")
    active_name = active.get("display_name") if isinstance(active, dict) else None
    active_id = str(active.get("profile_id")) if isinstance(active, dict) and active.get("profile_id") else ""

    def gib(value: object) -> str:
        try:
            return f"{int(value) / (1024 ** 3):.2f} GiB"
        except (TypeError, ValueError):
            return "unknown"

    touchpad_tap = " checked" if desired.get("touchpad_tap") else ""
    natural_scrolling = " checked" if desired.get("natural_scrolling") else ""
    disable_while_typing = " checked" if desired.get("disable_while_typing") else ""
    mouse_speed = _safe_speed(desired.get("mouse_speed"))
    touchpad_speed = _safe_speed(desired.get("touchpad_speed"))
    resolution = str(desired.get("resolution", "auto"))
    keyboard_layout = str(desired.get("keyboard_layout", "us"))
    mode_ids = [
        str(mode.get("id"))
        for mode in modes
        if isinstance(mode, dict) and isinstance(mode.get("id"), str)
    ]
    options = ["auto", *[mode for mode in mode_ids if mode != "auto"]]
    if resolution not in options:
        options.append(resolution)
    resolution_options = "".join(
        f'<option value="{html.escape(mode)}"{" selected" if mode == resolution else ""}>'
        f'{html.escape("Automatic" if mode == "auto" else mode)}</option>'
        for mode in options
    )
    from greia_platform.keyboard_layout import available_layouts

    keyboard_layout_options = "".join(
        f'<option value="{html.escape(layout.id)}"{" selected" if layout.id == keyboard_layout else ""}>'
        f"{html.escape(layout.label)}</option>"
        for layout in available_layouts()
    )
    apply_status = html.escape(str(hardware.get("message", "Waiting for hardware session.")))
    avatar_options = _avatar_options(avatars, "")
    profile_cards = "".join(
        _render_profile_card(item, avatars, len(profiles), active_id)
        for item in profiles
        if isinstance(item, dict)
    )
    progress = payload.get("progress", {})
    if isinstance(progress, dict) and progress.get("available"):
        rewards = progress.get("reward_balances", {})
        reward_items = (
            "".join(
                f"<li>{html.escape(str(name))}: {html.escape(str(value))}</li>"
                for name, value in sorted(rewards.items())
            )
            if isinstance(rewards, dict) and rewards
            else "<li>No rewards yet</li>"
        )
        sessions = progress.get("recent_sessions", [])
        session_items = (
            "".join(
                f"<li>{html.escape(str(item.get('activity_id', 'Activity')))} — "
                f"{html.escape(str(item.get('exit_reason') or 'in progress'))}</li>"
                for item in sessions
                if isinstance(item, dict)
            )
            if isinstance(sessions, list) and sessions
            else "<li>No sessions yet</li>"
        )
        progress_html = (
            f"<p><strong>Rewards</strong></p><ul>{reward_items}</ul>"
            f"<p><strong>Recent activity</strong></p><ul>{session_items}</ul>"
        )
    else:
        progress_html = "<p>Progress is unavailable for the current child.</p>"

    return f"""<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Greia OS — Parent controls</title>
<style>
:root{{--cream:#f6ecd1;--paper:#fffaf0;--ink:#3d2c1f;--accent:#f1b923;--danger:#b52e2e}}
body{{font-family:system-ui,sans-serif;margin:0;background:var(--cream);color:var(--ink)}}
main{{max-width:64rem;margin:auto;padding:1.2rem}} section{{background:var(--paper);border-radius:1rem;padding:1rem;margin:1rem 0}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(16rem,1fr));gap:1rem}} .profile{{border:1px solid #0002;border-radius:1rem;padding:1rem}}
.avatar{{width:5rem;height:5rem;object-fit:contain}} label{{display:block;font-weight:700;margin:.6rem 0}} input,select{{box-sizing:border-box;width:100%;padding:.55rem;border:1px solid #0004;border-radius:.6rem;font:inherit}}
input[type=checkbox]{{width:auto}} input[type=range]{{padding:0}} button{{font:inherit;font-weight:700;border:0;border-radius:.8rem;padding:.8rem 1rem;background:var(--accent);color:var(--ink)}}
button.danger{{background:var(--danger);color:white}} .actions{{display:flex;gap:.7rem;flex-wrap:wrap;margin-top:1rem}} small{{display:block;margin-top:.35rem}} dt{{font-weight:700}}dd{{margin:0 0 .7rem}}
</style><main>
<h1>Parent controls</h1><p><strong>Current child:</strong> {html.escape(str(active_name or "Account picker"))}</p>
<section><dl><dt>Runtime API</dt><dd>{html.escape(str(payload.get('runtime_api_version','unknown')))}</dd><dt>Uptime</dt><dd>{html.escape(str(payload.get('uptime_seconds',0)))} seconds</dd><dt>Memory available</dt><dd>{gib(payload.get('memory_available_bytes'))} / {gib(payload.get('memory_total_bytes'))}</dd><dt>Disk free</dt><dd>{gib(payload.get('disk_free_bytes'))} / {gib(payload.get('disk_total_bytes'))}</dd></dl></section>
<section><h2>Child accounts</h2><p>Reset child appearance is available separately for every account.</p><div class="grid">{profile_cards}</div>
<h3>Add child</h3><form method="post" action="/api/profiles/create"><label>Name<input name="display_name" maxlength="24" required></label><label>Avatar<select name="avatar_id">{avatar_options}</select></label><label>Optional simple password — shown while typing by default<input name="secret" maxlength="32" autocomplete="new-password"></label><label><input type="checkbox" name="mask_secret"> Hide password on the child screen</label><label><input type="checkbox" name="uppercase_text" checked> CAPITAL-letter text (recommended for young children)</label><button type="submit">Add child</button></form></section>
<section><h2>Progress</h2>{progress_html}</section>
<section><h2>Mouse, touchpad, and screen</h2><form method="post" action="/api/hardware"><label><input type="checkbox" name="touchpad_tap"{touchpad_tap}> Tap touchpad to click</label><small>Disabled by default. Physical touchpad buttons continue to work.</small><label><input type="checkbox" name="disable_while_typing"{disable_while_typing}> Ignore touchpad while typing</label><small>Disabled by default.</small><label><input type="checkbox" name="natural_scrolling"{natural_scrolling}> Natural scrolling</label><div class="grid"><label>Keyboard layout<select name="keyboard_layout">{keyboard_layout_options}</select></label><label>Mouse speed<input type="range" name="mouse_speed" min="-1" max="1" step="0.25" value="{mouse_speed}"></label><label>Touchpad speed<input type="range" name="touchpad_speed" min="-1" max="1" step="0.25" value="{touchpad_speed}"></label><label>Screen resolution<select name="resolution">{resolution_options}</select></label></div><p><small>{apply_status}</small></p><button type="submit">Apply hardware settings</button></form><form method="post" action="/api/hardware/reset"><div class="actions"><button class="danger" type="submit">Restore hardware defaults</button></div></form></section>
<section><h2>Installed activities</h2><ul>{activity_items}</ul></section></main>"""


def _render_profile_card(
    profile: dict[str, object],
    avatars: list[object],
    profile_count: int,
    active_profile_id: str = "",
) -> str:
    profile_id = html.escape(str(profile.get("profile_id", "")))
    name = html.escape(str(profile.get("display_name", "")))
    avatar = str(profile.get("avatar_id", "unicorn"))
    avatar_escaped = html.escape(avatar)
    mask = " checked" if profile.get("mask_secret") else ""
    uppercase = " checked" if profile.get("uppercase_text", True) else ""
    protected = "Yes" if profile.get("has_secret") else "No"
    customization = profile.get("customization", {})
    wallpaper = "Yes" if isinstance(customization, dict) and customization.get("wallpaper_enabled") else "No"
    is_active = str(profile.get("profile_id", "")) == active_profile_id
    delete_disabled = " disabled" if profile_count <= 1 or is_active else ""
    delete_note = "<small>Switch to another child before deleting this active account.</small>" if is_active else ""
    return f"""<article class="profile"><img class="avatar" src="/assets/avatar/{avatar_escaped}.png" alt=""><h3>{name}</h3><p>Password: {protected} · Wallpaper: {wallpaper}</p>
<form method="post" action="/api/profiles/update"><input type="hidden" name="profile_id" value="{profile_id}"><label>Name<input name="display_name" maxlength="24" value="{name}" required></label><label>Avatar<select name="avatar_id">{_avatar_options(avatars, avatar)}</select></label><label>Password action<select name="secret_action"><option value="keep">Keep current</option><option value="set">Set or replace</option><option value="clear">Remove</option></select></label><label>New password<input name="secret" maxlength="32" autocomplete="new-password"></label><label><input type="checkbox" name="mask_secret"{mask}> Hide password while child types</label><label><input type="checkbox" name="uppercase_text"{uppercase}> CAPITAL-letter text (recommended for young children)</label><button type="submit">Save account</button></form>
<div class="actions"><form method="post" action="/api/customization/reset"><input type="hidden" name="profile_id" value="{profile_id}"><button class="danger" type="submit">Reset child appearance</button></form><form method="post" action="/api/profiles/delete"><input type="hidden" name="profile_id" value="{profile_id}"><input type="hidden" name="confirm" value="delete"><button class="danger" type="submit"{delete_disabled}>Delete child</button>{delete_note}</form></div></article>"""


def _avatar_options(avatars: list[object], selected: str) -> str:
    return "".join(
        f'<option value="{html.escape(str(item))}"{" selected" if str(item) == selected else ""}>{html.escape(str(item).replace("_", " ").title())}</option>'
        for item in avatars
    )


def _form_checked(form: dict[str, list[str]], name: str) -> bool:
    return name in form


def _form_float(form: dict[str, list[str]], name: str) -> float:
    return float(form.get(name, ["0"])[0])


def _form_text(form: dict[str, list[str]], name: str, *, default: str | None = None) -> str:
    values = form.get(name)
    if not values:
        if default is not None:
            return default
        raise ValueError(f"missing form field: {name}")
    return values[0]


def _safe_speed(value: object) -> str:
    try:
        numeric = min(1.0, max(-1.0, float(value)))
    except (TypeError, ValueError):
        numeric = 0.0
    return f"{numeric:.2f}"


_BACKEND_ID_ALLOWED = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-"
)


def _read_hardware_backend(status_path: Path) -> str | None:
    """Return the watcher backend id tolerantly; None when absent/invalid.

    Old status files without the ``backend`` key stay readable. Values
    longer than 64 chars, empty, non-text, or with characters outside the
    platform backend-id alphabet degrade to None rather than breaking the
    Parent payload. No subprocess or filesystem probing happens here.
    """
    try:
        raw = json.loads(status_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, UnicodeDecodeError, ValueError):
        return None
    if not isinstance(raw, dict):
        return None
    backend = raw.get("backend")
    if not isinstance(backend, str):
        return None
    backend = backend.strip()
    if not backend or len(backend) > 64:
        return None
    if any(character not in _BACKEND_ID_ALLOWED for character in backend):
        return None
    return backend


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bind", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--root", type=Path, default=Path(os.environ.get("GREIA_OS_ROOT", "/opt/greia-os")))
    parser.add_argument("--state-dir", type=Path, default=Path("/var/lib/greia-os"))
    parser.add_argument("--profiles-dir", type=Path, default=Path(os.environ.get("GREIA_PROFILES_DIR", "/var/lib/greia-profiles")))
    parser.add_argument("--hardware-settings-dir", type=Path, default=Path(os.environ.get("GREIA_SYSTEM_SETTINGS_DIR", "/var/lib/greia-system-settings")))
    parser.add_argument("--hardware-status-path", type=Path, default=Path(os.environ.get("GREIA_HARDWARE_STATUS", "/run/greia-hardware/status.json")))
    parser.add_argument("--active-profile-status-path", type=Path, default=Path(os.environ.get("GREIA_ACTIVE_PROFILE_STATUS", "/run/greia-os/active-profile.json")))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    app = ParentStatusApplication(
        args.root,
        args.state_dir,
        hardware_settings_dir=args.hardware_settings_dir,
        hardware_status_path=args.hardware_status_path,
        profiles_dir=args.profiles_dir,
        active_profile_status_path=args.active_profile_status_path,
    )
    ParentHTTPServer((args.bind, args.port), app).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
