from __future__ import annotations

import inspect
import unittest
from types import SimpleNamespace

from greia_launcher.input_semantics import discard_preinteractive_input
from greia_launcher.presentation import GreiaLauncherPresentation


class _EventQueue:
    def __init__(self, initial: list[SimpleNamespace]) -> None:
        self.queue = list(initial)

    def clear(self, event_types) -> None:
        discarded = {int(value) for value in event_types}
        self.queue = [event for event in self.queue if int(event.type) not in discarded]

    def get(self, event_types=None):
        if event_types is None:
            pending = list(self.queue)
            self.queue.clear()
            return pending
        wanted = {int(value) for value in event_types}
        matched = [event for event in self.queue if int(event.type) in wanted]
        self.queue = [event for event in self.queue if int(event.type) not in wanted]
        return matched

    def post(self, event: SimpleNamespace) -> None:
        self.queue.append(event)


class _FallbackEventQueue(_EventQueue):
    def clear(self, event_types) -> None:
        raise TypeError("filtered clear unsupported")

    def get(self, event_types=None):
        if event_types is not None:
            raise TypeError("filtered get unsupported")
        return super().get(None)


class LauncherInputSemanticsTests(unittest.TestCase):
    def _pygame(self, queue: _EventQueue) -> SimpleNamespace:
        return SimpleNamespace(
            MOUSEMOTION=4,
            MOUSEBUTTONDOWN=1025,
            MOUSEBUTTONUP=1026,
            MOUSEWHEEL=1027,
            KEYDOWN=768,
            KEYUP=769,
            TEXTINPUT=771,
            FINGERMOTION=1792,
            FINGERDOWN=1793,
            FINGERUP=1794,
            JOYAXISMOTION=1536,
            JOYHATMOTION=1538,
            JOYBUTTONDOWN=1539,
            JOYBUTTONUP=1540,
            QUIT=256,
            VIDEORESIZE=32769,
            event=queue,
        )

    def test_preinteractive_quarantine_drops_user_actions_but_preserves_system_events(self) -> None:
        queued = [
            SimpleNamespace(type=4, pos=(10, 10)),
            SimpleNamespace(type=768, key=13),
            SimpleNamespace(type=769, key=13),
            SimpleNamespace(type=771, text="a"),
            SimpleNamespace(type=1025, button=1, pos=(20, 20)),
            SimpleNamespace(type=1026, button=1, pos=(20, 20)),
            SimpleNamespace(type=1027, y=1),
            SimpleNamespace(type=1539, button=0),
            SimpleNamespace(type=1540, button=0),
            SimpleNamespace(type=256),
            SimpleNamespace(type=32769, size=(800, 600)),
        ]
        queue = _EventQueue(queued)

        discard_preinteractive_input(self._pygame(queue))

        self.assertEqual(
            [int(event.type) for event in queue.queue],
            [256, 32769],
        )

    def test_preinteractive_quarantine_fallback_reposts_preserved_events_in_order(self) -> None:
        queued = [
            SimpleNamespace(type=768, key=13),
            SimpleNamespace(type=256),
            SimpleNamespace(type=1026, button=1, pos=(20, 20)),
            SimpleNamespace(type=32769, size=(800, 600)),
        ]
        queue = _FallbackEventQueue(queued)

        discard_preinteractive_input(self._pygame(queue))

        self.assertEqual(
            [int(event.type) for event in queue.queue],
            [256, 32769],
        )

    def test_launcher_quarantines_input_after_boot_handoff_before_first_poll(self) -> None:
        source = inspect.getsource(GreiaLauncherPresentation.run)
        quarantine_at = source.find("discard_preinteractive_input(pygame)")
        clock_at = source.find("clock = pygame.time.Clock()")
        first_poll_at = source.find("events = pygame.event.get()")

        self.assertGreaterEqual(quarantine_at, 0)
        self.assertGreater(clock_at, quarantine_at)
        self.assertGreater(first_poll_at, clock_at)


if __name__ == "__main__":
    unittest.main()
