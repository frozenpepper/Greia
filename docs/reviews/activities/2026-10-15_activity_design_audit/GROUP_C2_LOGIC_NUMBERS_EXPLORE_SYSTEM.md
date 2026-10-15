# Activity design audit — Group C2: logic, numbers, exploration, system

**Date:** 2026-10-15 · **Auditor:** design-c2 (Opus; game designer + early-years learning designer, ages 3–6, pre-readers)
**Status:** design review and recommendation for the main agent and owner. No source, asset, manifest or test was changed.
**Evidence label:** SOURCE + DESKTOP VISUAL REVIEW.
- Real Pygame frames came from the Greia simulator bridge (`greia_simulator.python_activity`, the same path as `tools/headless_greia_activity.py`).
- A scratch multi-step driver sent clicks, drags and keys. It used a seeded RNG so puzzles could be replayed. Locale `en`, 1024×600, plus one 800×480 capture per Activity. 4–10 captures per Activity.
- Activity storage and customization went to scratch stores.
- Checkout `main` @ `3ee4bda1`, with other agents' uncommitted edits in the working tree.
- There is no Shell, VM, Acer or physical evidence. Audio was not heard (dummy driver). Speech coverage comes from the shipped files and receipts.

**Activities (9):** `quattro_amici`, `specchi_magici`, `stelle_incantate`, `treno_numeri`, `piccola_serra`, `sottomarino_giramondo`, `viaggio_delfino`, `costruiamo_ponti`, and `workshop_settings` (the system "My Greia" space, judged as child-facing system UX).

This report extends Group A (`GROUP_A_MATH_LITERACY_LOGIC.md`) and Group B (`GROUP_B_NATURE_CARE_ACTION_MAKING.md`). Their shared-asset sets and feedback grammar are assumed and not repeated:
- `bg.meadow_day.*`, `bg.night_sky.*`, `bg.underwater.*`;
- `prop.food.*`, `creature.marine.*`, `fx.*`, `icon.hud.*`;
- the shared completion scene;
- `pose_think`/`pose_wave`.

Scores are 1–5 for: **Obj** learning objective clarity/correctness · **Age** age fit 3–6 / pre-reader independence · **Loop** core-loop fun · **FB** feedback & juice · **Prog** progression/replay · **Vis** visual quality & on-model cast · **Use** usability/input/Home safety · **Tech** technical health.

## Summary (best → worst)

| Activity | Portfolio family | Score /40 | Verdict | Effort |
|---|---|---:|---|---|
| `specchi_magici` | Logic & spatial (symmetry) | 26 | POLISH | M |
| `viaggio_delfino` | Motor/action + nature (withheld) | 26 | POLISH → becomes the **Journeys** host (absorbs `volo_draghetto` as the sky world) | M |
| `treno_numeri` | Math & quantities | 25 | REWORK (it has to require a decision: count-out / make-N / numeral match) | M |
| `stelle_incantate` | Math & quantities (number order) | 24 | REWORK (hide the answer, speak numbers, make it the number-sequence home) | M |
| `workshop_settings` | System — My Greia | 23 | REWORK (system UX: preview, voice, delight, safe wallpaper source) | M |
| `sottomarino_giramondo` | Nature (marine, withheld) | 22 | CUT-or-MERGE → **dive mode of the Ocean Activity** (Group B §5); keep its "Captain says" listening loop | M |
| `piccola_serra` | Nature (withheld) | 20 | CUT-or-MERGE → plant world of Group B's **"First, Then, Last"** sequencing Activity | M |
| `costruiamo_ponti` | Logic/building (withheld) | 20 | RETHINK (a length-and-support bridge puzzle, not icon copying) | M–L |
| `quattro_amici` | Logic & strategy | 17 | REWORK (**currently unplayable after the first disc**: S fix, then cast/feedback M) | S + M |

**Bottom line.** None of the nine is flagship-ready, and the group has two hard blockers.
- **`quattro_amici` cannot be played.** The drop animation never settles, so Leo never moves, and in two-player mode the second disc is refused. A drop-clack also fires about 20 times per second for ever.
- **`sottomarino_giramondo` can never leave 5 m depth.** Two of its three biomes are unreachable, along with the dolphin, manta, angler and whale species and their recorded facts.

The commonest design debt is **answer-revealing scaffolds**: the child taps through without thinking.
- Stelle highlights the next star.
- Treno prints the sum and auto-caps the count.
- Serra's thought bubble names the tool.
- Ponti draws the required block in every slot and marks it green or orange before GO.

Four Activities hide the OS pointer and draw no replacement (`treno_numeri`, `piccola_serra`, `costruiamo_ponti`, `viaggio_delfino`), so a mouse user cannot see where they are pointing. Four have no instructional voice at all (`treno`, `serra`, `ponti`, `workshop`), and `quattro` has two celebration clips only.

---

## 1. `specchi_magici` — Magic Mirrors (manifest age 5–7) · 26/40 · POLISH

**Played:**
- L1 start;
- wrong cell (rejected, wobble);
- one correct;
- puzzle complete → puzzle 2;
- L4 seeded (rotated triangles);
- 800×480.

| Obj | Age | Loop | FB | Prog | Vis | Use | Tech |
|---|---|---|---|---|---|---|---|
| 4 | 3 | 3 | 3 | 4 | 3 | 2 | 4 |

- **Obj 4:** reflections are geometrically correct (`reflect_piece`, `mirror_col`), and L5 mirrors right→left. The tray, however, holds the **already-reflected** pieces, so the child never decides orientation. The "spatial rotation" skill is reduced to "same row, same distance from the mirror".
- **Age 3:** the voice welcome, prompt and right/retry lines exist (14 cues). Cells are 52 px (≈40 px at 800×480): small for age 4–5. The pieces are random scatter, not a picture, so there is no "aha".
- **Loop 3:** select a piece then tap a cell. It is clean but abstract; six puzzles per set.
- **FB 3:** the wrong wobble lasts 0.28 s and the completion shimmer 0.35 s, too fast to read. A wrong tap never shows where the piece *should* go. The end is the generic text completion card.
- **Prog 4:** five tiers with bounded adaptation, persisted (the best progression in this group).
- **Vis 3:** a pretty stage/curtain theme and on-model Lilli. The ES/FR voice receipts name `greia.leo.v1` while Lilli is on screen. The completion screen is generic.
- **Use 2:** pointer only. There is no keyboard/controller path despite the ADR 0020 standard. **Undo only removes *correct* pieces** (wrong ones are never placed), so the button can only make things worse.
- **Tech 4:** event-driven redraw at 20 fps idle; fine.

