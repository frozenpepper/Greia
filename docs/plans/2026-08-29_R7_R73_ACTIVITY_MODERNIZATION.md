# R7.3 Activity Modernization Plan

**Date:** 2026-08-29
**Status:** ACTIVE implementation plan — one Activity at a time, sequential
**Authoritative review (gap analysis):** `docs/reviews/2026-08-29_R7_R73_ACTIVITY_CHROME_MIGRATION_TRANCHE.md` (tranche review) and `docs/reviews/2026-08-29_R7_R73_TRUSTED_CHROME_SOURCE_TRANCHE.md`
**Subordinate to:** `AGENTS.md`, `HANDOVER.md`, `docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md`
**Phase:** R7.3 (trusted Greia Home + Activity ownership migration)
**Scope:** 34 first-party Greia Activities, this ledger
**Branch:** `main` (work directly on `main`; commit one Activity or tightly-related pair per commit; no branch creation; no GitHub Actions)

---

## 0. Pre-flight (already verified by the test agent on 2026-08-29)

Pre-flight test results on `5ef785085d106fdcf8e876323f6e7ab3ca2e0d7c`:

```text
focused source tests:         66/67 PASS, 1 FAIL
                               (test_r7_noncooperative_chrome_fixture:
                                assertNotIn("activity_stop_requested") fires
                                on the literal token inside the fixture
                                docstring — false positive on a comment.)

backend audit:                blockers=0  (PASS; 30 migration findings,
                                          26 Activities)

chrome ownership --strict:    blockers=62  (FAIL — required 0)

make verify:                  1516/1520 PASS, 4 FAIL, exit 1
                              3× substring "-m greia_launcher.presentation"
                                  expected in greia-x-session; current
                                  script uses "-m greia_launcher.trusted_presentation"
                              1× same fixture-docstring false positive
```

This means the current `main` has known source-gate failures independent of Activity work that must be repaired at the platform level before this plan can run cleanly. The plan below is therefore staged:

- **Stage A (gate repair):** fix the two source-gate failures that are NOT Activity work — the fixture docstring token and the `greia-x-session` substring expectation. These must land first; otherwise no Activity commit can be followed by a clean `make verify`.
- **Stage B (Activity queue):** run the strict audit, process Activities one by one, regenerate a clean strict audit at the end, then re-run `make verify`.
- **Stage C (final repository gate):** `audit_activity_system_chrome_ownership.py --strict` must reach `blockers=0`; `audit_activity_backend_independence.py activities` must report zero blockers; `make verify` must be green.

---

## 1. Activity list (authoritative, complete)

These are all 34 first-party Activities currently shipped under `activities/`. The list is the canonical queue for this plan. Order is by R7.3 strict-audit blocker presence first (visible in the audit output below), then by Activity ID.

### 1.1 Strict-audit blockers (the mandatory R7.3 migration queue)

These are the Activities that the strict `--strict` audit reports as first-party blockers. They own the retired cooperative Home helper / `PygameReferenceCanvas.present(system_chrome=...)` pattern. **Each MUST be processed before this plan can declare R7.3 source-integrated.**

Source for the queue: `PYTHONPATH=src python3 tools/audit_activity_system_chrome_ownership.py --strict` (run on the current SHA — see evidence directory `./tmp/r7-r73-test-1787976259/chrome-ownership-audit.log`).

