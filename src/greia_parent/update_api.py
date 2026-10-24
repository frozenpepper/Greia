from __future__ import annotations

import os
from contextlib import contextmanager
from http.server import HTTPServer
from pathlib import Path
from uuid import uuid4
from typing import Iterator, cast
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
from greia_parent.update_catalog import (
    DEFAULT_UPDATE_INDEX_URL,
    UpdateCatalogClient,
    UpdateCatalogError,
)
from greia_parent.update_delivery import UpdateDeliveryError, UpdateDeliveryService
from greia_platform.software_update_jobs import (
    SoftwareUpdateCapacityError,
    SoftwareUpdateJobError,
    SoftwareUpdateJobStore,
    software_update_bootstrap_available,
)
from greia_platform.software_update_package import (
    MAX_SOFTWARE_UPDATE_BYTES,
    SOFTWARE_UPDATE_MEDIA_TYPE,
)


_ALLOWED_UPDATE_TYPES = frozenset(
    {
        BUNDLE_MEDIA_TYPE,
        "application/zip",
        "application/octet-stream",
    }
)
_UPDATE_UPLOAD_SOCKET_TIMEOUT_SECONDS = 120.0
SOFTWARE_UPDATE_PACKAGE_MEDIA_TYPE = SOFTWARE_UPDATE_MEDIA_TYPE


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
        update_privileged_client = kwargs.pop("update_privileged_client", None)
        update_catalog_client = kwargs.pop("update_catalog_client", None)
        software_update_enabled = kwargs.pop("software_update_enabled", None)
        software_update_job_store = kwargs.pop("software_update_job_store", None)
        if software_update_enabled is not None and not isinstance(software_update_enabled, bool):
            raise TypeError("software_update_enabled must be boolean when provided")
        configured_channel = os.environ.get("GREIA_SYSTEM_UPDATE_CHANNEL", "stable").strip()
        self.system_update_channel = configured_channel if configured_channel in {"stable", "dev"} else "stable"
        self.system_update_online_enabled = configured_channel in {"stable", "dev"}
        if update_catalog_client is None:
            index_url = os.environ.get("GREIA_SYSTEM_UPDATE_INDEX_URL", DEFAULT_UPDATE_INDEX_URL)
            try:
                update_catalog_client = UpdateCatalogClient(index_url)
            except UpdateCatalogError:
                self.system_update_online_enabled = False
                update_catalog_client = UpdateCatalogClient(DEFAULT_UPDATE_INDEX_URL)
        super().__init__(*args, **kwargs)
        self.software_update_enabled = (
            software_update_enabled
            if software_update_enabled is not None
            else software_update_bootstrap_available()
        )
        self.software_update_jobs = cast(
            SoftwareUpdateJobStore,
            software_update_job_store or SoftwareUpdateJobStore(),
        )
        self.update_inbox = SystemUpdateInbox(self.state_dir)
        self.system_update_upload_enabled = _system_update_upload_enabled()
        self.update_delivery = UpdateDeliveryService(
            self.state_dir,
            self.update_inbox,
            catalog=cast(UpdateCatalogClient, update_catalog_client),
            privileged=cast(object, update_privileged_client),
            channel=self.system_update_channel,
        )
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
                "system.update.package.install": self.software_update_enabled,
                "system.update.check": self.system_update_online_enabled,
                "system.update.prepare": self._system_update_prepare_available(),
                "system.update.restart": self._system_update_restart_available(),
                "system.update.activate": self._system_update_activation_available(),
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
        delivery = self.update_delivery.snapshot()
        readiness = delivery["readiness"]
        job = delivery["job"]
        activation_available = (
            isinstance(readiness, dict) and readiness.get("available") is True
        )
        public_job = _public_delivery_job(job)
        if isinstance(public_job, dict) and public_job.get("operation") != "check":
            payload["state"] = public_job.get("state", payload.get("state"))
        elif isinstance(public_job, dict) and payload.get("state") == "idle":
            payload["state"] = public_job.get("state", "idle")
        payload["upload_available"] = self.system_update_upload_enabled
        software_job = self.software_update_jobs.snapshot()
        software_restart_available = (
            self.software_update_enabled
            and isinstance(software_job, dict)
            and software_job.get("restart_available") is True
        )
        software_reason = (
            None
            if self.software_update_enabled
            else "This Greia needs the software update bootstrap before it can install package updates"
        )
        payload["software_update"] = {
            "available": self.software_update_enabled,
            "reason": software_reason,
            "job": software_job,
            "restart_available": software_restart_available,
        }
        payload["activation_available"] = activation_available
        payload["activation_reason"] = (
            readiness.get("reason", "Greia update readiness is unavailable")
            if isinstance(readiness, dict)
            else "Greia update readiness is unavailable"
        )
        software_busy = self._software_update_busy()
        payload["check_available"] = self.system_update_online_enabled and not software_busy
        payload["prepare_available"] = self._system_update_prepare_available()
        payload["restart_available"] = self._system_update_restart_available()
        payload["delivery"] = {
            "job": public_job,
            "readiness": readiness,
            "catalog": delivery["catalog"],
        }
        return payload

    def check_system_update(self) -> dict[str, object]:
        self._refuse_online_operation_during_software_update()
        if not self.system_update_online_enabled:
            raise UpdateDeliveryError("online Greia update checks are not configured")
        return self.update_delivery.check()

    def prepare_system_update(self, release_id: str) -> dict[str, object]:
        self._refuse_online_operation_during_software_update()
        if not self.system_update_online_enabled:
            raise UpdateDeliveryError("online Greia update preparation is not configured")
        return self.update_delivery.prepare(release_id)

    def request_system_update_restart(self) -> dict[str, object]:
        self._refuse_online_operation_during_software_update()
        return self.update_delivery.request_restart()

    @contextmanager
    def software_update_upload_lease(self) -> Iterator[None]:
        """Serialize package receipt and exclude the existing update inbox."""

        if not self.software_update_enabled:
            raise SoftwareUpdateJobError("software update bootstrap is unavailable")
        with self.software_update_jobs.receive_lease():
            if self.software_update_jobs.is_busy():
                raise SoftwareUpdateJobError("another software update job is active")
            with self.update_delivery.manual_upload_lease():
                yield

    def request_software_update_restart(self) -> dict[str, object]:
        if not self.software_update_enabled:
            raise SoftwareUpdateJobError("software update bootstrap is unavailable")
        return self.software_update_jobs.request_restart()

    def _software_update_busy(self) -> bool:
        return self.software_update_enabled and self.software_update_jobs.is_busy()

    def _refuse_online_operation_during_software_update(self) -> None:
        if self._software_update_busy():
            raise UpdateDeliveryError("another Greia software update operation is active")

    def _system_update_activation_available(self) -> bool:
        readiness = self.update_delivery.snapshot().get("readiness")
        return isinstance(readiness, dict) and readiness.get("available") is True

    def _system_update_prepare_available(self) -> bool:
        if (
            not self.system_update_online_enabled
            or self._software_update_busy()
            or not self._system_update_activation_available()
        ):
            return False
        catalog = self.update_delivery.snapshot().get("catalog")
        releases = catalog.get("releases") if isinstance(catalog, dict) else None
        return isinstance(releases, list) and bool(releases)

    def _system_update_restart_available(self) -> bool:
        if self._software_update_busy():
            return False
        snapshot = self.update_delivery.snapshot()
        job = snapshot.get("job")
        # A staged job remains explicitly retryable after an uncertain
        # handoff even when the cached identity/readiness snapshot is stale.
        # Root rechecks the profile-picker fence and staged journal before it
        # accepts REQUEST_RESTART, so this only controls the Parent affordance.
        return (
            isinstance(job, dict)
            and job.get("state") == "ready_to_restart"
        )

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
        if parsed.path == f"{API_BASE}/system/update/package":
            self._handle_software_update_upload()
            return
        if parsed.path == f"{API_BASE}/system/update/package/restart":
            self._handle_software_update_restart()
            return
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
        operation = {
            f"{API_BASE}/system/update/check": "check",
            f"{API_BASE}/system/update/prepare": "prepare",
            f"{API_BASE}/system/update/restart": "restart",
        }.get(parsed.path)
        if operation is not None:
            self._handle_update_operation(operation)
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
            # Receive directly on the update-state filesystem. The fixed
            # temporary (candidate.uploading) is atomically renamed to the
            # single fixed candidate (candidate.greiaupdate), avoiding a
            # second full-size local copy on the C0/Acer disk floor.
            with self.app.update_delivery.manual_upload_lease():
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
        except UpdateDeliveryError:
            self._send_api_error(409, "system_update_busy", "Another Greia update operation is active")
            return
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
                "activation_available": False,
                "status": self.app.system_update_payload(),
            },
        )

    def _handle_software_update_upload(self) -> None:
        query = parse_qs(urlparse(self.path).query)
        if not self._require_api_authorization(query):
            return
        if not self.app.software_update_enabled:
            self._send_api_error(
                403,
                "capability_unavailable",
                "This Greia needs the software update bootstrap before it can install package updates",
            )
            return
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type != SOFTWARE_UPDATE_PACKAGE_MEDIA_TYPE:
            self._send_api_error(
                415,
                "unsupported_software_update_type",
                "Upload a .greia_update package",
            )
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send_api_error(400, "invalid_content_length", "Invalid Content-Length")
            return
        if length <= 0 or length > MAX_SOFTWARE_UPDATE_BYTES:
            self._send_api_error(
                413,
                "software_update_too_large",
                f"Software update package must be between 1 and {MAX_SOFTWARE_UPDATE_BYTES} bytes",
            )
            return

        staging: Path | None = None
        try:
            with self.app.software_update_upload_lease():
                self.app.software_update_jobs.require_receive_capacity(length)
                staging = self.app.software_update_jobs.directory / f".uploading.{uuid4().hex}.tmp"
                descriptor = os.open(
                    staging,
                    os.O_WRONLY
                    | os.O_CREAT
                    | os.O_EXCL
                    | getattr(os, "O_NOFOLLOW", 0)
                    | getattr(os, "O_CLOEXEC", 0),
                    0o600,
                )
                self.connection.settimeout(_UPDATE_UPLOAD_SOCKET_TIMEOUT_SECONDS)
                with os.fdopen(descriptor, "wb") as handle:
                    remaining = length
                    while remaining:
                        chunk = self.rfile.read(min(1024 * 1024, remaining))
                        if not chunk:
                            raise SoftwareUpdateJobError("software update upload ended unexpectedly")
                        handle.write(chunk)
                        remaining -= len(chunk)
                    handle.flush()
                    os.fsync(handle.fileno())
                job = self.app.software_update_jobs.accept_received(staging, length)
        except SoftwareUpdateCapacityError as exc:
            self._send_api_error(507, "insufficient_storage", str(exc))
            return
        except (SoftwareUpdateJobError, UpdateDeliveryError) as exc:
            self._send_api_error(409, "software_update_unavailable", str(exc))
            return
        except (OSError, TimeoutError) as exc:
            self._send_api_error(400, "software_update_upload_failed", str(exc))
            return
        finally:
            if staging is not None:
                staging.unlink(missing_ok=True)

        self._send_json(202, {"job": job})

    def _handle_software_update_restart(self) -> None:
        query = parse_qs(urlparse(self.path).query)
        if not self._require_api_authorization(query):
            return
        if not self.app.software_update_enabled:
            self._send_api_error(
                403,
                "capability_unavailable",
                "Software update restart is unavailable on this Greia",
            )
            return
        try:
            body = self._read_json_object()
            if body:
                raise ValueError("software update restart request must be empty")
            job = self.app.request_software_update_restart()
        except SoftwareUpdateJobError as exc:
            self._send_api_error(409, "software_update_restart_unavailable", str(exc))
            return
        except (OSError, ValueError) as exc:
            self._send_api_error(400, "invalid_software_update_restart", str(exc))
            return
        self._send_json(202, {"job": job})

    def _handle_update_operation(self, operation: str) -> None:
        query = parse_qs(urlparse(self.path).query)
        if not self._require_api_authorization(query):
            return
        if operation in {"check", "prepare"} and not self.app.system_update_online_enabled:
            self._send_api_error(
                403,
                "capability_unavailable",
                "Online Greia updates are disabled on this image",
            )
            return
        try:
            body = self._read_json_object()
            if operation == "prepare":
                if set(body) != {"release_id"}:
                    raise ValueError("prepare requires only release_id")
                job = self.app.prepare_system_update(self._json_text(body, "release_id"))
            else:
                if body:
                    raise ValueError(f"{operation} does not accept request fields")
                if operation == "check":
                    job = self.app.check_system_update()
                else:
                    job = self.app.request_system_update_restart()
        except ValueError as exc:
            self._send_api_error(400, "invalid_system_update_request", str(exc))
            return
        except UpdateDeliveryError:
            self._send_api_error(
                409,
                "system_update_not_ready",
                "Greia cannot accept this update operation in its current state",
            )
            return
        public_job = _public_delivery_job(job)
        if public_job is None:
            self._send_api_error(500, "system_update_failed", "Greia could not queue the update operation")
            return
        self._send_json(202, {"job": public_job})


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
    # Manual code/system bundle upload remains opt-in on the explicit developer
    # lane. The Parent only receives the fixed inbox candidate; root independently
    # checks installed identity, A/B/PERSIST readiness and the candidate before
    # any inactive-slot write.
    marker = Path(
        os.environ.get(
            "GREIA_DEVELOPER_REMOTE_MARKER",
            "/etc/greia-os/developer-remote",
        )
    )
    return marker.is_file()


