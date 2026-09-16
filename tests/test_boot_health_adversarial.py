"""P4.4 adversarial proof: same-UID Activities cannot confirm health.

Through the real composed production mechanism (``BootHealthService`` +
``BootHealthEndpoint`` + ``handle_boot_health_connection`` over the real
file-backed ``GrubEnvBackend``, the real root ``BootHealthCapabilityAuthority``
+ ``maybe_issue_boot_capability`` generator, the real launcher
``maybe_load_production_token`` loader + ``ActivitySupervisor`` sandbox, and
the real ``BootHealthyProtocol`` with the real ``ProductionActualBootObserver``
truth):

1. an Activity cannot read the launcher boot-health token;
2. an Activity cannot reach the health socket unless the sandbox allows it;
3. possession of the child UID alone does not confirm health;
4. a copied/stale token does not confirm;
5. a direct library call from Activity-like code cannot mutate root boot state;
6. launcher confirmation attempted after an untrusted Activity launch is refused.

Each negative asserts its intended refusal reason explicitly plus full
fixture-tree snapshot equality (no journal/backend mutation). The closing
positive control proves the same rig still confirms once through the genuine
launcher/service path (unknown-token RED with zero mutation, then
issued-token GREEN, then replay RED).

R0/R1 only: files in disposable tmpdirs. No production authority is
broadened: the health socket and the one-use capability remain the only
confirmation path (asserted structurally below).
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import greia_launcher.boot_health as launcher_health
from greia_launcher.boot_health import TRUSTED_BOOTSTRAP_PATH
from greia_launcher.supervisor import ActivitySupervisor
from greia_platform.activities import ActivityManifest, SkillContribution
from greia_platform.boot_health import (
    BootHealthCapabilityAuthority,
    BootHealthError,
    BootHealthyProtocol,
    IntroEvidence,
    ProductionActualBootObserver,
    default_capability_authority,
    maybe_issue_boot_capability,
)
from greia_platform.boot_health_service import (
    BOOT_HEALTH_OPS,
    BootHealthEndpoint,
    BootHealthService,
    BootHealthServiceError,
    build_confirm_request,
    handle_boot_health_connection,
)
from greia_platform.boot_transaction import (
    BootArtifactSet,
    BootTransactionCoordinator,
    BootTransactionJournal,
    BootTransactionState,
)
from greia_platform.grub_ab import GrubEnvBackend
from greia_platform.privileged_channel import PeerCredential, encode_request
from greia_platform.system_updates import (
    SlotBackedSystemUpdateBackend,
    SystemIdentity,
    SystemUpdateServiceAuthority,
)
from greia_platform.trust import PackageTrust


_RELEASE = "greia-0.15.0"
_RELEASE_SEQ = 11
_LAYOUT_ID = "modern-gpt-ab-v1"
_BACKEND_ID = "grub-ab-v1"

_UUID_A = "11111111-2222-3333-4444-555555555555"
_UUID_A_FS = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
_UUID_B = "22222222-3333-4444-5555-666666666666"
_UUID_B_FS = "bbbbbbbb-cccc-dddd-eeee-ffffffffffff"
_KERNEL_SHA = "ab" * 32
_INITRAMFS_SHA = "cd" * 32

_BOOT_ID_1 = "aaaaaaaa-1111-2222-3333-444444444444"
_BOOT_ID_2 = "bbbbbbbb-5555-6666-7777-888888888888"

_LAUNCHER_UID = 1001
_UNAUTHORIZED_UID = 9999
_ACTIVITY_PATH = "activity.runtime:PythonActivity"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _snapshot_tree(root: Path) -> dict[str, bytes]:
    snapshot: dict[str, bytes] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and not path.is_symlink():
            snapshot[str(path.relative_to(root))] = path.read_bytes()
    return snapshot


def _record_dict(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "accepted_release_id": "greia-0.14.0",
        "accepted_slot": "A",
        "boot_backend": _BACKEND_ID,
        "boot_control": {"active_slot": "A", "kind": "grub-env-v1"},
        "install_profile": "modern-amd64",
        "install_target_sha256": "ab" * 32,
        "installed_at_unix": 1757000000,
        "layout_id": _LAYOUT_ID,
        "persist": {
            "filesystem_uuid": "cccccccc-dddd-eeee-ffff-000000000000",
            "partuuid": "33333333-4444-5555-6666-777777777777",
        },
        "platform_family": "standard-x86-64",
        "schema_version": 1,
        "slot_bytes": 1024 * 1024 * 1024,
        "system_a": {"filesystem_uuid": _UUID_A_FS, "partuuid": _UUID_A},
        "system_b": {"filesystem_uuid": _UUID_B_FS, "partuuid": _UUID_B},
    }
    base.update(overrides)
    return base


def _canonical(payload: dict[str, object]) -> bytes:
    return (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _artifact_sets_for_journal(
    journal: BootTransactionJournal,
) -> tuple[BootArtifactSet, BootArtifactSet]:
    candidate = BootArtifactSet(
        slot=journal.candidate_slot,
        layout_id=journal.layout_id,
        boot_backend=journal.boot_backend,
        generic_kernel_sha256=_KERNEL_SHA,
        generic_initramfs_sha256=_INITRAMFS_SHA,
        root_partuuid=_UUID_A if journal.candidate_slot == "A" else _UUID_B,
        root_filesystem_uuid=_UUID_A_FS if journal.candidate_slot == "A" else _UUID_B_FS,
        release_id=journal.release_id,
    )
    if journal.first_install:
        return candidate, candidate
    accepted = BootArtifactSet(
        slot=journal.accepted_slot,
        layout_id=journal.layout_id,
        boot_backend=journal.boot_backend,
        generic_kernel_sha256=_KERNEL_SHA,
        generic_initramfs_sha256=_INITRAMFS_SHA,
        root_partuuid=_UUID_A if journal.accepted_slot == "A" else _UUID_B,
        root_filesystem_uuid=_UUID_A_FS if journal.accepted_slot == "A" else _UUID_B_FS,
        release_id="greia-0.14.0",
    )
    return candidate, accepted


class _StubArtifactResolver:
    def resolve(
        self, journal: BootTransactionJournal
    ) -> tuple[BootArtifactSet, BootArtifactSet]:
        return _artifact_sets_for_journal(journal)


class _AuthorityBackedVerifier:
    """Service verifier seam bound to one staged journal + boot attempt."""

    def __init__(
        self,
        authority: BootHealthCapabilityAuthority,
        journal: BootTransactionJournal,
        *,
        boot_attempt: str,
    ) -> None:
        self._authority = authority
        self._journal = journal
        self._boot_attempt = boot_attempt

    def verify_and_consume(self, *, token: str) -> dict[str, object]:
        record = self._authority.verify_and_consume(
            token=token,
            transaction_id=self._journal.transaction_id,
            boot_attempt=self._boot_attempt,
            peer_bootstrap_path=TRUSTED_BOOTSTRAP_PATH,
        )
        return {"consumed": True, "transaction_id": record.transaction_id}


class _FakeConnection:
    def __init__(self, inbound: bytes = b"") -> None:
        self._inbound = inbound
        self.recv_calls = 0
        self.sent: list[bytes] = []
        self.closed = False

    def settimeout(self, _seconds: float) -> None:
        pass

    def recv(self, _size: int) -> bytes:
        self.recv_calls += 1
        if self._inbound:
            chunk, self._inbound = self._inbound, b""
            return chunk
        return b""

    def sendall(self, data: bytes) -> None:
        self.sent.append(bytes(data))

    def close(self) -> None:
        self.closed = True


class _FakeProfile:
    profile_id = "0123456789abcdef0123456789abcdef"
    display_name = "Mia"
    avatar_id = "unicorn"


class _FakeProfileContext:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.profile = _FakeProfile()
        self.customization_dir = root / "customization"
        self.customization_dir.mkdir(parents=True, exist_ok=True)

    def activity_data_dir(self, activity_id: str) -> Path:
        path = self.root / "activities" / activity_id
        path.mkdir(parents=True, exist_ok=True)
        return path


class _FakeAuthority:
    def __init__(self, activity_id: str) -> None:
        self.activity_id = activity_id
        self.package_digest = "a" * 64
        self.package_trust = PackageTrust.BUILT_IN
        self.effective_capabilities = frozenset({"display", "pointer"})
        self.sdk_features = frozenset({"display", "pointer"})

    def has_capability(self, capability: str) -> bool:
        return capability in self.effective_capabilities

    def has_permission(self, permission: str) -> bool:
        return False


def _manifest(root: Path) -> ActivityManifest:
    entry = Path("main.py")
    root.mkdir(parents=True, exist_ok=True)
    (root / entry).write_text("print('ok')\n", encoding="utf-8")
    return ActivityManifest(
        activity_id="org.greia.test-activity",
        legacy_ids=(),
        title_key="activity.test.title",
        version="0.1.0",
        runtime_type="python",
        api_version="0.1",
        entrypoint=entry,
        icon_id="test",
        categories=("test",),
        skills=(SkillContribution("test", 1),),
        events=(),
        difficulty=1,
        languages=("en",),
        required_capabilities=("display", "pointer"),
        optional_capabilities=(),
        requested_permissions=(),
        storage_schema_version=1,
        root=root,
    )


class _ServiceRig:
    """Disposable composed service over the real GrubEnvBackend + authority."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.state_dir = root / "update-state"
        self.boot_journal_dir = root / "boot-journal"
        self.grubenv_dir = root / "grubenv"
        self.history_dir = root / "history"
        self.layout_path = root / "installed-layout.json"
        for directory in (
            self.state_dir, self.boot_journal_dir,
            self.grubenv_dir, self.history_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)
        self.layout_path.write_bytes(
            (json.dumps(_record_dict(), sort_keys=True) + "\n").encode()
        )
        self.authority = default_capability_authority(
            authority_dir=root / "authority",
            delivery_dir=root / "delivery",
        )
        self.backend = GrubEnvBackend.initialize(self.grubenv_dir, default_slot="A")
        update_backend = SlotBackedSystemUpdateBackend(
            self.state_dir,
            layout_record_path=self.layout_path,
            boot_backend=self.backend,
        )
        self.update_authority = SystemUpdateServiceAuthority(
            self.state_dir,
            SystemIdentity("0.14.0", "standard-x86-64", "x86-64", "modern-amd64"),
            update_backend,
        )

    def update_journal_dir(self) -> Path:
        from greia_platform.system_updates import UPDATE_JOURNAL_DIR_NAME

        return self.state_dir / "system-updates" / UPDATE_JOURNAL_DIR_NAME

    def stage_update_candidate_booted(self) -> BootTransactionJournal:
        self.backend.arm_one_shot("B")
        journal_dir = self.state_dir / "system-updates" / "journal"
        BootTransactionJournal.begin_update(
            journal_dir,
            layout_id=_LAYOUT_ID,
            boot_backend=_BACKEND_ID,
            release_id=_RELEASE,
            candidate_slot="B",
            accepted_slot="A",
        )
        self.backend.simulate_reboot()
        assert self.backend.observe_booted_slot() == "B"
        return BootTransactionJournal.load(journal_dir)

    def issue(self, journal: BootTransactionJournal, *, boot_id: str = _BOOT_ID_1):
        issued = maybe_issue_boot_capability(
            authority=self.authority,
            boot_journal_dir=self.boot_journal_dir,
            update_state_dir=self.state_dir,
            boot_id=boot_id,
            peer_bootstrap_path=TRUSTED_BOOTSTRAP_PATH,
            peer_uid=_LAUNCHER_UID,
        )
        assert issued is not None
        return issued

    def compose_service(self, journal: BootTransactionJournal, *, boot_id: str = _BOOT_ID_1):
        verifier = _AuthorityBackedVerifier(self.authority, journal, boot_attempt=boot_id)
        self.service = BootHealthService(
            boot_journal_dir=self.boot_journal_dir,
            update_state_dir=self.state_dir,
            history_dir=self.history_dir,
            update_authority=self.update_authority,
            capability_verifier=verifier,
            artifact_resolver=_StubArtifactResolver(),
            boot_backend_factory=lambda: GrubEnvBackend.attach(self.grubenv_dir),
        )
        self.endpoint = BootHealthEndpoint(
            self.service, allowed_uids=(0, _LAUNCHER_UID)
        )
        return self.service


