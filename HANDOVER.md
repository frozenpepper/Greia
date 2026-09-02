# Greia — Current Engineering Handover

**Updated:** 2026-09-02  
**Canonical repository/branch:** `frozenpepper/Greia` / `main`  
**Primary blocking phase:** **R7 — direct graphics/session/input architecture**  
**Current subphase:** **EMERGENCY HOME SYSTEM-CHROME REGRESSION — SOURCE-FIXED, PHYSICAL PENDING (2026-09-02 runbook, supersedes other acceptance until Home restored)**  
**Latest runtime/source correction requiring execution:** **CURRENT = Home regression fix (this handover) + spoken-label cleanup + 1edb22ce ancestry; FROZEN R7 CANDIDATE 1edb22ce NO LONGER AUTHORITATIVE after runtime change**  
**Activity modernization:** **COMPLETE**  
**Latest fully executed source gate at exact current main + Home fix:** **PASS — 1564 tests (1561+3), backend blockers 0, chrome blockers 0, focused chrome 29 PASS, `audit_launcher_spoken_labels` PASS, `ruff` clean, 106 human ACCEPTED**  
**Latest exact-current source/Simulator verdict:** **PASS at current main + Home fix (1564), headless spoken IT/EN PASS, origin 1edb22ce Simulator 5/5 retained; NEW Home-reg simulator ordinary+hostile PENDING at this SHA**  
**R7.2/R7.3 Acer physical acceptance:** **BLOCKED BY HOME REGRESSION — Home absent on every Activity (owner report). SOURCE FIX LANDED (presentation.py rebuild), PENDING deploy + physical proof at (38,38) 1024×600. See §8. Prior 1edb22ce evidence remains valid but candidate is stale per runbook §9 (runtime changed).**
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

---

## 7. Launcher spoken-label tranche — current main (2026-09-02) — SOURCE-COMPLETE, HUMAN/FORMAL-PHYSICAL PENDING

**Implementation ancestry:** `aee9eea8` (Launcher spoken labels: Collection + Activity titles, Leo, it/en, 68+38 clips, dwell 160ms, bounded cache 48) + `f82aea2b` (Leo fallback clarification) + `10203efc` docs-only machine final + `47e955d5` merge with R7 gap gate. Current main `47e955d5` already contains `aee9eea8`/`f82aea2b` runtime/assets; this tranche adds **focused cleanup §3-6** as a new runtime correction (not docs-only).

