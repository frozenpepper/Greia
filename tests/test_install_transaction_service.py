"""A8-INSTALL-SVC: unprivileged UI split from the root transaction service.

Source-gate proof for Step 8A.5 on fakes with zero disk contact:

- the root service prepares nonce+digest and executes only through a live,
  revalidated nonce, rematerializing target/settings/layout/payload from
  Greia-owned service state;
- any inventory refresh or material target-state change invalidates the
  prepared plan and the UI confirmation;
- requests can never smuggle raw paths/commands/devices/URLs;
- the UI modules and units carry no destructive disk authority.

No valued physical disk is touched: probes, resolvers, runners and engines
are fakes; the only destructive backend (``InstallationEngine``) is never
constructed here.
"""

from __future__ import annotations

import hashlib
import json
import socket
import tempfile
import unittest
from pathlib import Path
from typing import Mapping

from greia_installer.disk import (
    DeviceObservation,
    DiskInventory,
    LiveMediaAncestry,
    PcInternalTargetPolicy,
)
from greia_installer.engine import InstallResult
from greia_installer.install_transaction import (
    INSTALL_TRANSACTION_ALLOWED_UIDS,
    INSTALLER_UI_UID,
    InstallTransactionError,
)
from greia_installer.transaction_client import (
    InstallTransactionClient,
    PreparedConfirmation,
    TransactionClientError,
    read_compatible_profile_id,
)
from greia_installer.transaction_service import (
    PlatformInstallAuthority,
    ServiceState,
    InstallTransactionService,
    TransactionServiceError,
    checked_service_settings,
    hardware_settings_from_snapshot,
)
from greia_platform.privileged_channel import PeerCredential, decode_response, encode_request


PROJECT_ROOT = Path(__file__).resolve().parents[1]
GIB = 1024**3

UI_PEER = PeerCredential(uid=INSTALLER_UI_UID)
ROOT_PEER = PeerCredential(uid=0)
FOREIGN_PEER = PeerCredential(uid=1000)
READY = "installer_ready"


def make_disk(
    name: str = "sda",
    *,
    serial: str = "SERIAL-1",
    wwn: str = "WWN-1",
    size_bytes: int = 8 * GIB,
    transport: str = "sata",
    removable: bool = False,
    read_only: bool = False,
    mountpoints: tuple[Path, ...] = (),
    model: str = "Test disk",
    major_minor: str = "8:0",
) -> DeviceObservation:
    return DeviceObservation(
        name=name,
        path=Path(f"/dev/{name}"),
        size_bytes=size_bytes,
        device_type="disk",
        model=model,
        serial=serial,
        transport=transport,
        removable=removable,
        read_only=read_only,
        mountpoints=mountpoints,
        wwn=wwn,
        major_minor=major_minor,
    )


class FakeProbe:
    def __init__(self, devices: list[DeviceObservation]) -> None:
        self.devices = list(devices)
        self.probe_calls = 0

    def probe(self) -> DiskInventory:
        self.probe_calls += 1
        return DiskInventory(tuple(self.devices), generation=self.probe_calls)


class FakeResolver:
    def __init__(self, ancestry: LiveMediaAncestry | None = None) -> None:
        self._ancestry = ancestry or LiveMediaAncestry.empty()
        self.resolve_calls = 0

    def resolve(self, inventory: object = None) -> LiveMediaAncestry:
        self.resolve_calls += 1
        return self._ancestry


class FakeEngine:
    def __init__(self) -> None:
        self.requests: list[object] = []

    def install(self, request: object, on_progress: object = None) -> InstallResult:
        self.requests.append(request)
        return InstallResult()


