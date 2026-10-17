"""Parent panel polish pass (2026-10-17): behaviour that the review found broken.

* A wrong password on the device read "Cannot check the password right now":
  ``authenticate`` raised ``ParentCredentialUnavailable`` for the service's 403.
* The Kids tab crashed (UnboundLocalError) as soon as one child existed.
* The account and password forms had no Backspace, no field movement and no
  Enter; Tab skipped those two sections entirely.
* A field focused on one tab stayed focused on the next.
* Typing a Wi-Fi password never updated the masked dots (not in the frame key).
* At 800x480 the tab strip wrapped and clipped controls out of the card.
"""

from __future__ import annotations

import io
import os
import time
import unittest
import urllib.error
import urllib.request
from types import SimpleNamespace

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from greia_launcher.panel_layout import find_overlaps  # noqa: E402
from greia_launcher.parent_credential_client import (  # noqa: E402
    ChildAccount,
    ParentCredentialClient,
    ParentPasswordRejected,
    ParentSession,
)
from greia_launcher.parent_panel import (  # noqa: E402
    ParentPanelState,
    ParentPanelTab,
    ParentSettingsOverlay,
)
from greia_platform.typography import GreiaTypography  # noqa: E402
from greia_platform.wifi import WifiSetupPhase, WifiSetupSnapshot  # noqa: E402


class _Keys:
    K_ESCAPE = 27
    K_BACKSPACE = 8
    K_RETURN = 13
    K_KP_ENTER = 271
    K_TAB = 9
    K_UP = 273
    K_DOWN = 274
    K_RIGHT = 275
    K_LEFT = 276
    K_SPACE = 32


class _Client:
    def __init__(self, accounts: int = 2) -> None:
        self.accounts = [
            ChildAccount(f"id-{i}", f"Child {i}", "unicorn", 6) for i in range(accounts)
        ]
        self.password_changes: list[tuple[str, str]] = []
        self.added: list[str] = []
        self.removed: list[str] = []

    def verify(self, _password: str) -> bool:
        return True

    def list_child_accounts(self, _session):
        return list(self.accounts)

    def add_child_account(self, _session, *, display_name, avatar_id, approximate_age=None):
        self.added.append(display_name)
        return ChildAccount("new", display_name, avatar_id, approximate_age)

    def remove_child_account(self, _session, profile_id):
        self.removed.append(profile_id)

    def change_parent_password(self, _session, current, new):
        self.password_changes.append((current, new))

    def get_audio_settings(self, _session):
        return {}


class _Language:
    def __init__(self, locale: str = "en") -> None:
        self.locale = locale

    def read(self):
        return SimpleNamespace(locale=self.locale)

    def set(self, _locale):
        raise AssertionError("must not mutate system language")


class _Ssh:
    def get_status(self):
        raise RuntimeError("no systemctl in tests")


class _Wifi:
    def __init__(self) -> None:
        self.snapshot = WifiSetupSnapshot(WifiSetupPhase.READY, (), -1, "")

    def begin(self) -> None:
        return None

    def skip(self) -> None:
        return None

    def drain(self) -> bool:
        return False


class _Mic:
    level = SimpleNamespace(
        available=False, device="starting", rms_dbfs=-60.0, peak_dbfs=-60.0, clipping=False
    )

    def start(self) -> None:
        return None

    def stop(self) -> None:
        return None


def _panel(client=None, locale: str = "en") -> ParentSettingsOverlay:
    panel = ParentSettingsOverlay(
        client if client is not None else _Client(),
        ssh_service=_Ssh(),
        language_service=_Language(locale),
        hardware_store=None,
    )
    panel.wifi_controller = _Wifi()
    panel._mic_level_reader = _Mic()
    panel.request_ssh_status_refresh = lambda *, force=False: None
    panel.open()
    panel.state = ParentPanelState.PANEL
    panel._session = ParentSession(token="tok", device_id="dev")
    return panel


