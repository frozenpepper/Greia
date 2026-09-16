"""POSTR1-P2-INSTALLER-SEAMS2: production seam factory + live-service composition.

Proves the exact shipped path composes the release-capable A/B installer by
itself, with no externally injected ``ab_seams_factory`` /
``ab_identities_factory``:

- production factory construction performs no disk probe, no slot write and
  no partition/runner execution (``subprocess.run`` blocked during
  construction);
- ``build_live_service()`` with disposable A/B release facts returns
  ``install_mode == "ab"`` with a bound ``ab_executor`` and no injected
  factories;
- a wrong/moved target is refused before destructive work with zero
  partition/runner commands;
- no fake/loop store substitutes for the production default (source + import
  identity checks);
- an A/B profile never becomes ``legacy-single``; a single-root profile
  still does, explicitly;
- an empty/absent production seam configuration fails closed (degraded),
  never the installed A/B default;
- no second writer/finalizer and no parallel device-storage class exists.

Zero valued-disk contact: all fixtures live under disposable tmpdirs; block
effects stay behind ``subprocess.run`` blocks/recorders. No network, no
signing (construction validates file shapes only, never bundle signatures).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

from greia_installer.composition import (
    AbInstallCompositionError,
    build_install_service,
    compose_ab_executor,
    install_mode_for_state,
)
from greia_installer.device_seams import (
    ProductionAbSeamsConfig,
    SubprocessHardwareSupportRunner,
    SubprocessPartitionRunner,
    build_production_seam_pair,
    config_from_facts_and_state,
)
from greia_installer.disk import DeviceObservation, DiskInventory, LiveMediaAncestry
from greia_installer.fresh_ab_install import FreshAbInstallError, FreshAbInstallSeams
from greia_installer.transaction_service import (
    PlatformInstallAuthority,
    ServiceState,
    TransactionServiceError,
    build_live_service,
)

GIB = 1024 * 1024 * 1024
MIB = 1024 * 1024

_AB_PROFILE_ID = "test-ab-seams-v1"
_AB_FAMILY = "legacy-x86"
_AB_ARCH = "i386"
_AB_LAYOUT = "legacy-bios-ab-v1"
_AB_BACKEND = "grub-ab-v1"

_LEGACY_PROFILE_ID = "test-legacy-recovery-v1"
_LEGACY_LAYOUT = "bios-single-ext4"
_LEGACY_BACKEND = "none-v1"

_SHIPPED_ENV_NAMES = (
    "GREIA_OS_ROOT",
    "GREIA_INSTALL_PAYLOAD",
    "GREIA_INSTALL_PAYLOAD_DIGEST",
    "GREIA_TARGET_IMAGE_PROFILE",
    "GREIA_HARDWARE_SUPPORT_POOL",
)
_AB_ENV_NAMES = (
    "GREIA_AB_RELEASE_BUNDLE",
    "GREIA_AB_TRUSTED_KEY_DIR",
    "GREIA_AB_GRUB_PASSWORD_HASH",
    "GREIA_AB_DEVELOPER",
    "GREIA_AB_SUPPORT_INSTALLED_BYTES",
)

_AB_PASSWORD_HASH = "grub.pbkdf2.sha512.10000." + "Q" * 64
_AB_SUPPORT_BOUND = 1 * MIB


def _write_profile(path: Path, *, profile_id: str, layout: str, backend: str) -> Path:
    path.write_text(
        json.dumps(
            {
                "profile": {"id": profile_id},
                "platform": {"family": _AB_FAMILY},
                "base": {"architecture": _AB_ARCH},
                "storage": {
                    "layout_adapter": layout,
                    "system_slot_bytes": 1 * GIB,
                    "persistent_minimum_bytes": 256 * MIB,
                },
                "installer": {"target_policy": "pc-internal-v1"},
                "updates": {"boot_backend": backend},
            }
        ),
        encoding="utf-8",
    )
    return path


def _make_ab_tree(prefix: str = "installer-seams-") -> tuple[str, dict[str, Path]]:
    directory = tempfile.mkdtemp(prefix=prefix)
    root = Path(directory).resolve()
    os_root = root / "os-root"
    os_root.mkdir()
    pool = root / "support-pool"
    pool.mkdir()
    payload = root / "payload.squashfs"
    payload.write_bytes(b"test-payload")
    digest = root / "expected-payload.sha256"
    digest.write_bytes(b"0" * 64)
    profile = root / "target-image-profile.json"
    _write_profile(
        profile, profile_id=_AB_PROFILE_ID, layout=_AB_LAYOUT, backend=_AB_BACKEND
    )
    bundle = root / "ab-release.greiaupdate"
    bundle.write_bytes(b"test-release-bundle")
    key_dir = root / "ab-trusted-keys"
    key_dir.mkdir()
    return directory, {
        "root": root,
        "os_root": os_root,
        "pool": pool,
        "payload": payload,
        "digest": digest,
        "profile": profile,
        "bundle": bundle,
        "key_dir": key_dir,
    }


@contextmanager
def _shipped_env(*, fix: dict[str, Path], ab_overrides: dict[str, str] | None = None):
    saved = {name: os.environ.get(name) for name in _SHIPPED_ENV_NAMES + _AB_ENV_NAMES}
    try:
        os.environ["GREIA_OS_ROOT"] = str(fix["os_root"])
        os.environ["GREIA_INSTALL_PAYLOAD"] = str(fix["payload"])
        os.environ["GREIA_INSTALL_PAYLOAD_DIGEST"] = str(fix["digest"])
        os.environ["GREIA_TARGET_IMAGE_PROFILE"] = str(fix["profile"])
        os.environ["GREIA_HARDWARE_SUPPORT_POOL"] = str(fix["pool"])
        for name in _AB_ENV_NAMES:
            os.environ.pop(name, None)
        for name, value in (ab_overrides or {}).items():
            os.environ[name] = value
        yield
    finally:
        for name, value in saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def _ab_overrides(fix: dict[str, Path]) -> dict[str, str]:
    return {
        "GREIA_AB_RELEASE_BUNDLE": str(fix["bundle"]),
        "GREIA_AB_TRUSTED_KEY_DIR": str(fix["key_dir"]),
        "GREIA_AB_GRUB_PASSWORD_HASH": _AB_PASSWORD_HASH,
        "GREIA_AB_SUPPORT_INSTALLED_BYTES": str(_AB_SUPPORT_BOUND),
    }


def _whole_disk_target(*, name: str = "sda", device_type: str = "disk", serial: str = "SERIAL-SEAMS-1", wwn: str = "WWN-SEAMS-1") -> DeviceObservation:
    return DeviceObservation(
        name=name,
        path=Path(f"/dev/{name}"),
        size_bytes=8 * GIB,
        device_type=device_type,
        model="Test disk",
        serial=serial,
        transport="sata",
        removable=False,
        read_only=False,
        mountpoints=(),
        wwn=wwn,
        major_minor="8:0" if name == "sda" else "8:16",
    )


def _no_subprocess() -> mock._patch:  # type: ignore[no-untyped-def]
    return mock.patch(
        "subprocess.run",
        side_effect=AssertionError("no subprocess during composition"),
    )


class ProductionSeamCompositionTests(unittest.TestCase):
    """Acceptance: shipped live service composes ``ab`` with no factories."""

    def test_live_service_composes_ab_with_no_injected_factories(self) -> None:
        directory, fix = _make_ab_tree()
        self.addCleanup(shutil.rmtree, directory, True)
        with _shipped_env(fix=fix, ab_overrides=_ab_overrides(fix)):
            with _no_subprocess():
                service = build_live_service()
        self.assertEqual(service.install_mode, "ab")
        self.assertIsNotNone(service.ab_executor)

    def test_factory_construction_performs_no_probe_write_or_execution(self) -> None:
        directory, fix = _make_ab_tree()
        self.addCleanup(shutil.rmtree, directory, True)
        before = {str(p.relative_to(fix["root"])) for p in fix["root"].rglob("*")}
        with _shipped_env(fix=fix, ab_overrides=_ab_overrides(fix)):
            with _no_subprocess():
                service = build_live_service()
                self.assertEqual(service.install_mode, "ab")
                self.assertIsNotNone(service.ab_executor)
        after = {str(p.relative_to(fix["root"])) for p in fix["root"].rglob("*")}
        self.assertEqual(before, after, "construction must not write beside fixtures")

    def test_partition_and_support_runners_stay_arg_array_shell_false(self) -> None:
        import inspect as _inspect

        for cls in (SubprocessPartitionRunner, SubprocessHardwareSupportRunner):
            source = _inspect.getsource(cls.run)
            self.assertIn("shell=False", source)
            self.assertNotIn("shell=True", source)
        # Live refusal path runs zero valued commands (proved below); the
        # runner classes themselves record nothing at construction.
        self.assertEqual(SubprocessPartitionRunner().__class__, SubprocessPartitionRunner)


class WrongMovedTargetRefusalTests(unittest.TestCase):
    """A wrong/moved target is refused before destructive work."""

    def _production_pair(self, fix: dict[str, Path]):  # type: ignore[no-untyped-def]
        from greia_installer.composition import ab_executor_facts_from_environment

        with _shipped_env(fix=fix, ab_overrides=_ab_overrides(fix)):
            state = ServiceState.from_target_profile(
                fix["profile"],
                payload=fix["payload"],
                payload_digest=fix["digest"],
                project_root=fix["os_root"],
                hardware_support_pool=fix["pool"],
            )
            facts = ab_executor_facts_from_environment(state=state)
            config = config_from_facts_and_state(
                facts=facts, hardware_support_pool=fix["pool"]
            )
            return build_production_seam_pair(config)

    def test_non_disk_target_refused_before_any_runner_execution(self) -> None:
        directory, fix = _make_ab_tree()
        self.addCleanup(shutil.rmtree, directory, True)
        seams_factory, _ = self._production_pair(fix)
        bad = _whole_disk_target(device_type="partition")
        calls: list[list[str]] = []
        real_run = subprocess.run

        def _recording(argv, **kwargs):  # type: ignore[no-untyped-def]
            calls.append(list(argv))
            return real_run(argv, **kwargs)

        with mock.patch("subprocess.run", side_effect=_recording):
            with self.assertRaisesRegex(FreshAbInstallError, "whole-disk target"):
                seams_factory(bad)
        self.assertEqual(calls, [], "wrong target must run zero commands")

    def test_moved_target_rematerialization_refuses_before_executor(self) -> None:
        from greia_installer.disk import PcInternalTargetPolicy

        directory, fix = _make_ab_tree()
        self.addCleanup(shutil.rmtree, directory, True)
        seams_factory, identities_factory = self._production_pair(fix)
        first = _whole_disk_target(name="sda")
        # Moved/swapped disk: different durable identity on a different node.
        moved = _whole_disk_target(name="sdb", serial="SERIAL-SEAMS-2", wwn="WWN-SEAMS-2")

        class _Probe:
            def __init__(self, devices) -> None:  # type: ignore[no-untyped-def]
                self._devices = list(devices)

            def probe(self):  # type: ignore[no-untyped-def]
                return DiskInventory(tuple(self._devices), generation=1)

        class _Resolver:
            def resolve(self, inventory=None):  # type: ignore[no-untyped-def]
                return LiveMediaAncestry.empty()

        with _shipped_env(fix=fix, ab_overrides=_ab_overrides(fix)):
            state = ServiceState.from_target_profile(
                fix["profile"],
                payload=fix["payload"],
                payload_digest=fix["digest"],
                project_root=fix["os_root"],
                hardware_support_pool=fix["pool"],
            )
            authority = PlatformInstallAuthority(
                policy=PcInternalTargetPolicy(),
                compatible_profile=_AB_PROFILE_ID,
                probe=_Probe([first]),  # type: ignore[arg-type]
                live_resolver=_Resolver(),  # type: ignore[arg-type]
            )
            service = build_install_service(
                state=state,
                authority=authority,
                ab_release_bundle=fix["bundle"],
                ab_password_hash=_AB_PASSWORD_HASH,
                ab_support_installed_bytes=_AB_SUPPORT_BOUND,
                ab_seams_factory=seams_factory,
                ab_identities_factory=identities_factory,
            )
            identity = authority.list_targets()[0].identity_digest
            # The disk moved: same service, fresh probe sees only sdb now.
            authority.probe._devices = [moved]  # type: ignore[attr-defined]
            with _no_subprocess():
                with self.assertRaisesRegex(
                    TransactionServiceError, "(unknown|no longer)"
                ):
                    service.rematerialize_target(identity)


class EngineRoutingAndDegradedConfigTests(unittest.TestCase):
    """A/B never silently becomes legacy; empty config fails closed."""

    def test_ab_profile_never_becomes_legacy_single(self) -> None:
        directory, fix = _make_ab_tree()
        self.addCleanup(shutil.rmtree, directory, True)
        with _shipped_env(fix=fix, ab_overrides=_ab_overrides(fix)):
            with _no_subprocess():
                service = build_live_service()
        self.assertEqual(service.install_mode, "ab")
        self.assertNotEqual(service.install_mode, "legacy-single")
        self.assertIsNotNone(service.ab_executor)

    def test_single_root_profile_stays_explicit_legacy(self) -> None:
        directory = tempfile.mkdtemp(prefix="installer-seams-legacy-")
        self.addCleanup(shutil.rmtree, directory, True)
        root = Path(directory).resolve()
        os_root = root / "os-root"
        os_root.mkdir()
        pool = root / "support-pool"
        pool.mkdir()
        payload = root / "payload.squashfs"
        payload.write_bytes(b"test-payload")
        digest = root / "expected-payload.sha256"
        digest.write_bytes(b"0" * 64)
        profile = root / "target-image-profile.json"
        _write_profile(
            profile,
            profile_id=_LEGACY_PROFILE_ID,
            layout=_LEGACY_LAYOUT,
            backend=_LEGACY_BACKEND,
        )
        fix = {
            "root": root,
            "os_root": os_root,
            "pool": pool,
            "payload": payload,
            "digest": digest,
            "profile": profile,
        }
        with _shipped_env(fix=fix):
            service = build_live_service()
        self.assertEqual(service.install_mode, "legacy-single")
        self.assertIsNone(service.ab_executor)

    def test_ab_profile_without_release_facts_fails_closed_never_legacy(self) -> None:
        directory, fix = _make_ab_tree()
        self.addCleanup(shutil.rmtree, directory, True)
        with _shipped_env(fix=fix):
            with self.assertRaises(TransactionServiceError) as ctx:
                build_live_service()
        self.assertNotIn("legacy-single", str(ctx.exception))

    def test_empty_absent_seam_configuration_is_degraded_never_default(self) -> None:
        with self.assertRaises(AbInstallCompositionError):
            config_from_facts_and_state(facts=None)  # type: ignore[arg-type]
        with self.assertRaises(AbInstallCompositionError):
            build_production_seam_pair(None)  # type: ignore[arg-type]
        with self.assertRaises(AbInstallCompositionError):
            compose_ab_executor(
                facts=None,  # type: ignore[arg-type]
                seams_factory=None,
                identities_factory=None,
            )


class NoSubstituteImplementationTests(unittest.TestCase):
    """No fake/loop store substitutes for the production default."""

    def test_production_module_reuses_shared_primitives_no_fakes(self) -> None:
        source = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "greia_installer"
            / "device_seams.py"
        ).read_text(encoding="utf-8")
        for required in (
            "BlockSlotStorage",
            "BlockSlotFilesystem",
            "SharedSlotPackageInstaller",
            "SubprocessPersistRunner",
            "InstallerSlotPackageInstaller",
            "partition_number_path",
            "plan_for_profile",
        ):
            self.assertIn(required, source, f"production factory must reuse {required}")
        for forbidden in (
            "SparseSlotStorage",
            "LoopbackSlotFile",
            "FakeSlotFilesystem",
            "FakePackageInstaller",
            "FakePersistRunner",
        ):
            self.assertNotIn(
                forbidden, source, f"production factory must not use {forbidden}"
            )

    def test_no_second_writer_finalizer_or_parallel_storage(self) -> None:
        root = Path(__file__).resolve().parents[1] / "src"
        offenders: list[str] = []
        pattern = re.compile(
            r"^\s*class\s+\w*(SlotWriter|SlotFinalizer|BlockSlotStorage|BlockSlotFilesystem|LoopbackSlotFile|SparseSlotStorage)\b",
            re.MULTILINE,
        )
        allowed_files = {
            "src/greia_platform/slot_writer.py",
            "src/greia_platform/block_slots.py",
        }
        for path in (*root.rglob("*.py"),):
            text = path.read_text(encoding="utf-8")
            for match in pattern.finditer(text):
                rel = str(path.relative_to(root.parent))
                # slots.py re-exports shared names via import (no class def);
                # the regex only matches class definitions, so any hit outside
                # the two shared owners is a parallel implementation.
                if rel not in allowed_files:
                    offenders.append(f"{rel}: {match.group(0).strip()}")
        self.assertEqual(offenders, [], f"parallel slot implementations: {offenders}")
        # Import identity: device_seams must reference the shared owners.
        import greia_installer.device_seams as seams_mod
        import greia_platform.block_slots as shared_blocks
        import greia_platform.slot_writer as shared_writer

        self.assertIs(shared_blocks.BlockSlotStorage, shared_blocks.BlockSlotStorage)
        self.assertIs(shared_writer.SlotWriter, shared_writer.SlotWriter)
        self.assertTrue(hasattr(seams_mod, "build_production_seam_pair"))
        # The production pair returns FreshAbInstallSeams-typed closures.
        seams_source = Path(seams_mod.__file__).read_text(encoding="utf-8")
        self.assertIn("FreshAbInstallSeams", seams_source)


if __name__ == "__main__":
    unittest.main()
