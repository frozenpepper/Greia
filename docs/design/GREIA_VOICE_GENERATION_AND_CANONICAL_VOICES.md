# Greia Voice Generation and Canonical Character Voices

**Status:** accepted Activity-authoring / Activity Designer direction; production compiler/runtime integration pending  
**Date:** 2026-08-23  
**Scope:** optional local character-voice production, deterministic pedagogical speech, shared character utterances, localized package audio, and the Dani system-TTS identity  
**Related authorities:** `docs/adr/0028-platform-and-activity-localization-language-context.md`, `docs/design/GREIA_CANONICAL_CAST_SYSTEM.md`, `docs/design/GREIA_SHARED_CHARACTER_UTTERANCES.md`, `skills/greia-activity-authoring/SKILL.md`

## 1. Core decision: speech has different semantic jobs

Greia must not treat all speech as one TTS problem.

The accepted split is:

```text
A. CHARACTER SPEECH
   personality, narration, reactions, instructions, story/dialogue
   → canonical character identity
   → optional local Chatterbox Multilingual V3 authoring
   → human-reviewed prerecorded Activity audio

B. SHARED CHARACTER INTERJECTIONS
   congratulations, great work, retry, let's go, etc.
   → OS/shared asset library
   → prerecorded canonical character clips
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

## 2. Why this changed

Local evaluation invalidated the previous MOSS-TTS-Nano production direction.

Observed results:

- MOSS-TTS-Nano speech quality was below an acceptable Greia production floor and is **REJECTED** as the canonical renderer;
- Chatterbox Multilingual V3 produced much better natural character speech and voice similarity;
- Chatterbox remained inconsistent on individual letters/syllables and other ultra-short pronunciation-authoritative inputs;
- constraining generated token length plus bounded audio analysis/cutting improved unwanted tail behavior for short character utterances;
- the `ma. ma. ma.` repeated-generation/middle-extraction experiment made results worse and is **REJECTED**;
- even when cutting worked, some individual syllables were pronounced incorrectly or inconsistently, which is unacceptable for a teaching tool.

Do not reopen the rejected MOSS or triple-repetition paths merely because they are simpler to automate.

## 3. Character speech renderer

### 3.1 Current optional authoring renderer

The current accepted local character-speech candidate is:

```text
Chatterbox Multilingual V3
family: Resemble AI Chatterbox
size class: 500M multilingual model
license: MIT (upstream repository)
Italian: supported by the multilingual model
purpose: reviewed zero-shot character voice cloning for normal speech
```

Chatterbox is an **authoring tool**, not a child-runtime dependency. It supports the five reviewed reference voices:

```text
greia.lilli.v1
greia.leo.v1
greia.flash.v1
greia.tito.v1
greia.momo.v1
```

Every generated line requires human review. Chatterbox's quality on normal sentences does not authorize its use as a pronunciation oracle.

### 3.2 Short character utterances

For genuinely short **character dialogue** such as:

```text
"Vai!"
"Sì!"
"Wow!"
"Ancora!"
```

an authoring provider may use a bounded output-token budget and Greia audio analysis/trimming to remove unwanted generated tails.

This is allowed only when:

- the clip is character feedback/dialogue rather than pronunciation-authoritative teaching content;
- audio analysis fails closed rather than hiding internal hallucinations;
- the final result is listened to and approved;
- initial consonants and intended endings are preserved.

Do not use repeated prompt padding (`ma. ma. ma.` or equivalent). That experiment is rejected.

### 3.3 Provider abstraction

Activity Designer must not bind source data to one Python package or CLI. The future character-speech provider should be conceptually equivalent to:

```text
generate_character_speech(
    voice_id,
    locale,
    text,
    output_master_path,
    synthesis_profile,
)
```

Provider identity/version, reference hash, locale, exact text, synthesis options and post-processing profile must participate in cache identity and generation receipts.

## 4. Pedagogical speech

### 4.1 Correctness is the first requirement

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

For these, Greia prefers a deterministic/native/system TTS path even when it sounds less natural than a cloned neural character voice.

A beautiful but occasionally wrong syllable is worse than a synthetic but reliably correct one.

### 4.2 Abstraction

The long-term authoring/runtime contract should be a small semantic provider such as:

```text
PedagogicalSpeechProvider
```

Possible implementations include:

```text
NativeMacSpeechProvider
NativeWindowsSpeechProvider
GreiaSystemSpeechProvider
```

A future Greia Linux implementation may use an appropriate compact deterministic speech engine behind the same platform interface. Activities must not select host voice names or invoke OS-specific commands directly.

For static Activity assets, Activity Designer may render reviewed pedagogical clips at authoring time through the available native/system provider. For genuinely dynamic child-runtime speech, the Greia platform must own the TTS service rather than exposing arbitrary shell/TTS authority to Activities.

### 4.3 Presentation rule

If pedagogical speech uses a noticeably different voice from the current mascot, do not pretend the mascot is literally speaking the teaching sample.

Prefer a visual sequence such as:

```text
Leo character dialogue: "Ascolta bene."
        ↓
