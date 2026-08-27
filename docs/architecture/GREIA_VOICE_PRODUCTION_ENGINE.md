# Greia Voice Production Engine

**Status:** implementation candidate / authoring-time subsystem; local provider acceptance pending  
**Date:** 2026-08-27  
**Scope:** prerecorded Greia character dialogue, pedagogical/system speech, Dani system speech, optional ASR verification, review receipts and future authoring backends  
**Runtime boundary:** this subsystem is **not shipped to the child device**

## 1. Purpose

Greia already has a correct semantic speech policy but historically duplicated the mechanics of producing that speech across Activity-specific scripts and agent instructions. The Voice Production Engine centralizes those mechanics behind one semantic request contract.

Activity, OS and Encyclopedia authoring code should know:

```text
speaker
speech kind
locale
exact reviewed text
semantic cue/output identity
```

They should not know:

```text
Chatterbox model IDs
MLX lifecycle/cache rules
canonical reference filenames
reference hashes
native host voice names
phonetic host-TTS workarounds
Whisper invocation details
FFmpeg commands
short-utterance token limits
trim thresholds
provider retry rules
```

Those are provider/engine implementation details.

## 2. Semantic request is the stable API

The core request is `VoiceRequest`.

Current semantic kinds:

```text
character_dialogue
shared_character_utterance
pedagogical_speech
dani_system_speech
```

The semantic kind, not text length, selects the production route.

Examples:

```text
speaker=leo, kind=character_dialogue, text="Guarda qui!"
    -> canonical Leo character renderer

speaker=pedagogical, kind=pedagogical_speech, text="ma"
    -> deterministic native/system pedagogical renderer

speaker=dani, kind=dani_system_speech, text="Schema completato!"
    -> deterministic system-TTS Dani route

kind=shared_character_utterance
    -> rejected by generation engine with instruction to resolve the reviewed shared library
```

A caller may not request `pedagogical_speech` while naming Leo/Lilli/Flash/Tito/Momo as if the character were pronunciation authority. The engine rejects that mismatch.

## 3. Architecture

```text
VoiceRequest
    |
    v
VoiceEngine
    |-- VoiceRegistry
    |     -> canonical voice IDs, references and SHA-256 integrity
    |
    |-- provider routing
    |     |-- ChatterboxMLXProvider
    |     |-- MacOSNativeSpeechProvider
    |     `-- UnsupportedNativeSpeechProvider (truthful fail-closed fallback)
    |
    |-- InterprocessGenerationLock
    |     -> one inference worker across local processes
    |
    |-- SpeechVerifier
    |     `-- WhisperVerifier (optional/advisory)
    |
    `-- AudioPipeline
          -> deterministic WAV/OGG packaging + bounded signal checks
```

The classes are intentionally narrow variation points. Future renderers should implement `VoiceProvider`; future transcript/quality checkers should implement `SpeechVerifier`. Activity code must not grow backend conditionals.

## 4. Chatterbox ownership

`ChatterboxMLXProvider` currently owns Greia canonical character rendering for Lilli, Leo, Flash, Tito and Momo on the existing Apple-Silicon production path.

It enforces the project lessons already established in the field guide:

- lazy model load;
- model reuse for subsequent requests in the same engine/service process;
- one local generation worker;
- canonical reference lookup from the voice manifest;
- canonical reference SHA-256 validation before generation;
- explicit language code;
- bounded output-token policy by utterance length;
- short-dialogue primary-speech-island trimming;
- general dialogue edge trimming that preserves internal pauses;
- `mx.clear_cache()` + Python garbage collection after every take;
- no silent stub generation.

Generation receipts record `model_load_count`. In a daemon/batch run it should stay `1` after the first Chatterbox request, proving model reuse rather than per-clip reload.

## 5. Native/pedagogical speech ownership

`MacOSNativeSpeechProvider` currently implements the first deterministic authoring adapter.

It owns the host-specific rules formerly embedded in Activity scripts:

```text
Italian pedagogical default: Alice @ 175 wpm
English pedagogical default: Samantha @ 180 wpm
lowercase pedagogical synthesis
Italian single-token pronunciation hints such as to -> tò, te -> tè
```

The semantic request and receipt continue to own the exact educational target text. Provider-only synthesis hints do **not** rewrite Activity localization or cue identity.

Host voices can be overridden without changing Activity source:

```text
GREIA_VOICE_PEDAGOGICAL_VOICE_IT
GREIA_VOICE_PEDAGOGICAL_VOICE_EN
GREIA_VOICE_DANI_VOICE_IT
GREIA_VOICE_DANI_VOICE_EN
```

The current Dani defaults are intentionally ordinary native voices pending owner tuning of the preferred robotic host profile. Dani still remains system-generated and is never routed through a cloned natural character voice.

Non-macOS native providers are an explicit extension point. Until one is implemented, the engine returns `UNAVAILABLE`; it must not silently choose an arbitrary backend.

## 6. Whisper verification policy

`WhisperVerifier` uses `mlx-community/whisper-tiny` when available.

It is an **advisory machine gate**, never an acceptance authority.

Eligible by default:

```text
character_dialogue
at least two normalized words
<= 500 characters
verification != off
```

Not eligible by default:

```text
pedagogical letters/syllables/phonics
Dani system speech
isolated one-word reactions where tiny-ASR reliability is poor
shared utterance resolution
```

The locale language is always passed explicitly to Whisper.

A likely transcript mismatch causes another bounded generation attempt while attempts remain. If all attempts still produce an ASR warning, the best surviving take is returned as:

```text
REVIEW_REQUIRED_ASR_WARNING
```

It is not deleted merely because Whisper disagrees; Whisper can itself be wrong.

A plausible transcript returns:

```text
REVIEW_REQUIRED
```

not `ACCEPTED`.

Human listening remains mandatory for character identity, delivery, pronunciation, tails/clicks, clipping and small-speaker suitability.

## 7. Single-worker and warm-service contract

Chatterbox inference must not run concurrently on the same authoring machine.

The engine therefore owns a machine-local cross-process generation lock under `GREIA_VOICE_HOME` (or the platform default Greia voice-production directory). A second process fails fast with an instruction to use the existing daemon/batch rather than contending for unified memory.

For repeated requests use the localhost service:

```bash
python3 tools/greia_voice.py serve
```

It binds only to localhost and processes requests serially in one process. It is deliberately not a network service, cloud API or child-runtime daemon.

Send requests with:

```bash
python3 tools/greia_voice.py request \
  --speaker leo \
  --kind character_dialogue \
  --locale it \
  --text "Guardiamo con calma." \
  --cue-id presenter.hint \
  --output activities/example/assets/audio/it/presenter-hint.ogg
