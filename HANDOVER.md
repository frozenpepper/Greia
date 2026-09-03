# Greia — Current Engineering Handover

**Updated:** 2026-09-03  
**Canonical repository/branch:** `frozenpepper/Greia` / `main`  
**Version:** `0.13.0-phase0-dev`  
**Primary blocking phase:** **R7 — display/session/input architecture and exact-current physical closure**  
**Public-source readiness:** **IN PROGRESS**  
**Ordinary-family release:** **NOT READY**

This file is current state only. Historical implementation detail belongs in Git history.

## 1. Start here

Read:

```text
AGENTS.md
README.md
docs/DOCUMENTATION.md
docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md
HANDOVER.md
skills/greia-os-work/SKILL.md
```

Before installing/configuring tools read `SETUP.md`.

Do not use GitHub-hosted Actions without explicit owner authorization.

## 2. Active acceptance procedures

These documents remain active because their work remains open:

```text
docs/testing/2026-09-03_ACTIVITY_AGE_POLICY_ACCEPTANCE.md
docs/testing/2026-09-02_RECENT_COMMIT_CLEANUP_ACCEPTANCE.md
docs/testing/2026-09-02_R7_FINAL_EVIDENCE_GAP_CLOSURE.md
docs/testing/2026-09-02_R7_PARENT_SPOKEN_LABEL_UNIFIED_PROMOTION_GATE.md
```

The maintained Parent client is the separate repository:

```text
frozenpepper/Greia-Parent-App-Html
```

Its still-active system-output-control browser gate is:

```text
docs/PARENT_SYSTEM_OUTPUT_CONTROLS_ACCEPTANCE_2026-09-02.md
```

Do not classify any of these as historical while the corresponding issue/workstream is open.

## 3. Activity catalogue + Parent age policy

Current first-party catalogue: **41 Activities**.

Recent age-3 additions include:

```text
org.greia.quattro-stagioni
org.greia.faccine-momo
org.greia.mondo-contrari
org.greia.sottomarino-giramondo (interactive wooden rudder wheel, cast-iron & brass rough throttle lever, 8-species educational random facts, spoken Captain's orders, and two-tone acoustic whistle)
```

The catalogue-wide invariant is structural:

> Every first-party Greia Activity declares a defensible `recommended_age_min`.

`tests/test_first_party_activity_audience_metadata.py` discovers the complete first-party catalogue and enforces the rule without hard-coding a maximum Activity count.

`recommended_age_max` remains optional for genuinely open-ended experiences. Age suitability and difficulty are separate dimensions.

### Canonical Parent modes

```text
show_all
recommended_only
age_and_easier
custom
```

For child age `N`:

```text
recommended_only  = “Age N only”
                    declared audience range contains N

age_and_easier    = “Age N + easier”
                    declared minimum age is not above N
```

Old persisted/API value `hide_too_simple` is compatibility input only and normalizes immediately to `age_and_easier`.

### Unknown-age compatible packages

Compatible third-party/legacy packages may omit age metadata. Greia does not invent an age.

```text
show_all / custom
    unknown-age Activity may remain available

recommended_only / age_and_easier
    wholly unknown age metadata is NOT automatically included

always_show
    parent may deliberately expose it
```

Explicit `always_show` / `always_hide` is evaluated before automatic age/difficulty policy.

If the profile has no `approximate_age`, age-specific filtering is inactive and the Parent client disables those preset choices.

Living authorities:

```text
docs/product/CHILD_ACTIVITY_DISCOVERY_AND_AUDIENCE.md
skills/greia-activity-authoring/DISCOVERY.md
skills/greia-activity-authoring/DESIGN_AND_TEACHING.md
src/greia_platform/activity_discovery.py
```

## 4. Catalogue consistency caught during age review

`org.greia.sottomarino-giramondo` landed concurrently with correct age metadata:

```toml
recommended_age_min = 3
recommended_age_max = 8
```

Its initial discovery tags were outside the platform-owned vocabulary. They were reconciled to:

```toml
discovery_tags = ["nature", "action"]
```

rather than expanding global navigation vocabulary for one Activity.

Sottomarino also has prior headless Simulator evidence recorded by its authoring tranche. That evidence remains scoped to the exact revision that produced it; the later metadata-only correction does not create new runtime evidence.

## 5. Parent client state

The maintained HTML Parent client now presents, for a child aged 3:

```text
All age ranges
Age 3 only
Age 3 + easier
Custom choices
```

It also:

- displays `Age 3+`, bounded ranges, or `Age not specified` honestly;
- keeps difficulty as a separate control;
- disables age-specific choices when no approximate age exists;
- preserves explicit per-Activity overrides;
- mirrors production age semantics in localhost demo mode;
- regression-tests an unknown-age demo Activity, including explicit `Always show` recovery.

### Parent pin intentionally remains unchanged

Greia does not serve moving Parent `main`. The existing accepted Parent revision remains pinned in:

```text
runtime/parent-app-client.toml
```

Required order before advancing it:

```text
1. execute exact-current age-policy acceptance on both repositories
2. obtain browser/source ACCEPTED verdict
3. use tools/update_parent_client_pin.py on that exact accepted Parent checkout
4. regenerate the integrity manifest
5. run Greia static-client/integration checks
```

