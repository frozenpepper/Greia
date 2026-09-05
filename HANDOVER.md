# Greia — Current Engineering Handover

**Updated:** 2026-09-05  
**Canonical repository/branch:** `frozenpepper/Greia` / `main`  
**Version:** `0.13.0-phase0-dev`  
**Primary blocking phase:** **R8 — Raspberry Pi 400 / Pi 500 ARM64 board and image adapters**  
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

## 7. R7 complete and accepted on reference hardware

Phase R7 is formally **COMPLETE** and verified at source, headless simulator, and physical hardware levels.

Core invariants verified:
- Home/Back is Greia platform authority, never Activity-owned UI;
- `DisplaySessionCoordinator` owns Shell/Activity display-session transitions;
- `SystemChromeCoordinator` owns trusted navigation semantics;
- `TrustedChromeActivitySupervisor` binds Home to authoritative Activity lifecycle;
- Activities remain display/input-backend neutral;
- ordinary Activities receive no raw `/dev/input` or `/dev/dri` authority;
- Controller navigation and reserved Guide button platform interception are proven via `ShellInputController` and `PygameControllerSet.poll_guide_button()`;
- Embedded Web runtime kiosk mode implemented via `WebRuntimeAdapter` with zero child-visible browser chrome;
- Physical reference Acer Aspire One evidence gap closed with verdict `ACCEPTED` on 2026-09-05 (10/10 hostile fixture forced returns, 20/20 durability cycles, writing persistence, system volume/mute/brightness keys).

Evidence report: `tmp/r7-final-20260905_014915-8599faaf/REPORT.txt`. Active blocking phase advances to R8.

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

## 22. Pre-intro boot optimization — R2 Phase 0+1 COMPLETE on-device, baseline recorded (2026-09-04)

T-BAG run R2 (`TBag/runs/R2`, analyst+grunt `opencode-go/muse-spark-1.3-contributor`) executes the owner-supplied plan `GREIA_PRE_INTRO_BOOT_OPTIMIZATION_PLAN.md`. Phase boot-01 graph B01–B05 fully terminal: B01 accepted, B02/B03R/B04 integrated, B03 superseded (scope-gate failure, delta abandoned, worktree cleaned), B05 accepted PASS on-device evidence.

Source-committed on `main` (pre-existing unrelated WIP in `activities/*` and parts of `src/greia_launcher/*` deliberately left uncommitted; staged hunks verified to contain all boot-marker lines and zero foreign lines):

```text
22461d1d boot: add pre-frame shell timing markers (GREIA_BOOT)
d593c1dd boot: instrument launcher Python path with exactly-once first-frame marker
4a68aced boot: add boot-marker analyzer and marker contract tests
```

What landed: `GREIA_BOOT` shell markers in the four launcher pre-hooks, `src/greia_platform/boot_markers.py` + launcher wiring with an exactly-once `intro_first_frame_flipped` guard after the first successful flip, `tools/boot/analyze_boot_markers.py` (fails closed on missing/duplicated first-frame marker), 13 new tests. 7-second intro untouched; initramfs/GRUB/network ordering untouched (no R2/R3 work).

Verification: combined-tree `make verify` green on re-run (exit 0) and green again after rebase onto `d8e28b06` (exit 0, pushed as `9f160cf2`). First local run showed one transient `ENOSPC` error from `tempfile.mkdtemp` under a 96%-full dev volume; re-runs clean, unrelated to these changes.

On-device closure (B05 PASS): target corrected to `greia-dev.local`/`192.168.68.104` (`acer.local` unresolvable; host key matches stored trust). R0 inventory: Debian 12 i686, kernel 6.1.0-52-686, single 7.4G ext4 with 5.4G free, initramfs `7c78167f…b2177` unchanged end-to-end, SSH healthy throughout. R1 deployed a marker-only 8-file port (rollback backup unused). 5-boot baseline medians: kernel 10.38s, userspace 11.00s, `activity_discovery` 19.15s (dominant — confirms index/composition phases next), `intro_first_frame` ~77ms, intro ~7.85s wall (nominal 5.0+2.0 design; tolerance watch item for Phase 4, not a gate failure). Evidence: `out/boot-optimization/` (93 files, `metrics.csv` 6 rows; gitignored, secret-scanned clean). Credential used strictly in-memory (`sshpass -e`, unset both ends, nothing persisted).

