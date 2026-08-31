# Greia Encyclopedia — Interactive Runtime Acceptance

**Date:** 2026-08-31  
**Authority:** bounded owner-review gate for the post-E3 quality/interactivity pass  
**Plan:** `docs/plans/2026-08-30_ENCYCLOPEDIA_QUALITY_INTERACTIVITY_PASS.md`  
**Status:** executable protocol; successful mechanics do **not** self-approve visual quality

## 1. Purpose

The 43-page headless traversal proves catalogue coverage, launchability and that a primary activation changes pixels. It does **not** prove that the new interactions are attractive, understandable, useful to a pre-reader, or fun.

This gate therefore reviews a bounded showcase set through the real Greia child Shell / Simulator path:

```text
Home focus treatment
Space navigation + orbit controls
Earth-as-planet visual quality
Volcano eruption toy
Pyramids assembly toy
Gears cause/effect toy
Heart beat toy
Lungs breathing toy
Lion reaction
```

The owner remains the final aesthetic/engagement authority.

## 2. Preconditions

From the real Greia checkout:

```bash
git fetch origin
git switch main
git pull --ff-only origin main
git status --short --untracked-files=all
git rev-parse HEAD
```

Required:

```text
tracked checkout clean
exact starting SHA recorded
no concurrent source edits during capture
```

Use the native ARM Python on the current maintainer Mac:

```bash
PY=/opt/homebrew/bin/python3.12
```

Read first:

```text
AGENTS.md
skills/greia-activity-authoring/LAUNCH_ACCEPTANCE.md
skills/greia-visual-authoring/SKILL.md
encyclopedia/HANDOVER.md
docs/plans/2026-08-30_ENCYCLOPEDIA_QUALITY_INTERACTIVITY_PASS.md
```

## 3. Source gate before visual evidence

Run:

```bash
/opt/homebrew/bin/python3.12 tools/build_encyclopedia_visual_assets.py --check --group all

PYTHONPATH=src /opt/homebrew/bin/python3.12 -m unittest \
  tests.test_activity_enciclopedia \
  tests.test_activity_enciclopedia_visual_foundation \
  tests.test_encyclopedia_authoring_tools \
  tests.test_encyclopedia_e3_review_tools \
  tests.test_encyclopedia_section_hit_geometry \
  tests.test_encyclopedia_focus_treatment \
  tests.test_encyclopedia_runtime_art_staging \
  tests.test_encyclopedia_interactions

make PYTHON=/opt/homebrew/bin/python3.12 verify
```

If any source gate fails, stop. Do not produce owner-review screenshots from a red source state.

Record the exact green SHA:

```bash
ACCEPT_SHA="$(git rev-parse HEAD)"
echo "$ACCEPT_SHA"
```

## 4. Full mechanical traversal on the current SHA

Because many entry visuals changed after the earlier traversal evidence, re-run the current 43-page mechanical traversal once before the bounded showcase review.

The Simulator workspace must live outside the Greia source tree:

```bash
rm -rf ./tmp/encyclopedia-v01-current-traversal
rm -rf "${TMPDIR:-/tmp}/greia-encyclopedia-v01-current-workspace"

PYTHONPATH=src /opt/homebrew/bin/python3.12 \
  tools/encyclopedia_v01_headless_traversal.py \
  --workspace-dir "${TMPDIR:-/tmp}/greia-encyclopedia-v01-current-workspace" \
  --evidence-dir ./tmp/encyclopedia-v01-current-traversal \
  --locale it \
  --viewport 1024x600
```

Required:

```text
6/6 section pages captured
36/36 entry pages captured
36/36 primary interactions produce a changed frame
protected Home returns to Shell
status PASS
```

This is coverage evidence only. Do not call the quality pass accepted from this result.

## 5. Bounded interactive owner-review set

Use the real Greia Simulator / child Shell and its remote bridge. `tools/greia_simulator_ctl.py` supports `key`, `click`, `move`, `status` and `screenshot` against the running Simulator bridge.

Evidence root:

```text
./tmp/encyclopedia-interactive-review-2026-08-31/
```

Every image below must be 1024x600 and come from the same exact source SHA.

### 5.1 Home

Capture:

```text
home/01-animals-selected.png
home/02-space-selected.png
```

Acceptance questions:

```text
Does focus fit the portal rather than forming an ugly generic circle?
Does the selected portal remain readable?
Does changing selection feel deliberate and attractive?
Is the 3x2 book composition still centered and uncluttered?
```

### 5.2 Space

The section starts on Earth.

Capture:

```text
space/01-earth-selected.png
space/02-next-body-selected.png
space/03-paused.png
space/04-earth-selected-slow.png
```

Exercise:

```text
LEFT/RIGHT target navigation
pause/resume
slow speed setting
selected target highlight
```

Current control centers at 1024x600 are intentionally large:

```text
pause/resume: 315,540
slow speed notch: approximately 120,540
labels toggle: 380,540
discover lens: 760,540
```

Acceptance questions:

```text
Are planets slow enough to visually follow?
Can a child select bodies reliably without chasing them with the pointer?
Is the selected body unmistakable without obscuring it?
Does Earth read immediately as Earth?
Do pause/speed controls look like intentional child controls rather than debug UI?
```

### 5.3 Earth-as-planet

Enter `space.earth` through Space.

Capture:

```text
earth-planet/01-hero.png
earth-planet/02-second-discovery-selected.png
earth-planet/03-second-discovery-active.png
```

Acceptance questions:

```text
Is Earth now a convincing child-facing globe rather than a blue procedural circle?
Do continents/clouds/ocean read at normal viewing distance?
Does focus fit the selected discovery?
Does activation visibly teach something?
```

