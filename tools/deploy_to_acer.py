#!/usr/bin/env python3
"""Deploy Greia repository updates to target hardware (Acer) via SSH."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import time
import pexpect

REPO_ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_PATH = REPO_ROOT / "tmp" / "greia-deploy.tar.gz"
HOST = "greia-dev.local"
USER = "greia"
PASSWORD = "greia"
KNOWN_HOSTS = Path.home() / ".greia" / "known_hosts"
REMOTE_TAR = "/var/lib/greia/greia-deploy.tar.gz"
DEFAULT_SSH_TIMEOUT_SECONDS = 60
DEPLOY_EXTRACT_TIMEOUT_SECONDS = 180


def run_ssh_cmd(
    cmd_str: str,
    timeout: int = DEFAULT_SSH_TIMEOUT_SECONDS,
) -> tuple[int, str]:
    args = [
        "-o", "StrictHostKeyChecking=accept-new",
        "-o", f"UserKnownHostsFile={KNOWN_HOSTS}",
        f"{USER}@{HOST}",
        cmd_str,
    ]
    child = pexpect.spawn("ssh", args, encoding="utf-8", timeout=timeout)
    idx = child.expect(["password:", "Password:", pexpect.EOF, pexpect.TIMEOUT])
    if idx in (0, 1):
        child.sendline(PASSWORD)
        child.expect(pexpect.EOF)
    output = child.before
    child.close()
    return child.exitstatus or 0, output


def run_scp(src: Path, dest_path: str, timeout: int = 180) -> int:
    args = [
        "-o", "StrictHostKeyChecking=accept-new",
        "-o", f"UserKnownHostsFile={KNOWN_HOSTS}",
        str(src),
        f"{USER}@{HOST}:{dest_path}",
    ]
    child = pexpect.spawn("scp", args, encoding="utf-8", timeout=timeout)
    idx = child.expect(["password:", "Password:", pexpect.EOF, pexpect.TIMEOUT])
    if idx in (0, 1):
        child.sendline(PASSWORD)
        child.expect(pexpect.EOF)
    output = child.before
    child.close()
    print("   SCP progress/status:", output.strip()[-120:] if output else "done")
    return child.exitstatus or 0


def main() -> int:
    print(f"1. Creating clean deployment bundle from {REPO_ROOT}...")
    ARCHIVE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if ARCHIVE_PATH.exists():
        ARCHIVE_PATH.unlink()

    # Create tarball without macOS AppleDouble resource forks (._* files)
    env = dict(os.environ)
    env["COPYFILE_DISABLE"] = "1"
    cmd = [
        "tar",
        "--exclude=.git",
        "--exclude=__pycache__",
        "--exclude=*.pyc",
        "--exclude=.DS_Store",
        "--exclude=._*",
        "--exclude=out",
        "--exclude=tmp",
        "-czf",
        str(ARCHIVE_PATH),
        "-C",
        str(REPO_ROOT),
        "activities",
        "src",
        "assets",
        "runtime",
        "docs",
        "tests",
        "tools",
        "AGENTS.md",
        "HANDOVER.md",
        "Makefile",
        "README.md",
        "SETUP.md",
        "VERSION",
    ]
    subprocess.run(cmd, env=env, check=True)
    size_mb = ARCHIVE_PATH.stat().st_size / (1024 * 1024)
    print(f"   Bundle size: {size_mb:.2f} MB")

    print(f"2. Uploading bundle to {USER}@{HOST}:{REMOTE_TAR}...")
    scp_status = run_scp(ARCHIVE_PATH, REMOTE_TAR)
    if scp_status != 0:
        print(f"   ERROR: SCP failed with exit status {scp_status}")
        return 1
    print("   Upload complete.")

    print("3. Extracting files to /opt/greia-os/ on target device...")
    extract_cmd = (
        f"echo greia | sudo -S tar -xzf {REMOTE_TAR} -C /opt/greia-os/ "
        f"&& echo greia | sudo -S find /opt/greia-os -name '._*' -delete "
        f"&& echo greia | sudo -S chown -R greiakid:greiakid /opt/greia-os/"
    )
    # The reference Atom N270 has measured this extraction/chown operation
    # beyond 60 seconds for a ~110 MB developer bundle. Keep ordinary SSH
    # probes bounded at 60s, but give this known slow hardware operation the
    # measured 180s acceptance window so operators never patch the tool after
    # freezing an evidence SHA.
    status, out = run_ssh_cmd(
        extract_cmd,
        timeout=DEPLOY_EXTRACT_TIMEOUT_SECONDS,
    )
    if status != 0:
        print(f"   ERROR: Extraction failed with status {status}: {out}")
        return 1
    print("   Extraction complete.")

    print("4. Verifying activity files in /opt/greia-os/activities/labirinto_magico/...")
    check_cmd = "ls -la /opt/greia-os/activities/labirinto_magico/"
    status, check_out = run_ssh_cmd(check_cmd)
    print("   Files present on target:")
    for line in check_out.strip().split("\n"):
        if any(k in line for k in ("maze_", "main.py", "activity.toml")):
            print("    ", line.strip())

    print("5. Restarting greia-launcher service...")
    restart_cmd = "echo greia | sudo -S systemctl restart greia-launcher"
    status, out = run_ssh_cmd(restart_cmd)
    print("   Service restarted.")

    time.sleep(3.0)

    print("6. Verifying target hardware status...")
    status_cmd = "echo greia | sudo -S /usr/local/sbin/greia-devctl status"
    status, status_out = run_ssh_cmd(status_cmd)
    print("   Target status:")
    print(status_out)

    print("Deployment completed successfully!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
