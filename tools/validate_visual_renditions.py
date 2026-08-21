#!/usr/bin/env python3
"""Validate generated shared visual PNG renditions without rasterizing anything.

This check is suitable for image builds and local acceptance: it verifies that
an explicit generated runtime catalogue matches the current source spec digest,
that every declared source/output mapping is preserved, and that every PNG has
the exact expected dimensions.
"""

from __future__ import annotations

import argparse
import hashlib
import struct
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


class VisualRenditionValidationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ExpectedVariant:
    asset_id: str
    kind: str
    role: str
    name: str
    output_relative: str
    width: int
    height: int


_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--assets-root", type=Path, default=Path("assets"))
    parser.add_argument(
        "--source-spec",
        type=Path,
        default=Path("assets/catalog/shared_visuals_v1_source.toml"),
    )
    parser.add_argument(
        "--runtime-catalog",
        type=Path,
        default=Path("assets/catalog/shared_visuals_v1.toml"),
    )
    args = parser.parse_args(argv)

    assets_root = args.assets_root.resolve(strict=True)
    source_spec = args.source_spec.resolve(strict=True)
    runtime_catalog = args.runtime_catalog.resolve(strict=True)
    _require_within(assets_root, source_spec, "source spec")
    _require_within(assets_root, runtime_catalog, "runtime catalogue")
    validate(assets_root, source_spec, runtime_catalog)
    return 0


def validate(assets_root: Path, source_spec: Path, runtime_catalog: Path) -> None:
    source_raw = _load_toml(source_spec, "source spec")
    runtime_raw = _load_toml(runtime_catalog, "runtime catalogue")

    expected_digest = hashlib.sha256(source_spec.read_bytes()).hexdigest()
    actual_digest = runtime_raw.get("source_sha256")
    if actual_digest != expected_digest:
        raise VisualRenditionValidationError(
            "runtime visual catalogue is stale: source_sha256 does not match "
            "shared_visuals_v1_source.toml"
        )

    expected_catalog_id = _text(source_raw, "catalog_id", "source spec")
    expected_version = _text(source_raw, "catalog_version", "source spec")
    if _text(runtime_raw, "catalog_id", "runtime catalogue") != expected_catalog_id:
        raise VisualRenditionValidationError("runtime catalogue id does not match source spec")
    if _text(runtime_raw, "catalog_version", "runtime catalogue") != expected_version:
        raise VisualRenditionValidationError(
            "runtime catalogue version does not match source spec"
        )

    expected = _expected_variants(source_raw)
    runtime = _runtime_variants(runtime_raw)
    if set(runtime) != set(expected):
        missing = sorted(set(expected) - set(runtime))
        extra = sorted(set(runtime) - set(expected))
        raise VisualRenditionValidationError(
            f"runtime visual IDs differ from source spec; missing={missing}, extra={extra}"
        )

    for asset_id in sorted(expected):
        expected_entry = expected[asset_id]
        runtime_entry = runtime[asset_id]
        if runtime_entry["kind"] != expected_entry["kind"]:
            raise VisualRenditionValidationError(
                f"runtime kind mismatch for {asset_id!r}"
            )
        if runtime_entry["role"] != expected_entry["role"]:
            raise VisualRenditionValidationError(
                f"runtime role mismatch for {asset_id!r}"
            )
        runtime_variants = runtime_entry["variants"]
        expected_variants = expected_entry["variants"]
        if runtime_variants != {
            name: variant.output_relative for name, variant in expected_variants.items()
        }:
            raise VisualRenditionValidationError(
                f"runtime variant mapping mismatch for {asset_id!r}"
            )
        for variant in expected_variants.values():
            output = (assets_root / variant.output_relative).resolve(strict=True)
            _require_within(assets_root, output, "runtime PNG")
            if not output.is_file():
                raise VisualRenditionValidationError(
                    f"runtime PNG is not a file: {variant.output_relative}"
                )
            _verify_png(output, variant.width, variant.height)


