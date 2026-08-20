# V5 Shared Activity Card — Activity Simulator Acceptance

**Status:** required simulator protocol for the second visible Shell shared-visual consumer  
**Date:** 2026-08-20  
**Consumer:** `ui.card.activity`  
**Evidence class on success:** `SIMULATOR VISUAL REVIEW`

## Purpose

This protocol validates the first **substantial visible** shared UI artwork in the real Greia child Shell. It is not an isolated graphics demo. The Activity Simulator must run the real `GreiaChildShell` and the normal launcher catalogue/lifecycle.

The source implementation is:

```text
src/greia_launcher/shared_ui_presentation.py
src/greia_launcher/child_shell.py
```

The semantic runtime assets are:

```text
ui.card.activity/default
ui.card.activity/focused
```

The already accepted `ui.shadow.soft` remains available to the primitive fallback path.

## Hard rules

- all runtime/visual/interaction acceptance in this tranche is through the Greia Activity Simulator;
- no standalone Pygame harness;
- no browser mock screen;
- no simulator-specific production rendering branch;
- no runtime SVG rendering;
- no per-frame file decode/scale;
- no new launcher geometry forks by hard-coded resolution;
- missing/corrupt optional shared artwork must leave the launcher usable through the existing primitive tile renderer;
- do not claim physical Acer/Pi evidence or R7 closure.

## Before starting

```bash
git status --short
git branch --show-current
git fetch origin
git checkout main
git pull --ff-only origin main
git rev-parse HEAD
```

Record the start SHA.

Use isolated simulator state outside the checkout:

```bash
export GREIA_V5_CARD_SIM_STATE="$HOME/.greia-simulator-v5-card"
mkdir -p ./tmp/v5-card-simulator-evidence
export GREIA_V5_CARD_EVIDENCE="$PWD/tmp/v5-card-simulator-evidence"
```

Do not commit `tmp/` evidence.

## Start the simulator

```bash
python3 tools/greia_simulator.py --state-dir "$GREIA_V5_CARD_SIM_STATE"
```

Use the normal simulator control plane to select the required viewport/profile/interface-size combination and press **Start / Apply**.

The remote bridge is loopback-only:

```text
http://127.0.0.1:8767
```

## Baseline 1024×600 normal

Enter the Activity catalogue through the normal profile flow.

Capture:

```bash
python3 tools/greia_simulator_ctl.py status \
  > "$GREIA_V5_CARD_EVIDENCE/01-status-1024x600-normal.json"
python3 tools/greia_simulator_ctl.py screenshot \
  "$GREIA_V5_CARD_EVIDENCE/02-cards-1024x600-normal.png"
```

Required visible result:

- Activity tiles use the reviewed portrait shared card artwork instead of the old plain rectangular tile body;
- neutral tiles use `ui.card.activity/default`;
- selected/hovered tiles use the focused artwork with the stronger sunshine frame/star treatment;
- icons remain centered in the authored illustration well;
- titles remain centered in the authored lower label band;
- the shared card keeps its authored 360:430 aspect ratio and is not stretched into a square;
- the logical launcher hit target remains unchanged even though the artwork is portrait inside it;
- neighboring cards do not overlap;
- no clipping of card shadow/frame occurs;
- no text is hidden by the card artwork.

If the new card is not visibly present, do not call the test green just because the launcher still works. Find the root cause.

## Selection and hover

Use the simulator controls:

```bash
python3 tools/greia_simulator_ctl.py key RIGHT
python3 tools/greia_simulator_ctl.py screenshot \
  "$GREIA_V5_CARD_EVIDENCE/03-selected-right.png"
python3 tools/greia_simulator_ctl.py key LEFT
```

Move the pointer into a visible Activity hit target and capture the hover state:

```bash
python3 tools/greia_simulator_ctl.py move X Y
python3 tools/greia_simulator_ctl.py screenshot \
  "$GREIA_V5_CARD_EVIDENCE/04-hover.png"
```

Required:

- focus/hover changes the card to the focused shared variant;
- the existing hover lift remains subtle;
- the portrait card stays centered within its unchanged logical hit rectangle;
- no oscillation/flicker between default/focused variants;
- selection remains keyboard-visible even when the pointer is elsewhere.

