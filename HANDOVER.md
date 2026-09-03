# Greia — Current Engineering Handover

**Updated:** 2026-09-03  
**Canonical repository/branch:** `frozenpepper/Greia` / `main`  
**Version file:** `0.13.0-phase0-dev`  
**Primary blocking phase:** **R7 — display/session/input architecture and exact-current physical closure**  
**Public source readiness:** **IN PROGRESS**  
**Ordinary-family release:** **NOT READY**

This is the short continuation contract. Historical implementation detail belongs in the append-only active plan, dated reviews and Git history.

---

## 1. Start here

Before substantive work read:

```text
AGENTS.md
README.md
docs/DOCUMENTATION.md
docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md
HANDOVER.md
skills/greia-os-work/SKILL.md
```

Before installing/configuring tools read `SETUP.md`.

Current focused procedures include:

```text
docs/testing/2026-09-03_ACTIVITY_AGE_POLICY_ACCEPTANCE.md
docs/testing/2026-09-02_RECENT_COMMIT_CLEANUP_ACCEPTANCE.md
docs/testing/2026-09-02_R7_FINAL_EVIDENCE_GAP_CLOSURE.md
```

For public-source/release preparation also read:

```text
docs/release/GREIA_PUBLIC_RELEASE_READINESS.md
docs/governance/LICENSING_AND_TRADEMARK.md
docs/reviews/2026-09-02_PUBLIC_REPOSITORY_DOCUMENTATION_DEEP_DIVE.md
```

Do not use GitHub-hosted Actions without explicit owner authorization.

---

## 2. Current source/evidence boundary

Always freeze actual clean `origin/main` before an acceptance claim. Do not copy a historical SHA forward as evidence.

The latest runtime-affecting Greia change in the Activity-age tranche is:

```text
508e0a946f3093caf3eb4e43ec7883bb10f5f63c
Activities: make parent age mixes educationally bounded
```

Later commits in this tranche add/strengthen tests and documentation. The age-policy tranche is **SOURCE-only until `docs/testing/2026-09-03_ACTIVITY_AGE_POLICY_ACCEPTANCE.md` is executed on exact-current heads**.

The earlier trusted-Home physical evidence remains scoped to:

```text
57626d3f65a8bf3ae074eee15b00ee32ba3277bd
```

At that candidate Writing, Painting, Shape Garden and Acquario physically showed/actioned trusted Home and returned to a responsive Shell. That PASS does not certify later toddler, system-control, Parent or Activity-age source.

---

## 3. Activity catalogue age contract

The first-party catalogue has expanded since the old 37-Activity handover and now includes the three additional age-3 Activities:

```text
org.greia.quattro-stagioni
org.greia.faccine-momo
org.greia.mondo-contrari
```

alongside the earlier toddler set:

```text
org.greia.il-giardino-dei-numeri
org.greia.alfabeto-leo
org.greia.bosco-numeri
```

The important catalogue-wide rule is now structural rather than count-pinned:

> Every first-party Greia Activity must declare a defensible `recommended_age_min`.

`tests/test_first_party_activity_audience_metadata.py` enforces that rule over the complete discovered first-party catalogue and no longer contains a stale maximum catalogue count.

`recommended_age_max` remains optional. Open-ended creative/sensory/imaginative Activities must not receive fake upper-age limits merely for symmetry.

The parser still tolerates missing audience metadata for compatible legacy/external packages. Such metadata fails open and must be shown as unknown, not silently invented.

Authoring guidance is current in:

```text
skills/greia-activity-authoring/DISCOVERY.md
docs/product/CHILD_ACTIVITY_DISCOVERY_AND_AUDIENCE.md
```

---

## 4. Parent Activity age presets

Greia now owns four canonical per-profile visibility modes:

```text
show_all
recommended_only
age_and_easier
custom
```

### `recommended_only` — “Age N only”

The Activity's declared age range must contain the child's approximate age:

```text
recommended_age_min <= age <= recommended_age_max
```

A missing max is open-ended.

### `age_and_easier` — “Age N + easier”

The Activity's declared minimum age must not be above the child:

```text
recommended_age_min <= age
```

For a three-year-old this may include `2–4`, `3–6`, `3+` and simpler material, but it does not automatically admit `4+`, `4–8`, `5+` or `5–9`.

