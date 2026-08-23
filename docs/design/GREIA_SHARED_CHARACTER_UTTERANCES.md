# Greia Shared Character Utterances

**Status:** accepted design direction; audio asset production/runtime catalogue integration pending  
**Date:** 2026-08-23  
**Scope:** small OS-owned multilingual character interjections shared across Activities  
**Related:** `docs/design/GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md`, `docs/design/GREIA_CANONICAL_CAST_SYSTEM.md`, `docs/adr/0032-profile-presentation-and-grammatical-agreement.md`

## 1. Decision

Greia should ship a small, bounded library of **canonical prerecorded character utterances** for feedback that recurs across many Activities.

Examples are praise, encouragement, progress, playful starts, and completion reactions. These clips are platform/shared assets, not duplicated into every Activity package.

An Activity requests a semantic utterance family, for example:

```text
character = lilli
utterance = praise.general
locale = it
```

The Activity does **not** select an exact sentence or filename.

Greia resolves the reviewed array of available recordings for that character/locale/family, randomly selects one available variant, and presents it with the family's canonical expression/motion.

This library has three goals:

1. give Activities useful character personality even when the developer has **no local voice-cloning toolchain**;
2. keep common praise/encouragement consistent across Greia while still providing some variety;
3. avoid storing the same short audio in dozens of Activity packages.

It is not a general dialogue system and it is not the source of educational pronunciation truth.

## 2. Semantic families and v0.1 phrase variants

The semantic ID names the **meaning**, not one sentence.

Every variant inside one family must be safe wherever that family is requested. Do not put stronger/weaker or context-specific meanings into the same random pool merely because the wording sounds similar.

The initial v0.1 families are:

| Family | Italian variants | English variants | Default expression | Default motion |
|---|---|---|---|---|
| `praise.general` | `Complimenti!` · `Ottimo lavoro!` · `Ben fatto!` | `Congratulations!` · `Great work!` · `Well done!` | `happy` | `happy_hop` |
| `celebrate.success` | `Ce l'hai fatta!` · `Evviva!` · `Che meraviglia!` | `You did it!` · `Hooray!` · `Wonderful!` | `happy` | `celebrate_pop` |
| `encourage.retry` | `Riproviamo!` · `Quasi! Proviamo ancora!` · `Ancora una volta!` | `Let's try again!` · `Almost! Let's try again!` · `One more time!` | `happy` | `idle_bounce` |
| `encourage.progress` | `Continua così!` · `Ci sei quasi!` · `Vai avanti!` | `Keep going!` · `Almost there!` · `You're doing great!` | `happy` | `idle_bounce` |
| `ready.go` | `Forza, andiamo!` · `Ci siamo? Via!` · `Si parte!` | `Come on, let's go!` · `Ready? Go!` · `Here we go!` | `happy` | `happy_hop` |

The Italian v0.1 phrases deliberately avoid child-gender agreement such as `bravo/brava`. Gender-aware variants may be introduced later through the profile/localization agreement layer, but random selection happens **after** locale/agreement resolution so one random pool never mixes grammatically incompatible child-directed forms.

Exclamation marks and question/exclamation combinations in the reviewed source text are intentional. These are short character reactions, not neutral narration.

## 3. Character coverage

The complete v0.1 target matrix is:

```text
6 characters
× 5 semantic families
× 3 variants
× 2 initial locales (it, en)
= 180 reviewed clips
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

Production split:

```text
Lilli/Leo/Flash/Tito/Momo:
5 × 5 × 3 × 2 = 150 reviewed Chatterbox clips

Dani:
1 × 5 × 3 × 2 = 30 reviewed Greia system-TTS clips
```

Dani remains intentionally system-TTS/robotic. His shared clips must use the approved Greia Dani system-TTS profile, not a cloned natural voice.

A family is still valid when fewer than three variants survive review. The runtime catalogue contains only accepted recordings.

## 4. Variant-array and random-picker contract

Every resolved character + locale + semantic family owns a **non-empty ordered array of reviewed audio assets**.

Conceptually:

```text
shared_utterances[character][locale][family] = [
    reviewed_file_01,
    reviewed_file_02,
    reviewed_file_03,
]
```

Selection semantics are deliberately simple:

```python
variants = resolved_family.variants

if len(variants) == 1:
    selected = variants[0]
else:
    selected = rng.choice(variants)
