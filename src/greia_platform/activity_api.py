from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .assets import AssetCatalogue, AssetCatalogueError
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
from .profile_presentation import (
    GrammaticalGender,
    ProfilePresentation,
    ProfilePresentationPreferences,
    ProfilePresentationStore,
)
from .profiles import ProfilePolicy, write_avatar_request
from .storage_client import ActivityStorageClient
from .system_language import SystemLanguageStore
from .theme_snapshot import ThemeSnapshotError, decode_theme_snapshot
from .ui_preferences import InterfaceSize, UiPreferences, UiPreferencesStore


@dataclass(frozen=True, slots=True)
class SharedVisualReference:
    """One read-only semantic Greia visual resolved for an Activity.

    Activities request product semantics (asset ID + explicit variant), never an
    arbitrary host path. ``path`` is the current Python-runtime realization of
    that semantic reference. Future Web/runtime adapters may expose the same ID
    and variant through a renderer-appropriate transport without changing the
    semantic request contract.
    """

    asset_id: str
    kind: str
    role: str
    variant: str
    path: Path


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
    """Return the Activity-visible semantic asset catalogue.

    Core icons remain mandatory. Generated shared visuals are optional so an
    Activity that only uses established platform APIs still starts on a build or
    installed image where the optional visual rendition catalogue is absent or
    malformed. Visual requests then fail narrowly as unknown shared visuals.
    """

    core = AssetCatalogue.load(_root() / "assets" / "catalog" / "core_icons_v1.toml")
    shared_path = _root() / "assets" / "catalog" / "shared_visuals_v1.toml"
    try:
        shared = AssetCatalogue.load(shared_path)
        return core.merged(shared)
    except (AssetCatalogueError, FileNotFoundError, OSError, RuntimeError, ValueError):
        return core


@lru_cache(maxsize=1)
def _theme_store() -> ThemeStore:
    state_dir = os.environ.get("GREIA_CUSTOMIZATION_DIR")
    if not state_dir:
        state_dir = str(Path.home() / ".greia-simulator" / "dev-customization")
        Path(state_dir).mkdir(parents=True, exist_ok=True)
    return ThemeStore.load(
        _root() / "runtime" / "theme-defaults.toml",
        Path(state_dir),
    )


@lru_cache(maxsize=1)
def _ui_preferences_store() -> UiPreferencesStore:
    state_dir = os.environ.get("GREIA_CUSTOMIZATION_DIR")
    if not state_dir:
        state_dir = str(Path.home() / ".greia-simulator" / "dev-customization")
        Path(state_dir).mkdir(parents=True, exist_ok=True)
    return UiPreferencesStore(Path(state_dir))


@lru_cache(maxsize=1)
def _profile_presentation_store() -> ProfilePresentationStore:
    state_dir = os.environ.get("GREIA_CUSTOMIZATION_DIR")
    if not state_dir:
        state_dir = str(Path.home() / ".greia-simulator" / "dev-customization")
        Path(state_dir).mkdir(parents=True, exist_ok=True)
    return ProfilePresentationStore(Path(state_dir))


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
def _system_language_store() -> SystemLanguageStore:
    return SystemLanguageStore.from_environment()


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


def get_audio_capture_device() -> str | None:
    """Return Greia's selected capture endpoint for this Activity launch.

    Activities with ``audio.basic`` must use this semantic platform route rather
    than enumerating physical microphones and selecting a card/device themselves.
    ``None`` means use the runtime's normal default capture endpoint, which is
    also the correct development/simulator fallback when no production route was
    injected.
    """

    _require_capability("audio.basic")
    value = os.environ.get("GREIA_AUDIO_CAPTURE_DEVICE", "").strip()
    return value or None


def get_audio_processing_mode() -> str:
    """Return the descriptive microphone processing mode for this launch."""

    _require_capability("audio.basic")
    value = os.environ.get("GREIA_AUDIO_PROCESSING_MODE", "off").strip().casefold()
    return value if value in {"off", "lightweight", "advanced"} else "off"


def emit_activity_event(
    event_id: str,
    payload_or_key: object = None,
    *,
    idempotency_key: str | None = None,
    score: float | int | None = None,
    payload: object = None,
) -> ActivityEventReceipt | None:
    """Report an Activity fact to Greia's platform-owned progression pipeline."""

    if payload is None and isinstance(payload_or_key, dict):
        payload = payload_or_key
    elif idempotency_key is None and isinstance(payload_or_key, str):
        idempotency_key = payload_or_key

    if idempotency_key is None:
        idempotency_key = f"{event_id}-{os.getpid()}-{id(payload)}"

    try:
        return get_events().emit(
            event_id,
            idempotency_key=idempotency_key,
            score=score,
            payload=payload,
        )
    except Exception:
        return None


def get_active_profile() -> dict[str, object]:
    profile_id = os.environ.get("GREIA_PROFILE_ID", "")
    if not profile_id:
        return {
            "profile_id": "default",
            "display_name": "Explorer",
            "avatar_id": "unicorn",
        }
    return {
        "profile_id": profile_id,
        "display_name": os.environ.get("GREIA_PROFILE_NAME", ""),
        "avatar_id": os.environ.get("GREIA_PROFILE_AVATAR", ""),
    }


