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

## 6. Verification at `d947eb7ef5ad3703cb7293a8bba73bf9db9277e4` (2026-09-01)

### 6.1 Source gate

```text
HEAD == origin/main == d947eb7e, tree clean
test_writing_physical_surface_contract: PASS (2)
test_core_creation_activities: PASS (16)
test_first_party_activity_readiness: PASS (1)
audit_activity_backend_independence: activities=34 blockers=0
audit_activity_system_chrome_ownership --strict: blockers=0
make verify: PASS Ran 1512 tests in 112.831s OK (skipped=2), project/Activity/shell validation PASS
```

### 6.2 Simulator visual-pixel gate

```text
tools/greia_simulator_gate.py --activity-dir activities/writing --locale it --survival-seconds 8
  first frame writing-02-activity.png: toolbar visible YES, editor/page visible YES, not black, not blank+pointer, no corruption
  post-interaction writing-03-post.png: same, survival PASS, clean stop
  gate log PASS, exit 0
```

Mechanical READY/process survival is not sufficient; the first frame pixel check is required and now passes.

### 6.3 Acer deployment provenance

```text
tools/deploy_to_acer.py: bundle 110.21 MB, upload 2.8 MB/s 39s, extraction/chown, greia-launcher restart, wait 180 ready
sha256sum /opt/greia-os/activities/writing/main.py = e2f69027... matches local d947eb7e (vs 496b45fd at 83ed5d58)
candidate-sha.txt: candidate=d947eb7e origin=d947eb7e
acer-status-after-deploy.json: greia-launcher active, display :0, active_profile null then Explorer after selection
```

### 6.4 Physical Writing retest (child path, observation-only)

Launch via CREA (14) page 3/3 → `SCRITTURA E LETTERE` → `Return`:

- T+2s `writing-t2.png`: `Starting…` overlay (beige)
- T+7s `writing-t7.png` + `acer-writing-visible/screen.png`: **Writing visible** – beige top bar, toolbar (book, undo, emoji, green-dot, `+` yellow, `SALVO`, brush), large white editor with text `GREIA TESTO DI PROVA` etc., yellow cursor, not black, not blank+pointer, no child-visible Linux, no traceback/platform_failure, xrandr LVDS1 1024x600@60.04, Xorg no EE

Typing/editing `NUOVO TEST 123` + `Seconda riga di prova` (>15s) via `greia_remote type`: **PASS** – `writing-after-text.png` shows new lines, cursor responsive, pointer usable; autosave 5s wait.

`key Escape` return: **PASS** – immediate `writing-shell-after-return.png` CREA 3/3, pointer/focus restored.

Relaunch after autosave: **PASS** – after one `windowfocus 4194311` recovery (observed X Focus loss after Activity return, unrelated to black root cause, recovered observation-only), second launch `writing-relaunch2.png` shows editor with persisted `NUOVO TEST 123` + `Seconda riga di prova` plus prior content, proving **save/autosave and relaunch persistence PASS**; second `Escape` clean (`writing-final-return.png`).

Overall Writing lane at d947eb7e: launch PASS, input PASS, save/autosave PASS, protected return PASS (with one focus recovery), relaunch persistence PASS, no black frame. The fix therefore **closes** the `ACTIVITY_X11_RENDERING_OR_SURFACE_FAILURE` classified at 83ed5d58.

### 6.5 Physical Painting independent check

At d947eb7e, after Writing green:

- `painting-t2.png`: `Starting…`
- `painting-t7.png` + `acer-painting-visible/screen.png`: **Painting visible** – white 1024x600 canvas, top toolbar (palette, undo), bottom 10-color palette + 3 brush sizes, `SALVO` badge, not black, not blank+pointer.

`key Escape` return to CREA 1/3: **PASS**.

Sustained 20s high-rate draw / tool change / save/relaunch via physical high-rate path not yet executed (remote injection is not a substitute per the acceptance doc) – presentation is proven, durability lanes remain INCOMPLETE as intended.

### 6.6 Remaining R7.2/R7.3

With Writing and Painting presentation now green on the same exact deployed d947eb7e, the presentation path is usable. The remaining required physical lanes per `docs/testing/2026-08-29_R7_R72_LEGACY_X_CONTAINMENT_SOURCE_AND_ACER_ACCEPTANCE.md` §§9–14 and `docs/testing/2026-08-29_R7_R73_TRUSTED_SYSTEM_CHROME_SOURCE_AND_ACER_ACCEPTANCE.md` §§7–13 are:

```text
hostile first cycle + 10/10 forced Home
abrupt Activity crash recovery
normal 20/20 Shell→Activity→Shell durability (mix, ≥5 Writing/Painting)
performance evidence
final logs
```

These are deferred in this tranche and must be executed on the already-deployed d947eb7e without rerunning source/Simulator gates if source unchanged. The Writing black/dot root cause is therefore **FIXED**; the full R7.2/R7.3 `ACCEPTED` verdict remains blocked until those lanes are green.
