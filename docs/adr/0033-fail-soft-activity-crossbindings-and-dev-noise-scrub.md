# ADR 0033 — Fail-soft Activity cross-bindings and boot-time development-noise scrub

Status: **Accepted for staged implementation**

Date: 2026-08-25

Extends: ADR 0017 (platform-owned sessions/events/progression/reward ledger), ADR 0018 (lightweight UI), ADR 0012 (platform architecture constitution)

## Context

A single broken or not-loadable Activity must never take the whole child OS down. Greia already refuses to *load* an Activity that fails registered-input validation: `ActivityRegistry.discover(fail_closed=False)` skips an invalid/corrupt package with a per-package warning and records it as unvalidated. That per-Activity isolation at discovery is correct and is preserved.

The failure observed in practice was not discovery. It was a **downstream cross-binding**: a progression/history policy rule referenced an Activity that had been skipped as not-loaded, and `ProgressionPolicy.load` raised `HistoryPolicyError` for that single dangling reference. That exception propagated through `build_launcher_runtime_services` and aborted `child_shell`, so systemd's `Restart=` produced an endless restart loop with no child-visible degradation. The broken Activity was already an island; the *policy rule referencing it* was not, and it took the launcher down.

A second, compounding factor: during development, host tooling (notably macOS `tar`/`scp`) injects fully regenerable sidecar/cache noise into Activity trees — `._*` AppleDouble files, `.DS_Store`, `__MACOSX/`, `__pycache__/*.pyc`, `Thumbs.db`, editor droppings. The Greia validator correctly rejects many of these (e.g. executable AppleDouble files), so an otherwise healthy Activity failed registration purely because of dev-environment dirt.

## Decision

Two independent, complementary behaviors:

### 1. Fail-soft cross-bindings (progression/history/achievement)

At the boundary where platform policy references Activity identities, distinguish **absence** from **corruption**:

- A policy rule (progression, history, and by extension achievement) that references an Activity **not present in the loaded catalogue** — because it failed validation and was not loaded, or was retired — is **dropped with a warning**, not raised. The launcher boots; progression for every other Activity continues to work; the broken Activity stays an island.
- A policy that is genuinely **corrupt or inconsistent against loaded Activities** remains a hard failure: unparseable TOML, wrong field types, duplicate rule ids, zero reward delta, and a rule that references an **undeclared event on a loaded Activity**. These indicate a policy contract bug, not an unloaded Activity, and must stay loud.

This applies the project's established fail-soft principle to presentation/enrichment authorities: **safety/trust authorities fail closed (permissions, trust, storage, removable media); presentation/enrichment authorities fail soft and independently** (achievement already failed soft to `None`; progression/history now do the same for absent Activities).

### 2. Boot-time development-noise scrub

Before Activities are loaded, a small Greia-owned scrub removes only the curated, fully regenerable dev-noise files from the built-in Activity root:

- macOS: `._*` (AppleDouble), `.DS_Store`, `__MACOSX/`
- Windows: `Thumbs.db`, `desktop.ini`, `~$*` office/editor lock files
- Linux/editor/cache: `*~`, `*.swp`, `*.swx`, `*.tmp`, `.nfs*`, `__pycache__/`, `*.pyc`

Guarantees:

- **Fixed, versioned, curated list.** Every pattern is a review decision, not an open-ended "delete anything suspicious." The list stays in lockstep with the Activity validator's forbidden-file vocabulary.
- **Bounded and non-escaping.** Operates strictly under the Activity root; never follows symlinks out of the tree; a symlinked directory is never descended into; paths resolving outside the root are never touched.
- **Not an Activity repair mechanism.** A genuinely broken or missing file is deliberately left untouched and simply not loaded. The scrub only removes regenerable environment noise; it never hides, rewrites, re-validates, or "fixes" a real defect.
- **Observable.** Removals are logged and counted so a *recurringly* dirty tree is evidence that the push/sync tooling is still wrong, rather than being silently papered over.

The scrub runs in `GreiaShell.__init__` (the single launcher boot composition point used by both the child shell and the presentation fallback) before the `ActivityRegistry` is built, so it cannot be skipped by any entry path that loads Activities. It is deliberately cheap and idempotent on a healthy boot.

## Consequences

- A single not-loadable Activity can no longer brick the child OS: discovery keeps it unloaded, fail-soft cross-bindings keep the launcher up, and `__pycache__`/`*.pyc` scrubbing also ensures Python recompiles from canonical source rather than running stale bytecode.
- Progression/reward behavior for a retired or broken Activity is absent (its rules are dropped) until the Activity is restored — this is honest and observable, not silent.
- Policy-authoring bugs that reference undeclared events on real Activities still surface loudly at build/validation time.
- The scrub is a one-time boot cost, bounded to the Activity root, with no impact on the hot child session path (ADR 0018 low-resource discipline preserved).

## Rejected alternatives

- **Reject the whole install at the device validation gate.** Agents routinely skip a manual validation step; a boot-time behavior that runs at the point of use is self-enforcing and cannot be forgotten. (The junk-scrub choice supersedes a purely gate-based fix for this failure class.)
- **Auto-heal or re-validate broken Activities at runtime.** This would mask genuine defects and conflict with "a broken Activity is treated as broken." Rejected: the scrub never rebuilds a broken package.
- **Run the scrub only from developer tooling / parent-install pipeline.** Parent/agent activity installation is a separate pipeline (owned elsewhere); the device must remain self-healing for regenglerable dirt regardless of how bytes arrive.
- **Make every progression cross-reference fail-soft, including undeclared events.** That would hide genuine policy contract bugs. The decision keeps hard failure for corruption against *loaded* Activities.

## Source closure evidence

- `src/greia_platform/history.py`: `ProgressionPolicy.load` drops rules referencing absent Activities with a `logger.warning` and keeps hard failure for undeclared events / structural policy corruption.
- `src/greia_platform/activity_tree_cleanup.py`: `scrub_activity_tree` removes the curated dev-noise patterns, bounded/non-escaping under the Activity root.
- `src/greia_launcher/main.py`: scrub invoked in `GreiaShell.__init__` before the `ActivityRegistry` is built (covers `child_shell` and `presentation` entry paths).
- Regression tests: `tests/test_activity_tree_cleanup.py` (4) and fail-soft progression tests in `tests/test_history.py`.
- `make verify`: full suite **1,313/1,313 tests PASS**. Physical-device re-validation of a scrubbed int after the earlier `._` incident is outstanding.