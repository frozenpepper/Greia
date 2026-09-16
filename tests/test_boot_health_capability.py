"""P4.3 product proof: root-owned one-use BOOT_HEALTHY capability lifecycle.

Through production code (``greia_platform.boot_health`` authority +
generator, ``greia_launcher.boot_health`` read-only loader, the real
``BootHealthService`` commit path, the shipped systemd units):

- the root generator issues a capability only for a real pending
  transaction (first-install or update); a plain boot issues nothing and
  writes nothing (bounded no-op);
- the authoritative record is digest-only on the root side; delivery to the
  launcher is a read-only one-use token the launcher loader opens
  ``O_RDONLY`` and never writes;
- the root health service consumes the capability before committing: a
  failing consume commits nothing (full fixture-tree snapshot equality);
- replay, copied/stale-token, wrong-attempt and double-provision attempts
  refuse fail-closed;
- an Activity-scoped process (sanitized env + private /run mounts) cannot
  read the token;
- the full health predicate and the 7.0 s intro are retained.

R0/R1 only: files and fakes in disposable tmpdirs. The kernel boot ID and
the launcher UID are fixture-driven through the documented env seams.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import greia_launcher.boot_health as launcher_health
import greia_platform.boot_health as platform_health
from greia_launcher.boot_health import TRUSTED_BOOTSTRAP_PATH
from greia_launcher.supervisor import ActivitySupervisor
from greia_platform.activities import ActivityManifest, SkillContribution
from greia_platform.boot_health import (
    BOOT_HEALTH_SCHEMA_VERSION,
    BootHealthCapabilityAuthority,
    BootHealthError,
    BootHealthyProtocol,
    BootHealthCredentialVault,
    FakeActualBootIdentity,
    ActualBootIdentity,
    IntroEvidence,
    default_capability_authority,
    load_pending_boot_journal,
    main as capability_main,
    maybe_issue_boot_capability,
    read_boot_id,
)
from greia_platform.boot_health_service import (
    BootHealthService,
    BootHealthServiceError,
)
from greia_platform.boot_transaction import (
    BootArtifactSet,
    BootTransactionCoordinator,
    BootTransactionJournal,
    BootTransactionState,
    FakeGrubBackend,
)
from greia_platform.grub_ab import GrubEnvBackend
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

_PEER_UID = 1001


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _snapshot_tree(root: Path) -> dict[str, bytes]:
    snapshot: dict[str, bytes] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and not path.is_symlink():
            snapshot[str(path.relative_to(root))] = path.read_bytes()
    return snapshot


class _EnvGuard:
    """Save/restore the narrow capability-lifecycle env surface."""

    NAMES = (
        "GREIA_BOOT_HEALTH_AUTHORITY_DIR",
        "GREIA_BOOT_HEALTH_DELIVERY_DIR",
        "GREIA_BOOT_HEALTH_PEER_UID",
        "GREIA_BOOT_HEALTH_PEER_PATH",
        "GREIA_BOOT_ID_PATH",
        "CREDENTIALS_DIRECTORY",
    )

    def __init__(self, values: dict[str, str] | None = None) -> None:
        self.saved: dict[str, str | None] = {}
        self.values = values or {}

    def __enter__(self) -> "_EnvGuard":
        for name in self.NAMES:
            self.saved[name] = os.environ.get(name)
        for name, value in self.values.items():
            os.environ[name] = value
        return self

    def __exit__(self, *exc: object) -> bool:
        for name in self.NAMES:
            old = self.saved[name]
            if old is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = old
        return False


def _write_boot_id(root: Path, name: str, value: str) -> Path:
    path = root / name
    path.write_text(value + "\n", encoding="utf-8")
    return path


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


def _authority(root: Path) -> BootHealthCapabilityAuthority:
    return default_capability_authority(
        authority_dir=root / "authority",
        delivery_dir=root / "delivery",
    )


def _stage_pending_update(root: Path) -> Path:
    """Stage a non-terminal update journal (candidate B) in a tmpdir."""
    journal_dir = root / "update-state" / "system-updates" / "journal"
    journal_dir.mkdir(parents=True, exist_ok=True)
    BootTransactionJournal.begin_update(
        journal_dir,
        layout_id=_LAYOUT_ID,
        boot_backend=_BACKEND_ID,
        release_id=_RELEASE,
        candidate_slot="B",
        accepted_slot="A",
    )
    return journal_dir


def _stage_pending_first_install(root: Path) -> Path:
    journal_dir = root / "boot-journal"
    journal_dir.mkdir(parents=True, exist_ok=True)
    BootTransactionJournal.begin_first_install(
        journal_dir,
        layout_id=_LAYOUT_ID,
        boot_backend=_BACKEND_ID,
        release_id=_RELEASE,
    )
    return journal_dir


def _issue_for(
    root: Path,
    journal_dir: Path,
    *,
    boot_id: str = _BOOT_ID_1,
):
    """Issue through the production generator entry for one journal dir."""
    owner = _authority(root)
    if journal_dir.name == "journal":
        update_state = journal_dir.parents[1]
        boot_journal: Path | None = None
    else:
        update_state = root / "update-state"
        boot_journal = journal_dir
    with _EnvGuard(
        {
            "GREIA_BOOT_HEALTH_PEER_UID": str(_PEER_UID),
            "GREIA_BOOT_HEALTH_PEER_PATH": TRUSTED_BOOTSTRAP_PATH,
        }
    ):
        return maybe_issue_boot_capability(
            authority=owner,
            boot_journal_dir=boot_journal,
            update_state_dir=update_state,
            boot_id=boot_id,
            peer_bootstrap_path=TRUSTED_BOOTSTRAP_PATH,
            peer_uid=_PEER_UID,
        ), owner


class CapabilityIssuanceTests(unittest.TestCase):
    def test_update_pending_transaction_gets_a_capability(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            journal_dir = _stage_pending_update(root)
            issued, owner = _issue_for(root, journal_dir)
            assert issued is not None
            journal = BootTransactionJournal.load(journal_dir)
            self.assertEqual(issued.transaction_id, journal.transaction_id)
            self.assertEqual(issued.boot_attempt, _BOOT_ID_1)
            self.assertTrue(owner.capability_live())
            # Authoritative record: digest-only, canonical, owner-only.
            record_path = owner.record_path
            self.assertTrue(record_path.is_file())
            self.assertEqual(stat.S_IMODE(record_path.stat().st_mode), 0o600)
            record = json.loads(record_path.read_bytes().decode("utf-8"))
            self.assertEqual(record["schema_version"], BOOT_HEALTH_SCHEMA_VERSION)
            self.assertEqual(record["transaction_id"], journal.transaction_id)
            self.assertEqual(record["boot_attempt"], _BOOT_ID_1)
            self.assertEqual(record["peer_bootstrap_path"], TRUSTED_BOOTSTRAP_PATH)
            self.assertEqual(record["peer_uid"], _PEER_UID)
            self.assertNotIn(issued.token, record_path.read_bytes().decode("utf-8"))
            self.assertEqual(
                record["token_digest"],
                hashlib.sha256(issued.token.encode("utf-8")).hexdigest(),
            )
            # Delivery: raw token staged for the launcher.
            delivery = owner.delivery_path
            self.assertTrue(delivery.is_file())
            self.assertEqual(delivery.read_bytes().decode("utf-8").strip(), issued.token)

    def test_first_install_pending_transaction_gets_a_capability(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            journal_dir = _stage_pending_first_install(root)
            issued, owner = _issue_for(root, journal_dir)
            assert issued is not None
            self.assertTrue(owner.capability_live())

    def test_plain_boot_issues_nothing_and_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "update-state").mkdir(parents=True)
            (root / "boot-journal").mkdir(parents=True)
            before = _snapshot_tree(root)
            owner = _authority(root)
            with _EnvGuard(
                {
                    "GREIA_BOOT_HEALTH_PEER_UID": str(_PEER_UID),
                    "GREIA_BOOT_HEALTH_PEER_PATH": TRUSTED_BOOTSTRAP_PATH,
                }
            ):
                issued = maybe_issue_boot_capability(
                    authority=owner,
                    boot_journal_dir=root / "boot-journal",
                    update_state_dir=root / "update-state",
                    boot_id=_BOOT_ID_1,
                    peer_bootstrap_path=TRUSTED_BOOTSTRAP_PATH,
                    peer_uid=_PEER_UID,
                )
            self.assertIsNone(issued)
            self.assertFalse(owner.capability_live())
            self.assertEqual(_snapshot_tree(root), before)

    def test_terminal_journal_refuses(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            backend = FakeGrubBackend.initialize(root / "grub", default_slot="A")
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
            backend.simulate_reboot()
            coordinator = BootTransactionCoordinator.resume(
                journal_dir=root / "journal", backend=FakeGrubBackend.attach(root / "grub"),
                candidate_artifacts=candidate, accepted_artifacts=accepted,
            )
            coordinator.observe_boot()
            protocol = BootHealthyProtocol(
                coordinator=coordinator,
                candidate_root_partuuid=_UUID_B,
                candidate_release_id=_RELEASE,
                vault=BootHealthCredentialVault(root / "vault"),
                observer=FakeActualBootIdentity(
                    ActualBootIdentity(
                        booted_slot="B", root_partuuid=_UUID_B,
                        release_id=_RELEASE,
                    )
                ),
                trusted_bootstrap_path=TRUSTED_BOOTSTRAP_PATH,
            )
            record = protocol.provision_for_boot_attempt(
                boot_attempt="attempt-1", peer_uid=os.getuid()
            )
            ticket = protocol.confirm(
                token=record.token,
                boot_attempt="attempt-1",
                peer_bootstrap_path=TRUSTED_BOOTSTRAP_PATH,
                peer_uid=os.getuid(),
                intro=IntroEvidence(
                    first_frame_visible=True,
                    intro_completed=True,
                    lifecycle_state="interactive_ready",
                    untrusted_activity_launched=False,
                ),
            )
            protocol.finalize(ticket)
            committed = BootTransactionJournal.load(root / "journal")
            self.assertTrue(committed.is_terminal)
            owner = _authority(root)
            with self.assertRaises(BootHealthError):
                owner.issue_for_pending_journal(
                    committed,
                    boot_attempt=_BOOT_ID_1,
                    peer_bootstrap_path=TRUSTED_BOOTSTRAP_PATH,
                    peer_uid=_PEER_UID,
                )
            self.assertFalse(owner.capability_live())

    def test_double_provision_same_attempt_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            journal_dir = _stage_pending_update(root)
            journal = BootTransactionJournal.load(journal_dir)
            owner = _authority(root)
            first = owner.issue_for_pending_journal(
                journal,
                boot_attempt=_BOOT_ID_1,
                peer_bootstrap_path=TRUSTED_BOOTSTRAP_PATH,
                peer_uid=_PEER_UID,
            )
            with self.assertRaises(BootHealthError):
                owner.issue_for_pending_journal(
                    journal,
                    boot_attempt=_BOOT_ID_1,
                    peer_bootstrap_path=TRUSTED_BOOTSTRAP_PATH,
                    peer_uid=_PEER_UID,
                )
            # The first delivery still carries the original token.
            self.assertEqual(
                owner.delivery_path.read_bytes().decode("utf-8").strip(),
                first.token,
            )
            # And the original capability still verifies exactly once.
            record = owner.verify_and_consume(
                token=first.token,
                transaction_id=journal.transaction_id,
                boot_attempt=_BOOT_ID_1,
                peer_bootstrap_path=TRUSTED_BOOTSTRAP_PATH,
            )
            self.assertEqual(record.transaction_id, journal.transaction_id)


class ReadOnlyDeliveryTests(unittest.TestCase):
    def test_launcher_loader_returns_the_issued_token(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            journal_dir = _stage_pending_update(root)
            issued, owner = _issue_for(root, journal_dir)
            assert issued is not None
            with _EnvGuard(
                {"GREIA_BOOT_HEALTH_DELIVERY_DIR": str(root / "delivery")}
            ):
                loaded = launcher_health.maybe_load_production_token()
            self.assertEqual(loaded, issued.token)

    def test_loader_is_functionally_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            journal_dir = _stage_pending_update(root)
            issued, owner = _issue_for(root, journal_dir)
            assert issued is not None
            before = _snapshot_tree(root)
            # Even with the delivery tree forced read-only, loading works:
            # the loader performs no write.
            os.chmod(owner.delivery_path, 0o444)
            os.chmod(owner.delivery_dir, 0o555)
            try:
                with _EnvGuard(
                    {"GREIA_BOOT_HEALTH_DELIVERY_DIR": str(root / "delivery")}
                ):
                    loaded = launcher_health.maybe_load_production_token()
            finally:
                os.chmod(owner.delivery_dir, 0o750)
                os.chmod(owner.delivery_path, 0o640)
            self.assertEqual(loaded, issued.token)
            self.assertEqual(_snapshot_tree(root), before)

    def test_loader_source_never_touches_the_authority(self) -> None:
        source = inspect.getsource(launcher_health.maybe_load_production_token)
        self.assertIn("O_RDONLY", source)
        for marker in (
            "provision(",
            "atomic_write",
            "authority_dir",
            "CAPABILITY_AUTHORITY",
            "unlink(",
            "issue_for",
            "default_vault",
            "systemd_vault_dir",
        ):
            self.assertNotIn(marker, source)

    def test_missing_delivery_is_a_bounded_noop(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            with _EnvGuard(
                {"GREIA_BOOT_HEALTH_DELIVERY_DIR": str(root / "absent")}
            ):
                self.assertIsNone(launcher_health.maybe_load_production_token())

    def test_corrupt_delivery_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            delivery = root / "delivery"
            delivery.mkdir(parents=True)
            (delivery / "boot-healthy-token").write_text("not-a-token\n")
            with _EnvGuard({"GREIA_BOOT_HEALTH_DELIVERY_DIR": str(delivery)}):
                with self.assertRaises(BootHealthError):
                    launcher_health.maybe_load_production_token()

    def test_peer_path_default_matches_the_launcher_single_source(self) -> None:
        self.assertEqual(
            platform_health.CAPABILITY_PEER_PATH_DEFAULT, TRUSTED_BOOTSTRAP_PATH
        )
        self.assertEqual(
            platform_health.capability_peer_bootstrap_path(), TRUSTED_BOOTSTRAP_PATH
        )

    def test_delivery_default_hides_under_the_activity_private_run(self) -> None:
        self.assertEqual(
            str(launcher_health.production_delivery_path()),
            "/run/greia-os/boot-health/boot-healthy-token",
        )

    def test_units_declare_root_owned_read_only_delivery(self) -> None:
        units = _repo_root() / "build" / "overlay" / "etc" / "systemd" / "system"
        generator = (units / "greia-boot-health-credential.service").read_text()
        launcher = (units / "greia-launcher.service").read_text()

        def directives(text: str) -> dict[str, list[str]]:
            current, out = "", {}
            for raw_line in text.splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or line.startswith(";"):
                    continue
                if line.startswith("[") and line.endswith("]"):
                    current = line[1:-1].strip()
                    continue
                if "=" not in line:
                    continue
                key, _, value = line.partition("=")
                out.setdefault(f"{current}.{key.strip()}", []).append(value.strip())
            return out

        gen = directives(generator)
        self.assertEqual(gen.get("Service.User"), ["root"])
        self.assertEqual(gen.get("Service.Group"), ["root"])
        self.assertIn("greia-launcher.service", gen.get("Unit.Before", [""])[0])
        self.assertTrue(
            any("--issue-for-pending" in value for value in gen.get("Service.ExecStart", []))
        )
        # The generator never writes journal/GRUB/layout state.
        self.assertIn("/var/lib/greia-os", gen.get("Service.BindReadOnlyPaths", []))

        svc = directives(launcher)
        self.assertEqual(svc.get("Service.User"), ["greiakid"])
        binds = svc.get("Service.BindReadOnlyPaths", [])
        self.assertIn("-/run/greia-os/boot-health", binds)
        after = " ".join(svc.get("Unit.After", []))
        wants = " ".join(svc.get("Unit.Wants", []))
        self.assertIn("greia-boot-health-credential.service", after)
        self.assertIn("greia-boot-health-credential.service", wants)


class _AuthorityBackedVerifier:
    """Health-service verifier seam bound to one staged journal + boot ID."""

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


class _StubArtifactResolver:
    """Injected resolver: layout-bound identity for the journal's slot."""

    def resolve(
        self, journal: BootTransactionJournal
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


def _compose_with_authority(root: Path):
    """Stage a booted update candidate and wire the authority-backed service."""
    from greia_platform.boot_health_service import BootHealthService

    state_dir = root / "update-state"
    boot_journal_dir = root / "boot-journal"
    grubenv_dir = root / "grubenv"
    history_dir = root / "history"
    layout_path = root / "installed-layout.json"
    layout_path.write_bytes(
        (json.dumps(_record_dict(), sort_keys=True) + "\n").encode()
    )
    for directory in (state_dir, boot_journal_dir, grubenv_dir, history_dir):
        directory.mkdir(parents=True, exist_ok=True)
    backend = GrubEnvBackend.initialize(grubenv_dir, default_slot="A")
    update_backend = SlotBackedSystemUpdateBackend(
        state_dir,
        layout_record_path=layout_path,
        boot_backend=backend,
    )
    update_authority = SystemUpdateServiceAuthority(
        state_dir,
        SystemIdentity("0.14.0", "standard-x86-64", "x86-64", "modern-amd64"),
        update_backend,
    )
    backend.arm_one_shot("B")
    update_journal_dir = state_dir / "system-updates" / "journal"
    BootTransactionJournal.begin_update(
        update_journal_dir,
        layout_id=_LAYOUT_ID,
        boot_backend=_BACKEND_ID,
        release_id=_RELEASE,
        candidate_slot="B",
        accepted_slot="A",
    )
    backend.simulate_reboot()
    assert backend.observe_booted_slot() == "B"
    journal = BootTransactionJournal.load(update_journal_dir)
    owner = _authority(root)
    with _EnvGuard(
        {
            "GREIA_BOOT_HEALTH_PEER_UID": str(_PEER_UID),
            "GREIA_BOOT_HEALTH_PEER_PATH": TRUSTED_BOOTSTRAP_PATH,
        }
    ):
        issued = maybe_issue_boot_capability(
            authority=owner,
            boot_journal_dir=boot_journal_dir,
            update_state_dir=state_dir,
            boot_id=_BOOT_ID_1,
            peer_bootstrap_path=TRUSTED_BOOTSTRAP_PATH,
            peer_uid=_PEER_UID,
        )
    assert issued is not None
    verifier = _AuthorityBackedVerifier(owner, journal, boot_attempt=_BOOT_ID_1)
    service = BootHealthService(
        boot_journal_dir=boot_journal_dir,
        update_state_dir=state_dir,
        history_dir=history_dir,
        update_authority=update_authority,
        capability_verifier=verifier,
        artifact_resolver=_StubArtifactResolver(),
        boot_backend_factory=lambda: GrubEnvBackend.attach(grubenv_dir),
    )
    return service, journal, owner, issued, root


class ConsumeBeforeCommitTests(unittest.TestCase):
    def test_unknown_token_then_issued_token_red_then_green(self) -> None:
        """Positive control: unknown RED (zero mutation) then issued GREEN."""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            service, journal, owner, issued, _ = _compose_with_authority(root)
            before = _snapshot_tree(root)
            # RED: a guessed token refuses with zero mutation.
            with self.assertRaises(BootHealthServiceError):
                service.confirm(token="0" * 64)
            self.assertEqual(_snapshot_tree(root), before)
            pending = BootTransactionJournal.load(service.update_journal_dir)
            self.assertFalse(pending.is_terminal)
            self.assertFalse((root / "history").joinpath("boot-history.json").exists())
            self.assertTrue(owner.capability_live())
            # GREEN: the root-issued token consumes exactly once, then commits.
            detail = service.confirm(token=issued.token)
            self.assertEqual(detail.get("journal"), "update")
            committed = BootTransactionJournal.load(service.update_journal_dir)
            self.assertEqual(committed.state, BootTransactionState.ACCEPTED)
            self.assertTrue(committed.is_terminal)
            self.assertFalse(owner.capability_live())
            # The same token never commits twice.
            with self.assertRaises(BootHealthServiceError):
                service.confirm(token=issued.token)

    def test_failing_consume_commits_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            service, journal, owner, issued, _ = _compose_with_authority(root)

            class _AlwaysRefuse:
                def verify_and_consume(self, *, token: str):
                    raise BootHealthServiceError("capability refused")

            service.capability_verifier = _AlwaysRefuse()
            before = _snapshot_tree(root)
            with self.assertRaises(BootHealthServiceError):
                service.confirm(token=issued.token)
            self.assertEqual(_snapshot_tree(root), before)
            pending = BootTransactionJournal.load(service.update_journal_dir)
            self.assertFalse(pending.is_terminal)
            # The unconsumed capability is still live for the real verifier.
            self.assertTrue(owner.capability_live())


class OneUseNegativeTests(unittest.TestCase):
    def test_replay_refuses(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            journal_dir = _stage_pending_update(root)
            journal = BootTransactionJournal.load(journal_dir)
            owner = _authority(root)
            issued = owner.issue_for_pending_journal(
                journal,
                boot_attempt=_BOOT_ID_1,
                peer_bootstrap_path=TRUSTED_BOOTSTRAP_PATH,
                peer_uid=_PEER_UID,
            )
            owner.verify_and_consume(
                token=issued.token,
                transaction_id=journal.transaction_id,
                boot_attempt=_BOOT_ID_1,
                peer_bootstrap_path=TRUSTED_BOOTSTRAP_PATH,
            )
            with self.assertRaises(BootHealthError):
                owner.verify_and_consume(
                    token=issued.token,
                    transaction_id=journal.transaction_id,
                    boot_attempt=_BOOT_ID_1,
                    peer_bootstrap_path=TRUSTED_BOOTSTRAP_PATH,
                )
            self.assertFalse(owner.capability_live())

    def test_copied_token_for_another_transaction_refuses(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            first_dir = root / "update-state" / "system-updates" / "journal"
            first_dir.mkdir(parents=True, exist_ok=True)
            BootTransactionJournal.begin_update(
                first_dir,
                layout_id=_LAYOUT_ID, boot_backend=_BACKEND_ID,
                release_id=_RELEASE,
                candidate_slot="B", accepted_slot="A",
            )
            first_journal = BootTransactionJournal.load(first_dir)
            owner = _authority(root)
            copied = owner.issue_for_pending_journal(
                first_journal,
                boot_attempt=_BOOT_ID_1,
                peer_bootstrap_path=TRUSTED_BOOTSTRAP_PATH,
                peer_uid=_PEER_UID,
            )
            # A second transaction supersedes the record...
            second_dir = root / "second-journal"
            second_dir.mkdir(parents=True, exist_ok=True)
            second = BootTransactionJournal.begin_update(
                second_dir,
                layout_id=_LAYOUT_ID, boot_backend=_BACKEND_ID,
                release_id=_RELEASE,
                candidate_slot="B", accepted_slot="A",
            )
            owner.issue_for_pending_journal(
                second,
                boot_attempt=_BOOT_ID_1,
                peer_bootstrap_path=TRUSTED_BOOTSTRAP_PATH,
                peer_uid=_PEER_UID,
            )
            # ...so the copied token matches neither the new record (digest)
            # nor its own stale bindings (record replaced).
            with self.assertRaises(BootHealthError):
                owner.verify_and_consume(
                    token=copied.token,
                    transaction_id=second.transaction_id,
                    boot_attempt=_BOOT_ID_1,
                    peer_bootstrap_path=TRUSTED_BOOTSTRAP_PATH,
                )
            with self.assertRaises(BootHealthError):
                owner.verify_and_consume(
                    token=copied.token,
                    transaction_id=first_journal.transaction_id,
                    boot_attempt=_BOOT_ID_1,
                    peer_bootstrap_path=TRUSTED_BOOTSTRAP_PATH,
                )

    def test_stale_boot_attempt_refuses(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            journal_dir = _stage_pending_update(root)
            journal = BootTransactionJournal.load(journal_dir)
            owner = _authority(root)
            issued = owner.issue_for_pending_journal(
                journal,
                boot_attempt=_BOOT_ID_1,
                peer_bootstrap_path=TRUSTED_BOOTSTRAP_PATH,
                peer_uid=_PEER_UID,
            )
            # A token from an earlier boot never matches the current attempt.
            with self.assertRaises(BootHealthError):
                owner.verify_and_consume(
                    token=issued.token,
                    transaction_id=journal.transaction_id,
                    boot_attempt=_BOOT_ID_2,
                    peer_bootstrap_path=TRUSTED_BOOTSTRAP_PATH,
                )
            self.assertTrue(owner.capability_live())

    def test_wrong_presenter_path_refuses(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            journal_dir = _stage_pending_update(root)
            journal = BootTransactionJournal.load(journal_dir)
            owner = _authority(root)
            issued = owner.issue_for_pending_journal(
                journal,
                boot_attempt=_BOOT_ID_1,
                peer_bootstrap_path=TRUSTED_BOOTSTRAP_PATH,
                peer_uid=_PEER_UID,
            )
            with self.assertRaises(BootHealthError):
                owner.verify_and_consume(
                    token=issued.token,
                    transaction_id=journal.transaction_id,
                    boot_attempt=_BOOT_ID_1,
                    peer_bootstrap_path="activity.runtime:ActivityRuntime",
                )
            self.assertTrue(owner.capability_live())

    def test_tampered_delivery_token_is_useless(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            journal_dir = _stage_pending_update(root)
            journal = BootTransactionJournal.load(journal_dir)
            owner = _authority(root)
            owner.issue_for_pending_journal(
                journal,
                boot_attempt=_BOOT_ID_1,
                peer_bootstrap_path=TRUSTED_BOOTSTRAP_PATH,
                peer_uid=_PEER_UID,
            )
            # An attacker replacing the delivery file still faces the digest.
            attacker = "f" * 64
            owner.delivery_path.write_bytes((attacker + "\n").encode("utf-8"))
            with _EnvGuard(
                {"GREIA_BOOT_HEALTH_DELIVERY_DIR": str(root / "delivery")}
            ):
                loaded = launcher_health.maybe_load_production_token()
            self.assertEqual(loaded, attacker)
            with self.assertRaises(BootHealthError):
                owner.verify_and_consume(
                    token=loaded,
                    transaction_id=journal.transaction_id,
                    boot_attempt=_BOOT_ID_1,
                    peer_bootstrap_path=TRUSTED_BOOTSTRAP_PATH,
                )


class PeerUidBindingClaimTests(unittest.TestCase):
    """Pin the R01-01 unclaim disposition: claim and gate agree on UID.

    Enforced set is token digest + transaction_id + boot_attempt +
    peer_bootstrap_path; peer_uid is provenance/audit metadata only
    (shape-validated, never consume-gated). Any divergence between the
    documented set and the enforced set must turn this class RED.
    """

    def _rewrite_record_peer_uid(self, owner, peer_uid: object) -> None:
        record = json.loads(owner.record_path.read_bytes().decode("utf-8"))
        record["peer_uid"] = peer_uid
        canonical = (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        owner.record_path.write_bytes(canonical)
        os.chmod(owner.record_path, 0o600)

    def test_peer_uid_change_does_not_break_verify(self) -> None:
        """Behavioral pin: stored peer_uid is not a consume-time binding."""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            journal_dir = _stage_pending_update(root)
            journal = BootTransactionJournal.load(journal_dir)
            owner = _authority(root)
            issued = owner.issue_for_pending_journal(
                journal,
                boot_attempt=_BOOT_ID_1,
                peer_bootstrap_path=TRUSTED_BOOTSTRAP_PATH,
                peer_uid=_PEER_UID,
            )
            self._rewrite_record_peer_uid(owner, _PEER_UID + 1000)
            record = owner.verify_and_consume(
                token=issued.token,
                transaction_id=journal.transaction_id,
                boot_attempt=_BOOT_ID_1,
                peer_bootstrap_path=TRUSTED_BOOTSTRAP_PATH,
            )
            self.assertEqual(record.transaction_id, journal.transaction_id)
            self.assertFalse(owner.capability_live())

    def test_peer_uid_shape_still_validated(self) -> None:
        """The retained field is meaningfully validated (shape, not gate)."""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            journal_dir = _stage_pending_update(root)
            journal = BootTransactionJournal.load(journal_dir)
            owner = _authority(root)
            owner.issue_for_pending_journal(
                journal,
                boot_attempt=_BOOT_ID_1,
                peer_bootstrap_path=TRUSTED_BOOTSTRAP_PATH,
                peer_uid=_PEER_UID,
            )
            self._rewrite_record_peer_uid(owner, -1)
            self.assertFalse(owner.capability_live())
            with self.assertRaises(BootHealthError):
                owner.verify_and_consume(
                    token="0" * 64,
                    transaction_id=journal.transaction_id,
                    boot_attempt=_BOOT_ID_1,
                    peer_bootstrap_path=TRUSTED_BOOTSTRAP_PATH,
                )

    def test_documented_set_matches_enforced_set(self) -> None:
        """Claim/behavior agreement: no UID-binding claim; no UID gate."""
        module_path = Path(inspect.getfile(platform_health))
        module_text = module_path.read_text(encoding="utf-8")
        # No durable comment may present peer_uid as part of the bound tuple.
        self.assertNotIn("peer_bootstrap_path, peer_uid", module_text)
        self.assertNotIn("launcher path, launcher UID", module_text)
        # The non-binding disposition must be stated explicitly.
        self.assertIn("NOT a consume-time binding", module_text)
        self.assertIn("never gates on it", module_text)
        # The enforced gate itself must not compare peer_uid.
        verifier_source = inspect.getsource(
            BootHealthCapabilityAuthority.verify_and_consume
        )
        self.assertNotIn("record.peer_uid", verifier_source)
        self.assertNotIn("resolve_capability_peer_uid", verifier_source)
        self.assertIn("NOT enforced here", verifier_source)
        # The generator unit claim must agree as well.
        units = _repo_root() / "build" / "overlay" / "etc" / "systemd" / "system"
        generator = (units / "greia-boot-health-credential.service").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("launcher UID", generator)
        self.assertIn("not a consume-time", generator)


class ActivityIsolationTests(unittest.TestCase):
    def _manifest(self, root: Path) -> ActivityManifest:
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

    def test_activity_environment_drops_the_credential(self) -> None:
        from greia_launcher.runtime_adapter import RuntimeCommand

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            manifest = self._manifest(root / "activity")
            profile = _FakeProfileContext(root / "profile")
            authority = _FakeAuthority(manifest.activity_id)
            with mock.patch.dict(
                os.environ,
                {
                    "CREDENTIALS_DIRECTORY": "/run/credentials/greia-launcher.service",
                    "GREIA_BOOT_HEALTH_DELIVERY_DIR": str(root / "delivery"),
                },
                clear=False,
            ):
                environment = ActivitySupervisor._sanitized_environment(
                    manifest, profile, authority, "session-1", sandboxed=True
                )
        self.assertNotIn("CREDENTIALS_DIRECTORY", environment)
        self.assertNotIn("GREIA_BOOT_HEALTH_DELIVERY_DIR", environment)
        # The allowlist is closed: no credential-shaped name survives.
        for name in environment:
            self.assertNotIn("CREDENTIAL", name.upper())
            self.assertNotIn("BOOT_HEALTH", name.upper())

    def test_activity_mounts_hide_the_runtime_delivery(self) -> None:
        from greia_launcher.runtime_adapter import RuntimeCommand

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            manifest = self._manifest(root / "activity")
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

    def test_activity_scoped_process_cannot_resolve_a_token(self) -> None:
        """A process with only Activity-visible env finds no capability."""
        from greia_launcher.runtime_adapter import RuntimeCommand

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            delivery = root / "delivery"
            delivery.mkdir(parents=True)
            (delivery / "boot-healthy-token").write_text("a" * 64 + "\n")
            manifest = self._manifest(root / "activity")
            profile = _FakeProfileContext(root / "profile")
            authority = _FakeAuthority(manifest.activity_id)
            with mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop("GREIA_BOOT_HEALTH_DELIVERY_DIR", None)
                os.environ.pop("CREDENTIALS_DIRECTORY", None)
                activity_env = ActivitySupervisor._sanitized_environment(
                    manifest, profile, authority, "session-1", sandboxed=True
                )
            # The Activity env carries neither the vault pointer nor a
            # delivery override, so the loader resolves the production bind
            # (/run/..., absent in this sandbox) and yields the plain-boot
            # no-op instead of the staged token.
            with mock.patch.dict(os.environ, activity_env, clear=True):
                self.assertNotIn("GREIA_BOOT_HEALTH_DELIVERY_DIR", os.environ)
                self.assertIsNone(launcher_health.maybe_load_production_token())


class _FakeProfile:
    profile_id = "0123456789abcdef0123456789abcdef"
    display_name = "Mia"
    avatar_id = "unicorn"


class _FakeProfileContext:
    def __init__(self, root: Path):
        self.root = root
        self.profile = _FakeProfile()
        self.customization_dir = root / "customization"
        self.customization_dir.mkdir(parents=True, exist_ok=True)

    def activity_data_dir(self, activity_id: str) -> Path:
        path = self.root / "activities" / activity_id
        path.mkdir(parents=True, exist_ok=True)
        return path


class _FakeAuthority:
    def __init__(self, activity_id: str):
        self.activity_id = activity_id
        self.package_digest = "a" * 64
        self.package_trust = PackageTrust.BUILT_IN
        self.effective_capabilities = frozenset({"display", "pointer"})
        self.sdk_features = frozenset({"display", "pointer"})

    def has_capability(self, capability: str) -> bool:
        return capability in self.effective_capabilities

    def has_permission(self, permission: str) -> bool:
        return False


class PredicateAndIntroTests(unittest.TestCase):
    def test_intro_remains_seven_seconds(self) -> None:
        from greia_launcher import boot_intro

        self.assertEqual(boot_intro.ANIMATION_SECONDS, 5.0)
        self.assertEqual(boot_intro.FINAL_FRAME_HOLD_SECONDS, 2.0)
        self.assertEqual(
            boot_intro.ANIMATION_SECONDS + boot_intro.FINAL_FRAME_HOLD_SECONDS, 7.0
        )

    def test_full_health_predicate_is_retained(self) -> None:
        """First-frame-only evidence still refuses through the protocol."""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            backend = FakeGrubBackend.initialize(root / "grub", default_slot="A")
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
            backend.simulate_reboot()
            rebooted = FakeGrubBackend.attach(root / "grub")
            coordinator = BootTransactionCoordinator.resume(
                journal_dir=root / "journal", backend=rebooted,
                candidate_artifacts=candidate, accepted_artifacts=accepted,
            )
            coordinator.observe_boot()
            protocol = BootHealthyProtocol(
                coordinator=coordinator,
                candidate_root_partuuid=_UUID_B,
                candidate_release_id=_RELEASE,
                vault=BootHealthCredentialVault(root / "vault"),
                observer=FakeActualBootIdentity(
                    ActualBootIdentity(
                        booted_slot="B", root_partuuid=_UUID_B,
                        release_id=_RELEASE,
                    )
                ),
                trusted_bootstrap_path=TRUSTED_BOOTSTRAP_PATH,
            )
            record = protocol.provision_for_boot_attempt(
                boot_attempt="attempt-1", peer_uid=os.getuid()
            )
            ready_only = IntroEvidence(
                first_frame_visible=True,
                intro_completed=False,
                lifecycle_state="first_frame_visible",
                untrusted_activity_launched=False,
            )
            self.assertFalse(ready_only.is_post_intro_interactive)
            with self.assertRaises(BootHealthError):
                protocol.confirm(
                    token=record.token,
                    boot_attempt="attempt-1",
                    peer_bootstrap_path=TRUSTED_BOOTSTRAP_PATH,
                    peer_uid=os.getuid(),
                    intro=ready_only,
                )
            # The full evidence still accepts.
            ticket = protocol.confirm(
                token=record.token,
                boot_attempt="attempt-1",
                peer_bootstrap_path=TRUSTED_BOOTSTRAP_PATH,
                peer_uid=os.getuid(),
                intro=IntroEvidence(
                    first_frame_visible=True,
                    intro_completed=True,
                    lifecycle_state="interactive_ready",
                    untrusted_activity_launched=False,
                ),
            )
            outcome = protocol.finalize(ticket)
            self.assertEqual(outcome.accepted_slot, "B")
            self.assertTrue(protocol.untrusted_launch_allowed)


class GeneratorEntryTests(unittest.TestCase):
    def test_main_issues_for_pending(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            journal_dir = _stage_pending_update(root)
            boot_id_file = _write_boot_id(root, "boot-id", _BOOT_ID_1)
            with _EnvGuard(
                {
                    "GREIA_BOOT_HEALTH_PEER_UID": str(_PEER_UID),
                    "GREIA_BOOT_HEALTH_PEER_PATH": TRUSTED_BOOTSTRAP_PATH,
                }
            ):
                code = capability_main(
                    [
                        "--issue-for-pending",
                        "--authority-dir", str(root / "authority"),
                        "--delivery-dir", str(root / "delivery"),
                        "--update-state-dir", str(root / "update-state"),
                        "--boot-journal-dir", str(root / "boot-journal"),
                        "--boot-id-path", str(boot_id_file),
                    ]
                )
            self.assertEqual(code, 0)
            owner = _authority(root)
            self.assertTrue(owner.capability_live())
            journal = BootTransactionJournal.load(journal_dir)
            record = owner.verify_and_consume(
                token=owner.delivery_path.read_bytes().decode("utf-8").strip(),
                transaction_id=journal.transaction_id,
                boot_attempt=_BOOT_ID_1,
                peer_bootstrap_path=TRUSTED_BOOTSTRAP_PATH,
            )
            self.assertEqual(record.transaction_id, journal.transaction_id)

    def test_main_plain_boot_is_a_noop(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "update-state").mkdir(parents=True)
            (root / "boot-journal").mkdir(parents=True)
            boot_id_file = _write_boot_id(root, "boot-id", _BOOT_ID_1)
            before = _snapshot_tree(root)
            with _EnvGuard(
                {
                    "GREIA_BOOT_HEALTH_PEER_UID": str(_PEER_UID),
                    "GREIA_BOOT_HEALTH_PEER_PATH": TRUSTED_BOOTSTRAP_PATH,
                }
            ):
                code = capability_main(
                    [
                        "--issue-for-pending",
                        "--authority-dir", str(root / "authority"),
                        "--delivery-dir", str(root / "delivery"),
                        "--update-state-dir", str(root / "update-state"),
                        "--boot-journal-dir", str(root / "boot-journal"),
                        "--boot-id-path", str(boot_id_file),
                    ]
                )
            self.assertEqual(code, 0)
            # Only the boot-id fixture exists; nothing was generated.
            self.assertEqual(_snapshot_tree(root), before)

    def test_main_second_issue_for_same_boot_refuses(self) -> None:
        """Positive control on the CLI path: ISSUE GREEN then REFUSED RED."""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _stage_pending_update(root)
            boot_id_file = _write_boot_id(root, "boot-id", _BOOT_ID_1)
            argv = [
                "--issue-for-pending",
                "--authority-dir", str(root / "authority"),
                "--delivery-dir", str(root / "delivery"),
                "--update-state-dir", str(root / "update-state"),
                "--boot-journal-dir", str(root / "boot-journal"),
                "--boot-id-path", str(boot_id_file),
            ]
            with _EnvGuard(
                {
                    "GREIA_BOOT_HEALTH_PEER_UID": str(_PEER_UID),
                    "GREIA_BOOT_HEALTH_PEER_PATH": TRUSTED_BOOTSTRAP_PATH,
                }
            ):
                self.assertEqual(capability_main(argv), 0)
                self.assertEqual(capability_main(argv), 1)

    def test_boot_id_shape_is_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            bad = _write_boot_id(root, "boot-id", "not-a-uuid")
            with self.assertRaises(BootHealthError):
                read_boot_id(bad)
            good = _write_boot_id(root, "boot-id-good", _BOOT_ID_1)
            self.assertEqual(read_boot_id(good), _BOOT_ID_1)

    def test_pending_journal_discovery_helpers(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "update-state").mkdir(parents=True)
            (root / "boot-journal").mkdir(parents=True)
            self.assertIsNone(
                load_pending_boot_journal(
                    boot_journal_dir=root / "boot-journal",
                    update_state_dir=root / "update-state",
                )
            )
            journal_dir = _stage_pending_update(root)
            found = load_pending_boot_journal(
                boot_journal_dir=root / "boot-journal",
                update_state_dir=root / "update-state",
            )
            assert found is not None
            self.assertEqual(found[0], journal_dir)


if __name__ == "__main__":
    unittest.main()
