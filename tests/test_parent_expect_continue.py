"""Browser-style Expect: 100-continue upload handshake for the Parent API."""
from __future__ import annotations

import socket
import threading
import unittest
from unittest import mock

from greia_parent.production_api import ProductionParentApiHTTPServer
from greia_parent.update_api import UpdateParentApiRequestHandler


def _respond(handler) -> None:
    length = int(handler.headers.get("Content-Length", "0"))
    body = handler.rfile.read(length)
    handler.send_response(200)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


class ExpectContinueTests(unittest.TestCase):
    def setUp(self) -> None:
        patch = mock.patch.object(UpdateParentApiRequestHandler, "do_POST", _respond)
        patch.start()
        self.addCleanup(patch.stop)
        self.server = ProductionParentApiHTTPServer(
            ("127.0.0.1", 0), object(), static_client=object()  # type: ignore[arg-type]
        )
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(self.server.shutdown)
        self.addCleanup(self.server.server_close)

    def test_expect_continue_is_acknowledged_as_http_1_1_before_the_body(self) -> None:
        port = self.server.server_address[1]
        with socket.create_connection(("127.0.0.1", port), timeout=5) as connection:
            connection.sendall(
                b"POST /api/v1/example HTTP/1.1\r\n"
                b"Host: 127.0.0.1\r\n"
                b"Content-Length: 5\r\n"
                b"Expect: 100-continue\r\n"
                b"\r\n"
            )
            interim = connection.recv(1024)
            self.assertTrue(
                interim.startswith(b"HTTP/1.1 100 Continue"),
                interim.decode("latin1", "replace"),
            )
            connection.sendall(b"hello")
            final = b""
            while b"hello" not in final:
                chunk = connection.recv(4096)
                if not chunk:
                    break
                final += chunk
            self.assertIn(b"HTTP/1.1 200", final)
            self.assertIn(b"hello", final)


if __name__ == "__main__":
    unittest.main()
