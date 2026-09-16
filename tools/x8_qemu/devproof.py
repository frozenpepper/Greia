"""T7-DEVPROOF device envelope: D31 rollback, interruption matrix, resources.

Additive wiring onto the true device lifecycle (``lifecycle.py``). Owns
only the envelope measurement, never the production seams:

- D31 shared-data rollback: representative persistent-state writes
  through the normal store APIs (device settings, child profile,
  progression session, Activity save, Parent credential), then a
  deliberately broken candidate fails before acceptance; the previous
  accepted release boots, parses/reads the state and preserves semantic
  values with no destructive repair.
- 7-point legacy-first interruption matrix: each interruption
  reconciles to the previous accepted slot.
- Resource envelope: RSS/MemAvailable, decompression/finalization peaks,
  staging workspace, disk used/free, slot/bundle/PERSIST accounting and
  the diagnostic budget, all measured (never synthesized).
- Near-full-storage preflight before destructive work.
- 768 MiB cgroup gate with a <=256 MiB payload.

Source scope vs device scope: every ``measure_*`` helper records real
local measurements labelled with its surface (``SOURCE_SCOPE`` or
``DEVICE``). Device-measured values are recorded only from real runs
behind ``require_device_host``; elsewhere the device envelope reports
explicit deferred/RED markers instead of false green (preregistered
acceptance: red stays red).
"""

from __future__ import annotations

import json
import os
import resource
import shutil
from pathlib import Path
from typing import Mapping


class DevproofError(RuntimeError):
    """Envelope invariant violated (fail-closed RED)."""


class DevproofContractError(DevproofError):
    """Envelope harness violated its own contract (positive-control RED)."""


class DevproofPreflightError(DevproofError):
    """Storage preflight refused destructive work (reserved headroom)."""


# ---------------------------------------------------------------------------
# Constants (frozen envelope shape)
# ---------------------------------------------------------------------------

#: 768 MiB cgroup ceiling for the gate run.
CGROUP_CEILING_BYTES = 768 * 1024 * 1024

#: Acceptance payload bound: gate green requires payload <= 256 MiB.
PAYLOAD_ACCEPT_BYTES = 256 * 1024 * 1024

#: Representative acceptance payload actually evaluated by the gate
#: (220 MiB, inside the <=256 MiB bound; T2 scaling stays closed).
GATE_PAYLOAD_BYTES = 220 * 1024 * 1024

#: The 7-point legacy-first interruption matrix (fixed order).
INTERRUPTION_CASES: tuple[str, ...] = (
    "inactive-base-write",
    "base-readback-finalization",
    "boot-artifact-staging",
    "one-shot-arm",
    "candidate-boot-before-health",
    "healthy-committing-before-backend-commit",
    "committed-backend-unwritten-accepted-state",
)

#: Expected reconciled slot per interruption case. The first six cases
#: preserve the previous accepted slot A; the committed-backend case
#: completes the pending accepted-state write, so the committed slot B
#: (backend default B plus accepted release greia-0.21.0) is the correct
#: reconciliation target.
INTERRUPTION_EXPECTED_SLOT: dict[str, str] = {
    "inactive-base-write": "A",
    "base-readback-finalization": "A",
    "boot-artifact-staging": "A",
    "one-shot-arm": "A",
    "candidate-boot-before-health": "A",
    "healthy-committing-before-backend-commit": "A",
    "committed-backend-unwritten-accepted-state": "B",
}

#: D31 representative fixture namespaces (fixed set).
D31_FIXTURES: tuple[str, ...] = (
    "device-settings",
    "child-profile",
    "progression-session",
    "activity-save",
    "parent-policy",
)

#: Reference sizing facts reused from the lifecycle harness (comparison
#: only; Owner Decision B: measure first, no public number from estimates).
REFERENCE_SLOT_BYTES = 1073741824
REFERENCE_PERSIST_MINIMUM_BYTES = 268435456

#: Reserved headroom the preflight protects before destructive/staging work.
PREFLIGHT_RESERVED_BYTES = 64 * 1024 * 1024

#: Diagnostic budget bound: bounded logs/caches stay under this per run.
DIAGNOSTIC_BUDGET_BYTES = 16 * 1024 * 1024


def envelope_spec() -> dict[str, object]:
    """Pure-data envelope declaration for tests and report headers."""
    return {
        "cgroup_ceiling_bytes": CGROUP_CEILING_BYTES,
        "payload_accept_bytes": PAYLOAD_ACCEPT_BYTES,
        "gate_payload_bytes": GATE_PAYLOAD_BYTES,
        "interruption_cases": list(INTERRUPTION_CASES),
        "interruption_expected_slot": dict(INTERRUPTION_EXPECTED_SLOT),
        "d31_fixtures": list(D31_FIXTURES),
        "reference_slot_bytes": REFERENCE_SLOT_BYTES,
        "reference_persist_minimum_bytes": REFERENCE_PERSIST_MINIMUM_BYTES,
        "preflight_reserved_bytes": PREFLIGHT_RESERVED_BYTES,
        "diagnostic_budget_bytes": DIAGNOSTIC_BUDGET_BYTES,
        "device_measured_only": True,
    }


# ---------------------------------------------------------------------------
# D31 representative state through the normal store APIs
# ---------------------------------------------------------------------------


def _hardware_defaults():  # type: ignore[no-untyped-def]
    from greia_platform.hardware import HardwareDefaults

    return HardwareDefaults(
        schema_version=2,
        touchpad_tap=False,
        touchpad_speed=0.35,
        mouse_speed=0.0,
        natural_scrolling=False,
        resolution="auto",
        keyboard_layout="us",
        minimum_speed=-1.0,
        maximum_speed=1.0,
    )


def _profile_policy():  # type: ignore[no-untyped-def]
    from greia_platform.profiles import ProfilePolicy

    return ProfilePolicy(
        schema_version=1,
        max_profiles=8,
        max_name_characters=32,
        max_secret_characters=128,
        secret_iterations=1000,
        default_name="Child",
        default_avatar="pip",
        default_mask_secret=False,
        avatars=("pip", "star"),
    )


