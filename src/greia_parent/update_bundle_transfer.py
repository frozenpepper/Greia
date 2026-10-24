"""Receive one catalog-selected bundle through Greia's existing inbox contract."""

from __future__ import annotations

import hashlib
import http.client
import os
import time
from typing import Callable
from urllib.error import HTTPError, URLError

from greia_platform.system_updates import (
    InspectedUpdateBundle,
    SystemUpdateError,
    SystemUpdateInbox,
    UpdateManifest,
    inspect_update_bundle,
)

from greia_parent.update_catalog import (
    DeviceUpdateIdentity,
    UpdateCatalogClient,
    UpdateRelease,
)
from greia_parent.update_job_store import UpdateDeliveryError


CHUNK_BYTES = 256 * 1024
ProgressCallback = Callable[..., None]


class UpdateBundleReceiver:
    """Stream, checksum, inspect and atomically publish a selected update."""

    def __init__(self, inbox: SystemUpdateInbox, catalog: UpdateCatalogClient) -> None:
        self.inbox = inbox
        self.catalog = catalog

    def receive(
        self,
        release: UpdateRelease,
        identity: DeviceUpdateIdentity,
        progress: ProgressCallback,
    ) -> InspectedUpdateBundle:
        try:
            staging = self.inbox.create_receive_staging(release.size)
        except SystemUpdateError as exc:
            raise UpdateDeliveryError("Greia could not reserve enough space for the update") from exc
        progress("downloading", downloaded_bytes=0, total_bytes=release.size)
        digest = hashlib.sha256()
        received = 0
        last_persisted = 0
        last_progress_at = time.monotonic()
        try:
            response = self.catalog.open_bundle(release, timeout_seconds=30.0)
            with response, staging.open("wb") as output:
                status_code = getattr(response, "status", 200)
                if status_code != 200:
                    raise UpdateDeliveryError("Greia update server returned an unexpected response")
                content_length = response.headers.get("Content-Length")
                if content_length is not None and content_length != str(release.size):
                    raise UpdateDeliveryError("Greia update server returned an unexpected bundle size")
                while True:
                    chunk = response.read(CHUNK_BYTES)
                    if not chunk:
                        break
                    received += len(chunk)
                    if received > release.size:
                        raise UpdateDeliveryError("Greia update download exceeded its catalog size")
                    output.write(chunk)
                    digest.update(chunk)
                    now = time.monotonic()
                    if received - last_persisted >= 8 * 1024 * 1024 or now - last_progress_at >= 2.0:
                        progress("downloading", downloaded_bytes=received, total_bytes=release.size)
                        last_persisted = received
                        last_progress_at = now
                output.flush()
                os.fsync(output.fileno())
            if received != release.size:
                raise UpdateDeliveryError("Greia update download ended before the catalog size")
            if digest.hexdigest() != release.sha256:
                raise UpdateDeliveryError("Greia update checksum did not match the catalog")
            progress("receiving", downloaded_bytes=received, total_bytes=release.size)
            inspected = inspect_update_bundle(staging)
            _assert_release_matches_bundle(release, identity, inspected.manifest)
            received_bundle = self.inbox.receive_staged(staging)
            progress("verifying", downloaded_bytes=received, total_bytes=release.size)
            return received_bundle
        except UpdateDeliveryError:
            staging.unlink(missing_ok=True)
            raise
        except (OSError, HTTPError, URLError, TimeoutError, SystemUpdateError, http.client.HTTPException) as exc:
            staging.unlink(missing_ok=True)
            raise UpdateDeliveryError("Greia update download or bundle validation failed") from exc

    def candidate_matches(self, release: UpdateRelease, identity: DeviceUpdateIdentity) -> bool:
        """Check whether the fixed inbox candidate is the selected release."""

        try:
            path = self.inbox.candidate_path
            if not path.is_file() or path.stat().st_size != release.size:
                return False
            inspected = inspect_update_bundle(path)
            _assert_release_matches_bundle(release, identity, inspected.manifest)
            return _sha256_file(path) == release.sha256
        except (OSError, SystemUpdateError, UpdateDeliveryError):
            return False

    def discard_staged_candidate(
        self,
        release: UpdateRelease,
        identity: DeviceUpdateIdentity,
        recorded_sha256: str,
    ) -> bool:
        """Remove a leftover candidate only after matching its full identity and digest.

        Recovery may observe the durable staged journal after a crash that
        happened before the root service discarded its inbox bundle. The
        root-reported digest, inspected manifest, selected catalog release,
        device identity, and bytes on disk must all agree before cleanup.
        """

        try:
            path = self.inbox.candidate_path
            if not path.is_file() or path.stat().st_size != release.size:
                return False
            inspected = inspect_update_bundle(path)
            _assert_release_matches_bundle(release, identity, inspected.manifest)
            digest = _sha256_file(path)
            if digest != release.sha256 or recorded_sha256 != release.sha256:
                return False
            self.inbox.discard_candidate_after_stage(inspected, digest)
            return True
        except (OSError, SystemUpdateError, UpdateDeliveryError):
            return False


def _assert_release_matches_bundle(
    release: UpdateRelease,
    identity: DeviceUpdateIdentity,
    manifest: UpdateManifest,
) -> None:
    if (
        manifest.release_id != release.release_id
        or manifest.version != release.version
        or manifest.profile != identity.profile
        or manifest.platform_family != identity.platform_family
        or manifest.architecture != identity.architecture
        or manifest.board != release.board
        or (manifest.board is not None and manifest.board != identity.board)
    ):
        raise UpdateDeliveryError("downloaded Greia bundle does not match the selected catalog release")


def _sha256_file(path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
