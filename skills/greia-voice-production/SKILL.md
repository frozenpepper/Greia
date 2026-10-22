---
name: greia-voice-production
description: Canonical Greia authoring skill for producing prerecorded character, shared-library, pedagogical and Dani speech. Use for generation, installation/readiness, batch/service operation and voice-engine maintenance.
---

# Greia Voice Production

**Status:** canonical authoring-time voice-production contract  
**Reviewed:** 2026-10-22

## One rule

All new Greia prerecorded speech production goes through:

```text
tools/greia_voice.py
```

Activity, OS/shared-library and content-project agents must not invoke VoxStage, Chatterbox, `mlx_audio`, `mlx_whisper`, macOS `say`, `afconvert`, FFmpeg trimming or canonical reference files directly. Those are implementation details owned by the Voice Production Engine.

If an older project generator, runbook or queue contains direct backend instructions, treat those **production mechanics as superseded** by this skill. Preserve useful semantic cue/text/acceptance data, but submit speech through the engine.

Read first:

```text
tools/greia_voice_core/README.md
docs/design/GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md
docs/architecture/GREIA_VOICE_PRODUCTION_ENGINE.md
```

For installation/readiness work also read:

```text
docs/agents/GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md
```

Only engine maintainers/troubleshooters should normally read:

```text
docs/agents/GREIA_CHATTERBOX_PRODUCTION_FIELD_GUIDE.md
```

## 2026-10-14 owner-approved four-language all-Activity recording task

The owner approved **all currently authored EN/IT/ES/FR text
translations** for voice recording and explicitly requested that the
local agent inspect **all 45 Activities plus shared OS/Parent/Creations,
Encyclopedia and incubated voice surfaces**, then actually record each
missing clip. The executable sequence is
`docs/plans/2026-10-12_GREIA_FOUR_LANGUAGE_ROLLOUT/LOCAL_AGENT_ALL_APP_VOICE_RECORDING_ORDER.md`.
The detailed cue identity and per-Activity legacy inventory remain in
`LOCAL_AGENT_VOICE_PRODUCTION.md` beside that work order, and the
single task queue remains `docs/testing/GREIA_LOCAL_AGENT_TASK_QUEUE.md`.

This is explicit authority to use an **already configured, registered,
no-new-spend local VoiceEngine provider** for exact current approved
scripts in reviewed small batches; it is *not* authority for new paid
cloud/Modal spend, heavy downloads, direct backend scripting, or
unreviewed voice anchors. Owner-approved visible text does not fill in
an absent long spoken transcript or decide preschool letter-name
versus phoneme; those are `BLOCKED_SCRIPT` cue rows pending a complete
script. EN/IT/ES/FR are all released (2026-10-17): every new line is
recorded in all four with the same speaker, and integrated with
`tools/integrate_reviewed_voices.py --layout mirror` (never overwrites).

## Voice Studio identity and existing owner-approved assets

`SETUP.md` §7 and `docs/design/GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md`
§1 explicitly define **Voice Studio as the VoiceEngine authoring
workflow**: semantic request → routed provider → optional verification
→ review audio/receipt → human listening → accepted asset promotion.
It is not automatically a separate GUI. The public production
surface is `tools/greia_voice.py` (`generate`, `batch`,
`serve`/`request`); do not build another Activity-owned speech
producer because an instruction uses the term “studio”.

Before generating shared voice speech, audit the current
`assets/audio/characters/shared/v0.2/` catalogue, its `manifest.toml` and
`review.csv`; do not infer current acceptance from historical counts. Before the
v3 corpus replacement, 192 shared EN/IT recordings (180 reactions and 12
introductions) had owner-approved state. The owner-authorized v3 scope replaced
the Dani/Momo/Tito entries selected by its frozen 1,340-cue plan, and those new
receipts are PENDING; Lilli/Leo/Flash entries remain unchanged. The external v3
run backups retain the overwritten bytes and receipts. Reusing currently
accepted bytes, missing playback wiring and actually missing voice audio are
separate ledger states. See
`docs/design/GREIA_SHARED_CHARACTER_UTTERANCES.md` and HANDOVER.

## Current selected provider and masters — v0.3 promotion on 2026-10-21

