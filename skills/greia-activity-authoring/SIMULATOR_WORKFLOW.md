# Greia Activity Simulator Workflow

**Status:** mandatory focused companion once Activity implementation starts  
**Audience:** Activity authors, coding agents, reviewers

The Simulator is part of the authoring loop, not a ceremonial test at the end.

Use two different modes for two different jobs:

```text
HEADLESS SIMULATOR
    frequent mechanical integration checks during implementation

GUI SIMULATOR
    final human visual/interaction review of the exact final Activity state
```

Neither mode is physical Acer/Pi evidence.

## 1. Why both modes exist

The headless runner exercises the real Greia child Shell, catalogue route, Activity supervisor/lifecycle and protected Home path without requiring a person to drive the UI.

It is excellent for catching:

- manifest/discovery mistakes;
- script/package import errors;
- runtime-policy failures;
- startup exceptions;
- READY failures;
- dead first frame;
- immediate crashes;
- first-interaction crashes;
- Home/return lifecycle failures.

It does **not** prove that the Activity is attractive, understandable, pedagogically good, readable at the intended size, visually balanced, or actually obvious to a pre-reader.

That is why the final exact source state must also be launched with the normal GUI Simulator for human review.

## 2. Headless first: normal implementation loop

For a built-in Activity under `activities/<id>/`, run from repository root:

```bash
PYTHONPATH=src python3 tools/headless_greia_simulator.py \
  --activity-dir activities/<activity_dir> \
  --workspace-dir /tmp/greia-sim-<activity_dir> \
  --locale it \
  --viewport 1024x600 \
  --survival-seconds 12 \
  --screenshot-prefix /tmp/greia-<activity_dir>-it
```

The runner detects that a direct child of repository `activities/` is built-in and launches its canonical identity instead of republishing it as developer content.

For an external/new Activity source outside the built-in tree, the same `--activity-dir` route publishes it into an isolated developer workspace through the Simulator's normal source transaction.

Use a fresh/Activity-specific workspace. Do not share mutable simulator workspaces between concurrent Activity runs.

## 3. Run headless early, not only when coding is finished

Recommended rhythm:

```text
minimal valid Activity skeleton
-> headless launch

first meaningful play loop
-> headless launch + one meaningful input

major module/refactor/import change
-> focused tests + headless launch

audio/resource/startup integration change
-> headless launch

completion/restart flow added
-> headless launch exercising that path where possible

final runtime edit
-> final headless launch again
```

Do not build several thousand lines and dozens of assets before the first real Greia launch.

For multi-Activity work, get the first Activity through a real headless launch before mechanically cloning the architecture into the others.

## 4. Headless meaningful interaction

The runner supports one simple target-Activity interaction:

```text
--press-key <KEY>
```

or:

```text
--click-x <X> --click-y <Y>
```

Use whichever meaningfully exercises the current Activity.

Example:

```bash
PYTHONPATH=src python3 tools/headless_greia_simulator.py \
  --activity-dir activities/my_activity \
  --workspace-dir /tmp/greia-sim-my-activity \
  --locale it \
  --viewport 1024x600 \
  --survival-seconds 12 \
  --press-key RETURN \
  --screenshot-prefix /tmp/greia-my-activity-it
```

The headless runner already exercises the protected Greia Home return after the Activity phase. Do not replace this with a direct `python main.py` run and call it equivalent.

## 5. Locale coverage

If child-facing spoken/localized behavior changes, repeat relevant headless checks for the shipped locales.

For the normal current first-party locale pair:

```bash
# Italian
PYTHONPATH=src python3 tools/headless_greia_simulator.py \
  --activity-dir activities/<activity_dir> \
  --workspace-dir /tmp/greia-sim-<activity_dir>-it \
  --locale it \
  --viewport 1024x600 \
  --survival-seconds 12 \
  --screenshot-prefix /tmp/greia-<activity_dir>-it

# English
PYTHONPATH=src python3 tools/headless_greia_simulator.py \
  --activity-dir activities/<activity_dir> \
  --workspace-dir /tmp/greia-sim-<activity_dir>-en \
  --locale en \
  --viewport 1024x600 \
  --survival-seconds 12 \
  --screenshot-prefix /tmp/greia-<activity_dir>-en
```

Only test locales the Activity actually claims to ship. Do not infer support from unrelated translation tables.

## 6. Headless screenshots are diagnostic, not human acceptance

The headless runner can capture frames. Inspect them when useful for obvious crashes/layout regressions.

But do not write:

```text
VISUAL_ACCEPTANCE=PASS
PRE_READER_UX=PASS
```

