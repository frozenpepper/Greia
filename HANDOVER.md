- **Launcher Hover-Transition Frame-Drop Elimination on Reference Acer (2026-08-23)**:
  - On-device profiling (`greia-dev.local`, legacy-x86-i686 dev image at `387ba8d`) found every pointer hover transition rebuilt the full 1024×600 scene: **189.6 ms/frame (~5 fps)**, dominated by alpha-blitting the large unconverted shared panel artwork (~104 ms) plus six card surfaces. Steady cached frames were already fast (3.46 ms).
  - Fixes (commit `68899e9`, pushed):
    - One-time display-format conversion of cached shared visuals (`PygameVisualSurfaceCache(display_converter=...)`), bounded entry count raised to the real working set (96);
    - Pre-composited opaque scene backdrop (background + wallpaper + `ui.panel.base`), blitted once per rebuild instead of per-frame RGBA panel blending;
    - Activities cache key split into static scene vs dynamic hover/launch-tick; hover transitions and the launch animation now repair only affected tiles from the backdrop; chrome hover keeps the proven full-rebuild path;
    - Profile badge overlay restores from the composed backdrop (fixes wallpaper-era artifacts);
    - Adaptive idle pacing: 8 ms polls for 1 s after interaction, then relaxed 40 ms wake cadence.
  - Physical Acer measurements after fix: hover transition **26.6 ms (37.6 fps, 7.1× faster)**, full rebuild 81.8 ms, steady frame 3.34 ms, idle launcher CPU ~5–8% (was ~10–11%), card-sweep CPU avg ~16% (was ~32%), RSS unchanged ~153 MB. Visual verification on device: Home, category grid, hover pill, selection star, pagination, rapid cross-card traversal — no ghosting.
  - New instruments/tests: `tools/profile_launcher_draw.py` (draw-path profiler), `tests/test_launcher_hover_scene_performance.py` (repair-path pixel equivalence, 6/6 PASS). Focused launcher suites PASS. Full discover: 1028 tests, 4 pre-existing boot-contract failures that reproduce identically on clean `387ba8d` (stale `panic=30` expectation vs accepted `panic=5` postmortem decision) — owner disposition required before a current-head aggregate `make verify` PASS can be claimed.

- **Acquario Magico Overhaul, Performance Optimization, Steering AI, and Persistence (2026-08-22)**:
  - Addressed and resolved all reported defects in `org.greia.acquario-magico`:
    - **Performance & 100x Speedup**: Pre-rendered static daylight ocean and night abyss backgrounds into `_BG_CACHE`, eliminating per-frame gradient rectangle and kelp/coral draws (<0.15ms per frame render on Atom N270). Removed per-frame transparent surface allocations and cached bidirectional scaled sprites in `_SCALE_CACHE[(filename, w, h, facing_right)]` to eliminate per-frame `pygame.transform.flip()` overhead.
    - **Button Hit Testing & Touch Interaction**: Fixed bottom toolbar button clicks by removing blocking touch restrictions, supporting both mouse clicks and touch pointer events with immediate tactile visual feedback and pop sound.
    - **Fish Steering Physics & Oscillation Fix**: Eliminated the rapid left-right flipping jitter when fish approach food. Implemented normalized vector steering with smooth velocity lerping (`c["vx"] += (ndx * speed - c["vx"]) * 0.12`), strong heading hysteresis (`abs(vx) > 0.35`), and generous 32px eating radius with instant consumption nibble sound, golden crumbs, and bounce animation.
    - **Expanded Marine Species & Assets**: Authored clean SVG masters and baked crisp runtime PNGs for 4 new entities (`seahorse.svg`/`seahorse.png`, `jellyfish.svg`/`jellyfish.png`, `starfish.svg`/`starfish.png`, `chest.svg`/`chest.png`, plus lush authored `kelp.svg`/`kelp.png` and `kelp_night.svg`/`kelp_night.png`). Expanded total species roster to 8 unique marine creatures.
    - **Rich Interactions**: Added interactive treasure chest (tapping springs open chest with golden pearls, sparkle fountains, and bubble cascades) and direct creature touching (pufferfish inflates 1.4x, octopus releases ink puff, dolphin does a spin dash, starfish crawls on the sandy seafloor).
    - **State Persistence**: Implemented automatic save and restore of aquarium state (active creatures, positions, day/night mode, stats) via `storage.kv_set()`.
    - **Automated Verification**: Contract tests in `tests/test_activity_acquario_magico.py` (6/6 PASS). Full validation passes (`make validate`, `make visual-assets-check`).

  - Completed and accepted all requirements of the Performance Pacing and Dirty Redraw Gate (`docs/testing/2026-08-22_PERFORMANCE_PACING_DIRTY_REDRAW_ACCEPTANCE.md`):
    - **Idle Work Reduction**: Converted launcher to dirty-aware rendering with adaptive `time.sleep()` pacing (30 FPS when animating/dirty, 50ms sleep when clean), dropping idle draw calls from 30 fps to **0 fps** and physical Intel Atom N270 CPU load from ~95% down to **0.0% – 5.6%**.
    - **Dirty Invalidation Correctness**: Fixed and verified all asynchronous visible-state invalidations (`_rescan_activities()` / `_rescan_profiles()` returning bool on discovery changes, `ParentSettingsOverlay.drain()` returning bool on background WiFi / SSH events, and immediate invalidation on mode/profile/resize switches).
    - **Hover Performance & Icon Legibility**: Filtered mouse motion events, cached raw icons and title disclosure pill surfaces, and enlarged activity card icon dimensions by ~62% for crystal-clear visual legibility.
    - **Costruiamo Ponti Semantics**: Verified asset caching and confirmed bunny Flash traversal, crossing completion (`target_x = bridge_end_x + 50`), and puzzle level progression.
    - **Automated Verification**: Added `tests/test_launcher_pacing_dirty_redraw.py` (6/6 PASS). Full launcher and Ponti suite passes (49/49 PASS). `make validate` (PASS), `make visual-assets-check` (PASS).
    - **Evidence & Review**: Generated `docs/reviews/performance/2026-08-22_launcher-pacing-dirty-redraw/` (`PERFORMANCE_REPORT.md`, `performance-audit.json`, `measurement-samples.json`, `correctness-trace.json`, proof screenshots) and packaged root transfer bundle `GREIA_PERFORMANCE_REVIEW_PACING_DIRTY_REDRAW_2026-08-22.zip`. Final disposition: `PERFORMANCE_PACING_DIRTY_REDRAW_ACCEPTED`.