class ServiceHarness:
    """One service on fakes: fresh probe per call, recording fake engine."""

    def __init__(
        self,
        devices: list[DeviceObservation],
        *,
        profile_id: str = "profile-test",
        slot_bytes: int = 1 * GIB,
        persist_minimum_bytes: int = 256 * 1024 * 1024,
        ancestry: LiveMediaAncestry | None = None,
    ) -> None:
        self.probe = FakeProbe(devices)
        self.resolver = FakeResolver(ancestry)
        self.engine = FakeEngine()
        self.state = ServiceState(
            payload=Path("/run/live/medium/payload/pip-rootfs.squashfs"),
            payload_digest=Path("/etc/greia-os/expected-payload.sha256"),
            project_root=PROJECT_ROOT,
            compatible_profile_id=profile_id,
            platform_family="legacy-x86",
            architecture="i386",
            target_policy_id="pc-internal-v1",
            layout_adapter_id="legacy-bios-ab-v1",
            boot_backend="grub-ab-v1",
            slot_bytes=slot_bytes,
            persist_minimum_bytes=persist_minimum_bytes,
        )
        self.authority = PlatformInstallAuthority(
            policy=PcInternalTargetPolicy(),
            compatible_profile=profile_id,
            probe=self.probe,  # type: ignore[arg-type]
            live_resolver=self.resolver,  # type: ignore[arg-type]
        )
        self.service = InstallTransactionService(
            authority=self.authority,
            state=self.state,
            engine_factory=lambda: self.engine,  # type: ignore[return-value]
        )

    def client(self) -> InstallTransactionClient:
        def transport(raw: bytes) -> bytes:
            return self.service.handle_request(raw, peer=UI_PEER, boot_state=READY)

        return InstallTransactionClient(transport)

    def prepare_snapshot(self, settings: dict[str, str] | None = None) -> dict[str, str]:
        snapshot = {
            "touchpad_tap": "false",
            "touchpad_speed": "0.35",
            "mouse_speed": "0.0",
            "natural_scrolling": "false",
            "resolution": "auto",
            "keyboard_layout": "us",
            "mic_gain": "2.0",
            "disable_while_typing": "false",
            "locale": "en",
        }
        if settings:
            snapshot.update(settings)
        return snapshot


def eligible_digest(harness: ServiceHarness) -> str:
    targets = harness.authority.list_targets()
    eligible = [item for item in targets if item.eligible]
    assert len(eligible) == 1, f"expected one eligible target, got {len(eligible)}"
    return eligible[0].identity_digest


