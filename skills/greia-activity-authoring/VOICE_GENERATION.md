# Voice and Spoken Cues for Greia Activities

**Status:** focused companion for Activity speech planning and production  
**Load when:** a new Activity needs spoken instructions/presenter dialogue/pedagogical sounds, or existing speech is changed

This document owns the Activity-facing speech rules. The canonical engine implementation is owned by:

```text
skills/greia-voice-production/SKILL.md
tools/greia_voice.py
tools/greia_voice_core/
```

## 1. Core runtime rule

Greia Activity narration/instructions are **prerecorded at authoring time**.

The child runtime does not run VoxCPM2, Chatterbox, Whisper or ordinary live TTS for Activity narration.

Activity code receives reviewed static audio or uses an accepted Greia shared/runtime speech resolver.

Do not build a second speech engine inside an Activity.

## 2. Required spoken instructions

Greia children may not read.

If the child needs language to understand a required action and visuals alone do not communicate it reliably, provide a spoken cue.

Examples:

```text
"Trova la lettera S."
"Metti tre mele nel cestino."
"Quale animale fa questo verso?"
```

A text caption is not a substitute.

Required speech must:

- use a stable semantic cue ID;
- cover every shipped locale for that interaction;
- be short and contain one idea at a time;
- use the correct semantic speaker/kind;
- play at the correct moment;
- be repeatable when useful;
- be human-reviewed before final acceptance.

Do not narrate every tap. Use speech where it improves orientation, comprehension, hints, feedback or personality.

## 3. Choose semantic purpose before generating

Every new cue belongs to one semantic route.

### `character_dialogue`

Use for natural-character communication:

```text
presenter welcome
Activity-specific instruction
contextual hint
story/narration
curiosity fact
Activity-specific reaction
```

Examples:

```text
Leo: "Ciao! Scopriamo le lettere!"
Tito: "Trova l'orca con la pinna alta!"
```

### `shared_character_utterance`

Use for generic reusable meaning when the current runtime resolver exposes the accepted family:

```text
praise.general
celebrate.success
encourage.retry
encourage.progress
ready.go
```

Do not duplicate generic praise into every Activity merely because it is easy to generate.

### `pedagogical_speech`

Use only when **the sound itself is educational truth**:

```text
letter name/sound
syllable
phonics target
spelling/pronunciation unit
foreign-language target sound
```

Correctness and consistency outrank natural character quality.

An Activity being educational does not make all its speech pedagogical.

Examples:

```text
Leo welcome                         -> character_dialogue
"A" taught as the target letter    -> pedagogical_speech
"MA" taught as a syllable          -> pedagogical_speech
generic "Ottimo lavoro!"            -> shared utterance when available
```

A phrase containing a pronunciation target may legitimately use pedagogical speech when exact pronunciation of that target is part of what is being taught. Do not use this as an excuse to route unrelated welcomes, praise or general instructions through the pedagogical voice.

### `dani_system_speech`

Use for Dani's intentionally robotic presenter/logic speech.

Example:

```text
Dani: "Metti tre mele nel cestino."
```

Dani uses its selected v0.3 cloned master (`greia.dani.v3`) through the default VoxStage/VoxCPM2 provider. `dani_system_speech` remains a compatible semantic kind; ordinary `character_dialogue` is also supported. Pedagogical pronunciation keeps its separate native/system route.

## 4. Canonical speakers

```text
Lilli -> creativity, stories, art, wonder
Leo   -> language, reading, knowledge, calm guidance
Flash -> action, speed, lively challenge
Tito  -> nature, exploration, discovery
Momo  -> music, emotion, playful experimentation
Dani  -> logic, patterns, concise robotic guidance
```

These are affinities, not rigid silos.

For presenter choice and curiosity/facts design load:

```text
skills/greia-activity-authoring/PRESENTERS_AND_CURIOSITY.md
```

## 5. Shared speech current state

The shared library lives in `assets/audio/characters/shared/v0.2/`: generic reactions per character plus canonical character introductions, in EN/IT/ES/FR. Its `manifest.toml` and `review.csv` (and `docs/design/GREIA_SHARED_CHARACTER_UTTERANCES.md`) hold the current per-clip acceptance state; do not infer it from older counts and do not call owner-accepted clips pending.