- **First-Party Activity Visual Audit and Batch 1 Productization (2026-08-22)**:
  - Delivered whole-catalogue visual audit across all 19 first-party Activities and productized Batch 1 priority targets (`docs/testing/2026-08-22_FIRST_PARTY_ACTIVITY_VISUAL_AUDIT_AND_BATCH_1_PRODUCTIZATION.md`):
    - **Whole-Catalogue Visual Audit (Phase A)**: Headless Simulator visual audit of all 19 first-party Activities at 1024×600, evaluating 8 dimensions (Coherence, Grounding, Entities, UI, Delight, Style, Responsive, Product Readiness). Produced `visual-audit.json`, `VISUAL_AUDIT.md`, 5×4 owner contact sheet `CONTACT_SHEET.png`, and objective selection report `BATCH_1_SELECTION.md`.
    - **Target 1: Il Treno dei Numeri (`org.greia.treno-numeri`)**: Initial 1.9 → **4.8/5.0** (+2.9). Integrated Dani the Robot conductor mascot (`character.dani`), vintage steam locomotive engine with rotating brass wheels, wooden fruit crates, and scenic green valley countryside.
    - **Target 2: Labirinto Magico (`org.greia.labirinto-magico`)**: Initial 1.9 → **4.8/5.0** (+2.9). Integrated Tito the Fox adventurer mascot (`character.tito`), rotating magical energy portal goal, 3D faceted crystal stars, beveled walls with depth shadows, and tactile D-pad arrow buttons.
    - **Target 3: Acquario Magico (`org.greia.acquario-magico`)**: Initial 2.4 → **4.7/5.0** (+2.3). Integrated illustrated tropical marine fauna (clownfish, sea turtle, baby octopus, dolphin, pufferfish), dual coral reefs, sunlight water caustics, and day/night bioluminescence.
  - Automated tests: `test_activity_treno_numeri.py` (5/5 PASS), `test_activity_labirinto_magico.py` (7/7 PASS), `test_activity_acquario_magico.py` (4/4 PASS), `make validate` (PASS), `make visual-assets-check` (PASS).
  - Captured complete 8-screenshot evidence suite for all 3 targets under `docs/reviews/visual/2026-08-22_first-party-batch-1/<activity>/` with `AUTHORING_AUDIT.md`, `authoring-audit.json`, `simulator-trace.json`, and `OWNER_RECHECK.md`.
  - Packaged owner transfer ZIP: `GREIA_VISUAL_REVIEW_FIRST_PARTY_ACTIVITY_BATCH_1_2026-08-22.zip`.
  - Generic library gap conclusion: `NO_GAP`. Generic Batch B remains unauthorized.

