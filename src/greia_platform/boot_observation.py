"""Platform-owned early-boot observation owner (P4.1).

Single narrow production entry point that establishes the actual booted
slot from the kernel root before launcher health acceptance or the
recovery deadline depend on it, and reconciles the x86 GRUB backend so
every consumer reads one authoritative ``greia_last_booted`` fact.

Mechanism (all reused, no second observer/parser or second backend):

- observe actual boot identity by reusing
  :class:`greia_platform.boot_health.ProductionActualBootObserver`
  (exactly one ``root=PARTUUID=`` from the kernel cmdline, resolved
  through the trusted installed layout record, cross-checked against the
  booted slot's ``release-identity.json``);
- reconcile exactly that observed slot into
  :class:`greia_platform.grub_ab.GrubEnvBackend` by reusing
  :meth:`reconcile` (records ``greia_last_booted``, consumes a pending
  one-shot, preserves the persistent default);
- emit bounded evidence (one journal/stdout line, small result record).

Makes no acceptance decision: no BOOT_HEALTHY predicate, no
journal/health/accepted-state commit, no layout-authority mutation.

Fail-closed behavior:

- zero, multiple, or malformed ``root=PARTUUID=`` tokens refuse;
- a root PARTUUID matching no layout slot refuses;
- a release-identity slot disagreeing with the PARTUUID-resolved slot
  refuses;
- corrupt/unreadable layout, cmdline, identity, or grubenv state refuses;
- the slot is never inferred from ``next_entry`` and no PARTUUID or slot
  is ever fabricated.
- a machine not running an installed A/B layout (absent layout record,
  or a single-root record with ``system_b`` null) is a bounded observable
  no-op: returns ``observed_slot=None`` with ``reconciled=False`` and
  writes nothing — single-root stays unavailable.

Idempotent: re-observing the same slot reconciles the same authoritative
fact and consumes no additional state (``reconcile`` preserves the
default and rewrites the same ``greia_last_booted`` value).
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from greia_platform.boot_health import (
    BootHealthError,
    ProductionActualBootObserver,
)


class BootObservationError(BootHealthError):
    """Early-boot observation refused or the backend could not reconcile."""


#: Bounded reason strings emitted in the result record / journal line.
REASON_RECONCILED = "reconciled"
REASON_NOOP_ABSENT_LAYOUT = "no-op:absent-layout-record"
REASON_NOOP_SINGLE_ROOT = "no-op:single-root-layout"


@dataclass(frozen=True, slots=True)
class BootObservationResult:
    """Bounded evidence for one observer run.

    ``observed_slot`` is ``"A"``/``"B"`` after a successful observation,
    else ``None`` for the bounded no-op. ``reconciled`` is True only when
    :meth:`GrubEnvBackend.reconcile` recorded exactly that slot.
    """

    observed_slot: str | None
    root_partuuid: str | None
    release_id: str | None
    release_sequence: int | None
    reconciled: bool
    reason: str

    def evidence_line(self) -> str:
        """One bounded journal/stdout line describing this run."""
        slot = self.observed_slot if self.observed_slot is not None else "-"
        return f"greia-boot-observer: {self.reason} slot={slot}"


def _resolve_grubenv_dir(explicit: Path | None) -> Path:
    if explicit is not None:
        return Path(explicit)
    from greia_platform.system_updates import resolve_grubenv_dir

    return resolve_grubenv_dir()


def _layout_record_allows_ab(layout_record_path: Path) -> bool | None:
    """Return True for A/B layout, False for single-root, None when absent.

    Raises :class:`BootObservationError` for corrupt/unreadable records
    (fail-closed); a missing file is the normal non-A/B case (None).
    """
    from greia_platform.persistent_layout import (
        InstalledLayoutRecord,
        PersistentLayoutError,
    )

    candidate = Path(layout_record_path)
    if candidate.is_symlink():
        raise BootObservationError("installed layout record must not be a symlink")
    try:
        raw = candidate.read_bytes()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise BootObservationError(
            f"installed layout record is unreadable: {exc}"
        ) from exc
    import json as _json

    try:
        document = _json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise BootObservationError(
            "installed layout record is not valid JSON"
        ) from exc
    try:
        record = InstalledLayoutRecord.from_dict(document)
    except PersistentLayoutError as exc:
        raise BootObservationError(
            f"installed layout record is not authoritative: {exc}"
        ) from exc
    return record.system_b is not None


def observe_and_reconcile_boot(
    *,
    cmdline_path: Path | None = None,
    layout_record_path: Path | None = None,
    release_identity_path: Path | None = None,
    grubenv_dir: Path | None = None,
) -> BootObservationResult:
    """Observe the actual booted slot and reconcile it into the GRUB backend.

    Reuses :class:`ProductionActualBootObserver` for observation and
    :meth:`GrubEnvBackend.reconcile` for the single authoritative
    ``greia_last_booted`` fact. Performs no BOOT_HEALTHY decision and no
    journal/health/accepted-state commit.

    Returns a no-op result (no observation, no write) when the machine is
    not on an installed A/B layout. Raises :class:`BootObservationError`
    (a :class:`BootHealthError`) fail-closed for missing, multiple,
    ambiguous, or layout-mismatched kernel-root identity.
    """
    from greia_platform.boot_health import (
        production_cmdline_path,
        production_layout_record_path,
        production_release_identity_path,
    )
    from greia_platform.grub_ab import GrubEnvBackend

    resolved_cmdline = (
        Path(cmdline_path) if cmdline_path is not None else production_cmdline_path()
    )
    resolved_layout = (
        Path(layout_record_path)
        if layout_record_path is not None
        else production_layout_record_path()
    )
    resolved_identity = (
        Path(release_identity_path)
        if release_identity_path is not None
        else production_release_identity_path()
    )
    resolved_grubenv = _resolve_grubenv_dir(grubenv_dir)

    # Bounded no-op gate before any observation: without an installed A/B
    # layout there is no authoritative slot to establish and nothing is
    # fabricated. Corrupt records still refuse (fail-closed) inside the
    # helper; only absent/single-root pass through as no-ops.
    allows_ab = _layout_record_allows_ab(resolved_layout)
    if allows_ab is None:
        return BootObservationResult(
            observed_slot=None,
            root_partuuid=None,
            release_id=None,
            release_sequence=None,
            reconciled=False,
            reason=REASON_NOOP_ABSENT_LAYOUT,
        )
    if not allows_ab:
        return BootObservationResult(
            observed_slot=None,
            root_partuuid=None,
            release_id=None,
            release_sequence=None,
            reconciled=False,
            reason=REASON_NOOP_SINGLE_ROOT,
        )

    # Single production observer: kernel root PARTUUID -> trusted layout
    # slot -> release-identity cross-check. Any refusal propagates as
    # BootHealthError (BootObservationError is a subclass, so callers may
    # catch either); nothing is inferred from next_entry here.
    observer = ProductionActualBootObserver(
        cmdline_path=resolved_cmdline,
        layout_record_path=resolved_layout,
        release_identity_path=resolved_identity,
    )
    try:
        observed = observer.observe()
    except BootHealthError as exc:
        raise BootObservationError(str(exc)) from exc

    # Reconcile exactly the observed slot. attach() fail-closed on missing
    # or corrupt grubenv; reconcile() preserves the persistent default and
    # only records greia_last_booted (no commit_accepted, no journal).
    from greia_platform.boot_transaction import BootTransactionError
    from greia_platform.grub_ab import GrubAbConfigError

    try:
        backend = GrubEnvBackend.attach(resolved_grubenv)
    except (BootTransactionError, GrubAbConfigError, OSError, ValueError) as exc:
        raise BootObservationError(f"boot backend is unavailable: {exc}") from exc
    try:
        backend.reconcile(observed.booted_slot)
    except (BootTransactionError, GrubAbConfigError, OSError, ValueError) as exc:
        raise BootObservationError(f"boot observation reconcile refused: {exc}") from exc
    state = backend.inspect()
    if state.last_booted_slot != observed.booted_slot:
        raise BootObservationError(
            "boot observation reconcile did not record the observed slot"
        )
    return BootObservationResult(
        observed_slot=observed.booted_slot,
        root_partuuid=observed.root_partuuid,
        release_id=observed.release_id,
        release_sequence=observed.release_sequence,
        reconciled=True,
        reason=REASON_RECONCILED,
    )


def main(argv: list[str] | None = None) -> int:
    """Systemd entry point: observe, reconcile, emit one bounded line.

    Exit 0 after a reconciled observation or a bounded no-op; exit 1
    fail-closed on any refused observation or unavailable backend (the
    unit is ordered Before the launcher but never Required by it, so a
    refused boot fact fails loudly without silently authorizing boot).
    """
    _ = argv
    try:
        result = observe_and_reconcile_boot()
    except BootHealthError as exc:
        print(f"greia-boot-observer: refused: {exc}", file=sys.stderr)
        return 1
    print(result.evidence_line())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
