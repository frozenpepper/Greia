# Update release acceptance result — A/B and application packages

Date: 2026-10-27/28 · Status: **INSTALLED LINUX/QEMU ACCEPTANCE PASS** for both
current update mechanisms · Tested source:
`810caa91f363a5eb39676f68862a8bef276a6998` · Work order:
[`GREIA_UPDATE_RELEASE_ACCEPTANCE.md`](../testing/GREIA_UPDATE_RELEASE_ACCEPTANCE.md)

The work was rebased onto concurrent `main`; the later commits there change only
licensing/trademark documentation, so the tested production source tree is
unchanged.

Host: Ubuntu 24.04 x86_64 (kernel 7.0.0-38), Python 3.12.3, QEMU 8.2.2, KVM.
Guest: disposable i386 Acer A/B fixture, 1024 MiB RAM, one vCPU.
Evidence root:
`/var/tmp/greia-update-acceptance-810caa91f363a5eb39676f68862a8bef276a6998-20261027T204906Z/`

## Result summary

The full-system A/B route now installs, boots A, stages and accepts B through
the shipped updater, rolls back a health-failing candidate to A, and recovers
from a power cut during the inactive-slot write. The lightweight
`.greia_update` route applies Python, built-in Activity and combined packages
through the installed Parent HTTPS API, keeps processing after the upload
client disconnects, preserves profiles/saves/settings and EN/IT/ES/FR, and
restores the previous application generation after a deliberately broken
Python package.

| Scenario | Result |
|---|---|
| Fresh A/B installation | **PASS** |
| First healthy boot A | **PASS** |
| Stage update into B | **PASS** |
| Activate update | **PASS** |
| Healthy boot B | **PASS** |
| Failed B update rollback | **PASS** |
| Interrupted update recovery | **PASS** |
| Python application update | **PASS** |
| Activity update | **PASS** |
| Combined update | **PASS** |
| Parent disconnect continuation | **PASS** |
| Failed application update recovery | **PASS** |
| EN/IT/ES/FR language preservation | **PASS** |

## Production defects found and fixed

1. **i386 block capacity was unobservable.** `_block_node_size_bytes` used the
   x86_64 `BLKGETSIZE64` request and relied on a possibly absent `blockdev`.
   It now selects the native 32/64-bit request, falls back to bounded
   `/sys/class/block/<name>/size` sectors, then `blockdev`, and reports each
   method's cause. The observed size is still checked against the installed
   slot capacity.
2. **Finalized A/B slots lacked GRUB's kernel/initramfs aliases.** The
   production `_MountTrackingFilesystem` wrapper did not expose the finalizer's
   `link_file` seam, so a staged B received `finalized-generic.json` but not
   `boot/vmlinuz-greia` / `boot/initramfs-greia.img` and could not boot.
   The wrapper now delegates `link_file`; the standard finalizer publishes the
   aliases.
3. **UUID binding ran before the filesystem check.** A fixture payload whose
   journal needed replay made `tune2fs -U` refuse with "requires a freshly
   checked filesystem". Finalization now checks/expands the staged filesystem
   before binding the role UUID, then mounts with the same identity checks.
4. **The candidate health-deadline rollback timer was not enabled.** A
   candidate that booted but never became healthy stayed on B indefinitely.
   A/B image composition now enables `greia-candidate-recovery.timer` (and the
   image verifier requires it), so the 3-minute deadline records `FAILED` and
   reboots to the accepted slot.
5. **Application generations could not identify an A/B root.** The stable
   bootstrap required `/etc/greia-os/root-filesystem-uuid`, which only
   single-root build images carry. It now falls back to the installed layout
   record plus `root=PARTUUID=` from `/proc/cmdline`, binding the candidate
   boot to its own slot even while the accepted slot is still A.
6. **A new upload could be deleted by the previous job's cleanup.** The
   terminal job state and candidate cleanup were separate lock acquisitions.
   Terminal publication now clears the candidate/pending marker under the same
   job lock and verifies the expected job ID, so a fast follow-up upload
   cannot be mistaken for the completed job.
7. **Diagnostics:** filesystem command failures now include bounded stdout
   when stderr is empty, so a silent `tune2fs` refusal names its cause.

Focused harness defects fixed while exercising the failure lanes (test-only):
candidate staging before `update-verify`, control-disk sizing for real v3
bundles, A-start recovery report shape, post-recovery prefailure inspection,
and accepting a settled `failed` journal after rollback.

## Artifacts under test

| Artifact | SHA-256 | Bytes |
|---|---|---|
| Base A/B v3 bundle `greia-acceptance-fixture-0.13.0-phase0-dev` | `322c70744ee92cbb660dc3f28b718836c2b20b15d49bbc573d4fcb97fd971eeb` | 714,362,489 |
| A/B installer `acer-aspire-one-i386-ab` | `812f13ce8d84dd746f3551a6cd097e9582c3954207059c364ce6f049e284467d` | 2,270,167,040 |
| Next v3 bundle `greia-acceptance-fixture-0.13.1-phase0-dev` | `467178951fcd3e1e462205c8f5a416d3e51c24b92431dcc934e83b66d038cc25` | 714,357,272 |
| Deliberately unhealthy v3 candidate `greia-acceptance-unhealthy-0.13.2-phase0-dev` | `d07904d8bb395b9df597f5e8ff866c9b518c3d999c32e10421aba2cf3af8247f` | 794,131,238 |
| `python.greia_update` | `ba32bf633b6a5a0d4bdfb83a99f89677f2fdb692bf9ccd447772a986a26b2c4c` | 1,325,204 |
| `activity.greia_update` | `80450e3f4409143cf0b23afbfaba204f80df17efb682308840f0a45467aecbc7` | 230,370 |
| `combined.greia_update` | `5eda0e82abd733a70721a921e03129383de085d8bd86aff5d2c168f98156704a` | 1,555,354 |
| `broken.greia_update` | `07ee09b1c41c1e4790ca3bcf9bc907c7dce3fab2c6960249f997d318bf00ad26` | 1,324,955 |

