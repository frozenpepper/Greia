from __future__ import annotations

import argparse
import os
import queue
import threading
import time
from dataclasses import dataclass, replace
from enum import Enum, auto
from pathlib import Path
from typing import Any

from greia_platform.boot_logo import canonical_boot_logo as _canonical_boot_logo
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
from .power import PowerSupplyProbe
from .transaction_client import (
    InstallTransactionClient,
    PreparedConfirmation,
    TransactionClientError,
    live_target_facts,
    read_compatible_profile_id,
)
from .wifi import IwdWifiBackend, WifiSecurity
from .wifi_setup import DemoWifiBackend, WifiSetupController, WifiSetupPhase


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
    def install(self, request: InstallRequest, on_progress: Any = None) -> InstallResult:
        callback = on_progress or (lambda _: None)
        stages = (
            (0.10, "prepare", "Checking the selected disk"),
            (0.22, "erase", "Preparing the internal disk"),
            (0.38, "format", "Creating the Greia OS filesystem"),
            (0.68, "copy", "Copying the system"),
            (0.82, "configure", "Applying parent choices"),
            (0.94, "bootloader", "Making the disk bootable"),
            (1.0, "complete", "Installation complete"),
        )
        for fraction, stage, detail in stages:
            callback(InstallProgress(fraction, stage, detail))
            time.sleep(0.45)
        return InstallResult()


