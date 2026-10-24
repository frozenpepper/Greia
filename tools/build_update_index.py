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
version's entries; the newest three releases per exact target and the
``parents_app`` block are kept. Artifact files are never deleted.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

SCHEMA = "greia-updates/1"
CHANNELS = ("stable", "dev")
MAX_NOTES = 4096
MAX_CHANNEL_ENTRIES = 128
MAX_INDEX_BYTES = 512 * 1024
DEFAULT_KEEP_RELEASES = 3


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
    if report.get("artifact_class", "release") != "release" or report.get(
        "release_eligible", True
    ) is not True:
        raise SystemExit(
            f"{report_path}: experimental or non-release-eligible artifacts "
            "cannot be added to a public update index"
        )
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


def merge(
    index: dict[str, object], channel: str, entries: list[dict[str, object]],
    *, keep_releases: int = DEFAULT_KEEP_RELEASES,
) -> dict[str, object]:
    releases = index["greia_os"]["channels"][channel]  # type: ignore[index]
    replaced = {(entry["version"], tuple(entry["profiles"])) for entry in entries}
    kept = [item for item in releases if (item.get("version"), tuple(item.get("profiles", []))) not in replaced]
    # Retain a short history per exact target without allowing a long-lived
    # channel to grow beyond the device catalog reader's bounded work budget.
    counts: dict[tuple[object, ...], int] = {}
    retained = []
    for entry in [*entries, *kept]:
        target = (tuple(entry.get("profiles", [])), entry.get("platform_family"),
                  entry.get("architecture"), entry.get("board"))
        count = counts.get(target, 0)
        if count < keep_releases:
            retained.append(entry)
            counts[target] = count + 1
    if len(retained) > MAX_CHANNEL_ENTRIES:
        raise SystemExit("channel exceeds 128 entries; reduce --keep-releases or retire old targets")
    index["greia_os"]["channels"][channel] = retained  # type: ignore[index]
    index["updated_at"] = _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()
    return index


def write_index(path: Path, index: dict[str, object]) -> None:
    """Publish a complete local index, preserving the previous file on failure."""
    raw = (json.dumps(index, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    if len(raw) > MAX_INDEX_BYTES:
        raise SystemExit("index exceeds the device catalog's 512 KiB limit")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: str | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as handle:
            temporary = handle.name
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            Path(temporary).unlink(missing_ok=True)


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
    parser.add_argument("--notes-es")
    parser.add_argument("--notes-fr")
    parser.add_argument("--keep-releases", type=int, default=DEFAULT_KEEP_RELEASES,
                        help="retained releases per exact target (default: 3; artifacts are not deleted)")
    parser.add_argument("--install-help-url")
    parser.add_argument("--published-at", default=_dt.date.today().isoformat())
    args = parser.parse_args(argv)

    if not 1 <= args.keep_releases <= MAX_CHANNEL_ENTRIES:
        parser.error("--keep-releases must be between 1 and 128")
    notes = {locale: value for locale in ("en", "it", "es", "fr")
             if (value := read_notes(getattr(args, f"notes_{locale}")))}
    index = load_index(args.index)
    entries = release_entries(
        args.release,
        base_url=args.base_url,
        notes=notes,
        install_help_url=args.install_help_url,
        published_at=args.published_at,
    )
    merge(index, args.channel, entries, keep_releases=args.keep_releases)
    write_index(args.index, index)
    print(f"{args.index}: {len(entries)} {args.channel} entr{'y' if len(entries) == 1 else 'ies'} for {entries[0]['version'] if entries else '-'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
