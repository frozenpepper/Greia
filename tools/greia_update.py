#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import tomllib
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from greia_platform.system_updates import (  # noqa: E402
    BUNDLE_MEDIA_TYPE,
    MAX_BUNDLE_BYTES,
    SystemUpdateError,
    build_update_bundle,
    inspect_update_bundle,
)


@dataclass(frozen=True, slots=True)
class UpdateTarget:
    platform_family: str
    architecture: str
    profile: str


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create, inspect and push unsigned Greia .greiaupdate v3 bundles."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build", help="build one unsigned .greiaupdate v3 bundle")
    build.add_argument("--payload", type=Path, required=True)
    build.add_argument(
        "--profile-file",
        type=Path,
        help="Greia build profile TOML; derives profile/family/architecture",
    )
    build.add_argument("--platform-family")
    build.add_argument("--architecture")
    build.add_argument("--profile")
    build.add_argument("--board", default=None)
    build.add_argument("--version", required=True)
    build.add_argument("--hardware-support", type=Path, default=None)
    build.add_argument("--payload-uncompressed-bytes", type=int, required=True)
    build.add_argument("--minimum-slot-bytes", type=int, default=None)
    build.add_argument("--persist-read-min", type=int, required=True)
    build.add_argument("--persist-read-max", type=int, required=True)
    build.add_argument("--persist-write", type=int, required=True)
    build.add_argument(
        "--release-id",
        help="stable release identifier; defaults to greia-<version>",
    )
    build.add_argument(
        "--output",
        type=Path,
        help="output path; defaults to out/greia-<version>-<profile>.greiaupdate",
    )
    build.add_argument("--release-notes", default="")
    build.add_argument("--release-notes-file", type=Path)

    inspect = sub.add_parser("inspect", help="inspect a v3 bundle")
    inspect.add_argument("bundle", type=Path)

    push = sub.add_parser("push", help="upload a bundle through the Greia Parent API")
    push.add_argument("bundle", type=Path)
    push.add_argument("--url", default="http://greia.local:8766")
    auth = push.add_mutually_exclusive_group(required=True)
    auth.add_argument("--bearer", help="paired Parent bearer credential")
    auth.add_argument(
        "--legacy-token",
        help="development-only existing Parent pairing token (X-Pip-Token)",
    )
    push.add_argument("--timeout", type=float, default=300.0)

    status = sub.add_parser("status", help="read Greia system-update status")
    status.add_argument("--url", default="http://greia.local:8766")
    auth_status = status.add_mutually_exclusive_group(required=True)
    auth_status.add_argument("--bearer")
    auth_status.add_argument("--legacy-token")
    status.add_argument("--timeout", type=float, default=20.0)

    return parser


def _release_notes(args: argparse.Namespace) -> str:
    if args.release_notes_file is not None:
        if args.release_notes:
            raise SystemUpdateError(
                "use only one of --release-notes or --release-notes-file"
            )
        try:
            return args.release_notes_file.read_text(encoding="utf-8").strip()
        except (OSError, UnicodeDecodeError) as exc:
            raise SystemUpdateError(f"unable to read release notes: {exc}") from exc
    return args.release_notes


def _target_from_profile_file(path: Path) -> UpdateTarget:
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise SystemUpdateError(f"unable to read Greia build profile: {exc}") from exc
    try:
        profile = raw["profile"]["id"]
        platform_family = raw["platform"]["family"]
        architecture = raw["base"]["architecture"]
    except (KeyError, TypeError) as exc:
        raise SystemUpdateError(
            "build profile must define profile.id, platform.family and base.architecture"
        ) from exc
    if not all(isinstance(value, str) and value for value in (profile, platform_family, architecture)):
        raise SystemUpdateError("build profile update identity fields must be non-empty text")
    return UpdateTarget(platform_family, architecture, profile)


def _resolve_target(args: argparse.Namespace) -> UpdateTarget:
    explicit = (args.platform_family, args.architecture, args.profile)
    if args.profile_file is not None:
        if any(value is not None for value in explicit):
            raise SystemUpdateError(
                "use --profile-file or explicit --platform-family/--architecture/--profile, not both"
            )
        return _target_from_profile_file(args.profile_file)
    if not all(isinstance(value, str) and value for value in explicit):
        raise SystemUpdateError(
            "build requires --profile-file or all of --platform-family, --architecture and --profile"
        )
    return UpdateTarget(args.platform_family, args.architecture, args.profile)


