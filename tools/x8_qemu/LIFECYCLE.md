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

Loop-attach the file-backed DOS image and run the production
observation path (`read_mbr_disk_signature`,
`probe_mbr_partition_partuuid`, `probe_partition_filesystem_uuid` via
`SubprocessMbrProbeRunner`); assert the bound record equals the observed
topology. The `sfdisk`/`blkid -p` file cross-check executes (not
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
payload + sector guard, installs the payload to partition 1, pushes
each armed block to the image, boots each boot-outcome leg once under
real SeaBIOS firmware with a clean-exit gate, derives the observed
slot solely from on-image pre/post consumption evidence, stamps it
through the production `reconcile` on the real on-image bytes, gates
it with `read_attestation_signal` through the post-boot loop
remount/read path, and only then folds it into the host backend, the
journal coordinator and the launcher seam (with the guest-observed
boot identity). Post-run loop/cross-check binding is enforced
executed-and-green. Device execution stays RED/deferred off capable
hosts — never claimed from source evidence. There is no `on_boot`
hook: stubbed-spawn runs are source scope and explicitly non-proxying
for the live predicate.

## 8. Sector 1-2047 gap coordination (future GRUB installer: read this)

Sectors 1–2047 of the disposable image are RESERVED. Sector 1 carries
the T7-PAYLOAD descriptor (magic `GREIAPY1`, pinned by
`verify_sector_gap_reserved` plus an explicit refusal on foreign or
non-zero sector bytes); sectors 2–2047 must read zero. Partition 1
starts at sector 2048. No gap embed lands in this task.

A future real GRUB `core.img` gap embed MUST NOT land in sectors
1–2047 without first relocating the descriptor through an explicit,
reviewed migration: reserve a different gap region, or move the
descriptor and update `read_payload_descriptor`,
`embed_payload_descriptor` and `verify_sector_gap_reserved` together.
Silently clobbering the descriptor (or hiding core bytes inside the
reserved gap) fails the guard RED by design.

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
