# Greia — Standalone Engineering Handover

**Date:** 2026-08-23  
**Version family:** `0.13.x` development  
**Repository:** `frozenpepper/Greia` (private)  
**Canonical/default/development branch:** `main`  
**Primary blocking platform phase:** **R7 — Direct graphics/session/input architecture**  
**External Parent HTML runtime revision pinned by Greia:** `frozenpepper/Greia-Parent-App-Html@7ff7e318eb246618dab26939ba086999864538ce`  
**Parent client integration state:** `source-pinned-not-yet-vendored`

This file is the project-wide **current continuation contract**. Chronology belongs in plans/reviews; exact APIs/limits remain source-owned.

---

# 1. Current state at a glance

## Latest retained physical performance work

The reference Acer Aspire One launcher hover-transition tranche remains accepted at its measured scope.

On-device profiling found pointer hover transitions rebuilding the full 1024×600 scene at roughly **189.6 ms/frame (~5.3 fps)** while steady cached frames were already fast. The accepted `68899e9` tranche added:

- one-time display-format conversion of shared cached surfaces;
- a bounded working-set cache;
- pre-composited opaque scene backdrops;
- static-scene versus dynamic hover/launch cache-key separation;
- tile-level repair for hover/launch dynamics with full-rebuild fallback;
- backdrop-based profile badge repair;
- measurement-backed adaptive idle pacing.

Measured reference-Acer result:

```text
hover transition: 189.6 ms → 26.6 ms  (~5.3 → 37.6 fps)
full scene rebuild: 191.0 ms → 81.8 ms
steady cached frame: 3.46 ms → 3.34 ms
idle launcher CPU: ~10–11% → ~5–8%
card-sweep CPU avg: ~32% → ~16%
launcher RSS: ~153 MB → ~153 MB
```

On-device visual verification covered Collection Home, category grid, hover lift/title disclosure, focus/selection badge, pagination and rapid cross-card traversal without ghosting.

`docs/engineering/GREIA_PERFORMANCE_BEST_PRACTICES.md` is now the single accumulating performance manual for measured device cost, cache/alpha/invalidation rules, evidence discipline and case studies. This Parent/discovery tranche does not supersede or modify that performance work.

## Current source-test boundary

Focused launcher/performance suites associated with the Acer tranche passed. The current aggregate discover remains **not green**:

```text
1028 discovered tests
4 failures
```

All four failures are pre-existing boot-contract/diagnostic expectation drift around `panic=30` versus the accepted postmortem `panic=5` direction and reproduce on the pre-hover reference baseline. They were not caused by the Parent/discovery work in this handover.

Therefore **no current-head aggregate `make verify` PASS is claimed**. Owner disposition of that boot expectation remains required before an aggregate green claim.

No hosted GitHub Actions were queried or run.

---

# 2. Parent HTML client — rebuilt and repinned

Greia now pins the rebuilt external Parent client at:

```text
repository: frozenpepper/Greia-Parent-App-Html
revision:   7ff7e318eb246618dab26939ba086999864538ce
runtime:    /usr/share/greia-parent-app
state:      source-pinned-not-yet-vendored
```

Pin authorities:

```text
runtime/parent-app-client.toml
runtime/parent-app-client.manifest.json
```

The integrity manifest now contains exactly the rebuilt **12 runtime files**:

```text
index.html
styles/app.css
src/api.js
src/app.js
src/credential_store.js
src/demo_api.js
src/state.js
src/ui.js
src/views_helpers.js
src/views_home_children.js
src/views_activities.js
src/views_device.js
```

Deleted observer-era modules are no longer listed or loaded.

Verification performed before repin:

```text
Parent npm test:                  28 / 28 PASS
changed JS syntax checks:         PASS
changed published Git blobs:      byte-identical to tested local copies
Greia manifest vs Parent runtime: 12 / 12 byte-count + SHA-256 PASS
Greia pin TOML parse/revision:     PASS
```

Manual desktop/mobile browser visual acceptance remains open because the current execution environment could not provide a normal owner-controlled browser session. Source/unit/integrity evidence is not being reported as visual-browser acceptance.

## Parent product architecture

The rebuilt client has one state model and one product renderer around four parent jobs:

```text
Home
Children
Activities
This Greia
```

Implemented typed surfaces include:

- child profile create/edit/delete;
- child password set/replace/remove;
- optional approximate age;
- Automatic/Easier/Standard/Harder challenge preference;
- installed Activity inventory;
- per-child Activity visibility policy and individual Always show/Always hide overrides;
- Wi-Fi scan/connect;
- language;
- mouse/touchpad/display settings;
- microphone input gain when Greia exposes it;
- Parent password change;
- SSH maintenance enable/disable;
- paired-device list/revoke;
- system/update status and capability-gated delivery;
- Activity install only when the API advertises it.

The client remains API-first. It does not gain shell/filesystem/package-manager shortcuts.

---

# 3. Connected microphone-gain work reconciled