Accepted asset bytes do not prove that every Activity runtime path already resolves every family. Inspect the current shared resolver/source before depending on a family.

Canonical character introductions are OS/shared presentation content. Do not rerecord "Hi, I'm Leo/Lilli/..." independently in every Activity.

### Shared locale-aware audio resolution (owner decision)

The shared Greia runtime subsystem owns localized prerecorded-audio
lookup through `greia_platform.localization.LocalizedResources`.
Activity code requests stable semantic IDs through `audio_path(key)`
(fail-soft `Path | None`), or the compatibility `audio_cue(key)`
(`LocalizedAudioCue`, raising on absence). Do not duplicate language
folder resolution in a new Activity SoundManager.

**Resolution:** an existing recording for the selected Activity UI locale
wins. If absent, use the **English** recording. This policy includes
phoneme/letter/syllable pronunciation cues **for now**, by explicit
owner direction. An absent selected-locale file is a useful coverage
observation, **not** a runtime rejection or a reason to regenerate
already approved assets.

New Activities follow the convention
`assets/audio/<locale>/<semantic-id>.wav` (or `.ogg`), using the same
ID in each language; launcher titles use
`locales/<locale>/audio/activity-title.wav`. Where a legacy English
bundle declares a different filename, `LocalizedResources` projects
that **one** canonical path into the requested locale and tries its
actual file before English. For other legacy filenames, provide a
single `filename="existing-name.wav"` argument to `audio_path`.

Use the existing `activity_resources(package_root)` composition
factory: it reads the Activity manifest's supported languages and
the active child profile/device locale. The localization resolver
does not decode audio or create a Pygame mixer; the Activity sound
owner handles only cache/channels/playback and procedural effects.

Committed recordings are **personally owner-approved**. Preserve them during
ordinary Activity work. Corpus-wide replacement is a separate owner-authorized
operation (`tools/regenerate_voice_corpus.py`,
`docs/agents/GREIA_VOICE_CORPUS_REGENERATION.md`) that preserves deterministic
isolated letters/syllables and marks fresh output pending listening; replaced
takes stay pending until individually heard. New recordings always require owner
listening approval. No source/signature tamper checking is required: users are
allowed to modify installed media.

VoxStage character acting defaults are editable in
`tools/greia_voice_core/character_delivery.json`. Use the semantic
`delivery_prompt` field (CLI `--delivery-prompt`) for a cue-specific tone/mood
override, separate from spoken text. Batch/service preserve the same field;
receipts include actual effective direction. Chatterbox/native do not support
explicit acting prompts and reject them.


## 6. Semantic cue IDs and localization

For post-generation automated review, follow
`docs/agents/GREIA_AUTOMATED_VOICE_REVIEW.md`. The corpus `review` command screens
installed audio and eligible ASR through engine collaborators, producing external
reports and a prioritized listening queue. It never modifies recordings/receipts
or acceptance. ASR exclusions/unavailability remain explicit. Keep this authoring
analysis out of Activity runtime packages; human listening is still required.

Gameplay code chooses semantic meaning, not filenames or sentences.

Prefer IDs such as:

```text
presenter.welcome
instruction.count_objects
instruction.find_letter
hint.first
phonics.letter_a
curiosity.orca.family_pods
```

For every shipped locale:

- provide reviewed localized wording;
- preserve the same gameplay meaning;
- keep character identity consistent;
- provide accepted audio when speech is required by the interaction;
- keep spoken and displayed wording semantically aligned.

Do not hard-code locale branches into game rules.

## 7. Produce through VoiceEngine only

Default character production uses the shared local VoxStage/VoxCPM2 worker and active v0.3 registry references: Dani/Momo/Tito use their selected v3 IDs while Lilli/Leo/Flash retain their exact v2 IDs and bytes. The operator starts the installed worker with `voxstage start`; Activity producers still submit only semantic Greia requests. Chatterbox is an explicit operator alternative, never a silent fallback. Do not regenerate existing accepted clips outside an explicit owner-authorized corpus operation.

