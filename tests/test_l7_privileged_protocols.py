"""L7-PROTOCOLS: semantic privileged protocols (R0/R1 source scope).

Installer ``PREPARE_PLAN``/``EXECUTE`` plus the six semantic update
operations, over file-free fake authorities: protocol cannot carry raw
path/device/command/URL authority (negative tests), socket peer/schema
bounds hold, and the current single-root backend stays unavailable.
"""

from __future__ import annotations

import json
import unittest

from greia_installer.install_transaction import (
    ExecuteAuthorization,
    InstallTargetSummary,
    InstallTransactionCoordinator,
    InstallTransactionEndpoint,
    InstallTransactionError,
    PreparePlanRequest,
)
from greia_platform.privileged_channel import (
    MAX_MESSAGE_BYTES,
    PeerCredential,
    PrivilegedChannelError,
    authorize_peer,
    decode_response,
    encode_request,
    format_log_record,
    new_transaction_id,
    require_transaction_id,
)
from greia_platform.update_privileged import (
    CurrentCandidateSummary,
    UpdatePrivilegedEndpoint,
    UpdatePrivilegedError,
    build_request,
    read_response,
)
from greia_platform.system_updates import (
    UnavailableSystemUpdateBackend,
    UpdateBackendUnavailable,
)


ROOT_PEER = PeerCredential(uid=0)
PARENT_PEER = PeerCredential(uid=1000)
READY = "installer_ready"
UPDATE_READY = "update_ready"


def _digest(seed: str) -> str:
    import hashlib

    return hashlib.sha256(seed.encode()).hexdigest()


class FakeInstallAuthority:
    def __init__(
        self,
        targets: list[InstallTargetSummary],
        *,
        profile_id: str = "greia-test-profile",
        token: str = "inventory-token-1",
    ) -> None:
        self._targets = list(targets)
        self._profile_id = profile_id
        self._token = token

    def list_targets(self) -> tuple[InstallTargetSummary, ...]:
        return tuple(self._targets)

    def inventory_token(self) -> str:
        return self._token

    def compatible_profile_id(self) -> str:
        return self._profile_id


def _eligible_target(seed: str = "disk-a") -> InstallTargetSummary:
    return InstallTargetSummary(
        identity_digest=_digest(seed),
        eligible=True,
        policy_id="pc-internal",
        display_summary="Test disk 8 GB",
    )


def _make_installer(
    targets: list[InstallTargetSummary] | None = None,
    **kwargs: object,
) -> tuple[InstallTransactionEndpoint, FakeInstallAuthority]:
    authority = FakeInstallAuthority(
        targets if targets is not None else [_eligible_target()], **kwargs  # type: ignore[arg-type]
    )
    coordinator = InstallTransactionCoordinator(authority=authority)
    return InstallTransactionEndpoint(coordinator), authority


def _prepare_params(
    target: InstallTargetSummary, profile: str = "greia-test-profile"
) -> dict[str, object]:
    return {
        "expected_target_identity": target.identity_digest,
        "compatible_profile_id": profile,
        "settings_snapshot": {"locale": "en"},
    }


