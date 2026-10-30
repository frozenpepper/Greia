---
name: greia-voice-production
description: Use when generating, regenerating, reviewing or installing prerecorded Greia speech (character, shared-library, pedagogical, Dani, launcher or Activity voice lines), operating the VoiceEngine/VoxStage/Parakeet pipeline, or maintaining the voice corpus. Authoring-time only; never runtime TTS.
---

# Greia Voice Production

**Status:** canonical authoring-time voice-production contract  
**Reviewed:** 2026-10-30

## When to use / Read first

Use for any new or replacement prerecorded speech, voice-engine maintenance, corpus regeneration/recovery, or automated/human voice review. Not for child microphone recording (`skills/greia-activity-authoring/MICROPHONE_RECORDING.md`) and not for adding a language (`skills/greia-language-expansion/SKILL.md`, which calls back here for the voice step).

Read first:

```text
tools/greia_voice_core/README.md                              practical CLI/JSON/Python entry point, defaults, recovery
docs/design/GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md
docs/architecture/GREIA_VOICE_PRODUCTION_ENGINE.md
```

Then as needed:

```text
docs/agents/GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md      installation/readiness (also SETUP.md §7)
docs/agents/GREIA_AUTOMATED_VOICE_REVIEW.md            post-generation machine screening
docs/agents/GREIA_VOICE_CORPUS_REGENERATION.md         corpus replacement/recovery operations
docs/agents/GREIA_NATURAL_VOICE_COMPLETION.md          natural-carrier completion method
docs/agents/GREIA_SPOKEN_CARRIER_EXTRACTION.md         short-cue carrier extraction
docs/agents/GREIA_CHATTERBOX_PRODUCTION_FIELD_GUIDE.md engine maintainers only
```

For a **new language** begin with `skills/greia-language-expansion/SKILL.md` and `docs/development/ADD_A_GREIA_LANGUAGE.md`. The VoxStage worker and cached Parakeet weights on the owner's workstation are not a reproducible installation on another contributor's machine.

## One rule

All new Greia prerecorded speech goes through:

```text
tools/greia_voice.py
```

Activity, OS/shared-library and content-project agents must not invoke VoxStage, Chatterbox, `mlx_audio`, `mlx_whisper`, macOS `say`, `afconvert`, FFmpeg trimming or canonical reference files directly. Those are implementation details owned by the Voice Production Engine. If an older generator, runbook or queue contains direct backend instructions, treat those production mechanics as superseded; keep the semantic cue/text/acceptance data and submit the speech through the engine.

"Voice Studio" (`SETUP.md` §7) means this VoiceEngine authoring workflow: semantic request → routed provider → optional verification → review audio/receipt → human listening → accepted asset promotion. It is not a separate GUI; do not build another Activity-owned speech producer because an instruction says "studio".

## Standing authority and limits

- EN/IT/ES/FR are all released: every new line is recorded in all four with the same speaker and integrated with `tools/integrate_reviewed_voices.py --layout mirror` (never overwrites). The all-Activity recording order is `docs/plans/2026-10-12_GREIA_FOUR_LANGUAGE_ROLLOUT/LOCAL_AGENT_ALL_APP_VOICE_RECORDING_ORDER.md`; cue identity/legacy inventory is in `LOCAL_AGENT_VOICE_PRODUCTION.md` beside it; the single task queue is `docs/testing/GREIA_LOCAL_AGENT_TASK_QUEUE.md`.
- That authority covers an **already configured, registered, no-new-spend local VoiceEngine provider** and exact current approved scripts in reviewed small batches. It is **not** authority for new paid cloud/Modal spend, heavy downloads, direct backend scripting or unreviewed voice anchors. Install the heavy MLX stack only with explicit owner authorization.
- Owner-approved visible text does not supply an absent long spoken transcript or decide letter-name versus phoneme for preschool content; those stay `BLOCKED_SCRIPT` until a complete script exists.
- Committed recordings are owner-reviewed and accepted: never regenerate them for perceived provenance problems. Replacement of accepted speech happens only inside an explicit owner-authorized corpus operation (below) and yields listening-pending receipts.
- Scoped owner exceptions (for example a native system-voice replacement of specific corpus rows recorded as `verification=NOT_RUN`, `human_review=WAIVED_BY_OWNER`) apply only to the named external run. Ordinary new speech always needs its configured delivered-audio verification and human review.
- Do not add file anti-tampering, signing or elaborate asset verification to voice assets.

## Providers and masters