The old persisted/API value:

```text
hide_too_simple
```

remains accepted as compatibility input and normalizes immediately to canonical `age_and_easier`; new stored/API output uses the canonical value.

Difficulty remains an independent `1..10` dimension. Explicit `always_show` / `always_hide` overrides remain authoritative before automatic age/difficulty filtering.

If a child has no `approximate_age`, automatic age filtering stays inactive/fail-open.

---

## 5. Maintained Parent HTML app

The maintained browser client is the separate repository:

```text
frozenpepper/Greia-Parent-App-Html
```

Its current source now presents, for a child aged 3:

```text
All age ranges
Age 3 only
Age 3 + easier
Custom choices
```

It also:

- displays honest Activity audience labels such as `Age 3+` and `3–6 years`;
- displays wholly missing metadata as `Age not specified`, not `All ages`;
- disables age-specific presets when no approximate age exists;
- explains the exact preset meaning to the parent;
- keeps difficulty separate;
- preserves explicit per-Activity show/hide choices;
- keeps the localhost demo aligned with production policy semantics.

Greia does **not** serve moving Parent `main`. After exact-current browser acceptance succeeds, the accepted Parent revision must be deliberately pinned into Greia using the canonical `tools/update_parent_client_pin.py` workflow and integrity manifest, followed by Greia static-client/integration checks.

**Do not advance the Greia Parent pin before browser acceptance.**

---

## 6. Age-policy acceptance procedure

Use exactly:

```text
docs/testing/2026-09-03_ACTIVITY_AGE_POLICY_ACCEPTANCE.md
```

It requires clean exact-current heads of both repositories and covers:

```text
Greia activity audience manifest tests
Greia discovery-policy tests
first-party catalogue minimum-age gate
Parent API age-policy tests
Greia make verify
Parent npm test
localhost demo Age 3 only
localhost demo Age 3 + easier
explicit override precedence
no-age profile UX
1024×600 + mobile smoke review
zero feature-caused console errors
```

The required verdict is:

```text
FINAL_ACTIVITY_AGE_POLICY_VERDICT=ACCEPTED|REJECTED|STALE|INCOMPLETE
```

No Simulator/Acer claim follows merely from this browser/source gate.

---

## 7. R7 remains blocking

Core invariants remain:

- Home/Back is Greia platform authority, never Activity-owned UI;
- `DisplaySessionCoordinator` owns Shell/Activity display-session transitions;
- `SystemChromeCoordinator` owns trusted navigation semantics;
- `TrustedChromeActivitySupervisor` binds Home to authoritative Activity lifecycle;
- Activities remain display-backend neutral and retain direct safe SDL/Pygame rendering/input paths;
- ordinary Activities receive no raw `/dev/input` or `/dev/dri` authority;
- Legacy X is migration/compatibility plumbing, not the final architecture;
- Simulator evidence never substitutes for production backend/hardware evidence.

Authoritative exact-current R7 procedure:

```text
docs/testing/2026-09-02_R7_FINAL_EVIDENCE_GAP_CLOSURE.md
```

Recent system-control source corrections still await exact-current physical execution, including normal media keys, rapid key bursts, Parent-setting→physical-relative-key composition and media-key isolation while an Activity is active.

**Do not begin R7.4 implementation before required R7.2/R7.3 exact-current physical closure is accepted.**

---

## 8. Recent toddler/runtime cleanup still needs its gate

The catalogue-wide modernization/decomposition pass remains complete; do not restart a broad refactor sweep without a concrete defect. Current built-in Activity inventory: **41**.

Toddler & Discovery Activities in recent authoring:

```text
org.greia.il-giardino-dei-numeri
org.greia.alfabeto-leo
org.greia.bosco-numeri
org.greia.sottomarino-giramondo
```

Sottomarino Giramondo (`org.greia.sottomarino-giramondo`) adds a submarine simulator and cockpit busy-board with pseudo-3D porthole projection, 3 distinct depth biomes, tactile instrument controls with high-contrast pre-reader vector icons (Light, Sonar, Bubbles, Horn, Emergency Beacon) and balanced 23 px symmetrical spacing, phosphor radar, depth meter, non-scary animal encounters, signed PCM16 audio cues, and bilingual localization (`it`/`en`). Verified via Headless Simulator in both `it` and `en` with clean Home return.

