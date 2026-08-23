# ADR 0032 — Profile presentation preference and grammatical agreement

Status: **Accepted for staged implementation**

Date: 2026-08-23

Extends: ADR 0012 (platform architecture constitution), ADR 0018 (lightweight UI), ADR 0022 (Parent API), ADR 0028 (localization language context)

## Context

Greia child profiles already own independent customization state. Some languages also require occasional grammatical agreement when an Activity addresses the child directly. Italian is the motivating example: a celebratory adjective may naturally be `bravo` for a boy and `brava` for a girl.

A single profile preference can usefully provide two very small conveniences:

1. a gentle first-run visual starting point; and
2. a grammatical-addressing hint for localized child-directed text and prerecorded speech.

Those conveniences must not turn sex/gender into a gameplay taxonomy or create permanent stereotyped themes. Activities must not use the value to decide what the child may play, what they are good at, which difficulty they receive, what rewards they earn, or what capabilities they receive.

Greia also runs on very constrained machines. Runtime grammatical handling must therefore be small and deterministic, while high-quality character voices remain authoring/build-time assets rather than runtime neural TTS.

## Decision

### 1. Store a profile presentation preference, not a broad identity model

Greia defines the bounded profile presentation values:

- `neutral`
- `boy`
- `girl`

The persisted value lives in the profile customization namespace as `presentation.json`. It is separate from the core profile record and separate from security/progression state.

`neutral` is the compatibility and fail-safe default. Existing profiles therefore require no migration.

This field is intentionally named **presentation**, not `sex`, `gender_identity`, `content_gender`, or similar. Greia does not attempt to infer or model a child's identity. The setting exists only for presentation and child-directed grammatical agreement.

### 2. Derive a small grammatical agreement selector

Greia maps presentation to a separate semantic value:

| Presentation | Grammatical agreement |
| --- | --- |
| `neutral` | `neutral` |
| `boy` | `masculine` |
| `girl` | `feminine` |

Activities receive only these resolved semantic launch values:

- `GREIA_PROFILE_PRESENTATION`
- `GREIA_PROFILE_GRAMMATICAL_GENDER`

Python Activities should use the typed Activity API helpers rather than reading environment variables directly:

- `get_profile_presentation()`
- `get_profile_grammatical_gender()`

Ordinary Activities do not receive the profile customization path or presentation store.

### 3. Neutral wording remains the baseline

Activity authors should prefer a natural gender-neutral complete phrase whenever the language allows it without making the writing awkward.

For example, Italian can often use:

- base/neutral: `Ottimo lavoro!`
- masculine variant: `Bravo!`
- feminine variant: `Brava!`

The neutral form is not required to be a mechanical neutralization of the adjective. It should be a natural sentence in the target language.

This is important because:

- old profiles default to neutral;
- some parents may choose neutral;
- not every language needs grammatical gender here;
- a translation may reasonably omit a variant;
- it gives every cue a robust fallback.

### 4. Localization bundles use bounded semantic resource variants

ADR 0028 remains authoritative for locale selection and fallback. This ADR adds one deliberately small extension instead of introducing a full ICU-style message language.

A semantic resource may have optional variant keys:

```json
{
  "strings": {
    "feedback.correct": "Ottimo lavoro!",
    "feedback.correct.masculine": "Bravo!",
    "feedback.correct.feminine": "Brava!"
  }
}
```

Audio uses the same semantic convention:

```json
{
  "audio": {
    "feedback.correct": {"path": "audio/it/correct-neutral.ogg"},
    "feedback.correct.masculine": {"path": "audio/it/correct-masculine.ogg"},
    "feedback.correct.feminine": {"path": "audio/it/correct-feminine.ogg"}
  }
}
```

When a caller requests a variant, Greia resolves resources in this order for each locale in the existing locale fallback chain:

1. `<semantic-key>.<variant>` in the current locale;
2. the base `<semantic-key>` in the same locale;
3. then the next locale.

Therefore an Italian neutral fallback is preferred over an English gendered variant when the Italian bundle lacks a requested variant.

The variant identifier is bounded and semantic. It is not arbitrary source text and does not select files directly.

### 5. Text and speech must use the same agreement decision