def _public_delivery_job(value: object) -> dict[str, object] | None:
    """Whitelist the finite Parent job contract, excluding URL and disk data."""

    if not isinstance(value, dict):
        return None
    operation = value.get("operation")
    state = value.get("state")
    if operation not in {"check", "prepare", "restart"} or state not in {
        "checking",
        "checked",
        "queued",
        "downloading",
        "receiving",
        "verifying",
        "staging",
        "ready_to_restart",
        "restart_pending",
        "updated",
        "rolled_back",
        "failed",
    }:
        return None
    job_id = value.get("job_id")
    if not isinstance(job_id, str) or len(job_id) != 32:
        return None
    return {
        "job_id": job_id,
        "operation": operation,
        "state": state,
        "release_id": _public_text(value.get("release_id"), 96),
        "version": _public_text(value.get("version"), 64),
        "downloaded_bytes": _public_int(value.get("downloaded_bytes")),
        "total_bytes": _public_int(value.get("total_bytes")),
        "created_at": _public_text(value.get("created_at"), 64),
        "updated_at": _public_text(value.get("updated_at"), 64),
        "error_code": _public_text(value.get("error_code"), 64),
        "error_message": _safe_public_error(value.get("error_message")),
        "restart_request_id": _public_text(value.get("restart_request_id"), 64),
    }


def _public_text(value: object, limit: int) -> str | None:
    return value[:limit] if isinstance(value, str) and value else None


def _public_int(value: object) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0


def _safe_public_error(value: object) -> str | None:
    text = _public_text(value, 256)
    if text is None:
        return None
    if "/" in text or "\\" in text:
        return "Greia could not complete the update operation."
    return text


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
