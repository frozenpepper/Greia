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
    vault: BootHealthCredentialVault,
    observer: object,
) -> BootHealthyProtocol:
    """Bind a BOOT_HEALTHY protocol to the trusted bootstrap path."""
    return BootHealthyProtocol(
        coordinator=coordinator,
        candidate_root_partuuid=candidate_root_partuuid,
        candidate_release_id=candidate_release_id,
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
# P4.3 read-only production token loading (unprivileged launcher side)
# ---------------------------------------------------------------------------
#
# The root generator (``greia-boot-health-credential.service``) owns the
# authoritative digest record and stages only the raw one-use token in the
# read-only delivery directory. This seam is the launcher's only production
# token path: it opens the delivery file ``O_RDONLY``, validates the token
# shape, and never writes — the authority directory is never even resolved
# here, so the launcher cannot own, write, or invalidate the authoritative
# vault. A missing delivery file is the normal plain-boot case and yields
# ``None`` (bounded no-op); a corrupt file fails closed. Consumption stays
# owned by the root health service (one-use ``verify_and_consume``): reading
# the token never burns it, so a failed presentation never destroys the real
# capability, while a consumed capability can never be presented twice.

#: Delivery token file name staged by the root generator.
DELIVERY_TOKEN_FILE_NAME = "boot-healthy-token"

#: Environment override for the delivery directory (tests point at tmpdirs).
DELIVERY_DIR_ENV = "GREIA_BOOT_HEALTH_DELIVERY_DIR"

#: Production delivery directory (root-owned, launcher-readable only).
DELIVERY_DIR_DEFAULT = "/run/greia-os/boot-health"


def production_delivery_path(explicit_path: Path | None = None) -> Path:
    """Resolve the delivery token file (explicit path, env, or system bind)."""
    if explicit_path is not None:
        return Path(explicit_path)
    override = os.environ.get(DELIVERY_DIR_ENV, "").strip()
    base = Path(override) if override else Path(DELIVERY_DIR_DEFAULT)
    return base / DELIVERY_TOKEN_FILE_NAME


def maybe_load_production_token(
    explicit_path: Path | None = None,
) -> str | None:
    """Read the root-issued one-use token, or ``None`` on a plain boot.

    Read-only: the file is opened ``O_RDONLY`` and the authority directory
    is never resolved, so this call cannot provision, overwrite, or
    invalidate any capability. ``None`` means no pending transaction exists
    (bounded no-op); a present-but-malformed file raises
    :class:`BootHealthError` fail-closed.
    """
    from greia_platform.boot_health import BootHealthError as _PlatformError

    path = production_delivery_path(explicit_path)
    if path.is_symlink():
        raise _PlatformError("boot-health delivery token must not be a symlink")
    try:
        descriptor = os.open(os.fspath(path), os.O_RDONLY)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise _PlatformError(
            f"boot-health delivery token is unreadable: {exc}"
        ) from exc
    try:
        with os.fdopen(descriptor, "rb") as handle:
            raw = handle.read(257)
    except OSError as exc:
        raise _PlatformError(
            f"boot-health delivery token read failed: {exc}"
        ) from exc
    if len(raw) > 256:
        raise _PlatformError("boot-health delivery token exceeds Greia bounds")
    try:
        text = raw.decode("utf-8").strip()
    except UnicodeDecodeError as exc:
        raise _PlatformError(
            "boot-health delivery token is not valid text"
        ) from exc
    # Local shape gate only (defense in depth): the root authority's digest
    # comparison stays authoritative at consume time.
    if len(text) != 64 or any(
        char not in "0123456789abcdef" for char in text
    ):
        raise _PlatformError("boot-health delivery token must be 256-bit hex")
    return text


# ---------------------------------------------------------------------------
# Production post-intro acceptance at the INTERACTIVE_READY transition
# ---------------------------------------------------------------------------
#
# The unprivileged launcher (``greiakid``) performs no privileged boot-state
# write. At ``INTERACTIVE_READY`` — after the full 7 s intro, first frame
# visible, no untrusted Activity launched — it presents the root-issued
# one-use token (:func:`maybe_load_production_token`) exactly once to the
# root ``greia-boot-health`` service/socket and returns the real outcome.
# All journal/GRUB/layout/history mutation is owned by that root endpoint;
# the launcher-side credential provisioning and in-process privileged
# mutation it replaces are gone (see the service module for the owner).

#: Environment override for the root health socket (tests point at tmpdirs).
BOOT_HEALTH_SOCKET_ENV = "GREIA_BOOT_HEALTH_SOCKET_PATH"

#: Production root health socket served by ``greia-boot-health.socket``.
BOOT_HEALTH_SOCKET_DEFAULT = "/run/greia-os/boot-health.sock"

#: Single semantic op echoed on a CONFIRMED health response.
CONFIRM_BOOT_HEALTH_OP = "CONFIRM_BOOT_HEALTH"


def production_boot_health_socket_path() -> Path:
    """Resolve the root health socket (env override or system bind)."""
    override = os.environ.get(BOOT_HEALTH_SOCKET_ENV, "").strip()
    return Path(override) if override else Path(BOOT_HEALTH_SOCKET_DEFAULT)


def maybe_accept_production_boot(
    guard: BootLifecycleGuard,
) -> BootHealthOutcome | None:
    """Present the root-issued token once, or bounded no-op.

    Called exactly once from ``LauncherApplication.apply_prepared_state``
    after ``mark_interactive_ready()``. With no delivered token (plain
    boot) it returns None having written nothing. Otherwise it carries
    the one-use token to the root ``greia-boot-health`` socket over a
    single ``CONFIRM_BOOT_HEALTH`` transaction and returns the confirmed
    outcome mapped from the service detail. Any refusal — unreadable
    socket, malformed frame, non-CONFIRMED status — raises
    :class:`BootHealthError` instead of silently skipping acceptance.

    Intro evidence is the transition itself: reaching ``INTERACTIVE_READY``
    is the intro-end boundary, so first frame and intro completion are
    implied and no untrusted Activity has launched yet (the supervisor is
    composed but has issued nothing).
    """
    _require_guard_type(guard)
    if guard.state is not BootLifecycleState.INTERACTIVE_READY:
        raise BootHealthError(
            "production BOOT_HEALTHY acceptance requires INTERACTIVE_READY; "
            f"guard reports {guard.state.value}"
        )
    # Plain-boot fast path: without a root-issued token there is no
    # presentable capability, so no acceptance can exist. No mutation: the
    # loader is read-only and the socket is never touched.
    token = maybe_load_production_token()
    if token is None:
        return None
    from greia_platform.boot_health_service import (
        BootHealthServiceError as _ServiceError,
    )
    from greia_platform.boot_health_service import (
        build_confirm_request,
        read_confirm_response,
    )

    try:
        request = build_confirm_request(token)
    except _ServiceError as exc:
        raise BootHealthError(
            f"production BOOT_HEALTHY request refused: {exc}"
        ) from exc
    raw = _transact_with_health_service(request)
    try:
        _, op, payload = read_confirm_response(raw)
    except _ServiceError as exc:
        raise BootHealthError(
            f"production BOOT_HEALTHY response refused: {exc}"
        ) from exc
    return _outcome_from_service_detail(op, payload)


def _transact_with_health_service(request: bytes) -> bytes:
    """Send one framed request to the root socket; return one raw frame.

    Exactly one connection, one send, one bounded frame read. The socket
    unit (``greia-boot-health.socket``) owns listening and activation; the
    launcher never opens, binds or serves any socket.
    """
    import socket as _socket

    from greia_platform.privileged_channel import MAX_MESSAGE_BYTES

    path = production_boot_health_socket_path()
    if path.is_symlink():
        raise BootHealthError("boot-health socket must not be a symlink")
    client = _socket.socket(_socket.AF_UNIX, _socket.SOCK_STREAM)
    try:
        client.settimeout(10.0)
        try:
            client.connect(os.fspath(path))
        except OSError as exc:
            raise BootHealthError(
                f"root boot-health service is unreachable: {exc}"
            ) from exc
        try:
            client.sendall(request)
        except OSError as exc:
            raise BootHealthError(
                f"root boot-health request was not delivered: {exc}"
            ) from exc
        chunks: list[bytes] = []
        received = 0
        while True:
            try:
                chunk = client.recv(4096)
            except OSError as exc:
                raise BootHealthError(
                    f"root boot-health response was not readable: {exc}"
                ) from exc
            if not chunk:
                break
            received += len(chunk)
            if received > MAX_MESSAGE_BYTES:
                raise BootHealthError(
                    "root boot-health response exceeds Greia bounds"
                )
            chunks.append(chunk)
            if chunk.endswith(b"\n"):
                break
        return b"".join(chunks)
    finally:
        try:
            client.close()
        except OSError:
            pass


def _outcome_from_service_detail(op: str, payload: dict[str, object]) -> BootHealthOutcome:
    """Map one CONFIRMED service payload to the launcher outcome."""
    from greia_platform.boot_health import (
        ACCEPTED_SLOT_MEDIUM,
        SETUP_MEDIUM,
    )

    reason = payload.get("reason") if isinstance(payload, dict) else None
    if op != CONFIRM_BOOT_HEALTH_OP or not isinstance(payload, dict):
        raise BootHealthError(
            f"root boot-health service refused: {reason or op}"
        )
    if payload.get("status") != "CONFIRMED":
        raise BootHealthError(
            f"root boot-health service refused: {reason or payload.get('status')}"
        )
    detail = payload.get("detail")
    if not isinstance(detail, dict):
        raise BootHealthError("root boot-health service gave no confirm detail")
    accepted_slot = detail.get("accepted_slot")
    release_id = detail.get("release_id")
    journal = detail.get("journal")
    if accepted_slot not in ("A", "B"):
        raise BootHealthError("root boot-health detail carries no accepted slot")
    if not isinstance(release_id, str) or not release_id:
        raise BootHealthError("root boot-health detail carries no release")
    if journal not in ("update", "first-install"):
        raise BootHealthError("root boot-health detail carries no journal kind")
    first_install = journal == "first-install"
    return BootHealthOutcome(
        accepted_slot=str(accepted_slot),
        release_id=str(release_id),
        first_install=first_install,
        recovery_medium_if_failed=(
            SETUP_MEDIUM if first_install else ACCEPTED_SLOT_MEDIUM
        ),
    )