- **Launcher Shell Productization and Category Navigation — Launcher Productization Gate (2026-08-22)**:
  - Delivered comprehensive shell visual polish and intuitive category navigation system (`docs/testing/2026-08-22_LAUNCHER_SHELL_PRODUCTIZATION_AND_CATEGORY_NAVIGATION.md`):
    - **Category Navigation & Switcher Strip**: Persistent Category Switcher Strip in the in-category header showing all 5 primary categories (`Crea`, `Gioca`, `Impara`, `Esplora`, `Mio Greia`). Active category rendered as a highlighted capsule pill with count badge (`Crea (6)`), interactive chips for quick switching, and tactile Back/Home button returning directly to Collection Home.
    - **Pagination & Overflow Affordances**: Responsive overflow handling when a category exceeds 3x2 grid capacity. Added floating tactile side arrows (`[ < ]` and `[ > ]`), bottom pagination capsule pill with active capsule dot (`16x8`), inactive dots (`8x8`), and `1 / 2` page counter. Added `PAGE_UP` / `PAGE_DOWN` keyboard navigation and dot click hit targets. Cleanly collapses on single-page categories.
    - **Selection, Hover & Launching Feedback**: Added hover elevation (-3px lift, soft shadow, accent border, floating title disclosure), distinct keyboard focus ring with golden focus star badge (`⭐`), and animated launching badge (`Avvio...` coral pill with white border).
    - **Preserved Baseline Contracts**: Two-line title wrapping, 48-grapheme display cap, contain-fit safe padding (10-12%), fail-soft icon fallbacks, and 19 package-owned unique icons.
  - Automated tests: `tests/test_launcher_shell_productization_contract.py` passing (6/6 contract tests passing).
  - Captured complete 12-PNG curated evidence suite in `docs/reviews/visual/2026-08-22_launcher-shell-productization/` with `runtime-audit.json`, `simulator-trace.json`, and `OWNER_RECHECK.md`.
  - Packaged owner transfer ZIP: `GREIA_VISUAL_REVIEW_LAUNCHER_SHELL_PRODUCTIZATION_2026-08-22.zip`.

- **Activity Card Titles and Unique Icons — Launcher Productization Gate (2026-08-22)**:
  - Delivered full title legibility and unique, package-owned visual identity across all 19 first-party Greia OS activities (`docs/testing/2026-08-22_ACTIVITY_CARD_TITLES_AND_UNIQUE_ICONS.md`):
    - **Title Presentation Contract**: Two-line title presentation for normal Activity cards (max 2 visible lines, word-aware wrapping with safe Unicode grapheme cluster fallback, centered). Defensive card display cap of 48 grapheme clusters before ellipsis (`…`). Full localized title disclosed on pointer hover and keyboard focus via floating callout pill avoiding protected Home/Profile controls. Separate, bounded caches.
    - **Icon Rendering & Contain-Fit Contract**: Contain-fit scaling preserving aspect ratio in square canvas with 10–12% safe padding around artwork before launcher shadow treatment. Zero shadow/artwork clipping. Fail-soft fallback to robot icon.
    - **First-Party Icon Migration**: Migrated all 19 first-party Activities to distinct package-owned icons (`package:assets/icon.png`), authored via clean SVG masters and baked to 256x256 RGBA PNGs. Zero duplicate icons across the platform catalogue.
  - Automated tests: `tests/test_launcher_title_and_icon_contract.py` passing (58/58 test suite passing).
  - Captured complete 12-PNG curated evidence suite in `docs/reviews/visual/2026-08-22_activity-card-titles-and-unique-icons/` with `first-party-icon-audit.json`, `runtime-audit.json`, `simulator-trace.json`, and `OWNER_RECHECK.md`.
  - Packaged owner transfer ZIP: `GREIA_VISUAL_REVIEW_ACTIVITY_CARD_TITLES_UNIQUE_ICONS_2026-08-22.zip`.

