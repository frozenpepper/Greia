"""Parent API Wi-Fi responsiveness contracts used by the installed appliance."""

from __future__ import annotations

import threading
import time
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from unittest import mock

from greia_parent.production_api import ProductionParentApiHTTPServer
from greia_parent.protocol import API_BASE
from greia_parent.update_api import UpdateParentApiRequestHandler
from greia_platform.wifi import IwdWifiBackend, NETWORK_INTERFACE, STATION_INTERFACE


class ProductionParentApiThreadingTests(unittest.TestCase):
    def test_installed_parent_api_uses_bounded_threads(self) -> None:
        self.assertTrue(
            issubclass(ProductionParentApiHTTPServer, ThreadingHTTPServer)
        )
        self.assertTrue(ProductionParentApiHTTPServer.daemon_threads)
        self.assertFalse(ProductionParentApiHTTPServer.block_on_close)
        self.assertEqual(ProductionParentApiHTTPServer.max_concurrent_requests, 4)


class RequestSerializationTests(unittest.TestCase):
    """Non-Wi-Fi requests never overlap; Wi-Fi requests do not block them."""

    def setUp(self) -> None:
        self.active = 0
        self.max_active = 0
        self.guard = threading.Lock()
        self.wifi_started = threading.Event()
        self.release_wifi = threading.Event()

        def respond(handler, body: bytes = b"ok") -> None:
            handler.send_response(200)
            handler.send_header("Content-Length", str(len(body)))
            handler.end_headers()
            handler.wfile.write(body)

        def mutating(handler) -> None:
            with self.guard:
                self.active += 1
                self.max_active = max(self.max_active, self.active)
            time.sleep(0.15)
            with self.guard:
                self.active -= 1
            respond(handler)

        def get(handler) -> None:
            if handler.path.endswith("/network/wifi/connect"):
                respond(handler)
            elif handler.path.endswith("/network/wifi"):
                self.wifi_started.set()
                self.release_wifi.wait(5)
                respond(handler)
            else:
                respond(handler)

        def post(handler) -> None:
            if handler.path.endswith("/network/wifi/connect"):
                self.wifi_started.set()
                self.release_wifi.wait(5)
                respond(handler)
            else:
                mutating(handler)

        patches = [
            mock.patch.object(UpdateParentApiRequestHandler, "do_GET", get),
            mock.patch.object(UpdateParentApiRequestHandler, "do_POST", post),
            mock.patch.object(UpdateParentApiRequestHandler, "do_PUT", mutating),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        self.server = ProductionParentApiHTTPServer(
            ("127.0.0.1", 0), object(), static_client=object()  # type: ignore[arg-type]
        )
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.addCleanup(self.release_wifi.set)

    def _request(self, method: str, path: str) -> int:
        request = urllib.request.Request(
            self.base + path, method=method, data=b"{}" if method != "GET" else None
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status

    def test_slow_wifi_connect_does_not_block_a_concurrent_get(self) -> None:
        wifi = threading.Thread(
            target=self._request, args=("POST", f"{API_BASE}/network/wifi/connect")
        )
        wifi.start()
        self.assertTrue(self.wifi_started.wait(5))
        started = time.monotonic()
        self.assertEqual(self._request("GET", f"{API_BASE}/index"), 200)
        self.assertLess(time.monotonic() - started, 2.0)
        self.release_wifi.set()
        wifi.join(5)

    def test_mutating_requests_never_overlap(self) -> None:
        threads = [
            threading.Thread(target=self._request, args=(method, f"{API_BASE}/x"))
            for method in ("POST", "PUT", "POST", "PUT")
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(10)
        self.assertEqual(self.max_active, 1)


class ConnectedSsidTests(unittest.TestCase):
    def _backend(self, objects):
        backend = IwdWifiBackend()
        backend._managed_objects = lambda: objects  # type: ignore[method-assign]
        return backend

    def test_connected_station_returns_ssid_without_a_scan(self) -> None:
        station = "/net/connman/iwd/0/3/576972656c6573732050656e64656e7465_psk"
        network = station.rsplit("/", 1)[0] + "/network"
        backend = self._backend(
            {
                station: {
                    STATION_INTERFACE: {
                        "State": "connected",
                        "ConnectedNetwork": network,
                    }
                },
                network: {NETWORK_INTERFACE: {"Name": "Wireless Pendente"}},
            }
        )
        self.assertEqual(backend.connected_ssid(), "Wireless Pendente")

    def test_disconnected_or_missing_station_returns_empty(self) -> None:
        station = "/net/connman/iwd/0/3/00000000000000000000000000000000_psk"
        backend = self._backend(
            {station: {STATION_INTERFACE: {"State": "disconnected"}}}
        )
        self.assertEqual(backend.connected_ssid(), "")
        self.assertEqual(self._backend({}).connected_ssid(), "")


if __name__ == "__main__":
    unittest.main()
