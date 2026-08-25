# Greia Activity Pre-Reader UX

**Status:** mandatory focused companion for child-facing Activity design  
**Audience:** Activity authors, coding agents, reviewers  
**Reviewed:** 2026-08-25

Greia targets young children, and **many intended users cannot read yet**. Therefore ordinary Activity gameplay must not depend on written instructions, labels, menus, or explanatory prose.

This document owns the pre-reader interaction rule. Use it for every new Activity and every substantive child-facing UI/interaction redesign.

## 1. Core invariant

> **A child in the target age range who cannot read must still be able to understand what to do, act, recover from mistakes, and continue playing.**

Text may exist as a secondary caption for parents, older children, localization review, accessibility support, or reinforcement. It must not be the only channel carrying the gameplay instruction.

Bad:

```text
"Click the blue whale, then press Continue."
"Choose the number of fish you saw."
"Drag the triangle to the matching shape."
```

if the child must read those sentences to proceed.

Preferred communication stack:

```text
clear scene composition
+ obvious visual target
+ large icon / symbol / number
+ motion or demonstration
+ short reviewed spoken cue when language helps
+ optional child voice recording when expression/replay adds value
+ immediate visual/audio feedback
```

## 2. Design the screen so the action is obvious

Do not use voice to rescue a confusing screen.

The Activity should communicate through hierarchy and affordance first:

- one visually dominant current goal;
- large interactive targets;
- strong contrast between active and decorative elements;
- familiar shapes/icons rather than abstract text labels;
- animated pointing, pulsing, bouncing, highlighting or example motion when useful;
- clear cause-and-effect after input;
- minimal competing UI;
- no dense toolbars or adult-style settings panels in the child play surface;
- no hidden essential action available only through hover or reading.

A good first frame should make a reasonable next action apparent even with the speakers muted.

## 3. Use large icons, symbols and numbers

For pre-reader Activities, prefer semantic visual language:

```text
▶ / large play symbol       -> start/replay
🔊 or controlled Greia audio icon -> hear/replay sound
🎙 / Greia microphone affordance  -> record child voice when appropriate
large 1, 2, 3, 4            -> quantity/choice
matching pictures/shapes     -> selection
arrows / gesture animation   -> movement direction
character demonstration      -> how to act
```

Use controlled Greia semantic assets for platform/system controls; do not replace trusted system Home/Back with arbitrary emoji.

Numbers are acceptable when the Activity teaches or uses number recognition. Keep them large and visually dominant; do not bury them inside explanatory sentences.

Touch/click targets should follow the current Greia child-size standards, normally at least 64×64 logical px and preferably larger for primary actions.

## 4. Voice is often the right replacement for written instruction

When language genuinely helps, use short spoken cues through the Greia speech architecture rather than text-only instructions.

Examples:

```text
Tito: "Trova l'orca con la pinna alta!"
Leo:  "Quale fa rima con gatto?"
Dani: "Quanti ne hai visti?"
```

Keep spoken instructions short. Prefer one idea at a time.

### 4.1 Gender-Neutral Spoken & Written Praise (MANDATORY)

**Never use gender-specific adjectives in Italian (or any other language)** such as *"Bravissimo!"*, *"Bravissima!"*, *"Bravo!"*, or *"Brava!"*. 

Always use universal, inclusive gender-neutral praise:
- `Ottimo lavoro!` ("Great job!")
- `Ben fatto!` ("Well done!")
- `Esatto!` ("Exactly right!")
- `Fantastico!` ("Fantastic!")
- `Evviva!` ("Hooray!")
- `Perfetto!` ("Perfect!")
- `Super!` ("Super!")
- `Che meraviglia!` ("Wonderful!")

Do not narrate every interaction. A good pattern is:

```text
brief spoken cue
-> child acts
-> quiet exploration/play
-> concise feedback only when useful
```

Read:

```text
skills/greia-activity-authoring/PRESENTERS_AND_CURIOSITY.md
skills/greia-activity-authoring/VOICE_GENERATION.md
```

for speaker selection, multilingual semantic cues, shared utterances, custom dialogue and pedagogical speech.

### 4.2 Child voice recording is an available pre-reader input/creation tool

Greia also has a platform-owned, lightweight-cleaned microphone path for Activities with `audio.basic`.

When it genuinely helps the experience, **consider letting the child speak instead of requiring typing or written composition**. Good examples include narrating a puppet scene, recording a pretend radio segment, explaining a drawing, imitating an animal sound, or recording/replaying a phrase.

This does not mean every Activity should record. The question is whether voice gives the child a meaningful expressive action that would otherwise be harder for a pre-reader.

A pre-reader recording flow should be visually self-explanatory:

```text
large mic button
-> obvious recording state / lightweight level animation
-> large stop button
-> large play button
-> clear re-record/delete option
```

