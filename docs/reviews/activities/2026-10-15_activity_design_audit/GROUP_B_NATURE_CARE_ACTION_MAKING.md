# Activity Design Audit — Group B: Nature, Care, Action, Making

**Status:** design review / recommendation for main-agent and owner decision. No source, asset, manifest or test was changed.
**Auditor:** Opus design auditor "design-b" (senior game designer + early-childhood learning designer, ages 3–6, pre-readers), 2026-10-15.
**Evidence label:** SOURCE + DESKTOP VISUAL REVIEW. Every Activity was played headlessly through the real Simulator bridge (`greia_simulator.python_activity`, Pygame dummy video, `--locale en`) with a scripted multi-step driver (clicks, drags, holds, keys), 4–11 captures per Activity at 1024×600 plus one at 800×480. Checkout: `main` at `0d903962`→`3b48dbfe` with other agents' uncommitted Activity edits in the working tree. No simulator-Shell, VM, Acer or physical-device evidence. Audio was not heard (dummy driver); speech coverage was established from shipped files.
**Scope:** `acquario_magico`, `baia_delle_orche`, `enciclopedia_greia`, `nascondino_bosco`, `quattro_stagioni`, `clinica_cuccioli`, `cucciolo_mio`, `morbidi_mostriciattoli`, `nanna_delle_nuvolette`, `colline_allegre`, `corsa_bacche`, `volo_draghetto`, `torre_forme`, `pasticceria_magica`.
**Constraints assumed:** Acer floor 1024×600 / 768 MiB, Pygame, build-time SVG→PNG only, prerecorded speech only (voice lines below are *requests*, not approvals), offline, platform-owned Home (top-left), shared Activity control kit coming (buttons/pills/toolbar/HUD chips/progress dots/prompt banner) and assumed adopted everywhere below. Encyclopedia E1–E3 art is accepted and not re-opened; E4 entry migration is its next phase.

Scores are 1–5 for: **L** learning objective clarity & correctness · **A** age fit / pre-reader independence · **F** core-loop fun · **J** feedback & juice · **P** progression & replay · **V** visual quality & on-model consistency · **U** usability (targets, input profiles, Home safety) · **T** technical health.

## Summary (best → worst)

| Activity | Portfolio family | Score /40 | Verdict | Effort |
|---|---|---:|---|---|
| `enciclopedia_greia` | Nature & observation | 25 | POLISH (continue E4, add E5 "find & collect" loop) | L (E4) + M |
| `colline_allegre` | Motor/action | 25 | POLISH (add real course/finish/levels) | M |
| `nascondino_bosco` | Nature & observation | 25 | POLISH (scenes, spatial words, progression) | M |
| `pasticceria_magica` | Making / early math | 23 | REWORK (spoken orders, count-along, levels, PNG creation) | M |
| `acquario_magico` | Nature & observation | 23 | REWORK → becomes the single **Ocean** Activity (absorbs Baia) | M |
| `corsa_bacche` | Motor/action | 23 | REWORK (tiny mazes, big sprites, tap-to-go, on-model Momo) | M |
| `baia_delle_orche` | Nature (marine) | 23 | CUT-or-MERGE → second scene of the Ocean Activity | S (as merge) |
| `torre_forme` | Logic/spatial | 22 | RETHINK (silhouette tower puzzle, no Tetris line clears) | M–L |
| `morbidi_mostriciattoli` | Creative making | 22 | REWORK (real part previews, PNG to Creations, fix bugs) | M |
| `quattro_stagioni` | Nature & observation | 21 | REWORK (coherent seasons + "what belongs?" missions) | M |
| `clinica_cuccioli` | Care & emotions | 21 | CUT-or-MERGE → vet corner of one **Pet House** Activity | M (as merge) |
| `nanna_delle_nuvolette` | Care / calm | 20 | REWORK (colour + star-count wishes, fix tap-tap) | S |
| `volo_draghetto` | Motor/action | 20 | CUT-or-MERGE → dragon world/skin inside `viaggio_delfino` | S |
| `cucciolo_mio` | Care & emotions | 16 | CUT-or-MERGE → base of one **Pet House** Activity (rebuilt) | L (as merge) |

---

## 1. `enciclopedia_greia` — Greia Encyclopedia — 25/40 — POLISH

**Played:** Discovery Home (open book, 6 domain portals, Leo), Animals section (habitat world), Lion entry (5 discovery symbols, mane activation, legs activation), Frog entry (process archetype, pre-E4), Home at 800×480.

| L | A | F | J | P | V | U | T |
|---|---|---|---|---|---|---|---|
| 4 — 43 real factual entries, 199 narrated clips per language; correct content | 3 — book→section→entry is learnable, but entry symbols are abstract (circle-in-circle, three dots, oval) and captions carry meaning | 3 — touch-and-listen only; no question, no goal | 3 — activation rings/particles exist but persist and stack (mane ring stays after legs is chosen) | 2 — `events = []`; nothing is collected, remembered or revisited | 3 — E3 sections strong; pre-E4 entries are bare (frog page: empty pond, abstract dots) | 4 — navigation profile, controller via `input_core`, big chevrons; Leo overlaps the Pyramids portal | 3 — ~1977 primitive draw calls in `pages/*.py`; frog caption overflows its banner at 1024×600 |

