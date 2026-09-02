# Greia — Unified R7 + Parent Controls + Launcher Spoken-Label Promotion Gate

**Date:** 2026-09-02  
**Provisional source baseline:** `cdf5f30e1c15a7920a58b163c9e3e3a9a466494f`  
**Historical frozen R7 Acer candidate:** `1edb22cec7709aafe3f08519fabf69cb93cb8083`  
**Parent App pin inherited by the provisional baseline:** `7db9a94…`  
**Status on creation:** source/headless evidence green; human spoken-audio review, full GUI Simulator, current-candidate Acer evidence, exact R7.2/R7.3 process/crash evidence and Parent real-expiry evidence remain open.

This protocol is the continuation authority for **future execution** of the still-open physical/interactive gates. It deliberately does not rewrite or erase the earlier exact-`1edb22ce` evidence. That evidence remains useful historical/supporting evidence, but `1edb22ce` is no longer a valid final current-head candidate because runtime/assets/source/tool changes exist after it.

The old procedure remains the detailed authority for the R7 lifecycle mechanics:

```text
docs/testing/2026-09-02_R7_FINAL_EVIDENCE_GAP_CLOSURE.md
```

Use its §§5–11 for process proof, exact 1024×600 geometry, normal 20/20, hostile 10/10, abrupt crash, Parent usage-limit lifecycle and final logs. **Do not execute or apply its old-candidate preflight/verdict binding to `1edb22ce`.** This document replaces that binding with the final candidate selected below.

Launcher spoken-label semantic requirements remain in:

```text
docs/agents/2026-09-01_LAUNCHER_SPOKEN_LABELS_LOCAL_COMPLETION.md
```

In particular, human review is mandatory (§20), real GUI Simulator acceptance is mandatory (§26), and physical Acer acceptance/performance is separate (§28).

---

## 0. Non-negotiable rules

1. **Do not ask the owner to repeat the already accepted Writing/Painting physical keyboard/touchpad/drawing-feel checks.** Those remain accepted historical physical evidence.
2. **Do not finish the old `1edb22ce` machine gate first and then deploy spoken-label source.** That would duplicate the same Shell/lifecycle acceptance on a superseded runtime.
3. `cdf5f30e` is a **provisional source baseline**, not automatically the final Acer candidate. All 106 spoken-label candidates still have `human_review=PENDING` in the reported review workspace. A known verifier warning exists for `activities/workshop_settings/en/activity-title.wav` (`"My grayer. My grayer."`). Human review must happen before candidate freeze so rejected audio can be corrected without forcing a second hardware run.
4. Whisper/receipt verification never substitutes for human listening. `PASS`, `WARN` and `NOT_APPLICABLE` are machine evidence only.
5. Once `FINAL_RUNTIME_SHA` is frozen in §4, make **no runtime/source/build/tool changes** until the physical gate is complete. Documentation/evidence-only commits may occur, but must be clearly separated from the runtime candidate.
6. Screen coordinates are navigation, not launch evidence. Every counted Activity launch in the R7 lanes must satisfy the semantic process proof from the old gate §5.
7. Never edit the usage ledger to manufacture acceptance. Real Activity runtime must increment `profile_used_seconds` through `UsageLimitedActivitySupervisor`.
8. Never expose Parent credentials or pairing material in committed evidence.
9. Stop on the first real invariant failure. Do not “repair the evidence” by retrying until screenshots look green.
10. No GitHub-hosted Actions.

---

## 1. Repository preflight

Run from the normal Greia checkout:

```bash
set -euo pipefail

CANDIDATE_BASE=cdf5f30e1c15a7920a58b163c9e3e3a9a466494f
PY=/opt/homebrew/bin/python3.12
[ -x "$PY" ] || PY=python3

 git fetch origin
 git switch main
 git pull --ff-only

HEAD_SHA="$(git rev-parse HEAD)"
ORIGIN_SHA="$(git rev-parse origin/main)"
printf 'HEAD=%s\nORIGIN_MAIN=%s\n' "$HEAD_SHA" "$ORIGIN_SHA"
test "$HEAD_SHA" = "$ORIGIN_SHA"
git status --porcelain
```

