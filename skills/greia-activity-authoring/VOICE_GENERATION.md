# Voice Generation for Greia Activities

This is the focused speech-production companion to `SKILL.md`.

For deciding **when and why** an Activity should use a canonical presenter, spoken presentation, or researched curiosity facts, read first:

```text
skills/greia-activity-authoring/PRESENTERS_AND_CURIOSITY.md
```

Then read the speech authorities:

```text
docs/design/GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md
docs/design/GREIA_SHARED_CHARACTER_UTTERANCES.md
docs/adr/0032-profile-presentation-and-grammatical-agreement.md
```

For optional local character-voice setup and field troubleshooting:

```text
docs/agents/GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md
docs/agents/GREIA_CHATTERBOX_PRODUCTION_FIELD_GUIDE.md
```

For producing the shared character-reaction library:

```text
docs/agents/GREIA_SHARED_CHARACTER_UTTERANCE_RECORDING.md
```

## 1. Mandatory speech classification

Before generating or adding speech, classify the cue by **semantic purpose**:

```text
character_dialogue
shared_character_utterance
pedagogical_speech
dani_system_speech
```

Do not choose the production path from text length alone.

Examples:

```text
"Vai!"                                      -> character_dialogue
"Le orche vivono in gruppi familiari..."   -> character_dialogue / curiosity fact
"ma"                                        -> pedagogical_speech when the syllable itself is taught
"Ottimo lavoro!"                            -> shared_character_utterance when generic praise is sufficient
Dani explanation                            -> dani_system_speech
```

The governing rule is:

> If the sound itself is the educational truth being taught, use pedagogical/system speech. If speech communicates content through a character, use character speech.

A researched factual sentence is normally **character dialogue**, because the knowledge is being communicated through the presenter; it is not pronunciation-authoritative pedagogical speech.

## 2. Speech design is mandatory to consider; the custom voice toolchain is optional

Do not confuse these two things.

For every new Activity, the authoring/design pass must explicitly consider:

```text
lead presenter/mascot
shared character reactions
custom Activity-specific dialogue
pedagogical speech, if any
optional curiosity/fact narration, if appropriate
supported locales and spoken coverage
```

The decision may legitimately be "no custom speech" or even "no presenter" for a specific Activity, but it must be deliberate.

A normal Activity authoring environment is **not required** to have Chatterbox or any cloning model installed. That means the **production backend** is optional, not the speech architecture.

When creating or modifying an Activity:

1. decide whether a canonical character should present/guide the Activity;
2. decide whether subject-specific curiosity facts would enrich it;
3. prefer a Greia shared character utterance when a generic cue is enough;
4. route letters/syllables/phonics/pronunciation to the pedagogical/system path;
5. use custom character dialogue for presenter lines, contextual hints, narration and researched facts when valuable;
6. model every cue with stable semantic IDs and localization from the beginning;
7. only then probe the local custom-voice toolchain without installing anything;
8. if it is unavailable and the user did not explicitly ask for voice-toolchain setup, keep the semantic/localized speech plan ready, use available shared/system paths, and report custom audio as unavailable/pending rather than hard-coding one locale or impersonating a character with arbitrary TTS;
9. preserve visual/text interaction so optional character audio failure never makes the core Activity unusable.

Do not silently install models, create a multi-gigabyte environment, or download weights because a character could say a line.

Do not block Activity creation merely because custom voice generation is unavailable, but do not erase the intended presenter/speech design because of that local limitation either.

## 3. Multilingual-ready is mandatory from the first speech implementation

Activity speech must not be designed as Italian strings in gameplay code with localization added later.

Use stable semantic cue IDs:

```text
presenter.welcome
presenter.hint.first
curiosity.orca.family_pods
curiosity.orca_unique_calls
```

Runtime code requests semantic cues. Localization owns wording.

For every locale the Activity claims to support:

- provide reviewed localized text for the cue;
- keep the same semantic meaning across locales;
- use the same canonical speaker identity for localized character dialogue;
- generate/review localized audio when custom voice is part of the accepted feature;
- resolve grammatical child-address variants before choosing/playing the audio;
- keep displayed and spoken wording aligned;
- never make gameplay/scoring depend on locale or on which spoken variant is selected.

A multilingual Activity must not ship a presenter or curiosity button that works only in one language while silently falling back to unrelated wording in another.

If custom voice production is temporarily unavailable for one locale, record that coverage gap honestly. Text fallback may preserve function where the product allows optional speech degradation, but it does **not** mean multilingual voice production is complete.

## 4. Non-mutating toolchain probe

There is not yet one canonical Greia provider-probe command. Until one exists, inspect the environment that the user/agent already uses and perform only non-mutating checks.

Examples may include:

```text
- the configured Chatterbox virtual environment exists;
- its Python can import the installed Chatterbox/MLX implementation;
- the configured model/checkpoint is already available or the user has explicitly authorized its download;
- ffmpeg and ffprobe are available if short-clip analysis/post-processing is required;
- canonical Greia reference files exist and match the voice manifest.
```

