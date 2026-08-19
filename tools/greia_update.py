#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import urllib.error
import urllib.request
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
    generate_ed25519_keypair,
    inspect_update_bundle,
    verify_update_signature,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create, inspect and push signed Greia .greiaupdate bundles."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    keygen = sub.add_parser("keygen", help="create an Ed25519 release signing keypair")
    keygen.add_argument("--private-key", type=Path, required=True)
    keygen.add_argument("--public-key", type=Path, required=True)

    build = sub.add_parser("build", help="build and sign one .greiaupdate bundle")
    build.add_argument("--payload", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--version", required=True)
    build.add_argument("--release-id", required=True)
    build.add_argument("--platform-family", required=True)
    build.add_argument("--architecture", required=True)
    build.add_argument("--profile", required=True)
    build.add_argument("--signer", required=True)
    build.add_argument("--private-key", type=Path, required=True)
    build.add_argument("--release-notes", default="")
    build.add_argument("--release-notes-file", type=Path)

    inspect = sub.add_parser("inspect", help="inspect and optionally verify a bundle")
    inspect.add_argument("bundle", type=Path)
    inspect.add_argument("--public-key", type=Path)

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


def _verify_with_single_key(bundle_path: Path, public_key: Path) -> dict[str, object]:
    inspected = inspect_update_bundle(bundle_path)
    with tempfile.TemporaryDirectory(prefix="greia-update-key-") as directory:
        key_dir = Path(directory)
        trusted = key_dir / f"{inspected.manifest.signer}.pem"
        shutil.copyfile(public_key, trusted)
        verify_update_signature(inspected, key_dir)
    payload = inspected.as_json_dict()
    payload["signature_verified"] = True
    return payload


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
    # urllib accepts a file-like object poorly for fixed-length PUT/POST across
    # Python versions. The tool intentionally uses a bounded in-memory body only
    # for small bundles and streams large artifacts with HTTPConnection below.
    # Keeping this implementation dependency-free matters on operator Macs.
    import http.client
    from urllib.parse import urlsplit

    parts = urlsplit(url)
    connection_cls = http.client.HTTPSConnection if parts.scheme == "https" else http.client.HTTPConnection
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
        if args.command == "keygen":
            generate_ed25519_keypair(args.private_key, args.public_key)
            print(json.dumps({
                "private_key": str(args.private_key),
                "public_key": str(args.public_key),
            }, indent=2))
            return 0
        if args.command == "build":
            manifest = build_update_bundle(
                payload_path=args.payload,
                output_path=args.output,
                version=args.version,
                release_id=args.release_id,
                platform_family=args.platform_family,
                architecture=args.architecture,
                profile=args.profile,
                signer=args.signer,
                private_key_path=args.private_key,
                release_notes=_release_notes(args),
            )
            inspected = inspect_update_bundle(args.output)
            payload = inspected.as_json_dict()
            payload["output"] = str(args.output)
            print(json.dumps(payload, indent=2, ensure_ascii=False))
            return 0
        if args.command == "inspect":
            payload = (
                _verify_with_single_key(args.bundle, args.public_key)
                if args.public_key is not None
                else inspect_update_bundle(args.bundle).as_json_dict()
            )
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
