# Greia Shared Character Utterances — Production & Review

**Purpose:** produce and review Greia's central shared reaction library through the canonical Voice Production Engine.  
**Languages:** Italian (`it`) and English (`en`).  
**Characters:** Lilli, Leo, Flash, Tito, Momo and Dani.

## 1. Canonical production rule

Use:

```text
tools/record_shared_character_utterances.py
```

That script is a thin semantic producer over `VoiceEngine`. It must remain free of direct Chatterbox, Whisper, native-TTS and FFmpeg implementation logic.

Do not use the historical direct Chatterbox recording mechanics for new library production.

Read first:

```text
AGENTS.md
SETUP.md
skills/greia-voice-production/SKILL.md
tools/greia_voice_core/README.md
docs/design/GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md
docs/design/GREIA_SHARED_CHARACTER_UTTERANCES.md
```

If the production environment needs installation or troubleshooting:

```text
docs/agents/GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md
```

The Chatterbox field guide is only for Voice Engine maintainers diagnosing provider internals.

## 2. What the engine does

For this library every line is submitted as:

```text
kind = shared_character_utterance
```

Routing is automatic:

```text
Lilli/Leo/Flash/Tito/Momo -> canonical cloned-character provider
Dani                       -> deterministic system/native provider
```

Suitable multi-word cloned-character lines may receive advisory Whisper verification. Tiny reactions and Dani normally skip ASR.

The engine owns:

```text
canonical voice/reference selection and hash validation
model loading/reuse
single-worker protection
MLX cache cleanup
short-output limits/trim rules
native TTS profiles
optional Whisper checks
WAV production
receipts
```

The recording runbook does not duplicate those mechanics.

## 3. Before production

Run the non-mutating readiness probe:

```bash
python3 tools/greia_voice.py doctor
```

If a needed provider is unavailable, follow the engine installation guide. Do not silently substitute another TTS backend.

Default review workspace:

```text
./tmp/shared-character-utterances/
```

Generated/rejected review material is not a runtime asset and must not be committed as accepted library content until human review is complete.

## 4. Produce the library

Full current phrase matrix:

```bash
python3 tools/record_shared_character_utterances.py
```

Optional subset during testing/review:

```bash
python3 tools/record_shared_character_utterances.py \
  --characters leo,dani
```

The script keeps one engine/model warm, holds the global generation lock for the complete run and refuses to overwrite an existing audio/receipt candidate blindly.

Expected output shape:

```text
tmp/shared-character-utterances/
  lilli/it/*.wav
  lilli/en/*.wav
  leo/...
  flash/...
  tito/...
  momo/...
  dani/...
  review.csv
```

Each newly generated audio file also has:

```text
<audio>.receipt.json
```

All engine-generated candidates remain `human_review = PENDING`.

## 5. Phrase matrix

Each semantic family has three interchangeable source variants.

### `praise.general`

Italian:

```text
Complimenti!
Ottimo lavoro!
Ben fatto!
```

English:

```text
Congratulations!
Great work!
Well done!
```

Default animation:

```text
expression: happy
motion: happy_hop
```

### `celebrate.success`

Italian:

```text
Ce l'hai fatta!
Evviva!
Che meraviglia!
```

English:

```text
You did it!
Hooray!
Wonderful!
```

Default animation:

```text
expression: happy
motion: celebrate_pop
```

### `encourage.retry`

Italian:

```text
Riproviamo!
Quasi! Proviamo ancora!
Ancora una volta!
```

English:

```text
Let's try again!
Almost! Let's try again!
One more time!
```

Default animation:

```text
expression: happy
motion: idle_bounce
```

### `encourage.progress`

Italian:

```text
Continua così!
Ci sei quasi!
Vai avanti!
```

English:

```text
Keep going!
Almost there!
You're doing great!
```

Default animation:

```text
expression: happy
motion: idle_bounce
```

### `ready.go`

Italian:

```text
Forza, andiamo!
Ci siamo? Via!
Si parte!
```

English:

```text
Come on, let's go!
Ready? Go!
Here we go!
```

Default animation:

```text
expression: happy
motion: happy_hop
```

Preserve punctuation exactly. These are reactions and should remain lively.

## 6. Expected candidate count

```text
6 characters
× 5 semantic families
× 3 variants
× 2 locales
= 180 review candidates
```

The five natural characters use their canonical cloned identities. Dani uses his system-TTS identity. Never clone a natural character voice for Dani.

## 7. Naming

Stable example filenames:

```text
lilli__it__praise.general__01.wav
leo__en__ready.go__03.wav
dani__it__encourage.retry__02.wav
```

Variant numbers correspond to phrase order here. Do not encode model parameters/seeds in canonical names.

## 8. Machine result vs human review

`review.csv` initially records machine-production dispositions such as:

```text
REVIEW_REQUIRED
REVIEW_REQUIRED_ASR_WARNING
EXISTING_REVIEW_CANDIDATE
UNAVAILABLE
REJECTED
BLOCKED_PARTIAL_OUTPUT
```

These are **not human acceptance results**.

During human review, record/derive a separate final disposition such as:

```text
ACCEPT
REGENERATE
BAD_PRONUNCIATION
EXTRA_SPEECH
WRONG_WORDS
VOICE_DRIFT
CLIPPED
OTHER
```

`ACCEPT` requires:

- exact words;
- correct locale/pronunciation;
- no invented/repeated sounds;
- no unwanted tail;
- no clipped initial/final sound;
- correct canonical character identity where applicable;
- suitable delivery and small-speaker intelligibility.

For Dani, verify that the selected system voice remains clearly synthetic/robotic enough for the character identity.

Whisper PASS never substitutes for this listening gate.

## 9. Preserve character personality

Do not normalize all characters into the same performance style.

Desired identities remain approximately:

```text
Lilli -> warm and delighted
Leo   -> warm, older, quietly pleased
Flash -> lively and energetic
Tito  -> adventurous and encouraging
Momo  -> playful and expressive
Dani  -> concise, fun and clearly robotic
```

Variants within one family are interchangeable in meaning, not identical performances.

## 10. Runtime shared-family contract

Activities do not choose generated filenames or variant numbers. They request only:

```text
character
semantic family
locale
```

Greia owns the reviewed available array:

```text
one accepted file       -> use it
multiple accepted files -> choose a reviewed variant for presentation variety
```

A rejected/missing variant is simply absent. Random selection must never affect score, correctness, rewards, difficulty or progression.

This recording tool is authoring-only; it does not create child-runtime synthesis.

## 11. Evidence to return

Return:

```text
1. exact Greia git SHA
2. `doctor` result
3. output directory
4. review.csv
5. generated/existing/blocked count per character + locale
6. representative receipt(s)
7. any phrase that repeatedly failed
8. human accepted/rejected count after listening
9. whether all 180 intended variants are accepted or which remain absent
```

Do not hide failures and do not commit model environments, caches, canonical references or rejected review audio.