Do not treat `pip` being available as evidence that Chatterbox is installed.

If no previously configured Chatterbox environment can be identified, classify custom character generation as `UNAVAILABLE`, not as an invitation to install it.

If the user explicitly requests installation/configuration, follow:

```text
docs/agents/GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md
```

## 5. Canonical character speech

Current character voice IDs:

| Speaker | Voice ID | Use when |
|---|---|---|
| Lilli | `greia.lilli.v1` | wonder, creativity, stories, art, gentle encouragement |
| Leo | `greia.leo.v1` | reading, language, patient explanation, reflective hints, knowledge moments |
| Flash | `greia.flash.v1` | action, speed, games, lively retries |
| Tito | `greia.tito.v1` | exploration, nature, investigation, adventure, discovery facts |
| Momo | `greia.momo.v1` | music, emotion, silliness, experimentation, celebration |
| Dani | `greia.dani.system-v1` | logic, patterns, numbers and clearly robotic feedback |

For Lilli/Leo/Flash/Tito/Momo, the current optional local renderer is **Chatterbox Multilingual V3**.

For Dani, use the Greia system-TTS policy. Dani intentionally has no cloning anchor in v0.1.

Never use arbitrary host system TTS to impersonate Lilli, Leo, Flash, Tito or Momo.

## 6. Presenter and curiosity/fact dialogue

Custom character dialogue is especially appropriate for:

```text
brief welcome/orientation
contextual hints
short story/narration beats
Activity-specific explanation
optional researched curiosity facts
```

A subject-rich Activity should consider a small fact pool when it genuinely adds curiosity. Example:

```text
Baia delle Orche
-> child presses a small curiosity/info affordance
-> Tito or Leo speaks one short, researched orca fact
-> fact is also available as localized text
-> next request selects another reviewed fact without immediate repetition
```

Facts must be researched and provenance-recorded according to:

```text
skills/greia-activity-authoring/PRESENTERS_AND_CURIOSITY.md
```

Never ask an LLM at runtime to invent a fact. Never require network access on the child device to retrieve one.

Fact selection is presentation-only. It must not affect correctness, score, rewards, difficulty or progression.

## 7. MOSS and triple repetition are rejected

Do not use MOSS-TTS-Nano for Greia production character speech. Local evaluation found its quality unsuitable.

Do not use the `ma. ma. ma.` / repeated-generation-middle-extraction technique for micro speech. Local testing made output worse.

These are retained lessons, not fallback choices.

## 8. Short character dialogue

Chatterbox can produce extra tail sounds on ultra-short character utterances.

For short **character dialogue only**, a production worker may use:

```text
bounded output-token limit
+ audio analysis
+ bounded leading/trailing trim
+ mandatory human review
```

This may be appropriate for lines such as:

```text
"Vai!"
"Wow!"
"Ancora!"
```

It is **not** a way to make Chatterbox trustworthy for teaching syllables or phonemes.

If the intended sound is internally wrong, reject it. Do not cut/splice the waveform until it appears correct.

## 9. Pedagogical speech

Use deterministic/native/system TTS when teaching:

```text
letters
letter names
syllables
phonics
spelling units
pronunciation
foreign-language target sounds
```

Correctness and consistency outrank natural character identity.

The future abstraction is `PedagogicalSpeechProvider`; Activity code must not hard-code macOS, Windows, Linux or individual host voice names.

For static assets, Activity Designer may render through an approved native/system provider and package the reviewed result. Dynamic child-runtime TTS, when implemented, must remain a Greia platform service.

A fluent speaker/educator must review pronunciation-critical outputs.

## 10. Shared character utterances: prefer semantic families first

When the Activity needs generic feedback, use the Greia shared utterance library instead of generating a new custom line.

Initial semantic families:

```text
praise.general
celebrate.success
encourage.retry
encourage.progress
ready.go
```

Each character/locale/family resolves to a **non-empty array of reviewed recordings**. Activities never choose a concrete phrase, filename, or variant number.

Conceptually:

```text
Activity requests character + semantic family + locale
-> Greia resolves locale/agreement fallback
-> Greia gets the reviewed variant array
-> one file: use it
-> multiple files: randomly choose one
-> Greia presents the family-level canonical expression/motion
```

The v0.1 source wording provides three neutral Italian and three English variants per family. Exact wording, the 180-clip full target, random-picker rules, and animation mappings are defined in:

```text
docs/design/GREIA_SHARED_CHARACTER_UTTERANCES.md
```

Rules for Activity authors/agents:

- request the **family**, not `01`, `02`, `03`, text, or filename;
- do not reproduce the same shared files inside an Activity package;
- do not assume three recordings exist: one accepted variant is sufficient;
- do not branch gameplay based on which random variant is selected;
- random selection is presentation-only and must never change scoring, rewards, correctness, difficulty, or progression;
- if a shared family is unavailable on the target platform version, fail soft to visual feedback;
- if generic shared feedback is sufficient, do not generate custom Chatterbox dialogue merely to get different wording.

If producing or extending the shared library itself, follow:

