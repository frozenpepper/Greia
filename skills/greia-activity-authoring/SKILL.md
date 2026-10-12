---
name: greia-activity-authoring
description: Design and build one or more Greia Activities from a parent's request. Child/play/teaching design comes first, followed by clean implementation, prerecorded speech, repeated headless Simulator integration and final GUI user review.
---

# Greia Activity Authoring

**Status:** living Activity-authoring contract  
**Reviewed:** 2026-09-03

The normal entry point is simple:

> **A parent asks for one or more Activities.**

Act as a small Activity designer/producer, not merely a coder. Turn the request into coherent child experiences, plan the set, implement each Activity cleanly, and prove the final result through Greia.

## 1. Mandatory authoring loop

For every new Activity request:

```text
parent request
-> decompose into one or more coherent Activity concepts
-> design child fantasy + play/teaching loop
-> choose defensible minimum age + challenge model
-> design no-reading communication + required speech
-> choose presenter, feedback/audio sequencing and progression semantics
-> plan implementation + Activity-local authoring tools
-> implement one small vertical slice
-> headless Greia Simulator
-> iterate with focused tests + headless Simulator
-> produce/review required prerecorded voice/assets
-> final exact-state headless Simulator
-> launch GUI Greia Simulator
-> user reviews actual child experience
-> accepted only after applicable evidence is complete
```

Do not build first and try to make it child-friendly afterward.

## 2. Creation core — load these every time

Before coding a new first-party Activity or materially redesigning gameplay, load:

```text
DESIGN_AND_TEACHING.md
PRE_READER_UX.md
DISCOVERY.md
FEEDBACK_ORCHESTRATION.md
ACHIEVEMENTS.md
ENGINEERING.md
SIMULATOR_WORKFLOW.md
```

These seven companions are the normal creation core:

- `DESIGN_AND_TEACHING.md` — parent-request decomposition, gameplay and learning design;
- `PRE_READER_UX.md` — operation without reading and spoken-command requirements;
- `DISCOVERY.md` — mandatory minimum age, difficulty and Collection/discovery metadata;
- `FEEDBACK_ORCHESTRATION.md` — audio/event conflicts, shared reactions and terminal transitions;
- `ACHIEVEMENTS.md` — local score/progress/events versus Greia-owned rewards;
- `ENGINEERING.md` — clean architecture, runtime rules and performance;
- `SIMULATOR_WORKFLOW.md` — repeated headless integration and final GUI review.

Do not load every specialist companion merely because it exists.

## 3. First action: decompose the parent's request

If several Activities are requested, plan the set before coding.

Decide whether the request is best represented as:

- several distinct Activities;
- one Activity with progressive stages;
- or one coherent Activity with multiple modes.

Prefer separate Activities when the child fantasy, primary learning goal or core interaction is materially different.

For multiple Activities, first make a compact matrix:

```text
Activity | child fantasy | learning/development goal | core mechanic | presenter | age/challenge | why distinct
```

Avoid producing several copies of the same quiz with different nouns/art.

Infer ordinary design details from the request and Greia's existing product language. Ask only when a missing choice genuinely changes product direction.

## 4. No code before the child loop is clear

Every Activity gets the compact brief in `DESIGN_AND_TEACHING.md` first.

At minimum know:

```text
what world/fantasy the child enters
what the child repeatedly does
what the child learns/practices/creates
what happens in the first five seconds
how a non-reader knows what to do
recommended_age_min and why it is defensible
how challenge/scaffolding changes
what keeps repetition varied
what success and mistakes look/sound like
which presenter/character is used
which commands require spoken language
which locales ship
how completion/progress works
what score/events exist, if any
what happens on the final item/final answer
which cue wins when speech/SFX/celebration collide
```

If these are vague, keep designing instead of writing infrastructure.

## 5. Design for children who cannot read instructions

Normal Greia operation must not depend on reading button labels, prose or instructions.

Prefer:

```text
obvious scene composition
+ large child-sized targets
+ pictures / shapes / numbers / icons
+ short visual demonstration or motion cue
+ spoken instruction when language is necessary
+ immediate visual/audio cause-and-effect
```

Text is secondary support.

Even a reading/phonics Activity is not exempt: letters/words may be learning content, but the instruction for how to play must still be understandable to a pre-reader.

