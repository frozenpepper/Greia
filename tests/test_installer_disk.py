from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(PROJECT_ROOT / "tools"))
from build_profile import _ALLOWED_TARGET_POLICIES  # noqa: E402

from greia_installer.disk import (  # noqa: E402
    BlockDevice,
    DeviceIdentity,
    DeviceObservation,
    DiskInventory,
    DiskProbeError,
    IdentityProvenance,
    LiveMediaAncestry,
    LiveMediaResolver,
    LsblkDiskProbe,
    PcInternalTargetPolicy,
    PiBuiltInMicroSdTargetPolicy,
    TargetSelection,
    default_install_target_policy,
    partition_one_path,
    policy_for_profile_id,
)
from greia_installer.engine import InstallationEngine, InstallationError  # noqa: E402


INTERNAL = {
    "name": "sda",
    "path": "/dev/sda",
    "size": 7_500_000_000,
    "type": "disk",
    "rm": 0,
    "ro": 0,
    "mountpoints": [None],
    "model": "Internal SSD",
    "serial": "ABC",
    "wwn": "WWN-ABC",
    "maj:min": "8:0",
    "tran": "ata",
    "children": [],
}


def _payload(*devices: dict) -> str:
    return json.dumps({"blockdevices": list(devices)})


class FakeRunner:
    def __init__(self, payload: str, failures: int = 0):
        self.payload = payload
        self.calls = 0
        self.failures = failures

    def run(self, command):
        self.calls += 1
        if self.calls <= self.failures:
            return subprocess.CompletedProcess(command, 1, "", "boom")
        return subprocess.CompletedProcess(command, 0, self.payload, "")


def probe_of(*devices: dict) -> DiskInventory:
    return LsblkDiskProbe(FakeRunner(_payload(*devices))).probe()


def obs(name="sda", path="/dev/sda", **overrides) -> DeviceObservation:
    base = {
        "name": name,
        "path": Path(path),
        "size_bytes": 7_500_000_000,
        "device_type": "disk",
        "model": "Internal SSD",
        "serial": "ABC",
        "transport": "ata",
        "removable": False,
        "read_only": False,
        "mountpoints": (),
        "wwn": "WWN-ABC",
        "major_minor": "8:0",
    }
    base.update(overrides)
    return DeviceObservation(**base)


def live_tree(
    root: Path,
    *,
    live_id: str | None = "4f6fc2a3-578e-4af1-bf48-8b6eab7c72d9",
    live_major_minor: str | None = "8:17",
    extra_mounts: tuple[str, ...] = (),
) -> LiveMediaResolver:
    """Build a fake live-identifier + mountinfo + sysfs tree in ``root``."""
    id_path = root / "live-media-id"
    if live_id is not None:
        id_path.write_text(live_id + "\n")
    lines = ["1 0 8:1 / / rw,relatime - ext4 /dev/sda1 rw"]
    if live_major_minor is not None:
        lines.append(
            f"24 1 {live_major_minor} / /run/live/medium ro,relatime "
            "- vfat /dev/sdb1 ro"
        )
    lines.extend(extra_mounts)
    mountinfo = root / "mountinfo"
    mountinfo.write_text("\n".join(lines) + "\n")
    dev_root = root / "dev-block"
    class_root = root / "class-block"
    dev_root.mkdir()
    class_root.mkdir()
    return LiveMediaResolver(
        live_media_id_path=id_path,
        mountinfo_path=mountinfo,
        sys_dev_block_root=dev_root,
        sys_class_block_root=class_root,
    )


def link_sysfs(
    resolver: LiveMediaResolver,
    root: Path,
    major_minor: str,
    block_name: str,
    whole_name: str | None,
) -> None:
    """Link a fake ``major:minor -> whole disk`` ancestry into the resolver."""
    real = root / "real"
    if whole_name is None or whole_name == block_name:
        target = real / block_name
        target.mkdir(parents=True, exist_ok=True)
        dev_link = resolver.sys_dev_block_root / major_minor
        if not dev_link.is_symlink() and not dev_link.exists():
            dev_link.symlink_to(target)
        class_link = resolver.sys_class_block_root / block_name
        if not class_link.is_symlink() and not class_link.exists():
            class_link.symlink_to(target)
    else:
        parent = real / whole_name
        child = parent / block_name
        child.mkdir(parents=True, exist_ok=True)
        (child / "partition").write_text("1\n")
        dev_link = resolver.sys_dev_block_root / major_minor
        if not dev_link.is_symlink() and not dev_link.exists():
            dev_link.symlink_to(child)
        class_link = resolver.sys_class_block_root / block_name
        if not class_link.is_symlink() and not class_link.exists():
            class_link.symlink_to(child)
        whole_link = resolver.sys_class_block_root / whole_name
        if not whole_link.is_symlink() and not whole_link.exists():
            whole_link.symlink_to(parent)


