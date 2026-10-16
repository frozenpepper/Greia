# Voice lines requested by the 2026-10 Activity reworks (for owner review)

**Date:** 2026-10-16 · **Status:** REQUEST LIST — **nothing in this file has been generated, recorded or accepted.**
**Owner:** four-language rollout ([PLAN.md](./PLAN.md), [PROGRESS.md](./PROGRESS.md)); cue/voice policy in [LOCAL_AGENT_VOICE_PRODUCTION.md](./LOCAL_AGENT_VOICE_PRODUCTION.md); executable recording order in [LOCAL_AGENT_ALL_APP_VOICE_RECORDING_ORDER.md](./LOCAL_AGENT_ALL_APP_VOICE_RECORDING_ORDER.md). Product context: P7 in `docs/plans/2026-10-07_CREATIONS_LIBRARY_AND_ACTIVITY_RELEASE/P7_ACTIVITY_QUALITY_PROGRAM.md` (foundation F6).

## What this is

The 45 reworked Activities (commits `39733dd9..HEAD`) were designed word-free and voice-first, and every Activity falls back gracefully (selected language, base language, English, silence) when a line is missing. The lines below are the **spoken lines the reworks would like to have**. Each row is a request: the owner reviews the text, strikes or edits lines, and approves. Only after approval may the zero-new-spend local Greia Voice Studio / registered local Voice Engine provider produce **candidates** (never auto-accepted; a person must listen, per the voice-production rules). Paid cloud or model installation still needs separate cost approval. ES/FR are staged and are not requested here except where a defect is noted.

Lines marked `proposed` or "to be authored" were drafted from the rework intent, not from a shipped locale bundle; texts taken verbatim from the reworks' backlog are unmarked. Lines marked `existing` in the "clip" columns already have an approved recording; they are listed only so the review sees the complete set.

## File and id conventions (proposed — final ids follow each Activity's `locales/<locale>.json` `audio` map)

| Kind | Semantic id | File |
|---|---|---|
| Shared noun names (vocabulary bank, language-neutral concept id) | `<noun_id>` e.g. `apple` | `assets/audio/vocab/v1/<locale>/<noun_id>.wav` (+ `.receipt.json`); resolver `shared_vocab_audio_path` (`00d303a5`). The Italian clip for `apple` says "mela". |
| Shared numbers 0–25 | `<n>` | `assets/audio/numbers/v1/<locale>/<n>.wav` via a future `greia_platform.localization.shared_number_audio_path(project_root, n, locale)` (this resolver name is already probed by `pasticceria_magica`; owner confirms folder name and implementation lands with the clips) |
| Shared colour names, direction/position words, shape names | `<noun_id>`-style concept ids | same vocabulary bank (`assets/audio/vocab/v1/<locale>/<concept_id>.wav`): `colour_pink`, `pos_behind`, `shape_circle`, ... so Activities need no per-Activity copy |
| Cast voice (Leo, Tito, Dani, Momo, Lilli, Flash) general reactions | cue id e.g. `celebrate.success` | shared character library `assets/audio/characters/shared/v0.2/<speaker>/<locale>/` (not requested here) |
| Per-Activity lines | `<cue_id>` (proposed snake_case below) | `activities/<activity_id>/assets/audio/<locale>/<cue_id>.wav`, registered in `locales/<locale>.json` `audio` with a `caption_key` where text is purposeful |

Rules for every line: simple, child-sized, warm; no device words (mouse/keyboard/click); no answer-revealing wording (prompts never name the correct choice). Child-facing text is shown in capitals by the platform case policy; the recording text below is the natural-case spoken line.

---

## A. Shared sets (record once, used by many Activities)

### A1. Numbers 0–25 (EN / IT)

Used by: Giardino (6–10, "That is N!"), Treno (1–10), Luci (6–10), Stelle (1–20), Bosco (0), Pasticceria (1–10), Nanna (1–5), Delfino (0–25), Casa and others.

