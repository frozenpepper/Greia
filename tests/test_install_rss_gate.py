"""T2-STREAM: RSS-level gate for the streaming install path (D33).

Preregistered acceptance (frozen before observation):
- R1 streaming consume of a 32 MiB payload via ``open_bundle_payload_stream``
  peaks far below payload scale (< 96 MiB process RSS including the
  interpreter baseline), while the legacy whole-buffering control
  (``ZipFile.read -> BytesIO``) peaks at payload scale (>= 32 MiB).
- R2 streaming peak does not scale ~1:1 with payload: |peak(32MiB) -
  peak(8MiB)| < 8 MiB.
- R3 whole-path ``execute_fresh_ab_install`` (verify, slot write, readback,
  finalize, PERSIST, GRUB, journal) with file-backed storage peaks below
  128 MiB process RSS at 32 MiB payload and writes every payload byte.

Each mode runs in a CHILD process so the peak is attributed per mode.
On Linux the child peak is read from ``VmHWM`` in ``/proc/self/status``:
``RUSAGE_SELF.ru_maxrss`` is inherited across fork+exec, so a child
spawned after the parent builds payload bundles would report the
parent's high-water mark instead of its own cost (device-measured
T04-FIX-RSS: an identical streaming child reads 18.37 MiB from a lean
parent vs 108.47 MiB from a +100 MiB parent, while ``VmHWM`` reads
7.84 vs 8.05 MiB — stable). ``VmHWM`` resets at exec, so it attributes
only the child. macOS keeps the ``ru_maxrss``-in-bytes path (no
``/proc``, no such inheritance). Linux without ``/proc`` falls back to
``ru_maxrss``. This is the permanent
CI mirror of the 768 MiB cgroup gate evidence (384 MiB payload, disposable
install+update, swap off) recorded in the T2-STREAM fixer report: it fails
if whole-buffering is reintroduced into the production seam.
"""

from __future__ import annotations

import json
import os
import resource
import shutil
import subprocess
import sys
import tempfile
import unittest
import uuid
import zipfile
from io import BytesIO
from pathlib import Path

import test_install_streaming_memory as stream_mod
from greia_installer.fresh_ab_install import execute_fresh_ab_install
from greia_installer.fresh_ab_install import (
    FreshAbInstallRequest,
    FreshAbInstallSeams,
    open_bundle_payload_stream,
)
from greia_platform.system_updates import PAYLOAD_NAME, inspect_update_bundle

MIB = 1024 * 1024
GIB = 1024 * 1024 * 1024
_SMALL = 8 * MIB
_LARGE = 32 * MIB

_STREAM_RSS_BOUND = 96 * MIB
_WHOLE_PATH_RSS_BOUND = 128 * MIB
# Non-scaling bound: half the 24 MiB payload delta. A ~1:1 scaling defect
# would add ~24 MiB; both peaks sit on a ~35 MiB interpreter baseline with
# a few MiB of allocator noise (observed run-to-run jitter up to ~9 MiB),
# so the bound must clear noise while still catching payload-scale growth.
_NONSCALE_BOUND = 12 * MIB


def _peak_rss_bytes() -> int:
    """Return this child process's own post-exec peak RSS in bytes.

    See the module docstring: on Linux ``VmHWM`` is the attribution
    source because ``ru_maxrss`` inherits the spawner's high-water mark
    across fork+exec.
    """
    if sys.platform != "darwin":
        try:
            with open("/proc/self/status", "r", encoding="utf-8") as handle:
                for line in handle:
                    if line.startswith("VmHWM:"):
                        return int(line.split()[1]) * 1024
        except OSError:
            pass
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform == "darwin":
        return int(peak)
    return int(peak) * 1024


def _consume(bundle: Path, kind: str) -> int:
    if kind == "stream":
        stream = open_bundle_payload_stream(bundle)
        total = 0
        try:
            while True:
                piece = stream.read(64 * 1024)
                if not piece:
                    break
                total += len(piece)
        finally:
            stream.close()
        return total
    with zipfile.ZipFile(bundle, "r") as archive:
        data = archive.read(PAYLOAD_NAME)
    stream = BytesIO(data)
    total = 0
    while True:
        piece = stream.read(64 * 1024)
        if not piece:
            break
        total += len(piece)
    stream.close()
    return total


