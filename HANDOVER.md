# Greia — Current Engineering Handover

**Updated:** 2026-09-04  
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
docs/testing/2026-09-04_CHILD_ACTIVITY_POLICY_FAIL_CLOSED_ACCEPTANCE.md
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

Parent visibility policy is now a mandatory child-launcher boundary rather than an optional adaptive-presentation feature. The normal `GreiaChildShell` applies the policy before adaptive Collection grouping, while `TrustedGreiaLauncherPresentation` applies the same policy to a direct/non-adaptive catalogue. A genuinely missing policy file retains the normal default. A malformed, unreadable, unsupported-schema or symlink policy fails closed to zero launchable Activities until repaired; it is never reinterpreted as `show_all`.

The launcher also treats the policy file as a versioned atomic snapshot: the file identity is sampled before and after each read. A replacement that lands during the read is retried instead of allowing one policy version to be applied while a different version's token is acknowledged. Repeated churn fails closed and the ordinary bounded rescan retries later. Repair of a rejected policy clears the policy-specific error state when a valid snapshot becomes active.

Adaptive sub-Collection hysteresis is launcher-owned presentation state, not Parent authority. Historical `subdivided_collections` may seed the active rich Shell once for compatibility, but current launcher code keeps subsequent hysteresis in memory and does not write it back to the Parent policy file. This prevents stale Shell presentation state from clobbering a concurrent Parent `always_hide`, age-mode or difficulty change.

Living authorities:

```text
docs/product/CHILD_ACTIVITY_DISCOVERY_AND_AUDIENCE.md
skills/greia-activity-authoring/DISCOVERY.md
skills/greia-activity-authoring/DESIGN_AND_TEACHING.md
src/greia_platform/activity_discovery.py
src/greia_launcher/activity_policy_presentation.py
src/greia_launcher/child_shell.py
src/greia_launcher/trusted_presentation.py
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
- mandatory normal-Shell and trusted-fallback projection of Parent Activity visibility policy;
- fail-closed zero-Activity behavior for invalid existing discovery-policy state, distinct from a legitimate missing-policy default;
- stable atomic policy-snapshot reads that do not acknowledge a different replacement than the policy applied;
- launcher-owned adaptive subdivision hysteresis that cannot write back and clobber Parent policy;
- integrated real API client and production runtime manifest;
- deterministic Greia image installation of the reviewed browser bundle;
- installed-runtime integrity preflight;
- fail-closed production Wi-Fi composition;
- typed speaker volume/mute desired-state API;
- Parent client responsive and unavailable states.

Current production Parent status is:

```text
SOURCE/IMAGE-INTEGRATION IMPLEMENTED
CHILD POLICY FALLBACK + SNAPSHOT + NO-WRITEBACK SOURCE HARDENING IMPLEMENTED / EXACT-CURRENT ACCEPTANCE PENDING
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
src/greia_launcher/activity_policy_presentation.py
src/greia_launcher/child_shell.py
src/greia_launcher/trusted_presentation.py
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

C02 finishes the close-out on the C01-integrated tree. The reviewer-verified T10-R2 5-path docs delta (ADR 0035, os-work skill `display_metrics.py` entry point + live-catalogue-discovery sentence, responsive seams, HANDOVER §14 candidate/`NOT EXECUTED` markers, append-only plan entry + fixer-1 RED disclosure) is carried onto this tree byte-identically (no re-authoring, no history rewrite; base files were byte-identical so the carry is merge-clean). C01's repair — deletion of the three dead `import sys` lines (`faccine_momo`, `mondo_contrari`, `quattro_stagioni`; accepted C01 reviewer-1 PASS) — is the sole behaviour-adjacent change and predates this task. No `src/`/`activities/`/`runtime/`/`build/`/`tests/` change in C02 itself (docs-only: carried delta + this section + plan entry).

Green evidence on the frozen candidate: `make verify` exit 0 — unit stage `Ran 1768 tests OK` (includes `tests/test_typography.py` 6 ok and `tests/test_parent_system_updates.py` 5 ok, retiring F03/F04 with no dangling planned state); `validate` PASS `activities=41`; `tools/audit_activity_backend_independence.py activities` exit 0 (`activities=41 blockers=0`, 2 pre-existing non-blocking migration notes); `audit_activity_system_chrome_ownership.py --strict` exit 0 (`blockers=0`). Exact `SOURCE_CANDIDATE_SHA`, counts, and audit output in the C02 implementer-1 attempt report.

