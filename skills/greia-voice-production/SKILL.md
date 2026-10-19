---
name: greia-voice-production
description: Canonical Greia authoring skill for producing prerecorded character, shared-library, pedagogical and Dani speech. Use for generation, installation/readiness, batch/service operation and voice-engine maintenance.
---

# Greia Voice Production

**Status:** canonical authoring-time voice-production contract  
**Reviewed:** 2026-10-19

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

Before generating shared voice speech, audit the accepted
`assets/audio/characters/shared/v0.2/` catalogue, its
`manifest.toml` and `review.csv`: **192 owner-approved EN/IT
recordings (180 reactions and 12 introductions)** are DONE.
Reusing accepted bytes, missing playback wiring and actually missing
voice audio are separate ledger states. See
`docs/design/GREIA_SHARED_CHARACTER_UTTERANCES.md`.
The 2026-10-14 all-app agent work order explicitly respects this
distinction.

## Current selected provider and masters — owner decision 2026-10-19

All six characters use the owner-accepted **v0.2 cloned masters**, including Dani.
VoxCPM2 through the existing shared local VoxStage worker is now the default
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

Active registry: `assets/audio/characters/canonical/v0.2/manifest.toml`.
Source masters/provenance: `assets/source/audio/character-voice-masters/v0.2/`.
The old v0.1 set is historical. The owner's acceptance of these masters and the
24 EN/IT/FR/ES comparison samples does not accept future generations or authorize
regeneration of previously accepted runtime recordings.

**Subsequent scoped owner authorization (2026-10-19):** the owner explicitly
requested replacement of existing Activity/system recordings using these new
masters, except deterministic isolated letters/syllables, and a tone/mood prompt
for every recording. Execute `tools/regenerate_voice_corpus.py` under
`docs/agents/GREIA_VOICE_CORPUS_REGENERATION.md`. This is the authorized exception
to older preservation instructions for this corpus operation. It uses the same
VoiceEngine, serial production, frozen requests, explicit metadata blockers,
backups/recovery and pending-review receipts. Do not use the add-only approved
asset importer for new unlistened takes. Full production has not been launched
by the tool-preparation session.

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

## Whisper

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
