# Greia Activity Launch Acceptance

**Status:** mandatory completion gate for new Activities and substantive runtime Activity work  
**Audience:** Activity authors, coding agents, reviewers

This file defines the completion evidence. The working procedure lives in:

```text
skills/greia-activity-authoring/SIMULATOR_WORKFLOW.md
```

## 1. One rule

> **A new or substantively changed Activity is not complete until the exact final runtime-relevant state has passed Greia's real Simulator integration path. New/child-facing work also requires final GUI human review.**

Static validation, unit tests, imports, `python main.py`, package creation or `make verify` do not replace Simulator evidence.

## 2. Two evidence stages

### Stage A — headless integration

Use during development and once more on the final state:

```text
tools/headless_greia_simulator.py
```

This proves mechanical Greia integration such as:

- real child Shell/catalogue launch route;
- Activity discovery/runtime validation;
- script/package import compatibility;
- first Activity frame;
- startup survival;
- optional simple meaningful interaction;
- protected Greia Home return;
- clean workspace/Shell lifecycle.

Headless PASS does **not** prove visual quality, pedagogical quality or pre-reader comprehension.

### Stage B — GUI human review

For every new Activity and substantive child-facing redesign, launch:

```text
tools/greia_simulator.py
```

and present the exact final Activity to the user/reviewer.

This proves the subjective child-experience contract that automation cannot honestly approve:

- first action understandable without reading;
- required spoken commands actually work in context;
- gameplay/teaching loop makes sense;
- visual hierarchy/target sizes are appropriate;
- retry/completion are understandable;
- presenter and audio timing feel coherent;
- responsive behavior is acceptable where relevant.

## 3. When headless final acceptance is mandatory

Rerun the final headless gate after runtime-relevant changes including:

- new Activity creation;
- Python/module/refactor/import changes;
- `activity.toml` changes;
- startup/lifecycle/READY changes;
- runtime-loaded asset changes;
- localization/audio changes;
- input/rendering/layout changes;
- storage/events/progression changes;
- completion/restart changes;
- performance changes affecting runtime paths.

Documentation-only edits may mark it not applicable.

## 4. Final-source rule

Simulator evidence belongs to the exact source state tested.

Examples:

```text
headless PASS -> edit renderer.py -> headless evidence stale
GUI review PASS -> replace required voice clip -> GUI evidence stale for changed experience
headless PASS -> change activity.toml -> headless evidence stale
```

Rerun the applicable final checks after the final edit.

## 5. Canonical headless command

For a built-in Activity:

```bash
PYTHONPATH=src python3 tools/headless_greia_simulator.py \
  --activity-dir activities/<activity_dir> \
  --workspace-dir /tmp/greia-sim-<activity_dir> \
  --locale it \
  --viewport 1024x600 \
  --survival-seconds 12 \
  --screenshot-prefix /tmp/greia-<activity_dir>-it
```

Use a meaningful `--press-key` or `--click-x/--click-y` when appropriate.

For localized/spoken child behavior, exercise the relevant shipped locales.

Do not replace this with direct Activity execution.

## 6. What counts as a mechanical failure

Any of these is a failed headless/integration gate:

- `ImportError` / `ModuleNotFoundError`;
- Activity missing/rejected by the real catalogue/runtime path;
- startup traceback/exception;
- missing runtime resource/localization/audio file;
- READY never reached when required;
- blank/dead first frame;
- Activity exits unexpectedly after startup;
- first meaningful interaction crashes/kills it;
- protected Home fails to return through Greia lifecycle;
- Shell/runtime teardown remains stuck.

Fix the root cause and rerun against the new source state.

## 7. New Activity child-experience failure

A mechanically alive Activity still fails final acceptance when ordinary child use has problems such as:

- child must read instructions to know what to do;
- required language command is text-only;
- required spoken cue is missing in a shipped locale;
- targets are too small/ambiguous;
- wrong-action feedback gives no usable clue;
- completion/replay requires reading prose;
- learning goal is not expressed through the play mechanic;
- Activity is visually incoherent or obviously placeholder quality;
- critical spoken cues overlap/cut each other off;
- target child cannot reasonably manage the cognitive/motor load.

These require design/implementation correction and another final GUI review.

## 8. GUI review procedure

After final headless PASS, launch:

```bash
python3 tools/greia_simulator.py \
  --state-dir ~/.greia-simulator-review-<activity_dir>
```

Use normal Greia child navigation for built-ins. Use **Load Activity Folder…** for external source and **Install Activity Package…** when validating distribution/package behavior.

Review at `1024×600` at minimum.

When responsive/layout work is relevant, use the additional matrix in `SIMULATOR_WORKFLOW.md` / `docs/development/GREIA_ACTIVITY_SIMULATOR.md`.

## 9. No-reading review is part of GUI acceptance

For new/child-facing work load:

```text
skills/greia-activity-authoring/PRE_READER_UX.md
```

Require:

```text
first action understandable without reading
required language command spoken
primary targets clear and large
wrong action understandable without prose
continue/replay/completion understandable without prose
```

The human reviewer should hear actual required speech in context rather than approving cue tables on paper.

## 10. If GUI presentation is impossible

If the execution environment can perform headless checks but cannot launch/present the GUI Simulator, use status:

```text
SOURCE-VERIFIED / HEADLESS-SIMULATOR-PASS / GUI-REVIEW-PENDING
```

Do not call the new Activity fully accepted.

Similarly, if headless Simulator cannot run:

```text
SOURCE-VERIFIED / SIMULATOR-UNVERIFIED
```

The environment limitation changes the status; it does not weaken the gate.

## 11. Minimum evidence record

Record:

```text
ACTIVITY_ID=
SOURCE_SHA=
HEADLESS_SIMULATOR_FINAL=PASS/FAIL
HEADLESS_LOCALES=
HEADLESS_VIEWPORTS=
MEANINGFUL_INTERACTION=
PROTECTED_HOME_RETURN=PASS/FAIL
GUI_SIMULATOR_LAUNCHED=yes/no
GUI_REVIEW_SHA=
GUI_REVIEW_VIEWPORTS=
USER_VISUAL_REVIEW=PASS/FAIL/PENDING
PRE_READER_REVIEW=PASS/FAIL/PENDING
GAMEPLAY_TEACHING_REVIEW=PASS/FAIL/PENDING
FINAL_STATUS=
```

Do not invent PASS from expected behavior or authored tests that never executed.

## 12. Reviewer question

For a substantive Activity review, ask:

> **What exact final SHA passed the headless Greia Simulator, and what exact final GUI state did the human reviewer inspect?**

For new/child-facing work also ask:

> **Could the target child understand and operate the normal flow without reading, with required commands actually spoken?**

If those questions have no concrete evidence, the Activity is not finished.