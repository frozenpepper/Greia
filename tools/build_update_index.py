#!/usr/bin/env python3
"""Build or update the public Greia update channel index (``greia-updates.json``).

Parent clients (the HTML and native Parent apps) fetch this one static file to
tell parents whether a newer Greia release exists for their device. It is a
plain, unsigned discovery document (ADR 0036: no signing authority); checksums
are transfer aids only. Greia itself still validates every bundle before any
slot write, and installing remains a Greia-side action.

Typical use after ``tools/greia_release.py`` produced a release directory::

    python3 tools/build_update_index.py \\
        --release out/releases/greia-0.14.0 \\
        --base-url https://example.org/greia/updates/0.14.0 \\
        --channel stable \\
        --notes-en notes-en.txt --notes-it notes-it.txt \\
        --install-help-url https://example.org/greia/how-to-update \\
        --index site/updates/greia-updates.json

Then upload the release's ``updates/*.greiaupdate`` files under ``--base-url``
and the index file to the site. Re-running for the same version replaces that
version's entries; other releases and the ``parents_app`` block are kept.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import sys
from pathlib import Path

SCHEMA = "greia-updates/1"
CHANNELS = ("stable", "dev")
MAX_NOTES = 4096


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def empty_index() -> dict[str, object]:
    return {
        "schema": SCHEMA,
        "updated_at": None,
        "parents_app": None,
        "greia_os": {"channels": {channel: [] for channel in CHANNELS}},
    }


def load_index(path: Path) -> dict[str, object]:
    if not path.exists():
        return empty_index()
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != SCHEMA:
        raise SystemExit(f"{path}: unsupported schema {data.get('schema')!r}")
    channels = data.setdefault("greia_os", {}).setdefault("channels", {})
    for channel in CHANNELS:
        channels.setdefault(channel, [])
    return data


def release_entries(
    release_root: Path,
    *,
    base_url: str,
    notes: dict[str, str],
    install_help_url: str | None,
    published_at: str,
) -> list[dict[str, object]]:
    report_path = release_root / "release-report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("status") != "complete":
        raise SystemExit(f"{report_path}: release is not complete")
    version = str(report["version"])
    base = base_url.rstrip("/")
    entries: list[dict[str, object]] = []
    for profile in report.get("profiles", []):
        profile_id = str(profile["profile_id"])
        bundle = release_root / "updates" / f"{profile_id}.greiaupdate"
        if not bundle.is_file():
            raise SystemExit(f"missing update bundle for {profile_id}: {bundle}")
        entries.append(
            {
                "version": version,
                "release_id": str(report.get("release_id") or f"greia-{version}"),
                "published_at": published_at,
                "profiles": [profile_id],
                "platform_family": profile.get("platform_family"),
                "architecture": profile.get("architecture"),
                "board": profile.get("board"),
                "notes": notes,
                "update": {
                    "url": f"{base}/{bundle.name}",
                    "size": bundle.stat().st_size,
                    "sha256": sha256_file(bundle),
                },
                "setup_image": None,
                "install_help_url": install_help_url,
            }
        )
    return entries


def merge(index: dict[str, object], channel: str, entries: list[dict[str, object]]) -> dict[str, object]:
    releases = index["greia_os"]["channels"][channel]  # type: ignore[index]
    replaced = {(entry["version"], tuple(entry["profiles"])) for entry in entries}
    kept = [item for item in releases if (item.get("version"), tuple(item.get("profiles", []))) not in replaced]
    index["greia_os"]["channels"][channel] = [*entries, *kept]  # type: ignore[index]
    index["updated_at"] = _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()
    return index


def read_notes(path: str | None) -> str | None:
    if not path:
        return None
    text = Path(path).read_text(encoding="utf-8").strip()
    if len(text) > MAX_NOTES:
        raise SystemExit(f"{path}: release notes exceed {MAX_NOTES} characters")
    return text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--release", required=True, type=Path, help="release directory containing release-report.json")
    parser.add_argument("--base-url", required=True, help="public URL where this release's .greiaupdate files are hosted")
    parser.add_argument("--channel", choices=CHANNELS, default="stable")
    parser.add_argument("--index", required=True, type=Path, help="greia-updates.json to create or update")
    parser.add_argument("--notes-en")
    parser.add_argument("--notes-it")
    parser.add_argument("--install-help-url")
    parser.add_argument("--published-at", default=_dt.date.today().isoformat())
    args = parser.parse_args(argv)

    notes = {key: value for key, value in (("en", read_notes(args.notes_en)), ("it", read_notes(args.notes_it))) if value}
    index = load_index(args.index)
    entries = release_entries(
        args.release,
        base_url=args.base_url,
        notes=notes,
        install_help_url=args.install_help_url,
        published_at=args.published_at,
    )
    merge(index, args.channel, entries)
    args.index.parent.mkdir(parents=True, exist_ok=True)
    args.index.write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{args.index}: {len(entries)} {args.channel} entr{'y' if len(entries) == 1 else 'ies'} for {entries[0]['version'] if entries else '-'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
