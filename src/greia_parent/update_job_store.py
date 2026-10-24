"""Small durable store for the single unprivileged update delivery job."""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Mapping
from uuid import uuid4


JOB_SCHEMA = 1
JOB_FILE_NAME = "delivery.json"
# The bounded catalog can contain 32 rows with four localized notes each.
MAX_JOB_FILE_BYTES = 640 * 1024
ACTIVE_STATES = frozenset(
    {"checking", "queued", "downloading", "receiving", "verifying", "staging"}
)
READY_STATES = frozenset({"ready_to_restart", "restart_pending"})
TERMINAL_STATES = frozenset({"checked", "updated", "rolled_back", "failed"})


class UpdateDeliveryError(RuntimeError):
    """A Parent update operation cannot safely be accepted or continued."""


class UpdateJobStore:
    """Atomically persist one bounded job, readiness snapshot and catalog."""

    def __init__(self, state_dir: Path) -> None:
        self.directory = Path(state_dir) / "system-updates"
        self.path = self.directory / JOB_FILE_NAME
        self._lock = threading.RLock()
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.directory.is_symlink() or not self.directory.is_dir():
            raise UpdateDeliveryError("system update state directory is invalid")
        try:
            self._state = self._read()
        except FileNotFoundError:
            self._state = self._empty()

    @staticmethod
    def _empty() -> dict[str, object]:
        return {"schema": JOB_SCHEMA, "job": None, "readiness": None, "last_check": None}

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            return json.loads(json.dumps(self._state))

    def replace(self, state: Mapping[str, object]) -> None:
        with self._lock:
            candidate = dict(state)
            candidate["schema"] = JOB_SCHEMA
            self._write(candidate)
            self._state = candidate

    def update_job(self, job: Mapping[str, object] | None) -> None:
        with self._lock:
            candidate = dict(self._state)
            candidate["job"] = dict(job) if job is not None else None
            self._write(candidate)
            self._state = candidate

    def update_readiness(self, readiness: Mapping[str, object]) -> None:
        with self._lock:
            candidate = dict(self._state)
            candidate["readiness"] = dict(readiness)
            self._write(candidate)
            self._state = candidate

    def update_check(self, value: Mapping[str, object]) -> None:
        with self._lock:
            candidate = dict(self._state)
            candidate["last_check"] = dict(value)
            self._write(candidate)
            self._state = candidate

    def _read(self) -> dict[str, object]:
        info = self.path.lstat()
        if self.path.is_symlink() or not self.path.is_file() or info.st_size > MAX_JOB_FILE_BYTES:
            raise UpdateDeliveryError("system update job state is invalid")
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise UpdateDeliveryError("system update job state is invalid") from exc
        if not isinstance(raw, dict) or raw.get("schema") != JOB_SCHEMA:
            raise UpdateDeliveryError("system update job state schema is invalid")
        job = raw.get("job")
        if job is not None and not _valid_job(job):
            raise UpdateDeliveryError("system update job record is invalid")
        readiness = raw.get("readiness")
        last_check = raw.get("last_check")
        if readiness is not None and not isinstance(readiness, dict):
            raise UpdateDeliveryError("system update readiness record is invalid")
        if last_check is not None and not _valid_check(last_check):
            raise UpdateDeliveryError("system update catalog record is invalid")
        return {
            "schema": JOB_SCHEMA,
            "job": job,
            "readiness": readiness,
            "last_check": last_check,
        }

    def _write(self, value: Mapping[str, object]) -> None:
        raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        if len(raw) > MAX_JOB_FILE_BYTES:
            raise UpdateDeliveryError("system update job state exceeds its bound")
        temporary = self.directory / f".{JOB_FILE_NAME}.{uuid4().hex}.tmp"
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
            directory_fd = os.open(self.directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise


def _valid_job(value: object) -> bool:
    return (
        isinstance(value, dict)
        and isinstance(value.get("job_id"), str)
        and len(value["job_id"]) == 32
        and value.get("operation") in {"check", "prepare", "restart"}
        and value.get("state") in ACTIVE_STATES | READY_STATES | TERMINAL_STATES
        and isinstance(value.get("created_at"), str)
        and isinstance(value.get("updated_at"), str)
    )


def _valid_check(value: object) -> bool:
    if not isinstance(value, dict) or value.get("channel") not in {"stable", "dev"}:
        return False
    releases = value.get("releases")
    return (
        isinstance(value.get("checked_at"), str)
        and isinstance(releases, list)
        and len(releases) <= 32
        and all(isinstance(item, dict) for item in releases)
    )
