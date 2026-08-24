# Greia Activity Presenters, Character Voice and Curiosity Facts

**Status:** focused companion for new Activity concept/presentation work  
**Audience:** Activity authors, coding agents, reviewers  
**Reviewed:** 2026-08-24

Use this companion when creating a new Activity or materially redesigning its child-facing presentation.

It owns **when and why** an Activity should use Greia's recurring characters, spoken presentation, and small researched curiosity/fact moments. Voice production mechanics remain in:

```text
skills/greia-activity-authoring/VOICE_GENERATION.md
docs/design/GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md
```

Canonical cast identity remains in:

```text
docs/design/GREIA_CANONICAL_CAST_SYSTEM.md
```

## 1. A presenter decision is mandatory for every new Activity

Greia's recurring cast exists to give children recognizable social anchors across the OS and Activities. A new Activity design must therefore explicitly decide:

```text
lead presenter/mascot
supporting character(s), if any
or a deliberate no-presenter decision with a product reason
```

Do not accidentally omit the cast merely because the gameplay can technically function without characters.

A presenter is not mandatory in every single Activity. It is, however, a **mandatory design consideration**. The default should be to use a fitting recurring character when that adds warmth, orientation, personality, encouragement, curiosity or continuity without obstructing play.

Useful default affinities:

```text
Lilli  -> creativity, stories, art, imagination, wonder
Leo    -> reading, language, knowledge, calm explanation
Flash  -> games, speed, action, playful challenge
Dani   -> math, logic, patterns, sequencing
Tito   -> exploration, nature, discovery, investigation
Momo   -> music, emotion, silliness, experimentation, celebration
```

These are affinities, not hard silos. A nature Activity may have Tito lead and Leo contribute a knowledge moment; a game may have Flash lead while Momo celebrates.

## 2. What a presenter should actually do

A lead character should have a small, meaningful role rather than being decorative wallpaper.

Good presenter jobs include:

- brief welcome/orientation;
- demonstrate or frame the first interaction visually;
- give one short spoken instruction when language is useful;
- react to progress through shared utterance families;
- offer a contextual hint without solving the task;
- celebrate completion;
- introduce an optional curiosity/fact interaction;
- narrate a tiny piece of relevant real-world knowledge.

Avoid turning every Activity into a talking tutorial. Greia is child-driven and often language-light.

Prefer:

```text
short character moment -> child acts -> quiet play -> occasional meaningful reaction
```

over:

```text
long speech -> more speech -> modal explanation -> child waits
```

Character presentation must never block the child from replaying, experimenting or understanding the core interaction visually.

## 3. Speech is a design tool, not an afterthought

For every new Activity, make an explicit **speech plan** during design. Ask:

```text
Does a character welcome or frame the Activity?
Does spoken feedback improve warmth or comprehension?
Is any sound itself pedagogical truth?
Would an optional curiosity/facts feature enrich the subject?
Which lines should use shared utterances versus custom dialogue?
Which locales must be covered?
```

The **voice-generation toolchain is optional**; this design pass is not.

Do not interpret a missing local Chatterbox installation as a reason to design an Activity with no semantic speech architecture. Keep cue IDs, localization and presenter ownership clean so reviewed audio can be produced when the toolchain is available.

Then follow:

```text
skills/greia-activity-authoring/VOICE_GENERATION.md
```

for classification and production.

## 4. Use the right speech path

Classify every spoken cue by purpose:

```text
shared_character_utterance
    generic praise, retry, progress, ready/go, celebration

character_dialogue
    presenter welcome, contextual narration, hints, curiosity facts,
    Activity-specific explanation or story

pedagogical_speech
    the sound itself is what the child is learning: phonics, letters,
    syllables, spelling/pronunciation targets

dani_system_speech
    Dani's intentionally robotic system/logic voice
```

A factual sentence about an orca is normally **character dialogue**, because the sentence communicates knowledge through the character. It is not pronunciation-authoritative pedagogical speech.

Use Greia's shared utterance families before generating custom generic praise. Use custom character voice only when the wording itself is Activity-specific and valuable.

## 5. Curiosity/fact moments

Subject-rich Activities should actively consider a small optional **curiosity/facts interaction**.

Examples:

```text
orca play Activity
    -> small "curiosity" / info affordance
    -> Tito or Leo says one short researched orca fact

space Activity
    -> telescope/info affordance
    -> Leo says one short astronomy fact

music Activity
    -> Momo shares a short instrument/sound fact

bridge-building Activity
    -> Dani or Leo shares a short engineering fact
```

This is not mandatory when the Activity subject has no useful real-world knowledge angle, when it would clutter the interaction, or when facts would distract from a very focused sensory/gameplay experience.

When it fits, it is strongly encouraged because it turns play into a gateway for curiosity without turning the Activity into a lesson screen.

### Fact interaction rules

The fact feature should normally be:

- optional and child-invoked;
- one tap/click/controller action away;
- non-modal or very lightweight;
- short enough to hear without interrupting play for long;
- repeatable;
- presentation-only: never required for score/progression/completion;
- offline at runtime;
- safe to ignore entirely.

