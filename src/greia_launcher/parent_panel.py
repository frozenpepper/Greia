import os
import queue
import threading
import sys
import time
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Callable

from greia_platform.display_metrics import PhysicalUiPolicy
from greia_platform.hardware import HardwareSettingsStore
from greia_platform.hardware_session import (
    preset_to_speed,
    speed_preset_names,
    speed_to_preset,
)
from greia_platform.microphone_level import (
    SILENCE_FLOOR_DBFS,
    MicrophoneLevel,
    MicrophoneLevelClient,
)

from greia_launcher import panel_layout
from greia_launcher import panel_strings as text
from greia_launcher.parent_credential_client import (
    ChildAccount,
    ParentCredentialClient,
    ParentCredentialUnavailable,
    ParentPasswordVerifier,
    ParentRequestFailed,
    ParentSession,
)
from greia_platform.ssh_maintenance import SshMaintenanceService, SshStatus
from greia_platform.system_language import (
    SUPPORTED_SYSTEM_LANGUAGES,
    SystemLanguageError,
    SystemLanguageService,
)
from greia_platform.typography import FontRole, GreiaTypography
from greia_platform.ui_core import BoundedCache
from greia_platform.wifi import (
    DemoWifiBackend,
    IwdWifiBackend,
    WifiBackend,
    WifiSecurity,
    WifiSetupController,
    WifiSetupPhase,
)


class ParentPanelState(StrEnum):
    AUTH = "auth"
    PANEL = "panel"
    CLOSED = "closed"


class ParentPanelTab(StrEnum):
    LANGUAGE = "language"
    AUDIO = "audio"
    ACCOUNTS = "accounts"
    SECURITY = "security"
    WIFI = "wifi"
    SSH = "ssh"
    INFO = "info"
    POINTER = "pointer"


@dataclass(frozen=True, slots=True)
class PanelHitTarget:
    action: str
    value: object
    rect: Any


#: Shown when the typed password was rejected. The service answered; the
#: candidate was wrong.
_PASSWORD_REJECTED = "Incorrect password"

#: Shown when no verdict could be obtained at all. Distinct from a rejection:
#: the parent may have typed the right thing.
_PASSWORD_CHECK_FAILED = "Cannot check the password right now"

