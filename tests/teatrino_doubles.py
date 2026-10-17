"""Test doubles for Teatrino delle Fiabe: storage, clock, audio, creations.

``make_app`` builds the real ``TeatrinoApp`` on a dummy SDL display with
in-memory storage, a manual clock and silent audio, so tests drive the same
input -> step -> render loop the child uses.
"""
from __future__ import annotations

import os
from pathlib import Path
import sys
from types import SimpleNamespace

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from activities.teatrino_fiabe.teatrino_app import TeatrinoApp  # noqa: E402


class MemoryStorage:
    """Minimal profile-scoped Activity storage (kv + private files)."""

    def __init__(self) -> None:
        self.kv: dict[str, object] = {}
        self.files: dict[str, bytes] = {}
        self.fail_kv = False
        self.fail_get = False

    def kv_get(self, key, default=None):
        if self.fail_get:
            raise RuntimeError("read failed")
        return self.kv.get(key, default)

    def kv_set(self, key, value):
        if self.fail_kv:
            raise RuntimeError("kv failed")
        self.kv[key] = value

    def file_write_atomic(self, name, data):
        self.files[name] = bytes(data)

    def file_read(self, name):
        if name not in self.files:
            raise RuntimeError("missing")
        return self.files[name]

    def file_delete(self, name):
        return self.files.pop(name, None) is not None

    def file_list(self, prefix=None):
        return tuple(sorted(n for n in self.files if not prefix or n.startswith(prefix)))


class ManualClock:
    def __init__(self, start: float = 1000.0) -> None:
        self.now = float(start)

    def __call__(self) -> float:
        return self.now


class SilentSounds:
    def __init__(self) -> None:
        self.played: list[str] = []

    def play(self, name: str) -> None:
        self.played.append(name)

    def stop_all(self) -> None:
        pass


class SilentHost:
    def __init__(self) -> None:
        self.said: list[str] = []

    def say(self, cue: str) -> float:
        self.said.append(cue)
        return 0.0

    def say_if_quiet(self, cue: str) -> float:
        return self.say(cue)

    def stop(self) -> None:
        pass


class FakeMic:
    def __init__(self) -> None:
        self.enabled = True
        self.current_volume = 0.0
        self.started = 0
        self.stopped = 0

    def toggle(self) -> bool:
        self.enabled = not self.enabled
        return self.enabled

    def start_recording(self) -> None:
        self.started += 1

    def stop_recording(self):
        self.stopped += 1
        return b"RIFF-microphone-wav-" + bytes(40)


class FakeCreations:
    """Platform picker double: records requests; replies are set per test."""

    def __init__(self) -> None:
        self.requests: list[tuple] = []
        self.polls: list[str] = []
        self.published: list[tuple] = []
        self.reply = SimpleNamespace(state="pending", selection_token=None)
        self.transfer = None

    def request_selection(self, *, media_types, roles=()):
        self.requests.append((media_types, roles))
        return f"request-{len(self.requests)}"

    def poll_selection(self, request_id):
        self.polls.append(request_id)
        return self.reply

    def import_selected(self, token):
        return self.transfer

    def publish_private_file(self, filename, *, media_type, role, title=""):
        self.published.append((filename, media_type, role))
        return {}


def make_app(
    *,
    size: tuple[int, int] = (1024, 600),
    storage: MemoryStorage | None = None,
    creations=None,
    clock: ManualClock | None = None,
    events: list | None = None,
) -> TeatrinoApp:
    pygame.init()
    screen = pygame.display.set_mode(size)
    recorded = events if events is not None else []
    return TeatrinoApp(
        screen,
        storage=storage if storage is not None else MemoryStorage(),
        creations=creations,
        locale="en",
        clock=clock if clock is not None else ManualClock(),
        sounds=SilentSounds(),
        microphone=FakeMic(),
        host_voice=SilentHost(),
        emit_event=lambda event_id, **kwargs: recorded.append((event_id, kwargs)),
    )


def advance(app: TeatrinoApp, seconds: float, *, fps: int = 30, render: bool = False) -> None:
    """Advance the manual clock, stepping (and optionally rendering) each frame."""

    clock = app.clock
    for _ in range(max(1, int(seconds * fps))):
        clock.now += 1.0 / fps  # type: ignore[attr-defined]
        app.step()
        if render:
            app.render()


def record_show(app: TeatrinoApp, seconds: float = 2.0) -> dict | None:
    """Press record, wait out the curtain ritual, perform, press stop."""

    app.tap(app.layout.rec.center)
    advance(app, 3.0)
    assert app.is_recording, "capture starts when the curtain opens"
    advance(app, seconds)
    app.tap(app.layout.rec.center)
    advance(app, 1.0)
    return app.saved_meta


__all__ = [
    "FakeCreations",
    "FakeMic",
    "ManualClock",
    "MemoryStorage",
    "SilentHost",
    "SilentSounds",
    "advance",
    "make_app",
    "record_show",
]
