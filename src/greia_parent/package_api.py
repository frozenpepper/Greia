from __future__ import annotations

import os
import tempfile
from http.server import HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from greia_parent.api_server import (
    ParentApiApplication,
    ParentApiHTTPServer,
    ParentApiRequestHandler,
)
from greia_parent.protocol import API_BASE, api_index_payload
from greia_parent.server import parse_args
from greia_parent.static_client import ParentStaticClient
from greia_platform.activities import ActivityRegistry, ActivityValidationError
from greia_platform.activity_package_format import ACTIVITY_PACKAGE_MEDIA_TYPE
from greia_platform.activity_packages import (
    MAX_ARCHIVE_BYTES,
    ActivityPackageError,
    ActivityPackageService,
)
from greia_platform.trust import ActivitySource, PackageTrust


_ALLOWED_PACKAGE_TYPES = frozenset(
    {
        ACTIVITY_PACKAGE_MEDIA_TYPE,
        # The raw upload protocol carries no original filename. Generic ZIP and
        # octet-stream remain transport compatibility values only; neither is
        # treated as evidence that the bytes are a valid Greia Activity package.
        "application/zip",
        "application/octet-stream",
    }
)


class PackageParentApiApplication(ParentApiApplication):
    """Parent API composition with bounded local Activity package management."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self.package_service = ActivityPackageService.from_environment()
        self.activity_install_enabled = _activity_install_enabled()
        # Install and remove are both package-code mutations and therefore share
        # the same explicit owner/developer enablement boundary while transport
        # remains provisional HTTP.
        self.activity_remove_enabled = self.activity_install_enabled

    def index_payload(self) -> dict[str, object]:
        return api_index_payload(
            {
                "activities.install": self.activity_install_enabled,
                "activities.remove": self.activity_remove_enabled,
            }
        )

    def activities_payload(self) -> list[dict[str, object]]:
        # Parent-installed Activities are a distinct trust source. Never fold
        # them into the immutable built-in root merely for discovery convenience.
        sources = (
            ActivitySource(
                self.root / "activities",
                PackageTrust.BUILT_IN,
                "greia-system",
            ),
            ActivitySource(
                self.package_service.active_root,
                PackageTrust.PARENT_TRUSTED_UNSIGNED,
                self.package_service.SOURCE_ID,
            ),
        )
        registry = ActivityRegistry(sources, self.package_service.runtime)
        return [
            {
                "activity_id": registration.manifest.activity_id,
                "version": registration.manifest.version,
                "title_key": registration.manifest.title_key,
                "icon_id": registration.manifest.icon_id,
                "categories": list(registration.manifest.categories),
                "launcher_categories": list(
                    registration.manifest.launcher_categories
                    or registration.manifest.categories
                ),
                "discovery_tags": list(registration.manifest.discovery_tags),
                "difficulty": registration.manifest.difficulty,
                "difficulty_min": registration.manifest.difficulty_min,
                "difficulty_max": registration.manifest.difficulty_max,
                "adaptive_difficulty": registration.manifest.adaptive_difficulty,
                "recommended_age_min": registration.manifest.recommended_age_min,
                "recommended_age_max": registration.manifest.recommended_age_max,
                "languages": list(registration.manifest.languages),
                "input_profile": registration.manifest.input_profile,
                "package_trust": registration.package_trust.value,
                "source_id": registration.source_id,
                "removable": (
                    registration.package_trust == PackageTrust.PARENT_TRUSTED_UNSIGNED
                    and registration.source_id == self.package_service.SOURCE_ID
                ),
            }
            for registration in registry.discover_registrations()
        ]


class PackageParentApiRequestHandler(ParentApiRequestHandler):
    @property
    def app(self) -> PackageParentApiApplication:
        return self.server.app  # type: ignore[attr-defined,return-value]

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == API_BASE:
            query = parse_qs(parsed.query)
            if not self._require_api_authorization(query):
                return
            self._send_json(200, self.app.index_payload())
            return
        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path != f"{API_BASE}/activities/install":
            super().do_POST()
            return
        query = parse_qs(parsed.query)
        if not self._require_api_authorization(query):
            return
        if not self.app.activity_install_enabled:
            self._send_api_error(
                403,
                "capability_unavailable",
                "Activity installation is disabled on this Greia image",
            )
            return
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type not in _ALLOWED_PACKAGE_TYPES:
            self._send_api_error(
                415,
                "unsupported_package_type",
                "Upload a .greiaactivity ZIP package",
            )
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send_api_error(400, "invalid_content_length", "Invalid Content-Length")
            return
        if length <= 0 or length > MAX_ARCHIVE_BYTES:
            self._send_api_error(
                413,
                "package_too_large",
                f"Activity package must be between 1 and {MAX_ARCHIVE_BYTES} bytes",
            )
            return

        upload: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                prefix="greia-parent-upload-",
                suffix=".greiaactivity",
                delete=False,
            ) as handle:
                upload = Path(handle.name)
                remaining = length
                while remaining:
                    chunk = self.rfile.read(min(1024 * 1024, remaining))
                    if not chunk:
                        raise ActivityPackageError("Activity package upload ended unexpectedly")
                    handle.write(chunk)
                    remaining -= len(chunk)
            receipt = self.app.package_service.install_archive(upload)
        except (ActivityPackageError, ActivityValidationError, OSError) as exc:
            self._send_api_error(400, "activity_install_rejected", str(exc))
            return
        finally:
            if upload is not None:
                upload.unlink(missing_ok=True)
        self._send_json(201, {"installed": receipt.as_json_dict()})

    def do_DELETE(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        prefix = f"{API_BASE}/activities/"
        if not parsed.path.startswith(prefix):
            super().do_DELETE()
            return
        query = parse_qs(parsed.query)
        if not self._require_api_authorization(query):
            return
        if not self.app.activity_remove_enabled:
            self._send_api_error(
                403,
                "capability_unavailable",
                "Activity removal is disabled on this Greia image",
            )
            return
        encoded_id = parsed.path[len(prefix) :]
        if not encoded_id or "/" in encoded_id:
            self._send_api_error(404, "not_found", "Not found")
            return
        activity_id = unquote(encoded_id)
        try:
            receipt = self.app.package_service.uninstall(activity_id)
        except (ActivityPackageError, ActivityValidationError, OSError) as exc:
            self._send_api_error(400, "activity_remove_rejected", str(exc))
            return
        self._send_json(200, {"removed": receipt.as_json_dict()})


class PackageParentApiHTTPServer(ParentApiHTTPServer):
    def __init__(
        self,
        address: tuple[str, int],
        app: PackageParentApiApplication,
        *,
        static_client: ParentStaticClient | None = None,
    ) -> None:
        self.app = app
        self.static_client = static_client or ParentStaticClient.from_environment()
        HTTPServer.__init__(self, address, PackageParentApiRequestHandler)


def _activity_install_enabled() -> bool:
    explicit = os.environ.get("GREIA_PARENT_ACTIVITY_INSTALL", "").strip().casefold()
    if explicit in {"1", "true", "yes", "on"}:
        return True
    if explicit in {"0", "false", "no", "off"}:
        return False
    marker = Path(
        os.environ.get(
            "GREIA_DEVELOPER_REMOTE_MARKER",
            "/etc/greia-os/developer-remote",
        )
    )
    return marker.is_file()


def main() -> int:
    args = parse_args()
    app = PackageParentApiApplication(
        args.root,
        args.state_dir,
        hardware_settings_dir=args.hardware_settings_dir,
        hardware_status_path=args.hardware_status_path,
        profiles_dir=args.profiles_dir,
        active_profile_status_path=args.active_profile_status_path,
    )
    PackageParentApiHTTPServer((args.bind, args.port), app).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
