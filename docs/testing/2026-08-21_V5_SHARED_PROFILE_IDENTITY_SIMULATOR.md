# Greia V5 Shared Profile Identity Frame — Activity Simulator Acceptance

**Date:** 2026-08-21  
**Repository:** `frozenpepper/Greia`  
**Branch:** `main`  
**Consumer:** `ui.avatar.frame/default`  
**Testing authority:** Greia Activity Simulator only

This protocol validates the next visible shared-UI tranche: the reviewed shared avatar frame around child identity in both the profile picker and the active-profile switcher in the Activity catalogue.

Do not use direct pytest/unittest/make-verify output as acceptance evidence for this tranche. Build-time rendition generation is allowed; runtime/visual/fallback/responsive acceptance must happen through the Activity Simulator.

---

## 1. Sync current main

```bash
git status --short
git fetch origin
git checkout main
git pull --ff-only origin main
git rev-parse HEAD
```

Do not discard unknown owner work and do not force-push.

---

## 2. Read the current visual authorities

Read:

```text
AGENTS.md
docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md
src/greia_launcher/profile_chrome_presentation.py
src/greia_launcher/child_shell.py
assets/catalog/shared_visuals_v1_source.toml
assets/visual/ui/v0.1/avatar_frame.svg
```

The new source semantic ID is:

```text
ui.avatar.frame/default
```

Expected generated runtime path:

```text
assets/visual/runtime/v1/ui/avatar_frame.png
```

---

## 3. Build the explicit runtime rendition

The source manifest changed, so regenerate the explicit runtime catalogue/renditions before simulator acceptance:

```bash
command -v rsvg-convert
make visual-assets
```

If `rsvg-convert` is absent on macOS, install `librsvg` using the existing project/build-host procedure.

This is a build prerequisite, not acceptance evidence.

Inspect that the generated catalogue now contains `ui.avatar.frame/default` and that `avatar_frame.png` exists. Do not manually fabricate the generated catalogue or PNG.

---

## 4. Evidence locations

Simulator state must remain outside the checkout:

```bash
export GREIA_V5_SIM_STATE="$HOME/.greia-simulator-v5-profile"
```

Local evidence remains disposable/project-local:

```bash
mkdir -p ./tmp/v5-profile-simulator-evidence
export GREIA_V5_EVIDENCE="$PWD/tmp/v5-profile-simulator-evidence"
```

Do not commit `tmp/` evidence and do not ZIP it unless explicitly requested.

---

## 5. Start the real Activity Simulator

```bash
python3 tools/greia_simulator.py --state-dir "$GREIA_V5_SIM_STATE"
```

Use the simulator control plane at loopback only:

```text
http://127.0.0.1:8767
```

No Cloudflare, tunnel or hosted service belongs in this workflow.

Start at:

```text
1024×600
normal interface size
```

---

## 6. Profile picker baseline

Capture simulator status and screenshot while the real child Shell shows the profile picker:

```bash
python3 tools/greia_simulator_ctl.py status \
  | tee "$GREIA_V5_EVIDENCE/01-status-profile.json"
python3 tools/greia_simulator_ctl.py screenshot \
  "$GREIA_V5_EVIDENCE/01-profile-frame-1024x600.png"
```

Acceptance:

- the shared yellow/storybook avatar frame is visibly present around each visible child avatar;
- the avatar is centered inside the authored inner well rather than over the decorative stars/border;
- the child's name remains unobscured;
- selected-profile outline remains readable;
- profile hit rectangles and keyboard selection are unchanged;
- no frame overlaps adjacent profile cards;
- no clipped frame/shadow at 1024×600.

If the frame looks too large/small/misaligned, fix the shared profile presentation geometry, not the source asset blindly.

---

## 7. Profile selection / Activity catalogue identity

Select a profile normally and enter the Activity catalogue.

Capture:

```bash
python3 tools/greia_simulator_ctl.py screenshot \
  "$GREIA_V5_EVIDENCE/02-active-profile-frame.png"
```

Acceptance:

- the top-left active-profile switcher uses the same `ui.avatar.frame` visual language;
- the avatar remains centered in the frame;
- the switch-profile hit rectangle still behaves normally;
- category buttons, shared panel and shared Activity cards remain visually intact;
- frame treatment is subordinate to the catalogue and does not crowd the category row.

Click/tap the active-profile switcher and verify it returns to the profile picker through the normal Shell lifecycle.

Capture:

```bash
python3 tools/greia_simulator_ctl.py screenshot \
  "$GREIA_V5_EVIDENCE/03-returned-profile-picker.png"
```

---

## 8. Fail-soft cases

