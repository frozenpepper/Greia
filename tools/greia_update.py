#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
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

from greia_platform.payload_receipt import (  # noqa: E402
    PAYLOAD_RECEIPT_SCHEMA_VERSION,
)
from greia_platform.system_updates import (  # noqa: E402
    BUNDLE_MEDIA_TYPE,
    MAX_BUNDLE_BYTES,
    MAX_PAYLOAD_BYTES,
    SystemUpdateError,
    build_update_bundle,
    inspect_update_bundle,
)
from greia_installer.hardware_support import (  # noqa: E402
    HardwareSupportPoolError,
    support_installed_size_bound,
)
from greia_installer.layout import (  # noqa: E402
    LayoutError,
    require_finalized_slot_capacity,
)
from greia_platform.slot_writer import (  # noqa: E402
    FINALIZATION_GROWTH_BYTES,
    SLOT_METADATA_RESERVE_BYTES,
)


@dataclass(frozen=True, slots=True)
class UpdateTarget:
    platform_family: str
    architecture: str
    profile: str
    board: str | None = None
    system_slot_bytes: int | None = None


# Payload receipt contract (R4-G-RECEIPT, R4-G3-RECEIPT-HARDENING). The
# schema version constant lives in ``greia_platform.payload_receipt``
# (single owner, imported above); the shape/field contract mirrors the
# producer side in ``tools/build_release.py``:
# schema_version, payload_sha256, payload_compressed_bytes,
# payload_uncompressed_bytes, minimum_slot_bytes, profile_id, release_id.
# Field names are stable for Session 03 release CLI work.
_RECEIPT_MAX_BYTES = 64 * 1024
_HASH_CHUNK_BYTES = 64 * 1024
_DECOMPRESS_TIMEOUT_SECONDS = 600.0
_ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"


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
        help="Greia build profile TOML; derives profile/family/architecture/board/slot-size",
    )
    build.add_argument(
        "--platform-family",
        help="DEVELOPER-ONLY low-level seam: explicit identity without a profile file (no slot bound, no normal production use)",
    )
    build.add_argument(
        "--architecture",
        help="DEVELOPER-ONLY low-level seam: explicit identity without a profile file (no slot bound, no normal production use)",
    )
    build.add_argument(
        "--profile",
        help="DEVELOPER-ONLY low-level seam: explicit identity without a profile file (no slot bound, no normal production use)",
    )
    build.add_argument(
        "--board",
        default=None,
        help="DEVELOPER-ONLY low-level seam: explicit identity without a profile file (no slot bound, no normal production use)",
    )
    build.add_argument("--version", required=True)
    build.add_argument("--hardware-support", type=Path, default=None)
    build.add_argument(
        "--payload-uncompressed-bytes",
        type=int,
        default=None,
        help=(
            "DEVELOPER-ONLY low-level seam: manually typed size without artifact "
            "verification; refused unless --payload-receipt or "
            "--developer-allow-unverified-payload-facts is given"
        ),
    )
    build.add_argument(
        "--minimum-slot-bytes",
        type=int,
        default=None,
        help=(
            "DEVELOPER-ONLY low-level seam: manually typed size without artifact "
            "verification; refused unless --payload-receipt or "
            "--developer-allow-unverified-payload-facts is given"
        ),
    )
    build.add_argument(
        "--payload-receipt",
        type=Path,
        default=None,
        help=(
            "Machine-readable payload receipt JSON from "
            "build-payload --receipt-output; profile-based builds derive "
            "size facts from it and verify it against the payload artifact."
        ),
    )
    build.add_argument(
        "--developer-allow-unverified-payload-facts",
        action="store_true",
        help=(
            "DEVELOPER-ONLY: allow manually typed --payload-uncompressed-bytes "
            "without artifact verification (tiny test fixtures, low-level "
            "developer builds). Never used by normal profile-based production."
        ),
    )
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
    push.add_argument("--bearer", required=True, help="paired Parent bearer credential")
    push.add_argument("--timeout", type=float, default=300.0)

    status = sub.add_parser("status", help="read Greia system-update status")
    status.add_argument("--url", default="http://greia.local:8766")
    status.add_argument("--bearer", required=True, help="paired Parent bearer credential")
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
        board_raw = raw["platform"]["board"]
        slot_bytes = raw["storage"]["system_slot_bytes"]
    except (KeyError, TypeError) as exc:
        raise SystemUpdateError(
            "build profile must define profile.id, platform.family, base.architecture, "
            "platform.board and storage.system_slot_bytes"
        ) from exc
    if not all(isinstance(value, str) and value for value in (profile, platform_family, architecture)):
        raise SystemUpdateError("build profile update identity fields must be non-empty text")
    if not isinstance(board_raw, str) or not board_raw:
        raise SystemUpdateError("build profile platform.board must be non-empty text")
    board = None if board_raw == "none" else board_raw
    if isinstance(slot_bytes, bool) or not isinstance(slot_bytes, int) or slot_bytes <= 0:
        raise SystemUpdateError("build profile storage.system_slot_bytes must be a positive integer")
    return UpdateTarget(platform_family, architecture, profile, board, slot_bytes)


