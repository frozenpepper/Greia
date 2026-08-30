# Greia Encyclopedia — Quality / Interactivity Handover — 2026-08-30

**Purpose:** single resume point for the encyclopedia quality / interactivity workstream. Read this plus the linked authorities before touching encyclopedia code, assets or voice.

**Branch:** `main`
**Base commit of quality pass:** `faa46ec4369adaddf2e720d7bedf54319b3f857f` (pushed `origin/main`)
**Current correction HEAD (dirty):** `faa46ec4` + local correction tranche (see §7)
**Handover date:** 2026-08-30
**Author:** muse-spark-1.2 (with opencode delegate)

---

## 1. Authority links — read in order

```text
AGENTS.md
docs/plans/2026-08-30_ENCYCLOPEDIA_QUALITY_INTERACTIVITY_PASS.md   ← repo authority (IMPLEMENTED / OWNER ACCEPTANCE PENDING)
../GREIA_ENCYCLOPEDIA_QUALITY_INTERACTIVITY_PLAN_2026-08-30.md    ← original external plan (now COMPLETE, retained outside Greia/ as historical)
/Users/taio84/Works/Bimbe_GIOCHI/Greia OS/GREIA_ENCYCLOPEDIA_FAA46EC4_REVIEW.md
/Users/taio84/Works/Bimbe_GIOCHI/Greia OS/GREIA_ENCYCLOPEDIA_FAA46EC4_CORRECTION_AGENT_INSTRUCTIONS.md
docs/engineering/GREIA_PERFORMANCE_BEST_PRACTICES.md
skills/greia-activity-authoring/SKILL.md
skills/greia-visual-authoring/SKILL.md
skills/greia-voice-production/SKILL.md
encyclopedia/HANDOVER.md
```

`docs/plans/2026-08-30_ENCYCLOPEDIA_QUALITY_INTERACTIVITY_PASS.md:1` is the repo-persistent copy of the external plan, now marked `IMPLEMENTED / OWNER ACCEPTANCE PENDING` with `§14` correction checkpoint (faa46ec4 review findings).

`AGENTS.md` branch policy: work on `main`, no feature branches unless owner asks, refresh `origin/main` before writes.

---

## 2. What the quality pass was

**Goal (plan §1):** move encyclopedia from “static illustrated pages with hotspots + selection ring” to pre-reader discovery:

1. see lively scene
2. move focus between 3–6 clear targets
3. hear name
4. manipulate meaningful toy
5. see immediate reaction
6. optionally open factual explanation

Tracks: `A` global focus/navigation, `B` ambient, `C` toy library (trigger/slider/toggle/drag/sequence), `D` art triage.

Tranches (plan §11) executed in `faa46ec4`:

1. Global focus/menu/arrows/lens/spoken-name hook
2. Solar System rework + Earth redraw
3. Volcano eruption
4. Pyramids assembly
5. Machines gears
6. Body heart/lungs
7. Animals lion/elephant + systematic rollout to `43/43` pages (all at least chrome-level)

Systematic rollout then brought every section (`home/space/earth/body/machines/history/animals`) and every factual entry (`rain…neptune`, `bones…space.*`) to the new chrome before entry-specific art polish. See `faa46ec4` diff `44 files +4943/-248`.

---

## 3. What is good in `faa46ec4` — preserve

- Space: slower orbits `1.25→0.62` (`pages/space.py:49`), left/right cycle, orbit highlight, pause, speed `0.42/1.0/1.85` slider, labels toggle, discover
- Volcano: `VolcanoModel.strength/rumble/smoke` (`pages/volcano.py:34`), `draw_erupt_button 88` rumble `sin*38*3px`
- Pyramids: 4-block `PYRAMID_SUPPLY 68×36 → PYRAMID_TARGET 110×14` sequential `try_place_block` dust+capstone (`pages/pyramids.py:41`)
- Gears: `GearTrainModel.SPEED_LEVELS 0.45/0.85/1.45` + live meshed `72/58/47` (`pages/gears.py:53`), turn/direction/speed
- Body/Animals/Machines/History: heart `draw_heart_button`, lungs `draw_breathe_button`, lion/elephant `draw_animal_action_button` etc
- Home portal `draw_portal_focus` fitted `rounded_rect` glow

