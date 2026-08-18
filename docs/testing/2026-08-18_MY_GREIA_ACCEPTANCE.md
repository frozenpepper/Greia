# Greia — My Greia child settings acceptance addendum

**Status:** mandatory addendum to `2026-08-18_LOCAL_AGENT_FULL_TEST_AND_FIX_SESSION.md`  
**Date:** 2026-08-18

The current local-agent session must include this tranche before claiming the child UI/customization work complete.

## 1. Read first

Read:

```text
docs/product/MY_GREIA_SETTINGS.md
docs/product/RESPONSIVE_UI_AND_DISPLAY_LAYOUT.md
docs/adr/0026-resolution-adaptive-ui-layout.md
src/greia_platform/ui_preferences.py
src/greia_platform/theme_snapshot.py
src/greia_platform/activity_api.py
src/greia_platform/activity_ui.py
src/greia_launcher/theme.py
src/greia_launcher/child_shell.py
activities/workshop_settings/activity.toml
activities/workshop_settings/main.py
```

My Greia is child customization, **not** a child system-administration panel. Do not add Parent credentials, Wi-Fi, SSH, Activity installation, disks or developer settings to make the screen look more complete.

## 2. Focused source gate

From repository root:

```bash
set -o pipefail
PYTHONPATH=src python3 -m unittest \
  tests.test_ui_preferences \
  tests.test_theme_snapshot \
  tests.test_activity_theme_access \
  tests.test_activity_ui_preferences \
  tests.test_my_greia_settings_contract \
  tests.test_my_greia_runtime \
  tests.test_customization \
  tests.test_activity_ui \
  tests.test_responsive_layout \
  tests.test_launcher_presentation \
  -v 2>&1 | tee "$SESSION_ROOT/my-greia-focused.log"
```

Then run the other current launcher/Activity focused tests and finally:

```bash
make verify
```

These tests were added/changed in the repository but are **not evidence of PASS until you execute them locally**.

If a genuine source defect is found, fix it, add/repair the regression, commit to `main`, rerun the smallest affected set, then rerun this focused gate.

## 3. Required code review

Review for these invariants:

- only built-in `org.greia.workshop-settings` receives the permanent customization/profile permissions;
- ordinary Activities do not receive `GREIA_CUSTOMIZATION_DIR` merely to match colors;
- ordinary Activities may receive only the bounded resolved theme snapshot and semantic interface-size value;
- wallpaper file paths are not present in ordinary Activity snapshots;
- interface size remains `compact`, `normal` or `large`; there is no arbitrary pixel/percentage setting;
- setting size never selects a device-specific layout;
- My Greia contains no shell/subprocess/root/Parent-admin shortcuts;
- no Activity-owned fake Home/Back/close control replaces platform system chrome;
- wallpaper scanning/import remains bounded and symlink/path safe;
- removable media disappearing during browsing is handled without crashing the child session;
- thumbnail/cache growth remains bounded;
- Activity lifecycle calls `mark_activity_ready()` and honors `activity_stop_requested()`.

A source regression now covers the scan-to-thumbnail removable-media disappearance race, but that does **not** replace physically ejecting the media while the wallpaper screen is open.

## 4. Visual/interaction acceptance

For each representative viewport in the responsive protocol, launch My Greia and verify all four icon tabs remain visible/reachable:

```text
colors
wallpapers
size
avatar
```

Do not rely on text labels to make the tabs understandable.

### Colors

- background swatches are directly selectable;
- accent swatches are directly selectable;
- text-color swatches are directly selectable;
- selected choice has a clear visual state;
- changes are immediate;
- no swatch/hit target is clipped or overlaps another essential target.

### Wallpapers

- solid/no-wallpaper choice is visually obvious;
- imported candidates are shown as bounded thumbnails;
- selecting a candidate immediately updates the managed wallpaper;
- paging/scrolling works when candidates exceed visible capacity;
- empty removable-media state remains understandable visually;
- remove/eject media while this screen is open and confirm no crash;
- corrupt/oversized/unsupported images fail safely.

### Interface size

The child must see three visually different choices. Verify:

- compact is visibly smaller;
- normal is the default/reference size;
- large is visibly larger;
- choice persists after leaving/re-entering My Greia;
- launcher typography/interface presentation reflects the selected profile preference after return;
- Writing/Painting and other first-party Activities using shared `ChildUiMetrics` receive the semantic size without per-resolution/per-size branches;
- `large` does not clip launcher labels, category header, profile/password UI or launch overlay;
- `compact` does not fall below documented readable/hit-target floors;
- changing resolution does not reset the preference or require a separate layout.

### Avatar

- all supported avatars are reachable through responsive bounded layout;
- current avatar is visibly selected;
- selection persists;
- returning to launcher shows the updated profile avatar.

## 5. Per-profile isolation

Create/use at least two child profiles A and B.

Set visibly different choices, for example:

```text
A: lavender/grape + large + unicorn
B: mint/ocean + compact + robot
```

Switch A -> B -> A and verify:

- launcher background/colors switch with profile;
- interface-size preference switches with profile;
- avatar switches with profile;
- one child never overwrites the other's customization state.

## 6. Ordinary Activity visual-context acceptance

Launch at least Writing and Painting from a child with non-default colors.

Verify they consume the child-resolved read-only colors where their UI uses Greia theme values, while still lacking customization write authority.

Inspect the launched Activity environment/sandbox as needed and prove:

```text
GREIA_THEME_SNAPSHOT       present and bounded
GREIA_INTERFACE_SIZE       compact|normal|large
GREIA_CUSTOMIZATION_DIR    absent for ordinary Activities
```

For My Greia itself, `GREIA_CUSTOMIZATION_DIR` is expected because it is the trusted writer.

Do not put raw customization paths or wallpaper paths into the ordinary snapshot to make a test pass.

Where a first-party Activity still bypasses shared semantic UI/typography helpers, treat that as implementation debt and migrate it through the shared layer rather than adding Activity-specific resolution/size branches.

## 7. Launcher refresh acceptance

Change each setting and return to the launcher without rebooting.

Verify:

- color updates are visible;
- wallpaper updates are visible;
- interface-size update is visible;
- avatar update is visible;
- no stale scaled wallpaper/font/icon cache survives incorrectly;
- repeated change/return cycles do not grow memory/cache without bound.

## 8. Physical Acer acceptance

At 1024x600 verify My Greia remains intentionally designed rather than merely technically contained:

- four mode buttons are comfortably distinguishable;
- color swatches are large enough for a child;
- wallpaper thumbnails remain useful;
- three size previews are obviously different;
- avatars remain reachable;
- animations/pointer rendering remain responsive;
- memory/CPU remain appropriate for the reference floor.

## 9. Required result section

Add this to the main session result:

```text
## My Greia
- focused source tests:
- colors:
- wallpaper:
- media-removal source regression:
- physical media-removal race:
- interface size compact/normal/large:
- avatar:
- profile isolation:
- launcher live refresh:
- ordinary Activity read-only theme snapshot:
- ordinary Activity customization path absent:
- responsive matrix:
- Acer 1024x600:
- defects fixed / commits:
```

Use PASS/FAIL/NOT-RUN/UNPROVEN honestly. Do not infer physical/visual PASS from source tests.
