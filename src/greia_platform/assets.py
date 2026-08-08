from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


class AssetCatalogueError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class IconAsset:
    asset_id: str
    category: str
    alt_key: str
    path_64: Path
    path_128: Path
    path_256: Path


class AssetCatalogue:
    def __init__(self, root: Path, icons: Mapping[str, IconAsset]):
        self.root = root.resolve()
        self._icons = dict(icons)

    @classmethod
    def load(cls, manifest_path: Path) -> "AssetCatalogue":
        manifest_path = manifest_path.resolve(strict=True)
        with manifest_path.open("rb") as handle:
            raw = tomllib.load(handle)
        entries = raw.get("icons")
        if not isinstance(entries, list):
            raise AssetCatalogueError("icons must be an array of tables")
        root = manifest_path.parent.parent
        icons: dict[str, IconAsset] = {}
        for entry in entries:
            if not isinstance(entry, dict):
                raise AssetCatalogueError("invalid icon entry")
            asset_id = _text(entry, "id")
            if asset_id in icons:
                raise AssetCatalogueError(f"duplicate icon id: {asset_id}")
            icon = IconAsset(
                asset_id=asset_id,
                category=_text(entry, "category"),
                alt_key=_text(entry, "alt_key"),
                path_64=_safe_path(root, _text(entry, "path_64")),
                path_128=_safe_path(root, _text(entry, "path_128")),
                path_256=_safe_path(root, _text(entry, "path_256")),
            )
            icons[asset_id] = icon
        return cls(root, icons)

    def get(self, asset_id: str) -> IconAsset:
        try:
            return self._icons[asset_id]
        except KeyError as exc:
            raise AssetCatalogueError(f"unknown icon: {asset_id}") from exc

    def all_icons(self) -> tuple[IconAsset, ...]:
        return tuple(self._icons[key] for key in sorted(self._icons))


def _text(entry: Mapping[str, object], key: str) -> str:
    value = entry.get(key)
    if not isinstance(value, str) or not value:
        raise AssetCatalogueError(f"{key} must be a non-empty string")
    return value


def _safe_path(root: Path, relative: str) -> Path:
    candidate = (root / relative).resolve(strict=True)
    if root not in candidate.parents:
        raise AssetCatalogueError(f"asset path escapes library: {relative}")
    return candidate