Catalogue state: **41 Activities**, with `org.greia.sottomarino-giramondo` accepted. `ACTIVITY_INPUT_STANDARDS.md` remains intentionally untouched (pointer interaction semantics unchanged — settings UX only).

**NOT EXECUTED (human/hardware-owned, runnable on the frozen candidate):** the four §14 lanes (Acer panel, USB mouse, second display, resolution change). Do not copy a physical PASS from an earlier candidate onto this one; execute all four lanes on the exact frozen SHA before hardware claims.

## 16. Child Activity policy fallback safety closure — source implemented (2026-09-04)

Source commit `28c58e06018c735f185ca2e6e674b1f695938222` closes two policy-authority defects found during the Parent production review:

1. the normal rich child Shell consumed Parent Activity visibility/age/difficulty policy, but the emergency `greia_launcher.trusted_presentation` fallback could present the raw catalogue if the richer Shell exited;
2. malformed stored discovery-policy data was caught in presentation code and replaced with `ActivityDiscoveryPolicy()`, which meant corruption could become the permissive `show_all` default even though the policy store already classified malformed state as invalid.

The correction introduces `src/greia_launcher/activity_policy_presentation.py` as one mandatory safety boundary. `GreiaChildShell` uses `PolicyEnforcedAdaptiveActivityDiscoveryMixin`: it applies Parent policy first, then retains the existing optional one-level adaptive Collection presentation. `TrustedGreiaLauncherPresentation` uses `DirectActivityPolicyDiscoveryMixin`: it deliberately remains a simple direct catalogue but consumes the same Parent visibility, age and difficulty authority before exposing any Activity.

Stored-policy states are now distinct:

```text
missing policy file
  -> legitimate normal default

valid policy file
  -> apply Parent intent

malformed / unreadable / unsupported-schema / symlink policy
  -> empty launchable catalogue until repaired
  -> keep launcher/profile recovery process alive
  -> never reinterpret as show_all
```

Repair is observed through the normal bounded rescan token using `lstat` state plus mtime/size/inode/mode, so replacing a rejected symlink or atomically repairing a corrupt policy can restore the catalogue without a permissive default.

Regression source is in `tests/test_launcher_activity_policy_safety.py`; it covers shared boundary inheritance, explicit hide in both paths, restrictive age filtering in the trusted fallback, missing-file defaults, malformed JSON, unsupported schema, symlink rejection, repair detection, and the fallback remaining non-adaptive.

Exact-current acceptance authority:

```text
docs/testing/2026-09-04_CHILD_ACTIVITY_POLICY_FAIL_CLOSED_ACCEPTANCE.md
```

Evidence actually produced in the remote authoring environment for the initial source commit: Python syntax compilation of the exact new/modified launcher and test files passed. The focused unit suite and `make verify` were **NOT RUN** here because this environment has no executable Greia checkout/network path to execute the repository; GitHub-hosted Actions were deliberately not used. The previous C02 `1768 tests OK` evidence predates this source change and does **not** certify `28c58e...` or later commits. Physical Acer trusted-fallback policy evidence is also **NOT RUN**.

## 17. Child Activity policy snapshot race hardening — source implemented, verification pending (2026-09-04)

Adversarial review after §16 found a second-order atomic-replacement race: the launcher could read policy version A, Parent could atomically replace it with version B immediately after the read, and the launcher could then record B's file token while still applying A. That would suppress the normal rescan until another file change.

`src/greia_launcher/activity_policy_presentation.py` now brackets each policy read with the same `lstat`-derived identity token. If the identity changes during the read, the snapshot is retried. The retry count is bounded; repeated churn fails closed with a deliberate retry token so the next ordinary rescan tries again. A valid repaired snapshot also clears the policy-specific error state instead of leaving a stale catalogue-error badge.

