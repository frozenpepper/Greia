# T6-HARNESS3 Lifecycle Procedure — Disposable A/B Lifecycle on Device/QEMU

Executable end-to-end lifecycle harness (`tools/x8_qemu/lifecycle.py`;
contract in `tests/test_x8_qemu/test_lifecycle.py`). Supersedes the frozen
7-step source-only X8 sequence (kept intact in `runner.py`) without
redesigning it.

## 1. Sequence (8 steps, fixed order)

`fresh-install-A` → `boot-A-accepted` → `stage-B-one-shot` →
`boot-B-commit` → `stage-broken-candidate` → `boot-broken-candidate` →
`recovery-boot-B` → `reverse-update-B-to-A`.

Frozen T7-ATTEST leg definition (verbatim): the 8-step lifecycle
comprises 3 non-boot transitions (`fresh-install-A`,
`stage-B-one-shot`, `stage-broken-candidate`) and 5 boot-outcome legs
(`boot-A-accepted`, `boot-B-commit`, `boot-broken-candidate`,
`recovery-boot-B`, `reverse-update-B-to-A`); every transition records
per-transition evidence (default/one-shot/last-booted, journal,
accepted slot/release/sequence, PERSIST marker, release hashes, image
SHA), but only the 5 boot-outcome legs assert a guest-observed boot
outcome through the frozen seam (grubenv-on-image with post-boot loop
remount/read via `GrubEnvBackend.attach(mountpoint).inspect()`;
consumption predicate: `next_entry` absent AND `last_booted ==
expected`). Expected slots: A, B, A, B, A respectively.

Release lineage: `greia-0.20.0`/20 (A) → `greia-0.21.0`/21 (B) →
`greia-0.21.1`/22 (broken B→A candidate, validly signed, controlled
post-boot failure) → `greia-0.22.0`/23 (A).

## 2. Shipped update path (successful-update legs)

Stage/arm/reboot/commit traverse the shipped
`build_live_update_service` constructor path including the production
boot-backend attach, entered through the shipped socket endpoint
(`UpdatePrivilegedEndpoint` + kernel-attested `PeerCredential`).
Production destination-device factories arrive as explicit
image-integration parameters (`ImageIntegrationSeams`) through that
shipped path — the backend is never constructed directly around the
authority. Default construction without destination seams stages
fail-closed (`UpdateBackendUnavailable`, no journal, no default move,
no single-root routing).

## 3. Launcher acceptance (boot legs)

Every boot leg publishes one prepared state through the real
`LauncherApplication.apply_prepared_state` →
`maybe_accept_production_boot` → `run_post_intro_acceptance` production
seam with the production observer/vault/journal/layout bindings. The
persistent default stays on the previous slot until the health commit.
The recovery boot (accepted slot, terminal FAILED journal) is a bounded
no-op: no acceptance, reconcile stays with the privileged service.

## 4. Broken candidate + recovery

The broken candidate boots (observed on the candidate slot, journal
`CANDIDATE_BOOTING`), health never confirms, and the real
`mark_candidate_unhealthy` trigger records `FAILED` without mutating the
persistent default. PERSIST markers must be byte-identical across the
failure and the recovery boot.

## 5. Observations and the `ok` flag

After each transition the harness observes: semantic slot/release,
layout record, GRUB env/default/one-shot, journal, accepted sequence,
PERSIST markers, release hashes, image SHA, boot outcome. `ok` derives
from those assertions; `assert_lifecycle_transitions` fails the harness's
own contract on out-of-order, movement-free, or leg-bypassed reports.

## 6. On-device identity observation

Loop-attach the file-backed DOS image, force a bounded kernel
partition rescan first (`partprobe` and/or `partx -u` for whichever
tool exists, then `udevadm settle`), and run the production
observation path (`read_mbr_disk_signature`,
`probe_mbr_partition_partuuid`, `probe_partition_filesystem_uuid` via
`SubprocessMbrProbeRunner`) with bounded settle/sleep retries so a
stale kernel partition view settles instead of REDing permanently;
exhausted retries fail closed at the
`post-run-loop-attach-partition-rescan` gate naming the device, the
rescan detail and the last probe error. Assert the bound record equals
the observed topology. The `sfdisk`/`blkid -p` file cross-check executes (not
skipped) on capable hosts and reports explicit deferred elsewhere —
never false green. Record teardown/remount/reload semantics hold.

## 7. Fake boundary and scope

Recording/sparse fakes only at the block-driver seam (sparse
`LoopbackSlotFile` stores, scripted `MbrProbeRunner` answers where no
device exists). No stubbed health, no stubbed launcher acceptance, no
fabricated slot/journal/GRUB state, no `simulate_reboot`.

