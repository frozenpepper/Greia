"""Root install-transaction service wiring: revalidation plus owned destruction (8A.5).

Step 8A.5 wires the R0/R1 semantic protocol
(:mod:`greia_installer.install_transaction`) to the privileged side of the
split:

- ``greia-installer-ui.service`` runs the graphical UI unprivileged and
  speaks only ``PREPARE_PLAN``/``EXECUTE`` over the local socket;
- this module runs as root behind ``greia-install-transaction.socket`` and
  owns every destructive command, but runs one only while a valid prepared
  transaction executes.

The root service rematerializes everything from Greia-owned state on every
call — never from request bytes:

- ``setup release``: :class:`ServiceState` loaded from the installer image's
  own target-image profile (profile id, layout adapter, slot bytes, PERSIST
  floor, target policy, boot backend) plus the service-owned payload and
  digest paths;
- ``actual block device``: :class:`PlatformInstallAuthority` re-probes
  ``lsblk`` and the live-media ancestry resolver on every
  ``list_targets``/``inventory_token`` call; requests select targets only by
  identity digest, never by ``/dev`` path, index or label;
- ``layout adapter``: the registered adapter from :mod:`greia_installer.layout`
  re-proves plan fit against the freshly verified target before anything
  destructive runs;
- ``support set`` / ``boot backend``: the release-bound hardware-support
  pool and boot backend from service state, re-loaded at the point of use
  by :class:`greia_installer.engine.InstallationEngine`.

Any inventory refresh or material target-state change between
``PREPARE_PLAN`` and ``EXECUTE`` invalidates the prepared plan fail-closed
(coordinator inventory-token + eligibility + profile re-probe), and the
executor re-resolves the block device a final time immediately before the
engine's own pre-erase re-verification. ``EXECUTE`` consumes the nonce
single-use; retries need a fresh ``PREPARE_PLAN``.

No valued physical disk is touched by the unit suite: tests inject fake
probes and recording runners; the only destructive backend is
:mod:`greia_installer.engine` behind a live nonce.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import socket
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Mapping, NoReturn, Sequence

from greia_platform.hardware import HardwareDefaults, HardwareSettings
from greia_platform.privileged_channel import (
    MAX_MESSAGE_BYTES,
    PeerCredential,
    PrivilegedChannelError,
    decode_request,
    encode_response,
    format_log_record,
    new_transaction_id,
    reject_raw_authority,
)
from greia_platform.system_language import system_language

from .disk import (
    DeviceObservation,
    DiskInventory,
    DiskProbeError,
    InstallTargetPolicy,
    LiveMediaAncestry,
    LiveMediaResolver,
    LsblkDiskProbe,
    policy_for_profile_id,
)
from .engine import InstallRequest, InstallResult, InstallationEngine, InstallationError
from .install_transaction import (
    INSTALL_TRANSACTION_ALLOWED_UIDS,
    InstallPlanAuthority,
    InstallTargetSummary,
    InstallTransactionCoordinator,
    InstallTransactionEndpoint,
    InstallTransactionError,
    PreparePlanRequest,
    PreparedInstallPlan,
)
from .layout import KNOWN_LAYOUT_ADAPTER_IDS, LayoutError, adapter_for


class TransactionServiceError(RuntimeError):
    """Root-side service check failed fail-closed (no destructive work)."""


def _require_absolute_owned_path(value: object, *, field_name: str) -> Path:
    if not isinstance(value, Path):
        raise TransactionServiceError(f"service {field_name} must be a Path")
    if not value.is_absolute():
        raise TransactionServiceError(f"service {field_name} must be absolute")
    if value.is_symlink():
        raise TransactionServiceError(f"service {field_name} must not be a symlink")
    return value


def _require_bounded_id(value: object, *, field_name: str, allowed: frozenset[str] | None = None) -> str:
    if not isinstance(value, str) or not value or len(value) > 64:
        raise TransactionServiceError(f"service {field_name} is outside Greia bounds")
    if allowed is not None and value not in allowed:
        raise TransactionServiceError(f"service {field_name} is not a known Greia id")
    return value


@dataclass(frozen=True, slots=True)
class ServiceState:
    """Greia-owned install facts the root service rematerializes from.

    Every field comes from the installer image itself (target-image profile
    manifest, service environment, baked-in payload paths) — never from UI
    request bytes. ``from_target_profile`` is the production constructor;
    tests build the dataclass directly with tmpdir fixtures.
    """

    payload: Path
    payload_digest: Path
    project_root: Path
    compatible_profile_id: str
    target_policy_id: str
    layout_adapter_id: str
    boot_backend: str
    slot_bytes: int
    persist_minimum_bytes: int
    hardware_support_pool: Path | None = None
    target_profile: Path | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "payload", _require_absolute_owned_path(self.payload, field_name="payload"))
        object.__setattr__(
            self, "payload_digest", _require_absolute_owned_path(self.payload_digest, field_name="payload_digest")
        )
        object.__setattr__(
            self, "project_root", _require_absolute_owned_path(self.project_root, field_name="project_root")
        )
        _require_bounded_id(self.compatible_profile_id, field_name="compatible_profile_id")
        from .disk import POLICY_IDS

        _require_bounded_id(self.target_policy_id, field_name="target_policy_id", allowed=POLICY_IDS)
        _require_bounded_id(
            self.layout_adapter_id, field_name="layout_adapter_id", allowed=KNOWN_LAYOUT_ADAPTER_IDS
        )
        _require_bounded_id(self.boot_backend, field_name="boot_backend")
        if isinstance(self.slot_bytes, bool) or not isinstance(self.slot_bytes, int) or self.slot_bytes <= 0:
            raise TransactionServiceError("service slot_bytes must be a positive integer")
        if (
            isinstance(self.persist_minimum_bytes, bool)
            or not isinstance(self.persist_minimum_bytes, int)
            or self.persist_minimum_bytes <= 0
        ):
            raise TransactionServiceError("service persist_minimum_bytes must be a positive integer")
        if self.hardware_support_pool is not None:
            object.__setattr__(
                self,
                "hardware_support_pool",
                _require_absolute_owned_path(self.hardware_support_pool, field_name="hardware_support_pool"),
            )
        if self.target_profile is not None:
            object.__setattr__(
                self,
                "target_profile",
                _require_absolute_owned_path(self.target_profile, field_name="target_profile"),
            )

    @classmethod
    def from_target_profile(
        cls,
        profile_path: Path,
        *,
        payload: Path,
        payload_digest: Path,
        project_root: Path,
        hardware_support_pool: Path | None = None,
    ) -> "ServiceState":
        """Load service state from the installer image's own release manifest."""
        if not isinstance(profile_path, Path) or profile_path.is_symlink() or not profile_path.is_file():
            raise TransactionServiceError("target image profile is missing or unsafe")
        try:
            raw_text = profile_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise TransactionServiceError("target image profile is unreadable") from exc
        if len(raw_text.encode("utf-8")) > 256 * 1024:
            raise TransactionServiceError("target image profile exceeds Greia bound")
        try:
            raw = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise TransactionServiceError("target image profile is not valid JSON") from exc
        if not isinstance(raw, dict):
            raise TransactionServiceError("target image profile has no release shape")
        try:
            profile_id = raw["profile"]["id"]
            storage = raw["storage"]
            layout_adapter_id = storage["layout_adapter"]
            slot_bytes = storage["system_slot_bytes"]
            persist_minimum_bytes = storage["persistent_minimum_bytes"]
            target_policy_id = raw["installer"]["target_policy"]
            boot_backend = raw["updates"]["boot_backend"]
        except (KeyError, TypeError) as exc:
            raise TransactionServiceError("target image profile misses release facts") from exc
        if not isinstance(slot_bytes, int) or isinstance(slot_bytes, bool):
            raise TransactionServiceError("target image profile slot_bytes is invalid")
        if not isinstance(persist_minimum_bytes, int) or isinstance(persist_minimum_bytes, bool):
            raise TransactionServiceError("target image profile persist floor is invalid")
        return cls(
            payload=payload,
            payload_digest=payload_digest,
            project_root=project_root,
            compatible_profile_id=profile_id,
            target_policy_id=target_policy_id,
            layout_adapter_id=layout_adapter_id,
            boot_backend=boot_backend,
            slot_bytes=slot_bytes,
            persist_minimum_bytes=persist_minimum_bytes,
            hardware_support_pool=hardware_support_pool,
            target_profile=profile_path,
        )


