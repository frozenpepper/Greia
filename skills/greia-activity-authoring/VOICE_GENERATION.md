# Voice Generation for Greia Activities

This is the focused Activity-facing companion to `SKILL.md`.

## Canonical production rule

All new prerecorded Greia speech is produced through the repository-wide Voice Production Engine / authoring “Voice Studio” workflow:

```text
skills/greia-voice-production/SKILL.md
tools/greia_voice_core/README.md
tools/greia_voice.py
```

Activity code and Activity-specific authoring scripts must **not** invoke Chatterbox, MLX, Whisper, macOS `say`, `afconvert`, FFmpeg trimming or canonical reference recordings directly. Those mechanics belong behind `VoiceEngine`.

Tracked `tools/generate_*_audio.py` Activity scripts are thin semantic request/batch producers only.

The child runtime never contains the voice-production models/providers. It receives only already-reviewed static audio or uses Greia's reviewed shared runtime catalogue.

For presenter/fact design read first:

```text
skills/greia-activity-authoring/PRESENTERS_AND_CURIOSITY.md
```

For actual production read:

```text
skills/greia-voice-production/SKILL.md
```

## 1. Classify speech by semantic purpose

Every produced cue is one of:

```text
character_dialogue
shared_character_utterance
pedagogical_speech
dani_system_speech
```

The semantic purpose selects the route, not text length.

Examples:

```text
"Vai!"                                      -> character_dialogue
"Le orche vivono in gruppi familiari..."   -> character_dialogue / curiosity fact
"ma"                                        -> pedagogical_speech when the syllable itself is taught
"Ottimo lavoro!"                            -> shared_character_utterance when generic praise is enough
Dani Activity explanation                   -> dani_system_speech
```

Governing rule:

> If the sound itself is the educational truth being taught, use `pedagogical_speech`. If speech communicates content through a character, use character speech.

Do not ask Lilli, Leo, Flash, Tito or Momo to become pronunciation authority merely to preserve mascot identity.

## 2. Shared utterances: design vs current availability

The designed shared families are:

```text
praise.general
celebrate.success
encourage.retry
encourage.progress
ready.go
```

Normal Activities should eventually request only:

```text
character + semantic family + locale
```

not a phrase filename/variant and not runtime synthesis.

However, **the v0.1 shared audio library is still pending generation and human acceptance**. Current design target:

```text
6 characters × 5 families × 3 variants × 2 locales = 180 clips
```

Therefore:

- do not claim a shared family is runtime-available merely because it is documented;
- do not copy the 180 planned phrases into Activity packages as a substitute for completing the shared library;
- while the shared catalogue is unavailable, keep visual feedback sufficient and report shared speech as pending;
- if an Activity genuinely needs unique contextual speech now, use reviewed Activity-specific `character_dialogue`, not a fake generic shared-family implementation.

Shared production/status authority:

```text
docs/design/GREIA_SHARED_CHARACTER_UTTERANCES.md
docs/agents/GREIA_SHARED_CHARACTER_UTTERANCE_RECORDING.md
```

## 3. Character voices

Canonical identities:

| Speaker | Voice ID | Typical role |
|---|---|---|
| Lilli | `greia.lilli.v1` | wonder, creativity, stories, art |
| Leo | `greia.leo.v1` | warm older storyteller, reading, knowledge, thoughtful guidance |
| Flash | `greia.flash.v1` | action, speed, lively challenge |
| Tito | `greia.tito.v1` | exploration, nature, investigation, discovery |
| Momo | `greia.momo.v1` | music, emotion, playful experimentation |
| Dani | `greia.dani.system-v1` | robotic logic, patterns and concise feedback |

Lilli/Leo/Flash/Tito/Momo character dialogue routes to the canonical cloned-character provider behind the engine.

Dani routes to deterministic system speech. Never clone a natural voice to impersonate Dani.

## 4. OS-owned character introductions

Greia is defining a reusable character-introduction pack with stable cues:

```text
character.intro.lilli
character.intro.leo
character.intro.flash
character.intro.dani
character.intro.tito
character.intro.momo
```

This is **platform/shared presentation content**, not something every Activity should re-record.

Possible future use includes first-run introduction, tappable characters on Home, a character gallery or another OS-owned discovery surface. Final placement is not decided yet.

Activity rule:

- do not duplicate the canonical “Hi, I'm Lilli/Leo/…” introduction in Activity packages;
- use a short Activity-specific welcome only when the Activity context needs one;
- a contextual welcome should not repeat the character biography unless genuinely useful.

The current intro scripts and production status live in:

```text
docs/design/GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md
docs/agents/GREIA_SHARED_CHARACTER_UTTERANCE_RECORDING.md
```

## 5. Pedagogical speech

