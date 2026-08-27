# Greia Voice Production Engine

**Status:** canonical authoring-time voice production subsystem  
**Reviewed:** 2026-08-28  
**Scope:** prerecorded character dialogue, central shared-library production, pedagogical/system speech, Dani system speech, optional ASR verification, review receipts and future authoring backends  
**Runtime boundary:** this subsystem is **not shipped to the child device**

## 1. Purpose

Greia speech policy has several semantic jobs but one production abstraction. The Voice Production Engine centralizes provider/model mechanics behind a semantic request contract.

Activity, OS/shared-library and Encyclopedia authoring code knows:

```text
speaker
speech kind
locale
exact reviewed text
semantic cue/output identity
```

It does not know:

```text
Chatterbox model IDs
MLX lifecycle/cache rules
canonical reference filenames/hashes
native host voice names/rates
pedagogical synthesis workarounds
Whisper invocation details
FFmpeg commands
short-utterance token budgets
trim thresholds
provider retry rules
```

Those are engine/provider implementation details.

Canonical entry point:

```text
tools/greia_voice.py
```

Quick install/use guide:

```text
tools/greia_voice_core/README.md
```

## 2. Stable semantic request

The core request is `VoiceRequest`.

Kinds:

```text
character_dialogue
shared_character_utterance
pedagogical_speech
dani_system_speech
```

The semantic kind, not text length, selects production behavior.

Examples:

```text
speaker=leo, kind=character_dialogue, text="Guarda qui!"
    -> canonical Leo character provider

speaker=leo, kind=shared_character_utterance, text="Ottimo lavoro!"
    -> produce a review candidate for Greia's central shared library

speaker=dani, kind=shared_character_utterance, text="Ottimo lavoro!"
    -> system provider for Dani's central shared-library candidate

speaker=pedagogical, kind=pedagogical_speech, text="ma"
    -> deterministic native/system pedagogical provider

speaker=dani, kind=dani_system_speech, text="Schema completato!"
    -> deterministic system provider
```

`shared_character_utterance` in this engine is an **authoring-production** semantic. Normal Activities do not call the engine at runtime; they resolve the already-reviewed shared family through Greia's runtime/shared-asset system.

A caller may not request `pedagogical_speech` while naming Leo/Lilli/Flash/Tito/Momo as pronunciation authority.

## 3. Architecture

```text
VoiceRequest
    |
    v
VoiceEngine
    |-- VoiceRegistry
    |     -> canonical voice IDs, references and SHA-256 integrity
    |
    |-- VoiceProvider
    |     |-- ChatterboxMLXProvider
    |     |-- MacOSNativeSpeechProvider
    |     `-- UnsupportedNativeSpeechProvider
    |
    |-- InterprocessGenerationLock
    |     -> one inference worker across local processes
    |
    |-- SpeechVerifier
    |     `-- WhisperVerifier (optional/advisory)
    |
    `-- AudioPipeline
          -> review-WAV validation + deterministic WAV/OGG packaging
```

The classes are narrow polymorphic variation points. Future renderers implement `VoiceProvider`; future semantic checkers implement `SpeechVerifier`. Caller scripts do not grow backend conditionals.

## 4. Canonical registry and routing

Voice identity comes from:

```text
assets/audio/characters/canonical/v0.1/manifest.toml
```

Current identities:

```text
greia.lilli.v1
greia.leo.v1
greia.flash.v1
greia.tito.v1
greia.momo.v1
greia.dani.system-v1
```

For cloned profiles the engine verifies the reference SHA-256 before generation. A mismatch is a hard stop.

Routing policy:

```text
character_dialogue + cloned character
    -> cloned-character provider

shared_character_utterance + cloned character
    -> cloned-character provider

shared_character_utterance + Dani
    -> native/system Dani provider

pedagogical_speech
    -> native/system pedagogical provider

dani_system_speech
    -> native/system Dani provider