## Evidence by lane

### Lane A — full-system A/B

- **Install:** `vm/install/result.json`; shipped installer phases
  `install-prepare`/`install-execute` PASS; observed default A, valid MBR
  PARTUUIDs, PERSIST schema 1.
- **First A boot:** `vm/first-boot/result.json`; accepted
  `greia-acceptance-fixture-0.13.0-phase0-dev`, default/last-booted A,
  journal `accepted`, unbooted B digest unchanged.
- **A → B:** `vm/healthy-update/result.json`; phases
  `status → verify → stage → arm → B health`; B accepted
  `greia-acceptance-fixture-0.13.1-phase0-dev`, default/last-booted B,
  journal `accepted`, layout authority B, PERSIST schema 1.
- **Failed B rollback:** `vm/rollback/result.json`; unhealthy B staged/armed
  and booted, the deadline trigger recorded
  `recovery:health-service-failure:automatic-reboot:deadline expired without
  BOOT_HEALTHY`, QEMU returned to A, and A remained accepted
  `greia-acceptance-fixture-0.13.0-phase0-dev` with default/last-booted A.
- **Interrupted write:** `vm/interrupted-stage/result.json`; QEMU was killed
  25 s into a real `update-stage`. Offline observation immediately after the
  cut and after a cold reboot both showed default/committed/last-booted A,
  accepted base release, journal `accepted`; the recovery boot powered off
  cleanly. The partially written B was never armed.
- Serial logs and control-phase artifacts are under each
  `vm/<leg>/product/` directory.

### Lane B — `.greia_update` application packages

Installed baseline: accepted A clone of the same fixture. The Parent HTTPS
service was reached on the guest loopback with the real pairing/bootstrap
endpoint and bearer credential. The serial console used a test-only root
password on the disposable clone; **no production helper or application code
was hand-patched**. Each upload returned `202`, then the client waited 20 s
without polling to model an app disconnect before status polling resumed.

- **Python:** job `186e...` reached `applied`; generation
  `app-186e131e...` contains
  `src/greia_platform/acceptance_canary.py`; Activity stayed at version
  `0.1.0`.
- **Activity:** generation `app-985d07cc...` contains the writing canary file,
  `activity.toml` version `0.1.1-acceptance`, and the 45-registration built-in
  index (only the listed Activity changed).
- **Combined:** generation `app-33c72183...` contains both the Python canary
  and the Activity canary/version; the index still has 45 registrations.
- **Failed application update:** broken launcher package `82575d...` reached
  `rolled_back` with `launcher_not_ready`; the active generation remained the
  previous combined generation `app-33c72183...`, launcher and Parent were
  active, and `/api/v1/system/update` still returned HTTP 200.
- **Persistence:** a real profile `Acceptance`
  (`1c30aeb2f87d42e8b0f224951759cba5`) was created through the Parent
  `/profiles` API before the updates; the existing `Explorer` profile also
  remained. Profile registry, profile save marker, PERSIST state marker and
  settings marker were identical after every update and after rollback.
- **Languages:** every updated generation contains paired
  `src/greia_platform/languages/{en,it,es,fr}/manifest.json` and `ui.json`.
  `app-activity-index-facts.txt` records the offline index/profile facts.
- Evidence: `vm/app-updates/packages.img` (`evidence/results.txt`,
  `snapshot-*.txt`, `status-*.json`, `upload-*.json`) and
  `vm/app-updates/parent-target4.img`.

## Verification

- Focused update/lifecycle suites at `810caa91f`: **353 tests PASS**
  (`focused-update-tests.log`).
- `make verify` at `810caa91f`: **6,009 tests, 7 failures, 3 errors, 3
  skips; NOT GREEN** (`make-verify.log`, exit 2). The failures/errors are the
  documented Linux baseline, not new update regressions: Foresta content
  (3), Parent Wi-Fi source assertions (2), MBR message wording (1),
  `morbidi_mostriciattoli` timing (1), ARM64 profile error (1), and two
  optional voice-module errors (2). No update/capacity/finalizer/bootstrap
  test failed.

## Not run / remaining gaps

- Physical Acer/USB installer, physical rollback, and family release approval.
- HTML/Mobile browser upload clicks (the installed Parent HTTPS API and bearer
  pairing were used; the clients call the same endpoint).
- Reverse B → A full-system update, full-system `.greia_update` wrapper,
  HTTP 507 low-space, and mobile-client upload.
- The deliberately unhealthy A/B candidate is a test fixture, not a release.
  No production image, family disk or real child data was touched.

This result establishes installed Linux/QEMU acceptance for the two update
mechanisms at the recorded source. It does not establish physical-hardware or
ordinary-family release readiness.