Source scope (`run_source_scope`) drives the same seams with declared
boot outcomes folded through the real backend + journal reconcile;
device scope (`run_device`, capable Linux host only) gates on the
payload + gap + boot-chain gate, installs the payload to partition 1,
pushes each armed block to the image, boots each boot-outcome leg once
under real SeaBIOS firmware with a progress-aware bounded wait (COM1
serial-byte growth and image SHA delta count as progress with the leg
timeout as the hard ceiling; silence and progress-then-stall are RED)
and a clean-exit gate, derives the observed slot solely from on-image
pre/post consumption evidence, stamps it through the production
`reconcile` on the real on-image bytes, gates it with
`read_attestation_signal` through the post-boot loop remount/read path,
and only then folds it into the host backend, the journal coordinator
and the launcher seam (with the guest-observed boot identity). Post-run loop/cross-check binding is enforced
executed-and-green. Device execution stays RED/deferred off capable
hosts — never claimed from source evidence. There is no `on_boot`
hook: stubbed-spawn runs are source scope and explicitly non-proxying
for the live predicate.

## 8. Sector 1-2047 gap coordination (guest boot core + relocated descriptor)

Sectors 1–2047 of the disposable image are RESERVED under the
GUEST-BOOT-CHAIN layout:

- sector 0: MBR — 440 bytes of guest boot stub code (COM1 progress +
  single EDD LBA core load + bounded reboot exit) owned by
  `tools/x8_qemu/bootchain.py`, then the disk signature + DOS partition
  table owned by `write_mbr_table_for_plan` (the chain installer
  preserves bytes 440–511 and re-proves the table through the
  production parse seam). The single call (not a CHS call, not a loop:
  repeated EDD calls silently repeat the first transfer on this
  target) loads sectors 1..N and preserves DL for the core entry; a
  disk error or a missing EDD BIOS takes the bounded reboot exit;
- sectors 1–127: the guest boot core reservation. Source scope installs
  the reviewed stub core (sectors 1–15, zero-padded image of
  `stub_core_bytes()`); a capable host replaces it at assembly time
  via `maybe_install_genuine_grub_core` (`assemble_disposable_image`)
  with a genuine GRUB `core.img` through `install_genuine_grub_chain`
  (matching MBR load count derived from the core length + zeroed
  reservation tail), with the sector-2047 binding replaced through the
  explicit `rebind_payload_descriptor` path (previous binding evidenced,
  never silently overwritten; off a capable host the stub stays and
  armed-leg consumption stays RED). Split-core architecture (Acer-measured):
  `normal.mod` alone exceeds the reservation, so the embedded core is
  the minimal disk-reaching set (serial + loadenv + reboot/halt +
  terminal + biosdisk + part_msdos + ext2 + test + echo, plus an
  embedded early serial config) while `normal`, the `password_pbkdf2`
  stack, and their dependency closure load from `/i386-pc/` on
  partition 1 at boot (normal-mode auto-insmod resolves them there).
  The mkimage prefix is `(,msdos1)/`, so genuine GRUB consumes the
  partition-ROOT `grub.cfg`/`grubenv` — the exact paths the frozen
  attestation seam inspects, with no mirror copy to drift;
- sectors 128–2046: must read zero;
- sector 2047: the T7-PAYLOAD descriptor (magic `GREIAPY1`, version 2),
  relocated here from sector 1 by the GUEST-BOOT-CHAIN migration, now
  binding the installed core bytes (`core_sha256` + `core_sectors`) next
  to the staged payload hashes.

The guard (`verify_sector_gap_reserved` + `verify_boot_chain_present`,
both enforced by `device_gate_for_image` before any QEMU boot) proves
the descriptor field-by-field, re-hashes sectors 1–N against the bound
`core_sha256`, and refuses any foreign/non-zero byte elsewhere in the
gap. An old-layout image (descriptor still at sector 1, zero MBR boot
code) REDs this guard: the relocation omission is itself a RED
condition, pinned by test. Silently clobbering the descriptor, hiding
bytes inside the reserved gap, or swapping the core without rebinding
the descriptor fails RED by design.

`read_payload_descriptor`, `embed_payload_descriptor` and
`verify_sector_gap_reserved` were updated together for this relocation
and must stay consistent: the embed verifies the installed core hash
before writing, and the guard re-proves it on every device boot.

## 9. T7-DEVPROOF envelope (D31, interruptions, resources, cgroup gate)

`tools/x8_qemu/devproof.py` (contract in
`tests/test_x8_qemu/test_devproof.py`) adds the device-observed
data/fault/resource envelope onto the lifecycle above without changing
its legs:

- D31 rollback: representative writes through the normal store APIs
  (device settings, child profile, progression session, Activity save,
  Parent credential), then the deliberately broken candidate fails via
  the real `mark_candidate_unhealthy` trigger; the previous accepted
  release re-opens the state through the store parse paths and semantic
  values must match with no destructive repair.
- 7-point legacy-first interruption matrix
  (`inactive-base-write`, `base-readback-finalization`,
  `boot-artifact-staging`, `one-shot-arm`,
  `candidate-boot-before-health`,
  `healthy-committing-before-backend-commit`,
  `committed-backend-unwritten-accepted-state`): the first six
  reconcile to the previous accepted slot A through the real backend +
  journal; the committed-backend case completes the pending
  accepted-state write (accepted-sequence 20 → 21) and reconciles to
  the committed slot B, verified by re-reading the backend default
  plus the accepted sequence.
