# Recent Commit Cleanup — Source, Simulator and Acer Acceptance

**Status:** ACTIVE focused acceptance procedure  
**Date:** 2026-09-02  
**Scope:** recent toddler-Activity runtime cleanup and installed Parent production composition  
**Evidence class:** SOURCE / SIMULATOR / PHYSICAL are separate; do not promote one into another

This procedure validates the cleanup that followed the `09381df6` Bosco educational-flow remediation. It does **not** replace the current R7 physical procedure in `docs/testing/2026-09-02_R7_FINAL_EVIDENCE_GAP_CLOSURE.md`.

The cleanup under test includes:

- Greia-owned pointer mapping for the three toddler Activities; no Activity-side Home authority;
- bounded/prebuilt toddler procedural SFX and mixer-aware signed PCM16 formatting;
- Bosco localization through `LocalizedResources` rather than a duplicate hard-coded string table;
- explicit installed Parent composition in `greia_parent.production_api`;
- production Wi-Fi fail-closed behavior with no demo fallback;
- removal of the one-shot self-mutating Parent GitHub workflow;
- removal of the obsolete root toddler voice batch producer.

No source SHA is hard-coded here. Freeze the exact `origin/main` candidate at execution time.

---

## 1. Operator rules

- Do not run GitHub Actions.
- Do not create ZIP bundles unless explicitly requested.
- Do not use filesystem-root `/tmp`; use `./tmp/...` inside the repository.
- Do not reset, stash, delete, or overwrite unknown owner work.
- Stop on source-integrity, safety, or evidence-validity failure.
- A failed test is evidence. Preserve it; do not patch tests or implementation during the acceptance run.
- If `origin/main` advances after the candidate is frozen, finish source/Simulator evidence only if it remains useful, but do **not** deploy the stale candidate to the Acer as exact-current evidence.

---

## 2. Freeze the candidate

From the repository root:

```bash
set -euo pipefail

git status --short
git fetch origin
SOURCE_SHA="$(git rev-parse origin/main)"
HEAD_SHA="$(git rev-parse HEAD)"

test "$HEAD_SHA" = "$SOURCE_SHA"
test -z "$(git status --short)"

EVIDENCE_DIR="./tmp/recent-cleanup-acceptance-$(date +%Y%m%d_%H%M%S)-${SOURCE_SHA:0:8}"
mkdir -p "$EVIDENCE_DIR"
printf '%s\n' "$SOURCE_SHA" | tee "$EVIDENCE_DIR/source_sha.txt"
```

**Expected:** clean tree; `HEAD == origin/main`; evidence directory exists.

**STOP** if either SHA differs or the working tree is not clean. Report the exact state. Do not repair it inside this gate.

---

## 3. Focused source contracts

Run exactly:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_pygame_audio.py' -v \
  2>&1 | tee "$EVIDENCE_DIR/test_pygame_audio.log"

PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_parent_production_api.py' -v \
  2>&1 | tee "$EVIDENCE_DIR/test_parent_production_api.log"

PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_parent_api.py' -v \
  2>&1 | tee "$EVIDENCE_DIR/test_parent_api.log"
```

Required behavior:

- mixer helper uses the actual active mixer frequency/channel count and refuses unsupported PCM formats;
- installed Parent defaults to real IWD rather than sample/demo Wi-Fi;
- an unavailable backend yields no fake network list and no simulated connection success;
- direct IWD that is detectable but not writable by the Parent process is not advertised as `network.manage`;
- package/update/settings capabilities remain present through the production composition;
- the shipped systemd unit points to `greia_parent.production_api`.

Any focused-test failure is **REJECTED source evidence**. Stop and return the logs.

---

## 4. Architecture audits and full verification

```bash
PYTHONPATH=src python3 tools/audit_activity_backend_independence.py activities \
  2>&1 | tee "$EVIDENCE_DIR/backend_audit.log"

PYTHONPATH=src python3 tools/audit_activity_system_chrome_ownership.py --strict \
  2>&1 | tee "$EVIDENCE_DIR/system_chrome_audit.log"

