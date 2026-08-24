# Session 01 — Luci di Momo: subitizing and small quantities

**Provider calls:** forbidden; repository art plus local SVG work only
**Prerequisite:** Session 00 accepted/committed and its content hash matches
**Commit:** `feat(activity): add Luci di Momo subitizing game`

## Outcome

`org.greia.luci-di-momo` launches as a modular bilingual five-round subitizing game with deterministic adaptation, non-punitive replay, one completion event, bounded rendering, and focused tests.

## Preconditions

- Pull current `main`; verify Session 00 evidence.
- Read Activity `CORE.md`, `ENGINEERING.md`, `TERMINAL_RENDERING.md`, `ACHIEVEMENTS.md`, `DISCOVERY.md`, `VOICE_GENERATION.md`, and visual-authoring authorities.

## Allowed files

```text
activities/luci_di_momo/**
tests/test_activity_luci_di_momo.py
docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md
docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md
HANDOVER.md
```

## Forbidden changes

- No platform, policy, shared-catalogue, or existing-Activity edit.
- No countdown, lives, speed score, click telemetry, direct reward, text dependency, or train/recipe counting loop.

## Evidence and source decisions

Head Start names subitizing small sets and numeral/quantity relationships. Existing Activities count visible items but do not isolate brief small-set recognition. Momo is the canonical playful guide; firefly source art is adapted into package-local runtime art.

## Exact implementation

1. Manifest: ID/title `org.greia.luci-di-momo` / `activity.luci_di_momo.title`; languages `it,en`; collections `learn,play`; tag `numbers`; education `early_math,subitizing,quantity_comparison`, difficulty 2, age 4–6, adaptive 1–4; pointer input; required `display,pointer,audio.basic`, optional `touch`; event `firefly.garden_completed` completion; storage 1.
2. Create thin `main.py` plus `firefly_model.py`, `firefly_content.py`, `firefly_services.py`, `firefly_audio.py`, `firefly_art.py`, `firefly_renderer.py`, `firefly_app.py`.
3. Define frozen `FireflyRound(round_id, quantity, positions, choice_values, reveal_ms)`, `AttemptResult(correct, used_replay, hints_used)`, and `FireflySession` owning five rounds and one-shot terminal/event flags.
4. Levels: L1 quantities 1–3 canonical layouts/1600 ms; L2 1–4 mixed layouts/1400 ms; L3 1–5 varied layouts/1200 ms; L4 1–5 varied spacing/sprite size/1100 ms. Three numeral choices contain one answer and two unique in-range distractors.
5. Inject `random.Random`; enforce ≥72 logical px center separation and safe-playfield containment. Same seed produces identical rounds.
6. After reveal, show one sleeping-lantern silhouette and three 88×88 numeral choices. Replay is unlimited, sets `used_replay`, and is not failure. Wrong choice replays fireflies one-by-one, then restores the same choices without progress loss.
7. Persist `luci_di_momo.progress.v1`: schema, level, at most eight summaries. Apply README adaptation only after a five-round set.
8. Emit `firefly.garden_completed` once after round five with level, first-attempt count, and replays; use stable set idempotency.
9. Reuse `character.momo` with a local fallback. Adapt `fx.particles.fireflies` and contact-shadow sources into reviewed local masters/runtime PNGs. Icon: lantern plus three fireflies, no text.
10. Use `PygameCompletionScreen`; terminal freezes simulation. READY follows first presented playable frame.

## Tests

- Exact manifest/event and collision-free ID.
- Seed determinism, level bounds, unique choices, safe spacing, and correct answers.
- Wrong/replay paths retain round identity; five completions emit one event; restart cannot duplicate it.
- Malformed storage recovers safely and history stays ≤8.
- Shared viewport mapping rejects protected input; static idle does not redraw; terminal freezes/restarts.

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

Expected: exit 0 with no failures/errors/skips introduced.

## Stop conditions

- Current shared-visual/manifest source cannot support the package without platform edits.
- Object size/spacing reveals the answer, text is required, or terminal repaints continuously.

## Handoff

Return the standard packet plus seeded challenge matrix, cache bounds, idle redraw count, manifest/emission proof, asset hashes, and SOURCE label.
