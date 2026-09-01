# Launcher Spoken Labels for Greia Activities

This companion owns the Activity-authoring side of spoken catalogue names.
Runtime selection, hover behavior and playback are Greia Shell responsibilities.

## Contract

Every newly created first-party Activity that supplies localized catalogue text MUST also supply a reviewed prerecorded spoken launcher title for every catalogue locale it claims as complete.

The semantic cue is always:

```text
activity.title
```

Do not invent per-Activity cue names such as `launcher.my_game_name`, do not add speech code to `main.py`, and do not synthesize the title at child runtime.

The localized bundle already used by ADR 0028 owns the mapping:

```json
{
  "schema_version": 1,
  "locale": "it",
  "direction": "ltr",
  "strings": {
    "activity.title": "L'Acquario Magico"
  },
  "audio": {
    "activity.title": {
      "path": "locales/it/audio/activity-title.wav",
      "caption_key": "activity.title"
    }
  }
}
```

Equivalent English example:

```json
{
  "audio": {
    "activity.title": {
      "path": "locales/en/audio/activity-title.wav",
      "caption_key": "activity.title"
    }
  }
}
```

The displayed title and spoken title must identify the same Activity. They need not be byte-for-byte identical when natural speech requires a harmless article or pronunciation choice, but they must not communicate a different name.

## Production

Use the canonical Voice Production Engine only:

```text
skills/greia-voice-production/SKILL.md
tools/greia_voice_core/README.md
tools/greia_voice.py
```

Launcher titles are ordinary communicative speech, not pronunciation teaching. Do not route them through `pedagogical_speech` merely because the title is short.

Choose a canonical Greia speaker that matches the Activity's accepted presenter/identity when one exists. If an Activity deliberately has no presenter, use the project-approved neutral/system speaker route defined by the Voice Production skill; do not pick an arbitrary host voice.

Generate into a review workspace first. Example:

```bash
python3 tools/greia_voice.py generate \
  --speaker tito \
  --kind character_dialogue \
  --locale it \
  --text "L'Acquario Magico" \
  --cue-id activity.title \
  --output ./tmp/voice-review/acquario_magico/it/activity-title.wav
```

Human listening remains mandatory before copying the clip into the Activity package.

## Runtime ownership

The Activity does NOT:

- listen for launcher hover/focus;
- play the launcher-title clip;
- own a mixer/channel for catalogue narration;
- query mouse position while it is not running;
- synthesize speech at runtime;
- copy platform Collection/category speech into its package.

Greia Shell resolves the current child UI locale, loads the Activity's localized `activity.title` cue, and speaks it when the Activity destination gains pointer hover or keyboard/controller selection.

Greia Shell also owns interruption/de-duplication: repeated motion inside one tile must not replay the title and moving to another destination replaces the previous spoken label rather than queuing speech.

## Locale and fallback rules

Launcher-title speech is catalogue localization, which is intentionally separate from the Activity's own runtime UI language under ADR 0028.

Authoring target:

- provide `activity.title` text + audio for each supported catalogue locale;
- locale-specific and base-language fallback is platform-owned;
- an English compatibility fallback may keep an older/single-locale package understandable, but it is not evidence that the missing locale is complete;
- missing optional speech must fail silent at runtime, but first-party authoring/validation should report it as incomplete rather than hiding the omission.

## Existing Activities

Do not hand-edit every Activity's Python code. Migration consists only of:

1. confirm the accepted localized launcher title;
2. produce/review `activity.title` speech through the Voice Production Engine;
3. place the accepted clip below that locale's package resources;
4. add the `audio.activity.title` mapping to the locale JSON;
5. validate package/localization resources;
6. exercise launcher hover + keyboard navigation in the Greia Simulator;
7. later perform physical-device audio/latency acceptance on the Acer floor.

## Completion checklist

An Activity's launcher-name accessibility is complete only when:

```text
[ ] activity.title display string exists for every claimed catalogue locale
[ ] activity.title audio mapping exists for every completed catalogue locale
[ ] clip produced through VoiceEngine
[ ] clip human-reviewed
[ ] no runtime TTS or Activity-side launcher behavior added
[ ] package/localization validation passes
[ ] hover speaks once on entering the tile
[ ] repeated motion within the same tile does not repeat
[ ] keyboard/controller selection speaks once per newly selected tile
[ ] moving selection interrupts/replaces old title rather than queues it
[ ] missing/broken optional clip cannot crash or hide the Activity
```