class TypedPolicyTests(unittest.TestCase):
    def test_policy_ids_match_declarative_profile_authority(self) -> None:
        self.assertEqual(
            {PcInternalTargetPolicy().policy_id,
             PiBuiltInMicroSdTargetPolicy().policy_id},
            set(_ALLOWED_TARGET_POLICIES),
        )
        self.assertIsInstance(
            policy_for_profile_id("pc-internal-v1"), PcInternalTargetPolicy
        )
        self.assertIsInstance(
            policy_for_profile_id("pi-builtin-microsd-v1"),
            PiBuiltInMicroSdTargetPolicy,
        )
        with self.assertRaises(DiskProbeError):
            policy_for_profile_id("yes-to-everything-v1")

    def test_pc_policy_rejects_external_removable_hotplug_mounted_small(self) -> None:
        policy = PcInternalTargetPolicy()
        cases = [
            obs(transport="usb"),
            obs(removable=True),
            obs(hotplug=True),
            obs(read_only=True),
            obs(size_bytes=2_000_000_000),
            obs(mountpoints=(Path("/mnt/x"),)),
            obs(transport="mmc", path="/dev/mmcblk0", name="mmcblk0"),
        ]
        for candidate in cases:
            with self.subTest(candidate=candidate):
                self.assertFalse(policy.evaluate(candidate).eligible)
        active = obs(
            children=(
                obs(
                    name="sda1",
                    path="/dev/sda1",
                    device_type="crypt",
                    mountpoints=(),
                    serial="",
                    wwn="",
                ),
            )
        )
        self.assertFalse(policy.evaluate(active).eligible)

    def test_pc_policy_never_rejects_builtin_emmc_for_its_prefix(self) -> None:
        policy = PcInternalTargetPolicy()
        card_reader = obs(
            name="mmcblk0", path="/dev/mmcblk0", transport="mmc",
            serial="SD", wwn="", major_minor="179:0",
        )
        self.assertFalse(policy.evaluate(card_reader).eligible)
        builtin = obs(
            name="mmcblk0", path="/dev/mmcblk0", transport="mmc",
            serial="EMMC", wwn="", major_minor="179:0",
            mmc_host_built_in=True,
        )
        decision = policy.evaluate(builtin)
        self.assertTrue(decision.eligible, decision.reason)

    def test_pi_policy_accepts_only_the_builtin_microsd_host(self) -> None:
        policy = PiBuiltInMicroSdTargetPolicy()
        builtin = obs(
            name="mmcblk0", path="/dev/mmcblk0", transport="mmc",
            serial="CARD", wwn="", major_minor="179:0",
            mmc_host_built_in=True,
        )
        self.assertTrue(policy.evaluate(builtin).eligible)
        self.assertFalse(policy.evaluate(obs()).eligible)
        usb = obs(name="sda", path="/dev/sda", transport="usb", major_minor="8:0")
        decision = policy.evaluate(usb)
        self.assertFalse(decision.eligible)
        self.assertIn("separate feature", decision.reason)
        unproven = obs(
            name="mmcblk0", path="/dev/mmcblk0", transport="mmc",
            serial="CARD", wwn="", major_minor="179:0",
        )
        self.assertFalse(policy.evaluate(unproven).eligible)

    def test_unknown_identity_fails_closed_everywhere(self) -> None:
        blank = obs(model="", serial="", wwn="", nguid="", eui="", mmc_cid="")
        for policy in (
            PcInternalTargetPolicy(),
            PiBuiltInMicroSdTargetPolicy(),
        ):
            decision = policy.evaluate(blank)
            self.assertFalse(decision.eligible)
            self.assertIn("fails closed", decision.reason)

    def test_legacy_ata_fallback_is_explicit_and_evidence_gated(self) -> None:
        legacy_shape = obs(model="Old ATA Disk", serial="", wwn="")
        identity = DeviceIdentity.from_observation(legacy_shape)
        self.assertEqual(identity.provenance, IdentityProvenance.UNKNOWN)
        for policy in (
            PcInternalTargetPolicy(),
            PiBuiltInMicroSdTargetPolicy(),
            default_install_target_policy(),
        ):
            self.assertFalse(policy.permit_legacy_ata_fallback)
            self.assertFalse(policy.evaluate(legacy_shape).eligible)
        permitted = PcInternalTargetPolicy(permit_legacy_ata_fallback=True)
        gated = DeviceIdentity.from_observation(
            legacy_shape, allow_legacy_ata_fallback=True
        )
        self.assertEqual(
            gated.provenance, IdentityProvenance.LEGACY_ATA_OBSERVATION_ONLY
        )
        decision = permitted.evaluate(legacy_shape)
        self.assertTrue(decision.eligible, decision.reason)
        self.assertIn("legacy ATA fallback", decision.reason)