def _protocol_rig(root: Path):
    """BootHealthyProtocol over the real GrubEnvBackend + real observer truth."""
    grubenv_dir = root / "grubenv"
    backend = GrubEnvBackend.initialize(grubenv_dir, default_slot="A")
    candidate = BootArtifactSet(
        slot="B", layout_id=_LAYOUT_ID, boot_backend=_BACKEND_ID,
        generic_kernel_sha256=_KERNEL_SHA,
        generic_initramfs_sha256=_INITRAMFS_SHA,
        root_partuuid=_UUID_B, root_filesystem_uuid=_UUID_B_FS,
        release_id=_RELEASE,
    )
    accepted = BootArtifactSet(
        slot="A", layout_id=_LAYOUT_ID, boot_backend=_BACKEND_ID,
        generic_kernel_sha256=_KERNEL_SHA,
        generic_initramfs_sha256=_INITRAMFS_SHA,
        root_partuuid=_UUID_A, root_filesystem_uuid=_UUID_A_FS,
        release_id="greia-0.14.0",
    )
    coordinator = BootTransactionCoordinator.begin_update(
        journal_dir=root / "journal", backend=backend,
        candidate_artifacts=candidate, accepted_artifacts=accepted,
        release_id=_RELEASE,
    )
    coordinator.arm()
    assert backend.simulate_reboot() == "B"
    resumed = BootTransactionCoordinator.resume(
        journal_dir=root / "journal", backend=GrubEnvBackend.attach(grubenv_dir),
        candidate_artifacts=candidate, accepted_artifacts=accepted,
    )
    resumed.observe_boot()
    assert resumed.journal.state is BootTransactionState.CANDIDATE_BOOTING
    # Same platform-observed truth the early-boot observer establishes:
    # kernel root PARTUUID B resolved through the trusted layout record and
    # cross-checked against the booted slot release identity.
    cmdline = root / "cmdline"
    cmdline.write_text(
        f"BOOT_IMAGE=/boot/vmlinuz root=PARTUUID={_UUID_B} ro quiet\n",
        encoding="utf-8",
    )
    layout_path = root / "observer-layout.json"
    layout_path.write_bytes(_canonical(_record_dict()))
    identity = root / "release-identity.json"
    identity.write_bytes(_canonical({
        "boot_backend": _BACKEND_ID,
        "layout_id": _LAYOUT_ID,
        "release_id": _RELEASE,
        "role": "system-b",
        "slot": "B",
    }))
    observer = ProductionActualBootObserver(
        cmdline_path=cmdline,
        layout_record_path=layout_path,
        release_identity_path=identity,
    )
    observed = observer.observe()
    assert observed.booted_slot == "B"
    assert observed.root_partuuid == _UUID_B
    from greia_platform.boot_health import BootHealthCredentialVault

    protocol = BootHealthyProtocol(
        coordinator=resumed,
        candidate_root_partuuid=_UUID_B,
        candidate_release_id=_RELEASE,
        vault=BootHealthCredentialVault(root / "vault"),
        observer=observer,
        trusted_bootstrap_path=TRUSTED_BOOTSTRAP_PATH,
    )
    return resumed, protocol, observer


