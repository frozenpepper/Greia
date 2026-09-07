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
"""

from __future__ import annotations

import os
from pathlib import Path

from greia_platform.boot_health import (
    BootHealthCredentialRecord,
    BootHealthCredentialVault,
    BootHealthyProtocol,
    BootHealthError,
    HealthyCommittingTicket,
    IntroEvidence,
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


def _require_guard_type(guard: object) -> BootLifecycleGuard:
    if not isinstance(guard, BootLifecycleGuard):
        raise BootHealthError("BOOT_HEALTHY seam requires the launcher boot guard")
    return guard