- Dani, Momo and Tito use the owner-selected **v0.3 cloned masters** (`greia.dani.v3`, `greia.momo.v3`, `greia.tito.v3`); Lilli, Leo and Flash retain their exact v0.2 master IDs and bytes. Active registry: `assets/audio/characters/canonical/v0.3/manifest.toml`; source masters/provenance: `assets/source/audio/character-voice-masters/v0.3/`. The v0.2 registry stays intact as history. Master selection does not accept any later generation.
- VoxCPM2 through the shared local VoxStage worker is the default provider. Chatterbox stays explicitly selectable (`--character-provider chatterbox` on `doctor`/`generate`/`batch`/`serve`, or `GREIA_VOICE_CHARACTER_PROVIDER=chatterbox`); unload the VoxStage model before switching on the same host. There is no silent fallback when the selected backend is unavailable.
- Start/reuse the worker with `voxstage start`, then run `python3 tools/greia_voice.py doctor`. Model installation needs explicit authorization. The adapter reuses/imports exact registry references on a fresh worker, never replaces an existing voice ID and never starts a second MLX process. The shared worker owns warm-model lifecycle: run `voxstage unload` only when the worker is idle and your session is finished. Never restart the shared worker or repeat an uncertain POST.
- Loopback integration: `GREIA_VOXSTAGE_URL` (default `http://127.0.0.1:8791`); job wait bounded by `GREIA_VOXSTAGE_TIMEOUT` (default 1,800 s; a timeout does not cancel the external job, so record the job ID and inspect it before resubmitting); HTTP response timeout `GREIA_VOXSTAGE_HTTP_TIMEOUT` (default 120 s, up to 7,200); `request --timeout` bounds the warm-service response (default 3,600 s).
- `dani_system_speech` clones Dani's selected master; Dani can also use `character_dialogue`. Pedagogical pronunciation keeps the independent native/system route. VoxCPM2 language direction is probabilistic (no hard language selector), so every clip needs listening review.

### Identity versus acting

Pitch/register, voice age, timbre and permanent character traits belong only in the master voice design. Do not repeat them in a recording's `delivery_prompt`. Defaults for all six characters are the same warm, calm, clear reading with careful natural pronunciation (`tools/greia_voice_core/character_delivery.json`; VoxStage applies them to normal generation too). Add line-specific intention/emotion/pace only when needed, via `VoiceRequest.delivery_prompt`, CLI `--delivery-prompt` or the batch/service field. Acting instructions stay separate from the exact spoken text; receipts keep the supplied prompt and the provider's effective direction. Chatterbox/native reject unsupported explicit direction rather than ignoring it. Do not reuse the retired persona-prefixed prompt overrides for a replacement run.

## Semantic input and routing

Every generated cue needs speaker, kind, locale, exact reviewed text, cue ID (strongly preferred) and an output path when the destination is known. Kinds: `character_dialogue`, `shared_character_utterance`, `pedagogical_speech`, `dani_system_speech`. The caller chooses semantic purpose, never backend/model.

```text
Lilli/Leo/Flash/Tito/Momo/Dani + character_dialogue -> canonical cloned-character provider
shared_character_utterance  -> Greia's central reviewed shared library; cloned provider for all six
pedagogical_speech          -> deterministic native/system provider; speaker must be pedagogical or system
Dani + dani_system_speech   -> selected Dani cloned-character provider
```

At runtime Activities never synthesize `shared_character_utterance`; they resolve reviewed static shared assets through the runtime resolver. Do not infer `pedagogical_speech` from short text (`Vai!` may be dialogue; `ma` may be a teaching target).

Semantic-speaker rule: ordinary guidance uses a real presenter route, not `pedagogical_speech`:

```text
Leo welcome/instruction -> character_dialogue
Dani instruction        -> dani_system_speech
generic praise          -> shared_character_utterance when the resolver supports it
exact letter/syllable   -> pedagogical_speech
```

Before generating shared speech, audit `assets/audio/characters/shared/v0.2/` (its `manifest.toml` and `review.csv`) and `docs/design/GREIA_SHARED_CHARACTER_UTTERANCES.md`; do not infer current acceptance from historical counts. Reusing accepted bytes, missing playback wiring and genuinely missing audio are separate ledger states.

## Packaging and footprint

`VoiceEngine` delegates WAV checks and output packaging to `AudioPipeline`: 22,050 Hz mono, WAV PCM16, OGG Vorbis quality 5 by default; maintainers may pass a bounded `ogg_quality` (0–10) to `AudioPipeline` for an explicit footprint constraint. Retain output hashes in receipts. Never invoke FFmpeg from corpus or Activity code to work around a bound.

## Installation / readiness

The engine source ships in the repository; the heavy MLX production environment lives outside Git. Start with `python3 tools/greia_voice.py doctor`; full Apple-Silicon setup is `tools/greia_voice_core/README.md` with the tested dependency set `tools/greia_voice_requirements_mlx.txt`. Use the explicit prepared Greia venv interpreter from `SETUP.md` §7.5 (the global Anaconda Python has an unrelated NumPy/Numba ABI mismatch). Do not silently install or download a multi-GB stack.