Required before proceeding:

```text
HEAD == origin/main
working tree clean
cdf5f30e is an ancestor of HEAD
```

Then:

```bash
git merge-base --is-ancestor "$CANDIDATE_BASE" HEAD
mkdir -p tmp/r7-spoken-unified-preflight
git diff --name-only "$CANDIDATE_BASE"..HEAD \
  | tee tmp/r7-spoken-unified-preflight/delta-from-cdf5.txt
```

At the time this protocol is introduced, later changes are expected to be documentation-only. If the delta contains any path outside documentation/evidence coordination (`docs/**`, `HANDOVER.md`, `AGENTS.md`), **STOP** and return the exact delta. A new source review is required before continuing.

Do not rewrite current source merely to make it resemble the handover. The source baseline already passed:

```text
focused spoken-label tests: 20 passed
ruff: clean
spoken-label audit: 34 built-ins / 68 Activity locale clips / 38 system clips complete
make verify: 1561 PASS
IT/EN headless semantic matrix: PASS
```

Those source results are inherited unless a later non-doc delta exists.

---

## 2. Human audio acceptance comes before hardware candidate freeze

Review workspace expected:

```text
tmp/voice-review/launcher-spoken-labels/
```

Expected pending inventory:

```text
system IT:      19
system EN:      19
Activities IT:  34
Activities EN:  34
TOTAL:         106
```

First prove the workspace is present and counts are coherent:

```bash
ROOT=tmp/voice-review/launcher-spoken-labels
find "$ROOT" -name '*.wav.receipt.json' -print | sort > /tmp/greia-spoken-receipts.txt
wc -l /tmp/greia-spoken-receipts.txt

grep -r '"human_review"' "$ROOT" --include='*.json' | grep 'PENDING' | wc -l
grep -r '"human_review"' "$ROOT" --include='*.json' | grep 'ACCEPTED' | wc -l
```

If the receipt workspace is missing, incomplete, or no longer corresponds to runtime assets, **do not regenerate the catalogue wholesale**. Stop and report the missing paths/counts so review provenance can be recovered first.

### 2.1 Known-warning clip first

Play this before the bulk review:

```bash
afplay tmp/voice-review/launcher-spoken-labels/activities/workshop_settings/en/activity-title.wav
```

The expected phrase is the exact receipt request text (reported as `My Greia`). The verifier heard `"My grayer. My grayer."`.

Only the human owner decides:

```text
ACCEPTED -> audio clearly says the intended title once and is intelligible
REJECTED -> wrong/repeated wording, clipped/garbled delivery, wrong voice/locale, or poor small-speaker intelligibility
```

Do not infer acceptance from the transcript.

### 2.2 Deterministic resumable human-review helper

The local agent may create this **temporary, uncommitted** helper under `/tmp` to make the 106-item review fast and auditable. It must never choose for the human.

```bash
cat > /tmp/greia_spoken_human_review.py <<'PY'
from __future__ import annotations
import json
from pathlib import Path
import subprocess

ROOT = Path('tmp/voice-review/launcher-spoken-labels')

def order_key(p: Path):
    rel = p.relative_to(ROOT)
    parts = rel.parts
    if parts[0] == 'system':
        locale = parts[1]
        bucket = 0 if locale == 'it' else 1 if locale == 'en' else 2
        return (bucket, *parts)
    locale = parts[-2]
    bucket = 3 if locale == 'it' else 4 if locale == 'en' else 5
    return (bucket, *parts)

receipts = sorted(ROOT.rglob('*.wav.receipt.json'), key=order_key)
print(f'receipts={len(receipts)}')
for i, receipt in enumerate(receipts, 1):
    data = json.loads(receipt.read_text(encoding='utf-8'))
    state = str(data.get('human_review', 'PENDING'))
    if state == 'ACCEPTED':
        continue
    wav = Path(str(receipt).removesuffix('.receipt.json'))
    req = data.get('request') or {}
    ver = data.get('verification') or {}
    print('\n' + '=' * 72)
    print(f'[{i}/{len(receipts)}] {wav}')
    print('expected :', req.get('text'))
    print('speaker  :', req.get('speaker'))
    print('locale   :', req.get('locale'))
    print('verify   :', ver.get('disposition'), repr(ver.get('transcript')))
    while True:
        subprocess.run(['afplay', str(wav)], check=False)
        answer = input('[a]ccept / [r]eject / [p]lay again / [q]uit: ').strip().lower()
        if answer == 'p':
            continue
        if answer == 'q':
            raise SystemExit(0)
        if answer in {'a', 'r'}:
            data['human_review'] = 'ACCEPTED' if answer == 'a' else 'REJECTED'
            receipt.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            break
PY

"$PY" /tmp/greia_spoken_human_review.py
```

