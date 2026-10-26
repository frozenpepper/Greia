"""Run one bounded installed A/B update-stage diagnostic boot.

This is a diagnostic operation only. It clones an existing accepted-A image,
injects the verified candidate into the clone's PERSIST inbox while offline,
boots exactly one ``update-stage`` control phase, then collects offline facts
from the stopped clone even when staging fails. It does not assess health or
acceptance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
import time
import traceback
from pathlib import Path
from typing import Callable

from tools.x8_qemu.diagnostics import _write_result, collect_image_diagnostics
from tools.x8_qemu.lifecycle import LifecycleConfig, LifecycleHarnessError
from tools.x8_qemu.product import (
    ProductHarness,
    clone_product_image,
    inject_boot_slot,
    inject_update_candidate_into_persist,
    materialize_control_disk,
    product_boot_qemu_argv,
    require_product_host,
    select_install_qemu_binary,
    write_control_phase,
)


STAGE_TIMEOUT_SECONDS = 2400
CONTROL_DISK_BYTES = 64 * 1024 * 1024


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_json(path: Path, payload: dict[str, object]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, target)


def _control_evidence(diagnostics: dict[str, object]) -> dict[str, object]:
    """Return the collector's saved control files without interpreting health."""
    partitions = diagnostics.get("partitions")
    persist = partitions.get("PERSIST") if isinstance(partitions, dict) else None
    if not isinstance(persist, dict):
        return {}
    files = persist.get("files")
    if not isinstance(files, dict):
        return {}
    evidence: dict[str, object] = {}
    for name in ("phase-result.json", "service-diagnostics.txt"):
        entry = files.get(name)
        if isinstance(entry, dict):
            evidence[name] = entry
    return evidence


def _result_exit_code(result: dict[str, object]) -> int:
    """Keep stage, collector, source-preservation and result-write failures red."""
    if result.get("stage_error_present"):
        return 1
    if result.get("collector_error_present"):
        return 1
    if result.get("source_image_unchanged") is not True:
        return 1
    if result.get("release_bundle_unchanged") is not True:
        return 1
    if result.get("result_write_error_present"):
        return 1
    return 0


