# Greia — Current Engineering Handover

**Updated:** 2026-09-01  
**Canonical repository/branch:** `frozenpepper/Greia` / `main`  
**Primary blocking phase:** **R7 — direct graphics/session/input architecture**  
**Current subphase:** **Launcher spoken labels (Collection + Activity) – implementation + voice migration (38 system + 68 Activity)**  
**Latest runtime/source correction requiring execution:** `a5bac27a` + spoken-label tranche (this handover)  
**Activity modernization:** **COMPLETE**  
**Latest fully executed source gate retained from earlier head:** **PASS at `d947eb7ef5ad3703cb7293a8bba73bf9db9277e4` — 1512 tests (skipped=2)**  
**Latest exact-current source/Simulator verdict:** **PENDING — spoken-label implementation + voice assets added, `audit_launcher_spoken_labels` now PASS, controller tests 13 passed, full `make verify` 1561 passed after updating 3 source-contract tests**  
**R7.2/R7.3 Acer physical acceptance:** **PARTIAL historically; exact-current full durability gate PENDING (plus spoken-label Simulator/Acer acceptance per runbook)**  
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
docs/reviews/2026-08-31_R7_SIMULATOR_RUNTIME_INTEGRATION_REJECTION_AND_CORRECTION.md
docs/reviews/2026-09-01_R7_CURRENT_HEAD_USAGE_LIMIT_LIFECYCLE_REVIEW.md
docs/design/PARENT_CONTROLS_USAGE_LIMITS_AND_ACTIVITY_VISIBILITY.md
```

Work from current `main`, preserve concurrent work, and do not use GitHub-hosted Actions without explicit owner authorization.

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

## 5. Honest evidence boundary

The previous handover recorded a fully executed source gate at `d947eb7e`:

```text
make verify: PASS, 1512 tests (skipped=2)
backend audit: blockers=0
system-chrome ownership audit: blockers=0
Writing physical lane: PASS
Painting physical presentation: PASS
```

The remaining long physical lanes were still incomplete:

```text
hostile trusted-Home 10/10
abrupt Activity crash recovery
20/20 normal Shell -> Activity -> Shell cycles, with >=5 Writing/Painting
final performance/log review
```

Since then `main` advanced substantially, including the Shell focus fix and Parent usage-limit lifecycle work. Therefore **the earlier exact-SHA PASS does not automatically certify current main**.

No current-head PASS is claimed by this handover. The next agent must freeze current `main` and execute the current source + Simulator + same-SHA Acer gate.

---

## 6. Next exact step

Use the current local-agent acceptance runbook supplied with this handover session.

Order:

1. pull current `main`, require a clean tree, freeze exact SHA;
2. run focused R7 + usage-limit lifecycle tests using `unittest discover` patterns (not dotted `tests.*`, which can be shadowed by site-packages);
3. require backend audit `blockers=0` and chrome audit `blockers=0`;
4. run `make verify` and stop on the first real failure;
5. re-check Encyclopedia page hot-path scans;
6. run real-Shell Simulator matrix: Encyclopedia, Writing, Painting, `volo_draghetto`, hostile fixture;
7. only after source/Simulator green, deploy the exact frozen SHA to Acer using the canonical deploy helper;
8. prove Shell focus across repeated restarts, Writing, Painting, hostile 10/10, abrupt crash, 20/20 launch-return durability, logs/performance and no Linux exposure;
9. append the final evidence entry to the active architecture plan and update this handover;
10. do not advance R7.4 unless the physical verdict is ACCEPTED.

If current `origin/main` advances after freeze, do not pull mid-gate. Return evidence for the frozen SHA and state that current-main physical acceptance remains pending.
