from __future__ import annotations

from contextlib import AbstractContextManager
import json
import os
from pathlib import Path
import time


class GenerationLockError(RuntimeError):
    pass


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        # Conservative on platforms where kill(pid, 0) is not fully supported.
        return True
    return True


class InterprocessGenerationLock(AbstractContextManager["InterprocessGenerationLock"]):
    """Fail-fast cross-process guard against concurrent local ML voice workers.

    The lock is deliberately not a queue. Greia voice production is a single-worker
    authoring facility; callers should use the daemon or batch command when they have
    multiple requests instead of starting competing inference processes.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self._owned = False

    def __enter__(self) -> "InterprocessGenerationLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps({"pid": os.getpid(), "created": time.time()}) + "\n"
        for _ in range(2):
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            except FileExistsError:
                try:
                    current = json.loads(self.path.read_text(encoding="utf-8"))
                    owner_pid = int(current.get("pid", -1))
                except Exception:
                    owner_pid = -1
                if _pid_alive(owner_pid):
                    raise GenerationLockError(
                        f"another Greia voice worker is active (pid {owner_pid}); "
                        "use the running service/batch instead of concurrent inference"
                    )
                try:
                    self.path.unlink()
                except FileNotFoundError:
                    pass
                continue
            else:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    handle.write(payload)
                self._owned = True
                return self
        raise GenerationLockError("could not acquire Greia voice generation lock")

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._owned:
            try:
                current = json.loads(self.path.read_text(encoding="utf-8"))
                if int(current.get("pid", -1)) == os.getpid():
                    self.path.unlink(missing_ok=True)
            finally:
                self._owned = False


class NullGenerationLock(AbstractContextManager["NullGenerationLock"]):
    """No-op lock for an engine already protected by a longer-lived owner lock."""

    def __enter__(self) -> "NullGenerationLock":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None