`tests/test_launcher_activity_policy_safety.py` now includes a deterministic atomic-replacement regression for both adaptive and direct launcher paths, plus explicit repair/error-clearing assertions. `docs/testing/2026-09-04_CHILD_ACTIVITY_POLICY_FAIL_CLOSED_ACCEPTANCE.md` requires these cases.

Verification status remains deliberately **PENDING**: neither the focused current suite nor current-head `make verify` has executed after the snapshot-hardening source changes. The historical C02 1768-test green predates them and cannot be inherited. No current physical Acer fallback-policy PASS is claimed.

## 18. Adaptive discovery policy writeback removed — source implemented, verification pending (2026-09-04)

A further end-to-end review found that adaptive Collection hysteresis was still being written into the same Parent policy file. Because that write was a read-modify-write based on an earlier snapshot, a concurrent Parent `always_hide`, age-mode or difficulty update could be overwritten by presentation-only state and potentially re-expose content.

That writeback is now removed from the installed rich child Shell. `PolicyEnforcedAdaptiveActivityDiscoveryMixin` owns `_adaptive_subdivision_state` in memory for the active profile/session. Historical `subdivided_collections` remains readable as a one-time compatibility seed, but the Shell no longer calls `ActivityDiscoveryPolicyStore.write()` to persist adaptive grouping. The trusted emergency fallback remains direct/non-adaptive and never writes policy.

Regression coverage now additionally requires:

- adaptive grouping can subdivide without any Shell policy write;
- a post-projection Parent `always_hide` changes the policy token, is observed by the next bounded rescan, remains stored, and removes the Activity from the child catalogue;
- stale presentation state cannot clobber Parent visibility/age/difficulty authority.

Current core commits for the complete policy-safety chain are:

```text
28c58e06018c735f185ca2e6e674b1f695938222  mandatory normal/fallback policy boundary
2e2d9f10316bb570e77d433a2e5779dd87af4e5b  stable policy snapshot hardening
52358aa892b5b1630fdedefbb2f43dd0eb4d3c94  snapshot-race + repair regressions
8cc7816f80ff79cfadd979e744ffdd02c02952f2  remove adaptive Shell Parent-policy writeback
daf14863273fd33ffabb6d5fc9278f382019f936  no-writeback + Parent-update regressions
a087c9664d0ef48e5082cc8b0b63b9535fc766f5  product authority reconciliation
fdcbb68d1a10ff9c6f5414c27d5beace293b327a  acceptance gate reconciliation
2265c5c456e173e2b670d5d5d42776d5526f0aa6  OS-work router reconciliation
```

Verification remains **PENDING** for the current chain: no focused exact-current unit run, no current `make verify`, and no current physical Acer trusted-fallback policy run has executed in this connector-only environment. The previous C02 `1768 tests OK` evidence predates every source change above and does not certify them.

Next exact step: freeze current `main`, run the focused policy safety suite, existing discovery/Parent regressions, and `make verify` exactly as specified by `docs/testing/2026-09-04_CHILD_ACTIVITY_POLICY_FAIL_CLOSED_ACCEPTANCE.md`. Only after the source/local gate is green should the sanctioned R7 physical fallback lane hide one harmless Activity through Parent and prove it remains hidden in both normal and emergency launcher paths.

## 19. Enciclopedia Greia — 398 Owner-Accepted Voice Lines Packaging (2026-09-04)

Packaged and registered all 398 pre-recorded owner-accepted voice assets (199 Italian, 199 English) into `activities/enciclopedia_greia/assets/audio/{it,en}/{group}/` and wired them through `locales/it.json` and `locales/en.json`:
- Home portal welcome (`encyclopedia.home.welcome`), 6 section introductions (`animals`, `body`, `earth`, `history`, `machines`, `space`), and 36 topic entry intros.
- All discovery tokens across all 36 topic pages speak full narrations by Leo, Tito, Lilli, and Dani upon activation.
- Conforms strictly to the Greia audio mapping contract (`assets/audio/<locale>/<group>/...`).
- Verification: 97/97 encyclopedia unit tests pass (`pytest tests/test_activity_enciclopedia*.py tests/test_encyclopedia_*.py`), 398/398 activity tests pass, automated audio playback verification script 100% PASS, headless simulator lifecycle & Home exit PASS (`rc=0`).

