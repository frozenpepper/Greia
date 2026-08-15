from __future__ import annotations

import os
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
    """One successfully tested iwd profile safe to persist into the target.

    The profile text can contain a Wi-Fi passphrase, so its repr is deliberately
    suppressed. Callers must never log or place ``content`` into install records.
    """

    ssid: str
    filename: str
    content: str = field(repr=False)

    def __post_init__(self) -> None:
        _validate_ssid(self.ssid)
        if Path(self.filename).name != self.filename or not self.filename:
            raise ValueError("iwd profile filename must be one safe basename")
        if not self.filename.endswith((".open", ".psk")):
            raise ValueError("installer may persist only open or PSK iwd profiles")
        if "\x00" in self.content:
            raise ValueError("iwd profile contains NUL")

    def write_to(self, target_root: Path) -> Path:
        state_dir = target_root / IWD_STATE_DIR.relative_to("/")
        state_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(state_dir, 0o700)
        destination = state_dir / self.filename
        temporary = state_dir / f".{self.filename}.greia-installer.tmp"
        try:
            temporary.write_text(self.content, encoding="utf-8")
            os.chmod(temporary, 0o600)
            os.replace(temporary, destination)
            os.chmod(destination, 0o600)
        finally:
            temporary.unlink(missing_ok=True)
        return destination


@dataclass(frozen=True, slots=True)
class WifiConnection:
    network: WifiNetwork
    profile: IwdNetworkProfile = field(repr=False)


class WifiBackend(Protocol):
    def available(self) -> bool: ...
    def scan(self) -> tuple[WifiNetwork, ...]: ...
    def connect(self, network: WifiNetwork, passphrase: str = "") -> WifiConnection: ...