Start with:

```bash
python3 tools/greia_voice.py doctor
```

Generate through `generate`, `batch`, or the warm `serve`/`request` workflow described by `skills/greia-voice-production/SKILL.md`.

Example natural-character cue:

```bash
python3 tools/greia_voice.py generate \
  --speaker leo \
  --kind character_dialogue \
  --locale it \
  --text "Guardiamo con calma." \
  --cue-id presenter.hint \
  --output /tmp/greia-voice-review/my_activity/it/presenter-hint.wav
```

Example exact pedagogical target:

```bash
python3 tools/greia_voice.py generate \
  --speaker pedagogical \
  --kind pedagogical_speech \
  --locale it \
  --text "ma" \
  --cue-id phonics.ma \
  --verification off \
  --output /tmp/greia-voice-review/my_activity/it/phonics-ma.wav
```

Generate review candidates outside the final runtime asset location. Integrate only accepted clips.

## 8. Activity-specific voice tooling location

If an Activity needs a helper to assemble many semantic requests, it belongs under that Activity from the start:

```text
activities/<activity>/tools/generate_voice_requests.py
```

It may own:

- cue IDs;
- reviewed localized text;
- semantic speaker/kind assignment;
- expected output names;
- request/batch assembly.

It must not own:

- VoxStage/Chatterbox/MLX imports or direct service calls;
- model IDs;
- reference voice paths/hashes;
- Whisper invocation;
- macOS `say`/native voice choice;
- FFmpeg/trim policy;
- model token budgets/retry internals;
- a parallel voice backend.

Do **not** put one-Activity generators in repository root `tools/`.

Before final Activity/package acceptance, remove obsolete/one-shot authoring helpers and scratch request files from the Activity package tree. The Activity directory is package content; development machinery must not accidentally ship to the child device.

Root `tools/` is for genuinely Greia-wide facilities such as the canonical VoiceEngine itself and shared-library producers.

## 9. Human review is mandatory

Every successful generated candidate remains:

```text
human_review = PENDING
```

Machine success or an ASR (Parakeet/Whisper) pass is not acceptance.

Reject natural-character speech for:

- wrong words;
- wrong locale;
- character identity drift;
- bad pronunciation/stress;
- clipping/tails/noise;
- inappropriate delivery.

Reject pedagogical speech for any incorrect or ambiguous target sound.

ASR screening is advisory for suitable multi-word natural speech and never pronunciation authority for letters/syllables/phonics.

## 10. Audio sequencing is part of child UX

Plan when cues play.

Avoid:

- welcome and first instruction stomping each other;
- number/letter pronunciation being cut off by celebration;
- repeated taps starting overlapping copies of the same command;
- long queues that keep talking after the child moved on.

Prefer one explicit Activity audio owner with bounded interruption/queue semantics appropriate to the experience.

Required instruction replay should be obvious when useful, for example tapping the speaking presenter or a large semantic replay affordance.

## 11. Launcher title speech is separate

Every built-in Activity also needs localized launcher-title speech for each completed catalogue locale.

Runtime playback is Shell-owned. The Activity does not implement hover/focus speech.

Load:

```text
skills/greia-activity-authoring/LAUNCHER_SPOKEN_LABELS.md
```

Launcher titles are communicative speech, not `pedagogical_speech` merely because a title is one word.

## 12. Final speech checklist

Before calling speech complete:

```text
required spoken commands identified
semantic cue IDs stable
correct speaker/kind chosen
all shipped locales covered
VoiceEngine used for new/replacement generation
Activity-local request tooling stayed in activities/<id>/tools/
human review complete
only accepted audio integrated
required cues play at the correct time
required cues can be repeated where useful
audio does not stomp pedagogical targets/instructions
shared families used only when current runtime resolver supports them
canonical character introductions not duplicated
final headless Simulator rerun after runtime audio integration
final GUI Simulator review includes real speech timing/comprehension
```

If required speech is missing, the Activity may be mechanically launchable but its pre-reader child UX is not accepted.