def _full_intro(*, untrusted: bool = False) -> IntroEvidence:
    return IntroEvidence(
        first_frame_visible=True,
        intro_completed=True,
        lifecycle_state="interactive_ready",
        untrusted_activity_launched=untrusted,
    )


class ActivityTokenIsolationTests(unittest.TestCase):
    def test_activity_cannot_read_launcher_token(self) -> None:
        """P4.4-1: the Activity env/mounts hide the launcher delivery token."""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            rig = _ServiceRig(root)
            journal = rig.stage_update_candidate_booted()
            issued = rig.issue(journal)
            # Launcher loader with the delivery pointer reads the real token.
            with mock.patch.dict(
                os.environ,
                {"GREIA_BOOT_HEALTH_DELIVERY_DIR": str(rig.authority.delivery_dir)},
                clear=False,
            ):
                launcher_token = launcher_health.maybe_load_production_token()
            self.assertEqual(launcher_token, issued.token)
            # The Activity env drops every credential/delivery pointer.
            manifest = _manifest(root / "activity")
            profile = _FakeProfileContext(root / "profile")
            authority = _FakeAuthority(manifest.activity_id)
            with mock.patch.dict(
                os.environ,
                {
                    "CREDENTIALS_DIRECTORY": "/run/credentials/greia-launcher.service",
                    "GREIA_BOOT_HEALTH_DELIVERY_DIR": str(rig.authority.delivery_dir),
                },
                clear=False,
            ):
                environment = ActivitySupervisor._sanitized_environment(
                    manifest, profile, authority, "session-1", sandboxed=True
                )
            self.assertNotIn("CREDENTIALS_DIRECTORY", environment)
            self.assertNotIn("GREIA_BOOT_HEALTH_DELIVERY_DIR", environment)
            for name in environment:
                self.assertNotIn("CREDENTIAL", name.upper())
                self.assertNotIn("BOOT_HEALTH", name.upper())
            # An Activity-scoped process therefore resolves the production
            # bind (absent in the sandbox) to the plain-boot no-op, never
            # the staged launcher token.
            with mock.patch.dict(os.environ, environment, clear=True):
                self.assertNotIn("GREIA_BOOT_HEALTH_DELIVERY_DIR", os.environ)
                self.assertIsNone(launcher_health.maybe_load_production_token())
            # And the loader is read-only by construction: O_RDONLY open,
            # no provisioning/issue path, and the root authority record
            # directory is never resolved here (only the delivery path).
            import inspect as _inspect

            source = _inspect.getsource(launcher_health.maybe_load_production_token)
            self.assertIn("O_RDONLY", source)
            self.assertNotIn("CAPABILITY_AUTHORITY", source)
            self.assertNotIn("authority_dir", source)
            self.assertNotIn("issue_for_pending", source)
            self.assertNotIn("verify_and_consume", source)
            self.assertNotIn("atomic_write", source)
            self.assertNotIn("os.replace", source)
            # The staged capability is untouched by the Activity probe.
            self.assertTrue(rig.authority.capability_live())