**Focused cleanup §3-6 — committed on this main (not yet deployed to Acer):**
```text
src/greia_launcher/spoken_labels.py: added activity_focus(manifest,locale)->(identity,clip) + collection_focus(cid,locale)->(identity,clip) behind SpokenLabelController
src/greia_launcher/presentation.py: removed dynamic from .spoken_labels import ... inside _speakable_for_target, removed self._spoken_labels._root reach-through, removed clip = self._spoken_labels.player noqa, narrowed except Exception to (ValueError,TypeError,AttributeError,KeyError); _target_at now for target in reversed(self._targets) with pos None guard
tests/test_launcher_spoken_labels_controller.py: tautological assert ... is False or True -> is True via fresh SpokenLabelController(tmp_path) to avoid dedup, plus new test_controller_locale_fallback_missing_audio (it-only, fr -> False) and test_target_at_uses_current_frame_reversed_topmost (overlap topmost = reversed(_targets))
tools/audit_launcher_spoken_labels.py: caption_key strict (bad caption_key -> missing_mapping), vocabulary fail-closed (raise RuntimeError not 19 hard-coded fallback, audit_collections returns VOCABULARY_ERROR), WAV sanity via wave.open (mono, 22050 Hz, 16-bit sampwidth 2, >0.1s) for both activity and system labels
```
**Integrity per §2 — human review:** `human_review: ACCEPTED` for all 106 receipts after owner listening session 2026-09-02 (including regenerated `posta_di_leo/it` clean transcript "La poste di Leo." and workshop_settings/en "My Greia" accepted).
```text
ACTIVITY_GENERATED=68, HUMAN_ACCEPTED=68, PENDING=0
SYSTEM_GENERATED=38, HUMAN_ACCEPTED=38, PENDING=0
WORKSHOP_SETTINGS_EN: ACCEPTED — owner confirms audio says "My Greia" (transcript "My grayer. My grayer." was Whisper approximation; human confirms intelligible)
POSTA_DI_LEO_IT: REGENERATED from 85K 1.98s "Ah, posta di Leo!" to 59K 1.38s "La poste di Leo." via leo character_dialogue it (60716 bytes, sha256 e717fe..., receipt PASS) and now ACCEPTED
SYSTEM verification disposition NOT_APPLICABLE where expected — all receipts now stamped human_review:ACCEPTED + owner_decision_at_utc
```
**Source/audit gates at current main (after §3-6):**
```text
DYNAMIC_IMPORTS_REMOVED=yes (no from .spoken_labels import inside _speakable_for_target)
PRIVATE_ROOT_REACH_THROUGH_REMOVED=yes (no self._spoken_labels._root)
HIT_TARGET_AUTHORITY=reversed(_targets) (cached rendering republishes into _targets; no second authority)
TAUTOLOGICAL_TEST_FIXED=yes (is True + missing_audio test)
AUDIT_CAPTION_KEY_STRICT=yes
AUDIT_VOCABULARY_FAIL_CLOSED=yes
AUDIT_WAV_SANITY=yes (wave.open checks)
FOCUSED_TESTS=20 passed (5 test_launcher_spoken_labels + 13 controller -> 20 after fix)
LAUNCHER_REGRESSIONS: presentation still owns dwell/poll/stop, collection 5 + controller 13 etc.
RUFF=All checks passed (spoken_labels.py presentation.py collection_home_presentation.py adaptive_discovery_presentation.py tests/... tools/audit...)
SPOKEN_LABEL_AUDIT=PASS 68+38 (BUILT_IN_ACTIVITIES=34, ACTIVITY_TITLE_LOCALE_COMBINATIONS=68, COLLECTION_LABELS_REQUIRED=38)
MAKE_VERIFY=1561 PASS (105s) at 47e955d5 + 4-file cleanup (clean-bytecode, unittest discover)
```
**Simulator — headless controller logic (current main):**
```text
SIMULATOR_IT_HEADLESS=PASS — Collection Home keyboard >=4 changes + boundary clamp -> no replay, pointer <160ms no speech / >dwell once / within-tile no replay / leave-reenter -> replay / rapid A->B->C only C speaks, adaptive 3 sub-Collections, Activity grid keyboard >=5 + boundary + PAGEUP/DOWN (via controller dedup), pointer >=5, launch during speech stops channel, stale-target Activity->Home->Collection = home_collection (reversed topmost)
SIMULATOR_EN_HEADLESS=PASS — same matrix with en locale, en fallback, rapid, boundary PASS
SIMULATOR_GUI_FULL=PENDING — real tools/greia_simulator.py Collection Home + adaptive + Activity grid matrix with real 1024×600 rendering not executed in this headless session; origin 1edb22ce Simulator 5/5 (Encyclopedia/Writing/Painting/Volo/hostile) remains PASS and is not re-asked
```
**Acer — current main vs frozen 1edb22ce:**
```text
FROZEN_R7_CANDIDATE=1edb22ce (exact runtime/source for R7.2/R7.3/Parent gaps; see §5 and docs/testing/2026-09-02_R7_FINAL_EVIDENCE_GAP_CLOSURE.md)
CURRENT_MAIN=47e955d5 + spoken-label cleanup (not docs-only; delta from 1edb22ce contains runtime/assets + src/tools/tests — therefore R7 physical remains bound to 1edb22ce per §1 rule)
ACER_REACHABLE=yes (greia-dev.local:22, Greia 0.12.0-phase0-dev, greia-launcher active)
ACER_FILE_COUNTS_AT_1edb22ce_DEPLOYMENT (via _ssh_user_command bash -c ls/find):
  SYSTEM_IT=19 /19 wav (ls /opt/greia-os/assets/audio/system/launcher-labels/it)
  SYSTEM_EN=19 /19 wav
  ACTIVITY_IT=34 /34 locales/it/audio/activity-title.wav
  ACTIVITY_EN=34 /34 locales/en/audio/activity-title.wav
ACER_IDLE_CPU=PENDING formal measurement (pidstat not available on image; ps shows no launcher CPU regression, but canonical pidstat 1 30 not executed)
ACER_RSS_BEFORE/AFTER_BOUNDED=PENDING (bounded cache 48 proven via unit test; physical RSS before/after 48+ second traversal not measured; previous 1edb22ce informal ps showed VmRSS 153M uncached 0.0013s cached 0.0004s rapid only-final but marked PHYSICAL-UNVERIFIED)
ACER_RAPID_POINTER/KEYBOARD=PENDING formal matrix (controller rapid/launch covered headless; physical rapid 10 pointer/keyboard + perceived onset not executed)
ACER_LAUNCH_DURING_SPEECH=PENDING formal (unit stop() proven; physical immediate launch + no leak not executed)
DEPLOY_STATUS=NOT_DEPLOYED current 4-file cleanup; Acer still at 1edb22ce + spoken-label assets (aee9eea8) deployment. A 180s deploy_to_acer.py is required to promote current cleanup to a new exact candidate before combining formal Acer spoken-label latency/RSS/rapid evidence.
```
**Blockers and verdict:**
```text
R7.2/R7.3/Parent physical: INCOMPLETE at frozen 1edb22ce per §5-6 (exact 20/20, hostile 10/10, crash, Parent finite pill + accounting remain per 2026-09-02 gate). Current main's R7 evidence is unchanged and remains at 1edb22ce.
Launcher spoken-label tranche:
  SOURCE=SOURCE-COMPLETE (audit 68+38 PASS, 1561 PASS, ruff PASS, 20 spoken tests, controller logic IT/EN headless PASS, _target_at reversed, private reach-through removed)
  HUMAN_REVIEW=COMPLETE (106/106 ACCEPTED — 68 activity + 38 system, including regenerated posta_di_leo/it now 59K "La poste di Leo." and workshop_settings/en "My Greia" accepted)
  SIMULATOR_GUI_FULL=PENDING (headless controller PASS, full desktop simulator matrix screenshots not captured this session)
  ACER_FORMAL=PENDING (file counts 19/19/34/34 PASS; idle/RSS/latency/rapid/launch formal matrix requires deployed current main + 180s extraction + pidstat/ps + dispatch timing; current main 57cd5f1a contains human-accepted audio, see unified promotion gate)
  FINAL_SPOKEN_LABEL_TRANCHE_VERDICT=SOURCE-AND-HUMAN-COMPLETE / SOURCE-COMPLETE for formal GUI/physical; NOT COMPLETE per runbook requiring Simulator GUI + formal Acer §28 (human now green)
```
**Next exact step for spoken labels:** 1) full `tools/greia_simulator.py` GUI matrix IT then EN (4+ Collections, boundary, TAB, pointer dwell/rapid, adaptive 3, grid 5+ PAGEUP/DOWN, launch during speech, stale-target) with screenshots, 2) freeze `FINAL_RUNTIME_SHA` per `docs/testing/2026-09-02_R7_PARENT_SPOKEN_LABEL_UNIFIED_PROMOTION_GATE.md` §4 (current main 57cd5f1a contains accepted audio; if no further runtime change, FINAL=57cd5f1a), 3) `tools/deploy_to_acer.py` exact candidate (180s) then `find ...|wc -l 19/19/34/34`, `pidstat`/`ps` idle >=10s, RSS before/after >48 clips + second traversal, dispatch UNCACHED/CACHED + PERCEIVED_ONSET, rapid >=10 pointer/keyboard, small-speaker intelligibility, 4) update plan/HANDOVER with simulator + Acer evidence + FINAL_RUNTIME_SHA, 5) commit docs-only after new exact candidate.

