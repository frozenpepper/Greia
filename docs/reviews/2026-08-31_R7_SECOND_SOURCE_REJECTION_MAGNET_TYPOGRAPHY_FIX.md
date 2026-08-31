# Greia — R7 Second Current-Head Source Rejection and Magnet Typography Fix

**Date:** 2026-08-31  
**Repository/branch:** `frozenpepper/Greia` / `main`  
**Rejected source SHA:** `650ce2ebeb9eaee82efb292745568afabde7cce9`  
**Corrective runtime commit:** `0828cd35b957203775759f442069b9d51e0caf5a`  
**Disposition:** **SECOND MASKED HOT-PATH DEFECT FIXED / POST-FIX EXECUTION REQUIRED**

---

## 1. Context

The first current-head R7 acceptance attempt at `9b6b055e` was rejected because the Encyclopedia Earth page bypassed `VisualLibrary` with direct `pygame.image.load()` / `smoothscale()` in its draw path. Commit `6024240` removed that bypass.

The operator then repeated the exact-current source gate at:

```text
650ce2ebeb9eaee82efb292745568afabde7cce9
```

The Earth regression was confirmed fixed. `make verify` then surfaced the next assertion in the same Encyclopedia hot-path contract: `pages/magnet.py` constructed a `pygame.font.SysFont()` inside its frame draw path.

This second rejection is therefore not a regression caused by the Earth fix. It is a pre-existing masked violation exposed after the earlier assertion became green.

---

## 2. Exact second-run evidence

The local operator reported:

```text
working_tree_clean_before_test: PASS
working_tree_clean_after_test: PASS
focused_source_gate: PASS
focused tests: 136 PASS
backend_audit: PASS
backend_audit_blockers: 0
chrome_audit: PASS
chrome_audit_blockers: 0
make_verify: FAIL
make_verify_test_count: 1507
failures: 1
planet_earth_page_hotpath_decode_scale_present: NO
postfix_runtime_commit_in_history: YES
Simulator: not run after aggregate failure
Acer: unreachable / not run
verdict: REJECTED
```

The remaining failure was:

```text
tests.test_activity_enciclopedia.EncyclopediaSourceContractTests
  .test_page_hot_paths_do_not_decode_or_smoothscale_assets
```

The forbidden token was:

```python
pygame.font.SysFont(None, 22)
```

inside:

```text
activities/enciclopedia_greia/pages/magnet.py
MagnetPage._draw_bar_magnet()
```

The method is called several times from the normal page draw path, so the constructor was per-frame-capable.

---

## 3. Root cause

The Encyclopedia already provides a dedicated bounded typography owner:

```text
activities/enciclopedia_greia/enciclopedia_services.py
CachedEncyclopediaTypography
```

Its contract is:

```text
GreiaTypography font-family/role ownership
font objects cached by role+size
MAX_TEXT_SURFACES = 160
LRU-style cache of repeated rendered lines
```

`MagnetPage` already receives this object through:

```python
self.context.typography
```

and already uses it for the title/caption.

However, `_draw_bar_magnet()` was a `@staticmethod`, so it could not reach the injected typography service and instead constructed an ad-hoc system font for the constant `N` / `S` pole labels.

That violated both the performance contract and the visual-system contract:

1. font construction was possible on every rendered frame;
2. the constant `N`/`S` surfaces bypassed the bounded rendered-text cache;
3. the page selected a host/system font rather than Greia's canonical typography family.

---

## 4. Corrective implementation

Committed:

```text
0828cd35b957203775759f442069b9d51e0caf5a
Encyclopedia: route magnet labels through Greia typography
```

The correction:

- converts `_draw_bar_magnet()` from a static helper to an instance method;
- removes `pygame.font.SysFont()` and direct font rendering;
- renders the constant pole labels through:

```python
self.context.typography.render(
    label,
    FontRole.CONTROL,
    22,
    (255, 255, 255),
)
```

Because the real Encyclopedia context uses `CachedEncyclopediaTypography`, the two constant surfaces become bounded cached entries after their first render.

No new cache, font subsystem or Activity-local typography abstraction was introduced.

