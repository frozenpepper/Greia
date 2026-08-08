from __future__ import annotations

import shutil
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from greia_platform.activities import ActivityRegistry, ActivityValidationError, RuntimeCatalogue
from greia_platform.permissions import (
    PermissionBroker,
    PermissionDecisionError,
    PermissionPolicy,
)
from greia_platform.trust import ActivitySource, PackageTrust


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_PATH = PROJECT_ROOT / "runtime" / "child-runtime.toml"
POLICY_PATH = PROJECT_ROOT / "runtime" / "permission-policy.toml"


class PermissionBrokerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runtime = RuntimeCatalogue.load(RUNTIME_PATH)

    def _built_in_registry(self) -> ActivityRegistry:
        return ActivityRegistry(
            [
                ActivitySource(
                    PROJECT_ROOT / "activities",
                    trust=PackageTrust.BUILT_IN,
                    source_id="greia-system",
                )
            ],
            self.runtime,
        )

    def test_built_in_settings_receives_only_requested_privileged_grants(self) -> None:
        registry = self._built_in_registry()
        manifests = registry.discover()
        manifest = next(item for item in manifests if item.activity_id == "workshop_settings")
        authority = PermissionBroker.phase0(self.runtime, POLICY_PATH).issue(
            registry.registration_for(manifest)
        )

        self.assertEqual(authority.package_trust, PackageTrust.BUILT_IN)
        self.assertEqual(
            authority.granted_permissions,
            frozenset(
                {
                    "customization.manage",
                    "profile.manage_own",
                    "removable_media.read",
                }
            ),
        )
        self.assertNotIn("display", authority.granted_permissions)
        self.assertIn("display", authority.effective_capabilities)

    def test_built_in_non_system_activity_cannot_self_request_system_permission(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            activities = Path(temporary) / "activities"
            activities.mkdir()
            copied = activities / "shape_garden"
            shutil.copytree(PROJECT_ROOT / "activities" / "shape_garden", copied)
            manifest_path = copied / "activity.toml"
            text = manifest_path.read_text(encoding="utf-8").replace(
                'capabilities = ["display", "pointer", "audio.basic"]',
                'capabilities = ["display", "pointer", "audio.basic", "customization.manage"]',
            )
            manifest_path.write_text(text, encoding="utf-8")
            registry = ActivityRegistry(
                [
                    ActivitySource(
                        activities,
                        trust=PackageTrust.BUILT_IN,
                        source_id="greia-system-test",
                    )
                ],
                self.runtime,
            )
            manifest = registry.discover()[0]
            authority = PermissionBroker.phase0(self.runtime, POLICY_PATH).issue(
                registry.registration_for(manifest)
            )

        self.assertEqual(authority.package_trust, PackageTrust.BUILT_IN)
        self.assertIn("customization.manage", authority.requested_permissions)
        self.assertNotIn("customization.manage", authority.granted_permissions)

    def test_external_package_cannot_gain_privilege_by_claiming_system_id(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            activities = Path(temporary) / "activities"
            activities.mkdir()
            shutil.copytree(
                PROJECT_ROOT / "activities" / "workshop_settings",
                activities / "workshop_settings",
            )
            registry = ActivityRegistry(
                [
                    ActivitySource(
                        activities,
                        trust=PackageTrust.DEVELOPER_UNSIGNED,
                        source_id="external-test",
                    )
                ],
                self.runtime,
            )
            manifest = registry.discover()[0]
            authority = PermissionBroker.phase0(self.runtime, POLICY_PATH).issue(
                registry.registration_for(manifest)
            )

        self.assertEqual(manifest.activity_id, "workshop_settings")
        self.assertEqual(authority.package_trust, PackageTrust.DEVELOPER_UNSIGNED)
        self.assertEqual(authority.granted_permissions, frozenset())
        self.assertTrue(authority.requested_permissions)

    def test_fabricated_manifest_is_not_a_registry_issued_registration(self) -> None:
        registry = self._built_in_registry()
        manifest = next(
            item for item in registry.discover() if item.activity_id == "shape_garden"
        )
        fabricated = replace(
            manifest,
            capabilities=manifest.capabilities + ("customization.manage",),
        )

        with self.assertRaisesRegex(ActivityValidationError, "not issued"):
            registry.registration_for(fabricated)
        with self.assertRaises(PermissionDecisionError):
            PermissionBroker.phase0(self.runtime, POLICY_PATH).issue(fabricated)  # type: ignore[arg-type]

    def test_parent_policy_can_remove_a_built_in_permission(self) -> None:
        registry = self._built_in_registry()
        manifest = next(
            item for item in registry.discover() if item.activity_id == "workshop_settings"
        )
        registration = registry.registration_for(manifest)
        base = PermissionPolicy.load(POLICY_PATH, self.runtime)
        policy = replace(
            base,
            parent_allowed_permissions=base.parent_allowed_permissions
            - {"removable_media.read"},
        )
        authority = PermissionBroker(policy).issue(registration)

        self.assertNotIn("removable_media.read", authority.granted_permissions)
        self.assertIn("customization.manage", authority.granted_permissions)

    def test_missing_permission_capability_blocks_grant(self) -> None:
        registry = self._built_in_registry()
        manifest = next(
            item for item in registry.discover() if item.activity_id == "workshop_settings"
        )
        registration = registry.registration_for(manifest)
        base = PermissionPolicy.load(POLICY_PATH, self.runtime)
        policy = replace(
            base,
            hardware_capabilities=base.hardware_capabilities
            - {"removable_media.read"},
        )
        authority = PermissionBroker(policy).issue(registration)

        self.assertNotIn("removable_media.read", authority.granted_permissions)


if __name__ == "__main__":
    unittest.main()
