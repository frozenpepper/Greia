# Update systems and first public image — detailed situation report

Date: 2026-10-28
Status: **installed Linux/QEMU update acceptance PASS; public release still BLOCKED**
Tested production tree: `810caa91f363a5eb39676f68862a8bef276a6998`
(rebased production commits `72d1ccbd0`, `885f15029`, `999a1ab0f`,
`fcf619bdf`, `d21fcc8fb`; equivalent to current `main`)
Current `main` before this report commit: `7485c5fc4`
Concise acceptance record:
[`2026-10-27_UPDATE_RELEASE_ACCEPTANCE_RESULT.md`](2026-10-27_UPDATE_RELEASE_ACCEPTANCE_RESULT.md)
Execution authority:
[`GREIA_UPDATE_RELEASE_ACCEPTANCE.md`](../testing/GREIA_UPDATE_RELEASE_ACCEPTANCE.md)

## 1. Executive summary

Both of Greia's update mechanisms now work on a real installed system.

The full-system A/B route installs a fresh disposable i386 image, boots slot A,
stages a genuinely newer release into slot B, arms the one-shot boot, boots B,
accepts B only after health confirmation, rolls a deliberately unhealthy
candidate back to A, and recovers from a simulated power cut during the
inactive-slot write. The lightweight `.greia_update` route applies Python,
built-in Activity and combined packages through the installed Parent HTTPS API,
keeps processing after the upload client disconnects, preserves real profiles,
save data and settings, preserves EN/IT/ES/FR, and restores the previous
application generation after a broken Python package.

A fresh installer candidate was built from current `main` and stored at
`/home/orb/Greia-Images/2026-10-28-first-public-candidate/`. This exact image
passes install and first healthy boot A in QEMU. It is **not yet
release-eligible**: the normal release build still refuses because the
`greia-early-framebuffer-v1` boot cover has not passed its release-safety
acceptance gate. The supplied image therefore uses the explicit experimental
A/B acceptance-fixture route. It is a strong first-public-image candidate, not
an approved public release.

The attached USB key has **not** been updated. It still contains a
2026-10-22 `legacy-x86-i686-rc` live image with a single-root layout, which
predates every fix in this tranche.

## 2. Starting problem

A previous installed i386 test could not stage an A/B update:

```text
STAGE_CURRENT_CANDIDATE -> ERROR / REFUSED
inactive-slot filesystem is unavailable: block topology observation failed:
slot device capacity is unobservable: sda2
```

The first source path was `_block_node_size_bytes` in
`src/greia_platform/system_updates.py`. It used the x86_64 `BLKGETSIZE64`
request encoding and then `blockdev --getsize64`. On a 32-bit guest the first
request could be wrong, and the minimized image could lack or deny `blockdev`.
The captured error could not distinguish those causes.

The owner authorized a consolidated repair-and-acceptance session: fix current
source, use disposable images only, and do not preserve compatibility with
unreleased development snapshots. Rollback and interrupted-update recovery are
required product behavior; migration from old development images is not.

## 3. Production fixes delivered

### 3.1 Architecture-correct block capacity

Commit `72d1ccbd0` (`fix(update): observe block capacity on i386 and x86_64`).

`_block_node_size_bytes` now:

- tries the native `BLKGETSIZE64` request first (`0x80041272` on i386,
  `0x80081272` on x86_64) and the alternate encoding second;
- validates a positive, bounded byte count;
- falls back to the bounded read-only sysfs sector count
  `/sys/class/block/<validated-name>/size`;
- keeps `blockdev` as a last resort;
- reports the concrete failure from each method instead of only
  "capacity is unobservable";
- still checks the observed slot capacity against the installed layout and
  refuses a mismatch.

Focused tests cover both encodings, ioctl success/failure, sysfs success and
malformed/missing values, missing/failing `blockdev`, bounds, device-name
traversal refusal and mismatched capacities.

### 3.2 Staged slots now publish bootable kernel/initramfs names

Commit `885f15029` (`fix(update): publish inactive-slot boot aliases through
the finalizer wrapper`).

The GRUB A/B entries boot `boot/vmlinuz-greia` and
`boot/initramfs-greia.img`. The finalizer supports that alias publication
through a `link_file` seam, but the production `_MountTrackingFilesystem`
wrapper did not expose it. A staged B therefore contained
`boot/finalized-generic.json` and no aliases, and could not boot.

The wrapper now delegates `link_file`. A regression test asserts that the
production wrapper exposes the full finalizer filesystem seam and delegates
the hardlink operation.

### 3.3 Check/expand before binding the role filesystem UUID

