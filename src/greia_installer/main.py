from __future__ import annotations

import argparse
import dataclasses
import enum
import json
import os
import queue
import threading
import time
from dataclasses import dataclass, replace
from enum import Enum, auto
from pathlib import Path
from typing import Any

from greia_platform.display_metrics import (
    DisplayPolicy,
    DisplaySuitability,
    PhysicalUiPolicy,
    filter_supported_modes,
)
from greia_platform.hardware import HardwareDefaults, HardwareSettings
from greia_platform.hardware_session import (
    HardwareSessionController,
    PointerDeviceInfo,
    PointerKind,
    preset_to_speed,
    speed_preset_names,
    speed_to_preset,
)

from greia_platform.keyboard_layout import (
    PROBES,
    _HID_TO_XKB,
    available_layouts,
    infer_layout,
    layout_by_id,
    layout_candidates,
)
from greia_platform.activity_controls import BodyShape
from greia_platform.typography import FontRole, GreiaTypography

from .composition import provisional_installer_hardware_controller
from .disk import (
    BlockDevice,
    DiskProbeError,
    LiveMediaResolver,
    LsblkDiskProbe,
    default_install_target_policy,
)
from .engine import (
    InstallProgress,
    InstallRequest,
    InstallResult,
)
from .install_progress import ProgressFrame, overall_fraction, phase_label
from .power import PowerSupplyProbe
from .presentation import (
    BURGUNDY,
    COCOA,
    DANGER,
    DANGER_PRESSED,
    FIELD,
    FOREST,
    HINT,
    MUTED,
    SUNSHINE,
    SURFACE,
    WARNING_FIELD,
    WHITE,
    InstallerLook,
    keycap,
    mix,
    page_frame,
    step_for_page,
    text_scale,
)
from .transaction_client import (
    InstallTransactionClient,
    PreparedConfirmation,
    TransactionClientError,
    live_target_facts,
    read_compatible_profile_id,
)
from .wifi import IwdWifiBackend, WifiSecurity
from .wifi_setup import DemoWifiBackend, WifiSetupController, WifiSetupPhase
from .wifi_carryover import carryover_snapshot_fields
from .live_ssh import LiveSshToggle


class InstallerPage(Enum):
    WELCOME = auto()
    LAYOUT = auto()
    TARGET = auto()
    POINTER = auto()
    DISPLAY = auto()
    SETTINGS = auto()
    WIFI = auto()
    CONFIRM = auto()
    INSTALLING = auto()
    COMPLETE = auto()
    ERROR = auto()


@dataclass(frozen=True, slots=True)
class WifiAwareInstallResult(InstallResult):
    """Install result that also carries the display-only Wi-Fi firmware note.

    Subclasses the engine result (owned elsewhere) instead of widening it:
    ``isinstance(result, InstallResult)`` keeps holding.
    """

    wifi_firmware_unavailable: bool = False


@dataclass(slots=True)
class InstallerState:
    page: InstallerPage
    targets: tuple[BlockDevice, ...]
    selected_target: int
    settings: HardwareSettings
    progress: InstallProgress
    error: str = ""
    result: InstallResult | None = None

    @property
    def target(self) -> BlockDevice | None:
        if not self.targets or self.selected_target >= len(self.targets):
            return None
        return self.targets[self.selected_target]


class DemoInstallationEngine:
    """Zero-disk simulation emitting the same phase frames as the service."""

    #: (phase, measured steps, seconds per step). Copy and verify report a
    #: measured fraction, like the root service's byte counts.
    SCRIPT: tuple[tuple[str, int, float], ...] = (
        ("check", 1, 0.4),
        ("partition", 1, 0.4),
        ("copy", 8, 0.25),
        ("verify", 4, 0.2),
        ("setup", 1, 0.4),
        ("bootloader", 1, 0.4),
        ("complete", 1, 0.1),
    )

    def install(self, request: InstallRequest, on_progress: Any = None) -> InstallResult:
        callback = on_progress or (lambda _: None)
        for phase, steps, pause in self.SCRIPT:
            for step in range(1, steps + 1):
                measured = step / steps if steps > 1 else None
                callback(_progress_from_frame(ProgressFrame(
                    phase, overall_fraction(phase, measured), measured
                )))
                time.sleep(pause)
        return InstallResult()


def _progress_from_frame(frame: ProgressFrame) -> InstallProgress:
    """UI progress state for one validated service (or demo) frame."""

    return InstallProgress(
        frame.fraction, frame.phase, phase_label(frame.phase), frame.phase_fraction
    )


# Sentinel meaning "no frame has been composed yet". It is deliberately not
# ``None``: an uncomputable render signature also returns ``None``, and
# ``None != None`` is false, which would suppress the redraw that the
# uncomputable case exists to force. See InstallerApplication._render_signature.
_NEVER_RENDERED = object()

# Bounds for the render signature's recursive fingerprint. This runs every
# frame, so nested collections are summarised rather than fully walked.
_SIGNATURE_MAX_DEPTH = 2
_SIGNATURE_MAX_ITEMS = 4

#: Marker file the unprivileged installer UI creates after a successful
#: installation. The root ``greia-installer-finish.path`` unit watches exactly
#: this file and activates one ``systemctl poweroff``. The UI cannot call
#: logind itself (``nobody``, no session, NoNewPrivileges): the direct call was
#: denied and the completion button did nothing (2026-10-18).
POWEROFF_REQUEST_PATH = Path("/run/greia-installer/finish-request")
#: Completion note when a known Wi-Fi chip needs firmware Greia cannot include
#: (Broadcom b43 family, wl-only chips). Translated through ``i18n``.
WIFI_FIRMWARE_UNAVAILABLE_NOTE = (
    "This computer's Wi-Fi chip needs firmware Greia cannot include. "
    "Use an Ethernet cable or a USB Wi-Fi adapter."
)