## Generate

```bash
python3 tools/greia_voice.py generate --speaker leo --kind character_dialogue --locale it \
  --text "Guardiamo con calma." --cue-id presenter.hint \
  --output /tmp/greia-voice-review/presenter-hint.wav

python3 tools/greia_voice.py generate --speaker pedagogical --kind pedagogical_speech \
  --locale it --text "ma" --cue-id phonics.ma --verification off \
  --output /tmp/greia-voice-review/ma.wav
```

Generate into review staging, never directly into final runtime assets. For repeated work run one warm worker (`python3 tools/greia_voice.py serve`) and use `request`, or `batch` for JSONL queues. Never launch concurrent raw model workers; VoxStage owns one serialized worker and the engine owns the cross-process generation lock.

**Chatterbox length policy:** for `character_dialogue` and natural-character `shared_character_utterance`, never derive `max_new_tokens` from word count (acoustic-token length is not predictable and short-prompt caps caused truncation). Letters/syllables route through `pedagogical_speech` and do not justify a cap. Do not reintroduce a word-count token table in callers or providers.

## Short cues, verification and comparison policy

- Normal VoxStage character requests with fewer than five words (including Dani and single words) auto-route through the localized carrier → target-only cut → final Parakeet check (`short_text_mode=auto`, `short_text_max_words=4`, three total takes). Override via CLI/JSON/Python; native pedagogical speech stays excluded; Chatterbox keeps its ordinary route. Explicit corpus raw synthesis uses `short_text_mode=off` to avoid double wrapping.
- Extraction: `tools/voice_carrier.py` / `tools/voice_carrier_search.py` (current v7) generate carrier plus target as one request, keep the raw carrier WAV and receipt, ignore the disposable intro (no raw-intro ASR), and use PCM-first bounded suffix candidates with exactly one target-only match, then cut at a measured low-energy gap. Reject any unidentifiable/ambiguous target, malformed timing, missing clean pause, ambiguous boundary or too little voiced signal (the `warn` corpus policy still requires an identifiable suffix, timing, unique gap and ≥80 ms voiced signal). Never transcribe the removed intro to accept a cut. Normal intros end with a period, not an ellipsis (`period-separated-intro-v1`).
- Verifier: new requests use the cached local multilingual Parakeet-TDT v3 (`mlx-community/parakeet-tdt-0.6b-v3`, revision `ed2b7e8c15f9aaa0b5772e2efb986255eaef7e15`, from `tools/greia_voice_core/parakeet_asr.py`). Missing model/dependencies are reported; the engine never downloads weights or falls back to Whisper silently. Historical reports keep their recorded verifier (Whisper Base/Tiny); never reinterpret or re-score old evidence.
- Pass rule: similarity > 0.8, equal canonical unit count, identical numeric sequence (locale cardinals/digits 0–100 are equivalent), and the signal checks clear. Comparison policy `locale-number-tokens-v3-chck-orthographic` (locale cardinals/literals first, then lexical `ch`/`c`/`k` canonicalized to `k`; submitted phrase and exact transcript retained). Registered corpus jobs carry their own frozen policy ID; never rewrite a registered plan to a newer default. Diacritics are ignored only during ASR comparison (`ignore_accents=True` default; `--strict-accents` / `"ignore_accents": false` / `ignore_accents=False` restore strict).
- `verification=off` is explicitly unverified, not a machine PASS. ASR/IO failures require recovery and must not spend a fresh take. Inspect each result's `disposition`, `verification` and receipt (`result.evidence_dir`), not exit status or error prose.
- Parakeet is a screening gate: PASS = transcript plausibly matches (still needs human review); WARN = unresolved candidate, inspect/regenerate. Never use ASR as pronunciation authority for letters, syllables or phonics.

## Automated review and human listening

After corpus generation follow `docs/agents/GREIA_AUTOMATED_VOICE_REVIEW.md`: `tools/regenerate_voice_corpus.py review --work-dir <external-run> --report-dir <separate-external-reports> --asr auto`. It reads installed files and the frozen plan, checks metadata/decoding/signal metrics, runs eligible ASR only with already installed/cached dependencies, and writes resumable reports plus a prioritized listening queue. It never changes audio, receipts, plans or acceptance and never downloads models. Missing ASR is BLOCKED; `--asr off` is incomplete screening, not PASS. Dani, short utterances, teaching targets and long scripts keep explicit ASR exclusions; identity, acting, pronunciation and language recognition remain unassessed. Current screening policy (`greia-audio-screen-v3`): silence/score thresholds as v2, diacritics ignored, trailing silence/internal pauses warn at ≥ 1.5 s, ASR PASS needs similarity > 0.8. `reassess --evidence-dir <finished-report>` reapplies policy to saved evidence without another ASR run (use a fresh report directory); procedure §3a of the review doc.

