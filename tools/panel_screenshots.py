"""Render Parent panel tabs to PNG so layout can be reviewed, not assumed.

The panel's layout faults (a level label spilling over its buttons, tab labels
overlapping their neighbours) were found by eye on a physical machine, which is
slow and only covers the language the reviewer reads. This renders each tab
offscreen at a chosen size and writes a PNG, so layout can be inspected directly
and diffed when it changes.

It also reports, per tab, whether any registered hit target overlaps another and
whether every label stayed inside the card that owns it. Those are the two
failure modes that matter for a translated panel, and both are silent in code
review because the offending text is a runtime string.

Run directly to write images and print the overlap report:

    SDL_VIDEODRIVER=dummy PYTHONPATH=src \\
        python3 tools/panel_screenshots.py --out /tmp/shots

Not part of `make verify`: it needs a writable output directory and a headless
SDL video driver. The assertions it performs are duplicated as unit tests in
`tests/test_panel_layout.py`, which do run in the suite.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402 - requires the SDL video driver chosen above

from greia_launcher.parent_panel import (  # noqa: E402
    ParentPanelTab,
    ParentSettingsOverlay,
)
from greia_platform.typography import GreiaTypography  # noqa: E402

#: Sizes chosen to cover the real reference panel (1024x600) and a deliberately
#: cramped one, because cramped is where fixed offsets break first.
SIZES = ((1024, 600), (800, 600))

#: A long translated string, used to prove the layout survives German and
#: Finnish rather than only fitting the English the author wrote.
STRESS_LABEL = (
    "Mikrofonverstärkung für Aufnahmepuppenspiele und "
    "Stimmaktivitäten mit zusätzlicher Verdeutlichung"
)


def _load_icon(_name: str, size: int, _pygame: Any) -> Any:
    surface = pygame.Surface((size, size), pygame.SRCALPHA)
    surface.fill((120, 100, 90, 255))
    return surface


def _offline_overlay() -> ParentSettingsOverlay:
    """An overlay wired to inert fakes so nothing touches the machine."""

    class _NoWifi:
        def list_networks(self) -> list[Any]:
            return []

        def status(self) -> Any:
            return None

    class _NoSsh:
        def status(self) -> Any:
            return None

    class _NoLanguage:
        def read(self) -> Any:
            class _Current:
                locale = "en-GB"

            return _Current()

        def set(self, _locale: str) -> Any:
            raise AssertionError("screenshots must not mutate system language")

    return ParentSettingsOverlay(
        _RejectingVerifier(),
        wifi_backend=_NoWifi(),
        ssh_service=_NoSsh(),
        language_service=_NoLanguage(),
    )


class _Theme:
    """Minimal theme stub: the panel only reads ``background`` when it draws
    its own chrome, which is the standalone path these screenshots exercise."""

    background = (255, 250, 240)


class _RejectingVerifier:
    """Never authenticates: screenshots must render, not unlock anything."""

    def verify(self, _password: str) -> bool:
        return False


def _pose(overlay: ParentSettingsOverlay, tab: ParentPanelTab, variant: str) -> None:
    """Put the overlay into a specific state so sub-screens are reviewable."""

    if tab is ParentPanelTab.ACCOUNTS and variant == "add":
        overlay._accounts_mode = "add"  # noqa: SLF001
        overlay._text_field = "account_name"
        overlay._account_name = "Robin"
        overlay._account_age = "7"
    elif tab is ParentPanelTab.ACCOUNTS and variant == "confirm":
        from greia_launcher.parent_credential_client import ChildAccount

        overlay._accounts_mode = "confirm"  # noqa: SLF001
        overlay._pending_remove = ChildAccount(  # noqa: SLF001
            profile_id="1ec82f21c5544a3ab3e694d38fb4248e",
            display_name="Explorer",
            avatar_id="unicorn",
            approximate_age=None,
        )
    elif tab is ParentPanelTab.SECURITY:
        overlay._security_current = "greia"  # noqa: SLF001
        overlay._security_new = "a-longer-passphrase"  # noqa: SLF001
        overlay._security_confirm = "a-longer-passphrase"  # noqa: SLF001
        overlay._text_field = "security_new"  # noqa: SLF001


def render_tab(
    tab: ParentPanelTab,
    size: tuple[int, int],
    out_dir: Path,
    variant: str = "list",
) -> dict[str, Any]:
    pygame.display.init()
    screen = pygame.display.set_mode(size)
    typography = GreiaTypography()
    from greia_launcher.parent_panel import ParentPanelState

    overlay = _offline_overlay()
    overlay.open()
    # open() resets state and the active tab, so select after it, not before.
    overlay.state = ParentPanelState.PANEL
    overlay.active_tab = tab
    _pose(overlay, tab, variant)
    overlay._targets.clear()  # noqa: SLF001 - measuring one frame, not accumulating

    overlay.draw(screen, _Theme(), typography, pygame, _load_icon)

    out_dir.mkdir(parents=True, exist_ok=True)
    name = f"{tab.value}{'' if variant == 'list' else '-' + variant}-{size[0]}x{size[1]}.png"
    path = out_dir / name
    pygame.image.save(screen, str(path))

    rects = [(t.action, t.rect) for t in overlay._targets]  # noqa: SLF001
    from greia_launcher.panel_layout import find_overlaps

    return {
        "tab": tab.value,
        "size": size,
        "path": str(path),
        "targets": len(rects),
        "overlaps": find_overlaps(rects),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="/tmp/greia-panel-shots")
    args = parser.parse_args(argv)
    out_dir = Path(args.out)

    failures = 0
    variants = {
        ParentPanelTab.ACCOUNTS: ("list", "add", "confirm"),
        ParentPanelTab.SECURITY: ("list",),
    }
    for size in SIZES:
        for tab in ParentPanelTab:
            for variant in variants.get(tab, ("list",)):
                result = render_tab(tab, size, out_dir, variant)
                status = "OK " if not result["overlaps"] else "OVERLAP"
                label = result["tab"] + ("" if variant == "list" else "-" + variant)
                print(
                    f"  {status} {label:<18} {size[0]}x{size[1]} "
                    f"targets={result['targets']:<3} {result['path']}"
                )
                for pair in result["overlaps"]:
                    print(f"        overlapping targets: {pair[0]} <-> {pair[1]}")
                    failures += 1
    print(f"\n  {failures} overlapping target pair(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
