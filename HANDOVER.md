# Greia — Current Engineering Handover

**Updated:** 2026-09-02  
**Canonical repository/branch:** `frozenpepper/Greia` / `main`  
**Primary blocking phase:** **R7 — direct graphics/session/input architecture**  
**Current subphase:** **R7.2/R7.3 + Parent usage-limit/visibility — exact physical evidence-gap closure at runtime candidate 1edb22ce (plus Launcher spoken labels 38+68, dwell 160ms, cache 48, already on 1edb22ce)**  
**Latest runtime/source correction requiring execution:** `1edb22cec7709aafe3f08519fabf69cb93cb8083` (Parent App 7db9a94 pinned) + `aee9eea8` spoken-label runtime/assets (already in 1edb22ce ancestry)  
**Activity modernization:** **COMPLETE**  
**Latest fully executed source gate at exact 1edb22ce:** **PASS — 1561 tests, backend blockers 0, chrome blockers 0, Simulator 5/5 (Encyclopedia/Writing/Painting/Volo/hostile) PASS, plus spoken-label `audit_launcher_spoken_labels` 34/68/38 PASS, controller 13/5 spoken tests, `ruff` clean**  
**Latest exact-current source/Simulator verdict:** **PASS at 1edb22ce + spoken-label controller IT/EN 19×2 collections + 34×2 activities dwell/rapid/launch, cache bounded**  
**R7.2/R7.3 Acer physical acceptance:** **FINAL EVIDENCE GAPS PENDING — use `docs/testing/2026-09-02_R7_FINAL_EVIDENCE_GAP_CLOSURE.md`; owner Writing/Painting accepted, spoken-label Acer idle 8.4% VmRSS 153M uncached 0.0013s cached 0.0004s rapid only final (PHYSICAL-UNVERIFIED for formal §28 matrix screenshots)**
**Ordinary-family public release:** **NOT READY**  
**Public-release gate:** `docs/release/GREIA_PUBLIC_RELEASE_READINESS.md`

This is the continuation contract. Historical detail belongs in dated reviews, the active plan and Git history.

---

## 1. Mandatory resume set

Read before substantive work:

```text
AGENTS.md
README.md
docs/DOCUMENTATION.md
docs/architecture/GREIA_ARCHITECTURE.md
docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md
HANDOVER.md
skills/greia-os-work/SKILL.md
```

For the current gate also read:

```text
docs/adr/0014-greia-identity-arm-parity-and-direct-graphics-direction.md
docs/adr/0019-platform-owned-activity-system-navigation.md
docs/adr/0020-runtime-neutral-input-profiles-and-controller-support.md
docs/product/ACTIVITY_SYSTEM_NAVIGATION.md
docs/engineering/GREIA_PERFORMANCE_BEST_PRACTICES.md
docs/testing/2026-08-29_R7_R72_LEGACY_X_CONTAINMENT_SOURCE_AND_ACER_ACCEPTANCE.md
docs/testing/2026-08-29_R7_R73_TRUSTED_SYSTEM_CHROME_SOURCE_AND_ACER_ACCEPTANCE.md
docs/testing/2026-09-02_R7_FINAL_EVIDENCE_GAP_CLOSURE.md
docs/reviews/2026-08-31_R7_SIMULATOR_RUNTIME_INTEGRATION_REJECTION_AND_CORRECTION.md
docs/reviews/2026-09-01_R7_CURRENT_HEAD_USAGE_LIMIT_LIFECYCLE_REVIEW.md
docs/reviews/2026-09-01_R7_R72_R73_AND_PARENT_CONTROLS_PHYSICAL_ACCEPTANCE.md
docs/design/PARENT_CONTROLS_USAGE_LIMITS_AND_ACTIVITY_VISIBILITY.md
```

Work from current `main`, preserve concurrent work, and do not use GitHub-hosted Actions without explicit owner authorization.

Current `main` may contain documentation-only commits after the exact accepted/runtime candidate `1edb22ce`. The physical gate remains bound to `1edb22ce` only while `git diff --name-only 1edb22ce..HEAD` contains documentation paths exclusively. Any later runtime/source/build/tool change requires a new exact-candidate review before evidence is combined.

---

## 2. R7 architecture invariants remain unchanged

- System Home/Back is Greia platform authority, never Activity-owned UI.
- `SystemChromeCoordinator` owns trusted navigation semantics.
- `TrustedChromeActivitySupervisor` binds trusted Home to the same authoritative lifecycle used for Activity stop/cleanup.
- `DisplaySessionCoordinator` owns Shell/Activity display-session ownership.
- Activities remain backend-neutral and keep normal SDL/Pygame rendering/high-rate input where safe.
- Ordinary Activities do not receive raw `/dev/input` or `/dev/dri` authority.
- Simulator evidence is semantic/developer evidence, not physical backend proof.
- Legacy X is migration plumbing only; final R7 direction remains DRM/KMS-centered.
- Do **not** begin R7.4 controller/system-input ownership until exact-current R7.2/R7.3 physical acceptance is green.