class AuthenticateReportsRejectionTests(unittest.TestCase):
    def _authenticate_with_http_error(self, code: int) -> None:
        def fake(request, timeout=None):  # noqa: ANN001
            raise urllib.error.HTTPError(
                request.full_url, code, "denied", {}, io.BytesIO(b"{}")
            )

        original = urllib.request.urlopen
        urllib.request.urlopen = fake
        try:
            ParentCredentialClient().authenticate("wrong")
        finally:
            urllib.request.urlopen = original

    def test_403_is_a_rejection_not_an_outage(self) -> None:
        with self.assertRaises(ParentPasswordRejected) as caught:
            self._authenticate_with_http_error(403)
        self.assertFalse(caught.exception.rate_limited)

    def test_429_is_a_rate_limited_rejection(self) -> None:
        with self.assertRaises(ParentPasswordRejected) as caught:
            self._authenticate_with_http_error(429)
        self.assertTrue(caught.exception.rate_limited)

    def test_panel_shows_incorrect_password_for_a_rejection(self) -> None:
        class _Rejecting:
            def verify(self, _p):
                return False

            def authenticate(self, _p):
                raise ParentPasswordRejected(403)

        panel = ParentSettingsOverlay(_Rejecting())
        panel.state = ParentPanelState.AUTH
        panel.password_text = "nope"
        panel._attempt_auth(None)
        self.assertIs(panel.state, ParentPanelState.AUTH)
        self.assertIsNone(panel._password_problem)  # i.e. "Incorrect password"
        self.assertIsNone(panel._session)
        self.assertGreater(panel.password_error_until, time.monotonic())

    def test_panel_says_wait_when_rate_limited(self) -> None:
        class _Limited:
            def verify(self, _p):
                return False

            def authenticate(self, _p):
                raise ParentPasswordRejected(429)

        panel = ParentSettingsOverlay(_Limited())
        panel.state = ParentPanelState.AUTH
        panel.password_text = "nope"
        panel._attempt_auth(None)
        self.assertIs(panel.state, ParentPanelState.AUTH)
        from greia_launcher import parent_panel as module

        self.assertEqual(panel._password_problem, module._PASSWORD_RATE_LIMITED)


class FormKeyboardTests(unittest.TestCase):
    def test_backspace_edits_the_focused_password_field(self) -> None:
        panel = _panel()
        panel._select_tab(ParentPanelTab.SECURITY)
        panel.handle_text_input("abc")
        panel.handle_key(_Keys.K_BACKSPACE, _Keys)
        self.assertEqual(panel._security_current, "ab")

    def test_down_moves_between_fields_and_enter_submits(self) -> None:
        client = _Client()
        panel = _panel(client)
        panel._select_tab(ParentPanelTab.SECURITY)
        panel.handle_text_input("old")
        panel.handle_key(_Keys.K_DOWN, _Keys)
        panel.handle_text_input("new-pass")
        panel.handle_key(_Keys.K_DOWN, _Keys)
        panel.handle_text_input("new-pass")
        panel.handle_key(_Keys.K_RETURN, _Keys)
        self.assertEqual(client.password_changes, [("old", "new-pass")])

    def test_enter_on_account_form_creates_and_backspace_edits_the_name(self) -> None:
        client = _Client()
        panel = _panel(client)
        panel._select_tab(ParentPanelTab.ACCOUNTS)
        panel.handle_key(_Keys.K_RETURN, _Keys)  # opens the form
        self.assertEqual(panel._accounts_mode, "add")
        panel.handle_text_input("Robinx")
        panel.handle_key(_Keys.K_BACKSPACE, _Keys)
        panel.handle_key(_Keys.K_RETURN, _Keys)
        self.assertEqual(client.added, ["Robin"])

    def test_enter_never_confirms_a_removal(self) -> None:
        client = _Client()
        panel = _panel(client)
        panel._select_tab(ParentPanelTab.ACCOUNTS)
        panel._accounts = list(client.accounts)
        panel._accounts_mode = "confirm"
        panel._pending_remove = client.accounts[0]
        panel.handle_key(_Keys.K_RETURN, _Keys)
        self.assertEqual(client.removed, [])
        self.assertEqual(panel._accounts_mode, "confirm")

    def test_escape_leaves_the_form_before_closing_the_panel(self) -> None:
        panel = _panel()
        panel._select_tab(ParentPanelTab.ACCOUNTS)
        panel._open_account_form()
        self.assertTrue(panel.handle_key(_Keys.K_ESCAPE, _Keys))
        self.assertEqual(panel._accounts_mode, "list")
        self.assertTrue(panel.is_open)
        self.assertFalse(panel.handle_key(_Keys.K_ESCAPE, _Keys))
        self.assertFalse(panel.is_open)

    def test_a_focused_field_does_not_follow_into_another_tab(self) -> None:
        panel = _panel()
        panel._select_tab(ParentPanelTab.SECURITY)
        panel._select_tab(ParentPanelTab.ACCOUNTS)
        self.assertIsNone(panel._text_field)
        panel.handle_text_input("x")
        self.assertEqual(panel._security_current, "")

    def test_close_forgets_typed_secrets_and_the_session(self) -> None:
        panel = _panel()
        panel._select_tab(ParentPanelTab.SECURITY)
        panel.handle_text_input("secret")
        panel.close()
        self.assertEqual(panel._security_current, "")
        self.assertIsNone(panel._session)


