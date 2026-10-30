"""POSTR1-P2-INSTALLER-PROOF Gate-P2 negatives (fail-closed before mutation).

Each negative drives a shipped surface — ``build_live_service()`` (the exact
release composition root) or ``InstallTransactionService.handle_request``
(the exact socket-protocol framing) — and proves refusal happens for its
intended reason with zero destructive effect:

- missing unsigned v3 bundle → ``AbInstallCompositionError`` naming the bundle;
- legacy trusted-key-dir entry → ``AbInstallCompositionError`` naming the
  unknown key (v3 carries no key material);
- mismatched (mixed A/B + single-root) profile → composition error naming
  the mix, never a silent ``legacy-single`` fallback;
- A/B composition missing → ``TransactionServiceError`` naming ``GREIA_AB_``,
  never ``legacy-single``;
- selected target identity changing between ``PREPARE_PLAN`` and ``EXECUTE``
  → socket ``EXECUTE`` refused and the install backend never runs
  (plus a restore→GREEN positive control proving the detector is live).

Construction-level negatives block ``subprocess.run`` and assert fixture-tree
snapshot equality (no disk mutation). The socket-level negative asserts the
recording A/B executor has zero calls after the refused ``EXECUTE``.

Gate P2 green does not close T3-P: T3-P remains OPEN until Gate P5.

Offline only: disposable tmpdirs, fake probes/resolvers, no ``/etc`` /
``/run`` / ``/dev`` contact, no network, no signing.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

from greia_installer.composition import (
    AB_INSTALL_CONFIG_PATH_ENV,
    AbInstallCompositionError,
    install_mode_for_state,
)
from greia_installer.disk import (
    DeviceObservation,
    DiskInventory,
    LiveMediaAncestry,
    PcInternalTargetPolicy,
)
from greia_installer.engine import InstallResult
from greia_installer.install_transaction import INSTALLER_UI_UID
from greia_installer.transaction_client import InstallTransactionClient, TransactionClientError
from greia_installer.transaction_service import (
    InstallTransactionService,
    PlatformInstallAuthority,
    ServiceState,
    TransactionServiceError,
    build_live_service,
)
from greia_platform.privileged_channel import PeerCredential

GIB = 1024 * 1024 * 1024
MIB = 1024 * 1024

_AB_PROFILE_ID = "test-ab-negatives-v1"
_AB_FAMILY = "legacy-x86"
_AB_ARCH = "i386"
_AB_LAYOUT = "legacy-bios-ab-v1"
_AB_BACKEND = "grub-ab-v1"

_SHIPPED_ENV_NAMES = (
    "GREIA_OS_ROOT",
    "GREIA_INSTALL_PAYLOAD",
    "GREIA_INSTALL_PAYLOAD_DIGEST",
    "GREIA_TARGET_IMAGE_PROFILE",
    "GREIA_HARDWARE_SUPPORT_POOL",
)
_AB_ENV_NAMES = (
    "GREIA_AB_RELEASE_BUNDLE",
    "GREIA_AB_GRUB_PASSWORD_HASH",
    "GREIA_AB_DEVELOPER",
    "GREIA_AB_SUPPORT_INSTALLED_BYTES",
)

_AB_PASSWORD_HASH = "grub.pbkdf2.sha512.10000." + "N" * 64
_AB_SUPPORT_BOUND = 1 * MIB

UI_PEER = PeerCredential(uid=INSTALLER_UI_UID)
READY = "installer_ready"


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


def _write_ab_env_file(path: Path, *, bundle: Path) -> Path:
    path.write_text(
        "# disposable A/B facts for the Gate-P2 negatives\n"
        f"GREIA_AB_RELEASE_BUNDLE={bundle}\n"
        f"GREIA_AB_GRUB_PASSWORD_HASH={_AB_PASSWORD_HASH}\n"
        "GREIA_AB_DEVELOPER=0\n"
        f"GREIA_AB_SUPPORT_INSTALLED_BYTES={_AB_SUPPORT_BOUND}\n",
        encoding="utf-8",
    )
    return path


def _make_ab_tree(prefix: str = "installer-negatives-") -> tuple[str, dict[str, Path]]:
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
    env_file = root / "installer-ab.env"
    _write_ab_env_file(env_file, bundle=bundle)
    return directory, {
        "root": root,
        "os_root": os_root,
        "pool": pool,
        "payload": payload,
        "digest": digest,
        "profile": profile,
        "bundle": bundle,
        "env_file": env_file,
    }


def _snapshot(root: Path) -> set[str]:
    return {str(p.relative_to(root)) for p in root.rglob("*")}


@contextmanager
def _shipped_env(*, fix: dict[str, Path], config_path: Path | str | None = "default"):
    saved = {
        name: os.environ.get(name)
        for name in _SHIPPED_ENV_NAMES + _AB_ENV_NAMES + (AB_INSTALL_CONFIG_PATH_ENV,)
    }
    try:
        os.environ["GREIA_OS_ROOT"] = str(fix["os_root"])
        os.environ["GREIA_INSTALL_PAYLOAD"] = str(fix["payload"])
        os.environ["GREIA_INSTALL_PAYLOAD_DIGEST"] = str(fix["digest"])
        os.environ["GREIA_TARGET_IMAGE_PROFILE"] = str(fix["profile"])
        os.environ["GREIA_HARDWARE_SUPPORT_POOL"] = str(fix["pool"])
        for name in _AB_ENV_NAMES:
            os.environ.pop(name, None)
        if config_path == "default":
            os.environ[AB_INSTALL_CONFIG_PATH_ENV] = str(fix["env_file"])
        elif config_path is not None:
            os.environ[AB_INSTALL_CONFIG_PATH_ENV] = str(config_path)
        else:
            os.environ.pop(AB_INSTALL_CONFIG_PATH_ENV, None)
        yield
    finally:
        for name, value in saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def _no_block_commands():  # type: ignore[no-untyped-def]
    return mock.patch.object(
        subprocess, "run", side_effect=AssertionError("no block commands")
    )


def make_disk(
    name: str = "sda",
    *,
    serial: str = "SERIAL-NEG-1",
    wwn: str = "WWN-NEG-1",
    size_bytes: int = 8 * GIB,
    major_minor: str = "8:0",
) -> DeviceObservation:
    return DeviceObservation(
        name=name,
        path=Path(f"/dev/{name}"),
        size_bytes=size_bytes,
        device_type="disk",
        model="Test disk",
        serial=serial,
        transport="sata",
        removable=False,
        read_only=False,
        mountpoints=(),
        wwn=wwn,
        major_minor=major_minor,
    )


class _FakeProbe:
    def __init__(self, devices: list[DeviceObservation]) -> None:
        self.devices = list(devices)

    def probe(self) -> DiskInventory:
        return DiskInventory(tuple(self.devices), generation=1)


class _FakeResolver:
    def resolve(self, inventory: object = None) -> LiveMediaAncestry:
        return LiveMediaAncestry.empty()


class ConstructionNegativesTests(unittest.TestCase):
    """Missing/mismatched composition refuses before any disk mutation."""

    def test_missing_unsigned_bundle_fails_before_mutation(self) -> None:
        directory, fix = _make_ab_tree()
        self.addCleanup(shutil.rmtree, directory, True)
        fix["bundle"].unlink()
        before = _snapshot(fix["root"])
        with _shipped_env(fix=fix):
            with _no_block_commands():
                with self.assertRaisesRegex(
                    (AbInstallCompositionError, TransactionServiceError),
                    "(bundle|regular file)",
                ):
                    build_live_service()
        self.assertEqual(before, _snapshot(fix["root"]))

    def test_legacy_key_dir_entry_rejected_before_mutation(self) -> None:
        directory, fix = _make_ab_tree()
        self.addCleanup(shutil.rmtree, directory, True)
        with open(fix["env_file"], "a", encoding="utf-8") as handle:
            handle.write("GREIA_AB_TRUSTED_KEY_DIR=/no/such/keys\n")
        before = _snapshot(fix["root"])
        with _shipped_env(fix=fix):
            with _no_block_commands():
                with self.assertRaisesRegex(
                    (AbInstallCompositionError, TransactionServiceError),
                    "unknown key",
                ):
                    build_live_service()
        self.assertEqual(before, _snapshot(fix["root"]))

    def test_mismatched_profile_fails_before_mutation(self) -> None:
        directory, fix = _make_ab_tree()
        self.addCleanup(shutil.rmtree, directory, True)
        mixed = fix["root"] / "mixed-profile.json"
        _write_profile(
            mixed, profile_id=_AB_PROFILE_ID, layout=_AB_LAYOUT, backend="none-v1"
        )
        mixed_fix = dict(fix)
        mixed_fix["profile"] = mixed
        before = _snapshot(fix["root"])
        with _shipped_env(fix=mixed_fix):
            with _no_block_commands():
                with self.assertRaisesRegex(
                    (AbInstallCompositionError, TransactionServiceError),
                    "mixes",
                ) as ctx:
                    build_live_service()
        self.assertNotIn("legacy-single", str(ctx.exception))
        self.assertEqual(before, _snapshot(fix["root"]))

    def test_ab_composition_missing_never_falls_back_to_legacy(self) -> None:
        directory, fix = _make_ab_tree()
        self.addCleanup(shutil.rmtree, directory, True)
        missing = fix["root"] / "absent-installer-ab.env"
        before = _snapshot(fix["root"])
        with _shipped_env(fix=fix, config_path=missing):
            state = ServiceState.from_target_profile(
                fix["profile"],
                payload=fix["payload"],
                payload_digest=fix["digest"],
                project_root=fix["os_root"],
                hardware_support_pool=fix["pool"],
            )
            # The profile itself is still authoritatively A/B.
            self.assertEqual(install_mode_for_state(state), "ab")
            with _no_block_commands():
                with self.assertRaisesRegex(TransactionServiceError, "GREIA_AB_") as ctx:
                    build_live_service()
        self.assertNotIn("legacy-single", str(ctx.exception))
        self.assertEqual(before, _snapshot(fix["root"]))


class SocketIdentityChangeTests(unittest.TestCase):
    """PREPARE_PLAN → changed identity → EXECUTE refuses; backend never runs."""

    def _ab_service(self, devices: list[DeviceObservation]):  # type: ignore[no-untyped-def]
        probe = _FakeProbe(devices)
        resolver = _FakeResolver()
        calls: list[object] = []

        def _ab_executor(authorization, settings, locale, target):  # type: ignore[no-untyped-def]
            calls.append((authorization, target))
            return InstallResult()

        project_root = Path(__file__).resolve().parents[1]
        state = ServiceState(
            payload=Path("/run/live/medium/payload/greia-rootfs.squashfs"),
            payload_digest=Path("/etc/greia-os/expected-payload.sha256"),
            project_root=project_root,
            compatible_profile_id=_AB_PROFILE_ID,
            platform_family=_AB_FAMILY,
            architecture=_AB_ARCH,
            target_policy_id="pc-internal-v1",
            layout_adapter_id=_AB_LAYOUT,
            boot_backend=_AB_BACKEND,
            slot_bytes=1 * GIB,
            persist_minimum_bytes=256 * MIB,
        )
        authority = PlatformInstallAuthority(
            policy=PcInternalTargetPolicy(),
            compatible_profile=_AB_PROFILE_ID,
            probe=probe,  # type: ignore[arg-type]
            live_resolver=resolver,  # type: ignore[arg-type]
        )
        service = InstallTransactionService(
            authority=authority,
            state=state,
            ab_executor=_ab_executor,  # type: ignore[arg-type]
            install_mode="ab",
        )
        return service, probe, calls

    def _snapshot_settings(self) -> dict[str, str]:
        return {
            "touchpad_tap": "false",
            "touchpad_speed": "0.35",
            "mouse_speed": "0.0",
            "natural_scrolling": "false",
            "resolution": "auto",
            "keyboard_layout": "us",
            "mic_gain": "2.0",
            "disable_while_typing": "false",
            "locale": "en",
        }

    def _client(self, service):  # type: ignore[no-untyped-def]
        def _transport(raw: bytes) -> bytes:
            return service.handle_request(raw, peer=UI_PEER, boot_state=READY)

        return InstallTransactionClient(_transport)

    def test_changed_identity_between_prepare_and_execute_fails(self) -> None:
        service, probe, calls = self._ab_service([make_disk()])
        client = self._client(service)
        digest = next(
            item.identity_digest
            for item in service.authority.list_targets()
            if item.eligible
        )
        prepared = client.prepare(
            expected_target_identity=digest,
            compatible_profile_id=_AB_PROFILE_ID,
            settings_snapshot=self._snapshot_settings(),
        )
        # The disk is swapped: a different durable identity answers now.
        probe.devices = [
            make_disk(name="sdb", serial="SERIAL-NEG-2", wwn="WWN-NEG-2")
        ]
        with self.assertRaises(TransactionClientError):
            client.execute(
                transaction_nonce=prepared.transaction_nonce,
                plan_digest=prepared.plan_digest,
            )
        self.assertEqual(calls, [], "refused EXECUTE must never reach the A/B backend")

    def test_unchanged_identity_restores_green(self) -> None:
        """Positive control: same identity through the same path installs."""
        service, probe, calls = self._ab_service([make_disk()])
        client = self._client(service)
        digest = next(
            item.identity_digest
            for item in service.authority.list_targets()
            if item.eligible
        )
        prepared = client.prepare(
            expected_target_identity=digest,
            compatible_profile_id=_AB_PROFILE_ID,
            settings_snapshot=self._snapshot_settings(),
        )
        receipt = client.execute(
            transaction_nonce=prepared.transaction_nonce,
            plan_digest=prepared.plan_digest,
        )
        self.assertEqual(receipt.target_identity, digest)
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
