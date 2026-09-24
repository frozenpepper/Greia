#!/usr/bin/env python3
"""Session 04 QEMU lifecycle driver (disposable /tmp state only).

One leg per invocation: ``sudo python3 /tmp/s04driver.py <leg>``.
Legs chain through result JSON in $SESSION04/results; every input is a
prior leg's disposable output, never synthesized. All QEMU/loop/mount
contact stays on disposable regular files under /tmp.
"""

import json
import os
import sys
from pathlib import Path

REPO = Path("/home/orb/Works/Greia")
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "tests"))

HEAD_SHA = os.environ.get("S04_HEAD", "45c3d283717372cebd2636db860fc162f752f1ee")
SESSION04 = Path(os.environ.get("SESSION04", f"/tmp/greia-session04-{HEAD_SHA}"))
S03_SHA = "6c58601eaad32ad2bba30acb24e33333b9c4bbf3"
VERSION = "0.13.0-phase0-dev"

S03 = REPO / f"tmp/session03-linux-release-{S03_SHA}/out/greia-{VERSION}"
S03_BUNDLE = S03 / "updates/acer-aspire-one-i386-ab.greiaupdate"
S03_REL = "greia-0.13.0-phase0-dev"

S04B_REL = "greia-0.13.0-s04-b"
S04BROKEN_REL = "greia-0.13.0-s04-broken"
S04NB_REL = "greia-0.13.0-s04-nonboot"

CAND = SESSION04 / "candidates"
S04B = CAND / "s04-b.greiaupdate"
S04BROKEN = CAND / "s04-broken.greiaupdate"
S04NB = CAND / "s04-nonboot.greiaupdate"
S04P99 = CAND / "s04-persist99.greiaupdate"

RESULTS = SESSION04 / "results"


def _jsonable(value):
    if isinstance(value, Mapping):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, Path):
        return str(value)
    return value


try:
    from collections.abc import Mapping
except ImportError:  # pragma: no cover
    from collections import Mapping  # type: ignore[no-redef]


def _save(name: str, result: dict) -> Path:
    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / f"{name}.json"
    out.write_text(json.dumps(_jsonable(result), indent=2, sort_keys=True) + "\n")
    print(f"leg {name}: ok={result.get('ok')} -> {out}", flush=True)
    return out


def _load(name: str) -> dict:
    path = RESULTS / f"{name}.json"
    if not path.is_file():
        raise SystemExit(f"s04driver: missing prior leg result {path}")
    return json.loads(path.read_text())


def _harness():
    from tools.x8_qemu.lifecycle import LifecycleConfig
    from tools.x8_qemu.product import ProductHarness

    run_root = sorted(SESSION04.glob("installer")) or sorted(Path("/tmp").glob("greia-session04-*"))
    head_installer = (
        Path(f"/tmp/greia-session04-{HEAD_SHA}")
        / "installer/greia-os-installer-acer-aspire-one-i386-ab.img"
    )
    if head_installer.is_file():
        installer = head_installer
    else:
        installer_imgs = sorted(
            Path("/tmp").glob("greia-session04-*/installer/greia-os-installer-acer-aspire-one-i386-ab.img"),
            key=lambda p: p.stat().st_mtime,
        )
        if not installer_imgs:
            raise SystemExit("s04driver: no installer image found under /tmp/greia-session04-*/installer")
        installer = installer_imgs[-1]
    print(f"installer: {installer}", flush=True)
    config = LifecycleConfig(
        output_dir=SESSION04 / "s04legs",
        timeout_seconds=int(os.environ.get("S04_QEMU_TIMEOUT", "3600")),
        memory_mib=2048,
        cpus=2,
    )
    return ProductHarness(
        config, official_image=installer, release_bundle=S03_BUNDLE
    )


def leg_install() -> None:
    harness = _harness()
    result = harness.run_product()
    _save("install", result)
    target = result["disposable_target"]["target"]
    print(f"install target: {target}", flush=True)


def leg_firstboot() -> None:
    install = _load("install")
    target = Path(str(install["disposable_target"]["target"]))
    harness = _harness()
    result = harness.run_first_boot_product(
        installed_image=target,
        release_bundle=S03_BUNDLE,
        expected_release_id=S03_REL,
    )
    _save("firstboot", result)
    print(f"firstboot clone: {result['clone']['clone']}", flush=True)
    print(f"observed: {result['observed']}", flush=True)


def leg_seed() -> None:
    from tools.x8_qemu.gate_p5 import prepare_on_image_d31_seed

    firstboot = _load("firstboot")
    clone = Path(str(firstboot["clone"]["clone"]))
    work = SESSION04 / "d31"
    work.mkdir(parents=True, exist_ok=True)
    seeded = prepare_on_image_d31_seed(
        installed_image=clone, recovery_clone=clone, work_dir=work
    )
    saved = {
        "seeded_image": str(clone),
        "persist_mapping": seeded.get("persist_mapping"),
        "semantic_before": seeded.get("semantic_before"),
        "bytes_before": seeded.get("bytes_before"),
    }
    _save("seed", saved)
    print(f"seeded {clone}", flush=True)