class FrameKeyTests(unittest.TestCase):
    def test_typing_a_wifi_password_changes_the_frame_key(self) -> None:
        panel = _panel()
        panel.active_tab = ParentPanelTab.WIFI
        before = panel._composite_key(None, (1024, 600))
        panel.wifi_controller.snapshot = WifiSetupSnapshot(WifiSetupPhase.READY, (), -1, "a")
        self.assertNotEqual(before, panel._composite_key(None, (1024, 600)))

    def test_feedback_colour_flags_are_in_the_frame_key(self) -> None:
        panel = _panel()
        before = panel._composite_key(None, (1024, 600))
        panel._audio_message_is_error = True
        self.assertNotEqual(before, panel._composite_key(None, (1024, 600)))

    def test_a_failed_audio_write_is_reported_as_an_error(self) -> None:
        panel = _panel(client=object())  # no Parent API surface: offline
        panel._set_mic_gain(2.5)
        self.assertTrue(panel._audio_message_is_error)


class LayoutAtTheFloorTests(unittest.TestCase):
    """Every section renders at 800x480 with no overlap and nothing clipped."""

    @classmethod
    def setUpClass(cls) -> None:
        pygame.display.init()
        cls.typography = GreiaTypography()

    def _render(self, panel: ParentSettingsOverlay, size: tuple[int, int]):
        screen = pygame.display.set_mode(size)

        def icon(_n, s, _pg):
            return pygame.Surface((s, s), pygame.SRCALPHA)

        panel.draw(
            screen, SimpleNamespace(background=(255, 250, 240)), self.typography,
            pygame, icon,
        )
        visible = screen.get_rect().inflate(-24, -24)
        targets = [(f"{t.action}:{t.value}", t.rect) for t in panel._targets]
        self.assertEqual(find_overlaps(targets), [])
        clipped = [name for name, rect in targets if not visible.contains(rect)]
        self.assertEqual(clipped, [])
        return panel._targets

    def test_every_section_fits_in_italian_and_french(self) -> None:
        for locale in ("it", "fr"):
            for tab in ParentPanelTab:
                with self.subTest(locale=locale, tab=tab.value):
                    panel = _panel(locale=locale)
                    panel._select_tab(tab)
                    self._render(panel, (800, 480))

    def test_kids_tab_draws_children_and_pages_past_the_floor(self) -> None:
        client = _Client(accounts=8)
        panel = _panel(client)
        panel._select_tab(ParentPanelTab.ACCOUNTS)
        targets = self._render(panel, (800, 480))
        shown = [t for t in targets if t.action == "account_rename"]
        self.assertGreater(len(shown), 0)
        self.assertLess(len(shown), 8)
        self.assertTrue(any(t.action == "account_page" for t in targets))
        seen = {t.value for t in shown}
        while any(t.action == "account_page" and t.value == 1 for t in targets):
            panel._accounts_page += 1
            targets = self._render(panel, (800, 480))
            seen |= {t.value for t in targets if t.action == "account_rename"}
        self.assertEqual(seen, {a.profile_id for a in client.accounts})


if __name__ == "__main__":
    unittest.main()
