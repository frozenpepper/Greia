from __future__ import annotations

import os
import queue
import threading
import time
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence


IWD_SERVICE = "net.connman.iwd"
OBJECT_MANAGER_INTERFACE = "org.freedesktop.DBus.ObjectManager"
PROPERTIES_INTERFACE = "org.freedesktop.DBus.Properties"
STATION_INTERFACE = "net.connman.iwd.Station"
NETWORK_INTERFACE = "net.connman.iwd.Network"
IWD_STATE_DIR = Path("/var/lib/iwd")
_MAX_NETWORKS = 32


class WifiError(RuntimeError):
    pass


class WifiSecurity(StrEnum):
    OPEN = "open"
    PERSONAL = "psk"
    ENTERPRISE = "8021x"


@dataclass(frozen=True, slots=True)
class WifiNetwork:
    ssid: str
    security: WifiSecurity
    signal_dbm: float
    object_path: str

    def __post_init__(self) -> None:
        _validate_ssid(self.ssid)
        if not self.object_path.startswith("/net/connman/iwd/"):
            raise ValueError("Wi-Fi network object path is invalid")
        if not -100.0 <= float(self.signal_dbm) <= 0.0:
            raise ValueError("Wi-Fi signal must be between -100 and 0 dBm")

    @property
    def installer_supported(self) -> bool:
        return self.security in {WifiSecurity.OPEN, WifiSecurity.PERSONAL}


@dataclass(frozen=True, slots=True)
class IwdNetworkProfile:
    """One tested iwd profile safe to copy into the target or write to system state.

    ``content`` can contain a Wi-Fi credential and is deliberately suppressed
    from repr. Callers must never put it in ordinary logs or install records.
    """

    ssid: str
    filename: str
    content: str = field(repr=False)

    def __post_init__(self) -> None:
        _validate_ssid(self.ssid)
        if Path(self.filename).name != self.filename or not self.filename:
            raise ValueError("iwd profile filename must be one safe basename")
        if not self.filename.endswith((".open", ".psk")):
            raise ValueError("may persist only open or PSK iwd profiles")
        if "\x00" in self.content:
            raise ValueError("iwd profile contains NUL")

    @classmethod
    def for_network(
        cls,
        network: WifiNetwork,
        passphrase: str = "",
    ) -> "IwdNetworkProfile":
        if not network.installer_supported:
            raise WifiError(
                "This Wi-Fi network needs enterprise credentials; "
                "configure it later in Greia Parents"
            )
        if network.security is WifiSecurity.PERSONAL:
            _validate_passphrase(passphrase)
        elif passphrase:
            raise WifiError("Open Wi-Fi networks do not use a password")
        return cls(
            network.ssid,
            _profile_filename(network.ssid, network.security),
            _profile_content(network.security, passphrase),
        )

    def write_to(self, target_root: Path) -> Path:
        state_dir = target_root / IWD_STATE_DIR.relative_to("/")
        state_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(state_dir, 0o700)
        destination = state_dir / self.filename
        _atomic_private_write(destination, self.content)
        return destination


@dataclass(frozen=True, slots=True)
class WifiConnection:
    network: WifiNetwork
    profile: IwdNetworkProfile = field(repr=False)


class WifiBackend(Protocol):
    def available(self) -> bool: ...

    def scan(self) -> tuple[WifiNetwork, ...]: ...

    def connect(
        self,
        network: WifiNetwork,
        passphrase: str = "",
    ) -> WifiConnection: ...


