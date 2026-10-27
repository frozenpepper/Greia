#!/usr/bin/python3
"""Stable root apply/recovery entrypoint for Greia application generations.

This file intentionally uses only the Python standard library until recovery
has completed.  It lives outside ``/opt/greia-os`` so a package that replaces
Parent, launcher, or platform code cannot replace the code that repairs its
own interrupted generation switch.
"""

from __future__ import annotations

import argparse
import fcntl
import http.client
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping


BOOTSTRAP_VERSION = 1
MARKER_PATH = Path("/etc/greia-os/software-update-bootstrap.json")
HELPER_PATH = Path("/usr/local/lib/greia-os/software-update-bootstrap.py")
APP_ROOT = Path("/opt/greia-os")
GENERATION_ROOT = Path("/opt/greia-software/generations")
STATE_ROOT = Path("/var/lib/greia-os/software-updates")
JOB_PATH = STATE_ROOT / "job.json"
JOB_LOCK_PATH = STATE_ROOT / "job.lock"
PENDING_PATH = STATE_ROOT / "pending"
JOURNAL_PATH = STATE_ROOT / "apply-journal.json"
ACTIVE_PROFILE_PATH = Path("/run/greia-os/active-profile.json")
ROOT_FILESYSTEM_UUID_PATH = Path("/etc/greia-os/root-filesystem-uuid")
LAYOUT_RECORD_PATH = Path("/etc/greia-os/layout/installed-layout.json")
PROC_CMDLINE_PATH = Path("/proc/cmdline")
ACTIVE_PROFILE_LOCK = Path("/run/greia-update-authority/profile-session.lock")
RESTART_FENCE_PATH = Path("/run/greia-update-authority/restart-pending.json")
BOOT_MARKER_SPOOL = Path("/run/greia-os/boot-markers.log")
BUILTIN_INDEX = Path("/usr/share/greia/activity-index-v1.json")
SOFTWARE_UPDATE_DIR = Path("/var/lib/greia-os/software-updates")
MAX_SMALL_JSON_BYTES = 64 * 1024
MAX_JOB_JSON_BYTES = 1024 * 1024
MAX_JOURNAL_BYTES = 32 * 1024
GENERATION_ID_RE = re.compile(r"^(?:base|app-[0-9a-f]{32}|bootstrap-[0-9a-f]{32})$")
JOB_ID_RE = re.compile(r"^[0-9a-f]{32}$")
ROOT_UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
ACTIVE_JOB_STATES = frozenset(
    {"queued", "validating", "waiting_for_idle", "applying", "restarting"}
)
TERMINAL_JOB_STATES = frozenset({"applied", "rolled_back", "failed"})


class BootstrapError(RuntimeError):
    """The installed update bootstrap cannot safely continue or recover."""


