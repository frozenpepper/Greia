# Greia V5 — Activity Shared Visual Simulator Protocol

**Date:** 2026-08-20  
**Phase:** V5 shared consumption/integration  
**Target:** first Python Activity semantic shared-visual consumer  
**Activity:** `shape_garden`  
**Semantic visual:** `ui.shadow.soft`  
**Evidence class if passed:** `SIMULATOR VISUAL REVIEW`

---

# 1. Purpose

Validate the first Activity-facing shared visual path through the real Greia Activity Simulator.

The source seam under test is:

```text
Activity calls get_shared_visual_path("ui.shadow.soft")
→ activity_api loads explicit core + optional generated visual catalogue
→ semantic ID resolves to generated PNG
→ Shape Garden decodes/scales the PNG once at Activity startup
→ the prepared shadow surface is reused while drawing shapes
```

This is deliberately a small first seam. It must prove semantic reuse without introducing a second asset catalogue/cache framework.

---

# 2. Owner testing rule

For this tranche, runtime/visual/fallback/responsive acceptance is performed through the **Greia Activity Simulator**.

Do not use these as PASS evidence:

```bash
pytest
python -m unittest
make test
make verify
GitHub Actions
```

Build generation such as `make visual-assets` may run as a prerequisite. It is not simulator PASS evidence.

The simulator bridge is local loopback only. No Cloudflare/tunnel/hosted service is involved.

---

# 3. Read before executing

Read:

```text
AGENTS.md
docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md
docs/development/GREIA_ACTIVITY_SIMULATOR.md
src/greia_platform/activity_api.py
activities/shape_garden/main.py
assets/catalog/shared_visuals_v1.toml
```

---

# 4. Sync and record starting state

```bash
git status --short
git checkout main
git pull --ff-only origin main
git rev-parse HEAD
```

Do not discard unknown local changes.

Create disposable evidence storage:

```bash
mkdir -p ./tmp/v5-activity-shared-visual-evidence
export GREIA_V5_ACTIVITY_EVIDENCE="$PWD/tmp/v5-activity-shared-visual-evidence"
export GREIA_V5_ACTIVITY_SIM_STATE="$HOME/.greia-simulator-v5-activity-visual"
```

Do not commit `tmp/` evidence.

---

# 5. Build prerequisite

Confirm the generated shared visual catalogue and PNG exist.

```bash
test -f assets/catalog/shared_visuals_v1.toml
test -f assets/visual/runtime/v1/ui/soft_shadow.png
```

If missing/stale and the host has librsvg:

```bash
make visual-assets
```

Do not hand-write the generated catalogue.

---

# 6. Start simulator

```bash
python3 tools/greia_simulator.py \
  --state-dir "$GREIA_V5_ACTIVITY_SIM_STATE"
```

Use the real Greia Shell inside the simulator. Launch **Shape Garden** through the normal Activity catalogue.

---

# 7. Baseline semantic-consumption case

Start at:

```text
1024×600
interface size: normal
```

Launch Shape Garden.

Create at least 8 shapes at different positions and with multiple sizes.

Expected visual behavior:

- each shape receives a restrained soft grounding shadow;
- shadow is visually subordinate to the shape;
- shadow does not obscure the shape;
- no repeated flicker or delayed loading after the first Activity startup;
- Home remains functional;
- Activity remains responsive.

Capture:

```bash
python3 tools/greia_simulator_ctl.py status \
  | tee "$GREIA_V5_ACTIVITY_EVIDENCE/01-baseline-status.json"

python3 tools/greia_simulator_ctl.py screenshot \
  "$GREIA_V5_ACTIVITY_EVIDENCE/02-shape-garden-shared-shadow.png"
```

---

# 8. Interaction sanity

Create shapes by mouse/touch-equivalent pointer interaction at:

- upper-left safe area;
- center;
- upper-right safe area;
- near the soil boundary without entering protected platform UI.

Expected:

- pointer mapping remains correct;
- protected Home region remains protected;
- no shared visual affects hit geometry;
- Activity stop/Home lifecycle remains correct.

Return Home through the normal Greia control, then relaunch Shape Garden once.

Expected on relaunch:

- shared visual loads normally;
- no stale previous Activity state leaks through the visual resolver.

---

# 9. Missing generated catalogue fallback

Stop the simulator before changing prerequisites.

Temporarily move:

```bash
mv assets/catalog/shared_visuals_v1.toml \
   assets/catalog/shared_visuals_v1.toml.v5-activity-disabled
```

Restart the simulator and launch Shape Garden.

Expected:

- Shape Garden starts;
- shapes remain fully playable;
- shared shadows are absent;
- no crash;
- no error loop;
- core icon/platform behavior still works.