Next exact step: Phase 2 (2A–2D: scrub-to-trust-boundary, account migration, ALSA owner, VT minimal) Analyst decomposition. No Acer action needed until the next R1/R2 tranche is accepted.

## 23. Pre-intro boot optimization — R2 Phase 2 COMPLETE on-device (2026-09-04)

Phase boot-02 fully terminal (A1/B1/C1/D1 przyjęte; A2F/B2/C2F/D2 integrated; A3/B3/C3/D3 accepted PASS; A2/C2 superseded by their F-successors). Commits on `main`:

```text
0d63f979 boot: relocate recurring Activity scrubbing to trust boundaries (2A)
cfbd96be boot: move account/group repair off launcher start into versioned migration (2B)
d6c956f5 boot: remove competing pre-hook ALSA resets, single watcher owns volume (2C)
4e4434c5 boot: minimize VT pre-hook to native asserts, keep only dynamic setup (2D)
```

Each tranche proven on the Acer as one R1-class change (validation reboot + 3 timed boots, parser exit 0 throughout, initramfs `7c78167f…` unchanged end-to-end, machine healthy). Evidence: `out/boot-optimization/phase-02{a,b,c,d}/` (+ B05/A3 precedent), secret-scanned clean, gitignored.

Measured end-of-Phase-2 medians: kernel ~10.37s, userspace ~11.0s, VT pre-hook wall 0.255s (structural minimality per D1, not a speedup claim), `activity_discover` ~18.8s (still dominant — the Phase 3 target), first frame ~68ms, intro ~7.86s wall. Credentials strictly in-memory both ends, cleared after each tranche.

Process lessons recorded in-run: commit each integrated delta before its Acer tranche (A3/B3 pattern); verification reservation clarification pre-attached from C3 on (killed the wasted first cycle); cache-deletion recovery (worktree restored from retained branch, ghost analysis views removed).

Next exact step: Phase 3 (trusted Activity indexes + one-pass source composition) Analyst decomposition.

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

## 26. Acer Physical Hardware Session & Media Key Continuity Resolution (2026-09-04)

Addressed physical volume controls on Acer Aspire One (`192.168.68.104`):

1. **Diagnosis & Root Cause:**
   - Deployed `/usr/local/lib/greia-os/greia-x-session` on the physical Acer was invoking `/usr/bin/python3 -m greia_platform.hardware_session` instead of `hardware_session_legacy_x`.
   - The entrypoint had moved to `hardware_session_legacy_x` in the August 29 containment refactor; `hardware_session` exited immediately with code 0, leaving no `LegacyXMediaKeyListener` active on display `:0`.
   - Brightness hotkeys (`Fn+Left`/`Fn+Right`) functioned because ACPI firmware/`video.ko` directly adjusts GMA950 backlight PWM, whereas volume keys (`Fn+Up`/`Fn+Down`/`Fn+F8`) require a user-space listener to drive ALSA `amixer`.

2. **Live Device Remediation:**
   - Started background `greia_platform.hardware_session_legacy_x` as `greiakid` on display `:0`.
   - Patched `/usr/local/lib/greia-os/greia-x-session` on the Acer to ensure `hardware_session_legacy_x` starts automatically on every session launch.
   - Confirmed `LegacyXMediaKeyListener` listening on keycodes `121` (Mute), `122` (Volume Down), `123` (Volume Up), `232` (Brightness Down), and `233` (Brightness Up).

3. **Live Hardware Verification:**
   - Injected key events on display `:0`: confirmed Volume Up stepped ALSA `Master` mixer by +5% (70% → 75%), Mute toggled playback to `[off]`, second Mute toggled playback to `[on]`.
   - User physically tested and confirmed physical volume keys and audio response passed on the hardware device.