### 5.4 Volcano

Enter `earth.volcano` through the Earth/Nature section.

Capture:

```text
volcano/01-idle.png
volcano/02-erupting.png
volcano/03-high-eruption.png
volcano/04-smoke-toggle.png
```

Current main toy centers:

```text
strength slider: center 185,485; high notch approximately 245,485
erupt: 512,485
smoke toggle: 700,485
discover: 820,485
```

Acceptance questions:

```text
Is the eruption visually obvious and rewarding?
Does changing strength cause a meaningful visible change?
Is smoke control understandable without reading?
Does the page feel like a small discovery toy rather than a static diagram?
```

### 5.5 Pyramids

Enter `history.pyramids` through History.

The keyboard ACTIVATE path places the next block and is the required non-pointer alternative.

Capture:

```text
pyramids/01-initial.png
pyramids/02-partial-build.png
pyramids/03-completed-build.png
```

Build all four blocks in order and allow each placement animation to settle before the next activation.

Acceptance questions:

```text
Can the child understand that the loose blocks belong in the pyramid?
Is partial progress obvious?
Does the final pyramid remain visible long enough to feel rewarding?
Do dust/celebration effects reinforce success rather than obscure it?
```

### 5.6 Gears

Enter `machines.gears` through Machines.

Capture:

```text
gears/01-running.png
gears/02-paused.png
gears/03-reversed-fast.png
```

Current controls:

```text
speed slider: center 185,485; high notch approximately 245,485
pause/resume: 380,485
turn: 512,485
direction: 700,485
```

Acceptance questions:

```text
Do the three gears unmistakably mesh?
Do neighboring gears rotate in opposite directions?
Can speed/direction changes be understood from the animation?
Does the page teach cause/effect rather than merely decorate the image?
```

### 5.7 Heart

Enter `body.heart`.

Capture:

```text
heart/01-idle.png
heart/02-beating.png
```

Main heart toy center:

```text
512,485
```

Acceptance questions:

```text
Is the heart recognizable?
Does the beat reaction clearly affect the heart rather than only a button?
Is the body drawing appropriate and understandable for a small child?
```

### 5.8 Lungs

Enter `body.lungs`.

Capture:

```text
lungs/01-idle.png
lungs/02-breathe.png
```

Main breathe toy center:

```text
512,485
```

Acceptance questions:

```text
Do the lungs visibly inflate/deflate or otherwise demonstrate breathing?
Does the interaction teach body motion rather than only flash UI chrome?
```

### 5.9 Lion

Enter `animals.lion`.

Capture:

```text
lion/01-idle.png
lion/02-reaction.png
```

Main reaction control center:

```text
512,485
```

Acceptance questions:

```text
Does the lion remain anatomically coherent and immediately recognizable?
Is the reaction playful enough to justify pressing the toy button?
Is focus unobtrusive and fitted to the discovery object?
```

## 6. Interaction review rules

A frame changing is necessary but not sufficient.

Reject or flag any case where:

```text
selection graphics still look like arbitrary circles/ellipses
focus obscures the artwork
an interaction mainly animates the button instead of the subject
controls are too small or visually cryptic for a pre-reader
motion is too fast to follow/select
page-specific toy is not obvious without reading text
subject art is unrecognizable or anatomically/mechanically misleading
buttons overlap captions, presenter, trusted Home, or key content
interaction produces only trivial sparkle/halo changes
```

## 7. Contact sheet

Build a contact sheet containing only the bounded review frames above. Do not mix in all 72 traversal before/after frames.

Preferred order:

```text
Home
Space
Earth planet
Volcano
Pyramids
Gears
Heart
Lungs
Lion
```

Return both the contact sheet and the individual full-resolution frames.

## 8. Audio boundary

Solar System focus-name batch `E6-FOCUS-01` is currently a separate voice-production lane.

If accepted focus-name assets have not yet been integrated:

```text
visual/mechanical interactive review may proceed
spoken-name acceptance = PENDING
```

Do not substitute silent fail-soft hooks for audio acceptance.

Do not synthesize at runtime.

## 9. Exact-SHA integrity

After capture:

```bash
git rev-parse HEAD
git status --short --untracked-files=all
```

Required:

```text
HEAD == ACCEPT_SHA
tracked tree unchanged
review evidence only under ignored ./tmp paths
```

If source moved during review, mark evidence stale and rerun only after the new source gate is green.

## 10. Owner disposition

The agent must return one of:

```text
MECHANICAL_PASS_OWNER_REVIEW_REQUIRED
SOURCE_OR_RUNTIME_FAIL
STALE_SOURCE_EVIDENCE
```

The agent must **not** return `QUALITY_ACCEPTED` or mark the plan COMPLETE.

Only the owner review may change:

```text
IMPLEMENTED / OWNER RUNTIME REVIEW PENDING
```

to:

```text
COMPLETE / OWNER ACCEPTED
```

## 11. Required report

```text
ENCYCLOPEDIA_INTERACTIVE_RUNTIME_REVIEW_REPORT

source_sha:
build_check:
focused_tests:
make_verify:
full_traversal:
  sections:
  entries:
  interactions:

showcase:
  home:
  space:
  earth_planet:
  volcano:
  pyramids:
  gears:
  heart:
  lungs:
  lion:

contact_sheet:
individual_frames_root:

focus_name_audio:
  status: PENDING / INTEGRATED_OWNER_ACCEPTED
  batch: E6-FOCUS-01

tracked_tree_clean_after:
ending_sha:

mechanical_disposition:
OWNER_REVIEW_REQUIRED: YES
FIRST_FAILURE: NONE | <exact blocker>
```

Do not commit the review screenshots until the owner has reviewed them and requested preservation.