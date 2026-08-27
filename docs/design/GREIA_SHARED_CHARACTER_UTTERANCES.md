# Greia Shared Character Utterances

**Status:** accepted design direction; Voice Engine production implemented; reviewed audio/runtime catalogue completion remains separate  
**Reviewed:** 2026-08-28  
**Scope:** small OS-owned multilingual character interjections shared across Activities  
**Related:** `docs/design/GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md`, `docs/design/GREIA_CANONICAL_CAST_SYSTEM.md`, `docs/adr/0032-profile-presentation-and-grammatical-agreement.md`, `skills/greia-voice-production/SKILL.md`

## 1. Decision

Greia should ship a small, bounded library of **canonical prerecorded character utterances** for feedback that recurs across many Activities.

Examples are praise, encouragement, progress, playful starts, and completion reactions. These clips are platform/shared assets, not duplicated into every Activity package.

An Activity requests a semantic utterance family, for example:

```text
character = lilli
utterance = praise.general
locale = it
```

The Activity does **not** select an exact sentence or filename and does not synthesize the line at child runtime.

Greia resolves the reviewed array of available recordings for that character/locale/family, randomly selects one available variant, and presents it with the family's canonical expression/motion.

This library has three goals:

1. give Activities useful character personality even when the developer has **no local voice-cloning toolchain**;
2. keep common praise/encouragement consistent across Greia while still providing variety;
3. avoid storing the same short audio in dozens of Activity packages.

It is not a general dialogue system and it is not the source of educational pronunciation truth.

## 2. Semantic families and v0.1 phrase variants

The semantic ID names the **meaning**, not one sentence.

Every variant inside one family must be safe wherever that family is requested. Do not put stronger/weaker or context-specific meanings into the same random pool merely because wording sounds similar.

| Family | Italian variants | English variants | Default expression | Default motion |
|---|---|---|---|---|
| `praise.general` | `Complimenti!` · `Ottimo lavoro!` · `Ben fatto!` | `Congratulations!` · `Great work!` · `Well done!` | `happy` | `happy_hop` |
| `celebrate.success` | `Ce l'hai fatta!` · `Evviva!` · `Che meraviglia!` | `You did it!` · `Hooray!` · `Wonderful!` | `happy` | `celebrate_pop` |
| `encourage.retry` | `Riproviamo!` · `Quasi! Proviamo ancora!` · `Ancora una volta!` | `Let's try again!` · `Almost! Let's try again!` · `One more time!` | `happy` | `idle_bounce` |
| `encourage.progress` | `Continua così!` · `Ci sei quasi!` · `Vai avanti!` | `Keep going!` · `Almost there!` · `You're doing great!` | `happy` | `idle_bounce` |
| `ready.go` | `Forza, andiamo!` · `Ci siamo? Via!` · `Si parte!` | `Come on, let's go!` · `Ready? Go!` · `Here we go!` | `happy` | `happy_hop` |

The Italian v0.1 phrases deliberately avoid child-gender agreement such as `bravo/brava`. Gender-aware variants may be introduced later through profile/localization agreement, but random selection happens **after** locale/agreement resolution so one pool never mixes incompatible forms.

Punctuation is intentional. These are short character reactions, not neutral narration.

## 3. Character coverage and production route

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

All central library production goes through the Greia Voice Production Engine with:

```text
kind = shared_character_utterance
```

The engine routes automatically:

```text
Lilli/Leo/Flash/Tito/Momo -> canonical cloned-character provider
Dani                       -> deterministic native/system Dani provider
```

The underlying provider is an engine implementation detail. Do not maintain a parallel shared-library Chatterbox/Dani production stack.

Dani remains intentionally system-TTS/robotic. His shared clips must use `greia.dani.system-v1`, not a cloned natural voice.

A family is valid when fewer than three variants survive review. Runtime catalogue arrays contain only accepted recordings.

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

Selection semantics:

```python
variants = resolved_family.variants
selected = variants[0] if len(variants) == 1 else rng.choice(variants)
```

Rules:

- one available recording is valid and always selected;
- two or more provide presentation variety;
- rejected/missing recordings are absent, not empty placeholders;
- Activities never request `variant 01`, a filename, or an array index;
- adding/removing a reviewed variant requires no Activity change;
- random source belongs to Greia resolver/presentation and should be injectable in tests;
- semantic family owns expression/motion defaults;
- randomness must never alter correctness, score, rewards, difficulty or progression.

