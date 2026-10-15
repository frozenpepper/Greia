# Greia Asset Library Audit — 2026-10-15

**Status:** review / recommendation for main-agent and owner acceptance (no asset, source or catalogue was changed)
**Scope label:** SOURCE + DESKTOP VISUAL REVIEW (rsvg-convert 2.40.20 / PIL contact sheets, headless 1024×600 Pygame captures of all 45 Activities on the owner's Mac). No simulator-shell, VM or physical evidence.
**Checkout:** `main` at `277a0689` with other agents' uncommitted Activity edits in the working tree (screenshots reflect that working tree, not a commit).
**Companion draft:** `docs/design/GREIA_SVG_AUTHORING_RULES.md`
**Direction already decided (not re-opened here):** flat, constraint-native vector (style guide §20); Opus is the sole SVG-authoring model (bake-off winners: `icon_marble_run`, `leo_celebrate`, `scene_river_valley`); SVG → PNG at build time with `rsvg-convert`; no runtime SVG.

---

## 0. Top findings (severity-ranked)

| # | Sev | Finding |
|---|---|---|
| 1 | **S1** | **Off-model canonical cast inside Activities.** `torre_forme` labels a hard-hat *cat* "LILLI"; `quattro_amici` labels a *purple owl* "LEO" and draws Flash without shirt/bolt; `sillabe_magiche` uses a purple owl with pink glasses as its Leo; `corsa_bacche` calls an orange squirrel "Momo" (canonical Momo is a purple monster); `teatrino_fiabe` ships 6 freshly invented cast puppets (quadruped horse-Lilli, orange-brown Flash, different Dani/Tito/Momo/Leo); `treno_numeri/conductor_dani`, `labirinto_magico/tito_adventurer`, `quattro_stagioni`, `bosco_numeri`, `mondo_contrari` draw their own Tito/Flash/Dani. About 22 Activity renderer methods named `_draw_<cast>`/`_render_<cast>` exist (a few only wrap the shared PNG), while just 14 Activities consume any `character.*` shared visual. |
| 2 | **S1** | **Placeholder Activity icons ship.** `la_discesa_della_biglia` (plain orange disc), `storie_della_mia_voce` (plain red disc; in-Activity `assets/emblem_voice.png` is a plain blue ring), `enciclopedia_greia` (generic document), `bottega_delle_misure` (ambiguous gift box). 16 of 45 Activity icons have **no SVG source** at all. |
| 3 | **S1** | **39 glossy-3D raster core icons** (`assets/catalog/core_icons_v1.toml`, 117 PNG, 3.53 MiB) are the style outlier and are visible on Home (Collection icons), profile avatars, installer/launcher check/close, and inside `workshop_settings`. Several are defective at 48–128 px (`pink_star` malformed blob, `pouch`/`dinosaur` stray specks, `close_button` torn top edge). `unicorn`/`robot`/`owl`/`green_monster` are non-canonical duplicates of Lilli/Dani/Leo/Momo. |
| 4 | **S2** | **Two Activity-icon conventions coexist** — ~20 icons are a full-bleed rounded tile, ~25 are a floating object on transparency — so the launcher grid has no rhythm. Icons also bake text (`foresta_parole`, `officina_dei_suoni` "M", `sillabe_magiche` "BA/MA", `treno_numeri` "1", `bottega_delle_misure`) via `<text>` that depends on the build host's fonts. |
| 5 | **S2** | **Three incompatible vector dialects in "accepted" packs.** Cast v0.1 + bake-off winners: filter-free, cocoa contour `#4B372F`, ≤3-stop fills. Environment packs (forest v0.2/v0.3, workshop, clinic, reading, fantasy, water, generic) and 28/35 UI v0.1 masters: Gaussian-blur / drop-shadow filters, no contour on foliage, near-black `#241B12`/`#140D07` darks and Material greens. Theme palette (`runtime/theme-defaults.toml`) is used only by UI v0.1. |
| 6 | **S2** | **Runtime meadow renditions come from the superseded pack.** `assets/catalog/shared_visuals_v1_source.toml` renders 16 IDs from `forest_meadow/v0.2` (`status = "provenance"`) while `packs_v0.1.toml` marks `v0.3` as "promoted"; v0.3 feeds nothing at runtime. |
| 7 | **S2** | **The target image ships ~2.7 MiB of non-runtime SVG sources and candidate PNG previews.** `build/lib/compose.sh` rsyncs all of `assets/` excluding only `source/` and `*contact_sheet*`; `assets/visual/{authoring_kit,authoring_candidates,pack_candidates,environments,characters,…}` are therefore installed onto C0 although only `assets/visual/runtime/` + `assets/catalog/*.toml` are consumed. |
| 8 | **S2** | **Primitive-drawn art dominates.** 25/45 Activities use no shared visual and ship no runtime art besides their icon; heaviest `pygame.draw` users: `enciclopedia_greia` 1977 calls (pages/*.py illustrations), `sottomarino_giramondo` 189, `memory_meraviglie` 167, `teatrino_fiabe` 161, `viaggio_delfino` 123, `clinica_cuccioli` 118, `quattro_stagioni` 115. Emoji stand in for content/HUD art in `cucciolo_mio`, `pasticceria_magica`, `festa_delle_rime`, `officina_dei_suoni`, `faccine_momo`, `writing`, `posta_di_leo`, `treno_numeri`. |
| 9 | **S3** | **Retire-able tracked weight ≈ 7.45 MiB now, ≈ 6.4 MiB more after the P0 redraw** (§3). Largest: `assets/source/generated_variants/` 5.0 MiB (labelled non-canonical experiments), `assets/source/core_icons_v1_source.png` 2.8 MiB, core icon PNGs 3.5 MiB, `authoring_kit` + `authoring_candidates` 1.6 MiB (byte-identical or near-identical to forest v0.3). |
| 10 | **S3** | **Inventory sprawl / stale indexes.** Five overlapping inventories: `library_v0.1.toml` (still lists Nino + `specimens/a1`), `library/catalog.toml`, `packs_v0.1.toml`, `authoring_library/*.toml`, `shared_visuals_v1_source.toml`. Activity runtime PNGs are built by three different rasterizers (rsvg-convert, CairoSVG in `tools/build_encyclopedia_visual_assets.py`, ad-hoc `tools/generate_teatrino_assets.py`) or have no recorded source (`baia_delle_orche` 12 orca PNGs). |

---

## 1. Inventory (tracked files, `git ls-files`)

"Consumed" = referenced by runtime code, a runtime catalogue, the build, or an Activity manifest. "Tool" = referenced only by developer tooling/tests. "Docs" = referenced only by Markdown.

### 1.1 Shared/platform families

| Family | Files | Bytes | Format | Referenced by | Status |
|---|---:|---:|---|---|---|
| `assets/icons/core/v1/{64,128,256}` | 117 | 3,613,612 | PNG (glossy raster, extracted) | `core_icons_v1.toml` → launcher `main.py`, `catalogue_view.py` (17 Collection icons), `runtime/profile-defaults.toml` (12 avatars), installer/launcher (check/close/star), `activity_api.py`, `workshop_settings`, parent server | **Consumed** (29 of 39 IDs) |
| `assets/source/core_icons_v1_source.png` | 1 | 2,907,186 | PNG sheet | `Makefile` core-icon extraction (`tools/extract_core_icons.py`) | Tool |
| `assets/catalog/core_icons_v1_contact_sheet.png` | 1 | 695,703 | PNG | `Makefile` output; excluded from image | Generated artefact |
| `assets/source/generated_variants/` | 2 | 5,118,644 | PNG | docs only ("non-canonical experiments") | **Orphan** |
| `assets/visual/runtime/v1/{characters,forest_meadow,ui,shared}` | 62 | 1,097,000 ≈ | PNG | `shared_visuals_v1.toml` (32 IDs) → Shell presentation mixins, 12 Activities, `assets/scenes/forest_meadow_day_v1.toml` (nascondino_bosco) | **Consumed** |
| `assets/visual/characters/canonical/v0.1` | 57 | ≈146,000 | SVG (filter-free) | `shared_visuals_v1_source.toml` (30 renditions), tests | **Consumed (source)** |
| `assets/visual/ui/v0.1` | 39 | ≈45,000 | SVG (28 use filters) | 16 renditions; 10 runtime IDs consumed by Shell | **Consumed (source)** |
| `assets/visual/environments/forest_meadow/v0.2` | 35 | 64,867 | SVG (filters) | 16 renditions (14 IDs used by scene + costruiamo_ponti/shape_garden/nascondino_bosco) | **Consumed (source)**, labelled "provenance" |
| `assets/visual/environments/forest_meadow/v0.3` | 34 | ≈92,000 | SVG (filters, near-black darks) | `authoring_library` only | Tool ("promoted", not runtime) |
| `assets/visual/environments/workshop/v0.2` | 29 | ≈52,000 | SVG (filters) | `authoring_library` only | Tool |
| `assets/visual/environments/workshop/v0.1` | 25 | 25,130 | SVG | docs; `packs_v0.1.toml` dependency of reading_classroom | Docs |
| `assets/visual/environments/{clinic,reading_classroom,fantasy_village_night,water_pond}/v0.1` | 88 | ≈100,000 | SVG (filters) | `authoring_library` (water, fantasy, reading); clinic v0.1 docs only | Tool / docs |
| `assets/visual/generic/core_essentials/v0.1` | 13 | ≈33,000 | SVG (filters, navy shadow) | `authoring_library`, `tests/test_visual_authoring_library.py` | Tool |
| `assets/visual/pack_candidates/*` (7 sets) | 181 | ≈437,000 | SVG | `authoring_library` uses `clinic/2026-08-21` (13) and `generic_core_essentials` (7); canonical `catalog.toml` provenance strings; rest docs | Mostly orphan |
| `assets/visual/authoring_kit/v0.{1,2,3}-candidate` | 50 | 852,758 | SVG + PNG previews + MD recipes | docs only | **Orphan** |
| `assets/visual/authoring_candidates/2026-08-21_*` | 18 | 803,339 | SVG + PNG | docs only | **Orphan** |
| `assets/visual/characters/{lilli,momo,nino,tito}/blink.svg` | 4 | 9,768 | SVG | docs (`library/README.md`) | **Orphan** (superseded by canonical) |
| `assets/visual/specimens/a1,a2` | 12 | 27,363 | SVG/HTML/TOML | `library_v0.1.toml` | Historical |
| `assets/visual/library/` + `library_v0.1.toml` + `packs_v0.1.toml` + `authoring_library/` | 13 | ≈72,000 | TOML/MD/HTML | `tools/visual_authoring_library.py`, docs | Tool / inventory |
| `assets/source/achievements/*.svg` | 5 | ≈10,700 | SVG medals | docs only (no renditions) | Orphan source |
| `assets/boot/{frames,static,source}` | 54 | 4,946,000 ≈ | PNG | `boot_intro.py`, SD-installer build | Consumed (brand; not audited for redraw) |
| `assets/scenes/forest_meadow_day_v1.toml` | 1 | 3,150 | TOML | `nascondino_bosco/woodland_art.py` | Consumed |
| `assets/fonts/nunito-sans` | 5 | 556,000 ≈ | TTF | typography | Consumed (out of scope) |

### 1.2 Per-Activity families (45 packages)

| Family | Files | Bytes | Notes |
|---|---:|---:|---|
| `activities/*/assets/icon.png` | 45 | ≈560,000 | all 256×256; 29 have `assets/source/icon.svg`, **16 have no source**: alfabeto_leo, bosco_numeri, colline_allegre, corsa_bacche, enciclopedia_greia, faccine_momo, il_giardino_dei_numeri, la_discesa_della_biglia, mondo_contrari, quattro_amici, quattro_stagioni, sottomarino_giramondo, stelle_incantate, storie_della_mia_voce, torre_forme, viaggio_delfino |
| `activities/*/assets/source/*.svg` | 101 | ≈258,000 | 30 use filters, 6 contain `<text>` |
| `activities/*/assets/runtime/*.png` | 85 | 1,931,000 ≈ | acquario (12), baia (13, **no sources**), costruiamo_ponti (9), enciclopedia (12, CairoSVG), labirinto (4), painting (9), teatrino (16, generator script), treno (10) |
| other | 2 | ≈22,000 | `stelle_incantate/assets/achievements/stella.png`, `storie_della_mia_voce/assets/emblem_voice.png` (placeholder) |

Shared-visual consumers (14): bottega_delle_misure, casa_del_dieci, costruiamo_ponti, enciclopedia_greia, festa_delle_rime, luci_di_momo, nanna_delle_nuvolette, nascondino_bosco, officina_dei_suoni, posta_di_leo, shape_garden, specchi_magici, stelle_incantate, viaggio_delfino (some only one character PNG). **No Activity consumes any UI-kit visual except `ui.shadow.soft` (shape_garden).**

---

## 2. Quality and style conformance (verdicts)

Verdicts: **KEEP** (use as-is) · **RESTYLE** (keep geometry, convert to the rules) · **REDRAW** (new art under the rules) · **RETIRE** (remove from tracked tree).

| Family | Verdict | Severity | Notes from the rendered sheets |
|---|---|---|---|
| Canonical cast v0.1 (6 × 5 states) | **KEEP** — the reference dialect | — | Reads at 48 px; strokes 2.5/3.5, contour `#4B372F`, contact shadow `#6A5147 @ .14`. Bake-off `leo_celebrate` proves poses can be derived without drift. Missing: poses + avatar crops. |
| Core icons v1 (39 glossy raster) | **REDRAW** 29 used IDs; **RETIRE** 10 unused (`potions, treasure_chest, map, coin_bag, cup_trophy, medal, puzzle_trophy, pouch, small_heart, pink_star`) | S1 | Glossy painted 3D, inconsistent lighting, artefacts. Retiring the 10 breaks `tests/test_asset_catalogue.py` (`>= 35`) and `tests/test_visual_family_contact_sheet.py` (`== 39`) — adjust tests in the same tranche. |
| Activity icons (45) | **REDRAW** placeholders (P0); **RESTYLE** the rest onto one tile template (P1) | S1/S2 | See §0 #2/#4. Good concepts worth keeping: acquario_magico, casa_del_dieci, nanna_delle_nuvolette, stelle_incantate, teatrino_fiabe, treno_numeri, shape_garden, writing, painting. |
| Activity cast art (Pygame + puppets + baia/labirinto/treno sprites) | **REDRAW** via canonical components | S1 | See §0 #1. Drawing the cast with primitives guarantees drift; consume `character.*` PNGs (plus new poses) instead. |
| UI v0.1 (35 masters) | **RESTYLE** (drop blur filters/sheen, add contour, keep geometry & theme colours) | S2 | Already theme-palette aligned and Shell-consumed; glossy pill sheen and blurred shadows clash with flat cast. Missing components: HUD counter chip, toolbar tray, letter/number tile, star-pips, toast. |
| forest_meadow v0.2 (runtime) | **RESTYLE → new `bg.meadow` kit**, then RETIRE | S2 | Soft gradients, no contour; acceptable but off-dialect. Re-point the 16 renditions at the restyled kit. |
| forest_meadow v0.3 / workshop v0.2 | **RESTYLE** selected pieces only | S2 | Higher craft but near-black contours, Material greens, blur filters; trees too detailed for 1024×600 backgrounds behind flat characters. |
| clinic / reading_classroom / fantasy_village_night / water_pond v0.1, generic core_essentials | **KEEP as reference**, restyle only on demand | S3 | Not runtime-consumed. Generic essentials use a navy `#1A1A2E`-like floor shadow inconsistent with every other pack. |
| Encyclopedia galleries (12 runtime PNG + SVG) | **KEEP**, palette harmonise later | S3 | Good flat dioramas; dusky muted palette and realistic lion; page illustrations are 1977 primitive calls → P2 migration. |
| Achievement medal SVGs (`assets/source/achievements`) | **RESTYLE** when achievements art is scheduled | S3 | Decent; no renditions; gradient metallic. |
| Boot frames / logo | **KEEP** (brand, separate decision) | — | Not judged against Activity style. |
| authoring_kit, authoring_candidates, pack_candidates (superseded sets), legacy `characters/<id>/blink.svg`, `source/generated_variants` | **RETIRE** | S3 | Byte-identical or superseded; see §3. |

### 2.1 Duplicated metaphors

- **Owl ×4 for literacy:** alfabeto_leo, foresta_parole (purple owl icon, brown owl in-game), sillabe_magiche (purple owl), plus core `owl` avatar — none canonical except partly alfabeto_leo. Use Leo + distinct subjects (letter blocks, word tree, syllable train).
- **Night-blue tile ×4:** luci_di_momo, nanna_delle_nuvolette, stelle_incantate, festa_delle_rime.
- **Music ×3:** orchestra_animali (drum), officina_dei_suoni ("M" letter — actually phonics), festa_delle_rime (music lantern — actually rhymes). Two of the three are literacy Activities wearing music icons.
- **Fox ×4 non-canonical:** bosco_numeri, corsa_bacche icon, labirinto tito_adventurer, quattro_stagioni.
- **Palette ×2 styles:** core `palette` (Create Collection) vs `painting` Activity icon.
- **Unicorn ×3 meanings:** core `unicorn` = `my_greia` Collection **and** `settings` category **and** default avatar.

### 2.2 Emoji in place of art

Allowed for expressive text, but used as gameplay content/HUD in counting, food, pet and rhyme Activities (`🍎🍓🐟🍪`, `🔊`). Mixed with flat vector characters this reads as two products. Replace with the shared food/content prop set and HUD glyph set (P1).

---

## 3. Disk / repo weight — retire candidates

### 3.1 Retire now (no code/catalogue/test consumer; docs/provenance only)

| Path | Files | Bytes | Risk / what references it |
|---|---:|---:|---|
| `assets/source/generated_variants/` | 2 | 5,118,644 | Low — 2 docs mention them as rejected experiments. |
| `assets/visual/authoring_kit/` | 50 | 852,758 | Low — 5 docs; the 7 MD recipes (~13 KB) should be folded into `GREIA_SVG_AUTHORING_RULES.md` or kept; the 18 preview PNGs alone are 769,927. |
| `assets/visual/authoring_candidates/` | 18 | 803,339 | Low — 5 docs (2026-08-21 comparison/quality-ceiling reviews). |
| `assets/catalog/core_icons_v1_contact_sheet.png` | 1 | 695,703 | Low — regenerated by `make` core-icon target; already excluded from the image. |
| `assets/visual/pack_candidates/{canonical_characters,canonical_cast_expansion,flash_identity_revision}/2026-08-22` | 78 | 192,723 | Medium — `characters/canonical/v0.1/catalog.toml` `provenance` strings and ~20 docs point here; Nino provenance lives here. Update strings to cite the git commit instead. |
| `assets/visual/pack_candidates/{forest_meadow,workshop}/2026-08-21` | 60 | 136,144 | Low — promoted into forest v0.3 / workshop v0.2 (41 files byte-identical). |
| `assets/visual/characters/{lilli,momo,nino,tito}/blink.svg` | 4 | 9,768 | Low — `assets/visual/library/README.md`. |
| **Subtotal** | **213** | **7,809,079 (≈7.45 MiB)** | |

### 3.2 Retire after the redraw / re-point lands

| Path | Files | Bytes | Precondition |
|---|---:|---:|---|
| `assets/icons/core/v1/**` + `assets/source/core_icons_v1_source.png` + `tools/extract_core_icons.py` + Makefile target | 118 | 6,520,798 | Flat core icons rendered from SVG (expected ≈1.1 MiB for 29 IDs × 3 sizes, from bake-off PNG sizes). Update `tests/test_asset_catalogue.py`, `tests/test_visual_family_contact_sheet.py`. |
| `assets/visual/environments/forest_meadow/v0.2/` | 35 | 64,867 | `shared_visuals_v1_source.toml` re-pointed at the restyled meadow kit. |
| `assets/visual/environments/workshop/v0.1/`, `clinic/v0.1/` | 48 | 47,080 | `packs_v0.1.toml` reading_classroom dependency rewritten; clinic superseded by `pack_candidates/clinic` (which `authoring_library` already uses). |
| `assets/visual/specimens/`, `assets/visual/library/`, `library_v0.1.toml` | 17 | 44,623 | One inventory (§4.3) replaces them; update README/art-system doc. |
| `activities/baia_delle_orche/assets/runtime/tito_avatar.png` | 1 | 18,719 | Byte-identical to a `runtime/v1/characters` PNG; consume `character.tito` instead. |
| **Subtotal** | **219** | **≈6,696,000 (≈6.4 MiB)**, net ≈5.3 MiB after new icon PNGs | |

### 3.3 Image-composition weight (build fix, not a deletion)

`compose_install_target_content` should install only `assets/visual/runtime/**` plus `assets/catalog/*.toml` from the visual tree (and could skip `activities/*/assets/source/`). Today ≈2.7 MiB of SVG/candidate material lands on every target image. Owner of the fix: `build/lib/compose.sh` (not edited here). Note also `compose_install_live_content` copies only `icons/core/v1/256` while `AssetCatalogue` resolves 64/128/256 paths — harmless today only if the installer never asks for <256.

---

## 4. Recommended target library

### 4.1 Structure

```text
assets/visual/
  src/                      # the only SVG masters for shared art (one dialect)
    icons/core/             # 29 semantic icons, 256 viewBox
    icons/hud/              # 16 small HUD glyphs, 96 viewBox
    cast/<id>/              # = characters/canonical/v0.1 moved, + poses/
    bg/<biome>/             # layered 1024x600 backdrops
    props/<family>/         # nature, indoor, sea, food, toys
    ui/                     # restyled UI kit components
    fx/                     # celebration/feedback FX
  runtime/v2/               # generated PNGs only (what ships)
assets/catalog/
  shared_visuals_v2_source.toml   # the single selection + inventory index
  shared_visuals_v2.toml          # generated runtime catalogue
activities/<a>/assets/source|runtime  # Activity-private art, same rules/tool
```

One builder (`tools/build_visual_renditions.py`) for shared **and** Activity-private renditions; retire the CairoSVG and generator-script paths once their outputs are rebuilt.

### 4.2 Minimal shared set the 45 Activities need (~230 assets, one model, tranche-able)

| Family | Count | Contents / consumers |
|---|---:|---|
| Core icons | 29 | Collection/category (15), system (`check`, `x_mark`, `close_button`, `yellow_star`, `heart`), avatars (12 — owner decides whether `unicorn/robot/owl/green_monster` become Lilli/Dani/Leo/Momo faces; keep IDs, profiles store them) |
| Activity icons | 45 | one tile template (§ rules) |
| Cast poses | 6 × 4 = 24 | `pose.cheer`, `pose.point`, `pose.wave`, `pose.think` derived from canonical components (+ avatar crop via viewBox, no new art). Consumers: every Activity presenter (quattro_amici, torre_forme, sillabe_magiche, alfabeto_leo, bosco_numeri, corsa_bacche, mondo_contrari, il_giardino_dei_numeri, quattro_stagioni, teatrino_fiabe, treno_numeri, labirinto_magico …) |
| Biome backdrops (3–5 layers each) | 8 kits ≈ 32 layers | `meadow_day` (bosco_numeri, colline_allegre, costruiamo_ponti, il_giardino, mondo_contrari, quattro_stagioni, quattro_amici, shape_garden, nascondino_bosco, piccola_serra), `forest_night` (foresta_parole, luci_di_momo), `night_sky` (stelle_incantate, nanna, festa_delle_rime, casa_del_dieci), `sky_clouds` (volo_draghetto), `sea_surface` (baia_delle_orche, viaggio_delfino), `underwater` (acquario_magico, sottomarino_giramondo), `indoor_room` wall/floor variants (bottega, torre_forme, alfabeto_leo, clinica, cucciolo_mio, pasticceria, officina, posta_di_leo, sillabe, storie), `stage` (orchestra_animali, teatrino_fiabe, specchi_magici) |
| Props | ≈46 | nature 18 (tree ×3, bush ×2, rock ×2, flower ×3, cloud ×2, sun, moon, star, grass edge, fence, mushroom), indoor 10 (shelf, table, rug, window, jar, basket, crate, book stack, pot, lamp), sea 6 (coral ×2, kelp, shell, rock, bubble), food/content 12 (apple, strawberry, banana, carrot, blueberry, cherry, cookie, cupcake, fish, milk, bone, seed) replacing emoji in counting/food/pet Activities |
| UI kit | ≈30 | button primary/secondary/quiet × default/hover/pressed/disabled, round icon button × 2, pill/tab × 2, toolbar tray, HUD counter chip, card default/focused/completed/locked, panel, sheet, progress track/fill/complete + star-pip on/off, speech bubble, toast, letter/number tile (blank; text drawn at runtime) |
| FX | ≈12 | sparkle S/M/L, confetti set, star burst, heart pop, bubble, dust puff, glow ring, check pop, contact shadow small/wide |
| HUD glyphs | 16 | listen, play, pause, undo, clear, save, star, trophy, coin, heart, timer, plus, check, cross, arrow ×4 (Home/Back stay platform-owned and are **not** in this set) |

### 4.3 One inventory

Make `shared_visuals_v2_source.toml` the single selection *and* inventory (status, scope, consumers); fold `library_v0.1.toml`, `library/catalog.toml`, `packs_v0.1.toml` into it; keep `authoring_library/*.toml` only if the discovery tool still earns its keep.

---

## 5. Prioritized redraw backlog

IDs follow the existing namespace (`character.*`, `ui.*`, dotted families). Activity icons keep their package path `activities/<a>/assets/icon.png` with source `assets/source/icon.svg`.

### P0 — visible correctness / identity (do first)

1. **Cast poses** (enables removal of off-model art): `character.{lilli,leo,flash,dani,tito,momo}` variants `pose_cheer`, `pose_point` (12 SVGs). Then Activity code switches (owned by Activity agents, not art): torre_forme (cat→Lilli), quattro_amici (purple owl→Leo, Flash→canonical), sillabe_magiche (→Leo), corsa_bacche (rename player or use Momo), mondo_contrari (→Flash), bosco_numeri / quattro_stagioni (→Tito), il_giardino_dei_numeri / alfabeto_leo (drop procedural fallbacks).
2. **Teatrino puppets on-model:** `activities/teatrino_fiabe/assets/source/puppet_{lilli,leo,flash,dani,tito,momo}.svg` rebuilt from canonical components; `treno_numeri/conductor_dani.svg`, `labirinto_magico/tito_adventurer.svg` likewise.
3. **Placeholder Activity icons:** `la_discesa_della_biglia`, `storie_della_mia_voce` (+ `assets/emblem_voice.png`), `enciclopedia_greia`, `bottega_delle_misure`, `foresta_parole`, `sillabe_magiche`, `officina_dei_suoni`, `festa_delle_rime` (metaphor fixes per §2.1).
4. **Core icons — Home-visible first:** `backpack, palette, puzzle_pieces, book, magnifier, unicorn, notebook, music_star, train_blocks, coins, abc_board, block_puzzle, garden, heart, lightning` + system `check, x_mark, close_button, yellow_star`.

### P1 — coherence

5. Core avatars: `robot, owl, dinosaur, wizard, green_monster, rainbow, globe, car, star_trophy` (+ `unicorn`, `book`, `backpack` already in P0).
6. Remaining 33 Activity icons re-tiled onto the template (generate sources for the 16 sourceless ones).
7. UI kit v2 restyle: `ui.button.{primary,secondary,quiet}` × states, `ui.button.icon`, `ui.tab.pill`, `ui.card.activity` × states, `ui.panel.base`, `ui.panel.sheet`, `ui.progress.*`, new `ui.hud.counter`, `ui.toolbar.tray`, `ui.tile.letter`, `ui.progress.pip`, `ui.toast`.
8. HUD glyph set `icon.hud.*` (16) replacing emoji/primitive glyphs in HUD chips.
9. Backdrops: `bg.meadow_day.{sky,far,mid,ground}` (then re-point the 16 v0.2 renditions), `bg.night_sky.*`, `bg.underwater.*`, `bg.sea_surface.*`, `bg.indoor_room.{wall_*,floor_*}`, `bg.stage.{curtain,proscenium,floor}`.
10. Food/content props `prop.food.*` (12) and FX `fx.{sparkle,confetti,star_burst,heart_pop,check_pop}`.

### P2 — depth and cleanup

11. `bg.forest_night.*`, `bg.sky_clouds.*`; nature/indoor/sea props beyond the minimal set.
12. Encyclopedia page illustrations from primitives to SVG renditions; gallery palette harmonised.
13. `baia_delle_orche` orca sprites: author SVG sources (12 PNGs have none).
14. Achievement medals restyle (`assets/source/achievements/*`) + renditions; `stelle_incantate/assets/achievements/stella.png`.
15. Restyle reference packs (clinic, reading, fantasy, water, workshop) only where an Activity actually adopts them.

---

## 6. Evidence and limits

- Contact sheets were produced in a scratch folder (deleted) from the actual tracked SVG/PNG files; `tools/visual_family_contact_sheet.py` was used for core/Activity/cast at 128/64/48 px.
- Activity screenshots: `tools/headless_greia_activity.py --viewport 1024x600 --survival-seconds 3 --locale en`, one first frame + one post frame per Activity, all 45 exited 0. Only the opening state was seen; later game states may contain more art.
- Primitive-draw counts are `grep -c pygame.draw.|gfxdraw.` over each package's `.py` files — a proxy that also counts legitimate UI drawing.
- Nothing here claims simulator-shell, VM or physical acceptance.