Do not describe 1edb22ce as current main. Current main is 47e955d5 plus this additive 4-file cleanup (pre-commit). Do not rewrite earlier R7 progress entries.

---

## 8. Emergency Home system-chrome regression — SOURCE-FIXED, PHYSICAL PENDING (2026-09-02)

**Runbook:** `/GREIA_HOME_SYSTEM_CHROME_REGRESSION_FIX_2026-09-02.md` (BLOCKING, supersedes spoken-label/other acceptance until Home restored)

**Observed physical defect:** Acer runs every Activity with **no Greia Home in top-left**; owner also reports loss of other platform-owned wrapper behaviors (usage-limit/profile/achievement).

**Root cause (source-confirmed):** `GreiaLauncherPresentation._configure_parent_package_source()` did:

```python
try:
    discovered = registry.discover()
except ActivityValidationError:
    self._catalogue_error = True
    return   # ← left plain ActivitySupervisor from LauncherApplication.__init__
```

If one Parent-installed package is invalid/corrupt, this returned **before `_rebuild_runtime_services()`**. The shell retained the plain `ActivitySupervisor`, losing together:

```text
trusted Greia Home/Back lifecycle
daily usage-limit wrapper (UsageLimitedActivitySupervisor)
ProfileVisual launch-context/audio + achievement integration (ProfileVisualActivitySupervisor)
```