Dani, Momo and Tito use owner-selected **v0.3 cloned masters**; Lilli, Leo and
Flash retain their exact v0.2 master IDs and bytes. VoxCPM2 through the existing shared local VoxStage worker is the default
VoiceEngine provider. Chatterbox remains explicitly selectable through
`--character-provider chatterbox` on `doctor`/`generate`/`batch`/`serve`, or
`GREIA_VOICE_CHARACTER_PROVIDER=chatterbox` for repository producers. No silent
fallback occurs when the selected backend is unavailable.

Start/reuse the installed service with `voxstage start`, then run the Greia
`doctor`. Model installation still needs explicit authorization. The adapter
reuses/imports exact registry references on a fresh local worker, never replaces
an existing voice ID, and does not start a second MLX process. The shared worker
owns warm-model lifecycle: finish with `voxstage unload`; closing Greia leaves
other projects' worker intact. Chatterbox is a retained alternative; unload the
VoxStage model before switching to it on the same host.

Active registry: `assets/audio/characters/canonical/v0.3/manifest.toml`.
Active source masters/provenance: `assets/source/audio/character-voice-masters/v0.3/`.
The v0.2 canonical master registry and localized comparison evidence remain
historical. No v0.3 multilingual cloned-line comparison is claimed as accepted.
Master selection does not accept future generations; new corpus takes remain
listening-pending.

**Scoped owner authorization (2026-10-19; v0.3 continuation 2026-10-21):**
the owner explicitly requested replacement of existing Activity/system
recordings using these new masters, except deterministic isolated
letters/syllables, and a tone/mood prompt
for every recording. Execute `tools/regenerate_voice_corpus.py` under
`docs/agents/GREIA_VOICE_CORPUS_REGENERATION.md`. This is the authorized exception
to older preservation instructions for this corpus operation. It uses the same
VoiceEngine, serial production, frozen requests, explicit metadata blockers,
backups/recovery and pending-review receipts. Do not use the add-only approved
asset importer for new unlistened takes. The v2 run used its selected v0.2
masters; the separately frozen v3 run used the exact owner-selected v0.3
masters documented below.

**Owner clarification 2026-10-21 — identity versus acting:** pitch/register,
voice age, timbre/texture and permanent character vocal traits belong only in
master voice design. Do not repeat these in each recording's delivery_prompt.
Defaults for all six characters are now the same warm, calm, clear reading
with careful natural pronunciation (owner update2026-10-22). Only add line-specific intention/emotion/pace when needed. The
completed v2 corpus's frozen prompts and receipts remain historical evidence;
its old PERSONA-prefixed overrides must not be reused for the next replacement.
The original Dani/Momo/Tito voices were rejected for high pitch, inconsistent
Momo, overexcited delivery and hyperactive/aged Tito.

**Owner selection and promotion 2026-10-21:** Momo v3 candidate 1, Tito v3
candidate 1 and Dani v5 candidate 2 are selected. Their immutable VoxStage IDs
are `greia-audition-20261021-momo-v3-01`,
`greia-audition-20261021-tito-v3-01` and
`greia-audition-20261021-dani-v5-02`. Exact hashes, saved approvals, source WAVs
and provenance are archived under `assets/source/audio/character-voice-masters/v0.3/`;
active semantic IDs are `greia.momo.v3`, `greia.tito.v3` and `greia.dani.v3`.
Lilli, Leo and Flash remain byte-for-byte and ID-for-ID unchanged from v0.2.
Dani v5 candidates 01/03 are rejected. The active canonical master registry is
`assets/audio/characters/canonical/v0.3/manifest.toml`; the v0.2 master registry
remains intact. Existing shared utterance paths retain their `shared/v0.2`
filenames; selected rows included in the frozen v3 scope now carry v3 recordings
with pending receipts, while original bytes/receipts remain in external backups.
Source-master approval does not approve fresh runtime generations or localized
cloned lines. The scoped v3 replacement then completed 1,340 DONE / 3,575
PRESERVED with no unresolved rows. Its full policy-v2 automated screen covered
all 1,340 (1,115 PASS / 225 WARN / no FAIL or BLOCKED; 533 ASR policy
exclusions); every new receipt remains `human_review=PENDING`. Full report and
Takeboard batch are external in
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-21-corpus-v3/`. Owner
listening is still required across the entire batch.

Character performance defaults live in
`tools/greia_voice_core/character_delivery.json`; VoxStage applies them to normal
generation too. `VoiceRequest.delivery_prompt`, CLI `--delivery-prompt`, and the
batch/service field override the default for one cue. Acting instructions stay
separate from the exact spoken text. Receipts retain the supplied prompt and
the provider's actual effective language/delivery direction. Chatterbox/native
reject explicit unsupported direction instead of silently ignoring it.

`dani_system_speech` remains compatible and now clones Dani's selected master;
Dani can also use `character_dialogue`. Pedagogical pronunciation retains the
independent native/system route. VoxCPM2 language direction is probabilistic;
there is no hard language selector. Every new clip still needs listening review.

The default integration uses loopback HTTP (`GREIA_VOXSTAGE_URL`, default
`http://127.0.0.1:8791`). A job wait is bounded by `GREIA_VOXSTAGE_TIMEOUT`
(default 1,800 seconds); timeout does not cancel an external job. Preserve the
reported ID and inspect it before resubmitting. `request --timeout` separately
bounds the warm-service response (default 3,600 seconds).

