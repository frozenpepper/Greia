---
name: greia-activity-authoring
description: Canonical agent guide for designing, implementing, packaging, validating and testing Greia Activities, including discovery/audience metadata, optional canonical character speech, deterministic pedagogical speech, shared character utterances, and platform-owned microphone routing.
---

# Greia Activity Authoring Skill

**Status:** living derived authoring guide  
**Reviewed:** 2026-08-23

This skill is intentionally split so small local agents do not have to load unrelated specialist guidance for every task.

## Mandatory reading order

1. Read `CORE.md` completely for the canonical general Activity-authoring contract.
2. Read `DISCOVERY.md` whenever creating or editing `activity.toml`, launcher categories, audience/age metadata, difficulty/adaptive difficulty, discovery tags, or reasoning about how an Activity appears for a child.
3. When the Activity speaks, produces localized audio, uses shared Greia character utterances, teaches pronunciation, uses a Greia character voice, or changes Activity Designer audio tooling, also read `VOICE_GENERATION.md` completely.
4. When the Activity records from or listens to the microphone, also read `docs/adr/0031-platform-owned-microphone-processing.md` and `docs/architecture/GREIA_AUDIO_SERVICE.md`.
5. Follow every narrower repository `AGENTS.md` that applies to the files being changed.
6. Exact implemented APIs/schemas remain owned by source/runtime declarations; accepted ADRs own architecture; product docs own child-facing requirements.

Do not treat this index as permission to skip `CORE.md`.

## Discovery decision summary

Current Activity manifests may declare independent launcher, grouping, audience and challenge facts:

```toml
[presentation]
categories = ["play", "learn"]
discovery_tags = ["puzzles", "numbers"]

[education]
difficulty = 4
recommended_age_min = 5
recommended_age_max = 8
difficulty_min = 2
difficulty_max = 7
adaptive_difficulty = true
```

Do not reinterpret difficulty as age. Do not invent upper-age limits for open-ended creative Activities. Discovery tags are semantic hints from Greia's platform-owned grouping vocabulary; they are not filesystem folders and do not command a sub-Collection to exist. Greia/Parent policy owns per-child visibility, and missing age metadata fails open.

Full current manifest/discovery guidance:

```text
skills/greia-activity-authoring/DISCOVERY.md
docs/product/CHILD_ACTIVITY_DISCOVERY_AND_AUDIENCE.md
src/greia_platform/activities.py
src/greia_platform/activity_discovery.py
src/greia_launcher/catalogue_view.py
```

## Microphone decision summary

Microphone cleanup is a **Greia platform responsibility**, not an Activity DSP feature.

An Activity that captures microphone audio must declare/receive `audio.basic` through the normal capability path and obtain the platform-selected capture endpoint through:

```python
from greia_platform.activity_api import get_audio_capture_device

capture_device = get_audio_capture_device()
```

Pass that value to the runtime's capture-device open call. When it is `None` in a development/simulator composition, use the runtime's normal default capture endpoint.

Do **not**:

- enumerate host capture devices and select the first one;
- hard-code ALSA card/device names or `/dev/snd` nodes;
- add per-Activity denoising, AGC or noise-gate policy;
- inspect CPU/model/hardware and choose lightweight versus advanced processing;
- bypass Greia because a raw physical microphone appears to work locally.

Greia defaults to its lightweight processor when the concrete backend is available. A parent may disable processing, and advanced processing is an explicit Parent opt-in that is only exposed when the platform reports a real advanced endpoint. Activities should not care which DSP library realizes those modes.

Use `get_audio_processing_mode()` only for narrow diagnostics/presentation when genuinely needed; game/educational behavior must not depend on a particular DSP implementation.

Full microphone architecture and physical acceptance:

```text
docs/adr/0031-platform-owned-microphone-processing.md
docs/architecture/GREIA_AUDIO_SERVICE.md
docs/testing/2026-08-23_ACER_MICROPHONE_PROCESSING_ACCEPTANCE.md
src/greia_platform/audio.py
src/greia_platform/activity_api.py
```

## Speech/voice decision summary

Greia now distinguishes four semantic speech jobs:

```text
character_dialogue
shared_character_utterance
pedagogical_speech
dani_system_speech
```

The governing rule is:

> If the sound itself is the educational truth being taught, use pedagogical/system speech. If speech communicates content through a character, use character speech.

### Character dialogue

Lilli, Leo, Flash, Tito and Momo may use optional build-time/local **Chatterbox Multilingual V3** generation from the canonical reference voices. Every generated line is human-reviewed and packaged as an ordinary localized playback asset.

MOSS-TTS-Nano is **rejected** for Greia production quality. The repeated `ma. ma. ma.` / middle-extraction experiment is also **rejected**.

For ultra-short character reactions only, bounded Chatterbox output plus FFmpeg analysis/trim may be used when the final clip is reviewed. Do not use that technique to make Chatterbox a phonics/pronunciation engine.

### Pedagogical speech

Letters, letter names, syllables, phonics, spelling units and pronunciation targets use a deterministic/native/system TTS path. Correctness and consistency outrank mascot voice identity.

Do not pretend a mascot is speaking a teaching sample when the pedagogical voice is noticeably different; present it as a neutral educational audio object between character prompts/reactions.

### Shared character utterances

Before generating custom dialogue for generic feedback, prefer Greia's shared semantic character utterances such as:

```text
praise.congratulations
praise.great_work
praise.well_done
celebrate.you_did_it
encourage.try_again
ready.lets_go
```

The Italian/English v0.1 inventory, six-character coverage target and canonical animation associations are defined in:

```text
docs/design/GREIA_SHARED_CHARACTER_UTTERANCES.md
```

These are platform/shared assets, not duplicated into every Activity package.

### Dani

Dani remains:

```text
greia.dani.system-v1
```

A clearly robotic system voice is intentional. Do not clone Dani from another character or replace him with a natural cheerful voice.

## Voice toolchain capability rule

**Custom character voice generation is optional. Do not install it automatically.**

When custom character speech would be useful:

1. first check whether a shared Greia utterance satisfies the need;
2. if the sound is pedagogical, route to the deterministic/system speech path;
3. only then perform a non-mutating check for an already configured Chatterbox toolchain;
4. if Chatterbox is unavailable and the user did not explicitly request its installation, omit optional custom character dialogue and continue the Activity;
5. preserve captions/visual feedback and all essential instructions;
6. never substitute an arbitrary host voice for Lilli/Leo/Flash/Tito/Momo.

A missing optional voice toolchain must not make an otherwise valid Activity fail to build.

If the user explicitly requires custom canonical character dialogue and the toolchain is missing, follow the opt-in setup guide rather than silently downloading models:

```text
docs/agents/GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md
```

Current canonical IDs:

```text
greia.lilli.v1
greia.leo.v1
greia.flash.v1
greia.tito.v1
greia.momo.v1
greia.dani.system-v1
```

Every custom/static line must remain a semantic localization cue, be reviewed in every shipped language, and obey the non-overlap/sequencing requirements in `CORE.md`.

Full speech policy and workflow:

```text
docs/design/GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md
docs/design/GREIA_SHARED_CHARACTER_UTTERANCES.md
docs/agents/GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md
skills/greia-activity-authoring/VOICE_GENERATION.md
```