neutral pedagogical audio object: "ma"
        ↓
Leo character/shared feedback: "Ottimo lavoro!"
```

This makes the voice change intentional and keeps pronunciation authority separate from character acting.

## 5. Dani

Dani remains an intentional system-TTS character:

```text
greia.dani.system-v1
```

The designed cloning attempts did not produce an unmistakably robotic identity. For Dani, a clearly synthetic platform voice is more correct than a natural voice clone.

The platform should eventually expose at least two distinct semantic system-TTS profiles:

```text
pedagogical.neutral
greia.dani.system-v1
```

They may share an underlying engine while differing in approved pitch/rate/processing where supported.

Activities do not choose arbitrary macOS/Windows/Linux voice names.

## 6. Canonical reference registry

Canonical source masters remain under:

```text
assets/source/audio/character-voice-masters/v0.1/
```

Reviewed derived references remain under:

```text
assets/audio/characters/canonical/v0.1/
```

The five character mappings remain:

| Character | Voice ID | Character reason |
|---|---|---|
| Lilli | `greia.lilli.v1` | warm wonder, creativity, stories and imagination |
| Leo | `greia.leo.v1` | warm oldish savvy storyteller; thoughtful guidance without young-teacher energy |
| Flash | `greia.flash.v1` | bright, quick, playful action and friendly challenge |
| Tito | `greia.tito.v1` | warm adventurous discovery, nature and investigation |
| Momo | `greia.momo.v1` | musical, unusual, playful emotion and celebration |

Dani has no cloning reference in v0.1.

References are shared-world identity assets, not per-Activity customization points. Do not replace them because one generated line fails; reject/regenerate the line or use the appropriate non-character speech path.

## 7. Shared character utterances

Greia should ship a small platform-owned library of common canonical character clips so Activities can gain personality without generating custom dialogue.

The accepted inventory and animation policy live in:

```text
docs/design/GREIA_SHARED_CHARACTER_UTTERANCES.md
```

Initial semantic examples include:

```text
praise.congratulations
praise.great_work
praise.well_done
celebrate.you_did_it
encourage.try_again
ready.lets_go
```

The target v0.1 matrix is six characters × six cues × Italian/English = 72 reviewed clips.

Shared clips are resolved by semantic IDs and live in Greia's shared asset/runtime catalogue. They are not copied into every Activity package.

This library is especially important when the local developer does **not** have or want the Chatterbox voice-generation toolchain installed.

## 8. Voice toolchain is optional

A normal Greia Activity-authoring workstation does **not** require Chatterbox.

When an Activity authoring agent identifies useful character speech, it must first determine what kind of speech is needed:

```text
shared generic reaction?
    → use Greia shared utterance when available

pedagogical pronunciation?
    → use pedagogical/system speech

custom character dialogue?
    → use local Chatterbox only if the toolchain is already available or the user explicitly asks to install/configure it
```

The agent must not silently install model weights or a voice environment merely because speech would be nice.

If custom character speech would be optional and the Chatterbox toolchain is unavailable/unwanted:

- drop that custom voiced line from the Activity plan;
- preserve the caption/text/visual feedback where appropriate;
- use a matching shared utterance if one exists;
- do **not** substitute arbitrary system TTS for Lilli, Leo, Flash, Tito or Momo;
- continue building a fully functional Activity without custom character audio.

If the user explicitly requires custom character speech, point to the opt-in setup procedure rather than installing silently.

## 9. Activity Designer semantic model

Speech source should record semantic intent rather than only text.

Conceptual example (not current `activity.toml` syntax):

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
    utterance: praise.great_work
```

