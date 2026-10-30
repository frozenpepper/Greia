#!/usr/bin/env python3
"""Synchronize Greia's frozen Parent HTML client from the in-repo ``parent-app/``.

``parent-app/`` is the single editable source of the browser Parent client.
The installed image ships only a frozen, integrity-checked copy of its runtime
closure, so after committing changes to ``parent-app/`` run this tool and
commit its output.

The pin ``revision`` is the 40-hex Git **tree id of the committed
``parent-app/`` directory** (``git rev-parse HEAD:parent-app``). It names the
exact reviewed source without needing a separate repository, and keeps the
40-character format that ``greia_parent.parent_client_integrity`` and the pin/
manifest equality check rely on.

The tool refuses to run unless ``parent-app/`` has no uncommitted or untracked
changes. Runtime files are discovered from the actual ``index.html`` dependency
graph and read **from Git objects at ``HEAD:parent-app``** (never the working
tree), each exactly once. Those exact bytes own all three Greia artifacts:

- ``runtime/parent-app-client.toml``
- ``runtime/parent-app-client.manifest.json``
- ``build/overlay/usr/share/greia-parent-app/``

All replacement artifacts are staged before any current artifact is moved.
Replacement then uses sibling backups so a failed multi-path swap can restore
the previous checkout state instead of leaving a half-repinned tree.

``--check`` computes the same result and reports drift without writing.
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
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit


PARENT_APP_DIR = "parent-app"
PIN_REPOSITORY = "frozenpepper/Greia:parent-app"
REVISION_LINE = re.compile(r'^revision = "[0-9a-f]{40}"$', re.MULTILINE)
REPOSITORY_LINE = re.compile(r'^repository = "[^"\n]*"$', re.MULTILINE)
_REGULAR_FILE_MODES = frozenset({"100644", "100755"})
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


def _git(greia_root: Path, *args: str) -> bytes:
    """Run one Git command (argument array, no shell) and return raw stdout."""

    try:
        completed = subprocess.run(
            ["git", "-C", str(greia_root), *args],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.decode("utf-8", "replace").strip() or str(exc)
        raise PinError(f"could not inspect Greia checkout: {detail}") from exc
    except OSError as exc:
        raise PinError(f"could not inspect Greia checkout: {exc}") from exc
    return completed.stdout


def _committed_tree_id(greia_root: Path) -> str:
    """Return the tree id of ``HEAD:parent-app`` after requiring it to be clean."""

    dirty = _git(
        greia_root, "status", "--porcelain", "--untracked-files=all", "--", PARENT_APP_DIR
    ).decode("utf-8", "replace").strip()
    if dirty:
        raise PinError(
            "parent-app/ has uncommitted or untracked changes; "
            "commit them before pinning (the pin names the committed tree)"
        )
    tree = _git(greia_root, "rev-parse", "--verify", f"HEAD:{PARENT_APP_DIR}").decode("ascii").strip()
    if not re.fullmatch(r"[0-9a-f]{40}", tree):
        raise PinError(f"unexpected tree id for HEAD:{PARENT_APP_DIR}: {tree!r}")
    return tree


def _tree_blobs(greia_root: Path, tree: str) -> dict[str, str]:
    """Map every regular file in the tree to its blob id (symlinks/submodules refused)."""

    listing = _git(greia_root, "ls-tree", "-r", "-z", tree)
    blobs: dict[str, str] = {}
    for record in listing.split(b"\0"):
        if not record:
            continue
        meta, _, raw_path = record.partition(b"\t")
        mode, kind, oid = meta.decode("ascii").split()
        path = raw_path.decode("utf-8", "surrogateescape")
        if kind != "blob" or mode not in _REGULAR_FILE_MODES:
            raise PinError(f"parent-app/{path} is not a regular file (mode {mode})")
        blobs[path] = oid
    return blobs


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


def _discover_runtime_payloads(greia_root: Path, tree: str) -> dict[str, bytes]:
    """Capture the exact transitive runtime closure rooted at ``index.html``.

    Bytes come from the committed Git objects of ``tree``, not the working tree.
    """

    blobs = _tree_blobs(greia_root, tree)
    pending = [PurePosixPath("index.html")]
    payloads: dict[str, bytes] = {}
    while pending:
        relative = pending.pop()
        key = relative.as_posix()
        if key in payloads:
            continue
        oid = blobs.get(key)
        if oid is None:
            raise PinError(f"referenced Parent runtime file is missing: {relative}")
        data = _git(greia_root, "cat-file", "blob", oid)
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
    if len(REVISION_LINE.findall(config)) != 1:
        raise PinError("Parent pin config must contain exactly one exact revision line")
    if len(REPOSITORY_LINE.findall(config)) != 1:
        raise PinError("Parent pin config must contain exactly one repository line")
    config = REPOSITORY_LINE.sub(f'repository = "{PIN_REPOSITORY}"', config, count=1)
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


@dataclass(frozen=True)
class _Plan:
    """The complete repin result computed from one committed ``parent-app`` tree."""

    config_path: Path
    manifest_path: Path
    overlay_path: Path
    tree: str
    payloads: dict[str, bytes]
    manifest_text: str
    config_text: str

    @classmethod
    def compute(cls, greia_root: Path) -> "_Plan":
        config_path = greia_root / "runtime" / "parent-app-client.toml"
        manifest_path = greia_root / "runtime" / "parent-app-client.manifest.json"
        overlay_path = greia_root / "build" / "overlay" / "usr" / "share" / "greia-parent-app"
        tree = _committed_tree_id(greia_root)
        _load_manifest_metadata(manifest_path)  # refuse to overwrite a foreign/corrupt manifest
        payloads = _discover_runtime_payloads(greia_root, tree)
        manifest = {
            "files": _hash_runtime_payloads(payloads),
            "repository": PIN_REPOSITORY,
            "revision": tree,
            "schema_version": 1,
        }
        return cls(
            config_path=config_path,
            manifest_path=manifest_path,
            overlay_path=overlay_path,
            tree=tree,
            payloads=payloads,
            manifest_text=json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
            config_text=_updated_config_text(config_path, tree),
        )


def update_pin(greia_root: Path) -> tuple[Path, Path, Path]:
    """Rewrite pin, manifest and image overlay from the committed ``parent-app/``."""

    greia_root = greia_root.resolve()
    plan = _Plan.compute(greia_root)

    staged: list[tuple[Path, Path]] = []
    try:
        staged.append((plan.config_path, _stage_text_file(plan.config_path, plan.config_text)))
        staged.append((plan.manifest_path, _stage_text_file(plan.manifest_path, plan.manifest_text)))
        staged.append((plan.overlay_path, _stage_runtime_tree(plan.overlay_path, plan.payloads)))
        # Refuse the swap if parent-app/ moved or became dirty while its
        # dependency graph/bytes were being captured.
        if _committed_tree_id(greia_root) != plan.tree:
            raise PinError("parent-app/ changed while the pin was being computed")
        _commit_replacements(staged)
    except Exception:
        for _target, temporary in staged:
            _remove_path(temporary)
        raise

    return plan.config_path, plan.manifest_path, plan.overlay_path


def _overlay_files(root: Path) -> dict[str, bytes]:
    if not root.is_dir() or root.is_symlink():
        return {}
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def check_pin(greia_root: Path) -> list[str]:
    """Return human-readable drift between the committed tree and the pinned artifacts."""

    greia_root = greia_root.resolve()
    plan = _Plan.compute(greia_root)
    problems: list[str] = []
    try:
        current_config = plan.config_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise PinError(f"could not read Parent pin config: {exc}") from exc
    if current_config != plan.config_text:
        problems.append(f"{plan.config_path.name} does not name tree {plan.tree}")
    try:
        current_manifest = plan.manifest_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise PinError(f"could not read Parent manifest: {exc}") from exc
    if current_manifest != plan.manifest_text:
        problems.append(f"{plan.manifest_path.name} does not match the committed runtime files")
    overlay = _overlay_files(plan.overlay_path)
    for relative in sorted(set(plan.payloads) | set(overlay)):
        if relative not in overlay:
            problems.append(f"overlay is missing {relative}")
        elif relative not in plan.payloads:
            problems.append(f"overlay has unexpected file {relative}")
        elif overlay[relative] != plan.payloads[relative]:
            problems.append(f"overlay differs from committed parent-app/{relative}")
    return problems


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--greia-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Greia checkout root (default: inferred from this tool)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="report drift between committed parent-app/ and the pin/manifest/overlay; write nothing",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.check:
            problems = check_pin(args.greia_root)
            if problems:
                for problem in problems:
                    print(f"drift: {problem}")
                print("run tools/update_parent_client_pin.py after committing parent-app/")
                return 1
            print("Parent client pin, manifest and overlay match the committed parent-app/")
            return 0
        config, manifest, overlay = update_pin(args.greia_root)
    except PinError as exc:
        raise SystemExit(f"parent pin update refused: {exc}")
    print(f"updated {config}")
    print(f"updated {manifest}")
    print(f"synchronized {overlay}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
