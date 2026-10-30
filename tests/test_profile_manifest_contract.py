"""Canonical image-manifest profile contract: writer-produced proof.

The Gate-P5 V12C closure run exposed a shipped writer/reader split: the
declared manifest writer emitted ``profile.profile_id`` while the live
installer protocol readers require ``profile.id``. The canonical key is
``profile.id``. This suite derives its document through the production
writer path (``BuildProfile.load(...).declared_manifest(...)``) and feeds
that exact document to every production reader, so a writer/reader key
divergence fails here instead of at install-prepare time. A hand-written
fixture alone is not acceptable proof.
"""

from __future__ import annotations

import copy
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS = PROJECT_ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from build_profile import BuildProfile  # noqa: E402

# Production dev profile whose target manifest carries the developer-remote
# package set, so the same writer-produced document can feed the installer
# protocol readers, the updater identity reader, and the developer-image
# provisioner reader.
_WRITER_PROFILE = "acer-aspire-one-i386-dev"


def _writer_manifest(scope: str = "target") -> tuple[str, dict]:
    profile = BuildProfile.load(PROJECT_ROOT / "build/profiles" / f"{_WRITER_PROFILE}.toml")
    document = profile.declared_manifest(scope)
    assert isinstance(document, dict)
    return profile.identity.profile_id, document


def _write_json(root: Path, name: str, document: dict) -> Path:
    path = root / name
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


class WriterEmitsCanonicalKeyTests(unittest.TestCase):
    def test_writer_profile_section_is_exactly_canonical(self) -> None:
        expected_id, document = _writer_manifest("target")
        section = document["profile"]
        self.assertEqual(
            set(section),
            {"id", "certification_state", "description"},
        )
        self.assertEqual(section["id"], expected_id)
        self.assertNotIn("profile_id", section)

    def test_writer_installer_scope_is_canonical_too(self) -> None:
        expected_id, document = _writer_manifest("installer")
        self.assertEqual(document["profile"]["id"], expected_id)
        self.assertNotIn("profile_id", document["profile"])


class WriterProducedContractTests(unittest.TestCase):
    """Feed one real writer-produced manifest through every production reader."""

    def test_writer_document_feeds_installer_and_updater_readers(self) -> None:
        from greia_installer.transaction_client import read_compatible_profile_id
        from greia_installer.transaction_service import ServiceState
        from greia_platform.system_updates import (
            _installed_profile_compat_facts,
            resolve_installed_system_identity,
        )

        expected_id, document = _writer_manifest("target")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest_path = _write_json(root, "target-image-profile.json", document)

            # Live installer protocol readers (canonical `id` contract).
            state = ServiceState.from_target_profile(
                manifest_path,
                payload=Path("/run/live/medium/payload/greia-rootfs.squashfs"),
                payload_digest=Path("/etc/greia-os/expected-payload.sha256"),
                project_root=Path("/opt/greia-os"),
            )
            self.assertEqual(state.compatible_profile_id, expected_id)
            self.assertEqual(read_compatible_profile_id(manifest_path), expected_id)

            # Updater installed-profile compatibility fallback.
            facts = _installed_profile_compat_facts(manifest_path)
            self.assertEqual(facts.get("profile"), expected_id)

            # Full updater identity composition with the writer document as
            # the only installed fact source (no release/layout authority,
            # no GREIA_SYSTEM_* environment).
            with mock.patch.dict(
                os.environ,
                {
                    "GREIA_RELEASE_IDENTITY_PATH": str(root / "absent-release.json"),
                    "GREIA_INSTALLED_LAYOUT_RECORD": str(root / "absent-layout.json"),
                    "GREIA_IMAGE_PROFILE_PATH": str(manifest_path),
                    "GREIA_SYSTEM_VERSION": "",
                    "GREIA_SYSTEM_PLATFORM_FAMILY": "",
                    "GREIA_SYSTEM_ARCHITECTURE": "",
                    "GREIA_SYSTEM_PROFILE": "",
                },
                clear=False,
            ):
                identity = resolve_installed_system_identity(
                    layout_record_path=root / "absent-layout.json",
                    release_identity_path=root / "absent-release.json",
                    image_profile_path=manifest_path,
                )
            self.assertEqual(identity.profile, expected_id)

    def test_writer_document_feeds_developer_provisioner_reader(self) -> None:
        from provision_developer_image import DeveloperImageProvisioner, ProvisionConfig

        expected_id, document = _writer_manifest("target")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            profile_path = root / "etc/greia-os/image-profile.json"
            profile_path.parent.mkdir(parents=True)
            profile_path.write_text(json.dumps(document), encoding="utf-8")
            provisioner = DeveloperImageProvisioner(
                ProvisionConfig(
                    image=root / "unused.img",
                    output_dir=root / "out",
                    expected_profile=expected_id,
                )
            )
            payload = provisioner._validate_profile(root)
            self.assertEqual(payload["profile"]["id"], expected_id)


