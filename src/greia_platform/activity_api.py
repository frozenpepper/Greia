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
from .input_core import InteractionProfile, parse_interaction_profile
from .profiles import ProfilePolicy, write_avatar_request
from .storage_client import ActivityStorageClient
from .theme_snapshot import ThemeSnapshotError, decode_theme_snapshot
from .ui_preferences import InterfaceSize, UiPreferences, UiPreferencesStore


@lru_cache(maxsize=1)
def _root() -> Path:
    explicit = os.environ.get("GREIA_OS_ROOT")
    if explicit:
        return Path(explicit).resolve()
    opt = Path("/opt/greia-os")
    if opt.exists():
        return opt.resolve()
    repo = Path(__file__).resolve().parents[2]
    if (repo / "runtime" / "theme-defaults.toml").exists():
        return repo.resolve()
    return opt


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
def _ui_preferences_store() -> UiPreferencesStore:
    state_dir = os.environ.get("GREIA_CUSTOMIZATION_DIR")
    if not state_dir:
        raise RuntimeError("activity was not launched with profile-scoped customization")
    return UiPreferencesStore(Path(state_dir))


@lru_cache(maxsize=1)
def _default_theme_store() -> ThemeStore:
    """Return the read-only canonical theme view available as safe fallback."""

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
    """Return this launch's runtime-neutral Greia durable storage client."""

    return ActivityStorageClient.from_environment()


@lru_cache(maxsize=1)
def get_events() -> ActivityEventClient:
    """Return this launch's runtime-neutral validated Activity event client."""

    return ActivityEventClient.from_environment()


def get_input_profile() -> InteractionProfile:
    """Return the platform-validated default interaction profile for this launch."""

    raw = os.environ.get(
        "GREIA_ACTIVITY_INPUT_PROFILE",
        InteractionProfile.HYBRID.value,
    )
    return parse_interaction_profile(raw)


def emit_activity_event(
    event_id: str,
    *,
    idempotency_key: str,
    score: float | int | None = None,
    payload: object = None,
) -> ActivityEventReceipt:
    """Report an Activity fact to Greia's platform-owned progression pipeline."""

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


def get_profile_locale() -> str:
    """Return the active profile or device UI locale tag string (e.g. 'it' or 'en')."""
    return os.environ.get("GREIA_PROFILE_LOCALE", os.environ.get("GREIA_DEVICE_LOCALE", "it"))


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
    """Return this launch's read-only resolved visual theme.

    Trusted My Greia/customization code receives the real profile store because
    it owns `customization.manage`. Ordinary Activities instead receive a
    launch-time resolved snapshot. The snapshot carries colors only: it exposes
    neither the customization directory nor the managed wallpaper file.
    """

    if os.environ.get("GREIA_CUSTOMIZATION_DIR"):
        try:
            return _theme_store().resolve()
        except Exception:
            pass
    snapshot = os.environ.get("GREIA_THEME_SNAPSHOT")
    if snapshot:
        try:
            return decode_theme_snapshot(snapshot)
        except ThemeSnapshotError:
            pass
    try:
        return _default_theme_store().resolve()
    except Exception:
        from .customization import ThemePreferences
        return ResolvedTheme(
            preferences=ThemePreferences(1, "buttercup", "sky", "ink", False),
            background=(255, 250, 240),
            panel=(247, 235, 203),
            accent=(255, 194, 52),
            text=(61, 44, 31),
            accent_text=(255, 255, 255),
            wallpaper_path=None,
        )


def get_ui_preferences() -> UiPreferences:
    """Return bounded profile presentation preferences for this launch.

    This is descriptive presentation context, not write authority. Ordinary
    Activities receive a semantic value injected by Greia; only a trusted
    customization Activity may persist a new value.
    """

    if os.environ.get("GREIA_CUSTOMIZATION_DIR"):
        return _ui_preferences_store().read()
    raw = os.environ.get("GREIA_INTERFACE_SIZE", InterfaceSize.NORMAL.value)
    try:
        size = InterfaceSize(raw)
    except ValueError:
        size = InterfaceSize.NORMAL
    return UiPreferences(interface_size=size)


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


def set_interface_size(value: str | InterfaceSize) -> UiPreferences:
    _require_capability("customization.manage")
    return _ui_preferences_store().set_interface_size(value)


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
    """Signal that the Activity has created its usable child-facing surface."""

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
