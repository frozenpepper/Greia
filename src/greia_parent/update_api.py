from __future__ import annotations

import os
from http.server import HTTPServer
from pathlib import Path
from typing import cast
from urllib.parse import parse_qs, urlparse

from greia_parent.package_api import (
    PackageParentApiApplication,
    PackageParentApiRequestHandler,
)
from greia_parent.protocol import API_BASE, api_index_payload
from greia_parent.server import parse_args
from greia_parent.static_client import ParentStaticClient
from greia_platform.audio import AudioProcessingBackend, AudioService, AudioSettingsError
from greia_platform.customization import ThemeStore
from greia_platform.profile_presentation import (
    ProfilePresentationError,
    ProfilePresentationStore,
)
from greia_platform.profiles import ProfileError
from greia_platform.system_controls import (
    SystemControlError,
    SystemControlSettingsStore,
)
from greia_platform.system_language import SystemLanguageError, SystemLanguageStore
from greia_platform.system_updates import (
    BUNDLE_MEDIA_TYPE,
    MAX_BUNDLE_BYTES,
    SystemUpdateError,
    SystemUpdateInbox,
)


_ALLOWED_UPDATE_TYPES = frozenset(
    {
        BUNDLE_MEDIA_TYPE,
        "application/zip",
        "application/octet-stream",
    }
)
_UPDATE_UPLOAD_SOCKET_TIMEOUT_SECONDS = 120.0


class UpdateParentApiApplication(PackageParentApiApplication):
    """Top-level Parent composition for typed settings and bounded delivery.

    The HTTP process can receive bounded update bytes and mutate only typed
    Greia settings such as language, output volume, microphone processing and
    profile-scoped presentation preferences. It is intentionally not a privileged
    updater/audio daemon and cannot install DSP code, write OS slots, select boot
    targets or directly own mixer/backlight devices.
    """

    def __init__(self, *args: object, **kwargs: object) -> None:
        audio_backend = cast(
            AudioProcessingBackend | None, kwargs.pop("audio_backend", None)
        )
        super().__init__(*args, **kwargs)
        self.update_inbox = SystemUpdateInbox(self.state_dir)
        self.system_update_upload_enabled = _system_update_upload_enabled()
        self.language_store = SystemLanguageStore(
            self.hardware_settings_dir,
            install_record_path=Path(
                os.environ.get(
                    "GREIA_INSTALL_RECORD",
                    "/etc/greia-os/install-record.json",
                )
            ),
        )
        self.audio_service = AudioService.load(
            self.root / "runtime" / "audio-settings.toml",
            self.hardware_settings_dir,
            backend=audio_backend,
        )
        self.system_controls = SystemControlSettingsStore(self.hardware_settings_dir)

    def index_payload(self) -> dict[str, object]:
        return api_index_payload(
            {
                "activities.install": self.activity_install_enabled,
                "system.update.upload": self.system_update_upload_enabled,
                # No current single-root Greia profile has a proven transactional
                # slot backend. Do not infer activation from upload availability.
                "system.update.activate": False,
                # This concrete top-level composition owns the typed AudioService.
                "settings.audio": True,
                "settings.system_controls": True,
                "profiles.presentation": True,
            }
        )

    def profiles_payload(self) -> list[dict[str, object]]:
        profiles = super().profiles_payload()
        for payload in profiles:
            profile_id = payload.get("profile_id")
            if not isinstance(profile_id, str) or not profile_id:
                continue
            preferences = ProfilePresentationStore(
                self.profile_store.context(profile_id).customization_dir
            ).read()
            payload["presentation"] = preferences.presentation.value
            payload["grammatical_gender"] = preferences.grammatical_gender.value
        return profiles

    def profile_presentation_payload(self, profile_id: str) -> dict[str, object]:
        context = self.profile_store.context(profile_id)
        preferences = ProfilePresentationStore(context.customization_dir).read()
        return {
            "profile_id": profile_id,
            **preferences.as_json_dict(),
        }

    def update_profile_presentation(
        self,
        profile_id: str,
        *,
        presentation: str,
        seed_theme_if_unset: bool,
    ) -> dict[str, object]:
        context = self.profile_store.context(profile_id)
        store = ProfilePresentationStore(context.customization_dir)
        preferences = store.set(presentation)
        theme_seeded = False
        if seed_theme_if_unset:
            theme = ThemeStore.load(
                self.root / "runtime" / "theme-defaults.toml",
                context.customization_dir,
            )
            theme_seeded = store.seed_theme_if_unset(theme, preferences)
        return {
            "profile_id": profile_id,
            **preferences.as_json_dict(),
            "theme_seeded": theme_seeded,
        }

    def system_update_payload(self) -> dict[str, object]:
        payload = self.update_inbox.status_payload()
        payload["upload_available"] = self.system_update_upload_enabled
        payload["activation_available"] = False
        payload["activation_reason"] = (
            "A/B system-slot backend is not configured for this image"
        )
        return payload

    def language_payload(self) -> dict[str, object]:
        return self.language_store.as_json_dict()

    def update_language(self, locale: str) -> dict[str, object]:
        self.language_store.replace(locale)
        return self.language_store.as_json_dict()

    def audio_payload(self) -> dict[str, object]:
        return self.audio_service.payload()

    def update_audio(
        self,
        *,
        microphone_processing_enabled: object | None = None,
        advanced_noise_reduction: object | None = None,
    ) -> dict[str, object]:
        return self.audio_service.update(
            microphone_processing_enabled=microphone_processing_enabled,
            advanced_noise_reduction=advanced_noise_reduction,
        )

    def reset_audio(self) -> dict[str, object]:
        return self.audio_service.reset()

    def system_controls_payload(self) -> dict[str, object]:
        """Return bounded desired state; host mixer/backlight details stay private."""

        return self.system_controls.read().as_json_dict()

    def update_system_controls(
        self,
        *,
        volume_percent: object | None = None,
        muted: object | None = None,
    ) -> dict[str, object]:
        """Update Parent-owned output controls consumed by greia-hardware."""

        return self.system_controls.update(
            volume_percent=volume_percent,
            muted=muted,
        ).as_json_dict()