A latest-commit review before repinning found that Greia had added microphone input gain after the older Parent-client pin.

Current platform hardware contract:

```text
desired.mic_gain
minimum: 0.5× / 50%
default: 2.0× / 200%
maximum: 4.0× / 400%
```

The setting is implemented in `HardwareSettingsStore`, the Parent hardware API payload/update path and the on-device Parent settings panel.

The rebuilt external HTML client now exposes the same bounded control **only when** the returned hardware payload contains `desired.mic_gain`. Older payloads therefore remain fail-soft compatible.

This does **not** mean general audio management is complete. `settings.audio` remains false; microphone input gain is currently a typed hardware setting while general output volume/mute/device-selection awaits the Audio Service contract.

The Parent demo adapter mirrors the real 0.5×–4.0× bounds/default and rejects out-of-range values. New hardware-audio tests are included in the 28/28 Parent result.

---

# 4. Child Activity discovery — implementation is active, not future-only

Authorities:

```text
docs/product/CHILD_ACTIVITY_DISCOVERY_AND_AUDIENCE.md
docs/design/GREIA_LAUNCHER_INTERACTION_AND_ACTIVITY_CATALOGUE.md
src/greia_platform/activity_discovery.py
src/greia_launcher/catalogue_view.py
```

Normal child flow remains:

```text
profile
  → Greia Home
    → primary Collection
      → optional sub-Collection
        → Activity
```

Platform-owned primary vocabulary:

```text
create
play
learn
explore
my_greia
```

Valid Activities with no recognized primary destination fail open through bounded `browse` / More recovery. Arbitrary package category strings do not manufacture Home destinations. One Activity may appear in multiple Collections without duplicating installation/state/progression.

## Implemented audience metadata

`ActivityManifest` now owns:

```text
difficulty                 1..10 baseline
recommended_age_min        optional 1..18
recommended_age_max        optional 1..18
difficulty_min             optional 1..10
difficulty_max             optional 1..10
adaptive_difficulty        boolean
presentation.discovery_tags
```

Adaptive-difficulty ranges must be declared as a valid min/max pair and require `adaptive_difficulty = true`.

`ChildProfile` now owns:

```text
approximate_age            optional 1..18
challenge_preference       automatic/easier/standard/harder
```

No date of birth is required.

## Implemented Parent policy

`ActivityDiscoveryPolicy` owns:

```text
visibility_mode:
  show_all
  hide_too_simple
  recommended_only
  custom

overrides:
  always_show
  always_hide
```

Explicit Parent override wins before automatic recommendation. Missing age/audience metadata fails open for ordinary discovery.

`ActivityDiscoveryService` computes the effective visible/ranked set without changing package authority, saves or permissions.

## Implemented adaptive depth

`AdaptiveCollectionPlanner` currently uses:

```text
enter threshold:    > 10 triggers subdivision evaluation
collapse threshold: <= 8 returns direct Activities
9–10:               retained subdivision only when previously validly subdivided
semantic groups:    2–5, platform-owned vocabulary, >=2 Activities/group
maximum depth:      Home → primary → optional sub-Collection → Activity
```

Bad/incomplete semantic partitions remain direct rather than manufacturing a meaningless Other bucket.

The policy store carries bounded `subdivided_collections` hysteresis state separately from Parent visibility intent.

Collection-first, bounded-primary-vocabulary and adaptive-catalogue simulator acceptance is already recorded in repository testing documentation. Do **not** return to the old All/filter Home model.

---

# 5. Parent/security boundary still open

The current LAN Parent transport remains provisional HTTP/bootstrap pairing.

Implemented foundations include per-device bearer credentials and individual revocation, but production acceptance still requires:

- short-lived Greia-owned pairing challenge;
- local device Allow/Deny confirmation;
- authenticated encrypted transport;
- device binding plus expiry/replay protections.

Ordinary/release capability advertisement must remain honest. In particular, source presence does not authorize package/system mutation over an insecure transport.

The external Parent client remains a source-pinned integrity-checked build input; it is **not yet vendored/composed into the release image as a closed packaging tranche**.

---

# 6. Device language / localization

Authorities:

```text
docs/adr/0028-platform-and-activity-localization-language-context.md
docs/product/SYSTEM_LANGUAGE_AND_LOCALIZATION.md
```

Effective language is selected at install, persisted, and may later be overridden by `SystemLanguageStore`. English remains default; current canonical selectable registry includes:

```text
en, it, es, de, fr, zh-CN, pt, ar, hi, id, bn, sw
```

`zh` canonicalizes to `zh-CN`. Installer, on-device Parent panel and external Parent client consume the Greia-owned registry.

Selectable does not imply complete translations, shaping/font coverage or RTL acceptance.

---

# 7. Transactional Greia system updates

Authorities:

```text
docs/adr/0030-platform-owned-transactional-system-updates.md
docs/product/SYSTEM_UPDATES.md
docs/development/GREIA_SYSTEM_UPDATE_RELEASE_WORKFLOW.md
```