def _build_output(args: argparse.Namespace, target: UpdateTarget) -> Path:
    if args.output is not None:
        return args.output
    return PROJECT_ROOT / "out" / f"greia-{args.version}-{target.profile}.greiaupdate"


def _auth_headers(args: argparse.Namespace) -> dict[str, str]:
    if getattr(args, "bearer", None):
        return {"Authorization": f"Bearer {args.bearer}"}
    return {"X-Pip-Token": str(args.legacy_token)}


def _base_url(value: str) -> str:
    value = value.strip().rstrip("/")
    if not value.startswith(("http://", "https://")):
        raise SystemUpdateError("--url must begin with http:// or https://")
    return value


def _json_request(request: urllib.request.Request, timeout: float) -> object:
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemUpdateError(f"Parent API rejected request ({exc.code}): {body}") from exc
    except urllib.error.URLError as exc:
        raise SystemUpdateError(f"unable to reach Greia Parent API: {exc.reason}") from exc
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SystemUpdateError("Parent API returned invalid JSON") from exc


def _push(args: argparse.Namespace) -> object:
    bundle = args.bundle.resolve()
    inspected = inspect_update_bundle(bundle)
    size = bundle.stat().st_size
    if size > MAX_BUNDLE_BYTES:
        raise SystemUpdateError("bundle exceeds Greia upload bound")
    url = _base_url(args.url) + "/api/v1/system/update/bundle"
    headers = {
        **_auth_headers(args),
        "Content-Type": BUNDLE_MEDIA_TYPE,
        "Content-Length": str(size),
        "X-Greia-Update-Release": inspected.manifest.release_id,
    }
    # Stream the potentially large artifact without loading it into RAM.
    import http.client
    from urllib.parse import urlsplit

    parts = urlsplit(url)
    if not parts.hostname:
        raise SystemUpdateError("--url must include a host")
    connection_cls = (
        http.client.HTTPSConnection if parts.scheme == "https" else http.client.HTTPConnection
    )
    connection = connection_cls(parts.hostname, parts.port, timeout=args.timeout)
    target = parts.path + (("?" + parts.query) if parts.query else "")
    try:
        connection.putrequest("POST", target)
        for name, value in headers.items():
            connection.putheader(name, value)
        connection.endheaders()
        with bundle.open("rb") as handle:
            while True:
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    break
                connection.send(chunk)
        response = connection.getresponse()
        raw = response.read()
        if response.status < 200 or response.status >= 300:
            body = raw.decode("utf-8", errors="replace")
            raise SystemUpdateError(
                f"Parent API rejected upload ({response.status}): {body}"
            )
    except OSError as exc:
        raise SystemUpdateError(f"update upload failed: {exc}") from exc
    finally:
        connection.close()
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SystemUpdateError("Parent API returned invalid JSON") from exc


def _status(args: argparse.Namespace) -> object:
    request = urllib.request.Request(
        _base_url(args.url) + "/api/v1/system/update",
        headers=_auth_headers(args),
        method="GET",
    )
    return _json_request(request, args.timeout)


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "build":
            target = _resolve_target(args)
            output = _build_output(args, target)
            release_id = args.release_id or f"greia-{args.version}"
            build_update_bundle(
                payload_path=args.payload,
                hardware_support_path=args.hardware_support,
                output_path=output,
                version=args.version,
                release_id=release_id,
                platform_family=target.platform_family,
                architecture=target.architecture,
                profile=target.profile,
                board=args.board,
                payload_uncompressed_bytes=args.payload_uncompressed_bytes,
                minimum_slot_bytes=args.minimum_slot_bytes,
                persist_read_schema_min=args.persist_read_min,
                persist_read_schema_max=args.persist_read_max,
                persist_write_schema=args.persist_write,
                release_notes=_release_notes(args),
            )
            inspected = inspect_update_bundle(output)
            payload = inspected.as_json_dict()
            payload["output"] = str(output)
            print(json.dumps(payload, indent=2, ensure_ascii=False))
            return 0
        if args.command == "inspect":
            payload = inspect_update_bundle(args.bundle).as_json_dict()
            print(json.dumps(payload, indent=2, ensure_ascii=False))
            return 0
        if args.command == "push":
            print(json.dumps(_push(args), indent=2, ensure_ascii=False))
            return 0
        if args.command == "status":
            print(json.dumps(_status(args), indent=2, ensure_ascii=False))
            return 0
    except (SystemUpdateError, OSError) as exc:
        print(f"greia-update: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
