---
name: greia-activity-authoring
description: Canonical agent guide for designing, implementing, packaging, validating and testing Greia Activities, including clean OOP structure, measured low-resource performance, discovery/audience metadata, optional canonical character speech, deterministic pedagogical speech, shared character utterances, child grammatical agreement, and platform-owned microphone routing.
---

# Greia Activity Authoring Skill

**Status:** living derived authoring guide  
**Reviewed:** 2026-08-23

This skill is intentionally split so small local agents do not have to load unrelated specialist guidance for every task.

## Mandatory reading order

1. Read `CORE.md` completely for the canonical general Activity-authoring contract.
2. Read `ENGINEERING.md` whenever creating, modifying, reviewing, optimizing or substantially refactoring Activity implementation code. For new/substantively changed first-party Activities it is mandatory: it owns the practical clean-code/OOP/decomposition/performance protocol, including the rule that `main.py` is a thin composition root rather than the Activity implementation.
3. Read `DISCOVERY.md` whenever creating or editing `activity.toml`, launcher categories, audience/age metadata, difficulty/adaptive difficulty, discovery tags, or reasoning about how an Activity appears for a child.
4. When packaging or exporting an Activity, also read `docs/architecture/GREIA_ACTIVITY_PACKAGE_FORMAT.md`. Parent-facing distribution uses the `.greiaactivity` ZIP contract; the extension is a UX/routing signal, never package validation or trust.
5. When the Activity speaks, produces localized audio, uses shared Greia character utterances, teaches pronunciation, uses a Greia character voice, changes Activity Designer audio tooling, or needs child-directed grammatical agreement, also read `VOICE_GENERATION.md` completely and `docs/adr/0032-profile-presentation-and-grammatical-agreement.md` where agreement is relevant.
6. When the Activity records from or listens to the microphone, also read `docs/adr/0031-platform-owned-microphone-processing.md` and `docs/architecture/GREIA_AUDIO_SERVICE.md`.
7. Follow every narrower repository `AGENTS.md` that applies to the files being changed.
8. Exact implemented APIs/schemas remain owned by source/runtime declarations; accepted ADRs own architecture; product docs own child-facing requirements.

Do not treat this index as permission to skip `CORE.md` or, for implementation work, `ENGINEERING.md`.

## Implementation engineering decision summary

Greia Activities are supervised content, not miniature standalone applications. Their code should expose obvious, reusable responsibilities instead of accumulating everything in one script.

For non-trivial Python Activities:

```text
main.py
    thin composition/bootstrap boundary

app/lifecycle owner
    top-level Activity state/transitions

domain/model objects
    round/game/content state + invariants

presentation/renderer
    drawing/layout + bounded prepared resources

optional collaborators
    challenge generation, semantic input, audio sequencing,
    persistence mapping, Activity-owned resource preparation
```

Exact filenames are not mandated; cohesive ownership is.

Strong defaults:

- model stable state/lifecycle/invariants with classes/dataclasses;
- use narrow Protocol/ABC seams only for genuine substitutable behavior;
- prefer composition over deep inheritance;
- inject dependencies rather than discover mutable global services;
- reuse Greia platform APIs/primitives instead of Activity-local copies;
- keep `main.py` bootstrap-only (roughly >150 lines triggers review; >250 normally requires decomposition for first-party code);
- review modules above roughly 500 lines and methods above roughly 60–80 lines for mixed ownership rather than gaming line counts;
- public/non-obvious extension objects document responsibility, lifecycle, invariants and resource bounds;
- comments explain architectural/performance **why**, not obvious syntax.

Performance is a correctness concern on Greia's Acer-class floor. In normal frame/event hot paths, do not decode images, large-scale/flip reusable sprites, construct fonts, render stable text repeatedly, allocate large unchanged Surfaces, regenerate static scenery, walk/stat the filesystem, enumerate devices, launch subprocesses, parse configuration or write durable storage.

Required performance patterns include bounded caches with complete keys/invalidation, pre-rendered static scenes, dirty/invalidation-driven redraw where practical, bounded monotonic-time animations, fail-soft optimized paths, and semantic/pixel-equivalence testing for rendering optimizations.

Current Activity working targets:

```text
smooth gameplay:       ~30 fps on Atom-class floor
added input latency:   <= 50 ms
static/paused idle:    near-zero CPU where architecture permits
```

Desktop/simulator timing is diagnostic only. Claims about Acer/Pi performance require named physical hardware and exact source SHA.