class PrepareExecuteServiceTests(unittest.TestCase):
    def test_prepare_execute_installs_once_with_service_owned_facts(self) -> None:
        harness = ServiceHarness([make_disk()])
        client = harness.client()
        digest = eligible_digest(harness)
        snapshot = harness.prepare_snapshot({"touchpad_tap": "true"})
        prepared = client.prepare(
            expected_target_identity=digest,
            compatible_profile_id="profile-test",
            settings_snapshot=snapshot,
        )
        self.assertEqual(prepared.plan["target_identity_digest"], digest)
        receipt = client.execute(
            transaction_nonce=prepared.transaction_nonce,
            plan_digest=prepared.plan_digest,
        )
        self.assertEqual(receipt.target_identity, digest)
        self.assertEqual(len(harness.engine.requests), 1)
        request = harness.engine.requests[0]
        assert hasattr(request, "payload")
        self.assertEqual(request.payload, harness.state.payload)
        self.assertEqual(request.payload_digest, harness.state.payload_digest)
        self.assertTrue(request.hardware_settings.touchpad_tap)
        self.assertEqual(request.locale, "en")
        # Single-use: the same nonce never executes twice.
        with self.assertRaises(TransactionClientError):
            client.execute(
                transaction_nonce=prepared.transaction_nonce,
                plan_digest=prepared.plan_digest,
            )
        self.assertEqual(len(harness.engine.requests), 1)

    def test_wrong_digest_never_reaches_the_engine(self) -> None:
        harness = ServiceHarness([make_disk()])
        client = harness.client()
        digest = eligible_digest(harness)
        prepared = client.prepare(
            expected_target_identity=digest,
            compatible_profile_id="profile-test",
            settings_snapshot=harness.prepare_snapshot(),
        )
        other = hashlib.sha256(b"other-plan").hexdigest()
        with self.assertRaises(TransactionClientError):
            client.execute(
                transaction_nonce=prepared.transaction_nonce, plan_digest=other
            )
        self.assertEqual(harness.engine.requests, [])

    def test_unknown_nonce_never_reaches_the_engine(self) -> None:
        harness = ServiceHarness([make_disk()])
        client = harness.client()
        with self.assertRaises(TransactionClientError):
            client.execute(
                transaction_nonce="0" * 32, plan_digest="0" * 64
            )
        self.assertEqual(harness.engine.requests, [])

    def test_inventory_refresh_between_prepare_and_execute_invalidates(self) -> None:
        disk = make_disk()
        harness = ServiceHarness([disk])
        client = harness.client()
        digest = eligible_digest(harness)
        prepared = client.prepare(
            expected_target_identity=digest,
            compatible_profile_id="profile-test",
            settings_snapshot=harness.prepare_snapshot(),
        )
        # Material state change with the same identity: a mount appears.
        harness.probe.devices = [
            make_disk(mountpoints=(Path("/mnt/sneaky"),)),
        ]
        with self.assertRaisesRegex(TransactionClientError, "invalid|refus|stopped"):
            client.execute(
                transaction_nonce=prepared.transaction_nonce,
                plan_digest=prepared.plan_digest,
            )
        self.assertEqual(harness.engine.requests, [])

    def test_target_ineligibility_change_invalidates(self) -> None:
        harness = ServiceHarness([make_disk()])
        client = harness.client()
        digest = eligible_digest(harness)
        prepared = client.prepare(
            expected_target_identity=digest,
            compatible_profile_id="profile-test",
            settings_snapshot=harness.prepare_snapshot(),
        )
        harness.probe.devices = [make_disk(removable=True)]
        with self.assertRaises(TransactionClientError):
            client.execute(
                transaction_nonce=prepared.transaction_nonce,
                plan_digest=prepared.plan_digest,
            )
        self.assertEqual(harness.engine.requests, [])

    def test_target_disappearance_invalidates(self) -> None:
        harness = ServiceHarness([make_disk()])
        client = harness.client()
        digest = eligible_digest(harness)
        prepared = client.prepare(
            expected_target_identity=digest,
            compatible_profile_id="profile-test",
            settings_snapshot=harness.prepare_snapshot(),
        )
        harness.probe.devices = []
        with self.assertRaises(TransactionClientError):
            client.execute(
                transaction_nonce=prepared.transaction_nonce,
                plan_digest=prepared.plan_digest,
            )
        self.assertEqual(harness.engine.requests, [])

    def test_execute_rematerializes_the_live_locator_not_stale_state(self) -> None:
        harness = ServiceHarness([make_disk(name="sda", major_minor="8:0")])
        client = harness.client()
        digest = eligible_digest(harness)
        prepared = client.prepare(
            expected_target_identity=digest,
            compatible_profile_id="profile-test",
            settings_snapshot=harness.prepare_snapshot(),
        )
        # Same durable identity re-enumerated at a new session locator.
        harness.probe.devices = [make_disk(name="sdb", major_minor="8:16")]
        # Identity digest is locator-free, so the plan survives; the engine
        # must receive the live observation, never the stale /dev/sda path.
        new_digest = eligible_digest(harness)
        self.assertEqual(new_digest, digest)
        client.execute(
            transaction_nonce=prepared.transaction_nonce,
            plan_digest=prepared.plan_digest,
        )
        self.assertEqual(len(harness.engine.requests), 1)
        request = harness.engine.requests[0]
        self.assertEqual(request.target.path, Path("/dev/sdb"))

    def test_layout_misfit_refuses_before_any_engine_call(self) -> None:
        harness = ServiceHarness(
            [make_disk(size_bytes=4 * GIB)],
            slot_bytes=2 * GIB,
        )
        client = harness.client()
        digest = eligible_digest(harness)
        prepared = client.prepare(
            expected_target_identity=digest,
            compatible_profile_id="profile-test",
            settings_snapshot=harness.prepare_snapshot(),
        )
        with self.assertRaisesRegex(TransactionClientError, "layout|fit|REFUSED"):
            client.execute(
                transaction_nonce=prepared.transaction_nonce,
                plan_digest=prepared.plan_digest,
            )
        self.assertEqual(harness.engine.requests, [])

    def test_foreign_peer_is_refused_without_engine_contact(self) -> None:
        harness = ServiceHarness([make_disk()])
        digest = eligible_digest(harness)
        raw = encode_request(
            "PREPARE_PLAN",
            {
                "expected_target_identity": digest,
                "compatible_profile_id": "profile-test",
                "settings_snapshot": harness.prepare_snapshot(),
            },
        )
        with self.assertRaises(InstallTransactionError):
            harness.service.handle_request(raw, peer=FOREIGN_PEER, boot_state=READY)
        self.assertEqual(harness.engine.requests, [])

    def test_root_peer_keeps_protocol_access(self) -> None:
        self.assertIn(0, INSTALL_TRANSACTION_ALLOWED_UIDS)
        self.assertIn(INSTALLER_UI_UID, INSTALL_TRANSACTION_ALLOWED_UIDS)