def _resolve_target(args: argparse.Namespace) -> UpdateTarget:
    explicit = (args.platform_family, args.architecture, args.profile)
    board_explicit = getattr(args, "board", None)
    if args.profile_file is not None:
        if any(value is not None for value in explicit) or board_explicit is not None:
            raise SystemUpdateError(
                "use --profile-file or explicit --platform-family/--architecture/--profile/--board, not both"
            )
        return _target_from_profile_file(args.profile_file)
    if not all(isinstance(value, str) and value for value in explicit):
        raise SystemUpdateError(
            "build requires --profile-file or all of --platform-family, --architecture and --profile "
            "(explicit identity is a DEVELOPER-ONLY low-level seam, not normal production)"
        )
    return UpdateTarget(args.platform_family, args.architecture, args.profile, board_explicit, None)


def _support_installed_bytes(hardware_support: Path | None) -> int:
    """Return the verified support installed-size bound for the capacity proof.

    Absent support (no ``--hardware-support``) yields 0. Present support is
    inspected/verified through ``greia_installer.hardware_support`` and the
    bound is ``total_installed_bytes`` from verified pool metadata — never
    operator-entered values and never compressed ``.deb`` bytes. An
    unverifiable support artifact fails closed here, before any bundle byte
    is written.
    """
    try:
        return support_installed_size_bound(hardware_support)
    except HardwareSupportPoolError as exc:
        raise SystemUpdateError(
            f"hardware-support is not verifiable, refusing bundle: {exc}"
        ) from exc


def _sha256_file(path: Path) -> str:
    """Hash a file with bounded RAM (chunked reads, never ``read_bytes``)."""
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while True:
                chunk = handle.read(_HASH_CHUNK_BYTES)
                if not chunk:
                    break
                digest.update(chunk)
    except OSError as exc:
        raise SystemUpdateError(f"payload digest read failed: {exc}") from exc
    return digest.hexdigest()