class IdentityAuthorityTests(unittest.TestCase):
    def test_session_locators_never_participate_in_identity(self) -> None:
        first = obs()
        moved = obs(path="/dev/sdb", major_minor="8:16", sysfs_path="/sys/x")
        self.assertEqual(first.fingerprint, moved.fingerprint)
        self.assertEqual(first.identity_digest, moved.identity_digest)
        self.assertEqual(
            first.device_identity().identity_key,
            moved.device_identity().identity_key,
        )
        other = obs(serial="OTHER", wwn="WWN-OTHER")
        self.assertNotEqual(first.fingerprint, other.fingerprint)

    def test_probe_ignores_label_only_fields(self) -> None:
        plain = dict(INTERNAL)
        labelled = dict(INTERNAL)
        labelled["label"] = "GREIA_SETUP"
        labelled["partlabel"] = "GREIA_SETUP_DATA"
        first = probe_of(plain).devices[0]
        second = probe_of(labelled).devices[0]
        self.assertEqual(first.fingerprint, second.fingerprint)
        self.assertFalse(hasattr(first, "label"))
        policy = PcInternalTargetPolicy()
        self.assertEqual(
            probe_of(plain).install_targets(policy)[0].path,
            probe_of(labelled).install_targets(policy)[0].path,
        )

    def test_no_device_path_or_model_is_hardcoded_into_policy(self) -> None:
        for policy in (
            PcInternalTargetPolicy(),
            PiBuiltInMicroSdTargetPolicy(),
            default_install_target_policy(),
        ):
            self.assertNotIn("/dev/", policy.policy_id)
            decision = policy.evaluate(obs())
            self.assertNotIn("/dev/sda", decision.reason)
            self.assertNotIn("Acer", decision.reason)

    def test_stable_facts_include_wwn_serial_nguid_eui_and_cid(self) -> None:
        for key in ("wwn", "serial", "nguid", "eui", "mmc_cid"):
            overrides = {"serial": "", "wwn": "", key: "STABLE-1"}
            candidate = obs(**overrides)
            self.assertEqual(
                candidate.device_identity().provenance,
                IdentityProvenance.STRONG_STABLE,
                key,
            )
            self.assertTrue(PcInternalTargetPolicy().evaluate(candidate).eligible)


class RefreshSelectionTests(unittest.TestCase):
    def _inventories(self) -> tuple[DiskInventory, DiskInventory]:
        probe = LsblkDiskProbe(FakeRunner(_payload(dict(INTERNAL))))
        return probe.probe(), probe.probe()

    def test_refresh_mints_a_new_generation_and_selection_survives(self) -> None:
        policy = PcInternalTargetPolicy()
        first, second = self._inventories()
        self.assertNotEqual(first.generation, second.generation)
        selection = TargetSelection.from_observation(first.devices[0], policy)
        self.assertIsNotNone(selection.reselect(second, policy))

    def test_reselect_rejects_path_and_index_authority(self) -> None:
        policy = PcInternalTargetPolicy()
        first = probe_of(dict(INTERNAL))
        selection = TargetSelection.from_observation(first.devices[0], policy)
        moved = dict(INTERNAL)
        moved["path"] = "/dev/sdb"
        moved["maj:min"] = "8:16"
        reordered = probe_of(
            {
                "name": "sdz", "path": "/dev/sdz", "size": 9_000_000_000,
                "type": "disk", "rm": 0, "ro": 0, "mountpoints": [None],
                "model": "Decoy", "serial": "DECOY", "wwn": "WWN-DECOY",
                "maj:min": "8:240", "tran": "ata", "children": [],
            },
            moved,
        )
        survived = selection.reselect(reordered, policy)
        self.assertIsNotNone(survived)
        self.assertEqual(survived.path, Path("/dev/sdb"))
        self.assertNotEqual(survived.path, Path("/dev/sda"))

    def test_reselect_clears_on_identity_or_eligibility_change(self) -> None:
        policy = PcInternalTargetPolicy()
        first = probe_of(dict(INTERNAL))
        selection = TargetSelection.from_observation(first.devices[0], policy)
        mutations = []
        swapped = dict(INTERNAL)
        swapped["serial"] = "EVIL"
        swapped["wwn"] = "WWN-EVIL"
        mutations.append(swapped)
        for key, value in (
            ("size", 7_500_000_001),
            ("ro", 1),
            ("rm", 1),
        ):
            mutated = dict(INTERNAL)
            mutated[key] = value
            mutations.append(mutated)
        mounted = dict(INTERNAL)
        mounted["mountpoints"] = ["/mnt/now"]
        mutations.append(mounted)
        for mutated in mutations:
            with self.subTest(mutated=mutated):
                refreshed = probe_of(mutated)
                self.assertIsNone(selection.reselect(refreshed, policy))
        # A different policy id never inherits the selection.
        self.assertIsNone(
            selection.reselect(first, PiBuiltInMicroSdTargetPolicy())
        )

    def test_probe_generation_increments_per_refresh(self) -> None:
        probe = LsblkDiskProbe(FakeRunner(_payload(dict(INTERNAL))))
        self.assertEqual(probe.probe().generation, 1)
        self.assertEqual(probe.probe().generation, 2)


