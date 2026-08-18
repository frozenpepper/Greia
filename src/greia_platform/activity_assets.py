from __future__ import annotations

from pathlib import Path

from .activities import ActivityManifest, ActivityValidationError


PACKAGE_ICON_PREFIX = "package:"
_ALLOWED_ICON_SUFFIXES = frozenset({".png", ".webp"})
MAX_ICON_BYTES = 4 * 1024 * 1024
MAX_ICON_DIMENSION = 1024
MAX_ICON_PIXELS = 1024 * 1024
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


class ActivityAssetError(ActivityValidationError):
    """An Activity-owned presentation asset violates the package boundary."""


def package_icon_path(manifest: ActivityManifest) -> Path | None:
    """Resolve and validate an optional package-owned launcher icon.

    Existing Activities continue to use global catalogue IDs such as ``paint``.
    Portable packages may instead declare ``package:assets/icon.png``. The
    Activity tree validator already rejects symlinks; this resolver additionally
    constrains the manifest reference and rejects malformed or unreasonably large
    images before a child-facing renderer attempts to decode them.
    """

    value = manifest.icon_id.strip()
    if not value.startswith(PACKAGE_ICON_PREFIX):
        return None
    relative_text = value.removeprefix(PACKAGE_ICON_PREFIX).strip()
    if not relative_text:
        raise ActivityAssetError("package Activity icon path is empty")
    relative = Path(relative_text)
    if relative.is_absolute() or ".." in relative.parts or "." in relative.parts:
        raise ActivityAssetError("package Activity icon must be a safe relative path")
    if len(relative.parts) > 6 or len(relative_text) > 180:
        raise ActivityAssetError("package Activity icon path is too deep or long")
    suffix = relative.suffix.casefold()
    if suffix not in _ALLOWED_ICON_SUFFIXES:
        raise ActivityAssetError("package Activity icon must be PNG or WebP")
    try:
        root = manifest.root.resolve(strict=True)
        resolved = (root / relative).resolve(strict=True)
        resolved.relative_to(root)
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise ActivityAssetError(
            "package Activity icon does not resolve inside the package"
        ) from exc
    if not resolved.is_file():
        raise ActivityAssetError("package Activity icon is not a file")
    _validate_icon_file(resolved, suffix)
    return resolved


def _validate_icon_file(path: Path, suffix: str) -> None:
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise ActivityAssetError("package Activity icon cannot be inspected") from exc
    if size <= 0 or size > MAX_ICON_BYTES:
        raise ActivityAssetError(
            f"package Activity icon must be between 1 and {MAX_ICON_BYTES} bytes"
        )
    try:
        with path.open("rb") as handle:
            header = handle.read(64)
    except OSError as exc:
        raise ActivityAssetError("package Activity icon cannot be read") from exc

    if suffix == ".png":
        dimensions = _png_dimensions(header)
    elif suffix == ".webp":
        dimensions = _webp_dimensions(header)
    else:  # pragma: no cover - guarded by the suffix allowlist above.
        raise ActivityAssetError("unsupported package Activity icon format")
    _validate_dimensions(*dimensions)


def _png_dimensions(header: bytes) -> tuple[int, int]:
    # Signature + IHDR length/type + width/height are all available in 24 bytes.
    if len(header) < 24 or header[:8] != _PNG_SIGNATURE:
        raise ActivityAssetError("package Activity PNG icon has an invalid header")
    if header[12:16] != b"IHDR" or int.from_bytes(header[8:12], "big") != 13:
        raise ActivityAssetError("package Activity PNG icon is missing a valid IHDR")
    return (
        int.from_bytes(header[16:20], "big"),
        int.from_bytes(header[20:24], "big"),
    )


def _webp_dimensions(header: bytes) -> tuple[int, int]:
    # A launcher icon must expose its dimensions in the first image/header chunk.
    # This covers the three standard WebP bitstream forms without importing an
    # image decoder into package validation.
    if (
        len(header) < 30
        or header[:4] != b"RIFF"
        or header[8:12] != b"WEBP"
    ):
        raise ActivityAssetError("package Activity WebP icon has an invalid header")
    chunk = header[12:16]
    chunk_size = int.from_bytes(header[16:20], "little")
    payload = header[20:]
    if chunk == b"VP8X":
        if chunk_size < 10 or len(payload) < 10:
            raise ActivityAssetError("package Activity WebP VP8X header is truncated")
        width = 1 + int.from_bytes(payload[4:7], "little")
        height = 1 + int.from_bytes(payload[7:10], "little")
        return width, height
    if chunk == b"VP8L":
        if chunk_size < 5 or len(payload) < 5 or payload[0] != 0x2F:
            raise ActivityAssetError("package Activity WebP VP8L header is invalid")
        bits = int.from_bytes(payload[1:5], "little")
        return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
    if chunk == b"VP8 ":
        if (
            chunk_size < 10
            or len(payload) < 10
            or payload[3:6] != b"\x9d\x01\x2a"
        ):
            raise ActivityAssetError("package Activity WebP VP8 header is invalid")
        return (
            int.from_bytes(payload[6:8], "little") & 0x3FFF,
            int.from_bytes(payload[8:10], "little") & 0x3FFF,
        )
    raise ActivityAssetError("package Activity WebP icon uses an unsupported header")


def _validate_dimensions(width: int, height: int) -> None:
    if width <= 0 or height <= 0:
        raise ActivityAssetError("package Activity icon dimensions must be positive")
    if width > MAX_ICON_DIMENSION or height > MAX_ICON_DIMENSION:
        raise ActivityAssetError(
            f"package Activity icon dimensions must not exceed {MAX_ICON_DIMENSION}x{MAX_ICON_DIMENSION}"
        )
    if width * height > MAX_ICON_PIXELS:
        raise ActivityAssetError("package Activity icon has too many pixels")
