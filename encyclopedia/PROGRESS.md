# Greia Encyclopedia — implementation progress ledger

**Purpose:** append-only operational progress for the long-lived `encyclopedia/PLAN.md` workstream.  
**Plan authority:** `encyclopedia/PLAN.md` remains the product/architecture/content plan.  
**Runtime implementation:** `activities/enciclopedia_greia/`.

Do not rewrite older entries to make history cleaner. Append corrections.

---

## 2026-08-27 — first source-construction pass: Activity shell + all six sections

Owner testing direction for this construction pass:

- do **not** interrupt first-pass construction with Simulator acceptance after every phase/page;
- build a solid coherent source base first;
- run the real Greia Simulator/interaction/visual acceptance as one consolidated later pass;
- until that later pass, use the exact label **SOURCE-VERIFIED / SIMULATOR-UNVERIFIED** rather than claiming runtime acceptance.

Implemented on `main`:

- first-party Activity manifest `org.greia.enciclopedia`;
- thin `main.py` composition root;
- `EncyclopediaApp` lifecycle/input owner;
- tiny Activity-local executable page engine (`EncyclopediaPage`, explicit `PageRegistry`, bounded `PageNavigator`);
- no runtime filesystem page discovery or dynamic imports;
- semantic page input vocabulary mapped from Greia input translation;
- Greia protected Home remains platform-owned;
- distinct Activity-internal Back tab for encyclopedia page navigation, outside protected system chrome;
- fixed 1024x600 reference canvas through Greia's shared Pygame canvas adapter;
- bounded shared-character rendition cache with fail-soft fallbacks;
- bounded prerecorded-audio owner using `LocalizedResources.audio_cue()`; no runtime synthesis;
- bilingual `it`/`en` runtime resource bundles;
- runtime page registry now implements exactly seven pages: Home + six section pages.

Implemented section behavior:

1. `home` — six large visual worlds, Leo presenter, keyboard/controller grid navigation and pointer/touch selection;
2. `animals` — Tito-hosted habitat collage containing the six v0.1 animal anchors (lion, elephant, octopus, bee, penguin, frog);
3. `space` — Leo-hosted lightweight Solar System with all eight major planets continuously orbiting and selectable;
4. `earth` — Tito-hosted nature scene with rain/ocean/tree/rainbow and a touch-triggered volcano eruption;
5. `body` — Lilli-hosted body schematic with breathing lungs and animated/touch-emphasized heartbeat;
6. `machines` — Dani-hosted workshop with linked animated gears and touch acceleration plus mechanism hints;
7. `history` — Leo-hosted visual timeline for dinosaurs, fossils, mammoth, cave paintings and pyramids.

Audio state:

- page code requests the existing stable semantic cue IDs from `VOICE_RECORDING_REQUESTS.md`;
- runtime locale audio tables deliberately remain empty until accepted prerecorded files are integrated;
- no runtime/on-device TTS, speech recognition, LLM, network knowledge lookup or voice model exists;
- existing `REQUESTED` voice rows were not rewritten during this source pass.

Product decisions recorded for the Activity-authoring contract:

- presenter plan: recurring Greia cast as listed above;
- pre-reader strategy: visual worlds/scenes and direct manipulation; text is supporting labels only;
- microphone/child recording: considered and intentionally excluded from this encyclopedia v0.1 base because it does not materially improve the core browse/discovery interaction;
- score: deliberately none;
- durable Activity progress: deliberately deferred until the Discovery/collection semantics are designed; no fake completion score or badge farming;
- events/Stars/global achievements: none in this base; later discovery milestones may report semantic facts only after their contract is designed;
- locales: Italian and English first;
- speech: all presenter narration prerecorded during authoring/parent-device production.

Source checks actually executed during authoring before persistence:

- all new Python source parsed with `ast.parse`;
- all new Python source passed `py_compile` in the construction workspace;
- Activity TOML parsed with `tomllib`;
- locale JSON parsed and locale key sets matched;
- manual/static curated-import-policy check against current `runtime/child-runtime.toml` roots passed;
- manifest capability sets are disjoint/allowed and request no permissions/network;
- discovery tag uses the platform-owned `nature` vocabulary;
- explicit scan found no runtime TTS/speech-recognition backend imports.

Repository test fixtures reconciled for the 33rd built-in Activity:

- `tests/test_activity_contract.py`;
- `tests/test_first_party_activity_audience_metadata.py`;
- `tests/test_first_party_activity_readiness.py`;
- new `tests/test_activity_enciclopedia.py`.

Not claimed / deliberately deferred:

- no Simulator launch/survival evidence yet;
- no rendered screenshot/visual acceptance yet;
- no physical Acer/Pi evidence;
- no factual final-entry narration/research yet;
- no final entry pages yet;
- no accepted recordings integrated yet;
- no completion/progression/discovery-book persistence yet.

Next construction tranche:

1. review the seven-page source base for architecture drift and fix any source-level defect found;
2. implement the six stress-test final entries from the plan: `animals.octopus`, `space.saturn`, `earth.volcano`, `body.heart`, `machines.gears`, `history.fossils`;
3. for each factual pilot, research claims first and create provenance before requesting factual narration;
4. append bilingual factual cues to the unified recording queue only after wording is research-ready;
5. keep the tiny engine free of subject-specific branches;
6. after the coherent first-pass base is sufficiently broad, run one consolidated Greia Simulator/visual/input acceptance pass as directed by the owner.
