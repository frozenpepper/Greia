# Greia — Responsive UI Acceptance and Repair Protocol

**Date:** 2026-08-18  
**Audience:** owner-controlled local coding/test agent  
**Applies with:** `docs/testing/2026-08-18_LOCAL_AGENT_FULL_TEST_AND_FIX_SESSION.md`  
**Architecture:** ADR 0018 + ADR 0026  
**Product requirement:** `docs/product/RESPONSIVE_UI_AND_DISPLAY_LAYOUT.md`

---

## 0. Mandatory session amendment

This protocol is a mandatory addendum to the current local-agent full test/fix session.

Do not call the UI tranche complete merely because it works on the Acer's 1024×600 panel.

The local agent is authorized to inspect, refactor, test and repair launcher, installer, profile picker, shared UI helpers and first-party Activities when a responsive-layout defect is found. Preserve project architecture, add regressions, commit coherent fixes to `main`, and continue testing.

Do not solve responsiveness by introducing device-specific layout branches, a heavyweight desktop/widget framework, a general constraint solver, or a fixed virtual 1024×600 canvas stretched to every display.

---

# 1. Read before editing

From repository root:

```bash
cat docs/adr/0018-lightweight-ui-foundation.md
cat docs/adr/0026-resolution-adaptive-ui-layout.md
cat docs/product/RESPONSIVE_UI_AND_DISPLAY_LAYOUT.md
cat docs/design/GREIA_LAUNCHER_INTERACTION_AND_ACTIVITY_CATALOGUE.md
cat docs/testing/2026-08-18_LOCAL_AGENT_FULL_TEST_AND_FIX_SESSION.md
```

Also read the exact source owners you are about to change.

---

# 2. First source gate

Run the renderer-neutral responsive tests first:

```bash
PYTHONPATH=src python3 -m unittest tests.test_responsive_layout -v
```

Then run the UI-focused source set:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_responsive_layout \
  tests.test_ui_motion_scroll \
  tests.test_launcher_presentation \
  -v
