"""Trusted launcher seam for the post-intro BOOT_HEALTHY protocol.

This module is the single holder of the trusted launcher bootstrap path
identifier. Only code presenting this exact peer path can complete a
``BOOT_HEALTHY`` confirmation; Parent panels, Activity runtimes and any
same-UID child presenting their own path fail closed even when they share
the child OS identity. The seam never changes intro timing: it only reads
the :class:`BootLifecycleGuard` state and the launcher's own intro flags
and translates them into platform :class:`IntroEvidence`.

Call order on a candidate boot (after ``observe_boot`` reached
``CANDIDATE_BOOTING`` and the 7-second intro completed)::

    record = provision_post_intro_credential(protocol, guard=guard, ...)
    ticket = confirm_post_intro_healthy(protocol, guard=guard, token=...,
                                        first_frame_visible=True,
                                        intro_completed=True, ...)
    outcome = protocol.finalize(ticket)

or, at the real ``INTERACTIVE_READY`` transition, the single
:func:`run_post_intro_acceptance` call below (confirm + finalize).

First-frame systemd readiness (the first-visible-flip signal owned by
:mod:`greia_launcher.boot_intro` for PID 1 process liveness) never implies
update health: this
seam additionally requires the full intro completion flag and
``INTERACTIVE_READY``, and the platform revalidates actual slot/release
identity itself on both phases.
"""

from __future__ import annotations

import os
from pathlib import Path

from greia_platform.boot_health import (
    BootHealthCredentialRecord,
    BootHealthCredentialVault,
    BootHealthyProtocol,
    BootHealthError,
    BootHealthOutcome,
    HealthyCommittingTicket,
    IntroEvidence,
    ProductionActualBootObserver,
    systemd_vault_dir,
)

from .bootstrap import BootLifecycleGuard, BootLifecycleState

#: Stable identifier of the trusted launcher bootstrap path. Presented as
#: the peer on every provision/confirm call; the platform vault binds it
#: into the one-use credential, so no other path can use the token.
TRUSTED_BOOTSTRAP_PATH = "greia_launcher.bootstrap:LauncherBootstrap"


def trusted_bootstrap_path() -> str:
    """Return the single peer path authorized for BOOT_HEALTHY."""
    return TRUSTED_BOOTSTRAP_PATH


def default_vault(explicit_dir: Path | None = None) -> BootHealthCredentialVault:
    """Resolve the credential vault: explicit dir, else systemd credentials."""
    if explicit_dir is not None:
        return BootHealthCredentialVault(Path(explicit_dir))
    systemd_dir = systemd_vault_dir()
    if systemd_dir is None:
        raise BootHealthError(
            "no BOOT_HEALTHY vault: pass an explicit run directory or run "
            "under a systemd unit with LoadCredential="
        )
    return BootHealthCredentialVault(systemd_dir)


def build_protocol(
    *,
    coordinator: object,
    candidate_root_partuuid: str,
    candidate_release_id: str,
    candidate_release_sequence: int,
    vault: BootHealthCredentialVault,
    observer: object,
) -> BootHealthyProtocol:
    """Bind a BOOT_HEALTHY protocol to the trusted bootstrap path."""
    return BootHealthyProtocol(
        coordinator=coordinator,
        candidate_root_partuuid=candidate_root_partuuid,
        candidate_release_id=candidate_release_id,
        candidate_release_sequence=candidate_release_sequence,
        vault=vault,
        observer=observer,  # type: ignore[arg-type]
        trusted_bootstrap_path=TRUSTED_BOOTSTRAP_PATH,
    )


def provision_post_intro_credential(
    protocol: BootHealthyProtocol,
    *,
    guard: BootLifecycleGuard,
    boot_attempt: str,
) -> BootHealthCredentialRecord:
    """Provision the one-use credential from the trusted bootstrap path."""
    _require_guard_type(guard)
    return protocol.provision_for_boot_attempt(
        boot_attempt=boot_attempt, peer_uid=os.getuid()
    )


