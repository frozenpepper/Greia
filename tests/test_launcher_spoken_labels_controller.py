from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from greia_launcher.spoken_labels import SpokenLabelController


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

    def Sound(self, path: str) -> object:  # noqa: N802
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


def _bundle_activity(root: Path, activity_id: str, locale: str, title: str) -> SimpleNamespace:
    (root / "locales").mkdir(parents=True, exist_ok=True)
    audio_rel = f"locales/{locale}/audio/activity-title.wav"
    p = root / audio_rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"clip-" + activity_id.encode())
    (root / "locales" / f"{locale}.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "locale": locale,
                "direction": "ltr",
                "strings": {"activity.title": title},
                "audio": {
                    "activity.title": {
                        "path": audio_rel,
                        "caption_key": "activity.title",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    return SimpleNamespace(activity_id=activity_id, root=root)


def _make_collection_clip(root: Path, cid: str, locale: str) -> Path:
    p = root / "assets/audio/system/launcher-labels" / locale / f"{cid}.wav"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"clip-" + cid.encode())
    return p


def test_controller_keyboard_activity_selection_announces_once(tmp_path: Path) -> None:
    # 1. Activity keyboard selection changes -> title announced once.
    act_root = tmp_path / "act"
    m1 = _bundle_activity(act_root / "a", "org.greia.foo", "it", "Foo")
    m2 = _bundle_activity(act_root / "b", "org.greia.bar", "it", "Bar")
    pygame = _FakePygame()
    ctrl = SpokenLabelController(tmp_path, dwell_ms=160)
    # first announcement
    assert ctrl.announce_activity(m1, "it", pygame) is True
    assert len(pygame.mixer.channel.played) == 1
    # same activity again -> no replay (dedup)
    assert ctrl.announce_activity(m1, "it", pygame) is False
    assert len(pygame.mixer.channel.played) == 1
    # different activity -> announces
    assert ctrl.announce_activity(m2, "it", pygame) is True
    assert len(pygame.mixer.channel.played) == 2
    # clamped arrow: same selection does not replay via controller's dedup
    assert ctrl.navigation_focus_changed("activity:org.greia.bar", tmp_path / "act/b/locales/it/audio/activity-title.wav", pygame) is False


def test_controller_pointer_dwell_and_cancel(tmp_path: Path) -> None:
    # 4-8. Pointer dwell
    clip = tmp_path / "clip.wav"
    clip.write_bytes(b"x")
    pygame = _FakePygame()
    ctrl = SpokenLabelController(tmp_path, dwell_ms=160)
    now = 100.0
    # pointer enters
    ctrl.pointer_focus_changed("activity:a", clip, now)
    # before dwell, poll does not speak
    assert ctrl.poll_pending_pointer_focus(now + 0.05, pygame) is False
    assert len(pygame.mixer.channel.played) == 0
    # after dwell, speaks once
    assert ctrl.poll_pending_pointer_focus(now + 0.2, pygame) is True
    assert len(pygame.mixer.channel.played) == 1
    # repeated motion inside same tile does not replay (pending already cleared, last_identity prevents)
    ctrl.pointer_focus_changed("activity:a", clip, now + 0.3)
    # because last_identity is activity:a, pending will be set but announce will be deduped
    assert ctrl.poll_pending_pointer_focus(now + 0.5, pygame) is False
    # re-enter after clear should speak again
    ctrl.clear_pointer_focus()
    ctrl.pointer_focus_changed("activity:a", clip, now + 0.6)
    assert ctrl.poll_pending_pointer_focus(now + 0.8, pygame) is True
    assert len(pygame.mixer.channel.played) == 2


def test_controller_rapid_cross_cancels_intermediate(tmp_path: Path) -> None:
    # 7. A -> B -> C faster than dwell -> only C speaks
    cA = tmp_path / "a.wav"
    cB = tmp_path / "b.wav"
    cC = tmp_path / "c.wav"
    for p in (cA, cB, cC):
        p.write_bytes(b"x")
    pygame = _FakePygame()
    ctrl = SpokenLabelController(tmp_path, dwell_ms=160)
    now = 200.0
    ctrl.pointer_focus_changed("activity:a", cA, now)
    ctrl.pointer_focus_changed("activity:b", cB, now + 0.05)
    ctrl.pointer_focus_changed("activity:c", cC, now + 0.1)
    # only C pending
    assert ctrl.poll_pending_pointer_focus(now + 0.3, pygame) is True
    assert pygame.mixer.channel.played[-1][1].endswith("c.wav")
    assert len(pygame.mixer.channel.played) == 1


def test_controller_pointer_leave_cancels(tmp_path: Path) -> None:
    clip = tmp_path / "clip.wav"
    clip.write_bytes(b"x")
    pygame = _FakePygame()
    ctrl = SpokenLabelController(tmp_path, dwell_ms=160)
    now = 300.0
    ctrl.pointer_focus_changed("activity:a", clip, now)
    # leave before dwell
    ctrl.pointer_focus_changed(None, None, now + 0.05)
    assert ctrl.poll_pending_pointer_focus(now + 0.3, pygame) is False
    assert len(pygame.mixer.channel.played) == 0


def test_controller_navigation_immediate_no_dwell(tmp_path: Path) -> None:
    clip = tmp_path / "clip.wav"
    clip.write_bytes(b"x")
    pygame = _FakePygame()
    ctrl = SpokenLabelController(tmp_path, dwell_ms=160)
    # navigation should be immediate, not pending
    assert ctrl.navigation_focus_changed("activity:a", clip, pygame) is True
    assert len(pygame.mixer.channel.played) == 1
    # clamped arrow: same identity does not replay
    assert ctrl.navigation_focus_changed("activity:a", clip, pygame) is False


def test_controller_new_destination_interrupts(tmp_path: Path) -> None:
    c1 = tmp_path / "1.wav"
    c2 = tmp_path / "2.wav"
    for p in (c1, c2):
        p.write_bytes(b"x")
    pygame = _FakePygame()
    ctrl = SpokenLabelController(tmp_path, dwell_ms=160)
    # play first
    assert ctrl.navigation_focus_changed("activity:a", c1, pygame) is True
    assert pygame.mixer.channel.stop_calls == 1
    # new destination should stop previous and play
    assert ctrl.navigation_focus_changed("activity:b", c2, pygame) is True
    assert pygame.mixer.channel.stop_calls == 2
    assert len(pygame.mixer.channel.played) == 2


def test_controller_collection_announce(tmp_path: Path) -> None:
    _make_collection_clip(tmp_path, "create", "it")
    pygame = _FakePygame()
    ctrl = SpokenLabelController(tmp_path, dwell_ms=160)
    assert ctrl.announce_collection("create", "it", pygame) is True
    # same collection again -> no replay
    assert ctrl.announce_collection("create", "it", pygame) is False
    # different -> replay
    _make_collection_clip(tmp_path, "play", "it")
    assert ctrl.announce_collection("play", "it", pygame) is True


def test_controller_missing_clip_fail_silent(tmp_path: Path) -> None:
    pygame = _FakePygame()
    ctrl = SpokenLabelController(tmp_path)
    # missing file -> fail silent, no exception
    assert ctrl.navigation_focus_changed("activity:missing", tmp_path / "missing.wav", pygame) is False
    assert ctrl.announce_collection("create", "it", pygame) is False
    assert len(pygame.mixer.channel.played) == 0


def test_controller_stop_clears_and_allows_replay(tmp_path: Path) -> None:
    clip = tmp_path / "clip.wav"
    clip.write_bytes(b"x")
    pygame = _FakePygame()
    ctrl = SpokenLabelController(tmp_path)
    assert ctrl.navigation_focus_changed("activity:a", clip, pygame) is True
    ctrl.stop()
    # after stop, same identity can speak again (launch scenario)
    assert ctrl.navigation_focus_changed("activity:a", clip, pygame) is True


def test_controller_cache_bounded(tmp_path: Path) -> None:
    pygame = _FakePygame()
    ctrl = SpokenLabelController(tmp_path, dwell_ms=160, cache_entries=2)
    clips = []
    for i in range(5):
        p = tmp_path / f"{i}.wav"
        p.write_bytes(b"x")
        clips.append(p)
        ctrl.navigation_focus_changed(f"activity:{i}", p, pygame)
        # clear so next can be different
        ctrl.clear_pointer_focus()
    # cache should be bounded to 2, but player still works
    assert len(pygame.mixer.sound_calls) == 5
    assert ctrl.player._cache.max_entries == 2  # type: ignore[attr-defined]
    assert len(ctrl.player._cache) <= 2


def test_controller_locale_fallback(tmp_path: Path) -> None:
    # Exact locale fallback is platform-owned, controller uses activity_title_audio which does fallback
    act_root = tmp_path / "act"
    # only en bundle
    _bundle_activity(act_root, "org.greia.foo", "en", "Foo")
    manifest = SimpleNamespace(activity_id="org.greia.foo", root=act_root)
    pygame = _FakePygame()
    ctrl = SpokenLabelController(tmp_path)
    # request it-IT should fall back to it then en
    assert ctrl.announce_activity(manifest, "it-IT", pygame) is True
    # fr with en fallback should also succeed because en exists — use fresh controller to avoid dedup
    pygame2 = _FakePygame()
    ctrl2 = SpokenLabelController(tmp_path)
    assert ctrl2.announce_activity(manifest, "fr", pygame2) is True


def test_controller_locale_fallback_missing_audio(tmp_path: Path) -> None:
    act_root = tmp_path / "act2"
    # only it bundle, no en
    _bundle_activity(act_root, "org.greia.bar", "it", "Bar")
    manifest = SimpleNamespace(activity_id="org.greia.bar", root=act_root)
    pygame = _FakePygame()
    ctrl = SpokenLabelController(tmp_path)
    # fr with only it available should fail (no en to fall back to, and fr not present)
    # it-IT should still succeed via it
    assert ctrl.announce_activity(manifest, "it-IT", pygame) is True
    # fr should fail (no fr, no en)
    # Clear to allow same identity check
    ctrl.clear_pointer_focus()
    ctrl.stop()
    assert ctrl.announce_activity(manifest, "fr", pygame) is False


def test_controller_activity_launch_calls_stop(tmp_path: Path) -> None:
    clip = tmp_path / "clip.wav"
    clip.write_bytes(b"x")
    pygame = _FakePygame()
    ctrl = SpokenLabelController(tmp_path)
    ctrl.navigation_focus_changed("activity:a", clip, pygame)
    assert pygame.mixer.channel.stop_calls == 1
    ctrl.stop()
    assert pygame.mixer.channel.stop_calls == 2
    assert ctrl._pending is None  # type: ignore[attr-defined]


def test_pointer_dwell_does_not_require_redraw(tmp_path: Path) -> None:
    # Ensure poll does not throw and is cheap (no extra imports)
    clip = tmp_path / "clip.wav"
    clip.write_bytes(b"x")
    pygame = _FakePygame()
    ctrl = SpokenLabelController(tmp_path, dwell_ms=160)
    now = 400.0
    ctrl.pointer_focus_changed("activity:a", clip, now)
    # poll multiple times before due should not speak or throw
    for i in range(5):
        assert ctrl.poll_pending_pointer_focus(now + i * 0.02, pygame) is False


def test_target_at_uses_current_frame_reversed_topmost(tmp_path: Path) -> None:
    # Activity grid -> Home -> hover Collection = home_collection (not stale Activity)
    # Home -> Collection -> hover Activity = Activity
    # Overlap resolution follows reversed/topmost click semantics
    from types import SimpleNamespace

    # Minimal fake targets
    class FakeRect:
        def __init__(self, x, y, w, h):
            self.x, self.y, self.width, self.height = x, y, w, h
            self._rect = (x, y, w, h)

        def collidepoint(self, pos):
            px, py = pos
            return self.x <= px < self.x + self.width and self.y <= py < self.y + self.height

    # Simulate _targets with overlapping rects: first is Activity, second is Home Collection on top
    launcher = SimpleNamespace(_targets=[])
    # Add Activity at (0,0,100,100) and Home Collection at (50,50,100,100) overlapping
    launcher._targets.append(SimpleNamespace(action="presented_activity", value=0, rect=FakeRect(0, 0, 100, 100)))
    launcher._targets.append(SimpleNamespace(action="home_collection", value="create", rect=FakeRect(50, 50, 100, 100)))
    # _target_at should return topmost (last in reversed) i.e., home_collection for overlap point (75,75)
    # Use the actual method
    from greia_launcher.presentation import GreiaLauncherPresentation as GLP

    # Bind the method
    result = GLP._target_at(launcher, (75, 75))
    assert result == ("home_collection", "create")
    # Point only in first rect (25,25) should be presented_activity
    assert GLP._target_at(launcher, (25, 25)) == ("presented_activity", 0)
    # Point only in second rect (125,125) should be home_collection
    assert GLP._target_at(launcher, (125, 125)) == ("home_collection", "create")
    # None should return None
    assert GLP._target_at(launcher, None) is None
    # Test that cached targets are not used as fallback (should use _targets only)
    launcher._cached_activities_targets = [SimpleNamespace(action="presented_activity", value=99, rect=FakeRect(75, 75, 10, 10))]
    # Should still return home_collection for (75,75) from _targets, not the cached one
    assert GLP._target_at(launcher, (75, 75)) == ("home_collection", "create")