merely because a PNG exists.

Human visual/interaction review happens in the GUI Simulator.

## 7. Source tests and headless Simulator complement each other

Use focused tests for deterministic logic, state, storage, event semantics and layout calculations.

Use the headless Simulator for integration.

Neither substitutes for the other.

A useful implementation cycle is:

```text
edit
-> focused tests
-> headless Simulator
-> inspect concrete failure
-> fix
-> repeat
```

Run broader repository gates when the change warrants them; do not substitute a full test count for an actual Activity launch.

## 8. Final GUI Simulator review is mandatory for new Activities

After the Activity is functionally complete and the final headless run is green, launch the normal Simulator:

```bash
python3 tools/greia_simulator.py \
  --state-dir ~/.greia-simulator-review-<activity_dir>
```

Then present the running Simulator to the user/reviewer.

For built-in Activities, use the normal Greia child launcher/catalogue path.

For external source Activities, use **Load Activity Folder…**.

For distributable package acceptance, use **Install Activity Package…** rather than manually copying files.

The GUI review must be against the exact final runtime-relevant source state.

## 9. What the human reviewer checks

At minimum, review at `1024×600`:

### Child comprehension

- Is the first meaningful action obvious without reading?
- If language is required, is the command spoken automatically or through an obvious/repeatable cue?
- Are required instructions short and understandable?
- Can a wrong action be understood/retried without prose?
- Is continue/replay/completion understandable without reading?

### Gameplay/teaching

- Does the mechanic actually express the intended learning/development goal?
- Is the challenge appropriate for the target child?
- Does difficulty progress gently?
- Is repetition varied enough to remain engaging?
- Is feedback immediate, warm and informative?

### Visual quality

- Are important entities visually dominant and large enough?
- Are interactive and decorative elements distinguishable?
- Is the canonical presenter visible/appropriate where expected?
- Is the scene coherent rather than programmer-placeholder UI?
- Is anything clipped, overlapped, tiny, visually noisy or ambiguous?

### Audio

- Do spoken instructions play at the correct moment?
- Do clips overlap/stomp each other?
- Is required speech repeatable where useful?
- Are character identity and pedagogical-sound routing correct?
- Does the Activity remain understandable if optional decorative audio is absent?

### Lifecycle

- Does Activity launch normally?
- Does it remain alive after interaction?
- Does protected Greia Home work?
- Does return to Shell remain clean?

## 10. Responsive GUI review when layout changed

When layout/responsive behavior is part of the work, review more than one shape/scale.

Useful matrix from the canonical Simulator guide includes:

```text
1024×600  normal
1024×600  large
1280×800  normal
1366×768  compact
1920×1080 normal
one non-preset intermediate viewport when relevant
```

Do not make the Activity branch on Simulator identity or preset names.

## 11. The user review is not optional evidence invented by the agent

An agent may run automated/headless checks itself.

For meaningful final visual/child-experience acceptance, the agent must **launch the GUI Simulator and hand the exact final state to the user/reviewer** when the working environment allows it.

Do not self-approve subjective visual quality merely because the agent authored the Activity.

If the environment cannot launch/present the GUI Simulator, report:

```text
SOURCE-VERIFIED / HEADLESS-SIMULATOR-PASS / GUI-REVIEW-PENDING
```

Do not call the Activity fully accepted.

## 12. Any final runtime edit invalidates both final checks

After the final headless/GUI review, if you change:

- Activity Python/runtime code;
- `activity.toml`;
- runtime-loaded assets;
- localized runtime resources;
- audio used by the Activity;
- startup/lifecycle behavior;

rerun the final headless integration check and re-present the changed GUI state as appropriate.

Do not cite a screenshot or GUI review from a previous source state.

## 13. Exact completion record

For every new Activity record:

```text
HEADLESS_SIMULATOR_FINAL=PASS/FAIL
HEADLESS_SHA=
HEADLESS_LOCALES=
HEADLESS_VIEWPORTS=
HEADLESS_MEANINGFUL_INTERACTION=
PROTECTED_HOME_RETURN=PASS/FAIL
GUI_SIMULATOR_LAUNCHED=yes/no
GUI_REVIEW_SHA=
GUI_REVIEW_VIEWPORTS=
USER_VISUAL_REVIEW=PASS/FAIL/PENDING
PRE_READER_REVIEW=PASS/FAIL/PENDING
GAMEPLAY_TEACHING_REVIEW=PASS/FAIL/PENDING
FINAL_ACTIVITY_STATUS=
```

Normal complete result for a new first-party Activity requires both a green final headless integration check and a completed GUI child-experience review.