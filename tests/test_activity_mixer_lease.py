"""Idle Activity mixer: closes after silence, reopens transparently (Acer finding A.2 #1)."""

from __future__ import annotations

import array
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from greia_platform import activity_mixer_lease as lease_module
from greia_platform.activity_mixer_lease import (
    ActivityMixerLease,
    LeasedChannel,
    LeasedSound,
    install_activity_mixer_lease,
    release_idle_activity_audio,
    uninstall_activity_mixer_lease,
)

ROOT = Path(__file__).resolve().parents[1]


class FakeClock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


class FakeChannel:
    def __init__(self, backend: "FakeBackend", index: int) -> None:
        self.backend = backend
        self.index = index

    def set_volume(self, *volume: float) -> None:
        self.backend.volumes[self.index] = volume

    def get_busy(self) -> bool:
        return self.index in self.backend.busy_channels


class FakeBackend:
    """Records the real-mixer calls the lease makes."""

    def __init__(self) -> None:
        self.spec: tuple[int, int, int] | None = None
        self.inits: list[dict[str, object]] = []
        self.quits = 0
        self.busy = False
        self.music = False
        self.other = False
        self.channels = 8
        self.reserved = 0
        self.volumes: dict[int, tuple[float, ...]] = {}
        self.busy_channels: set[int] = set()
        self.on_quit = None

    def init(self, frequency=44100, size=-16, channels=2, buffer=512, allowedchanges=None):
        self.inits.append({"frequency": frequency, "size": size, "channels": channels, "buffer": buffer, "allowedchanges": allowedchanges})
        self.spec = (frequency, size, channels)
        self.channels, self.reserved, self.volumes = 8, 0, {}

    def quit(self) -> None:
        if self.on_quit is not None:
            self.on_quit()
        self.quits += 1
        self.spec = None

    def get_init(self):
        return self.spec

    def get_busy(self) -> bool:
        return self.busy

    def music_busy(self) -> bool:
        return self.music

    def set_num_channels(self, count: int) -> None:
        self.channels = count

    def get_num_channels(self) -> int:
        return self.channels

    def set_reserved(self, count: int) -> int:
        self.reserved = count
        return count

    def channel(self, index: int) -> FakeChannel:
        return FakeChannel(self, index)

    def other_devices_open(self):
        return self.other


def opened(clock: FakeClock, **kwargs) -> tuple[ActivityMixerLease, FakeBackend]:
    backend = FakeBackend()
    lease = ActivityMixerLease(backend, quiet_seconds=10.0, clock=clock, background=False, **kwargs)
    lease.owner_init(22050, -16, 1, 256)
    return lease, backend


def poll_at(lease: ActivityMixerLease, clock: FakeClock, when: float) -> bool:
    clock.now = when
    return lease.poll()