## Launch motion/lifecycle

Launch one harmless built-in Activity through the normal catalogue:

```bash
python3 tools/greia_simulator_ctl.py key RETURN
```

Required:

- launch motion remains bounded and uses the shared focused card during the animation;
- no sudden fallback flash unless the shared asset actually fails;
- the Activity launches through the normal supervisor/lifecycle;
- returning to the launcher restores correct card states.

## Responsive simulator matrix

Run all rows:

```text
1024×600  + normal
1024×600  + large
1280×800  + normal
1366×768  + compact
1920×1080 + normal
1111×700  + normal
```

For each row:

1. apply viewport/interface size in the simulator control plane;
2. enter the Activity catalogue;
3. navigate at least two cards;
4. exercise one hover;
5. capture screenshot + status;
6. inspect card aspect, title fit, icon fit, spacing and hit alignment.

The shared card must remain portrait at every viewport. Do not add resolution-specific production branches to make screenshots pass.

## Fallback case 1 — missing generated catalogue

Stop the simulator, then temporarily move:

```bash
mv assets/catalog/shared_visuals_v1.toml \
   assets/catalog/shared_visuals_v1.toml.v5-card-disabled
```

Restart the simulator.

Required:

- launcher starts;
- Activity catalogue remains usable;
- primitive tile renderer is used;
- no crash/blank launcher;
- no source-art directory scanning.

Capture evidence, stop, then restore the exact catalogue.

## Fallback case 2 — malformed catalogue

Back up the generated catalogue, replace it temporarily with invalid TOML, then restart the simulator.

Required: same primitive fail-soft behavior.

Restore the exact good catalogue immediately after the case.

## Fallback case 3 — corrupt `ui.card.activity` PNG

With the simulator stopped, back up the exact runtime card PNG used by the `default` variant and replace it temporarily with invalid bytes. Restart the simulator.

Required:

- launcher remains usable;
- primitive tile renderer appears for the session;
- no repeated decode/error loop every frame;
- no crash;
- hit targets/navigation remain correct.

Restore the exact PNG immediately after the case.

Repeat for the focused card PNG only if the default-corruption case does not already exercise the relevant narrow error boundary.

## Frame sanity

At a stable Activity catalogue screen:

```bash
python3 tools/greia_simulator_ctl.py status \
  > "$GREIA_V5_CARD_EVIDENCE/frame-before.json"
sleep 10
python3 tools/greia_simulator_ctl.py status \
  > "$GREIA_V5_CARD_EVIDENCE/frame-after.json"
```

This is a gross regression check only. The simulator Shell targets about 30 fps. Look for obvious starvation, repeated stalls, or variant decode/scaling on every frame.

If performance regresses, inspect:

```text
PygameVisualSurfaceCache reuse
_tile_surface_cache reuse
stable card requested sizes
cache invalidation only on display-size changes
no per-frame filesystem work
```

Do not increase cache bounds blindly.

## PASS criteria

All must be true:

```text
shared portrait card visibly consumed in normal path
focused variant visibly consumed for selected/hovered/launching state
icon and title fit authored regions
logical hit geometry unchanged/aligned
6/6 viewport/interface rows visually correct
normal navigation PASS
hover PASS
launch lifecycle PASS
missing catalogue fallback PASS
malformed catalogue fallback PASS
corrupt card PNG fallback PASS
no obvious repeated-render stall
```

Record successful evidence as **SIMULATOR VISUAL REVIEW** only.

## On failure

Preserve the first failing screenshot/status and classify the root cause as one of:

```text
shared card source/rendition
catalogue mapping
PygameVisualSurfaceCache
SharedUiActivityCardMixin geometry
launcher tile cache interaction
fallback boundary
responsive geometry
```

Fix the smallest shared owner, rerun the exact failure, then rerun 1024×600 normal and any matrix rows affected by the change.

## Result report

Append the result to the project-local `LOCAL_AGENT_RESULT.md` or the current V5 simulator result file, including:

```text
START SHA
FINAL SHA
6-row matrix
selection/hover/launch results
fallback results
frame-count sanity
exact screenshot/status evidence paths
failures and fixes
explicit non-claims
```

Then update:

```text
docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md
HANDOVER.md
```

Commit and push accepted work to `main`.