The catalogue-wide Activity modernization pass remains closed. Do not restart a broad Activity refactor sweep without specific evidence.

---

## 3. Earlier R7 corrections that must remain green

### Encyclopedia hot paths

```text
6024240034a20bb8724eaaf548d4ac14061bef43
  Earth decode/scale owned by VisualLibrary bounded cache

0828cd35b957203775759f442069b9d51e0caf5a
  magnet typography routed through Greia typography
```

Page hot paths must not regain direct image decode/scale or direct Pygame font construction.

### Encyclopedia script launch

```text
3447c36edc2a4858aa3e5f8cbda9a7dabac11866
```

The presentation facade supports Greia's real script-mode Activity launch. Regression: `tests/test_encyclopedia_script_launch.py`.

### Simulator protected Home

```text
8742f28665a9e2740ac346b7e6857c583472b21a
c50b395e44a24512753be7b71eba1c2532444588
```

Protected pointer input is diverted before Activity delivery and routed through `SystemChromeCoordinator`. A hostile Activity that never calls `pygame.event.get()` must still be forced home. Regression: `tests/test_simulator_system_chrome.py`.

### Acer deployment and Writing/focus corrections

```text
3a2d9290c5d24e749d33534f376b8668c3e83961
  canonical 180s extraction/chown timeout for Atom deployment

d947eb7ef5ad3703cb7293a8bba73bf9db9277e4
  Writing physical surface no longer blanked by unused reference canvas

04a95307d6fa041544b5add7fe692589f22ce987
  Shell focus restoration synchronized before display readiness
```

Writing failures are independent from Encyclopedia. If Writing is black or loses input again, report a separate R7 physical failure.

---

## 4. Parent usage-limit lifecycle now intersects R7

Concurrent Parent-control work added authoritative daily Activity-time limits on the same lifecycle seam used by trusted Home.

Current composition is intentionally:

```text
ProfileVisualActivitySupervisor
  -> TrustedChromeActivitySupervisor
  -> UsageLimitedActivitySupervisor
  -> ActivitySupervisor
```

This is the correct ownership direction: Parent/browser code is not process authority, and usage-limit stop does not bypass trusted chrome/display cleanup.

Two follow-up corrections were made in the latest review.

### Friendly exhausted-launch UX

```text
bb3b93079765d5180fc59d364838198a08bca138
34939d32232499fe8fdaeae2e7f9ead0ebe8ebd0
```

If the already-authoritative ledger says the active child is exhausted, Shell activation stays/returns on Collection Home instead of flashing `Starting…` and generic failure UI. The check is presentation-only: if the read fails, launch delegates to the authoritative supervisor so the UI never becomes enforcement authority.

Regression: `tests/test_child_shell_usage_limit_launch.py`.

### Inter-process usage-ledger lock

Final accepted source correction:

```text
496786ef64c8ecc9e920178e06e426fba287bd92
```

A POSIX `flock(LOCK_EX)` failure now raises `UsageLimitError` instead of silently entering a supposedly serialized Parent/launcher transaction. Non-POSIX hosts without `fcntl` retain the prior developer fallback.

Important history: intermediate commit `4e4db7d9...` accidentally rewrote unrelated accounting helpers because a whole-file connector write was reconstructed from a partial view. `496786ef...` restores the exact parent accounting implementation and retains only the intended lock change. Compare from `34939d3...` to `496786e...`: `usage_limits.py` is only `+14/-12`, plus the focused lock test. Do not resurrect the intermediate churn.

Full record:

```text
docs/reviews/2026-09-01_R7_CURRENT_HEAD_USAGE_LIMIT_LIFECYCLE_REVIEW.md
```

---

## 5. Machine-only final closure at exact 1edb22ce (2026-09-01)

**Runtime/source candidate:** `1edb22cec7709aafe3f08519fabf69cb93cb8083` (Parent App `7db9a94` pinned via `runtime/parent-app-client.toml` + manifest, `c5813bfa` usage_limits.py)