## 20. Enciclopedia Greia — Navigation Chevrons & Layout Collision Remediation (2026-09-04)

Remediated visual and interaction flaws identified during simulator visual inspection:
- Corrected chevron drawing coordinates in `enciclopedia_controls.py` so Left points `<` and Right points `>` (reversed drawing bug resolved).
- Uncovered discover lens in `animals.py` by relocating Tito the Fox to `(905, 560)` (bottom right corner).
- Lowered discover button in `body.py` to `(505, 560)` to clear the X-ray skeleton exhibit.
- Elevated navigation arrows in `space.py` to $y=270$ to clear the star chart easel and telescope.
- Resized action buttons to 76px with 86px hit areas and centered them at `(512, 460)` across 32 entry pages, providing clean vertical margins above the `(270, 507, 470, 72)` caption ribbon.
- Relocated Leo in `saturn.py` to `(130, 575)` to eliminate token overlap.
- Added direct canvas touch handling on key subjects (Lion mane/roar, Octopus ink squirt, Volcano eruption).
- Verification: 97/97 encyclopedia tests pass, 401/401 activity tests pass, and headless simulator 19-stage inspection tour verified visually with clean frames and zero collisions.

## 21. Activity discovery policy-store file-boundary hardening — source implemented, verification pending (2026-09-04)

A final adversarial pass moved the remaining pathname-race protection below the launcher into `ActivityDiscoveryPolicyStore`, so every consumer shares the same file-boundary guarantees. The store now opens only a regular-file snapshot, uses no-follow semantics where the host exposes them, verifies `lstat`/open-file identity, rejects replacement between lookup and open, rejects non-regular files, bounds the read to `MAX_BYTES + 1`, and verifies the opened file did not mutate while being read. Oversized content is rejected without first loading an unbounded file into memory.

Deterministic regressions in `tests/test_activity_discovery_policy.py` cover symlink rejection, a regular-file replacement between `lstat` and `open`, non-regular path rejection, and oversized-file rejection. The exact-current acceptance procedure was updated so these store-level invariants are part of the same fail-closed source gate.

Core store-hardening commits:

```text
82a64d9b596e81937fac9b996f7e89b2291010af  harden Activity discovery policy file reads
b754d970e5bb70f07eb1be5fbed5d5850c0aebba  deterministic bounded/no-follow store regressions
f5f4d9a5cd456dfc93e55d3e9a5c498c25645f64  acceptance procedure includes file-boundary cases
```

Verification is still **PENDING** for this policy-safety chain. No focused exact-current unit run, aggregate `make verify`, or physical Acer fallback-policy run is claimed from this connector-only work. Concurrent Enciclopedia/system-graphics work is a separate lane and is intentionally not modified by this policy tranche.

Next exact step remains `docs/testing/2026-09-04_CHILD_ACTIVITY_POLICY_FAIL_CLOSED_ACCEPTANCE.md` on a clean exact-current checkout; if `main` advances because of the independent Enciclopedia/system-graphics lane, freeze and test the new descendant rather than inheriting older evidence.

## 22. Pre-intro boot optimization — R2 Phase 0+1 source instrumentation landed, Acer gates pending (2026-09-04)

T-BAG run R2 (`TBag/runs/R2`, analyst+grunt `opencode-go/muse-spark-1.3-contributor`) executes the owner-supplied plan `GREIA_PRE_INTRO_BOOT_OPTIMIZATION_PLAN.md` (Phase 0+1 graph B01–B05; B03 superseded by B03R after a scope-gate failure, B02/B03R/B04 integrated, B05 human-blocked).

Source-committed on `main` (pre-existing unrelated WIP in `activities/*` and parts of `src/greia_launcher/*` deliberately left uncommitted; staged hunks verified to contain all boot-marker lines and zero foreign lines):

```text
22461d1d boot: add pre-frame shell timing markers (GREIA_BOOT)
d593c1dd boot: instrument launcher Python path with exactly-once first-frame marker
4a68aced boot: add boot-marker analyzer and marker contract tests
```

