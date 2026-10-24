"""Durable handoff shared by the unprivileged Parent and root updater.

The Parent owns only receipt and authorization. The installed bootstrap owns
inspection, compatibility, activation, restart and recovery. Both processes
coordinate through one bounded JSON record, one candidate file and one lock.
"""

from __future__ import annotations

import fcntl
import json
import os
import re
import shutil
import stat
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Mapping
from uuid import uuid4

from greia_platform.system_updates import MIN_INBOX_FREE_BYTES


SCHEMA_VERSION = 1
DEFAULT_SOFTWARE_UPDATE_DIRECTORY = Path("/var/lib/greia-os/software-updates")
DEFAULT_BOOTSTRAP_MARKER = Path("/etc/greia-os/software-update-bootstrap.json")
DEFAULT_BOOTSTRAP_HELPER = Path("/usr/local/lib/greia-os/software-update-bootstrap.py")
CANDIDATE_NAME = "candidate.greia_update"
JOB_NAME = "job.json"
PENDING_NAME = "pending"
LOCK_NAME = "job.lock"
RECEIVE_LOCK_NAME = "receive.lock"
MAX_JOB_FILE_BYTES = 64 * 1024
MAX_BOOTSTRAP_HELPER_BYTES = 1024 * 1024
MAX_STALE_UPLOADS_PER_RECEIVE = 16
MAX_SOFTWARE_UPDATE_DIRECTORY_ENTRIES = 4096
_UPLOAD_TEMP_RE = re.compile(r"^\.uploading\.[0-9a-f]{32}\.tmp$")

PACKAGE_TYPES = frozenset(
    {"python_platform", "activities", "combined", "full_system"}
)
STATES = frozenset(
    {
        "queued",
        "validating",
        "waiting_for_idle",
        "applying",
        "restarting",
        "applied",
        "rolled_back",
        "failed",
        "ready_to_restart",
    }
)
TERMINAL_STATES = frozenset({"applied", "rolled_back", "failed"})
BUSY_STATES = STATES - TERMINAL_STATES
_JOB_ID_RE = re.compile(r"^[0-9a-f]{32}$")
_PUBLIC_FIELDS = frozenset(
    {
        "job_id",
        "state",
        "created_at",
        "updated_at",
        "package_bytes",
        "received_bytes",
        "package_type",
        "version",
        "release_id",
        "error_code",
        "error_message",
        "activation_requested",
    }
)
_MUTABLE_FIELDS = frozenset(
    {
        "package_bytes",
        "received_bytes",
        "package_type",
        "version",
        "release_id",
        "error_code",
        "error_message",
        "activation_requested",
        "restart_requested",
        "previous_generation",
        "candidate_generation",
        "package_sha256",
        "member_sha256",
    }
)
_PRIVATE_FIELDS = frozenset(_MUTABLE_FIELDS - _PUBLIC_FIELDS)


class SoftwareUpdateJobError(RuntimeError):
    """A software update job cannot be safely accepted or reconciled."""


class SoftwareUpdateCapacityError(SoftwareUpdateJobError):
    """The upload would consume Greia's reserved Parent/data capacity."""