```text
docs/agents/GREIA_SHARED_CHARACTER_UTTERANCE_RECORDING.md
```

## 11. Child-directed grammatical agreement

Greia exposes a small semantic grammatical selector for the active child:

```text
neutral
masculine
feminine
```

This selector exists only so localization can choose wording that addresses the child correctly. It must not select Activities, subjects, difficulty, rewards, interests, characters, permissions, or gameplay.

Prefer a natural neutral base phrase whenever possible. Create masculine/feminine variants only where the target language genuinely benefits from them.

Italian example:

```text
feedback.correct             -> "Ottimo lavoro!"
feedback.correct.masculine   -> "Bravo!"
feedback.correct.feminine    -> "Brava!"
```

The base semantic cue is the required same-locale neutral fallback. Masculine/feminine entries are optional.

For future gender-aware shared utterance arrays, resolve the grammatical form **before** random phrase selection. Never put masculine, feminine and neutral recordings into the same random array.

If a cue is both displayed and spoken, text and audio must resolve through the **same** wording/grammatical variant. For Activity-owned static audio, generate each supported wording with the same canonical speaker voice:

```text
feedback.correct             -> locales/it/audio/feedback-correct-neutral.ogg
feedback.correct.masculine   -> locales/it/audio/feedback-correct-masculine.ogg
feedback.correct.feminine    -> locales/it/audio/feedback-correct-feminine.ogg
```

At runtime:

### 11.1 Gender-Neutral Spoken & Written Praise (MANDATORY)

**Never use gender-specific adjectives for verbal or written praise in Italian (or any other language)** such as *"Bravissimo!"*, *"Bravissima!"*, *"Bravo!"*, or *"Brava!"*. 

Always use universal, inclusive gender-neutral praise:
- `Ottimo lavoro!` ("Great job!")
- `Ben fatto!` ("Well done!")
- `Esatto!` ("Exactly right!")
- `Fantastico!` ("Fantastic!")
- `Evviva!` ("Hooray!")
- `Perfetto!` ("Perfect!")
- `Super!` ("Super!")
- `Che meraviglia!` ("Wonderful!")

This ensures every child feels welcomed and encouraged without requiring gendered grammar branches or incorrect gendered adjectives.

## 12. Writing custom character lines

For custom Chatterbox generation:

```text
semantic cue ID
-> exact localized text
-> canonical character
-> decide whether grammatical variants are genuinely needed
-> generate review WAV(s) for each shipped locale/variant in scope
-> listen and review
-> regenerate/reject as needed
-> bounded post-process
-> package final OGG/WAV
-> verify text/audio locale + variant parity
```

Prefer complete natural utterances over concatenated fragments.

Do not generate pronunciation-authoritative fragments as character dialogue merely to preserve mascot voice.

## 13. Human audio gate

Reject custom character speech for:

- wrong/drifting character identity;
- wrong language;
- omitted, repeated or invented words/sounds;
- bad stress/pronunciation;
- clipped start/end;
- unwanted generated tail;
- noise/distortion;
- inappropriate delivery.

Reject pedagogical speech for any incorrect or ambiguous target sound even if the voice sounds pleasant.

For shared utterance libraries, reject only the bad recording from the family array when the other reviewed variants remain valid. Never keep a broken file as an empty/random slot.

For grammatical variant sets, also reject the set if delivery, pacing or energy differs enough that masculine/feminine selection sounds like a different character performance rather than the same cue with different wording.

A successful model/process exit is never audio acceptance.

## 14. Audio analysis

FFmpeg/ffprobe are the preferred cross-platform authoring primitives for:

```text
metadata inspection
silence/tail analysis
bounded trim
loudness/clipping inspection
package conversion
```

Audio analysis is transport/post-processing, not semantic repair.

Keep generated masters as WAV during review. Package reviewed WAV when phonetic detail/very short duration justify it; otherwise use the current supported OGG path.

## 15. Activity degradation behavior

When custom voice generation is unavailable:

Good:

```text
- preserve the presenter/speech semantic plan;
- use shared Greia praise/reaction families;
- use deterministic pedagogical speech for teaching sounds;
- keep localized captions/visual instructions;
- omit or mark pending optional custom mascot audio;
- finish and validate the Activity normally when the missing audio is genuinely optional.
```

Bad:

```text
- auto-install Chatterbox;
- silently download model weights;
- use a random OS voice as Lilli/Leo/Flash/Tito/Momo;
- hard-code only one language because generation is inconvenient;
- remove essential instructional information because speech could not be generated;
- claim multilingual voice coverage that was not produced/reviewed;
- fail the Activity build solely because optional character audio is absent.
```

If custom character speech is an explicit owner requirement rather than an optional enhancement, report the missing toolchain and use the setup guide.

## 16. Package boundary

Never package:

```text
Chatterbox/model weights
model caches
Python/MLX/PyTorch environments
canonical reference masters
FFmpeg binaries merely because authoring used them
voice-design models
```

Package only reviewed Activity-owned playback assets. Shared Greia character utterances remain platform assets.