**Redesign spec**
- Target: a picture-book a 4-year-old can *finish*: each entry is a small diorama where touching the real body part/process step (not an abstract chip) plays narration, and a "Can you find…?" question closes the page with a sticker.
- E4 (already planned): replace abstract discovery chips with **hit-areas on the hero illustration** (mane, paw, mouth for roar…); chips remain only as a controller focus ring path (D-pad cycles hotspots in reading order).
- Add an E5 loop per entry: after ≥3 discoveries Leo asks one spoken question ("Which part helps the lion roar?"); child taps the part; correct → sticker flies into a **sticker book** (one per section, 7–11 slots). Wrong → gentle glow on the right part after 2 tries.
- Sticker book page reachable from the Discovery Home (bookmark ribbon); it is the progression and replay driver; emit `encyclopedia.sticker_earned` (milestone) and `encyclopedia.section_completed` (completion).
- One guide: **Leo** (owl = knowledge) everywhere; use `character.leo` `pose_point` while a question is open and `pose_cheer` on sticker. Remove Tito-as-presenter on entry pages (or make Tito the Animals-section guide only, consistently). Move Leo off the Pyramids portal (anchor him on the desk at x≈930, below the right page edge).
- Clear previous activation FX when a new hotspot is activated; captions max one line at 1024×600, auto-shrink then wrap — never clip.
- Progression: sections unlock nothing (no gating for pre-readers); completion = all stickers in a section → section card gets a gold frame on Home.
- New art: `prop.encyclopedia.sticker_frame` (sticker slot, empty/filled), `ui.encyclopedia.sticker_book_page` (open-book page with 12 slots), `icon.hud.bookmark` (ribbon to sticker book), plus E4 per-entry hero dioramas already scheduled (no new list here).
- Voice lines (EN): one question per entry (43, e.g. "Which part helps the lion roar?", "Where does the tadpole grow its legs?"), plus "You found it!", "Look here!", "Your sticker book is full!".
- Effort: E4 L (already planned); E5 loop M. Risks: draw-call budget on Acer if dioramas stay primitive — E4 must move entry art to build-time PNG; 43 new questions need owner voice approval.

## 2. `colline_allegre` — Bumpy Hills — 25/40 — POLISH

**Played:** start, hold GO 3/7/15/30/50 s (airtime, landing, comical flip auto-recover), 800×480.

| L | A | F | J | P | V | U | T |
|---|---|---|---|---|---|---|---|
| 2 — "physics.momentum" claimed, but holding GO always wins | 3 — two huge buttons; distance in metres means nothing to a 3-year-old | 4 — suspension, airtime and flips are genuinely funny | 4 — confetti, PERFECT LANDING, boing | 1 — hard-coded `CollineWorld(difficulty=2)`; no finish line; collectibles run out (22 stars by 712 m, then empty terrain forever); manifest `adaptive_difficulty = true` is not true | 3 — clean flat terrain, but driver is an unidentified orange creature | 4 — keyboard, pointer, controller axis/buttons; protected Home region respected | 4 — light, stable |

**Redesign spec**
- Target: short, finishable **courses** (45–90 s) that end at a picnic flag with a friend waiting, where *slowing down at the right moment* matters on later courses.
- Course model: finite course of N "hill tiles" ending in a finish arch; HUD replaces metres with a **progress road** (start flag → car icon → finish flag) from the control kit's progress track.
- Levels (child-visible as 5 picnic baskets on a map): 1 gentle rolling, auto-upright; 2 bigger hills + 1 bridge; 3 mud patch (must not brake in mud — visual brown splat cue); 4 steep drop where GO-only flips (brake before the cliff sign); 5 mushrooms to bounce. Unlock next on finish; never lock replays.
- Adaptive rule: 3 flips on one course → next attempt of that course auto-uprights and lowers amplitude 20 %; 2 clean finishes → offer next basket with Leo `pose_point`.
- Stars: each course has exactly 5 big stars (counted with progress dots, not a number); finish screen shows 0–5 star dots and Tito `pose_cheer` at the picnic. The driver becomes canonical **Tito** (`character.tito` head composited over the seat), replacing the primitive orange creature.
- Inputs: keep Space/→/south button = GO, ←/east = brake; pedals adopt control-kit round buttons with icons (▶▶ / ■) and no text dependence.
- New art: `prop.vehicle.buggy` (side view, wheels separate: `prop.vehicle.buggy_wheel`), `prop.course.finish_arch`, `prop.course.sign_cliff`, `prop.course.mud_patch`, `prop.course.mushroom_bounce`, `bg.meadow_day.*` layers (shared), `fx.dust_puff`, `fx.confetti`.
- Voice lines: "Ready, steady, go!", "Slow down!", "You made it to the picnic!".
- Effort M. Risks: course length/physics tuning must be play-tested with 3-year-olds; keep sub-step physics within Acer CPU budget.

## 3. `nascondino_bosco` — Woodland Hide & Seek — 25/40 — POLISH

**Played:** fresh round (target portrait), wrong spot (wrong animal leaps out), right spot, several rounds, 800×480.

| L | A | F | J | P | V | U | T |
|---|---|---|---|---|---|---|---|
| 3 — visual search + animal names; target portrait works without reading | 4 — portrait cue is pre-reader-safe; target name is text only (not spoken) | 3 — fine for 2–3 rounds | 3 — leap-out reveal; wrong animal is kind | 1 — 5 fixed spots in one scene; animals peek visibly (bunny fully visible above the log); lifetime star counter shows "1116" | 4 — shared meadow, canonical Lilli (decorative only) | 3 — keyboard ring; no controller; ring starts on a spot (fine) | 4 |

