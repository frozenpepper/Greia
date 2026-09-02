# Recent Commit Cleanup — Parent Production Path and Toddler Runtime

**Date:** 2026-09-02  
**Status:** SOURCE review; post-cleanup execution pending  
**Repository:** `frozenpepper/Greia` / `main`  
**Reviewed owner boundary:** recent work around the Bosco remediation at `09381df6` through the runtime cleanup source boundary ending at `2b0a1d7a`  
**Public release implication:** no new release PASS; R7 remains blocking

## 1. Review purpose

This pass reviewed the latest source after the new toddler Activities and Parent-web work landed. The goal was not another catalogue-wide refactor. It was to remove concrete architectural residue, duplicated low-level mechanics, release-risking tooling and Acer-floor hot-path problems while preserving the newly corrected educational behavior.

The owner’s Bosco educational remediation was treated as valid product work and preserved:

- completion auto-advances through the counting sequence;
- final cardinality is reinforced before praise;
- guess mode continues generating rounds instead of becoming a one-shot interaction.

No cleanup below intentionally changes that state machine.

## 2. Findings and corrections

### 2.1 Toddler Activities copied platform pointer/Home responsibilities

The new toddler Activities contained local physical-to-logical pointer transforms and Activity-side checks intended to avoid the trusted Home region.

That was the wrong ownership direction under R7. Greia already owns viewport mapping through `PygameReferenceCanvas`, and protected Home input belongs to trusted platform chrome before Activity input delivery.

Corrections:

- Bosco, Giardino and Alfabeto now use `PygameReferenceCanvas.pointer()`;
- the copied Activity-side Home assumptions were removed;
- no new Activity input broker or drawing API was introduced.

This reduces three divergent implementations to the existing platform contract and keeps Activities backend-neutral.

### 2.2 Procedural SFX work was in interaction hot paths

Bosco generated waveform samples during interaction and attempted a four-note fanfare as repeated immediate plays on one mixer channel. Alfabeto generated a full marimba waveform on each letter press.

Corrections:

- bounded procedural cues are built outside the click hot path;
- Bosco’s fanfare is one sequenced clip rather than same-channel replacement calls;
- Alfabeto prebuilds its per-letter marimba feedback.

The trade-off is explicit: Alfabeto moves work from interaction latency to Activity startup. That is architecturally preferable to click-time synthesis only if the Acer-floor first-frame/READY cost remains acceptable. No desktop-side timing assumption is being promoted to a product PASS; the new focused acceptance procedure requires physical measurement.

### 2.3 Generated PCM assumed the wrong mixer format

Giardino and Alfabeto synthesized raw signed PCM as fixed 22.05 kHz mono bytes. Pygame may have opened a different frequency/channel layout. This can produce incorrect duration/pitch and incorrect interpretation under a stereo mixer. Bosco had already begun querying the mixer but duplicated the low-level PCM interleave logic.

Correction:

- added the deliberately small `src/greia_platform/pygame_audio.py` boundary;
- `current_pcm16_mixer_spec()` accepts only an active signed 16-bit mixer and returns its real sample rate/channel count;
- `append_mono_pcm16()` clamps and writes one sample across the active channel layout;
- Bosco, Alfabeto and Giardino use the same helper;
- unsupported mixer formats fail by omitting procedural SFX rather than manufacturing malformed bytes.

This is a format helper, not a generic Greia audio engine. Prerecorded speech and platform audio policy remain with their existing owners.

### 2.4 Bosco had two localization authorities

Bosco already shipped `locales/it.json` and `locales/en.json`, but the renderer also imported a separate hard-coded `STRINGS` table, manually assembled the number question and displayed Italian `di` inside the progress badge.

Correction:

- mode labels and guess prompt now resolve through `LocalizedResources`;
- the duplicated `STRINGS` table was removed;
- the numeric progress badge is language-neutral;
- child-facing text now receives the platform’s normal localized presentation/case policy.

The bilingual descriptive fields inside `NumberDefinition` were not removed because this review did not prove them unnecessary enough to justify unrelated data-model churn.

### 2.5 Root toddler voice producer had become project-specific residue

`tools/generate_toddler_audio.py` had accumulated Giardino, Alfabeto and Bosco content-specific voice requests. The current voice workflow reserves root tooling for reusable Greia-wide production machinery; Activity-specific producers are disposable/local authoring aids. Generated assets and receipts already preserve the semantic production request.

Correction:

- removed the obsolete root producer;
- retained the actual generated assets/receipts and the reusable `tools/greia_voice.py` / VoiceEngine path.

Do not recreate a catalogue-specific root batch script merely for convenience.

### 2.6 Parent production could silently retain demo behavior

The installed Parent service previously launched the generic top-level update composition. A one-shot GitHub workflow had been added to rewrite Parent source in-place and push a repair, but that repair was not represented in ordinary source. Leaving a self-mutating hosted workflow as permanent repository machinery also conflicted with current repository policy.

Correction:

