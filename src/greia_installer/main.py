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

from greia_platform.hardware import HardwareDefaults, HardwareSettings
from greia_platform.hardware_session import HardwareSessionController

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
from .disk import BlockDevice, DiskProbeError, LsblkDiskProbe
from .engine import (
    InstallProgress,
    InstallRequest,
    InstallResult,
    InstallationEngine,
)
from .power import PowerSupplyProbe
from .wifi import IwdWifiBackend, WifiSecurity
from .wifi_setup import DemoWifiBackend, WifiSetupController, WifiSetupPhase


class InstallerPage(Enum):
    WELCOME = auto()
    LAYOUT = auto()
    TARGET = auto()
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
        return InstallResult(
            recovery_user="pip-recovery",
            recovery_code="DEMO2345DEMO6789DEMO",
        )


class InstallerApplication:
    HOLD_SECONDS = 2.0
    WIFI_ROWS_PER_PAGE = 3

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
    ):
        self.root = root.resolve()
        self.payload = payload.resolve()
        self.payload_digest = (
            payload_digest.resolve() if payload_digest is not None else None
        )
        self.windowed = windowed
        self.demo = demo
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
            return LsblkDiskProbe().probe().install_targets()
        except DiskProbeError:
            return ()

    def _available_resolutions(self) -> tuple[str, ...]:
        if self.demo:
            return ("auto", "800x600", "1024x600", "1024x768")
        controller = (
            self.hardware_controller or provisional_installer_hardware_controller()
        )
        display = controller.probe_display()
        return ("auto", *display.allowed_mode_ids)

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
            for event in pygame.event.get():
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
            self._draw(screen, pygame)
            self._draw_pointer(screen, pygame)
            pygame.display.flip()
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
            self.state.page = InstallerPage.SETTINGS
        elif self.state.page == InstallerPage.SETTINGS:
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
            self.state.page = InstallerPage.TARGET
        elif page == InstallerPage.WIFI:
            # Leaving this stage means no in-flight scan/connection may later
            # become the parent's chosen installation profile.
            self.wifi.skip()
            self.state.page = InstallerPage.SETTINGS
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

    def _handle_settings_click(self, position: tuple[int, int]) -> None:
        settings = self.state.settings
        if self._inside("tap", position):
            settings = replace(settings, touchpad_tap=not settings.touchpad_tap)
        elif self._inside("natural", position):
            settings = replace(
                settings, natural_scrolling=not settings.natural_scrolling
            )
        elif self._inside("mouse-minus", position):
            settings = replace(
                settings, mouse_speed=max(-1.0, settings.mouse_speed - 0.25)
            )
        elif self._inside("mouse-plus", position):
            settings = replace(
                settings, mouse_speed=min(1.0, settings.mouse_speed + 0.25)
            )
        elif self._inside("touch-minus", position):
            settings = replace(
                settings, touchpad_speed=max(-1.0, settings.touchpad_speed - 0.25)
            )
        elif self._inside("touch-plus", position):
            settings = replace(
                settings, touchpad_speed=min(1.0, settings.touchpad_speed + 0.25)
            )
        elif self._inside("resolution", position):
            current = self.available_resolutions.index(settings.resolution)
            settings = replace(
                settings,
                resolution=self.available_resolutions[
                    (current + 1) % len(self.available_resolutions)
                ],
            )
        self.state.settings = settings

    def _start_installation(self) -> None:
        target = self.state.target
        if target is None or self._worker is not None:
            return
        power_problem = self.power_probe.installation_block_reason()
        if power_problem:
            self.state.error = power_problem
            self.state.page = InstallerPage.ERROR
            return
        self.state.error = ""
        self.state.result = None
        self.state.page = InstallerPage.INSTALLING
        engine: Any
        if self.demo:
            engine = DemoInstallationEngine()
        else:
            engine = InstallationEngine(project_root=self.root)
        request = InstallRequest(
            target=target,
            payload=self.payload,
            payload_digest=self.payload_digest,
            hardware_settings=self.state.settings,
            wifi_profile=self.wifi.profile,
        )

        def worker() -> None:
            try:
                result = engine.install(request, self._events.put)
                self._events.put(result)
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
                (width - 190, height - 70),
                260,
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
                label = font.render(target.display_name, True, text)
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
        elif page == InstallerPage.SETTINGS:
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
            self._stepper_row(
                screen,
                pygame,
                "mouse",
                "Mouse speed",
                self.state.settings.mouse_speed,
                font,
                text,
                accent,
                main.top + 246,
            )
            self._stepper_row(
                screen,
                pygame,
                "touch",
                "Touchpad speed",
                self.state.settings.touchpad_speed,
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
            rect = self._button(
                screen,
                pygame,
                "install",
                "Hold to erase and install",
                danger,
                (255, 255, 255),
                font,
                (width // 2, main.bottom - 110),
                390,
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
                label = font.render("Keep holding…", True, (255, 255, 255))
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
            result = self.state.result
            self._center_text(
                screen,
                "Save this parent recovery code",
                font,
                text,
                main.top + 245,
            )
            recovery_code = (
                result.grouped_recovery_code
                if result is not None
                else "CODE UNAVAILABLE"
            )
            code_font = self._typography.font(FontRole.DISPLAY, max(33, height // 15))
            self._center_text(
                screen, recovery_code, code_font, danger, main.top + 305
            )
            self._center_text(
                screen,
                "Photograph or write it down.",
                small_font,
                text,
                main.top + 350,
            )
            self._center_text(
                screen,
                "When asked, type only the letters and numbers — not the spaces.",
                small_font,
                text,
                main.top + 382,
            )
            message = "Close the demo" if self.demo else "I saved it — turn off"
            self._button(
                screen,
                pygame,
                "primary",
                message,
                accent,
                text,
                font,
                (width // 2, main.bottom - 52),
                480,
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
                (screen.get_width() // 2, screen.get_height() - 62),
                260,
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
            image = font.render(label, True, text)
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
                (screen.get_width() - 190, screen.get_height() - 70),
                270,
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
                (screen.get_width() - 185, screen.get_height() - 70),
                250,
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
                (screen.get_width() // 2, screen.get_height() - 70),
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
                (screen.get_width() - 170, screen.get_height() - 70),
                210,
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
            label = font.render(network.ssid, True, text)
            screen.blit(label, (rect.left + 16, rect.top + 10))
            if network.security is WifiSecurity.OPEN:
                security = "Open"
            elif network.security is WifiSecurity.PERSONAL:
                security = "Password"
            else:
                security = "Enterprise — later"
            strength = _signal_label(network.signal_dbm)
            detail = small_font.render(f"{security} · {strength}", True, text)
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
                text_render = small_font.render("".join(segments), True, text)
            else:
                text_render = small_font.render("Wi-Fi password", True, (160, 150, 135))
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
            note = small_font.render(
                "Enterprise Wi-Fi can be configured later in Greia Parents.",
                True,
                danger,
            )
            screen.blit(note, note.get_rect(center=(main.centerx, controls_y + 24)))

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
            (main.right - 145, main.bottom - 56),
            250,
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
            (main.left + 130, main.bottom - 56),
            190,
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
    ) -> None:
        rect = pygame.Rect(
            screen.get_width() * 0.16, y, screen.get_width() * 0.68, 54
        )
        pygame.draw.rect(screen, (247, 235, 203), rect, border_radius=16)
        screen.blit(font.render(label, True, text), (rect.left + 18, rect.top + 13))
        state_rect = pygame.Rect(rect.right - 116, rect.top + 7, 98, 40)
        pygame.draw.rect(
            screen, accent if value else (180, 175, 165), state_rect, border_radius=20
        )
        knob_x = state_rect.right - 20 if value else state_rect.left + 20
        pygame.draw.circle(screen, (255, 255, 255), (knob_x, state_rect.centery), 15)
        self._buttons[key] = rect

    def _stepper_row(
        self,
        screen: Any,
        pygame: Any,
        key: str,
        label: str,
        value: float,
        font: Any,
        text: tuple[int, int, int],
        accent: tuple[int, int, int],
        y: int,
    ) -> None:
        rect = pygame.Rect(
            screen.get_width() * 0.16, y, screen.get_width() * 0.68, 54
        )
        pygame.draw.rect(screen, (247, 235, 203), rect, border_radius=16)
        screen.blit(font.render(label, True, text), (rect.left + 18, rect.top + 13))
        minus = pygame.Rect(rect.right - 210, rect.top + 6, 46, 42)
        plus = pygame.Rect(rect.right - 58, rect.top + 6, 46, 42)
        for button_rect, glyph in ((minus, "−"), (plus, "+")):
            pygame.draw.rect(screen, accent, button_rect, border_radius=14)
            glyph_image = font.render(glyph, True, text)
            screen.blit(glyph_image, glyph_image.get_rect(center=button_rect.center))
        value_image = font.render(f"{value:+.2f}", True, text)
        screen.blit(
            value_image, value_image.get_rect(center=(rect.right - 111, rect.centery))
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
    ) -> None:
        rect = pygame.Rect(
            screen.get_width() * 0.16, y, screen.get_width() * 0.68, 54
        )
        pygame.draw.rect(screen, (247, 235, 203), rect, border_radius=16)
        screen.blit(font.render(label, True, text), (rect.left + 18, rect.top + 13))
        value_rect = pygame.Rect(rect.right - 190, rect.top + 6, 172, 42)
        pygame.draw.rect(screen, accent, value_rect, border_radius=14)
        value_image = font.render(value, True, text)
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
        rect = pygame.Rect(0, 0, width, 58)
        rect.center = center
        pygame.draw.rect(screen, background, rect, border_radius=18)
        image = font.render(label, True, foreground)
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
            frame_path = (
                Path("/usr/share/plymouth/themes/greia/frames/frame_0051.png")
            )
            source = frame_path if frame_path.is_file() else None
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
            frame_path = Path("/usr/share/plymouth/themes/greia/frames/frame_0051.png")
            source = frame_path if frame_path.is_file() else (
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
        if not pygame.mouse.get_focused():
            return
        size = max(34, min(54, screen.get_height() // 12))
        x, y = pygame.mouse.get_pos()
        self._icon(screen, pygame, "yellow_star", size, (x, y))

    def _center_title(
        self,
        screen: Any,
        text_value: str,
        font: Any,
        color: tuple[int, int, int],
        y: int,
    ) -> None:
        image = font.render(text_value, True, color)
        screen.blit(image, image.get_rect(midtop=(screen.get_width() // 2, y)))

    def _center_text(
        self,
        screen: Any,
        text_value: str,
        font: Any,
        color: tuple[int, int, int],
        y: int,
    ) -> None:
        image = font.render(text_value, True, color)
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
                screen.blit(font.render(line, True, color), (rect.left, y))
                y += font.get_linesize()
                line = word
            else:
                line = candidate
        if line:
            screen.blit(font.render(line, True, color), (rect.left, y))

    def _inside(self, key: str, position: tuple[int, int]) -> bool:
        rect = self._buttons.get(key)
        return bool(rect and rect.collidepoint(position))

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
    parser.add_argument("--windowed", action="store_true")
    parser.add_argument("--demo", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.demo and os.geteuid() != 0:
        raise SystemExit(
            "The live installer must run as root. Use --demo for a safe preview."
        )
    return InstallerApplication(
        root=args.root,
        payload=args.payload,
        payload_digest=args.payload_digest,
        windowed=args.windowed,
        demo=args.demo,
        hardware_controller=(
            None if args.demo else provisional_installer_hardware_controller()
        ),
    ).run()


if __name__ == "__main__":
    raise SystemExit(main())