```

Rules:

- one available recording is completely valid and is always selected;
- two or more available recordings are randomly selected to provide variety;
- rejected/missing recordings are absent from the runtime array rather than represented as empty placeholders;
- Activities never request `variant 01`, a filename, or an array index;
- adding a reviewed variant later must not require Activity changes;
- removing a bad variant must not require Activity changes;
- the random source belongs to the Greia resolver/presentation layer and should be injectable in tests;
- deterministic tests may supply a seeded/test RNG without changing production semantics;
- the semantic family owns expression/motion defaults, so a randomly selected filename cannot accidentally choose a different animation contract.

Greia may later add optional immediate-repeat suppression above this primitive, but the v0.1 contract is simply random choice from the current reviewed array. Do not build shuffle bags, histories, weighted selection, or adaptive reinforcement until there is evidence they are needed.

## 5. Relationship to canonical animation

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

The family table provides defaults, not an instruction for an Activity to animate raw frames itself. Greia's character presentation layer owns the actual implementation and must respect resource bounds.

The selected voice clip and its expression/motion are one presentation event. A caller must not start a different character animation and independently pick a speech file that implies another semantic state.

A shared utterance should be scheduled at a safe moment. Do not interrupt a timed answer, drawing gesture, text entry, pronunciation target, or another spoken instruction merely to play praise.

## 6. Selection, cooldown and repetition policy

Activities should request **semantics**, not precise wording.

The random picker provides wording variety, but it is not permission to spam feedback:

- do not play a spoken interjection for every trivial interaction;
- use a short platform/presentation cooldown or repetition-suppression policy where needed;
- never overlap two character clips;
- do not begin the next spoken instruction until the interjection has completed or been deliberately skipped;
- visual feedback must remain sufficient when speech is disabled;
- do not use randomness to change educational meaning, scoring, rewards, difficulty, or progression.

Randomness here is presentation-only.

## 7. Activity package boundary

Shared utterance audio belongs to the Greia shared asset/runtime catalogue.

An Activity package must **not** copy these files into its own `locales/<locale>/audio/` directory merely to use them.

Future source/runtime integration should expose a semantic resolver conceptually equivalent to:

```text
resolve_character_utterance(
    character_id,
    utterance_family,
    locale,
    grammatical_variant,
    rng,
) -> selected shared audio + expression/motion metadata
```

Resolution order is conceptually:

```text
character
→ locale/fallback
→ grammatical agreement/fallback where relevant
→ semantic family
→ non-empty reviewed variant array
→ random file selection
→ expression/motion metadata
```

The exact API is implementation-owned and is not created by this design document.

If a target Greia version lacks the requested family/locale, the Activity must fail soft: keep visual feedback and continue. Do not substitute an unrelated phrase.

## 8. Why this is separate from pedagogical speech

These utterances communicate emotion and feedback. They do not teach the child how a letter, syllable, phoneme, spelling unit, or foreign-language target is pronounced.

Greia therefore applies a stronger rule:

> If the sound itself is the educational truth being taught, use the deterministic pedagogical-speech path, not a character interjection or generative character voice.

For example:

```text
Lilli shared reaction:
randomly one of "Complimenti!" / "Ottimo lavoro!" / "Ben fatto!"

Pedagogical speech:
"ma"
```

The pedagogical clip may intentionally sound less characterful if that is required for stable correct pronunciation.

## 9. Recording and acceptance

The simple local-agent production runbook is:

```text
docs/agents/GREIA_SHARED_CHARACTER_UTTERANCE_RECORDING.md
```

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

One failed variant does not invalidate the entire family. Remove/reject that variant and keep the accepted non-empty array. A family with zero accepted variants is unavailable and must fail soft.

The library is versioned. Do not replace accepted bytes silently; publish a new asset/version when a materially different recording is accepted.

## 10. Implementation status

Accepted now:

- platform/shared ownership rather than per-Activity duplication;
- five semantic families with three Italian/English source variants each;
- six-character coverage target;
- 180-clip complete v0.1 target;
- random choice from the current reviewed variant array;
- one-element arrays naturally resolving to the only available file;
- canonical family-level animation association;
- semantic request/fail-soft direction;
- pedagogical-speech separation;
- local Chatterbox recording/review runbook for the five cloned characters.

Not yet implemented by this documentation change:

- the 180 audio files;
- runtime/shared-asset catalogue entries;
- semantic resolver API/source;
- cooldown source;
- Activity Designer picker UI;
- automated asset validation.
