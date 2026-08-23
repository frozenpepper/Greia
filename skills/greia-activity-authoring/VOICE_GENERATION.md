# Voice Generation for Greia Activities

This is the focused speech companion to `SKILL.md`.

Read first:

```text
docs/design/GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md
docs/design/GREIA_SHARED_CHARACTER_UTTERANCES.md
docs/adr/0032-profile-presentation-and-grammatical-agreement.md
```

For optional local character-voice setup:

```text
docs/agents/GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md
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
"Vai!"           → character_dialogue
"ma"             → pedagogical_speech when the syllable itself is taught
"Ottimo lavoro!" → shared_character_utterance when generic praise is sufficient
Dani explanation → dani_system_speech
```

The governing rule is:

> If the sound itself is the educational truth being taught, use pedagogical/system speech. If speech communicates content through a character, use character speech.

## 2. Voice support is optional

A normal Activity authoring environment is **not required** to have Chatterbox or any cloning model installed.

When creating or modifying an Activity:

1. decide whether speech genuinely improves the Activity;
2. prefer a Greia shared character utterance when a generic cue is enough;
3. route letters/syllables/phonics/pronunciation to the pedagogical/system path;
4. only consider custom cloned character dialogue after those checks;
5. probe the local custom-voice toolchain without installing anything;
6. if it is unavailable and the user did not explicitly ask for voice-toolchain setup, **drop optional custom character voice support** and continue building the Activity;
7. preserve visual/text interaction so the Activity remains complete without custom character audio.

Do not silently install models, create a multi-gigabyte environment, or download weights because a character could say a line.

Do not block Activity creation merely because custom voice generation is unavailable.

## 3. Non-mutating toolchain probe

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

## 4. Canonical character speech

Current character voice IDs:

| Speaker | Voice ID | Use when |
|---|---|---|
| Lilli | `greia.lilli.v1` | wonder, creativity, stories, art, gentle encouragement |
| Leo | `greia.leo.v1` | reading, language, patient explanation, reflective hints |
| Flash | `greia.flash.v1` | action, speed, games, lively retries |
| Tito | `greia.tito.v1` | exploration, nature, investigation, adventure |
| Momo | `greia.momo.v1` | music, emotion, silliness, experimentation, celebration |
| Dani | `greia.dani.system-v1` | logic, patterns, numbers and clearly robotic feedback |

For Lilli/Leo/Flash/Tito/Momo, the current optional local renderer is **Chatterbox Multilingual V3**.

For Dani, use the Greia system-TTS policy. Dani intentionally has no cloning anchor in v0.1.

Never use arbitrary host system TTS to impersonate Lilli, Leo, Flash, Tito or Momo.

## 5. MOSS and triple repetition are rejected

Do not use MOSS-TTS-Nano for Greia production character speech. Local evaluation found its quality unsuitable.

Do not use the `ma. ma. ma.` / repeated-generation-middle-extraction technique for micro speech. Local testing made output worse.

These are retained lessons, not fallback choices.

## 6. Short character dialogue

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

## 7. Pedagogical speech

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

## 8. Shared character utterances: prefer semantic families first

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
→ Greia resolves locale/agreement fallback
→ Greia gets the reviewed variant array
→ one file: use it
→ multiple files: randomly choose one
→ Greia presents the family-level canonical expression/motion
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

## 9. Child-directed grammatical agreement

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
feedback.correct             → "Ottimo lavoro!"
feedback.correct.masculine   → "Bravo!"
feedback.correct.feminine    → "Brava!"
```

The base semantic cue is the required same-locale neutral fallback. Masculine/feminine entries are optional.

For future gender-aware shared utterance arrays, resolve the grammatical form **before** random phrase selection. Never put masculine, feminine and neutral recordings into the same random array.

If a cue is both displayed and spoken, text and audio must resolve through the **same** wording/grammatical variant. For Activity-owned static audio, generate each supported wording with the same canonical speaker voice:

```text
feedback.correct             → locales/it/audio/feedback-correct-neutral.ogg
feedback.correct.masculine   → locales/it/audio/feedback-correct-masculine.ogg
feedback.correct.feminine    → locales/it/audio/feedback-correct-feminine.ogg
```

At runtime:

```python
from greia_platform.activity_api import get_profile_grammatical_gender

variant = get_profile_grammatical_gender().value
caption = resources.text("feedback.correct", variant=variant)
voice = resources.audio_cue("feedback.correct", variant=variant)
```

Do not hand-code Italian logic such as `if boy: "bravo"` inside gameplay. Localization owns language-specific words; Greia provides only the semantic selector.

The selector does not change the speaker. If Lilli says `Bravo!` or `Brava!`, both versions remain Lilli. For Dani/system speech, resolve the localized text with the same selector before passing it to the approved system-TTS path.

Keep this selector deliberately small. If a future language needs richer plural/case/select semantics, extend localization deliberately rather than inventing Activity-specific suffix vocabularies.

## 10. Writing custom character lines

For custom Chatterbox generation:

```text
semantic cue ID
→ exact localized text
→ canonical character
→ decide whether grammatical variants are genuinely needed
→ generate review WAV(s)
→ listen and review
→ regenerate/reject as needed
→ bounded post-process
→ package final OGG/WAV
→ verify text/audio variant parity where variants exist
```

Prefer complete natural utterances over concatenated fragments.

Do not generate pronunciation-authoritative fragments as character dialogue merely to preserve mascot voice.

## 11. Human audio gate

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

## 12. Audio analysis

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

## 13. Activity degradation behavior

When custom voice generation is unavailable:

Good:

```text
- use shared Greia praise/reaction families;
- use deterministic pedagogical speech for teaching sounds;
- keep captions/visual instructions;
- omit optional custom mascot dialogue;
- finish and validate the Activity normally.
```

Bad:

```text
- auto-install Chatterbox;
- silently download model weights;
- use a random OS voice as Lilli/Leo/Flash/Tito/Momo;
- remove essential instructional information because speech could not be generated;
- fail the Activity build solely because optional character audio is absent.
```

If custom character speech is an explicit owner requirement rather than an optional enhancement, report the missing toolchain and use the setup guide.

## 14. Package boundary

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