```

Stop cleanly with:

```bash
python3 tools/greia_voice.py shutdown
```

For large known queues, `batch` accepts newline-delimited JSON and keeps the same engine/model alive for the entire file.

## 8. Doctor / provider probe

The previous ad-hoc environment inspection is replaced by:

```bash
python3 tools/greia_voice.py doctor
```

The command is non-mutating. It reports:

- canonical registry version;
- per-character anchor presence/hash validity;
- FFmpeg availability;
- Chatterbox MLX import readiness;
- native/system provider readiness;
- Whisper availability.

It must not download weights or install packages.

## 9. Output and receipts

Default review output lives outside Git under the machine-local Greia voice-production directory. `GREIA_VOICE_HOME` can override that location.

Callers may explicitly request `.wav` or `.ogg` output. FFmpeg is the canonical packaging boundary and standardizes output to mono 22,050 Hz.

Every successful generation writes a sibling receipt:

```text
<output>.receipt.json
```

The receipt records:

```text
exact semantic request
provider ID
canonical voice ID
voice-registry version
reference SHA-256
provider/model/native parameters
Whisper disposition/transcript/score when run
attempt count
output SHA-256/size
human_review = PENDING
```

Repository-contained output paths are stored repository-relative so portable receipts do not embed a contributor home directory.

No generation path may write a silent placeholder and report success.

## 10. Human acceptance and integration boundary

The engine produces **review assets**, not accepted product assets.

Correct flow:

```text
semantic request
-> Voice Production Engine
-> review WAV/OGG + receipt (human_review=PENDING)
-> owner/human listening
-> accepted/rejected disposition in the owning workflow
-> package/integrate only accepted audio
```

The Encyclopedia `OWNER_ACCEPTED` integrator remains the authority for its content. The voice engine should feed its staging/review side, not bypass it.

Likewise Activity-specific packaging should not infer acceptance from exit code, receipt presence or Whisper PASS.

## 11. CLI contract

One-shot generation:

```bash
python3 tools/greia_voice.py generate \
  --speaker tito \
  --kind character_dialogue \
  --locale it \
  --text "Le orche vivono in gruppi familiari." \
  --cue-id curiosity.orca.family_pods \
  --output activities/example/assets/audio/it/orca-family.ogg
```

Pedagogical speech:

```bash
python3 tools/greia_voice.py generate \
  --speaker pedagogical \
  --kind pedagogical_speech \
  --locale it \
  --text "ma" \
  --cue-id phonics.ma \
  --verification off \
  --output activities/example/assets/audio/it/phonics-ma.wav
```

Batch JSONL row:

```json
{"speaker":"leo","kind":"character_dialogue","locale":"it","text":"Guardiamo con calma.","cue_id":"presenter.hint","output":"activities/example/assets/audio/it/presenter-hint.ogg"}
```

Batch command:

```bash
python3 tools/greia_voice.py batch --input path/to/requests.jsonl
```

## 12. Migration policy

The existing `generate_*_audio.py` scripts remain compatibility/production evidence until the new engine passes local provider acceptance.

After acceptance:

1. new Activity/OS/Encyclopedia production must call `tools/greia_voice.py` or the same core classes;
2. do not create another Activity-specific Chatterbox implementation;
3. migrate old generators opportunistically into thin semantic request/batch definitions;
4. preserve existing accepted audio; migration of the generator does not require regenerating reviewed assets;
5. move reusable pronunciation quirks/provider parameters into provider adapters, never into Activities;
6. keep the detailed Chatterbox field guide as engine-maintainer documentation rather than mandatory per-Activity operational procedure.

## 13. Future provider extension

A future TTS/voice model should require a new `VoiceProvider` implementation, not caller changes.

Examples:

```text
ChatterboxPyTorchProvider
LinuxNativeSpeechProvider / espeak-ng adapter
WindowsNativeSpeechProvider
future local neural TTS provider
future explicitly owner-approved cloud authoring provider
```

Routing remains semantic. A model change must never force Activities to rename cues or encode model IDs.

## 14. Explicit non-goals

The engine does not:

- run on the Acer/Pi child device;
- provide runtime TTS to Activities;
- own child microphone capture or microphone DSP;
- research/write factual narration;
- decide shared-utterance wording;
- mark human acceptance;
- upload canonical references to cloud services;
- auto-install Chatterbox, Whisper, FFmpeg or model weights;
- expose a LAN/network voice service.
