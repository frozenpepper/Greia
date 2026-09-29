from __future__ import annotations

import time
import unittest

from greia_installer.wifi import (
    IwdNetworkProfile,
    WifiConnection,
    WifiNetwork,
    WifiSecurity,
)
from greia_installer.wifi_setup import WifiSetupController, WifiSetupPhase


class FakeBackend:
    def __init__(self) -> None:
        self.networks = (
            WifiNetwork(
                "Home",
                WifiSecurity.PERSONAL,
                -40.0,
                "/net/connman/iwd/demo/home",
            ),
            WifiNetwork(
                "Guest",
                WifiSecurity.OPEN,
                -60.0,
                "/net/connman/iwd/demo/guest",
            ),
            WifiNetwork(
                "School",
                WifiSecurity.ENTERPRISE,
                -65.0,
                "/net/connman/iwd/demo/school",
            ),
        )
        self.available_value = True
        self.calls = 0

    def available(self) -> bool:
        return self.available_value

    def scan(self) -> tuple[WifiNetwork, ...]:
        # A backend with no adapter cannot produce results either. Keeping the
        # fake honest matters now that begin() no longer decides availability
        # from a single check: a fake that scanned networks while claiming no
        # adapter would hide the real ordering.
        if not self.available_value:
            return ()
        return self.networks

    def connect(
        self,
        network: WifiNetwork,
        passphrase: str = "",
    ) -> WifiConnection:
        self.calls += 1
        return WifiConnection(
            network,
            IwdNetworkProfile.for_network(network, passphrase),
        )


