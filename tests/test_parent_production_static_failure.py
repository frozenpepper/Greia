from __future__ import annotations

import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from greia_parent.production_api import ProductionParentApiHTTPServer
from greia_parent.static_client import ParentStaticClient


class ProductionParentStaticFailureTests(unittest.TestCase):
    def _request_once(self, client_root: Path) -> tuple[int, str]:
        server = ProductionParentApiHTTPServer(
            ("127.0.0.1", 0),
            object(),  # root static handling does not consult application state
            static_client=ParentStaticClient(client_root),
        )
        thread = threading.Thread(target=server.handle_request, daemon=True)
        thread.start()
        url = f"http://127.0.0.1:{server.server_port}/"
        try:
            try:
                with urllib.request.urlopen(url, timeout=3) as response:
                    return response.status, response.read().decode("utf-8")
            except urllib.error.HTTPError as exc:
                return exc.code, exc.read().decode("utf-8")
        finally:
            thread.join(timeout=3)
            server.server_close()

    def test_missing_production_client_returns_service_unavailable_without_controls(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            status, body = self._request_once(Path(temporary) / "missing")
        self.assertEqual(status, 503)
        self.assertIn("not installed correctly", body)
        self.assertIn("No substitute or sample interface", body)
        self.assertNotIn('action="/api/', body)

    def test_present_production_client_still_serves_normal_shell(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "index.html").write_text("<!doctype html><title>Real Parent</title>", encoding="utf-8")
            status, body = self._request_once(root)
        self.assertEqual(status, 200)
        self.assertIn("Real Parent", body)


if __name__ == "__main__":
    unittest.main()
