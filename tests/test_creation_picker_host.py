"""Trusted picker host lifecycle without opening SDL/X11."""
from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest import mock

from greia_launcher.creation_picker_host import (
    ActivityCreationPickerHost,
    CreationPickerHostError,
)
from greia_launcher.lifecycle import ActivitySession, ActivitySessionState
from greia_launcher.shell_window import ShellActivityModalLease
from greia_platform.ui_core import UiEventResult


class _Process:
    pid = 4321


def _session() -> ActivitySession:
    return ActivitySession(
        activity_id="org.greia.painting",
        package_digest="a" * 64,
        session_id="session-1",
        control=None,
        process=_Process(),
        state=ActivitySessionState.RUNNING,
        started_at=1.0,
        ready_deadline=2.0,
        graceful_stop_seconds=1.0,
    )


class _ShellBackend:
    def __init__(self):
        self.lease = ShellActivityModalLease("session-1", 1, 4321)
        self.prepares = []
        self.shows = []
        self.dismisses = []
        self.abandons = []
        self.show_result = True
        self.dismiss_result = True

    def prepare_activity_modal(self, pygame, *, session_id, activity_pid):
        self.prepares.append((pygame, session_id, activity_pid))
        return self.lease

    def show_activity_modal(self, lease):
        self.shows.append(lease)
        return self.show_result

    def dismiss_activity_modal(self, lease):
        self.dismisses.append(lease)
        return self.dismiss_result

    def abandon_activity_modal(self, lease):
        self.abandons.append(lease)


class _Supervisor:
    def __init__(self):
        self.enabled = []
        self.disabled = []
        self.pending = None
        self.cancelled = []
        self.completed = []
        self.chrome_ok = True

    def enable_creation_picker(self, session):
        self.enabled.append(session)

    def disable_creation_picker(self, session):
        self.disabled.append(session)

    def pending_creation_selection(self, session):
        return self.pending

    def cancel_creation_selection(self, session, request_id):
        self.cancelled.append((session, request_id))

    def complete_creation_selection(self, session, request_id, creation_id):
        self.completed.append((session, request_id, creation_id))
        return "selected-once"

    def ensure_system_chrome_visible(self, session):
        return self.chrome_ok


class _Display:
    def __init__(self):
        self.surface = object()
        self.flips = 0

    def get_surface(self):
        return self.surface

    def flip(self):
        self.flips += 1


class _Mouse:
    def __init__(self):
        self.values = []

    def set_visible(self, value):
        self.values.append(value)


class _Events:
    def __init__(self):
        self.clears = 0

    def clear(self):
        self.clears += 1


class _Pygame:
    def __init__(self):
        self.display = _Display()
        self.mouse = _Mouse()
        self.event = _Events()


class _Controller:
    def __init__(self, *args, on_pick=None, **kwargs):
        self.on_pick = on_pick
        self.selected_handle = None


class _Screen:
    next_result = UiEventResult.IGNORED

    def __init__(self, controller, **kwargs):
        self.controller = controller
        self.closed = False
        self.draws = 0

    def handle_event(self, event):
        return self.next_result

    def needs_frame(self):
        return False

    def draw(self, surface):
        self.draws += 1

    def on_exit(self):
        self.closed = True


