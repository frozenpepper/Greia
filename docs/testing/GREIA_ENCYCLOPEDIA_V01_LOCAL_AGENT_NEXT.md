# Greia Encyclopedia v0.1 — LOCAL AGENT NEXT TASK

This is the single rolling instruction for the **next** owner-machine task.

## Task now: Simulator / UX acceptance only

The deterministic source gate is COMPLETE and GREEN on runtime/source commit:

```text
d89809a43cdfe62c85775ccdcfd04eb6e34fbd05
```

Evidence:

```text
tmp/encyclopedia-v01-acceptance/20260828_044052/
```

Proven there:

```text
voice rows                    378 / 378
focused Encyclopedia tests     53 / 53 PASS
make verify                  1431 / 1431 PASS
first-party Activity validation 35 / 35 PASS
accepted-audio sync             PASS (0 OWNER_ACCEPTED rows)
worktree postflight             clean
```

Truthful state entering this task:

```text
SOURCE-VERIFIED / SIMULATOR-UNVERIFIED
NARRATION ACCEPTANCE PENDING
```

**DO NOT rerun the source gate in this task.**
**DO NOT generate any narration.**
**DO NOT wait for the 378 requested recordings.**

The Simulator pass is specifically allowed to run with zero accepted narration. Missing narration must be reported as `NARRATION ACCEPTANCE PENDING`, not repaired with runtime TTS.

---

## 1. Read the Simulator authorities

Before testing, read:

```text
AGENTS.md
encyclopedia/HANDOVER.md
skills/greia-activity-authoring/LAUNCH_ACCEPTANCE.md
skills/greia-activity-authoring/PRE_READER_UX.md
docs/development/GREIA_ACTIVITY_SIMULATOR.md
docs/testing/GREIA_ENCYCLOPEDIA_V01_CONSOLIDATED_ACCEPTANCE.md
```

For this task, the source-gate portions of the consolidated runbook are already satisfied by the evidence above. Execute only its **Simulator / visual / input / pre-reader / responsive** stages.

Do not repair source during the evidence run. Preserve the first reproducible blocking runtime failure.

---

## 2. Update safely and prove no runtime source changed after the green gate

From the existing Greia checkout:

```bash
git branch --show-current
git status --short
git fetch origin
git pull --ff-only origin main
git rev-parse HEAD
git status --short
```

Required:

```text
branch = main
worktree = clean
```

Now compare the source-gate commit to current HEAD:

```bash
git diff --name-only d89809a43cdfe62c85775ccdcfd04eb6e34fbd05..HEAD
```

The commits added after the green gate should be acceptance/documentation instructions only. If the diff includes any runtime Encyclopedia Python, manifest, locale, runtime audio asset, shared platform code, or test code, STOP and report the paths before launching Simulator.

Do not reset, clean, stash or discard anything.

---

## 3. Create a fresh Simulator evidence directory

From repository root:

```bash
bash
set -u
RUN_ID="$(date +%Y%m%d_%H%M%S)"
EVIDENCE="./tmp/encyclopedia-v01-acceptance/${RUN_ID}-simulator"
mkdir -p "${EVIDENCE}/screenshots"
printf '%s\n' "${EVIDENCE}" > ./tmp/encyclopedia-v01-acceptance/.latest-run

git rev-parse HEAD | tee "${EVIDENCE}/starting-sha.txt"
git status --short | tee "${EVIDENCE}/git-status-before.txt"
printf '%s\n' "tmp/encyclopedia-v01-acceptance/20260828_044052/" > "${EVIDENCE}/source-gate-evidence.txt"
```

Record explicitly in the final report that source verification came from the green source-gate evidence at `20260828_044052`.

---

## 4. Start the real Greia Simulator

Simulator mutable state MUST remain outside the checkout:

```bash
python3 tools/greia_simulator.py \
  --state-dir ~/.greia-simulator-encyclopedia-v01
```

Set:

```text
viewport = 1024x600
profile UI size = normal
```

Use **Load Activity Folder…** and select exactly:

```text
activities/enciclopedia_greia/
```

Launch **Enciclopedia Greia** from the normal Greia Shell/catalogue path.

Do not instantiate page classes directly and do not bypass the Shell.

### Mandatory initial launch gate

Confirm all of these:

```text
first usable frame appears
Activity survives >= 10 seconds
one visible meaningful interaction succeeds
Activity remains alive afterward
protected Greia Home remains reachable
return to Shell is possible
```

In a second Bash terminal, from the repository root:

```bash
EVIDENCE="$(cat ./tmp/encyclopedia-v01-acceptance/.latest-run)"
python3 tools/greia_simulator_ctl.py status \
  | tee "${EVIDENCE}/simulator-status-initial.txt"
python3 tools/greia_simulator_ctl.py screenshot \
  "${EVIDENCE}/screenshots/00-home.png"
```

