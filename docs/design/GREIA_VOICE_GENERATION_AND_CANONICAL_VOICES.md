# Greia Voice Generation and Canonical Character Voices

**Status:** accepted voice policy + canonical authoring production path  
**Reviewed:** 2026-08-28  
**Scope:** presenter speech, researched narration, shared character utterances, deterministic pedagogical speech, Dani system speech, multilingual prerecorded assets and human review  
**Canonical production tool:** `tools/greia_voice.py`

Related authorities:

```text
skills/greia-voice-production/SKILL.md
tools/greia_voice_core/README.md
docs/architecture/GREIA_VOICE_PRODUCTION_ENGINE.md
docs/design/GREIA_SHARED_CHARACTER_UTTERANCES.md
skills/greia-activity-authoring/PRESENTERS_AND_CURIOSITY.md
```

## 1. Core decision: speech has different semantic jobs

Greia does not treat all speech as one TTS problem.

```text
A. character_dialogue
   presenter welcome, narration, researched facts, contextual hints, story/dialogue
   -> canonical Lilli/Leo/Flash/Tito/Momo identity

B. shared_character_utterance
   praise, success, retry, progress, start reactions
   -> central Greia reviewed shared library
   -> library production uses the same Voice Production Engine
   -> normal Activities resolve the reviewed family at runtime

C. pedagogical_speech
   letters, syllables, phonics, spelling/pronunciation targets
   -> deterministic native/system speech
   -> correctness and consistency outrank mascot identity

D. dani_system_speech
   Activity-specific Dani dialogue
   -> deterministic system speech preserving a clearly robotic identity
```

Governing rule:

> **If the sound itself is the educational truth being taught, use pedagogical speech. If speech communicates content through a character, use character speech.**

Text length is not the selector. `Vai!` may be character dialogue; `ma` may be a teaching target.

## 2. The Voice Production Engine is the canonical authoring boundary

All new voice production goes through:

```text
tools/greia_voice.py
```

Activity, OS/shared-library and Encyclopedia authoring code provides semantic intent:

```text
speaker
kind
locale
exact reviewed text
cue/output identity
```

It does **not** choose or operate:

```text
Chatterbox model IDs
MLX lifecycle/cache rules
canonical reference filenames/hashes
native host voice names/rates
pedagogical synthesis workarounds
Whisper commands/models
FFmpeg trim/packaging commands
short-utterance token budgets
```

Those mechanics belong behind `VoiceEngine` and its providers.

Direct Chatterbox/native/Whisper instructions in historical one-off scripts are legacy implementation evidence, not the extension point for new work.

Existing owner-accepted audio does not need regeneration solely because its historical generator predates the engine.

## 3. Canonical character identities

| Character | Voice ID | Character reason |
|---|---|---|
| Lilli | `greia.lilli.v1` | warm wonder, creativity, stories and imagination |
| Leo | `greia.leo.v1` | warm oldish savvy storyteller; knowledge and thoughtful guidance without young-teacher energy |
| Flash | `greia.flash.v1` | bright, quick, playful action and friendly challenge |
| Tito | `greia.tito.v1` | warm adventurous discovery, nature, investigation and curiosity |
| Momo | `greia.momo.v1` | musical, unusual, playful emotion and celebration |
| Dani | `greia.dani.system-v1` | fun, clearly robotic logic/pattern feedback |

Canonical source masters:

```text
assets/source/audio/character-voice-masters/v0.1/
```

Reviewed cloning references and registry:

```text
assets/audio/characters/canonical/v0.1/
assets/audio/characters/canonical/v0.1/manifest.toml
```

The engine verifies cloning-reference SHA-256 values from the manifest before generation.

Dani intentionally has no cloned natural-voice reference in v0.1. Dani is system-generated.

## 4. Current provider implementation

Current providers behind the engine are implementation details, not caller contracts:

```text
Lilli/Leo/Flash/Tito/Momo
    -> Chatterbox Multilingual V3 on the accepted Apple-Silicon MLX path

pedagogical_speech
    -> macOS deterministic native/system provider

Dani
    -> macOS deterministic native/system provider

optional semantic checking
    -> mlx-whisper-tiny for suitable multi-word character/shared-library lines
```

Rejected production directions remain rejected:

- MOSS-TTS-Nano for canonical Greia character speech;
- repeated `ma. ma. ma.` / middle-extraction prompting;
- cloned character speech as pronunciation authority for syllables/phonics;
- runtime voice models on the child device.

A future provider is added behind the engine. Activities do not learn a new backend command.

## 5. Presenter/speech design is part of Activity design

Every new Activity explicitly considers:

```text
lead presenter/mascot or deliberate none
shared character reaction plan
custom Activity-specific dialogue
pedagogical speech, if any
optional researched curiosity/fact narration
supported locales and spoken coverage
```

This does not mean every Activity needs a lot of speech. It means omission and inclusion are deliberate.

Detailed presenter/fact design:

```text
skills/greia-activity-authoring/PRESENTERS_AND_CURIOSITY.md
```

Production procedure:

```text
skills/greia-voice-production/SKILL.md
```

## 6. Multilingual-ready from the beginning

Speech uses stable semantic cue IDs independent of language:

```text
presenter.welcome
curiosity.orca.family_pods
phonics.ma
```

