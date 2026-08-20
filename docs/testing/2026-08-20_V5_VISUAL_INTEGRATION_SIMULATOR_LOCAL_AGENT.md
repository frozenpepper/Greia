# Greia V5 Visual Integration — Local Agent Continuation Runbook

**Date:** 2026-08-20  
**Repository:** `frozenpepper/Greia`  
**Branch:** `main`  
**Workstream:** `docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md`  
**Current phase:** **V5 — Shared consumption / integration**  
**Testing rule for this session:** **ALL TEST EXECUTION AND ACCEPTANCE MUST BE HANDLED THROUGH THE GREIA ACTIVITY SIMULATOR**

---

# 0. Mission

Continue V5. Do **not** create more environment packs, character variants, mockup HTML, concept-art sheets, alternate launchers, browser demos, Cloudflare/tunnels, VMs, or a parallel graphics framework.

The visual library is broad enough. The next job is to make the existing shared visual system actually consumed by the real Greia Shell, beginning with the safest first integration:

```text
ui.shadow.soft
```

under the existing launcher Activity tiles.

The current launcher presentation, layout, Activity catalogue, lifecycle, permissions, profile state, and Pygame architecture remain authoritative. Extend them; do not replace them.

The intended V5 pipeline is:

```text
reviewed SVG master
        ↓
explicit source manifest
        ↓
build-time PNG rendition
        ↓
explicit generated runtime catalogue
        ↓
AssetCatalogue
        ↓
PygameVisualSurfaceCache
        ↓
real Greia Shell consumer
        ↓
Greia Activity Simulator acceptance
```

V5 is not “make a prettier demo.” It is to prove one clean, bounded, reusable shared-asset consumption path that can later be reused by the rest of Greia.

---

# 1. Absolute testing rule

The owner explicitly requires:

> **All tests need to be handled through the Activity Simulator.**

Interpret that strictly.

## Do not use these directly as PASS/acceptance commands

```bash
pytest
python3 -m unittest ...
make test
make verify
make visual-assets-check
```

Do not use GitHub Actions. Do not use a VM or physical hardware for this tranche. Do not invent a second standalone visual test application.

## What may run outside the simulator

Build/setup commands that create prerequisites or generated assets are allowed, specifically:

```bash
brew install librsvg
make visual-assets
```

`make visual-assets` is generation, not acceptance. If generation fails, that is a build failure and must be fixed before simulator testing.

Static source inspection is allowed, but static inspection is **not PASS evidence**.

## What counts as test evidence

Runtime, fallback, visual, responsiveness, cache behavior, interaction behavior, and regression acceptance for this V5 tranche must be observed through:

```text
tools/greia_simulator.py
tools/greia_simulator_ctl.py
the real Greia child Shell running inside the simulator
the simulator loopback canvas/state/screenshot interface
```

The simulator bridge is local loopback only:

```text
http://127.0.0.1:8767
```

There is no Cloudflare, tunnel, hosted service, or external web dependency in this workflow.

---

# 2. Read before editing

Read these in order:

```text
AGENTS.md
docs/DOCUMENTATION.md
docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
HANDOVER.md

docs/adr/0018-lightweight-ui-foundation.md
docs/adr/0029-real-runtime-activity-simulator.md
docs/development/GREIA_ACTIVITY_SIMULATOR.md
docs/testing/2026-08-19_ACTIVITY_SIMULATOR_ACCEPTANCE.md

skills/greia-visual-authoring/SKILL.md

src/greia_platform/assets.py
src/greia_platform/pygame_visual_assets.py
src/greia_platform/pygame_effects.py

src/greia_launcher/main.py
src/greia_launcher/presentation.py
src/greia_launcher/child_shell.py
src/greia_launcher/visual_assets.py

assets/catalog/core_icons_v1.toml
assets/catalog/shared_visuals_v1_source.toml

tools/build_visual_renditions.py
tools/validate_visual_renditions.py

tests/test_asset_catalogue.py
tests/test_asset_catalogue_merge.py
tests/test_pygame_visual_assets.py
tests/test_build_visual_renditions.py
tests/test_validate_visual_renditions.py
tests/test_launcher_visual_assets.py
```