**Redesign spec**
- Target: hide-and-seek that teaches **position words** (in, under, behind, on top of, next to) and grows from "spot the peeking ears" to "listen and look".
- Each round Lilli (`pose_point`) asks with a spoken line: "Who is hiding *behind the rock*?" (level 3+) or shows the portrait (levels 1–2). The child taps the spot; the answer is the spot, not the animal, at higher levels.
- Scenes: meadow (existing), pond, autumn wood, snowy wood (shared biome kits), 6–8 spots each, chosen randomly so memorisation fails.
- Levels: 1 = 3 spots, ears clearly peeking; 2 = 5 spots, small peek; 3 = position words spoken, no peek; 4 = two animals per request ("Find the frog *and* the owl"); 5 = sound clue (animal call) + position word.
- Adaptive: 2 misses → the correct spot wiggles; 3 consecutive first-try finds → advance.
- Replace the lifetime star number with a per-round **friend line-up** (found animals sit on a log; 4/4 = round done) and a collectible "woodland friends" page.
- New art: `bg.pond_day.*`, `bg.autumn_wood.*`, `bg.snow_wood.*` (shared biome kits), `prop.nature.{hollow_log,mushroom_ring,reed_clump,snowy_bush,leaf_pile}`, `creature.woodland.{fox,bunny,owl,hedgehog,squirrel,frog}` in `peek` and `full` variants (flat SVG; the fox must read as a woodland fox, not as Tito).
- Voice lines: 6 animal names, 5 position phrases ("behind the rock", "under the bush", "in the tree", "next to the log", "on the rock"), "Who is hiding…", "Found you!", 6 animal calls (SFX, not voice).
- Effort M. Risks: position-word recordings in IT/EN must match scenes exactly; keep spot hit-boxes ≥ 96 px.

## 4. `pasticceria_magica` — Magic Bakery — 23/40 — REWORK

**Played:** partial order + Serve (error), correct order (fanfare), Patterns tab, Free tab, 800×480.

| L | A | F | J | P | V | U | T |
|---|---|---|---|---|---|---|---|
| 4 — exact counting with numeral + pictured quantity; AB patterns are real | 3 — order not spoken; error is a text banner | 3 | 2 — "CHECK THE RECIPE AND TRY AGAIN" text overlaps the Clear button; no per-item feedback | 2 — random 1–4 + 1–3 counts, 5 fixed patterns cycling, no levels | 2 — emoji toppings on a flat ring plate; generic bakery | 3 — pointer-only (no keyboard/controller); large targets | 4 |

**Redesign spec**
- Target: a counting bakery where cast friends order cakes, every placed topping is **counted aloud**, and the order card ticks off item by item, so the child self-checks before serving.
- Customer queue: Dani/Momo/Flash walk in (`pose_point` at the order card), order is spoken ("Three strawberries and two blueberries, please!").
- Place topping → number word spoken ("one… two… three!") and the order row fills a dot per item; over-count makes the extra topping wobble (tap to remove). Serve only lights up when every row matches — no failing serve.
- Levels: 1 one topping ≤3; 2 one topping ≤5; 3 two toppings ≤5 total; 4 two toppings ≤10; 5 "one more than" orders ("Two cherries… and one more!"); patterns track: AB → AAB → ABB → ABC → grow-the-pattern (child places the next two).
- Adaptive: 2 corrections on a level → stay; 3 clean orders → next level.
- Free mode = Create: decorated cake is saved and published as a flattened PNG through the Creations SDK (P7 condition) so it appears in My Creations and Teatrino.
- Celebrate: customer `pose_cheer`, cake slides into a takeaway box, heart pop.
- New art: `bg.indoor_room.bakery` (wall + counter variant), `prop.bakery.{cake_round,cake_box,order_card,display_shelf}`, `prop.food.{strawberry,blueberry,cherry,chocolate,cookie,star_sugar}` (shared food set, replaces emoji), `fx.heart_pop`.
- Voice lines: number words 1–10 (reuse platform/numbers clips if they exist), 6 topping names, order template parts ("…please!", "and"), "One more!", "Ready to serve!", "Yummy, thank you!".
- Effort M. Risks: composing spoken orders from fragments needs careful IT gender/plural agreement — prefer whole prerecorded orders for levels 1–3.

## 5. `acquario_magico` — Magic Aquarium — 23/40 — REWORK (becomes the single Ocean Activity)

**Played:** start, Feed, tap puffer/octopus, Night, Bubbles, chest, 800×480.

| L | A | F | J | P | V | U | T |
|---|---|---|---|---|---|---|---|
| 1 — `lexicon.nature.marine` claimed but creature names are never spoken or shown; no facts | 4 — tap anything, nothing breaks | 3 — pleasant toy for a minute | 3 — puff, ink, spin, hearts | 1 — none; "9 / 20" creature counter is meaningless | 4 — the best flat creature set in this group (SVG sources exist) | 3 — keyboard cursor; no controller; tapping water silently spawns creatures in Creatures mode | 4 |

**Redesign spec**
- Target: one ocean Activity with a **reef aquarium** scene (this one) and the **orca bay** surface scene (from Baia), driven by short spoken *observation missions* that teach names, diets and night/day behaviour.
- Mission loop (Tito `pose_point` in a porthole): "Who has eight arms?", "Feed the turtle what it likes", "Which friend glows at night?" → child taps/feeds; success = creature joins the "reef family" strip; 3 missions = a pearl.
- Tap any creature → its name is spoken and a one-line fact plays on second tap ("The octopus has eight arms").
- Feeding becomes a choice: food tray with 3 foods (pellets, leaf, shrimp); each species likes one; wrong food is politely ignored (bubble "no thanks"), right food → happy dance. This replaces Baia's hidden craving mechanic with a visible one.
- Day/Night toggle shows *true* behaviour changes: jellyfish glow, octopus comes out, fish sleep near coral.
- Remove the counter; remove tap-to-spawn (spawning is a reward from missions — new creature arrives).
- Progression: mission tiers 1 (names), 2 (diets), 3 (day/night), 4 (counting: "How many clownfish?"); scene unlock: orca bay after 3 pearls.
- New art: `creature.marine.{clownfish,turtle,octopus,dolphin,puffer,seahorse,jellyfish,starfish}` (move existing SVGs to the shared set), `creature.marine.orca_{baby,adult,elder}` (author SVG sources for the 12 sourceless Baia PNGs), `prop.sea.{coral,kelp,shell,pearl,food_pellet,food_leaf,food_shrimp}`, `bg.underwater.*`, `bg.sea_surface.*`, `fx.bubble`.
- Voice lines: 8 creature names + 8 one-line facts, ~12 mission prompts, "No thanks!", "Yum!", reuse Baia's 6 orca facts.
- Effort M. Risks: merging two packages' saves (keep Baia's discovered facts on migration); Explore collection keeps one card instead of two.