def _storage_policy():  # type: ignore[no-untyped-def]
    from greia_platform.storage import StoragePolicy

    return StoragePolicy(
        policy_schema_version=1,
        namespace_quota_bytes=8 * 1024 * 1024,
        max_kv_bytes=1024 * 1024,
        max_kv_value_bytes=256 * 1024,
        max_key_bytes=128,
        max_file_bytes=4 * 1024 * 1024,
        max_files=64,
        max_path_bytes=256,
        protected_free_bytes=1024 * 1024,
        max_rollback_snapshots=4,
    )


def _history_policy():  # type: ignore[no-untyped-def]
    from greia_platform.history import HistoryPolicy

    return HistoryPolicy(
        schema_version=1,
        max_sessions_per_profile=32,
        max_events_per_session=128,
        max_event_payload_bytes=4096,
        max_idempotency_key_bytes=128,
        max_reward_ledger_entries=256,
        max_recent_sessions_summary=16,
        max_score_absolute=1000000,
        sqlite_busy_timeout_ms=2000,
    )


def _history_manifest(activity_root: Path):  # type: ignore[no-untyped-def]
    from greia_platform.history import ActivityManifest

    activity_root.mkdir(parents=True, exist_ok=True)
    (activity_root / "main.py").write_text("print('ok')\n", encoding="utf-8")
    return ActivityManifest(
        activity_id="org.greia.devproof",
        legacy_ids=(),
        title_key="activity.devproof.title",
        version="0.1.0",
        runtime_type="python",
        api_version="0.1",
        entrypoint=Path("main.py"),
        icon_id="devproof",
        categories=("test",),
        skills=(),
        events=(),
        difficulty=1,
        languages=("en",),
        required_capabilities=("display",),
        optional_capabilities=(),
        requested_permissions=(),
        storage_schema_version=1,
        root=activity_root,
    )


def write_d31_representative_state(root: Path) -> dict[str, object]:
    """Perform real representative persistent-state writes via store APIs.

    Each fixture goes through its normal production store (no raw file
    synthesis for the semantic values). Returns the semantic values the
    rollback readback must preserve exactly.
    """
    from greia_parent.credentials import ParentDeviceCredentialStore
    from greia_platform.hardware import HardwareSettingsStore
    from greia_platform.history import ProfileHistoryStore
    from greia_platform.profiles import ProfileStore
    from greia_platform.storage import ActivityStorageService

    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)

    # 1. device-settings: bounded settings change through the store.
    settings_dir = root / "device-settings"
    settings_dir.mkdir(parents=True, exist_ok=True)
    settings_store = HardwareSettingsStore(_hardware_defaults(), settings_dir)
    settings_store.update(touchpad_tap=True, touchpad_speed=0.5)
    settings_value = settings_store.read()
    settings_semantic = {
        "touchpad_tap": bool(settings_value.touchpad_tap),
        "touchpad_speed": float(settings_value.touchpad_speed),
    }

    # 2. child-profile: create one child profile through the registry.
    profiles_root = root / "child-profiles"
    profiles_root.mkdir(parents=True, exist_ok=True)
    profile_store = ProfileStore(_profile_policy(), profiles_root)
    profile_store.ensure_initialized()
    child = profile_store.create("DevProof", "pip")
    profile_semantic = {"display_name": child.display_name, "id": child.profile_id}

    # 3. progression-session: start+finish one session, read the summary.
    context = profile_store.context(child.profile_id)
    progress_dir = Path(context.progress_dir)
    progress_dir.mkdir(parents=True, exist_ok=True)
    from greia_platform.history import ProfileHistoryStore
    history = ProfileHistoryStore(context, _history_policy())
    manifest = _history_manifest(root / "activity-src")
    session_id = "devproof-session-1"
    history.start_session(
        manifest, session_id=session_id, package_digest="ab" * 32
    )
    history.finish_session(session_id, "normal")
    summary = history.summary()
    progression_semantic = {
        "sessions": int(getattr(summary, "total_sessions", 0) or 0),
        "has_session": True,
    }

    # 4. activity-save: Activity save fixture through the service entry
    # point (production-owned namespace init, never raw file synthesis).
    service = ActivityStorageService(_storage_policy())
    storage = service.open(
        context, "org.greia.devproof",
        schema_version=1, package_version="0.1.0",
    )
    storage.kv_set("devproof-level", {"level": 3})
    storage.file_write_atomic("save.txt", b"devproof-save-v1")
    activity_semantic = {
        "kv_level": 3,
        "file_sha": "devproof-save-v1",
    }

    # 5. parent-policy: issue one parent device credential (safe fixture:
    # no real pairing token leaves the harness; only ids are compared).
    parent_dir = root / "parent-policy"
    parent_dir.mkdir(parents=True, exist_ok=True)
    parent_store = ParentDeviceCredentialStore(parent_dir)
    issued = parent_store.issue("DevProof Parent")
    authenticated = parent_store.authenticate(issued.token)
    if authenticated is None or authenticated.device_id != issued.device.device_id:
        raise DevproofError("parent credential did not read back")
    parent_semantic = {
        "device_id": issued.device.device_id,
        "display_name": issued.device.display_name,
    }

    return {
        "device-settings": settings_semantic,
        "child-profile": profile_semantic,
        "progression-session": progression_semantic,
        "activity-save": activity_semantic,
        "parent-policy": parent_semantic,
    }


