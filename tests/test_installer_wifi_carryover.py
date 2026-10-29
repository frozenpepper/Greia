"""Installer Wi-Fi carry-over: the joined network survives the install.

Source proof on temporary directories (no device, no iwd, no root):

- the UI sends only SSID hex + security, never the passphrase, and the
  choice is part of the digest-bound plan;
- the root side copies exactly the chosen network's live iwd profile, 0600
  in a 0700 directory, and nothing else from live iwd state;
- SSIDs can never address a path; symlinks/oversize/odd files are refused;
- every failure is non-fatal and logged without SSID or secret;
- no network joined means nothing is copied.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

from greia_installer.disk import BlockDevice, PcInternalTargetPolicy
from greia_installer.engine import InstallRequest, InstallationEngine
from greia_installer.transaction_service import (
    InstallTransactionService,
    PlatformInstallAuthority,
    ServiceState,
    TransactionServiceError,
    checked_service_settings,
)
from greia_installer.install_transaction import INSTALLER_UI_UID
from greia_installer.transaction_client import (
    InstallTransactionClient,
    TransactionClientError,
)
from greia_installer.wifi import IwdNetworkProfile, WifiNetwork, WifiSecurity
from greia_installer.wifi_carryover import (
    IwdProfileCarryover,
    WifiCarryoverChoice,
    WifiCarryoverError,
    carryover_snapshot_fields,
)
from greia_platform.hardware import HardwareDefaults, HardwareSettings
from greia_platform.privileged_channel import PeerCredential

from test_install_transaction_service import (
    FakeProbe,
    FakeResolver,
    FakeEngine,
    eligible_digest,
    make_disk,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SECRET = "correct horse battery"
PSK_FILE = (
    "[Security]\n"
    "PreSharedKey=00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff\n"
    f"Passphrase={SECRET.replace(' ', chr(92) + 's')}\n"
)


class RecordingLog:
    def __init__(self) -> None:
        self.events: list[str] = []

    def __call__(self, event: str, **fields: object) -> None:
        self.events.append(event + " " + " ".join(f"{k}={v}" for k, v in sorted(fields.items())))


def live_iwd(root: Path, files: dict[str, str]) -> Path:
    source = root / "live/var/lib/iwd"
    source.mkdir(parents=True)
    os.chmod(source, 0o700)
    for name, content in files.items():
        path = source / name
        path.write_text(content, encoding="utf-8")
        os.chmod(path, 0o600)
    return source


def target_root(root: Path) -> Path:
    target = root / "target"
    (target / "var/lib").mkdir(parents=True)
    return target


def copier(source: Path, log: RecordingLog | None = None) -> IwdProfileCarryover:
    return IwdProfileCarryover(source_dir=source, log=log or RecordingLog())


class CarryoverChoiceTests(unittest.TestCase):
    def test_ui_fields_carry_no_passphrase_and_round_trip(self) -> None:
        profile = IwdNetworkProfile.for_network(
            WifiNetwork("Family Wi-Fi", WifiSecurity.PERSONAL, -40.0, "/net/connman/iwd/0/1"),
            SECRET,
        )
        fields = carryover_snapshot_fields(profile)
        self.assertEqual(set(fields), {"wifi_ssid_hex", "wifi_security"})
        self.assertNotIn(SECRET, json.dumps(fields))
        self.assertNotIn("Family", json.dumps(fields))
        choice = WifiCarryoverChoice.from_snapshot(fields)
        self.assertEqual(choice, WifiCarryoverChoice("Family Wi-Fi", WifiSecurity.PERSONAL))
        self.assertEqual(choice.filename, "Family Wi-Fi.psk")
        self.assertEqual(carryover_snapshot_fields(None), {})

    def test_malformed_choices_are_refused(self) -> None:
        for bad in (
            {"wifi_ssid_hex": "41"},
            {"wifi_security": "psk"},
            {"wifi_ssid_hex": "zz", "wifi_security": "psk"},
            {"wifi_ssid_hex": "414", "wifi_security": "psk"},
            {"wifi_ssid_hex": "41" * 33, "wifi_security": "psk"},
            {"wifi_ssid_hex": "ff", "wifi_security": "psk"},
            {"wifi_ssid_hex": "41", "wifi_security": "8021x"},
            {"wifi_ssid_hex": "41", "wifi_security": "wep"},
        ):
            with self.subTest(bad=bad), self.assertRaises(WifiCarryoverError):
                WifiCarryoverChoice.from_snapshot(bad)
        self.assertIsNone(WifiCarryoverChoice.from_snapshot({"locale": "en"}))

    def test_traversal_ssid_derives_a_single_hex_basename(self) -> None:
        for ssid in ("../../etc/shadow", "/etc/passwd", "..", "a/b", "x://y"):
            choice = WifiCarryoverChoice(ssid, WifiSecurity.PERSONAL)
            with self.subTest(ssid=ssid):
                self.assertEqual(Path(choice.filename).name, choice.filename)
                self.assertTrue(choice.filename.startswith("="))
                self.assertNotIn("/", choice.filename)


class CarryoverCopyTests(unittest.TestCase):
    def test_copies_into_ab_network_namespace_and_rejects_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = live_iwd(root, {"Family Wi-Fi.psk": PSK_FILE})
            namespace = root / "network-state"
            namespace.mkdir()
            choice = WifiCarryoverChoice("Family Wi-Fi", WifiSecurity.PERSONAL)
            service = copier(source)
            self.assertTrue(service.carry_over_to_state_dir(choice, namespace).copied)
            self.assertEqual((namespace / choice.filename).read_text(), PSK_FILE)
            self.assertEqual(stat.S_IMODE(namespace.stat().st_mode), 0o700)
            self.assertEqual(stat.S_IMODE((namespace / choice.filename).stat().st_mode), 0o600)
            link = root / "link"
            link.symlink_to(namespace, target_is_directory=True)
            self.assertFalse(service.carry_over_to_state_dir(choice, link).copied)

    def test_copies_only_the_chosen_profile_private(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = live_iwd(
                root,
                {
                    "Family Wi-Fi.psk": PSK_FILE,
                    "Neighbour.psk": "[Security]\nPassphrase=other-secret\n",
                    "Cafe.open": "",
                },
            )
            target = target_root(root)
            log = RecordingLog()
            outcome = copier(source, log).carry_over(
                WifiCarryoverChoice("Family Wi-Fi", WifiSecurity.PERSONAL), target
            )
            self.assertTrue(outcome.copied, outcome)
            state = target / "var/lib/iwd"
            self.assertEqual(sorted(p.name for p in state.iterdir()), ["Family Wi-Fi.psk"])
            saved = state / "Family Wi-Fi.psk"
            self.assertEqual(saved.read_text(encoding="utf-8"), PSK_FILE)
            self.assertEqual(stat.S_IMODE(saved.stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(state.stat().st_mode), 0o700)
            logged = "\n".join(log.events)
            self.assertIn("outcome=copied", logged)
            self.assertNotIn("Family", logged)
            self.assertNotIn("correct", logged)

    def test_hex_named_ssid_is_copied_inside_the_state_dir(self) -> None:
        ssid = "../../etc/shadow"
        choice = WifiCarryoverChoice(ssid, WifiSecurity.PERSONAL)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = live_iwd(root, {choice.filename: PSK_FILE})
            target = target_root(root)
            self.assertTrue(copier(source).carry_over(choice, target).copied)
            self.assertTrue((target / "var/lib/iwd" / choice.filename).is_file())
            self.assertFalse((root / "etc").exists())
            self.assertFalse((target / "etc").exists())

    def test_open_network_copied_or_defaulted(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = live_iwd(root, {"Cafe.open": "[Settings]\nAutoConnect=true\n"})
            target = target_root(root)
            outcome = copier(source).carry_over(
                WifiCarryoverChoice("Cafe", WifiSecurity.OPEN), target
            )
            self.assertEqual((outcome.copied, outcome.reason), (True, "copied"))
            outcome = copier(source).carry_over(
                WifiCarryoverChoice("Library", WifiSecurity.OPEN), target
            )
            self.assertEqual((outcome.copied, outcome.reason), (True, "copied-open-default"))
            text = (target / "var/lib/iwd/Library.open").read_text(encoding="utf-8")
            self.assertIn("AutoConnect=true", text)

    def test_refusals_are_non_fatal_and_write_nothing(self) -> None:
        cases = {
            "source-missing": {},
            "source-invalid": {"Home.psk": "[Settings]\nAutoConnect=true\n"},
            "source-too-large": {"Home.psk": PSK_FILE + "#" * 9000 + "\n"},
        }
        for reason, files in cases.items():
            with self.subTest(reason=reason), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                source = live_iwd(root, files)
                target = target_root(root)
                outcome = copier(source).carry_over(
                    WifiCarryoverChoice("Home", WifiSecurity.PERSONAL), target
                )
                self.assertFalse(outcome.copied)
                self.assertEqual(outcome.reason, reason)
                self.assertFalse((target / "var/lib/iwd/Home.psk").exists())

    def test_symlinked_source_profile_is_never_followed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = live_iwd(root, {})
            elsewhere = root / "elsewhere.psk"
            elsewhere.write_text(PSK_FILE, encoding="utf-8")
            os.chmod(elsewhere, 0o600)
            (source / "Home.psk").symlink_to(elsewhere)
            target = target_root(root)
            outcome = copier(source).carry_over(
                WifiCarryoverChoice("Home", WifiSecurity.PERSONAL), target
            )
            self.assertEqual((outcome.copied, outcome.reason), (False, "source-unsafe"))

    def test_symlinked_target_state_dir_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = live_iwd(root, {"Home.psk": PSK_FILE})
            target = target_root(root)
            escape = root / "escape"
            escape.mkdir()
            (target / "var/lib/iwd").symlink_to(escape)
            outcome = copier(source).carry_over(
                WifiCarryoverChoice("Home", WifiSecurity.PERSONAL), target
            )
            self.assertFalse(outcome.copied)
            self.assertEqual(list(escape.iterdir()), [])

    def test_no_network_chosen_copies_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = live_iwd(root, {"Home.psk": PSK_FILE})
            target = target_root(root)
            outcome = copier(source).carry_over(None, target)
            self.assertFalse(outcome.copied)
            self.assertFalse((target / "var/lib/iwd").exists())


def _settings() -> HardwareSettings:
    defaults = HardwareDefaults.load(PROJECT_ROOT / "runtime/hardware-settings.toml")
    return HardwareSettings(
        schema_version=defaults.schema_version,
        touchpad_tap=defaults.touchpad_tap,
        touchpad_speed=defaults.touchpad_speed,
        mouse_speed=defaults.mouse_speed,
        natural_scrolling=defaults.natural_scrolling,
        resolution=defaults.resolution,
        keyboard_layout=defaults.keyboard_layout,
    )


class _Runner:
    def run(self, command, *, check=True):
        return subprocess.CompletedProcess(command, 0, "", "")


def _block_device() -> BlockDevice:
    return BlockDevice(
        name="sda",
        path=Path("/dev/sda"),
        size_bytes=7_500_000_000,
        device_type="disk",
        model="Acer internal drive",
        serial="SERIAL-1",
        transport="ata",
        removable=False,
        read_only=False,
        mountpoints=(),
        wwn="WWN-1",
        major_minor="8:0",
    )


class EngineCarryoverTests(unittest.TestCase):
    def _configure(self, files: dict[str, str], choice: WifiCarryoverChoice | None):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        source = live_iwd(root, files)
        target = target_root(root)
        defaults = target / "opt/greia-os/runtime/hardware-settings.toml"
        defaults.parent.mkdir(parents=True)
        defaults.write_bytes((PROJECT_ROOT / "runtime/hardware-settings.toml").read_bytes())
        engine = InstallationEngine(
            project_root=PROJECT_ROOT, runner=_Runner(), wifi_carryover=copier(source)
        )
        request = InstallRequest(
            _block_device(), target / "unused", _settings(), wifi_carryover=choice
        )
        engine._write_initial_configuration(target, request)
        record_text = (target / "etc/greia-os/install-record.json").read_text(encoding="utf-8")
        return target, json.loads(record_text), record_text

    def test_engine_copies_the_chosen_network_and_records_only_a_boolean(self) -> None:
        target, record, text = self._configure(
            {"Home.psk": PSK_FILE}, WifiCarryoverChoice("Home", WifiSecurity.PERSONAL)
        )
        self.assertTrue(record["wifi_configured"])
        self.assertTrue((target / "var/lib/iwd/Home.psk").is_file())
        self.assertNotIn("Home", text)
        self.assertNotIn("correct", text)

    def test_engine_copy_failure_is_not_fatal(self) -> None:
        target, record, _ = self._configure(
            {}, WifiCarryoverChoice("Home", WifiSecurity.PERSONAL)
        )
        self.assertFalse(record["wifi_configured"])
        self.assertFalse((target / "var/lib/iwd/Home.psk").exists())

    def test_engine_without_network_copies_nothing(self) -> None:
        target, record, _ = self._configure({"Home.psk": PSK_FILE}, None)
        self.assertFalse(record["wifi_configured"])
        self.assertFalse((target / "var/lib/iwd").exists())


class ServiceCarryoverTests(unittest.TestCase):
    def _service(self):
        probe = FakeProbe([make_disk()])
        engine = FakeEngine()
        state = ServiceState(
            payload=Path("/run/live/medium/payload/pip-rootfs.squashfs"),
            payload_digest=Path("/etc/greia-os/expected-payload.sha256"),
            project_root=PROJECT_ROOT,
            compatible_profile_id="profile-test",
            platform_family="legacy-x86",
            architecture="i386",
            target_policy_id="pc-internal-v1",
            layout_adapter_id="legacy-bios-ab-v1",
            boot_backend="grub-ab-v1",
            slot_bytes=1024**3,
            persist_minimum_bytes=256 * 1024 * 1024,
        )
        authority = PlatformInstallAuthority(
            policy=PcInternalTargetPolicy(),
            compatible_profile="profile-test",
            probe=probe,  # type: ignore[arg-type]
            live_resolver=FakeResolver(),  # type: ignore[arg-type]
        )
        service = InstallTransactionService(
            authority=authority, state=state, engine_factory=lambda: engine  # type: ignore[return-value]
        )

        class _H:
            pass

        harness = _H()
        harness.authority = authority
        client = InstallTransactionClient(
            lambda raw: service.handle_request(
                raw, peer=PeerCredential(uid=INSTALLER_UI_UID), boot_state="installer_ready"
            )
        )
        return harness, client, engine

    def _install(self, extra: dict[str, str]):
        harness, client, engine = self._service()
        snapshot = {"locale": "en", **extra}
        prepared = client.prepare(
            expected_target_identity=eligible_digest(harness),  # type: ignore[arg-type]
            compatible_profile_id="profile-test",
            settings_snapshot=snapshot,
        )
        client.execute(
            transaction_nonce=prepared.transaction_nonce, plan_digest=prepared.plan_digest
        )
        return prepared, engine.requests[0]

    def test_confirmed_choice_reaches_the_engine_through_the_plan(self) -> None:
        choice = WifiCarryoverChoice("Family Wi-Fi", WifiSecurity.PERSONAL)
        prepared, request = self._install(choice.snapshot_fields())
        self.assertEqual(prepared.plan["settings"]["wifi_security"], "psk")
        self.assertEqual(request.wifi_carryover, choice)
        self.assertIsNone(request.wifi_profile)

    def test_no_choice_means_no_carryover(self) -> None:
        _, request = self._install({})
        self.assertIsNone(request.wifi_carryover)

    def test_malformed_choice_refused_at_prepare(self) -> None:
        harness, client, engine = self._service()
        with self.assertRaises(TransactionClientError):
            client.prepare(
                expected_target_identity=eligible_digest(harness),  # type: ignore[arg-type]
                compatible_profile_id="profile-test",
                settings_snapshot={"wifi_ssid_hex": "41"},
            )
        with self.assertRaises(TransactionServiceError):
            checked_service_settings({"wifi_ssid_hex": "41", "wifi_security": "8021x"})
        self.assertEqual(engine.requests, [])


if __name__ == "__main__":
    unittest.main()
