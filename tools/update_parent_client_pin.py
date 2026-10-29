#!/usr/bin/env python3
"""Synchronize Greia's frozen Parent HTML client from a reviewed checkout.

The caller supplies a clean Parent checkout and the exact commit SHA that was
reviewed/tested. Runtime files are discovered from the actual ``index.html``
dependency graph and each runtime file is read once. Those exact captured bytes
own all four Greia artifacts:

- ``runtime/parent-app-client.toml``
- ``runtime/parent-app-client.manifest.json``
- ``vendor/parent-app/``
- ``build/overlay/usr/share/greia-parent-app/``

All replacement artifacts are staged before any current artifact is moved.
Replacement then uses sibling backups so a failed multi-path swap can restore
the previous checkout state instead of leaving a half-repinned tree.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import uuid
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


def _discover_runtime_payloads(parent_root: Path) -> dict[str, bytes]:
    """Capture the exact transitive runtime closure rooted at ``index.html``."""

    checkout = parent_root.resolve()
    pending = [PurePosixPath("index.html")]
    payloads: dict[str, bytes] = {}
    while pending:
        relative = pending.pop()
        key = relative.as_posix()
        if key in payloads:
            continue
        path = (checkout / Path(*relative.parts)).resolve()
        try:
            path.relative_to(checkout)
        except ValueError as exc:
            raise PinError(f"runtime file escapes Parent checkout: {relative}") from exc
        if not path.is_file():
            raise PinError(f"referenced Parent runtime file is missing: {relative}")
        data = path.read_bytes()
        payloads[key] = data
        for dependency in _references_for(relative, data):
            if dependency.as_posix() not in payloads:
                pending.append(dependency)
    return dict(sorted(payloads.items()))


def _hash_runtime_payloads(payloads: dict[str, bytes]) -> dict[str, dict[str, object]]:
    return {
        relative: {
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }
        for relative, data in sorted(payloads.items())
    }


def _updated_config_text(config_path: Path, revision: str) -> str:
    try:
        config = config_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise PinError(f"could not read Parent pin config: {exc}") from exc
    matches = REVISION_LINE.findall(config)
    if len(matches) != 1:
        raise PinError("Parent pin config must contain exactly one exact revision line")
    return REVISION_LINE.sub(f'revision = "{revision}"', config, count=1)


def _stage_text_file(target: Path, content: str) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    mode = 0o644
    if target.exists() and not target.is_symlink():
        mode = target.stat().st_mode & 0o777
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.pin-",
        suffix=".tmp",
        dir=target.parent,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            handle.write(content)
        temporary.chmod(mode)
    except Exception:
        try:
            os.close(descriptor)
        except OSError:
            pass
        temporary.unlink(missing_ok=True)
        raise
    return temporary


def _stage_runtime_tree(target: Path, payloads: dict[str, bytes]) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{target.name}.pin-", dir=target.parent))
    try:
        for relative, data in sorted(payloads.items()):
            destination = temporary / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
            destination.chmod(0o644)
        # mkdtemp creates 0700 regardless of umask. This tree becomes an
        # image overlay served by greiapanel, so every directory must be
        # traversable by that non-root identity even under a restrictive umask.
        temporary.chmod(0o755)
        for directory in temporary.rglob("*"):
            if directory.is_dir():
                directory.chmod(0o755)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return temporary


def _remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink(missing_ok=True)
    elif path.exists():
        shutil.rmtree(path)


def _commit_replacements(staged: list[tuple[Path, Path]]) -> None:
    """Install all staged paths with rollback to the prior checkout on failure."""

    replacements: list[tuple[Path, Path | None]] = []
    try:
        for target, temporary in staged:
            backup: Path | None = None
            if target.exists() or target.is_symlink():
                backup = target.with_name(f".{target.name}.backup-{uuid.uuid4().hex}")
                target.replace(backup)
            replacements.append((target, backup))
            temporary.replace(target)
    except Exception as exc:
        rollback_errors: list[str] = []
        for target, backup in reversed(replacements):
            try:
                _remove_path(target)
                if backup is not None and (backup.exists() or backup.is_symlink()):
                    backup.replace(target)
            except Exception as rollback_exc:  # pragma: no cover - catastrophic filesystem failure
                rollback_errors.append(f"{target}: {rollback_exc}")
        detail = ""
        if rollback_errors:
            detail = f"; rollback also failed: {'; '.join(rollback_errors)}"
        raise PinError(f"could not synchronize Parent runtime artifacts: {exc}{detail}") from exc
    else:
        for _target, backup in replacements:
            if backup is not None:
                _remove_path(backup)
    finally:
        for _target, temporary in staged:
            _remove_path(temporary)


def update_pin(greia_root: Path, parent_root: Path, revision: str) -> tuple[Path, Path, Path, Path]:
    greia_root = greia_root.resolve()
    parent_root = parent_root.resolve()
    _validate_parent_checkout(parent_root, revision)

    config_path = greia_root / "runtime" / "parent-app-client.toml"
    manifest_path = greia_root / "runtime" / "parent-app-client.manifest.json"
    vendor_path = greia_root / "vendor" / "parent-app"
    overlay_path = greia_root / "build" / "overlay" / "usr" / "share" / "greia-parent-app"

    manifest = _load_manifest_metadata(manifest_path)
    payloads = _discover_runtime_payloads(parent_root)
    hashed = _hash_runtime_payloads(payloads)
    rewritten_manifest = {
        "files": hashed,
        "repository": manifest.get("repository", "frozenpepper/Greia-Parent-App-Html"),
        "revision": revision,
        "schema_version": 1,
    }
    manifest_text = json.dumps(rewritten_manifest, indent=2, ensure_ascii=False) + "\n"
    config_text = _updated_config_text(config_path, revision)

    staged: list[tuple[Path, Path]] = []
    try:
        staged.append((config_path, _stage_text_file(config_path, config_text)))
        staged.append((manifest_path, _stage_text_file(manifest_path, manifest_text)))
        staged.append((vendor_path, _stage_runtime_tree(vendor_path, payloads)))
        staged.append((overlay_path, _stage_runtime_tree(overlay_path, payloads)))
        # Refuse the swap if the reviewed checkout moved or became dirty while
        # its dependency graph/bytes were being captured.
        _validate_parent_checkout(parent_root, revision)
        _commit_replacements(staged)
    except Exception:
        for _target, temporary in staged:
            _remove_path(temporary)
        raise

    return config_path, manifest_path, vendor_path, overlay_path


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
        config, manifest, vendor, overlay = update_pin(args.greia_root, args.parent_root, args.revision)
    except PinError as exc:
        raise SystemExit(f"parent pin update refused: {exc}")
    print(f"updated {config}")
    print(f"updated {manifest}")
    print(f"synchronized {vendor}")
    print(f"synchronized {overlay}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