An empty/missing Parent root does **not** trigger this (skipped by registry); only a validation failure does. Latent bug exposed by R7.3 migration that removed old Activity-drawn Home.

**Central correction (this handover):**

```python
except ActivityValidationError:
    self._catalogue_error = True
    self._rebuild_runtime_services()  # dynamic dispatch restores full composition
    return
```

- `src/greia_launcher/presentation.py:246` — 6-line rebuild with comment explaining optional Parent input vs mandatory rebuild
- Does NOT assign `self.registry = registry` in error branch (keeps known-good built-in/developer registry)
- Does NOT swallow `_rebuild_runtime_services()` failure (fail-closed)
- Fixes both `GreiaChildShell` and `TrustedGreiaLauncherPresentation` via dynamic dispatch

**Tests added:**

```text
tests/test_parent_source_supervisor_fallback.py — 3 tests (launcher, child_shell, trusted_fallback)
  asserts _catalogue_error True + registry/_activities unchanged + _rebuild called once
  (unittest, not pytest, so counted by make verify)

tests/test_r7_child_shell_trusted_chrome_composition.py — dual assert:
  ProfileVisualActivitySupervisor -> TrustedChromeActivitySupervisor
  TrustedChromeActivitySupervisor -> UsageLimitedActivitySupervisor
```

**Source gates at this SHA (clean, PYTHONPATH=src):**

```text
FOCUSED: PYTHONPATH=src python3 -m pytest -q tests/test_parent_source_supervisor_fallback.py tests/test_r7_child_shell_trusted_chrome_composition.py tests/test_system_chrome.py tests/test_system_chrome_legacy_x.py tests/test_trusted_chrome_supervisor.py → 29 passed
FULL: PYTHONPATH=src python3 -m unittest discover -s tests → 1564 tests PASS (was 1561, +3 new; 84s, resource warnings only)
AUDITS: audit_activity_system_chrome_ownership --strict → blockers=0
        audit_activity_backend_independence → blockers=0 migration 2 (labirinto_magico + workshop_settings)
RUFF: ruff check src/greia_launcher/presentation.py tests/test_parent_source_supervisor_fallback.py tests/test_r7_child_shell_trusted_chrome_composition.py → All checks passed
git diff --check → 0
validate_project → PASS runtime_api=0.1 activities=34
footprint-source → 725M tree, runtime 3.1M src / 46M activities
```

**Pre-fix Parent-source condition:**

```text
PRE_FIX_STRICT_PARENT_DISCOVERY=PENDING — not captured on Acer in this session (local dev only)
PRE_FIX_UNVALIDATED_COUNT=PENDING
PRE_FIX_UNVALIDATED_PACKAGES=PENDING
Launcher logs 500 lines: PENDING
→ Must run on Acer via sudo -u greiakid diagnostic (runbook §2) before concluding §11.
Do not delete/repair invalid package merely to make Home return — platform must be correct even with damaged optional storage.
```

**Current Home regression status:**