class SoftwareUpdateJobStore:
    """Persist the one authorized software update and its root-worker handoff.

    The directory is provisioned by the installed update bootstrap. This
    Parent-side store never creates it, so an old image cannot advertise
    software updates merely because the UI queried status.
    """

    def __init__(self, directory: Path = DEFAULT_SOFTWARE_UPDATE_DIRECTORY) -> None:
        self.directory = Path(directory)
        self.candidate_path = self.directory / CANDIDATE_NAME
        self.job_path = self.directory / JOB_NAME
        self.pending_path = self.directory / PENDING_NAME
        self.lock_path = self.directory / LOCK_NAME
        self._local_lock = threading.RLock()
        self._receive_local_lock = threading.Lock()

    @contextmanager
    def receive_lease(self) -> Iterator[None]:
        """Own the sole live receive and reap bounded crash leftovers safely.

        The process-shared flock is held from before stale-file inspection
        through the complete request body write. A second Parent process or
        request cannot mistake an active writer's temp file for crash debris.
        """

        if not self._receive_local_lock.acquire(blocking=False):
            raise SoftwareUpdateJobError("another software update upload is active")
        descriptor: int | None = None
        try:
            self._require_directory()
            descriptor = os.open(
                self.directory / RECEIVE_LOCK_NAME,
                os.O_RDWR | os.O_CREAT | _nofollow_flag() | getattr(os, "O_CLOEXEC", 0),
                0o660,
            )
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                raise SoftwareUpdateJobError("software update receive lock is invalid")
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise SoftwareUpdateJobError("another software update upload is active") from exc
            self._reap_stale_uploads_locked()
            self._reap_inactive_candidate_locked()
            yield
        except SoftwareUpdateJobError:
            raise
        except OSError as exc:
            raise SoftwareUpdateJobError("software update receive area is unavailable") from exc
        finally:
            if descriptor is not None:
                try:
                    fcntl.flock(descriptor, fcntl.LOCK_UN)
                finally:
                    os.close(descriptor)
            self._receive_local_lock.release()

    def require_receive_capacity(self, total_bytes: int) -> None:
        """Preflight package bytes while preserving the shared Parent reserve."""

        if isinstance(total_bytes, bool) or not isinstance(total_bytes, int) or total_bytes <= 0:
            raise SoftwareUpdateCapacityError("software update size is invalid")
        self._require_directory()
        try:
            free_bytes = shutil.disk_usage(self.directory).free
        except OSError as exc:
            raise SoftwareUpdateCapacityError("software update free space is unavailable") from exc
        if free_bytes < total_bytes + MIN_INBOX_FREE_BYTES:
            raise SoftwareUpdateCapacityError(
                "not enough free space to receive update while preserving the 256 MiB Greia reserve"
            )

    def _reap_stale_uploads_locked(self) -> None:
        """Remove only old receive temps while the exclusive receive flock is held."""

        candidates: list[Path] = []
        try:
            with os.scandir(self.directory) as entries:
                for index, entry in enumerate(entries, start=1):
                    if index > MAX_SOFTWARE_UPDATE_DIRECTORY_ENTRIES:
                        raise SoftwareUpdateJobError(
                            "software update directory exceeds its bounded receive scan"
                        )
                    if _UPLOAD_TEMP_RE.fullmatch(entry.name):
                        candidates.append(Path(entry.path))
                        if len(candidates) > MAX_STALE_UPLOADS_PER_RECEIVE:
                            break
            if len(candidates) > MAX_STALE_UPLOADS_PER_RECEIVE:
                raise SoftwareUpdateJobError(
                    "too many abandoned software update uploads to reap safely"
                )
            for candidate in candidates:
                try:
                    info = candidate.lstat()
                except FileNotFoundError:
                    continue
                if stat.S_ISREG(info.st_mode) and not stat.S_ISLNK(info.st_mode):
                    candidate.unlink()
        except SoftwareUpdateJobError:
            raise
        except OSError as exc:
            raise SoftwareUpdateJobError("could not reap abandoned software update uploads") from exc

    def _reap_inactive_candidate_locked(self) -> None:
        """Free a candidate left between atomic rename and durable job publish.

        The shared job lock makes the state decision atomic with root-worker
        progress. Active jobs and any still-pending handoff retain their exact
        candidate; a missing/terminal job with no pending marker has no current
        authorized package to protect.
        """

        try:
            with self._exclusive_lock():
                job = self._job_from_disk()
                if job is not None and job.get("state") in BUSY_STATES:
                    return
                try:
                    self.pending_path.lstat()
                    return
                except FileNotFoundError:
                    pass
                try:
                    info = self.candidate_path.lstat()
                except FileNotFoundError:
                    return
                if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
                    raise SoftwareUpdateJobError("orphan software update candidate is invalid")
                self.candidate_path.unlink()
                self._fsync_directory()
        except SoftwareUpdateJobError:
            raise
        except OSError as exc:
            raise SoftwareUpdateJobError("could not reap orphan software update candidate") from exc

    def snapshot(self) -> dict[str, object] | None:
        """Read a bounded public status snapshot without creating state."""

        job = self._read_job()
        return _public_job(job) if job is not None else None

    def read_internal(self) -> dict[str, object] | None:
        """Read the complete shared record for the root bootstrap worker."""

        return self._read_job()

    def is_busy(self) -> bool:
        job = self._read_job()
        return job is not None and job.get("state") in BUSY_STATES

    def accept_received(
        self, staging_file: Path, total_bytes: int
    ) -> dict[str, object]:
        """Durably publish an authorized upload before returning HTTP 202.

        `staging_file` must already be a complete, exclusively created file in
        the bootstrap-provisioned directory. The caller fsyncs its stream;
        this method fsyncs it again, atomically names it as the fixed candidate,
        writes the authorized job, and creates `pending` last.
        """

        if isinstance(total_bytes, bool) or not isinstance(total_bytes, int) or total_bytes <= 0:
            raise SoftwareUpdateJobError("software update size is invalid")
        source = Path(staging_file)
        if source.parent != self.directory:
            raise SoftwareUpdateJobError("software update staging path is invalid")
        try:
            with self._exclusive_lock():
                self._require_directory()
                info = source.lstat()
                if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
                    raise SoftwareUpdateJobError("software update staging file is invalid")
                if info.st_size != total_bytes:
                    raise SoftwareUpdateJobError("software update size did not match Content-Length")
                existing = self._job_from_disk()
                if existing is not None and existing.get("state") in BUSY_STATES:
                    raise SoftwareUpdateJobError("another software update job is active")

                descriptor = os.open(source, os.O_RDONLY | _nofollow_flag())
                try:
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
                os.replace(source, self.candidate_path)
                self._fsync_directory()

                now = _timestamp()
                job: dict[str, object] = {
                    "job_id": uuid4().hex,
                    "state": "queued",
                    "created_at": now,
                    "updated_at": now,
                    "package_bytes": total_bytes,
                    "received_bytes": total_bytes,
                    "package_type": None,
                    "version": None,
                    "release_id": None,
                    "error_code": None,
                    "error_message": None,
                    "activation_requested": True,
                }
                self._write_job_locked(job)
                self._write_pending_locked(job["job_id"])
                return _public_job(job)
        except SoftwareUpdateJobError:
            raise
        except OSError as exc:
            raise SoftwareUpdateJobError("could not durably queue software update") from exc

    def update(self, job_id: str, state: str, **fields: object) -> dict[str, object]:
        """Atomically update progress/outcome under the shared process lock."""

        if state not in STATES:
            raise SoftwareUpdateJobError("software update state is invalid")
        unknown = set(fields) - _MUTABLE_FIELDS
        if unknown:
            raise SoftwareUpdateJobError("software update job field is unsupported")
        with self._exclusive_lock():
            job = self._job_from_disk()
            if job is None or job.get("job_id") != job_id:
                raise SoftwareUpdateJobError("software update job changed")
            if job.get("state") in TERMINAL_STATES:
                raise SoftwareUpdateJobError("software update job is already complete")
            updated = dict(job)
            updated.update(fields)
            updated["state"] = state
            updated["updated_at"] = _timestamp()
            _validate_job(updated)
            self._write_job_locked(updated)
            if state in TERMINAL_STATES | {"ready_to_restart"}:
                self._remove_pending_locked()
            elif state in BUSY_STATES:
                self._write_pending_locked(job_id)
            return _public_job(updated)

    def request_restart(self) -> dict[str, object]:
        """Durably authorize the explicit restart for a staged full-system job."""

        with self._exclusive_lock():
            job = self._job_from_disk()
            if (
                job is None
                or job.get("state") != "ready_to_restart"
                or job.get("package_type") != "full_system"
            ):
                raise SoftwareUpdateJobError("no full-system software update is ready to restart")
            if job.get("restart_requested") is True:
                return _public_job(job)
            updated = dict(job)
            updated["restart_requested"] = True
            updated["updated_at"] = _timestamp()
            _validate_job(updated)
            self._write_job_locked(updated)
            self._write_pending_locked(str(job["job_id"]))
            return _public_job(updated)

    @contextmanager
    def _exclusive_lock(self) -> Iterator[None]:
        with self._local_lock:
            self._require_directory()
            descriptor = os.open(
                self.lock_path,
                os.O_RDWR | os.O_CREAT | _nofollow_flag() | getattr(os, "O_CLOEXEC", 0),
                0o660,
            )
            try:
                if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                    raise SoftwareUpdateJobError("software update job lock is invalid")
                fcntl.flock(descriptor, fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    fcntl.flock(descriptor, fcntl.LOCK_UN)
            finally:
                os.close(descriptor)

    def _read_job(self) -> dict[str, object] | None:
        try:
            self.directory.lstat()
        except FileNotFoundError:
            return None
        try:
            with self._exclusive_lock():
                return self._job_from_disk()
        except FileNotFoundError:
            return None

    def _job_from_disk(self) -> dict[str, object] | None:
        try:
            info = self.job_path.lstat()
        except FileNotFoundError:
            return None
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode) or info.st_size > MAX_JOB_FILE_BYTES:
            raise SoftwareUpdateJobError("software update job record is invalid")
        try:
            document = json.loads(self.job_path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SoftwareUpdateJobError("software update job record is invalid") from exc
        if (
            not isinstance(document, dict)
            or document.get("schema_version") != SCHEMA_VERSION
            or not isinstance(document.get("job"), dict)
        ):
            raise SoftwareUpdateJobError("software update job record schema is invalid")
        job = dict(document["job"])
        _validate_job(job)
        return job

    def _write_job_locked(self, job: Mapping[str, object]) -> None:
        _validate_job(dict(job))
        document = {"schema_version": SCHEMA_VERSION, "job": dict(job)}
        raw = json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        if len(raw) > MAX_JOB_FILE_BYTES:
            raise SoftwareUpdateJobError("software update job record exceeds its bound")
        temporary = self.directory / f".job.{uuid4().hex}.tmp"
        descriptor = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | _nofollow_flag() | getattr(os, "O_CLOEXEC", 0),
            0o660,
        )
        try:
            os.fchmod(descriptor, 0o660)
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.job_path)
            self._fsync_directory()
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise

    def _write_pending_locked(self, job_id: str) -> None:
        temporary = self.directory / f".pending.{uuid4().hex}.tmp"
        descriptor = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | _nofollow_flag() | getattr(os, "O_CLOEXEC", 0),
            0o660,
        )
        try:
            os.fchmod(descriptor, 0o660)
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(f"{job_id}\n".encode("ascii"))
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.pending_path)
            self._fsync_directory()
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise

    def _remove_pending_locked(self) -> None:
        self.pending_path.unlink(missing_ok=True)
        self._fsync_directory()

    def _require_directory(self) -> None:
        try:
            info = self.directory.lstat()
        except FileNotFoundError as exc:
            raise SoftwareUpdateJobError("software update bootstrap is unavailable") from exc
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise SoftwareUpdateJobError("software update state directory is invalid")

    def _fsync_directory(self) -> None:
        descriptor = os.open(self.directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | _nofollow_flag())
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def _public_job(job: Mapping[str, object]) -> dict[str, object]:
    public = {key: value for key, value in job.items() if key in _PUBLIC_FIELDS}
    public["restart_available"] = (
        job.get("state") == "ready_to_restart"
        and job.get("package_type") == "full_system"
        and job.get("restart_requested") is not True
    )
    return public


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _nofollow_flag() -> int:
    return getattr(os, "O_NOFOLLOW", 0)


