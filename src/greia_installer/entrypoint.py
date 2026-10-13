from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

from greia_platform.system_language import (
    DEFAULT_SYSTEM_LOCALE,
    SUPPORTED_SYSTEM_LANGUAGES,
    system_language,
)
from greia_platform.typography import FontRole, GreiaTypography

from .composition import provisional_installer_hardware_controller
from .i18n import LocalizedTypography
from .main import (
    InstallerApplication,
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

    def _snapshot_locale(self) -> str:
        """Carry the language-first selection into the transaction snapshot."""
        return self.locale


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
                "Choose a language",
                FontRole.TITLE,
                max(30, min(44, height // 13)),
                (61, 44, 31),
            )
            screen.blit(title, title.get_rect(center=(panel.centerx, panel.top + 42)))
            hint = typography.render(
                "Language  •  Lingua",
                FontRole.BODY,
                max(17, min(22, height // 28)),
                (118, 104, 93),
            )
            screen.blit(hint, hint.get_rect(center=(panel.centerx, panel.top + 78)))

            count = len(SUPPORTED_SYSTEM_LANGUAGES)
            # The previous 12-language 3x4 table left two very wide, tiny
            # buttons stranded at the top once only EN/IT became selectable.
            # Keep the product choice group centered and child/parent-sized.
            columns = min(count, 2 if width >= 540 else 1)
            rows = (count + columns - 1) // columns
            gap = max(8, min(14, width // 80))
            grid_available = panel.width - 2 * max(18, width // 28)
            grid_width = min(grid_available, 620 if columns == 2 else 380)
            grid_left = panel.centerx - grid_width // 2
            grid_right = grid_left + grid_width
            button_h = max(44, min(66, height // 7))
            continue_h = max(44, min(54, height // 10))
            row_h = button_h + gap
            group_h = rows * row_h - gap + continue_h + 36
            grid_top = max(panel.top + 98, panel.centery - group_h // 2)
            # At unusually short resolutions the button must remain inside
            # the actual viewport rather than moving behind Continue.
            grid_top = min(grid_top, panel.bottom - group_h - 14)
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
                    language.native_name,
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
            continue_rect.midtop = (panel.centerx, grid_top + rows * row_h + 26)
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
    return None


def _draw_pointer(screen: Any, pygame: Any, pointer: Any | None = None) -> None:
    if not pygame.mouse.get_focused():
        return
    from greia_platform.activity_ui import draw_activity_pointer

    pos = pygame.mouse.get_pos()
    draw_activity_pointer(screen, pos)


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


#: Where the installer publishes what it is currently showing, so a failure can
#: be read over the developer remote surface instead of transcribed by hand
#: from the framebuffer. Written from process start, because the language
#: chooser runs its own loop before the installer's, and a reader otherwise
#: sees an empty runtime directory and cannot tell "stuck at the language
#: screen" from "not started". Bounded, and carries only what is on screen.
INSTALLER_STATUS_PATH = Path("/run/greia-installer/status.json")


def _write_boot_status(stage: str) -> None:
    """Publish a one-line boot-stage record; never raise."""

    try:
        INSTALLER_STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
        INSTALLER_STATUS_PATH.write_text(
            json.dumps(
                {
                    "page": stage,
                    "phase": stage,
                    "fraction": 0.0,
                    "detail": "",
                    "error": "",
                    "monotonic": round(time.monotonic(), 3),
                }
            ),
            encoding="utf-8",
        )
    except Exception:  # noqa: BLE001 - a diagnostic must never break start-up
        return


def main() -> int:
    args = parse_args()
    _write_boot_status("starting")
    # Step 8A.5: the graphical UI is unprivileged by design (see
    # greia-installer-ui.service); destruction lives only in the root
    # transaction service behind nonce+digest. Use --demo for the
    # zero-disk-contact simulation.
    _write_boot_status("language")
    locale = choose_language(root=args.root, windowed=args.windowed, demo=args.demo)
    return LanguageFirstInstallerApplication(
        root=args.root,
        payload=args.payload,
        payload_digest=args.payload_digest,
        windowed=args.windowed,
        demo=args.demo,
        locale=locale,
        transaction_socket=args.transaction_socket,
        target_profile=args.target_profile,
        hardware_controller=(
            None if args.demo else provisional_installer_hardware_controller()
        ),
    ).run()


if __name__ == "__main__":
    raise SystemExit(main())
