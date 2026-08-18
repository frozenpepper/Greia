from __future__ import annotations

from pathlib import Path

from greia_platform.activities import ActivityManifest, ActivityValidationError


PACKAGE_ICON_PREFIX = "package:"
_ALLOWED_SUFFIXES = frozenset({".png", ".webp"})


class ActivityIconError(ActivityValidationError):
    pass


def package_icon_path(manifest: ActivityManifest) -> Path | None:
    """Resolve an optional Activity-owned icon without escaping its package.

    Existing core Activities continue to use global AssetCatalogue IDs such as
    ``paint``. A portable Activity may instead declare, for example,
    ``icon = "package:assets/icon.png"``. The package tree has already rejected
    symlinks; this resolver additionally enforces a relative bounded image path.
    """

    value = manifest.icon_id.strip()
    if not value.startswith(PACKAGE_ICON_PREFIX):
        return None
    relative_text = value.removeprefix(PACKAGE_ICON_PREFIX).strip()
    if not relative_text:
        raise ActivityIconError("package Activity icon path is empty")
    relative = Path(relative_text)
    if relative.is_absolute() or ".." in relative.parts or "." in relative.parts:
        raise ActivityIconError("package Activity icon must be a safe relative path")
    if len(relative.parts) > 6 or len(relative_text) > 180:
        raise ActivityIconError("package Activity icon path is too deep or long")
    if relative.suffix.casefold() not in _ALLOWED_SUFFIXES:
        raise ActivityIconError("package Activity icon must be PNG or WebP")
    try:
        resolved = (manifest.root / relative).resolve(strict=True)
        resolved.relative_to(manifest.root.resolve(strict=True))
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise ActivityIconError("package Activity icon does not resolve inside the package") from exc
    if not resolved.is_file():
        raise ActivityIconError("package Activity icon is not a file")
    return resolved