**Redesign spec**
- Target: "Lilli's Magic Mirror". Half a picture (butterfly, house, robot Dani, flower, rocket) is on the left; the child completes the mirror half and the picture comes alive (wings flap, rocket launches).
- Puzzles become **authored half-pictures** built from the existing four tile shapes (plus rhombus/heart), not random scatter. There are 24 designs in 4 themes.
- Tiers:
  - T1, 2–3 tiles next to the mirror, each in its own row;
  - T2, tiles one or two columns away;
  - T3, rotated tiles, where the tray offers the **unreflected and reflected** versions (a rotate button on the tile) so orientation is a real choice;
  - T4, the mirror on the right;
  - T5, horizontal mirror (water reflection).
- Adaptive rule: keep the current rule. On a second error in the same puzzle, Lilli `pose_point`s and a ghost tile pulses in the target cell (demonstrate, then retry).
- Replace Undo with **drag a placed tile back to the tray** (or tap it); remove the Undo button.
- Input: arrows move a cell cursor (the platform focus ring), A/Space places, shoulder/Tab cycles the tray. Cells are ≥ 64 px (grid 6×5 per half instead of 4×6 to fit).
- Celebrate: when the picture completes, it is animated, Lilli does `pose_cheer`, and `fx.sparkle` runs along the mirror line. The completion scene is a gallery wall of finished pictures (the shared completion scene).
- Optional reward mode: "free mirror painting". Tiles mirror live, and the picture saves to Creations as PNG. This is a real creation, unlike the puzzle mode.
- New art:
  - `prop.mosaic_tile.{circle,square,triangle,semicircle,rhombus,heart}` (flat, 6 palette colours, 128);
  - `prop.mirror_picture.{butterfly,house,rocket,flower,fish,robot}_frame` (prop 512×256, completed-state overlays for animation);
  - `bg.stage_theatre.{curtain,floor}` (scene layers; can be shared with `teatrino_fiabe`);
  - `fx.mirror_shimmer`.
- Voice (EN): "Make it the same on the other side!", "Look at the mirror line.", "Turn it around!", "It's a butterfly!" (one per picture, 24), "Try this spot!".
- Effort M. Risk: authored pictures must be solvable with the tile set at 6×5 per half; keep the generator for T5 variety.

## 2. `viaggio_delfino` — The Dolphin's Journey (age 4–8, withheld) · 26/40 · POLISH → Journeys host

**Played:**
- start + wordless swim tutorial;
- hover steering low/high;
- leap/dash;
- Tito button;
- 60 s run into chapter 2;
- 800×480.

| Obj | Age | Loop | FB | Prog | Vis | Use | Tech |
|---|---|---|---|---|---|---|---|
| 2 | 4 | 3 | 3 | 3 | 4 | 3 | 4 |

- **Obj 2:** this is a motor/tracking game. The six Tito facts are well sourced but adult-level ("mammal", "echolocation"), unrelated to what is on screen, and only heard when the child taps Tito.
- **Age 4:** there is no fail state; jellyfish only nudge. The spoken welcome tells a 4-year-old to "press the space bar" (device words). The tutorial's Space key renders as an **empty white box**.
- **Loop 3:** gentle steer-and-collect with satisfying leaps. Pearl lines are well paced; there is nothing to decide.
- **FB 3:** sparkles, pearl counter, jelly bounce. No celebration at chapter borders, and the end is a text completion.
- **Prog 3:** a real finite structure (3 chapters × ~1 min, progress rail with chapter dots). The chapters look almost identical (the "kelp forest" at 60 s still showed open water and jellies).
- **Vis 4:** a lovely flat dolphin and kawaii jellies. Tito's button is on-model. The background is coherent.
- **Use 3:** **the OS pointer is hidden** with no replacement. Hover-steering works for mouse; touch needs drag. No controller handling (the hybrid profile promises it).
- **Tech 4:** bounded caption cache and lightweight drawing.

**Redesign spec**
- Target: one **Journeys** Activity with the same steering engine and three worlds, each a 60–90 s finite course with a goal at the end:
  - Sea (dolphin, this one);
  - Sky (the dragon from `volo_draghetto`, per Group B §14);
  - River (the duckling; optional later).
  A world-picker card row with three big pictures sits at the start. **Confirmed technically compatible:** both are y-steer + dash + collect, and only the biome layer, the hero sprite and obstacle kinds change.
- Each world has a mission spoken at the start that turns collecting into a learning micro-task:
  - L1 "Collect all the pearls!" (counting, 5 chapter progress dots);
  - L2 "Only the **pink** shells!" (colour discrimination, inhibition);
  - L3 "Follow the dolphin family!" (keep in the pod = tracking);
  - L4 "Find 3 starfish, then leap over the boat!" (two-step instructions).
- Facts become **contextual discoveries**. A turtle/whale/pod swims past, a sparkle marks it, and touching it plays a one-line simple fact ("Dolphins breathe air! Splash!"). Each world has a 6-sticker "journey book" page.
- Chapter borders: a finish arch, Tito `pose_cheer` and a pearl-total count-up spoken with the shared numbers (§Cross C).
- Input:
  - restore a visible pointer (platform pointer);
  - touch = drag anywhere;
  - controller = left stick/D-pad + A for leap;
  - tutorial key art from `icon.hud.key_space` / `icon.hud.button_a` (no blank box).
- New art:
  - `bg.sea_journey.{kelp,reef,open_sea}_mid` (scene mid layers per chapter, so the chapters look different);
  - `prop.journey.{finish_arch,boat,pink_shell}`;
  - `creature.marine.{dolphin_pod_member,whale_pass,turtle_pass}` (reuse Group B `creature.marine.*`);
  - for the sky world, `bg.sky_clouds.*` and `creature.fantasy.dragon` (Group B list).
- Voice (EN): 4 mission lines per world (12), 6 short child-level facts per world (18), and "You made it!".
- Effort M (plus S per extra world). Risks: migrating `volo_draghetto` saves/achievements; keep one card in Play (not three).

## 3. `treno_numeri` — Number Express (age 4–7) · 25/40 · REWORK