class InstallerPrepareExecuteTests(unittest.TestCase):
    def test_prepare_returns_nonce_plan_and_matching_digest(self) -> None:
        endpoint, _ = _make_installer()
        target = _eligible_target()
        raw = encode_request("PREPARE_PLAN", _prepare_params(target))
        response = endpoint.handle_request(raw, peer=ROOT_PEER, boot_state=READY)
        transaction_id, op, payload = decode_response(response)
        require_transaction_id(transaction_id)
        self.assertEqual(op, "PREPARE_PLAN")
        self.assertEqual(payload["status"], "PREPARED")
        self.assertRegex(str(payload["transaction_nonce"]), r"^[0-9a-f]{32}$")
        self.assertRegex(str(payload["plan_digest"]), r"^[0-9a-f]{64}$")
        plan = payload["plan"]
        assert isinstance(plan, dict)
        self.assertEqual(plan["target_identity_digest"], target.identity_digest)
        self.assertIn("verify-target", plan["steps"])

    def test_execute_authorizes_then_retires_nonce(self) -> None:
        endpoint, _ = _make_installer()
        target = _eligible_target()
        _, _, prepared = decode_response(
            endpoint.handle_request(
                encode_request("PREPARE_PLAN", _prepare_params(target)),
                peer=ROOT_PEER,
                boot_state=READY,
            )
        )
        execute_raw = encode_request(
            "EXECUTE",
            {
                "transaction_nonce": prepared["transaction_nonce"],
                "plan_digest": prepared["plan_digest"],
            },
        )
        _, op, payload = decode_response(
            endpoint.handle_request(execute_raw, peer=ROOT_PEER, boot_state=READY)
        )
        self.assertEqual(op, "EXECUTE")
        self.assertEqual(payload["status"], "AUTHORIZED")
        self.assertFalse(payload["destructive_enabled"])
        self.assertEqual(payload["target_identity"], target.identity_digest)
        with self.assertRaises(InstallTransactionError):
            endpoint.handle_request(execute_raw, peer=ROOT_PEER, boot_state=READY)

    def test_execute_rejects_wrong_digest(self) -> None:
        endpoint, _ = _make_installer()
        target = _eligible_target()
        _, _, prepared = decode_response(
            endpoint.handle_request(
                encode_request("PREPARE_PLAN", _prepare_params(target)),
                peer=ROOT_PEER,
                boot_state=READY,
            )
        )
        with self.assertRaises(InstallTransactionError):
            endpoint.handle_request(
                encode_request(
                    "EXECUTE",
                    {
                        "transaction_nonce": prepared["transaction_nonce"],
                        "plan_digest": _digest("other-plan"),
                    },
                ),
                peer=ROOT_PEER,
                boot_state=READY,
            )

    def test_execute_rejects_unknown_nonce(self) -> None:
        endpoint, _ = _make_installer()
        with self.assertRaises(InstallTransactionError):
            endpoint.handle_request(
                encode_request(
                    "EXECUTE",
                    {"transaction_nonce": "0" * 32, "plan_digest": "0" * 64},
                ),
                peer=ROOT_PEER,
                boot_state=READY,
            )

    def test_inventory_refresh_invalidates_plan(self) -> None:
        endpoint, authority = _make_installer()
        target = _eligible_target()
        _, _, prepared = decode_response(
            endpoint.handle_request(
                encode_request("PREPARE_PLAN", _prepare_params(target)),
                peer=ROOT_PEER,
                boot_state=READY,
            )
        )
        authority._token = "inventory-token-2"
        with self.assertRaisesRegex(InstallTransactionError, "invalidated"):
            endpoint.handle_request(
                encode_request(
                    "EXECUTE",
                    {
                        "transaction_nonce": prepared["transaction_nonce"],
                        "plan_digest": prepared["plan_digest"],
                    },
                ),
                peer=ROOT_PEER,
                boot_state=READY,
            )

    def test_target_disappearance_invalidates_plan(self) -> None:
        endpoint, authority = _make_installer()
        target = _eligible_target()
        _, _, prepared = decode_response(
            endpoint.handle_request(
                encode_request("PREPARE_PLAN", _prepare_params(target)),
                peer=ROOT_PEER,
                boot_state=READY,
            )
        )
        authority._targets = []
        with self.assertRaisesRegex(InstallTransactionError, "disappeared"):
            endpoint.handle_request(
                encode_request(
                    "EXECUTE",
                    {
                        "transaction_nonce": prepared["transaction_nonce"],
                        "plan_digest": prepared["plan_digest"],
                    },
                ),
                peer=ROOT_PEER,
                boot_state=READY,
            )

    def test_target_ineligibility_change_invalidates_plan(self) -> None:
        target = _eligible_target()
        endpoint, authority = _make_installer([target])
        _, _, prepared = decode_response(
            endpoint.handle_request(
                encode_request("PREPARE_PLAN", _prepare_params(target)),
                peer=ROOT_PEER,
                boot_state=READY,
            )
        )
        authority._targets = [
            InstallTargetSummary(
                identity_digest=target.identity_digest,
                eligible=False,
                policy_id="pc-internal",
                display_summary="Test disk 8 GB",
            )
        ]
        with self.assertRaisesRegex(InstallTransactionError, "eligible"):
            endpoint.handle_request(
                encode_request(
                    "EXECUTE",
                    {
                        "transaction_nonce": prepared["transaction_nonce"],
                        "plan_digest": prepared["plan_digest"],
                    },
                ),
                peer=ROOT_PEER,
                boot_state=READY,
            )

    def test_unknown_target_fails_closed_at_prepare(self) -> None:
        endpoint, _ = _make_installer()
        with self.assertRaisesRegex(InstallTransactionError, "unknown"):
            endpoint.handle_request(
                encode_request(
                    "PREPARE_PLAN", _prepare_params(_eligible_target("disk-b"))
                ),
                peer=ROOT_PEER,
                boot_state=READY,
            )

    def test_profile_mismatch_fails_closed(self) -> None:
        endpoint, _ = _make_installer()
        target = _eligible_target()
        with self.assertRaisesRegex(InstallTransactionError, "profile"):
            endpoint.handle_request(
                encode_request(
                    "PREPARE_PLAN", _prepare_params(target, profile="other-profile")
                ),
                peer=ROOT_PEER,
                boot_state=READY,
            )


