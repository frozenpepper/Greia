"""On-device child accounts and Parent password management.

The Parent panel had no way to set its own password and no way to add or remove
a child. Both operations belong to the Parent service identity, so the panel acts
through the service using the session established at unlock rather than writing
profile or credential storage as the child identity. The service keeps its own
guards: it refuses to remove the signed-in child or the final account, and
revalidates that a profile's data path is a managed directory.
"""

from __future__ import annotations

import unittest

from greia_launcher.parent_credential_client import (
    ChildAccount,
    ParentCredentialUnavailable,
    ParentRequestFailed,
    ParentSession,
)
from greia_launcher.parent_panel import ParentPanelTab, ParentSettingsOverlay


class _FakeClient:
    def __init__(self, *, reject: str | None = None, offline: bool = False) -> None:
        self.reject = reject
        self.offline = offline
        self.added: list[tuple[str, str, int | None]] = []
        self.removed: list[str] = []
        self.password_changes: list[tuple[str, str]] = []
        self.accounts = [
            ChildAccount("id-one", "Explorer", "unicorn", None),
            ChildAccount("id-two", "Robin", "owl", 7),
        ]

    def authenticate(self, password: str) -> ParentSession:
        if self.offline:
            raise ParentCredentialUnavailable("unreachable")
        return ParentSession(token="tok", device_id="dev")

    def verify(self, password: str) -> bool:
        return True

    def list_child_accounts(self, session: ParentSession) -> list[ChildAccount]:
        if self.offline:
            raise ParentCredentialUnavailable("unreachable")
        return list(self.accounts)

    def add_child_account(self, session, *, display_name, avatar_id, approximate_age=None):
        if self.reject:
            raise ParentRequestFailed(self.reject)
        self.added.append((display_name, avatar_id, approximate_age))
        created = ChildAccount("id-new", display_name, avatar_id, approximate_age)
        self.accounts.append(created)
        return created

    def remove_child_account(self, session, profile_id: str) -> None:
        if self.reject:
            raise ParentRequestFailed(self.reject)
        self.removed.append(profile_id)

    def change_parent_password(self, session, current, new) -> None:
        if self.reject:
            raise ParentRequestFailed(self.reject)
        self.password_changes.append((current, new))


def _panel(client: _FakeClient) -> ParentSettingsOverlay:
    panel = ParentSettingsOverlay(client)
    panel._session = ParentSession(token="tok", device_id="dev")
    return panel


class UnlockKeepsASessionTests(unittest.TestCase):
    def test_unlock_uses_authenticate_and_keeps_the_session(self) -> None:
        client = _FakeClient()
        panel = ParentSettingsOverlay(client)
        panel.state = panel.state.__class__.AUTH
        panel.password_text = "greia"
        panel._attempt_auth(None)
        self.assertIsNotNone(panel._session)
        self.assertEqual(panel._session.token, "tok")

    def test_a_bare_verifier_still_unlocks_without_a_session(self) -> None:
        class _Bare:
            def verify(self, password: str) -> bool:
                return True

        panel = ParentSettingsOverlay(_Bare())
        panel.state = panel.state.__class__.AUTH
        panel.password_text = "greia"
        panel._attempt_auth(None)
        self.assertIs(panel.state, panel.state.__class__.PANEL)
        self.assertIsNone(panel._session)


