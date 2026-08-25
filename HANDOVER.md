# Greia — Standalone Engineering Handover

**Date:** 2026-08-24  
**Version family:** `0.13.x` development  
**Repository:** `frozenpepper/Greia` (private)  
**Canonical/default/development branch:** `main`  
**Primary blocking platform phase:** **R7 — Direct graphics/session/input architecture**  
**External Parent HTML runtime revision currently pinned by Greia:** `frozenpepper/Greia-Parent-App-Html@7ff7e318eb246618dab26939ba086999864538ce`  
**Newer reviewed-source candidate containing microphone-processing UI:** `frozenpepper/Greia-Parent-App-Html@cdea281a1848d1372a18822a559dc15494e749b0`  
**Parent client integration state:** `source-pinned-not-yet-vendored`; microphone UI repin still requires local test/integrity regeneration

This file is the project-wide **current continuation contract**. Chronology belongs in plans/reviews; exact APIs/limits remain source-owned.

---

# 1. Current state at a glance

## New Activity: Stelle Incantate (2026-08-25)

**Stelle Incantate** (`org.greia.stelle-incantate`, 31st first-party Activity) — connect-the-dots **real constellations**: tap numbered stars in order, lines glow, the finished figure celebrates with its real name, Leo hosts an optional researched astronomy fact per figure (it/en captions; voice audio pending — honest scaffold, see `activities/stelle_incantate/research/facts.md`). Durable progress resumes across sessions; whole-sky finish shows the platform completion screen with replay. Pointer profile + number-key shortcuts; events `constellation.completed` (Star-eligible, once/session) + `curiosity.fact_opened`; two decorative emblems declared.

- **Verification**: `tests/test_activity_stelle_incantate.py` (12) + reconciled contract/audience/readiness/history-policy fixtures; full `make verify` **1,345/1,345 PASS** (activities=31, progression_rules=5). Simulator gate on the exact final state: Esplora → launch → ≥12 s survival → full Cassiopea round via star taps (completion + event path) → fact opened → Next → clean Home return, rc 0; durable progress proven across sessions. No-reading UX pass passed (`TEXT_REQUIRED_FOR_GAMEPLAY=no`).
- **Evidence lane**: source tests + simulator visual review. Leo fact voice audio pending production; physical hardware not claimed.

## Child Text Letter-Case Policy + Launcher Card Scale (2026-08-25)

Implemented (ADR 0034) and simulator-verified on the final source state.

- **Policy**: child-facing UI words present in CAPITAL letters by default (children learn capitals first); a parent may choose normal text per child. Platform owner: `src/greia_platform/child_text.py`; profile preference `ChildProfile.uppercase_text` (default true, backward-compatible); Parent App checkbox + Parent API `uppercase_text`; launch env `GREIA_PROFILE_UPPERCASE`; `LocalizedResources.text()` applies it automatically; Shell applies it at child-facing render chokepoints (card titles, disclosure, launch badge, profile names, category/collection/discovery labels, achievement copy).
- **Activity pass**: mixed-case package-local literals routed through `display_text` (painting, pasticceria_magica, posta_di_leo, sillabe_magiche, tre_carte_una_storia, memory_meraviglie, cucciolo_mio, foresta_parole, teatrino_fiabe). Child-authored content (Writing) is never transformed.
- **Cards +4%**: Activity tiles 218 px, Collection portals 141 px, sub-Collection portals 177 px, profile tiles 213 px at reference layout; label fonts unchanged; two-line card labels now compress leading instead of clipping past the card border (fit bug fixed in `title_presentation.py`).
- **Verification**: full `make verify` **1,324/1,324 PASS** (new `tests/test_child_text_case.py`). Simulator gate on the exact final state (1024×600, isolated workspace): uppercase launcher + activities, parent-disabled profile shows normal case, Painting/Acquario launch → ≥10 s survival → interaction → clean Home return, rc 0.
- **Evidence lane**: source tests + simulator visual review (screenshots reviewed in-session). Physical-device visual re-check rides the next hardware evidence pass.
- **Docs**: ADR 0034, style guide §3.3, activity-authoring skill rule 5 + PRE_READER_UX §7.1, os-work + visual-authoring skills; `skills/` and `.agents/skills/` fully reconciled.

## Fail-Soft Activity Cross-Bindings & Boot-Time Dev-Noise Scrub (2026-08-25)

Implemented (ADR 0033) so a single not-loadable Activity can never take down the child OS, and to remove the recurring dev-environment-dirt failure class.

- **Fail-soft cross-bindings**: `src/greia_platform/history.py` `ProgressionPolicy.load` now **drops** a progression rule that references an Activity absent from the loaded catalogue (with a `logger.warning`) instead of raising. Discovery already keeps a broken Activity unloaded; the previously-fatal dangling progression rule is what caused the launcher restart-loop. Structural policy corruption and undeclared events against *loaded* Activities remain hard failures.
- **Boot-time dev-noise scrub**: new `src/greia_platform/activity_tree_cleanup.py::scrub_activity_tree` removes the curated regenerable dev-noise set (`._*`, `.DS_Store`, `__MACOSX/`, `Thumbs.db`, `desktop.ini`, `__pycache__/`, `*.pyc`, editor droppings) before Activity loading. Invoked from `GreiaShell.__init__` before the `ActivityRegistry` is built (covers both `child_shell` and `presentation`). Bounded/non-escaping under the Activity root; **never** auto-repairs a genuinely broken Activity.
- **Verification**: `tests/test_activity_tree_cleanup.py` (4) + two fail-soft progression tests. Full `make verify` **1,313/1,313 PASS**.
- **Evidence lane**: source tests. Physical-device re-validation after a scrubbed tree is outstanding.

## Launcher Boot-Intro Background White Fix (2026-08-25)

Fixed the animated Greia boot intro so the background around the professor graphics is **pure white** on every display instead of dark/non-uniform.

- **Root cause**: `src/greia_launcher/boot_intro.py::_background_rgb()` sampled the animation-frame corner pixel (`logo.get_at((0,0))`). The 222×600 portrait frames have dark borders, so the letterboxing painted around the animation was dark.
- **Fix**: `_background_rgb()` now returns a fixed `(255, 255, 255)` core colour, independent of frame pixel content and resolution. The animation still fits proportionally/centred to any viewport. This aligns source with the already-documented "pure-white surrounding background" design (`docs/design/GREIA_BOOT_EXPERIENCE.md` Stage D). No per-resolution baked full-screen images are introduced.
- **Verification**: boot contract/diagnostics tests pass (66/66). Verified live on the reference Acer (`greia-dev.local`) over SSH: cleared the `/run/greia-os/boot-intro-played` one-shot marker, replayed the launcher intro, observed white background around the animation graphics.
- **Evidence lane**: source tests + physical-device visual review.

## Luci di Momo (`activities/luci_di_momo`) Pre-Reader & Momo Voice Overhaul (2026-08-25)

Overhauled **Luci di Momo** (`org.greia.luci-di-momo`) to give children ample time to prepare, eliminate rushed starts, integrate Momo's canonical cloned voice, and provide non-verbal/spoken pre-reader scaffolding:
1. **Paced Game Flow with Big Start / Play Button**:
   - Introduced a prominent `READY` phase at the start of each round: the child is not rushed by immediate flashing lights.
   - Screen presents Momo, the sleeping lantern in the enchanted night garden, and a **180×180 glowing Play button** `▶️` with a golden aura and `"TOCCA PER GIOCARE!"` / `"TAP TO PLAY!"` at the center of the screen.
   - Tapping the Play button initiates the firefly reveal with sparkling feedback.
2. **Canonical Momo Cloned Voice (32 Clips Total)**:
   - Synthesized using **Chatterbox Multilingual V3** (`mlx-community/chatterbox-multilingual-v3`) with Momo's canonical character reference master [`assets/audio/characters/canonical/v0.1/momo-reference-v1.flac`](file:///Users/taio84/Works/Bimbe_GIOCHI/Greia%20OS/Greia/assets/audio/characters/canonical/v0.1/momo-reference-v1.flac).
   - Generated with continuous GPU Metal cache clearing (`mx.clear_cache()`) and garbage collection (`gc.collect()`) to ensure small, bounded memory usage.
   - Welcome intro: *"Ciao! Guarda bene quante lucciole brillano nella notte, poi tocca il numero giusto!"* / *"Hello! Look closely at how many fireflies glow in the night, then tap the right number!"*.
   - Added `[ 🔊 ASCOLTA ]` speech balloon button `(145, 500, 150, 48)` beside Momo at `(25, 435)` to replay instructions anytime.
3. **Spoken Quantity & Gender-Neutral Praise**:
   - Correct choices pronounce the quantity (*"Una lucciola!"*, *"Due lucciole!"*, *"Tre lucciole!"*, etc.) accompanied by gender-neutral spoken praise (*"Ottimo lavoro!"*, *"Ben fatto!"*, *"Esatto!"*, *"Fantastico!"*, *"Evviva!"*).
   - Incorrect choices offer encouraging cues (*"Quasi! Guarda di nuovo quante lucciole brillano!"*, *"Riprova, guarda bene le lucine!"*) and step through visual hints.
   - Garden completion triggers joyful victory fanfare and Momo celebration cue (*"Che meraviglia! Tutte le lucciole sono felici e illuminate!"*).
4. **Verification**:
   - `tests/test_activity_luci_di_momo.py`: 11/11 tests PASS.
   - Full repository test suite: **1,307/1,307 tests PASS**, project validation PASS.

## Specchi Magici (`activities/specchi_magici`) Pre-Reader & Lilli Voice Overhaul (2026-08-25)

Overhauled **Specchi Magici** (`org.greia.specchi-magici`) to resolve the giant inactive "ANNULLA" button, eliminate text-only dependence, and implement Lilli's canonical cloned voice pipeline:
1. **Controls & Undo Button Fix**:
   - Replaced the oversized 140×76 text rectangle on the far right with a child-sized `↩️ ANNULLA` / `↩️ UNDO` capsule `(720, 492, 140, 50)` styled alongside the piece tray.
   - Disabled/dimmed in subtle dark slate when `len(session.undo_stack) == 0` (preventing child confusion on empty states) and brightly highlighted in vibrant amethyst + gold border when undo is actionable.
