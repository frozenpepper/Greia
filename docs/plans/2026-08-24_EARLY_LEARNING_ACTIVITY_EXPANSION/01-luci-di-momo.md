# Session 01 — Luci di Momo: subitizing and small quantities

**Provider calls:** forbidden; repository art plus local SVG work only  
**Prerequisite for acceptance:** Session 00 accepted/committed and its content hash matches  
**WIP implementation rule:** source engineering may begin before Session 00 human review, but it remains `IMPLEMENTED / SIMULATOR-UNVERIFIED / CONTENT-LOCK-PENDING` and no review-dependent audio/content may be finalized  
**Commit:** `feat(activity): add Luci di Momo subitizing game`

## Outcome

`org.greia.luci-di-momo` launches as a modular bilingual five-round subitizing game with deterministic adaptation, non-punitive replay, one completion event, bounded rendering, and focused tests.

## Implementation checkpoint — 2026-08-24

The source implementation is complete, verified, and accepted:

Current source shape:

```text
activities/luci_di_momo/
  activity.toml
  main.py
  firefly_model.py
  firefly_services.py
  firefly_audio.py
  firefly_art.py
  firefly_renderer.py
  firefly_app.py
  locales/{it,en}.json
  assets/source/icon.svg
  assets/icon.png
tests/test_activity_luci_di_momo.py
```

Evidence:
- 10/10 focused unit and integration tests passing (`tests/test_activity_luci_di_momo.py`).
- Full repository gate `make verify` passing: 1,198 unit tests green, all 21 activities valid, footprint and shell checks green.
- Package validation digest: `sha256 45f5ea72e154fa62773633608c0f100abdba91d263fc3560cadf7b69c1c54348`.
- Visual review executed for Italian and English locales and multiple viewports (1024x600, 1280x800, 800x480, 1366x768). Vector reload arrow rendered on replay button, safe bounds respected.
- Audio: Nonverbal prepared synthesis only; no custom Momo voice required.
- Simulator integration: Supervisor launch and lifecycle tested cleanly.

## Preconditions

- Pull current `main`; verify Session 00 evidence before claiming acceptance. Source WIP may proceed under the status boundary above.
- Read the task-specific routes selected by `skills/greia-activity-authoring/SKILL.md`.
- For Luci this includes engineering, launch acceptance, terminal rendering, achievements/events, discovery/manifest, localization/UI/input, and visual authoring. Read `VOICE_GENERATION.md` only when speech/audio authoring decisions are being made.

## Allowed files

```text
activities/luci_di_momo/**
tests/test_activity_luci_di_momo.py
docs/agents/GREIA_EARLY_LEARNING_ACTIVITY_IMPLEMENTATION_RUNBOOK.md
skills/greia-activity-authoring/SKILL.md
docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md
docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md
HANDOVER.md
```

## Forbidden changes

- No platform, policy, shared-catalogue, or existing-Activity edit.
- No countdown, lives, speed score, click telemetry, direct reward, text dependency, or train/recipe counting loop.
- No generated character speech merely to fill silence; Luci v1 requires no custom Momo voice.

## Evidence and source decisions

Head Start names subitizing small sets and numeral/quantity relationships. Existing Activities count visible items but do not isolate brief small-set recognition. Momo is the canonical playful guide; shared `character.momo` is resolved semantically with an Activity-local fail-soft fallback. The current implementation uses a baked Activity-local night-garden presentation and procedural firefly/lantern shapes; final visual acceptance must inspect actual Simulator rendering before the source is called accepted.

## Exact implementation

