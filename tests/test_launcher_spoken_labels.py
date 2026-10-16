from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace

from greia_launcher.spoken_labels import (
    SpokenLabelPlayer,
    activity_title_audio,
    collection_title_audio,
    locale_candidates,
)


def _bundle(root: Path, locale: str, audio_path: str) -> None:
    (root / "locales").mkdir(parents=True, exist_ok=True)
    path = root / audio_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"not-decoded-by-resolver")
    (root / "locales" / f"{locale}.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "locale": locale,
                "direction": "ltr",
                "strings": {"activity.title": "Example"},
                "audio": {
                    "activity.title": {
                        "path": audio_path,
                        "caption_key": "activity.title",
                    }
                },
            }
        ),
        encoding="utf-8",
    )


class _FakeChannel:
    def __init__(self) -> None:
        self.stop_calls = 0
        self.played: list[object] = []

    def stop(self) -> None:
        self.stop_calls += 1

    def play(self, sound: object) -> None:
        self.played.append(sound)


class _FakeMixer:
    def __init__(self) -> None:
        self.channel = _FakeChannel()
        self.sound_calls: list[str] = []

    def get_init(self) -> bool:
        return True

    def Sound(self, path: str) -> object:  # noqa: N802 - mirrors pygame API
        self.sound_calls.append(path)
        return ("sound", path)

    def find_channel(self, force: bool = False) -> _FakeChannel:
        assert force is True
        return self.channel


class _FakePygame:
    class error(Exception):
        pass

    def __init__(self) -> None:
        self.mixer = _FakeMixer()

class LauncherSpokenLabelTests(unittest.TestCase):
    """Spoken-label resolution and playback (unittest form so `make verify` runs it)."""

    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        # resolve(): macOS temp roots are /var -> /private/var symlinks.
        self.tmp_path = Path(temporary.name).resolve()

    def test_locale_candidates_are_specific_then_language_then_english(self) -> None:
        assert tuple(item.value for item in locale_candidates("it-IT")) == (
            "it-IT",
            "it",
            "en",
        )
        assert tuple(item.value for item in locale_candidates("en-GB")) == (
            "en-GB",
            "en",
        )

    def test_activity_title_audio_resolves_profile_locale_and_fallback(self) -> None:
        _bundle(self.tmp_path, "it", "locales/it/audio/activity-title.wav")
        manifest = SimpleNamespace(root=self.tmp_path)
        assert activity_title_audio(manifest, "it-IT") == (
            self.tmp_path / "locales/it/audio/activity-title.wav"
        )
        assert activity_title_audio(manifest, "fr") is None

    def test_activity_title_audio_can_fall_back_to_english(self) -> None:
        _bundle(self.tmp_path, "en", "locales/en/audio/activity-title.wav")
        manifest = SimpleNamespace(root=self.tmp_path)
        assert activity_title_audio(manifest, "it") == (
            self.tmp_path / "locales/en/audio/activity-title.wav"
        )

    def test_my_time_legacy_underscore_title_is_resolved_without_json_audio_mapping(self) -> None:
        root = Path(__file__).resolve().parents[1] / "activity_incubator" / "tempo_di_greia"
        manifest = SimpleNamespace(root=root)
        english = root / "locales/en/audio/activity_title.wav"
        italian = root / "locales/it/audio/activity_title.wav"
        assert english.is_file() and italian.is_file()
        assert activity_title_audio(manifest, "en") == english
        assert activity_title_audio(manifest, "it") == italian
        assert activity_title_audio(manifest, "fr") == english

    def test_collection_title_audio_is_platform_owned_and_safe(self) -> None:
        clip = self.tmp_path / "assets/audio/system/launcher-labels/it/create.wav"
        clip.parent.mkdir(parents=True)
        clip.write_bytes(b"clip")
        assert collection_title_audio(self.tmp_path, "create", "it-IT") == clip
        assert collection_title_audio(self.tmp_path, "../create", "it") is None

    def test_player_deduplicates_same_focus_interrupts_new_focus_and_caches(self) -> None:
        clip = self.tmp_path / "name.wav"
        clip.write_bytes(b"clip")
        pygame = _FakePygame()
        player = SpokenLabelPlayer(cache_entries=2)

        assert player.announce("activity:a", clip, pygame) is True
        assert player.announce("activity:a", clip, pygame) is False
        assert player.announce("activity:b", clip, pygame) is True

        assert len(pygame.mixer.sound_calls) == 1
        assert len(pygame.mixer.channel.played) == 2
        assert pygame.mixer.channel.stop_calls == 2

        player.clear_focus()
        assert player.announce("activity:b", clip, pygame) is True