Signed `.greiaupdate` source/trust/inbox/tooling foundations exist.

Current x86 profile remains `bios-single-ext4` with:

```text
system.update.activate = false
```

A/B inactive-slot activation, boot-health confirmation and automatic rollback are not accepted on the current production layout. No in-place active-root fallback is authorized for convenience.

---

# 8. R7 remains the blocking architecture phase

Current production remains provisional Xorg/xinit compatibility behavior while direct appliance display/session/input is resolved.

Mandatory architecture remains:

- Greia-owned display/session authority;
- protected platform Home/Back above Activity content;
- protected-system input intercepted before Activity delivery;
- controller ownership/normalization platform-owned;
- ordinary Activities do not gain raw `/dev/input` or DRM authority.

Recent launcher performance work is valuable physical evidence but is **not** R7 display/session closure.

---

# 9. Boot / installer / physical facts retained

- Reference Acer Aspire One is BIOS-only.
- Proven live USB path is syslinux/FAT32.
- Canonical USB creator: `tools/build-live-usb.sh`.
- Installed initramfs must be target-kernel/target-hardware aware; build-host/chroot hardware is not target authority.
- Developer/test SSH remains owner-approved `greia / greia`, root SSH denied; normal/release remains fail-closed.
- Physical evidence applies only to the exact source/image/tranche measured and must not be generalized to later source.

Canonical hardware history:

```text
docs/INSTALLATION_ISSUES_LOG.md
docs/INSTALLATION_USB_BOOT_POSTMORTEM.md
docs/INSTALLED_OS_BOOT_POSTMORTEM.md
docs/testing/LOCAL_AGENT_START_HERE.md
```

---

# 10. Visual/art continuation

Stable/current authorities:

```text
docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
docs/engineering/GREIA_PERFORMANCE_BEST_PRACTICES.md
docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md
docs/design/GREIA_GENERIC_ART_LIBRARY_TAXONOMY.md
skills/greia-visual-authoring/SKILL.md
docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md
docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
```

Theme/source bundles remain provenance pools; the generic semantic authoring library is the primary authoring interface. Generic authoring tooling stays development-time and does not become a second runtime catalogue.

Do not infer arbitrary Activity-authoring-agent drawing capability from the owner's stronger maintainer-side agent.

---

# 11. Next exact steps

## Blocking engineering

1. Resolve current `main` before each new implementation tranche.
2. Owner disposition: reconcile the four stale boot-contract tests (`panic=30`) with the accepted postmortem/source direction (`panic=5`).
3. Re-run the current aggregate verification only after that disposition; preserve genuine failures.
4. Continue R7 from its first incomplete blocking gate; do not treat launcher performance optimization as display/session closure.
5. Preserve the current Acer performance measurements in the engineering performance manual as future UI/render work is added.

## Parent

1. On an owner-controlled browser checkout, run `npm test`, serve the Parent client and visually exercise desktop + mobile/narrow layouts including microphone gain.
2. Preserve the exact `7ff7e318...` runtime pin until a newer Parent runtime is reviewed and its integrity manifest regenerated.
3. Decide/implement the separate vendoring/release-image composition tranche; do not runtime-fetch moving Parent `main`.
4. Continue production pairing/encrypted-transport work before enabling ordinary release mutation capabilities.

## Child discovery

1. Treat adaptive Collection depth, profile age/challenge and Parent visibility as **implemented foundations**.
2. Calibrate metadata/group vocabulary/thresholds through evidence rather than adding hierarchy depth.
3. Keep missing metadata fail-open and Parent overrides authoritative.
4. Keep education taxonomy separate from navigation taxonomy.

---

# 12. Non-negotiable continuation rules

- `main` only unless owner changes policy;
- GitHub is canonical persistence;
- no unauthorized GitHub Actions use/inspection;
- no current-head PASS without current-head execution;
- no visible Linux shell/desktop in normal child path;
- R7 remains open and Xorg/xinit provisional;
- protected Home/Back stays outside Activity authority;
- controller/input/device authority stays platform-owned;
- one canonical device-language registry;
- selectable language is not translation/font/RTL completion;
- system-update activation stays false on current single-root profiles;
- Parent HTTP/bootstrap transport remains provisional;
- external Parent JS is pinned/integrity-checked, never fetched from moving `main` at runtime;
- Collection-first Home is accepted; old All/filter root is not normal child IA;
- root and sub-Collection vocabularies are platform-owned;
- effective catalogue is per child after Parent policy;
- age and difficulty remain separate dimensions;
- missing audience metadata fails open;
- explicit Parent Activity overrides win over automatic recommendation;
- adaptive discovery never exceeds one sub-Collection layer;
- Collections are semantic child groupings, never filesystem folders;
- visual runtime caches remain bounded and avoid per-frame decode/scale;
- performance claims require measurement on the claimed execution scope.

**Resume the blocking platform path from R7 in `docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md`. Preserve the Parent pin/discovery implementation documented above; do not re-open them as hypothetical future design.**
