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
docs/testing/2026-09-02_PARENT_REAL_RUNTIME_FINAL_ACCEPTANCE.md
```

The maintained Parent client is the separate repository:

```text
frozenpepper/Greia-Parent-App-Html
```

Its current production revision integrated into Greia is:

```text
75ee275771c495dc187efb5275732ea10c10af4b
```

The Parent real-runtime/Acer gate is the Greia-side authority for final production-browser/system-control evidence. `?demo=1` is never acceptance evidence.

Do not classify any active procedure as historical while the corresponding issue/workstream is open.

## 3. Activity catalogue + Parent age policy

Current first-party catalogue: **41 Activities**.

Recent age-3 additions include:

```text
org.greia.quattro-stagioni
org.greia.faccine-momo
org.greia.mondo-contrari
org.greia.sottomarino-giramondo
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

Compatible third-party/legacy packages may omit age metadata. Greia does not invent an age. Unknown-age Activities are not automatically included by restrictive age presets; explicit `always_show` / `always_hide` is evaluated before automatic age/difficulty policy.

If the profile has no `approximate_age`, age-specific filtering is inactive and the Parent client disables those preset choices.

Living authorities:

```text
docs/product/CHILD_ACTIVITY_DISCOVERY_AND_AUDIENCE.md
skills/greia-activity-authoring/DISCOVERY.md
skills/greia-activity-authoring/DESIGN_AND_TEACHING.md
src/greia_platform/activity_discovery.py
```

## 4. Catalogue consistency caught during age review

`org.greia.sottomarino-giramondo` landed with correct age metadata:

```toml
recommended_age_min = 3
recommended_age_max = 8
```

Its discovery tags were reconciled to the platform-owned vocabulary rather than expanding global navigation vocabulary for one Activity.

Prior headless Simulator evidence remains scoped to the exact revision that produced it. Later metadata/audio changes do not automatically inherit that runtime evidence.

## 5. Parent production client state

Greia now has one production browser implementation with an explicit source/integration chain:

```text
Greia-Parent-App-Html accepted revision
  -> runtime/parent-app-client.toml pin
  -> runtime/parent-app-client.manifest.json exact file hashes
  -> vendor/parent-app exact reviewed runtime
  -> build/overlay/usr/share/greia-parent-app exact image payload
  -> /usr/share/greia-parent-app installed runtime
```

Current pin:

```text
revision = 75ee275771c495dc187efb5275732ea10c10af4b
integration_state = vendored-image-integrity-enforced
```

The production manifest excludes localhost demo adapters. The accepted Parent source lazy-loads demo code only on loopback when explicitly requested; the Acer image does not contain those demo modules.

`greia_parent.parent_client_integrity` verifies exact installed files, byte counts and SHA-256 digests. `greia-parent.service` executes it in `ExecStartPre`; missing, changed, symlinked, unexpected or substituted runtime files prevent Parent service startup.

The lower-level error page is not a second management UI: it contains no controls or sample state. Production HTTP routing returns service-unavailable semantics when the real static shell is absent.

Architecture/update authority:

```text
docs/architecture/PARENT_APP_SOURCE_INTEGRATION.md
```

Final physical/browser authority:

```text
docs/testing/2026-09-02_PARENT_REAL_RUNTIME_FINAL_ACCEPTANCE.md
```

### Parent UI behavior

The maintained client presents child age presets, separate difficulty controls, real usage-limit controls, real Activity policy/install/remove surfaces when capabilities allow them, grouped device management, speaker volume/mute controls and a truthful Wi-Fi unavailable card when `network.manage=false`.

No browser visual state is sufficient evidence of mutation. Real device/child/system state must change.

## 6. Parent evidence boundary

Parent source now includes:

- exact-age and `Age N + easier` filtering;
- legacy-mode migration;
- unknown-age restrictive-preset handling;
- explicit Activity override precedence;
- catalogue-wide first-party age metadata enforcement;
- integrated real API client and production runtime manifest;
- deterministic Greia image installation of the reviewed browser bundle;
- installed-runtime integrity preflight;
- fail-closed production Wi-Fi composition;
- typed speaker volume/mute desired-state API;
- Parent client responsive and unavailable states.

Current production Parent status is:

```text
SOURCE/IMAGE-INTEGRATION IMPLEMENTED
PHYSICAL ACER REAL-RUNTIME ACCEPTANCE PENDING
```

No physical Acer acceptance was executed from the remote editing environment. Source review is not physical PASS evidence.

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

The minimum age is chosen from shipped cognitive, language, motor and interaction demands—not copied from `difficulty`.

The authoring skill also requires parent-request decomposition, pre-reader command design, prerecorded VoiceEngine speech architecture, semantic feedback/audio conflict resolution, Greia progression/reward separation, Acer-class performance discipline, project-local authoring tools, repeated headless Simulator integration and final GUI Simulator user review.

## 11. Parent production/API ownership

Current exact owners include:

```text
runtime/parent-app-client.toml
runtime/parent-app-client.manifest.json
vendor/parent-app/
build/overlay/usr/share/greia-parent-app/
src/greia_parent/static_client.py
src/greia_parent/parent_client_integrity.py
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

The Parent HTTP process remains unprivileged. Unavailable privileged mutations remain unavailable rather than being faked or solved by broadening HTTP-server authority.

### Wi-Fi

The installed production composition always starts from real `IwdWifiBackend`. `network.manage` becomes false when iwd is unavailable or its state is not effectively writable in the service namespace. Production connect rejects an SSID not returned by the real scan. Demo Wi-Fi remains lower-level developer/test fixture material only.

### Speaker output

Parent volume/mute does not own ALSA. The browser writes typed desired state through `/api/v1/settings/system-controls`; the child Legacy-X hardware session consumes shared state and applies `Master`, `Speaker`, then `PCM` through ALSA. Hardware media keys update the same authority. Do not “fix” Parent output by giving `greiapanel` mixer privileges.

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

A committed test is not a PASS. A later source revision does not inherit earlier physical evidence. A Simulator screenshot does not prove production trusted chrome. An audio receipt does not replace human listening. A successful Parent PUT does not prove physical hardware changed.

## 14. Display/input settings tranche — T10-R2 source candidate (2026-09-03)

T10-R2 re-authors the T10 close-out docs delta additively on the current tree (replaces T10-R, which never launched; retires F03/F04 as overtaken by events). No `src/`/`activities/`/`runtime/`/`build/`/`tests/` behaviour change in this task.

(This section is appended as §14 rather than §10 so the parallel agent's §§10–13 edits stay intact; it carries the candidate/NOT EXECUTED markers the T10-R2 brief assigns to the close-out section.)

T01–T09 implemented physical display facts, schema-v2 pointer settings, Legacy-X isolation, status/HAL exposure, shared touch-target floors, installer pointer/display pages, Parent pointer tab, and typed Parent hardware API. T10 closed the tranche at source level (ADR 0035 extends ADR 0020 + ADR 0026, neither replaced). The T10 forbidden-outcome sweep and 17 review answers are preserved by reference and not silently re-authored.

Normative pointers: `src/greia_platform/display_metrics.py` (facts/suitability/minimums), `HardwareSettingsStore` schema v2 tap-OFF, the Legacy-X hardware-session controller as the only pointer/display translation seam, `docs/adr/0035-physical-display-facts-and-shared-pointer-display-semantics.md`.

Catalogue state: **41 Activities**, with `org.greia.sottomarino-giramondo` accepted (T10-R's inventory-40 line is stale and was not carried over). Activity/catalogue pins follow live catalogue discovery, per the standing owner rule accepting Sottomarino and any new activity.

`SOURCE_CANDIDATE_SHA`, `make verify` test count, and both audit results are recorded in the T10-R2 implementer attempt report; `ACTIVITY_INPUT_STANDARDS.md` is intentionally untouched (pointer interaction semantics did not change — settings UX only).

**NOT EXECUTED (human/hardware-owned, runnable on the frozen candidate):**

1. Acer panel lane — boot the frozen candidate on the Acer Aspire One reference, confirm installer DISPLAY page reports detected size, complete install, confirm Shell/launcher readable and Home/Back reachable.
2. USB mouse lane — attach a USB mouse, confirm pointer tab lists a generic Mouse entry (no backend id), preset change applies, Escape/keyboard recovery works.
3. Second-display lane — attach a second display, confirm mode list offers only supported/reflow modes and unknown-physical fails open.
4. Resolution-change lane — change mode at runtime, confirm geometry recomputes with no stale hit rectangles and no unbounded log/cache growth.

Do not copy a physical PASS from an earlier candidate onto this one; execute all four lanes on the exact frozen SHA before hardware claims.

## 15. Bootstrap docs close-out — C02 source candidate (2026-09-03)

C02 finishes the close-out on the C01-integrated tree. The reviewer-verified T10-R2 5-path docs delta (ADR 0035, os-work skill `display_metrics.py` entry point + live-catalogue-discovery sentence, responsive pointer-setup seams, HANDOVER §14 candidate/`NOT EXECUTED` markers, append-only plan entry + fixer-1 RED disclosure) is carried onto this tree byte-identically (no re-authoring, no history rewrite; base files were byte-identical so the carry is merge-clean). C01's repair — deletion of the three dead `import sys` lines (`faccine_momo`, `mondo_contrari`, `quattro_stagioni`; accepted C01 reviewer-1 PASS) — is the sole behaviour-adjacent change and predates this task. No `src/`/`activities/`/`runtime/`/`build/`/`tests/` change in C02 itself (docs-only: carried delta + this section + plan entry).

Green evidence on the frozen candidate: `make verify` exit 0 — unit stage `Ran 1768 tests OK` (includes `tests/test_typography.py` 6 ok and `tests/test_parent_system_updates.py` 5 ok, retiring F03/F04 with no dangling planned state); `validate` PASS `activities=41`; `tools/audit_activity_backend_independence.py activities` exit 0 (`activities=41 blockers=0`, 2 pre-existing non-blocking migration notes); `audit_activity_system_chrome_ownership.py --strict` exit 0 (`blockers=0`). Exact `SOURCE_CANDIDATE_SHA`, counts, and audit output in the C02 implementer-1 attempt report.

Catalogue state: **41 Activities**, with `org.greia.sottomarino-giramondo` accepted. `ACTIVITY_INPUT_STANDARDS.md` remains intentionally untouched (pointer interaction semantics unchanged — settings UX only).

**NOT EXECUTED (human/hardware-owned, runnable on the frozen candidate):** the four §14 lanes (Acer panel, USB mouse, second display, resolution change). Do not copy a physical PASS from an earlier candidate onto this one; execute all four lanes on the exact frozen SHA before hardware claims.