Capture:

```bash
python3 tools/greia_simulator_ctl.py screenshot \
  "$GREIA_V5_ACTIVITY_EVIDENCE/10-fallback-missing-catalogue.png"
```

Stop simulator and restore immediately:

```bash
mv assets/catalog/shared_visuals_v1.toml.v5-activity-disabled \
   assets/catalog/shared_visuals_v1.toml
```

---

# 10. Malformed generated catalogue fallback

With simulator stopped:

```bash
cp assets/catalog/shared_visuals_v1.toml \
   "$GREIA_V5_ACTIVITY_EVIDENCE/shared_visuals_v1.good.toml"

printf 'not valid toml = [\n' > assets/catalog/shared_visuals_v1.toml
```

Restart simulator and launch Shape Garden.

Expected:

- Activity starts;
- shapes remain playable;
- no shared shadow;
- no crash/error loop.

Capture:

```bash
python3 tools/greia_simulator_ctl.py screenshot \
  "$GREIA_V5_ACTIVITY_EVIDENCE/11-fallback-malformed-catalogue.png"
```

Stop simulator and restore:

```bash
cp "$GREIA_V5_ACTIVITY_EVIDENCE/shared_visuals_v1.good.toml" \
   assets/catalog/shared_visuals_v1.toml
```

---

# 11. Corrupt PNG fallback

With simulator stopped, identify the exact generated file referenced by `ui.shadow.soft/default` and back it up.

For the current catalogue it is:

```text
assets/visual/runtime/v1/ui/soft_shadow.png
```

Back up then replace temporarily with invalid bytes.

Restart simulator and launch Shape Garden.

Expected:

- Activity starts;
- shapes remain playable;
- shared shadows are absent;
- no crash/error loop.

Restore the exact good PNG immediately after the case.

Capture:

```bash
python3 tools/greia_simulator_ctl.py screenshot \
  "$GREIA_V5_ACTIVITY_EVIDENCE/12-fallback-corrupt-png.png"
```

---

# 12. Responsive simulator matrix

Exercise Shape Garden through the simulator at:

```text
1024×600  + normal
1024×600  + large
1280×800  + normal
1366×768  + compact
1920×1080 + normal
1111×700  + normal
```

For each row:

1. apply viewport/interface size in simulator;
2. launch Shape Garden;
3. create at least 5 shapes across the safe area;
4. inspect shared-shadow alignment;
5. use Home and relaunch once on at least two rows;
6. capture screenshot + status.

Acceptance:

- canvas transform remains correct;
- shared shadow stays attached to the logical shape position;
- no resolution-specific source branch is needed;
- protected platform UI remains aligned;
- no clipping introduced by the shared visual;
- Activity remains responsive.

---

# 13. Frame sanity

At a stable Shape Garden scene containing at least 30 shapes:

```bash
python3 tools/greia_simulator_ctl.py status \
  > "$GREIA_V5_ACTIVITY_EVIDENCE/frame-before.json"

sleep 10

python3 tools/greia_simulator_ctl.py status \
  > "$GREIA_V5_ACTIVITY_EVIDENCE/frame-after.json"
```

Record frame-count delta and elapsed time.

This is a gross simulator regression check, not physical Acer/Pi performance evidence.

Look for:

- obvious periodic stalls;
- progressively worsening frame rate as shapes are added;
- visible per-frame image loading/flicker.

The source contract should show the PNG is loaded/scaled once at Activity startup, not from the draw loop.

---

# 14. Hard failure conditions

Stop and report rather than improvising if the fix would require:

- runtime SVG rendering;
- Activity source-directory scanning;
- a second global asset catalogue;
- a second generic shared-image cache architecture;
- simulator-specific production branches;
- per-resolution hard-coded forks;
- broad `except Exception` around the Activity frame/render loop;
- exposing arbitrary host paths supplied by the Activity;
- removing Activity-private asset support.

---

# 15. Acceptance gate

The first Python Activity shared-visual seam passes when:

```text
semantic ui.shadow.soft resolves in Shape Garden
shared rendition is visibly reused in Activity rendering
missing catalogue fallback PASS
malformed catalogue fallback PASS
corrupt PNG fallback PASS
Home/input lifecycle PASS
full responsive matrix PASS
frame sanity shows no gross regression
```

Evidence label:

```text
SIMULATOR VISUAL REVIEW
```

Do not claim:

- Web Activity semantic support;
- physical low-resource performance;
- release-art approval;
- R7 closure.

---

# 16. Required result update

Append the simulator result to the visual plan and update:

```text
docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md
HANDOVER.md
```

If the Activity semantic API changes, also update:

```text
docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
```

Commit and push coherent accepted work to `main`.