## 27. Web Runtime Adapter & Kiosk Mode Implementation (2026-09-04)

Implemented `WebRuntimeAdapter` (`src/greia_launcher/web_runtime.py`) providing natural, platform-governed execution of HTML/Web-based Activities in full appliance kiosk mode:

1. **Architecture & Product Contracts (ADR 0012 §33, ADR 0014 §6, ADR 0019, ADR 0020):**
   - Subordinate to `RuntimeLaunchAdapter` contract for `runtime_type = "web"`.
   - Strictly enforced kiosk mode: `--kiosk`, `--no-first-run`, `--no-default-browser-check`, `--disable-default-apps`, `--disable-sync`, `--disable-features=Translate,OptimizationHints`, `--incognito`, and `--disable-background-networking` when network capability is ungranted.
   - Zero visible browser chrome: no address bar, tabs, dev tools, or navigation UI exposed to the child.
   - Entrypoint verification: requires local `index.html` (or `.htm`), rejecting traversal, absolute paths, or non-HTML targets.
   - Package tree validation: rejects dangerous binaries (`.exe`, `.sh`, `.bin`, `.so`), symlinks pointing outside the activity root, and forbidden path names (`.git`, `node_modules`).
   - Process lifecycle: managed via `RuntimeInvocation` with bounded timeout collection, force-stop (`SIGTERM`/`SIGKILL`), and cleanup.

2. **Browser Discovery & Multi-Platform Support:**
   - Checks `GREIA_WEB_BROWSER` environment override.
   - Auto-detects `chromium-shell` (minimal kiosk package on Debian/Ubuntu), `chromium`, `cog` (WPE WebKit), `google-chrome`, `firefox-esr` (with `--kiosk`), and macOS Google Chrome for development.
   - Added `build/package-sets/runtime-web.txt` defining `chromium-shell` for build profile package resolution.

3. **Composition & Verification:**
   - Registered `WebRuntimeAdapter` in `src/greia_launcher/runtime_adapter.py` and `src/greia_launcher/composition.py` (`default_runtime_adapters()`).
   - Added `WebRuntimeAdapter` to static project validation in `tools/validate_project.py`.
   - 17/17 dedicated unit tests passing in `tests/test_web_runtime_adapter.py`.
   - Regression suites passing: `tests/test_runtime_manager.py` (14/14 PASS), `tests/test_supervisor.py` (14/14 PASS), `tests/test_r7*composition.py` (5/5 PASS).
   - `PYTHONPATH=src python3 tools/validate_project.py` PASS (`activities=41`, `image_profiles=10`).

## 28. Controller Navigation & Reserved System Input Integration (2026-09-04)

Completed physical controller and reserved Guide button system input integration across Shell and Activity supervisor per ADR 0019 and ADR 0020:

1. **Reserved Guide Button Platform Interception (ADR 0019, ADR 0020 §7):**
   - Added `poll_guide_button() -> bool` to `PygameControllerSet` (`src/greia_platform/pygame_input.py`).
   - Injected typed `ControllerGuideSource` into `TrustedChromeActivitySupervisor` (`src/greia_launcher/trusted_chrome_supervisor.py`).
   - While an Activity is in flight, `supervisor.poll()` checks `controller_set.poll_guide_button()`: pressing Guide immediately invokes `request_stop()`, terminating the Activity cleanly and returning to Greia Home without giving raw `/dev/input` to the Activity.
   - Forwarded `controller_set` from `ProfileVisualActivitySupervisor` (`child_shell.py`) and `TrustedGreiaLauncherPresentation` (`trusted_presentation.py`).

