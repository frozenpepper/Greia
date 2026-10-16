# Control placement and keyboard affordance audit (2026-10-16)

**Scope:** all 45 Activities in `activities/` at `1a4b9cc3` (plus this tranche's changes).
**Rules audited:** `docs/product/ACTIVITY_INPUT_STANDARDS.md` § *Mouse-first control placement* and § *Keyboard affordance (drawn keys)*; ADR 0037 §4a/§4b.
**Owner direction:** Greia is used with a mouse or touchpad; controls used together must sit close together (Colline Allegre's GO and BRAKE in opposite corners is the counter-example); Activities controllable by keyboard should show a simple drawing of the arrow keys / Space that teaches the keyboard works too.
**Evidence:** SOURCE review of each Activity's layout/controls/input modules + one DESKTOP headless capture each (`tools/headless_greia_activity.py --locale en --viewport 1024x600`, all 45 PASS, scratch only). Several Activities open on a menu (pet/deck/story/level picker); their play-screen positions come from source. Not Acer evidence.

## Legend

* **Keys** — `focus`: arrows move the kit focus ring and Space/Enter activate (every Activity has this through `ControlLayer`); `direct`: arrows/Space act on play itself (steer, move, drop, carry); `letters`: letter keys act; `text`: real typing.
* **Hint** — is a keyboard hint required by the new rule (required for `directional`/`game` profiles and for `hybrid` play that acts directly on arrows/Space), and is it shown.
* **Spread** — are controls used together placed far apart (more than ~2 button widths, e.g. opposite corners)?
* **Verdict** — OK; FIXED (this tranche); FOLLOW-UP (problem, not changed here).

## Summary

| Count | Finding |
|---:|---|
| 45 | Activities audited (45 captures, all PASS) |
| 45 | operable by keyboard focus (arrows + Space/Enter) |
| 12 | play acts directly on arrows/Space (direct keys) |
| 10 | keyboard hint required by the new rule — **1 now shown** (quattro_amici), 9 follow-up (all in the concurrent game-fps set) |
| 2 | direct-key pointer tools where the hint is optional (shape_garden, teatrino_fiabe: Space picks up, arrows carry) |
| 2 | letter-key play outside the rule until a letter-keycap set exists (orchestra_animali, alfabeto_leo) |
| 5 | related controls spread apart — **1 fixed** (morbidi_mostriciattoli), 4 follow-up (colline_allegre, sottomarino_giramondo, costruiamo_ponti, la_discesa_della_biglia; all game-fps set) |
| 4 | paging arrows flanking their content — allowed by the rule's paging exception (enciclopedia_greia, teatrino_fiabe tray, shape_garden gallery, morbidi_mostriciattoli gallery) |
| 2 | FIXED in this tranche (quattro_amici, morbidi_mostriciattoli) |
| 11 | FOLLOW-UP (all in the game-fps set) |
| 32 | OK with no change |

## Per Activity

| Activity | Profile | On-screen controls (1024×600 logical) | Spread | Keys | Hint | Verdict / recommendation |
|---|---|---|---|---|---|---|
| acquario_magico | hybrid | mode pills bottom-left→centre (creatures/feed/bubbles/day); tank is the play area | no | focus + direct (arrows move the tool cursor in the tank) | required, not shown | FOLLOW-UP (game-fps): `KeyboardHint` arrows + Space beside the mode row (right end) |
| alfabeto_leo | hybrid | listen top-left, letter cards centre, progress top-right | no | focus + letters (typing the letter) | n/a (letters) | OK; later: letter-keycap hint once a letter set exists |
| baia_delle_orche | hybrid | care pills bottom row (feed/cuddle/play/song) + day/friend icons bottom-right; food picker top-centre; counters top-right | no | focus + direct (arrows move the cursor) | required, not shown | FOLLOW-UP (game-fps): hint arrows + Space at the right end of the care row |
| bosco_numeri | hybrid | listen top-left, number card centre, answers in card, progress top-right | no | focus | not required | OK |
| bottega_delle_misure | hybrid | shelves centre, answer card right, listen + progress top-right | no | focus | not required | OK |
| casa_del_dieci | hybrid | windows centre, OK button bottom-centre under the house, listen + dots top-right | no | focus | not required | OK |
| clinica_cuccioli | hybrid | tool tray bottom-centre, progress top-right | no | focus | not required | OK |
| colline_allegre | game | BRAKE round 132 px bottom-**left**, GO 132 px bottom-**right** (~740 px apart); top bar dots/road/stars/listen | **yes** (owner's counter-example) | focus + direct (→/↑/Space go, ←/↓ brake) | required, not shown | FOLLOW-UP (game-fps): `layout.cluster([(132,132)]*2, hint_size=...)` → BRAKE + GO adjacent bottom-right (brake left of go), hint ← → + Space in the cluster's hint slot; buggy anchor x 300 keeps the road ahead visible |
| corsa_bacche | directional | path board centre; basket counter top-left; dots + hint bulb top-right; no steering buttons (tap/drag on the path) | no | direct (arrows walk, Space waits) | required, not shown | FOLLOW-UP (game-fps): hint arrows + Space bottom-right outside the board |
| costruiamo_ponti | hybrid | GO pill top-**left** beside Home; plank tray bottom-centre; dots + hint top-right | **yes** (GO far from the tray it confirms, next to Home) | focus | not required | FOLLOW-UP (game-fps): move GO to the right end of the plank tray (one cluster: planks → GO) |
| cucciolo_mio | hybrid | pet picker cards centre + confirm bottom-right; play screen: care tray bottom + confirm bottom-right (`CONFIRM_RECT` 882,452) | no | focus | not required | OK |
| enciclopedia_greia | navigation | book with topic tiles; prev/next arrows on the book's left/right edges | paging exception | focus | not required | OK (paging arrows flank the pages they turn) |
| faccine_momo | navigation | six feeling choices in two columns flanking Momo, listen top-right | no (choices, not a pair) | focus | not required | OK |
| festa_delle_rime | navigation | listen top-left, two answer cards bottom-centre | no | focus | not required | OK |
| foresta_parole | directional | word sign left, basket bottom-centre, letters falling; listen top-left, dots top-right | no | direct (← → move the basket, Space drops) | required, not shown | FOLLOW-UP (game-fps): hint ← → + Space bottom-right |
| il_giardino_dei_numeri | hybrid | acorns + basket centre-right, listen + dots top-right | no | focus | not required | OK |
| la_discesa_della_biglia | hybrid | GO pill top-**left** beside Home; piece tray top-left; board centre; dots + hint top-right | **yes** (GO next to Home, away from the board's exit) | focus | not required | FOLLOW-UP (game-fps): GO into a bottom-right cluster beside the board (or under the piece tray) |
| labirinto_magico | directional | maze board centre; dots + hint bulb top-right; no steering buttons (tap/drag) | no | direct (arrows) | required, not shown | FOLLOW-UP (game-fps): hint arrows (+ Space if it acts) bottom-right outside the board |
| luci_di_momo | hybrid | jar + Momo bottom-left, sky is the play area, listen + dots top-right | no | focus | not required | OK |
| memory_meraviglie | hybrid | deck picker centre; play: card grid centre | no | focus | not required | OK |
| mondo_contrari | hybrid | scene centre, answer objects in scene, listen + dots top-right | no | focus | not required | OK |
| morbidi_mostriciattoli | hybrid | undo/dice top-left, save/gallery top-right; part **drawers far left** (x 12–196) and **option tray far right** (x 772–1012), ~580 px apart, used in alternation | **yes** | focus | not required | **FIXED**: drawers moved beside the tray (x 576–760); stage keeps the left; sizes unchanged. Gallery prev/next flank the cards (paging exception) |
| nanna_delle_nuvolette | hybrid | three clouds centre, blanket tray bottom-centre, dots top-left | no | focus | not required | OK |
| nascondino_bosco | hybrid | request banner top-centre, hiding props in scene, dots top-left | no | focus | not required | OK |
| officina_dei_suoni | navigation | listen top-left, machine centre, three answers bottom-centre-left, dots top-right | no | focus | not required | OK |
| orchestra_animali | hybrid | play-along mic + play top-left (together), loud/soft + slow/fast strips top-right (together), xylophone bottom-centre | no (separate families) | focus + letters (A S D F … play bars) | n/a (letters) | OK; later: letter-keycap strip under the xylophone once a letter set exists |
| painting | pointer | gallery/undo top-left, save/new top-right, palette + sizes + eraser/stamp bottom bar | no (tool families) | focus + canvas cursor | not required (pointer tool) | OK |
| pasticceria_magica | hybrid | order bubble left, ingredients bottom-centre, SERVE right (846,292), clear bottom-right (920,…) | no (~1.5 widths) | focus | not required | OK |
| piccola_serra | hybrid | seed cards bottom-centre, dots + hint top-right | no | focus | not required | OK |
| posta_di_leo | hybrid | mode tabs top-left, letter centre, send top-right of the letter, mailbox right, sticker tray bottom | no | focus (+ Home/Up keys in the tray) | not required | OK |
| quattro_amici | hybrid | who-plays strip + turn banner + dots top bar; board columns are the controls; score plates under the friends | no | focus + direct (← → choose the column, ↓/Space drop) | required — **now shown** | **FIXED**: `KeyboardHint` ← ↓ → + Space right of the board's top row (shown 8 s at start, demonstrated on idle hints, lights while pressed) |
| quattro_stagioni | hybrid | four season buttons in one row bottom-centre, prompt top-centre | no | focus | not required | OK |
| shape_garden | pointer | gallery/undo top-left, backdrop/house/new top-right, colours left column, shapes bottom row, size/rotate tools right column, bin bottom-right | no (tool families; gallery prev/next = paging) | focus + direct carry (Space picks up, arrows carry) | optional (pointer tool) | OK; optional later: show the hint while a shape is carried by keyboard |
| sillabe_magiche | navigation | listen top-left, train centre, two answers bottom-centre | no | focus | not required | OK |
| sottomarino_giramondo | hybrid | LEFT/RIGHT bottom-**left** under the wheel, SURFACE/DIVE top-**right**, AHEAD/STOP right-middle lever, lights/sonar/alarm/bubbles/horn bottom row | **yes** (steering split over three areas) | focus + direct (arrows steer) | required, not shown | FOLLOW-UP (game-fps): one bottom-right CROSS cluster (↑ dive/surface, ← →, ↓) + AHEAD/STOP beside it; hint arrows + Space in its slot; keep the fun buttons row |
| specchi_magici | hybrid | mirror grid centre, tile tray bottom-centre, listen top-right | no | focus | not required | OK |
| stelle_incantate | hybrid | numbered stars in the sky, banner + listen top-centre, dots top-right | no | focus | not required | OK |
| storie_della_mia_voce | hybrid | story cards centre; story screen: mic with play + redo directly under it (`voice_layout` 129–133) | no | focus | not required | OK |
| teatrino_fiabe | pointer | scene/shows/brush top-left, mic + rec top-right (together), sticker columns left/right, puppet tray bottom with prev/next at its ends | paging exception (tray arrows) | focus + direct carry (Space picks up, arrows move a puppet) | optional (pointer tool) | OK; optional later: show the hint while a puppet is carried by keyboard |
| torre_forme | hybrid | piece tray + rotate button bottom-centre (together), target card right, listen + dots top | no | focus (+ controller west/north rotate) | not required | OK |
| treno_numeri | hybrid | number sign left, wagons centre, apples bottom, GO bottom-right | no | focus | not required | OK |
| viaggio_delfino | hybrid | level cards centre (menu); play: dolphin steered by pointer, no steering buttons | no | direct (↑ ↓ steer, Space jump) | required, not shown | FOLLOW-UP (game-fps): hint ↑ ↓ (← → dimmed) + Space bottom-right |
| volo_draghetto | directional | course cards + look row (menu); play: tap to flap, drag to steer | no | direct (arrows steer, Space flaps) | required, not shown | FOLLOW-UP (game-fps): hint arrows + Space bottom-right during the flight |
| workshop_settings | navigation | tabs top, preview left, choices grid right, reset top-right | no | focus | not required | OK |
| writing | text | book/undo/emoji top-left, save/new top-right, page | no | text | exempt (text) | OK |

## Follow-up pass (not changed here)

All in the concurrent **game-fps** set, which this tranche was told not to edit:

1. **colline_allegre** — BRAKE + GO as one bottom-right `ControlLayout.cluster` (ROW), keyboard hint ← → + Space in the cluster's hint slot (owner's original example).
2. **sottomarino_giramondo** — steering/depth/throttle into one bottom-right cluster (CROSS + throttle pair) with hint.
3. **costruiamo_ponti**, **la_discesa_della_biglia** — move GO out of the top bar beside Home into a cluster with the tray/board it confirms.
4. Keyboard hints (`KeyboardHint`, shown at start, `demonstrate()` from `IdleHintScheduler` steps, `observe_event` for lighting): **corsa_bacche**, **labirinto_magico**, **foresta_parole**, **volo_draghetto**, **viaggio_delfino**, **acquario_magico**, **baia_delle_orche** (and the two above).
5. Optional: shape_garden / teatrino_fiabe show the hint only while something is carried by keyboard; a letter-keycap set for orchestra_animali / alfabeto_leo.
