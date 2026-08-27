# Greia — Current Engineering Handover

**Updated:** 2026-08-28  
**Canonical repository:** `frozenpepper/Greia`  
**Canonical branch:** `main`  
**Primary blocking platform phase:** **R7 — Direct graphics/session/input architecture**  
**Purpose:** short current continuation contract. Detailed chronology belongs in the active plan and dated reviews/handovers.

The previous long-form root handover is preserved verbatim as:

```text
docs/handovers/GREIA_ROOT_HANDOVER_ARCHIVE_2026-08-27.md
```

Git history remains canonical for earlier root-handover revisions.

---

## 1. Resume rules

Before substantive work, read `AGENTS.md`, `README.md`, `docs/DOCUMENTATION.md`, the active architecture plan, this handover, and the relevant OS/Activity/visual/voice skill.

Do not use GitHub-hosted Actions unless the owner explicitly authorizes that execution. Work on current `main`; refresh the head before writes and preserve concurrent work.

No current-head PASS may be claimed unless it actually executed on that exact state. Source review, local provider/audio review, Simulator evidence and physical-device evidence are separate evidence classes.

---

## 2. Platform state

Triaged on 2026-08-26 (non-closing): retired `tre_carte_una_storia`; shipped two new first-party Activities — `la_discesa_della_biglia` (real 2D marble physics for pre-readers) and `storie_della_mia_voce` (microphone-first pre-reader narrative). First-party manifest count is now **34** (was 33 before `enciclopedia_greia` landed from the encyclopedia workstream). `make verify` was **1,380/1,380 PASS** with both Activities inserted in their alphabetical positions and the retired Activity removed. Voice production for both Activities remains **UNPROVEN** at v1 — placeholder semantic cue ids are shipped, Lilli (for `storie_della_mia_voce`) and Leo (for `la_discesa_della_biglia`) are reserved for a future voice-production pass. The full long-form triage detail lives in the active plan's progress ledger at `docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md`.

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

Current truthful evidence label remains:

```text
SOURCE-REVIEWED / TESTS-UNEXECUTED / SIMULATOR-UNVERIFIED
```

No consolidated 43-page Simulator pass or physical Acer/Pi acceptance has executed yet.

The checked-in recording queue remains the earlier 176-row snapshot until the synchronizer actually runs locally. Expected synchronized invariant is 378 bilingual rows.

Voice production is now explicitly centralized:

```text
VOICE_RECORDING_REQUESTS.md
-> encyclopedia/export_voice_batch.py
-> tools/greia_voice.py batch
-> staging audio + Voice Engine receipts
-> human review / OWNER_ACCEPTED
-> encyclopedia/integrate_voice_assets.py
-> packaged runtime audio
```

The Markdown ledger remains authority for exact text/cues/speaker/status. The Voice Engine owns Chatterbox/native/Whisper/packaging mechanics. Historical direct-backend instructions in old queue prose are superseded by the canonical voice-production skill/README; do not alter immutable voice rows merely to migrate implementation guidance.

A fail-closed deterministic pre-Simulator helper also exists at:

```text
tools/encyclopedia_v01_source_gate.py
```

Its tests have not yet executed against current source, so no source-gate PASS is claimed.

Exact closure procedure:

```text
docs/testing/GREIA_ENCYCLOPEDIA_V01_CONSOLIDATED_ACCEPTANCE.md
```

Do not add more v0.1 topics before that gate is reviewed. Only `OWNER_ACCEPTED` clips may be packaged into runtime resources.

---

## 5. Greia Voice Production Engine — canonical authoring subsystem

The repository-wide authoring-time voice subsystem is now the canonical path for **all new prerecorded Greia speech production**:

```text
tools/greia_voice.py
tools/greia_voice_core/
tools/greia_voice_core/README.md
tools/greia_voice_requirements_mlx.txt
skills/greia-voice-production/SKILL.md
docs/architecture/GREIA_VOICE_PRODUCTION_ENGINE.md
```

Caller-facing semantic contract:

```text
speaker
kind
locale
exact reviewed text
cue/output identity
```

Current kinds:

```text
character_dialogue
shared_character_utterance
pedagogical_speech
dani_system_speech
```

Current implementation routes:

```text
Lilli/Leo/Flash/Tito/Momo character/shared production -> Chatterbox MLX provider
pedagogical pronunciation                            -> macOS native/system provider
Dani Activity/shared production                      -> macOS native/system provider
suitable multi-word natural-character speech         -> optional advisory Whisper check
```

Important boundaries:

- authoring-time only; no child-runtime TTS/model/Whisper dependency;
- canonical reference hashes are checked before cloned generation;
- warm service/batch reuse one model and a cross-process lock prevents a second inference worker;
- no silent placeholder success;
- every receipt says `human_review=PENDING`;
- Whisper may warn/retry but never accepts audio;
- existing owner-accepted historical audio is not regenerated merely to migrate tooling.

### Repository-wide adoption completed in source/docs