def _read_persist_state(clone: Path) -> dict:
    import tempfile as _tempfile

    from greia_installer.disk import partition_number_path
    from tools.x8_qemu import devproof as _devproof
    from tools.x8_qemu.product import (
        _loop_attach_partscan,
        _loop_detach,
        _mount_fs,
        _umount_fs,
        snapshot_persist_tree,
    )

    mnt = Path(_tempfile.mkdtemp(prefix="s04-persist-"))
    loopdev = ""
    try:
        loopdev = _loop_attach_partscan(clone)
        node = str(partition_number_path(Path(loopdev), 4))
        _mount_fs(node, mnt, read_only=True)
        semantic = _devproof.read_d31_representative_state(mnt)
        snap = snapshot_persist_tree(mnt)
        return {"semantic": semantic, "bytes": snap}
    finally:
        try:
            _umount_fs(mnt)
        except Exception:
            pass
        if loopdev:
            try:
                _loop_detach(loopdev)
            except Exception:
                pass
        import shutil

        shutil.rmtree(mnt, ignore_errors=True)


def leg_check_persist(name: str, clone_key: str = "clone") -> None:
    from tools.x8_qemu import devproof as _devproof

    seed = _load("seed")
    leg = _load(name)
    clone = Path(str(leg[clone_key]["clone"]))
    after = _read_persist_state(clone)
    semantic_ok = bool(
        _devproof.verify_d31_rollback(seed["semantic_before"], after["semantic"])
    )
    before_files = dict(seed["bytes_before"])
    after_files = dict(after["bytes"])
    drifted = sorted(
        k for k in set(before_files) & set(after_files) if before_files[k] != after_files[k]
    )
    missing = sorted(set(before_files) - set(after_files))
    extra = sorted(set(after_files) - set(before_files))
    result = {
        "leg": name,
        "clone": str(clone),
        "semantic_preserved": semantic_ok,
        "byte_identical": not (drifted or missing or extra),
        "drifted": drifted,
        "missing": missing,
        "extra": extra,
    }
    _save(f"persist-after-{name}", result)
    print(json.dumps(result, indent=2, sort_keys=True), flush=True)


def leg_update() -> None:
    firstboot = _load("firstboot")
    clone = Path(str(firstboot["clone"]["clone"]))
    assert S04B.is_file(), f"missing candidate {S04B}"
    harness = _harness()
    result = harness.run_boot_health_product(
        installed_image=clone,
        release_bundle=S04B,
        expected_release_id_b=S04B_REL,
    )
    _save("update", result)
    print(f"update clone: {result['clone']['clone']}", flush=True)
    print(f"observed: {result['observed']}", flush=True)
    print(f"isolation: {result['slot_isolation']}", flush=True)


def leg_unhealthy() -> None:
    update = _load("update")
    clone = Path(str(update["clone"]["clone"]))
    assert S04BROKEN.is_file(), f"missing candidate {S04BROKEN}"
    harness = _harness()
    result = harness.run_userspace_failure_product(
        installed_image=clone,
        unhealthy_bundle=S04BROKEN,
        accepted_slot="B",
        accepted_release_id=S04B_REL,
        candidate_release_id=S04BROKEN_REL,
    )
    _save("unhealthy", result)
    print(f"unhealthy clone: {result['clone']['clone']}", flush=True)
    print(f"stages: {json.dumps(result['stages'], indent=2, sort_keys=True)}", flush=True)


def leg_nonboot() -> None:
    unhealthy = _load("unhealthy")
    clone = Path(str(unhealthy["clone"]["clone"]))
    assert S04NB.is_file(), f"missing candidate {S04NB}"
    harness = _harness()
    result = harness.run_nonboot_failure_product(
        installed_image=clone,
        nonboot_bundle=S04NB,
        accepted_slot="B",
        accepted_release_id=S04B_REL,
        candidate_release_id=S04NB_REL,
        attempt_timeout_seconds=300,
    )
    _save("nonboot", result)
    print(f"nonboot clone: {result['clone']['clone']}", flush=True)
    print(f"attempt: {result['attempt']}", flush=True)
    print(f"reset: {json.dumps(result['reset'], indent=2, sort_keys=True)}", flush=True)


def leg_persist() -> None:
    nonboot = _load("nonboot")
    clone = Path(str(nonboot["clone"]["clone"]))
    assert S04P99.is_file(), f"missing candidate {S04P99}"
    harness = _harness()
    result = harness.run_persist_refusal_product(
        installed_image=clone,
        refused_bundle=S04P99,
        accepted_slot="B",
        accepted_release_id=S04B_REL,
    )
    _save("persist", result)
    print(f"persist clone: {result['clone']['clone']}", flush=True)
    print(f"journal: {result['journal_before']} -> {result['journal_after']}", flush=True)


LEGS = {
    "install": leg_install,
    "firstboot": leg_firstboot,
    "seed": leg_seed,
    "update": leg_update,
    "unhealthy": leg_unhealthy,
    "nonboot": leg_nonboot,
    "persist": leg_persist,
}


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] not in LEGS and not argv[1].startswith("check-persist:"):
        print(f"usage: s04driver.py [{'|'.join(sorted(LEGS))}|check-persist:<leg>]", flush=True)
        return 2
    if argv[1].startswith("check-persist:"):
        leg_check_persist(argv[1].split(":", 1)[1])
        return 0
    LEGS[argv[1]]()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
