"""Bounded loopback transport for the existing shared VoxStage worker."""
from __future__ import annotations

import json
import os
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from .providers import VoiceProviderError


class VoxStageServiceError(VoiceProviderError):
    """A service/transport failure, optionally carrying an HTTP status."""

    def __init__(self, detail: str, status: int | None = None) -> None:
        super().__init__(detail)
        self.status = status


class _NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class VoxStageClient:
    """Own HTTP exchanges, job polling and artifact transfer, never model lifecycle.

    VoxStage serializes inference and owns its model/library. This client neither
    starts another model process nor shuts down a worker shared with other projects.
    POSTs are never automatically repeated. A timeout reports the job identity so
    the operator can recover the same work rather than submit a duplicate.
    """

    MAX_JSON_BYTES = 8 * 1024 * 1024
    MAX_AUDIO_BYTES = 64 * 1024 * 1024

    def __init__(
        self,
        base_url: str | None = None,
        job_timeout: float | None = None,
        poll_interval: float = 1.0,
        http_timeout: float | None = None,
    ) -> None:
        self.base_url = (base_url or os.environ.get("GREIA_VOXSTAGE_URL", "http://127.0.0.1:8791")).rstrip("/")
        parsed = urlsplit(self.base_url)
        if (
            parsed.scheme != "http"
            or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
            or parsed.username or parsed.password
            or parsed.path or parsed.query or parsed.fragment
        ):
            raise ValueError("GREIA_VOXSTAGE_URL must be a loopback HTTP origin")
        # Validate malformed ports now, before any speech can be submitted.
        parsed.port
        self.job_timeout = float(job_timeout if job_timeout is not None else os.environ.get("GREIA_VOXSTAGE_TIMEOUT", "1800"))
        if not 1 <= self.job_timeout <= 7200 or not 0 < poll_interval <= 10:
            raise ValueError("VoxStage timeout must be 1–7200 seconds; poll interval must be 0–10 seconds")
        self.http_timeout = float(http_timeout if http_timeout is not None else os.environ.get("GREIA_VOXSTAGE_HTTP_TIMEOUT", "120"))
        if not 1 <= self.http_timeout <= 7200:
            raise ValueError("VoxStage HTTP timeout must be 1–7200 seconds")
        self.poll_interval = poll_interval
        self.opener = build_opener(ProxyHandler({}), _NoRedirects())

    def _request(self, route: str, payload: dict | None = None, key: str | None = None) -> Request:
        headers = {"Accept": "application/json"}
        token = os.environ.get("VOXSTAGE_API_KEY", "").strip()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if key:
            headers["Idempotency-Key"] = key
        body = None
        if payload is not None:
            headers["Content-Type"] = "application/json"
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        return Request(self.base_url + route, data=body, headers=headers)

    def json(self, route: str, payload: dict | None = None, key: str | None = None) -> dict:
        try:
            with self.opener.open(self._request(route, payload, key), timeout=self.http_timeout) as response:
                raw = response.read(self.MAX_JSON_BYTES + 1)
            if len(raw) > self.MAX_JSON_BYTES:
                raise VoxStageServiceError("VoxStage JSON response exceeds the transport bound")
            result = json.loads(raw)
            if not isinstance(result, dict):
                raise VoxStageServiceError("VoxStage returned an invalid object response")
            return result
        except HTTPError as exc:
            try:
                detail = json.loads(exc.read(4096)).get("detail", exc.reason)
            except (ValueError, AttributeError):
                detail = exc.reason
            raise VoxStageServiceError(f"VoxStage HTTP {exc.code}: {detail}", exc.code) from exc
        except (URLError, OSError, ValueError) as exc:
            raise VoxStageServiceError(
                f"VoxStage request failed at {self.base_url}{route}: {exc}. Start the installed service with 'voxstage start'; do not resubmit uncertain POSTs."
            ) from exc

    def wait_job(self, job_id: str) -> dict:
        deadline = time.monotonic() + self.job_timeout
        try:
            while time.monotonic() < deadline:
                record = self.json(f"/v1/jobs/{job_id}?summary=true")
                state = record.get("status")
                if state == "completed":
                    return self.json(f"/v1/jobs/{job_id}")
                if state in {"failed", "interrupted"}:
                    raise VoxStageServiceError(f"VoxStage job {job_id} {state}: {record.get('error')}")
                if state not in {"queued", "running"}:
                    raise VoxStageServiceError(f"VoxStage job {job_id} has unexpected status: {state}")
                time.sleep(min(self.poll_interval, max(0, deadline - time.monotonic())))
        except VoxStageServiceError as exc:
            raise VoxStageServiceError(f"{exc}; inspect 'voxstage jobs get {job_id}' before retrying") from exc
        raise VoxStageServiceError(
            f"Timed out waiting for VoxStage job {job_id}. The shared worker may still be running it; inspect 'voxstage jobs get {job_id}' before resubmitting."
        )

    def download(self, job_id: str, filename: str, destination: Path) -> None:
        route = f"/v1/jobs/{job_id}/files/{filename}"
        try:
            with self.opener.open(self._request(route), timeout=self.http_timeout) as response:
                remaining = self.MAX_AUDIO_BYTES
                with destination.open("wb") as stream:
                    while True:
                        block = response.read(min(1024 * 1024, remaining + 1))
                        if not block:
                            break
                        remaining -= len(block)
                        if remaining < 0:
                            raise VoxStageServiceError("VoxStage audio exceeds the transport bound")
                        stream.write(block)
        except (URLError, OSError) as exc:
            raise VoxStageServiceError(f"Could not retrieve audio from VoxStage job {job_id}: {exc}") from exc
