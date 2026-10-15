"""Pure domain/state model for Teatrino delle Fiabe.

No pygame, storage or platform APIs at import time. Owns the
persistent show library in-memory contract and the interactive puppet
and ambient spark state machines.
"""

from __future__ import annotations

import hashlib
import json
import random
import time
import uuid
from dataclasses import dataclass

if __package__:
    from .teatrino_content import MAX_SAVED_SHOWS, SHOWS_INDEX_KEY
else:
    from teatrino_content import MAX_SAVED_SHOWS, SHOWS_INDEX_KEY


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
    ) -> dict:
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
        show_payload = {
            "metadata": show_meta,
            "puppets": puppets,
            "frames": frames,
            "sfx_events": sfx_events,
        }
        json_bytes = json.dumps(show_payload).encode("utf-8")

        if self.storage is None:
            self._save_memory_only(
                show_meta,
                json_bytes,
                audio_wav_bytes,
                backdrop_png_bytes,
            )
            return show_meta

        old_backdrops = self._referenced_backdrops(old_shows)
        candidates = [
            show_meta,
            *[item for item in old_shows if item.get("id") != show_id],
        ]
        new_shows = candidates
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


@dataclass(slots=True)
class Puppet:
    """Interactive theatrical puppet with wooden rod and physics state.

    Pure state owner: position, held/talk/jump timers, flip/tilt.
    Rendering is owned by teatrino_renderer / teatrino_assets.
    """

    puppet_id: str
    name: str
    x: float
    y: float
    target_x: float = 0.0
    target_y: float = 0.0
    is_held: bool = False
    flip_x: bool = False
    tilt_angle: float = 0.0
    talk_timer: float = 0.0
    jump_timer: float = 0.0
    size: int = 110
    shadow_size: int = 90

    def __init__(self, puppet_id: str, name: str, x: float, y: float) -> None:
        # Custom init to keep original constructor signature.
        object.__setattr__(self, "puppet_id", puppet_id)
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "x", float(x))
        object.__setattr__(self, "y", float(y))
        object.__setattr__(self, "target_x", float(x))
        object.__setattr__(self, "target_y", float(y))
        object.__setattr__(self, "is_held", False)
        object.__setattr__(self, "flip_x", False)
        object.__setattr__(self, "tilt_angle", 0.0)
        object.__setattr__(self, "talk_timer", 0.0)
        object.__setattr__(self, "jump_timer", 0.0)
        object.__setattr__(self, "size", 110)
        object.__setattr__(self, "shadow_size", 90)
        object.__setattr__(self, "_last_x", float(x))

    # _last_x is not a dataclass field to preserve original private attribute.
    _last_x: float = 0.0

    def contains(self, px: int, py: int) -> bool:
        half = self.size // 2
        return (self.x - half <= px <= self.x + half) and (self.y - half <= py <= self.y + half + 40)

    def jump(self) -> None:
        self.jump_timer = 1.0

    def speak(self) -> None:
        self.talk_timer = 1.0

    def update(self) -> None:
        if self.talk_timer > 0.0:
            self.talk_timer = max(0.0, self.talk_timer - 0.04)
        if self.jump_timer > 0.0:
            self.jump_timer = max(0.0, self.jump_timer - 0.05)

        dx = self.x - getattr(self, "_last_x", self.x)
        if abs(dx) > 1.5:
            self.flip_x = dx < 0.0
            self.tilt_angle = max(-15.0, min(15.0, -dx * 1.8))
        else:
            self.tilt_angle *= 0.85
        self._last_x = self.x

    # Back-compat: original Puppet had a draw() method that owned rendering.
    # Keep a thin delegation so old callers still function, but the canonical
    # drawing path is teatrino_renderer.draw_puppet().
    def draw(self, surface, sprite_img, typography) -> None:  # type: ignore[no-untyped-def]
        # Lazy local import to avoid circular dependency and keep model pure
        # at import time; rendering is delegated to the renderer module.
        try:
            if __package__:
                from .teatrino_renderer import draw_puppet
            else:
                from teatrino_renderer import draw_puppet
            draw_puppet(surface, self, sprite_img, typography)
        except Exception:
            # Fallback: at least update timers if renderer unavailable.
            self.update()


class AmbientSpark:
    """Floating ambient spark particle owned by the stage backdrop."""

    def __init__(self, bg_id: str) -> None:
        self.bg_id = bg_id
        self.x = random.uniform(140, 900)
        self.y = random.uniform(80, 420)
        self.speed_y = random.uniform(-0.6, -0.2)
        self.speed_x = random.uniform(-0.3, 0.3)
        self.alpha = random.uniform(0.3, 1.0)
        self.size = random.uniform(2.0, 4.5)

    def update(self) -> None:
        self.y += self.speed_y
        self.x += self.speed_x
        self.alpha -= 0.008
        if self.y < 70 or self.alpha <= 0.0:
            self.x = random.uniform(140, 900)
            self.y = random.uniform(320, 420)
            self.alpha = random.uniform(0.6, 1.0)

    def draw(self, surface) -> None:  # type: ignore[no-untyped-def]
        # Keep back-compat for callers that expect spark.draw(surface);
        # canonical path is teatrino_renderer.draw_ambient_spark.
        try:
            if __package__:
                from .teatrino_renderer import draw_ambient_spark
            else:
                from teatrino_renderer import draw_ambient_spark
            draw_ambient_spark(surface, self)
        except Exception:
            pass


__all__ = [
    "DeleteConfirmation",
    "ShowLibraryFullError",
    "ShowRepository",
    "ShowStorageError",
    "Puppet",
    "AmbientSpark",
]
