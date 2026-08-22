#!/usr/bin/env python3
"""Deploy codebase to Acer laptop target with staging validation, atomic swap, and auto-rollback."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import pexpect

ROOT = Path(__file__).resolve().parents[1]
TARBALL = Path("/tmp/greia_deploy.tar.gz")
ACER_IP = os.environ.get("GREIA_ACER_IP", "192.168.68.104")
ACER_USER = os.environ.get("GREIA_ACER_USER", "greia")
ACER_PASS = os.environ.get("GREIA_ACER_PASS", "greia")


def run_local(cmd: list[str]) -> bool:
    print("Running local:", " ".join(cmd))
    res = subprocess.run(cmd, cwd=str(ROOT))
    return res.returncode == 0


def main() -> int:
    print("=== Step 1: Local Pre-Flight Checks ===")
    print("Validating Python bytecode...")
    if not run_local([sys.executable, "-m", "compileall", "-q", "src", "activities"]):
        print("ERROR: Local syntax / compile check failed! Deployment aborted.")
        return 1

    print("=== Step 2: Creating Clean Deployment Tarball ===")
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

    print(f"=== Step 3: Transferring Payload to Acer ({ACER_IP}) ===")
    scp_cmd = f"scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null {TARBALL} {ACER_USER}@{ACER_IP}:/dev/shm/greia_update.tar.gz"
    scp_child = pexpect.spawn(scp_cmd, encoding="utf-8", timeout=180)
    idx = scp_child.expect(["password:", pexpect.EOF, pexpect.TIMEOUT])
    if idx == 0:
        scp_child.sendline(ACER_PASS)
        scp_child.expect(pexpect.EOF, timeout=180)
    scp_child.close()
    if scp_child.exitstatus != 0:
        print("ERROR: SCP transfer failed!")
        return 1
    print("Tarball transferred successfully!")

    print("=== Step 4: On-Target Staged Extraction & Integrity Gate ===")
    ssh_cmd = f"ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null {ACER_USER}@{ACER_IP}"
    child = pexpect.spawn(ssh_cmd, encoding="utf-8", timeout=180)
    child.expect("password:")
    child.sendline(ACER_PASS)
    child.expect(r"greia-dev:.*")

    staging_script = (
        f"echo {ACER_PASS} | sudo -S rm -rf /opt/greia-os-staging "
        f"&& echo {ACER_PASS} | sudo -S mkdir -p /opt/greia-os-staging "
        f"&& echo {ACER_PASS} | sudo -S tar --no-same-owner -xzf /dev/shm/greia_update.tar.gz -C /opt/greia-os-staging "
        f"&& rm -f /dev/shm/greia_update.tar.gz "
        f"&& echo {ACER_PASS} | sudo -S find /opt/greia-os-staging -name '._*' -delete "
        f"&& echo {ACER_PASS} | sudo -S chown -R greiakid:greiakid /opt/greia-os-staging "
        f"&& echo STAGING_EXTRACT_DONE"
    )
    child.sendline(staging_script)
    child.expect("STAGING_EXTRACT_DONE", timeout=180)
    child.expect(r"greia-dev:.*")

    print("Verifying staged files and packages on target...")
    validation_script = (
        "python3 -c '"
        "import sys, tomllib;"
        "from pathlib import Path;"
        "root = Path(\"/opt/greia-os-staging\");"
        "assert (root / \"runtime\" / \"child-runtime.toml\").stat().st_size > 0, \"child-runtime.toml is empty!\";"
        "sys.path.insert(0, str(root / \"src\"));"
        "from greia_platform.activities import RuntimeCatalogue, ActivityRegistry;"
        "from greia_platform.trust import ActivitySource, PackageTrust;"
        "runtime = RuntimeCatalogue.load(root / \"runtime\" / \"child-runtime.toml\");"
        "registry = ActivityRegistry([ActivitySource(root / \"activities\", trust=PackageTrust.BUILT_IN)], runtime);"
        "activities = registry.discover();"
        "assert len(activities) > 0, \"No activities discovered in staging!\";"
        "print(f\"STAGING_VERIFY_PASS: {len(activities)} activities discovered cleanly\");"
        "'"
    )
    child.sendline(validation_script)
    child.expect(r"greia-dev:.*", timeout=60)
    output = child.before
    if "STAGING_VERIFY_PASS" not in output:
        print("ERROR: Staging validation failed on target! Aborting without modifying /opt/greia-os.")
        print(output)
        child.sendline(f"echo {ACER_PASS} | sudo -S rm -rf /opt/greia-os-staging")
        child.expect(r"greia-dev:.*")
        child.sendline("exit")
        child.close()
        return 1

    print("Staging verification PASSED!")

    print("=== Step 5: Atomic Activation & Backup ===")
    swap_script = (
        f"echo {ACER_PASS} | sudo -S rm -rf /opt/greia-os-backup "
        f"&& echo {ACER_PASS} | sudo -S cp -a /opt/greia-os /opt/greia-os-backup "
        f"&& echo {ACER_PASS} | sudo -S cp -a /opt/greia-os-staging/. /opt/greia-os/ "
        f"&& echo {ACER_PASS} | sudo -S chown -R greiakid:greiakid /opt/greia-os "
        f"&& echo {ACER_PASS} | sudo -S rm -rf /opt/greia-os-staging "
        f"&& echo SWAP_COMPLETE"
    )
    child.sendline(swap_script)
    child.expect("SWAP_COMPLETE", timeout=120)
    child.expect(r"greia-dev:.*")

    print("=== Step 6: Service Restart & Live Health Check ===")
    child.sendline(f"echo {ACER_PASS} | sudo -S systemctl restart greia-parent.service greia-launcher.service && echo RESTARTED")
    child.expect("RESTARTED", timeout=60)
    child.expect(r"greia-dev:.*")

    print("Waiting 4s for service stability check...")
    child.sendline("sleep 4 && systemctl is-active greia-launcher.service && systemctl is-active greia-parent.service && echo HEALTH_CHECK_PASS")
    child.expect(r"greia-dev:.*", timeout=30)
    health_output = child.before

    if "HEALTH_CHECK_PASS" in health_output:
        print("Service Health Check: PASSED (greia-launcher and greia-parent are active and running)!")
        child.sendline(f"echo {ACER_PASS} | sudo -S rm -rf /opt/greia-os-backup")
        child.expect(r"greia-dev:.*")
    else:
        print("WARNING: Health check failed! Initiating automatic rollback from /opt/greia-os-backup...")
        rollback_script = (
            f"echo {ACER_PASS} | sudo -S cp -a /opt/greia-os-backup/. /opt/greia-os/ "
            f"&& echo {ACER_PASS} | sudo -S chown -R greiakid:greiakid /opt/greia-os "
            f"&& echo {ACER_PASS} | sudo -S systemctl restart greia-parent.service greia-launcher.service "
            f"&& echo ROLLBACK_COMPLETE"
        )
        child.sendline(rollback_script)
        child.expect("ROLLBACK_COMPLETE", timeout=60)
        child.expect(r"greia-dev:.*")
        print("Automatic rollback executed. System restored to previous working state.")
        child.sendline("exit")
        child.close()
        return 1

    child.sendline("exit")
    child.close()
    print("Deployment successfully completed, validated, and confirmed healthy on hardware!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