class IwdWifiBackend:
    """Root-side live-installer Wi-Fi backend using iwd's documented D-Bus API.

    Credentials never appear in subprocess arguments because this adapter does
    not use ``iwctl --passphrase``. For a Personal network it writes one
    root-only iwd profile, asks iwd to connect through D-Bus, and returns the
    exact successfully tested profile for target installation.
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
        self.scan_timeout_seconds = _bounded_timeout(scan_timeout_seconds, 1.0, 15.0)
        self.connect_timeout_seconds = _bounded_timeout(connect_timeout_seconds, 5.0, 45.0)
        self.poll_interval_seconds = _bounded_timeout(poll_interval_seconds, 0.02, 0.50)
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
            # iwd may report Busy when a scan is already underway. We still wait
            # for Scanning to clear and consume that scan instead of failing UX.
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

    def connect(self, network: WifiNetwork, passphrase: str = "") -> WifiConnection:
        if not network.installer_supported:
            raise WifiError("This Wi-Fi network needs enterprise credentials; configure it later in Greia Parents")
        if network.security is WifiSecurity.PERSONAL:
            _validate_passphrase(passphrase)
        elif passphrase:
            raise WifiError("Open Wi-Fi networks do not use a password")

        profile_path = self.state_dir / _profile_filename(network.ssid, network.security)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(self.state_dir, 0o700)
        previous = profile_path.read_bytes() if profile_path.exists() else None
        profile_content = _profile_content(network.security, passphrase)
        created_by_attempt = previous is None
        try:
            if network.security is WifiSecurity.PERSONAL:
                _atomic_private_write(profile_path, profile_content)
                # Let iwd's state-directory watch observe the newly provisioned
                # profile before Connect. A bounded retry below handles slower
                # devices without exposing the secret through iwctl argv.
                time.sleep(self.poll_interval_seconds)
            connection = self._connect_network(network)
            saved_path = self.state_dir / _profile_filename(network.ssid, network.security)
            try:
                saved_content = saved_path.read_text(encoding="utf-8")
            except OSError as exc:
                raise WifiError("Wi-Fi connected but its saved profile could not be read") from exc
            os.chmod(saved_path, 0o600)
            return WifiConnection(
                connection,
                IwdNetworkProfile(connection.ssid, saved_path.name, saved_content),
            )
        except Exception:
            if created_by_attempt:
                profile_path.unlink(missing_ok=True)
            elif previous is not None:
                temporary = profile_path.with_name(f".{profile_path.name}.restore.tmp")
                try:
                    temporary.write_bytes(previous)
                    os.chmod(temporary, 0o600)
                    os.replace(temporary, profile_path)
                finally:
                    temporary.unlink(missing_ok=True)
            raise

    def _connect_network(self, network: WifiNetwork) -> WifiNetwork:
        interface = self._interface(network.object_path, NETWORK_INTERFACE)
        error: Exception | None = None
        for attempt in range(2):
            try:
                interface.Connect()
                error = None
                break
            except Exception as exc:
                error = exc
                if attempt == 0 and network.security is WifiSecurity.PERSONAL and "NotConfigured" in str(exc):
                    time.sleep(min(0.50, self.poll_interval_seconds * 2.0))
                    continue
                break
        if error is not None:
            raise WifiError("Could not connect to the selected Wi-Fi network") from error

        objects = self._managed_objects()
        station_path = self._station_path(objects)
        if station_path is None:
            raise WifiError("Wi-Fi device disappeared while connecting")
        deadline = time.monotonic() + self.connect_timeout_seconds
        while time.monotonic() < deadline:
            state = self._property(station_path, STATION_INTERFACE, "State")
            if str(state) == "connected":
                return network
            if str(state) == "disconnected":
                raise WifiError("Wi-Fi connection was rejected")
            time.sleep(self.poll_interval_seconds)
        raise WifiError("Wi-Fi connection timed out")

    def _wait_station_scanning(self, station_path: str) -> None:
        deadline = time.monotonic() + self.scan_timeout_seconds
        while time.monotonic() < deadline:
            if not bool(self._property(station_path, STATION_INTERFACE, "Scanning")):
                return
            time.sleep(self.poll_interval_seconds)
        raise WifiError("Wi-Fi scan timed out")

    def _managed_objects(self) -> Mapping[str, Mapping[str, Mapping[str, Any]]]:
        manager = self._interface("/", OBJECT_MANAGER_INTERFACE)
        try:
            return manager.GetManagedObjects()
        except Exception as exc:
            raise WifiError("iwd is not available") from exc

    @staticmethod
    def _station_path(objects: Mapping[str, Mapping[str, Mapping[str, Any]]]) -> str | None:
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
            raise WifiError(f"Wi-Fi state property {name!r} is unavailable") from exc

    def _interface(self, object_path: str, interface: str) -> Any:
        bus = self._system_bus()
        try:
            proxy = bus.get_object(IWD_SERVICE, object_path)
        except Exception as exc:
            raise WifiError("iwd D-Bus service is unavailable") from exc
        try:
            import dbus  # type: ignore[import-not-found]
        except ImportError as exc:
            raise WifiError("python3-dbus is missing from the live installer") from exc
        return dbus.Interface(proxy, interface)

    def _system_bus(self) -> Any:
        if self._bus is not None:
            return self._bus
        try:
            import dbus  # type: ignore[import-not-found]
        except ImportError as exc:
            raise WifiError("python3-dbus is missing from the live installer") from exc
        self._bus = dbus.SystemBus()
        return self._bus


def _profile_filename(ssid: str, security: WifiSecurity) -> str:
    _validate_ssid(ssid)
    if security not in {WifiSecurity.OPEN, WifiSecurity.PERSONAL}:
        raise ValueError("unsupported installer Wi-Fi security type")
    raw = ssid.encode("utf-8")
    safe = all(
        byte in b"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 _-"
        for byte in raw
    )
    stem = ssid if safe else "=" + raw.hex()
    suffix = ".open" if security is WifiSecurity.OPEN else ".psk"
    return stem + suffix


def _profile_content(security: WifiSecurity, passphrase: str) -> str:
    if security is WifiSecurity.OPEN:
        return "[Settings]\nAutoConnect=true\n"
    if security is WifiSecurity.PERSONAL:
        _validate_passphrase(passphrase)
        return f"[Security]\nPassphrase={passphrase}\n\n[Settings]\nAutoConnect=true\n"
    raise ValueError("unsupported installer Wi-Fi security type")


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
    temporary = path.with_name(f".{path.name}.greia-installer.tmp")
    try:
        temporary.write_text(content, encoding="utf-8")
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
