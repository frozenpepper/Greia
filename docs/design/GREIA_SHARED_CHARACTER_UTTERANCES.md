# Greia Shared Character Utterances

**Status:** accepted design direction; audio asset production/runtime catalogue integration pending  
**Date:** 2026-08-23  
**Scope:** small OS-owned multilingual character interjections shared across Activities  
**Related:** `docs/design/GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md`, `docs/design/GREIA_CANONICAL_CAST_SYSTEM.md`

## 1. Decision

Greia should ship a small, bounded library of **canonical prerecorded character utterances** for feedback that recurs across many Activities.

Examples are praise, encouragement, a playful start, and completion reactions. These clips are platform/shared assets, not duplicated into every Activity package.

An Activity requests a semantic utterance, for example:

```text
character = lilli
utterance = praise.great_work
locale = it
```

Greia resolves the reviewed shared audio asset and a compatible canonical expression/motion. Activity code must not hard-code a shared asset filesystem path.

This library has three goals:

1. give Activities useful character personality even when the developer has **no local voice-cloning toolchain**;
2. keep common praise/encouragement consistent across Greia;
3. avoid storing the same short audio in dozens of Activity packages.

It is not a general dialogue system and it is not the source of educational pronunciation truth.

## 2. Initial v0.1 semantic inventory

The initial library should remain deliberately small. The same semantic cue exists for every canonical character; wording may remain identical in v0.1 and may later gain reviewed character-specific variants without changing the semantic cue ID.

| Cue ID | Italian | English | Default expression | Default motion |
|---|---|---|---|---|
| `praise.congratulations` | `Complimenti!` | `Congratulations!` | `happy` | `celebrate_pop` |
| `praise.great_work` | `Ottimo lavoro!` | `Great work!` | `happy` | `happy_hop` |
| `praise.well_done` | `Ben fatto!` | `Well done!` | `happy` | `happy_hop` |
| `celebrate.you_did_it` | `Ce l'hai fatta!` | `You did it!` | `happy` | `celebrate_pop` |
| `encourage.try_again` | `Riproviamo insieme!` | `Let's try again!` | `happy` | `idle_bounce` |
| `ready.lets_go` | `Forza, andiamo!` | `Come on, let's go!` | `happy` | `happy_hop` |

The Italian v0.1 phrases deliberately avoid child-gender agreement such as `bravo/brava`. Gender-aware variants may be introduced later through localization/profile grammar policy; shared v0.1 clips must not guess a child's gender.

## 3. Character coverage

The target matrix is:

```text
6 characters
× 6 semantic utterances
× 2 initial locales (it, en)
= 72 reviewed clips
```

Characters:

```text
lilli
leo
flash
dani
tito
momo
```

For Lilli, Leo, Flash, Tito and Momo, production may use the reviewed canonical character voice workflow.

Dani remains intentionally system-TTS/robotic. His shared clips should be rendered with the approved Greia Dani system-TTS profile, not by cloning another character.

## 4. Relationship to canonical animation

Shared speech may request only the established semantic expression/motion vocabulary from the canonical cast system:

```text
neutral
happy
surprised

idle_bounce
happy_hop
celebrate_pop
surprised_wobble
```

The table above provides defaults, not an instruction for an Activity to animate raw frames itself. Greia's character presentation layer owns the actual implementation and must respect resource bounds.

A shared utterance should be scheduled at a safe moment. Do not interrupt a timed answer, drawing gesture, text entry, pronunciation target, or another spoken instruction merely to play praise.

## 5. Selection and repetition policy

Activities should request **semantics**, not a precise line whenever a shared cue is sufficient.

Greia may later select among reviewed variants for the same cue ID, but selection must remain bounded and predictable. Avoid repetitive praise spam:

- do not play a spoken interjection for every trivial interaction;
- use a short cooldown/repetition-suppression policy;
- never overlap two character clips;
- do not begin the next spoken instruction until the interjection has completed or been deliberately skipped;
- visual feedback must remain sufficient when speech is disabled.

## 6. Activity package boundary

Shared utterance audio belongs to the Greia shared asset/runtime catalogue.

An Activity package should **not** copy these files into its own `locales/<locale>/audio/` directory merely to use them.

Future source/runtime integration should expose a semantic resolver conceptually equivalent to:

```text
resolve_character_utterance(
    character_id,
    utterance_id,
    locale,
) -> shared audio + expression/motion metadata
```

The exact API is implementation-owned and is not created by this design document.

If a target Greia version lacks the requested shared cue or locale, the Activity must fail soft: keep visual feedback and continue. Do not substitute an unrelated phrase.

## 7. Why this is separate from pedagogical speech

These utterances communicate emotion and feedback. They do not teach the child how a letter, syllable, phoneme, spelling unit, or foreign-language target is pronounced.

Greia therefore applies a stronger rule:

> If the sound itself is the educational truth being taught, use the deterministic pedagogical-speech path, not a character interjection or generative character voice.

For example:

```text
Lilli: shared/character speech
"Ottimo lavoro!"

Pedagogical speech
"ma"
```

The second clip may intentionally sound less characterful if that is required for stable correct pronunciation.

## 8. Production/acceptance

Before any shared clip is promoted:

- exact locale/text must be reviewed by a fluent speaker;
- generated content must contain no invented/repeated sounds;
- character identity must be recognizable where applicable;
- Dani must remain clearly robotic;
- beginnings/endings must not be clipped;
- loudness must be consistent with other Greia speech;
- expression/motion association must be appropriate;
- the clip must be tested on small speakers;
- provenance/model/provider information must be retained outside the runtime asset where appropriate.

The library should be versioned. Do not replace accepted bytes silently; publish a new asset/version when a materially different recording is accepted.

## 9. Implementation status

Accepted now:

- platform/shared ownership rather than per-Activity duplication;
- initial Italian/English semantic inventory;
- six-character coverage target;
- canonical animation association;
- semantic request/fail-soft direction;
- pedagogical-speech separation.

Not yet implemented by this documentation change:

- the 72 audio files;
- runtime/shared-asset catalogue entries;
- semantic resolver API;
- cooldown/variant-selection source;
- Activity Designer picker;
- automated asset validation.