def confirm_post_intro_healthy(
    protocol: BootHealthyProtocol,
    *,
    guard: BootLifecycleGuard,
    token: str,
    boot_attempt: str,
    first_frame_visible: bool,
    intro_completed: bool,
    untrusted_activity_launched: bool,
) -> HealthyCommittingTicket:
    """Confirm BOOT_HEALTHY from the trusted bootstrap path.

    Refuses locally unless the guard already reports ``INTERACTIVE_READY``
    (defense in depth: the platform re-checks the same evidence), then
    delegates to the platform two-phase protocol with the trusted peer path.
    """
    _require_guard_type(guard)
    if guard.state is not BootLifecycleState.INTERACTIVE_READY:
        raise BootHealthError(
            "trusted BOOT_HEALTHY confirmation requires INTERACTIVE_READY; "
            f"guard reports {guard.state.value}"
        )
    return protocol.confirm(
        token=token,
        boot_attempt=boot_attempt,
        peer_bootstrap_path=TRUSTED_BOOTSTRAP_PATH,
        peer_uid=os.getuid(),
        intro=IntroEvidence(
            first_frame_visible=first_frame_visible,
            intro_completed=intro_completed,
            lifecycle_state=guard.state.value,
            untrusted_activity_launched=untrusted_activity_launched,
        ),
    )


def run_post_intro_acceptance(
    protocol: BootHealthyProtocol,
    *,
    guard: BootLifecycleGuard,
    boot_attempt: str,
    token: str,
    first_frame_visible: bool,
    intro_completed: bool,
    untrusted_activity_launched: bool = False,
) -> BootHealthOutcome:
    """Complete BOOT_HEALTHY acceptance at the real lifecycle transition.

    The launcher calls this exactly once when the prepared state is
    published into ``INTERACTIVE_READY`` after the full 7-second intro on
    a candidate boot: confirmation consumes the one-use credential bound
    to this boot attempt, finalization re-observes identity and commits
    through the boot journal, opening the untrusted-launch gate. First
    install uses the same predicate (outcome carries ``first_install`` and
    the ``setup-medium`` recovery medium; never "rollback").

    First-frame systemd readiness (``READY=1``) alone never reaches this
    call: the guard must already report ``INTERACTIVE_READY`` and the
    platform re-checks the completed intro, the actual slot/release
    identity and the trusted bootstrap path on both phases.
    """
    ticket = confirm_post_intro_healthy(
        protocol,
        guard=guard,
        token=token,
        boot_attempt=boot_attempt,
        first_frame_visible=first_frame_visible,
        intro_completed=intro_completed,
        untrusted_activity_launched=untrusted_activity_launched,
    )
    return protocol.finalize(ticket)


def _require_guard_type(guard: object) -> BootLifecycleGuard:
    if not isinstance(guard, BootLifecycleGuard):
        raise BootHealthError("BOOT_HEALTHY seam requires the launcher boot guard")
    return guard


# ---------------------------------------------------------------------------
# Production post-intro acceptance at the INTERACTIVE_READY transition
# ---------------------------------------------------------------------------

#: First-install boot journal directory (image-integration parameter: the
#: installer device seam owns the on-device path; T6-HARNESS2/T7-LIFE2 own
#: its device execution. Tests point it at a disposable directory).
PRODUCTION_BOOT_JOURNAL_ENV = "GREIA_BOOT_JOURNAL_DIR"
PRODUCTION_BOOT_JOURNAL_DEFAULT = "/var/lib/greia-os/boot-journal"

#: Slot-local finalization receipt visible on the running system
#: (``etc/greia-os/finalization-receipt.json`` in the booted slot, hence
#: ``/etc/greia-os/finalization-receipt.json`` on device). Carries the
#: boot-artifact digests the coordinator binds to the candidate slot.
PRODUCTION_FINALIZATION_RECEIPT_ENV = "GREIA_FINALIZATION_RECEIPT_PATH"
PRODUCTION_FINALIZATION_RECEIPT_DEFAULT = "/etc/greia-os/finalization-receipt.json"


def production_boot_journal_dir() -> Path:
    """Resolve the first-install boot journal directory (env or system bind)."""
    override = os.environ.get(PRODUCTION_BOOT_JOURNAL_ENV, "").strip()
    return Path(override) if override else Path(PRODUCTION_BOOT_JOURNAL_DEFAULT)


def production_update_journal_dir() -> Path:
    """Resolve the system-update boot journal directory (env or system bind).

    Mirrors the privileged update composition root
    (``greia_platform.system_updates`` state dir + ``system-updates/journal``)
    so the launcher observes the same journal the update backend staged.
    """
    from greia_platform.system_updates import (
        UPDATE_JOURNAL_DIR_NAME,
        UPDATE_STATE_DIR_DEFAULT,
        UPDATE_STATE_DIR_ENV,
    )

    raw = os.environ.get(UPDATE_STATE_DIR_ENV, "").strip()
    state_dir = Path(raw) if raw else Path(UPDATE_STATE_DIR_DEFAULT)
    return state_dir / "system-updates" / UPDATE_JOURNAL_DIR_NAME