2. **Lilli Spoken Game Introduction & Replay (`🔊 ASCOLTA`)**:
   - Generated canonical voice assets using **Chatterbox Multilingual V3** (`mlx-community/chatterbox-multilingual-v3`) on Apple Silicon GPU with [`assets/audio/characters/canonical/v0.1/lilli-reference-v1.flac`](file:///Users/taio84/Works/Bimbe_GIOCHI/Greia%20OS/Greia/assets/audio/characters/canonical/v0.1/lilli-reference-v1.flac).
   - Welcome intro: *"Ciao! Guarda lo specchio magico e posiziona le forme uguali dall'altra parte!"* / *"Hello! Look in the magic mirror and place the matching shapes on the other side!"*.
   - Auto-played on activity startup and replayable anytime via the `[ 🔊 ASCOLTA ]` speech balloon button `(135, 492, 160, 50)` beside Lilli `(25, 435)`.
3. **Shape Pronunciation & Spoken Feedback**:
   - Tapping pieces in the tray pronounces their geometric shape name (*"Cerchio!"*, *"Quadrato!"*, *"Triangolo!"*, *"Semicerchio!"*).
   - Placing pieces correctly triggers gentle chime + randomized gender-neutral praise (*"Ottimo lavoro!"*, *"Ben fatto!"*, *"Esatto!"*, *"Fantastico!"*, *"Evviva!"*).
   - Incorrect placements trigger gentle wobble + encouraging prompt (*"Quasi! Guarda bene la distanza dallo specchio!"*, *"Riprova, sei quasi riuscito!"*).
   - Puzzle completion triggers fanfare + completion cue (*"Che bello specchio! Ecco il prossimo mosaico!"*).
4. **Verification**:
   - `test_activity_specchi_magici.py`: 14/14 tests PASS.
   - Full repository test suite: **1,306/1,306 tests PASS**, project validation PASS.

## Tre Carte Una Storia (`activities/tre_carte_una_storia`) Pre-Reader & Lilli Voice Overhaul (2026-08-25)

Overhauled **Tre Carte Una Storia** (`org.greia.tre-carte-una-storia`) to eliminate reliance on reading text and fully embrace the non-verbal, voice-first pre-reader standard:
1. **Lilli Spoken Game Introduction & Replay (`🔊 ASCOLTA`)**:
   - Synthesized using the canonical **Chatterbox Multilingual V3** (`mlx-community/chatterbox-multilingual-v3`) voice-cloning pipeline with official character reference master [`assets/audio/characters/canonical/v0.1/lilli-reference-v1.flac`](file:///Users/taio84/Works/Bimbe_GIOCHI/Greia%20OS/Greia/assets/audio/characters/canonical/v0.1/lilli-reference-v1.flac).
   - Welcome audio: *"Ciao! Metti in ordine le tre carte per raccontare la storia: prima, poi, e infine!"* / *"Hello! Put the three cards in order to tell the story: first, then, and last!"*.
   - Auto-played on activity startup once the initial frame is presented (`mark_activity_ready()`).
   - Added a prominent `[ 🔊 ASCOLTA ]` speech balloon button beside Lilli at the bottom-left `(130, 492, 160, 50)` so kids can tap Lilli or the button to hear the game explanation at any time.
2. **Step Order Audio & High-Contrast Sequence Tokens**:
   - Enhanced the 3 slot badges with high-contrast colored capsules: `1. PRIMA` (Green), `2. POI` (Orange), `3. INFINE` (Purple).
   - Tapping any slot plays step audio (`slot_1` / `slot_2` / `slot_3`).
3. **Gender-Neutral Praise & Encouraging Hints**:
   - Correct sequence check triggers chime + spoken praise: *"Ottimo lavoro! La storia è perfetta!"*, *"Ben fatto!"*, or *"Fantastico!"*.
   - Incorrect sequence triggers gentle wobble + spoken retry cue: *"Quasi! Guarda bene cosa succede prima!"*.
4. **Full Story Read-Aloud (70 Audio Clips Total)**:
   - Generated narration clips for all 8 narrative seeds × 3 cards (24 sentences per language) in 22050Hz LEI16 mono WAV with SHA-256 integrity manifest.
   - In Caption stage, tapping any preset caption row plays the sentence audio aloud to pre-readers.
5. **Clean Layout Geometry & Zero Overlaps**:
   - Redesigned the 1024×600 sequence layout with generous vertical margins (`y=75..385` for cards, `y=397..433` for step badges, `y=470..550` for controls), eliminating all control overlap.
6. **Verification**:
   - `test_activity_tre_carte_una_storia.py`: 11/11 tests PASS.
   - Full repository test suite: **1,304/1,304 tests PASS**, project validation PASS.

## Universal Gender-Neutral Speech & Praise Policy Enforcement (2026-08-25)

Enforced a strict, repository-wide rule across all audio assets, localized copy, code, and authoring guidelines:
- **Rule**: Never use gender-specific Italian adjectives (or other gender-specific adjectives) such as *"Bravissimo!"*, *"Bravissima!"*, *"Bravo!"*, or *"Brava!"*.
- **Canonical Praise Set**: Use universal, inclusive gender-neutral praise across all activities:
  - `Ottimo lavoro!` ("Great job!")
  - `Ben fatto!` ("Well done!")
  - `Esatto!` ("Exactly right!")
  - `Fantastico!` ("Fantastic!")
  - `Evviva!` ("Hooray!")
  - `Perfetto!` ("Perfect!")
  - `Super!` ("Super!")
  - `Che meraviglia!` ("Wonderful!")
- **Refactored & Regenerated Audio**:
  - `activities/casa_del_dieci`: Spoken verbal reinforcement updated to *"Ben fatto!"*, *"Esatto!"*, *"Ottimo lavoro!"*.
  - `activities/bottega_delle_misure`: Spoken verbal reinforcement updated to *"Ben fatto!"*, *"Esatto!"*, *"Ottimo lavoro!"*.
  - `activities/foresta_parole`: `bravissima.wav` replaced with `ben_fatto.wav` (*"Ben fatto!"*), Italian copy updated in `it.json` and `main.py`.
  - `activities/sillabe_magiche`: `bravissima.wav` replaced with `esatto.wav` (*"Esatto!"*), Italian copy updated in `it.json`, `main.py`, and test suite.
  - `activities/costruiamo_ponti`, `activities/memory_meraviglie`, `activities/orchestra_animali`, `activities/treno_numeri`: Replaced all gendered completion titles and subtitles with `"Ottimo lavoro!"` / `"Evviva!"`.
- **Guidelines Updated**:
  - `skills/greia-activity-authoring/VOICE_GENERATION.md` (§11.1)
  - `skills/greia-activity-authoring/PRE_READER_UX.md` (§4.1)
  - `skills/greia-activity-authoring/CORE.md` (§10.11)
- **Verification**:
  - Full test suite: **1,302/1,302 tests PASS**, project validation PASS, all 30 activities valid.

## Baia delle Orche (`activities/baia_delle_orche`) Physical Acer Deployment & Acceptance (2026-08-24)

`activities/baia_delle_orche` (Baia delle Orche / Orca Bay) is deployed to the physical Acer Aspire One test hardware (`greia-dev.local` / `192.168.68.104`) and verified live over SSH remote control:

1. **Remote Deployment & Developer Tooling**:
   - Enhanced `tools/greia_remote.py` to seamlessly handle SSH and sudo password authentication (`greia` / `greia`) via `SSH_ASKPASS` without external dependencies.
   - Configured launcher developer environment and deployed `baia_delle_orche` to `/opt/greia-os/activities/baia_delle_orche` and `/var/lib/greia-developer/activities/org.greia.baia-delle-orche`.
2. **Chatterbox Audio Generation**:
   - Fixed endpoint speech slicer with `trim_speech_ends()` to preserve natural ~400ms inter-sentence conversational pauses.
   - Generated and verified all 12 clips (6 Italian, 6 English) voiced by Tito (`tito_fast` / Matchbox) in 22050Hz LEI16 mono WAV with SHA-256 manifest.
3. **Child-Centric Visual UI & Tito Comic Speech Balloon**:
   - Replaced text box with a compact animated circular Tito avatar + white comic speech bubble with 3 animated pulsing dots (`• • •`).
   - Enlarged child-sized toolbar buttons (Pappa 46px fish, Coccole 36px heart, Giochi 36px ball, Canto 36px music notes, Notte 36px moon, Tito 46px avatar).
4. **Day/Night Simulation & Bioluminescence**:
   - Bioluminescent cyan outline rendering keeps orca silhouettes and white patches visible at night.
5. **Physical Hardware Evidence**:
   - Launched and verified on Acer Aspire One (1024x600, `LVDS1` display): launcher card selection, live swimming pod, food feeding, toy play with ball and hoop, Tito speech playback, and night mode toggle.

## Latest retained physical performance work

The reference Acer Aspire One launcher hover-transition tranche remains accepted at its measured scope.

On-device profiling found pointer hover transitions rebuilding the full 1024×600 scene at roughly **189.6 ms/frame (~5.3 fps)** while steady cached frames were already fast. The accepted `68899e9` tranche added:

- one-time display-format conversion of shared cached surfaces;
- a bounded working-set cache;
- pre-composited opaque scene backdrops;
- static-scene versus dynamic hover/launch cache-key separation;
- tile-level repair for hover/launch dynamics with full-rebuild fallback;
- backdrop-based profile badge repair;
- measurement-backed adaptive idle pacing.

Measured reference-Acer result:

```text
hover transition: 189.6 ms → 26.6 ms  (~5.3 → 37.6 fps)
full scene rebuild: 191.0 ms → 81.8 ms
steady cached frame: 3.46 ms → 3.34 ms
idle launcher CPU: ~10–11% → ~5–8%
card-sweep CPU avg: ~32% → ~16%
launcher RSS: ~153 MB → ~153 MB
```

On-device visual verification covered Collection Home, category grid, hover lift/title disclosure, focus/selection badge, pagination and rapid cross-card traversal without ghosting.

`docs/engineering/GREIA_PERFORMANCE_BEST_PRACTICES.md` is now the single accumulating performance manual for measured device cost, cache/alpha/invalidation rules, evidence discipline and case studies. The microphone tranche does not supersede or modify that performance work.

## Early-learning Activity Expansion: Complete Portfolio Acceptance (2026-08-24)

All 10 Early Learning Activities specified in `docs/plans/2026-08-24_EARLY_LEARNING_ACTIVITY_EXPANSION/` are fully implemented, visually overhauled, and verified under `make verify` (1,300/1,300 tests PASS; 30/30 activities valid):

1. **Luci di Momo (`org.greia.luci-di-momo`)**: Subitizing fireflies in enchanted twilight meadow, glowing multi-tiered moon, 3D lantern and choice cards with hover lift.
2. **La Casa del Dieci (`org.greia.casa-del-dieci`)**: Number bonds to 10 in a cozy storybook cottage with cobblestone path, chimney smoke, glowing windows, 3D buttons.
3. **La Bottega delle Misure (`org.greia.bottega-delle-misure`)**: Comparison and non-standard measurement in a warm carpenter workshop with wood walls, hanging scales, brass ruler, 3D satin gift boxes.
4. **Specchi Magici (`org.greia.specchi-magici`)**: Geometric symmetry and reflection in a royal velvet palace chamber, baroque gold frame, glowing symmetry beam, 3D gems, ghost piece preview.
5. **Festa delle Rime (`org.greia.festa-delle-rime`)**: Phonological rhyme matching at a festival night market, colorful bunting, hanging paper lanterns with tassels, 3D choice cards.
6. **Officina dei Suoni (`org.greia.officina-dei-suoni`)**: Initial phoneme and syllable sound workshop with acoustic pegboard, copper resonator tubes, synthesizer workbench, 3D wooden letter tiles and picture cards.
7. **La Posta di Leo (`org.greia.posta-di-leo`)**: Storybook postcard creation and stamp collecting with mahogany desk, green leather blotter mat with brass corner pins, 3D perforated postage stamps.
8. **Tre Carte, Una Storia (`org.greia.tre-carte-una-storia`)**: Story sequencing and caption authoring with 4 narrative seeds, audio narration, caption editor, 12-story gallery, and privacy-safe storage/events.
9. **Nanna delle Nuvolette (`org.greia.nanna-delle-nuvolette`)**: Toddler bedtime care with 3 cloud friends, 6 cozy blanket patterns, wicker star basket, yawning/sleeping animations, privacy-safe storage and `cloud.rest_completed` events.
10. **Morbidi Mostriciattoli (`org.greia.morbidi-mostriciattoli`)**: Soft monster creator with 6 body shapes, 8 colors, 6 eyes, 6 mouths, 6 tufts, 6 accessories, 24-recipe gallery with LRU thumbnail cache, squash-stretch preview animations, and privacy-safe `monster.portrait_created` events.

Universal UX & Pointer Overhaul:
- Continuous mouse cursor visibility enabled across all activities (`pygame.mouse.set_visible(True)`).
- Continuous `MOUSEMOTION` hover tracking across all cards, tabs, and buttons for immediate visual feedback and responsive mouse interaction.
- Flat programmer art completely replaced with high-contrast, warm, storybook-quality scenery, 3D beveled cards with drop shadows, and rich child UI.

## Early-learning Activity expansion: Casa del Dieci acceptance (2026-08-24)

`activities/casa_del_dieci` (La Casa del Dieci / The Ten House) number bonds Activity is fully implemented, verified, and accepted following `docs/agents/GREIA_EARLY_LEARNING_ACTIVITY_IMPLEMENTATION_RUNBOOK.md` and `skills/greia-activity-authoring/SKILL.md`.

- Architecture:
  - `ten_house_model.py`: Concrete 2x5 ten-frame representation with `OperationMode(COMPOSE, ADD, TAKE_AWAY, MISSING_PART)`, immutable `TenHouseChallenge`, deterministic factory with 6 unique challenges per set across L1–L5, between-set bounded adaptation, and one-shot `ten_house.room_completed` (milestone) and `ten_house.house_completed` (completion) events.
  - `ten_house_app.py`: Hybrid input orchestrator (Keyboard Left/Right/Up/Down navigation across 2x5 rooms and choices, Space/Enter activation; Pointer/Touch clicks; Home/ESC lifecycle), low-allocation state machine with brief wobble/transition states, and completion restart.
  - `ten_house_renderer.py`: 1024x600 cozy two-story house presentation with 10 large clickable rooms (glowing golden yellow when lit, slate blue when dark), Dani robot guide, dynamic prompt / equation bar, high-contrast choice cards and confirm button.
  - `ten_house_art.py`: Nighttime facade backdrop with stars/chimney, pre-scaled Dani character integration (`character.dani`).
  - `ten_house_audio.py`: Prepared nonverbal procedural synthesis (`toggle`, `correct`, `retry`, `complete`).
  - `ten_house_services.py`: Storage adapter for `casa_del_dieci.progress.v1` (bounded history <= 8) and event publisher.
- Evidence & Verification:
  - `tests/test_activity_casa_del_dieci.py`: 11/11 focused tests passing (model determinism, arithmetic invariants, room toggles, operation choices, adaptation, storage recovery, manifest, app keyboard/pointer integration, simulator supervisor lifecycle).
  - Platform contract tests reconciled: `test_activity_contract.py`, `test_first_party_activity_audience_metadata.py` (22 built-in activities), `test_first_party_activity_readiness.py`.
  - Full test suite `make verify`: **1,209 unit tests PASS**, project validation PASS, all 22 activities valid, footprint and shell checks green.
  - Package validation digest: `sha256 ea81b746fbc2d493d36fac1032ec8ed41b73dbef6bd14c04d2db63940a69dd8e`.
## Early-learning Activity expansion: Bottega delle Misure acceptance (2026-08-24)

`activities/bottega_delle_misure` (La Bottega delle Misure / The Measurement Workshop) comparison and non-standard unit measurement Activity is fully implemented, verified, and accepted following `docs/agents/GREIA_EARLY_LEARNING_ACTIVITY_IMPLEMENTATION_RUNBOOK.md` and `skills/greia-activity-authoring/SKILL.md`.

- Architecture:
  - `measure_model.py`: Domain comparison and unit measurement invariants (`Attribute(LENGTH, HEIGHT)`, `MeasureMode(COMPARE, ORDER, MEASURE, SHELF)`), immutable `MeasureItem` and `MeasureChallenge`, deterministic factory with 5 unique challenges per set across L1–L5, between-set bounded adaptation, and one-shot `measure.parcel_completed` (milestone) and `measure.delivery_completed` (completion) events.
  - `measure_app.py`: Pointer/touch interaction orchestrator with fail-closed system safe region validation, gentle wobble baseline assistance on errors, low-allocation state machine, and completion restart.
  - `measure_renderer.py`: 1024x600 workshop presentation with baseline-grounded parcels, measuring rail with numbered unit slots, Dani mascot, prompt text, and high-contrast numeric choice cards.
  - `measure_art.py`: Artisan workshop backdrop with back-wall tool shelf and wooden counter bench.
  - `measure_audio.py`: Prepared nonverbal procedural synthesis (`snap`, `correct`, `retry`, `complete`).
  - `measure_services.py`: Storage adapter for `bottega_delle_misure.progress.v1` (bounded history <= 8) and event publisher.
- Evidence & Verification:
  - `tests/test_activity_bottega_delle_misure.py`: 10/10 focused tests passing (model determinism, arithmetic invariants, compare/order/measure modes, adaptation, storage recovery, manifest, app pointer integration, simulator supervisor lifecycle).
  - Platform contract tests reconciled: `test_activity_contract.py`, `test_first_party_activity_audience_metadata.py` (23 built-in activities), `test_first_party_activity_readiness.py`.
  - Full test suite `make verify`: **1,219 unit tests PASS**, project validation PASS, all 23 activities valid, footprint and shell checks green.
  - Package validation digest: `sha256 4e7bde50746d1cfdad347b5e663fc95df658c67b367dcd16354112c5b8500bee`.
## Early-learning Activity expansion: Specchi Magici acceptance (2026-08-24)

`activities/specchi_magici` (Specchi Magici / Magic Mirrors) geometric symmetry and spatial reflection Activity is fully implemented, verified, and accepted following `docs/agents/GREIA_EARLY_LEARNING_ACTIVITY_IMPLEMENTATION_RUNBOOK.md` and `skills/greia-activity-authoring/SKILL.md`.

- Architecture:
  - `mirror_model.py`: Discrete 8x6 board model with vertical reflection axis between columns 3 and 4 (`mirror_col(c) = 7 - c`), shape reflection rules (`reflect_piece`) for `CIRCLE, SQUARE, TRIANGLE, SEMICIRCLE` ensuring exact involution (`reflect(reflect(p)) == p`), deterministic factory generating 6 unique puzzles per set across L1–L5, between-set bounded adaptation, and one-shot `mirror.mosaic_completed` (milestone) and `mirror.gallery_completed` (completion) events.
  - `mirror_app.py`: Pointer/touch interaction orchestrator with fail-closed system safe region validation, piece tray selection and placement, Activity-owned undo support, brief wobble/shimmer states, and completion restart.
  - `mirror_renderer.py`: 1024x600 enchanted chamber presentation with dual-tint 8x6 grid, glowing crystal mirror axis beam, bottom piece tray with selection halo, Undo button, and Lilli mascot.
  - `mirror_art.py`: Ambient crystal chamber backdrop, Lilli character loader (`character.lilli`), and crisp geometric shape renderers.
  - `mirror_audio.py`: Prepared nonverbal procedural synthesis (`place`, `correct`, `retry`, `complete`).
  - `mirror_services.py`: Storage adapter for `specchi_magici.progress.v1` (bounded history <= 8) and event publisher.
- Evidence & Verification:
  - `tests/test_activity_specchi_magici.py`: 12/12 focused tests passing (model determinism, reflection involution, rotation invariants, tray placement and undo, adaptation, storage recovery, manifest, app pointer integration, simulator supervisor lifecycle).
  - Platform contract tests reconciled: `test_activity_contract.py`, `test_first_party_activity_audience_metadata.py` (24 built-in activities), `test_first_party_activity_readiness.py`.
  - Full test suite `make verify`: **1,231 unit tests PASS**, project validation PASS, all 24 activities valid, footprint and shell checks green.
## Early-learning Activity expansion: Festa delle Rime acceptance (2026-08-24)

`activities/festa_delle_rime` (Festa delle Rime / Rhyme Festival) audio-first phonological awareness listening Activity is fully implemented, verified, and accepted following `docs/agents/GREIA_EARLY_LEARNING_ACTIVITY_IMPLEMENTATION_RUNBOOK.md` and `skills/greia-activity-authoring/SKILL.md`.

- Architecture:
  - `rhyme_content.py`: Bilingual phonological corpora (Italian and English rhyme pairs and alliteration families) matching `docs/reviews/2026-08-24_FESTA_DELLE_RIME_AUDIO_REVIEW.md` without printed text answer leakage.
  - `rhyme_model.py`: 8 balanced listening challenges per set across L1 (2-choice rhyme matching), L2 (3-choice rhyme matching), L3 (odd-one-out among 3 choices), and L4 (alliteration matching same initial sound), non-repeating pairs, between-set bounded adaptation, and one-shot `rhyme.match_completed` (milestone) and `rhyme.festival_completed` (completion) events.
  - `rhyme_audio.py`: Bounded `SpeechQueue` (maxlen $\le 4$, non-overlapping, distinct SFX and speech channels, cancellation on round change or stop), loading 64 reviewed LEI16 mono 22050Hz WAV assets and synthetic nonverbal chimes.
  - `rhyme_art.py`: Twilight meadow garden backdrop with hanging paper lanterns and pre-scaled Leo mascot (`character.leo`).
  - `rhyme_renderer.py`: 1024x600 festival presentation with top replay button `[ 🔊 ASCOLTA ]`, golden target lantern, distinct colored paper lantern choices, Leo mascot, and progress badge.
  - `rhyme_app.py`: Pointer/touch interaction orchestrator with safe-viewport validation, timed wobble on retry, celebration chime on success, terminal completion screen with 8 achievements.
  - `rhyme_services.py`: Storage adapter for `festa_delle_rime.progress.v1` (bounded history <= 8) and event publisher.
- Evidence & Verification:
  - `tests/test_activity_festa_delle_rime.py`: 11/11 focused tests passing (corpora completeness, factory determinism across 4 modes, bounded speech queue, round session invariants, adaptation, storage recovery, manifest, app integration, simulator supervisor lifecycle).
  - Platform contract tests reconciled: `test_activity_contract.py`, `test_first_party_activity_audience_metadata.py` (25 built-in activities), `test_first_party_activity_readiness.py`.
## Early-learning Activity expansion: Officina dei Suoni acceptance (2026-08-24)

`activities/officina_dei_suoni` (Officina dei Suoni / Sound Workshop) phoneme-grapheme association and word building Activity is fully implemented, verified, and accepted following `docs/agents/GREIA_EARLY_LEARNING_ACTIVITY_IMPLEMENTATION_RUNBOOK.md` and `skills/greia-activity-authoring/SKILL.md`.

- Architecture:
  - `sound_content.py`: Bilingual phonological corpora (Italian and English phonemes, uppercase/lowercase graphemes, and word structures) matching `docs/reviews/2026-08-24_OFFICINA_DEI_SUONI_AUDIO_REVIEW.md` without string length inference.
  - `sound_workshop_model.py`: 6 balanced challenges per set across L1 (find sound with 3 picture choices), L2 (initial letter selection with 3 letter tile choices), and L3 (build word with connected sound boxes `[ ? ][ E ][ L ][ A ]` and 3 letter tile choices), non-repeating items, between-set bounded adaptation, and one-shot `sound.word_completed` (milestone) and `sound.workshop_completed` (completion) events.
  - `sound_audio.py`: Bounded `SpeechQueue` (maxlen $\le 4$, non-overlapping, distinct SFX and speech channels, cancellation on round change or stop), loading 70 reviewed LEI16 mono 22050Hz WAV assets and synthetic nonverbal chimes.
  - `sound_art.py`: Acoustic workshop interior with glowing sound beads on rail, workbench, and pre-scaled Leo mascot (`character.leo`).
  - `sound_renderer.py`: 1024x600 workshop presentation with top replay button `[ 🔊 ASCOLTA ]`, target speaker / picture card, connected sound boxes, chunky wooden letter tiles, Leo mascot, and progress badge.
  - `sound_app.py`: Hybrid input orchestrator (Keyboard Left/Right/A/D navigation, Space/Enter activation, R replay; Pointer/Touch clicks; Home/ESC lifecycle), timed wobble on retry, celebration chime on success, terminal completion screen with 6 achievements.
  - `sound_services.py`: Storage adapter for `officina_dei_suoni.progress.v1` (bounded history <= 8) and event publisher.
- Evidence & Verification:
  - `tests/test_activity_officina_dei_suoni.py`: 11/11 focused tests passing (corpora completeness, factory determinism across 3 modes, bounded speech queue, round session invariants, adaptation, storage recovery, manifest, app hybrid keyboard/pointer integration, simulator supervisor lifecycle).
  - Platform contract tests reconciled: `test_activity_contract.py`, `test_first_party_activity_audience_metadata.py` (26 built-in activities), `test_first_party_activity_readiness.py`.
  - Full test suite `make verify`: **1,257 unit tests PASS**, project validation PASS, all 26 activities valid, footprint and shell checks green.
## Early-learning Activity expansion: Posta di Leo acceptance (2026-08-24)

`activities/posta_di_leo` (Posta di Leo / Leo's Post) meaningful emergent writing and postcard creator Activity is fully implemented, verified, and accepted following `docs/agents/GREIA_EARLY_LEARNING_ACTIVITY_IMPLEMENTATION_RUNBOOK.md` and `skills/greia-activity-authoring/SKILL.md`.

- Architecture:
  - `postcard_content.py`: 6 canonical character recipients (`momo`, `dani`, `lilli`, `leo`, `pina`, `tito`) and 6 picture stamps (`heart`, `sun`, `star`, `rainbow`, `flower`, `butterfly`).
  - `postcard_model.py`: Grapheme-safe Unicode cursor editing (atomic emoji ZWJ/skin tone/flags, Backspace/Delete, left/right arrow navigation, max 80 graphemes), `SavedPostcard` immutable records, and `PostcardLibrary` strictly capped at 20 cards without auto-eviction.
  - `postcard_services.py`: Storage adapter for `posta_di_leo.library.v1` (bounded at 20 cards, strict schema sanitization) and privacy-preserving `GreiaPostcardEvents` emitting `postcard.created` with `{"recipient": r_id, "stamp": stamp_id}` and `idempotency_key=f"posta-di-leo:{card_id}"` (strictly no child message text in event payload!).
  - `postcard_audio.py`: Procedural nonverbal tones for typing clicks, stamp thud, sending fanfare, delete swoop, and selection blip.
  - `postcard_art.py`: Warm wooden post office desk backdrop, circular character avatars, perforated scalloped stamps, and lined cream postcard paper.
  - `postcard_renderer.py`: 1024x600 composer layout (top recipient bar, left ruled writing canvas with blinking cursor, right stamp tray + address lines, bottom send/gallery/clear toolbar), gallery grid viewer, card preview modal, and polite full-mailbox sheet.
  - `postcard_app.py`: Text input orchestrator (`TEXTINPUT`, `KEYDOWN`, pointer/touch, home/ESC), save-before-event write invariant, gallery deletion confirmation modal, and ready state publication.
- Evidence & Verification:
  - `tests/test_activity_posta_di_leo.py`: 11/11 focused tests passing (atomic emoji/grapheme editing, 80-grapheme ceiling, empty-text stamp validity, 20-card library cap & no auto-eviction, storage recovery, manifest, app integration with privacy proof, full-dialog and gallery delete flow, simulator supervisor lifecycle).
  - Platform contract tests reconciled: `test_activity_contract.py`, `test_first_party_activity_audience_metadata.py` (27 built-in activities, open-ended creative list), `test_first_party_activity_readiness.py`.
## Early-learning Activity expansion: Tre Carte, Una Storia acceptance (2026-08-24)

`activities/tre_carte_una_storia` (Tre Carte, Una Storia / Three Cards, One Story) narrative sequencing and story caption Activity is fully implemented, verified, and accepted following `docs/agents/GREIA_EARLY_LEARNING_ACTIVITY_IMPLEMENTATION_RUNBOOK.md` and `skills/greia-activity-authoring/SKILL.md`.

- Architecture:
  - `story_cards_content.py`: 8 bilingual story seeds (`drawing`, `rain`, `kite`, `picnic`, `postcard`, `tower`, `cloud`, `spill`), each with 3 distinct card symbols and 3 narrative step captions.
  - `story_cards_model.py`: `StorySeed`, `StoryRound` with guaranteed non-solved initial shuffle, drag/tap/keyboard slot swapping, hint display on slot 0 after 2 errors, and `StoryLibrary` capped at 12 stories with strict no-auto-eviction policy.
  - `story_cards_services.py`: Storage adapter for `tre_carte_una_storia.library.v1` (bounded at 12 stories, strict deserialization validation) and privacy-preserving `GreiaStoryEvents` emitting `story.sequence_completed` milestone and `story.created` creation event with `{"seed": seed_id, "mode": caption_mode}` (strictly no child caption text in event payload!).
  - `story_cards_audio.py`: Procedural nonverbal tones for card swapping, correct sequence fanfare, hint wobble, and storybook save.
  - `story_cards_art.py`: Enchanted twilight meadow backdrop, open storybook slots (`Prima`, `Poi`, `Infine`), high-contrast picture card illustrations, and pre-scaled Lilli mascot (`character.lilli`).
  - `story_cards_renderer.py`: 1024x600 logical presentation (3 large card frames in puzzle stage, 3 top mini cards + 3 preset rows + custom text input box in caption stage, gallery grid viewer with modal reader and delete confirmation dialog, polite full-library limit sheet).
  - `story_cards_app.py`: Hybrid input orchestrator (Keyboard Left/Right/Space/1/2/3 navigation, typing in caption mode, Pointer/Touch clicks; Home/ESC lifecycle), save-before-event write invariant, and ready state publication.
- Evidence & Verification:
  - `tests/test_activity_tre_carte_una_storia.py`: 9/9 focused tests passing (8 valid story seeds, non-trivial initial shuffle, swap mechanics, error hint activation after 2 wrong checks, 12-story library cap & no auto-eviction, storage recovery, manifest, app integration with sequence event and privacy proof, simulator supervisor lifecycle).
  - Platform contract tests reconciled: `test_activity_contract.py`, `test_first_party_activity_audience_metadata.py` (28 built-in activities, open-ended creative list), `test_first_party_activity_readiness.py`.
  - Full test suite `make verify`: **1,284 unit tests PASS**, project validation PASS, all 28 activities valid, footprint and shell checks green.
  - Package validation digest: `sha256 c077724e4806a7bc9266789074b5abbc867449ef8ccb56278c0cbb815e0410a6`.
  - Visual review executed for Italian and English locales (Sequence stage, Sequence hint, Caption stage with preset selection, Gallery grid, Story modal reader, English custom caption).


## Built-in Activity Refinement: Baia delle Orche Visual Overhaul & Night Bioluminescence (2026-08-24)

`activities/baia_delle_orche` (Baia delle Orche / Orca Bay) cetacean sanctuary and creation/nurture Activity has undergone full visual redesign and physical orientation polish:

- Architecture:
  - `orca_model.py`: 3-member pod model (`kiko` baby, `luna` acrobat, `oskar` elder) with dynamic pitch tracking, parabolic breach physics with natural dive curves ($-20^\circ \rightarrow +20^\circ$), gentle cuddle rocking ($\pm 6^\circ$), and food/toy interactions.
  - `orca_renderer.py`: Layered Arctic fjord presentation, high-contrast bioluminescent night ocean with cyan caustics, and cached anti-aliased sprite blitting with quantized rotozoom rotation.
  - `assets/runtime/`: 12 high-resolution, anti-aliased, storybook character sprites (`orca_{baby|acrobat|elder}_{day|night|happy}.png`) with sleek proportioned white underbellies, curved falcate dorsal fins, rounded cetacean flukes, and electric-cyan night rim lighting (`#38d7ff`).
  - `orca_audio.py`: Procedural cetacean harmonics, chimes, purrs, splashes, and bubbles.
  - `orca_services.py`: Profile-scoped storage and milestone event publisher.
- Evidence & Verification:
  - `tests/test_activity_baia_delle_orche.py`: 12/12 focused tests passing.
  - Package validation digest: `PASS org.greia.baia-delle-orche 0.1.0`.
  - Visual verification in simulator across Day, Night, Feed, Cuddle, Leap, and Song modes.

## Contributor engineering skills integration (2026-08-23)

The measured performance lessons and existing OOP/polymorphism foundations are now integrated into the contributor-facing skills rather than remaining specialist documentation only.

Created:

```text
skills/greia-activity-authoring/ENGINEERING.md
skills/greia-os-work/SKILL.md
```

The Activity engineering companion is mandatory for new/substantively changed first-party Activity implementation. It makes `main.py` a thin composition/bootstrap boundary, defines pragmatic module/class decomposition and OOP/polymorphism/reuse protocols, and operationalizes the Acer performance rules: no heavyweight IO/decode/scale/font/device/subprocess/config/storage work in hot loops, bounded caches with invalidation, pre-rendered static presentation, dirty rendering, bounded animations and fast-path equivalence testing.

The OS work skill is the practical contributor router for architecture ownership, extension seams, reusable class placement, OOP/polymorphism, low-resource performance, UI/display/input authority, audio/microphone boundaries, simulator policy, install/update/trust, comments/docstrings, documentation maintenance and evidence discipline.

`AGENTS.md` now requires the OS skill for substantive platform/Shell/Parent/installer/simulator/build/runtime/hardware-service work and requires future changes to keep it synchronized. The performance manual records Activity-skill integration as complete. Durable review: `docs/reviews/2026-08-23_ENGINEERING_SKILLS_INTEGRATION.md`.

## Acer boot contract and boot screen physical acceptance (2026-08-23)

The physical Acer Aspire One boot contract reconciliation and boot screen test protocol (`GREIA_ACER_BOOT_CONTRACT_AND_BOOT_SCREEN_TEST_PROTOCOL.md`) has been fully executed and accepted on hardware.

- **Target host:** Acer Aspire One (`greia-dev.local`, `legacy-x86-i686-dev`, Linux `6.1.0-52-686 i686`).
- **Source contract reconciliation:** `src/greia_platform/boot_contract.py` now enforces the postmortem contract: developer builds require `panic=0` (no reboot loop on failure), `console=tty1`, `loglevel=4`, `systemd.show_status=true`, `rd.systemd.show_status=true`, `udev.log_priority=4`, `vt.global_cursor_default=1`, and forbid release arguments (`quiet`, `splash`, `loglevel=0`, `console=null`, `panic=5`, `systemd.show_status=false`, `rd.systemd.show_status=false`, `udev.log_priority=3`, `vt.global_cursor_default=0`).
- **Pre-change state & backup:** Full backup created at `/var/lib/greia/boot-acceptance-backup-20260823-160333` containing previous `10_greia_appliance`, `grub.cfg`, `greia-theme.txt`, `greia-boot-logo.png`, `boot-logo.ppm`, and `greia-fb-splash`.
- **Initramfs storage module preservation:** Verified `/boot/initrd.img-6.1.0-52-686` retains critical storage drivers before and after regeneration: `ahci.ko`, `libahci.ko`, `libata.ko`, `acard-ahci.ko`, `sd_mod.ko`.
- **Target compilation:** `greia-fb-splash.c` compiled directly on target using `klcc -static -Os -s` producing a native i386 ELF32 executable installed to `/usr/lib/greia-boot/greia-fb-splash` and packaged into the initramfs hooks (`init-top`, `local-premount`, `init-bottom`).
- **GRUB generation & contract validation:** GRUB configuration generated via `update-grub` on the Acer and validated remotely with `PYTHONPATH=src python3 -m greia_platform.boot_contract ... --developer` passing 1 kernel command line. Running kernel command line verified:
  ```text
  BOOT_IMAGE=/vmlinuz root=UUID=cdc4dc87-acde-4bf9-bad1-0ac2b413446f ro loglevel=4 systemd.show_status=true rd.systemd.show_status=true udev.log_priority=4 vt.global_cursor_default=1 console=tty1 panic=0 systemd.crash_shell=no systemd.crash_chvt=0 consoleblank=0
  ```
- **Safety gates & automatic SSH recovery:** Mandatory SSH recovery gate passed prior to reboot; second independent fresh SSH connection confirmed (`GREIA_SSH_PRE_REBOOT_OK`). Machine rebooted cleanly with `systemctl reboot`. Automatic SSH password login (`greia/greia`) succeeded on attempt 1 post-boot (`GREIA_SSH_POST_BOOT_OK`).
- **Launcher & services:** `greia-launcher.service` active with 0 failed units. Service restarted cleanly and verified reachable via SSH (`GREIA_SSH_AFTER_LAUNCHER_RESTART_OK`). Developer remote marker `/etc/greia-os/developer-remote` preserved throughout.
- **Verification evidence:** 73/73 focused boot tests PASSED (`test_boot_contract`, `test_boot_diagnostics_hardening`, `test_boot_animation_contract`, `test_boot_experience_contract`, `test_boot_progress_contract`, `test_launcher_boot_fallback`, `test_grub_security`). Full repository gate `make verify` PASSED (1,089 unit tests OK, 19/19 activities valid). Stored evidence in `tmp/boot-contract-acer-acceptance/`.

## Clinica Cuccioli Activity architecture calibration (2026-08-23)

`activities/clinica_cuccioli` is the first real calibration of the strengthened Activity engineering rules. It was deliberately selected because it required **no new generated character voices** while its previous ~33.5 KB `main.py` mixed gameplay state, random treatment generation, persistence, event publication, procedural SFX synthesis, input, particles and all rendering.

The refactor now separates:

```text
main.py                 thin composition root
clinic_model.py         ClinicSession / TreatmentResult domain invariants
clinic_app.py           lifecycle + semantic input orchestration
clinic_renderer.py      prepared/cached presentation + bounded transient FX
clinic_art.py           stateless procedural drawing helpers
clinic_audio.py         prepared procedural SFX owner behind ClinicAudioPort
clinic_services.py      Greia storage/event adapters behind narrow ports
```

The calibration also found and intentionally repaired real contract/behavior drift hidden inside the monolith:

- `activity.toml` declared `vet.treatment_applied` / `vet.patient_healed`, while the old code emitted undeclared `clinic.patient_cured`; event publication now uses only the manifest-declared IDs;
- palette clicks could complete a later treatment out of order while patient taps enforced the next visible step; all input paths now delegate to one `ClinicSession.use_tool(...)` rule;
- the Activity declared Italian + English and carried localization bundles, but tool/victory UI remained hard-coded Italian; those visible labels now resolve through `LocalizedResources`.

Source-level performance structure now includes a pre-rendered opaque clinic backdrop, finite cached localized tool labels, current-value star text caching, a 96-particle explicit bound, one-time procedural SFX synthesis, and a victory modal that pays the full-screen alpha composition once then freezes to an opaque reusable frame. These are **SOURCE architecture improvements only**; no Acer/Pi speedup is claimed without measurement.

New provider-free tests are authored in `tests/test_clinica_cuccioli_refactor.py` for domain sequencing/session completion and manifest-to-event consistency. They have **not executed in this GitHub editing environment**. The durable review and exact simulator/local verification checklist are in:

```text
docs/reviews/2026-08-23_CLINICA_CUCCIOLI_ARCHITECTURE_CALIBRATION.md
```

The real refactor exposed reusable lessons, so the Activity skill now also contains:

```text
skills/greia-activity-authoring/REFACTORING.md
```

Structural refactors must inventory manifest/runtime/storage/event/localization/input/audio behavior before moving code, classify intentional changes as structural preservation / contract repair / behavior fix / performance structure, and normally extract pure domain truth before platform adapters, presentation ownership, application coordination and finally the thin composition root.

R7 remains the blocking platform phase; this parallel Activity-quality calibration does not change R7 status.

## Nascondino nel Bosco Activity refactoring & physical Acer performance calibration (2026-08-24)

`activities/nascondino_bosco` (Woodland Hide & Seek) had critical performance and visual composition defects on physical hardware:
- **Root cause 1 (performance)**: Re-rendered 15 SVG/PNG scene layers from scratch twice every frame at 30 Hz with software alpha blending (including 1024×512 sunlight rays and 1024×256 fog strips), resulting in physical Acer Atom execution at **505.35 ms/frame (2.0 fps)**.
- **Root cause 2 (visual composition)**: Hardcoded spot coordinates (such as a pine tree at `y=210` in the sky) and drew crude procedural shapes on top of the vector scene instead of grounding hiding spots to natural scene props.
- **Root cause 3 (architecture)**: 714-line monolith executing dynamic font rendering and per-frame fullscreen alpha blending on victory.

The refactor separated the Activity into clean, cohesive modules:
```text
main.py                 thin composition root + test compatibility exports (ANIMALS, SEASONS, WoodlandAudio, SPOTS)
woodland_model.py       AnimalDefinition / HidingSpotDefinition / WoodlandGameState domain invariants
woodland_app.py         lifecycle + semantic input + PygameCompletionScreen terminal victory integration
woodland_renderer.py    one-pass active game compositor + responsive HUD layout (normal/large/compact)
woodland_art.py         pre-rendered background baking + cached animal portraits + grounded clue animations
woodland_audio.py       synthesized PCM sound effects (rustle, pop, win)
```

**Measured physical Acer Aspire One results:**
- Pre-rendered background blit: **1.88 ms** (530 fps capability)
- Active frame render time: **505.35 ms → 9.05 ms** (**55× speedup**, locked at 30 fps with ~27% CPU margin)
- Test suite: `tests/test_activity_nascondino_bosco.py` (9/9 PASS); full suite **1,142 tests PASS**
- **Physical Hardware Live Deployment (`greia-dev.local`)**:
  - Successfully deployed all updated source and activities to Acer Aspire One (`greia-dev.local`).
  - Corrected tree hollow alignment in `woodland_art.py` and `woodland_model.py`: centered the illustrated hollow directly onto the brown oak trunk geometry (`cx=146, cy=398`), with warm wooden rim chamfer, bark collar shadow, and deep interior cavity.
  - Verified live on physical Acer display: Profile Picker (Explorer) -> Collection Home -> Esplora -> Nascondino nel Bosco launch. Live screenshot confirms animal peeking directly from the centered tree hollow with zero visual disconnect, smooth 30 FPS rendering, and full interactivity.
  - All 1,153 unit tests passing (`make verify` PASS).
- **Simulator End-to-End Verification**: Tested via `greia_simulator.child_shell` and `greia_simulator_ctl.py` at 1024×600 in Italian:
  1. Selected profile Explorer → navigated Collection Home → opened `Esplora` → launched `Nascondino nel Bosco`.
  2. Verified active gameplay rendering: mascot on tree bough, target animal HUD ("SCOIATTOLO", "VOLPE"), 5 grounded spots with peeking animations, responsive star score increments upon discovering animals.
  3. Verified terminal victory: upon completing 4 animal searches, `PygameCompletionScreen` displays opaque victory frame ("TROVATI TUTTI!", "Tutti gli animaletti sono felici!", 4 gold celebration medals, and green "GIOCA ANCORA" button).
  4. Verified restart & exit: clicking "GIOCA ANCORA" (`primary_contains`) immediately starts a fresh round with new animal positions and accumulated star score; clicking protected Home button (`(36, 36)`) returns cleanly to the Launcher shell.
  5. Fixed `primary_action_rect` attribute error on `PygameCompletionScreen` by replacing it with canonical `primary_contains((mx, my))`.

## Activity top space reclamation and painting performance optimization (2026-08-24)

Reclaimed ~100px of wasted vertical screen space across first-party creation activities and massively boosted Painting (Drawing) render performance:
- **Geometry & Top Bar Integration**:
  - `ChildUiMetrics.activity_toolbar_button` now embeds Activity toolbar buttons directly into the top bar alongside platform-owned Home/Back system chrome (`x >= chrome.protected_region.right + gap`), vertically centered in the top bar (`y = (top_bar_height - button_size) // 2`).
  - `ChildUiMetrics.activity_content_rect` starts content immediately below the top bar (~80px instead of ~178px).
  - Reclaimed ~98px of vertical drawing/writing space on 1024×600 screens:
    - Painting (Drawing) canvas height: **326px → 420px (+28.8% usable canvas)**
    - Writing editor height: **404px → 498px (+23.3% usable editor)**
- **Painting Performance Optimization**:
  - Pre-scaled and cached all tool button icons, color dish wells, brush size buttons, and gallery card frames on initialization / size updates, completely eliminating all 17 per-frame `pygame.transform.smoothscale()` calls (over 510 software bilinear rescales/second on CPU).
  - Pre-rendered static studio background onto a dedicated display-format Surface.
  - Pre-instantiated status fonts and pre-rendered status label surfaces (`"Salvo"`, `"Salva..."`, `"Errore"`).
  - Benchmarked render time: dropped from **2.28 ms/frame to 1.20 ms/frame on macOS** (and eliminating heavy CPU utilization on Atom/ARM floor).
- **Tests & Simulator Verification**:
  - `test_activity_ui.py` (8/8 PASS): verified zero overlap with system chrome protected region across all resolutions and interface sizes.
  - `test_core_activity_system_safe_ui.py` (3/3 PASS) and `test_core_creation_activities.py` (16/16 PASS).
  - Full automated functional tests for drawing, erasing, undo, color picking, brush resizing, gallery, text editing, and emoji picking passed cleanly.
  - Multi-resolution simulator visual evidence across 1024×600, 800×600, 1280×720, 1366×768, 1920×1080 and Compact/Normal/Large interface sizes captured in `tmp/simulator_evidence/`.

## Labirinto Magico fullscreen expansion, extreme complexity & zero-allocation performance overhaul (2026-08-24)

Overhauled `org.greia.labirinto-magico` (Magical Labyrinth):
- **On-Screen Arrow Controls Removed**: Deleted the cramped right-side D-pad arrow buttons to allow the maze to occupy the entire viewport (~2.5× surface area).
- **Fullscreen Layout**: Centered the maze grid in the available area (`~988×504` on 1024×600) beneath a streamlined top bar HUD (Star score pill, Difficulty level button, World theme button, New Maze button) respecting platform-owned Home chrome.
- **Extreme Complexity**: Expanded difficulty to 9 progressive levels from toddler-friendly `13×9` up to an intricate **89×41** grid ("Infinito") with 35 collectible crystal stars and hundreds of labyrinthine branches.
- **Sliding Continuous Movement & Click-to-Move**: Implemented sliding movement (moving at 18 cells/s until hitting a wall, reaching an intersection/crossing with >2 choices, or reaching the exit portal) for arrow keys, WASD, and gamepad D-pad, plus click-to-move cardinal impulse towards click position without pathfinding.
- **Zero-Allocation Performance Overhaul**:
  - Pre-rendered and cached 16 discrete portal rotation angles (`get_portal_rotation_frames`), eliminating per-frame floating-point `pygame.transform.rotate()` allocations.
  - Pre-cached flipped Tito adventurer sprites (`get_flipped_asset`).
  - Pre-cached ambient particle alpha surfaces (`get_particle_surface`), eliminating 25 per-frame `pygame.Surface(..., pygame.SRCALPHA)` allocations.
  - Pre-cached FreeType typography rendering across all UI buttons and HUD counters (`_text_cache`).
  - Pre-baked static maze background surface on generation/biome switch.
  - Render throughput measured at **0.598 ms/frame** (~1,670 FPS) even on the 89×41 Infinito grid.
- **Architecture**: Modular decomposition into `maze_model.py`, `maze_art.py`, `maze_audio.py`, `maze_renderer.py`, `maze_app.py`, and `main.py`.
- **Tests & Simulator Verification**:
  - `tests/test_activity_labirinto_magico.py` (11/11 PASS).
  - Full suite: **1,176 tests PASS**.
  - Verified live inside the Activity Simulator (`greia_simulator.child_shell` + `tools/greia_simulator_ctl.py`) across navigation, sliding moves, *Infinito* (89×41) scaling, and protected Home button return.

## Activity terminal freeze repair P2-S1 — PARTIAL/BLOCKED at Acer deployment (2026-08-24)

The three affected terminal paths are now source-migrated to the existing `PygameCompletionScreen` owner: `activities/labirinto_magico/maze_app.py` + `maze_renderer.py`, `activities/piccola_serra/main.py`, and `activities/treno_numeri/main.py`. Active simulation/render stops in terminal state; one prepared opaque frame is presented and reused until semantic invalidation; terminal restart and protected Home/STOP handling remain platform-aligned. Treno emits only declared `train.station_completed` / `train.journey_completed` facts with idempotency keys. Focused regressions are in `tests/test_activity_terminal_rendering.py`.

Local evidence is complete at `Lunacy/runs/activity-terminal-freeze-acer/evidence/p2-s1-local-verification.md`: focused terminal suite 4/4 PASS, three Activity validations PASS, and syntax compilation PASS. `make verify` was required and executed but is not green in this macOS environment (925 tests, 53 errors, including missing `pygame`, `PIL`, and `pytest` plus unrelated existing failures); no source claim is based on those unavailable modules.

The device gate is blocked. Strict-host-key interactive fallback reached the Acer, but the approved `greia-devctl ... deploy-activity ... --replace-system` path rejects the exact package because manifests use opaque IDs (`org.greia.labirinto-magico`, etc.) while installed built-in directories use snake_case (`labirinto_magico`, etc.). No direct root move/symlink, manifest mutation, or trust-bypassing duplicate was used. See `Lunacy/runs/activity-terminal-freeze-acer/evidence/p2-s1-device-gate.md` and `decisions/p2-s1-deployment-mapping.md`.

All Activity/test changes are present in concurrent externally created and already-pushed `5dfe553` (`main` = `origin/main`); history was not amended or reset. No Acer source hashes/screenshots/process samples/win→idle→restart→Home proof are claimed. Next exact step: separately authorize and repair the deployment owner's manifest-ID→installed-directory resolution, add focused duplicate/missing/backup/restore tests, then repeat the three-Activity physical protocol before P2 acceptance.

## Il Volo del Draghetto performance, arrow input & endless flight overhaul (2026-08-24)

`activities/volo_draghetto` (Il Volo del Draghetto / Dragon Flight) had severe performance issues on the physical Acer Aspire One (Atom N270):
- **Hardware Bottleneck**: Un-converted `1280×220` transparent `SRCALPHA` surface blits across the frame caused CPU-bound floating-point software alpha-blending in SDL, taking **53.63 ms/frame** on the Atom N270 and dragging total frame time to **73.04 ms (~13 FPS)**.
- **Colorkey Architecture**: Replaced full-frame alpha blits with display-converted colorkey surfaces (`_make_colorkey_surface` with `.convert()` and `.set_colorkey((1, 2, 3))`) and 3 independent pre-rendered storybook cumulus clouds at parallax offsets (`0.23 ms` total).
- **Physical Performance on Acer**: Per-frame render time dropped from **73.04 ms** to **6.19 ms** (a **12× speedup** / ~161 FPS rendering headroom, running locked at 30 FPS with ~20% CPU load).
- **Responsive Arrow Controls**: Implemented direct, snappy altitude control for arrow keys (`Up`/`Down`/`W`/`S` in both continuous hold and discrete steps), right-arrow turbo dash, and `Tab`/`L`/button accessory toggles (`👑 Look`).
- **Endless Flight & Clean HUD**: Removed the 20-star victory interruption and all distracting text toast banners. The dragon flies endlessly with cumulative stars (`⭐ 228 🏆 3495`), 10-star fanfare audio cues, and continuous scenery/obstacle streaming.
- **Decomposition**: Modular architecture across `dragon_model.py`, `dragon_art.py`, `dragon_audio.py`, `dragon_renderer.py`, `dragon_app.py`, and thin `main.py`. Tests: `tests/test_activity_volo_draghetto.py` (10/10 PASS). Full suite `make verify`: **1,167 tests PASS**. Deployed and verified on physical Acer hardware (`greia-dev.local`).

## Baia delle Orche Activity creation (2026-08-24)

Created the first-party Activity `activities/baia_delle_orche` (**Baia delle Orche / Orca Bay**, `org.greia.baia-delle-orche`):
- **Core Experience**: A delightful Arctic fjord marine cove featuring 3 lovable orcas (baby pup *Kiko*, agile acrobat *Luna*, and gentle elder *Oskar*) with zero-text child interaction across 5 rich modes:
  1. 🐟 **Nutri & Lancia**: Toss and feed delicious silver herring, pink salmon, glowing squid, and ice treats; orcas breach and dive to catch them with crisp nibbles.
  2. ❤️ **Coccole & Cura**: Stroke/brush and tickle orca bellies; orcas roll onto their white tummies, blush, wag flukes, and spray mist hearts from their blowholes with happy purrs and whistles.
  3. 🎪 **Giochi & Acrobazie**: Bouncy floating beach ball physics (orcas bump and tail-flick it across the bay) and rainbow jump rings for high graceful acrobatic breaches.
  4. 🎶 **Canto delle Orche**: 4 floating musical sea bells / crystal chimes with melodic call-and-response from the orcas using synthesized cetacean whistles and echolocation click bursts.
  5. 🌌 **Giorno & Aurora Notte**: Toggle between sunny crystal fjord and magical Northern Lights (Aurora Borealis) night with glowing bioluminescence and peaceful bedtime breathing.
- **Clean OOP Decomposition**:
  - `main.py`: Thin composition root (< 70 lines).
  - `orca_app.py`: Top-level lifecycle, input routing, display presentation, authoritative `mark_activity_ready()` after first frame.
  - `orca_model.py`: Domain entities (`OrcaEntity`, `FoodEntity`, `ToyEntity`, `ParticleEntity`, `OrcaPod`) with full state machines and buoyant physics.
  - `orca_renderer.py`: Bounded static scenery caches, 1024×600 reference canvas, layered composition, high-contrast child UI toolbar ($\ge 80\times 72\text{px}$).
  - `orca_audio.py`: Pure synthetic audio generation for orca whistles, clicks, splashes, nibbles, purrs, bounces, and chimes.
  - `orca_services.py`: Storage progress adapter and platform milestone event emitter (`orca.fed`, `orca.cuddled`, `orca.acrobatics_performed`, `orca.song_completed`).
- **Validation & Tests**:
  - `tools/validate_activity.py activities/baia_delle_orche` PASS.
  - `tools/validate_project.py` PASS (`activities=20`).
  - `tests/test_activity_baia_delle_orche.py` (12/12 PASS).
  - `tests/test_first_party_activity_readiness.py` & `tests/test_first_party_activity_audience_metadata.py` PASS.
  - Full test suite: **1,187/1,187 tests PASS**.

## Parent Settings overlay tranche (2026-08-23, `3c3e91f`)

The chord-opened (hold S+T) on-device Parent Settings panel had two owner-reported defects, both fixed and verified on the reference Acer:

- **Password field dead**: SDL delivers `TEXTINPUT` only while text input is active, and parent-panel entry never activated it — typed characters vanished while Enter/Backspace still worked. Entry/exit now flows through `_enter_parent_panel`/`_exit_parent_panel`, which manage text input and clear stale input events at every transition site in both production and legacy run loops.
- **UI-thread stalls**: SSH status (two systemctl subprocesses + route probe per call) was invoked per-frame by the Info tab, blocked mid-draw every ~2 s on the SSH tab and was double-polled by `drain()`. Status refreshes now run on a worker thread into a queue drained exactly like Wi-Fi results; tabs render cached snapshots with honest placeholders; toggles cache their returned status; Audio mic-gain reads are throttled; the full-screen dim is composited once per picker-state change (`ParentSettingsOverlay.dim_surface()` + `draw_backdrop=False`) instead of alpha-blended every redraw.

Physical verification sequence: injected 5 s chord → auth dialog → typed dots visible → unlock → Language/SSH/Remote-and-Pairing tabs all render (device IP shown from cached status) → close restores the picker. Info/SSH tabs idle at **6–9 % launcher CPU** (previously subprocess-per-frame). Tests: `tests/test_parent_panel_input_lifecycle.py` (4 PASS).

## Achievement presentation, Activity victory contracts & progression simulator acceptance (2026-08-23)

The complete interactive acceptance protocol from `Greia_Achievement_Activity_Simulator_Acceptance_2026-08-23.md` was executed and **ACCEPTED** at the then-tested source state (`850bf6d` reported by the local-agent completion tranche).

Evidence captured in `./tmp/greia-achievement-simulator-acceptance/` includes:
- **Test A:** Empty Badge Library and collection routes (0/6 unlocked, 6 locked, secret `greia.stars.constellation` hidden).
- **Test B:** Clinica Cuccioli session: out-of-order treatment rejection, 5 patients healed, shared victory card, `First Friend Helped` celebratory popup, NEW/seen badge state, and verified `star=1` once-per-session award.
- **Test C:** Child shell restart persistence: badge and star balances preserved.
- **Test D:** Memory of Wonders completion: shared victory screen, `Memory in Action` badge, `star=2`, count 2/6.
- **Test E:** Costruiamo Ponti (3 levels in 1 session): `Bridge Builder` badge, `star=3` (strictly 1 star gained despite 3 level completions), count 3/6.
- **Test F:** Star milestone at 5 stars: `A Handful of Stars` unlocked, count 4/6, secret badge hidden.
- **Test G:** Profile isolation: second profile `BadgeTest2` starts with 0/6 badges and 0 stars; original profile restores 4/6 badges and 5 stars.
- **Test H:** Responsive smoke across 5 viewports (`1024x600 norm/large`, `1280x800`, `1366x768 compact`, `1920x1080`) plus Activity smoke checks.
- **Test I:** Static repaint sanity check: 0 frame repaints during 5s idle display.

Full Acceptance Ledger recorded in `tmp/greia-achievement-simulator-acceptance/results.md`.

## Achievement localization and Activity-themed art — post-acceptance source tranche (2026-08-24)

After the accepted simulator run, the owner identified that an Italian simulated Greia still opened the Badge Library with English Shell chrome. Root cause: the achievement presentation path could successfully read an empty installed-language store and receive its English default before consulting the simulator's explicit `GREIA_PROFILE_LOCALE` / `GREIA_DEVICE_LOCALE` context.

That presentation bug has been repaired through:

```text
src/greia_launcher/achievement_localization.py
src/greia_launcher/achievement_presentation.py
```

The achievement Shell now resolves explicit launch locale before installed-store fallback and owns localized Badge Library/celebration chrome for the current Greia language registry rather than using `if Italian else English` presentation branches.

The visual award renderer has also moved from one generic medallion shape to a coherent Greia family:

```text
bronze / silver -> medal + ribbons
gold            -> trophy cup
special/secret  -> rosette / constellation treatment
```

The owner then chose a layered Activity-art model: Activities may optionally contribute content-specific artwork while Greia retains global achievement authority.

Implemented contract:

```text
src/greia_platform/achievement_art.py
    bounded package-local Activity emblem declarations and validation

activities/*/activity.toml [achievement_art]
    optional decorative contribution only

runtime/achievement-policy.toml art = {...}
    explicit Greia admission of one Activity emblem into one platform achievement

src/greia_platform/achievements.py
    trusted policy admission; no Activity unlock authority

src/greia_platform/pygame_achievements.py
    Greia frame + admitted Activity emblem, with icon_id fail-soft fallback
```

V1 Activity emblems are static square PNGs, max 512 KiB, 32–1024 px, recommended 256×256, package-local, non-symlink and text-free. A SHA-256 content fingerprint participates in badge cache identity so updated artwork at the same package path invalidates prepared presentation cleanly.

Clinic, Memory and Bridges now opt in using their existing package icons as initial `activity` emblems, and the platform achievement policy explicitly admits those contributions for their Activity-specific badges. Greia-wide Star achievements remain platform-art-only. The infrastructure supports multiple purpose-made emblem IDs per Activity; future Activity authoring should generate dedicated content-specific emblems where they improve the result rather than treating launcher-icon reuse as the final art ceiling.

Authority remains:

> Activities report facts and may offer art. Greia decides rewards, achievements, tier/frame, localization, persistence, visibility and celebration.

Parent-installed content does not automatically add global badges merely by declaring artwork.

Durable contracts/review:

```text
docs/design/GREIA_ACTIVITY_ACHIEVEMENT_ART.md
docs/design/GREIA_ACHIEVEMENTS_AND_BADGE_LIBRARY.md
skills/greia-activity-authoring/ACHIEVEMENTS.md
docs/reviews/2026-08-24_ACTIVITY_THEMED_ACHIEVEMENT_ART.md
```

### Current source-test boundary

The earlier local-agent result remains:

```text
Ran 1110 tests in 20.284s
OK (0 failures, 0 errors)
```

That is retained evidence for the earlier accepted source state. **It is not automatically evidence for the newer localization / award-art / Activity-emblem commits.**

New provider-free tests have been authored in:

```text
tests/test_achievement_localization.py
tests/test_achievement_art.py
tests/test_achievement_emblem_cache.py
tests/test_pygame_achievements.py
```

They have not been executed in the GitHub editing environment. Current-head PASS requires local execution. No hosted GitHub Actions were queried or run.

---

# 2. Parent HTML client — runtime pin retained, microphone candidate ready for local repin

Greia still pins the previously tested external Parent client at:

```text
repository: frozenpepper/Greia-Parent-App-Html
revision:   7ff7e318eb246618dab26939ba086999864538ce
runtime:    /usr/share/greia-parent-app
state:      source-pinned-not-yet-vendored
```

Pin authorities:

```text
runtime/parent-app-client.toml
runtime/parent-app-client.manifest.json
```

That integrity manifest contains the established 12 runtime files:

```text
index.html
styles/app.css
src/api.js
src/app.js
src/credential_store.js
src/demo_api.js
src/state.js
src/ui.js
src/views_helpers.js
src/views_home_children.js
src/views_activities.js
src/views_device.js
```

The Parent source repository now has a newer microphone-processing candidate at:

```text
cdea281a1848d1372a18822a559dc15494e749b0
```

It adds:

- `GET/PUT /settings/audio` and reset client methods;
- capability-gated audio state loading/refresh;
- a **Microphone cleanup** card;
- **Improve microphone sound** as the normal/default control;
- **Enhanced noise reduction** only when `available.advanced` is true;
- explicit UI text that Greia never auto-enables the advanced path;
- demo behavior and focused tests.

This newer revision is intentionally **not yet written into Greia's runtime pin** because its `npm test`, syntax checks and exact 12-file SHA-256 manifest regeneration still need to execute on a real local checkout. Do not bypass that integrity boundary.

Greia now includes:

```text
tools/update_parent_client_pin.py
```

Use it from a clean exact Parent checkout after tests to regenerate both the revision and the exact byte/SHA-256 manifest. The tool refuses dirty or revision-mismatched Parent checkouts.

The previously pinned Parent revision had been verified as:

```text
Parent npm test:                  28 / 28 PASS
changed JS syntax checks:         PASS
changed published Git blobs:      byte-identical to tested local copies
Greia manifest vs Parent runtime: 12 / 12 byte-count + SHA-256 PASS
Greia pin TOML parse/revision:     PASS
```

Those results apply to `7ff7e318...`, not automatically to `cdea281...`.

Manual desktop/mobile browser visual acceptance also remains required for the newer microphone UI.

## Parent product architecture

The rebuilt client has one state model and one product renderer around four parent jobs:

```text
Home
Children
Activities
This Greia
```

Implemented typed surfaces include:

- child profile create/edit/delete;
- child password set/replace/remove;
- optional approximate age;
- Automatic/Easier/Standard/Harder challenge preference;
- installed Activity inventory;
- per-child Activity visibility policy and individual Always show/Always hide overrides;
- Wi-Fi scan/connect;
- language;
- mouse/touchpad/display settings;
- microphone input gain when Greia exposes it;
- typed microphone-processing preferences in the newer source candidate;
- Parent password change;
- SSH maintenance enable/disable;
- paired-device list/revoke;
- system/update status and capability-gated delivery;
- Activity install only when the API advertises it.

The client remains API-first. It does not gain shell/filesystem/package-manager shortcuts.

---

# 3. Platform-owned microphone processing — PHYSICALLY ACCEPTED on the reference Acer (2026-08-24)

Architecture authority:

```text
docs/adr/0031-platform-owned-microphone-processing.md
docs/architecture/GREIA_AUDIO_SERVICE.md
```

Physical finalization protocol and acceptance evidence:

```text
docs/testing/2026-08-23_ACER_MICROPHONE_PROCESSING_ACCEPTANCE.md
docs/reviews/2026-08-24_ACER_MICROPHONE_PHYSICAL_ACCEPTANCE.md
```

## Product decision

The microphone-processing policy is now explicit:

```text
lightweight cleanup desired by default
advanced cleanup OFF by default
parent may disable all processing
parent may explicitly enable advanced only when a real endpoint exists
NO automatic benchmark/model/load-based processor selection
```

This is separate from the existing microphone input-gain setting.

## Source implementation

Implemented:

```text
src/greia_platform/audio.py
runtime/audio-settings.toml
src/greia_parent/protocol.py
src/greia_parent/update_api.py
src/greia_launcher/child_shell.py
src/greia_platform/activity_api.py
src/greia_platform/audio_alsa/        (greia_mic_light ExtPlug source)
runtime/alsa/                         (per-launch SDL ALSA composition)
build/overlay/etc/asound.conf
build/overlay/usr/local/lib/greia-os/greia-audio-endpoint-probe
build/overlay/etc/systemd/system/greia-audio-endpoints.service
build/package-sets/platform-shell-pygame.txt   (libspeexdsp1)
```

The typed `AudioService` owns desired state, backend availability, effective route and truthful fallback. The provisional ALSA adapter names stable logical endpoints:

```text
raw/default:   default
lightweight:   greia_mic_light
advanced:      greia_mic_advanced
```

Current route readiness is adapter-fed from current-boot markers under `/run/greia-audio/`; markers must never be created unless the corresponding endpoint really works.

An Activity granted `audio.basic` receives the resolved microphone route through its sanitized launch context. Python Activities obtain it through:

```python
from greia_platform.activity_api import get_audio_capture_device
from greia_platform.activity_api import get_sdl_capture_device
```

`get_sdl_capture_device()` designates the SDL-enumerated capture device that carries the route (SDL 2.26 cannot open arbitrary ALSA PCM names; the launcher injects the composed ALSA view for non-off modes). Activities must not enumerate physical microphones and choose the first host device.

Focused source tests cover the default/no-auto-promotion policy, explicit advanced opt-in, unavailable-backend handling, processing-off route, Activity environment projection, the SDL designation and Parent API settings semantics (31 focused tests PASS at `2972127`).

## Physical acceptance state (2026-08-24, Acer Aspire One)

The lightweight route is implemented and physically accepted on the reference Acer:

- `greia_mic_light` = in-process ALSA ExtPlug: FIR decimation 48k→24k,
  SpeexDSP preprocessor denoise (−15 dB, AGC off), FIR interpolation back,
  primed delay-line FIFO. On-demand only; no daemon; zero idle cost.
- Boot probe service creates `/run/greia-audio/lightweight-ready` only after
  a real one-second capture; verified recreated automatically after reboot.
- Live route proof: during a real launcher-launched Teatrino recording the
  capture hardware ran at 48000 Hz (route contract) owned by the Teatrino pid.
- Measured: −19.9 dB stationary noise-floor reduction, voice band preserved
  (stimulus A/B within ~1.5 dB), zero glitches, ~5–10% of one core, +0.4 MB
  RSS during capture. Owner A/B verdict: routed clearly better.
- Parent controls verified against the device API: default (lightweight),
  off (raw, no ALSA injection), restore, and reboot persistence.
- Negative check: an Activity without `audio.basic` (painting) receives zero
  audio-route environment variables.
- Advanced endpoint intentionally NOT INSTALLED (`available.advanced = false`).
- Device tuning notes: ALSA Capture level was found maxed (+31.5 dB) causing
  hard clipping; set to +3 dB on this device. Parent `mic_gain` raised
  2.0 → 3.0 on this device for post-denoise loudness (Parent-adjustable).

Open follow-up: image-build integration must compile
`src/greia_platform/audio_alsa/` into future i686 images. Images without the
plugin honestly fall back to raw with `lightweight_unavailable`.

## Existing microphone gain retained

Current hardware gain contract remains:

```text
desired.mic_gain
minimum: 0.5× / 50%
default: 2.0× / 200%
maximum: 4.0× / 400%
```

It remains in `HardwareSettingsStore` for compatibility. Do not conflate it with denoising mode or silently move gain/AGC ownership without measured migration of existing consumers.

---

# 4. Child Activity discovery — implementation is active, not future-only

Authorities:

```text
docs/product/CHILD_ACTIVITY_DISCOVERY_AND_AUDIENCE.md
docs/design/GREIA_LAUNCHER_INTERACTION_AND_ACTIVITY_CATALOGUE.md
src/greia_platform/activity_discovery.py
src/greia_launcher/catalogue_view.py
```

Normal child flow remains:

```text
profile
  → Greia Home
    → primary Collection
      → optional sub-Collection
        → Activity
```

Platform-owned primary vocabulary:

```text
create
play
learn
explore
my_greia
```

Valid Activities with no recognized primary destination fail open through bounded `browse` / More recovery. Arbitrary package category strings do not manufacture Home destinations. One Activity may appear in multiple Collections without duplicating installation/state/progression.

## Implemented audience metadata

`ActivityManifest` now owns:

```text
difficulty                 1..10 baseline
recommended_age_min        optional 1..18
recommended_age_max        optional 1..18
difficulty_min             optional 1..10
difficulty_max             optional 1..10
adaptive_difficulty        boolean
presentation.discovery_tags
```

Adaptive-difficulty ranges must be declared as a valid min/max pair and require `adaptive_difficulty = true`.

`ChildProfile` now owns:

```text
approximate_age            optional 1..18
challenge_preference       automatic/easier/standard/harder
```

No date of birth is required.

## Implemented Parent policy

`ActivityDiscoveryPolicy` owns:

```text
visibility_mode:
  show_all
  hide_too_simple
  recommended_only
  custom

overrides:
  always_show
  always_hide
```

Explicit Parent override wins before automatic recommendation. Missing age/audience metadata fails open for ordinary discovery.

`ActivityDiscoveryService` computes the effective visible/ranked set without changing package authority, saves or permissions.

## Implemented adaptive depth

`AdaptiveCollectionPlanner` currently uses:

```text
enter threshold:    > 10 triggers subdivision evaluation
collapse threshold: <= 8 returns direct Activities
9–10:               retained subdivision only when previously validly subdivided
semantic groups:    2–5, platform-owned vocabulary, >=2 Activities/group
maximum depth:      Home → primary → optional sub-Collection → Activity
```

Bad/incomplete semantic partitions remain direct rather than manufacturing a meaningless Other bucket.

The policy store carries bounded `subdivided_collections` hysteresis state separately from Parent visibility intent.

Collection-first, bounded-primary-vocabulary and adaptive-catalogue simulator acceptance is already recorded in repository testing documentation. Do **not** return to the old All/filter Home model.

---

# 5. Parent/security boundary still open

The current LAN Parent transport remains provisional HTTP/bootstrap pairing.

Implemented foundations include per-device bearer credentials and individual revocation, but production acceptance still requires:

- short-lived Greia-owned pairing challenge;
- local device Allow/Deny confirmation;
- authenticated encrypted transport;
- device binding plus expiry/replay protections.

Ordinary/release capability advertisement must remain honest. In particular, source presence does not authorize package/system mutation over an insecure transport.

The external Parent client remains a source-pinned integrity-checked build input; it is **not yet vendored/composed into the release image as a closed packaging tranche**.

---

# 6. Device language / localization

Authorities:

```text
docs/adr/0028-platform-and-activity-localization-language-context.md
docs/product/SYSTEM_LANGUAGE_AND_LOCALIZATION.md
```

Effective language is selected at install, persisted, and may later be overridden by `SystemLanguageStore`. English remains default; current canonical selectable registry includes:

```text
en, it, es, de, fr, zh-CN, pt, ar, hi, id, bn, sw
```

`zh` canonicalizes to `zh-CN`. Installer, on-device Parent panel and external Parent client consume the Greia-owned registry.

Selectable does not imply complete translations, shaping/font coverage or RTL acceptance.

---

# 7. Transactional Greia system updates

Authorities:

```text
docs/adr/0030-platform-owned-transactional-system-updates.md
docs/product/SYSTEM_UPDATES.md
docs/development/GREIA_SYSTEM_UPDATE_RELEASE_WORKFLOW.md
```

Signed `.greiaupdate` source/trust/inbox/tooling foundations exist.

Current x86 profile remains `bios-single-ext4` with:

```text
system.update.activate = false
```

A/B inactive-slot activation, boot-health confirmation and automatic rollback are not accepted on the current production layout. No in-place active-root fallback is authorized for convenience.

---

# 8. R7 remains the blocking architecture phase

Current production remains provisional Xorg/xinit compatibility behavior while direct appliance display/session/input is resolved.

Mandatory architecture remains:

- Greia-owned display/session authority;
- protected platform Home/Back above Activity content;
- protected-system input intercepted before Activity delivery;
- controller ownership/normalization platform-owned;
- ordinary Activities do not gain raw `/dev/input` or DRM authority.

Recent launcher performance work, achievement presentation/art work and microphone service are useful platform work but are **not** R7 display/session closure.

---

# 9. Boot / installer / physical facts retained

- Reference Acer Aspire One is BIOS-only.
- Proven live USB path is syslinux/FAT32.
- Canonical USB creator: `tools/build-live-usb.sh`.
- Installed initramfs must be target-kernel/target-hardware aware; build-host/chroot hardware is not target authority.
- Developer/test SSH remains owner-approved `greia / greia`, root SSH denied; normal/release remains fail-closed.
- Physical evidence applies only to the exact source/image/tranche measured and must not be generalized to later source.

Canonical hardware history:

```text
docs/INSTALLATION_ISSUES_LOG.md
docs/INSTALLATION_USB_BOOT_POSTMORTEM.md
docs/INSTALLED_OS_BOOT_POSTMORTEM.md
docs/testing/LOCAL_AGENT_START_HERE.md
docs/testing/2026-08-23_ACER_MICROPHONE_PROCESSING_ACCEPTANCE.md
```

---

# 10. Visual/art continuation

Stable/current authorities:

```text
docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
docs/engineering/GREIA_PERFORMANCE_BEST_PRACTICES.md
docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md
docs/design/GREIA_GENERIC_ART_LIBRARY_TAXONOMY.md
docs/design/GREIA_ACTIVITY_ACHIEVEMENT_ART.md
skills/greia-visual-authoring/SKILL.md
skills/greia-activity-authoring/ACHIEVEMENTS.md
docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md
docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
```

Theme/source bundles remain provenance pools; the generic semantic authoring library is the primary authoring interface. Generic authoring tooling stays development-time and does not become a second runtime catalogue.

For global achievements, Activity-generated art is now a supported **decorative contribution**: Greia owns award frames and achievement authority, while explicitly admitted Activity emblems may supply the center artwork. Purpose-made Activity emblem generation should remain inside the Activity's own art/source workflow and obey the bounded PNG contract.

Do not infer arbitrary Activity-authoring-agent drawing capability from the owner's stronger maintainer-side agent.

---

# 11. Next exact steps

## Immediate achievement-art verification

1. Record current `main` SHA before testing.
2. Run:
   ```bash
   PYTHONPATH=src python3 -m unittest \
     tests.test_achievement_art \
     tests.test_achievement_emblem_cache \
     tests.test_achievements \
     tests.test_pygame_achievements \
     tests.test_achievement_localization \
     tests.test_activity_contract \
     -v
   ```
3. Run the checkout's normal complete local unit/validation gate; preserve the first real failure rather than repairing around it during acceptance.
4. In the Activity Simulator, do only the focused visual recheck documented in `docs/reviews/2026-08-24_ACTIVITY_THEMED_ACHIEVEMENT_ART.md`: Italian Badge Library localization, unlocked Clinic/Memory/Bridge Activity-derived centers inside Greia frames, locked-art non-disclosure, Greia-wide Star badge remaining platform art, and idle repaint sanity.
5. Treat this as simulator/developer evidence only; no Acer performance claim follows without hardware measurement.

## Blocking engineering

1. Resolve current `main` before each new implementation tranche.
2. Read `skills/greia-os-work/SKILL.md` for substantive OS/platform work and the Activity skill's `ENGINEERING.md` for substantive Activity implementation; structural Activity refactors additionally require `REFACTORING.md`. Keep the derived skills synchronized when their governed contracts change.
3. Owner disposition: reconcile the four stale boot-contract tests (`panic=30`) with the accepted postmortem/source direction (`panic=5`).
4. Re-run the current aggregate verification only after that disposition; preserve genuine failures.
5. Continue R7 from its first incomplete blocking gate; do not treat launcher performance optimization, microphone processing, achievements or the Activity calibration as display/session closure.
6. Preserve the current Acer performance measurements in the engineering performance manual as future UI/render work is added.

## Clinica Cuccioli calibration verification

1. Run `PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_clinica_cuccioli_refactor.py' -v` in a real checkout.
2. Run `make verify`; preserve the known aggregate baseline failures separately from any new regression.
3. Load `activities/clinica_cuccioli` in the real Activity Simulator and execute the Italian/English, sequence-consistency, five-patient, Play Again/persistence, resize and protected-Home checks in `docs/reviews/2026-08-23_CLINICA_CUCCIOLI_ARCHITECTURE_CALIBRATION.md`.
4. Only after simulator/source verification, compare the same Activity on the reference Acer if a performance claim is desired.
5. Do not yet extract the Clinic app-loop/particle/progress/render helpers into `greia_platform`; inspect at least one or two more Activities first and extract only genuinely shared semantics.

## Microphone physical finalization

1. Follow `docs/testing/2026-08-23_ACER_MICROPHONE_PROCESSING_ACCEPTANCE.md` exactly on the owner-controlled Acer lane.
2. Run the new focused Greia source tests before touching hardware.
3. Implement/prove `greia_mic_light` with the smallest real denoiser that materially helps the Acer signal; prefer on-demand SpeexDSP evaluation before heavyweight architecture.
4. Migrate remaining first-party microphone consumers away from host-device enumeration to `get_audio_capture_device()`.
5. Measure raw vs lightweight CPU/RSS/quality/dropouts; leave readiness absent on failure.
6. Evaluate advanced processing only after lightweight is stable; it is acceptable for Acer to report `advanced = false`.
7. Update this handover with exact PHYSICAL evidence only after it exists.

## Parent

1. In a clean owner-controlled `Greia-Parent-App-Html` checkout at `cdea281a1848d1372a18822a559dc15494e749b0`, run `npm test` and JS syntax checks, then visually exercise desktop + mobile/narrow layouts including the new microphone card.
2. If that revision passes, run `tools/update_parent_client_pin.py --parent-root <clean-parent-checkout> --revision cdea281a1848d1372a18822a559dc15494e749b0` from Greia and validate the regenerated exact 12-file integrity manifest.
3. Commit the Greia repin as a distinct coherent commit; do not runtime-fetch moving Parent `main`.
4. Decide/implement the separate vendoring/release-image composition tranche later.
5. Continue production pairing/encrypted-transport work before enabling ordinary release mutation capabilities.

## Child discovery

1. Treat adaptive Collection depth, profile age/challenge and Parent visibility as **implemented foundations**.
2. Calibrate metadata/group vocabulary/thresholds through evidence rather than adding hierarchy depth.
3. Keep missing metadata fail-open and Parent overrides authoritative.
4. Keep education taxonomy separate from navigation taxonomy.

---

# 12. Non-negotiable continuation rules

- `main` only unless owner changes policy;
- GitHub is canonical persistence;
- no unauthorized GitHub Actions use/inspection;
- no current-head PASS without current-head execution;
- substantive OS/platform work consumes `skills/greia-os-work/SKILL.md`;
- substantive Activity implementation consumes `skills/greia-activity-authoring/ENGINEERING.md` through the Activity skill;
- structural Activity refactors additionally consume `skills/greia-activity-authoring/REFACTORING.md` and inventory declaration/behavior contracts before moving code;
- Activity `main.py` is a composition/bootstrap boundary rather than a monolithic application implementation;
- multiple input paths for one semantic child action delegate to one domain rule rather than duplicating correctness/scoring policy;
- Activities may offer bounded language-neutral achievement emblems, but global achievement IDs/criteria/tier/frame/localization/state/rewards remain Greia-owned and require explicit platform-policy admission;
- parent-installed Activity emblem declarations never auto-create global Badge Library entries;
- no visible Linux shell/desktop in normal child path;
- R7 remains open and Xorg/xinit provisional;
- protected Home/Back stays outside Activity authority;
- controller/input/device authority stays platform-owned;
- microphone capture routing is platform-owned for Activities with `audio.basic`;
- lightweight microphone cleanup is desired default; advanced is explicit Parent opt-in only;
- no automatic microphone processor selection/benchmark promotion;
- no readiness marker without a real working endpoint;
- one canonical device-language registry;
- selectable language is not translation/font/RTL completion;
- system-update activation stays false on current single-root profiles;
- Parent HTTP/bootstrap transport remains provisional;
- external Parent JS is pinned/integrity-checked, never fetched from moving `main` at runtime;
- Collection-first Home is accepted; old All/filter root is not normal child IA;
- root and sub-Collection vocabularies are platform-owned;
- effective catalogue is per child after Parent policy;
- age and difficulty remain separate dimensions;
- missing audience metadata fails open;
- explicit Parent Activity overrides win over automatic recommendation;
- adaptive discovery never exceeds one sub-Collection layer;
- Collections are semantic child groupings, never filesystem folders;
- visual/runtime/Activity caches remain bounded with explicit invalidation and avoid per-frame decode/scale/IO;
- performance claims require measurement on the claimed execution scope.

**Resume the blocking platform path from R7 in `docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md`. In parallel, verify the post-acceptance achievement localization/Activity-art tranche through its focused source + simulator checks before calling current head green; the microphone tranche may be physically finalized only through its dedicated Acer protocol. Do not report source architecture as hardware acceptance.**
