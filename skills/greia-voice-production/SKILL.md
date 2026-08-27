---
name: greia-voice-production
description: Produce Greia prerecorded character or pedagogical speech through the canonical semantic voice tool. Use for actual voice generation, provider probing, batch production and voice-tool maintenance.
---

# Greia Voice Production

**Status:** implementation candidate; local provider acceptance pending  
**Reviewed:** 2026-08-27

## Use this tool, not backend commands

For actual speech generation use:

```text
tools/greia_voice.py
```

Do not invoke Chatterbox, `mlx_audio`, `mlx_whisper`, macOS `say`, `afconvert`, FFmpeg trimming or canonical reference files directly from Activity/OS/Encyclopedia authoring code unless you are maintaining the voice engine itself.

Read:

```text
docs/design/GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md
docs/architecture/GREIA_VOICE_PRODUCTION_ENGINE.md
```

Only engine maintainers / environment setup work should additionally read:

```text
docs/agents/GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md
docs/agents/GREIA_CHATTERBOX_PRODUCTION_FIELD_GUIDE.md
```

## Required semantic input

Every generated cue needs:

```text
speaker
kind
locale
exact reviewed text
cue ID (strongly preferred)
output path when integration location is already known
```

Kinds:

```text
character_dialogue
shared_character_utterance
pedagogical_speech
dani_system_speech
```

The caller chooses **semantic kind**, never backend/model.

Examples:

```bash
python3 tools/greia_voice.py generate \
  --speaker leo \
  --kind character_dialogue \
  --locale it \
  --text "Guardiamo con calma." \
  --cue-id presenter.hint
```

```bash
python3 tools/greia_voice.py generate \
  --speaker pedagogical \
  --kind pedagogical_speech \
  --locale it \
  --text "ma" \
  --cue-id phonics.ma \
  --verification off
```

## Routing rules

```text
Lilli/Leo/Flash/Tito/Momo + character_dialogue
    -> canonical cloned-character provider

pedagogical_speech
    -> deterministic native/system provider
    -> speaker must be pedagogical or system

Dani
    -> dani_system_speech
    -> native/system provider

shared_character_utterance
    -> resolve reviewed Greia shared library
    -> do not synthesize a new clip here
```

Do not infer `pedagogical_speech` from short text. `Vai!` may be character dialogue; `ma` may be a teaching target.

## Before generation

Run the non-mutating probe:

```bash
python3 tools/greia_voice.py doctor
```

If the intended provider is unavailable, report `UNAVAILABLE`. Do not silently install/download a heavy voice toolchain unless the owner explicitly asked for setup.

## Repeated generation

Prefer one warm worker:

```bash
python3 tools/greia_voice.py serve
```

Then use `request`, or use `batch` for JSONL queues. Never launch concurrent Chatterbox workers. The engine has a cross-process lock and will reject competing workers.

## Whisper

Whisper is advisory. `PASS` means only that the transcript plausibly matches. `WARN` may trigger a bounded regenerate. Neither state accepts audio.

Do not use Whisper as pronunciation authority for letters/syllables/phonics.

## Acceptance

Every successful generation remains:

```text
human_review = PENDING
```

Listen before packaging/accepting. Verify exact words, locale, character identity when applicable, pronunciation, clipping/tails, delivery and small-speaker suitability.

A process exit, receipt, valid audio container or Whisper PASS is never final acceptance.

## Maintainer extension rule

New synthesis systems implement the provider contract behind `VoiceEngine`. Never spread model/backend conditionals back into Activity scripts or skills.
