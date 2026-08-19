from __future__ import annotations

import os
import subprocess
import threading
from pathlib import Path
from typing import Any

from greia_platform.system_language import (
    DEFAULT_SYSTEM_LOCALE,
    SUPPORTED_SYSTEM_LANGUAGES,
    system_language,
)
from greia_platform.typography import FontRole, GreiaTypography

from .composition import provisional_installer_hardware_controller
from .engine import InstallRequest, InstallationEngine
from .i18n import LocalizedTypography
from .main import (
    DemoInstallationEngine,
    InstallerApplication,
    InstallerPage,
    parse_args,
)


class LanguageFirstInstallerApplication(InstallerApplication):
    """Existing Greia installer with one selected device locale bound to install."""

    def __init__(self, *args: object, locale: str, **kwargs: object) -> None:
        self.locale = system_language(locale).locale
        super().__init__(*args, **kwargs)
        # Keep the existing installer state/layout implementation intact. All
        # installer-owned visible copy already flows through this typography
        # object, so localization belongs at this presentation seam rather than
        # in disk/network/destructive-install code.
        self._typography = LocalizedTypography(self._typography, self.locale)

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
            locale=self.locale,
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


def choose_language(*, root: Path, windowed: bool, demo: bool) -> str:
    """Run the installer's mandatory first flag-first language screen."""

    import pygame

    pygame.init()
    pygame.font.init()
    flags = pygame.RESIZABLE if (windowed or demo) else pygame.FULLSCREEN
    if windowed or demo:
        screen = pygame.display.set_mode((1024, 600), flags)
    else:
        screen = pygame.display.set_mode((0, 0), flags)
    pygame.display.set_caption("Greia OS Installer — Language")
    # The legacy-X/Acer path does not reliably provide a visible system cursor.
    # Match the normal installer: hide it and draw Greia's own pointer after
    # every frame while continuing to use SDL's authoritative mouse position.
    pygame.mouse.set_visible(False)
    typography = GreiaTypography(root / "assets" / "fonts" / "nunito-sans")
    pointer = _load_pointer(root, pygame)
    selected_index = next(
        (
            index
            for index, item in enumerate(SUPPORTED_SYSTEM_LANGUAGES)
            if item.locale == DEFAULT_SYSTEM_LOCALE
        ),
        0,
    )
    clock = pygame.time.Clock()
    first_frame = True

    try:
        while True:
            width, height = screen.get_size()
            screen.fill((247, 235, 203))
            panel = pygame.Rect(
                max(18, int(width * 0.045)),
                max(16, int(height * 0.045)),
                int(width * 0.91),
                int(height * 0.91),
            )
            pygame.draw.rect(screen, (255, 250, 240), panel, border_radius=28)
            title = typography.render(
                "Choose your language",
                FontRole.TITLE,
                max(30, min(44, height // 13)),
                (61, 44, 31),
            )
            screen.blit(title, title.get_rect(center=(panel.centerx, panel.top + 42)))
            hint = typography.render(
                "Language  •  Lingua  •  Idioma  •  Langue",
                FontRole.BODY,
                max(17, min(22, height // 28)),
                (118, 104, 93),
            )
            screen.blit(hint, hint.get_rect(center=(panel.centerx, panel.top + 78)))

            columns = 3 if width >= 760 else 2
            count = len(SUPPORTED_SYSTEM_LANGUAGES)
            rows = (count + columns - 1) // columns
            gap = max(8, min(14, width // 80))
            grid_left = panel.left + max(18, width // 28)
            grid_right = panel.right - max(18, width // 28)
            grid_top = panel.top + 104
            button_h = max(42, min(54, height // 10))
            continue_h = max(44, min(54, height // 10))
            available_h = panel.bottom - grid_top - continue_h - 34
            row_h = max(button_h, available_h // max(1, rows))
            cell_w = (grid_right - grid_left - gap * (columns - 1)) // columns
            hit_targets: list[tuple[int, Any]] = []
            pointer_position = pygame.mouse.get_pos()

            for index, language in enumerate(SUPPORTED_SYSTEM_LANGUAGES):
                row, column = divmod(index, columns)
                cell = pygame.Rect(
                    grid_left + column * (cell_w + gap),
                    grid_top + row * row_h,
                    cell_w,
                    button_h,
                )
                selected = index == selected_index
                hovered = cell.collidepoint(pointer_position)
                pygame.draw.rect(
                    screen,
                    (255, 194, 52)
                    if selected
                    else ((252, 241, 211) if hovered else (247, 235, 203)),
                    cell,
                    border_radius=16,
                )
                pygame.draw.rect(
                    screen,
                    (61, 44, 31),
                    cell,
                    width=3 if selected else (2 if hovered else 1),
                    border_radius=16,
                )
                flag = typography.render(
                    language.flag,
                    FontRole.DISPLAY,
                    max(24, min(34, button_h - 14)),
                    (61, 44, 31),
                )
                screen.blit(flag, flag.get_rect(midleft=(cell.left + 14, cell.centery)))
                label = typography.render(
                    language.name,
                    FontRole.CONTROL,
                    max(16, min(21, height // 30)),
                    (61, 44, 31),
                )
                screen.blit(
                    label,
                    label.get_rect(midleft=(cell.left + 62, cell.centery)),
                )
                hit_targets.append((index, cell))

            continue_rect = pygame.Rect(0, 0, min(240, panel.width // 3), continue_h)
            continue_rect.midbottom = (panel.centerx, panel.bottom - 14)
            pygame.draw.rect(screen, (255, 194, 52), continue_rect, border_radius=18)
            continue_label = typography.render(
                "Continue",
                FontRole.CONTROL,
                max(19, min(24, height // 25)),
                (61, 44, 31),
            )
            screen.blit(continue_label, continue_label.get_rect(center=continue_rect.center))
            _draw_pointer(screen, pygame, pointer)

            pygame.display.flip()
            if first_frame:
                first_frame = False
                _release_boot_cover()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    if demo:
                        return SUPPORTED_SYSTEM_LANGUAGES[selected_index].locale
                    continue
                if event.type == pygame.VIDEORESIZE and (windowed or demo):
                    screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    for index, rect in hit_targets:
                        if rect.collidepoint(event.pos):
                            selected_index = index
                            break
                    if continue_rect.collidepoint(event.pos):
                        return SUPPORTED_SYSTEM_LANGUAGES[selected_index].locale
                elif event.type == pygame.KEYDOWN:
                    if event.key in {pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE}:
                        return SUPPORTED_SYSTEM_LANGUAGES[selected_index].locale
                    if event.key in {pygame.K_RIGHT, pygame.K_TAB}:
                        selected_index = (selected_index + 1) % count
                    elif event.key == pygame.K_LEFT:
                        selected_index = (selected_index - 1) % count
                    elif event.key == pygame.K_DOWN:
                        selected_index = min(count - 1, selected_index + columns)
                    elif event.key == pygame.K_UP:
                        selected_index = max(0, selected_index - columns)
            clock.tick(60)
    finally:
        typography.clear()
        pygame.display.quit()
        pygame.quit()


def _load_pointer(root: Path, pygame: Any) -> Any | None:
    path = root / "assets" / "icons" / "core" / "v1" / "256" / "yellow_star.png"
    try:
        image = pygame.image.load(str(path)).convert_alpha()
        return pygame.transform.smoothscale(image, (34, 34))
    except (OSError, pygame.error):
        return None


def _draw_pointer(screen: Any, pygame: Any, pointer: Any | None) -> None:
    x, y = pygame.mouse.get_pos()
    if pointer is not None:
        screen.blit(pointer, pointer.get_rect(center=(x, y)))
        return
    # Resource failure must not make the first installer screen mouse-invisible.
    pygame.draw.circle(screen, (255, 194, 52), (x, y), 10)
    pygame.draw.circle(screen, (61, 44, 31), (x, y), 10, width=2)


def _release_boot_cover() -> None:
    helper = "/usr/local/lib/greia-os/release-boot-cover"
    if not os.path.exists(helper):
        return
    subprocess.run(
        [helper],
        check=False,
        shell=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def main() -> int:
    args = parse_args()
    if not args.demo and os.geteuid() != 0:
        raise SystemExit(
            "The live installer must run as root. Use --demo for a safe preview."
        )
    locale = choose_language(root=args.root, windowed=args.windowed, demo=args.demo)
    return LanguageFirstInstallerApplication(
        root=args.root,
        payload=args.payload,
        payload_digest=args.payload_digest,
        windowed=args.windowed,
        demo=args.demo,
        locale=locale,
        hardware_controller=(
            None if args.demo else provisional_installer_hardware_controller()
        ),
    ).run()


if __name__ == "__main__":
    raise SystemExit(main())