class ParentSettingsOverlay:
    """On-device Parent Settings Panel for physical Greia devices.

    Accessible from the user selection screen via a protected hidden key combination.
    Provides immediate on-device access to the device language, audio & mic gain, Wi-Fi
    configuration, SSH maintenance, and remote pairing diagnostics without
    exposing a Linux shell.
    """

    def __init__(
        self,
        credential_verifier: ParentPasswordVerifier,
        *,
        wifi_backend: WifiBackend | None = None,
        ssh_service: SshMaintenanceService | None = None,
        language_service: SystemLanguageService | None = None,
        hardware_store: HardwareSettingsStore | None = None,
        pointer_controller: Any | None = None,
    ) -> None:
        # The Parent password is owned by the Parent service identity. The panel
        # never reads the digest: it asks the service that owns it. Seeding a
        # local 0600 store here could only fail as the child identity, which is
        # what made every password look wrong.
        self.credential_verifier = credential_verifier
        self._password_problem: str | None = None

        if wifi_backend is None:
            backend = (
                IwdWifiBackend()
                if Path("/var/lib/iwd").exists() or Path("/etc/greia-os").exists()
                else DemoWifiBackend()
            )
        else:
            backend = wifi_backend

        self.wifi_controller = WifiSetupController(backend)
        self.ssh_service = ssh_service or SshMaintenanceService()
        self.language_service = language_service or SystemLanguageService.from_environment()

        if hardware_store is None:
            defaults_path = (
                Path(os.environ.get("GREIA_OS_ROOT", "/opt/greia-os"))
                / "runtime"
                / "hardware-settings.toml"
            )
            if not defaults_path.exists():
                repo_root = Path(__file__).resolve().parents[2]
                defaults_path = repo_root / "runtime" / "hardware-settings.toml"
            system_settings_dir = Path(
                os.environ.get("GREIA_SYSTEM_SETTINGS_DIR", "/var/lib/greia-system-settings")
            )
            self.hardware_store: HardwareSettingsStore | None = (
                HardwareSettingsStore.load(defaults_path, system_settings_dir)
                if defaults_path.exists()
                else None
            )
        else:
            self.hardware_store = hardware_store

        self.state = ParentPanelState.CLOSED
        self.active_tab = ParentPanelTab.LANGUAGE
        self.password_text = ""
        self.password_error_until = 0.0
        self._password_problem = None
        self._session = None
        self._text_field = None
        self._accounts = []
        self._accounts_loaded = False
        self._accounts_mode = "list"
        self._accounts_message = None
        self._accounts_message_is_error = False
        self._account_name = ""
        self._account_age = ""
        self._account_avatar_index = 0
        self._pending_remove = None
        self._renaming = None
        self._security_current = ""
        self._security_new = ""
        self._security_confirm = ""
        self._security_message = None
        self._security_message_is_error = False
        self._targets: list[PanelHitTarget] = []
        self._ssh_cached_status: SshStatus | None = None
        self._last_ssh_poll = 0.0
        # SSH status comes from systemctl subprocesses; polling it on the UI
        # thread froze the panel (the Info tab used to call it every frame).
        # Refreshes therefore run on a short-lived worker and are consumed by
        # drain(), mirroring the Wi-Fi controller pattern.
        self._ssh_results: "queue.Queue[SshStatus]" = queue.Queue()
        self._ssh_refresh_in_flight = False
        self._language_index = 0
        self._language_message = ""
        self._audio_message = ""
        self._backdrop_surface: Any = None
        self._cached_mic_gain: float | None = None
        self._content_origin: tuple[int, int] = (0, 0)
        self._meter_band_rect: Any = None
        self._panel_composite_meter: Any = None
        self._typography_for_overlay: Any = None
        self._mic_gain_read_at = 0.0
        # Software rounded rects (pygame.draw.rect with border_radius) cost
        # several milliseconds EACH on Atom-class CPUs; a tab rendering ~25 of
        # them per frame ran at 10-15 fps. Chips render each fill+outline
        # combination once into an opaque surface whose corners carry the
        # known backdrop color, so every later frame is one fast opaque blit.
        self._chip_cache: BoundedCache[tuple[Any, ...], Any] = BoundedCache(128)
        # The AUTH card and the main panel sit on the launcher's dimmed
        # underlay whose pixels are not a single solid color, so they cannot be
        # chips with a baked backdrop. They are instead composed once, on top
        # of a copy of that underlay, into `_panel_base` (keyed by the underlay
        # identity, state and size) and presented with one opaque blit.
        self._panel_base: Any = None
        self._panel_base_key: Any = None
        # Whole-panel composite cache. The panel is redrawn every frame by the
        # Shell, and profiling on the reference Acer showed 45 large alpha blits
        # per frame at ~150 ms, because the display is software (hwaccel=0) and
        # each composite of a translucent surface is expensive. A static panel
        # therefore composes once and is then presented with a single blit.
        self._panel_composite: Any = None
        self._panel_composite_key: Any = None
        self._panel_composite_targets: list[PanelHitTarget] = []
        # Set by the Shell when the tab has something that moves every frame, so
        # an animated tab is never served from the cache.
        self._content_animating = False
        # Live input level. The gain meter only reflected the setting; nothing
        # showed what the microphone was hearing, so a parent could not tell a
        # working mic from a muted one. Measured on the reference Acer's ALC268
        # input: RMS -9.0 dBFS with the peak pinned at 0.0 dBFS, which is
        # clipping, and it was invisible.
        self._mic_level_reader = MicrophoneLevelClient()
        self._mic_peak_hold_dbfs = SILENCE_FLOOR_DBFS
        self._mic_peak_hold_until = 0.0
        self._text_surface_cache: dict[tuple[Any, ...], Any] = {}
        self._sync_language_selection()
        # Pointer tab state. The settings store parses a JSON file on read
        # and the preview seam may run device subprocesses, so both are
        # served from small time-bounded caches (same style as mic gain /
        # SSH status) and never re-read per frame.
        self._pointer_controller = pointer_controller
        self._cached_pointer_settings: Any = None
        self._pointer_settings_read_at = 0.0
        self._pointer_probe_cache: tuple[Any, ...] = ()
        self._pointer_probe_at = 0.0
        self._pointer_probe_known = False
        self._pointer_message = ""
        self._pointer_focus = 0
        self._audio_processing_enabled = True
        self._audio_advanced_enabled = False
        self._audio_advanced_available = False
        self._audio_settings_loaded = False
        self._pointer_test_flash: int | None = None
        self._pointer_test_flash_at = 0.0

    def auth_card_rect(self, size: tuple[int, int]) -> Any:
        """Return the centered Parent-password card rectangle."""

        import pygame

        width, height = size
        card_w = min(480, width - 40)
        card_h = min(320, height - 40)
        card = pygame.Rect(0, 0, card_w, card_h)
        card.center = (width // 2, height // 2)
        return card

    def _rounded_card(
        self,
        size: tuple[int, int],
        radius: int,
        backdrop: tuple[int, int, int],
        fill: tuple[int, int, int],
        outline: tuple[int, int, int] | None = None,
        width: int = 0,
        pygame: Any = None,
    ) -> Any:
        """Return a cached opaque rounded chip matching `size`.

        The chip bakes `backdrop` into its corners so blitting it over the
        surface it was cut for is pixel-identical to drawing the rounded rect
        in place, without per-frame software corner geometry.
        """

        key = (size, radius, backdrop, fill, outline, width)
        cached = self._chip_cache.get(key)
        if cached is not None:
            return cached
        chip = pygame.Surface(size).convert()
        chip.fill(backdrop)
        rect = chip.get_rect()
        pygame.draw.rect(chip, fill, rect, border_radius=radius)
        if outline is not None and width > 0:
            pygame.draw.rect(chip, outline, rect, width=width, border_radius=radius)
        self._chip_cache[key] = chip
        return chip

    def _blit_rounded_card(
        self,
        screen: Any,
        rect: Any,
        backdrop: tuple[int, int, int],
        fill: tuple[int, int, int],
        pygame: Any,
        outline: tuple[int, int, int] | None = None,
        width: int = 0,
        radius: int | None = None,
    ) -> None:
        if radius is None:
            radius = 12
        chip = self._rounded_card(
            (rect.width, rect.height),
            radius,
            backdrop,
            fill,
            outline,
            width,
            pygame,
        )
        screen.blit(chip, rect.topleft)

    def open(self) -> None:
        self.state = ParentPanelState.AUTH
        self.active_tab = ParentPanelTab.LANGUAGE
        self.password_text = ""
        self.password_error_until = 0.0
        self._password_problem = None
        self._language_message = ""
        self._pointer_message = ""
        self._pointer_focus = 0
        self._pointer_test_flash = None
        self._sync_language_selection()
        self._targets.clear()
        self.wifi_controller.begin()
        self.request_ssh_status_refresh(force=True)

    def close(self) -> None:
        self.state = ParentPanelState.CLOSED
        self.password_text = ""
        self.wifi_controller.skip()

    @property
    def is_open(self) -> bool:
        return self.state != ParentPanelState.CLOSED

    def drain(self) -> bool:
        wifi_changed = self.wifi_controller.drain()
        ssh_changed = False
        while True:
            try:
                status = self._ssh_results.get_nowait()
            except queue.Empty:
                break
            if status != self._ssh_cached_status:
                ssh_changed = True
            self._ssh_cached_status = status
        if self.state == ParentPanelState.PANEL and self.active_tab in {
            ParentPanelTab.SSH,
            ParentPanelTab.INFO,
        }:
            self.request_ssh_status_refresh()
        return wifi_changed or ssh_changed

    def request_ssh_status_refresh(self, *, force: bool = False) -> None:
        """Start one non-blocking SSH status refresh, throttled to ~2 seconds.

        The status requires systemctl subprocesses; running those on the UI
        thread made the SSH/Info tabs visibly freeze on Atom-class devices.
        """

        if self._ssh_refresh_in_flight:
            return
        now = time.monotonic()
        if not force and now - self._last_ssh_poll < 2.0:
            return
        self._last_ssh_poll = now
        self._ssh_refresh_in_flight = True
        threading.Thread(
            target=self._run_ssh_status_refresh,
            name="greia-ssh-status",
            daemon=True,
        ).start()

    def _run_ssh_status_refresh(self) -> None:
        try:
            status = self.ssh_service.get_status()
        except Exception:
            status = None
        finally:
            self._ssh_refresh_in_flight = False
            if status is not None:
                self._ssh_results.put(status)

    @property
    def ssh_status(self) -> SshStatus | None:
        """Last known cached SSH status without any blocking work."""

        return self._ssh_cached_status

    def handle_text_input(self, value: str) -> None:
        if self.state == ParentPanelState.AUTH:
            if time.monotonic() < self.password_error_until or not value:
                return
            accepted = "".join(
                ch for ch in value if ch not in "\r\n\x00" and ch.isprintable()
            )
            if len(self.password_text) < 64:
                self.password_text += accepted[: 64 - len(self.password_text)]
        elif (
            self.state == ParentPanelState.PANEL
            and self._text_field is not None
            and self.active_tab
            in {ParentPanelTab.ACCOUNTS, ParentPanelTab.SECURITY}
        ):
            accepted = "".join(ch for ch in value if ch.isprintable())
            self._set_field_value(self._text_field, self._field_value(self._text_field) + accepted)
        elif self.state == ParentPanelState.PANEL and self.active_tab == ParentPanelTab.WIFI:
            self.wifi_controller.append_password(value)

    def handle_key(self, key: int, pygame: Any) -> bool:
        """Handle key input. Returns True to stay in overlay, False to close."""
        if self.state == ParentPanelState.AUTH:
            if key == pygame.K_ESCAPE:
                self.close()
                return False
            if key == pygame.K_BACKSPACE:
                self.password_text = self.password_text[:-1]
                return True
            if key in {pygame.K_RETURN, pygame.K_KP_ENTER}:
                self._attempt_auth(pygame)
                return True
            return True

        if self.state == ParentPanelState.PANEL:
            if key == pygame.K_ESCAPE:
                self.close()
                return False
            if key == pygame.K_TAB:
                tabs = [
                    ParentPanelTab.LANGUAGE,
                    ParentPanelTab.AUDIO,
                    ParentPanelTab.WIFI,
                    ParentPanelTab.SSH,
                    ParentPanelTab.INFO,
                    ParentPanelTab.POINTER,
                ]
                idx = (tabs.index(self.active_tab) + 1) % len(tabs)
                self.active_tab = tabs[idx]
                return True

            if self.active_tab == ParentPanelTab.LANGUAGE:
                if key in {pygame.K_RIGHT, pygame.K_DOWN}:
                    self._language_index = (
                        self._language_index + 1
                    ) % len(SUPPORTED_SYSTEM_LANGUAGES)
                elif key in {pygame.K_LEFT, pygame.K_UP}:
                    self._language_index = (
                        self._language_index - 1
                    ) % len(SUPPORTED_SYSTEM_LANGUAGES)
                elif key in {pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE}:
                    self._apply_language(self._language_index)
                return True

            if self.active_tab == ParentPanelTab.AUDIO:
                if key in {pygame.K_LEFT, pygame.K_DOWN}:
                    self._adjust_mic_gain(-0.25)
                elif key in {pygame.K_RIGHT, pygame.K_UP}:
                    self._adjust_mic_gain(0.25)
                return True

            if self.active_tab == ParentPanelTab.POINTER:
                self._pointer_handle_key(key, pygame)
                return True

            if self.active_tab == ParentPanelTab.WIFI:
                if key == pygame.K_UP:
                    self.wifi_controller.move_selection(-1)
                elif key == pygame.K_DOWN:
                    self.wifi_controller.move_selection(1)
                elif key == pygame.K_BACKSPACE:
                    self.wifi_controller.backspace_password()
                elif key in {pygame.K_RETURN, pygame.K_KP_ENTER}:
                    self.wifi_controller.connect()

            elif self.active_tab == ParentPanelTab.SSH:
                if key in {pygame.K_RETURN, pygame.K_SPACE}:
                    self._toggle_ssh()

            return True

        return False

    def handle_click(self, pos: tuple[int, int], pygame: Any = None) -> bool:
        """Handle click input. Returns True if handled, False if overlay closed."""
        for target in reversed(self._targets):
            if not target.rect.collidepoint(pos):
                continue

            try:
                if target.action in {"cancel_auth", "close_panel"}:
                    self.close()
                    return False
                elif target.action == "confirm_auth":
                    self._attempt_auth(pygame)
                    return True
                elif target.action == "switch_tab":
                    if isinstance(target.value, ParentPanelTab):
                        self.active_tab = target.value
                    elif isinstance(target.value, str):
                        val = str(target.value)
                        for tab in ParentPanelTab:
                            if tab.value == val or tab.name.lower() == val.lower() or str(tab) == val:
                                self.active_tab = tab
                                break
                    return True
                elif target.action == "language_select":
                    self._language_index = int(target.value)
                    self._apply_language(self._language_index)
                    return True
                elif target.action == "mic_gain_set":
                    self._set_mic_gain(float(target.value))
                    return True
                elif target.action == "mic_gain_adjust":
                    self._adjust_mic_gain(float(target.value))
                    return True
                elif target.action == "mic_processing_toggle":
                    self._toggle_microphone_processing(str(target.value))
                    return True
                elif target.action == "pointer_touchpad_preset":
                    self._set_pointer_preset("touchpad", str(target.value))
                    return True
                elif target.action == "pointer_mouse_preset":
                    self._set_pointer_preset("mouse", str(target.value))
                    return True
                elif target.action == "pointer_toggle":
                    self._toggle_pointer_setting(str(target.value))
                    return True
                elif target.action == "pointer_reset":
                    self._reset_pointer_defaults()
                    return True
                elif target.action == "pointer_test":
                    self._flash_pointer_test_target(int(target.value))
                    return True
                elif target.action == "focus_field":
                    self._text_field = str(target.value)
                    return True
                elif target.action == "account_add":
                    self._accounts_mode = "add"
                    self._text_field = "account_name"
                    self._set_accounts_message(None)
                    return True
                elif target.action == "account_cancel":
                    self._accounts_mode = "list"
                    self._text_field = None
                    self._renaming = None
                    self._set_accounts_message(None)
                    return True
                elif target.action == "account_create":
                    self._create_account()
                    return True
                elif target.action == "account_save":
                    self._save_rename()
                    return True
                elif target.action == "account_rename":
                    found = next(
                        (a for a in self._accounts if a.profile_id == target.value),
                        None,
                    )
                    if found is not None:
                        self._start_rename(found)
                    return True
                elif target.action == "account_avatar":
                    self._cycle_avatar(int(target.value))
                    return True
                elif target.action == "account_remove":
                    self._pending_remove = next(
                        (a for a in self._accounts if a.profile_id == target.value),
                        None,
                    )
                    if self._pending_remove is not None:
                        self._accounts_mode = "confirm"
                        self._text_field = None
                    return True
                elif target.action == "account_remove_cancel":
                    self._pending_remove = None
                    self._accounts_mode = "list"
                    return True
                elif target.action == "account_remove_confirm":
                    if self._pending_remove is not None:
                        self._remove_account(self._pending_remove)
                    return True
                elif target.action == "security_change":
                    self._change_password()
                    return True
                elif target.action == "wifi_refresh":
                    self.wifi_controller.refresh()
                    return True
                elif target.action == "wifi_select":
                    self.wifi_controller.select(int(target.value))
                    return True
                elif target.action == "wifi_connect":
                    self.wifi_controller.connect()
                    return True
                elif target.action == "ssh_toggle":
                    self._toggle_ssh()
                    return True
            except Exception:
                return True

        return True

    def _toggle_ssh(self) -> None:
        """Apply one user-initiated SSH toggle and cache its returned status."""

        try:
            self._ssh_cached_status = self.ssh_service.toggle()
        except Exception:
            self.request_ssh_status_refresh(force=True)

    def _current_mic_gain(self) -> float:
        # The hardware store parses a TOML file on read; never do that per
        # frame. Serve the cached value and refresh it at most once a second.
        now = time.monotonic()
        if self._cached_mic_gain is None or now - self._mic_gain_read_at > 1.0:
            value = 2.0
            if self.hardware_store is not None:
                try:
                    value = float(self.hardware_store.read().mic_gain)
                except Exception:
                    pass
            self._cached_mic_gain = value
            self._mic_gain_read_at = now
        return self._cached_mic_gain

    def _refresh_audio_processing(self) -> None:
        """Read microphone processing policy through the Parent service.

        The settings directory is greiapel-owned and this panel runs as greiakid,
        which has read but not write access, so the policy is read and written
        through the service. Reading it directly is what left the noise cancelling
        controls unwired for so long.
        """

        client, session = self._parent_client(), self._session
        if client is None or session is None:
            return
        try:
            payload = client.get_audio_settings(session)
        except Exception:
            self._audio_settings_loaded = False
            return
        if not isinstance(payload, dict):
            return
        self._audio_processing_enabled = bool(
            payload.get("microphone_processing_enabled", True)
        )
        self._audio_advanced_enabled = bool(payload.get("advanced_noise_reduction", False))
        advanced = payload.get("advanced_available")
        self._audio_advanced_available = advanced is True
        self._audio_settings_loaded = True

    def _set_microphone_processing(self, enabled: bool, advanced: bool) -> None:
        """Apply microphone processing policy, refusing an unavailable backend."""

        if advanced and not self._audio_advanced_available:
            self._audio_message = (
                "Advanced noise reduction is not available on this Greia."
            )
            return
        client, session = self._parent_client(), self._session
        if client is None or session is None:
            self._audio_message = text.STATUS_OFFLINE
            return
        try:
            client.set_microphone_processing(
                session, enabled=enabled, advanced=advanced
            )
        except Exception as exc:
            self._audio_message = f"Could not change noise cancelling: {exc}"
            return
        self._audio_processing_enabled = enabled
        self._audio_advanced_enabled = advanced
        mode = (
            "off"
            if not enabled
            else ("advanced" if advanced else "lightweight")
        )
        self._audio_message = f"Noise cancelling set to {mode}."

    def _toggle_microphone_processing(self, field: str) -> None:
        """Flip one noise cancelling control, keeping the pair coherent.

        Turning processing off also turns advanced reduction off, so the stored
        policy never describes noise cancelling that is not running.
        """

        if field == "mic_processing":
            enabled = not self._audio_processing_enabled
            self._set_microphone_processing(
                enabled, self._audio_advanced_enabled if enabled else False
            )
        elif field == "mic_advanced":
            self._set_microphone_processing(
                self._audio_processing_enabled,
                not self._audio_advanced_enabled,
            )

    def _set_mic_gain(self, value: float) -> None:
        val = max(0.5, min(4.0, round(value, 2)))
        # Through the service, like every other setting. A direct store write
        # raised PermissionError here too - the panel is greiakid and the
        # settings directory is greiapel-owned - so the gain steppers and
        # presets looked live and applied nothing.
        if self._apply_hardware_change(
            {"mic_gain": val},
            f"Microphone gain set to {int(val * 100)}% ({val:.2f}x boost).",
        ):
            self._cached_mic_gain = float(val)
            self._mic_gain_read_at = time.monotonic()
        else:
            self._audio_message = self._pointer_message

    def _adjust_mic_gain(self, delta: float) -> None:
        current = self._current_mic_gain()
        self._set_mic_gain(current + delta)

    # --- Pointer tab: semantic settings through HardwareSettingsStore -------
    # Same preset helper and same semantics as the installer (T03
    # SPEED_PRESETS via speed_preset_names/preset_to_speed/speed_to_preset);
    # no forked float mapping lives here. Capability gating mirrors the
    # installer: touchpad-only controls are shown dimmed and inactive when
    # the preview seam reports no touchpad.

    _POINTER_TOGGLE_FIELDS = ("touchpad_tap", "natural_scrolling", "disable_while_typing")
    _POINTER_TEST_TARGETS = 4

    def _pointer_settings(self) -> Any:
        """Return cached pointer settings (bounded reads, 1 s throttle)."""
        now = time.monotonic()
        if (
            self._cached_pointer_settings is None
            or now - self._pointer_settings_read_at > 1.0
        ):
            value = None
            if self.hardware_store is not None:
                try:
                    value = self.hardware_store.read()
                except Exception:
                    value = None
            if value is None and self.hardware_store is not None:
                try:
                    value = self.hardware_store.default_settings()
                except Exception:
                    value = None
            self._cached_pointer_settings = value
            self._pointer_settings_read_at = now
        return self._cached_pointer_settings

    def _pointer_probe(self) -> tuple[Any, ...]:
        """Return cached pointer capability facts (2 s throttle, soft-fail)."""
        now = time.monotonic()
        if self._pointer_probe_known and now - self._pointer_probe_at < 2.0:
            return self._pointer_probe_cache
        infos: tuple[Any, ...] = ()
        known = False
        controller = self._pointer_controller
        if controller is not None:
            probe = getattr(controller, "probe_pointers", None)
            if callable(probe):
                try:
                    result = probe()
                except Exception:
                    result = ()
                if isinstance(result, (tuple, list)):
                    infos = tuple(result)
                    known = True
        self._pointer_probe_cache = infos
        self._pointer_probe_at = now
        self._pointer_probe_known = known
        return infos

    @staticmethod
    def _pointer_kind_token(info: Any) -> str:
        kind = getattr(info, "kind", "")
        value = getattr(kind, "value", kind)
        try:
            return str(value).strip().lower()
        except Exception:
            return ""

    def _pointer_has_touchpad(self) -> bool:
        self._pointer_probe()
        if not self._pointer_probe_known:
            return True
        return any(
            self._pointer_kind_token(info) == "touchpad"
            for info in self._pointer_probe_cache
        )

    def _pointer_has_relative(self) -> bool:
        self._pointer_probe()
        if not self._pointer_probe_known:
            return True
        return any(
            self._pointer_kind_token(info) in ("mouse", "other_relative")
            for info in self._pointer_probe_cache
        )

    @staticmethod
    def _pointer_min_touch_px() -> int:
        """Shared physical floor for essential pointer controls (T01)."""
        try:
            return int(
                PhysicalUiPolicy.minimum_pixels(
                    9, fallback_px=48, metrics=None
                )
            )
        except Exception:
            return 48

    def _pointer_speed_value(self, which: str) -> float:
        settings = self._pointer_settings()
        try:
            raw = getattr(settings, "touchpad_speed" if which == "touchpad" else "mouse_speed", 0.0)
            value = float(raw)
        except Exception:
            return 0.0
        if value != value or value in (float("inf"), float("-inf")):
            return 0.0
        return max(-1.0, min(1.0, value))

    def _pointer_current_preset(self, which: str) -> str:
        try:
            return speed_to_preset(self._pointer_speed_value(which))
        except Exception:
            names = speed_preset_names()
            return names[len(names) // 2]

    def _set_pointer_preset(self, which: str, name: str) -> None:
        names = speed_preset_names()
        if name not in names:
            return
        if which == "touchpad" and not self._pointer_has_touchpad():
            self._pointer_message = "No touchpad detected — touchpad speed is not active."
            return
        if which == "mouse" and not self._pointer_has_relative():
            self._pointer_message = "No mouse detected — mouse speed is not active."
            return
        if self.hardware_store is None:
            return
        try:
            speed = float(preset_to_speed(name))
        except (KeyError, TypeError, ValueError):
            return
        label = "Touchpad" if which == "touchpad" else "Mouse"
        field = "touchpad_speed" if which == "touchpad" else "mouse_speed"
        self._apply_hardware_change({field: speed}, f"{label} speed: {name}.")
        if self.hardware_store is None:
            return
        self._pointer_message = f"{label} feel set to {name}."

    def _step_pointer_preset(self, which: str, delta: int) -> None:
        names = list(speed_preset_names())
        if not names:
            return
        try:
            current = self._pointer_current_preset(which)
            index = names.index(current)
        except ValueError:
            index = len(names) // 2
        index = max(0, min(len(names) - 1, index + (1 if delta > 0 else -1)))
        self._set_pointer_preset(which, names[index])

    def _apply_hardware_change(
        self, changes: dict[str, object], success: str
    ) -> bool:
        """Apply one settings change through the Parent service.

        The panel runs as greiakid and the settings directory is greiapel-owned
        with mode 2750, so a direct store write raised PermissionError. Every
        control caught that and showed nothing, which is why the pointer switches
        looked interactive and changed nothing. The service owns the write.
        """

        client, session = self._parent_client(), self._session
        if client is None or session is None:
            self._pointer_message = text.STATUS_OFFLINE
            return False
        try:
            updated = client.update_hardware_settings(session, changes)
        except Exception as exc:
            self._pointer_message = f"Could not apply: {exc}"
            return False
        self._pointer_settings = updated
        self._cached_pointer_settings = updated
        self._pointer_settings_read_at = time.monotonic()
        self._pointer_message = success
        return True

    def _toggle_pointer_setting(self, field: str) -> None:
        if field not in self._POINTER_TOGGLE_FIELDS:
            return
        if field in ("touchpad_tap", "disable_while_typing") and not self._pointer_has_touchpad():
            self._pointer_message = "No touchpad detected — this switch is not active."
            return
        if self.hardware_store is None:
            return
        settings = self._pointer_settings()
        try:
            current = bool(getattr(settings, field, False))
        except Exception:
            current = False
        self._apply_hardware_change(
            {field: (not current)},
            f"{'On' if not current else 'Off'} {field.replace('_', ' ')}.",
        )
        self._pointer_message = f"{'On' if not current else 'Off'}: {field.replace('_', ' ')}."

    def _reset_pointer_defaults(self) -> None:
        client, session = self._parent_client(), self._session
        if client is not None and session is not None:
            try:
                updated = client.reset_hardware_settings(session)
            except Exception as exc:
                self._pointer_message = f"Could not reset pointer settings: {exc}"
                return
            self._pointer_settings = updated
            self._cached_pointer_settings = updated
            self._pointer_settings_read_at = time.monotonic()
            self._pointer_message = "Pointer settings reset to defaults."
            return
        if self.hardware_store is None:
            return
        try:
            updated = self.hardware_store.reset()
        except Exception as exc:
            self._pointer_message = f"Could not reset pointer settings: {exc}"
            return
        self._cached_pointer_settings = updated
        self._pointer_settings_read_at = time.monotonic()
        self._pointer_focus = 0
        self._pointer_message = "Pointer settings reset to defaults."

    def _flash_pointer_test_target(self, index: int) -> None:
        try:
            index = int(index)
        except (TypeError, ValueError):
            return
        if 0 <= index < self._POINTER_TEST_TARGETS:
            self._pointer_test_flash = index
            self._pointer_test_flash_at = time.monotonic()
            self._pointer_message = "Tapped — try moving across the test area."

    def _pointer_focus_items(self) -> list[str]:
        items = [
            "touchpad_speed",
            "mouse_speed",
            "touchpad_tap",
            "natural_scrolling",
            "disable_while_typing",
            "reset",
        ]
        items.extend(f"test{i}" for i in range(self._POINTER_TEST_TARGETS))
        return items

    def _pointer_handle_key(self, key: int, pygame: Any) -> None:
        items = self._pointer_focus_items()
        if not items:
            return
        try:
            self._pointer_focus = int(self._pointer_focus)
        except (TypeError, ValueError):
            self._pointer_focus = 0
        self._pointer_focus = max(0, min(len(items) - 1, self._pointer_focus))
        focused = items[self._pointer_focus]
        if key in {pygame.K_DOWN, pygame.K_TAB}:
            self._pointer_focus = (self._pointer_focus + 1) % len(items)
            return
        if key == pygame.K_UP:
            self._pointer_focus = (self._pointer_focus - 1) % len(items)
            return
        if key == pygame.K_LEFT:
            if focused == "touchpad_speed":
                self._step_pointer_preset("touchpad", -1)
            elif focused == "mouse_speed":
                self._step_pointer_preset("mouse", -1)
            elif focused in self._POINTER_TOGGLE_FIELDS:
                self._toggle_pointer_setting(focused)
            return
        if key == pygame.K_RIGHT:
            if focused == "touchpad_speed":
                self._step_pointer_preset("touchpad", 1)
            elif focused == "mouse_speed":
                self._step_pointer_preset("mouse", 1)
            elif focused in self._POINTER_TOGGLE_FIELDS:
                self._toggle_pointer_setting(focused)
            return
        if key in {pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE}:
            if focused == "touchpad_speed":
                self._step_pointer_preset("touchpad", 1)
            elif focused == "mouse_speed":
                self._step_pointer_preset("mouse", 1)
            elif focused in self._POINTER_TOGGLE_FIELDS:
                self._toggle_pointer_setting(focused)
            elif focused == "reset":
                self._reset_pointer_defaults()
            elif focused.startswith("test"):
                try:
                    self._flash_pointer_test_target(int(focused[4:]))
                except ValueError:
                    pass
            return

    def _attempt_auth(self, pygame: Any) -> None:
        if time.monotonic() < self.password_error_until:
            return
        session_holder = getattr(self.credential_verifier, "authenticate", None)
        try:
            if callable(session_holder):
                # Prefer a real session: the account and password operations
                # below need the device token, and re-verifying separately would
                # spend a second rate-limited attempt.
                self._session = session_holder(self.password_text)
                verified = True
            else:
                verified = bool(self.credential_verifier.verify(self.password_text))
        except ParentCredentialUnavailable:
            # The check could not be performed. Say so. Reporting this as an
            # incorrect password is what cost a full diagnosis cycle: an
            # unreadable credential looked exactly like a typing mistake.
            self._password_problem = _PASSWORD_CHECK_FAILED
            self.password_text = ""
            self.password_error_until = time.monotonic() + 1.2
            return
        except Exception:
            self._password_problem = _PASSWORD_CHECK_FAILED
            self.password_text = ""
            self.password_error_until = time.monotonic() + 1.2
            return
        if verified:
            self._password_problem = None
            self._session = self._session  # established above, or None for a bare verifier
            self.state = ParentPanelState.PANEL
            self.password_text = ""
            self._sync_language_selection()
            self.wifi_controller.begin()
        else:
            self._password_problem = None
            self.password_text = ""
            self.password_error_until = time.monotonic() + 1.2

    def _sync_language_selection(self) -> None:
        try:
            current = self.language_service.read().locale
        except Exception:
            current = SUPPORTED_SYSTEM_LANGUAGES[0].locale
        self._language_index = next(
            (
                index
                for index, language in enumerate(SUPPORTED_SYSTEM_LANGUAGES)
                if language.locale == current
            ),
            0,
        )

    def _apply_language(self, index: int) -> None:
        try:
            language = SUPPORTED_SYSTEM_LANGUAGES[index]
            saved = self.language_service.set(language.locale)
            self._language_index = next(
                (
                    item_index
                    for item_index, item in enumerate(SUPPORTED_SYSTEM_LANGUAGES)
                    if item.locale == saved.locale
                ),
                index,
            )
            self._language_message = f"Language changed to {saved.name}."
        except (SystemLanguageError, OSError, IndexError) as exc:
            self._language_message = f"Could not change language: {exc}"

    def _get_text(self, text: str, role: FontRole, size: int, color: tuple[int, int, int], typography: GreiaTypography) -> Any:
        """Render one label through the shared Greia typography service.

        ``GreiaTypography.render`` owns Nunito Sans roles AND the Noto Color
        Emoji fallback (flags, 🎙️, 🔒, ⭐ …) with bounded surface caching.
        Rendering through ``typography.font(...).render(...)`` instead produced
        tofu boxes for every emoji on device and skipped that shared cache.
        """

        key = (text, role, size, color)
        cached = self._text_surface_cache.get(key)
        if cached is None:
            cached = typography.render(text, role, size, color)
            if len(self._text_surface_cache) > 128:
                self._text_surface_cache.clear()
            self._text_surface_cache[key] = cached
        return cached

    def _masked_password(self, max_visible: int) -> str:
        """Mask the typed password to at most `max_visible` dots."""

        if not self.password_text:
            return ""
        visible = max(1, int(max_visible))
        if len(self.password_text) <= visible:
            return "•" * len(self.password_text)
        return "•" * visible

    def dim_surface(self, size: tuple[int, int], pygame: Any) -> Any:
        """Return the cached translucent dim layer for `size`."""

        width, height = size
        if (
            self._backdrop_surface is None
            or self._backdrop_surface.get_size() != (width, height)
        ):
            self._backdrop_surface = pygame.Surface((width, height), pygame.SRCALPHA)
            self._backdrop_surface.fill((30, 24, 20, 210))
        return self._backdrop_surface

    def draw(
        self,
        screen: Any,
        theme: Any,
        typography: GreiaTypography,
        pygame: Any,
        load_icon_fn: Callable[[str, int, Any], Any],
        *,
        draw_backdrop: bool = True,
        base_surface: Any = None,
        base_key: Any = None,
    ) -> None:
        """Draw the overlay content onto `screen`.

        When the calling launcher composites the dim itself (the fast opaque
        path) it passes ``draw_backdrop=False`` plus the cached dimmed
        underlay as ``base_surface``/``base_key``; this overlay then composes
        its large rounded chrome (AUTH card or main panel + header) onto one
        copy of that base exactly once per state change and presents it with
        a single fast blit. Blending a full-screen translucent layer here on
        every redraw otherwise dominates frame time on low-resource devices.
        """

        width, height = screen.get_size()
        composite_key = self._composite_key(base_key, (width, height))
        # The capture device is exclusive, so hold it only while the tab that shows
        # the meter is on screen. This call is the only thing that stops it: without
        # it the panel kept the microphone for the rest of the session and starved
        # every later open, including its own.
        self._ensure_mic_level_running(self.active_tab is ParentPanelTab.AUDIO)
        self._typography_for_overlay = typography
        cached = self._serve_composite(screen, composite_key)
        if cached:
            return

        self._targets.clear()

        chrome_in_base = base_surface is not None and base_key is not None
        if chrome_in_base:
            self._ensure_panel_base(
                screen, theme, typography, pygame, load_icon_fn, base_surface, base_key
            )
            screen.blit(self._panel_base, (0, 0))
        elif draw_backdrop:
            screen.blit(self.dim_surface((width, height), pygame), (0, 0))

        if self.state == ParentPanelState.AUTH:
            self._draw_auth_dialog(
                screen, theme, typography, pygame, load_icon_fn, chrome_in_base
            )
        elif self.state == ParentPanelState.PANEL:
            self._draw_panel(
                screen, theme, typography, pygame, load_icon_fn, chrome_in_base
            )
        self._store_composite(screen, composite_key)

    # --- frame caching -------------------------------------------------
    #
    # Everything the panel draws is derived from the values below, so when none of
    # them has changed the previous frame is still correct. Anything that moves
    # on its own (a spinner, a level meter, a wifi scan) sets
    # ``_content_animating`` and opts out, so caching can never freeze motion.

    # Every instance attribute the drawing code reads. This list is audited by
    # ``tests/test_panel_frame_cache.py``, which scans the draw methods for
    # ``self._x`` reads and fails if one is missing here. An audit rather than a
    # comment matters here: an omission does not slow the panel down, it silently
    # stops that state updating on screen, which is the worse failure.
    _COMPOSITE_STATE_FIELDS = (
        "state",
        "active_tab",
        "password_text",
        "password_error_until",
        "_password_problem",
        "_language_index",
        "_language_message",
        "_audio_message",
        "_cached_mic_gain",
        "_accounts",
        "_accounts_loaded",
        "_accounts_mode",
        "_accounts_message",
        "_accounts_message_is_error",
        "_account_name",
        "_account_age",
        "_account_avatar_index",
        "_pending_remove",
        "_renaming",
        "_security_current",
        "_security_new",
        "_security_confirm",
        "_security_message",
        "_security_message_is_error",
        "_text_field",
        "_pointer_settings",
        "_pointer_current_preset",
        "_pointer_focus",
        "_pointer_focus_items",
        "_pointer_has_relative",
        "_pointer_has_touchpad",
        "_pointer_message",
        "_pointer_min_touch_px",
        "_audio_processing_enabled",
        "_audio_advanced_enabled",
        "_audio_advanced_available",
        "_pointer_test_flash",
        "_pointer_test_flash_at",
        "_ssh_cached_status",
        "_ssh_enabled",
        "_info_lines",
        "_content_animating",
    )

    def _composite_key(self, base_key: Any, size: tuple[int, int]) -> Any:
        """A hashable summary of everything the current frame depends on."""

        parts: list[Any] = [base_key, size, self._content_animating]
        for name in self._COMPOSITE_STATE_FIELDS:
            value = getattr(self, name, None)
            if isinstance(value, (list, set)):
                value = tuple(str(item) for item in value)
            elif isinstance(value, dict):
                value = tuple(sorted((k, str(v)) for k, v in value.items()))
            else:
                value = repr(value)
            parts.append(value)
        # The password error window is time-based: round it so the red border and
        # its message disappear on schedule without a per-frame signature change.
        if getattr(self, "password_error_until", 0.0):
            parts.append(self.password_error_until > 0.0)
        parts.append(self._collaborator_signature())
        return tuple(parts)

    def _collaborator_signature(self) -> Any:
        """Summarise the injected collaborators the drawing code reads.

        The Wi-Fi tab renders ``wifi_controller.snapshot`` and the SSH tab renders
        ``ssh_service.status()``. Both live outside this object, so without this
        the composite cache would freeze a network scan behind a stale frame —
        the worst kind of wrong, because it looks like the radio is broken.
        Summarising their *content* rather than excluding the tab keeps the tab
        cacheable while it is idle, which is where the 240 ms cost was.
        """

        parts: list[Any] = []
        try:
            snapshot = self.wifi_controller.snapshot
            parts.append(
                (
                    str(getattr(snapshot, "phase", "")),
                    tuple(
                        (
                            str(getattr(network, "ssid", "")),
                            str(getattr(network, "secure", "")),
                            str(getattr(network, "connected", "")),
                        )
                        for network in getattr(snapshot, "networks", ())
                    ),
                    str(getattr(snapshot, "selected_index", "")),
                    str(getattr(snapshot, "connected_ssid", "")),
                    str(getattr(snapshot, "error", "")),
                )
            )
        except Exception:
            parts.append("wifi-unavailable")
        try:
            status = self.ssh_service.status()
            parts.append(
                tuple(sorted((k, str(v)) for k, v in dict(status or {}).items()))
            )
        except Exception:
            parts.append("ssh-unavailable")
        return tuple(parts)

    def _serve_composite(self, screen: Any, key: Any) -> bool:
        """Present the cached frame when nothing it depends on has changed."""

        if self._content_animating:
            return False
        if self._panel_composite is None or self._panel_composite_key != key:
            return False
        if self._panel_composite.get_size() != screen.get_size():
            return False
        screen.blit(self._panel_composite, (0, 0))
        # Click handling needs the hit targets even when nothing was redrawn.
        self._targets[:] = self._panel_composite_targets
        if self.active_tab is ParentPanelTab.AUDIO:
            self._repaint_input_meter(screen, self._panel_composite_meter)
        return True

    def _store_composite(self, screen: Any, key: Any) -> None:
        """Keep this frame so the next one can be a single blit."""

        if self._content_animating:
            self._panel_composite = None
            self._panel_composite_key = None
            self._panel_composite_meter = None
            return
        self._panel_composite = screen.copy()
        self._panel_composite_key = key
        self._panel_composite_targets = list(self._targets)
        # Capture the live meter's band with the frame it belongs to, in screen
        # coordinates, so a served frame and the band used to top it up can never
        # disagree. A remembered band from an earlier layout is what put the meter
        # behind the tab strip, where a parent could not see it at all.
        self._panel_composite_meter = (
            self._meter_band_for_current_content()
            if self.active_tab is ParentPanelTab.AUDIO
            else None
        )

    def _ensure_panel_base(
        self,
        screen: Any,
        theme: Any,
        typography: GreiaTypography,
        pygame: Any,
        load_icon_fn: Callable[[str, int, Any], Any],
        base_surface: Any,
        base_key: Any,
    ) -> None:
        """Compose dim + large rounded chrome once per state change."""

        size = screen.get_size()
        key = (base_key, self.state, size)
        if (
            self._panel_base is not None
            and self._panel_base_key == key
            and self._panel_base.get_size() == size
        ):
            return

        base = base_surface.copy()
        if self.state == ParentPanelState.AUTH:
            card = self.auth_card_rect(size)
            pygame.draw.rect(base, (255, 250, 240), card, border_radius=24)
            pygame.draw.rect(base, (61, 44, 31), card, width=3, border_radius=24)
        else:
            panel_rect = pygame.Rect(20, 20, size[0] - 40, size[1] - 40)
            pygame.draw.rect(base, (255, 250, 240), panel_rect, border_radius=24)
            pygame.draw.rect(base, (61, 44, 31), panel_rect, width=3, border_radius=24)

            # Static header identity: title text and the close control.
            title = typography.render(
                "Parent Settings", FontRole.TITLE, 24, (61, 44, 31)
            )
            base.blit(title, (panel_rect.left + 24, panel_rect.top + 16))
            close_btn = pygame.Rect(
                panel_rect.right - 50, panel_rect.top + 10, 36, 36
            )
            pygame.draw.rect(base, (246, 236, 209), close_btn, border_radius=10)
            pygame.draw.rect(base, (61, 44, 31), close_btn, width=2, border_radius=10)
            icon_close = load_icon_fn("close_button", 22, pygame)
            base.blit(icon_close, icon_close.get_rect(center=close_btn.center))

        self._panel_base = base.convert()
        self._panel_base_key = key

    @staticmethod
    def _panel_close_button_rect(size: tuple[int, int]) -> Any:
        import pygame

        return pygame.Rect(size[0] - 70, 30, 36, 36)

    def _draw_auth_dialog(
        self,
        screen: Any,
        theme: Any,
        typography: GreiaTypography,
        pygame: Any,
        load_icon_fn: Callable[[str, int, Any], Any],
        chrome_in_base: bool = False,
    ) -> None:
        width, height = screen.get_size()

        # Card chrome (rounded fill + border) is baked into the composed
        # base when the launcher provides one.
        card = self.auth_card_rect((width, height))
        card_w = card.width
        if not chrome_in_base:
            self._blit_rounded_card(
                screen, card, theme.background, (255, 250, 240),
                pygame, (61, 44, 31), 3, radius=24,
            )

        title = self._get_text("Parent Settings", FontRole.TITLE, 28, (61, 44, 31), typography)
        screen.blit(title, title.get_rect(center=(card.centerx, card.top + 36)))

        subtitle = self._get_text("Enter Parent Password", FontRole.BODY, 18, (118, 104, 93), typography)
        screen.blit(subtitle, subtitle.get_rect(center=(card.centerx, card.top + 70)))

        input_rect = pygame.Rect(card.left + 30, card.top + 106, card_w - 60, 52)
        border_col = (181, 46, 46) if time.monotonic() < self.password_error_until else (241, 185, 35)
        self._blit_rounded_card(screen, input_rect, (255, 250, 240), (246, 236, 209), pygame, border_col, 3, radius=14)

        masked = self._masked_password(max(3, (input_rect.width - 32) // 14)) or "…"
        text_surf = self._get_text(masked, FontRole.CONTROL, 24, (61, 44, 31), typography)
        screen.blit(text_surf, text_surf.get_rect(midleft=(input_rect.left + 16, input_rect.centery)))

        if time.monotonic() < self.password_error_until:
            reason = self._password_problem or _PASSWORD_REJECTED
            reason_surf = self._get_text(
                reason, FontRole.BODY, 15, (181, 46, 46), typography
            )
            screen.blit(
                reason_surf,
                reason_surf.get_rect(center=(card.centerx, input_rect.bottom + 16)),
            )

        btn_w = (card_w - 80) // 2
        btn_h = 48
        btn_y = card.bottom - 66

        cancel_rect = pygame.Rect(card.left + 30, btn_y, btn_w, btn_h)
        confirm_rect = pygame.Rect(card.right - 30 - btn_w, btn_y, btn_w, btn_h)

        self._blit_rounded_card(screen, cancel_rect, (255, 250, 240), (230, 220, 205), pygame, radius=14)
        lbl_cancel = self._get_text("Cancel", FontRole.BODY, 18, (61, 44, 31), typography)
        screen.blit(lbl_cancel, lbl_cancel.get_rect(center=cancel_rect.center))
        self._targets.append(PanelHitTarget("cancel_auth", None, cancel_rect))

        self._blit_rounded_card(screen, confirm_rect, (255, 250, 240), (241, 185, 35), pygame, radius=14)
        lbl_confirm = self._get_text("Unlock", FontRole.BODY, 18, (61, 44, 31), typography)
        screen.blit(lbl_confirm, lbl_confirm.get_rect(center=confirm_rect.center))
        self._targets.append(PanelHitTarget("confirm_auth", None, confirm_rect))

    def _draw_panel(
        self,
        screen: Any,
        theme: Any,
        typography: GreiaTypography,
        pygame: Any,
        load_icon_fn: Callable[[str, int, Any], Any],
        chrome_in_base: bool = False,
    ) -> None:
        width, height = screen.get_size()
        panel_rect = pygame.Rect(20, 20, width - 40, height - 40)

        header_h = 56
        header_rect = pygame.Rect(panel_rect.left, panel_rect.top, panel_rect.width, header_h)

        if not chrome_in_base:
            # Standalone rendering (no composed base): draw all chrome here.
            self._blit_rounded_card(
                screen, panel_rect, theme.background, (255, 250, 240),
                pygame, (61, 44, 31), 3, radius=24,
            )

            title = self._get_text("Parent Settings", FontRole.TITLE, 24, (61, 44, 31), typography)
            screen.blit(title, (header_rect.left + 24, header_rect.top + 16))

            close_btn = self._panel_close_button_rect((width, height))
            self._blit_rounded_card(screen, close_btn, (255, 250, 240), (246, 236, 209), pygame, (61, 44, 31), 2, radius=10)
            icon_close = load_icon_fn("close_button", 22, pygame)
            screen.blit(icon_close, icon_close.get_rect(center=close_btn.center))

        # The close control's pixels live in the composed base when present;
        # its hit target must exist on every frame either way.
        self._targets.append(
            PanelHitTarget(
                "close_panel", None, self._panel_close_button_rect((width, height))
            )
        )

        tab_y = header_rect.bottom + 8
        tab_gap = 10
        tab_pad = 24
        tab_h = 38
        # Minimum column that still reads as a word. Below this the strip wraps
        # onto another row rather than shrinking every label into an ellipsis,
        # which is the same "grow downwards" rule the body text follows and the
        # only honest answer to a translated label that is wider than English.
        min_tab_w = 104
        usable = panel_rect.width - tab_pad * 2
        per_row = max(1, (usable + tab_gap) // (min_tab_w + tab_gap))
        rows = -(-len(text.TABS) // per_row)  # ceiling division
        row_widths = [
            panel_layout.even_columns(usable, count, tab_gap)
            for count in (
                [per_row] * (rows - 1) + [len(text.TABS) - per_row * (rows - 1)]
            )
        ]

        tab_x = panel_rect.left + tab_pad
        tab_row_top = tab_y
        index = 0
        for row, row_widths_for_row in enumerate(row_widths):
            for column, tab_w in enumerate(row_widths_for_row):
                label, tab_value = text.TABS[index]
                tab_id = ParentPanelTab(tab_value)
                is_active = self.active_tab == tab_id
                tab_rect = pygame.Rect(tab_x, tab_row_top + row * (tab_h + tab_gap), tab_w, tab_h)
                bg = (241, 185, 35) if is_active else (246, 236, 209)
                self._blit_rounded_card(
                    screen, tab_rect, (255, 250, 240), bg, pygame,
                    (61, 44, 31), 2 if is_active else 1, radius=12,
                )
                # Still measured, so an over-long single word shrinks before it
                # would ever be clipped.
                block = panel_layout.fit_single_line(
                    typography, label, FontRole.CONTROL, 16, (61, 44, 31),
                    tab_w - 12,
                )
                panel_layout.blit_block(
                    screen, block, pygame, tab_rect.centerx, tab_rect.centery,
                    align="center", bounds=tab_rect,
                )
                self._targets.append(PanelHitTarget("switch_tab", tab_id, tab_rect))
                tab_x += tab_w + tab_gap
                index += 1
            tab_x = panel_rect.left + tab_pad
        tab_strip_bottom = tab_row_top + rows * (tab_h + tab_gap) - tab_gap

        content_top = tab_strip_bottom + 12
        content_rect = pygame.Rect(
            panel_rect.left + 24,
            content_top,
            panel_rect.width - 48,
            max(80, panel_rect.bottom - content_top - 12),
        )

        # Tab content is composed on its own surface of exactly the content rect
        # and then blitted, so a form taller than the card is clipped rather than
        # spilling over the card edge onto the panel chrome. Surface blits clip
        # unconditionally, which makes "content can never escape its card" a
        # property of the structure instead of a thing each tab must remember.
        content_surface = pygame.Surface(
            (max(content_rect.width, 1), max(content_rect.height, 1)), pygame.SRCALPHA
        )
        _paint = content_surface
        # Tabs lay out from the surface origin, so they are given a local rect.
        # Their hit targets are content-local too and are rebased to screen space
        # after drawing.
        local_rect = pygame.Rect(0, 0, content_surface.get_width(), content_surface.get_height())
        # Everything registered before this point (the close control and the tab
        # strip) is already in screen coordinates and must not be rebased.
        content_target_start = len(self._targets)

        if self.active_tab == ParentPanelTab.LANGUAGE:
            self._draw_language_tab(_paint, local_rect, typography, pygame)
        elif self.active_tab == ParentPanelTab.AUDIO:
            self._draw_audio_tab(_paint, local_rect, typography, pygame)
        elif self.active_tab == ParentPanelTab.ACCOUNTS:
            self._draw_accounts_tab(_paint, local_rect, typography, pygame)
        elif self.active_tab == ParentPanelTab.SECURITY:
            self._draw_security_tab(_paint, local_rect, typography, pygame)
        elif self.active_tab == ParentPanelTab.WIFI:
            self._draw_wifi_tab(_paint, local_rect, typography, pygame, load_icon_fn)
        elif self.active_tab == ParentPanelTab.SSH:
            self._draw_ssh_tab(_paint, local_rect, typography, pygame, load_icon_fn)
        elif self.active_tab == ParentPanelTab.INFO:
            self._draw_info_tab(_paint, local_rect, typography, pygame, load_icon_fn)
        elif self.active_tab == ParentPanelTab.POINTER:
            self._draw_pointer_tab(_paint, local_rect, typography, pygame)

        # The content surface is drawn in content-local coordinates, so the
        # hit targets it registered are offset by the same amount before they
        # are used for click hit-testing against screen coordinates.
        self._content_origin = content_rect.topleft
        self._rebase_targets(content_rect, content_target_start)
        screen.blit(content_surface, content_rect.topleft)

    def _rebase_targets(self, content_rect: Any, start: int) -> None:
        """Move content-local hit targets into screen coordinates.

        Tabs are painted onto a surface whose origin is the content rect, so the
        rectangles they register are relative to that origin. Rebasing keeps click
        handling correct without every tab knowing it is being painted offscreen.
        Only targets from ``start`` onwards are content-local; the close control
        and tab strip are registered earlier, already in screen coordinates, and
        rebasing them would shift the tab bar out from under its own pixels.
        """

        offset = (content_rect.left, content_rect.top)
        for index in range(start, len(self._targets)):
            target = self._targets[index]
            self._targets[index] = PanelHitTarget(
                target.action, target.value, target.rect.move(*offset)
            )

    def _draw_language_tab(
        self,
        screen: Any,
        rect: Any,
        typography: GreiaTypography,
        pygame: Any,
    ) -> None:
        font_body_size = 16
        card = pygame.Rect(rect.left, rect.top, rect.width, rect.height)
        self._blit_rounded_card(screen, card, (255, 250, 240), (246, 236, 209), pygame, radius=16)
        title = self._get_text("Greia language", FontRole.TITLE, 22, (61, 44, 31), typography)
        screen.blit(title, (card.left + 20, card.top + 14))
        note = self._get_text(
            "This changes the device default. Activities use their own supported-language fallback.",
            FontRole.BODY,
            font_body_size,
            (118, 104, 93),
            typography,
        )
        screen.blit(note, (card.left + 20, card.top + 44))

        columns = 3
        gap = 10
        left = card.left + 18
        top = card.top + 78
        width = card.width - 36
        cell_w = (width - gap * (columns - 1)) // columns
        cell_h = 62
        for index, language in enumerate(SUPPORTED_SYSTEM_LANGUAGES):
            row, column = divmod(index, columns)
            cell = pygame.Rect(
                left + column * (cell_w + gap),
                top + row * (cell_h + 8),
                cell_w,
                cell_h,
            )
            selected = index == self._language_index
            self._blit_rounded_card(
                screen,
                cell,
                (246, 236, 209),
                (241, 185, 35) if selected else (255, 250, 240),
                pygame,
                (61, 44, 31),
                3 if selected else 1,
                radius=12,
            )
            flag = self._get_text(language.flag, FontRole.DISPLAY, 28, (61, 44, 31), typography)
            screen.blit(flag, flag.get_rect(midleft=(cell.left + 10, cell.centery)))
            label = self._get_text(language.name, FontRole.BODY, font_body_size, (61, 44, 31), typography)
            screen.blit(label, label.get_rect(midleft=(cell.left + 54, cell.centery)))
            self._targets.append(PanelHitTarget("language_select", index, cell))

        if self._language_message:
            message = self._get_text(
                self._language_message,
                FontRole.BODY,
                font_body_size,
                (181, 46, 46) if self._language_message.startswith("Could not") else (47, 117, 81),
                typography,
            )
            screen.blit(message, (card.left + 20, card.bottom - 26))

    # --- Child accounts and Parent password -------------------------------
    #
    # Both tabs act through the Parent API using the session established at
    # unlock, so the panel never writes profile or credential storage as the
    # child identity. The service keeps its own guards: it refuses to remove the
    # signed-in child or the last remaining account, and it revalidates that a
    # profile's data path is a managed directory rather than a symlink.

    def _parent_client(self) -> Any:
        """The verifier when it can also issue API calls, else no client."""

        return self.credential_verifier if hasattr(
            self.credential_verifier, "list_child_accounts"
        ) else None

    def _available_avatars(self) -> tuple[str, ...]:
        """Avatars from the shipped profile policy, never a duplicated list.

        The service validates avatar ids against
        ``runtime/profile-defaults.toml``; offering anything else produces a
        refusal the parent cannot act on. An unreadable policy falls back to the
        store's own default, so the tab still renders.
        """

        try:
            from greia_platform.profiles import ProfilePolicy

            root = Path(os.environ.get("GREIA_OS_ROOT", "/opt/greia-os"))
            policy = ProfilePolicy.load(root / "runtime" / "profile-defaults.toml")
            if policy.avatars:
                return tuple(policy.avatars)
            return (policy.default_avatar,)
        except Exception:
            return ("rainbow",)

    def _max_profiles(self) -> int:
        try:
            from greia_platform.profiles import ProfilePolicy

            root = Path(os.environ.get("GREIA_OS_ROOT", "/opt/greia-os"))
            return int(
                ProfilePolicy.load(root / "runtime" / "profile-defaults.toml").max_profiles
            )
        except Exception:
            return 8

    def _max_name_characters(self) -> int:
        try:
            from greia_platform.profiles import ProfilePolicy

            root = Path(os.environ.get("GREIA_OS_ROOT", "/opt/greia-os"))
            return int(
                ProfilePolicy.load(
                    root / "runtime" / "profile-defaults.toml"
                ).max_name_characters
            )
        except Exception:
            return 24

    def _ensure_mic_level_running(self, wanted: bool) -> None:
        """Hold the capture device only while the audio tab is on screen.

        A parent who is looking at Wi-Fi should not have the microphone held
        open, so capture follows the tab rather than the panel's lifetime.
        """

        if wanted:
            self._mic_level_reader.start()
        else:
            self._mic_level_reader.stop()
            self._mic_peak_hold_dbfs = SILENCE_FLOOR_DBFS

    def _refresh_accounts(self) -> None:
        client, session = self._parent_client(), self._session
        if client is None or session is None:
            return
        try:
            self._accounts = list(client.list_child_accounts(session))
            self._accounts_loaded = True
        except ParentCredentialUnavailable:
            self._set_accounts_message(text.STATUS_OFFLINE, error=True)
        except Exception:
            self._set_accounts_message(text.STATUS_OFFLINE, error=True)

    def _set_accounts_message(self, message: str | None, *, error: bool = False) -> None:
        self._accounts_message = message
        self._accounts_message_is_error = error

    def _set_security_message(self, message: str | None, *, error: bool = False) -> None:
        self._security_message = message
        self._security_message_is_error = error

    def _create_account(self) -> None:
        client, session = self._parent_client(), self._session
        if client is None or session is None:
            self._set_accounts_message(text.STATUS_OFFLINE, error=True)
            return
        name = self._account_name.strip()
        if not name:
            self._set_accounts_message(text.ACCOUNTS_NAME_LABEL, error=True)
            return
        age: int | None = None
        if self._account_age.strip():
            try:
                age = int(self._account_age.strip())
            except ValueError:
                self._set_accounts_message(text.ACCOUNTS_AGE_LABEL, error=True)
                return
        avatars = self._available_avatars()
        avatar = avatars[self._account_avatar_index % len(avatars)]
        try:
            client.add_child_account(
                session, display_name=name, avatar_id=avatar, approximate_age=age
            )
        except ParentRequestFailed as exc:
            self._set_accounts_message(exc.reason, error=True)
            return
        except ParentCredentialUnavailable:
            self._set_accounts_message(text.STATUS_OFFLINE, error=True)
            return
        except Exception:
            self._set_accounts_message(text.STATUS_OFFLINE, error=True)
            return
        self._account_name = ""
        self._account_age = ""
        self._accounts_mode = "list"
        self._text_field = None
        self._set_accounts_message(text.STATUS_SAVED)
        self._refresh_accounts()

    def _start_rename(self, account: ChildAccount) -> None:
        """Open the add form pre-filled to edit one child instead of adding one."""

        self._renaming = account
        self._accounts_mode = "add"
        self._text_field = "account_name"
        self._account_name = account.display_name
        avatars = self._available_avatars()
        if account.avatar_id in avatars:
            self._account_avatar_index = avatars.index(account.avatar_id)
        self._account_age = (
            str(account.approximate_age) if account.approximate_age is not None else ""
        )
        self._set_accounts_message(None)

    def _save_rename(self) -> None:
        client, session = self._parent_client(), self._session
        target = self._renaming
        name = self._account_name.strip()
        if target is None or not name:
            self._set_accounts_message(text.ACCOUNTS_NAME_LABEL, error=True)
            return
        if client is None or session is None:
            self._set_accounts_message(text.STATUS_OFFLINE, error=True)
            return
        try:
            client.rename_child_account(session, target.profile_id, name)
        except ParentRequestFailed as exc:
            self._set_accounts_message(exc.reason, error=True)
            return
        except Exception:
            self._set_accounts_message(text.STATUS_OFFLINE, error=True)
            return
        self._renaming = None
        self._account_name = ""
        self._account_age = ""
        self._accounts_mode = "list"
        self._text_field = None
        self._set_accounts_message(text.STATUS_SAVED)
        self._refresh_accounts()

    def _remove_account(self, account: ChildAccount) -> None:
        client, session = self._parent_client(), self._session
        if client is None or session is None:
            self._set_accounts_message(text.STATUS_OFFLINE, error=True)
            return
        try:
            client.remove_child_account(session, account.profile_id)
        except ParentRequestFailed as exc:
            self._set_accounts_message(exc.reason, error=True)
            return
        except Exception:
            self._set_accounts_message(text.STATUS_OFFLINE, error=True)
            return
        self._pending_remove = None
        self._accounts_mode = "list"
        self._set_accounts_message(text.STATUS_SAVED)
        self._refresh_accounts()

    def _change_password(self) -> None:
        client, session = self._parent_client(), self._session
        if client is None or session is None:
            self._set_security_message(text.STATUS_OFFLINE, error=True)
            return
        if self._security_new != self._security_confirm:
            self._set_security_message(text.SECURITY_MISMATCH, error=True)
            return
        try:
            client.change_parent_password(
                session, self._security_current, self._security_new
            )
        except ParentRequestFailed as exc:
            reason = exc.reason
            if "current" in reason.lower():
                reason = text.SECURITY_CURRENT_WRONG
            self._set_security_message(reason, error=True)
            return
        except Exception:
            self._set_security_message(text.STATUS_OFFLINE, error=True)
            return
        self._security_current = ""
        self._security_new = ""
        self._security_confirm = ""
        self._set_security_message(text.SECURITY_CHANGED)

    def _cycle_avatar(self, step: int) -> None:
        count = len(self._available_avatars())
        if count:
            self._account_avatar_index = (self._account_avatar_index + step) % count

    def _field_value(self, name: str) -> str:
        return {
            "account_name": self._account_name,
            "account_age": self._account_age,
            "security_current": self._security_current,
            "security_new": self._security_new,
            "security_confirm": self._security_confirm,
        }.get(name, "")

    def _set_field_value(self, name: str, value: str) -> None:
        if name == "account_name":
            self._account_name = value[: self._max_name_characters()]
        elif name == "account_age":
            self._account_age = value[:3]
        elif name == "security_current":
            self._security_current = value
        elif name == "security_new":
            self._security_new = value
        elif name == "security_confirm":
            self._security_confirm = value

    def _draw_text_field(
        self,
        screen: Any,
        pygame: Any,
        typography: GreiaTypography,
        rect: Any,
        label: str,
        value: str,
        field: str,
        *,
        placeholder: str = "",
        secret: bool = False,
    ) -> None:
        """A labelled single-line input whose width is driven by measurement."""

        self._blit_rounded_card(
            screen, rect, (255, 250, 240), (246, 236, 209), pygame,
            (61, 44, 31), 2 if self._text_field == field else 1, radius=12,
        )
        shown = ("\u2022" * len(value)) if secret else value
        if not shown and placeholder:
            body = panel_layout.fit_single_line(
                typography, placeholder, FontRole.BODY, 16, (150, 138, 126),
                rect.width - 20,
            )
        else:
            body = panel_layout.fit_single_line(
                typography, shown, FontRole.BODY, 16, (61, 44, 31), rect.width - 20
            )
        panel_layout.blit_block(
            screen, body, pygame, rect.left + 10, rect.centery,
            bounds=rect,
        )
        self._targets.append(PanelHitTarget("focus_field", field, rect))

    def _draw_card_header(
        self,
        screen: Any,
        pygame: Any,
        typography: GreiaTypography,
        card: Any,
        pad: int,
        title_text: str,
        intro_text: str,
        top: int | None = None,
        reserve_right: int = 0,
    ) -> int:
        """Draw a wrapped title and intro, returning the next free y.

        ``reserve_right`` narrows the text so a header-row action button cannot
        sit on top of it. Without it the intro ran the full card width and the
        button was painted over the first line.
        """

        y = card.top + 16 if top is None else top
        text_w = card.width - pad * 2 - reserve_right
        title = panel_layout.fit_text_block(
            typography, title_text, FontRole.TITLE, 22, (61, 44, 31), text_w
        )
        panel_layout.blit_block(screen, title, pygame, card.left + pad, y)
        y += title.height + 8
        intro = panel_layout.fit_text_block(
            typography, intro_text, FontRole.BODY, 16, (118, 104, 93), text_w
        )
        panel_layout.blit_block(screen, intro, pygame, card.left + pad, y)
        return y + intro.height + 18

    def _draw_status(
        self,
        screen: Any,
        pygame: Any,
        typography: GreiaTypography,
        card: Any,
        pad: int,
        y: int,
        message: str | None,
        is_error: bool,
    ) -> None:
        if not message:
            return
        block = panel_layout.fit_text_block(
            typography, message, FontRole.BODY, 16,
            (181, 46, 46) if is_error else (47, 117, 81),
            card.width - pad * 2, max_lines=3,
        )
        panel_layout.blit_block(screen, block, pygame, card.left + pad, y)

    def _draw_accounts_tab(
        self,
        screen: Any,
        rect: Any,
        typography: GreiaTypography,
        pygame: Any,
    ) -> None:
        card = pygame.Rect(rect.left, rect.top, rect.width, rect.height)
        self._blit_rounded_card(screen, card, (255, 250, 240), (246, 236, 209), pygame, radius=16)
        pad = 24
        inner_w = card.width - pad * 2

        if self._accounts_mode == "add":
            editing = self._renaming is not None
            y = self._draw_card_header(
                screen, pygame, typography, card, pad,
                text.ACCOUNTS_EDIT if editing else text.ACCOUNTS_ADD,
                text.ACCOUNTS_INTRO,
            )
            # Name and age share a row. Stacked, the form was taller than the
            # card at 600 px with a wrapped tab strip, and the action buttons
            # were clipped in half. Sharing a row is layout-driven, not cosmetic.
            gap = 12
            age_w = min(220, inner_w // 3)
            name_w = inner_w - age_w - gap
            for index, (label, field, value, placeholder, field_w) in enumerate((
                (text.ACCOUNTS_NAME_LABEL, "account_name", self._account_name,
                 text.ACCOUNTS_NAME_PLACEHOLDER, name_w),
                (text.ACCOUNTS_AGE_LABEL, "account_age", self._account_age,
                 text.ACCOUNTS_AGE_PLACEHOLDER, age_w),
            )):
                field_x = card.left + pad + (0 if index == 0 else name_w + gap)
                caption = panel_layout.fit_text_block(
                    typography, label, FontRole.BODY, 15, (118, 104, 93), field_w
                )
                panel_layout.blit_block(screen, caption, pygame, field_x, y)
                caption_h = caption.height
                field_rect = pygame.Rect(field_x, y + caption_h + 4, field_w, 44)
                self._draw_text_field(
                    screen, pygame, typography, field_rect, label, value, field,
                    placeholder=placeholder,
                )
            y += caption_h + 4 + 44 + 16

            avatars = self._available_avatars()
            caption = panel_layout.fit_text_block(
                typography, text.ACCOUNTS_AVATAR_LABEL, FontRole.BODY, 15,
                (118, 104, 93), inner_w,
            )
            panel_layout.blit_block(screen, caption, pygame, card.left + pad, y)
            y += caption.height + 4
            picker = pygame.Rect(card.left + pad, y, inner_w, 48)
            self._blit_rounded_card(
                screen, picker, (255, 250, 240), (246, 236, 209), pygame,
                (61, 44, 31), 1, radius=12,
            )
            current = avatars[self._account_avatar_index % len(avatars)]
            name_block = panel_layout.fit_single_line(
                typography, current.replace("_", " "), FontRole.CONTROL, 17,
                (61, 44, 31), picker.width - 140,
            )
            panel_layout.blit_block(
                screen, name_block, pygame, picker.centerx, picker.centery,
                align="center", bounds=picker,
            )
            step_w = 64
            for side, step in (("prev", -1), ("next", 1)):
                btn = pygame.Rect(
                    picker.right - 12 - step_w if side == "prev" else picker.right - 12 - step_w,
                    picker.top + 6, step_w, picker.height - 12,
                )
                if side == "prev":
                    btn.x = picker.left + 12
                self._blit_rounded_card(
                    screen, btn, (246, 236, 209), (255, 250, 240), pygame,
                    (61, 44, 31), 1, radius=10,
                )
                # Drawn, not typeset: U+25C0/U+25B6 are absent from the bundled
                # fonts and rendered as grey tofu boxes, the same defect the
                # audio tab's U+2796 step buttons had.
                cx, cy = btn.centerx, btn.centery
                size = min(btn.width, btn.height) // 4
                if side == "prev":
                    points = [
                        (cx + size // 2, cy - size),
                        (cx + size // 2, cy + size),
                        (cx - size // 2, cy),
                    ]
                else:
                    points = [
                        (cx - size // 2, cy - size),
                        (cx - size // 2, cy + size),
                        (cx + size // 2, cy),
                    ]
                pygame.draw.polygon(screen, (61, 44, 31), points)
                self._targets.append(PanelHitTarget("account_avatar", step, btn))
            y += 48 + 18

            gap = 12
            half = (inner_w - gap) // 2
            for index, (label, action) in enumerate((
                (text.ACCOUNTS_CANCEL, "account_cancel"),
                (
                    text.ACCOUNTS_SAVE if editing else text.ACCOUNTS_CREATE,
                    "account_save" if editing else "account_create",
                ),
            )):
                btn = pygame.Rect(
                    card.left + pad + index * (half + gap), y, half, 48
                )
                self._blit_rounded_card(
                    screen, btn, (255, 250, 240),
                    (241, 185, 35)
                    if action in {"account_create", "account_save"}
                    else (246, 236, 209),
                    pygame, (61, 44, 31),
                    2 if action in {"account_create", "account_save"} else 1,
                    radius=12,
                )
                block = panel_layout.fit_single_line(
                    typography, label, FontRole.CONTROL, 17, (61, 44, 31), btn.width - 14
                )
                panel_layout.blit_block(
                    screen, block, pygame, btn.centerx, btn.centery,
                    align="center", bounds=btn,
                )
                self._targets.append(PanelHitTarget(action, None, btn))
            y += 48 + 12
            self._draw_status(
                screen, pygame, typography, card, pad, y,
                self._accounts_message, self._accounts_message_is_error,
            )
            return

        if self._accounts_mode == "confirm" and self._pending_remove is not None:
            y = self._draw_card_header(
                screen, pygame, typography, card, pad,
                text.ACCOUNTS_CONFIRM_REMOVE_TITLE,
                text.ACCOUNTS_CONFIRM_REMOVE_BODY,
            )
            name = panel_layout.fit_text_block(
                typography, self._pending_remove.display_name, FontRole.TITLE, 20,
                (61, 44, 31), inner_w,
            )
            panel_layout.blit_block(screen, name, pygame, card.left + pad, y)
            y += name.height + 20
            gap = 12
            half = (inner_w - gap) // 2
            for index, (label, action, tone) in enumerate((
                (text.ACCOUNTS_CANCEL, "account_remove_cancel", (246, 236, 209)),
                (text.ACCOUNTS_CONFIRM_REMOVE_YES, "account_remove_confirm", (181, 46, 46)),
            )):
                btn = pygame.Rect(card.left + pad + index * (half + gap), y, half, 48)
                self._blit_rounded_card(
                    screen, btn, (255, 250, 240), tone, pygame, (61, 44, 31), 2, radius=12
                )
                block = panel_layout.fit_single_line(
                    typography, label, FontRole.CONTROL, 16, (61, 44, 31), btn.width - 14
                )
                panel_layout.blit_block(
                    screen, block, pygame, btn.centerx, btn.centery,
                    align="center", bounds=btn,
                )
                self._targets.append(PanelHitTarget(action, None, btn))
            return

        # The "Add child" button shares the title's row, so the flow below it
        # starts under the button rather than beside it. Letting the intro run
        # full width under the button only avoided it by vertical luck.
        header_top = card.top + 16
        add_w = 168
        y = self._draw_card_header(
            screen, pygame, typography, card, pad,
            text.ACCOUNTS_TITLE, text.ACCOUNTS_INTRO, top=header_top,
            reserve_right=add_w + 12,
        )
        y = max(y, header_top + 42 + 12)
        limit = self._max_profiles()
        at_limit = len(self._accounts) >= limit
        add_rect = pygame.Rect(card.right - pad - add_w, header_top, add_w, 42)
        self._blit_rounded_card(
            screen, add_rect, (255, 250, 240),
            (222, 208, 178) if at_limit else (241, 185, 35), pygame,
            (61, 44, 31), 1, radius=12,
        )
        block = panel_layout.fit_single_line(
            typography, text.ACCOUNTS_ADD, FontRole.CONTROL, 17, (61, 44, 31), add_w - 14
        )
        panel_layout.blit_block(
            screen, block, pygame, add_rect.centerx, add_rect.centery,
            align="center", bounds=add_rect,
        )
        if not at_limit:
            self._targets.append(PanelHitTarget("account_add", None, add_rect))

        if not self._accounts_loaded:
            self._refresh_accounts()
        if not self._accounts:
            empty = panel_layout.fit_text_block(
                typography, text.ACCOUNTS_EMPTY, FontRole.BODY, 16,
                (118, 104, 93), inner_w,
            )
            panel_layout.blit_block(screen, empty, pygame, card.left + pad, y + 8)
        else:
            row_h = 60
            gap_y = 10
            for index, account in enumerate(self._accounts):
                row = pygame.Rect(
                    card.left + pad, y + index * (row_h + gap_y), inner_w, row_h
                )
                if row.bottom > card.bottom - 40:
                    break
                self._blit_rounded_card(
                    screen, row, (246, 236, 209), (255, 250, 240), pygame,
                    (61, 44, 31), 1, radius=12,
                )
                name = panel_layout.fit_single_line(
                    typography, account.display_name, FontRole.CONTROL, 18,
                    (61, 44, 31),
                    row.width - (rename_w + remove_w + 38),
                )
                panel_layout.blit_block(
                    screen, name, pygame, row.left + 14, row.centery, bounds=row
                )
                remove_w = 110
                rename_w = 110
                remove_rect = pygame.Rect(
                    row.right - 14 - remove_w, row.top + 9, remove_w, row_h - 18
                )
                rename_rect = pygame.Rect(
                    remove_rect.left - 10 - rename_w, row.top + 9, rename_w, row_h - 18
                )
                self._blit_rounded_card(
                    screen, rename_rect, (255, 250, 240), (246, 236, 209), pygame,
                    (61, 44, 31), 1, radius=10,
                )
                rename_label = panel_layout.fit_single_line(
                    typography, text.ACCOUNTS_RENAME, FontRole.CONTROL, 16,
                    (61, 44, 31), rename_w - 12,
                )
                panel_layout.blit_block(
                    screen, rename_label, pygame, rename_rect.centerx,
                    rename_rect.centery, align="center", bounds=rename_rect,
                )
                self._targets.append(
                    PanelHitTarget("account_rename", account.profile_id, rename_rect)
                )
                self._blit_rounded_card(
                    screen, remove_rect, (255, 250, 240), (246, 236, 209), pygame,
                    (181, 46, 46), 1, radius=10,
                )
                remove_label = panel_layout.fit_single_line(
                    typography, text.ACCOUNTS_REMOVE, FontRole.CONTROL, 16,
                    (181, 46, 46), remove_w - 12,
                )
                panel_layout.blit_block(
                    screen, remove_label, pygame, remove_rect.centerx,
                    remove_rect.centery, align="center", bounds=remove_rect,
                )
                self._targets.append(
                    PanelHitTarget("account_remove", account.profile_id, remove_rect)
                )
            y += len(self._accounts) * (row_h + gap_y)
        y += 12
        if at_limit:
            self._draw_status(
                screen, pygame, typography, card, pad, y,
                text.ACCOUNTS_LIMIT_REACHED.format(count=limit), True,
            )
        else:
            self._draw_status(
                screen, pygame, typography, card, pad, y,
                self._accounts_message, self._accounts_message_is_error,
            )

    def _draw_security_tab(
        self,
        screen: Any,
        rect: Any,
        typography: GreiaTypography,
        pygame: Any,
    ) -> None:
        card = pygame.Rect(rect.left, rect.top, rect.width, rect.height)
        self._blit_rounded_card(screen, card, (255, 250, 240), (246, 236, 209), pygame, radius=16)
        pad = 24
        inner_w = card.width - pad * 2
        header_top = card.top + 16
        action_w = 200
        y = self._draw_card_header(
            screen, pygame, typography, card, pad,
            text.SECURITY_TITLE, text.SECURITY_INTRO, top=header_top,
            reserve_right=action_w + 12,
        )
        # The action sits on the title's row, as "Add child" does on the accounts
        # tab. Stacked below three masked fields it was clipped in half at 600 px
        # once the tab strip wrapped onto two rows.
        action = pygame.Rect(card.right - pad - action_w, header_top, action_w, 42)
        self._blit_rounded_card(
            screen, action, (255, 250, 240), (241, 185, 35), pygame, (61, 44, 31), 2, radius=12
        )
        action_label = panel_layout.fit_single_line(
            typography, text.SECURITY_CHANGE, FontRole.CONTROL, 16, (61, 44, 31),
            action_w - 14,
        )
        panel_layout.blit_block(
            screen, action_label, pygame, action.centerx, action.centery,
            align="center", bounds=action,
        )
        self._targets.append(PanelHitTarget("security_change", None, action))
        y = max(y, header_top + 42 + 14)

        for label, field, value in (
            (text.SECURITY_CURRENT_LABEL, "security_current", self._security_current),
            (text.SECURITY_NEW_LABEL, "security_new", self._security_new),
            (text.SECURITY_CONFIRM_LABEL, "security_confirm", self._security_confirm),
        ):
            caption = panel_layout.fit_text_block(
                typography, label, FontRole.BODY, 15, (118, 104, 93), inner_w
            )
            panel_layout.blit_block(screen, caption, pygame, card.left + pad, y)
            y += caption.height + 4
            field_rect = pygame.Rect(card.left + pad, y, inner_w, 44)
            self._draw_text_field(
                screen, pygame, typography, field_rect, label, value, field, secret=True
            )
            y += 44 + 14
        self._draw_status(
            screen, pygame, typography, card, pad, y,
            self._security_message, self._security_message_is_error,
        )

    #: Height reserved below the readout for the value row, its gap and the bar,
    #: so a band's height does not depend on which readout is showing.
    _METER_RESERVED_TAIL = 38

    _POINTER_FLASH_SECONDS = 1.2

    def needs_frame(self) -> bool:
        """Whether the overlay has live content that must be repainted.

        The launcher is event driven: it draws when something happens. A live
        input meter is content that changes with no event behind it, so without
        this the visualiser only advanced when the pointer happened to move. This
        asks for a frame only while the meter is actually on screen, so every
        other state keeps its existing no-redraw-when-nothing-changed behaviour.
        """

        # True for as long as the audio tab is the one on screen, not only once a
        # level has arrived. Gating this on having a level deadlocked: the client
        # is started from inside draw(), draw() only happens on an event, and the
        # event loop only redraws when this returns True. No level meant no redraw
        # meant the client was never started, so the meter only ever appeared when
        # something moved the pointer. The client starts the level service on its
        # first connect, so a few frames here is all it takes to come up.
        if self.active_tab is ParentPanelTab.AUDIO:
            return True
        # The pointer test area flashes a marker where the last press landed, and
        # that flash decays with time. Redraw only while one is visible, so the
        # test area responds without making the tab repaint continuously.
        if self.active_tab is ParentPanelTab.POINTER:
            flash = self._pointer_test_flash
            if flash is not None:
                return (
                    time.monotonic() - self._pointer_test_flash_at
                    < _POINTER_FLASH_SECONDS
                )
        return False

    def _meter_band_for_current_content(self) -> Any:
        """The meter's band in screen coordinates, or None if there is none.

        Tabs lay out on a content surface whose origin is zero, so the band a tab
        records is content-local and has to be offset before it can be used on the
        presented frame. Skipping that offset is what drew the meter over the tab
        strip when a cached audio frame was topped up.
        """

        if self._meter_band_rect is None:
            return None
        return self._meter_band_rect.move(self._content_origin)

    def _draw_input_meter(
        self,
        screen: Any,
        pygame: Any,
        typography: GreiaTypography,
        card: Any,
        pad: int,
        y: int,
        inner_w: int,
    ) -> int:
        """Draw the live meter and record the band it occupies.

        On a cache hit this is not called at all; the band recorded here is
        captured into the cache entry and used to repaint just this region.
        Excluding the whole audio tab from the cache instead was tried, and cost a
        full software redraw - about 262 ms a frame on the reference Acer - to
        change the same few hundred pixels.
        """

        start = y
        bottom = self._paint_input_meter(
            screen, pygame, typography, card, pad, y, inner_w
        )
        band_w = inner_w - self._noise_column_width(inner_w) - 12
        self._meter_band_rect = pygame.Rect(
            card.left + pad - 4, start, band_w + 8, max(0, bottom - start) + 6
        )
        return bottom

    def _repaint_input_meter(self, screen: Any, band: Any) -> None:
        """Repaint only the meter on top of an already presented frame."""

        if band is None or band.height <= 0:
            return
        pygame = sys.modules["pygame"]
        typography = self._typography_for_overlay
        if typography is None:
            return
        pygame.draw.rect(screen, (255, 250, 240), band, border_radius=8)
        self._paint_input_meter(
            screen, pygame, typography, band, 8, band.top + 3, band.width - 16
        )

    def _paint_input_meter(
        self,
        screen: Any,
        pygame: Any,
        typography: GreiaTypography,
        card: Any,
        pad: int,
        y: int,
        inner_w: int,
    ) -> int:
        """Live microphone input level, with a peak hold and a clip warning.

        The gain meter below shows the *setting*. This shows what the microphone
        is actually hearing, which is the only way a parent can tell a working
        microphone from a muted one, and the only way to notice that a gain is
        too high. Measured on the reference Acer, whose ALC268 input was peaking
        at 0.0 dBFS, i.e. clipping, with no indication of it anywhere in the UI.
        """

        noise_w = self._noise_column_width(inner_w)
        meter_w = inner_w - noise_w - 12 if noise_w else inner_w
        level: MicrophoneLevel = self._mic_level_reader.level
        now = time.monotonic()
        if level.available:
            if level.peak_dbfs >= self._mic_peak_hold_dbfs:
                self._mic_peak_hold_dbfs = level.peak_dbfs
                self._mic_peak_hold_until = now + 1.2
            elif now > self._mic_peak_hold_until:
                self._mic_peak_hold_dbfs = max(
                    SILENCE_FLOOR_DBFS, self._mic_peak_hold_dbfs - 1.0
                )

        title = panel_layout.fit_text_block(
            typography, text.AUDIO_INPUT_LABEL, FontRole.CONTROL, 18,
            (61, 44, 31), meter_w,
        )
        panel_layout.blit_block(screen, title, pygame, card.left + pad, y)
        y += title.height + 6

        if not level.available:
            # "No microphone" is only honest when the endpoint itself is gone. The
            # capture device is exclusive, so another process opening it briefly -
            # including a diagnostic - starves the meter without there being
            # anything wrong with the microphone.
            reason = str(level.device or "")
            waiting = not reason or reason in {"starting", "reconnecting", "service stopped", "no service"}
            note = panel_layout.fit_text_block(
                typography,
                text.AUDIO_INPUT_WAITING if waiting else text.AUDIO_INPUT_UNAVAILABLE,
                FontRole.BODY, 15, (150, 138, 126), meter_w,
            )
            panel_layout.blit_block(screen, note, pygame, card.left + pad, y)
            # Reserve the same height the value row and bar would occupy. The
            # repaint band is captured from one of these draws and replayed on
            # cached frames, so a band measured while the input looked unavailable
            # was shorter than the bar actually needed, and repainting a live
            # level then painted over the gain controls below.
            return y + note.height + self._METER_RESERVED_TAIL

        readout = f"{level.rms_dbfs:+.0f} dB" if not level.silent else text.AUDIO_INPUT_SILENT
        if level.clipping:
            readout = f"{text.AUDIO_INPUT_CLIPPING}  {level.rms_dbfs:+.0f} dB"
        value = panel_layout.fit_single_line(
            typography, readout, FontRole.CONTROL, 16,
            (181, 46, 46) if level.clipping else (61, 44, 31), meter_w,
        )
        # Right-aligned inside the meter's own width. It was placed at
        # card.left + pad + inner_w, which is the far edge of the whole row: it
        # landed under the noise cancelling column and clamp_ip then shoved it to
        # the panel edge, leaving a stray "dB" fragment there.
        panel_layout.blit_block(
            screen, value, pygame, card.left + pad + meter_w, y,
            align="right",
        )

        bar_h = 16
        track = pygame.Rect(card.left + pad, y + value.height + 4, meter_w, bar_h)
        pygame.draw.rect(screen, (222, 208, 178), track, border_radius=bar_h // 2)

        def position(db: float) -> int:
            span = 0.0 - SILENCE_FLOOR_DBFS
            fraction = (db - SILENCE_FLOOR_DBFS) / span if span else 0.0
            return int(track.width * max(0.0, min(1.0, fraction)))

        filled = position(level.rms_dbfs)
        if filled > 0:
            pygame.draw.rect(
                screen, (181, 46, 46) if level.clipping else (241, 185, 35),
                pygame.Rect(track.left, track.top, filled, track.height),
                border_radius=bar_h // 2,
            )
        peak_x = track.left + position(self._mic_peak_hold_dbfs)
        pygame.draw.rect(
            screen, (61, 44, 31),
            pygame.Rect(peak_x - 1, track.top - 3, 3, track.height + 6),
        )
        return track.bottom

    def _draw_audio_tab(
        self,
        screen: Any,
        rect: Any,
        typography: GreiaTypography,
        pygame: Any,
    ) -> None:
        self._ensure_mic_level_running(True)
        if not self._audio_settings_loaded:
            self._refresh_audio_processing()
        card = pygame.Rect(rect.left, rect.top, rect.width, rect.height)
        self._blit_rounded_card(screen, card, (255, 250, 240), (246, 236, 209), pygame, radius=16)
        pad = 24
        inner_w = card.width - pad * 2
        y = card.top + 16

        # Title and intro are measured, not placed at fixed offsets, so a
        # translated string that needs two lines pushes everything below it
        # down instead of landing on the first control.
        title = panel_layout.fit_text_block(
            typography, text.AUDIO_TITLE, FontRole.TITLE, 22, (61, 44, 31), inner_w
        )
        panel_layout.blit_block(screen, title, pygame, card.left + pad, y)
        y += title.height + 8

        intro = panel_layout.fit_text_block(
            typography, text.AUDIO_INTRO, FontRole.BODY, 16, (118, 104, 93), inner_w
        )
        panel_layout.blit_block(screen, intro, pygame, card.left + pad, y)
        y += intro.height + 18

        meter_top = y
        y = self._draw_input_meter(screen, pygame, typography, card, pad, y, inner_w)
        # The noise cancelling controls sit beside the meter rather than below
        # it. The audio tab already fills the 600 px reference screen vertically,
        # and this is the one region the layout was leaving empty.
        self._draw_noise_cancelling(
            screen, pygame, typography, card, pad, meter_top,
            self._meter_band_rect.height if self._meter_band_rect else 0,
        )
        y += 8

        current_gain = self._current_mic_gain()
        pct = int(round(current_gain * 100))

        # Level row: a readout, a real meter, and the two step controls. The
        # widths are distributed rather than hard-coded, and each label is fitted
        # to the box it lives in. The previous version centred the level text in
        # a fixed 300 px badge with no measurement, so it overlapped these
        # buttons, and used U+2796/U+2795, which the bundled fonts lack and
        # which rendered as a grey tofu box.
        step_w = 104
        gap = 12
        meter_w = max(120, inner_w - step_w * 2 - gap * 2)
        # The readout and the track are separate bands inside one card. Centring
        # the text across the whole card and then drawing the track near its
        # bottom edge put the track straight through the text, which the
        # screenshot review caught.
        text_band = 30
        track_h = 8
        row_h = text_band + 10 + track_h + 12

        badge_rect = pygame.Rect(card.left + pad, y, meter_w, row_h)
        self._blit_rounded_card(
            screen, badge_rect, (246, 236, 209), (255, 250, 240), pygame,
            (241, 185, 35), 2, radius=12,
        )
        badge_text = f"{text.AUDIO_LEVEL_LABEL}: {pct}%"
        badge = panel_layout.fit_single_line(
            typography, badge_text, FontRole.CONTROL, 17, (61, 44, 31), meter_w - 24
        )
        panel_layout.blit_block(
            screen, badge, pygame, badge_rect.centerx, badge_rect.top + 6,
            align="center", bounds=badge_rect,
        )

        # The meter itself: a track with a filled portion, sized from the
        # actual gain rather than implied by a number in a badge.
        track = pygame.Rect(
            badge_rect.left + 12, badge_rect.top + text_band + 8,
            badge_rect.width - 24, track_h,
        )
        pygame.draw.rect(screen, (222, 208, 178), track, border_radius=track_h // 2)
        filled_w = int(track.width * max(0.0, min(1.0, (current_gain - 1.0) / 3.0)))
        if filled_w > 0:
            pygame.draw.rect(
                screen, (241, 185, 35),
                pygame.Rect(track.left, track.top, filled_w, track.height),
                border_radius=track_h // 2,
            )
        knob_x = track.left + filled_w
        # draw.circle has no border_radius; a plain disc is what we want anyway.
        pygame.draw.circle(screen, (61, 44, 31), (knob_x, track.centery), 7)
        pygame.draw.circle(screen, (255, 250, 240), (knob_x, track.centery), 4)

        for offset, delta, label in (
            (meter_w + gap, -0.25, text.AUDIO_DECREASE),
            (meter_w + gap + step_w + gap, 0.25, text.AUDIO_INCREASE),
        ):
            btn = pygame.Rect(card.left + pad + offset, y, step_w, row_h)
            self._blit_rounded_card(
                screen, btn, (246, 236, 209), (255, 250, 240), pygame,
                (61, 44, 31), 1, radius=12,
            )
            block = panel_layout.fit_single_line(
                typography, label, FontRole.CONTROL, 17, (61, 44, 31), btn.width - 12
            )
            panel_layout.blit_block(
                screen, block, pygame, btn.centerx, btn.centery,
                align="center", bounds=btn,
            )
            self._targets.append(PanelHitTarget("mic_gain_adjust", delta, btn))
        y += row_h + 20

        presets_title = panel_layout.fit_text_block(
            typography, text.AUDIO_PRESETS_TITLE, FontRole.CONTROL, 18,
            (61, 44, 31), inner_w,
        )
        panel_layout.blit_block(screen, presets_title, pygame, card.left + pad, y)
        y += presets_title.height + 10

        values = sorted(text.AUDIO_PRESET_NAMES)
        gap_x = 10
        widths = panel_layout.even_columns(inner_w, len(values), gap_x)
        preset_h = 58
        for index, value in enumerate(values):
            p_rect = pygame.Rect(
                card.left + pad + sum(widths[:index]) + gap_x * index, y,
                widths[index], preset_h,
            )
            is_active = abs(current_gain - value) < 0.05
            self._blit_rounded_card(
                screen, p_rect, (246, 236, 209),
                (241, 185, 35) if is_active else (255, 250, 240),
                pygame, (61, 44, 31), 3 if is_active else 1, radius=14,
            )
            percent = panel_layout.fit_single_line(
                typography, f"{int(value * 100)}%", FontRole.CONTROL, 17,
                (61, 44, 31), p_rect.width - 12,
            )
            panel_layout.blit_block(
                screen, percent, pygame, p_rect.centerx, p_rect.top + 16,
                align="center", bounds=p_rect,
            )
            name = panel_layout.fit_single_line(
                typography, text.AUDIO_PRESET_NAMES[value], FontRole.BODY, 13,
                (90, 80, 70), p_rect.width - 12,
            )
            panel_layout.blit_block(
                screen, name, pygame, p_rect.centerx, p_rect.top + 36,
                align="center", bounds=p_rect,
            )
            self._targets.append(PanelHitTarget("mic_gain_set", value, p_rect))
        y += preset_h + 12

        if self._audio_message:
            message = panel_layout.fit_text_block(
                typography, self._audio_message, FontRole.BODY, 16,
                (47, 117, 81), inner_w, max_lines=2,
            )
            # Anchored to the flow, not the card bottom, so a two-line message
            # cannot ride up over the presets.
            panel_layout.blit_block(screen, message, pygame, card.left + pad, y)

    def _noise_column_width(self, inner_w: int) -> int:
        """Width of the noise cancelling column beside the meter, or 0.

        The meter's bar and the column share one row, so both must agree on where
        the split is. They did not: the bar was drawn at the full inner width and
        ran underneath the column, and its readout was clipped. That only ever
        showed up with a live input - with the microphone unavailable there is no
        bar to collide.
        """

        if inner_w < 420:
            return 0
        return int(inner_w * 0.34)

    def _draw_noise_cancelling(
        self,
        screen: Any,
        pygame: Any,
        typography: GreiaTypography,
        card: Any,
        pad: int,
        top: int,
        height: int,
    ) -> None:
        """Noise cancelling: processing on/off, and advanced reduction.

        Drawn in the column beside the live meter. The policy already existed in
        greia_platform.audio but was exposed nowhere - not the Parent API, not this
        panel - and the tab was already full-height on the 600 px reference
        screen, so this needed a home that did not push anything else out.

        Read and written through the Parent service: the settings directory is
        greiapel-owned and this panel runs as greiakid, which has read but not
        write access. That gap is why the pointer and audio controls looked
        functional and silently did nothing.
        """

        inner_w = card.width - pad * 2
        col_w = self._noise_column_width(inner_w)
        if height <= 0 or col_w < 120:
            return
        col_x = card.left + pad + inner_w - col_w
        top = top - 4

        title = panel_layout.fit_text_block(
            typography, text.AUDIO_NOISE_TITLE, FontRole.CONTROL, 15,
            (61, 44, 31), col_w, max_lines=1,
        )
        panel_layout.blit_block(screen, title, pygame, col_x, top)
        row_y = top + title.height + 4
        row_h = 30

        toggles = [
            (
                "mic_processing",
                text.AUDIO_NOISE_PROCESSING,
                self._audio_processing_enabled,
                True,
            ),
            (
                "mic_advanced",
                text.AUDIO_NOISE_ADVANCED,
                self._audio_advanced_enabled and self._audio_processing_enabled,
                self._audio_advanced_available and self._audio_processing_enabled,
            ),
        ]
        for index, (field, label, is_on, enabled) in enumerate(toggles):
            box = pygame.Rect(col_x, row_y + index * (row_h + 8), col_w, row_h)
            self._blit_rounded_card(
                screen, box, (246, 236, 209),
                (241, 185, 35) if (is_on and enabled) else (
                    (235, 228, 214) if not enabled else (255, 250, 240)
                ),
                pygame, (61, 44, 31), 3 if (is_on and enabled) else 1, radius=10,
            )
            state = "On" if (is_on and enabled) else (
                "Unavailable" if not enabled else "Off"
            )
            # One line, state right-aligned. Two stacked lines never fitted in
            # the height available beside the meter, and the second line was drawn
            # over the first.
            state_w = 96
            t1 = panel_layout.fit_single_line(
                typography, label, FontRole.BODY, 12, (61, 44, 31),
                max(40, col_w - state_w - 18),
            )
            panel_layout.blit_block(
                screen, t1, pygame, box.left + 6, box.top + 9, bounds=box
            )
            t2 = panel_layout.fit_single_line(
                typography, state, FontRole.CONTROL, 12, (61, 44, 31), state_w
            )
            # Blit_block's "right" alignment sets the block's *centre*, not its
            # right edge, so passing box.right put half the state outside the
            # button. Place it by its own measured width instead.
            state_x = box.right - 8 - t2.surface.get_width()
            panel_layout.blit_block(
                screen, t2, pygame, max(box.left + 6, state_x), box.top + 9,
                bounds=box,
            )
            if enabled:
                self._targets.append(
                    PanelHitTarget("mic_processing_toggle", field, box)
                )

    def _draw_pointer_tab(
        self,
        screen: Any,
        rect: Any,
        typography: GreiaTypography,
        pygame: Any,
    ) -> None:
        """Draw the dedicated pointer-feel tab (semantic settings only)."""
        card = pygame.Rect(rect.left, rect.top, rect.width, rect.height)
        self._blit_rounded_card(screen, card, (255, 250, 240), (246, 236, 209), pygame, radius=16)

        title = self._get_text("Pointer feel", FontRole.TITLE, 22, (61, 44, 31), typography)
        screen.blit(title, (card.left + 20, card.top + 12))
        note = self._get_text(
            "Comfort is preference — try the test area. Arrows move, Space selects, Esc closes.",
            FontRole.BODY, 14, (118, 104, 93), typography,
        )
        screen.blit(note, (card.left + 20, card.top + 40))

        settings = self._pointer_settings()
        min_touch = self._pointer_min_touch_px()
        has_touchpad = self._pointer_has_touchpad()
        has_relative = self._pointer_has_relative()
        presets = list(speed_preset_names())
        touch_preset = self._pointer_current_preset("touchpad")
        mouse_preset = self._pointer_current_preset("mouse")
        try:
            tap_on = bool(getattr(settings, "touchpad_tap", False))
            natural_on = bool(getattr(settings, "natural_scrolling", False))
            dwt_on = bool(getattr(settings, "disable_while_typing", False))
        except Exception:
            tap_on = natural_on = dwt_on = False

        focus_items = self._pointer_focus_items()
        try:
            focus = int(self._pointer_focus)
        except (TypeError, ValueError):
            focus = 0
        focus = max(0, min(len(focus_items) - 1, focus))

        left_w = int(card.width * 0.58)
        left = card.left + 16
        right = card.left + 16 + left_w + 12
        test_w = card.width - (left_w + 12 + 32)
        row_h = max(34, min(44, min_touch - 4))

        # --- Touchpad speed presets ---
        y = card.top + 62
        lbl = self._get_text("Touchpad speed", FontRole.CONTROL, 15, (61, 44, 31), typography)
        screen.blit(lbl, (left, y))
        if not has_touchpad:
            hint = self._get_text("(no touchpad detected)", FontRole.BODY, 13, (118, 104, 93), typography)
            screen.blit(hint, (left + lbl.get_width() + 8, y + 2))
        y += 20
        chip_w = max(40, (left_w - 8 * (len(presets) - 1)) // max(1, len(presets)))
        for idx, name in enumerate(presets):
            chip = pygame.Rect(left + idx * (chip_w + 8), y, chip_w, row_h)
            active = name == touch_preset and has_touchpad
            focused = focus_items[focus] == "touchpad_speed" and idx == presets.index(touch_preset)
            self._blit_rounded_card(
                screen, chip, (246, 236, 209),
                (241, 185, 35) if active else ((235, 228, 214) if not has_touchpad else (255, 250, 240)),
                pygame, (61, 44, 31), 3 if (active or focused) else 1, radius=10,
            )
            short = name.split()[0][:5]
            txt = self._get_text(short, FontRole.BODY, 13, (61, 44, 31), typography)
            screen.blit(txt, txt.get_rect(center=chip.center))
            self._targets.append(PanelHitTarget("pointer_touchpad_preset", name, chip))

        # --- Mouse speed presets ---
        y += row_h + 10
        lbl = self._get_text("Mouse speed", FontRole.CONTROL, 15, (61, 44, 31), typography)
        screen.blit(lbl, (left, y))
        if not has_relative:
            hint = self._get_text("(no mouse detected)", FontRole.BODY, 13, (118, 104, 93), typography)
            screen.blit(hint, (left + lbl.get_width() + 8, y + 2))
        y += 20
        for idx, name in enumerate(presets):
            chip = pygame.Rect(left + idx * (chip_w + 8), y, chip_w, row_h)
            active = name == mouse_preset and has_relative
            focused = focus_items[focus] == "mouse_speed" and idx == presets.index(mouse_preset)
            self._blit_rounded_card(
                screen, chip, (246, 236, 209),
                (241, 185, 35) if active else ((235, 228, 214) if not has_relative else (255, 250, 240)),
                pygame, (61, 44, 31), 3 if (active or focused) else 1, radius=10,
            )
            short = name.split()[0][:5]
            txt = self._get_text(short, FontRole.BODY, 13, (61, 44, 31), typography)
            screen.blit(txt, txt.get_rect(center=chip.center))
            self._targets.append(PanelHitTarget("pointer_mouse_preset", name, chip))

        # --- Toggles ---
        y += row_h + 10
        toggles = [
            ("touchpad_tap", "Tap to click", tap_on, has_touchpad),
            ("natural_scrolling", "Natural scroll", natural_on, True),
            ("disable_while_typing", "Calm while typing", dwt_on, has_touchpad),
        ]
        tog_w = max(60, (left_w - 2 * 8) // 3)
        tog_h = max(40, min(52, min_touch))
        for idx, (field, label, is_on, enabled) in enumerate(toggles):
            tog = pygame.Rect(left + idx * (tog_w + 8), y, tog_w, tog_h)
            focused = focus_items[focus] == field
            self._blit_rounded_card(
                screen, tog, (246, 236, 209),
                (241, 185, 35) if (is_on and enabled) else ((235, 228, 214) if not enabled else (255, 250, 240)),
                pygame, (61, 44, 31), 3 if (focused or (is_on and enabled)) else 1, radius=10,
            )
            state = "On" if (is_on and enabled) else "Off"
            t1 = self._get_text(label, FontRole.BODY, 12, (61, 44, 31), typography)
            screen.blit(t1, t1.get_rect(center=(tog.centerx, tog.top + 14)))
            t2 = self._get_text(state, FontRole.CONTROL, 13, (61, 44, 31), typography)
            screen.blit(t2, t2.get_rect(center=(tog.centerx, tog.top + 30)))
            self._targets.append(PanelHitTarget("pointer_toggle", field, tog))

        # --- Reset + message ---
        y += tog_h + 8
        reset_rect = pygame.Rect(left, y, min(220, left_w), 34)
        focused = focus_items[focus] == "reset"
        self._blit_rounded_card(
            screen, reset_rect, (246, 236, 209), (255, 250, 240),
            pygame, (61, 44, 31), 3 if focused else 1, radius=10,
        )
        lbl = self._get_text("Reset to defaults", FontRole.CONTROL, 14, (61, 44, 31), typography)
        screen.blit(lbl, lbl.get_rect(center=reset_rect.center))
        self._targets.append(PanelHitTarget("pointer_reset", None, reset_rect))
        if self._pointer_message:
            msg = self._get_text(self._pointer_message[:80], FontRole.BODY, 13, (47, 117, 81), typography)
            screen.blit(msg, (reset_rect.right + 10, reset_rect.top + 9))

        # --- Bounded test region (right column) ---
        test_top = card.top + 62
        test_h = card.bottom - test_top - 12
        test_rect = pygame.Rect(right, test_top, max(120, test_w), max(80, test_h))
        self._blit_rounded_card(screen, test_rect, (246, 236, 209), (255, 250, 240), pygame, (220, 210, 190), 1, radius=12)
        cap = self._get_text("Test area", FontRole.CONTROL, 14, (61, 44, 31), typography)
        screen.blit(cap, (test_rect.left + 10, test_rect.top + 6))
        margin = 10
        cell = max(min_touch, 56)
        positions = [
            (test_rect.left + margin, test_rect.top + 30),
            (test_rect.right - margin - cell, test_rect.top + 30),
            (test_rect.left + margin, test_rect.bottom - margin - cell),
            (test_rect.right - margin - cell, test_rect.bottom - margin - cell),
        ]
        now = time.monotonic()
        for idx, (tx, ty) in enumerate(positions):
            if tx < test_rect.left or ty < test_rect.top:
                continue
            if tx + cell > test_rect.right or ty + cell > test_rect.bottom:
                continue
            target = pygame.Rect(int(tx), int(ty), int(cell), int(cell))
            flashed = self._pointer_test_flash == idx and now - self._pointer_test_flash_at < 0.6
            focused = focus_items[focus] == f"test{idx}"
            self._blit_rounded_card(
                screen, target, (255, 250, 240),
                (47, 117, 81) if flashed else (241, 185, 35),
                pygame, (61, 44, 31), 3 if (flashed or focused) else 2, radius=12,
            )
            glyph = self._get_text("●", FontRole.CONTROL, 20, (255, 255, 255) if flashed else (61, 44, 31), typography)
            screen.blit(glyph, glyph.get_rect(center=target.center))
            self._targets.append(PanelHitTarget("pointer_test", idx, target))

    def _draw_wifi_tab(
        self,
        screen: Any,
        rect: Any,
        typography: GreiaTypography,
        pygame: Any,
        load_icon_fn: Callable[[str, int, Any], Any],
    ) -> None:
        snapshot = self.wifi_controller.snapshot
        def _body(text, color=(61, 44, 31)):
            return self._get_text(text, FontRole.BODY, 18, color, typography)
        def _bold(text, color=(61, 44, 31)):
            return self._get_text(text, FontRole.CONTROL, 18, color, typography)

        top_bar = pygame.Rect(rect.left, rect.top, rect.width, 42)
        status_text = f"Status: {snapshot.phase.value.title()}"
        if snapshot.connected_ssid:
            status_text += f" (Connected: {snapshot.connected_ssid})"
        if snapshot.error:
            status_text = f"Error: {snapshot.error}"

        status_surf = _body(status_text, (181, 46, 46) if snapshot.error else (61, 44, 31))
        screen.blit(status_surf, (top_bar.left, top_bar.top + 10))

        refresh_btn = pygame.Rect(top_bar.right - 110, top_bar.top, 100, 36)
        self._blit_rounded_card(screen, refresh_btn, (255, 250, 240), (246, 236, 209), pygame, (61, 44, 31), 1, radius=10)
        lbl_refresh = _body("Scan")
        screen.blit(lbl_refresh, lbl_refresh.get_rect(center=refresh_btn.center))
        self._targets.append(PanelHitTarget("wifi_refresh", None, refresh_btn))

        list_rect = pygame.Rect(rect.left, top_bar.bottom + 10, rect.width // 2 - 10, rect.height - 52)
        self._blit_rounded_card(screen, list_rect, (255, 250, 240), (246, 236, 209), pygame, (220, 210, 190), 1, radius=16)

        item_y = list_rect.top + 8
        for idx, network in enumerate(snapshot.networks[:6]):
            item_rect = pygame.Rect(list_rect.left + 8, item_y, list_rect.width - 16, 40)
            is_selected = idx == snapshot.selected_index
            bg = (241, 185, 35) if is_selected else (255, 250, 240)
            self._blit_rounded_card(
                screen,
                item_rect,
                (246, 236, 209),
                bg,
                pygame,
                (61, 44, 31),
                2 if is_selected else 1,
                radius=10,
            )

            label = network.ssid
            if network.security == WifiSecurity.PERSONAL:
                label += " 🔒"
            elif network.security == WifiSecurity.ENTERPRISE:
                label += " (Enterprise)"
            txt_surf = _body(label)
            screen.blit(txt_surf, (item_rect.left + 12, item_rect.top + 10))

            self._targets.append(PanelHitTarget("wifi_select", idx, item_rect))
            item_y += 46

        if not snapshot.networks:
            no_nets = _body("No networks found. Click Scan.", (118, 104, 93))
            screen.blit(no_nets, no_nets.get_rect(center=list_rect.center))

        form_rect = pygame.Rect(list_rect.right + 20, top_bar.bottom + 10, rect.width // 2 - 10, rect.height - 52)
        self._blit_rounded_card(screen, form_rect, (255, 250, 240), (246, 236, 209), pygame, radius=16)

        selected = snapshot.selected_network
        if selected is not None:
            lbl_title = _bold(f"Network: {selected.ssid}")
            screen.blit(lbl_title, (form_rect.left + 16, form_rect.top + 16))

            lbl_sec = _body(f"Security: {selected.security.value.upper()}", (118, 104, 93))
            screen.blit(lbl_sec, (form_rect.left + 16, form_rect.top + 46))

            if selected.security == WifiSecurity.PERSONAL:
                pwd_label = _body("Password:")
                screen.blit(pwd_label, (form_rect.left + 16, form_rect.top + 80))

                pwd_box = pygame.Rect(form_rect.left + 16, form_rect.top + 106, form_rect.width - 32, 44)
                self._blit_rounded_card(screen, pwd_box, (246, 236, 209), (255, 250, 240), pygame, (61, 44, 31), 1, radius=10)

                masked = "•" * len(snapshot.passphrase) or "Type password…"
                txt = _body(masked, (61, 44, 31) if snapshot.passphrase else (150, 140, 130))
                screen.blit(txt, (pwd_box.left + 12, pwd_box.top + 12))

            connect_btn = pygame.Rect(form_rect.left + 16, form_rect.bottom - 60, form_rect.width - 32, 44)
            self._blit_rounded_card(screen, connect_btn, (246, 236, 209), (241, 185, 35), pygame, (61, 44, 31), 2, radius=12)
            lbl_conn = _bold("Connect")
            screen.blit(lbl_conn, lbl_conn.get_rect(center=connect_btn.center))
            self._targets.append(PanelHitTarget("wifi_connect", None, connect_btn))
        else:
            hint = _body("Select a Wi-Fi network from the list", (118, 104, 93))
            screen.blit(hint, hint.get_rect(center=form_rect.center))

    def _draw_ssh_tab(
        self,
        screen: Any,
        rect: Any,
        typography: GreiaTypography,
        pygame: Any,
        load_icon_fn: Callable[[str, int, Any], Any],
    ) -> None:
        # Never call the service from here: status needs systemctl subprocesses
        # and froze this tab. Draw the last cached snapshot and let drain()
        # refresh it on a worker thread.
        self.request_ssh_status_refresh()
        status = self._ssh_cached_status

        card = pygame.Rect(rect.left, rect.top, rect.width, rect.height)
        self._blit_rounded_card(screen, card, (255, 250, 240), (246, 236, 209), pygame, radius=16)

        title = self._get_text("SSH Maintenance Switch", FontRole.TITLE, 22, (61, 44, 31), typography)
        screen.blit(title, (card.left + 24, card.top + 20))

        if status is None:
            waiting = self._get_text("Checking SSH status…", FontRole.BODY, 18, (118, 104, 93), typography)
            screen.blit(waiting, (card.left + 24, card.top + 70))
            return

        def _body(text, color=(61, 44, 31)):
            return self._get_text(text, FontRole.BODY, 18, color, typography)
        def _bold(text, color=(61, 44, 31)):
            return self._get_text(text, FontRole.CONTROL, 18, color, typography)

        is_on = status.active or status.enabled
        badge_rect = pygame.Rect(card.left + 24, card.top + 58, 140, 36)
        badge_bg = (47, 117, 81) if is_on else (181, 46, 46)
        self._blit_rounded_card(screen, badge_rect, (246, 236, 209), badge_bg, pygame, radius=10)
        lbl_status = _bold("ENABLED" if is_on else "DISABLED", (255, 255, 255))
        screen.blit(lbl_status, lbl_status.get_rect(center=badge_rect.center))

        toggle_btn = pygame.Rect(badge_rect.right + 20, card.top + 58, 160, 36)
        self._blit_rounded_card(screen, toggle_btn, (246, 236, 209), (241, 185, 35), pygame, (61, 44, 31), 2, radius=10)
        lbl_toggle = _bold("Turn OFF" if is_on else "Turn ON")
        screen.blit(lbl_toggle, lbl_toggle.get_rect(center=toggle_btn.center))
        self._targets.append(PanelHitTarget("ssh_toggle", None, toggle_btn))

        y = card.top + 116
        lines = [
            f"Administrative user: {status.username}",
            f"Device IP: {status.host_ip}",
            f"SSH Port: {status.port}",
            f"Connection command: ssh {status.username}@{status.host_ip}",
        ]
        for line in lines:
            line_surf = _body(line)
            screen.blit(line_surf, (card.left + 24, y))
            y += 28

        note_y = card.bottom - 48
        note = _body(
            "Note: SSH allows administrative terminal access. Keep disabled when not in use.",
            (118, 104, 93),
        )
        screen.blit(note, (card.left + 24, note_y))

    def _draw_info_tab(
        self,
        screen: Any,
        rect: Any,
        typography: GreiaTypography,
        pygame: Any,
        load_icon_fn: Callable[[str, int, Any], Any],
    ) -> None:
        # The Info tab used to resolve host_ip through the SSH service on
        # EVERY frame (two systemctl subprocesses per redraw) and made this
        # tab unusable. Only the cached snapshot is read here.
        self.request_ssh_status_refresh()
        cached_status = self._ssh_cached_status
        host_ip = cached_status.host_ip if cached_status is not None else "…"

        card = pygame.Rect(rect.left, rect.top, rect.width, rect.height)
        self._blit_rounded_card(screen, card, (255, 250, 240), (246, 236, 209), pygame, radius=16)

        title = self._get_text("Remote Parent Companion & Pairing", FontRole.TITLE, 22, (61, 44, 31), typography)
        screen.blit(title, (card.left + 24, card.top + 20))

        y = card.top + 64
        lines = [
            "Greia Parents is accessible from any browser on this home network.",
            "1. Connect your phone or laptop to the same Wi-Fi network.",
            f"2. Open http://{host_ip}:8766 in your browser.",
            "3. mDNS Service: _greia-parent._tcp (Bonjour / Avahi auto-discovery).",
            "4. Main Parent login: username 'greia', default password 'greia'.",
        ]
        for line in lines:
            surf = self._get_text(line, FontRole.BODY, 18, (61, 44, 31), typography)
            screen.blit(surf, (card.left + 24, y))
            y += 32
