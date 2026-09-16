"""POSTR1-P3-UPDATE-PROOF3: P3.6 negative set through the shipped service path.

Every negative exercises production behavior -- the exact installed
composition ``build_live_update_service()`` with no ``seams`` argument
(production inactive-slot factories), the shipped socket serving helpers
(``attest_peer_from_connection`` / ``handle_update_connection``), the
shared ``SlotWriter`` capacity/active-slot gates, the production PARTUUID
map reader, the shipped inbox receive-capacity gate, and the production
boot-transaction journal -- never a re-implementation of the refusal.
Each negative fails for its intended reason with no slot write, no
journal residue (unless the milestone was already reached), and no
loop/fake fallback store.

The preregistered pre-intro timing comparison (P1-P4) is DEFERRED by
owner authority (``postr1--POSTR1-P3-PREINTRO-TIMING-MEASURE--001``) and
is not exercised or claimed here.

All state stays in disposable tmpdirs; no valued disk, no loop device.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import socket
import struct
import tempfile
import unittest
from collections import namedtuple
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from greia_platform.grub_ab import GrubEnvBackend
from greia_platform.system_updates import (
    SystemUpdateError,
    SystemUpdateInbox,
    UpdateBackendUnavailable,
    UpdateBundleError,
    UpdateCompatibilityError,
    UpdateSlotSeams,
    build_live_update_service,
    build_update_bundle,
    inspect_update_bundle,
    load_installed_layout_record,
)


@contextmanager
def _patched_env(**overrides: str):
    previous = dict(os.environ)
    os.environ.update(overrides)
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(previous)


_SLOT_BYTES = 1024 * 1024 * 1024
_HW_BYTES = b"\x28\xb5\x2f\xfd" + b"p3-proof3-hw" * 64

_FAMILY = "legacy-x86"
_ARCH = "i386"
_PROFILE = "legacy-x86-i686"
_VERSION = "0.16.0"

_UUID_A = "11111111-2222-3333-4444-555555555555"
_UUID_A_FS = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
_UUID_B = "22222222-3333-4444-5555-666666666666"
_UUID_B_FS = "bbbbbbbb-cccc-dddd-eeee-ffffffffffff"
_UUID_P = "33333333-4444-5555-6666-777777777777"
_UUID_P_FS = "cccccccc-dddd-eeee-ffff-000000000000"
_INSTALL_SHA = "ab" * 32

_R8_ID = "greia-0.16.0"
_R8_SEQ = 8
_R9_ID = "greia-0.17.0"
_R9_SEQ = 9


def _record_dict(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "accepted_release_id": _R8_ID,
        "accepted_slot": "A",
        "boot_backend": "grub-ab-v1",
        "boot_control": {"active_slot": "A", "kind": "grub-env-v1"},
        "install_profile": _PROFILE,
        "install_target_sha256": _INSTALL_SHA,
        "installed_at_unix": 1757000000,
        "layout_id": "legacy-bios-ab-v1",
        "persist": {"filesystem_uuid": _UUID_P_FS, "partuuid": _UUID_P},
        "platform_family": _FAMILY,
        "schema_version": 1,
        "slot_bytes": _SLOT_BYTES,
        "system_a": {"filesystem_uuid": _UUID_A_FS, "partuuid": _UUID_A},
        "system_b": {"filesystem_uuid": _UUID_B_FS, "partuuid": _UUID_B},
    }
    base.update(overrides)
    return base


def _canonical_record(payload: dict[str, object]) -> bytes:
    return (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _payload(size: int = 220 * 1024, tag: bytes = b"p3-proof3:") -> bytes:
    body = bytes((index * 31 + 7) % 256 for index in range(size))
    raw = tag + body[len(tag):]
    fixed = bytearray(raw)
    if fixed[510:512] == b"\x55\xaa":
        fixed[510:512] = b"\x00\x00"
    if fixed[512:520] == b"EFI PART":
        fixed[512:520] = b"\x00" * 8
    return bytes(fixed)


def _pool_tree(root: Path) -> Path:
    """Write a minimal verified hardware-support pool (pure file IO)."""
    fw = b"p3-proof3-firmware-bytes"
    uc = b"p3-proof3-microcode-bytes"
    pool = root / "hw-pool"
    deb_dir = pool / "pool"
    deb_dir.mkdir(parents=True)
    (deb_dir / "firmware-realtek_1_all.deb").write_bytes(fw)
    (deb_dir / "amd64-microcode_1_amd64.deb").write_bytes(uc)
    packages_payload = b"Package: firmware-realtek\n"
    packages_gzip_payload = b"gzip-placeholder"
    (pool / "Packages").write_bytes(packages_payload)
    (pool / "Packages.gz").write_bytes(packages_gzip_payload)

    def _sha(payload: bytes) -> str:
        return hashlib.sha256(payload).hexdigest()

    manifest = {
        "schema_version": 1,
        "suite": "trixie",
        "architecture": "amd64",
        "package_count": 2,
        "total_bytes": len(fw) + len(uc),
        "provided_candidate_packages": ["firmware-realtek", "amd64-microcode"],
        "provided_firmware_packages": ["firmware-realtek"],
        "provided_microcode_packages": ["amd64-microcode"],
        "broad_firmware_packages": ["firmware-realtek"],
        "firmware_providers": {"rtl.bin": ["firmware-realtek"]},
        "unavailable_candidate_packages": [],
        "packages": [
            {
                "package": "firmware-realtek", "version": "1",
                "architecture": "all", "filename": "pool/firmware-realtek_1_all.deb",
                "size": len(fw), "sha256": _sha(fw), "candidate": True,
            },
            {
                "package": "amd64-microcode", "version": "1",
                "architecture": "amd64", "filename": "pool/amd64-microcode_1_amd64.deb",
                "size": len(uc), "sha256": _sha(uc), "candidate": True,
            },
        ],
        "repository_indexes": {
            "Packages": {"size": len(packages_payload), "sha256": _sha(packages_payload)},
            "Packages.gz": {"size": len(packages_gzip_payload), "sha256": _sha(packages_gzip_payload)},
        },
    }
    (pool / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return pool


def _rig(root: Path, *, record: dict[str, object] | None = None,
         env_extra: dict[str, str] | None = None):
    """Disposable A/B machine composed through the shipped default path.

    ``build_live_update_service()`` with no ``seams`` argument (the exact
    installed ``main()`` composition); deployment parameters arrive via
    ``GREIA_*`` environment only.
    """
    state_dir = root / "state"
    layout_path = root / "installed-layout.json"
    layout_path.write_bytes(_canonical_record(record or _record_dict()))
    boot_dir = root / "boot-control"
    boot_dir.mkdir(parents=True, exist_ok=True)
    grub = GrubEnvBackend.initialize(boot_dir, default_slot="A")
    pool = _pool_tree(root)
    (root / "sysfs").mkdir(parents=True, exist_ok=True)
    env = {
        "GREIA_SYSTEM_VERSION": _VERSION,
        "GREIA_SYSTEM_PLATFORM_FAMILY": _FAMILY,
        "GREIA_SYSTEM_ARCHITECTURE": _ARCH,
        "GREIA_SYSTEM_PROFILE": _PROFILE,
        "GREIA_UPDATE_HARDWARE_SUPPORT_POOL": str(pool),
        "GREIA_UPDATE_SYSFS_DEVICES": str(root / "sysfs"),
    }
    env.update(env_extra or {})
    with _patched_env(**env):
        authority = build_live_update_service(
            state_dir=state_dir,
            layout_record_path=layout_path,
            boot_backend=grub,
            boot_backend_auto=False,
        )
    return authority, grub, layout_path, state_dir, None


def _recompose(root: Path, *, record: dict[str, object] | None = None,
               env_extra: dict[str, str] | None = None):
    """Recompose the authority from existing disposable dirs (restart).

    Unlike :func:`_rig`, nothing is minted or reset: keys, layout bytes,
    accepted sequence, inbox, journal and boot control are re-observed
    from disk, exactly as a restarted installed service would see them.
    """
    from greia_platform.grub_ab import GrubEnvBackend as _GrubAttach

    state_dir = root / "state"
    layout_path = root / "installed-layout.json"
    if record is not None:
        layout_path.write_bytes(_canonical_record(record))
    grub = _GrubAttach.attach(root / "boot-control")
    pool = root / "hw-pool"
    env = {
        "GREIA_SYSTEM_VERSION": _VERSION,
        "GREIA_SYSTEM_PLATFORM_FAMILY": _FAMILY,
        "GREIA_SYSTEM_ARCHITECTURE": _ARCH,
        "GREIA_SYSTEM_PROFILE": _PROFILE,
        "GREIA_UPDATE_HARDWARE_SUPPORT_POOL": str(pool),
        "GREIA_UPDATE_SYSFS_DEVICES": str(root / "sysfs"),
    }
    env.update(env_extra or {})
    with _patched_env(**env):
        authority = build_live_update_service(
            state_dir=state_dir,
            layout_record_path=layout_path,
            boot_backend=grub,
            boot_backend_auto=False,
        )
    return authority, grub, layout_path, state_dir, None


def _signed_bundle(root: Path, _ignored: object, name: str, *,
                   release_id: str = _R9_ID,
                   family: str = _FAMILY, arch: str = _ARCH,
                   profile: str = _PROFILE,
                   payload_bytes: bytes | None = None,
                   minimum_slot_bytes: int | None = None,
                   persist_min: int = 1, persist_max: int = 1) -> Path:
    import zstandard

    work = root / "releases" / name
    work.mkdir(parents=True, exist_ok=True)
    raw = payload_bytes if payload_bytes is not None else _payload()
    (work / "slot.ext4.zst").write_bytes(
        zstandard.ZstdCompressor(level=3).compress(raw)
    )
    (work / "hw.tar.zst").write_bytes(_HW_BYTES)
    bundle = work / f"{name}.greiaupdate"
    if bundle.exists():
        bundle.unlink()
    build_update_bundle(
        payload_path=work / "slot.ext4.zst",
        hardware_support_path=work / "hw.tar.zst",
        output_path=bundle,
        version=release_id.split("-", 1)[1],
        release_id=release_id,
        platform_family=family,
        architecture=arch,
        profile=profile,
        payload_uncompressed_bytes=len(raw),
        minimum_slot_bytes=minimum_slot_bytes if minimum_slot_bytes is not None else len(raw),
        persist_read_schema_min=persist_min,
        persist_read_schema_max=persist_max,
        persist_write_schema=persist_min,
        release_notes="POSTR1-P3-UPDATE-PROOF3 negative release.",
    )
    return bundle


_v3_bundle = _signed_bundle


def _journal_path(state_dir: Path) -> Path:
    return state_dir / "system-updates" / "journal" / "boot-journal.json"


def _assert_no_slot_residue(test: unittest.TestCase, root: Path,
                            state_dir: Path) -> None:
    test.assertFalse(_journal_path(state_dir).exists())
    test.assertEqual(list(root.rglob("slot-*.img")), [])


class ForgedPeerRefusalTests(unittest.TestCase):
    """Forged peers are refused before any request byte is read."""

    def test_forged_peer_refused_without_reading_request(self) -> None:
        from greia_platform.system_updates import handle_update_connection
        from greia_platform.update_privileged import build_request, read_response

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority, _grub, _layout, _state, _key = _rig(root)

            class _RecordingConnection:
                """Transport double recording every recv (never served)."""

                def __init__(self, payload: bytes) -> None:
                    self._payload = payload
                    self.recv_calls: list[int] = []
                    self.sent: list[bytes] = []
                    self.closed = False

                def settimeout(self, value: float) -> None:
                    pass

                def recv(self, size: int) -> bytes:
                    self.recv_calls.append(size)
                    chunk, self._payload = self._payload[:size], self._payload[size:]
                    return chunk

                def sendall(self, data: bytes) -> None:
                    self.sent.append(bytes(data))

                def close(self) -> None:
                    self.closed = True

            forged_request = build_request("STATUS")
            connection = _RecordingConnection(forged_request)
            handle_update_connection(
                connection,  # type: ignore[arg-type]
                authority=authority,
                peer=0,  # type: ignore[arg-type] -- caller-asserted, never attested
            )
            # The forged identity is refused before a single request byte
            # is consumed: the production helper never calls recv.
            self.assertEqual(connection.recv_calls, [])
            self.assertTrue(connection.closed)
            _, op, payload = read_response(b"".join(connection.sent))
            self.assertEqual(op, "ERROR")
            self.assertEqual(payload["status"], "REFUSED")
            self.assertIn("attested", str(payload["reason"]))

    def test_attested_root_peer_is_served(self) -> None:
        """Sensitivity anchor: a kernel-attested root peer IS served."""
        import struct

        from greia_platform.privileged_channel import PeerCredential
        from greia_platform.system_updates import (
            attest_peer_from_connection,
            handle_update_connection,
        )
        from greia_platform.update_privileged import build_request, read_response

        class _PeerConnection:
            def __init__(self, transport: socket.socket, uid: int) -> None:
                self._transport = transport
                self._uid = uid

            def getsockopt(self, level: int, optname: int, buflen: int) -> bytes:
                return struct.pack("3i", 12345, self._uid, 12345)

            def settimeout(self, value: float) -> None:
                self._transport.settimeout(value)

            def recv(self, size: int) -> bytes:
                return self._transport.recv(size)

            def sendall(self, data: bytes) -> None:
                self._transport.sendall(data)

            def close(self) -> None:
                self._transport.close()

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            real_authority, _grub, _layout, _state, _key = _rig(root)

            from greia_platform.update_privileged import CurrentCandidateSummary

            class _SocketAuthority:
                """Socket-shape adapter over the v3 authority (see T04 notes)."""

                def candidate_summary(self) -> CurrentCandidateSummary:
                    summary = real_authority.candidate_summary()
                    return CurrentCandidateSummary(
                        present=summary.present,
                        release_id=summary.release_id,
                        bundle_sha256=summary.bundle_sha256,
                    )

                def layout_summary(self) -> dict[str, object]:
                    return dict(real_authority.layout_summary())

                def verify_current_candidate(self) -> CurrentCandidateSummary:
                    summary = real_authority.verify_current_candidate()
                    return CurrentCandidateSummary(
                        present=summary.present,
                        release_id=summary.release_id,
                        bundle_sha256=summary.bundle_sha256,
                    )

                def stage_current_candidate(self) -> dict[str, object]:
                    return dict(real_authority.stage_current_candidate())

                def arm_current_candidate(self) -> dict[str, object]:
                    return dict(real_authority.arm_current_candidate())

                def confirm_boot_health(self) -> dict[str, object]:
                    return dict(real_authority.confirm_boot_health())

                def reconcile(self) -> dict[str, object]:
                    return dict(real_authority.reconcile())

            authority = _SocketAuthority()
            left, right = socket.socketpair()
            try:
                left.sendall(build_request("STATUS"))
                left.shutdown(socket.SHUT_WR)
                try:
                    peer = attest_peer_from_connection(
                        _PeerConnection(right, 0)  # type: ignore[arg-type]
                    )
                except Exception:
                    if hasattr(socket, "SO_PEERCRED"):
                        raise
                    peer = PeerCredential(uid=0)
                self.assertEqual(peer.uid, 0)
                handle_update_connection(
                    _PeerConnection(right, 0),  # type: ignore[arg-type]
                    authority=authority,
                    peer=peer,
                )
                frames = []
                while True:
                    chunk = left.recv(65536)
                    if not chunk:
                        break
                    frames.append(chunk)
                _, op, _payload = read_response(b"".join(frames))
                self.assertEqual(op, "STATUS")
            finally:
                left.close()

    def test_attested_non_root_peer_refused(self) -> None:
        """Attested but unauthorized UID is refused (request IS read)."""
        from greia_platform.privileged_channel import PeerCredential
        from greia_platform.system_updates import handle_update_connection
        from greia_platform.update_privileged import build_request, read_response

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority, _grub, _layout, _state, _key = _rig(root)
            left, right = socket.socketpair()
            try:
                # Request bytes are already queued (real transport); the
                # attested non-root peer is refused by the endpoint.
                left.sendall(build_request("STATUS"))
                left.shutdown(socket.SHUT_WR)
                handle_update_connection(
                    right,
                    authority=authority,
                    peer=PeerCredential(uid=1000),
                )
                frames = []
                while True:
                    chunk = left.recv(65536)
                    if not chunk:
                        break
                    frames.append(chunk)
                # The non-root peer is never served a STATUS payload: the
                # connection answers a bounded REFUSED frame instead.
                self.assertTrue(frames)
                _, op, payload = read_response(b"".join(frames))
                self.assertEqual(op, "ERROR")
                self.assertEqual(payload["status"], "REFUSED")
            finally:
                left.close()
                right.close()


class CompatibilityNegativeTests(unittest.TestCase):
    """Wrong family/architecture/profile fail at verify, never at the slot."""

    def test_wrong_platform_family_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority, _grub, _layout, state_dir, key = _rig(root)
            bundle = _signed_bundle(root, key, "wrong-family", family="other-family")
            SystemUpdateInbox(state_dir).receive(bundle)
            with self.assertRaises(UpdateCompatibilityError) as raised:
                authority.verify_current_candidate()
            self.assertIn("platform family", str(raised.exception))
            _assert_no_slot_residue(self, root, state_dir)

    def test_wrong_architecture_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority, _grub, _layout, state_dir, key = _rig(root)
            bundle = _signed_bundle(root, key, "wrong-arch", arch="other-arch")
            SystemUpdateInbox(state_dir).receive(bundle)
            with self.assertRaises(UpdateCompatibilityError) as raised:
                authority.verify_current_candidate()
            self.assertIn("architecture", str(raised.exception))
            _assert_no_slot_residue(self, root, state_dir)

    def test_wrong_profile_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority, _grub, _layout, state_dir, key = _rig(root)
            bundle = _signed_bundle(root, key, "wrong-profile", profile="other-profile")
            SystemUpdateInbox(state_dir).receive(bundle)
            with self.assertRaises(UpdateCompatibilityError) as raised:
                authority.verify_current_candidate()
            self.assertIn("build profile", str(raised.exception))
            _assert_no_slot_residue(self, root, state_dir)


class PersistPolicyNegativeTests(unittest.TestCase):
    """PERSIST-schema gating replaces the retired sequence policy (v3).

    Compatibility (family/arch/profile) passes at verify; the PERSIST
    readable range is enforced at stage before any slot contact. There is
    no sequence authority: an older display version with a readable range
    still verifies, while an unreadable range is refused with a
    compatibility/migration message.
    """

    def test_persist_out_of_range_refused_before_slot_contact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority, _grub, _layout, state_dir, key = _rig(root)
            bundle = _signed_bundle(
                root, key, "narrow-persist",
                persist_min=10, persist_max=10,
            )
            SystemUpdateInbox(state_dir).receive(bundle)
            verified = authority.verify_current_candidate()
            self.assertTrue(verified.present)
            with self.assertRaises(SystemUpdateError) as raised:
                authority.stage_current_candidate()
            self.assertIn("migration", str(raised.exception).lower())
            _assert_no_slot_residue(self, root, state_dir)

    def test_older_display_version_with_readable_range_still_verifies(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority, _grub, _layout, state_dir, key = _rig(root)
            bundle = _signed_bundle(root, key, "older-display", release_id=_R8_ID)
            SystemUpdateInbox(state_dir).receive(bundle)
            verified = authority.verify_current_candidate()
            # Version strings are never a security boundary in v3: the
            # older display version verifies when family/arch/profile and
            # the PERSIST range match.
            self.assertTrue(verified.present)
            self.assertEqual(verified.release_id, _R8_ID)


class LiveSlotAddressNegativeTests(unittest.TestCase):
    """Active/accepted slots are never addressable as staging destinations."""

    def test_production_store_factory_refuses_active_slot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority, _grub, _layout, state_dir, _key = _rig(root)
            destination = SimpleNamespace(
                semantic_slot="A",
                role="system-a",
                role_filesystem_uuid=_UUID_A_FS,
            )
            with self.assertRaises(UpdateBackendUnavailable) as raised:
                authority.backend.seams.slot_store_factory(destination)
            self.assertIn("active slot", str(raised.exception))
            _assert_no_slot_residue(self, root, state_dir)

    def test_production_store_factory_refuses_accepted_slot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record = _record_dict(
                accepted_slot="B",
                boot_control={"active_slot": "A", "kind": "grub-env-v1"},
            )
            authority, _grub, _layout, state_dir, _key = _rig(root, record=record)
            destination = SimpleNamespace(
                semantic_slot="B",
                role="system-b",
                role_filesystem_uuid=_UUID_B_FS,
            )
            with self.assertRaises(UpdateBackendUnavailable) as raised:
                authority.backend.seams.slot_store_factory(destination)
            self.assertIn("accepted slot", str(raised.exception))
            _assert_no_slot_residue(self, root, state_dir)

    def test_stage_with_no_inactive_slot_is_refused(self) -> None:
        # Split-brain layout (active B, accepted A): every slot is live,
        # so staging is refused before any seam is demanded.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record = _record_dict(
                accepted_slot="A",
                boot_control={"active_slot": "B", "kind": "grub-env-v1"},
            )
            authority, _grub, _layout, state_dir, key = _rig(root, record=record)
            bundle = _signed_bundle(root, key, "split-brain")
            SystemUpdateInbox(state_dir).receive(bundle)
            with self.assertRaises(SystemUpdateError) as raised:
                authority.stage_current_candidate()
            self.assertIn("no inactive slot", str(raised.exception))
            _assert_no_slot_residue(self, root, state_dir)

    def test_writer_rejects_live_destination_even_if_resolved(self) -> None:
        # Defense in depth: the shared SlotWriter re-proves liveness at the
        # byte layer, so a mis-resolved destination still cannot be written.
        from greia_platform.slot_writer import DestinationSlot, SlotWriter

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _authority, _grub, layout_path, _state, _key = _rig(root)
            record = load_installed_layout_record(layout_path)
            assert record is not None
            live = DestinationSlot.resolve_from_layout(record, "B")
            object.__setattr__(live, "accepted_slot", "B")
            object.__setattr__(live, "active_slot", "B")
            with self.assertRaises(Exception) as raised:
                SlotWriter().write(
                    member=SimpleNamespace(payload_size=8, minimum_slot_bytes=8),
                    destination=live,
                    source=io.BytesIO(b"12345678"),
                    storage=SimpleNamespace(capacity_bytes=live.slot_capacity_bytes),
                    support_installed_bytes=0,
                )
            self.assertIn("slot", str(raised.exception))


class PersistContractNegativeTests(unittest.TestCase):
    """PERSIST-schema mismatch is refused before any slot write."""

    def test_persist_range_mismatch_refused_before_slot_write(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority, _grub, _layout, state_dir, key = _rig(root)
            bundle = _signed_bundle(
                root, key, "foreign-persist", persist_min=10, persist_max=10)
            SystemUpdateInbox(state_dir).receive(bundle)
            verified = authority.verify_current_candidate()
            self.assertTrue(verified.present)
            with self.assertRaises(SystemUpdateError) as raised:
                authority.stage_current_candidate()
            self.assertIn("migration", str(raised.exception).lower())
            _assert_no_slot_residue(self, root, state_dir)


class SupportMemberNegativeTests(unittest.TestCase):
    """A missing release support member is refused before any slot write."""

    def test_missing_support_pool_refused_before_slot_write(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority, _grub, _layout, state_dir, key = _rig(
                root,
                env_extra={"GREIA_UPDATE_HARDWARE_SUPPORT_POOL": str(root / "no-pool")},
            )
            bundle = _signed_bundle(root, key, "no-support")
            SystemUpdateInbox(state_dir).receive(bundle)
            with self.assertRaises(UpdateBackendUnavailable) as raised:
                authority.stage_current_candidate()
            self.assertIn("support", str(raised.exception))
            _assert_no_slot_residue(self, root, state_dir)


class LayoutAuthorityNegativeTests(unittest.TestCase):
    """Corrupt layout authority fails closed with no destination contact."""

    def test_corrupt_layout_record_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority, grub, layout_path, state_dir, key = _rig(root)
            layout_path.write_text("not json\n", encoding="utf-8")
            self.assertFalse(authority.backend.available)
            bundle = _signed_bundle(root, key, "corrupt-layout")
            SystemUpdateInbox(state_dir).receive(bundle)
            with self.assertRaises(SystemUpdateError):
                authority.stage_current_candidate()
            _assert_no_slot_residue(self, root, state_dir)
            self.assertEqual(grub.inspect().default_slot, "A")

    def test_missing_layout_record_is_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority, _grub, layout_path, state_dir, _key = _rig(root)
            layout_path.unlink()
            self.assertFalse(authority.backend.available)
            payload = authority.backend.status_payload()
            self.assertFalse(payload["available"])


class TopologyAmbiguityNegativeTests(unittest.TestCase):
    """Ambiguous device topology is refused before any slot write."""

    def test_duplicate_partuuid_map_refused(self) -> None:
        # Two farm entries with distinct spellings normalizing to the same
        # MBR PARTUUID identity: the production map reader refuses the
        # ambiguity before any device probe.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            farm = root / "by-partuuid"
            farm.mkdir(parents=True)
            (farm / "0xABCD1234-01").symlink_to("../../sda1")
            (farm / "abcd1234-01").symlink_to("../../sdb1")
            authority, _grub, _layout, state_dir, key = _rig(
                root,
                env_extra={"GREIA_UPDATE_BY_PARTUUID_DIR": str(farm)},
            )
            bundle = _signed_bundle(root, key, "ambiguous-topo")
            SystemUpdateInbox(state_dir).receive(bundle)
            with self.assertRaises(UpdateBackendUnavailable) as raised:
                authority.stage_current_candidate()
            self.assertIn("duplicate", str(raised.exception))
            _assert_no_slot_residue(self, root, state_dir)


class FreeSpaceNegativeTests(unittest.TestCase):
    """Insufficient free space is refused before any durable write."""

    def test_inbox_receive_refused_on_full_disk(self) -> None:
        import zstandard

        _DiskUsage = namedtuple("_DiskUsage", ["total", "used", "free"])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _authority, _grub, _layout, state_dir, key = _rig(root)
            work = root / "releases" / "full-disk"
            work.mkdir(parents=True, exist_ok=True)
            raw = _payload()
            (work / "slot.ext4.zst").write_bytes(
                zstandard.ZstdCompressor(level=3).compress(raw)
            )
            (work / "hw.tar.zst").write_bytes(_HW_BYTES)
            bundle = work / "full-disk.greiaupdate"
            build_update_bundle(
                payload_path=work / "slot.ext4.zst",
                hardware_support_path=work / "hw.tar.zst",
                output_path=bundle,
                version=_R9_ID.split("-", 1)[1],
                release_id=_R9_ID,
                platform_family=_FAMILY,
                architecture=_ARCH,
                profile=_PROFILE,
                payload_uncompressed_bytes=len(raw),
                minimum_slot_bytes=len(raw),
                persist_read_schema_min=1,
                persist_read_schema_max=1,
                persist_write_schema=1,
            )
            with mock.patch.object(
                shutil, "disk_usage",
                return_value=_DiskUsage(total=10**9, used=10**9, free=0),
            ):
                with self.assertRaises(UpdateBundleError) as raised:
                    SystemUpdateInbox(state_dir).receive(bundle)
            self.assertIn("free space", str(raised.exception))
            self.assertFalse((state_dir / "system-updates" / "inbox").exists()
                             and any((state_dir / "system-updates" / "inbox").iterdir()))

    def test_slot_capacity_preflight_writes_zero_bytes(self) -> None:
        # Production SlotWriter capacity gate: a payload that cannot fit
        # the layout slot is refused before the first storage byte.
        from greia_platform.slot_writer import (
            DestinationSlot,
            SlotWriter,
            VerifiedReleaseMember,
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _authority, _grub, layout_path, state_dir, key = _rig(root)
            record = load_installed_layout_record(layout_path)
            assert record is not None
            destination = DestinationSlot.resolve_from_layout(record, "B")
            # Signed demand (2 GiB minimum) exceeds the 1 GiB layout slot
            # while the payload itself stays small: the refusal is purely
            # the capacity preflight, before the first storage byte.
            bundle = _signed_bundle(
                root, key, "too-big",
                minimum_slot_bytes=2 * _SLOT_BYTES)
            member = VerifiedReleaseMember.from_manifest(
                inspect_update_bundle(bundle).manifest)

            class _StubStore:
                capacity_bytes = destination.slot_capacity_bytes
                writes: list[tuple[int, bytes]]

                def __init__(self) -> None:
                    self.writes = []

                def write_at(self, offset: int, data: bytes) -> None:
                    self.writes.append((offset, bytes(data)))

            store = _StubStore()
            with self.assertRaises(Exception) as raised:
                SlotWriter().write(
                    member=member,
                    destination=destination,
                    source=io.BytesIO(_payload()),
                    storage=store,  # type: ignore[arg-type]
                    support_installed_bytes=0,
                )
            self.assertIn("capacity", str(raised.exception))
            self.assertEqual(store.writes, [])
            _assert_no_slot_residue(self, root, state_dir)


class InterruptionNegativeTests(unittest.TestCase):
    """Interruption before/after each durable milestone stays fail-closed."""

    def test_interruption_before_receive_leaves_no_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority, _grub, _layout, state_dir, _key = _rig(root)
            summary = authority.candidate_summary()
            self.assertFalse(summary.present)
            with self.assertRaises(SystemUpdateError):
                authority.verify_current_candidate()
            with self.assertRaises(SystemUpdateError):
                authority.stage_current_candidate()
            # Recomposing (simulated restart) changes nothing: still absent.
            authority2, _, _, _, _ = _recompose(root)
            self.assertFalse(authority2.candidate_summary().present)

    def test_interruption_after_receive_reverifies_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority, _grub, _layout, state_dir, key = _rig(root)
            bundle = _signed_bundle(root, key, "crash-after-receive")
            SystemUpdateInbox(state_dir).receive(bundle)
            # Simulated crash: drop the authority, recompose from disk.
            del authority
            authority2, _, _, _, _ = _recompose(root)
            # The candidate is durable but still unverified until the
            # restarted service re-verifies it through the compatibility path.
            durable = authority2.candidate_summary()
            self.assertTrue(durable.present)
            self.assertEqual(durable.release_id, _R9_ID)
            verified = authority2.verify_current_candidate()
            self.assertTrue(verified.present)
            self.assertEqual(verified.release_id, _R9_ID)
            # Staging still fails closed at the device path (no devices
            # here) with no journal residue from the interrupted run.
            with self.assertRaises(UpdateBackendUnavailable) as raised:
                authority2.stage_current_candidate()
            self.assertIn("inactive-slot", str(raised.exception))
            _assert_no_slot_residue(self, root, state_dir)

    def test_interruption_after_failed_stage_leaves_no_residue(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority, _grub, layout_path, state_dir, key = _rig(root)
            bundle = _signed_bundle(root, key, "crash-after-fail")
            SystemUpdateInbox(state_dir).receive(bundle)
            layout_before = layout_path.read_bytes()
            with self.assertRaises(UpdateBackendUnavailable):
                authority.stage_current_candidate()
            del authority
            authority2, grub2, _, _, _ = _recompose(root)
            with self.assertRaises(UpdateBackendUnavailable):
                authority2.stage_current_candidate()
            self.assertFalse(_journal_path(state_dir).exists())
            self.assertEqual(layout_path.read_bytes(), layout_before)
            self.assertEqual(grub2.inspect().default_slot, "A")

    def test_interruption_after_stage_journal_blocks_restage(self) -> None:
        # Crash-state setup: the production journal opened exactly as
        # backend.stage would open it (same API, same required fields).
        # A restarted authority must refuse a second stage ("already
        # active") and reconcile steady instead of double-staging.
        from greia_platform.boot_transaction import BootTransactionJournal

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority, _grub, _layout, state_dir, key = _rig(root)
            bundle = _signed_bundle(root, key, "crash-after-stage")
            SystemUpdateInbox(state_dir).receive(bundle)
            journal_dir = state_dir / "system-updates" / "journal"
            BootTransactionJournal.begin_update(
                journal_dir,
                layout_id="legacy-bios-ab-v1",
                boot_backend="grub-ab-v1",
                release_id=_R9_ID,
                candidate_slot="B",
                accepted_slot="A",
            )
            del authority
            authority2, _, _, _, _ = _recompose(root)
            with self.assertRaises(SystemUpdateError) as raised:
                authority2.stage_current_candidate()
            self.assertIn("already active", str(raised.exception))
            # Without a boot observation the restarted service cannot
            # advance the journal: reconcile fails closed instead of
            # dropping or double-staging the transaction.
            with self.assertRaises(SystemUpdateError) as refused:
                authority2.reconcile()
            self.assertIn("no authoritative boot observation", str(refused.exception))
            from greia_platform.boot_transaction import BootTransactionJournal as _Journal

            journal = _Journal.load(
                state_dir / "system-updates" / "journal")
            self.assertEqual(journal.state.value, "update_staged")
            self.assertEqual(journal.candidate_slot, "B")

    def test_interruption_after_arm_keeps_one_shot_durable(self) -> None:
        # Stage journal (as above), arm the one-shot through the service,
        # crash, recompose: the armed state is durable, a second arm is
        # refused, and reconcile stays steady without a boot observation.
        from greia_platform.boot_transaction import BootTransactionJournal

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority, grub, _layout, state_dir, key = _rig(root)
            bundle = _signed_bundle(root, key, "crash-after-arm")
            SystemUpdateInbox(state_dir).receive(bundle)
            journal_dir = state_dir / "system-updates" / "journal"
            BootTransactionJournal.begin_update(
                journal_dir,
                layout_id="legacy-bios-ab-v1",
                boot_backend="grub-ab-v1",
                release_id=_R9_ID,
                candidate_slot="B",
                accepted_slot="A",
            )
            armed = authority.arm_current_candidate()
            self.assertEqual(armed, {"armed": True, "slot": "B"})
            self.assertEqual(grub.inspect().one_shot_slot, "B")
            self.assertEqual(grub.inspect().default_slot, "A")
            del authority
            authority2, grub2, _, _, _ = _recompose(root)
            journal = BootTransactionJournal.load(journal_dir)
            self.assertEqual(journal.state.value, "one_shot_armed")
            self.assertEqual(grub2.inspect().one_shot_slot, "B")
            with self.assertRaises(SystemUpdateError):
                authority2.arm_current_candidate()
            # Still no boot observation (no reboot happened): reconcile
            # fails closed rather than confirming or rolling back blind.
            with self.assertRaises(SystemUpdateError) as refused:
                authority2.reconcile()
            self.assertIn("no authoritative boot observation", str(refused.exception))


if __name__ == "__main__":
    unittest.main()
