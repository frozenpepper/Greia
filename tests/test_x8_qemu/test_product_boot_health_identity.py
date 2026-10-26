"""P5.3 boot-health identity fold: observed leg facts bound for Gate-P5.

Focused tests for ``tools/x8_qemu/product.py`` without QEMU/loop/mount
contact:

- GREEN: ``run_boot_health_product()`` builds and asserts a complete P5.3
  identity record containing the boot facts (installed-image SHA-256,
  signed-bundle SHA-256, shipped boot-unit SHAs via the pinned
  ``PRODUCT_IDENTITY_UNITS``, per-slot pre/post clone SHAs + exact
  injected-file lists via ``record_slot_injection_mutation``,
  slot-isolation digests via ``verify_update_slot_isolation``, and the
  observed MBR/PARTUUID/filesystem/journal/release/layout facts from
  ``gather_boot_health_observation``).
- RED (never a partial green): a missing slot-injection provenance, a
  missing slot-isolation digest/proof, or a missing observed boot fact
  raises; a mutated source image raises; an ambiguous image leg refuses.
- Registered baseline: the unit/module key sets stay pinned; tamper is
  RED (synthetic-violation positive control).
- Fail-closed host gate: the real entry point without fakes stays
  ``BLOCKED`` naming the facility on this host.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock as _mock

from tools.x8_qemu import product as _product
from tools.x8_qemu.lifecycle import LifecycleConfig, LifecycleHarnessError
from tools.x8_qemu.product import (
    PRODUCT_IDENTITY_MODULES,
    PRODUCT_IDENTITY_UNITS,
    ProductHarness,
    assert_product_identity_complete,
    build_product_identity_record,
    record_slot_injection_mutation,
    sha256_file,
)


def _write_installed(base: Path, name: str = "installed.img") -> Path:
    path = base / name
    path.write_bytes(b"installed-system-a-image" * 64)
    return path


def _write_bundle(base: Path, name: str = "greia-0.21.0.greiaupdate") -> Path:
    path = base / name
    path.write_bytes(b"signed-release-bundle" * 64)
    return path


def _slot_mutation(pre: str = "aa" * 32, post: str = "bb" * 32) -> dict[str, object]:
    return record_slot_injection_mutation(
        pre_sha256=pre,
        post_sha256=post,
        injected_files=[
            "etc/systemd/system/greia-x8-control.service",
            "usr/local/sbin/greia-x8-control",
            "etc/systemd/system/multi-user.target.wants/greia-x8-control.service",
        ],
    )


def _green_digests() -> dict[str, object]:
    return {
        "active_before": "aa" * 32,
        "active_after": "aa" * 32,
        "inactive_before": "bb" * 32,
        "inactive_after": "cc" * 32,
    }


def _green_isolation() -> dict[str, object]:
    return {
        "active_slot": "A",
        "active_unchanged": None,
        "inactive_changed": None,
        "scope": "raw_hashes_observational_across_boots",
        "booted_slots": ["A", "B"],
    }


def _green_observation() -> dict[str, object]:
    return {
        "disk_identities": {
            "disk_signature": "1a2b3c4d",
            "system_a_partuuid": "1a2b3c4d-02",
            "system_b_partuuid": "1a2b3c4d-03",
            "persist_partuuid": "1a2b3c4d-04",
        },
        "observed_identities": {
            "system-a": {
                "partuuid": "1a2b3c4d-02",
                "filesystem_uuid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            },
            "system-b": {
                "partuuid": "1a2b3c4d-03",
                "filesystem_uuid": "bbbbbbbb-cccc-dddd-eeee-ffffffffffff",
            },
            "persist": {
                "partuuid": "1a2b3c4d-04",
                "filesystem_uuid": "cccccccc-dddd-eeee-ffff-000000000000",
            },
        },
        "default_slot": "B",
        "accepted_release_id": "greia-0.21.0",
        "committed_slot": "B",
        "last_booted": "B",
        "journal_state": "accepted",
    }


def _green_record(base: Path) -> tuple[dict[str, object], Path, Path]:
    installed = _write_installed(base)
    bundle = _write_bundle(base)
    record = build_product_identity_record(
        installed_image=installed,
        release_bundles=[bundle],
        slot_a_mutation=_slot_mutation("aa" * 32, "bb" * 32),
        slot_b_mutation=_slot_mutation("cc" * 32, "dd" * 32),
        slot_digests=_green_digests(),
        slot_isolation=_green_isolation(),
        boot_observation=_green_observation(),
    )
    return record, installed, bundle


def _scripted_digest_fn(values: list[str]):
    remaining = list(values)

    def _fn(clone, slot):
        return remaining.pop(0)

    return _fn


class BootIdentityGreenTests(unittest.TestCase):
    def test_complete_boot_record_binds_exact_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            record, installed, bundle = _green_record(base)
            self.assertEqual(
                set(record["units"]["entries"]), set(PRODUCT_IDENTITY_UNITS)  # type: ignore[index]
            )
            self.assertEqual(
                set(record["modules"]["entries"]), set(PRODUCT_IDENTITY_MODULES)  # type: ignore[index]
            )
            self.assertEqual(
                record["installed_image"]["sha256"], sha256_file(installed)  # type: ignore[index]
            )
            self.assertEqual(
                record["release_bundles"][bundle.name]["sha256"],  # type: ignore[index]
                sha256_file(bundle),
            )
            self.assertEqual(
                record["slot_a_mutation"]["pre_sha256"], "aa" * 32  # type: ignore[index]
            )
            self.assertEqual(
                record["slot_b_mutation"]["pre_sha256"], "cc" * 32  # type: ignore[index]
            )
            self.assertEqual(
                record["slot_digests"]["active_before"], "aa" * 32  # type: ignore[index]
            )
            self.assertIsNone(record["slot_isolation"]["active_unchanged"])  # type: ignore[index]
            self.assertIsNone(record["slot_isolation"]["inactive_changed"])  # type: ignore[index]
            self.assertEqual(
                record["boot_observation"]["default_slot"], "B"  # type: ignore[index]
            )
            self.assertEqual(
                record["boot_observation"]["accepted_release_id"], "greia-0.21.0"  # type: ignore[index]
            )
            self.assertFalse(record["source_image_mutated"])
            assert_product_identity_complete(
                record, installed_image=installed, release_bundles=[bundle]
            )

    def test_recorded_hashes_are_read_from_real_bytes(self) -> None:
        import hashlib as _hashlib

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            record, installed, bundle = _green_record(base)
            self.assertEqual(
                record["installed_image"]["sha256"],  # type: ignore[index]
                _hashlib.sha256(installed.read_bytes()).hexdigest(),
            )
            self.assertEqual(
                record["release_bundles"][bundle.name]["sha256"],  # type: ignore[index]
                _hashlib.sha256(bundle.read_bytes()).hexdigest(),
            )
            from tools.x8_qemu.lifecycle import PROJECT_ROOT

            unit_path = (
                PROJECT_ROOT
                / "build/overlay/etc/systemd/system/greia-boot-health.service"
            )
            self.assertEqual(
                record["units"]["entries"][  # type: ignore[index]
                    "build/overlay/etc/systemd/system/greia-boot-health.service"
                ]["sha256"],
                _hashlib.sha256(unit_path.read_bytes()).hexdigest(),
            )

    def test_run_boot_health_product_carries_bound_identity(self) -> None:
        # Production-proof through the real entry point: the identity is
        # built inside run_boot_health_product from the booted installed
        # image, the staged bundle, both slot-injection provenances, the
        # slot-isolation digests and the observed boot facts, then
        # re-asserted GREEN against those same artifacts.
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            installed = _write_installed(base)
            bundle = _write_bundle(base)
            gate = _mock.patch.object(
                _product, "require_product_host", lambda **kwargs: None
            )
            qemu = _mock.patch.object(
                _product,
                "select_install_qemu_binary",
                lambda **kwargs: "qemu-system-i386",
            )
            with gate, qemu:
                harness = ProductHarness(
                    LifecycleConfig(output_dir=base / "out"),
                    official_image=installed,
                    release_bundle=bundle,
                )
                result = harness.run_boot_health_product(
                    clone_fn=lambda s, d: {
                        "source_sha256": sha256_file(Path(s)),
                        "clone": str(d),
                    },
                    inject_fn=lambda c, s: {
                        "clone": str(c),
                        "slot": s,
                        "injected_files": [
                            "etc/systemd/system/greia-x8-control.service",
                        ],
                        "pre_sha256": "aa" * 32,
                        "post_sha256": "bb" * 32,
                        "source_image_mutated": False,
                    },
                    materialize_fn=lambda d, i: None,
                    boot_fn=lambda phase, *a: None,
                    candidate_inject_fn=lambda *_: {"fake": "candidate-receipt"},
                    observe_fn=lambda t: dict(_green_observation()),
                    slot_digest_fn=_scripted_digest_fn(
                        ["bb" * 32, "aa" * 32, "aa" * 32, "cc" * 32]
                    ),
                )
            identity = result["unit_identity"]
            self.assertEqual(
                identity["installed_image"]["sha256"],
                result["installed_image_sha256"],
            )
            self.assertEqual(
                identity["release_bundles"][bundle.name]["sha256"],
                result["release_bundle_sha256"],
            )
            self.assertEqual(identity["boot_observation"]["default_slot"], "B")
            self.assertEqual(identity["boot_observation"]["accepted_release_id"], "greia-0.21.0")
            self.assertFalse(result["source_image_mutated"])
            self.assertFalse(identity["source_image_mutated"])
            self.assertEqual(
                result["candidate_inject"], {"fake": "candidate-receipt"}
            )
            assert_product_identity_complete(
                identity, installed_image=installed, release_bundles=[bundle]
            )

    def test_flat_mutated_source_stays_red_not_dropped(self) -> None:
        # Hardening: a flat inject_fn proof carrying
        # source_image_mutated=True must refuse RED through the entry
        # point instead of being silently dropped to False.
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            installed = _write_installed(base)
            bundle = _write_bundle(base)
            gate = _mock.patch.object(
                _product, "require_product_host", lambda **kwargs: None
            )
            qemu = _mock.patch.object(
                _product,
                "select_install_qemu_binary",
                lambda **kwargs: "qemu-system-i386",
            )
            with gate, qemu:
                harness = ProductHarness(
                    LifecycleConfig(output_dir=base / "out"),
                    official_image=installed,
                    release_bundle=bundle,
                )
                with self.assertRaises(LifecycleHarnessError):
                    harness.run_boot_health_product(
                        clone_fn=lambda s, d: {
                            "source_sha256": sha256_file(Path(s)),
                            "clone": str(d),
                        },
                        inject_fn=lambda c, s: {
                            "clone": str(c),
                            "slot": s,
                            "injected_files": ["x"],
                            "pre_sha256": "aa" * 32,
                            "post_sha256": "bb" * 32,
                            "source_image_mutated": True,
                        },
                        materialize_fn=lambda d, i: None,
                        boot_fn=lambda phase, *a: None,
                        candidate_inject_fn=lambda *_: {"fake": "candidate-receipt"},
                        observe_fn=lambda t: dict(_green_observation()),
                        slot_digest_fn=_scripted_digest_fn(
                            ["bb" * 32, "aa" * 32, "aa" * 32, "cc" * 32]
                        ),
                    )


class BootIdentityNegativeTests(unittest.TestCase):
    def test_missing_slot_a_provenance_is_red(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            installed = _write_installed(base)
            bundle = _write_bundle(base)
            with self.assertRaises(LifecycleHarnessError) as caught:
                build_product_identity_record(
                    installed_image=installed,
                    release_bundles=[bundle],
                    slot_a_mutation=None,
                    slot_b_mutation=_slot_mutation(),
                    slot_digests=_green_digests(),
                    slot_isolation=_green_isolation(),
                    boot_observation=_green_observation(),
                )
            self.assertIn("slot-A", str(caught.exception))

    def test_missing_slot_b_field_is_red(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            installed = _write_installed(base)
            bundle = _write_bundle(base)
            partial = {"pre_sha256": "cc" * 32, "injected_files": ["x"]}
            with self.assertRaises(LifecycleHarnessError) as caught:
                build_product_identity_record(
                    installed_image=installed,
                    release_bundles=[bundle],
                    slot_a_mutation=_slot_mutation(),
                    slot_b_mutation=partial,
                    slot_digests=_green_digests(),
                    slot_isolation=_green_isolation(),
                    boot_observation=_green_observation(),
                )
            self.assertIn("post_sha256", str(caught.exception))

    def test_missing_slot_digest_is_red(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            installed = _write_installed(base)
            bundle = _write_bundle(base)
            digests = dict(_green_digests())
            del digests["inactive_after"]
            with self.assertRaises(LifecycleHarnessError) as caught:
                build_product_identity_record(
                    installed_image=installed,
                    release_bundles=[bundle],
                    slot_a_mutation=_slot_mutation(),
                    slot_b_mutation=_slot_mutation(),
                    slot_digests=digests,
                    slot_isolation=_green_isolation(),
                    boot_observation=_green_observation(),
                )
            self.assertIn("inactive_after", str(caught.exception))

    def test_missing_isolation_proof_is_red(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            installed = _write_installed(base)
            bundle = _write_bundle(base)
            with self.assertRaises(LifecycleHarnessError):
                build_product_identity_record(
                    installed_image=installed,
                    release_bundles=[bundle],
                    slot_a_mutation=_slot_mutation(),
                    slot_b_mutation=_slot_mutation(),
                    slot_digests=_green_digests(),
                    slot_isolation=None,
                    boot_observation=_green_observation(),
                )

    def test_missing_hash_scope_is_red(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            installed = _write_installed(base)
            bundle = _write_bundle(base)
            proof = _green_isolation()
            del proof["scope"]
            with self.assertRaisesRegex(LifecycleHarnessError, "scope"):
                build_product_identity_record(
                    installed_image=installed,
                    release_bundles=[bundle],
                    slot_a_mutation=_slot_mutation(),
                    slot_b_mutation=_slot_mutation(),
                    slot_digests=_green_digests(),
                    slot_isolation=proof,
                    boot_observation=_green_observation(),
                )

    def test_observational_hash_scope_requires_known_ab_boot_roles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            installed = _write_installed(base)
            bundle = _write_bundle(base)
            digests = _green_digests()
            digests["active_after"] = "dd" * 32
            digests["inactive_after"] = digests["inactive_before"]
            proof = {
                "active_slot": "A",
                "active_unchanged": None,
                "inactive_changed": None,
                "scope": "raw_hashes_observational_across_boots",
                "booted_slots": ["A", "B"],
            }
            record = build_product_identity_record(
                installed_image=installed,
                release_bundles=[bundle],
                slot_a_mutation=_slot_mutation(),
                slot_b_mutation=_slot_mutation(),
                slot_digests=digests,
                slot_isolation=proof,
                boot_observation=_green_observation(),
            )
            self.assertIsNone(record["slot_isolation"]["active_unchanged"])

            for forged in (
                {**proof, "active_slot": "B"},
                {**proof, "booted_slots": ["A"]},
                {**proof, "active_unchanged": True},
            ):
                with self.subTest(forged=forged), self.assertRaises(LifecycleHarnessError):
                    build_product_identity_record(
                        installed_image=installed,
                        release_bundles=[bundle],
                        slot_a_mutation=_slot_mutation(),
                        slot_b_mutation=_slot_mutation(),
                        slot_digests=digests,
                        slot_isolation=forged,
                        boot_observation=_green_observation(),
                    )

    def test_missing_observed_disk_identities_is_red(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            installed = _write_installed(base)
            bundle = _write_bundle(base)
            observed = dict(_green_observation())
            del observed["disk_identities"]
            with self.assertRaises(LifecycleHarnessError) as caught:
                build_product_identity_record(
                    installed_image=installed,
                    release_bundles=[bundle],
                    slot_a_mutation=_slot_mutation(),
                    slot_b_mutation=_slot_mutation(),
                    slot_digests=_green_digests(),
                    slot_isolation=_green_isolation(),
                    boot_observation=observed,
                )
            self.assertIn("disk_identities", str(caught.exception))

    def test_missing_observed_default_is_red(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            installed = _write_installed(base)
            bundle = _write_bundle(base)
            observed = dict(_green_observation())
            del observed["default_slot"]
            with self.assertRaises(LifecycleHarnessError) as caught:
                build_product_identity_record(
                    installed_image=installed,
                    release_bundles=[bundle],
                    slot_a_mutation=_slot_mutation(),
                    slot_b_mutation=_slot_mutation(),
                    slot_digests=_green_digests(),
                    slot_isolation=_green_isolation(),
                    boot_observation=observed,
                )
            self.assertIn("default_slot", str(caught.exception))

    def test_missing_journal_state_is_red(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            installed = _write_installed(base)
            bundle = _write_bundle(base)
            observed = dict(_green_observation())
            del observed["journal_state"]
            with self.assertRaises(LifecycleHarnessError) as caught:
                build_product_identity_record(
                    installed_image=installed,
                    release_bundles=[bundle],
                    slot_a_mutation=_slot_mutation(),
                    slot_b_mutation=_slot_mutation(),
                    slot_digests=_green_digests(),
                    slot_isolation=_green_isolation(),
                    boot_observation=observed,
                )
            self.assertIn("journal_state", str(caught.exception))

    def test_mutated_source_image_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            installed = _write_installed(base)
            bundle = _write_bundle(base)
            with self.assertRaises(LifecycleHarnessError):
                build_product_identity_record(
                    installed_image=installed,
                    release_bundles=[bundle],
                    slot_a_mutation={
                        "pre_sha256": "aa" * 32,
                        "post_sha256": "bb" * 32,
                        "injected_files": ["x"],
                        "source_image_mutated": True,
                    },
                    slot_b_mutation=_slot_mutation(),
                    slot_digests=_green_digests(),
                    slot_isolation=_green_isolation(),
                    boot_observation=_green_observation(),
                )

    def test_ambiguous_image_leg_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            installed = _write_installed(base)
            bundle = _write_bundle(base)
            with self.assertRaises(LifecycleHarnessError):
                build_product_identity_record(
                    installer_image=installed,
                    installed_image=installed,
                    release_bundles=[bundle],
                )

    def test_wrong_installed_image_binding_is_red(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            record, _installed, bundle = _green_record(base)
            other = _write_installed(base, "other.img")
            other.write_bytes(b"different-installed-bytes" * 64)
            with self.assertRaises(LifecycleHarnessError) as caught:
                assert_product_identity_complete(
                    record, installed_image=other, release_bundles=[bundle]
                )
            self.assertIn("booted image", str(caught.exception))

    def test_tampered_boot_unit_sha_is_red_positive_control(self) -> None:
        # Synthetic-violation control: flip one recorded boot-unit SHA;
        # the gate must go RED, proving it detects what it claims.
        import copy as _copy

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            record, installed, bundle = _green_record(base)
            drifted = _copy.deepcopy(record)
            name = "build/overlay/etc/systemd/system/greia-boot-health.service"
            entry = dict(drifted["units"]["entries"][name])
            tampered = ("0" if entry["sha256"][0] != "0" else "1") + entry["sha256"][1:]
            entry["sha256"] = tampered
            drifted["units"]["entries"][name] = entry
            with self.assertRaises(LifecycleHarnessError) as caught:
                assert_product_identity_complete(
                    drifted, installed_image=installed, release_bundles=[bundle]
                )
            self.assertIn(name, str(caught.exception))
            # Restore the exact intended state -> GREEN again.
            drifted["units"]["entries"][name] = dict(
                record["units"]["entries"][name]  # type: ignore[index]
            )
            assert_product_identity_complete(
                drifted, installed_image=installed, release_bundles=[bundle]
            )

    def test_missing_observation_break_restore_positive_control(self) -> None:
        # Break the observed boot fact -> RED; restore -> GREEN.
        import copy as _copy

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            record, installed, bundle = _green_record(base)
            drifted = _copy.deepcopy(record)
            boot_obs = dict(drifted["boot_observation"])  # type: ignore[arg-type]
            del boot_obs["accepted_release_id"]
            drifted["boot_observation"] = boot_obs
            with self.assertRaises(LifecycleHarnessError) as caught:
                assert_product_identity_complete(
                    drifted, installed_image=installed, release_bundles=[bundle]
                )
            self.assertIn("accepted_release_id", str(caught.exception))
            drifted["boot_observation"] = dict(record["boot_observation"])  # type: ignore[arg-type]
            assert_product_identity_complete(
                drifted, installed_image=installed, release_bundles=[bundle]
            )


class BootHostGateTests(unittest.TestCase):
    def test_real_entry_blocked_names_facility(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            harness = ProductHarness(LifecycleConfig(output_dir=Path(tmp) / "out"))
            with self.assertRaises(LifecycleHarnessError) as caught:
                harness.run_boot_health_product()
            self.assertIn("BLOCKED", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