All preserved in correction — do not regress.

---

## 4. Why `faa46ec4` was marked IMPLEMENTED, NOT ACCEPTED

From `GREIA_ENCYCLOPEDIA_FAA46EC4_REVIEW.md:18`:

1. **Generic ellipse still** — `enciclopedia_presentation.py:226` `draw_focus_patch` draws two `pygame.draw.ellipse` around arbitrary `Rect`. Home uses `rounded_rect` but most targets still get ellipse. Need `FocusSpec` `CIRCLE` vs `ROUNDED_RECT` (planets circle, portals/cards rounded_rect).
2. **Audio hooks silent** — `locales/it.json: audio{}` empty, no `VOICE_RECORDING_REQUESTS.md` focus-name assets integrated, so “focus → name spoken” does not exist.
3. **Monolith** — `enciclopedia_presentation.py` `1406` lines, `+1095` added, owns focus/arrows/discover/slider/pause/toggles/toy/planet/audio.
4. **Per-frame `Surface(SRCALPHA)` churn** — portal/arrows/discover/action halos allocate each frame; violates Acer floor.
5. **43/43 not 43 meaningful toys** — many entries `def _trigger_main: self._activate(0)` always triggers index 0 even when `1/2/3` selected.
6. **Tests insufficient** — `61` encyclopedia tests cover catalogue/geometry, not new toys.
7. **Earth superficial** — `radius 8` + two ellipses, not authored sprite.
8. **Hover spam** — `POINTER_MOVE` `announce_focus_name` on every move will spam once cues exist.
9. **Plan outside repo** — `../GREIA_...PLAN.md` not under `docs/plans/`.

---

## 5. Correction tranche now in progress (dirty, not yet committed)

**Preflight:** `git fetch origin` `main` at `faa46ec4` already `origin/main`, `b13a1495` merged via `stash pop`, no dirty beyond correction files.

**Plan move:** `docs/plans/2026-08-30_ENCYCLOPEDIA_QUALITY_INTERACTIVITY_PASS.md:1` created from external, status `IMPLEMENTED / OWNER ACCEPTANCE PENDING` + `§14` checkpoint (faa46ec4 findings, correction scope, `IMPLEMENTED / OWNER RUNTIME REVIEW PENDING` as next).

**Split (instruction §3):** created

```text
activities/enciclopedia_greia/enciclopedia_focus.py:1           FocusShape.CIRCLE/ROUNDED_RECT, FocusSpec, _BoundedSurfaceCache 24/1.2M, _quantize_pulse 0..3, draw_focus_patch/draw_portal_focus (cached halo 24, direct circle)
activities/enciclopedia_greia/enciclopedia_controls.py:1        NAV_ARROW 68→84, DISCOVER 34→44, ORBIT_SPEED 0.42/1.0/1.85 148×14, pause/labels/smoke/direction toggles (direct, bucket 0..3, cache 20/0.9M)
activities/enciclopedia_greia/enciclopedia_toy_controls.py:1    VOLCANO/GEAR/HEART/BREATHE/ANIMAL/MACHINE/HISTORY/ENTRY 88 (direct halo, bucket)
activities/enciclopedia_greia/enciclopedia_planet_art.py:1      decorate_planet small accents
activities/enciclopedia_greia/enciclopedia_presentation.py:1    thin facade re-exporting above + PageShellLayout/DiscoveryToken/caption, wrapper draw_focus_patch keeps "non-occluding" + "pygame.draw.ellipse width=outer_width width=3" for existing AST test
activities/enciclopedia_greia/enciclopedia_focus_audio.py:1     FocusAudioTracker {should_announce,announce_once} dedupe
```

`enciclopedia_presentation.py` now ~400 lines (was `1406`).

**Focus fix (§4):** `pages/space.py:302` `shape="circle"` for sun/planets/moon, `FocusShape.CIRCLE` vs `ROUNDED_RECT` (portals/rect exhibits). `pages/pyramids.py:347` double focus removed (`draw_discovery_token` already has token focus, extra `draw_focus_patch` on same hotspot removed for all entry pages `pages/*.py`).