class _LifecycleChannel:
    def __init__(self) -> None:
        self.busy = False

    def stop(self) -> None:
        self.busy = False

    def play(self, sound: object) -> None:
        self.busy = True

    def get_busy(self) -> bool:
        return self.busy


class _LifecycleMixer:
    """Fake mixer with an open/closed device, like pygame.mixer."""

    def __init__(self) -> None:
        self.open = False
        self.calls: list[str] = []
        self.channel = _LifecycleChannel()

    def get_init(self):
        return (22050, -16, 1) if self.open else None

    def init(self) -> None:
        self.calls.append("init")
        self.open = True

    def quit(self) -> None:
        self.calls.append("quit")
        self.open = False
        self.channel = _LifecycleChannel()

    def get_busy(self) -> bool:
        return self.channel.busy

    def Sound(self, path: str) -> object:  # noqa: N802 - mirrors pygame API
        assert self.open, "Sound() on a closed mixer"
        self.calls.append("Sound")
        return ("sound", path)

    def find_channel(self, force: bool = False) -> _LifecycleChannel:
        assert self.open, "find_channel() on a closed mixer"
        return self.channel


class ShellMixerLeaseTests(unittest.TestCase):
    """Acer sweep at 15212f44: Home idled at ~9% CPU once any Shell sound played."""

    def setUp(self) -> None:
        from greia_launcher.spoken_labels import ShellMixerLease

        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.clip = Path(temporary.name).resolve() / "label.wav"
        self.clip.write_bytes(b"clip")
        self.now = 100.0
        self.pygame = SimpleNamespace(mixer=_LifecycleMixer(), error=RuntimeError)
        self.lease = ShellMixerLease(quiet_seconds=10.0, clock=lambda: self.now)
        self.player = SpokenLabelPlayer(mixer=self.lease)

    def test_mixer_closes_after_quiet_period_and_reopens_lazily(self) -> None:
        mixer = self.pygame.mixer
        self.assertTrue(self.player.announce("activity:a", self.clip, self.pygame))
        self.assertEqual(mixer.calls, ["init", "Sound"])
        # Still audible: never closed, however long the clip plays.
        self.now += 30.0
        self.assertFalse(self.player.poll_idle_audio(self.now, self.pygame))
        mixer.channel.busy = False  # clip ended
        self.now += 9.0
        self.assertFalse(self.player.poll_idle_audio(self.now, self.pygame))
        self.assertTrue(mixer.open)
        self.now += 1.5
        self.assertTrue(self.player.poll_idle_audio(self.now, self.pygame))
        self.assertFalse(mixer.open)
        self.assertEqual(self.lease.generation, 1)
        # Bounded: polling a closed mixer does nothing.
        self.assertFalse(self.player.poll_idle_audio(self.now + 60.0, self.pygame))
        # The next sound reopens the device and reloads its clip.
        self.assertTrue(self.player.announce("activity:b", self.clip, self.pygame))
        self.assertEqual(mixer.calls, ["init", "Sound", "quit", "init", "Sound"])

    def test_release_closes_at_once_for_an_activity_launch(self) -> None:
        from greia_launcher.spoken_labels import SpokenLabelController

        controller = SpokenLabelController(Path("."), player=self.player)
        self.assertTrue(self.player.announce("activity:a", self.clip, self.pygame))
        self.assertTrue(controller.release_audio(self.pygame))
        self.assertFalse(self.pygame.mixer.open)
        self.assertFalse(controller.release_audio(self.pygame))
        self.assertTrue(self.player.play_if_idle(self.clip, self.pygame))
        self.assertTrue(self.pygame.mixer.open)

    def test_mixer_opened_elsewhere_gets_a_full_quiet_period(self) -> None:
        self.pygame.mixer.init()
        self.assertFalse(self.lease.poll(self.pygame, self.now))
        self.now += 9.9
        self.assertFalse(self.lease.poll(self.pygame, self.now))
        self.now += 0.2
        self.assertTrue(self.lease.poll(self.pygame, self.now))

    def test_shell_loop_polls_the_lease_and_launch_releases_it(self) -> None:
        source = (Path(__file__).resolve().parents[1] / "src/greia_launcher/presentation.py").read_text()
        self.assertIn("self._spoken_labels.poll_idle_audio(now, pygame)", source)
        main = (Path(__file__).resolve().parents[1] / "src/greia_launcher/main.py").read_text()
        launch = main[main.index("def _launch_selected"):]
        self.assertIn("release_audio", launch[: launch.index("manifest = self._activities")])
