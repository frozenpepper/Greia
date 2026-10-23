# System updates: current implementation and lightweight completion

**Date:** 2026-10-23
**Scope:** SOURCE REVIEW + focused local tests + public-index HTTP read. Recommendations are proposals, not a replacement implementation plan or new accepted architecture.
**Greia baseline:** `9fe3c9f6e506a855cfa694998703677dba9c6602`, refreshed against `origin/main` (0 ahead / 0 behind).
**HTML client:** inspected the installed pin and fetched remote main `5518a9eed8ba61503249a1c827b7ef4fef5dab36`; local tests ran at older local HEAD `01301d285c6ba2a9a1f2948a9768b821d2536729`.
**Mobile client:** local checkout `4992203726ceda9bf9d85442785d7e99c8967d63`. It has no `origin`; attempts to read a same-named GitHub repository returned 404. Mobile findings are exact local-source findings, not a claim about an independently verified store build.

## 1. Answer

The intended product is already largely the one the owner described: build releases, host files on the owner's server, tell a parent that an update exists, let Greia prepare it, then restart into it with rollback protection. Substantial release, delivery and A/B primitives exist. The ordinary-parent journey is not connected end to end.

Current `legacy-x86-i686` and `legacy-x86-i686-rc` installations are single-root installations, have `boot_backend = "none-v1"`, and omit the `system-update` package set. They cannot perform the planned transactional update. The Parent API deliberately reports activation unavailable. Uploading a bundle does not install it.

The mobile app already discovers updates from a public JSON index, but only offers information and browser links. The live index is reachable and currently advertises zero OS releases. The format transfers a compressed complete system image even for a Python-only change; compression is not incremental delivery.

Recommended direction: finish the existing A/B lifecycle, connect one device-owned background delivery job to the Parent API, retain a static server, and add an optional bandwidth-saving transport for the same complete target release. Keep the installer, updater and rollback under their existing owners.

## 2. Authorities and actual progress

Read against the repository rules, documentation authority map, OS-work router, architecture overview, ADRs 0012–0014/0018–0020/0030/0036, engineering foundations, update product requirements, lifecycle plan, handover and relevant source/test owners.

The decision owners are:

- [ADR 0036](../adr/0036-unified-system-slot-releases-and-platform-install-media.md): one composition engine, one eventual universal Setup image, unsigned v3 complete-slot releases, A/B + PERSIST, streamed writes and interactive boot health.
- [ADR 0030](../adr/0030-platform-owned-transactional-system-updates.md): platform-owned transactional update; existing single-root devices need reinstall/migration.
- [System Updates](../product/SYSTEM_UPDATES.md): preferred device-to-server download after parent authorization; no automatic interruption of child play; optional upload/offline delivery.
- [Lifecycle plan](../plans/2026-09-15_MULTIPLATFORM_RELEASE_INSTALL_UPDATE_COMPLETION.md): execution sequence and completion criteria.

Important chronology: the lifecycle ledger explicitly closes **Session 03 on 2026-09-23**, with a real Linux owner-command release build, and opens **Session 04**. The OS-work router still points to Session 03 acceptance; that continuation pointer is stale. Later successful single-root RC image builds do not close Session 04's A/B install/update/rollback matrix. Pi work remains source foundation with a pre-erase refusal, and universal Setup remains incomplete.

Some older update prose is also stale in the opposite direction: the privileged A/B implementation is no longer simply absent. Production slot seams, boot-health composition and a real launcher call site now exist. Their existence does not make the shipped Parent flow or single-root images update-capable.

## 3. What exists

