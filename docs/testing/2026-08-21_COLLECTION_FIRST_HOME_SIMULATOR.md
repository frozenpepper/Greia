# Greia Collection-first Home — Activity Simulator Acceptance

**Status:** owner/local-agent acceptance protocol  
**Date:** 2026-08-21  
**Evidence class:** `SIMULATOR VISUAL REVIEW` only  
**Required execution path:** Greia Activity Simulator, headless preferred  
**Target source:** `CollectionFirstHomeMixin` + `ui.portal.frame/default`

## 1. Purpose

This gate validates the first real migration from the temporary **All Activities + category filters** launcher toward the accepted child information architecture:

```text
profile → Greia Home → primary Collection → Activity
```

The normal child Home must now present the available primary Collections as large destinations. `All` remains an internal catalogue projection but must no longer appear as the normal child Home wall of Activity cards.

This is not a filesystem-folder test. Collections are semantic Greia destinations and one Activity may still belong to more than one Collection without duplicating package state.

## 2. Hard constraints

- Perform runtime/visual/input/fallback/responsive acceptance **through the Activity Simulator only**.
- Use non-intrusive headless mode for the run.
- Do not open ordinary desktop Pygame windows for acceptance.
- Do not use GitHub Actions.
- Do not substitute direct `pytest`, `unittest`, `make verify` or ad-hoc Pygame scripts for this acceptance.
- `make visual-assets` is a build prerequisite, not acceptance evidence.
- Work in the Greia repository tree. Do not use filesystem-root `/tmp`.
- Do not manufacture PASS evidence for states that were not exercised.
- Commit and push accepted fixes/results to canonical `main` when complete.

## 3. Preparation

From the repository root:

```bash
git status --short
git branch --show-current
git pull --ff-only origin main

command -v rsvg-convert
make visual-assets
```

Confirm these generated files exist after the build:

```text
assets/visual/runtime/v1/ui/portal_frame.png
assets/catalog/shared_visuals_v1.toml
```

Confirm the generated catalogue contains:

```text
ui.portal.frame
```

Use an isolated simulator state root:

```bash
export GREIA_SIMULATOR_HEADLESS=1
export GREIA_SIMULATOR_STATE="$HOME/.greia-simulator-collection-home"
rm -rf "$GREIA_SIMULATOR_STATE"
mkdir -p tmp/collection-home-simulator-evidence
python3 tools/greia_simulator.py --state-dir "$GREIA_SIMULATOR_STATE"
```

Use the simulator bridge at:

```text
http://127.0.0.1:8767
```

Do not expose it through a tunnel or hosted service.

## 4. Baseline Home acceptance

At `1024×600`, interface size `normal`:

1. select a child profile normally;
2. capture the first child Home frame;
3. verify the screen shows **primary Collection destinations**, not the All-Activities card wall;
4. verify the old root category-button/filter row is not acting as the Home information architecture;
5. verify only non-empty Collections are shown;
6. verify each visible Collection has:
   - large `ui.portal.frame` treatment;
   - stable semantic icon;
   - readable localized Collection title;
   - large child-sized target;
   - obvious selected state;
7. verify the active-profile switcher remains available;
8. verify portal layout is balanced inside the accepted shared panel/tray and does not clip.

Capture at least:

```text
tmp/collection-home-simulator-evidence/01-home-1024x600-normal.png
tmp/collection-home-simulator-evidence/01-status.json
```

**Reject** if Home still looks like a giant Activity catalogue with category filters merely restyled as buttons.

## 5. Keyboard navigation

On Collection Home:

1. use `RIGHT` and verify semantic focus moves to the next Collection;
2. use `DOWN` / `UP` and verify focus follows the visible grid rather than hidden Activity selection;
3. use `TAB` and verify it cycles Collection focus;
4. press `ENTER` on a Collection;
5. verify the selected Collection opens and now shows that Collection's Activities using the already accepted Activity cards/panel/navigation chrome.

Capture:

```text
tmp/collection-home-simulator-evidence/10-home-keyboard-focus.png
tmp/collection-home-simulator-evidence/11-collection-open-keyboard.png
```

## 6. Pointer navigation

Return to Home, then:

1. move the synthetic pointer over a Collection portal;
2. verify the portal lifts/emphasizes without geometry breakage;
3. click it;
4. verify the correct Collection opens.

Capture:

```text
tmp/collection-home-simulator-evidence/12-home-hover.png
tmp/collection-home-simulator-evidence/13-collection-open-pointer.png
```

## 7. Local Back hierarchy

From inside a primary Collection:

1. verify the accepted tactile local Back control is still visible;
2. activate Back;
3. verify it returns to **Collection Home**, not to an All-Activities wall;
4. verify the previously focused Collection remains a sensible/nearby focus target;
5. press launcher Back/Escape again at Home and verify root semantics return to profile choice.

