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

### 2026-08-28 — Owner-workstation clean reinstall + per-OS install sections

Source HEAD `b0ae7e8` (post-`b0ae7e8` cherry-pick). On owner `darwin arm64` (M1) machine the earlier chatterbox install had fallen into a broken state under the system Anaconda Python (`mlx_audio.tts.load` import collision with the new MLX provider API), `mlx-whisper` was missing entirely, and the legacy cache lived at `~/Library/Caches/greia/voice-production` (the lowercase path) instead of the canonical `~/Library/Caches/Greia/voice-production` macOS-specified path. Owner asked to delete the existing install to reclaim disk space, then follow the engine README; OS-specific guidance was previously collapsed into a one-line "Other hosts: UNAVAILABLE" so the docs were also corrected to add explicit `§12.1 Apple Silicon`, `§12.2 Intel macOS`, `§12.3 Linux`, `§12.4 Windows` sections and a hard rule prohibiting Activity-side `say`/`espeak`/`Add-Type` shortcuts to flip providers green.

Actions and evidence on this same checkout:

- Cleared `~/Library/Application Support/Greia/voice-production/venv` (1.1 GB) and `~/Library/Caches/greia/voice-production` (3.0 GB; same inode as the new path on case-insensitive HFS). Net **4.1 GB freed**. Subsequent full Apple-Silicon install + first-generation model download lands at **1.1 GB venv + 3.6 GB HF cache** (`mlx-community/chatterbox-multilingual-v3` weights + tokenizer; `mlx-community/whisper-tiny` is colocated).
- Recreated the venv with `uv venv --python 3.12` and installed `tools/greia_voice_requirements_mlx.txt` via `uv pip install --python …`. Provider `chatterbox-mlx-multilingual-v3==0.5.0`, `mlx==0.32.1`, `mlx-whisper==0.4.3`, `soundfile==0.14.0`, `sentencepiece==0.2.2`. Pinned in source at `tools/greia_voice_requirements_mlx.txt`; unchanged in this session.
- `python tools/greia_voice.py doctor` (run through the new venv): `anchors all ok: True` (Lilli, Leo, Flash, Tito, Momo); `provider chatterbox-mlx-multilingual-v3 -> OK`; `provider macos-native-say -> OK`; `verifier mlx-whisper-tiny -> OK`; `ffmpeg: OK`. `native-system-unavailable` stays `UNAVAILABLE` on macOS, by design (the slot exists so Linux/Windows can flip it green later via a real provider).
- Smoke test through the engine on this commit:
  - `python tools/greia_voice.py generate --speaker leo --kind character_dialogue --locale it --text "Guardiamo con calma." --cue-id smoke.leo --output …/smoke/leo.ogg` → 14.1 KB OGG; receipt shows `provider: chatterbox-mlx-multilingual-v3`, `verification: PASS` from `mlx-whisper-tiny` with `transcript: "Guardiamo con calma."` (exact match).
  - `… --speaker pedagogical --kind pedagogical_speech --locale it --text "ma" --cue-id smoke.phonics.ma --verification off --output …/smoke/ma.wav` → 11.2 KB WAV; `provider: macos-native-say`; ASR intentionally skipped for this class.
  - `… --speaker dani --kind dani_system_speech --locale it --text "Schema completato!" --cue-id smoke.dani --output …/smoke/dani.ogg` → 13.1 KB OGG; `provider: macos-native-say`; ASR intentionally skipped.
- Three smoke clips + three receipts are in `~/Library/Application Support/Greia/voice-production/smoke/`. Human listening review still required before any of these get marked `human_review = ACCEPTED`.
- Updates in this session: `docs/agents/GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md` §12 split into `12.1…12.4` per OS with explicit env vars and package commands (`brew` / `apt-get` / `dnf` / `pacman` / `winget`); `tools/greia_voice_core/README.md` §3 mirrors the same per-host stance; cross-reference added in `§13 Hard rule across all hosts` forbidding Activity-side `say`/`espeak`/`Add-Type` shortcuts.