```

If these fail because of a genuine defect, diagnose and repair the source. Do not weaken containment or generated-viewport tests to obtain PASS.

After focused repair, rerun the focused set and then:

```bash
make verify
```

Record exact commands, SHA and result. Do not claim PASS for commands not actually executed.

---

# 3. Static audit for fixed-resolution assumptions

Inspect Greia-owned UI code, especially:

```text
src/greia_launcher/
src/greia_installer/
src/greia_platform/ui_core.py
src/greia_platform/responsive_layout.py
src/greia_platform/activity_ui.py
src/greia_platform/pygame_ui.py
src/greia_platform/system_chrome.py
activities/
```

Look for:

- literal full-screen coordinates copied from 1024×600;
- fixed `Rect` positions for essential controls;
- minimum widths/heights that can force overflow;
- fixed two/three-column logic that ignores available content space;
- hit targets computed separately from displayed geometry;
- font/icon creation that does not account for changed size;
- caches not invalidated/keyed by size;
- artwork stretched independently on x/y axes;
- overlays/dialogs that cannot fit a constrained viewport;
- Activities using the physical screen size instead of their actual Greia Activity viewport;
- device/model-specific UI branches.

Do not mechanically ban every pixel constant. Local minimums, padding and design caps are legitimate when bounded by responsive containment/reflow. The defect is an assumption that makes the composition depend on one screen geometry.

---

# 4. Shared-layout migration rule

Use `greia_platform.responsive_layout` for shared renderer-neutral viewport/grid calculations where it removes duplicated/fixed geometry.

Do not force every tiny local draw expression through an abstraction. The shared layer should own stable responsive rules; renderer-specific drawing can remain local.

When migrating a surface:

1. identify its semantic regions;
2. reserve protected/system regions first;
3. derive the remaining content rect from the live viewport;
4. choose rows/columns from available space;
5. reflow/paginate/scroll before shrinking readability-critical elements;
6. derive visible rects and hit rects from the same layout result;
7. key/invalidate size-dependent caches;
8. add pure geometry tests where possible;
9. add rendered interaction tests where useful.

---

# 5. Required resolution matrix

Exercise at least these dimensions in windowed/headless/render-test mode where the surface supports it:

```text
640x480
800x600
1024x600
1024x768
1280x720
1366x768
1920x1080
2560x1440
3840x2160
720x1280
```

These dimensions are probes, not a whitelist.

Also exercise a deterministic set of nearby/non-round dimensions, for example:

```text
641x479
853x533
999x599
1117x731
1439x899
1711x967
```

Where the test harness allows arbitrary sizing, add generated/property-style geometry coverage rather than snapshotting only the list above.

---

# 6. Required launcher acceptance

For every representative resolution verify:

- profile/avatar control remains visible;
- root category controls remain reachable;
- labels do not overlap category icons;
- in-category Back + category icon + title stay visible;
- Activity name bands remain readable;
- package-owned icons preserve aspect ratio;
- tile geometry remains fully inside content bounds;
- enough Activities force scrolling/paging without losing selection;
- keyboard/controller movement keeps the selected item visible;
- pointer hit targets match rendered tiles after resize;
- hover/shadow/launch animation remains bounded and does not draw destructive artifacts outside the intended region;
- error/status badges remain visible;
- large resolutions cap tile/text growth rather than creating enormous controls;
- portrait/narrow probes reflow rather than clip.

The current launcher already handles resize events and clears size-dependent caches; preserve that behavior while replacing remaining fixed breakpoint/minimum assumptions with viewport-driven geometry where needed.

---

# 7. Required installer acceptance

Exercise every installer page, not only Welcome:

1. Welcome
2. keyboard layout probe/selector
3. target selection
4. hardware settings
5. Wi-Fi scan/list
6. Wi-Fi password entry
7. confirmation / destructive hold control
8. installing/progress
9. completion
10. error path

At every resolution verify:

- all essential actions fit;
- Back/Continue/Install are reachable;
- text wraps or reflows rather than being clipped;
- Wi-Fi rows/password field remain usable;
- destructive confirmation cannot move partly off-screen;
- progress/status copy remains readable;
- the completion screen follows the new credential policy from the main session and does **not** resurrect the obsolete random recovery-code UX;
- pointer hit targets match visible controls.

If the installer cannot render a page safely at a mode Greia advertises as usable, that is a defect.

---

# 8. Profile/password acceptance

Verify the profile chooser with:

- one profile;
- maximum/near-maximum profile count;
- long valid child names;
- optional password field visible/unmasked and masked modes where supported;
- wrong-password error;
- no-password profile;
- different viewport sizes before and during password entry.

No child may become inaccessible because a password control or Continue/Back action is clipped.

---

# 9. System chrome acceptance

Home/Back system chrome is higher-trust platform UI.

For every tested viewport:

- protected geometry remains fully visible;
- Activity content geometry excludes the protected region;
- Activity input cannot steal the protected region;
- resize recomputes both visible chrome and input hit regions;
- controls do not overlap each other at narrow sizes;
- the Activity receives correctly translated coordinates for its remaining viewport.

Do not fix an overlap by letting Activities draw under or intercept the real system controls.

---

# 10. First-party Activity acceptance

At minimum test Writing and Painting plus one pointer/game-like Activity if available.

Verify:

- Activity reads its actual current surface/content size;
- no hard-coded 1024×600 assumption controls placement;
- toolbars/controls reflow or remain reachable;
- canvases/editor regions consume remaining space safely;
- saved content semantics do not change merely because viewport size changes;
- artwork/text input coordinate mapping remains correct after resize;
- Home/Back protected region remains respected;
- repeated resizes do not leak unbounded surfaces/fonts/cache entries.

A game may maintain its own logical coordinate system, but mapping to/from the real Activity viewport must preserve aspect ratio and input correctness.

---

# 11. Parent HTML responsive acceptance

Use the exact Parent-App revision currently pinned by:

```text
runtime/parent-app-client.toml
runtime/parent-app-client.manifest.json
```

Run its normal tests first:

```bash
npm test
```

Then inspect/render the client at representative browser viewport widths, including approximately:

```text
320x568
375x667
390x844
768x1024
1024x768
1366x768
1920x1080
```

Verify:

- pairing/auth UI remains usable;
- profile creation/edit/password controls remain usable;
- hardware settings remain usable;
- Activity install control and errors remain visible;
- no horizontal page overflow is required for ordinary actions;
- destructive/revocation controls remain explicit and reachable;
- the client does not couple its layout to the Greia device's physical display resolution.

If Parent-App source must change, commit/push that repository first, run its tests, then update Greia's pinned revision and integrity manifest in the same coherent tranche.

---

# 12. Runtime resize transition

Where the environment supports resizing without reboot, test a live sequence such as:

```text
1280x720 -> 800x600 -> 1920x1080 -> 1024x600
```

At each transition verify:

- geometry recomputes;
- no stale hit targets remain;
- selection/focus remains on a valid semantic item;
- scroll position remains valid or is safely normalized;
- icons/fonts/shadows are not stale-size artifacts;
- no unbounded cache growth occurs;
- launcher/Activity remains responsive.

Capture screenshots before/after when useful.

---

# 13. Physical low-resource acceptance

The Acer 1024×600 physical test remains mandatory because responsiveness must not trade away the resource floor.

On the physical machine verify:

- launcher still looks deliberate at 1024×600;
- text remains readable;
- hover/launch effects remain smooth enough;
- Activity scrolling remains responsive;
- installer controls remain fully visible;
- no new layout abstraction produces measurable hot-loop or memory regressions.

If broader responsiveness makes the Acer path materially slower/heavier, treat that as a correctness regression and optimize the shared implementation rather than adding an Acer-only UI fork.

---

# 14. Repair policy

The local agent may fix responsive defects immediately.

For each real defect:

1. preserve the failing resolution/surface/step;
2. identify the root geometry/state cause;
3. repair the shared owner when the issue is general;
4. avoid device-name/model-specific branching;
5. add a regression that would have caught the failure without physical hardware where practical;
6. rerun the smallest relevant tests;
7. rerun `make verify` after the tranche;
8. commit/push coherently;
9. continue the resolution matrix.

Do not rewrite a test to match broken clipping.

---

# 15. Required result report

At the end, report:

```text
START SHA:
END SHA:
COMMITS CREATED:

SOURCE GATES:
- responsive layout tests:
- focused UI tests:
- make verify:

SURFACES REVIEWED:
- installer:
- profile picker/password:
- launcher/categories/scroll:
- system chrome:
- Writing:
- Painting:
- other Activity:
- Parent HTML:

RESOLUTIONS EXERCISED:

RUNTIME RESIZE RESULT:

PHYSICAL ACER 1024x600 RESULT:

DEFECTS FOUND AND FIXED:

REMAINING RESPONSIVE GAPS:

FILES / EVIDENCE PATHS:
```

Use PASS/FAIL/NOT-RUN/UNPROVEN with honest scope. A source PASS plus one screenshot is not a complete responsive-UI claim.