## Semantic input

Every generated cue needs:

```text
speaker
kind
locale
exact reviewed text
cue ID (strongly preferred)
output path when the destination is known
```

Kinds:

```text
character_dialogue
shared_character_utterance
pedagogical_speech
dani_system_speech
```

The caller chooses semantic purpose, never backend/model.

Routing:

```text
Lilli/Leo/Flash/Tito/Momo/Dani + character_dialogue
    -> canonical cloned-character provider

shared_character_utterance
    -> production of Greia's central reviewed shared library
    -> cloned provider for all six characters

pedagogical_speech
    -> deterministic native/system provider
    -> speaker must be pedagogical or system

Dani + dani_system_speech
    -> selected Dani cloned-character provider
```

At runtime, Activities never synthesize `shared_character_utterance`; they resolve reviewed static Greia shared assets through the current runtime resolver.

Do not infer `pedagogical_speech` from short text. `Vai!` may be character dialogue; `ma` may be a teaching target.

## Packaging and footprint

`VoiceEngine` delegates WAV checks and output packaging to `AudioPipeline`.
Outputs are 22,050 Hz mono; WAV uses PCM16 and OGG uses Vorbis quality 5 by
default. Engine maintainers may pass a bounded `ogg_quality` value from 0 to 10
to `AudioPipeline` for an explicit corpus package-footprint constraint. Keep
that choice inside the shared pipeline, retain output hashes in receipts, and
leave every new recording `human_review=PENDING` until a person listens. Do not
invoke FFmpeg directly from corpus or Activity code to work around the bound.

## Installation / readiness

The engine source ships in the repository. The optional heavy MLX production environment lives outside Git.

Start with:

```bash
python3 tools/greia_voice.py doctor
```

For full Apple-Silicon setup follow:

```text
tools/greia_voice_core/README.md
```

The tested dependency set is:

```text
tools/greia_voice_requirements_mlx.txt
```

Do not silently install/download a multi-GB production stack merely because optional speech might be useful. If actual production is requested and the environment is absent, install only with owner authorization using the canonical setup procedure.

## Generate one line

```bash
python3 tools/greia_voice.py generate \
  --speaker leo \
  --kind character_dialogue \
  --locale it \
  --text "Guardiamo con calma." \
  --cue-id presenter.hint \
  --output /tmp/greia-voice-review/presenter-hint.wav
```

Pedagogical example:

```bash
python3 tools/greia_voice.py generate \
  --speaker pedagogical \
  --kind pedagogical_speech \
  --locale it \
  --text "ma" \
  --cue-id phonics.ma \
  --verification off \
  --output /tmp/greia-voice-review/ma.wav
```

Generate into review staging, not directly into final runtime assets.

## Repeated generation

Prefer one warm worker:

```bash
python3 tools/greia_voice.py serve
```

Then use `request`, or use `batch` for JSONL queues. Never launch concurrent raw model workers. VoxStage owns one serialized shared worker; Chatterbox remains in-process when explicitly selected. The engine owns the cross-process generation lock.

## Chatterbox output-length policy

For `character_dialogue` and natural-character `shared_character_utterance`, Greia must **not derive `max_new_tokens` from text word count**. Chatterbox acoustic-token length is not predictable from a simple words→tokens formula, and earlier short-prompt caps caused truncation.

Letters/syllables/phonics do not justify such a cap because they route through `pedagogical_speech`.

Do not reintroduce a guessed word-count token table in callers or providers.