class IwdWifiBackend:
    """Wi-Fi backend using iwd's D-Bus API.

    The password never appears in a subprocess argument. Greia creates a
    root-only iwd profile, asks iwd to connect, and returns the exact profile
    that succeeded so it can be preserved atomically.
    """

    def __init__(
        self,
        *,
        state_dir: Path = IWD_STATE_DIR,
        scan_timeout_seconds: float = 8.0,
        connect_timeout_seconds: float = 35.0,
        poll_interval_seconds: float = 0.10,
        bus: Any | None = None,
    ) -> None:
        self.state_dir = state_dir
        self.scan_timeout_seconds = _bounded_timeout(
            scan_timeout_seconds, 1.0, 15.0
        )
        self.connect_timeout_seconds = _bounded_timeout(
            connect_timeout_seconds, 5.0, 45.0
        )
        self.poll_interval_seconds = _bounded_timeout(
            poll_interval_seconds, 0.02, 0.50
        )
        self._bus = bus

    def available(self) -> bool:
        try:
            return self._station_path(self._managed_objects()) is not None
        except Exception:
            return False

    def scan(self) -> tuple[WifiNetwork, ...]:
        objects = self._managed_objects()
        station_path = self._station_path(objects)
        if station_path is None:
            return ()
        station = self._interface(station_path, STATION_INTERFACE)
        try:
            station.Scan()
        except Exception as exc:
            # If iwd already has an in-flight scan, consume it instead of making
            # a harmless refresh race visible.
            if "Busy" not in str(exc):
                raise WifiError("Wi-Fi scan could not start") from exc
        self._wait_station_scanning(station_path)
        try:
            ordered: Sequence[Sequence[Any]] = station.GetOrderedNetworks()
        except Exception as exc:
            raise WifiError("Wi-Fi scan results are unavailable") from exc

        refreshed = self._managed_objects()
        result: list[WifiNetwork] = []
        seen: set[tuple[str, WifiSecurity]] = set()
        for record in ordered[:_MAX_NETWORKS]:
            if len(record) != 2:
                continue
            object_path = str(record[0])
            props = refreshed.get(object_path, {}).get(NETWORK_INTERFACE, {})
            if not isinstance(props, Mapping):
                continue
            name = props.get("Name")
            network_type = props.get("Type")
            if not isinstance(name, str) or not isinstance(network_type, str):
                continue
            try:
                security = WifiSecurity(network_type)
                signal_dbm = max(-100.0, min(0.0, int(record[1]) / 100.0))
                network = WifiNetwork(name, security, signal_dbm, object_path)
            except (ValueError, TypeError):
                continue
            key = (network.ssid, network.security)
            if key in seen:
                continue
            seen.add(key)
            result.append(network)
        return tuple(result)

    def connect(
        self,
        network: WifiNetwork,
        passphrase: str = "",
    ) -> WifiConnection:
        profile = IwdNetworkProfile.for_network(network, passphrase)
        profile_path = self.state_dir / profile.filename
        self.state_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(self.state_dir, 0o700)
        previous = profile_path.read_bytes() if profile_path.exists() else None
        created_by_attempt = previous is None
        try:
            _atomic_private_write(profile_path, profile.content)
            time.sleep(self.poll_interval_seconds)
            self._connect_network(network)
            try:
                saved_content = profile_path.read_text(encoding="utf-8")
            except OSError as exc:
                raise WifiError(
                    "Wi-Fi connected but its saved profile could not be read"
                ) from exc
            os.chmod(profile_path, 0o600)
            return WifiConnection(
                network,
                IwdNetworkProfile(network.ssid, profile_path.name, saved_content),
            )
        except Exception:
            if created_by_attempt:
                profile_path.unlink(missing_ok=True)
            elif previous is not None:
                _atomic_private_write_bytes(profile_path, previous)
            raise

    def _connect_network(self, network: WifiNetwork) -> None:
        interface = self._interface(network.object_path, NETWORK_INTERFACE)
        error: Exception | None = None
        for attempt in range(2):
            try:
                interface.Connect(timeout=self.connect_timeout_seconds + 5.0)
                error = None
                break
            except Exception as exc:
                error = exc
                if attempt == 0 and "NotConfigured" in str(exc):
                    time.sleep(min(0.50, self.poll_interval_seconds * 2.0))
                    continue
                break
            if error is not None:
                raise WifiError("Could not connect to the selected Wi-Fi network") from error

        station_path = self._station_path(self._managed_objects())
        if station_path is None:
            raise WifiError("Wi-Fi device disappeared while connecting")
        deadline = time.monotonic() + self.connect_timeout_seconds
        while time.monotonic() < deadline:
            state = str(self._property(station_path, STATION_INTERFACE, "State"))
            if state == "connected":
                return
            if state == "disconnected":
                raise WifiError("Wi-Fi connection was rejected")
            time.sleep(self.poll_interval_seconds)
        raise WifiError("Wi-Fi connection timed out")

    def _wait_station_scanning(self, station_path: str) -> None:
        deadline = time.monotonic() + self.scan_timeout_seconds
        while time.monotonic() < deadline:
            if not bool(
                self._property(station_path, STATION_INTERFACE, "Scanning")
            ):
                return
            time.sleep(self.poll_interval_seconds)
        raise WifiError("Wi-Fi scan timed out")

    def _managed_objects(
        self,
    ) -> Mapping[str, Mapping[str, Mapping[str, Any]]]:
        manager = self._interface("/", OBJECT_MANAGER_INTERFACE)
        try:
            return manager.GetManagedObjects()
        except Exception as exc:
            raise WifiError("iwd is not available") from exc

    @staticmethod
    def _station_path(
        objects: Mapping[str, Mapping[str, Mapping[str, Any]]],
    ) -> str | None:
        candidates = sorted(
            str(path)
            for path, interfaces in objects.items()
            if STATION_INTERFACE in interfaces
        )
        return candidates[0] if candidates else None

    def _property(self, object_path: str, interface: str, name: str) -> Any:
        properties = self._interface(object_path, PROPERTIES_INTERFACE)
        try:
            return properties.Get(interface, name)
        except Exception as exc:
            raise WifiError(
                f"Wi-Fi state property {name!r} is unavailable"
            ) from exc

    def _interface(self, object_path: str, interface: str) -> Any:
        bus = self._system_bus()
        try:
            proxy = bus.get_object(IWD_SERVICE, object_path)
        except Exception as exc:
            raise WifiError("iwd D-Bus service is unavailable") from exc
        try:
            import dbus  # type: ignore[import-not-found]
        except ImportError as exc:
            raise WifiError("python3-dbus is missing from the system") from exc
        return dbus.Interface(proxy, interface)

    def _system_bus(self) -> Any:
        if self._bus is not None:
            return self._bus
        try:
            import dbus  # type: ignore[import-not-found]
        except ImportError as exc:
            raise WifiError("python3-dbus is missing from the system") from exc
        self._bus = dbus.SystemBus()
        return self._bus


