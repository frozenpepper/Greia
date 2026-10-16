"""Orchestra Animali — band sounds, approved cast speech and backing tracks.

The Activity ships no packaged instrument audio. ``BandAudio`` synthesizes
the six band instruments (one short strike each, so echo beats stay
countable), the rainbow-xylophone octave and two feedback cues once, after
the first frame; playback never re-decodes or re-synthesizes. Speech uses only
approved shared character takes (``ready.go``, ``praise.general``,
``encourage.retry``, ``celebrate.success``), one take per musician loaded up
front. Loud/soft is a volume set once per toggle. Without a mixer (headless
runs) everything is a silent no-op.
"""

from __future__ import annotations

from array import array
import io
import math
from pathlib import Path
import random
import wave
from dataclasses import dataclass
from typing import Final

import pygame

from greia_platform.creation_media import CreationMediaError, WavCodec
from greia_platform.localization import LocalizationError, shared_character_audio_path
from greia_platform.pygame_audio import DeferredSoundBank

if __package__:
    from .orchestra_content import BAND, BAND_LEADER, NOTE_FREQS, Dynamics
else:
    from orchestra_content import BAND, BAND_LEADER, NOTE_FREQS, Dynamics


SYNTH_RATE: Final = 22050
SPEECH_CHANNEL: Final = 1
MIXER_CHANNELS: Final = 16
PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
SPEECH_FAMILIES: Final = ("ready.go", "praise.general", "encourage.retry")


def _synth_wav(samples: array, rate: int = SYNTH_RATE) -> bytes:
    """Wrap mono PCM16 samples in a WAV container (the mixer converts once)."""

    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(samples.tobytes())
    return buf.getvalue()


def _render(duration: float, voice) -> array:
    """Sample ``voice(t)`` (-1..1) for ``duration`` seconds into clamped PCM16."""

    count = int(SYNTH_RATE * duration)
    out = array("h", bytes(2 * count))
    for index in range(count):
        value = voice(index / SYNTH_RATE)
        out[index] = max(-32767, min(32767, int(value * 30000)))
    return out


@dataclass(frozen=True, slots=True)
class ImportedBackingTrack:
    """Canonical bounded WAV selected through My Creations."""

    wav_bytes: bytes
    duration_seconds: float

    @classmethod
    def from_wav(
        cls,
        payload: bytes,
        *,
        max_duration_seconds: float = 90.0,
    ) -> "ImportedBackingTrack":
        if max_duration_seconds <= 0:
            raise ValueError("backing-track duration bound must be positive")
        try:
            prepared = WavCodec().prepare(payload)
        except CreationMediaError as exc:
            raise ValueError("invalid backing-track WAV") from exc
        duration = float(prepared.attributes.get("duration_seconds", 0.0))
        if duration <= 0.0 or duration > max_duration_seconds:
            raise ValueError("backing track exceeds Orchestra duration")
        return cls(prepared.data, duration)


class BackingTrackPlayer:
    """One reserved mixer channel for optional play-along audio."""

    def __init__(self) -> None:
        self.track: ImportedBackingTrack | None = None
        self._sound: pygame.mixer.Sound | None = None
        self._channel: pygame.mixer.Channel | None = None
        self._paused = False

    @property
    def state(self) -> str:
        if self.track is None:
            return "empty"
        if self._paused:
            return "paused"
        channel = self._channel
        if channel is not None:
            try:
                if channel.get_busy():
                    return "playing"
            except Exception:
                pass
        return "ready"

    def load(self, track: ImportedBackingTrack) -> None:
        self.stop()
        self.track = track

    def clear(self) -> None:
        self.stop()
        self.track = None

    def toggle(self) -> str:
        track = self.track
        if track is None:
            return "empty"
        if self._channel is not None and self._paused:
            try:
                self._channel.unpause()
                self._paused = False
                return "playing"
            except Exception:
                self.stop()
                return "error"
        if self._channel is not None:
            try:
                if self._channel.get_busy():
                    self._channel.pause()
                    self._paused = True
                    return "paused"
            except Exception:
                self.stop()
                return "error"

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(22050, -16, 1, 512)
            # Channel 0 is reserved so rapid child instrument taps cannot steal
            # the backing narration/song from underneath the performance.
            pygame.mixer.set_reserved(1)
            channel = pygame.mixer.Channel(0)
            sound = pygame.mixer.Sound(io.BytesIO(track.wav_bytes))
            channel.play(sound)
        except Exception:
            self.stop()
            return "error"
        self._sound = sound
        self._channel = channel
        self._paused = False
        return "playing"

    def refresh(self) -> bool:
        """Return True exactly once when active playback ends naturally."""
        channel = self._channel
        if channel is None or self._paused:
            return False
        try:
            busy = channel.get_busy()
        except Exception:
            busy = False
        if busy:
            return False
        self._channel = None
        self._sound = None
        return True

    def stop(self) -> None:
        if self._channel is not None:
            try:
                self._channel.stop()
            except Exception:
                pass
        self._channel = None
        self._sound = None
        self._paused = False