Stop the simulator cleanly before changing generated prerequisites.

### 8.1 Missing generated catalogue

Temporarily move `assets/catalog/shared_visuals_v1.toml` aside, restart simulator, and verify:

- profile picker remains usable with the previous primitive identity treatment;
- Activity catalogue remains usable;
- no crash or retry loop.

Capture:

```text
10-fallback-missing-catalogue-profile.png
10-fallback-missing-catalogue-activities.png
```

Restore the catalogue immediately.

### 8.2 Malformed generated catalogue

Back up the generated catalogue, replace it temporarily with malformed TOML, restart simulator, and verify the same fail-soft behavior.

Capture:

```text
11-fallback-malformed-catalogue.png
```

Restore the exact good catalogue immediately.

### 8.3 Corrupt avatar-frame PNG

Back up:

```text
assets/visual/runtime/v1/ui/avatar_frame.png
```

Replace it temporarily with invalid bytes and restart simulator.

Required result:

- profile identity falls back to the existing primitive treatment;
- already-accepted `ui.panel.base`, `ui.card.activity`, and `ui.button.primary` remain active;
- no crash, repeated decode loop, or full shared-visual shutdown caused solely by this frame failure.

Capture both profile picker and Activity catalogue:

```text
12-fallback-corrupt-avatar-profile.png
12-fallback-corrupt-avatar-activities.png
```

Restore the exact generated PNG immediately.

If corrupt avatar-frame handling disables unrelated panel/card/button artwork, treat that as a FAIL and narrow the profile-frame error isolation before continuing.

---

## 9. Responsive simulator matrix

Run these through the Activity Simulator:

```text
1024×600  + normal
1024×600  + large
1280×800  + normal
1366×768  + compact
1920×1080 + normal
1111×700  + normal
```

For every row capture the profile picker. For at least 1024×600, 1366×768 and 1920×1080 also capture the Activity catalogue active-profile frame.

Suggested names:

```text
20-1024x600-normal-profile.png
20-1024x600-normal-activities.png
21-1024x600-large-profile.png
22-1280x800-normal-profile.png
23-1366x768-compact-profile.png
23-1366x768-compact-activities.png
24-1920x1080-normal-profile.png
24-1920x1080-normal-activities.png
25-1111x700-normal-profile.png
```

Acceptance:

- authored circular frame remains proportionate;
- frame and avatar remain centered;
- names remain readable;
- selected profile remains obvious;
- top-left active frame does not collide with category buttons;
- no resolution-specific source branches are introduced.

---

## 10. Performance sanity

At a stable profile picker or Activity catalogue screen:

```bash
python3 tools/greia_simulator_ctl.py status > "$GREIA_V5_EVIDENCE/frame-before.json"
sleep 10
python3 tools/greia_simulator_ctl.py status > "$GREIA_V5_EVIDENCE/frame-after.json"
```

Record frame-count delta. This is only a regression sanity check against Greia's ~30 FPS simulator clock; do not convert it into physical Acer performance evidence.

The source architecture must still show that avatar-frame PNG load/scale is served by `PygameVisualSurfaceCache`, not decoded from disk every frame.

---

## 11. Fix policy

On failure:

1. preserve the first failing screenshot/status;
2. classify whether the problem is source rendition, generated catalogue, profile-frame placement, cache/fallback isolation, responsive geometry, or simulator behavior;
3. fix the smallest shared owner;
4. rerun the failed simulator case;
5. rerun 1024×600 normal;
6. rerun the responsive rows if geometry changed.

Do not:

- add per-resolution forks;
- add a second image cache;
- rasterize SVG at runtime;
- hide failures with broad exception swallowing;
- replace the shared frame with a primitive because integration is inconvenient;
- redesign the profile system or Activity lifecycle during this visual tranche.

---

## 12. Acceptance boundary

This tranche is accepted only when:

```text
profile picker shared avatar frames visible and coherent
active-profile switcher shared frame visible and coherent
profile selection/switch lifecycle unchanged
missing catalogue fallback PASS
malformed catalogue fallback PASS
corrupt avatar-frame PNG isolated fallback PASS
existing panel/card/button consumers remain active during frame-only failure
responsive matrix PASS
frame sanity PASS
```

Evidence label:

```text
SIMULATOR VISUAL REVIEW
```

Do not claim physical hardware performance, R7 closure, or blanket release-art approval.

---

## 13. Finish

Update:

```text
LOCAL_AGENT_RESULT.md
docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md
HANDOVER.md
```

Record the generated `avatar_frame.png` and updated generated catalogue in the commit.

Commit coherent accepted work and push `main` without force.

Return the final SHA plus the simulator matrix/result summary.
