# Greia Voice Generation and Canonical Character Voices

**Status:** accepted Activity-authoring / Activity Designer direction; production compiler/runtime integration pending  
**Date:** 2026-08-23  
**Scope:** optional local character-voice production, deterministic pedagogical speech, shared character utterances, localized package audio, and the Dani system-TTS identity  
**Related authorities:** `docs/adr/0028-platform-and-activity-localization-language-context.md`, `docs/design/GREIA_CANONICAL_CAST_SYSTEM.md`, `docs/design/GREIA_SHARED_CHARACTER_UTTERANCES.md`, `skills/greia-activity-authoring/VOICE_GENERATION.md`

## 1. Core decision: speech has different semantic jobs

Greia must not treat all speech as one TTS problem.

```text
A. CHARACTER SPEECH
   personality, narration, reactions, instructions, story/dialogue
   → canonical character identity
   → optional local Chatterbox Multilingual V3 authoring
   → human-reviewed prerecorded Activity audio

B. SHARED CHARACTER UTTERANCES
   praise, success, retry, progress, start reactions
   → OS/shared asset library
   → semantic family with one or more reviewed recordings
   → Greia randomly selects one available reviewed variant
   → no per-Activity voice-generation toolchain required

C. PEDAGOGICAL SPEECH
   letters, letter names, syllables, phonics, spelling/pronunciation targets
   → deterministic/system/native TTS path
   → correctness and consistency outrank character identity

D. DANI
   clearly robotic character identity
   → Greia system-TTS profile
```

The governing rule is:

> **If the sound itself is the educational truth being taught, use pedagogical speech. If speech communicates content through a character, use character speech.**

Text length is not the selector. `Vai!` may be character dialogue; `mamma` may be a pronunciation target.

## 2. Evaluated renderer policy

Local evaluation established:

- **MOSS-TTS-Nano is REJECTED** for Greia production quality;
- **Chatterbox Multilingual V3** produces substantially better natural character speech and voice similarity and is the current optional local character-speech renderer;
- Chatterbox is not reliable enough for pronunciation-authoritative individual letters/syllables;
- bounded generated-token output plus bounded FFmpeg analysis/cutting is useful for unwanted tails on short **character reactions**;
- the repeated `ma. ma. ma.` / middle-extraction workaround made results worse and is **REJECTED**;
- a wrong or inconsistent pedagogical syllable must never be accepted merely because the voice sounds good.

Do not reopen MOSS or triple repetition as silent fallbacks.

## 3. Canonical character speech

Current character voice IDs:

| Character | Voice ID | Character reason |
|---|---|---|
| Lilli | `greia.lilli.v1` | warm wonder, creativity, stories and imagination |
| Leo | `greia.leo.v1` | warm oldish savvy storyteller; thoughtful guidance without young-teacher energy |
| Flash | `greia.flash.v1` | bright, quick, playful action and friendly challenge |
| Tito | `greia.tito.v1` | warm adventurous discovery, nature and investigation |
| Momo | `greia.momo.v1` | musical, unusual, playful emotion and celebration |
| Dani | `greia.dani.system-v1` | fun, clearly robotic logic/pattern feedback |

Canonical source masters remain under:

```text
assets/source/audio/character-voice-masters/v0.1/
```

Reviewed derived references remain under:

```text
assets/audio/characters/canonical/v0.1/
```

Lilli, Leo, Flash, Tito and Momo may use optional local Chatterbox Multilingual V3 generation from those reviewed references.

Dani intentionally has no cloning reference in v0.1. A clearly synthetic platform voice is more correct for Dani than a natural clone that loses his robotic identity.

Every generated character line requires human listening review. A process exit code is never audio acceptance.

## 4. Short character reactions

Chatterbox can add unwanted speech/tails on ultra-short inputs.

For short **character dialogue/reactions** only, an authoring provider may use:

```text
bounded output-token budget
+ FFmpeg/ffprobe analysis
+ bounded leading/trailing trim
+ mandatory human review
```

This may be used for reactions such as:

```text
Vai!
Wow!
Ancora!
```

Audio cutting may remove unwanted material outside the intended phrase. It must not repair wrong pronunciation, invented sounds inside the phrase, or voice drift. Reject/regenerate those outputs.

Do not use repeated prompt padding such as `ma. ma. ma.`.

## 5. Pedagogical speech

Pedagogical speech covers cases where the child is expected to learn or imitate the sound itself:

```text
letters
letter names
syllables
phonics
spelling units
pronunciation exercises
foreign-language pronunciation targets
```

Use deterministic/native/system TTS for this role even when it sounds less natural than the canonical character voices.

A beautiful but occasionally wrong syllable is worse than a synthetic but reliably correct one.

The long-term abstraction is a small Greia-owned provider seam such as:

```text
PedagogicalSpeechProvider
```

with platform adapters such as native macOS, Windows, and Greia/Linux system speech. Activities must not hard-code host voice names or invoke platform-specific shell commands.

If the pedagogical voice is visibly different from the mascot voice, present it as an educational audio object rather than pretending the mascot is speaking it.

## 6. Shared character utterances

