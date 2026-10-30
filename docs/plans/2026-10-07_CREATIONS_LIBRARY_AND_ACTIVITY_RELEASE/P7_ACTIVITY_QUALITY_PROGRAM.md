# P7 — Activity Quality Program (decisions of 2026-10-15)

**Status:** ACTIVE execution record (W0–W3 DONE at source level 2026-10-16; W4 and the follow-ups in §8 remain) for P7 of [PLAN.md](./PLAN.md). Owner mandate (2026-10-15): *"a serious and solid collection of first-class Activities, all engaging, fun and educational"*; the primary agent may change looks, design, gameplay and interactions.
**Inputs:** four design audits in `docs/reviews/activities/2026-10-15_activity_design_audit/` (archived; see git history) (all 45 Activities played headlessly and scored /40), the asset-library audit `docs/reviews/visual/2026-10-15_asset_library_audit/REVIEW.md` (archived; see git history), and the binding art recipe `docs/design/GREIA_SVG_AUTHORING_RULES.md` (Opus is the sole SVG authoring model).
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

| ID | Foundation | State 2026-10-16 |
|---|---|---|
| F0 | P0 custody fixes (galleries reachable, no silent eviction, deliberate delete, no blank saves) + blockers (Quattro drop, Submarine dive, Marble soft-lock, Nanna tap, Morbidi gallery/face) + missing pointers | **DONE** (every reworked creative Activity: paged gallery, deliberate delete with preview, full-shelf refusal without eviction, no blank saves; pointer visible everywhere) |
| F1 | Shared Activity control kit + feedback grammar + completion scene (ADR 0037) + `pose_think` | **DONE** — `src/greia_platform/activity_controls.py` (control kit), `activity_feedback.py` (`CastFeedback`), `pygame_completion.py` (shared cast completion scene), `pose_think` in the cast; used by all 45 Activities |
| F2 | Shared drafts gallery for Activity-private creations (paged big cards, hold-to-delete, shelf-full card) | **PARTIAL** — each creative Activity (Painting, Writing, Shape Garden, Teatrino, Story Cards, Posta, Morbidi) shipped its own paged gallery with confirm-delete (preview, back default) and a full-shelf sheet; the confirm dialog, save-status icon builder, burst FX, synth sound bank and sheet class are duplicated per Activity → extract into the kit (see §8) |
| F3 | One platform voice recorder (Storie, Teatrino, Posta) | **TODO** — Story Cards and Teatrino still use private mic modules |
| F4 | Runtime draws the Greia pointer whenever an Activity hides the OS cursor; virtual pointer for pointer Activities | **PARTIAL** — reworks keep the platform pointer visible (checked per Activity, e.g. Bridges no longer hides it); the runtime-level guarantee is not yet implemented |
| F5 | Graduated hint helper (idle → point → demonstrate) in the kit | **PARTIAL** — the behaviour (idle ~6 s point + pulse, first error demonstrate, unlimited retry) exists in every Activity but is implemented per Activity; `CastFeedback` has no pointing-hint pose helper (Festa draws its own) → shared helper still to extract |
| F6 | Shared spoken numbers 0–20 + direction/position words (EN/IT; ES/FR staged) | **NEEDS OWNER VOICE APPROVAL** — nothing generated; consolidated request list: [`VOICE_LINES_REQUESTED_2026-10-16.md`](../2026-10-12_GREIA_FOUR_LANGUAGE_ROLLOUT/VOICE_LINES_REQUESTED_2026-10-16.md). The shared vocabulary audio bank (`00d303a5`) exists for noun clips; `shared_number_audio_path` is named by `pasticceria_magica` but not yet implemented |

## 5. Shared art library to author once (Opus, binding recipe)

Biome scene kits (layered 1024×600): meadow day (exists, extend layers), night sky, underwater + sea surface, sky clouds, woodland seasons (pond/autumn/snow), indoor rooms (kitchen, bedroom, bathroom, vet corner, bakery, playroom, workshop), stage (curtains, boards). Props: `prop.vocab.*` (~64 nouns), `prop.food.*` (12), `prop.everyday.*` (~16), `prop.nature.*`, `prop.blocks.*`/`prop.shape.*`, `prop.instrument.*`, `prop.plant.*` growth stages, `prop.tree.seasonal_*`, `prop.code_card.*`, `prop.lab.*`, `prop.bridge.*`/`prop.picnic.*`, `prop.mosaic_tile.*`. Creatures: `creature.marine.*`, `creature.woodland.*`, `creature.pet.*` (states). Cast: `pose_think` (F1), `pose_wave`, `pose_play`, `puppet`, expressions sad/angry/silly. FX set (`fx.confetti`, sparkle, star_burst, bubble_pop, splash, …). HUD icons `icon.hud.*` (replace all HUD emoji/text buttons). UI: completion stage, dot cards, letter/number tiles, memory cards, creation cards, avatar accessories, wallpapers. Consumers and IDs per the audits' "shared assets" tables.