make verify 2>&1 | tee "$EVIDENCE_DIR/make_verify.log"
```

Required:

- backend-independence blockers: `0`;
- system-chrome blockers: `0`;
- `make verify`: exit `0`.

Record the actual test count reported by `make verify`; do not copy a historical number.

---

## 5. Real-Shell Simulator toddler matrix

Use the current Simulator route and the semantic Activity launch procedure from:

```text
docs/testing/2026-09-02_R7_FINAL_EVIDENCE_GAP_CLOSURE.md
```

Run each current built-in Activity through the real child Shell composition:

```text
org.greia.il-giardino-dei-numeri
org.greia.alfabeto-leo
org.greia.bosco-numeri
```

For **each** Activity record:

1. first Activity frame appears;
2. Greia-owned Home is visible;
3. Home returns through Greia lifecycle;
4. no duplicate/Activity-owned Home is visible;
5. pointer selection remains correct under at least one non-native/scaled Simulator geometry;
6. no traceback, SDL/Pygame warning that changes behavior, or stuck process is observed.

For Bosco, exercise both Italian and English presentation and verify:

- the mode-switch label comes from the selected locale;
- the guess prompt contains the selected number in the selected locale;
- English does not display the old Italian-only progress word `di`.

If Simulator audio is genuinely available, also listen to at least one generated feedback cue per Activity and record whether pitch/duration/channel playback sounds normal. If no usable audio output exists, record `NOT_RUN`; do not call it PASS.

The Simulator lane is semantic/developer evidence only. It does not prove production trusted-chrome/backend isolation.

---

## 6. Reconfirm exact current source before Acer

Only proceed if source and Simulator lanes are green.

```bash
git status --short
git fetch origin
CURRENT_HEAD="$(git rev-parse HEAD)"
CURRENT_ORIGIN="$(git rev-parse origin/main)"
printf 'SOURCE_SHA=%s\nHEAD=%s\nORIGIN_MAIN=%s\n' \
  "$SOURCE_SHA" "$CURRENT_HEAD" "$CURRENT_ORIGIN" \
  | tee "$EVIDENCE_DIR/pre_acer_sha.txt"

test "$CURRENT_HEAD" = "$SOURCE_SHA"
test "$CURRENT_ORIGIN" = "$SOURCE_SHA"
test -z "$(git status --short)"
```

**STOP** if `main` advanced, the working tree changed, or the local SHA differs. Do not deploy a stale candidate as exact-current evidence.

Use canonical repository deployment tooling. Do not locally patch timeout constants or source after this check.

---

## 7. Acer focused physical observations

This lane supplements, but does not replace, the full R7.2/R7.3 physical procedure.

### 7.1 Toddler Activities

Launch all three toddler Activities from the real child Shell. For each, record raw launch/READY or first-visible-frame latency if the current tooling exposes it:

```text
Giardino:
Alfabeto:
Bosco:
```

Do **not** invent a numerical pass threshold for this cleanup gate. Record the values and classify whether a material regression is observable on the Acer floor. Pay particular attention to Alfabeto because its 26 marimba cues are now prebuilt outside the interaction hot path.

Physically verify:

- pointer selection is correct at the actual device display geometry;
- Greia-owned Home remains visible and responsive;
- Home returns to a responsive Shell;
- no child-visible Linux surface appears;
- Activities do not require raw input or direct DRM authority;
- generated SFX are not obviously half-speed, double-speed, pitch-shifted, or channel-garbled;
- normal prerecorded voice cues remain intelligible and are not replaced by runtime TTS.

If startup cost is materially worse, preserve the measurement and report it. Do not move synthesis back into the click hot path during the gate.

### 7.2 Parent production capability

Inspect the actual installed Parent service and `/api/v1` capability response.

Expected architectural behavior on the current unprivileged direct-IWD composition:

- service entrypoint is `greia_parent.production_api`;
- the service remains the sandboxed `greiapanel` process; do not broaden it to root or generic filesystem authority;
- no demo/sample Wi-Fi is exposed when real management is unavailable;
- `network.manage` may legitimately be `false` when direct IWD state is not writable by the service;
- a future usable mutation path belongs behind the narrow typed privileged broker described in `docs/architecture/GREIA_PARENT_MANAGEMENT.md`.

Record the actual capability value. `network.manage=false` under that boundary is **fail-closed behavior**, not a reason to weaken the sandbox.

---

## 8. Return evidence

Return the evidence directory and this exact summary block:

```text
GREIA_RECENT_CLEANUP_ACCEPTANCE
source_sha:
origin_main_at_start:
origin_main_before_acer:
main_advanced_during_gate:
working_tree_clean_before_test:
working_tree_clean_after_test:
pygame_audio_tests:
parent_production_tests:
parent_api_tests:
backend_audit:
chrome_audit:
make_verify:
make_verify_test_count:
giardino_simulator:
alfabeto_simulator:
bosco_simulator:
trusted_home_all_three:
pointer_mapping_scaled_simulator:
bosco_it_en_localization:
local_audio_listening:
acer_reachable:
acer_exact_source:
giardino_ready_latency:
alfabeto_ready_latency:
bosco_ready_latency:
material_startup_regression:
audio_pitch_duration_physical:
parent_network_manage_payload:
parent_service_sandbox_unchanged:
child_visible_linux:
notes:
evidence_dir:
```

Verdict vocabulary:

- **ACCEPTED** — all required available lanes passed for the exact candidate;
- **REJECTED** — a source/product/security/performance invariant was proven false;
- **INCOMPLETE** — a required lane was genuinely unavailable or exact-current source could not be preserved.

On any failure, preserve the first failing evidence and stop destructive troubleshooting. A later fix requires a new source SHA and a new acceptance run.
