# Greia Encyclopedia v0.1 — LOCAL AGENT NEXT TASK

This is the single rolling instruction for the **next** owner-machine task.

## Current state

The previous source-gate run reached `focused-tests` and executed the real test suite successfully enough to expose two genuine pre-existing drifts:

1. `encyclopedia/research/space/saturn.md` was the only factual authority missing the required `## Scope guardrails` section.
2. `tests/test_activity_contract.py` expected `org.greia.piccola_serra`, while the authoritative Activity manifest uses `org.greia.piccola-serra`.

Both have now been corrected on `origin/main` by the primary agent.

Already proven in earlier runs:

- voice ledger is canonical and idempotent;
- exactly **378** voice-request rows exist;
- all 378 rows are currently `REQUESTED`;
- voice synchronization generates **zero** audio files;
- the source-gate unittest invocation now actually executes the repository tests;
- the previous failed run left the worktree clean.

This task generates **ZERO voice files**.
Do **not** start the Simulator in this task.

---

## Step 1 — update to current main

From the existing owner-controlled Greia checkout:

```bash
git branch --show-current
git status --short
git fetch origin
git pull --ff-only origin main
git rev-parse HEAD
git status --short
```

Required:

```text
branch = main
worktree = clean
```

If unrelated source is dirty or the pull cannot fast-forward, STOP and report it. Do not reset/clean/discard anything.

---

## Step 2 — run the Encyclopedia source gate exactly ONCE

Run exactly:

```bash
python3 tools/encyclopedia_v01_source_gate.py
```

Do not run it a second time if it fails.
Do not repair source during the gate.
Do not generate narration.
Do not invoke the Greia Voice Engine, Chatterbox, native TTS, Whisper generation, or any LLM/provider.
Do not start the Simulator.

---

## If the source gate FAILS

STOP immediately.

Return:

1. exact starting SHA;
2. exact failing step;
3. exact exit code;
4. complete terminal output around the failure;
5. `FIRST_FAILURE.txt`;
6. failed-step log;
7. `git-status-before.txt`;
8. `git-status-at-failure.txt`;
9. `voice-row-count.json` if present;
10. exact evidence-directory path;
11. final `git status --short`.

Do not fix or rerun anything until the primary agent reviews that first failure.

---

## If the source gate PASSES

The terminal must explicitly report:

```text
SOURCE GATE PASS — Simulator acceptance is still pending.
```

Return:

1. exact starting/current SHA;
2. `source-gate-summary.json`;
3. `voice-row-count.json`;
4. `focused-tests.txt`;
5. `make-verify.txt`;
6. `voice-assets-check-before.txt`;
7. integration/post-audio logs if they exist;
8. `git-diff-check.txt`;
9. `git-status-after.txt`;
10. exact evidence-directory path;
11. final `git status --short`.

A PASS means only:

```text
SOURCE-VERIFIED / SIMULATOR-UNVERIFIED
```

Do **not** start the Simulator yet. Stop and return the source-gate evidence to the owner/primary agent.