Greia should ship common character feedback as a small shared library so Activities can have personality without requiring developers to install Chatterbox.

The exact semantic families, Italian/English wording, animation defaults, variant-array rules, and complete v0.1 coverage target are owned by:

```text
docs/design/GREIA_SHARED_CHARACTER_UTTERANCES.md
```

Current families are:

```text
praise.general
celebrate.success
encourage.retry
encourage.progress
ready.go
```

Each resolved character + locale + semantic family owns a **non-empty array of reviewed files**.

Selection contract:

```text
one available file
→ always use that file

more than one available file
→ randomly choose one from the reviewed array
```

Activities request only:

```text
character + semantic family + locale
```

They never choose the phrase text, filename, array index, or variant number.

Randomness is presentation-only. It must not affect correctness, scoring, rewards, progression, difficulty, or gameplay.

The family's semantic ID owns its default expression/motion, so all randomly selectable files must be safe substitutes for the same presentation event.

For future grammatical-agreement variants, resolve locale/agreement first, then randomly choose inside the resulting compatible array. Never mix grammatically incompatible child-directed phrases in one random pool.

The local production runbook for this shared library is:

```text
docs/agents/GREIA_SHARED_CHARACTER_UTTERANCE_RECORDING.md
```

## 7. Voice toolchain is optional

A normal Greia Activity-authoring workstation does **not** require Chatterbox.

When an Activity authoring agent identifies useful speech:

```text
shared generic reaction?
    → request a Greia shared utterance family

pedagogical pronunciation?
    → use deterministic/system speech

custom character dialogue?
    → use local Chatterbox only if already configured
      or if the user explicitly requests installation/configuration
```

The Activity skill must not silently install Chatterbox, download model weights, or create a multi-gigabyte environment merely because a mascot could speak.

If custom character speech is optional and Chatterbox is unavailable or unwanted:

- omit the optional custom line;
- preserve captions/visual feedback and essential interaction;
- use a matching shared utterance family where appropriate;
- never use arbitrary system TTS to impersonate Lilli/Leo/Flash/Tito/Momo;
- continue building and validating the Activity normally.

If custom character speech is explicitly required, use the opt-in setup guide:

```text
docs/agents/GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md
```

## 8. Activity Designer semantic model

Activity Designer should store speech **intent**, not backend commands or generated filenames.

Conceptual example; this is not current `activity.toml` syntax:

```yaml
cues:
  intro:
    kind: character_dialogue
    speaker: leo
    text:
      it: "Guardiamo con calma."
      en: "Let's look carefully."

  phonics.ma:
    kind: pedagogical_syllable
    text:
      it: "ma"

  result.correct:
    kind: shared_character_utterance
    speaker: lilli
    utterance: praise.general
```

The semantic kind controls production/resolution. Do not infer pedagogical authority from string length alone.

## 9. Package/runtime boundary

Activity packages may contain reviewed custom playback assets, but must not contain:

```text
Chatterbox/model weights
MLX/PyTorch environments
model caches
canonical reference masters
FFmpeg binaries merely because authoring used FFmpeg
voice-design models
cloud credentials
```

Shared character utterance recordings belong to the Greia platform/shared asset catalogue and are not duplicated into each Activity package.

Dynamic platform/system TTS remains Greia-owned capability, not arbitrary shell/TTS authority exposed to Activities.

## 10. Human review, privacy and provenance

Character/shared speech review must confirm:

- exact intended words and locale;
- canonical character identity where applicable;
- no invented/repeated words or sounds;
- no bad pronunciation;
- no clipped onset/ending;
- no unwanted generated tail;
- appropriate delivery and animation association;
- acceptable playback on small speakers.

Pedagogical speech review is stricter: a fluent speaker/educator must approve the exact educational target sound.

Local production is preferred. Agents must not upload Greia reference voices to cloud services without explicit owner authorization. Preserve reference hashes and provider/model versions in production evidence.

## 11. Current implementation boundary

Accepted policy now:

- MOSS-TTS-Nano: **REJECTED**;
- Chatterbox Multilingual V3: optional local renderer for reviewed character speech;
- triple repetition/middle extraction: **REJECTED**;
- bounded token output + audio analysis/cutting: useful for short character reactions only;
- pedagogical pronunciation: deterministic/system speech;
- Dani: robotic system-TTS path;
- local cloning toolchain: optional and never silently installed;
- shared character library: five semantic families, up to three reviewed source variants per family/character/locale, random choice from the currently available array;
- one accepted shared variant is sufficient; additional accepted files add variety without Activity changes.

Not yet implemented:

- Activity Designer speech-kind schema/UI;
- provider capability probe API;
- native/system pedagogical TTS adapters;
- shared utterance audio files/runtime catalogue/resolver;
- Dani production profile;
- Chatterbox production worker/cache/receipts;
- generic audio-analysis wrapper integration into Activity Designer.

Exact future APIs/schemas belong in source and tests. Keep `skills/greia-activity-authoring/SKILL.md`, `VOICE_GENERATION.md`, `SETUP.md`, and the local voice setup/recording guides synchronized with this policy.