def _display_summary(observation: DeviceObservation) -> str:
    """Safe display facts only: model + human size, never paths/serials."""
    model = observation.model.strip() or observation.name
    safe_model = "".join(
        character for character in model if character.isalnum() or character in " _-."
    ).strip()[:64] or "disk"
    return f"{safe_model} · {observation.human_size}"


@dataclass
class PlatformInstallAuthority:
    """Production :class:`InstallPlanAuthority` over live platform probes.

    Every method re-probes: ``list_targets`` runs a fresh ``lsblk`` probe
    plus a fresh live-media ancestry resolution, and ``inventory_token``
    digests the durable-identity listing so any refresh or material change
    invalidates prepared plans. Probes/resolvers are injectable so the unit
    suite proves invalidation on fakes with zero disk contact.
    """

    policy: InstallTargetPolicy
    compatible_profile: str
    probe: LsblkDiskProbe | None = None
    live_resolver: LiveMediaResolver | None = None

    def __post_init__(self) -> None:
        _require_bounded_id(self.compatible_profile, field_name="compatible_profile")
        if self.probe is None:
            object.__setattr__(self, "probe", LsblkDiskProbe())
        if self.live_resolver is None:
            object.__setattr__(self, "live_resolver", LiveMediaResolver())

    @classmethod
    def from_service_state(
        cls,
        state: ServiceState,
        *,
        probe: LsblkDiskProbe | None = None,
        live_resolver: LiveMediaResolver | None = None,
    ) -> "PlatformInstallAuthority":
        return cls(
            policy=policy_for_profile_id(state.target_policy_id),
            compatible_profile=state.compatible_profile_id,
            probe=probe,
            live_resolver=live_resolver,
        )

    def _fresh_inventory(self) -> tuple[DiskInventory, LiveMediaAncestry]:
        assert self.probe is not None and self.live_resolver is not None
        try:
            inventory = self.probe.probe()
        except DiskProbeError as exc:
            raise InstallTransactionError(f"target inventory is unavailable: {exc}") from exc
        ancestry = self.live_resolver.resolve(inventory)
        return inventory, ancestry

    def _identity_digest(self, device: DeviceObservation) -> str:
        return _strong_or_unknown_digest(
            device,
            allow_legacy_ata_fallback=self.policy.permit_legacy_ata_fallback,
        )

    def list_targets(self) -> tuple[InstallTargetSummary, ...]:
        inventory, ancestry = self._fresh_inventory()
        summaries: list[InstallTargetSummary] = []
        for device in inventory.devices:
            if device.device_type != "disk":
                continue
            if ancestry.ambiguous or device.name in ancestry.whole_disk_names:
                summaries.append(
                    InstallTargetSummary(
                        identity_digest=self._identity_digest(device),
                        eligible=False,
                        policy_id=self.policy.policy_id,
                        display_summary=_display_summary(device),
                    )
                )
                continue
            decision = self.policy.evaluate(device)
            summaries.append(
                InstallTargetSummary(
                    identity_digest=self._identity_digest(device),
                    eligible=decision.eligible,
                    policy_id=self.policy.policy_id,
                    display_summary=_display_summary(device),
                )
            )
        if len(summaries) > 16:
            raise InstallTransactionError("target inventory exceeds Greia bound")
        return tuple(summaries)

    def inventory_token(self) -> str:
        inventory, ancestry = self._fresh_inventory()
        entries: list[dict[str, object]] = []
        for device in inventory.devices:
            if device.device_type != "disk":
                continue
            if (
                device.device_type == "disk"
                and not ancestry.ambiguous
                and device.name not in ancestry.whole_disk_names
            ):
                eligible = self.policy.evaluate(device).eligible
            else:
                eligible = False
            entries.append(
                {
                    "identity": self._identity_digest(device),
                    "eligible": eligible,
                    "size": int(device.size_bytes),
                    "mounts": sorted(str(path) for path in device.all_mountpoints()),
                    "stack": bool(device.has_active_storage_stack()),
                    "ro": bool(device.read_only),
                    "removable": bool(device.removable),
                    "hotplug": bool(device.hotplug),
                    "transport": str(device.transport or "").strip().lower(),
                }
            )
        entries.sort(key=lambda item: str(item["identity"]))
        canonical = {
            "profile": self.compatible_profile,
            "policy": self.policy.policy_id,
            "ancestry_ambiguous": ancestry.ambiguous,
            "ancestry_names": sorted(ancestry.whole_disk_names),
            "devices": entries,
        }
        raw = (json.dumps(canonical, sort_keys=True, separators=(",", ":")) + "\n").encode()
        return hashlib.sha256(raw).hexdigest()

    def compatible_profile_id(self) -> str:
        return self.compatible_profile