class SmugglingNegativeTests(unittest.TestCase):
    def test_smuggled_device_key_refused_at_prepare(self) -> None:
        harness = ServiceHarness([make_disk()])
        params = {
            "expected_target_identity": eligible_digest(harness),
            "compatible_profile_id": "profile-test",
            "settings_snapshot": harness.prepare_snapshot(),
            "device": "sda",
        }
        with self.assertRaises((InstallTransactionError, TransactionClientError)):
            harness.service.prepare(params)  # type: ignore[arg-type]
        self.assertEqual(harness.engine.requests, [])

    def test_absolute_path_value_rejected_before_framing(self) -> None:
        harness = ServiceHarness([make_disk()])
        client = harness.client()
        with self.assertRaises(TransactionClientError):
            client.prepare(
                expected_target_identity=eligible_digest(harness),
                compatible_profile_id="profile-test",
                settings_snapshot={"locale": "/etc/shadow"},
            )
        self.assertEqual(harness.engine.requests, [])

    def test_unknown_settings_key_refused_at_prepare(self) -> None:
        harness = ServiceHarness([make_disk()])
        client = harness.client()
        with self.assertRaises(TransactionClientError):
            client.prepare(
                expected_target_identity=eligible_digest(harness),
                compatible_profile_id="profile-test",
                settings_snapshot=harness.prepare_snapshot({"mountpoint": "/mnt/x"}),
            )
        self.assertEqual(harness.engine.requests, [])

    def test_raw_execute_params_rejected(self) -> None:
        harness = ServiceHarness([make_disk()])
        raw = json.dumps(
            {
                "protocol_version": 1,
                "op": "EXECUTE",
                "params": {
                    "transaction_nonce": "0" * 32,
                    "plan_digest": "0" * 64,
                    "command": "wipefs --all",
                },
            }
        ).encode()
        with self.assertRaises(InstallTransactionError):
            harness.service.handle_request(raw, peer=UI_PEER, boot_state=READY)
        self.assertEqual(harness.engine.requests, [])

    def test_unknown_op_rejected(self) -> None:
        harness = ServiceHarness([make_disk()])
        with self.assertRaises(InstallTransactionError):
            harness.service.handle_request(
                encode_request("FORMAT_DISK", {}), peer=UI_PEER, boot_state=READY
            )


