# Greia V5 Shared Shell Panel — Activity Simulator Acceptance

**Date:** 2026-08-20  
**Repository:** `frozenpepper/Greia`  
**Branch:** `main`  
**Consumer:** `ui.panel.base/default`  
**Implementation:** `SharedUiShellPanelMixin` in `src/greia_launcher/shared_ui_presentation.py`  
**Testing authority:** Greia Activity Simulator only

---

# 1. Purpose

Validate the next substantial visible V5 integration: the reviewed shared `ui.panel.base` artwork framing the real Greia child Shell profile picker and Activity catalogue.

This is presentation only. Profile selection, Activity catalogue/navigation, hit targets, lifecycle, permissions and runtime authority must remain unchanged.

The existing plain theme background remains the fail-soft fallback.

---

# 2. Required setup

From the Greia checkout:

```bash
git fetch origin
git checkout main
git pull --ff-only origin main
export GREIA_V5_PANEL_SIM_STATE="$HOME/.greia-simulator-v5-panel"
mkdir -p ./tmp/v5-panel-simulator-evidence
export GREIA_V5_PANEL_EVIDENCE="$PWD/tmp/v5-panel-simulator-evidence"
python3 tools/greia_simulator.py --state-dir "$GREIA_V5_PANEL_SIM_STATE"
```

Do not use GitHub Actions, a VM, physical hardware or a standalone Pygame harness for acceptance in this session.

Simulator bridge is local loopback only (`127.0.0.1:8767`).

---

# 3. Baseline profile-picker acceptance

At `1024x600`, interface size `normal`:

1. start/apply simulator;
2. remain on the real Greia profile picker;
3. capture simulator status and screenshot.

Evidence:

```text
01-profile-1024x600-normal.png
01-status-profile.json
```

PASS requires:

- `ui.panel.base` visibly frames the profile-card area;
- rainbow/header remains unobstructed;
- profile tiles remain entirely visible;
- panel shadow/highlight is restrained and not a giant opaque box;
- profile hit targets remain aligned;
- selected profile remains readable;
- no clipping at 1024×600.

---

# 4. Activity catalogue acceptance

Enter one profile through normal Shell interaction.

Capture:

```text
02-activities-1024x600-normal.png
02-status-activities.json
```

PASS requires:

- shared panel is visibly behind the Activity-card grid;
- accepted `ui.card.activity` cards remain fully visible on top;
- category controls/avatar remain on top and readable;
- central card grid is visually coherent rather than crowded;
- no card is clipped by the panel frame;
- shared panel preserves its authored 640:420 aspect ratio;
- no input geometry changed.

Use keyboard selection and pointer hover on at least two cards. The already-accepted shared card behavior must remain correct.

---

# 5. Profile → Activity → Home lifecycle

Launch a harmless first-party Activity through the real Shell and return Home normally.

Capture the returned Shell:

```text
03-returned-home.png
```

PASS requires the shared panel/card composition to return intact and the child Shell to remain responsive.

---

# 6. Fail-soft cases

All fallback testing must be performed through the Activity Simulator.

## 6.1 Missing generated shared catalogue

Stop simulator, temporarily move:

```text
assets/catalog/shared_visuals_v1.toml
```

Restart simulator.

PASS requires:

- Shell boots;
- profile picker and Activity catalogue remain usable;
- panel disappears cleanly;
- Activity cards use their existing primitive fallback;
- no crash/error loop.

Capture:

```text
10-fallback-missing-catalogue-profile.png
10-fallback-missing-catalogue-activities.png
```

Restore the exact catalogue immediately.

## 6.2 Malformed generated catalogue

Back up the catalogue, replace it temporarily with invalid TOML, restart simulator.

PASS requirements are identical to missing catalogue.

Capture:

```text
11-fallback-malformed-catalogue.png
```

Restore the exact good catalogue immediately.

## 6.3 Corrupt only `panel_base.png`

Back up:

```text
assets/visual/runtime/v1/ui/panel_base.png
```

Replace only that PNG temporarily with invalid bytes and restart simulator.

PASS requires:

- profile picker and Activity catalogue remain usable;
- only shared panel framing falls back to the theme background;
- accepted shared Activity cards remain usable if their PNGs are intact;
- no repeated decode/crash loop.

This case specifically verifies the panel consumer has a narrow fail-soft boundary and does not unnecessarily disable all shared artwork.

Capture:

```text
12-fallback-corrupt-panel-profile.png
12-fallback-corrupt-panel-activities.png
```

Restore exact good PNG immediately.

---

# 7. Responsive matrix

Run both **profile picker** and **Activity catalogue** at each row:

| Viewport | Interface size |
|---|---|
| 1024×600 | normal |
| 1024×600 | large |
| 1280×800 | normal |
| 1366×768 | compact |
| 1920×1080 | normal |
| 1111×700 | normal |

For each row, capture at least the Activity catalogue. Profile-picker screenshots are required for 1024×600 normal, 1024×600 large and 1920×1080 normal; inspect profile picker manually on all rows.

PASS requires:

- panel aspect ratio remains stable;
- panel never stretches into a thin banner or giant slab;
- panel remains behind content rather than covering it;
- profile/cards remain reachable and readable;
- no per-resolution production branch is introduced;
- accepted Activity-card behavior does not regress.

Suggested evidence names:

```text
20-1024x600-normal.png
21-1024x600-large.png
22-1280x800-normal.png
23-1366x768-compact.png
24-1920x1080-normal.png
25-1111x700-normal.png
```

---

# 8. Frame sanity

At a stable Activity catalogue screen:

```bash
python3 tools/greia_simulator_ctl.py status > "$GREIA_V5_PANEL_EVIDENCE/frame-before.json"
sleep 10
python3 tools/greia_simulator_ctl.py status > "$GREIA_V5_PANEL_EVIDENCE/frame-after.json"
```

Record frame-count delta and elapsed time.

This is a simulator regression sanity check only, not physical-hardware performance evidence.

A visible periodic stall, repeated PNG decode or severe frame starvation is a FAIL.

---

# 9. Fix discipline

On failure:

1. preserve first failing screenshot/status;
2. identify whether the defect belongs to panel geometry, cache/fallback handling, base Shell layout or simulator input/capture;
3. fix the smallest shared owner;
4. rerun the exact failed case;
5. rerun 1024×600 normal;
6. rerun full matrix for geometry/cache changes.

Do not remove the panel merely to make the test pass. Do not introduce per-resolution forks or simulator-only production behavior.

---

# 10. Evidence classification

If all required cases pass, record:

```text
ui.panel.base — SIMULATOR VISUAL REVIEW
```

Do not claim physical hardware performance, R7 closure or blanket release-art approval.

Update:

```text
docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md
HANDOVER.md
LOCAL_AGENT_RESULT.md
```

Commit and push accepted work to `main`.
