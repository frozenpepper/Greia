import os
import queue
import threading
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
from greia_platform.main_credential import MainCredentialStore
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
    WIFI = "wifi"
    SSH = "ssh"
    INFO = "info"
    POINTER = "pointer"


@dataclass(frozen=True, slots=True)
class PanelHitTarget:
    action: str
    value: object
    rect: Any


class ParentSettingsOverlay:
    """On-device Parent Settings Panel for physical Greia devices.

    Accessible from the user selection screen via a protected hidden key combination.
    Provides immediate on-device access to the device language, audio & mic gain, Wi-Fi
    configuration, SSH maintenance, and remote pairing diagnostics without
    exposing a Linux shell.
    """

    def __init__(
        self,
        credential_store: MainCredentialStore,
        *,
        wifi_backend: WifiBackend | None = None,
        ssh_service: SshMaintenanceService | None = None,
        language_service: SystemLanguageService | None = None,
        hardware_store: HardwareSettingsStore | None = None,
        pointer_controller: Any | None = None,
    ) -> None:
        self.credential_store = credential_store
        try:
            self.credential_store.ensure_initialized()
        except Exception:
            pass

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

    def handle_text_input(self, text: str) -> None:
        if self.state == ParentPanelState.AUTH:
            if time.monotonic() < self.password_error_until or not text:
                return
            accepted = "".join(
                ch for ch in text if ch not in "\r\n\x00" and ch.isprintable()
            )
            if len(self.password_text) < 64:
                self.password_text += accepted[: 64 - len(self.password_text)]
        elif self.state == ParentPanelState.PANEL and self.active_tab == ParentPanelTab.WIFI:
            self.wifi_controller.append_password(text)

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

    def _set_mic_gain(self, value: float) -> None:
        if self.hardware_store is not None:
            try:
                val = max(0.5, min(4.0, round(value, 2)))
                self.hardware_store.update(mic_gain=val)
                self._cached_mic_gain = float(val)
                self._mic_gain_read_at = time.monotonic()
                self._audio_message = f"Microphone gain set to {int(val * 100)}% ({val:.2f}x Boost)."
            except Exception as exc:
                self._audio_message = f"Could not update mic gain: {exc}"

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
        try:
            if which == "touchpad":
                updated = self.hardware_store.update(touchpad_speed=speed)
            else:
                updated = self.hardware_store.update(mouse_speed=speed)
        except Exception as exc:
            self._pointer_message = f"Could not update pointer speed: {exc}"
            return
        self._cached_pointer_settings = updated
        self._pointer_settings_read_at = time.monotonic()
        label = "Touchpad" if which == "touchpad" else "Mouse"
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
        try:
            updated = self.hardware_store.update(**{field: (not current)})
        except Exception as exc:
            self._pointer_message = f"Could not update pointer setting: {exc}"
            return
        self._cached_pointer_settings = updated
        self._pointer_settings_read_at = time.monotonic()
        self._pointer_message = f"{'On' if not current else 'Off'}: {field.replace('_', ' ')}."

    def _reset_pointer_defaults(self) -> None:
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
        try:
            verified = bool(self.credential_store.verify(self.password_text))
        except Exception:
            verified = False
        if verified:
            self.state = ParentPanelState.PANEL
            self.password_text = ""
            self._sync_language_selection()
            self.wifi_controller.begin()
        else:
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

        self._targets.clear()
        width, height = screen.get_size()

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
        tabs = [
            (ParentPanelTab.LANGUAGE, "Language"),
            (ParentPanelTab.AUDIO, "Audio & Mic"),
            (ParentPanelTab.WIFI, "Wi-Fi"),
            (ParentPanelTab.SSH, "SSH"),
            (ParentPanelTab.INFO, "Remote & Pairing"),
            (ParentPanelTab.POINTER, "Pointer"),
        ]
        tab_gap = 10
        tab_w = min(145, (panel_rect.width - 48 - tab_gap * (len(tabs) - 1)) // len(tabs))
        tab_w = max(80, tab_w)
        tab_x = panel_rect.left + 24

        for tab_id, label in tabs:
            is_active = self.active_tab == tab_id
            tab_rect = pygame.Rect(tab_x, tab_y, tab_w, 38)
            bg = (241, 185, 35) if is_active else (246, 236, 209)
            self._blit_rounded_card(
                screen, tab_rect, (255, 250, 240), bg, pygame,
                (61, 44, 31), 2 if is_active else 1, radius=12,
            )

            txt = self._get_text(label, FontRole.CONTROL, 16, (61, 44, 31), typography)
            screen.blit(txt, txt.get_rect(center=tab_rect.center))
            self._targets.append(PanelHitTarget("switch_tab", tab_id, tab_rect))
            tab_x += tab_w + 10

        content_rect = pygame.Rect(
            panel_rect.left + 24,
            tab_y + 50,
            panel_rect.width - 48,
            panel_rect.bottom - (tab_y + 66),
        )

        if self.active_tab == ParentPanelTab.LANGUAGE:
            self._draw_language_tab(screen, content_rect, typography, pygame)
        elif self.active_tab == ParentPanelTab.AUDIO:
            self._draw_audio_tab(screen, content_rect, typography, pygame)
        elif self.active_tab == ParentPanelTab.WIFI:
            self._draw_wifi_tab(screen, content_rect, typography, pygame, load_icon_fn)
        elif self.active_tab == ParentPanelTab.SSH:
            self._draw_ssh_tab(screen, content_rect, typography, pygame, load_icon_fn)
        elif self.active_tab == ParentPanelTab.INFO:
            self._draw_info_tab(screen, content_rect, typography, pygame, load_icon_fn)
        elif self.active_tab == ParentPanelTab.POINTER:
            self._draw_pointer_tab(screen, content_rect, typography, pygame)

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

    def _draw_audio_tab(
        self,
        screen: Any,
        rect: Any,
        typography: GreiaTypography,
        pygame: Any,
    ) -> None:
        card = pygame.Rect(rect.left, rect.top, rect.width, rect.height)
        self._blit_rounded_card(screen, card, (255, 250, 240), (246, 236, 209), pygame, radius=16)

        title = self._get_text("Microphone Input Gain (Guadagno Microfono)", FontRole.TITLE, 22, (61, 44, 31), typography)
        screen.blit(title, (card.left + 24, card.top + 16))

        note = self._get_text(
            "Controls the microphone recording volume for puppet theater storytelling and voice activities.",
            FontRole.BODY,
            16,
            (118, 104, 93),
            typography,
        )
        screen.blit(note, (card.left + 24, card.top + 46))

        current_gain = self._current_mic_gain()
        pct = int(round(current_gain * 100))

        # Current Gain Display Badge
        badge_rect = pygame.Rect(card.left + 24, card.top + 84, 300, 48)
        self._blit_rounded_card(screen, badge_rect, (246, 236, 209), (255, 250, 240), pygame, (241, 185, 35), 2, radius=14)
        
        lbl_current = self._get_text(
            f"🎙️ Livello: {pct}% ({current_gain:.1f}x Boost)", FontRole.CONTROL, 18, (61, 44, 31), typography
        )
        screen.blit(lbl_current, lbl_current.get_rect(center=badge_rect.center))

        # Fine Adjust [-25%] and [+25%] buttons
        btn_minus = pygame.Rect(badge_rect.right + 16, card.top + 84, 95, 48)
        self._blit_rounded_card(screen, btn_minus, (246, 236, 209), (255, 250, 240), pygame, (61, 44, 31), 1, radius=14)
        lbl_m = self._get_text("➖ 25%", FontRole.CONTROL, 18, (61, 44, 31), typography)
        screen.blit(lbl_m, lbl_m.get_rect(center=btn_minus.center))
        self._targets.append(PanelHitTarget("mic_gain_adjust", -0.25, btn_minus))

        btn_plus = pygame.Rect(btn_minus.right + 12, card.top + 84, 95, 48)
        self._blit_rounded_card(screen, btn_plus, (246, 236, 209), (255, 250, 240), pygame, (61, 44, 31), 1, radius=14)
        lbl_p = self._get_text("➕ 25%", FontRole.CONTROL, 18, (61, 44, 31), typography)
        screen.blit(lbl_p, lbl_p.get_rect(center=btn_plus.center))
        self._targets.append(PanelHitTarget("mic_gain_adjust", 0.25, btn_plus))

        # Preset Quick Select Cards
        lbl_presets = self._get_text("Preset rapidi consigliati:", FontRole.CONTROL, 18, (61, 44, 31), typography)
        screen.blit(lbl_presets, (card.left + 24, card.top + 150))

        presets = [
            (1.0, "100%", "Normale (1.0x)"),
            (1.5, "150%", "Medio (1.5x)"),
            (2.0, "200%", "Alto (2.0x) ⭐"),
            (3.0, "300%", "Forte (3.0x)"),
            (4.0, "400%", "Massimo (4.0x)"),
        ]

        card_y = card.top + 182
        card_w = (card.width - 48 - (len(presets) - 1) * 10) // len(presets)
        card_h = 72

        for idx, (val, p_pct, p_desc) in enumerate(presets):
            p_rect = pygame.Rect(card.left + 24 + idx * (card_w + 10), card_y, card_w, card_h)
            is_active = abs(current_gain - val) < 0.05
            self._blit_rounded_card(
                screen,
                p_rect,
                (246, 236, 209),
                (241, 185, 35) if is_active else (255, 250, 240),
                pygame,
                (61, 44, 31),
                3 if is_active else 1,
                radius=14,
            )

            txt_p = self._get_text(p_pct, FontRole.CONTROL, 18, (61, 44, 31), typography)
            screen.blit(txt_p, txt_p.get_rect(center=(p_rect.centerx, p_rect.top + 24)))

            txt_d = self._get_text(p_desc, FontRole.BODY, 16, (90, 80, 70), typography)
            screen.blit(txt_d, txt_d.get_rect(center=(p_rect.centerx, p_rect.top + 50)))

            self._targets.append(PanelHitTarget("mic_gain_set", val, p_rect))

        if self._audio_message:
            msg = self._get_text(self._audio_message, FontRole.BODY, 16, (47, 117, 81), typography)
            screen.blit(msg, (card.left + 24, card.bottom - 26))

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
