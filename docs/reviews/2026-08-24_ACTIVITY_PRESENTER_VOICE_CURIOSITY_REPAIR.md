# Review — Activity presenter, voice and curiosity authoring repair

**Date:** 2026-08-24  
**Scope:** Activity-authoring guidance / design authority  
**Runtime implementation changed:** no

## Problem

The concise Activity `SKILL.md` correctly routed engineering/testing tasks but reduced canonical-character and voice work to a narrow optional branch. An agent creating a new Activity could therefore complete design and implementation without ever making an explicit presenter decision or considering useful character speech.

The existing voice companion also used wording equivalent to "voice support is optional". The intended meaning was that the heavy custom Chatterbox toolchain is optional, but the wording could be interpreted as "speech/presenter design is optional".

This weakened a core Greia product idea: recurring characters should provide recognizable social continuity across Activities, often acting as brief presenters/guides rather than appearing only occasionally as decoration.

A second missed opportunity was subject-driven curiosity. Activities about animals, nature, space, engineering, music, history-like subject matter, etc. can enrich play with tiny optional, researched, spoken facts without turning gameplay into a text-heavy lesson.

## Correction

Created:

```text
skills/greia-activity-authoring/PRESENTERS_AND_CURIOSITY.md
```

Updated:

```text
skills/greia-activity-authoring/SKILL.md
skills/greia-activity-authoring/VOICE_GENERATION.md
docs/design/GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md
docs/design/GREIA_CANONICAL_CAST_SYSTEM.md
```

## New authoring contract

Every new Activity must explicitly decide:

```text
lead presenter/mascot or deliberate none
supporting character presence, if useful
shared-utterance plan
custom dialogue plan
pedagogical speech plan
whether subject-driven curiosity facts are appropriate
supported locales / multilingual spoken coverage
```

The presenter decision is mandatory to make; a character is not mandatory to force into every Activity.

The default product direction is to use a fitting recurring character when it adds warmth, orientation, personality, encouragement, curiosity or continuity without blocking play.

## Curiosity/facts contract

Subject-rich Activities must explicitly consider a small optional curiosity/facts interaction.

When used, facts must be:

- short and child-safe;
- optional and child-invoked;
- finite reviewed content;
- researched from authoritative sources during authoring;
- provenance-recorded in source/development material;
- offline at child runtime;
- represented by stable semantic IDs;
- localized independently of gameplay logic;
- spoken in reviewed canonical-character voice when voice is part of the accepted feature;
- multilingual-ready across the Activity's supported locales;
- presentation-only, never required for score/progression/completion.

Example design pattern:

```text
Baia delle Orche
-> curiosity/info affordance
-> Tito or Leo presents one short researched orca fact
-> localized text mirrors the same meaning
-> another activation selects another reviewed fact without immediate repetition
```

This example is an authoring pattern; this documentation tranche does not itself implement the feature in `baia_delle_orche`.

## Important voice distinction

The corrected rule is:

```text
presenter/speech design pass     -> mandatory to consider
custom Chatterbox installation   -> optional / never silently installed
shared utterances                -> use when generic reaction is enough
custom character dialogue        -> use for presenter/context/facts when valuable
pedagogical pronunciation        -> deterministic/system speech
Dani                              -> robotic Greia system voice
```

A missing Chatterbox environment must not cause an agent to hard-code one language, impersonate a canonical character with arbitrary OS TTS, or erase the intended semantic speech architecture.

## Multilingual invariant

Character dialogue and curiosity facts are localized semantic content from the first implementation, not Italian strings that are translated later.

If a voice-driven feature is claimed complete for a multilingual Activity, its shipped locales require reviewed spoken coverage (or an explicitly documented product-approved degradation policy). Text fallback may preserve function but does not prove multilingual voice production is complete.

## Evidence boundary

This tranche changes documentation/authoring policy only. It does not:

- generate new voice assets;
- add a fact UI to an existing Activity;
- establish simulator acceptance for an Activity;
- establish physical Acer evidence.
