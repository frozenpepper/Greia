from __future__ import annotations

import queue
import threading
from dataclasses import dataclass
from enum import StrEnum

from .wifi import (
    IwdNetworkProfile,
    WifiBackend,
    WifiConnection,
    WifiError,
    WifiNetwork,
    WifiSecurity,
)


class WifiSetupPhase(StrEnum):
    IDLE = "idle"
    UNAVAILABLE = "unavailable"
    SCANNING = "scanning"
    READY = "ready"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class WifiSetupSnapshot:
    phase: WifiSetupPhase
    networks: tuple[WifiNetwork, ...]
    selected_index: int
    passphrase: str
    connected_ssid: str
    error: str

    @property
    def selected_network(self) -> WifiNetwork | None:
        if not self.networks or not 0 <= self.selected_index < len(self.networks):
            return None
        return self.networks[self.selected_index]


class DemoWifiBackend:
    """Deterministic preview backend; never touches host networking."""

    def available(self) -> bool:
        return True

    def scan(self) -> tuple[WifiNetwork, ...]:
        return (
            WifiNetwork(
                "Greia Family Wi-Fi",
                WifiSecurity.PERSONAL,
                -37.0,
                "/net/connman/iwd/demo/1",
            ),
            WifiNetwork(
                "Library Guest",
                WifiSecurity.OPEN,
                -58.0,
                "/net/connman/iwd/demo/2",
            ),
            WifiNetwork(
                "School Enterprise",
                WifiSecurity.ENTERPRISE,
                -66.0,
                "/net/connman/iwd/demo/3",
            ),
        )

    def connect(
        self,
        network: WifiNetwork,
        passphrase: str = "",
    ) -> WifiConnection:
        return WifiConnection(
            network,
            IwdNetworkProfile.for_network(network, passphrase),
        )


