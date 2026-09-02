# Greia Activity Presenters and Curiosity

**Status:** focused companion for new Activity presentation/character/fact design  
**Load when:** a new Activity chooses a presenter, uses character dialogue, or includes optional researched facts

This file owns **what the presenter does and why**. Voice production mechanics live in `VOICE_GENERATION.md` and `skills/greia-voice-production/SKILL.md`.

## 1. Every new Activity makes a presenter decision

Choose deliberately:

```text
lead presenter/mascot
supporting character(s), if useful
or deliberate no-presenter decision with a product reason
```

Do not accidentally omit Greia's recurring cast merely because the Activity can technically run without them.

A presenter is not mandatory in every Activity, but the decision is mandatory.

Useful affinities:

```text
Lilli  -> creativity, stories, art, imagination, wonder
Leo    -> reading, language, knowledge, calm explanation
Flash  -> games, speed, action, playful challenge
Dani   -> math, logic, patterns, sequencing
Tito   -> exploration, nature, investigation, discovery
Momo   -> music, emotion, silliness, experimentation, celebration
```

These are affinities, not hard silos.

## 2. A presenter should have a real job

Good presenter roles include:

- short welcome/orientation;
- visual demonstration of the first action;
- required spoken command when language is needed;
- contextual hint;
- progress/retry reaction;
- completion celebration;
- optional curiosity/fact moment.

Do not place a character portrait on screen as decoration while anonymous text or unrelated audio carries the actual interaction.

Prefer:

```text
short character moment
-> child acts
-> quiet play
-> occasional useful reaction
```

over constant narration.

## 3. Required presenter commands are not optional

If the Activity relies on a presenter to communicate a required language instruction, that instruction must have accepted spoken coverage for the shipped locale.

A missing local voice-production environment may delay production. It does **not** convert a required spoken command into an accepted text-only feature.

Allowed interim status:

```text
DESIGN/SOURCE READY — REQUIRED SPEECH PENDING
```

Not allowed:

```text
COMPLETE
```

until required speech has been produced/reviewed and exercised in the final GUI Simulator flow.

The screen must still visually reinforce the command; speech should not be the only clue to a confusing interaction.

## 4. Decide speech purpose during design

Classify planned cues before generation:

```text
character_dialogue
    welcome, Activity-specific command, contextual hint, narration, fact

shared_character_utterance
    generic praise/retry/progress/ready/celebration when the current runtime
    resolver exposes the accepted family

pedagogical_speech
    exact sound being taught: letter name/sound, syllable, phonics,
    spelling/pronunciation target

dani_system_speech
    Dani's intentionally robotic presenter/logic speech
```

Do not route all speech through `pedagogical_speech` simply because the Activity is educational.

Examples:

```text
Leo: "Ciao! Scopriamo le lettere!"     -> character_dialogue
Tito: "Trova l'orca con la pinna alta" -> character_dialogue
Dani: "Metti tre mele nel cestino"     -> dani_system_speech
exact "A" / "MA" teaching target       -> pedagogical_speech
```

Generic praise/retry should use shared semantics when the current resolver supports them instead of being rerecorded repeatedly.

## 5. Accepted shared character material

Current accepted shared asset set:

```text
assets/audio/characters/shared/v0.2/
180 shared reactions
12 canonical character introductions
192 owner-accepted clips total
```

Do not call this asset set pending generation/listening.

Runtime resolver availability is separate. Check current source before depending on a family from an Activity.

Canonical character self-introductions are shared/OS presentation content. Do not duplicate them in each Activity.

A short contextual welcome is fine when it tells the child something specific about the current Activity.

## 6. Curiosity/fact moments are optional but valuable

Subject-rich Activities should deliberately consider a small curiosity/facts interaction.

Examples:

```text
orca Activity
    -> Tito/Leo shares a short researched orca fact

space Activity
    -> Leo shares a short astronomy fact

music Activity
    -> Momo shares a short instrument/sound fact

bridge Activity
    -> Dani/Leo shares a short engineering fact
```