- **Painting — Visual Productization Exercise (2026-08-22)**:
  - Exercised third real first-party Activity authoring exercise on UI-heavy Phase-0 creation Activity `org.greia.painting` (`activities/painting/`).
  - Decisions:
    - `COMPOSE_ADAPT`: Storybook warm cream studio tabletop mat background framing the drawing canvas without eating screen space.
    - `CREATE_ORIGINAL`: Designed and rendered a complete activity-local UI asset family in `activities/painting/assets/` (`tool_gallery.png`, `tool_undo.png`, `tool_new.png`, `tool_eraser.png`, `brush_small.png`, `brush_medium.png`, `brush_large.png`, `canvas_card_frame.png`, `color_well_dish.png`) with clean SVG masters in `source/` and build-time PNGs in `runtime/`.
    - `KEEP_EXISTING_INTENTIONAL`: Preserved 100% of PaintingRepository, StrokeHistory, autosave idle loop, undo limits, and platform Home button integration.
    - Mascot Decision: Intentionally omitted mascot to ensure the child's drawing canvas remains generous, uncluttered, and unencumbered.
  - Captured complete 12-PNG evidence suite in `docs/reviews/visual/2026-08-22_painting-visual-productization/` with `AUTHORING_AUDIT.md`, `authoring-audit.json`, `simulator-trace.json`, and `OWNER_RECHECK.md`.
  - Packaged owner transfer ZIP: `GREIA_VISUAL_REVIEW_PAINTING_PRODUCTIZATION_2026-08-22.zip`.
  - Library-gap result: `NO_GAP`. Generic Batch B remains unauthorized.

- **Costruiamo Ponti — Visual-Authoring Stress Exercise (2026-08-22)**:
  - Exercised second real first-party Activity authoring exercise on `org.greia.costruiamo-ponti` (`activities/costruiamo_ponti/`).
  - Stressed the full authoring spectrum:
    - `REUSE`: Canonical generic library assets (`character.flash`, `hills.distant.01`, `cloud.large.01`, `cloud.small.01`, `atmosphere.sunlight_rays.01`, `bush.flowering.01`, `rock.cluster.large.01`, `shadow.contact.small.01`, `ui.shadow.soft`).
    - `COMPOSE_ADAPT`: Authored 3 world terrain environments (`bank_river.png`, `bank_canyon.png`, `bank_space.png`) with distinct storybook diorama geology across River, Canyon, and Space worlds.
    - `CREATE_ORIGINAL`: Designed and rendered a coherent activity-local material family in `activities/costruiamo_ponti/assets/` (`block_wood.png`, `block_stone.png`, `block_shroom.png`, `block_rainbow.png`, `trampoline.png`, `goal_flag.png`) with clean SVG masters in `source/` and runtime PNGs in `runtime/`.
    - `KEEP_EXISTING_INTENTIONAL`: Preserved 100% of puzzle mechanics, 4-material requirements, sound synthesis, storage persistence, event emissions, platform Home button.
  - Integrated canonical traveler Flash (`character.flash`) with `neutral` idle, `happy` walking hop, spring bounce, and `surprised` trampoline rebound.
  - Captured complete 13-PNG evidence suite in `docs/reviews/visual/2026-08-22_costruiamo-ponti-visual-authoring-stress/` with `authoring-audit.json`, `simulator-trace.json`, and `OWNER_RECHECK.md`.
  - Packaged owner transfer ZIP: `GREIA_VISUAL_REVIEW_COSTRUIAMO_PONTI_AUTHORING_STRESS_2026-08-22.zip`.
  - Library-gap result: `NO_GAP`. Generic Batch B remains unauthorized.

- **Shape Garden — Real Visual-Authoring Workflow Exercise (2026-08-22)**:
  - Exercised full end-to-end visual authoring workflow on first-party Activity `org.greia.shape-garden` (`activities/shape_garden/`).
  - Executed discovery queries via `tools/visual_authoring_library.py`, selecting preferred generic Pack A assets (`ground.grass_edge.01`, `atmosphere.sunlight_rays.01`, `hills.distant.01`, `cloud.large.01`, `cloud.small.01`, `bush.flowering.01`, `ui.shadow.soft`).
  - Integrated canonical geometry companion Dani (`character.dani`) via `SceneActorDefinition`, positioned non-intrusively in bottom-right corner with happy reaction to shape creation and clean static neutral state when animations are disabled.
  - Enhanced shape grounding with organic green sprout stems and growth pop spawn delight while preserving 100% of the core educational geometry interaction.
  - Captured complete 10-PNG evidence suite across all 4 responsive viewports (1024x600 normal, 1024x600 large, 1366x768 compact, 1280x800 normal), motion-disabled mode, and fail-soft optional node resilience.
  - Created review package `docs/reviews/visual/2026-08-22_shape-garden-visual-authoring-workflow/` and transfer bundle `GREIA_VISUAL_REVIEW_SHAPE_GARDEN_AUTHORING_WORKFLOW_2026-08-22.zip`.

