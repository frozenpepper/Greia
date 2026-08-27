# Greia Encyclopedia v0.1 — Consolidated Acceptance Runbook

**Status:** mandatory closure gate for the frozen 43-page v0.1 source base  
**Activity:** `org.greia.enciclopedia` (`activities/enciclopedia_greia/`)  
**Authoring authority:** `encyclopedia/`  
**Scope:** source contracts, voice-ledger synchronization, accepted-audio integration, Greia Simulator launch/input/visual/no-reading review  
**Evidence boundary:** this run can establish source + desktop Simulator evidence only; it is not physical Acer/Pi evidence

This procedure exists because the owner deliberately chose a **source-first construction pass** instead of interrupting every page with a Simulator launch. The 43-page breadth is now frozen, so the deferred work is one consolidated acceptance pass. Do not add topics while executing this runbook.

Read before execution:

```text
AGENTS.md
encyclopedia/README.md
encyclopedia/HANDOVER.md
skills/greia-activity-authoring/SKILL.md
skills/greia-activity-authoring/LAUNCH_ACCEPTANCE.md
skills/greia-activity-authoring/PRE_READER_UX.md
docs/development/GREIA_ACTIVITY_SIMULATOR.md
```

---

## 1. Non-negotiable execution rules

The local test agent MUST follow these rules:

1. Work on the existing owner-controlled Greia checkout. Do not create another branch.
2. Do **not** run GitHub-hosted Actions.
3. Do **not** `git reset`, `git clean`, discard changes, rewrite recorder statuses, or remove audio files.
4. Do **not** repair source during this acceptance run. On the first real failure, stop and return evidence so the failure can be reviewed deliberately.
5. Do **not** generate narration during this run. Voice generation is a separate production workflow.
6. Do **not** change `REQUESTED` / `RECORDED_UNREVIEWED` rows to `OWNER_ACCEPTED`. Only an actual owner listening decision may do that.
7. `sync_voice_requests.py` may update factual queue rows deterministically; it must preserve recorder-owned status/notes.
8. `integrate_voice_assets.py` may package rows that are **already** `OWNER_ACCEPTED`; it must ignore all others.
9. No runtime TTS, speech recognition, LLM/provider call, network fact lookup, or heavy runtime dependency may be added to make a test pass.
10. Evidence must describe what actually ran. Do not infer PASS from source inspection.
11. Simulator state must remain **outside** the repository checkout. Use the state directory specified below.
12. Keep evidence project-local under `./tmp/encyclopedia-v01-acceptance/...`; do not commit the evidence directory.

A source/test failure is a hard stop before Simulator work. A Simulator/runtime failure is a hard stop before any claim of acceptance. Do not silently fix-and-rerun inside the same evidence run.

---

## 2. Create the evidence directory and record the starting state

From the Greia repository root:

```bash
set -u
RUN_ID="$(date +%Y%m%d_%H%M%S)"
EVIDENCE="./tmp/encyclopedia-v01-acceptance/${RUN_ID}"
mkdir -p "${EVIDENCE}/screenshots"

git rev-parse --show-toplevel | tee "${EVIDENCE}/repo-root.txt"
git branch --show-current | tee "${EVIDENCE}/branch.txt"
git rev-parse HEAD | tee "${EVIDENCE}/starting-sha.txt"
git status --short | tee "${EVIDENCE}/git-status-before.txt"
```

Required branch:

```text
main
```

Do not auto-clean a dirty tree.

- If the only existing changes are encyclopedia voice-ledger statuses/notes and requested staging audio created by the recording workflow, preserve them and continue.
- If runtime encyclopedia source (`activities/enciclopedia_greia/**/*.py`, `activity.toml`, runtime locale files) is unexpectedly dirty before this run, **STOP** and report the paths.
- If unrelated project source is dirty and could affect tests/runtime, **STOP** and report it rather than guessing.

---

## 3. Synchronize the complete v0.1 recording queue

Run exactly:

```bash
python3 encyclopedia/sync_voice_requests.py \
  2>&1 | tee "${EVIDENCE}/voice-sync.txt"
SYNC_RC=${PIPESTATUS[0]}
[ "${SYNC_RC}" -eq 0 ] || exit "${SYNC_RC}"

python3 encyclopedia/sync_voice_requests.py --check \
  2>&1 | tee "${EVIDENCE}/voice-sync-check.txt"
SYNC_CHECK_RC=${PIPESTATUS[0]}
[ "${SYNC_CHECK_RC}" -eq 0 ] || exit "${SYNC_CHECK_RC}"
```

Then independently check the row invariant:

```bash
python3 - <<'PY' | tee "${EVIDENCE}/voice-row-count.txt"
from pathlib import Path
from encyclopedia.voice_ledger import parse_ledger_rows

path = Path("encyclopedia/VOICE_RECORDING_REQUESTS.md")
rows = parse_ledger_rows(path.read_text(encoding="utf-8"))
print(f"rows={len(rows)}")
print(f"owner_accepted={sum(r.status == 'OWNER_ACCEPTED' for r in rows.values())}")
print(f"recorded_unreviewed={sum(r.status == 'RECORDED_UNREVIEWED' for r in rows.values())}")
print(f"requested={sum(r.status == 'REQUESTED' for r in rows.values())}")
assert len(rows) == 378, len(rows)
PY
```

Expected invariant:

```text
rows=378
```

The other status counts depend on real recording progress and must **not** be forced to a predetermined value.

If synchronization fails because a locked recorded row drifted, **STOP**. Do not rewrite the row. Return the exact error and current ledger diff.

Record the queue diff:

```bash
git diff -- encyclopedia/VOICE_RECORDING_REQUESTS.md \
  > "${EVIDENCE}/voice-ledger.diff"
```

---

## 4. Run focused provider-free source/authoring contracts

Run the focused suites first:

```bash
python3 -m unittest \
  tests.test_encyclopedia_authoring_tools \
  tests.test_activity_enciclopedia \
  tests.test_activity_contract \
  tests.test_first_party_activity_audience_metadata \
  tests.test_first_party_activity_readiness \
  -v 2>&1 | tee "${EVIDENCE}/focused-tests.txt"
FOCUSED_RC=${PIPESTATUS[0]}
[ "${FOCUSED_RC}" -eq 0 ] || exit "${FOCUSED_RC}"
```

These are provider-free. They must not invoke a voice model, LLM or network service.

Then run the repository validation gate:

```bash
make verify 2>&1 | tee "${EVIDENCE}/make-verify.txt"
VERIFY_RC=${PIPESTATUS[0]}
[ "${VERIFY_RC}" -eq 0 ] || exit "${VERIFY_RC}"
```

If either command fails, **STOP**. Return the failing test name/assertion/trace and the evidence directory. Do not patch source in this run.

---

## 5. Integrate any audio that is already OWNER_ACCEPTED

First inspect deterministically:

```bash
python3 encyclopedia/integrate_voice_assets.py --check \
  2>&1 | tee "${EVIDENCE}/voice-assets-check-before.txt"
VOICE_CHECK_RC=${PIPESTATUS[0]}
```

Interpretation:

- exit `0`: accepted assets/maps are already synchronized; continue;
- exit `1`: at least one already-`OWNER_ACCEPTED` clip needs deterministic packaging; run the integrator below;
- exit `2`: validation/source failure; **STOP** and return the error.

If and only if the check returned `1`:

```bash
python3 encyclopedia/integrate_voice_assets.py \
  2>&1 | tee "${EVIDENCE}/voice-assets-integrate.txt"
INTEGRATE_RC=${PIPESTATUS[0]}
[ "${INTEGRATE_RC}" -eq 0 ] || exit "${INTEGRATE_RC}"

python3 encyclopedia/integrate_voice_assets.py --check \
  2>&1 | tee "${EVIDENCE}/voice-assets-check-after.txt"
INTEGRATE_CHECK_RC=${PIPESTATUS[0]}
[ "${INTEGRATE_CHECK_RC}" -eq 0 ] || exit "${INTEGRATE_CHECK_RC}"
```

