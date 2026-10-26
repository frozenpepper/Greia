# Single-stage diagnostic — source-reuse gate failure

Date: 2026-10-26 · Status: **SOURCE-REUSE GATE FAILED; one-stage boot NOT RUN;
Session 04 OPEN**

Work order: `docs/testing/2026-10-26_AB_SINGLE_STAGE_DIAGNOSTIC.md`
Source at the gate stop:
`abd9f5045ba65d07edb567fa47a66d1dffa7d8b7` (clean `main`)
Current `main` during push reconciliation (at last check):
`ef8eb3415` (broader localization source; the workstream was still advancing; see §5)
Evidence:
`/var/tmp/greia-ab-stage-preflight-abd9f5045ba65d07edb567fa47a66d1dffa7d8b7-20261026T171039Z/`

## 1. Test gate now passes

With the documented parent `PYTHONUNBUFFERED=1`, the work order's source
preflight passed:

```text
Ran 80 tests in 2.248s
OK
```

The previous closed-stderr test-fixture failure is fixed. No VM boot occurred.

## 2. Reuse allowlist stopped the run

`git pull --ff-only` inside the work order advanced main with two new
**production source** files:

- `src/greia_platform/languages/en/manifest.json` (`265acd873`)
- `src/greia_platform/languages/it/manifest.json` (`abd9f5045`)

These paths are outside the work order's allowlist
(`tools/x8_qemu/`, `tests/`, `docs/`, `skills/`, `HANDOVER.md`, `AGENTS.md`,
`CONTRIBUTING.md`, `README.md`, `SETUP.md`, `.github/CODEOWNERS`). The
work order says any other changed path may affect the image: stop and inspect,
do not rebuild blindly.

The files are selector metadata (`locale`, `name`, `native_name`, `flag`,
`order`, `direction`) under the shipped `src/` tree. They are not in the
accepted-A image or the next bundle, both produced from `1275e0be1`. Whether
that makes them irrelevant to the updater-stage diagnostic is a review
decision; the strict reuse gate does not authorize assuming it.

## 3. Read-only input facts

- Accepted-A SHA-256 `83d693d9…`: **OK**.
- Next-bundle SHA-256 `3ae9cdea…`: **OK**.
- Input holder check: `fuser` status 1 with **empty output** (offline).
- Owned loops under the old evidence root: **0**.

No one-stage `RUN_ROOT`, command log, `result.json` or collector output was
created. No install, arm, B boot, update replay or fault matrix ran. Inputs and
permissions were preserved.

## 4. Next decision

Before the single stage boot can be authorized, the owner/reviewer must either:

1. explicitly record that the new language-selector manifests do not affect
   the A/B updater-stage target and amend the reuse exception; or
2. rebuild the next bundle/image from current `main` so they are part of the
   tested release.

Do not run the stage diagnostic until that decision is recorded. Do not treat
this report as a stage result or as authorization to rebuild automatically.
Healthy B remains unproven; Session 04 remains OPEN.

## 5. Concurrent main advancement (post-stop)

The first push was rejected because `origin/main` advanced during this work.
The local evidence commit was rebased onto `ef8eb3415`, which includes the
broader localization implementation. The source diff from `1275e0be1` now
contains additional non-allowlisted production source, including:

- `src/greia_installer/entrypoint.py`
- `src/greia_installer/i18n.py`
- `src/greia_launcher/catalogue_view.py`
- `src/greia_launcher/launch_feedback.py`
- `src/greia_launcher/panel_localization.py`
- `src/greia_launcher/parent_panel.py`
- `src/greia_platform/languages/{en,es,fr,it}/manifest.json`
- `src/greia_platform/system_language.py`
- `tools/audit_greia_language_coverage.py` (outside the
  `tools/x8_qemu/`-only allowlist)

These are shipped installer/launcher/platform inputs, not harness, tests,
docs or root collaboration documents. The source-reuse gate therefore remains
failed and is broader than the initial two-manifest stop. The write-only
80-test preflight passed at `abd9f5045`; it was not rerun at `ef8eb3415`
because the source gate already blocks the stage boot. No VM, install, arm,
B boot, update replay or collector ran. The same review/rebuild decision in §4
is required before any reuse.

## 6. 2026-10-27 review decision

The next-action decision requested above is now explicitly recorded in
[`2026-10-27_UPDATE_AGENT_HANDOFF.md`](../testing/2026-10-27_UPDATE_AGENT_HANDOFF.md).
At reviewed host source `78f07861c0ddfad6ed51fb2e1c564d3f95e70115`, the 19 changed
production source paths since `1275e0be1` are localization/UI. The updater/slot/
boot owners and image composition inputs are unchanged. The existing verified
old payloads may be used for one **old-release** stage diagnostic with current
host control/error collection. They do not test new localization or establish
current-release acceptance. The new handoff supplies a reviewed-snapshot source
gate, records host and guest versions separately, and does not authorize builds.

Current source verification at the reviewed SHA: 80 update-preflight tests PASS
in 14.121 s; 59 language tests PASS and EN/IT/ES/FR audits each zero issues.
No Linux boot or artifact inspection was executed on this Mac. The decision
assumes fresh hash/holder/loop checks on the Linux host before the one boot.

Cross-seam source review also found that current Python/combined packages omit
and reject the new language JSON while the new registry requires it. Do not
send that code to pre-manifest bases as a test; the handoff records the package-
data/compatibility correction needed first. This is separate from the old-
release full-system diagnostic, and no production fix is claimed here.
