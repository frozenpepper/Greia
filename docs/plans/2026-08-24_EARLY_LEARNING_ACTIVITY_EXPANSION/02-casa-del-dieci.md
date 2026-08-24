# Session 02 — Casa del Dieci: number composition and operations

**Provider calls:** forbidden; repository art plus local SVG work only
**Prerequisite:** Sessions 00–01 accepted and committed
**Commit:** `feat(activity): add Casa del Dieci number-bond game`

## Outcome

`org.greia.casa-del-dieci` provides six concrete ten-room challenges progressing from composition to add, take-away, and missing-part reasoning within ten.

## Implementation checkpoint — 2026-08-24

The source implementation is complete, verified, and accepted:

Current source shape:

```text
activities/casa_del_dieci/
  activity.toml
  main.py
  ten_house_model.py
  ten_house_services.py
  ten_house_audio.py
  ten_house_art.py
  ten_house_renderer.py
  ten_house_app.py
  locales/{it,en}.json
  assets/source/icon.svg
  assets/icon.png
tests/test_activity_casa_del_dieci.py
```

Evidence:
- 11/11 focused unit and integration tests passing (`tests/test_activity_casa_del_dieci.py`).
- Cumulative test suite passing: 81 tests green across early learning and platform contracts.
- Repository-wide `make verify` completely passing: 1,209 unit tests green, all 22 activities valid, footprint and shell checks green.
- Package validation digest: `sha256 ea81b746fbc2d493d36fac1032ec8ed41b73dbef6bd14c04d2db63940a69dd8e`.
- Visual review executed for Italian and English locales and multiple game modes (Compose, Add, Missing-Part, Take-Away, Completion). 10-room 2x5 ten-frame layout with high-contrast glowing rooms and keyboard focus ring.
- Audio: Prepared procedural tones (`toggle`, `correct`, `retry`, `complete`).
- Simulator integration: Supervisor launch and lifecycle tested cleanly.

## Preconditions

- Pull current `main`; verify the prior handoff/gate.
- Read the same specialist documents required by Session 01.

## Allowed files

```text
activities/casa_del_dieci/**
tests/test_activity_casa_del_dieci.py
docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md
docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md
HANDOVER.md
```

## Forbidden changes

- No platform/shared helper, existing Activity, progression/achievement policy, or reward edit.
- No timed arithmetic, negative quantity, operand above ten, equation-only prompt, or failure penalty.

## Evidence and source decisions

Head Start supports concrete joining/separating with objects. `Treno dei Numeri` owns counting/cardinality; this package owns a stable 2×5 part–whole representation and visible transformations. Dani is the math/logic guide.

## Exact implementation

1. Manifest: `org.greia.casa-del-dieci`, key `activity.casa_del_dieci.title`; `it,en`; collections `learn,play`; tags `numbers,puzzles`; education `early_math,number_composition,operations`; difficulty 3, age 5–7, adaptive 2–5; hybrid input; required `display,pointer`, optional `keyboard,touch`; milestone `ten_house.room_completed`, completion `ten_house.house_completed`; storage 1.
2. Create thin `main.py` and `ten_house_model/content/services/art/renderer/app.py`. Define `OperationMode(COMPOSE,ADD,TAKE_AWAY,MISSING_PART)`, frozen `TenHouseChallenge(target,starting_lit,delta,answer,mode)`, and `TenHouseSession`.
3. Render ten fixed rooms in two rows of five. Animate concrete room lights before showing the large numeral and optional operator/equality symbol.
4. L1 compose 2–5; L2 complete 5–10 from a nonzero given part; L3 add 1–3 to 1–6 with result ≤10; L4 remove 1–3 from 3–10 with result ≥0; L5 mixed modes including missing addend. Generate six unique tuples per set.
5. COMPOSE uses room toggles and enables confirm only at target. Operation modes present three unique numeral answers, then animate the actual join/remove and finally show the symbolic sentence.
6. Wrong answer wobbles the choice and highlights/counts concrete rooms without mutating challenge. Arrows move semantic focus; Space/Enter and pointer call the same domain action. Open no input device.
7. Persist `casa_del_dieci.progress.v1` with level and ≤8 summaries. Emit milestone once per challenge and completion once per set with stable keys.
8. Reuse `character.dani`; adapt block material language but create original ten-house/on-off rooms. Cache numerals 0–10 and operators. Icon has house/Dani motif without text.
9. Use `PygameCompletionScreen`; terminal stops room animation and restarts a valid set.

## Tests

- Equation/bound/level invariants and six unique deterministic tuples.
- Toggle/confirm correctness; wrong input cannot advance; repeated correct input cannot duplicate events.
- Pointer and keyboard share one domain action; protected region rejected.
- Storage bound, prepared finite caches, terminal freeze/restart, exact manifest/events.

## Local gate

```bash
find activities/casa_del_dieci -type d -name __pycache__ -prune -exec rm -rf {} +
PYTHONPATH=src:tests:. python3 -m unittest tests.test_activity_casa_del_dieci -v
PYTHONPATH=src:tools python3 tools/validate_activity.py activities/casa_del_dieci
```

Expected: tests and validation exit 0; package has no cached bytecode.

## Cumulative gate

```bash
PYTHONPATH=src:tests:. python3 -m unittest tests.test_activity_luci_di_momo tests.test_activity_casa_del_dieci tests.test_activity_contract tests.test_activity_audience_manifest tests.test_first_party_activity_audience_metadata tests.test_first_party_activity_readiness tests.test_core_activity_system_safe_ui tests.test_activity_ui tests.test_activity_viewport tests.test_localization tests.test_typography_emoji -v
```

Expected: exit 0 with both portfolio suites and named contracts green.

## Stop conditions

- A mode needs a number above ten or visible rooms disagree with equation truth.
- Pointer/keyboard reach different correctness/event paths or raw controller authority is required.

## Handoff

Return the standard packet plus six seeded examples per level, equation proof, input map, cache/event counts, asset hashes, and SOURCE label.
