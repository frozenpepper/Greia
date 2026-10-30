# Greia Art & Graphics System

**Status:** stable visual-system architecture, production guide and documentation index  
**Repository:** `frozenpepper/Greia`  
**Branch:** `main`  
**Last architecture review:** 2026-08-21

This is the **main entry point** for humans and agents working on Greia artwork, UI graphics, characters, environments, animation, visual assets, runtime rendering, Shell presentation, or shared visual reuse by Activities.

The intent is that a new contributor can start here, understand the architecture, and then follow links only when a narrower authority is needed.

This document owns stable architecture and system-wide rules. It does **not** own day-to-day chronology.

---

# 1. Fast navigation

For any visual-system task, read in this order:

```text
1. AGENTS.md
2. docs/design/GREIA_ART_GRAPHICS_SYSTEM.md          ← this file
3. docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
4. docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md
5. HANDOVER.md
6. skills/greia-visual-authoring/SKILL.md
7. the exact source pack/runtime files for the task
```

Narrower authorities:

| Topic | Authority |
|---|---|
| Current phase, checkpoint, progress ledger | `docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md` |
| Fast cross-session continuation | `docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md` |
| Project-wide continuation | `HANDOVER.md` |
| Practical visual-authoring workflow | `skills/greia-visual-authoring/SKILL.md` |
| **SVG authoring recipe (binding, ACCEPTED 2026-10-15)** — canvas, palette tokens, strokes, shading, forbidden constructs, budgets, review procedure | `docs/design/GREIA_SVG_AUTHORING_RULES.md` |
| Visual style, palette, typography | `docs/design/GREIA_VISUAL_STYLE_GUIDE.md` |
| Library audit and redraw backlog (2026-10-15) | `docs/reviews/visual/2026-10-15_asset_library_audit/REVIEW.md` (archived; see git history) |
| Art/core-asset requirements | `docs/design/GREIA_VISUAL_ART_AND_CORE_ASSET_REQUIREMENTS.md` |
| Character construction grammar | `docs/design/GREIA_CONSTRAINT_NATIVE_CHARACTER_GRAMMAR.md` |
| Character expressions/motion | `docs/design/GREIA_CHARACTER_EXPRESSIONS_AND_MOTION.md` |
| Source-tree inventory and shared library v1 families | `assets/visual/README.md`, `assets/catalog/shared_visuals_v1_source.toml` |
| Pack inventory | `assets/visual/packs_v0.1.toml` |
| Visual-library inventory | `assets/visual/library_v0.1.toml` |
| Activity Simulator architecture/use | `docs/development/GREIA_ACTIVITY_SIMULATOR.md` |

`AGENTS.md` makes this guide mandatory for substantive visual work.

**Art-direction reset (2026-10-15).** `docs/design/GREIA_SVG_AUTHORING_RULES.md` is the mandatory SVG recipe for every new or redrawn shared or Activity-private vector asset: flat shapes, one cocoa contour, at most two-stop fills, explicit ellipse shadows, no filters/text/raster, rendered to PNG at build time with `rsvg-convert`. The older glossy-3D raster core icons, blur-filter environment/UI packs and Activity-drawn off-model cast art are being replaced under it; the audit linked above owns the inventory, verdicts and redraw backlog. Runtime consumption is unchanged (semantic IDs → committed PNG renditions → bounded Pygame cache), and the target image installs only `assets/visual/runtime/` plus the catalogues, never SVG sources or candidate packs.

---

# 2. Product constraints

Greia is a child-first educational/game Linux appliance. The visual system must fit the product rather than behave like a desktop theme or a portfolio art project.

Hard product constraints include:

- no visible Linux shell in the normal child path;
- the Greia child Shell is the normal graphical OS surface;
- protected platform Home/Back semantics remain platform-owned;
- offline-first operation;
- x86 and ARM are co-equal targets;
- low-resource hardware remains a real constraint;
- historical reference resolutions include 800×600 and 1024×600;
- current simulator acceptance covers a broader responsive matrix;
- static presentation must remain complete when animation is absent;
- Python/Pygame Activities exist today and Web/HTML Activities are intended as first-class peers;
- the system cannot depend on a professional artist/animator manually polishing every new Activity;
- target devices must not require heavyweight runtime SVG/3D/vector stacks merely to show normal UI.

Visual richness is encouraged. Runtime unpredictability is not.

---

# 3. Core production architecture

The accepted production sequence is:

> **excellent individual assets → reusable asset packs → layered composition → subtle parallax / ambient motion / light / shadow → shared UI system → explicit semantic runtime consumption → Shell/Activity reuse**

This sequence is deliberate.

## 3.1 Asset-first means individual assets must stand on their own

Do not hide weak building blocks inside a finished mock scene.

Examples of reusable masters:

```text
tree
bush
rock cluster
fallen log
ground edge
cloud
fog strip
sunlight shaft
window
workbench
shelf
bookcase
rug
lamp
panel frame
button frame
avatar frame
soft shadow
badge
loading illustration
error illustration
```

A composed scene is downstream of these masters, not a substitute for them.

## 3.2 Simplified does not mean crude

Greia deliberately uses constraint-native art, but simplification applies to **production complexity and animation burden**, not visual quality.

Do not use as final art:

- tutorial circles as trees;
- raw rectangles as buildings;
- generic flat SaaS cards;
- unstyled Pygame primitives where reviewed shared artwork exists;
- crude full-screen mockups presented as the visual target.

The target is polished storybook / felt-board / toy-diorama presentation with:

- strong silhouettes;
- warm local light;
- shallow tactile depth;
- clean alpha edges;
- controlled gradients;
- soft cast/contact shadows;
- good readability at low resolution.

---

# 4. Visual language

Detailed palette and typography values live in `GREIA_VISUAL_STYLE_GUIDE.md` and `runtime/theme-defaults.toml`.

System-wide direction:

- warm and friendly;
- tactile and rounded without looking like generic web UI;
- restrained highlight/shadow depth;
- readable silhouettes before detail;
- decoration that supports play rather than competing with it;
- state must not rely on color alone;
- static frames must remain understandable without animation.

Current shared palette families include warm cream, sky, mint, lavender, peach, rose, sand and aqua backgrounds with sunshine, coral, leaf, ocean, grape, raspberry, orange and turquoise accents.

Current primary type choice is Nunito Sans.

---

# 5. Character system

Canonical 6-member cast (Authority: `docs/design/GREIA_CANONICAL_CAST_SYSTEM.md`):

```text
Lilli — unicorn Puff (creative / arts)
Leo   — owl Bean (logic / thinking, signature teal glasses)
Flash — white rabbit Puff (speed / agility, coral shirt & gold lightning bolt)
Dani  — friendly robot (technology / mechanics, sky casing & antenna)
Tito  — fox Puff (playful / adventure)
Momo  — friendly monster Puff (gentle / curiosity)
```

*(Historical note: `Leo` supersedes the earlier candidate identity `Nino` for the owl; historical candidate provenance is preserved in archive documentation).*

The character architecture intentionally avoids traditional detailed quadruped rigs as the default.

Identity comes primarily from:

- silhouette;
- color grouping;
- face;
- ears/horns/tufts;
- tails/wings/accessories;
- sound/behavior;
- a small number of clear authored face states.

Shared expression vocabulary:

```text
neutral
blink
happy
surprised
sleepy
```

A blink must visibly close the eyes.

Shared motion vocabulary:

```text
idle_bounce
blink
happy_hop
celebrate_pop
surprised_wobble
sleepy_sway
```

Motion favors whole-character translate/tilt/squash/stretch/wobble plus authored face swaps. Realistic shoulder/elbow/knee gait is not a normal prerequisite.

Character refinement must not block environment/UI/runtime integration.

---

# 6. Environment architecture

Scenes are built from separable depth layers.