class ConfirmationInvalidationTests(unittest.TestCase):
    def _confirmation(self, settings: dict[str, str] | None = None):
        from greia_installer.transaction_client import PreparedPlan

        snapshot = {
            "touchpad_tap": "false",
            "resolution": "auto",
            "locale": "en",
        }
        if settings:
            snapshot.update(settings)
        plan = {
            "schema_version": 1,
            "target_identity_digest": "a" * 64,
            "target_policy_id": "pc-internal-v1",
            "target_display": "Test disk · 8.0 GiB",
            "compatible_profile_id": "profile-test",
            "settings": dict(snapshot),
            "steps": ["verify-target"],
        }
        from greia_installer.install_transaction import canonical_plan_bytes

        digest = hashlib.sha256(canonical_plan_bytes(plan)).hexdigest()
        prepared = PreparedPlan(
            transaction_nonce="b" * 32, plan=plan, plan_digest=digest
        )
        return PreparedConfirmation(
            prepared=prepared,
            expected_target_identity="a" * 64,
            expected_display_summary="Test disk · 8.0 GiB",
            settings_snapshot=dict(snapshot),
        ), snapshot

    def _live(self, **overrides: object) -> dict[str, dict[str, object]]:
        facts: dict[str, dict[str, object]] = {
            "a" * 64: {"eligible": True, "display_summary": "Test disk · 8.0 GiB"}
        }
        facts["a" * 64].update(overrides)  # type: ignore[typeddict-item]
        return facts

    def test_fresh_facts_keep_confirmation(self) -> None:
        confirmation, snapshot = self._confirmation()
        self.assertTrue(
            confirmation.still_valid(live_targets=self._live(), current_settings=snapshot)
        )

    def test_ineligible_target_invalidates(self) -> None:
        confirmation, snapshot = self._confirmation()
        self.assertFalse(
            confirmation.still_valid(
                live_targets=self._live(eligible=False), current_settings=snapshot
            )
        )

    def test_disappeared_target_invalidates(self) -> None:
        confirmation, snapshot = self._confirmation()
        self.assertFalse(
            confirmation.still_valid(live_targets={}, current_settings=snapshot)
        )

    def test_display_change_invalidates(self) -> None:
        confirmation, snapshot = self._confirmation()
        self.assertFalse(
            confirmation.still_valid(
                live_targets=self._live(display_summary="Other disk · 8.0 GiB"),
                current_settings=snapshot,
            )
        )

    def test_settings_drift_invalidates(self) -> None:
        confirmation, _ = self._confirmation()
        drifted = dict(self._confirmation()[1])
        drifted["resolution"] = "800x600"
        self.assertFalse(
            confirmation.still_valid(
                live_targets=self._live(), current_settings=drifted
            )
        )


class ClientVerificationTests(unittest.TestCase):
    def test_client_rejects_tampered_plan_digest(self) -> None:
        harness = ServiceHarness([make_disk()])
        real = harness.client()._transport

        def tampering(raw: bytes) -> bytes:
            response = real(raw)
            transaction_id, op, payload = decode_response(response)
            if op == "PREPARE_PLAN":
                payload = dict(payload)
                payload["plan_digest"] = "f" * 64
                from greia_platform.privileged_channel import encode_response

                return encode_response(transaction_id, op, payload)
            return response

        client = InstallTransactionClient(tampering)
        with self.assertRaisesRegex(TransactionClientError, "digest"):
            client.prepare(
                expected_target_identity=eligible_digest(harness),
                compatible_profile_id="profile-test",
                settings_snapshot=harness.prepare_snapshot(),
            )

    def test_client_rejects_plan_bound_to_another_target(self) -> None:
        harness = ServiceHarness([make_disk()])
        real = harness.client()._transport

        def swapping(raw: bytes) -> bytes:
            response = real(raw)
            transaction_id, op, payload = decode_response(response)
            if op == "PREPARE_PLAN":
                from greia_installer.install_transaction import canonical_plan_bytes
                from greia_platform.privileged_channel import encode_response

                payload = dict(payload)
                plan = dict(payload["plan"])
                plan["target_identity_digest"] = "c" * 64
                payload["plan"] = plan
                payload["plan_digest"] = hashlib.sha256(
                    canonical_plan_bytes(plan)
                ).hexdigest()
                return encode_response(transaction_id, op, payload)
            return response

        client = InstallTransactionClient(swapping)
        with self.assertRaisesRegex(TransactionClientError, "bound"):
            client.prepare(
                expected_target_identity=eligible_digest(harness),
                compatible_profile_id="profile-test",
                settings_snapshot=harness.prepare_snapshot(),
            )

    def test_unreachable_service_fails_closed(self) -> None:
        def dead(_raw: bytes) -> bytes:
            raise OSError("no socket")

        client = InstallTransactionClient(dead)
        with self.assertRaises(TransactionClientError):
            client.prepare(
                expected_target_identity="a" * 64,
                compatible_profile_id="profile-test",
                settings_snapshot={},
            )

    def test_execute_uses_the_long_wait_transport_only(self) -> None:
        harness = ServiceHarness([make_disk()])
        used: list[str] = []

        def short(raw: bytes) -> bytes:
            used.append("short")
            return harness.service.handle_request(raw, peer=UI_PEER, boot_state=READY)

        def long(raw: bytes) -> bytes:
            used.append("long")
            return harness.service.handle_request(raw, peer=UI_PEER, boot_state=READY)

        client = InstallTransactionClient(short, execute_transport=long)
        digest = eligible_digest(harness)
        prepared = client.prepare(
            expected_target_identity=digest,
            compatible_profile_id="profile-test",
            settings_snapshot=harness.prepare_snapshot(),
        )
        client.execute(
            transaction_nonce=prepared.transaction_nonce,
            plan_digest=prepared.plan_digest,
        )
        self.assertEqual(used, ["short", "long"])
        self.assertEqual(len(harness.engine.requests), 1)