## Post-generation automated review (2026-10-21)

Follow `docs/agents/GREIA_AUTOMATED_VOICE_REVIEW.md` after corpus generation.
Use the explicit prepared Greia venv interpreter from SETUP §7.5; the global
Anaconda Python has an unrelated NumPy/Numba ABI mismatch. Whisper and cached
multilingual Base weights are cached in the prepared environment (default since
2026-10-22); Tiny is retained for historical comparisons.
Use `tools/regenerate_voice_corpus.py review --work-dir <external-run>
--report-dir <separate-external-reports> --asr auto`. It reads installed files
and the frozen plan, checks metadata/decoding/signal metrics, runs existing
eligible ASR only with already installed/cached dependencies, and creates
resumable reports plus a prioritized listening queue. It never changes audio,
receipts, plan, generation state or acceptance, and never downloads models.
Missing ASR is BLOCKED; `--asr off` is incomplete speech review, not PASS.
Dani/short utterances/teaching targets/long scripts retain explicit eligibility
exclusions. Identity, acting, pronunciation and independent language recognition
remain unassessed. The legacy receipt-score audit does not run ASR or audio
analysis. Generation complete, automated review and human listening are separate
evidence states. Review exit 0 never accepts a recording.

## Short spoken-carrier extraction experiment (2026-10-21)

Use `tools/voice_carrier.py` through the bounded short-cue pipeline documented in
`docs/agents/GREIA_SPOKEN_CARRIER_EXTRACTION.md`. Generate carrier plus target
as one VoiceEngine request; preserve the raw carrier WAV and provider receipt.
The extractor accepts mono PCM16 WAV up to 120 seconds, ignores disposable intro wording, locates the final target suffix with valid word timings, then requires one independently measured
low-energy PCM gap before making a deterministic sample cut. The default target
policy is `required` and checks exact target transcripts. The explicit corpus
policy `warn` still requires an identifiable target suffix, timing, unique-gap and at least 80 ms
of voiced signal, while preserving target transcript mismatches as a visible
machine WARN. Whisper transcript/alignment and waveform checks do not prove
pronunciation or replace human listening. An unidentifiable/ambiguous target, malformed
timing, no clean pause, ambiguous boundary or insufficient voiced duration must
reject. Generated/extracted clips remain listening-pending. Isolated
pedagogical letters/syllables remain outside the method.

## Shared human listening tool (2026-10-21)

After automated review, use shared `takeboard` (catalog/skill/README at
`/Volumes/Test1/Works/takeboard`) for HTML generated/master comparison and
save/export/reload of human state, 1–5 scores and notes. Greia's thin adapter
is `tools/export_voice_review_batch.py`; exact commands are in
`docs/agents/GREIA_AUTOMATED_VOICE_REVIEW.md` §6. Keep its manifests external.
Machine findings never initialize human acceptance. Takeboard edits only its
review JSON; importing decisions into Greia receipts/runtime is a separate task.

## Current automated review policy (2026-10-21)

Policy v3 (same silence/score thresholds; diacritics ignored by default): trailing silence/internal pauses warn at ≥1.5s; ASR transcript PASS
requires similarity >0.8 and other applicable checks clear. Other quality flags
remain. `reassess --evidence-dir <finished-report>` reapplies policy to matching
saved evidence without another ASR run; use a fresh report directory. Human
judgments stay separate. Exact commands/boundaries: automated review procedure §3a.

## Whisper screening policy

Whisper is advisory for human acceptance, but warnings are actionable production evidence.

```text
PASS -> transcript plausibly matches; still needs human review
WARN -> unresolved candidate; inspect/regenerate
```

Do not use Whisper as pronunciation authority for letters, syllables or phonics.

## Acceptance

Every successful generation remains:

```text
human_review = PENDING
```

Listen before integrating. Verify exact words, locale, character identity when applicable, pronunciation, clipping/tails, delivery and small-speaker suitability.

A process exit, receipt, valid audio container or Whisper PASS is never final acceptance.

## Project-specific producer rule

A project may need a thin helper that assembles many semantic VoiceEngine requests.

That helper belongs **inside the project that owns the cues**, not in repository root `tools/`.

Examples:

```text
activities/my_activity/tools/generate_voice_requests.py
activities/my_activity/tools/build_voice_batch.py
<other-project>/tools/generate_voice_requests.py
```

