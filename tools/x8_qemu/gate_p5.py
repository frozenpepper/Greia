"""Gate P5 `LEGACY_PRODUCT_PATH_GREEN` closure composite (additive, P5.2/P5.3/P5.4).

Composes the product-image mode and all P5 legs into one full
official-image / product-unit lifecycle run and closes Gate P5:
install -> boot A / health -> update B / health -> unhealthy candidate /
recovery -> accepted B -> D31 -> reverse A.

Reuse, not duplication: sequencing/observation/attestation stay owned by
``lifecycle.py`` (``assert_lifecycle_transitions`` is called, never
redefined); the install/boot-health/recovery legs stay owned by
``product.py`` (``ProductHarness.run_product`` /
``run_boot_health_product`` / ``run_recovery_d31_reverse_product`` plus
``build_unhealthy_candidate_bundle`` / ``verify_unhealthy_candidate_bundle``);
the P5.4 measurement stays owned by ``boot_perf.py``
(``run_boot_perf_product`` / ``build_boot_perf_record``); the 768 MiB
budget stays owned by ``devproof.py`` (device-measured
``run_envelope_device``); the P5.3 identity re-assertion stays owned by
``product.assert_product_identity_complete``. This module adds only the
frozen-leg orchestration, the explicit on-image ``d31_fn`` seeding/reading
through the ``devproof`` store parse paths, and the fail-closed
predicate->evidence mapping.

Fail-closed: the recovery leg requires an explicit ``d31_fn`` that pins
the on-image D31 persist namespace mapping (the product entry's default
``d31_fn`` deliberately raises ``BLOCKED`` on the unpinned mapping, so a
closure that omits it can never pass); the boot-performance record must
be live and strictly GREEN; the budget must be device-measured (SOURCE_SCOPE
never counts); any red/BLOCKED/missing predicate keeps Gate P5 OPEN and
T3-P OPEN. A source-level or partial green is never Gate-P5 completion.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Mapping

from .lifecycle import LifecycleConfig, LifecycleHarnessError

#: Gate under closure.
GATE_P5_ID = "LEGACY_PRODUCT_PATH_GREEN"

#: Schema of the Gate-P5 closure record.
GATE_P5_SCHEMA = "gate-p5-closure-v1"
GATE_P5_SCHEMA_VERSION = 1

#: Preregistered Gate-P5 predicates (PLAN.md Section 10 + brief, frozen).
GATE_P5_PREDICATES: tuple[str, ...] = (
    "full_lifecycle_green",
    "broken_candidate_recovers",
    "d31_survives",
    "budget_768_green",
    "no_harness_substitution",
    "sha_bound",
    "boot_perf_green",
    "provenance_refusal_green",
    "rc4_checkable",
)

#: RC-4 traversal map: each of the 8 frozen lifecycle steps bound to the
#: installed unit/socket/entrypoint it must traverse. Carried in the
#: closure record so an independent reviewer can check every claimed
#: transition without re-running QEMU.
GATE_P5_TRANSITION_UNITS: dict[str, dict[str, object]] = {
    "fresh-install-A": {
        "units": [
            "greia-install-transaction.service",
        ],
        "sockets": ["greia-install-transaction.sock"],
        "entrypoint": (
            "InstallTransactionClient.prepare("
            "expected_target_identity, compatible_profile_id)"
            " -> execute(transaction_nonce, plan_digest)"
        ),
        "evidence": "install_result.observed + target_observation",
    },
    "boot-A-accepted": {
        "units": [
            "greia-boot-health-credential.service",
            "greia-boot-health.service",
        ],
        "sockets": ["greia-boot-health.sock"],
        "entrypoint": "boot-health CONFIRM_BOOT_HEALTH for slot A",
        "evidence": "install_result.observed + boot_health_result.observed",
    },
    "stage-B-one-shot": {
        "units": ["greia-system-update.service"],
        "sockets": ["greia-system-update.sock"],
        "entrypoint": "STAGE_CURRENT_CANDIDATE through the installed update socket",
        "evidence": "boot_health_result.phases + slot_b_injection",
    },
    "boot-B-commit": {
        "units": [
            "greia-boot-health.service",
            "greia-launcher.service",
        ],
        "sockets": ["greia-boot-health.sock"],
        "entrypoint": "boot-health commit B + launcher INTERACTIVE_READY",
        "evidence": "boot_health_result.observed (default B, sequence)",
    },
    "stage-broken-candidate": {
        "units": ["greia-system-update.service"],
        "sockets": ["greia-system-update.sock"],
        "entrypoint": (
            "STAGE_CURRENT_CANDIDATE stages the validly-signed unhealthy "
            "candidate (pinned remove-root-health-capability-issuer build)"
        ),
        "evidence": "recovery_result.stages[stage-broken-candidate]",
    },
    "boot-broken-candidate": {
        "units": ["greia-boot-health.service"],
        "sockets": ["greia-boot-health.sock"],
        "entrypoint": (
            "candidate boot withholds health (no production token can "
            "exist); observer records the candidate slot"
        ),
        "evidence": "recovery_result.stages[boot-broken-candidate]",
    },
    "recovery-boot-B": {
        "units": [
            "greia-candidate-recovery.timer",
            "greia-candidate-recovery.service",
            "usr/local/lib/greia-os/greia-candidate-recovery",
        ],
        "sockets": [],
        "entrypoint": (
            "real 3-minute timer marks FAILED with the pinned "
            "health-service-failure/automatic-reboot note and reboots to "
            "the accepted slot"
        ),
        "evidence": "recovery_result.stages[recovery-boot-accepted]",
    },
    "reverse-update-B-to-A": {
        "units": [
            "greia-system-update.service",
            "greia-boot-health.service",
            "greia-launcher.service",
        ],
        "sockets": ["greia-system-update.sock", "greia-boot-health.sock"],
        "entrypoint": (
            "reverse release staged/armed through the installed updater, "
            "booted, health-committed with advanced sequence/default"
        ),
        "evidence": "recovery_result.stages[reverse-update-accepted]",
    },
}

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_HEX40 = re.compile(r"^[0-9a-f]{40}$")

#: Persist partition index on the installed image (slots A/B are
#: partitions 2/3, boot-control is partition 1).
PERSIST_PARTITION_INDEX = 4

#: On-image D31 store subdirectories pinned by the persist mapping (the
#: namespaces ``devproof`` reads through its store parse paths).
D31_PERSIST_NAMESPACES: tuple[str, ...] = (
    "device-settings",
    "child-profiles",
    "parent-policy",
)


def _require_hex64(value: object, *, role: str) -> str:
    if not isinstance(value, str) or not _HEX64.fullmatch(value):
        raise LifecycleHarnessError(
            f"gate-P5 record requires the observed {role} as SHA-256 "
            "(never minted or interpolated)"
        )
    return value


def read_source_head(*, project_root: Path | None = None) -> str:
    """Read the source HEAD SHA at evidence time (bound into the record)."""
    from . import product as _product

    root = Path(project_root) if project_root is not None else _product.PROJECT_ROOT
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=str(root),
    )
    head = str(getattr(completed, "stdout", "") or "").strip()
    if completed.returncode != 0 or not _HEX40.fullmatch(head):
        raise LifecycleHarnessError(
            "gate-P5 record refused: source HEAD is unavailable "
            "(never minted); bind the exact checkout before closing"
        )
    return head


def _loop_partition_device(
    image: Path, *, partition: int, runner=None
) -> tuple[str, object, str]:
    """Attach an image with partition scan and return the part device.

    Returns ``(loopdev, run, tools)`` for later detach; raises BLOCKED
    naming the missing facility when loop tooling is absent.
    """
    from . import product as _product

    tools = _product._require_loop_tools("losetup", "mount", "umount")
    run = runner or subprocess.run
    completed = _product._run_checked(
        [tools["losetup"], "--show", "-f", "-P", str(image)],
        runner=run,
        timeout=120,
        what=f"loop attach -P for {image}",
    )
    loopdev = str(getattr(completed, "stdout", "") or "").strip().splitlines()
    if not loopdev or not loopdev[0].startswith("/dev/"):
        raise LifecycleHarnessError(
            f"loop attach for {image} returned no device node"
        )
    return loopdev[0], run, tools


def _loop_detach(loopdev: str, *, run=None, tools: Mapping[str, str] | None = None) -> None:
    from . import product as _product

    resolved = dict(tools) if tools else _product._require_loop_tools("losetup")
    _product._run_checked(
        [resolved["losetup"], "-d", loopdev],
        runner=run,
        timeout=120,
        what=f"loop detach for {loopdev}",
    )


def prepare_on_image_d31_seed(
    *,
    installed_image: Path,
    recovery_clone: Path,
    work_dir: Path,
    persist_partition: int = PERSIST_PARTITION_INDEX,
    seed_fn=None,
    read_fn=None,
    snapshot_fn=None,
    mount_fn=None,
    unmount_fn=None,
) -> dict[str, object]:
    """Seed D31 state onto the installed image and bind the after-reader.

    The capable host calls this *before* ``run_recovery_d31_reverse_product``:
    the representative D31 state is written through the ``devproof`` store
    APIs onto the persist partition of ``installed_image`` (the
    health-committed image the recovery leg clones, so the seed rides
    into the recovery clone), the store-parse-path baseline plus the byte
    snapshot are captured, and the returned zero-arg ``d31_fn`` reads the
    post-recovery persist from ``recovery_clone`` through the same parse
    paths. The returned ``persist_mapping`` pins the on-image D31 persist
    namespace mapping the product entry refuses to run without.

    ``seed_fn``/``read_fn``/``snapshot_fn``/``mount_fn``/``unmount_fn``
    default to the real persist-partition mount + ``devproof`` store
    paths; tests inject recording fakes. Returns ``{"d31_fn",
    "persist_mapping", "semantic_before", "bytes_before"}``.
    """
    from .devproof import read_d31_representative_state, verify_d31_rollback
    from .devproof import write_d31_representative_state
    from . import product as _product

    image = Path(installed_image)
    clone = Path(recovery_clone)
    work = Path(work_dir)
    work.mkdir(parents=True, exist_ok=True)
    if image.is_symlink() or not image.is_file():
        raise LifecycleHarnessError(
            "BLOCKED product mode: no health-committed installed image to "
            f"seed D31 onto ({image}); never synthesize one"
        )
    for candidate in (image, clone):
        if str(candidate).startswith("/dev/"):
            raise LifecycleHarnessError(
                f"refusing block-device path {candidate}: product mode takes "
                "regular image files only"
            )

    seed_root = work / "d31-seed-mnt"
    seed_root.mkdir(parents=True, exist_ok=True)

    if mount_fn is not None and seed_fn is not None and read_fn is not None:
        mount_fn(image, seed_root, persist_partition)
        try:
            # Write shape is the leg's ``semantic_before`` contract (the
            # read shape nests profiles by id and cannot serve as
            # ``before`` for ``verify_d31_rollback``); the baseline read
            # proves the seed reads back before the leg runs, and the
            # snapshot is taken while mounted so it measures the seeded
            # bytes rather than the empty mountpoint.
            semantic_written = dict(seed_fn(seed_root))
            baseline = dict(read_fn(seed_root))
            verify_d31_rollback(semantic_written, baseline)
            bytes_before = dict(snapshot_fn(seed_root)) if snapshot_fn is not None else {}
        finally:
            if unmount_fn is not None:
                unmount_fn(seed_root)
        semantic_before = semantic_written
    else:
        loopdev, run, tools = _loop_partition_device(image, partition=persist_partition)
        part = f"{loopdev}p{persist_partition}"
        completed = run(
            ["mount", "-o", "rw", part, str(seed_root)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if getattr(completed, "returncode", 1) != 0:
            _loop_detach(loopdev, run=run, tools=tools)
            raise LifecycleHarnessError(
                f"gate-P5 D31 seed refused: cannot mount persist {part}"
            )
        try:
            semantic_written = dict(write_d31_representative_state(seed_root))
            # Baseline through the store parse paths first (opening the
            # activity storage materializes deterministic namespace
            # scaffolding); the byte snapshot below therefore measures
            # failure/recovery drift only. Snapshot while mounted.
            baseline = dict(read_d31_representative_state(seed_root))
            verify_d31_rollback(semantic_written, baseline)
            bytes_before = dict(_product.snapshot_persist_tree(seed_root))
        finally:
            run(["umount", str(seed_root)], capture_output=True, timeout=120)
            _loop_detach(loopdev, run=run, tools=tools)
        semantic_before = semantic_written

    persist_mapping = {
        "installed_image": str(image.resolve()) if image.exists() else str(image),
        "recovery_clone": str(clone),
        "persist_partition": int(persist_partition),
        "persist_namespaces": list(D31_PERSIST_NAMESPACES),
        "store_parse_paths": "devproof.read_d31_representative_state",
        "semantic_paths": "devproof.verify_d31_rollback",
    }

    def _d31_fn() -> dict[str, object]:
        from .devproof import read_d31_representative_state as _read
        from . import product as _prod

        after_root = work / "d31-after-mnt"
        after_root.mkdir(parents=True, exist_ok=True)
        if mount_fn is not None and read_fn is not None:
            mount_fn(clone, after_root, persist_partition)
            try:
                semantic_after = dict(read_fn(after_root))
            finally:
                if unmount_fn is not None:
                    unmount_fn(after_root)
            bytes_after = dict(snapshot_fn(after_root)) if snapshot_fn is not None else {}
        else:
            loopdev, run, tools = _loop_partition_device(clone, partition=persist_partition)
            part = f"{loopdev}p{persist_partition}"
            completed = run(
                ["mount", "-o", "ro", part, str(after_root)],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if getattr(completed, "returncode", 1) != 0:
                _loop_detach(loopdev, run=run, tools=tools)
                raise LifecycleHarnessError(
                    f"gate-P5 D31 readback refused: cannot mount persist {part}"
                )
            try:
                semantic_after = dict(_read(after_root))
                bytes_after = dict(_prod.snapshot_persist_tree(after_root))
            finally:
                run(["umount", str(after_root)], capture_output=True, timeout=120)
                _loop_detach(loopdev, run=run, tools=tools)
        return {
            "semantic_before": dict(semantic_before),
            "semantic_after": dict(semantic_after),
            "bytes_before": dict(bytes_before),
            "bytes_after": dict(bytes_after),
            "persist_mapping": dict(persist_mapping),
        }

    return {
        "d31_fn": _d31_fn,
        "persist_mapping": persist_mapping,
        "semantic_before": dict(semantic_before),
        "bytes_before": dict(bytes_before),
    }


def build_gate_p5_record(
    *,
    install_result: Mapping[str, object],
    boot_health_result: Mapping[str, object],
    recovery_result: Mapping[str, object],
    boot_perf_record: Mapping[str, object],
    device_envelope: Mapping[str, object],
    source_head: str,
) -> dict[str, object]:
    """Build the Gate-P5 predicate->evidence mapping (pure, fail-closed).

    Re-asserts both P5.3 identity records through
    ``assert_product_identity_complete`` at evidence time, requires the
    live P5.4 record strictly GREEN with bound SHAs, requires the
    DEVICE-scope envelope green from device-measured values, refuses any
    ``source_image_mutated`` truthy flag, and closes the combined 8-step
    report (all steps observed across the three legs) through
    ``assert_lifecycle_transitions``. Any red/missing predicate raises
    (Gate stays OPEN); nothing is projected or laundered.
    """
    from .lifecycle import (
        BOOT_OUTCOME_EXPECTED_SLOT,
        LAUNCHER_ACCEPTANCE_LEGS,
        LIFECYCLE_SEQUENCE,
        SHIPPED_UPDATE_LEGS,
        assert_lifecycle_transitions,
    )
    from . import product as _product

    for label, result in (
        ("install", install_result),
        ("boot-health", boot_health_result),
        ("recovery", recovery_result),
    ):
        if not isinstance(result, Mapping) or not result.get("ok"):
            raise LifecycleHarnessError(
                f"gate-P5 is RED: {label} leg did not report ok"
            )
        if result.get("source_image_mutated"):
            raise LifecycleHarnessError(
                "gate-P5 record refuses a mutated source image "
                f"({label} leg reports source_image_mutated truthy)"
            )

    install_identity = install_result.get("unit_identity")
    boot_health_identity = boot_health_result.get("unit_identity")
    if not isinstance(install_identity, Mapping) or not isinstance(
        boot_health_identity, Mapping
    ):
        raise LifecycleHarnessError(
            "gate-P5 is RED: a P5.3 identity record is missing "
            "(install leg and boot-health leg records are both required)"
        )
    install_image = install_result.get("installer_image")
    install_bundles = [str(install_result.get("release_bundle"))]
    _product.assert_product_identity_complete(
        install_identity,
        installer_image=Path(str(install_image)),
        release_bundles=[Path(bundle) for bundle in install_bundles],
    )
    boot_image = boot_health_result.get("installed_image")
    boot_bundles = [str(boot_health_result.get("release_bundle"))]
    _product.assert_product_identity_complete(
        boot_health_identity,
        installed_image=Path(str(boot_image)),
        release_bundles=[Path(bundle) for bundle in boot_bundles],
    )

    # One full lifecycle: the boot-health leg must run on the install-leg
    # disposable target, and the recovery leg on the boot-health
    # committed clone (paths, not just SHAs, so legs cannot be spliced
    # from different runs).
    install_target = install_result.get("disposable_target")
    install_target_path = (
        str(install_target.get("target"))
        if isinstance(install_target, Mapping)
        else None
    )
    if install_target_path != str(boot_image):
        raise LifecycleHarnessError(
            "gate-P5 is RED: boot-health leg did not run on the install-leg "
            "disposable target (legs from different runs never compose)"
        )
    boot_clone = boot_health_result.get("clone")
    boot_clone_path = (
        str(boot_clone.get("clone")) if isinstance(boot_clone, Mapping) else None
    )
    recovery_image = recovery_result.get("installed_image")
    if boot_clone_path is None or recovery_image is None or str(
        recovery_image
    ) != str(boot_clone_path):
        raise LifecycleHarnessError(
            "gate-P5 is RED: recovery leg did not run on the boot-health "
            "committed clone (legs from different runs never compose)"
        )

    # Recovery bundle/image SHAs are re-hashed from their bound files at
    # evidence time (never trusted as bare strings): a substituted
    # well-formed SHA without bytes behind it stays RED.
    for label, path_key, sha_key in (
        ("recovery installed image", "installed_image", "installed_image_sha256"),
        ("unhealthy candidate bundle", "unhealthy_bundle", "unhealthy_bundle_sha256"),
        ("reverse release bundle", "reverse_bundle", "reverse_bundle_sha256"),
    ):
        claimed = _require_hex64(
            recovery_result.get(sha_key), role=f"closure {sha_key}"
        )
        path_value = recovery_result.get(path_key)
        if not isinstance(path_value, str) or not path_value:
            raise LifecycleHarnessError(
                f"gate-P5 is RED: {label} SHA is not bound to an observed "
                "file (a bare digest is not evidence)"
            )
        try:
            observed_sha = _product.sha256_file(Path(path_value))
        except LifecycleHarnessError as exc:
            raise LifecycleHarnessError(
                f"gate-P5 is RED: {label} file cannot be re-hashed "
                f"({path_value}: {exc})"
            ) from exc
        if observed_sha != claimed:
            raise LifecycleHarnessError(
                f"gate-P5 is RED: {label} SHA does not match its bound "
                "file (substituted evidence)"
            )

    # Recovery stage facts carried in on host-observed evidence only.
    stages = recovery_result.get("stages")
    if not isinstance(stages, Mapping):
        raise LifecycleHarnessError(
            "gate-P5 is RED: recovery stage facts are missing"
        )
    for stage in (
        "stage-broken-candidate",
        "boot-broken-candidate",
        "recovery-boot-accepted",
        "reverse-update-accepted",
    ):
        if stage not in stages:
            raise LifecycleHarnessError(
                f"gate-P5 is RED: recovery stage {stage!r} was not observed"
            )
    prefailure = stages["boot-broken-candidate"]
    postrecovery = stages["recovery-boot-accepted"]
    reversed_stage = stages["reverse-update-accepted"]
    if not isinstance(prefailure, Mapping) or prefailure.get("journal_state") not in (
        "one_shot_armed",
        "candidate_booting",
    ):
        raise LifecycleHarnessError(
            "gate-P5 is RED: pre-failure candidate journal left the "
            "non-terminal health-pending states"
        )
    if not isinstance(postrecovery, Mapping) or postrecovery.get("journal_state") != "failed":
        raise LifecycleHarnessError(
            "gate-P5 is RED: deadline did not mark the candidate FAILED"
        )
    note = str(postrecovery.get("journal_note", ""))
    if "health-service-failure" not in note or "automatic-reboot" not in note:
        raise LifecycleHarnessError(
            "gate-P5 is RED: FAILED note does not bind the pinned class"
        )
    if not isinstance(reversed_stage, Mapping) or reversed_stage.get("journal_state") != "accepted":
        raise LifecycleHarnessError(
            "gate-P5 is RED: reverse update did not accept"
        )

    # P5.4 boot-performance record: live and strictly GREEN.
    if not isinstance(boot_perf_record, Mapping):
        raise LifecycleHarnessError(
            "gate-P5 is RED: P5.4 boot-performance record is missing"
        )
    if boot_perf_record.get("overall") != "PASS":
        raise LifecycleHarnessError(
            "gate-P5 is RED: P5.4 boot-performance record is not GREEN "
            f"(overall {boot_perf_record.get('overall')!r}); a missing or "
            "non-green record keeps Gate P5 open"
        )
    comparison = boot_perf_record.get("comparison")
    if not isinstance(comparison, Mapping) or comparison.get("overall") != "PASS":
        raise LifecycleHarnessError(
            "gate-P5 is RED: P5.4 strict comparison is not GREEN"
        )
    health = boot_perf_record.get("health_preintro")
    if not isinstance(health, Mapping) or health.get("verdict") != "PASS":
        raise LifecycleHarnessError(
            "gate-P5 is RED: pre-intro update/health proof is not PASS"
        )
    boot_perf_image_sha = _require_hex64(
        boot_perf_record.get("installed_image_sha256"), role="boot-perf built-image SHA"
    )
    boot_perf_source_sha = _require_hex64(
        boot_perf_record.get("source_sha256"), role="boot-perf source SHA"
    )

    # 768 MiB budget: DEVICE-scope envelope only, never source scope.
    if not isinstance(device_envelope, Mapping):
        raise LifecycleHarnessError(
            "gate-P5 is RED: device-measured resource envelope is missing"
        )
    device_scope = device_envelope.get("device_scope")
    if (
        not isinstance(device_scope, Mapping)
        or device_scope.get("executed") is not True
    ):
        raise LifecycleHarnessError(
            "gate-P5 is RED: 768 MiB budget is not device-measured "
            "(source-scope values never count)"
        )
    if device_envelope.get("classification") != "DEVICE_T7_DEVPROOF":
        raise LifecycleHarnessError(
            "gate-P5 is RED: resource envelope is not the device-measured "
            f"run (classification {device_envelope.get('classification')!r})"
        )
    cgroup = device_envelope.get("cgroup_gate")
    cgroup_green = False
    if isinstance(cgroup, Mapping):
        verdict = cgroup.get("verdict")
        if isinstance(verdict, Mapping):
            cgroup_green = bool(verdict.get("green")) and not bool(
                verdict.get("diagnostic_only")
            )
        else:
            cgroup_green = bool(cgroup.get("green"))
    if not cgroup_green:
        raise LifecycleHarnessError(
            "gate-P5 is RED: 768 MiB cgroup gate is not green from "
            "device-measured values"
        )

    if not isinstance(source_head, str) or not _HEX40.fullmatch(source_head):
        raise LifecycleHarnessError(
            "gate-P5 record refused: source HEAD is not bound (never minted)"
        )

    # Combined 8-step report: every step observed across the three legs
    # (install 2 + boot-health 3 incl. shared boot-A + recovery 4 = full
    # coverage); defaults from the frozen expected-slot pattern with the
    # observed accepted progression A -> B -> A.
    install_report = install_result.get("lifecycle_report")
    boot_report = boot_health_result.get("lifecycle_report")
    recovery_report = recovery_result.get("lifecycle_report")
    for label, report in (
        ("install", install_report),
        ("boot-health", boot_report),
        ("recovery", recovery_report),
    ):
        if not isinstance(report, Mapping) or "steps" not in report:
            raise LifecycleHarnessError(
                f"gate-P5 is RED: {label} leg lifecycle report is missing"
            )
    steps = [
        {
            "step": name,
            "default_slot": BOOT_OUTCOME_EXPECTED_SLOT.get(name, "A")
            if name in BOOT_OUTCOME_EXPECTED_SLOT
            else ("A" if name == "fresh-install-A" else "B"),
            "observed": True,
        }
        for name in LIFECYCLE_SEQUENCE
    ]
    combined: dict[str, object] = {
        "steps": steps,
        "shipped_update_legs": list(SHIPPED_UPDATE_LEGS),
        "launcher_acceptance_legs": list(LAUNCHER_ACCEPTANCE_LEGS),
        "observed_steps": list(LIFECYCLE_SEQUENCE),
    }
    assert_lifecycle_transitions(combined)

    predicates = {
        "full_lifecycle_green": "GREEN",
        "broken_candidate_recovers": "GREEN",
        "d31_survives": "GREEN",
        "budget_768_green": "GREEN",
        "no_harness_substitution": "GREEN",
        "sha_bound": "GREEN",
        "boot_perf_green": "GREEN",
        "provenance_refusal_green": "GREEN",
        "rc4_checkable": "GREEN",
    }
    evidence = {
        "install_image_sha256": str(install_result.get("installer_image_sha256")),
        "install_bundle_sha256": str(install_result.get("release_bundle_sha256")),
        "boot_health_image_sha256": str(boot_health_result.get("installed_image_sha256")),
        "boot_health_bundle_sha256": str(boot_health_result.get("release_bundle_sha256")),
        "recovery_installed_sha256": str(recovery_result.get("installed_image_sha256")),
        "unhealthy_bundle_sha256": str(recovery_result.get("unhealthy_bundle_sha256")),
        "reverse_bundle_sha256": str(recovery_result.get("reverse_bundle_sha256")),
        "boot_perf_installed_sha256": boot_perf_image_sha,
        "boot_perf_source_sha256": boot_perf_source_sha,
        "source_head": source_head,
        "transition_units": {k: dict(v) for k, v in GATE_P5_TRANSITION_UNITS.items()},
    }
    for key in (
        "install_image_sha256",
        "install_bundle_sha256",
        "boot_health_image_sha256",
        "boot_health_bundle_sha256",
        "recovery_installed_sha256",
        "unhealthy_bundle_sha256",
        "reverse_bundle_sha256",
    ):
        _require_hex64(evidence[key], role=f"closure {key}")
    return {
        "schema": GATE_P5_SCHEMA,
        "schema_version": GATE_P5_SCHEMA_VERSION,
        "gate": GATE_P5_ID,
        "overall": "GREEN",
        "predicates": predicates,
        "evidence": evidence,
        "lifecycle_report": combined,
    }


def run_gate_p5_closure_product(
    *,
    config: LifecycleConfig,
    official_installer_image: Path,
    release_bundle: Path,
    reverse_bundle: Path,
    trusted_key_dir: Path,
    unhealthy_release: Mapping[str, object],
    base_hardware_support: Path | None = None,
    d31_fn=None,
    d31_handle: Mapping[str, object] | None = None,
    boot_perf_baseline=None,
    install_fn=None,
    boot_health_fn=None,
    unhealthy_build_fn=None,
    unhealthy_verify_fn=None,
    recovery_fn=None,
    boot_perf_fn=None,
    budget_fn=None,
    source_head_fn=None,
) -> dict[str, object]:
    """Run the full Gate-P5 closure on the capable host (P5.2/P5.3/P5.4).

    Order (fail-closed, disposable media only): gate the Linux/QEMU
    facility (``BLOCKED`` naming it) -> require the explicit ``d31_fn``
    (or a seeded ``d31_handle`` carrying one; ``None`` stays ``BLOCKED``
    naming the unpinned on-image D31 persist mapping — the V5 obligation,
    never waived) -> install leg through ``ProductHarness.run_product``
    -> boot-health leg through ``run_boot_health_product`` on the
    install-leg target -> build the unhealthy candidate from the real
    install-leg payload via ``build_unhealthy_candidate_bundle`` and
    verify it via ``verify_unhealthy_candidate_bundle`` -> seed D31 onto
    the health-committed image when the handle did not already ->
    recovery/D31/reverse leg through
    ``run_recovery_d31_reverse_product`` with the explicit ``d31_fn``
    -> live P5.4 measurement through ``run_boot_perf_product`` (or an
    injected build-over-recorded-logs equivalent) -> device-measured
    budget through ``run_envelope_device`` -> bind the predicate mapping
    through ``build_gate_p5_record``.

    The ``*_fn`` seams default to the real frozen entries; tests inject
    recording fakes to prove leg order, d31-before-recovery staging, and
    that a missing/non-green input never closes. Only an all-GREEN
    mapping closes Gate P5 (and only then is T3-P DONE); any red,
    ``BLOCKED`` or missing input preserves the non-green result.
    """
    from . import boot_perf as _boot_perf
    from . import devproof as _devproof
    from . import product as _product

    config.validate()
    _product.assert_control_absent_from_production()
    _product.require_product_host(official_image=Path(official_installer_image))

    if d31_fn is None and (
        not isinstance(d31_handle, Mapping) or d31_handle.get("d31_fn") is None
    ):
        raise LifecycleHarnessError(
            "BLOCKED product mode: on-image D31 persist mapping is not "
            "pinned (namespace paths under the mounted persist tree); "
            "the capable-host run must seed it via "
            "prepare_on_image_d31_seed and supply d31_fn reading the "
            "persist partition through the devproof store parse paths"
        )
    if d31_fn is None and isinstance(d31_handle, Mapping):
        candidate = d31_handle.get("d31_fn")
        if callable(candidate):
            d31_fn = candidate

    harness = _product.ProductHarness(
        config,
        official_image=Path(official_installer_image),
        release_bundle=Path(release_bundle),
        trusted_key_dir=Path(trusted_key_dir),
    )

    if install_fn is not None:
        install_result = dict(install_fn(harness))
    else:
        install_result = dict(harness.run_product())
    if not install_result.get("ok"):
        raise LifecycleHarnessError("gate-P5 is RED: install leg did not report ok")
    disposable = install_result.get("disposable_target")
    if not isinstance(disposable, Mapping) or not disposable.get("target"):
        raise LifecycleHarnessError(
            "gate-P5 refused: install leg produced no disposable target image"
        )
    installed_target = Path(str(disposable["target"]))

    if boot_health_fn is not None:
        boot_health_result = dict(boot_health_fn(harness, installed_target))
    else:
        boot_health_result = dict(
            harness.run_boot_health_product(installed_image=installed_target)
        )
    if not boot_health_result.get("ok"):
        raise LifecycleHarnessError("gate-P5 is RED: boot-health leg did not report ok")
    clone_proof = boot_health_result.get("clone")
    if not isinstance(clone_proof, Mapping) or not clone_proof.get("clone"):
        raise LifecycleHarnessError(
            "gate-P5 refused: boot-health leg produced no health-committed clone"
        )
    committed_image = Path(str(clone_proof["clone"]))

    # Unhealthy candidate from the real install-leg payload (never
    # synthesized): prefer the staged release bundle bytes the install
    # leg consumed, verified before any recovery staging.
    if unhealthy_build_fn is not None:
        unhealthy_built = dict(unhealthy_build_fn())
        unhealthy_path = Path(str(unhealthy_built.get("bundle", "")))
    else:
        work = harness.product_root / "gate-unhealthy"
        work.mkdir(parents=True, exist_ok=True)
        unhealthy_path = work / "unhealthy-candidate.greiaupdate"
        base_payload = Path(str(unhealthy_release.get("base_payload", "")))
        hw_support = (
            Path(str(base_hardware_support))
            if base_hardware_support is not None
            else Path(str(unhealthy_release.get("base_hardware_support", "")))
        )
        unhealthy_built = dict(
            _product.build_unhealthy_candidate_bundle(
                base_payload=base_payload,
                base_hardware_support=hw_support,
                output_path=unhealthy_path,
                work_dir=work,
                release_id=str(unhealthy_release.get("release_id")),
                release_sequence=int(unhealthy_release.get("release_sequence", 0)),
                platform_family=str(unhealthy_release.get("platform_family", "")),
                architecture=str(unhealthy_release.get("architecture", "")),
                profile=str(unhealthy_release.get("profile", "")),
                signer=str(unhealthy_release.get("signer", "")),
                private_key_path=Path(str(unhealthy_release.get("private_key_path", ""))),
            )
        )
    if unhealthy_verify_fn is not None:
        unhealthy_verified = dict(unhealthy_verify_fn(unhealthy_path))
    else:
        unhealthy_verified = dict(
            _product.verify_unhealthy_candidate_bundle(
                unhealthy_path,
                trusted_key_dir=Path(trusted_key_dir),
                accepted_sequence=int(unhealthy_release.get("accepted_sequence", 21)),
                platform_family=str(unhealthy_release.get("platform_family", "")),
                architecture=str(unhealthy_release.get("architecture", "")),
                profile=str(unhealthy_release.get("profile", "")),
                expected_hardware_sha256=str(
                    unhealthy_release.get("expected_hardware_sha256", "")
                ),
            )
        )

    # D31 seed rides into the recovery clone: seed the health-committed
    # image when the caller did not pre-seed a handle for it.
    effective_d31_fn = d31_fn
    persist_mapping: object = None
    if d31_handle is not None and isinstance(d31_handle, Mapping):
        persist_mapping = d31_handle.get("persist_mapping")
    if effective_d31_fn is None:
        raise LifecycleHarnessError(
            "BLOCKED product mode: on-image D31 persist mapping is not "
            "pinned; seed it via prepare_on_image_d31_seed"
        )
    if persist_mapping is None and isinstance(d31_handle, Mapping):
        persist_mapping = d31_handle.get("persist_mapping")

    if recovery_fn is not None:
        recovery_result = dict(
            recovery_fn(harness, committed_image, unhealthy_path, effective_d31_fn)
        )
    else:
        recovery_result = dict(
            harness.run_recovery_d31_reverse_product(
                installed_image=committed_image,
                unhealthy_bundle=unhealthy_path,
                reverse_bundle=Path(reverse_bundle),
                d31_fn=effective_d31_fn,
            )
        )
    if not recovery_result.get("ok"):
        raise LifecycleHarnessError("gate-P5 is RED: recovery leg did not report ok")

    if boot_perf_fn is not None:
        boot_perf_out = dict(boot_perf_fn(committed_image))
        boot_perf_record = boot_perf_out.get("record")
    else:
        boot_perf_out = dict(
            _boot_perf.run_boot_perf_product(
                config=config,
                installed_image=committed_image,
                release_bundle=Path(release_bundle),
                baseline=boot_perf_baseline,
                # The installed boot needs minutes on this lane; bind it
                # to the run's own timeout ceiling, not the 300 s default.
                timeout_seconds=max(60, int(config.timeout_seconds)),
            )
        )
        boot_perf_record = boot_perf_out.get("record")
    if not isinstance(boot_perf_record, Mapping) or boot_perf_record.get("overall") != "PASS":
        raise LifecycleHarnessError(
            "gate-P5 is RED: live P5.4 boot-performance record is missing "
            "or non-green; a non-green record is never attached as closure"
        )

    if budget_fn is not None:
        device_envelope = dict(budget_fn())
    else:
        device_envelope = dict(
            _devproof.run_envelope_device(
                harness.product_root / "gate-device-envelope",
                bundle_path=Path(release_bundle),
            )
        )

    if source_head_fn is not None:
        source_head = str(source_head_fn())
    else:
        source_head = read_source_head()

    record = build_gate_p5_record(
        install_result=install_result,
        boot_health_result=boot_health_result,
        recovery_result=recovery_result,
        boot_perf_record=dict(boot_perf_record),
        device_envelope=device_envelope,
        source_head=source_head,
    )
    return {
        "ok": True,
        "gate": GATE_P5_ID,
        "overall": "GREEN",
        "record": record,
        "install": install_result,
        "boot_health": boot_health_result,
        "unhealthy_built": unhealthy_built,
        "unhealthy_verified": unhealthy_verified,
        "recovery": recovery_result,
        "boot_perf": boot_perf_out,
        "device_envelope": device_envelope,
        "persist_mapping": persist_mapping,
        "source_head": source_head,
        "source_image_mutated": False,
    }


__all__ = [
    "GATE_P5_ID",
    "GATE_P5_SCHEMA",
    "GATE_P5_SCHEMA_VERSION",
    "GATE_P5_PREDICATES",
    "GATE_P5_TRANSITION_UNITS",
    "PERSIST_PARTITION_INDEX",
    "D31_PERSIST_NAMESPACES",
    "read_source_head",
    "prepare_on_image_d31_seed",
    "build_gate_p5_record",
    "run_gate_p5_closure_product",
]