@dataclass(frozen=True, slots=True)
class BootstrapPaths:
    """Injectable filesystem paths for source-level bootstrap tests."""

    marker: Path = MARKER_PATH
    helper: Path = HELPER_PATH
    application_root: Path = APP_ROOT
    generation_root: Path = GENERATION_ROOT
    software_update_root: Path = SOFTWARE_UPDATE_DIR
    candidate: Path = SOFTWARE_UPDATE_DIR / "candidate.greia_update"
    job: Path = JOB_PATH
    job_lock: Path = JOB_LOCK_PATH
    pending: Path = PENDING_PATH
    journal: Path = JOURNAL_PATH
    active_profile: Path = ACTIVE_PROFILE_PATH
    root_filesystem_uuid: Path = ROOT_FILESYSTEM_UUID_PATH
    layout_record: Path = LAYOUT_RECORD_PATH
    proc_cmdline: Path = PROC_CMDLINE_PATH
    active_profile_lock: Path = ACTIVE_PROFILE_LOCK
    restart_fence: Path = RESTART_FENCE_PATH
    boot_marker_spool: Path = BOOT_MARKER_SPOOL
    builtin_index: Path = BUILTIN_INDEX


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _atomic_write_json(path: Path, payload: Mapping[str, object], *, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    encoded = (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")
    descriptor = os.open(
        temporary,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
        mode,
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def _read_regular_json(path: Path, maximum: int) -> dict[str, object]:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise BootstrapError(f"required update state is unavailable: {path.name}") from exc
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_size > maximum:
            raise BootstrapError(f"update state is invalid: {path.name}")
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = -1
            raw = handle.read(maximum + 1)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if len(raw) > maximum:
        raise BootstrapError(f"update state exceeds its bound: {path.name}")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BootstrapError(f"update state is malformed: {path.name}") from exc
    if not isinstance(value, dict):
        raise BootstrapError(f"update state is invalid: {path.name}")
    return value


def _ready(paths: BootstrapPaths) -> None:
    marker = _read_regular_json(paths.marker, MAX_SMALL_JSON_BYTES)
    if set(marker) != {"schema_version"} or marker.get("schema_version") != 1:
        raise BootstrapError("software update bootstrap marker is unsupported")
    try:
        helper_info = paths.helper.lstat()
    except OSError as exc:
        raise BootstrapError("stable software update bootstrap helper is missing") from exc
    if not stat.S_ISREG(helper_info.st_mode) or not helper_info.st_mode & 0o111:
        raise BootstrapError("stable software update bootstrap helper is invalid")


def _generation_target(paths: BootstrapPaths, generation_id: str) -> Path:
    if not GENERATION_ID_RE.fullmatch(generation_id):
        raise BootstrapError("application generation id is invalid")
    target = paths.generation_root / generation_id
    try:
        info = target.lstat()
    except OSError as exc:
        raise BootstrapError("application generation is missing") from exc
    if not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode):
        raise BootstrapError("application generation is not a real directory")
    return target


def current_generation_id(paths: BootstrapPaths) -> str:
    """Read the generation id from the one stable ``/opt/greia-os`` link."""

    try:
        info = paths.application_root.lstat()
    except OSError as exc:
        raise BootstrapError("installed application root is missing") from exc
    if not stat.S_ISLNK(info.st_mode):
        raise BootstrapError("installed application root is not generation-backed")
    resolved = paths.application_root.resolve(strict=True)
    generations = paths.generation_root.resolve(strict=True)
    try:
        resolved.relative_to(generations)
    except ValueError as exc:
        raise BootstrapError("application root points outside its generation store") from exc
    generation_id = resolved.name
    _generation_target(paths, generation_id)
    return generation_id


def switch_generation(paths: BootstrapPaths, generation_id: str) -> None:
    """Atomically replace the single app-root symlink and sync its parent."""

    target = _generation_target(paths, generation_id)
    paths.application_root.parent.mkdir(parents=True, exist_ok=True)
    temporary = paths.application_root.with_name(
        f".{paths.application_root.name}.next-{uuid.uuid4().hex}"
    )
    try:
        relative_target = os.path.relpath(target, paths.application_root.parent)
        os.symlink(relative_target, temporary)
        os.replace(temporary, paths.application_root)
        _fsync_directory(paths.application_root.parent)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def _write_journal(paths: BootstrapPaths, payload: Mapping[str, object]) -> None:
    if payload.get("schema_version") != 1:
        raise BootstrapError("software update journal schema is invalid")
    durable = dict(payload)
    if durable.get("phase") in {
        "migration_started",
        "switching",
        "trial",
        "committed",
    }:
        durable["base_root_uuid"] = _current_root_uuid(paths)
    encoded = json.dumps(
        durable, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    if len(encoded) > MAX_JOURNAL_BYTES:
        raise BootstrapError("software update journal exceeds its bound")
    _atomic_write_json(paths.journal, durable, mode=0o600)


def _current_root_uuid(paths: BootstrapPaths) -> str:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(paths.root_filesystem_uuid, flags)
    except FileNotFoundError:
        return _current_ab_slot_root_uuid(paths)
    except OSError as exc:
        raise BootstrapError("installed root filesystem identity is unavailable") from exc
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_size > 64:
            raise BootstrapError("installed root filesystem identity is invalid")
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = -1
            raw = handle.read(65)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    try:
        value = raw.decode("ascii").strip()
    except UnicodeDecodeError as exc:
        raise BootstrapError("installed root filesystem identity is invalid") from exc
    if not ROOT_UUID_RE.fullmatch(value):
        raise BootstrapError("installed root filesystem identity is invalid")
    try:
        canonical = str(uuid.UUID(value))
    except ValueError as exc:
        raise BootstrapError("installed root filesystem identity is invalid") from exc
    if canonical != value.lower():
        raise BootstrapError("installed root filesystem identity is invalid")
    return canonical


def _current_ab_slot_root_uuid(paths: BootstrapPaths) -> str:
    """Resolve the booted A/B slot's filesystem UUID from the layout record.

    Single-root builds carry ``/etc/greia-os/root-filesystem-uuid``. A/B
    images do not: their root identity is the booted slot's filesystem UUID
    from installed-layout authority. Match the kernel ``root=PARTUUID=``
    command line against the record so a candidate boot is bound to its own
    slot even while the accepted slot is still the other one.
    """
    try:
        layout = _read_regular_json(paths.layout_record, MAX_SMALL_JSON_BYTES)
    except BootstrapError as exc:
        raise BootstrapError("installed root filesystem identity is unavailable") from exc
    if layout.get("schema_version") != 1:
        raise BootstrapError("installed root filesystem identity is invalid")
    try:
        cmdline = Path(paths.proc_cmdline).read_text(encoding="ascii", errors="strict")
    except (OSError, UnicodeDecodeError) as exc:
        raise BootstrapError("installed root filesystem identity is unavailable") from exc
    if len(cmdline) > 64 * 1024:
        raise BootstrapError("installed root filesystem identity is invalid")
    root_tokens = [
        token[len("root=PARTUUID="):]
        for token in cmdline.split()
        if token.startswith("root=PARTUUID=")
    ]
    if len(root_tokens) != 1 or not root_tokens[0]:
        raise BootstrapError("installed root filesystem identity is unavailable")
    booted_partuuid = root_tokens[0].lower()
    matches = []
    for slot in ("system_a", "system_b"):
        identity = layout.get(slot)
        if not isinstance(identity, dict):
            continue
        partuuid = identity.get("partuuid")
        filesystem_uuid = identity.get("filesystem_uuid")
        if not isinstance(partuuid, str) or not isinstance(filesystem_uuid, str):
            continue
        if partuuid.lower() != booted_partuuid:
            continue
        matches.append(filesystem_uuid)
    if len(matches) != 1 or not ROOT_UUID_RE.fullmatch(matches[0]):
        raise BootstrapError("installed root filesystem identity is invalid")
    try:
        canonical = str(uuid.UUID(matches[0]))
    except ValueError as exc:
        raise BootstrapError("installed root filesystem identity is invalid") from exc
    if canonical != matches[0].lower():
        raise BootstrapError("installed root filesystem identity is invalid")
    return canonical


def _clear_journal(paths: BootstrapPaths) -> None:
    paths.journal.unlink(missing_ok=True)
    if paths.journal.parent.is_dir():
        _fsync_directory(paths.journal.parent)


def _current_job_matches_journal(paths: BootstrapPaths, journal: Mapping[str, object]) -> bool:
    try:
        job = _read_job_locked(paths)
    except (OSError, BootstrapError):
        return False
    return job.get("job_id") == journal.get("job_id")


def _abandon_foreign_application_job(
    paths: BootstrapPaths, journal: Mapping[str, object]
) -> None:
    """Finish only the matching app job when its slot-local trial vanished."""

    job_id = journal.get("job_id")
    if not isinstance(job_id, str) or not JOB_ID_RE.fullmatch(job_id):
        return
    try:
        job = _read_job_locked(paths)
    except (OSError, BootstrapError):
        return
    if (
        job.get("job_id") != job_id
        or job.get("package_type") == "full_system"
        or job.get("state") not in {"applying", "restarting"}
    ):
        return
    _job_state_update(
        paths,
        "failed",
        error_code="application_slot_changed",
        error_message="the application trial belonged to a different system slot",
    )
    _clear_pending(paths)
    _clear_candidate(paths)


def _read_journal(paths: BootstrapPaths) -> dict[str, object] | None:
    try:
        return _read_regular_json(paths.journal, MAX_JOURNAL_BYTES)
    except BootstrapError as exc:
        if not paths.journal.exists() and not paths.journal.is_symlink():
            return None
        raise exc


def _read_job_locked(paths: BootstrapPaths) -> dict[str, object]:
    lock_fd = os.open(
        paths.job_lock,
        os.O_RDWR | os.O_CREAT | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
        0o660,
    )
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        state = _read_regular_json(paths.job, MAX_JOB_JSON_BYTES)
        if set(state) != {"schema_version", "job"} or state.get("schema_version") != 1:
            raise BootstrapError("software update job schema is invalid")
        job = state.get("job")
        if not isinstance(job, dict) or not isinstance(job.get("job_id"), str):
            raise BootstrapError("software update job is missing its identity")
        if not JOB_ID_RE.fullmatch(job["job_id"]):
            raise BootstrapError("software update job id is invalid")
        return job
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)


def _update_job_locked(
    paths: BootstrapPaths,
    *,
    state: str | None = None,
    fields: Mapping[str, object] | None = None,
    expected_job_id: str | None = None,
    clear_candidate: bool = False,
) -> dict[str, object]:
    lock_fd = os.open(
        paths.job_lock,
        os.O_RDWR | os.O_CREAT | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
        0o660,
    )
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        raw = _read_regular_json(paths.job, MAX_JOB_JSON_BYTES)
        if set(raw) != {"schema_version", "job"} or raw.get("schema_version") != 1:
            raise BootstrapError("software update job schema is invalid")
        original_job = raw.get("job")
        if not isinstance(original_job, dict) or not JOB_ID_RE.fullmatch(
            str(original_job.get("job_id", ""))
        ):
            raise BootstrapError("software update job identity is invalid")
        job = dict(original_job)
        if expected_job_id is not None and job.get("job_id") != expected_job_id:
            raise BootstrapError("software update job changed during activation")
        if state is not None:
            job["state"] = state
        if fields:
            job.update(fields)
        job["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        info = paths.job.lstat()
        temporary = paths.job.with_name(f".job.{uuid.uuid4().hex}.tmp")
        encoded = json.dumps(
            {"schema_version": 1, "job": job},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8") + b"\n"
        if len(encoded) > MAX_JOB_JSON_BYTES:
            raise BootstrapError("software update job exceeds its bound")
        descriptor = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
            stat.S_IMODE(info.st_mode),
        )
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            # Keep the job readable by greiapanel after root publishes status.
            os.chown(temporary, info.st_uid, info.st_gid)
            sync_descriptor = os.open(
                temporary, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
            )
            try:
                os.fsync(sync_descriptor)
            finally:
                os.close(sync_descriptor)
            os.replace(temporary, paths.job)
            _fsync_directory(paths.job.parent)
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
        if clear_candidate:
            # Keep the candidate cleanup inside the job lock that publishes
            # the terminal state. Otherwise a new upload can publish a fresh
            # candidate between the two operations and this worker deletes it.
            _clear_candidate(paths)
            _clear_pending(paths)
        return job
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)


def _clear_pending(paths: BootstrapPaths) -> None:
    paths.pending.unlink(missing_ok=True)
    if paths.pending.parent.is_dir():
        _fsync_directory(paths.pending.parent)


def _clear_candidate(paths: BootstrapPaths) -> None:
    paths.candidate.unlink(missing_ok=True)
    if paths.candidate.parent.is_dir():
        _fsync_directory(paths.candidate.parent)


def _restore_builtin_index_alias(paths: BootstrapPaths) -> None:
    """Keep the legacy index path following the same app generation pointer."""

    source = paths.application_root / "activity-index-v1.json"
    alias = paths.builtin_index
    relative_target = os.path.relpath(source, alias.parent)
    if alias.is_symlink():
        if os.readlink(alias) == relative_target:
            return
        try:
            if alias.resolve(strict=True) != source.resolve(strict=True):
                raise BootstrapError("built-in Activity index alias has the wrong target")
        except OSError as exc:
            raise BootstrapError("built-in Activity index alias has the wrong target") from exc
    elif alias.exists():
        if source.exists():
            raise BootstrapError("both the installed Activity index and generation index exist")
        source.parent.mkdir(parents=True, exist_ok=True)
        os.replace(alias, source)
        _fsync_directory(source.parent)
    if not source.is_file():
        raise BootstrapError("built-in Activity index is missing from the app generation")
    alias.parent.mkdir(parents=True, exist_ok=True)
    temporary = alias.with_name(f".{alias.name}.next-{uuid.uuid4().hex}")
    try:
        os.symlink(relative_target, temporary)
        os.replace(temporary, alias)
        _fsync_directory(alias.parent)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def _pin_installed_source(paths: BootstrapPaths) -> Path:
    """Pin this worker to the physical generation it started with.

    ``/opt/greia-os`` is the publication symlink. Keeping that symlink itself
    in ``sys.path`` would make late imports in this root worker cross into the
    candidate midway through its health transaction.
    """

    source = (paths.application_root / "src").resolve(strict=True)
    if not source.is_dir():
        raise BootstrapError("installed Greia source tree is unavailable")
    source_text = str(source)
    if source_text not in sys.path:
        sys.path.insert(0, source_text)
    return source


def migrate_directory_layout(paths: BootstrapPaths) -> str:
    """Convert a bootstrapped legacy directory to the one-pointer layout.

    The durable migration journal is written before the first rename.  If the
    process or machine stops between moving the directory and publishing its
    symlink, ``recover_before_services`` recreates the link before launcher or
    Parent can import application code.
    """

    if paths.application_root.is_symlink():
        generation_id = current_generation_id(paths)
        _restore_builtin_index_alias(paths)
        return generation_id
    if not paths.application_root.is_dir():
        raise BootstrapError("legacy application directory is missing")
    paths.generation_root.mkdir(parents=True, exist_ok=True)
    generation_id = "bootstrap-" + uuid.uuid4().hex
    target = _generation_target_for_migration(paths, generation_id)
    _write_journal(
        paths,
        {
            "schema_version": 1,
            "phase": "migration_started",
            "job_id": None,
            "previous_generation": generation_id,
            "candidate_generation": generation_id,
        },
    )
    _restore_builtin_index_alias(paths)
    os.replace(paths.application_root, target)
    _fsync_directory(paths.generation_root)
    _publish_root_link(paths, generation_id)
    _write_journal(
        paths,
        {
            "schema_version": 1,
            "phase": "layout_ready",
            "job_id": None,
            "previous_generation": generation_id,
            "candidate_generation": generation_id,
        },
    )
    return generation_id


def _generation_target_for_migration(paths: BootstrapPaths, generation_id: str) -> Path:
    if not GENERATION_ID_RE.fullmatch(generation_id):
        raise BootstrapError("bootstrap generation id is invalid")
    target = paths.generation_root / generation_id
    if target.exists() or target.is_symlink():
        raise BootstrapError("bootstrap generation destination already exists")
    return target


def _publish_root_link(paths: BootstrapPaths, generation_id: str) -> None:
    target = _generation_target(paths, generation_id)
    temporary = paths.application_root.with_name(
        f".{paths.application_root.name}.next-{uuid.uuid4().hex}"
    )
    try:
        os.symlink(os.path.relpath(target, paths.application_root.parent), temporary)
        os.replace(temporary, paths.application_root)
        _fsync_directory(paths.application_root.parent)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def _reconcile_migration(paths: BootstrapPaths, journal: Mapping[str, object]) -> None:
    generation_id = str(journal.get("candidate_generation", ""))
    target = _generation_target_for_recovery(paths, generation_id)
    app_root = paths.application_root
    if app_root.is_symlink():
        current_generation_id(paths)
        _restore_builtin_index_alias(paths)
        _write_journal(paths, {**journal, "phase": "layout_ready"})
        return
    if app_root.is_dir():
        # An interrupted migration may already have moved the external index
        # into the app tree.  The operation is safe to repeat under the journal.
        if paths.builtin_index.is_file() and not paths.builtin_index.is_symlink():
            if (app_root / "activity-index-v1.json").exists():
                raise BootstrapError("both built-in Activity index copies exist")
            os.replace(paths.builtin_index, app_root / "activity-index-v1.json")
            _fsync_directory(app_root)
        if target.exists():
            raise BootstrapError("both legacy and migrated application roots exist")
        os.replace(app_root, target)
        _fsync_directory(paths.generation_root)
        _publish_root_link(paths, generation_id)
        _restore_builtin_index_alias(paths)
        _write_journal(paths, {**journal, "phase": "layout_ready"})
        return
    if target.is_dir():
        _publish_root_link(paths, generation_id)
        _restore_builtin_index_alias(paths)
        _write_journal(paths, {**journal, "phase": "layout_ready"})
        return
    raise BootstrapError("interrupted app-root migration has no recoverable base tree")


def _restore_parent_activity_generation(paths: BootstrapPaths, generation_id: str) -> None:
    """Restore the PERSIST Activity source through its existing owner."""

    _pin_installed_source(paths)
    from greia_platform.activity_packages import ActivityPackageService

    service = ActivityPackageService.from_environment()
    with service.software_update_lock():
        service.restore_software_update_generation(generation_id)


def _generation_target_for_recovery(paths: BootstrapPaths, generation_id: str) -> Path:
    if not GENERATION_ID_RE.fullmatch(generation_id):
        raise BootstrapError("recovery generation id is invalid")
    return paths.generation_root / generation_id


def recover_before_services(paths: BootstrapPaths = BootstrapPaths()) -> None:
    """Repair a directory migration or interrupted generation trial at boot."""

    _ready(paths)
    journal = _read_journal(paths)
    if journal is not None and journal.get("schema_version") != 1:
        raise BootstrapError("software update journal schema is unsupported")
    phase = journal.get("phase") if journal else None
    if phase in {"migration_started", "switching", "trial", "committed"}:
        # The app generation directory belongs to one installed root slot.
        # Its journal is on shared PERSIST, so a later boot into the other
        # slot must discard that slot-local pointer instruction.
        if journal.get("base_root_uuid") != _current_root_uuid(paths):
            _abandon_foreign_application_job(paths, journal)
            _clear_journal(paths)
            journal = None
            phase = None
    if phase == "migration_started":
        _reconcile_migration(paths, journal)
    elif phase in {"switching", "trial", "switching_parent_activities", "trial_parent_activities"}:
        previous = str(journal.get("previous_generation", ""))
        if phase in {"switching_parent_activities", "trial_parent_activities"}:
            _restore_parent_activity_generation(paths, previous)
        else:
            _generation_target(paths, previous)
            switch_generation(paths, previous)
            _restore_builtin_index_alias(paths)
        job_id = journal.get("job_id")
        job_matches = _current_job_matches_journal(paths, journal)
        if isinstance(job_id, str) and JOB_ID_RE.fullmatch(job_id):
            if job_matches:
                try:
                    _update_job_locked(
                        paths,
                        state="rolled_back",
                        fields={
                            "error_code": "interrupted_activation",
                            "error_message": "the prior software generation was restored at boot",
                        },
                    )
                except (OSError, BootstrapError):
                    pass
        if job_matches:
            _clear_pending(paths)
            _clear_candidate(paths)
        if isinstance(job_id, str) and JOB_ID_RE.fullmatch(job_id):
            _clear_matching_restart_fence(paths, job_id)
        _write_journal(
            paths,
            {**journal, "phase": "rolled_back", "active_generation": previous},
        )
    elif phase == "committed":
        candidate = str(journal.get("candidate_generation", ""))
        _generation_target(paths, candidate)
        if current_generation_id(paths) != candidate:
            switch_generation(paths, candidate)
        _restore_builtin_index_alias(paths)
        job_id = journal.get("job_id")
        job_matches = _current_job_matches_journal(paths, journal)
        if isinstance(job_id, str) and JOB_ID_RE.fullmatch(job_id):
            if job_matches:
                try:
                    _update_job_locked(paths, state="applied", fields={"error_code": None, "error_message": None})
                except (OSError, BootstrapError):
                    pass
        if job_matches:
            _clear_pending(paths)
            _clear_candidate(paths)
    elif phase == "committed_parent_activities":
        job_id = journal.get("job_id")
        job_matches = _current_job_matches_journal(paths, journal)
        if isinstance(job_id, str) and JOB_ID_RE.fullmatch(job_id):
            if job_matches:
                try:
                    _update_job_locked(paths, state="applied", fields={"error_code": None, "error_message": None})
                except (OSError, BootstrapError):
                    pass
        if job_matches:
            _clear_pending(paths)
            _clear_candidate(paths)
    elif phase in {None, "layout_ready", "rolled_back"}:
        # No app update transaction is in flight.  A bootstrapped image has a
        # generation pointer; old regular directories are migrated only when
        # this stable helper and marker have both been installed.
        if paths.application_root.is_dir() and not paths.application_root.is_symlink():
            migrate_directory_layout(paths)
        else:
            current_generation_id(paths)
            _restore_builtin_index_alias(paths)
    else:
        raise BootstrapError("software update journal phase is unknown")
    _reconcile_job_marker(paths)


def _reconcile_job_marker(paths: BootstrapPaths) -> None:
    try:
        job = _read_job_locked(paths)
    except (OSError, BootstrapError):
        return
    state = job.get("state")
    if state in {"queued", "validating", "waiting_for_idle", "applying"} or (
        state == "ready_to_restart" and job.get("restart_requested") is True
    ) or state == "restarting":
        if not paths.pending.exists():
            paths.pending.parent.mkdir(parents=True, exist_ok=True)
            descriptor = os.open(
                paths.pending,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
                0o600,
            )
            os.close(descriptor)
            _fsync_directory(paths.pending.parent)
    elif state in TERMINAL_JOB_STATES or state == "ready_to_restart":
        _clear_pending(paths)
        if state in TERMINAL_JOB_STATES:
            _clear_candidate(paths)


def _job_state_update(
    paths: BootstrapPaths,
    state: str,
    *,
    expected_job_id: str | None = None,
    clear_candidate: bool = False,
    **fields: object,
) -> dict[str, object]:
    if state not in ACTIVE_JOB_STATES | TERMINAL_JOB_STATES | {"ready_to_restart"}:
        raise BootstrapError("software update state is not supported")
    return _update_job_locked(
        paths,
        state=state,
        fields=fields,
        expected_job_id=expected_job_id,
        clear_candidate=clear_candidate,
    )


def _fresh_launcher_ready(paths: BootstrapPaths, after_monotonic_ns: int) -> bool:
    """Accept only a launcher-ready event emitted after the switch boundary.

    The marker spool rotates by byte count, so a persisted byte offset can
    reject a fresh marker or accept a delayed old process marker. The existing
    boot marker carries the kernel monotonic timestamp needed for this boundary.
    """

    if (
        isinstance(after_monotonic_ns, bool)
        or not isinstance(after_monotonic_ns, int)
        or after_monotonic_ns < 0
    ):
        return False
    try:
        info = paths.boot_marker_spool.lstat()
        if not stat.S_ISREG(info.st_mode):
            return False
        with paths.boot_marker_spool.open("rb") as handle:
            handle.seek(max(0, info.st_size - 64 * 1024))
            tail = handle.read(64 * 1024)
    except OSError:
        return False
    for line in tail.decode("utf-8", errors="replace").splitlines():
        if not line.startswith("GREIA_BOOT "):
            continue
        fields = dict(
            field.split("=", 1)
            for field in line.split()[1:]
            if "=" in field
        )
        if fields.get("event") != "launcher_interactive_ready":
            continue
        try:
            emitted_at = int(fields.get("monotonic_ns", ""))
        except ValueError:
            continue
        if emitted_at > after_monotonic_ns:
            return True
    return False


def _profile_picker_idle(paths: BootstrapPaths) -> bool:
    """Do a cheap profile-lock check before hashing or extracting a package."""

    _pin_installed_source(paths)
    from greia_platform.profiles import ActiveProfileSession, ProfileError

    session = ActiveProfileSession(
        paths.active_profile,
        lock_path=paths.active_profile_lock,
        restart_fence_path=paths.restart_fence,
    )
    try:
        with session.profile_picker_restart_guard():
            return True
    except ProfileError:
        return False


def _restart_fence_job_id(paths: BootstrapPaths) -> str | None:
    if not paths.restart_fence.exists() and not paths.restart_fence.is_symlink():
        return None
    fence = _read_regular_json(paths.restart_fence, MAX_SMALL_JSON_BYTES)
    request_id = fence.get("request_id")
    if (
        set(fence) != {"request_id", "schema", "state"}
        or fence.get("schema") != 1
        or fence.get("state") != "handoff_pending"
        or not isinstance(request_id, str)
        or not JOB_ID_RE.fullmatch(request_id)
    ):
        raise BootstrapError("software update restart fence is invalid")
    return request_id


def _clear_matching_restart_fence(paths: BootstrapPaths, job_id: str) -> None:
    if _restart_fence_job_id(paths) == job_id:
        _clear_restart_fence(paths)


def _ensure_previous_services_ready(paths: BootstrapPaths) -> None:
    """Start only missing services while a matching fence blocks child entry."""

    try:
        _run_systemctl("is-active", "--quiet", "greia-launcher.service")
    except BootstrapError:
        boundary = time.monotonic_ns()
        _run_systemctl("start", "greia-launcher.service")
        if not _wait_for_ready(paths, boundary, timeout=90.0):
            raise BootstrapError("restored launcher did not reach its profile picker")
        _run_systemctl("is-active", "--quiet", "greia-launcher.service")
    _start_parent_and_wait()


def _ensure_pending_marker(paths: BootstrapPaths) -> None:
    if paths.pending.exists():
        return
    paths.pending.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        paths.pending,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
        0o600,
    )
    os.close(descriptor)
    _fsync_directory(paths.pending.parent)


def _wait_for_parent_ready(*, timeout: float) -> bool:
    """Wait for the existing loopback health endpoint after Parent starts."""

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        connection = http.client.HTTPConnection("127.0.0.1", 8767, timeout=1.0)
        try:
            connection.request("GET", "/healthz", headers={"Connection": "close"})
            response = connection.getresponse()
            payload = response.read(128)
            if (
                response.status == 200
                and json.loads(payload.decode("utf-8")) == {"status": "ok"}
            ):
                return True
        except (OSError, http.client.HTTPException, UnicodeDecodeError, json.JSONDecodeError):
            pass
        finally:
            connection.close()
        time.sleep(0.25)
    return False


def _start_parent_and_wait(*, timeout: float = 30.0) -> None:
    _run_systemctl("start", "greia-parent.service")
    _run_systemctl("is-active", "--quiet", "greia-parent.service")
    if not _wait_for_parent_ready(timeout=timeout):
        raise BootstrapError("Parent loopback health endpoint did not become ready")


def _run_systemctl(*arguments: str, timeout: float = 30.0) -> None:
    result = subprocess.run(
        ["/usr/bin/systemctl", *arguments],
        check=False,
        shell=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise BootstrapError(f"systemd operation failed: {arguments[0]}")


def apply_pending(paths: BootstrapPaths = BootstrapPaths()) -> int:
    """Apply one durable queued job; detailed preparation lives in source code."""

    _ready(paths)
    if not paths.pending.is_file():
        return 0
    job = _read_job_locked(paths)
    if job.get("state") == "restarting":
        return _reconcile_restart_job(paths, job)
    journal = _read_journal(paths)
    if (
        journal is not None
        and journal.get("job_id") == job.get("job_id")
        and journal.get("phase") in {
            "switching", "trial", "switching_parent_activities", "trial_parent_activities"
        }
    ):
        return _reconcile_application_trial(paths, job)
    if (
        job.get("state") in {"waiting_for_idle", "applying"}
        and _restart_fence_job_id(paths) == job.get("job_id")
    ):
        return _reconcile_orphan_restart_fence(paths, job)
    if job.get("state") == "ready_to_restart" and job.get("restart_requested") is True:
        return _request_full_system_restart(paths, job)
    if job.get("state") in TERMINAL_JOB_STATES or job.get("state") == "ready_to_restart":
        _clear_pending(paths)
        _clear_candidate(paths)
        return 0
    if job.get("state") not in ACTIVE_JOB_STATES:
        raise BootstrapError("software update job is not applicable")

    # The timer also runs while a child may be playing. Check the small local
    # profile authority before package hashing, archive validation, extraction,
    # or Python compilation. _activate_generation repeats the guard after the
    # potentially long preparation to close the race before pointer changes.
    if not _profile_picker_idle(paths):
        if job.get("state") != "waiting_for_idle":
            _job_state_update(paths, "waiting_for_idle")
        return 0

    # Import app code only for a new/retryable preparation. A restarting
    # transaction is reconciled above by this stable file, even if the new
    # application modules cannot be imported.
    _pin_installed_source(paths)
    from greia_platform.software_update_apply import prepare_software_update
    from greia_platform.profiles import ProfileError

    try:
        _job_state_update(paths, "validating", error_code=None, error_message=None)
        job = _read_job_locked(paths)
        plan = prepare_software_update(job, paths)
    except Exception as exc:
        _job_state_update(
            paths,
            "failed",
            error_code="package_invalid",
            error_message=_bounded_message(exc),
        )
        _clear_pending(paths)
        _clear_candidate(paths)
        return 1

    job = _job_state_update(
        paths,
        "validating",
        package_type=plan.package_type,
        version=plan.version,
        release_id=plan.release_id,
        package_sha256=plan.package_sha256,
    )
    if plan.kind == "full_system":
        _job_state_update(
            paths,
            "ready_to_restart",
            restart_requested=False,
            error_code=None,
            error_message=None,
        )
        _clear_pending(paths)
        _clear_candidate(paths)
        return 0

    if plan.kind not in {"parent_activities", "application_generation"}:
        raise BootstrapError("software update preparation returned an unknown operation")
    job = _job_state_update(
        paths,
        "waiting_for_idle",
        activation_kind=plan.kind,
        previous_generation=plan.previous_generation,
        candidate_generation=plan.candidate_generation,
    )
    try:
        _activate_generation(paths, job, plan)
    except ProfileError:
        # Busy or unreadable authority is not idle evidence. Keep the job for
        # the next timer tick; the guard releases its lock without activating.
        return 0
    except Exception as exc:
        if _rollback_failed_activation(paths, str(job["job_id"]), exc):
            return 1
        _job_state_update(
            paths,
            "failed",
            error_code="activation_failed",
            error_message=_bounded_message(exc),
        )
        _clear_pending(paths)
        _clear_candidate(paths)
        return 1
    return 0


def _rollback_failed_activation(
    paths: BootstrapPaths, job_id: str, failure: BaseException
) -> bool:
    """Recover an activation that failed before the normal health path."""

    journal = _read_journal(paths)
    if (
        journal is None
        or journal.get("job_id") != job_id
        or journal.get("phase")
        not in {"switching", "trial", "switching_parent_activities", "trial_parent_activities"}
    ):
        return False
    previous = str(journal.get("previous_generation", ""))
    candidate = str(journal.get("candidate_generation", ""))
    try:
        _run_systemctl("stop", "greia-parent.service", "greia-launcher.service")
        if journal.get("phase") in {"switching_parent_activities", "trial_parent_activities"}:
            _restore_parent_activity_generation(paths, previous)
        else:
            _generation_target(paths, previous)
            switch_generation(paths, previous)
            _restore_builtin_index_alias(paths)
        readiness_boundary = time.monotonic_ns()
        _run_systemctl("start", "greia-launcher.service")
        if not _wait_for_ready(paths, readiness_boundary, timeout=90.0):
            raise BootstrapError("restored launcher did not reach its profile picker")
        _run_systemctl("is-active", "--quiet", "greia-launcher.service")
        _start_parent_and_wait()
        _write_journal(
            paths,
            {
                "schema_version": 1,
                "phase": "rolled_back",
                "job_id": job_id,
                "previous_generation": previous,
                "candidate_generation": candidate,
            },
        )
        _job_state_update(
            paths,
            "rolled_back",
            error_code="activation_failed",
            error_message=_bounded_message(failure),
        )
        _clear_pending(paths)
        _clear_restart_fence(paths)
        _clear_candidate(paths)
    except Exception as rollback_error:
        _job_state_update(
            paths,
            "restarting",
            error_code="rollback_incomplete",
            error_message=_bounded_message(rollback_error),
        )
        _reconcile_job_marker(paths)
        return True
    return True


def _activate_generation(paths: BootstrapPaths, job: Mapping[str, object], plan: object) -> None:
    from contextlib import nullcontext
    from greia_platform.profiles import ProfileError

    job_id = str(job["job_id"])
    previous = str(plan.previous_generation)
    candidate = str(plan.candidate_generation)
    profile_session = getattr(plan, "profile_session", None)
    if profile_session is None:
        raise BootstrapError("application update has no profile session authority")
    parent_service = getattr(plan, "activity_service", None)
    update_lock = parent_service.software_update_lock() if parent_service is not None else nullcontext()
    phase = "trial_parent_activities" if getattr(plan, "kind", "") == "parent_activities" else "trial"
    receipt_fields = _parent_receipt_journal_fields(plan)
    if phase == "trial":
        if current_generation_id(paths) != previous:
            raise BootstrapError("application generation changed while the update was staged")
        _generation_target(paths, candidate)

    # Hold the shared profile lock through the pointer change, then release it
    # before the new launcher writes its profile-picker-idle status. The root
    # restart fence blocks child activation until startup is accepted.
    with profile_session.profile_picker_restart_guard():
        with update_lock:
            if phase == "trial" and current_generation_id(paths) != previous:
                raise BootstrapError(
                    "application generation changed before the profile-picker switch"
                )
            if phase != "trial" and parent_service.active_generation_id() != previous:
                raise BootstrapError(
                    "Parent Activity generation changed before the profile-picker switch"
                )
            # The fence is published under the same profile lock as the idle
            # proof. The journal follows before any service is stopped. If the
            # worker dies between these writes, the next tick can safely clear
            # the orphan fence without disturbing the old running generation.
            _write_restart_fence(paths, job_id)
            _write_journal(
                paths,
                {
                    "schema_version": 1,
                    "phase": "switching_parent_activities" if phase != "trial" else "switching",
                    "job_id": job_id,
                    "previous_generation": previous,
                    "candidate_generation": candidate,
                    **receipt_fields,
                },
            )
            _job_state_update(paths, "applying")
            _run_systemctl("stop", "greia-parent.service", "greia-launcher.service")
            if phase == "trial":
                switch_generation(paths, candidate)
                _restore_builtin_index_alias(paths)
            else:
                plan.publish_parent_generation()
            readiness_boundary = time.monotonic_ns()
            _write_journal(
                paths,
                {
                    "schema_version": 1,
                    "phase": phase,
                    "job_id": job_id,
                    "previous_generation": previous,
                    "candidate_generation": candidate,
                    "readiness_boundary_monotonic_ns": readiness_boundary,
                    "trial_started_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    **receipt_fields,
                },
            )
            _job_state_update(paths, "restarting")

    try:
        _run_systemctl("start", "greia-launcher.service")
        ready = _wait_for_ready(paths, readiness_boundary, timeout=90.0)
        if ready:
            _run_systemctl("is-active", "--quiet", "greia-launcher.service")
            _start_parent_and_wait()
            if phase != "trial":
                with parent_service.software_update_lock():
                    plan.commit_parent_generation()
            _write_journal(
                paths,
                {
                    "schema_version": 1,
                    "phase": "committed_parent_activities" if phase != "trial" else "committed",
                    "job_id": job_id,
                    "previous_generation": previous,
                    "candidate_generation": candidate,
                },
            )
            _job_state_update(
                paths,
                "applied",
                error_code=None,
                error_message=None,
                expected_job_id=job_id,
                clear_candidate=True,
            )
            _clear_restart_fence(paths)
            if phase == "trial":
                _prune_generations(paths, keep={previous, candidate})
            return
    except Exception:
        ready = False

    # Any missing launcher readiness or Parent service startup means the
    # previous complete generation is the recovery choice. Preserve the fence
    # until the old services are back at their profile picker.
    try:
        _run_systemctl("stop", "greia-parent.service", "greia-launcher.service")
        if phase == "trial":
            switch_generation(paths, previous)
            _restore_builtin_index_alias(paths)
        else:
            with parent_service.software_update_lock():
                plan.rollback_parent_generation()
        readiness_boundary = time.monotonic_ns()
        _run_systemctl("start", "greia-launcher.service")
        if not _wait_for_ready(paths, readiness_boundary, timeout=90.0):
            raise BootstrapError("restored launcher did not reach its profile picker")
        _run_systemctl("is-active", "--quiet", "greia-launcher.service")
        _start_parent_and_wait()
        _write_journal(
            paths,
            {
                "schema_version": 1,
                "phase": "rolled_back",
                "job_id": job_id,
                "previous_generation": previous,
                "candidate_generation": candidate,
            },
        )
        _job_state_update(
            paths,
            "rolled_back",
            error_code="launcher_not_ready",
            error_message="the previous software generation was restored",
            expected_job_id=job_id,
            clear_candidate=True,
        )
        _clear_restart_fence(paths)
        if phase == "trial":
            _prune_generations(paths, keep={previous})
    except Exception as exc:
        _job_state_update(
            paths,
            "restarting",
            error_code="rollback_incomplete",
            error_message=_bounded_message(exc),
        )
        # Keep marker, journal and profile fence for stable boot recovery.
        raise BootstrapError("software update rollback needs boot recovery") from exc


def _wait_for_ready(
    paths: BootstrapPaths, after_monotonic_ns: int, *, timeout: float
) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _fresh_launcher_ready(paths, after_monotonic_ns):
            return True
        time.sleep(0.25)
    return False


def _write_restart_fence(paths: BootstrapPaths, job_id: str) -> None:
    """Publish the existing profile-session fence using stable stdlib code."""

    if not JOB_ID_RE.fullmatch(job_id):
        raise BootstrapError("software update restart fence identity is invalid")
    _atomic_write_json(
        paths.restart_fence,
        {"request_id": job_id, "schema": 1, "state": "handoff_pending"},
        mode=0o644,
    )


def _clear_restart_fence(paths: BootstrapPaths) -> None:
    paths.restart_fence.unlink(missing_ok=True)
    if paths.restart_fence.parent.is_dir():
        _fsync_directory(paths.restart_fence.parent)


def _bounded_message(exc: BaseException) -> str:
    message = " ".join(str(exc).split())
    return message[:240] or type(exc).__name__


def _prune_generations(paths: BootstrapPaths, *, keep: set[str]) -> None:
    if not paths.generation_root.is_dir():
        return
    for entry in paths.generation_root.iterdir():
        if entry.name in keep or not GENERATION_ID_RE.fullmatch(entry.name):
            continue
        if entry.is_symlink() or not entry.is_dir():
            continue
        _remove_tree(entry)


def _remove_tree(root: Path) -> None:
    for current, directories, _files in os.walk(root, topdown=False, followlinks=False):
        for name in directories:
            path = Path(current) / name
            if path.is_symlink():
                path.unlink(missing_ok=True)
            else:
                os.chmod(path, 0o755)
        try:
            os.chmod(current, 0o755)
        except OSError:
            pass
    shutil.rmtree(root)
    _fsync_directory(root.parent)


def _reconcile_restart_job(paths: BootstrapPaths, job: Mapping[str, object]) -> int:
    """Resolve a previous explicit A/B handoff without issuing it again."""

    if job.get("package_type") != "full_system":
        return _reconcile_application_trial(paths, job)

    _pin_installed_source(paths)
    from greia_platform.update_client import UpdatePrivilegedClient

    try:
        status = UpdatePrivilegedClient().request("STATUS")
    except Exception:
        return 0
    if status.get("status") != "OK":
        return 0
    journal = status.get("journal")
    if isinstance(journal, dict):
        outcome = journal.get("state")
        if outcome in {"accepted", "updated", "committed", "healthy"}:
            _job_state_update(paths, "applied", error_code=None, error_message=None)
            _clear_pending(paths)
        elif outcome in {"rolled_back", "failed"}:
            _job_state_update(paths, "rolled_back", error_code="system_update_rollback", error_message="the system slot restored its accepted release")
            _clear_pending(paths)
        elif (
            outcome in {"update_staged", "one_shot_armed"}
            and status.get("restart_pending") is False
            and job.get("restart_requested") is False
        ):
            _job_state_update(paths, "ready_to_restart", restart_requested=False)
            _clear_pending(paths)
    return 0


def _parent_receipt_journal_fields(plan: object) -> dict[str, object]:
    generation = getattr(plan, "parent_generation", None)
    if generation is None:
        return {}
    receipts = getattr(generation, "receipts", None)
    if not isinstance(receipts, (tuple, list)) or len(receipts) > 64:
        raise BootstrapError("Parent Activity update receipts exceed their bound")
    compact: list[dict[str, object]] = []
    for receipt in receipts:
        serialize = getattr(receipt, "as_json_dict", None)
        if not callable(serialize):
            raise BootstrapError("Parent Activity update receipt is invalid")
        raw = serialize()
        compact.append(
            {
                "activity_id": raw.get("activity_id"),
                "version": raw.get("version"),
                "package_digest": raw.get("package_digest"),
                "size_bytes": raw.get("size_bytes"),
                "size_guideline_bytes": raw.get("size_guideline_bytes"),
            }
        )
    return {"parent_receipts": compact}


def _journal_parent_receipts(journal: Mapping[str, object]) -> list[Mapping[str, object]]:
    receipts = journal.get("parent_receipts", [])
    if not isinstance(receipts, list) or len(receipts) > 64:
        raise BootstrapError("Parent Activity update receipts are invalid")
    if any(not isinstance(receipt, Mapping) for receipt in receipts):
        raise BootstrapError("Parent Activity update receipts are invalid")
    return receipts


def _reconcile_orphan_restart_fence(
    paths: BootstrapPaths, job: Mapping[str, object]
) -> int:
    """Clear the fence-before-journal crash cut without changing generations."""

    job_id = str(job.get("job_id", ""))
    if _restart_fence_job_id(paths) != job_id:
        return 0
    previous = job.get("previous_generation")
    if not isinstance(previous, str):
        return 0
    if job.get("activation_kind") == "parent_activities":
        _pin_installed_source(paths)
        from greia_platform.activity_packages import ActivityPackageService

        active = ActivityPackageService.from_environment().active_generation_id() or "gen-000001"
    else:
        try:
            active = current_generation_id(paths)
        except BootstrapError:
            return 0
    if active != previous:
        # No switching journal means the durable pointer must not be guessed.
        # Keep the fence and pending job for boot recovery/review.
        return 1
    if not _profile_picker_idle(paths):
        return 0
    _ensure_previous_services_ready(paths)
    _clear_matching_restart_fence(paths, job_id)
    _job_state_update(paths, "waiting_for_idle", error_code=None, error_message=None)
    _write_journal(
        paths,
        {
            "schema_version": 1,
            "phase": "rolled_back",
            "job_id": job_id,
            "previous_generation": previous,
            "candidate_generation": job.get("candidate_generation"),
        },
    )
    _ensure_pending_marker(paths)
    return 0


def _reconcile_application_trial(paths: BootstrapPaths, job: Mapping[str, object]) -> int:
    journal = _read_journal(paths)
    supported = {
        "switching",
        "trial",
        "switching_parent_activities",
        "trial_parent_activities",
    }
    if journal is None or journal.get("phase") not in supported:
        return 0
    if journal.get("job_id") != job.get("job_id"):
        return 0
    phase = str(journal["phase"])
    parent_update = phase in {"switching_parent_activities", "trial_parent_activities"}
    previous = str(journal.get("previous_generation", ""))
    candidate = str(journal.get("candidate_generation", ""))
    if phase in {"switching", "switching_parent_activities"}:
        return _reconcile_pretrial_activation(
            paths, job, journal, previous, candidate, parent_update
        )
    if _restart_fence_job_id(paths) != job.get("job_id"):
        _job_state_update(
            paths,
            "restarting",
            error_code="activation_fence_missing",
            error_message="the active software trial has no matching profile fence",
        )
        return 1
    readiness_boundary = journal.get("readiness_boundary_monotonic_ns")
    generation_is_active = False
    if parent_update:
        _pin_installed_source(paths)
        from greia_platform.activity_packages import ActivityPackageService

        generation_is_active = (
            ActivityPackageService.from_environment().active_generation_id() == candidate
        )
    else:
        try:
            generation_is_active = current_generation_id(paths) == candidate
        except BootstrapError:
            generation_is_active = False
    if (
        generation_is_active
        and isinstance(readiness_boundary, int)
        and not isinstance(readiness_boundary, bool)
        and _fresh_launcher_ready(paths, readiness_boundary)
    ):
        try:
            _run_systemctl("is-active", "--quiet", "greia-launcher.service")
            _start_parent_and_wait()
            if parent_update:
                _pin_installed_source(paths)
                from greia_platform.activity_packages import ActivityPackageService

                service = ActivityPackageService.from_environment()
                generation = service.active_generation_id()
                if generation != candidate:
                    raise BootstrapError("Parent Activity candidate is not active")
                service.commit_software_update_generation_receipts(
                    previous,
                    candidate,
                    _journal_parent_receipts(journal),
                )
            committed_phase = "committed_parent_activities" if parent_update else "committed"
            _write_journal(paths, {**journal, "phase": committed_phase})
            _job_state_update(
                paths,
                "applied",
                error_code=None,
                error_message=None,
                expected_job_id=str(job.get("job_id", "")),
                clear_candidate=True,
            )
            _clear_restart_fence(paths)
            if not parent_update and GENERATION_ID_RE.fullmatch(previous) and GENERATION_ID_RE.fullmatch(candidate):
                _prune_generations(paths, keep={previous, candidate})
            return 0
        except Exception:
            return _rollback_reconciled_activation(
                paths, job, journal, previous, candidate, parent_update
            )
    if isinstance(readiness_boundary, bool) or not isinstance(readiness_boundary, int):
        return _rollback_reconciled_activation(
            paths, job, journal, previous, candidate, parent_update
        )
    now_monotonic_ns = time.monotonic_ns()
    if readiness_boundary < 0 or readiness_boundary > now_monotonic_ns:
        return _rollback_reconciled_activation(
            paths, job, journal, previous, candidate, parent_update
        )
    elapsed_ns = now_monotonic_ns - readiness_boundary
    if elapsed_ns < 90_000_000_000:
        return 0
    return _rollback_reconciled_activation(
        paths, job, journal, previous, candidate, parent_update
    )


def _reconcile_pretrial_activation(
    paths: BootstrapPaths,
    job: Mapping[str, object],
    journal: Mapping[str, object],
    previous: str,
    candidate: str,
    parent_update: bool,
) -> int:
    """Recover worker death between the switching journal and trial record."""

    job_id = str(job.get("job_id", ""))
    if parent_update:
        _pin_installed_source(paths)
        from greia_platform.activity_packages import ActivityPackageService

        active = ActivityPackageService.from_environment().active_generation_id() or "gen-000001"
    else:
        try:
            active = current_generation_id(paths)
        except BootstrapError:
            return 1
    fence_job_id = _restart_fence_job_id(paths)

    if active == previous:
        if fence_job_id == job_id:
            # No pointer moved. The matching fence proves the original idle
            # check happened before any stop, but verify the marker again and
            # start only services that had not yet been stopped.
            if not _profile_picker_idle(paths):
                return 0
            _ensure_previous_services_ready(paths)
            _clear_matching_restart_fence(paths, job_id)
        elif fence_job_id is not None:
            return 0
        # With no matching fence, never stop a possibly active old child.
        _write_journal(paths, {**journal, "phase": "rolled_back"})
        _job_state_update(
            paths,
            "waiting_for_idle",
            error_code=None,
            error_message=None,
        )
        _ensure_pending_marker(paths)
        return 0

    if active == candidate and fence_job_id == job_id:
        if not _profile_picker_idle(paths):
            return 0
        return _rollback_reconciled_activation(
            paths, job, journal, previous, candidate, parent_update
        )

    # A pointer change without the journaled fence is ambiguous. Keep the
    # candidate running and leave boot recovery the authority; never kill an
    # unproven live session to guess the previous state.
    _job_state_update(
        paths,
        "restarting",
        error_code="activation_state_ambiguous",
        error_message="the incomplete activation cannot be reconciled safely",
    )
    return 1


def _rollback_reconciled_activation(
    paths: BootstrapPaths,
    job: Mapping[str, object],
    journal: Mapping[str, object],
    previous: str,
    candidate: str,
    parent_update: bool,
) -> int:
    """Restore a staged generation after the previous worker stopped."""

    if not parent_update:
        _generation_target(paths, previous)
    _run_systemctl("stop", "greia-parent.service", "greia-launcher.service")
    if parent_update:
        _restore_parent_activity_generation(paths, previous)
    else:
        switch_generation(paths, previous)
        _restore_builtin_index_alias(paths)
    readiness_boundary = time.monotonic_ns()
    _run_systemctl("start", "greia-launcher.service")
    if not _wait_for_ready(paths, readiness_boundary, timeout=90.0):
        return 1
    _run_systemctl("is-active", "--quiet", "greia-launcher.service")
    _start_parent_and_wait()
    _write_journal(paths, {**journal, "phase": "rolled_back"})
    _job_state_update(
        paths,
        "rolled_back",
        error_code="launcher_not_ready",
        error_message="the previous software generation was restored",
    )
    _clear_pending(paths)
    _clear_restart_fence(paths)
    _clear_candidate(paths)
    if not parent_update and GENERATION_ID_RE.fullmatch(candidate) and candidate != previous:
        _prune_generations(paths, keep={previous})
    return 1


def _request_full_system_restart(paths: BootstrapPaths, job: Mapping[str, object]) -> int:
    job_id = str(job.get("job_id", ""))
    if not JOB_ID_RE.fullmatch(job_id):
        raise BootstrapError("full-system update job id is invalid")
    _pin_installed_source(paths)
    from greia_platform.update_client import UpdatePrivilegedClient

    # Consume the authorization before handing it to the existing A/B service.
    # A lost/unknown handoff is reconciled from root STATUS and is never
    # automatically issued again by the timer.
    _job_state_update(paths, "restarting", restart_requested=False, error_code=None, error_message=None)
    try:
        response = UpdatePrivilegedClient().request("REQUEST_RESTART")
    except Exception as exc:
        _job_state_update(
            paths,
            "restarting",
            error_code="restart_handoff_unknown",
            error_message=_bounded_message(exc),
        )
        return 1
    if response.get("status") == "RESTART_ACCEPTED":
        return 0
    _job_state_update(
        paths,
        "ready_to_restart",
        restart_requested=False,
        error_code="restart_refused",
        error_message=_bounded_message(BootstrapError(str(response.get("reason", "restart refused")))),
    )
    _clear_pending(paths)
    return 1


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Greia stable software-update bootstrap")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--recover", action="store_true")
    group.add_argument("--apply", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        if args.recover:
            recover_before_services()
            return 0
        return apply_pending()
    except Exception as exc:
        print(f"software-update bootstrap failed: {_bounded_message(exc)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
