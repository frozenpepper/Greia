# Control placement and keyboard affordance audit (2026-10-16)

**Scope:** all 45 Activities in `activities/` at `1a4b9cc3` (plus this tranche's changes).
**Rules audited:** `docs/product/ACTIVITY_INPUT_STANDARDS.md` § *Mouse-first control placement* and § *Keyboard affordance (drawn keys)*; ADR 0037 §4a/§4b.
**Owner direction:** Greia is used with a mouse or touchpad; controls used together must sit close together (Colline Allegre's GO and BRAKE in opposite corners is the counter-example); Activities controllable by keyboard should show a simple drawing of the arrow keys / Space that teaches the keyboard works too.
**Evidence:** SOURCE review of each Activity's layout/controls/input modules + one DESKTOP headless capture each (`tools/headless_greia_activity.py --locale en --viewport 1024x600`, all 45 PASS, scratch only). Several Activities open on a menu (pet/deck/story/level picker); their play-screen positions come from source. Not Acer evidence.
**Follow-up pass (same day, after `87322f0d`):** the 11 FOLLOW-UP rows below were applied — see § *Follow-up pass applied*. Evidence: focused unit tests per Activity + DESKTOP headless captures at 1024×600 and 800×480 (one with `--press-key` showing the lit key per Activity). Not Acer evidence.

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
| 10 | keyboard hint required by the new rule — **all 10 now shown** (quattro_amici first, the other 9 in the follow-up pass) |
| 2 | direct-key pointer tools where the hint is optional (shape_garden, teatrino_fiabe: Space picks up, arrows carry) |
| 2 | letter-key play outside the rule until a letter-keycap set exists (orchestra_animali, alfabeto_leo) |
| 5 | related controls spread apart — **all 5 fixed** (morbidi_mostriciattoli first; colline_allegre, sottomarino_giramondo, costruiamo_ponti, la_discesa_della_biglia in the follow-up pass) |
| 4 | paging arrows flanking their content — allowed by the rule's paging exception (enciclopedia_greia, teatrino_fiabe tray, shape_garden gallery, morbidi_mostriciattoli gallery) |
| 13 | FIXED (quattro_amici, morbidi_mostriciattoli in the first tranche; 11 in the follow-up pass) |
| 0 | FOLLOW-UP left open from the required rules (optional items in § *Follow-up pass applied*) |
| 32 | OK with no change |

## Per Activity

| Activity | Profile | On-screen controls (1024×600 logical) | Spread | Keys | Hint | Verdict / recommendation |
|---|---|---|---|---|---|---|
| acquario_magico | hybrid | mode pills bottom-left→centre (creatures/feed/bubbles/day); tank is the play area | no | focus + direct (arrows move the tool cursor in the tank) | required — **shown** | **FIXED**: `KeyboardHint` arrows + Space (32 px keys) resting on the sand right above the Day/Night pill (right end of the bottom bar); shown 8 s at start, demonstrated with each mission hint, lit while pressed; display-only, nothing else changed |
| alfabeto_leo | hybrid | listen top-left, letter cards centre, progress top-right | no | focus + letters (typing the letter) | n/a (letters) | OK; later: letter-keycap hint once a letter set exists |
| baia_delle_orche | hybrid | care pills bottom row (feed/cuddle/play/song) + day/friend icons bottom-right; food picker top-centre; counters top-right | no | focus + direct (arrows move the cursor) | required — **shown** | **FIXED**: hint arrows + Space (32 px keys) in the sky under the counters (top-right, above the water and clear of the food tray) so it never covers a swimming orca; composed into the cached `HudOverlay` (re-composed only when its look changes); start/mission-hint/lit as acquario; nothing else changed |
| bosco_numeri | hybrid | listen top-left, number card centre, answers in card, progress top-right | no | focus | not required | OK |
| bottega_delle_misure | hybrid | shelves centre, answer card right, listen + progress top-right | no | focus | not required | OK |
| casa_del_dieci | hybrid | windows centre, OK button bottom-centre under the house, listen + dots top-right | no | focus | not required | OK |
| clinica_cuccioli | hybrid | tool tray bottom-centre, progress top-right | no | focus | not required | OK |
| colline_allegre | game | BRAKE round 132 px bottom-**left**, GO 132 px bottom-**right** (~740 px apart); top bar dots/road/stars/listen | **yes → fixed** | focus + direct (→/↑/Space go, ←/↓ brake) | required — **shown** | **FIXED**: `layout.cluster` ROW → BRAKE + GO side by side bottom-right (16 px gap, 132 px pedals; overlapping slop resolved to the nearer pedal), hint ← ↑ → ↓ + Space (34 px keys, ≥ 28 px on screen) in the cluster's hint slot; hint drawn in the cached HUD overlay (key includes its look); shown at set start, demonstrated with each idle hint |
| corsa_bacche | directional | path board centre; basket counter top-left; dots + hint bulb top-right; no steering buttons (tap/drag on the path) | no | direct (arrows walk, Space waits) | required — **shown** | **FIXED**: hint arrows + Space bottom-right outside the garden panel (34 px keys; the widest gardens fit beside it with ≤ 4 % smaller cells or slightly smaller keys); start of visit, idle nudges, lit while pressed; a look change forces a full (not dirty-rect) frame |
| costruiamo_ponti | hybrid | GO pill top-**left** beside Home; plank tray bottom-centre; dots + hint top-right | **yes → fixed** | focus | not required | **FIXED**: GO moved from the top bar beside Home to the right end of the plank tray (24 px gap, centred with it as one group: planks → GO) |
| cucciolo_mio | hybrid | pet picker cards centre + confirm bottom-right; play screen: care tray bottom + confirm bottom-right (`CONFIRM_RECT` 882,452) | no | focus | not required | OK |
| enciclopedia_greia | navigation | book with topic tiles; prev/next arrows on the book's left/right edges | paging exception | focus | not required | OK (paging arrows flank the pages they turn) |
| faccine_momo | navigation | six feeling choices in two columns flanking Momo, listen top-right | no (choices, not a pair) | focus | not required | OK |
| festa_delle_rime | navigation | listen top-left, two answer cards bottom-centre | no | focus | not required | OK |
| foresta_parole | directional | word sign left, basket bottom-centre, letters falling; listen top-left, dots top-right | no | direct (← → move the basket, Space drops) | required — **shown** | **FIXED**: hint ← → + Space (↑ ↓ dimmed) hanging above the picture sign (Space replays the word, like the sign), clear of the letter rain, the basket path and the chrome; part of the static-frame signature |
| il_giardino_dei_numeri | hybrid | acorns + basket centre-right, listen + dots top-right | no | focus | not required | OK |
| la_discesa_della_biglia | hybrid | GO pill top-**left** beside Home; piece tray top-left; board centre; dots + hint top-right | **yes → fixed** | focus | not required | **FIXED**: GO moved from the top bar to the tray column, directly under the last piece (column width, never over the board); tiles 86 px, Tito shrinks only on screens where the touch floor needs it |
| labirinto_magico | directional | maze board centre; dots + hint bulb top-right; no steering buttons (tap/drag) | no | direct (arrows) | required — **shown** | **FIXED**: hint arrows + Space bottom-right outside the maze (same fitting rule as corsa); Space also calls the firefly |
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
| sottomarino_giramondo | hybrid | LEFT/RIGHT bottom-**left** under the wheel, SURFACE/DIVE top-**right**, AHEAD/STOP right-middle lever, lights/sonar/alarm/bubbles/horn bottom row | **yes → fixed** | focus + direct (arrows steer) | required — **shown** | **FIXED**: all six piloting buttons in one right-panel cluster — Surface / Left / Right / Dive D-pad + Ahead / Stop under it + hint arrows + Space under that; the left panel is now the helm station (wheel above the throttle lever, both still draggable); look, fun-button row and arrow piloting unchanged |
| specchi_magici | hybrid | mirror grid centre, tile tray bottom-centre, listen top-right | no | focus | not required | OK |
| stelle_incantate | hybrid | numbered stars in the sky, banner + listen top-centre, dots top-right | no | focus | not required | OK |
| storie_della_mia_voce | hybrid | story cards centre; story screen: mic with play + redo directly under it (`voice_layout` 129–133) | no | focus | not required | OK |
| teatrino_fiabe | pointer | scene/shows/brush top-left, mic + rec top-right (together), sticker columns left/right, puppet tray bottom with prev/next at its ends | paging exception (tray arrows) | focus + direct carry (Space picks up, arrows move a puppet) | optional (pointer tool) | OK; optional later: show the hint while a puppet is carried by keyboard |
| torre_forme | hybrid | piece tray + rotate button bottom-centre (together), target card right, listen + dots top | no | focus (+ controller west/north rotate) | not required | OK |
| treno_numeri | hybrid | number sign left, wagons centre, apples bottom, GO bottom-right | no | focus | not required | OK |
| viaggio_delfino | hybrid | level cards centre (menu); play: dolphin steered by pointer, no steering buttons | no | direct (↑ ↓ steer, Space jump) | required — **shown** | **FIXED**: hint ↑ ↓ + Space (← → dimmed) on the sand bottom-right, below the deepest pearl row and far from the dolphin; shown at journey start, demonstrated with each idle hint, hidden for the count-up (a low jellyfish's tentacles can pass under it) |
| volo_draghetto | directional | course cards + look row (menu); play: tap to flap, drag to steer | no | direct (arrows steer, Space flaps) | required — **shown** | **FIXED**: hint arrows + Space on the cloud floor bottom-right, below the band the dragon and pickups fly in; shown at flight start, demonstrated with each idle hint (the existing over-the-dragon glyph hint is unchanged) |
| workshop_settings | navigation | tabs top, preview left, choices grid right, reset top-right | no | focus | not required | OK |
| writing | text | book/undo/emoji top-left, save/new top-right, page | no | text | exempt (text) | OK |

## Follow-up pass applied (2026-10-16, after `87322f0d`)

All 11 follow-ups from the first tranche are FIXED (rows above). Common implementation (no kit change):

* every hint is `ControlKit.keyboard_hint(...)` — display-only (never a layer/focus/touch target), shown 8 s at start, `demonstrate()` from the Activity's existing idle-hint step (IdleHintScheduler / mission hint / Captain Leo's order hint), lit through `observe_event` on every Pygame event, `update()` once per loop with `FrameGovernor.wake_at(deadline())` on static loops;
* keycaps are 32–34 logical px at 1024×600 (≈ 28–30 px visible) and are raised to ≥ 26–28 physical px on 800×480 where the space allows (the kit default of 44 in `preferred_size` is not used by any Activity; quattro_amici still uses 36);
* drawing preserves the Acer fast path: Activities with a cached `HudOverlay` (colline_allegre, baia_delle_orche) compose the hint into it and key the overlay on the hint's look; the others blit one RLE copy per look (`PreparedSurfaces`), and dirty-rect Activities (corsa_bacche, foresta_parole) force a full frame when the look changes;
* captures: `tools/headless_greia_activity.py` at 1024×600 + 800×480 for all 11 (flight/swim screens via `--click-*`), contact sheet `~/.cache/greia-art-review/control_followups.png` (scratch, not committed).

Still optional (unchanged):

1. shape_garden / teatrino_fiabe: show the hint only while something is carried by keyboard;
2. a letter-keycap set for orchestra_animali / alfabeto_leo;
3. kit candidates reported to the owner, not done here: a shared legible-key helper (logical key size from `ControlLayout.scale`) and a corner/"beside this rect" placement helper — four Activities carry the same few lines.