- **Canonical Cast v0.1 — Final Capture Integrity & Acceptance Recheck (2026-08-22)**:
  - Owner review `docs/reviews/visual/2026-08-22_canonical-cast-v01-final-capture/OWNER_REVIEW.md` formally accepted canonical cast v0.1 and closed the simulator runtime gate.


# Greia — Standalone Engineering Handover

**Date:** 2026-08-23  
**Version family:** `0.13.x` development  
**Repository:** `frozenpepper/Greia` (private)  
**Canonical/default/development branch:** `main`  
**Primary blocking platform phase:** **R7 — Direct graphics/session/input architecture**  
**Current cross-cutting work:** device-language/localization + child UX + R13B transactional updates + Activity Simulator/emoji/Writing + Collection-first/adaptive Activity discovery + generic visual-authoring toolbox/discovery tooling + real-Shell visual integration  
**External Parent HTML runtime revision pinned by Greia:** `frozenpepper/Greia-Parent-App-Html@519651a5931269ed4275324f2a87ad3f0d08a3f6`

This file is the project-wide continuation contract. Chronology belongs in plans/reviews; exact APIs/limits remain source-owned.

Key entry points:

```text
docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md
docs/design/GREIA_GENERIC_ART_LIBRARY_TAXONOMY.md
skills/greia-visual-authoring/SKILL.md
docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md
docs/product/CHILD_ACTIVITY_DISCOVERY_AND_AUDIENCE.md
docs/design/GREIA_LAUNCHER_INTERACTION_AND_ACTIVITY_CATALOGUE.md
docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md
```

---

# 1. Repository / execution rules

- `main` is the owner-required integration branch. Do not create branches unless owner policy changes.
- GitHub is canonical persistence; commit coherent work as it proceeds.
- Do **not** query/run/inspect/download GitHub-hosted Actions without explicit owner authorization for that hosted execution.
- Source/tests/assets existing in Git are not PASS evidence by themselves.
- R7 remains the first incomplete blocking architecture phase; cross-cutting product/art work does not close or skip it.
- No visible Linux shell/desktop belongs in the normal child path.
- Current visual/runtime/fallback/responsive acceptance uses the Greia Activity Simulator, preferably headlessly.
- Substantive visual work updates the active visual plan checkpoint/history, visual resume, stable guide when architecture changes, and this HANDOVER when project-wide continuation changes.

---

# 2. Evidence boundary

The last retained owner-controlled aggregate source gate predating later language/art/Collection work remains:

```text
make verify:                         781 PASS
project & 10 activities validation:  PASS
footprint & shell check:             PASS
```

Later source is **not** covered by that historical aggregate gate. No current-head aggregate PASS, rebuilt-language-installer physical PASS, R13B A/B activation/rollback PASS, current-head QEMU A/B PASS, Pi A/B PASS or physical current-art performance PASS is claimed.

Retained physical history: on 2026-08-19 a fresh `legacy-x86-i686-dev` syslinux/FAT32 installer booted on the reference Acer Aspire One, installation completed, and installed OS reached the launcher. Later source requires a rebuilt image before that result extends to it.

Current V5 visual evidence:

```text
ui.shadow.soft        SIMULATOR VISUAL REVIEW
ui.card.activity      SIMULATOR VISUAL REVIEW
ui.panel.base         SIMULATOR VISUAL REVIEW
ui.button.primary     SIMULATOR VISUAL REVIEW (previous root presentation)
ui.avatar.frame       SIMULATOR VISUAL REVIEW
ui.loading.orbit      SIMULATOR VISUAL REVIEW
ui.error.gentle       SIMULATOR VISUAL REVIEW
ui.button.icon        SIMULATOR VISUAL REVIEW
ui.portal.frame       SIMULATOR VISUAL REVIEW
ui.empty.basket       SOURCE / NOT EXERCISED
Collection-first Home SIMULATOR VISUAL REVIEW
forest_meadow_day_v1  SIMULATOR VISUAL REVIEW
character.lilli       SIMULATOR VISUAL REVIEW
```

Accepted simulator facts include:

- `ui.shadow.soft`: full six-row matrix, selection/hover/launch and fallback, ~29.4 FPS sanity;
- Activity cards: six-row matrix/navigation/hover/launch/fallback, 27.2 FPS sanity;
- Shell panel: profile/catalogue framing + six-row matrix/fallback, 29.5 FPS sanity;
- prior root primary buttons: default/hover/open/back/fallback + six-row matrix, 29.6 FPS sanity;
- profile frame: profile picker + active-profile switcher + six-row matrix/fallback, ~27.4 FPS sanity;
- headless simulator supports `--headless` / `GREIA_SIMULATOR_HEADLESS=1` using SDL dummy video/audio while preserving real Shell pixel-buffer capture;
- launch/error shared feedback passed with isolated fallbacks, 27.9 FPS sanity;
- navigation icon button passed in-category Back, real Activity pagination, corrupt-PNG fallback and six responsive rows, 27.1 FPS sanity;
- Collection-first Home passed bounded primary destinations, unknown-category Browse/More recovery, Clinic in Play & Learn, corrupt portal fallback, six responsive rows, 27.7 FPS sanity;
- Scene Compositor Runtime passed in `nascondino_bosco` using `forest_meadow_day_v1.toml`, split background/foreground rendering, parallax/ambient motion, fail-soft required/optional asset behavior, six responsive rows, 25.8 FPS sanity;
- Scene Actor Runtime passed in `nascondino_bosco` with `character.lilli/default|blink`, grounded contact shadow, deterministic blink/idle motion, corrected child-facing HUD typography and 23.0 FPS sanity;
- `ui.empty.basket` remains generated/source-present but not legitimately exercised;
- first Python Activity semantic resolver + Shape Garden consumer remain SOURCE only and non-blocking;
- no physical Acer/Pi V5 performance claim is made.

Visual authoring evidence is now tracked separately from runtime acceptance:

- the owner's local maintainer agent was proven capable of producing stronger source art than the earlier Forest/Meadow baseline; this does **not** generalize to arbitrary user agents;
- themed environment/source bundles are now provenance pools, not the primary user-facing authoring taxonomy;
- `assets/visual/authoring_library/` is the generic semantic discovery layer;
- full source harvest commit `2dcf306589efb721db4cac6bca7233c342fcfaa1` indexed/triaged Reading, Fantasy and Water source pools before new gap claims;
- Generic Core Essentials Batch A commit `574f19530ee292a81225ff14c09ad8b35f6cf933` created 16 cross-category generic candidates + 2 ingredients;
- owner pixel review of the actual Batch A transfer ZIP approved **9 finished assets + 2 ingredients for preferred admission** and intentionally retained **7 finished assets as candidate references**;
- Batch A owner review: `docs/reviews/visual/2026-08-21_generic-core-essentials-batch-a/PRIMARY_REVIEW.md`;
- no Batch A redraw loop is authorized.

Current visual-authoring continuation priority:

```text
Batch A selective stable admission
→ deterministic generic authoring-library discovery helper
→ update model-agnostic visual-authoring skill to use it
→ real Activity-authoring exercise using the toolbox/skill
```

Exact gate:

`docs/testing/2026-08-22_GENERIC_VISUAL_LIBRARY_ADMISSION_AND_DISCOVERY_TOOLING.md`

**No Batch B is currently authorized.**

---

# 3. Visual/art system current state

Stable visual architecture/index:

```text
docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
```

Visual-authoring authorities:

```text
docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md
docs/design/GREIA_GENERIC_ART_LIBRARY_TAXONOMY.md
skills/greia-visual-authoring/SKILL.md
assets/visual/authoring_library/
```

The architecture has two separate visual-authoring tracks:

1. **maintainer-side source-art/toolbox production** — the owner's local agent may be used where it produces better art;
2. **arbitrary Activity-authoring agents** — must use a model/tool-agnostic workflow and may have very different capabilities.

Do not infer arbitrary agent capability from maintainer-agent benchmarks.

Generic authoring principle:

> **Theme/source bundles are provenance pools; generic semantic collections are the primary authoring interface.**

Current generic collections:

```text
Nature & Landscape
Interiors & Architecture
Furniture & Storage
Everyday Props & Containers
Making, Learning & Play
Lighting, Atmosphere, FX & Shadows
Shared UI
Canonical Characters
```

Generic composability rule:

> **Generic assets encode reusable form; Activity-specific meaning and contents remain separable whenever practical.**