## 6. Execution waves

1. **W0 (DONE):** F0, F1, Shell browse/gallery pages redesign.
2. **W1 (art kits done as needed per rework; F2–F5 partial, see §4):** F2–F5; art kits by family in parallel (biomes; props/vocab/food/everyday; creatures; cast extras + FX + HUD).
3. **W2 — ladders first (DONE):** number ladder (Giardino, Bosco, Treno, Stelle, Luci, Casa, Bottega); literacy ladder (Festa, Alfabeto, Officina, Foresta, Sillabe-IT); creative anchors (Painting, Writing, Teatrino, Shape Garden, Voice Stories, Posta); child favourites Aquarium, Orca Bay, Submarine polished early and conservatively (keep what children love).
4. **W3 — remaining reworks (DONE):** Dolphin, Dragon, Pet, Vet Clinic, Greenhouse, Orchestra, Torre, Ponti, Biglia, Quattro, Faccine, Morbidi, Mondo, Memory, Labirinto, Nanna, Colline, Corsa, Stagioni, Nascondino, Pasticceria (+Fair Share), Specchi, My Greia.
5. **W4 — new Activities (NOT STARTED):** Tidy-Up Time, Robot Path, Float Lab (+ Sound Blender / Story Time if voice approved).

Each rework is one end-to-end owner (design + art + code + tests + headless review at 1024×600/800×480/480×320), using only shared kits and the control kit; the primary agent reviews one before/after sheet per Activity and commits.

## 6a. W0–W3 result (2026-10-16): all 45 Activities reworked or deliberately polished

Evidence class: **SOURCE + headless desktop review** (1024×600 / 800×480 / 480×320 frames per Activity, app-loop tests). No audible review, no VM, no physical hardware. `[release].status` is still `draft` for every Activity.

| Activity | New core experience (≤8 words) | Commit |
|---|---|---|
| il_giardino_dei_numeri | First counting rung: touch-and-count into frames | `76e75c9d` |
| bosco_numeri | Numerals 0–10: meet, find, trace, show | `a235db57` |
| treno_numeri | Count-out cargo, make-N, same-as wagon | `ce66c9bd` |
| stelle_incantate | Connect stars in number order 1–20 | `b94e59b9` |
| luci_di_momo | Subitizing: glance, pick numeral card | `5bfa34a0` |
| casa_del_dieci | Enacted part-whole within ten-frame house | `6bf707c6` |
| bottega_delle_misure | Child lays unit blocks; compare, balance | `8e10a82e` |
| costruiamo_ponti | Test plank length and weight, press GO | `190ba96a` |
| pasticceria_magica | Counting and pattern orders, then free cake | `878a47f8` |
| festa_delle_rime | Listen to a word, find the rhyme | `115179d5` |
| alfabeto_leo | Letter garden: meet, find, trace, plant | `1fb937a0` |
| officina_dei_suoni | Sound-first: first sound, then build word | `fc5d98fe` |
| foresta_parole | Catch the word's first letter in basket | `eef7facd` |
| sillabe_magiche | Syllable train: tap beats, build wagons | `83c32eb5` |
| mondo_contrari | Flash's guided opposite game, act then answer | `c398738a` |
| memory_meraviglie | Matching pairs filling sticker albums | `8e2f4460` |
| labirinto_magico | Four short hedge mazes with Tito | `5774067c` |
| la_discesa_della_biglia | Marble Run puzzle: place pieces, press GO | `83a08c61` |
| specchi_magici | Build the mirror half tile by tile | `d0d21889` |
| quattro_amici | Kind turn-taking match, best of three | `c6ba4471` |
| torre_forme | Fill a silhouette with turnable blocks | `965760e0` |
| nascondino_bosco | Hide-and-seek with position words | `d9896b4c` |
| quattro_stagioni | Dress the scene for the chosen season | `fe2f2739` |
| piccola_serra | Read what the plant needs, care, order stages | `52505f46` |
| cucciolo_mio | Read the pet's need, care through a day | `e0670fd9` |
| clinica_cuccioli | Vet clinic: find the hurt, fixed care sequence | `58a1c01a` |
| faccine_momo | Recognise, explain, help with feelings | `0b8fdacb` |
| nanna_delle_nuvolette | Calm tuck-in: match blanket colour and stars | `e5692523` |
| colline_allegre | Five finite buggy courses with Tito | `11b994ca` |
| corsa_bacche | Small kind garden mazes, collect berries | `8000d346` |
| volo_draghetto | Four finite rainbow-ring flight courses | `8333b6e8` |
| viaggio_delfino | Three finite dolphin journeys, pearls, leaps | `8a1ecfb2` |
| acquario_magico | Free-play aquarium, optional gentle missions (polish) | `9d4820e5` |
| baia_delle_orche | Free-play orca fjord with Tito facts (polish) | `2a5174b8` |
| sottomarino_giramondo | Free dive, Captain Leo's optional orders (polish) | `c096a6e0` |
| painting | Word-free painting studio, colouring pages, gallery | `2fac1996`, `552011a1` |
| writing | Calm word-free writing studio with paper colours | `ebe457d8` |
| shape_garden | Compose a garden from shapes and ghosts | `889f6cc2` |
| teatrino_fiabe | Puppet theatre: record, curtain call, poster | `d1d630cc` |
| storie_della_mia_voce | Order story cards, then tell each | `b4e2fa72` |
| posta_di_leo | Make and send picture postcards | `b98be3be` |
| morbidi_mostriciattoli | Monster character creator saved as picture | `697cde00` |
| orchestra_animali | Animal Band: free play, then echo calls | `ec9d5217` |
| workshop_settings (My Greia) | Word-free make-it-mine Home preview | `677f0cd1` |
| enciclopedia_greia | Hub kept; E4 storybook scenes for 36 entries | `7b1f6b2c` |

