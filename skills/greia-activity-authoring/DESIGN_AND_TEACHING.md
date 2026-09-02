# Greia Activity Design and Teaching

**Status:** mandatory focused companion for every new Activity request and substantive gameplay redesign  
**Audience:** Activity designers, coding agents, reviewers

This document owns the **child experience, gameplay and teaching design pass that happens before implementation**.

A Greia Activity is not a technical demo with educational content added afterward. It is a small child experience designed for young children first, then implemented within Greia's platform contracts.

## 1. Start from the parent's request

Assume Activity-authoring work begins with a parent asking for one or more Activities.

Do not jump directly into files, manifests or Pygame.

First turn the request into a small design plan.

For a request containing several ideas, decide whether they are:

- several distinct Activities;
- several modes of one coherent Activity; or
- one Activity with progressive stages.

Prefer separate Activities when the child fantasy, core interaction or learning goal is materially different. Do not create a kitchen-sink Activity merely to reduce file count.

If the parent asks for several Activities, **plan the full set first** so they differ meaningfully and cover the intended learning/play space without accidental duplication. Then implement them in a sensible order.

Do not interrogate the parent for every design choice. Infer ordinary details from the request, existing Greia product language and target audience. Ask only when a missing fact genuinely changes the product direction; otherwise record the assumption and proceed.

## 2. Mandatory Activity brief before code

Before implementing a new Activity, write a compact brief for each Activity:

```text
ACTIVITY:
TARGET CHILD / AGE RANGE:
CHILD FANTASY:
PRIMARY PLAY LOOP:
PRIMARY LEARNING / DEVELOPMENT GOAL:
SECONDARY GOAL (optional):
WHAT THE CHILD DOES IN THE FIRST 5 SECONDS:
HOW THE CHILD KNOWS WHAT TO DO WITHOUT READING:
DIFFICULTY / SCAFFOLDING:
VARIATION / REPLAY VALUE:
SUCCESS FEEDBACK:
MISTAKE / RETRY FEEDBACK:
PRESENTER / CHARACTER:
SPOKEN INSTRUCTION PLAN:
PEDAGOGICAL-SOUND PLAN:
SUPPORTED LOCALES:
INPUT PLAN:
PROGRESS / COMPLETION PLAN:
VISUAL / AUDIO ASSET NEEDS:
TOOLS NEEDED DURING AUTHORING:
```

This is a design checkpoint, not paperwork. If the brief cannot explain the child's first action, play loop and learning purpose in a few clear lines, the Activity is not ready to code.

## 3. Design for a child who cannot read

Greia's normal operating assumption is that the child **cannot read instructions**.

The child must be able to:

- understand the immediate goal;
- perform the primary action;
- notice cause and effect;
- recover from mistakes;
- continue/replay;
- understand completion;

without reading prose or button labels.

Use this communication order:

```text
scene/layout makes the action obvious
-> visual demonstration / motion / highlight when useful
-> large picture, shape, icon or number
-> short spoken instruction when language is needed
-> immediate visual/audio feedback
-> optional caption/text as secondary support
```

A spoken sentence does not excuse a confusing screen, and a beautiful screen does not excuse a required instruction being available only as text.

For the exact pre-reader acceptance rules, load:

```text
skills/greia-activity-authoring/PRE_READER_UX.md
```

## 4. Required commands must be spoken when visuals alone are insufficient

If the child needs language to know what to do, that instruction is part of the gameplay contract and **must be spoken**.

Examples:

```text
"Trova la lettera S."
"Metti tre mele nel cestino."
"Quale animale fa questo verso?"
```

Do not ship these as text-only instructions.

Every required spoken instruction must:

- have a stable semantic cue ID;
- exist in every shipped locale for which that interaction is supported;
- use the correct Greia speaker/speech kind;
- be short and contain one idea at a time;
- be repeatable through an obvious interaction when repetition is useful;
- be human-reviewed before acceptance.

Do not narrate every tap. Use speech to orient, instruct, hint and reinforce where it adds value; leave room for quiet play.

Greia has a canonical authoring-time Voice Production Engine. There is no normal child-runtime TTS for these lines. The top-level Activity skill must always know this architecture; load `VOICE_GENERATION.md` when actual speech planning/production details are needed.

## 5. Teaching should happen through play

Do not paste a worksheet or quiz onto a cute background.

Prefer a learning loop in which the educational idea is the thing the child **does**.

Examples:

```text
counting
    child touches/moves real visible objects one by one
    rather than reading "How many?" repeatedly

shape matching
    child physically fits/moves shapes into meaningful silhouettes
    rather than selecting text answers

phonics
    child hears an authoritative target sound and manipulates/chooses its symbol
    rather than relying on explanatory prose

sequencing
    child arranges visible steps/objects and immediately sees the result
    rather than answering an abstract multiple-choice question
```

A good learning mechanic has observable cause and effect.

## 6. Scaffold, then let the child act

A useful default progression is:

```text
show one tiny example
-> guided first attempt
-> independent repetition
-> gentle variation
-> slightly harder variation
-> celebration / natural continuation
```

Do not front-load a long tutorial.

Change one important difficulty dimension at a time. Examples:

- more objects;
- closer distractors;
- less visual hinting;
- longer sequence;
- wider choice set;
- simple combination of already-learned mechanics.

Avoid difficulty created by tiny controls, time pressure, dense screens, reading requirements or deliberately confusing presentation.

## 7. Repetition needs variation

Young children benefit from repetition, but identical rounds become mechanical quickly.