| Concern | Source owner | Current behavior |
|---|---|---|
| Shared target/live composition | `build/lib/compose.sh`, profile TOML, package sets | One composer with explicit roles; reused by release tools |
| Owner release command | `tools/greia_release.py` | Builds current Acer A/B bundle and release report; default matrix contains only `acer-aspire-one-i386-ab` |
| Real payload production | `tools/build_release.py` | Complete relocatable ext4, fsck/shrink, zstd; source and historical real-build evidence |
| Bundle format and validation | `src/greia_platform/system_updates.py` | v3 ZIP: `manifest.json`, `payload.ext4.zst`, optional `hardware-support.tar.zst`; compatibility, sizes and ordinary corruption checks |
| Update index generation | `tools/build_update_index.py` | Generates/merges `greia-updates/1` entries from `release-report.json` and bundle files |
| Public index | `website/updates/greia-updates.json` | Stable/dev lists empty; same content retrieved from live server |
| Native discovery | Mobile `src/core/update-channel.ts`, `update-logic.ts` | Foreground hook, 12-hour check interval, manual refresh, 10-second fetch timeout, cache and failure backoff |
| Native update screen | Mobile `src/app/(tabs)/greia/updates.tsx` | Version, availability, notes, file size, help/download links; no OS install command |
| HTML client | Pinned `src/api.js`, `src/views_device.js` | Read status, conditionally show `.greiaupdate` upload; no online check/prepare/restart sequence |
| Parent HTTP API | `src/greia_parent/update_api.py`, `protocol.py` | GET status, POST bundle upload; activation hard-coded false |
| Receive staging | `SystemUpdateInbox` | Same-filesystem temporary + fixed candidate, bounded streaming, incoming size + 256 MiB reserve, cleanup after successful staging |
| Privileged coordinator | `SystemUpdateService`, `SystemUpdateServiceAuthority` | Rechecks installed compatibility and orchestrates existing backend |
| Inactive-slot implementation | `SlotBackedSystemUpdateBackend`, `block_slots.py`, `slot_writer.py` | Resolves inactive device from layout; streaming ext4 write, capacity checks, finalization, journal and boot arming |
| Shared hardware finalization | `greia_installer.slots`, `hardware_support_install.py` | Offline verified package pool; candidate hardware support, not network APT |
| Boot acceptance | `boot_health_service.py`, launcher `boot_health.py` and `main.py` | Production post-intro call exists; acceptance is separate from first-frame READY |
| Durable state | `persistent_layout.py` | Declared PERSIST bindings for profiles, settings, Parent state, Wi-Fi, machine identity and update state |

The v3 data model already carries exact profile, architecture, optional board, payload sizes and readable/writable PERSIST schema facts. No release signing keys or anti-tampering infrastructure should be reintroduced.

### Historical size evidence, not a current-release estimate

Session 03's 2026-09-23 artifact at `6c58601e…` recorded:

- complete bundle: **540,126,645 bytes** (about 515 MiB);
- compressed root payload: **383,881,888 bytes**;
- optional hardware-support archive: **156,244,008 bytes**;
- raw shrunk ext4: **1,110,081,536 bytes**.

This is useful evidence that full-bundle delivery can be expensive. It is not a measurement of the current four-language release. The later single-root RC ledger records 1,323 MiB accounted core; its compressed installer payload is a different artifact and must not be equated with an A/B update size.

## 4. The intended parent journey

After a supported A/B installation:

```text
Parent opens System Update
  -> small index check
  -> Greia confirms an applicable release and explains changes/size
  -> parent authorizes preparation
  -> Greia downloads directly from the server
  -> privileged service prepares inactive B while accepted A remains usable
  -> Ready to restart
  -> parent requests restart at a safe child-session boundary
  -> B boots once
  -> interactive Greia health accepts B
  -> Parent reconnects and reads the durable result
```

On the next update, the roles reverse. PERSIST remains outside both system slots. Shared-state migrations must keep the accepted version usable until the trial is accepted. A kernel start or merely reachable Parent API is not the child appliance's health criterion.

A failed userspace candidate can return to the accepted system. A hang before Greia userspace may require a manual reset/power cycle; existing decisions explicitly do not promise automatic recovery from every pre-kernel failure.

For today's single-root RC installs, the honest screen must say that the installation needs migration/reinstall before transactional updates are supported. Do not advertise an A/B bundle as an ordinary in-place upgrade for those devices. Data-preserving conversion needs the explicit recovery/migration work already owned by the lifecycle plan; no automatic repartitioning is proposed here.

## 5. Concrete completion gaps

### 5.1 Parent authorization cannot reach the installed update authority

Only read and upload routes are declared. `system_update_payload()` reads inbox state, not the privileged transaction outcome, and always sets `activation_available = False`. There are no implemented online check/download/prepare/restart routes.

The root socket is mode `0600`, owned by root. The privileged endpoint's default allowed UID is root, and production constructs it with that default. Therefore wiring a button to the socket is insufficient: the unprivileged `greiapanel` daemon cannot access it. Add one narrow authenticated integration path with kernel-attested peer identity. Keep raw device names, slot selection and shell commands out of Parent requests.