class MixerLeaseStateTests(unittest.TestCase):
    def test_closes_only_after_the_quiet_period(self) -> None:
        clock = FakeClock()
        lease, backend = opened(clock)
        self.assertFalse(poll_at(lease, clock, 109.0))
        self.assertTrue(poll_at(lease, clock, 110.5))
        self.assertEqual(backend.quits, 1)
        self.assertTrue(lease.quiesced)
        self.assertEqual(lease.reported_init(), (22050, -16, 1))
        self.assertEqual(lease.quiesce_count, 1)

    def test_never_closes_while_busy_in_use_pinned_or_capturing(self) -> None:
        clock = FakeClock()
        lease, backend = opened(clock)
        backend.busy = True
        self.assertFalse(poll_at(lease, clock, 111.0))
        backend.busy = False
        # Busy restarted the quiet period.
        self.assertFalse(poll_at(lease, clock, 120.0))
        backend.music = True
        self.assertFalse(poll_at(lease, clock, 140.0))
        backend.music = False
        backend.other = True  # e.g. a microphone capture device
        self.assertFalse(poll_at(lease, clock, 160.0))
        backend.other = None  # SDL cannot be inspected: stay open
        self.assertFalse(poll_at(lease, clock, 180.0))
        backend.other = False
        with lease.use():
            self.assertFalse(poll_at(lease, clock, 200.0))
        lease.pin()
        self.assertFalse(poll_at(lease, clock, 300.0))
        self.assertEqual(backend.quits, 0)

    def test_poll_is_rate_limited(self) -> None:
        clock = FakeClock()
        lease, backend = opened(clock)
        clock.now = 120.0
        backend.busy = True
        lease.poll()
        backend.busy = False
        self.assertFalse(lease.poll())  # within 0.5 s: no work at all
        self.assertEqual(backend.quits, 0)

    def test_use_reopens_with_format_channels_reservation_and_volumes(self) -> None:
        clock = FakeClock()
        lease, backend = opened(clock)
        backend.set_num_channels(12)
        lease.remember_num_channels(12)
        backend.set_reserved(2)
        lease.remember_reserved(2)
        backend.channel(5).set_volume(0.4)
        lease.remember_channel_volume(5, (0.4,))
        self.assertTrue(poll_at(lease, clock, 111.0))
        with lease.use():
            pass
        reopen = backend.inits[-1]
        self.assertEqual((reopen["frequency"], reopen["size"], reopen["channels"]), (22050, -16, 1))
        self.assertEqual(reopen["buffer"], 256)  # the Activity's own buffer choice
        self.assertEqual(reopen["allowedchanges"], 0)
        self.assertEqual((backend.channels, backend.reserved), (12, 2))
        self.assertEqual(backend.volumes, {5: (0.4,)})
        self.assertFalse(lease.quiesced)
        self.assertEqual(lease.reopen_count, 1)

    def test_owner_init_while_quiesced_reopens_in_the_remembered_format(self) -> None:
        clock = FakeClock()
        lease, backend = opened(clock)
        poll_at(lease, clock, 111.0)
        lease.owner_init()  # an Activity's "if not get_init(): init()" path
        self.assertEqual(backend.spec, (22050, -16, 1))
        self.assertEqual(len(backend.inits), 2)

    def test_reopen_in_another_format_stops_quiescing(self) -> None:
        clock = FakeClock()
        lease, backend = opened(clock)
        poll_at(lease, clock, 111.0)
        original = backend.init

        def other_format(**kwargs):
            original(**kwargs)
            backend.spec = (44100, -16, 2)

        backend.init = other_format
        with lease.use():
            pass
        self.assertFalse(poll_at(lease, clock, 500.0))
        self.assertEqual(backend.quits, 1)

    def test_status_queries_do_not_wait_for_a_close_in_progress(self) -> None:
        clock = FakeClock()
        lease, backend = opened(clock)
        answers: list[bool] = []

        def query_during_close() -> None:
            def query() -> None:
                with lease.if_open() as open_now:
                    answers.append(open_now)

            worker = threading.Thread(target=query)
            worker.start()
            worker.join(1.0)
            answers.append(worker.is_alive())

        backend.on_quit = query_during_close
        self.assertTrue(poll_at(lease, clock, 111.0))
        self.assertEqual(answers, [False, False])
        self.assertEqual(lease.reported_init(), (22050, -16, 1))

    def test_owner_quit_owes_no_reopen(self) -> None:
        clock = FakeClock()
        lease, backend = opened(clock)
        poll_at(lease, clock, 111.0)
        lease.owner_quit()
        self.assertIsNone(lease.reported_init())
        with lease.use():
            pass
        self.assertEqual(len(backend.inits), 1)

    def test_rejects_non_positive_quiet_period(self) -> None:
        with self.assertRaises(ValueError):
            ActivityMixerLease(FakeBackend(), quiet_seconds=0.0)


