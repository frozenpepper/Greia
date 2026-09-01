# R7 current-head usage-limit lifecycle review

**Date:** 2026-09-01  
**Blocking phase:** R7.2 / R7.3 exact-current source, Simulator and physical acceptance  
**Starting current-main SHA:** `bbde1606aa1e1a298b1e98f014f00a29b24368e3`  
**Latest runtime/source correction in this review:** `496786ef64c8ecc9e920178e06e426fba287bd92`  
**Execution status:** **NOT YET EXECUTED on the corrected head**

## Why this review was required

The earlier R7 source/Simulator corrections had reached a physically useful state, but `main` advanced with Parent usage-limit and Activity-visibility work before the remaining R7.2/R7.3 Acer durability lanes were complete.

That work now sits directly on the Activity lifecycle seam:

```text
ProfileVisualActivitySupervisor
  -> TrustedChromeActivitySupervisor
  -> UsageLimitedActivitySupervisor
  -> ActivitySupervisor
```

Therefore the next R7 freeze must validate trusted Home, usage-limit stop, display restoration and Activity return together rather than assuming the previous exact-SHA evidence transfers automatically.

## Architecture finding

The new usage-limit design is correctly layered in the important respect: authoritative time accounting and stop enforcement stay in the supervisor/lifecycle path, while `SystemChromeCoordinator` and trusted Home continue to use the same lifecycle authority. The Parent browser is not the accounting or process authority.

The review found two narrower gaps.

### 1. Exhausted child launch UX

Before this review, an already-exhausted child could still activate an Activity tile. The authoritative supervisor would refuse/end the launch, but the Shell could briefly present `Starting…` and then generic failure presentation.

That contradicted the feature design's intended child UX: exhausted children should remain on Greia Home with the calm `Finished for today` state and should not experience a fake launch attempt.

Correction:

- `bb3b93079765d5180fc59d364838198a08bca138`
- `src/greia_launcher/child_shell.py`

`GreiaChildShell._launch_selected()` now performs a presentation-only status read before launch. If the already-authoritative ledger says the active profile is exhausted it:

- does not call the ordinary launch presentation path;
- clears generic launch/catalogue error presentation;
- returns the category to `ALL_ACTIVITIES_ID` Collection Home;
- invalidates the cached Home scene so the finished state is redrawn.

This is deliberately **not** enforcement authority. If the presentation read fails, the Shell delegates to the normal launch path and the authoritative usage-limit supervisor remains responsible for fail-closed enforcement and race handling.

Regression source:

- `34939d32232499fe8fdaeae2e7f9ead0ebe8ebd0`
- `tests/test_child_shell_usage_limit_launch.py`

The test covers exhausted/no-launch, available/delegate, and presentation-read-error/delegate behavior.

### 2. Usage ledger lock failure was fail-open

`UsageLimitStore` describes its persistence as inter-process-safe because Parent policy mutation and launcher accounting may occur in separate processes. The existing POSIX lock path caught `OSError` from `fcntl.flock(..., LOCK_EX)` and continued as though serialization had succeeded.

That was not consistent with the stated data-integrity contract: a real lock-acquisition failure could allow two read/modify/write operations to race and silently erase policy/accounting changes.

Correction:

- `4e4db7d9e2607bae186dfba37f81bb64def93631` first attempted the correction but, because the GitHub contents API requires whole-file writes, that commit accidentally reconstructed unrelated later helpers from a partial view.
- **Do not treat `4e4db7d9...` alone as the accepted source state.**
- `496786ef64c8ecc9e920178e06e426fba287bd92` restores the exact parent accounting implementation and retains only the narrow lock correction.

The final intended behavior is:

- `ImportError` for `fcntl`: retain the existing single-process non-POSIX developer fallback;
- POSIX `flock(LOCK_EX)` `OSError`: raise `UsageLimitError`, do not enter the transaction body;
- successful POSIX lock: hold it for the entire transaction; closing the lock file releases it even if the body raises.

Regression source:

- `04307c565cc908002aad9ca704ed69d01a50c39b`
- `tests/test_usage_limits.py`

The added test requires a simulated POSIX `flock` failure to surface as `UsageLimitError` rather than proceeding.

## Accidental-churn verification

After the correction, compare:

```text
base: 34939d32232499fe8fdaeae2e7f9ead0ebe8ebd0
head: 496786ef64c8ecc9e920178e06e426fba287bd92
```

shows only:

```text
src/greia_platform/usage_limits.py  +14 -12
tests/test_usage_limits.py          +11 -0
```

for the lock tranche. The unrelated accounting/helper changes visible in intermediate commit `4e4db7d9...` are not present in the corrected source.

## R7 evidence boundary

Do **not** inherit an exact-current R7 PASS from earlier source candidates. Current `main` has moved through physical Writing/focus corrections and the Parent usage-limit lifecycle integration.

The next freeze must re-run:

1. current focused R7 + usage-limit source suites;
2. both Activity authority audits;
3. `make verify`;
4. real-Shell Simulator matrix for Encyclopedia, Writing, Painting, animated Activity and hostile fixture;
5. same exact source on Acer for Shell-focus restart stability, Writing, Painting, hostile 10/10, abrupt crash, 20 normal return cycles, logs and performance.

Writing physical failure remains independent from Encyclopedia. If Writing becomes black or loses input again, report it as its own physical R7 failure.

## Release / phase disposition

- R7 remains the first incomplete blocking platform phase.
- R7.2/R7.3 are **not** called physically accepted by this review.
- R7.4 controller/system-input ownership must not start until the exact-current R7.2/R7.3 source/Simulator/Acer verdict is green.
- Parent usage-limit functionality likewise must not be called hardware-accepted until the current exact-SHA gate exercises its lifecycle composition.