Do not advance the pin before browser acceptance.

## 6. Age-policy evidence boundary

Source now includes:

- exact-age range filtering;
- bounded `Age N + easier` filtering;
- legacy-mode migration;
- unknown-age exclusion from restrictive presets;
- explicit override precedence;
- catalogue-wide first-party minimum-age enforcement;
- Parent UI/demo semantics;
- regression tests for the above.

Current status remains:

```text
SOURCE-IMPLEMENTED / ACCEPTANCE-PENDING
```

Use:

```text
docs/testing/2026-09-03_ACTIVITY_AGE_POLICY_ACCEPTANCE.md
```

It requires exact-current clean heads of both repositories, focused Greia tests, `make verify`, Parent `npm test`, localhost browser review at desktop/1024×600/mobile, override/no-age/unknown-age checks and zero feature-caused console errors.

No such execution was performed from the current remote editing environment because no clean checkout is mounted and its shell environment cannot resolve GitHub. Static source review is not PASS evidence.

## 7. R7 remains blocking

Core invariants remain:

- Home/Back is Greia platform authority, never Activity-owned UI;
- `DisplaySessionCoordinator` owns Shell/Activity display-session transitions;
- `SystemChromeCoordinator` owns trusted navigation semantics;
- `TrustedChromeActivitySupervisor` binds Home to authoritative Activity lifecycle;
- Activities remain display/input-backend neutral;
- ordinary Activities receive no raw `/dev/input` or `/dev/dri` authority;
- Legacy X is compatibility/migration plumbing, not final architecture;
- Simulator evidence never substitutes for production backend/hardware evidence.

Earlier trusted-Home physical proof remains scoped to:

```text
57626d3f65a8bf3ae074eee15b00ee32ba3277bd
```

It does not automatically certify later Activity-age, toddler, Parent or system-control source.

Use:

```text
docs/testing/2026-09-02_R7_FINAL_EVIDENCE_GAP_CLOSURE.md
```

for exact-current R7 closure.

## 8. Recent toddler/runtime cleanup

The catalogue-wide modernization/decomposition pass remains complete. Do not restart a broad refactor sweep without a concrete defect.

Recent Giardino/Alfabeto/Bosco cleanup corrected pointer mapping, Activity-owned Home residue, feedback hot-path synthesis, fanfare sequencing, PCM format and localization issues.

Alfabeto still needs Acer first-frame/READY measurement because prepared audio cues may trade interaction latency for startup cost.

Use:

```text
docs/testing/2026-09-02_RECENT_COMMIT_CLEANUP_ACCEPTANCE.md
```

before claiming that cleanup accepted.

## 9. Voice/audio boundary

Launcher spoken labels remain Shell-owned prerecorded audio; no normal child-runtime narration TTS is introduced.

Shared accepted character speech remains:

```text
180 shared reactions
12 canonical character introductions
assets/audio/characters/shared/v0.2/
```

Pedagogical letters/syllables remain on the deterministic prerecorded path; character dialogue uses the canonical character voice path. Generation receipts/Whisper never replace human listening acceptance.

## 10. Activity authoring contract

For every new first-party Activity, the mandatory design pass requires:

```text
RECOMMENDED_AGE_MIN_DEFINED=yes
DISCOVERY_METADATA_PLAN_DEFINED=yes
PROGRESSION_REWARD_RELATIONSHIP_DEFINED=yes
```

The minimum age is chosen from the shipped cognitive, language, motor and interaction demands—not copied from `difficulty`.

The authoring skill also requires:

- parent-request decomposition;
- pre-reader/no-text-only command design;
- prerecorded VoiceEngine speech architecture;
- semantic feedback/audio conflict resolution;
- Greia progression/reward separation;
- Acer-class performance discipline;
- project-local authoring tools;
- repeated headless Simulator integration;
- final GUI Simulator user review.

## 11. Parent production path

Current exact owners include:

```text
src/greia_parent/protocol.py
src/greia_parent/api_server.py
src/greia_parent/package_api.py
src/greia_parent/update_api.py
src/greia_parent/production_api.py
src/greia_platform/activity_discovery.py
src/greia_platform/system_controls.py
src/greia_platform/system_controls_legacy_x.py
src/greia_platform/hardware_session.py
src/greia_platform/hardware_session_legacy_x.py
```

The Parent HTTP process remains unprivileged. Unavailable privileged mutations must remain unavailable rather than being faked or solved by broadening HTTP-server authority.

## 12. Public-source work

Public-source publication and ordinary-family release remain separate thresholds.

Still-open public-source work includes documentation/path cleanup, licensing/provenance, full-history secret/security review, legal/community entry points and contributor quick-start work.

Use:

```text
docs/release/GREIA_PUBLIC_RELEASE_READINESS.md
```

as release-readiness authority.

## 13. Evidence discipline

Always preserve:

```text
SOURCE
AUTHORING PROVIDER + HUMAN LISTENING
BROWSER
SIMULATOR
VM / IMAGE
PHYSICAL DEVICE
```

A committed test is not a PASS. A later source revision does not inherit earlier physical evidence. A Simulator screenshot does not prove production trusted chrome. An audio receipt does not replace human listening.
