"""T04: the candidate hardware-support member drives candidate finalization.

Proves, through the real production seams
(``_production_support_set_factory`` -> ``VerifiedHardwareSupportPool.load``
-> ``pool_to_support_set`` -> ``resolve_hardware_selection`` ->
``_LazyTargetPackageInstaller`` -> ``InstallerSlotPackageInstaller`` /
``TargetHardwareSupportInstaller``):

- candidate X's pool wins over running pool Y;
- an X-only package installs through the real factory/selection/install
  path (only command execution is faked; no SSH/mount/flash, no APT);
- digest/size mismatch is rejected (at inspection and at staging time,
  when the candidate changed after inspection);
- the absent-support path extracts nothing;
- temp staging is removed on success and on failure;
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
from greia_platform.candidate_support import (
    MAX_CANDIDATE_SUPPORT_COMPRESSED_BYTES,
    materialized_candidate_support,
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
            },
            {
                "package": microcode, "version": "1",
                "architecture": "amd64", "filename": f"pool/{uc_name}",
                "size": len(uc), "sha256": _sha(uc), "candidate": True,
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
        minimum_slot_bytes=len(raw),
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
            support = seams.support_set_factory(inspected)
            self.assertEqual(support.support_digest, _sha(hw_bytes))
            self.assertEqual(support.support_size, len(hw_bytes))
            self.assertEqual(support.provided_firmware, frozenset({_X_FIRMWARE}))
            self.assertEqual(support.provided_microcode, frozenset({_X_MICROCODE}))
            self.assertNotIn(_Y_FIRMWARE, support.provided_firmware)
            self.assertNotIn(_Y_MICROCODE, support.provided_microcode)
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
            support = seams.support_set_factory(inspected)
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
                # Bind the lazy installer to this stage: support ran first,
                # then the mounted slot of the same stage.
                installer_factory = seams.package_installer_factory
                # Reach the shared context cell: the support factory stored
                # the candidate bundle; thread a fake mount tracker the same
                # way the production filesystem factory would.
                context = self._context_of(seams)
                context.filesystem_tracker = _FakeTracker(mountpoint)  # type: ignore[attr-defined]
                installer = installer_factory()
                installed = installer.install(
                    tuple(selection.firmware), tuple(selection.microcode)
                )
            names = [getattr(item, "name", item) for item in installed]
            self.assertEqual(names, [_X_FIRMWARE])
            kinds = [cmd[0] for cmd in commands]
            self.assertIn("mount", kinds)
            bind = [cmd for cmd in commands if cmd[:2] == ["mount", "--bind"]]
            self.assertEqual(len(bind), 1)
            bind_source = Path(bind[0][2])
            self.assertNotEqual(bind_source.resolve(), pool_x.resolve())
            self.assertTrue(
                str(bind_source).startswith(
                    str(state_dir / "system-updates" / "candidate-support")
                )
            )
            apt_install = [cmd for cmd in commands if "install" in cmd]
            self.assertTrue(any(_X_FIRMWARE in cmd for cmd in apt_install))
            self.assertEqual(_staging_names(state_dir), [])

    @staticmethod
    def _context_of(seams: object) -> object:
        """Reach the shared production context cell behind the factories."""
        factory = getattr(seams, "support_set_factory")
        closure = getattr(factory, "__closure__", None) or ()
        for cell in closure:
            candidate = cell.cell_contents
            if hasattr(candidate, "candidate_bundle"):
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
            self.assertEqual(_staging_names(state_dir), [])
            # The lazy installer accepts the empty plan with no pool.
            mountpoint = root / "mnt"
            mountpoint.mkdir(parents=True)
            context = InstallThroughRealSeamsTests._context_of(seams)
            context.filesystem_tracker = _FakeTracker(mountpoint)  # type: ignore[attr-defined]
            installer = seams.package_installer_factory()
            self.assertEqual(installer.install((), ()), ())


class CleanupTests(unittest.TestCase):
    """Temp staging is removed on success and on failure."""

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
            seams.support_set_factory(inspected)
            self.assertEqual(_staging_names(state_dir), [])

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
            with self.assertRaises(UpdateBackendUnavailable):
                seams.support_set_factory(inspected)
            self.assertEqual(_staging_names(state_dir), [])

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
                    with self.assertRaises(UpdateBackendUnavailable):
                        seams.support_set_factory(inspected)
                    self.assertEqual(_staging_names(state_dir), [])

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
            with self.assertRaises(UpdateBackendUnavailable):
                seams.support_set_factory(inspected)
            self.assertEqual(_staging_names(state_dir), [])


class ContractSyncTests(unittest.TestCase):
    """Materializer constants track the bundle contract."""

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

    def test_null_manifest_is_noop_without_filesystem_touch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            staging = root / "staging-parent"
            manifest = SimpleNamespace(
                hardware_support_sha256=None, hardware_support_size=None
            )
            with materialized_candidate_support(
                root / "no-bundle.greiaupdate", manifest, staging
            ) as result:
                self.assertIsNone(result)
            self.assertFalse(staging.exists())


if __name__ == "__main__":
    unittest.main()
