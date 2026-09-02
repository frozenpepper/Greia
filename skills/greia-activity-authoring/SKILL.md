---
name: greia-activity-authoring
description: Design and build one or more Greia Activities from a parent's request. Starts with child/play/teaching design, then implementation, prerecorded speech, iterative headless Simulator checks and final GUI user review.
---

# Greia Activity Authoring

**Status:** living Activity authoring contract  
**Reviewed:** 2026-09-02

This skill assumes the normal entry point is:

> **A parent asks for one or more Activities.**

The job is not to jump immediately into Pygame or manifests. The job is to turn that request into a coherent child experience, plan it, implement it cleanly, and prove the final result through Greia.

## 1. The authoring loop

For every new Activity request, follow this order:

```text
1. understand the parent's intent
2. split the request into one or more coherent Activity concepts
3. design the child experience and teaching/play loop
4. design pre-reader communication and spoken cues
5. choose presenter/character, locales, input and progression
6. plan implementation and Activity-local authoring tools
7. implement in small vertical slices
8. use the headless Greia Simulator repeatedly while building
9. produce/review required static voice/assets
10. rerun final headless integration on the exact final state
11. launch the GUI Greia Simulator for user visual/interaction review
12. only then call the Activity accepted
```

Do not invert this into “build first, make it child-friendly later.”

## 2. Mandatory context for a new Activity

Before coding a new Activity or materially redesigning its gameplay, load:

```text
skills/greia-activity-authoring/DESIGN_AND_TEACHING.md
skills/greia-activity-authoring/PRE_READER_UX.md
skills/greia-activity-authoring/ENGINEERING.md
skills/greia-activity-authoring/SIMULATOR_WORKFLOW.md
```

These four are the normal creation core.

The top-level skill already carries the essential speech architecture below. Load the deeper voice companion when the Activity needs actual spoken cue design/production:

```text
skills/greia-activity-authoring/VOICE_GENERATION.md
skills/greia-voice-production/SKILL.md
```

Load other focused companions only when their subject is actually part of the Activity:

```text
PRESENTERS_AND_CURIOSITY.md  canonical presenter/facts design
MICROPHONE_RECORDING.md      child microphone recording
ACHIEVEMENTS.md              progress/events/Stars/achievements
DISCOVERY.md                 age/difficulty/Collection/discovery metadata
LAUNCHER_SPOKEN_LABELS.md    launcher title speech details
TERMINAL_RENDERING.md        completion/results/replay presentation
REFACTORING.md               substantive existing-Activity refactor
LAUNCH_ACCEPTANCE.md         detailed final launch evidence contract
```

For actual visual asset creation/adaptation load:

```text
skills/greia-visual-authoring/SKILL.md
```

Do **not** load every companion merely because it exists.

## 3. First action: decompose the parent's request

When a parent asks for several Activities, plan the set before coding.

Decide whether the request describes:

- several distinct Activities;
- one Activity with progressive stages;
- or one coherent Activity with multiple modes.

Prefer distinct Activities when the child fantasy, primary learning goal or core interaction is materially different.

For a multi-Activity request, make a compact matrix:

```text
Activity | child fantasy | learning/development goal | core mechanic | presenter | target age/challenge | why distinct
```

Avoid five Activities that are the same multiple-choice quiz with different nouns.

Do not ask the parent to specify ordinary implementation details the skill can infer. Ask only when a missing decision genuinely changes the product direction; otherwise record a sensible assumption and proceed.

## 4. No code before the child loop is clear

Every new Activity gets the compact brief defined in `DESIGN_AND_TEACHING.md` before implementation.

At minimum the agent must know:

```text
what fantasy/world the child is entering
what the child actually does repeatedly
what the child learns/practices/creates
what the first meaningful action is
how a non-reader knows what to do
how difficulty/scaffolding changes
what makes repetition varied and fun
what happens on success
what happens on a mistake
which presenter/character is involved
which commands must be spoken
which locales are supported
how completion/progress works
```

If those answers are vague, continue designing instead of writing infrastructure.

## 5. The child cannot be assumed to read

This is a hard Greia design rule.

A child must not need written instructions, button labels or explanatory prose to operate the normal Activity flow.

Use:

```text
obvious scene composition
+ large interactive targets
+ pictures / shapes / numbers / icons
+ short visual demonstrations and motion cues
+ spoken instruction when language is necessary
+ immediate visual/audio feedback
```

Text is secondary support.