def run_stage_diagnostic(
    *,
    installed_image: Path,
    release_bundle: Path,
    output_dir: Path,
    clone_fn: Callable[[Path, Path], dict[str, object]] | None = None,
    candidate_inject_fn: Callable[[Path, Path], dict[str, object]] | None = None,
    slot_inject_fn: Callable[[Path, str], dict[str, object]] | None = None,
    materialize_fn: Callable[[Path, Path], dict[str, object]] | None = None,
    boot_fn: Callable[[str, list[str], Path, Path], None] | None = None,
    collect_fn: Callable[[Path], dict[str, object]] | None = None,
) -> dict[str, object]:
    """Run one ``update-stage`` boot on a fresh clone and collect it offline.

    Injection hooks exist only for source-level orchestration tests. Normal
    operation uses the real clone, inbox, slot-injection, control-disk, QEMU,
    serial failure parser and offline collector implementations.
    """
    source = Path(installed_image)
    bundle = Path(release_bundle)
    output = Path(output_dir)
    for path, label in ((source, "accepted-A image"), (bundle, "release bundle")):
        try:
            info = path.lstat()
        except OSError as exc:
            raise LifecycleHarnessError(f"{label} is unavailable: {path}: {exc}") from exc
        if path.is_symlink() or not path.is_file() or info.st_size == 0:
            raise LifecycleHarnessError(f"{label} must be a nonempty regular file: {path}")
    if output.exists() or output.is_symlink():
        raise LifecycleHarnessError(f"refusing to reuse existing diagnostic output: {output}")
    if not output.is_absolute():
        raise LifecycleHarnessError("output_dir must be absolute")
    if source.resolve() == bundle.resolve():
        raise LifecycleHarnessError("accepted-A image and release bundle must differ")

    config = LifecycleConfig(
        output_dir=output,
        timeout_seconds=STAGE_TIMEOUT_SECONDS,
        memory_mib=1024,
        cpus=1,
        keep_image=True,
    )
    config.validate()
    require_product_host(official_image=source)

    # Establish the output directory only after all non-mutating input gates.
    output.mkdir(parents=True, mode=0o700)
    clone = output / "stage-diagnostic-clone.img"
    control_dir = output / "control-disk"
    control_image = output / "control-disk.img"
    serial_log = output / "update-stage.serial.log"
    host_log = output / "update-stage.host.log"
    started = time.monotonic()
    source_sha = _sha256(source)
    bundle_sha = _sha256(bundle)
    result: dict[str, object] = {
        "schema_version": 1,
        "classification": "STAGE_DIAGNOSTIC_ONLY",
        "health_acceptance": "NOT_EVALUATED",
        "stage_phase": "update-stage",
        "stage_outcome": "NOT_RUN",
        "stage_attempted": False,
        "boot_returned": False,
        "collector_outcome": "NOT_RUN",
        "installed_image": str(source.resolve()),
        "installed_image_sha256_before": source_sha,
        "release_bundle": str(bundle.resolve()),
        "release_bundle_sha256": bundle_sha,
        "clone": str(clone),
        "control_disk_bytes": CONTROL_DISK_BYTES,
        "stage_timeout_seconds": STAGE_TIMEOUT_SECONDS,
        "logs": {"serial": str(serial_log), "host": str(host_log)},
    }
    clone_exists = False
    stage_error: str | None = None
    collector_error: str | None = None
    result_write_error: str | None = None
    try:
        clone_proof = (clone_fn or clone_product_image)(source, clone)
        clone_exists = clone.is_file()
        result["clone_proof"] = clone_proof
        if not clone_exists:
            raise LifecycleHarnessError("clone operation returned without a clone file")

        candidate_proof = (candidate_inject_fn or inject_update_candidate_into_persist)(
            clone, bundle
        )
        result["candidate_injection"] = candidate_proof
        slot_proof = (slot_inject_fn or inject_boot_slot)(clone, "A")
        result["slot_A_control_injection"] = slot_proof

        control_dir.mkdir(mode=0o700)
        write_control_phase(control_dir, phase="update-stage", inputs={})
        materializer = materialize_fn or materialize_control_disk
        if materialize_fn is None:
            result["control_materialization"] = materializer(
                control_dir, control_image, size_bytes=CONTROL_DISK_BYTES
            )
        else:
            result["control_materialization"] = materializer(control_dir, control_image)

        qemu_binary = select_install_qemu_binary()
        result["qemu_binary"] = qemu_binary
        argv, generated_serial, generated_host = product_boot_qemu_argv(
            installed_clone=clone,
            control_image=control_image,
            output_dir=output,
            memory_mib=config.memory_mib,
            cpus=config.cpus,
            qemu_binary=qemu_binary,
            leg="stage-diagnostic-update-stage",
        )
        # Keep the paths declared by the shared QEMU product command builder.
        serial_log = generated_serial
        host_log = generated_host
        result["logs"] = {"serial": str(serial_log), "host": str(host_log)}
        result["stage_attempted"] = True
        if boot_fn is None:
            ProductHarness(config)._boot_installed_phase(
                phase="update-stage", argv=argv, serial_log=serial_log, host_log=host_log
            )
        else:
            boot_fn("update-stage", argv, serial_log, host_log)
        result["boot_returned"] = True
        result["stage_outcome"] = "BOOT_CALL_RETURNED_NO_CAPTURED_FAILURE"
    except Exception as exc:
        stage_error = f"{type(exc).__name__}: {exc}"
        result["stage_outcome"] = "FAILED_OR_NOT_COMPLETED"
        result["stage_error"] = stage_error
        result["stage_traceback"] = traceback.format_exc()[-12000:]
    finally:
        if clone_exists:
            try:
                collector = collect_fn or collect_image_diagnostics
                diagnostics = collector(clone)
                diagnostics_path = _write_result(output / "offline-collector", diagnostics)
                result["collector_outcome"] = "COLLECTED"
                result["collector_result"] = str(diagnostics_path)
                result["offline_diagnostics"] = diagnostics
                result["control_evidence"] = _control_evidence(diagnostics)
                cleanup = diagnostics.get("cleanup")
                diagnostic_errors = diagnostics.get("errors", [])
                result["collector_errors"] = diagnostic_errors
                if isinstance(cleanup, dict):
                    result["collector_cleanup"] = cleanup
                if diagnostic_errors or (
                    not isinstance(cleanup, dict) or cleanup.get("status") != "ok"
                ):
                    collector_error = "offline collector reported errors or incomplete cleanup"
                    result["collector_outcome"] = "COLLECTED_WITH_ERRORS"
                    result["collector_error"] = collector_error
                    result["collector_error_present"] = True
            except Exception as exc:
                collector_error = f"{type(exc).__name__}: {exc}"
                result["collector_outcome"] = "FAILED"
                result["collector_error"] = collector_error
                result["collector_traceback"] = traceback.format_exc()[-12000:]
        else:
            result["collector_outcome"] = "NOT_RUN_NO_CLONE"

        try:
            result["installed_image_sha256_after"] = _sha256(source)
            result["source_image_unchanged"] = (
                result["installed_image_sha256_before"]
                == result["installed_image_sha256_after"]
            )
        except Exception as exc:
            result["source_image_unchanged"] = False
            result["source_hash_after_error"] = f"{type(exc).__name__}: {exc}"
        try:
            result["release_bundle_sha256_after"] = _sha256(bundle)
            result["release_bundle_unchanged"] = (
                result["release_bundle_sha256"] == result["release_bundle_sha256_after"]
            )
        except Exception as exc:
            result["release_bundle_unchanged"] = False
            result["release_bundle_hash_after_error"] = f"{type(exc).__name__}: {exc}"
        result["elapsed_seconds"] = round(time.monotonic() - started, 3)
        result["stage_error_present"] = stage_error is not None
        result["collector_error_present"] = (
            collector_error is not None or result.get("collector_error_present") is True
        )
        result["result_write_error_present"] = False
        try:
            _write_json(output / "result.json", result)
        except Exception as exc:
            result_write_error = f"{type(exc).__name__}: {exc}"
            result["result_write_error_present"] = True
            result["result_write_error"] = result_write_error

    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--installed-image", required=True, type=Path)
    parser.add_argument("--release-bundle", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    if sys.platform != "linux" or platform.machine().lower() not in ("x86_64", "amd64"):
        parser.error("stage diagnostic requires a Linux x86_64 product host")
    if os.geteuid() != 0:
        parser.error("stage diagnostic requires root on the Linux product host")
    try:
        result = run_stage_diagnostic(
            installed_image=args.installed_image,
            release_bundle=args.release_bundle,
            output_dir=args.output,
        )
    except LifecycleHarnessError as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return _result_exit_code(result)


if __name__ == "__main__":
    raise SystemExit(main())