Do not auto-record on launch. The child should deliberately start recording.

Do not continuously capture ambient audio in the background.

Do not claim speech recognition, pronunciation scoring or semantic understanding merely because the Activity can record audio.

For the exact Activity microphone contract, processing behavior, storage/privacy rules and Parent-owned disable path, read:

```text
skills/greia-activity-authoring/MICROPHONE_RECORDING.md
```

## 5. Visual demonstration beats explanation

For a new mechanic, prefer showing one tiny example over explaining it in prose.

Examples:

- animate one puzzle piece sliding toward its matching silhouette;
- briefly pulse the three countable objects, then pulse the numeric choices;
- show a character tapping the relevant control once;
- ghost a drag path or show a hand/pointer motion;
- highlight the current playable region while dimming unrelated decoration.

Do not force a long tutorial sequence before play. Demonstrations should be short, interruptible where possible, and disappear once the child understands the loop.

## 6. Failure/retry must also be pre-reader friendly

A wrong answer must not produce only:

```text
"Incorrect. Try again."
```

Prefer:

```text
friendly wobble / bounce / shake
+ retry sound or character reaction
+ highlight/replay of the relevant clue
+ same task remains available
```

The child should understand both **that it did not work** and **what to try next** without reading an error message.

Never use punitive red error dialogs, desktop-style alerts, or text-heavy explanations as the primary retry loop.

## 7. Multilingual-ready from the start

Pre-reader design does not remove localization requirements.

Every spoken cue uses a stable semantic ID and localized wording/audio. Do not hard-code Italian sentences into gameplay.

Example:

```text
instruction.find_orca
instruction.choose_number
instruction.drag_match
```

If the Activity supports Italian and English, both must have a coherent spoken/visual path. A child must not lose the primary instruction because one locale lacks the voice asset.

When spoken language is part of the accepted interaction contract, missing reviewed audio coverage is an acceptance gap, not a reason to fall back silently to text-only instructions.

### 7.1 CAPITAL-letter presentation default (ADR 0034)

Children learn CAPITAL letters first, so Greia presents child-facing UI words in capitals by default: Activity names, Collection/Category labels, instructions, buttons, feedback and achievement copy.

- Localized strings comply automatically: `LocalizedResources.text()` applies the profile letter-case policy.
- Package-local literal strings must go through `greia_platform.child_text.display_text(...)`; do not hand-capitalize and do not leave child-facing literals mixed-case.
- A parent may choose normal text per child; the policy is presentation-only and must never feed gameplay, difficulty, permissions or stored data.
- Never case-transform child-authored content (for example what the child writes in the Writing Activity).

## 8. Reading-focused Activities are the exception, not a loophole

An Activity may intentionally teach reading, letters, spelling or words. That does not mean the **instructions about how to interact** may depend on reading.

Example:

Good reading Activity:

```text
spoken target word
+ large letter/word choices
+ visual demonstration of selection
```

Bad:

```text
"Read the word below and click the matching answer."
```

The learning content may be written language; the operating instructions must still be understandable to a pre-reader.

## 9. Acceptance: perform a no-reading pass

Before a new or materially redesigned Activity is accepted in the Simulator, explicitly perform a **NO-READING UX PASS**.

Review the Activity as if the child cannot read any instruction or button label.

Required questions:

```text
Can the first meaningful action be inferred without reading?
Are primary choices large and visually distinct?
Are icons/numbers/pictures sufficient where appropriate?
Is spoken instruction available when language is necessary?
If microphone recording is included, can start/stop/play/re-record be understood without reading?
Can a wrong action be understood and retried without reading?
Can the next round/start/replay action be found without reading?
Does completion/continue/replay make sense without reading prose?
```

If the answer to a core-flow question is no, the child-facing UX is not accepted even if unit tests, imports and Simulator launch all pass.

## 10. Completion evidence

For new Activities and substantial UI redesigns, record:

```text
PRE_READER_CORE_FLOW_PASS=yes/no
TEXT_REQUIRED_FOR_GAMEPLAY=yes/no
PRIMARY_INSTRUCTION_CHANNEL=visual/voice/combined
NO_READING_FIRST_ACTION_PASS=yes/no
NO_READING_RETRY_PASS=yes/no
NO_READING_COMPLETION_PASS=yes/no
MICROPHONE_RECORDING_USED=yes/no
MICROPHONE_RECORDING_NO_READING_FLOW_PASS=yes/no/not-applicable
SUPPORTED_LOCALES=
SPOKEN_INSTRUCTION_COVERAGE=
```

Required normal result:

```text
PRE_READER_CORE_FLOW_PASS=yes
TEXT_REQUIRED_FOR_GAMEPLAY=no
```

A technically functioning Activity that requires a 3–7-year-old child to read its instructions is a failed Greia Activity UX.