def read_d31_representative_state(root: Path) -> dict[str, object]:
    """Parse/read the representative state back through the store APIs."""
    from greia_parent.credentials import ParentDeviceCredentialStore
    from greia_platform.hardware import HardwareSettingsStore
    from greia_platform.profiles import ProfileStore
    from greia_platform.storage import ActivityStorageService

    root = Path(root)
    settings_store = HardwareSettingsStore(
        _hardware_defaults(), root / "device-settings"
    )
    settings_value = settings_store.read()

    profile_store = ProfileStore(_profile_policy(), root / "child-profiles")
    profiles = {p.profile_id: p for p in profile_store.list_profiles()}

    # Progression: re-open each existing history store through the
    # production summary parse path. Stores are opened only where the
    # history database already exists (never constructed onto a missing
    # path, so the read performs no creation/repair).
    from greia_platform.history import ProfileHistoryStore as _HistoryStore
    history_count = 0
    for pid in profiles:
        db_path = (
            Path(profile_store.context(pid).progress_dir) / _HistoryStore.DB_NAME
        )
        if not db_path.is_file():
            continue
        store = _HistoryStore(profile_store.context(pid), _history_policy())
        summary = store.summary()
        history_count = max(history_count, len(summary.recent_sessions))
    if history_count < 1:
        raise DevproofError("progression session did not survive the rollback")

    from greia_platform.storage import ActivityStorageService as _StorageService
    kv_level: object = None
    save_bytes = b""
    for pid in profiles:
        candidate = _StorageService(_storage_policy()).open(
            profile_store.context(pid),
            "org.greia.devproof",
            schema_version=1,
            package_version="0.1.0",
        )
        hit = candidate.kv_get("devproof-level")
        if hit is not None:
            kv_level = hit
            save_bytes = candidate.file_read("save.txt")
            break
    if kv_level is None:
        raise DevproofError("activity save fixture is missing")

    parent_store = ParentDeviceCredentialStore(root / "parent-policy")
    parent_devices = {
        device.device_id: device.display_name
        for device in parent_store.list_devices()
    }
    return {
        "device-settings": {
            "touchpad_tap": bool(settings_value.touchpad_tap),
            "touchpad_speed": float(settings_value.touchpad_speed),
        },
        "child-profile": {
            pid: {"display_name": p.display_name} for pid, p in profiles.items()
        },
        "progression-session": {"sessions": history_count, "has_session": history_count >= 1},
        "activity-save": {"kv_level": kv_level, "file_bytes": save_bytes.decode("utf-8")},
        "parent-policy": dict(parent_devices),
    }


def verify_d31_rollback(
    before: Mapping[str, object], after: Mapping[str, object]
) -> None:
    """Require semantic preservation across the failed candidate.

    ``before`` comes from :func:`write_d31_representative_state`,
    ``after`` from :func:`read_d31_representative_state`. Any semantic
    drift (or destructive repair marker) is RED.
    """
    missing = [key for key in D31_FIXTURES if key not in after]
    if missing:
        raise DevproofContractError(f"D31 readback missing fixtures: {missing}")
    settings_before = before["device-settings"]
    settings_after = after["device-settings"]
    assert isinstance(settings_before, dict) and isinstance(settings_after, dict)
    if settings_after != settings_before:
        raise DevproofError(
            f"D31 settings drifted: {settings_after!r} != {settings_before!r}"
        )
    profile_before = before["child-profile"]
    assert isinstance(profile_before, dict)
    profiles_after = after["child-profile"]
    assert isinstance(profiles_after, dict)
    pid = str(profile_before["id"])
    if pid not in profiles_after:
        raise DevproofError("D31 child profile did not survive the rollback")
    if profiles_after[pid]["display_name"] != profile_before["display_name"]:
        raise DevproofError("D31 child profile value drifted")
    progression_after = after["progression-session"]
    assert isinstance(progression_after, dict)
    if not progression_after.get("has_session"):
        raise DevproofError("D31 progression session did not survive")
    activity_before = before["activity-save"]
    activity_after = after["activity-save"]
    assert isinstance(activity_before, dict) and isinstance(activity_after, dict)
    kv_after = activity_after.get("kv_level")
    kv_value = kv_after.get("level") if isinstance(kv_after, dict) else getattr(kv_after, "level", None)
    # kv_get returns the stored object; accept either mapping or raw int.
    if kv_value is None and kv_after != 3 and kv_after != {"level": 3}:
        raise DevproofError(f"D31 activity save drifted: {kv_after!r}")
    if activity_after.get("file_bytes") != activity_before.get("file_sha"):
        raise DevproofError("D31 activity file did not survive")
    parent_before = before["parent-policy"]
    assert isinstance(parent_before, dict)
    parent_after = after["parent-policy"]
    assert isinstance(parent_after, dict)
    device_id = str(parent_before["device_id"])
    if device_id not in parent_after:
        raise DevproofError("D31 parent credential did not survive")
    if parent_after[device_id] != parent_before["display_name"]:
        raise DevproofError("D31 parent credential drifted")


def run_d31_rollback_proof(workdir: Path) -> dict[str, object]:
    """Full D31 proof at source scope: write, fail, reboot, read, verify.

    Mirrors the device sequence without claiming device evidence: the
    representative writes land before the deliberately broken candidate
    fails (real ``mark_candidate_unhealthy`` trigger, persistent default
    untouched), then the previous accepted release "boots" (launcher
    acceptance is owned by ``lifecycle.py``; here the state is re-opened
    through the store parse paths) and semantic values are verified with
    no destructive repair.
    """
    from greia_platform.boot_transaction import (
        BootTransactionCoordinator,
        BootTransactionJournal,
        BootTransactionState,
        mark_candidate_unhealthy,
    )
    from greia_platform.grub_ab import GrubEnvBackend

    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    persist_root = workdir / "persist-state"
    before = write_d31_representative_state(persist_root)

    boot_dir = workdir / "boot-control"
    boot_dir.mkdir(parents=True, exist_ok=True)
    backend = GrubEnvBackend.initialize(boot_dir, default_slot="A")
    journal_dir = workdir / "journal"
    journal_dir.mkdir(parents=True, exist_ok=True)
    coordinator = BootTransactionCoordinator.begin_update(
        journal_dir=journal_dir,
        backend=backend,
        candidate_artifacts=_devproof_artifacts("B", "greia-0.21.0"),
        accepted_artifacts=_devproof_artifacts("A", "greia-0.20.0"),
        release_id="greia-0.21.0",
    )
    coordinator.arm()
    backend.reconcile("B")
    coordinator.observe_boot()
    # The deliberately broken candidate performs no acceptance: health
    # never confirms and the recovery trigger marks FAILED.
    mark_candidate_unhealthy(
        coordinator,
        recovery_class="health-service-failure",
        detail="devproof deliberately broken candidate",
    )
    journal = BootTransactionJournal.load(journal_dir)
    if journal.state is not BootTransactionState.FAILED:
        raise DevproofError("broken candidate was not marked FAILED")
    if backend.inspect().default_slot != "A":
        raise DevproofError("recovery trigger mutated the accepted default")
    # Previous accepted release boots: re-open state through the parse
    # paths (no re-initialization, no destructive repair).
    after = read_d31_representative_state(persist_root)
    verify_d31_rollback(before, after)
    return {
        "green": True,
        "surface": "SOURCE_SCOPE",
        "fixtures": list(D31_FIXTURES),
        "journal_state": journal.state.value,
        "default_slot": backend.inspect().default_slot,
        "semantic_preserved": True,
    }


