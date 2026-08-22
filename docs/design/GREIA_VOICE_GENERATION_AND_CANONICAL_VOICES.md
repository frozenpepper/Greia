# Greia Voice Generation and Canonical Character Voices

**Status:** accepted Activity-authoring / Activity Designer direction; production compiler integration pending  
**Date:** 2026-08-22  
**Scope:** build-time/local Activity voice production, canonical character voice identity, localized package audio, and the deliberate Dani system-TTS exception  
**Related authorities:** `docs/adr/0028-platform-and-activity-localization-language-context.md`, `docs/design/GREIA_CANONICAL_CAST_SYSTEM.md`, `skills/greia-activity-authoring/SKILL.md`

## 1. Decision

Greia Activities may use generated speech, but ordinary Activity packages must not carry a text-to-speech model or download one at runtime.

The accepted authoring direction is:

```text
localized semantic speech cues
        ↓
Activity Designer / local voice-production worker
        ↓
canonical Greia character voice policy
        ↓
MOSS-TTS-Nano voice cloning for Lilli, Leo, Flash, Tito and Momo
Greia OS text-to-speech for Dani
        ↓
reviewed WAV masters
        ↓
bounded normalization / package conversion
        ↓
locales/<locale>/audio/<cue>.ogg or .wav
        ↓
ordinary Greia Activity package
```

The generated audio is package data. The model, model cache, Python environment and generation service are developer tooling and must not enter `.greiaactivity` packages or the child OS image merely because an Activity used them during authoring.

This document defines the current Activity Designer/authoring contract. It does **not** add a new `activity.toml` table or claim that a voice compiler is already implemented in the runtime.

## 2. Why build-time generation is the default

Build-time generation is preferable for normal Activity speech because it:

- keeps the Acer-class child runtime free of model memory, model storage and generation latency;
- gives authors a reviewable audio result rather than nondeterministic speech at play time;
- makes offline execution and package validation straightforward;
- lets localization bundles refer to stable semantic cues;
- keeps the same character voice recognizable across Activities;
- allows loudness, silence, clipping and pronunciation to be checked before distribution;
- avoids exposing a general text-to-speech authority to untrusted Activities.

Runtime/system TTS remains useful for genuinely dynamic platform-owned speech and for the intentional Dani exception described below.

## 3. Production model policy

### 3.1 Canonical local renderer

The current canonical production renderer is:

```text
MOSS-TTS-Nano
model family: OpenMOSS MOSS-TTS-Nano
size class: approximately 0.1B parameters
purpose: multilingual voice cloning from a canonical reference
primary Mac backend: MLX Audio on Apple Silicon
portable fallback backend: upstream MOSS-TTS-Nano ONNX CPU path
```

MOSS-TTS-Nano is selected because it is small, multilingual, supports voice cloning, and can produce the same character identity in several languages from one approved reference.

The Apple Silicon authoring path should use:

```text
mlx-community/MOSS-TTS-Nano-100M
```

through MLX Audio so generation uses Apple Silicon efficiently. The official ONNX CPU path is the fallback for machines where MLX is unavailable.

### 3.2 Explicitly excluded from the production install

Voice-design models are not part of ordinary local production setup:

- Qwen3-TTS VoiceDesign;
- MOSS-VoiceGenerator;
- any cloud voice-design service.

Those tools may be used separately to create a new candidate reference voice. Once a reference is approved, production uses the lightweight cloning renderer only.

### 3.3 Provider abstraction

Activity Designer must not bind project data directly to one Python package or CLI command. It should address a small provider contract conceptually equivalent to:

```text
generate(
    voice_id,
    locale,
    text,
    output_master_path,
    synthesis_profile,
)
```

The provider resolves the canonical reference and backend internally.

The cache key must include at least:

```text
renderer/model ID + pinned model revision
backend/version
voice ID + voice manifest version
reference SHA-256
locale
normalized full text
synthesis options
post-processing profile version
```

Changing any of these must invalidate the cached output. File names alone are not sufficient cache authority.

## 4. Canonical voice registry v0.1

Canonical production anchors live under:

```text
assets/audio/characters/canonical/v0.1/
```

The full owner-supplied source recordings and the smaller production anchors have different roles:

```text
assets/source/audio/character-voice-masters/v0.1/   full provenance masters
assets/audio/characters/canonical/v0.1/              reviewed production anchors
```

The current production anchors are lossless 12-second FLAC derivations from the beginning of the supplied WAV masters. They preserve the approved voice identity while reducing repeated reference-tokenization, repository size and local batch cost. The exact source and derivative hashes are recorded in `manifest.toml`.

| Character | Voice ID | Production source | Character reason |
|---|---|---|---|
| Lilli | `greia.lilli.v1` | cloned reference | Warm wonder, creativity, stories and imagination |
| Leo | `greia.leo.v1` | cloned reference | Warm, oldish, savvy storyteller; thoughtful guidance without young-teacher energy |
| Flash | `greia.flash.v1` | cloned reference | Bright, quick, playful action and friendly challenge |
| Tito | `greia.tito.v1` | cloned reference | Warm adventurous discovery, nature and investigation |
| Momo | `greia.momo.v1` | cloned reference | Musical, unusual, playful emotion and celebration |
| Dani | `greia.dani.system-v1` | Greia OS TTS | Dani must read unmistakably as a fun robot; the current designed candidates did not preserve that identity |

