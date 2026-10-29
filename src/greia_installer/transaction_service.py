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
from typing import Callable, Mapping, NoReturn, Sequence, TextIO

from greia_platform.hardware import HardwareDefaults, HardwareSettings
from greia_platform.persistent_layout import ALLOWED_LAYOUT_ADAPTERS
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
from .install_progress import PROGRESS_OP, ProgressReporter
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
from .layout import LayoutError, adapter_for
from .wifi_carryover import WIFI_SNAPSHOT_KEYS, WifiCarryoverChoice, WifiCarryoverError


class TransactionServiceError(RuntimeError):
    """Root-side service check failed fail-closed (no destructive work)."""


_S04_DIAG_SERIAL_HANDLE: TextIO | None = None
_S04_DIAG_FAULTHANDLER_SECONDS = 120


def _s04_diag_faulthandler() -> None:
    """TEMPORARY Session-04 diagnostic: crash/hang tracebacks to serial.

    When the test-only marker ``/run/greia-x8-debug`` exists, enables
    faulthandler dumping to the guest serial console (fatal signals get
    a traceback; a repeating dump names hangs). Production never creates
    the marker. Removed before Session 04 closure.
    """
    global _S04_DIAG_SERIAL_HANDLE
    if _S04_DIAG_SERIAL_HANDLE is not None:
        return
    if not os.path.exists("/run/greia-x8-debug"):
        return
    try:
        import faulthandler

        handle = open("/dev/ttyS0", "a")  # noqa: PTH123
        _S04_DIAG_SERIAL_HANDLE = handle
        faulthandler.enable(file=handle)
        faulthandler.dump_traceback_later(
            _S04_DIAG_FAULTHANDLER_SECONDS,
            exit=False,
            repeat=True,
            file=handle,
        )
        handle.write("s04-svc: faulthandler armed\n")
        handle.flush()
    except Exception:
        return


def _s04_diag_detail(exc: BaseException) -> str:
    try:
        reason = str(exc).replace("\r", "\\r").replace("\n", "\\n")
    except Exception:
        reason = "unprintable"
    return f"{type(exc).__name__}: {reason[:192]}"


def _greia_log_event(event: str, **fields: object) -> None:
    """Write one bounded, always-on record of an install-transaction event.

    The Session-04 boundary traces above only reach the serial console and only
    when a test marker exists, which is why a refused install on real hardware
    left nothing readable afterwards: the operator had to transcribe the error
    by hand. This is the minimum always-on record needed to diagnose an
    install remotely — op, outcome and the service's own refusal reason — and
    nothing else.

    Deliberately narrow. Nonce, plan digest, settings values and credentials are
    never included, matching :func:`format_log_record`'s discipline; the reason
    is the service's own bounded refusal string. Volume is bounded by the
    request count (roughly four lines per install request), and the endpoint is
    a local one-request-per-connection socket, not a network service.
    """

    parts = [event]
    for key in sorted(fields):
        value = fields[key]
        if value is None:
            continue
        text = str(value).replace("\r", " ").replace("\n", " ")
        if len(text) > 192:
            text = text[:192] + "..."
        parts.append(f"{key}={text}")
    try:
        print("greia-install-tx: " + " ".join(parts), file=sys.stderr, flush=True)
    except (OSError, ValueError):
        return