Recommended conceptual stack:

```text
0   sky / room base
10  far background
20  mid background
30  playfield / ground
40  interactive props
50  foreground framing
60  atmosphere / fog
70  light / shadow / FX
80  characters
90  Activity-local UI
100 protected Greia platform UI/chrome where applicable
```

Exact z values are composition-specific; layer separation is the stable rule.

## 6.1 Parallax

Use small depth differences rather than dramatic camera tricks.

Typical intent:

```text
sky                  0.00
far landscape        0.05–0.10
mid background       0.10–0.20
playfield props      0.25–0.35
foreground framing   0.40–0.55
```

Parallax is optional enrichment. Static composition must remain coherent.

## 6.2 Ambient motion

Good low-cost candidates:

- slow cloud drift;
- tiny foliage/reed sway;
- low-count fireflies/dust;
- water shimmer/ripples;
- fog drift;
- subtle light breathing;
- tiny prop idles.

Do not make meaning depend on continuous motion.

---

# 7. Lighting, shadow and atmosphere are reusable assets

Depth cues should not be repainted uniquely into every scene when a shared overlay works.

Reusable families include:

```text
soft contact shadow
cast-shadow decal
highlight sheen
window-light shaft
sunlight shaft
fog/haze strip
window glow
reflection glow
reward glow
subtle vignette/framing shadow
```

Light/shadow overlays should remain independently removable where reuse benefits.

---

# 8. Current reusable source library

**Current runtime source: the shared art library v1 (2026-10-15, catalogue 0.7.0; 0.8.0 on 2026-10-16 added the `ui.keycap.*` keyboard-hint keycaps).** New Activity and Shell visuals consume it by semantic ID; the source-tree summary is `assets/visual/README.md` ("Shared art library v1") and the selection is `assets/catalog/shared_visuals_v1_source.toml`.

| Family | ID pattern | Contents |
|---|---|---|
| Biome scene layers and wallpapers (1024×600) | `bg.<biome>.<layer>` | meadow_day, night_sky, underwater, sea_surface, sky_clouds, woodland pond/autumn/snow, indoor_room walls and floors, stage, 8 wallpapers |
| Props | `prop.<family>.<name>` | food, vocab nouns, everyday, nature, blocks (+colours, outline slots), shapes, instruments |
| Creatures | `creature.<role>.<name>` | pets (readable need states), marine (incl. orca), woodland (peek/full/asleep); `prop.vocab.<animal>` aliases the creature art |
| HUD glyphs | `icon.hud.<name>` | 33 control/HUD glyphs (control-kit glyphs keep `ui/controls/v1`) |
| FX frames | `fx.<name>` | 17 multi-frame effects (`default` = peak frame) |
| Cast variants | `character.<id>` variants | pose_cheer, pose_point, pose_think, pose_wave, pose_play, sad, angry, silly |

Reuse these before drawing anything new; add to the library (never an Activity-private cast or biome redraw) only for a demonstrated gap, under `GREIA_SVG_AUTHORING_RULES.md`. The pre-reset environment packs below remain SOURCE/provenance pools and design references: they use superseded blur-filter dialects, are **not** the runtime source for new work, and are not installed on the image (only `assets/visual/runtime/` plus catalogues are).

Earlier broad source coverage (provenance pools, not runtime sources):

```text
assets/visual/environments/forest_meadow/v0.2/
assets/visual/ui/v0.1/
assets/visual/environments/workshop/v0.1/
assets/visual/environments/clinic/v0.1/
assets/visual/environments/reading_classroom/v0.1/
assets/visual/environments/fantasy_village_night/v0.1/
assets/visual/environments/water_pond/v0.1/
```

Do **not** add another environment family just to keep producing art. New environment packs require a demonstrated reusable coverage gap.

Pack metadata is design/review inventory, not runtime discovery permission.

Useful metadata includes:

- semantic asset ID;
- role/family;
- source path;
- version/status/provenance;
- alpha behavior;
- reuse dependencies;
- composition/parallax hints;
- review/evidence scope;
- whether a selected asset has been promoted into the runtime rendition set.

---

# 9. Shared UI source system

Primary source pack:

```text
assets/visual/ui/v0.1/
```

Activity-facing controls (pills, icon buttons, tool strips, HUD chips, progress dots, prompt banners, completion card, stars and HUD glyphs) are the flat control-kit art under `assets/visual/ui/controls/v1/`, composed by `greia_platform.activity_controls` per ADR 0037. Activities must not hand-draw equivalents. The packs below are the earlier UI v0.1 source.

Current source families include:

```text
panel / sheet frame
activity card frame
primary/secondary/quiet/icon buttons
button states
tabs
badges
progress track/fill/complete
speech/thought bubbles
reward frame
avatar frame
loading orbit
gentle error cloud
empty basket
portal/category frame
focus ring
soft shadow
highlight sheen
```

These files provide the visual treatment. They do not own launcher semantics.

## 9.1 Interaction state language

Use multiple cues where needed:

```text
hover/focus  → tiny lift + depth change
press        → small depress/squash
selected     → stronger frame + depth
launch       → short bounce/squiggle/pop
reward       → pop + restrained sparkle
gentle error → restrained wobble / friendly error illustration
```

Protected platform navigation remains platform-owned.

---

# 10. Semantic asset architecture

Runtime-facing visuals use Greia's explicit asset catalogue architecture.

Core owners:

```text
src/greia_platform/assets.py
assets/catalog/core_icons_v1.toml        # masters: assets/source/icons/core/v1/*.svg, built by tools/build_core_icons.py
assets/catalog/shared_visuals_v1_source.toml
assets/catalog/shared_visuals_v1.toml
```

## 10.1 One semantic namespace

Icons and shared visuals share one semantic namespace.

Examples:

```text
paint
backpack
ui.shadow.soft
ui.panel.base
ui.card.activity
ui.button.primary
ui.avatar.frame
ui.loading.orbit
ui.error.gentle
ui.empty.basket
```

A runtime visual has:

```text
semantic ID
kind
role
explicit variants
required default variant
explicit contained path
```

Consumers ask for semantics. Filenames remain implementation detail.

## 10.2 Runtime discovery is forbidden

Do not:

```text
scan assets/visual recursively
pick assets by filename convention
auto-register arbitrary SVGs
search host directories
```

Benefits of explicit catalogues:

- deterministic content;
- bounded startup work;
- review/provenance clarity;
- duplicate-ID rejection;
- path containment;
- predictable cache accounting;
- renderer-independent semantic contracts.

## 10.3 Catalogue merge contract

Core icons remain mandatory. Generated shared visuals may be optional for fail-soft consumers.

Merge invariants:

- same assets root;
- globally unique semantic IDs;
- path containment;
- malformed optional visual catalogue must not make otherwise-valid core icons unusable;
- consumers fail narrowly to their previous presentation where appropriate.

---

# 11. Source masters versus runtime renditions

High-quality SVG masters are kept separate from low-cost target files.

Current pipeline:

```text
assets/visual/ui/v0.1/*.svg
        ↓ explicit selection
assets/catalog/shared_visuals_v1_source.toml
        ↓ build-host librsvg / rsvg-convert
assets/visual/runtime/v1/.../*.png
        +
assets/catalog/shared_visuals_v1.toml
```

Build authority:

```text
tools/build_visual_renditions.py
```

Validation authority:

```text
tools/validate_visual_renditions.py
```

Entry points:

```text
make visual-assets
make visual-assets-check
```

The builder writes transactionally: failed generation must not destroy the previous good generated output.

### @2x renditions (2026-10-21)

