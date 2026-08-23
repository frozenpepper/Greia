#!/usr/bin/env python3
"""Regenerate Greia's exact Parent HTML client pin from a reviewed checkout.

The caller supplies a local clean Parent checkout and the exact commit SHA that
was reviewed/tested. Runtime files are discovered from the actual ``index.html``
module/style graph, then every discovered file is hashed from exact bytes.

This deliberately avoids a stale hand-maintained file list: adding a new local
ES module or stylesheet to the Parent app automatically adds it to the generated
integrity manifest, while unreferenced source/tests/docs remain outside the
runtime payload.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit


REVISION_LINE = re.compile(r'^revision = "[0-9a-f]{40}"$', re.MULTILINE)
STATIC_IMPORT = re.compile(
    r"(?:^|\n)\s*(?:import|export)\s+(?:[^;\n]*?\s+from\s+)?[\"']([^\"']+)[\"']",
    re.MULTILINE,
)
CSS_IMPORT = re.compile(r"@import\s+(?:url\()?\s*[\"']([^\"']+)[\"']\s*\)?", re.IGNORECASE)
CSS_URL = re.compile(r"url\(\s*[\"']?([^\"')]+)[\"']?\s*\)", re.IGNORECASE)


class PinError(RuntimeError):
    pass


class _RuntimeHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.references: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {name.casefold(): value for name, value in attrs}
        tag = tag.casefold()
        if tag == "script" and values.get("src"):
            self.references.append(str(values["src"]))
        elif tag == "link" and values.get("href"):
            rel = str(values.get("rel") or "").casefold().split()
            if "stylesheet" in rel:
                self.references.append(str(values["href"]))
        elif tag in {"img", "source"} and values.get("src"):
            self.references.append(str(values["src"]))


def _git(parent_root: Path, *args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", "-C", str(parent_root), *args],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise PinError(f"could not inspect Parent checkout: {exc}") from exc
    return completed.stdout.strip()


def _validate_parent_checkout(parent_root: Path, revision: str) -> None:
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise PinError("revision must be an exact 40-character lowercase Git SHA")
    head = _git(parent_root, "rev-parse", "HEAD")
    if head != revision:
        raise PinError(f"Parent checkout HEAD is {head}, expected {revision}")
    dirty = _git(parent_root, "status", "--porcelain")
    if dirty:
        raise PinError("Parent checkout is dirty; commit/review changes before pinning")


def _load_manifest_metadata(path: Path) -> dict[str, object]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PinError(f"invalid existing Parent manifest: {exc}") from exc
    if document.get("schema_version") != 1:
        raise PinError("Parent manifest must use schema 1")
    return document


def _local_reference(base: PurePosixPath, reference: str) -> PurePosixPath | None:
    """Resolve one same-package relative reference or return None for fragments/data."""

    reference = reference.strip()
    if not reference or reference.startswith(("#", "data:")):
        return None
    parsed = urlsplit(reference)
    if parsed.scheme or parsed.netloc:
        raise PinError(f"remote Parent runtime dependency is forbidden: {reference}")
    raw_path = parsed.path
    if not raw_path:
        return None
    if raw_path.startswith("/"):
        raise PinError(f"Parent runtime reference must be package-relative: {reference}")
    combined = base.parent.joinpath(PurePosixPath(raw_path))
    parts: list[str] = []
    for part in combined.parts:
        if part in {"", "."}:
            continue
        if part == "..":
            if not parts:
                raise PinError(f"Parent runtime reference escapes checkout: {reference}")
            parts.pop()
        else:
            parts.append(part)
    if not parts:
        raise PinError(f"invalid Parent runtime reference: {reference}")
    resolved = PurePosixPath(*parts)
    if any(part.startswith(".") for part in resolved.parts):
        raise PinError(f"hidden Parent runtime path is not supported: {resolved}")
    return resolved


def _references_for(relative: PurePosixPath, data: bytes) -> list[PurePosixPath]:
    suffix = relative.suffix.casefold()
    if suffix not in {".html", ".js", ".css"}:
        return []
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PinError(f"Parent runtime source is not UTF-8: {relative}") from exc

    raw: list[str] = []
    if suffix == ".html":
        parser = _RuntimeHtmlParser()
        parser.feed(text)
        raw.extend(parser.references)
    elif suffix == ".js":
        raw.extend(match.group(1) for match in STATIC_IMPORT.finditer(text))
    else:
        raw.extend(match.group(1) for match in CSS_IMPORT.finditer(text))
        raw.extend(match.group(1) for match in CSS_URL.finditer(text))

    output: list[PurePosixPath] = []
    for reference in raw:
        resolved = _local_reference(relative, reference)
        if resolved is not None:
            output.append(resolved)
    return output


def _discover_runtime_files(parent_root: Path) -> list[str]:
    """Return the exact transitive runtime closure rooted at ``index.html``."""

    checkout = parent_root.resolve()
    pending = [PurePosixPath("index.html")]
    visited: set[PurePosixPath] = set()
    while pending:
        relative = pending.pop()
        if relative in visited:
            continue
        path = (checkout / Path(*relative.parts)).resolve()
        try:
            path.relative_to(checkout)
        except ValueError as exc:
            raise PinError(f"runtime file escapes Parent checkout: {relative}") from exc
        if not path.is_file():
            raise PinError(f"referenced Parent runtime file is missing: {relative}")
        data = path.read_bytes()
        visited.add(relative)
        for dependency in _references_for(relative, data):
            if dependency not in visited:
                pending.append(dependency)
    return [path.as_posix() for path in sorted(visited, key=lambda value: value.as_posix())]


def _hash_runtime_files(parent_root: Path, relative_paths: list[str]) -> dict[str, dict[str, object]]:
    output: dict[str, dict[str, object]] = {}
    checkout = parent_root.resolve()
    for relative in relative_paths:
        path = (checkout / relative).resolve()
        try:
            path.relative_to(checkout)
        except ValueError as exc:
            raise PinError(f"runtime file escapes Parent checkout: {relative}") from exc
        if not path.is_file():
            raise PinError(f"required Parent runtime file is missing: {relative}")
        data = path.read_bytes()
        output[relative] = {
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }
    return output


def update_pin(greia_root: Path, parent_root: Path, revision: str) -> tuple[Path, Path]:
    greia_root = greia_root.resolve()
    parent_root = parent_root.resolve()
    _validate_parent_checkout(parent_root, revision)

    config_path = greia_root / "runtime" / "parent-app-client.toml"
    manifest_path = greia_root / "runtime" / "parent-app-client.manifest.json"
    manifest = _load_manifest_metadata(manifest_path)
    relative_paths = _discover_runtime_files(parent_root)
    hashed = _hash_runtime_files(parent_root, relative_paths)
    rewritten_manifest = {
        "files": hashed,
        "repository": manifest.get("repository", "frozenpepper/Greia-Parent-App-Html"),
        "revision": revision,
        "schema_version": 1,
    }

    try:
        config = config_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise PinError(f"could not read Parent pin config: {exc}") from exc
    matches = REVISION_LINE.findall(config)
    if len(matches) != 1:
        raise PinError("Parent pin config must contain exactly one exact revision line")
    rewritten_config = REVISION_LINE.sub(f'revision = "{revision}"', config, count=1)

    manifest_text = json.dumps(rewritten_manifest, indent=2, ensure_ascii=False) + "\n"
    config_tmp = config_path.with_name(f".{config_path.name}.tmp")
    manifest_tmp = manifest_path.with_name(f".{manifest_path.name}.tmp")
    try:
        config_tmp.write_text(rewritten_config, encoding="utf-8")
        manifest_tmp.write_text(manifest_text, encoding="utf-8")
        config_tmp.replace(config_path)
        manifest_tmp.replace(manifest_path)
    finally:
        config_tmp.unlink(missing_ok=True)
        manifest_tmp.unlink(missing_ok=True)
    return config_path, manifest_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--greia-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Greia checkout root (default: inferred from this tool)",
    )
    parser.add_argument("--parent-root", type=Path, required=True, help="reviewed Parent HTML checkout")
    parser.add_argument("--revision", required=True, help="exact reviewed Parent commit SHA")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        config, manifest = update_pin(args.greia_root, args.parent_root, args.revision)
    except PinError as exc:
        raise SystemExit(f"parent pin update refused: {exc}")
    print(f"updated {config}")
    print(f"updated {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