```text
CURRENT_HOME_REGRESSION=SOURCE_FIX_PENDING_PHYSICAL
STARTING_MAIN_SHA=a5c38d421dd39a2aa2c4d2de6da920601206aba9
FIX_SHA=PENDING (this commit)
ENDING_MAIN_SHA=PENDING (after push)
HEAD_EQUALS_ORIGIN_MAIN=PENDING (must be verified after push)

ROOT_CAUSE_CONFIRMED=yes (source path proven, matches owner loss of Home + other wrappers)
PARENT_FAILURE_REBUILD_TEST=PASS (3/3)
PRIMARY_TRUSTED_COMPOSITION=PASS (ProfileVisual -> TrustedChrome -> UsageLimited)
FALLBACK_TRUSTED_COMPOSITION=PASS (TrustedGreiaLauncherPresentation -> same trusted chain)
FOCUSED_CHROME_TESTS=PASS (29)
CHROME_OWNERSHIP_AUDIT=PASS (0 blockers)
BACKEND_AUDIT=PASS (0 blockers, 2 migration)
RUFF=PASS
MAKE_VERIFY=PASS (1564)
SIMULATOR ordinary=PENDING at this SHA (must run Writing/Painting/Shape Garden + one extra + hostile fixture; Home must return through platform host even when Activity hostile)
SIMULATOR hostile=PENDING
```

**Next exact step (runbook §§2,8,10,11):**

1. Record `STARTING_MAIN_SHA` (`a5c38d`) and `ORIGIN_SHA`; working tree clean — already proven
2. Commit this fix + tests + plan/HANDOVER, push to `origin/main`, verify `HEAD==origin/main`
3. **On Acer** (greia-dev.local via tools/greia_remote.py), run §2 read-only diagnostic:
   `sudo -u greiakid GREIA_OS_ROOT=/opt/greia-os GREIA_PROFILES_DIR=/var/lib/greia-profiles PYTHONPATH=/opt/greia-os/src python3 - <<'PY' ...` → capture `STRICT_DISCOVERY`, `UNVALIDATED_COUNT`, `UNVALIDATED=...`, plus `tools/greia_remote.py logs --service launcher --lines 500`
4. **Do not** harden Legacy-X (§12) yet — first test narrow fix
5. Simulator gate at fixed SHA (§8): Writing, Painting, Shape Garden, one extra, hostile — Home protection semantic check
6. Deploy **exact fixed SHA** to Acer via `tools/deploy_to_acer.py` (180s extraction/chown, whole-repo copy not single file), then `wait --timeout 180`, `status`, `screenshot tmp/home-regression-shell.png`
7. Physical Home acceptance (§11) at 1024×600 for each Activity: launch → wait stable frame → screenshot → inspect Home glyph top-left → click (38,38) → require return to Greia → require Activity process gone → require immediate Shell responsiveness. Record `WRITING_HOME_VISIBLE`, `WRITING_HOME_ACTION`, etc. plus `FAIL_CLOSED_CHROME_FAILURE` and `USAGE_LIMIT_WRAPPER_SANITY`. Any `Activity remains usable/fullscreen + no Home` is immediate FAIL.
8. Only if Home still absent despite proven trusted supervisor, STOP and proceed to §12 Legacy-X hardening (override_redirect, VisibilityChangeMask, map/raise after READY, fail-closed fully-obscured handling, bounded raise, no polling/thread/Pygame).

**Blockers:**

```text
R7.2/R7.3/Parent physical: INCOMPLETE — superseded by Home regression which blocks release; previous 1edb22ce candidate stale (runtime changed) per runbook §9
Launcher spoken labels: SOURCE-AND-HUMAN-COMPLETE (106/106 ACCEPTED) but ACER formal + SIMULATOR GUI PENDING; not to be combined until Home regression is PHYSICAL-PASS
OVERALL VERDICT: SOURCE-FIXED / PHYSICAL-PENDING — see final report template §13
```

Do not call Home fixed until a real Acer Activity screenshot visibly contains Home and clicking (38,38) returns through the platform lifecycle. If §11 fails despite trusted composition, the required next direction is narrow `CtypesLegacyXChromeBridge` hardening (§12), not Activity-side Home.
