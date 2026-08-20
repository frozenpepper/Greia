# Greia V5 Shared Navigation Chrome — Activity Simulator Acceptance

**Status:** required local acceptance protocol  
**Date:** 2026-08-21  
**Evidence class:** `SIMULATOR VISUAL REVIEW` only  
**Consumer:** `ui.button.icon/default`  
**Implementation:** `src/greia_launcher/navigation_chrome_presentation.py`

This protocol validates the next product-visible V5 tranche: the reviewed tactile icon-button frame used for Shell-local navigation controls. It must be executed through the real Greia Activity Simulator in non-intrusive headless mode.

Do not use GitHub Actions. Do not claim physical Acer/Pi performance from this run.

---

## 1. Sync and build the new rendition

From the Greia repository root:

```bash
git status --short
git fetch origin
git checkout main
git pull --ff-only origin main
git rev-parse HEAD

command -v rsvg-convert
make visual-assets
```

Confirm generation of:

```text
assets/visual/runtime/v1/ui/icon_button.png
```

and confirm `assets/catalog/shared_visuals_v1.toml` contains:

```text
ui.button.icon/default
```

Do not manually fabricate either file.

---

## 2. Start an isolated headless Activity Simulator

Use a fresh state root:

```bash
export GREIA_V5_NAV_STATE="$HOME/.greia-simulator-v5-navigation"
export GREIA_V5_NAV_EVIDENCE="$PWD/tmp/v5-navigation-simulator-evidence"
mkdir -p "$GREIA_V5_NAV_EVIDENCE"

GREIA_SIMULATOR_HEADLESS=1 python3 tools/greia_simulator.py \
  --state-dir "$GREIA_V5_NAV_STATE"
```

The simulator loopback bridge remains:

```text
http://127.0.0.1:8767
```

Use `tools/greia_simulator_ctl.py` for status, screenshots and input. Headless mode must still render the exact real `GreiaChildShell` pixel buffer.

---

## 3. Baseline regression check

At `1024x600`, normal interface size, enter a child profile and capture the Activity catalogue:

```bash
python3 tools/greia_simulator_ctl.py status \
  | tee "$GREIA_V5_NAV_EVIDENCE/01-status.json"
python3 tools/greia_simulator_ctl.py screenshot \
  "$GREIA_V5_NAV_EVIDENCE/01-catalogue.png"
```

Acceptance:

- maximized `ui.panel.base` tray remains intact;
- large Activity cards remain intact;
- root category buttons remain intact;
- profile frame remains intact;
- no layout regression was introduced merely by adding navigation chrome.

---

## 4. Mandatory in-category Back control

Open one real Activity category through the normal category button.

Capture:

```bash
python3 tools/greia_simulator_ctl.py screenshot \
  "$GREIA_V5_NAV_EVIDENCE/10-category-back-default.png"
```

Expected:

- the local Back control uses the circular/tactile `ui.button.icon` frame;
- the existing back-arrow meaning remains obvious;
- category icon/title remain aligned and readable;
- the new frame does not change the hit rectangle or category identity;
- it does not impersonate or replace protected Activity Home/Back chrome.

Move the synthetic pointer over the Back control and capture:

```bash
python3 tools/greia_simulator_ctl.py move <X> <Y>
python3 tools/greia_simulator_ctl.py screenshot \
  "$GREIA_V5_NAV_EVIDENCE/11-category-back-hover.png"
```

Acceptance:

- hover produces the intended tiny lift/accent response;
- no flicker or hit/render drift appears;
- pointer click returns to the root Activity catalogue.

---

## 5. Activity scroll controls — exercise when legitimately reachable

If the current real catalogue produces a multi-page Activity collection, exercise its up/down scroll controls.

Capture default and hover states, navigate one page, then navigate back.

Expected:

- available scroll controls use `ui.button.icon`;
- arrows remain directionally unambiguous;
- selection and scroll window remain authoritative in existing launcher logic;
- the visual frame does not alter the original hit rectangles;
- panel/card composition remains clean.

If the current catalogue genuinely does not expose a scroll control, record this sub-case as:

```text
SOURCE / NOT EXERCISED
```

Do not create fake production state merely to manufacture a PASS.

---

## 6. Profile page controls — exercise when legitimately reachable

If the isolated simulator state contains enough valid child profiles to require profile pagination, verify the previous/next profile-page controls use the same `ui.button.icon` family and remain functional.

If pagination is not naturally present, record this sub-case as `SOURCE / NOT EXERCISED` rather than fabricating it.

The mandatory accepted runtime consumer for this tranche is the real in-category Back control; scroll/profile pagination broaden reuse when reachable.

---

## 7. Corrupt icon-button fail-soft isolation

Stop the simulator before changing the generated PNG.

Back up:

```bash
cp assets/visual/runtime/v1/ui/icon_button.png \
  "$GREIA_V5_NAV_EVIDENCE/icon_button.good.png"
```

Replace `icon_button.png` with invalid bytes, then restart the same headless simulator state.

Enter a category again.

Expected:

- Shell remains usable;
- the in-category Back control falls back to the existing primitive treatment;
- `ui.panel.base`, Activity cards, category buttons, profile frame and feedback visuals remain independently active;
- there is no per-frame retry/error loop;
- category open/back navigation still works.

Capture:

```bash
python3 tools/greia_simulator_ctl.py screenshot \
  "$GREIA_V5_NAV_EVIDENCE/20-fallback-corrupt-icon-button.png"
```

Stop the simulator and restore the exact good PNG:

```bash
cp "$GREIA_V5_NAV_EVIDENCE/icon_button.good.png" \
  assets/visual/runtime/v1/ui/icon_button.png
```

Never commit corrupted test output.

---

## 8. Responsive matrix

Run the real in-category Back control through at least:

```text
1024×600  + normal
1024×600  + large
1280×800  + normal
1366×768  + compact
1920×1080 + normal
1111×700  + normal
```

For every row:

1. apply the viewport/interface size through the simulator;
2. enter a profile;
3. open one category;
4. verify/capture the shared Back control;
5. return to root;
6. record status.

Suggested evidence names:

```text
30-1024x600-normal.png
31-1024x600-large.png
32-1280x800-normal.png
33-1366x768-compact.png
34-1920x1080-normal.png
35-1111x700-normal.png
```

Acceptance:

- control stays large enough to recognize and hit;
- circular frame remains circular rather than stretched;
- arrow stays centered;
- category title/icon remain reachable;
- no clipping against screen edge/profile switcher/category title;
- no hard-coded per-resolution production branches are added.

---

## 9. Frame-rate sanity

At a stable in-category screen:

```bash
python3 tools/greia_simulator_ctl.py status \
  > "$GREIA_V5_NAV_EVIDENCE/frame-before.json"
sleep 10
python3 tools/greia_simulator_ctl.py status \
  > "$GREIA_V5_NAV_EVIDENCE/frame-after.json"
```

Record the frame-count delta and elapsed time.

This is only a gross simulator regression check. Do not translate it into a physical-hardware performance claim.

---

## 10. Failure rules

If the shared icon-button treatment looks visually wrong, fix the shared/root cause. Do not:

- add simulator-only production rendering;
- alter category/navigation semantics to fit artwork;
- create per-resolution forks;
- make the image cache unbounded;
- decode/scale the PNG per frame;
- swallow broad exceptions;
- weaken other accepted shared-visual fallbacks.

After a fix, rerun the exact failed case, then `1024x600 normal`, then the full responsive matrix if geometry changed.

---

## 11. Required result record

Update:

```text
LOCAL_AGENT_RESULT.md
docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md
HANDOVER.md
```

Record separately:

```text
in-category Back          PASS / FAIL
Activity scroll controls PASS / FAIL / NOT EXERCISED
profile pagination       PASS / FAIL / NOT EXERCISED
corrupt PNG fallback     PASS / FAIL
responsive matrix        exact rows
frame sanity             exact frame delta / elapsed time
```

Evidence scope remains `SIMULATOR VISUAL REVIEW`.

Commit and push coherent accepted work to canonical `main`.
