---
name: greia-activity-authoring
description: Canonical agent guide for designing, implementing, packaging, validating and testing Greia Activities, including current discovery/audience metadata and localized canonical character-voice generation.
---

# Greia Activity Authoring Skill

**Status:** living derived authoring guide  
**Reviewed:** 2026-08-23

This skill is intentionally split so small local agents do not have to load unrelated specialist guidance for every task.

## Mandatory reading order

1. Read `CORE.md` completely for the canonical general Activity-authoring contract.
2. Read `DISCOVERY.md` whenever creating or editing `activity.toml`, launcher categories, audience/age metadata, difficulty/adaptive difficulty, discovery tags, or reasoning about how an Activity appears for a child. The discovery schema migration is now implemented; `DISCOVERY.md` is the current source-aligned correction to older prose that still labels those fields as future.
3. When the Activity speaks, produces localized audio, uses a Greia character voice, or changes Activity Designer audio tooling, also read `VOICE_GENERATION.md` completely.
4. Follow every narrower repository `AGENTS.md` that applies to the files being changed.
5. Exact implemented APIs/schemas remain owned by source/runtime declarations; accepted ADRs own architecture; product docs own child-facing requirements.

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

## Voice-generation decision summary

Greia's current Activity-authoring direction is build-time/local voice production:

```text
semantic localized cue
→ canonical character voice policy
→ MOSS-TTS-Nano local rendering for Lilli/Leo/Flash/Tito/Momo
→ Greia OS TTS policy for Dani
→ human-reviewed WAV master
→ bounded OGG/WAV package asset
→ ordinary localization audio cue
```

The production model, Python environment, model cache, canonical voice references and generation scratch files are developer tooling. They do not belong in `.greiaactivity` packages and do not become a child-runtime dependency.

Current canonical voice IDs:

```text
greia.lilli.v1       warm wonder, stories, art and imagination
greia.leo.v1         warm oldish savvy storyteller and patient guidance
greia.flash.v1       bright quick playful action and friendly challenge
greia.tito.v1        warm adventurous exploration and discovery
greia.momo.v1        musical unusual emotion, silliness and celebration
greia.dani.system-v1 clearly robotic Greia OS text-to-speech
```

Dani intentionally has no cloned reference in v0.1. A natural cloned voice that does not sound robotic is a worse character match than the platform's clearly synthetic voice. Activities address `greia.dani.system-v1`; they must not select an arbitrary macOS/Linux voice by name.

Every line must remain a semantic localization cue, be reviewed by a human in every shipped language, and obey the non-overlap/sequencing requirements in `CORE.md`.

Full voice policy and workflow:

```text
docs/design/GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md
docs/agents/GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md
skills/greia-activity-authoring/VOICE_GENERATION.md
```
