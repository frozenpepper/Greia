# Activity design audit — Group A: math, literacy, logic

**Date:** 2026-10-15 · **Auditor:** design-a (Opus; game designer + early-years learning designer)
**Scope label:** SOURCE + DESKTOP VISUAL REVIEW. Real Pygame frames came from the Greia simulator bridge (`greia_simulator.python_activity`, the same path as `tools/headless_greia_activity.py`), driven by a scratch multi-step input script, locale `en`, 1024×600 plus one 800×480 capture each. Checkout `main` @ `3b48dbfe`, with other agents' uncommitted Activity edits in the working tree. No simulator Shell, VM, physical hardware or listening review. Spoken-line texts come from voice receipts where they exist.
**Activities (13):** bottega_delle_misure, casa_del_dieci, il_giardino_dei_numeri, luci_di_momo, bosco_numeri, alfabeto_leo, festa_delle_rime, foresta_parole, sillabe_magiche, mondo_contrari, memory_meraviglie, labirinto_magico, la_discesa_della_biglia. `officina_dei_suoni`, `treno_numeri` and `stelle_incantate` were read only for the overlap analysis. They are not scored here.

Score scale per dimension: 1 poor … 5 flagship. Dimensions, in order: **Obj** learning objective clarity/correctness · **Age** age fit 3–6 / pre-reader independence · **Loop** core-loop fun · **FB** feedback & juice · **Prog** progression/replay · **Vis** visual quality & on-model cast · **Use** usability/input/Home safety · **Tech** technical health.

## Summary (best → worst)

| Activity | Portfolio family | Score /40 | Verdict | Effort |
|---|---|---:|---|---|
| il_giardino_dei_numeri | Math & quantities | 27 | POLISH (and absorb bosco_numeri) | M |
| casa_del_dieci | Math & quantities | 26 | POLISH | M |
| luci_di_momo | Math & quantities | 25 | POLISH | S |
| festa_delle_rime | Words & literacy | 25 | POLISH | M |
| labirinto_magico | Logic & spatial | 25 | POLISH | M |
| bosco_numeri | Math & quantities (withheld) | 24 | CUT-or-MERGE → `il_giardino_dei_numeri` | M |
| memory_meraviglie | Logic & spatial | 24 | POLISH (art is REWORK) | M |
| mondo_contrari | Words & literacy (concepts) | 22 | REWORK | M |
| bottega_delle_misure | Math & quantities | 21 | REWORK | M |
| alfabeto_leo | Words & literacy (withheld) | 20 | RETHINK | M |
| foresta_parole | Words & literacy | 19 | CUT-or-MERGE → `officina_dei_suoni` (catch round) | S |
| sillabe_magiche | Words & literacy (withheld) | 19 | RETHINK | L |
| la_discesa_della_biglia | Logic & spatial | 15 | RETHINK | L |

**Bottom line.** Nothing in this group is flagship-ready. The math family has one real progression (Garden → Lights → Ten House → Workshop), but the steps blur. Bosco and Garden are the same activity. Casa and Bottega both turn into number-choice quizzes at their higher levels. The literacy family is worse: "find the letter that goes with a picture" appears in **four** Activities (Alfabeto quiz, Foresta catch, Officina L2, Festa D4 alliteration ≈ Officina L1). Nothing teaches oral blending, the step that actually turns listening into reading. Common debts across the group:
- emoji used as content;
- primitive-drawn, off-model cast;
- text chips used as settings;
- one generic text-only completion card (`PygameCompletionScreen`, used by 16 Activities) with no cast, motion or voice.

---

## 1. il_giardino_dei_numeri — The Number Garden (age 2–4) · 27/40 · POLISH (merge host)

Played: start → wrong taps (ripples) → counted 1/2 → 2/2 celebration (items arc into basket, confetti, Dani surprised) → next basket (1 item). 800×480 OK.

| Obj | Age | Loop | FB | Prog | Vis | Use | Tech |
|---|---|---|---|---|---|---|---|
| 4 | 4 | 3 | 3 | 2 | 3 | 4 | 4 |

- **Obj 4:** correct one-to-one tap counting with spoken numbers. Cardinality ("the last number tells how many") is never stated or shown as a big numeral.
- **Age 4:** huge forgiving hitboxes and nothing to fail. The "0/2" basket label is the only goal cue, and it is text.
- **Loop 3:** tapping to count is pleasant but thin, and rounds of 1 item happen (trivial).
- **FB 3:** good number badges, arcs into the basket and confetti dots. No closing "Two!" moment.
- **Prog 2:** quantities top out at 1–5, rising automatically by basket count. No goal and no end.
- **Vis 3:** clean meadow and on-model Dani PNG, but emoji items in white bubbles read as a second product.
- **Use 4:** pointer plus Space. Targets ≫ 64 px.
- **Tech 4:** fine. Unused `ui.next`/`ui.keep_counting` keys.

**Redesign spec**
- Target: the toddler-to-preschool counting home. Tap-count objects into Dani's basket, hear the total, see the numeral and the ten-frame. One continuous garden "path" absorbs Bosco's 6–10 content.
- Stages (one adaptive ladder, never a menu):
  - S1, 1–3 objects, line layout;
  - S2, 1–5, scattered;
  - S3, 1–5 counted into a 5-frame;
  - S4, 6–10 into a ten-frame (from Bosco);
  - S5, "make N": Dani asks for N and the child drags N items from a pile into the basket (counting out, the harder inverse skill).