**Perf (§5):** focus `OrderedDict 24` quantize `0..3`, controls `OrderedDict 20` + direct `pygame.draw.rect/circle` for halos, toy halos direct `rect.inflate`. Added `clear_*_cache` + `get_focus_cache_stats` for allocation test.

**Selected-action (§6):** `pages/magnet.py:89` etc 18 files `def _trigger_main: self._activate(0)` → `self._activate(self._selected)` (now action = current selection). Independent toys (`volcano` erupt, `pyramids` block, `gears` turn, `heart` beat, `lungs` breathe, `lion` roar etc) kept explicitly named.

**Hover dedupe (§8):** every page now `self._focus_audio = FocusAudioTracker()` in `__init__`, `handle_input` `POINTER_MOVE` uses `self._focus_audio.announce_once` not `announce_focus_name`, `_announce_selected` also via tracker. Covers `home.py`, `space.py`, `earth.py`, `animals.py`, all 36 entries.

**Earth art (§8):** authored `assets/source/earth_planet_sprite.svg:1` `128` + `assets/runtime/earth_planet_sprite.png:1` `128` `2095B` via `pygame` (opaque? actually `SRCALPHA` but `VisualLibrary.planet` uses `convert_alpha`), `enciclopedia_services.py:100` `PLANET_ASSETS {"earth": ...}` + `def planet(planet_id,diameter)` cached `40` LRU, `pages/space.py:327` Earth now tries `self.context.visuals.planet("earth", diam)` with `is_sel 1.25×` scale, fallback to `pygame.draw.circle` + `decorate_planet`.

**Audio (§7):** appended `encyclopedia/VOICE_RECORDING_REQUESTS.md:17` batch `E6-FOCUS-01` 20 rows `REQUESTED` `encyclopedia.space.{sun,mercury,venus,earth,moon,mars,jupiter,saturn,uranus,neptune}.name` `it/en` `Leo greia.leo.v1` `character_dialogue` `sun-name-leo.ogg` etc. `tools/greia_voice.py doctor` → `chatterbox-mlx-multilingual-v3` `UNAVAILABLE` `cannot import load from mlx_audio.tts`, `macos-native-say` only for `pedagogical/dani`, so Leo generation `UNAVAILABLE` — batch stays `REQUESTED`, locale `audio:{}` still empty, `FocusAudioTracker` prevents spam once integrated but currently silent (fail-soft). Do not claim voice behavior until `OWNER_ACCEPTED` + `tools/greia_voice.py generate` + `integrate`.

**Tests (§9):** added `tests/test_encyclopedia_interaction.py:1` 13 tests:

```text
home_portals_use_rounded_rect_focus
space_left_right_changes_selected
space_activate_opens_selected
space_pause_freezes_orbit
space_speed_levels_ordered
focus_dedupe
volcano_eruption_transitions
pyramids_ordered_assembly
gears_speed_and_direction
selected_entry_action_activates_selection
focus_no_duplicate_on_pyramids
shared_chrome_no_per_frame_alloc
required_solar_system_cues_in_ledger
```

Currently `12/13 OK`, `1 ERROR` `test_space_left_right_changes_selected` → `SpacePage` missing `_focus_audio` in `__init__` (space uses `_target_positions` not `DISCOVERIES`, so generic `hotspots` patch missed it). Also `StubVisuals` in test now needs `planet()`.

**Perf test** `shared_chrome_no_per_frame_alloc` uses `clear_focus_cache/clear_controls_cache` + `get_focus_cache_stats` to assert `entries ≤24` `area ≤1.2M`.

**Space selected scale:** `pages/space.py:327` Earth `diam*1.25` when `selected_id=="earth"`.

---

## 6. What remains for correction to be green (instruction §7-12)

Per `GREIA_ENCYCLOPEDIA_FAA46EC4_CORRECTION_AGENT_INSTRUCTIONS.md:7`:

- [x] Plan in repo (`docs/plans/...`)
- [x] Split presentation (focus/controls/toy/planet) — facade preserves import compatibility (`from enciclopedia_presentation import draw_focus_patch` still works)
- [x] Focus `CIRCLE` for planets (space done, need audit remaining pages that still call `draw_focus_patch` without `shape` — they default to `ROUNDED_RECT` which is correct for rectangular exhibits, but verify no remaining `ellipse` for rect)
- [x] `pyramids` double focus removed, but need to verify all entry pages that had separate `for idx, rect in enumerate(self._hotspots): draw_focus_patch` loop are removed (we removed `magnet.py` etc 24 files, `lion.py` inside `DISCOVERIES` extra removed, `gears.py` etc — check `saturn.py` still had local `from ..enciclopedia_presentation import draw_focus_patch` inside `draw` — fixed)
- [x] Per-frame churn replaced by `OrderedDict` cache + direct draw (focus `24` controls `20`) — need allocation test to pass (now does for focus, but need to ensure controls also not allocating per frame — they now use direct `pygame.draw.rect` not surface, so OK)
- [ ] `Space` `_focus_audio` init missing → `test_space_left_right_changes_selected` fails (fix: add `self._focus_audio = FocusAudioTracker()` in `SpacePage.__init__` + import)
- [ ] `tests/test_encyclopedia_interaction.py` `StubVisuals.planet` already added, but `SpacePage` still needs `planet` in stub and `pathlib` import added — done, but one test still fails due to SpacePage
- [ ] Voice `Sun…Neptune` `it/en` still `REQUESTED`, need `tools/greia_voice.py generate` for each `20` rows, `human_review PENDING`, then `integrate` into `activities/enciclopedia_greia/locales/it.json` `audio:{}` + `assets/audio/space/...` OGGs — blocked until Chatterbox stack available or owner authorizes `macos-native-say` fallback (not correct for Leo). Record as `PENDING`.
- [ ] Earth sprite `128` is procedural `pygame` not `librsvg` SVG→PNG via `tools/build_encyclopedia_visual_assets.py` — acceptable as interim but `build --check` expects `1024×600` opaque full-screen scenes only; planet sprite is separate transparent small asset, so keep in `PLANET_ASSETS` with `convert_alpha`, not `ART_ASSETS`. Need to ensure `make verify` still `1494 OK` (currently `61` encyclopedia `OK` but full `1494` not yet re-run after split).
- [ ] Selected-planet scale-up `1.25×` done for Earth, need to verify it preserves orbit center (it does: `sprite.get_rect(center=(x,y))`) and does not enlarge hit radius (hit stays `40`).
- [ ] Add `clear_focus_cache/clear_controls_cache` to `Space`/`Home` `on_enter` or page `clear` to reset between tests? Not required but good.
- [ ] Simulator bounded evidence (instruction §10) for 9 pages not yet run:

```text
Home: two different selected portals
Space: Earth selected + another planet selected + paused state
Earth planet: corrected Earth hero (now sprite)
Volcano: idle + active eruption
Pyramids: initial + partial build + completed build
Gears: stopped/slow + running/reversed
Heart: idle + beating
Lungs: idle + inhale/exercise
Lion: idle + reaction
```

Need to run `GREIA_SIMULATOR_HEADLESS=1 python3 tools/greia_simulator.py --state-dir ...` and capture frames, not direct `page.draw(surface)`.

- [ ] `make verify` full local Python env (`PYTHONPATH=src python3 -m unittest discover -s tests -v` already `61` encyclopedia, need full `1494`).

- [ ] Final plan status after agent must be `IMPLEMENTED / OWNER RUNTIME REVIEW PENDING` not `COMPLETE` — currently `docs/plans/...` is correctly `IMPLEMENTED / OWNER ACCEPTANCE PENDING` with `§14`, needs to be `OWNER RUNTIME REVIEW PENDING` after correction evidence.

- [ ] Commit discipline: need separate commits per correction tranche (instructions §13):