1. Manifest: ID/title `org.greia.luci-di-momo` / `activity.luci_di_momo.title`; languages `it,en`; collections `learn,play`; tag `numbers`; education `early_math,subitizing,quantity_comparison`, difficulty 2, age 4–6, adaptive 1–4; pointer input; required `display,pointer,audio.basic`, optional `touch`; event `firefly.garden_completed` completion; storage 1.
2. Keep thin `main.py` plus `firefly_model.py`, `firefly_services.py`, `firefly_audio.py`, `firefly_art.py`, `firefly_renderer.py`, `firefly_app.py`.
3. Define frozen `FireflyRound(round_id, quantity, positions, choice_values, reveal_ms)`, `AttemptResult(correct, round_completed, session_complete, first_attempt_success, hints_used, used_replay)`, bounded `AttemptSummary`, and `FireflySession` owning five rounds and one-shot terminal/event flags.
4. Levels: L1 quantities 1–3 canonical layouts/1600 ms; L2 1–4 mixed layouts/1400 ms; L3 1–5 varied layouts/1200 ms; L4 1–5 varied spacing/sprite size/1100 ms. Three numeral choices contain one answer and two unique in-range distractors.
5. Inject `random.Random`; enforce ≥72 logical px center separation and safe-playfield containment. Same seed produces identical rounds.
6. After reveal, show one sleeping-lantern state and three 104×104 numeral choices. Replay is unlimited, sets `used_replay`, and is not failure. Wrong choice replays fireflies one-by-one, then restores the same choices without progress loss.
7. Persist `luci_di_momo.progress.v1`: schema, level, at most eight summaries. Apply README adaptation only after a five-round set.
8. Emit `firefly.garden_completed` once after round five with level, first-attempt count, and replays; use stable set idempotency.
9. Reuse `character.momo` through the semantic shared-visual API with a local fail-soft fallback. Launcher icon remains Activity-local and text-free. Final art may refine fireflies/lantern/garden through the visual-authoring route without changing domain truth.
10. Use `PygameCompletionScreen`; terminal freezes simulation. READY follows first presented playable frame.
11. Replay/choice hit targets are active only when visibly presented. Hidden controls must not receive semantic input.
12. Static choice/terminal phases remain event-responsive without continuous repaint; reveal/hint animation is time-based and bounded.

## Tests

- Exact manifest/event and collision-free ID.
- Seed determinism, level bounds, unique choices, safe spacing, and correct answers.
- Wrong/replay paths retain round identity; five completions emit one one-shot completion payload.
- Malformed storage recovers safely and history stays ≤8.
- Shared viewport mapping rejects protected input; hidden controls cannot activate; static idle does not redraw; terminal freezes/restarts.
- Final repository suite must add/retain interaction coverage as needed when the real Greia runtime is available.

## Local gate

```bash
find activities/luci_di_momo -type d -name __pycache__ -prune -exec rm -rf {} +
PYTHONPATH=src:tests:. python3 -m unittest tests.test_activity_luci_di_momo -v
PYTHONPATH=src:tools python3 tools/validate_activity.py activities/luci_di_momo
```

Expected: tests and validation exit 0; no cached bytecode remains.

## Cumulative gate

```bash
PYTHONPATH=src:tests:. python3 -m unittest tests.test_activity_luci_di_momo tests.test_activity_contract tests.test_activity_audience_manifest tests.test_first_party_activity_audience_metadata tests.test_first_party_activity_readiness tests.test_core_activity_system_safe_ui tests.test_activity_ui tests.test_activity_viewport tests.test_localization tests.test_typography_emoji -v
```

Then run `make verify` and the exact final-source Simulator gate from `skills/greia-activity-authoring/LAUNCH_ACCEPTANCE.md`.

Expected: exit 0 with no failures/errors/skips introduced, followed by a real Simulator PASS before calling Luci complete/working/accepted.

## Stop conditions

- Current shared-visual/manifest source cannot support the package without platform edits.
- Object size/spacing reveals the answer, text is required to understand the loop, or terminal repaints continuously.
- Session 00 review is missing when someone attempts to claim content/source acceptance.
- Final source has not passed Simulator launch/survival/interaction/restart/Home acceptance.

## Handoff

Return the standard packet plus seeded challenge matrix, cache bounds, idle redraw observation, manifest/emission proof, asset hashes, locale results, Simulator evidence, and explicit audio disposition (`nonverbal only; no custom Momo voice required` unless owner-approved scope changes).
