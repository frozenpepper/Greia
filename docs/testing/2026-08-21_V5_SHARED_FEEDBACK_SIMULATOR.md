# Greia V5 Shared Shell Feedback — Activity Simulator Acceptance

**Date:** 2026-08-21  
**Repository:** `frozenpepper/Greia`  
**Branch:** `main`  
**Evidence class:** `SIMULATOR VISUAL REVIEW` only  
**Execution rule:** all runtime/visual/fallback acceptance in this protocol runs through the Greia Activity Simulator.  
**Preferred mode:** headless (`GREIA_SIMULATOR_HEADLESS=1`) so validation does not steal desktop focus.

---

## 1. Scope

This gate validates the next visible shared-UI feedback tranche:

```text
ui.loading.orbit/default
ui.error.gentle/default
ui.empty.basket/default
```

Production consumers:

```text
src/greia_launcher/feedback_presentation.py
src/greia_launcher/child_shell.py
```

The launch overlay is the primary visible acceptance target. Error and empty-state visuals must remain fail-soft and may only be promoted beyond SOURCE when their real Shell state is actually exercised in this protocol.

Do not modify Activity lifecycle, catalogue authority, profile authority, permissions, or protected Home/Back semantics to make a screenshot pass.

---

## 2. Sync and generation

From the Greia checkout:

```bash
git status --short
git fetch origin
git checkout main
git pull --ff-only origin main
git rev-parse HEAD
```

Record the starting SHA.

Generate the newly selected PNG renditions:

```bash
make visual-assets
```

This is a build step, not acceptance evidence.

Confirm these generated files exist:

```text
assets/visual/runtime/v1/ui/loading_orbit.png
assets/visual/runtime/v1/ui/error_cloud.png
assets/visual/runtime/v1/ui/empty_basket.png
```

and that `assets/catalog/shared_visuals_v1.toml` contains:

```text
ui.loading.orbit
ui.error.gentle
ui.empty.basket
```

Do not hand-edit the generated runtime catalogue.

---

## 3. Isolated non-intrusive simulator

Use an isolated state root and project-local evidence directory:

```bash
export GREIA_V5_STATE="$HOME/.greia-simulator-v5-feedback"
export GREIA_V5_EVIDENCE="$PWD/tmp/v5-feedback-simulator-evidence"
mkdir -p "$GREIA_V5_EVIDENCE"
```

Start the real Activity Simulator in the user-requested non-intrusive headless mode:

```bash
GREIA_SIMULATOR_HEADLESS=1 \
python3 tools/greia_simulator.py \
  --state-dir "$GREIA_V5_STATE"
```

The remote bridge remains loopback-only at:

```text
http://127.0.0.1:8767
```

Headless mode must still run the real `GreiaChildShell` and real simulator lifecycle/service composition. It is not permission to add a simulator-only visual renderer.

---

## 4. Baseline regression check

Set:

```text
1024x600 + normal
```

Enter the Activity catalogue and capture:

```bash
python3 tools/greia_simulator_ctl.py status \
  > "$GREIA_V5_EVIDENCE/01-status.json"
python3 tools/greia_simulator_ctl.py screenshot \
  "$GREIA_V5_EVIDENCE/01-catalogue.png"
```

Confirm the already accepted visible system remains intact:

```text
maximized ui.panel.base tray
large Activity cards
shared category buttons
shared profile identity frame
correct hit geometry
```

A regression here is a FAIL before feedback-state testing.

---

## 5. Launch overlay — required visible acceptance

Select a safe built-in Activity.

The overlay may be brief, so capture a rapid burst while the normal launch lifecycle is starting. Do not insert production sleeps or simulator-specific launch delays.

Example:

```bash
(
  for n in 01 02 03 04 05 06 07 08; do
    python3 tools/greia_simulator_ctl.py screenshot \
      "$GREIA_V5_EVIDENCE/10-launch-$n.png" >/dev/null 2>&1 || true
    sleep 0.04
  done
) &
CAPTURE_PID=$!

python3 tools/greia_simulator_ctl.py key RETURN
wait "$CAPTURE_PID" || true
```

Inspect the burst and retain the clearest frame that actually contains the launch overlay.

Required result:

- `ui.loading.orbit` is visible and centered;
- the overlay remains calm and child-friendly rather than looking like generic desktop progress chrome;
- the launch text remains readable at current interface size;
- no card/category/profile controls remain visually actionable underneath;
- normal Activity launch still completes;
- returning Home still restores the same accepted Shell composition;
- no runtime SVG work occurs.

If the selected Activity becomes READY too quickly to capture the overlay, use another trusted built-in Activity with naturally longer startup. Do **not** alter production timing to make this test easier.

Capture the returned Shell:

```bash
python3 tools/greia_simulator_ctl.py screenshot \
  "$GREIA_V5_EVIDENCE/11-returned-home.png"
```