`tools/build_visual_renditions.py` also renders, from the same SVG master, a `<name>@2x.png` sibling of each declared rendition at exactly twice its size (limit 4096 px; `--no-hires` skips them). The shared-library contract accepts only `@2x` siblings of declared outputs and checks their exact 2x size. They are optional and loaded only by the transparent high-resolution layer (`greia_platform.hires_surface`, `HIRES_SUFFIX`) at a display scale of at least 1.2x; the 1x files remain the only art on the 1024x600 reference netbook path. Activity-private PNGs get an `@2x` only where a fresh 1x render matches the shipped PNG: 13 Activity PNGs have none because the shipped PNG no longer matches its SVG (commits 47eafcd49, f22db8cb3).

## Why target runtime does not render SVG

Build-time conversion gives:

- smaller target dependency set;
- bounded startup behavior;
- predictable dimensions;
- easier cache accounting;
- lower resource risk;
- no surprise SVG parser/render cost during play.

---

# 12. Runtime Pygame visual cache

Current adapter:

```text
src/greia_platform/pygame_visual_assets.py
```

`PygameVisualSurfaceCache` realizes semantic visuals as Pygame surfaces.

Current contract:

- PNG-only runtime paths;
- key = semantic ID + variant + requested size;
- lazy Pygame decode;
- smoothscale only on cache miss when required;
- existing `ui_core.BoundedCache` reuse;
- bounded LRU entries;
- bounded requested surface area;
- explicit clear on meaningful display-size invalidation;
- no per-frame disk decode after cache hit.

This cache is a renderer adapter, not the architecture itself. Future Web or other renderer adapters must preserve semantic ID/variant meaning without copying Pygame internals.

---

# 13. Production child-Shell visual composition

Current visible shared UI is composed into the real `GreiaChildShell` through narrow presentation mixins/helpers rather than by replacing the launcher/lifecycle core.

Current implementation owners:

```text
src/greia_launcher/shared_ui_presentation.py
src/greia_launcher/profile_chrome_presentation.py
src/greia_launcher/feedback_presentation.py
src/greia_launcher/child_shell.py
src/greia_launcher/presentation.py
```

Current accepted simulator-visible consumers:

```text
ui.shadow.soft
ui.card.activity/default
ui.card.activity/focused
ui.panel.base/default
ui.button.primary/default
ui.button.primary/hover
ui.avatar.frame/default
```

Evidence scope: **SIMULATOR VISUAL REVIEW**.

## 13.1 Activity catalogue composition

The Activity catalogue currently uses:

- vertically maximized `ui.panel.base` framing;
- authored 640:420 panel ratio;
- an explicit authored inner-tray region used by the Activity grid;
- full prominent Activity cards around ~198–205 px when geometry permits;
- shared root category buttons;
- shared avatar frame on the active profile switcher;
- shared soft shadow beneath Activity cards;
- primitive/static fallback for each optional visual path where appropriate.

The panel begins directly beneath the category row (`panel_top` roughly 52–62 px at current accepted geometry) and extends to a minimal lower margin while preserving its authored aspect ratio.

This relationship matters: do not later let cards float outside the visual tray simply because an independent grid formula happens to fit the screen.

## 13.2 Profile picker composition

The profile picker uses the shared panel plus `ui.avatar.frame/default` for visible child identities. Selection, profile storage, names, secrets and hit targets remain owned by the launcher/profile system.

## 13.3 Category controls

Root category controls use `ui.button.primary/default|hover`.

The in-category Back control intentionally retains its existing dedicated geometry because the reviewed wide primary button asset is not an appropriate shape for it.

## 13.3a Award frames and the Badge Library (2026-10-16, SOURCE + DESKTOP VISUAL REVIEW)

