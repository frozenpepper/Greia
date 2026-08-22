#!/usr/bin/env python3
"""
Greia Generic Visual Authoring Library Helper
Authoring/development tooling for discovering, searching, and validating generic source assets.
"""

import argparse
import json
import os
import sys
import tomllib
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LIBRARY_DIR = REPO_ROOT / "assets" / "visual" / "authoring_library"
ALLOWED_STATUSES = {"preferred", "candidate_reference"}


def load_library(library_dir: Optional[Path] = None) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Loads all collection TOMLs from the library directory."""
    if library_dir is None:
        library_dir = DEFAULT_LIBRARY_DIR

    collections: List[Dict[str, Any]] = []
    errors: List[str] = []

    if not library_dir.exists() or not library_dir.is_dir():
        errors.append(f"Library directory does not exist: {library_dir}")
        return collections, errors

    for toml_path in sorted(library_dir.glob("*.toml")):
        try:
            with open(toml_path, "rb") as f:
                data = tomllib.load(f)
            data["_file"] = str(toml_path.relative_to(REPO_ROOT) if toml_path.is_relative_to(REPO_ROOT) else toml_path)
            collections.append(data)
        except Exception as e:
            errors.append(f"Failed to parse {toml_path}: {e}")

    return collections, errors


def get_all_items(collections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Flattens all assets and ingredients across collections with collection context."""
    items = []
    for col_data in collections:
        col = col_data.get("collection", {})
        col_id = col.get("id", "unknown")
        col_name = col.get("name", "Unknown")

        for asset in col_data.get("assets", []):
            item = dict(asset)
            item["collection_id"] = col_id
            item["collection_name"] = col_name
            item["item_type"] = "finished"
            items.append(item)

        for ing in col_data.get("ingredients", []):
            item = dict(ing)
            item["collection_id"] = col_id
            item["collection_name"] = col_name
            item["item_type"] = "ingredient"
            items.append(item)
    return items


def cmd_collections(args: argparse.Namespace, collections: List[Dict[str, Any]]) -> int:
    results = []
    for col_data in collections:
        col = col_data.get("collection", {})
        assets = col_data.get("assets", [])
        ings = col_data.get("ingredients", [])

        pref_assets = sum(1 for a in assets if a.get("library_status") == "preferred")
        cand_assets = sum(1 for a in assets if a.get("library_status") == "candidate_reference")
        pref_ings = sum(1 for i in ings if i.get("library_status") == "preferred")
        cand_ings = sum(1 for i in ings if i.get("library_status") == "candidate_reference")

        col_info = {
            "id": col.get("id"),
            "name": col.get("name"),
            "description": col.get("description"),
            "version": col.get("version"),
            "file": col_data.get("_file"),
            "stats": {
                "preferred_finished": pref_assets,
                "candidate_finished": cand_assets,
                "total_finished": len(assets),
                "preferred_ingredients": pref_ings,
                "candidate_ingredients": cand_ings,
                "total_ingredients": len(ings),
                "total_resources": len(assets) + len(ings),
            },
        }
        results.append(col_info)

    if getattr(args, "json", False):
        print(json.dumps(results, indent=2))
        return 0

    print(f"Generic Visual Authoring Library — {len(results)} Collections:")
    print("=" * 80)
    for c in results:
        stats = c["stats"]
        print(f"• {c['id']} — {c['name']} (v{c.get('version', '1.0.0')})")
        print(f"  Description: {c['description']}")
        print(f"  Finished Assets: {stats['total_finished']} ({stats['preferred_finished']} preferred, {stats['candidate_finished']} candidate)")
        print(f"  Ingredients:     {stats['total_ingredients']} ({stats['preferred_ingredients']} preferred, {stats['candidate_ingredients']} candidate)")
        print(f"  Index File:      {c['file']}")
        print()
    return 0


def filter_items(
    items: List[Dict[str, Any]],
    collection: Optional[str] = None,
    status: Optional[str] = None,
    kind: Optional[str] = None,
) -> List[Dict[str, Any]]:
    filtered = items

    if collection:
        col_norm = collection.lower()
        filtered = [
            i for i in filtered
            if col_norm in i.get("collection_id", "").lower()
            or col_norm in i.get("collection_name", "").lower()
        ]

    if status:
        stat_norm = status.lower()
        filtered = [i for i in filtered if i.get("library_status", "").lower() == stat_norm]

    if kind:
        kind_norm = kind.lower()
        if kind_norm in ("finished", "ingredient"):
            filtered = [i for i in filtered if i.get("item_type") == kind_norm]

    return filtered