The character-to-voice mapping is a shared-world identity contract, not a suggestion to change voices per Activity.

### 4.1 Dani is an intentional exception

There is no missing Dani reference in v0.1.

A natural cloned voice that merely sounds cheerful is less correct for Dani than a clearly synthetic platform voice. Until a reviewed robotic reference or a proven lightweight robotic renderer exists, Dani uses Greia OS text-to-speech.

Rules:

- Activity source still addresses semantic character/voice ID `greia.dani.system-v1`;
- the Activity must not select an arbitrary host voice by name;
- the platform/Activity Designer resolves the approved Greia system-TTS profile;
- packaged prerecorded Dani speech may be introduced later only after a reviewed robotic voice is accepted;
- do not silently substitute Dani's system voice for another character;
- do not silently substitute a generic system voice for Lilli, Leo, Flash, Tito or Momo.

The exact OS TTS engine/profile remains an implementation-owned platform decision. This design document does not hard-code a host-specific voice name.

## 5. Reference-master and production-anchor rules

The five full WAV files supplied by the owner are canonical **source masters**. They are not Activity playback assets and are not sent to the child device.

Current common source-master format:

```text
WAV
mono
24,000 Hz
16-bit PCM
approximately 51–67 seconds
```

The local production path uses a reviewed, deterministic anchor derived from each source master:

```text
FLAC
mono
24,000 Hz
16-bit lossless PCM
first 12.0 seconds of the source master
```

Rules:

- preserve the source-master and production-anchor bytes recorded in `manifest.toml`;
- do not normalize, denoise, pitch-shift, compress lossily or overwrite either file in place;
- if a different excerpt is needed, create a new version and record source hash, exact time range and transform;
- use the production FLAC anchor for normal MOSS-TTS-Nano generation;
- do not ship either the source master or production anchor inside an Activity package;
- do not replace a reference because one generated line is imperfect; first review text, locale, punctuation and synthesis settings;
- any accepted replacement increments the voice/reference version and keeps provenance;
- no real-person voice cloning may be introduced without explicit rights, consent and provenance review.

The current references were supplied by the project owner as synthetic character-voice candidates. Before public redistribution, the project must record the final asset-license decision in the governance/licensing authority. Do not invent a license in an Activity package.

## 6. Activity Designer authoring model

Activity Designer should expose speech as semantic data, not as a loose collection of generated filenames.

A conceptual source file may look like:

```yaml
schema_version: 1

cues:
  welcome:
    speaker: lilli
    text:
      it: "Ciao! Giochiamo insieme?"
      en: "Hello! Shall we play together?"
    delivery: warm

  hint.look_again:
    speaker: leo
    text:
      it: "Guardiamo con calma. C'è qualcosa che non abbiamo ancora notato."
      en: "Let's look carefully. There is something we have not noticed yet."
    delivery: gentle

  result.solved:
    speaker: dani
    text:
      it: "Schema completato!"
      en: "Pattern complete!"
    production: system_tts
```

This is an **Activity Designer source concept**, not current `activity.toml` syntax.

The compiler resolves it into the existing localization-bundle audio shape, for example:

```json
{
  "schema_version": 1,
  "locale": "it",
  "direction": "ltr",
  "strings": {
    "welcome": "Ciao! Giochiamo insieme?",
    "hint.look_again": "Guardiamo con calma. C'è qualcosa che non abbiamo ancora notato."
  },
  "audio": {
    "welcome": {
      "path": "locales/it/audio/welcome.ogg",
      "caption_key": "welcome"
    },
    "hint.look_again": {
      "path": "locales/it/audio/hint-look-again.ogg",
      "caption_key": "hint.look_again"
    }
  }
}
```

Gameplay code uses cue IDs. It must not branch on generated filenames or a model/backend name.

## 7. Voice selection in Activities

Choose the speaking character because the character belongs in the experience, not merely because a matching category exists.

Default affinities:

- **Lilli:** imagination, art, stories, gentle welcome, creative encouragement;
- **Leo:** explanation, reflection, language, reading, patient hints, thoughtful discovery;
- **Flash:** energetic starts, timed action, playful retry, reflex challenges;
- **Tito:** exploration, nature, investigation, “let us look over there” discovery;
- **Momo:** music, emotion, silly experiments, expressive celebration;
- **Dani:** logic, sequences, patterns, counting and concise system-like confirmations.

Soft specialization still applies. Characters may support one another and appear outside their home turf. Do not create six isolated content silos.

Avoid assigning a character voice to every possible UI sound. Speech should be purposeful, brief and readable alongside visual communication.

## 8. Writing lines for generation

For ages 3–7:

- keep one cue focused on one idea;
- prefer short, natural sentences;
- use complete localized utterances rather than concatenated fragments;
- write numbers as they should be spoken when pronunciation matters;
- punctuate for intended pacing, then listen to the output;
- avoid unexplained abbreviations, URLs and symbol-heavy strings;
- do not use speech as the only way to discover an essential action;
- keep captions/string equivalents available through semantic keys;
- use the child's resolved UI/content locale according to ADR 0028;
- review every supported locale with a fluent human before release.

Do not encode emotional directions such as `[happy]` into child-visible text unless the selected renderer explicitly owns a reviewed control syntax. Character identity comes primarily from the reference voice and writing/performance, not unportable prompt tricks.

## 9. Batch production workflow

Recommended Activity Designer flow:

1. validate all cue IDs, locales and speaker IDs;
2. resolve the canonical voice manifest;
3. group clone-rendered cues by voice and locale;
4. start one persistent local worker and load the model once;
5. generate review WAV masters into an ignored work directory;
6. reuse content-addressed cache hits;
7. audition outputs in context, including surrounding sound effects;
8. regenerate only rejected cues;
9. post-process accepted masters with a versioned profile;
10. copy/package only final OGG/WAV outputs under `locales/<locale>/audio/`;
11. validate that every audio bundle path exists and stays inside the Activity;
12. keep a generation receipt outside the child package or as non-runtime source metadata.

Do not spawn and reload the model once per sentence.

## 10. Audio post-processing and package policy

The renderer master should remain WAV until approved.

For package output:

- use WAV when lossless phonetic detail or very short clips justify the size;
- otherwise use OGG Vorbis, which is within the current portable localized-audio contract;
- keep speech mono unless a reviewed Activity has a real spatial reason;
- apply bounded loudness normalization consistently;
- prevent clipping;
- trim only excessive leading/trailing silence, never internal expressive pauses blindly;
- do not place music/reverb/background effects into the canonical voice reference;
- do not let sound effects mask initial consonants or overlap spoken prompts.

Activity packages contain generated playback assets only. They must not contain:

```text
model weights
Hugging Face cache
MLX/PyTorch/ONNX environments
pip/uv/conda state
canonical reference masters
voice-design prompts
cloud credentials
```

A package may keep compact source-side generation metadata if the project later standardizes it, but runtime authority remains the localization bundle and packaged audio path.

## 11. Review and acceptance

Every generated cue requires human audio review. Structural validation cannot decide that a line sounds warm, old, robotic, correctly stressed or emotionally appropriate.

Review at least:

- correct character identity;
- correct language and pronunciation;
- exact intended text with no omitted/repeated words;
- child-safe tone;
- intelligibility on small speakers;
- no clipping/noise/reverb contamination;
- beginning consonants are not cut;
- no excessive silence;
- no overlap with adjacent prompts or sound effects;
- consistent perceived loudness;
- caption/string parity;
- correct cue-to-file mapping.

For educational phonemes, syllables, spelling and language-learning content, review is stricter: a fluent speaker/educator must approve the exact pronunciation. Generic TTS quality is not sufficient evidence.

## 12. Failure and fallback policy

At authoring time:

- a failed generation leaves the previous accepted asset untouched;
- no output is accepted merely because the command exited zero;
- store error details and the cache/input identity;
- allow explicit retry/regeneration;
- never silently switch character, reference, locale or provider.

At child runtime:

- packaged audio failure must fail soft without crashing the Activity;
- visual affordances remain sufficient to continue where product scope requires zero-text dependency;
- Dani's approved system-TTS path may be used when the platform owns and exposes it;
- other characters do not fall back to arbitrary system speech without an explicit future policy.

## 13. Privacy, safety and provenance

- production is local by default;
- Activity text must not be sent to a cloud service silently;
- voice references are project assets and must not be uploaded to third-party services by an agent without explicit owner authorization;
- generated speech must not impersonate a real person;
- preserve source method, approval, hashes, model/backend version and public-release license status;
- do not claim a synthetic voice is a human performer;
- keep model and dependency licenses in the development-tooling attribution record.

## 14. Current implementation boundary and next steps

Accepted now:

- five owner-supplied canonical reference masters;
- MOSS-TTS-Nano as the lightweight cloning renderer;
- MLX Audio as the preferred Apple Silicon production backend;
- upstream ONNX CPU as the portable fallback direction;
- Dani resolved through Greia OS TTS;
- build-time localized audio packaging;
- the Activity-authoring rules in this document and the Activity skill.

Not yet implemented by this documentation tranche:

- an Activity Designer voice UI;
- a canonical speech-source schema parser;
- a production worker/service and cache;
- generation receipts;
- automated post-processing;
- runtime/system-TTS API details for Dani;
- package validation beyond current ordinary localization audio rules.

When implementing those pieces, preserve current authority boundaries: exact APIs/schemas belong in source and tests; architectural expansion may require an ADR; `skills/greia-activity-authoring/SKILL.md` must remain synchronized.