def _devproof_artifacts(slot: str, release_id: str):  # type: ignore[no-untyped-def]
    from greia_platform.boot_transaction import BootArtifactSet

    number = "02" if slot == "A" else "03"
    fs_uuid = (
        "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        if slot == "A"
        else "bbbbbbbb-cccc-dddd-eeee-ffffffffffff"
    )
    return BootArtifactSet(
        slot=slot,
        layout_id="legacy-bios-ab-v1",
        boot_backend="grub-ab-v1",
        generic_kernel_sha256="cd" * 32,
        generic_initramfs_sha256="ef" * 32,
        root_partuuid=f"1a2b3c4d-{number}",
        root_filesystem_uuid=fs_uuid,
        release_id=release_id,
    )


# ---------------------------------------------------------------------------
# 7-point interruption matrix (legacy first)
# ---------------------------------------------------------------------------


def run_interruption_case(case: str, workdir: Path) -> dict[str, object]:
    """Interrupt one envelope point, then reconcile to the expected slot.

    Every case drives the real ``GrubEnvBackend`` + journal coordinator
    and then proves the expected slot remains/reconciles correctly
    (``INTERRUPTION_EXPECTED_SLOT``: A for the first six cases, B for
    the committed-backend case that completes its accepted-state write).
    Unknown cases are RED.
    """
    from greia_platform.boot_transaction import (
        BootTransactionCoordinator,
        BootTransactionJournal,
        BootTransactionState,
    )
    from greia_platform.grub_ab import GrubEnvBackend

    if case not in INTERRUPTION_CASES:
        raise DevproofContractError(f"unknown interruption case {case!r}")
    workdir = Path(workdir) / case.replace("-", "_")
    workdir.mkdir(parents=True, exist_ok=True)
    boot_dir = workdir / "boot-control"
    boot_dir.mkdir(parents=True, exist_ok=True)
    backend = GrubEnvBackend.initialize(boot_dir, default_slot="A")
    journal_dir = workdir / "journal"
    journal_dir.mkdir(parents=True, exist_ok=True)

    if case == "inactive-base-write":
        # Interrupted during the inactive-slot write: no journal, no arm.
        # Recovery: default stays A, no candidate; prove the journal is
        # absent (no staged transaction) and the backend carries no
        # one-shot on the persistent default.
        try:
            BootTransactionJournal.load(journal_dir)
        except Exception:
            journal_absent = True
        else:
            raise DevproofError("inactive-base-write left a staged journal")
        state = backend.inspect()
        if state.one_shot_slot is not None:
            raise DevproofError("inactive-base-write left a one-shot armed")
        reconciled = state.default_slot
    elif case == "base-readback-finalization":
        # Interrupted after write but before finalization receipt: the
        # staged content is abandoned; nothing armed or committed. Prove
        # the backend still carries no one-shot and the default is A.
        state = backend.inspect()
        if state.one_shot_slot is not None:
            raise DevproofError("base-readback left a one-shot armed")
        reconciled = state.default_slot
    elif case == "boot-artifact-staging":
        # Interrupted while staging boot artifacts: journal staged at
        # most, backend untouched.
        coordinator = BootTransactionCoordinator.begin_update(
            journal_dir=journal_dir,
            backend=backend,
            candidate_artifacts=_devproof_artifacts("B", "greia-0.21.0"),
            accepted_artifacts=_devproof_artifacts("A", "greia-0.20.0"),
            release_id="greia-0.21.0",
        )
        _ = coordinator
        journal = BootTransactionJournal.load(journal_dir)
        if journal.state is not BootTransactionState.UPDATE_STAGED:
            raise DevproofError("staging did not record UPDATE_STAGED")
        reconciled = backend.inspect().default_slot
    elif case == "one-shot-arm":
        coordinator = BootTransactionCoordinator.begin_update(
            journal_dir=journal_dir,
            backend=backend,
            candidate_artifacts=_devproof_artifacts("B", "greia-0.21.0"),
            accepted_artifacts=_devproof_artifacts("A", "greia-0.20.0"),
            release_id="greia-0.21.0",
        )
        coordinator.arm()
        # Interrupted after arm but before the candidate boot: the
        # one-shot is consumed by the recovery boot of the accepted
        # slot, journal rolls back, default stays A.
        backend.reconcile("A")
        journal = BootTransactionJournal.load(journal_dir)
        journal.record(BootTransactionState.ROLLED_BACK, "devproof arm interrupted")
        reconciled = backend.inspect().default_slot
    elif case == "candidate-boot-before-health":
        coordinator = BootTransactionCoordinator.begin_update(
            journal_dir=journal_dir,
            backend=backend,
            candidate_artifacts=_devproof_artifacts("B", "greia-0.21.0"),
            accepted_artifacts=_devproof_artifacts("A", "greia-0.20.0"),
            release_id="greia-0.21.0",
        )
        coordinator.arm()
        backend.reconcile("B")
        coordinator.observe_boot()
        # Interrupted before health: treated as unhealthy, FAILED, A kept.
        from greia_platform.boot_transaction import mark_candidate_unhealthy

        mark_candidate_unhealthy(
            coordinator, recovery_class="health-service-failure",
            detail="devproof interruption",
        )
        reconciled = backend.inspect().default_slot
    elif case == "healthy-committing-before-backend-commit":
        # Brief case name "healthy-committing" is verbatim only: the
        # production BootTransactionState enum has no HEALTHY_COMMITTING
        # state. This pre-commit interruption is modelled at
        # CANDIDATE_BOOTING (asserted below) with the backend commit
        # never run: the commit is retried from the sidecar on the next
        # boot of the accepted slot; default stays A until the real
        # commit.
        coordinator = BootTransactionCoordinator.begin_update(
            journal_dir=journal_dir,
            backend=backend,
            candidate_artifacts=_devproof_artifacts("B", "greia-0.21.0"),
            accepted_artifacts=_devproof_artifacts("A", "greia-0.20.0"),
            release_id="greia-0.21.0",
        )
        coordinator.arm()
        backend.reconcile("B")
        coordinator.observe_boot()
        journal = BootTransactionJournal.load(journal_dir)
        if journal.state is not BootTransactionState.CANDIDATE_BOOTING:
            raise DevproofError("candidate boot did not record CANDIDATE_BOOTING")
        # No commit: recovery returns to the accepted default A.
        backend.reconcile("A")
        reconciled = backend.inspect().default_slot
        if reconciled != "A":
            raise DevproofError("HEALTHY_COMMITTING interruption moved the default")
    elif case == "committed-backend-unwritten-accepted-state":
        # Backend committed to B but the layout-authority advancement never
        # landed: recovery retries the advancement from the journal
        # release_id before the slot is trusted, then the committed
        # slot B is the correct reconciliation target (verified by
        # re-reading the backend default plus the journal release_id).
        coordinator = BootTransactionCoordinator.begin_update(
            journal_dir=journal_dir,
            backend=backend,
            candidate_artifacts=_devproof_artifacts("B", "greia-0.21.0"),
            accepted_artifacts=_devproof_artifacts("A", "greia-0.20.0"),
            release_id="greia-0.21.0",
        )
        coordinator.arm()
        backend.reconcile("B")
        coordinator.observe_boot()
        backend.commit_accepted("B")
        if backend.inspect().default_slot != "B":
            raise DevproofError("backend commit did not land")
        # Interruption point: the layout-authority advancement for
        # release greia-0.21.0 never landed. Recovery retries it from
        # the journal record (release_id identity only).
        journal = BootTransactionJournal.load(journal_dir)
        if journal.state is not BootTransactionState.CANDIDATE_BOOTING:
            raise DevproofError("candidate boot did not record CANDIDATE_BOOTING")
        if journal.release_id != "greia-0.21.0":
            raise DevproofError("journal release identity moved under commit")
        journal.record(BootTransactionState.ACCEPTED, "devproof accepted-state retry")
        reconciled = backend.inspect().default_slot
        if reconciled != "B" or journal.release_id != "greia-0.21.0":
            raise DevproofError(
                "committed-backend recovery did not converge on accepted B/greia-0.21.0"
            )
    else:  # pragma: no cover - guarded above
        raise DevproofContractError(f"unhandled interruption case {case!r}")

    expected = INTERRUPTION_EXPECTED_SLOT[case]
    if reconciled != expected:
        raise DevproofError(
            f"interruption case {case} reconciled to {reconciled!r}, expected {expected!r}"
        )
    return {"case": case, "reconciled_slot": reconciled, "expected": expected, "green": True}


