"""HTTPS Parent LAN and loopback-only HTTP smoke tests (no device required)."""
from __future__ import annotations

import http.client
import shutil
import ssl
import tempfile
import threading
import unittest
from pathlib import Path

from greia_parent.parent_tls import parent_tls_context
from greia_parent.production_api import create_parent_listeners
from greia_parent.static_client import ParentStaticClient


class _MetaApp:
    def api_meta_payload(self) -> dict[str, object]:
        return {"product": "Greia", "service": "Greia Parents"}


@unittest.skipUnless(shutil.which("openssl"), "openssl not available on test host")
class ParentTlsTests(unittest.TestCase):
    def test_certificate_persists_and_partial_state_refuses_restart(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = parent_tls_context(root)
            directory = root / "parent-tls"
            cert = directory / "parent.crt"
            key = directory / "parent.key"
            original = (cert.read_bytes(), key.read_bytes())
            self.assertTrue(original[0].startswith(b"-----BEGIN CERTIFICATE-----"))
            self.assertTrue(original[1].startswith(b"-----BEGIN PRIVATE KEY-----"))
            self.assertEqual(key.stat().st_mode & 0o777, 0o600)
            self.assertEqual(directory.stat().st_mode & 0o777, 0o700)
            self.assertIsNotNone(first)
            parent_tls_context(root)
            self.assertEqual(original, (cert.read_bytes(), key.read_bytes()))
            key.unlink()
            with self.assertRaisesRegex(RuntimeError, "incomplete"):
                parent_tls_context(root)

    def test_https_and_loopback_http_share_real_request_handler(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            app = _MetaApp()
            web = ParentStaticClient(root)
            secure, local = create_parent_listeners(
                app, state_dir=root, bind="127.0.0.1", port=0,
                loopback_port=0, static_client=web
            )
            self.assertIs(secure.request_lock, local.request_lock)
            self.assertEqual(local.server_address[0], "127.0.0.1")
            threads = [
                threading.Thread(target=server.serve_forever, daemon=True)
                for server in (secure, local)
            ]
            for thread in threads:
                thread.start()
            try:
                private_client = http.client.HTTPConnection(
                    "127.0.0.1", local.server_port, timeout=3
                )
                private_client.request("GET", "/api/v1/meta")
                self.assertEqual(private_client.getresponse().status, 200)
                private_client.close()

                remote_client = http.client.HTTPSConnection(
                    "127.0.0.1", secure.server_port,
                    timeout=3, context=ssl._create_unverified_context()
                )
                remote_client.request("GET", "/api/v1/meta")
                self.assertEqual(remote_client.getresponse().status, 200)
                remote_client.close()

                # HTTPS listener must not silently accept unencrypted requests.
                wrong_protocol = http.client.HTTPConnection(
                    "127.0.0.1", secure.server_port, timeout=3
                )
                with self.assertRaises((OSError, http.client.HTTPException)):
                    wrong_protocol.request("GET", "/api/v1/meta")
                    wrong_protocol.getresponse()
                wrong_protocol.close()
            finally:
                for server in (secure, local):
                    server.shutdown()
                    server.server_close()
                for thread in threads:
                    thread.join(timeout=3)