def production_finalization_receipt_path() -> Path:
    """Resolve the booted-slot finalization receipt path (env or system bind)."""
    override = os.environ.get(PRODUCTION_FINALIZATION_RECEIPT_ENV, "").strip()
    return Path(override) if override else Path(PRODUCTION_FINALIZATION_RECEIPT_DEFAULT)


def _load_non_terminal_journal(journal_dir: Path):  # type: ignore[no-untyped-def]
    """Return the journal at ``journal_dir``, or None when absent/terminal.

    Read-only: loading never writes. A corrupt journal raises
    :class:`BootHealthError` (fail-closed, observable); a missing journal
    file is the normal plain-boot case and returns None.
    """
    from greia_platform.boot_transaction import (
        JOURNAL_FILE_NAME,
        BootJournalError,
        BootTransactionJournal,
    )

    candidate = Path(journal_dir) / JOURNAL_FILE_NAME
    if candidate.is_symlink():
        raise BootHealthError("boot journal must not be a symlink")
    if not candidate.is_file():
        return None
    try:
        journal = BootTransactionJournal.load(Path(journal_dir))
    except BootJournalError as exc:
        raise BootHealthError(f"boot journal is not authoritative: {exc}") from exc
    except OSError as exc:
        raise BootHealthError(f"boot journal is unreadable: {exc}") from exc
    if journal.is_terminal:
        return None
    return journal