Related platform/shared work in the same span: shared vocabulary audio bank with locale fallback `00d303a5`; 62 vocabulary pictures in the shared library (catalogue 0.7.0) `a779b10f`; `set_alpha(None)` transparency fix `11a61e59`; stdlib `abc` allowed in the curated child runtime `ab0fabc7`; Parent-installed Activity policy `8d1588f3`; Python 3.11 f-string fixes in the Parent panel `ce2e2c95`, `7f745bca`; `set_curated_wallpaper` / `WallpaperImporter.install_curated` `677f0cd1`; fail-soft handling of unrecorded sessions. Sea theme folder (acquario, baia, sottomarino, delfino) landed earlier in `ebf6d942`.

Full unit suite at the end of the span: 5,300 tests; the only 2 failures were fixed afterwards and not re-run individually. A fresh full `make verify` on the final head is still owed (≈85 min).

## 7. Progress log (append-only)

- **2026-10-15** — Program created from the four design audits; W0 started (custody/blocker fixes, control kit, Shell pages). Home/picker redesign committed `5e7e089e`; core icons flat SVG `54c6ff7f`; P0 Activity icons `a29178c4`; cast poses `3305c19f`.
- **2026-10-15** — Owner: no multi-game merges as a standard; one Activity = one experience; grouping via Shell sub-collection theme folders (e.g. Sea). All merges cancelled; Aquarium/Orca Bay/Submarine were the child-testing favourites.
- **2026-10-16** — W0–W3 complete at source level: all 45 Activities reworked or conservatively polished, each as one end-to-end commit (table in §6a); F0 and F1 DONE, F2/F4/F5 PARTIAL, F3 TODO, F6 awaits owner voice approval. Shared vocabulary audio bank (`00d303a5`), 62 vocabulary pictures (`a779b10f`), Encyclopedia E4 (`7b1f6b2c`), `set_alpha(255)` transparency fix (`11a61e59`), `abc` allowed in the child runtime (`ab0fabc7`). Unit suite 5,300 tests with 2 failures fixed afterwards; no audible review, no hardware. Follow-ups recorded in §8.


## 8. Follow-ups (from the rework backlog, 2026-10-16)