What landed: `GREIA_BOOT` shell markers in the four launcher pre-hooks, `src/greia_platform/boot_markers.py` + launcher wiring with an exactly-once `intro_first_frame_flipped` guard after the first successful flip, `tools/boot/analyze_boot_markers.py` (fails closed on missing/duplicated first-frame marker), 13 new tests. 7-second intro untouched; initramfs/GRUB/network ordering untouched (no R2/R3 work).

Verification: combined-tree `make verify` green on re-run (exit 0). First run showed one transient `ENOSPC` error from `tempfile.mkdtemp` under a 96%-full dev volume; re-run clean, unrelated to these changes. No Acer evidence yet: Phase 0 inventory/hashes and the 5-boot baseline are unmeasured, gates stay red, nothing waived.

Blocker (owner decision required): B05 needs a bounded Acer operator session (R0 inventory → Phase 0 gate → R1 single-change deploy + one reboot → 5 one-at-a-time reboots) or an explicit deferral of the Acer baseline. No worker tier has an SSH/operator path to the Acer; password/credentials must never enter source/history/evidence.

Next exact step: owner provisions the Acer session (supply host + credential channel + operator window) or defers; on provision, B05 resumes verbatim under existing authority. Downstream boot phases stay unplanned until the baseline exists.

## 23. Enciclopedia di Greia & Sottomarino Giramondo Visual & Interaction Remediation (2026-09-04)

Addressed user feedback across both activities following strict order of operations (local headless simulator -> test suite -> physical Acer Aspire One deployment & verification):

1. **Enciclopedia di Greia:**
   - Intro screen dark murky overlay eliminated: removed `paperGrain` SVG filter that caused CairoSVG to render a dark gray tint over `home_discovery_book` and `animals_field_table`. Ivory book is now bright, warm, and inviting with vivid category icons.
   - "Cosa vuoi scoprire?" title text moved upwards to $y=50$ in `enciclopedia_presentation.py`, clearing the top book edge.
   - Redundant and confusing center-bottom lens button with persistent selection circle retired across all screens in `enciclopedia_controls.py`.
   - Elephant page (`pages/elephant.py`) and animals field card completely redesigned from deformed gray blobs into a cuddly storybook elephant with pink inner ears, toenails, sweet eyes, and water pool.

2. **Sottomarino Giramondo:**
   - Bottom row of instrument buttons lowered by ~18px to $y=464$ (height 86) in `sub_cockpit_view.py`, aligning flush with the radar and depth gauge bezels.
   - Viewport populated with 26 active marine entities with inward swimming velocities in `sub_model.py`, eliminating the empty window issue.
   - Central red emergency button overhauled: replaced confusing starburst with a nautical Fresnel siren dome with brass cage and prominent "ALLARME" / "ALARM" label.
   - Condition satisfaction / encounter resolution bug fixed in `sub_app.py`: `bubbles` (octopus), `light` (shark), `horn`, and `action` all reliably trigger encounter resolution and celebration cues.
   - Octopus encounter upgraded in `sub_art.py` with 8 dynamic wrapping tentacles and suction cups pressed against the porthole glass.
   - Educational facts voiced aloud via generated Leo TTS audio cues (`sub_fact_*_1.wav`) with receipts, and displayed in centered high-contrast HUD cards with vector accent dots (no missing font glyphs).
   - Captain's orders filtered intelligently based on vehicle dynamics.

3. **Verification & Device Evidence:**
   - Unit tests: 87/87 enciclopedia tests, 6/6 sottomarino tests (`tests/test_activity_sottomarino.py`), 4/4 audit voice tests pass (`PYTHONPATH=src:tools pytest`).
   - Headless simulator runs for both activities exit 0 with clean Home return.
   - Deployed to physical Acer Aspire One (`192.168.68.104`) via `greia_remote.py deploy --replace-system`.
   - On-device live verification: captured screenshots confirming bright intro book, cute elephant, aligned submarine console, populated ocean, emergency siren dome, intact ADR 0019 system navigation pill, and clean return to Shell upon pressing Home.


## 24. Enciclopedia di Greia: Bridge & Airplane 4-5yo Storybook Overhaul (2026-09-04)