class DemoWifiBackend:
    """Deterministic preview/testing backend; never touches host networking."""

    def __init__(self, networks: Sequence[WifiNetwork] | None = None) -> None:
        self._networks = tuple(networks) if networks is not None else (
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

    def available(self) -> bool:
        return True

    def scan(self) -> tuple[WifiNetwork, ...]:
        return self._networks

    def connect(
        self,
        network: WifiNetwork,
        passphrase: str = "",
    ) -> WifiConnection:
        if network.security is WifiSecurity.PERSONAL and passphrase == "wrongpassword":
            raise WifiError("Wi-Fi connection was rejected")
        return WifiConnection(
            network,
            IwdNetworkProfile.for_network(network, passphrase),
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
    passphrase: str = field(repr=False)
    connected_ssid: str = ""
    error: str = ""

    @property
    def selected_network(self) -> WifiNetwork | None:
        if not self.networks or not 0 <= self.selected_index < len(self.networks):
            return None
        return self.networks[self.selected_index]


class WifiSetupController:
    """UI-facing owner for asynchronous Wi-Fi scan/connect work.

    The Pygame UI stays responsive while iwd scans or obtains network
    configuration. A monotonically increasing generation invalidates stale
    results whenever the user skips, refreshes, or starts a newer operation.
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
        self._generation = 0
        self._results: queue.Queue[tuple[int, str, object]] = queue.Queue()

    @property
    def busy(self) -> bool:
        return self._phase in {WifiSetupPhase.SCANNING, WifiSetupPhase.CONNECTING}

    @property
    def snapshot(self) -> WifiSetupSnapshot:
        return WifiSetupSnapshot(
            phase=self._phase,
            networks=self._networks,
            selected_index=self._selected_index,
            passphrase=self._passphrase,
            connected_ssid=self._connected_ssid,
            error=self._error,
        )

    @property
    def profile(self) -> IwdNetworkProfile | None:
        return self._profile

    def begin(self) -> None:
        if self._phase not in {WifiSetupPhase.IDLE, WifiSetupPhase.ERROR}:
            return
        if not self._backend.available():
            self._phase = WifiSetupPhase.UNAVAILABLE
            return
        self.refresh()

    def refresh(self) -> None:
        self._generation += 1
        current = self._generation
        self._phase = WifiSetupPhase.SCANNING
        self._error = ""
        threading.Thread(
            target=self._run_scan,
            args=(current,),
            name="greia-wifi-scan",
            daemon=True,
        ).start()

    def select(self, index: int) -> None:
        if not self._networks:
            return
        bounded = max(0, min(index, len(self._networks) - 1))
        if bounded != self._selected_index:
            self._selected_index = bounded
            self._passphrase = ""
            self._error = ""
            if self._phase == WifiSetupPhase.ERROR:
                self._phase = WifiSetupPhase.READY

    def move_selection(self, delta: int) -> None:
        if not self._networks:
            return
        self.select((self._selected_index + delta) % len(self._networks))

    def append_password(self, text: str) -> None:
        if self._phase not in {WifiSetupPhase.READY, WifiSetupPhase.ERROR}:
            return
        accepted = "".join(
            ch
            for ch in text
            if ch not in "\r\n\x00" and ch.isprintable()
        )
        remaining = self.MAX_PASSWORD_CHARACTERS - len(self._passphrase)
        if remaining > 0 and accepted:
            self._passphrase += accepted[:remaining]
            self._error = ""

    def backspace_password(self) -> None:
        if self._phase in {WifiSetupPhase.READY, WifiSetupPhase.ERROR}:
            self._passphrase = self._passphrase[:-1]
            self._error = ""

    def connect(self) -> None:
        if self._phase not in {WifiSetupPhase.READY, WifiSetupPhase.ERROR}:
            return
        network = self.snapshot.selected_network
        if network is None:
            return
        if not network.installer_supported:
            self._phase = WifiSetupPhase.ERROR
            self._error = "Enterprise Wi-Fi is not supported yet."
            return
        if network.security is WifiSecurity.PERSONAL and len(self._passphrase) < 8:
            self._phase = WifiSetupPhase.ERROR
            self._error = "Wi-Fi password must be at least 8 characters."
            return

        self._generation += 1
        current = self._generation
        self._phase = WifiSetupPhase.CONNECTING
        self._error = ""
        passphrase = self._passphrase if network.security is WifiSecurity.PERSONAL else ""
        threading.Thread(
            target=self._run_connect,
            args=(current, network, passphrase),
            name="greia-wifi-connect",
            daemon=True,
        ).start()

    def skip(self) -> None:
        self._generation += 1
        self._passphrase = ""
        self._error = ""

    def drain(self) -> bool:
        changed = False
        while True:
            try:
                generation, kind, payload = self._results.get_nowait()
            except queue.Empty:
                break
            if generation != self._generation:
                continue
            changed = True
            if kind == "scan":
                if isinstance(payload, tuple):
                    self._networks = payload
                    self._phase = WifiSetupPhase.READY
                    self._selected_index = 0
                    self._passphrase = ""
                else:
                    self._phase = WifiSetupPhase.ERROR
                    self._error = str(payload)
            elif kind == "connect":
                if isinstance(payload, WifiConnection):
                    self._profile = payload.profile
                    self._connected_ssid = payload.network.ssid
                    self._phase = WifiSetupPhase.CONNECTED
                    self._passphrase = ""
                else:
                    self._phase = WifiSetupPhase.ERROR
                    self._error = str(payload)
        return changed

    def _run_scan(self, generation: int) -> None:
        try:
            result = self._backend.scan()
            self._results.put((generation, "scan", result))
        except Exception as exc:
            self._results.put((generation, "scan", str(exc)))

    def _run_connect(
        self,
        generation: int,
        network: WifiNetwork,
        passphrase: str,
    ) -> None:
        try:
            connection = self._backend.connect(network, passphrase)
            self._results.put((generation, "connect", connection))
        except Exception as exc:
            self._results.put((generation, "connect", str(exc)))


def _profile_filename(ssid: str, security: WifiSecurity) -> str:
    _validate_ssid(ssid)
    if security not in {WifiSecurity.OPEN, WifiSecurity.PERSONAL}:
        raise ValueError("unsupported Wi-Fi security type")
    raw = ssid.encode("utf-8")
    safe_bytes = b"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 _-"
    stem = ssid if all(byte in safe_bytes for byte in raw) else "=" + raw.hex()
    suffix = ".open" if security is WifiSecurity.OPEN else ".psk"
    return stem + suffix


def _profile_content(security: WifiSecurity, passphrase: str) -> str:
    if security is WifiSecurity.OPEN:
        return "[Settings]\nAutoConnect=true\n"
    if security is WifiSecurity.PERSONAL:
        _validate_passphrase(passphrase)
        escaped = _escape_iwd_value(passphrase)
        return (
            f"[Security]\nPassphrase={escaped}\n\n"
            "[Settings]\nAutoConnect=true\n"
        )
    raise ValueError("unsupported Wi-Fi security type")


def _escape_iwd_value(value: str) -> str:
    """Escape an iwd settings value using its documented key-file syntax."""

    result: list[str] = []
    for character in value:
        if character == "\\":
            result.append("\\\\")
        elif character == " ":
            result.append("\\s")
        elif character == "\t":
            result.append("\\t")
        elif character in {"\x00", "\r", "\n"}:
            raise WifiError("Wi-Fi password contains unsupported control characters")
        else:
            result.append(character)
    return "".join(result)


def _validate_ssid(ssid: str) -> None:
    if not isinstance(ssid, str):
        raise TypeError("SSID must be text")
    raw = ssid.encode("utf-8")
    if not 1 <= len(raw) <= 32 or "\x00" in ssid:
        raise ValueError("SSID must contain 1 to 32 UTF-8 bytes")


def _validate_passphrase(passphrase: str) -> None:
    if not isinstance(passphrase, str):
        raise TypeError("Wi-Fi password must be text")
    if not 8 <= len(passphrase) <= 63:
        raise WifiError("Wi-Fi password must contain 8 to 63 characters")
    if any(character in passphrase for character in ("\x00", "\r", "\n")):
        raise WifiError("Wi-Fi password contains unsupported control characters")


def _atomic_private_write(path: Path, content: str) -> None:
    temporary = path.with_name(f".{path.name}.greia-wifi.tmp")
    try:
        temporary.write_text(content, encoding="utf-8")
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    finally:
        temporary.unlink(missing_ok=True)


def _atomic_private_write_bytes(path: Path, content: bytes) -> None:
    temporary = path.with_name(f".{path.name}.greia-wifi.restore.tmp")
    try:
        temporary.write_bytes(content)
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    finally:
        temporary.unlink(missing_ok=True)


def _bounded_timeout(value: float, minimum: float, maximum: float) -> float:
    number = float(value)
    if not minimum <= number <= maximum:
        raise ValueError(f"timeout must be in [{minimum}, {maximum}]")
    return number