class BandAudio:
    """Prepared band sound bank plus approved cast speech (one per Activity run)."""

    def __init__(
        self,
        *,
        locale: str = "en",
        project_root: Path = PROJECT_ROOT,
        rng: random.Random | None = None,
    ) -> None:
        self._rng = rng if rng is not None else random.Random(7)
        # Instruments, bars ("note.<n>") and cues share one bank that is
        # synthesized after the first frame (see DeferredSoundBank).
        self._bank = DeferredSoundBank()
        self._speech: dict[tuple[str, str], pygame.mixer.Sound] = {}
        self.dynamics = Dynamics.LOUD
        self.last_speech: tuple[str, str] | None = None
        self._enabled = False
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pygame.mixer.set_num_channels(max(pygame.mixer.get_num_channels(), MIXER_CHANNELS))
            self._build()
            self._load_speech(project_root, locale)
            self._enabled = True
        except (pygame.error, RuntimeError, OSError, ValueError):
            self._enabled = False
        self.set_dynamics(self.dynamics)

    # -- playback -------------------------------------------------------------

    def play_instrument(self, instrument: str) -> None:
        self._play(self._bank.get(f"instrument.{instrument}"))

    def play_note(self, index: int) -> None:
        if 0 <= index < len(NOTE_FREQS):
            self._play(self._bank.get(f"note.{index}"))

    def cue(self, name: str) -> None:
        self._play(self._bank.get(f"cue.{name}"))

    def say(self, character: str, family: str) -> None:
        """Speak one approved shared take (silent when it is missing)."""

        self.last_speech = (character, family)
        sound = self._speech.get((character, family))
        if not self._enabled or sound is None:
            return
        try:
            pygame.mixer.Channel(SPEECH_CHANNEL).play(sound)
        except (pygame.error, RuntimeError):
            return

    def set_dynamics(self, dynamics: Dynamics) -> None:
        """Loud/soft for every instrument and bar (set once, not per play)."""

        self.dynamics = dynamics
        for name in self._bank:
            if self._bank.built(name) and name.startswith(("instrument.", "note.")):
                try:
                    self._bank[name].set_volume(dynamics.volume)
                except (pygame.error, AttributeError, KeyError):
                    continue

    def _play(self, sound: pygame.mixer.Sound | None) -> None:
        if not self._enabled or sound is None:
            return
        try:
            sound.play()
        except (pygame.error, RuntimeError):
            return

    # -- preparation ----------------------------------------------------------

    def _load_speech(self, project_root: Path, locale: str) -> None:
        wanted = [(m.character, family) for m in BAND for family in SPEECH_FAMILIES]
        wanted.append((BAND_LEADER, "celebrate.success"))
        for character, family in wanted:
            try:
                path = shared_character_audio_path(project_root, character, family, locale)
            except LocalizationError:
                path = None
            if path is None:
                continue
            try:
                self._speech[(character, family)] = pygame.mixer.Sound(str(path))
            except (pygame.error, OSError):
                continue

    def _build(self) -> None:
        noise = self._rng
        voices = {
            "drum": (0.3, _drum),
            "maracas": (0.16, lambda t: noise.uniform(-1, 1) * math.exp(-t * 30.0) * 0.55),
            "bells": (0.6, _bells),
            "trumpet": (0.32, _trumpet),
            "tambourine": (0.24, lambda t: _tambourine(t, noise)),
            "keyboard": (0.45, _keyboard),
        }
        # Maracas and tambourine draw from the run's RNG: render those two now,
        # in their original order, so the RNG sequence is unchanged by deferral.
        eager = {name: _render(*voices[name]) for name in ("maracas", "tambourine")}
        for name, (duration, voice) in voices.items():
            if name in eager:
                samples = eager[name]
                self._bank.define(f"instrument.{name}", lambda samples=samples: self._instrument(samples))
            else:
                self._bank.define(
                    f"instrument.{name}",
                    lambda duration=duration, voice=voice: self._instrument(_render(duration, voice)),
                )
        for index, frequency in enumerate(NOTE_FREQS):
            self._bank.define(
                f"note.{index}",
                lambda f=frequency * 2: self._instrument(_render(0.42, lambda t: _bar(t, f))),
            )
        self._bank.define("cue.fanfare", lambda: self._sound(_render(0.8, _fanfare)))
        self._bank.define("cue.boop", lambda: self._sound(_render(0.24, _boop)))

    def _instrument(self, samples: array) -> pygame.mixer.Sound:
        """An instrument/bar sound at the current loud/soft dynamics."""

        sound = self._sound(samples)
        sound.set_volume(self.dynamics.volume)
        return sound

    @staticmethod
    def _sound(samples: array) -> pygame.mixer.Sound:
        return pygame.mixer.Sound(io.BytesIO(_synth_wav(samples)))