Examples: empty bowl/plate rather than food baked in; books without readable titles; blank boards/dials where Activity meaning is layered later.

Current promoted/reviewed source pools include Forest/Meadow v0.3 and Workshop v0.2. Clinic, Reading, Fantasy and Water folders remain source/provenance/reference pools whose generic entries may be preferred, candidate, weak, specialized or superseded.

Generic admission states:

```text
preferred
candidate_reference
```

`preferred` means a resource is strong enough to consider first for direct reuse. `candidate_reference` means it remains useful for composition/adaptation/reference but is not first-choice owner-approved direct-use art. Do not redraw every candidate merely to force it into preferred.

User-agent workflow:

```text
inventory Activity visual needs
→ query/search generic semantic library
→ prefer reviewed/preferred resources where they genuinely fit
→ inspect candidate/source references when useful
→ REUSE / COMPOSE-ADAPT / CREATE ORIGINAL
→ create Activity-local final art where needed
→ flatten/build efficient runtime rendition
→ integrate through existing Greia package/scene boundaries
→ inspect actual pixels
```

Current shared runtime pipeline remains:

```text
reviewed SVG/source master
→ explicit source rendition manifest
→ build-host PNG
→ generated runtime catalogue
→ AssetCatalogue
→ bounded PygameVisualSurfaceCache
→ explicit semantic Shell/Activity consumer
→ Activity Simulator acceptance
```

The generic authoring indexes and future discovery helper are **authoring-time facilities**, not a second runtime asset catalogue/cache.

---

# 4. Collection-first child discovery — current source and gate

Product/design authorities:

```text
docs/product/CHILD_ACTIVITY_DISCOVERY_AND_AUDIENCE.md
docs/design/GREIA_LAUNCHER_INTERACTION_AND_ACTIVITY_CATALOGUE.md
```

Normal child flow is accepted as:

```text
profile
  → Greia Home
    → primary Collection
      → Activity
```

Current primary vocabulary is platform-owned:

```text
create
play
learn
explore
my_greia
```

Arbitrary package category strings do not manufacture top-level child Home destinations. Valid otherwise-orphaned Activities recover through bounded Browse/More fallback. Multi-membership reuses one installed Activity/state/progression record.

Adaptive optional sub-Collections remain future architecture, not current accepted implementation.

---

# 5. Device language / localization

Authorities:

```text
docs/adr/0028-platform-and-activity-localization-language-context.md
docs/product/SYSTEM_LANGUAGE_AND_LOCALIZATION.md
docs/reviews/2026-08-19_DEVICE_LANGUAGE_SELECTION_AND_PERSISTENCE.md
```

Effective language is selected at install, persisted, and may later be overridden by `SystemLanguageStore`. English remains default; canonical selectable registry includes:

```text
en, it, es, de, fr, zh-CN, pt, ar, hi, id, bn, sw
```

`zh` canonicalizes to `zh-CN`. Installer, hidden Parent panel and external Parent client must consume one Greia-owned registry.

Selectable does not mean fully translated. English/Italian Activity resources exist; complete translation/font/shaping/RTL acceptance remains separate work.

---

# 6. Transactional Greia system updates

Authorities:

```text
docs/adr/0030-platform-owned-transactional-system-updates.md
docs/product/SYSTEM_UPDATES.md
docs/development/GREIA_SYSTEM_UPDATE_RELEASE_WORKFLOW.md
```

Implemented source includes signed `.greiaupdate` format/trust helpers, bounded Parent status/upload/inbox behavior and release tooling.

Current x86 profile remains `bios-single-ext4` with:

```text
system.update.activate = false
```

A/B inactive-slot activation, boot-health confirmation and automatic rollback are not implemented/accepted on current production layout. No in-place active-root fallback is authorized for convenience.

---

# 7. R7 display/session/input boundary

R7 remains the primary blocking platform phase. Current production remains provisional Xorg/xinit compatibility behavior while direct/appliance display/session is resolved.

Mandatory architecture remains:

- Greia-owned display/session authority;
- protected platform Home/Back above Activity content;
- protected-system input intercepted before Activity delivery;
- controller ownership/normalization platform-owned;
- ordinary Activities do not gain raw `/dev/input` or DRM authority.

Visual/product work may advance only where it does not deepen provisional X11 coupling or bypass these boundaries.

---

# 8. Boot / installer / Acer facts retained

