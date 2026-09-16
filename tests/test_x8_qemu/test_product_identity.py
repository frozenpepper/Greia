"""P5.3 product-unit identity record including squashfs mutation provenance.

Focused tests for ``tools/x8_qemu/product.py`` without QEMU/loop/mount
contact:

- GREEN: a complete record for the proven composition (P5.3 units +
  service modules + built installer image + every staged ``.greiaupdate``
  + clone-only squashfs provenance) binds the exact run: image/bundle
  SHAs equal the booted/staged files, module SHAs equal the ``src/``
  tree at evidence time, and the record rides in the ``run_product``
  evidence JSON for Gate-P5 closure.
- RED (never a partial green): a missing/unreadable identity is
  ``BLOCKED`` (never fabricated); a missing provenance field, an empty
  bundle set or a mutated source image raises.
- Registered baseline: the unit/module key sets are pinned stable
  identities. An unexplained disappearance, an unregistered extra entry
  or a tampered SHA is RED — including a synthetic-violation positive
  control proving the gate detects what it claims to detect.
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
    UNIT_IDENTITY_SCHEMA_VERSION,
    ProductHarness,
    assert_product_identity_complete,
    build_product_identity_record,
    record_file_identity,
    record_live_squashfs_mutation,
    sha256_file,
)

EXPECTED_INJECTED_FILES = [
    "etc/systemd/system/greia-x8-control.service",
    "usr/local/sbin/greia-x8-control",
    "etc/systemd/system/multi-user.target.wants/greia-x8-control.service",
    "etc/systemd/system/greia-installer.service -> /dev/null (masked in clone only)",
]


def _write_image(base: Path, name: str = "installer.img") -> Path:
    path = base / name
    path.write_bytes(b"official-installer-image" * 64)
    return path


def _write_bundle(base: Path, name: str = "greia-release.greiaupdate") -> Path:
    import zstandard

    from greia_platform.system_updates import build_update_bundle

    raw = bytes((index * 31 + 7) % 256 for index in range(64 * 1024))
    payload = base / "payload.ext4.zst"
    payload.write_bytes(zstandard.ZstdCompressor(level=3).compress(raw))
    path = base / name
    build_update_bundle(
        payload_path=payload,
        hardware_support_path=None,
        output_path=path,
        version="0.20.0",
        release_id="greia-0.20.0",
        platform_family="legacy-x86",
        architecture="i386",
        profile="acer-aspire-one-i386-ab",
        payload_uncompressed_bytes=len(raw),
        persist_read_schema_min=1,
        persist_read_schema_max=1,
        persist_write_schema=1,
    )
    return path


def _provenance() -> dict[str, object]:
    return record_live_squashfs_mutation(
        pre_sha256="aa" * 32,
        post_sha256="bb" * 32,
        injected_files=list(EXPECTED_INJECTED_FILES),
    )


def _green_record(base: Path) -> tuple[dict[str, object], Path, Path]:
    image = _write_image(base)
    bundle = _write_bundle(base)
    record = build_product_identity_record(
        installer_image=image,
        release_bundles=[bundle],
        squashfs_mutation=_provenance(),
    )
    return record, image, bundle


class IdentityRegisterTests(unittest.TestCase):
    def test_pinned_unit_set_covers_p5_dot_3(self) -> None:
        self.assertEqual(len(PRODUCT_IDENTITY_UNITS), 10)
        for required in (
            "build/installer-overlay/etc/systemd/system/greia-install-transaction.service",
            "build/installer-overlay/etc/systemd/system/greia-install-transaction.socket",
            "build/overlay/etc/systemd/system/greia-system-update.service",
            "build/overlay/etc/systemd/system/greia-system-update.socket",
            "build/overlay/etc/systemd/system/greia-launcher.service",
            "build/overlay/etc/systemd/system/greia-boot-observer.service",
            "build/overlay/etc/systemd/system/greia-boot-health.service",
            "build/overlay/etc/systemd/system/greia-boot-health.socket",
            "build/overlay/etc/systemd/system/greia-candidate-recovery.service",
            "build/overlay/etc/systemd/system/greia-candidate-recovery.timer",
        ):
            self.assertIn(required, PRODUCT_IDENTITY_UNITS)

    def test_pinned_module_set_covers_service_owners(self) -> None:
        self.assertEqual(len(PRODUCT_IDENTITY_MODULES), 7)
        for required in (
            "src/greia_installer/transaction_service.py",
            "src/greia_installer/transaction_client.py",
            "src/greia_platform/system_updates.py",
            "src/greia_platform/boot_observation.py",
            "src/greia_platform/boot_health_service.py",
            "src/greia_launcher/boot_health.py",
            "src/greia_platform/boot_transaction.py",
        ):
            self.assertIn(required, PRODUCT_IDENTITY_MODULES)


class IdentityGreenTests(unittest.TestCase):
    def test_complete_record_binds_exact_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            record, image, bundle = _green_record(base)
            self.assertEqual(record["schema_version"], UNIT_IDENTITY_SCHEMA_VERSION)
            units = record["units"]
            modules = record["modules"]
            self.assertEqual(set(units["entries"]), set(PRODUCT_IDENTITY_UNITS))
            self.assertEqual(set(modules["entries"]), set(PRODUCT_IDENTITY_MODULES))
            self.assertEqual(record["installer_image"]["sha256"], sha256_file(image))
            self.assertEqual(
                record["installer_image"]["size_bytes"], image.stat().st_size
            )
            bundle_entries = record["release_bundles"]
            self.assertEqual(set(bundle_entries), {bundle.name})
            self.assertEqual(bundle_entries[bundle.name]["sha256"], sha256_file(bundle))
            mutation = record["squashfs_mutation"]
            self.assertEqual(mutation["pre_sha256"], "aa" * 32)
            self.assertEqual(mutation["post_sha256"], "bb" * 32)
            self.assertEqual(mutation["injected_files"], EXPECTED_INJECTED_FILES)
            self.assertFalse(mutation["source_image_mutated"])
            self.assertFalse(record["source_image_mutated"])
            # Binding at evidence time: re-hash proves the record names the
            # exact files, not a prediction.
            assert_product_identity_complete(
                record, installer_image=image, release_bundles=[bundle]
            )

    def test_recorded_hashes_are_read_from_real_bytes(self) -> None:
        import hashlib as _hashlib

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            record, image, bundle = _green_record(base)
            self.assertEqual(
                record["installer_image"]["sha256"],
                _hashlib.sha256(image.read_bytes()).hexdigest(),
            )
            self.assertEqual(
                record["release_bundles"][bundle.name]["sha256"],
                _hashlib.sha256(bundle.read_bytes()).hexdigest(),
            )
            from tools.x8_qemu.lifecycle import PROJECT_ROOT

            unit_path = (
                PROJECT_ROOT
                / "build/overlay/etc/systemd/system/greia-launcher.service"
            )
            self.assertEqual(
                record["units"]["entries"][
                    "build/overlay/etc/systemd/system/greia-launcher.service"
                ]["sha256"],
                _hashlib.sha256(unit_path.read_bytes()).hexdigest(),
            )
            module_path = PROJECT_ROOT / "src/greia_platform/boot_transaction.py"
            self.assertEqual(
                record["modules"]["entries"][
                    "src/greia_platform/boot_transaction.py"
                ]["sha256"],
                _hashlib.sha256(module_path.read_bytes()).hexdigest(),
            )

    def test_run_product_evidence_carries_bound_identity(self) -> None:
        # Production-proof through the real entry point: the identity
        # record is built inside run_product from the booted image, the
        # staged bundle and the clone-injection provenance, and re-asserts
        # GREEN against those same artifacts.
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            official = _write_image(base, "official.img")
            bundle = _write_bundle(base)
            seen: dict[str, object] = {}
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
                    official_image=official,
                )
                result = harness.run_product(
                    release_bundle=bundle,
                    target_fn=lambda p: {
                        "target": str(p),
                        "size_bytes": _product.DISPOSABLE_TARGET_BYTES,
                    },
                    clone_fn=lambda s, d: {
                        "source_sha256": sha256_file(Path(s)),
                        "clone": str(d),
                    },
                    inject_fn=lambda c: {
                        "clone": str(c),
                        "pre_sha256": "aa" * 32,
                        "post_sha256": "bb" * 32,
                        "injected_files": list(EXPECTED_INJECTED_FILES),
                        "source_image_mutated": False,
                    },
                    materialize_fn=lambda d, i: None,
                    boot_fn=lambda phase, *a: seen.setdefault(
                        "boots", []
                    ).append(phase),
                    observe_fn=lambda t: {"default_slot": "A"},
                )
            identity = result["unit_identity"]
            self.assertEqual(
                identity["installer_image"]["sha256"],
                result["installer_image_sha256"],
            )
            self.assertEqual(
                identity["release_bundles"][bundle.name]["sha256"],
                result["release_bundle_sha256"],
            )
            assert_product_identity_complete(
                identity, installer_image=official, release_bundles=[bundle]
            )


class IdentityNegativeTests(unittest.TestCase):
    def test_missing_unit_tree_is_blocked_never_partial(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            image = _write_image(base)
            bundle = _write_bundle(base)
            with self.assertRaises(LifecycleHarnessError) as caught:
                build_product_identity_record(
                    project_root=base / "empty-root",
                    installer_image=image,
                    release_bundles=[bundle],
                    squashfs_mutation=_provenance(),
                )
            self.assertIn("BLOCKED", str(caught.exception))

    def test_missing_image_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            bundle = _write_bundle(base)
            with self.assertRaises(LifecycleHarnessError) as caught:
                build_product_identity_record(
                    installer_image=base / "absent.img",
                    release_bundles=[bundle],
                    squashfs_mutation=_provenance(),
                )
            self.assertIn("BLOCKED", str(caught.exception))

    def test_missing_bundle_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            image = _write_image(base)
            with self.assertRaises(LifecycleHarnessError) as caught:
                build_product_identity_record(
                    installer_image=image,
                    release_bundles=[base / "absent.greiaupdate"],
                    squashfs_mutation=_provenance(),
                )
            self.assertIn("BLOCKED", str(caught.exception))

    def test_empty_bundle_set_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            image = _write_image(base)
            with self.assertRaises(LifecycleHarnessError):
                build_product_identity_record(
                    installer_image=image,
                    release_bundles=[],
                    squashfs_mutation=_provenance(),
                )

    def test_missing_provenance_is_red_not_partial(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            image = _write_image(base)
            bundle = _write_bundle(base)
            with self.assertRaises(LifecycleHarnessError):
                build_product_identity_record(
                    installer_image=image,
                    release_bundles=[bundle],
                    squashfs_mutation=None,
                )

    def test_missing_provenance_field_is_red(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            image = _write_image(base)
            bundle = _write_bundle(base)
            partial = {
                "pre_sha256": "aa" * 32,
                "injected_files": list(EXPECTED_INJECTED_FILES),
            }
            with self.assertRaises(LifecycleHarnessError) as caught:
                build_product_identity_record(
                    installer_image=image,
                    release_bundles=[bundle],
                    squashfs_mutation=partial,
                )
            self.assertIn("post_sha256", str(caught.exception))

    def test_empty_injected_list_is_red(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            image = _write_image(base)
            bundle = _write_bundle(base)
            with self.assertRaises(LifecycleHarnessError):
                build_product_identity_record(
                    installer_image=image,
                    release_bundles=[bundle],
                    squashfs_mutation={
                        "pre_sha256": "aa" * 32,
                        "post_sha256": "bb" * 32,
                        "injected_files": [],
                    },
                )

    def test_non_hex_provenance_sha_is_red(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            image = _write_image(base)
            bundle = _write_bundle(base)
            with self.assertRaises(LifecycleHarnessError):
                build_product_identity_record(
                    installer_image=image,
                    release_bundles=[bundle],
                    squashfs_mutation={
                        "pre_sha256": "not-a-sha",
                        "post_sha256": "bb" * 32,
                        "injected_files": list(EXPECTED_INJECTED_FILES),
                    },
                )

    def test_mutated_source_image_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            image = _write_image(base)
            bundle = _write_bundle(base)
            with self.assertRaises(LifecycleHarnessError):
                build_product_identity_record(
                    installer_image=image,
                    release_bundles=[bundle],
                    squashfs_mutation={
                        "pre_sha256": "aa" * 32,
                        "post_sha256": "bb" * 32,
                        "injected_files": list(EXPECTED_INJECTED_FILES),
                        "source_image_mutated": True,
                    },
                )

    def test_run_product_refuses_flat_mutated_source_image(self) -> None:
        # Production-proof through the real entry point: a flat
        # clone-mutation provenance carrying ``source_image_mutated=True``
        # must reach the existing refusal (RED naming the mutated source
        # image), never normalized to ``False``; the same flat mapping
        # with ``False`` still builds a complete record (GREEN).
        def _run_with_flat_flag(base: Path, flag: object) -> dict[str, object]:
            official = _write_image(base, "official.img")
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
                    official_image=official,
                )
                return harness.run_product(
                    release_bundle=bundle,
                    target_fn=lambda p: {
                        "target": str(p),
                        "size_bytes": _product.DISPOSABLE_TARGET_BYTES,
                    },
                    clone_fn=lambda s, d: {
                        "source_sha256": sha256_file(Path(s)),
                        "clone": str(d),
                    },
                    inject_fn=lambda c: {
                        "clone": str(c),
                        "pre_sha256": "aa" * 32,
                        "post_sha256": "bb" * 32,
                        "injected_files": list(EXPECTED_INJECTED_FILES),
                        "source_image_mutated": flag,
                    },
                    materialize_fn=lambda d, i: None,
                    boot_fn=lambda phase, *a: None,
                    observe_fn=lambda t: {"default_slot": "A"},
                )

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            with self.assertRaises(LifecycleHarnessError) as caught:
                _run_with_flat_flag(base, True)
            self.assertIn("mutated source image", str(caught.exception))
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            official = base / "official.img"
            bundle = base / "greia-release.greiaupdate"
            result = _run_with_flat_flag(base, False)
            identity = result["unit_identity"]
            assert_product_identity_complete(
                identity, installer_image=official, release_bundles=[bundle]
            )

    def test_symlinked_identity_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            real = _write_image(base, "real.img")
            link = base / "link.img"
            link.symlink_to(real)
            with self.assertRaises(LifecycleHarnessError):
                record_file_identity(link, role="built installer image")


class IdentityDriftTests(unittest.TestCase):
    """Registered-baseline gate: disappearance, extra or tamper is RED."""

    def test_unexplained_disappearance_is_red(self) -> None:
        import copy as _copy

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            record, image, bundle = _green_record(base)
            drifted = _copy.deepcopy(record)
            drifted["units"]["entries"].pop(PRODUCT_IDENTITY_UNITS[0])
            with self.assertRaises(LifecycleHarnessError) as caught:
                assert_product_identity_complete(
                    drifted, installer_image=image, release_bundles=[bundle]
                )
            self.assertIn("missing", str(caught.exception))

    def test_unregistered_extra_entry_is_red(self) -> None:
        import copy as _copy

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            record, image, bundle = _green_record(base)
            drifted = _copy.deepcopy(record)
            drifted["modules"]["entries"]["src/greia_platform/audio.py"] = {
                "path": "src/greia_platform/audio.py",
                "size_bytes": 1,
                "sha256": "cc" * 32,
            }
            with self.assertRaises(LifecycleHarnessError) as caught:
                assert_product_identity_complete(
                    drifted, installer_image=image, release_bundles=[bundle]
                )
            self.assertIn("extra", str(caught.exception))

    def test_tampered_sha_is_red_positive_control(self) -> None:
        # Synthetic-violation control: flip one recorded SHA char; the
        # gate must go RED, proving it detects what it claims to detect.
        import copy as _copy

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            record, image, bundle = _green_record(base)
            drifted = _copy.deepcopy(record)
            name = PRODUCT_IDENTITY_UNITS[4]
            entry = dict(drifted["units"]["entries"][name])
            tampered = ("0" if entry["sha256"][0] != "0" else "1") + entry["sha256"][1:]
            entry["sha256"] = tampered
            drifted["units"]["entries"][name] = entry
            with self.assertRaises(LifecycleHarnessError) as caught:
                assert_product_identity_complete(
                    drifted, installer_image=image, release_bundles=[bundle]
                )
            self.assertIn(name, str(caught.exception))

    def test_wrong_image_binding_is_red(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            record, _image, bundle = _green_record(base)
            other = _write_image(base, "other.img")
            other.write_bytes(b"different-official-bytes" * 64)
            with self.assertRaises(LifecycleHarnessError) as caught:
                assert_product_identity_complete(
                    record, installer_image=other, release_bundles=[bundle]
                )
            self.assertIn("booted image", str(caught.exception))

    def test_wrong_bundle_set_is_red(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            record, image, _bundle = _green_record(base)
            other = _write_bundle(base, "other.greiaupdate")
            with self.assertRaises(LifecycleHarnessError):
                assert_product_identity_complete(
                    record, installer_image=image, release_bundles=[other]
                )


if __name__ == "__main__":
    unittest.main()