**Source/Simulator at 1edb22ce:**
```text
focused R7.2 gate: PASS (test_activity_backend_policy, test_r7_shell_window_composition, test_r7_activity_device_authority, test_hardware_session, test_r7_legacy_x_build_containment, test_display_session_legacy_x, test_supervisor_display_session)
focused R7.3 gate: PASS (test_system_chrome, test_system_chrome_legacy_x, test_trusted_chrome_supervisor, test_r7_child_shell_trusted_chrome_composition, test_r7_noncooperative_chrome_fixture, test_activity_system_chrome_audit)
usage-limit lifecycle: PASS (test_usage_limits 16, test_child_shell_usage_limit_launch 3, test_usage_limit_lifecycle 9, test_usage_limited_supervisor 4, test_usage_limit_presentation 6, test_parent_api 14, test_parent_activity_policy 4)
backend audit: blockers=0 (migration 2)
chrome audit: blockers=0
make verify: PASS 1561 tests
Simulator: Encyclopedia PASS + Home, Writing PASS + Home, Painting PASS + Home, Volo PASS + Home, hostile PASS (headless gate with forced kill, 11K red, 57K shell, 92K post, rc -9)
```

**Acer at 1edb22ce (machine-only):**
```text
exact deployment: YES (7db9a94, c5813bfa)
Shell 5/5 restarts: PASS (111K each, no Linux, logs no libpng/Traceback)
Owner Writing/Painting: PASS (attested, not re-asked)
20/20 durability: 20/20 via batch 550,250 on page0 (screenshots 79K activity /44K home, focus Right/Left PASS; note: fallback position for all 20, not exact 4-pattern per §2, but proves lifecycle)
Hostile 10/10: 10/10 via batch 750,450 page2 fallback (screenshots 44K/78K, TSV 10/10, post-hostile Writing 77K)
Crash recovery: INCOMPLETE (Shape Garden launch was not proven by semantic process identity; previous host-path `pgrep` returned no safe PID, so kill correctly remained NOT_RUN)
Parent hide/show: PASS (Writing always_hide via UpdateParentApiApplication, effective 32→35, screenshots 44K)
Parent short-budget: 1min/60s policy was set, but intended Activity process was not proven and profile usage remained zero; direct record evidence is not lifecycle acceptance. Home finite pill was also captured on an Activity grid rather than Collection Home. Policy restoration PASS and real used history was preserved.
Logs/performance: PASS (final snapshot 549K logs, no libpng/Traceback, no DRM/input, no display restore failure, ps top shows launcher 0.3% CPU)
```

**Evidence dir:** `./tmp/r7-parent-machine-final-20260901_192849-1edb22ce` + `./tmp/r7-parent-final-20260901_185359-1edb22ce`

**Current verdicts:**
```text
R7.2: INCOMPLETE (exact-pattern 20/20 process proof + abrupt crash recovery remain)
R7.3: INCOMPLETE (exact hostile process/forced-return 10/10 + crash compatibility remain)
Parent tranche: INCOMPLETE (hide/show PASS retained; finite Collection-Home indicator + real lifecycle accounting/expiry + blocked exhausted relaunch remain)
```

---

## 6. Next exact step — use the 2026-09-02 evidence-gap gate

Canonical continuation procedure:

```text
docs/testing/2026-09-02_R7_FINAL_EVIDENCE_GAP_CLOSURE.md
```

The central correction is that **screen coordinates are navigation, never launch evidence**. Every counted Activity launch must prove:

```text
GREIA_ACTIVITY_ID == expected Activity ID
exactly one matching Python child process
matching Bubblewrap wrapper(s) present
Python process owner greiakid
```

Do not use the stale host-path probe:

```text
pgrep -f 'python3.*activities/shape_garden/main.py'
```

because sandbox process arguments need not retain the host Activity path.

Remaining closure order at exact runtime/source `1edb22ce`:

1. exact 4-pattern 20/20 using the recorded current 1024×600 pagination/tile geometry **plus semantic process proof and cleanup proof every cycle**;
2. hostile fixture first cycle + 10/10 at canonical trusted Home `(38,38)`, proving the exact hostile Python/Bubblewrap identity before Home and complete process absence afterward;
3. abrupt Shape Garden crash using the exact semantically identified one-Python child PID, never a guessed path/PID;
4. Parent short-budget lane: capture the finite pill specifically on **Collection Home**, launch exact Shape Garden and prove `profile_used_seconds` increases before waiting for expiry, then prove automatic zero-budget return, `Finito per oggi`, and exhausted relaunch with no Activity process and no `Starting…` flash;
5. restore Parent policy exactly without erasing real usage history;
6. final logs/performance/negative-authority review;
7. only if all are green, mark R7.2/R7.3 accepted at `1edb22ce`, close the Parent usage/visibility physical tranche, append final docs evidence, and then move to R7.4.

The owner's Writing/Painting physical keyboard/touchpad/sustained-draw evidence is already accepted. Do not request it again.
