# Voice Generation for Greia Activities

This file is a focused companion to `SKILL.md`. Read the canonical design first:

```text
docs/design/GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md
```

For installation and local production commands:

```text
docs/agents/GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md
```

For child-directed grammatical agreement:

```text
docs/adr/0032-profile-presentation-and-grammatical-agreement.md
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
9. Child-directed text and speech for one cue must resolve through the same grammatical-agreement variant.
10. Prefer a natural neutral phrase when possible; create masculine/feminine variants only where the target language genuinely benefits from them.

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
→ decide whether grammatical variants are actually needed
→ generate review WAV(s)
→ listen and review
→ regenerate if needed
→ convert accepted output to OGG/WAV
→ reference from locale bundle
→ test text/audio variant parity and sequencing in the Activity
```

Prefer short, complete utterances. Do not concatenate translated fragments. Preserve text/caption parity.

Example bundle entry without grammatical variants:

```json
"audio": {
  "feedback.correct": {
    "path": "locales/it/audio/feedback-correct.ogg",
    "caption_key": "feedback.correct"
  }
}
```

## Child-directed grammatical agreement

Greia exposes a small grammatical selector for the active child:

```text
neutral
masculine
feminine
```

This is for localized agreement only. It does not select content, difficulty, rewards, characters, interests or gameplay.

### Prefer neutral wording when it is natural

Do **not** manufacture masculine/feminine forms merely because the API supports them.

For Italian, a good cue set could be:

```text
feedback.correct             → "Ottimo lavoro!"
feedback.correct.masculine   → "Bravo!"
feedback.correct.feminine    → "Brava!"
```

The base semantic cue is the required neutral fallback. The masculine/feminine entries are optional.

When the child has a neutral/unset preference, or a requested variant is absent, Greia uses the base cue in the same locale.

### Text and audio variants must be parallel

If the cue is spoken, generate every supported wording with the **same canonical speaker voice**:

```text
feedback.correct             → locales/it/audio/feedback-correct-neutral.ogg
feedback.correct.masculine   → locales/it/audio/feedback-correct-masculine.ogg
feedback.correct.feminine    → locales/it/audio/feedback-correct-feminine.ogg
```

A bundle can then contain:

```json
{
  "strings": {
    "feedback.correct": "Ottimo lavoro!",
    "feedback.correct.masculine": "Bravo!",
    "feedback.correct.feminine": "Brava!"
  },
  "audio": {
    "feedback.correct": {
      "path": "locales/it/audio/feedback-correct-neutral.ogg",
      "caption_key": "feedback.correct"
    },
    "feedback.correct.masculine": {
      "path": "locales/it/audio/feedback-correct-masculine.ogg",
      "caption_key": "feedback.correct.masculine"
    },
    "feedback.correct.feminine": {
      "path": "locales/it/audio/feedback-correct-feminine.ogg",
      "caption_key": "feedback.correct.feminine"
    }
  }
}
```

At runtime, resolve both resources with the same variant:

```python
from greia_platform.activity_api import get_profile_grammatical_gender
from greia_platform.localization import LocalizedResources

variant = get_profile_grammatical_gender().value
caption = resources.text("feedback.correct", variant=variant)
voice = resources.audio_cue("feedback.correct", variant=variant)
```

Do not hand-code Italian checks such as `if boy: "bravo"` inside gameplay. The Activity should ask Greia for the semantic grammatical selector and let localization own the language-specific words.

### The child's selector does not change the speaker

If Lilli says `Bravo!` or `Brava!`, both versions are generated with Lilli's canonical voice. The child-directed adjective changes; Lilli does not become a male or female voice.

The same applies to every canonical character.

### Keep the variant set small

Do not attempt to encode a complete grammar engine into cue suffixes. `neutral`, `masculine`, and `feminine` cover the current child-addressing requirement. If a future language requires richer plural/case/select semantics, extend the localization architecture deliberately rather than creating Activity-specific suffix vocabularies.

## Dani policy

Dani has no canonical cloning anchor in v0.1. This is intentional.

Do not:

- clone Dani from another character;
- use a natural cheerful voice and call it robotic;
- choose a developer-machine voice by arbitrary host name;
- fall back to system TTS for the other five characters.

Address Dani through `greia.dani.system-v1`; the platform/Designer owns the eventual approved system-TTS profile.

If Dani speaks a cue that requires child-directed grammatical agreement, supply the selected localized text to the approved Dani/OS TTS path. The same semantic cue and selector rules still apply even though Dani's audio is not pre-rendered in v0.1.

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

For variant sets, also reject the set when delivery, pacing or energy changes enough that masculine/feminine selection feels like a different character performance rather than a wording variant.

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