def get_profile_locale() -> str:
    """Return the profile override or current Greia device UI locale.

    A launch-time profile/device environment value wins when the platform has
    supplied one. Otherwise the Activity reads the same small, read-only Greia
    device-language store used by the installer and Parent surfaces. Installed
    Activities can read this descriptive state but cannot mutate it through the
    Activity API.
    """

    profile_locale = os.environ.get("GREIA_PROFILE_LOCALE", "").strip()
    if profile_locale:
        return profile_locale
    device_locale = os.environ.get("GREIA_DEVICE_LOCALE", "").strip()
    if device_locale:
        return device_locale
    return _system_language_store().read().locale


def get_profile_presentation() -> ProfilePresentation:
    """Return the child's bounded presentation hint for this launch.

    The value is descriptive only.  Activities must not use it to hide content,
    change permissions, alter difficulty or otherwise partition the product.
    Trusted customization Activities may read the profile-local store directly;
    ordinary Activities receive only the Shell-injected semantic value.
    """

    if os.environ.get("GREIA_CUSTOMIZATION_DIR"):
        return _profile_presentation_store().read().presentation
    raw = os.environ.get(
        "GREIA_PROFILE_PRESENTATION",
        ProfilePresentation.NEUTRAL.value,
    ).strip().casefold()
    try:
        return ProfilePresentation(raw)
    except ValueError:
        return ProfilePresentation.NEUTRAL


def get_profile_grammatical_gender() -> GrammaticalGender:
    """Return the localization agreement selector for child-directed language.

    This is intentionally a tiny grammar hint rather than a general identity
    model.  Use it only when a localized utterance genuinely requires agreement,
    e.g. Italian ``bravo``/``brava``. Prefer a neutral complete phrase whenever
    that sounds natural.
    """

    if os.environ.get("GREIA_CUSTOMIZATION_DIR"):
        return _profile_presentation_store().read().grammatical_gender
    raw = os.environ.get("GREIA_PROFILE_GRAMMATICAL_GENDER", "").strip().casefold()
    try:
        return GrammaticalGender(raw)
    except ValueError:
        presentation = ProfilePresentationPreferences(
            presentation=get_profile_presentation()
        )
        return presentation.grammatical_gender


def get_profile_avatar_choices() -> tuple[str, ...]:
    _require_capability("profile.manage_own")
    return _profile_policy().avatars


def set_active_profile_avatar(avatar_id: str) -> dict[str, object]:
    _require_capability("profile.manage_own")
    profile_id = os.environ.get("GREIA_PROFILE_ID", "default")
    request_path = os.environ.get("GREIA_AVATAR_REQUEST_PATH", "")
    if request_path:
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


def get_shared_visual(
    asset_id: str,
    *,
    variant: str = "default",
) -> SharedVisualReference:
    """Resolve one explicit shared Greia visual for this Activity.

    The request is semantic and read-only. The caller cannot supply a path or
    mutate the catalogue. Unknown IDs/variants raise ``AssetCatalogueError``;
    Activities should keep a static/private fallback when a shared visual is
    optional to their experience.
    """

    visual = _catalogue().get_visual(asset_id)
    return SharedVisualReference(
        asset_id=visual.asset_id,
        kind=visual.kind,
        role=visual.role,
        variant=variant,
        path=visual.path_for(variant),
    )


def get_shared_visual_path(
    asset_id: str,
    *,
    variant: str = "default",
) -> Path:
    """Python-runtime convenience wrapper for ``get_shared_visual``."""

    return get_shared_visual(asset_id, variant=variant).path


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

    raw = os.environ.get("GREIA_ACTIVITY_CAPABILITIES")
    if raw is None:
        return
    capabilities = frozenset(item for item in raw.split(",") if item)
    if capability not in capabilities:
        raise PermissionError(f"activity lacks required capability: {capability}")


def mark_activity_ready() -> None:
    """Signal that the Activity has created its usable child-facing surface."""

    session_id, path = _lifecycle_path("GREIA_ACTIVITY_READY_PATH")
    if session_id and path:
        _write_lifecycle_marker(path, session_id)


def activity_stop_requested() -> bool:
    """Return whether Greia requested a graceful stop for this launch."""

    session_id, path = _lifecycle_path("GREIA_ACTIVITY_STOP_PATH")
    if not session_id or not path:
        return False
    try:
        return path.read_text(encoding="ascii").strip() == session_id
    except (OSError, UnicodeDecodeError):
        return False


def _lifecycle_path(environment_name: str) -> tuple[str, Path] | tuple[None, None]:
    session_id = os.environ.get("GREIA_ACTIVITY_SESSION_ID", "").strip()
    raw_path = os.environ.get(environment_name, "").strip()
    raw_data = os.environ.get("GREIA_ACTIVITY_DATA_DIR", "").strip()
    if not session_id or not raw_path or not raw_data:
        return None, None
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