- Adaptive rule: 3 clean baskets → next stage. 2 over-/under-counts on make-N → back one stage.
- Cardinality close: after the last tap, items pulse in order; then a big numeral and dot card pop above the basket, and the voice says the total ("Three apples!").
- Remove the "0/N" text. Show N empty basket slots instead (S1–S3 only, hidden in S5).
- Celebration: `character.dani.pose_cheer` hop plus `fx.confetti`; every 5 baskets, a garden plant grows (persistent garden = replay reason).
- Keyboard/controller: arrows move a focus ring between items, Space counts.
- New art:
  - `bg.meadow_day.{sky,far,mid,ground}` (shared);
  - `prop.food.{apple,strawberry,carrot,cherry}`;
  - `prop.nature.{sunflower,mushroom,acorn,leaf}`;
  - `prop.critter.{butterfly,duckling,ladybird}`;
  - `prop.basket.wicker` (open top, 5/10 slot variants);
  - `ui.frame.ten` (2×5 frame with token wells);
  - `ui.card.dots_1..10` are runtime-drawn from one `prop.token.dot`;
  - `fx.confetti`;
  - `prop.garden.growth_{1..4}`.
- Voice (EN): "Count with Dani!", "Give Dani [N] …" ×N (or the reuse pattern "[N]" plus "please!"), "[N] apples!" — 10 numbers × 1 item class with a generic "That's [N]!". Prefer "That's" + count clips.
- Effort M. Risk: the merge must keep Bosco's save data.

## 2. casa_del_dieci — The Ten House (age 5–7) · 26/40 · POLISH

Played: D1 compose. Lit rooms 3 and 5 out of order, pressed OK at 1/5 (no visible error feedback in the captured frame), toggled more rooms. 800×480 OK.

| Obj | Age | Loop | FB | Prog | Vis | Use | Tech |
|---|---|---|---|---|---|---|---|
| 3 | 3 | 3 | 2 | 4 | 3 | 4 | 4 |

- **Obj 3:** the ten-frame house is an excellent manipulative, but the pedagogy leaks:
  - the HUD shows "lit/target" (e.g. "2/5"), so the child can toggle until the numbers match without counting;
  - rooms can be lit in any order, which destroys the 5-and-10 structure that makes ten-frames work;
  - ADD/TAKE-AWAY/MISSING-PART only show `starting_lit` rooms plus an emoji equation string (`🎯 3 💡 + 2 💡 = ❓`), so the operation is never acted out;
  - distractors are random 0–10 instead of near misses.
- **Age 3:** symbolic equations are too abstract for 5, and the equation glyphs are emoji.
- **Loop 3:** lighting windows is satisfying.
- **FB 2:** a wrong OK gives only a 0.35 s button wobble. No "count with me" hint. Generic completion card.
- **Prog 4:** five real level families with attempt-based adaptation.
- **Vis 3:** a charming house. The Listen pill tail overlaps Dani's head. The night palette feels heavy.
- **Use 4:** hybrid with keyboard focus. Big rooms.
- **Tech 4:** fine.

**Redesign spec**
- Target: "Dani's house has 10 windows; make the house show the number." The child physically acts every operation on the frame.
- Filling rule: windows fill left→right, top row first. Tapping any dark window lights the next one; tapping a lit window turns off the last one.
- Remove the lit/target HUD. Keep only the target numeral and its dot card in the roof sign.
- ADD: start with `a` lit; `b` "guest" fireflies fly in and wait at the door; the child taps each one into the next window; then answers. TAKE-AWAY: `b` lights fly out of the chimney (animated) before the answer.
- MISSING-PART: the target numeral stands on the roof; the child lights the missing windows (constructive) instead of picking a numeral.
- Answer choices: always answer ±1 or ±2, shown as numeral plus mini ten-frame, fading the frame out at D4+.
- Wrong answer: Dani `pose_point` at the frame. Windows count aloud one by one ("one, two, three…"), then the child retries.
- Celebration: lights twinkle in sequence, smoke-puff hearts from the chimney, `character.dani.pose_cheer`. The shared completion card (see §Cross) shows the house fully lit.
- Background: keep the night (lit windows need it) but lift contrast; use the shared `bg.night_sky` kit.
- New art:
  - `prop.house.ten_frame` (facade with 10 window wells, 3 window states as `prop.house.window_{dark,lit,flash}`);
  - `prop.firefly.guest` (shared with Luci);
  - `fx.chimney_puff`;
  - `fx.window_twinkle`.
- Voice (EN): "Count the lights with me!", "Some friends are coming in!", "Some lights are going out!", "How many lights now?", "Make [N] lights." (N clips 1–10 already exist as `prompt_compose_N`).
- Effort M. Risk: tests assert the free-toggle model and need updating.

## 3. luci_di_momo — Momo's Lights (age 4–6) · 25/40 · POLISH

Played: Play → 1-firefly flash → choices → wrong/right taps → 6 cycles → completion card ("THE GARDEN IS GLOWING!" with 5 dots). 800×480 OK.

| Obj | Age | Loop | FB | Prog | Vis | Use | Tech |
|---|---|---|---|---|---|---|---|
| 4 | 3 | 3 | 3 | 3 | 3 | 3 | 3 |

- **Obj 4:** this is the only true subitizing activity in the catalogue (a distinct skill). L1 uses canonical arrangements; later levels scatter randomly, which teaches less.
- **Age 3:** answers are numerals only, so the activity silently assumes numeral literacy.
- **Loop 3:** a good flash-and-guess tension, but "TAP TO PLAY" before every round adds friction.
- **FB 3:** the lantern fills and lights; the completion card is generic.
- **Prog 3:** reveal time shrinks 1.6→1.1 s, but the range is capped at 5 with random distractors.
- **Vis 3:** a pleasant night with an on-model Momo PNG, but Momo is tiny and the scene is empty.
- **Use 3:** pointer only, no keyboard focus. Fireflies are ~40 px.
- **Tech 3:** the ready screen allocates alpha surfaces every frame (backlog).

