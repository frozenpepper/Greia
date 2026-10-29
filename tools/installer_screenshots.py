"""Render every Greia installer page/state to PNG for layout review.

The installer draws straight onto the framebuffer of a machine that is about
to be erased, so its layout used to be reviewed only by photographing the
reference Acer, in one language, at one resolution. This renders every page
and the interesting states of each page (layout probe vs. selector, Wi-Fi
scanning/list/password/connected/unavailable/error, the held erase button,
progress, success and failure) offscreen through the real installer drawing
code, in the selectable languages, at the reference 1024x600 panel and a
cramped 800x480 panel, and writes one PNG per state plus an optional contact
sheet.

It also reports silent layout faults per state: registered hit targets that
overlap each other or leave the screen, text drawn below the installer's
readability floor (``presentation.text_floors``: 16 px helper text at 600 px
high, 15 px at 480), kit labels still too wide for their box at that floor,
and translated copy cut with an ellipsis. All are invisible in code review
because the offending size comes from runtime copy.

Run directly (headless, touches no disk, network or audio):

    SDL_VIDEODRIVER=dummy PYTHONPATH=src \\
        python3 tools/installer_screenshots.py --out ~/.cache/installer-shots \\
        --sheet ~/.cache/installer-shots/sheet.png

Not part of ``make verify``: it needs a writable output directory. A smoke
test (``tests/test_installer_screenshots.py``) runs a reduced matrix in the
suite.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = str(REPO_ROOT / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame  # noqa: E402 - needs the SDL driver chosen above

from greia_installer.entrypoint import LanguageFirstInstallerApplication  # noqa: E402
from greia_installer.main import InstallerPage  # noqa: E402
from greia_installer.engine import InstallProgress  # noqa: E402
from greia_installer.presentation import text_floors  # noqa: E402
from greia_platform.hardware import DisplayMode  # noqa: E402
from greia_platform.hardware_session import (  # noqa: E402
    ApplyResult,
    DisplayProbe,
    PointerCapabilities,
    PointerDeviceInfo,
    PointerKind,
)
from greia_platform.wifi import (  # noqa: E402
    WifiNetwork,
    WifiSecurity,
    WifiSetupPhase,
    WifiSetupSnapshot,
)

SIZES: tuple[tuple[int, int], ...] = ((1024, 600), (800, 480))
LOCALES: tuple[str, ...] = ("en", "it", "es", "fr")


class _PreviewController:
    """Hardware double: a touchpad + mouse and a 1024x600 panel, no side effects."""

    backend_id = "screenshot-preview"

    def topology_token(self) -> tuple[str, ...]:
        return ("screenshot-preview",)

    def probe_pointers(self) -> tuple[PointerDeviceInfo, ...]:
        return (
            PointerDeviceInfo(
                kind=PointerKind.TOUCHPAD,
                label="Touchpad",
                capabilities=PointerCapabilities(
                    supports_tap=True,
                    supports_natural_scrolling=True,
                    supports_disable_while_typing=True,
                    supports_speed=True,
                ),
            ),
            PointerDeviceInfo(
                kind=PointerKind.MOUSE,
                label="Mouse",
                capabilities=PointerCapabilities(
                    supports_natural_scrolling=True, supports_speed=True
                ),
            ),
        )

    def probe_display(self) -> DisplayProbe:
        return DisplayProbe(
            "panel-0", (DisplayMode(1024, 600, 60.0, preferred=True, current=True),)
        )

    def apply_pointer_settings(self, settings: Any) -> ApplyResult:
        return ApplyResult(True, self.probe_display(), ("preview",))


_NETWORKS = (
    WifiNetwork("Casa Rossi", WifiSecurity.PERSONAL, -41.0, "/net/connman/iwd/demo/1"),
    WifiNetwork("Biblioteca Ospiti", WifiSecurity.OPEN, -60.0, "/net/connman/iwd/demo/2"),
    WifiNetwork("Scuola Enterprise", WifiSecurity.ENTERPRISE, -70.0, "/net/connman/iwd/demo/3"),
    WifiNetwork("Vicino di casa 5G", WifiSecurity.PERSONAL, -80.0, "/net/connman/iwd/demo/4"),
)


class _ScriptedWifi:
    """Stand-in for ``WifiSetupController`` exposing a fixed snapshot only."""

    def __init__(self, snapshot: WifiSetupSnapshot, profile: Any = None) -> None:
        self.snapshot = snapshot
        self.profile = profile

    def drain(self) -> None:
        return None


@dataclass(frozen=True, slots=True)
class _ProfileStub:
    ssid: str


def _wifi(phase: WifiSetupPhase, *, networks=_NETWORKS, index=0, passphrase="",
          connected="", error="", profile=None) -> _ScriptedWifi:
    return _ScriptedWifi(
        WifiSetupSnapshot(
            phase=phase,
            networks=tuple(networks),
            selected_index=index,
            passphrase=passphrase,
            connected_ssid=connected,
            error=error,
        ),
        profile,
    )


Setup = Callable[[Any], None]


def _page(page: InstallerPage) -> Setup:
    def setup(app: Any) -> None:
        app.state.page = page

    return setup


def _layout_probe(pressed: int) -> Setup:
    def setup(app: Any) -> None:
        app.state.page = InstallerPage.LAYOUT
        app._layout_probe_results = {
            character: (4 + index, False, "")
            for index, character in enumerate("qwzy/@"[:pressed])
        }

    return setup


def _layout_selector(app: Any) -> None:
    app.state.page = InstallerPage.LAYOUT
    app._layout_probe_results = {c: (4 + i, False, "") for i, c in enumerate("qwzy/")}
    app._refresh_layout_candidates()


def _no_target(app: Any) -> None:
    app.state.page = InstallerPage.TARGET
    app.state.targets = ()


def _target_changed(app: Any) -> None:
    app.state.page = InstallerPage.TARGET
    app.state.error = "The selected disk changed; choose the internal disk again"


def _wifi_state(wifi: _ScriptedWifi) -> Setup:
    def setup(app: Any) -> None:
        app.state.page = InstallerPage.WIFI
        app.wifi = wifi

    return setup


def _wifi_ssh_state(*, enabled: bool = False, busy: bool = False, error: bool = False) -> Setup:
    def setup(app: Any) -> None:
        from greia_installer.live_ssh import LiveSshSnapshot
        _wifi_state(_wifi(WifiSetupPhase.READY, passphrase="segreto"))(app)
        app._live_ssh.snapshot = LiveSshSnapshot(enabled, busy, error)
    return setup


def _confirm(*, holding: bool = False, wifi_ssid: str | None = None,
             keyboard: bool = False) -> Setup:
    def setup(app: Any) -> None:
        app.state.page = InstallerPage.CONFIRM
        if wifi_ssid is not None:
            app.wifi = _wifi(WifiSetupPhase.CONNECTED, connected=wifi_ssid,
                             profile=_ProfileStub(wifi_ssid))
        if keyboard:
            # Tab moved focus to the erase control (Enter alone never does).
            app._confirm_visit_page = InstallerPage.CONFIRM
            app._confirm_focus = "install"
            app._confirm_keyboard = True
        if holding:
            # Half way through the two-second hold.
            app._hold_started = time.monotonic() - app.HOLD_SECONDS / 2

    return setup


def _installing(fraction: float, stage: str, detail: str, *,
                phase_fraction: float | None = None, stalled_for: float = 0.0) -> Setup:
    def setup(app: Any) -> None:
        app.state.page = InstallerPage.INSTALLING
        app.state.progress = InstallProgress(fraction, stage, detail, phase_fraction)
        now = time.monotonic()
        app._installing_since = now - 200.0
        app._phase_since = now - max(5.0, stalled_for)
        app._last_progress_at = now - stalled_for

    return setup


def _error(message: str) -> Setup:
    def setup(app: Any) -> None:
        app.state.page = InstallerPage.ERROR
        app.state.error = message

    return setup


#: (state id, setup). Order is the parent's journey through the installer.
SCENARIOS: tuple[tuple[str, Setup], ...] = (
    ("02-welcome", _page(InstallerPage.WELCOME)),
    ("03-keyboard-probe", _layout_probe(0)),
    ("04-keyboard-probe-3", _layout_probe(3)),
    ("05-keyboard-list", _layout_selector),
    ("06-disk", _page(InstallerPage.TARGET)),
    ("07-disk-none", _no_target),
    ("08-disk-changed", _target_changed),
    ("09-pointer", _page(InstallerPage.POINTER)),
    ("10-display", _page(InstallerPage.DISPLAY)),
    ("11-wifi-scanning", _wifi_state(_wifi(WifiSetupPhase.SCANNING, networks=()))),
    ("11a-wifi-ssh-off", _wifi_ssh_state()),
    ("11b-wifi-ssh-on", _wifi_ssh_state(enabled=True)),
    ("11c-wifi-ssh-busy", _wifi_ssh_state(busy=True)),
    ("11d-wifi-ssh-error", _wifi_ssh_state(error=True)),
    ("12-wifi-password", _wifi_state(_wifi(WifiSetupPhase.READY, passphrase="segreto"))),
    ("13-wifi-open", _wifi_state(_wifi(WifiSetupPhase.READY, index=1))),
    ("14-wifi-enterprise", _wifi_state(_wifi(WifiSetupPhase.READY, index=2))),
    ("15-wifi-page2", _wifi_state(_wifi(WifiSetupPhase.READY, index=3))),
    ("16-wifi-wrong-password", _wifi_state(_wifi(
        WifiSetupPhase.ERROR, passphrase="abc",
        error="Wi-Fi password must be at least 8 characters."))),
    ("17-wifi-connecting", _wifi_state(_wifi(WifiSetupPhase.CONNECTING))),
    ("18-wifi-connected", _wifi_state(_wifi(
        WifiSetupPhase.CONNECTED, connected="Casa Rossi", profile=_ProfileStub("Casa Rossi")))),
    ("19-wifi-none", _wifi_state(_wifi(WifiSetupPhase.READY, networks=()))),
    ("20-wifi-scan-failed", _wifi_state(_wifi(
        WifiSetupPhase.ERROR, networks=(), error="iwd D-Bus service is unavailable"))),
    ("21-wifi-unavailable", _wifi_state(_wifi(WifiSetupPhase.UNAVAILABLE, networks=()))),
    ("22-confirm", _confirm()),
    ("23-confirm-wifi-holding", _confirm(holding=True, wifi_ssid="Casa Rossi")),
    ("23k-confirm-keyboard-hold", _confirm(holding=True, keyboard=True)),
    ("24-installing-start", _installing(0.02, "prepare", "Confirming the selected disk")),
    ("24s-installing-stalled", _installing(
        0.04, "check", "Checking the installation files", stalled_for=95.0)),
    ("25-installing", _installing(0.42, "copy", "Copying the system", phase_fraction=0.42)),
    ("25v-installing-verify", _installing(
        0.80, "verify", "Checking the installed system", phase_fraction=0.67)),
    ("26-complete", _page(InstallerPage.COMPLETE)),
    ("27-error", _error("selected disk identity changed; installation stopped")),
    ("28-error-power", _error(
        "Connect the power adapter before installing (battery is 30%).")),
)


@dataclass(frozen=True, slots=True)
class ShotReport:
    """Where one state was written and which layout faults it showed.

    ``min_text_px`` is the smallest font size any non-empty text was drawn
    at; ``text_floor_px`` is the readability floor for that viewport. A
    state whose ``min_text_px`` is below the floor is a fault.
    """

    path: Path
    overlaps: tuple[tuple[str, str], ...]
    offscreen: tuple[str, ...]
    min_text_px: int | None = None
    text_floor_px: int = 0
    overflowing: tuple[str, ...] = ()
    truncated: tuple[str, ...] = ()

    @property
    def text_too_small(self) -> bool:
        return self.min_text_px is not None and self.min_text_px < self.text_floor_px

    @property
    def faulty(self) -> bool:
        return bool(
            self.overlaps or self.offscreen or self.text_too_small or self.overflowing or self.truncated
        )


def _watch_copy_truncation(app: Any) -> list[str]:
    """Record installer copy that ``_fit_text`` had to cut with an ellipsis.

    ``_fit_text`` is the path for translated copy (machine data such as SSIDs
    and disk models goes through ``_fit_line``); cut copy means the layout
    did not leave room for that language at that size.
    """

    cut: list[str] = []
    original = app._fit_text

    def fit_text(font: Any, text_value: str, color: Any, max_width: int) -> Any:
        if max_width > 0 and app._typography.surface_width(font, text_value) > max_width:
            cut.append(text_value)
        return original(font, text_value, color, max_width)

    app._fit_text = fit_text
    return cut



def _watch_label_overflow(look: Any) -> list[str]:
    """Record kit labels still wider than their box at the minimum size.

    ``InstallerLook.label`` shrinks a label only down to the hint size; copy
    that still does not fit would spill out of its button or tile.
    """

    spilled: list[str] = []
    original = look.label

    def label(text: str, size: int, color: Any, *, max_width: int | None = None, **kwargs: Any) -> Any:
        image = original(text, size, color, max_width=max_width, **kwargs)
        if max_width is not None and image.get_width() > max_width:
            spilled.append(text)
        return image

    look.label = label
    return spilled


class _TextSizeRecorder:
    """Typography proxy recording the px size of every non-empty line drawn.

    Wraps the installer's (localized) typography: ``render`` carries its size,
    and ``surface`` is mapped back to the size its font was built at.
    """

    def __init__(self, inner: Any) -> None:
        self._inner = inner
        self._font_sizes: dict[int, int] = {}
        self.sizes: list[int] = []

    def font(self, role: Any, size: int) -> Any:
        font = self._inner.font(role, size)
        self._font_sizes[id(font)] = int(size)
        base = getattr(font, "base", None)
        if base is not None:
            self._font_sizes[id(base)] = int(size)
        return font

    def render(self, text: str, role: Any, size: int, color: Any) -> Any:
        if str(text).strip():
            self.sizes.append(int(size))
        return self._inner.render(text, role, size, color)

    def surface(self, font: Any, text: str, color: Any) -> Any:
        size = self._font_sizes.get(id(font))
        if size is not None and isinstance(text, str) and text.strip():
            self.sizes.append(size)
        return self._inner.surface(font, text, color)

    @property
    def minimum(self) -> int | None:
        return min(self.sizes) if self.sizes else None

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


def _layout_faults(
    buttons: dict[str, Any], size: tuple[int, int]
) -> tuple[tuple[tuple[str, str], ...], tuple[str, ...]]:
    screen_rect = pygame.Rect((0, 0), size)
    names = sorted(buttons)
    overlaps = tuple(
        (a, b)
        for index, a in enumerate(names)
        for b in names[index + 1 :]
        if pygame.Rect(buttons[a]).colliderect(pygame.Rect(buttons[b]))
    )
    offscreen = tuple(
        name for name in names if not screen_rect.contains(pygame.Rect(buttons[name]))
    )
    return overlaps, offscreen


def _make_app(locale: str) -> Any:
    return LanguageFirstInstallerApplication(
        root=REPO_ROOT,
        payload=Path("/nonexistent/greia-payload.squashfs"),
        payload_digest=None,
        windowed=True,
        demo=True,
        locale=locale,
        hardware_controller=_PreviewController(),
    )


def render_language_screen(size: tuple[int, int], out: Path) -> ShotReport | None:
    """Render the language-first chooser, when the chooser exposes a draw API."""

    from greia_installer import entrypoint

    chooser_type = getattr(entrypoint, "LanguageChooser", None)
    if chooser_type is None:
        return None
    from greia_platform.typography import GreiaTypography

    surface = pygame.Surface(size).convert()
    recorder = _TextSizeRecorder(GreiaTypography(REPO_ROOT / "assets" / "fonts" / "nunito-sans"))
    chooser = chooser_type(root=REPO_ROOT, typography=recorder)
    chooser.draw(surface, pygame, pointer_position=(-100, -100))
    out.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(surface, str(out))
    overlaps, offscreen = _layout_faults(chooser.hit_targets(), size)
    return ShotReport(out, overlaps, offscreen, recorder.minimum, text_floors(size[1])[1])


def render_matrix(
    out_dir: Path,
    *,
    locales: Iterable[str] = LOCALES,
    sizes: Iterable[tuple[int, int]] = SIZES,
    only: Iterable[str] | None = None,
) -> list[ShotReport]:
    """Render every scenario for every locale and size; return the reports."""

    pygame.display.init()
    pygame.font.init()
    if pygame.display.get_surface() is None:
        # convert()/convert_alpha() need a display; the dummy driver gives one.
        pygame.display.set_mode((1024, 600))
    wanted = set(only) if only else None
    reports: list[ShotReport] = []
    for locale in locales:
        for width, height in sizes:
            folder = out_dir / locale / f"{width}x{height}"
            if wanted is None or "01-language" in wanted:
                report = render_language_screen(
                    (width, height), folder / "01-language.png"
                )
                if report is not None:
                    reports.append(report)
            for state_id, setup in SCENARIOS:
                if wanted is not None and state_id not in wanted:
                    continue
                app = _make_app(locale)
                recorder = _TextSizeRecorder(app._typography)
                app._typography = recorder
                app._look_cache = None
                spilled = _watch_label_overflow(app._look())
                cut = _watch_copy_truncation(app)
                setup(app)
                surface = pygame.Surface((width, height)).convert()
                app._buttons.clear()
                app._draw(surface, pygame)
                path = folder / f"{state_id}.png"
                path.parent.mkdir(parents=True, exist_ok=True)
                pygame.image.save(surface, str(path))
                overlaps, offscreen = _layout_faults(dict(app._buttons), (width, height))
                reports.append(ShotReport(
                    path, overlaps, offscreen, recorder.minimum, text_floors(height)[1],
                    tuple(dict.fromkeys(spilled)),
                    tuple(dict.fromkeys(cut)),
                ))
                app._typography.clear()
    return reports


def write_contact_sheet(
    reports: list[ShotReport], sheet: Path, *, columns: int = 4, thumb_width: int = 400
) -> Path:
    """Tile every rendered state into one labelled PNG."""

    pygame.font.init()
    font = pygame.font.Font(None, 22)
    images = [(report.path, pygame.image.load(str(report.path))) for report in reports]
    if not images:
        raise ValueError("no screenshots to tile")
    label_h = 22
    cells = []
    for path, image in images:
        scale = thumb_width / image.get_width()
        thumb = pygame.transform.smoothscale(
            image, (thumb_width, max(1, int(image.get_height() * scale)))
        )
        cells.append((f"{path.parent.parent.name} {path.parent.name} {path.stem}", thumb))
    cell_h = max(thumb.get_height() for _, thumb in cells) + label_h + 8
    rows = (len(cells) + columns - 1) // columns
    canvas = pygame.Surface((columns * (thumb_width + 8) + 8, rows * cell_h + 8))
    canvas.fill((236, 230, 218))
    for index, (label, thumb) in enumerate(cells):
        row, column = divmod(index, columns)
        x = 8 + column * (thumb_width + 8)
        y = 8 + row * cell_h
        canvas.blit(font.render(label, True, (40, 30, 20)), (x, y + 2))
        canvas.blit(thumb, (x, y + label_h))
    sheet.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(canvas, str(sheet))
    return sheet


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--sheet", type=Path, default=None)
    parser.add_argument("--locale", action="append", choices=("en", "it", "es", "fr"))
    parser.add_argument("--size", action="append", help="WIDTHxHEIGHT, repeatable")
    parser.add_argument("--only", action="append", help="state id, repeatable")
    args = parser.parse_args(argv)
    sizes = (
        tuple(tuple(int(v) for v in size.lower().split("x", 1)) for size in args.size)
        if args.size
        else SIZES
    )
    reports = render_matrix(
        args.out.expanduser(),
        locales=tuple(args.locale or LOCALES),
        sizes=sizes,  # type: ignore[arg-type]
        only=args.only,
    )
    faults = 0
    for report in reports:
        if report.faulty:
            faults += 1
            print(
                f"{report.path}: overlaps={list(report.overlaps)} offscreen={list(report.offscreen)}"
                f" min_text_px={report.min_text_px} floor={report.text_floor_px}"
                f" overflowing={list(report.overflowing)} truncated={list(report.truncated)}"
            )
    print(f"rendered {len(reports)} states; {faults} with layout faults")
    if args.sheet is not None:
        print(f"contact sheet: {write_contact_sheet(reports, args.sheet.expanduser())}")
    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
