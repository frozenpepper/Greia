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


def run_ssh_cmd(cmd_str: str, timeout: int = 30) -> str:
    ssh_cmd = (
        f"ssh -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile={KNOWN_HOSTS} "
        f"{USER}@{HOST} {cmd_str}"
    )
    child = pexpect.spawn(ssh_cmd, encoding="utf-8", timeout=timeout)
    idx = child.expect(["password:", "Password:", pexpect.EOF, pexpect.TIMEOUT])
    if idx in (0, 1):
        child.sendline(PASSWORD)
        child.expect(pexpect.EOF)
    return child.before


def run_scp(src: Path, dest_path: str, timeout: int = 60) -> None:
    scp_cmd = (
        f"scp -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile={KNOWN_HOSTS} "
        f"{src} {USER}@{HOST}:{dest_path}"
    )
    child = pexpect.spawn(scp_cmd, encoding="utf-8", timeout=timeout)
    idx = child.expect(["password:", "Password:", pexpect.EOF, pexpect.TIMEOUT])
    if idx in (0, 1):
        child.sendline(PASSWORD)
        child.expect(pexpect.EOF)


def main() -> int:
    print(f"1. Creating deployment bundle from {REPO_ROOT}...")
    ARCHIVE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if ARCHIVE_PATH.exists():
        ARCHIVE_PATH.unlink()

    # Create tarball of repository contents excluding caches and git
    cmd = [
        "tar",
        "--exclude=.git",
        "--exclude=__pycache__",
        "--exclude=*.pyc",
        "--exclude=.DS_Store",
        "--exclude=out",
        "--exclude=tmp",
        "-czf",
        str(ARCHIVE_PATH),
        "-C",
        str(REPO_ROOT),
        ".",
    ]
    subprocess.run(cmd, check=True)
    size_mb = ARCHIVE_PATH.stat().st_size / (1024 * 1024)
    print(f"   Bundle size: {size_mb:.2f} MB")

    print(f"2. Uploading bundle to {USER}@{HOST}:/tmp/greia-deploy.tar.gz...")
    run_scp(ARCHIVE_PATH, "/tmp/greia-deploy.tar.gz")
    print("   Upload complete.")

    print("3. Extracting files to /opt/greia-os/ on target device...")
    extract_cmd = (
        "\"echo greia | sudo -S tar -xzf /tmp/greia-deploy.tar.gz -C /opt/greia-os/ "
        "&& echo greia | sudo -S chown -R greiakid:greiakid /opt/greia-os/\""
    )
    out = run_ssh_cmd(extract_cmd)
    print("   Extraction complete.")

    print("4. Restarting greia-launcher service...")
    restart_cmd = "\"echo greia | sudo -S systemctl restart greia-launcher\""
    out = run_ssh_cmd(restart_cmd)
    print("   Service restarted.")

    time.sleep(3.0)

    print("5. Verifying target hardware status...")
    status_cmd = "\"echo greia | sudo -S /usr/local/sbin/greia-devctl status\""
    status_out = run_ssh_cmd(status_cmd)
    print("   Target status:")
    print(status_out)

    print("6. Capturing screenshot from physical hardware...")
    screenshot_cmd = "\"echo greia | sudo -S /usr/local/sbin/greia-devctl screenshot > /tmp/acer_screen.png\""
    run_ssh_cmd(screenshot_cmd)
    
    local_screenshot = REPO_ROOT / "tmp" / "acer_screen_live.png"
    scp_fetch = (
        f"scp -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile={KNOWN_HOSTS} "
        f"{USER}@{HOST}:/tmp/acer_screen.png {local_screenshot}"
    )
    child = pexpect.spawn(scp_fetch, encoding="utf-8", timeout=30)
    idx = child.expect(["password:", "Password:", pexpect.EOF, pexpect.TIMEOUT])
    if idx in (0, 1):
        child.sendline(PASSWORD)
        child.expect(pexpect.EOF)

    print(f"   Screenshot saved locally to {local_screenshot} ({local_screenshot.stat().st_size} bytes)")
    print("Deployment completed successfully!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