## 6. `corsa_bacche` — Berry Chase — 23/40 — REWORK

**Played:** arrow-key steering, tap-direction steering, level 1 start, 800×480.

| L | A | F | J | P | V | U | T |
|---|---|---|---|---|---|---|---|
| 2 — maze navigation; "inhibition" claim weak | 2 — level 1 has **93 berries**; sprites ≈30 px; tap means "go in that direction", not "go there" | 3 | 3 — hearts refill, apple munch, no game over (good) | 3 — 5 authored levels with gentle critter ramp | 2 — "Momo" is an orange squirrel (canonical Momo is a purple monster); flat hedge grid | 4 — arrows, D-pad/stick, swipe/drag | 4 |

**Redesign spec**
- Target: a 60-second berry hunt in a **small** garden maze where a 3-year-old can see every berry and reach them by tapping where to go.
- Maze sizes: L1 5×5 cells / 8 berries, L2 7×5 / 12, L3 7×7 / 16 + 1 sleepy hedgehog, L4 9×7 / 20 + 2 critters, L5 9×7 / 24 + rainbow berry. Cells ≥ 72 px at 1024×600.
- Tap/click a path cell → Momo walks the shortest path there (BFS on the grid); directional input keeps the current per-cell steering. Controller unchanged.
- Player = canonical **Momo** (`character.momo` head sprite + simple walk bob) or rename and redesign as a non-cast squirrel — never call a squirrel Momo.
- Critters are visibly sleepy/awake (eyes closed = safe), giving the "inhibition" skill a real cue: wait while awake.
- HUD: berry basket filling (progress dots per 4 berries) instead of "7/93"; level as garden-gate pictures, not "L1".
- Celebrate: Momo `pose_cheer`, berries become a pie (link to Pasticceria theme).
- New art: `prop.garden.{hedge_tile,hedge_corner,gate,berry_bush}`, `prop.food.{blueberry,strawberry,raspberry}` (shared food set), `creature.woodland.{hedgehog,beetle}` with awake/asleep variants, `fx.sparkle`.
- Voice lines: "Find all the berries!", "Shh… the hedgehog is awake. Wait!", "Basket full!".
- Effort M. Risks: path-to-tap must not let pointer users bypass critters unfairly — path stops if a critter blocks.

## 7. `baia_delle_orche` — Orca Bay — 23/40 — CUT-or-MERGE (into the Ocean Activity)

**Played:** Feed, Tito fact, Song (bells), Play (pod breach), Night, 800×480.

| L | A | F | J | P | V | U | T |
|---|---|---|---|---|---|---|---|
| 2 — 6 spoken Tito facts; orcas show craved food in thought bubbles but the child cannot choose food (Feed cycles types automatically) | 3 — six tool modes; fact banner text 12–14 px | 3 | 4 — breaches, songs, hearts, sleeping orcas | 1 — none | 4 — attractive orcas; canonical Tito avatar | 3 — mode confusion (tapping water does different things per tool); DO/MI/SOL bells overlap the ring and orcas | 3 — 12 orca PNGs have no SVG source |

**Redesign spec (as merge)**
- Target: Orca Bay becomes the **surface scene** of the Ocean Activity (§5), reached by the submarine/boat portal after 3 pearls.
- Keep: three orcas with personalities, breach on tap, sleeping at night, the 6 Tito facts.
- Change: visible food choice tray (shared with the reef); orca craving bubble + food tray = matching task; remove the 6-tool toolbar (actions come from tapping the orca and the tray); Song becomes a 3-note echo game (orca sings 2–3 notes, child repeats on 3 large bells placed on a floating platform — no overlap with the ring).
- Facts unlock in the shared reef "family" book.
- New art: SVG sources for `creature.marine.orca_{baby,adult,elder}` (day/night/happy variants), `prop.sea.{bell_buoy,ring_hoop,beach_ball}`.
- Voice lines: none new (reuse 6 facts); "Your turn!" for echo.
- Effort S as a merge once §5 exists. Risks: losing the standalone package ID — migrate `discovered_facts`.

## 8. `torre_forme` — Shape Tower — 22/40 — RETHINK

**Played:** Free mode placement (blueprint sockets), Gentle mode falling piece with arrows, Tower mode, 800×480.

| L | A | F | J | P | V | U | T |
|---|---|---|---|---|---|---|---|
| 2 — "geometry" claimed but pieces are polyominoes; Tetris line clears *remove* the tower the child is told to build ("HEIGHT 0/10") | 2 — falling blocks are beyond most 3-year-olds; modes are text tabs "1. FREE / 2. GENTLE / 3. TOWER" | 3 | 3 — snap, bunting, celebration on top-out | 2 — top-out = celebrate, no difficulty logic | 3 — clean board, but builder is an off-model cat labelled "LILLI" | 3 — arrows/controller present; Gentle mode has no Rotate button; free grid persists across mode switch | 4 |

