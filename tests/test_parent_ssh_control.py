from __future__ import annotations

import json
import socket
import struct
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from greia_platform.parent_ssh_control import ParentSshAuthority, ParentSshError, serve_connection
from greia_platform.ssh_maintenance import ParentSocketSshMaintenanceProvider


class FakeConnection:
    def __init__(self, payload: bytes, uid: int = 42) -> None:
        self.payload = payload
        self.uid = uid
        self.sent = b''
    def settimeout(self, value): pass
    def getsockopt(self, *args): return struct.pack('3i', 123, self.uid, 42)
    def recv(self, size):
        result, self.payload = self.payload[:size], self.payload[size:]
        return result
    def sendall(self, data): self.sent += data


class ParentSshControlTests(unittest.TestCase):
    def test_fixed_password_start_stop_and_observed_state(self):
        active = False
        calls = []
        def run(args, **kwargs):
            nonlocal active
            calls.append((args, kwargs))
            if args[:2] == ['systemctl', 'enable']: active = True
            if args[:2] == ['systemctl', 'disable']: active = False
            if args[:2] == ['systemctl', 'is-active']:
                return SimpleNamespace(returncode=0 if active else 3, stdout='active\n' if active else 'inactive\n')
            if args[:2] == ['systemctl', 'is-enabled']:
                return SimpleNamespace(returncode=0 if active else 1, stdout='enabled\n' if active else 'disabled\n')
            return SimpleNamespace(returncode=0, stdout='')
        with tempfile.TemporaryDirectory() as directory:
            floor = Path(directory) / 'floor.conf'
            authority = ParentSshAuthority(run, floor)
            self.assertEqual(authority.set_enabled(True), {'active': True, 'enabled': True})
            self.assertIn('PermitRootLogin no', floor.read_text())
            self.assertIn('PasswordAuthentication yes', floor.read_text())
            self.assertEqual(next(k['input'] for a, k in calls if a == ['/usr/sbin/chpasswd']), 'greia:greia\n')
            self.assertEqual(authority.set_enabled(False), {'active': False, 'enabled': False})
            self.assertTrue(all(k.get('shell') is False for _, k in calls))

    def test_failure_does_not_report_success(self):
        def fail(args, **kwargs):
            raise subprocess.CalledProcessError(1, args)
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(subprocess.CalledProcessError):
                ParentSshAuthority(fail, Path(directory) / 'floor').set_enabled(True)

    def test_observed_wrong_state_rejected(self):
        def run(args, **kwargs):
            return SimpleNamespace(returncode=3 if 'is-active' in args else 1, stdout='inactive' if 'is-active' in args else 'disabled')
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ParentSshError):
                ParentSshAuthority(run, Path(directory) / 'floor').set_enabled(True)

    def test_rejects_unapproved_peer_and_non_fixed_operations(self):
        authority = mock.Mock()
        for payload, uid in ((b'ENABLE\n', 99), (b'ENABLE /bin/sh\n', 42), (b'ENABLE\nmore', 42)):
            conn = FakeConnection(payload, uid)
            with mock.patch.object(socket, 'SO_PEERCRED', 17, create=True):
                serve_connection(conn, authority, 42)
            self.assertFalse(json.loads(conn.sent)['ok'])
        authority.set_enabled.assert_not_called()

    def test_parent_peer_can_toggle(self):
        authority = mock.Mock()
        authority.set_enabled.return_value = {'active': True, 'enabled': True}
        conn = FakeConnection(b'ENABLE\n')
        with mock.patch.object(socket, 'SO_PEERCRED', 17, create=True):
            serve_connection(conn, authority, 42)
        authority.set_enabled.assert_called_once_with(True)
        self.assertTrue(json.loads(conn.sent)['active'])

    def test_client_uses_fixed_socket_operations_and_observed_response(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'control.sock'
            listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            listener.bind(str(path))
            listener.listen(1)
            received = []
            def worker():
                with listener:
                    conn, _ = listener.accept()
                    with conn:
                        received.append(conn.recv(32))
                        conn.sendall(b'{"ok":true,"active":true,"enabled":true}\n')
            thread = threading.Thread(target=worker)
            thread.start()
            provider = ParentSocketSshMaintenanceProvider(path)
            self.assertTrue(provider.available())
            status = provider.enable()
            thread.join(2)
            self.assertEqual(received, [b'ENABLE\n'])
            self.assertTrue(status.active and status.enabled)

    def test_image_enables_socket_not_ssh_daemon(self):
        root = Path(__file__).resolve().parents[1]
        composition = (root / 'build/lib/compose.sh').read_text()
        self.assertIn('greia-parent-ssh.socket', composition)
        unit = (root / 'build/overlay/etc/systemd/system/greia-parent-ssh.socket').read_text()
        self.assertIn('SocketGroup=greiapanel', unit)
        self.assertIn('WantedBy=sockets.target', unit)

    def test_socket_availability_is_not_inferred_from_a_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'control'
            path.touch()
            self.assertFalse(ParentSocketSshMaintenanceProvider(path).available())


if __name__ == '__main__': unittest.main()