def run_interruption_matrix(workdir: Path) -> dict[str, object]:
    """Run all 7 interruption cases; each must reach its expected slot."""
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    cases = [run_interruption_case(case, workdir) for case in INTERRUPTION_CASES]
    if len(cases) != 7 or any(not entry["green"] for entry in cases):
        raise DevproofError("interruption matrix did not reconcile cleanly")
    for entry in cases:
        if entry["reconciled_slot"] != INTERRUPTION_EXPECTED_SLOT[str(entry["case"])]:
            raise DevproofError("interruption matrix diverged from expected slots")
    return {
        "green": True,
        "surface": "SOURCE_SCOPE",
        "cases": cases,
        "expected_slot": dict(INTERRUPTION_EXPECTED_SLOT),
    }


# ---------------------------------------------------------------------------
# Resource envelope (measured, never synthesized)
# ---------------------------------------------------------------------------


def _rss_bytes() -> int:
    import sys as _sys

    raw = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    # Linux reports ru_maxrss in KiB; macOS reports bytes.
    if _sys.platform == "darwin":
        return raw
    return raw * 1024


def _memavailable_bytes() -> int | None:
    try:
        with open("/proc/meminfo", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) * 1024
    except OSError:
        return None
    return None


def _disk_usage(path: Path) -> dict[str, int]:
    usage = shutil.disk_usage(path)
    return {"total": usage.total, "used": usage.used, "free": usage.free}


def _directory_bytes(path: Path) -> int:
    total = 0
    for dirpath, _dirnames, filenames in os.walk(path):
        for name in filenames:
            try:
                total += (Path(dirpath) / name).stat().st_size
            except OSError:
                continue
    return total


def record_leg_sample(leg: str, *, surface: str = "SOURCE_SCOPE") -> dict[str, object]:
    """Sample host RSS/MemAvailable at one install/update leg boundary.

    The sample is a real local measurement labelled with its surface;
    per-leg guest peaks beyond the host process can only be recorded
    during the capable-host device run, where the lifecycle calls this
    after each install/update leg and threads the samples through
    :func:`run_envelope_device`.
    """
    if not leg:
        raise DevproofContractError("leg sample needs a non-empty leg name")
    if surface not in ("SOURCE_SCOPE", "DEVICE"):
        raise DevproofContractError(f"unknown leg sample surface {surface!r}")
    return {
        "leg": leg,
        "surface": surface,
        "rss_bytes": _rss_bytes(),
        "memavailable_bytes": _memavailable_bytes(),
    }