class InstallerApplication:
    HOLD_SECONDS = 2.0
    # Bounded boot-cover release: at most this many attempts, doubling the
    # delay each time. A helper that keeps failing must not become a busy loop.
    BOOT_HANDOFF_MAX_ATTEMPTS = 4
    BOOT_HANDOFF_RETRY_SECONDS = 0.5
    BUTTON_HEIGHT = 50

    def __init__(
        self,
        *,
        root: Path,
        payload: Path,
        payload_digest: Path | None,
        windowed: bool,
        demo: bool,
        power_probe: PowerSupplyProbe | None = None,
        hardware_controller: HardwareSessionController | None = None,
        transaction_client: InstallTransactionClient | None = None,
        transaction_socket: Path | None = None,
        target_profile: Path | None = None,
    ):
        self.root = root.resolve()
        # Payload paths are retained for the demo simulation only. The
        # production install path never reads them: the root transaction
        # service owns the payload/digest from its own Greia-owned state and
        # the UI travels with nonce+digest alone.
        self.payload = payload.resolve()
        self.payload_digest = (
            payload_digest.resolve() if payload_digest is not None else None
        )
        self.windowed = windowed
        self.demo = demo
        self.transaction_socket = (
            transaction_socket
            or Path(os.environ.get("GREIA_INSTALL_TRANSACTION_SOCKET", ""))
            or None
        )
        self.target_profile = target_profile or Path(
            os.environ.get(
                "GREIA_TARGET_IMAGE_PROFILE",
                "/etc/greia-os/target-image-profile.json",
            )
        )
        self._transaction_client = transaction_client
        if self._transaction_client is None and not self.demo:
            from .transaction_client import (
                DEFAULT_TRANSACTION_SOCKET_PATH,
                EXECUTE_TIMEOUT_SECONDS,
                socket_transport,
            )

            socket_path = self.transaction_socket or DEFAULT_TRANSACTION_SOCKET_PATH
            self._transaction_client = InstallTransactionClient(
                socket_transport(socket_path),
                execute_transport=socket_transport(
                    socket_path, timeout=EXECUTE_TIMEOUT_SECONDS
                ),
            )
        self.power_probe = power_probe or PowerSupplyProbe()
        self.hardware_controller = hardware_controller
        defaults = HardwareDefaults.load(self.root / "runtime" / "hardware-settings.toml")
        settings = HardwareSettings(
            schema_version=defaults.schema_version,
            touchpad_tap=defaults.touchpad_tap,
            touchpad_speed=defaults.touchpad_speed,
            mouse_speed=defaults.mouse_speed,
            natural_scrolling=defaults.natural_scrolling,
            resolution=defaults.resolution,
            keyboard_layout=defaults.keyboard_layout,
            mic_gain=defaults.mic_gain,
            disable_while_typing=defaults.disable_while_typing,
        )
        targets = self._load_targets()
        self.state = InstallerState(
            page=InstallerPage.WELCOME,
            targets=targets,
            selected_target=0,
            settings=settings,
            progress=InstallProgress(0.0, "ready", "Ready"),
        )
        self.available_resolutions = self._available_resolutions()
        self._pointer_focus = 0
        self._pointer_test_hits = 0
        self._pointer_test_feedback = ""
        self._pointer_preview_error = ""
        # Memoised attached-pointer inventory, valid for one page visit. See
        # _pointer_infos(): the legacy-x preview seam answers by spawning a
        # helper process, so probing must not happen once per rendered frame.
        self._pointer_infos_cache: tuple[PointerDeviceInfo, ...] | None = None
        self._pointer_infos_page: InstallerPage | None = None
        # A sentinel, not None: a signature that cannot be computed returns
        # None, and comparing None to None would suppress the very redraw that
        # the None is supposed to force. A unique object can never equal a
        # computed signature, so the first frame always paints and an
        # uncomputable signature always repaints.
        self._last_render_signature: object = _NEVER_RENDERED
        self._status_record: tuple[object, ...] | None = None
        self._cover_released = False
        self._pointer_seen = False
        self._display_probe_cache: Any = None
        self._display_probe_failed = False
        self._refresh_display_cache()
        self.wifi = WifiSetupController(
            DemoWifiBackend() if self.demo else IwdWifiBackend()
        )
        self._live_ssh = LiveSshToggle(self._transaction_client, demo=self.demo)
        self._wifi_ssh_focus = False
        self._events: queue.Queue[InstallProgress | InstallResult | Exception] = (
            queue.Queue()
        )
        self._worker: threading.Thread | None = None
        self._hold_started: float | None = None
        self._buttons: dict[str, Any] = {}
        # Presentation-only state (never part of install logic).
        self._look_cache: InstallerLook | None = None
        self._installing_since: float | None = None
        # When the current phase began and when any progress last arrived
        # (monotonic). A phase that reports nothing for STALL_SECONDS shows
        # its own elapsed time so a long silent step never looks frozen.
        self._phase_since: float | None = None
        self._last_progress_at: float | None = None
        # Erase-confirmation keyboard model: which control has focus on the
        # confirm page ("back" by default; the erase control only after a
        # deliberate Tab/arrow), the source of the current hold, and the
        # keys physically down (a KEYDOWN for a key already down is a
        # repeat and never starts a hold).
        self._confirm_focus = "back"
        # Focus ring is shown only once the parent used the keyboard here, so
        # pointer users never see Back looking "recommended".
        self._confirm_keyboard = False
        self._hold_source = "pointer"
        self._hold_key: int | None = None
        self._keys_down: set[int] = set()
        self._confirm_visit_page: InstallerPage | None = None
        self._wifi_next_page_index = 0
        self._title_px = 37
        self._control_px = 25
        self._body_px = 22
        self._hint_px = 16
        self._exit_requested = False
        self._poweroff_failed = False
        self._boot_released = False
        self._next_boot_handoff_attempt = 0.0
        self._boot_handoff_attempts = 0
        self._layout_probe_results: dict[str, tuple[int, bool]] = {}
        self._layout_candidates: tuple[str, ...] = ("us",)
        self._layout_alternative_index = 0
        self._layout_scroll = 0
        self._layout_selector_forced = False
        self._last_password_character: tuple[str, float] | None = None
        self._last_caret_blink = 0.0
        self._typography = GreiaTypography(
            self.root / "assets" / "fonts" / "nunito-sans"
        )

    def _load_targets(self) -> tuple[BlockDevice, ...]:
        if self.demo:
            return (
                BlockDevice(
                    name="sda",
                    path=Path("/dev/sda"),
                    size_bytes=7_500_000_000,
                    device_type="disk",
                    model="Acer internal drive",
                    serial="DEMO",
                    transport="ata",
                    removable=False,
                    read_only=False,
                    mountpoints=(),
                ),
            )
        try:
            inventory = LsblkDiskProbe().probe()
            ancestry = LiveMediaResolver().resolve(inventory)
            if ancestry.ambiguous:
                return ()
            return inventory.install_targets(
                default_install_target_policy(), excluded=ancestry
            )
        except DiskProbeError:
            return ()

    def _available_resolutions(self) -> tuple[str, ...]:
        if self.demo:
            return ("auto", "800x600", "1024x600", "1024x768")
        probe = getattr(self, "_display_probe_cache", None)
        if probe is None and not getattr(self, "_display_probe_failed", False):
            self._refresh_display_cache()
            probe = getattr(self, "_display_probe_cache", None)
        if probe is None:
            return ("auto",)
        return ("auto", *self._supported_mode_ids(probe))

    @staticmethod
    def _supported_mode_ids(probe: Any) -> tuple[str, ...]:
        """Greia-supported mode ids only, via the shared T01 mode filter."""
        modes = tuple(getattr(probe, "modes", ()) or ())
        if not modes:
            return ()
        metrics = getattr(probe, "metrics", None)
        try:
            if metrics is not None and bool(
                getattr(metrics, "physical_size_known", False)
            ):
                kept = filter_supported_modes(
                    modes,
                    physical_width_mm=metrics.physical_width_mm,
                    physical_height_mm=metrics.physical_height_mm,
                    source=metrics.source,
                    policy=DisplayPolicy.phase0(),
                )
            else:
                kept = filter_supported_modes(
                    modes, policy=DisplayPolicy.phase0()
                )
        except Exception:
            return tuple(dict.fromkeys(mode.mode_id for mode in modes))
        return tuple(dict.fromkeys(mode.mode_id for mode in kept))

    def _probe_display_uncached(self) -> Any | None:
        if self.demo:
            return None
        controller = (
            self.hardware_controller or provisional_installer_hardware_controller()
        )
        try:
            return controller.probe_display()
        except Exception:
            return None

    def _refresh_display_cache(self) -> None:
        probe = self._probe_display_uncached()
        if probe is None:
            if not self.demo:
                self._display_probe_failed = True
            self._display_probe_cache = None
            return
        self._display_probe_cache = probe
        self._display_probe_failed = False

    # --- Pointer setup (T07): capability gating, presets, live preview ------
    # All pointer state lives in ``self.state.settings`` (profile-scoped
    # parent choices). Preview goes through the narrow
    # ``PointerSettingsController.apply_pointer_settings`` seam with semantic
    # settings only and never persists: ``Continue`` carries the values into
    # ``InstallRequest`` through the normal commit path.

    def _pointer_infos(self) -> tuple[PointerDeviceInfo, ...] | None:
        """Backend-neutral pointer facts, or ``None`` when unknown.

        ``None`` means the controller has no pointer seam or probing failed;
        callers fail open (show every control) rather than trapping the
        parent. An empty tuple from a working seam is also treated as
        unknown: no attached pointer was described.

        The probe is memoised for the lifetime of the current page. The
        legacy-x backend answers it by spawning a helper process for the
        device list and again for each device's properties, and
        ``pointer_rows()`` consults it twice. Asking per frame
        meant well over a hundred process spawns per second while the pointer
        page was open, which pinned a full core on the reference Acer and made
        the page feel frozen. Attached-pointer inventory only changes on
        hotplug, so caching per page visit is both correct and cheap; leaving
        the page drops the cache and re-probes.
        """
        if self._pointer_infos_page is self.state.page:
            return self._pointer_infos_cache
        controller = self.hardware_controller
        if controller is None:
            if self.demo:
                return None
            controller = provisional_installer_hardware_controller()
        probe = getattr(controller, "probe_pointers", None)
        if not callable(probe):
            return None
        try:
            infos = probe()
        except Exception:
            return None
        if not isinstance(infos, (tuple, list)):
            return None
        cleaned = tuple(
            info for info in infos if isinstance(info, PointerDeviceInfo)
        )
        result: tuple[PointerDeviceInfo, ...] | None = cleaned if cleaned else None
        self._pointer_infos_cache = result
        self._pointer_infos_page = self.state.page
        return result

    def _has_touchpad(self) -> bool:
        infos = self._pointer_infos()
        if infos is None:
            return True
        return any(info.kind is PointerKind.TOUCHPAD for info in infos)

    def _touchpad_supports(self, capability: str) -> bool:
        """Whether any attached touchpad actually exposes ``capability``.

        Presence of a touchpad is not the same as being able to configure it.
        The legacy-x backend reports, per device, which properties the X
        server really exposes. On the reference Acer's touchpad no tapping
        property is exposed at all, so the backend correctly declines to set
        it, and the backend's "not available" result was being silently
        discarded. Because
        the rows were gated only on "a touchpad exists", the installer offered
        a tap-to-click toggle that could never do anything: it looked live and
        changed nothing. Rows that the hardware cannot honour are now gated on
        the reported capability, and the page says so rather than pretending.
        """
        infos = self._pointer_infos()
        if infos is None:
            return True
        return any(
            info.kind is PointerKind.TOUCHPAD
            and bool(getattr(info.capabilities, capability, False))
            for info in infos
        )

    def _pointer_unavailable_note(self) -> str:
        """One-line explanation for pointer controls this machine cannot set."""
        notes: list[str] = []
        if self._has_touchpad() and not self._touchpad_supports("supports_tap"):
            notes.append("tap to click")
        if (
            self._has_touchpad()
            and not self._touchpad_supports("supports_disable_while_typing")
        ):
            notes.append("disable while typing")
        if not notes:
            return ""
        return "Not adjustable on this touchpad: " + " · ".join(notes)

    def _has_relative_mouse(self) -> bool:
        infos = self._pointer_infos()
        if infos is None:
            return True
        return any(
            info.kind is PointerKind.MOUSE or info.kind is PointerKind.OTHER_RELATIVE
            for info in infos
        )

    def pointer_rows(self) -> tuple[str, ...]:
        """Visible pointer-page rows after capability gating (state, not pixels)."""
        rows: list[str] = []
        if self._touchpad_supports("supports_tap"):
            rows.append("tap")
        if self._touchpad_supports("supports_disable_while_typing"):
            rows.append("disable-while-typing")
        rows.append("natural")
        if self._has_touchpad():
            rows.append("touchpad-preset")
        if self._has_relative_mouse():
            rows.append("mouse-preset")
        elif self._has_touchpad():
            # A touchpad-only station still needs one clearly labeled
            # fallback so an attached mouse later behaves sanely.
            rows.append("mouse-preset-labeled")
        rows.extend(["reset", "test-1", "test-2", "test-3"])
        return tuple(rows)

    def _pointer_focus_rows(self) -> tuple[str, ...]:
        """Keyboard focus order: visible rows plus the Continue step."""
        return (*self.pointer_rows(), "continue")

    def _clamp_pointer_focus(self) -> None:
        rows = self._pointer_focus_rows()
        if self._pointer_focus >= len(rows):
            self._pointer_focus = max(0, len(rows) - 1)
        if self._pointer_focus < 0:
            self._pointer_focus = 0

    def move_pointer_focus(self, delta: int) -> str:
        """Move keyboard focus across visible pointer rows; return the row."""
        self._clamp_pointer_focus()
        rows = self._pointer_focus_rows()
        if rows:
            self._pointer_focus = (self._pointer_focus + delta) % len(rows)
        return rows[self._pointer_focus] if rows else ""

    def focused_pointer_row(self) -> str:
        self._clamp_pointer_focus()
        rows = self._pointer_focus_rows()
        return rows[self._pointer_focus] if rows else ""

    def _preview_pointer_settings(self) -> None:
        """Best-effort live preview through the narrow pointer seam.

        Sends semantic settings only (never display/audio/resolution
        commands — that is the seam's contract). Any failure renders as
        status text; keyboard navigation always keeps working.
        """
        controller: Any = self.hardware_controller
        if controller is None:
            if self.demo:
                self._pointer_preview_error = ""
                return
            controller = provisional_installer_hardware_controller()
        apply = getattr(controller, "apply_pointer_settings", None)
        if not callable(apply):
            self._pointer_preview_error = ""
            return
        try:
            apply(self.state.settings)
        except Exception as exc:
            message = " ".join(str(exc).split()) or exc.__class__.__name__
            self._pointer_preview_error = (
                f"Pointer preview unavailable ({message[:120]})"
            )
            return
        self._pointer_preview_error = ""

    def set_pointer_preset(self, kind: str, preset_name: str) -> float:
        """Apply a friendly T03 speed preset; return the stored speed."""
        speed = preset_to_speed(preset_name)
        if kind == "touchpad":
            self.state.settings = replace(
                self.state.settings, touchpad_speed=speed
            )
        elif kind == "mouse":
            self.state.settings = replace(self.state.settings, mouse_speed=speed)
        else:
            raise KeyError(f"unknown pointer kind: {kind!r}")
        self._preview_pointer_settings()
        return speed

    def cycle_pointer_preset(self, kind: str, delta: int) -> str:
        """Step one preset up/down from the nearest preset; return its name."""
        names = speed_preset_names()
        if kind == "touchpad":
            current = self.state.settings.touchpad_speed
        elif kind == "mouse":
            current = self.state.settings.mouse_speed
        else:
            raise KeyError(f"unknown pointer kind: {kind!r}")
        nearest = speed_to_preset(current)
        index = names.index(nearest)
        chosen = names[(index + delta) % len(names)]
        self.set_pointer_preset(kind, chosen)
        return chosen

    def toggle_pointer_flag(self, name: str) -> bool:
        """Flip one pointer boolean; return the stored value."""
        settings = self.state.settings
        if name == "tap":
            settings = replace(settings, touchpad_tap=not settings.touchpad_tap)
            value = settings.touchpad_tap
        elif name == "natural":
            settings = replace(
                settings, natural_scrolling=not settings.natural_scrolling
            )
            value = settings.natural_scrolling
        elif name == "disable-while-typing":
            settings = replace(
                settings,
                disable_while_typing=not settings.disable_while_typing,
            )
            value = settings.disable_while_typing
        else:
            raise KeyError(f"unknown pointer flag: {name!r}")
        self.state.settings = settings
        self._preview_pointer_settings()
        return value

    def reset_pointer_to_defaults(self) -> None:
        """Restore the pointer subset from the central v2 defaults."""
        defaults = HardwareDefaults.load(
            self.root / "runtime" / "hardware-settings.toml"
        )
        self.state.settings = replace(
            self.state.settings,
            schema_version=defaults.schema_version,
            touchpad_tap=defaults.touchpad_tap,
            touchpad_speed=defaults.touchpad_speed,
            mouse_speed=defaults.mouse_speed,
            natural_scrolling=defaults.natural_scrolling,
            disable_while_typing=defaults.disable_while_typing,
        )
        self._pointer_test_feedback = "Pointer feel reset"
        self._preview_pointer_settings()

    def hit_pointer_test_target(self, target: str) -> int:
        """Record one test-target hit with click feedback; return the count."""
        if target not in {"test-1", "test-2", "test-3"}:
            raise KeyError(f"unknown pointer test target: {target!r}")
        self._pointer_test_hits += 1
        self._pointer_test_feedback = (
            f"Nice click! ({self._pointer_test_hits})"
        )
        return self._pointer_test_hits

    def activate_pointer_focus(self) -> str:
        """Activate the focused pointer row for keyboard-only completion."""
        row = self.focused_pointer_row()
        if row in {"tap", "natural", "disable-while-typing"}:
            self.toggle_pointer_flag(row)
        elif row == "touchpad-preset":
            self.cycle_pointer_preset("touchpad", 1)
        elif row in {"mouse-preset", "mouse-preset-labeled"}:
            self.cycle_pointer_preset("mouse", 1)
        elif row == "reset":
            self.reset_pointer_to_defaults()
        elif row in {"test-1", "test-2", "test-3"}:
            self.hit_pointer_test_target(row)
        elif row == "continue":
            self._activate_primary()
        return row

    # --- Display page (T07): supported modes, physical facts, gating --------

    def display_facts(self) -> dict[str, Any]:
        """Semantic display facts for the Display page (state, not pixels)."""
        probe = self._display_probe_cache
        modes = tuple(getattr(probe, "modes", ()) or ()) if probe is not None else ()
        supported_ids = self._supported_mode_ids(probe) if probe is not None else ()
        metrics = getattr(probe, "metrics", None) if probe is not None else None
        current_id = self.state.settings.resolution
        described = metrics
        if described is None and modes:
            from greia_platform.display_metrics import (
                current_mode,
                sanitize_display_metrics,
            )

            if current_id != "auto":
                chosen = next(
                    (mode for mode in modes if mode.mode_id == current_id), None
                )
            else:
                chosen = None
            if chosen is None:
                chosen = current_mode(modes)
            if chosen is not None:
                described = sanitize_display_metrics(chosen.width, chosen.height)
        verdict: DisplaySuitability | None = None
        if described is not None:
            try:
                verdict = DisplayPolicy.phase0().evaluate(described)
            except (TypeError, ValueError):
                verdict = None
        return {
            "current_resolution": current_id,
            "supported_mode_ids": supported_ids,
            "metrics": metrics,
            "described_metrics": described,
            "verdict": verdict,
            "probe_failed": self._display_probe_failed and probe is None,
        }

    def display_status_copy(self) -> str:
        """Parent-friendly suitability line for the current display."""
        facts = self.display_facts()
        verdict = facts["verdict"]
        metrics = facts["metrics"]
        if verdict in {
            DisplaySuitability.UNSUPPORTED_PIXEL_ENVELOPE,
            DisplaySuitability.UNSUPPORTED_ORIENTATION,
            DisplaySuitability.UNSUPPORTED_PHYSICAL_SIZE,
        }:
            return "This screen is not fully supported — safe pixels are used"
        if verdict is None or facts["probe_failed"] or metrics is None:
            return "Safe display: installer uses safe pixels (1024x600)"
        if verdict in {
            DisplaySuitability.SUPPORTED,
            DisplaySuitability.SUPPORTED_WITH_REFLOW,
        }:
            if bool(getattr(metrics, "physical_size_known", False)):
                return "Screen size detected automatically"
            return "Safe display: installer uses safe pixels (1024x600)"
        if verdict is DisplaySuitability.UNKNOWN_PHYSICAL_SIZE:
            return "Safe display: installer uses safe pixels (1024x600)"
        return "This screen is not fully supported — safe pixels are used"

    def display_install_block_reason(self) -> str | None:
        """Destructive-install gate for a provably unsupported display."""
        facts = self.display_facts()
        verdict = facts["verdict"]
        if verdict in {
            DisplaySuitability.UNSUPPORTED_PIXEL_ENVELOPE,
            DisplaySuitability.UNSUPPORTED_ORIENTATION,
            DisplaySuitability.UNSUPPORTED_PHYSICAL_SIZE,
        }:
            return (
                "This screen is not fully supported — "
                "installation to the internal disk is paused. "
                "Ask a grown-up to try a supported screen."
            )
        return None

    def essential_control_px(self, fallback_px: int) -> int:
        """T01 physical floor for essential installer controls.

        Uses a 9 mm touch minimum against trustworthy probe metrics and
        falls back to the caller-supplied pixel value otherwise; always
        within 8..320 px. This never scales a layout.
        """
        metrics = getattr(self._display_probe_cache, "metrics", None)
        try:
            return PhysicalUiPolicy.minimum_pixels(
                9.0, fallback_px=fallback_px, metrics=metrics
            )
        except Exception:
            return max(8, min(320, int(fallback_px)))

    def build_install_request(self, target: Any, wifi_profile: Any = None) -> Any:
        """Single commit path for the demo simulation: live settings carried.

        Production installs never build this object: they travel through
        the transaction client as identity digest + settings snapshot
        (:meth:`settings_snapshot_for_service`). Retained because the demo
        simulation and its pinned regression exercise it.
        """
        return InstallRequest(
            target=target,
            payload=self.payload,
            payload_digest=self.payload_digest,
            hardware_settings=self.state.settings,
            wifi_profile=wifi_profile if wifi_profile is not None else self.wifi.profile,
        )

    def _snapshot_locale(self) -> str:
        """Locale carried in the service settings snapshot (base default)."""
        return "en"

    def settings_snapshot_for_service(self) -> dict[str, str]:
        """Bounded semantic preference scalars for ``PREPARE_PLAN``.

        Booleans/numbers render as canonical text; only allowlisted keys
        travel (see ``transaction_service.checked_service_settings``). No
        paths, devices, commands or credentials are ever included.
        """
        settings = self.state.settings
        return {
            "touchpad_tap": "true" if settings.touchpad_tap else "false",
            "touchpad_speed": repr(float(settings.touchpad_speed)),
            "mouse_speed": repr(float(settings.mouse_speed)),
            "natural_scrolling": "true" if settings.natural_scrolling else "false",
            "resolution": str(settings.resolution),
            "keyboard_layout": str(settings.keyboard_layout),
            "mic_gain": repr(float(settings.mic_gain)),
            "disable_while_typing": (
                "true" if settings.disable_while_typing else "false"
            ),
            "locale": self._snapshot_locale(),
            # The network joined on the Wi-Fi page (SSID hex + security only,
            # never the passphrase): the root service copies that one iwd
            # profile into the installed system.
            **carryover_snapshot_fields(self.wifi.profile),
        }

    def read_live_confirmation_facts(self) -> dict[str, dict[str, object]]:
        """Fresh read-only inventory projected to safe confirmation facts.

        ``lsblk`` observation only: this never opens or writes a disk, it
        only re-reads which identity digests are still present and
        eligible so a changed inventory invalidates the confirmation.
        """
        try:
            inventory = LsblkDiskProbe().probe()
            ancestry = LiveMediaResolver().resolve(inventory)
        except DiskProbeError:
            return {}
        if ancestry.ambiguous:
            return {}
        policy = default_install_target_policy()
        facts: dict[str, dict[str, object]] = {}
        for device in inventory.devices:
            if device.device_type != "disk":
                continue
            if device.name in ancestry.whole_disk_names:
                facts[device.identity_digest] = {
                    "eligible": False,
                    "display_summary": device.display_name,
                }
                continue
            facts[device.identity_digest] = {
                "eligible": policy.evaluate(device).eligible,
                "display_summary": device.display_name,
            }
        return facts

    def run(self) -> int:
        import pygame

        os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
        pygame.init()
        pygame.font.init()
        pygame.key.start_text_input()
        flags = pygame.RESIZABLE if self.windowed else pygame.FULLSCREEN
        size = (1024, 600) if self.windowed else (0, 0)
        screen = pygame.display.set_mode(size, flags)
        pygame.display.set_caption("Install Greia OS")
        pygame.mouse.set_visible(False)
        clock = pygame.time.Clock()
        frame_budget = 1.0 / 30.0
        running = True
        while running and not self._exit_requested:
            frame_started = time.monotonic()
            self._drain_worker_events()
            self.wifi.drain()
            self._live_ssh.drain()
            self._write_status_record()
            handled_event = False
            for event in pygame.event.get():
                handled_event = True
                if event.type == pygame.QUIT and self.windowed:
                    running = False
                elif event.type == pygame.TEXTINPUT:
                    self._handle_text_input(event.text)
                elif event.type == pygame.KEYDOWN:
                    fresh = self._note_key_down(event)
                    self._handle_keydown(event, pygame)
                    if self._handle_confirm_key(event.key, pygame, fresh=fresh):
                        continue
                    running = self._handle_key(event.key, pygame)
                elif event.type == pygame.KEYUP:
                    self._note_key_up(event.key)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self._handle_mouse_down(event.pos)
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    self._handle_mouse_up(event.pos)
            self._update_install_hold(pygame)
            # Repaint only when the composed frame could actually differ, or
            # when this tick handled input. Skipping is a pure optimisation:
            # any signature that cannot be computed still repaints.
            signature = self._render_signature(screen)
            if handled_event or signature != self._last_render_signature:
                self._draw(screen, pygame)
                self._draw_pointer(screen, pygame)
                pygame.display.flip()
                self._last_render_signature = signature
            if not self.windowed and os.environ.get("PIP_SKIP_BOOT_HANDOFF") != "1":
                self._release_boot_cover_once()
            clock.tick(30)
            # Some low-end X/framebuffer configurations do not throttle via
            # pygame's Clock (SDL_Delay no-ops), which would otherwise spin the
            # CPU at 100%. Guarantee a frame budget with a wall-clock sleep.
            elapsed = time.monotonic() - frame_started
            remaining = frame_budget - elapsed
            if remaining > 0:
                time.sleep(remaining)
        pygame.key.stop_text_input()
        pygame.quit()
        return 0

    def _handle_text_input(self, text: str) -> None:
        if self.state.page != InstallerPage.WIFI or self._wifi_ssh_focus:
            return
        network = self.wifi.snapshot.selected_network
        if network is not None and network.security is WifiSecurity.PERSONAL:
            self.wifi.append_password(text)
            if text:
                self._last_password_character = (
                    text[-1],
                    time.monotonic(),
                )

    def _handle_keydown(self, event: Any, pygame: Any) -> None:
        if self.state.page != InstallerPage.LAYOUT:
            return
        scancode = int(getattr(event, "scancode", -1))
        modifiers = int(getattr(event, "mod", 0)) or int(pygame.key.get_mods())
        shift_held = bool(modifiers & pygame.KMOD_SHIFT)
        keycode_name = _HID_TO_XKB.get(scancode)
        if not keycode_name:
            return
        # The parent was asked to press the physical key that types the probe
        # character on THEIR keyboard. Whatever the active layout produced is
        # irrelevant (it may be wrong); the physical scancode is layout-
        # independent and is the signal we score.
        for probe in PROBES:
            if probe.character in self._layout_probe_results:
                continue
            self._layout_probe_results[probe.character] = (
                scancode,
                shift_held,
                "",
            )
            self._refresh_layout_candidates()
            return

    def _refresh_layout_candidates(self) -> None:
        self._layout_candidates = layout_candidates(self._layout_probe_results)
        self._layout_alternative_index = 0
        inferred = infer_layout(self._layout_probe_results)
        all_ids = self._all_layout_ids
        if inferred in all_ids:
            self._layout_alternative_index = all_ids.index(inferred)
        self._layout_scroll = 0

    def _move_layout_selection(self, delta: int) -> None:
        all_ids = self._all_layout_ids
        if not all_ids:
            return
        self._layout_alternative_index = (
            self._layout_alternative_index + delta
        ) % len(all_ids)

    def _confirm_layout(self) -> None:
        all_ids = self._all_layout_ids
        if not all_ids:
            return
        index = min(self._layout_alternative_index, len(all_ids) - 1)
        layout_id = all_ids[index]
        self.state.settings = replace(self.state.settings, keyboard_layout=layout_id)
        self._apply_keyboard_layout(layout_id)
        self.state.page = InstallerPage.TARGET

    @property
    def _all_layout_ids(self) -> tuple[str, ...]:
        return tuple(layout.id for layout in available_layouts())

    def _layout_scroll_to(self, index: int, rows_visible: int) -> None:
        if index < self._layout_scroll:
            self._layout_scroll = index
        elif index >= self._layout_scroll + rows_visible:
            self._layout_scroll = index - rows_visible + 1

    def _apply_keyboard_layout(self, layout_id: str) -> None:
        import subprocess

        try:
            subprocess.run(
                ["setxkbmap", layout_id],
                check=False,
                shell=False,
                stdin=subprocess.DEVNULL,
            )
        except OSError:
            pass

    def _handle_key(self, key: int, pygame: Any) -> bool:
        if self.state.page == InstallerPage.LAYOUT:
            if key == pygame.K_ESCAPE:
                self._back()
            elif len(self._layout_probe_results) >= 5:
                if key == pygame.K_UP:
                    self._move_layout_selection(-1)
                elif key == pygame.K_DOWN:
                    self._move_layout_selection(1)
                elif key in {pygame.K_RETURN, pygame.K_SPACE}:
                    self._confirm_layout()
            elif key in {pygame.K_RETURN, pygame.K_SPACE} and len(
                self._layout_probe_results
            ) >= 3:
                # Enough probes to show a useful selector; jump to it early if
                # the parent cannot type the remaining characters.
                self._layout_selector_forced = True
                self._refresh_layout_candidates()
            return True
        if self.state.page == InstallerPage.WIFI:
            if key == pygame.K_ESCAPE:
                self._back()
            elif key == pygame.K_TAB:
                self._wifi_ssh_focus = not self._wifi_ssh_focus
            elif self._wifi_ssh_focus and key in {pygame.K_RETURN, pygame.K_SPACE}:
                self._live_ssh.toggle()
            elif key == pygame.K_UP:
                self._wifi_ssh_focus = False
                self.wifi.move_selection(-1)
            elif key == pygame.K_DOWN:
                self._wifi_ssh_focus = False
                self.wifi.move_selection(1)
            elif self._wifi_ssh_focus:
                return True
            elif key == pygame.K_BACKSPACE:
                self.wifi.backspace_password()
                self._last_password_character = None
            elif key == pygame.K_r:
                self.wifi.refresh()
            elif key == pygame.K_RETURN:
                self._activate_primary()
            return True
        if self.state.page == InstallerPage.POINTER:
            if key == pygame.K_ESCAPE:
                self._back()
            elif key == pygame.K_UP:
                self.move_pointer_focus(-1)
            elif key == pygame.K_DOWN:
                self.move_pointer_focus(1)
            elif key in {pygame.K_LEFT, pygame.K_RIGHT}:
                row = self.focused_pointer_row()
                delta = -1 if key == pygame.K_LEFT else 1
                if row == "touchpad-preset":
                    self.cycle_pointer_preset("touchpad", delta)
                elif row in {"mouse-preset", "mouse-preset-labeled"}:
                    self.cycle_pointer_preset("mouse", delta)
                else:
                    self.move_pointer_focus(delta)
            elif key in {pygame.K_1, pygame.K_2, pygame.K_3}:
                index = {pygame.K_1: 1, pygame.K_2: 2, pygame.K_3: 3}[key]
                self.hit_pointer_test_target(f"test-{index}")
            elif key == pygame.K_r:
                self.reset_pointer_to_defaults()
            elif key in {pygame.K_RETURN, pygame.K_SPACE}:
                self.activate_pointer_focus()
            return True
        if self.state.page == InstallerPage.DISPLAY:
            if key == pygame.K_ESCAPE:
                self._back()
            elif key in {pygame.K_RETURN, pygame.K_SPACE}:
                self._activate_primary()
            elif key == pygame.K_r:
                self._cycle_resolution()
            return True
        if key in {pygame.K_RETURN, pygame.K_SPACE}:
            self._activate_primary()
        elif key == pygame.K_ESCAPE and self.state.page not in {
            InstallerPage.INSTALLING,
            InstallerPage.COMPLETE,
        }:
            self._back()
        return True

    def _activate_primary(self) -> None:
        if self.state.page == InstallerPage.WELCOME:
            self.state.page = InstallerPage.LAYOUT
            self._layout_probe_results = {}
            self._layout_candidates = ("us",)
            self._layout_alternative_index = 0
        elif self.state.page == InstallerPage.LAYOUT:
            self._confirm_layout()
        elif self.state.page == InstallerPage.TARGET and self.state.target:
            # A "disk changed" notice belongs to the selection it rejected.
            self.state.error = ""
            self.state.page = InstallerPage.POINTER
            self._pointer_focus = 0
            self._pointer_test_feedback = ""
            self._preview_pointer_settings()
        elif self.state.page == InstallerPage.POINTER:
            self._refresh_display_cache()
            self.state.page = InstallerPage.DISPLAY
        elif self.state.page == InstallerPage.DISPLAY:
            self.state.page = InstallerPage.WIFI
            self._wifi_ssh_focus = False
            self._live_ssh.refresh()
            self.wifi.begin()
        elif self.state.page == InstallerPage.SETTINGS:
            # Legacy combined page (superseded by POINTER + DISPLAY).
            self.state.page = InstallerPage.WIFI
            self._wifi_ssh_focus = False
            self._live_ssh.refresh()
            self.wifi.begin()
        elif self.state.page == InstallerPage.WIFI:
            snapshot = self.wifi.snapshot
            if snapshot.phase in {WifiSetupPhase.CONNECTED, WifiSetupPhase.UNAVAILABLE}:
                self.state.page = InstallerPage.CONFIRM
            elif snapshot.selected_network is None:
                self.wifi.skip()
                self.state.page = InstallerPage.CONFIRM
            else:
                self.wifi.connect()
        elif self.state.page == InstallerPage.COMPLETE:
            if self.demo:
                self._exit_requested = True
            else:
                self._request_poweroff()

    def _request_poweroff(self) -> None:
        """Ask the machine to power off through the root finish-marker path.

        The installer UI is unprivileged and has no logind session, so a
        direct ``systemctl poweroff`` is denied by logind/polkit. The UI owns
        its runtime directory, so it drops the marker file that the root
        ``greia-installer-finish.path`` unit watches; that unit runs exactly
        one ``systemctl poweroff`` as root. If the marker cannot be written,
        the completion page shows the manual fallback instead of a dead
        button.
        """

        try:
            POWEROFF_REQUEST_PATH.write_text("poweroff\n", encoding="ascii")
        except OSError:
            self._poweroff_failed = True
        else:
            self._poweroff_failed = False

    def _back(self) -> None:
        page = self.state.page
        if page == InstallerPage.TARGET:
            self.state.page = InstallerPage.LAYOUT
            self._layout_probe_results = {}
            self._layout_candidates = ("us",)
            self._layout_alternative_index = 0
        elif page == InstallerPage.LAYOUT:
            self.state.page = InstallerPage.WELCOME
        elif page == InstallerPage.SETTINGS:
            # Legacy combined page (superseded by POINTER + DISPLAY).
            self.state.page = InstallerPage.TARGET
        elif page == InstallerPage.POINTER:
            self.state.page = InstallerPage.TARGET
        elif page == InstallerPage.DISPLAY:
            self.state.page = InstallerPage.POINTER
            self._pointer_focus = 0
        elif page == InstallerPage.WIFI:
            # Leaving this stage means no in-flight scan/connection may later
            # become the parent's chosen installation profile.
            self.wifi.skip()
            self.state.page = InstallerPage.DISPLAY
        elif page == InstallerPage.CONFIRM:
            # Back from final confirmation means the parent wants to reconsider
            # Wi-Fi, so discard the accepted profile and present a fresh scan.
            self.state.page = InstallerPage.WIFI
            self.wifi.refresh()
        elif page == InstallerPage.ERROR:
            self.state.page = InstallerPage.CONFIRM

    def _handle_mouse_down(self, position: tuple[int, int]) -> None:
        if self.state.page == InstallerPage.CONFIRM and self._inside(
            "install", position
        ):
            self._hold_source = "pointer"
            self._hold_key = None
            self._hold_started = time.monotonic()

    # -- erase confirmation: keyboard equivalent of the pointer hold ----------
    #
    # Same 2-second hold, same fill, same revalidation (the hold only ever
    # calls _start_installation, which re-probes power, display and the
    # selected disk). Extra keyboard safety: focus must be on the erase
    # control (never the default), the Enter/Space press must be a fresh
    # press on this page (a key already down — auto-repeat, or a key still
    # held from the previous page — never starts a hold), and releasing the
    # key, any other key, or leaving the page cancels.

    HOLD_KEYS_NAMES = ("K_RETURN", "K_KP_ENTER", "K_SPACE")
    FOCUS_KEYS_NAMES = ("K_TAB", "K_LEFT", "K_RIGHT", "K_UP", "K_DOWN")

    def _note_key_down(self, event: Any) -> bool:
        """Track physical key state; True only for a fresh (non-repeat) press."""

        key = int(getattr(event, "key", -1))
        fresh = key not in self._keys_down and not getattr(event, "repeat", False)
        self._keys_down.add(key)
        if len(self._keys_down) > 32:
            # A lost KEYUP (focus change) must not grow this without bound.
            self._keys_down = {key}
        return fresh

    def _note_key_up(self, key: int) -> None:
        self._keys_down.discard(int(key))
        if self._hold_source == "key" and self._hold_key == int(key):
            self._cancel_hold()

    def _cancel_hold(self) -> None:
        self._hold_started = None
        self._hold_source = "pointer"
        self._hold_key = None

    def _sync_confirm_visit(self) -> None:
        """Reset confirm-page focus and any hold when the page is (re)entered."""

        page = self.state.page
        if page == self._confirm_visit_page:
            return
        self._confirm_visit_page = page
        self._confirm_focus = "back"
        self._confirm_keyboard = False
        if self._hold_source == "key":
            self._cancel_hold()

    def _handle_confirm_key(self, key: int, pygame: Any, *, fresh: bool) -> bool:
        """Confirm-page keys; True when consumed (generic handling skipped)."""

        self._sync_confirm_visit()
        if self.state.page != InstallerPage.CONFIRM:
            return False
        hold_keys = {getattr(pygame, name) for name in self.HOLD_KEYS_NAMES if hasattr(pygame, name)}
        focus_keys = {getattr(pygame, name) for name in self.FOCUS_KEYS_NAMES if hasattr(pygame, name)}
        if self._hold_source == "key" and key != self._hold_key:
            # Any other key during a keyboard hold cancels it.
            self._cancel_hold()
        if key in focus_keys:
            if fresh:
                self._confirm_focus = "install" if self._confirm_focus == "back" else "back"
                self._confirm_keyboard = True
            return True
        if key in hold_keys:
            if not fresh:
                return True
            if self._confirm_focus == "install":
                self._hold_source = "key"
                self._hold_key = key
                self._hold_started = time.monotonic()
            elif not self._confirm_keyboard:
                # First Enter/Space only reveals where focus is (Back).
                self._confirm_keyboard = True
            else:
                self._back()
            return True
        return False

    def _handle_mouse_up(self, position: tuple[int, int]) -> None:
        if self._inside("back", position):
            self._cancel_hold()
            self._back()
            return
        if self.state.page == InstallerPage.CONFIRM:
            self._cancel_hold()
            return
        if self.state.page == InstallerPage.LAYOUT:
            if self._inside("primary", position):
                self._confirm_layout()
                return
            for index in range(len(self._all_layout_ids)):
                if self._inside(f"layout-{index}", position):
                    self._layout_alternative_index = index
                    return
            return
        if self.state.page == InstallerPage.WIFI:
            if self._inside("wifi-ssh", position):
                self._wifi_ssh_focus = True
                self._live_ssh.toggle()
                return
            self._wifi_ssh_focus = False
            if self._inside("wifi-refresh", position):
                self.wifi.refresh()
                return
            if self._inside("wifi-skip", position):
                self.wifi.skip()
                self.state.page = InstallerPage.CONFIRM
                return
            if self._inside("wifi-more", position):
                # Presentation paging only: select the first network of the
                # next page so a pointer-only parent can reach every network.
                self.wifi.select(self._wifi_next_page_index)
                return
            for index in range(len(self.wifi.snapshot.networks)):
                if self._inside(f"wifi-{index}", position):
                    self.wifi.select(index)
                    return
        if self.state.page == InstallerPage.POINTER:
            self._handle_pointer_click(position)
        elif self.state.page == InstallerPage.DISPLAY:
            if self._inside("resolution", position):
                self._cycle_resolution()
        if self._inside("primary", position):
            self._activate_primary()
            return
        if self.state.page == InstallerPage.TARGET:
            for index in range(len(self.state.targets)):
                if self._inside(f"target-{index}", position):
                    self.state.selected_target = index
        elif self.state.page == InstallerPage.SETTINGS:
            self._handle_settings_click(position)

    def _update_install_hold(self, pygame: Any) -> None:
        """Require one uninterrupted hold (pointer inside, or key on focus)."""

        self._sync_confirm_visit()
        if self._hold_started is None:
            return
        if self.state.page != InstallerPage.CONFIRM:
            self._cancel_hold()
            return
        if self._hold_source == "key":
            if (
                self._confirm_focus != "install"
                or self._hold_key is None
                or self._hold_key not in self._keys_down
                or not self._key_still_pressed(pygame, self._hold_key)
            ):
                self._cancel_hold()
                return
        else:
            pressed = pygame.mouse.get_pressed(num_buttons=3)
            position = pygame.mouse.get_pos()
            if not pressed[0] or not self._inside("install", position):
                self._cancel_hold()
                return
        if time.monotonic() - self._hold_started >= self.HOLD_SECONDS:
            self._cancel_hold()
            self._start_installation()

    @staticmethod
    def _key_still_pressed(pygame: Any, key: int) -> bool:
        """Cross-check our KEYUP tracking against SDL's live keyboard state.

        A KEYUP can be lost (window focus change); SDL's state cannot lie
        about a released key. Unknown/unavailable state defers to tracking.
        """

        getter = getattr(getattr(pygame, "key", None), "get_pressed", None)
        if getter is None:
            return True
        try:
            return bool(getter()[key])
        except Exception:  # noqa: BLE001 - no keyboard state on this backend
            return True

    def _cycle_resolution(self) -> None:
        if not self.available_resolutions:
            return
        try:
            current = self.available_resolutions.index(self.state.settings.resolution)
        except ValueError:
            current = 0
        self.state.settings = replace(
            self.state.settings,
            resolution=self.available_resolutions[
                (current + 1) % len(self.available_resolutions)
            ],
        )

    def _handle_pointer_click(self, position: tuple[int, int]) -> None:
        if self._inside("tap", position):
            self.toggle_pointer_flag("tap")
            return
        if self._inside("natural", position):
            self.toggle_pointer_flag("natural")
            return
        if self._inside("disable-while-typing", position):
            self.toggle_pointer_flag("disable-while-typing")
            return
        if self._inside("touch-minus", position):
            self.cycle_pointer_preset("touchpad", -1)
            return
        if self._inside("touch-plus", position):
            self.cycle_pointer_preset("touchpad", 1)
            return
        if self._inside("mouse-minus", position):
            self.cycle_pointer_preset("mouse", -1)
            return
        if self._inside("mouse-plus", position):
            self.cycle_pointer_preset("mouse", 1)
            return
        if self._inside("pointer-reset", position):
            self.reset_pointer_to_defaults()
            return
        for target in ("test-1", "test-2", "test-3"):
            if self._inside(target, position):
                self.hit_pointer_test_target(target)
                return

    def _handle_settings_click(self, position: tuple[int, int]) -> None:
        # Legacy combined page (superseded by POINTER + DISPLAY).
        settings = self.state.settings
        if self._inside("tap", position):
            self.toggle_pointer_flag("tap")
        elif self._inside("natural", position):
            self.toggle_pointer_flag("natural")
        elif self._inside("mouse-minus", position):
            self.cycle_pointer_preset("mouse", -1)
        elif self._inside("mouse-plus", position):
            self.cycle_pointer_preset("mouse", 1)
        elif self._inside("touch-minus", position):
            self.cycle_pointer_preset("touchpad", -1)
        elif self._inside("touch-plus", position):
            self.cycle_pointer_preset("touchpad", 1)
        elif self._inside("resolution", position):
            self._cycle_resolution()
        else:
            self.state.settings = settings

    def _transaction_client_or_error(self) -> InstallTransactionClient | None:
        """Return the UI transaction client, or fail closed to the error page."""
        if self._transaction_client is not None:
            return self._transaction_client
        self.state.error = "The install service is unavailable; installation stopped"
        self.state.page = InstallerPage.ERROR
        return None

    def _checked_hold_target(self) -> BlockDevice | None:
        """Re-probe read-only inventory and require the selection to survive.

        Any inventory refresh or material target-state change since the
        confirm page was shown invalidates the confirmation fail-closed:
        the parent returns to target selection and no nonce is prepared.
        """
        target = self.state.target
        if target is None:
            self.state.error = "No disk is selected; installation stopped"
            self.state.page = InstallerPage.ERROR
            return None
        facts = self.read_live_confirmation_facts()
        live = facts.get(target.identity_digest)
        if not isinstance(live, dict) or live.get("eligible") is not True:
            self.state.error = (
                "The selected disk changed; choose the internal disk again"
            )
            self.state.page = InstallerPage.TARGET
            self.state.targets = self._load_targets()
            self.state.selected_target = 0
            return None
        return target

    def _start_installation(self) -> None:
        target = self.state.target
        if target is None or self._worker is not None:
            return
        display_block = self.display_install_block_reason()
        if display_block:
            self.state.error = display_block
            self.state.page = InstallerPage.ERROR
            return
        power_problem = self.power_probe.installation_block_reason()
        if power_problem:
            self.state.error = power_problem
            self.state.page = InstallerPage.ERROR
            return
        self.state.error = ""
        self.state.result = None
        self.state.page = InstallerPage.INSTALLING
        if self.demo:
            # Demo simulation only: timed stages, zero disk contact. The
            # production path below never constructs an engine or a request.
            engine: Any = DemoInstallationEngine()
            request = self.build_install_request(target)

            def demo_worker() -> None:
                try:
                    result = engine.install(request, self._events.put)
                    self._events.put(result)
                except Exception as exc:
                    self._events.put(exc)

            self._worker = threading.Thread(
                target=demo_worker, name="greia-installer", daemon=True
            )
            self._worker.start()
            return
        # Production path (8A.5 split): the unprivileged UI only prepares a
        # plan by identity digest and executes nonce+digest. Every
        # destructive command runs in the root transaction service after it
        # revalidates the plan against fresh Greia-owned state.
        held = self._checked_hold_target()
        if held is None:
            return
        client = self._transaction_client_or_error()
        if client is None:
            return
        try:
            profile_id = read_compatible_profile_id(self.target_profile)
        except TransactionClientError as exc:
            self.state.error = str(exc)
            self.state.page = InstallerPage.ERROR
            return
        snapshot = self.settings_snapshot_for_service()
        identity = held.identity_digest
        display = held.display_name

        def worker() -> None:
            try:
                self._events.put(
                    InstallProgress(0.02, "prepare", "Confirming the selected disk")
                )
                prepared = client.prepare(
                    expected_target_identity=identity,
                    compatible_profile_id=profile_id,
                    settings_snapshot=snapshot,
                )
                confirmation = PreparedConfirmation(
                    prepared=prepared,
                    expected_target_identity=identity,
                    expected_display_summary=display,
                    settings_snapshot=dict(snapshot),
                )
                live = self.read_live_confirmation_facts()
                if not confirmation.still_valid(
                    live_targets=live, current_settings=self.settings_snapshot_for_service()
                ):
                    raise TransactionClientError(
                        "the selected disk changed; confirmation invalidated"
                    )
                self._events.put(
                    InstallProgress(0.04, "prepare", "Confirming the selected disk")
                )
                receipt = client.execute(
                    transaction_nonce=prepared.transaction_nonce,
                    plan_digest=prepared.plan_digest,
                    # Validated display-only frames from the root service.
                    on_progress=lambda frame: self._events.put(_progress_from_frame(frame)),
                )
                self._events.put(
                    WifiAwareInstallResult(
                        hardware_detection_incomplete=bool(
                            getattr(receipt, "hardware_detection_incomplete", False)
                        ),
                        wifi_firmware_unavailable=bool(
                            getattr(receipt, "wifi_firmware_unavailable", False)
                        ),
                    )
                )
            except Exception as exc:
                self._events.put(exc)

        self._worker = threading.Thread(
            target=worker, name="greia-installer", daemon=True
        )
        self._worker.start()

    def _drain_worker_events(self) -> None:
        while True:
            try:
                event = self._events.get_nowait()
            except queue.Empty:
                return
            if isinstance(event, InstallProgress):
                self._apply_progress(event)
            elif isinstance(event, InstallResult):
                self.state.result = event
                self.state.page = InstallerPage.COMPLETE
                self._worker = None
            elif isinstance(event, Exception):
                self.state.error = str(event) or event.__class__.__name__
                self.state.page = InstallerPage.ERROR
                self._worker = None

    #: Seconds without any progress frame before the installing page shows
    #: the current step's own elapsed time ("still working").
    STALL_SECONDS = 20.0

    def _apply_progress(self, event: InstallProgress) -> None:
        """Adopt one progress observation; the bar never moves backwards."""

        now = time.monotonic()
        previous = self.state.progress
        if previous is None or event.stage != previous.stage or self._phase_since is None:
            self._phase_since = now
        self._last_progress_at = now
        fraction = event.fraction
        if previous is not None and self.state.page == InstallerPage.INSTALLING:
            fraction = max(fraction, previous.fraction)
        self.state.progress = replace(event, fraction=max(0.0, min(1.0, fraction)))

    def _stalled_phase_seconds(self, now: float | None = None) -> int | None:
        """Elapsed seconds of the current phase once it went quiet, else None."""

        if self._last_progress_at is None or self._phase_since is None:
            return None
        now = time.monotonic() if now is None else now
        if now - self._last_progress_at < self.STALL_SECONDS:
            return None
        return max(0, int(now - self._phase_since))

    # --- Presentation ---------------------------------------------------------
    # Everything below draws state; none of it changes what a page does. The
    # look (meadow, Leo, kit controls, prepared layers) is owned by
    # ``presentation.InstallerLook``; hit-target keys are unchanged so the
    # input handlers above keep their exact behaviour.

    _PAGE_CHROME: dict[str, tuple[str, str | None]] = {
        "WELCOME": ("Install Greia", None),
        "LAYOUT": ("Your keyboard", "pose_think"),
        "TARGET": ("Choose the internal disk", "pose_point"),
        "POINTER": ("Pointer setup", "happy"),
        "DISPLAY": ("Display", "default"),
        "SETTINGS": ("Input and screen", "default"),
        "WIFI": ("Wi-Fi (optional)", "pose_wave"),
        "CONFIRM": ("Ready to install", "pose_point"),
        "INSTALLING": ("Installing", "happy"),
        "COMPLETE": ("All done!", "pose_cheer"),
        "ERROR": ("Installation stopped", "sad"),
    }

    def _look(self) -> InstallerLook:
        """The page renderer, built lazily so the localized typography is used."""

        if self._look_cache is None:
            self._look_cache = InstallerLook(self.root, self._typography)
        return self._look_cache

    def _fonts(self, height: int) -> tuple[Any, Any, Any]:
        """(control, title, body) fonts sized for the viewport height.

        Sizes come from :func:`presentation.text_scale`, which never goes
        below the readability floors (20/16 px body/hint at 600 px, 17/15 px
        at 480 px); labels are never shrunk below the hint size either.
        """

        scale = text_scale(height)
        self._title_px = scale.title
        self._control_px = scale.control
        self._body_px = scale.body
        self._hint_px = scale.hint
        self._look().min_text_px = scale.hint
        return (
            self._typography.font(FontRole.CONTROL, self._control_px),
            self._typography.font(FontRole.TITLE, self._title_px),
            self._typography.font(FontRole.BODY, self._body_px),
        )

    def _draw(self, screen: Any, pygame: Any) -> None:
        width, height = screen.get_size()
        self._buttons.clear()
        look = self._look()
        font, title_font, small_font = self._fonts(height)
        page = self.state.page
        if page != InstallerPage.INSTALLING:
            self._installing_since = None
        elif self._installing_since is None:
            self._installing_since = time.monotonic()
        step = step_for_page(page.name)
        frame = page_frame(pygame, (width, height), steps=step is not None)
        title, pose = self._PAGE_CHROME[page.name]
        y = look.page_base(
            screen,
            pygame,
            frame,
            title=title,
            title_size=self._title_px,
            title_color=BURGUNDY if page == InstallerPage.ERROR else COCOA,
            step=step,
            pose=pose,
            poster=page == InstallerPage.WELCOME,
        )
        main = frame.main
        y += max(6, height // 80)
        if page == InstallerPage.WELCOME:
            self._draw_welcome(screen, pygame, main, y, font, small_font)
        elif page == InstallerPage.LAYOUT:
            self._draw_layout(screen, pygame, main, y, font, title_font, small_font)
        elif page == InstallerPage.TARGET:
            self._draw_target(screen, pygame, main, y, font, small_font)
        elif page == InstallerPage.POINTER:
            self._draw_pointer_page(screen, pygame, main, y, font, small_font)
        elif page == InstallerPage.DISPLAY:
            self._draw_display_page(screen, pygame, main, y, font, small_font)
        elif page == InstallerPage.SETTINGS:
            self._draw_legacy_settings(screen, pygame, main, y, font)
        elif page == InstallerPage.WIFI:
            self._draw_wifi(screen, pygame, main, y, font, small_font)
        elif page == InstallerPage.CONFIRM:
            self._draw_confirm(screen, pygame, main, y, font, title_font, small_font)
        elif page == InstallerPage.INSTALLING:
            self._draw_installing(screen, pygame, main, y, font, small_font)
        elif page == InstallerPage.COMPLETE:
            self._draw_complete(screen, pygame, main, y, font, title_font, small_font)
        elif page == InstallerPage.ERROR:
            self._draw_error(screen, pygame, main, y, font, small_font)

    # -- pages ----------------------------------------------------------------

    def _draw_welcome(self, screen: Any, pygame: Any, main: Any, y: int, font: Any, small_font: Any) -> None:
        look = self._look()
        nav_top = self._bottom_row_y(main) - self.BUTTON_HEIGHT // 2 - 8
        y += max(4, self._body_px // 2)
        y = self._paragraph(
            screen,
            "Greia will be installed on this computer's internal disk.",
            font,
            COCOA,
            pygame.Rect(main.left, y, main.width, nav_top - y),
        )
        y += max(10, self._body_px)
        bullets = (
            "First you choose the keyboard, the disk, the pointer, the screen and Wi-Fi.",
            "Nothing is erased until you confirm at the last step.",
            "Keep the power adapter connected.",
        )
        dot = max(14, self._control_px - 6)
        line_h = font.get_linesize()
        for bullet in bullets:
            if y >= nav_top - line_h:
                break
            body = look.painter.body(BodyShape.ROUND, (dot, dot), SUNSHINE, contour_width=2)
            screen.blit(look.painter.presentable(body, screen), (main.left, y + (line_h - dot) // 2))
            y = self._paragraph(
                screen,
                bullet,
                font,
                COCOA,
                pygame.Rect(main.left + dot + 14, y, main.width - dot - 14, nav_top - y),
            )
            y += max(8, self._body_px * 2 // 3)
        primary = self._primary_button(screen, pygame, main, "Start")
        # Leo greets the parent in the free lower corner (cached rendition).
        size = min(150, primary.top - y - 8)
        if size >= 90:
            leo = look.art.character(pygame, "pose_wave", size)
            if leo is not None:
                screen.blit(leo, leo.get_rect(bottomleft=(main.left, primary.bottom)))

    def _draw_layout(
        self,
        screen: Any,
        pygame: Any,
        main: Any,
        y: int,
        font: Any,
        title_font: Any,
        small_font: Any,
    ) -> None:
        look = self._look()
        remaining = [
            probe for probe in PROBES if probe.character not in self._layout_probe_results
        ]
        # The 'z' probe (5th) separates QWERTZ from QWERTY, which is what
        # distinguishes German from Italian/Spanish/Portuguese. Requiring it
        # avoids presenting a wrong guess. The final '@' probe is optional
        # (AltGr-only on many layouts) and is handled by the selector.
        done_count = len(self._layout_probe_results)
        if done_count >= 5 or self._layout_selector_forced:
            remaining = []
        nav_top = self._bottom_row_y(main) - self.BUTTON_HEIGHT // 2 - 6
        if remaining:
            probe = remaining[0]
            image = self._fit_text(font, probe.instruction, COCOA, main.width)
            screen.blit(image, image.get_rect(midtop=(main.centerx, y)))
            y += image.get_height() + 10
            key_size = max(56, min(112, (nav_top - y) // 2))
            key_rect = pygame.Rect(0, 0, key_size, key_size)
            key_rect.midtop = (main.centerx, y)
            keycap(look, screen, key_rect, probe.character, int(key_size * 0.55))
            y = key_rect.bottom + 10
            self._center_line(screen, "I'm listening — press that key now.", small_font, HINT, main, y)
            y += small_font.get_linesize() + 8
            dot = max(14, self._body_px)
            gap = dot // 2
            total = len(PROBES) * dot + (len(PROBES) - 1) * gap
            left = main.centerx - total // 2
            for index in range(len(PROBES)):
                fill = SUNSHINE if index < done_count else SURFACE
                body = look.painter.body(BodyShape.ROUND, (dot, dot), fill, contour_width=2)
                screen.blit(look.painter.presentable(body, screen), (left + index * (dot + gap), y))
            y += dot + 6
            self._center_line(screen, f"{done_count} of {len(PROBES)} pressed", small_font, COCOA, main, y)
            y += small_font.get_linesize() + 4
            if y + small_font.get_linesize() <= nav_top:
                self._center_line(
                    screen,
                    f"After {5 - done_count} more key{'s' if 5 - done_count != 1 else ''} I'll show a list to confirm.",
                    small_font,
                    HINT,
                    main,
                    y,
                )
                y += small_font.get_linesize()
            if done_count >= 3 and y + small_font.get_linesize() <= nav_top:
                self._center_line(screen, "Or press Enter to see the list now.", small_font, HINT, main, y)
        else:
            self._draw_layout_selector(screen, pygame, main, y, font, small_font, nav_top)
        self._back_button(screen, pygame, main)
        if not remaining:
            self._primary_button(screen, pygame, main, "Confirm")

    def _draw_layout_selector(
        self,
        screen: Any,
        pygame: Any,
        main: Any,
        y: int,
        font: Any,
        small_font: Any,
        nav_top: int,
    ) -> None:
        look = self._look()
        self._center_line(
            screen, "Use Up/Down or click to choose, then Enter to confirm", small_font, HINT, main, y
        )
        y += small_font.get_linesize() + 10
        inferred_id = infer_layout(self._layout_probe_results)
        all_ids = self._all_layout_ids
        columns = 2 if main.width >= 460 else 1
        row_h = max(40, min(52, font.get_height() + 18))
        gap = 8
        rows = max(1, (nav_top - y + gap) // (row_h + gap))
        capacity = rows * columns
        index = min(self._layout_alternative_index, max(0, len(all_ids) - 1))
        start = self._layout_scroll - self._layout_scroll % columns
        if index < start:
            start = index - index % columns
        elif index >= start + capacity:
            start = (index // columns - rows + 1) * columns
        self._layout_scroll = max(0, start)
        cell_w = (main.width - gap * (columns - 1)) // columns
        badge = self._tr("Suggested")
        for offset in range(capacity):
            item = self._layout_scroll + offset
            if item >= len(all_ids):
                break
            layout_id = all_ids[item]
            row, column = divmod(offset, columns)
            rect = pygame.Rect(main.left + column * (cell_w + gap), y + row * (row_h + gap), cell_w, row_h)
            selected = item == self._layout_alternative_index
            look.panel(screen, rect, SUNSHINE if selected else FIELD, width=3 if selected else 2)
            self._buttons[f"layout-{item}"] = rect
            label_max = rect.width - 28
            if layout_id == inferred_id:
                tag = look.label(badge, self._hint_px, COCOA, role=FontRole.CONTROL)
                tag_rect = pygame.Rect(0, 0, tag.get_width() + 18, tag.get_height() + 6)
                tag_rect.midright = (rect.right - 10, rect.centery)
                look.panel(screen, tag_rect, mix(SUNSHINE, WHITE, 0.45), width=2)
                screen.blit(tag, tag.get_rect(center=tag_rect.center))
                label_max = tag_rect.left - rect.left - 24
            image = self._fit_text(font, layout_by_id(layout_id).label, COCOA, label_max)
            screen.blit(image, image.get_rect(midleft=(rect.left + 14, rect.centery)))
            if selected:
                look.focus(screen, rect)

    def _draw_target(self, screen: Any, pygame: Any, main: Any, y: int, font: Any, small_font: Any) -> None:
        look = self._look()
        y = self._paragraph(
            screen,
            "Greia will be installed on the disk you choose. Only internal disks that are safe to use are shown.",
            small_font,
            HINT,
            pygame.Rect(main.left, y, main.width, main.height),
            center=True,
        )
        y += 10
        if self.state.error:
            y = self._banner(screen, pygame, main, y, self.state.error, small_font) + 10
        nav_top = self._bottom_row_y(main) - self.BUTTON_HEIGHT // 2 - 10
        if not self.state.targets:
            box = pygame.Rect(main.left, y, main.width, max(60, min(110, nav_top - y)))
            look.panel(screen, box, WARNING_FIELD, contour=BURGUNDY)
            self._paragraph(
                screen,
                "No safe internal disk was found.",
                font,
                BURGUNDY,
                box.inflate(-28, -20).move(0, max(0, box.height // 2 - font.get_linesize())),
                center=True,
            )
        row_h = max(60, min(84, (nav_top - y) // max(1, min(3, len(self.state.targets) or 1)) - 10))
        for index, target in enumerate(self.state.targets[:4]):
            rect = pygame.Rect(main.left, y, main.width, row_h)
            if rect.bottom > nav_top:
                break
            selected = index == self.state.selected_target
            look.panel(screen, rect, SUNSHINE if selected else FIELD, width=3 if selected else 2)
            glyph = pygame.Rect(rect.left + 10, rect.top + 8, rect.height - 16, rect.height - 16)
            look.disk_glyph(screen, pygame, glyph)
            text_left = glyph.right + 14
            model = target.model.strip() or target.name
            name = self._fit_line(font, model, COCOA, rect.right - text_left - 14)
            facts = self._fit_line(
                small_font, f"{target.human_size} · {target.path}", COCOA, rect.right - text_left - 14
            )
            block = name.get_height() + facts.get_height()
            top = rect.centery - block // 2
            screen.blit(name, (text_left, top))
            screen.blit(facts, (text_left, top + name.get_height()))
            self._buttons[f"target-{index}"] = rect
            if selected:
                look.focus(screen, rect)
            y = rect.bottom + 10
        self._back_button(screen, pygame, main)
        self._primary_button(screen, pygame, main, "Continue", enabled=self.state.target is not None)

    def _draw_pointer_page(
        self,
        screen: Any,
        pygame: Any,
        main: Any,
        y: int,
        font: Any,
        small_font: Any,
    ) -> None:
        """Deliberate Pointer Setup page: presets, gated toggles, test area."""
        look = self._look()
        self._clamp_pointer_focus()
        rows = self.pointer_rows()
        focused = self.focused_pointer_row()
        # Measure the header from the fonts actually in use. The reference Acer
        # renders taller metrics than the development host, so the old fixed
        # +52 title gap drew the subtitle on top of the title and the fixed
        # 96 px header start pushed the first row up into it.
        subtitle_y = y
        subtitle_h = small_font.get_height()
        header_height = (subtitle_y + subtitle_h + self.POINTER_HEADER_PAD) - main.top
        self._center_line(screen, "Pointer feel", small_font, HINT, main, subtitle_y)

        # Measure the vertical budget instead of assuming it (see
        # _pointer_vertical_budget): row height, gaps and the test target are
        # derived from the card that is actually available.
        setting_count = sum(
            1
            for name in rows
            if name
            in {
                "tap",
                "disable-while-typing",
                "natural",
                "touchpad-preset",
                "mouse-preset",
                "mouse-preset-labeled",
            }
        )
        strip_label_h = max(1, small_font.get_linesize())
        status_h = strip_label_h
        strip_tail = 14 + status_h + 6 + 40
        row_h, step, target_size = self._pointer_vertical_budget(
            main.height,
            setting_count,
            header_height,
            font.get_height() + 2 * self.POINTER_ROW_PAD,
            strip_label_h,
            strip_tail,
        )
        y = main.top + header_height
        settings = self.state.settings
        if "tap" in rows:
            self._toggle_row(screen, pygame, main, "tap", "Tap touchpad to click",
                             settings.touchpad_tap, font, y, row_h, focused == "tap")
            y += step
        if "disable-while-typing" in rows:
            self._toggle_row(screen, pygame, main, "disable-while-typing", "Disable while typing",
                             settings.disable_while_typing, font, y, row_h,
                             focused == "disable-while-typing")
            y += step
        if "natural" in rows:
            self._toggle_row(screen, pygame, main, "natural", "Natural scrolling",
                             settings.natural_scrolling, font, y, row_h, focused == "natural")
            y += step
        if "touchpad-preset" in rows:
            self._preset_row(screen, pygame, main, "touch", "Touchpad feel",
                             speed_to_preset(settings.touchpad_speed), font, y, row_h,
                             focused == "touchpad-preset")
            y += step
        if "mouse-preset" in rows:
            self._preset_row(screen, pygame, main, "mouse", "Mouse feel",
                             speed_to_preset(settings.mouse_speed), font, y, row_h,
                             focused == "mouse-preset")
            y += step
        elif "mouse-preset-labeled" in rows:
            self._preset_row(screen, pygame, main, "mouse", "Mouse feel (when a mouse is attached)",
                             speed_to_preset(settings.mouse_speed), font, y, row_h,
                             focused == "mouse-preset-labeled")
            y += step
        self._back_button(screen, pygame, main)
        self._primary_button(screen, pygame, main, "Continue", focused=focused == "continue")
        # Test strip: three large dispersed targets with click feedback. The
        # budget drops the strip entirely (target_size 0) on a card too short
        # to hold it and the legible rows, rather than overlapping the
        # navigation row. The 1 2 3 keys still run the same test.
        if target_size <= 0:
            return
        target_mid = y + strip_label_h + 12 + target_size // 2
        centers = tuple(
            (main.left + int(main.width * fraction), target_mid) for fraction in (0.2, 0.5, 0.8)
        )
        note = self._pointer_unavailable_note()
        self._center_fitted_text(
            screen, note or "Try it here", small_font, HINT, y + strip_label_h // 2, main.width, main
        )
        for index, center in enumerate(centers):
            key = f"test-{index + 1}"
            rect = pygame.Rect(0, 0, target_size, target_size)
            rect.center = center
            is_focused = focused == key
            look.tile(screen, rect, SUNSHINE if is_focused else SURFACE, width=3 if is_focused else 2)
            label = self._text(font, str(index + 1), COCOA)
            screen.blit(label, label.get_rect(center=rect.center))
            if is_focused:
                look.focus(screen, rect, shape=BodyShape.TILE)
            self._buttons[key] = rect
        feedback = self._pointer_test_feedback or "Click a circle, or press 1 2 3"
        status = feedback
        if self._pointer_preview_error:
            status = f"{self._tr(feedback)} · {self._tr(self._pointer_preview_error)}"
        self._center_fitted_text(
            screen, status, small_font, COCOA, target_mid + target_size // 2 + 14, main.width, main
        )
        reset_width = min(main.width, max(200, self._typography.surface_width(small_font, "Reset pointer feel") + 48))
        reset_rect = pygame.Rect(0, 0, reset_width, 40)
        reset_rect.midtop = (main.centerx, target_mid + target_size // 2 + 14 + status_h // 2 + 6)
        look.pill(screen, reset_rect, "Reset pointer feel", size=self._body_px)
        if focused == "reset":
            look.focus(screen, reset_rect, shape=BodyShape.PILL)
        self._buttons["pointer-reset"] = reset_rect

    def _draw_display_page(self, screen: Any, pygame: Any, main: Any, y: int, font: Any, small_font: Any) -> None:
        """Display page: resolution choice, suitability, supported modes."""
        look = self._look()
        facts = self.display_facts()
        y += 8
        value = "Automatic" if self.state.settings.resolution == "auto" else self.state.settings.resolution
        self._value_row(screen, pygame, main, "resolution", "Screen resolution", value, font, y, 58)
        y += 58 + 16
        box = pygame.Rect(main.left, y, main.width, max(64, small_font.get_linesize() * 2 + font.get_linesize() + 24))
        look.panel(screen, box, FIELD)
        inner = box.inflate(-28, -18)
        bottom = self._paragraph(screen, self.display_status_copy(), font, COCOA, inner)
        supported = facts["supported_mode_ids"]
        modes = f"Greia screens: {', '.join(supported[:4])}" if supported else "Greia screens: Automatic"
        self._paragraph(screen, modes, small_font, HINT, pygame.Rect(inner.left, bottom + 4, inner.width, inner.height))
        y = box.bottom + 12
        if self.display_install_block_reason() is not None:
            self._banner(screen, pygame, main, y, "This screen is not fully supported — install is paused.", small_font)
        self._back_button(screen, pygame, main)
        self._primary_button(screen, pygame, main, "Continue")

    def _draw_legacy_settings(self, screen: Any, pygame: Any, main: Any, y: int, font: Any) -> None:
        # Legacy combined page (superseded by POINTER + DISPLAY).
        settings = self.state.settings
        row_h = max(40, min(52, (self._bottom_row_y(main) - 40 - y) // 5 - 6))
        step = row_h + 6
        self._toggle_row(screen, pygame, main, "tap", "Tap touchpad to click", settings.touchpad_tap, font, y, row_h)
        self._toggle_row(screen, pygame, main, "natural", "Natural scrolling", settings.natural_scrolling, font, y + step, row_h)
        self._preset_row(screen, pygame, main, "mouse", "Mouse feel", speed_to_preset(settings.mouse_speed), font, y + 2 * step, row_h)
        self._preset_row(screen, pygame, main, "touch", "Touchpad feel", speed_to_preset(settings.touchpad_speed), font, y + 3 * step, row_h)
        self._value_row(screen, pygame, main, "resolution", "Screen resolution", settings.resolution, font, y + 4 * step, row_h)
        self._back_button(screen, pygame, main)
        self._primary_button(screen, pygame, main, "Continue")

    def _draw_wifi(self, screen: Any, pygame: Any, main: Any, y: int, font: Any, small_font: Any) -> None:
        look = self._look()
        snapshot = self.wifi.snapshot
        y = self._paragraph(
            screen,
            "Connect now to make Greia ready for the Parents app. You can also set up Wi-Fi later.",
            small_font,
            HINT,
            pygame.Rect(main.left, y, main.width, main.height),
            center=True,
        ) + 8
        ssh = self._live_ssh.snapshot
        self._toggle_row(screen, pygame, main, "wifi-ssh", "Installer SSH: greia / greia",
                         ssh.enabled, small_font, y, 42, focused=self._wifi_ssh_focus)
        y += 46
        if ssh.busy or ssh.error or ssh.enabled:
            message = ("Changing SSH…" if ssh.busy else
                       "SSH unavailable. Try again." if ssh.error else
                       "Connect: ssh greia@greia-installer.local")
            y = self._paragraph(screen, message, small_font, BURGUNDY if ssh.error else HINT,
                                pygame.Rect(main.left, y, main.width, main.height), center=True) + 4
        nav_top = self._bottom_row_y(main) - self.BUTTON_HEIGHT // 2 - 8
        error_h = small_font.get_linesize() + 6 if snapshot.error else 0
        area = pygame.Rect(main.left, y, main.width, max(40, nav_top - error_h - y))
        phase = snapshot.phase
        tick = int(time.monotonic() * 3)
        if phase is WifiSetupPhase.SCANNING:
            self._status_card(screen, pygame, area, "Looking for Wi-Fi networks…", font, COCOA, busy=tick)
        elif phase is WifiSetupPhase.CONNECTING:
            selected = snapshot.selected_network
            name = selected.ssid if selected is not None else "Wi-Fi"
            self._status_card(screen, pygame, area, f"Connecting to {name}…", font, COCOA, busy=tick)
        elif phase is WifiSetupPhase.UNAVAILABLE:
            self._status_card(
                screen, pygame, area, "No wireless adapter is available. You can continue offline.", font, COCOA
            )
            self._primary_button(screen, pygame, main, "Continue offline")
        elif phase is WifiSetupPhase.CONNECTED:
            self._status_card(
                screen,
                pygame,
                area,
                f"Connected to {snapshot.connected_ssid}",
                font,
                FOREST,
                detail="This network will be ready after the first boot.",
                detail_font=small_font,
                check=True,
            )
            self._primary_button(screen, pygame, main, "Continue")
        else:
            self._draw_wifi_networks(screen, pygame, area, font, small_font)

        if snapshot.error and phase is not WifiSetupPhase.UNAVAILABLE and snapshot.networks:
            self._center_fitted_text(
                screen, snapshot.error, small_font, BURGUNDY, nav_top - error_h // 2, main.width, main
            )

        self._back_button(screen, pygame, main)
        if phase not in {
            WifiSetupPhase.CONNECTED,
            WifiSetupPhase.UNAVAILABLE,
            WifiSetupPhase.CONNECTING,
        }:
            back = self._buttons["back"]
            skip_w = max(150, min(230, main.width // 3))
            skip = pygame.Rect(main.right - skip_w, back.top, skip_w, back.height)
            look.pill(screen, skip, "Skip for now", size=self._body_px + 1)
            self._buttons["wifi-skip"] = skip
            refresh_w = max(120, min(190, skip.left - back.right - 24))
            refresh = pygame.Rect(0, back.top, refresh_w, back.height)
            refresh.centerx = (back.right + skip.left) // 2
            look.pill(screen, refresh, "Refresh", size=self._body_px + 1)
            self._buttons["wifi-refresh"] = refresh

    def _draw_wifi_networks(self, screen: Any, pygame: Any, area: Any, font: Any, small_font: Any) -> None:
        look = self._look()
        snapshot = self.wifi.snapshot
        if not snapshot.networks:
            # An empty list is not the same thing as a failed scan. Showing
            # "No networks found" for both hid the real reason the scan failed
            # on the reference Acer, so an actual error is surfaced instead.
            if snapshot.phase is WifiSetupPhase.ERROR and snapshot.error:
                self._status_card(
                    screen, pygame, area, "Wi-Fi could not be checked", font, BURGUNDY,
                    detail=snapshot.error, detail_font=small_font,
                )
            else:
                self._status_card(
                    screen, pygame, area, "No networks found. Refresh, or continue offline.", font, COCOA
                )
            return

        network = snapshot.selected_network
        controls_h = (self.BUTTON_HEIGHT + 12) if network is not None else 0
        row_h = max(44, min(56, font.get_height() + 22))
        gap = 8
        list_h = area.height - controls_h
        total = len(snapshot.networks)
        per_page = max(1, (list_h + gap) // (row_h + gap))
        if total > per_page:
            # One slot becomes the "More networks" row so a pointer-only parent
            # can reach every network (arrow keys page through them as well).
            per_page = max(1, per_page - 1)
        page_start = (snapshot.selected_index // per_page) * per_page
        visible = snapshot.networks[page_start : page_start + per_page]
        y = area.top
        for offset, item in enumerate(visible):
            index = page_start + offset
            rect = pygame.Rect(area.left, y, area.width, row_h)
            selected = index == snapshot.selected_index
            supported = item.installer_supported
            fill = SUNSHINE if selected else (FIELD if supported else mix(MUTED, SURFACE, 0.4))
            look.panel(screen, rect, fill, width=3 if selected else 2)
            self._buttons[f"wifi-{index}"] = rect
            bars = pygame.Rect(0, 0, 26, rect.height - 22)
            bars.midright = (rect.right - 14, rect.centery)
            look.signal(screen, pygame, bars, _signal_level(item.signal_dbm))
            if item.security is WifiSecurity.OPEN:
                security = "Open"
            elif item.security is WifiSecurity.PERSONAL:
                security = "Password"
            else:
                security = "Enterprise — later"
            detail = self._text(small_font, security, COCOA)
            screen.blit(detail, detail.get_rect(midright=(bars.left - 12, rect.centery)))
            name = self._fit_line(font, item.ssid, COCOA, bars.left - 24 - detail.get_width() - rect.left - 16)
            screen.blit(name, name.get_rect(midleft=(rect.left + 16, rect.centery)))
            if selected:
                look.focus(screen, rect)
            y = rect.bottom + gap
        if total > per_page:
            more = pygame.Rect(area.left, y, area.width, max(34, row_h - 14))
            pages = (total + per_page - 1) // per_page
            label = f"{self._tr('More networks')}  {page_start // per_page + 1}/{pages}"
            look.pill(screen, more, label, size=self._body_px)
            self._buttons["wifi-more"] = more
            self._wifi_next_page_index = (page_start + per_page) % total

        if network is None:
            return
        controls = pygame.Rect(area.left, area.bottom - self.BUTTON_HEIGHT, area.width, self.BUTTON_HEIGHT)
        connect_w = max(140, min(220, area.width // 3))
        connect = pygame.Rect(controls.right - connect_w, controls.top, connect_w, controls.height)
        if network.security is WifiSecurity.PERSONAL:
            field = pygame.Rect(controls.left, controls.top, connect.left - controls.left - 14, controls.height - 4)
            look.panel(screen, field, WHITE, width=2)
            passphrase = snapshot.passphrase
            if passphrase:
                revealed = False
                if self._last_password_character is not None:
                    _character, typed_at = self._last_password_character
                    revealed = time.monotonic() - typed_at < 1.0
                masked = ("*" * (len(passphrase) - 1) + passphrase[-1]) if revealed else "*" * len(passphrase)
                text_render = self._fit_line(small_font, masked, COCOA, field.width - 36)
            else:
                text_render = self._text(small_font, "Wi-Fi password", HINT)
            text_rect = text_render.get_rect(midleft=(field.left + 16, field.centery))
            screen.blit(text_render, text_rect)
            if int(time.monotonic() * 2) % 2 == 0:
                pygame.draw.rect(
                    screen, COCOA, (text_rect.right + 3, text_rect.top + 2, 2, max(8, text_rect.height - 4))
                )
            self._buttons["wifi-password"] = field
        if network.installer_supported:
            self._kit_button(screen, pygame, "primary", connect, "Connect", fill=SUNSHINE)
        else:
            self._paragraph(
                screen,
                "Enterprise Wi-Fi can be configured later in Greia Parents.",
                small_font,
                BURGUNDY,
                pygame.Rect(controls.left, controls.top + 4, controls.width, controls.height),
                center=True,
            )

    def _draw_confirm(
        self,
        screen: Any,
        pygame: Any,
        main: Any,
        y: int,
        font: Any,
        title_font: Any,
        small_font: Any,
    ) -> None:
        look = self._look()
        target = self.state.target
        nav_center = self._bottom_row_y(main)
        hold_h = self.BUTTON_HEIGHT + 8
        hint_y = nav_center - hold_h // 2 - small_font.get_linesize() - 8
        # The disk that will be erased: big, unambiguous, with its size and
        # device path, framed as the destructive object it is.
        card_h = max(70, min(108, (hint_y - y) // 2))
        card = pygame.Rect(main.left, y, main.width, card_h)
        look.panel(screen, card, WARNING_FIELD, contour=BURGUNDY, width=3)
        glyph = pygame.Rect(card.left + 12, card.top + 10, card.height - 20, card.height - 20)
        look.disk_glyph(screen, pygame, glyph, danger=True)
        text_left = glyph.right + 16
        if target is not None:
            model = target.model.strip() or target.name
            name = self._fit_line(title_font, model, COCOA, card.right - text_left - 14)
            facts = self._fit_line(font, f"{target.human_size} · {target.path}", COCOA, card.right - text_left - 14)
        else:
            name = self._fit_text(title_font, "Unknown disk", COCOA, card.right - text_left - 14)
            facts = self._text(font, "", COCOA)
        block = name.get_height() + facts.get_height()
        top = card.centery - block // 2
        screen.blit(name, (text_left, top))
        screen.blit(facts, (text_left, top + name.get_height()))
        y = card.bottom + 10
        warning = f"{self._tr('Everything currently on this disk will be erased.')} {self._tr('This cannot be undone.')}"
        y = self._paragraph(
            screen, warning, font, BURGUNDY, pygame.Rect(main.left, y, main.width, hint_y - y), translate=False
        ) + 6
        layout = layout_by_id(self.state.settings.keyboard_layout)
        wifi_value = self.wifi.profile.ssid if self.wifi.profile is not None else self._tr("Set up later")
        summary = (
            f"{self._tr('Keyboard')}: {self._tr(layout.label) if layout else self.state.settings.keyboard_layout}"
            f"    Wi-Fi: {wifi_value}"
        )
        if y + small_font.get_linesize() <= hint_y:
            image = self._fit_line(small_font, summary, COCOA, main.width)
            screen.blit(image, (main.left, y))
            y += small_font.get_linesize() + 4
        if self.display_install_block_reason() is not None and y + small_font.get_linesize() <= hint_y:
            self._paragraph(
                screen,
                "This screen is not fully supported — install is paused.",
                small_font,
                BURGUNDY,
                pygame.Rect(main.left, y, main.width, hint_y - y),
            )
        back = self._back_button(screen, pygame, main)
        hold_w = max(220, min(440, main.right - back.right - 20))
        rect = pygame.Rect(main.right - hold_w, nav_center - hold_h // 2, hold_w, hold_h)
        body = look.painter.body(BodyShape.PILL, rect.size, DANGER, lip=4)
        screen.blit(look.painter.presentable(body, screen), rect.topleft)
        label = "Hold to erase and install"
        if self._hold_started is not None:
            fraction = min(1.0, (time.monotonic() - self._hold_started) / self.HOLD_SECONDS)
            # The darker fill grows over the same body; the label is redrawn
            # on top so no earlier label bleeds through the progress fill.
            pressed = look.painter.body(BodyShape.PILL, rect.size, DANGER_PRESSED, lip=4)
            screen.blit(pressed, rect.topleft, area=pygame.Rect(0, 0, int(rect.width * fraction), rect.height))
            label = "Keep holding…"
        image = look.label(label, self._control_px, WHITE, max_width=rect.width - 32)
        screen.blit(image, image.get_rect(center=(rect.centerx, rect.centery - 2)))
        self._buttons["install"] = rect
        # Keyboard focus (Tab/arrows) is drawn like every other page's focus;
        # it starts on Back so Enter alone can never reach the erase hold.
        if self._confirm_focus == "install":
            look.focus(screen, rect, shape=BodyShape.PILL)
            hint_copy = f"Hold Enter or Space for {int(self.HOLD_SECONDS)} seconds."
        else:
            if self._confirm_keyboard:
                look.focus(screen, back, shape=BodyShape.PILL)
            hint_copy = f"Keep the button pressed for {int(self.HOLD_SECONDS)} seconds."
        hint = self._fit_text(small_font, hint_copy, HINT, main.width - back.width - 16)
        screen.blit(hint, hint.get_rect(bottomright=(main.right, rect.top - 6)))

    def _draw_installing(self, screen: Any, pygame: Any, main: Any, y: int, font: Any, small_font: Any) -> None:
        look = self._look()
        progress = self.state.progress
        now = time.monotonic()
        y = self._paragraph(
            screen,
            "This can take several minutes.",
            small_font,
            HINT,
            pygame.Rect(main.left, y, main.width, main.height),
            center=True,
        ) + 10
        bar = pygame.Rect(main.left, y, main.width, max(30, self._control_px + 10))
        tick = int(now * 4)
        look.progress(screen, pygame, bar, progress.fraction, busy_tick=tick)
        y = bar.bottom + 10
        # Phase name, plus the measured share of it when the service can
        # measure (bytes copied / read back). Numbers are drawn verbatim.
        detail = self._tr(progress.detail)
        if progress.phase_fraction is not None:
            detail = f"{detail} · {int(progress.phase_fraction * 100)}%"
        image = self._fit_line(font, detail, COCOA, main.width)
        screen.blit(image, image.get_rect(midtop=(main.centerx, y)))
        y += font.get_linesize() + 2
        if self._installing_since is not None:
            elapsed = max(0, int(now - self._installing_since))
            clock = f"{self._tr('Time elapsed')} {elapsed // 60}:{elapsed % 60:02d}"
            image = self._line(small_font, clock, HINT)
            screen.blit(image, image.get_rect(midtop=(main.centerx, y)))
            y += small_font.get_linesize()
        stalled = self._stalled_phase_seconds(now)
        if stalled is not None:
            # A long step that reports nothing (e.g. checking the release
            # files) still shows that it is alive and for how long.
            note = f"{self._tr('Still working on this step')} {stalled // 60}:{stalled % 60:02d}"
            image = self._fit_line(small_font, note, HINT, main.width)
            screen.blit(image, image.get_rect(midtop=(main.centerx, y)))
        box_h = small_font.get_linesize() * 2 + 26
        box = pygame.Rect(main.left, main.bottom - box_h - 8, main.width, box_h)
        look.panel(screen, box, WARNING_FIELD, contour=BURGUNDY)
        self._center_line(screen, "Do not remove the USB key.", small_font, BURGUNDY, box, box.top + 12)
        self._center_line(
            screen, "Do not turn off the computer.", small_font, BURGUNDY, box, box.top + 12 + small_font.get_linesize()
        )

    def _draw_complete(
        self,
        screen: Any,
        pygame: Any,
        main: Any,
        y: int,
        font: Any,
        title_font: Any,
        small_font: Any,
    ) -> None:
        look = self._look()
        self._center_line(screen, "Greia is installed and ready.", font, COCOA, main, y)
        y += font.get_linesize() + 10
        nav_top = self._bottom_row_y(main) - self.BUTTON_HEIGHT // 2 - 10
        change = self._tr("You can change it in Greia Parents after first boot.")
        change_lines = min(2, len(_wrap(change, getattr(small_font, "base", small_font), main.width - 32)))
        box_h = small_font.get_linesize() * (1 + change_lines) + title_font.get_linesize() + 24
        box = pygame.Rect(main.left, y, main.width, box_h)
        look.panel(screen, box, FIELD)
        self._center_line(screen, "Parent login", small_font, HINT, box, box.top + 8)
        # The development credential itself is fixed data, never translated.
        credential = self._line(title_font, "greia  /  greia", COCOA)
        screen.blit(credential, credential.get_rect(midtop=(box.centerx, box.top + 8 + small_font.get_linesize())))
        self._paragraph(
            screen,
            change,
            small_font,
            COCOA,
            pygame.Rect(
                box.left + 16,
                box.bottom - 10 - change_lines * small_font.get_linesize(),
                box.width - 32,
                change_lines * small_font.get_linesize(),
            ),
            center=True,
            translate=False,
            max_lines=2,
        )
        y = box.bottom + 12
        if self.state.result is not None and self.state.result.hardware_detection_incomplete:
            # Short and non-alarming: the install itself succeeded.  A known
            # unsupported Wi-Fi chip gets its own, more precise sentence.
            wifi_missing = bool(
                getattr(self.state.result, "wifi_firmware_unavailable", False)
            )
            y = self._paragraph(
                screen,
                WIFI_FIRMWARE_UNAVAILABLE_NOTE
                if wifi_missing
                else "Some hardware could not be identified automatically. If Wi-Fi or sound do not work, check them in Greia Parents after first boot.",
                small_font,
                COCOA,
                pygame.Rect(main.left, y, main.width, 3 * small_font.get_linesize()),
                center=True,
                max_lines=3,
            ) + 6
        # If the finish marker could not be delivered, a dead button must not
        # look like a shut-down request in flight: show the manual fallback.
        instruction = (
            "The power-off request could not be sent. Press the computer's power button to switch it off."
            if self._poweroff_failed
            else "After the computer turns off, remove the USB key, then turn the computer on again."
        )
        self._paragraph(
            screen,
            instruction,
            small_font,
            BURGUNDY if self._poweroff_failed else COCOA,
            pygame.Rect(main.left, y, main.width, nav_top - y),
            center=True,
        )
        message = "Close the demo" if self.demo else "I'm ready — turn off"
        width = max(240, min(420, main.width // 2 + 40))
        rect = pygame.Rect(0, 0, width, self.BUTTON_HEIGHT)
        rect.center = (main.centerx, self._bottom_row_y(main))
        self._kit_button(screen, pygame, "primary", rect, message, fill=SUNSHINE)

    def _draw_error(self, screen: Any, pygame: Any, main: Any, y: int, font: Any, small_font: Any) -> None:
        look = self._look()
        nav_top = self._bottom_row_y(main) - self.BUTTON_HEIGHT // 2 - 10
        message = _sentence(self._tr(self.state.error or "Installation stopped"))
        note = _sentence(self._tr(" The selected disk may be incomplete if installation had already begun."))
        width = main.width - 32
        message_lines = min(4, len(_wrap(message, getattr(font, "base", font), width)))
        note_lines = min(3, len(_wrap(note, getattr(small_font, "base", small_font), width)))
        height = message_lines * font.get_linesize() + note_lines * small_font.get_linesize() + 40
        box = pygame.Rect(main.left, y + 6, main.width, min(max(80, nav_top - y - 12), height))
        look.panel(screen, box, WARNING_FIELD, contour=BURGUNDY)
        inner = box.inflate(-32, -28)
        bottom = self._paragraph(screen, message, font, BURGUNDY, inner, translate=False, max_lines=4)
        self._paragraph(
            screen,
            note,
            small_font,
            COCOA,
            pygame.Rect(inner.left, bottom + 10, inner.width, inner.bottom - bottom - 10),
            translate=False,
            max_lines=3,
        )
        self._back_button(screen, pygame, main)

    # -- shared building blocks -------------------------------------------------

    def _bottom_row_y(self, main: Any) -> int:
        return main.bottom - 40

    def _kit_button(
        self,
        screen: Any,
        pygame: Any,
        key: str,
        rect: Any,
        label: str,
        *,
        fill: tuple[int, int, int] = SURFACE,
        enabled: bool = True,
        focused: bool = False,
    ) -> Any:
        look = self._look()
        look.pill(screen, rect, label, fill=fill, size=self._control_px, enabled=enabled)
        if focused:
            look.focus(screen, rect, shape=BodyShape.PILL)
        self._buttons[key] = rect
        return rect

    def _back_button(self, screen: Any, pygame: Any, main: Any) -> Any:
        width = max(120, min(180, int(main.width * 0.24)))
        rect = pygame.Rect(0, 0, width, self.BUTTON_HEIGHT)
        rect.midleft = (main.left, self._bottom_row_y(main))
        return self._kit_button(screen, pygame, "back", rect, "Back")

    def _primary_button(
        self,
        screen: Any,
        pygame: Any,
        main: Any,
        label: str,
        *,
        enabled: bool = True,
        focused: bool = False,
    ) -> Any:
        width = max(160, min(260, int(main.width * 0.36)))
        rect = pygame.Rect(0, 0, width, self.BUTTON_HEIGHT)
        rect.midright = (main.right, self._bottom_row_y(main))
        return self._kit_button(
            screen, pygame, "primary", rect, label, fill=SUNSHINE, enabled=enabled, focused=focused
        )

    def _setting_row(self, screen: Any, main: Any, y: int, height: int, focused: bool) -> Any:
        import pygame

        rect = pygame.Rect(main.left, y, main.width, height)
        self._look().panel(screen, rect, FIELD)
        if focused:
            self._look().focus(screen, rect)
        return rect

    def _toggle_row(
        self,
        screen: Any,
        pygame: Any,
        main: Any,
        key: str,
        label: str,
        value: bool,
        font: Any,
        y: int,
        height: int = 54,
        focused: bool = False,
    ) -> None:
        rect = self._setting_row(screen, main, y, height, focused)
        state_h = min(34, max(22, height - 14))
        state_rect = pygame.Rect(0, 0, int(state_h * 1.9), state_h)
        state_rect.midright = (rect.right - 16, rect.centery)
        label_surface = self._fit_text(font, label, COCOA, state_rect.left - rect.left - 36)
        screen.blit(label_surface, label_surface.get_rect(midleft=(rect.left + 18, rect.centery)))
        self._look().toggle(screen, state_rect, value)
        self._buttons[key] = rect

    def _preset_row(
        self,
        screen: Any,
        pygame: Any,
        main: Any,
        key: str,
        label: str,
        preset_name: str,
        font: Any,
        y: int,
        height: int = 54,
        focused: bool = False,
    ) -> None:
        look = self._look()
        rect = self._setting_row(screen, main, y, height, focused)
        btn = min(40, max(24, height - 12))
        value_w = max(
            self._typography.surface_width(font, name) for name in speed_preset_names()
        ) + 16
        plus = pygame.Rect(0, 0, btn + 8, btn)
        plus.midright = (rect.right - 12, rect.centery)
        minus = pygame.Rect(0, 0, btn + 8, btn)
        minus.midright = (plus.left - value_w - 8, rect.centery)
        for button_rect, glyph in ((minus, "−"), (plus, "+")):
            body = look.painter.body(BodyShape.PILL, button_rect.size, SUNSHINE, contour_width=2)
            screen.blit(look.painter.presentable(body, screen), button_rect.topleft)
            glyph_image = self._line(font, glyph, COCOA)
            screen.blit(glyph_image, glyph_image.get_rect(center=button_rect.center))
        value_image = self._fit_text(font, preset_name, COCOA, value_w)
        screen.blit(value_image, value_image.get_rect(center=((minus.right + plus.left) // 2, rect.centery)))
        label_surface = self._fit_text(font, label, COCOA, minus.left - rect.left - 30)
        screen.blit(label_surface, label_surface.get_rect(midleft=(rect.left + 18, rect.centery)))
        self._buttons[f"{key}-minus"] = minus
        self._buttons[f"{key}-plus"] = plus

    def _value_row(
        self,
        screen: Any,
        pygame: Any,
        main: Any,
        key: str,
        label: str,
        value: str,
        font: Any,
        y: int,
        height: int = 54,
    ) -> None:
        rect = self._setting_row(screen, main, y, height, False)
        value_h = min(42, max(26, height - 14))
        value_rect = pygame.Rect(0, 0, max(150, min(220, rect.width // 3)), value_h)
        value_rect.midright = (rect.right - 12, rect.centery)
        label_surface = self._fit_text(font, label, COCOA, value_rect.left - rect.left - 36)
        screen.blit(label_surface, label_surface.get_rect(midleft=(rect.left + 18, rect.centery)))
        self._look().pill(screen, value_rect, value, fill=SUNSHINE, size=self._control_px)
        self._buttons[key] = rect

    def _banner(self, screen: Any, pygame: Any, main: Any, y: int, message: str, font: Any) -> int:
        """Burgundy-on-rose warning strip; returns its bottom."""

        text = _sentence(self._tr(message))
        raw = getattr(font, "base", font)
        lines = _wrap(text, raw, main.width - 40)[:3]
        box = pygame.Rect(main.left, y, main.width, len(lines) * raw.get_linesize() + 18)
        self._look().panel(screen, box, WARNING_FIELD, contour=BURGUNDY)
        self._paragraph(screen, text, font, BURGUNDY, box.inflate(-40, -18), translate=False, max_lines=3)
        return box.bottom

    def _status_card(
        self,
        screen: Any,
        pygame: Any,
        area: Any,
        message: str,
        font: Any,
        color: tuple[int, int, int],
        *,
        detail: str = "",
        detail_font: Any = None,
        busy: int | None = None,
        check: bool = False,
    ) -> None:
        """Centred message card for waiting/empty/finished states."""

        look = self._look()
        raw = getattr(font, "base", font)
        text = self._tr(message)
        lines = _wrap(text, raw, area.width - 56)[:3]
        detail_lines: list[str] = []
        if detail and detail_font is not None:
            detail_lines = _wrap(_sentence(self._tr(detail)), getattr(detail_font, "base", detail_font), area.width - 56)[:2]
        extra = 34 if (busy is not None or check) else 0
        height = (
            len(lines) * raw.get_linesize()
            + (len(detail_lines) * detail_font.get_linesize() + 6 if detail_lines else 0)
            + extra
            + 32
        )
        box = pygame.Rect(area.left, 0, area.width, min(area.height, height))
        box.centery = area.top + min(area.height // 2, max(height // 2, area.height // 3))
        look.panel(screen, box, FIELD)
        y = box.top + 16
        if check:
            mark = pygame.Rect(0, 0, 26, 22)
            mark.midtop = (box.centerx, y)
            look.check_mark(screen, pygame, mark, FOREST)
            y += extra
        y = self._paragraph(screen, text, font, color, pygame.Rect(box.left + 28, y, box.width - 56, box.height), center=True, translate=False, max_lines=3)
        if detail_lines:
            y = self._paragraph(
                screen, "\n".join(detail_lines), detail_font, COCOA,
                pygame.Rect(box.left + 28, y + 6, box.width - 56, box.height), center=True, translate=False,
            )
        if busy is not None:
            dot = 12
            for index in range(3):
                fill = SUNSHINE if index == busy % 3 else SURFACE
                body = look.painter.body(BodyShape.ROUND, (dot, dot), fill, contour_width=2)
                screen.blit(look.painter.presentable(body, screen), (box.centerx - 30 + index * 24, y + 10))

    def _tr(self, text: str) -> str:
        """Installer copy in the selected language (identity without one)."""

        translator = getattr(self._typography, "translator", None)
        return translator.text(text) if translator is not None else text

    def _line(self, font: Any, text_value: str, color: tuple[int, int, int]) -> Any:
        """Render final text verbatim (data, or copy that is already translated)."""

        return self._typography.surface(getattr(font, "base", font), text_value, color)

    def _fit_line(self, font: Any, text_value: str, color: tuple[int, int, int], max_width: int) -> Any:
        """``_line`` ellipsized to ``max_width`` (SSIDs, disk models)."""

        raw = getattr(font, "base", font)
        if max_width <= 0 or raw.size(text_value)[0] <= max_width:
            return self._line(font, text_value, color)
        trimmed = text_value
        while trimmed and raw.size(trimmed + "…")[0] > max_width:
            trimmed = trimmed[:-1]
        return self._line(font, (trimmed + "…").rstrip(), color)

    def _center_line(self, screen: Any, text_value: str, font: Any, color: tuple[int, int, int], box: Any, y: int) -> None:
        image = self._fit_text(font, text_value, color, box.width)
        screen.blit(image, image.get_rect(midtop=(box.centerx, y)))

    def _center_fitted_text(
        self,
        screen: Any,
        text_value: str,
        font: Any,
        color: tuple[int, int, int],
        y: int,
        max_width: int,
        box: Any = None,
    ) -> None:
        """Centre one line that must first be constrained to ``max_width``.

        ``_fit_text`` returns an already-rendered surface, so it must be
        blitted rather than rendered again from a string.
        """

        image = self._fit_text(font, text_value, color, max_width)
        center_x = box.centerx if box is not None else screen.get_width() // 2
        screen.blit(image, image.get_rect(center=(center_x, y)))

    def _paragraph(
        self,
        screen: Any,
        text_value: str,
        font: Any,
        color: tuple[int, int, int],
        rect: Any,
        *,
        center: bool = False,
        translate: bool = True,
        max_lines: int | None = None,
    ) -> int:
        """Wrap copy into ``rect``; return the y below the last line.

        Copy is translated *before* wrapping and lines are drawn verbatim:
        wrapping the English source and translating each fragment produced
        untranslatable half sentences.
        """

        text = self._tr(text_value) if translate else text_value
        raw = getattr(font, "base", font)
        lines = _wrap(text, raw, rect.width)
        if max_lines is not None and len(lines) > max_lines:
            lines = lines[:max_lines]
            lines[-1] = lines[-1].rstrip(" .") + "…"
        y = rect.top
        for line in lines:
            image = self._fit_line(font, line, color, rect.width)
            x = rect.centerx - image.get_width() // 2 if center else rect.left
            screen.blit(image, (x, y))
            y += raw.get_linesize()
        return y

    POINTER_HEADER_H = 96
    # Vertical padding under the page subtitle before the first setting row.
    POINTER_HEADER_PAD = 12
    # Minimum interior padding above and below a setting row's label, so a
    # taller font never renders outside the pill that owns it.
    POINTER_ROW_PAD = 7
    POINTER_ROW_GAP = 4
    POINTER_ROW_MIN = 34
    # Absolute floor, reached only once a dense pointer inventory has
    # exhausted the space the test targets are willing to give up.
    POINTER_ROW_HARD_MIN = 30
    POINTER_ROW_MAX = 54
    POINTER_NAV_RESERVE = 68
    POINTER_TARGET_HINT = 64
    POINTER_TARGET_FLOOR = 52
    POINTER_TARGET_HARD_MIN = 40
    # Nominal height of the "Try it here" strip label, and the fixed chrome
    # below the test targets (status line gap + status + reset button). The
    # label is drawn at its measured height, but the budget is reserved from
    # this constant so the arithmetic stays independent of the font.
    POINTER_LABEL_H = 28
    POINTER_STRIP_LABEL_GAP = 12
    POINTER_STRIP_TAIL = 72

    def _pointer_vertical_budget(
        self,
        panel_height: int,
        setting_count: int,
        header_height: int = 0,
        min_row_height: int = 0,
        strip_label_h: int = 0,
        strip_tail: int = 0,
    ) -> tuple[int, int, int]:
        """Fit the pointer page into ``panel_height`` by measurement.

        Returns ``(row_height, step, test_target_size)``. The page previously
        used a hard-coded 56 px step and a hard-coded 64 px test target, and its
        content is taller than the 600 px reference display: rows overlapped and
        the reset control fell outside the panel. Everything is now derived from
        the panel that is actually available.

        ``header_height`` and ``min_row_height`` are measured from the fonts
        actually in use. The reference Acer renders with taller metrics than the
        development host, and a fixed header plus a fixed row floor made the
        title collide with its subtitle and pushed the lower row labels outside
        their own pills, where the next row covered them.

        Navigation buttons are centred on ``main.bottom - 40`` and are
        ``BUTTON_HEIGHT`` tall, so the last 63 px of the panel belong to them.
        The test strip below the final row is a label, a gap, the square
        targets, the status line and the 40 px reset button, so its height is
        ``label + gap + target + tail``. Drawing the label clear of the
        targets is why the label height is part of the budget at all.

        The test targets start at the 9 mm physical touch floor because they
        are what a child aims at, and are only shrunk below it when the row
        count would otherwise collide with the navigation row. Setting rows keep
        their measured readable floor: a label must never render outside its own
        pill, so the targets give up space before any row may.
        """

        count = max(1, int(setting_count))
        header = max(self.POINTER_HEADER_H, int(header_height))
        row_floor = max(self.POINTER_ROW_HARD_MIN, int(min_row_height))
        label_h = max(1, int(strip_label_h) or self.POINTER_LABEL_H)
        tail = max(1, int(strip_tail) or self.POINTER_STRIP_TAIL)
        available = panel_height - header - self.POINTER_NAV_RESERVE
        nav_top = panel_height - self.POINTER_NAV_RESERVE - 5
        floor = min(self.POINTER_TARGET_FLOOR, max(1, available // 4))
        target_size = max(floor, min(self.POINTER_TARGET_HINT, available // 4))

        def layout(target: int) -> tuple[int, int, int]:
            # A target size of zero means the strip is dropped entirely, label
            # and tail included: leaving a floating "Try it here" caption with
            # nothing under it is not a usable layout.
            strip = (
                0
                if target <= 0
                else label_h + self.POINTER_STRIP_LABEL_GAP + target + tail
            )
            room = available - strip
            row = int(room / count) - self.POINTER_ROW_GAP
            row = max(row_floor, min(self.POINTER_ROW_MAX, row))
            step = row + self.POINTER_ROW_GAP
            # The content height is measured from the top of the panel, so the
            # header is part of it. It used to be omitted here, which made every
            # fit comparison under-count the header by its full height and let
            # the strip run into the navigation row on the reference Acer.
            return row, step, header + count * step + strip

        # Setting rows keep their measured floor; the test targets give way
        # first because they are the least critical control on this page (the
        # same test is reachable with 1 2 3). Shrinking them before any row may
        # render its label outside its own pill means a dense pointer inventory
        # degrades instead of overlapping the navigation row.
        while True:
            row, step, bottom = layout(target_size)
            fits = bottom <= nav_top and row >= row_floor
            if fits or target_size <= self.POINTER_TARGET_HARD_MIN:
                break
            target_size = max(self.POINTER_TARGET_HARD_MIN, target_size - 4)
        # The strip still may not fit even at its hard minimum. On the 600 px
        # reference Acer the label font is tall enough that five legible setting
        # rows plus the targets, the status line and the reset control simply
        # do not fit inside the panel. Rather than let the strip collide with
        # Back/Continue or push the reset control off the panel, drop the strip
        # and give its space to the rows. This removes no capability a child
        # can reach: the same pointer test is still available from the 1 2 3
        # keys, which is why those keys exist alongside the targets.
        row, step, bottom = layout(target_size)
        if bottom > nav_top or row < row_floor:
            row, step, _ = layout(0)
            target_size = 0
            # Even without the strip, rows sized greedily can still overrun the
            # navigation row by a pixel or two. Give the row height back to the
            # navigation reserve until the page genuinely clears it, never
            # dropping below the measured readable floor.
            if header + count * (row + self.POINTER_ROW_GAP) > nav_top:
                room = nav_top - header
                row = max(row_floor, int(room / count) - self.POINTER_ROW_GAP)
                step = row + self.POINTER_ROW_GAP
        return row, step, target_size

    def _draw_pointer(self, screen: Any, pygame: Any) -> None:
        """Draw the Greia pointer.

        The native cursor is hidden at startup, so this is the only pointer a
        child ever sees. It used to be skipped whenever the mouse was not
        "focused", which left the pointer-configuration screen with no visible
        pointer at all — on the one screen whose entire purpose is configuring
        the pointer. Presence, not focus, decides whether a pointer exists: the
        cursor is drawn whenever a pointer has been seen, and simply is not
        invented on a machine that has never reported one.
        """
        position = pygame.mouse.get_pos()
        if not self._pointer_seen and position == (0, 0):
            return
        self._pointer_seen = True
        size = max(34, min(54, screen.get_height() // 12))
        x, y = position
        star = self._look().art.icon(pygame, "yellow_star", size)
        if star is not None:
            screen.blit(star, star.get_rect(center=(x, y)))

    def _text(
        self,
        font: Any,
        text_value: str,
        color: tuple[int, int, int],
    ) -> Any:
        """Render one line through the platform's bounded text-surface cache.

        The installer repaints its pages continuously. Rasterizing identical
        copy on every frame pinned a full core on the reference Acer and made
        the pointer page feel frozen. Caching lives in
        ``greia_platform.typography`` so the installer and the launcher share
        one owner instead of growing parallel caches.
        """

        return self._typography.surface(font, text_value, color)

    def _inside(self, key: str, position: tuple[int, int]) -> bool:
        rect = self._buttons.get(key)
        return bool(rect and rect.collidepoint(position))

    def _fit_text(
        self,
        font: Any,
        text_value: str,
        color: tuple[int, int, int],
        max_width: int,
    ) -> Any:
        """Render one line, ellipsized so it cannot escape ``max_width``.

        Fixed-width buttons with unmeasured copy overflowed on the reference
        Acer: the reset control is 200 px wide and its Italian label is far
        longer than the English one, so text ran outside the button it belongs
        to. Layout here is measured rather than assumed.
        """

        if max_width <= 0:
            return self._text(font, text_value, color)
        if self._typography.surface_width(font, text_value) <= max_width:
            return self._text(font, text_value, color)
        # Trim the *translated* copy with the untranslated font: trimming the
        # English source produced a string with no translation, so a long
        # French line used to come out as truncated English.
        translated = self._tr(text_value)
        raw = getattr(font, "base", font)
        trimmed = translated
        while trimmed and self._typography.surface_width(raw, trimmed + "…") > max_width:
            trimmed = trimmed[:-1]
        return self._line(font, (trimmed + "…").rstrip(), color)

    def _render_signature(self, screen: Any) -> tuple[object, ...] | None:
        """Cheap fingerprint of everything the current frame would draw.

        Returning an unchanged signature means the composed frame would be
        pixel-identical, so the redraw and the display flip can be skipped.
        The installer used to repaint and re-flip the whole screen 30 times a
        second unconditionally, which is a large fixed cost on the reference
        Acer even once text rasterization and pointer probing are cached.

        The signature is derived from the live state rather than from a
        hand-maintained dirty flag, so a new piece of state cannot be silently
        forgotten. Anything unhashable, unexpected or slow is simply excluded,
        and any failure at all returns ``None``, which forces a redraw. Skipping
        is therefore only ever an optimisation: it can never leave a stale
        screen behind.

        That last promise was false twice over. ``InstallerState`` is a
        ``dataclass(slots=True)`` and therefore has no ``__dict__``, so
        ``vars()`` raised ``TypeError`` on every frame, the signature was
        always ``None`` — and because ``_last_render_signature`` also started
        as ``None``, ``None != None`` meant the installer never repainted from
        a state change on any page. Only an input event could refresh the
        screen, which is exactly what the reference Acer showed: nothing updated
        until the pointer moved. Both halves are fixed: slotted dataclasses are
        read through their declared fields, and the initial fingerprint is a
        sentinel that no computed signature can equal, so a genuinely
        uncomputable signature really does force a redraw.
        """

        def scalars(source: Any) -> tuple[object, ...]:
            items: Any
            if dataclasses.is_dataclass(source) and not isinstance(source, type):
                # A slots dataclass has no __dict__; vars() raises TypeError.
                items = (
                    (spec.name, getattr(source, spec.name, None))
                    for spec in dataclasses.fields(source)
                )
            else:
                try:
                    items = vars(source).items()
                except TypeError:
                    return ()
            parts: list[object] = []
            for name, value in items:
                if name.startswith("_typography") or name.startswith("_pointer_infos"):
                    continue
                if value is None or isinstance(value, (bool, int, float, str)):
                    parts.append((name, value))
                elif isinstance(value, enum.Enum):
                    parts.append((name, str(value)))
                elif isinstance(value, tuple) and all(
                    item is None or isinstance(item, (bool, int, float, str))
                    for item in value
                ):
                    parts.append((name, value))
            return tuple(parts)

        def fingerprint(value: Any, depth: int = 0) -> Any:
            """Bound a value down to something cheap, stable and comparable.

            The scalar walk above cannot see an Enum, a nested dataclass or a
            tuple of dataclasses, which is how ``page``, ``progress``,
            ``settings`` and the network list all fell out of the signature. It
            is bounded on purpose: this runs every frame, so collections are
            summarised by length and depth, and anything unrecognised collapses
            to its type name rather than being walked.
            """

            if value is None or isinstance(value, (bool, int, float, str)):
                return value
            if isinstance(value, enum.Enum):
                return str(value)
            if isinstance(value, (tuple, list)):
                if depth >= _SIGNATURE_MAX_DEPTH:
                    return (type(value).__name__, len(value))
                return (
                    type(value).__name__,
                    len(value),
                    tuple(
                        fingerprint(item, depth + 1)
                        for item in value[:_SIGNATURE_MAX_ITEMS]
                    ),
                )
            if dataclasses.is_dataclass(value) and not isinstance(value, type):
                if depth >= _SIGNATURE_MAX_DEPTH:
                    return type(value).__name__
                return tuple(
                    (
                        spec.name,
                        fingerprint(getattr(value, spec.name, None), depth + 1),
                    )
                    for spec in dataclasses.fields(value)
                )
            return type(value).__name__

        try:
            snapshot = self.wifi.snapshot
            return (
                tuple(screen.get_size()),
                scalars(self),
                # Every declared state field, including enums and nested
                # dataclasses. ``targets`` is covered separately below and is
                # skipped here so devices are not walked twice per frame.
                tuple(
                    (spec.name, fingerprint(getattr(self.state, spec.name, None)))
                    for spec in dataclasses.fields(self.state)
                    if spec.name != "targets"
                ),
                # The network list is a tuple of dataclasses; its observable
                # facts are named explicitly rather than left to be forgotten.
                (
                    str(snapshot.phase),
                    len(snapshot.networks),
                    snapshot.selected_index,
                    snapshot.connected_ssid,
                    bool(snapshot.error),
                    self.wifi.profile is not None,
                ),
                self._live_ssh.snapshot,
                len(self._pointer_infos_cache or ()),
                tuple(self.state.targets),
                self._live_tick(),
            )
        except Exception:
            return None

    def _live_tick(self) -> int:
        """Time bucket for the few states whose pixels change without input.

        The signature skips repaints of unchanged frames, but a held erase
        button, the install progress/elapsed time, a Wi-Fi scan or connect
        and the password caret all move on their own. Each gets a coarse
        bucket (at most 20 Hz while holding, 2-4 Hz otherwise) so those
        states repaint at that rate and every other page stays idle.
        """

        page = self.state.page
        now = time.monotonic()
        if page == InstallerPage.INSTALLING:
            return int(now * 4)
        if page == InstallerPage.CONFIRM and self._hold_started is not None:
            return int(now * 20)
        if page == InstallerPage.WIFI:
            snapshot = self.wifi.snapshot
            if snapshot.phase in {WifiSetupPhase.SCANNING, WifiSetupPhase.CONNECTING}:
                return int(now * 3)
            network = snapshot.selected_network
            if network is not None and network.security is WifiSecurity.PERSONAL:
                return int(now * 2)
        return 0

    def _write_status_record(self) -> None:
        """Mirror the current screen state to a small readable file.

        The installer draws everything on the framebuffer and the privileged
        service journals almost nothing, so a failure on real hardware could
        only be reported by an operator transcribing it by hand. This writes
        the page, progress phase and error text — nothing else — to the
        service's own runtime directory, so a failure can be read over the
        developer remote surface instead.

        Only state the UI already displays is written, the content is bounded,
        and it carries no nonce, digest, setting value or credential. It is
        rewritten only when the summary actually changes, so the common case
        costs one tuple comparison per frame.
        """

        path = Path("/run/greia-installer/status.json")
        try:
            progress = self.state.progress
            summary = (
                str(self.state.page),
                str(progress.stage) if progress is not None else "",
                round(float(progress.fraction), 4) if progress is not None else 0.0,
                (progress.detail if progress is not None else "")[:160],
                (self.state.error or "")[:256],
            )
            if summary == self._status_record:
                return
            self._status_record = summary
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(
                    {
                        "page": summary[0],
                        "phase": summary[1],
                        "fraction": summary[2],
                        "detail": summary[3],
                        "error": summary[4],
                        "monotonic": round(time.monotonic(), 3),
                    }
                ),
                encoding="utf-8",
            )
        except Exception:  # noqa: BLE001
            # A diagnostic must never be able to take the installer down. This
            # already happened once: a wrong attribute raised AttributeError,
            # which the narrower ``except OSError`` did not catch, and the
            # frame loop died with the service. Read-only state and a missing
            # runtime directory are not worth an install.
            self._status_record = None
            return

    def _release_boot_cover_once(self) -> None:
        """Release the early-boot cover exactly once, with a bounded retry.

        The installer runs unprivileged and the helper writes a marker, so the
        call can legitimately fail. It used to be retried every 0.5 s for the
        whole session: because a failure never sets ``_boot_released``, the
        reference Acer spawned the helper 2754 times in one boot, which is the
        CPU spin observed there. Retries are now capped and back off, so a
        helper that cannot succeed costs a bounded number of spawns and then
        stops rather than burning a core for as long as the page is open.
        """

        if self._boot_released:
            return
        if self._boot_handoff_attempts >= self.BOOT_HANDOFF_MAX_ATTEMPTS:
            return
        now = time.monotonic()
        delay = self.BOOT_HANDOFF_RETRY_SECONDS * (2 ** self._boot_handoff_attempts)
        if now < self._next_boot_handoff_attempt:
            return
        self._next_boot_handoff_attempt = now + delay
        self._boot_handoff_attempts += 1
        helper = Path("/usr/local/lib/greia-os/release-boot-cover")
        if helper.exists():
            import subprocess

            completed = subprocess.run(
                [str(helper)],
                check=False,
                shell=False,
                stdin=subprocess.DEVNULL,
            )
            self._boot_released = completed.returncode == 0


def _signal_level(signal_dbm: float) -> int:
    """Signal bars (1-4) for the Wi-Fi list, same thresholds as the labels."""
    if signal_dbm >= -50:
        return 4
    if signal_dbm >= -67:
        return 3
    if signal_dbm >= -78:
        return 2
    return 1


def _sentence(text: str) -> str:
    """Machine error text shown as a sentence (capitalised first letter)."""
    text = " ".join(str(text).split())
    return text[:1].upper() + text[1:] if text else text


def _wrap(text: str, font: Any, width: int) -> list[str]:
    """Greedy word wrap measured with ``font`` (already-final text)."""
    lines: list[str] = []
    line = ""
    for word in str(text).split():
        candidate = f"{line} {word}".strip()
        if line and font.size(candidate)[0] > width:
            lines.append(line)
            line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    return lines


def _signal_label(signal_dbm: float) -> str:
    if signal_dbm >= -50:
        return "Strong"
    if signal_dbm >= -67:
        return "Good"
    if signal_dbm >= -78:
        return "Fair"
    return "Weak"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(os.environ.get("GREIA_OS_ROOT", "/opt/greia-os")),
    )
    parser.add_argument(
        "--payload",
        type=Path,
        default=Path("/run/live/medium/payload/pip-rootfs.squashfs"),
    )
    parser.add_argument("--payload-digest", type=Path)
    parser.add_argument(
        "--transaction-socket",
        type=Path,
        default=None,
        help="Root install-transaction socket (8A.5 split; default is the platform socket)",
    )
    parser.add_argument(
        "--target-profile",
        type=Path,
        default=None,
        help="Greia-owned target-image profile the UI reads its profile id from",
    )
    parser.add_argument("--windowed", action="store_true")
    parser.add_argument("--demo", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    # Step 8A.5: the graphical UI is unprivileged by design. Destructive
    # installation runs only in the root transaction service, reached here
    # through nonce+digest alone, so no root gate belongs in this process.
    # Use --demo for the zero-disk-contact simulation.
    return InstallerApplication(
        root=args.root,
        payload=args.payload,
        payload_digest=args.payload_digest,
        windowed=args.windowed,
        demo=args.demo,
        transaction_socket=args.transaction_socket,
        target_profile=args.target_profile,
        hardware_controller=(
            None if args.demo else provisional_installer_hardware_controller()
        ),
    ).run()


if __name__ == "__main__":
    raise SystemExit(main())
