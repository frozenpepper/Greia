"""Fixed, Parent-authorized control of the installed SSH maintenance service.

The socket accepts only three fixed operations from the Parent UID. It carries
no command, path, credentials, or other caller-selected authority.
"""
from __future__ import annotations

import json
import os
import pwd
import socket
import struct
import subprocess
from pathlib import Path
from typing import Callable

SOCKET_PATH = Path('/run/greia-parent-ssh/control.sock')
SECURITY_FLOOR = Path('/etc/ssh/sshd_config.d/00-greia-security-floor.conf')
PASSWORD_POLICY = ("# Parent-enabled Greia maintenance SSH.\n"
                   "PasswordAuthentication yes\nKbdInteractiveAuthentication no\n"
                   "PermitRootLogin no\nAuthenticationMethods publickey password\nDenyUsers root\n")


class ParentSshError(RuntimeError):
    """An SSH maintenance request could not be completed."""


class ParentSshAuthority:
    """Root-side owner of the fixed SSH service and development login."""

    def __init__(self, runner: Callable[..., object] = subprocess.run,
                 security_floor: Path = SECURITY_FLOOR) -> None:
        self.run = runner
        self.security_floor = security_floor

    def status(self) -> dict[str, bool]:
        def state(verb: str, expected: str) -> bool:
            result = self.run(['systemctl', verb, 'ssh.service'], shell=False,
                              capture_output=True, text=True, timeout=15, check=False)
            observed = result.stdout.strip()
            if result.returncode == 0 and observed == expected:
                return True
            inactive = {'is-active': {'inactive', 'failed'},
                        'is-enabled': {'disabled', 'masked', 'static'}}
            if observed in inactive[verb]:
                return False
            raise ParentSshError('Could not read SSH service state')
        return {'active': state('is-active', 'active'),
                'enabled': state('is-enabled', 'enabled')}

    def set_enabled(self, enabled: bool) -> dict[str, bool]:
        if enabled:
            # This is the owner-requested maintenance account, not a caller-
            # supplied password or arbitrary command. SSH remains off until now.
            self.run(['/usr/sbin/chpasswd'], input='greia:greia\n', text=True,
                     shell=False, capture_output=True, timeout=15, check=True)
            self.run(['/usr/bin/ssh-keygen', '-A'], shell=False, capture_output=True,
                     timeout=120, check=True)
            self.security_floor.write_text(PASSWORD_POLICY, encoding='utf-8')
        self.run(['systemctl', 'enable' if enabled else 'disable', '--now', 'ssh.service'],
                 shell=False, capture_output=True, timeout=45, check=True)
        status = self.status()
        if status['active'] != enabled or status['enabled'] != enabled:
            raise ParentSshError('SSH did not reach the requested state')
        return status


def serve_connection(conn: socket.socket, authority: ParentSshAuthority, panel_uid: int) -> None:
    """Serve one bounded operation after checking the kernel-reported peer."""
    conn.settimeout(180)
    try:
        raw_peer = conn.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize('3i'))
        _, uid, _ = struct.unpack('3i', raw_peer)
        if uid not in (0, panel_uid):
            raise ParentSshError('SSH control is unavailable')
        data = bytearray()
        while b'\n' not in data and len(data) <= 32:
            chunk = conn.recv(33 - len(data))
            if not chunk:
                break
            data.extend(chunk)
        if bytes(data) not in (b'STATUS\n', b'ENABLE\n', b'DISABLE\n'):
            raise ParentSshError('Invalid SSH operation')
        op = bytes(data).strip()
        result = authority.status() if op == b'STATUS' else authority.set_enabled(op == b'ENABLE')
        response = {'ok': True, **result}
    except (OSError, ValueError, subprocess.SubprocessError, ParentSshError):
        response = {'ok': False, 'error': 'SSH maintenance request failed'}
    try:
        conn.sendall(json.dumps(response, separators=(',', ':')).encode() + b'\n')
    except OSError:
        pass  # A disconnected browser must not terminate the control service.


def main() -> int:
    if os.environ.get('LISTEN_PID') != str(os.getpid()) or os.environ.get('LISTEN_FDS') != '1':
        raise SystemExit('Socket activation required')
    panel_uid = pwd.getpwnam('greiapanel').pw_uid
    listener = socket.fromfd(3, socket.AF_UNIX, socket.SOCK_STREAM)
    authority = ParentSshAuthority()
    while True:
        conn, _ = listener.accept()
        with conn:
            serve_connection(conn, authority, panel_uid)


if __name__ == '__main__':
    raise SystemExit(main())