class SettingsMappingTests(unittest.TestCase):
    def test_full_snapshot_maps_to_platform_settings(self) -> None:
        settings, locale = hardware_settings_from_snapshot(
            {
                "touchpad_tap": "true",
                "touchpad_speed": "0.5",
                "mouse_speed": 0,
                "natural_scrolling": False,
                "resolution": "1024x600",
                "keyboard_layout": "de",
                "mic_gain": "2.5",
                "disable_while_typing": "true",
                "locale": "it",
            },
            project_root=PROJECT_ROOT,
        )
        self.assertTrue(settings.touchpad_tap)
        self.assertAlmostEqual(settings.touchpad_speed, 0.5)
        self.assertEqual(settings.resolution, "1024x600")
        self.assertEqual(settings.keyboard_layout, "de")
        self.assertEqual(locale, "it")

    def test_unknown_key_refused(self) -> None:
        with self.assertRaises(TransactionServiceError):
            checked_service_settings({"mountpoint": "/mnt/x"})

    def test_malformed_scalars_refused(self) -> None:
        for snapshot in (
            {"touchpad_tap": "yes"},
            {"touchpad_speed": "fast"},
            {"touchpad_speed": "99.0"},
            {"resolution": ""},
            {"locale": "xx-not-a-locale"},
        ):
            with self.subTest(snapshot=snapshot):
                with self.assertRaises(TransactionServiceError):
                    checked_service_settings(snapshot)