- added `greia_parent.production_api` as the explicit installed composition;
- the systemd service now launches that module;
- production defaults to real `IwdWifiBackend` rather than a demo/sample backend;
- unavailable Wi-Fi returns no fake network list and refuses connection attempts;
- capability composition preserves package/update/settings/profile capabilities;
- the one-shot self-mutating workflow was removed after normal source/tests represented the policy.

Lower layers may retain injectable adapters for tests/development. The installed appliance path is now explicit instead of depending on environmental fallback.

### 2.7 Real IWD availability is not sufficient mutation authority

A deeper privilege check found a critical boundary: `greia-parent.service` runs as unprivileged `greiapanel` under a strict systemd sandbox, while direct `IwdWifiBackend.connect()` persists profiles under IWD state. Merely detecting iwd could therefore advertise `network.manage=true` even when the HTTP service cannot successfully perform the mutation.

The living Parent architecture explicitly rejects turning the web/API process into a privileged manager. Privileged operations belong behind a narrow typed broker.

Correction:

- the production composition advertises direct-IWD `network.manage` only when the backend is available **and** its state directory is writable by the current process;
- `wifi_payload()` and `connect_wifi()` share that same fail-closed availability decision;
- an injected future semantic backend/broker can expose management without being forced through the direct-IWD writable-directory rule;
- the current service sandbox was not weakened.

Therefore `network.manage=false` can be the correct product truth on today’s unprivileged direct-IWD composition. The next implementation step, if ordinary-family Wi-Fi mutation is required, is the already-designed typed privileged broker—not root privileges or generic filesystem access for the HTTP server.

## 3. Tests added or corrected in source

New/focused source contracts include:

- `tests/test_parent_production_api.py`
  - real-IWD production default;
  - no fake scan/connect on unavailable backend;
  - fail-closed direct IWD when the state boundary is not writable;
  - composed capability preservation;
- `tests/test_pygame_audio.py`
  - actual mixer frequency/channel use;
  - unsupported/missing/unsigned PCM rejection;
  - mono-to-current-channel signed PCM writing;
  - sample clamping/channel validation;
- existing Parent service expectation updated to the explicit production entrypoint while preserving the unrelated credential-limit assertion.

These tests were authored/reviewed in source during this tranche. **They have not yet been executed after the complete cleanup.** No PASS count is claimed here.

## 4. Removed residue

Removed as part of this cleanup:

```text
.github/workflows/repair-real-parent-production.yml
tools/generate_toddler_audio.py
```

The first was a one-shot self-mutating hosted repair mechanism. The second was Activity-specific generation content living in a root reusable-tool namespace. Neither belongs in the public-source steady state.

## 5. Evidence boundary

The latest earlier physical trusted-Home evidence remains evidence for its exact earlier candidate only. None of the source changes in this review inherit that physical PASS.

Current classification:

```text
SOURCE CHANGES: PRESENT
FOCUSED POST-CLEANUP EXECUTION: PENDING
SIMULATOR ACCEPTANCE: PENDING
ACER PERFORMANCE/AUDIO OBSERVATION: PENDING
CURRENT R7 EXACT-CANDIDATE PHYSICAL CLOSURE: PENDING
ORDINARY-FAMILY RELEASE: NOT READY
```

Use:

```text
docs/testing/2026-09-02_RECENT_COMMIT_CLEANUP_ACCEPTANCE.md
```

for the focused cleanup gate, and continue to use:

```text
docs/testing/2026-09-02_R7_FINAL_EVIDENCE_GAP_CLOSURE.md
```

for authoritative R7 closure.

## 6. What the local acceptance must answer

The next execution should determine, rather than assume:

1. whether the focused Parent and PCM tests pass at the exact current candidate;
2. whether both architecture audits remain at zero blockers;
3. whether `make verify` remains green and what its fresh test count is;
4. whether all three toddler Activities still launch/return through the real Shell Simulator at scaled geometry;
5. whether Bosco’s Italian/English renderer now uses the canonical locale bundle correctly;
6. whether generated SFX have correct pitch/duration/channel behavior on a real mixer;
7. whether prebuilding Alfabeto’s 26 letter cues causes a material Acer-floor startup regression;
8. what `network.manage` truthfully reports on the installed sandboxed Parent service;
9. whether exact-current R7 physical evidence can proceed without source drift.

If Alfabeto startup proves materially worse on the Atom floor, do not move waveform synthesis back into the interaction hot path. Prefer a measured follow-up such as pre-generated bounded SFX or another startup-safe cache strategy.

## 7. Architectural lessons to preserve

- Activities consume platform viewport/input ownership; they do not approximate trusted Home locally.
- Performance cleanup must move work to a measured safe location, not merely somewhere else.
- Raw PCM must match the actual runtime mixer format.
- A locale bundle should be the single child-facing string authority for an Activity.
- Root Greia tools should be genuinely reusable; one-off Activity content producers should not accumulate there.
- Production composition should be explicit and fail closed; demo adapters are not appliance fallbacks.
- Capability advertisement describes operations the current authority can actually complete.
- An unprivileged Parent API must stay unprivileged. Add narrow typed privilege behind it when required; do not dissolve the boundary.
- Source tests/reviews are not physical acceptance evidence.