# -- instrument voices (t in seconds -> -1..1) ----------------------------------


def _drum(t: float) -> float:
    pitch = max(52.0, 150.0 - t * 420.0)
    body = math.sin(2 * math.pi * pitch * t) * math.exp(-t * 13.0)
    return body * 0.9


def _bells(t: float) -> float:
    env = math.exp(-t * 5.5)
    f = 1318.5
    return (
        math.sin(2 * math.pi * f * t) * 0.5
        + math.sin(2 * math.pi * f * 2.76 * t) * 0.22 * math.exp(-t * 9.0)
        + math.sin(2 * math.pi * f * 5.4 * t) * 0.1 * math.exp(-t * 14.0)
    ) * env


def _trumpet(t: float) -> float:
    f = 466.16
    attack = min(1.0, t / 0.02)
    release = max(0.0, 1.0 - max(0.0, t - 0.18) / 0.14)
    tone = (
        math.sin(2 * math.pi * f * t) * 0.5
        + math.sin(6 * math.pi * f * t) * 0.25
        + math.sin(10 * math.pi * f * t) * 0.12
        + math.sin(4 * math.pi * f * t) * 0.1
    )
    return tone * attack * release * 0.8


def _tambourine(t: float, rng: random.Random) -> float:
    jingle = math.sin(2 * math.pi * 5200 * t) * 0.5 + math.sin(2 * math.pi * 7300 * t) * 0.5
    return (rng.uniform(-1, 1) * 0.5 + jingle * 0.35) * math.exp(-t * 16.0) * 0.6


def _keyboard(t: float) -> float:
    env = math.exp(-t * 5.0) * min(1.0, t / 0.008)
    value = 0.0
    for f in (261.63, 329.63, 392.0):
        value += math.sin(2 * math.pi * f * t) * 0.28 + math.sin(4 * math.pi * f * t) * 0.08
    return value * env


def _bar(t: float, frequency: float) -> float:
    env = math.exp(-t * 9.0) * min(1.0, t / 0.004)
    return (math.sin(2 * math.pi * frequency * t) * 0.62 + math.sin(2 * math.pi * frequency * 3.93 * t) * 0.12 * math.exp(-t * 30.0)) * env


def _fanfare(t: float) -> float:
    value = 0.0
    for start, length, f in ((0.0, 0.14, 523.25), (0.12, 0.14, 659.25), (0.24, 0.14, 783.99), (0.36, 0.42, 1046.5)):
        if start <= t < start + length:
            local = t - start
            value += math.sin(2 * math.pi * f * local) * math.exp(-3.0 * local / length)
    return value * 0.4


def _boop(t: float) -> float:
    f = 420.0 - 90.0 * t / 0.24
    return math.sin(2 * math.pi * f * t) * math.sin(math.pi * t / 0.24) * 0.3


__all__ = ["BackingTrackPlayer", "BandAudio", "ImportedBackingTrack", "SPEECH_CHANNEL"]