def _measured_uncompressed_bytes(payload: Path) -> int:
    """Return the real decompressed byte length of a zstd payload artifact.

    Streams ``zstd -d -c`` stdout and counts bytes in bounded chunks (never
    the whole payload in RAM, no mounts). Falls back to the ``zstandard``
    module when the ``zstd`` binary is unavailable. Any decompression
    failure, bound violation, or missing tooling refuses fail-closed.
    """
    path = Path(payload)
    if path.is_symlink() or not path.is_file():
        raise SystemUpdateError("payload is not a regular file")
    try:
        compressed_size = path.stat().st_size
    except OSError as exc:
        raise SystemUpdateError(f"payload is unreadable: {exc}") from exc
    if compressed_size <= 0 or compressed_size > MAX_PAYLOAD_BYTES:
        raise SystemUpdateError("payload size is outside Greia bounds")
    try:
        with path.open("rb") as handle:
            magic = handle.read(len(_ZSTD_MAGIC))
    except OSError as exc:
        raise SystemUpdateError(f"payload is unreadable: {exc}") from exc
    if magic != _ZSTD_MAGIC:
        raise SystemUpdateError(
            "payload receipt verification refused: "
            "payload is not zstd-compressed bytes"
        )
    zstd = shutil.which("zstd")
    total = 0
    if zstd is not None:
        try:
            proc = subprocess.Popen(
                [zstd, "-d", "-c", "--", str(path)],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False,
            )
        except OSError as exc:
            raise SystemUpdateError(
                f"payload receipt verification is unavailable: {exc}"
            ) from exc
        try:
            assert proc.stdout is not None
            while True:
                chunk = proc.stdout.read(_HASH_CHUNK_BYTES)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_PAYLOAD_BYTES:
                    proc.kill()
                    try:
                        proc.wait(timeout=30)
                    except (OSError, subprocess.SubprocessError):
                        pass
                    raise SystemUpdateError(
                        "payload receipt verification refused: "
                        "decompressed payload is outside Greia bounds"
                    )
            _, _stderr = proc.communicate(timeout=_DECOMPRESS_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired as exc:
            proc.kill()
            try:
                proc.wait(timeout=30)
            except (OSError, subprocess.SubprocessError):
                pass
            raise SystemUpdateError(
                "payload receipt verification timed out, refusing bundle"
            ) from exc
        except SystemUpdateError:
            raise
        except (OSError, subprocess.SubprocessError) as exc:
            raise SystemUpdateError(
                f"payload receipt verification failed: {exc}"
            ) from exc
        if proc.returncode != 0:
            raise SystemUpdateError(
                "payload receipt verification refused: "
                "payload does not decompress as zstd"
            )
        return total
    try:
        import zstandard
    except ImportError as exc:
        raise SystemUpdateError(
            "payload receipt verification is unavailable: "
            "neither zstd nor the zstandard module is present"
        ) from exc
    try:
        with path.open("rb") as handle:
            stream = zstandard.ZstdDecompressor().stream_reader(handle)
            try:
                while True:
                    chunk = stream.read(_HASH_CHUNK_BYTES)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > MAX_PAYLOAD_BYTES:
                        raise SystemUpdateError(
                            "payload receipt verification refused: "
                            "decompressed payload is outside Greia bounds"
                        )
            finally:
                try:
                    stream.close()
                except (OSError, ValueError):
                    pass
    except SystemUpdateError:
        raise
    except Exception as exc:
        raise SystemUpdateError(
            "payload receipt verification refused: "
            f"payload does not decompress as zstd ({exc})"
        ) from exc
    return total


def _load_payload_receipt(path: Path) -> dict[str, object]:
    """Load and shape-validate a payload receipt JSON document."""
    receipt_path = Path(path)
    if receipt_path.is_symlink() or not receipt_path.is_file():
        raise SystemUpdateError("payload receipt is not a regular file")
    try:
        if receipt_path.stat().st_size <= 0 or receipt_path.stat().st_size > _RECEIPT_MAX_BYTES:
            raise SystemUpdateError("payload receipt size is outside Greia bounds")
    except OSError as exc:
        raise SystemUpdateError(f"payload receipt is unreadable: {exc}") from exc
    try:
        raw = receipt_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise SystemUpdateError(f"payload receipt is unreadable: {exc}") from exc
    try:
        document = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemUpdateError(
            f"payload receipt is not valid JSON: {exc}"
        ) from exc
    if not isinstance(document, dict):
        raise SystemUpdateError("payload receipt must be a JSON object")
    if document.get("schema_version") != PAYLOAD_RECEIPT_SCHEMA_VERSION:
        raise SystemUpdateError(
            "payload receipt schema_version is unsupported, refusing bundle"
        )
    for field in (
        "payload_sha256",
        "payload_compressed_bytes",
        "payload_uncompressed_bytes",
        "minimum_slot_bytes",
        "profile_id",
        "release_id",
    ):
        if field not in document:
            raise SystemUpdateError(
                f"payload receipt is missing {field!r}, refusing bundle"
            )
    return document


def _resolve_payload_facts(
    args: argparse.Namespace,
    target: UpdateTarget,
    *,
    release_id: str,
) -> tuple[int, int]:
    """Derive (base, minimum) size facts from the artifact, never bare typing.

    Both production paths (``--profile-file`` and explicit-identity) require
    ``--payload-receipt``: facts come from the receipt after it is verified
    against the real payload file (shape, profile/release identity, sha256,
    compressed size, decompressed length) in that order. A manually
    typed ``--payload-uncompressed-bytes``/``--minimum-slot-bytes`` alongside
    a receipt must equal the receipt facts, otherwise the build refuses
    (understated/mismatched facts). Without a receipt, both paths refuse
    unless the explicit developer-only seam
    ``--developer-allow-unverified-payload-facts`` is set with manually typed
    facts. The explicit-identity path (no profile file) is a DEVELOPER-ONLY
    low-level seam: it carries no profile slot bound and skips the capacity
    check, so it must never be usable as normal production.
    """
    payload_path = Path(args.payload)
    receipt_path = getattr(args, "payload_receipt", None)
    developer_unverified = bool(
        getattr(args, "developer_allow_unverified_payload_facts", False)
    )
    manual_base = getattr(args, "payload_uncompressed_bytes", None)
    manual_minimum = getattr(args, "minimum_slot_bytes", None)
    profile_based = target.system_slot_bytes is not None

    if receipt_path is not None:
        receipt = _load_payload_receipt(receipt_path)
        for field in ("payload_compressed_bytes", "payload_uncompressed_bytes", "minimum_slot_bytes"):
            value = receipt[field]
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise SystemUpdateError(
                    f"payload receipt {field!r} must be a positive integer, "
                    "refusing bundle"
                )
        for field in ("payload_sha256", "profile_id", "release_id"):
            value = receipt[field]
            if not isinstance(value, str) or not value:
                raise SystemUpdateError(
                    f"payload receipt {field!r} must be non-empty text, "
                    "refusing bundle"
                )
        receipt_base = int(receipt["payload_uncompressed_bytes"])
        receipt_minimum = int(receipt["minimum_slot_bytes"])
        if receipt_base > MAX_PAYLOAD_BYTES:
            raise SystemUpdateError(
                "payload receipt uncompressed size is outside Greia bounds, "
                "refusing bundle"
            )
        if receipt_minimum < receipt_base or receipt_minimum > MAX_BUNDLE_BYTES:
            raise SystemUpdateError(
                "payload receipt minimum_slot_bytes must cover the uncompressed "
                "image, refusing bundle"
            )
        if str(receipt["profile_id"]) != target.profile:
            raise SystemUpdateError(
                f"payload receipt profile {str(receipt['profile_id'])!r} does not match "
                f"build profile {target.profile!r}, refusing bundle"
            )
        if str(receipt["release_id"]) != release_id:
            raise SystemUpdateError(
                f"payload receipt release {str(receipt['release_id'])!r} does not match "
                f"build release {release_id!r}, refusing bundle"
            )
        actual_sha = _sha256_file(payload_path)
        if actual_sha != str(receipt["payload_sha256"]):
            raise SystemUpdateError(
                "payload receipt digest does not match the payload artifact, "
                "refusing bundle"
            )
        try:
            actual_compressed = payload_path.stat().st_size
        except OSError as exc:
            raise SystemUpdateError(f"payload is unreadable: {exc}") from exc
        if actual_compressed != int(receipt["payload_compressed_bytes"]):
            raise SystemUpdateError(
                "payload receipt compressed size does not match the payload "
                "artifact, refusing bundle"
            )
        measured = _measured_uncompressed_bytes(payload_path)
        if measured != receipt_base:
            raise SystemUpdateError(
                f"payload receipt uncompressed size ({receipt_base}) does not match "
                f"the payload artifact ({measured}), refusing bundle"
            )
        if manual_base is not None and manual_base != receipt_base:
            raise SystemUpdateError(
                f"manually typed --payload-uncompressed-bytes ({manual_base}) does not "
                f"match the payload receipt ({receipt_base}), refusing bundle"
            )
        if manual_minimum is not None and manual_minimum != receipt_minimum:
            raise SystemUpdateError(
                f"manually typed --minimum-slot-bytes ({manual_minimum}) does not "
                f"match the payload receipt ({receipt_minimum}), refusing bundle"
            )
        return receipt_base, receipt_minimum

    if profile_based:
        if not developer_unverified:
            raise SystemUpdateError(
                "profile-based build requires --payload-receipt deriving size facts "
                "from the payload artifact; manually typed "
                "--payload-uncompressed-bytes without artifact verification is "
                "refused (developer-only seam: "
                "--developer-allow-unverified-payload-facts)"
            )
        if manual_base is None:
            raise SystemUpdateError(
                "developer-only unverified build still requires "
                "--payload-uncompressed-bytes"
            )
        return manual_base, manual_minimum if manual_minimum is not None else manual_base

    if manual_base is None:
        raise SystemUpdateError(
            "explicit-identity (DEVELOPER-ONLY low-level seam) build requires "
            "--payload-receipt deriving size facts from the payload artifact; "
            "manually typed --payload-uncompressed-bytes without artifact "
            "verification is refused (developer-only seam: "
            "--developer-allow-unverified-payload-facts)"
        )
    if not developer_unverified:
        raise SystemUpdateError(
            "explicit-identity (DEVELOPER-ONLY low-level seam) build requires "
            "--payload-receipt deriving size facts from the payload artifact; "
            "manually typed --payload-uncompressed-bytes without artifact "
            "verification is refused (developer-only seam: "
            "--developer-allow-unverified-payload-facts)"
        )
    return manual_base, manual_minimum if manual_minimum is not None else manual_base


def _check_profile_capacity(
    target: UpdateTarget,
    *,
    payload_uncompressed_bytes: int,
    minimum_slot_bytes: int | None,
    hardware_support_path: Path | None = None,
) -> int | None:
    """Refuse bundles that cannot reach finalization inside the profile slot.

    The profile file is the single release-identity authority: its
    ``storage.system_slot_bytes`` bounds the destination slot. The decision
    is the single owned finalized-slot capacity calculation
    (``greia_installer.layout.require_finalized_slot_capacity`` — the same
    bound the installer plan gate and the runtime ``SlotWriter`` enforce)::

        max(base, minimum) + support installed-size bound
            + finalization growth + metadata/reserve <= slot capacity

    ``base`` is the receipt-derived uncompressed size (profile-based
    production) or a developer-allowed manually typed fact; the effective
    minimum is the receipt-derived minimum or the explicit
    ``--minimum-slot-bytes`` (which must equal the receipt when both are
    given) or the uncompressed size by default. The support bound comes only from verified hardware-support metadata
    (see :func:`_support_installed_bytes`); growth/reserve are the
    platform-owned bounds, never operator flags. Refusal happens before the
    output bundle is written. Explicit-identity builds carry no profile slot
    bound and skip this check (returns ``None``); otherwise returns the
    required finalized bytes.
    """
    if target.system_slot_bytes is None:
        return None
    effective_minimum = (
        minimum_slot_bytes if minimum_slot_bytes is not None else payload_uncompressed_bytes
    )
    if (
        isinstance(payload_uncompressed_bytes, bool)
        or isinstance(effective_minimum, bool)
        or payload_uncompressed_bytes <= 0
        or effective_minimum <= 0
    ):
        raise SystemUpdateError("payload size facts must be positive integers")
    support_bound = _support_installed_bytes(hardware_support_path)
    try:
        return require_finalized_slot_capacity(
            slot_bytes=target.system_slot_bytes,
            base_bytes=payload_uncompressed_bytes,
            minimum_slot_bytes=effective_minimum,
            support_installed_bytes=support_bound,
        )
    except LayoutError as exc:
        # Reporting-only display of the required total next to the owner's
        # verdict; the refuse/accept decision stays entirely with the owner.
        required = (
            max(payload_uncompressed_bytes, effective_minimum)
            + support_bound
            + FINALIZATION_GROWTH_BYTES
            + SLOT_METADATA_RESERVE_BYTES
        )
        raise SystemUpdateError(
            f"payload does not fit profile {target.profile!r} finalized system slot "
            f"({target.system_slot_bytes} bytes): base={payload_uncompressed_bytes} "
            f"minimum={effective_minimum} support_installed={support_bound} "
            f"finalization_growth={FINALIZATION_GROWTH_BYTES} "
            f"metadata_reserve={SLOT_METADATA_RESERVE_BYTES} "
            f"required={required}; cross-profile bundling refused ({exc})"
        ) from exc


def _build_output(args: argparse.Namespace, target: UpdateTarget) -> Path:
    if args.output is not None:
        return args.output
    return PROJECT_ROOT / "out" / f"greia-{args.version}-{target.profile}.greiaupdate"


def _auth_headers(args: argparse.Namespace) -> dict[str, str]:
    bearer = getattr(args, "bearer", None)
    if not bearer:
        raise SystemUpdateError("push/status requires --bearer (paired Parent bearer credential)")
    return {"Authorization": f"Bearer {bearer}"}


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
            release_id = args.release_id or f"greia-{args.version}"
            payload_base, payload_minimum = _resolve_payload_facts(
                args, target, release_id=release_id
            )
            _check_profile_capacity(
                target,
                payload_uncompressed_bytes=payload_base,
                minimum_slot_bytes=payload_minimum,
                hardware_support_path=args.hardware_support,
            )
            output = _build_output(args, target)
            build_update_bundle(
                payload_path=args.payload,
                hardware_support_path=args.hardware_support,
                output_path=output,
                version=args.version,
                release_id=release_id,
                platform_family=target.platform_family,
                architecture=target.architecture,
                profile=target.profile,
                board=target.board,
                payload_uncompressed_bytes=payload_base,
                minimum_slot_bytes=payload_minimum,
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