The latest cleanup preserved Bosco's owner-authored educational-flow remediation: count completion auto-advance, final-cardinality reinforcement and continuing guess rounds.

Recent source cleanup then corrected concrete runtime/architecture residue:

- Bosco, Giardino and Alfabeto use `PygameReferenceCanvas.pointer()` instead of copied physical→logical transforms;
- Activity-local attempts to protect/own the Greia Home region were removed;
- Bosco and Alfabeto no longer synthesize full feedback waveforms in the click hot path;
- Bosco fanfare is one sequenced clip instead of repeated same-channel replacement calls;
- bounded generated PCM in all three toddler Activities now uses the actual signed-PCM16 mixer rate/channel layout through `src/greia_platform/pygame_audio.py`;
- Bosco renderer now resolves child-facing strings through `LocalizedResources`; its duplicate hard-coded localization table and Italian-only progress word were removed;
- obsolete project-specific root `tools/generate_toddler_audio.py` was removed. Reusable voice production remains `tools/greia_voice.py` / VoiceEngine.

Important open measurement: Alfabeto now prebuilds 26 marimba cues outside interaction. This removes click-time synthesis but may increase startup cost on the Atom floor. **Measure first-frame/READY latency on the Acer; do not assume desktop behavior.** If materially slow, prefer pre-generated bounded SFX or another startup-safe strategy rather than moving synthesis back into the interaction hot path.

Use:

```text
docs/testing/2026-09-02_RECENT_COMMIT_CLEANUP_ACCEPTANCE.md
```

Historical toddler Simulator evidence predates parts of this cleanup and does not replace a fresh exact-current run.

---

## 9. Voice/audio evidence boundary

Launcher spoken labels remain Shell-owned prerecorded audio; no child-runtime normal narration TTS is introduced.

Shared accepted character speech remains:

```text
180 shared reactions: OWNER-ACCEPTED
12 character introductions: OWNER-ACCEPTED
accepted set: assets/audio/characters/shared/v0.2/
```

Pedagogical letters/syllables remain on the deterministic prerecorded path; character dialogue uses the canonical character voice path. Voice receipts/provider or Whisper success never replaces human listening acceptance.

`src/greia_platform/pygame_audio.py` is only a small format boundary for bounded Activity-generated SFX, not a replacement audio engine.

---

## 10. Parent production path

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

The installed Parent composition remains explicit and fail-closed. The HTTP process stays unprivileged `greiapanel`; unavailable privileged mutations must remain unavailable rather than being faked or solved by broadening HTTP-server authority.

`network.manage=false` may be correct current appliance truth until the planned typed privileged broker exists.

---

## 11. Public-source cleanup

Authoritative release checklist:

```text
docs/release/GREIA_PUBLIC_RELEASE_READINESS.md
```

Still pending for Threshold A includes documentation-path auditing, historical-doc classification, licensing/provenance/history-secret/security/privacy/community-file review, reviewed legal/community entry points and a public developer quick start.

Do not confuse public-source publication, technical preview and ordinary-family release.

---

## 12. Next exact work

1. Execute `docs/testing/2026-09-03_ACTIVITY_AGE_POLICY_ACCEPTANCE.md` on exact-current Greia + Parent heads.
2. If green, advance the Greia Parent pin deliberately and run Greia static-client/integration checks on the resulting new exact Greia SHA.
3. Execute the still-pending recent toddler/runtime cleanup gate as required by its runbook.
4. Continue exact-current R7 physical evidence-gap closure; do not infer it from age-policy/browser acceptance.
5. Public-source cleanup may continue in parallel where it does not invalidate runtime evidence.

---

## 13. Evidence discipline

Always preserve these distinctions:

```text
SOURCE
AUTHORING PROVIDER + HUMAN LISTENING
BROWSER
SIMULATOR
VM / IMAGE
PHYSICAL DEVICE
```

A committed test is not a PASS. A later source commit does not inherit an earlier physical PASS. A valid audio receipt/Whisper result does not replace human listening. Browser/demo review does not prove the Greia staged pin or Acer behavior. Historical reviews remain evidence for their exact state, not current truth by default.