- Resource envelope: RSS/MemAvailable, decompression and finalization
  peaks, staging workspace, disk used/free measured per run; slot
  sizes and the PERSIST minimum are layout-plan facts owned by
  `tools/x8_qemu/runner.py` (`PROFILE_SLOT_BYTES` /
  `PROFILE_PERSIST_MINIMUM_BYTES`); bundle size is measured from the
  supplied bundle file (explicitly absent otherwise); diagnostic
  budget bound recorded. Near-full-storage preflight refuses before
  destructive/staging work when headroom is short.
- 768 MiB cgroup gate evaluated at the representative 220 MiB payload
  (`GATE_PAYLOAD_BYTES`, inside the ≤256 MiB bound; larger payloads
  are non-acceptance diagnostic only, never green): the gate streams
  the acceptance-sized payload through bounded 1 MiB chunks while
  sampling RSS, combines that streaming peak with the cgroup/ru_maxrss
  peak, requires headroom below the ceiling, no OOM, swap off at
  device scope, and RSS recorded.

`run_source_scope` carries the source-scope envelope additively;
`run_device` carries the device-measured envelope additively (RED fails
the device run closed). Device-measured values are recorded only from
real runs behind `require_device_host`, never synthesized; elsewhere
the device predicates report deferred/RED, never source-proxied green.

## 10. Fail-collect observation mode (DIAG-C1)

`LifecycleHarness.run_device_collect` runs the same production path as
`run_device` (same image assembly, device gate, shipped update path,
real SeaBIOS boots, frozen attestation seam, launcher seam, post-run
loop/cross-check binding, devproof device envelope) but wraps each of
the 8 lifecycle legs plus the post-run loop/cross-check binding and the
devproof device envelope in per-leg capture (`DeviceCollectRecorder` /
`run_collect_sequence` in `tools/x8_qemu/lifecycle.py`). Collection
widens OBSERVATION only: predicates are frozen before observation and
no RED is weakened, bypassed, or converted.

Continuation rules (code-authoritative in `COLLECT_CONTINUATION_RULES`):

1. every boot-outcome leg re-reads on-image state independently (fresh
   pre/post per leg; no leg consumes another leg's cached observation);
2. a RED boot leg never blocks later stage/boot legs;
3. a RED stage/arm leg never blocks later legs either: each later leg
   re-syncs and re-reads image state, REDing under its own frozen
   predicate when its preconditions are absent;
 4. the post-run loop/cross-check binding is always attempted with its
    own capture once setup yields an image, even with prior reds;
 5. the devproof device envelope is always attempted with its own
    capture once setup yields an image, even with prior reds;
 6. only abort-class conditions stop the run; nothing is skipped after
    an observed RED, except the no-image fail-closed early return
    (setup never produced an image, so boots/bindings have no image
    to observe — diagnostics are still emitted with setup reds).

 Collect-vs-abort boundary: teardown/loop-detach safety (checked
 `*_checked` helpers) and destructive-bound violations
 (`assert_collect_destructive_bounds`: non-absolute output dir or an
 image escaping the disposable output dir) abort immediately and fail
 closed (`CollectAbortError`, never collected); `require_device_host`,
clean-exit gate predicates, consumption checks, and attestation binding
predicates are observed and recorded but their REDs are never weakened,
bypassed, or converted — production/device behavior stays fail-fast and
fail-closed.

The frozen attestation seam (grubenv-on-image, T7-ATTEST leg partition)
is byte-identical in semantics: `decide_device_boot_observation`
predicates are called, never changed; only RED collection/reporting
differs. A collected RED carries the verbatim fail-fast error, so a
single injected fault produces the identical RED predicate as the
fail-fast path.

Per-leg timeout policy: serial-byte growth and image SHA delta count as
progress, the leg timeout (`LegTimeoutPolicy`, thresholds mirroring the
frozen `bootchain.wait_for_clean_exit` predicates) is the hard ceiling,
and silence plus progress-then-stall are RED with the timeout recorded —
so a hung leg cannot eat the run. The real wait mechanism stays inside
`_boot_image_once`; the collect layer only stamps the evidence.

 Each run emits `greia-device-collect-diagnostics.json` containing, per
 red: gate name, frozen predicate, leg name, verbatim error, return code,
 serial bytes/growth, QEMU/host log paths, on-image pre/post grubenv
 bytes, disk state snapshot (image SHA pre/post, slot/default/one-shot/
 last-booted, journal state, accepted slot/release/sequence, PERSIST
 marker), and timeout/progress detail. Boot-leg REDs forward the live
 pre/boot/post/elapsed evidence present at the throw site
 (`BootLegCapture`, populated progressively inside the boot leg), so a
 consumption/clean-exit RED still carries its serial/log/pre/post/timeout
 detail. The final verdict aggregates ALL
 reds; aggregated reporting never converts a RED to green/yellow.
