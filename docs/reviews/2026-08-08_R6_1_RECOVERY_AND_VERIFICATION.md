# Greia R6.1 — Recovery and Verification Record

**Date:** 2026-08-08  
**Status:** R6.1 coherent source tranche recovered and verified; R6 remains IN PROGRESS  
**Active plan:** `docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md`

## Recovery reason

The implementation session was interrupted while R6 had already begun after the verified R5 source closure. The filesystem working tree at `/mnt/data/greia_work` was recovered and treated as authority rather than reconstructing code from chat narration.

The recovered tree contained the complete R1–R5 work plus partial R6 files. The R6 files were reviewed, completed into a coherent first tranche, tested in isolation, and then subjected to the full project verification gate before being mirrored to GitHub.

## Recovered baseline

The last confirmed pre-interruption remote milestone was:

- `12674010e47bd3299aa7ac625ae05abd614c3882` — R5 source closure record.

The recovered local tree independently passed the R5-era gate before R6 completion. The stale top section of the old remote `HANDOVER.md` was identified as continuity drift; the implementation itself was intact.

## R6.1 implemented/recovered

### Typed HAL boundary

Added typed semantic HAL interfaces/states for:

- display;
- input;
- audio;
- removable media;
- network;
- power.

The initial implementation deliberately keeps existing Linux/X behavior behind provisional adapters rather than making those backends part of the Activity/platform contract.

Current adapters include:

- provisional legacy-X display/input adapters;
- Linux ALSA-device availability probe;
- Greia removable-media-root availability probe;
- Linux network-device probe;
- systemd controlled-shutdown availability probe;
- deterministic static adapters for source tests.

R7 and R8 may replace these backends without changing Activity, Storage, Session, Progression, or Permission contracts.

### Device Capability Service

Added platform-owned semantic capability authority:

- immutable `DeviceCapabilitySnapshot`;
- stable semantic capability IDs;
- bounded source/provenance identifier;
- architecture/machine metadata;
- portable JSON-compatible detail validation;
- deterministic capability-state token;
- deep-frozen snapshot details so token/state cannot diverge through later mutation;
- explicit cache/refresh behavior in `DeviceCapabilityService`;
- `HALDeviceCapabilityProbe` mapping typed HAL observations into Greia semantic capabilities.

Current semantic capability examples include:

- `display`;
- `pointer`;
- `keyboard`;
- `touch`;
- `audio.basic`;
- `removable_media`;
- `network`;
- `power.controlled_shutdown`.

### PermissionBroker integration

`PermissionBroker` now accepts an injected trusted `DeviceCapabilityService` and uses the service snapshot as hardware/service capability truth for launch and permission decisions.

Consequences:

- Activity manifests describe requirements/requests but cannot define device truth;
- a missing required device capability refuses launch authority;
- a missing optional capability removes that effective capability and any dependent permission grant;
- package trust/origin and built-in identity policy remain independent permission gates;
- the static capability service remains only an explicit deterministic source-test/developer fallback;
- installed composition must inject the real HAL-backed service before R6 closes.

### Provisional X-session seam

The existing X-session hardware controller now exposes bounded pointer-presence probing used by the temporary HAL adapter. This is migration scaffolding only. ADR 0014 and the active plan still require direct appliance graphics; no new architectural dependency on X11 is created by R6.1.

## Verification

Focused Device Capability + PermissionBroker tests passed:

```text
13 / 13
```

Final recovered-tree gate:

```text
make verify
```

passed with:

- **219 / 219 provider-free unit tests**;
- project/runtime/Activity/asset validation PASS;
- canonical bundled Activity validation PASS;
- build/system-overlay source-contract validation PASS;
- source footprint approximately **16 MiB**.

Canonical Activity digests at this recovery point:

- `org.greia.shape-garden` — `dd53995e845564fc1bf735de76c1f4753d8de9e829cc86e78ba562265f21ca99`
- `org.greia.workshop-settings` — `a2d60444a3e95f2f00d5f0a1410819955e108bfbcc22315cf20d4ff4bfbcfeae`

A stale comment that still claimed Phase 0 had no Device Capability Service was corrected after recovery; the complete gate was rerun and remained **219/219**.

## Recovery commits

The recovered R6.1 work was mirrored through these GitHub commits:

- `5e3bcdbfc881dad2622f1e273c89d25c7eeef0e3` — trusted Device Capability Service;
- `a38d803b246338089afb7545bf24d538a1e29136` — typed Greia HAL protocols/adapters;
- `dc707d763551eb28bbd63a8f5a3209d85d9a6a6c` — PermissionBroker consumes trusted device capability authority;
- `971202e4723bab9a6ed619e5f885b9be01442b7d` — hardware-session controller mirrored with bounded pointer probe;
- `14da2032dfda0b7a9e1dc0691d6fc1cecd512233` — Device Capability/HAL tests;
- `8832e05a9d1fe46cee7a30ef36e4daead7b4f949` — PermissionBroker device-capability tests and current permanent-ID semantics;
- `1274f18daa9e822062da3e4b45218c5fdcd7ff52` — recovered root handover/current-state correction;
- `e35154e951e2d9d2b767bb6948f35672f6c78e1b` — post-recovery stale-comment correction.

## Current R6 status

R6 is **not complete**.

R6.2 still needs:

1. runtime-specific package/static validation moved behind the Runtime Adapter/Manager instead of the Python-oriented Activity registry being treated as universal;
2. runtime compatibility/resource selection based on trusted semantic device capability snapshots;
3. the installed launcher composition root to instantiate and inject the real HAL-backed `DeviceCapabilityService`;
4. negative tests proving Activity/runtime code cannot forge capability truth;
5. preservation of Storage, Session, Progression, and Permission services as runtime-neutral platform authorities.

Do not start R7 direct graphics, R8 Pi images, or R9 Web by bypassing this shared seam.

## Evidence limits

This recovery is source evidence only. It does **not** prove:

- Linux/Bubblewrap runtime socket behavior;
- DRM/KMS behavior;
- Acer behavior;
- Raspberry Pi 400/500 behavior;
- real audio/input/network device behavior;
- memory/resource certification;
- boot/recovery continuity.

Those remain later evidence gates.

## R0 continuity warning

R0 remains open. GitHub still lacks the complete binary asset library and some historical untouched files from the full verified local tree. This R6.1 record means the recovered *current tranche* is committed; it must not be interpreted as a claim that remote GitHub HEAD is already an independently reproducible full repository clone.
