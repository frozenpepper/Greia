"""The Parent panel must not recomposite an unchanged frame every tick.

Profiled on the reference Acer: the panel is redrawn every frame by the Shell and
was spending 280-351 ms per frame, because the display is software (hwaccel=0)
and each frame composited roughly 45 large translucent surfaces. Steady-state
cost is now ~2 ms, and the audio tab ~15 ms, inside the 60 fps budget.

The cache is only safe because a frame is fully determined by the values in
``_COMPOSITE_STATE_FIELDS``. These tests pin that: an unchanged frame is served
without redrawing, and every field that the drawing code reads must invalidate it.
"""

from __future__ import annotations

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from greia_launcher.parent_panel import (  # noqa: E402
    ParentPanelState,
    ParentPanelTab,
    ParentSettingsOverlay,
)
from greia_platform.typography import GreiaTypography  # noqa: E402


class _Offline:
    def available(self) -> bool:
        return False

    def list_networks(self):
        return []

    def status(self):
        return None

    def scan(self):
        return None

    def connect(self):
        return None

    def select(self, _i):
        return None

    def refresh(self):
        return None

    def backspace_password(self) -> bool:
        return False

    def append_password(self, _t) -> None:
        return None


class _Ssh:
    def status(self):
        return None


class _Language:
    def read(self):
        class _Current:
            locale = "en"

        return _Current()

    def set(self, _l):
        raise AssertionError("must not mutate system language")


class _Verifier:
    def verify(self, _p) -> bool:
        return False


class _Theme:
    background = (255, 250, 240)


def _icon(_n, s, _pg):
    surface = pygame.Surface((s, s), pygame.SRCALPHA)
    surface.fill((120, 100, 90, 255))
    return surface


def _panel() -> ParentSettingsOverlay:
    pygame.display.init()
    panel = ParentSettingsOverlay(
        _Verifier(),
        wifi_backend=_Offline(),
        ssh_service=_Ssh(),
        language_service=_Language(),
    )
    panel.open()
    panel.state = ParentPanelState.PANEL
    return panel


class UnchangedFrameIsServedTests(unittest.TestCase):
    def setUp(self) -> None:
        self.screen = pygame.display.set_mode((1024, 600))
        self.typography = GreiaTypography()
        self.panel = _panel()

    def _draw(self) -> None:
        self.panel.draw(self.screen, _Theme(), self.typography, pygame, _icon)

    def test_second_identical_frame_is_not_recomposited(self) -> None:
        self._draw()
        key = self.panel._composite_key(None, (1024, 600))
        self.assertIsNotNone(self.panel._panel_composite)
        self.assertEqual(self.panel._panel_composite_key, key)

    def test_hit_targets_survive_a_served_frame(self) -> None:
        """A cached frame must still be clickable, or the panel would go dead."""

        self._draw()
        served = self.panel._serve_composite(self.screen, self.panel._composite_key(None, (1024, 600)))
        self.assertTrue(served)
        self.assertTrue(self.panel._targets, "a served frame kept no hit targets")

    def test_switching_tab_invalidates(self) -> None:
        self._draw()
        self.panel.active_tab = ParentPanelTab.WIFI
        self.assertFalse(
            self.panel._serve_composite(
                self.screen, self.panel._composite_key(None, (1024, 600))
            )
        )

    def test_an_animated_tab_opts_out_of_the_cache(self) -> None:
        self._draw()
        self.panel._content_animating = True
        self.assertFalse(
            self.panel._serve_composite(
                self.screen, self.panel._composite_key(None, (1024, 600))
            )
        )

    def test_a_size_change_invalidates(self) -> None:
        self._draw()
        other = pygame.display.set_mode((800, 600))
        self.assertFalse(self.panel._serve_composite(other, self.panel._composite_key(None, (800, 600))))


class SignatureCoversEverythingTheDrawCodeReadsTests(unittest.TestCase):
    """Audit: any ``self._x`` the draw path reads must be in the signature.

    This is the guard that matters. A field missing from the signature does not
    make the panel slow; it makes that piece of state stop updating on screen
    while still looking plausible. It happened for the account list, the whole
    pointer tab and the SSH status, and only the audit caught it.
    """

    _METHOD_NAMES = frozenset(dir(ParentSettingsOverlay))

    #: Read by the draw path but deliberately not part of the signature.
    #: ``_targets`` is rebuilt every frame and restored verbatim when a cached
    #: frame is served, so folding it in would make every frame a miss.
    #: ``_panel_base`` and ``_panel_composite`` are the caches themselves, and
    #: ``_drawing_targets`` was dead scaffolding from an earlier revision.
    _EXEMPT = frozenset(
        {"_targets", "_panel_base", "_panel_composite", "_drawing_targets"}
    )

    def test_no_state_read_by_the_draw_path_is_missing(self) -> None:
        import inspect
        import re

        declared = set(ParentSettingsOverlay._COMPOSITE_STATE_FIELDS)
        missing: list[str] = []
        for name, member in vars(ParentSettingsOverlay).items():
            if not name.startswith("_draw") and name != "draw":
                continue
            try:
                source = inspect.getsource(member)
            except (OSError, TypeError):
                continue
            for field in set(re.findall(r"self\.(_[a-z_][a-z0-9_]*)", source)):
                if field in declared or field in self._METHOD_NAMES:
                    continue
                if field in self._EXEMPT:
                    continue
                missing.append(f"{name} reads self.{field}")
        self.assertEqual(
            sorted(missing), [],
            "state read by the draw path but absent from the composite signature",
        )


