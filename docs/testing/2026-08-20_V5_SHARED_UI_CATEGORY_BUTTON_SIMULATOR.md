# Greia V5 Shared Category Buttons — Activity Simulator Acceptance

**Date:** 2026-08-20  
**Repository:** `frozenpepper/Greia`  
**Branch:** `main`  
**Evidence class:** `SIMULATOR VISUAL REVIEW`  
**Testing authority:** Greia Activity Simulator only for this tranche

---

# 1. Purpose

Validate the next visible shared Greia UI consumer in the real production child Shell:

```text
ui.button.primary/default
ui.button.primary/hover
```

The consumer is the **root Activity-category button row** in the normal Activity catalogue.

This is not a category-system redesign. The existing category IDs, ordering, hit targets, category navigation, in-category Back control, Activity catalogue, Activity cards, shared panel, launch lifecycle and responsive geometry remain authoritative.

The expected stack is now:

```text
ui.panel.base
  + ui.card.activity
  + ui.button.primary on root category controls
```

The in-category Back/header control remains on the existing renderer because its geometry does not match the reviewed wide primary-button artwork.

---

# 2. Source under test

Read before running:

```text
src/greia_launcher/shared_ui_presentation.py
src/greia_launcher/child_shell.py
src/greia_launcher/presentation.py
assets/catalog/shared_visuals_v1.toml
assets/visual/ui/v0.1/button_primary.svg
assets/visual/ui/v0.1/button_primary_hover.svg
assets/visual/ui/v0.1/button_primary_pressed.svg
assets/visual/ui/v0.1/button_disabled.svg
```

Expected implementation owner:

```text
SharedUiCategoryButtonMixin
```

Expected production composition:

```text
GreiaChildShell(
    SharedUiCategoryButtonMixin,
    SharedUiShellPanelMixin,
    SharedUiActivityCardMixin,
    GreiaLauncherPresentation,
)
```

---

# 3. Hard rules

All runtime, interaction, responsive, fallback and visual acceptance for this tranche must be performed through the Greia Activity Simulator.

Do not use GitHub Actions.

Do not create a standalone Pygame screenshot harness.

Do not add simulator-only branches to production Shell code.

Do not alter the category model or category IDs merely to make the shared button fit.

Do not stretch the work into another UI redesign.

Do not change Activity tile/card geometry in this tranche.

Do not replace `ui.panel.base` or `ui.card.activity` while validating buttons.

---

# 4. Synchronize and evidence directories

From the Greia checkout:

```bash
git status --short
git fetch origin
git checkout main
git pull --ff-only origin main
git rev-parse HEAD
```

Record the starting SHA.

Simulator state:

```bash
export GREIA_V5_BUTTON_SIM_STATE="$HOME/.greia-simulator-v5-button"
```

Project-local disposable evidence:

```bash
mkdir -p ./tmp/v5-button-simulator-evidence
export GREIA_V5_BUTTON_EVIDENCE="$PWD/tmp/v5-button-simulator-evidence"
```

Do not commit `tmp/` evidence.

---

# 5. Start the real Activity Simulator

```bash
python3 tools/greia_simulator.py \
  --state-dir "$GREIA_V5_BUTTON_SIM_STATE"
```

Set:

```text
Viewport: 1024x600
Interface size: normal
```

Click **Start / Apply**.

Enter the normal child profile and reach the root Activity catalogue.

The Shell displayed by the simulator must be the real `GreiaChildShell`.

---

# 6. Baseline shared-button acceptance

Capture status:

```bash
python3 tools/greia_simulator_ctl.py status \
  | tee "$GREIA_V5_BUTTON_EVIDENCE/01-status-1024x600-normal.json"
```

Capture screenshot:

```bash
python3 tools/greia_simulator_ctl.py screenshot \
  "$GREIA_V5_BUTTON_EVIDENCE/02-buttons-1024x600-normal.png"
```

PASS requires all of the following:

- root Activity categories use the shared yellow primary-button artwork;
- category icon and localized label remain centered/readable;
- buttons remain visually subordinate to Activity cards;
- the shared panel remains visible behind catalogue content;
- no label is clipped by the button artwork;
- no category control overlaps its neighbor;
- buttons do not overlap the active-profile badge or error badge region;
- logical hit targets remain exactly the existing category rectangles;
- no raw primitive button rectangle is visible underneath the shared rendition;
- Activity cards remain unchanged from the already-accepted card integration.

