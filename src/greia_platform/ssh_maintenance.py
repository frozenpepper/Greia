from __future__ import annotations

import os
import json
import stat
import socket
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .parent_ssh_control import SOCKET_PATH


ENABLE_SSH_SCRIPT = Path("/usr/local/sbin/greia-enable-ssh")


@dataclass(frozen=True, slots=True)
class SshStatus:
    """Observable facts about the SSH maintenance service."""

    active: bool
    enabled: bool
    port: int
    username: str
    host_ip: str

    def public_dict(self) -> dict[str, object]:
        return {
            "active": self.active,
            "enabled": self.enabled,
            "port": self.port,
            "username": self.username,
            "host_ip": self.host_ip,
            "connection_string": (
                f"ssh {self.username}@{self.host_ip}"
                if self.host_ip and self.host_ip != "offline"
                else f"ssh {self.username}@<ip>"
            ),
        }


class SshMaintenanceProvider(Protocol):
    def status(self) -> SshStatus: ...

    def enable(self, public_key_content: str | None = None) -> SshStatus: ...

    def disable(self) -> SshStatus: ...


class SystemSshMaintenanceProvider:
    """Real system provider interacting with systemd and greia-enable-ssh."""

    def __init__(
        self,
        *,
        enable_script: Path = ENABLE_SSH_SCRIPT,
        username: str = "greia",
        port: int = 22,
    ) -> None:
        self._enable_script = enable_script
        self._username = username
        self._port = port

    def status(self) -> SshStatus:
        active = self._is_unit_active("ssh.service")
        enabled = self._is_unit_enabled("ssh.service")
        host_ip = _detect_lan_ip()
        return SshStatus(
            active=active,
            enabled=enabled,
            port=self._port,
            username=self._username,
            host_ip=host_ip,
        )

    def enable(self, public_key_content: str | None = None) -> SshStatus:
        if public_key_content and self._enable_script.is_file() and os.access(self._enable_script, os.X_OK):
            tmp = Path(f"/tmp/greia-ssh-key-{os.getpid()}.pub")
            try:
                tmp.write_text(public_key_content.strip() + "\n", encoding="utf-8")
                os.chmod(tmp, 0o600)
                subprocess.run(
                    [str(self._enable_script), str(tmp)],
                    check=True,
                    shell=False,
                    capture_output=True,
                )
            finally:
                tmp.unlink(missing_ok=True)
        else:
            subprocess.run(
                ["systemctl", "enable", "--now", "ssh.service"],
                check=False,
                shell=False,
                capture_output=True,
            )
        return self.status()

    def disable(self) -> SshStatus:
        subprocess.run(
            ["systemctl", "disable", "--now", "ssh.service"],
            check=False,
            shell=False,
            capture_output=True,
        )
        return self.status()

    @staticmethod
    def _is_unit_active(unit: str) -> bool:
        try:
            completed = subprocess.run(
                ["systemctl", "is-active", unit],
                check=False,
                shell=False,
                capture_output=True,
                text=True,
            )
            return completed.stdout.strip() == "active"
        except Exception:
            return False

    @staticmethod
    def _is_unit_enabled(unit: str) -> bool:
        try:
            completed = subprocess.run(
                ["systemctl", "is-enabled", unit],
                check=False,
                shell=False,
                capture_output=True,
                text=True,
            )
            return completed.stdout.strip() == "enabled"
        except Exception:
            return False


class ParentSocketSshMaintenanceProvider:
    """Use the installed, fixed-operation Parent SSH authority."""

    def __init__(self, path: Path = SOCKET_PATH) -> None:
        self.path = path

    def available(self) -> bool:
        try:
            return stat.S_ISSOCK(self.path.stat().st_mode) and os.access(self.path, os.W_OK)
        except OSError:
            return False

    def _request(self, operation: str) -> SshStatus:
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
                connection.settimeout(180)
                connection.connect(str(self.path))
                connection.sendall(operation.encode("ascii") + b"\n")
                response = bytearray()
                while b"\n" not in response and len(response) < 512:
                    part = connection.recv(512 - len(response))
                    if not part:
                        break
                    response.extend(part)
            payload = json.loads(response)
            if not isinstance(payload, dict) or payload.get("ok") is not True:
                raise ValueError("control request refused")
            if type(payload.get("active")) is not bool or type(payload.get("enabled")) is not bool:
                raise ValueError("invalid control response")
            return SshStatus(payload["active"], payload["enabled"], 22, "greia", _detect_lan_ip())
        except (OSError, ValueError, UnicodeError) as exc:
            raise RuntimeError("SSH maintenance is unavailable or failed") from exc

    def status(self) -> SshStatus:
        return self._request("STATUS")

    def enable(self, public_key_content: str | None = None) -> SshStatus:
        if public_key_content:
            raise ValueError("SSH public keys are not supported by this switch")
        return self._request("ENABLE")

    def disable(self) -> SshStatus:
        return self._request("DISABLE")


class MockSshMaintenanceProvider:
    """In-memory stateful provider for testing and development environments."""

    def __init__(
        self,
        *,
        active: bool = False,
        enabled: bool = False,
        username: str = "greia",
        port: int = 22,
        host_ip: str = "192.168.1.42",
    ) -> None:
        self._active = active
        self._enabled = enabled
        self._username = username
        self._port = port
        self._host_ip = host_ip

    def status(self) -> SshStatus:
        return SshStatus(
            active=self._active,
            enabled=self._enabled,
            port=self._port,
            username=self._username,
            host_ip=self._host_ip,
        )

    def enable(self, public_key_content: str | None = None) -> SshStatus:
        self._active = True
        self._enabled = True
        return self.status()

    def disable(self) -> SshStatus:
        self._active = False
        self._enabled = False
        return self.status()


class SshMaintenanceService:
    """Platform-level SSH maintenance service."""

    def __init__(self, provider: SshMaintenanceProvider | None = None) -> None:
        self._provider = provider or (
            SystemSshMaintenanceProvider()
            if Path("/etc/greia-os").exists() or Path("/usr/local/sbin/greia-enable-ssh").exists()
            else MockSshMaintenanceProvider()
        )

    def get_status(self) -> SshStatus:
        return self._provider.status()

    def enable(self, public_key_content: str | None = None) -> SshStatus:
        return self._provider.enable(public_key_content=public_key_content)

    def disable(self) -> SshStatus:
        return self._provider.disable()

    def toggle(self) -> SshStatus:
        current = self.get_status()
        if current.active or current.enabled:
            return self.disable()
        return self.enable()


def _detect_lan_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            # Connecting to a non-routable address to probe default route IP
            sock.connect(("10.255.255.255", 1))
            ip = sock.getsockname()[0]
            if ip and not ip.startswith("127."):
                return ip
    except Exception:
        pass
    try:
        return socket.gethostbyname(socket.gethostname())
    except Exception:
        return "offline"