| n | EN | IT | file (proposed) |
|---|---|---|---|
| 0 | Zero! | Zero! | `<locale>/0.wav` |
| 1 | One! | Uno! | `<locale>/1.wav` |
| 2 | Two! | Due! | `<locale>/2.wav` |
| 3 | Three! | Tre! | `<locale>/3.wav` |
| 4 | Four! | Quattro! | `<locale>/4.wav` |
| 5 | Five! | Cinque! | `<locale>/5.wav` |
| 6 | Six! | Sei! | `<locale>/6.wav` |
| 7 | Seven! | Sette! | `<locale>/7.wav` |
| 8 | Eight! | Otto! | `<locale>/8.wav` |
| 9 | Nine! | Nove! | `<locale>/9.wav` |
| 10 | Ten! | Dieci! | `<locale>/10.wav` |
| 11 | Eleven! | Undici! | `<locale>/11.wav` |
| 12 | Twelve! | Dodici! | `<locale>/12.wav` |
| 13 | Thirteen! | Tredici! | `<locale>/13.wav` |
| 14 | Fourteen! | Quattordici! | `<locale>/14.wav` |
| 15 | Fifteen! | Quindici! | `<locale>/15.wav` |
| 16 | Sixteen! | Sedici! | `<locale>/16.wav` |
| 17 | Seventeen! | Diciassette! | `<locale>/17.wav` |
| 18 | Eighteen! | Diciotto! | `<locale>/18.wav` |
| 19 | Nineteen! | Diciannove! | `<locale>/19.wav` |
| 20 | Twenty! | Venti! | `<locale>/20.wav` |
| 21 | Twenty-one! | Ventuno! | `<locale>/21.wav` |
| 22 | Twenty-two! | Ventidue! | `<locale>/22.wav` |
| 23 | Twenty-three! | Ventitré! | `<locale>/23.wav` |
| 24 | Twenty-four! | Ventiquattro! | `<locale>/24.wav` |
| 25 | Twenty-five! | Venticinque! | `<locale>/25.wav` |

Optional carrier phrase for the same set: "That's N!" / "Sono N!" (Giardino) — request only if the owner wants it; otherwise the bare number is reused.

### A2. Colour names

