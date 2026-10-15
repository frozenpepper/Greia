"""Pure domain/state model for Teatrino delle Fiabe.

No pygame, storage or platform APIs at import time. Owns:

* ``ShowRepository`` - the bounded, never-evicting saved-show shelf with
  content-addressed custom backdrops;
* ``DeleteConfirmation`` - the deliberate keep/delete step;
* ``Puppet`` / ``Stage`` - the puppets on stage (at most ``MAX_ON_STAGE``,
  one of each), their gestures and the drag/remove rules;
* ``ShowRecorder`` / ``ShowPlayback`` - sampling a performance into bounded
  frames and replaying it with interpolation.

Saved-show data stays schema-compatible with shows recorded before the
rework (frames of ``{t, puppets: [{id, x, y, flip, jumping, talking}]}`` and
``{t, sound}`` sfx events); new fields are optional additions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import math
import time
import uuid

if __package__:
    from .teatrino_content import (
        MAX_FRAMES,
        MAX_ON_STAGE,
        MAX_SAVED_SHOWS,
        MAX_SFX_EVENTS,
        RECORD_HZ,
        SHOWS_INDEX_KEY,
    )
else:
    from teatrino_content import (
        MAX_FRAMES,
        MAX_ON_STAGE,
        MAX_SAVED_SHOWS,
        MAX_SFX_EVENTS,
        RECORD_HZ,
        SHOWS_INDEX_KEY,
    )


class ShowStorageError(RuntimeError):
    """A saved show could not be committed to Greia private storage."""


class ShowLibraryFullError(ShowStorageError):
    """The show shelf is full; the child must delete a show on purpose.

    Saving never evicts older child work to make room. The bound is an Activity
    UX safeguard well under the platform Storage quota (a 45 s mono show WAV is
    roughly 1.5 MiB, so 16 shows stay near 25 MiB at most).
    """


class DeleteConfirmation:
    """Pure state for the deliberate "delete this?" step shown before removal.

    The dialog always opens with the safe choice (keep) focused, so a stray
    Space/Enter or controller south-button press never deletes. The destructive
    choice only works after a short arming delay, which also absorbs a
    double-tap that opened and then immediately confirmed the dialog.
    """

    KEEP = "keep"
    DELETE = "delete"
    ARM_SECONDS = 0.6

    def __init__(self, target_id: str, opened_at: float) -> None:
        self.target_id = target_id
        self.opened_at = float(opened_at)
        self.focus = self.KEEP

    def move_focus(self) -> None:
        """Toggle between the two buttons (left/right/up/down all do this)."""
        self.focus = self.DELETE if self.focus == self.KEEP else self.KEEP

    def armed(self, now: float) -> bool:
        return (float(now) - self.opened_at) >= self.ARM_SECONDS

    def resolve(self, choice: str, now: float) -> str | None:
        """Return ``keep``/``delete`` when the choice takes effect, else ``None``."""
        if choice == self.KEEP:
            return self.KEEP
        if choice == self.DELETE and self.armed(now):
            return self.DELETE
        return None


class ShowRepository:
    """Bounded saved shows with deduplicated content-addressed custom backdrops.

    The repository never evicts a saved show: when the shelf holds
    ``MAX_SAVED_SHOWS`` it raises :class:`ShowLibraryFullError` and the child
    deletes a show deliberately before saving another.
    """

    MAX_BACKDROP_BYTES = 8 * 1024 * 1024
    BACKDROP_PREFIX = "backdrop_"

    def __init__(self, storage) -> None:
        self.storage = storage
        self._mem_index: list[dict] = []
        self._mem_files: dict[str, bytes] = {}

    @classmethod
    def _backdrop_name(cls, digest: str) -> str:
        return f"{cls.BACKDROP_PREFIX}{digest}.png"

    @staticmethod
    def _show_json_name(show_id: str) -> str:
        return f"show_{show_id}.json"

    @staticmethod
    def _show_wav_name(show_id: str) -> str:
        return f"show_{show_id}.wav"

    def _storage_index(self, *, strict: bool) -> list[dict]:
        if self.storage is None:
            return list(self._mem_index[:MAX_SAVED_SHOWS])
        try:
            raw = self.storage.kv_get(SHOWS_INDEX_KEY, [])
        except Exception as exc:
            if strict:
                raise ShowStorageError("show index could not be read") from exc
            return []
        if not isinstance(raw, list):
            if strict:
                raise ShowStorageError("show index is invalid")
            return []
        cleaned: list[dict] = []
        for item in raw:
            if isinstance(item, dict) and isinstance(item.get("id"), str):
                cleaned.append(item)
        return cleaned[:MAX_SAVED_SHOWS]

    def is_full(self) -> bool:
        """True when another show would be refused by the shelf bound."""
        return len(self.list_shows()) >= MAX_SAVED_SHOWS

    def list_shows(self) -> list[dict]:
        if self.storage is None:
            return list(self._mem_index[:MAX_SAVED_SHOWS])
        return self._storage_index(strict=False)

    @staticmethod
    def _referenced_backdrops(index: list[dict]) -> set[str]:
        return {
            item["backdrop_sha256"]
            for item in index
            if isinstance(item, dict)
            and item.get("has_custom_backdrop")
            and isinstance(item.get("backdrop_sha256"), str)
        }

    def save_show(
        self,
        backdrop_id: str,
        puppets: list[dict],
        frames: list[dict],
        sfx_events: list[dict],
        duration: float,
        audio_wav_bytes: bytes | None = None,
        backdrop_png_bytes: bytes | None = None,
        *,
        poster: list[dict] | None = None,
    ) -> dict:
        """Commit one show; ``poster`` is the stage line-up for its card.

        ``poster`` is a short list of ``{id, x, y, flip}`` (the puppets as the
        curtain closed). It lives in the small index entry so library cards
        can draw a poster without reading the large frame file.
        """
        if backdrop_png_bytes is not None and (
            not isinstance(backdrop_png_bytes, bytes)
            or not backdrop_png_bytes
            or len(backdrop_png_bytes) > self.MAX_BACKDROP_BYTES
        ):
            raise ValueError("custom backdrop exceeds bounds")

        old_shows = (
            self._storage_index(strict=True)
            if self.storage is not None
            else self.list_shows()
        )
        if len(old_shows) >= MAX_SAVED_SHOWS:
            raise ShowLibraryFullError("show shelf is full")
        show_id = uuid.uuid4().hex[:12]
        backdrop_digest = (
            hashlib.sha256(backdrop_png_bytes).hexdigest()
            if backdrop_png_bytes
            else None
        )
        show_meta = {
            "id": show_id,
            "title": f"Storia {len(old_shows) + 1}",
            "backdrop": backdrop_id,
            "actors": [p["id"] for p in puppets],
            "duration": round(duration, 1),
            "has_audio": bool(audio_wav_bytes),
            "has_custom_backdrop": backdrop_digest is not None,
            "backdrop_sha256": backdrop_digest,
            "created_at": time.time(),
        }
        if poster:
            show_meta["poster"] = [
                {
                    "id": str(item["id"]),
                    "x": round(float(item["x"]), 1),
                    "y": round(float(item["y"]), 1),
                    "flip": bool(item.get("flip", False)),
                }
                for item in poster[:MAX_ON_STAGE]
                if isinstance(item, dict) and isinstance(item.get("id"), str)
            ]
        show_payload = {
            "metadata": show_meta,
            "puppets": puppets,
            "frames": frames,
            "sfx_events": sfx_events,
        }
        json_bytes = json.dumps(show_payload, separators=(",", ":")).encode("utf-8")

        if self.storage is None:
            self._save_memory_only(
                show_meta,
                json_bytes,
                audio_wav_bytes,
                backdrop_png_bytes,
            )
            return show_meta

        old_backdrops = self._referenced_backdrops(old_shows)
        new_shows = [
            show_meta,
            *[item for item in old_shows if item.get("id") != show_id],
        ]
        try:
            self.storage.file_write_atomic(
                self._show_json_name(show_id), json_bytes
            )
            if audio_wav_bytes:
                self.storage.file_write_atomic(
                    self._show_wav_name(show_id), bytes(audio_wav_bytes)
                )
            if backdrop_digest is not None and backdrop_png_bytes is not None:
                self.storage.file_write_atomic(
                    self._backdrop_name(backdrop_digest), backdrop_png_bytes
                )
            self.storage.kv_set(SHOWS_INDEX_KEY, new_shows)
        except Exception as exc:
            self._rollback_failed_save(
                show_id,
                backdrop_digest=backdrop_digest,
                old_backdrops=old_backdrops,
            )
            raise ShowStorageError("show could not be saved") from exc

        self._cleanup_storage_backdrops(new_shows)
        return show_meta

    def _save_memory_only(
        self,
        show_meta: dict,
        json_bytes: bytes,
        audio_wav_bytes: bytes | None,
        backdrop_png_bytes: bytes | None,
    ) -> None:
        show_id = show_meta["id"]
        self._mem_files[self._show_json_name(show_id)] = json_bytes
        if audio_wav_bytes:
            self._mem_files[self._show_wav_name(show_id)] = bytes(audio_wav_bytes)
        digest = show_meta.get("backdrop_sha256")
        if isinstance(digest, str) and backdrop_png_bytes:
            self._mem_files[self._backdrop_name(digest)] = backdrop_png_bytes
        self._mem_index = [
            show_meta,
            *[item for item in self._mem_index if item.get("id") != show_id],
        ]
        self._cleanup_mem_backdrops()

    def _rollback_failed_save(
        self,
        show_id: str,
        *,
        backdrop_digest: str | None,
        old_backdrops: set[str],
    ) -> None:
        if self.storage is None:
            return
        try:
            self.storage.file_delete(self._show_json_name(show_id))
            self.storage.file_delete(self._show_wav_name(show_id))
            if (
                backdrop_digest is not None
                and backdrop_digest not in old_backdrops
            ):
                self.storage.file_delete(self._backdrop_name(backdrop_digest))
        except Exception:
            pass

    def load_show(self, show_id: str) -> tuple[dict | None, bytes | None]:
        if self.storage is None:
            json_bytes = self._mem_files.get(self._show_json_name(show_id))
            wav_bytes = self._mem_files.get(self._show_wav_name(show_id))
        else:
            try:
                json_bytes = self.storage.file_read(self._show_json_name(show_id))
            except Exception:
                json_bytes = None
            try:
                wav_bytes = self.storage.file_read(self._show_wav_name(show_id))
            except Exception:
                wav_bytes = None

        if not json_bytes:
            return None, wav_bytes
        try:
            show_data = json.loads(json_bytes.decode("utf-8"))
        except Exception:
            show_data = None
        if not isinstance(show_data, dict):
            show_data = None
        return show_data, wav_bytes

    def load_show_backdrop(self, show_id: str) -> bytes | None:
        meta = next(
            (item for item in self.list_shows() if item.get("id") == show_id),
            None,
        )
        if not isinstance(meta, dict) or not meta.get("has_custom_backdrop"):
            return None
        expected = meta.get("backdrop_sha256")
        if not isinstance(expected, str):
            return None
        name = self._backdrop_name(expected)
        if self.storage is None:
            payload = self._mem_files.get(name)
        else:
            try:
                payload = self.storage.file_read(name)
            except Exception:
                return None
        if (
            not isinstance(payload, bytes)
            or not payload
            or len(payload) > self.MAX_BACKDROP_BYTES
            or hashlib.sha256(payload).hexdigest() != expected
        ):
            return None
        return payload

    def write_private_file(self, name: str, payload: bytes) -> bool:
        """Write one private file (the poster to publish); False when impossible."""
        if self.storage is None:
            return False
        try:
            self.storage.file_write_atomic(name, payload)
        except Exception:
            return False
        return True

    def _delete_mem_show_files(self, show_id: str) -> None:
        self._mem_files.pop(self._show_json_name(show_id), None)
        self._mem_files.pop(self._show_wav_name(show_id), None)

    def _delete_storage_show_files(self, show_id: str) -> None:
        if self.storage is None:
            return
        for name in (
            self._show_json_name(show_id),
            self._show_wav_name(show_id),
        ):
            try:
                self.storage.file_delete(name)
            except Exception:
                pass

    def _cleanup_mem_backdrops(self) -> None:
        keep = {
            self._backdrop_name(digest)
            for digest in self._referenced_backdrops(self._mem_index)
        }
        for name in tuple(self._mem_files):
            if name.startswith(self.BACKDROP_PREFIX) and name not in keep:
                self._mem_files.pop(name, None)

    def _cleanup_storage_backdrops(self, index: list[dict]) -> None:
        if self.storage is None:
            return
        keep = {
            self._backdrop_name(digest)
            for digest in self._referenced_backdrops(index)
        }
        try:
            names = self.storage.file_list(prefix=self.BACKDROP_PREFIX)
        except Exception:
            return
        for name in names[: MAX_SAVED_SHOWS + 4]:
            if name not in keep:
                try:
                    self.storage.file_delete(name)
                except Exception:
                    pass

    def delete_show(self, show_id: str) -> None:
        if self.storage is None:
            self._mem_index = [
                item for item in self._mem_index if item.get("id") != show_id
            ]
            self._delete_mem_show_files(show_id)
            self._cleanup_mem_backdrops()
            return

        try:
            shows = [
                item
                for item in self._storage_index(strict=True)
                if item.get("id") != show_id
            ]
            self.storage.kv_set(SHOWS_INDEX_KEY, shows)
        except Exception:
            return
        self._delete_storage_show_files(show_id)
        self._cleanup_storage_backdrops(shows)


# ---------------------------------------------------------------------------
# Puppets on stage
# ---------------------------------------------------------------------------

TALK_SECONDS = 1.1
JUMP_SECONDS = 0.6
BOW_SECONDS = 0.9
REACT_SECONDS = 1.2
TALK_FLAPS_PER_SECOND = 4.0
MAX_TILT = 8.0


@dataclass(slots=True)
class Puppet:
    """One rod puppet on stage: position plus short-lived gesture timers.

    ``(x, y)`` is the centre of the puppet's body in 1024x600 stage space
    (saved shows store exactly this). Timers count down in seconds so the
    gesture speed never depends on the frame rate. Rendering is owned by the
    renderer; this class never imports pygame.
    """

    puppet_id: str
    x: float
    y: float
    flip: bool = False
    held: bool = False
    talk_timer: float = 0.0
    jump_timer: float = 0.0
    bow_timer: float = 0.0
    react_timer: float = 0.0
    reaction: str | None = None
    tilt: float = 0.0
    voice_talking: bool = False
    clock: float = 0.0
    half_width: float = 62.0
    half_height: float = 70.0
    _last_x: float = field(default=0.0, repr=False)

    def __post_init__(self) -> None:
        self.x = float(self.x)
        self.y = float(self.y)
        self._last_x = self.x

    # -- gestures --------------------------------------------------------
    def speak(self, seconds: float = TALK_SECONDS) -> None:
        self.talk_timer = max(self.talk_timer, float(seconds))

    def jump(self) -> None:
        self.jump_timer = JUMP_SECONDS

    def bow(self) -> None:
        self.bow_timer = BOW_SECONDS

    def react(self, variant: str | None) -> None:
        """Show a sound-sticker reaction (a cast variant) and hop."""
        self.reaction = variant
        self.react_timer = REACT_SECONDS
        self.jump()

    @property
    def talking(self) -> bool:
        return self.talk_timer > 0.0 or self.voice_talking

    @property
    def jumping(self) -> bool:
        return self.jump_timer > 0.0

    @property
    def mouth_open(self) -> bool:
        """Mouth flap phase while talking (open on even half-beats)."""
        if not self.talking:
            return False
        return int(self.clock * TALK_FLAPS_PER_SECOND * 2) % 2 == 0

    def jump_offset(self) -> float:
        """Upward hop in px (0 when standing)."""
        if self.jump_timer <= 0.0:
            return 0.0
        progress = 1.0 - self.jump_timer / JUMP_SECONDS
        return math.sin(math.pi * progress) * 46.0

    def talk_offset(self) -> float:
        if not self.talking:
            return 0.0
        return math.sin(self.clock * 18.0) * 3.5

    def bow_dip(self) -> float:
        """Downward nod in px during a bow: two little dips toward the audience."""
        if self.bow_timer <= 0.0:
            return 0.0
        progress = 1.0 - self.bow_timer / BOW_SECONDS
        return abs(math.sin(2.0 * math.pi * progress)) * 16.0

    @property
    def animating(self) -> bool:
        return (
            self.held
            or self.talking
            or self.jump_timer > 0.0
            or self.bow_timer > 0.0
            or self.react_timer > 0.0
            or abs(self.tilt) > 0.5
        )

    def update(self, dt: float) -> None:
        """Advance timers by ``dt`` seconds and derive the motion tilt."""
        dt = max(0.0, min(0.25, float(dt)))
        self.clock += dt
        self.talk_timer = max(0.0, self.talk_timer - dt)
        self.jump_timer = max(0.0, self.jump_timer - dt)
        self.bow_timer = max(0.0, self.bow_timer - dt)
        self.react_timer = max(0.0, self.react_timer - dt)
        if self.react_timer <= 0.0:
            self.reaction = None
        dx = self.x - self._last_x
        if abs(dx) > 1.5:
            self.flip = dx < 0.0
            # Whole-body lean stays within the cast rule (<= 8 degrees).
            self.tilt = max(-MAX_TILT, min(MAX_TILT, -dx * 1.2))
        else:
            self.tilt *= 0.7
            if abs(self.tilt) < 0.5:
                self.tilt = 0.0
        self._last_x = self.x

    # -- geometry --------------------------------------------------------
    def contains(self, px: float, py: float) -> bool:
        return (
            self.x - self.half_width <= px <= self.x + self.half_width
            and self.y - self.half_height <= py <= self.y + self.half_height + 24
        )

    def rect_tuple(self) -> tuple[int, int, int, int]:
        return (
            int(self.x - self.half_width),
            int(self.y - self.half_height),
            int(self.half_width * 2),
            int(self.half_height * 2),
        )


@dataclass(frozen=True, slots=True)
class StageBounds:
    """Where puppet centres may go; below ``remove_y`` a puppet goes home."""

    left: float
    top: float
    right: float
    bottom: float
    remove_y: float

    def clamp(self, x: float, y: float, *, allow_remove: bool = False) -> tuple[float, float]:
        bottom = self.remove_y + 40.0 if allow_remove else self.bottom
        return (max(self.left, min(self.right, x)), max(self.top, min(bottom, y)))


DEFAULT_BOUNDS = StageBounds(210.0, 150.0, 814.0, 430.0, 470.0)


class Stage:
    """The puppets on stage, in draw order (last = front).

    Rules (child-sized and predictable): one of each puppet, at most
    ``MAX_ON_STAGE``; a newcomer pops up at the freest spot; dragging a
    puppet down into the tray (below ``remove_y``) takes it off stage.
    """

    def __init__(self, bounds: StageBounds = DEFAULT_BOUNDS) -> None:
        self.bounds = bounds
        self.puppets: list[Puppet] = []

    # -- membership --------------------------------------------------------
    def find(self, puppet_id: str) -> Puppet | None:
        return next((p for p in self.puppets if p.puppet_id == puppet_id), None)

    def ids(self) -> tuple[str, ...]:
        return tuple(p.puppet_id for p in self.puppets)

    @property
    def full(self) -> bool:
        return len(self.puppets) >= MAX_ON_STAGE

    def add(self, puppet_id: str, *, x: float | None = None, y: float | None = None) -> Puppet | None:
        """Bring a puppet on stage; ``None`` when it is already there or full."""
        if self.find(puppet_id) is not None or self.full:
            return None
        if x is None:
            x = self.free_x()
        if y is None:
            y = (self.bounds.top + self.bounds.bottom) / 2 + 40.0
        x, y = self.bounds.clamp(x, y)
        puppet = Puppet(puppet_id, x, y)
        self.puppets.append(puppet)
        return puppet

    def remove(self, puppet_id: str) -> bool:
        before = len(self.puppets)
        self.puppets = [p for p in self.puppets if p.puppet_id != puppet_id]
        return len(self.puppets) != before

    def clear(self) -> None:
        self.puppets = []

    def free_x(self) -> float:
        """The x farthest from every puppet already on stage."""
        # Keep newcomers clear of the curtains' edges.
        left, right = self.bounds.left + 40.0, self.bounds.right - 40.0
        if not self.puppets:
            return (left + right) / 2
        best_x, best_gap = left, -1.0
        steps = 24
        for index in range(steps + 1):
            candidate = left + (right - left) * index / steps
            gap = min(abs(candidate - p.x) for p in self.puppets)
            if gap > best_gap:
                best_x, best_gap = candidate, gap
        return best_x

    # -- interaction -------------------------------------------------------
    def hit(self, x: float, y: float) -> Puppet | None:
        for puppet in reversed(self.puppets):
            if puppet.contains(x, y):
                return puppet
        return None

    def raise_to_front(self, puppet: Puppet) -> None:
        if puppet in self.puppets:
            self.puppets.remove(puppet)
            self.puppets.append(puppet)

    def move(self, puppet: Puppet, x: float, y: float, *, allow_remove: bool = False) -> None:
        puppet.x, puppet.y = self.bounds.clamp(x, y, allow_remove=allow_remove)

    def in_remove_zone(self, puppet: Puppet) -> bool:
        return puppet.y > self.bounds.remove_y

    def update(self, dt: float) -> None:
        for puppet in self.puppets:
            puppet.update(dt)

    @property
    def animating(self) -> bool:
        return any(p.animating for p in self.puppets)

    def snapshot(self) -> list[dict]:
        """The line-up as plain data (poster / restore after watching)."""
        return [
            {"id": p.puppet_id, "x": round(p.x, 1), "y": round(p.y, 1), "flip": p.flip}
            for p in self.puppets
        ]

    def restore(self, line_up: list[dict], known: set[str] | frozenset[str]) -> None:
        self.puppets = []
        for item in line_up:
            if not isinstance(item, dict):
                continue
            puppet_id = item.get("id")
            if puppet_id not in known or self.find(puppet_id) is not None or self.full:
                continue
            try:
                x, y = float(item.get("x", 512)), float(item.get("y", 300))
            except (TypeError, ValueError):
                continue
            puppet = Puppet(puppet_id, x, y)
            puppet.flip = bool(item.get("flip", False))
            self.puppets.append(puppet)


# ---------------------------------------------------------------------------
# Recording and playback
# ---------------------------------------------------------------------------


class ShowRecorder:
    """Sample the stage into bounded frames while a show is recorded.

    Frames keep the original schema (one entry per puppet per sample) at
    ``RECORD_HZ``; sound stickers are separate ``{t, sound}`` events. Both
    lists are hard-bounded, so a 45 s show stays a few hundred KiB of JSON.
    """

    def __init__(self, *, hz: int = RECORD_HZ) -> None:
        self._interval = 1.0 / max(1, int(hz))
        self.frames: list[dict] = []
        self.sfx: list[dict] = []
        self._started = 0.0
        self._next = 0.0
        self.active = False

    def start(self, now: float) -> None:
        self.frames = []
        self.sfx = []
        self._started = float(now)
        self._next = float(now)
        self.active = True

    def elapsed(self, now: float) -> float:
        return max(0.0, float(now) - self._started) if self.active else 0.0

    def sample(self, now: float, stage: Stage, *, force: bool = False) -> bool:
        if not self.active or len(self.frames) >= MAX_FRAMES:
            return False
        if not force and now < self._next:
            return False
        self._next = float(now) + self._interval
        self.frames.append(
            {
                "t": round(self.elapsed(now), 2),
                "puppets": [
                    {
                        "id": p.puppet_id,
                        "x": round(p.x, 1),
                        "y": round(p.y, 1),
                        "flip": p.flip,
                        "jumping": p.jumping,
                        "talking": p.talking,
                    }
                    for p in stage.puppets
                ],
            }
        )
        return True

    def note_sfx(self, now: float, sound: str) -> None:
        if self.active and len(self.sfx) < MAX_SFX_EVENTS:
            self.sfx.append({"t": round(self.elapsed(now), 2), "sound": sound})

    def stop(self) -> None:
        self.active = False


@dataclass(frozen=True, slots=True)
class PuppetPose:
    """One puppet's interpolated place at a playback instant."""

    puppet_id: str
    x: float
    y: float
    flip: bool
    jumping: bool
    talking: bool