Keep the learning truth stable while varying presentation:

- object sets;
- positions;
- scene details;
- challenge order;
- characters/reactions;
- small safe surprises;
- controlled difficulty parameters.

Randomness must be bounded and authored. It must not accidentally generate impossible, misleading or developmentally inappropriate rounds.

## 8. Feedback is immediate, warm and informative

Correct actions should produce clear cause and effect quickly.

Use combinations such as:

- object movement/change;
- character expression/motion;
- concise sound;
- short shared praise/celebration when useful;
- visible progress in the current scene.

Wrong actions are not punishment.

Prefer:

```text
friendly wobble / bounce / funny miss
+ relevant clue is highlighted/replayed
+ task remains available immediately
+ short retry encouragement when useful
```

over red error dialogs, losing lives, long explanations or shame language.

The feedback should help answer: **what happened, and what can I try now?**

## 9. Match cognitive and motor load to the target child

For younger children especially:

- use few simultaneous choices;
- use large targets;
- keep gestures simple;
- avoid precision dragging unless the mechanic really needs it;
- keep one dominant goal visible;
- use short interaction cycles;
- avoid nested menus/settings in play;
- avoid requiring working-memory chains before the child understands the base interaction.

An Activity can become richer through stages without making every screen busy.

## 10. Presenter and character use is part of design

Every new Activity must deliberately choose a lead presenter/character or explicitly choose none.

A presenter should do useful child-facing work, for example:

- welcome/orient briefly;
- demonstrate the mechanic;
- speak a required instruction;
- give a contextual hint;
- react to progress;
- share an optional curiosity fact;
- celebrate completion.

Do not use a canonical character as decorative wallpaper while an unrelated anonymous voice gives the actual instructions.

For detailed presenter/curiosity design load:

```text
skills/greia-activity-authoring/PRESENTERS_AND_CURIOSITY.md
```

## 11. Speech-purpose decisions happen during design

For each planned spoken cue decide its semantic purpose before generating anything:

```text
character_dialogue
    presenter instructions, welcome, contextual hints, narration, facts

shared_character_utterance
    generic praise, retry, progress, ready/go, celebration when the accepted
    runtime catalogue actually exposes the required family

pedagogical_speech
    the sound itself is educational truth: letter name/sound, syllable, phonics,
    spelling/pronunciation target

dani_system_speech
    Dani's intentionally robotic presenter/logic speech
```

Do not classify a whole Activity as pedagogical speech just because it teaches something.

A Leo welcome is `character_dialogue`. Generic praise should normally use a shared utterance when available. A letter/syllable whose exact pronunciation is being taught is `pedagogical_speech`.

The accepted shared asset set is v0.2 (180 reactions + 12 introductions), but runtime resolver availability is a separate implementation fact. Check the current resolver before assuming a family is callable from an Activity.

For production mechanics load:

```text
skills/greia-activity-authoring/VOICE_GENERATION.md
skills/greia-voice-production/SKILL.md
```

## 12. Visual quality serves the play loop

The child should see a coherent little world, not programmer rectangles plus labels.

Before implementation identify:

- dominant scene/fantasy;
- important entities;
- interactive vs decorative elements;
- character presence;
- feedback/animation needs;
- reusable Greia assets versus Activity-specific art.

Art should improve comprehension and delight without making interactive targets visually ambiguous.

Load `skills/greia-visual-authoring/SKILL.md` when actual visual assets need to be created or adapted.

## 13. Progress and rewards should reinforce mastery, not grind

Decide what completion means for the Activity.

Good progress often comes from:

- discovering new content;
- completing a small set;
- mastering a progressively harder loop;
- creating something;
- reaching natural milestones.

Do not add points, streaks, timers or reward spam merely because games often have them.

Activities report facts/events; Greia owns global Stars/achievements/progression authority.

Load `ACHIEVEMENTS.md` only when progress/events/rewards are actually part of the Activity.

## 14. Multi-Activity requests need a set-level plan

When a parent asks for several Activities, first make a compact matrix:

```text
Activity | child fantasy | primary learning goal | core mechanic | presenter | age/challenge | why it is distinct
```

Check the set for:

- duplicated mechanics wearing different art;
- all Activities teaching in the same quiz format;
- missing variety between exploratory, creative, puzzle, action and calm play where appropriate;
- inconsistent input complexity for the intended child;
- repeated presenter use where another character would fit better;
- accidental gaps in the parent's requested learning scope.

Then implement in a deliberate sequence, validating each Activity rather than building a large broken batch before the first real simulator run.

## 15. Design acceptance before implementation

Before code starts, confirm:

```text
PARENT_REQUEST_DECOMPOSED=yes
ACTIVITY_SET_PLAN_COMPLETE=yes/not-applicable
PRIMARY_PLAY_LOOP_CLEAR=yes
PRIMARY_LEARNING_GOAL_CLEAR=yes
FIRST_ACTION_CLEAR_WITHOUT_READING=yes
REQUIRED_LANGUAGE_INSTRUCTIONS_IDENTIFIED=yes
SPOKEN_CUE_PLAN_DEFINED=yes
PRESENTER_DECISION_DEFINED=yes
DIFFICULTY_SCAFFOLD_DEFINED=yes
RETRY_FEEDBACK_DEFINED=yes
VARIATION_DEFINED=yes
SUPPORTED_LOCALES_DEFINED=yes
```

If the core child flow is still vague, continue designing. Do not compensate by writing more infrastructure.