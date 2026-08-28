# Greia Voice Generation and Canonical Character Voices

**Status:** accepted voice policy + canonical authoring Voice Production Engine; shared-library and character-intro audio still pending production/review  
**Reviewed:** 2026-08-28  
**Scope:** presenter speech, researched narration, shared reactions, pedagogical speech, Dani system speech, character introductions, multilingual static audio and human review  
**Canonical production tool:** `tools/greia_voice.py`

Related authorities:

```text
skills/greia-voice-production/SKILL.md
tools/greia_voice_core/README.md
docs/architecture/GREIA_VOICE_PRODUCTION_ENGINE.md
docs/design/GREIA_SHARED_CHARACTER_UTTERANCES.md
docs/design/GREIA_CANONICAL_CAST_SYSTEM.md
skills/greia-activity-authoring/PRESENTERS_AND_CURIOSITY.md
```

## 1. “Voice Studio” means the authoring workflow, not child runtime

In contributor conversation, “Voice Studio” may be used as shorthand for Greia's authoring voice workflow:

```text
semantic request
-> tools/greia_voice.py / VoiceEngine
-> provider routing
-> optional advisory verification
-> review audio + receipt
-> human listening
-> owning workflow promotion
```

It is currently a repository CLI/service workflow, not a child-runtime service and not a requirement for a GUI.

No TTS model, Whisper model or provider stack runs on the Acer/child device. The child only receives already-reviewed static audio.

## 2. Speech has different semantic jobs

Greia does not treat all speech as one TTS problem.

```text
A. character_dialogue
   presenter welcome, narration, researched facts, contextual hints,
   story/dialogue, OS-owned character introductions
   -> canonical Lilli/Leo/Flash/Tito/Momo identity

B. shared_character_utterance
   generic praise, success, retry, progress and start reactions
   -> central reviewed Greia shared library
   -> production through VoiceEngine; runtime resolves accepted static assets

C. pedagogical_speech
   letters, syllables, phonics, spelling/pronunciation targets
   -> deterministic native/system provider
   -> correctness and consistency outrank mascot identity

D. dani_system_speech
   Dani-specific dialogue/introduction
   -> deterministic system speech preserving Dani's robotic identity
```

Governing rule:

> **If the sound itself is the educational truth being taught, use pedagogical speech. If speech communicates content through a character, use character speech.**

Text length is not the selector. `Vai!` may be character dialogue; `ma` may be a teaching target.

## 3. Canonical production boundary

All new prerecorded Greia speech production goes through:

```text
tools/greia_voice.py
```

Callers provide only semantic intent:

```text
speaker
kind
locale
exact reviewed text
cue/output identity
```

Callers do not operate:

```text
Chatterbox model IDs
MLX lifecycle/cache rules
canonical cloning references/hashes
native host voice names/rates
pedagogical pronunciation workarounds
Whisper commands/models
FFmpeg trim/packaging commands
token budgets or silence-trim heuristics
```

Those mechanics belong behind `VoiceEngine` and its provider interfaces.

Historical direct-backend Activity generators are not accepted extension points. Tracked Activity generators must stay thin semantic request/batch producers.

## 4. Canonical character identities

| Character | Voice ID | Speech personality |
|---|---|---|
| Lilli | `greia.lilli.v1` | warm wonder, creativity, stories, art and imagination |
| Leo | `greia.leo.v1` | warm oldish savvy storyteller; thoughtful, curious, never young-teacher energy |
| Flash | `greia.flash.v1` | bright, quick, playful action and friendly challenge |
| Tito | `greia.tito.v1` | warm adventurous discovery, nature, investigation and curiosity |
| Momo | `greia.momo.v1` | musical, unusual, playful emotion, silliness and celebration |
| Dani | `greia.dani.system-v1` | fun, concise, clearly robotic logic/pattern feedback |

Canonical source masters:

```text
assets/source/audio/character-voice-masters/v0.1/
```

Reviewed cloning references and registry:

```text
assets/audio/characters/canonical/v0.1/
assets/audio/characters/canonical/v0.1/manifest.toml
```

The engine verifies cloning-reference SHA-256 values before cloned generation. Dani intentionally has no cloned natural-voice reference.

## 5. Current providers are implementation details

Current accepted implementation path:

```text
Lilli/Leo/Flash/Tito/Momo
    -> Chatterbox Multilingual V3 on Apple-Silicon MLX

pedagogical_speech
    -> macOS deterministic native/system provider

Dani
    -> macOS deterministic native/system provider

optional semantic warning
    -> mlx-whisper-tiny for suitable multi-word natural-character lines
```

A future provider is added behind `VoiceEngine`; Activities do not learn a new backend command.

Rejected directions remain rejected:

- cloned character speech as phonics/syllable authority;
- arbitrary host TTS impersonating a canonical character;
- silent/synthetic placeholders reported as successful speech;
- runtime voice models on the child device.

## 6. Presenter/speech design is part of Activity design

Every new Activity explicitly decides:

```text
lead presenter/mascot or deliberate none
shared character reaction plan
custom Activity-specific dialogue
pedagogical speech, if any
optional researched curiosity/fact narration
supported locales and spoken coverage
```

Use the shared library when generic praise/retry meaning is sufficient. Do not duplicate generic reaction recordings per Activity.

Detailed Activity rules:

```text
skills/greia-activity-authoring/PRESENTERS_AND_CURIOSITY.md
skills/greia-activity-authoring/VOICE_GENERATION.md
```

## 7. Multilingual contract

Speech uses stable semantic cue IDs independent of language:

```text
presenter.welcome
curiosity.orca.family_pods
phonics.ma
character.intro.lilli
```

Each supported locale owns reviewed wording. If speech is an accepted feature, each shipped locale needs reviewed audio with the correct semantic speaker.

Do not:

- hard-code locale-specific gameplay branches;
- let displayed and spoken wording drift semantically;
- impersonate a canonical character with arbitrary system TTS;
- make scoring/correctness/difficulty depend on locale or spoken variant.

If a provider is unavailable, retain the semantic cue/text plan and report audio pending. Do not erase or fake the feature.

## 8. Character dialogue and researched narration

Use `character_dialogue` for:

```text
brief welcome/orientation
contextual hints
short story/narration beats
Activity-specific explanation
researched curiosity facts
OS-owned natural-character introductions
```

Facts are finite reviewed authoring content with provenance. They are never generated by an LLM at child runtime and never require network access.

## 9. Pedagogical speech

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

The exact educational target belongs to the semantic request. Provider-specific spellings/accent hints are private engine implementation details.

A fluent speaker/educator must review pronunciation-critical output.

## 10. Shared character reactions — designed, not yet produced

Current v0.1 families:

```text
praise.general
celebrate.success
encourage.retry
encourage.progress
ready.go
```

Target:

```text
6 characters × 5 families × 3 variants × 2 locales = 180 clips
```

The producer and VoiceEngine route exist. The v0.1 content tranche (180 shared clips,
generated 2026-08-23 under the older engine build) is **RETIRED**; see
`assets/audio/characters/shared/v0.1/RETIRED.md`. The current authoritative state:

```text
shared reaction library: assets/audio/characters/shared/v0.2/   (192 clips: 180 shared + 12 intros, OWNER_ACCEPTED 2026-08-28)
180 shared candidates generated: COMPLETE (tmp/shared-character-utterances/)
12 intro candidates generated:   COMPLETE (tmp/character-intros/)
human listening:                 COMPLETE (in-session 2026-08-28)
accepted runtime set:            assets/audio/characters/shared/v0.2/  (registry_version v0.2)
runtime resolver wiring:         PENDING (separate child-runtime task)
```

Do not claim the shared library is complete merely because `tools/record_shared_character_utterances.py` exists.

Exact phrase/design authority:

```text
docs/design/GREIA_SHARED_CHARACTER_UTTERANCES.md
```

Production/review authority:

```text
docs/agents/GREIA_SHARED_CHARACTER_UTTERANCE_RECORDING.md
```

## 11. OS-owned character introduction pack

Greia should also produce one fun self-introduction per character per initial locale. This is a reusable platform asset pack whose final UX placement remains deliberately undecided.

Target:

```text
6 characters × 2 locales = 12 intro clips
```

Stable cue IDs:

```text
character.intro.lilli
character.intro.leo
character.intro.flash
character.intro.dani
character.intro.tito
character.intro.momo
```

### Lilli

Italian:

> Ciao! Io sono Lilli! Adoro inventare storie, disegnare cose colorate e trovare un po' di magia dappertutto. Hai un'idea buffa? Vieni con me!

English:

> Hi! I'm Lilli! I love making up stories, drawing colorful things, and finding a little magic everywhere. Got a silly idea? Come with me!

### Leo

Italian:

> Oh, ciao! Io sono Leo. Mi piacciono le storie, le parole e tutte quelle domande che cominciano con “perché”. Se c'è qualcosa da scoprire, io sono pronto!

English:

> Oh, hello! I'm Leo. I like stories, words, and all those questions that start with “why”. If there's something to discover, I'm ready!

### Flash

Italian:

> Ehi! Io sono Flash! Adoro correre, giocare e provare sfide velocissime. Se senti qualcuno gridare “via!”, probabilmente sono già partito!

English:

> Hey! I'm Flash! I love running, playing, and trying super-fast challenges. If you hear someone shout “go!”, I've probably already started!