This is an owner-listening step. The local agent may operate the review session, but may not answer `a`/`r` on the owner's behalf.

Acceptance checklist for every clip:

```text
exact words
correct locale
correct speaker identity
no invented/repeated sounds
no clipped start/end
no excessive silence/tail
concise launcher delivery
intelligible through ordinary small speakers
```

After a review pass:

```bash
grep -r '"human_review"' "$ROOT" --include='*.json' | grep 'PENDING' | wc -l
grep -r '"human_review"' "$ROOT" --include='*.json' | grep 'REJECTED' | wc -l
grep -r '"human_review"' "$ROOT" --include='*.json' | grep 'ACCEPTED' | wc -l
```

Required before candidate freeze:

```text
PENDING=0
REJECTED=0
ACCEPTED=106
```

### 2.3 Regenerate only rejected clips

If any clip is rejected, do not touch accepted clips and do not invent new wording. Build a retry JSONL directly from each rejected receipt's original semantic request, overriding only the output path back to that candidate WAV:

```bash
"$PY" - <<'PY'
import json
from pathlib import Path
root = Path('tmp/voice-review/launcher-spoken-labels')
out = Path('/tmp/greia-spoken-rejected.jsonl')
rows = []
for receipt in sorted(root.rglob('*.wav.receipt.json')):
    data = json.loads(receipt.read_text(encoding='utf-8'))
    if data.get('human_review') != 'REJECTED':
        continue
    req = dict(data['request'])
    req['output'] = str(Path(str(receipt).removesuffix('.receipt.json')))
    rows.append(json.dumps(req, ensure_ascii=False))
out.write_text('\n'.join(rows) + ('\n' if rows else ''), encoding='utf-8')
print(f'rejected_requests={len(rows)} file={out}')
PY

cat /tmp/greia-spoken-rejected.jsonl
```

Then, only when the file contains rejected requests:

```bash
"$PY" tools/greia_voice.py doctor
"$PY" tools/greia_voice.py batch --input /tmp/greia-spoken-rejected.jsonl \
  | tee /tmp/greia-spoken-regeneration.json
```

The newly generated receipt must return to `human_review=PENDING`; re-run the human review helper for those replacements. Repeat only rejected items until every required clip is human accepted or the tranche is explicitly left incomplete.

Do not run multiple Chatterbox workers.

---

## 3. Promote human-accepted candidate audio into runtime source

Only after all 106 review decisions are `ACCEPTED`, synchronize the accepted temp candidates back into their canonical runtime locations. Copying all accepted candidates is safe: unchanged clips remain byte-identical, while regenerated clips become the only source diffs.