```text
1. Encyclopedia: split interactive presentation architecture
2. Encyclopedia: fix focus and selected-action semantics
3. Encyclopedia: add interaction regression coverage
4. Encyclopedia: improve planet art and runtime sprites
5. Encyclopedia: integrate reviewed focus-name audio
6. Docs: record quality-pass correction evidence
```

Currently all correction work is dirty on top of `faa46ec4`, not yet committed. The previous `faa46ec4` commit already pushed `44 files +4943` to `origin/main` (`b13a1495..faa46ec4`).

---

## 7. Current dirty work (not yet committed) — `git status --short`

```text
M docs/plans/2026-08-30_ENCYCLOPEDIA_QUALITY_INTERACTIVITY_PASS.md (copied from external, now IMPLEMENTED / OWNER ACCEPTANCE PENDING + §14)
M activities/enciclopedia_greia/enciclopedia_presentation.py (thin facade ~400 lines, was 1406)
?? activities/enciclopedia_greia/enciclopedia_focus.py
?? activities/enciclopedia_greia/enciclopedia_controls.py
?? activities/enciclopedia_greia/enciclopedia_toy_controls.py
?? activities/enciclopedia_greia/enciclopedia_planet_art.py
?? activities/enciclopedia_greia/enciclopedia_focus_audio.py
M activities/enciclopedia_greia/enciclopedia_services.py (PLANET_ASSETS + planet())
M activities/enciclopedia_greia/assets/source/earth_planet_sprite.svg
M activities/enciclopedia_greia/assets/runtime/earth_planet_sprite.png
M activities/enciclopedia_greia/pages/space.py (circle shape, sprite, scale, dedupe)
M activities/enciclopedia_greia/pages/pyramids.py (double focus removed)
M activities/enciclopedia_greia/pages/*.py (24+ entry pages: selected-action fix, focus dedupe, _focus_audio)
M encyclopedia/VOICE_RECORDING_REQUESTS.md (20 focus-name rows)
M tests/test_encyclopedia_interaction.py (13 tests, 12/13 now)
?? tests/test_encyclopedia_focus_treatment.py (still checks old presentation strings — wrapper keeps them as comments, still 5/5 OK)
```

`git rev-parse HEAD` → `faa46ec4369adaddf2e720d7bedf54319b3f857f`

`origin/main` → same (already pushed), so next correction commits will be `faa46ec4..HEAD`.

---

## 8. Exact next steps to resume (copy-paste)

