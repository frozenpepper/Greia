# Session 12 — Simulator interaction and visual acceptance

**Provider calls:** forbidden
**Prerequisite:** Session 11 SOURCE-CLOSED commit accepted; no later source change
**Production edits:** forbidden; evidence/docs only

## Outcome

The ten source-closed Activities pass one reproducible Greia Activity Simulator review for launch, protected navigation, Italian/English interaction, required semantic paths, persistence, terminal behavior, and responsive visual integrity. Evidence remains `SIMULATOR VISUAL REVIEW`, not physical or production-backend proof.

## Preconditions

- Pull current `main`; record SHA and require a clean tree. If Activity/runtime source changed after Session 11, return to Session 11.
- Read `docs/testing/2026-08-19_ACTIVITY_SIMULATOR_ACCEPTANCE.md`, responsive UI acceptance, Activity skill, visual skill, and current Simulator CLI help.
- Use an isolated state directory and a free localhost bridge port; never reuse profile data from a different checkout.

## Allowed files

```text
docs/reviews/2026-08-24_EARLY_LEARNING_ACTIVITY_SIMULATOR_ACCEPTANCE.md
docs/plans/2026-08-24_EARLY_LEARNING_ACTIVITY_EXPANSION/README.md
docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md
HANDOVER.md
tmp/early-learning-activity-simulator/**
```

## Forbidden changes

- No production, test, package, art, manifest, content, runtime, simulator, or platform edits.
- No standalone Pygame harness, GitHub Actions, VM/physical claim, pedagogy/effectiveness claim, or acceptance based only on screenshots.

## Evidence and source decisions

The Simulator composes real catalogue/package/profile/capability/UI owners around a synthetic device. It can prove source-connected interaction and responsive semantics, but not Bubblewrap host denial, physical input/audio, Acer resource use, boot, scanout, or the selected R7 production backend.

## Exact implementation

1. Create `tmp/early-learning-activity-simulator/` with `state/`, `screens/it/`, `screens/en/`, and `logs/`. Record `git rev-parse HEAD`, `git status --short`, Python/Pygame versions, Simulator status, viewport, UI setting, locale, and capability set in the report.
2. Start the real Simulator from this checkout with its isolated state. Drive it only through visible UI and `tools/greia_simulator_ctl.py`; do not import an Activity's app class directly.
3. For every Activity at 1024×600 NORMAL in Italian: launch from catalogue, verify first usable frame/READY, verify real protected Home and conditional Back remain visible and unintercepted, exercise one complete semantic path, capture start/core/end screenshots, exit with Home, relaunch, and verify declared durable state. Repeat the same path in English without carrying an Italian in-progress session.
4. Run one additional viewport per Activity: Luci 1111×700 LARGE; Casa 1280×800 COMPACT; Bottega 1366×768 NORMAL; Specchi 1920×1080 LARGE; Festa 1111×700 COMPACT; Officina 1280×800 LARGE; Posta 1366×768 COMPACT; Tre Carte 1920×1080 NORMAL; Nanna 1111×700 LARGE; Morbidi 1366×768 NORMAL. Confirm no clipping, overlap, tiny targets, exposed Linux chrome, or mismatch between draw/hit geometry.
5. Exercise exact concepts: Luci flashes 1–5 and a misleading-size comparison; Casa completes one number bond and one take-away; Bottega rejects a gapped unit rail and accepts a correct one; Specchi reflects one rotated piece; Festa plays/replays one rhyme target; Officina builds one reviewed sound family; Posta saves and reloads one Unicode postcard; Tre Carte rejects one order then saves a captioned story; Nanna sleeps three clouds without error state; Morbidi saves and reloads one unnamed portrait.
6. Verify terminal ownership: the six completion Activities use a frozen bounded completion/continuation state and emit once; Posta, Tre Carte after save, Nanna, and Morbidi remain calm explicit loops with no fake system navigation. Force Home during active motion/audio in each package and require prompt clean termination with no stale audio/subprocess.
7. Verify persistence boundaries using only visible relaunch plus Simulator-owned state inspection: no raw child text in events, creation save precedes event, item caps/sheets work for the three galleries, malformed-state fixtures from source tests are not recreated by hand in the UI session.
8. Inspect all 60 primary screenshots plus ten alternate-viewport screenshots at native pixels. Record PASS/FAIL per image for hierarchy, target size, text fit, contrast, character consistency, semantic clarity, protected chrome, and visible feedback. Keep screenshot/contact-sheet files under `tmp/`; commit only the report with SHA-256 manifest and selected small evidence images only when repository visual-evidence policy explicitly permits them.
9. Capture bridge/Activity logs and require zero traceback, uncaught exception, missing localization key, missing asset, repeated READY, undeclared event, or stop-time warning. Record start-to-ready observations without converting them into physical performance evidence.
10. If every row passes, update README to `SIMULATOR ACCEPTED; physical Acer acceptance pending`, append the art plan checkpoint/ledger, visual resume, and `HANDOVER.md`. Preserve R7 as blocking.

## Tests

- Twenty locale runs, ten alternate viewports, 70 primary screenshots, and one concept path per package are accounted for.
- READY, protected Home/Back, STOP, audio cancellation, event idempotency, save/reload, and terminal/open-loop semantics match each contract.
- Screenshot review and logs contain no clipping, hidden navigation, stale language, missing asset/key, traceback, or warning.
- Report states exact SHA and `SIMULATOR VISUAL REVIEW`; it explicitly withholds physical, backend, learning-efficacy, and release claims.

## Local gate

```bash
python3 tools/greia_simulator.py --repo-root . --state-dir tmp/early-learning-activity-simulator/state --language it
```

Expected: Simulator opens its Greia-owned device window and loopback control bridge from the recorded checkout; keep this process running while executing the protocol.

## Cumulative gate

```bash
python3 tools/greia_simulator_ctl.py status
PYTHONPATH=src:tests:. python3 -m unittest tests.test_early_learning_activity_portfolio -v
git diff --check
```

Expected: status reports the intended isolated Simulator; portfolio tests and diff check exit 0; all report rows are PASS.

## Stop conditions

- Any concept, locale, protected-navigation, persistence, log, or viewport row fails; preserve evidence and return to the owning implementation session.
- Source SHA changes during execution, evidence cannot be bound to the checkout, or review would require a production edit.

## Handoff

Return the standard packet plus Simulator/state identity, 70-image checklist, screenshot hash manifest, per-Activity interaction trace, logs, storage/event observations, exact source SHA, report link, and `SIMULATOR ACCEPTED; physical Acer acceptance pending` boundary.