Never package `RECORDED_UNREVIEWED` clips merely to improve test coverage.

If integration changed runtime locale maps/audio assets, rerun the two encyclopedia-specific suites before launching the Simulator:

```bash
python3 -m unittest \
  tests.test_encyclopedia_authoring_tools \
  tests.test_activity_enciclopedia \
  -v 2>&1 | tee "${EVIDENCE}/post-audio-focused-tests.txt"
POST_AUDIO_RC=${PIPESTATUS[0]}
[ "${POST_AUDIO_RC}" -eq 0 ] || exit "${POST_AUDIO_RC}"
```

---

## 6. Start the real Greia Activity Simulator

Simulator mutable state must be outside the checkout:

```bash
python3 tools/greia_simulator.py \
  --state-dir ~/.greia-simulator-encyclopedia-v01
```

Use the desktop control plane to select:

```text
viewport: 1024x600
profile UI size: normal
```

Then use **Load Activity Folder…** and select exactly:

```text
activities/enciclopedia_greia/
```

Do not copy the Activity directly into simulator-managed storage.

Launch **Enciclopedia Greia** from the normal Greia Shell/catalogue path.

Mandatory Activity-level launch gate:

```text
first usable frame appears
Activity survives >= 10 seconds after first usable frame
one meaningful interaction succeeds
Activity remains alive afterward
protected Greia Home remains reachable
return to Shell succeeds cleanly
```

Capture initial evidence from a second terminal:

```bash
python3 tools/greia_simulator_ctl.py status \
  | tee "${EVIDENCE}/simulator-status-initial.txt"
python3 tools/greia_simulator_ctl.py screenshot \
  "${EVIDENCE}/screenshots/00-home.png"
```

If the Activity crashes, exits, hangs, fails to draw a usable first frame, loses input, or cannot return to Shell, **STOP** and return the concrete log/error. Do not repair and rerun inside this evidence run.

---

## 7. Reference-resolution full reachability + signature-interaction pass

At **1024x600 / normal**, visit every section and every final entry. For each final entry:

1. reach it through the visible section page, not by importing/opening the page class directly;
2. perform its signature interaction once;
3. confirm a visible state change/animation/result occurs;
4. confirm the Activity remains responsive;
5. use the encyclopedia's normal internal Back path to return to the section;
6. capture a screenshot **after** the interaction.

Use these signature interactions as the acceptance matrix:

```text
ANIMALS
animals.lion          roar + mane/paw exploration
animals.elephant      trunk/water + ear/size exploration
animals.octopus       camouflage + ink
animals.bee           flower-to-flower pollination
animals.penguin       waddle/swim or habitat demonstration
animals.frog          life-cycle sequence

SPACE
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

EARTH & NATURE
earth.volcano         pressure -> eruption
earth.rain            water-cycle loop
earth.ocean           surface-to-depth journey
earth.tree            roots / seasons
earth.rainbow         Sun/rain alignment

MY BODY
body.heart             beat + circulation
body.lungs             breathe in/out
body.bones             skeleton reveal/assemble
body.teeth             tooth-shape jobs
body.senses            multi-sense exploration

SCIENCE & MACHINES
machines.gears         linked gear train
machines.magnet        attract/repel/material comparison
machines.bicycle       pedal-chain-wheel drivetrain
machines.airplane      wing/airflow schematic
machines.bridge        load / force-path comparison

LONG AGO
history.dinosaurs      representative dinosaur forms
history.fossils        brush/reveal fossil
history.mammoth        cold-adaptation comparison
history.cave_paintings light/reveal rock art
history.pyramids       bounded layer/cross-section build
```

Screenshot naming convention:

```text
screenshots/animals.lion.png
screenshots/space.saturn.png
screenshots/earth.volcano.png
...
```

The exact click coordinates are intentionally not prescribed: the test is partly checking that a child-sized visible target can actually be found and used. If the tester cannot identify the intended target without reading implementation source, record that as a UX finding rather than guessing coordinates from code.