def finish(controller: WifiSetupController, timeout: float = 1.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        controller.drain()
        if not controller.busy:
            controller.drain()
            return
        time.sleep(0.005)
    raise AssertionError("Wi-Fi worker did not finish")


class InstallerWifiSetupTests(unittest.TestCase):
    def test_scan_and_personal_connection(self) -> None:
        backend = FakeBackend()
        controller = WifiSetupController(backend)
        controller.begin()
        finish(controller)
        self.assertEqual(controller.snapshot.phase, WifiSetupPhase.READY)
        controller.append_password("correct-horse")
        self.assertNotIn("correct-horse", repr(controller.snapshot))
        controller.connect()
        finish(controller)
        self.assertEqual(controller.snapshot.phase, WifiSetupPhase.CONNECTED)
        self.assertEqual(controller.snapshot.passphrase, "")
        self.assertIsNotNone(controller.profile)

    def test_enterprise_is_deferred_without_backend_connect(self) -> None:
        backend = FakeBackend()
        controller = WifiSetupController(backend)
        controller.begin()
        finish(controller)
        controller.select(2)
        controller.connect()
        self.assertEqual(controller.snapshot.phase, WifiSetupPhase.ERROR)
        self.assertEqual(backend.calls, 0)

    def test_no_adapter_is_nonfatal(self) -> None:
        backend = FakeBackend()
        backend.available_value = False
        controller = WifiSetupController(backend)
        original = controller.SCAN_RETRY_DELAY_SECONDS
        controller.SCAN_RETRY_DELAY_SECONDS = 0.01
        try:
            controller.begin()
            finish(controller, timeout=10.0)
        finally:
            controller.SCAN_RETRY_DELAY_SECONDS = original
        self.assertEqual(controller.snapshot.phase, WifiSetupPhase.UNAVAILABLE)
        self.assertIsNone(controller.profile)

    def test_password_is_hard_bounded(self) -> None:
        controller = WifiSetupController(FakeBackend())
        controller.begin()
        finish(controller)
        controller.append_password("x" * 100)
        self.assertEqual(len(controller.snapshot.passphrase), 63)


if __name__ == "__main__":
    unittest.main()


class SlowAdapterBackend(FakeBackend):
    """Adapter that reports no networks until it has settled.

    iwd only publishes its Station interface once the adapter is in station
    mode, so the first scan after the installer reaches the Wi-Fi page can
    legitimately come back empty even though networks are in range.
    """

    def __init__(self, empty_scans: int) -> None:
        super().__init__()
        self.empty_scans = empty_scans

    def scan(self) -> tuple[WifiNetwork, ...]:
        self.calls += 1
        if self.calls <= self.empty_scans:
            return ()
        return self.networks


class NeverReadyBackend(FakeBackend):
    """Adapter that never reports anything, to bound the retry."""

    def scan(self) -> tuple[WifiNetwork, ...]:
        self.calls += 1
        return ()


class WifiSetupScanRetryTests(unittest.TestCase):
    """An early empty scan must not be published as 'there is no Wi-Fi'."""

    def settle(self, controller: WifiSetupController, seconds: float = 6.0) -> None:
        deadline = time.time() + seconds
        while time.time() < deadline:
            controller.drain()
            if not controller.busy:
                return
            time.sleep(0.05)
        controller.drain()

    def test_empty_scan_is_retried_until_the_adapter_is_ready(self) -> None:
        backend = SlowAdapterBackend(empty_scans=2)
        controller = WifiSetupController(backend)
        original_delay = controller.SCAN_RETRY_DELAY_SECONDS
        controller.SCAN_RETRY_DELAY_SECONDS = 0.01
        try:
            controller.begin()
            self.settle(controller)
        finally:
            controller.SCAN_RETRY_DELAY_SECONDS = original_delay
        snapshot = controller.snapshot
        self.assertEqual(snapshot.phase, WifiSetupPhase.READY)
        self.assertEqual(
            len(snapshot.networks),
            len(backend.networks),
            "a later successful scan must replace the early empty one",
        )
        self.assertGreaterEqual(backend.calls, 3)

    def test_retry_is_bounded_and_settles_on_the_empty_state(self) -> None:
        backend = NeverReadyBackend()
        controller = WifiSetupController(backend)
        original_delay = controller.SCAN_RETRY_DELAY_SECONDS
        controller.SCAN_RETRY_DELAY_SECONDS = 0.01
        try:
            controller.begin()
            self.settle(controller)
        finally:
            controller.SCAN_RETRY_DELAY_SECONDS = original_delay
        self.assertEqual(controller.snapshot.phase, WifiSetupPhase.READY)
        self.assertEqual(controller.snapshot.networks, ())
        self.assertEqual(
            backend.calls,
            controller.SCAN_RETRY_LIMIT + 1,
            "retries must stop, not spin forever",
        )


class LateAdapterBackend(FakeBackend):
    """Adapter that only becomes usable after the first availability check."""

    def __init__(self, available_after: int) -> None:
        super().__init__()
        self.available_after = available_after
        self.availability_checks = 0

    def available(self) -> bool:
        self.availability_checks += 1
        return self.availability_checks > self.available_after

    def scan(self) -> tuple[WifiNetwork, ...]:
        self.calls += 1
        if not self.available():
            return ()
        return self.networks


class WifiSetupAdapterReadinessTests(unittest.TestCase):
    """A late-settling adapter must never latch into a permanent dead end."""

    def settle(self, controller: WifiSetupController, seconds: float = 20.0) -> None:
        deadline = time.time() + seconds
        while time.time() < deadline:
            controller.drain()
            if not controller.busy:
                return
            time.sleep(0.05)
        controller.drain()

    def test_adapter_that_appears_late_still_reaches_ready(self) -> None:
        """The old code latched UNAVAILABLE on the first false check.

        iwd publishes its Station interface only once the adapter settles, so
        reaching the Wi-Fi screen early produced a permanent "no wireless
        adapter" verdict that only the Refresh button could undo.
        """

        backend = LateAdapterBackend(available_after=1)
        controller = WifiSetupController(backend)
        original_delay = controller.SCAN_RETRY_DELAY_SECONDS
        controller.SCAN_RETRY_DELAY_SECONDS = 0.01
        try:
            controller.begin()
            self.settle(controller)
        finally:
            controller.SCAN_RETRY_DELAY_SECONDS = original_delay
        snapshot = controller.snapshot
        self.assertEqual(
            snapshot.phase,
            WifiSetupPhase.READY,
            "an adapter that settles late must not be latched as unavailable",
        )
        self.assertEqual(len(snapshot.networks), len(backend.networks))

    def test_begin_never_latches_unavailable_on_its_first_check(self) -> None:
        backend = LateAdapterBackend(available_after=99)
        controller = WifiSetupController(backend)
        controller.SCAN_RETRY_DELAY_SECONDS = 0.01
        controller.begin()
        self.assertNotEqual(
            controller.snapshot.phase,
            WifiSetupPhase.UNAVAILABLE,
            "begin() must not decide availability from a single early check",
        )

    def test_genuinely_absent_adapter_still_reports_unavailable(self) -> None:
        class NeverAvailable(SlowAdapterBackend):
            def available(self) -> bool:
                return False

        backend = NeverAvailable(empty_scans=10**6)
        controller = WifiSetupController(backend)
        original = controller.SCAN_RETRY_DELAY_SECONDS
        controller.SCAN_RETRY_DELAY_SECONDS = 0.01
        try:
            controller.begin()
            self.settle(controller)
        finally:
            controller.SCAN_RETRY_DELAY_SECONDS = original
        self.assertEqual(controller.snapshot.phase, WifiSetupPhase.UNAVAILABLE)
        self.assertEqual(controller.snapshot.networks, ())
        self.assertEqual(backend.calls, controller.SCAN_RETRY_LIMIT + 1)