Capture:

```text
tmp/collection-home-simulator-evidence/20-returned-collection-home.png
tmp/collection-home-simulator-evidence/21-returned-profile-picker.png
```

## 8. Activity launch and return origin

1. enter a Collection;
2. launch one normal Activity;
3. allow the standard shared launch overlay to appear;
4. return Home from the Activity through the normal Greia lifecycle;
5. verify the launcher returns to the same Collection context rather than flattening back to All Activities;
6. use local Back and verify Collection Home is one level above it.

Capture:

```text
tmp/collection-home-simulator-evidence/30-activity-returned-to-collection.png
tmp/collection-home-simulator-evidence/31-after-local-back-home.png
```

## 9. Multi-membership sanity

Use an Activity that belongs to more than one primary Collection (for example the current Shape Garden/Writing metadata where applicable):

1. enter the first Collection and confirm the Activity is present;
2. return Home;
3. enter the second Collection and confirm the same Activity is present;
4. do not expect duplicate installation/state identities.

This test validates presentation projection only; do not mutate package/storage data to prove it.

Capture one screenshot from each Collection if the current built-in catalogue provides a multi-membership Activity.

If the current installed test catalogue has no multi-membership Activity, record `SOURCE / NOT EXERCISED` rather than fabricating a PASS.

## 10. Portal-specific fail-soft isolation

Temporarily corrupt only:

```text
assets/visual/runtime/v1/ui/portal_frame.png
```

Restart the isolated headless simulator and return to child Home.

Verify:

- the **Collection-first hierarchy remains intact**;
- primary Collections still appear as large usable circular fallback destinations;
- category icons/titles remain readable;
- existing panel/profile/card/navigation shared visuals remain active;
- no crash, repeated decode loop or visible Linux error occurs.

Capture:

```text
tmp/collection-home-simulator-evidence/40-fallback-corrupt-portal.png
```

Restore/regenerate the rendition afterward:

```bash
make visual-assets
```

## 11. Responsive matrix

Exercise Collection Home plus one opened Collection through the simulator at:

| Row | Viewport | Interface size |
|---|---:|---|
| 1 | 1024×600 | normal |
| 2 | 1024×600 | large |
| 3 | 1280×800 | normal |
| 4 | 1366×768 | compact |
| 5 | 1920×1080 | normal |
| 6 | 1111×700 | normal |

For every Home row verify:

- all visible primary Collections fit without scrolling;
- no portal/title clipping;
- no overlap with active-profile control/error indicator;
- portal circles stay circular;
- selected state is obvious without pointer;
- Collection Home remains visually stronger than a filter bar;
- no per-resolution special-case layout appears.

For at least `1024×600 normal`, `1366×768 compact` and `1920×1080 normal`, also open one Collection and verify the accepted Activity catalogue remains intact.

Store screenshots/status under:

```text
tmp/collection-home-simulator-evidence/
```

using clear `50-...`, `51-...` etc names.

## 12. Frame sanity

Measure a 10-second idle period on Collection Home through simulator status/frame counters.

Record before/after status files and compute observed FPS. The intent is regression detection against the established ~30 FPS clock, not a physical-hardware benchmark.

Store:

```text
tmp/collection-home-simulator-evidence/frame-before.json
tmp/collection-home-simulator-evidence/frame-after.json
```

Reject obvious starvation/stalls. Do not convert simulator FPS into an Acer/Pi hardware claim.

## 13. Fix policy

If anything fails:

- fix the root/shared cause;
- do not add per-resolution forks;
- do not reintroduce All-Activities Home to make a test easy;
- do not turn Collections into filesystem folders;
- do not duplicate Activity package/state when an Activity belongs to several Collections;
- keep root Home bounded to primary Collections;
- preserve existing registry/runtime/trust/lifecycle authority;
- rerun the affected simulator cases plus the baseline after every fix.

## 14. Required documentation/result updates

When accepted, update:

```text
LOCAL_AGENT_RESULT.md
docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md
HANDOVER.md
```

Also update the Collection-first implementation status in:

```text
docs/product/CHILD_ACTIVITY_DISCOVERY_AND_AUDIENCE.md
docs/design/GREIA_LAUNCHER_INTERACTION_AND_ACTIVITY_CATALOGUE.md
```

Do not claim adaptive sub-Collections, age/development policy or Parent per-child visibility as implemented merely because Collection Home passes. This gate covers the first **Home → primary Collection → Activity** migration only.

## 15. Git completion

After all accepted fixes/documentation are complete:

```bash
git status --short
git add -A
git commit -m "accept collection-first Greia Home in simulator"
git pull --rebase origin main
git push origin main
git rev-parse HEAD
```

Do not force-push.

Return the final canonical SHA plus a concise matrix of PASS / SOURCE-NOT-EXERCISED / FAIL evidence.