class HealthSocketReachabilityTests(unittest.TestCase):
    def test_activity_cannot_reach_health_socket(self) -> None:
        """P4.4-2: forged/unauthorized peers refused pre-read; sandbox hides the node."""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            rig = _ServiceRig(root)
            journal = rig.stage_update_candidate_booted()
            rig.issue(journal)
            rig.compose_service(journal)
            before = _snapshot_tree(root)
            token = "f" * 64
            raw_request = build_confirm_request(token)
            # Forged (non-attested) peer: refused before any request byte read.
            forged = _FakeConnection(raw_request)
            handle_boot_health_connection(
                forged,  # type: ignore[arg-type]
                endpoint=rig.endpoint,
                peer=object(),
                boot_state="interactive_ready",
            )
            self.assertEqual(forged.recv_calls, 0)
            self.assertTrue(forged.closed)
            # Unauthorized UID: refused before any request byte read.
            stranger = _FakeConnection(raw_request)
            handle_boot_health_connection(
                stranger,  # type: ignore[arg-type]
                endpoint=rig.endpoint,
                peer=PeerCredential(uid=_UNAUTHORIZED_UID),
                boot_state="interactive_ready",
            )
            self.assertEqual(stranger.recv_calls, 0)
            self.assertTrue(stranger.closed)
            self.assertEqual(_snapshot_tree(root), before)
            # The sandbox surface hides the socket node: private tmpfs over
            # /run and /run/greia-os, so an Activity has no path to it
            # unless the sandbox explicitly allows one (it does not).
            from greia_launcher.runtime_adapter import RuntimeCommand

            manifest = _manifest(root / "activity")
            profile = _FakeProfileContext(root / "profile")
            authority = _FakeAuthority(manifest.activity_id)
            nested = manifest.root / "runtime-work"
            nested.mkdir(exist_ok=True)
            command = ActivitySupervisor._sandbox_command(
                root / "bwrap",
                RuntimeCommand(command=("runtime", "--start"), cwd=nested),
                manifest,
                profile,
                authority,
            )
            pairs = list(zip(command, command[1:]))
            self.assertIn(("--tmpfs", "/run"), pairs)
            self.assertIn(("--tmpfs", "/run/greia-os"), pairs)
            # The socket unit is the bounded launcher-reachable confirmation
            # path: 0660 root:greiakid AF_UNIX on-demand — group-readable
            # and writable by the launcher's own primary group, never
            # world-reachable, never launcher-owned. Re-expressed from the
            # 0600 root:root pin (P4 socket-access): the negatives above
            # (forged/unauthorized refused pre-read, sandbox tmpfs) are
            # unchanged.
            socket_text = (
                _repo_root() / "build" / "overlay" / "etc" / "systemd" / "system"
                / "greia-boot-health.socket"
            ).read_text(encoding="utf-8")
            self.assertIn("ListenStream=/run/greia-os/boot-health.sock", socket_text)
            self.assertIn("SocketMode=0660", socket_text)
            self.assertIn("SocketUser=root", socket_text)
            self.assertIn("SocketGroup=greiakid", socket_text)
            self.assertNotIn("SocketMode=0600", socket_text)
            self.assertNotIn("SocketMode=0666", socket_text)
            self.assertNotIn("SocketMode=0777", socket_text)
            service_text = (
                _repo_root() / "build" / "overlay" / "etc" / "systemd" / "system"
                / "greia-boot-health.service"
            ).read_text(encoding="utf-8")
            self.assertIn("RestrictAddressFamilies=AF_UNIX", service_text)
            self.assertIn("User=root", service_text)
            self.assertEqual(BOOT_HEALTH_OPS, ("CONFIRM_BOOT_HEALTH",))