Also capture the six section pages:

```text
01-animals-section.png
02-space-section.png
03-earth-section.png
04-body-section.png
05-machines-section.png
06-history-section.png
```

No visible subject anchor may be dead.

---

## 8. Pointer vs semantic keyboard/controller parity

The six original architecture-stress entries are the parity sample:

```text
animals.octopus
space.saturn
earth.volcano
body.heart
machines.gears
history.fossils
```

For each sample:

1. enter once using pointer/touch-style interaction;
2. trigger its primary interaction with pointer;
3. return to the section;
4. reach/activate the same subject using Greia semantic keyboard navigation (arrows + `RETURN`/activation as exposed by the Activity);
5. confirm both routes manipulate the same page-owned state/behavior rather than two divergent implementations.

The CLI may be used for semantic keys, for example:

```bash
python3 tools/greia_simulator_ctl.py key RIGHT
python3 tools/greia_simulator_ctl.py key DOWN
python3 tools/greia_simulator_ctl.py key RETURN
```

Do not hard-code a sequence until the on-screen selection state has been observed; the point is to verify semantic navigation, not merely replay coordinates.

---

## 9. Mandatory no-reading UX pass

Review the Activity as if the child cannot read any title, caption or button label.

For Home, every section, and the six stress entries answer:

```text
Can the first meaningful action be inferred without reading?
Are primary targets large and visually distinct?
Does movement/highlighting/demonstration reveal what can be touched?
Can the child return/back without reading prose?
Does an interaction produce immediate understandable visual feedback?
Would a missing spoken clip make the page unusable, or only less informative?
```

Required evidence fields:

```text
PRE_READER_CORE_FLOW_PASS=yes/no
TEXT_REQUIRED_FOR_GAMEPLAY=yes/no
NO_READING_FIRST_ACTION_PASS=yes/no
NO_READING_RETRY_PASS=yes/no/not-applicable
NO_READING_COMPLETION_PASS=yes/no/not-applicable
PRIMARY_INSTRUCTION_CHANNEL=visual/voice/combined
SUPPORTED_LOCALES=it,en
SPOKEN_INSTRUCTION_COVERAGE=<actual packaged/accepted coverage observed>
MICROPHONE_RECORDING_USED=no
MICROPHONE_RECORDING_NO_READING_FLOW_PASS=not-applicable
```

Important: v0.1 intentionally excludes child speech recognition and runtime TTS. Do not mark those absences as defects.

If narration production is still incomplete, report the exact audio-coverage gap separately. A visually operable page can pass the **visual no-reading** check while the intended narrated encyclopedia experience remains **audio-acceptance pending**. Do not pretend missing reviewed narration is already accepted.

---

## 10. Responsive spot-check after the complete 1024x600 pass

The full 43-page traversal is required at the reference 1024x600 geometry. After it passes, run the following representative responsive sample:

```text
1024x600  + large
1280x800  + normal
1366x768  + compact
1920x1080 + normal
1111x700  + normal/custom
```

At every geometry/size combination inspect:

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

- no clipping outside the child viewport;
- protected Greia chrome remains unobscured;
- Activity-internal Back remains visually distinct from system Home;
- large targets remain reachable;
- render and hit regions remain aligned;
- text is supporting information, not the only interaction clue;
- animations remain bounded and coherent;
- no aspect-ratio distortion or off-screen state.

Changing the simulator preset may restart the child Shell. Reload/relaunch through the normal path as required by the simulator.

---

## 11. Clean return and final evidence capture

After the final interaction, use Greia Home and confirm clean return to the Shell.

Then capture:

```bash
python3 tools/greia_simulator_ctl.py status \
  | tee "${EVIDENCE}/simulator-status-final.txt"

git diff --check \
  2>&1 | tee "${EVIDENCE}/git-diff-check.txt"
DIFF_CHECK_RC=${PIPESTATUS[0]}
[ "${DIFF_CHECK_RC}" -eq 0 ] || exit "${DIFF_CHECK_RC}"

git status --short | tee "${EVIDENCE}/git-status-after.txt"
git diff -- encyclopedia/VOICE_RECORDING_REQUESTS.md \
  activities/enciclopedia_greia/locales \
  > "${EVIDENCE}/final-managed-diff.txt"
```