Each supported locale owns reviewed wording. If speech is an accepted feature, each shipped locale also needs reviewed audio with the correct semantic speaker.

Do not:

- hard-code Italian/English branches in gameplay;
- let displayed and spoken wording drift semantically;
- impersonate a canonical character with arbitrary system TTS in one locale;
- make scoring/correctness/difficulty depend on locale or voice variant.

If a provider is temporarily unavailable, keep the semantic cue and localized text ready and report audio as pending/unavailable. Do not erase the design.

## 7. Character dialogue and curiosity narration

Use `character_dialogue` for:

```text
brief welcome/orientation
contextual hints
short story/narration beats
Activity-specific explanation
researched curiosity facts
```

Subject-rich Activities should consider a small optional fact pool when it genuinely adds curiosity.

Facts are:

- finite reviewed authoring content;
- researched and provenance-recorded;
- never runtime LLM output;
- offline on the child device;
- presentation-only and unable to change score/correctness/rewards/difficulty/progression.

## 8. Pedagogical speech

Use `pedagogical_speech` when the child is expected to learn or imitate the sound itself:

```text
letters
letter names
syllables
phonics
spelling units
pronunciation exercises
foreign-language pronunciation targets
```

A beautiful but occasionally wrong syllable is worse than synthetic but reliable pronunciation.

The exact educational text belongs to the semantic request. Provider-specific spelling/accent hints used to make a native synthesizer pronounce it correctly are private engine implementation details and must not rewrite Activity localization.

A fluent speaker/educator must review pronunciation-critical output.

## 9. Shared character utterances

Current shared semantic families:

```text
praise.general
celebrate.success
encourage.retry
encourage.progress
ready.go
```

Normal Activities request:

```text
character + semantic family + locale
```

They do not choose phrase text, filename, array index or variant number and do not synthesize speech at runtime.

One reviewed file is valid; multiple reviewed files add presentation variety. Random selection must never affect gameplay semantics.

The shared library itself is produced during authoring through the same Voice Production Engine with:

```text
kind = shared_character_utterance
```

Lilli/Leo/Flash/Tito/Momo use their canonical character profile. Dani uses the system profile.

Exact phrase/runbook authority:

```text
docs/design/GREIA_SHARED_CHARACTER_UTTERANCES.md
docs/agents/GREIA_SHARED_CHARACTER_UTTERANCE_RECORDING.md
```

## 10. Whisper is advisory

For suitable multi-word character/shared-library audio the engine may run Whisper with the requested language explicitly set.

It is a cheap automatic warning/regeneration aid, not an acceptance authority.

```text
PASS -> plausible transcript match; human listening still required
WARN -> likely mismatch; regenerate/inspect
NOT_RUN / NOT_APPLICABLE -> no machine transcription gate
```

Do not use Whisper to certify letters, syllables or phonics.

## 11. Human acceptance

Every generated result remains:

```text
human_review = PENDING
```

Human listening verifies:

- exact intended words and locale;
- canonical character identity when applicable;
- no invented/repeated words or sounds;
- pronunciation/stress;
- no clipping or unwanted tail;
- appropriate delivery;
- small-speaker intelligibility.

For factual narration also verify the researched meaning is preserved.

For pedagogical speech exact target pronunciation is the primary gate.

A process exit code, audio file, receipt or Whisper PASS is never acceptance.

The owning workflow remains final authority. Example: Encyclopedia audio is not packageable until its ledger says `OWNER_ACCEPTED`.

## 12. Installation and readiness

The engine source ships in the Greia repository. The heavy character-production environment is authoring-workstation only.

Start with:

```bash
python3 tools/greia_voice.py doctor
```

Quick install/use guide:

```text
tools/greia_voice_core/README.md
```

Detailed setup:

```text
docs/agents/GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md
```

The low-level Chatterbox field guide is engine-maintainer/troubleshooting documentation, not normal Activity/Encyclopedia operating procedure.

## 13. Package/runtime boundary

Activity/runtime packages may contain reviewed static audio, but must not contain:

```text
Chatterbox/Whisper model weights
MLX/PyTorch environments
model caches
canonical cloning-reference masters
FFmpeg binaries used only for authoring
cloud credentials
rejected/unreviewed generation scratch
```

No child runtime TTS/model is introduced by this authoring architecture.

Runtime child microphone capture is a different Greia platform subsystem (`audio.basic`) and must not be confused with prerecorded voice production.

## 14. Current implementation status

Implemented now:

- semantic `VoiceRequest` / `VoiceEngine` abstraction;
- canonical voice registry + hash validation;
- Chatterbox MLX canonical-character provider;
- macOS pedagogical/Dani native provider;
- central shared-library authoring through the same engine;
- optional Whisper advisory verifier;
- bounded retry policy;
- cross-process single-worker lock;
- warm localhost service and batch mode;
- WAV/OGG packaging;
- machine generation receipts with `human_review=PENDING`;
- non-mutating `doctor` command;
- repository quickstart/install guide + tested dependency set.

Still future/host-specific:

- Windows/Linux native/system provider;
- non-MLX accepted cloned-character provider;
- Activity Designer speech-kind UI/schema integration;
- complete shared utterance runtime catalogue/resolver if not yet completed elsewhere.

Exact command/API behavior belongs to source/tests under `tools/greia_voice.py` and `tools/greia_voice_core/`.