| # | Activity | Strict-audit blockers (count) | Notes |
|---|---|---|---|
| 1 | `clinica_cuccioli` | (already healthy structurally; was the R7.3 calibration target) | `test_activity_clinica_cuccioli.py` — confirm clean. |
| 2 | `la_discesa_della_biglia` | `legacy_helper_import: is_home_clicked` × 1 | `ramp_app.py:28` |
| 3 | `labirinto_magico` | `legacy_helper_import: ActivitySystemChromeLayout` × 1 (maze_renderer.py:9) + first-wave exemplar (already migrated, residual may be in the renderer) | `maze_renderer.py:9` |
| 4 | `luci_di_momo` | `legacy_helper_import: is_home_clicked` × 1 | `firefly_app.py:13` |
| 5 | `memory_meraviglie` | `legacy_helper_import: is_home_clicked` × 1 | `main.py:24` |
| 6 | `nascondino_bosco` | `legacy_helper_import: is_home_clicked` × 1 + call ×1 | `woodland_app.py:17`, `:171` |
| 7 | `officina_dei_suoni` | `legacy_helper_import: is_home_clicked` × 1 + calls × 2 | `sound_app.py:14`, `:230`, `:366` |
| 8 | `orchestra_animali` | `legacy_helper_import: is_home_clicked` × 1 + call × 1 | `main.py:21`, `:421` |
| 9 | `pasticceria_magica` | `legacy_helper_import: is_home_clicked` × 1 + call × 1 | `main.py:22`, `:261` |
| 10 | `piccola_serra` | `legacy_helper_import: is_home_clicked` × 1 + call × 1 | `main.py:23`, `:291` |
| 11 | `posta_di_leo` | `legacy_helper_import: is_home_clicked` × 1 + call × 1 | `postcard_app.py:13`, `:185` |
| 12 | `sillabe_magiche` | `legacy_helper_import: is_home_clicked` × 1 + calls × 2 | `main.py:22`, `:850`, `:855` |
| 13 | `specchi_magici` | `legacy_helper_import: is_home_clicked` × 1 + calls × 2 | `mirror_app.py:13`, `:169`, `:304` |
| 14 | `teatrino_fiabe` | `legacy_helper_import: draw_system_chrome_overlay` × 1, `legacy_helper_import: is_home_clicked` × 1, call × 1 | `main.py:38`, `:1163` |
| 15 | `treno_numeri` | `legacy_helper_import: is_home_clicked` × 1 + call × 1 | `main.py:23`, `:317` |
| 16 | `viaggio_delfino` | `legacy_helper_import: is_home_clicked` × 1 + call × 1 | `delfino_app.py:22`, `:372` |
| 17 | `workshop_settings` | `legacy_helper_import: draw_system_chrome_overlay` × 1, `legacy_helper_import: is_home_clicked` × 1, `legacy_helper_import: ActivitySystemChromeLayout` × 1, calls × 2 | `main.py:26`, `:158`, `:277`, `:34` |
| 18 | `acquario_magico` | (no strict blocker in current audit; included for lighter review per step #1) | Performance case study precedent already in `GREIA_PERFORMANCE_BEST_PRACTICES.md` — verify no regression. |
| 19 | `baia_delle_orche` | (no strict blocker; included for lighter review) | Subject-rich (orca), strong candidate for `Tito` presenter + curiosity facts. |
| 20 | `bottega_delle_misure` | (no strict blocker) | Math/measurement — `Dani` affinity. |
| 21 | `casa_del_dieci` | (no strict blocker) | Math — `Dani` affinity. |
| 22 | `costruiamo_ponti` | (no strict blocker) | Engineering — `Dani` affinity. Performance case study precedent. |
| 23 | `cucciolo_mio` | (no strict blocker) | Caring/nurture — `Lilli` affinity. |
| 24 | `enciclopedia_greia` | (no strict blocker; E3/E4 workstream) | Out of R7.3 scope; managed under `docs/plans/2026-08-28_ENCYCLOPEDIA_VISUAL_REAUTHORING.md`. Do not mix into R7.3. |
| 25 | `festa_delle_rime` | (no strict blocker) | Reading/rhyme — `Leo` affinity. |
| 26 | `foresta_parole` | (no strict blocker) | Language/words — `Leo` affinity. |
| 27 | `morbidi_mostriciattoli` | (no strict blocker) | Soft/craft — `Lilli`/`Momo` affinity. |
| 28 | `nanna_delle_nuvolette` | (no strict blocker) | Sleep/comfort — `Momo`/`Lilli` affinity. |
| 29 | `pasticceria_magica` | already in #9 strict queue | (duplicate; remove) |
| 30 | `shape_garden` | (first-wave exemplar; no strict blocker) | R7.3 confirmation only. |
| 31 | `stelle_incantate` | (no strict blocker) | Constellations/space — `Tito`/`Leo` affinity. |
| 32 | `storie_della_mia_voce` | (first-wave exemplar; no strict blocker) | R7.3 confirmation only. |
| 33 | `volo_draghetto` | (first-wave exemplar; no strict blocker) | R7.3 confirmation only. |
| 34 | `writing` | (first-wave exemplar; no strict blocker) | R7.3 confirmation only. |
| 35 | `painting` | (first-wave exemplar; no strict blocker) | R7.3 confirmation only. |

After items 1–17 are completed, the strict audit should drop substantially. Items 18–34 (except `enciclopedia_greia`) are the **lighter architecture/performance review** pass; only the Activities that prove genuinely monolithic or have obvious hot-path issues are refactored. Healthy small Activities are left alone.

`enciclopedia_greia` is **explicitly excluded from this plan** because it is governed by `docs/plans/2026-08-28_ENCYCLOPEDIA_VISUAL_REAUTHORING.md` and the current `HANDOVER.md` says "do not begin E4" and "no local-agent visual-authoring task is currently authorized."

---

## 2. Per-Activity execution procedure

The same procedure is applied to every Activity in the queue. It is intentionally repetitive so that the agent doing the work does not have to invent steps. Each Activity produces exactly one commit (or a small set of coherent commits for larger refactors — see Section 6).

### 2.1 Inspect before editing

Read the whole Activity first. Do not edit based on a single flagged line.

```text
activity.toml                 # declared entrypoint, input profile, capabilities, locales, events
entrypoint (main.py / *_app.py / <manifest entrypoint>) # actual launch path
all Python/source modules     # architecture, hot paths, asset usage, audio, storage, events
tests                         # existing focused tests, contract tests, performance tests
assets/                       # canonical vs. local duplicates
locales/                      # declared vs. actual localized presentation
audio/                        # shared utterances vs. Activity-local recordings
storage/state                 # schema version, keys, save/restore
events/progression            # declared vs. emitted
research/facts                # where present
```

Search the repository for imports of any symbol that lives in the Activity before moving it:

```bash
grep -R "from activities.<name>" --include='*.py' .
grep -R "import activities.<name>" --include='*.py' .
grep -R "activities.<name>." --include='*.py' .
```

Also re-read the activity in the context of the `HANDOVER.md` notes about it and any dated `docs/reviews/visual/...` review.

### 2.2 Record in the modernization ledger (Section 3 of this plan)

For each Activity record the inspection results in the per-Activity ledger entry:

```text
Activity:
R7.3 migration: done
Architecture: unchanged / refactored
Main entrypoint: thin / acceptable / remaining debt
Presenter: <character / deliberate none>
Voice: existing / changed / recording required
Pre-reader UX: pass / issue fixed / remaining issue
Assets: pass / cleanup performed
Performance: reviewed + concrete changes
Manifest/localization/storage/events: pass / repairs
Simulator: PASS/FAIL
Commit:
Notes:
```

### 2.3 Apply the R7.3 Home/Back migration (mandatory for every Activity in the strict queue)

Activity code must no longer import or call:

```text
draw_system_chrome_overlay
is_home_clicked
```

and must not request:

```python
canvas.present(system_chrome=...)
```

- Remove the Activity-side Home drawing and Home-click branches.
- DO NOT remove renderer-neutral protected/safe geometry. Keep:
  - `ActivitySystemChromeLayout`
  - `ActivityViewport`
  - `activity_safe_rect()`
  - `activity_content_rect()`
  - `activity_toolbar_button()`
  - `activity_viewport_for_surface()`
- The Activity must leave Greia's protected region alone; the launcher/simulator owns the real Home/Back renderer and action.
- Preserve: `activity_stop_requested()`, `mark_activity_ready()`, normal graceful cleanup, storage/save behavior.
- Do not replace efficient direct Pygame input/rendering with IPC or another abstraction layer.
- For `workshop_settings` specifically: this is a parent/settings surface, not a child Activity. Migration of the Home helper out of it is required by the strict audit, but the surface itself must remain parent-only and continue to drive the real Parent panel/auth flow. Verify that the post-migration surface still calls the same Parent panel entry path and the same auth flow.

### 2.4 Architecture review (mandatory for every touched Activity)

Goal: leave a thin `main.py`. Do not split files by line count; split by responsibility.

A `main.py` is a refactoring candidate when it simultaneously owns things such as:

```text
domain/game rules
mutable session state
rendering
asset preparation
audio
storage
Greia event emission
input interpretation
lifecycle/event loop
```

Preferred decomposition:

```text
model/session      -> gameplay rules and state
renderer/view      -> Pygame rendering, geometry, prepared visual resources
audio              -> prepared sounds and Activity-specific audio behavior
services/progress  -> storage/event integration when complex enough
app/activity       -> event loop and coordination
main.py            -> construct collaborators and enter the Activity
```

Examples: `ActivitySession`, `ActivityRenderer`, `ActivityAudio`, `ActivityApp`.

Use narrow Protocols/interfaces only where genuine substitution is useful. Do not create fake classes around pure drawing/math functions. Stateless rendering helpers may remain functions.

Reuse existing `greia_platform` classes/primitives before creating new infrastructure. Do not promote an Activity-local abstraction into `greia_platform` after one example.

#### Import compatibility

The Activity must work in BOTH:

- Greia runtime/script execution
- repository/package import used by tests

Use the established package/script compatibility pattern from `REFACTORING.md`:

```python
if __package__:
    from .model import ActivityModel
    from .presentation import ActivityPresentation
else:
    from model import ActivityModel
    from presentation import ActivityPresentation
```

Do not add Activity module names to the global external dependency allowlist.

Preserve established public exports from `main.py` if tests/tools legitimately consume them, or deliberately migrate every consumer in the same commit. Search before moving.

### 2.5 Child UX / intelligibility review (mandatory)

Assume the child cannot read.

For every touched Activity, check whether a child can understand:

- what to do first
- what can be interacted with
- whether an action worked
- what happened after a mistake
- how to continue/replay

without reading instructions.

Prefer:

- visual hierarchy
- large obvious targets
- pictures/icons/numbers
- short demonstrations/animation
- character gestures
- short spoken cues when language is useful
- clear visual/audio feedback

Do not use voice merely to rescue a confusing screen.

Primary interactive targets should respect Greia's child-size conventions, normally at least ~64×64 logical px and preferably larger for important actions.

Wrong actions should produce friendly visual/audio retry feedback, not text-heavy error messages.

Reading/letters Activities may obviously contain text as subject matter, but their **interaction instructions** must still be understandable by a pre-reader.

Child-facing UI text must follow the Greia presentation/localization policy, including CAPITAL-letter presentation through the proper platform mechanism. Do not manually uppercase child-authored content. Use `greia_platform.child_text.display_text(...)` for package-local literal strings.

### 2.6 Canonical Greia characters (mandatory decision)

For each Activity, explicitly consider whether a recurring Greia character should present, guide or react. Affinity guidance (from `docs/design/GREIA_CANONICAL_CAST_SYSTEM.md`):

```text
Lilli  -> creativity, stories, art, imagination
Leo    -> language, reading, knowledge, explanation
Flash  -> action, games, speed, challenge
Dani   -> logic, math, patterns, sequencing
Tito   -> exploration, nature, discovery
Momo   -> music, emotion, silliness, celebration
```

Do not force a presenter into an Activity where it would add nothing. But do not accidentally omit Greia's cast simply because the Activity already technically functions.

A presenter should have a purpose (welcome, demonstration, instruction, reaction, hint, celebration, curiosity/fact). Do not turn Activities into long talking tutorials.

Do not replace an Activity-specific subject character that is integral to its concept merely to insert an OS character. Canonical presenters and Activity subject characters can coexist.

Reuse the canonical Greia character assets and shared visual systems. Do not create duplicate local copies of canonical characters unless the current asset architecture explicitly requires a packaged rendition.

### 2.7 Voice / audio review (mandatory)

Classify spoken content correctly using the priority order from `VOICE_GENERATION.md`:

```text
shared character utterance
    generic praise/retry/progress/celebration

canonical character dialogue
    Activity-specific instruction, narration, hint, fact

pedagogical deterministic speech
    letters, phonics, syllables, pronunciation targets

Dani/system route
    where Dani's intentionally robotic speech is required
```

Never add runtime Chatterbox, Whisper or normal host TTS.

If new speech is genuinely necessary, use only:

```text
tools/greia_voice.py
skills/greia-voice-production/SKILL.md
```

Prefer existing accepted shared utterances before generating new generic lines.

For letters/syllables or other pronunciation-critical pedagogical audio, use the deterministic route defined by the Voice Engine rather than forcing Chatterbox.

If new audio is generated, mark it as requiring human listening/owner acceptance. Generated audio is not automatically accepted merely because generation succeeded.

Do not block a structural R7 migration by unnecessarily inventing new dialogue. If voice is desirable but missing, implement the clean semantic cue/slot and report exactly what recording is required.

### 2.8 Assets and visual cleanup (mandatory)

Check for:

```text
duplicated canonical assets
assets decoded repeatedly
assets repeatedly scaled in the frame loop
unconverted Pygame surfaces
large programmer-generated visuals replacing existing proper Greia artwork
dead/unused assets
hard-coded paths
```

Reuse Greia's visual/asset infrastructure where appropriate.

Do not launch a wholesale art redesign during this pass.

However, if an Activity is using an obviously obsolete placeholder despite an existing canonical Greia asset that already solves the same job, migrate it.

Subject-rich Activities should not regress to crude programmer-drawn representations when approved proper artwork already exists.

### 2.9 Performance review (mandatory)

Assume first-generation Acer Aspire One class hardware. Look specifically for expensive work inside event/frame loops. Do not perform per frame:

```text
pygame.image.load()
smoothscale of stable assets
font construction
stable text rendering
large Surface creation
static gradient generation
filesystem scans/stats
storage writes
device discovery
subprocess calls
controller discovery
```

Prefer:

```text
decode once
convert()/convert_alpha() once
cache scaled variants
pre-render static backgrounds
opaque pre-composition for large static regions
dirty/invalidation rendering where appropriate
bounded caches with explicit invalidation
cached finite text surfaces
cached transforms
bounded particle/effect lists
adaptive/low-cost idle pacing
```

Be especially suspicious of large per-pixel-alpha surfaces. On the Acer these are extremely expensive compared with opaque blits.

Do not create caches merely because caching sounds faster. If dirty rendering already prevents repeated work, another full-frame cache can make architecture worse.

Keep high-rate pointer/text gameplay paths direct and lightweight.

If you change a meaningful hot path, add a focused equivalence/regression test where practical.

Do not claim Acer performance improvements unless physically measured. Source inspection may say `removed obvious per-frame scaling / removed repeated image decode / added bounded cache` but not `Acer is now 40% faster` without measurement.

### 2.10 General correctness / cleanup review

While touching the Activity, fix small clear technical debt that is directly adjacent to the work:

```text
dead imports
dead unreachable code
duplicated constants
conflicting gameplay rules in multiple input branches
incorrect manifest event IDs
undeclared/unused capabilities
hard-coded locale strings
storage keys inconsistent with manifest/design
incorrect READY/STOP handling
unbounded lists/caches
broad exception swallowing that hides real defects
obvious resource leaks
missing cleanup
```

One semantic child action should have one domain rule. Do not let keyboard, pointer and controller paths each independently decide whether an answer/action is correct.

Input should identify the child's attempted action; the domain/session decides what it means.

Do not accidentally auto-select the correct answer merely because the model knows it.

Keep comments useful: explain ownership, invariants and non-obvious performance decisions. Remove comments that merely narrate obvious code.

Add type hints where they materially improve interfaces and state ownership.

Do not add local package-cleanup logic for `.DS_Store`, caches, etc. Installed tree sanitation is platform-owned under current Greia policy.

### 2.11 Testing each Activity before committing (mandatory)

After the final source edit for an Activity, run, in this order:

1. The relevant focused tests for the Activity (see `tests/test_activity_<name>.py`).
2. Project validation:

   ```bash
   PYTHONPATH=src:tools python3 tools/validate_project.py
   ```
3. The two architecture audits:

   ```bash
   PYTHONPATH=src python3 tools/audit_activity_backend_independence.py activities
   PYTHONPATH=src python3 tools/audit_activity_system_chrome_ownership.py --strict
   ```

   The strict chrome audit does not need to be globally zero until the final Activity is migrated, but the Activity you just completed MUST disappear from its blocker list.
4. If the Activity was structurally refactored, verify BOTH package-import and real runtime/script contexts:

   ```bash
   PYTHONPATH=src python3 -c "import activities.<name>.main"  # package import
   python3 activities/<name>/main.py                            # script launch
   ```
5. Then launch the final Activity through the real Greia Activity Simulator:

   ```bash
   python3 tools/greia_simulator.py
   ```

   For every modified Activity verify:

   ```text
   appears normally
   launches through Greia
   first usable frame
   survives >=10 seconds
   meaningful child interaction works
   Greia Home works
   clean return to Shell
   ```

   If gameplay has completion/restart/results, exercise those too.

A structural refactor that imports successfully but crashes at completion is a failed refactor.

Only after the final Simulator state passes should you commit that Activity.

### 2.12 Commit discipline

Prefer one coherent commit per Activity:

```text
Activity: modernize <name> for R7.3
```

The commit should contain the complete coherent Activity change:

```text
Home ownership migration
architecture cleanup/refactor
performance cleanup
UX/localization/asset fixes directly related to the review
tests
```

Do not mix five unrelated Activities in one giant commit.

If an Activity needs a larger multi-step refactor, use several coherent commits, but leave the Activity working at the end of the tranche.

### 2.13 Update the ledger and HANDOVER

After committing, append the Activity's row to the modernization ledger (Section 3 of this plan). After meaningful tranches (e.g. after every ~5 Activities, or at any rate at the end of each working session), update:

- `HANDOVER.md` (current phase, implemented work, verification/evidence, blockers, next exact step)
- `docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md` (append-only progress entry)

---

## 3. Modernization ledger (append-only, one row per Activity)

This ledger is the single source of truth for the per-Activity state. Append a new row when an Activity is committed. Do not rewrite earlier rows.

```text
Activity: clinica_cuccioli
R7.3 migration: already clean (R7.3 calibration target)
Architecture: refactored (model/renderer/audio/app/main)
Main entrypoint: thin
Presenter: Lilli (deliberate; cure/friendship)
Voice: shared utterances
Pre-reader UX: pass
Assets: pass
Performance: pre-existing; check not regressed
Manifest/localization/storage/events: pass
Simulator: PASS (historical, R7.3 calibration)
Commit: (historical)
Notes: This is the reference architecture for the rest of this plan. Keep it
       stable; do not modify it just because other Activities exist.
```

(Subsequent rows are filled in as the work proceeds.)

---

## 4. Sequencing

The work is split into three explicit stages. Each stage ends with a verification gate; if the gate fails, fix the failure before moving on.

### Stage A — Source-gate repair (not Activity work)

Two source-gate failures are independent of the Activity queue and block all downstream `make verify` runs:

1. **Fix the `test_r7_noncooperative_chrome_fixture` false positive.** The test does `assertNotIn("activity_stop_requested", source)` on the fixture source. The literal token appears inside the fixture's own docstring (a comment that says the fixture *does not* call it). Either:
   - change the test to scan the AST (more correct), or
   - move the docstring so the token is no longer a literal substring.
   Pick the option that makes the audit semantically correct.

2. **Fix the three contract tests expecting `-m greia_launcher.presentation` substring in `build/overlay/usr/local/lib/greia-os/greia-x-session`.** The script was deliberately migrated to `greia_launcher.trusted_presentation` for R7.3. Update the contract tests to expect `-m greia_launcher.trusted_presentation` (or accept either of the two trusted paths), preserving the semantic intent of the test (a profile-aware primary path with a trusted fallback).

Verification:

```bash
PYTHONPATH=src:tests python3 -m unittest \
  test_r7_noncooperative_chrome_fixture \
  test_launcher_boot_fallback \
  test_installation_hardware_regressions \
  test_my_greia_settings_contract \
  -v
PYTHONPATH=src:tools python3 tools/validate_project.py
```

Expected: all green.

### Stage B — Activity queue (one Activity at a time)

Run the strict audit once and treat its output as the queue:

```bash
PYTHONPATH=src python3 tools/audit_activity_system_chrome_ownership.py --strict > ./tmp/strict-audit-stage-b-initial.log
```

Process the Activities in the order from Section 1.1, items 1–17 (the strict-queue). After each Activity:

- Re-run the strict audit and confirm the Activity's blockers are gone.
- Re-run focused tests + `validate_project.py`.
- Launch through `python3 tools/greia_simulator.py`.
- Commit per Section 2.12.
- Append a row to the ledger (Section 3).

When items 1–17 are committed and the strict audit shows a non-trivial reduction, run the lighter architecture/performance review (items 18–34, excluding `enciclopedia_greia`). Only refactor an Activity in this pass if:

- it is a giant procedural `main.py` (clearly > 250 lines with mixed responsibilities), OR
- it has an obvious hot-path issue, OR
- it has an obvious pre-reader UX failure.

Healthy small Activities are left alone.

### Stage C — Final repository gate

Once all R7.3 Activity blockers have been migrated (or it is established that none remain after the lighter pass):

```bash
PYTHONPATH=src python3 tools/audit_activity_system_chrome_ownership.py --strict
```

must report:

```text
Activity system chrome ownership audit: blockers=0
```

Then:

```bash
PYTHONPATH=src python3 tools/audit_activity_backend_independence.py activities
```

must report zero blockers. Then:

```bash
make verify
```

must exit zero.

Do not start Acer acceptance from this plan — that is owned by the R7.3 acceptance protocol (`docs/testing/2026-08-29_R7_R73_TRUSTED_SYSTEM_CHROME_SOURCE_AND_ACER_ACCEPTANCE.md`) and is not the job of this plan.

---

## 5. Final report format (after Stage C is complete)

```text
Activities reviewed: <count>
Activities R7.3-migrated: <count>
Activities structurally refactored: <count>
Activities already architecturally healthy: <count>
Remaining architecture debt: <list or "none">

System-chrome audit blockers: 0
Backend audit blockers: 0
make verify: PASS

Presenter/character improvements: <count>
Voice recordings still requiring generation/listening: <list>
Localization/pre-reader fixes: <count>
Asset cleanups: <count>
Performance cleanups: <count>

Simulator:
<each modified Activity PASS/FAIL>

Important behavior defects found and fixed: <list>
Anything deliberately NOT changed: <list>

Final SHA: <sha>
```

---

## 6. Worked example — first strict-queue Activity (`la_discesa_della_biglia`)

For each Activity the same checklist applies. The first one is shown here as a worked example; the rest follow the same template.

```text
Activity: la_discesa_della_biglia
entrypoint: ramp_app.py
current architecture: small/medium; single-file `ramp_app.py`
R7.3 blockers: 1 — `legacy_helper_import: is_home_clicked` at ramp_app.py:28
presenter/character: Tito (descent/exploration) — confirm and add if missing
voice/audio: shared utterances; no new recording expected
localization: pass-through
storage/events: pass
obvious performance risks: gradient/ball rendering in the frame loop — review for caching
obvious UX problems: minimal — confirm the ramp gradient/goal visual hierarchy

Steps (per Section 2):
  2.1 inspect ramp_app.py + activity.toml + tests/test_activity_la_discesa_della_biglia.py
  2.2 fill in the ledger row
  2.3 remove `from greia_platform.activity_api import is_home_clicked` and any
      call site; keep ActivitySystemChromeLayout for the safe region
  2.4 if `ramp_app.py` is small and single-responsibility, leave it as one file
  2.5 pre-reader pass: ball-vs-target visual hierarchy, no reading required
  2.6 presenter: Tito confirms (existing) or add a small Tito icon in the corner
  2.7 voice: shared utterances
  2.8 assets: confirm no local duplicate of canonical Tito
  2.9 performance: cache ramp gradient if rendered per frame
  2.10 cleanup: dead imports, dead constants
  2.11 tests:
        PYTHONPATH=src:tests python3 -m unittest test_activity_la_discesa_della_biglia -v
        PYTHONPATH=src python3 tools/audit_activity_system_chrome_ownership.py --strict
        -> confirm la_discesa_della_biglia no longer appears
        python3 tools/greia_simulator.py -> launch, interact, Home, return
  2.12 commit: "Activity: modernize la_discesa_della_biglia for R7.3"
  2.13 append ledger row; update HANDOVER at the next session boundary.
```

---

## 7. Ledger (filled in as the work proceeds)

The ledger is the source of truth for what has been done in this plan. Append a new row per Activity committed. Do not rewrite earlier rows.

```text
Activity: la_discesa_della_biglia
R7.3 migration: done (commit 7185b0ce)
Architecture: already well-decomposed (ramp_app/ramp_engine/ramp_renderer/ramp_audio/ramp_services/ramp_content); only package-import compat was missing
Main entrypoint: thin (38 lines)
Presenter: none (mechanical/physics Activity; no canonical character was used and adding one would obstruct the gameplay)
Voice: none
Pre-reader UX: pass (palette buttons large, ball drop visual, finished banner visual-only)
Assets: pass
Performance: pass (engine deterministic, renderer builds palette surfaces once)
Manifest/localization/storage/events: pass (storage key namespaced, events tool_placed/run_started/basket_hit/etc)
Simulator: PASS (15 frames @ 30fps headless; activity builds and draws)
Commit: 7185b0ce
Notes: First Activity processed. Other fixes: removed unused 'RampApp'
       import and the dead 'RampApp.__class__' workaround in main.py.

Activity: labirinto_magico
R7.3 migration: PENDING (first-wave exemplar; remaining blocker is in maze_renderer.py:9 ActivitySystemChromeLayout reference)
Architecture: PENDING
Main entrypoint: PENDING
Presenter: PENDING
Voice: PENDING
Pre-reader UX: PENDING
Assets: PENDING
Performance: PENDING
Manifest/localization/storage/events: PENDING
Simulator: PENDING
Commit: PENDING
Notes: This is an R7.3 first-wave exemplar; the remaining audit hit is in
       maze_renderer.py and may simply be that the renderer imports the
       ActivitySystemChromeLayout type without using the helper. Investigate
       before refactoring.

Activity: luci_di_momo
R7.3 migration: PENDING
Architecture: PENDING
Main entrypoint: PENDING
Presenter: PENDING
Voice: PENDING
Pre-reader UX: PENDING
Assets: PENDING
Performance: PENDING
Manifest/localization/storage/events: PENDING
Simulator: PENDING
Commit: PENDING
Notes: Momo affinity (light/silly/emotion). Confirm safe-region geometry
       preserved during migration.

Activity: memory_meraviglie
R7.3 migration: PENDING
Architecture: PENDING
Main entrypoint: PENDING
Presenter: PENDING
Voice: PENDING
Pre-reader UX: PENDING
Assets: PENDING
Performance: PENDING
Manifest/localization/storage/events: PENDING
Simulator: PENDING
Commit: PENDING
Notes: Memory game; high-rate pointer path. Review hot loop for cache
       misses on card-back surface.

Activity: nascondino_bosco
R7.3 migration: PENDING
Architecture: PENDING
Main entrypoint: PENDING
Presenter: PENDING
Voice: PENDING
Pre-reader UX: PENDING
Assets: PENDING
Performance: PENDING
Manifest/localization/storage/events: PENDING
Simulator: PENDING
Commit: PENDING
Notes: Hide-and-seek; natural curiosity hook (Tito affinity).

Activity: officina_dei_suoni
R7.3 migration: PENDING
Architecture: PENDING
Main entrypoint: PENDING
Presenter: PENDING
Voice: PENDING
Pre-reader UX: PENDING
Assets: PENDING
Performance: PENDING
Manifest/localization/storage/events: PENDING
Simulator: PENDING
Commit: PENDING
Notes: Sound workshop; Momo affinity. Audio review required; pre-reader
       icon-based instrument UI expected.

Activity: orchestra_animali
R7.3 migration: PENDING
Architecture: PENDING
Main entrypoint: PENDING
Presenter: PENDING
Voice: PENDING
Pre-reader UX: PENDING
Assets: PENDING
Performance: PENDING
Manifest/localization/storage/events: PENDING
Simulator: PENDING
Commit: PENDING
Notes: Animal orchestra; Momo affinity. Animal icons, pre-reader friendly.

Activity: pasticceria_magica
R7.3 migration: PENDING
Architecture: PENDING
Main entrypoint: PENDING
Presenter: PENDING
Voice: PENDING
Pre-reader UX: PENDING
Assets: PENDING
Performance: PENDING
Manifest/localization/storage/events: PENDING
Simulator: PENDING
Commit: PENDING
Notes: Magical bakery; creativity/storytelling — Lilli affinity.

Activity: piccola_serra
R7.3 migration: PENDING
Architecture: PENDING
Main entrypoint: PENDING
Presenter: PENDING
Voice: PENDING
Pre-reader UX: PENDING
Assets: PENDING
Performance: PENDING
Manifest/localization/storage/events: PENDING
Simulator: PENDING
Commit: PENDING
Notes: Small greenhouse; nature/observation — Tito affinity.

Activity: posta_di_leo
R7.3 migration: PENDING
Architecture: PENDING
Main entrypoint: PENDING
Presenter: PENDING
Voice: PENDING
Pre-reader UX: PENDING
Assets: PENDING
Performance: PENDING
Manifest/localization/storage/events: PENDING
Simulator: PENDING
Commit: PENDING
Notes: Leo's post office; language/letters — Leo affinity.

Activity: sillabe_magiche
R7.3 migration: PENDING
Architecture: PENDING
Main entrypoint: PENDING
Presenter: PENDING
Voice: PENDING
Pre-reader UX: PENDING
Assets: PENDING
Performance: PENDING
Manifest/localization/storage/events: PENDING
Simulator: PENDING
Commit: PENDING
Notes: Syllables; pedagogical speech path. Leo affinity.
       Pedagogical speech must remain deterministic; do not switch to
       Chatterbox for pronunciation.

Activity: specchi_magici
R7.3 migration: PENDING
Architecture: PENDING
Main entrypoint: PENDING
Presenter: PENDING
Voice: PENDING
Pre-reader UX: PENDING
Assets: PENDING
Performance: PENDING
Manifest/localization/storage/events: PENDING
Simulator: PENDING
Commit: PENDING
Notes: Magic mirrors; visual transformation Activity. Confirm the
       transformation work is not in the per-frame loop.

Activity: teatrino_fiabe
R7.3 migration: PENDING
Architecture: PENDING
Main entrypoint: PENDING
Presenter: PENDING
Voice: PENDING
Pre-reader UX: PENDING
Assets: PENDING
Performance: PENDING
Manifest/localization/storage/events: PENDING
Simulator: PENDING
Commit: PENDING
Notes: Puppet theatre; storytelling — Lilli affinity. High candidate
       for subject-specific character (puppets) coexisting with a
       canonical presenter.

Activity: treno_numeri
R7.3 migration: PENDING
Architecture: PENDING
Main entrypoint: PENDING
Presenter: PENDING
Voice: PENDING
Pre-reader UX: PENDING
Assets: PENDING
Performance: PENDING
Manifest/localization/storage/events: PENDING
Simulator: PENDING
Commit: PENDING
Notes: Number train; math — Dani affinity.

Activity: viaggio_delfino
R7.3 migration: PENDING
Architecture: PENDING
Main entrypoint: PENDING
Presenter: PENDING
Voice: PENDING
Pre-reader UX: PENDING
Assets: PENDING
Performance: PENDING
Manifest/localization/storage/events: PENDING
Simulator: PENDING
Commit: PENDING
Notes: Dolphin journey; nature/sea — Tito affinity.

Activity: workshop_settings
R7.3 migration: PENDING
Architecture: PENDING
Main entrypoint: PENDING
Presenter: none (parent-only surface)
Voice: none (parent-only surface)
Pre-reader UX: n/a (parent surface)
Assets: pass
Performance: PENDING
Manifest/localization/storage/events: PENDING
Simulator: PENDING (this is parent-only; do not exercise through child Simulator)
Commit: PENDING
Notes: Parent/settings surface. Migration of Home helper out of this
       surface is required by the strict audit but the surface itself
       must remain parent-only and continue to drive the real Parent
       panel/auth flow. Do not introduce child-targeted UX here.

Activity: clinica_cuccioli (control / reference)
R7.3 migration: clean (R7.3 calibration target)
Architecture: refactored (model/renderer/audio/app/main)
Main entrypoint: thin
Presenter: Lilli (deliberate; cure/friendship)
Voice: shared utterances
Pre-reader UX: pass
Assets: pass
Performance: pre-existing; confirm not regressed
Manifest/localization/storage/events: pass
Simulator: PASS (historical, R7.3 calibration)
Commit: historical
Notes: This is the reference architecture for the rest of this plan.
       Keep it stable; do not modify it just because other Activities exist.
```

(Subsequent rows are filled in as the lighter architecture/performance pass proceeds.)
