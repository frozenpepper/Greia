"""T03: one stage streams the candidate support member exactly once.

Proves, through the real production seams
(``_production_support_set_factory`` -> ``CandidateSupportStage`` ->
``VerifiedHardwareSupportPool.load`` -> ``pool_to_support_set`` ->
``resolve_hardware_selection`` -> ``_LazyTargetPackageInstaller`` ->
``InstallerSlotPackageInstaller`` / ``TargetHardwareSupportInstaller``):

- candidate X's pool wins over running pool Y;
- an X-only package installs through the real factory/selection/install
  path (only command execution is faked; no SSH/mount/flash, no APT);
- one stage causes exactly one streaming extraction with no intermediate
  compressed temp file, and the resolver pool identity/root equals the
  installer pool identity/root (same stage-owned pool instance);
- digest/size mismatch is rejected (at inspection and at staging time,
  when the candidate changed after inspection);
- the absent-support path extracts nothing and creates no staging dir;
- temp staging is removed on success, on selection failure, and on
  installation failure;
- insufficient PERSIST space refuses before extraction;
- a support-carrying candidate fitting the shared finalized-slot formula
  stages while one exceeding it is refused before slot mutation;
- the running pool cannot satisfy an X-only requirement.

All state stays in disposable tmpdirs; no valued disk is touched.
"""

from __future__ import annotations

import hashlib
import io
import json
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from greia_platform import system_updates as _updates
from greia_platform import candidate_support as _candidate_support
from greia_platform.candidate_support import (
    MAX_CANDIDATE_SUPPORT_COMPRESSED_BYTES,
    STAGING_OPERATING_RESERVE_BYTES,
    CandidateSupportStage,
)
from greia_platform.system_updates import (
    HARDWARE_SUPPORT_NAME,
    SystemUpdateInbox,
    UpdateBackendUnavailable,
    UpdateBundleError,
    build_production_update_seams,
    build_update_bundle,
)


_FAMILY = "t04test"
_ARCH = "t04arch"
_PROFILE = "t04profile"