**Redesign spec**
- Target: a **silhouette tower puzzle**: each floor is an outline the child fills with real geometric shapes (square, rectangle, triangle, half-circle, arch), building upward floor by floor to a rooftop flag — spatial composition without time pressure.
- Remove line clears and auto-fall from the default mode. Drag (or select + tap) a shape from the tray; it snaps when it fits the outline with forgiving tolerance; rotate by tapping the piece (90°) or controller west button.
- Floors: L1 2 pieces, no rotation; L2 3 pieces incl. one rotation; L3 4 pieces + one decoy in tray; L4 mirrored outline; L5 two-floor plan. Each finished floor stacks; 5 floors = tower with flag and Lilli's balloon.
- Keep the current falling mode only as an optional "Gentle drop" for age 5+ (Parent/age-filtered), with a visible Rotate button and no line clears (blocks just stack).
- Builder = canonical **Lilli** (`pose_point` at the next outline, `pose_cheer` per floor); hard hat is a separate prop layer drawn above, not fused.
- Mode chooser = three picture cards (tower outline / falling block), no numbers or words.
- New art: `prop.blocks.{square,rectangle,triangle,half_circle,arch,cylinder}` (wooden toy look, 4 colours each by tint), `prop.blocks.outline_slot` (dashed silhouette style), `prop.construction.{hard_hat,flag_roof,crane_small}`, `bg.indoor_room.playroom`.
- Voice lines: shape names (5), "Turn it!", "It fits!", "One more floor!", "What a tall tower!".
- Effort M–L. Risks: touch drag on Acer touchpads — must also support select-then-tap placement.

## 9. `morbidi_mostriciattoli` — Fluffy Monsters — 22/40 — REWORK

**Played:** shape tab, colour tab, Surprise, Name (preset cycle "BUBU"), Save, My Monsters gallery, 800×480 (Escape exits the Activity).

| L | A | F | J | P | V | U | T |
|---|---|---|---|---|---|---|---|
| 2 — open-ended choice-making; no stated objective | 3 — tabs are emoji; action buttons rely on words ("SURPRISE", "UNDO", "NAME", "SAVE") | 4 — creature makers are intrinsically fun | 3 — sparkles, no voice reaction | 2 — private gallery only; gallery shows 12 of 24 saved (backlog bug: 13–24 unreachable) | 2 — a large white highlight blob covers the face on every body shape; shape options shown as pear/beans/egg emoji; primitive parts | 3 — pointer-only; no keyboard/controller; Name only cycles presets | 3 |

**Redesign spec**
- Target: a "make your own friend" studio whose result is a **real creation**: saved, shown in My Creations, and usable as a puppet in Teatrino.
- Option tiles show *rendered previews of the actual part* on a mini body (not emoji). Six part tabs as picture icons; every pick plays a squish/boing and the monster reacts (blink, giggle).
- Remove the white highlight blob (or reduce to the canonical ≤8 % upper-left highlight). Body shapes: round, tall, star, square-ish, pear, blob — named by silhouette.
- Name: platform text entry only where the profile has keyboard; otherwise a spoken-name picker of 8 silly names with audio.
- Save = flattened PNG via the Creations SDK + private editable recipe; gallery paginates all 24 (fix 12/24 bug) using control-kit pager dots.
- Optional bridge (later): "Bring to the Pet House" — the monster can be a pet there.
- Celebrate on save: Momo `pose_cheer` beside the frame ("A new friend!").
- New art: `prop.monster.{body_round,body_tall,body_star,body_square,body_pear,body_blob}`, `prop.monster.eyes_{1,2,3,sleepy,star}`, `prop.monster.mouth_{smile,fang,tongue,o}`, `prop.monster.tuft_{horn,antennae,fluff,leaf}`, `prop.monster.accessory_{bow,bowtie,glasses,scarf}`. Author each part once as flat SVG; body colour comes from palette tokens (build-time variants or a cached runtime palette swap, never per-frame).
- Voice lines: 8 silly names, "A new friend!", "Surprise!".
- Effort M. Risks: tinting at build time multiplies PNG count — budget ≤ 2 MiB total; prefer runtime palette swap on cached surfaces.

## 10. `quattro_stagioni` — The Big Seasons Tree — 21/40 — REWORK

**Played:** Spring start, Winter + Snow + snowman taps, Autumn + Wind, Night, Summer + apple tap, 800×480.

| L | A | F | J | P | V | U | T |
|---|---|---|---|---|---|---|---|
| 2 — season and weather are independent toggles, producing wrong facts (autumn leaves blowing in summer, smiling sun while snowing, snow persisting into autumn) | 4 — spoken season/weather words exist | 3 | 3 | 1 — "all seasons discovered" after four taps | 2 — primitive tree/hills; off-model fox labelled as Tito | 2 — `pointer` only; weather icons cryptic (wind = squiggle); toolbar overlaps a cloud | 4 |