**Redesign spec**
- Target: "Momo's fireflies blink — how many did you see?" A quick-look game that bridges dots → ten-frame → numerals.
- Remove the per-round Play button. Momo shakes the jar (0.8 s anticipation) and fireflies flash automatically. A replay button re-flashes once (and counts as a hint).
- Arrangement ladder:
  - L1, dice patterns 1–5;
  - L2, dice/random 1–5;
  - L3, two-colour groups (2+3) 4–7;
  - L4, firefly ten-frame 6–10, linked to Casa del Dieci.
- Answer cards show numeral + dot pattern at L1–L2 and numeral only at L3+. Distractors are always answer±1.
- Wrong answer: fireflies re-appear and stay. Momo counts them by touching each (`character.momo.pose_point`).
- Celebration: correct fireflies swirl into Momo's lantern. At 5/5 the lantern lights the whole valley, Momo does `pose_cheer` and the garden flowers open.
- Keyboard/controller: left/right between three answer cards, Space selects.
- Perf: pre-bake the glow halos once and blit cached alpha surfaces.
- New art:
  - `prop.firefly.{glow,flash}` (shared with Casa);
  - `prop.lantern.jar_{0..5}` (fill states);
  - `bg.night_sky.{sky,hills}` (shared);
  - `prop.nature.night_flower_{closed,open}`.
- Voice (EN): "Watch closely!", "Look again!", "Let's count them together."
- Effort S.

## 4. festa_delle_rime — Rhyme Festival (age 4–6) · 25/40 · POLISH

Played: D1 2-choice rhyme, several rounds (STAR→CAR, BOAT→GOAT, MOON→SPOON, SNAKE→CAKE). 800×480 OK.

| Obj | Age | Loop | FB | Prog | Vis | Use | Tech |
|---|---|---|---|---|---|---|---|
| 4 | 4 | 3 | 2 | 3 | 3 | 3 | 3 |

- **Obj 4:** a correct audio-first rhyme game. Weaknesses:
  - the EN corpus has only 8 pairs, so words repeat within one set;
  - picture errors: "top" is a yo-yo 🪀 and "lamp" is a light bulb 💡;
  - D4 "same beginning sound" duplicates Officina dei Suoni L1.
- **Age 4:** the child hears every word. On-screen text labels are optional reinforcement.
- **Loop 3:** tapping a lantern, but nothing else happens.
- **FB 2:** a short success gap only. Lanterns don't light or rise, and the completion card is generic.
- **Prog 3:** D1–D4 (2-choice, 3-choice, odd-one-out, alliteration).
- **Vis 3:** a nice lantern-string idea, but the lower half is an empty dark band and Leo is primitive-drawn.
- **Use 3:** pointer only.
- **Tech 3:** newer emoji (🪵 🪭 🪀 🪨) need verifying against the shipped Noto version.

**Redesign spec**
- Target: a pure *listening* festival. Each rhyme found lights a lantern on the festival string, and at the end the sky fills with fireworks.
- Scope:
  - remove the D4 alliteration and hand that skill to Officina dei Suoni;
  - replace it with D4 "rhyme completion": Leo says "I see a cat on a … ?" and the child picks the rhyming object (hat/dog/sun);
  - add D0 for age 3, "same or different?": two words, thumbs-up/thumbs-down cards.
- Corpus: ≥ 16 EN pairs; ban cross-pair accidental rhymes. Each challenge replays target, then choices, with a speaker glow on the current word.
- Feedback:
  - correct: the chosen lantern swings up and joins the string, lit;
  - wrong: that lantern dims and sways, and Leo repeats both words slowly.
- Progress = the visible lantern string (8 slots), not "1/8" text.
- Celebration: `character.leo.pose_cheer` plus `fx.firework` burst over the lit string.
- Cast: replace the drawn owl with `character.leo` PNG variants.
- Keyboard: left/right between lanterns, Space selects, R replays.
- New art:
  - `prop.lantern.paper_{dark,lit}` (shared with Luci style);
  - `prop.festival.string_lights`;
  - `fx.firework`;
  - `bg.night_sky.festival_square`;
  - `prop.vocab.*` rhyme set (cat, hat, moon, spoon, cake, snake, log, frog, bear, chair, boat, goat, star, car, mouse, house, plus 16 new nouns; see §Shared).
- Voice (EN): 16 new noun clips; "Do they rhyme?", "Yes, they rhyme!", "No, they don't rhyme.", plus 8 sentence frames ("I see a cat with a …").
- Effort M.

## 5. labirinto_magico — Magical Labyrinth (age 4–10) · 25/40 · POLISH

Played: arrow-key slides to junctions, several moves; chips (EASY/GALAXY/NEW). 800×480 OK.

| Obj | Age | Loop | FB | Prog | Vis | Use | Tech |
|---|---|---|---|---|---|---|---|
| 3 | 3 | 3 | 2 | 3 | 3 | 4 | 4 |

- **Obj 3:** valid route planning. Slide-to-junction movement is a smart kid-friendly choice. Stars are optional.
- **Age 3:** difficulty and world chips are text ("EASY", "GALAXY", "NEW").
- **Loop 3:** move, collect, exit — solid.
- **FB 2:** the star counter is a plain coin, and the only sound asset is the title clip.
- **Prog 3:** sizes from small to master, but chosen by hand, with no auto-step.
- **Vis 3:** clean tiles. The Tito sprite is not canonical, and the side areas are empty.
- **Use 4:** arrows, pointer direction and d-pad all natural.
- **Tech 4:** fine.

**Redesign spec**
- Target: "Help Tito reach the treasure tent through the hedge maze." Short mazes chained into a map of 9 stops, with a sticker per stop.
- Auto progression: 5×5 (no stars), 7×7 (1 star), 9×9 (3 stars), then 11×9 with a key + door (adds a sub-goal).
- Settings chips become one parent-facing world picker hidden behind a long-press icon, or are removed.
- Pre-readers: a glowing arrow shows the next open directions at each junction for the first two mazes.
- Hint button (firefly) traces 3 cells of the BFS path. Already in the content; surface it as a visible firefly icon.
- Feedback:
  - star pickup: `fx.star_burst` plus a chime;
  - bump into a wall: soft thud and a Tito squash;
  - exit: Tito `pose_cheer` and the tent opens.