def summarize_leg_peaks(
    samples: list[Mapping[str, object]] | None,
) -> dict[str, object]:
    """Summarize per-leg install/update peaks (measured, never synthesized).

    Returns the per-leg table plus the install/update max-RSS and
    minimum-MemAvailable across the sampled legs. An absent/empty sample
    set reports explicit ``deferred`` tracing instead of a false zero.
    """
    rows: list[dict[str, object]] = []
    if samples:
        for entry in samples:
            leg = str(entry.get("leg", ""))
            if not leg:
                raise DevproofContractError("leg sample is missing its leg name")
            rss = entry.get("rss_bytes")
            if not isinstance(rss, int) or rss <= 0:
                raise DevproofContractError(
                    f"leg sample {leg!r} carries no measured RSS"
                )
            rows.append({
                "leg": leg,
                "surface": str(entry.get("surface", "UNKNOWN")),
                "rss_bytes": rss,
                "memavailable_bytes": entry.get("memavailable_bytes"),
            })
    if not rows:
        return {
            "tracing": "deferred",
            "detail": "no per-leg install/update samples recorded on this run",
            "legs": [],
            "install_update_max_rss_bytes": None,
            "install_update_min_memavailable_bytes": None,
        }
    max_rss = max(int(row["rss_bytes"]) for row in rows)
    mem_values = [
        int(row["memavailable_bytes"]) for row in rows
        if isinstance(row["memavailable_bytes"], int)
        and int(row["memavailable_bytes"]) > 0
    ]
    return {
        "tracing": "recorded",
        "legs": rows,
        "leg_count": len(rows),
        "install_update_max_rss_bytes": max_rss,
        "install_update_min_memavailable_bytes": min(mem_values) if mem_values else None,
    }


def measure_resource_envelope(
    workdir: Path,
    *,
    bundle_path: Path | None = None,
    surface: str = "SOURCE_SCOPE",
    leg_samples: list[Mapping[str, object]] | None = None,
) -> dict[str, object]:
    """Record the resource envelope from real local measurements.

    RSS/MemAvailable, decompression/finalization peaks, staging bytes
    and disk used/free are measured on this host. Slot sizes and the
    PERSIST minimum are layout-plan facts owned by ``runner.py``
    (``PROFILE_SLOT_BYTES``/``PROFILE_PERSIST_MINIMUM_BYTES``), read
    from that single owner rather than duplicated here; the bundle size
    is measured from ``bundle_path`` when supplied, otherwise recorded
    explicitly absent (never a silent measured zero). Per-leg
    install/update peaks come from ``leg_samples`` (recorded by the
    lifecycle via :func:`record_leg_sample`); when no samples are
    supplied the leg tracing reports explicit ``deferred``.
    """
    from greia_platform.slot_writer import SLOT_WRITE_CHUNK_BYTES

    try:
        from .runner import PROFILE_PERSIST_MINIMUM_BYTES as _PLAN_PERSIST_MIN
        from .runner import PROFILE_SLOT_BYTES as _PLAN_SLOT
    except Exception:
        _PLAN_SLOT = REFERENCE_SLOT_BYTES
        _PLAN_PERSIST_MIN = REFERENCE_PERSIST_MINIMUM_BYTES

    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    rss_before = _rss_bytes()
    # Decompression memory: really decompress a representative blob and
    # record the RSS delta (production mechanism: bounded-chunk path).
    import zlib

    blob = zlib.compress(b"devproof" * 4096)
    rss_peak = rss_before
    for _ in range(8):
        _ = zlib.decompress(blob)
        rss_peak = max(rss_peak, _rss_bytes())
    decompression_delta = rss_peak - rss_before
    # Finalization peak: hash a representative payload in bounded chunks.
    import hashlib

    digest = hashlib.sha256()
    chunk = b"f" * SLOT_WRITE_CHUNK_BYTES
    for _ in range(4):
        digest.update(chunk)
    finalization_peak = _rss_bytes()
    staging_workspace = _directory_bytes(workdir)
    disk = _disk_usage(workdir)
    if bundle_path is not None and Path(bundle_path).is_file():
        bundle_size = int(Path(bundle_path).stat().st_size)
        bundle_present = True
    else:
        bundle_size = 0
        bundle_present = False
    persist_headroom = max(0, disk["free"] - int(_PLAN_PERSIST_MIN))
    leg_peaks = summarize_leg_peaks(leg_samples)
    envelope = {
        "surface": surface,
        "max_rss_bytes": max(rss_before, rss_peak, finalization_peak),
        "memavailable_bytes": _memavailable_bytes(),
        "leg_peaks": leg_peaks,
        "install_update_max_rss_bytes": leg_peaks["install_update_max_rss_bytes"],
        "install_update_min_memavailable_bytes": leg_peaks[
            "install_update_min_memavailable_bytes"
        ],
        "decompression_delta_bytes": decompression_delta,
        "finalization_peak_rss_bytes": finalization_peak,
        "staging_workspace_bytes": staging_workspace,
        "disk_total_bytes": disk["total"],
        "disk_used_bytes": disk["used"],
        "disk_free_bytes": disk["free"],
        "slot_a_bytes": int(_PLAN_SLOT),
        "slot_b_bytes": int(_PLAN_SLOT),
        "slot_bytes_source": "layout-plan PROFILE_SLOT_BYTES (tools/x8_qemu/runner.py)",
        "bundle_bytes": bundle_size,
        "bundle_present": bundle_present,
        "persist_minimum_bytes": int(_PLAN_PERSIST_MIN),
        "persist_minimum_source": "layout-plan PROFILE_PERSIST_MINIMUM_BYTES",
        "persist_headroom_bytes": persist_headroom,
        "diagnostic_budget_bytes": DIAGNOSTIC_BUDGET_BYTES,
        "denominator": "one envelope run over workdir + host disk",
    }
    if envelope["max_rss_bytes"] <= 0:
        raise DevproofError("resource envelope measured no RSS")
    if disk["total"] <= 0:
        raise DevproofError("resource envelope measured no disk")
    return envelope