def _validate_job(job: dict[str, object]) -> None:
    job_id = job.get("job_id")
    if not isinstance(job_id, str) or not _JOB_ID_RE.fullmatch(job_id):
        raise SoftwareUpdateJobError("software update job id is invalid")
    if job.get("state") not in STATES:
        raise SoftwareUpdateJobError("software update job state is invalid")
    if not isinstance(job.get("created_at"), str) or not isinstance(job.get("updated_at"), str):
        raise SoftwareUpdateJobError("software update job timestamps are invalid")
    package_bytes = job.get("package_bytes")
    received_bytes = job.get("received_bytes")
    if (
        isinstance(package_bytes, bool)
        or not isinstance(package_bytes, int)
        or package_bytes <= 0
        or isinstance(received_bytes, bool)
        or not isinstance(received_bytes, int)
        or received_bytes < 0
        or received_bytes > package_bytes
    ):
        raise SoftwareUpdateJobError("software update job byte counts are invalid")
    package_type = job.get("package_type")
    if package_type is not None and package_type not in PACKAGE_TYPES:
        raise SoftwareUpdateJobError("software update package type is invalid")
    for key, maximum in (("version", 64), ("release_id", 96)):
        value = job.get(key)
        if value is not None and (not isinstance(value, str) or len(value) > maximum):
            raise SoftwareUpdateJobError(f"software update job {key} is invalid")
    for key, maximum in (("error_code", 64), ("error_message", 256)):
        value = job.get(key)
        if value is not None and (not isinstance(value, str) or len(value) > maximum):
            raise SoftwareUpdateJobError(f"software update job {key} is invalid")
    if job.get("activation_requested") is not True:
        raise SoftwareUpdateJobError("software update activation authorization is missing")
    restart_requested = job.get("restart_requested", False)
    if restart_requested is not True and restart_requested is not False:
        raise SoftwareUpdateJobError("software update restart authorization is invalid")
    if job.get("state") == "ready_to_restart" and package_type != "full_system":
        raise SoftwareUpdateJobError("only a full-system update can wait for restart")
    for key in _PRIVATE_FIELDS - {"restart_requested"}:
        value = job.get(key)
        if value is not None and (not isinstance(value, str) or len(value) > 128):
            raise SoftwareUpdateJobError(f"software update job {key} is invalid")