```bash
"$PY" - <<'PY'
from pathlib import Path
import json, shutil
root = Path('tmp/voice-review/launcher-spoken-labels')

receipts = sorted(root.rglob('*.wav.receipt.json'))
if len(receipts) != 106:
    raise SystemExit(f'expected 106 receipts, got {len(receipts)}')
for receipt in receipts:
    data = json.loads(receipt.read_text(encoding='utf-8'))
    if data.get('human_review') != 'ACCEPTED':
        raise SystemExit(f'not human accepted: {receipt}')
    src = Path(str(receipt).removesuffix('.receipt.json'))
    rel = src.relative_to(root)
    if rel.parts[0] == 'system':
        _, locale, name = rel.parts
        dst = Path('assets/audio/system/launcher-labels') / locale / name
    elif rel.parts[0] == 'activities':
        _, activity_root, locale, name = rel.parts
        if name != 'activity-title.wav':
            raise SystemExit(f'unexpected activity candidate name: {src}')
        dst = Path('activities') / activity_root / 'locales' / locale / 'audio' / name
    else:
        raise SystemExit(f'unexpected candidate path: {src}')
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
print('PROMOTED_HUMAN_ACCEPTED=106')
PY
```

Inspect source changes:

```bash
git status --short
git diff --stat
git diff --name-only
```

Allowed runtime changes at this point are only specifically regenerated spoken-label WAV files. Locale JSON/source code/tool changes are not expected merely from audio review. If anything else changed, stop and explain it.

Run the final source gate:

```bash
PYTHONPATH=src "$PY" -m pytest -q \
  tests/test_launcher_spoken_labels.py \
  tests/test_launcher_spoken_labels_controller.py

ruff check \
  src/greia_launcher/spoken_labels.py \
  src/greia_launcher/presentation.py \
  src/greia_launcher/collection_home_presentation.py \
  src/greia_launcher/adaptive_discovery_presentation.py \
  tests/test_launcher_spoken_labels.py \
  tests/test_launcher_spoken_labels_controller.py \
  tools/audit_launcher_spoken_labels.py

"$PY" tools/audit_launcher_spoken_labels.py
make verify
git diff --check
```

Required:

```text
focused tests green
ruff green
spoken-label audit complete 68 Activity locale combinations + 38 Collection labels
make verify green
git diff --check green
```

If runtime WAV files changed, commit and push those exact accepted replacements before physical testing:

```bash
git add assets/audio/system/launcher-labels activities/*/locales/*/audio/activity-title.wav
git diff --cached --name-only
git diff --cached --stat
git commit -m "Launcher spoken labels: human-reviewed audio corrections"
git push origin main
```

Do not commit `tmp/voice-review`.

If there were no runtime byte changes, do not create an empty runtime commit.

---

## 4. Freeze the exact final runtime candidate

Determine the runtime candidate **after** §2–§3:

```text
If every cdf5f30e clip was human accepted and no runtime file changed:
  FINAL_RUNTIME_SHA=cdf5f30e1c15a7920a58b163c9e3e3a9a466494f

If one or more reviewed audio replacements were committed:
  FINAL_RUNTIME_SHA=<the exact commit containing those replacements>
```

Record:

```bash
FINAL_RUNTIME_SHA=<fill exact SHA>
git fetch origin
git merge-base --is-ancestor "$FINAL_RUNTIME_SHA" origin/main

git diff --name-only "$FINAL_RUNTIME_SHA"..origin/main \
  | tee tmp/r7-spoken-unified-preflight/delta-after-final-runtime.txt
```

After freeze, the delta from `FINAL_RUNTIME_SHA` to `origin/main` must be documentation/evidence-only. Any later change under `src/`, `activities/`, `assets/`, `runtime/`, `tools/`, tests that alter executable acceptance authority, build/provisioning code, or dependencies invalidates the freeze and requires review before hardware evidence is combined.

Create an exact detached worktree so the deployment bundle cannot accidentally include later docs/source state:

```bash
STAMP="$(date +%Y%m%d_%H%M%S)"
WT="/tmp/greia-final-runtime-${FINAL_RUNTIME_SHA:0:8}-${STAMP}"
git worktree add --detach "$WT" "$FINAL_RUNTIME_SHA"
git -C "$WT" status --porcelain
test "$(git -C "$WT" rev-parse HEAD)" = "$FINAL_RUNTIME_SHA"
```

Do all Simulator and Acer candidate execution below from this worktree unless a command explicitly targets the normal checkout for evidence/doc updates.

---

## 5. Full real GUI Simulator acceptance on the exact final candidate