```

## 5. Chatterbox provider ownership

`ChatterboxMLXProvider` currently owns canonical cloned-character rendering on the accepted Apple-Silicon path.

It owns the hard-won mechanics that old Activity scripts duplicated:

- lazy model load;
- model reuse in batch/service runs;
- one local generation worker;
- canonical reference lookup/hash enforcement;
- explicit language code;
- bounded output-token policy;
- short-dialogue primary-speech-island trimming;
- general edge trimming that preserves internal pauses;
- MLX cache clearing + Python garbage collection after every take;
- no silent stub generation.

Generation receipts record `model_load_count`. In a warm service/batch it should remain `1` after initial load.

The low-level field guide exists for provider maintainers/troubleshooting, not ordinary Activity/Encyclopedia production:

```text
docs/agents/GREIA_CHATTERBOX_PRODUCTION_FIELD_GUIDE.md
```

## 6. Native pedagogical/Dani provider ownership

`MacOSNativeSpeechProvider` currently implements the first deterministic authoring adapter.

It owns host-specific details formerly embedded in Activities, including:

```text
Italian pedagogical profile
English pedagogical profile
lowercase pedagogical synthesis
Italian single-token pronunciation hints such as to -> tò
Dani host-voice profile
```

The semantic request/receipt still records the exact educational target. Provider-only synthesis hints do not rewrite Activity localization.

Optional host voice overrides are engine configuration:

```text
GREIA_VOICE_PEDAGOGICAL_VOICE_IT
GREIA_VOICE_PEDAGOGICAL_VOICE_EN
GREIA_VOICE_DANI_VOICE_IT
GREIA_VOICE_DANI_VOICE_EN
```

Other hosts return `UNAVAILABLE` until an accepted provider is implemented. Do not bypass that boundary with direct Activity shell commands.

## 7. Whisper verification

`WhisperVerifier` currently uses `mlx-community/whisper-tiny` when available.

It is advisory, never acceptance authority.

Eligible by default:

```text
multi-word character_dialogue
multi-word shared_character_utterance
<= 500 characters
verification != off
```

Normally not eligible:

```text
pedagogical letters/syllables/phonics
Dani system speech
isolated one-word/tiny reactions where tiny-ASR reliability is poor
```

The requested language is always passed explicitly.

A likely mismatch can cause another bounded generation attempt. After the final attempt:

```text
plausible transcript -> REVIEW_REQUIRED
warning/mismatch     -> REVIEW_REQUIRED_ASR_WARNING
```

Neither means accepted.

## 8. Single-worker and warm-service contract

Chatterbox inference must not run concurrently on the same authoring machine.

The engine owns a machine-local cross-process lock below `GREIA_VOICE_HOME`. Batch/service paths hold it for their lifetime so another process cannot load a second multi-GB model beside a warm worker.

Warm service:

```bash
python3 tools/greia_voice.py serve
```

Request:

```bash
python3 tools/greia_voice.py request \
  --speaker leo \
  --kind character_dialogue \
  --locale it \
  --text "Guardiamo con calma." \
  --cue-id presenter.hint \
  --output ./tmp/voice-review/presenter-hint.ogg
```

Shutdown:

```bash
python3 tools/greia_voice.py shutdown
```

The service binds only to localhost and is not a child-runtime/network service.

For known queues use JSONL `batch`.

## 9. Doctor and installation

Non-mutating readiness probe:

```bash
python3 tools/greia_voice.py doctor
```

It reports:

- canonical registry version;
- per-character anchor presence/hash validity;
- FFmpeg availability;
- Chatterbox MLX import readiness;
- native/system provider readiness;
- Whisper availability.

It does not intentionally install/download weights.

Canonical installation instructions:

```text
tools/greia_voice_core/README.md
docs/agents/GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md
```

Tested MLX dependency declaration:

```text
tools/greia_voice_requirements_mlx.txt
```

## 10. Output and receipts

Default review output lives outside Git below `GREIA_VOICE_HOME`. Callers may explicitly request repository-relative or machine-local `.wav`/`.ogg` output.

Every successful generation writes:

```text
<audio>
<audio>.receipt.json
```

Receipt fields include:

```text
exact semantic request
provider ID
canonical voice ID
voice-registry version
reference SHA-256
generation parameters
Whisper disposition/transcript/score when run
attempt count
output SHA-256/size
human_review = PENDING
```

No generation path may write a silent placeholder and report success.

## 11. Human acceptance and integration boundary

The engine produces **review assets**, not accepted product assets.

```text
semantic request
-> Voice Production Engine
-> review audio + receipt (human_review=PENDING)
-> human listening
-> owning workflow accepts/rejects
-> only accepted audio is packaged/integrated
```

Examples of owning authorities:

- Encyclopedia ledger `OWNER_ACCEPTED` status;
- shared-library recording/review ledger;
- Activity-specific human review/asset acceptance.

Whisper, exit code, receipt presence and container validity never replace listening.

## 12. Canonical caller policy

New Activity, OS/shared-library and Encyclopedia production must use:

```text
tools/greia_voice.py
```

or the same `VoiceEngine` core classes when a repository tool needs tighter composition.

Do not create another Activity-specific Chatterbox/native-TTS/Whisper implementation.

Historical `generate_*_audio.py` scripts may remain as compatibility/evidence. When changed for new production they should be converted into thin semantic request producers rather than extended as parallel engines.

Existing owner-accepted assets do not require regeneration during migration.

## 13. Future provider extension

A future TTS/voice system adds a `VoiceProvider`, not caller changes.

Examples:

```text
ChatterboxPyTorchProvider
LinuxNativeSpeechProvider
WindowsNativeSpeechProvider
future local neural TTS provider
future explicitly owner-approved cloud authoring provider
```

Routing remains semantic. A provider/model change must never force Activities to rename cues or embed model IDs.

## 14. Explicit non-goals

The engine does not:

- run on Acer/Pi child devices;
- provide runtime TTS to Activities;
- own child microphone capture/DSP;
- research or write factual narration;
- decide shared-utterance wording;
- mark human acceptance;
- upload canonical references to cloud services without explicit authorization;
- expose a LAN voice service.
