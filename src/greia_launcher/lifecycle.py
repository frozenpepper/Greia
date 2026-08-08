from __future__ import annotations

import os
import shutil
import signal
import time
import uuid
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol


class ActivitySessionState(StrEnum):
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    EXITED = "exited"
    FAILED = "failed"


class ActivityExitReason(StrEnum):
    NORMAL = "normal"
    CRASH = "crash"
    LAUNCH_FAILURE = "launch_failure"
    READY_TIMEOUT = "ready_timeout"
    GRACEFUL_STOP = "graceful_stop"
    FORCED_STOP = "forced_stop"
    SYSTEM_SHUTDOWN = "system_shutdown"


class ProcessHandle(Protocol):
    pid: int
    returncode: int | None

    def poll(self) -> int | None: ...

    def terminate(self) -> None: ...

    def kill(self) -> None: ...


@dataclass(frozen=True, slots=True)
class ActivityControlChannel:
    """Per-launch lifecycle channel stored inside the Activity's private data.

    Markers are cooperation signals, not authority. The Activity can write them
    because it owns its own data namespace; it cannot use them to gain any new
    mount, device or broker permission.
    """

    session_id: str
    host_root: Path
    child_root: Path

    @classmethod
    def create(
        cls,
        host_activity_data: Path,
        child_activity_data: Path,
    ) -> "ActivityControlChannel":
        session_id = uuid.uuid4().hex
        host_root = host_activity_data / ".greia" / "runtime" / session_id
        child_root = child_activity_data / ".greia" / "runtime" / session_id
        host_root.mkdir(parents=True, exist_ok=False)
        os.chmod(host_root, 0o770)
        return cls(session_id, host_root, child_root)

    @property
    def host_ready_path(self) -> Path:
        return self.host_root / "ready"

    @property
    def host_stop_path(self) -> Path:
        return self.host_root / "stop-requested"

    @property
    def child_ready_path(self) -> Path:
        return self.child_root / "ready"

    @property
    def child_stop_path(self) -> Path:
        return self.child_root / "stop-requested"

    def ready(self) -> bool:
        return self._marker_matches(self.host_ready_path)

    def request_stop(self) -> None:
        self._write_marker(self.host_stop_path)

    def cleanup(self) -> None:
        try:
            shutil.rmtree(self.host_root)
        except FileNotFoundError:
            pass

    def _marker_matches(self, path: Path) -> bool:
        try:
            return path.read_text(encoding="ascii").strip() == self.session_id
        except (OSError, UnicodeDecodeError):
            return False

    def _write_marker(self, path: Path) -> None:
        temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        temporary.write_text(self.session_id + "\n", encoding="ascii")
        os.chmod(temporary, 0o660)
        temporary.replace(path)


@dataclass(frozen=True, slots=True)
class ActivityResult:
    activity_id: str
    session_id: str
    return_code: int
    exit_reason: ActivityExitReason
    ready: bool
    started_at: float
    ready_at: float | None
    ended_at: float

    @property
    def succeeded(self) -> bool:
        return self.return_code == 0 and self.exit_reason in {
            ActivityExitReason.NORMAL,
            ActivityExitReason.GRACEFUL_STOP,
        }


@dataclass(slots=True)
class ActivitySession:
    activity_id: str
    package_digest: str
    control: ActivityControlChannel
    process: ProcessHandle | None
    state: ActivitySessionState
    started_at: float
    ready_deadline: float
    graceful_stop_seconds: float
    ready_at: float | None = None
    stop_requested_at: float | None = None
    forced_reason: ActivityExitReason | None = None
    result: ActivityResult | None = None

    @property
    def session_id(self) -> str:
        return self.control.session_id

    @property
    def terminal(self) -> bool:
        return self.state in {ActivitySessionState.EXITED, ActivitySessionState.FAILED}


def signal_process_group(process: ProcessHandle, *, force: bool) -> None:
    """Signal the complete Activity process group when the OS supports it."""

    if process.poll() is not None:
        return
    if os.name == "posix":
        try:
            os.killpg(process.pid, signal.SIGKILL if force else signal.SIGTERM)
            return
        except (ProcessLookupError, PermissionError):
            if process.poll() is not None:
                return
    if force:
        process.kill()
    else:
        process.terminate()


def monotonic_now() -> float:
    return time.monotonic()
