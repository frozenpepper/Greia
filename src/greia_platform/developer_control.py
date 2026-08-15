from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import stat
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from .activities import ActivityRegistry, ActivityValidationError, RuntimeCatalogue
from .developer_session import DeveloperDisplayEndpoint, DeveloperSessionError
from .trust import ActivitySource, PackageTrust


DEVELOPER_MARKER = Path("/etc/greia-os/developer-remote")
GREIA_ROOT = Path("/opt/greia-os")
SYSTEM_ACTIVITY_ROOT = GREIA_ROOT / "activities"
RUNTIME_CATALOGUE = GREIA_ROOT / "runtime/child-runtime.toml"
STATE_ROOT = Path("/var/lib/greia-developer")
DEVELOPER_ACTIVITY_ROOT = STATE_ROOT / "activities"
UPLOAD_ROOT = Path("/var/lib/greia-admin/greia-dev-upload")
STATE_FILE = STATE_ROOT / "deployments.json"
STAGING_ROOT = STATE_ROOT / "staging"
BACKUP_ROOT = STATE_ROOT / "backups"

_SERVICE_MAP: Mapping[str, tuple[str, ...]] = {
    "launcher": ("greia-launcher.service",),
    "installer": ("greia-installer.service",),
    "parent": ("greia-parent.service",),
    "ssh": ("ssh.service",),
    "developer-remote": ("greia-developer-remote.service",),
    "network": (
        "systemd-networkd.service",
        "systemd-resolved.service",
        "iwd.service",
        "avahi-daemon.service",
    ),
    "all": (
        "greia-launcher.service",
        "greia-installer.service",
        "greia-parent.service",
        "greia-developer-remote.service",
        "ssh.service",
        "systemd-networkd.service",
        "systemd-resolved.service",
        "iwd.service",
        "avahi-daemon.service",
    ),
}


class DeveloperControlError(RuntimeError):
    """Raised when a development-only control operation must fail closed."""


@dataclass(frozen=True, slots=True)
class DeploymentRecord:
    activity_id: str
    version: str
    kind: str
    original_backup: str | None
    deployed_at_unix: int

    def as_dict(self) -> dict[str, object]:
        return {
            "activity_id": self.activity_id,
            "version": self.version,
            "kind": self.kind,
            "original_backup": self.original_backup,
            "deployed_at_unix": self.deployed_at_unix,
        }