def _whole_install(bundle: Path, key_dir: Path, case: Path) -> int:
    manifest = inspect_update_bundle(bundle).manifest
    observed = stream_mod._observed_mbr_identities()
    persist_stage = case / "persist-stage"
    persist_stage.mkdir(parents=True, exist_ok=True)
    boot_control = case / "boot-control"
    backend_state = case / "backend-state"
    journal = case / "journal"
    mount_dir = case / "mnt"
    for directory_path in (boot_control, backend_state, journal):
        directory_path.mkdir(parents=True, exist_ok=True)
    storage = stream_mod.LoopbackSlotFile.create(case / "slot-a.bin", 1 * GIB)
    try:
        seams = FreshAbInstallSeams(
            partition_runner=stream_mod.RecordingPartitionRunner(),
            slot_storage_factory=lambda _role: storage,
            slot_filesystem_factory=lambda: stream_mod.FakeSlotFilesystem(
                mount_dir
            ),
            package_installer_factory=stream_mod.FakePackageInstaller,
            inventory_token="cd" * 32,
            support_digest=manifest.hardware_support_sha256,
            support_size=manifest.hardware_support_size,
            support_installed_bound=stream_mod._SUPPORT_BOUND,
            persist_runner=stream_mod.FakePersistRunner(
                readback_uuid=observed["persist"]["filesystem_uuid"]
            ),
            persist_stage_dir=persist_stage,
            persist_uuid_factory=lambda: uuid.UUID(
                observed["persist"]["filesystem_uuid"]
            ),
            boot_control_dir=boot_control,
            backend_state_dir=backend_state,
            journal_dir=journal,
            post_layout_identity_observer=lambda target, plan: observed,
        )
        request = FreshAbInstallRequest(
            bundle_path=bundle,
            trusted_key_dir=key_dir,
            expected_profile_id=stream_mod._PROFILE,
            expected_platform_family=stream_mod._FAMILY,
            expected_architecture=stream_mod._ARCH,
            sizing=stream_mod._sizing(),
            target=stream_mod._target(),
            support_installed_bytes=stream_mod._SUPPORT_BOUND,
            install_target_sha256=stream_mod._INSTALL_SHA,
            password_hash=stream_mod._PASSWORD_HASH,
            installed_at_unix=1757000000,
        )
        result = execute_fresh_ab_install(request, seams)
        return int(result.bytes_written)
    finally:
        storage.close()


def _child_main() -> int:
    mode = sys.argv[2]
    bundle = Path(sys.argv[3])
    if mode in ("consume-stream", "consume-buffered"):
        kind = mode.split("-", 1)[1]
        total = _consume(bundle, kind)
        print("RESULT " + json.dumps({"total": total}), flush=True)
    elif mode == "whole-stream":
        key_dir = Path(sys.argv[4])
        case = Path(sys.argv[5])
        written = _whole_install(bundle, key_dir, case)
        print("RESULT " + json.dumps({"written": written}), flush=True)
    else:
        raise ValueError(f"unknown child mode {mode}")
    print("RSS " + json.dumps({"peak_rss_bytes": _peak_rss_bytes()}), flush=True)
    return 0


def _run_child(args: list[str]) -> tuple[int, int]:
    repo = Path(__file__).resolve().parents[1]
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(repo / "src"), str(repo / "tests"), env.get("PYTHONPATH", "")]
    )
    proc = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "child", *args],
        capture_output=True,
        text=True,
        timeout=600,
        env=env,
        cwd=str(repo),
    )
    total_or_written = 0
    peak = 0
    for line in proc.stdout.splitlines():
        if line.startswith("RESULT "):
            payload = json.loads(line[len("RESULT "):])
            total_or_written = int(payload.get("total", payload.get("written", 0)))
        elif line.startswith("RSS "):
            peak = int(json.loads(line[len("RSS "):])["peak_rss_bytes"])
    if proc.returncode != 0 or peak <= 0:
        raise AssertionError(
            f"gate child failed mode={args[0]} rc={proc.returncode} "
            f"stderr={proc.stderr[-1500:]}"
        )
    return total_or_written, peak


class InstallRssGateTests(unittest.TestCase):
    """R1/R2/R3: RSS-level streaming proof with a sensitive control."""

    def test_streaming_rss_bounded_control_payload_scale(self) -> None:
        directory = tempfile.mkdtemp(prefix="t2-rss-gate-")
        self.addCleanup(shutil.rmtree, directory, True)
        root = Path(directory)
        small_bundle, _ = stream_mod._build_bundle(
            root, stream_mod._payload(_SMALL), sequence=91
        )
        large_bundle, _ = stream_mod._build_bundle(
            root, stream_mod._payload(_LARGE), sequence=92
        )
        small_total, small_stream = _run_child(
            ["consume-stream", str(small_bundle)]
        )
        self.assertEqual(small_total, _SMALL)
        large_total, large_stream = _run_child(
            ["consume-stream", str(large_bundle)]
        )
        self.assertEqual(large_total, _LARGE)
        buffered_total, large_buffered = _run_child(
            ["consume-buffered", str(large_bundle)]
        )
        self.assertEqual(buffered_total, _LARGE)
        self.assertLess(
            large_stream,
            _STREAM_RSS_BOUND,
            f"streaming RSS {large_stream} exceeds bound for 32MiB payload",
        )
        self.assertGreaterEqual(
            large_buffered,
            _LARGE,
            f"positive control RSS {large_buffered} does not reach payload scale",
        )
        self.assertLess(
            abs(large_stream - small_stream),
            _NONSCALE_BOUND,
            f"streaming RSS scales with payload: 8MiB={small_stream} 32MiB={large_stream}",
        )

    def test_whole_path_rss_bounded(self) -> None:
        directory = tempfile.mkdtemp(prefix="t2-rss-whole-")
        self.addCleanup(shutil.rmtree, directory, True)
        root = Path(directory)
        bundle, key_dir = stream_mod._build_bundle(
            root, stream_mod._payload(_LARGE), sequence=93
        )
        case = root / "case"
        case.mkdir()
        written, peak = _run_child(
            ["whole-stream", str(bundle), str(key_dir), str(case)]
        )
        self.assertEqual(written, _LARGE)
        self.assertLess(
            peak,
            _WHOLE_PATH_RSS_BOUND,
            f"whole-path RSS {peak} exceeds bound for 32MiB payload",
        )


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "child":
        raise SystemExit(_child_main())
    unittest.main()
