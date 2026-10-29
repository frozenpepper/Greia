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
from greia_platform.hardware import HardwareSettings, HardwareSettingsStore
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
from greia_launcher.panel_localization import panel_message, panel_constant, panel_audio_preset
from greia_launcher.parent_credential_client import (
    ChildAccount,
    ParentCredentialClient,
    ParentCredentialUnavailable,
    ParentPasswordRejected,
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

#: Shown when the service refused because the attempt budget is spent. It
#: answered, so this is not an outage, but "incorrect password" would invite the
#: parent to keep guessing into the limit.
_PASSWORD_RATE_LIMITED = "Too many attempts"


class _Ink:
    """Colour tokens for the panel.

    These are the shared control kit's tokens (ADR 0037,
    ``greia_platform.activity_controls``: ink contour, cocoa text, cream face,
    sunshine accent), so the adult panel reads as the same product as the Shell.
    They are restated rather than imported to keep the kit's pygame-bound
    module out of the launcher's start-up import path.
    """

    CONTOUR = (75, 55, 47)
    TEXT = (61, 44, 31)
    MUTED = (118, 104, 93)
    FAINT = (150, 138, 126)
    PANEL = (255, 250, 240)
    CARD = (247, 238, 216)
    FACE = (255, 249, 236)
    ACCENT = (255, 194, 52)
    TRACK = (222, 208, 178)
    DISABLED = (222, 214, 201)
    DANGER = (181, 46, 46)
    SUCCESS = (47, 117, 81)
    WHITE = (255, 255, 255)


def _mix(color: tuple[int, int, int], other: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
    """Linear blend, the kit's ``mix`` (GREIA_SVG_AUTHORING_RULES derived steps)."""

    amount = max(0.0, min(1.0, float(amount)))
    return tuple(  # type: ignore[return-value]
        int(round(a * (1.0 - amount) + b * amount)) for a, b in zip(color, other)
    )


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
        self._device_locale = "en"
        self._language_message = ""
        self._language_message_is_error = False
        self._audio_message = ""
        self._audio_message_is_error = False
        # Focus rings appear only after keyboard/controller input and hide again
        # on pointer use ("focus-visible", as in the control kit).
        self._keyboard_focus_visible = False
        self._accounts_page = 0
        self._profile_policy_cache: Any = None
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
        self._chip_cache: BoundedCache[tuple[Any, ...], Any] = BoundedCache(192)
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
        self._mic_quiet = False
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
        self._pointer_message_is_error = False
        self._pointer_focus = 0
        self._audio_processing_enabled = True
        self._audio_advanced_enabled = False
        self._audio_advanced_available = False
        self._audio_settings_loaded = False
        self._pointer_test_flash: int | None = None
        self._pointer_test_flash_at = 0.0

    # --- shared panel controls ---------------------------------------------
    #
    # Every control in the panel is drawn by the helpers below, so the whole
    # surface uses one vocabulary: kit-style bodies (one ink contour, cream or
    # accent face, a darker tactile lip) as in ADR 0037, one spacing grid and one
    # set of text sizes. Bodies are opaque chips with the backdrop baked into
    # their corners, cached in ``_chip_cache``; the composite frame cache means
    # they are only blitted when the frame actually changes.

    #: Height of the header row that holds the title and the close control.
    _HEADER_H = 54

    @staticmethod
    def _panel_rect(size: tuple[int, int]) -> Any:
        """The main panel card. Tighter margins on short screens (800x480)."""

        import pygame

        margin = 20 if size[1] >= 560 else 12
        return pygame.Rect(margin, margin, size[0] - 2 * margin, size[1] - 2 * margin)

    @classmethod
    def _panel_close_button_rect(cls, size: tuple[int, int]) -> Any:
        import pygame

        panel = cls._panel_rect(size)
        rect = pygame.Rect(0, 0, 42, 42)
        rect.center = (panel.right - 14 - 21, panel.top + cls._HEADER_H // 2 + 2)
        return rect

    def auth_card_rect(self, size: tuple[int, int]) -> Any:
        """Return the centered Parent-password card rectangle."""

        import pygame

        width, height = size
        card_w = min(460, width - 32)
        card_h = min(288, height - 32)
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
        lip: int = 0,
    ) -> Any:
        """Return a cached opaque rounded chip matching `size`.

        The chip bakes `backdrop` into its corners so blitting it over the
        surface it was cut for is pixel-identical to drawing the rounded rect
        in place, without per-frame software corner geometry. ``lip`` adds the
        control kit's tactile bottom band: the face sits ``lip`` pixels above a
        darker shade of its own fill, all inside one ink contour.
        """

        key = (size, radius, backdrop, fill, outline, width, lip)
        cached = self._chip_cache.get(key)
        if cached is not None:
            return cached
        chip = pygame.Surface(size).convert()
        chip.fill(backdrop)
        rect = chip.get_rect()
        if lip > 0 and outline is not None and width > 0:
            pygame.draw.rect(chip, outline, rect, border_radius=radius)
            pygame.draw.rect(
                chip, _mix(fill, _Ink.CONTOUR, 0.34),
                rect.inflate(-2 * width, -2 * width),
                border_radius=max(1, radius - width),
            )
            face = pygame.Rect(0, 0, rect.width, rect.height - lip)
            pygame.draw.rect(chip, outline, face, border_radius=radius)
            pygame.draw.rect(
                chip, fill, face.inflate(-2 * width, -2 * width),
                border_radius=max(1, radius - width),
            )
        else:
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
        lip: int = 0,
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
            lip,
        )
        screen.blit(chip, rect.topleft)

    @staticmethod
    def _blit_centered(screen: Any, block: Any, rect: Any) -> Any:
        """Blit a measured text block centred (both axes) inside ``rect``.

        ``panel_layout.blit_block(..., align="center")`` centres horizontally
        only and takes ``y`` as the *top*. Passing a rect's ``centery`` there is
        what put every button and tab label in the lower half of its control.
        """

        target = block.surface.get_rect(center=rect.center)
        target.clamp_ip(rect)
        screen.blit(block.surface, target)
        return target

    def _kit_button(
        self,
        screen: Any,
        rect: Any,
        label: str,
        typography: GreiaTypography,
        pygame: Any,
        *,
        backdrop: tuple[int, int, int] = _Ink.CARD,
        role: str = "neutral",
        shape: str = "pill",
        selected: bool = False,
        disabled: bool = False,
        focused: bool = False,
        size: int = 16,
        sublabel: str | None = None,
        align: str = "center",
    ) -> Any:
        """Draw one kit-style control and return its face rectangle.

        ``role`` is ``neutral`` (cream), ``primary`` (accent), ``danger`` (red,
        white label) or ``danger_text`` (cream, red label). ``selected`` gives an
        exclusive option the accent fill. ``shape`` is ``pill`` for actions and
        ``tile`` for options. The focus ring is drawn only when ``focused``.
        """

        if role == "danger":
            base, ink = _Ink.DANGER, _Ink.WHITE
        elif role == "primary" or selected:
            base, ink = _Ink.ACCENT, _Ink.TEXT
        elif role == "danger_text":
            base, ink = _Ink.FACE, _Ink.DANGER
        else:
            base, ink = _Ink.FACE, _Ink.TEXT
        lip = 0 if disabled or rect.height < 30 else 3
        if disabled:
            base = _mix(base, _Ink.DISABLED, 0.62)
            ink = _mix(_Ink.TEXT, _Ink.DISABLED, 0.55)
        face = pygame.Rect(rect.left, rect.top, rect.width, rect.height - lip)
        radius = (min(face.height, rect.width) // 2) if shape == "pill" else 12
        self._blit_rounded_card(
            screen, rect, backdrop, base, pygame, _Ink.CONTOUR,
            3 if selected else 2, radius=radius, lip=lip,
        )
        if label:
            text_w = max(1, face.width - (28 if align == "left" else 16))
            block = panel_layout.fit_single_line(
                typography, label, FontRole.CONTROL, size, ink, text_w, min_size=11
            )
            if sublabel:
                sub = panel_layout.fit_single_line(
                    typography, sublabel, FontRole.BODY, 14, _mix(ink, base, 0.25),
                    text_w, min_size=10,
                )
                total = block.height + sub.height
                top = face.centery - total // 2
                screen.blit(block.surface, block.surface.get_rect(midtop=(face.centerx, top)))
                screen.blit(
                    sub.surface,
                    sub.surface.get_rect(midtop=(face.centerx, top + block.height)),
                )
            elif align == "left":
                screen.blit(
                    block.surface,
                    block.surface.get_rect(midleft=(face.left + 14, face.centery)),
                )
            else:
                self._blit_centered(screen, block, face)
        if focused:
            self._kit_focus_ring(screen, rect, radius, pygame)
        return face

    @staticmethod
    def _kit_focus_ring(screen: Any, rect: Any, radius: int, pygame: Any) -> None:
        """Keyboard/controller focus: accent band inside an ink band (ADR 0037)."""

        pygame.draw.rect(
            screen, _Ink.ACCENT, rect.inflate(8, 8), width=3, border_radius=radius + 4
        )
        pygame.draw.rect(
            screen, _Ink.CONTOUR, rect.inflate(13, 13), width=2, border_radius=radius + 6
        )

    def _kit_switch(
        self,
        screen: Any,
        rect: Any,
        on: bool,
        enabled: bool,
        backdrop: tuple[int, int, int],
        pygame: Any,
    ) -> None:
        """A drawn on/off switch: the state is a shape, not a word to read."""

        fill = _Ink.ACCENT if (on and enabled) else (_Ink.TRACK if enabled else _Ink.DISABLED)
        self._blit_rounded_card(
            screen, rect, backdrop, fill, pygame, _Ink.CONTOUR, 2, radius=rect.height // 2
        )
        knob_r = rect.height // 2 - 4
        cx = rect.right - rect.height // 2 if on else rect.left + rect.height // 2
        knob_fill = _Ink.WHITE if enabled else _Ink.FACE
        pygame.draw.circle(screen, _Ink.CONTOUR, (cx, rect.centery), knob_r + 1)
        pygame.draw.circle(screen, knob_fill, (cx, rect.centery), knob_r - 1)

    def _kit_toggle(
        self,
        screen: Any,
        rect: Any,
        label: str,
        on: bool,
        enabled: bool,
        typography: GreiaTypography,
        pygame: Any,
        *,
        focused: bool = False,
        note: str | None = None,
        stacked: bool = False,
        backdrop: tuple[int, int, int] = _Ink.CARD,
    ) -> None:
        """A labelled tile carrying a switch. ``stacked`` puts the switch below."""

        lip = 3 if enabled else 0
        tile_fill = _Ink.FACE if enabled else _mix(_Ink.FACE, _Ink.DISABLED, 0.62)
        self._blit_rounded_card(
            screen, rect, backdrop, tile_fill, pygame, _Ink.CONTOUR, 2, radius=12, lip=lip
        )
        face = pygame.Rect(rect.left, rect.top, rect.width, rect.height - lip)
        ink = _Ink.TEXT if enabled else _mix(_Ink.TEXT, _Ink.DISABLED, 0.55)
        switch = pygame.Rect(0, 0, 42, 24)
        if stacked:
            switch.midbottom = (face.centerx, face.bottom - 7)
            text_w = max(1, face.width - 12)
            block = panel_layout.fit_text_block(
                typography, label, FontRole.BODY, 14, ink, text_w, max_lines=2,
            )
            area = pygame.Rect(face.left + 6, face.top + 4, face.width - 12, switch.top - face.top - 6)
            screen.blit(block.surface, block.surface.get_rect(center=area.center))
        else:
            switch.midright = (face.right - 12, face.centery)
            text_w = max(1, switch.left - face.left - 22)
            block = panel_layout.fit_text_block(
                typography, label, FontRole.BODY, 15, ink, text_w, max_lines=2,
            )
            if note:
                sub = panel_layout.fit_single_line(
                    typography, note, FontRole.BODY, 13, _Ink.MUTED, text_w, min_size=10
                )
                top = face.centery - (block.height + sub.height) // 2
                screen.blit(block.surface, (face.left + 12, top))
                screen.blit(sub.surface, (face.left + 12, top + block.height))
            else:
                screen.blit(
                    block.surface,
                    block.surface.get_rect(midleft=(face.left + 12, face.centery)),
                )
        self._kit_switch(screen, switch, on, enabled, tile_fill, pygame)
        if focused:
            self._kit_focus_ring(screen, rect, 12, pygame)

    def _content_card(self, screen: Any, rect: Any, pygame: Any) -> int:
        """Paint a tab's content card and return its inner padding."""

        self._blit_rounded_card(screen, rect, _Ink.PANEL, _Ink.CARD, pygame, radius=16)
        return 20 if rect.width >= 600 else 16

    def open(self) -> None:
        self.state = ParentPanelState.AUTH
        self.active_tab = ParentPanelTab.LANGUAGE
        self.password_text = ""
        self.password_error_until = 0.0
        self._password_problem = None
        self._language_message = ""
        self._pointer_message = ""
        self._pointer_message_is_error = False
        self._audio_message = ""
        self._audio_message_is_error = False
        self._pointer_focus = 0
        self._pointer_test_flash = None
        self._keyboard_focus_visible = False
        self._text_field = None
        self._accounts_mode = "list"
        self._accounts_page = 0
        self._sync_language_selection()
        self._targets.clear()
        self.wifi_controller.begin()
        self.request_ssh_status_refresh(force=True)

    def close(self) -> None:
        self.state = ParentPanelState.CLOSED
        self.password_text = ""
        # Typed secrets and the unlocked session do not outlive the panel: the
        # next open asks for the password again anyway.
        self._security_current = ""
        self._security_new = ""
        self._security_confirm = ""
        self._security_message = None
        self._session = None
        self._text_field = None
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
            self._keyboard_focus_visible = True
            if key == pygame.K_ESCAPE:
                # Back one level first (an open form or confirmation), then close.
                if self._back_one_level():
                    return True
                self.close()
                return False
            if key == pygame.K_TAB:
                # Tab walks a form's fields, then carries on to the next section,
                # so it can never trap the keyboard inside a form.
                fields = self._form_fields()
                if self._text_field in fields and self._text_field != fields[-1]:
                    self._move_text_field(1)
                    return True
                self.step_section(1)
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

            if self.active_tab in {ParentPanelTab.ACCOUNTS, ParentPanelTab.SECURITY}:
                self._form_handle_key(key, pygame)
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
                if key in {pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE}:
                    self._toggle_ssh()

            return True

        return False

    @property
    def accepts_typed_text_only(self) -> bool:
        """True while the password prompt is up: text entry stays keyboard-owned."""

        return self.state == ParentPanelState.AUTH

    def step_section(self, delta: int) -> bool:
        """Move to the previous (``-1``) or next (``+1``) section, wrapping.

        One implementation for Tab and for the controller shoulder buttons, so
        the two can never disagree about section order. Only meaningful once
        the panel is unlocked; returns whether a section change was made.
        """

        if self.state != ParentPanelState.PANEL or delta == 0:
            return False
        self._keyboard_focus_visible = True
        order = [ParentPanelTab(value) for _, value in text.TABS]
        idx = (order.index(self.active_tab) + (1 if delta > 0 else -1)) % len(order)
        self._select_tab(order[idx])
        return True

    # Text fields of each form, in keyboard order.
    _FORM_FIELDS = {
        "add": ("account_name", "account_age"),
        "security": ("security_current", "security_new", "security_confirm"),
    }

    def _form_fields(self) -> tuple[str, ...]:
        if self.active_tab == ParentPanelTab.SECURITY:
            return self._FORM_FIELDS["security"]
        if self.active_tab == ParentPanelTab.ACCOUNTS and self._accounts_mode == "add":
            return self._FORM_FIELDS["add"]
        return ()

    def _move_text_field(self, step: int) -> None:
        fields = self._form_fields()
        if not fields:
            return
        if self._text_field in fields:
            index = (fields.index(self._text_field) + step) % len(fields)
        else:
            index = 0 if step > 0 else len(fields) - 1
        self._text_field = fields[index]

    def _form_handle_key(self, key: int, pygame: Any) -> None:
        """Keyboard editing for the account form and the password form.

        These forms took typed characters but had no Backspace, no way to move
        between fields and no Enter, so a typo could only be fixed by closing
        the panel. Up/Down move between fields, Enter submits.
        """

        fields = self._form_fields()
        if key == pygame.K_BACKSPACE:
            if self._text_field in fields:
                self._set_field_value(
                    self._text_field, self._field_value(self._text_field)[:-1]
                )
            return
        if key in {pygame.K_DOWN, pygame.K_UP} and fields:
            self._move_text_field(1 if key == pygame.K_DOWN else -1)
            return
        if key not in {pygame.K_RETURN, pygame.K_KP_ENTER}:
            return
        if self.active_tab == ParentPanelTab.SECURITY:
            self._change_password()
        elif self._accounts_mode == "add":
            if self._renaming is not None:
                self._save_rename()
            else:
                self._create_account()
        elif self._accounts_mode == "confirm":
            # Enter on a destructive confirmation does nothing: removing a
            # child's data needs the explicit red button, never a stray key.
            return
        elif len(self._accounts) < self._max_profiles():
            self._open_account_form()

    def _open_account_form(self) -> None:
        self._accounts_mode = "add"
        self._renaming = None
        self._account_name = ""
        self._account_age = ""
        self._text_field = "account_name"
        self._set_accounts_message(None)

    def _back_one_level(self) -> bool:
        """Leave an open sub-screen. Returns False when there is none."""

        if self.active_tab == ParentPanelTab.ACCOUNTS and self._accounts_mode != "list":
            self._accounts_mode = "list"
            self._pending_remove = None
            self._renaming = None
            self._text_field = None
            self._set_accounts_message(None)
            return True
        return False

    def _select_tab(self, tab: ParentPanelTab) -> None:
        """Switch section without carrying a focused field into it.

        A field focused on one tab used to stay focused after switching, so
        typing on the accounts list went into a password field on another tab.
        """

        self.active_tab = tab
        if tab == ParentPanelTab.SECURITY:
            self._text_field = "security_current"
        elif tab == ParentPanelTab.ACCOUNTS and self._accounts_mode == "add":
            self._text_field = "account_name"
        else:
            self._text_field = None

    def handle_click(self, pos: tuple[int, int], pygame: Any = None) -> bool:
        """Handle click input. Returns True if handled, False if overlay closed."""
        self._keyboard_focus_visible = False
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
                        self._select_tab(target.value)
                    elif isinstance(target.value, str):
                        val = str(target.value)
                        for tab in ParentPanelTab:
                            if tab.value == val or tab.name.lower() == val.lower() or str(tab) == val:
                                self._select_tab(tab)
                                break
                    return True
                elif target.action == "language_page":
                    self._language_index = int(target.value)
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
                    self._open_account_form()
                    return True
                elif target.action == "account_page":
                    self._accounts_page = max(0, self._accounts_page + int(target.value))
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
            self._audio_message = self._ui_message("audio.processing.unavailable")
            self._audio_message_is_error = True
            return
        client, session = self._parent_client(), self._session
        if client is None or session is None:
            self._audio_message = self._copy("STATUS_OFFLINE")
            self._audio_message_is_error = True
            return
        try:
            client.set_microphone_processing(
                session, enabled=enabled, advanced=advanced
            )
        except Exception as exc:
            self._audio_message = self._ui_message("audio.processing.failed", detail=str(exc))
            self._audio_message_is_error = True
            return
        self._audio_message_is_error = False
        self._audio_processing_enabled = enabled
        self._audio_advanced_enabled = advanced
        mode_key = (
            "audio.mode.off" if not enabled else
            "audio.mode.advanced" if advanced else "audio.mode.lightweight"
        )
        self._audio_message = self._ui_message(
            "audio.processing.changed", mode=self._ui_message(mode_key)
        )

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
            self._audio_message = self._pointer_message
            self._audio_message_is_error = False
        else:
            self._audio_message = self._pointer_message
            self._audio_message_is_error = True

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
            self._pointer_message = self._ui_message("pointer.disabled.touchpad")
            self._pointer_message_is_error = True
            return
        if which == "mouse" and not self._pointer_has_relative():
            self._pointer_message = self._ui_message("pointer.disabled.mouse")
            self._pointer_message_is_error = True
            return
        if self.hardware_store is None:
            return
        try:
            speed = float(preset_to_speed(name))
        except (KeyError, TypeError, ValueError):
            return
        label = self._ui_message(
            "pointer.device.touchpad" if which == "touchpad" else "pointer.device.mouse"
        )
        field = "touchpad_speed" if which == "touchpad" else "mouse_speed"
        message = self._ui_message(
            "pointer.speed.changed", device=label,
            name=self._ui_message(f"pointer.preset.{name}"),
        )
        # Only the actual API result may report success. The old code
        # overwrote failed writes with a cheerful false confirmation.
        self._apply_hardware_change({field: speed}, message)

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
            self._pointer_message = self._copy("STATUS_OFFLINE")
            self._pointer_message_is_error = True
            return False
        try:
            updated = client.update_hardware_settings(session, changes)
        except Exception as exc:
            self._pointer_message = self._ui_message("pointer.change.failed", detail=str(exc))
            self._pointer_message_is_error = True
            return False
        self._adopt_service_settings(updated)
        self._pointer_message = success
        self._pointer_message_is_error = False
        return True

    def _adopt_service_settings(self, payload: Any) -> None:
        """Cache the settings the Parent service confirmed.

        The service answers a write with the flat settings object. Anything the
        panel cannot read back as typed settings is dropped so the next read
        re-fetches them, instead of caching a shape the draw code cannot use.
        """

        settings: HardwareSettings | None = None
        if isinstance(payload, HardwareSettings):
            settings = payload
        elif isinstance(payload, dict):
            nested = payload.get("desired")
            source = nested if isinstance(nested, dict) else payload
            try:
                settings = HardwareSettings(
                    **{
                        name: source[name]
                        for name in HardwareSettings.__slots__
                        if name in source
                    }
                )
            except (TypeError, ValueError):
                settings = None
        self._cached_pointer_settings = settings
        self._pointer_settings_read_at = time.monotonic() if settings is not None else 0.0

    def _toggle_pointer_setting(self, field: str) -> None:
        if field not in self._POINTER_TOGGLE_FIELDS:
            return
        if field in ("touchpad_tap", "disable_while_typing") and not self._pointer_has_touchpad():
            self._pointer_message = self._ui_message("pointer.disabled.toggle")
            self._pointer_message_is_error = True
            return
        if self.hardware_store is None:
            return
        settings = self._pointer_settings()
        try:
            current = bool(getattr(settings, field, False))
        except Exception:
            current = False
        labels = {
            "touchpad_tap": "pointer.toggle.tap",
            "natural_scrolling": "pointer.toggle.scroll",
            "disable_while_typing": "pointer.toggle.typing",
        }
        message = self._ui_message(
            "pointer.toggle.changed",
            state=self._ui_message("state.on" if not current else "state.off"),
            setting=self._ui_message(labels[field]),
        )
        self._apply_hardware_change({field: (not current)}, message)

    def _reset_pointer_defaults(self) -> None:
        client, session = self._parent_client(), self._session
        if client is not None and session is not None:
            try:
                updated = client.reset_hardware_settings(session)
            except Exception as exc:
                self._pointer_message = self._ui_message("pointer.reset.failed", detail=str(exc))
                self._pointer_message_is_error = True
                return
            self._adopt_service_settings(updated)
            self._pointer_focus = 0
            self._pointer_message = self._ui_message("pointer.reset.done")
            self._pointer_message_is_error = False
            return
        if self.hardware_store is None:
            return
        try:
            updated = self.hardware_store.reset()
        except Exception as exc:
            self._pointer_message = self._ui_message("pointer.reset.failed", detail=str(exc))
            self._pointer_message_is_error = True
            return
        self._cached_pointer_settings = updated
        self._pointer_settings_read_at = time.monotonic()
        self._pointer_focus = 0
        self._pointer_message = self._ui_message("pointer.reset.done")
        self._pointer_message_is_error = False

    def _flash_pointer_test_target(self, index: int) -> None:
        try:
            index = int(index)
        except (TypeError, ValueError):
            return
        if 0 <= index < self._POINTER_TEST_TARGETS:
            self._pointer_test_flash = index
            self._pointer_test_flash_at = time.monotonic()
            self._pointer_message = self._ui_message("pointer.test.done")
            self._pointer_message_is_error = False

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
        except ParentPasswordRejected as rejection:
            # A definite "no" from the service: wrong password, or the attempt
            # budget is spent. Never an outage message.
            verified = False
            self._session = None
            self._password_problem = (
                _PASSWORD_RATE_LIMITED if rejection.rate_limited else None
            )
            self.password_text = ""
            self.password_error_until = time.monotonic() + 1.2
            return
        except ParentCredentialUnavailable:
            # The check could not be performed. Say so. Reporting this as an
            # incorrect password is what cost a full diagnosis cycle: an
            # unreadable credential looked exactly like a typing mistake.
            self._password_problem = _PASSWORD_CHECK_FAILED
            self.password_text = ""
            self.password_error_until = time.monotonic() + 5.0
            return
        except Exception:
            self._password_problem = _PASSWORD_CHECK_FAILED
            self.password_text = ""
            self.password_error_until = time.monotonic() + 5.0
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
        # Parent/device locale is not the currently active child's override.
        # The setting comes from the same service that owns the picker.
        self._device_locale = current

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
            self._device_locale = saved.locale
            self._language_message_is_error = False
            self._language_message = self._ui_message(
                "language.changed",
                name=SUPPORTED_SYSTEM_LANGUAGES[self._language_index].native_name,
            )
        except (SystemLanguageError, OSError, IndexError) as exc:
            self._language_message_is_error = True
            self._language_message = self._ui_message("language.failed", detail=str(exc))

    def _ui_message(self, key: str, **variables: str) -> str:
        return panel_message(key, self._device_locale, **variables)

    def _copy(self, name: str, **variables: str) -> str:
        """Resolve named Parent forms without translating arbitrary field data."""
        return panel_constant(name, self._device_locale, **variables)

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
        "_device_locale",
        "_language_message",
        "_language_message_is_error",
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
        "_cached_pointer_settings",
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
        "_audio_message_is_error",
        "_pointer_message_is_error",
        "_keyboard_focus_visible",
        "_accounts_page",
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
                    # Length only: the mask shows how many characters were
                    # typed, and the secret itself must not live in a cache key.
                    # Without it typing a Wi-Fi password never updated the dots.
                    len(str(getattr(snapshot, "passphrase", "") or "")),
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
        key = (base_key, self.state, size, self._device_locale)
        if (
            self._panel_base is not None
            and self._panel_base_key == key
            and self._panel_base.get_size() == size
        ):
            return

        base = base_surface.copy()
        if self.state == ParentPanelState.AUTH:
            self._paint_auth_chrome(base, size, pygame)
        else:
            self._paint_panel_chrome(base, size, typography, pygame, load_icon_fn)
        self._panel_base = base.convert()
        self._panel_base_key = key

    def _paint_auth_chrome(self, surface: Any, size: tuple[int, int], pygame: Any) -> None:
        card = self.auth_card_rect(size)
        pygame.draw.rect(surface, _Ink.PANEL, card, border_radius=24)
        pygame.draw.rect(surface, _Ink.CONTOUR, card, width=3, border_radius=24)

    def _paint_panel_chrome(
        self,
        surface: Any,
        size: tuple[int, int],
        typography: GreiaTypography,
        pygame: Any,
        load_icon_fn: Callable[[str, int, Any], Any],
    ) -> None:
        """Static panel identity: card, title, key hint, close control, divider.

        One painter for both the composed-base path the Shell uses and the
        standalone path, so the two can no longer drift apart (they did: the
        close button was drawn at one place and hit-tested at another).
        """

        panel = self._panel_rect(size)
        pygame.draw.rect(surface, _Ink.PANEL, panel, border_radius=24)
        pygame.draw.rect(surface, _Ink.CONTOUR, panel, width=3, border_radius=24)
        header_mid = panel.top + self._HEADER_H // 2 + 2
        close = self._panel_close_button_rect(size)
        title = panel_layout.fit_single_line(
            typography, self._ui_message("parent.title"), FontRole.TITLE, 24,
            _Ink.TEXT, max(1, (close.left - panel.left) // 2), min_size=16,
        )
        surface.blit(title.surface, title.surface.get_rect(midleft=(panel.left + 22, header_mid)))
        hint_left = panel.left + 22 + title.width + 24
        hint_w = close.left - 16 - hint_left
        if hint_w > 80:
            hint = panel_layout.fit_single_line(
                typography, self._ui_message("panel.hint"), FontRole.BODY, 14,
                _Ink.MUTED, hint_w, min_size=14,
            )
            if hint.fits:
                surface.blit(
                    hint.surface,
                    hint.surface.get_rect(midright=(close.left - 16, header_mid)),
                )
        chip = self._rounded_card(
            close.size, close.width // 2, _Ink.PANEL, _Ink.FACE, _Ink.CONTOUR, 2, pygame, 3
        )
        surface.blit(chip, close.topleft)
        icon = load_icon_fn("close_button", 20, pygame)
        face = pygame.Rect(close.left, close.top, close.width, close.height - 3)
        surface.blit(icon, icon.get_rect(center=face.center))
        divider_y = panel.top + self._HEADER_H + 2
        pygame.draw.line(
            surface, _Ink.TRACK, (panel.left + 20, divider_y), (panel.right - 20, divider_y), 2
        )

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
        card = self.auth_card_rect((width, height))
        if not chrome_in_base:
            self._paint_auth_chrome(screen, (width, height), pygame)
        pad = 26
        inner_w = max(1, card.width - pad * 2)
        y = card.top + 22

        title = panel_layout.fit_single_line(
            typography, self._ui_message("parent.title"),
            FontRole.TITLE, 26, _Ink.TEXT, inner_w, min_size=16,
        )
        screen.blit(title.surface, title.surface.get_rect(midtop=(card.centerx, y)))
        y += title.height + 2
        subtitle = panel_layout.fit_single_line(
            typography, self._ui_message("auth.prompt"),
            FontRole.BODY, 17, _Ink.MUTED, inner_w, min_size=12,
        )
        screen.blit(subtitle.surface, subtitle.surface.get_rect(midtop=(card.centerx, y)))
        y += subtitle.height + 14

        failing = time.monotonic() < self.password_error_until
        input_rect = pygame.Rect(card.left + pad, y, inner_w, 52)
        self._blit_rounded_card(
            screen, input_rect, _Ink.PANEL, _Ink.FACE, pygame,
            _Ink.DANGER if failing else _Ink.ACCENT, 3, radius=14,
        )
        masked = self._masked_password(max(3, (input_rect.width - 40) // 14))
        caret_x = input_rect.left + 18
        if masked:
            text_surf = self._get_text(masked, FontRole.CONTROL, 24, _Ink.TEXT, typography)
            text_rect = text_surf.get_rect(midleft=(input_rect.left + 18, input_rect.centery))
            screen.blit(text_surf, text_rect)
            caret_x = text_rect.right + 4
        if not failing:
            # A static caret says "type here" without animating the frame.
            pygame.draw.line(
                screen, _Ink.TEXT,
                (caret_x, input_rect.centery - 12), (caret_x, input_rect.centery + 12), 2,
            )
        y = input_rect.bottom + 8

        # The reason line always reserves its height, so an error does not make
        # the buttons jump under the parent's finger.
        line_h = 22
        if failing:
            problem = self._password_problem or _PASSWORD_REJECTED
            reason = {
                _PASSWORD_REJECTED: self._ui_message("auth.rejected"),
                _PASSWORD_CHECK_FAILED: self._ui_message("auth.unavailable"),
                _PASSWORD_RATE_LIMITED: self._ui_message("auth.rate_limited"),
            }.get(problem, problem)
            reason_label = panel_layout.fit_single_line(
                typography, reason, FontRole.CONTROL, 15, _Ink.DANGER, inner_w, min_size=11,
            )
            screen.blit(
                reason_label.surface,
                reason_label.surface.get_rect(center=(card.centerx, y + line_h // 2)),
            )
        hint = panel_layout.fit_single_line(
            typography, self._ui_message("auth.hint"), FontRole.BODY, 14,
            _Ink.MUTED, inner_w, min_size=11,
        )
        btn_h = 48
        hint_y = card.bottom - 16 - hint.height
        btn_y = min(y + line_h + 10, hint_y - 10 - btn_h)
        gap = 14
        btn_w = (inner_w - gap) // 2
        cancel_rect = pygame.Rect(card.left + pad, btn_y, btn_w, btn_h)
        confirm_rect = pygame.Rect(card.right - pad - btn_w, btn_y, btn_w, btn_h)
        self._kit_button(
            screen, cancel_rect, self._ui_message("auth.cancel"), typography, pygame,
            backdrop=_Ink.PANEL, size=17,
        )
        self._targets.append(PanelHitTarget("cancel_auth", None, cancel_rect))
        self._kit_button(
            screen, confirm_rect, self._ui_message("auth.unlock"), typography, pygame,
            backdrop=_Ink.PANEL, role="primary", size=17,
        )
        self._targets.append(PanelHitTarget("confirm_auth", None, confirm_rect))
        screen.blit(hint.surface, hint.surface.get_rect(midtop=(card.centerx, hint_y)))

    def _rail_width(self, typography: GreiaTypography, panel_width: int) -> int:
        """Width of the section rail: the longest label plus padding, bounded."""

        widest = max(
            panel_layout.measure(
                typography, self._ui_message(f"tab.{value}"), FontRole.CONTROL, 16
            )[0]
            for _, value in text.TABS
        )
        return max(128, min(int(panel_width * 0.22), widest + 34))

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
        panel_rect = self._panel_rect((width, height))
        if not chrome_in_base:
            self._paint_panel_chrome(screen, (width, height), typography, pygame, load_icon_fn)

        # The close control's pixels live in the composed base when present;
        # its hit target must exist on every frame either way.
        self._targets.append(
            PanelHitTarget(
                "close_panel", None, self._panel_close_button_rect((width, height))
            )
        )

        # Sections sit in a vertical rail on the left. A horizontal strip had to
        # wrap onto a second row in Italian, which cost the content 46 px and
        # clipped the audio presets, the account form buttons, the third
        # password field and the pointer reset at 800x480. Landscape screens
        # have width to spare and no height to spare, so the rail spends width.
        top = panel_rect.top + self._HEADER_H + 12
        bottom = panel_rect.bottom - 12
        rail_w = self._rail_width(typography, panel_rect.width)
        rail = pygame.Rect(panel_rect.left + 12, top, rail_w, bottom - top)
        count = len(text.TABS)
        gap = 6 if rail.height < 420 else 8
        item_h = max(34, min(48, (rail.height - gap * (count - 1)) // count))
        for index, (_, tab_value) in enumerate(text.TABS):
            tab_id = ParentPanelTab(tab_value)
            tab_rect = pygame.Rect(
                rail.left, rail.top + index * (item_h + gap), rail.width, item_h
            )
            self._kit_button(
                screen, tab_rect, self._ui_message(f"tab.{tab_value}"), typography, pygame,
                backdrop=_Ink.PANEL, shape="tile", selected=self.active_tab == tab_id,
                align="left",
            )
            self._targets.append(PanelHitTarget("switch_tab", tab_id, tab_rect))

        content_left = rail.right + 12
        content_rect = pygame.Rect(
            content_left, top, panel_rect.right - 12 - content_left, max(80, bottom - top)
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
        # Everything registered before this point (the close control and the
        # section rail) is already in screen coordinates and must not be rebased.
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
        card = pygame.Rect(rect.left, rect.top, rect.width, rect.height)
        pad = self._content_card(screen, card, pygame)
        inner_w = card.width - pad * 2
        y = self._draw_card_header(
            screen, pygame, typography, card, pad,
            self._ui_message("language.title"), self._ui_message("language.note"),
        )
        gap = 12
        columns = 2 if len(SUPPORTED_SYSTEM_LANGUAGES) <= 4 else 3
        page_size = 4 if columns == 2 else 6
        page_start = (self._language_index // page_size) * page_size
        visible = SUPPORTED_SYSTEM_LANGUAGES[page_start:page_start + page_size]
        cell_w = min(280, (inner_w - gap * (columns - 1)) // columns)
        cell_h = 60
        for offset, language in enumerate(visible):
            index = page_start + offset
            row, column = divmod(offset, columns)
            cell = pygame.Rect(
                card.left + pad + column * (cell_w + gap),
                y + row * (cell_h + gap),
                cell_w,
                cell_h,
            )
            selected = index == self._language_index
            face = self._kit_button(
                screen, cell, "", typography, pygame, shape="tile", selected=selected,
                focused=selected and self._keyboard_focus_visible,
            )
            flag = self._get_text(language.flag, FontRole.DISPLAY, 26, _Ink.TEXT, typography)
            screen.blit(flag, flag.get_rect(midleft=(face.left + 14, face.centery)))
            applied = language.locale == self._device_locale
            # Each language under its own name, so a parent who cannot read the
            # current one still finds theirs; the name in the current language
            # sits underneath when it differs.
            label_w = max(1, face.width - 54 - (30 if applied else 0))
            native = str(getattr(language, "native_name", "") or "")
            localized = self._ui_message(f"language.option.{language.locale}")
            label = panel_layout.fit_single_line(
                typography, native or localized, FontRole.CONTROL, 17, _Ink.TEXT,
                label_w, min_size=11,
            )
            if native and localized != native:
                sub = panel_layout.fit_single_line(
                    typography, localized, FontRole.BODY, 13, _Ink.MUTED, label_w, min_size=10
                )
                top = face.centery - (label.height + sub.height) // 2
                screen.blit(label.surface, (face.left + 50, top))
                screen.blit(sub.surface, (face.left + 50, top + label.height))
            else:
                screen.blit(
                    label.surface, label.surface.get_rect(midleft=(face.left + 50, face.centery))
                )
            if applied:
                # The language in force gets a drawn check mark: the selection
                # can move with the arrow keys before Enter applies it.
                cx, cy = face.right - 22, face.centery
                pygame.draw.lines(
                    screen, _Ink.TEXT, False,
                    [(cx - 8, cy), (cx - 2, cy + 6), (cx + 9, cy - 7)], 4,
                )
            self._targets.append(PanelHitTarget("language_select", index, cell))
        rows = -(-len(visible) // columns)
        y += rows * (cell_h + gap) + 6
        if len(SUPPORTED_SYSTEM_LANGUAGES) > page_size:
            page = page_start // page_size
            pages = (len(SUPPORTED_SYSTEM_LANGUAGES) + page_size - 1) // page_size
            nav_h = 38
            if page > 0:
                previous = pygame.Rect(card.left + pad, y, 86, nav_h)
                self._kit_button(screen, previous, "<", typography, pygame)
                self._targets.append(PanelHitTarget("language_page", (page - 1) * page_size, previous))
            if page + 1 < pages:
                following = pygame.Rect(card.right - pad - 86, y, 86, nav_h)
                self._kit_button(screen, following, ">", typography, pygame)
                self._targets.append(PanelHitTarget("language_page", (page + 1) * page_size, following))
            y += nav_h + 6
        self._draw_status(
            screen, pygame, typography, card, pad, y,
            self._language_message, self._language_message_is_error,
        )

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

    def _profile_policy(self) -> Any:
        """The shipped profile policy, loaded once per panel instance.

        The account tab asked for it three times per frame it composed and once
        per typed character, each a TOML parse from disk. Returns None when the
        policy cannot be read; callers keep their previous fallbacks.
        """

        if getattr(self, "_profile_policy_cache", None) is None:
            try:
                from greia_platform.profiles import ProfilePolicy

                root = Path(os.environ.get("GREIA_OS_ROOT", "/opt/greia-os"))
                self._profile_policy_cache = ProfilePolicy.load(
                    root / "runtime" / "profile-defaults.toml"
                )
            except Exception:
                return None
        return self._profile_policy_cache

    def _available_avatars(self) -> tuple[str, ...]:
        """Avatars from the shipped profile policy, never a duplicated list.

        The service validates avatar ids against
        ``runtime/profile-defaults.toml``; offering anything else produces a
        refusal the parent cannot act on. An unreadable policy falls back to the
        store's own default, so the tab still renders.
        """

        policy = self._profile_policy()
        try:
            if policy.avatars:
                return tuple(policy.avatars)
            return (policy.default_avatar,)
        except Exception:
            return ("rainbow",)

    def _max_profiles(self) -> int:
        try:
            return int(self._profile_policy().max_profiles)
        except Exception:
            return 8

    def _max_name_characters(self) -> int:
        try:
            return int(self._profile_policy().max_name_characters)
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
            self._accounts_page = 0
        except ParentCredentialUnavailable:
            self._set_accounts_message(self._copy("STATUS_OFFLINE"), error=True)
        except Exception:
            self._set_accounts_message(self._copy("STATUS_OFFLINE"), error=True)

    def _set_accounts_message(self, message: str | None, *, error: bool = False) -> None:
        self._accounts_message = message
        self._accounts_message_is_error = error

    def _set_security_message(self, message: str | None, *, error: bool = False) -> None:
        self._security_message = message
        self._security_message_is_error = error

    def _create_account(self) -> None:
        client, session = self._parent_client(), self._session
        if client is None or session is None:
            self._set_accounts_message(self._copy("STATUS_OFFLINE"), error=True)
            return
        name = self._account_name.strip()
        if not name:
            self._set_accounts_message(self._copy("ACCOUNTS_NAME_LABEL"), error=True)
            return
        age: int | None = None
        if self._account_age.strip():
            try:
                age = int(self._account_age.strip())
            except ValueError:
                self._set_accounts_message(self._copy("ACCOUNTS_AGE_LABEL"), error=True)
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
            self._set_accounts_message(self._copy("STATUS_OFFLINE"), error=True)
            return
        except Exception:
            self._set_accounts_message(self._copy("STATUS_OFFLINE"), error=True)
            return
        self._account_name = ""
        self._account_age = ""
        self._accounts_mode = "list"
        self._text_field = None
        self._set_accounts_message(self._copy("STATUS_SAVED"))
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
            self._set_accounts_message(self._copy("ACCOUNTS_NAME_LABEL"), error=True)
            return
        if client is None or session is None:
            self._set_accounts_message(self._copy("STATUS_OFFLINE"), error=True)
            return
        try:
            client.rename_child_account(session, target.profile_id, name)
        except ParentRequestFailed as exc:
            self._set_accounts_message(exc.reason, error=True)
            return
        except Exception:
            self._set_accounts_message(self._copy("STATUS_OFFLINE"), error=True)
            return
        self._renaming = None
        self._account_name = ""
        self._account_age = ""
        self._accounts_mode = "list"
        self._text_field = None
        self._set_accounts_message(self._copy("STATUS_SAVED"))
        self._refresh_accounts()

    def _remove_account(self, account: ChildAccount) -> None:
        client, session = self._parent_client(), self._session
        if client is None or session is None:
            self._set_accounts_message(self._copy("STATUS_OFFLINE"), error=True)
            return
        try:
            client.remove_child_account(session, account.profile_id)
        except ParentRequestFailed as exc:
            self._set_accounts_message(exc.reason, error=True)
            return
        except Exception:
            self._set_accounts_message(self._copy("STATUS_OFFLINE"), error=True)
            return
        self._pending_remove = None
        self._accounts_mode = "list"
        self._set_accounts_message(self._copy("STATUS_SAVED"))
        self._refresh_accounts()

    def _change_password(self) -> None:
        client, session = self._parent_client(), self._session
        if client is None or session is None:
            self._set_security_message(self._copy("STATUS_OFFLINE"), error=True)
            return
        if self._security_new != self._security_confirm:
            self._set_security_message(self._copy("SECURITY_MISMATCH"), error=True)
            return
        try:
            client.change_parent_password(
                session, self._security_current, self._security_new
            )
        except ParentRequestFailed as exc:
            reason = exc.reason
            if "current" in reason.lower():
                reason = self._copy("SECURITY_CURRENT_WRONG")
            self._set_security_message(reason, error=True)
            return
        except Exception:
            self._set_security_message(self._copy("STATUS_OFFLINE"), error=True)
            return
        self._security_current = ""
        self._security_new = ""
        self._security_confirm = ""
        self._set_security_message(self._copy("SECURITY_CHANGED"))

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
        """A single-line input; the focused one carries an accent border and caret."""

        focused = self._text_field == field
        self._blit_rounded_card(
            screen, rect, _Ink.CARD, _Ink.PANEL, pygame,
            _Ink.ACCENT if focused else _Ink.CONTOUR, 3 if focused else 1, radius=12,
        )
        shown = ("•" * len(value)) if secret else value
        text_x = rect.left + 14
        caret_x = text_x
        max_w = max(1, rect.width - 32)
        if shown:
            body = panel_layout.fit_single_line(
                typography, shown, FontRole.BODY, 17, _Ink.TEXT, max_w, min_size=12
            )
            body_rect = body.surface.get_rect(midleft=(text_x, rect.centery))
            screen.blit(body.surface, body_rect)
            caret_x = body_rect.right + 3
        elif placeholder and not focused:
            body = panel_layout.fit_single_line(
                typography, placeholder, FontRole.BODY, 16, _Ink.FAINT, max_w, min_size=12
            )
            screen.blit(body.surface, body.surface.get_rect(midleft=(text_x, rect.centery)))
        if focused:
            caret_x = min(caret_x, rect.right - 12)
            pygame.draw.line(
                screen, _Ink.TEXT, (caret_x, rect.centery - 11), (caret_x, rect.centery + 11), 2
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
        sit on top of it. The intro is limited to two lines on short cards so a
        long translation cannot push the controls out of the card.
        """

        y = card.top + 16 if top is None else top
        text_w = max(1, card.width - pad * 2 - reserve_right)
        title = panel_layout.fit_text_block(
            typography, title_text, FontRole.TITLE, 22, _Ink.TEXT, text_w, max_lines=2
        )
        panel_layout.blit_block(screen, title, pygame, card.left + pad, y)
        y += title.height + 4
        if intro_text:
            intro = panel_layout.fit_text_block(
                typography, intro_text, FontRole.BODY, 15, _Ink.MUTED, text_w,
                max_lines=2 if card.height < 440 else 3,
            )
            panel_layout.blit_block(screen, intro, pygame, card.left + pad, y)
            y += intro.height
        return y + 14

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
        width: int | None = None,
        left: int | None = None,
    ) -> int:
        """Draw a feedback line (red for errors, green otherwise); return its height."""

        if not message:
            return 0
        block = panel_layout.fit_text_block(
            typography, message, FontRole.CONTROL, 15,
            _Ink.DANGER if is_error else _Ink.SUCCESS,
            width if width is not None else card.width - pad * 2, max_lines=2,
        )
        panel_layout.blit_block(
            screen, block, pygame, card.left + pad if left is None else left, y
        )
        return block.height

    def _draw_accounts_tab(
        self,
        screen: Any,
        rect: Any,
        typography: GreiaTypography,
        pygame: Any,
    ) -> None:
        card = pygame.Rect(rect.left, rect.top, rect.width, rect.height)
        pad = self._content_card(screen, card, pygame)
        inner_w = card.width - pad * 2

        if self._accounts_mode == "add":
            editing = self._renaming is not None
            y = self._draw_card_header(
                screen, pygame, typography, card, pad,
                self._copy("ACCOUNTS_EDIT") if editing else self._copy("ACCOUNTS_ADD"),
                self._copy("ACCOUNTS_INTRO"),
            )
            # Name and age share a row: stacked, the form is taller than the card
            # on the 480 px floor.
            gap = 12
            age_w = min(200, inner_w // 3)
            name_w = inner_w - age_w - gap
            caption_h = 0
            for index, (label, field, value, placeholder, field_w) in enumerate((
                (self._copy("ACCOUNTS_NAME_LABEL"), "account_name", self._account_name,
                 self._copy("ACCOUNTS_NAME_PLACEHOLDER"), name_w),
                (self._copy("ACCOUNTS_AGE_LABEL"), "account_age", self._account_age,
                 self._copy("ACCOUNTS_AGE_PLACEHOLDER"), age_w),
            )):
                field_x = card.left + pad + (0 if index == 0 else name_w + gap)
                caption = panel_layout.fit_single_line(
                    typography, label, FontRole.CONTROL, 15, _Ink.MUTED, field_w, min_size=11
                )
                panel_layout.blit_block(screen, caption, pygame, field_x, y)
                caption_h = max(caption_h, caption.height)
            for index, (field, value, placeholder, field_w) in enumerate((
                ("account_name", self._account_name, self._copy("ACCOUNTS_NAME_PLACEHOLDER"), name_w),
                ("account_age", self._account_age, self._copy("ACCOUNTS_AGE_PLACEHOLDER"), age_w),
            )):
                field_x = card.left + pad + (0 if index == 0 else name_w + gap)
                field_rect = pygame.Rect(field_x, y + caption_h + 4, field_w, 44)
                self._draw_text_field(
                    screen, pygame, typography, field_rect, "", value, field,
                    placeholder=placeholder,
                )
            y += caption_h + 4 + 44 + 12

            avatars = self._available_avatars()
            caption = panel_layout.fit_single_line(
                typography, self._copy("ACCOUNTS_AVATAR_LABEL"), FontRole.CONTROL, 15,
                _Ink.MUTED, inner_w, min_size=11,
            )
            panel_layout.blit_block(screen, caption, pygame, card.left + pad, y)
            y += caption.height + 4
            picker = pygame.Rect(card.left + pad, y, inner_w, 48)
            self._blit_rounded_card(
                screen, picker, _Ink.CARD, _Ink.PANEL, pygame, _Ink.CONTOUR, 1, radius=12,
            )
            current = avatars[self._account_avatar_index % len(avatars)]
            name_block = panel_layout.fit_single_line(
                typography, current.replace("_", " ").capitalize(), FontRole.CONTROL, 17,
                _Ink.TEXT, max(1, picker.width - 150),
            )
            self._blit_centered(screen, name_block, picker)
            step_w = 60
            for side, step in (("prev", -1), ("next", 1)):
                btn = pygame.Rect(0, picker.top + 5, step_w, picker.height - 10)
                btn.x = picker.left + 6 if side == "prev" else picker.right - 6 - step_w
                face = self._kit_button(
                    screen, btn, "", typography, pygame, backdrop=_Ink.PANEL
                )
                # Drawn, not typeset: U+25C0/U+25B6 are absent from the bundled
                # fonts and rendered as grey tofu boxes.
                cx, cy = face.centerx, face.centery
                size = min(face.width, face.height) // 4
                sign = -1 if side == "prev" else 1
                points = [
                    (cx - sign * size // 2, cy - size),
                    (cx - sign * size // 2, cy + size),
                    (cx + sign * size // 2, cy),
                ]
                pygame.draw.polygon(screen, _Ink.TEXT, points)
                self._targets.append(PanelHitTarget("account_avatar", step, btn))
            y += 48 + 14

            gap = 12
            half = (inner_w - gap) // 2
            for index, (label, action, role) in enumerate((
                (self._copy("ACCOUNTS_CANCEL"), "account_cancel", "neutral"),
                (
                    self._copy("ACCOUNTS_SAVE") if editing else self._copy("ACCOUNTS_CREATE"),
                    "account_save" if editing else "account_create",
                    "primary",
                ),
            )):
                btn = pygame.Rect(card.left + pad + index * (half + gap), y, half, 46)
                self._kit_button(screen, btn, label, typography, pygame, role=role, size=17)
                self._targets.append(PanelHitTarget(action, None, btn))
            y += 46 + 10
            self._draw_status(
                screen, pygame, typography, card, pad, y,
                self._accounts_message, self._accounts_message_is_error,
            )
            return

        if self._accounts_mode == "confirm" and self._pending_remove is not None:
            y = self._draw_card_header(
                screen, pygame, typography, card, pad,
                self._copy("ACCOUNTS_CONFIRM_REMOVE_TITLE"),
                self._copy("ACCOUNTS_CONFIRM_REMOVE_BODY"),
            )
            name = panel_layout.fit_text_block(
                typography, self._pending_remove.display_name, FontRole.TITLE, 20,
                _Ink.TEXT, inner_w, max_lines=1,
            )
            panel_layout.blit_block(screen, name, pygame, card.left + pad, y)
            y += name.height + 16
            gap = 12
            half = (inner_w - gap) // 2
            for index, (label, action, role) in enumerate((
                (self._copy("ACCOUNTS_CANCEL"), "account_remove_cancel", "neutral"),
                (self._copy("ACCOUNTS_CONFIRM_REMOVE_YES"), "account_remove_confirm", "danger"),
            )):
                btn = pygame.Rect(card.left + pad + index * (half + gap), y, half, 46)
                self._kit_button(screen, btn, label, typography, pygame, role=role, size=17)
                self._targets.append(PanelHitTarget(action, None, btn))
            y += 46 + 10
            self._draw_status(
                screen, pygame, typography, card, pad, y,
                self._accounts_message, self._accounts_message_is_error,
            )
            return

        # The "Add child" button shares the title's row; the flow below it
        # starts under the button rather than beside it.
        header_top = card.top + 16
        limit = self._max_profiles()
        at_limit = len(self._accounts) >= limit
        add_label = self._copy("ACCOUNTS_ADD")
        add_w = min(
            inner_w // 2,
            max(150, panel_layout.measure(typography, add_label, FontRole.CONTROL, 17)[0] + 40),
        )
        y = self._draw_card_header(
            screen, pygame, typography, card, pad,
            self._copy("ACCOUNTS_TITLE"), self._copy("ACCOUNTS_INTRO"), top=header_top,
            reserve_right=add_w + 12,
        )
        y = max(y, header_top + 46 + 12)
        add_rect = pygame.Rect(card.right - pad - add_w, header_top, add_w, 46)
        self._kit_button(
            screen, add_rect, add_label, typography, pygame, role="primary",
            disabled=at_limit, size=17,
        )
        if not at_limit:
            self._targets.append(PanelHitTarget("account_add", None, add_rect))

        if not self._accounts_loaded:
            self._refresh_accounts()
        status_reserve = 46
        if not self._accounts:
            if self._accounts_loaded:
                empty = panel_layout.fit_text_block(
                    typography, self._copy("ACCOUNTS_EMPTY"), FontRole.BODY, 16,
                    _Ink.MUTED, inner_w,
                )
                panel_layout.blit_block(screen, empty, pygame, card.left + pad, y + 4)
                y += empty.height + 16
        else:
            row_h = 56
            gap_y = 8
            pager_h = 40
            space = card.bottom - status_reserve - y
            per_page = max(1, space // (row_h + gap_y))
            pages = -(-len(self._accounts) // per_page)
            if pages > 1:
                # Paging instead of silently dropping the rows that do not fit:
                # eight children is the shipped policy maximum and only four or
                # five rows fit on the 480 px floor.
                per_page = max(1, (space - pager_h) // (row_h + gap_y))
                pages = -(-len(self._accounts) // per_page)
            page = max(0, min(pages - 1, int(self._accounts_page)))
            shown = self._accounts[page * per_page:(page + 1) * per_page]
            button_w = min(130, max(96, inner_w // 5))
            for index, account in enumerate(shown):
                row = pygame.Rect(card.left + pad, y + index * (row_h + gap_y), inner_w, row_h)
                self._blit_rounded_card(
                    screen, row, _Ink.CARD, _Ink.PANEL, pygame, _Ink.CONTOUR, 1, radius=14,
                )
                remove_rect = pygame.Rect(
                    row.right - 8 - button_w, row.top + 7, button_w, row_h - 14
                )
                rename_rect = pygame.Rect(
                    remove_rect.left - 8 - button_w, row.top + 7, button_w, row_h - 14
                )
                name_w = max(1, rename_rect.left - row.left - 24)
                name = panel_layout.fit_single_line(
                    typography, account.display_name, FontRole.CONTROL, 18, _Ink.TEXT,
                    name_w, min_size=12,
                )
                details = account.avatar_id.replace("_", " ").capitalize()
                if account.approximate_age is not None:
                    details = f"{details} · {account.approximate_age}"
                sub = panel_layout.fit_single_line(
                    typography, details, FontRole.BODY, 13, _Ink.MUTED, name_w, min_size=10
                )
                top = row.centery - (name.height + sub.height) // 2
                screen.blit(name.surface, (row.left + 16, top))
                screen.blit(sub.surface, (row.left + 16, top + name.height))
                self._kit_button(
                    screen, rename_rect, self._copy("ACCOUNTS_RENAME"), typography, pygame,
                    backdrop=_Ink.PANEL, size=15,
                )
                self._targets.append(
                    PanelHitTarget("account_rename", account.profile_id, rename_rect)
                )
                self._kit_button(
                    screen, remove_rect, self._copy("ACCOUNTS_REMOVE"), typography, pygame,
                    backdrop=_Ink.PANEL, role="danger_text", size=15,
                )
                self._targets.append(
                    PanelHitTarget("account_remove", account.profile_id, remove_rect)
                )
            y += len(shown) * (row_h + gap_y)
            if pages > 1:
                pager_w = 56
                label = panel_layout.fit_single_line(
                    typography, f"{page + 1} / {pages}", FontRole.CONTROL, 15,
                    _Ink.TEXT, 80,
                )
                prev_rect = pygame.Rect(card.left + pad, y, pager_w, pager_h - 4)
                next_rect = pygame.Rect(prev_rect.right + 96, y, pager_w, pager_h - 4)
                for btn, step in ((prev_rect, -1), (next_rect, 1)):
                    enabled = 0 <= page + step < pages
                    face = self._kit_button(
                        screen, btn, "", typography, pygame, disabled=not enabled
                    )
                    cx, cy, size = face.centerx, face.centery, 7
                    points = [
                        (cx + step * -size // 2, cy - size),
                        (cx + step * -size // 2, cy + size),
                        (cx + step * size // 2, cy),
                    ]
                    pygame.draw.polygon(
                        screen,
                        _Ink.TEXT if enabled else _mix(_Ink.TEXT, _Ink.DISABLED, 0.55),
                        points,
                    )
                    if enabled:
                        self._targets.append(PanelHitTarget("account_page", step, btn))
                screen.blit(
                    label.surface,
                    label.surface.get_rect(
                        center=((prev_rect.right + next_rect.left) // 2, prev_rect.centery)
                    ),
                )
                y += pager_h
        y += 6
        if at_limit:
            self._draw_status(
                screen, pygame, typography, card, pad, y,
                self._copy("ACCOUNTS_LIMIT_REACHED", count=str(limit)), True,
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
        pad = self._content_card(screen, card, pygame)
        inner_w = card.width - pad * 2
        y = self._draw_card_header(
            screen, pygame, typography, card, pad,
            self._copy("SECURITY_TITLE"), self._copy("SECURITY_INTRO"),
        )
        # Current password on its own row, new + repeat side by side, then the
        # action after the fields it submits (it used to sit on the title row,
        # above the fields, which read backwards).
        gap = 12
        half = (inner_w - gap) // 2
        rows = (
            ((self._copy("SECURITY_CURRENT_LABEL"), "security_current", self._security_current, half),),
            (
                (self._copy("SECURITY_NEW_LABEL"), "security_new", self._security_new, half),
                (self._copy("SECURITY_CONFIRM_LABEL"), "security_confirm", self._security_confirm, half),
            ),
        )
        for row in rows:
            caption_h = 0
            for column, (label, field, value, field_w) in enumerate(row):
                caption = panel_layout.fit_single_line(
                    typography, label, FontRole.CONTROL, 15, _Ink.MUTED, field_w, min_size=11
                )
                panel_layout.blit_block(
                    screen, caption, pygame, card.left + pad + column * (half + gap), y
                )
                caption_h = max(caption_h, caption.height)
            for column, (label, field, value, field_w) in enumerate(row):
                field_rect = pygame.Rect(
                    card.left + pad + column * (half + gap), y + caption_h + 4, field_w, 44
                )
                self._draw_text_field(
                    screen, pygame, typography, field_rect, label, value, field, secret=True
                )
            y += caption_h + 4 + 44 + 12
        action_label = self._copy("SECURITY_CHANGE")
        action_w = min(
            inner_w,
            max(180, panel_layout.measure(typography, action_label, FontRole.CONTROL, 17)[0] + 44),
        )
        action = pygame.Rect(card.right - pad - action_w, y + 2, action_w, 46)
        self._kit_button(
            screen, action, action_label, typography, pygame, role="primary", size=17,
            focused=self._keyboard_focus_visible and self._text_field is None,
        )
        self._targets.append(PanelHitTarget("security_change", None, action))
        status_w = action.left - (card.left + pad) - 12
        if status_w >= 200:
            self._draw_status(
                screen, pygame, typography, card, pad, y + 6,
                self._security_message, self._security_message_is_error, width=status_w,
            )
        else:
            self._draw_status(
                screen, pygame, typography, card, pad, action.bottom + 8,
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
        noise_w = self._noise_column_width(inner_w)
        band_w = inner_w - noise_w - 16 if noise_w else inner_w
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
        # Card colour, so the repainted band is invisible against the card it
        # sits on (it used to be the lighter panel colour, a visible patch).
        pygame.draw.rect(screen, _Ink.CARD, band)
        self._paint_input_meter(
            screen, pygame, typography, band, 4, band.top, band.width - 8,
            full_width=True,
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
        *,
        full_width: bool = False,
    ) -> int:
        """Live microphone input level, with a peak hold and a clip warning.

        The gain controls below show the *setting*. This shows what the microphone
        is actually hearing, which is the only way a parent can tell a working
        microphone from a muted one, and the only way to notice that a gain is
        too high. Measured on the reference Acer, whose ALC268 input was peaking
        at 0.0 dBFS, i.e. clipping, with no indication of it anywhere in the UI.
        ``full_width`` is used by the repaint, whose band is already the meter's
        own width.
        """

        noise_w = 0 if full_width else self._noise_column_width(inner_w)
        meter_w = inner_w - noise_w - 16 if noise_w else inner_w
        level: MicrophoneLevel = self._mic_level_reader.level
        # Hysteresis on the silent label. A quiet room sits on the silence floor
        # and the label flickered on and off, which looked like a broken meter.
        if level.available:
            if level.rms_dbfs > MicrophoneLevel.SILENCE_RELEASE_DBFS:
                self._mic_quiet = False
            elif level.rms_dbfs <= SILENCE_FLOOR_DBFS:
                self._mic_quiet = True
        quiet = bool(self._mic_quiet)
        now = time.monotonic()
        if level.available:
            if level.peak_dbfs >= self._mic_peak_hold_dbfs:
                self._mic_peak_hold_dbfs = level.peak_dbfs
                self._mic_peak_hold_until = now + 1.2
            elif now > self._mic_peak_hold_until:
                self._mic_peak_hold_dbfs = max(
                    SILENCE_FLOOR_DBFS, self._mic_peak_hold_dbfs - 1.0
                )

        title = panel_layout.fit_single_line(
            typography, self._copy("AUDIO_INPUT_LABEL"), FontRole.CONTROL, 16,
            _Ink.TEXT, max(1, meter_w // 2 + meter_w // 4), min_size=11,
        )
        panel_layout.blit_block(screen, title, pygame, card.left + pad, y)
        line_h = title.height

        if not level.available:
            # "No microphone" is only honest when the endpoint itself is gone. The
            # capture device is exclusive, so another process opening it briefly -
            # including a diagnostic - starves the meter without there being
            # anything wrong with the microphone.
            reason = str(level.device or "")
            waiting = not reason or reason in {"starting", "reconnecting", "service stopped", "no service"}
            note = panel_layout.fit_text_block(
                typography,
                self._copy("AUDIO_INPUT_WAITING") if waiting else self._copy("AUDIO_INPUT_UNAVAILABLE"),
                FontRole.BODY, 15, _Ink.MUTED, meter_w, max_lines=2,
            )
            panel_layout.blit_block(screen, note, pygame, card.left + pad, y + line_h + 6)
            # Reserve the same height the bar would occupy. The repaint band is
            # captured from one of these draws and replayed on cached frames, so a
            # band measured while the input looked unavailable must not be shorter
            # than the live bar.
            return y + line_h + 6 + max(note.height, self._METER_RESERVED_TAIL - 6)

        readout = self._copy("AUDIO_INPUT_SILENT") if quiet else f"{level.rms_dbfs:+.0f} dB"
        if level.clipping:
            # Debian 12 ships Python 3.11: no same-quote nesting inside f-strings (PEP 701).
            clipping = self._copy("AUDIO_INPUT_CLIPPING")
            readout = f"{clipping}  {level.rms_dbfs:+.0f} dB"
        value = panel_layout.fit_single_line(
            typography, readout, FontRole.CONTROL, 15,
            _Ink.DANGER if level.clipping else _Ink.MUTED,
            max(1, meter_w - title.width - 12), min_size=11,
        )
        # Right-aligned by its own measured width inside the meter's width.
        # blit_block has no right alignment (anything but "center" is left), so
        # passing the right edge put the readout under the noise column.
        screen.blit(value.surface, (card.left + pad + meter_w - value.width, y + 1))

        bar_h = 16
        track = pygame.Rect(card.left + pad, y + line_h + 10, meter_w, bar_h)
        pygame.draw.rect(screen, _Ink.TRACK, track, border_radius=bar_h // 2)

        def position(db: float) -> int:
            span = 0.0 - SILENCE_FLOOR_DBFS
            fraction = (db - SILENCE_FLOOR_DBFS) / span if span else 0.0
            return int(track.width * max(0.0, min(1.0, fraction)))

        filled = position(level.rms_dbfs)
        if filled > 0:
            pygame.draw.rect(
                screen, _Ink.DANGER if level.clipping else _Ink.ACCENT,
                pygame.Rect(track.left, track.top, max(filled, bar_h), track.height),
                border_radius=bar_h // 2,
            )
        peak_x = track.left + position(self._mic_peak_hold_dbfs)
        pygame.draw.rect(
            screen, _Ink.CONTOUR,
            pygame.Rect(peak_x - 1, track.top - 3, 3, track.height + 6),
        )
        return track.bottom + 4

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
        pad = self._content_card(screen, card, pygame)
        inner_w = card.width - pad * 2
        y = self._draw_card_header(
            screen, pygame, typography, card, pad,
            self._copy("AUDIO_TITLE"), self._copy("AUDIO_INTRO"),
        )

        # Row 1: what the microphone hears, with noise cancelling beside it (or
        # below it when the card is too narrow for two columns).
        meter_top = y
        meter_bottom = self._draw_input_meter(screen, pygame, typography, card, pad, y, inner_w)
        noise_bottom = self._draw_noise_cancelling(
            screen, pygame, typography, card, pad, meter_top, meter_bottom
        )
        y = max(meter_bottom, noise_bottom) + 14

        # Row 2: the gain. The steppers flank the presets in one row of tiles,
        # so the setting, its named levels and the fine adjustment read as one
        # control; the exact value is in the caption. The former separate badge
        # + track + preset rows did not fit the 480 px floor at all.
        current_gain = self._current_mic_gain()
        pct = int(round(current_gain * 100))
        caption = panel_layout.fit_single_line(
            typography, f"{self._copy('AUDIO_LEVEL_LABEL')}: {pct}%", FontRole.CONTROL, 16,
            _Ink.TEXT, inner_w,
        )
        panel_layout.blit_block(screen, caption, pygame, card.left + pad, y)
        y += caption.height + 6

        values = sorted(text.AUDIO_PRESET_NAMES)
        gap = 8
        step_w = 76 if inner_w >= 560 else 64
        preset_area = inner_w - 2 * (step_w + gap)
        widths = panel_layout.even_columns(preset_area, len(values), gap)
        tile_h = 54
        x = card.left + pad
        down = pygame.Rect(x, y, step_w, tile_h)
        self._kit_button(
            screen, down, self._copy("AUDIO_DECREASE"), typography, pygame,
            shape="tile", size=16, disabled=current_gain <= 0.5,
        )
        self._targets.append(PanelHitTarget("mic_gain_adjust", -0.25, down))
        x = down.right + gap
        for index, value in enumerate(values):
            tile = pygame.Rect(x, y, widths[index], tile_h)
            self._kit_button(
                screen, tile, f"{int(value * 100)}%", typography, pygame, shape="tile",
                selected=abs(current_gain - value) < 0.05, size=16,
                sublabel=panel_audio_preset(value, self._device_locale),
            )
            self._targets.append(PanelHitTarget("mic_gain_set", value, tile))
            x = tile.right + gap
        up = pygame.Rect(x, y, card.left + pad + inner_w - x, tile_h)
        self._kit_button(
            screen, up, self._copy("AUDIO_INCREASE"), typography, pygame,
            shape="tile", size=16, disabled=current_gain >= 4.0,
        )
        self._targets.append(PanelHitTarget("mic_gain_adjust", 0.25, up))
        y += tile_h + 12

        self._draw_status(
            screen, pygame, typography, card, pad, y,
            self._audio_message, self._audio_message_is_error,
        )

    def _noise_column_width(self, inner_w: int) -> int:
        """Width of the noise cancelling column beside the meter, or 0.

        The meter's bar and the column share one row, so both must agree on where
        the split is (the bar used to run underneath the column).
        """

        if inner_w < 460:
            return 0
        return max(200, int(inner_w * 0.38))

    def _draw_noise_cancelling(
        self,
        screen: Any,
        pygame: Any,
        typography: GreiaTypography,
        card: Any,
        pad: int,
        top: int,
        meter_bottom: int,
    ) -> int:
        """Noise cancelling: processing on/off, and advanced reduction.

        Drawn in a column beside the live meter, or as a row below it on a narrow
        card. Returns the bottom of what it drew.

        Read and written through the Parent service: the settings directory is
        greiapel-owned and this panel runs as greiakid, which has read but not
        write access. That gap is why the pointer and audio controls looked
        functional and silently did nothing.
        """

        inner_w = card.width - pad * 2
        col_w = self._noise_column_width(inner_w)
        toggles = [
            (
                "mic_processing",
                self._copy("AUDIO_NOISE_PROCESSING"),
                self._audio_processing_enabled,
                True,
            ),
            (
                "mic_advanced",
                self._copy("AUDIO_NOISE_ADVANCED"),
                self._audio_advanced_enabled and self._audio_processing_enabled,
                self._audio_advanced_available and self._audio_processing_enabled,
            ),
        ]
        unavailable = self._ui_message("state.unavailable")
        if col_w:
            col_x = card.left + pad + inner_w - col_w
            title = panel_layout.fit_single_line(
                typography, self._copy("AUDIO_NOISE_TITLE"), FontRole.CONTROL, 16,
                _Ink.TEXT, col_w, min_size=11,
            )
            panel_layout.blit_block(screen, title, pygame, col_x, top)
            y = top + title.height + 6
            for field, label, is_on, enabled in toggles:
                box = pygame.Rect(col_x, y, col_w, 46)
                self._kit_toggle(
                    screen, box, label, is_on, enabled, typography, pygame,
                    note=None if enabled else unavailable,
                )
                if enabled:
                    self._targets.append(PanelHitTarget("mic_processing_toggle", field, box))
                y += 46 + 8
            return y - 8
        # Narrow card: a titled row of two tiles under the meter.
        y = meter_bottom + 10
        title = panel_layout.fit_single_line(
            typography, self._copy("AUDIO_NOISE_TITLE"), FontRole.CONTROL, 16,
            _Ink.TEXT, inner_w, min_size=11,
        )
        panel_layout.blit_block(screen, title, pygame, card.left + pad, y)
        y += title.height + 6
        gap = 10
        half = (inner_w - gap) // 2
        for index, (field, label, is_on, enabled) in enumerate(toggles):
            box = pygame.Rect(card.left + pad + index * (half + gap), y, half, 46)
            self._kit_toggle(
                screen, box, label, is_on, enabled, typography, pygame,
                note=None if enabled else unavailable,
            )
            if enabled:
                self._targets.append(PanelHitTarget("mic_processing_toggle", field, box))
        return y + 46

    def _draw_pointer_tab(
        self,
        screen: Any,
        rect: Any,
        typography: GreiaTypography,
        pygame: Any,
    ) -> None:
        """Draw the dedicated pointer-feel tab (semantic settings only)."""

        card = pygame.Rect(rect.left, rect.top, rect.width, rect.height)
        pad = self._content_card(screen, card, pygame)
        y = self._draw_card_header(
            screen, pygame, typography, card, pad,
            self._ui_message("pointer.title"), self._ui_message("pointer.note"),
        )
        section_top = y

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
        focused_item = focus_items[focus] if self._keyboard_focus_visible else None

        inner_w = card.width - pad * 2
        test_w = max(120, int(inner_w * 0.28))
        left_w = inner_w - test_w - 16
        left = card.left + pad
        right = left + left_w + 16
        # Shorter chips on the 480 px floor so the toggles and reset still fit.
        row_h = max(36, min(44 if card.height >= 420 else 36, min_touch - 4))
        gap = 8

        for which, label_key, none_key, current, available, action in (
            ("touchpad_speed", "pointer.touchpad.speed", "pointer.touchpad.none",
             touch_preset, has_touchpad, "pointer_touchpad_preset"),
            ("mouse_speed", "pointer.mouse.speed", "pointer.mouse.none",
             mouse_preset, has_relative, "pointer_mouse_preset"),
        ):
            caption_text = self._ui_message(label_key)
            if not available:
                caption_text = f"{caption_text}  {self._ui_message(none_key)}"
            caption = panel_layout.fit_single_line(
                typography, caption_text, FontRole.CONTROL, 15,
                _Ink.TEXT if available else _Ink.MUTED, left_w, min_size=11,
            )
            panel_layout.blit_block(screen, caption, pygame, left, y)
            y += caption.height + 4
            widths = panel_layout.even_columns(left_w, len(presets), 6)
            x = left
            for idx, name in enumerate(presets):
                chip = pygame.Rect(x, y, widths[idx], row_h)
                self._kit_button(
                    screen, chip, self._ui_message(f"pointer.preset.short.{name}"),
                    typography, pygame, shape="tile", size=14,
                    selected=name == current and available, disabled=not available,
                    focused=focused_item == which and name == current,
                )
                self._targets.append(PanelHitTarget(action, name, chip))
                x = chip.right + 6
            y += row_h + 10

        toggles = [
            ("touchpad_tap", self._ui_message("pointer.toggle.tap"), tap_on, has_touchpad),
            ("natural_scrolling", self._ui_message("pointer.toggle.scroll"), natural_on, True),
            ("disable_while_typing", self._ui_message("pointer.toggle.typing"), dwt_on, has_touchpad),
        ]
        widths = panel_layout.even_columns(left_w, len(toggles), gap)
        tog_h = 78  # two label lines above the switch
        x = left
        for idx, (field, label, is_on, enabled) in enumerate(toggles):
            tog = pygame.Rect(x, y, widths[idx], tog_h)
            self._kit_toggle(
                screen, tog, label, is_on, enabled, typography, pygame,
                focused=focused_item == field, stacked=True,
            )
            self._targets.append(PanelHitTarget("pointer_toggle", field, tog))
            x = tog.right + gap
        y += tog_h + 10

        reset_label = self._ui_message("pointer.reset")
        reset_w = min(
            left_w,
            max(150, panel_layout.measure(typography, reset_label, FontRole.CONTROL, 15)[0] + 36),
        )
        reset_rect = pygame.Rect(left, y, reset_w, 42)
        self._kit_button(
            screen, reset_rect, reset_label, typography, pygame, size=15,
            focused=focused_item == "reset",
        )
        self._targets.append(PanelHitTarget("pointer_reset", None, reset_rect))
        message_w = left_w - reset_w - 12
        if message_w >= 140:
            self._draw_status(
                screen, pygame, typography, card, pad, reset_rect.top + 2,
                self._pointer_message, self._pointer_message_is_error,
                width=message_w, left=reset_rect.right + 12,
            )
        else:
            self._draw_status(
                screen, pygame, typography, card, pad, reset_rect.bottom + 6,
                self._pointer_message, self._pointer_message_is_error, width=left_w,
            )

        # --- Bounded test region (right column) ---
        test_rect = pygame.Rect(
            right, section_top, card.left + pad + inner_w - right,
            max(120, card.bottom - pad - section_top),
        )
        self._blit_rounded_card(
            screen, test_rect, _Ink.CARD, _Ink.PANEL, pygame, _Ink.TRACK, 2, radius=14
        )
        cap = panel_layout.fit_single_line(
            typography, self._ui_message("pointer.test"), FontRole.CONTROL, 15,
            _Ink.MUTED, test_rect.width - 20, min_size=11,
        )
        screen.blit(cap.surface, cap.surface.get_rect(center=test_rect.center))
        margin = 10
        cell = max(min_touch, 52)
        positions = [
            (test_rect.left + margin, test_rect.top + margin),
            (test_rect.right - margin - cell, test_rect.top + margin),
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
            fill = _Ink.SUCCESS if flashed else _Ink.ACCENT
            self._blit_rounded_card(
                screen, target, _Ink.PANEL, fill, pygame, _Ink.CONTOUR, 2,
                radius=cell // 2, lip=3,
            )
            # Drawn dot: U+25CF is missing from the bundled fonts (tofu box).
            pygame.draw.circle(
                screen, _Ink.WHITE if flashed else _Ink.TEXT,
                (target.centerx, target.centery - 2), max(4, cell // 8),
            )
            if focused_item == f"test{idx}":
                self._kit_focus_ring(screen, target, cell // 2, pygame)
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
        card = pygame.Rect(rect.left, rect.top, rect.width, rect.height)
        pad = self._content_card(screen, card, pygame)
        inner_w = card.width - pad * 2

        scan_label = self._ui_message("wifi.scan")
        scan_w = max(110, panel_layout.measure(typography, scan_label, FontRole.CONTROL, 16)[0] + 40)
        scan = pygame.Rect(card.right - pad - scan_w, card.top + 14, scan_w, 42)
        self._kit_button(screen, scan, scan_label, typography, pygame, size=16)
        self._targets.append(PanelHitTarget("wifi_refresh", None, scan))

        title_w = max(1, scan.left - card.left - pad - 12)
        title = panel_layout.fit_single_line(
            typography, self._ui_message("wifi.title"), FontRole.TITLE, 22, _Ink.TEXT,
            title_w, min_size=14,
        )
        panel_layout.blit_block(screen, title, pygame, card.left + pad, card.top + 14)
        phase = self._ui_message(f"wifi.phase.{snapshot.phase.value}")
        status_text = self._ui_message("wifi.status", phase=phase)
        if snapshot.connected_ssid:
            status_text += self._ui_message("wifi.connected", ssid=snapshot.connected_ssid)
        if snapshot.error:
            status_text = self._ui_message("wifi.error", detail=str(snapshot.error))
        status = panel_layout.fit_text_block(
            typography, status_text, FontRole.BODY, 15,
            _Ink.DANGER if snapshot.error else _Ink.MUTED, title_w, max_lines=2,
        )
        panel_layout.blit_block(
            screen, status, pygame, card.left + pad, card.top + 14 + title.height
        )
        top = max(scan.bottom, card.top + 14 + title.height + status.height) + 12

        gap = 14
        list_w = (inner_w - gap) // 2
        body_h = card.bottom - pad - top
        list_rect = pygame.Rect(card.left + pad, top, list_w, body_h)
        self._blit_rounded_card(
            screen, list_rect, _Ink.CARD, _Ink.PANEL, pygame, _Ink.TRACK, 2, radius=14
        )
        item_h = 44
        capacity = max(0, (list_rect.height - 12) // (item_h + 6))
        item_y = list_rect.top + 8
        security_note = {
            WifiSecurity.PERSONAL: "wifi.security.personal",
            WifiSecurity.ENTERPRISE: "wifi.security.enterprise",
        }
        for idx, network in enumerate(snapshot.networks[:capacity]):
            item_rect = pygame.Rect(list_rect.left + 8, item_y, list_rect.width - 16, item_h)
            face = self._kit_button(
                screen, item_rect, "", typography, pygame, backdrop=_Ink.PANEL,
                shape="tile", selected=idx == snapshot.selected_index,
            )
            name = panel_layout.fit_single_line(
                typography, network.ssid, FontRole.CONTROL, 16, _Ink.TEXT,
                max(1, face.width - 72), min_size=11,
            )
            screen.blit(name.surface, name.surface.get_rect(midleft=(face.left + 12, face.centery)))
            self._paint_signal(screen, face, network.signal_dbm, pygame)
            if network.security in security_note:
                # A drawn padlock: the emoji lock needs the colour-emoji font.
                lx, ly = face.right - 46, face.centery
                pygame.draw.rect(screen, _Ink.TEXT, pygame.Rect(lx - 5, ly - 1, 10, 8), border_radius=2)
                pygame.draw.arc(screen, _Ink.TEXT, pygame.Rect(lx - 4, ly - 8, 8, 10), 0, 3.15, 2)
            self._targets.append(PanelHitTarget("wifi_select", idx, item_rect))
            item_y += item_h + 6

        if not snapshot.networks:
            empty = panel_layout.fit_text_block(
                typography, self._ui_message("wifi.empty"), FontRole.BODY, 15,
                _Ink.MUTED, list_rect.width - 24, max_lines=3,
            )
            screen.blit(empty.surface, empty.surface.get_rect(center=list_rect.center))

        form_rect = pygame.Rect(list_rect.right + gap, top, inner_w - list_w - gap, body_h)
        selected = snapshot.selected_network
        if selected is None:
            hint = panel_layout.fit_text_block(
                typography, self._ui_message("wifi.choose"), FontRole.BODY, 15,
                _Ink.MUTED, form_rect.width - 24, max_lines=3,
            )
            screen.blit(hint.surface, hint.surface.get_rect(center=form_rect.center))
            return
        y = form_rect.top + 4
        name = panel_layout.fit_text_block(
            typography, selected.ssid, FontRole.TITLE, 20, _Ink.TEXT, form_rect.width, max_lines=2
        )
        panel_layout.blit_block(screen, name, pygame, form_rect.left, y)
        y += name.height + 2
        security_key = {
            WifiSecurity.PERSONAL: "wifi.security.personal",
            WifiSecurity.ENTERPRISE: "wifi.security.enterprise",
        }.get(selected.security, "wifi.security.open")
        sec = panel_layout.fit_single_line(
            typography, self._ui_message(security_key), FontRole.BODY, 15, _Ink.MUTED,
            form_rect.width, min_size=11,
        )
        panel_layout.blit_block(screen, sec, pygame, form_rect.left, y)
        y += sec.height + 12
        if selected.security == WifiSecurity.PERSONAL:
            caption = panel_layout.fit_single_line(
                typography, self._ui_message("wifi.password"), FontRole.CONTROL, 15,
                _Ink.MUTED, form_rect.width, min_size=11,
            )
            panel_layout.blit_block(screen, caption, pygame, form_rect.left, y)
            y += caption.height + 4
            pwd_box = pygame.Rect(form_rect.left, y, form_rect.width, 44)
            self._blit_rounded_card(
                screen, pwd_box, _Ink.CARD, _Ink.PANEL, pygame, _Ink.ACCENT, 3, radius=12
            )
            if snapshot.passphrase:
                masked = panel_layout.fit_single_line(
                    typography, "•" * len(snapshot.passphrase), FontRole.BODY, 17,
                    _Ink.TEXT, pwd_box.width - 32, min_size=10,
                )
                masked_rect = masked.surface.get_rect(midleft=(pwd_box.left + 14, pwd_box.centery))
                screen.blit(masked.surface, masked_rect)
                caret_x = min(masked_rect.right + 3, pwd_box.right - 12)
            else:
                caret_x = pwd_box.left + 14
                placeholder = panel_layout.fit_single_line(
                    typography, self._ui_message("wifi.password.placeholder"), FontRole.BODY,
                    16, _Ink.FAINT, pwd_box.width - 40, min_size=11,
                )
                screen.blit(
                    placeholder.surface,
                    placeholder.surface.get_rect(midleft=(pwd_box.left + 22, pwd_box.centery)),
                )
            pygame.draw.line(
                screen, _Ink.TEXT, (caret_x, pwd_box.centery - 11), (caret_x, pwd_box.centery + 11), 2
            )
        connect_btn = pygame.Rect(form_rect.left, form_rect.bottom - 48, form_rect.width, 48)
        self._kit_button(
            screen, connect_btn, self._ui_message("wifi.connect"), typography, pygame,
            role="primary", size=17,
        )
        self._targets.append(PanelHitTarget("wifi_connect", None, connect_btn))

    @staticmethod
    def _paint_signal(screen: Any, face: Any, signal_dbm: float, pygame: Any) -> None:
        """Three rising bars, filled by signal strength (-90 .. -50 dBm)."""

        strength = max(0.0, min(1.0, (float(signal_dbm) + 90.0) / 40.0))
        lit = 1 + int(strength * 2.999)
        base_x, base_y = face.right - 26, face.centery + 8
        for bar in range(3):
            h = 6 + bar * 5
            color = _Ink.TEXT if bar < lit else _Ink.TRACK
            pygame.draw.rect(screen, color, pygame.Rect(base_x + bar * 6, base_y - h, 4, h))

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
        pad = self._content_card(screen, card, pygame)
        inner_w = card.width - pad * 2
        # The warning is the intro, at the top, where it is read before the
        # switch rather than after it.
        y = self._draw_card_header(
            screen, pygame, typography, card, pad,
            self._ui_message("ssh.title"), self._ui_message("ssh.note"),
        )

        if status is None:
            waiting = panel_layout.fit_single_line(
                typography, self._ui_message("ssh.checking"), FontRole.BODY, 16,
                _Ink.MUTED, inner_w,
            )
            panel_layout.blit_block(screen, waiting, pygame, card.left + pad, y)
            return

        is_on = status.active or status.enabled
        badge_label = self._ui_message("ssh.enabled") if is_on else self._ui_message("ssh.disabled")
        badge_w = max(150, panel_layout.measure(typography, badge_label, FontRole.CONTROL, 16)[0] + 36)
        badge_rect = pygame.Rect(card.left + pad, y, badge_w, 44)
        self._blit_rounded_card(
            screen, badge_rect, _Ink.CARD, _Ink.SUCCESS if is_on else _Ink.MUTED, pygame,
            radius=22,
        )
        badge = panel_layout.fit_single_line(
            typography, badge_label, FontRole.CONTROL, 16, _Ink.WHITE, badge_w - 20
        )
        self._blit_centered(screen, badge, badge_rect)

        toggle_label = self._ui_message("ssh.turn_off") if is_on else self._ui_message("ssh.turn_on")
        toggle_w = max(150, panel_layout.measure(typography, toggle_label, FontRole.CONTROL, 16)[0] + 40)
        toggle_btn = pygame.Rect(badge_rect.right + 14, y, toggle_w, 46)
        self._kit_button(
            screen, toggle_btn, toggle_label, typography, pygame, role="primary", size=16,
            focused=self._keyboard_focus_visible,
        )
        self._targets.append(PanelHitTarget("ssh_toggle", None, toggle_btn))
        y += 46 + 18

        lines = [
            self._ui_message("ssh.admin", username=status.username),
            self._ui_message("ssh.ip", ip=status.host_ip),
            self._ui_message("ssh.port", port=str(status.port)),
            self._ui_message("ssh.command", username=status.username, ip=status.host_ip),
        ]
        for line in lines:
            block = panel_layout.fit_text_block(
                typography, line, FontRole.BODY, 16, _Ink.TEXT, inner_w, max_lines=2,
            )
            panel_layout.blit_block(screen, block, pygame, card.left + pad, y)
            y += block.height + 6

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
        pad = self._content_card(screen, card, pygame)
        inner_w = card.width - pad * 2
        y = self._draw_card_header(
            screen, pygame, typography, card, pad,
            self._ui_message("info.title"), self._ui_message("info.intro"),
        )
        # Steps wrap instead of shrinking: fit_single_line squeezed the longer
        # Italian steps to an 11 px size nobody could read across a room.
        for key, variables, role in (
            ("info.step_wifi", {}, FontRole.BODY),
            ("info.step_url", {"ip": host_ip}, FontRole.CONTROL),
            ("info.step_mdns", {}, FontRole.BODY),
            ("info.step_login", {}, FontRole.BODY),
        ):
            block = panel_layout.fit_text_block(
                typography, self._ui_message(key, **variables), role, 16, _Ink.TEXT,
                inner_w, max_lines=2,
            )
            panel_layout.blit_block(screen, block, pygame, card.left + pad, y)
            y += block.height + 10
