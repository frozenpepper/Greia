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

from .composition import provisional_installer_hardware_controller
from .disk import BlockDevice, DiskProbeError, LsblkDiskProbe
from .engine import (
    InstallProgress,
    InstallRequest,
    InstallResult,
    InstallationEngine,
    InstallationError,
)
from .power import PowerSupplyProbe


class InstallerPage(Enum):
    WELCOME = auto()
    TARGET = auto()
    SETTINGS = auto()
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
        self.payload_digest = payload_digest.resolve() if payload_digest is not None else None
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
        self._events: queue.Queue[InstallProgress | InstallResult | Exception] = queue.Queue()
        self._worker: threading.Thread | None = None
        self._hold_started: float | None = None
        self._buttons: dict[str, Any] = {}
        self._icon_cache: dict[tuple[str, int], Any] = {}
        self._exit_requested = False
        self._boot_released = False
        self._next_boot_handoff_attempt = 0.0

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
        controller = self.hardware_controller or provisional_installer_hardware_controller()
        display = controller.probe_display()
        return ("auto", *display.allowed_mode_ids)

    def run(self) -> int:
        import pygame

        os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
        pygame.init()
        pygame.font.init()
        flags = pygame.RESIZABLE if self.windowed else pygame.FULLSCREEN
        size = (1024, 600) if self.windowed else (0, 0)
        screen = pygame.display.set_mode(size, flags)
        pygame.display.set_caption("Install Greia OS")
        pygame.mouse.set_visible(True)
        clock = pygame.time.Clock()
        running = True
        while running and not self._exit_requested:
            self._drain_worker_events()
            for event in pygame.event.get():
                if event.type == pygame.QUIT and self.windowed:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    running = self._handle_key(event.key, pygame)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self._handle_mouse_down(event.pos)
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    self._handle_mouse_up(event.pos)
            self._update_install_hold(pygame)
            self._draw(screen, pygame)
            pygame.display.flip()
            if not self.windowed and os.environ.get("PIP_SKIP_BOOT_HANDOFF") != "1":
                self._release_boot_cover_once()
            clock.tick(30)
        pygame.quit()
        return 0

    def _handle_key(self, key: int, pygame: Any) -> bool:
        if self.windowed and key in {pygame.K_ESCAPE, pygame.K_q}:
            return False
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
            self.state.page = InstallerPage.TARGET
        elif self.state.page == InstallerPage.TARGET and self.state.target:
            self.state.page = InstallerPage.SETTINGS
        elif self.state.page == InstallerPage.SETTINGS:
            self.state.page = InstallerPage.CONFIRM
        elif self.state.page == InstallerPage.COMPLETE:
            if self.demo:
                self._exit_requested = True
            else:
                import subprocess

                # Never ask the parent to pull a mounted live USB. Power off
                # cleanly first; the USB can then be removed before the next boot.
                subprocess.run(["systemctl", "poweroff"], check=False, shell=False)

    def _back(self) -> None:
        previous = {
            InstallerPage.TARGET: InstallerPage.WELCOME,
            InstallerPage.SETTINGS: InstallerPage.TARGET,
            InstallerPage.CONFIRM: InstallerPage.SETTINGS,
            InstallerPage.ERROR: InstallerPage.CONFIRM,
        }
        self.state.page = previous.get(self.state.page, self.state.page)

    def _handle_mouse_down(self, position: tuple[int, int]) -> None:
        if self.state.page == InstallerPage.CONFIRM and self._inside("install", position):
            self._hold_started = time.monotonic()

    def _handle_mouse_up(self, position: tuple[int, int]) -> None:
        if self._inside("back", position):
            self._hold_started = None
            self._back()
            return
        if self.state.page == InstallerPage.CONFIRM:
            self._hold_started = None
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
            settings = replace(settings, natural_scrolling=not settings.natural_scrolling)
        elif self._inside("mouse-minus", position):
            settings = replace(settings, mouse_speed=max(-1.0, settings.mouse_speed - 0.25))
        elif self._inside("mouse-plus", position):
            settings = replace(settings, mouse_speed=min(1.0, settings.mouse_speed + 0.25))
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
        )

        def worker() -> None:
            try:
                result = engine.install(request, self._events.put)
                self._events.put(result)
            except Exception as exc:
                self._events.put(exc)

        self._worker = threading.Thread(target=worker, name="greia-installer", daemon=True)
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
        screen.fill(background)
        self._buttons.clear()
        font = pygame.font.Font(None, max(27, height // 22))
        title_font = pygame.font.Font(None, max(42, height // 12))
        small_font = pygame.font.Font(None, max(22, height // 28))

        main = pygame.Rect(max(24, width * 0.06), max(20, height * 0.06), width * 0.88, height * 0.88)
        pygame.draw.rect(screen, panel, main, border_radius=28)
        page = self.state.page
        if page == InstallerPage.WELCOME:
            self._center_title(screen, "Install Greia OS", title_font, text, main.top + 45)
            self._icon(screen, pygame, "robot", min(220, int(height * 0.38)), (width // 2, height // 2))
            self._button(screen, pygame, "primary", "Start", accent, text, font, (width // 2, main.bottom - 70), 260)
        elif page == InstallerPage.TARGET:
            self._center_title(screen, "Choose the internal disk", title_font, text, main.top + 32)
            if not self.state.targets:
                self._center_text(screen, "No safe internal disk was found.", font, danger, height // 2)
            for index, target in enumerate(self.state.targets[:4]):
                rect = pygame.Rect(main.left + 60, main.top + 120 + index * 86, main.width - 120, 68)
                selected = index == self.state.selected_target
                pygame.draw.rect(screen, accent if selected else background, rect, border_radius=18)
                pygame.draw.rect(screen, text, rect, width=3 if selected else 1, border_radius=18)
                self._buttons[f"target-{index}"] = rect
                label = font.render(target.display_name, True, text)
                screen.blit(label, label.get_rect(midleft=(rect.left + 24, rect.centery)))
            self._navigation(screen, pygame, font, accent, text, enabled=self.state.target is not None)
        elif page == InstallerPage.SETTINGS:
            self._center_title(screen, "Input and screen", title_font, text, main.top + 26)
            self._toggle_row(screen, pygame, "tap", "Tap touchpad to click", self.state.settings.touchpad_tap, font, text, accent, main.top + 110)
            self._toggle_row(screen, pygame, "natural", "Natural scrolling", self.state.settings.natural_scrolling, font, text, accent, main.top + 178)
            self._stepper_row(screen, pygame, "mouse", "Mouse speed", self.state.settings.mouse_speed, font, text, accent, main.top + 246)
            self._stepper_row(screen, pygame, "touch", "Touchpad speed", self.state.settings.touchpad_speed, font, text, accent, main.top + 314)
            self._value_row(screen, pygame, "resolution", "Screen resolution", self.state.settings.resolution, font, text, accent, main.top + 382)
            self._navigation(screen, pygame, font, accent, text, enabled=True)
        elif page == InstallerPage.CONFIRM:
            self._center_title(screen, "Ready to install", title_font, text, main.top + 34)
            target = self.state.target
            target_text = target.display_name if target else "Unknown disk"
            self._center_text(screen, target_text, font, text, main.top + 130)
            self._center_text(screen, "Everything currently on this disk will be erased.", font, danger, main.top + 190)
            self._center_text(screen, "Tap-to-click starts disabled and can be changed later.", small_font, text, main.top + 235)
            rect = self._button(screen, pygame, "install", "Hold to erase and install", danger, (255,255,255), font, (width // 2, main.bottom - 110), 390)
            if self._hold_started is not None:
                fraction = min(1.0, (time.monotonic() - self._hold_started) / self.HOLD_SECONDS)
                fill = rect.copy(); fill.width = int(rect.width * fraction)
                pygame.draw.rect(screen, (120, 24, 24), fill, border_radius=18)
                label = font.render("Keep holding…", True, (255,255,255))
                screen.blit(label, label.get_rect(center=rect.center))
            self._back_button(screen, pygame, font, accent, text)
        elif page == InstallerPage.INSTALLING:
            self._center_title(screen, "Installing", title_font, text, main.top + 50)
            self._icon(screen, pygame, "robot", min(180, int(height * 0.3)), (width // 2, main.top + 220))
            track = pygame.Rect(main.left + 100, main.bottom - 170, main.width - 200, 28)
            pygame.draw.rect(screen, background, track, border_radius=14)
            fill = track.copy(); fill.width = int(track.width * self.state.progress.fraction)
            pygame.draw.rect(screen, accent, fill, border_radius=14)
            self._center_text(screen, self.state.progress.detail, font, text, main.bottom - 105)
            self._center_text(screen, "Do not remove the USB key.", small_font, danger, main.bottom - 65)
        elif page == InstallerPage.COMPLETE:
            self._center_title(screen, "All done!", title_font, text, main.top + 28)
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
            recovery_code = result.grouped_recovery_code if result is not None else "CODE UNAVAILABLE"
            code_font = pygame.font.Font(None, max(33, height // 15))
            self._center_text(screen, recovery_code, code_font, danger, main.top + 305)
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
            self._center_title(screen, "Installation stopped", title_font, danger, main.top + 45)
            self._icon(screen, pygame, "close_button", min(160, int(height * 0.28)), (width // 2, main.top + 210))
            message = self.state.error + " The selected disk may be incomplete if installation had already begun."
            self._wrapped_text(screen, message, small_font, text, pygame.Rect(main.left + 100, main.top + 300, main.width - 200, 150))
            self._back_button(screen, pygame, font, accent, text)

    def _navigation(self, screen: Any, pygame: Any, font: Any, accent: tuple[int,int,int], text: tuple[int,int,int], *, enabled: bool) -> None:
        self._back_button(screen, pygame, font, accent, text)
        color = accent if enabled else (200, 195, 180)
        self._button(screen, pygame, "primary", "Continue", color, text, font, (screen.get_width() - 185, screen.get_height() - 70), 250)

    def _back_button(self, screen: Any, pygame: Any, font: Any, accent: tuple[int,int,int], text: tuple[int,int,int]) -> None:
        self._button(screen, pygame, "back", "Back", accent, text, font, (150, screen.get_height() - 70), 190)

    def _toggle_row(self, screen: Any, pygame: Any, key: str, label: str, value: bool, font: Any, text: tuple[int,int,int], accent: tuple[int,int,int], y: int) -> None:
        rect = pygame.Rect(screen.get_width() * 0.16, y, screen.get_width() * 0.68, 54)
        pygame.draw.rect(screen, (247,235,203), rect, border_radius=16)
        screen.blit(font.render(label, True, text), (rect.left + 18, rect.top + 13))
        state_rect = pygame.Rect(rect.right - 116, rect.top + 7, 98, 40)
        pygame.draw.rect(screen, accent if value else (180,175,165), state_rect, border_radius=20)
        knob_x = state_rect.right - 20 if value else state_rect.left + 20
        pygame.draw.circle(screen, (255,255,255), (knob_x, state_rect.centery), 15)
        self._buttons[key] = rect

    def _stepper_row(self, screen: Any, pygame: Any, key: str, label: str, value: float, font: Any, text: tuple[int,int,int], accent: tuple[int,int,int], y: int) -> None:
        rect = pygame.Rect(screen.get_width() * 0.16, y, screen.get_width() * 0.68, 54)
        pygame.draw.rect(screen, (247,235,203), rect, border_radius=16)
        screen.blit(font.render(label, True, text), (rect.left + 18, rect.top + 13))
        minus = pygame.Rect(rect.right - 210, rect.top + 6, 46, 42)
        plus = pygame.Rect(rect.right - 58, rect.top + 6, 46, 42)
        for button_rect, glyph in ((minus, "−"), (plus, "+")):
            pygame.draw.rect(screen, accent, button_rect, border_radius=14)
            glyph_image = font.render(glyph, True, text)
            screen.blit(glyph_image, glyph_image.get_rect(center=button_rect.center))
        value_image = font.render(f"{value:+.2f}", True, text)
        screen.blit(value_image, value_image.get_rect(center=(rect.right - 111, rect.centery)))
        self._buttons[f"{key}-minus"] = minus
        self._buttons[f"{key}-plus"] = plus

    def _value_row(self, screen: Any, pygame: Any, key: str, label: str, value: str, font: Any, text: tuple[int,int,int], accent: tuple[int,int,int], y: int) -> None:
        rect = pygame.Rect(screen.get_width() * 0.16, y, screen.get_width() * 0.68, 54)
        pygame.draw.rect(screen, (247,235,203), rect, border_radius=16)
        screen.blit(font.render(label, True, text), (rect.left + 18, rect.top + 13))
        value_rect = pygame.Rect(rect.right - 190, rect.top + 6, 172, 42)
        pygame.draw.rect(screen, accent, value_rect, border_radius=14)
        value_image = font.render(value, True, text)
        screen.blit(value_image, value_image.get_rect(center=value_rect.center))
        self._buttons[key] = rect

    def _button(self, screen: Any, pygame: Any, key: str, label: str, background: tuple[int,int,int], foreground: tuple[int,int,int], font: Any, center: tuple[int,int], width: int) -> Any:
        rect = pygame.Rect(0, 0, width, 58); rect.center = center
        pygame.draw.rect(screen, background, rect, border_radius=18)
        image = font.render(label, True, foreground)
        screen.blit(image, image.get_rect(center=rect.center))
        self._buttons[key] = rect
        return rect

    def _icon(self, screen: Any, pygame: Any, icon_id: str, size: int, center: tuple[int,int]) -> None:
        key = (icon_id, size)
        image = self._icon_cache.get(key)
        if image is None:
            path = self.root / "assets" / "icons" / "core" / "v1" / "256" / f"{icon_id}.png"
            image = pygame.image.load(str(path)).convert_alpha()
            image = pygame.transform.smoothscale(image, (size, size))
            self._icon_cache[key] = image
        screen.blit(image, image.get_rect(center=center))

    def _center_title(self, screen: Any, text_value: str, font: Any, color: tuple[int,int,int], y: int) -> None:
        image = font.render(text_value, True, color)
        screen.blit(image, image.get_rect(midtop=(screen.get_width() // 2, y)))

    def _center_text(self, screen: Any, text_value: str, font: Any, color: tuple[int,int,int], y: int) -> None:
        image = font.render(text_value, True, color)
        screen.blit(image, image.get_rect(center=(screen.get_width() // 2, y)))

    def _wrapped_text(self, screen: Any, text_value: str, font: Any, color: tuple[int,int,int], rect: Any) -> None:
        words = text_value.split(); line = ""; y = rect.top
        for word in words:
            candidate = f"{line} {word}".strip()
            if font.size(candidate)[0] > rect.width and line:
                screen.blit(font.render(line, True, color), (rect.left, y)); y += font.get_linesize()
                line = word
            else:
                line = candidate
        if line:
            screen.blit(font.render(line, True, color), (rect.left, y))

    def _inside(self, key: str, position: tuple[int,int]) -> bool:
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

            completed = subprocess.run([str(helper)], check=False, shell=False)
            self._boot_released = completed.returncode == 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(os.environ.get("GREIA_OS_ROOT", "/opt/greia-os")))
    parser.add_argument("--payload", type=Path, default=Path("/run/live/medium/payload/pip-rootfs.squashfs"))
    parser.add_argument("--payload-digest", type=Path)
    parser.add_argument("--windowed", action="store_true")
    parser.add_argument("--demo", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.demo and os.geteuid() != 0:
        raise SystemExit("The live installer must run as root. Use --demo for a safe preview.")
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