def _expected_variants(raw: Mapping[str, object]) -> dict[str, dict[str, object]]:
    entries = raw.get("visuals")
    if not isinstance(entries, list) or not entries:
        raise VisualRenditionValidationError("source spec has no visuals")
    result: dict[str, dict[str, object]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise VisualRenditionValidationError("source spec has invalid visual entry")
        asset_id = _text(entry, "id", "source visual")
        if asset_id in result:
            raise VisualRenditionValidationError(f"duplicate source visual id: {asset_id}")
        variants_raw = entry.get("variants")
        if not isinstance(variants_raw, list) or not variants_raw:
            raise VisualRenditionValidationError(
                f"source visual {asset_id!r} has no variants"
            )
        variants: dict[str, ExpectedVariant] = {}
        for variant in variants_raw:
            if not isinstance(variant, dict):
                raise VisualRenditionValidationError(
                    f"source visual {asset_id!r} has invalid variant"
                )
            name = _text(variant, "name", "source variant")
            if name in variants:
                raise VisualRenditionValidationError(
                    f"source visual {asset_id!r} has duplicate variant {name!r}"
                )
            width = _positive_int(variant, "width")
            height = _positive_int(variant, "height")
            variants[name] = ExpectedVariant(
                asset_id=asset_id,
                kind=_text(entry, "kind", "source visual"),
                role=_text(entry, "role", "source visual"),
                name=name,
                output_relative=_text(variant, "output", "source variant"),
                width=width,
                height=height,
            )
        if "default" not in variants:
            raise VisualRenditionValidationError(
                f"source visual {asset_id!r} has no default variant"
            )
        result[asset_id] = {
            "kind": _text(entry, "kind", "source visual"),
            "role": _text(entry, "role", "source visual"),
            "variants": variants,
        }
    return result


def _runtime_variants(raw: Mapping[str, object]) -> dict[str, dict[str, object]]:
    entries = raw.get("visuals")
    if not isinstance(entries, list) or not entries:
        raise VisualRenditionValidationError("runtime catalogue has no visuals")
    result: dict[str, dict[str, object]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise VisualRenditionValidationError(
                "runtime catalogue has invalid visual entry"
            )
        asset_id = _text(entry, "id", "runtime visual")
        if asset_id in result:
            raise VisualRenditionValidationError(f"duplicate runtime visual id: {asset_id}")
        variants = entry.get("variants")
        if not isinstance(variants, dict) or not variants:
            raise VisualRenditionValidationError(
                f"runtime visual {asset_id!r} has no variants"
            )
        normalized: dict[str, str] = {}
        for name, path in variants.items():
            if not isinstance(name, str) or not isinstance(path, str) or not path:
                raise VisualRenditionValidationError(
                    f"runtime visual {asset_id!r} has invalid variant mapping"
                )
            normalized[name] = path
        result[asset_id] = {
            "kind": _text(entry, "kind", "runtime visual"),
            "role": _text(entry, "role", "runtime visual"),
            "variants": normalized,
        }
    return result


def _verify_png(path: Path, width: int, height: int) -> None:
    data = path.read_bytes()
    if len(data) < 24 or data[:8] != _PNG_SIGNATURE or data[12:16] != b"IHDR":
        raise VisualRenditionValidationError(f"runtime output is not a PNG: {path}")
    actual_width, actual_height = struct.unpack(">II", data[16:24])
    if (actual_width, actual_height) != (width, height):
        raise VisualRenditionValidationError(
            f"runtime PNG dimensions mismatch for {path}: "
            f"{actual_width}x{actual_height} != {width}x{height}"
        )


def _load_toml(path: Path, label: str) -> Mapping[str, object]:
    try:
        with path.open("rb") as handle:
            raw = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise VisualRenditionValidationError(f"invalid {label}: {exc}") from exc
    return raw


def _text(entry: Mapping[str, object], key: str, label: str) -> str:
    value = entry.get(key)
    if not isinstance(value, str) or not value:
        raise VisualRenditionValidationError(
            f"{label} {key} must be a non-empty string"
        )
    return value


def _positive_int(entry: Mapping[str, object], key: str) -> int:
    value = entry.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise VisualRenditionValidationError(f"{key} must be a positive integer")
    return value


def _require_within(root: Path, candidate: Path, label: str) -> None:
    root_resolved = root.resolve()
    candidate_resolved = candidate.resolve()
    if candidate_resolved == root_resolved or root_resolved not in candidate_resolved.parents:
        raise VisualRenditionValidationError(f"{label} escapes assets root: {candidate}")


if __name__ == "__main__":
    raise SystemExit(main())
