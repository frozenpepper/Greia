# P7 — Activity Quality Program (decisions of 2026-10-15)

**Status:** ACTIVE execution record for P7 of [PLAN.md](./PLAN.md). Owner mandate (2026-10-15): *"a serious and solid collection of first-class Activities, all engaging, fun and educational"*; the primary agent may change looks, design, gameplay and interactions.
**Inputs:** four design audits in `docs/reviews/activities/2026-10-15_activity_design_audit/` (all 45 Activities played headlessly and scored /40), the asset-library audit `docs/reviews/visual/2026-10-15_asset_library_audit/REVIEW.md`, and the binding art recipe `docs/design/GREIA_SVG_AUTHORING_RULES.md` (Opus is the sole SVG authoring model).
**Not:** a release approval. `[release].status` stays `draft` until each Activity passes the PLAN §7 decision record. This file does not override the architecture-remediation or lifecycle plans.

## 1. Design principles every reworked Activity must meet

1. **Spoken goal → act → celebrate → progress → end.** Finite rounds of 1–3 minutes, progress dots, a real ending (shared completion scene). No endless toys.
2. **Every task requires a decision.** No UI that reveals the answer (printed sums, auto-focus on the right star, per-slot answer icons, lit/target counters). Hints are graduated: ~6 s idle → cast `pose_point` + pulse; first error → demonstrate; unlimited kind retry.
3. **One feedback grammar.** Correct = cast `pose_cheer` + FX + short voice; try again = `pose_think` + demonstration; completion = shared cast completion scene.
4. **Pre-reader first.** No text dependence; prompts are voice + picture; text only where it is the taught object.
5. **On-model, library art.** Canonical cast via `character.<id>` variants; shared biome/prop/FX/HUD assets; no emoji as content; no Activity-private redraws of the cast.
6. **Shared controls + input parity.** Shared Activity control kit (ADR 0037) for all buttons/toolbars/HUD/banners; keyboard + controller + pointer + touch through the platform; platform pointer always visible.
7. **Child work is sacred.** Every saved item reachable; no silent eviction; deliberate delete with preview; no blank saves.
8. **Acer floor.** Static composition cached, bounded caches, no per-frame decode/scale, app-loop tests (not only model tests).

## 2. Catalogue decisions (owner, 2026-10-15)

**Standard: one Activity = one core experience.** Levels/stages of the same loop are fine; multi-game hubs (several different games behind one card) are NOT a standard pattern — rare exceptions only (e.g. the Encyclopedia). This keeps the system logic simple and keeps Activity authoring standard for future contributors/agents. **No merges.** Real child-testing preference outranks auditor overlap analysis (Aquarium, Orca Bay and Submarine were the three favourites).

**Grouping is the Shell's job, not the Activity's.** Related Activities are grouped through the existing platform sub-collection mechanism (manifest `discovery_tags` → themed sub-collection with a clear folder tile and theme icon), e.g. a **Sea** folder (acquario_magico, baia_delle_orche, sottomarino_giramondo, viaggio_delfino), Animals/care, Numbers, Words, Music. This extends P6's discovery themes; it does not redesign navigation.

| Decision | Result |
|---|---|
| All 45 Activities stay separate cards | overlapping ones are differentiated by improving each in its own identity (shared art only) |
| `bosco_numeri` / `il_giardino_dei_numeri`, `foresta_parole` / `officina_dei_suoni`, `clinica_cuccioli` / `cucciolo_mio`, `volo_draghetto` / `viaggio_delfino`, `piccola_serra` | keep separate; sharpen each one's distinct learning loop and age band so the ladder steps differ |
| `orchestra_animali` | improve as one music experience (no Jam/Echo/Pattern/Freeze hub); rhythm-echo / freeze-dance may become separate new Activities later |
| `pasticceria_magica` | improve its own loop; "Fair Share" is a candidate separate new Activity, not a mode |
| NEW candidates (standalone, standard Activities): **Tidy-Up Time** (sorting), **Dani's Robot Path** (plan → run → debug), **Tito's Float Lab** (predict → test) | W4, after reworks |
| DEFERRED pending owner voice approval: **Leo's Sound Blender**, **Leo's Story Time** | |

## 3. Curriculum ladders (Parent age presets must match manifests)

- **Numbers:** Giardino count (2–4) → Treno count-out/make N (4–5) → Stelle sequence 1–20 (4–6) → Luci subitize (4–6) → Casa part-whole, enacted ± (5–7) → Bottega (units laid by the child) + Ponti (just-right length/weight) (5–7). Treno loses its addition stations (Casa owns part-whole).
- **Literacy:** Festa rhyme (3–5) → Alfabeto "Letter Garden" names/shapes/tracing (3–5) → Officina first sound / letter-sound (4–6), Foresta catch-the-letter (5–6) → Sillabe IT syllable train (5–6) [EN: Sound Blender, deferred] → Officina build-a-word → Writing / Posta (authoring).
- **Logic/science:** Memory, Labirinto, Biglia (cause–effect), Specchi (symmetry), Quattro (turn-taking strategy), Torre (silhouette fitting), Robot Path, Float Lab, Tidy-Up.
- **Creative:** Painting, Writing, Shape Garden, Teatrino, Voice Stories, Posta (picture + voice postcard), Morbidi (character creator → Creations PNG), Orchestra.
- **Nature/care/emotion/motor:** Encyclopedia (E4 next), Nascondino, Quattro Stagioni, Aquarium, Orca Bay, Submarine, Dolphin, Dragon, Pet, Vet Clinic, Nanna, Faccine (recognise → explain → help), Colline, Corsa.

