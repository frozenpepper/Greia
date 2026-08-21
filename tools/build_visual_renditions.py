#!/usr/bin/env python3
"""Build explicit runtime PNG renditions from reviewed shared SVG masters.

This is a build-time tool. Runtime code consumes only the generated PNG paths
and generated explicit catalogue; it does not scan visual source directories or
require an SVG renderer on the target device.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import struct
import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


class VisualRenditionError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class VariantSpec:
    name: str
    source: Path
    output: Path
    output_relative: str
    width: int
    height: int


@dataclass(frozen=True, slots=True)
class VisualSpec:
    asset_id: str
    kind: str
    role: str
    variants: tuple[VariantSpec, ...]


_ALLOWED_KINDS = frozenset(
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
_MAX_RENDITION_DIMENSION = 2048
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--assets-root",
        type=Path,
        default=Path("assets"),
        help="Greia assets root containing visual source and generated output",
    )
    parser.add_argument(
        "--source-spec",
        type=Path,
        default=Path("assets/catalog/shared_visuals_v1_source.toml"),
    )
    parser.add_argument(
        "--output-catalog",
        type=Path,
        default=Path("assets/catalog/shared_visuals_v1.toml"),
    )
    parser.add_argument(
        "--rasterizer",
        default=os.environ.get("GREIA_RSVG_CONVERT", "rsvg-convert"),
        help="build-host SVG rasterizer; defaults to rsvg-convert",
    )
    args = parser.parse_args(argv)

    assets_root = args.assets_root.resolve(strict=True)
    source_spec = args.source_spec.resolve(strict=True)
    output_catalog = args.output_catalog.resolve()
    _require_within(assets_root, source_spec, "source spec")
    _require_within(assets_root, output_catalog, "output catalogue")

    rasterizer = _resolve_rasterizer(args.rasterizer)
    metadata, visuals = load_source_spec(source_spec, assets_root)
    render_all(visuals, rasterizer)
    write_runtime_catalog(output_catalog, source_spec, metadata, visuals)
    return 0


def load_source_spec(
    source_spec: Path, assets_root: Path
) -> tuple[Mapping[str, object], tuple[VisualSpec, ...]]:
    with source_spec.open("rb") as handle:
        raw = tomllib.load(handle)
    raw_visuals = raw.get("visuals")
    if not isinstance(raw_visuals, list) or not raw_visuals:
        raise VisualRenditionError("source spec must define at least one visual")

    ids: set[str] = set()
    outputs: set[Path] = set()
    visuals: list[VisualSpec] = []
    for raw_visual in raw_visuals:
        if not isinstance(raw_visual, dict):
            raise VisualRenditionError("invalid visual entry")
        asset_id = _text(raw_visual, "id")
        if asset_id in ids:
            raise VisualRenditionError(f"duplicate visual id: {asset_id}")
        ids.add(asset_id)
        kind = _text(raw_visual, "kind")
        if kind not in _ALLOWED_KINDS:
            raise VisualRenditionError(f"unsupported visual kind: {kind}")
        role = _text(raw_visual, "role")
        raw_variants = raw_visual.get("variants")
        if not isinstance(raw_variants, list) or not raw_variants:
            raise VisualRenditionError(f"visual {asset_id!r} has no variants")

        variants: list[VariantSpec] = []
        names: set[str] = set()
        for raw_variant in raw_variants:
            if not isinstance(raw_variant, dict):
                raise VisualRenditionError(f"visual {asset_id!r} has invalid variant")
            name = _text(raw_variant, "name")
            if not _valid_variant_name(name):
                raise VisualRenditionError(f"invalid visual variant name: {name!r}")
            if name in names:
                raise VisualRenditionError(
                    f"visual {asset_id!r} has duplicate variant {name!r}"
                )
            names.add(name)
            source_relative = _text(raw_variant, "source")
            output_relative = _text(raw_variant, "output")
            source = _contained_existing_file(assets_root, source_relative, "source")
            if source.suffix.lower() != ".svg":
                raise VisualRenditionError(
                    f"visual source must be SVG: {source_relative}"
                )
            output = _contained_output(assets_root, output_relative)
            if output.suffix.lower() != ".png":
                raise VisualRenditionError(
                    f"visual runtime rendition must be PNG: {output_relative}"
                )
            if output in outputs:
                raise VisualRenditionError(
                    f"duplicate visual output path: {output_relative}"
                )
            outputs.add(output)
            width = _dimension(raw_variant, "width")
            height = _dimension(raw_variant, "height")
            variants.append(
                VariantSpec(
                    name=name,
                    source=source,
                    output=output,
                    output_relative=output_relative,
                    width=width,
                    height=height,
                )
            )
        if "default" not in names:
            raise VisualRenditionError(
                f"visual {asset_id!r} must define a default variant"
            )
        variants.sort(key=lambda item: item.name)
        visuals.append(
            VisualSpec(
                asset_id=asset_id,
                kind=kind,
                role=role,
                variants=tuple(variants),
            )
        )

    visuals.sort(key=lambda item: item.asset_id)
    return raw, tuple(visuals)


def render_all(visuals: tuple[VisualSpec, ...], rasterizer: Path) -> None:
    for visual in visuals:
        for variant in visual.variants:
            variant.output.parent.mkdir(parents=True, exist_ok=True)
            temporary = _temporary_sibling(variant.output)
            temporary.unlink(missing_ok=True)
            command = [
                str(rasterizer),
                "--width",
                str(variant.width),
                "--height",
                str(variant.height),
                "--output",
                str(temporary),
                str(variant.source),
            ]
            try:
                subprocess.run(command, check=True)
                _verify_png(temporary, variant.width, variant.height)
                os.replace(temporary, variant.output)
            except subprocess.CalledProcessError as exc:
                raise VisualRenditionError(
                    f"rasterizer failed for {visual.asset_id!r}/{variant.name!r}"
                ) from exc
            finally:
                temporary.unlink(missing_ok=True)


def write_runtime_catalog(
    output_catalog: Path,
    source_spec: Path,
    metadata: Mapping[str, object],
    visuals: tuple[VisualSpec, ...],
) -> None:
    output_catalog.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(source_spec.read_bytes()).hexdigest()
    catalog_id = metadata.get("catalog_id")
    catalog_version = metadata.get("catalog_version")
    if not isinstance(catalog_id, str) or not catalog_id:
        raise VisualRenditionError("catalog_id must be a non-empty string")
    if not isinstance(catalog_version, str) or not catalog_version:
        raise VisualRenditionError("catalog_version must be a non-empty string")

    lines = [
        f'catalog_id = "{_toml_text(catalog_id)}"',
        f'catalog_version = "{_toml_text(catalog_version)}"',
        f'source_sha256 = "{digest}"',
        'generated_note = "Build-time PNG renditions from explicit reviewed SVG masters; runtime must not discover or rasterize SVG source."',
        "",
    ]
    for visual in visuals:
        lines.extend(
            [
                "[[visuals]]",
                f'id = "{_toml_text(visual.asset_id)}"',
                f'kind = "{_toml_text(visual.kind)}"',
                f'role = "{_toml_text(visual.role)}"',
                "",
                "[visuals.variants]",
            ]
        )
        for variant in visual.variants:
            lines.append(
                f'{variant.name} = "{_toml_text(variant.output_relative)}"'
            )
        lines.append("")
    _atomic_write_text(output_catalog, "\n".join(lines))


def _resolve_rasterizer(value: str) -> Path:
    path = Path(value)
    if path.parent != Path("."):
        resolved = path.expanduser().resolve(strict=True)
    else:
        found = shutil.which(value)
        if found is None:
            raise VisualRenditionError(
                "rsvg-convert is required on the build host to generate shared visual PNG renditions; "
                "install librsvg (Debian/Ubuntu: librsvg2-bin, macOS: brew install librsvg) "
                "or pass --rasterizer"
            )
        resolved = Path(found).resolve(strict=True)
    if not resolved.is_file():
        raise VisualRenditionError(f"rasterizer is not a file: {resolved}")
    return resolved


def _contained_existing_file(root: Path, relative: str, label: str) -> Path:
    candidate = (root / relative).resolve(strict=True)
    _require_within(root, candidate, label)
    if not candidate.is_file():
        raise VisualRenditionError(f"{label} is not a file: {relative}")
    return candidate


def _contained_output(root: Path, relative: str) -> Path:
    candidate = (root / relative).resolve()
    _require_within(root, candidate, "output")
    return candidate


def _require_within(root: Path, candidate: Path, label: str) -> None:
    root_resolved = root.resolve()
    candidate_resolved = candidate.resolve()
    if candidate_resolved == root_resolved or root_resolved not in candidate_resolved.parents:
        raise VisualRenditionError(f"{label} escapes assets root: {candidate}")


def _verify_png(path: Path, width: int, height: int) -> None:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise VisualRenditionError(f"rasterizer did not create output: {path}") from exc
    if len(data) < 24 or data[:8] != _PNG_SIGNATURE or data[12:16] != b"IHDR":
        raise VisualRenditionError(f"rasterizer output is not a PNG: {path}")
    actual_width, actual_height = struct.unpack(">II", data[16:24])
    if (actual_width, actual_height) != (width, height):
        raise VisualRenditionError(
            f"rasterizer output has unexpected dimensions for {path}: "
            f"{actual_width}x{actual_height} != {width}x{height}"
        )


def _temporary_sibling(path: Path) -> Path:
    return path.with_name(f".{path.name}.tmp-{os.getpid()}")


def _atomic_write_text(path: Path, content: str) -> None:
    temporary = _temporary_sibling(path)
    temporary.unlink(missing_ok=True)
    try:
        temporary.write_text(content, encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _text(entry: Mapping[str, object], key: str) -> str:
    value = entry.get(key)
    if not isinstance(value, str) or not value:
        raise VisualRenditionError(f"{key} must be a non-empty string")
    return value


def _dimension(entry: Mapping[str, object], key: str) -> int:
    value = entry.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise VisualRenditionError(f"{key} must be an integer")
    if value < 1 or value > _MAX_RENDITION_DIMENSION:
        raise VisualRenditionError(
            f"{key} must be between 1 and {_MAX_RENDITION_DIMENSION}"
        )
    return value


def _valid_variant_name(value: str) -> bool:
    return bool(value) and all(
        character.isalnum() or character in {"_", "-", "."} for character in value
    )


def _toml_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


if __name__ == "__main__":
    raise SystemExit(main())
