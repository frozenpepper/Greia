# R7 Acer Writing Black Surface — Physical Classification and Source Fix

**Date:** 2026-08-31  
**Physical evidence SHA:** `83ed5d58f40f068c91670e1cdc8b8e87b735478a`  
**Disposition:** physical failure CLASSIFIED; narrow source fix IMPLEMENTED; verification + Acer retest pending

## 1. Evidence boundary

At exact clean SHA `83ed5d58`, the current-head source and real-Shell Simulator gates were green:

```text
focused source gate: PASS, 139 tests
backend-independence audit: PASS, blockers=0
system-chrome audit --strict: PASS, blockers=0
make verify: PASS, 1510 tests
project / Activity / Shell validation: PASS
Simulator Encyclopedia: PASS + protected Home return
Simulator Writing: PASS + protected Home return
Simulator Painting: PASS + protected Home return
Simulator animated Activity: PASS + protected Home return
Simulator hostile fixture: PASS + protected Home return
```

The same exact source was deployed to the reference i686 Acer. Shell boot/focus/pointer were green and no child-visible Linux, Activity raw-input authority, Activity DRM authority or material performance regression was observed.

## 2. Physical failure

Writing was launched only through the normal child Shell path.

Observed:

```text
T+2 s: Greia Starting… overlay
T+7 s: solid black 1024x600 Activity window with only the pale pointer dot
Escape: immediate clean return to CREA/Shell; keyboard and pointer restored
```

While black:

```text
Writing process alive/stable inside bwrap
READY marker exists with the exact session id
DISPLAY=:0
SDL_VIDEODRIVER=x11
Activity X window exists, 1024x600 at 0,0
Activity X window is visible, focused and topmost over the Shell
LVDS1 remains 1024x600 @ 60.04 Hz
no READY timeout
no platform_failure
no traceback
no DISPLAY/XAUTHORITY/SDL error
no physical libpng warning
```

Therefore the failure is **not** launch/READY, X window creation, mapping, focus or Legacy-X stacking. Physical classification:

```text
ACTIVITY_X11_RENDERING_OR_SURFACE_FAILURE
```

Painting was intentionally not tested after classification, per the diagnostic protocol.

## 3. Source root cause

Writing's responsive renderer draws the whole Activity directly onto the physical SDL display surface (`WritingApp.screen`).

The composition root also created `PygameReferenceCanvas(screen)` and passed it to `WritingApp`. After drawing the real Writing UI, the loop called:

```python
canvas.present(clear=theme.background)
pygame.display.flip()
```

`PygameReferenceCanvas` owns a separate 1024x600 logical `surface`. Its contract is that Activity rendering targets **that** logical surface. `present()` clears the physical target, blits the logical surface, applies bars and then draws the pointer.

Writing never rendered its scene to `canvas.surface`. The call therefore overwrote the valid physical Writing frame with the untouched reference surface immediately before the flip. The remaining pointer dot is consistent with the canvas presentation path drawing the pointer last.

This matches the physical symptom exactly.

## 4. Correction

Writing already has a responsive physical-surface layout based on `ChildUiMetrics` and keeps protected-system geometry through `activity_viewport_for_surface()` in `WritingApp`. It does not need a second reference surface.

The production composition now:

```text
does not import PygameReferenceCanvas
does not construct PygameReferenceCanvas
passes canvas=None to the existing optional WritingApp compatibility seam
keeps the existing responsive physical renderer unchanged
keeps protected Home/Back platform-owned
```

A regression test prevents production Writing composition from recreating `PygameReferenceCanvas` or enabling the optional canvas seam.

No Legacy-X stacking/session behavior was changed because the physical evidence disproved stacking as the cause.

## 5. Required verification

Before physical retest:

```text
new Writing physical-surface regression PASS
core Writing tests PASS
first-party readiness PASS
Activity validation PASS
backend-independence audit blockers=0
system-chrome audit blockers=0
make verify PASS
real-Shell Simulator Writing first frame visually contains Writing UI, not merely READY/process survival
protected Home return PASS
```

Then deploy the exact verified fix SHA to the Acer and retest **Writing only first**.

Required physical result:

```text
Writing visible after Starting overlay
no blank/black frame
typing/editing usable
Home/Escape return clean
no child-visible Linux
```

Only after Writing is physically green should Painting be tested independently. Do not attribute Painting to this Writing-specific root cause without evidence.

The long hostile 10/10, abrupt-crash and normal 20/20 durability lanes remain deferred until the physical Activity presentation path is usable.
