# R7.3 Home Overlay — Post-Modernization Evidence Correction

**Date:** 2026-08-30  
**Status:** current continuation/evidence correction  
**Current source reviewed:** `83738f737a41aec7c139b3a4a3363e746ba0f266`  
**Phase:** R7.3 trusted system chrome, still subordinate to the active architecture-remediation plan  
**Release relationship:** `docs/release/GREIA_PUBLIC_RELEASE_READINESS.md` remains the public-release gate; this correction does not bypass R7.

---

## 1. Why this correction exists

The catalogue-wide R7.3 Activity migration and architecture/performance pass was closed at `e2b831da19a1ae706a8b675985f4191881a95321`, with its exact source/audit evidence recorded in `docs/plans/2026-08-29_R7_R73_ACTIVITY_MODERNIZATION.md`.

After that closure, a real Simulator presentation defect was found while manually inspecting the Encyclopedia: Activity-owned Home had correctly been removed, but the expected platform-owned replacement was not visibly present.

The defect was not in the Encyclopedia. The Activity follows the intended architecture:

- `activities/enciclopedia_greia/enciclopedia_app.py` draws only Activity content;
- it leaves Greia's protected region out of Activity pointer authority;
- it presents through `pygame.display.flip()`;
- it does not draw or hit-test the real Greia Home control.

The defect was in the Simulator compatibility presentation layer.

---

## 2. Implemented fix at `83738f7`

Commit:

```text
83738f737a41aec7c139b3a4a3363e746ba0f266
Simulator: make trusted Home overlay deterministic and fail loud
```

Before that commit, `src/greia_simulator/python_activity.py` wrapped trusted Home drawing in a broad exception handler and silently ignored any rendering failure:

```python
try:
    ... draw trusted chrome ...
except Exception:
    pass
```

That failure mode was unacceptable because the Activity could keep running while the visible platform Home control disappeared.

The current code now:

- imports the platform Pygame chrome renderer from trusted Greia source before Activity package path insertion;
- derives layout from `ActivitySystemChromeLayout`;
- draws the trusted overlay after each Activity frame presentation hook;
- does not suppress Home-rendering exceptions;
- retains Simulator-side Home hit testing outside Activity code.

The product architecture is unchanged:

```text
Activity
  -> draws its own content only
  -> presents its frame
Greia Simulator trusted compatibility layer
  -> draws Home last
  -> consumes Home pointer input
  -> ends the Activity independently of Activity cooperation
```

This remains Simulator/developer evidence only. It does not prove the installed Legacy-X sibling-window trust boundary or the final direct/compositor architecture.

---

## 3. Evidence consequence

The following distinction is mandatory.

### Still valid

The `e2b831da` evidence remains valid for the catalogue modernization state it actually tested:

- Activity system-chrome ownership audit `blockers=0`;
- Activity backend-independence audit `blockers=0`;
- the source gate that executed at that SHA;
- the Activity decomposition/cleanup decisions made in that completed pass.

The Activity-modernization pass therefore stays **COMPLETE**. Do not reopen all Activities because a later Simulator platform adapter changed.

### Stale for current Home visibility

Any Simulator runtime/visual evidence captured before `83738f7` is stale for the specific claim:

> the current Simulator visibly presents the Greia-owned Home layer over migrated Activities.

In particular, older captures or survival runs cannot certify the runtime behavior of `src/greia_simulator/python_activity.py` after its Home-rendering change.

No visual/runtime PASS is claimed for `83738f7` merely because the source change is straightforward.

---

## 4. Additional source-review observation: dirty-rectangle update hardening

The current Simulator compatibility patch wraps both:

```text
pygame.display.flip()
pygame.display.update(...)
```

For `flip()`, the sequence is unambiguous: Greia draws trusted chrome immediately before the full display flip.

For `display.update(...)`, however, the wrapper currently draws trusted chrome and then forwards the Activity's original update arguments unchanged. If a future/current Activity uses a dirty rectangle or dirty-rectangle list that excludes the Home corner, the newly drawn Home pixels are not guaranteed to be included in that presentation update.

This is a **general Simulator hardening issue**, not the explanation for the Encyclopedia report: the Encyclopedia uses `pygame.display.flip()`.

Before claiming that the Simulator compatibility adapter preserves visible Home for arbitrary conforming Pygame presentation styles, change the `display.update(...)` path so the protected chrome region is always included in the presented region (or otherwise perform an equivalent bounded trusted presentation). Do not solve this by moving Home drawing back into Activities.

A behavioral check is preferable to another source-string test. The user-visible contract is that a dirty-region Activity cannot accidentally omit platform Home from the displayed update.

---

## 5. Exact next verification sequence

Do not go directly from the old `e2b831da` source gate to Acer acceptance. The current candidate changed after that evidence.

On the next owner-controlled checkout, use one exact current SHA and:

1. resolve the dirty-rectangle `display.update(...)` compatibility issue described in §4 if the current Simulator adapter is expected to support partial display updates;
2. run the focused Simulator tests relevant to the compatibility bootstrap/display adapter;
3. launch the Encyclopedia through the real Greia Simulator and visually verify:
   - Home visibly present in the canonical protected corner;
   - normal Encyclopedia navigation works;
   - Activity-internal Back remains distinct from Greia Home;
   - Home exits cleanly to Shell;
4. rerun a representative migrated-Activity Simulator matrix, at minimum Writing, Painting, Encyclopedia and one continuously animated/game Activity;
5. rerun the canonical R7.3 source gate from `docs/testing/2026-08-29_R7_R73_TRUSTED_SYSTEM_CHROME_SOURCE_AND_ACER_ACCEPTANCE.md` on that same SHA:
   - focused R7.3 source suite;
   - backend-independence audit `blockers=0`;
   - system-chrome ownership audit `blockers=0`;
   - `make verify` exit 0;
6. only after that source state is fixed and green, deploy that **exact same SHA** to the reference Acer and execute the R7.2/R7.3 physical protocol.

Acer acceptance remains required because Simulator evidence cannot establish that an Activity cannot cover the installed trusted sibling window, that protected input is consumed first by the real backend, or that the performance cost is acceptable on the Atom floor.

---

## 6. Test-suite direction

The current test count is not a product goal.

Continue removing tests that merely freeze implementation shape, duplicate a stronger audit, or scan source strings for historical names/functions. Keep tests that protect real behavior or architecture contracts, especially:

- security/trust boundaries;
- lifecycle and cleanup behavior;
- package/storage/profile/progression semantics;
- renderer-neutral Home geometry/action routing;
- backend-independence audits;
- real failure/rollback behavior;
- gameplay/domain rules whose regression would affect the child.

Do not add a trivial test merely to assert that one shell-script line or function-name string exists. When a regression is worth protecting, prefer the narrowest behavioral contract that would actually fail if the user-visible/platform invariant broke.

---

## 7. Current disposition

```text
Activity-modernization catalogue pass: COMPLETE (historical closure at e2b831da)
Current Simulator Home source fix: IMPLEMENTED at 83738f7
Current Simulator Home visual/runtime acceptance: NOT YET RERUN
R7.3 source acceptance on current post-fix SHA: NOT YET RERUN
R7.2/R7.3 Acer physical acceptance: INCOMPLETE
R7 overall: OPEN
Ordinary-family public release: NOT READY
```

The next legitimate blocking work remains R7.3 verification/physical acceptance, followed by R7.4 controller/system-input ownership and then the remaining ADR-0014 direct/compositor evidence. Public-release work must continue to use `docs/release/GREIA_PUBLIC_RELEASE_READINESS.md` as the release gate rather than treating source-green development state as family-release certification.