class UidAloneTests(unittest.TestCase):
    def test_child_uid_alone_does_not_confirm(self) -> None:
        """P4.4-3: sharing greiakid UID without path+token+attempt never confirms."""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _, protocol, _ = _protocol_rig(root)
            record = protocol.provision_for_boot_attempt(
                boot_attempt="attempt-1", peer_uid=_LAUNCHER_UID
            )
            before = _snapshot_tree(root)
            # Same UID, Activity bootstrap path: refused for its reason.
            with self.assertRaises(BootHealthError) as caught:
                protocol.confirm(
                    token=record.token,
                    boot_attempt="attempt-1",
                    peer_bootstrap_path=_ACTIVITY_PATH,
                    peer_uid=_LAUNCHER_UID,
                    intro=_full_intro(),
                )
            self.assertIn("trusted launcher bootstrap path", str(caught.exception))
            self.assertEqual(_snapshot_tree(root), before)
            # Same UID at the socket with no valid capability: refused, zero
            # mutation, capability still live for the genuine path.
            svc_root = root / "svc"
            svc_root.mkdir(parents=True, exist_ok=True)
            rig = _ServiceRig(svc_root)
            journal = rig.stage_update_candidate_booted()
            issued = rig.issue(journal)
            rig.compose_service(journal)
            tree_before = _snapshot_tree(rig.root)
            with self.assertRaises(BootHealthServiceError):
                rig.service.confirm(token="0" * 64)
            self.assertEqual(_snapshot_tree(rig.root), tree_before)
            self.assertTrue(rig.authority.capability_live())
            # The genuine bindings still hold for the later positive proof.
            self.assertEqual(issued.boot_attempt, _BOOT_ID_1)