_X_FIRMWARE = "firmware-xonly"
_X_MICROCODE = "xonly-microcode"
_Y_FIRMWARE = "firmware-yonly"
_Y_MICROCODE = "yonly-microcode"


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _pool_tree(
    root: Path,
    *,
    name: str,
    firmware: str,
    microcode: str,
) -> Path:
    """Write a minimal verified hardware-support pool with X/Y identity."""
    fw = f"t04-{name}-firmware-bytes".encode()
    uc = f"t04-{name}-microcode-bytes".encode()
    pool = root / f"pool-{name}"
    deb_dir = pool / "pool"
    deb_dir.mkdir(parents=True)
    fw_name = f"{firmware}_1_all.deb"
    uc_name = f"{microcode}_1_amd64.deb"
    (deb_dir / fw_name).write_bytes(fw)
    (deb_dir / uc_name).write_bytes(uc)
    packages_payload = f"Package: {firmware}\n".encode()
    packages_gzip_payload = b"gzip-placeholder"
    (pool / "Packages").write_bytes(packages_payload)
    (pool / "Packages.gz").write_bytes(packages_gzip_payload)
    manifest = {
        "schema_version": 1,
        "suite": "trixie",
        "architecture": "amd64",
        "package_count": 2,
        "total_bytes": len(fw) + len(uc),
        "total_installed_bytes": len(fw) + len(uc) + 2 * 32 * 1024,
        "provided_candidate_packages": [firmware, microcode],
        "provided_firmware_packages": [firmware],
        "provided_microcode_packages": [microcode],
        "broad_firmware_packages": [firmware],
        "firmware_providers": {"x-firmware.bin": [firmware]},
        "unavailable_candidate_packages": [],
        "packages": [
            {
                "package": firmware, "version": "1",
                "architecture": "all", "filename": f"pool/{fw_name}",
                "size": len(fw), "sha256": _sha(fw), "candidate": True,
                "installed_bytes": len(fw) + 32 * 1024,
            },
            {
                "package": microcode, "version": "1",
                "architecture": "amd64", "filename": f"pool/{uc_name}",
                "size": len(uc), "sha256": _sha(uc), "candidate": True,
                "installed_bytes": len(uc) + 32 * 1024,
            },
        ],
        "repository_indexes": {
            "Packages": {"size": len(packages_payload), "sha256": _sha(packages_payload)},
            "Packages.gz": {
                "size": len(packages_gzip_payload),
                "sha256": _sha(packages_gzip_payload),
            },
        },
    }
    (pool / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return pool


def _hw_archive(pool_dir: Path, output: Path) -> bytes:
    """Deterministic tar.zst of a pool tree (mirrors tools/build_release)."""
    import zstandard

    members = [pool_dir / "manifest.json", pool_dir / "Packages", pool_dir / "Packages.gz"]
    members.extend(sorted((pool_dir / "pool").glob("*.deb")))
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w", format=tarfile.PAX_FORMAT) as tar:
        for member in sorted(members, key=lambda p: p.relative_to(pool_dir).as_posix()):
            arcname = member.relative_to(pool_dir).as_posix()
            info = tar.gettarinfo(str(member), arcname=arcname)
            info.uid = 0
            info.gid = 0
            info.uname = ""
            info.gname = ""
            info.mtime = 0
            info.mode = 0o644
            with member.open("rb") as src:
                tar.addfile(info, src)
    compressed = zstandard.ZstdCompressor(level=3).compress(buffer.getvalue())
    output.write_bytes(compressed)
    return compressed


def _payload_bytes(tag: bytes, size: int = 64 * 1024) -> bytes:
    body = bytes((index * 31 + 7) % 256 for index in range(size - len(tag)))
    return tag + body


def _candidate_bundle(
    root: Path,
    raw: bytes,
    *,
    name: str = "candidate.greiaupdate",
    hw_path: Path | None,
    release_id: str = "greia-t04",
    minimum_slot_bytes: int | None = None,
) -> Path:
    import zstandard

    work = root / f"release-{name}"
    work.mkdir(parents=True, exist_ok=True)
    payload_path = work / "slot.ext4.zst"
    payload_path.write_bytes(zstandard.ZstdCompressor(level=3).compress(raw))
    bundle = work / name
    if bundle.exists():
        bundle.unlink()
    build_update_bundle(
        payload_path=payload_path,
        hardware_support_path=hw_path,
        output_path=bundle,
        version="0.99.0",
        release_id=release_id,
        platform_family=_FAMILY,
        architecture=_ARCH,
        profile=_PROFILE,
        payload_uncompressed_bytes=len(raw),
        minimum_slot_bytes=minimum_slot_bytes if minimum_slot_bytes is not None else len(raw),
        persist_read_schema_min=1,
        persist_read_schema_max=1,
        persist_write_schema=1,
        release_notes="T04 candidate-support proof release.",
    )
    return bundle


def _rig(root: Path):
    """Production support/installer factories over disposable state."""
    state_dir = root / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    layout_path = root / "installed-layout.json"
    layout_path.write_text("{}\n", encoding="utf-8")
    seams = build_production_update_seams(
        layout_record_path=layout_path, state_dir=state_dir
    )
    return seams, state_dir


class _FakeCommandAdapter:
    """Records owned command arrays; executes nothing (no mount/APT)."""

    def __init__(self, commands: list[list[str]]) -> None:
        self._commands = commands

    def run(self, command: object, *, check: bool = True) -> object:
        self._commands.append(list(command))  # type: ignore[arg-type]
        return SimpleNamespace(returncode=0, stdout="", stderr="")


class _FakeTracker:
    def __init__(self, mountpoint: Path) -> None:
        self._mountpoint = mountpoint

    @property
    def current_mountpoint(self) -> Path:
        return self._mountpoint


def _staging_names(state_dir: Path) -> list[str]:
    parent = state_dir / "system-updates" / "candidate-support"
    if not parent.is_dir():
        return []
    return sorted(p.name for p in parent.iterdir())


def _staging_parent(state_dir: Path) -> Path:
    return state_dir / "system-updates" / "candidate-support"


def _assert_no_compressed_tmp_file(state_dir: Path) -> None:
    """No stage may ever leave the retired intermediate compressed file."""
    parent = _staging_parent(state_dir)
    if not parent.is_dir():
        return
    leftovers = list(parent.rglob(".hardware-support.tar.zst.tmp"))
    assert leftovers == [], f"intermediate compressed temp file escaped: {leftovers}"


class _ExtractionCounter:
    """Counts streaming tree-member extractions (not metadata inspection)."""

    def __init__(self) -> None:
        self.count = 0
        self._real = _candidate_support._extract_one

    def __call__(self, tar: object, member: object, **kwargs: object) -> object:
        self.count += 1
        return self._real(tar, member, **kwargs)  # type: ignore[arg-type]

    def patch(self) -> object:
        return mock.patch.object(_candidate_support, "_extract_one", self)


class CandidateWinsTests(unittest.TestCase):
    """Candidate X's pool wins over running pool Y (real factories)."""

    def test_candidate_pool_wins_over_running_pool(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pool_x = _pool_tree(root, name="x", firmware=_X_FIRMWARE, microcode=_X_MICROCODE)
            pool_y = _pool_tree(root, name="y", firmware=_Y_FIRMWARE, microcode=_Y_MICROCODE)
            _ = pool_y  # running pool exists on disk but is never consulted
            hw_path = root / "hw-x.tar.zst"
            hw_bytes = _hw_archive(pool_x, hw_path)
            raw = _payload_bytes(b"t04-x:")
            bundle = _candidate_bundle(root, raw, hw_path=hw_path)
            inspected = SystemUpdateInbox(root / "state").receive(bundle)
            seams, state_dir = _rig(root)
            counter = _ExtractionCounter()
            try:
                with counter.patch():
                    support = seams.support_set_factory(inspected)
                    first_count = counter.count
                    self.assertGreater(first_count, 0)
                    # The stage stays open for the installer of the same
                    # stage: exactly one extraction so far, one live root,
                    # never the retired intermediate compressed temp file.
                    context = InstallThroughRealSeamsTests._context_of(seams)
                    stage = context.support_stage
                    self.assertIsInstance(stage, CandidateSupportStage)
                    self.assertFalse(stage.closed)
                    self.assertEqual(_staging_names(state_dir), [stage.root.name])
                    _assert_no_compressed_tmp_file(state_dir)
                    self.assertEqual(support.support_digest, _sha(hw_bytes))
                    self.assertEqual(support.support_size, len(hw_bytes))
                    self.assertEqual(
                        support.installed_size_bound,
                        stage.pool.total_installed_bytes,
                    )
                    self.assertEqual(stage.pool.root, stage.root.resolve())
                    self.assertEqual(support.provided_firmware, frozenset({_X_FIRMWARE}))
                    self.assertEqual(support.provided_microcode, frozenset({_X_MICROCODE}))
                    self.assertNotIn(_Y_FIRMWARE, support.provided_firmware)
                    self.assertNotIn(_Y_MICROCODE, support.provided_microcode)
            finally:
                cleanup = getattr(seams, "support_stage_cleanup", None)
                self.assertTrue(callable(cleanup))
                cleanup()
            self.assertEqual(counter.count, first_count)
            self.assertEqual(_staging_names(state_dir), [])

    def test_running_pool_cannot_satisfy_x_only_requirement(self) -> None:
        from greia_installer.hardware_support import (
            HardwareSupportPoolError,
            VerifiedHardwareSupportPool,
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pool_y = _pool_tree(root, name="y", firmware=_Y_FIRMWARE, microcode=_Y_MICROCODE)
            pool = VerifiedHardwareSupportPool.load(pool_y)
            with self.assertRaises(HardwareSupportPoolError):
                pool.require_candidates([_X_FIRMWARE])
            with self.assertRaises(HardwareSupportPoolError):
                pool.require_firmware([_X_FIRMWARE])
            # Sanity: the running pool still satisfies its own packages.
            self.assertEqual(pool.require_firmware([_Y_FIRMWARE]), (_Y_FIRMWARE,))


class InstallThroughRealSeamsTests(unittest.TestCase):
    """An X-only package installs via factory/selection/install seams."""

    def test_x_only_package_installs(self) -> None:
        from greia_platform.hardware_enablement import (
            HardwareSupportPlan,
            HardwareSupportRecommendation,
            SupportDisposition,
            SupportKind,
        )
        from greia_platform.slot_writer import resolve_hardware_selection

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pool_x = _pool_tree(root, name="x", firmware=_X_FIRMWARE, microcode=_X_MICROCODE)
            hw_path = root / "hw-x.tar.zst"
            _hw_archive(pool_x, hw_path)
            raw = _payload_bytes(b"t04-install:")
            bundle = _candidate_bundle(root, raw, hw_path=hw_path)
            inspected = SystemUpdateInbox(root / "state").receive(bundle)
            seams, state_dir = _rig(root)
            counter = _ExtractionCounter()
            with counter.patch():
                support = seams.support_set_factory(inspected)
                extractions_after_support = counter.count
                self.assertGreater(extractions_after_support, 0)
                plan = HardwareSupportPlan(
                    inventory_token="ab" * 32,
                    recommendations=(
                        HardwareSupportRecommendation(
                            package=_X_FIRMWARE,
                            kind=SupportKind.FIRMWARE,
                            disposition=SupportDisposition.AUTO_ELIGIBLE,
                            source="t04-proof",
                        ),
                    ),
                    complete=True,
                )
                selection = resolve_hardware_selection(plan=plan, support=support)
            self.assertEqual(tuple(selection.firmware), (_X_FIRMWARE,))
            mountpoint = root / "mnt"
            mountpoint.mkdir(parents=True)
            commands: list[list[str]] = []
            with mock.patch.object(
                _updates, "_PlatformCommandAdapter", lambda *a, **k: _FakeCommandAdapter(commands)
            ):
                with counter.patch():
                    # Bind the lazy installer to this stage: support ran first,
                    # then the mounted slot of the same stage.
                    installer_factory = seams.package_installer_factory
                    # Reach the shared context cell: the support factory opened
                    # the stage-owned pool; thread a fake mount tracker the same
                    # way the production filesystem factory would.
                    context = self._context_of(seams)
                    stage_before = context.support_stage
                    self.assertIsInstance(stage_before, CandidateSupportStage)
                    context.filesystem_tracker = _FakeTracker(mountpoint)  # type: ignore[attr-defined]
                    installer = installer_factory()
                    try:
                        installed = installer.install(
                            tuple(selection.firmware), tuple(selection.microcode)
                        )
                    finally:
                        cleanup = getattr(seams, "support_stage_cleanup", None)
                        self.assertTrue(callable(cleanup))
                        cleanup()
            # One stage, one extraction: the installer reuses the
            # stage-owned pool instead of re-materializing the member.
            self.assertEqual(counter.count, extractions_after_support)
            self.assertIs(context.support_stage, None)
            names = [getattr(item, "name", item) for item in installed]
            self.assertEqual(names, [_X_FIRMWARE])
            kinds = [cmd[0] for cmd in commands]
            self.assertIn("mount", kinds)
            bind = [cmd for cmd in commands if cmd[:2] == ["mount", "--bind"]]
            self.assertEqual(len(bind), 1)
            bind_source = Path(bind[0][2])
            self.assertNotEqual(bind_source.resolve(), pool_x.resolve())
            # Resolver pool root equals installer pool root: the bind
            # source is exactly the stage-owned pool root.
            self.assertEqual(bind_source, stage_before.pool.root)
            self.assertEqual(stage_before.pool.root, stage_before.root.resolve())
            self.assertTrue(
                str(bind_source).startswith(
                    str(state_dir / "system-updates" / "candidate-support")
                )
            )
            apt_install = [cmd for cmd in commands if "install" in cmd]
            self.assertTrue(any(_X_FIRMWARE in cmd for cmd in apt_install))
            _assert_no_compressed_tmp_file(state_dir)
            self.assertEqual(_staging_names(state_dir), [])

    @staticmethod
    def _context_of(seams: object) -> object:
        """Reach the shared production context cell behind the factories."""
        factory = getattr(seams, "support_set_factory")
        closure = getattr(factory, "__closure__", None) or ()
        for cell in closure:
            candidate = cell.cell_contents
            if hasattr(candidate, "support_stage"):
                return candidate
        raise AssertionError("production support factory must close over its context")


class MismatchRejectionTests(unittest.TestCase):
    """Digest/size mismatch is rejected at inspection and at staging."""

    def test_tampered_member_rejected_at_inspection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pool_x = _pool_tree(root, name="x", firmware=_X_FIRMWARE, microcode=_X_MICROCODE)
            hw_path = root / "hw-x.tar.zst"
            _hw_archive(pool_x, hw_path)
            raw = _payload_bytes(b"t04-tamper:")
            bundle = _candidate_bundle(root, raw, hw_path=hw_path)
            tampered = root / "tampered.greiaupdate"
            with zipfile.ZipFile(bundle, "r") as source:
                members = {
                    info.filename: source.read(info.filename)
                    for info in source.infolist()
                }
            corrupted = bytearray(members[HARDWARE_SUPPORT_NAME])
            corrupted[len(corrupted) // 2] ^= 0x01
            members[HARDWARE_SUPPORT_NAME] = bytes(corrupted)
            with zipfile.ZipFile(tampered, "w", compression=zipfile.ZIP_STORED) as target:
                for name, payload in members.items():
                    target.writestr(name, payload)
            from greia_platform.system_updates import inspect_update_bundle

            with self.assertRaises(UpdateBundleError):
                inspect_update_bundle(tampered)

    def test_candidate_changed_after_inspection_rejected_at_staging(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pool_x = _pool_tree(root, name="x", firmware=_X_FIRMWARE, microcode=_X_MICROCODE)
            hw_path = root / "hw-x.tar.zst"
            _hw_archive(pool_x, hw_path)
            raw = _payload_bytes(b"t04-toctou:")
            bundle = _candidate_bundle(root, raw, hw_path=hw_path)
            inspected = SystemUpdateInbox(root / "state").receive(bundle)
            seams, _state = _rig(root)
            # Swap the staged inbox candidate bytes after inspection: same
            # size, new content. The materializer re-verifies the digest on
            # the exact bytes it extracts, so staging refuses instead of
            # installing from unverified bytes.
            staged = inspected.path
            with zipfile.ZipFile(staged, "r") as source:
                members = {
                    info.filename: source.read(info.filename)
                    for info in source.infolist()
                }
            swapped = bytearray(members[HARDWARE_SUPPORT_NAME])
            swapped[10] ^= 0xFF
            self.assertEqual(len(swapped), len(members[HARDWARE_SUPPORT_NAME]))
            members[HARDWARE_SUPPORT_NAME] = bytes(swapped)
            with zipfile.ZipFile(staged, "w", compression=zipfile.ZIP_STORED) as target:
                for name, payload in members.items():
                    target.writestr(name, payload)
            with self.assertRaises(UpdateBackendUnavailable) as raised:
                seams.support_set_factory(inspected)
            self.assertIn("support", str(raised.exception))


class AbsentSupportTests(unittest.TestCase):
    """Absent support extracts nothing and finalizes empty."""

    def test_absent_support_path_extracts_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = _payload_bytes(b"t04-absent:")
            bundle = _candidate_bundle(root, raw, hw_path=None)
            inspected = SystemUpdateInbox(root / "state").receive(bundle)
            self.assertIsNone(inspected.manifest.hardware_support_sha256)
            seams, state_dir = _rig(root)
            support = seams.support_set_factory(inspected)
            self.assertIsNone(support.support_digest)
            self.assertIsNone(support.support_size)
            self.assertEqual(tuple(support.provided_firmware), ())
            self.assertEqual(tuple(support.provided_microcode), ())
            # No support member creates no staging directory at all.
            self.assertFalse(_staging_parent(state_dir).exists())
            context = InstallThroughRealSeamsTests._context_of(seams)
            self.assertIsNone(context.support_stage)
            # The lazy installer accepts the empty plan with no pool.
            mountpoint = root / "mnt"
            mountpoint.mkdir(parents=True)
            context.filesystem_tracker = _FakeTracker(mountpoint)  # type: ignore[attr-defined]
            installer = seams.package_installer_factory()
            self.assertEqual(installer.install((), ()), ())
            self.assertFalse(_staging_parent(state_dir).exists())


class CleanupTests(unittest.TestCase):
    """Temp staging is removed on success, selection failure, and install failure."""

    def test_cleanup_on_success(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pool_x = _pool_tree(root, name="x", firmware=_X_FIRMWARE, microcode=_X_MICROCODE)
            hw_path = root / "hw-x.tar.zst"
            _hw_archive(pool_x, hw_path)
            raw = _payload_bytes(b"t04-clean:")
            bundle = _candidate_bundle(root, raw, hw_path=hw_path)
            inspected = SystemUpdateInbox(root / "state").receive(bundle)
            seams, state_dir = _rig(root)
            counter = _ExtractionCounter()
            with counter.patch():
                seams.support_set_factory(inspected)
                self.assertGreater(counter.count, 0)
                self.assertEqual(len(_staging_names(state_dir)), 1)
                _assert_no_compressed_tmp_file(state_dir)
                seams.support_stage_cleanup()
            self.assertEqual(_staging_names(state_dir), [])

    def test_cleanup_on_selection_failure(self) -> None:
        from greia_platform.slot_writer import SlotFinalizeError
        from greia_platform.hardware_enablement import (
            HardwareSupportPlan,
            HardwareSupportRecommendation,
            SupportDisposition,
            SupportKind,
        )
        from greia_platform.slot_writer import resolve_hardware_selection

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pool_x = _pool_tree(root, name="x", firmware=_X_FIRMWARE, microcode=_X_MICROCODE)
            hw_path = root / "hw-x.tar.zst"
            _hw_archive(pool_x, hw_path)
            raw = _payload_bytes(b"t04-selfail:")
            bundle = _candidate_bundle(root, raw, hw_path=hw_path)
            inspected = SystemUpdateInbox(root / "state").receive(bundle)
            seams, state_dir = _rig(root)
            counter = _ExtractionCounter()
            with counter.patch():
                support = seams.support_set_factory(inspected)
                self.assertGreater(counter.count, 0)
                # A resolver plan with no release provider fails closed
                # through the real selection seam; the stage still cleans up.
                plan = HardwareSupportPlan(
                    inventory_token="ab" * 32,
                    recommendations=(
                        HardwareSupportRecommendation(
                            package="firmware-not-in-candidate",
                            kind=SupportKind.FIRMWARE,
                            disposition=SupportDisposition.AUTO_ELIGIBLE,
                            source="t04-proof",
                        ),
                    ),
                    complete=True,
                )
                try:
                    with self.assertRaises(SlotFinalizeError):
                        resolve_hardware_selection(plan=plan, support=support)
                finally:
                    seams.support_stage_cleanup()
            self.assertEqual(_staging_names(state_dir), [])
            _assert_no_compressed_tmp_file(state_dir)

    def test_cleanup_on_installation_failure(self) -> None:
        from greia_platform.slot_writer import SlotFinalizeError

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pool_x = _pool_tree(root, name="x", firmware=_X_FIRMWARE, microcode=_X_MICROCODE)
            hw_path = root / "hw-x.tar.zst"
            _hw_archive(pool_x, hw_path)
            raw = _payload_bytes(b"t04-installfail:")
            bundle = _candidate_bundle(root, raw, hw_path=hw_path)
            inspected = SystemUpdateInbox(root / "state").receive(bundle)
            seams, state_dir = _rig(root)
            counter = _ExtractionCounter()
            with counter.patch():
                seams.support_set_factory(inspected)
                self.assertGreater(counter.count, 0)
                mountpoint = root / "mnt"
                mountpoint.mkdir(parents=True)
                context = InstallThroughRealSeamsTests._context_of(seams)
                context.filesystem_tracker = _FakeTracker(mountpoint)  # type: ignore[attr-defined]
                installer = seams.package_installer_factory()
                try:
                    with self.assertRaises(SlotFinalizeError):
                        installer.install(("firmware-not-in-candidate",), ())
                finally:
                    seams.support_stage_cleanup()
            self.assertEqual(_staging_names(state_dir), [])
            _assert_no_compressed_tmp_file(state_dir)

    def test_cleanup_on_failure(self) -> None:
        import zstandard

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bad = zstandard.ZstdCompressor(level=3).compress(b"not a tar archive")
            hw_path = root / "hw-bad.tar.zst"
            hw_path.write_bytes(bad)
            raw = _payload_bytes(b"t04-bad:")
            bundle = _candidate_bundle(root, raw, hw_path=hw_path)
            inspected = SystemUpdateInbox(root / "state").receive(bundle)
            seams, state_dir = _rig(root)
            counter = _ExtractionCounter()
            with counter.patch():
                with self.assertRaises(UpdateBackendUnavailable):
                    seams.support_set_factory(inspected)
                # The failed open never reached tree extraction.
                self.assertEqual(counter.count, 0)
            self.assertEqual(_staging_names(state_dir), [])
            _assert_no_compressed_tmp_file(state_dir)

    def test_unsafe_members_rejected_and_cleaned(self) -> None:
        import zstandard

        cases = {
            "absolute": "/manifest.json",
            "dotdot": "../escape.json",
            "unexpected": "unexpected-top-level.txt",
            "nested-pool": "pool/sub/extra.deb",
        }
        for label, arcname in cases.items():
            with self.subTest(member=label):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    buffer = io.BytesIO()
                    with tarfile.open(fileobj=buffer, mode="w") as tar:
                        payload = b"unsafe-bytes"
                        info = tarfile.TarInfo(name=arcname)
                        info.size = len(payload)
                        info.mode = 0o644
                        tar.addfile(info, io.BytesIO(payload))
                    hw_path = root / "hw-unsafe.tar.zst"
                    hw_path.write_bytes(
                        zstandard.ZstdCompressor(level=3).compress(buffer.getvalue())
                    )
                    raw = _payload_bytes(b"t04-unsafe:")
                    bundle = _candidate_bundle(root, raw, hw_path=hw_path)
                    inspected = SystemUpdateInbox(root / "state").receive(bundle)
                    seams, state_dir = _rig(root)
                    counter = _ExtractionCounter()
                    with counter.patch():
                        with self.assertRaises(UpdateBackendUnavailable):
                            seams.support_set_factory(inspected)
                        self.assertEqual(counter.count, 0)
                    self.assertEqual(_staging_names(state_dir), [])
                    _assert_no_compressed_tmp_file(state_dir)

    def test_symlink_and_fifo_members_rejected(self) -> None:
        import zstandard

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            buffer = io.BytesIO()
            with tarfile.open(fileobj=buffer, mode="w") as tar:
                link = tarfile.TarInfo(name="pool/evil.deb")
                link.type = tarfile.SYMTYPE
                link.linkname = "/etc/passwd"
                tar.addfile(link)
                fifo = tarfile.TarInfo(name="Packages")
                fifo.type = tarfile.FIFOTYPE
                tar.addfile(fifo)
            hw_path = root / "hw-link.tar.zst"
            hw_path.write_bytes(
                zstandard.ZstdCompressor(level=3).compress(buffer.getvalue())
            )
            raw = _payload_bytes(b"t04-link:")
            bundle = _candidate_bundle(root, raw, hw_path=hw_path)
            inspected = SystemUpdateInbox(root / "state").receive(bundle)
            seams, state_dir = _rig(root)
            counter = _ExtractionCounter()
            with counter.patch():
                with self.assertRaises(UpdateBackendUnavailable):
                    seams.support_set_factory(inspected)
                self.assertEqual(counter.count, 0)
            self.assertEqual(_staging_names(state_dir), [])
            _assert_no_compressed_tmp_file(state_dir)


class ContractSyncTests(unittest.TestCase):
    """Stager constants track the bundle contract."""

    def test_member_name_and_bounds_track_system_updates(self) -> None:
        from greia_platform import candidate_support
        from greia_platform import system_updates

        self.assertEqual(
            candidate_support.HARDWARE_SUPPORT_MEMBER,
            system_updates.HARDWARE_SUPPORT_NAME,
        )
        self.assertEqual(
            MAX_CANDIDATE_SUPPORT_COMPRESSED_BYTES,
            system_updates.MAX_HARDWARE_SUPPORT_BYTES,
        )
        self.assertEqual(STAGING_OPERATING_RESERVE_BYTES, 256 * 1024 * 1024)

    def test_null_manifest_is_noop_without_filesystem_touch(self) -> None:
        from greia_platform.candidate_support import CandidateSupportError

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            staging = root / "staging-parent"
            manifest = SimpleNamespace(
                hardware_support_sha256=None, hardware_support_size=None
            )
            with self.assertRaises(CandidateSupportError):
                CandidateSupportStage.open(root / "no-bundle.greiaupdate", manifest, staging)
            # Fact validation refuses before any filesystem touch.
            self.assertFalse(staging.exists())


class PersistPreflightTests(unittest.TestCase):
    """Insufficient PERSIST space refuses before extraction."""

    def test_insufficient_persist_space_refuses_before_extraction(self) -> None:
        import shutil as _shutil

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pool_x = _pool_tree(root, name="x", firmware=_X_FIRMWARE, microcode=_X_MICROCODE)
            hw_path = root / "hw-x.tar.zst"
            _hw_archive(pool_x, hw_path)
            raw = _payload_bytes(b"t04-persist:")
            bundle = _candidate_bundle(root, raw, hw_path=hw_path)
            inspected = SystemUpdateInbox(root / "state").receive(bundle)
            seams, state_dir = _rig(root)
            real_usage = _shutil.disk_usage
            counter = _ExtractionCounter()
            with counter.patch():
                with mock.patch.object(
                    _candidate_support.shutil,
                    "disk_usage",
                    lambda path: SimpleNamespace(
                        total=real_usage(path).total,
                        used=real_usage(path).total,
                        free=0,
                    ),
                ):
                    with self.assertRaises(UpdateBackendUnavailable) as raised:
                        seams.support_set_factory(inspected)
                    # The refusal is the PERSIST preflight, and no tree
                    # extraction was ever attempted.
                    self.assertIn("PERSIST", str(raised.exception))
                    self.assertEqual(counter.count, 0)
            self.assertEqual(_staging_names(state_dir), [])
            _assert_no_compressed_tmp_file(state_dir)


class RestageFreshnessTests(unittest.TestCase):
    """A restage never reuses a stale pool: one live stage at a time."""

    def test_restage_closes_previous_stage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pool_x = _pool_tree(root, name="x", firmware=_X_FIRMWARE, microcode=_X_MICROCODE)
            hw_x = root / "hw-x.tar.zst"
            _hw_archive(pool_x, hw_x)
            pool_y = _pool_tree(root, name="y", firmware=_Y_FIRMWARE, microcode=_Y_MICROCODE)
            hw_y = root / "hw-y.tar.zst"
            _hw_archive(pool_y, hw_y)
            bundle_x = _candidate_bundle(
                root, _payload_bytes(b"t04-restage-x:"), hw_path=hw_x,
                name="candidate-x.greiaupdate", release_id="greia-t04-x",
            )
            bundle_y = _candidate_bundle(
                root, _payload_bytes(b"t04-restage-y:"), hw_path=hw_y,
                name="candidate-y.greiaupdate", release_id="greia-t04-y",
            )
            inspected_x = SystemUpdateInbox(root / "inbox-x").receive(bundle_x)
            inspected_y = SystemUpdateInbox(root / "inbox-y").receive(bundle_y)
            seams, state_dir = _rig(root)
            try:
                support_x = seams.support_set_factory(inspected_x)
                context = InstallThroughRealSeamsTests._context_of(seams)
                stage_x = context.support_stage
                self.assertIsInstance(stage_x, CandidateSupportStage)
                self.assertEqual(
                    support_x.provided_firmware, frozenset({_X_FIRMWARE})
                )
                self.assertEqual(_staging_names(state_dir), [stage_x.root.name])
                support_y = seams.support_set_factory(inspected_y)
                # The previous stage was closed before the new one opened:
                # exactly one live root, the new pool, the old root gone.
                self.assertTrue(stage_x.closed)
                self.assertFalse(stage_x.root.exists())
                stage_y = context.support_stage
                self.assertIsNot(stage_y, stage_x)
                self.assertEqual(
                    support_y.provided_firmware, frozenset({_Y_FIRMWARE})
                )
                self.assertEqual(stage_y.pool.root, stage_y.root.resolve())
                self.assertEqual(_staging_names(state_dir), [stage_y.root.name])
                _assert_no_compressed_tmp_file(state_dir)
            finally:
                seams.support_stage_cleanup()
            self.assertEqual(_staging_names(state_dir), [])

    def test_restage_to_null_support_closes_open_stage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pool_x = _pool_tree(root, name="x", firmware=_X_FIRMWARE, microcode=_X_MICROCODE)
            hw_x = root / "hw-x.tar.zst"
            _hw_archive(pool_x, hw_x)
            bundle_x = _candidate_bundle(
                root, _payload_bytes(b"t04-restage-null-x:"), hw_path=hw_x,
                name="candidate-x.greiaupdate", release_id="greia-t04-x",
            )
            bundle_null = _candidate_bundle(
                root, _payload_bytes(b"t04-restage-null-none:"), hw_path=None,
                name="candidate-null.greiaupdate", release_id="greia-t04-null",
            )
            inspected_x = SystemUpdateInbox(root / "inbox-x").receive(bundle_x)
            inspected_null = SystemUpdateInbox(root / "inbox-null").receive(bundle_null)
            self.assertIsNone(inspected_null.manifest.hardware_support_sha256)
            seams, state_dir = _rig(root)
            try:
                counter = _ExtractionCounter()
                with counter.patch():
                    support_x = seams.support_set_factory(inspected_x)
                    self.assertEqual(
                        support_x.provided_firmware, frozenset({_X_FIRMWARE})
                    )
                    context = InstallThroughRealSeamsTests._context_of(seams)
                    stage_x = context.support_stage
                    self.assertIsInstance(stage_x, CandidateSupportStage)
                    self.assertFalse(stage_x.closed)
                    stage_root = stage_x.root
                    self.assertEqual(_staging_names(state_dir), [stage_root.name])
                    count_after_open = counter.count
                    self.assertGreater(count_after_open, 0)
                    # Direct factory-level restage to a null-support
                    # candidate: no intervening backend finally, so the
                    # acquire itself must close the stale stage.
                    result = _updates._acquire_support_stage(context, inspected_null)
                    self.assertIsNone(result)
                    self.assertIsNone(context.support_stage)
                    self.assertTrue(stage_x.closed)
                    self.assertFalse(stage_root.exists())
                    self.assertEqual(counter.count, count_after_open)
                    self.assertEqual(_staging_names(state_dir), [])
                    _assert_no_compressed_tmp_file(state_dir)
            finally:
                seams.support_stage_cleanup()
            self.assertEqual(_staging_names(state_dir), [])


class _StageFakeFilesystem:
    """Destination-only fake mirroring the update-service harness shape."""

    def __init__(self, mount_dir: Path) -> None:
        self.mount_dir = mount_dir
        self.ops: list[str] = []
        self.files: dict[str, bytes] = {}
        self.mounted = False

    def bind_filesystem_uuid(self, filesystem_uuid: str) -> None:
        self.ops.append("bind")

    def expand_to_capacity(self) -> None:
        self.ops.append("expand")

    def mount(self) -> Path:
        self.ops.append("mount")
        self.mounted = True
        return self.mount_dir

    def unmount(self) -> None:
        self.ops.append("unmount")
        self.mounted = False

    def sync(self) -> None:
        self.ops.append("sync")

    def write_file(self, relative_path: str, data: bytes) -> None:
        if not self.mounted:
            raise AssertionError("slot writes require a mounted destination")
        self.ops.append(f"write:{relative_path}")
        self.files[relative_path] = bytes(data)

    def missing_files(self, required: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(name for name in required if name not in self.files)

    def check_completeness(self) -> None:
        from greia_platform.slot_writer import check_slot_completeness

        self.ops.append("completeness")
        check_slot_completeness(self.mount_dir)

    def check_health(self) -> None:
        self.ops.append("health")


def _stage_layout_record(root: Path, *, slot_bytes: int) -> Path:
    import json as _json

    record: dict[str, object] = {
        "accepted_release_id": "greia-t04",
        "accepted_slot": "A",
        "boot_backend": "grub-ab-v1",
        "boot_control": {"active_slot": "A", "kind": "grub-env-v1"},
        "install_profile": "t04profile",
        "install_target_sha256": "ab" * 32,
        "installed_at_unix": 1757000000,
        "layout_id": "modern-gpt-ab-v1",
        "persist": {
            "filesystem_uuid": "cccccccc-dddd-eeee-ffff-000000000000",
            "partuuid": "33333333-4444-5555-6666-777777777777",
        },
        "platform_family": "standard-x86-64",
        "schema_version": 1,
        "slot_bytes": slot_bytes,
        "system_a": {
            "filesystem_uuid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            "partuuid": "11111111-2222-3333-4444-555555555555",
        },
        "system_b": {
            "filesystem_uuid": "bbbbbbbb-cccc-dddd-eeee-ffffffffffff",
            "partuuid": "22222222-3333-4444-5555-666666666666",
        },
    }
    path = root / "installed-layout.json"
    path.write_bytes((_json.dumps(record, sort_keys=True) + "\n").encode())
    return path


def _populate_stage_completeness(mount_dir: Path) -> None:
    from greia_platform.slot_writer import (
        REQUIRED_SLOT_COMPLETENESS_DIRS,
        REQUIRED_SLOT_COMPLETENESS_FILES,
    )

    for rel_path in REQUIRED_SLOT_COMPLETENESS_DIRS:
        (mount_dir / rel_path).mkdir(parents=True, exist_ok=True)
    for rel_path in REQUIRED_SLOT_COMPLETENESS_FILES:
        candidate = mount_dir / rel_path
        candidate.parent.mkdir(parents=True, exist_ok=True)
        if candidate.is_symlink() or not candidate.is_file():
            candidate.write_bytes(b"#!/bin/sh\nexit 0\n")
            try:
                candidate.chmod(0o755)
            except OSError:
                pass


class StageCapacityTests(unittest.TestCase):
    """Stage-time refusal uses the single-owner finalized-slot formula."""

    def _mixed_backend(
        self, root: Path, *, slot_bytes: int, contacts: list[str]
    ) -> tuple[object, Path, Path]:
        from greia_platform.persistent_layout import emit_persist_schema_marker
        from greia_platform.slot_writer import (
            HardwareInventoryAttestation,
            LoopbackSlotFile,
        )
        from greia_platform.system_updates import (
            SlotBackedSystemUpdateBackend,
            UpdateSlotSeams,
        )

        state_dir = root / "state"
        state_dir.mkdir(parents=True, exist_ok=True)
        layout_path = _stage_layout_record(root, slot_bytes=slot_bytes)
        prod = build_production_update_seams(
            layout_record_path=layout_path, state_dir=state_dir
        )
        context = InstallThroughRealSeamsTests._context_of(prod)
        mount_dir = root / "mnt"
        mount_dir.mkdir(parents=True, exist_ok=True)
        _populate_stage_completeness(mount_dir)
        filesystem = _StageFakeFilesystem(mount_dir)

        def _store(destination: object) -> object:
            contacts.append(f"store:{getattr(destination, 'role', '?')}")
            return LoopbackSlotFile.create(
                root / f"slot-{getattr(destination, 'role', 'x')}.img",
                int(getattr(destination, "slot_capacity_bytes", 0)),
            )

        def _filesystem() -> object:
            contacts.append("filesystem")
            context.filesystem_tracker = _FakeTracker(mount_dir)  # type: ignore[attr-defined]
            return filesystem

        def _inventory() -> object:
            contacts.append("inventory")
            return HardwareInventoryAttestation(
                token=hashlib.sha256(b"inventory-t03").hexdigest()
            )

        def _contract() -> bytes:
            contacts.append("contract")
            return emit_persist_schema_marker(1)

        def _support(bundle: object) -> object:
            contacts.append("support")
            return prod.support_set_factory(bundle)

        seams = UpdateSlotSeams(
            slot_store_factory=_store,
            filesystem_factory=_filesystem,
            package_installer_factory=prod.package_installer_factory,
            inventory_factory=_inventory,
            support_set_factory=_support,
            selection_factory=None,
            installed_contract_factory=_contract,
            support_stage_cleanup=prod.support_stage_cleanup,
        )
        backend = SlotBackedSystemUpdateBackend(
            state_dir, layout_record_path=layout_path, seams=seams
        )
        return backend, state_dir, layout_path

    def test_fitting_support_candidate_stages(self) -> None:
        from greia_installer.hardware_support import support_installed_size_bound
        from greia_installer.layout import require_finalized_slot_capacity
        from greia_platform.slot_writer import SlotWriter, VerifiedReleaseMember
        from greia_platform.system_updates import SystemUpdateError

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pool_x = _pool_tree(root, name="x", firmware=_X_FIRMWARE, microcode=_X_MICROCODE)
            hw_path = root / "hw-x.tar.zst"
            _hw_archive(pool_x, hw_path)
            raw = _payload_bytes(b"t04-fit:")
            bundle = _candidate_bundle(root, raw, hw_path=hw_path)
            inspected = SystemUpdateInbox(root / "state").receive(bundle)
            manifest = inspected.manifest
            member = VerifiedReleaseMember.from_manifest(manifest)
            bound = support_installed_size_bound(hw_path)
            # Single-owner agreement: the owner accepts and matches the
            # runtime writer for identical facts.
            required = require_finalized_slot_capacity(
                slot_bytes=1024 * 1024 * 1024,
                base_bytes=manifest.payload_uncompressed_bytes,
                minimum_slot_bytes=manifest.payload_minimum_slot_bytes,
                support_installed_bytes=bound,
            )
            self.assertEqual(
                required, SlotWriter().required_slot_bytes(member, bound)
            )
            contacts: list[str] = []
            backend, state_dir, _ = self._mixed_backend(
                root, slot_bytes=1024 * 1024 * 1024, contacts=contacts
            )
            try:
                backend.stage(inspected)
            except SystemUpdateError as exc:
                self.fail(f"fitting support candidate refused: {exc}")
            # The stage reached the slot seam and cleaned up afterwards.
            self.assertIn("store:system-b", contacts)
            self.assertEqual(_staging_names(state_dir), [])
            _assert_no_compressed_tmp_file(state_dir)

    def test_oversized_support_candidate_refused_before_slot_mutation(self) -> None:
        from greia_installer.hardware_support import support_installed_size_bound
        from greia_installer.layout import (
            LayoutError,
            require_finalized_slot_capacity,
        )
        from greia_platform.slot_writer import (
            SlotWriter,
            VerifiedReleaseMember,
        )
        from greia_platform.system_updates import SystemUpdateError

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pool_x = _pool_tree(root, name="x", firmware=_X_FIRMWARE, microcode=_X_MICROCODE)
            hw_path = root / "hw-x.tar.zst"
            _hw_archive(pool_x, hw_path)
            raw = _payload_bytes(b"t04-over:")
            # Same real support, but a manifest minimum that tips the
            # shared finalized-slot formula over the 1 GiB layout slot.
            bundle = _candidate_bundle(
                root, raw, hw_path=hw_path, minimum_slot_bytes=1024 * 1024 * 1024
            )
            inspected = SystemUpdateInbox(root / "state").receive(bundle)
            manifest = inspected.manifest
            member = VerifiedReleaseMember.from_manifest(manifest)
            bound = support_installed_size_bound(hw_path)
            # Single-owner agreement outside the stage: the owner refuses
            # and the runtime writer computes the same over-capacity total.
            with self.assertRaises(LayoutError):
                require_finalized_slot_capacity(
                    slot_bytes=1024 * 1024 * 1024,
                    base_bytes=manifest.payload_uncompressed_bytes,
                    minimum_slot_bytes=manifest.payload_minimum_slot_bytes,
                    support_installed_bytes=bound,
                )
            self.assertGreater(
                SlotWriter().required_slot_bytes(member, bound),
                1024 * 1024 * 1024,
            )
            contacts: list[str] = []
            backend, state_dir, _ = self._mixed_backend(
                root, slot_bytes=1024 * 1024 * 1024, contacts=contacts
            )
            counter = _ExtractionCounter()
            with counter.patch():
                with self.assertRaisesRegex(SystemUpdateError, "capacity preflight"):
                    backend.stage(inspected)
            # Refused before the first destination mutation, stage cleaned.
            self.assertNotIn("store:system-b", contacts)
            self.assertEqual(_staging_names(state_dir), [])
            _assert_no_compressed_tmp_file(state_dir)


if __name__ == "__main__":
    unittest.main()