def cmd_list(args: argparse.Namespace, collections: List[Dict[str, Any]]) -> int:
    items = get_all_items(collections)
    filtered = filter_items(items, collection=args.collection, status=args.status, kind=args.kind)

    if getattr(args, "json", False):
        print(json.dumps(filtered, indent=2))
        return 0

    print(f"Generic Visual Authoring Library — {len(filtered)} items:")
    print("=" * 80)
    for item in filtered:
        status_flag = "[PREFERRED]" if item.get("library_status") == "preferred" else "[CANDIDATE]"
        kind_flag = "(ingredient)" if item.get("item_type") == "ingredient" else ""
        print(f"{status_flag:12} {item.get('id')} {kind_flag}")
        print(f"             Collection: {item.get('collection_id')} | Family: {item.get('family')} | Role: {item.get('role')}")
        print(f"             Path: {item.get('source_path')}")
        if item.get("notes"):
            print(f"             Notes: {item.get('notes')}")
        print()
    return 0


def search_match(item: Dict[str, Any], query_tokens: List[str]) -> bool:
    search_fields = [
        item.get("id", ""),
        item.get("collection_id", ""),
        item.get("collection_name", ""),
        item.get("family", ""),
        item.get("role", ""),
        item.get("notes", ""),
        item.get("source_pack", ""),
        item.get("source_path", ""),
        " ".join(item.get("tags", [])),
    ]
    haystack = " ".join(search_fields).lower()
    return all(token in haystack for token in query_tokens)


def cmd_search(args: argparse.Namespace, collections: List[Dict[str, Any]]) -> int:
    items = get_all_items(collections)
    filtered = filter_items(items, collection=args.collection, status=args.status, kind=args.kind)

    query_tokens = args.query.lower().split()
    matched = [i for i in filtered if search_match(i, query_tokens)]

    if getattr(args, "json", False):
        print(json.dumps(matched, indent=2))
        return 0

    print(f"Search Query: \"{args.query}\" — {len(matched)} matching items:")
    print("=" * 80)
    for item in matched:
        status_flag = "[PREFERRED]" if item.get("library_status") == "preferred" else "[CANDIDATE]"
        kind_flag = "(ingredient)" if item.get("item_type") == "ingredient" else ""
        print(f"{status_flag:12} {item.get('id')} {kind_flag}")
        print(f"             Collection: {item.get('collection_id')} | Family: {item.get('family')} | Role: {item.get('role')}")
        print(f"             Path: {item.get('source_path')}")
        if item.get("tags"):
            print(f"             Tags: {', '.join(item.get('tags', []))}")
        if item.get("min_recommended_px"):
            print(f"             Size: {item.get('min_recommended_px')}px – {item.get('max_recommended_px')}px")
        if item.get("notes"):
            print(f"             Notes: {item.get('notes')}")
        print()
    return 0


def cmd_show(args: argparse.Namespace, collections: List[Dict[str, Any]]) -> int:
    items = get_all_items(collections)
    target_id = args.id.strip().lower()

    match = None
    for item in items:
        if item.get("id", "").lower() == target_id:
            match = item
            break

    if not match:
        if getattr(args, "json", False):
            print(json.dumps({"error": f"Item not found: {args.id}"}, indent=2))
        else:
            print(f"Error: Asset or ingredient with ID \"{args.id}\" was not found in the generic library.", file=sys.stderr)
        return 1

    if getattr(args, "json", False):
        print(json.dumps(match, indent=2))
        return 0

    print(f"Generic Asset: {match.get('id')}")
    print("=" * 80)
    print(f"Collection:       {match.get('collection_name')} ({match.get('collection_id')})")
    print(f"Library Status:   {match.get('library_status')}")
    print(f"Item Type:        {match.get('item_type')}")
    print(f"Family / Role:    {match.get('family')} / {match.get('role')}")
    print(f"Source Pack:      {match.get('source_pack')}")
    print(f"Source Path:      {match.get('source_path')}")
    print(f"Tags:             {', '.join(match.get('tags', []))}")
    if match.get("min_recommended_px"):
        print(f"Recommended Size: {match.get('min_recommended_px')}px – {match.get('max_recommended_px')}px")
    if match.get("alpha") is not None:
        print(f"Alpha:            {match.get('alpha')}")
    print(f"Notes:            {match.get('notes')}")
    return 0


