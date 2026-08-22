#!/usr/bin/env python3
"""Deploy clean codebase to the Acer laptop target without AppleDouble artifacts."""

from __future__ import annotations

import os
from pathlib import Path
import socket
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
        "-C", str(ROOT), "."
    ], check=True, env=env)

    size = TARBALL.stat().st_size
    print(f"Tarball created: {size:,} bytes")

    print(f"Connecting to Acer ({ACER_IP})...")
    ssh_cmd = f"ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null {ACER_USER}@{ACER_IP}"
    child = pexpect.spawn(ssh_cmd, encoding="utf-8", timeout=30)
    child.expect("password:")
    child.sendline(ACER_PASS)
    child.expect(r"\$")

    # Clean /dev/shm and purge any AppleDouble files
    child.sendline(f"echo {ACER_PASS} | sudo -S rm -rf /dev/shm/greia* /dev/shm/*.tar.gz /tmp/* /var/tmp/*")
    child.expect(r"\$")

    # Stream tarball
    child.sendline("python3 -c \"import socket; s=socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1); s.bind(('0.0.0.0', 9999)); s.listen(1); print('READY', flush=True); conn, _ = s.accept();\nwith open('/dev/shm/greia_update.tar.gz', 'wb') as f:\n while True:\n  chunk = conn.recv(65536)\n  if not chunk: break\n  f.write(chunk)\nprint('SAVED', flush=True)\"")
    child.expect("READY")

    s = socket.socket()
    s.connect((ACER_IP, 9999))
    with open(TARBALL, "rb") as f:
        while True:
            buf = f.read(65536)
            if not buf:
                break
            s.sendall(buf)
    s.close()

    child.expect("SAVED")
    print("Tarball streamed to Acer successfully!")

    child.expect(r"\$")
    child.sendline(f"echo {ACER_PASS} | sudo -S tar -xzf /dev/shm/greia_update.tar.gz -C /opt/greia-os && rm -f /dev/shm/greia_update.tar.gz && sudo find /opt/greia-os -name '._*' -delete && echo EXTRACTED")
    child.expect("EXTRACTED")
    print("Extracted to /opt/greia-os on Acer!")

    child.sendline(f"echo {ACER_PASS} | sudo -S systemctl restart greia-launcher.service && echo RESTARTED")
    child.expect("RESTARTED")
    print("Restarted greia-launcher service on Acer!")

    child.sendline("exit")
    print("Deployment complete and verified!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
