# Greia — R7 Current-Head Source-Gate Rejection and Encyclopedia Earth Cache Fix

**Date:** 2026-08-31  
**Repository/branch:** `frozenpepper/Greia` / `main`  
**Rejected source SHA:** `9b6b055e48681714672869f8800a5f7a7c407165`  
**Corrective source commit:** `6024240034a20bb8724eaaf548d4ac14061bef43`  
**Disposition:** **SOURCE FIX IMPLEMENTED / POST-FIX EXECUTION REQUIRED**

---

## 1. Why this review exists

The current-head R7.2/R7.3 acceptance run correctly stopped before Simulator and Acer work because the aggregate source gate failed.

The failure was narrow and useful: the R7 focused source gate and both architecture audits were green, but `make verify` found that the recently polished Encyclopedia Earth page had reintroduced image decode/scaling below the established bounded `VisualLibrary` ownership boundary.

This is a correction record. It does not claim that the corrective commit has passed tests or Simulator execution.

---

## 2. Exact rejected evidence

The local agent froze and tested:

```text
source_sha: 9b6b055e48681714672869f8800a5f7a7c407165
origin_main_at_start: same
origin_main_before_acer: same
main_advanced_during_gate: NO
working_tree_clean_before_test: PASS
working_tree_clean_after_test: PASS
```

Source results:

```text
focused_source_gate: PASS
focused tests executed: 136
backend_audit: PASS
backend_audit_blockers: 0
chrome_audit: PASS
chrome_audit_blockers: 0
make_verify: FAIL
make_verify_test_count: 1507
```

`make verify` stopped on two assertions:

```text
tests.test_activity_enciclopedia.EncyclopediaSourceContractTests
  .test_page_hot_paths_do_not_decode_or_smoothscale_assets

tests.test_activity_enciclopedia_visual_foundation.EncyclopediaVisualFoundationTests
  .test_page_hot_paths_do_not_decode_or_scale_assets
```

Both pointed to the same code in:

```text
activities/enciclopedia_greia/pages/planet_earth.py
```

The page-level `_draw_earth()` fallback contained:

```python
pygame.image.load(...)
pygame.transform.smoothscale(...)
```

Because `_draw_earth()` is called from the normal frame draw path, the fallback was per-frame-capable disk/decode/scale work.

The operator correctly stopped. Simulator and Acer acceptance were not executed and remain incomplete.

---

## 3. Root cause

The direct fallback duplicated and bypassed an owner that already exists.

`activities/enciclopedia_greia/enciclopedia_services.py` owns `VisualLibrary`, including:

```text
explicit PLANET_ASSETS mapping
bounded LRU-style surface cache
package-local runtime lookup
PNG decode
transparent-surface conversion
size-specific smoothscale
fail-soft None result on expected asset/decode failures
```

The Earth page already called:

```python
self.context.visuals.planet("earth", diameter)
```

but then, when that returned `None`, it performed its own filesystem lookup, decode and scale inside the page renderer.

That second path violated the established architecture in three ways:

1. page rendering regained asset-loading policy;
2. the page bypassed the bounded VisualLibrary cache;
3. low-resource hot-path safety depended on whether the authored sprite lookup happened to succeed.

The correct fail-soft behavior was already available: if `VisualLibrary.planet()` cannot provide the authored Earth sprite, the page has a complete procedural Earth renderer.

---

## 4. Corrective implementation

Committed:

```text
6024240034a20bb8724eaaf548d4ac14061bef43
Encyclopedia: keep Earth asset decode behind VisualLibrary
```

The page now only asks its injected visual provider for the prepared sprite:

```python
planet_loader = getattr(self.context.visuals, "planet", None)
sprite = planet_loader("earth", diam) if callable(planet_loader) else None
```

If the provider has no planet surface, the existing procedural renderer is used.

Removed from the page:

```text
direct Path lookup of assets/runtime/earth_planet_sprite.png
pygame.image.load(...)
pygame.transform.smoothscale(...)
broad page-local exception swallowing around that fallback
```

No change was made to `VisualLibrary.planet()` because it already owns the correct bounded cache-miss behavior.

No Activity-owned Home behavior, R7 display/input authority, sandbox grant, or device access changed.

---

## 5. Why the two source-string tests were not weakened

Greia generally avoids implementation-shape/string-presence tests when they merely freeze refactoring shape.

These two assertions are retained in this correction because the reported failure demonstrated that they currently guard a real product contract:

```text
no image decode / smoothscale in Encyclopedia page hot paths
```

That contract is independently established by:

```text
skills/greia-activity-authoring/ENGINEERING.md
docs/engineering/GREIA_PERFORMANCE_BEST_PRACTICES.md
docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md
```

The reference Acer floor makes repeated image decode/scaling a correctness concern. The fix therefore changes production ownership rather than changing the tests.

A later test-quality tranche may replace these lexical checks with an equally strong or stronger behavioral/architectural check if one is demonstrably less brittle. That is not part of this failure correction.

---

## 6. Focused-gate invocation issue discovered by the local run

The originally supplied focused command used module imports such as:

```bash
PYTHONPATH=src python3 -m unittest tests.test_...
```

On the operator machine, an installed regular package named `tests` shadowed the repository's namespace-style `tests/` directory.

The operator correctly used an evidence-only discovery runner and obtained the intended 136-test focused PASS. `make verify` already uses test discovery and was unaffected.

Future local instructions should prefer repository discovery patterns, for example:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_system_chrome.py' -v
```

rather than relying on `tests.<module>` imports in environments where `tests/` has no `__init__.py`.

This is an invocation/environment issue, not the product failure above.

---

## 7. Evidence boundary after the fix

Current honest state after `6024240`:

```text
R7 focused gate at rejected SHA 9b6b055e: PASS
backend audit at rejected SHA: blockers=0
chrome audit at rejected SHA: blockers=0
aggregate gate at rejected SHA: REJECTED (2 Earth hot-path failures)
Earth VisualLibrary ownership fix: IMPLEMENTED
post-fix focused gate: NOT RUN
post-fix audits: NOT RUN
post-fix make verify: NOT RUN
post-fix Simulator Home matrix: NOT RUN
R7.2/R7.3 Acer physical acceptance: INCOMPLETE
ordinary-family public release: NOT READY
```

Do not infer post-fix PASS from the small source change.

---

## 8. Next exact execution sequence

On a clean, refreshed current `main`, freeze one new exact SHA and execute:

1. focused R7 + Simulator + Encyclopedia source tests using `unittest discover` patterns so local `tests` package shadowing cannot change what runs;
2. `tools/audit_activity_backend_independence.py activities` — require `blockers=0`;
3. `tools/audit_activity_system_chrome_ownership.py --strict` — require `blockers=0`;
4. `make verify` — require exit 0;
5. only if source is green, execute the current-head real-Shell Simulator matrix for Encyclopedia, Writing, Painting, one animated Activity and the hostile fixture;
6. inspect Simulator screenshots for canonical Home/no duplicate Activity Home and scan for libpng/runtime errors;
7. only then execute same-SHA Acer R7.2/R7.3 physical acceptance when the reference Acer is reachable.

Acer was unreachable during the rejected run, so physical evidence remains explicitly incomplete even if the post-fix source gate becomes green.

---

## 9. Active-plan progress entry

The active plan is append-only. If this review is being consumed from a checkout that can safely append the complete plan file, append the following entry to:

```text
docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md
```

```text
2026-08-31 — R7 current-head source-gate rejection + Encyclopedia Earth cache correction
- Implemented: current-head acceptance at 9b6b055e correctly rejected before Simulator/Acer because make verify found page-local pygame.image.load/smoothscale in Encyclopedia space.earth. Root cause was a redundant direct filesystem fallback below the already-bounded VisualLibrary. Commit 6024240 removes that bypass; VisualLibrary remains the sole authored-planet decode/scale/cache owner and the page falls back procedurally when no prepared sprite is available.
- Tests/evidence: rejected SHA 9b6b055e: focused gate 136 PASS; backend audit blockers=0; system-chrome audit blockers=0; make verify 1507 tests with 2 failures, both the same Earth hot-path violation. Simulator/Acer not run per stop-on-first-source-failure. Post-fix execution is not claimed in this connector environment.
- Decisions: preserve the real Acer-floor hot-path contract; do not weaken the two tests merely because they are lexical today. No new test was added. Fix ownership at VisualLibrary. Use unittest discover patterns in future focused local gates to avoid installed tests-package shadowing.
- Remaining blockers: post-fix exact-current source gate; current-SHA Simulator Home matrix; R7.2/R7.3 Acer physical acceptance; then R7.4/controller and remaining ADR-0014 direct/compositor evidence.
- Next exact step: pull current main, freeze exact SHA, rerun focused discovery tests + both audits + make verify; if and only if green continue Simulator, then same-SHA Acer when reachable.
- Commit(s): 6024240034a20bb8724eaaf548d4ac14061bef43; docs correction commit following it.
```

This review itself is the durable correction record until that append can be performed without replacing/truncating the large historical plan.