Do not commit `./tmp/encyclopedia-v01-acceptance/`.

Do not commit/push source repairs as part of this acceptance run. If the only working-tree changes are the deterministic 378-row voice synchronization and/or packaging of rows that were already `OWNER_ACCEPTED`, leave them intact and report them explicitly for review/commit.

---

## 12. Required return report

Return one concise report with these exact sections.

### A. Source identity

```text
STARTING_SHA=
BRANCH=
WORKTREE_BEFORE=
WORKTREE_AFTER=
```

### B. Voice queue

```text
VOICE_SYNC=PASS/FAIL
VOICE_SYNC_CHECK=PASS/FAIL
VOICE_ROWS=
REQUESTED=
RECORDED_UNREVIEWED=
OWNER_ACCEPTED=
VOICE_LEDGER_CHANGED=yes/no
```

### C. Accepted-audio integration

```text
INTEGRATION_CHECK_BEFORE=PASS/DRIFT/FAIL
INTEGRATION_EXECUTED=yes/no
INTEGRATION_CHECK_AFTER=PASS/FAIL/not-applicable
RUNTIME_AUDIO_PATHS_CHANGED=yes/no
```

### D. Automated tests

```text
FOCUSED_TESTS=PASS/FAIL
MAKE_VERIFY=PASS/FAIL/not-run
POST_AUDIO_TESTS=PASS/FAIL/not-applicable
FIRST_FAILURE=<exact test/assertion/trace or none>
```

### E. Simulator

```text
SIMULATOR_LAUNCH=PASS/FAIL/not-run
REFERENCE_1024x600_SURVIVAL_10S=PASS/FAIL/not-run
ALL_6_SECTIONS_REACHABLE=PASS/FAIL/not-run
ALL_36_FINAL_ENTRIES_REACHABLE=PASS/FAIL/not-run
ALL_36_SIGNATURE_INTERACTIONS=PASS/FAIL/not-run
POINTER_SEMANTIC_PARITY_6_STRESS_ENTRIES=PASS/FAIL/not-run
RETURN_TO_SHELL=PASS/FAIL/not-run
RESPONSIVE_SAMPLE=PASS/FAIL/not-run
```

### F. Pre-reader / audio

```text
PRE_READER_CORE_FLOW_PASS=yes/no/not-run
TEXT_REQUIRED_FOR_GAMEPLAY=yes/no/not-run
NO_READING_FIRST_ACTION_PASS=yes/no/not-run
NO_READING_RETRY_PASS=yes/no/not-applicable/not-run
NO_READING_COMPLETION_PASS=yes/no/not-applicable/not-run
PRIMARY_INSTRUCTION_CHANNEL=visual/voice/combined/not-run
SPOKEN_INSTRUCTION_COVERAGE=
```

### G. Findings

List every concrete visual/input/performance/content defect. For each include:

```text
page_id
viewport/profile-size
steps to reproduce
expected
actual
screenshot filename
whether it blocks acceptance
```

### H. Evidence location

Return the exact project-relative evidence directory, for example:

```text
./tmp/encyclopedia-v01-acceptance/20260827_203000/
```

Do not create a ZIP unless the owner explicitly asks for one.

---

## 13. Acceptance language

Only after all applicable automated and Simulator gates above pass may the source be described as Simulator-accepted for this exact runtime state.

If tests pass but Simulator has not run:

```text
SOURCE-VERIFIED / SIMULATOR-UNVERIFIED
```

If Simulator passes but reviewed narration is incomplete:

```text
SOURCE + SIMULATOR ACCEPTED / NARRATION ACCEPTANCE PENDING
```

If owner-accepted narration is later integrated, that is a runtime-relevant asset/resource change. Rerun the focused encyclopedia tests and the mandatory Simulator launch/survival + meaningful-interaction gate on the new exact source state before calling that later state accepted.
