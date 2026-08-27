# Greia — Current Engineering Handover

**Updated:** 2026-08-27  
**Canonical repository:** `frozenpepper/Greia`  
**Canonical branch:** `main`  
**Primary blocking platform phase:** **R7 — Direct graphics/session/input architecture**  
**Purpose:** short current continuation contract. Detailed chronology belongs in the active plan and dated reviews/handovers.

The previous long-form root handover is preserved verbatim as:

```text
docs/handovers/GREIA_ROOT_HANDOVER_ARCHIVE_2026-08-27.md
```

Git history remains canonical for every earlier root-handover revision.

---

## 1. Resume rules

Before substantive work, read `AGENTS.md`, `README.md`, `docs/DOCUMENTATION.md`, the active architecture plan, this handover, and the relevant OS/Activity/visual/voice skill.

Do not use GitHub-hosted Actions unless the owner explicitly authorizes that specific execution. Work on current `main`; refresh the head before writes and preserve concurrent work.

No current-head PASS may be claimed unless it actually executed on that exact state. Source review, Simulator evidence and physical-device evidence are separate evidence classes.

---

## 2. Platform state

R7 remains the first incomplete blocking platform phase. Current production continues to use the provisional Xorg/xinit compatibility path while direct appliance display/session/input ownership is resolved.

R7 invariants remain:

- Greia owns display/session authority;
- protected Home/Back remain outside Activity rendering/input authority;
- protected system input is intercepted before Activity delivery;
- controller discovery/normalization is platform-owned;
- ordinary Activities do not gain raw `/dev/input` or DRM authority;
- any direct/compositor migration requires exact source, VM and physical legacy-x86 evidence before production acceptance.

Do not interpret later Activity, voice, launcher, achievement or microphone work as R7 closure.

The architecture sequencing and closure criteria remain authoritative in:

```text
docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md
```

---

## 3. Reference Acer / retained accepted evidence

The reference Acer Aspire One remains the low-resource floor. Previously accepted, scope-limited evidence includes:

- launcher hover-transition optimization on physical Acer;
- platform-owned lightweight microphone cleanup on physical Acer;
- multiple first-party Activity performance/interaction tranches;
- boot-contract and boot-screen physical acceptance at their tested source states;
- Il Viaggio del Delfino source/Simulator/Acer work through its latest documented tranche.

Physical evidence applies only to the exact source/tranche measured. Do not generalize historical Acer numbers to newer source.

Canonical performance guidance:

```text
docs/engineering/GREIA_PERFORMANCE_BEST_PRACTICES.md
```

---

## 4. Greia Encyclopedia v0.1 — current parallel Activity workstream

The encyclopedia is one normal first-party Activity:

```text
activities/enciclopedia_greia/
activity id: org.greia.enciclopedia
```

Current frozen source scope:

```text
1 Home
6 section pages
36 factual final entries
-----------------------
43 executable pages
```

Architecture remains intentionally small:

- one thin Activity composition root;
- one tiny subject-neutral page engine;
- sections and entries share the same executable-page lifecycle contract;
- subject-specific state/animation belongs in page modules;
- no generic exhibit DSL, physics engine or deep inheritance hierarchy;
- bounded caches and no reusable asset decode/font construction in page hot paths;
- no runtime TTS, speech recognition, LLM/provider, network fact lookup or voice model;
- narration is prerecorded during authoring and packaged as static audio.

Every factual final entry has a research authority under `encyclopedia/research/` with sources, accepted claims, misconception/scope guardrails, interaction mapping and approved bilingual narration.

The post-build drift review is:

```text
docs/reviews/2026-08-27_ENCYCLOPEDIA_V01_POST_BUILD_DRIFT_REVIEW.md
```

That review found and repaired real closure blockers including:

1. locale audio integration previously emitted the wrong schema; accepted cues now use Greia's canonical `{"path": ...}` object form;
2. the 378-row voice synchronizer originally understood only the newer research narration template; it now supports both historical research generations fail-closed;
3. source tests no longer maintain unnecessary shadow copies of the full research/topic inventory;
4. runtime semantic narration cue identities are guarded against synchronized-ledger drift;
5. encyclopedia audio lookup now catches the typed localization failure rather than arbitrary exceptions;
6. unreviewed recorder staging audio is git-ignored and only accepted runtime copies are shipped.

Current truthful evidence label:

```text
SOURCE-REVIEWED / TESTS-UNEXECUTED / SIMULATOR-UNVERIFIED
```

No consolidated 43-page Simulator pass or physical Acer/Pi acceptance has executed yet.