Headless IT/EN semantics are already green. This section closes the missing **real `tools/greia_simulator.py` GUI** lane at 1024×600.

Use separate state roots per locale:

```bash
cd "$WT"
"$PY" tools/greia_simulator.py \
  --repo-root "$WT" \
  --state-dir "/tmp/greia-sim-spoken-it-${STAMP}" \
  --language it
```

Then repeat with `--language en` and a distinct state directory.

For **each locale** visibly exercise:

### Collection Home

```text
keyboard across at least 4 Collections -> each semantic change speaks immediately
repeat arrow into a clamped boundary -> no replay
pointer hover under 160 ms -> no speech
stable pointer beyond dwell -> exactly one speech
motion within same target -> no replay
leave then re-enter -> may speak again
rapid pointer A -> B -> C -> only final stable C speaks
```

### Adaptive sub-Collection chooser

Exercise at least 3 sub-Collections with both keyboard and pointer dwell behavior.

### Activity grid

```text
keyboard across at least 5 Activities
boundary clamp -> no replay
pointer hover across at least 5 Activities
rapid sweep -> no queue/backlog
leave/re-enter one Activity -> speaks again
launch an Activity while its title is speaking -> launch begins immediately and speech stops
return Home -> stale previous Activity hit target must not speak over current Home target
```

Capture screenshots for:

```text
IT Collection Home
IT Activity grid
EN Collection Home
EN Activity grid
post-return Home after launch-during-speech
```

No screenshot can prove audio by itself; the operator report must record the actually observed/heard behavior.

If the real GUI cannot be executed, report `SIMULATOR_GUI_FULL=INCOMPLETE`; do not relabel headless evidence as GUI acceptance.

---

## 6. Deploy the exact final runtime candidate once

From the detached worktree:

```bash
cd "$WT"
"$PY" tools/deploy_to_acer.py 2>&1 \
  | tee "/tmp/greia-deploy-${FINAL_RUNTIME_SHA:0:8}.log"
```

The deploy tool's 180 s extraction/chown budget is canonical for the Atom N270. Do not patch the timeout during the frozen candidate run.

Then:

```bash
"$PY" tools/greia_remote.py --password greia wait --timeout 180
"$PY" tools/greia_remote.py --password greia status \
  | tee "/tmp/greia-status-${FINAL_RUNTIME_SHA:0:8}.txt"
```

Verify deployed spoken-label counts:

```text
system it = 19
system en = 19
Activity it = 34
Activity en = 34
```

Use the maintenance shell only for evidence collection, never expose it to the child session.

Hard deployment requirement: the exact runtime-relevant trees deployed from `$WT` (`activities/`, `src/`, `assets/`, `runtime/`) must be byte-equivalent to the candidate. If the agent cannot prove this with a deterministic SHA-256 manifest, the Acer evidence is not bound strongly enough to `FINAL_RUNTIME_SHA` and must remain incomplete.

A suitable deterministic proof is:

```text
local candidate manifest: relative_path + sha256 for every regular file under activities/src/assets/runtime
remote manifest: same from /opt/greia-os
sort both by relative path
exact diff = empty
```

The maintenance shell may be used to collect the remote `sha256sum` manifest. Do not commit credentials.

---

## 7. Run the remaining R7.2/R7.3 + Parent machine closure on this same candidate

Create one evidence root named with the exact candidate:

```bash
cd "$WT"
E="tmp/r7-parent-spoken-unified-$(date +%Y%m%d_%H%M%S)-${FINAL_RUNTIME_SHA:0:8}"
mkdir -p "$E"
```

Reuse these sections from:

```text
docs/testing/2026-09-02_R7_FINAL_EVIDENCE_GAP_CLOSURE.md
```

### Reuse unchanged

```text
§5  semantic Activity process proof / process absence proof
§6  exact 1024×600 geometry
§7  exact normal durability 20/20 pattern
§8  exact hostile first cycle + 10/10
§9  semantic-PID abrupt Shape Garden crash recovery
§10 Parent short-budget lifecycle/accounting/expiry/exhausted relaunch/policy restore
§11 final logs and performance sanity
```