class InstallerRawAuthorityNegativeTests(unittest.TestCase):
    """Requests can never smuggle raw path/device/command/URL authority."""

    def endpoint(self) -> InstallTransactionEndpoint:
        endpoint, _ = _make_installer()
        return endpoint

    def test_raw_path_field_rejected(self) -> None:
        with self.assertRaises((InstallTransactionError, PrivilegedChannelError)):
            encode_request("PREPARE_PLAN", {"path": "/dev/sda"})

    def test_raw_command_fields_rejected(self) -> None:
        for key in ("command", "argv", "shell", "script"):
            with self.subTest(key=key):
                with self.assertRaises((InstallTransactionError, PrivilegedChannelError)):
                    encode_request("PREPARE_PLAN", {key: "wipefs --all"})

    def test_raw_url_value_rejected(self) -> None:
        with self.assertRaises((InstallTransactionError, PrivilegedChannelError)):
            encode_request(
                "PREPARE_PLAN", {"note": "see https://example.invalid/x"}
            )

    def test_mountpoint_partition_bootargs_rejected(self) -> None:
        for params in (
            {"mountpoint": "/mnt/target"},
            {"partition_number": 1},
            {"boot_args": "quiet splash"},
            {"device": "sda"},
            {"url": "https://example.invalid/payload"},
        ):
            with self.subTest(params=params):
                with self.assertRaises((InstallTransactionError, PrivilegedChannelError)):
                    encode_request("PREPARE_PLAN", params)

    def test_absolute_path_string_value_rejected(self) -> None:
        with self.assertRaises((InstallTransactionError, PrivilegedChannelError)):
            encode_request("PREPARE_PLAN", {"note": "/etc/shadow"})

    def test_unknown_prepare_fields_rejected(self) -> None:
        endpoint = self.endpoint()
        target = _eligible_target()
        params = _prepare_params(target)
        params["extra_selector"] = "sda"
        with self.assertRaises(InstallTransactionError):
            endpoint.handle_request(
                encode_request("PREPARE_PLAN", params),
                peer=ROOT_PEER,
                boot_state=READY,
            )

    def test_execute_unknown_fields_rejected(self) -> None:
        endpoint = self.endpoint()
        raw = json.dumps(
            {
                "protocol_version": 1,
                "op": "EXECUTE",
                "params": {
                    "transaction_nonce": "0" * 32,
                    "plan_digest": "0" * 64,
                    "extra_selector": "sda",
                },
            }
        ).encode()
        with self.assertRaises(InstallTransactionError):
            endpoint.handle_request(raw, peer=ROOT_PEER, boot_state=READY)

    def test_unknown_op_rejected(self) -> None:
        endpoint = self.endpoint()
        with self.assertRaises(InstallTransactionError):
            endpoint.handle_request(
                encode_request("FORMAT_DISK", {}),
                peer=ROOT_PEER,
                boot_state=READY,
            )