def _read_production_receipt(path: Path) -> dict[str, object]:
    """Return the validated finalization receipt record for the booted slot."""
    import json as _json

    if path.is_symlink():
        raise BootHealthError("finalization receipt must not be a symlink")
    try:
        raw_bytes = path.read_bytes()
    except OSError as exc:
        raise BootHealthError(f"finalization receipt is unreadable: {exc}") from exc
    if len(raw_bytes) > 32 * 1024:
        raise BootHealthError("finalization receipt exceeds Greia bounds")
    try:
        raw = _json.loads(raw_bytes.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise BootHealthError(f"finalization receipt is not valid JSON: {exc}") from exc
    if not isinstance(raw, dict):
        raise BootHealthError("finalization receipt must be a JSON object")
    digests = raw.get("artifact_digests")
    if not isinstance(digests, dict):
        raise BootHealthError("finalization receipt carries no artifact digests")
    for key in ("generic_kernel_sha256", "host_initramfs_sha256"):
        value = digests.get(key)
        if not isinstance(value, str) or len(value) != 64 or any(
            char not in "0123456789abcdef" for char in value
        ):
            raise BootHealthError(
                f"finalization receipt digest {key} is not authoritative"
            )
    for key in ("release_id", "release_sequence", "slot", "layout_id"):
        if raw.get(key) is None:
            raise BootHealthError(
                f"finalization receipt is missing authoritative field {key}"
            )
    return raw


def maybe_accept_production_boot(
    guard: BootLifecycleGuard,
) -> BootHealthOutcome | None:
    """Run production BOOT_HEALTHY acceptance once, or bounded no-op.

    Called exactly once from ``LauncherApplication.apply_prepared_state``
    after ``mark_interactive_ready()``. On a candidate/first-install boot
    with a pending journal whose candidate observably booted, this
    provisions the one-use credential from the production systemd vault,
    confirms through :func:`run_post_intro_acceptance` with the production
    observer, and finalizes through the boot journal, returning the outcome.

    Outside candidate/first-install boots it is a bounded no-op returning
    None: missing vault/journal/backend/layout/observation, a terminal
    journal, or a machine running the accepted slot (failed candidate)
    writes nothing — no vault, journal, grubenv or health-state mutation.
    Journal reconcile of a failed candidate stays owned by the privileged
    update/install service, never by the launcher. Unexpected evidence
    failures on a pending candidate boot raise :class:`BootHealthError`
    instead of silently skipping acceptance.

    Intro evidence is the transition itself: reaching ``INTERACTIVE_READY``
    is the intro-end boundary, so first frame and intro completion are
    reported True and no untrusted Activity has launched yet (the
    supervisor is composed but has issued nothing).
    """
    _require_guard_type(guard)
    if guard.state is not BootLifecycleState.INTERACTIVE_READY:
        raise BootHealthError(
            "production BOOT_HEALTHY acceptance requires INTERACTIVE_READY; "
            f"guard reports {guard.state.value}"
        )
    # Plain-boot fast path: without a systemd credential vault there is no
    # provisionable credential, so no acceptance can exist. No mutation.
    try:
        vault = default_vault()
    except BootHealthError:
        return None
    observer = ProductionActualBootObserver()
    candidates: list[tuple[Path, object, bool]] = []
    update_journal_dir = production_update_journal_dir()
    for journal_dir, is_update in (
        (update_journal_dir, True),
        (production_boot_journal_dir(), False),
    ):
        journal = _load_non_terminal_journal(journal_dir)
        if journal is not None:
            candidates.append((Path(journal_dir), journal, is_update))
    if not candidates:
        return None
    if len(candidates) > 1:
        raise BootHealthError(
            "ambiguous boot authority: update and first-install journals "
            "are both pending; refusing to guess"
        )
    journal_dir, journal, is_update = candidates[0]
    return _accept_pending_journal(
        guard=guard, journal_dir=journal_dir, journal=journal,
        vault=vault, observer=observer, advance_layout=is_update,
    )


def _accept_pending_journal(  # type: ignore[no-untyped-def]
    *, guard: BootLifecycleGuard, journal_dir: Path, journal: object,
    vault: BootHealthCredentialVault, observer: ProductionActualBootObserver,
    advance_layout: bool,
) -> BootHealthOutcome | None:
    """Accept one pending journal whose candidate observably booted, else None."""
    from greia_platform.boot_transaction import (
        BootTransactionCoordinator,
        BootTransactionError,
    )
    from greia_platform.grub_ab import GrubAbConfigError
    from greia_platform.system_updates import (
        UpdateLayoutError,
        load_installed_layout_record,
        resolve_grubenv_dir,
    )

    try:
        from greia_platform.grub_ab import GrubEnvBackend
    except ImportError as exc:  # pragma: no cover - platform seam always present
        raise BootHealthError(f"boot backend is unavailable: {exc}") from exc
    try:
        backend = GrubEnvBackend.attach(resolve_grubenv_dir())
    except (BootTransactionError, GrubAbConfigError, OSError, ValueError):
        return None
    try:
        record = load_installed_layout_record()
    except UpdateLayoutError:
        return None
    if record is None or record.system_b is None:
        return None
    try:
        observed = backend.observe_booted_slot()
    except (BootTransactionError, OSError):
        return None
    if observed != journal.candidate_slot:
        # Failed candidate or pre-reboot staging: the launcher records
        # nothing; reconcile stays owned by the privileged service.
        return None
    candidate_artifacts, accepted_artifacts = _production_artifact_sets(
        journal=journal, record=record,
    )
    try:
        coordinator = BootTransactionCoordinator.resume(
            journal_dir=journal_dir,
            backend=backend,
            candidate_artifacts=candidate_artifacts,
            accepted_artifacts=accepted_artifacts,
        )
    except BootTransactionError as exc:
        raise BootHealthError(
            f"production boot coordinator refused: {exc}"
        ) from exc
    # Fold the authoritative observation (records CANDIDATE_BOOTING on a
    # pending candidate; no-op when already candidate-booting).
    try:
        coordinator.observe_boot()
    except BootTransactionError as exc:
        raise BootHealthError(
            f"production boot observation refused: {exc}"
        ) from exc
    protocol = build_protocol(
        coordinator=coordinator,
        candidate_root_partuuid=_slot_root_partuuid(record, journal.candidate_slot),
        candidate_release_id=journal.release_id,
        candidate_release_sequence=journal.release_sequence,
        vault=vault,
        observer=observer,
    )
    boot_attempt = str(journal.transaction_id)
    record_credential = protocol.provision_for_boot_attempt(
        boot_attempt=boot_attempt, peer_uid=os.getuid(),
    )
    outcome = run_post_intro_acceptance(
        protocol,
        guard=guard,
        boot_attempt=boot_attempt,
        token=record_credential.token,
        first_frame_visible=True,
        intro_completed=True,
        untrusted_activity_launched=False,
    )
    if advance_layout and not journal.first_install:
        _advance_update_layout_authority(journal=journal)
    return outcome


def _advance_update_layout_authority(journal: object) -> None:  # type: ignore[no-untyped-def]
    """Mirror the update backend's health-commit advancement after acceptance.

    Reuses :func:`greia_platform.system_updates.advance_layout_authority_for_acceptance`
    (no parallel mechanism): the trusted layout record follows the committed
    journal so the next sequenced update resolves the other inactive slot,
    and the accepted-sequence file follows the accepted release. Both are
    idempotent, so a later privileged-service confirm of the same terminal
    journal converges instead of conflicting.
    """
    from greia_platform.system_updates import (
        SystemUpdateError,
        advance_layout_authority_for_acceptance,
        installed_layout_record_path,
        write_accepted_sequence,
    )

    try:
        advance_layout_authority_for_acceptance(
            installed_layout_record_path(),
            candidate_slot=str(journal.candidate_slot),
            accepted_slot=str(journal.accepted_slot),
            release_id=str(journal.release_id),
            release_sequence=int(journal.release_sequence),
        )
        write_accepted_sequence(
            production_update_journal_dir().parent.parent,
            int(journal.release_sequence),
        )
    except SystemUpdateError as exc:
        raise BootHealthError(
            f"update layout advancement refused after acceptance: {exc}"
        ) from exc


def _slot_root_partuuid(record: object, slot: str) -> str:
    """Return the layout-authoritative root PARTUUID for ``slot``."""
    if slot == "A":
        return str(record.system_a.partuuid)  # type: ignore[union-attr]
    return str(record.system_b.partuuid)  # type: ignore[union-attr]


def _slot_filesystem_uuid(record: object, slot: str) -> str:
    """Return the layout-authoritative filesystem UUID for ``slot``."""
    if slot == "A":
        return str(record.system_a.filesystem_uuid)  # type: ignore[union-attr]
    return str(record.system_b.filesystem_uuid)  # type: ignore[union-attr]


def _production_artifact_sets(journal: object, record: object):  # type: ignore[no-untyped-def]
    """Build candidate/accepted artifact sets from layout + booted receipt.

    Release/slot/layout identity comes from the trusted layout record and
    the pending journal; boot-artifact digests come from the booted slot's
    finalization receipt (visible at the production receipt path because
    the machine observably runs the candidate slot). The accepted side
    reuses the candidate digests: accepted digests gate staging (already
    proven before the reboot), never health acceptance, which checks only
    slots, roots and release identity. A receipt that disagrees with the
    pending candidate release/slot fails closed.
    """
    from greia_platform.boot_transaction import BootArtifactSet

    receipt = _read_production_receipt(production_finalization_receipt_path())
    if receipt.get("slot") != journal.candidate_slot:
        raise BootHealthError(
            "finalization receipt is not the pending candidate slot"
        )
    if receipt.get("release_id") != journal.release_id:
        raise BootHealthError(
            "finalization receipt is not the pending candidate release"
        )
    if receipt.get("release_sequence") != journal.release_sequence:
        raise BootHealthError(
            "finalization receipt is not the pending candidate sequence"
        )
    if receipt.get("layout_id") != journal.layout_id:
        raise BootHealthError(
            "finalization receipt layout does not match the journal"
        )
    digests = receipt["artifact_digests"]
    assert isinstance(digests, dict)
    candidate_artifacts = BootArtifactSet(
        slot=str(journal.candidate_slot),
        layout_id=str(record.layout_id),  # type: ignore[union-attr]
        boot_backend=str(record.boot_backend),  # type: ignore[union-attr]
        generic_kernel_sha256=str(digests["generic_kernel_sha256"]),
        generic_initramfs_sha256=str(digests["host_initramfs_sha256"]),
        root_partuuid=_slot_root_partuuid(record, str(journal.candidate_slot)),
        root_filesystem_uuid=_slot_filesystem_uuid(record, str(journal.candidate_slot)),
        release_id=str(journal.release_id),
        release_sequence=int(journal.release_sequence),
    )
    accepted_artifacts = BootArtifactSet(
        slot=str(journal.accepted_slot),
        layout_id=str(record.layout_id),  # type: ignore[union-attr]
        boot_backend=str(record.boot_backend),  # type: ignore[union-attr]
        generic_kernel_sha256=str(digests["generic_kernel_sha256"]),
        generic_initramfs_sha256=str(digests["host_initramfs_sha256"]),
        root_partuuid=_slot_root_partuuid(record, str(journal.accepted_slot)),
        root_filesystem_uuid=_slot_filesystem_uuid(record, str(journal.accepted_slot)),
        release_id=str(record.accepted_release_id),  # type: ignore[union-attr]
        release_sequence=int(record.accepted_release_sequence),  # type: ignore[union-attr]
    )
    return candidate_artifacts, accepted_artifacts