Commit `999a1ab0f` (`fix(update): check staged filesystems before UUID binding
and repair recovery harness transport`).

A packaged payload can carry an ext4 journal that needs replay. `tune2fs -U`
then refuses with:

```text
This operation requires a freshly checked filesystem.
```

The finalizer now runs `expand_to_capacity()` (which includes `e2fsck -f -y`
and `resize2fs`) before `bind_filesystem_uuid()`. Expansion does not consume
the role UUID; the subsequent mount still verifies the bound identity. A
regression test pins the order: expand/check → bind → mount.

Filesystem-command diagnostics also now include bounded stdout when stderr is
empty, because `tune2fs` reports this refusal on stdout. This is what made the
silent failure diagnosable.

### 3.4 Candidate health-deadline rollback is actually enabled

Commit `fcf619bdf` (`fix(update): enable candidate health-deadline rollback
timer in A/B images`).

`greia-candidate-recovery.timer` existed but was not enabled in target image
composition. A candidate that booted but never became healthy therefore stayed
on B indefinitely; the 3-minute deadline never ran.

A/B image composition now enables the timer, and
`build/lib/verify-composed-root.sh` requires the enablement symlink. The timer
unit marks an unhealthy candidate `FAILED` and reboots to the accepted slot
without moving the persistent default.

### 3.5 Application generations work on A/B images

Commit `d21fcc8fb` (`fix(update): support A/B root identity and serialize
terminal candidate cleanup`).

The stable bootstrap previously required
`/etc/greia-os/root-filesystem-uuid`, which only single-root build images carry.
On an A/B image every application package failed with
`installed root filesystem identity is unavailable`.

The bootstrap now falls back to:

1. reading the installed layout record;
2. parsing `root=PARTUUID=` from `/proc/cmdline`;
3. matching that PARTUUID to the booted `system_a`/`system_b` identity;
4. using that slot's filesystem UUID.

This binds a candidate B boot to B even while the accepted slot is still A, so
a stale application journal cannot be replayed onto the wrong root. Single-root
images continue to use the existing root-filesystem-uuid file.

### 3.6 Fast follow-up uploads are no longer deleted by the previous job

Same commit `d21fcc8fb`.

A terminal job state and candidate cleanup were separate job-lock
transactions. A combined package uploaded immediately after an Activity job
reached `applied` could be deleted by the old worker's late cleanup, producing:

```text
package_invalid: accepted software-update package is missing
```

Terminal job publication now:

- verifies the expected job ID;
- writes the terminal state;
- removes the candidate and pending marker;
- all under the same job lock.

A new upload cannot publish between those steps, and a stale worker cannot
mark or delete a newer job. Regression tests cover expected-job-ID refusal and
same-lock candidate cleanup.

## 4. Test-harness corrections

These are test-only fixes; they do not change production behavior.

- Failure legs stage the candidate onto the control disk before
  `update-verify`, not only at `update-stage`.
- Control-disk size is derived from the actual v3 bundle plus a bounded margin;
  a 64 MiB control disk cannot carry a ~700 MiB candidate.
- A-start rollback reports use an A-start shape instead of the frozen
  B-start Session 04 report.
- Post-recovery observation accepts the terminal `failed` journal and the
  recovered accepted slot, since the harness observes after the recovery boot.
- The guest health wait treats `accepted`, `failed` and `rolled_back` as settled
  states after recovery.

## 5. Installed A/B acceptance

Evidence root:
`/var/tmp/greia-update-acceptance-810caa91f363a5eb39676f68862a8bef276a6998-20261027T204906Z/`

Artifacts:

| Artifact | SHA-256 | Bytes |
|---|---|---|
| Base A/B bundle `greia-acceptance-fixture-0.13.0-phase0-dev` | `322c70744ee92cbb660dc3f28b718836c2b20b15d49bbc573d4fcb97fd971eeb` | 714,362,489 |
| Installer `acer-aspire-one-i386-ab` | `812f13ce8d84dd746f3551a6cd097e9582c3954207059c364ce6f049e284467d` | 2,270,167,040 |
| Next bundle `greia-acceptance-fixture-0.13.1-phase0-dev` | `467178951fcd3e1e462205c8f5a416d3e51c24b92431dcc934e83b66d038cc25` | 714,357,272 |
| Unhealthy candidate `greia-acceptance-unhealthy-0.13.2-phase0-dev` | `d07904d8bb395b9df597f5e8ff866c9b518c3d999c32e10421aba2cf3af8247f` | 794,131,238 |

Results:

| Scenario | Result | Key evidence |
|---|---|---|
| Fresh A/B installation | PASS | `vm/install/result.json`; shipped installer phases, valid MBR/PARTUUIDs, PERSIST schema 1 |
| First healthy boot A | PASS | accepted base release, default/last-booted A, journal `accepted`, unbooted B unchanged |
| Stage update into B | PASS | `STATUS → VERIFY → STAGE → STAGED`; B release identity is the next fixture |
| Activate update | PASS | `ARM_CURRENT_CANDIDATE → ARMED`; one-shot consumed |
| Healthy boot B | PASS | default/last-booted B, accepted next release, journal `accepted`, layout authority B |
| Failed B update rollback | PASS | deadline note `recovery:health-service-failure:automatic-reboot`; return to accepted A |
| Interrupted update recovery | PASS | QEMU killed 25 s into a real inactive-slot write; A remained accepted, default and bootable |

The rollback evidence is important: the unhealthy candidate did not merely time
out. The production timer observed the candidate boot, recorded the recovery
reason, rebooted, and left the accepted slot and release unchanged.
The interrupted-write evidence is also not a clean poweroff: QEMU was killed
mid-write, then the same clone was cold-booted and returned to accepted A.

## 6. Installed application-update acceptance

Final profile run evidence:
`vm/app-updates/packages.img:evidence/` and
`vm/app-updates/parent-target4.img` in the same evidence root.

Packages:

| Package | SHA-256 | Bytes |
|---|---|---|
| `python.greia_update` | `ba32bf633b6a5a0d4bdfb83a99f89677f2fdb692bf9ccd447772a986a26b2c4c` | 1,325,204 |
| `activity.greia_update` | `80450e3f4409143cf0b23afbfaba204f80df17efb682308840f0a45467aecbc7` | 230,370 |
| `combined.greia_update` | `5eda0e82abd733a70721a921e03129383de085d8bd86aff5d2c168f98156704a` | 1,555,354 |
| `broken.greia_update` | `07ee09b1c41c1e4790ca3bcf9bc907c7dce3fab2c6960249f997d318bf00ad26` | 1,324,955 |

The disposable guest was booted from the accepted A image. The installed Parent
HTTPS service was paired through the real bootstrap endpoint using the main
Parent password, then packages were uploaded to
`/api/v1/system/update/package` with the issued bearer credential. The guest
serial console used a test-only root password; no production helper or
application source was hand-patched on this clone.

Each upload returned HTTP `202`. The client then waited 20 seconds without
polling before checking status, modelling a Parent app/client disconnect.

| Scenario | Result | Key facts |
|---|---|---|
| Python application update | PASS | job `186e131e...` reached `applied`; new generation contains `acceptance_canary.py`; Activity stays `0.1.0` |
| Activity update | PASS | job `985d07cc...` reached `applied`; writing Activity version `0.1.1-acceptance`, Activity canary present, 45 registrations retained |
| Combined update | PASS | job `33c72183...` reached `applied`; Python and Activity canaries both present under one generation |
| Parent disconnect continuation | PASS | 20 s no-poll window after `202`; all jobs still reached terminal state |
| Failed application update | PASS | broken job `82575d30...` reached `rolled_back`, `launcher_not_ready`; previous combined generation restored |
| EN/IT/ES/FR preservation | PASS | paired `manifest.json`/`ui.json` present in every updated generation |
| Profile/save/settings preservation | PASS | real profile `Acceptance` (`1c30aeb2...`) created through Parent API; registry, save marker, settings and existing `Explorer` profile intact after every update and rollback |

The activity index still has 45 registrations after the Activity and combined
updates. The `org.greia.writing` entry is `0.1.1-acceptance`; the package named
only that Activity.

## 7. Verification

At `810caa91f` (production tree now identical in current `main`):

- Focused update/lifecycle suites: **353 tests PASS**
  (`focused-update-tests.log`).
- `make verify`: **6,009 tests, 7 failures, 3 errors, 3 skips; NOT GREEN**
  (`make-verify.log`, exit 2).

The failures/errors match the documented Linux baseline and are unrelated to
this work:

- Foresta content/review-state assertions: 3 failures;
- Parent Wi-Fi source assertions: 2 failures;
- MBR message wording: 1 failure;
- `morbidi_mostriciattoli` first-frame timing: 1 failure;
- ARM64 profile build error: 1 error;
- optional voice modules `huggingface_hub` and `mlx_audio`: 2 errors.

No capacity, finalizer, bootstrap, job-store, generation, Parent delivery or
update-harness test failed. The full gate is still not green and must not be
reported as green.

## 8. First-public-image candidate

The normal release build was attempted first from current `main`. It refused:

```text
Release build refused: ERROR: boot cover 'greia-early-framebuffer-v1' is not
registered as release-safe; a noninteractive branded-only backend must pass its
acceptance gate first
```