**Played:**
- station 1 addition (tap crate 3 + crate 2 → 5, celebration);
- station 2 count (tap "+1" crate × 7, auto-capped at 3);
- 800×480.

| Obj | Age | Loop | FB | Prog | Vis | Use | Tech |
|---|---|---|---|---|---|---|---|
| 2 | 4 | 2 | 4 | 2 | 4 | 3 | 4 |

- **Obj 2:** the manifest claims cardinality and quantity matching, but **no input can be wrong**.
  - Addition: the header shows "3 + 2 = 5" and the child taps both crates.
  - Count mode: "+1" can be tapped endlessly and the model caps at the target, so stopping at the right number is never required.
- **Age 4:** large crates and nothing to fail. The prompt is text-only (no voice line exists; the item names carry emoji).
- **Loop 2:** tap until the train leaves. The arrival/departure spectacle carries it, not the thinking.
- **FB 4:** a charming chugging train, fruit arcs into the wagon, confetti, progress dots. Fruit draws over the wagon edge.
- **Prog 2:** 5 fixed stations with random tiny targets (2–6) and no adaptation. The persisted "stars" counter is a gold disc + number.
- **Vis 4:** the best vehicle art in the group (SVG sources). Dani as conductor is on-model. Emoji remain in buttons/strings (`🚂 Whistle!`, `🟢 Go!`).
- **Use 3:** **pointer hidden** with no replacement. Keyboard crate cycling works. No controller.
- **Tech 4.**

**Redesign spec**
- Target: Dani's train is the **counting-out** home: the child must decide how many and stop. This is the inverse of Giardino's tap-counting and the next rung of Group A's number ladder. **Move Group A's proposed Giardino S5 ("make N") here instead of building it twice.**
- Core task: the station sign shows the order as a numeral + dot card, and Dani speaks it ("Four apples, please!"). The child drags or taps fruit one at a time from a big pile into the wagon; each fruit is counted aloud (shared numbers). Pressing the whistle departs.
  - Right → departure.
  - Too many/few → the wagon creaks, Dani `pose_point`s, and the fruit are recounted aloud one by one with the extra/missing slot highlighted. Unlimited retry.
- Stages (adaptive ladder, no menu):
  - S1, N 1–3 with dot card + numeral;
  - S2, 1–5 numeral only;
  - S3, 1–10 with 5-slot wagons (a two-wagon ten-frame);
  - S4, **match numeral → wagon**: three wagons arrive with 2/4/5 fruit and the child sends the one that matches the sign;
  - S5, **more/fewer**: "Which wagon has more?" (one-to-one lines drawn between fruit).
- Adaptive rule: 3 clean stations → up; 2 miscounts in one stage → down. The journey is 5 stations, then the terminal (shared completion scene with the train arriving at a party station).
- Remove the addition stations. Casa del dieci owns part-whole (Group A), so Treno no longer duplicates it with a give-away equation.
- New art:
  - `prop.vehicle.train_{loco,wagon,wagon_full}` (promote the existing SVGs to shared);
  - `prop.station.{sign_board,platform,party_terminal}`;
  - `ui.card.dot_{1..10}` (blank card + dot layout at runtime is fine);
  - shared `prop.food.*` (Group A/B) instead of emoji fruit.
- Voice (EN): "N apples, please!" ×(4 fruits × 10) can be avoided by composing "[number] … [fruit plural]" from the shared numbers + 4 fruit-plural clips. Plus "All aboard!", "Let's count again.", "Which wagon has more?", "Toot toot!".
- Effort M. Risk: composite speech timing. Keep one sentence template, and test the IT plural/gender ("quattro mele").

## 4. `stelle_incantate` — Enchanted Stars (age 4–7) · 24/40 · REWORK

**Played:**
- Triangle: out-of-order tap rejected, 1→2→3, celebration + fact bubble, Next;
- Cassiopeia complete;
- Swan start at 800×480 (persisted progress).

| Obj | Age | Loop | FB | Prog | Vis | Use | Tech |
|---|---|---|---|---|---|---|---|
| 2 | 3 | 3 | 3 | 2 | 3 | 4 | 4 |