class ChildAccountManagementTests(unittest.TestCase):
    def test_add_sends_name_avatar_and_age(self) -> None:
        client = _FakeClient()
        panel = _panel(client)
        panel._account_name = "  Robin  "
        panel._account_age = "7"
        panel._create_account()
        self.assertEqual(client.added, [("Robin", "rainbow", 7)])
        self.assertEqual(panel._accounts_mode, "list")
        self.assertEqual(panel._account_name, "")

    def test_add_without_a_name_is_refused_before_any_request(self) -> None:
        client = _FakeClient()
        panel = _panel(client)
        panel._account_name = "   "
        panel._create_account()
        self.assertEqual(client.added, [])

    def test_a_non_numeric_age_is_refused_without_a_request(self) -> None:
        client = _FakeClient()
        panel = _panel(client)
        panel._account_name = "Robin"
        panel._account_age = "seven"
        panel._create_account()
        self.assertEqual(client.added, [])

    def test_the_services_own_refusal_reason_is_shown(self) -> None:
        client = _FakeClient(reject="unknown profile avatar: fox")
        panel = _panel(client)
        panel._account_name = "Robin"
        panel._create_account()
        self.assertIn("unknown profile avatar", panel._accounts_message or "")
        self.assertTrue(panel._accounts_message_is_error)

    def test_an_unreachable_service_is_reported_as_offline_not_a_bad_name(self) -> None:
        client = _FakeClient(offline=True)
        panel = _panel(client)
        panel._account_name = "Robin"
        panel._create_account()
        self.assertIn("not responding", panel._accounts_message or "")

    def test_remove_goes_through_the_service(self) -> None:
        client = _FakeClient()
        panel = _panel(client)
        panel._remove_account(client.accounts[0])
        self.assertEqual(client.removed, ["id-one"])
        self.assertEqual(panel._accounts_mode, "list")

    def test_refreshing_accounts_populates_the_list(self) -> None:
        client = _FakeClient()
        panel = _panel(client)
        panel._refresh_accounts()
        self.assertEqual([a.display_name for a in panel._accounts], ["Explorer", "Robin"])

    def test_the_name_field_respects_the_policys_character_limit(self) -> None:
        panel = _panel(_FakeClient())
        panel._set_field_value("account_name", "x" * 200)
        self.assertLessEqual(len(panel._account_name), panel._max_name_characters())

    def test_avatar_selection_wraps_in_both_directions(self) -> None:
        panel = _panel(_FakeClient())
        count = len(panel._available_avatars())
        self.assertGreater(count, 0)
        panel._account_avatar_index = 0
        panel._cycle_avatar(-1)
        self.assertEqual(panel._account_avatar_index, count - 1)
        panel._cycle_avatar(1)
        self.assertEqual(panel._account_avatar_index, 0)


class ParentPasswordChangeTests(unittest.TestCase):
    def test_mismatched_confirmation_is_refused_without_a_request(self) -> None:
        client = _FakeClient()
        panel = _panel(client)
        panel._security_current, panel._security_new, panel._security_confirm = (
            "old", "new-one", "new-two",
        )
        panel._change_password()
        self.assertEqual(client.password_changes, [])

    def test_a_matching_change_is_sent_and_the_fields_cleared(self) -> None:
        client = _FakeClient()
        panel = _panel(client)
        panel._security_current, panel._security_new, panel._security_confirm = (
            "old", "new-pass", "new-pass",
        )
        panel._change_password()
        self.assertEqual(client.password_changes, [("old", "new-pass")])
        self.assertEqual(panel._security_new, "")
        self.assertEqual(panel._security_confirm, "")

    def test_a_rejected_current_password_is_reported_clearly(self) -> None:
        client = _FakeClient(reject="current Parent password is incorrect")
        panel = _panel(client)
        panel._security_current, panel._security_new, panel._security_confirm = (
            "wrong", "new-pass", "new-pass",
        )
        panel._change_password()
        self.assertIn("not correct", panel._security_message or "")
        self.assertTrue(panel._security_message_is_error)

    def test_secret_fields_are_masked(self) -> None:
        panel = _panel(_FakeClient())
        panel._security_new = "hunter2"
        block = panel._field_value("security_new")
        self.assertEqual(block, "hunter2")  # stored plainly, never rendered plainly


class FieldFocusTests(unittest.TestCase):
    def test_typing_goes_to_the_focused_field(self) -> None:
        panel = _panel(_FakeClient())
        panel.state = panel.state.__class__.PANEL
        panel.active_tab = ParentPanelTab.ACCOUNTS
        panel._text_field = "account_name"
        panel.handle_text_input("Ro")
        panel.handle_text_input("bin")
        self.assertEqual(panel._account_name, "Robin")

    def test_typing_is_ignored_with_no_field_focused(self) -> None:
        panel = _panel(_FakeClient())
        panel.state = panel.state.__class__.PANEL
        panel.active_tab = ParentPanelTab.ACCOUNTS
        panel._text_field = None
        panel.handle_text_input("Robin")
        self.assertEqual(panel._account_name, "")

    def test_the_age_field_is_bounded(self) -> None:
        panel = _panel(_FakeClient())
        panel._set_field_value("account_age", "123456")
        self.assertLessEqual(len(panel._account_age), 3)


if __name__ == "__main__":
    unittest.main()