def software_update_bootstrap_available(
    marker_path: Path = DEFAULT_BOOTSTRAP_MARKER,
    helper_path: Path = DEFAULT_BOOTSTRAP_HELPER,
) -> bool:
    """Require the installed v1 bootstrap marker and stable root helper."""

    try:
        marker_bytes = _read_regular_file(marker_path, 4096)
        helper_bytes = _read_regular_file(helper_path, MAX_BOOTSTRAP_HELPER_BYTES)
        document = json.loads(marker_bytes.decode("utf-8"))
        helper_source = helper_bytes.decode("utf-8")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, SoftwareUpdateJobError):
        return False
    return (
        isinstance(document, dict)
        and set(document) == {"schema_version"}
        and document.get("schema_version") == SCHEMA_VERSION
        and re.search(r"(?m)^BOOTSTRAP_VERSION\s*=\s*1\s*$", helper_source) is not None
    )


def _read_regular_file(path: Path, maximum: int) -> bytes:
    descriptor = os.open(
        path,
        os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | _nofollow_flag(),
    )
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_size > maximum:
            raise SoftwareUpdateJobError("software update bootstrap file is invalid")
        chunks: list[bytes] = []
        remaining = maximum + 1
        while remaining:
            chunk = os.read(descriptor, min(remaining, 64 * 1024))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        content = b"".join(chunks)
        if len(content) > maximum:
            raise SoftwareUpdateJobError("software update bootstrap file exceeds its bound")
        return content
    finally:
        os.close(descriptor)