Outstanding: full local acceptance runbook still pending — `docs/testing/2026-08-27_GREIA_VOICE_PRODUCTION_LOCAL_ACCEPTANCE.md` covers the same providers this session confirmed, but a structured pass (warm service + batch + cross-process lock check + listening review) has not been executed. R7 remains the blocking platform phase. The owner's narrow ask was: delete the previous install, follow the README, and add Linux/Windows sections; that scope is complete on this commit and no further voice or model work was claimed.

### 2026-08-28 — Voice engine memory-growth mitigations + measurement probe

Owner memory of the previous direct-Chatterbox workflow: each generation visibly grew RSS in the running Python. That was the dropped `d4bebd6` script path, not the canonical `tools/greia_voice.py` engine. Investigation on this commit (`b0ae7e8` + follow-ups) on Apple-Silicon macOS confirmed the engine already uses one long-lived model instance per process and a cross-process generation lock, so the architectural footgun is closed at the engine level — but the lazy `mlx_audio` autoregressive path was still leaking per-call Metal buffers through the `model.generate(...)` Python generator. Patch applied (in `tools/greia_voice_core/providers.py` only):

- `provider.probe()` result is now cached on the provider instance (it was re-importing `mlx.core`/`mlx_audio.tts.load`/`soundfile` on every `engine.generate(...)` call).
- `model.generate(...)` is a Python generator; we now `next()` once, **materialize the audio tensor with `mx.eval(result.audio)`**, then `generator.close()` and `del generator, result, audio_tensor, cleaned` in the same `finally:` so the lazy MLX graph is dropped before `gc.collect()` runs.
- `gc.freeze()` is applied at first model load and the freeze is reversed on `provider.close()`. Per-call `gc.collect(2)` is used (full collection) once the model is frozen, so the warm weights stay out of GC re-scans.
- `_load_model` + `close` stay explicit; the provider deliberately has no `__del__` to avoid CPython teardown-order ambiguity — engine lifecycle remains `VoiceEngine.close()` only.

Measurement on this commit with the new `tools/measure_voice_memory_growth.py` (in-process engine, 3 calls, 2 characters, cheap line, verifier disabled to isolate MLX behaviour):

```text
baseline RSS                          :  22.59 MiB
after request 1 (lilli, model load)  : 769.06 MiB   (+746.47)
after request 2 (leo, warm)          : 769.06 MiB   (   +0.00)
after request 3 (lilli, warm)        : 769.06 MiB   (   +0.00)
```

The warm engine is **flat** at ~770 MiB RSS; there is no per-call accumulation. The same MLX provider in a fresh Python subprocess (`python tools/greia_voice.py generate` ×3) is the previous anti-pattern and produces peak RSS of **1852 MiB → 2615 MiB → 2869 MiB** (`/usr/bin/time -l`), because each subprocess re-loads the model + tokenizer from scratch. The engine's `serve` and `batch` paths already route that to a single long-lived process; the anti-pattern is "shell-loop calling `generate` per request", and the cross-process lock prevents two such loops from running at once.

Important honesty:

- `getrusage(RUSAGE_SELF).ru_maxrss` reports only what this process logically owns at sample time. macOS Activity Monitor may show ~3 GB because Metal's unified-memory pool counts GPU/CPU pages together; both views are correct, they measure different things.
- The `native-system-unavailable` provider remains unavailable on macOS by design (slot reserved for a future Linux/Windows provider per §12 README/install docs).
- Doctor and the post-edit smoke tests (`pedagogical_speech ma`, `dani_system_speech Schema completato!`) both still pass; the engine itself was not regressed.
- Total scope of this entry: 1 provider file edited + 1 probe script added; no Activity, OS, RFQ/backpack or child-runtime path touched. R7 remains the blocking platform phase.

The probe can be re-run any time:

```bash
"${GREIA_VOICE_HOME}/venv/bin/python" tools/measure_voice_memory_growth.py \
    --requests 8 --speakers lilli,leo,flash,tito,momo --output \
    "${GREIA_VOICE_HOME}/memory-probe/report.md"
```

Headline output (`headline: total growth`, `peak growth`) is the hot-path growth across N requests. The script intentionally disables the verifier (Whisper) because that loads a second multi-GB model and would mask the speaker/MLX behaviour we want to isolate.

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
