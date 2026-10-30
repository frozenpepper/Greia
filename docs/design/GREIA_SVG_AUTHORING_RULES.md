# Greia SVG Authoring Rules

**Status:** ACCEPTED (2026-10-15, main agent; tile hues per Collection accepted). Binding SVG recipe for all new and redrawn Greia shared art and Activity-private art.
**Derived from:** `GREIA_VISUAL_STYLE_GUIDE.md` §16/§20, `runtime/theme-defaults.toml`, the canonical cast masters in `assets/visual/characters/canonical/v0.1/`, and the 2026-10-15 SVG bake-off winners (`icon_marble_run`, `leo_celebrate`, `scene_river_valley`).
**Audit context:** `docs/reviews/visual/2026-10-15_asset_library_audit/REVIEW.md` (archived; see git history)
**Owners elsewhere:** colour values → `runtime/theme-defaults.toml` (UI/surfaces) and canonical cast SVGs (character ink/materials); runtime rendition contract → `tools/build_visual_renditions.py`; cast identity → `GREIA_CANONICAL_CAST_SYSTEM.md`. This file owns only the *recipe*.

The recipe in one line: **flat shapes, one warm cocoa contour, at most two-stop fills, one highlight and one shade per mass, explicit ellipse shadows, no filters, no text, no raster — rendered by `rsvg-convert` at build time.**

## 1. Canvas / viewBox per asset kind

Root element is always `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 W H" width="W" height="H">` with `width`/`height` equal to the viewBox (never `100%`).

| Kind | viewBox | Safe area / anchors | Rendered PNG sizes |
|---|---|---|---|
| Activity icon (tile) | `0 0 256 256` | tile = full canvas, `rx 48`; subject inside 24 px inset | 256 (package `icon.png`); review at 128/64/48 |
| Core semantic icon (no tile) | `0 0 256 256` | subject inside 16 px inset, transparent | 64/128/256 |
| HUD glyph | `0 0 96 96` | 8 px inset; one silhouette, ≤ 2 colours + ink | 32/48/96 |
| Cast pose / expression | `0 0 256 256` | feet baseline y 210–220, shadow centre y 228–232, head top ≥ y 36, centre x 128 | 64/128/256 |
| Prop | `0 0 256 256` or `0 0 512 256` (wide) | base on y = H − 24, contact shadow included | as consumed |
| FX | `0 0 128 128` | centred; transparent | as consumed |
| Scene / backdrop layer | `0 0 1024 600` | interaction-critical content inside x 112–912 (COVER crop on 4:3); horizon band y 280–360 | 1024×600 (opaque only for the sky/base layer) |
| UI component | its 1024×600-design pixel size + 8 px margin each side for the shadow | e.g. primary button art 300×76 on a 316×92 canvas | the size the Shell draws |

## 2. Palette tokens (do not invent new base hues)

**Surfaces, UI and tile bases — owner `runtime/theme-defaults.toml`:**

| Backgrounds | | Accents | | Text inks | |
|---|---|---|---|---|---|
| cream | `#F7EBCB` | sunshine | `#FFC234` | cocoa | `#3D2C1F` |
| sky | `#CFEAF7` | coral | `#F46F61` | navy | `#253B59` |
| mint | `#D9F2D0` | leaf | `#59B86A` | forest | `#28513A` |
| lavender | `#E8DDF7` | ocean | `#4A91D8` | plum | `#563A64` |
| peach | `#F8D8BD` | grape | `#9464C9` | charcoal | `#30343A` |
| rose | `#F5D6DF` | raspberry | `#D85683` | burgundy | `#6A3040` |
| sand | `#EEDDBA` | orange | `#F39A38` | | |
| aqua | `#CFEDE7` | turquoise | `#44B8AE` | | |

**Artwork constants — owner: canonical cast v0.1 masters (most-used values):**