The checked-in recording queue remains the earlier 176-row snapshot until the synchronizer actually runs locally. Expected synchronized invariant is 378 bilingual rows.

A deterministic bridge now exists at:

```text
encyclopedia/export_voice_batch.py
```

It converts only eligible ledger rows into the repository-wide Voice Production Engine JSONL contract without synthesizing speech or changing status. The Markdown ledger remains the single request/review authority and `OWNER_ACCEPTED` remains the packaging gate.

A fail-closed deterministic pre-Simulator helper also exists at:

```text
tools/encyclopedia_v01_source_gate.py
```

It automates only the source/ledger/accepted-audio part of the canonical acceptance runbook. Its own tests have not yet executed against current source, so the handwritten runbook remains authoritative and no source-gate PASS is claimed.

Exact closure procedure:

```text
docs/testing/GREIA_ENCYCLOPEDIA_V01_CONSOLIDATED_ACCEPTANCE.md
```

Do not add more v0.1 topics before that gate is reviewed. Recording may continue independently; only `OWNER_ACCEPTED` clips may be packaged into runtime resources.

---

## 5. Greia Voice Production Engine — authoring subsystem candidate

A repository-wide provider-neutral authoring-time voice subsystem now exists:

```text
tools/greia_voice.py
tools/greia_voice_core/
docs/architecture/GREIA_VOICE_PRODUCTION_ENGINE.md
skills/greia-voice-production/
```

Its purpose is to hide Chatterbox/native-system/Whisper/mechanical production details behind semantic requests containing speaker, speech kind, locale, reviewed text and cue/output identity.

Important boundary: the subsystem is **authoring-time only** and adds no child-runtime TTS/model dependency.

Current status is still **implementation candidate / local provider acceptance pending**. Existing accepted Activity audio must not be regenerated merely to test it. Human listening remains acceptance authority; Whisper is advisory only.

Exact local finalization procedure is the voice-engine acceptance document committed with the subsystem. Do not switch every historical generator/skill to the new engine until that local provider gate is genuinely green.

The encyclopedia now feeds this engine from its existing ledger through `encyclopedia/export_voice_batch.py`; that adapter is deterministic and provider-free. Actual use of the generated batch still waits for the Voice Production Engine's separate local provider acceptance. Encyclopedia `OWNER_ACCEPTED` packaging remains authoritative even after production is centralized.

---

## 6. Parent / microphone / updates

The external Parent HTML client remains source-pinned/integrity-checked and is not fetched from moving `main` at runtime. Production pairing/encrypted transport remains open; provisional HTTP/bootstrap transport must not be treated as production authorization for privileged mutations.

Platform microphone policy remains:

```text
lightweight cleanup desired by default
advanced cleanup off by default
parent may disable processing
advanced requires explicit parent opt-in and real availability
no automatic model/processor promotion
```

Current x86 system-update layout remains single-root with activation disabled. Signed update foundations do not authorize in-place active-root mutation; A/B/rollback closure remains future platform work.

---

## 7. Immediate next work

### Encyclopedia closure lane

On an owner-controlled local checkout, execute exactly:

```text
docs/testing/GREIA_ENCYCLOPEDIA_V01_CONSOLIDATED_ACCEPTANCE.md
```

The run must first synchronize/check the recording queue, prove the 378-row invariant, execute focused provider-free contracts and `make verify`, then integrate only already-`OWNER_ACCEPTED` clips, and only then perform the deferred real Simulator traversal/input/no-reading/responsive review.

Stop on the first genuine failure and return evidence. Do not repair source inside the acceptance run.

### Voice-engine lane

Execute the dedicated local Voice Production Engine finalization/acceptance protocol on the real production workstation. Preserve existing accepted audio. Do not run concurrent Chatterbox workers and do not promote Whisper output to human acceptance.

### Blocking platform lane

Resume R7 from the first incomplete gate in the active architecture plan. The encyclopedia and voice-engine lanes are parallel workstreams and do not change R7 status.

---

## 8. Non-negotiable continuation reminders

- `main` is canonical unless the owner changes branch policy;
- GitHub is canonical persistence;
- no unauthorized hosted Actions execution or inspection;
- Activity `main.py` remains a bootstrap/composition boundary;
- multiple input paths for one child action converge on one semantic/domain rule;
- child-facing flows remain offline-first and pre-reader friendly;
- ordinary Activities never gain runtime AI/TTS/speech-recognition merely to fill missing content;
- visual/runtime/Activity caches stay bounded with explicit invalidation;
- performance claims require measurement on the claimed execution scope;
- R7 remains open until its own evidence/closure criteria are satisfied.