Greia may later add immediate-repeat suppression, but do not add shuffle bags, histories, weighting or adaptive reinforcement without evidence.

## 5. Relationship to canonical animation

Shared speech may request only established semantic expression/motion vocabulary such as:

```text
neutral
happy
surprised
idle_bounce
happy_hop
celebrate_pop
surprised_wobble
```

The family table provides defaults. Greia's character presentation layer owns actual animation implementation and resource bounds.

The selected voice clip and expression/motion form one presentation event. Do not independently pick semantically conflicting speech/animation.

Schedule shared utterances safely. Do not interrupt a timed answer, drawing gesture, text entry, pronunciation target or another spoken instruction merely to play praise.

## 6. Selection, cooldown and repetition policy

Activities request **semantics**, not precise wording.

The random picker provides wording variety, not permission to spam feedback:

- do not play speech for every trivial interaction;
- use bounded cooldown/repetition suppression where needed;
- never overlap two character clips;
- do not start another spoken instruction until the interjection completes or is deliberately skipped;
- visual feedback remains sufficient when speech is unavailable/disabled;
- randomness is presentation-only.

## 7. Activity package/runtime boundary

Shared utterance audio belongs to Greia's shared asset/runtime catalogue.

An Activity package must **not** copy these files merely to use them.

Future/current source integration should expose a semantic resolver conceptually equivalent to:

```text
resolve_character_utterance(
    character_id,
    utterance_family,
    locale,
    grammatical_variant,
    rng,
) -> selected shared audio + expression/motion metadata
```

Resolution order:

```text
character
-> locale/fallback
-> grammatical agreement/fallback where relevant
-> semantic family
-> non-empty reviewed variant array
-> random file selection
-> expression/motion metadata
```

If a target Greia version lacks the requested family/locale, fail soft with visual feedback; do not substitute an unrelated phrase.

`shared_character_utterance` in `VoiceEngine` is solely the **authoring-production** kind used to create this central library. It does not mean Activities synthesize shared speech at runtime.

## 8. Why this is separate from pedagogical speech

These utterances communicate emotion/feedback. They do not teach how a letter, syllable, phoneme, spelling unit or foreign-language target is pronounced.

> If the sound itself is the educational truth being taught, use the deterministic `pedagogical_speech` route, not a character interjection or cloned character voice.

A pedagogical clip may intentionally sound less characterful when necessary for stable correct pronunciation.

## 9. Production and acceptance

Canonical producer:

```text
tools/record_shared_character_utterances.py
```

Canonical runbook:

```text
docs/agents/GREIA_SHARED_CHARACTER_UTTERANCE_RECORDING.md
```

The producer is intentionally a thin `VoiceEngine` client. It does not directly own Chatterbox, Whisper, native TTS, trimming or model lifecycle.

Every generated candidate has an engine receipt and remains:

```text
human_review = PENDING
```

Before promotion:

- exact locale/text is reviewed by a fluent speaker;
- no invented/repeated sounds;
- character identity recognizable where applicable;
- Dani clearly robotic;
- beginnings/endings not clipped;
- loudness consistent enough with Greia speech;
- expression/motion association appropriate;
- small-speaker playback acceptable.

Whisper may be used by the engine as an advisory filter for suitable natural-character multi-word lines. It never accepts a clip. Tiny reactions and Dani normally skip ASR.

One failed variant does not invalidate a family. A family with zero accepted variants is unavailable and must fail soft.

The library is versioned. Do not replace accepted bytes silently; publish a new accepted asset/version when materially changing a recording.

## 10. Implementation status

Implemented/accepted now:

- platform/shared ownership rather than per-Activity duplication;
- five semantic families with three Italian/English source variants each;
- six-character / 180-clip target;
- semantic runtime request/fail-soft direction;
- one/multiple reviewed-variant array semantics;
- family-level animation association;
- pedagogical-speech separation;
- repository-wide Voice Production Engine route for central library production;
- `tools/record_shared_character_utterances.py` as a thin engine producer for all six characters;
- Dani system-provider routing;
- optional advisory ASR for eligible natural-character shared lines;
- machine receipts/human-review boundary.

Still separately incomplete/evidence-owned where applicable:

- actual human acceptance of all 180 target clips;
- runtime/shared-asset catalogue population/resolver if not already implemented elsewhere;
- cooldown source;
- Activity Designer picker UI;
- complete runtime asset validation/coverage evidence.