Full implementation protocol and measured rationale:

```text
skills/greia-activity-authoring/ENGINEERING.md
docs/engineering/ENGINEERING_FOUNDATIONS.md
docs/engineering/GREIA_PERFORMANCE_BEST_PRACTICES.md
```

## Package decision summary

Normal parent-facing Activity distribution is one file:

```text
<activity-name>.greiaactivity
```

It is an ordinary ZIP whose Activity contents are stored directly at archive root, with `activity.toml` at root. Do not wrap the Activity in an extra directory.

The canonical media type is:

```text
application/vnd.greia.activity+zip
```

The extension/media type help file pickers and humans identify the package. They are **not** evidence of safety or trust. A renamed ZIP still has to pass `ActivityPackageService` and normal Activity validation before Greia activates it.

Developer/simulator tools may accept an unpacked Activity directory or raw `.zip` as convenience inputs. Do not present generic ZIP as the normal Parent install format.

Full package contract:

```text
docs/architecture/GREIA_ACTIVITY_PACKAGE_FORMAT.md
src/greia_platform/activity_package_format.py
src/greia_platform/activity_packages.py
```

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

## Child presentation and grammatical agreement summary

A child's optional presentation preference is deliberately small:

```text
neutral → neutral
boy     → masculine
girl    → feminine
```

This is **not** a gameplay or content classification. Never use it to hide Activities, choose subjects, alter challenge, change rewards/progression, select permissions, or infer interests.

Python Activities that genuinely need child-directed grammatical agreement should use:

```python
from greia_platform.activity_api import get_profile_grammatical_gender

variant = get_profile_grammatical_gender().value
```

and pass the same variant to both localized text and localized audio:

```python
caption = resources.text("feedback.correct", variant=variant)
voice = resources.audio_cue("feedback.correct", variant=variant)
```

Use a natural neutral base cue and optional semantic variants only when needed. Italian example:

```text
feedback.correct             = "Ottimo lavoro!"
feedback.correct.masculine   = "Bravo!"
feedback.correct.feminine    = "Brava!"
```

Do not write language-specific `if boy`/`if girl` branches in gameplay. Localization owns the words; Greia supplies only the semantic agreement selector.

Full contract:

```text
docs/adr/0032-profile-presentation-and-grammatical-agreement.md
skills/greia-activity-authoring/VOICE_GENERATION.md
src/greia_platform/profile_presentation.py
src/greia_platform/localization.py
src/greia_platform/activity_api.py
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

Greia distinguishes four semantic speech jobs:

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

Before generating custom dialogue for generic feedback, prefer the Greia shared semantic families:

```text
praise.general
celebrate.success
encourage.retry
encourage.progress
ready.go
```

Each family resolves to an array of reviewed files for the selected character/locale. The Activity never chooses an exact phrase or filename.

```text
one available file  → always that file
multiple files       → Greia randomly chooses one reviewed variant
```

The random choice is presentation-only; gameplay, scoring, correctness, rewards and difficulty must not depend on it.

The Italian/English variants, 180-clip complete target, random-picker contract, and canonical animation associations are defined in:

```text
docs/design/GREIA_SHARED_CHARACTER_UTTERANCES.md
```

These are platform/shared assets, not duplicated into every Activity package.

When producing the library itself, use:

```text
docs/agents/GREIA_SHARED_CHARACTER_UTTERANCE_RECORDING.md
```

### Dani

Dani remains:

```text
greia.dani.system-v1
```

A clearly robotic system voice is intentional. Do not clone Dani from another character or replace him with a natural cheerful voice.

## Voice toolchain capability rule

**Custom character voice generation is optional. Do not install it automatically.**

When custom character speech would be useful:

1. first check whether a shared Greia utterance family satisfies the need;
2. if the sound is pedagogical, route to deterministic/system speech;
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

Every custom/static line must remain a semantic localization cue, be reviewed in every shipped language, preserve text/audio grammatical-variant parity where variants are used, and obey the non-overlap/sequencing requirements in `CORE.md`.

Full speech policy and workflow:

```text
docs/design/GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md
docs/design/GREIA_SHARED_CHARACTER_UTTERANCES.md
docs/agents/GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md
docs/agents/GREIA_SHARED_CHARACTER_UTTERANCE_RECORDING.md
skills/greia-activity-authoring/VOICE_GENERATION.md
```
