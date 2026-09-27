from __future__ import annotations

import os
import unittest
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

from greia_installer.main import InstallerApplication, InstallerPage
from greia_platform.hardware import DisplayMode, HardwareDefaults, HardwareSettings
from greia_platform.hardware_session import (
    ApplyResult,
    DisplayProbe,
    PointerCapabilities,
    PointerDeviceInfo,
    PointerKind,
    preset_to_speed,
    speed_preset_names,
    speed_to_preset,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class _Keys:
    K_ESCAPE = 1
    K_UP = 2
    K_DOWN = 3
    K_LEFT = 4
    K_RIGHT = 5
    K_RETURN = 6
    K_SPACE = 7
    K_1 = 8
    K_2 = 9
    K_3 = 10
    K_r = 11


def _touchpad_info() -> PointerDeviceInfo:
    return PointerDeviceInfo(
        kind=PointerKind.TOUCHPAD,
        label="Touchpad",
        capabilities=PointerCapabilities(
            supports_tap=True,
            supports_natural_scrolling=True,
            supports_disable_while_typing=True,
            supports_speed=True,
        ),
    )


def _mouse_info() -> PointerDeviceInfo:
    return PointerDeviceInfo(
        kind=PointerKind.MOUSE,
        label="Mouse",
        capabilities=PointerCapabilities(
            supports_natural_scrolling=True,
            supports_speed=True,
        ),
    )


class _FakePointerController:
    """Narrow preview seam double: records pointer previews only."""

    backend_id = "fake-pointer"

    def __init__(
        self,
        pointers: tuple[PointerDeviceInfo, ...] = (),
        *,
        fail_preview: bool = False,
    ):
        self._pointers = pointers
        self._fail_preview = fail_preview
        self.preview_calls: list[HardwareSettings] = []
        self.generic_apply_calls = 0

    def topology_token(self):
        return ("fake-pointer",)

    def probe_pointers(self):
        return self._pointers

    def apply_pointer_settings(self, settings: HardwareSettings) -> ApplyResult:
        self.preview_calls.append(settings)
        if self._fail_preview:
            raise RuntimeError("simulated preview backend failure")
        return ApplyResult(True, self.probe_display(), ("pointer preview",))

    def probe_display(self):
        return DisplayProbe(
            "panel-0",
            (DisplayMode(1024, 600, 60.0, preferred=True, current=True),),
        )

    def apply(self, settings):  # pragma: no cover - must never run in preview
        self.generic_apply_calls += 1
        raise AssertionError("pointer preview must not use the generic apply path")


class _FakeDisplayController(_FakePointerController):
    def __init__(self, modes, **kwargs):
        super().__init__(**kwargs)
        self._modes = tuple(modes)

    def probe_display(self):
        return DisplayProbe("panel-0", self._modes)


class _NoSeamController:
    backend_id = "fake-no-seam"

    def topology_token(self):
        return ("fake-no-seam",)

    def probe_display(self):
        return DisplayProbe(
            "panel-0",
            (DisplayMode(1024, 600, 60.0, preferred=True, current=True),),
        )

    def apply(self, settings):
        raise AssertionError("preview must not use the generic apply path")


class InstallerPointerSetupTests(unittest.TestCase):
    def make_app(self, controller=None) -> InstallerApplication:
        app = InstallerApplication(
            root=PROJECT_ROOT,
            payload=Path("/tmp/not-used.squashfs"),
            payload_digest=None,
            windowed=True,
            demo=True,
        )
        if controller is not None:
            app.hardware_controller = controller
        return app

    def test_initial_state_derives_from_central_v2_defaults(self) -> None:
        app = self.make_app()
        defaults = HardwareDefaults.load(
            PROJECT_ROOT / "runtime" / "hardware-settings.toml"
        )
        self.assertEqual(app.state.settings.schema_version, 2)
        self.assertFalse(app.state.settings.touchpad_tap)
        self.assertEqual(
            app.state.settings.disable_while_typing, defaults.disable_while_typing
        )
        self.assertEqual(app.state.settings.mouse_speed, defaults.mouse_speed)
        self.assertEqual(
            app.state.settings.touchpad_speed, defaults.touchpad_speed
        )

    def test_pointer_and_display_pages_are_reachable_in_order(self) -> None:
        app = self.make_app()
        app.state.page = InstallerPage.TARGET
        app._activate_primary()
        self.assertEqual(app.state.page, InstallerPage.POINTER)
        app._activate_primary()
        self.assertEqual(app.state.page, InstallerPage.DISPLAY)
        app._activate_primary()
        self.assertEqual(app.state.page, InstallerPage.WIFI)

    def test_keyboard_only_completion_through_pointer_and_display(self) -> None:
        app = self.make_app(controller=_FakePointerController(pointers=()))
        app.state.page = InstallerPage.POINTER
        for _ in range(40):
            if app.state.page != InstallerPage.POINTER:
                break
            row = app.focused_pointer_row()
            if row == "continue":
                app._handle_key(_Keys.K_RETURN, _Keys)
            else:
                app.move_pointer_focus(1)
                if app.focused_pointer_row() == "continue":
                    app._handle_key(_Keys.K_RETURN, _Keys)
        self.assertEqual(app.state.page, InstallerPage.DISPLAY)
        app._handle_key(_Keys.K_RETURN, _Keys)
        self.assertEqual(app.state.page, InstallerPage.WIFI)

    def test_escape_never_traps_the_user(self) -> None:
        app = self.make_app(controller=_FakePointerController(pointers=()))
        app.state.page = InstallerPage.POINTER
        app._handle_key(_Keys.K_ESCAPE, _Keys)
        self.assertEqual(app.state.page, InstallerPage.TARGET)
        app.state.page = InstallerPage.DISPLAY
        app._handle_key(_Keys.K_ESCAPE, _Keys)
        self.assertEqual(app.state.page, InstallerPage.POINTER)

    def test_speed_change_mutates_state_through_shared_presets(self) -> None:
        app = self.make_app(
            controller=_FakePointerController(pointers=(_touchpad_info(),))
        )
        names = speed_preset_names()
        self.assertGreaterEqual(len(names), 3)
        app.set_pointer_preset("touchpad", "fast")
        self.assertEqual(app.state.settings.touchpad_speed, preset_to_speed("fast"))
        app.set_pointer_preset("mouse", "slow")
        self.assertEqual(app.state.settings.mouse_speed, preset_to_speed("slow"))
        chosen = app.cycle_pointer_preset("touchpad", 1)
        self.assertEqual(chosen, speed_to_preset(app.state.settings.touchpad_speed))
        with self.assertRaises(KeyError):
            app.set_pointer_preset("touchpad", "not a preset")

    def test_preview_seam_receives_semantic_settings_only(self) -> None:
        controller = _FakePointerController(
            pointers=(_touchpad_info(), _mouse_info())
        )
        app = self.make_app(controller=controller)
        before_resolution = app.state.settings.resolution
        app.set_pointer_preset("touchpad", "fast")
        app.toggle_pointer_flag("tap")
        self.assertGreaterEqual(len(controller.preview_calls, ), 2)
        for seen in controller.preview_calls:
            self.assertIsInstance(seen, HardwareSettings)
            self.assertEqual(seen.resolution, before_resolution)
        self.assertEqual(controller.preview_calls[-1], app.state.settings)
        self.assertEqual(controller.generic_apply_calls, 0)

    def test_preview_failure_renders_status_and_keeps_keyboard_working(self) -> None:
        controller = _FakePointerController(
            pointers=(_touchpad_info(),), fail_preview=True
        )
        app = self.make_app(controller=controller)
        app.state.page = InstallerPage.POINTER
        app.toggle_pointer_flag("tap")
        self.assertIn("preview", app._pointer_preview_error.lower())
        first = app.focused_pointer_row()
        app.move_pointer_focus(1)
        self.assertNotEqual(app.focused_pointer_row(), "")
        self.assertNotEqual(first, "")
        app._handle_key(_Keys.K_DOWN, _Keys)
        app._handle_key(_Keys.K_ESCAPE, _Keys)
        self.assertEqual(app.state.page, InstallerPage.TARGET)

    def test_capability_gating_hides_touchpad_controls_without_touchpad(self) -> None:
        mouse_only = self.make_app(
            controller=_FakePointerController(pointers=(_mouse_info(),))
        )
        mouse_only.state.page = InstallerPage.POINTER
        rows = mouse_only.pointer_rows()
        self.assertNotIn("tap", rows)
        self.assertNotIn("disable-while-typing", rows)
        self.assertNotIn("touchpad-preset", rows)
        self.assertIn("mouse-preset", rows)

        touch_only = self.make_app(
            controller=_FakePointerController(pointers=(_touchpad_info(),))
        )
        touch_rows = touch_only.pointer_rows()
        self.assertIn("tap", touch_rows)
        self.assertIn("disable-while-typing", touch_rows)
        self.assertIn("touchpad-preset", touch_rows)

        unknown = self.make_app(controller=_NoSeamController())
        unknown_rows = unknown.pointer_rows()
        self.assertIn("tap", unknown_rows)
        self.assertIn("touchpad-preset", unknown_rows)
        self.assertIn("mouse-preset", unknown_rows)

    def test_test_targets_give_click_feedback(self) -> None:
        app = self.make_app(controller=_FakePointerController(pointers=()))
        self.assertEqual(app.hit_pointer_test_target("test-2"), 1)
        self.assertEqual(app.hit_pointer_test_target("test-1"), 2)
        self.assertIn("2", app._pointer_test_feedback)
        with self.assertRaises(KeyError):
            app.hit_pointer_test_target("test-9")

    def test_reset_uses_central_defaults(self) -> None:
        app = self.make_app(
            controller=_FakePointerController(pointers=(_touchpad_info(),))
        )
        app.set_pointer_preset("touchpad", "very fast")
        app.toggle_pointer_flag("tap")
        app.toggle_pointer_flag("disable-while-typing")
        app.reset_pointer_to_defaults()
        defaults = HardwareDefaults.load(
            PROJECT_ROOT / "runtime" / "hardware-settings.toml"
        )
        self.assertEqual(app.state.settings.touchpad_speed, defaults.touchpad_speed)
        self.assertEqual(app.state.settings.mouse_speed, defaults.mouse_speed)
        self.assertEqual(app.state.settings.touchpad_tap, defaults.touchpad_tap)
        self.assertEqual(
            app.state.settings.disable_while_typing, defaults.disable_while_typing
        )
        self.assertEqual(
            app.state.settings.natural_scrolling, defaults.natural_scrolling
        )

    def test_continue_preserves_settings_into_install_request(self) -> None:
        app = self.make_app(
            controller=_FakePointerController(
                pointers=(_touchpad_info(), _mouse_info())
            )
        )
        app.set_pointer_preset("touchpad", "fast")
        app.toggle_pointer_flag("tap")
        request = app.build_install_request(app.state.target)
        self.assertEqual(request.hardware_settings, app.state.settings)
        self.assertEqual(
            request.hardware_settings.touchpad_speed, preset_to_speed("fast")
        )
        self.assertTrue(request.hardware_settings.touchpad_tap)

    def test_display_shows_supported_modes_only(self) -> None:
        modes = (
            DisplayMode(320, 200, 60.0),
            DisplayMode(800, 600, 60.0),
            DisplayMode(1024, 600, 60.0, preferred=True, current=True),
        )
        controller = _FakeDisplayController(modes)
        app = self.make_app(controller=controller)
        app.demo = False
        app._refresh_display_cache()
        supported = app._available_resolutions()
        self.assertIn("1024x600", supported)
        self.assertIn("800x600", supported)
        self.assertNotIn("320x200", supported)
        facts = app.display_facts()
        self.assertNotIn("320x200", facts["supported_mode_ids"])

    def test_unknown_metrics_use_safe_fallback_and_never_block_install(self) -> None:
        app = self.make_app()
        self.assertIsNone(app.display_install_block_reason())
        self.assertIn("Safe display", app.display_status_copy())

    def test_unsupported_display_copy_and_destructive_install_gating(self) -> None:
        modes = (DisplayMode(320, 200, 60.0, current=True),)
        controller = _FakeDisplayController(modes)
        app = self.make_app(controller=controller)
        app.demo = False
        app._refresh_display_cache()
        reason = app.display_install_block_reason()
        self.assertIsNotNone(reason)
        self.assertIn("not fully supported", app.display_status_copy())
        app.state.page = InstallerPage.CONFIRM

        class _PowerOK:
            def installation_block_reason(self):
                return None

        app.power_probe = _PowerOK()
        app._start_installation()
        self.assertEqual(app.state.page, InstallerPage.ERROR)
        self.assertIn("not fully supported", app.state.error)
        self.assertIsNone(app._worker)

    def test_supported_display_does_not_gate_install(self) -> None:
        controller = _FakeDisplayController(
            (DisplayMode(1024, 600, 60.0, preferred=True, current=True),)
        )
        app = self.make_app(controller=controller)
        app.demo = False
        app._refresh_display_cache()
        self.assertIsNone(app.display_install_block_reason())

    def test_essential_controls_apply_physical_floors(self) -> None:
        app = self.make_app()
        floored = app.essential_control_px(46)
        self.assertGreaterEqual(floored, 8)
        self.assertLessEqual(floored, 320)

    def test_installer_copy_never_says_calibration(self) -> None:
        import greia_installer.main as installer_main

        source = Path(installer_main.__file__).read_text(encoding="utf-8")
        self.assertNotIn("calibration", source.lower())
        self.assertIn("Pointer setup", source)
        self.assertIn("Pointer feel", source)

    def test_installer_uses_no_backend_device_vocabulary(self) -> None:
        import greia_installer.composition as composition
        import greia_installer.main as installer_main

        for module in (installer_main, composition):
            source = Path(module.__file__).read_text(encoding="utf-8").lower()
            self.assertNotIn("xinput", source)
            self.assertNotIn("xrandr", source)
            self.assertNotIn("libinput", source)
            self.assertNotIn("transformation matrix", source)
            self.assertNotIn("synps/2", source)

    def test_pointer_page_shows_touchpad_and_mouse_feel_presets(self) -> None:
        import greia_installer.main as installer_main

        source = Path(installer_main.__file__).read_text(encoding="utf-8")
        self.assertIn("Touchpad feel", source)
        self.assertIn("Mouse feel", source)
        self.assertIn("preset_to_speed", source)
        self.assertIn("speed_to_preset", source)
        self.assertNotIn("+.2f", source)

    def test_pointer_inventory_is_probed_once_per_page_visit_not_per_frame(self) -> None:
        """Probing shells out to xinput; it must not run per rendered frame.

        ``pointer_rows()`` consults the attached-pointer inventory twice, and
        the legacy-x backend satisfies each consultation by spawning
        ``xinput`` (plus one query per device). Asking per frame meant well over
        a hundred process spawns per second while the pointer page was open,
        which pinned a full core on the reference Acer and made the page feel
        frozen. Inventory only changes on hotplug, so it is memoised for the
        page visit and re-probed when the page changes.
        """

        class _Counting(_FakePointerController):
            def __init__(self, pointers):
                super().__init__(pointers)
                self.probe_calls = 0

            def probe_pointers(self):
                self.probe_calls += 1
                return self._pointers

        controller = _Counting((_touchpad_info(), _mouse_info()))
        app = self.make_app(controller)
        app.state.page = InstallerPage.POINTER
        for _ in range(50):
            app.pointer_rows()
        self.assertEqual(
            controller.probe_calls,
            1,
            "50 pointer_rows() calls on one page must not re-probe the hardware",
        )
        app.state.page = InstallerPage.DISPLAY
        app.pointer_rows()
        self.assertEqual(
            controller.probe_calls,
            2,
            "leaving the page must drop the cache so the inventory is re-read",
        )

    def test_pointer_page_layout_fits_the_reference_1024x600_display(self) -> None:
        """The pointer page must fit the panel it is given, by measurement.

        It previously used a hard-coded 56 px step and a hard-coded 64 px test
        target. Its content is taller than a 600 px display, so rows overlapped
        and the reset control was drawn outside the panel on the reference Acer.
        """

        app = self.make_app()
        # main = 6% inset with 88% height, exactly as _draw computes it.
        panel = int(600 * 0.88)
        for setting_count in range(3, 9):
            with self.subTest(setting_count=setting_count):
                row_h, step, target = app._pointer_vertical_budget(
                    panel, setting_count
                )
                strip_h = (
                    app.POINTER_LABEL_H
                    + app.POINTER_STRIP_LABEL_GAP
                    + target
                    + app.POINTER_STRIP_TAIL
                )
                content_bottom = setting_count * step + strip_h
                nav_top = panel - 63
                self.assertLessEqual(
                    content_bottom,
                    nav_top,
                    "pointer page content must stay clear of the navigation row",
                )
                self.assertGreaterEqual(row_h, app.POINTER_ROW_HARD_MIN)
                self.assertLessEqual(row_h, app.POINTER_ROW_MAX)
                self.assertGreaterEqual(target, app.POINTER_TARGET_HARD_MIN)

    def test_pointer_page_layout_grows_on_larger_displays(self) -> None:
        app = self.make_app()
        small = app._pointer_vertical_budget(int(600 * 0.88), 5)
        large = app._pointer_vertical_budget(int(1080 * 0.88), 5)
        self.assertLess(small[0], large[0])
        self.assertEqual(small[2], large[2])

    def test_every_installer_page_renders_headlessly(self) -> None:
        """Every page must actually paint, not merely have correct state.

        The installer's draw path had no executed coverage at all: state and
        row tests passed while the real boot crashed on the first page with
        ``NameError: name '_text' is not defined``. A missing ``self.`` on a
        helper call is invisible to a state test and fatal to a child holding
        the installer, so each page is now painted for real against a headless
        surface at the reference 1024x600.
        """

        import pygame

        pygame.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((1024, 600), pygame.HIDDEN)
        screen = pygame.display.set_mode((1024, 600))

        app = self.make_app(_FakePointerController((_touchpad_info(), _mouse_info())))
        for page in InstallerPage:
            with self.subTest(page=page.name):
                app.state.page = page
                app._buttons.clear()
                app._draw(screen, pygame)
                app._draw_pointer(screen, pygame)
        self.assertTrue(
            app._buttons,
            "the pointer page must register interactive controls",
        )

    def test_rows_are_gated_on_real_capability_not_just_a_touchpad(self) -> None:
        """A control the backend cannot honour must not be offered.

        The reference Acer's touchpad is driven by libinput and exposes no
        tapping property at all. The backend correctly declines to set it, but
        its "not available" result was discarded and the row was gated only on
        "a touchpad exists". The child was shown a live-looking tap-to-click
        toggle that could never do anything.
        """
        from greia_platform.hardware_session import PointerCapabilities

        class _Fixed(_FakePointerController):
            def __init__(self, pointers):
                super().__init__(pointers)
                self.probe_calls = 0

            def probe_pointers(self):
                self.probe_calls += 1
                return self._pointers

        bare_touchpad = PointerDeviceInfo(
            kind=PointerKind.TOUCHPAD,
            label="Touchpad",
            capabilities=PointerCapabilities(),
        )
        app = self.make_app(_Fixed((bare_touchpad, _mouse_info())))
        app.state.page = InstallerPage.POINTER
        rows = app.pointer_rows()
        self.assertNotIn("tap", rows)
        self.assertNotIn("disable-while-typing", rows)
        self.assertIn("natural", rows)
        self.assertIn("touchpad-preset", rows)
        self.assertIn("mouse-preset", rows)
        note = app._pointer_unavailable_note()
        self.assertIn("tap to click", note)

        capable = PointerDeviceInfo(
            kind=PointerKind.TOUCHPAD,
            label="Touchpad",
            capabilities=PointerCapabilities(supports_tap=True),
        )
        app2 = self.make_app(_Fixed((capable, _mouse_info())))
        app2.state.page = InstallerPage.POINTER
        self.assertIn("tap", app2.pointer_rows())
        self.assertNotIn("tap to click", app2._pointer_unavailable_note())


if __name__ == "__main__":
    unittest.main()