class DeveloperControl:
    """Root-side development controls exposed only by an explicitly marked image.

    SSH is only the transport. Privileged operations stay in this bounded command
    surface so remote tooling does not need to know Greia's internal filesystem or
    systemd implementation details. Ordinary remote Activity deployments live in a
    dedicated DEVELOPER_UNSIGNED source; only explicit system replacement touches
    the built-in Activity tree.
    """

    def __init__(self) -> None:
        self._require_root()
        self._require_developer_image()
        try:
            self.display_endpoint = DeveloperDisplayEndpoint.load()
        except DeveloperSessionError as exc:
            raise DeveloperControlError(str(exc)) from exc
        self._ensure_state_dirs()

    def status(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "developer_remote": True,
            "hostname": socket.gethostname(),
            "build_info": _read_key_value_file(Path("/etc/greia-os/build-info")),
            "services": {
                service: _service_state(service)
                for service in _SERVICE_MAP["all"]
            },
            "display_endpoint": {
                "user": self.display_endpoint.user,
                "display": self.display_endpoint.display,
            },
            "active_profile": _read_json_optional(
                Path("/run/greia-os/active-profile.json")
            ),
            "hardware": _read_json_optional(Path("/run/greia-hardware/status.json")),
            "developer_activity_root": str(DEVELOPER_ACTIVITY_ROOT),
            "deployments": self._load_state(),
        }

    def screenshot(self) -> bytes:
        argv = [
            *self.display_endpoint.runuser_prefix(),
            "PYGAME_HIDE_SUPPORT_PROMPT=1",
            "PYTHONPATH=/opt/greia-os/src",
            "PYTHONNOUSERSITE=1",
            "PYTHONDONTWRITEBYTECODE=1",
            "/usr/bin/python3",
            "-m",
            "greia_platform.developer_capture",
            "--display",
            self.display_endpoint.display,
        ]
        completed = subprocess.run(argv, check=False, capture_output=True)
        if completed.returncode != 0:
            detail = completed.stderr.decode("utf-8", errors="replace").strip()
            raise DeveloperControlError(
                f"screenshot capture failed with status {completed.returncode}: {detail}"
            )
        if completed.stdout[:8] != b"\x89PNG\r\n\x1a\n":
            raise DeveloperControlError("screenshot helper returned non-PNG output")
        return completed.stdout

    def logs(self, service_group: str, lines: int) -> str:
        if service_group not in _SERVICE_MAP:
            raise DeveloperControlError("unknown log service group")
        if isinstance(lines, bool) or lines < 1 or lines > 5000:
            raise DeveloperControlError("log line count must be between 1 and 5000")
        argv = ["journalctl", "--no-pager", "-n", str(lines), "-o", "short-iso"]
        for unit in _SERVICE_MAP[service_group]:
            argv.extend(["-u", unit])
        completed = subprocess.run(argv, check=False, capture_output=True, text=True)
        if completed.returncode != 0:
            raise DeveloperControlError(
                f"journalctl failed with status {completed.returncode}: {completed.stderr.strip()}"
            )
        return completed.stdout

    def restart_launcher(self) -> None:
        _run_checked(["systemctl", "restart", "greia-launcher.service"])

    def restart_installer(self) -> None:
        _run_checked(["systemctl", "restart", "greia-installer.service"])

    def reboot(self) -> None:
        _run_checked(["systemctl", "reboot"])

    def poweroff(self) -> None:
        _run_checked(["systemctl", "poweroff"])

    def deploy_activity(self, source: Path, *, replace_system: bool) -> DeploymentRecord:
        source = source.resolve(strict=True)
        if not source.is_dir():
            raise DeveloperControlError("Activity upload path must be a directory")
        if UPLOAD_ROOT.resolve() not in source.parents:
            raise DeveloperControlError(
                f"Activity source must be below the remote upload root {UPLOAD_ROOT}"
            )

        stage = STAGING_ROOT / f"deploy-{uuid.uuid4().hex}"
        shutil.copytree(source, stage, symlinks=True)
        current_backup: Path | None = None
        target: Path | None = None
        try:
            trust = (
                PackageTrust.BUILT_IN
                if replace_system
                else PackageTrust.DEVELOPER_UNSIGNED
            )
            registry = ActivityRegistry(
                [
                    ActivitySource(
                        STAGING_ROOT,
                        trust=trust,
                        source_id="greia-developer-upload",
                    )
                ],
                RuntimeCatalogue.load(RUNTIME_CATALOGUE),
            )
            manifest = registry.validate_package(stage)
            if not replace_system and manifest.requested_permissions:
                raise DeveloperControlError(
                    "ordinary remote developer deployments may not request privileged permissions; "
                    "use --replace-system only for deliberate built-in testing"
                )

            system_target = SYSTEM_ACTIVITY_ROOT / manifest.activity_id
            developer_target = DEVELOPER_ACTIVITY_ROOT / manifest.activity_id
            state = self._load_state()
            existing = state.get(manifest.activity_id)
            original_backup: str | None = None

            if replace_system:
                if developer_target.exists() or (
                    existing is not None and existing.get("kind") == "developer"
                ):
                    raise DeveloperControlError(
                        "remove the developer Activity before replacing a built-in with the same ID"
                    )
                target = system_target
                kind = "system-replacement"
                if existing is not None:
                    if existing.get("kind") != "system-replacement":
                        raise DeveloperControlError("deployment state kind mismatch")
                    value = existing.get("original_backup")
                    original_backup = value if isinstance(value, str) and value else None
                elif target.exists():
                    original = BACKUP_ROOT / (
                        f"{manifest.activity_id}-original-{int(time.time())}-{uuid.uuid4().hex}"
                    )
                    target.rename(original)
                    current_backup = original
                    original_backup = str(original)
                else:
                    raise DeveloperControlError(
                        f"{manifest.activity_id!r} is not an installed system Activity"
                    )
            else:
                if system_target.exists():
                    raise DeveloperControlError(
                        f"{manifest.activity_id!r} is an installed system Activity; "
                        "use --replace-system for deliberate built-in testing"
                    )
                if existing is not None and existing.get("kind") != "developer":
                    raise DeveloperControlError("deployment state kind mismatch")
                target = developer_target
                kind = "developer"

            if target.exists():
                previous = BACKUP_ROOT / (
                    f"{manifest.activity_id}-previous-{int(time.time())}-{uuid.uuid4().hex}"
                )
                target.rename(previous)
                current_backup = previous

            try:
                stage.rename(target)
            except Exception:
                if (
                    current_backup is not None
                    and current_backup.exists()
                    and not target.exists()
                ):
                    current_backup.rename(target)
                raise

            _make_tree_read_only(target)
            record = DeploymentRecord(
                activity_id=manifest.activity_id,
                version=manifest.version,
                kind=kind,
                original_backup=original_backup,
                deployed_at_unix=int(time.time()),
            )
            state[manifest.activity_id] = record.as_dict()
            self._write_state(state)

            if current_backup is not None and str(current_backup) != original_backup:
                shutil.rmtree(current_backup, ignore_errors=True)
            self.restart_launcher()
            return record
        except ActivityValidationError as exc:
            raise DeveloperControlError(f"Activity validation failed: {exc}") from exc
        finally:
            if stage.exists():
                shutil.rmtree(stage, ignore_errors=True)

    def remove_activity(self, activity_id: str) -> None:
        _validate_activity_id(activity_id)
        state = self._load_state()
        record = state.get(activity_id)
        if not isinstance(record, dict) or record.get("kind") != "developer":
            raise DeveloperControlError(
                "Activity is not an ordinary remote developer deployment"
            )
        target = DEVELOPER_ACTIVITY_ROOT / activity_id
        if target.exists():
            shutil.rmtree(target)
        state.pop(activity_id, None)
        self._write_state(state)
        self.restart_launcher()

    def restore_activity(self, activity_id: str) -> None:
        _validate_activity_id(activity_id)
        state = self._load_state()
        record = state.get(activity_id)
        if not isinstance(record, dict) or record.get("kind") != "system-replacement":
            raise DeveloperControlError("Activity has no original system backup to restore")
        backup_text = record.get("original_backup")
        if not isinstance(backup_text, str) or not backup_text:
            raise DeveloperControlError("system replacement record has no original backup")
        backup = Path(backup_text)
        if BACKUP_ROOT.resolve() not in backup.resolve().parents or not backup.is_dir():
            raise DeveloperControlError(
                "original Activity backup is missing or outside backup root"
            )
        target = SYSTEM_ACTIVITY_ROOT / activity_id
        if target.exists():
            shutil.rmtree(target)
        backup.rename(target)
        state.pop(activity_id, None)
        self._write_state(state)
        self.restart_launcher()

    def _ensure_state_dirs(self) -> None:
        for path, mode in (
            (STATE_ROOT, 0o755),
            (DEVELOPER_ACTIVITY_ROOT, 0o755),
            (STAGING_ROOT, 0o700),
            (BACKUP_ROOT, 0o700),
        ):
            path.mkdir(parents=True, exist_ok=True)
            os.chmod(path, mode)

    def _load_state(self) -> dict[str, dict[str, object]]:
        if not STATE_FILE.exists():
            return {}
        try:
            raw = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise DeveloperControlError(
                f"developer deployment state is invalid: {exc}"
            ) from exc
        if not isinstance(raw, dict):
            raise DeveloperControlError("developer deployment state root must be an object")
        result: dict[str, dict[str, object]] = {}
        for key, value in raw.items():
            if not isinstance(key, str) or not isinstance(value, dict):
                raise DeveloperControlError("developer deployment state is malformed")
            result[key] = value
        return result

    def _write_state(self, state: Mapping[str, Mapping[str, object]]) -> None:
        tmp = STATE_FILE.with_name(f".{STATE_FILE.name}.{uuid.uuid4().hex}.tmp")
        tmp.write_text(
            json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        os.chmod(tmp, 0o600)
        os.replace(tmp, STATE_FILE)

    @staticmethod
    def _require_root() -> None:
        if os.geteuid() != 0:
            raise DeveloperControlError(
                "greia-devctl must run as root through its sudo policy"
            )

    @staticmethod
    def _require_developer_image() -> None:
        if not DEVELOPER_MARKER.is_file():
            raise DeveloperControlError(
                "developer remote control is not enabled on this image"
            )


def _make_tree_read_only(root: Path) -> None:
    for path in [root, *root.rglob("*")]:
        try:
            mode = stat.S_IMODE(path.stat().st_mode)
            os.chmod(path, mode & ~0o222)
        except OSError as exc:
            raise DeveloperControlError(
                f"cannot seal deployed Activity path {path}: {exc}"
            ) from exc


def _validate_activity_id(value: str) -> None:
    if not value or len(value) > 128:
        raise DeveloperControlError("Activity ID is invalid")
    allowed_first = set("abcdefghijklmnopqrstuvwxyz0123456789")
    allowed_rest = allowed_first | set("._-")
    if value[0] not in allowed_first or any(ch not in allowed_rest for ch in value):
        raise DeveloperControlError("Activity ID contains unsupported characters")


def _read_key_value_file(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return result
    for line in lines:
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key and len(key) <= 128 and len(value) <= 4096:
            result[key] = value
    return result


def _read_json_optional(path: Path) -> object | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _service_state(service: str) -> str:
    completed = subprocess.run(
        ["systemctl", "is-active", service],
        check=False,
        capture_output=True,
        text=True,
    )
    state = completed.stdout.strip()
    return state if state else "unknown"


def _run_checked(argv: Sequence[str]) -> None:
    completed = subprocess.run(
        list(argv), check=False, capture_output=True, text=True
    )
    if completed.returncode != 0:
        raise DeveloperControlError(
            f"command failed ({' '.join(argv)}): {completed.stderr.strip()}"
        )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Greia development-image remote control"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    sub.add_parser("screenshot")
    logs = sub.add_parser("logs")
    logs.add_argument("--service", choices=sorted(_SERVICE_MAP), default="all")
    logs.add_argument("--lines", type=int, default=300)
    sub.add_parser("restart-launcher")
    sub.add_parser("restart-installer")
    deploy = sub.add_parser("deploy-activity")
    deploy.add_argument("path", type=Path)
    deploy.add_argument("--replace-system", action="store_true")
    remove = sub.add_parser("remove-activity")
    remove.add_argument("activity_id")
    restore = sub.add_parser("restore-activity")
    restore.add_argument("activity_id")
    sub.add_parser("reboot")
    sub.add_parser("poweroff")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        control = DeveloperControl()
        if args.command == "status":
            print(json.dumps(control.status(), indent=2, sort_keys=True))
        elif args.command == "screenshot":
            sys.stdout.buffer.write(control.screenshot())
            sys.stdout.buffer.flush()
        elif args.command == "logs":
            sys.stdout.write(control.logs(args.service, args.lines))
        elif args.command == "restart-launcher":
            control.restart_launcher()
        elif args.command == "restart-installer":
            control.restart_installer()
        elif args.command == "deploy-activity":
            record = control.deploy_activity(
                args.path, replace_system=args.replace_system
            )
            print(json.dumps(record.as_dict(), indent=2, sort_keys=True))
        elif args.command == "remove-activity":
            control.remove_activity(args.activity_id)
        elif args.command == "restore-activity":
            control.restore_activity(args.activity_id)
        elif args.command == "reboot":
            control.reboot()
        elif args.command == "poweroff":
            control.poweroff()
        else:  # pragma: no cover - argparse guarantees the command set.
            raise DeveloperControlError("unsupported command")
    except DeveloperControlError as exc:
        print(f"greia-devctl: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