The image was therefore built with the explicit experimental A/B
acceptance-fixture route and a matching installer, from source
`7485c5fc4` (the current main; production tree equal to the tested
`810caa91f` tree; later changes are licensing/trademark documentation only).

Stored at:

```text
/home/orb/Greia-Images/2026-10-28-first-public-candidate/
```

| File | SHA-256 | Notes |
|---|---|---|
| `greia-os-installer-acer-aspire-one-i386-ab.img` | `46c30f62ca91f9c6638ee3e7748bde7a23cadd28f3b66e1d72c0b819df6bb400` | 2,270,167,040 bytes; hybrid BIOS/EFI raw installer |
| `acer-aspire-one-i386-ab.greiaupdate` | `f9b17e397d7c621ad97fe76b5aa5fc38c1e88ab84ed452466e1ac1c659c47178` | matching base A/B bundle |
| `fixture-release-report.json` | `de2d2435b6027baae7bf2a5d76925797ed3dfc903f6c1fe0488b281daf4cd234` | `release_eligible: false` |

This exact installer was validated with a disposable QEMU install:

- install PASS;
- first healthy boot A PASS;
- accepted release `greia-acceptance-fixture-0.13.0-phase0-dev`;
- default/last-booted A, journal `accepted`.

The full installed update matrix was run on the equivalent production tree at
`810caa91f`, not on this newly built same-source image. The candidate README
records this boundary.

The candidate is **not** an approved first public release. It is the best
current functional candidate and contains all update fixes. Public release
still needs:

- an accepted release-safe boot-cover backend or an owner decision on that
  gate;
- physical Acer installation, boot, update and rollback evidence;
- ordinary-family release approval.

## 9. Attached USB key

The attached key is `/dev/sdc` (LaCie iamaKey, 7.5 GB, label `GREIA`). It was
**not** written in this session. Its files are dated 2026-10-22 and its
`target-image-profile.json` identifies:

- profile `legacy-x86-i686-rc`;
- single-root `bios-single-ext4`;
- boot backend `none-v1`;
- `updates.required: false`.

It predates every update fix in this tranche and is not the new A/B image. It
must not be described as current or public-release ready. Flashing
`/dev/sdc` with the new candidate would erase the key and requires explicit
operator confirmation.

## 10. Remaining risks and untested scenarios

- **Physical hardware:** no Acer/USB install, boot, update, rollback or
  power-cut evidence. QEMU success is not physical acceptance.
- **Browser clients:** the installed Parent HTTPS API was used directly with
  real pairing/bearer authentication. The HTML/Mobile upload button and UI
  states were not clicked through.
- **Reverse B→A full-system update:** not run.
- **`full_system` `.greia_update` wrapper:** not run.
- **HTTP 507 low-space:** not run.
- **Mobile client:** not run.
- **Public release eligibility:** blocked by the boot-cover gate and physical
  acceptance.
- **Candidate version string:** current `VERSION` is
  `0.13.0-phase0-dev`; the release identity is still experimental.

## 11. Recommended next actions

1. Decide the boot-cover release-safety route or explicitly accept the current
   cover for a first public candidate; do not silently bypass
   `check-release`.
2. Flash the stored candidate to the authorized 8 GB key only after operator
   confirmation, then run a physical Acer install/first-boot/update/rollback
   acceptance.
3. Run the HTML Parent client upload path and one Mobile upload against an
   installed guest.
4. Add reverse B→A, `full_system` wrapper and low-space 507 coverage.
5. Keep the public release label separate from QEMU acceptance until physical
   and boot-cover gates close.

## 12. Evidence index

| Item | Path |
|---|---|
| A/B + app acceptance evidence | `/var/tmp/greia-update-acceptance-810caa91f363a5eb39676f68862a8bef276a6998-20261027T204906Z/` |
| Evidence summary | same directory, `RESULT.md` |
| Full-gate log | same directory, `make-verify.log` |
| Focused suite log | same directory, `focused-update-tests.log` |
| A/B result JSONs | same directory, `vm/install|first-boot|healthy-update|rollback|interrupted-stage/result.json` |
| Application evidence | same directory, `vm/app-updates/packages.img:evidence/` |
| Candidate installer | `/home/orb/Greia-Images/2026-10-28-first-public-candidate/` |
| Concise acceptance report | [`2026-10-27_UPDATE_RELEASE_ACCEPTANCE_RESULT.md`](2026-10-27_UPDATE_RELEASE_ACCEPTANCE_RESULT.md) |

This report records the situation at the stated source and evidence boundary.
It does not replace physical acceptance or an owner release decision.