A project-local producer may own only:

- semantic cue IDs;
- exact reviewed localized text;
- semantic speaker/kind assignment;
- review-output naming;
- thin JSONL/batch request assembly for `tools/greia_voice.py`.

It must not own or reintroduce:

- VoxStage/Chatterbox/MLX imports, direct service calls or model IDs;
- canonical reference paths/hashes;
- native host voice names/rates or `say`/`afconvert` calls;
- Whisper calls;
- FFmpeg trimming/conversion policy;
- token budgets/model retries/accelerator cache lifecycle;
- silent/synthetic placeholder audio on generation failure.

For an Activity, remember that `activities/<id>/` is also package content. Remove obsolete/one-shot voice producers, temporary JSONL queues, receipts and scratch files from the Activity tree before final package acceptance. Do not accidentally ship authoring machinery to the child runtime.

Repository root `tools/` is reserved for genuinely Greia-wide reusable tooling such as the canonical VoiceEngine and central shared-library producers.

If a project-local helper becomes genuinely useful across multiple independent projects, promote it deliberately to a stable shared tool instead of copying variants everywhere.

## Semantic-speaker rule

When an Activity needs ordinary guidance rather than pronunciation-authoritative sound, choose an actual semantic presenter route rather than misclassifying the line as `pedagogical_speech`.

Examples:

```text
Leo welcome/instruction -> character_dialogue
Dani instruction        -> dani_system_speech
generic praise          -> shared_character_utterance when resolver supports it
exact letter/syllable   -> pedagogical_speech
```

Existing owner-accepted audio does not need regeneration merely because its historical generator predates the engine. New/replacement takes must be generated into review staging and accepted before integration.

## Maintainer extension rule

New synthesis systems implement the provider contract behind `VoiceEngine`. Never spread model/backend conditionals back into Activities, content projects, OS/shared-library scripts or skills.

## Historical paused extractor v4 retries (2026-10-21; superseded below)

Use the current corpus work order and HANDOVER for the scoped priority run.
Version 4 handles coincident word-boundary timestamps with a unique quiet run
inside the first target-word span, requiring exact independent removed-prefix
and retained-target transcripts; warn mode cannot waive those recovery checks.
Source snapshots and same-ASR replay evidence are external. Never silently
resume a frozen v2/v3 extraction plan with a changed algorithm. New retries
freeze v4 plus an explicit roughly one-second pause and retain the cumulative
three-generation limit. Primary owns diagnosis; batch monitoring must not
change thresholds, masters, transcripts, selection or code.

## Historical target-suffix cutter v5 (2026-10-22; superseded by v6 below)

Discarded intro spelling and recognized word count do not gate extraction. The
final expected target anchors the cut; the declared prefix/count are provenance
only. See the current extraction contract for exact/warn suffix matching and
adjacent-span PCM search with mandatory exact retained-target verification.
Never transcribe the removed intro to accept a cut. Historical v4 plans/receipts
remain immutable and cannot silently run under v5. Bulk priority generation is
STOPPED; saved-audio replay and human comparison do not authorize restarting it.

## ASR default / accent override (2026-10-22)

Use pinned cached multilingual Whisper Base from asr_policy.py for new checking.
Diacritics are ignored only during ASR comparison by default; exact authored
scripts and audio are preserved. `VoiceRequest(ignore_accents=False)`, JSON
ignore_accents=false or `--strict-accents` select strict comparison. This applies
to final verification, target location, extraction safety and saved review scoring.
Extractor v6 freezes the model/accent policy; review screen v3 prevents stale
cache reuse. Reassessment preserves original verifier provenance. No old corpus
plan or human review is rewritten. Current owner-authorized continuation is
described below and in HANDOVER; older paused plans remain historical.


### 2026-10-22 owner-authorized priority continuation

The latest owner request resumes only the previously frozen 667 problematic short
cues through `tools/finish_voice_priority.py`; the older STOPPED entries remain
historical. Read the corpus regeneration manual for exact continuation flags and
crash recovery. Saved provider sources are tried first, prior cumulative budgets
carry by maximum, and three fresh generations per cue remains the total limit.
Carrier raw synthesis verification is OFF because the intro is disposable;
required Base verification checks the delivered extracted target before install.
Keep master identity, deferred scope and human acceptance separate. Do not launch
an old v4 producer or the unimplemented shared two-queue plan.