class LiveAncestryTests(unittest.TestCase):
    def test_setup_whole_disk_and_descendants_are_excluded(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            resolver = live_tree(root)
            link_sysfs(resolver, root, "8:16", "sdb", "sdb")
            link_sysfs(resolver, root, "8:17", "sdb1", "sdb")
            link_sysfs(resolver, root, "8:0", "sda", "sda")
            live = {
                "name": "sdb", "path": "/dev/sdb", "size": 16_000_000_000,
                "type": "disk", "rm": 1, "ro": 0, "mountpoints": [None],
                "model": "Setup USB", "serial": "SETUP", "wwn": "WWN-SETUP",
                "maj:min": "8:16", "tran": "usb",
                "children": [
                    {
                        "name": "sdb1", "path": "/dev/sdb1",
                        "size": 15_900_000_000, "type": "part",
                        "rm": 0, "ro": 0, "mountpoints": ["/run/live/medium"],
                        "maj:min": "8:17",
                    }
                ],
            }
            inventory = probe_of(dict(INTERNAL), live)
            ancestry = resolver.resolve(inventory)
            self.assertFalse(ancestry.ambiguous, ancestry.reason)
            self.assertEqual(set(ancestry.whole_disk_names), {"sdb"})
            targets = inventory.install_targets(
                PcInternalTargetPolicy(), excluded=ancestry
            )
            self.assertEqual([t.path for t in targets], [Path("/dev/sda")])

    def test_ambiguous_ancestry_offers_zero_targets(self) -> None:
        policy = PcInternalTargetPolicy()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            # Corrupt identifier with an otherwise resolving live mount.
            resolver = live_tree(root, live_id="not-a-uuid")
            link_sysfs(resolver, root, "8:17", "sdb1", "sdb")
            inventory = probe_of(dict(INTERNAL))
            ancestry = resolver.resolve(inventory)
            self.assertTrue(ancestry.ambiguous)
            self.assertEqual(inventory.install_targets(policy, excluded=ancestry), ())
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            # Identifier present but the live mount source is missing.
            resolver = live_tree(root, live_major_minor=None)
            inventory = probe_of(dict(INTERNAL))
            self.assertTrue(resolver.resolve(inventory).ambiguous)
            self.assertEqual(
                inventory.install_targets(
                    policy, excluded=resolver.resolve(inventory)
                ),
                (),
            )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            # Two distinct live sources disagree.
            resolver = live_tree(
                root,
                extra_mounts=(
                    "25 1 8:33 / /run/live/medium ro,relatime - vfat /dev/sdc1 ro",
                ),
            )
            link_sysfs(resolver, root, "8:17", "sdb1", "sdb")
            link_sysfs(resolver, root, "8:33", "sdc1", "sdc")
            inventory = probe_of(dict(INTERNAL))
            self.assertTrue(resolver.resolve(inventory).ambiguous)
            self.assertEqual(
                inventory.install_targets(
                    policy, excluded=resolver.resolve(inventory)
                ),
                (),
            )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            # Ancestor outside the inventory (device-mapper style node).
            resolver = live_tree(root)
            link_sysfs(resolver, root, "8:17", "dm-0", "dm-0")
            inventory = probe_of(dict(INTERNAL))
            ancestry = resolver.resolve(inventory)
            self.assertTrue(ancestry.ambiguous, ancestry.reason)
            self.assertEqual(inventory.install_targets(policy, excluded=ancestry), ())

    def test_non_live_context_excludes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            resolver = live_tree(root, live_id=None, live_major_minor=None)
            ancestry = resolver.resolve(probe_of(dict(INTERNAL)))
            self.assertFalse(ancestry.ambiguous, ancestry.reason)
            self.assertFalse(ancestry.is_live_context)
            targets = probe_of(dict(INTERNAL)).install_targets(
                PcInternalTargetPolicy(), excluded=ancestry
            )
            self.assertEqual([t.path for t in targets], [Path("/dev/sda")])

    def test_whole_disk_ancestor_uses_structure_not_name_guessing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            resolver = live_tree(root)
            link_sysfs(resolver, root, "179:1", "mmcblk0p1", "mmcblk0")
            link_sysfs(resolver, root, "259:1", "nvme0n1p1", "nvme0n1")
            self.assertEqual(resolver.whole_disk_ancestor("179:1"), "mmcblk0")
            self.assertEqual(resolver.whole_disk_ancestor("259:1"), "nvme0n1")
            self.assertIsNone(resolver.whole_disk_ancestor("8:99"))
            self.assertIsNone(resolver.whole_disk_ancestor("bogus"))


class InstallerDiskLegacyTests(unittest.TestCase):
    def test_only_unmounted_non_usb_internal_disk_is_offered(self) -> None:
        inventory = probe_of(
            dict(INTERNAL),
            {
                "name": "sdb", "path": "/dev/sdb", "size": 12_000_000_000,
                "type": "disk", "rm": 0, "ro": 0,
                "mountpoints": [None], "model": "Mounted data disk",
                "serial": "MOUNTED", "wwn": "", "maj:min": "8:16",
                "tran": "ata",
                "children": [
                    {
                        "name": "sdb1", "path": "/dev/sdb1",
                        "size": 11_900_000_000, "type": "part",
                        "rm": 0, "ro": 0,
                        "mountpoints": ["/mnt/family-photos"],
                        "maj:min": "8:17",
                    }
                ],
            },
            {
                "name": "sdc", "path": "/dev/sdc", "size": 16_000_000_000,
                "type": "disk", "rm": 0, "ro": 0, "mountpoints": [None],
                "model": "External USB SSD", "serial": "USB", "wwn": "",
                "maj:min": "8:32", "tran": "usb",
            },
            {
                "name": "mmcblk0", "path": "/dev/mmcblk0",
                "size": 32_000_000_000, "type": "disk", "rm": 0,
                "hotplug": 0, "ro": 0, "mountpoints": [None],
                "model": "Inserted SD card", "serial": "SDCARD", "wwn": "",
                "maj:min": "179:0", "tran": "mmc",
            },
            {
                "name": "sde", "path": "/dev/sde", "size": 2_000_000_000,
                "type": "disk", "rm": 0, "hotplug": 0, "ro": 0,
                "mountpoints": [None], "model": "Too small", "serial": "SMALL",
                "wwn": "", "maj:min": "8:64", "tran": "ata",
            },
        )
        targets = inventory.install_targets(
            PcInternalTargetPolicy(), excluded=LiveMediaAncestry.empty()
        )
        self.assertEqual([target.path for target in targets], [Path("/dev/sda")])
        self.assertEqual(targets[0].major_minor, "8:0")
        self.assertEqual(len(targets[0].identity_digest), 64)

    def test_active_crypt_lvm_or_raid_descendants_are_never_offered(self) -> None:
        inventory = probe_of(
            dict(INTERNAL),
            {
                "name": "sdf", "path": "/dev/sdf", "size": 12_000_000_000,
                "type": "disk", "rm": 0, "hotplug": 0, "ro": 0,
                "mountpoints": [None], "model": "Active encrypted volume",
                "serial": "ACTIVE", "wwn": "", "maj:min": "8:80",
                "tran": "ata",
                "children": [
                    {
                        "name": "sdf1", "path": "/dev/sdf1",
                        "size": 11_900_000_000, "type": "part",
                        "rm": 0, "ro": 0, "mountpoints": [None],
                        "children": [
                            {
                                "name": "crypt-family",
                                "path": "/dev/mapper/crypt-family",
                                "size": 11_800_000_000, "type": "crypt",
                                "rm": 0, "ro": 0, "mountpoints": [None],
                            }
                        ],
                    }
                ],
            },
        )
        active = inventory.by_path(Path("/dev/sdf"))
        self.assertIsNotNone(active)
        self.assertTrue(active.has_active_storage_stack())
        self.assertNotIn(
            Path("/dev/sdf"),
            [
                target.path
                for target in inventory.install_targets(PcInternalTargetPolicy())
            ],
        )

    def test_partition_path_handles_classic_and_mmc_names(self) -> None:
        self.assertEqual(partition_one_path(Path("/dev/sda")), Path("/dev/sda1"))
        self.assertEqual(
            partition_one_path(Path("/dev/mmcblk0")), Path("/dev/mmcblk0p1")
        )
        self.assertEqual(
            partition_one_path(Path("/dev/nvme0n1")), Path("/dev/nvme0n1p1")
        )

    def test_block_device_alias_stays_constructible(self) -> None:
        device = BlockDevice(
            name="sda",
            path=Path("/dev/sda"),
            size_bytes=7_500_000_000,
            device_type="disk",
            model="Internal SSD",
            serial="ABC",
            transport="ata",
            removable=False,
            read_only=False,
            mountpoints=(),
            wwn="WWN-ABC",
            major_minor="8:0",
        )
        self.assertIsInstance(device, DeviceObservation)
        self.assertTrue(PcInternalTargetPolicy().evaluate(device).eligible)


class FakeProbe:
    def __init__(self, devices: list[DeviceObservation]):
        self.devices = devices
        self.calls = 0

    def probe(self) -> DiskInventory:
        self.calls += 1
        return DiskInventory(tuple(self.devices), generation=self.calls)


def non_live_resolver(root: Path) -> LiveMediaResolver:
    mountinfo = root / "mountinfo"
    mountinfo.write_text("1 0 8:1 / / rw,relatime - ext4 /dev/sda1 rw\n")
    return LiveMediaResolver(
        live_media_id_path=root / "missing-live-media-id",
        mountinfo_path=mountinfo,
        sys_dev_block_root=root / "dev-block",
        sys_class_block_root=root / "class-block",
    )


class EngineIdentityVerificationTests(unittest.TestCase):
    def test_verify_uses_identity_then_policy_then_ancestry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "dev-block").mkdir()
            (root / "class-block").mkdir()
            engine = InstallationEngine(
                project_root=PROJECT_ROOT,
                probe=FakeProbe([obs()]),
                live_resolver=non_live_resolver(root),
            )
            engine._verify_target(obs())
            # Identity, ancestry and policy all read one inventory generation.
            self.assertEqual(engine.probe.calls, 1)

    def test_verify_fails_closed_on_changed_identity_or_moved_locator(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "dev-block").mkdir()
            (root / "class-block").mkdir()
            engine = InstallationEngine(
                project_root=PROJECT_ROOT,
                probe=FakeProbe([obs(serial="OTHER", wwn="WWN-OTHER")]),
                live_resolver=non_live_resolver(root),
            )
            with self.assertRaisesRegex(InstallationError, "disappeared"):
                engine._verify_target(obs())
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "dev-block").mkdir()
            (root / "class-block").mkdir()
            moved = obs(path="/dev/sdb", major_minor="8:16")
            engine = InstallationEngine(
                project_root=PROJECT_ROOT,
                probe=FakeProbe([moved]),
                live_resolver=non_live_resolver(root),
            )
            with self.assertRaisesRegex(InstallationError, "identity changed"):
                engine._verify_target(obs())

    def test_verify_rejects_ambiguous_ancestry_and_live_targets(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bad_id = root / "live-media-id"
            bad_id.write_text("not-a-uuid\n")
            mountinfo = root / "mountinfo"
            mountinfo.write_text(
                "24 1 8:17 / /run/live/medium ro - vfat /dev/sdb1 ro\n"
            )
            ambiguous = LiveMediaResolver(
                live_media_id_path=bad_id,
                mountinfo_path=mountinfo,
                sys_dev_block_root=root / "dev-block",
                sys_class_block_root=root / "class-block",
            )
            engine = InstallationEngine(
                project_root=PROJECT_ROOT,
                probe=FakeProbe([obs()]),
                live_resolver=ambiguous,
            )
            with self.assertRaisesRegex(InstallationError, "ambiguous"):
                engine._verify_target(obs())


if __name__ == "__main__":
    unittest.main()
