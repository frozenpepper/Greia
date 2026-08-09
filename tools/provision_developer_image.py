#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from r7_qemu_kmsdrm_acceptance import CommandRunner, MountedRawImage


SCHEMA_VERSION = 1
EXPECTED_PROFILE = "modern-amd64-dev"
EXPECTED_PACKAGE_SET = "developer-remote"
MARKER = Path("etc/greia-os/developer-remote")
ADMIN_HOME = Path("var/lib/greia-admin")
AUTHORIZED_KEYS = ADMIN_HOME / ".ssh/authorized_keys"
SUDOERS = Path("etc/sudoers.d/greia-developer-remote")
SSH_DROPIN = Path("etc/systemd/system/ssh.service.d/30-greia-developer-remote.conf")


class DeveloperImageProvisionError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ProvisionConfig:
    image: Path
    output_dir: Path


class DeveloperImageProvisioner:
    """Provision key-only SSH and bounded developer control into one dev image."""

    def __init__(self, config: ProvisionConfig, *, runner: CommandRunner | None = None):
        self.config = config
        self.runner = runner or CommandRunner()

    @property
    def key_path(self) -> Path:
        return self.config.output_dir / f"greia-os-{EXPECTED_PROFILE}-ssh-key"

    @property
    def public_key_path(self) -> Path:
        return self.key_path.with_suffix(self.key_path.suffix + ".pub")

    @property
    def report_path(self) -> Path:
        return self.config.output_dir / f"greia-os-{EXPECTED_PROFILE}-developer-remote.json"

    def run(self) -> dict[str, object]:
        self._require_root()
        image = self.config.image.resolve()
        if not image.is_file() or image.stat().st_size == 0:
            raise DeveloperImageProvisionError(f"developer image is missing or empty: {image}")
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
                self._write_remote_policy(root, fingerprint=fingerprint)
                self._enable_units(root)
                self._validate_sshd(root)
                self._validate_sudoers(root)
                self._remove_temporary_client_key(root)
        finally:
            if mountpoint.exists():
                try:
                    mountpoint.rmdir()
                except OSError:
                    pass

        after_sha = _sha256_file(image)
        if before_sha == after_sha:
            raise DeveloperImageProvisionError("developer provisioning did not modify the image")
        report = {
            "schema_version": SCHEMA_VERSION,
            "ok": True,
            "profile": EXPECTED_PROFILE,
            "image": str(image),
            "image_sha256_before_provisioning": before_sha,
            "image_sha256": after_sha,
            "ssh_user": "greiaadmin",
            "ssh_host_hint": "greia-dev.local",
            "ssh_private_key": str(self.key_path.resolve()),
            "ssh_public_key": str(self.public_key_path.resolve()),
            "password_authentication": False,
            "root_login": False,
            "ssh_host_keys_cloned": False,
            "ssh_host_keys_generated_on_first_boot": True,
            "passwordless_sudo_surface": "/usr/local/sbin/greia-devctl",
            "production_profile_changed": False,
            "declared_profile": profile,
        }
        self.report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.chmod(self.report_path, 0o600)
        return report

    def _validate_profile(self, root: Path) -> Mapping[str, object]:
        path = root / "etc/greia-os/image-profile.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise DeveloperImageProvisionError(f"cannot read image profile: {exc}") from exc
        profile = payload.get("profile")
        package_sets = payload.get("package_sets")
        if not isinstance(profile, dict) or profile.get("profile_id") != EXPECTED_PROFILE:
            raise DeveloperImageProvisionError(
                f"refusing to provision non-developer profile; expected {EXPECTED_PROFILE!r}"
            )
        if not isinstance(package_sets, dict):
            raise DeveloperImageProvisionError("image profile has no package-set declaration")
        target_sets = package_sets.get("target")
        if not isinstance(target_sets, list) or EXPECTED_PACKAGE_SET not in target_sets:
            raise DeveloperImageProvisionError("developer image is missing developer-remote package set")
        return payload

    def _admin_identity(self, root: Path) -> tuple[int, int]:
        uid = int(self._chroot(root, ["id", "-u", "greiaadmin"], capture_output=True).stdout.strip())
        gid = int(self._chroot(root, ["id", "-g", "greiaadmin"], capture_output=True).stdout.strip())
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
            raise DeveloperImageProvisionError("ssh-keygen did not create the developer client key")

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

        completed = self.runner.run(
            ["ssh-keygen", "-lf", str(self.public_key_path)],
            capture_output=True,
        )
        fingerprint = completed.stdout.strip()
        if not fingerprint:
            raise DeveloperImageProvisionError("could not fingerprint generated developer key")
        return fingerprint

    def _write_remote_policy(self, root: Path, *, fingerprint: str) -> None:
        marker = root / MARKER
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(
            "profile=modern-amd64-dev\n"
            f"client_key_fingerprint={fingerprint}\n",
            encoding="utf-8",
        )
        os.chmod(marker, 0o600)

        sudoers = root / SUDOERS
        sudoers.parent.mkdir(parents=True, exist_ok=True)
        sudoers.write_text(
            "# Development-image only: privileged operations stay inside greia-devctl.\n"
            "greiaadmin ALL=(root) NOPASSWD: /usr/local/sbin/greia-devctl\n",
            encoding="utf-8",
        )
        os.chmod(sudoers, 0o440)

        dropin = root / SSH_DROPIN
        dropin.parent.mkdir(parents=True, exist_ok=True)
        dropin.write_text(
            "[Unit]\n"
            "Requires=greia-developer-remote.service\n"
            "After=greia-developer-remote.service\n",
            encoding="utf-8",
        )
        os.chmod(dropin, 0o644)

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

    def _validate_sshd(self, root: Path) -> None:
        self._chroot(root, ["/usr/sbin/sshd", "-t"])

    def _validate_sudoers(self, root: Path) -> None:
        self._chroot(root, ["/usr/sbin/visudo", "-cf", "/etc/sudoers.d/greia-developer-remote"])

    def _remove_temporary_client_key(self, root: Path) -> None:
        (root / "tmp/greia-dev-client-key").unlink(missing_ok=True)
        (root / "tmp/greia-dev-client-key.pub").unlink(missing_ok=True)

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
            raise DeveloperImageProvisionError("developer image provisioning must run as root")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Provision Greia's development-only remote-control image")
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        report = DeveloperImageProvisioner(
            ProvisionConfig(image=args.image, output_dir=args.output_dir)
        ).run()
    except DeveloperImageProvisionError as exc:
        print(f"developer image provisioning failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
