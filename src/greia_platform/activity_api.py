from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from .assets import AssetCatalogue
from .customization import (
    RemovableImageScanner,
    ResolvedTheme,
    ThemePalette,
    ThemePreferences,
    ThemeStore,
    WallpaperCandidate,
    WallpaperImporter,
)
from .event_client import ActivityEventClient, ActivityEventReceipt
from .profiles import ProfilePolicy, write_avatar_request
from .storage_client import ActivityStorageClient


@lru_cache(maxsize=1)
def _root() -> Path:
    return Path(os.environ.get("GREIA_OS_ROOT", "/opt/greia-os")).resolve()


@lru_cache(maxsize=1)
def _catalogue() -> AssetCatalogue:
    return AssetCatalogue.load(_root() / "assets" / "catalog" / "core_icons_v1.toml")


@lru_cache(maxsize=1)
def _theme_store() -> ThemeStore:
    state_dir = os.environ.get("GREIA_CUSTOMIZATION_DIR")
    if not state_dir:
        raise RuntimeError("activity was not launched with profile-scoped customization")
    return ThemeStore.load(
        _root() / "runtime" / "theme-defaults.toml",
        Path(state_dir),
    )


@lru_cache(maxsize=1)
def _default_theme_store() -> ThemeStore:
    """Return the read-only canonical theme view available to every Activity.

    Ordinary Activities must be able to render with Greia's canonical palette
    without receiving `customization.manage` or a raw path to the child's
    customization directory. The deliberately nonexistent state directory
    makes ThemeStore resolve only trusted platform defaults. A future
    read-only profile-theme snapshot may extend this without widening file
    authority.
    """

    return ThemeStore.load(
        _root() / "runtime" / "theme-defaults.toml",
        _root() / "runtime" / ".activity-theme-default",
    )


@lru_cache(maxsize=1)
def _media_scanner() -> RemovableImageScanner:
    return RemovableImageScanner(Path(os.environ.get("GREIA_MEDIA_ROOT", "/media/greia")))


@lru_cache(maxsize=1)
def _profile_policy() -> ProfilePolicy:
    return ProfilePolicy.load(_root() / "runtime" / "profile-defaults.toml")


@lru_cache(maxsize=1)
def get_storage() -> ActivityStorageClient:
    """Return this launch's runtime-neutral Greia durable storage client.

    The client talks to a per-session platform broker. It never receives the
    physical profile storage path, so quota, migration and backup semantics stay
    under Greia authority rather than becoming raw Activity filesystem policy.
    """

    return ActivityStorageClient.from_environment()


@lru_cache(maxsize=1)
def get_events() -> ActivityEventClient:
    """Return this launch's runtime-neutral validated Activity event client."""

    return ActivityEventClient.from_environment()


def emit_activity_event(
    event_id: str,
    *,
    idempotency_key: str,
    score: float | int | None = None,
    payload: object = None,
) -> ActivityEventReceipt:
    """Report an Activity fact to Greia's platform-owned progression pipeline.

    The Activity chooses only a declared event ID, an idempotency key, optional
    score, and portable payload. Profile/session/Activity identity and reward
    economics remain bound by trusted Greia services outside the Activity.
    """

    return get_events().emit(
        event_id,
        idempotency_key=idempotency_key,
        score=score,
        payload=payload,
    )


def get_active_profile() -> dict[str, object]:
    profile_id = os.environ.get("GREIA_PROFILE_ID", "")
    if not profile_id:
        raise RuntimeError("activity was not launched inside a child profile")
    return {
        "profile_id": profile_id,
        "display_name": os.environ.get("GREIA_PROFILE_NAME", ""),
        "avatar_id": os.environ.get("GREIA_PROFILE_AVATAR", ""),
    }


def get_profile_avatar_choices() -> tuple[str, ...]:
    _require_capability("profile.manage_own")
    return _profile_policy().avatars


def set_active_profile_avatar(avatar_id: str) -> dict[str, object]:
    _require_capability("profile.manage_own")
    profile_id = os.environ.get("GREIA_PROFILE_ID", "")
    request_path = os.environ.get("GREIA_AVATAR_REQUEST_PATH", "")
    if not profile_id or not request_path:
        raise RuntimeError("activity was not launched with an own-profile request channel")
    write_avatar_request(
        _profile_policy(), Path(request_path), profile_id, avatar_id
    )
    updated = get_active_profile()
    updated["avatar_id"] = avatar_id
    return updated