**Control-kit / platform gaps** (extract once, then delete the per-Activity copies)
- Calm completion variant (no bunting/confetti) for wind-down Activities (Nanna).
- Completion scene accepts an icon/visual id (Pasticceria aliases `icon.hud.cupcake` → `prop.food.cupcake`).
- Completion scene supports one cast member only (Quattro tie shows Flash); allow multi-cast.
- Selection-follows-focus support in kit lists/galleries (focus/selection desync caused the wrong-delete bug fixed in `552011a1`).
- Graduated hint helper incl. a pointing pose for `CastFeedback` (F5).
- Shared confirm-delete dialog, save-status icon builder, burst FX, synth sound bank and sheet class currently duplicated across Painting, Writing, Teatrino, Story Cards (F2).
- Kit listen button is small at 480×320; Memory completion labels shrink with two buttons.
- F3 platform voice recorder; F4 runtime-level pointer guarantee.
- Acquario and Quattro Amici load Tito shared clips by a relative `../..` path → switch to `shared_character_audio_path` (installed-image safety).
- `headless_greia_activity` should also sandbox the customization dir.

**Shared-library promotion / migration pass** (after reworks)
- Switch Activity-private copies to shared IDs and retire duplicates: promoted vocab (12), train set (`prop.train.*`, copied by Treno and Sillabe), lanterns, crate / ten-frame, jars, constellation figures, sea props, balance, `prop.vocab.fan` (Festa + Officina), Foresta can use library zebra/tiger/giraffe/island/ship/volcano to unlock recorded words.
- Other Activity-private candidates awaiting promotion: Serra plant stages (51 SVGs), Specchi mosaic tiles (36), Alfabeto pictures (15), Stelle constellation figures (12), Morbidi 69-part Puff kit, Teatrino fairy-tale puppets, Biglia/Ponti planks and board art (art pass: `prop.marble_run.*`, `prop.bridge.*`, picnic blanket, river-valley scene), Volo dragon and sky rings, Colline buggy/finish arch/flags, Orchestra xylophone, Cucciolo/Clinica pet props, Quattro token discs. Wished: more `prop.vocab.*` (word lists limited: IT 11, ES 8, FR 6, EN 10).
- Cast: left-facing `pose_point` variants (Quattro mirrors Leo → glasses highlight flips); woodland creatures lack hurt/happy states; `bg.sky_clouds` mid/fg layers do not tile.

**Disk / performance**
- Disk pass: Activity runtime PNGs are growing (Serra ≈ 930 KB). Evaluate lossless palette/quantized PNG optimisation across `activities/*/assets/runtime` and `assets/visual/runtime` (Pillow quantize, verify visually) against the ≤800 MiB core budget.
- Teatrino scene picker builds 6 full scenes on first open (pre-render thumbnails); Teatrino delete badges are 32 px at 480×320 (< 40 touch floor).

**Parent / profile**
- Parent App: wallpaper import (USB) has no child-flow surface any more; add a Parent-side import. `workshop_settings` manifest still requests `removable_media.read` (a permissions test uses it).
- Avatars for Flash and Tito (core-icon faces + profile defaults + launcher mapping); child painting as wallpaper via Creations.

**Language / voice**
- ES/FR clip issues: Luci ES/FR `prompt_choose` clips say the wrong instruction (re-record before promotion); Colline ES/FR bundles have empty audio maps despite title WAVs (verify resolver projection); Specchi ES/FR Lilli lines are in Leo's voice; Casa ES `prompt_add` is weak; Foresta EN/IT files missing receipts (EN j/k/x/y + find, IT h); Sillabe EN "bee" uses the "be" syllable clip (owner check); Bosco intro clip says "count to ten"; Delfino old welcome clip mentions mouse/space.
- `tools/generate_*_audio.py` scripts for Casa, Luci, Bosco still list old lines.
- Alfabeto teaches capitals only; ES/FR letters lack art.
- Docs still describing pre-rework Activities (Writing toolbar in `PHASE0_CORE_CREATION_ACTIVITIES.md`) — see HANDOVER entry of 2026-10-16.
- All requested voice lines are consolidated in [`VOICE_LINES_REQUESTED_2026-10-16.md`](../2026-10-12_GREIA_FOUR_LANGUAGE_ROLLOUT/VOICE_LINES_REQUESTED_2026-10-16.md).

**Design principles learned** — conservative polish must keep known controls (keyboard arrows) and signature colours (reviewers compare BEFORE vs AFTER); the on-screen guide character must match the recorded voice's character; one Activity = one experience.

**W4 (not started):** Tidy-Up Time, Dani's Robot Path, Tito's Float Lab; Sound Blender / Story Time await owner voice approval; "Fair Share" and rhythm-echo / freeze-dance candidates.

