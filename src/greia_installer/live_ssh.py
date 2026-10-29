"""Live-installer SSH control, scoped to a single systemd unit."""
from __future__ import annotations

import queue
import subprocess
import threading
from dataclasses import dataclass
from typing import Callable


class LiveSshError(RuntimeError):
    """The live installer's SSH state could not be changed or checked."""


class LiveSshService:
    """Root-side service: control only the live installer's SSH unit."""

    def __init__(self, runner: Callable[..., object] = subprocess.run) -> None:
        self._run = runner

    def status(self) -> bool:
        try:
            result = self._run(["systemctl", "is-active", "--quiet", "ssh.service"],
                               shell=False, capture_output=True, timeout=8, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise LiveSshError("Could not check SSH") from exc
        if result.returncode == 0:
            return True
        if result.returncode == 3:
            return False
        raise LiveSshError("Could not check SSH")

    def set_enabled(self, enabled: bool) -> bool:
        if not isinstance(enabled, bool):
            raise LiveSshError("SSH state must be true or false")
        try:
            result = self._run(["systemctl", "start" if enabled else "stop", "ssh.service"],
                               shell=False, capture_output=True, timeout=45, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise LiveSshError("Could not change SSH") from exc
        if result.returncode != 0:
            raise LiveSshError("Could not change SSH")
        active = self.status()
        if active != enabled:
            raise LiveSshError("SSH did not reach the requested state")
        return active


@dataclass(frozen=True, slots=True)
class LiveSshSnapshot:
    enabled: bool = False
    busy: bool = False
    error: bool = False


class LiveSshToggle:
    """Nonblocking UI owner for one in-flight status or toggle request."""

    def __init__(self, client: object | None, *, demo: bool = False) -> None:
        self._client = client
        self._demo = demo
        self.snapshot = LiveSshSnapshot()
        self._results: queue.Queue[tuple[bool | None, bool]] = queue.Queue(maxsize=1)

    def refresh(self) -> None:
        self._start(None)

    def toggle(self) -> None:
        self._start(not self.snapshot.enabled)

    def _start(self, desired: bool | None) -> None:
        if self.snapshot.busy:
            return
        if self._demo:
            if desired is not None:
                self.snapshot = LiveSshSnapshot(enabled=desired)
            return
        self.snapshot = LiveSshSnapshot(self.snapshot.enabled, True, False)
        def work() -> None:
            try:
                if desired is None:
                    value = self._client.live_ssh_status()
                else:
                    value = self._client.set_live_ssh(desired)
                self._results.put_nowait((value, False))
            except Exception:
                # A timed-out start/stop may still have taken effect. Re-read
                # the service instead of presenting the requested state as fact.
                try:
                    actual = self._client.live_ssh_status()
                except Exception:
                    actual = None
                self._results.put_nowait((actual, True))
        threading.Thread(target=work, name="installer-live-ssh", daemon=True).start()

    def drain(self) -> None:
        try:
            value, error = self._results.get_nowait()
        except queue.Empty:
            return
        self.snapshot = LiveSshSnapshot(
            self.snapshot.enabled if value is None else value, False, error
        )