class ShowPlayback:
    """Replay saved frames: linear interpolation by puppet occurrence.

    Puppets are matched by ``(id, n-th occurrence)`` so old shows that held
    two of the same puppet still replay. Frame times must be non-decreasing;
    the frame cursor only moves forward while time advances.
    """

    def __init__(self, frames: list[dict], sfx: list[dict], duration: float) -> None:
        self.frames = [f for f in frames if isinstance(f, dict) and isinstance(f.get("puppets"), list)]
        self.sfx = sorted(
            (e for e in sfx if isinstance(e, dict) and isinstance(e.get("sound"), str)),
            key=lambda e: float(e.get("t", 0.0)),
        )
        last = float(self.frames[-1].get("t", 0.0)) if self.frames else 0.0
        self.duration = max(1.0, float(duration or 0.0), last)
        self._cursor = 0
        self._sfx_cursor = 0
        self._actors: dict[str, Puppet] = {}

    def cast_ids(self) -> list[str]:
        """Every puppet id that appears, in first-appearance order."""
        seen: list[str] = []
        for frame in self.frames:
            for item in frame["puppets"]:
                puppet_id = item.get("id") if isinstance(item, dict) else None
                if isinstance(puppet_id, str) and puppet_id not in seen:
                    seen.append(puppet_id)
        return seen

    def rewind(self) -> None:
        self._cursor = 0
        self._sfx_cursor = 0
        self._actors = {}

    def drive(self, stage: Stage, t: float, known: set[str] | frozenset[str]) -> list[str]:
        """Put the puppets where the show had them at ``t``; return due sounds.

        One puppet per id is shown (older shows could hold duplicates); the
        stage's draw order follows the recorded order at that moment.
        """
        line: list[Puppet] = []
        seen: set[str] = set()
        for pose in self.poses_at(t):
            if pose.puppet_id in seen or pose.puppet_id not in known:
                continue
            seen.add(pose.puppet_id)
            puppet = self._actors.get(pose.puppet_id)
            if puppet is None:
                puppet = Puppet(pose.puppet_id, pose.x, pose.y)
                self._actors[pose.puppet_id] = puppet
            puppet.x, puppet.y = pose.x, pose.y
            puppet.flip = pose.flip
            if pose.jumping and not puppet.jumping:
                puppet.jump()
            if pose.talking:
                puppet.speak(0.15)
            line.append(puppet)
        stage.puppets = line
        return self.due_sfx(t)

    @staticmethod
    def _keyed(frame: dict) -> dict[tuple[str, int], dict]:
        counts: dict[str, int] = {}
        keyed: dict[tuple[str, int], dict] = {}
        for item in frame["puppets"]:
            if not isinstance(item, dict) or not isinstance(item.get("id"), str):
                continue
            index = counts.get(item["id"], 0)
            counts[item["id"]] = index + 1
            keyed[(item["id"], index)] = item
        return keyed

    def poses_at(self, t: float) -> list[PuppetPose]:
        if not self.frames:
            return []
        frames = self.frames
        if t < float(frames[self._cursor].get("t", 0.0)):
            self._cursor = 0
        while self._cursor + 1 < len(frames) and float(frames[self._cursor + 1].get("t", 0.0)) <= t:
            self._cursor += 1
        prev = frames[self._cursor]
        nxt = frames[min(self._cursor + 1, len(frames) - 1)]
        span = max(0.01, float(nxt.get("t", 0.0)) - float(prev.get("t", 0.0)))
        ratio = min(1.0, max(0.0, (t - float(prev.get("t", 0.0))) / span))
        following = self._keyed(nxt)
        poses: list[PuppetPose] = []
        for key, item in self._keyed(prev).items():
            target = following.get(key, item)
            try:
                x0, y0 = float(item.get("x", 512)), float(item.get("y", 300))
                x1, y1 = float(target.get("x", x0)), float(target.get("y", y0))
            except (TypeError, ValueError):
                continue
            poses.append(
                PuppetPose(
                    key[0],
                    x0 + (x1 - x0) * ratio,
                    y0 + (y1 - y0) * ratio,
                    bool(item.get("flip", False)),
                    bool(item.get("jumping", False)),
                    bool(item.get("talking", False)),
                )
            )
        return poses

    def due_sfx(self, t: float) -> list[str]:
        due: list[str] = []
        while self._sfx_cursor < len(self.sfx) and float(self.sfx[self._sfx_cursor].get("t", 0.0)) <= t:
            due.append(self.sfx[self._sfx_cursor]["sound"])
            self._sfx_cursor += 1
        return due

    def finished(self, t: float) -> bool:
        return t >= self.duration


__all__ = [
    "DEFAULT_BOUNDS",
    "DeleteConfirmation",
    "Puppet",
    "PuppetPose",
    "ShowLibraryFullError",
    "ShowPlayback",
    "ShowRecorder",
    "ShowRepository",
    "ShowStorageError",
    "Stage",
    "StageBounds",
]