def _s04_diag_boundary(label: str, *, detail: str | None = None) -> None:
    handle = _S04_DIAG_SERIAL_HANDLE
    if handle is None:
        return
    try:
        suffix = "" if detail is None else f": {detail}"
        handle.write(f"s04-svc: {label}{suffix}\n")
        handle.flush()
    except (OSError, ValueError):
        return


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
    platform_family: str
    architecture: str
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
        _require_bounded_id(self.platform_family, field_name="platform_family")
        _require_bounded_id(self.architecture, field_name="architecture")
        from .disk import POLICY_IDS

        _require_bounded_id(self.target_policy_id, field_name="target_policy_id", allowed=POLICY_IDS)
        _require_bounded_id(
            self.layout_adapter_id, field_name="layout_adapter_id", allowed=ALLOWED_LAYOUT_ADAPTERS
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
            platform_family = raw["platform"]["family"]
            architecture = raw["base"]["architecture"]
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
        if not isinstance(platform_family, str) or not platform_family:
            raise TransactionServiceError("target image profile platform family is invalid")
        if not isinstance(architecture, str) or not architecture:
            raise TransactionServiceError("target image profile architecture is invalid")
        return cls(
            payload=payload,
            payload_digest=payload_digest,
            project_root=project_root,
            compatible_profile_id=profile_id,
            platform_family=platform_family,
            architecture=architecture,
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
#: ``wifi_ssid_hex`` + ``wifi_security`` name the one network the parent joined
#: on the installer's Wi-Fi page (non-secret; see
#: :mod:`greia_installer.wifi_carryover`). Being in the snapshot makes the
#: choice part of the digest-bound plan the parent confirms.
_SETTINGS_ALLOWLIST = (
    _BOOL_SETTINGS_KEYS
    | _FLOAT_SETTINGS_KEYS
    | _TEXT_SETTINGS_KEYS
    | frozenset({"locale"})
    | WIFI_SNAPSHOT_KEYS
)


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
    try:
        wifi_choice = WifiCarryoverChoice.from_snapshot(snapshot)
    except WifiCarryoverError as exc:
        raise TransactionServiceError(f"setting 'wifi' is invalid: {exc}") from exc
    if wifi_choice is not None:
        checked.update(wifi_choice.snapshot_fields())
    for key, value in snapshot.items():
        if key in WIFI_SNAPSHOT_KEYS:
            continue
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


def wifi_carryover_from_snapshot(
    snapshot: Mapping[str, object],
) -> WifiCarryoverChoice | None:
    """Rematerialize the confirmed Wi-Fi carry-over choice (or ``None``)."""
    try:
        return WifiCarryoverChoice.from_snapshot(checked_service_settings(snapshot))
    except WifiCarryoverError as exc:
        raise TransactionServiceError(f"setting 'wifi' is invalid: {exc}") from exc


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
    delegating to :class:`InstallationEngine` (legacy single-partition
    path) or, when :attr:`ab_executor` is configured, to the Phase 8B
    fresh v3-release A/B installer
    (:mod:`greia_installer.fresh_ab_install`), which performs its own
    release/capacity preflight immediately before the first destructive
    command.
    """

    authority: PlatformInstallAuthority
    state: ServiceState
    coordinator: InstallTransactionCoordinator = field(init=False)
    endpoint: InstallTransactionEndpoint = field(init=False)
    _plan_settings: dict[str, dict[str, object]] = field(default_factory=dict)
    _last_installed_identity: str = field(default="")
    #: Wi-Fi carry-over choice of the plan currently executing (set by
    #: :meth:`_consume_authorized_plan`, consumed by the executing path).
    _authorized_wifi_carryover: WifiCarryoverChoice | None = field(default=None)
    #: Production is ``None`` (real :class:`InstallationEngine`). Tests
    #: inject a recording fake so gating is proven with zero disk contact.
    engine_factory: Callable[[], InstallationEngine] | None = None
    #: Phase 8B Step 8B.3 fresh A/B installer (see
    #: :mod:`greia_installer.fresh_ab_install`). When set, socket ``EXECUTE``
    #: routes through the same nonce+digest revalidation and then delegates
    #: destruction to this executor instead of the legacy single-partition
    #: engine. ``None`` preserves the legacy path (existing deployments and
    #: unit harnesses). The executor receives the revalidated
    #: ``(authorization, settings, locale, target)`` and returns an
    #: :class:`InstallResult`; any failure raises fail-closed with no
    #: destructive command issued by this service.
    ab_executor: Callable[[object, HardwareSettings, str, DeviceObservation], InstallResult] | None = None
    #: Explicit install mode bound to the configured executor: ``"ab"`` for
    #: release-capable A/B profiles (requires :attr:`ab_executor`),
    #: ``"legacy-single"`` for legacy/single-root recovery profiles
    #: (requires ``ab_executor=None``; update activation stays disabled via
    #: the ``none-v1`` boot backend). The mode never guesses: a mismatch
    #: refuses at construction so an A/B profile can never be served by the
    #: legacy engine, nor a recovery profile by the A/B executor.
    install_mode: str = "legacy-single"

    #: Capability flag read by :func:`handle_connection`: this service
    #: accepts a ``progress`` writer and streams ``PROGRESS`` frames on the
    #: EXECUTE connection before its final answer (display data only).
    streams_progress = True

    def _new_engine(self) -> InstallationEngine:
        if self.engine_factory is not None:
            return self.engine_factory()
        return InstallationEngine(project_root=self.state.project_root)

    def __post_init__(self) -> None:
        if self.install_mode not in ("ab", "legacy-single"):
            raise TransactionServiceError("install mode must be 'ab' or 'legacy-single'")
        if (self.ab_executor is None) == (self.install_mode == "ab"):
            raise TransactionServiceError(
                "install mode does not match the configured install executor"
            )
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
        self,
        raw: bytes,
        *,
        peer: PeerCredential,
        boot_state: str,
        progress: Callable[[bytes], None] | None = None,
    ) -> bytes:
        """Answer one framed socket request: PREPARE returns a plan.

        ``EXECUTE`` carries nonce+digest only and runs the authorized
        install synchronously in this root process before answering
        ``INSTALLED``: the destructive backend is reachable only through a
        live, revalidated nonce, never as a standalone command surface.

        ``progress``, when given, receives already-framed ``PROGRESS``
        responses (same transaction id as the final answer) while EXECUTE
        runs. It is an output channel only: nothing the UI sends can reach
        it, the frames carry phase/fraction/byte counts and nothing else,
        and :class:`ProgressReporter` rate-limits them and swallows any
        writer failure so a stalled or vanished UI never stops an install.
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
            reporter: ProgressReporter | None = None
            if progress is not None:
                writer = progress

                def emit(payload: Mapping[str, object]) -> None:
                    writer(encode_response(transaction_id, PROGRESS_OP, payload))

                reporter = ProgressReporter(emit)
            if self.ab_executor is not None:
                result = self.execute_ab_install(
                    transaction_nonce=params.get("transaction_nonce"),
                    plan_digest=params.get("plan_digest"),
                    progress=reporter,
                )
            else:
                result = self.execute_and_install(
                    transaction_nonce=params.get("transaction_nonce"),
                    plan_digest=params.get("plan_digest"),
                    on_progress=reporter.engine_progress if reporter is not None else None,
                )
            _ = format_log_record(transaction_id, op, "INSTALLED")
            _greia_log_event("installed", target=self._last_installed_identity)
            installed: dict[str, object] = {
                "status": "INSTALLED",
                "transaction_nonce": str(params.get("transaction_nonce")),
                "plan_digest": str(params.get("plan_digest")),
                "target_identity": self._last_installed_identity,
            }
            if getattr(result, "hardware_detection_incomplete", False) is True:
                # Display-only note for the completion page; never an install fact.
                installed["hardware_detection"] = "incomplete"
            if getattr(result, "wifi_firmware_unavailable", False) is True:
                # Display-only: Wi-Fi chip needs firmware Greia cannot include.
                installed["wifi_firmware"] = "unavailable"
            return encode_response(transaction_id, op, installed)
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
        authorization, settings, locale, target = self._consume_authorized_plan(
            transaction_nonce=transaction_nonce, plan_digest=plan_digest
        )
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
                    wifi_carryover=self._authorized_wifi_carryover,
                ),
                on_progress,  # type: ignore[arg-type]
            )
        except InstallationError as exc:
            raise TransactionServiceError(str(exc)) from exc

    def execute_ab_install(
        self,
        *,
        transaction_nonce: object,
        plan_digest: object,
        progress: ProgressReporter | None = None,
    ) -> InstallResult:
        """Consume a prepared nonce, revalidate everything, then A/B install.

        Phase 8B Step 8B.3 entry: the identical authorization prelude as
        :meth:`execute_and_install` (single-use nonce + digest + inventory
        re-probe, service-held settings, rematerialized target, layout fit),
        then destruction through the configured :attr:`ab_executor` — the
        fresh v3-release A/B installer (see
        :mod:`greia_installer.fresh_ab_install`) — instead of the legacy
        single-partition engine. Requires :attr:`ab_executor`; without one
        this entry refuses with no destructive command.

        ``progress`` is handed to the executor only when the executor
        declares ``accepts_progress`` (the production
        :func:`greia_installer.fresh_ab_install.build_ab_executor` does);
        the authorization prelude above is identical either way.
        """
        authorization, settings, locale, target = self._consume_authorized_plan(
            transaction_nonce=transaction_nonce, plan_digest=plan_digest
        )
        _s04_diag_faulthandler()
        executor = self.ab_executor
        if executor is None:
            raise TransactionServiceError(
                "fresh A/B install is not configured on this service"
            )
        try:
            if getattr(executor, "accepts_wifi_carryover", False):
                return executor(authorization, settings, locale, target, progress=progress, wifi_carryover=self._authorized_wifi_carryover)
            if progress is not None and getattr(executor, "accepts_progress", False):
                return executor(authorization, settings, locale, target, progress=progress)  # type: ignore[call-arg]
            return executor(authorization, settings, locale, target)
        except TransactionServiceError:
            raise
        except InstallTransactionError:
            raise
        except Exception as exc:
            raise TransactionServiceError(f"fresh A/B install refused: {exc}") from exc

    def _consume_authorized_plan(
        self,
        *,
        transaction_nonce: object,
        plan_digest: object,
    ) -> tuple[object, HardwareSettings, str, DeviceObservation]:
        """Consume a prepared nonce and rematerialize the authorized install.

        Shared prelude for the legacy engine path and the fresh A/B path:
        coordinator single-use re-probe, service-held canonical settings
        (never UI bytes), fresh-probe target rematerialization and
        layout-adapter fit proof. Records the installed identity before any
        destructive backend runs. The first failure stops with no
        destructive command issued by this service.
        """
        from .install_transaction import ExecuteAuthorization

        authorization: ExecuteAuthorization = self.coordinator.execute(
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
        # The confirmed network choice comes from the service-held plan, never
        # from EXECUTE bytes (which carry nonce + digest only).
        object.__setattr__(
            self, "_authorized_wifi_carryover", wifi_carryover_from_snapshot(plan_settings)
        )
        target = self.rematerialize_target(authorization.target_identity)
        self._prove_layout_fit(target)
        object.__setattr__(self, "_last_installed_identity", authorization.target_identity)
        return authorization, settings, locale, target

    def _prove_layout_fit(self, target: DeviceObservation) -> None:
        """Prove the release layout plan fits the freshly verified target.

        Runs whenever the state names a registered destructive adapter. A
        single-root recovery profile (pre-A/B adapter outside the
        destructive registry) skips this proof on the explicit
        ``"legacy-single"`` path only: the legacy single-partition engine
        owns its own pre-erase re-verification immediately before the first
        destructive command.
        """
        try:
            adapter = adapter_for(self.state.layout_adapter_id)
        except LayoutError as exc:
            if self.install_mode == "legacy-single":
                return
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
        _s04_diag_faulthandler()
        _s04_diag_boundary("handle_request entered")
        progress_writer = (
            _ConnectionProgressWriter(connection)
            if getattr(service, "streams_progress", False)
            else None
        )
        try:
            if progress_writer is not None:
                response = service.handle_request(
                    raw, peer=peer, boot_state="installer_ready", progress=progress_writer
                )
            else:
                response = service.handle_request(raw, peer=peer, boot_state="installer_ready")
        except (InstallTransactionError, TransactionServiceError, PrivilegedChannelError) as exc:
            _s04_diag_boundary("expected exception caught", detail=_s04_diag_detail(exc))
            _greia_log_event("refused", reason=str(exc)[:256])
            # USB logging must happen while the installer media is still
            # attached; the partially installed OS may be unbootable.
            from .install_diagnostics import publish_install_failure

            usb_log = publish_install_failure(exc)
            reason = str(exc)
            if usb_log:
                reason = f"USB log saved: {usb_log}. {reason}"
            else:
                reason = f"USB log could not be saved. {reason}"
            try:
                _s04_diag_boundary("error response encode starting")
                response = encode_response(
                    new_transaction_id(), "ERROR", {"status": "REFUSED", "reason": reason[:256]}
                )
                _s04_diag_boundary("error response encoded")
            except BaseException as encode_exc:
                _s04_diag_boundary(
                    "error response encode failed", detail=_s04_diag_detail(encode_exc)
                )
                raise
        except BaseException as exc:
            _s04_diag_boundary(
                "UNEXPECTED BASEEXCEPTION ESCAPE", detail=_s04_diag_detail(exc)
            )
            _greia_log_event(
                "unexpected_escape", error=_s04_diag_detail(exc)
            )
            from .install_diagnostics import publish_install_failure

            publish_install_failure(exc)
            raise
        _s04_diag_boundary("handle_request normal response ready")
        try:
            _s04_diag_boundary("sendall starting")
            connection.sendall(response)
            _s04_diag_boundary("sendall completed")
        except (BrokenPipeError, ConnectionResetError) as exc:
            # The caller hung up before the answer was delivered — a UI that
            # timed out, closed early, or was interrupted. That is a normal end
            # to one request, not a service fault. This used to propagate and
            # kill the whole privileged install service with status=1, so a
            # single client hiccup took every later install attempt down with
            # it. The service keeps its own state, so the request's effect is
            # unaffected; only the reply is lost.
            _s04_diag_boundary(
                "client disconnected before reply; request state retained",
                detail=_s04_diag_detail(exc),
            )
            _greia_log_event("client_disconnected_before_reply")
        except BaseException as exc:
            _s04_diag_boundary("sendall failed", detail=_s04_diag_detail(exc))
            raise
    finally:
        try:
            connection.close()
        except OSError:
            pass


class _ConnectionProgressWriter:
    """Writes framed PROGRESS lines to the requesting connection, best effort.

    A UI that stopped reading or hung up must not stall or kill the root
    install: the first failed write (including the connection's bounded
    send timeout) disables the writer for the rest of the request, and the
    final answer is still attempted by :func:`handle_connection`.
    """

    def __init__(self, connection: socket.socket) -> None:
        self._connection = connection
        self._dead = False

    def __call__(self, frame: bytes) -> None:
        if self._dead:
            return
        try:
            self._connection.sendall(frame)
        except (OSError, TimeoutError):
            self._dead = True
            _greia_log_event("progress_reader_gone")


def build_live_service(
    *,
    project_root: Path | None = None,
    ab_seams_factory: object = None,
    ab_identities_factory: object = None,
) -> InstallTransactionService:
    """Compose the production service from Greia-owned environment state.

    Single-root recovery profiles return the explicit legacy service
    (``legacy-single`` mode, no A/B executor). Release-capable A/B profiles
    resolve the A/B executor from the Setup-owned ``GREIA_AB_*``
    environment (see :mod:`greia_installer.composition`); any missing
    element — bundle, key dir, password hash, support bound, block-effect
    seams or observed-identity observation — raises fail-closed here,
    before any socket is served. An A/B profile never silently falls back
    to the legacy single-partition engine. Block-effect factories default
    to the production pair from :mod:`greia_installer.device_seams`
    (device-backed slot storage/filesystem/package installer over the
    rematerialized target, production partition/persist runners, post-layout
    ``blkid`` observer); pass them explicitly only when the device seam or
    a test harness owns them.
    """
    from .composition import (
        AbInstallCompositionError,
        ab_executor_facts_from_environment,
        build_install_service,
        install_mode_for_state,
    )

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
    authority = PlatformInstallAuthority.from_service_state(state)
    try:
        mode = install_mode_for_state(state)
    except AbInstallCompositionError as exc:
        raise TransactionServiceError(str(exc)) from exc
    if mode == "legacy-single":
        return InstallTransactionService(
            authority=authority, state=state, install_mode="legacy-single"
        )
    try:
        _defaulted_seams_factory = ab_seams_factory
        _defaulted_identities_factory = ab_identities_factory
        if _defaulted_seams_factory is None or _defaulted_identities_factory is None:
            # Production default: bind the rematerialized target into fully
            # typed seams from executor facts + service state. Explicit
            # injected factories remain a supported test/harness feature and
            # take precedence wherever supplied. A missing production
            # configuration raises here (fail-closed degraded construction),
            # never a silent legacy fallback.
            from .device_seams import (
                build_production_seam_pair,
                config_from_facts_and_state,
            )

            prod_facts = ab_executor_facts_from_environment(state=state)
            prod_config = config_from_facts_and_state(
                facts=prod_facts,
                hardware_support_pool=state.hardware_support_pool,
            )
            prod_seams, prod_identities = build_production_seam_pair(prod_config)
            if _defaulted_seams_factory is None:
                _defaulted_seams_factory = prod_seams
            if _defaulted_identities_factory is None:
                _defaulted_identities_factory = prod_identities
        return build_install_service(
            state=state,
            authority=authority,
            ab_from_environment=True,
            ab_seams_factory=_defaulted_seams_factory,  # type: ignore[arg-type]
            ab_identities_factory=_defaulted_identities_factory,  # type: ignore[arg-type]
        )
    except AbInstallCompositionError as exc:
        raise TransactionServiceError(str(exc)) from exc


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

