#!/usr/bin/env python3
"""Package owner-accepted encyclopedia narration into the runtime Activity.

Authoring-time only. This tool never generates speech. It converts the human
coordination state in ``VOICE_RECORDING_REQUESTS.md`` into deterministic runtime
assets and locale ``audio`` mappings:

``OWNER_ACCEPTED`` staging OGG -> Activity asset -> locale cue mapping.

Rows at ``RECORDED_UNREVIEWED`` or any other status are deliberately ignored.
The whole accepted set is preflighted before writes, so a missing/corrupt source
cannot leave a partially updated Activity.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import argparse
import json
import sys
import tempfile

try:
    from .voice_ledger import VoiceLedgerRow, parse_ledger_rows
except ImportError:  # Direct script execution from the repository checkout.
    from voice_ledger import VoiceLedgerRow, parse_ledger_rows


DEFAULT_REPO_ROOT = Path(__file__).resolve().parent.parent
LEDGER_RELATIVE = Path("encyclopedia/VOICE_RECORDING_REQUESTS.md")
ACTIVITY_RELATIVE = Path("activities/enciclopedia_greia")
SUPPORTED_LOCALES = ("it", "en")
ACCEPTED_STATUS = "OWNER_ACCEPTED"


@dataclass(frozen=True, slots=True)
class AcceptedAsset:
    cue_id: str
    locale: str
    source: Path
    target: Path
    runtime_relative: str


@dataclass(frozen=True, slots=True)
class IntegrationReport:
    accepted_rows: int
    changed_paths: tuple[str, ...]

    @property
    def in_sync(self) -> bool:
        return not self.changed_paths


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _accepted_asset(row: VoiceLedgerRow, repo_root: Path) -> AcceptedAsset:
    if row.locale not in SUPPORTED_LOCALES:
        raise ValueError(f"unsupported locale for {row.key!r}: {row.locale!r}")
    if not row.cue_id.startswith("encyclopedia."):
        raise ValueError(f"invalid encyclopedia cue id: {row.cue_id!r}")
    if "\\" in row.path or "\\" in row.filename:
        raise ValueError(f"voice path must use POSIX separators: {row.path!r}")

    relative = PurePosixPath(row.path)
    parts = relative.parts
    if relative.is_absolute() or ".." in parts or "." in parts:
        raise ValueError(f"unsafe staging path for {row.key!r}: {row.path!r}")
    if len(parts) < 7 or parts[:2] != ("encyclopedia", "pages"):
        raise ValueError(f"unexpected staging root for {row.key!r}: {row.path!r}")

    try:
        assets_index = parts.index("assets", 2)
    except ValueError as exc:
        raise ValueError(f"missing assets/audio segment for {row.key!r}: {row.path!r}") from exc

    page_parts = parts[2:assets_index]
    tail = parts[assets_index:]
    if not page_parts or len(tail) != 4 or tail[:2] != ("assets", "audio"):
        raise ValueError(f"invalid staging layout for {row.key!r}: {row.path!r}")
    if tail[2] != row.locale:
        raise ValueError(
            f"staging locale mismatch for {row.key!r}: path has {tail[2]!r}"
        )
    if tail[3] != row.filename:
        raise ValueError(
            f"staging filename mismatch for {row.key!r}: path has {tail[3]!r}"
        )
    if not row.filename.endswith(".ogg") or PurePosixPath(row.filename).name != row.filename:
        raise ValueError(f"invalid final OGG filename for {row.key!r}: {row.filename!r}")

    authoring_root = (repo_root / "encyclopedia").resolve()
    activity_root = (repo_root / ACTIVITY_RELATIVE).resolve()
    source = (repo_root / Path(*parts)).resolve()
    if not _is_within(source, authoring_root):
        raise ValueError(f"staging path escapes encyclopedia root: {row.path!r}")

    runtime_relative_path = PurePosixPath(
        "assets", "audio", row.locale, *page_parts, row.filename
    )
    target = (activity_root / Path(*runtime_relative_path.parts)).resolve()
    if not _is_within(target, activity_root):
        raise ValueError(f"runtime audio path escapes Activity root for {row.key!r}")

    return AcceptedAsset(
        cue_id=row.cue_id,
        locale=row.locale,
        source=source,
        target=target,
        runtime_relative=runtime_relative_path.as_posix(),
    )


def plan_accepted_assets(ledger_text: str, repo_root: Path) -> tuple[AcceptedAsset, ...]:
    """Return a deterministic, validated plan for all OWNER_ACCEPTED rows."""

    rows = parse_ledger_rows(ledger_text)
    accepted = [
        _accepted_asset(row, repo_root)
        for row in rows.values()
        if row.status == ACCEPTED_STATUS
    ]
    accepted.sort(key=lambda item: (item.locale, item.cue_id))

    target_keys: set[Path] = set()
    for asset in accepted:
        if asset.target in target_keys:
            raise ValueError(f"multiple accepted rows target the same file: {asset.target}")
        target_keys.add(asset.target)
    return tuple(accepted)


def _read_ogg(path: Path, *, cue_id: str, locale: str) -> bytes:
    if not path.is_file():
        raise FileNotFoundError(
            f"OWNER_ACCEPTED source is missing for {(cue_id, locale)!r}: {path}"
        )
    payload = path.read_bytes()
    if len(payload) < 4 or payload[:4] != b"OggS":
        raise ValueError(
            f"OWNER_ACCEPTED source is not an OGG container for {(cue_id, locale)!r}: {path}"
        )
    return payload


def _expected_locale_payload(
    current: dict[str, object],
    locale: str,
    assets: tuple[AcceptedAsset, ...],
    managed_cues: set[str],
) -> dict[str, object]:
    if current.get("locale") != locale:
        raise ValueError(
            f"locale bundle identity mismatch: expected {locale!r}, got {current.get('locale')!r}"
        )
    if not isinstance(current.get("strings"), dict):
        raise ValueError(f"locale {locale!r} is missing a strings object")
    current_audio = current.get("audio")
    if not isinstance(current_audio, dict):
        raise ValueError(f"locale {locale!r} is missing an audio object")

    accepted_audio = {
        asset.cue_id: asset.runtime_relative
        for asset in assets
        if asset.locale == locale
    }
    if len(accepted_audio) != sum(1 for asset in assets if asset.locale == locale):
        raise ValueError(f"duplicate accepted cue mapping in locale {locale!r}")

    # The voice ledger owns narration cues only. Preserve any unrelated Activity
    # audio mapping (for example a future licensed animal call) rather than
    # treating the entire locale audio object as voice-tool property.
    expected_audio = {
        str(cue_id): str(relative_path)
        for cue_id, relative_path in current_audio.items()
        if cue_id not in managed_cues
    }
    expected_audio.update(accepted_audio)

    result = dict(current)
    result["audio"] = dict(sorted(expected_audio.items()))
    return result


def _serialize_json(payload: dict[str, object]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _atomic_write(path: Path, payload: bytes) -> None:
    """Replace one file atomically after writing a sibling temporary file."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(payload)
            handle.flush()
            temporary = Path(handle.name)
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def integrate_accepted_assets(
    repo_root: Path = DEFAULT_REPO_ROOT,
    *,
    check_only: bool = False,
) -> IntegrationReport:
    """Synchronize accepted assets and locale maps, or report drift in check mode."""

    repo_root = repo_root.resolve()
    ledger_path = repo_root / LEDGER_RELATIVE
    activity_root = repo_root / ACTIVITY_RELATIVE
    ledger_text = ledger_path.read_text(encoding="utf-8")
    ledger_rows = parse_ledger_rows(ledger_text)
    assets = plan_accepted_assets(ledger_text, repo_root)
    managed_cues_by_locale = {
        locale: {
            row.cue_id
            for row in ledger_rows.values()
            if row.locale == locale
        }
        for locale in SUPPORTED_LOCALES
    }

    # Full preflight: validate every accepted source and both locale bundles
    # before any filesystem mutation.
    source_payloads = {
        asset: _read_ogg(asset.source, cue_id=asset.cue_id, locale=asset.locale)
        for asset in assets
    }
    locale_expected: dict[str, tuple[Path, bytes]] = {}
    for locale in SUPPORTED_LOCALES:
        locale_path = activity_root / "locales" / f"{locale}.json"
        current = json.loads(locale_path.read_text(encoding="utf-8"))
        if not isinstance(current, dict):
            raise ValueError(f"locale bundle must be a JSON object: {locale_path}")
        expected = _expected_locale_payload(
            current,
            locale,
            assets,
            managed_cues_by_locale[locale],
        )
        locale_expected[locale] = (locale_path, _serialize_json(expected))

    changed: list[str] = []
    for asset, payload in source_payloads.items():
        if not asset.target.is_file() or asset.target.read_bytes() != payload:
            changed.append(asset.target.relative_to(repo_root).as_posix())

    for locale in SUPPORTED_LOCALES:
        locale_path, expected_bytes = locale_expected[locale]
        if locale_path.read_bytes() != expected_bytes:
            changed.append(locale_path.relative_to(repo_root).as_posix())

    changed = sorted(set(changed))
    if check_only or not changed:
        return IntegrationReport(len(assets), tuple(changed))

    # Preflight succeeded. Package files first; locale maps are replaced last so
    # runtime never points at an accepted asset that has not been written yet.
    for asset, payload in source_payloads.items():
        if not asset.target.is_file() or asset.target.read_bytes() != payload:
            _atomic_write(asset.target, payload)

    for locale in SUPPORTED_LOCALES:
        locale_path, expected_bytes = locale_expected[locale]
        if locale_path.read_bytes() != expected_bytes:
            _atomic_write(locale_path, expected_bytes)

    return IntegrationReport(len(assets), tuple(changed))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="report drift without copying audio or rewriting locale bundles",
    )
    args = parser.parse_args(argv)

    try:
        report = integrate_accepted_assets(check_only=args.check)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"voice asset integration failed: {exc}", file=sys.stderr)
        return 2

    if args.check and not report.in_sync:
        print("accepted voice assets are out of sync:", file=sys.stderr)
        for path in report.changed_paths:
            print(f"  {path}", file=sys.stderr)
        return 1

    if report.in_sync:
        print(f"accepted voice assets already synchronized ({report.accepted_rows} rows)")
    else:
        print(
            f"accepted voice assets synchronized ({report.accepted_rows} rows; "
            f"{len(report.changed_paths)} paths changed)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