class InstallerApplication:
    HOLD_SECONDS = 2.0
    WIFI_ROWS_PER_PAGE = 3
    BUTTON_HEIGHT = 46

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
        self._last_render_signature: tuple[object, ...] | None = None
        self._cover_released = False
        self._pointer_seen = False
        self._display_probe_cache: Any = None
        self._display_probe_failed = False
        self._refresh_display_cache()
        self.wifi = WifiSetupController(
            DemoWifiBackend() if self.demo else IwdWifiBackend()
        )
        self._events: queue.Queue[InstallProgress | InstallResult | Exception] = (
            queue.Queue()
        )
        self._worker: threading.Thread | None = None
        self._hold_started: float | None = None
        self._buttons: dict[str, Any] = {}
        self._icon_cache: dict[tuple[str, int], Any] = {}
        self._exit_requested = False
        self._boot_released = False
        self._next_boot_handoff_attempt = 0.0
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
            handled_event = False
            for event in pygame.event.get():
                handled_event = True
                if event.type == pygame.QUIT and self.windowed:
                    running = False
                elif event.type == pygame.TEXTINPUT:
                    self._handle_text_input(event.text)
                elif event.type == pygame.KEYDOWN:
                    self._handle_keydown(event, pygame)
                    running = self._handle_key(event.key, pygame)
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
        if self.state.page != InstallerPage.WIFI:
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
            elif key == pygame.K_UP:
                self.wifi.move_selection(-1)
            elif key == pygame.K_DOWN:
                self.wifi.move_selection(1)
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
            self.state.page = InstallerPage.POINTER
            self._pointer_focus = 0
            self._pointer_test_feedback = ""
            self._preview_pointer_settings()
        elif self.state.page == InstallerPage.POINTER:
            self._refresh_display_cache()
            self.state.page = InstallerPage.DISPLAY
        elif self.state.page == InstallerPage.DISPLAY:
            self.state.page = InstallerPage.WIFI
            self.wifi.begin()
        elif self.state.page == InstallerPage.SETTINGS:
            # Legacy combined page (superseded by POINTER + DISPLAY).
            self.state.page = InstallerPage.WIFI
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
                import subprocess

                subprocess.run(
                    ["systemctl", "poweroff"],
                    check=False,
                    shell=False,
                    stdin=subprocess.DEVNULL,
                )

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
            self._hold_started = time.monotonic()

    def _handle_mouse_up(self, position: tuple[int, int]) -> None:
        if self._inside("back", position):
            self._hold_started = None
            self._back()
            return
        if self.state.page == InstallerPage.CONFIRM:
            self._hold_started = None
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
            if self._inside("wifi-refresh", position):
                self.wifi.refresh()
                return
            if self._inside("wifi-skip", position):
                self.wifi.skip()
                self.state.page = InstallerPage.CONFIRM
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
        """Require one uninterrupted pointer hold inside the erase button."""

        if self._hold_started is None:
            return
        if self.state.page != InstallerPage.CONFIRM:
            self._hold_started = None
            return
        pressed = pygame.mouse.get_pressed(num_buttons=3)
        position = pygame.mouse.get_pos()
        if not pressed[0] or not self._inside("install", position):
            self._hold_started = None
            return
        if time.monotonic() - self._hold_started >= self.HOLD_SECONDS:
            self._hold_started = None
            self._start_installation()

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
                    InstallProgress(0.05, "prepare", "Confirming the selected disk")
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
                    InstallProgress(0.10, "install", "Installing Greia OS")
                )
                client.execute(
                    transaction_nonce=prepared.transaction_nonce,
                    plan_digest=prepared.plan_digest,
                )
                self._events.put(InstallResult())
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
                self.state.progress = event
            elif isinstance(event, InstallResult):
                self.state.result = event
                self.state.page = InstallerPage.COMPLETE
                self._worker = None
            elif isinstance(event, Exception):
                self.state.error = str(event) or event.__class__.__name__
                self.state.page = InstallerPage.ERROR
                self._worker = None

    def _draw(self, screen: Any, pygame: Any) -> None:
        width, height = screen.get_size()
        background = (247, 235, 203)
        panel = (255, 250, 240)
        text = (61, 44, 31)
        accent = (255, 194, 52)
        danger = (181, 46, 46)
        success = (51, 128, 76)
        screen.fill(background)
        self._buttons.clear()
        font = self._typography.font(FontRole.CONTROL, max(27, height // 22))
        title_font = self._typography.font(FontRole.TITLE, max(42, height // 12))
        small_font = self._typography.font(FontRole.BODY, max(22, height // 28))

        page = self.state.page
        if page == InstallerPage.WELCOME:
            self._hero_logo(
                screen,
                pygame,
                width,
                height,
            )
            self._button(
                screen,
                pygame,
                "primary",
                "Start",
                accent,
                text,
                font,
                (width - 180, height - 60),
                220,
            )
            return

        main = pygame.Rect(
            max(24, width * 0.06),
            max(20, height * 0.06),
            width * 0.88,
            height * 0.88,
        )
        pygame.draw.rect(screen, panel, main, border_radius=28)
        if page == InstallerPage.LAYOUT:
            self._draw_layout(screen, pygame, main, font, title_font, small_font, text, accent, background)
        elif page == InstallerPage.TARGET:
            self._center_title(
                screen,
                "Choose the internal disk",
                title_font,
                text,
                main.top + 32,
            )
            if not self.state.targets:
                self._center_text(
                    screen,
                    "No safe internal disk was found.",
                    font,
                    danger,
                    height // 2,
                )
            for index, target in enumerate(self.state.targets[:4]):
                rect = pygame.Rect(
                    main.left + 60,
                    main.top + 120 + index * 86,
                    main.width - 120,
                    68,
                )
                selected = index == self.state.selected_target
                pygame.draw.rect(
                    screen, accent if selected else background, rect, border_radius=18
                )
                pygame.draw.rect(
                    screen,
                    text,
                    rect,
                    width=3 if selected else 1,
                    border_radius=18,
                )
                self._buttons[f"target-{index}"] = rect
                label = self._text(font, target.display_name, text)
                screen.blit(label, label.get_rect(midleft=(rect.left + 24, rect.centery)))
            self._navigation(
                screen,
                pygame,
                main,
                font,
                accent,
                text,
                enabled=self.state.target is not None,
            )
        elif page == InstallerPage.POINTER:
            self._draw_pointer_page(
                screen, pygame, main, font, title_font, small_font, text, accent
            )
        elif page == InstallerPage.DISPLAY:
            self._draw_display_page(
                screen, pygame, main, font, title_font, small_font, text, accent, danger
            )
        elif page == InstallerPage.SETTINGS:
            # Legacy combined page (superseded by POINTER + DISPLAY).
            self._center_title(
                screen, "Input and screen", title_font, text, main.top + 26
            )
            self._toggle_row(
                screen,
                pygame,
                "tap",
                "Tap touchpad to click",
                self.state.settings.touchpad_tap,
                font,
                text,
                accent,
                main.top + 110,
            )
            self._toggle_row(
                screen,
                pygame,
                "natural",
                "Natural scrolling",
                self.state.settings.natural_scrolling,
                font,
                text,
                accent,
                main.top + 178,
            )
            self._preset_row(
                screen,
                pygame,
                "mouse",
                "Mouse feel",
                speed_to_preset(self.state.settings.mouse_speed),
                font,
                text,
                accent,
                main.top + 246,
            )
            self._preset_row(
                screen,
                pygame,
                "touch",
                "Touchpad feel",
                speed_to_preset(self.state.settings.touchpad_speed),
                font,
                text,
                accent,
                main.top + 314,
            )
            self._value_row(
                screen,
                pygame,
                "resolution",
                "Screen resolution",
                self.state.settings.resolution,
                font,
                text,
                accent,
                main.top + 382,
            )
            self._navigation(screen, pygame, main, font, accent, text, enabled=True)
        elif page == InstallerPage.WIFI:
            self._draw_wifi(
                screen,
                pygame,
                main,
                font,
                title_font,
                small_font,
                background,
                text,
                accent,
                danger,
                success,
            )
        elif page == InstallerPage.CONFIRM:
            self._center_title(
                screen, "Ready to install", title_font, text, main.top + 34
            )
            target = self.state.target
            target_text = target.display_name if target else "Unknown disk"
            self._center_text(screen, target_text, font, text, main.top + 125)
            wifi_text = (
                f"Wi-Fi: {self.wifi.profile.ssid}"
                if self.wifi.profile is not None
                else "Wi-Fi: set up later"
            )
            self._center_text(screen, wifi_text, small_font, text, main.top + 170)
            self._center_text(
                screen,
                "Everything currently on this disk will be erased.",
                font,
                danger,
                main.top + 220,
            )
            self._center_text(
                screen,
                "Tap-to-click starts disabled and can be changed later.",
                small_font,
                text,
                main.top + 265,
            )
            if self.display_install_block_reason() is not None:
                self._center_text(
                    screen,
                    "This screen is not fully supported — install is paused.",
                    small_font,
                    danger,
                    main.top + 300,
                )
            rect = self._button(
                screen,
                pygame,
                "install",
                "Hold to erase and install",
                danger,
                (255, 255, 255),
                font,
                (width // 2, main.bottom - 120),
                340,
            )
            if self._hold_started is not None:
                fraction = min(
                    1.0,
                    (time.monotonic() - self._hold_started) / self.HOLD_SECONDS,
                )
                # Redraw the whole button surface so no prior label bleeds
                # through the progress fill.
                pygame.draw.rect(screen, danger, rect, border_radius=18)
                fill = rect.copy()
                fill.width = int(rect.width * fraction)
                pygame.draw.rect(screen, (120, 24, 24), fill, border_radius=18)
                label = self._text(font, "Keep holding…", (255, 255, 255))
                screen.blit(label, label.get_rect(center=rect.center))
            self._back_button(screen, pygame, font, accent, text, main)
        elif page == InstallerPage.INSTALLING:
            self._center_title(
                screen, "Installing", title_font, text, main.top + 50
            )
            self._icon(
                screen,
                pygame,
                "robot",
                min(180, int(height * 0.3)),
                (width // 2, main.top + 220),
            )
            track = pygame.Rect(
                main.left + 100, main.bottom - 170, main.width - 200, 28
            )
            pygame.draw.rect(screen, background, track, border_radius=14)
            fill = track.copy()
            fill.width = int(track.width * self.state.progress.fraction)
            pygame.draw.rect(screen, accent, fill, border_radius=14)
            self._center_text(
                screen, self.state.progress.detail, font, text, main.bottom - 105
            )
            self._center_text(
                screen,
                "Do not remove the USB key.",
                small_font,
                danger,
                main.bottom - 65,
            )
        elif page == InstallerPage.COMPLETE:
            self._center_title(
                screen, "All done!", title_font, text, main.top + 28
            )
            self._icon(
                screen,
                pygame,
                "check",
                min(125, int(height * 0.22)),
                (width // 2, main.top + 150),
            )
            self._center_text(
                screen,
                "Greia is installed and ready.",
                font,
                text,
                main.top + 245,
            )
            self._center_text(
                screen,
                "Your Parent login is:  greia  /  greia",
                font,
                accent,
                main.top + 305,
            )
            self._center_text(
                screen,
                "You can change it in Greia Parents after first boot.",
                small_font,
                text,
                main.top + 350,
            )
            message = "Close the demo" if self.demo else "I'm ready — turn off"
            self._button(
                screen,
                pygame,
                "primary",
                message,
                accent,
                text,
                font,
                (width // 2, main.bottom - 40),
                420,
            )
        elif page == InstallerPage.ERROR:
            self._center_title(
                screen,
                "Installation stopped",
                title_font,
                danger,
                main.top + 45,
            )
            self._icon(
                screen,
                pygame,
                "close_button",
                min(160, int(height * 0.28)),
                (width // 2, main.top + 210),
            )
            message = (
                self.state.error
                + " The selected disk may be incomplete if installation had already begun."
            )
            self._wrapped_text(
                screen,
                message,
                small_font,
                text,
                pygame.Rect(main.left + 100, main.top + 300, main.width - 200, 150),
            )
            self._back_button(screen, pygame, font, accent, text, main)

    POINTER_HEADER_H = 96
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
        self, panel_height: int, setting_count: int
    ) -> tuple[int, int, int]:
        """Fit the pointer page into ``panel_height`` by measurement.

        Returns ``(row_height, step, test_target_size)``. The page previously
        used a hard-coded 56 px step and a hard-coded 64 px test target, and its
        content is taller than the 600 px reference display: rows overlapped and
        the reset control fell outside the panel. Everything is now derived from
        the panel that is actually available.

        Navigation buttons are centred on ``main.bottom - 40`` and are
        ``BUTTON_HEIGHT`` tall, so the last 63 px of the panel belong to them.
        The test strip below the final row is a label, a gap, the square
        targets, the status line and the 40 px reset button, so its height is
        ``label + gap + target + tail``. Drawing the label clear of the
        targets is why the label height is part of the budget at all.

        The test targets start at the 9 mm physical touch floor because they
        are what a child aims at, and are only shrunk below it when the row
        count would otherwise collide with the navigation row. Setting rows are
        keyboard-navigable, so they may compress to :attr:`POINTER_ROW_MIN`
        before the targets are reduced, and to :attr:`POINTER_ROW_HARD_MIN`
        only after the targets have given all they will.
        """

        count = max(1, int(setting_count))
        available = panel_height - self.POINTER_HEADER_H - self.POINTER_NAV_RESERVE
        nav_top = panel_height - self.POINTER_NAV_RESERVE - 5
        floor = min(self.POINTER_TARGET_FLOOR, max(1, available // 4))
        target_size = max(floor, min(self.POINTER_TARGET_HINT, available // 4))

        def layout(target: int) -> tuple[int, int, int]:
            strip = (
                self.POINTER_LABEL_H
                + self.POINTER_STRIP_LABEL_GAP
                + target
                + self.POINTER_STRIP_TAIL
            )
            room = available - strip
            row = int(room / count) - self.POINTER_ROW_GAP
            row = max(self.POINTER_ROW_HARD_MIN, min(self.POINTER_ROW_MAX, row))
            step = row + self.POINTER_ROW_GAP
            return row, step, count * step + strip

        # Setting rows are keyboard-navigable and keep their readable floor.
        # The test targets give way first: they are the least critical control
        # on this page, because the same test is reachable with 1 2 3. Shrinking
        # them before any row may fall under its floor means a dense pointer
        # inventory degrades instead of overlapping the navigation row.
        while True:
            row, step, bottom = layout(target_size)
            if bottom <= nav_top or target_size <= self.POINTER_TARGET_HARD_MIN:
                break
            target_size = max(self.POINTER_TARGET_HARD_MIN, target_size - 4)
        return row, step, target_size

    def _draw_pointer_page(
        self,
        screen: Any,
        pygame: Any,
        main: Any,
        font: Any,
        title_font: Any,
        small_font: Any,
        text: tuple[int, int, int],
        accent: tuple[int, int, int],
    ) -> None:
        """Deliberate Pointer Setup page: presets, gated toggles, test area."""
        self._clamp_pointer_focus()
        rows = self.pointer_rows()
        self._center_title(screen, "Pointer setup", title_font, text, main.top + 18)
        self._center_text(
            screen, "Pointer feel", small_font, text, main.top + 18 + 52
        )

        # Measure the vertical budget instead of assuming it. This page used
        # to use a hard-coded 56 px step and a hard-coded 64 px test target, and
        # its content is simply taller than the 600 px reference display: the
        # reset control fell outside the panel and rows overlapped. The row
        # height, the gaps and the test target are now derived from the panel
        # that is actually available, each floored so a child's touch target
        # never collapses below the physical minimum.
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
        row_h, step, target_size = self._pointer_vertical_budget(
            main.height, setting_count
        )
        y = main.top + self.POINTER_HEADER_H
        if "tap" in rows:
            self._toggle_row(
                screen, pygame, "tap", "Tap touchpad to click",
                self.state.settings.touchpad_tap, font, text, accent, y, row_h,
            )
            y += step
        if "disable-while-typing" in rows:
            self._toggle_row(
                screen, pygame, "disable-while-typing", "Disable while typing",
                self.state.settings.disable_while_typing, font, text, accent, y, row_h,
            )
            y += step
        if "natural" in rows:
            self._toggle_row(
                screen, pygame, "natural", "Natural scrolling",
                self.state.settings.natural_scrolling, font, text, accent, y, row_h,
            )
            y += step
        if "touchpad-preset" in rows:
            self._preset_row(
                screen, pygame, "touch", "Touchpad feel",
                speed_to_preset(self.state.settings.touchpad_speed),
                font, text, accent, y, row_h,
            )
            y += step
        if "mouse-preset" in rows:
            self._preset_row(
                screen, pygame, "mouse", "Mouse feel",
                speed_to_preset(self.state.settings.mouse_speed),
                font, text, accent, y, row_h,
            )
            y += step
        elif "mouse-preset-labeled" in rows:
            self._preset_row(
                screen, pygame, "mouse", "Mouse feel (when a mouse is attached)",
                speed_to_preset(self.state.settings.mouse_speed),
                font, text, accent, y, row_h,
            )
            y += step
        # Test strip: three large dispersed targets with click feedback.
        width = screen.get_size()[0]
        strip_label_h = max(1, small_font.get_linesize())
        target_mid = y + strip_label_h + 12 + target_size // 2
        centers = (
            (int(width * 0.24), target_mid),
            (int(width * 0.50), target_mid),
            (int(width * 0.76), target_mid),
        )
        # The label used to be centred at y+2, which is exactly where the
        # target boxes begin, so it overlapped them. Put it clear of the row.
        strip_label_h = max(1, small_font.get_linesize())
        self._center_text(
            screen, "Try it here", small_font, text, y + strip_label_h // 2
        )
        for index, center in enumerate(centers):
            key = f"test-{index + 1}"
            rect = pygame.Rect(0, 0, target_size, target_size)
            rect.center = center
            focused = self.focused_pointer_row() == key
            pygame.draw.rect(
                screen, accent if focused else (247, 235, 203), rect, border_radius=16
            )
            pygame.draw.rect(
                screen, text, rect, width=3 if focused else 1, border_radius=16
            )
            label = self._text(font, str(index + 1), text)
            screen.blit(label, label.get_rect(center=rect.center))
            self._buttons[key] = rect
        note = self._pointer_unavailable_note()
        if note:
            self._center_fitted_text(
                screen,
                note,
                small_font,
                text,
                y + strip_label_h // 2,
                int(screen.get_width() * 0.86),
            )
        feedback = self._pointer_test_feedback or "Click a circle, or press 1 2 3"
        status = feedback
        if self._pointer_preview_error:
            status = f"{feedback} · {self._pointer_preview_error}"
        self._center_fitted_text(
            screen,
            status,
            small_font,
            text,
            target_mid + target_size // 2 + 14,
            int(screen.get_width() * 0.86),
        )
        reset_label = self._text(small_font, "Reset pointer feel", text)
        reset_width = min(
            screen.get_width() - 80, max(200, reset_label.get_width() + 40)
        )
        reset_rect = pygame.Rect(0, 0, reset_width, 40)
        reset_rect.midtop = (
            screen.get_size()[0] // 2, target_mid + target_size // 2 + 32
        )
        pygame.draw.rect(screen, accent, reset_rect, border_radius=14)
        reset_label = self._fit_text(
            small_font, "Reset pointer feel", text, reset_rect.width - 24
        )
        screen.blit(reset_label, reset_label.get_rect(center=reset_rect.center))
        self._buttons["pointer-reset"] = reset_rect
        self._navigation(screen, pygame, main, font, accent, text, enabled=True)

    def _draw_display_page(
        self,
        screen: Any,
        pygame: Any,
        main: Any,
        font: Any,
        title_font: Any,
        small_font: Any,
        text: tuple[int, int, int],
        accent: tuple[int, int, int],
        danger: tuple[int, int, int],
    ) -> None:
        """Display page: supported modes, physical facts, suitability copy."""
        facts = self.display_facts()
        self._center_title(screen, "Display", title_font, text, main.top + 22)
        if self.state.settings.resolution == "auto":
            resolution_line = "Resolution: Automatic"
        else:
            resolution_line = f"Resolution: {self.state.settings.resolution}"
        self._center_text(screen, resolution_line, font, text, main.top + 110)
        supported = facts["supported_mode_ids"]
        if supported:
            shown = ", ".join(supported[:4])
            self._center_text(
                screen, f"Greia screens: {shown}", small_font, text, main.top + 155
            )
        else:
            self._center_text(
                screen, "Greia screens: Automatic", small_font, text, main.top + 155
            )
        metrics = facts["metrics"]
        if metrics is not None and bool(
            getattr(metrics, "physical_size_known", False)
        ):
            self._center_text(
                screen,
                "Screen size detected automatically",
                small_font,
                text,
                main.top + 190,
            )
        else:
            self._center_text(
                screen,
                "Safe display: installer uses safe pixels (1024x600)",
                small_font,
                text,
                main.top + 190,
            )
        self._center_text(
            screen, self.display_status_copy()[:90], font, text, main.top + 235
        )
        if self.display_install_block_reason() is not None:
            self._center_text(
                screen,
                "This screen is not fully supported — install is paused.",
                small_font,
                danger,
                main.top + 275,
            )
        self._value_row(
            screen, pygame, "resolution", "Screen resolution",
            self.state.settings.resolution, font, text, accent, main.top + 310,
        )
        self._navigation(screen, pygame, main, font, accent, text, enabled=True)

    def _draw_layout(
        self,
        screen: Any,
        pygame: Any,
        main: Any,
        font: Any,
        title_font: Any,
        small_font: Any,
        text: tuple[int, int, int],
        accent: tuple[int, int, int],
        background: tuple[int, int, int],
    ) -> None:
        self._center_title(
            screen, "Your keyboard", title_font, text, main.top + 26
        )
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
        if remaining:
            probe = remaining[0]
            self._center_text(
                screen,
                probe.instruction,
                title_font,
                accent,
                main.top + 110,
            )
            self._center_text(
                screen,
                "I'm listening — press that key now.",
                font,
                text,
                main.top + 180,
            )
            done = len(self._layout_probe_results)
            self._center_text(
                screen,
                f"{done} of {len(PROBES)} pressed",
                small_font,
                accent,
                main.top + 250,
            )
            self._center_text(
                screen,
                f"After {5 - done_count} more key{'s' if 5 - done_count != 1 else ''} I'll show a list to confirm.",
                small_font,
                text,
                main.top + 300,
            )
            if done_count >= 3:
                self._center_text(
                    screen,
                    "Or press Enter to see the list now.",
                    small_font,
                    text,
                    main.top + 330,
                )
        else:
            self._draw_layout_selector(
                screen,
                pygame,
                main,
                font,
                small_font,
                text,
                accent,
                background,
            )
        self._back_button(screen, pygame, font, accent, text, main)
        if not remaining:
            self._button(
                screen,
                pygame,
                "primary",
                "Confirm",
                accent,
                text,
                font,
                (screen.get_width() // 2, self._bottom_row_y(main)),
                220,
            )

    def _draw_layout_selector(
        self,
        screen: Any,
        pygame: Any,
        main: Any,
        font: Any,
        small_font: Any,
        text: tuple[int, int, int],
        accent: tuple[int, int, int],
        background: tuple[int, int, int],
    ) -> None:
        inferred_id = infer_layout(self._layout_probe_results)
        all_ids = self._all_layout_ids
        rows_visible = min(6, len(all_ids))
        self._layout_scroll_to(self._layout_alternative_index, rows_visible)
        top = main.top + 90
        row_height = 50
        for offset in range(rows_visible):
            index = self._layout_scroll + offset
            if index >= len(all_ids):
                break
            layout_id = all_ids[index]
            layout = layout_by_id(layout_id)
            rect = pygame.Rect(
                main.left + 90, top + offset * row_height, main.width - 180, 44
            )
            selected = index == self._layout_alternative_index
            inferred = layout_id == inferred_id
            if selected:
                fill = accent
            elif inferred:
                fill = (240, 225, 180)
            else:
                fill = background
            pygame.draw.rect(screen, fill, rect, border_radius=14)
            pygame.draw.rect(
                screen,
                text,
                rect,
                width=3 if selected else 1,
                border_radius=14,
            )
            self._buttons[f"layout-{index}"] = rect
            label = layout.label
            if inferred:
                label = "> " + label
            image = self._text(font, label, text)
            screen.blit(image, (rect.left + 16, rect.top + 8))
        self._center_text(
            screen,
            "Use Up/Down or click to choose, then Enter to confirm",
            small_font,
            text,
            top + rows_visible * row_height + 18,
        )

    def _draw_wifi(
        self,
        screen: Any,
        pygame: Any,
        main: Any,
        font: Any,
        title_font: Any,
        small_font: Any,
        background: tuple[int, int, int],
        text: tuple[int, int, int],
        accent: tuple[int, int, int],
        danger: tuple[int, int, int],
        success: tuple[int, int, int],
    ) -> None:
        snapshot = self.wifi.snapshot
        self._center_title(
            screen, "Wi-Fi (optional)", title_font, text, main.top + 20
        )
        self._center_text(
            screen,
            "Connect now, or set it up later in Greia Parents.",
            small_font,
            text,
            main.top + 40 + title_font.get_height(),
        )

        if snapshot.phase is WifiSetupPhase.SCANNING:
            self._center_text(
                screen, "Looking for Wi-Fi networks…", font, text, main.centery
            )
        elif snapshot.phase is WifiSetupPhase.CONNECTING:
            selected = snapshot.selected_network
            name = selected.ssid if selected is not None else "Wi-Fi"
            self._center_text(
                screen,
                f"Connecting to {name}…",
                font,
                text,
                main.centery,
            )
        elif snapshot.phase is WifiSetupPhase.UNAVAILABLE:
            self._center_text(
                screen,
                "No wireless adapter is available. You can continue offline.",
                font,
                text,
                main.centery - 15,
            )
            self._button(
                screen,
                pygame,
                "primary",
                "Continue offline",
                accent,
                text,
                font,
                (screen.get_width() - 190, self._bottom_row_y(main)),
                230,
            )
        elif snapshot.phase is WifiSetupPhase.CONNECTED:
            self._center_text(
                screen,
                f"Connected to {snapshot.connected_ssid}",
                font,
                success,
                main.centery - 20,
            )
            self._center_text(
                screen,
                "This network will be ready after the first boot.",
                small_font,
                text,
                main.centery + 25,
            )
            self._button(
                screen,
                pygame,
                "primary",
                "Continue",
                accent,
                text,
                font,
                (screen.get_width() - 185, self._bottom_row_y(main)),
                220,
            )
        else:
            self._draw_wifi_networks(
                screen,
                pygame,
                main,
                font,
                title_font,
                small_font,
                background,
                text,
                accent,
                danger,
            )

        if snapshot.error and snapshot.phase is not WifiSetupPhase.UNAVAILABLE:
            self._center_text(
                screen,
                snapshot.error[:90],
                small_font,
                danger,
                main.bottom - 93,
            )

        self._back_button(screen, pygame, font, accent, text, main)
        if snapshot.phase not in {
            WifiSetupPhase.CONNECTED,
            WifiSetupPhase.UNAVAILABLE,
            WifiSetupPhase.CONNECTING,
        }:
            self._button(
                screen,
                pygame,
                "wifi-refresh",
                "Refresh",
                background,
                text,
                small_font,
                (screen.get_width() // 2, self._bottom_row_y(main)),
                170,
            )
            self._button(
                screen,
                pygame,
                "wifi-skip",
                "Skip for now",
                accent,
                text,
                small_font,
                (screen.get_width() - 170, self._bottom_row_y(main)),
                200,
            )

    def _draw_wifi_networks(
        self,
        screen: Any,
        pygame: Any,
        main: Any,
        font: Any,
        title_font: Any,
        small_font: Any,
        background: tuple[int, int, int],
        text: tuple[int, int, int],
        accent: tuple[int, int, int],
        danger: tuple[int, int, int],
    ) -> None:
        snapshot = self.wifi.snapshot
        if not snapshot.networks:
            self._center_text(
                screen,
                "No networks found. Refresh, or continue offline.",
                font,
                text,
                main.centery,
            )
            return

        rows_top = main.top + 40 + title_font.get_height() + small_font.get_height() + 8
        page_start = (
            snapshot.selected_index // self.WIFI_ROWS_PER_PAGE
        ) * self.WIFI_ROWS_PER_PAGE
        visible = snapshot.networks[page_start : page_start + self.WIFI_ROWS_PER_PAGE]
        for offset, network in enumerate(visible):
            index = page_start + offset
            rect = pygame.Rect(
                main.left + 70,
                rows_top + offset * 62,
                main.width - 140,
                52,
            )
            selected = index == snapshot.selected_index
            supported = network.installer_supported
            fill = accent if selected else background
            if not supported:
                fill = (232, 228, 217)
            pygame.draw.rect(screen, fill, rect, border_radius=15)
            pygame.draw.rect(
                screen,
                text,
                rect,
                width=3 if selected else 1,
                border_radius=15,
            )
            self._buttons[f"wifi-{index}"] = rect
            label = self._text(font, network.ssid, text)
            screen.blit(label, (rect.left + 16, rect.top + 10))
            if network.security is WifiSecurity.OPEN:
                security = "Open"
            elif network.security is WifiSecurity.PERSONAL:
                security = "Password"
            else:
                security = "Enterprise — later"
            strength = _signal_label(network.signal_dbm)
            detail = self._text(small_font, f"{security} · {strength}", text)
            screen.blit(detail, detail.get_rect(midright=(rect.right - 16, rect.centery)))

        network = snapshot.selected_network
        if network is None:
            return
        controls_y = rows_top + self.WIFI_ROWS_PER_PAGE * 62 + 16
        if network.security is WifiSecurity.PERSONAL:
            password_rect = pygame.Rect(
                main.left + 90, controls_y, main.width - 340, 48
            )
            pygame.draw.rect(screen, background, password_rect, border_radius=14)
            pygame.draw.rect(screen, text, password_rect, width=1, border_radius=14)
            passphrase = snapshot.passphrase
            if passphrase:
                revealed_index = None
                if self._last_password_character is not None:
                    character, typed_at = self._last_password_character
                    if time.monotonic() - typed_at < 1.0:
                        revealed_index = len(passphrase) - 1
                # Render masked with the last char briefly revealed
                segments = []
                if revealed_index is not None and passphrase:
                    segments.append("*" * (len(passphrase) - 1))
                    segments.append(passphrase[-1])
                else:
                    segments.append("*" * len(passphrase))
                text_render = self._text(small_font, "".join(segments), text)
            else:
                text_render = self._text(small_font, "Wi-Fi password", (160, 150, 135))
            screen.blit(
                text_render,
                (password_rect.left + 16, password_rect.top + 12),
            )
            # Blinking caret after the text
            caret_on = int(time.monotonic() * 2) % 2 == 0
            caret_x = password_rect.left + 16 + text_render.get_width() + 4
            if caret_on:
                pygame.draw.rect(
                    screen,
                    accent,
                    (caret_x, password_rect.top + 12, 2, text_render.get_height()),
                )
            self._buttons["wifi-password"] = password_rect
        if network.installer_supported:
            self._button(
                screen,
                pygame,
                "primary",
                "Connect",
                accent,
                text,
                font,
                (main.right - 165, controls_y + 24),
                220,
            )
        else:
            note = self._text(small_font, "Enterprise Wi-Fi can be configured later in Greia Parents.", danger)
            screen.blit(note, note.get_rect(center=(main.centerx, controls_y + 24)))

    def _bottom_row_y(self, main: Any) -> int:
        return main.bottom - 40

    def _navigation(
        self,
        screen: Any,
        pygame: Any,
        main: Any,
        font: Any,
        accent: tuple[int, int, int],
        text: tuple[int, int, int],
        *,
        enabled: bool,
    ) -> None:
        self._back_button(screen, pygame, font, accent, text, main)
        color = accent if enabled else (200, 195, 180)
        self._button(
            screen,
            pygame,
            "primary",
            "Continue",
            color,
            text,
            font,
            (main.right - 145, self._bottom_row_y(main)),
            220,
        )

    def _back_button(
        self,
        screen: Any,
        pygame: Any,
        font: Any,
        accent: tuple[int, int, int],
        text: tuple[int, int, int],
        main: Any,
    ) -> None:
        self._button(
            screen,
            pygame,
            "back",
            "Back",
            accent,
            text,
            font,
            (main.left + 120, self._bottom_row_y(main)),
            170,
        )

    def _toggle_row(
        self,
        screen: Any,
        pygame: Any,
        key: str,
        label: str,
        value: bool,
        font: Any,
        text: tuple[int, int, int],
        accent: tuple[int, int, int],
        y: int,
        height: int = 54,
    ) -> None:
        rect = pygame.Rect(
            screen.get_width() * 0.16, y, screen.get_width() * 0.68, height
        )
        pygame.draw.rect(screen, (247, 235, 203), rect, border_radius=16)
        state_h = min(40, max(28, height - 14))
        state_rect = pygame.Rect(
            rect.right - 116, rect.centery - state_h // 2, 98, state_h
        )
        label_surface = self._fit_text(
            font, label, text, state_rect.left - rect.left - 36
        )
        screen.blit(
            label_surface,
            (rect.left + 18, rect.centery - label_surface.get_height() // 2),
        )
        pygame.draw.rect(
            screen, accent if value else (180, 175, 165), state_rect, border_radius=20
        )
        knob_x = state_rect.right - 20 if value else state_rect.left + 20
        pygame.draw.circle(
            screen,
            (255, 255, 255),
            (knob_x, state_rect.centery),
            max(9, state_h // 2 - 5),
        )
        self._buttons[key] = rect

    def _preset_row(
        self,
        screen: Any,
        pygame: Any,
        key: str,
        label: str,
        preset_name: str,
        font: Any,
        text: tuple[int, int, int],
        accent: tuple[int, int, int],
        y: int,
        height: int = 54,
    ) -> None:
        rect = pygame.Rect(
            screen.get_width() * 0.16, y, screen.get_width() * 0.68, height
        )
        pygame.draw.rect(screen, (247, 235, 203), rect, border_radius=16)
        screen.blit(self._text(font, label, text), (rect.left + 18, rect.top + 13))
        btn = min(42, max(26, height - 12))
        minus = pygame.Rect(rect.right - 268, rect.centery - btn // 2, 46, btn)
        plus = pygame.Rect(rect.right - 58, rect.centery - btn // 2, 46, btn)
        for button_rect, glyph in ((minus, "−"), (plus, "+")):
            pygame.draw.rect(screen, accent, button_rect, border_radius=14)
            glyph_image = self._text(font, glyph, text)
            screen.blit(glyph_image, glyph_image.get_rect(center=button_rect.center))
        value_image = self._text(font, preset_name, text)
        screen.blit(
            value_image, value_image.get_rect(center=(rect.right - 140, rect.centery))
        )
        self._buttons[f"{key}-minus"] = minus
        self._buttons[f"{key}-plus"] = plus

    def _value_row(
        self,
        screen: Any,
        pygame: Any,
        key: str,
        label: str,
        value: str,
        font: Any,
        text: tuple[int, int, int],
        accent: tuple[int, int, int],
        y: int,
        height: int = 54,
    ) -> None:
        rect = pygame.Rect(
            screen.get_width() * 0.16, y, screen.get_width() * 0.68, height
        )
        pygame.draw.rect(screen, (247, 235, 203), rect, border_radius=16)
        value_h = min(42, max(26, height - 12))
        value_rect = pygame.Rect(
            rect.right - 190, rect.centery - value_h // 2, 172, value_h
        )
        label_surface = self._fit_text(
            font, label, text, value_rect.left - rect.left - 36
        )
        screen.blit(
            label_surface,
            (rect.left + 18, rect.centery - label_surface.get_height() // 2),
        )
        pygame.draw.rect(screen, accent, value_rect, border_radius=14)
        value_image = self._fit_text(font, value, text, value_rect.width - 16)
        screen.blit(value_image, value_image.get_rect(center=value_rect.center))
        self._buttons[key] = rect

    def _button(
        self,
        screen: Any,
        pygame: Any,
        key: str,
        label: str,
        background: tuple[int, int, int],
        foreground: tuple[int, int, int],
        font: Any,
        center: tuple[int, int],
        width: int,
    ) -> Any:
        rect = pygame.Rect(0, 0, width, self.BUTTON_HEIGHT)
        rect.center = center
        pygame.draw.rect(screen, background, rect, border_radius=18)
        image = self._fit_text(font, label, foreground, width - 24)
        screen.blit(image, image.get_rect(center=rect.center))
        self._buttons[key] = rect
        return rect

    def _icon(
        self,
        screen: Any,
        pygame: Any,
        icon_id: str,
        size: int,
        center: tuple[int, int],
    ) -> None:
        key = (icon_id, size)
        image = self._icon_cache.get(key)
        if image is None:
            path = (
                self.root
                / "assets"
                / "icons"
                / "core"
                / "v1"
                / "256"
                / f"{icon_id}.png"
            )
            image = pygame.image.load(str(path)).convert_alpha()
            image = pygame.transform.smoothscale(image, (size, size))
            self._icon_cache[key] = image
        screen.blit(image, image.get_rect(center=center))

    def _boot_logo(
        self,
        screen: Any,
        pygame: Any,
        center: tuple[int, int],
        max_height: int,
    ) -> None:
        key = ("boot-logo", max_height)
        image = self._icon_cache.get(key)
        if image is None:
            frame_path = _canonical_boot_logo(self.root)
            source = frame_path if frame_path is not None else None
            if source is None:
                source = (
                    self.root
                    / "assets"
                    / "icons"
                    / "core"
                    / "v1"
                    / "256"
                    / "robot.png"
                )
            loaded = pygame.image.load(str(source))
            if loaded.get_width() > loaded.get_height():
                width = max_height
                height = int(loaded.get_height() * width / loaded.get_width())
            else:
                height = max_height
                width = int(loaded.get_width() * height / loaded.get_height())
            image = pygame.transform.smoothscale(loaded, (width, height)).convert_alpha()
            self._icon_cache[key] = image
        screen.blit(image, image.get_rect(center=center))

    def _hero_logo(
        self,
        screen: Any,
        pygame: Any,
        width: int,
        height: int,
    ) -> None:
        """Render the boot-frame logo full-bleed, centered vertically.

        On screens taller than the artwork's natural height the logo keeps its
        aspect ratio and is centered; on short screens it fills the full height.
        There is no panel behind it.
        """
        key = ("hero-logo-full",)
        image = self._icon_cache.get(key)
        if image is None:
            frame_path = _canonical_boot_logo(self.root)
            source = frame_path if frame_path is not None else (
                self.root
                / "assets"
                / "icons"
                / "core"
                / "v1"
                / "256"
                / "robot.png"
            )
            loaded = pygame.image.load(str(source))
            if loaded.get_width() <= 0 or loaded.get_height() <= 0:
                loaded = pygame.image.load(
                    str(self.root / "assets" / "icons" / "core" / "v1" / "256" / "robot.png")
                )
            image = loaded.convert_alpha()
            self._icon_cache[key] = image
        natural = image.get_size()
        # Cap at the screen height; never upscale beyond natural size.
        scale = min(1.0, height / natural[1])
        display_height = int(natural[1] * scale)
        display_width = int(natural[0] * scale)
        rect = image.get_rect()
        rect.w, rect.h = display_width, display_height
        rect.center = (width // 2, height // 2)
        screen.blit(image, rect)

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
        self._icon(screen, pygame, "yellow_star", size, (x, y))

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

    def _center_title(
        self,
        screen: Any,
        text_value: str,
        font: Any,
        color: tuple[int, int, int],
        y: int,
    ) -> None:
        image = self._text(font, text_value, color)
        screen.blit(image, image.get_rect(midtop=(screen.get_width() // 2, y)))

    def _center_fitted_text(
        self,
        screen: Any,
        text_value: str,
        font: Any,
        color: tuple[int, int, int],
        y: int,
        max_width: int,
    ) -> None:
        """Centre one line that must first be constrained to ``max_width``.

        ``_fit_text`` returns an already-rendered surface, so it must be
        blitted rather than handed back to ``_center_text``, which renders a
        string. Keeping the two apart is what stops a status line from being
        passed a Surface as if it were text.
        """

        image = self._fit_text(font, text_value, color, max_width)
        screen.blit(image, image.get_rect(center=(screen.get_width() // 2, y)))

    def _center_text(
        self,
        screen: Any,
        text_value: str,
        font: Any,
        color: tuple[int, int, int],
        y: int,
    ) -> None:
        image = self._text(font, text_value, color)
        screen.blit(image, image.get_rect(center=(screen.get_width() // 2, y)))

    def _wrapped_text(
        self,
        screen: Any,
        text_value: str,
        font: Any,
        color: tuple[int, int, int],
        rect: Any,
    ) -> None:
        words = text_value.split()
        line = ""
        y = rect.top
        for word in words:
            candidate = f"{line} {word}".strip()
            if font.size(candidate)[0] > rect.width and line:
                screen.blit(self._text(font, line, color), (rect.left, y))
                y += font.get_linesize()
                line = word
            else:
                line = candidate
        if line:
            screen.blit(self._text(font, line, color), (rect.left, y))

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
        trimmed = text_value
        while trimmed and self._typography.surface_width(font, trimmed + "…") > max_width:
            trimmed = trimmed[:-1]
        return self._text(font, (trimmed + "…").rstrip(), color)

    def _render_signature(self, screen: Any) -> tuple[object, ...] | None:
        """Cheap fingerprint of everything the current frame would draw.

        Returning an unchanged signature means the composed frame would be
        pixel-identical, so the redraw and the display flip can be skipped.
        The installer used to repaint and re-flip the whole screen 30 times a
        second unconditionally, which is a large fixed cost on the reference
        Acer even once text rasterization and pointer probing are cached.

        The signature is derived from the live scalar state rather than from a
        hand-maintained dirty flag, so a new piece of state cannot be silently
        forgotten. Anything unhashable, unexpected or slow is simply excluded,
        and any failure at all returns ``None``, which forces a redraw. Skipping
        is therefore only ever an optimisation: it can never leave a stale
        screen behind.
        """

        def scalars(source: Any) -> tuple[object, ...]:
            parts: list[object] = []
            for name, value in sorted(vars(source).items()):
                if name.startswith("_typography") or name.startswith("_pointer_infos"):
                    continue
                if value is None or isinstance(value, (bool, int, float, str)):
                    parts.append((name, value))
                elif isinstance(value, tuple) and all(
                    item is None or isinstance(item, (bool, int, float, str))
                    for item in value
                ):
                    parts.append((name, value))
            return tuple(parts)

        try:
            return (
                tuple(screen.get_size()),
                scalars(self),
                scalars(self.state),
                scalars(self.wifi),
                len(self._pointer_infos_cache or ()),
                tuple(self.state.targets),
            )
        except Exception:
            return None

    def _release_boot_cover_once(self) -> None:
        if self._boot_released:
            return
        now = time.monotonic()
        if now < self._next_boot_handoff_attempt:
            return
        self._next_boot_handoff_attempt = now + 0.5
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