Use an asynchronous job: acknowledge authorization promptly and let one bounded, system-owned job finish even if the phone disconnects. Persist its state under the existing update-state owner; allow polling and reconnect. Do not put minutes of network transfer, decompression or finalization inside the Parent request lock. Production currently serializes non-Wi-Fi HTTP requests, including uploads.

The privileged updater is AF_UNIX-only. Internet fetching belongs in an unprivileged delivery component; do not simply give the root slot writer general network access.

### 5.2 Exact updater service limits have drifted behind shared finalization

`greia-system-update.service` retains:

```text
CAP_SYS_ADMIN CAP_SYS_CHROOT
TasksMax=8
RestrictSUIDSGID=yes
```

The installer now has an evidence-derived wider capability set and `TasksMax=64`. Its unit comments document real failures in APT identity/ownership operations, setgid file handling and `mkinitramfs` process creation. The updater delegates into the same `TargetHardwareSupportInstaller` chroot/APT path through `_LazyTargetPackageInstaller`.

This is a concrete **source integration risk**, not a freshly reproduced updater failure. Existing tests explicitly pin the older two-capability contract and can pass while this remains unresolved. Before enablement, execute the exact installed update unit against disposable A/B media with a release that actually selects hardware packages and runs the relevant package hooks. Derive required permissions/task bounds from that path; do not copy every installer permission blindly, since some installer operations are not update operations.

### 5.3 Discovery currently advertises compatibility too loosely

In the local mobile `findSystemUpdate()`, exact profile lookup falls back to platform family + architecture. `parseRelease()` discards `board` entirely. Reproduction using actual current Pi profile identities:

```text
device: raspberry-pi-400-arm64 / arm64 / arm64
only index release: raspberry-pi-500-arm64 / arm64 / arm64 / pi-500-v1
advertised: raspberry-pi-500-arm64
```

The privileged updater would refuse the mismatch, but the parent should never be offered it as installable. A single-root legacy profile can similarly be pointed toward the incompatible Acer A/B profile through the fallback.

Keep browsing/help suggestions distinct from installable releases. Device-side selection must require the exact declared compatible profile, matching board where required, supported layout/backend, PERSIST readability and capacity. Let the device resolve a release ID from its configured channel rather than treating a phone-provided arbitrary URL as a destination command.

The local RC profile also selects `stable`, since its name is `legacy-x86-i686-rc`, not `-dev`. Make channel intent explicit in device release metadata rather than relying only on name heuristics.

### 5.4 Mobile offline index cache loses OS entries

The fetch path saves the **parsed** index, which has top-level `channels`. `loadCached()` passes it back into `parseIndex()`, which expects wire-format `greia_os.channels`. It silently replaces the saved OS release lists with empty lists.

Reproduction: a parsed index with one stable release becomes zero stable releases after `parseIndex(parsedIndex)`. This affects discovery after app restart/offline use. Save the wire representation or validate the cached representation with its own consistent path; add the restart round-trip regression.

### 5.5 Reporting, release identity and documentation need alignment

Parent `health.installed_os_identity()` reads `build-info` plus `image-profile.json`; the updater prefers finalized `release-identity.json` plus layout authority. Parent identity omits board and release ID. Use the finalized release owner for A/B device reporting and explicit build metadata fallback for current single-root devices.

Both composer and Parent reader still use `PIP_*` build-info fields, so this naming debt is **not currently a producer/consumer mismatch**. It should not be reported as a demonstrated discovery failure.

HTTPS Parent transport is newly implemented and has its own pending device/client acceptance. Upload enablement still follows an explicit environment override/developer marker; HTTPS alone does not currently enable it. Complete that existing transport acceptance with the update integration.

The index generator accumulates historical releases indefinitely and currently accepts only EN/IT note-file flags. Keep the public feed bounded and add ES/FR notes through the same generator when shipping the four-language update experience. `release-report.status = complete` means artifact production completed, not that a device lifecycle or universal Setup image was certified.

## 6. Lightweight architecture

Separate four costs: transferred bytes, device RAM/CPU, temporary disk space, and implementation/operating complexity. A small download is not automatically cheap to apply.

### 6.1 Keep one complete release and A/B activation

A complete target release is valuable even when only Python changed: it defines a coherent OS/runtime/assets/Parent-client set, offers direct recovery from an arbitrary old version, and keeps rollback simple. Python, activities, locale data and artwork can change together. Native dependencies and the interpreter remain architecture-specific even if Python source is shared.

