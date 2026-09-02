# Greia — Current Engineering Handover

**Updated:** 2026-09-02  
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

For the source cleanup that must now be executed before new acceptance claims read:

```text
docs/reviews/2026-09-02_RECENT_COMMIT_CLEANUP_PARENT_AND_TODDLER_RUNTIME.md
docs/testing/2026-09-02_RECENT_COMMIT_CLEANUP_ACCEPTANCE.md
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

The latest reviewed **runtime** cleanup source boundary is:

```text
2b0a1d7ac020ce83148cc3218889fab1a389f795
Tests: reject unsigned PCM16 mixer format
```

Later commits in the same continuation may be documentation-only. Always freeze the actual `origin/main` at execution time rather than copying this SHA into a new acceptance claim.

The recent runtime cleanup is **SOURCE-only** until the named focused gate executes. No post-cleanup `make verify`, Simulator PASS, audio-listening PASS or Acer PASS has been claimed.

The latest earlier trusted-Home physical evidence remains scoped to its exact runtime candidate:

```text
57626d3f65a8bf3ae074eee15b00ee32ba3277bd
```

At that candidate Writing, Painting, Shape Garden and Acquario physically showed/actioned trusted Home and returned to a responsive Shell. That physical PASS does **not** automatically certify later system-control, Parent or toddler-runtime source.

---

## 3. R7 is still blocking

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

## 4. Activity catalogue and recent toddler cleanup

Current built-in Activity inventory: **37**.

The catalogue-wide modernization/decomposition pass remains **COMPLETE**. Do not restart a broad refactor sweep without a concrete defect.

Toddler Activities in the current catalogue:

```text
org.greia.il-giardino-dei-numeri
org.greia.alfabeto-leo
org.greia.bosco-numeri
```

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

Historical toddler Simulator evidence predates parts of this cleanup and does not replace a fresh exact-current run.

---

## 5. Voice/audio evidence boundary

Launcher spoken labels remain Shell-owned prerecorded audio; no child-runtime narration TTS is introduced.

Shared accepted character speech remains:

```text
180 shared reactions: OWNER-ACCEPTED
12 character introductions: OWNER-ACCEPTED
accepted set: assets/audio/characters/shared/v0.2/
```

The earlier Alfabeto voice correction remains valid in source intent: Leo character dialogue uses the Leo Chatterbox voice while deterministic pedagogical targets use the deterministic path. Newly generated receipts/provider or Whisper success never replaces human listening acceptance.

The new `pygame_audio.py` helper is only a tiny format boundary for bounded Activity-generated SFX. It is **not** a replacement audio engine and does not own prerecorded speech or platform microphone/audio policy.

---

## 6. Parent production path

Current exact owners include:

```text
src/greia_parent/protocol.py
src/greia_parent/api_server.py
src/greia_parent/package_api.py
src/greia_parent/update_api.py
src/greia_parent/production_api.py
src/greia_platform/system_controls.py
src/greia_platform/system_controls_legacy_x.py
src/greia_platform/hardware_session.py
src/greia_platform/hardware_session_legacy_x.py
```

The installed `greia-parent.service` now launches `greia_parent.production_api` rather than relying on a generic composition plus environmental demo fallback.

Production policy now is explicit and fail-closed:

- default Wi-Fi backend is real IWD, not sample/demo Wi-Fi;
- unavailable management returns no fake network list and no simulated connection success;
- capability composition preserves package/update/settings/profile features;
- direct IWD is advertised as `network.manage` only when it is available **and** its state boundary is writable by the current process;
- the Parent HTTP process remains unprivileged `greiapanel` under its strict service sandbox.

`network.manage=false` may therefore be the correct current appliance truth. Do **not** grant the HTTP server root or broad `/var/lib/iwd` authority merely to make that capability true. The living Parent architecture already places future privileged mutations behind a narrow typed privileged broker.

The obsolete one-shot self-mutating workflow `.github/workflows/repair-real-parent-production.yml` was removed after the intended policy existed in normal source/tests. Do not recreate it.

Because this Parent production seam is new source, it has not yet earned post-cleanup execution evidence.

---

## 7. Public-source cleanup

The first public-repository deep dive remains:

```text
docs/reviews/2026-09-02_PUBLIC_REPOSITORY_DOCUMENTATION_DEEP_DIVE.md
```

Recent cleanup additionally removed two steady-state public-repo liabilities:

```text
.github/workflows/repair-real-parent-production.yml
tools/generate_toddler_audio.py
```

Still pending for Threshold A public-source readiness:

1. add a deterministic provider-free repository-relative documentation path/link audit for living navigation contracts;
2. classify materially ambiguous stale one-off runbooks/reviews as historical/superseded without rewriting their evidence;
3. complete licensing/provenance/history-secret/security/privacy/community-file review;
4. add reviewed public legal/community entry points rather than generic placeholders;
5. produce a public developer quick start and later ordinary-parent/user documentation appropriate to the release threshold.

Authoritative release checklist:

```text
docs/release/GREIA_PUBLIC_RELEASE_READINESS.md
```

---

## 8. Next exact work

### First: execute the recent cleanup gate

Use:

```text
docs/testing/2026-09-02_RECENT_COMMIT_CLEANUP_ACCEPTANCE.md
```

It requires:

1. freeze exact clean `origin/main`;
2. run `test_pygame_audio.py`, `test_parent_production_api.py` and `test_parent_api.py` by unittest discovery;
3. run backend-independence and strict system-chrome audits;
4. run `make verify` and record its fresh test count;
5. run the three toddler Activities through real-Shell Simulator, including scaled pointer mapping and Bosco IT/EN localization;
6. only on the same still-current SHA, use the Acer to measure toddler first-frame/READY latency, listen for generated-SFX pitch/channel correctness and inspect the real Parent capability/sandbox behavior.

Do not repair failures inside that gate. Preserve evidence and create a new source candidate if a correction is needed.

### Then: current R7 closure

If the cleanup gate is green and `main` is still frozen, execute:

```text
docs/testing/2026-09-02_R7_FINAL_EVIDENCE_GAP_CLOSURE.md
```

including system-control, Writing, Painting, hostile 10/10, crash-recovery, 20/20 durability and performance/log lanes. Classify the exact candidate `ACCEPTED`, `REJECTED` or `INCOMPLETE`.

Only after accepted R7.2/R7.3 closure may the next R7 subphase permitted by the active plan advance.

### Public-source work may continue in parallel

- deterministic living-document path/link audit;
- licensing/provenance/security/community-file Threshold-A audit without unsupported legal claims.

---

## 9. Evidence discipline

Always preserve these distinctions:

```text
SOURCE
AUTHORING PROVIDER + HUMAN LISTENING
SIMULATOR
VM / IMAGE
PHYSICAL DEVICE
```

A committed test is not a PASS. A later source commit does not inherit an earlier physical PASS. A valid audio receipt/Whisper result does not replace human listening. A Simulator screenshot does not prove production trusted chrome. Historical reviews remain evidence for their exact state, not current truth by default.