## 4. Platform foundations (before mass rework)

| ID | Foundation | State 2026-10-15 |
|---|---|---|
| F0 | P0 custody fixes (galleries reachable, no silent eviction, deliberate delete, no blank saves) + blockers (Quattro drop, Submarine dive, Marble soft-lock, Nanna tap, Morbidi gallery/face) + missing pointers | IN PROGRESS |
| F1 | Shared Activity control kit + feedback grammar + completion scene (ADR 0037) + `pose_think` | IN PROGRESS (pilots: pasticceria, casa) |
| F2 | Shared drafts gallery for Activity-private creations (paged big cards, hold-to-delete, shelf-full card) | TODO |
| F3 | One platform voice recorder (Storie, Teatrino, Posta) | TODO |
| F4 | Runtime draws the Greia pointer whenever an Activity hides the OS cursor; virtual pointer for pointer Activities | TODO |
| F5 | Graduated hint helper (idle → point → demonstrate) in the kit | TODO (with F1 follow-up) |
| F6 | Shared spoken numbers 0–20 + direction/position words (EN/IT; ES/FR staged) | NEEDS OWNER VOICE APPROVAL (local Voice Studio, zero new spend) |

## 5. Shared art library to author once (Opus, binding recipe)

Biome scene kits (layered 1024×600): meadow day (exists, extend layers), night sky, underwater + sea surface, sky clouds, woodland seasons (pond/autumn/snow), indoor rooms (kitchen, bedroom, bathroom, vet corner, bakery, playroom, workshop), stage (curtains, boards). Props: `prop.vocab.*` (~64 nouns), `prop.food.*` (12), `prop.everyday.*` (~16), `prop.nature.*`, `prop.blocks.*`/`prop.shape.*`, `prop.instrument.*`, `prop.plant.*` growth stages, `prop.tree.seasonal_*`, `prop.code_card.*`, `prop.lab.*`, `prop.bridge.*`/`prop.picnic.*`, `prop.mosaic_tile.*`. Creatures: `creature.marine.*`, `creature.woodland.*`, `creature.pet.*` (states). Cast: `pose_think` (F1), `pose_wave`, `pose_play`, `puppet`, expressions sad/angry/silly. FX set (`fx.confetti`, sparkle, star_burst, bubble_pop, splash, …). HUD icons `icon.hud.*` (replace all HUD emoji/text buttons). UI: completion stage, dot cards, letter/number tiles, memory cards, creation cards, avatar accessories, wallpapers. Consumers and IDs per the audits' "shared assets" tables.

## 6. Execution waves

1. **W0 (running):** F0, F1, Shell browse/gallery pages redesign.
2. **W1:** F2–F5; art kits by family in parallel (biomes; props/vocab/food/everyday; creatures; cast extras + FX + HUD).
3. **W2 — ladders first:** number ladder (Giardino, Bosco, Treno, Stelle, Luci, Casa, Bottega); literacy ladder (Festa, Alfabeto, Officina, Foresta, Sillabe-IT); creative anchors (Painting, Writing, Teatrino, Shape Garden, Voice Stories, Posta); child favourites Aquarium, Orca Bay, Submarine polished early and conservatively (keep what children love).
4. **W3 — remaining reworks:** Dolphin, Dragon, Pet, Vet Clinic, Greenhouse, Orchestra, Torre, Ponti, Biglia, Quattro, Faccine, Morbidi, Mondo, Memory, Labirinto, Nanna, Colline, Corsa, Stagioni, Nascondino, Pasticceria (+Fair Share), Specchi, My Greia.
5. **W4 — new Activities:** Tidy-Up Time, Robot Path, Float Lab (+ Sound Blender / Story Time if voice approved).

Each rework is one end-to-end owner (design + art + code + tests + headless review at 1024×600/800×480/480×320), using only shared kits and the control kit; the primary agent reviews one before/after sheet per Activity and commits.

## 7. Progress log (append-only)

- **2026-10-15** — Program created from the four design audits; W0 started (custody/blocker fixes, control kit, Shell pages). Home/picker redesign committed `5e7e089e`; core icons flat SVG `54c6ff7f`; P0 Activity icons `a29178c4`; cast poses `3305c19f`.
- **2026-10-15** — Owner: no multi-game merges as a standard; one Activity = one experience; grouping via Shell sub-collection theme folders (e.g. Sea). All merges cancelled; Aquarium/Orca Bay/Submarine were the child-testing favourites.