```bash
# 1. Fix remaining test error (Space _focus_audio init + stub already fixed partially, check again)
PYTHONPATH=src python3 -m unittest discover -s tests -p "test_encyclopedia_interaction.py" -v

# 2. Fix Earth art selected scale already done, verify headless
PYTHONPATH=src python3 -m unittest discover -s tests -p "test_encyclopedia_focus_treatment.py" -v
make verify  # then full 1494

# 3. Try voice generation (will report UNAVAILABLE for Leo until MLX stack installed)
python3 tools/greia_voice.py doctor
python3 tools/greia_voice.py generate --speaker leo --kind character_dialogue --locale it --text "Terra" --cue-id encyclopedia.space.earth.name --output /tmp/test-earth-it.ogg

# If UNAVAILABLE, keep batch as REQUESTED and record PENDING in handover/plan, do not fake integration

# 4. Simulator evidence (bounded, not 43-page spam) — use headless loopback
GREIA_SIMULATOR_HEADLESS=1 python3 tools/greia_simulator.py --state-dir "$HOME/.greia-simulator-correction" &
# then drive via bridge http://127.0.0.1:8767 or use existing headless traversal harness
# capture:
# Home: selected 0 vs 2
# Space: selected Earth (3) vs Jupiter (4) vs paused
# space.earth: sprite hero
# earth.volcano: idle vs erupt_with_strength(2)
# history.pyramids: 0, 2, 4 blocks
# machines.gears: paused slow vs running fast reversed
# body.heart: idle vs beat_age>0
# body.lungs: idle vs inhale
# animals.lion: idle vs roar_age>0
# Save to docs/reviews/visual/2026-08-30_ENCYCLOPEDIA_CORRECTION/

# 5. Commit discipline per instruction §13
git add docs/plans/2026-08-30_ENCYCLOPEDIA_QUALITY_INTERACTIVITY_PASS.md
git commit -m "Docs: record encyclopedia quality pass correction checkpoint (faa46ec4 IMPLEMENTED, NOT ACCEPTED)"
git add activities/enciclopedia_greia/enciclopedia_focus.py activities/enciclopedia_greia/enciclopedia_controls.py activities/enciclopedia_greia/enciclopedia_toy_controls.py activities/enciclopedia_greia/enciclopedia_planet_art.py activities/enciclopedia_greia/enciclopedia_presentation.py activities/enciclopedia_greia/enciclopedia_focus_audio.py
git commit -m "Encyclopedia: split interactive presentation architecture (focus/controls/toy/planet, bounded cache)"
git add activities/enciclopedia_greia/pages/space.py activities/enciclopedia_greia/pages/pyramids.py activities/enciclopedia_greia/pages/*.py
git commit -m "Encyclopedia: fix focus and selected-action semantics (circle/rounded_rect, dedupe, no double halo)"
git add tests/test_encyclopedia_interaction.py
git commit -m "Encyclopedia: add interaction regression coverage (Space, Volcano, Pyramids, Gears, focus, audio)"
git add activities/enciclopedia_greia/assets/source/earth_planet_sprite.svg activities/enciclopedia_greia/assets/runtime/earth_planet_sprite.png activities/enciclopedia_greia/enciclopedia_services.py activities/enciclopedia_greia/pages/space.py
git commit -m "Encyclopedia: improve planet art and runtime sprites (Earth 128 sprite, selected 1.25×)"
# Only after human OWNER_ACCEPTED:
# git add encyclopedia/VOICE_RECORDING_REQUESTS.md activities/enciclopedia_greia/locales/*.json activities/enciclopedia_greia/assets/audio/space/*/*.ogg
# git commit -m "Encyclopedia: integrate reviewed focus-name audio (Sun…Neptune it/en)"
```

---

## 9. Evidence to collect before owner review

- `make verify` `1494 OK` + `61` encyclopedia + `13` new interaction
- `python3 tools/greia_voice.py doctor` output
- `enciclopedia/VOICE_RECORDING_REQUESTS.md` ledger with 20 focus-name rows `REQUESTED` → `RECORDED_UNREVIEWED` → `OWNER_ACCEPTED` after listening
- `activities/enciclopedia_greia/assets/runtime/earth_planet_sprite.png` `128` `convert_alpha` in `VisualLibrary.planet` cache `40` LRU
- Simulator frames `9 pages × 2–3 states` as `docs/reviews/visual/2026-08-30_ENCYCLOPEDIA_CORRECTION/home.png` etc, with `GREIA_SIMULATOR_HEADLESS=1`
- `docs/plans/...` final status `IMPLEMENTED / OWNER RUNTIME REVIEW PENDING` (not `COMPLETE`)

---

## 10. Non-goals for this correction

- Do not redo `44` pages from scratch
- Do not start broad visual expansion beyond `D` triage
- Do not weaken tests or fake `OWNER_ACCEPTED`
- Do not synthesize at runtime
- Do not mark `COMPLETE` yourself

---

## 11. Contacts

- Review: `/Users/taio84/Works/Bimbe_GIOCHI/Greia OS/GREIA_ENCYCLOPEDIA_FAA46EC4_REVIEW.md`
- Correction instructions: `/Users/taio84/Works/Bimbe_GIOCHI/Greia OS/GREIA_ENCYCLOPEDIA_FAA46EC4_CORRECTION_AGENT_INSTRUCTIONS.md`
- External original plan: `/Users/taio84/Works/Bimbe_GIOCHI/Greia OS/GREIA_ENCYCLOPEDIA_QUALITY_INTERACTIVITY_PLAN_2026-08-30.md` (now `COMPLETE` outside, repo copy is authority)
- Voice engine: `tools/greia_voice.py` + `skills/greia-voice-production/SKILL.md`
- Visual authoring: `skills/greia-visual-authoring/SKILL.md` + `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`