class InstalledLeaseTests(unittest.TestCase):
    """The real Pygame mixer (SDL dummy audio driver) behind the installed lease."""

    def setUp(self) -> None:
        pygame.mixer.quit()
        self.lease = install_activity_mixer_lease(quiet_seconds=0.5, background=False)
        self.addCleanup(self._restore)
        pygame.mixer.init(22050, -16, 1, 512)

    def _restore(self) -> None:
        uninstall_activity_mixer_lease()
        pygame.mixer.quit()

    def quiesce(self) -> None:
        self.lease._last_use -= 60.0
        self.lease._next_poll = 0.0
        if self.lease._backend.other_devices_open() is not False:
            self.skipTest("SDL audio devices cannot be inspected on this host")
        self.assertTrue(release_idle_activity_audio())
        self.assertTrue(self.lease.quiesced)

    def tone(self) -> pygame.mixer.Sound:
        return pygame.mixer.Sound(buffer=array.array("h", [1000, -1000] * 2205).tobytes())

    def test_install_replaces_entry_points_and_uninstall_restores(self) -> None:
        self.assertIs(pygame.mixer.Sound, LeasedSound)
        self.assertIs(pygame.mixer.Channel, LeasedChannel)
        self.assertIs(install_activity_mixer_lease(), self.lease)  # idempotent
        uninstall_activity_mixer_lease()
        self.assertIsNot(pygame.mixer.Sound, LeasedSound)
        self.assertIsNone(lease_module.active_mixer_lease())
        self.assertFalse(release_idle_activity_audio())

    def test_sounds_and_channels_survive_quiesce_and_reopen(self) -> None:
        pygame.mixer.set_num_channels(10)
        pygame.mixer.set_reserved(1)
        sound = self.tone()
        speech = pygame.mixer.Channel(0)
        speech.set_volume(0.5)
        length = sound.get_length()
        played = sound.play()
        self.assertIsInstance(played, LeasedChannel)
        self.assertGreaterEqual(played.index, 1)  # the reserved channel is skipped
        pygame.mixer.stop()
        self.quiesce()
        # A quiesced mixer looks open and silent; nothing here reopens it.
        self.assertEqual(pygame.mixer.get_init(), (22050, -16, 1))
        self.assertFalse(pygame.mixer.get_busy())
        self.assertFalse(speech.get_busy())
        speech.stop()
        sound.stop()
        self.assertEqual(sound.get_length(), length)
        self.assertEqual(pygame.mixer.get_num_channels(), 10)
        self.assertAlmostEqual(speech.get_volume(), 0.5, places=2)
        self.assertEqual(self.lease.reopen_count, 0)
        # The next playback reopens transparently with the old configuration.
        speech.play(sound)
        self.assertEqual(self.lease.reopen_count, 1)
        self.assertEqual(pygame.mixer.get_num_channels(), 10)
        self.assertAlmostEqual(pygame.mixer.Channel(0).get_volume(), 0.5, places=2)
        self.assertTrue(speech.get_busy())
        pygame.mixer.stop()
        self.quiesce()
        self.assertIsNotNone(sound.play())
        self.assertEqual(self.lease.reopen_count, 2)

    def test_new_sounds_and_explicit_init_reopen(self) -> None:
        self.quiesce()
        self.tone()
        self.assertFalse(self.lease.quiesced)
        self.quiesce()
        pygame.mixer.init()
        self.assertEqual(pygame.mixer.get_init(), (22050, -16, 1))

    def test_channel_index_is_validated_like_pygame(self) -> None:
        with self.assertRaises(IndexError):
            pygame.mixer.Channel(99)
        self.quiesce()
        with self.assertRaises(IndexError):
            pygame.mixer.Channel(99)
        self.assertEqual(pygame.mixer.Channel(3), LeasedChannel(3))


class EntryInstallsLeaseTests(unittest.TestCase):
    def test_python_activity_entry_routes_the_mixer_through_the_lease(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            script = Path(temporary) / "main.py"
            script.write_text(
                "import json, pygame\n"
                "from greia_platform.activity_mixer_lease import active_mixer_lease\n"
                "print(json.dumps({'sound': pygame.mixer.Sound.__name__, "
                "'channel': pygame.mixer.Channel.__name__, 'lease': active_mixer_lease() is not None}))\n",
                encoding="utf-8",
            )
            env = dict(os.environ)
            env.update({
                "PYTHONPATH": str(ROOT / "src"),
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYGAME_HIDE_SUPPORT_PROMPT": "1",
                "SDL_AUDIODRIVER": "dummy",
                "SDL_VIDEODRIVER": "dummy",
            })
            result = subprocess.run(
                [sys.executable, "-P", "-m", "greia_platform.python_activity_entry", str(script)],
                cwd=temporary, env=env, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout.strip().splitlines()[-1])
        self.assertEqual(payload, {"sound": "LeasedSound", "channel": "LeasedChannel", "lease": True})


if __name__ == "__main__":
    unittest.main()