---

## 6. Launch-overlay fail-soft isolation

Stop the simulator cleanly.

Back up and corrupt only:

```text
assets/visual/runtime/v1/ui/loading_orbit.png
```

Restart headless simulator using the same state root.

Launch the same Activity.

Required result:

- Shell does not crash;
- Activity lifecycle remains normal;
- the existing primitive launch overlay is used;
- already accepted panel/cards/buttons/avatar frame remain active after return Home;
- no repeated decode/error loop appears.

Capture one fallback launch frame if timing permits and the returned Shell.

Restore the exact generated PNG before continuing.

---

## 7. Error-state acceptance

Exercise the real launcher's catalogue-error state without modifying production source.

With the simulator running, create one deliberately malformed developer Activity directly inside the **isolated simulator state root**, never inside the repository:

```bash
mkdir -p "$GREIA_V5_STATE/developer-activities/_feedback-invalid"
printf 'this is not valid toml = [\n' \
  > "$GREIA_V5_STATE/developer-activities/_feedback-invalid/activity.toml"
```

Wait at least one normal rescan interval, then capture:

```bash
sleep 3
python3 tools/greia_simulator_ctl.py screenshot \
  "$GREIA_V5_EVIDENCE/20-error-cloud.png"
```

Required result:

- real Shell stays usable with last-known-good Activity catalogue;
- `ui.error.gentle` appears as the error/dismiss affordance;
- the error state does not occlude category controls or Activity cards excessively;
- clicking/tapping the error affordance dismisses the visible error state according to existing launcher semantics;
- no lifecycle/catalogue authority is moved into the visual mixin.

Remove the malformed simulator-only directory:

```bash
rm -rf "$GREIA_V5_STATE/developer-activities/_feedback-invalid"
```

Allow the normal rescan to recover.

### Error visual corrupt-PNG isolation

Stop the simulator, corrupt only `assets/visual/runtime/v1/ui/error_cloud.png`, restart, recreate the malformed simulator-state Activity above, and verify the existing primitive error affordance appears instead.

Restore the PNG and remove the malformed simulator directory immediately after the case.

---

## 8. Empty state

`ui.empty.basket` is implemented only for the genuine empty Activity catalogue state.

Do **not** fake this by hiding normal Activities with production source edits, by adding a simulator identity branch, or by changing child audience policy solely for the screenshot.

If the current simulator/profile configuration already provides a legitimate way to reach a profile with zero presented Activities through ordinary Greia policy, exercise it and capture:

```text
30-empty-basket.png
```

Required result if exercised:

- basket is centered and readable at low resolution;
- no misleading boot logo is shown as the Activity-empty state;
- protected navigation remains reachable;
- fallback to the existing empty renderer works when `empty_basket.png` is corrupt/missing.

If no legitimate current state can reach an empty Activity catalogue, record this asset consumer as **SOURCE, NOT EXERCISED**. Do not manufacture acceptance evidence.

---

## 9. Responsive launch-overlay matrix

Exercise the launch overlay at minimum on:

```text
1024×600  + normal
1024×600  + large
1366×768  + compact
1920×1080 + normal
```

For each:

1. restart/apply the simulator viewport/interface size;
2. enter Activity catalogue;
3. trigger a normal Activity launch;
4. capture a launch-overlay burst;
5. return Home;
6. verify the accepted Shell composition remains intact.

The orbit must remain proportionate and centered. Do not add per-resolution branches.

---

## 10. Frame sanity

On the stable Activity catalogue after the feedback tests:

```bash
python3 tools/greia_simulator_ctl.py status \
  > "$GREIA_V5_EVIDENCE/frame-before.json"
sleep 10
python3 tools/greia_simulator_ctl.py status \
  > "$GREIA_V5_EVIDENCE/frame-after.json"
```

Record frame delta and elapsed time.

This is simulator sanity only, not physical low-resource performance evidence.

---

## 11. Required result report

Update `LOCAL_AGENT_RESULT.md` with:

```text
START SHA
FINAL SHA
GENERATED RENDITIONS
LAUNCH OVERLAY RESULT
LOADING PNG FALLBACK RESULT
ERROR CLOUD RESULT
ERROR PNG FALLBACK RESULT
EMPTY STATE: PASS / SOURCE-NOT-EXERCISED
RESPONSIVE OVERLAY MATRIX
FRAME SANITY
HEADLESS MODE CONFIRMATION
EVIDENCE PATHS
FILES CHANGED
COMMITS
EXPLICIT NON-CLAIMS
```

Update in the same accepted tranche:

```text
docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md
HANDOVER.md
```

Also update `docs/development/GREIA_ACTIVITY_SIMULATOR.md` if any headless behavior or procedure had to be corrected during this run.

Commit and push accepted work to `main`.

Do not use GitHub Actions for this owner-directed visual acceptance.
