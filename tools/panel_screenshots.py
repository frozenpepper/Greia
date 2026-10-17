"""Render the on-device Parent panel to PNG so layout can be reviewed, not assumed.

The panel's layout faults (a level label spilling over its buttons, tab labels
overlapping their neighbours) were found by eye on a physical machine, which is
slow and only covers the language the reviewer reads. This renders every tab and
the states that matter (password dialog and its errors, empty/loaded lists,
sub-forms, status messages) offscreen at the reference sizes and in each
selectable locale, and writes one PNG per scene.

It drives the same composed path the Shell uses (a dimmed underlay passed as
``base_surface``), wired to inert fakes, so nothing touches the machine: no
Parent service, no Wi-Fi radio, no systemctl, no microphone, no settings write.

It also reports, per scene, whether any registered hit target overlaps another.
That failure mode is silent in code review because the offending text is a
runtime string.

Run directly to write images and print the overlap report:

    SDL_VIDEODRIVER=dummy python3 tools/panel_screenshots.py --out /tmp/shots

``--locale en,it`` picks locales (default: the selectable ones, en and it),
``--size 1024x600`` limits sizes and ``--scene auth`` limits scenes by prefix.

Not part of `make verify`: it needs a writable output directory and a headless
SDL video driver. The assertions it performs are duplicated as unit tests in
`tests/test_panel_layout.py`, which do run in the suite.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
# The script's own directory (tools/) is sys.path[0] and holds a
# ``greia_parent.py`` launcher that shadows the ``greia_parent`` package, so
# src/ must come first even when PYTHONPATH already lists it.
_SRC = str(REPO_ROOT / "src")
_TOOLS = Path(__file__).resolve().parent
sys.path[:] = [_SRC] + [
    p for p in sys.path if p != _SRC and Path(p or ".").resolve() != _TOOLS
]
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("GREIA_OS_ROOT", str(REPO_ROOT))

import pygame  # noqa: E402 - requires the SDL video driver chosen above

from greia_launcher.panel_layout import find_overlaps  # noqa: E402
from greia_launcher.parent_credential_client import (  # noqa: E402
    ChildAccount,
    ParentSession,
)
from greia_launcher.parent_panel import (  # noqa: E402
    ParentPanelState,
    ParentPanelTab,
    ParentSettingsOverlay,
)
from greia_platform.microphone_level import MicrophoneLevel  # noqa: E402
from greia_platform.ssh_maintenance import SshStatus  # noqa: E402
from greia_platform.typography import GreiaTypography  # noqa: E402
from greia_platform.wifi import (  # noqa: E402
    WifiNetwork,
    WifiSecurity,
    WifiSetupPhase,
    WifiSetupSnapshot,
)

#: The real reference panel (1024x600) and the smallest supported one (800x480),
#: because cramped is where fixed offsets break first.
SIZES = ((1024, 600), (800, 480))

#: The four owner-selected device languages (2026-10-17: en, it, es, fr).
LOCALES = ("en", "it", "es", "fr")

#: Shown on the language tab when the platform registry has not been promoted
#: yet in this checkout, so the four-language layout can be reviewed now. The
#: panel itself only ever offers what ``SUPPORTED_SYSTEM_LANGUAGES`` contains.
_PREVIEW_LANGUAGES = (("es", "Spanish", "Español", "\U0001F1EA\U0001F1F8"),
                      ("fr", "French", "Français", "\U0001F1EB\U0001F1F7"))


def _preview_four_languages() -> None:
    import greia_launcher.parent_panel as panel_module
    from greia_platform.system_language import SystemLanguage

    present = {item.locale for item in panel_module.SUPPORTED_SYSTEM_LANGUAGES}
    extra = tuple(
        SystemLanguage(locale, english, native, flag)
        for locale, english, native, flag in _PREVIEW_LANGUAGES
        if locale not in present
    )
    panel_module.SUPPORTED_SYSTEM_LANGUAGES = (
        tuple(panel_module.SUPPORTED_SYSTEM_LANGUAGES) + extra
    )


def _load_icon(_name: str, size: int, _pygame: Any) -> Any:
    surface = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.line(surface, (61, 44, 31), (4, 4), (size - 5, size - 5), 3)
    pygame.draw.line(surface, (61, 44, 31), (size - 5, 4), (4, size - 5), 3)
    return surface


class _FakeWifi:
    """Wi-Fi controller stand-in whose snapshot the scene chooses."""

    def __init__(self) -> None:
        self.snapshot = WifiSetupSnapshot(WifiSetupPhase.UNAVAILABLE, (), -1, "")

    def begin(self) -> None:
        return None

    def skip(self) -> None:
        return None

    def drain(self) -> bool:
        return False

    def __getattr__(self, _name: str) -> Callable[..., None]:
        return lambda *_a, **_k: None


class _FakeMic:
    def __init__(self) -> None:
        self.level = MicrophoneLevel.unavailable("starting")

    def start(self) -> None:
        return None

    def stop(self) -> None:
        return None


class _FakeLanguage:
    def __init__(self, locale: str) -> None:
        self.locale = locale

    def read(self) -> Any:
        locale = self.locale

        class _Current:
            pass

        current = _Current()
        current.locale = locale
        return current

    def set(self, _locale: str) -> Any:
        raise AssertionError("screenshots must not mutate system language")


class _FakeClient:
    """Parent service stand-in: answers reads, refuses to be written to."""

    def __init__(self) -> None:
        self.accounts = [
            ChildAccount("1ec82f21c5544a3ab3e694d38fb4248e", "Explorer", "unicorn", 7),
            ChildAccount("2ec82f21c5544a3ab3e694d38fb4248e", "Robin", "owl", 5),
            ChildAccount(
                "3ec82f21c5544a3ab3e694d38fb4248e",
                "Maximiliana Valentina",
                "rainbow",
                None,
            ),
        ]
        self.offline = False

    def verify(self, _password: str) -> bool:
        return False

    def list_child_accounts(self, _session: Any) -> list[ChildAccount]:
        if self.offline:
            raise RuntimeError("offline")
        return list(self.accounts)

    def get_audio_settings(self, _session: Any) -> dict[str, Any]:
        return {
            "microphone_processing_enabled": True,
            "advanced_noise_reduction": False,
            "advanced_available": False,
        }


class _NoSsh:
    def get_status(self) -> Any:
        raise RuntimeError("screenshots never query systemctl")


def _overlay(locale: str) -> tuple[ParentSettingsOverlay, _FakeClient]:
    client = _FakeClient()
    overlay = ParentSettingsOverlay(
        client,
        ssh_service=_NoSsh(),
        language_service=_FakeLanguage(locale),
        hardware_store=None,
    )
    overlay.wifi_controller = _FakeWifi()  # type: ignore[assignment]
    overlay._mic_level_reader = _FakeMic()  # noqa: SLF001
    overlay.request_ssh_status_refresh = lambda *, force=False: None  # type: ignore[method-assign]
    return overlay, client


def _unlocked(overlay: ParentSettingsOverlay, tab: ParentPanelTab) -> None:
    overlay.state = ParentPanelState.PANEL
    overlay.active_tab = tab
    overlay._session = ParentSession(token="tok", device_id="dev")  # noqa: SLF001


def _networks() -> tuple[WifiNetwork, ...]:
    return (
        WifiNetwork("Casa Rossi 5G", WifiSecurity.PERSONAL, -45.0, "/net/connman/iwd/0/1"),
        WifiNetwork("Ufficio", WifiSecurity.ENTERPRISE, -62.0, "/net/connman/iwd/0/2"),
        WifiNetwork("Biblioteca libera", WifiSecurity.OPEN, -70.0, "/net/connman/iwd/0/3"),
    )


def _scene_auth(o: ParentSettingsOverlay, _c: _FakeClient) -> None:
    return None


def _scene_auth_typed(o: ParentSettingsOverlay, _c: _FakeClient) -> None:
    o.password_text = "greia123"


def _scene_auth_rejected(o: ParentSettingsOverlay, _c: _FakeClient) -> None:
    o.password_error_until = time.monotonic() + 60.0


def _scene_auth_unavailable(o: ParentSettingsOverlay, _c: _FakeClient) -> None:
    o.password_error_until = time.monotonic() + 60.0
    o._password_problem = "Cannot check the password right now"  # noqa: SLF001


def _tab(tab: ParentPanelTab, extra: Callable[..., None] | None = None) -> Callable[..., None]:
    def scene(o: ParentSettingsOverlay, c: _FakeClient) -> None:
        _unlocked(o, tab)
        if extra is not None:
            extra(o, c)

    return scene


def _language_changed(o: ParentSettingsOverlay, _c: _FakeClient) -> None:
    o._language_message = o._ui_message(  # noqa: SLF001
        "language.changed", name=o._ui_message("language.option.it")  # noqa: SLF001
    )


def _audio_live(o: ParentSettingsOverlay, _c: _FakeClient) -> None:
    o._mic_level_reader.level = MicrophoneLevel(  # noqa: SLF001
        available=True, rms_dbfs=-18.0, peak_dbfs=-6.0, clipping=False, device="hw:0"
    )
    o._cached_mic_gain = 2.0  # noqa: SLF001
    o._mic_gain_read_at = time.monotonic() + 3600  # noqa: SLF001
    o._audio_message = o._copy("STATUS_OFFLINE")  # noqa: SLF001
    o._audio_message_is_error = True  # noqa: SLF001


def _accounts_empty(o: ParentSettingsOverlay, c: _FakeClient) -> None:
    c.accounts = []


def _accounts_offline(o: ParentSettingsOverlay, c: _FakeClient) -> None:
    c.offline = True


def _accounts_add(o: ParentSettingsOverlay, _c: _FakeClient) -> None:
    o._accounts_mode = "add"  # noqa: SLF001
    o._text_field = "account_name"  # noqa: SLF001
    o._account_name = "Robin"  # noqa: SLF001
    o._account_age = "7"  # noqa: SLF001


def _accounts_rename(o: ParentSettingsOverlay, c: _FakeClient) -> None:
    o._start_rename(c.accounts[0])  # noqa: SLF001


def _accounts_confirm(o: ParentSettingsOverlay, c: _FakeClient) -> None:
    o._accounts_mode = "confirm"  # noqa: SLF001
    o._pending_remove = c.accounts[0]  # noqa: SLF001


def _security_error(o: ParentSettingsOverlay, _c: _FakeClient) -> None:
    o._security_current = "greia"  # noqa: SLF001
    o._security_new = "a-longer-passphrase"  # noqa: SLF001
    o._security_confirm = "a-longer-passphras"  # noqa: SLF001
    o._text_field = "security_confirm"  # noqa: SLF001
    o._set_security_message(o._copy("SECURITY_MISMATCH"), error=True)  # noqa: SLF001


def _wifi_list(o: ParentSettingsOverlay, _c: _FakeClient) -> None:
    o.wifi_controller.snapshot = WifiSetupSnapshot(
        WifiSetupPhase.READY, _networks(), 0, "secret", connected_ssid=""
    )


def _wifi_connected(o: ParentSettingsOverlay, _c: _FakeClient) -> None:
    o.wifi_controller.snapshot = WifiSetupSnapshot(
        WifiSetupPhase.CONNECTED, _networks(), 2, "", connected_ssid="Casa Rossi 5G"
    )


def _wifi_error(o: ParentSettingsOverlay, _c: _FakeClient) -> None:
    o.wifi_controller.snapshot = WifiSetupSnapshot(
        WifiSetupPhase.ERROR, _networks(), 0, "x", error="Operation failed (net.connman.iwd.Failed)"
    )


def _ssh_on(o: ParentSettingsOverlay, _c: _FakeClient) -> None:
    o._ssh_cached_status = SshStatus(  # noqa: SLF001
        active=True, enabled=True, port=22, username="greia", host_ip="192.168.68.114"
    )


def _pointer_message(o: ParentSettingsOverlay, _c: _FakeClient) -> None:
    o._pointer_message = o._ui_message("pointer.reset.done")  # noqa: SLF001


SCENES: tuple[tuple[str, Callable[..., None]], ...] = (
    ("auth", _scene_auth),
    ("auth-typed", _scene_auth_typed),
    ("auth-rejected", _scene_auth_rejected),
    ("auth-unavailable", _scene_auth_unavailable),
    ("language", _tab(ParentPanelTab.LANGUAGE)),
    ("language-changed", _tab(ParentPanelTab.LANGUAGE, _language_changed)),
    ("audio", _tab(ParentPanelTab.AUDIO)),
    ("audio-live", _tab(ParentPanelTab.AUDIO, _audio_live)),
    ("accounts", _tab(ParentPanelTab.ACCOUNTS)),
    ("accounts-empty", _tab(ParentPanelTab.ACCOUNTS, _accounts_empty)),
    ("accounts-offline", _tab(ParentPanelTab.ACCOUNTS, _accounts_offline)),
    ("accounts-add", _tab(ParentPanelTab.ACCOUNTS, _accounts_add)),
    ("accounts-rename", _tab(ParentPanelTab.ACCOUNTS, _accounts_rename)),
    ("accounts-confirm", _tab(ParentPanelTab.ACCOUNTS, _accounts_confirm)),
    ("security", _tab(ParentPanelTab.SECURITY)),
    ("security-error", _tab(ParentPanelTab.SECURITY, _security_error)),
    ("wifi-empty", _tab(ParentPanelTab.WIFI)),
    ("wifi", _tab(ParentPanelTab.WIFI, _wifi_list)),
    ("wifi-connected", _tab(ParentPanelTab.WIFI, _wifi_connected)),
    ("wifi-error", _tab(ParentPanelTab.WIFI, _wifi_error)),
    ("ssh-checking", _tab(ParentPanelTab.SSH)),
    ("ssh", _tab(ParentPanelTab.SSH, _ssh_on)),
    ("info", _tab(ParentPanelTab.INFO, _ssh_on)),
    ("pointer", _tab(ParentPanelTab.POINTER)),
    ("pointer-message", _tab(ParentPanelTab.POINTER, _pointer_message)),
)


def _underlay(size: tuple[int, int]) -> Any:
    """A stand-in for the Shell's dimmed profile picker."""

    base = pygame.Surface(size)
    base.fill((246, 222, 170))
    for index in range(4):
        rect = pygame.Rect(0, 0, 150, 170)
        rect.center = (size[0] // 2 + (index - 1.5) * 190, size[1] // 2)
        pygame.draw.rect(base, (255, 250, 240), rect, border_radius=24)
    dim = pygame.Surface(size, pygame.SRCALPHA)
    dim.fill((30, 24, 20, 210))
    base.blit(dim, (0, 0))
    return base.convert()


def render_scene(
    name: str,
    setup: Callable[..., None],
    size: tuple[int, int],
    locale: str,
    out_dir: Path,
) -> dict[str, Any]:
    pygame.display.init()
    screen = pygame.display.set_mode(size)
    typography = GreiaTypography()
    overlay, client = _overlay(locale)
    overlay.open()
    setup(overlay, client)
    base = _underlay(size)

    class _Theme:
        background = (255, 250, 240)

    overlay.draw(
        screen, _Theme(), typography, pygame, _load_icon,
        draw_backdrop=False, base_surface=base, base_key=("shot", size),
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{locale}-{name}-{size[0]}x{size[1]}.png"
    pygame.image.save(screen, str(path))
    rects = [(f"{t.action}:{t.value}", t.rect) for t in overlay._targets]  # noqa: SLF001
    # The panel card is inset 20 px; content outside it is clipped away, so a
    # target there is a control the parent can never see.
    visible = screen.get_rect().inflate(-40, -40)
    escaped = [label for label, rect in rects if not visible.contains(rect)]
    return {
        "scene": name,
        "size": size,
        "locale": locale,
        "path": str(path),
        "targets": len(rects),
        "overlaps": find_overlaps(rects),
        "offscreen": escaped,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="/tmp/greia-panel-shots")
    parser.add_argument("--locale", default=",".join(LOCALES))
    parser.add_argument("--size", default="")
    parser.add_argument("--scene", default="")
    parser.add_argument(
        "--registry-only", action="store_true",
        help="do not preview es/fr on the language tab when the registry lacks them",
    )
    args = parser.parse_args(argv)
    if not args.registry_only:
        _preview_four_languages()
    out_dir = Path(args.out)
    sizes = SIZES
    if args.size:
        sizes = tuple(
            tuple(int(v) for v in item.split("x")) for item in args.size.split(",")
        )  # type: ignore[assignment]
    failures = 0
    for locale in [item for item in args.locale.split(",") if item]:
        for size in sizes:
            for name, setup in SCENES:
                if args.scene and not name.startswith(args.scene):
                    continue
                try:
                    result = render_scene(name, setup, size, locale, out_dir)
                except Exception as exc:  # a crashing scene is a finding, not a stop
                    print(f"  CRASH {locale} {name:<18} {size[0]}x{size[1]} {exc!r}")
                    failures += 1
                    continue
                bad = result["overlaps"] or result["offscreen"]
                status = "OK " if not bad else "BAD"
                print(
                    f"  {status} {locale} {name:<18} {size[0]}x{size[1]} "
                    f"targets={result['targets']:<3} {result['path']}"
                )
                for pair in result["overlaps"]:
                    print(f"        overlapping targets: {pair[0]} <-> {pair[1]}")
                    failures += 1
                for label in result["offscreen"]:
                    print(f"        target outside the panel: {label}")
                    failures += 1
    print(f"\n  {failures} layout fault(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