def _strong_or_unknown_digest(
    device: DeviceObservation, *, allow_legacy_ata_fallback: bool = False
) -> str:
    """Identity digest for the inventory listing (durable facts only).

    Uses the owning policy's own fallback flag so the UI-observed digest
    (``DeviceObservation.identity_digest``, fallback off under the default
    policy) always equals the service-side digest: selection by digest can
    never silently address a different device.
    """
    from .disk import DeviceIdentity

    identity = DeviceIdentity.from_observation(
        device, allow_legacy_ata_fallback=allow_legacy_ata_fallback
    )
    if identity.provenance.name == "UNKNOWN":
        return hashlib.sha256(b"v1|unknown").hexdigest()
    return hashlib.sha256(identity.identity_key.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Settings snapshot: bounded UI scalars -> platform HardwareSettings
# ---------------------------------------------------------------------------

_BOOL_SETTINGS_KEYS = frozenset({"touchpad_tap", "natural_scrolling", "disable_while_typing"})
_FLOAT_SETTINGS_KEYS = frozenset({"touchpad_speed", "mouse_speed", "mic_gain"})
_TEXT_SETTINGS_KEYS = frozenset({"resolution", "keyboard_layout"})
_SETTINGS_ALLOWLIST = _BOOL_SETTINGS_KEYS | _FLOAT_SETTINGS_KEYS | _TEXT_SETTINGS_KEYS | frozenset({"locale"})


def _coerce_service_bool(value: object, *, key: str) -> bool:
    # The privileged transport carries ints/strings/bools only (floats are
    # rejected by channel bounds), so the UI renders scalars as canonical
    # text. The service accepts exactly "true"/"false" (or real booleans
    # from in-process callers) and nothing else.
    if isinstance(value, bool):
        return value
    if value == "true":
        return True
    if value == "false":
        return False
    raise TransactionServiceError(f"setting {key!r} must be true/false")


def _coerce_service_float(value: object, *, key: str) -> float:
    if isinstance(value, bool):
        raise TransactionServiceError(f"setting {key!r} must be a number")
    if isinstance(value, int):
        number = float(value)
    elif isinstance(value, str) and re.fullmatch(r"-?\d+(\.\d+)?", value.strip()):
        try:
            number = float(value.strip())
        except ValueError as exc:
            raise TransactionServiceError(f"setting {key!r} must be a number") from exc
    else:
        raise TransactionServiceError(f"setting {key!r} must be a number")
    if not -1.0 <= number <= 4.0:
        raise TransactionServiceError(f"setting {key!r} is outside Greia bounds")
    return number


def checked_service_settings(snapshot: Mapping[str, object]) -> dict[str, object]:
    """Validate the UI settings snapshot against the service allowlist.

    Only semantic preference scalars travel here; unknown keys fail closed
    at ``PREPARE_PLAN`` so a plan can never be confirmed with settings the
    root service would later ignore or misread.
    """
    if not isinstance(snapshot, Mapping):
        raise TransactionServiceError("settings_snapshot must be an object")
    unknown = sorted(set(snapshot) - _SETTINGS_ALLOWLIST)
    if unknown:
        raise TransactionServiceError(
            "settings_snapshot carries unknown preferences: " + ", ".join(unknown)
        )
    checked: dict[str, object] = {}
    for key, value in snapshot.items():
        if key in _BOOL_SETTINGS_KEYS:
            checked[key] = _coerce_service_bool(value, key=key)
        elif key in _FLOAT_SETTINGS_KEYS:
            checked[key] = _coerce_service_float(value, key=key)
        elif key in _TEXT_SETTINGS_KEYS:
            if not isinstance(value, str) or not value or len(value.encode()) > 64:
                raise TransactionServiceError(f"setting {key!r} is outside Greia bounds")
            checked[key] = value
        elif key == "locale":
            if not isinstance(value, str) or not value:
                raise TransactionServiceError("setting 'locale' is outside Greia bounds")
            try:
                checked[key] = system_language(value).locale
            except Exception as exc:
                raise TransactionServiceError("setting 'locale' is not supported") from exc
    return checked


def hardware_settings_from_snapshot(
    snapshot: Mapping[str, object], *, project_root: Path
) -> tuple[HardwareSettings, str]:
    """Rematerialize platform settings from Greia-owned defaults + snapshot."""
    checked = checked_service_settings(snapshot)
    defaults = HardwareDefaults.load(project_root / "runtime" / "hardware-settings.toml")
    settings = HardwareSettings(
        schema_version=defaults.schema_version,
        touchpad_tap=bool(checked.get("touchpad_tap", defaults.touchpad_tap)),
        touchpad_speed=float(checked.get("touchpad_speed", defaults.touchpad_speed)),
        mouse_speed=float(checked.get("mouse_speed", defaults.mouse_speed)),
        natural_scrolling=bool(checked.get("natural_scrolling", defaults.natural_scrolling)),
        resolution=str(checked.get("resolution", defaults.resolution)),
        keyboard_layout=str(checked.get("keyboard_layout", defaults.keyboard_layout)),
        mic_gain=float(checked.get("mic_gain", defaults.mic_gain)),
        disable_while_typing=bool(
            checked.get("disable_while_typing", defaults.disable_while_typing)
        ),
    )
    locale = str(checked.get("locale", "en"))
    return settings, locale


# ---------------------------------------------------------------------------
# Root service: prepare framing + authorized destructive execution
# ---------------------------------------------------------------------------


@dataclass
class InstallTransactionService:
    """Root-side owner of prepare framing and authorized destruction.

    ``coordinator`` enforces nonce+digest single-use with inventory re-probe.
    The service additionally keeps the canonical plan settings it returned
    at prepare time (same-process store keyed by nonce) so ``EXECUTE`` —
    which carries nonce+digest only — can rematerialize settings, target,
    layout fit and payload from service-held state immediately before
    delegating to :class:`InstallationEngine`, which performs its own
    pre-erase re-verification (target identity, payload digest, AC/battery).
    """

    authority: PlatformInstallAuthority
    state: ServiceState
    coordinator: InstallTransactionCoordinator = field(init=False)
    endpoint: InstallTransactionEndpoint = field(init=False)
    _plan_settings: dict[str, dict[str, object]] = field(default_factory=dict)
    _last_installed_identity: str = field(default="")
    #: Production is ``None`` (real :class:`InstallationEngine`). Tests
    #: inject a recording fake so gating is proven with zero disk contact.
    engine_factory: Callable[[], InstallationEngine] | None = None

    def _new_engine(self) -> InstallationEngine:
        if self.engine_factory is not None:
            return self.engine_factory()
        return InstallationEngine(project_root=self.state.project_root)

    def __post_init__(self) -> None:
        coordinator = InstallTransactionCoordinator(authority=self.authority)
        object.__setattr__(self, "coordinator", coordinator)
        object.__setattr__(
            self, "endpoint", InstallTransactionEndpoint(coordinator)
        )

    def prepare(self, params: Mapping[str, object]) -> PreparedInstallPlan:
        """Validate service-owned settings policy, then prepare a plan."""
        if not isinstance(params, Mapping):
            raise TransactionServiceError("PREPARE_PLAN params must be an object")
        raw_settings = params.get("settings_snapshot")
        if not isinstance(raw_settings, dict):
            raise TransactionServiceError("settings_snapshot must be an object")
        try:
            checked_service_settings(raw_settings)
        except TransactionServiceError as exc:
            raise InstallTransactionError(str(exc)) from exc
        request = PreparePlanRequest.from_params(params)
        prepared = self.coordinator.prepare(request)
        self._plan_settings[prepared.transaction_nonce] = dict(request.settings_snapshot)
        while len(self._plan_settings) > 8:
            oldest = next(iter(self._plan_settings))
            del self._plan_settings[oldest]
        return prepared

    def handle_request(
        self, raw: bytes, *, peer: PeerCredential, boot_state: str
    ) -> bytes:
        """Answer one framed socket request: PREPARE returns a plan.

        ``EXECUTE`` carries nonce+digest only and runs the authorized
        install synchronously in this root process before answering
        ``INSTALLED``: the destructive backend is reachable only through a
        live, revalidated nonce, never as a standalone command surface.
        """
        from greia_platform.privileged_channel import authorize_peer, require_interactive_boot

        try:
            authorize_peer(peer, INSTALL_TRANSACTION_ALLOWED_UIDS)
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
            prepared = self.prepare(params)
            _ = format_log_record(transaction_id, op, "PREPARED")
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
            result = self.execute_and_install(
                transaction_nonce=params.get("transaction_nonce"),
                plan_digest=params.get("plan_digest"),
            )
            _ = format_log_record(transaction_id, op, "INSTALLED")
            _ = result
            return encode_response(
                transaction_id,
                op,
                {
                    "status": "INSTALLED",
                    "transaction_nonce": str(params.get("transaction_nonce")),
                    "plan_digest": str(params.get("plan_digest")),
                    "target_identity": self._last_installed_identity,
                },
            )
        raise InstallTransactionError(f"unknown install-transaction op: {op}")

    def rematerialize_target(self, identity_digest: str) -> DeviceObservation:
        """Re-resolve the authorized block device from a fresh probe.

        Identity digest is the only selector; the stored ``/dev`` locator is
        rechecked against the live observation and the typed policy plus
        live-media ancestry are re-evaluated. Anything moved, changed, or
        newly ineligible fails closed with zero destructive commands.
        """
        assert self.authority.probe is not None and self.authority.live_resolver is not None
        try:
            inventory = self.authority.probe.probe()
        except DiskProbeError as exc:
            raise TransactionServiceError(f"target inventory is unavailable: {exc}") from exc
        ancestry = self.authority.live_resolver.resolve(inventory)
        if ancestry.ambiguous:
            raise TransactionServiceError(
                "setup-medium ancestry is ambiguous; installation stopped"
            )
        matches = [
            device
            for device in inventory.devices
            if device.device_type == "disk"
            and _strong_or_unknown_digest(
                device,
                allow_legacy_ata_fallback=self.authority.policy.permit_legacy_ata_fallback,
            )
            == identity_digest
        ]
        if len(matches) != 1:
            raise TransactionServiceError("selected disk is unknown; installation stopped")
        current = matches[0]
        if current.name in ancestry.whole_disk_names:
            raise TransactionServiceError(
                "selected disk is no longer an eligible unmounted internal disk"
            )
        decision = self.authority.policy.evaluate(current)
        if not decision.eligible:
            raise TransactionServiceError(
                "selected disk is no longer an eligible unmounted internal disk"
            )
        return current

    def execute_and_install(
        self,
        *,
        transaction_nonce: object,
        plan_digest: object,
        engine: InstallationEngine | None = None,
        on_progress: Callable[[object], None] | None = None,
    ) -> InstallResult:
        """Consume a prepared nonce, revalidate everything, then install.

        Order: coordinator re-probe (single-use nonce + digest + inventory
        token + eligibility + profile) → settings from the service-held
        canonical plan (never UI bytes) → target rematerialization from a
        fresh probe → layout-adapter fit proof → engine install (which
        re-verifies payload, target, power immediately before the first
        destructive command). The first failure stops with no destructive
        command issued by this service.
        """
        authorization = self.coordinator.execute(
            transaction_nonce=transaction_nonce, plan_digest=plan_digest
        )
        if not isinstance(transaction_nonce, str):
            raise TransactionServiceError("transaction nonce is unknown or expired")
        plan_settings = self._plan_settings.pop(transaction_nonce, None)
        if plan_settings is None:
            raise TransactionServiceError("prepared plan settings are unknown or expired")
        settings, locale = hardware_settings_from_snapshot(
            plan_settings, project_root=self.state.project_root
        )
        target = self.rematerialize_target(authorization.target_identity)
        self._prove_layout_fit(target)
        object.__setattr__(self, "_last_installed_identity", authorization.target_identity)
        runner_engine = engine or self._new_engine()
        try:
            return runner_engine.install(
                InstallRequest(
                    target=target,
                    payload=self.state.payload,
                    payload_digest=self.state.payload_digest,
                    hardware_settings=settings,
                    locale=locale,
                    hardware_support_pool=self.state.hardware_support_pool,
                    target_profile=self.state.target_profile,
                ),
                on_progress,  # type: ignore[arg-type]
            )
        except InstallationError as exc:
            raise TransactionServiceError(str(exc)) from exc

    def _prove_layout_fit(self, target: DeviceObservation) -> None:
        """Prove the release layout plan fits the freshly verified target."""
        try:
            adapter = adapter_for(self.state.layout_adapter_id)
        except LayoutError as exc:
            raise TransactionServiceError(f"release layout adapter is unknown: {exc}") from exc
        if adapter.boot_backend != self.state.boot_backend:
            raise TransactionServiceError("release boot backend does not match the layout adapter")
        try:
            adapter.plan(
                device_size_bytes=int(target.size_bytes),
                slot_bytes=int(self.state.slot_bytes),
                persist_minimum_bytes=int(self.state.persist_minimum_bytes),
            )
        except LayoutError as exc:
            raise TransactionServiceError(f"release layout does not fit the target: {exc}") from exc


# ---------------------------------------------------------------------------
# Socket-activated serving (one framed request per connection)
# ---------------------------------------------------------------------------


def handle_connection(
    connection: socket.socket, *, service: InstallTransactionService, peer_uid: int
) -> None:
    """Answer exactly one framed request on an accepted socket connection."""
    peer = PeerCredential(uid=peer_uid)
    try:
        connection.settimeout(10.0)
        chunks: list[bytes] = []
        received = 0
        while True:
            chunk = connection.recv(4096)
            if not chunk:
                break
            received += len(chunk)
            if received > MAX_MESSAGE_BYTES:
                raise InstallTransactionError("request exceeds Greia bound")
            chunks.append(chunk)
            if chunk.endswith(b"\n"):
                break
        raw = b"".join(chunks)
        try:
            response = service.handle_request(raw, peer=peer, boot_state="installer_ready")
        except (InstallTransactionError, TransactionServiceError, PrivilegedChannelError) as exc:
            from greia_platform.privileged_channel import encode_response, new_transaction_id

            response = encode_response(
                new_transaction_id(), "ERROR", {"status": "REFUSED", "reason": str(exc)[:256]}
            )
        connection.sendall(response)
    finally:
        try:
            connection.close()
        except OSError:
            pass


def build_live_service(*, project_root: Path | None = None) -> InstallTransactionService:
    """Compose the production service from Greia-owned environment state."""
    root = project_root or Path(os.environ.get("GREIA_OS_ROOT", "/opt/greia-os"))
    payload = Path(
        os.environ.get("GREIA_INSTALL_PAYLOAD", "/run/live/medium/payload/pip-rootfs.squashfs")
    )
    payload_digest = Path(
        os.environ.get("GREIA_INSTALL_PAYLOAD_DIGEST", "/etc/greia-os/expected-payload.sha256")
    )
    target_profile = Path(
        os.environ.get("GREIA_TARGET_IMAGE_PROFILE", "/etc/greia-os/target-image-profile.json")
    )
    pool_value = os.environ.get("GREIA_HARDWARE_SUPPORT_POOL", "/opt/greia-hardware-support").strip()
    pool = Path(pool_value) if pool_value else None
    state = ServiceState.from_target_profile(
        target_profile,
        payload=payload,
        payload_digest=payload_digest,
        project_root=root,
        hardware_support_pool=pool,
    )
    return InstallTransactionService(
        authority=PlatformInstallAuthority.from_service_state(state), state=state
    )


def serve_forever(listener: socket.socket, *, service: InstallTransactionService) -> NoReturn:
    """Accept connections until the socket unit stops (systemd owns the fd)."""
    while True:
        connection, _ = listener.accept()
        try:
            peer_uid = _peer_uid(connection)
        except OSError:
            try:
                connection.close()
            except OSError:
                pass
            continue
        handle_connection(connection, service=service, peer_uid=peer_uid)


def _peer_uid(connection: socket.socket) -> int:
    import struct

    raw = connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i"))
    _pid, uid, _gid = struct.unpack("3i", raw)
    return int(uid)


def main(argv: Sequence[str] | None = None) -> int:
    """Socket-activated entry for ``greia-install-transaction.service``.

    With systemd socket activation (``LISTEN_FDS``) the passed file
    descriptor is the listening socket; without one (manual runs, unit
    suite) the service exits fail-closed instead of opening any socket
    itself.
    """
    _ = list(argv or [])
    listen_fds = int(os.environ.get("LISTEN_FDS", "0"))
    if listen_fds < 1:
        raise SystemExit(
            "greia-install-transaction: no socket-activated file descriptor; "
            "refusing to listen (see greia-install-transaction.socket)"
        )
    service = build_live_service()
    listener = socket.fromfd(3, socket.AF_UNIX, socket.SOCK_STREAM)
    serve_forever(listener, service=service)
    return 0  # pragma: no cover - serve_forever never returns


if __name__ == "__main__":  # pragma: no cover - service entry
    raise SystemExit(main(sys.argv[1:]))