2. **Shell Controller Navigation & Analog Stick Integration:**
   - Exposed `controllers` property on `ShellInputController` (`src/greia_launcher/shell_input.py`).
   - Wired `self._shell_input` into `LauncherApplication.__init__`, `run()`, and `_launch_selected()` (`src/greia_launcher/main.py`), and forwarded kwargs in `GreiaLauncherPresentation.__init__` (`presentation.py`).
   - Main event loop dispatches controller digital buttons (`CONTROLLERBUTTONDOWN`) to `self._shell_input.handle_event()` and analog stick polling to `self._shell_input.poll_analog(monotonic_now)`.
   - Implemented `_handle_semantic_action()` routing `NAV_*`, `ACTIVATE`, and `CANCEL` through polymorphic `self._handle_key()` across profiles, categories, activities, and overlays.

3. **Verification & Evidence:**
   - `tests/test_launcher_controller.py`: 3/3 tests PASS.
   - `tests/test_trusted_chrome_supervisor.py`: verified Guide stop request without Activity event delivery.
   - `tests/test_r7_child_shell_trusted_chrome_composition.py`: verified `controller_set` forwarding.
   - Comprehensive `make verify`: 1864/1864 tests PASS in 137s.
   - `validate_project.py`: PASS (`activities=41`).
   - Activity backend independence and system chrome audits: PASS (`blockers=0`).

## 29. R7 Physical Hardware Evidence Gap Closure & Acceptance (2026-09-05)

Executed the automated physical gap closure harness `tools/run_r7_final_gap_closure.py` against reference hardware Acer Aspire One (`192.168.68.104`, GMA950 1024×600, Intel Atom N270) on display `:0`:

1. **Hostile Non-Cooperative Fixture Forced Returns (`org.greia.fixture.r7-noncooperative-chrome`):**
   - 10/10 full-screen hostile cycles executed on physical display `:0`.
   - Verified that the non-cooperative red display cannot capture, obscure, or intercept the platform-owned Home pill.
   - Every cycle terminated via platform lifecycle force-stop (SIGKILL) within timeout bounds and returned cleanly to Greia Shell with 0 stuck child processes, 0 launcher restarts, and 0 Linux/Xorg/terminal exposure (10/10 PASS).

2. **Writing Real-Input Persistence Lane (`org.greia.writing`):**
   - Launched `org.greia.writing` from page 5/5.
   - Injected physical text input ("CIAO GREIA") and verified live rendering on display `:0`.
   - Returned to Home cleanly with state persisted (PASS).

3. **Durability & Resource Run (20/20 sequential cycles):**
   - Executed 20 continuous launch and Home return cycles across diverse activities (`tre_carte`, `treno_numeri`, `scrittura`) on hardware.
   - Verified 0 memory leaks, 0 frame hitching, 0 focus drops, and clean Xorg session recovery across all 20 cycles (20/20 PASS).

4. **System Controls & Media Keys:**
   - Verified `hardware_session_legacy_x` media key listener on hardware: Volume Up/Down stepping ALSA `Master` mixer (+5% / -5%), Mute toggle (`[off]` / `[on]`), and ACPI brightness stepping (`Fn+Left` / `Fn+Right`).

5. **Snapshot, Logs & Verdict:**
   - Captured full snapshot and service journal at `tmp/r7-final-20260905_014915-8599faaf/` with `REPORT.txt` verdict: **`ACCEPTED`**.
   - Phase R7 is closed; primary blocking phase advances to **R8 — Raspberry Pi 400 / Pi 500 ARM64 board and image adapters**.


## 30. Launcher Responsive Navigation, Semantic Visual Polish & Bounded Dynamic Compositor (2026-09-05)

Implemented comprehensive enhancement of launcher navigation layout, visual polish, and dynamic compositor performance:

1. **Renderer-Neutral Responsive Navigation Geometry (`src/greia_launcher/navigation_layout.py`):**
   - Implemented pure geometric layout engine free of Pygame/HitTarget imports: `PageControlsPlacement(OUTER_GUTTER, PANEL_RAIL, CONTAINED_FALLBACK)`, immutable `PageControlsState`, `PageControlsLayout`, and `resolve_page_controls_layout()`.
   - Adaptive placement dynamically evaluates available gutters vs compact panel rail (e.g. 104px outer gutter on 1024×600 -> `OUTER_GUTTER`; 12px outer gutter on 800×600 -> `PANEL_RAIL`), guaranteeing arrows never collide with cards or exceed viewport boundaries.
   - Windowed visible dots pagination contract: caps displayed dots at 5–7 with centered sliding active dot window and counter string (`X / N`).
   - Added dedicated geometry test suite `tests/test_launcher_navigation_geometry.py` (8/8 PASS).

2. **Unified Presentation Seams & Delegation:**
   - Formalized `ShellPanelLayout(outer_rect, content_rect)` on `SharedUiShellPanelMixin` in `src/greia_launcher/shared_ui_presentation.py`.
   - Rewrote `_draw_page_controls` in `src/greia_launcher/navigation_chrome_presentation.py` to accept `PageControlsState` or `GridPage`, blitting semantic `ui.button.icon` with circular tactile fallback and rendering the bounded capsule pill.
   - Extracted `_draw_page_arrow_button` helper for reuse by damage repair and normal drawing.
   - Replaced duplicate procedural drawing in `_draw_pagination_and_overflow` (`presentation.py`) with delegation to `_draw_page_controls`.
   - Unified indicator hit targets: dot clicks cleanly map to item index for profile/activity pickers (`profile_page` / `activity_page`) and page index for catalogue scrolling (`presented_activity_page`); verified with `test_profile_picker_pagination_targets_and_navigation` in `tests/test_launcher_shell_productization_contract.py`.

3. **Generalized Bounded Dynamic Scene Compositor (`src/greia_launcher/presentation.py`):**
   - Upgraded `_repair_dynamic_activities` to repair damaged cards, navigation arrows, and the category header directly from the pre-composited `_last_scene_backdrop`.
   - Hover transitions across cards, arrows, category chips, and back button now restore exact paint bounds without triggering full-scene rebuilds on Atom-class CPUs.
   - Extended `tests/test_launcher_hover_scene_performance.py` with `test_chrome_controls_hover_repair_matches_full_rebuild` (7/7 PASS), proving exact bit-for-bit pixel equivalence and 0 full scene rebuilds.

4. **Semantic Visual Assets & Pipeline:**
   - Authored SVG master `assets/visual/ui/v0.1/icon_button_hover.svg` with elevated lift, softer drop shadow, and brighter milky sheen.
   - Registered in `assets/visual/ui/v0.1/catalog.toml` and `assets/catalog/shared_visuals_v1_source.toml`.
   - Built runtime PNG `assets/visual/runtime/v1/ui/icon_button_hover.png` and updated `assets/catalog/shared_visuals_v1.toml` via `tools/build_visual_renditions.py`.
   - Replaced hardcoded shadow color `(203, 213, 225)` in `_draw_activity_title_disclosure` with theme-aware `_mix(theme.background, (0, 0, 0), 0.16)`.

5. **Acceptance & Verification:**
   - Full repository test suite: **1,972 passed, 0 failed in 178 seconds**.
   - Rendered and verified visual acceptance across 1024×600 and 800×600 for Activity pagination, Category switcher, and Profile picker.

## 31. Boot plan integrated with lifecycle architecture — Phases 7–11 replaced, boot-05…18 planned (2026-09-05)

Imported the integrating agent's return (`greia-boot-plan-handoff/`, manifest 47/47 hashes clean, input SHA matches our exact packed file). Verified before import: Phases 0–6 byte-identical (first diff hunk lands exactly on the Phase 7 header; earlier hunks pure additions), D1–D22 intact, D23–D50 added, all 14 task records schema-valid/planned/zero-attempt.

Imported into live run R2 (no new run): adjusted governing plan replaced the plan file (original backed up as `.pre-phase7-replacement`), frozen ruling `authority/decisions/boot-lifecycle-integration--001.md`, 14 bootstrap briefs, `OWNER-PHASE-MAP.json`, 14 planned `BOOT-PLAN-05…18` task records, worker-rules revision r0002 frozen on the new plan (r0001 retained for boot-04 and earlier).

