# Greia Shared Character Utterances — Local Recording Instructions

**Purpose:** generate and review the first shared Greia character-reaction library with Chatterbox Multilingual V3.  
**Languages:** Italian (`it`) and English (`en`).  
**Characters:** Lilli, Leo, Flash, Tito, Momo. Dani is **not** generated with Chatterbox; leave Dani for the Greia system-TTS profile.

## 1. Read first

From the Greia repository root, read:

```text
AGENTS.md
SETUP.md
docs/design/GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md
docs/design/GREIA_SHARED_CHARACTER_UTTERANCES.md
skills/greia-activity-authoring/VOICE_GENERATION.md
assets/audio/characters/canonical/v0.1/manifest.toml
```

Use the Chatterbox installation that is already known to work on this machine. Do not reinstall or change model/backend versions for this task.

## 2. Output location

Work under a project-local temporary directory:

```text
./tmp/shared-character-utterances/
```

Recommended structure:

```text
tmp/shared-character-utterances/
  lilli/
    it/
    en/
  leo/
    it/
    en/
  flash/
    it/
    en/
  tito/
    it/
    en/
  momo/
    it/
    en/
  review.csv
```

Do not commit generated files until they have been listened to and accepted.

## 3. Generation rules

For every line:

- use the character's canonical reference voice;
- use the correct language/locale;
- preserve the punctuation below exactly;
- **keep the exclamation marks**: these are reactions and should sound alive;
- do not use the rejected `ma. ma. ma.` repetition technique;
- use the already-tested bounded Chatterbox output-token limit for short speech;
- if Chatterbox adds an unwanted tail, use the established FFmpeg/audio-analysis trim path;
- trimming may remove only unwanted leading/trailing material;
- if pronunciation, words, or voice identity are wrong **inside** the intended phrase, reject and regenerate rather than editing the speech;
- listen to every accepted clip.

Do not over-tune the model per phrase. Prefer regeneration over a growing pile of per-line parameters.

## 4. Phrases to generate

Each semantic family has three interchangeable variants. Generate **all three variants for every character and both languages**.

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

Default animation family:

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

Default animation family:

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

Default animation family:

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

Default animation family:

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

Default animation family:

```text
expression: happy
motion: happy_hop
```

## 5. Naming

Use stable variant numbers. Example:

```text
lilli__it__praise.general__01.wav
lilli__it__praise.general__02.wav
lilli__it__praise.general__03.wav

leo__en__ready.go__01.wav
leo__en__ready.go__02.wav
leo__en__ready.go__03.wav
```

Variant numbers correspond to the phrase order in this document.

Do not encode model parameters or random seeds into the final canonical filename.

## 6. Expected recording count

Chatterbox batch:

```text
5 cloned characters
× 5 semantic families
× 3 variants
× 2 languages
= 150 reviewed Chatterbox clips
```

Dani is separate:

```text
1 character
× 5 semantic families
× 3 variants
× 2 languages
= 30 future Greia system-TTS clips
```

Final complete shared library target:

```text
180 clips
```

Do not generate Dani through Lilli/Leo/Flash/Tito/Momo or an arbitrary natural voice.

## 7. Review

Create `review.csv` with:

```text
character,locale,family,variant,text,file,result,notes
```

Allowed results:

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
- correct Italian/English pronunciation;
- no invented/repeated sounds;
- no unwanted tail;
- no clipped initial consonant;
- recognisable canonical character identity;
- pleasant short-reaction delivery;
- no excessive silence;
- no obvious audio artifact.

For these shared reactions, energetic delivery is desirable. The exclamation marks are intentional.

## 8. Do not normalize away character personality

The five characters should remain distinguishable. Do not force identical pitch, speed or emotional contour.

The phrases within one semantic family are interchangeable in **meaning**, not identical in performance.

A good result is:

```text
Lilli → warm and delighted
Leo   → warm, older, quietly pleased
Flash → lively and energetic
Tito  → adventurous and encouraging
Momo  → playful and expressive
```

while preserving the exact words.

## 9. Random-variant system contract

Activities do **not** select filenames or variant numbers.

They request only:

```text
character
semantic family
locale
```

Example:

```text
character = "lilli"
utterance = "praise.general"
locale = "it"
```

Greia owns the reviewed array of available files.

Conceptually:

```python
variants = catalogue[character][locale][utterance]

if len(variants) == 1:
    selected = variants[0]
else:
    selected = random.choice(variants)
```

Therefore:

- one reviewed file is completely valid and is always selected;
- adding a second or third reviewed file automatically adds variety;
- a missing/rejected variant is simply absent from the available array;
- Activities never depend on `01`, `02`, or `03`;
- all variants inside one array must be semantically safe substitutes;
- animation is selected from the semantic family, not from the filename.

Do not create separate Activity logic for each phrase.

## 10. Evidence to return

Return:

```text
1. Greia git SHA
2. Chatterbox model/backend/version
3. canonical reference hashes used
4. exact Chatterbox short-output/token settings
5. output directory
6. review.csv
7. accepted/rejected count per character and language
8. any phrase that repeatedly failed
9. representative accepted clips for each character
10. whether all 150 Chatterbox-target clips were accepted
```

Do not hide failed generations. Keep rejected files in the temporary evidence directory until review is complete.

Do not package models, Chatterbox environments, canonical reference voices, or temporary generations into an Activity.
