"""Installer prepare-plan/execute semantic protocol (L7-PROTOCOLS, R0/R1).

The ``greia-install-transaction`` socket-activated service exposes bounded
semantic operations over the shared :mod:`greia_platform.privileged_channel`
transport:

- ``LIVE_SSH_STATUS`` / ``LIVE_SSH_SET`` query or change only the live installer SSH service.
- ``PREPARE_PLAN(expected_target_identity, compatible_profile_id,
  settings_snapshot)`` returns a single-use ``transaction_nonce``, a
  canonical human-reviewable plan, and its ``plan_digest``.
- ``EXECUTE`` accepts only ``nonce`` + matching ``digest`` and re-probes
  every authority immediately before destructive work.

Requests can never carry raw paths, commands, URLs, mountpoints, partition
numbers or bootloader arguments: targets are selected only by identity
digest (``DeviceIdentity.digest``), never by ``/dev`` path, list index or
label. Any inventory refresh or material target-state change invalidates
the prepared plan fail-closed.

R0/R1 bound: protocol definitions only. The coordinator re-proves
authority and returns a bounded ``ExecuteAuthorization``; no destructive
backend is wired here, so nothing can be destructively enabled through
this module yet. Step 8A.5 wires destruction in
:mod:`greia_installer.transaction_service`, which consumes the single-use
nonce through this coordinator and rematerializes every other install
fact from Greia-owned service state. The socket units stay inactive during
ordinary pre-intro boot and accept only the root service and installer UI
peer UIDs.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Mapping, Protocol

from greia_platform.privileged_channel import (
    PeerCredential,
    PrivilegedChannelError,
    authorize_peer,
    decode_request,
    encode_response,
    format_log_record,
    new_transaction_id,
    reject_raw_authority,
    require_interactive_boot,
)


class InstallTransactionError(RuntimeError):
    """Prepare/execute semantic check failed fail-closed."""


#: Semantic operations of the install-transaction service.
INSTALL_TRANSACTION_OPS = ("PREPARE_PLAN", "EXECUTE", "LIVE_SSH_STATUS", "LIVE_SSH_SET")

#: Unprivileged installer UI identity (Debian ``nobody``, always present).
#: The graphical UI runs as this UID behind ``greia-installer-ui.service``
#: and is the only non-root peer the transaction socket authorizes. Root
#: stays authorized because root already owns the machine; authorizing it
#: here changes nothing, while every other UID is refused fail-closed.
INSTALLER_UI_UID = 65534

#: Peer UIDs authorized for the installer service (root service + UI peer).
INSTALL_TRANSACTION_ALLOWED_UIDS = (0, INSTALLER_UI_UID)

_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_NONCE_RE = re.compile(r"^[0-9a-f]{32}$")
_PROFILE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_SETTING_KEY_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
_MAX_SETTINGS_ENTRIES = 32
_MAX_SETTING_VALUE_BYTES = 256
_MAX_PENDING_PLANS = 8
_PLAN_SCHEMA_VERSION = 1


def _require_hex64(value: object, *, field_name: str) -> str:
    if not isinstance(value, str) or not _HEX64_RE.fullmatch(value):
        raise InstallTransactionError(f"{field_name} must be lowercase SHA-256 hex")
    return value


def _require_profile_id(value: object) -> str:
    if not isinstance(value, str) or not _PROFILE_ID_RE.fullmatch(value):
        raise InstallTransactionError("compatible_profile_id is outside Greia bounds")
    return value


def _check_settings_snapshot(value: object) -> dict[str, str]:
    if not isinstance(value, dict):
        raise InstallTransactionError("settings_snapshot must be an object")
    if len(value) > _MAX_SETTINGS_ENTRIES:
        raise InstallTransactionError("settings_snapshot exceeds Greia bounds")
    checked: dict[str, str] = {}
    for key, item in value.items():
        if not isinstance(key, str) or not _SETTING_KEY_RE.fullmatch(key):
            raise InstallTransactionError(
                f"settings_snapshot key is not a safe identifier: {key!r}"
            )
        if not isinstance(item, str) or len(item.encode("utf-8")) > _MAX_SETTING_VALUE_BYTES:
            raise InstallTransactionError(
                f"settings_snapshot value exceeds Greia bounds: {key!r}"
            )
        checked[key] = item
    return checked


def _canonical_bytes(value: Mapping[str, object]) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def canonical_plan_bytes(plan: Mapping[str, object]) -> bytes:
    """Canonical bytes a plan digest is computed over (shared with the UI)."""
    return _canonical_bytes(dict(plan))


# ---------------------------------------------------------------------------
# Typed requests / plans
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PreparePlanRequest:
    """Semantic prepare request: identity digest + profile + settings only."""

    expected_target_identity: str
    compatible_profile_id: str
    settings_snapshot: Mapping[str, str]

    def __post_init__(self) -> None:
        _require_hex64(self.expected_target_identity, field_name="expected_target_identity")
        _require_profile_id(self.compatible_profile_id)
        checked = _check_settings_snapshot(dict(self.settings_snapshot))
        object.__setattr__(self, "settings_snapshot", checked)

    @classmethod
    def from_params(cls, params: Mapping[str, object]) -> "PreparePlanRequest":
        if not isinstance(params, Mapping):
            raise InstallTransactionError("PREPARE_PLAN params must be an object")
        if set(params) != {
            "expected_target_identity",
            "compatible_profile_id",
            "settings_snapshot",
        }:
            raise InstallTransactionError("PREPARE_PLAN params carry unknown fields")
        reject_raw_authority(params)
        settings = params.get("settings_snapshot")
        if not isinstance(settings, dict):
            raise InstallTransactionError("settings_snapshot must be an object")
        return cls(
            expected_target_identity=params.get("expected_target_identity"),
            compatible_profile_id=params.get("compatible_profile_id"),  # type: ignore[arg-type]
            settings_snapshot=settings,  # type: ignore[arg-type]
        )


@dataclass(frozen=True, slots=True)
class PreparedInstallPlan:
    """Human-reviewable install plan plus its integrity digest."""

    transaction_nonce: str
    plan: Mapping[str, object]
    plan_digest: str

    def __post_init__(self) -> None:
        if not isinstance(self.transaction_nonce, str) or not _NONCE_RE.fullmatch(
            self.transaction_nonce
        ):
            raise InstallTransactionError("transaction nonce is outside Greia bounds")
        _require_hex64(self.plan_digest, field_name="plan_digest")
        expected = hashlib.sha256(_canonical_bytes(dict(self.plan))).hexdigest()
        if not hmac.compare_digest(expected, self.plan_digest):
            raise InstallTransactionError("plan digest does not match the plan")


@dataclass(frozen=True, slots=True)
class ExecuteAuthorization:
    """Bounded proof that EXECUTE re-probed every authority.

    R0/R1 carries no destructive backend: this receipt proves the nonce and
    digest matched a live, still-eligible target under a fresh inventory. The
    privileged service performs no disk write through this module.
    """

    transaction_nonce: str
    plan_digest: str
    target_identity: str
    compatible_profile_id: str
    destructive_enabled: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.transaction_nonce, str) or not _NONCE_RE.fullmatch(
            self.transaction_nonce
        ):
            raise InstallTransactionError("transaction nonce is outside Greia bounds")
        _require_hex64(self.plan_digest, field_name="plan_digest")
        _require_hex64(self.target_identity, field_name="target_identity")
        if self.destructive_enabled is not False:
            raise InstallTransactionError(
                "destructive install is not enabled at R0/R1"
            )


# ---------------------------------------------------------------------------
# Authority seam (target observation owned by the platform/installer stack)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class InstallTargetSummary:
    """Minimal observable facts for one install-eligible candidate target."""

    identity_digest: str
    eligible: bool
    policy_id: str
    display_summary: str

    def __post_init__(self) -> None:
        _require_hex64(self.identity_digest, field_name="target identity digest")
        if not self.policy_id or len(self.policy_id) > 64:
            raise InstallTransactionError("target policy_id is outside Greia bounds")
        if not isinstance(self.display_summary, str) or len(self.display_summary) > 256:
            raise InstallTransactionError("target display summary exceeds Greia bound")


class InstallPlanAuthority(Protocol):
    """Narrow observation seam the coordinator re-probes on every call."""

    def list_targets(self) -> tuple[InstallTargetSummary, ...]: ...

    def inventory_token(self) -> str: ...

    def compatible_profile_id(self) -> str: ...


@dataclass
class InstallTransactionCoordinator:
    """Semantic prepare/execute coordinator with plan invalidation.

    Holds at most ``_MAX_PENDING_PLANS`` single-use prepared plans. Each
    stores the inventory token observed at prepare time; ``EXECUTE``
    re-probes the authority and fails closed when the inventory refreshed
    or the target's eligibility/material state changed.
    """

    authority: InstallPlanAuthority
    pending: OrderedDict[str, dict[str, object]] = field(default_factory=OrderedDict)

    def prepare(self, request: PreparePlanRequest) -> PreparedInstallPlan:
        targets = self.authority.list_targets()
        if len(targets) > 16:
            raise InstallTransactionError("target inventory exceeds Greia bound")
        expected_profile = self.authority.compatible_profile_id()
        _require_profile_id(expected_profile)
        if request.compatible_profile_id != expected_profile:
            raise InstallTransactionError(
                "compatible profile does not match this installer image"
            )
        match: InstallTargetSummary | None = None
        for candidate in targets:
            if hmac.compare_digest(candidate.identity_digest, request.expected_target_identity):
                match = candidate
                break
        if match is None:
            raise InstallTransactionError("selected disk is unknown; installation stopped")
        if not match.eligible:
            raise InstallTransactionError(
                "selected disk is no longer an eligible unmounted internal disk"
            )
        inventory_token = self.authority.inventory_token()
        if not isinstance(inventory_token, str) or not inventory_token or len(
            inventory_token.encode("utf-8")
        ) > 256:
            raise InstallTransactionError("inventory token is outside Greia bounds")
        plan = {
            "schema_version": _PLAN_SCHEMA_VERSION,
            "target_identity_digest": match.identity_digest,
            "target_policy_id": match.policy_id,
            "target_display": match.display_summary,
            "compatible_profile_id": request.compatible_profile_id,
            "settings": dict(request.settings_snapshot),
            "steps": [
                "verify-target",
                "verify-payload",
                "prepare",
                "erase",
                "format",
                "copy",
                "configure",
                "bootloader",
                "verify",
            ],
        }
        digest = hashlib.sha256(_canonical_bytes(plan)).hexdigest()
        nonce = secrets.token_hex(16)
        self.pending[nonce] = {
            "plan_digest": digest,
            "target_identity": match.identity_digest,
            "compatible_profile_id": request.compatible_profile_id,
            "inventory_token": inventory_token,
        }
        while len(self.pending) > _MAX_PENDING_PLANS:
            self.pending.popitem(last=False)
        return PreparedInstallPlan(transaction_nonce=nonce, plan=plan, plan_digest=digest)

    def execute(self, *, transaction_nonce: object, plan_digest: object) -> ExecuteAuthorization:
        """Accept only a live nonce plus its matching digest, then re-probe."""
        if not isinstance(transaction_nonce, str) or not _NONCE_RE.fullmatch(transaction_nonce):
            raise InstallTransactionError("transaction nonce is unknown")
        if not isinstance(plan_digest, str) or not _HEX64_RE.fullmatch(str(plan_digest)):
            raise InstallTransactionError("plan digest does not match the plan")
        stored = self.pending.get(transaction_nonce)
        if stored is None:
            raise InstallTransactionError("transaction nonce is unknown or expired")
        if not hmac.compare_digest(str(stored["plan_digest"]), str(plan_digest)):
            raise InstallTransactionError("plan digest does not match the plan")
        # Re-probe all authority immediately before destructive work.
        fresh_token = self.authority.inventory_token()
        if not hmac.compare_digest(str(stored["inventory_token"]), str(fresh_token)):
            del self.pending[transaction_nonce]
            raise InstallTransactionError(
                "inventory refreshed since PREPARE_PLAN; plan invalidated"
            )
        targets = {item.identity_digest: item for item in self.authority.list_targets()}
        current = targets.get(str(stored["target_identity"]))
        if current is None:
            del self.pending[transaction_nonce]
            raise InstallTransactionError("selected disk disappeared")
        if not current.eligible:
            del self.pending[transaction_nonce]
            raise InstallTransactionError(
                "selected disk is no longer an eligible unmounted internal disk"
            )
        expected_profile = self.authority.compatible_profile_id()
        if str(stored["compatible_profile_id"]) != expected_profile:
            del self.pending[transaction_nonce]
            raise InstallTransactionError(
                "compatible profile changed since PREPARE_PLAN; plan invalidated"
            )
        del self.pending[transaction_nonce]
        return ExecuteAuthorization(
            transaction_nonce=transaction_nonce,
            plan_digest=str(plan_digest),
            target_identity=str(stored["target_identity"]),
            compatible_profile_id=str(stored["compatible_profile_id"]),
        )


# ---------------------------------------------------------------------------
# Socket-activated endpoint (semantic core; transport wiring deferred)
# ---------------------------------------------------------------------------


class InstallTransactionEndpoint:
    """Answer one framed request for the install-transaction service.

    Pure over bytes with injected peer/boot-state: peer UID must be the
    installer UID, boot must be interactive-ready, and every schema/raw
    authority bound applies before the coordinator runs.
    """

    def __init__(
        self,
        coordinator: InstallTransactionCoordinator,
        *,
        allowed_uids: tuple[int, ...] = INSTALL_TRANSACTION_ALLOWED_UIDS,
    ) -> None:
        self.coordinator = coordinator
        self.allowed_uids = allowed_uids

    def handle_request(
        self, raw: bytes, *, peer: PeerCredential, boot_state: str
    ) -> bytes:
        try:
            authorize_peer(peer, self.allowed_uids)
        except PrivilegedChannelError as exc:
            raise InstallTransactionError(str(exc)) from exc
        try:
            require_interactive_boot(boot_state)
        except PrivilegedChannelError as exc:
            raise InstallTransactionError(str(exc)) from exc
        try:
            op, params = decode_request(raw)
        except PrivilegedChannelError as exc:
            raise InstallTransactionError(str(exc)) from exc
        transaction_id = new_transaction_id()
        if op == "PREPARE_PLAN":
            request = PreparePlanRequest.from_params(params)
            prepared = self.coordinator.prepare(request)
            received = format_log_record(transaction_id, op, "PREPARED")
            _ = received
            return encode_response(
                transaction_id,
                op,
                {
                    "status": "PREPARED",
                    "transaction_nonce": prepared.transaction_nonce,
                    "plan": dict(prepared.plan),
                    "plan_digest": prepared.plan_digest,
                },
            )
        if op == "EXECUTE":
            if set(params) != {"transaction_nonce", "plan_digest"}:
                raise InstallTransactionError("EXECUTE params carry unknown fields")
            reject_raw_authority(params)
            authorization = self.coordinator.execute(
                transaction_nonce=params.get("transaction_nonce"),
                plan_digest=params.get("plan_digest"),
            )
            received = format_log_record(transaction_id, op, "AUTHORIZED")
            _ = received
            return encode_response(
                transaction_id,
                op,
                {
                    "status": "AUTHORIZED",
                    "transaction_nonce": authorization.transaction_nonce,
                    "plan_digest": authorization.plan_digest,
                    "target_identity": authorization.target_identity,
                    "destructive_enabled": False,
                },
            )
        raise InstallTransactionError(f"unknown install-transaction op: {op}")


def main(argv: list[str] | None = None) -> int:
    """Socket-service entry point (R0/R1: defined, never destructively enabled).

    The ``greia-install-transaction`` socket/service units reference this
    entry. It refuses to perform destructive work: with no socket-activated
    file descriptor and no destructive backend wired, it exits fail-closed.
    """
    _ = list(argv or [])
    raise SystemExit(
        "greia-install-transaction: destructive backend not wired at R0/R1; "
        "service defined but never enabled (see greia-install-transaction.service)"
    )


if __name__ == "__main__":
    raise SystemExit(main())