Patching the running `/opt/greia-os` tree would introduce partial-update failures, mixed imported code, cache and service-restart problems, and a second rollback mechanism. Independently updating already supported optional Activity packages remains the existing Activity package service's responsibility; it is not a substitute for OS updates.

### 6.2 First functional delivery: existing full v3 bundle

Use the existing streamed full-bundle path to prove the whole transaction. It already avoids a second full uncompressed image in PERSIST and limits the candidate to one compressed bundle. Preserve preflights for support extraction and final slot growth in addition to the 256 MiB receive reserve.

This is the simplest correctness baseline. It does **not** satisfy a promise that routine Python updates are small. Keep that performance work explicit before describing update delivery as lightweight.

### 6.3 Preferred optimization to evaluate: reuse existing content during transfer

The promising direction is an optional adaptive/chunked delivery representation of the **same complete target image**: read reusable content locally, download missing compressed chunks, and emit the complete candidate image to the inactive-slot writer. Continue through the existing filesystem checks, finalizer, journal, boot and health owners. Always retain a complete v3 fallback for USB/offline recovery and devices without suitable reusable data.

This is a **proposal requiring a documented format/service extension**, not something today's monolithic `payload.ext4.zst` supports by configuration. Do not pretend a chunk stream is an inspected v3 ZIP member or fabricate its manifest facts.

Existing mechanisms worth a bounded comparison:

