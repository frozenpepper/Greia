"""Exercise Parent HTTP upload through the real package and Shell registries."""
from __future__ import annotations

import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from unittest import mock

from greia_launcher.composition import ComposedActivityRegistry, resolve_parent_active_set
from greia_parent.production_api import ProductionParentApiApplication, ProductionParentApiHTTPServer
from greia_platform.activities import RuntimeCatalogue
from greia_platform.trust import ActivitySource, PackageTrust

ROOT = Path(__file__).resolve().parents[1]
ACTIVITY_ID = 'org.greia.parent-upload-probe'


class ParentActivityUploadTests(unittest.TestCase):
    def test_capability_refuses_unwritable_store_and_respects_off_override(self):
        from greia_parent.package_api import _activity_install_enabled
        from greia_platform.activity_packages import ActivityPackageService
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            store = root / 'packages'
            store.mkdir()
            service = ActivityPackageService(state_root=store, runtime_catalogue=ROOT / 'runtime/child-runtime.toml')
            with mock.patch.dict(os.environ, {'GREIA_PARENT_ACTIVITY_INSTALL': 'false'}):
                self.assertFalse(_activity_install_enabled(service))
            with mock.patch.dict(os.environ, {'GREIA_PARENT_ACTIVITY_INSTALL': 'true'}), \
                 mock.patch('greia_parent.package_api.os.access', return_value=False):
                self.assertFalse(_activity_install_enabled(service))
            with mock.patch.dict(os.environ, {'GREIA_PARENT_ACTIVITY_INSTALL': 'true'}):
                self.assertTrue(_activity_install_enabled(service))

    def test_upload_publishes_into_the_running_shell_registry(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            store = root / 'packages'
            store.mkdir()
            builtins = root / 'builtins'
            builtins.mkdir()
            env = {'GREIA_OS_ROOT': str(ROOT), 'GREIA_PARENT_ACTIVITY_PACKAGE_ROOT': str(store)}
            with mock.patch.dict(os.environ, env):
                os.environ.pop('GREIA_PARENT_ACTIVITY_INSTALL', None)
                app = ProductionParentApiApplication(
                    ROOT, root / 'parent', profiles_dir=root / 'profiles',
                    hardware_settings_dir=root / 'hardware',
                    hardware_status_path=root / 'hardware.json',
                    active_profile_status_path=root / 'active.json',
                )
                self.assertTrue(app.index_payload()['capabilities']['activities.install'])
                app.active_session.clear()
                app.package_service.built_in_root = builtins
                # Materialize the initial empty generation exactly as an install would.
                app.package_service._ensure_roots()
                parent = resolve_parent_active_set().source
                runtime = RuntimeCatalogue.load(ROOT / 'runtime/child-runtime.toml')
                registry = ComposedActivityRegistry(
                    (ActivitySource(builtins, PackageTrust.BUILT_IN, 'greia-system'), parent), runtime, ()
                )
                before = registry.discovery_token()
                token = str(app.bootstrap_device('greia', 'test browser')['credential'])
                archive = root / 'probe.greiaactivity'
                source = ROOT / 'activities/painting'
                with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as out:
                    for path in sorted(source.rglob('*')):
                        if not path.is_file() or '__pycache__' in path.parts:
                            continue
                        relative = path.relative_to(source).as_posix()
                        if relative == 'activity.toml':
                            out.writestr(relative, path.read_text().replace('id = "org.greia.painting"', f'id = "{ACTIVITY_ID}"', 1))
                        else:
                            out.write(path, relative)
                server = ProductionParentApiHTTPServer(('127.0.0.1', 0), app)
                thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': 0.05}, daemon=True)
                thread.start()
                try:
                    url = f'http://127.0.0.1:{server.server_address[1]}/api/v1/activities/install'
                    def post(body):
                        request = urllib.request.Request(url, data=body, method='POST', headers={
                            'Authorization': f'Bearer {token}',
                            'Content-Type': 'application/vnd.greia.activity+zip',
                        })
                        return urllib.request.urlopen(request, timeout=60)
                    with self.assertRaises(urllib.error.HTTPError) as bad:
                        post(b'not an archive')
                    self.assertEqual(bad.exception.code, 400)
                    self.assertEqual(registry.discovery_token(), before)
                    app.active_session.write(app.profile_store.list_profiles()[0])
                    with self.assertRaises(urllib.error.HTTPError) as busy:
                        post(archive.read_bytes())
                    self.assertEqual(busy.exception.code, 409)
                    self.assertEqual(registry.discovery_token(), before)
                    app.active_session.clear()
                    with post(archive.read_bytes()) as response:
                        self.assertEqual(response.status, 201)
                        receipt = json.load(response)['installed']
                    self.assertEqual(receipt['activity_id'], ACTIVITY_ID)
                    self.assertNotEqual(registry.discovery_token(), before)
                    self.assertTrue(registry.parent_source_needs_rescan)
                    registrations = registry.discover_registrations()
                    self.assertFalse(registry.parent_source_needs_rescan)
                    parent_activity = next(item for item in registrations if item.manifest.activity_id == ACTIVITY_ID)
                    self.assertEqual(parent_activity.package_trust, PackageTrust.PARENT_TRUSTED_UNSIGNED)
                    self.assertEqual(registry.registration_for(parent_activity.manifest), parent_activity)
                    with self.assertRaises(urllib.error.HTTPError) as duplicate:
                        post(archive.read_bytes())
                    self.assertEqual(duplicate.exception.code, 400)
                    self.assertTrue((app.package_service.active_root / ACTIVITY_ID).is_dir())
                    installed_token = registry.discovery_token()
                    app.package_service.uninstall(ACTIVITY_ID)
                    self.assertNotEqual(registry.discovery_token(), installed_token)
                    self.assertNotIn(ACTIVITY_ID, [r.manifest.activity_id for r in registry.discover_registrations()])
                finally:
                    server.shutdown()
                    server.server_close()
                    thread.join(timeout=5)


if __name__ == '__main__': unittest.main()