What changed materially: boot/install/update/hardware/persist/health are now one lifecycle architecture (one signed release artifact, v2 five-member contract, shared SlotWriter/Finalizer, explicit PERSIST, typed targets, separate narrow install/update services, common BootTransactionBackend, Pi tryboot, trusted one-use BOOT_HEALTHY, R4 risk class). Phase 7 non-destructive contracts, 8A–8G ordered substrate, Phase 9 HOST_FAST optional, rewritten final guards. Later planners are mechanical transcribers; D23–D50 closed to reopening.

Still open and unchanged: boot-04 (B04-IMPL reviewer PASS recorded, integration held for resume; B04-PROOF/DISP/REPROOF planned). boot-05 implementation is hard-gated on boot-04 terminal green — no phase skipped.

## 32. Launcher Navigation Buttons Sizing, Tactile Overhaul & Profile Panel Harmony (2026-09-05)

Completed visual and interaction overhaul of launcher navigation buttons, depth styling, and profile picker geometry:

1. **Enlarged, Tactile Button Disc:**
   - Vector masters `assets/visual/ui/v0.1/icon_button.svg` and `icon_button_hover.svg`: enlarged circle radius from 62 to 78 (diameter 156/180 = 87% fill vs 68% previously), switched palette from cold lavender to warm cream (`#FFFFFF` to `#FDF4E2`) with golden inner ring, top sheen arc, and rich gold hover border (`#FFC234`).
   - Recompiled runtime PNGs via `tools/build_visual_renditions.py` (`assets/visual/runtime/v1/ui/icon_button.png` and `icon_button_hover.png`).
   - Procedural fallback button in `_draw_page_arrow_button` updated to match tactile cream disc styling.

2. **Chunky Greia Directional Arrow Glyph:**
   - Replaced crude sharp isosceles triangles with canonical chunky Greia directional arrow glyph (chunky rounded shaft + rounded arrowhead with optical drop shadow), fully harmonized with `draw_back_symbol`.
   - Button size scaled responsively to available gutter: 72px disc with ~16px clearance in wide mode (1024×600) and 58px disc in compact rail mode (800×600).

3. **Profile Picker Panel & Pagination Harmony:**
   - Integrated `_shared_panel_inner_rect` into `_render_profile_picker_content` in `src/greia_launcher/main.py`: profile cards are now cleanly contained within the panel inner area with `pagination_reserve = 38` when multiple pages exist.
   - Resolved card and arrow collisions at 800×600: profile cards stop before the panel bezel, and navigation arrows center cleanly in the panel rails with generous clearance.
   - Centered bottom pagination capsule pill with proper vertical separation from cards.
   - Connected `self._page_content_rect` to `navigation_layout.py` when running without a tray panel, ensuring arrow buttons always center in the outer gutters outside the card content.

4. **Visual Cleanup & Polish:**
   - Removed redundant procedural polygon star from `SharedUiActivityCardMixin._draw_activity_tile_content` in `src/greia_launcher/shared_ui_presentation.py` (focused SVG master card already carries the badge).
   - Added grounding drop shadows, hover lift (-1px), subtle top sheen highlight line, and tactile circular Back button to category switcher chips in `presentation.py` and `navigation_chrome_presentation.py`.
   - Added grounding drop shadows, hover lift (-2px), and subtle top sheen lines to profile picker cards in `main.py` and `profile_chrome_presentation.py`.

5. **Verification & Performance:**
   - All 127 launcher tests PASS (`pytest tests/test_launcher*.py`).
   - `tests/test_launcher_hover_scene_performance.py`: verified bit-for-bit pixel equivalence and 0 full-scene rebuilds on hover.
   - `tools/validate_project.py`: PASS.
   - Rendered and visually inspected acceptance screenshots across 1024×600 and 800×600 for activities, category chips, and profile picker.


## 31. Collision degrade proven on-device — boot-04 proof green, dev-copy disposition due (2026-09-05)

