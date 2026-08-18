#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Sequence


DEFAULT_HOST = "greia-dev.local"
DEFAULT_USER = "greia"
DEFAULT_KEY = Path("out/greia-os-modern-amd64-dev-ssh-key")
DEFAULT_PASSWORD = "greia"
DEFAULT_KNOWN_HOSTS = Path.home() / ".greia" / "known_hosts"
_ACTIVITY_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
_LOG_SERVICE_CHOICES = (
    "all",
    "launcher",
    "installer",
    "parent",
    "ssh",
    "developer-remote",
    "network",
)


class RemoteError(RuntimeError):
    pass


class GreiaRemote:
    def __init__(
        self,
        *,
        host: str,
        user: str,
        key: Path,
        known_hosts: Path,
        password: str | None = None,
    ):
        self.host = host
        self.user = user
        self.key_path = key.expanduser().resolve()
        self.password = password
        self.known_hosts = known_hosts.expanduser().resolve()
        if self.password is None and not self.key_path.is_file():
            raise RemoteError(f"SSH private key not found: {self.key_path}")
        self.known_hosts.parent.mkdir(parents=True, exist_ok=True)

    @property
    def destination(self) -> str:
        return f"{self.user}@{self.host}"

    def ssh_base(self) -> list[str]:
        argv = ["ssh"]
        if self.password is not None:
            argv += ["-o", "BatchMode=no"]
        else:
            argv += [
                "-i",
                str(self.key_path),
                "-o",
                "BatchMode=yes",
            ]
        argv += [
            "-o",
            "StrictHostKeyChecking=accept-new",
            "-o",
            f"UserKnownHostsFile={self.known_hosts}",
            "-o",
            "ConnectTimeout=8",
            self.destination,
        ]
        return argv

    def scp_base(self) -> list[str]:
        argv = ["scp"]
        if self.password is not None:
            argv += ["-o", "BatchMode=no"]
        else:
            argv += ["-i", str(self.key_path), "-o", "BatchMode=yes"]
        argv += [
            "-o",
            "StrictHostKeyChecking=accept-new",
            "-o",
            f"UserKnownHostsFile={self.known_hosts}",
            "-o",
            "ConnectTimeout=8",
        ]
        return argv

    def devctl(
        self,
        *args: str,
        binary: bool = False,
        check: bool = True,
    ) -> subprocess.CompletedProcess[bytes] | subprocess.CompletedProcess[str]:
        command = shlex.join(["sudo", "-n", "/usr/local/sbin/greia-devctl", *args])
        completed = subprocess.run(
            [*self.ssh_base(), command],
            check=False,
            capture_output=True,
            text=not binary,
        )
        if check and completed.returncode != 0:
            stderr = (
                completed.stderr.decode("utf-8", errors="replace")
                if binary
                else completed.stderr
            )
            raise RemoteError(
                f"remote command failed with status {completed.returncode}: {stderr.strip()}"
            )
        return completed

    def status(self) -> str:
        completed = self.devctl("status")
        assert isinstance(completed.stdout, str)
        return completed.stdout

    def screenshot(self, output: Path) -> Path:
        completed = self.devctl("screenshot", binary=True)
        assert isinstance(completed.stdout, bytes)
        payload = completed.stdout
        if payload[:8] != b"\x89PNG\r\n\x1a\n":
            raise RemoteError("remote screenshot did not return PNG data")
        output = output.expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(payload)
        return output

    def logs(self, service: str, lines: int) -> str:
        completed = self.devctl("logs", "--service", service, "--lines", str(lines))
        assert isinstance(completed.stdout, str)
        return completed.stdout

    def snapshot(self, output_dir: Path, *, service: str = "all", lines: int = 500) -> Path:
        """Collect one agent-friendly local evidence snapshot from the target.

        Screenshot bytes are transferred directly over the existing authenticated
        SSH/devctl channel. Status and bounded logs are written beside the PNG so
        a local agent can inspect one self-contained observation without manual
        copying from the Greia machine.
        """

        if service not in _LOG_SERVICE_CHOICES:
            raise RemoteError(f"unknown log service group: {service}")
        if isinstance(lines, bool) or lines < 1 or lines > 5000:
            raise RemoteError("log line count must be between 1 and 5000")
        root = output_dir.expanduser().resolve()
        root.mkdir(parents=True, exist_ok=True)
        self.screenshot(root / "screen.png")
        (root / "status.json").write_text(self.status(), encoding="utf-8")
        (root / "logs.txt").write_text(self.logs(service, lines), encoding="utf-8")
        (root / "snapshot.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "host": self.host,
                    "user": self.user,
                    "captured_at_unix": int(time.time()),
                    "log_service": service,
                    "log_lines": lines,
                    "files": ["screen.png", "status.json", "logs.txt"],
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return root

    def restart_launcher(self) -> None:
        self.devctl("restart-launcher")

    def restart_installer(self) -> None:
        self.devctl("restart-installer")

    def key(self, keys: Sequence[str]) -> None:
        if not keys:
            raise RemoteError("at least one key expression is required")
        self.devctl("key", *keys)

    def mousemove(self, x: int, y: int) -> None:
        self.devctl("mousemove", str(x), str(y))

    def click(self, button: int = 1) -> None:
        self.devctl("click", str(button))

    def type_text(self, text: str) -> None:
        self.devctl("type", text)

    def deploy_activity(self, path: Path, *, replace_system: bool) -> str:
        source = path.expanduser().resolve(strict=True)
        if not source.is_dir() or not (source / "activity.toml").is_file():
            raise RemoteError(
                "deploy source must be an Activity directory containing activity.toml"
            )
        token = uuid.uuid4().hex
        remote_root = f"/var/lib/greia-admin/greia-dev-upload/{token}"
        self._ssh_user_command("mkdir", "-p", remote_root)
        try:
            completed = subprocess.run(
                [
                    *self.scp_base(),
                    "-r",
                    str(source) + "/.",
                    f"{self.destination}:{remote_root}/",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            if completed.returncode != 0:
                raise RemoteError(
                    f"Activity upload failed with status {completed.returncode}: "
                    f"{completed.stderr.strip()}"
                )
            args = ["deploy-activity", remote_root]
            if replace_system:
                args.append("--replace-system")
            result = self.devctl(*args)
            assert isinstance(result.stdout, str)
            return result.stdout
        finally:
            self._ssh_user_command("rm", "-rf", remote_root, check=False)

    def remove_activity(self, activity_id: str) -> None:
        _validate_activity_id(activity_id)
        self.devctl("remove-activity", activity_id)

    def restore_activity(self, activity_id: str) -> None:
        _validate_activity_id(activity_id)
        self.devctl("restore-activity", activity_id)

    def reboot(self) -> None:
        completed = self.devctl("reboot", check=False)
        if completed.returncode not in (0, 255):
            stderr = completed.stderr if isinstance(completed.stderr, str) else ""
            raise RemoteError(f"reboot request failed: {stderr.strip()}")

    def poweroff(self) -> None:
        completed = self.devctl("poweroff", check=False)
        if completed.returncode not in (0, 255):
            stderr = completed.stderr if isinstance(completed.stderr, str) else ""
            raise RemoteError(f"poweroff request failed: {stderr.strip()}")

    def wait_until_ready(self, timeout_seconds: int) -> None:
        if timeout_seconds < 1 or timeout_seconds > 1800:
            raise RemoteError("wait timeout must be between 1 and 1800 seconds")
        deadline = time.monotonic() + timeout_seconds
        last_error = "not attempted"
        while time.monotonic() < deadline:
            try:
                self.devctl("status")
                return
            except RemoteError as exc:
                last_error = str(exc)
                time.sleep(2)
        raise RemoteError(f"Greia did not become remotely ready: {last_error}")

    def shell(self) -> None:
        os.execvp("ssh", self.ssh_base())

    def _ssh_user_command(
        self, *args: str, check: bool = True
    ) -> subprocess.CompletedProcess[str]:
        completed = subprocess.run(
            [*self.ssh_base(), shlex.join(list(args))],
            check=False,
            capture_output=True,
            text=True,
        )
        if check and completed.returncode != 0:
            raise RemoteError(
                f"remote file-transfer preparation failed: {completed.stderr.strip()}"
            )
        return completed


def _validate_activity_id(value: str) -> None:
    if not _ACTIVITY_ID_RE.fullmatch(value):
        raise RemoteError("Activity ID is invalid")


def _add_log_options(parser: argparse.ArgumentParser, *, default_lines: int) -> None:
    parser.add_argument("--service", choices=_LOG_SERVICE_CHOICES, default="all")
    parser.add_argument("--lines", type=int, default=default_lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Control a Greia developer image over SSH"
    )
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--user", default=DEFAULT_USER)
    parser.add_argument("--key", type=Path, default=DEFAULT_KEY)
    parser.add_argument(
        "--password",
        default=None,
        help="Authenticate with the greia development password (greia/greia by default).",
    )
    parser.add_argument("--known-hosts", type=Path, default=DEFAULT_KNOWN_HOSTS)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status")
    screenshot = sub.add_parser("screenshot")
    screenshot.add_argument("output", type=Path)
    logs = sub.add_parser("logs")
    _add_log_options(logs, default_lines=300)
    snapshot = sub.add_parser("snapshot")
    snapshot.add_argument("output_dir", type=Path)
    _add_log_options(snapshot, default_lines=500)
    sub.add_parser("restart")
    sub.add_parser("restart-installer")

    key_parser = sub.add_parser("key")
    key_parser.add_argument("keys", nargs="+")
    move = sub.add_parser("mousemove")
    move.add_argument("x", type=int)
    move.add_argument("y", type=int)
    click = sub.add_parser("click")
    click.add_argument("button", type=int, nargs="?", default=1)
    type_parser = sub.add_parser("type")
    type_parser.add_argument("text")

    deploy = sub.add_parser("deploy")
    deploy.add_argument("activity", type=Path)
    deploy.add_argument("--replace-system", action="store_true")
    remove = sub.add_parser("remove")
    remove.add_argument("activity_id")
    restore = sub.add_parser("restore")
    restore.add_argument("activity_id")
    wait = sub.add_parser("wait")
    wait.add_argument("--timeout", type=int, default=120)
    sub.add_parser("reboot")
    sub.add_parser("poweroff")
    sub.add_parser("shell")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        remote = GreiaRemote(
            host=args.host,
            user=args.user,
            key=args.key,
            known_hosts=args.known_hosts,
            password=args.password,
        )
        if args.command == "status":
            sys.stdout.write(remote.status())
        elif args.command == "screenshot":
            path = remote.screenshot(args.output)
            print(path)
        elif args.command == "logs":
            sys.stdout.write(remote.logs(args.service, args.lines))
        elif args.command == "snapshot":
            root = remote.snapshot(
                args.output_dir,
                service=args.service,
                lines=args.lines,
            )
            print(root)
        elif args.command == "restart":
            remote.restart_launcher()
        elif args.command == "restart-installer":
            remote.restart_installer()
        elif args.command == "key":
            remote.key(args.keys)
        elif args.command == "mousemove":
            remote.mousemove(args.x, args.y)
        elif args.command == "click":
            remote.click(args.button)
        elif args.command == "type":
            remote.type_text(args.text)
        elif args.command == "deploy":
            sys.stdout.write(
                remote.deploy_activity(
                    args.activity, replace_system=args.replace_system
                )
            )
        elif args.command == "remove":
            remote.remove_activity(args.activity_id)
        elif args.command == "restore":
            remote.restore_activity(args.activity_id)
        elif args.command == "wait":
            remote.wait_until_ready(args.timeout)
            print("Greia developer remote is ready.")
        elif args.command == "reboot":
            remote.reboot()
        elif args.command == "poweroff":
            remote.poweroff()
        elif args.command == "shell":
            remote.shell()
        else:  # pragma: no cover
            raise RemoteError("unsupported command")
    except (OSError, RemoteError, subprocess.SubprocessError) as exc:
        print(f"greia_remote: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())