Use `pedagogical_speech` for:

```text
letters
letter names
syllables
phonics
spelling units
pronunciation exercises
foreign-language target sounds
```

Correctness and consistency outrank natural voice quality.

The Activity owns the semantic educational target (`"to"`, `"ma"`, etc.). Provider-specific pronunciation hints, host voice names and synthesis commands belong inside the engine.

A fluent speaker/educator must review pronunciation-critical output.

Ordinary instructions are not `pedagogical_speech` merely because the Activity is educational. Give them a real semantic speaker: canonical presenter, reviewed shared utterance once available, or Dani where the design deliberately uses Dani.

## 6. Multilingual-ready from the beginning

Use stable semantic cue IDs independent of language:

```text
presenter.welcome
presenter.hint.first
curiosity.orca.family_pods
phonics.ma
```

For every locale the Activity claims to support:

- provide reviewed localized text;
- preserve the same semantic meaning;
- keep the same canonical character identity for character dialogue;
- generate/review localized audio when speech is part of the accepted feature;
- keep displayed and spoken wording aligned;
- never make score/correctness/difficulty depend on locale or spoken variant.

If a production provider is unavailable, preserve the semantic cue/text plan and report audio pending/unavailable. Do not substitute arbitrary host TTS for a canonical character.

## 7. Producing Activity-specific audio

First probe the workstation:

```bash
python3 tools/greia_voice.py doctor
```

Generate into a **review workspace**, not directly into the Activity package:

```bash
python3 tools/greia_voice.py generate \
  --speaker leo \
  --kind character_dialogue \
  --locale it \
  --text "Guardiamo con calma." \
  --cue-id presenter.hint \
  --output ./tmp/voice-review/my_activity/it/presenter-hint.ogg
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
  --output ./tmp/voice-review/my_activity/it/phonics-ma.wav
```

For several lines use `batch`, or use the warm localhost `serve` / `request` workflow.

Only after human listening may the owning Activity workflow copy accepted static audio into `activities/<activity>/assets/audio/...` and update mappings/manifests.

Installation/setup:

```text
tools/greia_voice_core/README.md
docs/agents/GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md
```

Do not silently install the optional heavy MLX/model stack merely because speech might be useful.

## 8. Whisper verification

Suitable multi-word natural-character/shared-library generation may be checked automatically.

```text
PASS           -> transcript plausibly matches; still human-review
WARN           -> likely mismatch; bounded regeneration/inspection
NOT_RUN        -> verifier unavailable/optional
NOT_APPLICABLE -> tiny, pedagogical or system utterance where ASR is inappropriate
```

Whisper is never pronunciation authority for letters/syllables/phonics and never accepts audio.

## 9. Human audio gate

Every produced clip remains:

```text
human_review = PENDING
```

Reject character/shared speech for:

- wrong/drifting character identity;
- wrong language;
- omitted/repeated/invented words or sounds;
- bad stress/pronunciation;
- clipped start/end;
- unwanted tail;
- noise/distortion;
- inappropriate delivery.

Reject pedagogical speech for any incorrect or ambiguous target sound even if it sounds pleasant.

A successful process exit, valid container, receipt or Whisper PASS is never final acceptance.

## 10. Facts and curiosity narration

Subject-rich Activities should consider short optional researched facts when they genuinely enrich play.

Facts are finite, reviewed `character_dialogue` with provenance. Never ask an LLM at child runtime to invent facts and never require network access.

Fact selection is presentation-only and must not affect score, correctness, rewards, difficulty or progression.

Research/source rules:

```text
skills/greia-activity-authoring/PRESENTERS_AND_CURIOSITY.md
```

## 11. Runtime boundary

The child receives only reviewed static audio or resolves accepted Greia shared/platform-owned speech assets.

Never package:

```text
Chatterbox/Whisper model weights
MLX/PyTorch environments
model caches
canonical cloning references
FFmpeg binaries solely used for authoring
rejected/unreviewed generations
```

Generated presenter speech and runtime child microphone recording are separate systems. Child voice capture uses the platform-owned `audio.basic` route described in `MICROPHONE_RECORDING.md`.

## 12. Completion check for Activity speech

Before calling an Activity's speech work complete, confirm:

```text
semantic cue IDs defined
correct speech kind selected
supported locales covered
canonical speaker correct
production performed through tools/greia_voice.py / VoiceEngine
review candidates generated outside the runtime package
receipts retained where appropriate
human listening completed
only accepted audio integrated into runtime package
shared families are used only when actually available in the accepted shared catalogue
canonical character introductions are not duplicated locally
Activity still works when optional speech is unavailable where product policy permits degradation
```

The low-level Chatterbox field guide is for Voice Engine maintainers/troubleshooting only.