### Hard stop conditions

STOP immediately and return evidence if any of these occurs:

- crash;
- Activity process exits unexpectedly;
- unusable/blank first frame;
- persistent hang;
- input stops working;
- internal Back cannot work;
- protected Greia Home becomes unreachable;
- return to Shell fails;
- a visible section/final-entry anchor is genuinely unreachable.

Do not repair and relaunch inside this run.

Non-blocking visual/pre-reader defects may be recorded and the traversal may continue if the Activity remains operable.

---

## 5. Full 1024x600 reachability + interaction traversal

At `1024x600 / normal`, visit **all six section pages and all 36 factual final entries through normal child navigation**.

For every final entry:

1. enter from its visible section page;
2. perform the listed signature interaction;
3. confirm a visible state change, animation or result;
4. confirm the Activity remains responsive;
5. return with the Encyclopedia's internal Back path;
6. capture one screenshot after the interaction.

### Animals

```text
animals.lion          roar + mane/paw exploration
animals.elephant      trunk/water + ear/size exploration
animals.octopus       camouflage + ink
animals.bee           flower-to-flower pollination
animals.penguin       waddle/swim or habitat demonstration
animals.frog          life-cycle sequence
```

### Space

```text
space.sun             rotation / Earth-scale comparison
space.mercury         crater + day/night reveal
space.venus           cloud/surface reveal
space.earth           rotation + day/night
space.moon            phase demonstration
space.mars            landmark reveal
space.jupiter         bands / Great Red Spot exploration
space.saturn          ring tilt/rotation
space.uranus          sideways-rotation demonstration
space.neptune         bounded wind/cloud motion
```

### Earth & Nature

```text
earth.volcano         pressure -> eruption
earth.rain            water-cycle loop
earth.ocean           surface-to-depth journey
earth.tree            roots / seasons
earth.rainbow         Sun/rain alignment
```

### My Body

```text
body.heart             beat + circulation
body.lungs             breathe in/out
body.bones             skeleton reveal/assemble
body.teeth             tooth-shape jobs
body.senses            multi-sense exploration
```

### Science & Machines

```text
machines.gears         linked gear train
machines.magnet        attract/repel/material comparison
machines.bicycle       pedal-chain-wheel drivetrain
machines.airplane      wing/airflow schematic
machines.bridge        load / force-path comparison
```

### Long Ago

```text
history.dinosaurs      representative dinosaur forms
history.fossils        brush/reveal fossil
history.mammoth        cold-adaptation comparison
history.cave_paintings light/reveal rock art
history.pyramids       bounded layer/cross-section build
```

Screenshot filenames:

```text
screenshots/animals.lion.png
screenshots/animals.elephant.png
...
screenshots/history.pyramids.png
```

Also capture the six section pages:

```text
screenshots/01-animals-section.png
screenshots/02-space-section.png
screenshots/03-earth-section.png
screenshots/04-body-section.png
screenshots/05-machines-section.png
screenshots/06-history-section.png
```

Do NOT read implementation source to discover click coordinates. If the intended target cannot be found from the visual experience itself, record a pre-reader/UX defect.

---

## 6. Pointer vs semantic keyboard parity sample

Test these six entries with BOTH pointer and semantic keyboard navigation:

```text
animals.octopus
space.saturn
earth.volcano
body.heart
machines.gears
history.fossils
```

For each:

1. enter and trigger the primary interaction with pointer;
2. return to the section;
3. navigate to the same entry using visible focus + arrows + RETURN;
4. trigger the same primary interaction with semantic keyboard activation;
5. confirm both input routes manipulate the same visible behavior/state.

CLI keys may be used:

```bash
python3 tools/greia_simulator_ctl.py key RIGHT
python3 tools/greia_simulator_ctl.py key LEFT
python3 tools/greia_simulator_ctl.py key UP
python3 tools/greia_simulator_ctl.py key DOWN
python3 tools/greia_simulator_ctl.py key RETURN
```

Do not hard-code a sequence without visually observing the current focus state.

Capture one parity screenshot per stress entry after keyboard activation:

```text
screenshots/parity-animals.octopus.png
screenshots/parity-space.saturn.png
screenshots/parity-earth.volcano.png
screenshots/parity-body.heart.png
screenshots/parity-machines.gears.png
screenshots/parity-history.fossils.png
```

---

## 7. Mandatory pre-reader review

Review Home, all six sections, and the six stress entries as if the child cannot read any text.

For each ask:

```text
Can the first meaningful action be inferred without reading?
Are primary targets large and visually distinct?
Does focus/movement/animation reveal what is interactive?
Can the child go Back without reading prose?
Does interaction give immediate understandable visual feedback?
Would missing narration make the page unusable, or only less informative?
```