B04-PROOF-R3 PASS accepted: the 2-file degrade tranche (`15e4249d`) onto the fail-closed Phase-3 baseline converts the deterministic crash loop into degraded-but-safe boot — 5/5 timed boots reach first frame, `NRestarts=0`, parser exit 0, initramfs unchanged, dev copy untouched, exact mechanism observed (built-in wins, dev claimant rejected + unissuable, structured conflict in journald). Evidence: `out/boot-optimization/phase-03/` (24 files, secret-clean). Two honest non-claims preserved: on-site visual/interactive picker proof (no display tooling over SSH) and the intro-tolerance reading (measured `first_frame→intro_end` median 7.853s, stable ±0.1s — systematic across all phases, needs authority interpretation, not drift).

Intermediate path: B04-BASE deploy proven but health predicate amended as unsatisfiable-by-design (disposition recorded, rollback explicitly not ordered); dead briefs B04-PROOF/R/R2 retired. Credentials in-memory only, cleared both ends.

Next exact step: OWNER dev-copy disposition decision (discard via canonical developer-control operation / preserve outside active root / continue via explicit replacement workflow), then B04-DISP executes it and B04-REPROOF proves clean. Only then may boot-05 planning begin.

## 33. Launcher Adversarial Visual Audit, Bezel Alignment, Optical Centering & Secret Entry Polish (2026-09-05)

Completed rigorous review and resolved visual/mathematical discrepancies across launcher states and resolutions:

1. **Visible Panel Tray Bezel Alignment (`src/greia_launcher/shared_ui_presentation.py`):**
   - Corrected `ShellPanelLayout.outer_rect` to account for the ~41px transparent drop-shadow padding in `panel_base.png`. The visible rounded white tray is `rect(36, 28, 568, 336)` in source coordinates. Outer gutters and rail boundaries now calculate against the actual visible bezel.

2. **Dynamic Content Bounds Integration (`src/greia_launcher/presentation.py` & `navigation_chrome_presentation.py`):**
   - Recorded `self._page_content_rect` in `_render_activities_content` and prioritized actual card bounds in `panel_content` layout resolution.
   - 800×600 rail mode: Navigation arrows sit comfortably inside the white tray (`x=88..144` and `x=655..713`) with ~30px clearance from both the tray bezel and the activity cards, eliminating the previous bezel-straddling bug.
   - 1024×600 gutter mode: Outer gutter arrows are optically centered (39px margin to screen edge, 39px margin to visible panel bezel) rather than clinging to screen edges.

3. **Arrow Glyph Optical Centering (`src/greia_launcher/navigation_chrome_presentation.py`):**
   - Applied subtle optical offset (+1.5px toward shaft) so the center of visual mass of the chunky directional arrow glyph aligns with the circular disc's geometric center.

4. **Secret Entry Button Overlap Fix (`src/greia_launcher/main.py`):**
   - Cancel, Erase, and Accept buttons previously overlapped by 11px each due to mismatched coordinate offsets. Grouped and centered them as a unified cluster with 24px clean gaps.

5. **Category Switcher Strip Right Margin:**
   - Reserved 96px right margin on the category chip strip when error badges or achievement stars are active, preventing chip collision with top-right indicators.

6. **Bottom Pagination Capsule Clearance (`src/greia_launcher/navigation_layout.py`):**
   - Constrained bottom pagination pill `pill_y` to guarantee it never overlaps bottom-row cards while respecting viewport bottom bounds.

7. **Verification & Performance:**
   - Added unit tests in `tests/test_launcher_navigation_geometry.py` (`test_bottom_pill_never_overlaps_content_cards`, `test_secret_entry_button_geometry_no_overlap`).
   - All 129 launcher tests PASS (`pytest tests/test_launcher*.py`).
   - Bit-for-bit hover damage repair pixel equivalence verified (7/7 PASS, 0 full-scene rebuilds).
   - Project validation PASS (`tools/validate_project.py`).
