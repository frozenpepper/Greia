"""Renderer-neutral Greia child Creations picker and library controller.

Owned by the trusted Shell. A sandboxed Activity may not construct a chooser
that mints its own grants or browse this data source through a broker.
This controller intentionally does not import pygame or own audio hardware.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Callable, Protocol

from .creations import CreationRecord


class GalleryMode(StrEnum):
    LIBRARY = "library"
    PICKER = "picker"


class CreationFamily(StrEnum):
    ALL = "all"
    IMAGE = "image"
    AUDIO = "audio"
    TEXT = "text"

    @property
    def media_type(self) -> str | None:
        return {
            CreationFamily.ALL: None,
            CreationFamily.IMAGE: "image/png",
            CreationFamily.AUDIO: "audio/wav",
            CreationFamily.TEXT: "text/plain",
        }[self]


class GalleryError(RuntimeError):
    """Child-facing gallery operation failed with a bounded error message."""


class CreationsRepository(Protocol):
    def list(
        self, *, media_type: str | None = None, media_types: tuple[str, ...] | None = None,
        limit: int = 24, offset: int = 0
    ) -> tuple[CreationRecord, ...]: ...

    def preview(self, creation_id: str) -> tuple[str, bytes]: ...

    def read(self, creation_id: str) -> bytes: ...

    def delete(self, creation_id: str) -> bool: ...


class AudioPreviewPlayer(Protocol):
    def play(self, wav_bytes: bytes) -> None: ...

    def pause(self) -> None: ...

    def resume(self) -> None: ...

    def is_playing(self) -> bool: ...

    def stop(self) -> None: ...


@dataclass(frozen=True, slots=True)
class GalleryPage:
    family: CreationFamily
    index: int
    items: tuple[CreationRecord, ...]
    has_previous: bool
    has_next: bool
    focused_id: str | None
    detail_id: str | None
    pending_delete_id: str | None
    playing_id: str | None
    paused_id: str | None
    selected_handle: str | None


class CreationsGalleryController:
    """One state owner shared by the picker and standalone library viewer.

    Page operations retrieve at most three metadata records at once, plus one
    look-ahead. Detailed previews are requested lazily by presentation code;
    audio payloads are loaded only after the child explicitly asks to listen.

    For PICKER, the trusted caller passes a callback that mints a selection
    token on the active session's CreationSessionAccess. That callback is never
    serialized or reachable through the Activity storage broker.
    """

    MAX_PAGE_SIZE = 3

    def __init__(
        self,
        library: CreationsRepository,
        *,
        mode: GalleryMode = GalleryMode.LIBRARY,
        media_types: frozenset[str] | None = None,
        on_pick: Callable[[str], str] | None = None,
        audio_player: AudioPreviewPlayer | None = None,
        page_size: int = 2,
    ) -> None:
        if type(page_size) is not int or not 1 <= page_size <= self.MAX_PAGE_SIZE:
            raise ValueError("gallery page size outside resource bound")
        if mode == GalleryMode.PICKER and on_pick is None:
            raise ValueError("trusted picker requires an actual selection grant owner")
        if mode == GalleryMode.LIBRARY and on_pick is not None:
            raise ValueError("the library viewer cannot mint selection grants")
        allowed = frozenset({"image/png", "audio/wav", "text/plain"} if media_types is None else media_types)
        if not allowed or allowed - {"image/png", "audio/wav", "text/plain"}:
            raise ValueError("invalid picker media types")
        self.library = library
        self.mode = mode
        self.allowed = allowed
        self.on_pick = on_pick
        self.audio_player = audio_player
        self.page_size = page_size
        self.family = CreationFamily.ALL
        self.page_index = 0
        self._items: tuple[CreationRecord, ...] = ()
        self._has_next = False
        self.focused_id: str | None = None
        self.detail_id: str | None = None
        self.pending_delete_id: str | None = None
        self.playing_id: str | None = None
        self.paused_id: str | None = None
        self.selected_handle: str | None = None
        self.closed = False
        self.refresh()

    @property
    def families(self) -> tuple[CreationFamily, ...]:
        return (CreationFamily.ALL,) + tuple(
            family for family in (CreationFamily.IMAGE, CreationFamily.AUDIO, CreationFamily.TEXT)
            if family.media_type in self.allowed
        )

    @property
    def page(self) -> GalleryPage:
        return GalleryPage(
            family=self.family,
            index=self.page_index,
            items=self._items,
            has_previous=self.page_index > 0,
            has_next=self._has_next,
            focused_id=self.focused_id,
            detail_id=self.detail_id,
            pending_delete_id=self.pending_delete_id,
            playing_id=self.playing_id,
            paused_id=self.paused_id,
            selected_handle=self.selected_handle,
        )

    def _check_open(self) -> None:
        if self.closed:
            raise GalleryError("gallery has closed")

    def _stop_playback(self) -> None:
        if self.audio_player is not None:
            self.audio_player.stop()
        self.playing_id = None
        self.paused_id = None

    def refresh(self) -> None:
        self._check_open()
        media_type = self.family.media_type
        if media_type is not None:
            raw = self.library.list(
                media_type=media_type, limit=self.page_size + 1, offset=self.page_index * self.page_size
            )
            visible = raw[: self.page_size]
            extra = len(raw) > self.page_size
        else:
            if len(self.allowed) == 3:
                raw = self.library.list(limit=self.page_size + 1, offset=self.page_index * self.page_size)
                visible = raw[: self.page_size]
                extra = len(raw) > self.page_size
            else:
                # The repository handles this as one indexed, bounded query.
                # Never scan every file or load unbounded pages to join MIME
                # families in Python. This remains trusted-Shell-only.
                raw = self.library.list(
                    media_types=tuple(sorted(self.allowed)),
                    limit=self.page_size + 1,
                    offset=self.page_index * self.page_size,
                )
                visible = raw[: self.page_size]
                extra = len(raw) > self.page_size
        if not visible and self.page_index > 0:
            self.page_index -= 1
            return self.refresh()
        self._items = tuple(visible)
        self._has_next = extra
        self.focused_id = self._items[0].creation_id if self._items else None

    def set_page_size(self, size: int) -> None:
        """Reflow on device resize without expanding metadata/cache budgets."""
        self._check_open()
        if type(size) is not int or not 1 <= size <= self.MAX_PAGE_SIZE:
            raise ValueError("invalid gallery page size")
        if size == self.page_size:
            return
        self._stop_playback()
        self.page_size = size
        self.page_index = 0
        self.detail_id = None
        self.pending_delete_id = None
        self.refresh()

    def set_family(self, family: CreationFamily) -> None:
        self._check_open()
        if family not in self.families:
            raise GalleryError("the requested media family is not available")
        if family == self.family:
            return
        self._stop_playback()
        self.family = family
        self.page_index = 0
        self.detail_id = None
        self.pending_delete_id = None
        self.refresh()

    def next_page(self) -> bool:
        self._check_open()
        if not self._has_next:
            return False
        self._stop_playback()
        self.page_index += 1
        self.detail_id = None
        self.pending_delete_id = None
        self.refresh()
        return True

    def previous_page(self) -> bool:
        self._check_open()
        if self.page_index == 0:
            return False
        self._stop_playback()
        self.page_index -= 1
        self.detail_id = None
        self.pending_delete_id = None
        self.refresh()
        return True

    def focus_item(self, creation_id: str) -> None:
        self._check_open()
        if creation_id not in {item.creation_id for item in self._items}:
            raise GalleryError("creation is not on the visible page")
        self.focused_id = creation_id

    def open_item(self, creation_id: str) -> None:
        self._check_open()
        if creation_id not in {item.creation_id for item in self._items}:
            raise GalleryError("creation is not on the visible page")
        self._stop_playback()
        self.focused_id = creation_id
        self.detail_id = creation_id
        self.pending_delete_id = None

    def close_item(self) -> None:
        self._check_open()
        self._stop_playback()
        self.detail_id = None
        self.pending_delete_id = None

    def preview(self, creation_id: str) -> tuple[str, bytes]:
        self._check_open()
        if creation_id not in {item.creation_id for item in self._items}:
            raise GalleryError("creation preview is not on the visible page")
        return self.library.preview(creation_id)

    def full_image(self, creation_id: str) -> bytes:
        """Original PNG is available only for an opened picture preview."""
        self._check_open()
        record = next((item for item in self._items if item.creation_id == creation_id), None)
        if self.detail_id != creation_id or record is None or record.media_type != "image/png":
            raise GalleryError("full-resolution picture requires an opened image")
        return self.library.read(creation_id)

    def poll_playback(self) -> bool:
        """Clear stale Play indication after a recording naturally finishes."""
        if self.playing_id is None or self.paused_id is not None:
            return False
        busy = getattr(self.audio_player, "is_playing", None)
        if callable(busy) and not busy():
            self._stop_playback()
            return False
        return True

    def toggle_audio(self, creation_id: str) -> bool:
        self._check_open()
        item = next((item for item in self._items if item.creation_id == creation_id), None)
        if item is None or item.media_type != "audio/wav":
            raise GalleryError("this is not a visible audio recording")
        if self.playing_id == creation_id:
            if self.audio_player is None:
                self._stop_playback()
                return False
            if self.paused_id == creation_id:
                self.audio_player.resume()
                self.paused_id = None
                return True
            self.audio_player.pause()
            self.paused_id = creation_id
            return False
        if self.audio_player is None:
            raise GalleryError("audio preview player is unavailable")
        self._stop_playback()
        kind, wav = self.preview(creation_id)
        if kind != "audio/wav":
            raise GalleryError("recording preview did not contain WAV audio")
        self.audio_player.play(wav)
        self.playing_id = creation_id
        self.paused_id = None
        return True

    def replay_audio(self, creation_id: str) -> None:
        """Explicitly restart a recording from its beginning, even if paused."""
        self._check_open()
        item = next((item for item in self._items if item.creation_id == creation_id), None)
        if item is None or item.media_type != "audio/wav" or self.audio_player is None:
            raise GalleryError("recording preview is unavailable")
        self._stop_playback()
        kind, wav = self.preview(creation_id)
        if kind != "audio/wav":
            raise GalleryError("recording preview did not contain WAV audio")
        self.audio_player.play(wav)
        self.playing_id = creation_id

    def ask_delete(self) -> None:
        self._check_open()
        if self.mode != GalleryMode.LIBRARY or self.detail_id is None:
            raise GalleryError("deletion is only available in My Creations")
        self._stop_playback()
        self.pending_delete_id = self.detail_id

    def cancel_delete(self) -> None:
        self._check_open()
        self.pending_delete_id = None

    def confirm_delete(self) -> bool:
        self._check_open()
        if self.mode != GalleryMode.LIBRARY or self.pending_delete_id is None:
            raise GalleryError("deletion requires an explicit confirmation")
        item_id = self.pending_delete_id
        self._stop_playback()
        result = self.library.delete(item_id)
        self.pending_delete_id = None
        self.detail_id = None
        self.refresh()
        return result

    def choose(self) -> str:
        self._check_open()
        if self.mode != GalleryMode.PICKER or self.detail_id is None or self.on_pick is None:
            raise GalleryError("a visible selection is required")
        item = next((item for item in self._items if item.creation_id == self.detail_id), None)
        if item is None or item.media_type not in self.allowed:
            raise GalleryError("selected creation is not compatible")
        if self.selected_handle is not None:
            raise GalleryError("selection has already been confirmed")
        self._stop_playback()
        handle = self.on_pick(item.creation_id)
        if not isinstance(handle, str) or not handle:
            raise GalleryError("trusted picker failed to issue a selection handle")
        self.selected_handle = handle
        return handle

    def close(self) -> None:
        if self.closed:
            return
        self._stop_playback()
        self.closed = True