Used by: Nanna (six quilt colours), My Greia (room colour line + 8 colours; final id list to be taken from the Activity's palette at recording time).

| concept id | EN | IT |
|---|---|---|
| `colour_pink` | Pink | Rosa |
| `colour_yellow` | Yellow | Giallo |
| `colour_green` | Green | Verde |
| `colour_blue` | Blue | Blu |
| `colour_purple` | Purple | Viola |
| `colour_orange` | Orange | Arancione |
| `colour_red` | Red | Rosso |
| `colour_brown` | Brown | Marrone |
| `colour_white` | White | Bianco |
| `colour_black` | Black | Nero |

### A3. Direction and position words

Used by: Nascondino (positions), Mondo (existing concept words), Specchi, Torre, Bottega, Delfino (wordless steer hints stay wordless).

| concept id | EN | IT |
|---|---|---|
| `pos_behind` | Behind | Dietro |
| `pos_under` | Under | Sotto |
| `pos_in` | In | Dentro |
| `pos_on` | On | Sopra |
| `pos_next_to` | Next to | Accanto |
| `pos_in_front` | In front of | Davanti |
| `pos_up` / `pos_down` | Up / Down | Su / Giù |
| `pos_left` / `pos_right` | Left / Right | Sinistra / Destra |
| `pos_where_is` | Where is the…? | Dov'è…? |

### A4. Shape names

Used by: Shape Garden (8), Torre (6 block kinds), Specchi (rhombus, heart).

| concept id | EN | IT |
|---|---|---|
| `shape_circle` | Circle | Cerchio |
| `shape_square` | Square | Quadrato |
| `shape_triangle` | Triangle | Triangolo |
| `shape_rectangle` | Rectangle | Rettangolo |
| `shape_star` | Star | Stella |
| `shape_heart` | Heart | Cuore |
| `shape_oval` | Oval | Ovale |
| `shape_diamond` | Diamond (rhombus) | Rombo |
| `shape_half_circle` | Half circle | Semicerchio |
| `shape_arch` | Arch | Arco |
| `shape_cylinder` | Cylinder | Cilindro |

(The last three are also listed as nouns below; record once under whichever id the owner prefers.)

### A5. Noun names → vocabulary bank (`assets/audio/vocab/v1/<locale>/<noun_id>.wav`)

Used by: Memory (40 album pictures), Nascondino, Cucciolo (name tags), Clinica (patients), Torre (build names), Pasticceria (toppings), Orchestra (instruments), Stagioni, Serra (plants) and every later naming game. The bank today holds 21 EN and 17 IT approved clips; rows marked `REQUEST` have no clip in that language yet (silent or English fallback today). `moon` is spoken "Luna" in Italian and `puppy`/`kitten` etc. keep language-neutral ids.


**Animals and pets**

| noun_id | EN | IT | EN clip in bank | IT clip in bank |
|---|---|---|---|---|
| `cat` | Cat | Gatto | yes | yes |
| `dog` | Dog | Cane | REQUEST | yes |
| `lion` | Lion | Leone | yes | REQUEST |
| `elephant` | Elephant | Elefante | yes | yes |
| `pig` | Pig | Maialino | yes | REQUEST |
| `frog` | Frog | Rana | yes | yes |
| `penguin` | Penguin | Pinguino | yes | REQUEST |
| `mouse` | Mouse | Topo | yes | yes |
| `puppy` | Puppy | Cagnolino | REQUEST | REQUEST |
| `kitten` | Kitten | Gattino | REQUEST | REQUEST |
| `guinea_pig` | Guinea pig | Porcellino d'India | REQUEST | REQUEST |

**Woodland friends**

| noun_id | EN | IT | EN clip in bank | IT clip in bank |
|---|---|---|---|---|
| `hedgehog` | Hedgehog | Riccio | REQUEST | REQUEST |
| `squirrel` | Squirrel | Scoiattolo | REQUEST | REQUEST |
| `bear` | Bear | Orso | REQUEST | REQUEST |
| `deer` | Deer | Cerbiatto | REQUEST | REQUEST |
| `duck` | Duck | Papera | REQUEST | REQUEST |
| `snail` | Snail | Lumaca | REQUEST | REQUEST |
| `butterfly` | Butterfly | Farfalla | REQUEST | REQUEST |

**Sea creatures**

| noun_id | EN | IT | EN clip in bank | IT clip in bank |
|---|---|---|---|---|
| `fish` | Fish | Pesce | yes | yes |
| `turtle` | Turtle | Tartaruga | yes | REQUEST |
| `octopus` | Octopus | Polpo | REQUEST | REQUEST |
| `jellyfish` | Jellyfish | Medusa | REQUEST | REQUEST |
| `seahorse` | Seahorse | Cavalluccio marino | REQUEST | REQUEST |
| `crab` | Crab | Granchio | REQUEST | REQUEST |
| `starfish` | Starfish | Stella marina | REQUEST | REQUEST |
| `dolphin` | Dolphin | Delfino | yes | yes |

**Food and toppings**

| noun_id | EN | IT | EN clip in bank | IT clip in bank |
|---|---|---|---|---|
| `apple` | Apple | Mela | yes | yes |
| `banana` | Banana | Banana | REQUEST | REQUEST |
| `carrot` | Carrot | Carota | REQUEST | REQUEST |
| `grapes` | Grapes | Uva | REQUEST | yes |
| `pear` | Pear | Pera | yes | yes |
| `cake` | Cake | Torta | yes | yes |
| `pizza` | Pizza | Pizza | yes | yes |
| `ice_cream` | Ice cream | Gelato | REQUEST | REQUEST |
| `strawberry` | Strawberry | Fragola | REQUEST | REQUEST |
| `blueberry` | Blueberry | Mirtillo | REQUEST | REQUEST |
| `cherry` | Cherry | Ciliegia | REQUEST | REQUEST |
| `cookie` | Cookie | Biscotto | REQUEST | REQUEST |
| `chocolate` | Chocolate | Cioccolato | REQUEST | REQUEST |

**Vehicles and things**

| noun_id | EN | IT | EN clip in bank | IT clip in bank |
|---|---|---|---|---|
| `car` | Car | Auto | yes | REQUEST |
| `bus` | Bus | Autobus | REQUEST | REQUEST |
| `train` | Train | Treno | REQUEST | REQUEST |
| `boat` | Boat | Barca | yes | yes |
| `plane` | Plane | Aereo | REQUEST | REQUEST |
| `rocket` | Rocket | Razzo | yes | REQUEST |
| `bicycle` | Bicycle | Bicicletta | REQUEST | REQUEST |
| `kite` | Kite | Aquilone | REQUEST | REQUEST |
| `igloo` | Igloo | Igloo | REQUEST | REQUEST |
| `table` | Table | Tavolo | REQUEST | REQUEST |
| `chair` | Chair | Sedia | REQUEST | REQUEST |
| `house` | House | Casa | REQUEST | REQUEST |
| `lighthouse` | Lighthouse | Faro | REQUEST | REQUEST |
| `crown` | Crown | Corona | REQUEST | REQUEST |

**Nature**

| noun_id | EN | IT | EN clip in bank | IT clip in bank |
|---|---|---|---|---|
| `flower` | Flower | Fiore | yes | yes |
| `mushroom` | Mushroom | Fungo | REQUEST | REQUEST |
| `sun` | Sun | Sole | yes | yes |
| `moon` | Moon | Luna | yes | yes |
| `rainbow` | Rainbow | Arcobaleno | REQUEST | REQUEST |
| `leaf` | Leaf | Foglia | yes | yes |
| `snowflake` | Snowflake | Fiocco di neve | REQUEST | REQUEST |
| `acorn` | Acorn | Ghianda | REQUEST | REQUEST |
| `bean` | Bean | Fagiolo | REQUEST | REQUEST |
| `sunflower` | Sunflower | Girasole | REQUEST | REQUEST |

**Instruments**

| noun_id | EN | IT | EN clip in bank | IT clip in bank |
|---|---|---|---|---|
| `drum` | Drum | Tamburo | REQUEST | REQUEST |
| `maracas` | Maracas | Maracas | REQUEST | REQUEST |
| `bells` | Bells | Campanelli | REQUEST | REQUEST |
| `trumpet` | Trumpet | Tromba | REQUEST | REQUEST |
| `tambourine` | Tambourine | Tamburello | REQUEST | REQUEST |
| `keyboard` | Keyboard | Tastiera | REQUEST | REQUEST |
| `xylophone` | Xylophone | Xilofono | REQUEST | REQUEST |

**Vet tools**

| noun_id | EN | IT | EN clip in bank | IT clip in bank |
|---|---|---|---|---|
| `stethoscope` | Stethoscope | Stetoscopio | REQUEST | REQUEST |
| `towel` | Towel | Asciugamano | REQUEST | REQUEST |
| `medicine` | Medicine | Medicina | REQUEST | REQUEST |
| `bandage` | Bandage | Benda | REQUEST | REQUEST |
| `sponge` | Sponge | Spugna | REQUEST | REQUEST |

**Block shapes**

| noun_id | EN | IT | EN clip in bank | IT clip in bank |
|---|---|---|---|---|
| `half_circle` | Half circle | Semicerchio | REQUEST | REQUEST |
| `arch` | Arch | Arco | REQUEST | REQUEST |
| `cylinder` | Cylinder | Cilindro | REQUEST | REQUEST |

Existing clips keep their approved wording and are not re-requested. Italian pig is "Maialino" in Memory text.

---

## B. Per-Activity lines

Format: EN | IT. "Cue id" is the proposed key under `activities/<id>/assets/audio/<locale>/`. Lines that reuse a shared set (A1–A5) say so instead of repeating it.

### Numbers ladder

**il_giardino_dei_numeri** — shared numbers 6–10 (A1) as `count_6`…`count_10`; and:
- `how_many` — "How many are in the crate?" | "Quanti sono nella cassetta?"
- optional `thats_n` — "That's N!" | "Sono N!"

**bosco_numeri** — `count_0` "Zero!" | "Zero!" (shared number 0); `ask_0` "Where is number 0?" | "Dov'è il numero 0?"; `write_n` "Let's write number N!" | "Scriviamo il numero N!"; `show_n` "Show me N!" | "Fammi vedere N!". Existing intro clip says "count to ten" (slightly off): owner decides whether to re-record.

**treno_numeri** — numbers 1–10 (A1); `order_n` "N apples, please!" | "N mele, per favore!" (noun swaps by cargo); `all_aboard` "All aboard!" | "Tutti a bordo!"; `count_again` "Let's count again." | "Contiamo di nuovo."; `make_same` "Make this wagon the same!" | "Fai questo vagone uguale!"; `too_many` "Too many! Take some out." | "Troppi! Togline qualcuno."; `not_enough` "Not enough yet!" | "Non bastano ancora!"; `toot` "Toot toot!" | "Ciuf ciuf!"

**stelle_incantate** — numbers 1–20 (A1); `connect_in_order` "Connect the stars in order!" | "Collega le stelle in ordine!"; `start_at_four` "Start at four!" | "Si parte dal quattro!"; `count_back` "Let's count back!" | "Contiamo all'indietro!"; `which_missing` "Which number is missing?" | "Quale numero manca?"; names of the 7 new constellation figures (final list from the Activity content).

**luci_di_momo** — numbers 6–10 (A1); `watch_closely` "Watch closely!" | "Guarda bene!"; `count_together` "Let's count them together." | "Contiamole insieme." ES/FR `prompt_choose` clips say the wrong instruction ("touch the lights in order") → re-record before ES/FR promotion; `prompt_ready` currently unused.

**casa_del_dieci** — `friends_coming` "Some friends are coming! Bring them in." | "Arrivano degli amici! Falli entrare."; `fireflies_home` "Some fireflies are flying home!" | "Alcune lucciole tornano a casa!"; `count_lights` "Count the lights with me!" | "Contiamo le luci insieme!"; ES `prompt_add` ("¡Añade!") is weak.

**bottega_delle_misure** — balance prompts (put both parcels / heavier / lighter): `put_parcels` "Put both parcels on the scale." | "Metti i due pacchi sulla bilancia."; `which_heavier` "Which one is heavier?" | "Quale è più pesante?"; `which_lighter` "Which one is lighter?" | "Quale è più leggero?"; `line_up_blocks` "Line up the blocks under the parcel. No gaps!" | "Allinea i blocchetti sotto il pacco. Senza spazi!"; `how_many_long` "How many blocks long is it?" | "Quanti blocchetti è lungo?" (The first three are paraphrased from the Activity's balance prompts; owner may edit.)

**costruiamo_ponti** — `long_enough` "Is it long enough?" | "È abbastanza lungo?"; `too_short` "Too short!" | "Troppo corto!"; `just_right` "Just right!" | "Giusto!"; `too_heavy` "Too heavy — try a stone plank!" | "Troppo pesante — prova un asse di pietra!"; `pillar_on_rock` "Put a pillar on the rock!" | "Metti un pilastro sul sasso!"; `lets_picnic` "Let's go to the picnic!" | "Andiamo al picnic!"

**pasticceria_magica** — numbers 1–10 (A1; wired to `shared_number_audio_path`); topping names → A5 (strawberry, blueberry, cherry, banana, cookie, chocolate); order, pattern, thanks and count-together lines: `order_n_toppings` "N please!" | "N, per favore!"; `finish_pattern` "Finish the row!" | "Finisci la fila!"; `thank_you` "Thank you!" | "Grazie!"; `count_together` "Let's count together." | "Contiamo insieme." (texts proposed from the Activity's intent; owner edits).

### Literacy

**festa_delle_rime** — `listen_end_of_word` "Listen to the end of the word!" | "Ascolta la fine della parola!"; `do_they_rhyme` "Do they rhyme?" | "Fanno rima?"

**alfabeto_leo** — `trace_letter` "Trace the letter with your finger!" | "Ripassa la lettera con il dito!"; optional `this_is_letter` "This is A." | "Questa è la A." Only capitals are taught today; ES/FR letters have no art.

**officina_dei_suoni** — `find_another_sound` "Now find another sound in the word!" | "Ora trova un altro suono nella parola!"; more isolated phoneme units for Stage 3 (d, n, EN r, g, h, z, short vowels) per language.

**foresta_parole** — EN "O as Octopus", "G as Goat", "I as Ice cream", "T as Turtle", "R as Rocket", "V as Vase" (+ the word clips octopus, goat, ice cream, turtle, rocket, vase); IT "T come Treno", "V come Vaso". Some existing EN/IT files lack receipts (EN j/k/x/y + find, IT h) and need regenerating or receipt reconciliation by the owner.

**sillabe_magiche** — EN `clap_beats` "Clap the beats!", `which_picture_fits_train` "Which picture fits the train?"; IT `clap_beats` "Batti le sillabe sul tamburo!", `which_vowel` "Quale vocale ci vuole?"; 3-beat word clips: EN banana, tomato; IT patata, farfalla. OWNER CHECK: EN "bee" uses the "be" syllable clip.

**mondo_contrari** — `now_the_opposite` "Now the opposite!" | "E adesso il contrario!" (concept words up/down/big/small/in/out/open/closed/fast/slow are existing clips).

### Logic and creative

**memory_meraviglie** — `choose_album` "Choose an album!" | "Scegli un album!"; `find_two_same` "Find two the same!" | "Trova due uguali!"; the 40 picture names go to A5.

**labirinto_magico** — `help_tito_tent` "Help Tito find the way to his tent!" | "Aiuta Tito a trovare la strada per la sua tenda!"; `found_star` "You found a star!" | "Hai trovato una stella!"; `find_all_stars` "Find all the stars first!" | "Prima trova tutte le stelle!"; `find_key` "Find the key to open the door!" | "Trova la chiave per aprire la porta!"

**la_discesa_della_biglia** — `pieces_in_spots` "Put the pieces in the shining spots!" | "Metti i pezzi nei posti che brillano!"; `tap_ramp_turn` "Tap the ramp to turn it!" | "Tocca la rampa per girarla!"; `oops_stopped` "Oops, it stopped!" | "Oh, si è fermata!"; `into_basket` "Into the basket!" | "Nel cestino!"

**specchi_magici** — `look_mirror_line` "Look at the mirror line." | "Guarda la linea dello specchio."; `turn_it` "Turn it around!" | "Giralo!"; `try_this_spot` "Try this spot!" | "Prova questo posto!"; shapes "Rhombus!" | "Rombo!" and "Heart!" | "Cuore!" (A4). ES/FR Lilli lines are in Leo's voice (defect to fix before promotion).

**quattro_amici** — 9 lines: `make_three_in_row` "Make three in a row!" | "Fai tre in fila!"; `make_four_in_row` "Make four in a row!" | "Fai quattro in fila!"; `your_turn` "Your turn!" | "Tocca a te!"; `leo_thinking` "Leo is thinking…" | "Leo sta pensando…"; `three_in_row` "Three in a row!" | "Tre in fila!"; `i_stopped_you` "I stopped you!" | "Ti ho fermato!"; `you_blocked_me` "You blocked me!" | "Mi hai bloccato!"; `draw` "It's a draw!" | "Pareggio!"; `you_won_match` "You won the match!" | "Hai vinto la partita!"

**torre_forme** — `fill_shape_blocks` "Fill the shape with blocks!" | "Riempi la forma con i blocchi!"; `turn_it` "Turn it!" | "Giralo!"; `it_fits` "It fits!" | "Ci sta!"; 6 block-shape names (A4: square, rectangle, triangle, half circle, arch, cylinder); build names → A5 (igloo, table, boat, lighthouse, house, train, rocket, snail, chair, crown, car, cat, fish, turtle).

**nascondino_bosco** — animals and positions: names hedgehog/riccio, squirrel/scoiattolo, bear/orso, deer/cerbiatto, duck/papera, snail/lumaca, butterfly/farfalla (A5); place phrases `place_bush` "Behind the bush" | "Dietro il cespuglio"; `place_rock` "Behind the rock" | "Dietro il sasso"; `place_log` "Behind the log" | "Dietro il tronco"; `place_mushroom` "Behind the mushroom" | "Dietro il fungo"; `place_pumpkin` "Behind the pumpkin" | "Dietro la zucca"; `place_leaves` "Under the leaves" | "Sotto le foglie"; `place_snow` "Under the snow" | "Sotto la neve"; `place_pond` "In the pond" | "Nello stagno"; `where_is` "Where is the…?" | "Dov'è…?" (A3).

**quattro_stagioni** — per-mission prompts per season (the four season names; approved clips describe each season), ~13 item names with right/wrong-season lines. Items: sun / sole, rain / pioggia, wind / vento, snow / neve, flowers / fiori, strawberries / fragole, watermelon / anguria, pumpkin / zucca, mushrooms / funghi, snowman / pupazzo di neve, woolly hat / cappello di lana, scarf / sciarpa, sun hat / cappello di paglia; `belongs_here` "Yes, that belongs in this season!" | "Sì, questo è di questa stagione!"; `not_this_season` "Hmm, not in this season." | "Mmm, non in questa stagione."

**storie_della_mia_voce** — `order_pictures` "Put the pictures in order!" | "Metti le figure in ordine!"; `what_first` "What happens first?" | "Cosa succede prima?"; `tell_story` "Now tell me your story!" | "Ora raccontami la tua storia!"; `tell_picture` "Tell me about this picture!" | "Raccontami questa figura!"; `great_story` "What a great story!" | "Che bella storia!"; shelf-full line (text to be authored); titles of the 5 stories (texts per Activity content).

**teatrino_fiabe** — `three_two_one` "Three, two, one… action!" | "Tre, due, uno… si va in scena!"; shelf-full line; `stage_full` "The stage is full!" | "Il palco è pieno!"

**shape_garden** — 8 shape names (A4); `drag_shape` "Drag a shape into the garden!" | "Trascina una forma nel giardino!"; `beautiful_garden` "What a beautiful garden!" | "Che bel giardino!"

**posta_di_leo** — `who_is_it_for` "Who is it for?" | "Per chi è?"; `pick_picture` "Pick a picture!" | "Scegli un'immagine!"; `off_it_goes` "Off it goes!" | "Si parte!"; per-friend thank-you line (one per canonical friend; text to be authored).

**orchestra_animali** — `listen` "Listen…" | "Ascolta…"; `your_turn` "Your turn!" | "Tocca a te!"; Loud / Soft / Fast / Slow → Forte / Piano / Veloce / Lento; 6 instrument names (A5: drum, maracas, bells, trumpet, tambourine, keyboard) + xylophone.

**morbidi_mostriciattoli** — `new_friend` "A new friend!" | "Un nuovo amico!"; `surprise` "Surprise!" | "Sorpresa!"; spoken name syllables (the syllable bubbles used for names; list from `activities/morbidi_mostriciattoli` content at recording time).

**workshop_settings (My Greia)** — `this_is_your_greia` "This is your Greia!" | "Questo è il tuo Greia!"; `pick_your_friend` "Pick your friend!" | "Scegli il tuo amico!"; room colour line + 8 colours (A2); `bigger` / `smaller` "Bigger!" / "Smaller!" | "Più grande!" / "Più piccolo!"; `nice_picture` "What a nice picture!" | "Che bel disegno!"

### Nature, care and feelings

**nanna_delle_nuvolette** (whispered) — `goodnight_cloud` "Goodnight, little cloud" | "Buonanotte, nuvoletta"; `shh_sleepy` "Shh, sleepy time" | "Shh, è ora di nanna"; dream line with colour ("A [colour] blanket, please" | "Una coperta [colore], per favore" — wording to be authored); numbers 1–5 (A1) and six colour names (A2).

**clinica_cuccioli** — `where_hurt` "Where does it hurt?" | "Dove ti fa male?"; `what_first` "What do we do first?" | "Cosa facciamo prima?"; `whats_next` "What's next?" | "E adesso?"; `all_better` "All better! Bye bye!" | "Guarito! Ciao ciao!"; tool names (A5: stethoscope, towel, medicine, bandage, sponge).

**cucciolo_mio** — need lines: hungry, muddy, play, ouch, sleepy (texts to be authored, e.g. "I'm hungry!" | "Ho fame!", "I'm muddy!" | "Sono tutto sporco!", "Let's play!" | "Giochiamo!", "Ouch!" | "Ahi!", "I'm sleepy…" | "Ho sonno…"); `not_now` "Not now, thank you" | "Adesso no, grazie"; `thank_you` "Thank you!" | "Grazie!"; `time_for_bed` "Time for bed" | "È ora di dormire"; `who_look_after` "Who will you look after?" | "Di chi ti prenderai cura?"; `choose_name` "Choose a name" | "Scegli un nome" (existing name tags: moon, sun, flower, apple).

**faccine_momo** — no new lines requested.

**piccola_serra** — `pick_seed` "Pick a seed!" | "Scegli un seme!"; `thirsty` "The plant is thirsty!" | "La pianta ha sete!"; `needs_light` "It needs light!" | "Ha bisogno di luce!"; `too_much_water` "Too much water — let's wait." | "Troppa acqua — aspettiamo."; `ripe_pick` "It's ripe, let's pick it!" | "È maturo, raccogliamolo!"; `what_comes_first` "What comes first?" | "Cosa viene prima?"; per-plant harvest lines (bean, sunflower, strawberry, carrot; texts to be authored).

**acquario_magico** — 8 creature names EN/IT (A5: fish, turtle, octopus, jellyfish, seahorse, crab, starfish, dolphin; plus pufferfish as new); 14 mission prompts: `find_octopus` "Find the octopus" | "Trova il polipetto"; `feed_turtle` "Feed the hungry turtle" | "Dai la pappa alla tartaruga"; further prompts follow the same pattern for each creature (final 14 from the Activity's mission table). Submarine already has approved clownfish/turtle/dolphin names that can seed the shared bank.

**baia_delle_orche** — 9 lines: "Find Kiko" | "Trova Kiko", "Find Luna" | "Trova Luna", "Find Oskar" | "Trova Oskar", "Feed Kiko / Luna / Oskar" | "Dai da mangiare a Kiko / Luna / Oskar", "Make Kiko / Luna / Oskar jump" | "Fai saltare Kiko / Luna / Oskar".

**sottomarino_giramondo** — alarm line (EN e.g. "Alarm! All hands on deck!" | IT "Allarme! Tutti sul ponte!"); anglerfish vs "Lanternfish" naming to be settled by the owner.

**colline_allegre** — `slow_down` "Slow down!" | "Piano piano!"; `made_it_picnic` "You made it to the picnic!" | "Sei arrivato al picnic!"; ES/FR bundles have empty audio maps despite title WAVs (verify resolver projection).

**corsa_bacche** — `find_all_berries` "Find all the berries!" | "Trova tutte le bacche!"; `ladybird_passing` "Shh… wait, the ladybird is passing." | "Shh… aspetta, passa la coccinella."; `hedgehog_sleeping` "The hedgehog is sleeping — tiptoe past!" | "Il riccio dorme — passa in punta di piedi!"; `basket_full` "Basket full!" | "Cestino pieno!"

**volo_draghetto** — `fly_rings` "Fly through the rainbow rings!" | "Vola dentro gli anelli arcobaleno!"

**viaggio_delfino** — goal line without device words `swim_finish` "Swim to the finish and collect the pearls!" | "Nuota fino al traguardo e raccogli le perle!"; `choose_journey` "Choose a journey!" | "Scegli un viaggio!"; numbers 0–25 (A1). The old welcome clip mentions mouse/space and should be replaced.

**enciclopedia_greia** — no new lines requested by E4.

---

## C. Review / approval workflow

1. Owner strikes, edits or approves rows (a short list in chat is enough).
2. Approved rows are added to the local-agent task queue (`docs/testing/GREIA_LOCAL_AGENT_TASK_QUEUE.md`) as `READY` cues; unspecified texts (marked "to be authored") stay `BLOCKED_SCRIPT`.
3. The local Voice Studio produces candidates + receipts under ignored `tmp/`; the owner (or a person) listens before any file lands under `assets/audio/…` or an Activity's `assets/audio/`.
4. Shared sets land once (vocabulary bank, numbers bank) and Activities pick them up through the existing resolvers; no Activity code change is needed except implementing `shared_number_audio_path`.

Evidence class of this document: **DESIGN SPEC / request list** — no audio exists for any new row, no recording or listening has happened.