- [casync](https://github.com/systemd/casync): content-defined chunking, HTTP-hosted chunk stores and local seeds; can reconstruct images or trees.
- [RAUC adaptive updates](https://rauc.readthedocs.io/en/latest/advanced.html#adaptive-updates): an established example of reusing local image blocks while retaining a full logical release. Study the transport mechanism; replacing Greia's lifecycle with RAUC is not recommended here.
- A file-aware delta applied to a locally prepared inactive candidate: a comparison candidate if raw ext4 rebuilds churn too many blocks. It must handle deleted files, modes, links, version compatibility and source consistency without copying PERSIST mounts or arbitrary live-root mutations. This has more filesystem semantics to implement and is not the default recommendation.

Raw installed slots differ from the builder image after UUID binding, filesystem expansion, hardware finalization and runtime writes. A delta cannot assume that release version alone makes a slot byte-identical to the original builder artifact. Adaptive reuse must check each reused piece as a corruption/staleness check and fetch a replacement when it does not match. Reading from the slot being overwritten also needs explicit ordering; initially use the accepted slot as the read-only seed. Keep buffers/cache/index sizes bounded and never require a retained full old image.

Ordinary SHA checks for reuse/corruption do not add signing, provenance or local anti-tampering policy.

[Zstd patch mode](https://raw.githubusercontent.com/facebook/zstd/dev/programs/zstd.1.md) is not an automatic whole-OS solution: it uses the old file as a dictionary, increases window requirements and has explicit memory limits. A large reference image plus decoding window is a poor unmeasured assumption for the Acer floor. It also needs the correct base bytes, which current finalized slots do not preserve unchanged. Chunk/per-file use could be benchmarked, but do not adopt a whole-image `--patch-from` command on the strength of a small-file demo.

Before choosing a transport, measure two real adjacent current releases: Python-only change, one Activity change, audio/art change, and kernel/runtime change. Measure full compressed size, missing/reused bytes, wire requests, peak RSS, temporary storage, CPU time, local reads/writes and total preparation time on the Acer. Include a stale/locally edited base and an interrupted download. Use the complete bundle when the incremental path is bigger or cannot reuse data safely. No reduction percentage is claimed by this review.

## 7. Build and hosting pipeline

The existing owner command remains the front door:

```bash
sudo python3 tools/greia_release.py build --version <VERSION> --output <DIR>
```

It requires the repository `VERSION` to match. Today its default output matrix is Acer-only and explicitly marks universal Setup deferred. Extend that implementation as the other planned adapters become real; do not write a second image pipeline.

For ongoing development, use the selected Linux build host/manual owner invocation. No GitHub-hosted Actions are required or authorized by this review. Existing package caches can reduce build work; do not skip composition/compatibility checks merely because a source diff looks Python-only.

The server can remain:

```text
/greia/updates/greia-updates.json
/greia/updates/<version>/<profile>.greiaupdate
/greia/updates/<version>/... optional future chunk indices/content
/greia/downloads/... accepted Setup image
```

Use the existing `tools/build_update_index.py` and shared `site-ftp` tool (registered project `greia`) for publication. No new deployment service is needed. Build/test first; upload immutable versioned artifacts first; verify public size/availability; atomically publish the small index last. That ordering prevents an app discovering a release whose upload is incomplete. Retain enough previous accepted artifacts/content for rollback, fallback downloads and supported old devices.

Serve bundles over HTTPS with immutable caching; keep the small index on a short cache lifetime. Before promising resumable/chunk-range downloads, verify the actual host's relevant HTTP behavior. The current live-index check proves index availability only, not bundle bandwidth, range support or CDN performance.

The phone and Greia may fetch the same small index, but the device owns eligibility and installation. The phone should not relay a large release in the normal online path. No cloud account, per-device server database, telemetry service or always-running heavyweight agent is necessary.

## 8. Recommended continuation inside the existing plan

These are review recommendations mapped to the authoritative sessions, not a new execution authority:

1. **Session 04/common lifecycle:** prove current complete-release capacity, fresh A-only installation, accepted first boot, update to B, then a subsequent update back to A, failed health and interrupted writes. Reconcile the exact updater sandbox with real finalization. Preserve the accepted Syslinux removable boot path separately from installed GRUB A/B. Current single-root physical usability is not this proof.
2. **Existing platform sessions:** continue amd64/UEFI, ARM/Pi and universal Setup work under Sessions 05–11 and their hardware closure requirements. No universal-support claim follows from finishing Acer updates.
3. **Session 12 integration:** connect the existing Parent surfaces to device-owned check/prepare/status/restart/result operations, a narrow privileged bridge and one serialized update job. Correct local mobile matching/cache/channel issues and align identity/status. Finish manual upload through the same engine, then device-side online delivery; keep optional offline delivery on that engine.
4. **Delivery efficiency:** perform the bounded real-release benchmark and extend the same release transport if results support it. Online delivery is already an accepted requirement; the current Session 12 list emphasizes upload and needs an explicit online-download/efficiency addition when implementation is commissioned.
5. **Existing final acceptance:** prove interrupted receive/stage, invalid/wrong-board/oversized/schema-incompatible candidates, reboot recovery, backward-readable child data and Parent reconnection. Test the actual service units and real firmware, not just helper methods. Then publish only the proven device scope.

Useful acceptance includes the browser being closed after authorization, Parent daemon restart, double-submitted requests, exhausted PERSIST during transfer, edits to local reusable content, an offline reboot, and two successive accepted updates. Those cases expose job ownership, durable results and alternating-slot bugs that a single successful update misses.

## 9. Verification performed and limits

At the Greia baseline, Python 3.12.7, with bytecode writes disabled and `PYTHONPATH=src:tools:tests`:

```text
test_build_update_index, test_update_v3_bundle,
test_system_update_streaming, test_parent_system_updates,
test_update_product_composition, test_update_activation_contract,
test_update_unit_contract
    60 tests, OK

test_system_update_service, test_system_update_service_orchestration,
test_update_seam_composition, test_slot_writer,
test_installer_product_composition, test_boot_health_product_composition,
test_boot_health_recovery_product, test_greia_release,
test_parent_activity_titles_and_os_identity
    141 tests, OK (1 skipped)
```

An initial `tests.test_*` module invocation failed collection (this checkout does not expose those tests as that package). The corrected module invocation above is the executed result; the collection failure is not counted as passed tests.

Mobile local source: `node --test tests/update-logic.test.ts`, **10/10 PASS**. Separate direct calls reproduced cross-board advertising, cache entry loss and RC-to-stable selection; the existing tests do not cover those regressions. HTML local source: `node --test tests/system_update_api.test.js`, **3/3 PASS**; inspected the current installed pin separately. Its update API methods are unchanged; the constructor's default transport is now HTTPS and the UI is localized.

Live HTTP GET of `https://www.frozenpepper.it/greia/updates/greia-updates.json` succeeded and returned `stable: []`, `dev: []`, `updated_at: 2026-10-16T05:22:45+00:00`.

No implementation code changed. No full `make verify`, release/image build, privileged service run, mount, disk write, QEMU boot, physical-device operation, firmware trial, hosted Actions operation or server publication was performed. These source checks do not certify install/update/rollback, HTTPS client acceptance or device resource cost.
