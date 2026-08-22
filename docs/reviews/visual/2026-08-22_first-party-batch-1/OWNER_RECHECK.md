# First-Party Activity Visual Audit & Batch 1 Productization — Owner Recheck

**Date:** 2026-08-22  
**Status:** **BATCH 1 COMPLETE & OWNER READY**  
**Repository:** `frozenpepper/Greia`  
**Target Resolution:** 1024×600 NORMAL (with verified 1366×768 COMPACT & 1280×800 NORMAL responsive scaling)

---

## 1. Whole-Catalogue Visual Audit Summary (19 Activities)

A full, real Simulator-based visual audit was executed across all 19 first-party Activities using headless display captures at 1024×600. Every Activity was scored from 1 (prototype) to 5 (reference) across 8 dimensions.

### Quality Ranking Highlights
- **Productization References (5.0/5.0):**
  - `org.greia.shape-garden` (Giardino delle Forme)
  - `org.greia.costruiamo-ponti` (Costruiamo Ponti)
  - `org.greia.painting` (Colora e Disegna)
- **High Visual Readiness (4.0 – 4.6):**
  - `org.greia.nascondino-bosco` (4.6)
  - `org.greia.cucciolo-mio` (4.1)
  - `org.greia.pasticceria-magica` (4.0)
  - `org.greia.teatrino-fiabe` (4.0)
  - `org.greia.orchestra-animali` (4.0)
- **Moderate Polish Candidates (3.0 – 3.7):**
  - `org.greia.sillabe-magiche` (3.7), `workshop_settings` (3.7), `volo_draghetto` (3.6), `foresta_parole` (3.6), `clinica_cuccioli` (3.0), `piccola_serra` (2.9), `memory_meraviglie` (2.6)
- **Selected Batch 1 Priority Targets (<2.5):**
  - `org.greia.treno-numeri` (1.9 → **4.8**)
  - `org.greia.labirinto-magico` (1.9 → **4.8**)
  - `org.greia.acquario-magico` (2.4 → **4.7**)

Full audit matrix: `docs/reviews/visual/2026-08-22_first-party-activity-visual-audit/VISUAL_AUDIT.md`  
Owner Contact Sheet: `docs/reviews/visual/2026-08-22_first-party-activity-visual-audit/CONTACT_SHEET.png`

---

## 2. Selected Batch 1 Activities & Before/After Score Deltas

| Activity ID | Localized Title | Collection | Initial Score | Productized Score | Delta | Key Additions |
| :--- | :--- | :--- | :---: | :---: | :---: | :--- |
| `org.greia.treno-numeri` | **Il Treno dei Numeri** | `Impara` (Math) | 1.9 / 5.0 | **4.8 / 5.0** | **+2.9** | Illustrated steam engine, Dani robot conductor mascot, rotating brass wheels, wooden fruit crates, scenic countryside valley, smoke particles |
| `org.greia.labirinto-magico` | **Labirinto Magico** | `Gioca` (Logic) | 1.9 / 5.0 | **4.8 / 5.0** | **+2.9** | Tito the Fox adventurer mascot, rotating magical vortex portal goal, 3D faceted crystal stars, beveled walls with depth shadows, tactile arrow D-pad |
| `org.greia.acquario-magico` | **Acquario Magico** | `Scopri / Crea` (Ecosystem) | 2.4 / 5.0 | **4.7 / 5.0** | **+2.3** | Illustrated tropical species (clownfish, sea turtle, baby octopus, dolphin, pufferfish), dual coral reefs, sunlight water caustics, day/night bioluminescence |

---

## 3. Per-Activity Authoring Decisions

### 3.1 Il Treno dei Numeri (`activities/treno_numeri/`)
- **Mascot Integration:** Dani the friendly robot (`character.dani`) as the conductor leaning out of the locomotive cab, cheering on correct equation solutions.
- **Runtime Assets:** Authored clean SVG masters and baked PNGs for `locomotive.png` (400×300), `wagon.png` (320×200), `wheel_large.png` (120×120), `wheel_small.png` (80×80), `conductor_dani.png` (160×160), `crate_basket.png` (240×160), and 4 fruit species (`fruit_apple.png`, `fruit_banana.png`, `fruit_carrot.png`, `fruit_strawberry.png`).
- **Grounded Scenery:** Layered green countryside hills, smiling sun with corona rays, wooden railroad ties with gravel ballast bed, and billowing steam puffs.

### 3.2 Labirinto Magico (`activities/labirinto_magico/`)
- **Mascot Integration:** Tito the Fox (`character.tito`) as the intrepid labyrinth explorer with satchel, feather cap, natural walking bobbing, and celebration hops.
- **Magical Portal Goal:** Animated rotating vortex portal (`portal_goal.png`) with golden runes and energy core on the maze destination square.
- **Runtime Assets:** Baked `tito_adventurer.png`, `portal_goal.png`, `star_crystal.png`, and `arrow_btn.png`.
- **Atmosphere:** 4 distinct themed biomes with ambient particle dust (galaxy cosmic dust, forest fireflies, crystal sparkles, volcano embers) and 3D beveled wall depth.

### 3.3 Acquario Magico (`activities/acquario_magico/`)
- **Marine Fauna:** Authored and baked illustrated tropical clownfish, sea turtle, baby octopus, sleek dolphin, and yellow pufferfish with dynamic swim physics.
- **Seabed Grounding:** Textured sandy floor with dual coral reefs (`coral_reef.png` with pink branching coral, teal tube sponges, pearl shells) and swaying kelp forests.
- **Lighting & Modes:** Tropical sunlight water caustics filtering down from the surface during the day; deep midnight abyss with glowing translucent jellyfish and neon kelp in glow mode.

---

## 4. Generic Library Gap Conclusion

**Conclusion: `NO_GAP`**
All visual needs across the three Batch 1 activities were cleanly fulfilled using:
1. Canonical characters (`character.dani`, `character.tito`);
2. Preferred generic nature ingredients (hills, clouds, sunbeams);
3. Activity-local SVG masters baked into runtime PNGs.

No multi-activity generic library deficiency was found. **Generic Batch B remains unauthorized.**

---

## 5. Verification Results

- `tests/test_activity_treno_numeri.py`: **5/5 PASS**
- `tests/test_activity_labirinto_magico.py`: **7/7 PASS**
- `tests/test_activity_acquario_magico.py`: **4/4 PASS**
- `tests/test_visual_authoring_library.py`: **6/6 PASS**
- `python3 tools/visual_authoring_library.py validate --json`: **PASS**
- `make visual-assets-check`: **PASS (19/19 activities verified)**
- `make validate`: **PASS (all platform & launcher tests passing)**