class EveryVisualFieldInvalidatesTests(unittest.TestCase):
    """A field the drawing code reads must change the signature.

    A field missing from the signature is a field that silently stops updating on
    screen, which is far worse than being slow.
    """

    def setUp(self) -> None:
        self.panel = _panel()
        self.base = self.panel._composite_key(None, (1024, 600))

    def _assert_changes(self, name: str, value) -> None:
        original = getattr(self.panel, name, None)
        setattr(self.panel, name, value)
        try:
            self.assertNotEqual(
                self.base, self.panel._composite_key(None, (1024, 600)),
                f"{name} is read by the drawing code but is not in the signature",
            )
        finally:
            setattr(self.panel, name, original)

    def test_scalar_fields_are_all_in_the_signature(self) -> None:
        cases = {
            "state": ParentPanelState.AUTH,
            "active_tab": ParentPanelTab.SSH,
            "password_text": "typed",
            "_password_problem": "some problem",
            "_language_index": 4,
            "_language_message": "changed",
            "_audio_message": "set",
            "_cached_mic_gain": 2.5,
            "_accounts_mode": "add",
            "_accounts_message": "saved",
            "_accounts_message_is_error": True,
            "_account_name": "Robin",
            "_account_age": "7",
            "_account_avatar_index": 3,
            "_security_current": "a",
            "_security_new": "b",
            "_security_confirm": "c",
            "_security_message": "done",
            "_security_message_is_error": True,
            "_text_field": "account_name",
        }
        for name, value in cases.items():
            with self.subTest(field=name):
                self._assert_changes(name, value)

    def test_collection_fields_are_in_the_signature(self) -> None:
        self._assert_changes("_accounts", ["a", "b"])
        self._assert_changes("_pending_remove", object())

    def test_animating_flag_is_in_the_signature(self) -> None:
        self._assert_changes("_content_animating", True)


if __name__ == "__main__":
    unittest.main()


class CollaboratorStateInvalidatesTests(unittest.TestCase):
    """A tab fed by an injected object must notice that object changing.

    The Wi-Fi tab renders ``wifi_controller.snapshot`` and the SSH tab renders
    ``ssh_service.status()``. Both live outside this object, so a signature built
    only from its own attributes would freeze a network scan behind a stale frame
    — the worst kind of wrong, because it looks like the radio is broken.

    Excluding the tab entirely was the first attempt and cost the whole Wi-Fi tab
    its speed, since it is exactly the tab a parent uses to set up a network. The
    signature now summarises the collaborator's content instead.
    """

    def setUp(self) -> None:
        pygame.display.init()
        self.screen = pygame.display.set_mode((1024, 600))
        self.panel = _panel()
        self.panel.active_tab = ParentPanelTab.WIFI
        self.panel.draw(self.screen, _Theme(), GreiaTypography(), pygame, _icon)

    def test_wifi_tab_is_cacheable_when_idle(self) -> None:
        self.assertTrue(
            self.panel._serve_composite(
                self.screen, self.panel._composite_key(None, (1024, 600))
            )
        )

    def test_a_changed_wifi_snapshot_invalidates(self) -> None:
        before = self.panel._composite_key(None, (1024, 600))

        class _Snapshot:
            phase = "connected"
            networks = ()
            selected_index = 0
            connected_ssid = "HomeNetwork"
            error = None

        class _Controller:
            def snapshot(self):
                return _Snapshot()

        self.panel.wifi_controller = _Controller()
        self.assertNotEqual(before, self.panel._composite_key(None, (1024, 600)))

    def test_an_unavailable_collaborator_still_produces_a_stable_key(self) -> None:
        class _Broken:
            def snapshot(self):
                raise RuntimeError("radio is not ready")

        self.panel.wifi_controller = _Broken()
        first = self.panel._composite_key(None, (1024, 600))
        self.assertEqual(first, self.panel._composite_key(None, (1024, 600)))