- Cast: draw Tito from `character.tito` (canonical PNG scaled to the cell; the facing flip is a mirror of the whole group).
- New art:
  - `bg.maze.{hedge_garden,crystal_cave,night_sky}` (floor/wall tiles as `prop.maze.{wall,floor}_<world>` 64 px);
  - `prop.maze.{key,door,tent_goal}`;
  - `icon.hud.{star,hint}`;
  - `fx.star_burst`.
- Voice (EN): "Help Tito find the way!", "You found a star!", "Find the key first!", "Hooray, Tito made it!"
- Effort M.

## 6. bosco_numeri — Tito's Number Forest (age 3–5, withheld) · 24/40 · CUT-or-MERGE → il_giardino_dei_numeri

Played: count 1 (sun), carousel → 5 ducklings tapped → items hop into the ten-frame, then auto-advance to 6; FIND mode ("WHERE IS NUMBER 5?") 3 cards. 800×480 OK.

| Obj | Age | Loop | FB | Prog | Vis | Use | Tech |
|---|---|---|---|---|---|---|---|
| 3 | 3 | 3 | 3 | 2 | 3 | 3 | 4 |

- **Obj 3:** good 1–10 counting into a ten-frame. FIND cards show a numeral with **one** item icon instead of that quantity, so numeral and quantity never link.
- **Age 3:** fine for 3–5.
- **Loop 3:** tap-count.
- **FB 3:** a nice hop into ten-frame slots.
- **Prog 2:** a free number carousel plus auto-advance, no adaptivity.
- **Vis 3:** a primitive Tito close to the model, plus emoji.
- **Use 3:** carousel buttons are 50 px (< 64 px primary target rule; 39 px at 800×480).
- **Tech 4.**

**Verdict and merge spec.** Bosco duplicates Giardino's loop exactly (same tap-to-count, same scatter-and-fly code shape). Its only unique assets are the 6–10 range, the ten-frame destination and the numeral-find quiz, which become Giardino S3–S5 (see §1). The numeral-find quiz returns inside Giardino as "Which number says how many?" with **quantity cards**. Retire the package after migrating `bosco_numeri_progress` into the Garden save (highest number reached). Cast: Tito can appear in the Garden as a visiting helper (`character.tito.pose_point`) so his math role is not lost. Effort M (merge plus save migration).

## 7. memory_meraviglie — Wonder Match (age 3–8) · 24/40 · POLISH (art REWORK)

Played: 3×2 animals; matched ELEPHANT pair, mismatch LION/DOG flip-back, switched grid to 4×3. 800×480 OK.

| Obj | Age | Loop | FB | Prog | Vis | Use | Tech |
|---|---|---|---|---|---|---|---|
| 3 | 4 | 4 | 3 | 3 | 1 | 3 | 3 |

- **Obj 3:** genuine working-memory practice. Cards are labelled with words, which a pre-reader doesn't need.
- **Age 4:** 2×2 → 6×3 scales well.
- **Loop 4:** classic and fun.
- **FB 3:** sparkles and green borders.
- **Prog 3:** grid size is picked by hand from a "3x2"/"4x3" text chip.
- **Vis 1:** the art is the weakest in the group. "Elephant" is a grey disc with a pink ring; lion and dog are coloured discs with faces; the theme chip has a missing glyph.
- **Use 3:** keyboard focus exists, but the chips are small and text-based.
- **Tech 3:** 167 primitive draw calls per frame.

**Redesign spec**
- Target: "Lilli's sticker match". Flip two cards; each match becomes a sticker in Lilli's album page, so a finished board = a completed scene (for example a farm), giving a reason to replay all themes.
- Auto difficulty: 2×2 → 3×2 → 4×3 → 4×4 (two clean boards up, one long board down). The 6×3 "giant" goes to a parent-only option.
- Themes = 4 albums (farm, sea, food, vehicles) × 8 subjects.
- Remove word labels from card faces. Speak the noun on flip instead (reuse the `prop.vocab` clips).
- Mismatch: cards wiggle and flip back after 1.0 s (no penalty, no move counter shown to the child).
- Celebration: the album page fills, Lilli `pose_cheer`, `fx.sticker_pop`.
- Perf: pre-render 32 card faces once from PNG. No per-frame primitives.
- New art:
  - `ui.card.memory_back` (Greia star back);
  - `ui.card.memory_face` (blank);
  - 32 `prop.vocab.*` subjects (shared set: animals 8, food 8, vehicles 8, sea 8);
  - `prop.album.page_{farm,sea,food,vehicles}` (scene with 8 sticker wells);
  - `fx.sticker_pop`.
- Voice: noun clips from the shared vocabulary set; "Find two the same!", "A match!"
- Effort M (art volume is the cost; the gameplay code is small).

## 8. mondo_contrari — Opposites World (age 3+) · 22/40 · REWORK

Played: all 5 tabs and toggles (UP/DOWN balloon, BIG/SMALL bubble, INSIDE/OUTSIDE box, OPEN/CLOSED window, FAST/SLOW rabbit vs snail). 800×480 OK.

| Obj | Age | Loop | FB | Prog | Vis | Use | Tech |
|---|---|---|---|---|---|---|---|
| 3 | 4 | 2 | 3 | 1 | 2 | 3 | 4 |

- **Obj 3:** five correct concept pairs with spoken words. Pure toggling, though, so there is no check of understanding.
- **Age 4:** trivially operable.
- **Loop 2:** novelty is gone in about a minute.
- **FB 3:** motion, sparkles, speed lines and the spoken word.
- **Prog 1:** none.
- **Vis 2:**
  - Flash appears as a floating rabbit head with no body or shirt;
  - the BIG/SMALL robot is a generic teal robot, not Dani;
  - the UP balloon is drawn under the tab bar (clipped);
  - everything is primitive art.
