#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from r7_qemu_kmsdrm_acceptance import CommandRunner, MountedRawImage


SCHEMA_VERSION = 1
DEFAULT_EXPECTED_PROFILE = "modern-amd64-dev"
EXPECTED_PACKAGE_SET = "developer-remote"
_DEVELOPMENT_USER = "greia"
_DEVELOPMENT_PASSWORD = "greia"
_OPERATOR_USER = "greiaadmin"
_PROFILE_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
MARKER = Path("etc/greia-os/developer-remote")
DISPLAY_ENDPOINT = Path("etc/greia-os/developer-display.json")
ADMIN_HOME = Path("var/lib/greia-admin")
AUTHORIZED_KEYS = ADMIN_HOME / ".ssh/authorized_keys"
SUDOERS = Path("etc/sudoers.d/greia-developer-remote")
SSH_FLOOR = Path("etc/ssh/sshd_config.d/00-greia-security-floor.conf")
SSH_DROPIN = Path("etc/systemd/system/ssh.service.d/30-greia-developer-remote.conf")
LAUNCHER_DROPIN = Path(
    "etc/systemd/system/greia-launcher.service.d/30-greia-developer-activities.conf"
)
DEVELOPER_ACTIVITY_ROOT = "/var/lib/greia-developer/activities"

_DEVELOPMENT_SSH_FLOOR = (
    "# Development-image security floor (owner-approved greia/greia login).\n"
    "# Explicit developer provisioning rewrites the base closed floor so the\n"
    "# development/test SSH identity greia/greia works. root stays denied and\n"
    "# the operator key remains an additional automation path.\n"
    "PasswordAuthentication yes\n"
    "KbdInteractiveAuthentication yes\n"
    "PermitRootLogin no\n"
    "AuthenticationMethods publickey,password\n"
    "DenyUsers root\n"
    "AllowUsers greia greiaadmin\n"
)


class DeveloperImageProvisionError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ProvisionConfig:
    image: Path
    output_dir: Path
    expected_profile: str = DEFAULT_EXPECTED_PROFILE

    def __post_init__(self) -> None:
        if not _PROFILE_RE.fullmatch(self.expected_profile):
            raise DeveloperImageProvisionError("expected developer profile ID is invalid")


