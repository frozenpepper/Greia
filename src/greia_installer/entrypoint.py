from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

from greia_platform.system_language import (
    DEFAULT_SYSTEM_LOCALE,
    SUPPORTED_SYSTEM_LANGUAGES,
    system_language,
)
from greia_platform.typography import GreiaTypography

from .boot_intro import InstallerIntro
from .composition import provisional_installer_hardware_controller
from .i18n import InstallerTranslator, LocalizedTypography
from .presentation import (
    COCOA,
    FIELD,
    INK,
    SUNSHINE,
    SURFACE,
    InstallerLook,
    mix,
    page_frame,
)
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


class LanguageChooser:
    """The installer's mandatory first screen: one big tile per language.

    Drawn with the installer look (meadow, Leo, kit tiles) and laid out as a
    paginated 2-column grid so all languages remain child/parent-sized at
    800x480 and 1024x600. Flags are drawn shapes rather than emoji glyphs:
    the bundled fonts have no flag glyphs, which left an empty gap. The
    Continue label follows the highlighted language so a parent who cannot
    read English still recognises it.

    Selection needs a press *and* release on the same screen: the press that
    skipped the start-up animation is consumed there, and its release must
    not pick a language.
    """

    def __init__(
        self,
        *,
        root: Path,
        typography: GreiaTypography | None = None,
        languages: tuple = SUPPORTED_SYSTEM_LANGUAGES,
    ) -> None:
        self.root = Path(root)
        self.languages = tuple(languages)
        self.typography = typography or GreiaTypography(self.root / "assets" / "fonts" / "nunito-sans")
        self.look = InstallerLook(self.root, self.typography)
        self.selected_index = next(
            (
                index
                for index, item in enumerate(self.languages)
                if item.locale == DEFAULT_SYSTEM_LOCALE
            ),
            0,
        )
        self.columns = 2
        self.page_size = 4  # bounded two-row grid on the smallest supported screen
        self._targets: dict[str, Any] = {}
        self._pressed = False

    def hit_targets(self) -> dict[str, Any]:
        return dict(self._targets)

    @property
    def locale(self) -> str:
        return self.languages[self.selected_index].locale

    def draw(self, screen: Any, pygame: Any, *, pointer_position: tuple[int, int]) -> None:
        width, height = screen.get_size()
        frame = page_frame(pygame, (width, height), steps=False)
        main = frame.main
        title_px = max(26, min(38, height // 16))
        y = self.look.page_base(
            screen,
            pygame,
            frame,
            title=InstallerTranslator(self.locale).text("Choose your language"),
            title_size=title_px,
            pose="pose_wave",
        )
        self._targets = {}
        page_start = (self.selected_index // self.page_size) * self.page_size
        visible = self.languages[page_start:page_start + self.page_size]
        count = len(visible)
        columns = self.columns if count > 1 else 1
        rows = (count + columns - 1) // columns
        gap = max(10, min(18, width // 60))
        nav_center = main.bottom - 40
        top = y + max(14, height // 30)
        avail = nav_center - 25 - 16 - top
        tile_h = max(54, min(96, (avail - gap * (rows - 1)) // max(1, rows)))
        grid_h = rows * tile_h + (rows - 1) * gap
        top += max(0, (avail - grid_h) // 2)
        cell_w = (main.width - gap * (columns - 1)) // columns
        label_px = max(18, min(28, tile_h // 3))
        for offset, language in enumerate(visible):
            index = page_start + offset
            row, column = divmod(offset, columns)
            cell = pygame.Rect(main.left + column * (cell_w + gap), top + row * (tile_h + gap), cell_w, tile_h)
            selected = index == self.selected_index
            hovered = cell.collidepoint(pointer_position)
            fill = SUNSHINE if selected else (mix(SURFACE, SUNSHINE, 0.2) if hovered else FIELD)
            self.look.panel(screen, cell, fill, width=3 if selected else 2)
            flag_h = max(24, min(48, tile_h - 30))
            flag = pygame.Rect(0, 0, int(flag_h * 1.5), flag_h)
            flag.midleft = (cell.left + 16, cell.centery)
            _draw_flag(screen, pygame, language.locale, flag)
            label = self.look.label(
                language.native_name,
                label_px,
                COCOA,
                max_width=cell.right - flag.right - 26,
            )
            screen.blit(label, label.get_rect(midleft=(flag.right + 14, cell.centery)))
            if selected:
                self.look.focus(screen, cell)
            self._targets[f"language-{index}"] = cell
        continue_label = InstallerTranslator(self.locale).text("Continue")
        button = pygame.Rect(0, 0, max(170, min(260, int(main.width * 0.36))), 50)
        button.midright = (main.right, nav_center)
        self.look.pill(screen, button, continue_label, fill=SUNSHINE, size=max(18, min(25, height // 25)))
        self._targets["continue"] = button
        if len(self.languages) > self.page_size:
            page = page_start // self.page_size
            pages = (len(self.languages) + self.page_size - 1) // self.page_size
            nav_y = nav_center - 25
            if page > 0:
                previous = pygame.Rect(main.left, nav_y, 88, 50)
                self.look.pill(screen, previous, "Prev", fill=FIELD, size=18)
                self._targets["page-prev"] = previous
            if page + 1 < pages:
                following = pygame.Rect(main.left + 96, nav_y, 88, 50)
                self.look.pill(screen, following, "Next", fill=FIELD, size=18)
                self._targets["page-next"] = following

    def handle_event(self, event: Any, pygame: Any) -> str | None:
        """Apply one event; return the chosen locale when the parent confirms."""

        count = len(self.languages)
        if event.type == pygame.MOUSEBUTTONDOWN and getattr(event, "button", 0) == 1:
            self._pressed = True
        elif event.type == pygame.MOUSEBUTTONUP and getattr(event, "button", 0) == 1:
            if not self._pressed:
                return None
            self._pressed = False
            for key, rect in self._targets.items():
                if key == "page-prev" and rect.collidepoint(event.pos):
                    self.selected_index = max(0, (self.selected_index // self.page_size - 1) * self.page_size)
                    return None
                if key == "page-next" and rect.collidepoint(event.pos):
                    self.selected_index = min(len(self.languages) - 1, (self.selected_index // self.page_size + 1) * self.page_size)
                    return None
                if key.startswith("language-") and rect.collidepoint(event.pos):
                    self.selected_index = int(key.split("-", 1)[1])
                    return None
            target = self._targets.get("continue")
            if target is not None and target.collidepoint(event.pos):
                return self.locale
        elif event.type == pygame.KEYDOWN:
            if event.key in {pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE}:
                return self.locale
            if event.key in {pygame.K_RIGHT, pygame.K_TAB}:
                self.selected_index = (self.selected_index + 1) % count
            elif event.key == pygame.K_LEFT:
                self.selected_index = (self.selected_index - 1) % count
            elif event.key == pygame.K_DOWN:
                self.selected_index = min(count - 1, self.selected_index + self.columns)
            elif event.key == pygame.K_UP:
                self.selected_index = max(0, self.selected_index - self.columns)
        return None


def _draw_flag(screen: Any, pygame: Any, locale: str, rect: Any) -> None:
    """Simple drawn flag for a language tile (shapes, not emoji glyphs)."""

    white = (255, 255, 255)
    if locale == "it":
        bands = ((0, 146, 70), white, (206, 43, 55))
    elif locale == "fr":
        bands = ((0, 85, 164), white, (239, 65, 53))
    else:
        bands = ()
    if bands:
        third = rect.width / 3
        for index, color in enumerate(bands):
            pygame.draw.rect(
                screen, color, (rect.left + round(index * third), rect.top, round(third) + 1, rect.height)
            )
    elif locale == "es":
        red, yellow = (198, 11, 30), (255, 196, 0)
        pygame.draw.rect(screen, red, rect)
        pygame.draw.rect(screen, yellow, (rect.left, rect.top + rect.height // 4, rect.width, rect.height // 2))
    elif locale == "en":
        blue, red = (1, 33, 105), (200, 16, 46)
        pygame.draw.rect(screen, blue, rect)
        thick = max(3, rect.height // 5)
        pygame.draw.line(screen, white, rect.topleft, rect.bottomright, thick)
        pygame.draw.line(screen, white, rect.bottomleft, rect.topright, thick)
        pygame.draw.line(screen, red, rect.topleft, rect.bottomright, max(1, thick // 3))
        pygame.draw.line(screen, red, rect.bottomleft, rect.topright, max(1, thick // 3))
        pygame.draw.rect(screen, white, (rect.centerx - thick, rect.top, 2 * thick, rect.height))
        pygame.draw.rect(screen, white, (rect.left, rect.centery - thick, rect.width, 2 * thick))
        inner = max(2, thick * 2 // 3)
        pygame.draw.rect(screen, red, (rect.centerx - inner // 2 - 1, rect.top, inner + 1, rect.height))
        pygame.draw.rect(screen, red, (rect.left, rect.centery - inner // 2 - 1, rect.width, inner + 1))
    else:
        pygame.draw.rect(screen, SURFACE, rect)
        badge = pygame.font.Font(None, max(18, rect.height // 2)).render(locale.split("-")[0].upper(), True, INK)
        screen.blit(badge, badge.get_rect(center=rect.center))
    pygame.draw.rect(screen, INK, rect, width=2, border_radius=3)


def choose_language(*, root: Path, windowed: bool, demo: bool) -> str:
    """Play the start-up animation, then run the flag-first language screen."""

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
    pointer = _load_pointer(root, pygame)

    # The Greia logo animation the installed OS plays at boot, shared through
    # greia_platform.boot_animation. Its first flip continues the early-boot
    # splash, so that is where the boot cover is released.
    _write_boot_status("intro")
    released = {"cover": False}

    def _first_frame() -> None:
        released["cover"] = True
        _release_boot_cover()

    try:
        InstallerIntro.for_root(root).run(screen, pygame, on_first_frame=_first_frame)
    except Exception:  # noqa: BLE001 - presentation never blocks installation
        pass
    _write_boot_status("language")

    chooser = LanguageChooser(root=root)
    clock = pygame.time.Clock()
    first_frame = True
    dirty = True
    try:
        while True:
            pointer_position = pygame.mouse.get_pos()
            if dirty:
                chooser.draw(screen, pygame, pointer_position=pointer_position)
                _draw_pointer(screen, pygame, pointer)
                pygame.display.flip()
                dirty = False
            if first_frame:
                first_frame = False
                if not released["cover"]:
                    _release_boot_cover()

            for event in pygame.event.get():
                dirty = True
                if event.type == pygame.QUIT:
                    if demo:
                        return chooser.locale
                    continue
                if event.type == pygame.VIDEORESIZE and (windowed or demo):
                    screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)
                    continue
                chosen = chooser.handle_event(event, pygame)
                if chosen is not None:
                    return chosen
            clock.tick(60)
    finally:
        chooser.look.clear()
        chooser.typography.clear()
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