Award frames are shared UI art: `ui.award.<bronze|silver|gold|special>` with `default`/`size_112`/`size_64` and `locked`/`locked_112`/`locked_64` renditions (160/112/64 px) built from the flat masters in `assets/source/achievements/`. Tier is carried by shape and colour (round copper medal / scalloped silver medal / cup trophy / purple rosette over a star burst; locked = grey silhouette + padlock). `PygameAchievementBadgeRenderer` composites the Activity emblem or Greia icon into the frame's cream slot once per cached size and falls back to procedural frames. The celebration reuses `fx.sparkle` (gold/secret: `fx.star_burst`, `fx.confetti`) and the cast greeter; the trophy-shelf library reuses `bg.meadow_day.home`, `ui.shadow.soft`, `fx.sparkle` and the cast `pose_point`/`happy`/`pose_think` variants. Owner of behaviour: `docs/design/GREIA_ACHIEVEMENTS_AND_BADGE_LIBRARY.md`.

## 13.4 Fail-soft rule

A corrupt/missing optional visual may disable only the affected visual treatment where possible.

Examples already proven in simulator:

- corrupt panel → cards can remain shared;
- corrupt category hover button → panel/cards remain shared;
- corrupt avatar frame → panel/cards/buttons remain shared;
- missing/malformed shared catalogue → Shell remains usable through established primitive/static presentation.

Do not catch arbitrary exceptions around the entire frame loop just to hide visual failures.

---

# 14. Current shared feedback tranche

Source-selected, awaiting current simulator acceptance:

```text
ui.loading.orbit/default
ui.error.gentle/default
ui.empty.basket/default
```

Implementation:

```text
src/greia_launcher/feedback_presentation.py
```

Intended semantics:

- `ui.loading.orbit` → normal Activity launch feedback;
- `ui.error.gentle` → friendly dismissible catalogue/error affordance;
- `ui.empty.basket` → genuine empty Activity catalogue state.

The existing primitive launch/error/empty presentations remain fallbacks.

Current acceptance protocol:

```text
2026-08-21_V5_SHARED_FEEDBACK_SIMULATOR.md (archived; see git history)
```

Do not claim the empty-state consumer PASS if current normal Greia policy cannot legitimately reach an empty presented Activity collection. `SOURCE / NOT EXERCISED` is a valid result.

---

# 15. Activity shared-visual architecture

Python Activity API owner:

```text
src/greia_platform/activity_api.py
```

Current semantic request API:

```python
get_shared_visual(asset_id, variant="default")
get_shared_visual_path(asset_id, variant="default")
```

The Activity supplies semantic ID + variant, not an arbitrary filesystem path.

Current `SharedVisualReference` exposes a read-only semantic description plus the current Python runtime realization.

Important rules:

- Activities cannot mutate the catalogue;
- arbitrary host path traversal is not an API;
- Activity-private art remains valid;
- optional shared visual failure must remain narrow;
- the Python `Path` realization is **not** the future Web transport contract.

Current first source consumer is Shape Garden. It is a useful architecture proof but is no longer allowed to block visible Shell progress.

---

# 16. Web Activity direction

Web Activities must eventually request the same semantic IDs and variant names.

Intended model:

```text
Activity semantic request
→ platform-authorized resolver
→ runtime/renderer adapter
→ controlled local asset URL/handle/resource
```

Do not expose arbitrary host filesystem paths to Web content.

Do not freeze the Web contract by mechanically copying the Python `Path` API.

---

# 17. Activity-private art versus shared Greia art

Both are valid.

Use Activity-private assets when they belong uniquely to that Activity's content/gameplay.

Use shared Greia semantic assets when they are genuine cross-product concepts, for example:

- common panels/buttons/shadows;
- shared platform characters/props where appropriate;
- shared environment pieces explicitly promoted for reuse;
- common feedback/FX families;
- shared visual states.

Do not force every Activity image into the global catalogue.

Do not privately duplicate a shared master merely to bypass the semantic resolver.

---

# 18. Performance rules

Hard rules:

- no target runtime SVG rasterization;
- no per-frame image file load;
- no per-frame directory scan;
- no per-frame smoothscale when a bounded prepared surface can be reused;
- no unbounded image/texture cache;
- no giant mandatory atlas merely to avoid designing a sane cache;
- no full-screen animation dependency for basic meaning;
- static fallback remains valid;
- expensive conversion happens at build time;
- decode/scale happens once per bounded cache key;
- cache invalidation happens only on meaningful display/theme/state changes.

