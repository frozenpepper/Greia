# Session 11 — Catalogue integration and cumulative source gate

**Provider calls:** forbidden
**Prerequisite:** Sessions 00–10 accepted and committed
**Commit:** `test(activity): gate early-learning portfolio`

## Outcome

All ten packages are discoverable through the existing catalogue, their cross-package contracts are enforced by one portfolio regression suite, stable product documentation records the accepted scope, and the complete local source gate passes at one recorded commit.

## Preconditions

- Pull current `main`; confirm no uncommitted package work and verify all ten handoff packets.
- Read current source discovery, validator, manifest schema, product-document ownership, active plan, and `HANDOVER.md`. Run discovery before proposing any registry edit.

## Allowed files

```text
tests/test_early_learning_activity_portfolio.py
docs/product/EARLY_LEARNING_ACTIVITY_PORTFOLIO.md
docs/DOCUMENTATION.md
docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md
docs/plans/2026-08-24_EARLY_LEARNING_ACTIVITY_EXPANSION/README.md
HANDOVER.md
```

## Forbidden changes

- No Activity implementation/art/content edits, new catalogue owner, manual duplicate registry, event/reward policy change, or claim of simulator/physical effectiveness.
- Do not repair a failed package in this gate session; return it to its owning session.

## Evidence and source decisions

The repository's existing manifest discovery remains authoritative. This session adds a cross-package test only for predicates that one package test cannot prove: uniqueness, portfolio membership, language/audience completeness, event/privacy policy, and aggregate size.

## Exact implementation

1. Resolve the ten directories through the same production discovery owner used by Greia Shell. If all appear exactly once, make no catalogue production change. If one is absent, stop and amend its package session rather than creating a second registry.
2. Add `tests/test_early_learning_activity_portfolio.py` with a constant ordered tuple of the ten IDs/directories from the README. Assert each package validates, resolves exactly once, has a distinct launcher icon SHA-256, declares `it,en`, has the planned audience/difficulty/input metadata, and declares exactly the planned event kinds.
3. Assert only `Posta di Leo`, `Tre Carte, Una Storia`, and `Morbidi Mostriciattoli` declare creation events; their declared event schemas prohibit child-authored text. Assert no new package requests network, microphone, raw input, filesystem, subprocess, profile-write, or direct progression authority.
4. Assert package-local regular-file size is at most 12 MiB per Activity and aggregate size is at most 80 MiB, excluding rejected bytecode because any `__pycache__`, `.pyc`, archive, audio-review master, or generated contact sheet in a package is itself a failure. A limit breach requires measured asset optimization in the owning session.
5. Assert Italian and English localization key sets match per Activity; speech-bearing Activities contain every locale-specific reviewed clip listed by Session 00; silent visual fallback is represented in model tests and not inferred from file presence.
6. Create `docs/product/EARLY_LEARNING_ACTIVITY_PORTFOLIO.md` as the stable child-facing scope: catalogue table, age lanes, learning outcomes, non-assessment rule, language/content review rule, no-pressure rule, creation/privacy limits, and explicit non-duplication boundaries. Do not copy session mechanics or transient evidence into it.
7. Add the new product document to `docs/DOCUMENTATION.md` under product requirements. Update this README status to `SOURCE-CLOSED; simulator and physical acceptance pending`, record the exact commit candidate and executed commands, append the active plan's progress ledger, and update `HANDOVER.md` without changing the R7 blocking cursor.
8. Remove package bytecode, run all ten focused suites, the portfolio suite, every Activity validator, and `make verify`. Capture exact output, duration, Git SHA, and dirty-state result in the handoff.

## Tests

- Ten exact IDs/directories; discovery once each; icon hashes unique; locale/audience/input/event metadata exact.
- Forbidden capabilities absent; creation-event privacy; no undeclared event.
- No build/archive/review artifacts; per-package and aggregate footprint caps.
- Product document is linked from documentation authority; active blocking cursor unchanged.
- Complete repository verification from a clean commit candidate.

## Local gate

```bash
find activities/luci_di_momo activities/casa_del_dieci activities/bottega_delle_misure activities/specchi_magici activities/festa_delle_rime activities/officina_dei_suoni activities/posta_di_leo activities/tre_carte_una_storia activities/nanna_delle_nuvolette activities/morbidi_mostriciattoli -type d -name __pycache__ -prune -exec rm -rf {} +
PYTHONPATH=src:tests:. python3 -m unittest tests.test_early_learning_activity_portfolio -v
for activity_dir in activities/luci_di_momo activities/casa_del_dieci activities/bottega_delle_misure activities/specchi_magici activities/festa_delle_rime activities/officina_dei_suoni activities/posta_di_leo activities/tre_carte_una_storia activities/nanna_delle_nuvolette activities/morbidi_mostriciattoli; do PYTHONPATH=src:tools python3 tools/validate_activity.py "$activity_dir" || exit 1; done
```

Expected: portfolio tests pass; ten validators exit 0.

## Cumulative gate

```bash
make verify
git diff --check
git status --short
```

Expected: `make verify` and diff check exit 0; status contains only the planned documentation/test changes before commit and is clean after commit.

## Stop conditions

- Discovery needs a second catalogue authority, a package violates privacy/capability rules, or any package/art/content test is red.
- `make verify` is red or the source tree contains unowned files; do not label the portfolio SOURCE-CLOSED.

## Handoff

Return the standard packet plus exact discovered catalogue, icon hashes, manifest/event/capability matrix, package and aggregate byte counts, full gate output, documentation links, commit SHA, and explicit `SOURCE-CLOSED; simulator and physical acceptance pending` boundary.