- **Use 3:** the tab labels are text and small (backlog: 13–15 px in IT).
- **Tech 4.**

**Redesign spec**
- Target: "Flash's Opposite Game". Explore a pair, then Flash asks: "Make the balloon go UP!", "Which one is SLOW?"
- Two modes in one flow per pair:
  1. explore toggle (3 taps);
  2. challenge, alternating "make it X" (act) and "find the X one" (2 pictures).
- Pairs: 5 → 10, adding hot/cold, full/empty, day/night, wet/dry and loud/quiet. Unlock in order, shown as a picture road of pair icons (no text tabs).
- Tabs become 64 px picture icons. Text appears only as a word caption under the big scene after the voice.
- Feedback:
  - correct: Flash `pose_cheer` and a star on that pair's road stop;
  - wrong: the scene demonstrates the asked state while the word is repeated.
- Cast: Flash and Dani from canonical PNGs.
- New art:
  - `bg.meadow_day.*` (shared);
  - `prop.opposites.{balloon,bubble,gift_box,window_bird,snail,cup_hot,cup_cold,glass_full,glass_empty,umbrella_wet,drum_loud}`;
  - `icon.hud.pair_<id>` ×10 (64/96 px);
  - `fx.speedlines`, `fx.steam`.
- Voice (EN): 10 new words (hot, cold, full, empty, day, night, wet, dry, loud, quiet); "Make it …!", "Which one is …?" (2 frames × 20 words reuse the word clips).
- Effort M.

## 9. bottega_delle_misure — The Measurement Workshop (age 5–7) · 21/40 · REWORK

Played: D1 compare (SHORTEST/TALLEST), right and wrong taps, progress 1→3/5. Measure/shelf modes reviewed in source. 800×480 OK.

| Obj | Age | Loop | FB | Prog | Vis | Use | Tech |
|---|---|---|---|---|---|---|---|
| 3 | 3 | 2 | 2 | 3 | 2 | 3 | 3 |

- **Obj 3:**
  - compare and order are correct;
  - the MEASURE mode draws the rail already filled with blocks **numbered 1…N**, so "measuring" is reading the last label;
  - the SHELF mode is the same screen with a different prompt;
  - the core measurement skill (iterating a unit end-to-end without gaps or overlaps) is never practised;
  - `add_rail_block`/`remove_rail_block` are dead code.
- **Age 3:** prompts are voiced, but answer buttons are "4 🟧" numeral+emoji.
- **Loop 2:** tap the bigger gift box.
- **FB 2:** a 12 px hop and a wobble; taps during the 0.35 s wobble are dropped.
- **Prog 3:** 5 levels with adaptation, but L3 and L4 are duplicates.
- **Vis 2:** a dark empty workshop; the lower 45 % of the screen is a blank brown floor; primitive parcels. Dani is on-model.
- **Use 3:** pointer only.
- **Tech 3:** dead model state; emoji in the answer label.

**Redesign spec**
- Target: "Dani's Parcel Workshop". Customers' parcels must be compared, lined up and *measured with wooden blocks* before they fit on the delivery shelf, and then a toy truck drives off.
- D1 compare (2 parcels, the bigger difference first, then closer). D2 order 3 (drag into slots).
- D3 measure by laying blocks: the child drags blocks from a crate under the parcel; blocks snap end-to-end; overhang/gap glows; then the child taps the count (choices answer±1, no numbers on blocks).
- D4 "which parcel fits the shelf gap?": the gap is shown as N blocks long and the child picks among 3 parcels (indirect comparison, a distinct skill).
- D5: measure with two different units (blocks vs paperclips) to show that the unit matters (age 6–7 stretch).
- Use the full screen: the parcel conveyor in the middle, the crate of blocks lower left, Dani at the shelf on the right.
- Feedback:
  - correct: the parcel is wrapped with a bow and slides to the truck;
  - wrong: Dani `pose_point` at the gap/overhang;
  - 5 parcels: the truck drives off with a horn, then the cast completion.
- New art:
  - `bg.indoor_room.{wall_workshop,floor_wood}` (shared);
  - `prop.workshop.{conveyor,shelf_gap,crate_blocks,toy_truck}`;
  - `prop.measure.{unit_block,paperclip}`;
  - `prop.parcel.{box_short,box_tall,box_long}` (9-slice friendly, 3 colours);
  - `fx.bow_wrap`.
- Voice (EN): "Line up the blocks under the parcel.", "No gaps!", "How many blocks long?", "Which parcel fits?", "Off it goes!"
- Effort M. Risk: drag snapping needs keyboard/controller parity (arrows choose the crate/slot, Space places).

## 10. alfabeto_leo — Leo's Alphabet (age 2–4, withheld) · 20/40 · RETHINK

Played: letter strip (A→B), card BOAT; FIND mode ("WHERE IS L?" + lion picture, choices L/Q/S). 800×480 OK.

| Obj | Age | Loop | FB | Prog | Vis | Use | Tech |
|---|---|---|---|---|---|---|---|
| 2 | 3 | 2 | 2 | 1 | 3 | 3 | 4 |

- **Obj 2:**
  - EN examples include sound traps: X "Xylophone" (/z/), O "Owl", Y "Yacht", K "Kite" is fine, C "Cat" is fine;
  - the clips say "X as Xylophone", teaching names, not sounds, without saying so;
  - the manifest claims `fine_motor`, but there is no tracing.
- **Age 3:** explore works for age 3; FIND needs letter knowledge. The 2–4 band is too young for the quiz.
- **Loop 2:** browse cards.
- **FB 2:** minimal.
- **Prog 1:** a 26-letter menu, no ladder.
- **Vis 3:** a cozy room with an owl close to Leo (primitive), plus emoji pictures.
- **Use 3:** strip chips ≈ 60 px.
- **Tech 4.**

