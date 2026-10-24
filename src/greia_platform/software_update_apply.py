"""Prepare typed ``.greia_update`` packages for the stable root bootstrap.

This module is imported only by the root-owned bootstrap after its marker and
recovery journal have been checked. Application generations, Parent Activity
sets and full-system slot writes remain delegated to their existing owners.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import stat
import zipfile
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .activity_packages import (
    ActivityArchiveUpdate,
    ActivityPackageService,
    ActivityUpdateGeneration,
)
from .profiles import ActiveProfileSession
from .software_update_generation import (
    ApplicationGenerationBuilder,
    GenerationLayout,
    StagedApplicationGeneration,
)
from .software_update_package import (
    MAX_ACTIVITY_ENTRIES,
    MAX_ACTIVITY_PACKAGE_BYTES,
    InspectedSoftwareUpdatePackage,
    SoftwareUpdatePackageError,
    SoftwareUpdateType,
    inspect_software_update_package,
)


class SoftwareUpdateApplyError(RuntimeError):
    """A durable package cannot be prepared by this installed system."""


@dataclass(slots=True)
class PreparedSoftwareUpdate:
    """Prepared update facts and the owner that publishes its generation."""

    kind: str
    job_id: str
    package_type: str
    version: str
    release_id: str
    package_sha256: str
    package_size: int
    profile_session: ActiveProfileSession | None = None
    application_generation: StagedApplicationGeneration | None = None
    activity_service: ActivityPackageService | None = None
    parent_generation: ActivityUpdateGeneration | None = None

    @property
    def previous_generation(self) -> str:
        if self.application_generation is not None:
            return self.application_generation.previous_generation_id
        if self.parent_generation is not None:
            return self.parent_generation.previous_generation
        return ""

    @property
    def candidate_generation(self) -> str:
        if self.application_generation is not None:
            return self.application_generation.generation_id
        if self.parent_generation is not None:
            return self.parent_generation.candidate_generation
        return ""

    def publish_parent_generation(self) -> None:
        if self.activity_service is None or self.parent_generation is None:
            raise SoftwareUpdateApplyError("Parent Activity update plan is incomplete")
        self.activity_service.publish_software_update_generation(self.parent_generation)

    def rollback_parent_generation(self) -> None:
        if self.activity_service is None or self.parent_generation is None:
            raise SoftwareUpdateApplyError("Parent Activity update plan is incomplete")
        self.activity_service.restore_software_update_generation(
            self.parent_generation.previous_generation
        )

    def commit_parent_generation(self) -> None:
        if self.activity_service is None or self.parent_generation is None:
            raise SoftwareUpdateApplyError("Parent Activity update plan is incomplete")
        self.activity_service.commit_software_update_generation(self.parent_generation)


def prepare_software_update(
    job: Mapping[str, object],
    paths: object,
    *,
    generation_layout: GenerationLayout | None = None,
    activity_service: ActivityPackageService | None = None,
) -> PreparedSoftwareUpdate:
    """Inspect the accepted candidate and stage it through its owning service."""

    job_id = _required_job_id(job)
    candidate = Path(getattr(paths, "software_update_root")) / "candidate.greia_update"
    try:
        candidate_info = candidate.lstat()
    except OSError as exc:
        raise SoftwareUpdateApplyError("accepted software-update package is missing") from exc
    if not stat.S_ISREG(candidate_info.st_mode) or stat.S_ISLNK(candidate_info.st_mode):
        raise SoftwareUpdateApplyError("accepted software-update package is not a regular file")
    expected_bytes = job.get("package_bytes")
    received_bytes = job.get("received_bytes")
    if (
        isinstance(expected_bytes, bool)
        or not isinstance(expected_bytes, int)
        or expected_bytes <= 0
        or expected_bytes != candidate_info.st_size
        or received_bytes != expected_bytes
    ):
        raise SoftwareUpdateApplyError("accepted software-update byte count is inconsistent")
    try:
        inspected = inspect_software_update_package(candidate)
    except (SoftwareUpdatePackageError, OSError, zipfile.BadZipFile) as exc:
        raise SoftwareUpdateApplyError(str(exc)) from exc
    prior_digest = job.get("package_sha256")
    if prior_digest is not None and prior_digest != inspected.package_sha256:
        raise SoftwareUpdateApplyError("accepted software-update package changed after receipt")
    prior_type = job.get("package_type")
    if prior_type is not None and prior_type != inspected.manifest.type.value:
        raise SoftwareUpdateApplyError("accepted software-update type changed after receipt")

    if inspected.manifest.type is SoftwareUpdateType.FULL_SYSTEM:
        _stage_full_system(candidate, inspected)
        return PreparedSoftwareUpdate(
            kind="full_system",
            job_id=job_id,
            package_type=inspected.manifest.type.value,
            version=inspected.manifest.version,
            release_id=inspected.manifest.release_id,
            package_sha256=inspected.package_sha256,
            package_size=inspected.package_size,
        )

    _require_target_compatibility(inspected)
    if (
        inspected.manifest.type is SoftwareUpdateType.ACTIVITIES
        and inspected.manifest.activity_source is not None
        and inspected.manifest.activity_source.value == "parent"
    ):
        service = activity_service or ActivityPackageService.from_environment()
        generation = _stage_parent_activity_update(candidate, inspected, service)
        session = ActiveProfileSession(
            Path(getattr(paths, "active_profile")),
            lock_path=Path(getattr(paths, "active_profile_lock")),
            restart_fence_path=Path(getattr(paths, "restart_fence")),
        )
        return PreparedSoftwareUpdate(
            kind="parent_activities",
            job_id=job_id,
            package_type=inspected.manifest.type.value,
            version=inspected.manifest.version,
            release_id=inspected.manifest.release_id,
            package_sha256=inspected.package_sha256,
            package_size=inspected.package_size,
            profile_session=session,
            activity_service=service,
            parent_generation=generation,
        )

    builder = ApplicationGenerationBuilder(generation_layout or GenerationLayout())
    generation = builder.stage(candidate, inspected, job_id=job_id)
    service = activity_service or ActivityPackageService.from_environment()
    session = ActiveProfileSession(
        Path(getattr(paths, "active_profile")),
        lock_path=Path(getattr(paths, "active_profile_lock")),
        restart_fence_path=Path(getattr(paths, "restart_fence")),
    )
    return PreparedSoftwareUpdate(
        kind="application_generation",
        job_id=job_id,
        package_type=inspected.manifest.type.value,
        version=inspected.manifest.version,
        release_id=inspected.manifest.release_id,
        package_sha256=inspected.package_sha256,
        package_size=inspected.package_size,
        profile_session=session,
        activity_service=service,
        application_generation=generation,
    )


def _stage_parent_activity_update(
    candidate: Path,
    inspected: InspectedSoftwareUpdatePackage,
    service: ActivityPackageService,
) -> ActivityUpdateGeneration:
    manifest = inspected.manifest
    if manifest.activity_items == () or manifest.activity_source is None:
        raise SoftwareUpdateApplyError("Parent Activity update package is empty")
    with zipfile.ZipFile(candidate, "r", allowZip64=True) as outer, ExitStack() as stack:
        updates: list[ActivityArchiveUpdate] = []
        for item in manifest.activity_items:
            if item.size > MAX_ACTIVITY_PACKAGE_BYTES:
                raise SoftwareUpdateApplyError("Parent Activity package exceeds its bound")
            nested_stream = stack.enter_context(outer.open(item.member, "r"))
            nested_archive = stack.enter_context(
                zipfile.ZipFile(nested_stream, "r", allowZip64=False)
            )
            updates.append(
                ActivityArchiveUpdate(item.activity_id, item.version, nested_archive)
            )
        with service.software_update_lock():
            return service.stage_software_update_generation(
                updates, max_entries=MAX_ACTIVITY_ENTRIES
            )


def _stage_full_system(
    candidate: Path, inspected: InspectedSoftwareUpdatePackage
) -> None:
    descriptor = inspected.manifest.full_system
    if descriptor is None:
        raise SoftwareUpdateApplyError("full-system package has no v3 bundle")
    from .system_updates import (
        SystemUpdateInbox,
        build_live_update_service,
        sha256_file,
    )

    inbox = SystemUpdateInbox(Path("/var/lib/greia-os"))
    staging = inbox.create_receive_staging(descriptor.size)
    digest = hashlib.sha256()
    total = 0
    try:
        with zipfile.ZipFile(candidate, "r", allowZip64=True) as outer:
            with outer.open(descriptor.member, "r") as source, staging.open("wb") as sink:
                while True:
                    block = source.read(1024 * 1024)
                    if not block:
                        break
                    total += len(block)
                    if total > descriptor.size:
                        raise SoftwareUpdateApplyError(
                            "nested full-system bundle exceeds its declared size"
                        )
                    digest.update(block)
                    sink.write(block)
                sink.flush()
                os.fsync(sink.fileno())
        if total != descriptor.size or digest.hexdigest() != descriptor.sha256:
            raise SoftwareUpdateApplyError(
                "nested full-system bundle does not match its package digest"
            )
        received = inbox.receive_staged(staging)
        authority = build_live_update_service()
        staged = authority.service.stage(received.path)
        if (
            staged.manifest.release_id != inspected.manifest.release_id
            or staged.manifest.version != inspected.manifest.version
        ):
            raise SoftwareUpdateApplyError(
                "staged v3 identity differs from the software-update package"
            )
    except BaseException:
        staging.unlink(missing_ok=True)
        raise
    if inbox.candidate_path.exists():
        raise SoftwareUpdateApplyError(
            "existing system-update service did not consume its staged candidate"
        )
    if sha256_file(candidate) != inspected.package_sha256:
        raise SoftwareUpdateApplyError("software-update package changed during staging")
    candidate.unlink(missing_ok=True)


def _require_target_compatibility(
    inspected: InspectedSoftwareUpdatePackage,
) -> None:
    targets = inspected.manifest.targets
    if not targets:
        return
    from .update_client import UpdatePrivilegedClient

    status = UpdatePrivilegedClient().request("STATUS")
    identity = status.get("identity")
    if status.get("status") != "OK" or not isinstance(identity, dict):
        raise SoftwareUpdateApplyError(
            "installed Greia identity is unavailable for package compatibility"
        )
    if not any(target.matches(identity) for target in targets):
        raise SoftwareUpdateApplyError(
            "software-update package does not target this Greia installation"
        )


def _required_job_id(job: Mapping[str, object]) -> str:
    value = job.get("job_id")
    if (
        not isinstance(value, str)
        or len(value) != 32
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise SoftwareUpdateApplyError("software update job identity is invalid")
    return value


__all__ = [
    "PreparedSoftwareUpdate",
    "SoftwareUpdateApplyError",
    "prepare_software_update",
]