### Required language commands are spoken

If exact language is needed to know what to do, it must be spoken.

Examples:

```text
“Trova la lettera S.”
“Metti tre mele nel cestino.”
“Quale animale fa questo verso?”
```

Do not ship these as text-only commands.

Required speech is short, localized, semantically identified, repeatable when useful, produced through Greia's prerecorded voice system and human-reviewed before final acceptance.

## 6. Age metadata is part of design

Every first-party Activity must declare a defensible:

```toml
[education]
recommended_age_min = N
```

Choose the youngest ordinary child for whom the **actual shipped interaction** is appropriate considering concepts, language/reading assumptions, working-memory load and motor demands.

Do not copy `difficulty` into age. Difficulty and developmental suitability are independent.

`recommended_age_max` is optional. Open-ended creative/sensory/imaginative Activities should not receive fake upper limits merely for symmetry.

Parent restrictive age presets depend on truthful metadata. See `DISCOVERY.md` for exact semantics, including unknown-age compatible packages and explicit Parent overrides.

## 7. Teaching happens through play

Do not put a worksheet on a cute background.

Prefer mechanics where the educational idea is what the child actually does:

```text
count visible objects by touching/moving them
fit shapes into meaningful silhouettes
hear a phoneme and manipulate/choose its symbol
arrange a sequence and watch the consequence
build/experiment and see cause-and-effect
```

Useful default progression:

```text
tiny demonstration
-> guided first attempt
-> independent repetition
-> gentle variation
-> slightly harder variation
-> natural completion/continuation
```

Increase challenge through the learning mechanic, not through tiny targets, dense screens, reading requirements, punitive timers or confusing layout.

Mistakes should reorient and encourage, not shame or punish.

### Four-language rollout (2026-10-12)

Current Greia OS selectable locales: **English and Italian**.
Spanish and French are translation/voice targets but not globally
selectable. The accepted cross-surface plan is
`docs/plans/2026-10-12_GREIA_FOUR_LANGUAGE_ROLLOUT/PLAN.md`;
the exact local recording work order is the sibling
`LOCAL_AGENT_VOICE_PRODUCTION.md`. All built-in Activity semantic
UI/lesson-language separation, locale bundle keys, launcher titles,
caption/audio mappings and human-listened speech must pass before
ES/FR are promoted. Never mark a locale supported merely because
you copied `en.json` or created placeholder WAV paths. Preserve
current English/Italian recording assets and repair only identified
missing/incorrect cues.

## 8. Greia already owns voice production

Normal Activity narration/instructions are **authoring-time prerecorded audio**.

Canonical production entry point:

```text
tools/greia_voice.py
```

The child device does not run Chatterbox/Whisper or normal narration TTS.

Activity code and Activity-local tooling must not create a parallel Chatterbox/MLX/Whisper/native-TTS/FFmpeg routing stack.

Speech kinds are semantic:

```text
character_dialogue
    presenter welcome, instruction, hint, narration, fact

shared_character_utterance
    generic ready/praise/retry/progress/celebration when the shared resolver exposes it

pedagogical_speech
    the exact sound itself is educational truth: letter/syllable/phonics/pronunciation

dani_system_speech
    Dani's intentionally robotic presenter/logic speech
```

Do not classify all speech in an educational Activity as `pedagogical_speech`.

When actual speech needs producing/replacing, load:

```text
VOICE_GENERATION.md
skills/greia-voice-production/SKILL.md
```

### Shared character speech

Accepted shared v0.2 assets live at:

```text
assets/audio/characters/shared/v0.2/
```

Current accepted set:

```text
180 shared reactions
12 canonical character introductions
```

Documented generic families include:

```text
ready.go
praise.general
celebrate.success
encourage.retry
encourage.progress
```

Reuse shared reactions instead of generating duplicate generic praise when the current runtime resolver exposes the needed family.

Do not assume a generic greeting family exists, and do not copy the shared WAV catalogue into individual Activities.

## 9. Resolve semantic feedback before playing sound

One child action can simultaneously mean:

```text
ordinary item collected
teaching target completed
score changed
milestone emitted
round finished
victory reached
```

These events must not independently fire competing sounds.

Classic failure:

```text
collect final item
-> ordinary collect SFX starts
-> final-word speech starts
-> victory fanfare replaces it
-> character congratulations overlaps everything
```

Instead resolve the state transition first, then deliberately choose one of:

```text
SEQUENCE
SUPPRESS
REPLACE
INTERRUPT
COALESCE
```

The final item/final answer/final piece is normally a **terminal transition**, not merely an ordinary success plus another victory callback.

Protect pedagogical/required speech, keep queues bounded, and emit completion/score/milestone facts once.

`FEEDBACK_ORCHESTRATION.md` owns the detailed rules.

## 10. Score, Stars, medals and achievements

Every Activity must explicitly decide its progression relationship, even if the correct answer is `none`.

Keep these separate:

```text
local Activity score/progress
    Activity-owned presentation/state where appropriate

normalized completion/milestone/score facts
    emitted by Activity through Greia contracts

Greia Stars / medals / trophies / global progression
    platform-owned policy and ledger
```

Activities report facts. They do not directly grant or mutate global rewards.

Do not add streaks, points or reward spam simply because games often have them.

`ACHIEVEMENTS.md` owns the exact event/reward contract.

## 11. Technical implementation standard

For first-party Python Activities:

- keep `main.py` a thin bootstrap/composition root;
- use cohesive modules/classes around real responsibilities;
- prefer composition over deep inheritance;
- use polymorphism at genuine variation points;
- reuse Greia platform services/primitives rather than cloning them;
- preserve both Greia script-launch and repository/package import contexts;
- use Greia storage/events/progression/permissions rather than private substitutes;
- keep Activity code display/input-backend neutral;
- never draw or own the real Greia Home/Back system controls.

### Shared child creations — active platform workstream (not yet public SDK)

**Storage sizing:** do not assume the historical 32 MiB private namespace. Shipped Greia now uses an adaptive per-Activity namespace (25% of the actual writable profile-data filesystem, with the old byte quota only as a minimum/fallback), while a shared platform `VolumeBudget` caps aggregate variable child-data growth at 75% used plus 512 MiB free. Per-file/KV/media bounds still apply. Activities must never implement their own disk-usage policy or bypass the trusted storage broker.

The platform-owned PNG/WAV/UTF-8 `CreationLibrary` has a guarded Activity transfer API (`get_creations`) and manifest `creations.produces`/`creations.consumes` declarations. The universal `CreationsGalleryScreen`/controller and the nonblocking `request_selection(...)` / `poll_selection(...)` / `cancel_selection(...)` protocol now connect in SOURCE-WIP to a trusted modal host. Legacy-X and Simulator each implement the same runtime-neutral Shell modal contract; an Activity still cannot enumerate/delete the profile library or mint its own handle. **Never** read another Activity namespace, mount a global shared directory, create an Activity-local chooser, or block a frame loop waiting for human input.

Painting is the reference PNG integration: normal autosaves stay private; an explicit up-arrow publishes an immutable snapshot; from Painting's own gallery a down-arrow requests `image/png`, the Activity polls at a bounded cadence, and a child-selected one-use handle is imported as a new independent editable private painting after digest/type validation. This latest interaction is **SOURCE-WIP and not yet accepted in a complete checkout/GUI**. New consumers should copy the semantic pattern only after the consolidated acceptance is green. The cross-Activity implementation and 45-Activity release review remain tracked in the single Creations PLAN/PROGRESS; Shape Garden is not yet a persistent stamp editor and must not be treated as one without the planned project-model work.

### Performance is correctness

The Acer-class floor is part of the design target, not a later optimization pass.

Avoid hot-path work such as:

```text
filesystem scans
asset decoding/loading
image scaling/transforms
font recreation
subprocess/device discovery
storage/config reads
large allocation churn
unbounded audio/event queues
full-screen expensive alpha work that never settles
```

Prefer preloaded/cached immutable assets, bounded caches/queues, event-driven/invalidation rendering where appropriate, and cheap static states.

A performance stall can become an audio/timing bug by delaying feedback until semantic events collide.

Load `ENGINEERING.md` before implementation.

## 12. Project-specific tools stay with the project

Activity-specific authoring/generation/migration tooling belongs under:

```text
activities/<activity_dir>/tools/
```

Examples:

```text
activities/my_activity/tools/generate_voice_requests.py
activities/my_activity/tools/build_local_assets.py
activities/my_activity/tools/migrate_content.py
```

Rules:

1. place project-specific tools there from the start;
2. runtime code does not belong in `tools/`;
3. repository root `tools/` is only for genuinely Greia-wide tooling;
4. remove obsolete/one-shot tools and scratch output when work closes;
5. remember the Activity directory is also package input—do not ship development machinery accidentally;
6. promote a local tool to root only when it genuinely becomes a reusable Greia-wide facility with a stable contract.

## 13. Use the headless Simulator throughout development

Do not wait for the Activity to be finished.

Typical loop:

```text
minimal valid skeleton
-> headless Simulator

first meaningful child interaction
-> focused tests + headless Simulator

major runtime/resource/refactor change
-> focused tests + headless Simulator

completion/restart/audio integration
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

Use `--press-key` or `--click-x/--click-y` for meaningful mechanical interaction where practical, and test relevant shipped locales.

`SIMULATOR_WORKFLOW.md` owns the detailed loop.

## 14. Final GUI Simulator review is mandatory

Headless integration cannot decide whether:

- a toddler understands the first action;
- the game is fun/coherent;
- targets are large enough;
- the teaching mechanic works;
- presenter/audio timing feels right;
- final-item feedback collides;
- 1024×600 presentation is pleasant;
- obvious performance stalls exist.

After final headless integration launch:

```bash
python3 tools/greia_simulator.py \
  --state-dir ~/.greia-simulator-review-<activity_dir>
```

Present that exact final state to the user/reviewer.

If GUI review cannot be performed, the strongest honest result is:

```text
SOURCE-VERIFIED / HEADLESS-SIMULATOR-PASS / GUI-REVIEW-PENDING
```

Any runtime-relevant edit after evidence requires rerunning the applicable final checks.

## 15. Load specialist companions only when relevant

```text
PRESENTERS_AND_CURIOSITY.md   presenter/factual-curiosity design
VOICE_GENERATION.md           actual speech production/replacement
MICROPHONE_RECORDING.md       child microphone recording
LAUNCHER_SPOKEN_LABELS.md     launcher title speech
TERMINAL_RENDERING.md         completion/Continue/Replay presentation
REFACTORING.md                substantive existing-Activity refactor
LAUNCH_ACCEPTANCE.md          detailed final launch/evidence procedure
```

For actual visual asset creation/adaptation load:

```text
skills/greia-visual-authoring/SKILL.md
```

For `.greiaactivity` packaging use current package authority:

```text
docs/architecture/GREIA_ACTIVITY_PACKAGE_FORMAT.md
src/greia_platform/activity_packages.py
src/greia_platform/activity_package_format.py
```

## 16. Definition of done

A new first-party Activity is not done until all applicable items are true:

```text
PARENT_REQUEST_DECOMPOSED=yes
ACTIVITY_SET_PLAN_COMPLETE=yes/not-applicable
CHILD_PLAY_LOOP_CLEAR=yes
LEARNING_OR_CREATIVE_PURPOSE_CLEAR=yes
RECOMMENDED_AGE_MIN_DEFINED=yes
DISCOVERY_METADATA_VALID=yes
FIRST_ACTION_CLEAR_WITHOUT_READING=yes
REQUIRED_SPOKEN_COMMANDS_COMPLETE=yes/not-applicable
VOICE_KIND_SEMANTICS_CORRECT=yes/not-applicable
HUMAN_AUDIO_REVIEW_COMPLETE=yes/not-applicable
FINAL_ACTION_FEEDBACK_CONFLICT_RESOLVED=yes
PROGRESSION_REWARD_RELATIONSHIP_DEFINED=yes
PROJECT_LOCAL_TOOLS_CLEAN=yes
PERFORMANCE_HOT_PATHS_BOUNDED=yes
FOCUSED_TESTS_PASS=yes
FINAL_HEADLESS_SIMULATOR_PASS=yes
GUI_SIMULATOR_USER_REVIEW=PASS
```

Physical/Acer evidence is additionally required for claims that depend on physical performance, hardware behavior or production display/input paths.

Never upgrade source or Simulator evidence into a stronger evidence class that did not actually run.
