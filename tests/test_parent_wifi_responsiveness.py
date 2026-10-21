"""Parent API Wi-Fi responsiveness contracts used by the installed appliance."""

from __future__ import annotations

import unittest
from http.server import ThreadingHTTPServer

from greia_parent.production_api import ProductionParentApiHTTPServer
from greia_platform.wifi import IwdWifiBackend, NETWORK_INTERFACE, STATION_INTERFACE


class ProductionParentApiThreadingTests(unittest.TestCase):
    def test_installed_parent_api_uses_bounded_threads(self) -> None:
        self.assertTrue(
            issubclass(ProductionParentApiHTTPServer, ThreadingHTTPServer)
        )
        self.assertTrue(ProductionParentApiHTTPServer.daemon_threads)
        self.assertFalse(ProductionParentApiHTTPServer.block_on_close)
        self.assertEqual(ProductionParentApiHTTPServer.max_concurrent_requests, 4)


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
