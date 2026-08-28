# Greia Encyclopedia v0.1 — LOCAL AGENT NEXT TASK

## E1/E2 source is on `main`; build runtime art, verify, capture prototypes, then STOP

The owner rejected the old Encyclopedia graphics as a product target. The 43-page mechanical/runtime/research foundation remains useful and must be preserved.

Authoritative visual forensic review:

```text
docs/reviews/2026-08-28_ENCYCLOPEDIA_GRAPHICS_FORENSIC_AUDIT.md
```

Active Encyclopedia visual subplan:

```text
docs/plans/2026-08-28_ENCYCLOPEDIA_VISUAL_REAUTHORING.md
```

The first E1/E2 source tranche is now on `main`:

```text
shared Encyclopedia presentation primitives
bounded Activity-local authored-art cache
six editable SVG golden-master masters
Home golden-master page source
Animals golden-master page source
Lion golden-master page source
Saturn golden-master page source
Gears golden-master page source
Pyramids golden-master page source
authoring-time SVG -> PNG build/check tool
focused source contracts
```

The runtime PNG renditions are generated build products. They must now be built on the normal local maintainer checkout, verified, committed, and tested through the real Greia Simulator before the visual direction can be reviewed.

---

# 1. Hard prohibitions

Do **not**:

```text
redraw or migrate any additional Encyclopedia page
run the broad 43-page traversal/recapture
generate or integrate narration
start final pointer/responsive acceptance across all pages
change protected Greia Home chrome
change the stable 43-page factual scope
invent another asset/cache/scene system
add CairoSVG or SVG rasterization to the child runtime
weaken Activity/runtime/package validation
use GitHub-hosted Actions
```

If a golden-master direction looks poor, record it and stop. Do not hide that by propagating it.

---

# 2. Refresh and inspect first

From the existing Greia checkout:

```bash
git status --short
git fetch origin
git switch main
git pull --ff-only origin main
git status --short
git rev-parse HEAD
```

Expected: clean working tree before generation. If the tree is not clean, **STOP** and report the paths; do not discard or overwrite owner/concurrent work.

Read before execution:

```text
SETUP.md
AGENTS.md
skills/greia-activity-authoring/SKILL.md
skills/greia-activity-authoring/LAUNCH_ACCEPTANCE.md
skills/greia-activity-authoring/PRE_READER_UX.md
skills/greia-visual-authoring/SKILL.md
docs/testing/VISUAL_ACCEPTANCE_EVIDENCE_CONTRACT.md
docs/development/GREIA_ACTIVITY_SIMULATOR.md
docs/plans/2026-08-28_ENCYCLOPEDIA_VISUAL_REAUTHORING.md
```

Do not substitute old local notes for these current authorities.

---

# 3. Build and verify the six runtime PNGs

Editable masters:

```text
activities/enciclopedia_greia/assets/source/home_discovery_book.svg
activities/enciclopedia_greia/assets/source/animals_field_table.svg
activities/enciclopedia_greia/assets/source/lion_savanna.svg
activities/enciclopedia_greia/assets/source/saturn_observatory.svg
activities/enciclopedia_greia/assets/source/gears_workbench.svg
activities/enciclopedia_greia/assets/source/pyramids_diorama.svg
```

Build:

```bash
python3 tools/build_encyclopedia_visual_assets.py
```

Expected outputs:

```text
activities/enciclopedia_greia/assets/runtime/home_discovery_book.png
activities/enciclopedia_greia/assets/runtime/animals_field_table.png
activities/enciclopedia_greia/assets/runtime/lion_savanna.png
activities/enciclopedia_greia/assets/runtime/saturn_observatory.png
activities/enciclopedia_greia/assets/runtime/gears_workbench.png
activities/enciclopedia_greia/assets/runtime/pyramids_diorama.png
```

`CairoSVG` is an **authoring/maintainer dependency only**. If it is missing, follow `SETUP.md` maintainer/tooling rules. Do not add it to the child runtime, Activity manifest, or runtime dependencies.

Inspect the outputs:

```bash
ls -lh activities/enciclopedia_greia/assets/runtime/*.png
file activities/enciclopedia_greia/assets/runtime/*.png
```

All six must exist, be real non-empty 1024x600 PNGs. A partial pack is failure.

Then run the stale/generated-art guard:

```bash
python3 tools/build_encyclopedia_visual_assets.py --check
```

Expected final line:

```text
PASS 6 Encyclopedia runtime PNGs match editable masters
```

`--check` rebuilds into a temporary directory and byte-compares against the runtime pack. Any `MISSING` or `BUILD-DRIFT` result is a hard stop. Do not continue to Simulator evidence with stale or mismatched generated art.

---

# 4. Focused source/runtime checks

Run exactly:

```bash
python3 -m unittest \
  tests.test_activity_enciclopedia \
  tests.test_activity_enciclopedia_visual_foundation
```

Then run the repository's current normal local verification required for a changed first-party Activity, following `AGENTS.md` and the Activity skill. If `make verify` is the current local source gate in this checkout, run:

```bash
make verify
```

Do not invoke, inspect, rerun, or depend on GitHub-hosted Actions.

If any focused test or required local verification fails:

1. capture the exact command and complete failure;
2. identify the root cause;
3. make the smallest coherent fix;
4. rerun the failed focused gate;
5. rerun `python3 tools/build_encyclopedia_visual_assets.py --check` if source/build/runtime art was touched;
6. remember that later Simulator evidence must be from the final runtime-relevant source state.

Do not continue to visual acceptance with red tests.

---

# 5. Commit generated runtime art before Simulator acceptance

Refresh `main` again before the write:

```bash
git fetch origin
git status --short
git rev-parse HEAD
git rev-parse origin/main
```

If `origin/main` advanced, reconcile normally on `main`; do not create a feature branch and do not overwrite concurrent work.

Commit the six generated PNGs and only any necessary coherent fixes:

```bash
git add activities/enciclopedia_greia/assets/runtime/
git status --short
git commit -m "Encyclopedia: build golden-master runtime art"
git push origin main
```

Record the exact pushed SHA:

```bash
git rev-parse HEAD
```

Now rerun against the pushed final tree:

```bash
python3 tools/build_encyclopedia_visual_assets.py --check
python3 -m unittest \
  tests.test_activity_enciclopedia \
  tests.test_activity_enciclopedia_visual_foundation
```

The Simulator must test this final runtime-relevant SHA. If anything runtime-relevant changes afterward, restart Simulator acceptance from the beginning.

---

# 6. Real Greia Simulator launch gate

Use the real Simulator path documented by:

```text
docs/development/GREIA_ACTIVITY_SIMULATOR.md
skills/greia-activity-authoring/LAUNCH_ACCEPTANCE.md
```

Current canonical launcher is expected to be:

```bash
python3 tools/greia_simulator.py
```

Load the source Activity through **Load Activity Folder…**, not by manually copying files into simulator-managed storage.

Minimum launch gate:

```text
Activity appears in Greia launcher/catalogue
launch from Greia Shell
first usable frame appears
survive >= 10 seconds
perform meaningful interaction
remain alive afterward
internal Back works where applicable
protected Greia Home returns cleanly to Shell
```

Record the exact source SHA, locale/profile, viewport and result.

---

# 7. Golden-master visual evidence — only six prototypes

At minimum capture real Simulator pixels at **1024x600** for:

```text
Home
Animals section
Lion
Saturn
Gears
Pyramids
```

For Lion, Saturn, Gears and Pyramids capture:

```text
one clean initial state
one representative post-ACTIVATE state
```

The activated screenshot must prove that discovery interaction has a visible payoff, not merely that an audio cue fired.

Also capture a small responsive proof, not the full final matrix:

```text
one compact viewport/profile row
one larger viewport/profile row
```

Use representative prototypes rather than all 43 pages. Follow `VISUAL_ACCEPTANCE_EVIDENCE_CONTRACT.md` for evidence naming/classification.

Produce **one contact sheet** containing the six primary 1024x600 golden-master screens. If practical, also produce a second concise comparison sheet for the activated states/responsive samples. Do not generate giant redundant screenshot dumps.

Review the real pixels for:

```text
subject recognizability
composition/hierarchy
depth/material quality
palette/lighting coherence
discovery affordance clarity
interaction payoff
presenter integration
pre-reader first-action clarity
low-resolution legibility
Greia-family coherence
clipping/occlusion/protected-chrome conflicts
```

Do not call the direction accepted yourself. The owner is the aesthetic authority.

---

# 8. No-reading check

On the six prototypes, review as if the child cannot read:

```text
Can Home's first action be inferred from pictures/selection treatment?
Can Animals selection be understood without reading labels?
Are discovery tokens visibly actionable?
Does ACTIVATE produce understandable visual cause/effect?
Can the child return with internal Back / protected Home without prose?
```

Record:

```text
PRE_READER_CORE_FLOW_PASS=yes/no
TEXT_REQUIRED_FOR_GAMEPLAY=yes/no
NO_READING_FIRST_ACTION_PASS=yes/no
PRIMARY_INSTRUCTION_CHANNEL=visual/voice/combined
```

Do not use missing final narration as an excuse for unclear visuals; narration remains a separate acceptance lane.

---

# 9. Update continuation docs after evidence

After the final Simulator/evidence state, update truthfully:

```text
encyclopedia/HANDOVER.md
docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md
docs/plans/2026-08-28_ENCYCLOPEDIA_VISUAL_REAUTHORING.md
docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
HANDOVER.md
```

Append progress; do not rewrite old history to make experiments look cleaner.

Then commit/push the evidence/doc handoff on `main`.

---

# 10. STOP condition

After the six-prototype contact sheet and evidence are committed, **STOP**.

Do not start E3 or migrate another page.

Return to the owner/primary agent with:

```text
exact final Git SHA
six generated PNG paths and total bytes
build --check result
focused test results
local verification result
Simulator launch/survival result
interaction exercised
Back/Home result
1024x600 screenshot directory
responsive sample directory
contact-sheet path
pre-reader/no-reading result
any visual defects observed
anything still unverified
```

Current truthful state before this task executes:

```text
MECHANICAL 43-PAGE FOUNDATION: PREVIOUSLY PROVEN
OLD GRAPHICS PRODUCT TARGET: REJECTED
E1 SHARED PRESENTATION SOURCE: IMPLEMENTED ON MAIN
E2 SIX GOLDEN-MASTER PAGE SOURCES: IMPLEMENTED ON MAIN
EDITABLE SVG MASTERS: 6 / 6 ON MAIN
RUNTIME PNG PACK: BUILD/COMMIT PENDING
GENERATED-ART --CHECK GATE: IMPLEMENTED ON MAIN / EXECUTION PENDING ON REAL CHECKOUT
FOCUSED LOCAL REPO TESTS: PENDING ON REAL CHECKOUT
SIMULATOR FINAL-SHA ACCEPTANCE: PENDING
OWNER VISUAL DIRECTION APPROVAL: PENDING
E3/E4 BULK MIGRATION: BLOCKED
NARRATION ACCEPTANCE: SEPARATE / PENDING
```