**Rethink spec: "Leo's Letter Garden", the letter-shape and letter-name step of the literacy ladder (age 3–5)**
- Loop per letter: hear and see the letter → **trace it with a finger** (3 stroke arrows, generous tolerance) → the letter "blooms" into its picture → stamp it into Leo's alphabet book.
- Order: the child's name initials first (profile name, if any), then high-frequency letters (S A T P I N M D…), never A→Z.
- Show upper and lower case together.
- Example words must start with the letter's common short sound in each locale (replace Xylophone→"fox" ending for X, O→octopus, Y→yo-yo, E→egg). Clips state name and sound: "This is S. S says sss, like sun."
- FIND mode moves here as "Which one is S?". It unlocks only after a letter has been traced twice and uses 2→3 choices.
- Progress: the alphabet book fills, one page per letter; at 26 pages Leo does `pose_cheer` and reads the book aloud.
- Input: trace by pointer/touch; keyboard/controller fallback = press Space as an animated dot travels the stroke ("follow the dot"), so the Activity is not pointer-locked.
- New art:
  - `prop.vocab.*` 26 letter-example subjects (shared);
  - `ui.tile.letter` (blank; glyph drawn at runtime);
  - `prop.book.alphabet_{open,page}`;
  - `fx.bloom`;
  - `icon.hud.trace`.
- Voice (EN): 26 × "This is [L]. [L] says [sound], like [word]." (replacing letter_*); "Trace it with your finger!", "Beautiful!"
- Effort M. Risk: phoneme clips need native review (owner rule: prerecorded only).

## 11. foresta_parole — The Word Forest (age 5–8) · 19/40 · CUT-or-MERGE → officina_dei_suoni

Played: target "A — APPLE", moving letter orbs, wrong taps (letter tag feedback); orbs drift and overlap. 800×480 OK.

| Obj | Age | Loop | FB | Prog | Vis | Use | Tech |
|---|---|---|---|---|---|---|---|
| 3 | 2 | 3 | 2 | 2 | 2 | 2 | 3 |

- **Obj 3:** "find letter A as in Apple" is letter recognition with a word anchor. This is the same objective as Alfabeto FIND and Officina L2.
- **Age 2:** moving targets for 5-year-olds with a pointer; orbs overlap and occlude each other (A under H in the capture).
- **Loop 3:** catching has game energy.
- **FB 2:** "★ 0 🏆 0" score chips.
- **Prog 2:** a linear letter cycle.
- **Vis 2:** a dark empty hill.
- **Use 2:** no keyboard; moving small targets.
- **Tech 3.**

