# R7.3 Home Overlay — Post-Modernization Evidence Correction

**Date:** 2026-08-30  
**Status:** current continuation/evidence correction; post-fix execution pending  
**Current runtime source reviewed:** `45b185d92bb577a3f40c741552fe247a8f6d0b70`  
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

## 2. First fix — fail-loud trusted Home rendering

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

The code now:

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

## 3. Second fix — preserve Home during dirty-rectangle updates

Source review after `83738f7` found a second, more general presentation edge case.

`pygame.display.flip()` is always a full display presentation, so drawing trusted chrome immediately before the flip guarantees that the Home pixels are included.

`pygame.display.update(...)` may instead receive a dirty rectangle or list of dirty rectangles. The first fix drew Home and then forwarded the Activity's original dirty update unchanged. If that dirty region excluded the protected Home corner, the Home pixels were not guaranteed to reach the displayed window.

This was a general Simulator compatibility issue, not the explanation for the Encyclopedia report, because the Encyclopedia uses `pygame.display.flip()`.

Commit:

```text
45b185d92bb577a3f40c741552fe247a8f6d0b70
Simulator: preserve trusted Home on partial display updates
```

implements a bounded fix:

- Greia draws trusted chrome before presentation as before;
- the Activity's requested dirty update is preserved unchanged;
- when the update is partial, Greia performs one additional update only for `ActivitySystemChromeLayout.protected_region`;
- a full update/flip does not receive the extra protected-region update;
- no full-screen proxy/copy or Activity-side Home ownership was introduced.

This preserves the Activity dirty-rendering optimization while guaranteeing that the small trusted chrome footprint is presented even when the Activity updates another part of the window.

No extra source-string test was added. The next execution should validate the user-visible behavior rather than freeze function/file text shape.

---

## 4. Evidence consequence

The following distinction is mandatory.

### Still valid

The `e2b831da` evidence remains valid for the catalogue modernization state it actually tested:

- Activity system-chrome ownership audit `blockers=0`;
- Activity backend-independence audit `blockers=0`;
- the source gate that executed at that SHA;
- the Activity decomposition/cleanup decisions made in that completed pass.

The Activity-modernization pass therefore stays **COMPLETE**. Do not reopen all Activities because a later Simulator platform adapter changed.

### Stale for current Home visibility

Any Simulator runtime/visual evidence captured before `45b185d9` is stale for the specific claim:

> the current Simulator visibly presents the Greia-owned Home layer over migrated Activities through the current presentation adapter.

Older captures or survival runs cannot certify the runtime behavior of `src/greia_simulator/python_activity.py` after the two Home-presentation changes.

No focused-test, visual/runtime, `make verify`, or Acer PASS is claimed for `45b185d9` merely because the source diff is small.

---

## 5. Exact next verification sequence

Do not go directly from the old `e2b831da` source gate to Acer acceptance. The current candidate changed after that evidence.

On the next owner-controlled checkout, use one exact current SHA and:

1. run the focused Simulator tests relevant to the compatibility bootstrap/display adapter;
2. launch the Encyclopedia through the real Greia Simulator and visually verify:
   - Home visibly present in the canonical protected corner;
   - normal Encyclopedia navigation works;
   - Activity-internal Back remains distinct from Greia Home;
   - Home exits cleanly to Shell;
3. rerun a representative migrated-Activity Simulator matrix, at minimum Writing, Painting, Encyclopedia and one continuously animated/game Activity;
4. if a safe small developer fixture or existing Activity path uses `pygame.display.update(rect/list)`, exercise it and verify partial presentation cannot make Home disappear; do not modify an Activity merely to manufacture this evidence;
5. rerun the canonical R7.3 source gate from `docs/testing/2026-08-29_R7_R73_TRUSTED_SYSTEM_CHROME_SOURCE_AND_ACER_ACCEPTANCE.md` on that same SHA:
   - focused R7.3 source suite;
   - backend-independence audit `blockers=0`;
   - system-chrome ownership audit `blockers=0`;
   - `make verify` exit 0;
6. only after that source state is green, deploy that **exact same SHA** to the reference Acer and execute the R7.2/R7.3 physical protocol.

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

## 7. Active-plan progress entry

The active architecture plan is append-only and large. Preserve this exact semantic entry for its next safe append rather than rewriting/truncating plan history through a connector-only edit:

```text
2026-08-30 — R7.3 post-Activity Home presentation correction
- Implemented: after the completed catalogue Home-ownership migration, manual Simulator inspection exposed a platform presentation failure where migrated Activities could run without visibly presented Home. Commit 83738f7 removed broad exception swallowing from the trusted Simulator Home render path. Follow-up source review found partial pygame.display.update(rect/list) could still omit the protected corner from the actual window update; commit 45b185d9 preserves the Activity dirty update and performs one additional bounded update only for ActivitySystemChromeLayout.protected_region.
- Tests/evidence: no current-SHA execution PASS is claimed in this connector tranche. Historical e2b831da Activity modernization/audit evidence remains valid for that source state, but pre-45b185d9 Simulator Home visual/runtime evidence is stale for current presentation behavior.
- Decisions: keep the Activity catalogue modernization pass closed; fix the platform adapter rather than restoring Activity-owned Home. Preserve dirty-region rendering rather than forcing full-screen updates. Continue pruning brittle source-shape tests; do not add a string-presence test for this fix.
- Remaining blockers: execute focused Simulator tests and visual Home matrix, rerun the R7.3 source gate on one exact current SHA, then execute same-SHA R7.2/R7.3 Acer physical acceptance.
- Next exact step: current-SHA Simulator Home verification (Encyclopedia, Writing, Painting, animated Activity; partial-update path where already available), then exact R7.3 source gate, then same-SHA Acer protocol.
- Commits: 83738f737a41aec7c139b3a4a3363e746ba0f266, 45b185d92bb577a3f40c741552fe247a8f6d0b70.
```

---

## 8. Current disposition

```text
Activity-modernization catalogue pass: COMPLETE (historical closure at e2b831da)
Simulator Home fail-loud source fix: IMPLEMENTED at 83738f7
Simulator partial-update Home hardening: IMPLEMENTED at 45b185d9
Current Simulator Home visual/runtime acceptance: NOT YET RERUN
R7.3 source acceptance on current post-fix SHA: NOT YET RERUN
R7.2/R7.3 Acer physical acceptance: INCOMPLETE
R7 overall: OPEN
Ordinary-family public release: NOT READY
```

The next legitimate blocking work is R7.3 verification/physical acceptance, followed by R7.4 controller/system-input ownership and then the remaining ADR-0014 direct/compositor evidence. Public-release work must continue to use `docs/release/GREIA_PUBLIC_RELEASE_READINESS.md` as the release gate rather than treating source-green development state as family-release certification.
