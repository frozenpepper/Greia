# Greia Encyclopedia v0.1 — LOCAL AGENT PROMPT: Source Gate

## What you are doing

You are performing **only the deterministic pre-Simulator source acceptance gate** for the Greia Encyclopedia v0.1.

Do **not** edit or repair source during this run.
Do **not** generate voices.
Do **not** run the Simulator yet.
Do **not** commit, push, reset, clean, or discard anything.

The owner wants the first real failure, if any, returned intact for review.

---

## Repository

Use the owner's existing Greia checkout.

From the repository root, first read:

```text
AGENTS.md
HANDOVER.md
encyclopedia/HANDOVER.md
docs/testing/GREIA_ENCYCLOPEDIA_V01_CONSOLIDATED_ACCEPTANCE.md
```

The detailed consolidated acceptance document is background authority. For **this run**, execute only the source-gate procedure below.

---

## Step 1 — inspect starting state

Run:

```bash
git branch --show-current
git rev-parse HEAD
git status --short
```

Required branch:

```text
main
```

If the branch is not `main`, STOP and report it.

Do **not** clean a dirty working tree.

Legitimate pre-existing Encyclopedia recording state may include:

```text
encyclopedia/VOICE_RECORDING_REQUESTS.md
encyclopedia/pages/**/assets/audio/**
tmp/encyclopedia-v01-acceptance/**
```

If unrelated project source or Encyclopedia runtime source is already dirty, STOP and report the exact paths. Do not fix them.

---

## Step 2 — inspect the gate plan

Run exactly:

```bash
python3 tools/encyclopedia_v01_source_gate.py --plan-only
```

Expected high-level sequence:

```text
1. branch/worktree preflight
2. sync voice ledger
3. sync --check + 378-row invariant
4. focused provider-free tests
5. make verify
6. OWNER_ACCEPTED audio integration check/integration if required
7. post-audio focused tests if runtime resources changed
8. git diff --check + strict worktree postflight + summary
9. STOP: Simulator acceptance remains pending
```

If the tool itself fails to start, STOP and report the complete error.

---

## Step 3 — execute the source gate ONCE

Run exactly:

```bash
python3 tools/encyclopedia_v01_source_gate.py
```

Do not run it a second time if it fails.
Do not patch source during this run.
Do not manually change voice-ledger statuses.
Do not delete staging audio or receipts.

The tool is allowed to perform only its documented deterministic mutations, principally synchronizing the voice ledger and packaging audio that was already explicitly marked `OWNER_ACCEPTED`.

It must never generate speech or mark a recording owner-accepted.

---

## If the source gate FAILS

STOP immediately.

Do not repair anything.
Do not rerun.

Find the evidence directory printed by the tool. It should be under:

```text
./tmp/encyclopedia-v01-acceptance/<timestamp>/
```

Return to the owner:

```text
1. exact starting commit SHA
2. exact failing step
3. exact process exit code
4. complete terminal output around the failure
5. contents of FIRST_FAILURE.txt
6. git-status-before.txt
7. git-status-at-failure.txt
8. the log file for the failed step
9. voice-ledger.diff if it exists
10. the exact evidence directory path
```

Also run **only this non-mutating command after the failure** and include its output:

```bash
git status --short
```

Do not do anything else.

---

## If the source gate PASSES

The terminal must explicitly report:

```text
SOURCE GATE PASS — Simulator acceptance is still pending.
```

Do not start the Simulator yourself in this run.

Return to the owner:

```text
1. starting commit SHA
2. final `git status --short`
3. exact evidence directory path
4. source-gate-summary.json
5. voice-row-count.json
6. focused-tests.txt
7. make-verify.txt
8. voice-assets-check-before.txt
9. voice-assets-integrate.txt and voice-assets-check-after.txt if integration ran
10. post-audio-focused-tests.txt if it ran
11. git-diff-check.txt
12. git-status-after.txt
```

Report the final voice status counts exactly as recorded in `voice-row-count.json`.

Do **not** call the Encyclopedia fully accepted. A successful result means only:

```text
SOURCE-VERIFIED / SIMULATOR-UNVERIFIED
```

The owner/primary agent will review this evidence and give a separate prompt for the full Simulator traversal.

---

## Prohibited actions

During this task you MUST NOT:

- modify Python/source code to fix a failure;
- change factual narration text;
- change `REQUESTED`, `RECORDED_UNREVIEWED`, `REJECTED_REDO`, or other recorder statuses by hand;
- mark anything `OWNER_ACCEPTED`;
- generate narration;
- invoke Chatterbox, native speech generation, Whisper generation workflows, or any LLM/provider;
- delete `.ogg` files or `.receipt.json` files;
- run `git reset`, `git clean`, `git checkout --`, or equivalent destructive commands;
- commit or push;
- run GitHub Actions;
- run the Greia Simulator;
- continue after the first real failure.

The purpose of this task is to obtain trustworthy source-gate evidence, not to make the gate green at any cost.