The test files are executable specifications of invariants. Per owner directive, do **not** run them directly for this session’s acceptance.

Inspect the current `Makefile` targets for `visual-assets` and `visual-assets-check` as source contracts.

---

# 3. Synchronize safely

From the Greia repository root:

```bash
git status --short
git branch --show-current
git fetch origin
git checkout main
git pull --ff-only origin main
git rev-parse HEAD
```

Record the exact starting SHA.

Do not discard owner work. If the tree is dirty before you begin, inspect every change. Do not reset, clean, or overwrite unknown work.

Do not create a branch unless specifically asked. Current Greia policy expects coherent work committed to `main`.

Do not query or run GitHub Actions.

---

# 4. Evidence directories

Simulator state must remain outside the checkout:

```bash
export GREIA_V5_SIM_STATE="$HOME/.greia-simulator-v5"
```

Keep screenshots/reports in a disposable project-local directory:

```bash
mkdir -p ./tmp/v5-simulator-evidence
export GREIA_V5_EVIDENCE="$PWD/tmp/v5-simulator-evidence"
```

Do not commit `tmp/` evidence. Do not ZIP evidence unless explicitly asked.

---

# 5. Confirm the current V5 boundary

Before editing, confirm the repository already contains:

```text
AssetCatalogue typed visual support
AssetCatalogue.merged(...)
PygameVisualSurfaceCache
launcher optional shared-visual bridge
explicit shared_visuals_v1_source.toml
transactional build_visual_renditions.py
generated-rendition validator
Makefile visual-assets target
```

The active plan currently says the bridge exists but the actual Shell consumer is **not wired yet**.

Do not reinterpret already-written infrastructure as runtime consumption.

The first runtime consumer remains:

```text
ui.shadow.soft
```

Do not start consuming shared cards/buttons/panels until the soft-shadow path is stable and accepted in the simulator.

---

# 6. Generate runtime renditions

Check for the build-host rasterizer:

```bash
command -v rsvg-convert
```

On macOS, if absent:

```bash
brew install librsvg
```

Generate:

```bash
make visual-assets
```

Use the existing explicit source manifest and transactional builder.

Do **not** replace the builder with CairoSVG, ImageMagick, browser rendering, a custom SVG parser, or runtime SVG rendering merely because another tool is installed.

The target Greia runtime consumes PNG renditions, not SVG.

After generation, inspect without calling this acceptance:

```bash
git status --short
find assets/visual/runtime -type f -maxdepth 6 -print 2>/dev/null | sort
sed -n '1,240p' assets/catalog/shared_visuals_v1.toml
```

Confirm the generated catalogue includes at least:

```text
ui.panel.base
ui.card.activity
ui.button.primary
ui.shadow.soft
```

and that `ui.shadow.soft/default` points to a PNG under the explicit runtime output tree.

If `make visual-assets` fails, fix the build/root cause before proceeding. Do not manually fabricate generated catalogue data.

---

# 7. Wire the real launcher consumer

## 7.1 Use the existing bridge

Use:

```text
src/greia_launcher/visual_assets.py
```

Its intended model is:

```text
core icons mandatory
+
generated shared visuals optional
=
one merged AssetCatalogue
```

Missing or invalid generated shared visual output must preserve the established core/static launcher.

Wire the bridge into the normal launcher initialization path.

Do not add source-directory scanning. Do not add a second asset registry. Do not special-case the Activity Simulator. Do not put simulator identity in launcher logic.

## 7.2 Explicit catalogue paths

Core catalogue:

```text
<Greia root>/assets/catalog/core_icons_v1.toml
```

Optional generated shared catalogue:

```text
<Greia root>/assets/catalog/shared_visuals_v1.toml
```

Keep core icons mandatory. Shared visuals are an optional visual enhancement and must fail soft.

## 7.3 Use one bounded runtime surface cache

Use the existing:

```text
greia_platform.pygame_visual_assets.PygameVisualSurfaceCache
```

Do not create another image cache. Do not decode PNGs directly inside `_draw_activity_tile()` every frame. Do not scale from disk every frame.

The current cache already provides:

```text
semantic ID + variant + requested size key
12-entry default LRU
PNG-only enforcement
one-time scaling on cache miss
clear()
```

Use it.

## 7.4 Preserve the existing resize/cache lifecycle

`GreiaLauncherPresentation.run()` already clears presentation caches when the display size changes.

Add the shared visual cache to that existing relevant invalidation path.

Do not invent another resize observer. Do not clear the visual cache every frame. Do not retain an unbounded size-key dictionary.

## 7.5 First actual consumption: `ui.shadow.soft`

Use `ui.shadow.soft/default` as a restrained shadow underneath the existing Activity tile.

Preserve:

- the existing Activity tile rectangle;
- hit targets;
- label band geometry;
- hover state;
- selection state;
- launch motion;
- responsive grid.

The shared shadow is decoration only. It must not alter input geometry or become a new card layout.

A simple acceptable path is:

1. before drawing the existing tile/card body, request `ui.shadow.soft`;
2. scale it to a bounded footprint derived from the tile rectangle;
3. center it under the tile;
4. render it with restrained opacity;
5. continue drawing the existing tile.

If the shared asset is unavailable, use the current primitive/static shadow path.

If optional shared visual loading fails at runtime, disable that enhancement for the session and fall back. The Shell must not crash because one decorative PNG is missing or corrupt.

Catch only the narrow asset/cache/Pygame load failures that belong to this optional enhancement. Do not wrap the whole draw loop in `except Exception`.

---

# 8. Do not redesign the launcher

Do not change the following unless a genuine V5 integration defect absolutely requires a small shared fix:

```text
Activity tile dimensions
grid column logic
category navigation
Activity label band design
profile switcher
launcher interaction vocabulary
launcher category architecture
protected Activity Home/Back
Activity runtime/lifecycle
```

This tranche proves shared visual consumption. It is not a launcher redesign.

---

# 9. Start the Activity Simulator

Start the simulator:

```bash
python3 tools/greia_simulator.py \
  --state-dir "$GREIA_V5_SIM_STATE"
```

In the control plane select:

```text
Viewport: 1024x600
Interface size: normal
Capabilities: normal defaults
```

Click:

```text
Start / Apply
```

The child-facing window must be the real Greia Shell.

---

# 10. Baseline simulator capture

In another terminal:

```bash
python3 tools/greia_simulator_ctl.py status \
  | tee "$GREIA_V5_EVIDENCE/01-status-1024x600-normal.json"
```

Navigate through the normal profile flow into the Activity catalogue.

Capture:

```bash
python3 tools/greia_simulator_ctl.py screenshot \
  "$GREIA_V5_EVIDENCE/02-launcher-1024x600-normal.png"
```

Inspect the screenshot.

The shared shadow should:

- be visibly softer than the old hard primitive shadow;
- stay subordinate to the tile;
- not look like a giant dark oval;
- not make the tile float absurdly high;
- remain aligned;
- not invade neighboring cards;
- not obscure labels;
- not alter hit targets.

If it looks wrong, fix the integration before changing source art.

The current master is:

```text
assets/visual/ui/v0.1/soft_shadow.svg
```

Change the master only if the asset itself is demonstrably the problem.

---

# 11. Required simulator interaction checks

Use the live simulator, not a standalone Pygame harness.

## Selection

