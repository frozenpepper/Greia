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


class ShowRepository:
    """Manages persistent saved shows and companion audio narration tracks."""

    def __init__(self, storage) -> None:
        self.storage = storage
        self._mem_index: list[dict] = []
        self._mem_files: dict[str, bytes] = {}

    def list_shows(self) -> list[dict]:
        if self.storage is not None:
            try:
                raw = self.storage.kv_get(SHOWS_INDEX_KEY, [])
                if isinstance(raw, list):
                    cleaned: list[dict] = []
                    for item in raw:
                        if isinstance(item, dict) and "id" in item:
                            cleaned.append(item)
                    return cleaned[:MAX_SAVED_SHOWS]
            except Exception:
                pass
        return list(self._mem_index[:MAX_SAVED_SHOWS])

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
        show_id = uuid.uuid4().hex[:12]
        show_meta = {
            "id": show_id,
            "title": f"Storia {len(self.list_shows()) + 1}",
            "backdrop": backdrop_id,
            "actors": [p["id"] for p in puppets],
            "duration": round(duration, 1),
            "has_audio": bool(audio_wav_bytes and len(audio_wav_bytes) > 0),
            "has_custom_backdrop": bool(backdrop_png_bytes),
            "backdrop_sha256": (
                hashlib.sha256(backdrop_png_bytes).hexdigest()
                if backdrop_png_bytes
                else None
            ),
            "created_at": time.time(),
        }

        show_payload = {
            "metadata": show_meta,
            "puppets": puppets,
            "frames": frames,
            "sfx_events": sfx_events,
        }

        json_bytes = json.dumps(show_payload).encode("utf-8")
        self._mem_files[f"show_{show_id}.json"] = json_bytes
        if audio_wav_bytes:
            self._mem_files[f"show_{show_id}.wav"] = audio_wav_bytes
        if backdrop_png_bytes:
            self._mem_files[f"show_{show_id}_backdrop.png"] = backdrop_png_bytes
        prior_index = [s for s in self._mem_index if s.get("id") != show_id]
        dropped = prior_index[MAX_SAVED_SHOWS - 1 :]
        self._mem_index = [show_meta, *prior_index][:MAX_SAVED_SHOWS]
        for old in dropped:
            old_id = old.get("id")
            if isinstance(old_id, str):
                self._delete_mem_files(old_id)

        if self.storage is not None:
            try:
                self.storage.file_write_atomic(f"show_{show_id}.json", json_bytes)
                if audio_wav_bytes:
                    self.storage.file_write_atomic(f"show_{show_id}.wav", audio_wav_bytes)
                if backdrop_png_bytes:
                    self.storage.file_write_atomic(
                        f"show_{show_id}_backdrop.png", backdrop_png_bytes
                    )
                shows = self.list_shows()
                old_ids = [
                    item.get("id")
                    for item in shows[MAX_SAVED_SHOWS - 1 :]
                    if isinstance(item, dict)
                ]
                new_shows = [
                    show_meta,
                    *[item for item in shows if item.get("id") != show_id],
                ][:MAX_SAVED_SHOWS]
                self.storage.kv_set(SHOWS_INDEX_KEY, new_shows)
                for old_id in old_ids:
                    if isinstance(old_id, str) and old_id != show_id:
                        self._delete_storage_files(old_id)
            except Exception:
                pass

        return show_meta

    def load_show(self, show_id: str) -> tuple[dict | None, bytes | None]:
        json_bytes = self._mem_files.get(f"show_{show_id}.json")
        wav_bytes = self._mem_files.get(f"show_{show_id}.wav")

        if json_bytes is None and self.storage is not None:
            try:
                json_bytes = self.storage.file_read(f"show_{show_id}.json")
            except Exception:
                json_bytes = None

        if wav_bytes is None and self.storage is not None:
            try:
                wav_bytes = self.storage.file_read(f"show_{show_id}.wav")
            except Exception:
                wav_bytes = None

        show_data = None
        if json_bytes:
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
        name = f"show_{show_id}_backdrop.png"
        payload = self._mem_files.get(name)
        if payload is None and self.storage is not None:
            try:
                payload = self.storage.file_read(name)
            except Exception:
                return None
        if (
            not isinstance(payload, bytes)
            or len(payload) > 8 * 1024 * 1024
            or hashlib.sha256(payload).hexdigest() != expected
        ):
            return None
        return payload

    def _delete_mem_files(self, show_id: str) -> None:
        self._mem_files.pop(f"show_{show_id}.json", None)
        self._mem_files.pop(f"show_{show_id}.wav", None)
        self._mem_files.pop(f"show_{show_id}_backdrop.png", None)

    def _delete_storage_files(self, show_id: str) -> None:
        if self.storage is None:
            return
        for name in (
            f"show_{show_id}.json",
            f"show_{show_id}.wav",
            f"show_{show_id}_backdrop.png",
        ):
            try:
                self.storage.file_delete(name)
            except Exception:
                pass

    def delete_show(self, show_id: str) -> None:
        self._mem_index = [s for s in self._mem_index if s.get("id") != show_id]
        self._delete_mem_files(show_id)
        if self.storage is not None:
            try:
                shows = [s for s in self.list_shows() if s.get("id") != show_id]
                self.storage.kv_set(SHOWS_INDEX_KEY, shows)
                self._delete_storage_files(show_id)
            except Exception:
                pass


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


__all__ = ["ShowRepository", "Puppet", "AmbientSpark"]