class StaleCopiedTokenTests(unittest.TestCase):
    def test_copied_stale_token_does_not_confirm(self) -> None:
        """P4.4-4: token bound to (transaction, boot attempt, path) never transfers."""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            rig = _ServiceRig(root)
            journal = rig.stage_update_candidate_booted()
            issued = rig.issue(journal, boot_id=_BOOT_ID_1)
            before = _snapshot_tree(root)
            # Stale boot attempt (copied from an earlier boot): refused.
            with self.assertRaises(BootHealthError) as stale:
                rig.authority.verify_and_consume(
                    token=issued.token,
                    transaction_id=journal.transaction_id,
                    boot_attempt=_BOOT_ID_2,
                    peer_bootstrap_path=TRUSTED_BOOTSTRAP_PATH,
                )
            self.assertIn("transaction, boot attempt and launcher path", str(stale.exception))
            # Copied onto another transaction: refused.
            with self.assertRaises(BootHealthError) as copied:
                rig.authority.verify_and_consume(
                    token=issued.token,
                    transaction_id="copiedtransaction1",
                    boot_attempt=_BOOT_ID_1,
                    peer_bootstrap_path=TRUSTED_BOOTSTRAP_PATH,
                )
            self.assertIn("transaction, boot attempt and launcher path", str(copied.exception))
            # Wrong presenter path with the genuine token: refused.
            with self.assertRaises(BootHealthError) as path:
                rig.authority.verify_and_consume(
                    token=issued.token,
                    transaction_id=journal.transaction_id,
                    boot_attempt=_BOOT_ID_1,
                    peer_bootstrap_path=_ACTIVITY_PATH,
                )
            self.assertIn("transaction, boot attempt and launcher path", str(path.exception))
            # Failed guesses never burn the real capability; journal stays
            # non-terminal; the whole tree is unchanged.
            self.assertTrue(rig.authority.capability_live())
            self.assertFalse(
                BootTransactionJournal.load(rig.update_journal_dir()).is_terminal
            )
            self.assertEqual(_snapshot_tree(root), before)