class WifiSetupController:
    """UI-facing owner for asynchronous Wi-Fi scan/connect work.

    The Pygame installer stays responsive while iwd scans or obtains network
    configuration. A monotonically increasing generation invalidates stale
    results whenever the parent skips, refreshes, or starts a newer operation.
    """

    MAX_PASSWORD_CHARACTERS = 63

    def __init__(self, backend: WifiBackend) -> None:
        self._backend = backend
        self._phase = WifiSetupPhase.IDLE
        self._networks: tuple[WifiNetwork, ...] = ()
        self._selected_index = 0
        self._passphrase = ""
        self._profile: IwdNetworkProfile | None = None
        self._connected_ssid = ""
        self._error = ""
        self._events: queue.Queue[tuple[int, str, object]] = queue.Queue()
        self._worker: threading.Thread | None = None
        self._generation = 0

    @property
    def snapshot(self) -> WifiSetupSnapshot:
        return WifiSetupSnapshot(
            self._phase,
            self._networks,
            self._selected_index,
            self._passphrase,
            self._connected_ssid,
            self._error,
        )

    @property
    def profile(self) -> IwdNetworkProfile | None:
        return self._profile

    @property
    def busy(self) -> bool:
        return self._worker is not None and self._worker.is_alive()

    def begin(self) -> None:
        if self._phase is WifiSetupPhase.IDLE:
            self.refresh()

    def refresh(self) -> None:
        if self.busy:
            return
        generation = self._next_generation()
        self._profile = None
        self._connected_ssid = ""
        self._error = ""
        self._phase = WifiSetupPhase.SCANNING

        def worker() -> None:
            try:
                if not self._backend.available():
                    self._events.put((generation, "unavailable", ()))
                    return
                self._events.put((generation, "networks", self._backend.scan()))
            except Exception as exc:
                self._events.put((generation, "error", exc))

        self._worker = threading.Thread(
            target=worker,
            name="greia-wifi-scan",
            daemon=True,
        )
        self._worker.start()

    def select(self, index: int) -> None:
        if self.busy or not 0 <= index < len(self._networks):
            return
        self._selected_index = index
        self._passphrase = ""
        self._profile = None
        self._connected_ssid = ""
        self._error = ""
        self._phase = WifiSetupPhase.READY

    def move_selection(self, delta: int) -> None:
        if self.busy or not self._networks:
            return
        self.select((self._selected_index + delta) % len(self._networks))

    def append_password(self, text: str) -> None:
        network = self.snapshot.selected_network
        if (
            self.busy
            or network is None
            or network.security is not WifiSecurity.PERSONAL
            or self._phase not in {WifiSetupPhase.READY, WifiSetupPhase.ERROR}
        ):
            return
        filtered = "".join(
            character
            for character in text
            if character not in {"\x00", "\r", "\n"}
            and character.isprintable()
        )
        remaining = self.MAX_PASSWORD_CHARACTERS - len(self._passphrase)
        self._passphrase += filtered[:remaining]
        if filtered:
            self._error = ""
            self._phase = WifiSetupPhase.READY

    def backspace_password(self) -> None:
        if self.busy:
            return
        self._passphrase = self._passphrase[:-1]
        self._error = ""
        if self._phase is WifiSetupPhase.ERROR:
            self._phase = WifiSetupPhase.READY

    def connect(self) -> None:
        if self.busy:
            return
        network = self.snapshot.selected_network
        if network is None:
            return
        if not network.installer_supported:
            self._phase = WifiSetupPhase.ERROR
            self._error = (
                "Enterprise Wi-Fi can be configured later in Greia Parents"
            )
            return
        generation = self._next_generation()
        passphrase = self._passphrase
        self._phase = WifiSetupPhase.CONNECTING
        self._error = ""

        def worker() -> None:
            try:
                connection = self._backend.connect(network, passphrase)
                self._events.put((generation, "connected", connection))
            except Exception as exc:
                self._events.put((generation, "error", exc))

        self._worker = threading.Thread(
            target=worker,
            name="greia-wifi-connect",
            daemon=True,
        )
        self._worker.start()

    def skip(self) -> None:
        # The worker itself cannot be cancelled safely at arbitrary D-Bus/DHCP
        # points, so invalidate its result. It may finish in the background, but
        # it can no longer alter installer state or become the installed profile.
        self._next_generation()
        self._profile = None
        self._connected_ssid = ""
        self._passphrase = ""
        self._error = ""
        self._phase = WifiSetupPhase.IDLE

    def drain(self) -> None:
        while True:
            try:
                generation, kind, payload = self._events.get_nowait()
            except queue.Empty:
                return
            if generation != self._generation:
                continue
            self._worker = None
            if kind == "unavailable":
                self._phase = WifiSetupPhase.UNAVAILABLE
                self._networks = ()
                self._selected_index = 0
            elif kind == "networks":
                networks = tuple(payload)  # type: ignore[arg-type]
                self._networks = networks
                self._selected_index = min(
                    self._selected_index,
                    max(0, len(networks) - 1),
                )
                self._phase = WifiSetupPhase.READY
                if not networks:
                    self._error = (
                        "No Wi-Fi networks found. You can refresh or continue offline."
                    )
            elif kind == "connected":
                connection = payload
                if not isinstance(connection, WifiConnection):
                    self._phase = WifiSetupPhase.ERROR
                    self._error = (
                        "Wi-Fi backend returned an invalid connection result"
                    )
                    continue
                self._profile = connection.profile
                self._connected_ssid = connection.network.ssid
                self._passphrase = ""
                self._error = ""
                self._phase = WifiSetupPhase.CONNECTED
            elif kind == "error":
                self._profile = None
                self._connected_ssid = ""
                self._phase = WifiSetupPhase.ERROR
                self._error = str(payload) or payload.__class__.__name__
            else:
                self._phase = WifiSetupPhase.ERROR
                self._error = "Unknown Wi-Fi worker result"

    def _next_generation(self) -> int:
        self._generation += 1
        return self._generation