**Verdict and merge spec.** Its one distinctive ingredient, a light *catch* mechanic, is worth keeping as the reward round of Officina dei Suoni: after each 3-word set, Leo releases sound-bubbles for 15 s and the child pops every bubble that **starts with /s/** (picture bubbles, not letters, at D1; letter bubbles at D3). Rules:
- bubbles never overlap (separation solver);
- they move slowly (≤ 40 px/s at D1);
- they are ≥ 72 px;
- keyboard/controller gets a "next bubble" focus cycle.

Retire the stand-alone package and migrate stars into Officina. New art: `prop.bubble.{plain,pop}` and `fx.bubble_pop`. Effort S.

## 12. sillabe_magiche — Magic Syllables (age 5–8, withheld) · 19/40 · RETHINK

Played: Syllabary (B: BA BE BI BO BU), Catch ("LISTEN AND TOUCH: MI", overlapping bubbles), Words (BABY: 1st/2nd syllable slots + PE FE BA BY). 800×480 OK.

| Obj | Age | Loop | FB | Prog | Vis | Use | Tech |
|---|---|---|---|---|---|---|---|
| 2 | 2 | 3 | 2 | 2 | 2 | 3 | 3 |

- **Obj 2 (EN):**
  - the CV syllabary is the Italian *metodo sillabico* (valuable in IT, incoherent in EN: "BI", "BU");
  - the consonant column is hardwired to `CONSONANTS_IT`;
  - EN word chunks (RAB/BIT, ROCK/ET) don't follow one rule;
  - Catch prints the target syllable, turning listening into visual matching;
  - two "MI" bubbles appeared at once.
- **Age 2:** mode tabs, prompts and slot labels are all text. The "1ST SYLLABLE" label overflows its slot.
- **Loop 3:** the builder is decent.
- **FB 2.**
- **Prog 2:** free modes, no ladder.
- **Vis 2:** the purple owl with pink glasses is off-model Leo; a desktop-style tab bar.
- **Use 3:** big tiles.
- **Tech 3.**

**Rethink spec**
- **IT build: "Il Trenino delle Sillabe"**, the first decoding step for 5–6-year-olds (ladder step 4).
  - A loco carries a consonant; vowel wagons couple on and the train "reads" the syllable aloud as it passes a station.
  - Then 2-wagon words (PA+LLA → palla) are built by dragging wagons.
  - Ladder: open syllables with M/P/L/T first; then all consonants; then 3-syllable words; then CVC-final (non-open) syllables.
- **EN build:** do not ship the CV syllabary. Replace it with the new "Leo's Sound Blender" (§Cross gap #3), which covers syllable clapping and blending orally. Keep the train art for both.
- Catch mode: audio only. Never print the target; a speaker icon pulses.
- Cast: `character.leo` canonical PNGs (remove the purple owl).
- All tabs become picture icons (train / bubbles / word).
- New art:
  - `prop.train.{loco,wagon_blank,station}` (glyphs drawn at runtime on `ui.tile.letter`);
  - `bg.meadow_day.*` (shared);
  - `prop.vocab.*` (shared nouns for 2-syllable IT words).
- Voice (IT, owner approval): syllable clips exist (91 `syl_*`); new word-blend lines "PA… LLA… palla!" ×20.
- Effort L. Risk: needs a native IT literacy educator review.

## 13. la_discesa_della_biglia — The Marble's Descent (age 4–7) · 15/40 · RETHINK

Played: DROP with no tools (marble falls and is drawn *outside* the playfield below the frame; "MISSED! AGAIN!" text box); placed 2 slopes + bumper + spring, DROP → the marble lands on a flat "slope" and **stays there forever**. The timer ran 1.5 → 7.8 s, DROP and CLEAR are disabled while running, and Home is the only exit. 800×480 OK.

| Obj | Age | Loop | FB | Prog | Vis | Use | Tech |
|---|---|---|---|---|---|---|---|
| 3 | 2 | 2 | 1 | 2 | 1 | 2 | 2 |

- **Obj 3:** the cause-and-effect physics idea is good.
- **Age 2:**
  - text-only win/miss messages;
  - abstract tool icons (the slope icon is tilted, but placed slopes are flat);
  - no demonstration.
- **Loop 2:** see the soft-lock above.
- **FB 1:** no voice except the title, and the marble vanishes.
- **Prog 2:** 3 authored levels.
- **Vis 1:** a blank white playfield.
- **Use 2:** you can only tap-to-place. You cannot move, rotate or remove a single tool; the hybrid profile has no keyboard placement.
- **Tech 2:** real bugs:
  - `PlacedTool.angle` is always 0, so slopes are flat;
  - the engine documents a `"settled"` event, but nothing emits or handles it, so a resting marble soft-locks the run;
  - the marble renders outside the playfield on a miss.

**Rethink spec: "Tito's Marble Run" (age 4–6)**
- Each level is a picture puzzle: a marble chute top-left, a basket somewhere, and **2–4 fixed ghost slots** where pieces can go. The child drags pieces from a tray into slots: a ramp with a left/right tilt toggle on tap, a bouncer, a fan, a spring. Then they pull the lever.
- Slots make every level solvable and make keyboard/controller parity easy (arrows cycle slots, Space cycles the piece).
- Physics runs at most 8 s and ends on: basket, out-of-bounds, or speed < threshold for 0.6 s ("settled" → a gentle "Oops, it stopped!"). The run *always* returns to edit mode, keeping pieces.
- Before the drop, a dotted preview of the first 0.5 s of motion at D1 only, as scaffolding.
- Levels: 12 hand-authored, 3 per world (garden, kitchen, playroom, space), from 1 slot to 4. Stars for a basket hit with ≤ N pieces.
- Feedback:
  - pieces clack on contact (SFX per piece);
  - basket hit: confetti, Tito `pose_cheer`, the basket wiggles;
  - miss: the marble rolls off-screen into a visible "lost marbles" jar and auto-returns.
- New art:
  - `bg.playroom.{wall,floor}` and `bg.kitchen.*` (2 new kits; the garden kit is shared);
  - `prop.marble_run.{chute,lever,basket,ramp,bouncer,fan,spring,slot_ghost,marble}`;
  - `fx.{confetti,dust_puff}`;
  - `prop.jar.lost_marbles`.
- Voice (EN): "Put the pieces in the shining spots!", "Pull the lever!", "Oops, it stopped!", "Almost! Try moving a piece.", "In the basket!"
- Effort L. Risk: it replaces the free-placement assumptions in the existing Activity tests; physics needs tuning on the Acer at 4 sub-steps.

---

## Cross-Activity findings

### A. Duplicates and overlaps

**Numbers.** The family has 6 in my set plus treno_numeri and stelle_incantate outside it.

| Skill | Today | Recommendation |
|---|---|---|
| 1:1 counting 1–5 | Giardino, Bosco, (Treno cardinality) | **One home: Giardino**, absorbing Bosco's 6–10 ten-frame and numeral-find. Verify Treno is about *matching quantity to numeral* (wagons), not more counting, before release. |
| Subitizing | Luci only | Keep. It becomes the bridge to ten-frames (L4). |
| Part-whole within 10 | Casa (D1–D5); Bosco's ten-frame | Casa owns it. Make the operations enacted, not symbolic. |
| Numeral recognition | Bosco FIND, Luci answers, Casa answers | Teach numeral↔quantity jointly (numeral + dot cards) in Giardino and Luci; drop the numeral-only quiz. |
| Measurement/comparison | Bottega only | Keep, but its D3/D4 must stop being "count the numbered blocks". |
| Number order | Stelle incantate | Out of my scope; it's the only sequencing item. |

Curriculum path for numbers:
- Giardino S1–S3 (age 2–4);
- Luci L1–L2 + Giardino S4 (age 4);
- Luci L3–L4 + Casa D1–D2 (age 5);
- Casa D3–D5 + Bottega (age 5–7).

The Parent "age + easier" preset already supports this if the manifests' `recommended_age_*` match it: Giardino 2–5, Luci 4–6, Casa 5–7, Bottega 5–7.

**Literacy.** "Letter that goes with a picture" is taught **four times** and oral blending **zero** times.

| Skill | Today | Recommendation |
|---|---|---|
| Rhyme | Festa D1–D3 | Keep in Festa. |
| Same beginning sound (alliteration) | Festa D4 **and** Officina L1 | Officina only; remove Festa D4. |
| Letter recognition from a picture | Alfabeto FIND, Foresta catch, Officina L2 | Alfabeto owns letter names/shapes (+ tracing). Officina owns letter-sound. Foresta merges into Officina as its catch reward round. |
| Syllables | Sillabe (IT method shipped in EN too) | IT: syllable train (decoding). EN: syllable clapping inside the new Sound Blender. |
| Blending → word | Officina L3 (letters), Sillabe builder | Add an oral, picture-only blending step (new Activity #3) before letter-based building. |
| Concepts/opposites | Mondo | Keep as oral-vocabulary concepts (it's language, not logic). |

Literacy ladder:
1. Festa (listen to rhyme, age 3–5);
2. Alfabeto "Letter Garden" (shapes/names/tracing, age 3–5);
3. Officina (first sound, letter-sound, with the catch round, age 4–6);
4. Sound Blender / Sillabe-IT (blend, age 5–6);
5. Officina L3 build-a-word;
6. Writing / Posta di Leo (authoring).

**Logic.** Memory, Labirinto and Biglia are genuinely distinct (memory / route planning / cause-effect). No merge needed. The overlap there is only visual: three different HUD chip styles and text setting chips.

### B. Curriculum gaps for ages 3–6 (new Activity proposals, max 3)

1. **Dani's Pattern Parade** (math/logic, age 3–6). Patterns are Dani's canonical domain and are entirely missing.
   - Loop: a parade of animals or instruments marches in an AB / AAB / ABB / ABC pattern; the child fills the gap, then extends the pattern, then *creates* a pattern that the band plays as a rhythm.
   - It bridges math and the Music singleton (helps the `orchestra_animali` gap).
   - Art: `prop.parade.{drum,flag,hat}`, cast `pose_cheer`. Voice: ~10 lines.
2. **Tito's Sorting Baskets** (math/logic, age 3–5): classification plus more/fewer/same.
   - Loop: Tito's backpack spills; sort items by colour → kind → size (2 then 3 baskets; the rule is spoken and pictured on the basket); then compare two baskets: "Which has more?" (match items one-to-one with strings).
   - Fills sorting and comparison-of-quantity, which no Activity teaches directly.
   - Reuses the `prop.vocab` / food / nature sets.
3. **Leo's Sound Blender** (literacy, age 4–6). Oral blending and segmentation, picture-only, no letters.
   - Leo says a word in pieces (syl-la-ble → onset-rime "c…at" → phonemes "c-a-t"). The child taps the matching picture of 3, then "chops" a picture word into claps or beads.
   - It is the strongest pre-reading predictor, it is fully pre-reader-compatible, and it replaces the EN syllabary in Sillabe.
   - Voice-heavy (≈ 60 segmented clips per locale), so it needs owner voice approval.

### C. Shared assets to author once (SVG → PNG by `rsvg-convert`, per `GREIA_SVG_AUTHORING_RULES.md`)

| Semantic IDs | Kind | Consumers here |
|---|---|---|
| `bg.meadow_day.{sky,far,mid,ground}` | scene layers 1024×600 | giardino(+bosco), mondo, sillabe, labirinto (hedge world), biglia (garden), Pattern Parade, Sorting |
| `bg.night_sky.{sky,hills,stars}` + `bg.night_sky.festival_square` | scene layers | luci, casa, festa, labirinto (night world) |
| `bg.indoor_room.{wall_workshop,wall_cozy,floor_wood}`, `bg.playroom.*`, `bg.kitchen.*` | scene layers | bottega, alfabeto, memory album, biglia |
| `prop.vocab.*` (~64 nouns: rhyme set 32, alphabet examples 26, memory/album extras) | prop 256 | festa, alfabeto, officina(+foresta), sillabe, memory, Sound Blender, Sorting. **This single set removes most content emoji in literacy.** |
| `prop.food.*` (12), `prop.nature.*` (10), `prop.critter.{butterfly,duckling,ladybird,firefly}` | prop 256 | giardino, luci, casa, memory, Sorting |
| `prop.lantern.{paper_dark,paper_lit,jar_0..5}`, `prop.firefly.{glow,flash,guest}` | prop / FX | luci, festa, casa |
| `prop.basket.wicker` (slot variants), `ui.frame.ten`, `prop.token.dot` | prop / UI | giardino, casa, luci, Sorting |
| `ui.tile.letter` / `ui.tile.number` (blank; glyph at runtime), `ui.card.memory_{back,face}` | UI | alfabeto, sillabe, officina, casa, luci, memory |
| `fx.{confetti,sparkle,star_burst,firework,bubble_pop,sticker_pop,bloom,dust_puff,check_pop}` | FX 128 | all 13 |
| `icon.hud.{listen,replay,hint,star,trace,pair_*}` | HUD 96 | all (replace 🔊 ✨ 🎯 💡 ❓ 🟧 HUD emoji) |
| `character.<id>.pose_think` and `pose_wave` (new, 6 × 2) | cast | wrong-answer coaching (think) and Activity intro (wave) in every Activity here |
| **Shared completion scene:** `ui.completion.{stage,ribbon}` + cast `pose_cheer` + `fx.confetti` + 1 voice line per Activity | UI | replaces the text-only `PygameCompletionScreen` card used by 16 Activities (bottega, casa, festa, labirinto, luci, memory, officina, …) |

### D. Top cross-cutting rules for the main agent

1. **Merge before polishing.**
   - Bosco → Giardino;
   - Foresta → Officina catch round;
   - Festa alliteration → Officina;
   - Sillabe-EN → the new Sound Blender.

   This takes 13 + Officina from 14 overlapping cards to 11 distinct learning loops, forming two visible ladders.
2. **Make operations enacted, not symbolic.** Casa (+/− via fireflies entering and leaving), Bottega (laying unit blocks), Luci (dot cards with numerals). Distractors must be ±1/±2 everywhere. Never show a "lit/target" counter that gives the answer away.
3. **One feedback grammar for every Activity in this group:**
   - correct = cast `pose_cheer` + FX + short voice;
   - wrong = cast `pose_think`/`pose_point` + a demonstration of the right idea + an unlimited retry;
   - completion = the shared cast completion scene.

   Emoji as content and text-only setting chips go (settings move to the Parent app or a long-press). This is mostly shared-kit and shared-asset work, not per-Activity work.
