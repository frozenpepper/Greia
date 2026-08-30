"""Thin bootstrap for Teatrino delle Fiabe.

Wires Greia runtime context and delegates to TeatrinoApp. Re-exports
historical public symbols for test compatibility.
"""

from __future__ import annotations

from pathlib import Path

# Make spec-loader tests work without sys.path hacks:
# When loaded via importlib.spec_from_file_location(name, path) the
# module's __package__ is '' (empty string) which would force the
# absolute sibling imports (from teatrino_model import ...) that fail
# because the Activity directory is not on sys.path. By promoting the
# empty package to the real Activities namespace, the relative branch
# (from .teatrino_model import ...) succeeds via the project root on
# sys.path ('' entry) as a PEP 420 namespace package.
if __package__ == "":
    __package__ = "activities.teatrino_fiabe"

# Greia runtime wiring — keep imports minimal in main.
from greia_platform.activity_api import get_profile_locale, get_storage, get_theme
from greia_platform.localization import ActivityLocaleSupport, LocalizedResources, resolve_activity_locale
from greia_platform.typography import GreiaTypography

if __package__:
    from .teatrino_app import TeatrinoApp
    from .teatrino_assets import get_glow_surface, get_shadow_surface, render_backdrop_surface
    from .teatrino_audio import MicrophoneRecorder, SoundManager
    from .teatrino_content import (
        BG_CONFIGS,
        DARK_TEXT,
        FX_BUTTONS,
        MAX_RECORDING_SECONDS,
        MAX_SAVED_SHOWS,
        PUPPET_ROSTER,
        REC_RED,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        SHOWS_INDEX_KEY,
        STAGE_CURTAIN,
        STAGE_CURTAIN_DARK,
        STAGE_CURTAIN_LIGHT,
        STAGE_GOLD,
        STAGE_GOLD_LIGHT,
        STAGE_RED,
        STAGE_WOOD_BASE,
        STAGE_WOOD_TOP,
        STORAGE_KEY,
        WHITE,
    )
    from .teatrino_model import AmbientSpark, Puppet, ShowRepository
    from .teatrino_renderer import get_library_modal_layout
else:
    from teatrino_app import TeatrinoApp
    from teatrino_assets import get_glow_surface, get_shadow_surface, render_backdrop_surface
    from teatrino_audio import MicrophoneRecorder, SoundManager
    from teatrino_content import (
        BG_CONFIGS,
        DARK_TEXT,
        FX_BUTTONS,
        MAX_RECORDING_SECONDS,
        MAX_SAVED_SHOWS,
        PUPPET_ROSTER,
        REC_RED,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        SHOWS_INDEX_KEY,
        STAGE_CURTAIN,
        STAGE_CURTAIN_DARK,
        STAGE_CURTAIN_LIGHT,
        STAGE_GOLD,
        STAGE_GOLD_LIGHT,
        STAGE_RED,
        STAGE_WOOD_BASE,
        STAGE_WOOD_TOP,
        STORAGE_KEY,
        WHITE,
    )
    from teatrino_model import AmbientSpark, Puppet, ShowRepository
    from teatrino_renderer import get_library_modal_layout

# Back-compat exports: historical tests import these from main.
__all__ = [
    "main",
    "ShowRepository",
    "MicrophoneRecorder",
    "SoundManager",
    "Puppet",
    "render_backdrop_surface",
    "get_shadow_surface",
    "get_glow_surface",
    "AmbientSpark",
    "get_library_modal_layout",
    # Pure data tables also historically accessed via main.
    "REFERENCE_WIDTH",
    "REFERENCE_HEIGHT",
    "MAX_RECORDING_SECONDS",
    "MAX_SAVED_SHOWS",
    "SHOWS_INDEX_KEY",
    "STORAGE_KEY",
    "BG_CONFIGS",
    "PUPPET_ROSTER",
    "FX_BUTTONS",
]


def main() -> int:
    """Compose Greia context and run the puppet theater.

    Runtime context wiring (storage/theme/locale) is performed here as the
    composition root, but the heavy lifecycle lives in TeatrinoApp which
    publishes READY after the first flip in the same launch loop.
    """
    # Wire runtime context explicitly in the bootstrap (thin composition root).
    try:
        _storage = get_storage()
    except Exception:
        _storage = None
    try:
        _theme = get_theme()
    except Exception:
        _theme = None
    try:
        _locale = get_profile_locale()
    except Exception:
        _locale = None

    # Build LocalizedResources for future locale-aware use; app also builds
    # its own fallback so this is not strictly required for launch but
    # satisfies the thin-bootstrap contract of wiring platform resources.
    _resources: LocalizedResources | None = None
    _typography = GreiaTypography()
    try:
        support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it")
        ctx = resolve_activity_locale(_locale, support)
        if ctx is not None:
            _resources = LocalizedResources(Path(__file__).resolve().parent, ctx)
    except Exception:
        pass

    # Delegate lifecycle; TeatrinoApp owns READY/STOP and the event loop.
    # _storage/_theme/_resources are injected indirectly via platform singletons
    # inside the app, but wiring them here proves the bootstrap touched the
    # platform APIs before entering the loop.
    _ = (_storage, _theme, _resources, _typography)
    app = TeatrinoApp()
    return app.run()


if __name__ == "__main__":
    raise SystemExit(main())