Record these final fields exactly:

```text
PRE_READER_CORE_FLOW_PASS=yes/no
TEXT_REQUIRED_FOR_GAMEPLAY=yes/no
NO_READING_FIRST_ACTION_PASS=yes/no
NO_READING_RETRY_PASS=yes/no/not-applicable
NO_READING_COMPLETION_PASS=yes/no/not-applicable
PRIMARY_INSTRUCTION_CHANNEL=visual/voice/combined
SUPPORTED_LOCALES=it,en
SPOKEN_INSTRUCTION_COVERAGE=0/378 OWNER_ACCEPTED at this tested state
MICROPHONE_RECORDING_USED=no
MICROPHONE_RECORDING_NO_READING_FLOW_PASS=not-applicable
```

Do NOT fail the visual/input pass merely because narration is not produced yet. Report it separately as:

```text
NARRATION_ACCEPTANCE_PENDING=yes
```

Do NOT add runtime TTS.

---

## 8. Responsive spot-check

Only after the full 1024x600 traversal remains operable, spot-check these presets:

```text
1024x600  + large
1280x800  + normal
1366x768  + compact
1920x1080 + normal
1111x700  + normal/custom
```

At every preset inspect:

```text
home
animals
space
earth
body
machines
history
animals.octopus
space.saturn
earth.volcano
body.heart
machines.gears
history.fossils
```

Check:

```text
no child-viewport clipping
protected Greia chrome unobscured
internal Back visually distinct from system Home
large targets reachable
render/hit regions aligned
no aspect-ratio distortion
titles/captions not required to discover interaction
animations remain bounded/coherent
```

Capture at least one screenshot per preset showing Home plus one stress entry, with filenames that include the viewport/profile.

---

## 9. Final clean return and evidence

Return to Greia Shell using protected Home.

Then capture:

```bash
EVIDENCE="$(cat ./tmp/encyclopedia-v01-acceptance/.latest-run)"
python3 tools/greia_simulator_ctl.py status \
  | tee "${EVIDENCE}/simulator-status-final.txt"
git diff --check \
  2>&1 | tee "${EVIDENCE}/git-diff-check.txt"
git status --short | tee "${EVIDENCE}/git-status-after.txt"
```

Do not commit evidence or repair source in this run.

---

## 10. Return report

Return one report with exactly these sections.

### A. Identity

```text
STARTING_SHA=
SOURCE_GATE_SHA=d89809a43cdfe62c85775ccdcfd04eb6e34fbd05
SOURCE_GATE_EVIDENCE=tmp/encyclopedia-v01-acceptance/20260828_044052/
WORKTREE_BEFORE=
WORKTREE_AFTER=
```

### B. Reference traversal

```text
SIMULATOR_LAUNCH=PASS/FAIL
REFERENCE_1024x600_SURVIVAL_10S=PASS/FAIL
ALL_6_SECTIONS_REACHABLE=PASS/FAIL
ALL_36_FINAL_ENTRIES_REACHABLE=PASS/FAIL
ALL_36_SIGNATURE_INTERACTIONS=PASS/FAIL
INTERNAL_BACK_ALL_PAGES=PASS/FAIL
RETURN_TO_SHELL=PASS/FAIL
```

### C. Input parity

```text
POINTER_SEMANTIC_PARITY_6_STRESS_ENTRIES=PASS/FAIL
```

List each of the six entries individually.

### D. Pre-reader

```text
PRE_READER_CORE_FLOW_PASS=yes/no
TEXT_REQUIRED_FOR_GAMEPLAY=yes/no
NO_READING_FIRST_ACTION_PASS=yes/no
NO_READING_RETRY_PASS=yes/no/not-applicable
NO_READING_COMPLETION_PASS=yes/no/not-applicable
PRIMARY_INSTRUCTION_CHANNEL=visual/voice/combined
SPOKEN_INSTRUCTION_COVERAGE=0/378 OWNER_ACCEPTED
NARRATION_ACCEPTANCE_PENDING=yes
```

### E. Responsive

```text
RESPONSIVE_SAMPLE=PASS/FAIL
```

Report each preset individually.

### F. Findings

For every concrete defect:

```text
page_id=
viewport/profile=
severity=blocking/non-blocking
steps_to_reproduce=
expected=
actual=
screenshot=
```

Do not call something a defect solely because narration is absent.

### G. Evidence

Return the exact evidence directory and list its screenshot files.

---

## Acceptance language

If every Simulator/input/pre-reader/responsive gate passes on this runtime state, report exactly:

```text
SOURCE + SIMULATOR ACCEPTED / NARRATION ACCEPTANCE PENDING
```

If a blocking Simulator/runtime defect appears, report:

```text
SOURCE-VERIFIED / SIMULATOR-FAILED
```

and STOP without repairing it.