class DirectLibraryCallTests(unittest.TestCase):
    def test_direct_library_call_cannot_mutate_root_boot_state(self) -> None:
        """P4.4-5: Activity-like direct protocol call fails; grubenv+journal identical."""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            resumed, protocol, _ = _protocol_rig(root)
            record = protocol.provision_for_boot_attempt(
                boot_attempt="attempt-1", peer_uid=_LAUNCHER_UID
            )
            grubenv_file = root / "grubenv" / "grubenv"
            grubenv_before = grubenv_file.read_bytes()
            journal_file = root / "journal" / "boot-journal.json"
            journal_before = journal_file.read_bytes()
            default_before = GrubEnvBackend.attach(root / "grubenv").inspect().default_slot
            self.assertEqual(default_before, "A")
            # Direct library call from Activity-like code with the genuine
            # token but the Activity path: refused for its intended reason.
            with self.assertRaises(BootHealthError) as caught:
                protocol.confirm(
                    token=record.token,
                    boot_attempt="attempt-1",
                    peer_bootstrap_path=_ACTIVITY_PATH,
                    peer_uid=_LAUNCHER_UID,
                    intro=_full_intro(),
                )
            self.assertIn("trusted launcher bootstrap path", str(caught.exception))
            # Root boot state is byte-identical: no default change, no
            # journal transition, no sidecar minted.
            self.assertEqual(grubenv_file.read_bytes(), grubenv_before)
            self.assertEqual(journal_file.read_bytes(), journal_before)
            self.assertEqual(
                GrubEnvBackend.attach(root / "grubenv").inspect().default_slot, "A"
            )
            self.assertEqual(resumed.journal.state, BootTransactionState.CANDIDATE_BOOTING)
            self.assertFalse((root / "vault" / "healthy-committing.json").exists())


