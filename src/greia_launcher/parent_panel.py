import os
import queue
import threading
import time
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Callable

from greia_platform.hardware import HardwareSettingsStore
from greia_platform.main_credential import MainCredentialStore
from greia_platform.ssh_maintenance import SshMaintenanceService, SshStatus
from greia_platform.system_language import (
    SUPPORTED_SYSTEM_LANGUAGES,
    SystemLanguageError,
    SystemLanguageService,
)
from greia_platform.typography import FontRole, GreiaTypography
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
        self._text_surface_cache: dict[tuple[Any, ...], Any] = {}
        self._sync_language_selection()

    def open(self) -> None:
        self.state = ParentPanelState.AUTH
        self.active_tab = ParentPanelTab.LANGUAGE
        self.password_text = ""
        self.password_error_until = 0.0
        self._language_message = ""
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
        key = (text, role, size, color)
        cached = self._text_surface_cache.get(key)
        if cached is None:
            cached = typography.font(role, size).render(text, True, color)
            if len(self._text_surface_cache) > 128:
                self._text_surface_cache.clear()
            self._text_surface_cache[key] = cached
        return cached

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
    ) -> None:
        """Draw the overlay content onto `screen`.

        When the calling launcher composites the dim itself (the fast opaque
        path), pass ``draw_backdrop=False``; blending a full-screen translucent
        layer here on every redraw otherwise dominates frame time on
        Atom-class devices.
        """

        self._targets.clear()
        width, height = screen.get_size()

        if draw_backdrop:
            screen.blit(self.dim_surface((width, height), pygame), (0, 0))

        if self.state == ParentPanelState.AUTH:
            self._draw_auth_dialog(screen, theme, typography, pygame, load_icon_fn)
        elif self.state == ParentPanelState.PANEL:
            self._draw_panel(screen, theme, typography, pygame, load_icon_fn)

    def _draw_auth_dialog(
        self,
        screen: Any,
        theme: Any,
        typography: GreiaTypography,
        pygame: Any,
        load_icon_fn: Callable[[str, int, Any], Any],
    ) -> None:
        width, height = screen.get_size()
        center = (width // 2, height // 2)

        card_w = min(480, width - 40)
        card_h = min(320, height - 40)
        card = pygame.Rect(0, 0, card_w, card_h)
        card.center = center

        pygame.draw.rect(screen, (255, 250, 240), card, border_radius=24)
        pygame.draw.rect(screen, (61, 44, 31), card, width=3, border_radius=24)

        title = self._get_text("Parent Settings", FontRole.TITLE, 28, (61, 44, 31), typography)
        screen.blit(title, title.get_rect(center=(card.centerx, card.top + 36)))

        subtitle = self._get_text("Enter Parent Password", FontRole.BODY, 18, (118, 104, 93), typography)
        screen.blit(subtitle, subtitle.get_rect(center=(card.centerx, card.top + 70)))

        input_rect = pygame.Rect(card.left + 30, card.top + 106, card_w - 60, 52)
        pygame.draw.rect(screen, (246, 236, 209), input_rect, border_radius=14)
        border_col = (181, 46, 46) if time.monotonic() < self.password_error_until else (241, 185, 35)
        pygame.draw.rect(screen, border_col, input_rect, width=3, border_radius=14)

        masked = "•" * len(self.password_text) or "…"
        text_surf = self._get_text(masked, FontRole.CONTROL, 24, (61, 44, 31), typography)
        screen.blit(text_surf, text_surf.get_rect(midleft=(input_rect.left + 16, input_rect.centery)))

        btn_w = (card_w - 80) // 2
        btn_h = 48
        btn_y = card.bottom - 66

        cancel_rect = pygame.Rect(card.left + 30, btn_y, btn_w, btn_h)
        confirm_rect = pygame.Rect(card.right - 30 - btn_w, btn_y, btn_w, btn_h)

        pygame.draw.rect(screen, (230, 220, 205), cancel_rect, border_radius=14)
        lbl_cancel = self._get_text("Cancel", FontRole.BODY, 18, (61, 44, 31), typography)
        screen.blit(lbl_cancel, lbl_cancel.get_rect(center=cancel_rect.center))
        self._targets.append(PanelHitTarget("cancel_auth", None, cancel_rect))

        pygame.draw.rect(screen, (241, 185, 35), confirm_rect, border_radius=14)
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
    ) -> None:
        width, height = screen.get_size()
        panel_rect = pygame.Rect(20, 20, width - 40, height - 40)

        pygame.draw.rect(screen, (255, 250, 240), panel_rect, border_radius=24)
        pygame.draw.rect(screen, (61, 44, 31), panel_rect, width=3, border_radius=24)

        header_h = 56
        header_rect = pygame.Rect(panel_rect.left, panel_rect.top, panel_rect.width, header_h)

        font_title = typography.font(FontRole.TITLE, 24)
        title = font_title.render("Parent Settings", True, (61, 44, 31))
        screen.blit(title, (header_rect.left + 24, header_rect.top + 16))

        close_btn = pygame.Rect(header_rect.right - 50, header_rect.top + 10, 36, 36)
        pygame.draw.rect(screen, (246, 236, 209), close_btn, border_radius=10)
        pygame.draw.rect(screen, (61, 44, 31), close_btn, width=2, border_radius=10)
        icon_close = load_icon_fn("close_button", 22, pygame)
        screen.blit(icon_close, icon_close.get_rect(center=close_btn.center))
        self._targets.append(PanelHitTarget("close_panel", None, close_btn))

        tab_y = header_rect.bottom + 8
        tabs = [
            (ParentPanelTab.LANGUAGE, "Language"),
            (ParentPanelTab.AUDIO, "Audio & Mic"),
            (ParentPanelTab.WIFI, "Wi-Fi"),
            (ParentPanelTab.SSH, "SSH"),
            (ParentPanelTab.INFO, "Remote & Pairing"),
        ]
        tab_x = panel_rect.left + 24
        font_tab = typography.font(FontRole.CONTROL, 16)

        for tab_id, label in tabs:
            is_active = self.active_tab == tab_id
            tab_w = 145
            tab_rect = pygame.Rect(tab_x, tab_y, tab_w, 38)
            bg = (241, 185, 35) if is_active else (246, 236, 209)
            pygame.draw.rect(screen, bg, tab_rect, border_radius=12)
            pygame.draw.rect(screen, (61, 44, 31), tab_rect, width=2 if is_active else 1, border_radius=12)

            txt = font_tab.render(label, True, (61, 44, 31))
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

    def _draw_language_tab(
        self,
        screen: Any,
        rect: Any,
        typography: GreiaTypography,
        pygame: Any,
    ) -> None:
        font_title = typography.font(FontRole.TITLE, 22)
        font_body = typography.font(FontRole.BODY, 16)
        card = pygame.Rect(rect.left, rect.top, rect.width, rect.height)
        pygame.draw.rect(screen, (246, 236, 209), card, border_radius=16)
        title = font_title.render("Greia language", True, (61, 44, 31))
        screen.blit(title, (card.left + 20, card.top + 14))
        note = font_body.render(
            "This changes the device default. Activities use their own supported-language fallback.",
            True,
            (118, 104, 93),
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
            pygame.draw.rect(
                screen,
                (241, 185, 35) if selected else (255, 250, 240),
                cell,
                border_radius=12,
            )
            pygame.draw.rect(
                screen,
                (61, 44, 31),
                cell,
                width=3 if selected else 1,
                border_radius=12,
            )
            flag = typography.render(
                language.flag,
                FontRole.DISPLAY,
                28,
                (61, 44, 31),
            )
            screen.blit(flag, flag.get_rect(midleft=(cell.left + 10, cell.centery)))
            label = font_body.render(language.name, True, (61, 44, 31))
            screen.blit(label, label.get_rect(midleft=(cell.left + 54, cell.centery)))
            self._targets.append(PanelHitTarget("language_select", index, cell))

        if self._language_message:
            message = font_body.render(
                self._language_message,
                True,
                (181, 46, 46) if self._language_message.startswith("Could not") else (47, 117, 81),
            )
            screen.blit(message, (card.left + 20, card.bottom - 26))

    def _draw_audio_tab(
        self,
        screen: Any,
        rect: Any,
        typography: GreiaTypography,
        pygame: Any,
    ) -> None:
        font_title = typography.font(FontRole.TITLE, 22)
        font_body = typography.font(FontRole.BODY, 16)
        font_bold = typography.font(FontRole.CONTROL, 18)

        card = pygame.Rect(rect.left, rect.top, rect.width, rect.height)
        pygame.draw.rect(screen, (246, 236, 209), card, border_radius=16)

        title = font_title.render("Microphone Input Gain (Guadagno Microfono)", True, (61, 44, 31))
        screen.blit(title, (card.left + 24, card.top + 16))

        note = font_body.render(
            "Controls the microphone recording volume for puppet theater storytelling and voice activities.",
            True,
            (118, 104, 93),
        )
        screen.blit(note, (card.left + 24, card.top + 46))

        current_gain = self._current_mic_gain()
        pct = int(round(current_gain * 100))

        # Current Gain Display Badge
        badge_rect = pygame.Rect(card.left + 24, card.top + 84, 300, 48)
        pygame.draw.rect(screen, (255, 250, 240), badge_rect, border_radius=14)
        pygame.draw.rect(screen, (241, 185, 35), badge_rect, width=2, border_radius=14)
        
        lbl_current = font_bold.render(f"🎙️ Livello: {pct}% ({current_gain:.1f}x Boost)", True, (61, 44, 31))
        screen.blit(lbl_current, lbl_current.get_rect(center=badge_rect.center))

        # Fine Adjust [-25%] and [+25%] buttons
        btn_minus = pygame.Rect(badge_rect.right + 16, card.top + 84, 95, 48)
        pygame.draw.rect(screen, (255, 250, 240), btn_minus, border_radius=14)
        pygame.draw.rect(screen, (61, 44, 31), btn_minus, width=1, border_radius=14)
        lbl_m = font_bold.render("➖ 25%", True, (61, 44, 31))
        screen.blit(lbl_m, lbl_m.get_rect(center=btn_minus.center))
        self._targets.append(PanelHitTarget("mic_gain_adjust", -0.25, btn_minus))

        btn_plus = pygame.Rect(btn_minus.right + 12, card.top + 84, 95, 48)
        pygame.draw.rect(screen, (255, 250, 240), btn_plus, border_radius=14)
        pygame.draw.rect(screen, (61, 44, 31), btn_plus, width=1, border_radius=14)
        lbl_p = font_bold.render("➕ 25%", True, (61, 44, 31))
        screen.blit(lbl_p, lbl_p.get_rect(center=btn_plus.center))
        self._targets.append(PanelHitTarget("mic_gain_adjust", 0.25, btn_plus))

        # Preset Quick Select Cards
        lbl_presets = font_bold.render("Preset rapidi consigliati:", True, (61, 44, 31))
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
            pygame.draw.rect(screen, (241, 185, 35) if is_active else (255, 250, 240), p_rect, border_radius=14)
            pygame.draw.rect(screen, (61, 44, 31), p_rect, width=3 if is_active else 1, border_radius=14)

            txt_p = font_bold.render(p_pct, True, (61, 44, 31))
            screen.blit(txt_p, txt_p.get_rect(center=(p_rect.centerx, p_rect.top + 24)))

            txt_d = font_body.render(p_desc, True, (90, 80, 70))
            screen.blit(txt_d, txt_d.get_rect(center=(p_rect.centerx, p_rect.top + 50)))

            self._targets.append(PanelHitTarget("mic_gain_set", val, p_rect))

        if self._audio_message:
            msg = font_body.render(self._audio_message, True, (47, 117, 81))
            screen.blit(msg, (card.left + 24, card.bottom - 26))

    def _draw_wifi_tab(
        self,
        screen: Any,
        rect: Any,
        typography: GreiaTypography,
        pygame: Any,
        load_icon_fn: Callable[[str, int, Any], Any],
    ) -> None:
        font_body = typography.font(FontRole.BODY, 18)
        font_bold = typography.font(FontRole.CONTROL, 18)
        snapshot = self.wifi_controller.snapshot

        top_bar = pygame.Rect(rect.left, rect.top, rect.width, 42)
        status_text = f"Status: {snapshot.phase.value.title()}"
        if snapshot.connected_ssid:
            status_text += f" (Connected: {snapshot.connected_ssid})"
        if snapshot.error:
            status_text = f"Error: {snapshot.error}"

        status_surf = font_body.render(status_text, True, (181, 46, 46) if snapshot.error else (61, 44, 31))
        screen.blit(status_surf, (top_bar.left, top_bar.top + 10))

        refresh_btn = pygame.Rect(top_bar.right - 110, top_bar.top, 100, 36)
        pygame.draw.rect(screen, (246, 236, 209), refresh_btn, border_radius=10)
        pygame.draw.rect(screen, (61, 44, 31), refresh_btn, width=1, border_radius=10)
        lbl_refresh = font_body.render("Scan", True, (61, 44, 31))
        screen.blit(lbl_refresh, lbl_refresh.get_rect(center=refresh_btn.center))
        self._targets.append(PanelHitTarget("wifi_refresh", None, refresh_btn))

        list_rect = pygame.Rect(rect.left, top_bar.bottom + 10, rect.width // 2 - 10, rect.height - 52)
        pygame.draw.rect(screen, (246, 236, 209), list_rect, border_radius=16)
        pygame.draw.rect(screen, (220, 210, 190), list_rect, width=1, border_radius=16)

        item_y = list_rect.top + 8
        for idx, network in enumerate(snapshot.networks[:6]):
            item_rect = pygame.Rect(list_rect.left + 8, item_y, list_rect.width - 16, 40)
            is_selected = idx == snapshot.selected_index
            bg = (241, 185, 35) if is_selected else (255, 250, 240)
            pygame.draw.rect(screen, bg, item_rect, border_radius=10)
            pygame.draw.rect(screen, (61, 44, 31), item_rect, width=2 if is_selected else 1, border_radius=10)

            label = network.ssid
            if network.security == WifiSecurity.PERSONAL:
                label += " 🔒"
            elif network.security == WifiSecurity.ENTERPRISE:
                label += " (Enterprise)"
            txt_surf = font_body.render(label, True, (61, 44, 31))
            screen.blit(txt_surf, (item_rect.left + 12, item_rect.top + 10))

            self._targets.append(PanelHitTarget("wifi_select", idx, item_rect))
            item_y += 46

        if not snapshot.networks:
            no_nets = font_body.render("No networks found. Click Scan.", True, (118, 104, 93))
            screen.blit(no_nets, no_nets.get_rect(center=list_rect.center))

        form_rect = pygame.Rect(list_rect.right + 20, top_bar.bottom + 10, rect.width // 2 - 10, rect.height - 52)
        pygame.draw.rect(screen, (246, 236, 209), form_rect, border_radius=16)

        selected = snapshot.selected_network
        if selected is not None:
            lbl_title = font_bold.render(f"Network: {selected.ssid}", True, (61, 44, 31))
            screen.blit(lbl_title, (form_rect.left + 16, form_rect.top + 16))

            lbl_sec = font_body.render(f"Security: {selected.security.value.upper()}", True, (118, 104, 93))
            screen.blit(lbl_sec, (form_rect.left + 16, form_rect.top + 46))

            if selected.security == WifiSecurity.PERSONAL:
                pwd_label = font_body.render("Password:", True, (61, 44, 31))
                screen.blit(pwd_label, (form_rect.left + 16, form_rect.top + 80))

                pwd_box = pygame.Rect(form_rect.left + 16, form_rect.top + 106, form_rect.width - 32, 44)
                pygame.draw.rect(screen, (255, 250, 240), pwd_box, border_radius=10)
                pygame.draw.rect(screen, (61, 44, 31), pwd_box, width=1, border_radius=10)

                masked = "•" * len(snapshot.passphrase) or "Type password…"
                txt = font_body.render(masked, True, (61, 44, 31) if snapshot.passphrase else (150, 140, 130))
                screen.blit(txt, (pwd_box.left + 12, pwd_box.top + 12))

            connect_btn = pygame.Rect(form_rect.left + 16, form_rect.bottom - 60, form_rect.width - 32, 44)
            pygame.draw.rect(screen, (241, 185, 35), connect_btn, border_radius=12)
            pygame.draw.rect(screen, (61, 44, 31), connect_btn, width=2, border_radius=12)
            lbl_conn = font_bold.render("Connect", True, (61, 44, 31))
            screen.blit(lbl_conn, lbl_conn.get_rect(center=connect_btn.center))
            self._targets.append(PanelHitTarget("wifi_connect", None, connect_btn))
        else:
            hint = font_body.render("Select a Wi-Fi network from the list", True, (118, 104, 93))
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
        font_title = typography.font(FontRole.TITLE, 22)
        font_body = typography.font(FontRole.BODY, 18)

        card = pygame.Rect(rect.left, rect.top, rect.width, rect.height)
        pygame.draw.rect(screen, (246, 236, 209), card, border_radius=16)

        title = font_title.render("SSH Maintenance Switch", True, (61, 44, 31))
        screen.blit(title, (card.left + 24, card.top + 20))

        if status is None:
            waiting = font_body.render(
                "Checking SSH status…", True, (118, 104, 93)
            )
            screen.blit(waiting, (card.left + 24, card.top + 70))
            return

        font_bold = typography.font(FontRole.CONTROL, 18)

        is_on = status.active or status.enabled
        badge_rect = pygame.Rect(card.left + 24, card.top + 58, 140, 36)
        badge_bg = (47, 117, 81) if is_on else (181, 46, 46)
        pygame.draw.rect(screen, badge_bg, badge_rect, border_radius=10)
        lbl_status = font_bold.render("ENABLED" if is_on else "DISABLED", True, (255, 255, 255))
        screen.blit(lbl_status, lbl_status.get_rect(center=badge_rect.center))

        toggle_btn = pygame.Rect(badge_rect.right + 20, card.top + 58, 160, 36)
        pygame.draw.rect(screen, (241, 185, 35), toggle_btn, border_radius=10)
        pygame.draw.rect(screen, (61, 44, 31), toggle_btn, width=2, border_radius=10)
        lbl_toggle = font_bold.render("Turn OFF" if is_on else "Turn ON", True, (61, 44, 31))
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
            line_surf = font_body.render(line, True, (61, 44, 31))
            screen.blit(line_surf, (card.left + 24, y))
            y += 28

        note_y = card.bottom - 48
        note = font_body.render(
            "Note: SSH allows administrative terminal access. Keep disabled when not in use.",
            True,
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
        font_title = typography.font(FontRole.TITLE, 22)
        font_body = typography.font(FontRole.BODY, 18)

        # The Info tab used to resolve host_ip through the SSH service on
        # EVERY frame (two systemctl subprocesses per redraw) and made this
        # tab unusable. Only the cached snapshot is read here.
        self.request_ssh_status_refresh()
        cached_status = self._ssh_cached_status
        host_ip = cached_status.host_ip if cached_status is not None else "…"

        card = pygame.Rect(rect.left, rect.top, rect.width, rect.height)
        pygame.draw.rect(screen, (246, 236, 209), card, border_radius=16)

        title = font_title.render("Remote Parent Companion & Pairing", True, (61, 44, 31))
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
            surf = font_body.render(line, True, (61, 44, 31))
            screen.blit(surf, (card.left + 24, y))
            y += 32