**Redesign spec**
- Target: the child *causes* coherent seasonal change and then answers "what belongs in this season?" — clothing, animals, fruit, weather.
- Season wheel (4 big picture buttons) drives a coherent scene: weather becomes a property of the season with 2 plausible options each (spring: sun/rain; summer: sun/storm; autumn: wind/rain; winter: snow/sun). No snow in summer.
- Mission loop with canonical **Tito** (`pose_point`): "It's winter! Dress Tito" → drag scarf/hat/boots (not sunglasses); "Which fruit grows in summer?" → apples on the tree; "Who sleeps in winter?" → hedgehog to the leaf pile.
- Day/night stays as the sun/moon tap; at night show nocturnal animals (owl) as a separate mini-discovery.
- Progression: 4 seasons × 3 missions; completed season → a leaf/flower/apple/snowflake badge on the wheel; replay shuffles missions.
- New art: `prop.tree.seasonal_{spring,summer,autumn,winter}` (one tree, 4 canopy variants — shareable with `piccola_serra`), `prop.clothing.{scarf,beanie,boots,sunhat,raincoat,sunglasses}` (sized to Tito's canonical body; drawn as separate layers), `prop.nature.{leaf_pile,puddle,snowman,flower_patch,apple}`, `fx.{rain,snow,leaf_drift}`, `bg.meadow_day.*` season tints.
- Voice lines: 12 mission prompts, 6 clothing names, "That's right for winter!", "Hmm, too hot for that!".
- Effort M. Risks: clothing on canonical Tito must not fuse into the body (rules §8.3) — use separate prop layers at fixed anchor points.

## 11. `clinica_cuccioli` — Little Vet Clinic — 21/40 — CUT-or-MERGE (into one Pet House)

**Played:** wrong tool on patient (no visible response), right tool, brute-forced 5 patients to "PETS ALL BETTER!", 800×480.

| L | A | F | J | P | V | U | T |
|---|---|---|---|---|---|---|---|
| 2 — required steps are a random sample in random order (no care sequence); the answer is shown twice (thought bubble **and** green tool outline) | 4 — select tool → tap patient is pre-reader-friendly | 3 | 2 — wrong tool gives nothing visible; ending is a plain card on navy | 1 — random 2–4 steps; no difficulty | 2 — primitive patients; scratch drawn as a red "X" plaster | 3 — keyboard focus; no controller | 4 |

**Redesign spec (as merge)** — see the Pet House spec in §13; the vet corner keeps: patient arrives with **visible symptoms** (mud, scratch, droopy tummy, cough cloud), child *diagnoses by looking* (stethoscope reveals heartbeat/cough), then treats in a meaningful order (clean → bandage → treat → cuddle). Remove the green "correct tool" outline (hint only after 2 wrong tries); wrong tool → patient shakes head gently. Effort M as part of §13.

## 12. `nanna_delle_nuvolette` — Cloud Bedtime — 20/40 — REWORK

**Played:** tap cloud without items (hint), tap blanket then tap cloud (**does not work**), drag blanket/star to clouds, tuck all three, end state, 800×480.

| L | A | F | J | P | V | U | T |
|---|---|---|---|---|---|---|---|
| 1 — manifest claims colour matching and small sets, but clouds are all white (named "Pink/Blue/Purple Cloud" only in text) and each needs exactly one star | 3 — calm and wordless, but drag is mandatory | 2 — identical 30-second night every time | 3 — yawn and sleep animation; completion is just a small moon button | 1 — none; saved blanket preferences are not restored (P7 note) | 4 — soft clouds, canonical sleepy Momo | 2 — **tap-to-pick then tap-to-place is broken**: MOUSEBUTTONUP on the blanket immediately cancels the held item, so only press-drag works; pointer-only profile | 4 |

**Redesign spec**
- Target: a 2-minute wind-down where each sleepy cloud *wishes* for a blanket colour and a number of stars, giving genuine colour matching and counting to 5 in a calm frame.
- Each cloud is tinted (pink/blue/purple/yellow…) and shows a dream bubble: blanket swatch + 1–5 star dots. Child matches the colour, then gives stars one by one (each star counted aloud softly). Ready cloud yawns; tap to sleep.
- Fix input: support tap-pick/tap-place (only cancel on release when the press actually started a drag > 12 px) and keyboard/controller via focus ring over clouds/blankets/basket.
- Levels (nights): 1 one cloud, colour only; 2 two clouds, colour + 1–2 stars; 3 three clouds, 1–3 stars; 4 three clouds, 1–5 stars; 5 a "same as" wish (two clouds want the same colour).
- End of night: sky dims, Momo `sleepy` → lullaby chime, shooting star; then a big moon card offers "another night".
- New art: `bg.night_sky.*` (shared), `prop.bedtime.{blanket_quilt,pillow,star_token,dream_bubble}`, `fx.shooting_star`, cloud body tint variants via palette tokens.
- Voice lines (whispered): number words 1–5 (soft), "Goodnight, little cloud", "Shh, sleepy time".
- Effort S. Risks: keep it calm — no timers, no failure sounds.

## 13. Care cluster merge: `cucciolo_mio` — My Cute Pet — 16/40 — CUT-or-MERGE (rebuild as **Pet House**)

**Played:** Treats (any tap feeds, regardless of which food), Bath (taps fill bubbles), Dress (cycles accessory on every tap incl. the tab tap), Play (ball drag), Sleep, 800×480.

| L | A | F | J | P | V | U | T |
|---|---|---|---|---|---|---|---|
| 1 — no needs model: meters never fall, any tap in the content area feeds, food tray is decorative | 3 — emoji help, but all feedback is text ("YUM YUM! DELICIOUS!") | 2 | 3 — emoji particles | 1 — static "5 ★ / 100 🏆" | 2 — emoji everywhere + primitive pet | 2 — hard-coded pixel rectangles, pointer-only, no keyboard/controller, no test file | 2 — monolithic app with magic coordinates; untested |

**Pet House redesign spec (absorbs `cucciolo_mio` + `clinica_cuccioli`)**
- Target: one warm pet house where a 3–6-year-old **reads a pet's needs from its body language** and responds with the right routine — empathy and daily-routine sequencing, not tapping meters.
- Rooms (swipe/arrow between 4 picture tabs): kitchen (feed), bathroom (wash), garden (play), bedroom (sleep) + vet corner (from Clinica) when the pet looks unwell.
- Needs model: one active need at a time, shown by the pet (tummy rumble + looks at bowl; muddy paws; yawning; droopy + cough cloud; bored + brings ball). No numeric meters; a 4-icon "day strip" (sun→moon) shows routine progress.
- Food choice matters: each pet has a favourite and a no-thanks food; vet corner has a meaningful order (look → clean → bandage → treat → cuddle).
- Progression: day 1 two needs; day 2 four; day 3 vet visit; later days introduce a second pet and "who needs what?" choices. One full day ≈ 3 minutes; ends with bedtime (optionally hands off to Nanna's night).
- Pets: puppy, kitten, bunny as non-cast `creature.pet.*` (rules §8.6); optional monster from Morbidi later.
- Feedback: spoken pet reactions (SFX + short lines), heart pop, pet `happy` state; Dani (`pose_point`) as the friendly vet.
- New art: `bg.indoor_room.{kitchen,bathroom,bedroom,vet_corner}`, `bg.meadow_day.garden` variant, `creature.pet.{puppy,kitten,bunny}` × {neutral, hungry, muddy, sleepy, unwell, happy}, `prop.pet.{bowl,bath_tub,sponge,towel,ball,bed,brush,stethoscope,bandage,treat_box}`, `prop.food.*` (shared), `fx.{heart_pop,bubble,sparkle}`.
- Voice lines: "I'm hungry!", "I'm muddy!", "I'm sleepy!", "I don't feel well…", "Thank you!", 3 food names (+ reuse), "Time for bed".
- Effort L (new Activity body; reuse Clinica's tested `ClinicSession` treatment seam). Risks: scope creep into a Tamagotchi — no decay while away, no guilt mechanics, no time pressure.

## 14. `volo_draghetto` — Little Dragon's Flight — 20/40 — CUT-or-MERGE (into `viaggio_delfino`)

**Played:** hover-steer up/down, Look (accessory cycle), 15 s flight, 800×480.

| L | A | F | J | P | V | U | T |
|---|---|---|---|---|---|---|---|
| 1 — no learning objective | 3 — no fail state; "LOOK" text button | 3 | 3 — star bursts, rainbow dash | 1 — endless; stars counter only | 3 — cute dragon; plain sky | 2 — no controller handling; hover-follow means clicking LOOK flies the dragon into the top-left near Home; touch needs drag | 4 |

**Redesign spec**
- Target: do not ship a second endless vertical-steer collector next to `viaggio_delfino`; fold the dragon in as an **air world** of the Dolphin journey (same steering, same course/finish structure, different biome and character).
- If kept standalone, it needs the colline-style finite course: 60-s flight to a castle, 3 rainbow gates as progress dots, gentle cloud bumps, levels adding wind gusts.
- Accessories → move to a pre-flight "dress the dragon" card (picture buttons), not mid-flight.
- New art (if merged): `bg.sky_clouds.*` (shared), `creature.fantasy.dragon` (flat SVG from current design), `prop.sky.{rainbow_gate,castle_goal}`.
- Voice lines: none required.
- Effort S (merge) / M (standalone rework). Risks: Delfino is outside this audit group — decision belongs with that auditor/owner.

---

## Cross-Activity findings

### A. Duplicates and overlaps

1. **Marine overload (4 Activities):** `acquario_magico`, `baia_delle_orche`, `sottomarino_giramondo`, `viaggio_delfino` (+ Encyclopedia ocean/octopus). Acquario and Baia are both "tap and feed sea creatures in a pretty tank" with no learning loop. → **Merge Baia into Acquario as one Ocean Activity** (§5/§7). Sottomarino/Delfino decisions belong to their auditor; the shared `creature.marine.*` set should serve all of them.
2. **Care overload (feeding appears in 5 Activities):** `cucciolo_mio` (feed/bath/play/sleep/dress), `clinica_cuccioli` (bath/bandage/treat/cuddle), `baia_delle_orche` (feed/cuddle), `acquario_magico` (feed), `nanna_delle_nuvolette` (bedtime). Cucciolo and Clinica overlap almost entirely (bath, treat, cuddle) and neither models needs. → **One Pet House** (§13) for routines + empathy; Nanna stays as the separate calm wind-down with a real colour/count task; feeding in the Ocean becomes diet *knowledge*, not care.
3. **`morbidi_mostriciattoli` is not a care Activity** — it is a character creator and belongs in **Create**, competing with `faccine_momo` (expressions) and `shape_garden` (composition) only loosely. Its value depends on publishing a PNG friend into Creations/Teatrino. Keep, rework (§9).
4. **Endless steer-and-collect ×3:** `volo_draghetto`, `viaggio_delfino`, and (by behaviour, after the target distance) `colline_allegre`. → Courses with finish lines everywhere; merge the dragon into Delfino.
5. **Two "explore a nature scene by toggling" toys:** `quattro_stagioni` and `piccola_serra` (outside this group) both show a tree/plant changing; share `prop.tree.seasonal_*` and differentiate by intent (seasons/weather knowledge vs plant needs/growth sequence).
6. **Off-model cast in this group:** `quattro_stagioni` (own fox called Tito), `corsa_bacche` (squirrel called Momo), `torre_forme` (cat called Lilli), `colline_allegre` (unnamed orange driver), `enciclopedia_greia` (Leo on Home, Tito on entries — inconsistent guide role). All should consume `character.*` + `pose_cheer`/`pose_point`.
7. **Fake claims in manifests** (education skills/categories not supported by gameplay): `nanna` (colour matching, small sets), `colline` (adaptive difficulty), `clinica` (care sequencing), `acquario` (marine lexicon), `torre` (geometry). Fix gameplay or the manifest in the same tranche.

### B. Cross-cutting recommendations (priority order)

1. **Every loop needs a spoken goal and an end.** 9 of 14 Activities have no finish condition or no progression. Standardise a "mission → act → celebrate (cast `pose_cheer`) → progress dots" loop using the control kit's prompt banner + progress dots, with finite rounds of 1–3 minutes.
2. **Pre-reader feedback must be audible and pictorial, never text-only.** Remove text-only error/success banners (`pasticceria`, `cucciolo`, `morbidi` buttons, `torre` mode tabs, `baia` fact text) — speech line + character reaction + icon. Spoken names are missing in `acquario`, `nascondino`, `baia` (EN facts are present), `clinica`.
3. **Input parity is a platform job.** Only `enciclopedia` consumes `greia_platform.input_core`; 7 of 14 Activities have no keyboard and 11 have no controller path. The runtime adapter should give every `pointer` Activity the Greia virtual pointer, and the control kit should provide focus-ring navigation for toolbars, so Activities do not hand-roll it. Fix `nanna`'s tap-pick/tap-place cancel bug as part of the kit's drag helper (only cancel when a drag actually started).

### C. Curriculum gaps a NEW Activity should fill (max 3)

1. **Sorting & classifying ("Tidy-up Time", Learn/Play, age 3–5).** Sort toys by colour → shape → size → category ("things that fly") into labelled-by-picture boxes with Flash; later two attributes ("big *and* red"). Foundation for early maths/logic that no current Activity teaches directly.
2. **Sequencing & daily routines ("First, Then, Last", Learn, age 3–6).** Put 3–5 picture cards of a familiar process in order (getting dressed, planting a seed, baking a cake, frog life cycle) and watch the cast act it out; reuses Encyclopedia/Pet House/Bakery art. Narrative sequencing and temporal language are missing.
3. **Rhythm echo & beat ("Echo Drums", Music, age 3–6).** Call-and-response on 3–4 big drums: a cast member plays 2–6 beats, child repeats; later loud/soft and fast/slow. The music family has a single Activity (`orchestra_animali`) and no listening-memory loop.

### D. Shared assets to author once (SVG rules, Opus-authored)

| Semantic ID family | Assets | Consumers (this group → others) |
|---|---|---|
| `bg.meadow_day.{sky,far,mid,ground}` (+ `garden`, season tints) | restyled meadow kit | nascondino, colline, quattro_stagioni, pet house garden → bosco_numeri, costruiamo_ponti, shape_garden, piccola_serra |
| `bg.pond_day.*`, `bg.autumn_wood.*`, `bg.snow_wood.*` | 3 extra woodland kits | nascondino, quattro_stagioni, corsa |
| `bg.underwater.*`, `bg.sea_surface.*` | ocean kits | Ocean (acquario+baia) → sottomarino, viaggio_delfino, enciclopedia ocean |
| `bg.night_sky.*` | stars, moon, soft hills | nanna, pet house bedroom, quattro_stagioni night → stelle_incantate, festa_delle_rime |
| `bg.sky_clouds.*` | layered clouds | volo/delfino air world, colline sky |
| `bg.indoor_room.{kitchen,bathroom,bedroom,vet_corner,bakery,playroom}` | wall/floor variants | pet house, pasticceria, torre → bottega, alfabeto_leo, officina |
| `prop.food.*` (12) | apple, strawberry, blueberry, cherry, banana, carrot, cookie, cupcake, chocolate, fish, milk, seed | pasticceria, pet house, corsa, quattro_stagioni → counting Activities (replaces emoji) |
| `creature.woodland.*` (proposed namespace; fallback `prop.animal.*`) | fox, bunny, owl, hedgehog, squirrel, frog, beetle — `peek`/`full`/`asleep` | nascondino, corsa, quattro_stagioni, enciclopedia animals |
| `creature.marine.*` | 8 reef creatures + 3 orcas (with sources) | Ocean → sottomarino, delfino, enciclopedia |
| `creature.pet.*` | puppy, kitten, bunny × 6 states | pet house |
| `prop.tree.seasonal_{spring,summer,autumn,winter}` | one tree, 4 canopies | quattro_stagioni → piccola_serra |
| `prop.blocks.*` | wooden square/rectangle/triangle/half-circle/arch/cylinder + outline slot | torre → costruiamo_ponti, shape_garden, la_discesa_della_biglia |
| `fx.{sparkle,confetti,heart_pop,bubble,dust_puff,shooting_star,rain,snow,leaf_drift}` | feedback/weather FX | all 14 |
| `icon.hud.*` | basket, star, heart, bookmark, play, undo, save, camera, rotate, arrow ×4 | all HUD chips via control kit |
| `character.<id>` poses `pose_cheer` / `pose_point` (exist) | consume; no Activity-private cast drawing | all 14 |

### E. Bugs observed in passing (for the Activity owners)

- `nanna_delle_nuvolette`: tap-pick then tap-place never works (release over the blanket cancels the held item in `_handle_pointer_drop`).
- `morbidi_mostriciattoli`: large white highlight circle covers the upper-left face on every body; gallery hit-tests/draws 12 of `MAX_SAVED_PORTRAITS = 24`.
- `cucciolo_mio`: any tap in the content area feeds (food choice ignored); Dress cycles on the tab tap itself; no test module.
- `colline_allegre`: difficulty hard-coded to 2; collectibles exhausted after ~700 m; no finish/end state.
- `quattro_stagioni`: weather particles persist across season changes; summer + wind shows falling autumn leaves.
- `torre_forme`: free-build grid persists into Gentle mode; Gentle mode lacks a Rotate button.
- `enciclopedia_greia`: activation FX persists after another hotspot is chosen; frog caption overflows; Leo overlaps Pyramids portal (backlog).
- `pasticceria_magica`: error banner overlaps the Clear button.
- `volo_draghetto`: hover steering drives the dragon into the Home corner when the child reaches for LOOK.
- `baia_delle_orche`: Song-mode bells overlap the ring/orcas; craved food cannot be chosen.
- Tooling note: `ActivityStorageClient` falls back to `~/.greia-simulator/standalone-storage` unless `GREIA_STANDALONE_STORAGE_DIR` is set, so `tools/headless_greia_activity.py` runs share and mutate one host store across runs (seen as "1116" stars in Nascondino). The tool should point it at its temporary sandbox.