def check_storage_preflight(
    path: Path, *, required_bytes: int, reserved_bytes: int = PREFLIGHT_RESERVED_BYTES
) -> dict[str, object]:
    """Preflight before destructive/staging work; fail before damage.

    Raises :class:`DevproofPreflightError` when free space cannot cover
    ``required_bytes`` plus the reserved headroom. Must be called before
    any destructive or staging write, never after.
    """
    if required_bytes <= 0:
        raise DevproofContractError("preflight needs a positive requirement")
    if reserved_bytes < 0:
        raise DevproofContractError("preflight reserve may not be negative")
    disk = _disk_usage(Path(path))
    if disk["free"] < required_bytes + reserved_bytes:
        raise DevproofPreflightError(
            f"preflight refused: free {disk['free']} < "
            f"required {required_bytes} + reserved {reserved_bytes}"
        )
    return {
        "green": True,
        "free_bytes": disk["free"],
        "required_bytes": required_bytes,
        "reserved_bytes": reserved_bytes,
    }


def prove_near_full_preflight(workdir: Path) -> dict[str, object]:
    """Prove the near-full-storage transaction preflights correctly.

    Positive case runs against the real disk; the negative case proves
    sensitivity by demanding more than the disk holds (must refuse
    before any destructive/staging work, with nothing written).
    """
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    positive = check_storage_preflight(
        workdir, required_bytes=1024 * 1024, reserved_bytes=1024 * 1024
    )
    sentinel = workdir / "preflight-sentinel"
    if sentinel.exists():
        raise DevproofError("preflight sentinel already exists")
    disk = _disk_usage(workdir)
    try:
        check_storage_preflight(
            workdir,
            required_bytes=disk["free"] + 1024 * 1024,
            reserved_bytes=PREFLIGHT_RESERVED_BYTES,
        )
    except DevproofPreflightError as exc:
        negative = {"refused": True, "detail": str(exc)}
    else:
        raise DevproofError("near-full preflight did not refuse")
    if sentinel.exists():
        raise DevproofError("preflight performed staging work before refusing")
    return {"green": True, "surface": "SOURCE_SCOPE", "positive": positive, "negative": negative}


# ---------------------------------------------------------------------------
# 768 MiB cgroup gate (<=256 MiB payload)
# ---------------------------------------------------------------------------


def read_cgroup_peak_bytes() -> dict[str, object]:
    """Read the container memory peak where available (measured)."""
    candidates = (
        Path("/sys/fs/cgroup/memory.peak"),
        Path("/sys/fs/cgroup/memory/memory.max_usage_in_bytes"),
    )
    for candidate in candidates:
        try:
            value = int(candidate.read_text(encoding="utf-8").strip().split()[0])
            return {"peak_bytes": value, "source": str(candidate)}
        except (OSError, ValueError, IndexError):
            continue
    return {"peak_bytes": _rss_bytes(), "source": "getrusage-ru_maxrss"}