The grammatical selector is not a voice-only feature. If an Activity has both caption/text and prerecorded speech for one semantic cue, both must resolve using the same agreement value. Greia must not display `Bravo!` while playing a recording of `Brava!`, or vice versa.

Activity authoring should therefore treat the cue as one semantic resource with parallel text/audio variants rather than separate ad-hoc conditionals.

### 6. Voice variants are generated at authoring/build time

For high-quality Greia character voices, gendered wording variants are generated using the same approved character voice as the neutral cue and shipped as normal portable OGG/WAV resources.

Example authoring set for one Italian cue:

- neutral source text: `Ottimo lavoro!`
- masculine source text: `Bravo!`
- feminine source text: `Brava!`

All three recordings use the same character voice/persona. The child's presentation preference affects the adjective addressed to the child; it does **not** change the speaking character's voice.

Runtime neural voice generation is not required and should not be introduced for this feature. Existing OS TTS exceptions remain separate.

### 7. Presentation may seed a theme once, but never owns the theme

Greia may use the presentation selection to initialize an uncustomized child's visual theme:

| Presentation | Background | Accent | Text |
| --- | --- | --- | --- |
| neutral | normal Greia defaults | normal Greia defaults | normal Greia defaults |
| boy | `sky` | `turquoise` | `navy` |
| girl | `lavender` | `raspberry` | `plum` |

These are intentionally light starting points, not permanent rules.

Theme seeding is one-way initialization:

- it occurs only when no saved theme preference exists;
- changing `boy` / `girl` / `neutral` later does not overwrite the child's chosen theme;
- child/parent customization remains fully independent afterwards;
- Activities must not infer presentation from theme colors or theme colors from presentation.

### 8. Parent UI semantics

The Parent client presents this as **Style & wording**, with `Neutral`, `Boy`, and `Girl` choices and an explanation that it can affect gentle starting colors and grammatical wording but never Activity availability.

The versioned Parent API exposes:

- `GET /api/v1/profiles/{profile_id}/presentation`
- `PUT /api/v1/profiles/{profile_id}/presentation`

with capability `profiles.presentation`.

The protocol declares the resource globally but the base capability is fail-closed. Only a concrete composition that owns the profile customization store advertises it as enabled.

## Non-goals and prohibitions

This feature does **not**:

- create boy Activities and girl Activities;
- alter Activity discovery or recommendations;
- alter challenge/difficulty;
- alter progression, badges, scores, or rewards;
- alter capabilities or permissions;
- prescribe interests, characters, colors, subjects, or gameplay by gender;
- infer presentation from the child's name, avatar, activity history, or theme;
- require every sentence to have gendered variants;
- introduce a general-purpose grammatical engine;
- dynamically synthesize high-quality Activity voices on constrained child hardware.

## Failure behaviour

Invalid, missing, unreadable, or unsupported persisted presentation state resolves to `neutral`.

Invalid or missing launch context also resolves to neutral.

A missing requested localized variant falls back to the base semantic resource in the same locale.

A profile presentation update that requests initial theme seeding must leave an already customized theme untouched.

## Consequences

### Positive

- Italian and other agreement-sensitive languages can address the child naturally.
- Captions and prerecorded speech share one semantic decision.
- Existing profiles and existing localization bundles remain compatible.
- No expensive runtime language or TTS machinery is required.
- Parent-facing boy/girl convenience does not become a deep platform classification.

### Costs

- Activity authors may need two extra short text/audio assets for the relatively small number of cues that genuinely require agreement.
- The Parent update is currently a second typed mutation after core profile creation/update; failure leaves the safe neutral/default presentation rather than rolling back the profile.
- A richer future localization system may eventually supersede the suffix convention; the semantic cue IDs should make that migration straightforward.

## Implementation map

- profile state: `src/greia_platform/profile_presentation.py`
- Activity launch injection: `src/greia_launcher/child_shell.py`
- Activity helpers: `src/greia_platform/activity_api.py`
- localization variants: `src/greia_platform/localization.py`
- Parent protocol/API: `src/greia_parent/protocol.py`, `src/greia_parent/update_api.py`
- authoring guidance: `skills/greia-activity-authoring/VOICE_GENERATION.md`