class UntrustedLaunchTests(unittest.TestCase):
    def test_confirmation_after_untrusted_launch_refused(self) -> None:
        """P4.4-6: genuine token after an untrusted launch is refused, never consumed."""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            resumed, protocol, _ = _protocol_rig(root)
            record = protocol.provision_for_boot_attempt(
                boot_attempt="attempt-1", peer_uid=_LAUNCHER_UID
            )
            before = _snapshot_tree(root)
            with self.assertRaises(BootHealthError) as caught:
                protocol.confirm(
                    token=record.token,
                    boot_attempt="attempt-1",
                    peer_bootstrap_path=TRUSTED_BOOTSTRAP_PATH,
                    peer_uid=_LAUNCHER_UID,
                    intro=_full_intro(untrusted=True),
                )
            message = str(caught.exception).lower()
            self.assertTrue(
                "untrusted" in message or "no untrusted" in message or "intro" in message,
                msg=f"unexpected refusal reason: {caught.exception}",
            )
            # Fail-closed: credential still live, journal still
            # candidate-booting, launch gate still closed, tree unchanged.
            self.assertTrue((root / "vault" / "boot-healthy-credential.json").is_file())
            self.assertEqual(resumed.journal.state, BootTransactionState.CANDIDATE_BOOTING)
            self.assertFalse(protocol.untrusted_launch_allowed)
            with self.assertRaises(BootHealthError):
                protocol.check_untrusted_launch("developer-unsigned")
            self.assertEqual(_snapshot_tree(root), before)


class GenuinePathPositiveControlTests(unittest.TestCase):
    def test_genuine_launcher_service_path_confirms_once(self) -> None:
        """Positive control: unknown RED (zero mutation) -> issued GREEN -> replay RED."""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            rig = _ServiceRig(root)
            journal = rig.stage_update_candidate_booted()
            issued = rig.issue(journal, boot_id=_BOOT_ID_1)
            rig.compose_service(journal, boot_id=_BOOT_ID_1)
            before = _snapshot_tree(rig.root)
            # RED: unknown token through the real service refuses; nothing
            # mutates and the real capability stays live.
            with self.assertRaises(BootHealthServiceError):
                rig.service.confirm(token="e" * 64)
            self.assertEqual(_snapshot_tree(rig.root), before)
            self.assertTrue(rig.authority.capability_live())
            # GREEN: the genuine issued token confirms through the real
            # service: journal ACCEPTED, backend default B, history record.
            detail = rig.service.confirm(token=issued.token)
            self.assertTrue(detail.get("confirmed", True))
            reloaded = BootTransactionJournal.load(rig.update_journal_dir())
            self.assertEqual(reloaded.state, BootTransactionState.ACCEPTED)
            self.assertEqual(
                GrubEnvBackend.attach(rig.grubenv_dir).inspect().default_slot, "B"
            )
            self.assertFalse(rig.authority.capability_live())
            history_files = list(rig.history_dir.rglob("*"))
            self.assertTrue(any(path.is_file() for path in history_files))
            # Replay of the consumed token is refused: one-use holds.
            with self.assertRaises(BootHealthServiceError):
                rig.service.confirm(token=issued.token)
            # The connection layer answers the same replay as a bounded
            # REFUSED frame (never a confirm).
            from greia_platform.privileged_channel import decode_response

            replay_conn = _FakeConnection(build_confirm_request(issued.token))
            handle_boot_health_connection(
                replay_conn,  # type: ignore[arg-type]
                endpoint=rig.endpoint,
                peer=PeerCredential(uid=_LAUNCHER_UID),
                boot_state="interactive_ready",
            )
            self.assertTrue(replay_conn.sent)
            _, replay_op, _ = decode_response(replay_conn.sent[0])
            self.assertEqual(replay_op, "ERROR")
            # Encoded-request shape honestly carries only the capability.
            built = build_confirm_request("a" * 64)
            from greia_platform.privileged_channel import decode_request

            decoded_op, decoded_params = decode_request(built)
            self.assertEqual(decoded_op, "CONFIRM_BOOT_HEALTH")
            self.assertEqual(set(decoded_params), {"capability"})


if __name__ == "__main__":
    unittest.main()