### Dani

Italian:

> Bip-bop! Io sono Dani! Mi piacciono numeri, schemi, puzzle e cose che fanno clic proprio al posto giusto. Modalità amicizia: attivata!

English:

> Beep-bop! I'm Dani! I like numbers, patterns, puzzles, and things that click into exactly the right place. Friendship mode: activated!

### Tito

Italian:

> Ciao, esploratore! Io sono Tito! Mi piace curiosare tra boschi, mari, sentieri e piccoli misteri. Andiamo a vedere cosa c'è dietro l'angolo!

English:

> Hello, explorer! I'm Tito! I love poking around forests, seas, trails, and little mysteries. Let's see what's around the corner!

### Momo

Italian:

> Buuu! ... Scherzavo! Io sono Momo! Adoro musica, rumori buffi, esperimenti strani e feste improvvise. Se qualcosa fa boing, voglio provarla!

English:

> Booo! ... Just kidding! I'm Momo! I love music, silly noises, strange experiments, and surprise parties. If something goes boing, I want to try it!

Routing:

```text
Lilli/Leo/Flash/Tito/Momo -> character_dialogue
Dani                       -> dani_system_speech
```

These scripts are v0.1 **production candidates**, not accepted copy until owner listening. Small wording changes after listening are allowed, but update this authority and regenerate rather than silently changing spoken bytes.

### Candidate product placement

Possible later uses include:

- optional first-run “meet the cast” moment;
- characters walking/appearing on the first Home screen and introducing themselves when tapped/clicked;
- a future character gallery;
- occasional discoverable character moments.

Product constraints regardless of placement:

- never auto-play six speeches back-to-back at boot;
- one character voice at a time;
- speech must be skippable/interruptible;
- core navigation remains obvious without audio;
- hearing an introduction must not unlock permissions, progression or gameplay truth;
- the same reviewed asset should be reused instead of Activity-local re-recordings.

## 12. Whisper is advisory

Suitable multi-word natural-character dialogue/shared speech may be transcribed by Whisper with the requested language explicitly set.

```text
PASS -> plausible transcript match; human listening still required
WARN -> likely mismatch; regenerate/inspect
NOT_RUN / NOT_APPLICABLE -> no machine transcription gate
```

Do not use Whisper to certify letters, syllables or phonics. Dani and very short reactions may legitimately skip ASR.

## 13. Human acceptance

Every engine result remains:

```text
human_review = PENDING
```

Human listening verifies:

- exact intended words and locale;
- canonical character identity where applicable;
- no invented/repeated words or sounds;
- pronunciation/stress;
- no clipping or unwanted tail;
- appropriate delivery;
- small-speaker intelligibility.

A receipt, valid container, process success or Whisper PASS is never acceptance.

## 14. Installation/readiness

Start with:

```bash
python3 tools/greia_voice.py doctor
```

Quick install/use:

```text
tools/greia_voice_core/README.md
```

Detailed workstation setup:

```text
docs/agents/GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md
```

The low-level Chatterbox field guide is engine-maintainer/troubleshooting material only.

## 15. Package/runtime boundary

Never package authoring machinery into Activities/child runtime:

```text
Chatterbox/Whisper model weights
MLX/PyTorch environments
model caches
canonical cloning-reference masters
FFmpeg authoring binaries
rejected/unreviewed scratch audio
```

Runtime microphone capture is a separate Greia platform subsystem (`audio.basic`).

## 16. Current implementation and content status

Implemented authoring infrastructure:

- semantic `VoiceRequest` / `VoiceEngine` abstraction;
- canonical voice registry + hash validation;
- Apple-Silicon Chatterbox MLX character provider;
- macOS pedagogical/Dani native provider;
- shared-library authoring kind;
- optional advisory Whisper verifier;
- bounded retries;
- cross-process single-worker lock;
- warm localhost service + batch mode;
- WAV/OGG packaging;
- receipts initially emitted with `human_review=PENDING` and re-stamped to `OWNER_ACCEPTED` on owner listening authorization;
- `doctor` readiness probe;
- repository install/runbook documentation.

Content status:

```text
shared reaction library: 180 clips generated, 180 owner-accepted; published to assets/audio/characters/shared/v0.2/
character intro pack:     12 clips generated,  12 owner-accepted; published to assets/audio/characters/shared/v0.2/_intros/
runtime resolver wiring:  PENDING (separate child-runtime task; v0.2 assets are the source of truth)
```

Future/host-specific engineering remains separate:

- accepted Windows/Linux native providers;
- non-MLX cloned-character provider;
- Activity Designer speech-kind UI/schema integration;
- runtime shared-utterance catalogue/resolver completion where still missing;
- final product UX for character introductions.