Addressed user feedback regarding broken/overly complex Machine gallery card drawings and concepts:

1. **Machines Gallery Workbench:**
   - Bridge model completely redesigned in `assets/source/machines_gallery_workbench.svg` into an adorable red suspension/arch bridge diorama over sparkling blue river water with terracotta towers, golden cables, and a tiny red toy car.
   - Airplane model overhauled into a friendly red-and-blue toy plane on a fluffy cloud stand with spinning yellow propeller, portholes, and stars.
   - Murky `<filter id="grain">` and dark overlay removed. Rebuilt `assets/runtime/machines_gallery_workbench.png` via `build_encyclopedia_visual_assets.py`.

2. **Concepts & Text (Locales `it.json` & `en.json`):**
   - Completely eliminated complex engineering/physics concepts (Bernoulli lift myths, tension/compression vectors, truss shear, load paths).
   - Replaced with cute, relatable stories for 4-5 year olds (crossing the river with beep-beep, rainbow arches, sturdy underwater pillar legs, soaring on soft air with bird friends, miniature toy towns seen from round windows, spinning propeller breeze).

3. **Page Implementations (`pages/bridge.py`, `pages/airplane.py`):**
   - Built full interactive storybook pages with soft pastel landscapes, smiling mascots (rubber ducky, bunny with heart, smiling sun), animated vehicle movements, and child-sized discovery hotspots.
   - Integrated canonical `draw_caption_ribbon` from `enciclopedia_presentation.py` for cleanly wrapped caption text.
   - Action buttons in `enciclopedia_toy_controls.py` updated with cute arched bridge and toy airplane icons.

4. **Verification & Device Evidence:**
   - Unit tests: 22/22 tests PASS (`tests/test_activity_enciclopedia*.py`).
   - Headless simulator: 5-second survival and clean Home return (`rc=0`).
   - Deployed to Acer Aspire One (`192.168.68.104`) via `greia_remote.py deploy activities/enciclopedia_greia --replace-system`.
   - On-device live verification: captured screenshots on Acer display `:0` confirming workbench diorama models, 'IL PONTE' page with duck and driving car, 'L\'AEROPLANO' page with smiling sun and cloud bunny, ADR 0019 system navigation pill `[Home] [<]`, and clean return to Greia Shell.

### Educational Depth Calibration (Magnets, Bridge, Airplane) & Acer Physical Verification

Refined concepts to achieve the requested intuitive, instructive "middle ground" (clear physical concepts for 4-5yo kids without babyish fluff or university equations):

1. **Locales (it.json & en.json):**
   - Calibrated explanations across `bridge.*`, `airplane.*`, and `magnet.*` to physical fundamentals: deck load distribution into banks and bedrock, wing shape generating upward lift, engine thrust, control surfaces (ailerons/rudder), cloud altitude scale (Cumuli vs. Cirri), magnetic attraction/repulsion, material testing, and Earth compass orientation.

2. **Interactive Science Lab Table (pages/magnet.py):**
   - Modern tactile bar magnets with bold "N" and "S" polarity markers (FontRole.CONTROL typography).
   - Draggable right magnet with realistic physics: snaps with golden sparkles when opposite poles face (N vs S), repels and pushes away with red repulsion waves when like poles face (S vs S).
   - "GIRA POLI" button to flip polarity and demonstrate attraction vs repulsion.
   - Materials testing tray with steel nail, wooden block, and aluminum coin.
   - Earth dipole globe with brass compass needle oscillating toward magnetic North.

3. **Bridge Mechanics (pages/bridge.py):**
   - Visualized downward vehicle weight on deck, arch curves redirecting weight outward to riverbanks, columns transferring weight into bedrock anchor blocks, and upward tension chevrons along suspension cables.

4. **Airplane Flight Dynamics (pages/airplane.py):**
   - Visualized curved wings generating upward lift (PORTANZA), propeller engine producing forward thrust (SPINTA), movable ailerons and tail rudder for flight control (COMANDI), and cloud altitude scale (QUOTA).

5. **Remote Tooling (tools/greia_remote.py):**
   - Hardened password deployments by utilizing `sshpass` if available, eliminating interactive terminal hangs during SFTP transfers.

