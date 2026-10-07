"""Bounded, normalized, extensible *data* formats for child creations.

No consumer-supplied extension, MIME claim or filename is trusted as proof of
format. Codecs execute at the trusted import/publish boundary, not in the
child's gallery draw loop. New codecs are registered explicitly by the platform.
"""

from __future__ import annotations

import io
import unicodedata
import wave
from dataclasses import dataclass
from typing import Callable, Mapping, Protocol


class CreationMediaError(ValueError):
    """An artifact is unsupported, malformed, or exceeds the format bounds."""


@dataclass(frozen=True, slots=True)
class PreparedMedia:
    data: bytes
    preview: bytes
    attributes: dict[str, int | float | str]


class CreationMediaCodec(Protocol):
    media_type: str
    extension: str
    max_source_bytes: int

    def prepare(self, raw: bytes) -> PreparedMedia: ...

    def preview(
        self, *, original: Callable[[], bytes], thumbnail: Callable[[], bytes]
    ) -> tuple[str, bytes]: ...


class PngCodec:
    media_type = "image/png"
    extension = "png"
    max_source_bytes = 8 * 1024 * 1024
    max_pixels = 4_000_000
    max_side = 3_200
    thumbnail_size = (384, 320)

    def prepare(self, raw: bytes) -> PreparedMedia:
        if len(raw) > self.max_source_bytes or not raw.startswith(b"\x89PNG\r\n\x1a\n"):
            raise CreationMediaError("PNG header or encoded image size is invalid")
        try:
            from PIL import Image, UnidentifiedImageError
        except ImportError as exc:
            raise CreationMediaError("PNG decoder unavailable") from exc
        try:
            with Image.open(io.BytesIO(raw)) as source:
                if source.format != "PNG" or getattr(source, "n_frames", 1) != 1:
                    raise CreationMediaError("only static PNG images are supported")
                w, h = source.size
                if (
                    min(w, h) < 1
                    or max(w, h) > self.max_side
                    or w * h > self.max_pixels
                ):
                    raise CreationMediaError("PNG dimensions exceed the bounded decoder policy")
                # Convert and re-encode to shed untrusted ancillary metadata.
                image = source.convert("RGBA")
            output = io.BytesIO()
            image.save(output, format="PNG")
            canonical = output.getvalue()
            if len(canonical) > self.max_source_bytes:
                raise CreationMediaError("canonical PNG exceeds size policy")
            image.thumbnail(self.thumbnail_size, Image.Resampling.LANCZOS)
            thumbnail = io.BytesIO()
            image.save(thumbnail, format="PNG")
            return PreparedMedia(canonical, thumbnail.getvalue(), {"width": w, "height": h})
        except (OSError, ValueError, SyntaxError, UnidentifiedImageError) as exc:
            if isinstance(exc, CreationMediaError):
                raise
            raise CreationMediaError("PNG failed bounded decoding") from exc

    def preview(
        self, *, original: Callable[[], bytes], thumbnail: Callable[[], bytes]
    ) -> tuple[str, bytes]:
        return self.media_type, thumbnail()


class WavCodec:
    media_type = "audio/wav"
    extension = "wav"
    max_source_bytes = 16 * 1024 * 1024
    max_duration_seconds = 90.0

    def prepare(self, raw: bytes) -> PreparedMedia:
        if len(raw) > self.max_source_bytes or not raw.startswith(b"RIFF"):
            raise CreationMediaError("WAV header or audio file size is invalid")
        try:
            with wave.open(io.BytesIO(raw), "rb") as source:
                channels = source.getnchannels()
                rate = source.getframerate()
                width = source.getsampwidth()
                frames = source.getnframes()
                if (
                    channels not in (1, 2)
                    or width not in (1, 2)
                    or not 8_000 <= rate <= 48_000
                    or frames < 1
                    or frames / rate > self.max_duration_seconds
                    or source.getcomptype() != "NONE"
                ):
                    raise CreationMediaError("WAV audio format/duration exceeds supported limits")
                pcm = source.readframes(frames)
                if len(pcm) != frames * channels * width:
                    raise CreationMediaError("WAV PCM data is truncated")
            output = io.BytesIO()
            with wave.open(output, "wb") as target:
                target.setnchannels(channels)
                target.setsampwidth(width)
                target.setframerate(rate)
                target.writeframes(pcm)
            canonical = output.getvalue()
            if len(canonical) > self.max_source_bytes:
                raise CreationMediaError("canonical WAV exceeds size policy")
            # Audio preview deliberately means *play the actual clip* on demand.
            # We do not create a duplicate preview file or autoplay recordings.
            return PreparedMedia(canonical, b"", {
                "duration_seconds": round(frames / rate, 3),
                "channels": channels,
                "sample_rate": rate,
            })
        except (EOFError, OSError, ValueError, wave.Error) as exc:
            if isinstance(exc, CreationMediaError):
                raise
            raise CreationMediaError("WAV could not be decoded") from exc

    def preview(
        self, *, original: Callable[[], bytes], thumbnail: Callable[[], bytes]
    ) -> tuple[str, bytes]:
        return self.media_type, original()


class Utf8TextCodec:
    media_type = "text/plain"
    extension = "txt"
    max_source_bytes = 256 * 1024

    def prepare(self, raw: bytes) -> PreparedMedia:
        if len(raw) > self.max_source_bytes:
            raise CreationMediaError("text is too large")
        try:
            decoded = raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise CreationMediaError("text must be UTF-8") from exc
        normalized = unicodedata.normalize("NFC", decoded.replace("\r\n", "\n"))
        if any(ord(character) < 32 and character not in "\n\t" for character in normalized):
            raise CreationMediaError("text contains unsupported control characters")
        encoded = normalized.encode("utf-8")
        if len(encoded) > self.max_source_bytes:
            raise CreationMediaError("normalized text is too large")
        preview = normalized[:280].encode("utf-8")
        return PreparedMedia(encoded, preview, {"character_count": len(normalized)})

    def preview(
        self, *, original: Callable[[], bytes], thumbnail: Callable[[], bytes]
    ) -> tuple[str, bytes]:
        return self.media_type, original()[:1024]


class CreationMediaRegistry:
    """Explicit extensibility seam; codecs own format-specific normalization."""

    def __init__(self, codecs: Mapping[str, CreationMediaCodec] | None = None):
        candidates = (PngCodec(), WavCodec(), Utf8TextCodec()) if codecs is None else codecs.values()
        result: dict[str, CreationMediaCodec] = {}
        for codec in candidates:
            if codec.media_type in result:
                raise ValueError(f"duplicate creation media codec: {codec.media_type}")
            result[codec.media_type] = codec
        self._codecs = result

    def codec_for(self, media_type: str) -> CreationMediaCodec:
        try:
            return self._codecs[media_type]
        except (KeyError, TypeError) as exc:
            raise CreationMediaError(f"unsupported creation media type: {media_type!r}") from exc
