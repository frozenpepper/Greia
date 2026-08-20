"""Launcher bridge for optional generated shared-visual runtime assets.

Core icons remain mandatory. Generated shared visuals are an optional visual
upgrade: if their explicit catalogue is absent or invalid the launcher keeps its
existing static/icon path instead of scanning source art or failing the child UI.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from greia_platform.assets import AssetCatalogue, AssetCatalogueError


@dataclass(frozen=True, slots=True)
class LauncherAssetSet:
    catalogue: AssetCatalogue
    shared_visuals_available: bool
    shared_visuals_error: str | None = None


def load_launcher_assets(
    core_catalogue: Path,
    shared_visual_catalogue: Path | None = None,
) -> LauncherAssetSet:
    """Load mandatory core icons and optionally merge generated shared visuals.

    The shared catalogue is never discovered by walking asset directories; its
    exact path is supplied by the launcher. Missing/invalid optional visual output
    leaves the core catalogue intact so primitive/static fallback remains usable.
    """

    core = AssetCatalogue.load(core_catalogue)
    if shared_visual_catalogue is None or not shared_visual_catalogue.is_file():
        return LauncherAssetSet(core, shared_visuals_available=False)

    try:
        shared = AssetCatalogue.load(shared_visual_catalogue)
        merged = core.merged(shared)
    except (AssetCatalogueError, OSError) as exc:
        return LauncherAssetSet(
            core,
            shared_visuals_available=False,
            shared_visuals_error=str(exc),
        )
    return LauncherAssetSet(merged, shared_visuals_available=True)