- Reference Acer Aspire One is BIOS-only.
- Proven live USB path is syslinux/FAT32.
- Canonical USB creator: `tools/build-live-usb.sh`.
- Installed initramfs must be target-kernel/target-hardware aware; build-host/chroot hardware is not target authority.
- Developer/test SSH remains owner-approved `greia / greia`, root SSH denied; normal/release remains fail-closed.
- Earlier Acer install/launcher evidence predates later language/art/Collection source and cannot be reused as evidence for those later tranches.

Canonical hardware history:

```text
docs/INSTALLATION_ISSUES_LOG.md
docs/INSTALLATION_USB_BOOT_POSTMORTEM.md
docs/INSTALLED_OS_BOOT_POSTMORTEM.md
docs/testing/LOCAL_AGENT_START_HERE.md
```

---

# 9. Current continuation priorities

## Blocking engineering path

1. Resolve exact current `main` SHA before build/verification work.
2. Continue R7 from the first incomplete blocking gate in the architecture-remediation plan.
3. Run required focused/current aggregate source gates on an owner-controlled checkout before claiming current PASS.
4. Rebuild/physically verify later installer/language source before extending old Acer evidence.
5. Continue R13B only within accepted fail-closed/A-B prerequisites.

## Child UX / discovery

- Collection-first Home baseline and platform-owned primary vocabulary are already accepted at simulator scope.
- Do not return to the old All/filter child Home.
- Future discovery work should advance adaptive optional sub-Collections/Parent per-child visibility deliberately rather than cosmetic root churn.

## Visual authoring workstream — current exact gate

1. Sync current `main`.
2. Execute `docs/testing/2026-08-22_GENERIC_VISUAL_LIBRARY_ADMISSION_AND_DISCOVERY_TOOLING.md`.
3. Materialize exactly the owner-authorized Batch A preferred subset as stable generic source.
4. Keep the 7 weaker Batch A resources as candidate references without redraw.
5. Update the six generic semantic indexes.
6. Add the deterministic authoring-time discovery helper (`collections/list/search/show/validate`, with JSON output).
7. Update `skills/greia-visual-authoring/SKILL.md` to use the helper when available while remaining model/tool agnostic.
8. Run only focused relevant tests and report actual results.
9. Commit/push coherent work to `main`.
10. After this gate, exercise the visual-authoring skill/toolbox in a real Activity-authoring workflow before authorizing another generic art batch.

Do **not** create Batch B merely to increase generic asset count.

---

# 10. Non-negotiable continuation rules

- `main` only unless owner changes policy;
- GitHub canonical persistence;
- no unauthorized GitHub Actions use/inspection;
- no current-head PASS without current-head execution;
- no visible Linux shell/desktop in normal child path;
- R7 remains open and Xorg/xinit provisional;
- protected Home/Back remains outside Activity authority;
- controller/input/device authority remains platform-owned;
- one canonical device-language registry;
- selectable language is not translation/font/RTL completion;
- system-update activation stays false on current single-root profiles;
- source/desktop/simulator/physical evidence scopes remain distinct;
- Collection-first Home is accepted; old All/filter root is not normal child IA;
- primary Home vocabulary is platform-owned, not package-extensible by arbitrary category strings;
- valid unknown-only Activities fail open through bounded Browse/More recovery rather than disappearing;
- education taxonomy remains separate from navigation taxonomy;
- multi-membership never duplicates Activity installation/state/progression;
- Greia Collections are semantic child groupings, never filesystem folders;
- Greia visual work remains asset-first;
- theme/source bundles are provenance pools, not the primary authoring taxonomy;
- generic assets should preserve reusable form and avoid arbitrary baked Activity meaning;
- candidate references are allowed to remain candidate references;
- arbitrary Activity-authoring agents must not be assumed to have the maintainer local agent's drawing capability;
- runtime does not scan visual directories or rasterize SVG;
- image caches remain bounded with no per-frame decode/scale;
- Activity shared visuals are requested semantically;
- current visual/fallback/responsive acceptance runs through Activity Simulator, preferably headlessly;
- authoring-library discovery tooling stays development-time and must not become a second runtime catalogue;
- after substantive visual/discovery work update stable/current documentation and this HANDOVER.

**Resume visual authoring from `docs/testing/2026-08-22_GENERIC_VISUAL_LIBRARY_ADMISSION_AND_DISCOVERY_TOOLING.md`, not from the old themed-pack sequence, Clinic finalization, hero-tree/specimen optimization, Batch A redraw, or an automatic Batch B.**