If the reviewed button artwork looks poor when used as a category control, record that as a visual-integration failure. Do not hide it by changing category semantics.

---

# 7. Hover variant

Move the synthetic pointer into one visible category control:

```bash
python3 tools/greia_simulator_ctl.py move X Y
```

Use actual coordinates from the screenshot rather than guessing blindly.

Capture:

```bash
python3 tools/greia_simulator_ctl.py screenshot \
  "$GREIA_V5_BUTTON_EVIDENCE/03-button-hover.png"
```

PASS requires:

- only the hovered category uses `ui.button.primary/hover`;
- hover change is clearly visible but not visually violent;
- icon and label do not shift unexpectedly;
- pointer remains aligned with the hit target;
- other category buttons stay on `default`;
- cards/panel remain unchanged.

---

# 8. Category navigation lifecycle

Click the hovered category using the simulator.

PASS requires:

- correct category opens;
- Activity cards filter through the existing catalogue authority;
- the existing in-category header/back control appears;
- the wide shared primary button is **not** stretched into the Back control;
- Activity launch/navigation authority is unchanged.

Capture:

```bash
python3 tools/greia_simulator_ctl.py screenshot \
  "$GREIA_V5_BUTTON_EVIDENCE/04-category-open.png"
```

Use the normal Back control to return to All Activities.

Capture:

```bash
python3 tools/greia_simulator_ctl.py screenshot \
  "$GREIA_V5_BUTTON_EVIDENCE/05-category-returned.png"
```

PASS requires the root shared category-button row to return correctly.

---

# 9. Launch and return Home regression

Launch one harmless first-party Activity from the catalogue and return through normal Greia Home/lifecycle behavior.

Capture after return:

```bash
python3 tools/greia_simulator_ctl.py screenshot \
  "$GREIA_V5_BUTTON_EVIDENCE/06-returned-home.png"
```

PASS requires:

- launcher remains functional;
- shared panel remains active;
- shared Activity cards remain active;
- shared category buttons remain active;
- no duplicated/stale target row appears after return.

---

# 10. Fail-soft: missing generated catalogue

Stop simulator.

Temporarily rename:

```bash
mv assets/catalog/shared_visuals_v1.toml \
   assets/catalog/shared_visuals_v1.toml.v5-disabled
```

Restart simulator and reach Activity catalogue.

Capture:

```bash
python3 tools/greia_simulator_ctl.py screenshot \
  "$GREIA_V5_BUTTON_EVIDENCE/10-fallback-missing-catalogue.png"
```

PASS requires the proven base visual fallback:

- Shell usable;
- primitive category controls render;
- primitive cards/background path may render because the whole optional shared catalogue is absent;
- no crash or retry loop.

Stop simulator and restore:

```bash
mv assets/catalog/shared_visuals_v1.toml.v5-disabled \
   assets/catalog/shared_visuals_v1.toml
```

---

# 11. Fail-soft: malformed generated catalogue

Stop simulator.

```bash
cp assets/catalog/shared_visuals_v1.toml \
   "$GREIA_V5_BUTTON_EVIDENCE/shared_visuals_v1.good.toml"
printf 'not valid toml = [\n' > assets/catalog/shared_visuals_v1.toml
```

Restart and reach Activity catalogue.

Capture:

```bash
python3 tools/greia_simulator_ctl.py screenshot \
  "$GREIA_V5_BUTTON_EVIDENCE/11-fallback-malformed-catalogue.png"
```

PASS requires clean base fallback with no crash.

Restore immediately:

```bash
cp "$GREIA_V5_BUTTON_EVIDENCE/shared_visuals_v1.good.toml" \
   assets/catalog/shared_visuals_v1.toml
```

---

# 12. Isolated fail-soft: corrupt hover-button PNG

This case is important because the panel and cards must remain alive while only the category-button treatment falls back.

Stop simulator.

Resolve the generated hover PNG from `assets/catalog/shared_visuals_v1.toml` and back it up. Current expected path:

```text
assets/visual/runtime/v1/ui/button_primary_hover.png
```

Example:

```bash
cp assets/visual/runtime/v1/ui/button_primary_hover.png \
   "$GREIA_V5_BUTTON_EVIDENCE/button_primary_hover.good.png"
printf 'broken png' > assets/visual/runtime/v1/ui/button_primary_hover.png
```

Restart simulator and reach the root Activity catalogue.

First confirm default shared category buttons still render. Then move the pointer onto a category control to force `hover` resolution.

Capture:

```bash
python3 tools/greia_simulator_ctl.py screenshot \
  "$GREIA_V5_BUTTON_EVIDENCE/12-fallback-corrupt-hover-button.png"
```

PASS requires:

- Shell does not crash;
- category row falls back to the proven primitive category renderer;
- `ui.panel.base` **remains active**;
- `ui.card.activity` **remains active**;
- there is no repeated decode/error loop every frame;
- category hit targets/navigation still work.

Stop simulator and restore the exact good PNG:

```bash
cp "$GREIA_V5_BUTTON_EVIDENCE/button_primary_hover.good.png" \
   assets/visual/runtime/v1/ui/button_primary_hover.png
```

---

# 13. Responsive simulator matrix

Run the root Activity catalogue at:

```text
1024×600  + normal
1024×600  + large
1280×800  + normal
1366×768  + compact
1920×1080 + normal
1111×700  + normal
```

For every row:

1. set viewport/interface size in simulator control plane;
2. Start / Apply or Restart;
3. enter root Activity catalogue;
4. confirm panel + cards + category buttons all render;
5. hover at least one category button;
6. capture screenshot and status.

Suggested files:

```text
20-1024x600-normal.png
21-1024x600-large.png
22-1280x800-normal.png
23-1366x768-compact.png
24-1920x1080-normal.png
25-1111x700-normal.png
```

PASS requires:

- all category buttons remain reachable;
- no overlap at the narrowest viewport;
- icon-only fallback, if triggered by existing responsive logic, is coherent;
- labels fit when labels are shown;
- shared buttons do not consume so much vertical space that Activity cards are pushed/clipped;
- panel/card/button hierarchy remains visually coherent;
- no per-resolution production branch is added.

---

# 14. Frame-count sanity

At a stable 1024×600 normal root catalogue:

```bash
python3 tools/greia_simulator_ctl.py status \
  > "$GREIA_V5_BUTTON_EVIDENCE/frame-before.json"

sleep 10

python3 tools/greia_simulator_ctl.py status \
  > "$GREIA_V5_BUTTON_EVIDENCE/frame-after.json"
```

Record frame-count delta and interval.

This is a gross regression sanity check only. Do not create a hardware-performance claim from the Mac simulator.

FAIL if there are obvious repeated decode/scaling stalls or severe starvation.

---

# 15. Root-cause policy

On failure:

1. preserve first failing screenshot/status;
2. classify root owner:
   - shared button artwork/rendition;
   - visual cache;
   - category-button mixin;
   - synthetic pointer handling;
   - responsive base category geometry;
3. fix the smallest correct owner;
4. rerun the exact failing simulator case;
5. rerun 1024×600 normal;
6. rerun full matrix for any geometry/render/cache change.

Do not hide a bad visual result with exception swallowing or by disabling the feature permanently.

---

# 16. Documentation and commit requirements

After PASS, update:

```text
LOCAL_AGENT_RESULT.md
docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md
HANDOVER.md
```

Record:

- exact start/final SHA;
- all simulator evidence;
- hover/default shared-button acceptance;
- category navigation/back lifecycle;
- missing/malformed catalogue results;
- corrupt hover-button isolated fallback result;
- responsive matrix;
- frame-count sanity;
- root causes fixed.

Commit and **push `main` to `origin/main`**. Do not force-push.

Do not query/run GitHub Actions.

---

# 17. Explicit non-claims

Even on PASS, do not claim:

```text
PHYSICAL VISUAL REVIEW
Acer performance PASS
Pi performance PASS
R7 closure
blanket approval of every UI artwork master
```

Correct evidence class remains:

```text
SIMULATOR VISUAL REVIEW
```