class ServiceStateTests(unittest.TestCase):
    def _manifest(self, root: Path, **overrides: object) -> Path:
        manifest = {
            "profile": {"id": "profile-test"},
            "platform": {"family": "legacy-x86"},
            "base": {"architecture": "i386"},
            "storage": {
                "layout_adapter": "legacy-bios-ab-v1",
                "system_slot_bytes": 1 * GIB,
                "persistent_minimum_bytes": 256 * 1024 * 1024,
            },
            "installer": {"target_policy": "pc-internal-v1"},
            "updates": {"boot_backend": "grub-ab-v1"},
        }
        for dotted, value in overrides.items():
            section, key = dotted.split(".", 1)
            manifest[section][key] = value  # type: ignore[index]
        path = root / "target-image-profile.json"
        path.write_text(json.dumps(manifest), encoding="utf-8")
        return path

    def test_from_target_profile_loads_release_facts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            profile = self._manifest(root)
            state = ServiceState.from_target_profile(
                profile,
                payload=Path("/run/live/medium/payload/pip-rootfs.squashfs"),
                payload_digest=Path("/etc/greia-os/expected-payload.sha256"),
                project_root=Path("/opt/greia-os"),
            )
            self.assertEqual(state.compatible_profile_id, "profile-test")
            self.assertEqual(state.layout_adapter_id, "legacy-bios-ab-v1")
            self.assertEqual(state.target_policy_id, "pc-internal-v1")
            self.assertEqual(state.boot_backend, "grub-ab-v1")

    def test_from_target_profile_refuses_bad_manifests(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            missing = root / "absent.json"
            with self.assertRaises(TransactionServiceError):
                ServiceState.from_target_profile(
                    missing,
                    payload=Path("/payload"),
                    payload_digest=Path("/digest"),
                    project_root=Path("/opt/greia-os"),
                )
            broken = root / "broken.json"
            broken.write_text("not json", encoding="utf-8")
            with self.assertRaises(TransactionServiceError):
                ServiceState.from_target_profile(
                    broken,
                    payload=Path("/payload"),
                    payload_digest=Path("/digest"),
                    project_root=Path("/opt/greia-os"),
                )
            unknown_policy = self._manifest(root, **{"installer.target_policy": "nope"})
            with self.assertRaises(TransactionServiceError):
                ServiceState.from_target_profile(
                    unknown_policy,
                    payload=Path("/payload"),
                    payload_digest=Path("/digest"),
                    project_root=Path("/opt/greia-os"),
                )

    def test_read_compatible_profile_id(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            profile = self._manifest(root)
            self.assertEqual(read_compatible_profile_id(profile), "profile-test")
            with self.assertRaises(TransactionClientError):
                read_compatible_profile_id(root / "absent.json")


class SocketServeTests(unittest.TestCase):
    def test_prepare_and_execute_round_trip_over_a_socket(self) -> None:
        from greia_installer.transaction_service import handle_connection
        from greia_platform.privileged_channel import decode_response

        harness = ServiceHarness([make_disk()])
        digest = eligible_digest(harness)

        def one_shot(raw: bytes) -> bytes:
            local, remote = socket.socketpair()
            try:
                local.sendall(raw)
                local.shutdown(socket.SHUT_WR)
                handle_connection(remote, service=harness.service, peer_uid=INSTALLER_UI_UID)
                remote = None  # type: ignore[assignment]
                chunks: list[bytes] = []
                while True:
                    chunk = local.recv(4096)
                    if not chunk:
                        break
                    chunks.append(chunk)
                return b"".join(chunks)
            finally:
                local.close()

        prepare_raw = encode_request(
            "PREPARE_PLAN",
            {
                "expected_target_identity": digest,
                "compatible_profile_id": "profile-test",
                "settings_snapshot": harness.prepare_snapshot(),
            },
        )
        _, op, prepared = decode_response(one_shot(prepare_raw))
        self.assertEqual(op, "PREPARE_PLAN")
        self.assertEqual(prepared["status"], "PREPARED")
        execute_raw = encode_request(
            "EXECUTE",
            {
                "transaction_nonce": prepared["transaction_nonce"],
                "plan_digest": prepared["plan_digest"],
            },
        )
        _, op, receipt = decode_response(one_shot(execute_raw))
        self.assertEqual(op, "EXECUTE")
        self.assertEqual(receipt["status"], "INSTALLED")
        self.assertEqual(receipt["target_identity"], digest)
        self.assertEqual(len(harness.engine.requests), 1)


class UiAuthorityGuardTests(unittest.TestCase):
    """The unprivileged UI carries no destructive disk authority."""

    UI_FILES = (
        "src/greia_installer/main.py",
        "src/greia_installer/entrypoint.py",
        "src/greia_installer/transaction_client.py",
        "src/greia_installer/composition.py",
    )

    # Destructive installer commands owned solely by the root service engine.
    # Quoted command forms keep display prose ("mount points") out of scope.
    DISK_TOKENS = (
        "wipefs",
        "mkfs.ext4",
        "grub-install",
        "unsquashfs",
        "partprobe",
        "udevadm",
        "blkid",
        '"parted"',
        "'parted'",
        '"mount"',
        "'mount'",
        '"chroot"',
        "--rbind",
    )

    def _read(self, relative: str) -> str:
        return (PROJECT_ROOT / relative).read_text(encoding="utf-8")

    def test_ui_modules_carry_no_destructive_disk_commands(self) -> None:
        for relative in self.UI_FILES:
            with self.subTest(path=relative):
                source = self._read(relative)
                for token in self.DISK_TOKENS:
                    self.assertNotIn(token, source)

    def test_ui_never_instantiates_the_privileged_engine(self) -> None:
        for relative in (
            "src/greia_installer/main.py",
            "src/greia_installer/entrypoint.py",
            "src/greia_installer/transaction_client.py",
        ):
            with self.subTest(path=relative):
                # DemoInstallationEngine is the zero-disk-contact simulation;
                # anything else named *InstallationEngine is forbidden here.
                source = self._read(relative).replace("DemoInstallationEngine", "")
                self.assertNotIn("InstallationEngine", source)

    def test_client_opens_no_subprocess_or_device(self) -> None:
        source = self._read("src/greia_installer/transaction_client.py")
        self.assertNotIn("subprocess", source)
        self.assertNotIn("/dev/", source)
        self.assertNotIn("shell=True", source)


class SplitUnitContractTests(unittest.TestCase):
    """Unprivileged UI unit -> socket -> root service unit."""

    def _read(self, relative: str) -> str:
        return (PROJECT_ROOT / relative).read_text(encoding="utf-8")

    def test_ui_unit_is_unprivileged_and_aliased(self) -> None:
        unit = self._read(
            "build/installer-overlay/etc/systemd/system/greia-installer.service"
        )
        self.assertIn("User=nobody", unit)
        self.assertNotIn("User=root", unit)
        self.assertIn("Alias=greia-installer-ui.service", unit)
        self.assertIn("Wants=greia-install-transaction.socket", unit)
        self.assertIn("-m greia_installer.entrypoint", unit)
        self.assertIn("--transaction-socket /run/greia-os/install-transaction.sock", unit)
        self.assertIn("xinit", unit)
        self.assertIn(" vt1 ", unit)
        self.assertIn("TTYPath=/dev/tty1", unit)
        self.assertIn("StandardInput=null", unit)
        # The UI owns no release payload/support facts; those are service env.
        self.assertNotIn("GREIA_HARDWARE_SUPPORT_POOL", unit)
        self.assertNotIn("wipefs", unit)

    def test_socket_only_the_ui_identity_can_connect(self) -> None:
        unit = self._read(
            "build/installer-overlay/etc/systemd/system/greia-install-transaction.socket"
        )
        self.assertIn("ListenStream=/run/greia-os/install-transaction.sock", unit)
        self.assertIn("SocketMode=0600", unit)
        self.assertIn("SocketUser=nobody", unit)
        self.assertIn("Accept=no", unit)

    def test_transaction_service_is_root_and_owns_release_facts(self) -> None:
        unit = self._read(
            "build/installer-overlay/etc/systemd/system/greia-install-transaction.service"
        )
        self.assertIn("User=root", unit)
        self.assertIn("-m greia_installer.transaction_service", unit)
        self.assertIn(
            "Environment=GREIA_INSTALL_PAYLOAD_DIGEST=/etc/greia-os/expected-payload.sha256",
            unit,
        )
        self.assertIn(
            "Environment=GREIA_HARDWARE_SUPPORT_POOL=/opt/greia-hardware-support",
            unit,
        )
        self.assertIn(
            "Environment=GREIA_TARGET_IMAGE_PROFILE=/etc/greia-os/target-image-profile.json",
            unit,
        )
        self.assertIn("RestrictAddressFamilies=AF_UNIX", unit)
        self.assertIn("StandardInput=socket", unit)
        self.assertNotIn("WantedBy=", unit)

    def test_run_directory_is_declared_before_socket_bind(self) -> None:
        tmpfiles = self._read(
            "build/installer-overlay/etc/tmpfiles.d/greia-installer.conf"
        )
        self.assertIn("/run/greia-os", tmpfiles)


if __name__ == "__main__":
    unittest.main()
