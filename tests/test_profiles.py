from __future__ import annotations

import json
import os
import stat
import shutil
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

from greia_platform.customization import ThemeStore
from greia_platform.profiles import (
    ActiveProfileSession,
    ProfileError,
    ProfileStore,
    write_avatar_request,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ProfileStoreTests(unittest.TestCase):
    def make_store(self, root: Path) -> ProfileStore:
        return ProfileStore.load(PROJECT_ROOT / "runtime" / "profile-defaults.toml", root)

    def test_initializes_one_unprotected_default_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = self.make_store(Path(temporary))
            profiles = store.ensure_initialized()
            self.assertEqual(len(profiles), 1)
            self.assertEqual(profiles[0].display_name, "Explorer")
            self.assertFalse(profiles[0].has_secret)
            self.assertFalse(profiles[0].mask_secret)
            self.assertTrue(store.context(profiles[0].profile_id).customization_dir.is_dir())

    def test_parent_profile_directories_are_group_writable_setgid(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = self.make_store(Path(temporary))
            profile = store.create("Mia", "robot")
            context = store.context(profile.profile_id)
            for path in (
                store.root,
                store.data_root,
                context.root,
                context.customization_dir,
                context.activities_dir,
            ):
                with self.subTest(path=path):
                    self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o2770)
                    self.assertEqual(path.stat().st_gid, store.root.stat().st_gid)

    # The premise is the Linux kernel rule that mkdir() inside a setgid parent
    # yields a setgid child. BSD/macOS never sets S_ISGID on mkdir(), so the
    # appliance contract can only be observed on Linux.
    @unittest.skipUnless(
        sys.platform.startswith("linux"),
        "setgid inheritance on mkdir is Linux kernel behaviour",
    )
    def test_parent_umask_path_needs_no_sgid_chmod_for_new_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            store = self.make_store(root)
            store.ensure_initialized()
            original_chmod = os.chmod
            original_umask = os.umask(0o007)

            def deny_sgid_chmod(
                path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
                mode: int,
            ) -> None:
                if mode & stat.S_ISGID:
                    raise PermissionError("synthetic RestrictSUIDSGID refusal")
                original_chmod(path, mode)

            try:
                with mock.patch(
                    "greia_platform.profiles.os.chmod",
                    side_effect=deny_sgid_chmod,
                ):
                    profile = store.create("Mia", "robot")
                    context = store.context(profile.profile_id)
            finally:
                os.umask(original_umask)

            for path in (
                context.root,
                context.customization_dir,
                context.activities_dir,
            ):
                with self.subTest(path=path):
                    self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o2770)
                    self.assertEqual(path.stat().st_gid, store.data_root.stat().st_gid)

    def test_profile_creation_fails_before_registry_publish_when_mode_repair_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            store = self.make_store(root)
            first = store.ensure_initialized()[0]
            original_chmod = os.chmod
            original_umask = os.umask(0o027)

            def guarded_chmod(path: str | bytes | os.PathLike[str] | os.PathLike[bytes], mode: int) -> None:
                candidate = Path(path)
                if (
                    mode == 0o2770
                    and candidate.parent == store.data_root
                    and candidate.name != first.profile_id
                ):
                    raise PermissionError("synthetic parent sandbox refusal")
                original_chmod(path, mode)

            try:
                with mock.patch(
                    "greia_platform.profiles.os.chmod",
                    side_effect=guarded_chmod,
                ):
                    with self.assertRaisesRegex(
                        ProfileError,
                        "chmod was refused",
                    ):
                        store.create("Nora", "owl")
            finally:
                os.umask(original_umask)

            profiles = store.list_profiles()
            self.assertEqual([profile.profile_id for profile in profiles], [first.profile_id])
            profile_roots = sorted(
                path.name
                for path in store.data_root.iterdir()
                if path.is_dir()
            )
            self.assertEqual(profile_roots, [first.profile_id])

    def test_parent_service_umask_matches_shared_profile_contract(self) -> None:
        unit = (
            PROJECT_ROOT
            / "build/overlay/etc/systemd/system/greia-parent.service"
        ).read_text(encoding="utf-8")
        self.assertIn("UMask=0007", unit)
        self.assertIn("RestrictSUIDSGID=yes", unit)

    def test_profiles_have_separate_activity_and_customization_roots(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = self.make_store(Path(temporary))
            first = store.ensure_initialized()[0]
            second = store.create("Mia", "robot")
            first_context = store.context(first.profile_id)
            second_context = store.context(second.profile_id)
            self.assertNotEqual(first_context.root, second_context.root)
            self.assertNotEqual(
                first_context.activity_data_dir("shape_garden"),
                second_context.activity_data_dir("shape_garden"),
            )
            first_storage = first_context.activity_storage_dir("org.greia.shape-garden")
            second_storage = second_context.activity_storage_dir("org.greia.shape-garden")
            self.assertNotEqual(first_storage, second_storage)
            self.assertEqual(first_storage.parent, first_context.storage_dir)
            self.assertNotEqual(
                first_storage,
                first_context.activity_data_dir("org.greia.shape-garden"),
            )
            first_theme = ThemeStore.load(
                PROJECT_ROOT / "runtime" / "theme-defaults.toml",
                first_context.customization_dir,
            )
            second_theme = ThemeStore.load(
                PROJECT_ROOT / "runtime" / "theme-defaults.toml",
                second_context.customization_dir,
            )
            first_theme.set_colors(background="sky")
            self.assertEqual(first_theme.resolve().preferences.background, "sky")
            self.assertEqual(second_theme.resolve().preferences.background, "cream")

    def _deny_chmod_of(self, *foreign: Path):
        """Simulate directories owned by another identity (the Parent service).

        chmod by a non-owner is always EPERM, even to the current mode, so any
        chmod attempt on these paths is refused exactly as on the appliance.
        """
        original_chmod = os.chmod
        refused = {Path(path).resolve() for path in foreign}
        attempts: list[Path] = []

        def guarded_chmod(path, mode, *args, **kwargs):
            candidate = Path(path).resolve()
            if candidate in refused:
                attempts.append(candidate)
                raise PermissionError(1, "Operation not permitted", str(path))
            return original_chmod(path, mode, *args, **kwargs)

        return mock.patch("greia_platform.profiles.os.chmod", side_effect=guarded_chmod), attempts

    def test_child_creates_activity_dirs_inside_parent_owned_setgid_collection(self) -> None:
        # Acer sweep 2026-10-16 P0: the Parent service creates activities/ as
        # greiapanel 2770; the child must create its per-Activity leaf there
        # without chmodding (EPERM) or de-setgid'ing the shared parent.
        with tempfile.TemporaryDirectory() as temporary:
            store = self.make_store(Path(temporary))
            profile = store.create("Mia", "robot")
            context = store.context(profile.profile_id)
            self.assertEqual(stat.S_IMODE(context.activities_dir.stat().st_mode), 0o2770)
            patcher, attempts = self._deny_chmod_of(context.activities_dir)
            with patcher:
                first = context.activity_data_dir("painting")
                second = context.activity_data_dir("writing")
                again = context.activity_data_dir("painting")
            self.assertEqual(attempts, [])
            self.assertEqual(first, again)
            self.assertEqual(stat.S_IMODE(context.activities_dir.stat().st_mode), 0o2770)
            for leaf in (first, second):
                with self.subTest(leaf=leaf):
                    self.assertEqual(leaf.parent, context.activities_dir)
                    self.assertEqual(stat.S_IMODE(leaf.stat().st_mode), 0o770)
                    self.assertEqual(leaf.stat().st_gid, store.root.stat().st_gid)

    def test_child_owned_storage_collection_keeps_setgid_across_leaf_creation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = self.make_store(Path(temporary))
            profile = store.create("Mia", "robot")
            context = store.context(profile.profile_id)
            first = context.activity_storage_dir("org.greia.painting")
            self.assertEqual(stat.S_IMODE(context.storage_dir.stat().st_mode), 0o2770)
            # A second leaf must not need any chmod of the shared collection.
            patcher, attempts = self._deny_chmod_of(context.storage_dir)
            with patcher:
                second = context.activity_storage_dir("org.greia.writing")
            self.assertEqual(attempts, [])
            self.assertEqual(stat.S_IMODE(context.storage_dir.stat().st_mode), 0o2770)
            for leaf in (first, second):
                with self.subTest(leaf=leaf):
                    self.assertEqual(stat.S_IMODE(leaf.stat().st_mode), 0o770)
                    self.assertEqual(leaf.stat().st_gid, store.root.stat().st_gid)

    def test_wrong_mode_foreign_activity_collection_still_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = self.make_store(Path(temporary))
            profile = store.create("Mia", "robot")
            context = store.context(profile.profile_id)
            os.chmod(context.activities_dir, 0o2750)
            patcher, attempts = self._deny_chmod_of(context.activities_dir)
            with patcher, self.assertRaisesRegex(ProfileError, "chmod was refused"):
                context.activity_data_dir("painting")
            self.assertEqual(len(attempts), 1)
            self.assertFalse((context.activities_dir / "painting").exists())

    def test_activity_leaf_symlink_and_non_directory_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = self.make_store(Path(temporary))
            profile = store.create("Mia", "robot")
            context = store.context(profile.profile_id)
            outside = Path(temporary) / "outside"
            outside.mkdir()
            (context.activities_dir / "painting").symlink_to(outside)
            with self.assertRaisesRegex(ProfileError, "symbolic link"):
                context.activity_data_dir("painting")
            context.storage_dir.mkdir()
            os.chmod(context.storage_dir, 0o2770)
            (context.storage_dir / "org.greia.painting").write_text("x", encoding="utf-8")
            with self.assertRaisesRegex(ProfileError, "non-directory"):
                context.activity_storage_dir("org.greia.painting")

    def test_optional_secret_is_hashed_and_visible_entry_is_default(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = self.make_store(Path(temporary))
            store.ensure_initialized()
            profile = store.create("Luca", "dinosaur", secret="1234")
            self.assertTrue(profile.has_secret)
            self.assertFalse(profile.mask_secret)
            raw = (Path(temporary) / "profiles.json").read_text(encoding="utf-8")
            self.assertNotIn('"1234"', raw)
            self.assertTrue(store.verify_secret(profile.profile_id, "1234"))
            self.assertFalse(store.verify_secret(profile.profile_id, "0000"))

    def test_avatar_is_allowlisted_and_child_can_change_only_own_avatar(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = self.make_store(Path(temporary))
            profile = store.ensure_initialized()[0]
            updated = store.set_avatar(profile.profile_id, "owl")
            self.assertEqual(updated.avatar_id, "owl")
            with self.assertRaises(ProfileError):
                store.set_avatar(profile.profile_id, "../../bad")


    def test_avatar_request_is_consumed_once_by_profile_store(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = self.make_store(Path(temporary))
            profile = store.ensure_initialized()[0]
            request_path = store.avatar_request_path(profile.profile_id)
            write_avatar_request(
                store.policy, request_path, profile.profile_id, "owl"
            )
            updated = store.consume_avatar_request(profile.profile_id)
            self.assertIsNotNone(updated)
            self.assertEqual(updated.avatar_id, "owl")
            self.assertFalse(request_path.exists())
            self.assertIsNone(store.consume_avatar_request(profile.profile_id))

    def test_final_profile_cannot_be_deleted(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = self.make_store(Path(temporary))
            profile = store.ensure_initialized()[0]
            with self.assertRaises(ProfileError):
                store.delete(profile.profile_id)

    def test_active_session_contains_no_secret_digest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            store = self.make_store(root / "profiles")
            profile = store.create("Nora", "unicorn", secret="cat")
            session = ActiveProfileSession(root / "run" / "active.json")
            session.write(profile)
            payload = session.read()
            self.assertEqual(payload["profile_id"], profile.profile_id)
            raw = json.loads((root / "run" / "active.json").read_text(encoding="utf-8"))
            self.assertNotIn("secret", raw)
            self.assertNotIn("digest", raw)

    def test_active_session_status_uses_its_shared_directory_group(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            status = root / "run" / "active.json"
            session = ActiveProfileSession(status)
            real_chown = os.chown
            with mock.patch("greia_platform.profiles.os.chown", wraps=real_chown) as chown:
                session.clear()
            self.assertEqual(chown.call_count, 1)
            self.assertEqual(chown.call_args.args[1:], (-1, status.parent.stat().st_gid))
            self.assertEqual(status.stat().st_gid, status.parent.stat().st_gid)
            self.assertEqual(stat.S_IMODE(status.stat().st_mode), 0o660)
            with session.profile_picker_restart_guard():
                pass

    def test_restart_fence_blocks_a_new_profile_activation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            store = self.make_store(root / "profiles")
            profile = store.ensure_initialized()[0]
            status = root / "run" / "active.json"
            fence = root / "runtime" / "restart-pending.json"
            fence.parent.mkdir(parents=True)
            fence.write_text("pending\n", encoding="ascii")
            session = ActiveProfileSession(status, restart_fence_path=fence)
            with self.assertRaisesRegex(ProfileError, "restart is pending"):
                session.activate(store, profile.profile_id)
            self.assertFalse(status.exists())

    def test_restart_guard_requires_explicit_idle_marker_and_refuses_active(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            status = root / "run" / "active.json"
            session = ActiveProfileSession(status, lock_path=root / "runtime" / "lock")
            with self.assertRaisesRegex(ProfileError, "state is missing"):
                with session.profile_picker_restart_guard():
                    self.fail("missing profile state must not authorize restart")
            # Launcher clear publishes explicit picker-idle evidence.
            session.clear()
            with session.profile_picker_restart_guard():
                pass
            status.parent.mkdir(parents=True, exist_ok=True)
            status.write_text(
                '{"profile_id":"11111111111141118111111111111111"}\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ProfileError, "profile picker"):
                with session.profile_picker_restart_guard():
                    self.fail("restart must not pass while a child profile is active")



    def test_session_claim_blocks_deletion_until_profile_is_inactive(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            store = self.make_store(root / "profiles")
            store.ensure_initialized()
            second = store.create("Mia", "robot")
            session = ActiveProfileSession(root / "run" / "active.json")
            context = session.activate(store, second.profile_id)
            self.assertEqual(context.profile.profile_id, second.profile_id)
            with self.assertRaisesRegex(ProfileError, "switch away"):
                session.delete_inactive(store, second.profile_id)
            session.clear()
            session.delete_inactive(store, second.profile_id)
            with self.assertRaisesRegex(ProfileError, "does not exist"):
                store.get(second.profile_id)

    def test_truncated_registry_recovers_from_last_atomic_backup(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            store = self.make_store(root)
            profile = store.ensure_initialized()[0]
            (root / "profiles.json").write_text("{truncated", encoding="utf-8")
            recovered = store.list_profiles()
            self.assertEqual(recovered[0].profile_id, profile.profile_id)

    def test_profile_deletion_refuses_symlink_and_keeps_registry_entry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            store = self.make_store(root)
            first = store.ensure_initialized()[0]
            second = store.create("Mia", "robot")
            first_root = store.context(first.profile_id).root
            second_root = store.context(second.profile_id).root
            shutil.rmtree(second_root)
            try:
                second_root.symlink_to(first_root, target_is_directory=True)
            except OSError:
                self.skipTest("symlinks unavailable")
            with self.assertRaisesRegex(ProfileError, "not a managed directory"):
                store.delete(second.profile_id)
            self.assertEqual(store.get(second.profile_id).display_name, "Mia")
            self.assertTrue(first_root.is_dir())

    def test_profile_context_refuses_symlink_inside_managed_tree(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            store = self.make_store(root)
            profile = store.ensure_initialized()[0]
            context = store.context(profile.profile_id)
            shutil.rmtree(context.activities_dir)
            outside = root / "outside"
            outside.mkdir()
            try:
                context.activities_dir.symlink_to(outside, target_is_directory=True)
            except OSError:
                self.skipTest("symlinks unavailable")
            with self.assertRaisesRegex(ProfileError, "symbolic link"):
                store.context(profile.profile_id)

    def test_registry_rejects_unsafe_password_work_factor(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            store = self.make_store(root)
            store.create("Nora", "owl", secret="cat")
            registry_path = root / "profiles.json"
            payload = json.loads(registry_path.read_text(encoding="utf-8"))
            payload["profiles"][0]["secret"]["iterations"] = 1
            registry_path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ProfileError, "iterations"):
                store.list_profiles()

    def test_registry_rejects_malformed_password_digest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            store = self.make_store(root)
            store.create("Nora", "owl", secret="cat")
            registry_path = root / "profiles.json"
            payload = json.loads(registry_path.read_text(encoding="utf-8"))
            payload["profiles"][0]["secret"]["digest"] = "not-base64"
            registry_path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ProfileError, "digest"):
                store.list_profiles()


if __name__ == "__main__":
    unittest.main()