No R7 Home/input/display/session/sandbox authority changed.

---

## 5. Test disposition

Do **not** weaken the existing hot-path test for this correction.

Although the current implementation is lexical, both successive failures have now demonstrated that it is catching concrete Acer-floor/product violations rather than merely freezing class/file shape:

```text
first masked violation: page-level image decode/scale
second masked violation: page-level font construction
```

The correct engineering response in both cases is to restore the existing visual/typography ownership boundaries.

A later test-quality pass may replace the lexical implementation with a stronger architecture/behavior test, but only if the same contract remains protected.

No new regression test was added merely because this line changed.

---

## 6. Current evidence boundary

After `0828cd35`:

```text
9b6b055e source gate: REJECTED — Earth decode/scale masked later assertions
6024240 Earth fix: IMPLEMENTED
650ce2eb source gate: REJECTED — Earth fix confirmed; Magnet SysFont exposed
0828cd35 Magnet typography fix: IMPLEMENTED
post-0828cd35 focused source gate: NOT RUN
post-0828cd35 audits: NOT RUN
post-0828cd35 make verify: NOT RUN
post-0828cd35 Simulator Home matrix: NOT RUN
R7.2/R7.3 Acer physical acceptance: INCOMPLETE
ordinary-family public release: NOT READY
```

No post-fix PASS is inferred from source inspection.

---

## 7. Next exact step

Repeat the same disciplined exact-current gate on a clean current `main`:

1. freeze the exact current SHA;
2. run the 17 focused files using `unittest discover` patterns (not dotted `tests.*` imports);
3. require backend audit `blockers=0`;
4. require system-chrome audit `blockers=0`;
5. run `make verify` and stop on the first failure;
6. only after a green aggregate source gate, run the real-Shell Simulator matrix for Encyclopedia, Writing, Painting, one animated Activity and the hostile fixture;
7. visually inspect the protected Home/no-duplicate-Home evidence and scan Encyclopedia output for libpng/runtime failures;
8. only then attempt same-SHA Acer acceptance if the reference Acer is reachable.

The operator's all-pages scan at the rejected SHA found this `magnet.py` constructor as the remaining direct `pygame.font.SysFont` / `pygame.font.Font` occurrence in `activities/enciclopedia_greia/pages/*.py`. The next execution still owns the final proof; do not treat that scan alone as aggregate acceptance.

---

## 8. Active-plan append entry

When the active append-only plan is next safely updated, append:

```text
2026-08-31 — R7 second source rejection + Encyclopedia Magnet typography correction
- Implemented: after the Earth VisualLibrary fix, exact-current gate at 650ce2eb confirmed the Earth draw path clean and exposed the next masked Encyclopedia hot-path violation: MagnetPage._draw_bar_magnet constructed pygame.font.SysFont per-frame-capably. Commit 0828cd35 converts that helper to an instance method and routes constant N/S labels through the existing CachedEncyclopediaTypography / GreiaTypography owner (FontRole.CONTROL, size 22), gaining the existing bounded rendered-text cache and canonical Greia font family.
- Tests/evidence: 650ce2eb focused discovery gate 136 PASS; backend blockers=0; system-chrome blockers=0; make verify ran 1507 tests and failed one assertion on magnet.py SysFont. Earth scan was empty and its previous visual-foundation test passed. Simulator/Acer were not run after aggregate failure; Acer remained unreachable. Post-0828cd35 execution is not claimed here.
- Decisions: preserve the Encyclopedia hot-path contract; do not weaken its lexical check merely because it exposed successive masked defects. Reuse the existing cached typography owner; do not create another page cache or font abstraction.
- Remaining blockers: post-0828cd35 exact-current source gate; same-SHA Simulator Home matrix; R7.2/R7.3 Acer physical acceptance; then R7.4/controller and remaining ADR-0014 direct/compositor evidence.
- Next exact step: pull/freeze current main, repeat focused discovery tests + both audits + make verify; if green continue same-SHA Simulator, then Acer when reachable.
- Commit(s): 0828cd35b957203775759f442069b9d51e0caf5a; this review commit following it.
```
