"""Narrow production BOOT_HEALTHY capability verifier (P4.6 / HEALTH-PROOF2).

Root-side seam behind
:func:`greia_platform.boot_health_service.load_production_capability_verifier`.
It adapts the token-only service seam
(:class:`greia_platform.boot_health_service.BootHealthCapabilityVerifier`)
to the binding-ful root authority
(:class:`greia_platform.boot_health.BootHealthCapabilityAuthority`).

On every ``verify_and_consume`` call the verifier resolves the single
pending transaction, the current kernel boot ID and the trusted launcher
bootstrap path from Greia-owned state — never from request bytes (the
presented token is the only request-derived input) — and calls the
authority's ``verify_and_consume`` exactly once. Absent or ambiguous
pending state, unknown tokens and replays all fail closed through the
authority without mutation.

No vault is constructed here: the launcher-writable credential vault
serves the established in-process protocol path only and is never a
substitute for this root verifier.
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from .boot_health import (
    BootHealthCapabilityAuthority,
    BootHealthCapabilityRecord,
    BootHealthError,
    capability_peer_bootstrap_path,
    default_capability_authority,
    load_pending_boot_journal,
    read_boot_id,
)


class ProductionBootHealthCapabilityVerifier:
    """Token-only verifier resolving bindings from Greia-owned state.

    ``authority`` defaults to the production root authority (env-aware
    binds); ``boot_journal_dir``/``update_state_dir`` scope the pending
    journal lookup (``None`` resolves the production composition roots);
    ``boot_id``/``peer_bootstrap_path`` default to the live kernel boot ID
    and the trusted launcher bootstrap path. Explicit values exist so
    disposable-root tests exercise this exact class against tmpdirs.
    """

    def __init__(
        self,
        *,
        authority: BootHealthCapabilityAuthority | None = None,
        boot_journal_dir: Path | None = None,
        update_state_dir: Path | None = None,
        boot_id: str | None = None,
        peer_bootstrap_path: str | None = None,
    ) -> None:
        self._authority = authority
        self._boot_journal_dir = Path(boot_journal_dir) if boot_journal_dir is not None else None
        self._update_state_dir = Path(update_state_dir) if update_state_dir is not None else None
        self._boot_id = boot_id
        self._peer_bootstrap_path = peer_bootstrap_path

    def verify_and_consume(self, *, token: str) -> Mapping[str, object]:
        """Verify the one-use capability and consume it (exactly once).

        The pending journal is resolved read-only from Greia-owned state:
        no pending transaction refuses (plain boot); both-pending refuses
        rather than guessing. The single pending transaction's ID, the
        current boot attempt and the trusted launcher path bind the
        presented token through exactly one authority call. A failed guess
        never burns the live capability; a consumed capability never
        verifies twice.
        """
        pending = load_pending_boot_journal(
            boot_journal_dir=self._boot_journal_dir,
            update_state_dir=self._update_state_dir,
        )
        if pending is None:
            raise BootHealthError(
                "BOOT_HEALTHY capability refused: no pending boot-health "
                "transaction"
            )
        _, journal = pending
        transaction_id = str(getattr(journal, "transaction_id", ""))
        if not transaction_id:
            raise BootHealthError(
                "BOOT_HEALTHY capability refused: pending transaction "
                "carries no identity"
            )
        attempt = self._boot_id if self._boot_id is not None else read_boot_id()
        peer_path = (
            self._peer_bootstrap_path
            if self._peer_bootstrap_path is not None
            else capability_peer_bootstrap_path()
        )
        authority = (
            self._authority
            if self._authority is not None
            else default_capability_authority()
        )
        record = authority.verify_and_consume(
            token=token,
            transaction_id=transaction_id,
            boot_attempt=attempt,
            peer_bootstrap_path=peer_path,
        )
        return _record_view(record)


def _record_view(record: BootHealthCapabilityRecord) -> Mapping[str, object]:
    """Return the consumed record as a plain mapping (service seam)."""
    return dict(record.as_dict())


def build_production_verifier(
    *,
    authority: BootHealthCapabilityAuthority | None = None,
    boot_journal_dir: Path | None = None,
    update_state_dir: Path | None = None,
    boot_id: str | None = None,
    peer_bootstrap_path: str | None = None,
) -> ProductionBootHealthCapabilityVerifier:
    """Build the shipped root capability verifier.

    No-argument composition resolves everything from Greia-owned state
    (pending journal, kernel boot ID, trusted launcher path, root
    authority); explicit arguments scope the same class to disposable
    roots for tests.
    """
    return ProductionBootHealthCapabilityVerifier(
        authority=authority,
        boot_journal_dir=boot_journal_dir,
        update_state_dir=update_state_dir,
        boot_id=boot_id,
        peer_bootstrap_path=peer_bootstrap_path,
    )