class PrivilegedPeerSchemaBoundTests(unittest.TestCase):
    def test_unauthorized_peer_refused_installer(self) -> None:
        endpoint, _ = _make_installer()
        target = _eligible_target()
        with self.assertRaises(InstallTransactionError):
            endpoint.handle_request(
                encode_request("PREPARE_PLAN", _prepare_params(target)),
                peer=PARENT_PEER,
                boot_state=READY,
            )

    def test_pre_intro_boot_refused(self) -> None:
        endpoint, _ = _make_installer()
        target = _eligible_target()
        for state in ("pre_intro", "", "unknown", "interactive"):
            with self.subTest(state=state):
                with self.assertRaisesRegex(InstallTransactionError, "pre-intro"):
                    endpoint.handle_request(
                        encode_request("PREPARE_PLAN", _prepare_params(target)),
                        peer=ROOT_PEER,
                        boot_state=state,
                    )

    def test_authorize_peer_requires_allowlist_membership(self) -> None:
        with self.assertRaises(PrivilegedChannelError):
            authorize_peer(PARENT_PEER, (0,))
        self.assertIs(authorize_peer(ROOT_PEER, (0, 1000)), ROOT_PEER)

    def test_oversize_frame_rejected(self) -> None:
        endpoint, _ = _make_installer()
        with self.assertRaises(InstallTransactionError):
            endpoint.handle_request(b"x" * (MAX_MESSAGE_BYTES + 1), peer=ROOT_PEER, boot_state=READY)

    def test_wrong_protocol_version_rejected(self) -> None:
        endpoint, _ = _make_installer()
        raw = json.dumps(
            {"protocol_version": 999, "op": "PREPARE_PLAN", "params": {}}
        ).encode()
        with self.assertRaises(InstallTransactionError):
            endpoint.handle_request(raw, peer=ROOT_PEER, boot_state=READY)

    def test_non_json_frame_rejected(self) -> None:
        endpoint, _ = _make_installer()
        with self.assertRaises(InstallTransactionError):
            endpoint.handle_request(b"not json", peer=ROOT_PEER, boot_state=READY)

    def test_transaction_ids_unique_bounded_and_secret_free_in_logs(self) -> None:
        seen = {new_transaction_id() for _ in range(16)}
        self.assertEqual(len(seen), 16)
        for transaction_id in seen:
            require_transaction_id(transaction_id)
        endpoint, _ = _make_installer()
        target = _eligible_target()
        _, _, prepared = decode_response(
            endpoint.handle_request(
                encode_request("PREPARE_PLAN", _prepare_params(target)),
                peer=ROOT_PEER,
                boot_state=READY,
            )
        )
        record = format_log_record(new_transaction_id(), "PREPARE_PLAN", "PREPARED")
        self.assertNotIn(str(prepared["transaction_nonce"]), record)
        self.assertNotIn(str(prepared["plan_digest"]), record)
        self.assertNotIn(target.identity_digest, record)


class FakeUpdateAuthority:
    """Semantic-only fake: resolves candidate/layout/slot/backend internally."""

    def __init__(self, *, single_root: bool = False, present: bool = True) -> None:
        self.single_root = single_root
        self.present = present
        self.calls: list[str] = []

    def candidate_summary(self) -> CurrentCandidateSummary:
        if not self.present:
            return CurrentCandidateSummary(present=False)
        return CurrentCandidateSummary(
            present=True,
            release_id="greia-2026-01",
            bundle_sha256=_digest("bundle"),
        )

    def layout_summary(self) -> dict[str, object]:
        return {"single_root": self.single_root, "slots": ["A"] if self.single_root else ["A", "B"]}

    def verify_current_candidate(self) -> CurrentCandidateSummary:
        self.calls.append("verify")
        if not self.present:
            raise UpdatePrivilegedError("no current update candidate in the inbox")
        return self.candidate_summary()

    def stage_current_candidate(self) -> dict[str, object]:
        self.calls.append("stage")
        if self.single_root:
            raise UpdateBackendUnavailable("A/B system-slot backend is not configured")
        if not self.present:
            raise UpdatePrivilegedError("no current update candidate in the inbox")
        return {"staged": True}

    def arm_current_candidate(self) -> dict[str, object]:
        self.calls.append("arm")
        if self.single_root:
            raise UpdateBackendUnavailable("A/B system-slot backend is not configured")
        if not self.present:
            raise UpdatePrivilegedError("no current update candidate in the inbox")
        return {"armed": True}

    def confirm_boot_health(self) -> dict[str, object]:
        self.calls.append("confirm")
        return {"confirmed": True}

    def reconcile(self) -> dict[str, object]:
        self.calls.append("reconcile")
        return {"reconciled": True}