### Usage/reference consistency

`tools/greia_voice_core/README.md` is the practical entry point for current CLI,
JSON/Python fields, defaults, return statuses, service ports and recovery. Normal VoxStage character requests now auto-route fewer than five words to the
localized carrier/cut/final-Base path, including Dani and single words. Defaults:
short_text_mode=auto, short_text_max_words=4, short_text_max_alnum=null, three total
takes. CLI/JSON/Python can override mode/thresholds. Pedagogical speech stays native;
Chatterbox auto retains its ordinary route. Long/bypass verification retains its
older eligibility/advisory-warning behavior. Only separate verification queues
remain proposed. Explicit corpus raw synthesis uses short_text_mode=off to prevent
double wrapping; its frozen selection and cumulative budgets remain unchanged.


### 2026-10-22 correction: normal API v7; frozen corpus stopped

Normal automatic short requests now use `tools/voice_carrier_search.py` v7:
PCM-first bounded suffix candidates, no raw-intro ASR, exactly one target-only
Base match. The normal API uses score >0.8 plus equal canonical unit count and
identical numeric sequence; exact locale words/digits 0–100 are equivalent.
Final delivered signal/ASR checks remain mandatory unless explicitly disabled.
ASR/IO failures require recovery and must not spend a fresh take. See the
VoiceEngine README and `docs/reviews/2026-10-22_TARGET_ONLY_VOICE_EXTRACTION_V7.md`.
The historical 667-cue producer remains stopped on v6; never resume unchanged.
A versioned corpus adapter must preserve source/master/job provenance and
cumulative budgets before any synthesis or installation. Saved replay candidates
are external and listening-pending, not installed or human-approved.

### V7 saved-source corpus adapter

`tools/recover_voice_candidates.py` stages FAILED rows from an existing frozen v6
priority source run using `target-only-v7-saved-v1`, then installs only completed
passing candidates with `--install` through CorpusRunner/RunStore. It has no
provider capability/fresh mode; missing candidates never spend a take. Required
final count/numeric/signal checks cannot be disabled. Source plans/receipts,
master identities and cumulative counts remain unchanged. See the corpus manual
for exact flags and transaction recovery. Other saved histories and the preserved
letter_A job require explicit reconciliation, not a restart of the old producer.

Saved recovery can now use `--source-selection <index.json>` for explicitly
pinned historical FAILED/PRESERVED rows. The index binds source plan, remaining
list, priority, raw/receipt and completed provider job. Exact provider packaging
is replayed if its48kHz output and retained22,050Hz carrier have different hashes.
No synthesis, threshold or budget changes. Read the corpus manual's index schema;
unknown provenance or uncertain journal states remain blockers.

### Period/warm direction and final-take continuation

Normal automatic intros now end with a period, not ellipsis; composition policy
`period-separated-intro-v1`. Default reading is warm, calm and clear with careful
natural pronunciation. Silent-pause direction remains separate. Source masters
and historical frozen prompts are unchanged.

`continue_voice_priority_v7.py` prepares a separately versioned final-take plan
for exact remaining IDs with two prior attempts, then calls normal automatic
VoiceEngine with max_attempts1/required verification. CorpusRunner owns the last
take reservation and installation. Known quality exhaustion preserves originals;
unknown provider/ASR/IO outcomes stop NEEDS_RECOVERY. Inspect result.evidence_dir,
not error prose. HTTP response timeout now defaults120s (override
GREIA_VOXSTAGE_HTTP_TIMEOUT, up to7200) separately from job wait; never retry an
uncertain POST. Current220-file plan is NOT STARTED: live period/warm probes8/12
pass and miss their predeclared readiness gate. Investigate saved failures first.


Owner method-repair correction2026-10-22: corpus final-take-v7-02 is OWNER
STOPPED, not prepared/unstarted or runnable. Automatic continuation is deleted.
Owner permits bounded diagnostics on two consistently rejected targets only.
Current comparison v2 supports standard cardinals0–100 EN/IT/FR/ES, guards exact
numeric values/literals and removes internal-marker score inflation. Normal
Whisper verification and review/reassess v4 share it; historical v1 evidence
is retained. Source preparation and alternate natural-carrier prompts remain
experimental, not production defaults. Read HANDOVER and paired-method report;
no bulk restart or threshold relaxation follows from a small diagnostic result.
