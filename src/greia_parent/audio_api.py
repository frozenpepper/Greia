from __future__ import annotations

from http.server import HTTPServer
from urllib.parse import parse_qs, urlparse

from greia_parent.protocol import API_BASE
from greia_parent.server import parse_args
from greia_parent.static_client import ParentStaticClient
from greia_parent.update_api import (
    UpdateParentApiApplication,
    UpdateParentApiRequestHandler,
)
from greia_platform.audio import AudioProcessingBackend, AudioService, AudioSettingsError


class AudioParentApiApplication(UpdateParentApiApplication):
    """Top-level Parent composition with typed microphone processing settings."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        audio_backend = kwargs.pop("audio_backend", None)
        super().__init__(*args, **kwargs)
        self.audio_service = AudioService.load(
            self.root / "runtime" / "audio-settings.toml",
            self.hardware_settings_dir,
            backend=audio_backend if isinstance(audio_backend, AudioProcessingBackend) else None,
        )

    def index_payload(self) -> dict[str, object]:
        payload = super().index_payload()
        capabilities = payload.get("capabilities")
        if isinstance(capabilities, dict):
            capabilities["settings.audio"] = True
        return payload

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


class AudioParentApiRequestHandler(UpdateParentApiRequestHandler):
    @property
    def app(self) -> AudioParentApiApplication:
        return self.server.app  # type: ignore[attr-defined,return-value]

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == f"{API_BASE}/settings/audio":
            query = parse_qs(parsed.query)
            if not self._require_api_authorization(query):
                return
            self._send_json(200, self.app.audio_payload())
            return
        super().do_GET()

    def do_PUT(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path != f"{API_BASE}/settings/audio":
            super().do_PUT()
            return
        query = parse_qs(parsed.query)
        if not self._require_api_authorization(query):
            return
        try:
            body = self._read_json_object()
            payload = self.app.update_audio(
                microphone_processing_enabled=body.get("microphone_processing_enabled"),
                advanced_noise_reduction=body.get("advanced_noise_reduction"),
            )
        except (AudioSettingsError, OSError, TypeError, ValueError) as exc:
            self._send_api_error(400, "invalid_audio_settings", str(exc))
            return
        self._send_json(200, payload)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path != f"{API_BASE}/settings/audio/reset":
            super().do_POST()
            return
        query = parse_qs(parsed.query)
        if not self._require_api_authorization(query):
            return
        try:
            payload = self.app.reset_audio()
        except (AudioSettingsError, OSError, TypeError, ValueError) as exc:
            self._send_api_error(400, "audio_reset_failed", str(exc))
            return
        self._send_json(200, payload)


class AudioParentApiHTTPServer(HTTPServer):
    def __init__(
        self,
        address: tuple[str, int],
        app: AudioParentApiApplication,
        *,
        static_client: ParentStaticClient | None = None,
    ) -> None:
        self.app = app
        self.static_client = static_client or ParentStaticClient.from_environment()
        HTTPServer.__init__(self, address, AudioParentApiRequestHandler)


def main() -> int:
    args = parse_args()
    app = AudioParentApiApplication(
        args.root,
        args.state_dir,
        hardware_settings_dir=args.hardware_settings_dir,
        hardware_status_path=args.hardware_status_path,
        profiles_dir=args.profiles_dir,
        active_profile_status_path=args.active_profile_status_path,
    )
    AudioParentApiHTTPServer((args.bind, args.port), app).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