The following now point production through the engine rather than teaching backend mechanics:

- `skills/greia-voice-production/SKILL.md` — canonical voice production skill;
- `skills/greia-activity-authoring/VOICE_GENERATION.md` — Activity-facing semantic guidance;
- `SETUP.md` — workstation role/install/readiness routing;
- `docs/design/GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md` — accepted semantic/identity policy;
- `docs/architecture/GREIA_VOICE_PRODUCTION_ENGINE.md` — architecture/provider ownership;
- `docs/agents/GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md` — installation/runbook;
- `docs/agents/GREIA_CHATTERBOX_PRODUCTION_FIELD_GUIDE.md` — now maintainer/troubleshooting only;
- `docs/agents/GREIA_SHARED_CHARACTER_UTTERANCE_RECORDING.md` — shared library through engine;
- `encyclopedia/README.md` — Encyclopedia exporter/batch/review pipeline.

`tools/record_shared_character_utterances.py` has also been migrated from direct MLX/Whisper calls into a thin `VoiceEngine` semantic producer. It now supports all six characters; Dani is routed through the system provider.

All twelve historical Activity-specific `tools/generate_*_audio.py` speech generators have now been migrated away from direct backend ownership as well. Character-hosted Activities submit `character_dialogue`; pronunciation-authoritative letters/syllables/phonemes/words submit `pedagogical_speech`; legacy neutral guidance explicitly names Dani via `dani_system_speech`. Those scripts are thin semantic batch producers for `tools/greia_voice.py`, generate into review workspaces, and no longer load MLX models, reference files, native voice names, FFmpeg/afconvert pipelines, token budgets, accelerator caches, or silent/synthetic fallback audio. Existing packaged reviewed assets are preserved until separately human-reviewed replacements are accepted.

### Installation

Quick install/use:

```text
tools/greia_voice_core/README.md
```

Tested Apple-Silicon dependency declaration:

```text
tools/greia_voice_requirements_mlx.txt
```

Readiness probe:

```bash
python3 tools/greia_voice.py doctor
```

The heavy cloned-character environment remains optional on a general developer machine and must not be silently installed. When actual production is requested and owner-authorized, install it outside Git using the canonical README/setup procedure.

### Evidence status

The canonical routing/docs/code are committed, but the changes in this adoption tranche have **not yet been executed on the owner workstation in this session**. Do not claim current-head focused-test, `make verify`, actual Chatterbox/native/Whisper, or human-listening PASS merely because the code/runbooks exist.

The exact local provider acceptance protocol is:

```text
docs/testing/2026-08-27_GREIA_VOICE_PRODUCTION_LOCAL_ACCEPTANCE.md
```

That protocol now tests the already-canonical engine rather than treating its result as permission to switch documentation later.

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

Build-time prerecorded voice production and runtime child microphone capture are separate systems. `tools/greia_voice.py` must not be introduced into child `audio.basic` capture.

Current x86 system-update layout remains single-root with activation disabled. Signed update foundations do not authorize in-place active-root mutation; A/B/rollback closure remains future platform work.

---

## 7. Immediate next work

### Voice-engine evidence lane

On the owner-controlled production workstation execute exactly:

```text
docs/testing/2026-08-27_GREIA_VOICE_PRODUCTION_LOCAL_ACCEPTANCE.md
```

It must first run the focused provider-free voice tests and `make verify`, then `doctor`, deterministic pedagogical/Dani samples, real Chatterbox + Whisper sample generation, shared-library routing, warm-service/model-reuse and cross-process-lock tests, followed by human listening.

Stop on the first genuine failure. Do not bypass the engine or regenerate existing accepted Activity audio to manufacture evidence.

### Encyclopedia closure lane

Execute:

```text
docs/testing/GREIA_ENCYCLOPEDIA_V01_CONSOLIDATED_ACCEPTANCE.md
```

Synchronize/check the recording queue, prove the 378-row invariant, execute focused provider-free contracts and `make verify`, integrate only already-`OWNER_ACCEPTED` clips, and perform the deferred Simulator traversal/input/no-reading/responsive review.

### Blocking platform lane

Resume R7 from the first incomplete gate in the active architecture plan. Encyclopedia and voice production are parallel workstreams and do not change R7 status.

---

## 8. Non-negotiable continuation reminders

- `main` is canonical unless the owner changes branch policy;
- GitHub is canonical persistence;
- no unauthorized hosted Actions execution or inspection;
- Activity `main.py` remains a bootstrap/composition boundary;
- multiple input paths for one child action converge on one semantic/domain rule;
- child-facing flows remain offline-first and pre-reader friendly;
- ordinary Activities never gain runtime AI/TTS/speech-recognition merely to fill missing content;
- **all new prerecorded voice production goes through the Greia Voice Production Engine**;
- visual/runtime/Activity caches stay bounded with explicit invalidation;
- performance claims require measurement on the claimed execution scope;
- R7 remains open until its own evidence/closure criteria are satisfied.