class RetiredKeyRefusedTests(unittest.TestCase):
    """Negative/sensitivity proof: only the retired `profile_id` key refuses fail-closed."""

    @staticmethod
    def _retired(document: dict) -> dict:
        mutated = copy.deepcopy(document)
        section = mutated["profile"]
        section["profile_id"] = section.pop("id")
        return mutated

    def test_retired_key_only_document_is_refused_by_every_reader(self) -> None:
        from greia_installer.transaction_client import TransactionClientError
        from greia_installer.transaction_client import read_compatible_profile_id
        from greia_installer.transaction_service import (
            ServiceState,
            TransactionServiceError,
        )
        from greia_platform.system_updates import (
            _installed_profile_compat_facts,
            resolve_installed_system_identity,
        )
        from provision_developer_image import (
            DeveloperImageProvisionError,
            DeveloperImageProvisioner,
            ProvisionConfig,
        )

        expected_id, document = _writer_manifest("target")
        retired = self._retired(document)
        self.assertNotIn("id", retired["profile"])
        self.assertEqual(retired["profile"]["profile_id"], expected_id)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            retired_path = _write_json(root, "retired-profile.json", retired)

            # Installer protocol readers fail closed (no release facts / no id).
            with self.assertRaises(TransactionServiceError):
                ServiceState.from_target_profile(
                    retired_path,
                    payload=Path("/payload"),
                    payload_digest=Path("/digest"),
                    project_root=Path("/opt/greia-os"),
                )
            with self.assertRaises(TransactionClientError):
                read_compatible_profile_id(retired_path)

            # Updater fallback contributes no profile fact, so identity stays
            # unknown (which the compatibility gate refuses).
            self.assertNotIn("profile", _installed_profile_compat_facts(retired_path))
            with mock.patch.dict(
                os.environ,
                {
                    "GREIA_RELEASE_IDENTITY_PATH": str(root / "absent-release.json"),
                    "GREIA_INSTALLED_LAYOUT_RECORD": str(root / "absent-layout.json"),
                    "GREIA_IMAGE_PROFILE_PATH": str(retired_path),
                    "GREIA_SYSTEM_VERSION": "",
                    "GREIA_SYSTEM_PLATFORM_FAMILY": "",
                    "GREIA_SYSTEM_ARCHITECTURE": "",
                    "GREIA_SYSTEM_PROFILE": "",
                },
                clear=False,
            ):
                identity = resolve_installed_system_identity(
                    layout_record_path=root / "absent-layout.json",
                    release_identity_path=root / "absent-release.json",
                    image_profile_path=retired_path,
                )
            self.assertEqual(identity.profile, "unknown")

            # Developer provisioner refuses the retired-key document.
            dev_root = root / "devroot"
            profile_path = dev_root / "etc/greia-os/image-profile.json"
            profile_path.parent.mkdir(parents=True)
            profile_path.write_text(json.dumps(retired), encoding="utf-8")
            provisioner = DeveloperImageProvisioner(
                ProvisionConfig(
                    image=dev_root / "unused.img",
                    output_dir=dev_root / "out",
                    expected_profile=expected_id,
                )
            )
            with self.assertRaisesRegex(DeveloperImageProvisionError, "unexpected profile"):
                provisioner._validate_profile(dev_root)

    def test_missing_profile_id_is_refused(self) -> None:
        from greia_installer.transaction_client import TransactionClientError
        from greia_installer.transaction_client import read_compatible_profile_id
        from greia_installer.transaction_service import (
            ServiceState,
            TransactionServiceError,
        )
        from greia_platform.system_updates import _installed_profile_compat_facts

        _, document = _writer_manifest("target")
        mutated = copy.deepcopy(document)
        del mutated["profile"]["id"]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            missing_path = _write_json(root, "missing-id.json", mutated)
            with self.assertRaises(TransactionServiceError):
                ServiceState.from_target_profile(
                    missing_path,
                    payload=Path("/payload"),
                    payload_digest=Path("/digest"),
                    project_root=Path("/opt/greia-os"),
                )
            with self.assertRaises(TransactionClientError):
                read_compatible_profile_id(missing_path)
            self.assertNotIn("profile", _installed_profile_compat_facts(missing_path))


if __name__ == "__main__":
    unittest.main()