Human listening uses the shared `takeboard` tool (its own skill/README; HTML comparison, 1–5 scores, notes, JSON export). Greia's thin adapter is `tools/export_voice_review_batch.py` (commands in `docs/agents/GREIA_AUTOMATED_VOICE_REVIEW.md` §6); keep its manifests external. Machine findings never initialize human acceptance; importing takeboard decisions into receipts/runtime is a separate task.

**Acceptance:** every successful generation stays `human_review = PENDING` until a person listens (exact words, locale, character identity, pronunciation, clipping/tails, delivery, small-speaker suitability). A process exit, receipt, valid audio container or Parakeet PASS is never final acceptance. Keep generation DONE, automated coverage and human acceptance as separate evidence states.

## Project-specific producer rule

A project may have a thin helper that assembles many semantic VoiceEngine requests. It lives inside the project that owns the cues (`activities/<id>/tools/generate_voice_requests.py`, `build_voice_batch.py`, `<other-project>/tools/...`), not in repository root `tools/` (reserved for Greia-wide tooling such as the VoiceEngine and central shared-library producers). It may own only semantic cue IDs, exact reviewed localized text, speaker/kind assignment, review-output naming and thin JSONL/batch assembly. It must not own VoxStage/Chatterbox/MLX imports or model IDs, canonical reference paths/hashes, native voice names/rates or `say`/`afconvert`, Whisper calls, FFmpeg policy, token budgets/retries/accelerator lifecycle, or silent/synthetic placeholder audio on failure.

`activities/<id>/` is also package content: remove one-shot producers, temporary JSONL queues, receipts and scratch files before package acceptance so authoring machinery never ships. Promote a helper to a stable shared tool deliberately if it becomes useful across projects. Existing owner-accepted audio need not be regenerated merely because its historical generator predates the engine.

## Maintainer extension rule

New synthesis systems implement the provider contract behind `VoiceEngine`. Never spread model/backend conditionals into Activities, content projects, OS/shared-library scripts or skills. The saved-WAV contextual seam (`PackagedCandidateVerifier` in `voice_carrier_search.extract`, optional `TargetQualityChecker(context_checker=...)`) is disabled in normal production; read the core README's saved-WAV section before experimenting, never bypass its source/observation checks, and never infer live yield from unit tests or saved-audio screening.

## Corpus operations (replacement, recovery, held producers)

The owner-authorized corpus replacement runs through `tools/regenerate_voice_corpus.py` under `docs/agents/GREIA_VOICE_CORPUS_REGENERATION.md`: frozen requests, serial production through the same VoiceEngine, explicit metadata blockers, recoverable originals (external backups) and pending-review receipts. It is an exception to the add-only importer, which must not be used for new unlistened takes. Deterministic isolated letters/syllables are preserved. The v0.3 replacement is complete; exact counts, scope and listening state are in `HANDOVER.md` and the run's external reports.

Rules that outlive each run:

- Never silently resume a frozen plan with a changed extraction/comparison algorithm; each retry freezes its own version and keeps cumulative budgets (three fresh generations per cue in total; saved provider sources are tried before fresh synthesis).
- `tools/finish_voice_priority.py` and `tools/continue_voice_priority_v7.py` wrap the normal engine through CorpusRunner (which owns last-take reservation and installation); known quality exhaustion preserves originals; unknown provider/ASR/IO outcomes stop as NEEDS_RECOVERY.
- `tools/recover_voice_candidates.py` is the no-synthesis saved-source adapter (stage, then `--install` the same completed external folder; `--source-selection <index.json>` pins historical rows). It has no provider/fresh mode, cannot disable count/numeric/signal checks, cannot reset budgets, and installs only through CorpusRunner/RunStore with `human_review=PENDING`. Unknown provenance or uncertain journal states are blockers.
- The 667-cue priority producers, `natural-context-v1` and `natural-context-speech-v1` were stopped or held for poor yield: do not restart or duplicate them, and do not launch an old v4 producer. A failed prompt experiment never authorizes a blind bulk continuation; a small diagnostic result implies no bulk restart or threshold relaxation. Bounded diagnostics and any new run need explicit owner authorization and a separately versioned plan.
- Saved replay candidates and external listening batches are not installed or human-approved. Installed new-method clips stay listening-pending until a person accepts them.
- Do not claim a failed experimental gate passed; keep historical plans, receipts and comparison-policy IDs immutable.
