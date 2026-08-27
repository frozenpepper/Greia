---
name: greia-voice-production
description: Canonical Greia authoring skill for producing prerecorded character, shared-library, pedagogical and Dani speech. Use for generation, installation/readiness, batch/service operation and voice-engine maintenance.
---

# Greia Voice Production

**Status:** canonical authoring-time voice-production contract  
**Reviewed:** 2026-08-28

## One rule

All new Greia prerecorded speech production goes through:

```text
tools/greia_voice.py
```

Activity, OS/shared-library and Encyclopedia agents must not invoke Chatterbox, `mlx_audio`, `mlx_whisper`, macOS `say`, `afconvert`, FFmpeg trimming or canonical reference files directly. Those are implementation details owned by the Voice Production Engine.

If an older Activity generator, runbook or queue contains direct backend instructions, treat those **production mechanics as superseded** by this skill. Preserve its semantic text/cue/status/acceptance authority, but submit the speech through the engine.

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

The caller chooses the semantic kind, never a backend/model.

Routing:

```text
Lilli/Leo/Flash/Tito/Momo + character_dialogue
    -> canonical cloned-character provider

shared_character_utterance
    -> authoring production of Greia's central reviewed shared library
    -> cloned provider for Lilli/Leo/Flash/Tito/Momo
    -> system provider for Dani

pedagogical_speech
    -> deterministic native/system provider
    -> speaker must be pedagogical or system

Dani + dani_system_speech
    -> deterministic native/system provider
```

At **runtime**, Activities never synthesize `shared_character_utterance`; they resolve the reviewed Greia shared family. The semantic kind above exists so the central shared library itself is produced through the same authoring engine.

Do not infer `pedagogical_speech` from short text. `Vai!` may be character dialogue; `ma` may be a teaching target.

## Installation / readiness

The engine source ships in the repository. The optional heavy MLX production environment lives outside Git.

Start with the non-mutating probe:

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

Do not silently install/download a multi-GB production stack merely because an Activity could use optional speech. If actual production is requested and the environment is absent, install only with owner authorization using the canonical setup procedure.

## Generate one line

```bash
python3 tools/greia_voice.py generate \
  --speaker leo \
  --kind character_dialogue \
  --locale it \
  --text "Guardiamo con calma." \
  --cue-id presenter.hint \
  --output ./tmp/voice-review/presenter-hint.ogg
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
  --output ./tmp/voice-review/ma.wav
```

## Repeated generation

Prefer one warm worker:

```bash
python3 tools/greia_voice.py serve
```

Then use `request`, or use `batch` for JSONL queues. Never launch concurrent Chatterbox workers. The engine owns a cross-process generation lock and will reject competing workers.

## Whisper

Whisper is advisory. Suitable multi-word character/shared-library lines may be transcribed automatically. A mismatch can trigger bounded regeneration.

`PASS` means only that the transcript plausibly matches. `WARN` means inspect/regenerate. Neither state accepts audio.

Do not use Whisper as pronunciation authority for letters, syllables or phonics.

## Acceptance

Every successful generation remains:

```text
human_review = PENDING
```

Listen before integrating. Verify exact words, locale, character identity when applicable, pronunciation, clipping/tails, delivery and small-speaker suitability.

A process exit, receipt, valid audio container or Whisper PASS is never final acceptance.

The owning workflow keeps its final acceptance authority. For example, Encyclopedia audio is not packageable until the ledger says `OWNER_ACCEPTED`.

## Activity-specific generator rule

Tracked `tools/generate_*_audio.py` Activity scripts are allowed only as **thin semantic request/batch producers** for `tools/greia_voice.py`. They may own Activity-specific cue IDs, exact reviewed localized text, semantic speaker/kind assignment and review-output naming.

They must not own or reintroduce:

- Chatterbox/MLX imports or model IDs;
- canonical reference paths/hashes;
- native host voice names, rates, `say` or `afconvert` calls;
- Whisper calls;
- FFmpeg trimming/conversion policy;
- token budgets, model retries or accelerator cache lifecycle;
- silent/synthetic placeholder audio on generation failure.

When an Activity needs ordinary neutral guidance rather than pronunciation-authoritative sound, choose an actual semantic speaker (for the current legacy neutral Activities this is Dani) rather than misclassifying the line as `pedagogical_speech` or inventing another speech kind.

Existing owner-accepted audio does not need regeneration merely because its historical generator predates the engine. New/replacement takes must be generated into review staging and accepted before integration.

## Maintainer extension rule

New synthesis systems implement the provider contract behind `VoiceEngine`. Never spread model/backend conditionals back into Activities, Encyclopedia tooling, OS/shared-library scripts or skills.
