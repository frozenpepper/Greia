#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_PROFILE = "modern-amd64-dev"
LIVE_HOSTNAME = "greia-installer-dev"
SSH_CONFIG_SOURCE = (
    PROJECT_ROOT / "build/overlay/etc/ssh/sshd_config.d/20-greia-parent.conf"
)
DEVCTL_SOURCE = PROJECT_ROOT / "build/overlay/usr/local/sbin/greia-devctl"
PREPARE_SOURCE = (
    PROJECT_ROOT / "build/overlay/usr/local/lib/greia-os/prepare-developer-remote"
)


class DeveloperInstallerProvisionError(RuntimeError):
    pass


class CommandRunner:
    def run(
        self,
        argv: Sequence[str],
        *,
        check: bool = True,
        capture_output: bool = False,
        text: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            list(argv),
            check=check,
            capture_output=capture_output,
            text=text,
        )


@dataclass(frozen=True, slots=True)
class ProvisionConfig:
    root: Path
    public_key: Path
    report: Path
    profile: str = EXPECTED_PROFILE


class DeveloperInstallerProvisioner:
    """Enable bounded remote operation in the explicit developer live installer."""

    def __init__(
        self,
        config: ProvisionConfig,
        *,
        runner: CommandRunner | None = None,
    ) -> None:
        self.config = config
        self.runner = runner or CommandRunner()

    def run(self) -> dict[str, object]:
        self._require_root()
        root = self.config.root.resolve()
        public_key = self.config.public_key.resolve()
        if self.config.profile != EXPECTED_PROFILE:
            raise DeveloperInstallerProvisionError(
                f"refusing live remote provisioning for profile {self.config.profile!r}"
            )
        if not root.is_dir() or not (root / "etc").is_dir():
            raise DeveloperInstallerProvisionError(f"invalid live root: {root}")
        if not public_key.is_file() or public_key.stat().st_size == 0:
            raise DeveloperInstallerProvisionError(
                f"developer SSH public key is missing: {public_key}"
            )
        self._require_installed_tools(root)
        uid, gid = self._ensure_admin_user(root)
        self._install_authorized_key(root, public_key, uid=uid, gid=gid)
        self._install_developer_helpers(root)
        self._write_developer_policy(root)
        self._write_network_policy(root)
        self._write_hostname(root)
        self._enable_services(root)
        self._validate_sudoers(root)
        self._validate_sshd_without_persisting_host_keys(root)
        self._assert_no_host_keys(root)

        report = {
            "schema_version": 1,
            "ok": True,
            "profile": EXPECTED_PROFILE,
            "mode": "live-installer",
            "hostname": LIVE_HOSTNAME,
            "ssh_host_hint": f"{LIVE_HOSTNAME}.local",
            "ssh_user": "greiaadmin",
            "ssh_public_key_source": str(public_key),
            "password_authentication": False,
            "root_login": False,
            "ssh_host_keys_cloned": False,
            "ssh_host_keys_generated_on_boot": True,
            "display_endpoint": {"user": "root", "display": ":0"},
            "remote_graphical_installer": True,
            "unattended_destructive_install": False,
            "wired_dhcp_enabled": True,
            "mdns_enabled": True,
        }
        self.config.report.parent.mkdir(parents=True, exist_ok=True)
        self.config.report.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        os.chmod(self.config.report, 0o600)
        return report

    def _require_installed_tools(self, root: Path) -> None:
        required = (
            "usr/sbin/sshd",
            "usr/bin/ssh-keygen",
            "usr/bin/sudo",
            "usr/sbin/visudo",
            "usr/bin/xdotool",
            "usr/bin/python3",
        )
        missing = [path for path in required if not (root / path).is_file()]
        if missing:
            raise DeveloperInstallerProvisionError(
                "live installer developer packages are incomplete: " + ", ".join(missing)
            )
        self._chroot(root, ["/usr/bin/python3", "-c", "from PIL import ImageGrab"])

    def _ensure_admin_user(self, root: Path) -> tuple[int, int]:
        probe = self._chroot(
            root,
            ["/usr/bin/id", "-u", "greiaadmin"],
            check=False,
            capture_output=True,
        )
        if probe.returncode != 0:
            self._chroot(
                root,
                [
                    "/usr/sbin/useradd",
                    "--home-dir",
                    "/var/lib/greia-admin",
                    "--create-home",
                    "--shell",
                    "/bin/bash",
                    "greiaadmin",
                ],
            )
        self._chroot(root, ["/usr/bin/passwd", "--lock", "greiaadmin"])
        uid = int(
            self._chroot(
                root,
                ["/usr/bin/id", "-u", "greiaadmin"],
                capture_output=True,
            ).stdout.strip()
        )
        gid = int(
            self._chroot(
                root,
                ["/usr/bin/id", "-g", "greiaadmin"],
                capture_output=True,
            ).stdout.strip()
        )
        return uid, gid

    def _install_authorized_key(
        self,
        root: Path,
        public_key: Path,
        *,
        uid: int,
        gid: int,
    ) -> None:
        ssh_dir = root / "var/lib/greia-admin/.ssh"
        ssh_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(ssh_dir, 0o700)
        os.chown(ssh_dir, uid, gid)
        authorized = ssh_dir / "authorized_keys"
        shutil.copyfile(public_key, authorized)
        os.chmod(authorized, 0o600)
        os.chown(authorized, uid, gid)

    def _install_developer_helpers(self, root: Path) -> None:
        ssh_config = root / "etc/ssh/sshd_config.d/20-greia-parent.conf"
        ssh_config.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SSH_CONFIG_SOURCE, ssh_config)
        os.chmod(ssh_config, 0o644)

        devctl = root / "usr/local/sbin/greia-devctl"
        devctl.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(DEVCTL_SOURCE, devctl)
        os.chmod(devctl, 0o755)

        prepare = root / "usr/local/lib/greia-os/prepare-developer-remote"
        prepare.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(PREPARE_SOURCE, prepare)
        os.chmod(prepare, 0o755)

    def _write_developer_policy(self, root: Path) -> None:
        greia = root / "etc/greia-os"
        greia.mkdir(parents=True, exist_ok=True)
        marker = greia / "developer-remote"
        marker.write_text(
            "profile=modern-amd64-dev\nmode=live-installer\n",
            encoding="utf-8",
        )
        os.chmod(marker, 0o600)
        endpoint = greia / "developer-display.json"
        endpoint.write_text(
            json.dumps({"user": "root", "display": ":0"}, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.chmod(endpoint, 0o600)

        sudoers = root / "etc/sudoers.d/greia-developer-remote"
        sudoers.parent.mkdir(parents=True, exist_ok=True)
        sudoers.write_text(
            "greiaadmin ALL=(root) NOPASSWD: /usr/local/sbin/greia-devctl\n",
            encoding="utf-8",
        )
        os.chmod(sudoers, 0o440)

        service = root / "etc/systemd/system/greia-developer-remote.service"
        service.parent.mkdir(parents=True, exist_ok=True)
        service.write_text(
            "[Unit]\n"
            "Description=Greia live-installer developer remote preparation\n"
            "ConditionPathExists=/etc/greia-os/developer-remote\n"
            "After=local-fs.target\n"
            "Before=ssh.service\n\n"
            "[Service]\n"
            "Type=oneshot\n"
            "ExecStart=/bin/sh /usr/local/lib/greia-os/prepare-developer-remote\n"
            "RemainAfterExit=yes\n\n"
            "[Install]\n"
            "WantedBy=multi-user.target\n",
            encoding="utf-8",
        )
        os.chmod(service, 0o644)

        ssh_dropin = root / "etc/systemd/system/ssh.service.d/30-greia-developer-remote.conf"
        ssh_dropin.parent.mkdir(parents=True, exist_ok=True)
        ssh_dropin.write_text(
            "[Unit]\n"
            "Requires=greia-developer-remote.service\n"
            "After=greia-developer-remote.service\n",
            encoding="utf-8",
        )
        os.chmod(ssh_dropin, 0o644)

    def _write_network_policy(self, root: Path) -> None:
        network = root / "etc/systemd/network/20-greia-developer-ethernet.network"
        network.parent.mkdir(parents=True, exist_ok=True)
        network.write_text(
            "[Match]\n"
            "Type=ether\n\n"
            "[Network]\n"
            "DHCP=yes\n"
            "IPv6AcceptRA=yes\n"
            "MulticastDNS=yes\n",
            encoding="utf-8",
        )
        os.chmod(network, 0o644)

        resolved = root / "etc/systemd/resolved.conf.d/20-greia-developer.conf"
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text("[Resolve]\nMulticastDNS=yes\n", encoding="utf-8")
        os.chmod(resolved, 0o644)

        resolv_conf = root / "etc/resolv.conf"
        if resolv_conf.exists() or resolv_conf.is_symlink():
            resolv_conf.unlink()
        resolv_conf.symlink_to("../run/systemd/resolve/stub-resolv.conf")

    def _write_hostname(self, root: Path) -> None:
        (root / "etc/hostname").write_text(LIVE_HOSTNAME + "\n", encoding="utf-8")
        (root / "etc/hosts").write_text(
            "127.0.0.1 localhost\n"
            f"127.0.1.1 {LIVE_HOSTNAME}\n"
            "::1 localhost ip6-localhost ip6-loopback\n",
            encoding="utf-8",
        )

    def _enable_services(self, root: Path) -> None:
        self.runner.run(
            [
                "systemctl",
                f"--root={root}",
                "enable",
                "greia-developer-remote.service",
                "ssh.service",
                "systemd-networkd.service",
                "systemd-resolved.service",
                "iwd.service",
                "avahi-daemon.service",
            ]
        )

    def _validate_sudoers(self, root: Path) -> None:
        self._chroot(
            root,
            ["/usr/sbin/visudo", "-cf", "/etc/sudoers.d/greia-developer-remote"],
        )

    def _validate_sshd_without_persisting_host_keys(self, root: Path) -> None:
        try:
            self._chroot(root, ["/usr/bin/ssh-keygen", "-A"])
            self._chroot(root, ["/usr/sbin/sshd", "-t"])
        finally:
            for path in (root / "etc/ssh").glob("ssh_host_*"):
                if path.is_file() or path.is_symlink():
                    path.unlink(missing_ok=True)

    @staticmethod
    def _assert_no_host_keys(root: Path) -> None:
        remaining = [
            path.name for path in (root / "etc/ssh").glob("ssh_host_*") if path.exists()
        ]
        if remaining:
            raise DeveloperInstallerProvisionError(
                "live installer retained SSH host identity: " + ", ".join(sorted(remaining))
            )

    def _chroot(
        self,
        root: Path,
        argv: Sequence[str],
        *,
        check: bool = True,
        capture_output: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        return self.runner.run(
            ["chroot", str(root), *argv],
            check=check,
            capture_output=capture_output,
        )

    @staticmethod
    def _require_root() -> None:
        if os.geteuid() != 0:
            raise DeveloperInstallerProvisionError(
                "developer live-installer provisioning must run as root"
            )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Provision bounded remote control into Greia's developer live installer"
    )
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--public-key", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--profile", default=EXPECTED_PROFILE)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        report = DeveloperInstallerProvisioner(
            ProvisionConfig(
                root=args.root,
                public_key=args.public_key,
                report=args.report,
                profile=args.profile,
            )
        ).run()
    except DeveloperInstallerProvisionError as exc:
        print(f"developer live-installer provisioning failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