def get_icon_path(asset_id: str, size: int = 128) -> Path:
    """Resolve a shared semantic icon without exposing arbitrary asset paths."""

    icon = _catalogue().get(asset_id)
    if size <= 64:
        return icon.path_64
    if size <= 128:
        return icon.path_128
    return icon.path_256


def get_theme() -> ResolvedTheme:
    """Return the Activity-visible Greia theme without expanding authority.

    A trusted customization Activity that was granted the profile-scoped
    customization path receives the actual resolved child theme. Ordinary
    Activities receive the canonical default resolved palette and never gain
    raw read/write access to the child's customization files merely to obtain
    colors.
    """

    if os.environ.get("GREIA_CUSTOMIZATION_DIR"):
        return _theme_store().resolve()
    return _default_theme_store().resolve()


def get_theme_palette() -> ThemePalette:
    _require_capability("customization.manage")
    return _theme_store().palette


def set_theme_color(kind: str, swatch_id: str) -> ThemePreferences:
    _require_capability("customization.manage")
    store = _theme_store()
    if kind == "background":
        return store.set_colors(background=swatch_id)
    if kind == "accent":
        return store.set_colors(accent=swatch_id)
    if kind == "text":
        return store.set_colors(text=swatch_id)
    raise ValueError(f"unknown theme color kind: {kind}")


def list_wallpaper_candidates() -> tuple[WallpaperCandidate, ...]:
    _require_capability("removable_media.read")
    return _media_scanner().scan()


def import_wallpaper(candidate: WallpaperCandidate) -> Path:
    _require_capability("customization.manage")
    _require_capability("removable_media.read")
    return WallpaperImporter(_theme_store(), _media_scanner()).import_image(candidate.path)


def disable_wallpaper() -> ThemePreferences:
    _require_capability("customization.manage")
    return _theme_store().clear_wallpaper()


def _require_capability(capability: str) -> None:
    """Fail early when the launch context did not declare a capability.

    This is an SDK usability check, not the security boundary. An Activity can
    mutate its own environment after launch. Installed-system authority is
    enforced by the supervisor's mount/device/network/broker policy, which is
    derived from the validated manifest outside the Activity process.
    """
    raw = os.environ.get("GREIA_ACTIVITY_CAPABILITIES", "")
    capabilities = frozenset(item for item in raw.split(",") if item)
    if capability not in capabilities:
        raise PermissionError(f"activity lacks required capability: {capability}")


def mark_activity_ready() -> None:
    """Signal that the Activity has created its usable child-facing surface.

    This lifecycle marker is cooperative state, not an authorization token.
    The supervisor creates a unique per-launch channel inside the Activity's own
    writable namespace and verifies the session ID before accepting the marker.
    """

    session_id, path = _lifecycle_path("GREIA_ACTIVITY_READY_PATH")
    _write_lifecycle_marker(path, session_id)


def activity_stop_requested() -> bool:
    """Return whether Greia requested a graceful stop for this launch."""

    session_id, path = _lifecycle_path("GREIA_ACTIVITY_STOP_PATH")
    try:
        return path.read_text(encoding="ascii").strip() == session_id
    except (OSError, UnicodeDecodeError):
        return False


def _lifecycle_path(environment_name: str) -> tuple[str, Path]:
    session_id = os.environ.get("GREIA_ACTIVITY_SESSION_ID", "").strip()
    raw_path = os.environ.get(environment_name, "").strip()
    raw_data = os.environ.get("GREIA_ACTIVITY_DATA_DIR", "").strip()
    if not session_id or not raw_path or not raw_data:
        raise RuntimeError("activity was not launched with a lifecycle control channel")
    data_root = Path(raw_data).resolve(strict=False)
    path = Path(raw_path).resolve(strict=False)
    if path == data_root or data_root not in path.parents:
        raise RuntimeError("activity lifecycle path escapes the private data namespace")
    return session_id, path


def _write_lifecycle_marker(path: Path, session_id: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(session_id + "\n", encoding="ascii")
    temporary.replace(path)
