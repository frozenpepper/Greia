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


@dataclass(frozen=True, slots=True)
class VisualAsset:
    """One explicitly catalogued shared visual with named source variants.

    Lookup is deliberately separate from image decoding/caching. A later renderer
    may choose an appropriate pre-rendered variant without the catalogue scanning
    directories or performing per-frame filesystem work.
    """

    asset_id: str
    kind: str
    role: str
    variants: tuple[tuple[str, Path], ...]

    def path_for(self, variant: str = "default") -> Path:
        for name, path in self.variants:
            if name == variant:
                return path
        raise AssetCatalogueError(
            f"visual asset {self.asset_id!r} has no variant {variant!r}"
        )

    def variant_names(self) -> tuple[str, ...]:
        return tuple(name for name, _path in self.variants)


_VISUAL_KINDS = frozenset(
    {
        "ui",
        "environment",
        "character",
        "prop",
        "fx",
        "shadow",
        "atmosphere",
        "light",
    }
)


class AssetCatalogue:
    def __init__(
        self,
        root: Path,
        icons: Mapping[str, IconAsset],
        visuals: Mapping[str, VisualAsset] | None = None,
    ):
        self.root = root.resolve()
        self._icons = dict(icons)
        self._visuals = dict(visuals or {})
        overlap = self._icons.keys() & self._visuals.keys()
        if overlap:
            duplicate = sorted(overlap)[0]
            raise AssetCatalogueError(f"duplicate asset id: {duplicate}")

    @classmethod
    def load(cls, manifest_path: Path) -> "AssetCatalogue":
        manifest_path = manifest_path.resolve(strict=True)
        try:
            with manifest_path.open("rb") as handle:
                raw = tomllib.load(handle)
        except (tomllib.TOMLDecodeError, OSError) as exc:
            raise AssetCatalogueError(
                f"failed to load asset catalogue {manifest_path}: {exc}"
            ) from exc

        icon_entries = raw.get("icons")
        visual_entries = raw.get("visuals")
        if icon_entries is None and visual_entries is None:
            raise AssetCatalogueError("catalogue must define icons or visuals")
        if icon_entries is None:
            icon_entries = []
        if visual_entries is None:
            visual_entries = []
        if not isinstance(icon_entries, list):
            raise AssetCatalogueError("icons must be an array of tables")
        if not isinstance(visual_entries, list):
            raise AssetCatalogueError("visuals must be an array of tables")

        root = manifest_path.parent.parent
        icons: dict[str, IconAsset] = {}
        visuals: dict[str, VisualAsset] = {}
        seen_ids: set[str] = set()

        for entry in icon_entries:
            if not isinstance(entry, dict):
                raise AssetCatalogueError("invalid icon entry")
            asset_id = _text(entry, "id")
            _claim_id(asset_id, seen_ids)
            icon = IconAsset(
                asset_id=asset_id,
                category=_text(entry, "category"),
                alt_key=_text(entry, "alt_key"),
                path_64=_safe_path(root, _text(entry, "path_64")),
                path_128=_safe_path(root, _text(entry, "path_128")),
                path_256=_safe_path(root, _text(entry, "path_256")),
            )
            icons[asset_id] = icon

        for entry in visual_entries:
            if not isinstance(entry, dict):
                raise AssetCatalogueError("invalid visual entry")
            asset_id = _text(entry, "id")
            _claim_id(asset_id, seen_ids)
            kind = _text(entry, "kind")
            if kind not in _VISUAL_KINDS:
                raise AssetCatalogueError(f"unsupported visual kind: {kind}")
            visuals[asset_id] = VisualAsset(
                asset_id=asset_id,
                kind=kind,
                role=_text(entry, "role"),
                variants=_visual_variants(root, entry),
            )

        return cls(root, icons, visuals)

    def merged(self, *catalogues: "AssetCatalogue") -> "AssetCatalogue":
        """Return one explicit catalogue namespace across compatible manifests.

        Generated visual renditions intentionally live in a separate manifest from
        the established core-icon catalogue. Consumers merge those catalogues
        explicitly rather than scanning directories. Every merged catalogue must
        resolve under the same assets root and IDs remain globally unique.
        """

        icons = dict(self._icons)
        visuals = dict(self._visuals)
        seen_ids = set(icons) | set(visuals)
        for catalogue in catalogues:
            if catalogue.root != self.root:
                raise AssetCatalogueError(
                    "cannot merge asset catalogues with different roots: "
                    f"{self.root} != {catalogue.root}"
                )
            for asset_id, icon in catalogue._icons.items():
                _claim_id(asset_id, seen_ids)
                icons[asset_id] = icon
            for asset_id, visual in catalogue._visuals.items():
                _claim_id(asset_id, seen_ids)
                visuals[asset_id] = visual
        return AssetCatalogue(self.root, icons, visuals)

    def get(self, asset_id: str) -> IconAsset:
        try:
            return self._icons[asset_id]
        except KeyError as exc:
            raise AssetCatalogueError(f"unknown icon: {asset_id}") from exc

    def all_icons(self) -> tuple[IconAsset, ...]:
        return tuple(self._icons[key] for key in sorted(self._icons))

    def get_visual(self, asset_id: str) -> VisualAsset:
        try:
            return self._visuals[asset_id]
        except KeyError as exc:
            raise AssetCatalogueError(f"unknown visual asset: {asset_id}") from exc

    def all_visuals(self) -> tuple[VisualAsset, ...]:
        return tuple(self._visuals[key] for key in sorted(self._visuals))


def _claim_id(asset_id: str, seen_ids: set[str]) -> None:
    if asset_id in seen_ids:
        raise AssetCatalogueError(f"duplicate asset id: {asset_id}")
    seen_ids.add(asset_id)


def _visual_variants(
    root: Path, entry: Mapping[str, object]
) -> tuple[tuple[str, Path], ...]:
    raw = entry.get("variants")
    if not isinstance(raw, dict) or not raw:
        raise AssetCatalogueError("visual variants must be a non-empty table")
    variants: list[tuple[str, Path]] = []
    for name, relative in raw.items():
        if not isinstance(name, str) or not _valid_variant_name(name):
            raise AssetCatalogueError(f"invalid visual variant name: {name!r}")
        if not isinstance(relative, str) or not relative:
            raise AssetCatalogueError(
                f"visual variant {name!r} must be a non-empty path"
            )
        variants.append((name, _safe_path(root, relative)))
    if "default" not in raw:
        raise AssetCatalogueError("visual variants must define default")
    variants.sort(key=lambda item: item[0])
    return tuple(variants)


def _valid_variant_name(value: str) -> bool:
    return bool(value) and all(
        character.isalnum() or character in {"_", "-", "."} for character in value
    )


def _text(entry: Mapping[str, object], key: str) -> str:
    value = entry.get(key)
    if not isinstance(value, str) or not value:
        raise AssetCatalogueError(f"{key} must be a non-empty string")
    return value


def _safe_path(root: Path, relative: str) -> Path:
    try:
        candidate = (root / relative).resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise AssetCatalogueError(f"asset path does not resolve: {relative}") from exc
    if root not in candidate.parents:
        raise AssetCatalogueError(f"asset path escapes library: {relative}")
    return candidate