class CreationPickerHostTests(unittest.TestCase):
    def setUp(self):
        self.session = _session()
        self.shell = _ShellBackend()
        self.supervisor = _Supervisor()
        self.pygame = _Pygame()
        self.profile = SimpleNamespace(creations_dir="/trusted/profile/creations")
        self.host = ActivityCreationPickerHost(
            supervisor=self.supervisor,
            shell_window_backend=self.shell,
            session=self.session,
            profile=self.profile,
            typography=object(),
            locale="it",
        )
        self.patches = [
            mock.patch("greia_launcher.creation_picker_host.CreationLibrary", return_value=object()),
            mock.patch("greia_launcher.creation_picker_host.CreationsGalleryController", _Controller),
            mock.patch("greia_launcher.creation_picker_host.CreationsGalleryScreen", _Screen),
            mock.patch("greia_launcher.creation_picker_host.PygameRecordingPreview", return_value=object()),
        ]
        for patch in self.patches:
            patch.start()
            self.addCleanup(patch.stop)

    def test_prepare_enables_broker_only_after_exact_modal_lease(self):
        self.assertTrue(self.host.prepare(self.pygame))
        self.assertTrue(self.host.prepared)
        self.assertEqual(
            self.shell.prepares,
            [(self.pygame, "session-1", 4321)],
        )
        self.assertEqual(self.supervisor.enabled, [self.session])
        # Idempotent host preparation must not issue another native lease.
        self.assertTrue(self.host.prepare(self.pygame))
        self.assertEqual(len(self.shell.prepares), 1)

    def test_open_draw_cancel_restores_activity_and_cancels_request(self):
        self.assertTrue(self.host.prepare(self.pygame))
        self.supervisor.pending = SimpleNamespace(
            request_id="request-1",
            media_types=("image/png",),
            roles=("drawing",),
        )
        self.assertTrue(self.host.service(self.pygame, (object(),)))
        self.assertTrue(self.host.visible)
        self.assertEqual(self.shell.shows, [self.shell.lease])
        self.assertGreaterEqual(self.pygame.display.flips, 1)
        self.assertEqual(self.pygame.mouse.values[-1], True)

        self.host._screen.next_result = UiEventResult.REQUEST_CLOSE
        self.assertFalse(self.host.service(self.pygame, (object(),)))
        self.assertFalse(self.host.visible)
        self.assertEqual(
            self.supervisor.cancelled,
            [(self.session, "request-1")],
        )
        self.assertEqual(self.shell.dismisses, [self.shell.lease])
        self.assertEqual(self.pygame.mouse.values[-1], False)

    def test_selected_request_is_not_cancelled_and_restores_activity(self):
        self.assertTrue(self.host.prepare(self.pygame))
        self.supervisor.pending = SimpleNamespace(
            request_id="request-2",
            media_types=("image/png",),
            roles=(),
        )
        self.host.service(self.pygame, ())
        screen = self.host._screen
        handle = screen.controller.on_pick("creation-1")
        self.assertEqual(handle, "selected-once")
        self.assertEqual(
            self.supervisor.completed,
            [(self.session, "request-2", "creation-1")],
        )
        screen.controller.selected_handle = handle
        screen.next_result = UiEventResult.REQUEST_CLOSE
        self.host.service(self.pygame, (object(),))
        self.assertEqual(self.supervisor.cancelled, [])
        self.assertEqual(self.shell.dismisses, [self.shell.lease])

    def test_activity_cancellation_dismisses_stale_modal_without_second_cancel(self):
        self.assertTrue(self.host.prepare(self.pygame))
        self.supervisor.pending = SimpleNamespace(
            request_id="cancelled-by-child",
            media_types=("image/png",),
            roles=(),
        )
        self.host.service(self.pygame, ())
        screen = self.host._screen
        self.assertTrue(self.host.visible)

        # The Activity already cancelled the request through its broker.
        # The chooser must disappear before processing a stale tap.
        self.supervisor.pending = None
        self.assertFalse(self.host.service(self.pygame, (object(),)))
        self.assertFalse(self.host.visible)
        self.assertTrue(screen.closed)
        self.assertEqual(self.supervisor.completed, [])
        self.assertEqual(self.supervisor.cancelled, [])
        self.assertEqual(self.shell.dismisses, [self.shell.lease])
        self.assertEqual(self.pygame.mouse.values[-1], False)

    def test_expired_broker_request_restores_activity_and_stops_old_picker(self):
        from greia_launcher.creation_selection import CreationSelectionCoordinator

        now = [10.0]
        access = SimpleNamespace(consumable_media_types=frozenset({"audio/wav"}))
        picker = CreationSelectionCoordinator(access, "session-1", clock=lambda: now[0])
        picker.enable_presenter()
        self.supervisor.pending_creation_selection = lambda _session: picker.trusted_pending()

        self.host.prepare(self.pygame)
        req = picker.request(media_types=("audio/wav",))
        self.host.service(self.pygame, ())
        previous_screen = self.host._screen
        self.assertTrue(self.host.visible)

        now[0] += picker.REQUEST_SECONDS + 1
        self.assertFalse(self.host.service(self.pygame, (object(),)))
        self.assertFalse(self.host.visible)
        self.assertTrue(previous_screen.closed)
        self.assertEqual(self.supervisor.completed, [])
        self.assertEqual(self.supervisor.cancelled, [])
        self.assertEqual(self.shell.dismisses, [self.shell.lease])
        self.assertEqual(picker.poll(req.request_id).state, "cancelled")

    def test_replaced_request_never_receives_input_through_previous_modal(self):
        self.assertTrue(self.host.prepare(self.pygame))
        self.supervisor.pending = SimpleNamespace(
            request_id="old", media_types=("image/png",), roles=(),
        )
        self.host.service(self.pygame, ())
        old = self.host._screen
        self.supervisor.pending = SimpleNamespace(
            request_id="new", media_types=("image/png",), roles=(),
        )
        self.assertFalse(self.host.service(self.pygame, (object(),)))
        self.assertTrue(old.closed)
        self.assertFalse(self.host.visible)
        self.assertEqual(self.supervisor.completed, [])
        self.assertTrue(self.host.service(self.pygame, ()))
        self.assertEqual(self.host._request_id, "new")
        self.assertEqual(self.shell.shows, [self.shell.lease, self.shell.lease])

    def test_cancel_failure_still_restores_activity_before_raising(self):
        self.assertTrue(self.host.prepare(self.pygame))
        self.supervisor.pending = SimpleNamespace(
            request_id="cancel-error", media_types=("image/png",), roles=(),
        )
        self.host.service(self.pygame, ())
        screen = self.host._screen

        def fail_cancel(*_args):
            raise RuntimeError("broker unavailable")

        self.supervisor.cancel_creation_selection = fail_cancel
        screen.next_result = UiEventResult.REQUEST_CLOSE
        with self.assertRaisesRegex(CreationPickerHostError, "cancellation"):
            self.host.service(self.pygame, (object(),))
        self.assertTrue(screen.closed)
        self.assertFalse(self.host.visible)
        self.assertEqual(self.shell.dismisses, [self.shell.lease])
        self.assertEqual(self.pygame.mouse.values[-1], False)

    def test_show_failure_cancels_pending_request_and_never_leaves_visible_screen(self):
        self.assertTrue(self.host.prepare(self.pygame))
        self.shell.show_result = False
        self.supervisor.pending = SimpleNamespace(
            request_id="request-3",
            media_types=("image/png",),
            roles=(),
        )
        with self.assertRaisesRegex(CreationPickerHostError, "cover"):
            self.host.service(self.pygame, ())
        self.assertFalse(self.host.visible)
        self.assertEqual(
            self.supervisor.cancelled,
            [(self.session, "request-3")],
        )

    def test_chrome_restack_failure_restores_activity_and_cancels(self):
        self.assertTrue(self.host.prepare(self.pygame))
        self.supervisor.chrome_ok = False
        self.supervisor.pending = SimpleNamespace(
            request_id="request-4",
            media_types=("image/png",),
            roles=(),
        )
        with self.assertRaisesRegex(CreationPickerHostError, "Home chrome"):
            self.host.service(self.pygame, ())
        self.assertEqual(self.shell.dismisses, [self.shell.lease])
        self.assertEqual(
            self.supervisor.cancelled,
            [(self.session, "request-4")],
        )

    def test_abnormal_shutdown_cancels_pending_request_and_revokes_presenter(self):
        self.assertTrue(self.host.prepare(self.pygame))
        self.supervisor.pending = SimpleNamespace(
            request_id="request-shutdown",
            media_types=("image/png",),
            roles=(),
        )
        self.host.service(self.pygame, ())
        self.assertTrue(self.host.visible)
        self.assertTrue(self.host.shutdown(self.pygame, activity_alive=True))
        self.assertEqual(
            self.supervisor.cancelled,
            [(self.session, "request-shutdown")],
        )
        self.assertEqual(self.supervisor.disabled, [self.session])
        self.assertEqual(self.shell.dismisses, [self.shell.lease])
        self.assertEqual(self.shell.abandons, [self.shell.lease])

    def test_terminal_activity_never_opens_or_restores_stale_window(self):
        self.assertTrue(self.host.prepare(self.pygame))
        self.session.state = ActivitySessionState.EXITED
        self.supervisor.pending = SimpleNamespace(
            request_id="stale",
            media_types=("image/png",),
            roles=(),
        )
        self.assertFalse(self.host.service(self.pygame, ()))
        self.assertTrue(self.host.shutdown(self.pygame, activity_alive=False))
        self.assertEqual(self.supervisor.disabled, [self.session])
        self.assertEqual(self.shell.shows, [])
        self.assertEqual(self.shell.dismisses, [])
        self.assertEqual(self.shell.abandons, [self.shell.lease])


if __name__ == "__main__":
    unittest.main()
