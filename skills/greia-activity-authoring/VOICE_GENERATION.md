# Voice Generation for Greia Activities

This file is a focused companion to `SKILL.md`. Read the canonical design first:

```text
docs/design/GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md
```

For installation and local production commands:

```text
docs/agents/GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md
```

## Mandatory authoring rules

1. Speech is optional. Visual communication remains sufficient for the target age where the product contract requires it.
2. Use semantic cue IDs and localization bundles; never bind gameplay to model commands or generated filenames.
3. Generate ordinary character speech at build/authoring time.
4. Package only reviewed OGG/WAV playback assets.
5. Never package models, caches, Python environments or the canonical source masters or production anchors inside an Activity.
6. Do not create a new character voice per Activity.
7. Do not upload Greia reference voices to a cloud service without explicit owner authorization.
8. A generation command exiting zero is not audio acceptance.

## Canonical voice choice

| Speaker | Voice ID | Use when | Why |
|---|---|---|---|
| Lilli | `greia.lilli.v1` | wonder, creativity, stories, art, gentle encouragement | Lilli is Greia's warm imaginative guide |
| Leo | `greia.leo.v1` | reading, language, patient explanation, reflective hints | Leo is warm, oldish and savvy—not a young schoolteacher |
| Flash | `greia.flash.v1` | action, speed, games, lively retries | Flash communicates kinetic playful energy |
| Tito | `greia.tito.v1` | exploration, nature, investigation, adventure | Tito invites children to look, discover and investigate |
| Momo | `greia.momo.v1` | music, emotion, silliness, experimentation, celebration | Momo provides distinctive musical and expressive play |
| Dani | `greia.dani.system-v1` | logic, patterns, numbers, concise robot feedback | Dani must remain obviously robotic; use Greia OS TTS until a reviewed robotic reference exists |

Soft specialization applies. A character may support another character's Activity, but the voice must remain that character's canonical voice.

## Writing and generation workflow

For each spoken cue:

```text
semantic cue ID
→ exact localized text
→ intended character
→ generate review WAV
→ listen and review
→ regenerate if needed
→ convert accepted output to OGG/WAV
→ reference from locale bundle
→ test sequencing in the Activity
```

Prefer short, complete utterances. Do not concatenate translated fragments. Preserve text/caption parity.

Example bundle entry:

```json
"audio": {
  "feedback.correct": {
    "path": "locales/it/audio/feedback-correct.ogg",
    "caption_key": "feedback.correct"
  }
}
```

## Dani policy

Dani has no canonical cloning anchor in v0.1. This is intentional.

Do not:

- clone Dani from another character;
- use a natural cheerful voice and call it robotic;
- choose a developer-machine voice by arbitrary host name;
- fall back to system TTS for the other five characters.

Address Dani through `greia.dani.system-v1`; the platform/Designer owns the eventual approved system-TTS profile.

## Audio review

Reject and regenerate when there is:

- wrong or drifting speaker identity;
- wrong language;
- omitted, repeated or invented words;
- bad stress/pronunciation;
- clipped beginnings/endings;
- noise, reverb or distortion;
- excessive silence;
- an emotionally inappropriate delivery.

Test spoken cues with the Activity's sound effects and the sequencing rules in `SKILL.md`. Never overlap prompts, praise and the next instruction.

## Local production

On Apple Silicon, use MLX Audio with:

```text
mlx-community/MOSS-TTS-Nano-100M
```

For other machines, use the approved upstream ONNX CPU path. Voice-design models are not installed for production.

Exact setup and smoke-test commands live in:

```text
docs/agents/GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md
```