Do not force a child to listen to facts before continuing the game.

## 6. Facts must be researched, not improvised

Every shipped factual claim must have authoring-time provenance.

Prefer authoritative sources such as:

- government/scientific agencies;
- museums and recognized scientific institutions;
- universities;
- peer-reviewed or expert-reviewed reference material;
- established conservation/science organizations with clear editorial authority.

For a stable, simple fact, one strong authoritative source may be enough. For surprising, quantitative, contested or easily misunderstood claims, corroborate with a second reliable source.

Do not use an LLM's memory as the source of truth.

Do not generate facts dynamically at runtime.

Do not make the child device require internet access to retrieve facts.

### Provenance record

Keep a source-only research record next to Activity development material. Preferred pattern:

```text
activities/<activity>/research/facts.md
```

or, if that Activity already has an established source/research directory, use that existing location.

For each fact record at least:

```text
fact semantic ID
canonical meaning
source title / organization
source URL or publication identifier
retrieval/publication date when relevant
notes about simplification for children
```

Do not package research notes as runtime content unless the package format/project policy explicitly wants them there.

## 7. Child-safe fact writing

Facts should be accurate **and** written for a young child.

Prefer one compact idea per fact.

Good:

```text
"Le orche vivono in famiglie molto unite chiamate pod."
```

Avoid:

- dense statistics without meaning;
- scary detail merely because it is dramatic;
- anthropomorphic claims presented as scientific fact;
- oversimplification that becomes false;
- uncertain claims presented as settled;
- conservation messaging that frightens or guilts the child;
- long mini-lectures.

If simplifying a nuanced fact, preserve the scientific truth even if the wording becomes less flashy.

## 8. Multilingual-ready from the first implementation

**Character presentation, custom dialogue and curiosity facts must never be designed as one-language hard-coded strings.**

Every cue/fact should have a stable semantic ID independent of language:

```text
presenter.welcome
presenter.hint.first
curiosity.orca.family_pods
curiosity.orca_unique_calls
```

Runtime code selects semantic IDs. Localization owns the text.

Example conceptual structure:

```text
curiosity.orca.family_pods
    it -> reviewed Italian child-facing wording
    en -> reviewed English child-facing wording
```

Do not write:

```python
if locale == "it":
    fact = "..."
else:
    fact = "..."
```

inside gameplay logic.

When the Activity declares multiple supported locales, the fact/presenter feature must be designed for all of them. Do not ship a curiosity button that speaks only Italian while the Activity claims English support.

### Spoken coverage

For a voice-driven presenter/fact feature:

- generate/review audio for every shipped locale when custom character audio is part of the accepted feature;
- use the same canonical speaker identity across localized versions;
- keep text and spoken wording semantically aligned;
- if grammatical child-address variants are used, text/audio must resolve the same variant;
- if custom voice production is unavailable during development, keep semantic/localized cues ready and report the missing audio honestly rather than hard-coding one locale.

A text-only fallback may keep the Activity functional where the product deliberately allows optional speech degradation, but it is **not evidence that multilingual voice production itself is complete**.

## 9. Fact selection should not repeat badly

If several facts are available, prefer a tiny bounded selector that avoids immediate repetition rather than unconstrained randomness.

Good patterns:

```text
shuffle-bag of fact IDs
or
random selection excluding the just-played fact
```

Keep the fact pool finite and small enough to review fully.

Selection is presentation-only. It must not change gameplay state, scoring, rewards or difficulty.

## 10. Presenter visuals and voice should agree

If Tito speaks, the presentation should make it visually clear that Tito is speaking when practical. If Leo owns the curiosity button, do not play Flash's voice behind a Leo portrait.

Use canonical runtime character assets and semantic expression/motion states rather than Activity-local redraws of the cast.

Read:

```text
docs/design/GREIA_CANONICAL_CAST_SYSTEM.md
docs/design/GREIA_CHARACTER_EXPRESSIONS_AND_MOTION.md
skills/greia-visual-authoring/SKILL.md
```

when presenter visuals are being added or changed.

## 11. Acceptance checklist for new Activities

Before calling a new Activity presentation design complete, answer:

```text
PRESENTER_DECISION=
LEAD_CHARACTER_OR_NONE=
WHY=
SHARED_UTTERANCE_PLAN=
CUSTOM_DIALOGUE_PLAN=
PEDAGOGICAL_SPEECH_PLAN=
CURIOSITY_FACTS_APPROPRIATE=yes/no
FACT_RESEARCH_PROVENANCE_PATH=
SUPPORTED_LOCALES=
SPOKEN_LOCALE_COVERAGE=
```

If the Activity is subject-rich and `CURIOSITY_FACTS_APPROPRIATE=no`, record a brief reason. The purpose is to force the design decision, not to force a fact button into every game.

Runtime changes still finish with:

```text
skills/greia-activity-authoring/LAUNCH_ACCEPTANCE.md
```

and voice/audio acceptance still follows:

```text
skills/greia-activity-authoring/VOICE_GENERATION.md
```