class UpdateParentApiRequestHandler(PackageParentApiRequestHandler):
    @property
    def app(self) -> UpdateParentApiApplication:
        return self.server.app  # type: ignore[attr-defined,return-value]

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == API_BASE:
            query = parse_qs(parsed.query)
            if not self._require_api_authorization(query):
                return
            self._send_json(200, self.app.index_payload())
            return
        presentation_profile_id = _profile_presentation_id(parsed.path)
        if presentation_profile_id is not None:
            query = parse_qs(parsed.query)
            if not self._require_api_authorization(query):
                return
            try:
                payload = self.app.profile_presentation_payload(
                    presentation_profile_id
                )
            except ProfileError:
                self._send_api_error(404, "profile_not_found", "Profile not found")
                return
            self._send_json(200, payload)
            return
        if parsed.path == f"{API_BASE}/system/update":
            query = parse_qs(parsed.query)
            if not self._require_api_authorization(query):
                return
            self._send_json(200, self.app.system_update_payload())
            return
        if parsed.path == f"{API_BASE}/settings/language":
            query = parse_qs(parsed.query)
            if not self._require_api_authorization(query):
                return
            self._send_json(200, self.app.language_payload())
            return
        if parsed.path == f"{API_BASE}/settings/audio":
            query = parse_qs(parsed.query)
            if not self._require_api_authorization(query):
                return
            self._send_json(200, self.app.audio_payload())
            return
        if parsed.path == f"{API_BASE}/settings/system-controls":
            query = parse_qs(parsed.query)
            if not self._require_api_authorization(query):
                return
            self._send_json(200, self.app.system_controls_payload())
            return
        super().do_GET()

    def do_PUT(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        presentation_profile_id = _profile_presentation_id(parsed.path)
        if presentation_profile_id is not None:
            query = parse_qs(parsed.query)
            if not self._require_api_authorization(query):
                return
            try:
                body = self._read_json_object()
                seed_theme_if_unset = body.get("seed_theme_if_unset", False)
                if not isinstance(seed_theme_if_unset, bool):
                    raise ValueError("seed_theme_if_unset must be boolean")
                payload = self.app.update_profile_presentation(
                    presentation_profile_id,
                    presentation=self._json_text(body, "presentation"),
                    seed_theme_if_unset=seed_theme_if_unset,
                )
            except ProfileError:
                self._send_api_error(404, "profile_not_found", "Profile not found")
                return
            except (ProfilePresentationError, OSError, ValueError) as exc:
                self._send_api_error(400, "invalid_profile_presentation", str(exc))
                return
            self._send_json(200, payload)
            return
        if parsed.path == f"{API_BASE}/settings/system-controls":
            query = parse_qs(parsed.query)
            if not self._require_api_authorization(query):
                return
            try:
                body = self._read_json_object()
                allowed = {"volume_percent", "muted"}
                unknown = set(body) - allowed
                if unknown:
                    raise ValueError(
                        "unsupported system control field: " + ", ".join(sorted(unknown))
                    )
                if not body:
                    raise ValueError("at least one system control is required")
                if "volume_percent" in body and body["volume_percent"] is None:
                    raise ValueError("volume_percent cannot be null")
                if "muted" in body and body["muted"] is None:
                    raise ValueError("muted cannot be null")
                payload = self.app.update_system_controls(
                    volume_percent=body.get("volume_percent"),
                    muted=body.get("muted"),
                )
            except (SystemControlError, OSError, TypeError, ValueError) as exc:
                self._send_api_error(400, "invalid_system_controls", str(exc))
                return
            self._send_json(200, payload)
            return
        if parsed.path == f"{API_BASE}/settings/audio":
            query = parse_qs(parsed.query)
            if not self._require_api_authorization(query):
                return
            try:
                body = self._read_json_object()
                payload = self.app.update_audio(
                    microphone_processing_enabled=body.get(
                        "microphone_processing_enabled"
                    ),
                    advanced_noise_reduction=body.get("advanced_noise_reduction"),
                )
            except (AudioSettingsError, OSError, TypeError, ValueError) as exc:
                self._send_api_error(400, "invalid_audio_settings", str(exc))
                return
            self._send_json(200, payload)
            return
        if parsed.path != f"{API_BASE}/settings/language":
            super().do_PUT()
            return
        query = parse_qs(parsed.query)
        if not self._require_api_authorization(query):
            return
        try:
            body = self._read_json_object()
            payload = self.app.update_language(self._json_text(body, "locale"))
        except (SystemLanguageError, OSError, ValueError) as exc:
            self._send_api_error(400, "invalid_system_language", str(exc))
            return
        self._send_json(200, payload)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == f"{API_BASE}/settings/audio/reset":
            query = parse_qs(parsed.query)
            if not self._require_api_authorization(query):
                return
            try:
                payload = self.app.reset_audio()
            except (AudioSettingsError, OSError, TypeError, ValueError) as exc:
                self._send_api_error(400, "audio_reset_failed", str(exc))
                return
            self._send_json(200, payload)
            return
        if parsed.path != f"{API_BASE}/system/update/bundle":
            super().do_POST()
            return
        query = parse_qs(parsed.query)
        if not self._require_api_authorization(query):
            return
        if not self.app.system_update_upload_enabled:
            self._send_api_error(
                403,
                "capability_unavailable",
                "System update upload is disabled on this Greia image",
            )
            return
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type not in _ALLOWED_UPDATE_TYPES:
            self._send_api_error(
                415,
                "unsupported_update_type",
                "Upload a .greiaupdate bundle",
            )
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send_api_error(400, "invalid_content_length", "Invalid Content-Length")
            return
        if length <= 0 or length > MAX_BUNDLE_BYTES:
            self._send_api_error(
                413,
                "update_too_large",
                f"Update bundle must be between 1 and {MAX_BUNDLE_BYTES} bytes",
            )
            return

        upload: Path | None = None
        try:
            # Receive directly on the update-state filesystem. The exact staged
            # inode is later hard-linked to its content-addressed candidate name,
            # avoiding a second full-size local copy on the C0/Acer disk floor.
            upload = self.app.update_inbox.create_receive_staging(length)
            self.connection.settimeout(_UPDATE_UPLOAD_SOCKET_TIMEOUT_SECONDS)
            with upload.open("wb") as handle:
                remaining = length
                while remaining:
                    chunk = self.rfile.read(min(1024 * 1024, remaining))
                    if not chunk:
                        raise SystemUpdateError("system update upload ended unexpectedly")
                    handle.write(chunk)
                    remaining -= len(chunk)
            if upload.stat().st_size != length:
                raise SystemUpdateError("system update upload size did not match Content-Length")
            queued = self.app.update_inbox.receive_staged(upload)
        except (SystemUpdateError, OSError, TimeoutError) as exc:
            self._send_api_error(400, "system_update_rejected", str(exc))
            return
        finally:
            if upload is not None:
                upload.unlink(missing_ok=True)

        self._send_json(
            202,
            {
                "received": queued.manifest.as_json_dict(),
                "signature_verified": False,
                "activation_available": False,
                "status": self.app.system_update_payload(),
            },
        )


class UpdateParentApiHTTPServer(HTTPServer):
    def __init__(
        self,
        address: tuple[str, int],
        app: UpdateParentApiApplication,
        *,
        static_client: ParentStaticClient | None = None,
    ) -> None:
        self.app = app
        self.static_client = static_client or ParentStaticClient.from_environment()
        HTTPServer.__init__(self, address, UpdateParentApiRequestHandler)


def _profile_presentation_id(path: str) -> str | None:
    prefix = f"{API_BASE}/profiles/"
    suffix = "/presentation"
    if not path.startswith(prefix) or not path.endswith(suffix):
        return None
    value = path[len(prefix) : -len(suffix)]
    if not value or "/" in value:
        return None
    return value


def _system_update_upload_enabled() -> bool:
    explicit = os.environ.get("GREIA_PARENT_SYSTEM_UPDATE_UPLOAD", "").strip().casefold()
    if explicit in {"1", "true", "yes", "on"}:
        return True
    if explicit in {"0", "false", "no", "off"}:
        return False
    # Code/system bundle delivery remains disabled on provisional plaintext Parent
    # transport except on the explicit developer lane. Receiving is still only an
    # unprivileged inbox operation; privileged activation remains unavailable.
    marker = Path(
        os.environ.get(
            "GREIA_DEVELOPER_REMOTE_MARKER",
            "/etc/greia-os/developer-remote",
        )
    )
    return marker.is_file()


def main() -> int:
    args = parse_args()
    app = UpdateParentApiApplication(
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
