from __future__ import annotations

from pathlib import Path

from .activities import ActivityManifest, ActivityValidationError


PACKAGE_ICON_PREFIX = "package:"
_ALLOWED_ICON_SUFFIXES = frozenset({".png", ".webp"})


class ActivityAssetError(ActivityValidationError):
    """An Activity-owned presentation asset violates the package boundary."""


def package_icon_path(manifest: ActivityManifest) -> Path | None:
    """Resolve an optional package-owned icon without escaping the package.

    Existing Activities continue to use global catalogue IDs such as ``paint``.
    Portable packages may instead declare ``package:assets/icon.png``. The
    Activity tree validator already rejects symlinks; this resolver additionally
    constrains the manifest reference itself and is shared by installer and UI.
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
    if relative.suffix.casefold() not in _ALLOWED_ICON_SUFFIXES:
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
    return resolved