```bash
python3 tools/greia_simulator_ctl.py key RIGHT
python3 tools/greia_simulator_ctl.py key LEFT
python3 tools/greia_simulator_ctl.py key DOWN
python3 tools/greia_simulator_ctl.py key UP
```

Acceptance:

- shadow stays aligned with selected tile;
- selected outline still reads correctly;
- no shadow jump;
- label/hit geometry does not move unexpectedly.

## Hover

Use:

```bash
python3 tools/greia_simulator_ctl.py move X Y
```

with coordinates inside a visible Activity tile.

Acceptance:

- hover lift remains subtle;
- shadow still grounds the tile;
- no flicker;
- pointer and rendered geometry remain aligned.

## Launch motion

Select a harmless first-party Activity and trigger:

```bash
python3 tools/greia_simulator_ctl.py key RETURN
```

Acceptance:

- existing bounce/wiggle remains;
- shared shadow does not detach grotesquely;
- Activity launch still goes through normal supervisor/lifecycle;
- no launcher crash.

Return through normal Greia navigation.

---

# 12. Mandatory fallback tests — through the simulator

Stop the simulator cleanly before changing generated test preconditions.

## 12.1 Missing generated catalogue

With simulator stopped:

```bash
mv assets/catalog/shared_visuals_v1.toml \
   assets/catalog/shared_visuals_v1.toml.v5-disabled
```

Restart the simulator.

Expected:

```text
Shell starts
core icons work
Activity catalogue works
Activity tiles use fallback shadow
no crash
no blank launcher
no source-art scanning
```

Capture:

```bash
python3 tools/greia_simulator_ctl.py screenshot \
  "$GREIA_V5_EVIDENCE/10-fallback-missing-catalogue.png"
```

Stop and restore:

```bash
mv assets/catalog/shared_visuals_v1.toml.v5-disabled \
   assets/catalog/shared_visuals_v1.toml
```

## 12.2 Invalid generated catalogue

With simulator stopped:

```bash
cp assets/catalog/shared_visuals_v1.toml \
   "$GREIA_V5_EVIDENCE/shared_visuals_v1.good.toml"

printf 'this is not toml = [\n' > assets/catalog/shared_visuals_v1.toml
```

Restart the simulator.

Expected: the same fail-soft launcher fallback.

Capture:

```bash
python3 tools/greia_simulator_ctl.py screenshot \
  "$GREIA_V5_EVIDENCE/11-fallback-invalid-catalogue.png"
```

Stop and restore immediately:

```bash
cp "$GREIA_V5_EVIDENCE/shared_visuals_v1.good.toml" \
   assets/catalog/shared_visuals_v1.toml
```

Do not leave corrupt generated output in the repository.

## 12.3 Missing/corrupt optional PNG

Only perform this case after the consumer itself is narrowly fail-soft.

Back up the exact generated `ui.shadow.soft` PNG, temporarily remove it or replace it with invalid bytes, restart the simulator, and verify:

```text
launcher remains usable
fallback shadow appears
no crash loop
no repeated file/decode error every frame
```

Restore the exact good PNG immediately.

If the Shell crashes, fix the optional-consumer boundary and rerun this simulator case.

---

# 13. Required responsive simulator matrix

Exercise all of these in the Activity Simulator control plane:

```text
1024×600  + normal
1024×600  + large
1280×800  + normal
1366×768  + compact
1920×1080 + normal
1111×700  + normal
```

For every row:

1. set viewport and interface size in the simulator control plane;
2. click **Start / Apply** or **Restart**;
3. enter Activity catalogue;
4. navigate at least two tiles;
5. exercise one hover;
6. capture a screenshot;
7. record simulator status.

Suggested files:

```text
20-1024x600-normal.png
21-1024x600-large.png
22-1280x800-normal.png
23-1366x768-compact.png
24-1920x1080-normal.png
25-1111x700-normal.png
```

Acceptance:

- exact synthetic viewport is preserved;
- Activity tiles remain reachable;
- shared shadow scales proportionally;
- shadow is not stretched into an ugly full-card blur;
- no clipping at screen/card edges;
- no overlap into labels or neighboring cards;
- hit targets remain aligned;
- compact/large semantic size remains normal Greia behavior;
- no per-resolution fork appears in source.

Do not add resolution-specific branches to make screenshots green. Fix semantic/shared geometry.

---

# 14. Frame-rate/repeated-render sanity check

The simulator bridge exposes cumulative `frame_count`.

At a stable launcher screen:

```bash
python3 tools/greia_simulator_ctl.py status \
  > "$GREIA_V5_EVIDENCE/frame-before.json"

sleep 10

python3 tools/greia_simulator_ctl.py status \
  > "$GREIA_V5_EVIDENCE/frame-after.json"
```

Calculate the frame-count delta over the 10-second interval.

The Shell ticks at approximately 30 fps. Do not create a fake Mac-to-Acer hardware benchmark from this number. This is only a gross regression sanity check.

Severe frame starvation, repeated pauses, or obvious periodic disk-load stalls are a FAIL for this integration.

If poor:

- inspect repeated PNG decoding;
- inspect repeated scaling;
- inspect unstable cache keys;
- inspect cache clear frequency;
- inspect asset discovery/file scanning in draw code.

Do not solve performance by making caches arbitrarily large.

---

# 15. Cache-reuse requirement

Production requirement:

```text
no per-frame file decode
no per-frame directory discovery
no per-frame SVG rasterization
bounded cache
```

Preserve `PygameVisualSurfaceCache` as the single runtime surface cache. Make launcher requests use stable semantic IDs and stable bounded sizes.

Exercise repeated frames, selection, hover, launch and viewport changes in the simulator.

Do not add noisy permanent per-frame logging just to prove cache hits. If temporary instrumentation is essential, keep it developer-only, bounded, remove it before the final commit, and observe it while the simulator is running.

---

# 16. Failure handling

On failure:

1. preserve the first failing simulator screenshot/status;
2. identify whether root cause is generated asset, generated catalogue, catalogue merge, surface cache, launcher consumer, fallback handling, or responsive sizing;
3. fix the smallest correct shared owner;
4. restart simulator;
5. rerun exact failed case;
6. rerun 1024×600 normal;
7. rerun full matrix if geometry/cache/rendering changed.

Do not:

- suppress exceptions around the entire frame;
- catch `Exception` just to keep screenshots green;
- silently remove the shared asset;
- replace the shared system with hard-coded primitives;
- add simulator-only behavior to production launcher code;
- add hardware-model branches;
- weaken catalogue path/ID validation;
- turn SVG into a runtime dependency.

---

# 17. V5 simulator acceptance criteria

The first Shell consumer is accepted at simulator scope only when:

```text
generated catalogue present → ui.shadow.soft is consumed
missing catalogue → launcher fallback works
invalid catalogue → launcher fallback works
missing/corrupt optional PNG → launcher fallback works
normal navigation remains correct
hover remains correct
selection remains correct
launch animation remains correct
all required viewport/interface-size rows remain correct
no obvious repeated disk/decode stalls
cache remains bounded/reused by source architecture
no simulator identity enters production launcher logic
```

Evidence label:

```text
SIMULATOR VISUAL REVIEW
```

Do not call this:

```text
PHYSICAL VISUAL REVIEW
hardware PASS
Acer performance PASS
R7 PASS
release-art approval
```

---

# 18. After the first shadow consumer passes

Only after all of the above is green:

1. decide whether the same consumption contract is clean enough to reuse;
2. do not immediately restyle the entire launcher;
3. choose one next existing UI usage only if it proves reuse without layout redesign.

Later candidates already in the runtime source selection are:

```text
ui.panel.base
ui.card.activity
ui.button.primary
```

Do not consume them in this tranche unless the soft-shadow integration is complete, documented, and the owner has not asked you to stop.

