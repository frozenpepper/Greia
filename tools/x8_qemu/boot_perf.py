"""P5.4 boot-performance regression fold for the product-image mode (additive).

Wires the frozen P5.4 instrument (``tools/x8_qemu/preintro_timing.py``:
``measure_boot``/``compare``, frozen P1-P4 predicates,
``FIXED_INTRO_SECONDS == 7.0``) into the product-image installed-boot
path (``tools/x8_qemu/product.py`` ``product_boot_qemu_argv`` +
``ProductHarness.run_boot_health_product``) so each recorded installed
boot yields power/QEMU-start -> first-frame, intro -> interactive-ready
and total -> interactive-ready measurements derived from the canonical
markers (``src/greia_platform/boot_markers.py::emit_boot_marker``,
parsed by ``tools/boot/analyze_boot_markers.py``).

Reuse, not duplication: timing predicates/collection stay owned by
``preintro_timing`` (``compare`` is called, never reimplemented); the
lifecycle sequence, transition contract, observation folds, identity
record and QEMU argv stay owned by ``lifecycle.py``/``product.py``;
the marker vocabulary stays owned by ``boot_markers.py`` /
``analyze_boot_markers.py``; the intro length stays owned by
``src/greia_launcher/boot_intro.py`` (referenced, never changed).

Fail-closed: the seven-second intro is verified unchanged
(5 s animation + 2 s hold) before any measurement; a genuine
regression stays red (never narrowed/waived); a missing marker or a
missing Linux/QEMU facility yields ``BLOCKED``/``NOT_READY``, never a
pass; every measurement binds the exact built-image SHA and the source
SHA at evidence time; raw logs/preregistration live under the
disposable output root (outside the source tree); no bulky artifacts
are committed.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Mapping

from .lifecycle import LifecycleConfig, LifecycleHarnessError
from .product import sha256_file as _sha256_file
from . import product as _product

#: Schema of the P5.4 boot-performance record consumed by Gate-P5 closure.
BOOT_PERF_SCHEMA_VERSION = 1
BOOT_PERF_RECORD_SCHEMA = "boot-perf-product-v1"

#: Expected intro split owned by ``src/greia_launcher/boot_intro.py``
#: (``ANIMATION_SECONDS`` + ``FINAL_FRAME_HOLD_SECONDS``). Referenced
#: here only to prove the intro is unchanged; this module never edits it.
EXPECTED_INTRO_ANIMATION_SECONDS = 5.0
EXPECTED_INTRO_HOLD_SECONDS = 2.0

#: Supplemental pre-intro health/update patterns. The frozen P4
#: predicate (``preintro_timing.DEFAULT_MARKERS["update_service_started"]``)
#: already refuses update-service work before the first frame; these
#: extend the same ordering proof to the boot-health service/socket and
#: to socket-activation lines, using the shipped unit Descriptions
#: (``Greia OS system-update semantic service``,
#: ``Greia OS boot-health semantic service``). Absence means no
#: pre-intro work, never a failure; presence before the first-frame
#: marker is RED. This supplements ``compare`` -- it never replaces or
#: narrows P1-P4.
HEALTH_PREINTRO_PATTERNS: tuple[tuple[str, str], ...] = (
    ("update_service", r"Started Greia OS system-update"),
    ("boot_health_service", r"Started Greia OS boot-health"),
    ("update_socket", r"Listening on .*system-update"),
    ("boot_health_socket", r"Listening on .*boot-health"),
    ("update_sock_path", r"system-update\.sock"),
    ("boot_health_sock_path", r"boot-health\.sock"),
)

_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _preintro():
    """Import the frozen instrument (single owner of P1-P4)."""
    from . import preintro_timing as _mod

    return _mod


def sha256_file(path: Path) -> str:
    """Hash a file (single owner: ``product.sha256_file``)."""
    return _sha256_file(Path(path))


def verify_seven_second_intro_unchanged() -> dict[str, object]:
    """Prove the seven-second intro is unchanged (5 s + 2 s hold).

    Reads the production constants from
    ``src/greia_launcher/boot_intro.py`` and the frozen
    ``FIXED_INTRO_SECONDS`` from ``preintro_timing``. Any drift raises
    RED (fail-closed) instead of letting the metric be improved by
    shortening the intro.
    """
    from greia_launcher import boot_intro

    preintro = _preintro()
    animation = float(boot_intro.ANIMATION_SECONDS)
    hold = float(boot_intro.FINAL_FRAME_HOLD_SECONDS)
    total = float(boot_intro.MAX_INTRO_SECONDS)
    fixed = float(preintro.FIXED_INTRO_SECONDS)
    if animation != EXPECTED_INTRO_ANIMATION_SECONDS:
        raise LifecycleHarnessError(
            f"boot-perf refused: intro animation is {animation!r}s, "
            f"expected {EXPECTED_INTRO_ANIMATION_SECONDS!r}s (never shorten the intro)"
        )
    if hold != EXPECTED_INTRO_HOLD_SECONDS:
        raise LifecycleHarnessError(
            f"boot-perf refused: intro hold is {hold!r}s, "
            f"expected {EXPECTED_INTRO_HOLD_SECONDS!r}s (never shorten the intro)"
        )
    if total != 7.0 or fixed != 7.0:
        raise LifecycleHarnessError(
            f"boot-perf refused: intro total is {total!r}s / "
            f"frozen {fixed!r}s, expected 7.0s"
        )
    return {
        "animation_seconds": animation,
        "hold_seconds": hold,
        "total_seconds": total,
        "frozen_seconds": fixed,
    }


def derive_boot_perf_intervals(measurement: Mapping[str, object] | object) -> dict[str, object | None]:
    """Derive the P5.4 intervals from one ``BootMeasurement``.

    Returns ``power_to_first_frame`` (QEMU-start -> first visible
    frame), ``intro_end_to_ready`` (intro end -> interactive ready),
    ``first_frame_to_ready``, ``total_to_ready`` (QEMU-start ->
    interactive ready) and ``intro_duration`` (first frame -> intro
    end). A missing endpoint yields ``None`` (``NOT_READY``, never
    interpolated).
    """
    if isinstance(measurement, Mapping):
        get = measurement.get  # type: ignore[assignment]
        start = get("qemu_start_monotonic")  # type: ignore[operator]
        first = get("first_intro_frame")  # type: ignore[operator]
        end = get("intro_end")  # type: ignore[operator]
        ready = get("interactive_ready")  # type: ignore[operator]
    else:
        start = getattr(measurement, "qemu_start_monotonic", None)
        first = getattr(measurement, "first_intro_frame", None)
        end = getattr(measurement, "intro_end", None)
        ready = getattr(measurement, "interactive_ready", None)

    def _elapsed(a: object, b: object) -> float | None:
        if a is None or b is None:
            return None
        try:
            return float(b) - float(a)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return None

    return {
        "power_to_first_frame": _elapsed(start, first),
        "intro_end_to_ready": _elapsed(end, ready),
        "first_frame_to_ready": _elapsed(first, ready),
        "total_to_ready": _elapsed(start, ready),
        "intro_duration": _elapsed(first, end),
    }


def check_no_preintro_health_work(serial_text: str) -> dict[str, object]:
    """Prove no update/health socket/service work precedes the first frame.

    Orders the canonical first-frame marker against the supplemental
    ``HEALTH_PREINTRO_PATTERNS`` by byte offset in the guest serial
    stream. A missing first-frame marker yields ``NOT_READY`` (cannot
    order, never a pass); a health pattern strictly before it yields
    ``FAIL`` naming the hits; otherwise ``PASS``. Absence of health
    lines means no pre-intro work, never a failure (matches the frozen
    P4 semantics).
    """
    preintro = _preintro()
    first_pattern = preintro.DEFAULT_MARKERS["first_intro_frame"]
    first_match = re.search(first_pattern, serial_text)
    if first_match is None:
        return {
            "verdict": "NOT_READY",
            "detail": "FIRST_INTRO_FRAME marker missing; cannot order update/health work",
        }
    hits: list[str] = []
    for name, pattern in HEALTH_PREINTRO_PATTERNS:
        for match in re.finditer(pattern, serial_text):
            if match.start() < first_match.start():
                hits.append(name)
                break
    if hits:
        return {
            "verdict": "FAIL",
            "detail": "update/health work before the first intro frame: "
            + ", ".join(sorted(set(hits))),
        }
    return {
        "verdict": "PASS",
        "detail": "no update/health socket/service work observed before the first frame",
    }


def compare_boot_perf(
    baseline: object,
    activated: object,
) -> dict[str, object]:
    """Interpret one baseline/activated pair against the frozen predicates.

    Thin reuse wrapper over ``preintro_timing.compare``: the frozen
    P1-P4 interpretation is never reimplemented or narrowed here.
    """
    preintro = _preintro()
    return dict(preintro.compare(baseline, activated))  # type: ignore[arg-type]


def _require_hex64(value: object, *, role: str) -> str:
    if not isinstance(value, str) or not _HEX64.fullmatch(value):
        raise LifecycleHarnessError(
            f"boot-perf record requires the observed {role} as SHA-256 "
            "(never minted or interpolated)"
        )
    return value


def build_boot_perf_record(
    *,
    baseline: object,
    activated: object,
    serial_text: str,
    installed_image_sha256: str,
    source_sha256: str,
    qemu_argv: list[str] | None = None,
    leg: str = "boot-health",
) -> dict[str, object]:
    """Build the P5.4 boot-performance record (pure, fail-closed).

    Runs the frozen ``compare`` strictly, derives the P5.4 intervals
    for both runs, proves the intro unchanged and the extended
    no-pre-intro health check, and binds the exact built-image SHA and
    source SHA. A regression stays red; a missing marker stays
    ``NOT_READY``; a missing SHA refuses (never fabricated).
    """
    installed_sha = _require_hex64(installed_image_sha256, role="built-image SHA")
    source_sha = _require_hex64(source_sha256, role="source SHA")
    intro_proof = verify_seven_second_intro_unchanged()
    comparison = compare_boot_perf(baseline, activated)
    health = check_no_preintro_health_work(serial_text)
    intervals = {
        "baseline": derive_boot_perf_intervals(
            baseline.as_dict() if hasattr(baseline, "as_dict") else baseline  # type: ignore[union-attr]
        ),
        "activated": derive_boot_perf_intervals(
            activated.as_dict() if hasattr(activated, "as_dict") else activated  # type: ignore[union-attr]
        ),
    }
    predicates = dict(comparison.get("predicates", {}))
    overall_parts = [str(comparison.get("overall", "NOT_READY")), str(health.get("verdict"))]
    if overall_parts[0] != "PASS" or overall_parts[1] != "PASS":
        overall = "NOT_READY" if "NOT_READY" in overall_parts else "FAIL"
    else:
        overall = "PASS"
    return {
        "schema": BOOT_PERF_RECORD_SCHEMA,
        "schema_version": BOOT_PERF_SCHEMA_VERSION,
        "leg": leg,
        "installed_image_sha256": installed_sha,
        "source_sha256": source_sha,
        "intervals": intervals,
        "comparison": comparison,
        "health_preintro": health,
        "intro_proof": intro_proof,
        "overall": overall,
        "qemu_argv_head": (list(qemu_argv[:3]) if qemu_argv else []),
    }


def preregistration_text() -> str:
    """Return the frozen preregistration text (written to evidence)."""
    import io
    from contextlib import redirect_stdout

    preintro = _preintro()
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        code = preintro.main(["preregister"])
    if code != 0:
        raise LifecycleHarnessError("boot-perf refused: preregistration instrument failed")
    return buffer.getvalue()


def run_boot_perf_product(
    *,
    config: LifecycleConfig,
    installed_image: Path,
    release_bundle: Path | None = None,
    baseline: object | None = None,
    leg: str = "boot-health",
    timeout_seconds: int = 300,
    measure_fn=None,
    serial_reader=None,
) -> dict[str, object]:
    """Measure one installed boot in the product-image mode (P5.4).

    Order (fail-closed, disposable media only): prove the intro
    unchanged -> gate the Linux/QEMU facility (``BLOCKED`` naming it)
    -> hash the built image + source at evidence time -> build the
    installed-boot argv through ``product_boot_qemu_argv`` (virtual VGA
    for the real Xorg launcher, i386-capable binary) -> time the boot
    through the frozen ``measure_boot`` (injectable ``measure_fn`` for
    unit tests) -> derive intervals, interpret strictly via ``compare``
    plus the extended health check, bind SHAs, and persist the raw
    serial log, preregistration, measurement and comparison JSON under
    ``<output_dir>/product/boot-perf/`` (external evidence root, never
    the source tree).

    ``baseline`` is the pre-change ``BootMeasurement`` the frozen P1-P3
    compare against; ``None`` yields ``NOT_READY`` (never a pass).
    ``serial_reader`` overrides serial-text loading in tests; production
    reads the QEMU serial log bytes. Never shortens the intro, never
    fabricates a boot, never contacts ``/dev``.
    """
    config.validate()
    intro_proof = verify_seven_second_intro_unchanged()
    _product.assert_control_absent_from_production()
    origin = Path(installed_image)
    _product.require_product_host(official_image=origin)
    if origin.is_symlink() or not origin.is_file():
        raise LifecycleHarnessError(
            f"BLOCKED product mode: installed image is absent ({origin}); "
            "never synthesize one"
        )
    installed_sha = sha256_file(origin)
    if release_bundle is None:
        raise LifecycleHarnessError(
            "BLOCKED boot-perf: no source SHA is available "
            "(pass the signed release_bundle; never mint one)"
        )
    bundle = Path(release_bundle)
    if bundle.is_symlink() or not bundle.is_file():
        raise LifecycleHarnessError(
            f"BLOCKED product mode: source bundle is absent ({bundle})"
        )
    source_sha = sha256_file(bundle)
    qemu_binary = _product.select_install_qemu_binary()
    root = Path(config.output_dir) / "product" / "boot-perf"
    root.mkdir(parents=True, exist_ok=True)
    argv, serial_log, host_log = _product.product_boot_qemu_argv(
        installed_clone=origin,
        control_image=None,
        output_dir=root,
        memory_mib=config.memory_mib,
        cpus=config.cpus,
        qemu_binary=qemu_binary,
        leg=f"{leg}-perf",
    )
    if serial_log.exists():
        raise LifecycleHarnessError(
            f"boot-perf refused: serial log already exists ({serial_log}); "
            "refusing to reuse evidence"
        )
    preintro = _preintro()
    if measure_fn is not None:
        activated = measure_fn(
            label=f"product-{leg}",
            qemu_argv=[str(p) for p in argv],
            serial_log=serial_log,
            timeout_seconds=timeout_seconds,
        )
    else:
        activated = preintro.measure_boot(
            label=f"product-{leg}",
            qemu_argv=[str(p) for p in argv],
            serial_log=serial_log,
            timeout_seconds=timeout_seconds,
        )
    if serial_reader is not None:
        serial_text = str(serial_reader(serial_log))
    else:
        try:
            serial_text = serial_log.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            raise LifecycleHarnessError(
                f"boot-perf refused: unreadable serial log ({serial_log}: {exc})"
            ) from exc
    if baseline is None:
        record: dict[str, object] = {
            "schema": BOOT_PERF_RECORD_SCHEMA,
            "schema_version": BOOT_PERF_SCHEMA_VERSION,
            "leg": leg,
            "installed_image_sha256": installed_sha,
            "source_sha256": source_sha,
            "intervals": {
                "activated": derive_boot_perf_intervals(
                    activated.as_dict() if hasattr(activated, "as_dict") else activated
                )
            },
            "comparison": {
                "schema": "pre-intro-timing-comparison-v1",
                "overall": "NOT_READY",
                "detail": "no baseline measurement was supplied; regression is unproven",
            },
            "health_preintro": check_no_preintro_health_work(serial_text),
            "intro_proof": intro_proof,
            "overall": "NOT_READY",
            "qemu_argv_head": [str(p) for p in argv[:3]],
        }
    else:
        record = build_boot_perf_record(
            baseline=baseline,
            activated=activated,
            serial_text=serial_text,
            installed_image_sha256=installed_sha,
            source_sha256=source_sha,
            qemu_argv=[str(p) for p in argv],
            leg=leg,
        )
    # Persist raw evidence under the disposable output root (never the tree).
    (root / "preregistration.txt").write_text(preregistration_text(), encoding="utf-8")
    if hasattr(activated, "as_dict"):
        (root / "activated.json").write_text(
            json.dumps(activated.as_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    if baseline is not None and hasattr(baseline, "as_dict"):
        (root / "baseline.json").write_text(
            json.dumps(baseline.as_dict(), indent=2, sort_keys=True) + "\n",  # type: ignore[union-attr]
            encoding="utf-8",
        )
    (root / "comparison.json").write_text(
        json.dumps(record.get("comparison", {}), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (root / "boot-perf-record.json").write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    evidence = {
        "preregistration": str(root / "preregistration.txt"),
        "serial_log": str(serial_log),
        "host_log": str(host_log),
        "comparison": str(root / "comparison.json"),
        "record": str(root / "boot-perf-record.json"),
    }
    return {
        "ok": record.get("overall") == "PASS",
        "overall": record.get("overall"),
        "leg": leg,
        "installed_image": str(origin.resolve()),
        "installed_image_sha256": installed_sha,
        "source_sha256": source_sha,
        "record": record,
        "evidence": evidence,
        "source_image_mutated": False,
    }