6. **Verification & Physical Device Evidence:**
   - Unit tests: 22/22 tests pass in `tests/test_activity_enciclopedia*.py`.
   - Headless simulator: 5s survival and clean Home return (`rc=0`).
   - Physical deployment to Acer Aspire One (`192.168.68.104`) with `--replace-system`.
   - On-device screenshots on display `:0` verified:
     - `/tmp/acer_magnet_page_real.png`: "I MAGNETI" page with N/S magnets, field lines, "GIRA POLI" button, Dani mascot, caption ribbon.
     - `/tmp/acer_bridge_page.png` and `/tmp/acer_bridge_arch_active.png`: "IL PONTE" with load distribution vectors, arch chevrons, and bedrock anchors.
     - `/tmp/acer_airplane_page.png` and `/tmp/acer_airplane_lift.png`: "L'AEROPLANO" with lift forces, thrust, control surfaces, and cloud altitude ladder.
     - `/tmp/acer_final_shell.png`: ADR 0019 protected Home button returns cleanly to Greia Shell.

## 25. Submarine Octopus Resolution & Mongolfiera Launch Remediation (2026-09-04)

Addressed urgent user feedback on `sottomarino_giramondo` crash during octopus encounters and the "mongolfiera" activity launch failure:

1. **Submarine Bubbles + Octopus Crash Fix (`activities/sottomarino_giramondo/`):**
   - **Root cause:** `EncounterType` was referenced in `sub_app.py` lines 155 and 172 (`EncounterType.SHARK_WAVE`, `EncounterType.OCTOPUS_HUG`) without being imported, raising `NameError: name 'EncounterType' is not defined` when pressing `bubbles` or `light` during an encounter.
   - **Fix:** Imported `EncounterType` in both package and standalone import branches of `sub_app.py`.
   - Added direct encounter resolution when tapping inside the porthole glass where the octopus is hugging the glass.
   - Registered missing `"celebrate"` audio sample in `sub_audio.py` for celebration chimes.
   - Added regression test `test_octopus_bubbles_resolution_no_crash` in `tests/test_activity_sottomarino.py`.

2. **"Mongolfiera" (`mondo_contrari`) & Package Import Audit:**
   - **Root cause:** `activities/mondo_contrari/contrari_app.py` and `contrari_renderer.py` had unconditional `from .contrari_*` relative imports without `if __package__:` fallbacks, raising `ImportError: attempted relative import with no known parent package` when executed by the Python runtime adapter.
   - **Identity:** `mondo_contrari` features the hot-air balloon ("mongolfiera") with Flash the rabbit as its prominent gameplay and launcher card icon.
   - **Comprehensive audit:** Detected and corrected identical relative-import issues in `activities/faccine_momo` (`momo_app.py`, `momo_renderer.py`) and `activities/quattro_stagioni` (`tree_app.py`, `tree_renderer.py`).
   - Verified all 41 activities now import and launch cleanly (41/41 PASSED).

3. **Verification & Hardware Evidence:**
   - Unit tests: 404/404 tests PASS across all activities (`pytest tests/test_activity_*.py`).
   - Headless simulator: 5-second survival and clean Home return for both `org.greia.mondo-contrari` and `org.greia.sottomarino-giramondo` (`rc=0`).
   - Physical deployment to Acer Aspire One (`192.168.68.104`) via `greia_remote.py deploy --replace-system` for `sottomarino_giramondo`, `mondo_contrari`, `faccine_momo`, and `quattro_stagioni`.
   - On-device live verification:
     - `mondo_contrari` executed without import errors on hardware (`RC: 0`).
     - Captured screenshots on Acer display `:0` of `sottomarino_giramondo` (`/tmp/acer_sub_live.png`).
     - Pressed `BOLLE` (bubbles) button during close creature encounter: bubbles floated up smoothly with zero crash (`/tmp/acer_sub_bubbles.png`).
     - Toggled lights to resolve encounter (`/tmp/acer_sub_solved.png`).
     - Pressed ADR 0019 Home button: returned cleanly to Shell CREA category (`/tmp/acer_home_return.png`).