Simulator frame-count evidence catches gross regressions. It does not prove physical Acer/Pi performance.

---

# 19. Activity Simulator rule for visual work

For the current owner-directed workstream, **runtime/visual/fallback/responsive acceptance is performed through the Greia Activity Simulator**.

Build preparation such as:

```bash
make visual-assets
```

may run outside the simulator. That is generation, not acceptance.

## 19.1 Headless mode

The simulator child Shell supports non-intrusive headless execution:

```text
--headless
GREIA_SIMULATOR_HEADLESS=1
```

Headless mode configures SDL dummy video/audio drivers before Pygame initialization. The real child Shell still renders full pixel buffers and remains inspectable through the loopback simulator bridge.

Preferred local-agent pattern:

```bash
GREIA_SIMULATOR_HEADLESS=1 \
python3 tools/greia_simulator.py \
  --state-dir "$HOME/.greia-simulator-<workstream>"
```

This avoids opening/foregrounding Greia windows while an owner is using the desktop.

The loopback bridge remains:

```text
http://127.0.0.1:8767
```

No Cloudflare, tunnel, hosted service or remote dependency belongs in this workflow.

Headless simulator evidence is still **SIMULATOR VISUAL REVIEW**, never physical-hardware evidence.

## 19.2 Responsive reference matrix

Current visual protocols normally cover:

```text
1024×600  + normal
1024×600  + large
1280×800  + normal
1366×768  + compact
1920×1080 + normal
1111×700  + normal
```

Do not add production `if width == ...` screenshot hacks. Fix shared semantic layout instead.

---

# 20. Evidence vocabulary

Use these evidence classes exactly:

```text
DESIGN SPEC
SOURCE
DESKTOP VISUAL REVIEW
SIMULATOR VISUAL REVIEW
PHYSICAL VISUAL REVIEW
REJECTED EXPERIMENT
```

Artwork state and evidence are different concepts.

Possible artwork states:

```text
concept
candidate
approved
superseded
rejected
```

When `approved` could be ambiguous, state scope:

```text
design_grammar
static_style_anchor
runtime_asset
release_asset
physical_acceptance
```

Examples:

- an SVG may be candidate source art without runtime consumption;
- a character may be an approved static style anchor without release approval;
- generated PNG presence is not consumer evidence;
- simulator acceptance is not physical low-resource acceptance.

---

## 20.1 Offline visual discovery, same semantic index (2026-10-08 SOURCE)

The six existing `assets/visual/authoring_library/*.toml` indexes remain
the sole developer-facing semantic inventory of generic source masters. The
`tools/visual_authoring_library.py gallery --output tmp/greia-visual-library.html`
command now produces a **local-only** browser gallery with large previews,
search, collection/status filters and direct source links.

The visual gallery is not a second asset library, not part of Greia's child
runtime, not a source approval authority and not a network service. It reads
the existing indexes using `get_all_items`, refuses source paths outside the
allowed visual tree, renders only safe escaped metadata, and loads SVG sources
as browser previews on the developer workstation. A rendered thumbnail is not
the same as an owner-reviewed 128/64 px runtime rendition. See the indexed
library README and `tests/test_visual_library_gallery.py`. Source and tests
have not yet run together in the canonical checkout.

The new `activity_incubator/tempo_di_greia/assets/source/icon.svg` / WebP
pair is an isolated **candidate Activity** visual experiment, not promoted to
the shared art library. Review existing `component.mechanical.*` library
entries and reuse the current canonical Dani/Flash actor states before making
finished Greia Time art.

# 21. Standard source-asset workflow

For new or extended source art:

1. state the real reuse gap;
2. inspect existing packs first;
3. list proposed individual masters;
4. create/revise masters individually;
5. review masters on representative grounds;
6. correct weak assets before composition;
7. record metadata/provenance/status;
8. compose target references from actual masters;
9. add restrained light/parallax/motion only where it improves depth;
10. record cross-pack reuse;
11. promote only selected assets into the explicit runtime-rendition manifest;
12. generate runtime renditions;
13. consume through semantic catalogue/resolver/renderer adapter;
14. validate through the appropriate simulator/physical protocol;
15. update plan/resume/guide when stable contracts change.

---

# 22. Standard runtime-integration workflow

For a shared visual entering a real consumer:

```text
1. source master is reviewed enough for intended scope
2. semantic ID + variants are explicit
3. source-rendition manifest selects it
4. build host generates PNG rendition
5. generated catalogue is validated
6. consumer requests semantic ID; no directory scan
7. renderer/preparation layer uses bounded caching
8. optional visual has a safe fallback where appropriate
9. simulator exercises the real consumer
10. fallback/isolation is exercised
11. responsive matrix is exercised where geometry changes
12. physical testing is added only when the claim requires it
13. evidence/docs are updated
```

---

# 23. Anti-patterns and rejected architecture

Do not reintroduce:

- complex quadruped/puppet rig as default character architecture;
- generated sprite sheets assumed production-ready;
- degrading accepted characters through redraw/overlay drift;
- fake expression overlays;
- blink states that do not close eyes;
- crude primitive scenes presented as final direction;
- full-screen mockups before source assets exist;
- decorative HTML hiding weak art;
- one-shot concept images as source architecture;
- runtime SVG rasterization on low-end targets;
- arbitrary visual-directory discovery;
- second visual catalogue/cache systems;
- per-frame PNG decode/scale;
- unbounded caches;
- simulator-specific branches in production rendering;
- per-resolution hard-coded production UI forks;
- broad exception swallowing to hide visual failures;
- endless new environment packs after coverage is broad;
- duplicating generic assets instead of shared masters;
- spending the visual workstream indefinitely on invisible proof consumers once the architecture seam is already proven.

---

## 23.1 Canonical-art contact sheet (authoring only, 2026-10-08)

Use `python3 tools/visual_family_contact_sheet.py --output <new.png>`
to compare actual source-truth 39 core, 45 built-in Activity and 30
canonical cast-expression PNGs at 128/64/48px. The tool reads current
file/manifest owners, adds no alternate art index, and never runs on a
child's computer. Unit test `tests/test_visual_family_contact_sheet.py`;
actual captured visual acceptance is GLA-008 in the living local-agent queue.
No existing art or Greia UI style has yet been changed/approved through
this new sheet.

# 24. Current implementation snapshot

The authoritative live checkpoint remains the active plan and resume file, but the stable architecture currently has these important facts:

Added 2026-10-15 at **SOURCE + headless DESKTOP VISUAL REVIEW** scope only: shared art library v1 (families above, catalogue 0.6.0), complete flat core-icon family (29 icons), on-model cast poses/expressions, shared Activity control-kit art (ADR 0037) and the storybook Shell redesign (Home, picker, Collection pages, Sea theme folder, My Creations, launch screen). No Simulator/VM/physical visual acceptance yet; no Activity consumes the library yet.

Accepted at **SIMULATOR VISUAL REVIEW** scope:

```text
ui.shadow.soft
ui.card.activity
ui.panel.base
ui.button.primary
ui.avatar.frame
```

Also accepted in current composition:

- vertically maximized Activity panel preserving 640:420 source geometry;
- Activity grid aligned to the panel's authored inner tray;
- large Activity cards retained rather than shrinking merely to fit old independent layout math;
- non-intrusive headless Activity Simulator execution through SDL dummy drivers.

Currently implemented in source and awaiting the next simulator gate:

```text
ui.loading.orbit
ui.error.gentle
ui.empty.basket
```

Current protocol:

```text
2026-08-21_V5_SHARED_FEEDBACK_SIMULATOR.md (archived; see git history)
```

Current continuation authority:

```text
docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md
```

Resume from repository state, not chat history.