Even reading/phonics Activities are not exempt: the *learning content* may be letters/words, but the instructions for how to play must still be understandable to a pre-reader.

For new Activities and substantive child-facing redesigns, the no-reading pass in `PRE_READER_UX.md` is mandatory.

## 6. Required commands are spoken

If a child needs language to understand a required action and the meaning cannot be communicated reliably through visuals alone, that instruction must be spoken.

Do not ship:

```text
"Find the blue whale"
"Put three apples in the basket"
"Choose the letter S"
```

as text-only commands.

Required spoken cues must be:

- short;
- one idea at a time;
- localized for every shipped locale of that interaction;
- backed by stable semantic cue IDs;
- repeatable when repetition is useful;
- produced through Greia's canonical prerecorded speech system;
- human-reviewed before final acceptance.

Do not narrate every tap. Speech should orient, instruct, hint and reinforce; the child still needs room for quiet play.

## 7. Greia already has a voice-production system

New Activity speech is **authoring-time prerecorded audio**.

Canonical production entry point:

```text
tools/greia_voice.py
```

The child device does not run Chatterbox/Whisper or ordinary runtime TTS for Activity narration.

Activity code and Activity-specific tools must never implement their own Chatterbox, MLX, Whisper, native `say`, FFmpeg trimming or model-routing stack.

Speech kinds are semantic:

```text
character_dialogue
    presenter welcome/instructions/hints/narration/facts

shared_character_utterance
    generic praise/retry/progress/ready/celebration when the accepted runtime
    resolver exposes the required family

pedagogical_speech
    the sound itself is educational truth: letter name/sound, syllable,
    phonics, spelling/pronunciation target

dani_system_speech
    Dani's deliberately robotic presenter/logic speech
```

Do not classify all speech in an educational Activity as `pedagogical_speech`.

Examples:

```text
Leo: "Ciao! Scopriamo le lettere!"     -> character_dialogue
Leo: "Quasi! Proviamo ancora!"         -> shared utterance when available, otherwise character dialogue
"A" / "MA" taught as exact sound       -> pedagogical_speech
Dani: "Metti tre mele nel cestino."    -> dani_system_speech
```

The accepted shared v0.2 asset set contains 180 shared reactions + 12 character introductions. Runtime resolver availability is separate; inspect current source before assuming a shared family is callable.

When generating/replacing speech, load `VOICE_GENERATION.md` and `skills/greia-voice-production/SKILL.md`.

## 8. Teaching happens through the play mechanic

Do not build a cute wrapper around a worksheet.

Prefer learning through visible action and cause/effect:

```text
count visible objects by touching/moving them
fit shapes into meaningful silhouettes
hear a target phoneme and manipulate/choose its symbol
arrange a sequence and watch the result happen
build/experiment and see the physical consequence
```

A useful default progression is:

```text
show one tiny example
-> guided attempt
-> independent repetition
-> gentle variation
-> slightly harder variation
-> natural celebration/continuation
```

Increase challenge through the learning mechanic, not through tiny controls, confusing layouts, excessive reading or punitive time pressure.

Wrong answers should produce friendly, informative retry feedback, not punishment.

## 9. Technical implementation standard

Once the child design is coherent, implement cleanly.

For first-party Python Activities:

- keep `main.py` a thin composition/bootstrap root;
- use cohesive modules/classes around real state and responsibilities;
- prefer composition over deep inheritance;
- use polymorphism only at genuine variation points;
- reuse Greia platform services/primitives instead of cloning platform infrastructure;
- keep Activity code display/input-backend neutral;
- never implement the real Greia Home/Back inside the Activity;
- preserve both Greia script-launch and repository/package import contexts;
- keep caches bounded and rendering appropriate for the Acer-class performance floor;
- use platform storage/events/progression/permissions rather than private substitutes.

Load `ENGINEERING.md` for the detailed implementation rules before coding.

## 10. Project-specific tooling stays with the project

Do not throw one-off Activity authoring/generation/migration scripts into repository root `tools/`.

For an Activity, project-specific tooling is created under:

```text
activities/<activity_id_or_dir>/tools/
```

Examples:

```text
activities/my_activity/tools/generate_audio_requests.py
activities/my_activity/tools/build_local_assets.py
activities/my_activity/tools/migrate_content.py
```

Rules:

1. Put the tool in the Activity's `tools/` directory **from the start**.
2. Keep runtime code out of `tools/`; if the child runtime needs it, it is Activity implementation, not authoring tooling.
3. Root `tools/` is reserved for genuinely repository-wide/platform tooling used across projects.
4. Before final Activity/package acceptance, remove temporary/obsolete authoring tools and generated scratch files.
5. Because the Activity directory is also the package root, do not accidentally ship one-off development machinery. If a local tool has served its purpose, delete it before final package validation.
6. Promote a tool to root `tools/` only when it has become a genuinely reusable Greia-wide facility with a stable contract.

The same principle applies to other Greia subprojects: project-specific tooling belongs in that project's own `tools/` area and is cleaned up when no longer needed.

## 11. Implement in vertical slices and use the headless Simulator early

The headless Greia Simulator is the normal mechanical integration loop.

Do not wait until the Activity is “finished.”

Typical rhythm:

```text
minimal valid skeleton
-> headless Simulator

first real child interaction
-> focused tests + headless Simulator

major refactor/import/resource change
-> focused tests + headless Simulator

completion/restart added
-> headless Simulator

final runtime edit
-> final headless Simulator again
```

Canonical runner:

```bash
PYTHONPATH=src python3 tools/headless_greia_simulator.py \
  --activity-dir activities/<activity_dir> \
  --workspace-dir /tmp/greia-sim-<activity_dir> \
  --locale it \
  --viewport 1024x600 \
  --survival-seconds 12 \
  --screenshot-prefix /tmp/greia-<activity_dir>-it
```

Use `--press-key` or `--click-x/--click-y` when a simple meaningful interaction can be exercised mechanically.

For localized/spoken behavior, run the relevant shipped locales.

The detailed workflow is in `SIMULATOR_WORKFLOW.md`.

## 12. Headless PASS is not child-experience acceptance

Headless Simulator checks mechanical integration. It cannot honestly decide whether:

- the game is fun;
- the scene is visually coherent;
- a toddler understands the first action;
- the challenge teaches what it intends;
- controls are too small/confusing;
- character/audio timing feels right;
- the Activity is pleasant at 1024×600.

Therefore a new Activity is not complete after headless PASS.

## 13. Final step: launch the GUI Simulator for user review

After the final runtime state passes headless integration, launch:

```bash
python3 tools/greia_simulator.py \
  --state-dir ~/.greia-simulator-review-<activity_dir>
```

Present that exact final Activity to the user/reviewer.

The user review covers:

- first-action clarity with no reading;
- gameplay/teaching quality;
- visual composition and target sizes;
- presenter/character fit;
- spoken command timing/coverage;
- retry/completion clarity;
- responsiveness/layout where relevant;
- protected Home and clean return.

If the environment cannot launch/present the GUI Simulator, report:

```text
SOURCE-VERIFIED / HEADLESS-SIMULATOR-PASS / GUI-REVIEW-PENDING
```

Do not self-promote that to fully accepted.

Any runtime-relevant edit after final headless/GUI evidence invalidates that evidence and requires rerunning the applicable final checks.

## 14. Conditional companions

Load these only when relevant:

### Presenter / curiosity / facts

```text
PRESENTERS_AND_CURIOSITY.md
```

### Actual speech production or replacement

```text
VOICE_GENERATION.md
skills/greia-voice-production/SKILL.md
```

### Microphone / child recording

```text
MICROPHONE_RECORDING.md
```

### Progress / events / Stars / achievements

```text
ACHIEVEMENTS.md
```

### Manifest audience / Collection / age / challenge discovery

```text
DISCOVERY.md
```

### Completion / Continue / Replay UI

```text
TERMINAL_RENDERING.md
```

### Packaging / `.greiaactivity`

Read the current package authority:

```text
docs/architecture/GREIA_ACTIVITY_PACKAGE_FORMAT.md
src/greia_platform/activity_packages.py
src/greia_platform/activity_package_format.py
```

### Refactoring an existing Activity

```text
REFACTORING.md
```

## 15. Definition of done for a new Activity

A new first-party Activity is not done until all applicable items are true:

```text
parent request decomposed
child/activity brief complete
play loop coherent
learning/development goal expressed through play
pre-reader core flow passes
required commands have reviewed spoken coverage
presenter decision deliberate
locales complete
technical implementation follows Greia runtime/platform contracts
Activity-local tooling cleaned up
focused tests green
final headless Simulator green on exact runtime state
protected Home/return green
GUI Simulator launched on exact final state
user visual/interaction review completed
```

If actual voice production is pending, GUI review is pending, or final Simulator evidence is stale, say so explicitly instead of calling the Activity complete.