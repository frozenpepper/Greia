from __future__ import annotations

import json
from pathlib import Path
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


def test_locale_candidates_are_specific_then_language_then_english() -> None:
    assert tuple(item.value for item in locale_candidates("it-IT")) == (
        "it-IT",
        "it",
        "en",
    )
    assert tuple(item.value for item in locale_candidates("en-GB")) == (
        "en-GB",
        "en",
    )


def test_activity_title_audio_resolves_profile_locale_and_fallback(tmp_path: Path) -> None:
    _bundle(tmp_path, "it", "locales/it/audio/activity-title.wav")
    manifest = SimpleNamespace(root=tmp_path)
    assert activity_title_audio(manifest, "it-IT") == (
        tmp_path / "locales/it/audio/activity-title.wav"
    )
    assert activity_title_audio(manifest, "fr") is None


def test_activity_title_audio_can_fall_back_to_english(tmp_path: Path) -> None:
    _bundle(tmp_path, "en", "locales/en/audio/activity-title.wav")
    manifest = SimpleNamespace(root=tmp_path)
    assert activity_title_audio(manifest, "it") == (
        tmp_path / "locales/en/audio/activity-title.wav"
    )


def test_my_time_legacy_underscore_title_is_resolved_without_json_audio_mapping() -> None:
    root = Path(__file__).resolve().parents[1] / "activity_incubator" / "tempo_di_greia"
    manifest = SimpleNamespace(root=root)
    english = root / "locales/en/audio/activity_title.wav"
    italian = root / "locales/it/audio/activity_title.wav"
    assert english.is_file() and italian.is_file()
    assert activity_title_audio(manifest, "en") == english
    assert activity_title_audio(manifest, "it") == italian
    assert activity_title_audio(manifest, "fr") == english


def test_collection_title_audio_is_platform_owned_and_safe(tmp_path: Path) -> None:
    clip = tmp_path / "assets/audio/system/launcher-labels/it/create.wav"
    clip.parent.mkdir(parents=True)
    clip.write_bytes(b"clip")
    assert collection_title_audio(tmp_path, "create", "it-IT") == clip
    assert collection_title_audio(tmp_path, "../create", "it") is None


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


def test_player_deduplicates_same_focus_interrupts_new_focus_and_caches(tmp_path: Path) -> None:
    clip = tmp_path / "name.wav"
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
