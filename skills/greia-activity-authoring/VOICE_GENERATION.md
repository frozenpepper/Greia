# Voice Generation for Greia Activities

This is the focused Activity-facing companion to `SKILL.md`.

## Canonical production rule

All new prerecorded Greia speech is produced through the repository-wide Voice Production Engine:

```text
skills/greia-voice-production/SKILL.md
tools/greia_voice_core/README.md
tools/greia_voice.py
```

Activity code and Activity-specific authoring scripts must **not** invoke Chatterbox, MLX, Whisper, macOS `say`, `afconvert`, FFmpeg trimming or canonical reference recordings directly. Those mechanics belong behind `VoiceEngine`.

Tracked `tools/generate_*_audio.py` Activity scripts are thin semantic request/batch producers only. Do not copy backend mechanics into them and do not create a new Activity-local TTS implementation.

For presenter/fact design read first:

```text
skills/greia-activity-authoring/PRESENTERS_AND_CURIOSITY.md
```

For actual production read:

```text
skills/greia-voice-production/SKILL.md
```

## 1. Classify speech by semantic purpose

Every cue must be one of:

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

> If the sound itself is the educational truth being taught, use pedagogical/system speech. If speech communicates content through a character, use character speech.

Do not ask Lilli, Leo, Flash, Tito or Momo to pronounce a teaching target merely to preserve mascot identity.

## 2. Shared utterances: consume vs produce

Normal Activities **consume** Greia's reviewed shared families at runtime:

```text
praise.general
celebrate.success
encourage.retry
encourage.progress
ready.go
```

They request the semantic family, not a phrase filename/variant and not runtime synthesis.

The Voice Production Engine also accepts `shared_character_utterance` during **authoring** so Greia's central shared library can itself be produced through the same canonical tool. That does not create runtime TTS.

If generic shared feedback is sufficient, prefer it over Activity-specific custom dialogue.

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

Lilli/Leo/Flash/Tito/Momo character dialogue currently routes to the canonical cloned-character provider behind the engine.

Dani routes to deterministic system speech. Never clone a natural voice to impersonate Dani.

## 4. Pedagogical speech

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

The Activity owns the semantic educational target (`"to"`, `"ma"`, etc.). Provider-specific pronunciation hints, host voice names and synthesis commands belong inside the engine, not Activity source.

A fluent speaker/educator must review pronunciation-critical output.

Ordinary instructions are not `pedagogical_speech` merely because the Activity is educational. Give them a real semantic speaker (canonical presenter, a shared utterance family, or Dani where the Activity deliberately uses Dani).

## 5. Multilingual-ready from the beginning

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

If a production provider is temporarily unavailable, preserve the semantic cue/text plan and report audio as pending/unavailable. Do not hard-code one language or substitute arbitrary system TTS for a canonical character.

## 6. Producing audio

First probe the current workstation:

```bash
python3 tools/greia_voice.py doctor
```

Generate one line into a **review workspace**, not directly into the Activity package:

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

For several lines use `batch`, or start the warm localhost service with `serve` and submit requests with `request`.

Only after human listening acceptance may the owning Activity workflow copy/integrate the accepted static audio into `activities/<activity>/assets/audio/...` and update its locale/audio mapping or manifest as needed.

Installation/setup instructions are in:

```text
tools/greia_voice_core/README.md
docs/agents/GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md
```

Do not silently install the optional heavy MLX/model stack merely because speech might be useful. If actual voice production is requested and the provider is unavailable, follow the canonical install guide with owner authorization.

## 7. Whisper verification

Suitable multi-word character/shared-library generation may be checked by Whisper automatically.

Whisper is an advisory filter:

```text
PASS       -> transcript plausibly matches; still human-review
WARN       -> likely mismatch; bounded regeneration/inspection
NOT_RUN    -> verifier unavailable or optional
NOT_APPLICABLE -> tiny/pedagogical/system utterance where ASR is inappropriate
```

Whisper must never be treated as pronunciation authority for letters/syllables/phonics and never marks audio accepted.

## 8. Human audio gate

Every produced clip remains `human_review = PENDING` until listened to.

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

## 9. Facts and curiosity narration

Subject-rich Activities should consider short optional researched facts when they genuinely enrich play.

Facts are finite, reviewed `character_dialogue` with provenance. Never ask an LLM at child runtime to invent facts and never require network access.

Fact selection is presentation-only and must not affect score, correctness, rewards, difficulty or progression.

Research/source rules live in:

```text
skills/greia-activity-authoring/PRESENTERS_AND_CURIOSITY.md
```

## 10. Runtime boundary

The child receives only reviewed static audio or resolves Greia shared/platform-owned speech services.

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

## 11. Completion check for Activity speech

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
Activity still works if optional character audio is unavailable where product policy permits degradation
```

The low-level Chatterbox field guide is no longer normal Activity-authoring reading. It is for Voice Engine maintainers/troubleshooting only.