Do not force a fact feature into a purely sensory/simple game where it distracts from play.

When facts fit, prefer them to be:

- optional and child-invoked;
- one action away;
- short;
- spoken by a fitting presenter;
- repeatable;
- non-modal/lightweight;
- offline at runtime;
- unrelated to score/correctness/progression.

Do not force the child to listen before continuing play.

## 7. Facts are researched, never improvised at child runtime

Every shipped factual claim needs authoring-time provenance.

Prefer authoritative sources such as:

- scientific/government agencies;
- museums;
- universities;
- peer/expert-reviewed references;
- established science/conservation institutions.

Use one strong source for simple stable facts; corroborate surprising/quantitative/contested claims.

Do not use an LLM's memory as the source of truth and do not fetch/generate facts on the child device.

Keep research material in the Activity development area while authoring. Remove authoring-only research/scratch material from the final package tree unless it is intentionally runtime content.

For each fact record:

```text
semantic fact ID
canonical meaning
source title / organization
source URL/publication identifier
relevant date
notes on child-safe simplification
```

## 8. Write facts for young children

One compact idea per fact.

Prefer:

```text
"Le orche vivono in famiglie molto unite chiamate pod."
```

over mini-lectures.

Avoid:

- scary detail for drama;
- false anthropomorphism;
- dense statistics without meaning;
- oversimplification that becomes wrong;
- uncertain claims presented as certain;
- guilt/fear-heavy conservation messaging.

## 9. Multilingual from the first design

Use semantic IDs independent of language:

```text
presenter.welcome
instruction.find_orca
presenter.hint.first
curiosity.orca.family_pods
```

Runtime code chooses the semantic cue. Localization owns wording/audio.

For every shipped locale of a required presenter feature:

- localized wording exists;
- required audio exists and is accepted;
- same canonical character identity is preserved;
- text/audio remain semantically aligned;
- grammatical variants resolve consistently where used.

Do not ship a required presenter command that speaks only one language while the Activity claims another locale.

## 10. Presenter visual and voice must agree

When practical, make it visually clear who is speaking.

If Tito speaks, do not show Leo as the active speaker. If Dani owns the Activity, do not play an anonymous natural voice behind Dani art.

Use canonical Greia character assets/expression/motion systems rather than redrawing identity ad hoc.

Load:

```text
docs/design/GREIA_CANONICAL_CAST_SYSTEM.md
docs/design/GREIA_CHARACTER_EXPRESSIONS_AND_MOTION.md
skills/greia-visual-authoring/SKILL.md
```

when presenter visuals are created/changed.

## 11. Fact selection should avoid annoying repetition

For several facts use a tiny bounded selector such as:

```text
shuffle bag
or
random excluding the immediately previous fact
```

Keep the pool finite and fully reviewable.

Fact selection is presentation-only and must not alter gameplay truth, scoring or difficulty.

## 12. Final presenter review

For a new Activity record:

```text
PRESENTER_DECISION=
LEAD_CHARACTER_OR_NONE=
PRESENTER_JOB=
REQUIRED_PRESENTER_COMMANDS=
SHARED_UTTERANCE_PLAN=
CUSTOM_DIALOGUE_PLAN=
PEDAGOGICAL_SOUND_PLAN=
SUPPORTED_LOCALES=
REQUIRED_SPOKEN_COVERAGE=
CURIOSITY_FACTS_APPROPRIATE=yes/no
FACT_PROVENANCE_PATH=
```

Final GUI Simulator review must verify that required presenter speech actually occurs at the right time and that the child can act without reading.

Voice-production acceptance remains governed by `VOICE_GENERATION.md`; mechanical launch evidence remains governed by `SIMULATOR_WORKFLOW.md` / `LAUNCH_ACCEPTANCE.md`.