def cmd_validate(args: argparse.Namespace, library_dir: Optional[Path] = None) -> int:
    if library_dir is None:
        library_dir = DEFAULT_LIBRARY_DIR

    collections, parse_errors = load_library(library_dir)
    errors: List[str] = list(parse_errors)
    warnings: List[str] = []

    seen_ids: Dict[str, str] = {}
    total_resources = 0

    for col_data in collections:
        rel_file = col_data.get("_file", "unknown")
        col = col_data.get("collection", {})
        if not col.get("id"):
            errors.append(f"{rel_file}: Missing required collection.id")
        if not col.get("name"):
            errors.append(f"{rel_file}: Missing required collection.name")
        if not col.get("description"):
            errors.append(f"{rel_file}: Missing required collection.description")

        all_entries = []
        for a in col_data.get("assets", []):
            all_entries.append((a, "asset"))
        for i in col_data.get("ingredients", []):
            all_entries.append((i, "ingredient"))

        for entry, entry_type in all_entries:
            total_resources += 1
            item_id = entry.get("id")
            if not item_id:
                errors.append(f"{rel_file}: {entry_type} missing 'id'")
                continue

            if item_id in seen_ids:
                errors.append(f"Duplicate ID '{item_id}' in {rel_file} (already defined in {seen_ids[item_id]})")
            else:
                seen_ids[item_id] = rel_file

            status = entry.get("library_status")
            if not status or status not in ALLOWED_STATUSES:
                errors.append(f"{rel_file}: Item '{item_id}' has invalid library_status '{status}' (expected one of {sorted(ALLOWED_STATUSES)})")

            if not entry.get("source_pack"):
                errors.append(f"{rel_file}: Item '{item_id}' missing 'source_pack'")

            source_path_str = entry.get("source_path")
            if not source_path_str:
                errors.append(f"{rel_file}: Item '{item_id}' missing 'source_path'")
            else:
                if not source_path_str.startswith("assets/visual/"):
                    errors.append(f"{rel_file}: Item '{item_id}' source_path '{source_path_str}' must be within 'assets/visual/'")

                full_path = REPO_ROOT / source_path_str
                if not full_path.is_file():
                    errors.append(f"{rel_file}: Item '{item_id}' source file not found on disk: {source_path_str}")

            if not entry.get("family"):
                errors.append(f"{rel_file}: Item '{item_id}' missing 'family'")
            if not entry.get("role"):
                errors.append(f"{rel_file}: Item '{item_id}' missing 'role'")

    result = {
        "valid": len(errors) == 0,
        "collections_count": len(collections),
        "total_resources_checked": total_resources,
        "errors_count": len(errors),
        "warnings_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
    }

    if getattr(args, "json", False):
        print(json.dumps(result, indent=2))
        return 0 if len(errors) == 0 else 1

    print("Generic Visual Authoring Library Validation Report")
    print("=" * 80)
    print(f"Collections Checked: {len(collections)}")
    print(f"Total Resources:     {total_resources}")
    print(f"Validation Status:   {'PASSED' if len(errors) == 0 else 'FAILED'}")
    print(f"Errors:              {len(errors)}")
    print(f"Warnings:            {len(warnings)}")
    print()

    if errors:
        print("ERRORS:")
        for err in errors:
            print(f"  [ERROR] {err}")
        print()

    if warnings:
        print("WARNINGS:")
        for warn in warnings:
            print(f"  [WARN]  {warn}")
        print()

    return 0 if len(errors) == 0 else 1


def main() -> int:
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    parent_parser.add_argument("--library-dir", type=Path, default=None, help="Custom authoring library directory")

    parser = argparse.ArgumentParser(description="Greia Generic Visual Authoring Library Discovery Tool", parents=[parent_parser])
    subparsers = parser.add_subparsers(dest="command", required=True)

    # collections
    subparsers.add_parser("collections", parents=[parent_parser], help="List all generic visual collections")

    # list
    list_parser = subparsers.add_parser("list", parents=[parent_parser], help="List assets across collections")
    list_parser.add_argument("--collection", "-c", type=str, default=None, help="Filter by collection ID or name")
    list_parser.add_argument("--status", "-s", type=str, default=None, help="Filter by library status (preferred / candidate_reference)")
    list_parser.add_argument("--kind", "-k", type=str, default=None, help="Filter by item kind (finished / ingredient)")

    # search
    search_parser = subparsers.add_parser("search", parents=[parent_parser], help="Search assets across semantic ID, tags, roles, notes")
    search_parser.add_argument("query", type=str, help="Search query string")
    search_parser.add_argument("--collection", "-c", type=str, default=None, help="Filter by collection ID or name")
    search_parser.add_argument("--status", "-s", type=str, default=None, help="Filter by library status (preferred / candidate_reference)")
    search_parser.add_argument("--kind", "-k", type=str, default=None, help="Filter by item kind (finished / ingredient)")

    # show
    show_parser = subparsers.add_parser("show", parents=[parent_parser], help="Show full details for an asset by ID")
    show_parser.add_argument("id", type=str, help="Semantic asset ID")

    # validate
    subparsers.add_parser("validate", parents=[parent_parser], help="Validate structural integrity of library TOMLs and source file existence")

    args = parser.parse_args()

    if args.command == "validate":
        return cmd_validate(args, library_dir=args.library_dir)

    collections, errors = load_library(library_dir=args.library_dir)
    if errors and not getattr(args, "json", False):
        for e in errors:
            print(f"Warning: {e}", file=sys.stderr)

    if args.command == "collections":
        return cmd_collections(args, collections)
    elif args.command == "list":
        return cmd_list(args, collections)
    elif args.command == "search":
        return cmd_search(args, collections)
    elif args.command == "show":
        return cmd_show(args, collections)

    return 0


if __name__ == "__main__":
    sys.exit(main())
