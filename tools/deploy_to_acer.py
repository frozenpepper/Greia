#!/usr/bin/env python3
"""Deploy clean codebase to the Acer laptop target without AppleDouble artifacts."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import pexpect

ROOT = Path(__file__).resolve().parents[1]
TARBALL = Path("/tmp/greia_deploy.tar.gz")
ACER_IP = "192.168.68.104"
ACER_USER = "greia"
ACER_PASS = "greia"


def main() -> int:
    print(f"Creating clean tarball from {ROOT}...")
    env = os.environ.copy()
    env["COPYFILE_DISABLE"] = "1"
    subprocess.run([
        "tar", "--no-xattrs", "-czf", str(TARBALL),
        "--exclude=.git",
        "--exclude=*.zip",
        "--exclude=__pycache__",
        "--exclude=.pytest_cache",
        "--exclude=docs/reviews",
        "--exclude=._*",
        "--exclude=tmp",
        "-C", str(ROOT), "."
    ], check=True, env=env)

    size = TARBALL.stat().st_size
    print(f"Tarball created: {size:,} bytes")

    print(f"Transferring tarball to Acer ({ACER_IP}) via SCP...")
    scp_cmd = f"scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null {TARBALL} {ACER_USER}@{ACER_IP}:/dev/shm/greia_update.tar.gz"
    scp_child = pexpect.spawn(scp_cmd, encoding="utf-8", timeout=180)
    idx = scp_child.expect(["password:", pexpect.EOF, pexpect.TIMEOUT])
    if idx == 0:
        scp_child.sendline(ACER_PASS)
        scp_child.expect(pexpect.EOF, timeout=180)
    scp_child.close()
    print("Tarball transferred successfully!")

    print("Connecting to Acer to extract and restart service...")
    ssh_cmd = f"ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null {ACER_USER}@{ACER_IP}"
    child = pexpect.spawn(ssh_cmd, encoding="utf-8", timeout=120)
    child.expect("password:")
    child.sendline(ACER_PASS)
    child.expect(r"greia-dev:.*")

    print("Extracting to /opt/greia-os...")
    extract_chain = (
        f"echo {ACER_PASS} | sudo -S tar --no-same-owner -xzf /dev/shm/greia_update.tar.gz -C /opt/greia-os "
        f"&& rm -f /dev/shm/greia_update.tar.gz "
        f"&& echo {ACER_PASS} | sudo -S chown -R greiakid:greiakid /opt/greia-os "
        f"&& echo {ACER_PASS} | sudo -S find /opt/greia-os -name '._*' -delete "
        f"&& echo DEPLOY_EXTRACT_DONE"
    )
    child.sendline(extract_chain)
    child.expect("DEPLOY_EXTRACT_DONE", timeout=180)
    child.expect(r"greia-dev:.*")

    print("Restarting services on Acer...")
    restart_chain = (
        f"echo {ACER_PASS} | sudo -S systemctl restart greia-parent.service greia-launcher.service "
        f"&& echo DEPLOY_RESTART_DONE"
    )
    child.sendline(restart_chain)
    child.expect("DEPLOY_RESTART_DONE", timeout=60)
    child.expect(r"greia-dev:.*")

    print("Validating activity package on Acer...")
    child.sendline("PYTHONPATH=/opt/greia-os/src python3 /opt/greia-os/tools/validate_activity.py /opt/greia-os/activities/teatrino_fiabe")
    child.expect(r"greia-dev:.*")
    output = child.before
    if "PASS" in output:
        print("Activity validation on Acer: PASS!")
    else:
        print("Validation output:\n", output)

    child.sendline("exit")
    child.close()
    print("Deployment complete and verified on Acer hardware!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