### Candidate override

Every place the old document says the accepted/runtime candidate is `1edb22ce`, substitute **this protocol's exact `FINAL_RUNTIME_SHA`** for the new run. Do not alter the old historical document itself.

### Do not execute from the old document

```text
old §§1–4 exact-1edb22ce preflight/binding
old §12 verdict lines that hard-bind acceptance to 1edb22ce
old §13 final-doc SHA wording
old §14 report field values that assume 1edb22ce
```

The mechanics remain valid; only the candidate authority changes.

Required integrated R7/Parent result on `FINAL_RUNTIME_SHA`:

```text
normal exact 4-pattern durability: 20/20
hostile exact process-proven trusted Home: 10/10
abrupt Shape Garden crash: PASS using one semantically proven greiakid Python PID
post-crash Writing launch/return: PASS
child-visible Linux: NO
stale Activity process after return: 0
launcher/display restart during sequence: 0
Parent finite indicator: shown specifically on Collection Home
real Shape Garden profile_used_seconds increment: > baseline before waiting for expiry
natural expiry: Activity disappears through normal lifecycle
API exhausted=true and remaining=0
Collection Home: Finito per oggi
exhausted relaunch: no Python/bwrap and no Starting… at ~150/500/1250 ms
Parent policy restored exactly
real usage history preserved
```

The previously accepted physical hide/show evidence may be retained if no relevant visibility-policy source changed; do not manufacture a second hide/show run solely for paperwork. If later source changes touched discovery/visibility authority, re-run it.

---

## 8. Formal Acer spoken-label physical/performance matrix on the same candidate

Do this **after** deployment and before any source change.

### 8.1 Baseline CPU/RSS

With Shell idle and no pointer movement for at least 10 s, record the launcher service process tree and resident memory twice several seconds apart. `pidstat` is not required; use `/proc`/`ps` available on the image.

Record at minimum:

```text
launcher PID/process tree
%CPU snapshots while idle
RSS before spoken traversal
```

A transient boot spike is not an idle baseline. If the service just restarted, wait for the normal settled Home first.

### 8.2 Perceived first-touch onset

From a settled Home, focus/hover a label that has not yet been spoken in this launcher process.

Required:

```text
UI remains responsive
no boot-time catalogue preload occurred
speech begins promptly enough to feel attached to focus/hover
no redraw pause
```

Record an uncached dispatch timing if instrumentation is available, but do not claim human-perceived latency from a Python function-call microbenchmark alone.

### 8.3 Pointer dwell and rapid-pointer cancellation

Use the real remote pointer controls:

```bash
R=("$PY" tools/greia_remote.py --password greia)
"${R[@]}" mousemove <x1> <y1>
sleep 0.08
"${R[@]}" mousemove <x2> <y2>
sleep 0.08
"${R[@]}" mousemove <x3> <y3>
```

Choose three distinct visible speakable targets from the current screen. The first two moves must be shorter than the 160 ms dwell; hold the third past dwell.

Required:

```text
A does not begin a queued utterance
B does not begin a queued utterance
only final stable C is spoken
no backlog plays afterward
```

Then hold one target beyond dwell and move repeatedly inside that same tile: it must speak once, not replay on every motion. Leave and re-enter after focus clears: it may speak once again.

### 8.4 Rapid keyboard

Move keyboard selection rapidly across at least four semantic destinations using `greia_remote.py key`.

Required:

```text
selection stays responsive
latest semantic focus wins
no long queue of obsolete labels accumulates
boundary clamp does not replay
```

### 8.5 Launch while speech is active

Start an Activity title utterance and immediately activate that Activity.

Required:

```text
launch begins immediately
spoken-label channel is stopped/cleared
no stale title leaks into Activity runtime
Activity launch process proof is exact
trusted Home return remains normal
```

This also acts as a current-candidate regression check for the presentation/lifecycle seam shared with R7.

### 8.6 48+ unique-label cache/RSS traversal

Exercise at least **48 unique semantic labels** in one launcher process before re-measuring RSS. A practical route is the 34 built-in Activity titles plus at least 14 distinct current Collection/sub-Collection labels.

