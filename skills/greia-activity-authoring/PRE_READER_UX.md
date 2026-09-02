# Greia Activity Pre-Reader UX

**Status:** mandatory focused companion for every new Activity and substantive child-facing redesign  
**Audience:** Activity designers, coding agents, reviewers

Greia targets young children, including children who cannot read yet.

> **A child must be able to understand what to do, act, recover from mistakes and continue without reading written instructions or button labels.**

This is a product requirement, not an accessibility enhancement added later.

## 1. Communication order

Design the experience in this order:

```text
clear scene hierarchy
-> obvious interactive target
-> visual demonstration / movement / highlighting where useful
-> big picture, shape, icon or number
-> short spoken cue when language is needed
-> immediate visual/audio feedback
-> optional written caption as secondary support
```

Voice does not rescue a confusing screen. Visual clarity does not excuse a required language instruction existing only as text.

## 2. The first five seconds matter

On the first usable frame, the child should quickly understand a reasonable next action.

Prefer:

- one visually dominant current goal;
- few simultaneous choices;
- large targets;
- strong separation between interactive and decorative elements;
- characters looking/pointing/moving toward the relevant action;
- short visual demonstrations rather than tutorial prose;
- familiar symbols and concrete objects.

Avoid:

- adult-style menus;
- dense toolbars;
- long intro screens;
- hidden essential actions;
- instructions that say what to do while the screen itself gives no clue.

A useful test is to mute the speakers temporarily: the child should still understand the *kind* of interaction even when exact language detail needs speech.

## 3. Required language commands must be spoken

If exact language is needed to know the required action, provide reviewed spoken audio.

Examples:

```text
"Trova la lettera S."
"Metti tre mele nel cestino."
"Quale animale fa questo verso?"
```

These may have captions, but captions are secondary.

For every required spoken command:

- use a stable semantic cue ID;
- cover every shipped locale for that interaction;
- keep it short and one-idea-at-a-time;
- use the correct Greia presenter/speech route;
- play it at the right moment;
- provide an obvious way to hear it again when repetition is useful;
- human-review the final audio.

If required speech is missing in a shipped locale, that locale's pre-reader flow is incomplete.

Load:

```text
skills/greia-activity-authoring/VOICE_GENERATION.md
```

for the canonical prerecorded speech system and semantic routing.

Do not narrate every child action. A good rhythm is:

```text
brief cue
-> child acts/explores
-> concise feedback/hint when needed
-> quiet play
```

## 4. Show the mechanic instead of explaining it

For a new mechanic, prefer one tiny demonstration:

- one puzzle piece glides toward its silhouette;
- a hand/pointer taps one countable object;
- a character briefly drags an item to the right place;
- a target pulses while irrelevant decoration stays quiet;
- an example sequence runs once and stops.

Demonstrations should be short and should not force the child through a long tutorial before play.

## 5. Use large, forgiving interaction targets

Normal primary child controls should be large and forgiving.

Working guidance:

```text
primary targets: normally >=64×64 logical px, preferably larger
important entities: large enough to identify immediately
numbers/learning symbols: visually dominant when they are the content
```

Do not create difficulty through precision clicking, tiny arrows or tightly packed choices.

Use semantic Greia/system assets where Greia owns the control. Do not imitate protected Home/Back inside the Activity.

## 6. Wrong actions must be understandable without text

Do not make the only feedback:

```text
"Incorrect. Try again."
```

Prefer:

```text
friendly wobble/bounce/funny miss
+ replay/highlight the relevant clue
+ optional short retry encouragement
+ task remains immediately available
```

The child should understand:

1. that the action did not solve the task;
2. where to look/what to try next.

Avoid punishment, shame, scary error screens and long delays after mistakes.

Italian praise/retry copy must avoid child-gender agreement such as `bravo/brava` or `bravissimo/bravissima`. Prefer neutral expressions such as `Ottimo lavoro!`, `Ben fatto!`, `Esatto!`, `Evviva!`, `Che meraviglia!`.

## 7. Continue, replay and completion are part of pre-reader UX

Do not design a wonderful play loop that ends in a text-heavy result panel.

At completion, the child must understand visually how to:

- continue;
- replay;
- choose the next obvious action;
- return through Greia Home when desired.

Use clear scene transitions, animation and large semantic controls. Text labels can reinforce but not carry the interaction alone.

## 8. Reading-focused Activities are not exempt

An Activity may intentionally teach letters, words or reading.

The *learning material* may therefore be written language.

The operating instruction must still be pre-reader accessible.

Good:

```text
spoken target sound/word
+ big visual letter/word choices
+ demonstration of how to select
```

Bad:

```text
"Read the word below and click the matching answer."
```

when reading that sentence is necessary to know how to play.

## 9. Child voice recording is optional, not speech recognition

Where expressive voice adds real value, Greia offers platform-owned `audio.basic` capture.

Good uses include:

- narrating a drawing;
- puppet/story voice;
- animal sound imitation;
- recording/replaying a phrase;
- simple creative radio/play acting.

A pre-reader recording flow should be visually obvious:

```text
large mic
-> clear recording state
-> large stop
-> large play
-> clear redo/delete
```

Do not auto-record on launch, continuously capture ambient audio, or claim speech recognition/pronunciation scoring just because recording exists.

Load `MICROPHONE_RECORDING.md` only when the Activity actually records the child.

## 10. Multilingual pre-reader rule

Visual communication should stay semantically stable across locales.

Required spoken cues use stable IDs and localized reviewed audio.

Do not silently degrade a required spoken instruction to text-only because one locale's audio is missing.

Child-facing display text goes through Greia localization/letter-case presentation. Do not hand-uppercase strings; never transform child-authored content.

## 11. Perform two different pre-reader checks

### Mechanical/headless check

During implementation, use `SIMULATOR_WORKFLOW.md` and the headless Simulator to prove the Activity launches, responds and returns cleanly.

This cannot decide subjective child comprehension.

### Final human GUI check

At the end, launch the normal GUI Simulator and present the exact final Activity to the user/reviewer.

Review it as if the child cannot read any text.

Required questions:

```text
Can the first meaningful action be inferred without reading?
Are primary targets large and visually distinct?
If exact language is required, is the command spoken?
Can required speech be repeated where useful?
Can a wrong action be understood and retried without prose?
Can completion/continue/replay be understood without prose?
Does the gameplay remain calm enough to follow?
```

If a core answer is no, the child-facing UX is not accepted even if every unit test passes.

## 12. Completion record

For every new Activity/substantive child-flow redesign record:

```text
PRE_READER_CORE_FLOW_PASS=yes/no
TEXT_REQUIRED_FOR_GAMEPLAY=yes/no
FIRST_ACTION_NO_READING_PASS=yes/no
REQUIRED_LANGUAGE_COMMANDS=
REQUIRED_SPOKEN_COVERAGE=
SPOKEN_REPLAY_AVAILABLE=yes/no/not-applicable
RETRY_NO_READING_PASS=yes/no
COMPLETION_NO_READING_PASS=yes/no
PRIMARY_INSTRUCTION_CHANNEL=visual/voice/combined
GUI_USER_PRE_READER_REVIEW=PASS/FAIL/PENDING
```

Normal accepted result:

```text
PRE_READER_CORE_FLOW_PASS=yes
TEXT_REQUIRED_FOR_GAMEPLAY=no
GUI_USER_PRE_READER_REVIEW=PASS
```

A technically functioning Activity that requires a young child to read its instructions is a failed Greia Activity UX.