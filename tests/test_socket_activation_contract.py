"""POSTR1-P5-SOCKET-ACTIVATION-FIX: one shared native fd-store contract.

All three socket-activated Greia services (installer transaction, system
update, boot health) implement the same systemd native fd-store contract
in their Python entries (``LISTEN_FDS`` + ``socket.fromfd(3, ...)``), so
their units must all activate through that contract: no ``StandardInput``
inetd-style stdin passing (which leaves ``LISTEN_FDS`` unset and every
activation exiting fail-closed with ``no socket-activated file
descriptor``), started only via the matching socket, never enabled at
boot. The installed image must additionally enable
``greia-system-update.socket`` from ``sockets.target`` (alongside the
already-enabled boot-health socket); otherwise the shipped build never
listens for update clients.

Structured assertions (configparser + targeted reads), never full-file
snapshots. Includes a synthetic RED/GREEN sensitivity control proving the
checker itself can fail.
"""

from __future__ import annotations

import configparser
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD_IMAGE = ROOT / "build" / "build-image.sh"
# T01: installed-image service composition lives in the shared engine; the
# thin consumer invokes it through compose_root --role target.
COMPOSE_ENGINE = ROOT / "build" / "lib" / "compose.sh"

# (service unit, activating socket unit, Python entry, entry log name)
CONTRACTS: tuple[tuple[str, str, str, str], ...] = (
    (
        "build/installer-overlay/etc/systemd/system/greia-install-transaction.service",
        "greia-install-transaction.socket",
        "src/greia_installer/transaction_service.py",
        "greia-install-transaction",
    ),
    (
        "build/overlay/etc/systemd/system/greia-system-update.service",
        "greia-system-update.socket",
        "src/greia_platform/system_updates.py",
        "greia-system-update",
    ),
    (
        "build/overlay/etc/systemd/system/greia-boot-health.service",
        "greia-boot-health.socket",
        "src/greia_platform/boot_health_service.py",
        "greia-boot-health",
    ),
)


def check_native_fd_store(service_text: str, *, label: str) -> None:
    """Raise AssertionError unless unit text uses native fd-store activation.

    Shared checker: no ``StandardInput=socket`` (inetd-style), standard
    input disconnected (absent or ``null``), started only via its socket.
    """
    parser = configparser.ConfigParser(strict=False, interpolation=None)
    parser.optionxform = str  # type: ignore[assignment]
    parser.read_string(service_text)
    stdin_value = (
        parser.get("Service", "StandardInput").strip()
        if parser.has_option("Service", "StandardInput")
        else None
    )
    if stdin_value not in (None, "null"):
        raise AssertionError(
            f"{label}: must activate through the native fd store "
            f"(LISTEN_FDS + fd 3); got StandardInput={stdin_value!r} "
            "(StandardInput=socket leaves LISTEN_FDS unset)"
        )


def _parse_unit(path: Path) -> configparser.ConfigParser:
    parser = configparser.ConfigParser(strict=False, interpolation=None)
    parser.optionxform = str  # type: ignore[assignment]
    parser.read(path, encoding="utf-8")
    return parser


def _directive_values(path: Path, section: str, directive: str) -> set[str]:
    """Collect repeated systemd directives, which systemd treats cumulatively."""
    current = ""
    values: set[str] = set()
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("#", ";")):
            continue
        if line.startswith("[") and line.endswith("]"):
            current = line[1:-1].strip()
            continue
        key, separator, value = line.partition("=")
        if separator and current == section and key.strip() == directive:
            values.update(value.split())
    return values


def _installed_enable_tokens() -> set[str]:
    """Units the engine enables for the installed (target) role.

    The engine declares them as the ``target_services=(...)`` bash array that
    is passed to ``systemctl --root=... enable``; read that declaration rather
    than a particular line layout of the command.
    """
    tokens: set[str] = set()
    lines = COMPOSE_ENGINE.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        if line.strip() == "local target_services=(":
            for follow in lines[index + 1:]:
                content = follow.split("#", 1)[0].strip()
                if content == ")":
                    break
                tokens.update(content.split())
            break
    assert tokens, "target_services declaration not found in the composition engine"
    assert 'systemctl --root="$rootfs" enable "${target_services[@]}"' in (
        COMPOSE_ENGINE.read_text(encoding="utf-8")
    ), "target_services must be what the engine enables"
    consumer = BUILD_IMAGE.read_text(encoding="utf-8")
    assert 'compose_root --profile "$PROFILE_PATH" --role target' in consumer, (
        "thin consumer must compose the installed image through the engine"
    )
    return tokens


class NativeFdStoreTests(unittest.TestCase):
    def test_all_services_avoid_inetd_stdin_passing(self) -> None:
        for service_rel, _, _, label in CONTRACTS:
            with self.subTest(service=label):
                check_native_fd_store(
                    (ROOT / service_rel).read_text(encoding="utf-8"),
                    label=label,
                )

    def test_all_services_start_only_via_socket(self) -> None:
        for service_rel, socket_name, _, label in CONTRACTS:
            with self.subTest(service=label):
                parser = _parse_unit(ROOT / service_rel)
                self.assertIn(socket_name, _directive_values(ROOT / service_rel, "Unit", "Requires"))
                self.assertIn(socket_name, _directive_values(ROOT / service_rel, "Unit", "After"))
                self.assertNotIn("Install", parser.sections())

    def test_all_entries_consume_listen_fds_fd3(self) -> None:
        for _, _, entry_rel, label in CONTRACTS:
            with self.subTest(entry=label):
                text = (ROOT / entry_rel).read_text(encoding="utf-8")
                self.assertIn('os.environ.get("LISTEN_FDS"', text)
                self.assertIn("socket.fromfd(3", text)
                self.assertIn("no socket-activated file descriptor", text)


class UpdateSocketEnablementTests(unittest.TestCase):
    def test_installed_image_enables_update_socket(self) -> None:
        tokens = _installed_enable_tokens()
        self.assertIn(
            "greia-system-update.socket",
            tokens,
            "installed builds must listen for update clients from sockets.target",
        )
        self.assertIn(
            "greia-boot-health.socket",
            tokens,
            "boot-health socket enablement must be preserved",
        )


class SensitivityControlTests(unittest.TestCase):
    def test_prefixed_unit_fails_and_fixed_unit_passes(self) -> None:
        """Positive control: the checker (not the fixture) gates GREEN."""
        broken = (
            "[Unit]\nDescription=probe\nRequires=probe.socket\n"
            "After=probe.socket\n[Service]\nType=simple\n"
            "ExecStart=/usr/bin/python3 -m probe\nStandardInput=socket\n"
        )
        with self.assertRaises(AssertionError):
            check_native_fd_store(broken, label="synthetic-prefixed")
        fixed = broken.replace("StandardInput=socket\n", "")
        check_native_fd_store(fixed, label="synthetic-fixed")
        # The shipped update unit must agree with the synthetic GREEN shape.
        shipped = (
            ROOT
            / "build/overlay/etc/systemd/system/greia-system-update.service"
        ).read_text(encoding="utf-8")
        check_native_fd_store(shipped, label="greia-system-update")


if __name__ == "__main__":
    unittest.main()