class UpdateSemanticProtocolTests(unittest.TestCase):
    def endpoint(self, **kwargs: object) -> UpdatePrivilegedEndpoint:
        return UpdatePrivilegedEndpoint(FakeUpdateAuthority(**kwargs))  # type: ignore[arg-type]

    def test_all_six_ops_dispatch(self) -> None:
        endpoint = self.endpoint()
        expected = {
            "STATUS": "OK",
            "VERIFY_CURRENT_CANDIDATE": "VERIFIED",
            "STAGE_CURRENT_CANDIDATE": "STAGED",
            "ARM_CURRENT_CANDIDATE": "ARMED",
            "CONFIRM_BOOT_HEALTH": "CONFIRMED",
            "RECONCILE": "RECONCILED",
        }
        for op, status in expected.items():
            with self.subTest(op=op):
                _, returned_op, payload = read_response(
                    endpoint.handle_request(
                        build_request(op), peer=ROOT_PEER, boot_state=UPDATE_READY
                    )
                )
                self.assertEqual(returned_op, op)
                self.assertEqual(payload["status"], status)

    def test_requests_take_no_selectors(self) -> None:
        endpoint = self.endpoint()
        with self.assertRaises(UpdatePrivilegedError):
            endpoint.handle_request(
                encode_request("STAGE_CURRENT_CANDIDATE", {"candidate": "x"}),
                peer=ROOT_PEER,
                boot_state=UPDATE_READY,
            )

    def test_raw_authority_rejected_on_update_ops(self) -> None:
        with self.assertRaises(PrivilegedChannelError):
            encode_request("STAGE_CURRENT_CANDIDATE", {"device": "sda"})
        with self.assertRaises(PrivilegedChannelError):
            encode_request("ARM_CURRENT_CANDIDATE", {"path": "/dev/mmcblk0"})

    def test_unknown_update_op_rejected(self) -> None:
        endpoint = self.endpoint()
        with self.assertRaises(UpdatePrivilegedError):
            endpoint.handle_request(
                encode_request("INSTALL_BACKDOOR", {}),
                peer=ROOT_PEER,
                boot_state=UPDATE_READY,
            )

    def test_single_root_stage_and_arm_stay_unavailable(self) -> None:
        endpoint = self.endpoint(single_root=True)
        for op in ("STAGE_CURRENT_CANDIDATE", "ARM_CURRENT_CANDIDATE"):
            with self.subTest(op=op):
                with self.assertRaises(UpdatePrivilegedError):
                    endpoint.handle_request(
                        build_request(op), peer=ROOT_PEER, boot_state=UPDATE_READY
                    )

    def test_missing_candidate_fails_closed(self) -> None:
        endpoint = self.endpoint(present=False)
        _, _, payload = read_response(
            endpoint.handle_request(
                build_request("STATUS"), peer=ROOT_PEER, boot_state=UPDATE_READY
            )
        )
        self.assertFalse(payload["candidate"]["present"])
        with self.assertRaises(UpdatePrivilegedError):
            endpoint.handle_request(
                build_request("VERIFY_CURRENT_CANDIDATE"),
                peer=ROOT_PEER,
                boot_state=UPDATE_READY,
            )

    def test_update_peer_and_pre_intro_bounds(self) -> None:
        endpoint = self.endpoint()
        with self.assertRaises(UpdatePrivilegedError):
            endpoint.handle_request(
                build_request("STATUS"), peer=PARENT_PEER, boot_state=UPDATE_READY
            )
        with self.assertRaisesRegex(UpdatePrivilegedError, "pre-intro"):
            endpoint.handle_request(
                build_request("STATUS"), peer=ROOT_PEER, boot_state="pre_intro"
            )

    def test_current_single_root_backend_stays_unavailable(self) -> None:
        backend = UnavailableSystemUpdateBackend()
        self.assertFalse(backend.available)
        with self.assertRaises(UpdateBackendUnavailable):
            from pathlib import Path

            from greia_platform.system_updates import inspect_update_bundle  # noqa: F401
            backend.stage(object())  # type: ignore[arg-type]


class PreparePlanRequestUnitTests(unittest.TestCase):
    def test_request_rejects_non_identifier_profile(self) -> None:
        target = _eligible_target()
        with self.assertRaises(InstallTransactionError):
            PreparePlanRequest(
                expected_target_identity=target.identity_digest,
                compatible_profile_id="/etc/passwd",
                settings_snapshot={},
            )

    def test_authorization_never_enables_destruction(self) -> None:
        authorization = ExecuteAuthorization(
            transaction_nonce="0" * 32,
            plan_digest="0" * 64,
            target_identity="0" * 64,
            compatible_profile_id="greia-test-profile",
        )
        self.assertFalse(authorization.destructive_enabled)
        with self.assertRaises(InstallTransactionError):
            ExecuteAuthorization(
                transaction_nonce="0" * 32,
                plan_digest="0" * 64,
                target_identity="0" * 64,
                compatible_profile_id="greia-test-profile",
                destructive_enabled=True,
            )


if __name__ == "__main__":
    unittest.main()