The semantic `kind` controls the production path. Do not infer pedagogical authority only from character count.

## 10. Authoring decision table

| Need | Preferred source | Voice identity | Toolchain requirement |
|---|---|---|---|
| long/normal character line | Chatterbox prerecorded asset | canonical character | optional Chatterbox |
| short character exclamation | bounded Chatterbox + analysis/cut | canonical character | optional Chatterbox + FFmpeg |
| generic praise/retry/start | shared Greia utterance | canonical character | none for Activity author |
| letter/syllable/phonics | native/system pedagogical TTS | neutral teaching voice | system/native provider only |
| Dani dialogue | Greia system TTS | robotic Dani profile | platform/system provider |
| no speech/toolchain | visual/text interaction | none | none |

## 11. Audio analysis and post-processing

FFmpeg/ffprobe are the preferred cross-platform authoring primitives for inspection, trimming and package conversion.

Useful operations include:

```text
metadata inspection
silence/tail detection
bounded trim
clipping/loudness checks
WAV → OGG conversion
```

Audio analysis must not become semantic repair. If the generated clip contains the wrong syllable, an invented sound inside the intended utterance, or bad pronunciation, reject it. Do not cut/splice until it appears correct.

For package output:

- use WAV when phonetic detail or very short clips justify the size;
- otherwise use OGG Vorbis under current localized-audio policy;
- speech is normally mono;
- prevent clipping;
- preserve consonant onsets/endings;
- review after final conversion.

## 12. Human review

Every generated or system-rendered static cue must be listened to before release.

Character speech review:

- exact intended text;
- canonical speaker identity;
- locale/pronunciation;
- no invented/repeated words or tail sounds;
- appropriate expression;
- no clipped start/end;
- acceptable small-speaker playback.

Pedagogical speech review is stricter:

- a fluent speaker/educator approves the exact target sound;
- the clip contains only the intended educational unit;
- pronunciation is stable and unambiguous;
- sound effects or mascot animation do not mask the target.

System/native TTS being deterministic does not remove the human content-review requirement.

## 13. Package/runtime boundary

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

Shared character interjections belong to the platform shared asset catalogue and are not duplicated into packages.

Dynamic platform/system TTS remains a Greia-owned capability, not arbitrary shell access from Activities.

## 14. Privacy, licensing and provenance

- local character production is preferred;
- agents must not upload Greia reference voices to cloud services without explicit owner authorization;
- preserve source/reference hashes and provider/model version in generation evidence;
- generated voices must not impersonate real people;
- Chatterbox upstream code/model usage must retain the applicable MIT notices/attribution in developer-tooling records;
- native/system TTS licensing/redistribution rules remain platform-specific; prerendered asset rights must be checked before public redistribution where the host/platform licence requires it.

## 15. Current implementation boundary

Accepted policy now:

- MOSS-TTS-Nano: **REJECTED for production quality**;
- Chatterbox Multilingual V3: optional local renderer for reviewed character speech;
- triple-repetition/middle-extraction workaround: **REJECTED**;
- bounded token output plus audio analysis/cutting: useful for reviewed short character speech, not pedagogical pronunciation;
- pedagogical letters/syllables/phonics: deterministic/system speech path;
- Dani: system-TTS robotic path;
- local cloning toolchain: optional, never silently installed by the Activity skill;
- shared canonical character utterance library: accepted design direction for Italian and English first.

Not yet implemented by this documentation change:

- Activity Designer speech-kind schema/UI;
- provider capability probe API;
- native/system pedagogical TTS adapters;
- shared utterance audio assets/catalogue resolver;
- Dani production profile;
- Chatterbox production worker/cache/receipts;
- generic audio-analysis wrapper integration into Activity Designer.

Exact future APIs/schemas belong in source and tests. Keep `skills/greia-activity-authoring/SKILL.md`, `VOICE_GENERATION.md`, `SETUP.md` and the local voice setup guide synchronized with this policy.