---

# 19. Documentation before finishing

If implementation changed, update:

```text
docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
HANDOVER.md
```

The art plan must:

- update **Current checkpoint**;
- append a dated **Progress ledger** entry;
- record exact simulator evidence;
- record failures/rejected attempts honestly;
- state the next exact action.

If practical visual-consumption guidance changed, update:

```text
skills/greia-visual-authoring/SKILL.md
```

If simulator procedure itself changed, update:

```text
docs/development/GREIA_ACTIVITY_SIMULATOR.md
docs/testing/2026-08-19_ACTIVITY_SIMULATOR_ACCEPTANCE.md
```

Do not rewrite historical ledger entries. Do not promote simulator evidence into physical evidence.

---

# 20. Commit discipline

Commit coherent tranches as you work.

Suggested sequence:

```text
1. generated runtime renditions/catalogue
2. launcher shared-visual consumer + fallback
3. responsive/cache/fallback fixes found in simulator
4. documentation/evidence update
```

Before each commit:

```bash
git status --short
git diff --check
git diff
```

After each commit:

```bash
git rev-parse HEAD
git status --short
```

Push current `main` after coherent accepted work if credentials are available.

Do not trigger or inspect GitHub Actions.

---

# 21. Required final report

Create:

```text
LOCAL_AGENT_RESULT.md
```

It must contain:

```text
START SHA
FINAL SHA

FILES CHANGED
COMMITS CREATED

RUNTIME RENDITIONS GENERATED
- yes/no
- generated catalogue path
- shadow PNG path

SHELL INTEGRATION
- source files changed
- semantic ID consumed
- fallback behavior

SIMULATOR TEST MATRIX
- 1024x600 normal
- 1024x600 large
- 1280x800 normal
- 1366x768 compact
- 1920x1080 normal
- 1111x700 normal

SIMULATOR FALLBACK CASES
- missing catalogue
- invalid catalogue
- missing/corrupt optional PNG

INTERACTION
- selection
- hover
- launch

FRAME/RUNTIME SANITY
- frame_count before/after
- interval
- observed stalls yes/no

EVIDENCE PATHS
- screenshot/status files under ./tmp/v5-simulator-evidence/

FAILURES FOUND
- root cause
- fix
- rerun result

DOCUMENTS UPDATED

EXPLICIT NON-CLAIMS
- no physical/hardware performance claim
- no R7 closure
- no release-art approval
```

Do not ZIP the result unless asked.

---

# 22. Hard stop conditions

Stop and report instead of improvising if:

```text
the first consumer requires a second asset catalogue framework
the launcher needs runtime SVG parsing
the simulator requires a simulator-only launcher code path
the consumer requires per-resolution layout forks
optional visual failure can only be solved by swallowing broad exceptions
the visual cache must become unbounded
the Activity Simulator no longer runs the real GreiaChildShell
the change requires replacing launcher service/lifecycle composition
generated asset paths escape the Greia assets root
shared visual IDs collide with core icon IDs
work starts drifting into new environment packs or unrelated UI redesign
```

Preserve evidence and explain the blocker.

---

# 23. Exact continuation sequence

```text
SYNC CURRENT MAIN
→ READ V5 PLAN
→ CHECK/INSTALL LIBRSVG
→ make visual-assets
→ WIRE existing launcher visual bridge
→ CREATE one launcher-owned PygameVisualSurfaceCache
→ CONSUME ui.shadow.soft under existing Activity tiles
→ START Activity Simulator
→ TEST normal path
→ TEST missing/invalid/corrupt fallback through simulator
→ TEST hover/selection/launch through simulator
→ TEST full viewport/interface-size matrix through simulator
→ FIX root causes
→ REPEAT simulator acceptance
→ UPDATE plan + HANDOVER
→ COMMIT/PUSH
→ RETURN LOCAL_AGENT_RESULT.md
```

Do not drift beyond this sequence.