- **Obj 2:** the claimed skill is number order, but **the focus ring automatically jumps to the next star**, so the child taps the glowing ring and never reads a numeral. No numbers are spoken (star taps play tones). The facts are adult-level and partly unrelated (the Triangle's fact is "there are 88 official constellations").
- **Age 3:** taps are forgiving (46 px radius). Unlit stars are tiny grey 28 px digits on a dark sky, and the lit-star sprite covers its own numeral.
- **Loop 3:** connect-the-dots is pleasant. The promised "constellations come alive" never happens: only lines plus a name banner.
- **FB 3:** tones, line draw, name banner, spoken fact on tap. The lit-star sprite is malformed (asymmetric 4-point rays), and the name banner covers star 1.
- **Prog 2:** 6 constellations of 3–7 stars (≈3 minutes of content), then the first one repeats.
- **Vis 3:** the night sky is coherent and Leo is on-model, but this is visually the emptiest first screen in the group (backlog confirmed).
- **Use 4:** pointer, number keys, arrows, Space.
- **Tech 4.**

**Redesign spec**
- Target: Leo's **night-sky number path**. It is the curriculum's home for **number sequence 1–10 → 1–20, counting on, missing numbers and counting back**, and each finished figure becomes an animated picture (lion yawns, swan flies).
- Remove the auto-advancing focus ring. Every tap says its number aloud (shared numbers), and the next star is only hinted after 6 s idle or a wrong tap (Leo `pose_point` + a soft pulse).
- Stages:
  - S1, 1–5, stars spaced on a gentle path;
  - S2, 1–10;
  - S3, "start at 4" (count on);
  - S4, one numeral missing, where the child picks the missing number from 3 star-badges;
  - S5, countdown 10→1, where a rocket launches at 0 (count back);
  - S6, 1–20 by tens-pairs.
- Content: 12 figures across 3 skies (the existing 6 real constellations, plus 6 friendly "Greia" figures: rocket, Dani, fish, house, kite, flower). Facts are simplified to one sentence for 4-year-olds and tied to the figure ("The swan flies in summer!").
- Celebrate: line art fades into a silhouette illustration; Leo `pose_cheer`; the figure joins a "my sky" map (replay-collection screen).
- Adaptive rule: 2 clean figures → next stage; 2 wrong taps on the same star → demonstration then retry.
- New art:
  - `prop.star.{dim,next_hint,lit}` (FX 128, symmetric, numeral plate kept readable);
  - `prop.constellation.{triangle,queen,swan,dipper,lion,hunter,rocket,fish,house,kite,flower,dani}` (prop 512×256, line-art-friendly silhouettes);
  - `fx.star_trail`;
  - `prop.rocket.launch` (countdown);
  - `bg.night_sky.*` (Group A).
- Voice (EN): shared numbers 0–20 (Cross C), "Start at four!", "Which number is missing?", "Count down… blast off!", plus 12 one-line figure facts.
- Effort M. Risk: the 1–20 voice library is a cross-Activity dependency; build it first.

## 5. `workshop_settings` — My Greia (system UX, child space) · 23/40 · REWORK

**Played:**
- Colours tab (background/accent/text rows);
- an accent change re-themes the selection rings live;
- Wallpaper tab with no media (single red ✕);
- Size tab (three ABC-block sizes);
- Avatar tab (12 choices; selection persisted in the sandboxed profile);
- 800×480 (responsive, not letterboxed).

| Obj | Age | Loop | FB | Prog | Vis | Use | Tech |
|---|---|---|---|---|---|---|---|
| 3 | 3 | 2 | 2 | 2 | 4 | 3 | 4 |

- **Obj 3** (purpose: safe self-expression and ownership). Every choice is reversible and bounded, which is correct.
- **Age 3:** icon-only tabs are good. The colour screen, however, is three unlabeled rows (palette icon / star icon / ABC icon), and nothing explains that a row changes "the walls", "the sparkle colour" or "the letters". The ABC-blocks icon means both "text colour" (row) and "size" (tab). The wallpaper tab with no USB shows a lone red ✕, which a child reads as "wrong/broken".
- **Loop 2:** there is no delight moment: no voice, no sound, no character reaction, no live **preview of my Home**.
- **FB 2:** a small check badge flashes bottom-right for 0.8 s. The live accent ring change is the only visible consequence.
- **Prog 2:** a fixed set. There are no stickers/avatars earned from Activities (a natural, low-cost motivator that fits "platform-owned progression").
- **Vis 4:** clean, consistent core icons and on-model cast. The avatar set omits **Flash and Tito** while including a dino/wizard/car/globe/backpack/trophy. The tab icon stays the unicorn instead of showing my avatar.
- **Use 3:** the Greia pointer is drawn. Tab key and arrows work for size/wallpaper paging only; swatches/avatars have no keyboard or controller focus.
- **Tech 4:** bounded thumbnail cache and 1.5 s media rescans.
- **Safety:** a child can import **any image from an untrusted USB stick** as their wallpaper, with no parent review. This is contract-legal (read-only, imported copy), but it is a content-safety gap for a 3-year-old's space.

**Redesign spec**
- Target: "My Greia room". The child sees a **mini live preview of their own Home** (top half), with their avatar waving in it, and changes it by tapping big picture choices (bottom half). Every change is spoken and animated.
- Structure: four picture tabs:
  - **Me** (avatar, plus expression);
  - **Colours**, with two rows only: "my room colour" (background) and "my sparkle colour" (accent). Move text colour to Parent settings, because an unreadable text/background pair is possible and it is not a child preference;
  - **Pictures** (wallpaper);
  - **Big/small** (interface size, shown on the preview, not as abstract blocks).
- Wallpaper source: curated `bg.wallpaper.*` (8 built-in scenes) plus **the child's own paintings from the Creations Library** (Painting → "make it my wallpaper"). USB import moves to the Parent app (parent review). The ✕ card disappears.
- Feedback: on every choice the avatar does `pose_cheer` on the preview, `fx.sparkle` plays, and a voice line plays ("Your room is blue now!"). "Undo last change" is a back-arrow chip.
- Progression: Activities award avatar accessories/stickers through platform progression (hat, glasses, crown) that appear here. Locked items show as silhouettes with the Activity icon ("play Stelle to get the star hat").
- Avatars: all 6 cast members first (Dani, Flash, Leo, Lilli, Momo, Tito), then the 6 objects.
- Input: platform focus ring across tabs → grid; A selects; B returns to tabs.
- New art:
  - `ui.my_greia.preview_frame` (UI component);
  - `bg.wallpaper.{meadow,ocean,space,forest,castle,snow,candy,rainbow}` (scene 1024×600; reuse biome kits);
  - `prop.avatar_accessory.{hat_party,crown,glasses_star,bow,cap_captain,wizard_hat}` (prop 256, layered on cast poses);
  - `icon.hud.{room_colour,sparkle_colour,big_small,my_pictures}` (HUD 96).
- Voice (EN): "This is your Greia!", "Pick your friend!", "Your room is [colour] now!" (8 colour words), "Bigger!", "Smaller!", "What a nice picture!".
- Effort M. Risks:
  - accessories need a cast-layering contract (anchor points per pose);
  - the Creations→wallpaper path must respect Creations/Storage ownership (use the existing PNG share route, not file paths).

## 6. `sottomarino_giramondo` — Submarine Explorer (age 3–8, withheld) · 22/40 · CUT-or-MERGE → Ocean Activity dive mode

**Played:**
- start (auto fact banner);
- Captain's order "Turn to port!";
- Lights;
- 10× DOWN key (depth unchanged at 5 m);
- octopus encounter;
- Horn resolves it;
- 800×480.

| Obj | Age | Loop | FB | Prog | Vis | Use | Tech |
|---|---|---|---|---|---|---|---|
| 3 | 2 | 3 | 4 | 1 | 4 | 3 | 2 |

- **Obj 3:** the **Captain's orders** are a genuine early-years listening task: follow a spoken direction (stop/go/left/right, press the light). The marine facts are adult-level and auto-spoken whenever a creature passes ("all clownfish are born male…").
- **Age 2:** 11 controls; port/starboard jargon; fact/encounter banners are long text ("Honk the horn, release bubbles, or sound the alarm!"). Labels are about 9 px at 800×480.
- **Loop 3:** the cockpit fantasy is strong, but there is no goal: orders arrive every 8–14 s and facts stream continuously.
- **FB 4:** voiced orders and compliments, an octopus/shark encounter with giggles, and a good radar/gauges feel.
- **Prog 1:** **depth is not controllable.** `steer()` is only called with `dy = 0` and the lever is speed. The sub stays in the Coral Reef, so Kelp/Abyss, dolphins, mantas, anglers, whales and 3 × 4 recorded facts can never be seen. There is no end.
- **Vis 4:** an attractive cockpit. Porthole creatures are smooth-scaled from small sprites and look pixelated when close. "Angler" is labelled "Lanternfish".
- **Use 3:** keyboard covers buttons but not the wheel/lever drags. No controller.
- **Tech 2:**
  - the depth bug;
  - unbounded voice queue (facts queue faster than they play, so orders are heard late);
  - per-frame `smoothscale` for up to 26 entities plus several per-frame alpha surfaces (Acer risk).

**Redesign spec (as merge)**
- Target: in the single **Ocean** Activity (Group B §5: reef aquarium + orca bay), the submarine is the **dive mode** that travels between scenes. "Captain Tito says…" is the listening game that drives it.
- Loop: Tito (captain's hat, `pose_point`) gives one spoken order at a time, with a picture icon on the matching control:
  - "Go down!", "Stop!", "Lights on!", "Turn left!";
  - later two-step: "Go down, then lights on!".
  Obeying moves the sub; 5 orders reach the next zone (reef → kelp → deep), where a mission creature waits (Group B's reef "family" strip gains it).
- Controls reduced to 6 big picture buttons (up, down, left, right, lights, horn). Remove sonar/alarm/bubbles, or make them encounter-only. Words become left/right, never port/starboard.
- Facts are only on tap of a discovered creature, one short sentence, never auto-streamed. Bound the voice queue to 1 pending item (latest wins).
- Fix depth (up/down buttons + vertical drag), and render porthole creatures from pre-scaled size buckets (3 sizes cached), not per-frame smoothscale.
- New art:
  - `bg.underwater.{reef,kelp,deep}` (Group B, used as porthole layers);
  - `creature.marine.{manta,whale,angler,shark_friendly,octopus_friendly}` (prop 256, flat);
  - `ui.cockpit.{frame,porthole_ring}` (UI component);
  - `character.tito` captain-hat accessory (`prop.avatar_accessory.cap_captain`, shared with My Greia).
- Voice (EN): ~12 single orders, ~6 two-step orders, "Aye aye!", "Deeper and deeper!", plus a reuse of the existing creature names. Simplify the existing facts to one per species.
- Effort M as a merge once the Ocean shell exists. Risks: losing the standalone package ID (migrate `discovered_species`); the cockpit must fit the Ocean visual language.

## 7. `piccola_serra` — Little Green Thumb (age 4–9, withheld) · 20/40 · CUT-or-MERGE → "First, Then, Last" plant world

**Played:**
- seed pot 1 (sunflower);
- wrong tool on empty pot (silent no-op);
- water → sun → water → bloom;
- harvest (the pot empties, counter 1/6);
- 800×480.

| Obj | Age | Loop | FB | Prog | Vis | Use | Tech |
|---|---|---|---|---|---|---|---|
| 2 | 4 | 2 | 2 | 1 | 2 | 3 | 4 |

- **Obj 2:** the thought bubble always shows the needed tool, so the task is icon matching. The sequence seed→water→**sun**→water→harvest is arbitrary ("applying sun"). Carrots and strawberries "bloom" as flowers and are "harvested" the same way as sunflowers, which is botanically misleading.
- **Age 4:** big buttons and nothing can break. The plant type is chosen by tapping Seeds again, **invisibly** (no picture shows which seed is selected). The tool labels duplicate drawn icon + emoji + word.
- **Loop 2:** 5 identical taps × 6 harvests = 30 repetitive actions.
- **FB 2:** **a wrong tool does nothing at all** (no sound, no reaction). Harvest makes the plant vanish with no produce/basket moment. Plants are tiny; stage 1 is a 4-px dot.
- **Prog 1:** finishes at 6 harvests. `harvest_count` is saved but not loaded (P7 already notes this).
- **Vis 2:** flat primitive pots, half the screen is empty sky, no cast.
- **Use 3:** **pointer hidden.** Keyboard is partial (Tab for seed type, 1–4 for tools).
- **Tech 4.**

**Redesign spec (as the plant world of Group B's sequencing Activity)**
- Target: in "First, Then, Last", the child orders 3–5 picture cards of a bean's life cycle, then **does** it in a living pot. The plant only grows when its real needs are met (soil, water, light), and too much or too little shows (wilting, puddle).
- Sequence round:
  - S1, 3 cards (seed → sprout → flower);
  - S2, 4 cards (+ fruit);
  - S3, 5 cards including "water" and "sun" actions.
  Then the child acts it out on the pot; Flash narrates.
- Needs round (replaces the bubble): the plant shows a *symptom*, not the answer:
  - droopy leaves = thirsty;
  - pale, leaning to the window = needs light;
  - puddle = too much water, which a tap on the pot clears.
  The child chooses the fix from 3 picture tools; a wrong fix gives a gentle "Hmm, the plant is still thirsty" + Flash `pose_point`.
- Plants with honest cycles: bean (seed→pod), sunflower (seed→flower→seeds), strawberry (flower→berry), carrot (leaves→pull the root). The harvest flies into a basket that becomes a Pasticceria ingredient (cross-link).
- Seed choice is a visible seed-packet picture row.
- New art:
  - `prop.plant.{bean,sunflower,strawberry,carrot}_{seed,sprout,young,flower,fruit}` (prop 256, a growth-stage set shared with `quattro_stagioni`/Encyclopedia);
  - `prop.plant.state_{droopy,leaning,puddle}` overlays;
  - `prop.garden.{pot,watering_can,seed_packet_*,basket}`;
  - `ui.card.sequence_{blank,slot}`;
  - `bg.greenhouse.{wall,bench}` (scene).
- Voice (EN): "What comes first?", "Then…?", "The plant is thirsty!", "It needs light!", "Too much water!", "Look, beans!" (one line per plant), ~14 lines.
- Effort M (inside the new Activity). Risk: Group B's sequencing Activity must exist first; if it does not, ship this spec standalone as "Flash's Garden".

## 8. `costruiamo_ponti` — Bridge Builders (age 5–10, withheld) · 20/40 · RETHINK

**Played:**
- level 1, two correct planks + GO with empty slots (Flash falls, returns);
- wrong plank shown in orange before GO;
- solved level → level 2 canyon;
- 800×480.

| Obj | Age | Loop | FB | Prog | Vis | Use | Tech |
|---|---|---|---|---|---|---|---|
| 1 | 4 | 2 | 3 | 1 | 3 | 2 | 4 |

- **Obj 1:** every empty slot draws the required block, and placed blocks are marked right/wrong immediately. It is icon copying with an arbitrary code (`wood, wood, shroom, wood`), with no structural or physical reasoning. The manifest's "physics intuition" is false (P7 agrees).
- **Age 4:** a pre-reader can copy icons. Flash's fall/return is kind.
- **Loop 2:** copy, then watch.
- **FB 3:** hop, fall, confetti. No voice. A red trampoline floats under every bridge with no meaning.
- **Prog 1:** 3 fixed levels, then the end.
- **Vis 3:** Flash is on-model and the block SVGs are good. The canyon and space backdrops are primitive triangles/flat fills.
- **Use 2:** **pointer hidden** and pointer-only (only Escape on the keyboard); the hybrid profile is unimplemented.
- **Tech 4.**

**Redesign spec**
- Target: "Flash's Bridges", a **length and support** puzzle. Gaps are measured in unit stones; the child picks planks that are long enough, adds pillars, and tests with friends of different weights. It teaches longer/shorter, "just right", and heavier/lighter, which complements Bottega (Group A measurement) without copying it.
- Mechanics:
  - planks of length 1–4 units (visible unit notches);
  - the gap is shown as a dashed span on the water;
  - a plank too short falls in (splash, return);
  - too long sticks out but works (the right-length reward is a "just right" sparkle star).
  - From L3, pillars split a long gap. From L4, a heavy friend (Momo carrying a melon) needs stone planks, while wood bends then snaps with a funny boing.
- Levels (12, in 3 worlds: river, canyon, sky):
  - L1–3, one gap, choose 1 of 3 planks;
  - L4–6, two gaps;
  - L7–9, a pillar plus a long gap;
  - L10–12, weight (wood vs stone).
  Each level is solved by test-and-fix with unlimited GO.
- Adaptive rule: 2 failed GOs on a level → the needed plank gently glows (hint). Three-star rating = solved in 1 GO (shown, not required).
- Feedback: plank-length counting aloud ("one, two, three — just right!"). Flash/Momo `pose_cheer` at the picnic goal (they actually reach the picnic blanket). Shared completion scene.
- Input: visible pointer; drag planks; keyboard/controller via focus ring (pick plank → choose gap → A).
- New art:
  - `prop.bridge.plank_{wood,stone}_{1,2,3,4}` (wide prop 512×256);
  - `prop.bridge.{pillar,rope_rail,splash}`;
  - `prop.picnic.{blanket,basket}`;
  - `bg.canyon.*` and `bg.sky_islands.*` (scene layers; the river reuses `bg.meadow_day.*`);
  - `fx.{splash,snap_boing}`.
- Voice (EN): "Is it long enough?", "Too short — splash!", "Just right!", "Momo is heavy — try stone!", "Let's go to the picnic!" (~8).
- Effort M–L. Risk: overlaps the tactile build→GO→watch of `la_discesa_della_biglia` (Group A RETHINK). Keep biglia about *paths/cause-effect* and Ponti about *length/weight*, and share the "GO" control and test-replay pattern.

## 9. `quattro_amici` — Four Friends in a Row (age 3–7) · 17/40 · REWORK (blocker fix first)

**Played:**
- L2 start;
- first disc (it drops and then **never settles**);
- Leo's turn never comes;
- L1;
- two-player via M (the second disc is refused);
- 800×480.

| Obj | Age | Loop | FB | Prog | Vis | Use | Tech |
|---|---|---|---|---|---|---|---|
| 3 | 3 | 1 | 2 | 2 | 2 | 3 | 1 |

- **Obj 3:** the model is good: connect-3 on 5×4/6×5, then connect-4 on 7×6, with silly/defensive/smart/minimax CPU tiers and two-player turn-taking. Connect-3 strategy suits ages 5+ more than 3.
- **Age 3:** disc-icon turn banner, but the text banners/difficulty buttons ("1–4") and the mode toggle (one disc vs two discs) are not self-explaining.
- **Loop 1 (as shipped):** **`DropAnimation.update` never returns settled.** The bounce sets `current_y` above the target, which re-enters the falling branch, which resets `bounce_timer`, so the loop never ends. `app.active_drop` therefore stays set: Leo never thinks/moves, and two-player drops are refused. A 10-s pure-model check confirmed it never settles. Model unit tests pass because they never run the app loop. The design itself would score about 4.
- **FB 2:** the same bug fires `play_drop_clack` about 20 times per second for ever (counted 41 in 2 s). Only two shared celebration clips exist; no voice for turns/draws.
- **Prog 2:** 4 manual levels; `adaptive_difficulty = true` but nothing adapts. No persistence.
- **Vis 2:**
  - off-model cast: Leo as a **purple owl with yellow glasses** (canonical: brown owl, teal glasses), and Flash shirtless (canonical red lightning shirt);
  - both sit on black oval "bodies";
  - the meadow/board is otherwise tidy.
- **Use 3:** pointer, keyboard and D-pad hat/A button exist. Level buttons are 42 px.
- **Tech 1:** the blocker above.

**Redesign spec**
- **Immediate fix (S):** settle when the bounce timer expires, without re-entering the fall branch (track a `landed` flag). Add an app-loop test that drives `_update` until the CPU has moved. This is the single highest-value fix in the group.
- Target: "Flash vs Leo — Picnic Rows". A friendly table-top strategy game where Leo *thinks out loud with his face* and the child learns to make and block lines.
- Progression (automatic, no number buttons):
  - S1, 4×4 connect-3 versus silly Leo;
  - S2, 5×4 versus defensive Leo;
  - S3, 6×5 connect-3 versus smart Leo;
  - S4, 7×6 connect-4 versus smart;
  - S5, minimax.
  Win 2 of the last 3 → next; lose 3 in a row → back. Persist the stage. Two-friends mode stays a picture toggle (two avatars).
- Teaching layer:
  - when Leo blocks, he `pose_point`s at the child's almost-line ("You had two! I stopped you!");
  - after 2 child losses, a hint glow marks a winning/blocking column for 3 s;
  - the winning line animates disc by disc with spoken counting ("one, two, three — a row!").
- Feedback: voice for turns, draws and wins. Leo `happy`/`surprised` reacts to each move. Discs become carrots (Flash) and acorns (Leo) as real prop sprites.
- Visual: canonical `character.flash` and `character.leo` poses (no private drawing). Use the shared meadow table scene.
- New art:
  - `ui.board.drop_grid_{4x4,5x4,6x5,7x6}` (UI component, wooden);
  - `prop.token.{carrot_disc,acorn_disc}` (prop 128);
  - `fx.line_glow`;
  - `bg.meadow_day.picnic_table` (scene layer).
- Voice (EN): "Your turn, Flash!", "Leo is thinking…", "Three in a row!", "A draw — good game!", "I blocked you!", "Watch out, Leo has two!" (~10, Flash/Leo voices).
- Effort S (blocker) + M (rest). Risk: minimax depth 3 on 7×6 must stay within one frame on the Acer. Run the CPU search off the render step, or time-slice it.

---

## Cross-Activity findings

### A. Duplicates and overlaps (extending Groups A and B)

**Numbers.** Group A's ladder was Giardino → Luci → Casa → Bottega and left Treno and Stelle unverified. Verdict:

| Skill | Today | Owner after rework |
|---|---|---|
| Tap counting 1–10 | Giardino (+Bosco); Treno count mode is the same but give-away | **Giardino** |
| Counting out / make N; numeral → quantity; more/fewer between sets | nobody (Treno claims it but auto-caps) | **Treno** (takes Group A's Giardino S5) |
| Number sequence, counting on/back, missing number, 1–20 | Stelle (claimed, bypassed by the focus ring) | **Stelle** |
| Part-whole within 10 | Casa; Treno addition stations duplicate it with the sum printed | **Casa** (remove Treno addition) |
| Length / weight comparison | Bottega; Ponti could cover it | **Bottega** (units) + **Ponti** (just-right length, heavier) |

Resulting ladder:
1. Giardino count (age 2–4);
2. Treno count-out / match (age 4–5);
3. Stelle sequence (age 4–6);
4. Luci subitize (age 4–6);
5. Casa part-whole (age 5–7);
6. Bottega/Ponti measure (age 5–7).

**Marine and journeys.** Five Activities touch the sea: acquario, baia, sottomarino, delfino, plus the Encyclopedia ocean.
- One **Ocean** Activity: acquario reef + baia surface (Group B), with **sottomarino as its dive/travel mode** (§6).
- One **Journeys** Activity: delfino sea + volo_draghetto sky (Group B §14 confirmed: same steering and course model).

That leaves 2 cards instead of 5, each with a distinct verb: *observe/know* vs *move/collect*.

**Nature growth.** `piccola_serra` and `quattro_stagioni` both show plants changing by toggles. Serra's useful content (plant needs, life cycle) belongs inside Group B's "First, Then, Last" (§7), and Stagioni keeps seasons/weather. They share `prop.plant.*` / `prop.tree.seasonal_*`.

**Build → GO → watch.** Ponti, Biglia (A) and Torre (B) all use place-parts-then-test. Keep one shared "test" control and a "replay the run" pattern, and keep the concepts apart:
- Ponti = length/weight;
- Biglia = path/cause-effect;
- Torre = silhouette fitting.

**Logic/strategy.** Quattro is the only turn-taking strategy game and Specchi the only symmetry game. Neither overlaps anything; both need cast fixes and an input standard.

**Patterns (Group A #1).** Specchi's T5 horizontal mirror and the Pattern Parade are distinct (reflection vs repetition). They can share `prop.mosaic_tile.*`.

### B. Curriculum gaps for ages 3–6: new Activity proposals (max 3, none duplicating Groups A/B)

1. **Dani's Robot Path** (logic / early computational thinking, age 4–6). Greia is a computer for children, yet nothing teaches *plan → run → debug*.
   - Loop: Dani must reach a battery/flower on a 4×4 → 6×6 garden grid. The child lays 3–8 big arrow cards in a strip, presses GO, and Dani executes step by step, with each card lighting up as it runs. If Dani bumps or stops short, the child fixes the card where it went wrong.
   - Later stages: turn-left/right cards (instead of absolute arrows), a "repeat ×2" card, collecting 2 items.
   - It also teaches positional/directional words (left, right, forward), which only Sottomarino touches.
   - Art: `prop.code_card.{up,down,left,right,turn_l,turn_r,repeat}` (HUD/prop), `ui.board.grid_garden`, Dani `pose_point`/`pose_cheer`.
   - Voice ~12. Effort M. It reuses the build→GO→watch control above.
2. **Tito's Float Lab** (science inquiry, age 3–6). Serra claimed science and did not deliver it, and no Activity teaches *predict → test → observe*.
   - Loop: Tito holds an object (apple, key, leaf, coin, duck, stone, sponge, ball). The child first predicts by tapping "floats" or "sinks" (picture bowls), then drops it into the water tub, sees and hears the result, and sorts it on a results shelf. Later rounds: "heavy or light?" on a balance, then "will it roll?" on a ramp.
   - The joy is in the splash and in being surprised. There is no wrong answer to a prediction; the test is the teacher.
   - Art: `prop.lab.{tub,balance,ramp,shelf}`, `prop.everyday.*` (~16 objects, reusable by Sorting and Memory), `fx.{splash,ripple}`.
   - Voice ~20. Effort M.
3. **Picnic Fair Share** (early math: equal sharing and partitioning, age 4–6). Groups A/B cover counting, comparison and part-whole, but not dividing fairly, which is a core preschool concept.
   - Loop: 2–4 cast friends sit at a picnic. The child deals cookies/strawberries one at a time onto plates (one-to-one dealing); the friends react when shares are unequal ("Hey, Momo has more!"). The child fixes it, and any leftover is shared by cutting it in half.
   - Stages: 2 friends / 4–6 items → 3 friends → leftovers → halves.
   - It can ship as its own card or as a **mode of `pasticceria_magica`** (Group B rework) to keep the catalogue tight.
   - Art: `prop.picnic.{blanket,plate}` (shared with Ponti), `prop.food.*` (shared). Voice ~10. Effort S–M.

### C. Shared assets to author once (new items only; see Groups A/B for biome kits, food, creatures, FX, HUD, completion)

| Semantic IDs | Kind | Consumers |
|---|---|---|
| **Shared spoken numbers** `voice.number.{0..20}` (EN/IT, one narrator voice, plus a short "counting" cadence variant) | platform audio | stelle, treno, giardino(+bosco), luci, casa, quattro (line count), ponti (plank length), delfino (pearl count-up). Today number clips are Activity-private (`bosco_numeri/count_*`) and several Activities have none. **The highest-value voice investment for the math family; needs owner voice approval.** |
| Shared direction/position words `voice.word.{left,right,up,down,forward,stop,go,in,on,under}` | platform audio | sottomarino (Ocean dive), Robot Path, delfino missions, nascondino (Group B spatial words) |
| `prop.mosaic_tile.{circle,square,triangle,semicircle,rhombus,heart}` × 6 palette colours | prop 128 | specchi, Pattern Parade (A), torre silhouettes (B), shape_garden stickers |
| `prop.star.{dim,next_hint,lit}`, `prop.constellation.*` (12), `fx.star_trail` | FX / prop | stelle; nanna (B, night sky); festa (A, night square) |
| `prop.vehicle.train_{loco,wagon,wagon_full}` (promote existing SVG), `prop.station.*` | prop wide | treno; Robot Path (decor); Sorting (A) "load the right wagon" |
| `ui.card.dot_{1..10}`, `ui.card.sequence_{blank,slot}` | UI | treno, luci, casa (dot cards); serra-in-sequencing, First-Then-Last (B) |
| `prop.plant.<plant>_{seed,sprout,young,flower,fruit}` (bean, sunflower, strawberry, carrot) + `state_{droopy,leaning,puddle}` | prop 256 | sequencing (B) plant world, quattro_stagioni, enciclopedia plants, pasticceria (fruit) |
| `prop.bridge.plank_{wood,stone}_{1..4}`, `prop.bridge.pillar`, `prop.picnic.{blanket,basket,plate}` | prop wide | ponti, bottega (unit lengths), Fair Share, quattro picnic table |
| `ui.board.drop_grid_*`, `ui.board.grid_garden`, `prop.token.{carrot_disc,acorn_disc}`, `prop.code_card.*` | UI / prop | quattro, Robot Path, labirinto (A) grid reuse |
| `prop.avatar_accessory.{hat_party,crown,glasses_star,bow,cap_captain,wizard_hat}` with per-pose anchor points | prop 256 + cast contract | My Greia rewards, Ocean (Tito captain), teatrino puppets, completion scene |
| `bg.wallpaper.*` (8, cut from biome kits) | scene 1024×600 | My Greia; Shell Home wallpaper |
| `icon.hud.{key_space,button_a,drag_hint,go}` | HUD 96 | wordless tutorials in delfino, colline (B), corsa (B), ponti/biglia GO |

### D. Top cross-cutting recommendations for the main agent

1. **Fix the two blockers and the hidden-pointer class before any polish.**
   - `quattro_amici` drop settle (S).
   - `sottomarino_giramondo` depth control (S, even if it is later merged).
   - Remove `pygame.mouse.set_visible(False)` without a replacement in `treno_numeri`, `piccola_serra`, `costruiamo_ponti` and `viaggio_delfino` (use `draw_activity_pointer`, as `workshop_settings` does).
   - Give `specchi_magici` and `costruiamo_ponti` the keyboard/controller path their profiles promise.
   - Add app-loop tests (not only model tests). Quattro passed every model test while unplayable.
2. **Every task must require a decision; scaffolds appear only after hesitation or error.** Remove answer-revealing UI:
   - Stelle's auto focus ring;
   - Treno's printed sum and auto-cap;
   - Serra's tool bubble;
   - Ponti's per-slot required icon and pre-GO right/wrong marks;
   - Specchi's pre-reflected tray at higher tiers.

   Standard graduated hint (shared kit): 6 s idle → cast `pose_point` + gentle pulse; first error → demonstrate; never give the answer before the child tries.
3. **Consolidate by verb and give the math family one voice.**
   - Ocean (acquario + baia + sottomarino dive) and Journeys (delfino + volo).
   - Serra folds into First-Then-Last.
   - Treno/Stelle become the count-out and sequence rungs of Group A's ladder.

   Before any per-Activity voice work, author the shared spoken numbers 0–20 and direction words. Four of these nine Activities have zero instructional speech, and every number Activity needs the same 21 clips.

### E. Bugs observed in passing (for Activity owners)

- `quattro_amici`: `DropAnimation.update` infinite bounce (game-breaking) plus clack spam; `adaptive_difficulty = true` is unimplemented; off-model Leo/Flash.
- `sottomarino_giramondo`:
  - depth never changes (`steer(dx, 0.0)` only);
  - unbounded `_voice_queue`;
  - auto-fact speech floods ahead of orders;
  - "angler" shown as "Lanternfish";
  - per-frame `smoothscale` ×26.
- `specchi_magici`: Undo removes only correct placements; ES/FR receipts use the Leo voice for Lilli's lines; there is no keyboard/controller handling.
- `stelle_incantate`: the name banner covers star 1; the lit-star sprite has asymmetric rays and hides its numeral; the Triangle fact is unrelated to the triangle.
- `treno_numeri`: fruit overlaps the front wagon edge; emoji in button/strings; no voice for the prompt.
- `piccola_serra`: a wrong tool is silent; the selected plant type is invisible; `harvest_count` is not restored (P7).
- `costruiamo_ponti`: a meaningless trampoline under every bridge; only Escape on the keyboard.
- `viaggio_delfino`: the tutorial Space key renders as an empty white box; chapters are visually identical; the welcome speech names keyboard/mouse.
- `workshop_settings`:
  - the ABC-blocks icon means both "text colour" and "size";
  - the empty wallpaper tab shows only a red ✕;
  - Flash and Tito are missing from the avatars;
  - the tab icon does not show the chosen avatar.
- **Tooling:**
  - `greia_platform.activity_api._theme_store()` / `_ui_preferences_store()` fall back to the developer's `~/.greia-simulator/dev-customization` when `GREIA_CUSTOMIZATION_DIR` is unset;
  - `tools/headless_greia_activity.py` sets neither that nor `GREIA_STANDALONE_STORAGE_DIR`, so a headless My Greia or Activity run mutates the developer's real simulator state;
  - the tool should sandbox both (Group B noted the storage half).