class DeveloperImageProvisioner:
    """Provision key-only SSH and bounded developer control into one dev image.

    The exact expected profile is supplied by the developer-image builder and is
    verified against the image's embedded profile manifest. Remote capability is
    additionally gated by the explicit ``developer-remote`` package set, so this
    tool cannot silently turn an ordinary release/profile image into a remote
    developer target.
    """

    def __init__(self, config: ProvisionConfig, *, runner: CommandRunner | None = None):
        self.config = config
        self.runner = runner or CommandRunner()

    @property
    def key_path(self) -> Path:
        return self.config.output_dir / f"greia-os-{self.config.expected_profile}-ssh-key"

    @property
    def public_key_path(self) -> Path:
        return self.key_path.with_suffix(self.key_path.suffix + ".pub")

    @property
    def report_path(self) -> Path:
        return (
            self.config.output_dir
            / f"greia-os-{self.config.expected_profile}-developer-remote.json"
        )

    def run(self) -> dict[str, object]:
        self._require_root()
        image = self.config.image.resolve()
        if not image.is_file() or image.stat().st_size == 0:
            raise DeveloperImageProvisionError(
                f"developer image is missing or empty: {image}"
            )
        self.config.output_dir.mkdir(parents=True, exist_ok=True)
        for path in (self.key_path, self.public_key_path, self.report_path):
            if path.exists():
                path.unlink()

        before_sha = _sha256_file(image)
        mountpoint = self.config.output_dir / ".greia-developer-image-mount"
        try:
            with MountedRawImage(
                image,
                mountpoint,
                read_only=False,
                runner=self.runner,
            ) as root:
                profile = self._validate_profile(root)
                uid, gid = self._admin_identity(root)
                fingerprint = self._provision_client_key(root, uid=uid, gid=gid)
                self._provision_development_identity(root)
                self._write_remote_policy(root, fingerprint=fingerprint)
                self._enable_units(root)
                self._validate_sshd_without_persisting_host_keys(root)
                self._validate_sudoers(root)
                self._remove_temporary_client_key(root)
                self._assert_no_host_keys(root)
        finally:
            if mountpoint.exists():
                try:
                    mountpoint.rmdir()
                except OSError:
                    pass

        after_sha = _sha256_file(image)
        if before_sha == after_sha:
            raise DeveloperImageProvisionError(
                "developer provisioning did not modify the image"
            )
        report = {
            "schema_version": SCHEMA_VERSION,
            "ok": True,
            "profile": self.config.expected_profile,
            "image": str(image),
            "image_sha256_before_provisioning": before_sha,
            "image_sha256": after_sha,
            "ssh_user": _DEVELOPMENT_USER,
            "ssh_password": _DEVELOPMENT_PASSWORD,
            "ssh_operator_user": _OPERATOR_USER,
            "ssh_operator_public_key": str(self.public_key_path.resolve()),
            "ssh_host_hint": "greia-dev.local",
            "ssh_private_key": str(self.key_path.resolve()),
            "ssh_public_key": str(self.public_key_path.resolve()),
            "password_authentication": True,
            "root_login": False,
            "ssh_host_keys_cloned": False,
            "ssh_host_keys_generated_on_first_boot": True,
            "passwordless_sudo_surface": "/usr/local/sbin/greia-devctl",
            "display_endpoint": {"user": "greiakid", "display": ":0"},
            "developer_activity_root": DEVELOPER_ACTIVITY_ROOT,
            "developer_activity_trust": "developer_unsigned",
            "production_profile_changed": False,
            "declared_profile": profile,
        }
        self.report_path.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        os.chmod(self.report_path, 0o600)
        return report

    def _validate_profile(self, root: Path) -> Mapping[str, object]:
        path = root / "etc/greia-os/image-profile.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise DeveloperImageProvisionError(
                f"cannot read image profile: {exc}"
            ) from exc
        profile = payload.get("profile")
        package_sets = payload.get("package_sets")
        expected = self.config.expected_profile
        if not isinstance(profile, dict) or profile.get("profile_id") != expected:
            raise DeveloperImageProvisionError(
                f"refusing to provision non-developer/unexpected profile; expected {expected!r}"
            )
        if not isinstance(package_sets, dict):
            raise DeveloperImageProvisionError(
                "image profile has no package-set declaration"
            )
        target_sets = package_sets.get("target")
        if not isinstance(target_sets, list) or EXPECTED_PACKAGE_SET not in target_sets:
            raise DeveloperImageProvisionError(
                "developer image is missing developer-remote package set"
            )
        return payload

    def _admin_identity(self, root: Path) -> tuple[int, int]:
        uid = int(
            self._chroot(root, ["id", "-u", "greiaadmin"], capture_output=True)
            .stdout.strip()
        )
        gid = int(
            self._chroot(root, ["id", "-g", "greiaadmin"], capture_output=True)
            .stdout.strip()
        )
        return uid, gid

    def _provision_client_key(self, root: Path, *, uid: int, gid: int) -> str:
        tmp_key = root / "tmp/greia-dev-client-key"
        tmp_key.parent.mkdir(parents=True, exist_ok=True)
        self._chroot(
            root,
            [
                "/usr/bin/ssh-keygen",
                "-q",
                "-t",
                "ed25519",
                "-N",
                "",
                "-C",
                "greia-development-image",
                "-f",
                "/tmp/greia-dev-client-key",
            ],
        )
        tmp_pub = Path(str(tmp_key) + ".pub")
        if not tmp_key.is_file() or not tmp_pub.is_file():
            raise DeveloperImageProvisionError(
                "ssh-keygen did not create the developer client key"
            )

        fingerprint = self._chroot(
            root,
            ["/usr/bin/ssh-keygen", "-lf", "/tmp/greia-dev-client-key.pub"],
            capture_output=True,
        ).stdout.strip()
        if not fingerprint:
            raise DeveloperImageProvisionError(
                "could not fingerprint generated developer key"
            )

        shutil.copyfile(tmp_key, self.key_path)
        shutil.copyfile(tmp_pub, self.public_key_path)
        os.chmod(self.key_path, 0o600)
        os.chmod(self.public_key_path, 0o644)

        ssh_dir = root / ADMIN_HOME / ".ssh"
        ssh_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(ssh_dir, 0o700)
        os.chown(ssh_dir, uid, gid)
        shutil.copyfile(tmp_pub, root / AUTHORIZED_KEYS)
        os.chmod(root / AUTHORIZED_KEYS, 0o600)
        os.chown(root / AUTHORIZED_KEYS, uid, gid)
        return fingerprint

    def _provision_development_identity(self, root: Path) -> None:
        """Enable the owner-approved greia/greia development login.

        Base images fail closed (greia locked, SSH off, key-only floor). This
        explicit developer provisioning step sets the greia password and rewrites
        the shared security floor so password + the operator key both work while
        root stays denied. The developer account is a real Linux account used for
        development/test access only; it does not create per-child Linux logins.
        """

        probe = self._chroot(
            root,
            ["/usr/bin/id", "-u", _DEVELOPMENT_USER],
            check=False,
            capture_output=True,
        )
        if probe.returncode != 0:
            self._chroot(
                root,
                [
                    "/usr/sbin/useradd",
                    "--create-home",
                    "--home-dir",
                    "/var/lib/greia",
                    "--shell",
                    "/bin/bash",
                    "--groups",
                    "sudo",
                    _DEVELOPMENT_USER,
                ],
            )
        self._chroot(
            root,
            ["/bin/bash", "-c", f"echo '{_DEVELOPMENT_USER}:{_DEVELOPMENT_PASSWORD}' | /usr/sbin/chpasswd"],
        )

        floor = root / SSH_FLOOR
        floor.parent.mkdir(parents=True, exist_ok=True)
        floor.write_text(_DEVELOPMENT_SSH_FLOOR, encoding="utf-8")
        os.chmod(floor, 0o644)

    def _write_remote_policy(self, root: Path, *, fingerprint: str) -> None:
        marker = root / MARKER
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(
            f"profile={self.config.expected_profile}\n"
            f"client_key_fingerprint={fingerprint}\n",
            encoding="utf-8",
        )
        os.chmod(marker, 0o600)

        endpoint = root / DISPLAY_ENDPOINT
        endpoint.write_text(
            json.dumps({"user": "greiakid", "display": ":0"}, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
        os.chmod(endpoint, 0o600)

        sudoers = root / SUDOERS
        sudoers.parent.mkdir(parents=True, exist_ok=True)
        sudoers.write_text(
            "# Development-image only: privileged operations stay inside greia-devctl.\n"
            "greiaadmin ALL=(root) NOPASSWD: /usr/local/sbin/greia-devctl\n",
            encoding="utf-8",
        )
        os.chmod(sudoers, 0o440)

        ssh_dropin = root / SSH_DROPIN
        ssh_dropin.parent.mkdir(parents=True, exist_ok=True)
        ssh_dropin.write_text(
            "[Unit]\n"
            "Requires=greia-developer-remote.service\n"
            "After=greia-developer-remote.service\n",
            encoding="utf-8",
        )
        os.chmod(ssh_dropin, 0o644)

        launcher_dropin = root / LAUNCHER_DROPIN
        launcher_dropin.parent.mkdir(parents=True, exist_ok=True)
        launcher_dropin.write_text(
            "[Service]\n"
            f"Environment=GREIA_DEVELOPER_ACTIVITY_ROOT={DEVELOPER_ACTIVITY_ROOT}\n",
            encoding="utf-8",
        )
        os.chmod(launcher_dropin, 0o644)

    def _enable_units(self, root: Path) -> None:
        self.runner.run(
            [
                "systemctl",
                f"--root={root}",
                "enable",
                "greia-developer-remote.service",
                "ssh.service",
            ]
        )

    def _validate_sshd_without_persisting_host_keys(self, root: Path) -> None:
        try:
            self._chroot(root, ["/usr/bin/ssh-keygen", "-A"])
            self._chroot(root, ["/usr/sbin/sshd", "-t"])
        finally:
            for path in (root / "etc/ssh").glob("ssh_host_*"):
                if path.is_file() or path.is_symlink():
                    path.unlink(missing_ok=True)

    def _validate_sudoers(self, root: Path) -> None:
        self._chroot(
            root,
            ["/usr/sbin/visudo", "-cf", "/etc/sudoers.d/greia-developer-remote"],
        )

    def _remove_temporary_client_key(self, root: Path) -> None:
        (root / "tmp/greia-dev-client-key").unlink(missing_ok=True)
        (root / "tmp/greia-dev-client-key.pub").unlink(missing_ok=True)

    @staticmethod
    def _assert_no_host_keys(root: Path) -> None:
        remaining = sorted(
            path.name for path in (root / "etc/ssh").glob("ssh_host_*") if path.exists()
        )
        if remaining:
            raise DeveloperImageProvisionError(
                "developer image retained SSH host identity: " + ", ".join(remaining)
            )

    def _chroot(
        self,
        root: Path,
        argv: Sequence[str],
        *,
        capture_output: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        return self.runner.run(
            ["chroot", str(root), *argv],
            capture_output=capture_output,
        )

    @staticmethod
    def _require_root() -> None:
        if os.geteuid() != 0:
            raise DeveloperImageProvisionError(
                "developer image provisioning must run as root"
            )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Provision Greia's development-only remote-control image"
    )
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument(
        "--expected-profile",
        default=DEFAULT_EXPECTED_PROFILE,
        help="exact profile ID embedded in the image (default: modern-amd64-dev)",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        report = DeveloperImageProvisioner(
            ProvisionConfig(
                image=args.image,
                output_dir=args.output_dir,
                expected_profile=args.expected_profile,
            )
        ).run()
    except DeveloperImageProvisionError as exc:
        print(f"developer image provisioning failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