The agent must keep a TSV of semantic identities actually visited; repeated labels do not count toward 48.

```text
index	semantic_identity	locale	input_mode	heard	comment
```

After 48+ unique labels:

```text
record RSS
repeat the same broad traversal without restarting launcher
record RSS again
```

Required:

```text
no runaway RSS growth
second traversal does not grow proportionally to first traversal
cache remains bounded by the source contract (48 entries; already unit-proven)
no UI slowdown or speech backlog
```

Do not set an invented absolute MiB threshold. Compare against the before/after/second-traversal evidence and flag material unexplained growth.

### 8.7 Small-speaker intelligibility

On the Acer's real speaker, sample at minimum:

```text
2 system IT labels
2 system EN labels
3 Activity IT titles (include a multi-word title)
3 Activity EN titles (include a multi-word title)
the known-warning workshop_settings EN title if it survived human review unchanged
```

Required:

```text
understandable at ordinary child-use volume
no clipped initial consonant
no clipped ending
no doubled/repeated title
no obvious wrong-locale playback
```

This is physical playback evidence, not a replacement for the complete human source-audio review in §2.

---

## 9. Final negative-authority/log check

Capture a final snapshot from the exact candidate worktree:

```bash
"$PY" tools/greia_remote.py --password greia snapshot \
  "$E/final-snapshot" --service all --lines 5000
```

Review for:

```text
Traceback
platform_failure
ready timeout
restore failed
Permission denied
/dev/dri
/dev/input
DRM
KMS
XOpenDisplay
DISPLAY
XAUTHORITY
SDL_VIDEODRIVER
libpng
```

Required:

```text
child-visible Linux: NO
Activity direct DRM required: NO
Activity raw input required: NO
display restore failures: 0
unexplained platform_failure: 0
physical libpng warning: NO
material performance regression: NO
spoken-label queue/backlog failure: NO
```

---

## 10. Verdict rules

### R7.2 = ACCEPTED on `FINAL_RUNTIME_SHA` only if

```text
inherited source/Simulator evidence compatible
owner Writing/Painting physical evidence retained
exact current-candidate normal 20/20 PASS
abrupt crash recovery PASS
process cleanup/focus recovery PASS
no Linux exposure
no direct DRM/raw-input dependency
no material performance regression
```

### R7.3 = ACCEPTED on `FINAL_RUNTIME_SHA` only if

```text
R7.2 accepted on the same candidate
hostile first cycle PASS
hostile 10/10 PASS
forced cleanup/process absence PASS
focus recovery PASS
no stale trusted/hostile surface
no launcher restart
no Linux exposure
```

### Parent usage-limit/visibility tranche = PHYSICALLY ACCEPTED only if

```text
reviewed Parent App/pin evidence retained
physical hide/show PASS retained or validly re-run if authority changed
finite Collection-Home indicator PASS
real Activity usage accounting increment PASS
automatic expiry/return PASS
exhausted API state PASS
Finito per oggi PASS
exhausted relaunch blocked with no Starting flash PASS
policy restored exactly PASS
```

### Launcher spoken-label tranche = COMPLETE only if

```text
human audio acceptance 106/106
machine audit PASS
focused/source gate PASS
full real GUI Simulator IT PASS
full real GUI Simulator EN PASS
Acer rapid pointer PASS
Acer rapid keyboard PASS
Acer launch-during-speech PASS
Acer perceived onset PASS
Acer 48+ traversal + RSS bounded PASS
Acer second traversal stable PASS
Acer small-speaker intelligibility PASS
no material idle CPU regression
```

A real invariant failure is `REJECTED`. A lane that could not actually execute is `INCOMPLETE`.

**Do not start R7.4 until R7.2 and R7.3 are accepted on the final current runtime candidate.**

---

## 11. Stop conditions

Stop immediately and return evidence if any of these occur:

```text
non-doc source changed after candidate freeze
human review leaves any required clip PENDING or REJECTED
spoken-label audit fails
make verify fails
real Simulator Shell crashes or narration leaks into launched Activity
Acer deployment/runtime manifest differs from frozen candidate
expected GREIA_ACTIVITY_ID process proof fails
more than one expected Python child appears
expected greiakid ownership is absent
trusted Home fails to recover Shell
crash target cannot be semantically proven before SIGKILL
profile_used_seconds does not increase while exact Activity is proven running
usage-limit expiry requires manual ledger mutation
exhausted relaunch starts Python/bwrap or shows Starting…
runaway RSS/material idle CPU regression
child-visible Linux appears
```

Do not fix source inside the frozen acceptance run. Stop, report, correct source on main, run source gates, freeze a new exact candidate, then resume from the appropriate gate.

---

## 12. Final report shape

Return exactly enough detail to bind evidence without dumping secrets:

```text
GREIA_UNIFIED_R7_PARENT_SPOKEN_LABEL_PROMOTION_REPORT

SOURCE:
  provisional_source_baseline: cdf5f30e1c15a7920a58b163c9e3e3a9a466494f
  human_review_total:
  human_accepted:
  human_rejected_final:
  human_pending_final:
  workshop_settings_en_verdict:
  regenerated_clips:
  final_runtime_sha:
  head_at_freeze:
  source_delta_after_final_runtime:
  focused_tests:
  spoken_label_audit:
  make_verify:

SIMULATOR_GUI:
  it:
  en:
  rapid_pointer:
  rapid_keyboard:
  launch_during_speech:
  stale_target_return_home:
  screenshots:

ACER_BINDING:
  deployed_final_runtime_sha:
  runtime_manifest_match:
  system_it_count:
  system_en_count:
  activity_it_count:
  activity_en_count:

R7_NORMAL_20:
  result:
  exact_expected_process_proofs:
  returns:
  cleanup:
  focus:
  launcher_restarts:

R7_HOSTILE_10:
  result:
  exact_expected_process_proofs:
  forced_returns:
  cleanup:
  focus:
  launcher_restarts:

R7_CRASH:
  semantic_pid_proof:
  killed_pid:
  shell_recovered:
  cleanup:
  next_writing:
  result:

PARENT_USAGE_LIMIT:
  collection_home_indicator:
  exact_activity_process_proof:
  used_before:
  used_after_checkpoint:
  real_accounting_increment:
  automatic_expiry_return:
  exhausted_api:
  exhausted_home_wording:
  exhausted_relaunch_process_absent:
  starting_flash_seen:
  policy_restored:
  result:

SPOKEN_ACER:
  idle_cpu_baseline:
  rss_before:
  unique_labels_traversed:
  rss_after_48_plus:
  rss_after_second_traversal:
  perceived_onset:
  rapid_pointer:
  rapid_keyboard:
  launch_during_speech:
  small_speaker:

NEGATIVE_AUTHORITY:
  child_visible_linux:
  direct_drm_required:
  raw_input_required:
  display_restore_failure:
  unexplained_platform_failure:
  libpng_warning:
  material_performance_regression:

R72_VERDICT:
R73_VERDICT:
PARENT_USAGE_VISIBILITY_TRANCHE_VERDICT:
SPOKEN_LABEL_TRANCHE_VERDICT:

EVIDENCE_DIR:
FINAL_HEAD:
FINAL_GIT_STATUS:
```

---

## 13. Documentation closure only after execution

After the unified gate finishes, update:

```text
HANDOVER.md
docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md
docs/reviews/2026-09-01_R7_R72_R73_AND_PARENT_CONTROLS_PHYSICAL_ACCEPTANCE.md
```

and the Parent design document if the Parent physical tranche is accepted.

The final documentation must distinguish:

```text
historical physical evidence candidate: 1edb22ce
provisional spoken-label source baseline: cdf5f30e
final runtime/source candidate actually accepted: <FINAL_RUNTIME_SHA>
final later docs-only HEAD: <FINAL_HEAD>
```

Do not rewrite earlier incomplete runs as passes. Preserve the failed/incomplete evidence and append the exact later closure.