| Role | Hex | Note |
|---|---|---|
| `ink` (default contour) | `#4B372F` | every cast silhouette; **not** cocoa `#3D2C1F`, which is the text ink |
| `shadow` (contact) | `#6A5147` | always with opacity, never solid |
| `cream` (bellies, muzzles, face masks) | `#FFFBEB` | |
| `blush` | `#FDA4AF` | opacity 0.5–0.55 |
| `gold` / `gold_deep` | `#FBBF24` / `#F59E0B` | beaks, horns, stars, sparkles |
| `eye` | `#342C35` | pupils; highlights pure `#FFFFFF` |
| identity colours | as in each character's `neutral.svg` | e.g. Leo glasses `#0D9488`, Momo `#7E22CE` family, Dani `#0284C7` family |

**Derived steps (the only way to get more colours):** for any token `T` —
`light = mix(T, #FFFFFF, 35–45%)`, `shade = mix(T, ink, 20–25%)`, `material contour = mix(T, ink, 55%)` (e.g. foliage outline from leaf ≈ `#51714A`; the bake-off's darker `#3F6E3A` ≈ 65 % ink is the upper bound). Record the source token in a comment on the gradient (`<!-- leaf light→leaf -->`).

**Forbidden:** pure `#000000`; near-black darks such as `#241B12`/`#140D07`; neon/fully-saturated primaries (`#FF0000`, `#00FF00`); Material/Tailwind values that are not a cast constant or a derived step.

## 3. Strokes

| Context (at master size) | Width | Colour |
|---|---|---|
| Primary silhouette — cast, prop, icon subject | 3.5 (icons may use 4–5 so the 48 px render keeps an outline) | `ink` or material contour |
| Secondary / internal shapes (belly, wings, panels) | 2.5 | same as parent |
| Fine detail (rim highlight, whisker, small line) | 1.8–2.0 | light step or ink |
| Expressive lines (closed eyes, mouths) | 2.5–4.5 | `eye` / `#72513F` |
| Scene foreground & mid masses | 2.5–3.5 | material contour |
| Scene far layers (hills, distant trees) | none or 2.0 | material contour, low contrast |

Always `stroke-linejoin="round"`; `stroke-linecap="round"` on open paths. Strokes are never thinner than 1.8 at master size, and no element may rely on a stroke under 0.5 px at its smallest supported render size.

## 4. Corner radii

Activity tile `rx 48` on 256 (inner optional board `rx 34`). Core-icon objects: soften corners ≥ 6. UI pills/buttons `rx = height/2`; cards 24–32; panels/sheets 32–40; tabs fully rounded; badges `rx = h/2`. Props: no knife-sharp outer corners — minimum 4.

## 5. Shading recipe

1. Each mass is one flat fill **or** one `linearGradient` with **at most 2 stops**, light at top/top-left → base colour at bottom (light from the upper left, everywhere).
   Canonical cast bodies keep their existing 3-stop gradients — copy them, do not re-author.
2. **One highlight** per major mass: an ellipse or crescent in `#FFFFFF` or the light step at opacity 0.6–0.9, upper-left, ≤ 8 % of the mass area.
3. **One shade** per major mass (optional): a flat patch in the shade step, lower-right, or the gradient's second stop doing that job — not both.
4. `radialGradient` only for light sources (sun halo, glow, lamp) — never for form.
5. Opacity is for highlights, blush, shadows, glows and far-layer haze only; at most 3 semi-transparent shapes per object.
6. Depth in scenes comes from layer value (far = lighter/bluer/less contrast, near = saturated with contour), never from blur.

## 6. Contact shadow (canonical template)

Every grounded cast pose, prop and icon subject that "stands" gets one flat ellipse, drawn first:

```svg
<g id="shadow">
  <ellipse cx="128" cy="229" rx="55" ry="9" fill="#6A5147" opacity="0.14"/>
</g>
```

`ry ≈ rx/6`; `rx` ≈ 40–45 % of the object's width; opacity 0.11–0.18. Airborne/hop poses: shrink `rx` by ~25 % and drop opacity to ~0.11 (as `leo_celebrate`). On tiles use a tinted shadow (`mix(tile base, ink, 60%)`) at 0.18. No `feGaussianBlur`, no `feDropShadow`, no stacked blurred copies.

## 7. Activity icon tile template

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256">
  <defs>
    <!-- ocean light (mix 35% white) → ocean -->
    <linearGradient id="marble_run_tile" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#89B8E6"/>
      <stop offset="1" stop-color="#4A91D8"/>
    </linearGradient>
  </defs>
  <g id="tile_bg">
    <rect width="256" height="256" rx="48" fill="url(#marble_run_tile)"/>
    <rect x="22" y="22" width="212" height="212" rx="34" fill="#FFF6E3" opacity="0.22"/>
  </g>
  <g id="subject"><!-- one hero subject, inset ≥ 24 px, ink contour --></g>
  <g id="accent"><!-- ≤ 2 support cues: sparkle, motion swoosh, goal --></g>
</svg>
```

Rules: one hero subject that says what the child *does*; ≤ 2 supporting cues; no letters/numbers unless they are the pedagogical object, and then as paths; no flags, no localized words, no Home/Back look-alikes. Tile hue by primary Collection (ACCEPTED 2026-10-15): create → coral, play → ocean, learn → orange, explore → leaf, my_greia → grape; turquoise for music.

## 8. Canonical cast — on-model rules

1. Start from `assets/visual/characters/canonical/v0.1/<id>/neutral.svg` (or `source_master.svg`) and **copy path data verbatim** for body, belly/muzzle, face mask, ears/horn/tufts, glasses, shirt/bolt, antennae, feet, tail.
2. Allowed transforms: whole-character `translate`; uniform `scale`; whole-body `rotate` ≤ ±8°; vertical squash/stretch ≤ ±8 % for motion keys; appendages (wings, arms, ears, tail, antennae) rotated about their root point (up to ±150°, as `leo_celebrate`); swap the face group with one of the five registered states or a new face built from the same eye/mouth vocabulary.
3. Forbidden: redrawing a silhouette path; changing any identity colour; adding clothing, hats, tools or accessories fused into the body; changing species (no "Lilli the cat"); recolouring a character to stand in for another; mirroring Leo's glasses highlight or Flash's bolt so they read wrong (mirror the whole group, then re-flip the emblem).
4. Hand-held props are a separate `prop` group drawn after the hand/wing.
5. Group order and IDs: `shadow`, `fx_back`, `character` › (`<identity_back>`, `body`, `<identity_front>`, `face`, `eyes`, `mouth`, …), `fx`. Keep the canonical group IDs.
6. Non-canonical creatures (orcas, puppies, dragons) follow the same grammar (style guide §20: 1 mass, 0–2 feet, 0–2 flaps, ≤ 3 identity cues) and must not reuse a cast name.

## 9. Forbidden constructs

`<image>` and any raster/`data:` URI; `<text>`, `<tspan>`, fonts (convert required glyphs to `<path>`); `filter`, `feGaussianBlur`, `feDropShadow`, any `fe*`; `mask`; `pattern`; `mix-blend-mode`; `<style>`/CSS classes (use presentation attributes); `<script>`, `<foreignObject>`, SMIL `<animate*>`; external `href`/`xlink:href` (only same-file `#id` references); `skewX/skewY`; `vector-effect`; editor metadata (Inkscape/Illustrator namespaces, `sodipodi:*`). `clipPath` is allowed for at most one clip per asset.

Lint before review (must print nothing):

```bash
grep -nE '<image|data:|<text|<tspan|<filter|fe[A-Z]|<mask|<pattern|<style|<script|foreignObject|<animate|blend-mode|skew|href="[^#]|xlink:href="[^#]|sodipodi|inkscape:' FILE.svg
```

## 10. Naming, IDs and files

- File names `snake_case.svg`; one asset (one semantic ID + variant) per file. Variants as sibling files: `button_primary_hover.svg`, `leo/pose_cheer.svg`.
- Semantic IDs keep the existing dotted namespace: `character.<id>` (+ variant), `ui.<component>` (+ state variant), `bg.<biome>.<layer>`, `prop.<family>.<name>`, `fx.<name>`, `icon.hud.<name>`; core icons keep their v1 IDs (`backpack`, `palette`, …) because profiles and Collections store them.
- `id` attributes are `snake_case`; gradients/clips are prefixed with the asset slug (`leo_body`, `marble_run_tile`) so composited files never collide.
- Paint order top-to-bottom in the file: `shadow` → back appendages → main mass → face/details → front appendages → `fx`.
- Coordinates rounded to ≤ 1 decimal; no transforms nested more than 2 deep.

## 11. Budgets

| Kind | SVG source | Paths | Gradients | PNG rendition |
|---|---|---|---|---|
| Activity / core icon | ≤ 6 KB | ≤ 60 | ≤ 4 | 256 px ≤ 30 KB |
| HUD glyph | ≤ 2 KB | ≤ 12 | 0–1 | 96 px ≤ 6 KB |
| Cast pose | ≤ 8 KB | ≤ 50 | ≤ 3 | 256 px ≤ 30 KB |
| Prop / FX | ≤ 6 KB | ≤ 50 | ≤ 4 | ≤ 30 KB |
| Scene layer / full scene | ≤ 16 KB / ≤ 24 KB | ≤ 200 | ≤ 8 | 1024×600 ≤ 120 KB |

## 12. 48 px legibility check (icons, HUD, cast)

At 48 px (and 64 px for cast) on both cream `#F7EBCB` and navy `#253B59`:

- the subject is nameable by an adult in 2 s without the title;
- the silhouette still has a visible ink outline and no feature smaller than ~2 px (≈ 11 units on a 256 master) carries meaning;
- gaps between distinct features ≥ 12 units at 256;
- next to its Collection neighbours in a contact sheet it is not confusable (different hero subject *and* different tile hue or silhouette);
- for cast: identity cues survive (horn+forelock, glasses, ears+shirt bolt, antenna+display, ears+tail, antennae+fluff).

## 13. Render and review procedure

```bash
R=/opt/local/bin/rsvg-convert          # build host; Debian: librsvg2-bin; >= 2.40
"$R" --version
S=$HOME/.cache/greia-claude-review/<task>   # scratch only, never inside the repo
"$R" -w 256 -h 256 asset.svg -o "$S/asset_256.png"
"$R" -w 64  -h 64  asset.svg -o "$S/asset_64.png"
"$R" -w 48  -h 48  asset.svg -o "$S/asset_48.png"
"$R" -w 1024 -h 600 -b '#CFEAF7' scene.svg -o "$S/scene.png"   # opaque base layer only
```

1. Lint (§9) and check budgets (§11) — `wc -c`, path count via `grep -c '<path'`.
2. Render the sizes above; open them at 1:1 and inspect pixels (no producer-written PASS).
3. Compare against neighbours: `python3 tools/visual_family_contact_sheet.py --output "$S/family.png"` (core/Activity/cast at 128/64/48).
4. Cast: overlay the new pose on `neutral.svg` render — silhouette paths must coincide where untransformed.
5. Shared runtime asset: add it to `assets/catalog/shared_visuals_v1_source.toml`, run `make visual-assets` then `make visual-assets-check`; commit the generated PNG + catalogue. Core semantic icon: master at `assets/source/icons/core/v1/<id>.svg` with `source_svg` in `assets/catalog/core_icons_v1.toml`, then `make assets` and `make assets-check` (`tools/build_core_icons.py`, 64/128/256). Activity-private art: commit `assets/source/*.svg` beside the rendered `assets/runtime/*.png` (or `assets/icon.png`) made with the same `rsvg-convert` command.
6. Record evidence with the correct label (SOURCE / DESKTOP VISUAL REVIEW); in-Activity look needs `tools/headless_greia_activity.py` captures; delete the scratch folder.
