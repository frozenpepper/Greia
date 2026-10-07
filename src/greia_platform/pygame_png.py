"""Shared bounded PNG conversion helpers for Pygame Activities.

Keep PIL/Pygame pixel conversion in one place so Painting, Shape Garden and
future trusted creative Activities use the same fit/letterbox semantics.
"""

from __future__ import annotations

import io

from PIL import Image, UnidentifiedImageError
import pygame


class PygamePngError(ValueError):
    """PNG bytes/surface conversion failed."""


def decode_png_surface(
    payload: bytes,
    target_size: tuple[int, int],
    *,
    background: tuple[int, int, int] = (255, 255, 255),
) -> pygame.Surface:
    if not isinstance(payload, bytes) or not payload:
        raise PygamePngError("PNG payload must be non-empty bytes")
    width, height = target_size
    if (
        type(width) is not int
        or type(height) is not int
        or width <= 0
        or height <= 0
        or width * height > 4_000_000
    ):
        raise PygamePngError("invalid PNG target size")
    try:
        with Image.open(io.BytesIO(payload)) as image:
            if image.format != "PNG":
                raise PygamePngError("payload is not PNG")
            converted = image.convert("RGB")
            if converted.size != target_size:
                converted.thumbnail(target_size, Image.Resampling.LANCZOS)
                fitted = Image.new("RGB", target_size, background)
                fitted.paste(
                    converted,
                    (
                        (width - converted.width) // 2,
                        (height - converted.height) // 2,
                    ),
                )
                converted = fitted
            surface = pygame.image.fromstring(
                converted.tobytes(), converted.size, "RGB"
            )
            return surface.convert()
    except (UnidentifiedImageError, OSError, ValueError, pygame.error) as exc:
        if isinstance(exc, PygamePngError):
            raise
        raise PygamePngError("PNG could not be decoded") from exc


def encode_surface_png(surface: pygame.Surface) -> bytes:
    try:
        width, height = surface.get_size()
    except Exception as exc:
        raise PygamePngError("invalid Pygame surface") from exc
    if (
        type(width) is not int
        or type(height) is not int
        or width <= 0
        or height <= 0
        or width * height > 4_000_000
    ):
        raise PygamePngError("surface exceeds PNG conversion bounds")
    try:
        image = Image.frombytes(
            "RGBA",
            (width, height),
            pygame.image.tostring(surface, "RGBA"),
        )
        output = io.BytesIO()
        image.save(output, format="PNG", optimize=False)
        return output.getvalue()
    except (OSError, ValueError, pygame.error) as exc:
        raise PygamePngError("surface could not be encoded as PNG") from exc


__all__ = ["PygamePngError", "decode_png_surface", "encode_surface_png"]