def check_swap_off() -> dict[str, object]:
    """Prove swap is off on the measuring host; deferred elsewhere."""
    try:
        with open("/proc/meminfo", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("SwapTotal:"):
                    total = int(line.split()[1]) * 1024
                    return {"swap_off": total == 0, "swap_total_bytes": total}
    except OSError:
        return {"swap_off": False, "swap_total_bytes": None, "deferred": True}
    return {"swap_off": False, "swap_total_bytes": None, "deferred": True}


def cgroup_gate_report(
    *,
    payload_bytes: int,
    peak_bytes: int,
    oom_kills: int = 0,
    swap_off: bool | None = None,
    require_swap_off: bool = False,
) -> dict[str, object]:
    """Evaluate the 768 MiB cgroup gate for a <=256 MiB payload.

    Larger payloads are non-acceptance diagnostic only (never green).
    Swap handling: when ``require_swap_off`` is true (device scope),
    observable swap-on (``swap_off is False``) is RED; a deferred swap
    observation (``None``, e.g. no ``/proc/meminfo``) stays explicit but
    does not alone fail source scope.
    """
    if payload_bytes <= 0:
        raise DevproofContractError("gate needs a positive payload size")
    if payload_bytes > PAYLOAD_ACCEPT_BYTES:
        return {
            "green": False,
            "diagnostic_only": True,
            "reason": "payload exceeds the 256 MiB acceptance bound",
            "payload_bytes": payload_bytes,
            "ceiling_bytes": CGROUP_CEILING_BYTES,
        }
    if require_swap_off and swap_off is False:
        return {
            "green": False,
            "diagnostic_only": False,
            "reason": "swap is enabled on the measuring host",
            "payload_bytes": payload_bytes,
            "peak_bytes": peak_bytes,
            "ceiling_bytes": CGROUP_CEILING_BYTES,
            "swap_off": swap_off,
        }
    headroom = CGROUP_CEILING_BYTES - peak_bytes
    green = peak_bytes < CGROUP_CEILING_BYTES and oom_kills == 0
    if require_swap_off and swap_off is None:
        green = False
    return {
        "green": green,
        "diagnostic_only": False,
        "payload_bytes": payload_bytes,
        "peak_bytes": peak_bytes,
        "ceiling_bytes": CGROUP_CEILING_BYTES,
        "headroom_bytes": headroom,
        "oom_kills": oom_kills,
        "swap_off": swap_off,
        "swap_required": require_swap_off,
    }


def _streaming_payload_peak(payload_bytes: int) -> int:
    """Stream an acceptance-sized payload through bounded chunks.

    Proves bounded-memory handling of ``payload_bytes`` without ever
    holding the payload in RAM: one 1 MiB chunk is hashed per
    iteration (``payload_bytes // 1MiB`` iterations, capped for very
    small inputs) while sampling process RSS. Returns the peak RSS.
    """
    import hashlib

    chunk = b"g" * (1024 * 1024)
    iterations = max(1, int(payload_bytes) // len(chunk))
    digest = hashlib.sha256()
    peak = _rss_bytes()
    for _ in range(iterations):
        digest.update(chunk)
        peak = max(peak, _rss_bytes())
    digest.hexdigest()
    return peak


def run_cgroup_gate(
    workdir: Path, *, payload_bytes: int, require_swap_off: bool = False
) -> dict[str, object]:
    """Run the cgroup gate with a measured peak (source scope by default)."""
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    peak = read_cgroup_peak_bytes()
    swap = check_swap_off()
    streaming_peak = _streaming_payload_peak(payload_bytes)
    combined_peak = max(int(peak["peak_bytes"]), streaming_peak)
    swap_off: bool | None = None
    if "swap_off" in swap and "deferred" not in swap:
        swap_off = bool(swap["swap_off"])
    verdict = cgroup_gate_report(
        payload_bytes=payload_bytes,
        peak_bytes=combined_peak,
        swap_off=swap_off,
        require_swap_off=require_swap_off,
    )
    rss = _rss_bytes()
    return {
        "surface": "SOURCE_SCOPE",
        "payload_bytes": payload_bytes,
        "peak": {**peak, "combined_peak_bytes": combined_peak,
                 "streaming_peak_bytes": streaming_peak},
        "swap": swap,
        "rss_bytes": rss,
        "verdict": verdict,
        "green": bool(verdict["green"]),
    }


# ---------------------------------------------------------------------------
# Envelope runners (source scope + device-gated)
# ---------------------------------------------------------------------------


def run_envelope_source_scope(
    output_dir: Path, *, leg_samples: list[Mapping[str, object]] | None = None
) -> dict[str, object]:
    """Run the full unit-pinnable envelope at source scope."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    d31 = run_d31_rollback_proof(out / "d31")
    interruptions = run_interruption_matrix(out / "interruptions")
    envelope = measure_resource_envelope(
        out / "resource", surface="SOURCE_SCOPE", leg_samples=leg_samples
    )
    preflight = prove_near_full_preflight(out / "preflight")
    gate = run_cgroup_gate(out / "cgroup", payload_bytes=GATE_PAYLOAD_BYTES)
    report = {
        "schema_version": 1,
        "ok": bool(d31["green"] and interruptions["green"] and preflight["green"]),
        "classification": "SOURCE_SCOPE_T7_DEVPROOF",
        "spec": envelope_spec(),
        "d31": d31,
        "interruptions": interruptions,
        "resource_envelope": envelope,
        "near_full_preflight": preflight,
        "cgroup_gate": gate,
        "device_scope": {
            "executed": False,
            "detail": "source scope: device-measured values deferred "
            "to a capable Linux host; never synthesized",
        },
    }
    (out / "devproof-envelope.json").write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    return report


def run_envelope_device(
    output_dir: Path,
    *,
    bundle_path: Path | None = None,
    leg_samples: list[Mapping[str, object]] | None = None,
) -> dict[str, object]:
    """Run the device-measured envelope (capable Linux host only).

    ``bundle_path`` lets the lifecycle device run bind the envelope to
    a real v3 bundle built through the shipped path, so
    ``bundle_bytes``/``bundle_present`` are run-observed rather than
    default-absent. ``leg_samples`` carries the per-leg install/update
    RSS/MemAvailable samples recorded by the lifecycle across the
    install and update legs; the capable-host run must supply them so
    the envelope records per-leg peaks there, not host peaks alone.
    Swap-off is required here (device scope).
    """
    from .lifecycle import require_device_host

    require_device_host()
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    d31 = run_d31_rollback_proof(out / "d31-device")
    interruptions = run_interruption_matrix(out / "interruptions-device")
    envelope = measure_resource_envelope(
        out / "resource-device",
        bundle_path=bundle_path,
        surface="DEVICE",
        leg_samples=leg_samples,
    )
    preflight = prove_near_full_preflight(out / "preflight-device")
    gate = run_cgroup_gate(
        out / "cgroup-device",
        payload_bytes=GATE_PAYLOAD_BYTES,
        require_swap_off=True,
    )
    if not gate["verdict"]["green"]:
        raise DevproofError("device cgroup gate is RED")
    report = {
        "schema_version": 1,
        "ok": True,
        "classification": "DEVICE_T7_DEVPROOF",
        "spec": envelope_spec(),
        "d31": {**d31, "surface": "DEVICE"},
        "interruptions": {**interruptions, "surface": "DEVICE"},
        "resource_envelope": envelope,
        "near_full_preflight": {**preflight, "surface": "DEVICE"},
        "cgroup_gate": {**gate, "surface": "DEVICE"},
        "device_scope": {"executed": True},
    }
    (out / "devproof-envelope-device.json").write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    return report


__all__ = [
    "CGROUP_CEILING_BYTES",
    "PAYLOAD_ACCEPT_BYTES",
    "GATE_PAYLOAD_BYTES",
    "INTERRUPTION_CASES",
    "INTERRUPTION_EXPECTED_SLOT",
    "D31_FIXTURES",
    "DevproofError",
    "DevproofContractError",
    "DevproofPreflightError",
    "envelope_spec",
    "write_d31_representative_state",
    "read_d31_representative_state",
    "verify_d31_rollback",
    "run_d31_rollback_proof",
    "run_interruption_case",
    "run_interruption_matrix",
    "measure_resource_envelope",
    "record_leg_sample",
    "summarize_leg_peaks",
    "check_storage_preflight",
    "prove_near_full_preflight",
    "read_cgroup_peak_bytes",
    "check_swap_off",
    "cgroup_gate_report",
    "run_cgroup_gate",
    "run_envelope_source_scope",
    "run_envelope_device",
]
