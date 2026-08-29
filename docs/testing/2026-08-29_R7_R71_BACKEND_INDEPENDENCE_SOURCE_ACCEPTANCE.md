# R7.1 Activity Backend-Independence Source Acceptance

**Status:** required local/source acceptance for the 2026-08-29 R7.1 enforcement tranche  
**Scope:** source validation only; does not close R7 display/session/chrome/input or physical-performance gates  
**Authority:** subordinate to the active architecture-remediation plan and `docs/reviews/2026-08-29_R7_ACTIVITY_BACKEND_INDEPENDENCE_AND_DISPLAY_SESSION_REVIEW.md`

## Purpose

Verify that the new Activity backend-independence policy:

1. rejects direct Activity ownership/probing of X11, Wayland, DRM/KMS and raw host input;
2. does not reject ordinary SDL/Pygame rendering or established Greia performance techniques;
3. cannot be trivially bypassed through ordinary Python import aliases;
4. is active in both one-Activity and project-wide validation;
5. inventories existing cooperative system-chrome/controller debt separately from new hard blockers;
6. introduces no child-runtime/render-loop work.

This protocol does **not** authorize claims about Xorg/Wayland runtime performance, trusted Home enforcement, controller brokerage, Acer hardware or Pi hardware.

## Preconditions

Work from a clean, current checkout of canonical `main`.

Record:

```bash
git status --short
git rev-parse HEAD
python3 --version
```

If local uncommitted changes exist that are unrelated to this acceptance, stop and preserve/reconcile them before testing. Do not delete or reset owner work.

Do not use GitHub-hosted Actions for this protocol.

## A. Focused policy tests

Run:

```bash
python3 -m unittest tests.test_activity_backend_policy -v
```

Required result:

```text
exit code 0
all tests PASS
```

The suite must prove at least:

- normal `pygame.display.set_mode()`, `pygame.display.flip()`, Surfaces and event polling remain allowed;
- backend imports are blocked;
- backend environment access is blocked;
- import aliases do not bypass environment/command policy;
- raw `/dev/input`, `/dev/dri`, `/sys/class/input` and `/sys/class/drm` paths are blocked;
- Xorg/Wayland/DRM/compositor host commands are blocked when actually executed from Activity source;
- X11/Wayland/DRM native-library probes are blocked;
- `pygame.display.get_driver()` / `get_wm_info()` backend introspection is blocked;
- current Activity-side system chrome and direct `pygame.joystick` use are reported as R7 migration debt rather than silently reclassified as complete.

Stop on any failure. Return the exact traceback/output; do not weaken the policy to make a failing fixture pass.

## B. Full first-party catalogue audit

Run:

```bash
python3 tools/audit_activity_backend_independence.py
```

Required result for the hard R7.1 gate:

```text
exit code 0
SUMMARY ... blockers=0 ...
```

`MIGRATION` findings are expected while R7.3/R7.4/R7.5 remain open. They are evidence to preserve, not failures to hide. Copy the complete output into the return report so the next migration wave has an exact Activity/file/line inventory.

Do **not** use `--strict-migration` as the R7.1 pass/fail gate. That mode exists for later R7 closure, after trusted chrome and input migration are implemented.

If any `BLOCKER` appears:

1. stop;
2. classify whether it is a real Activity/backend dependency or a validator false positive;
3. return the exact Activity path, line, code and surrounding source;
4. do not automatically exempt it.

## C. Canonical project validation

Run:

```bash
python3 tools/validate_project.py
```

Required result:

```text
exit code 0
PASS ...
```

This proves project validation now includes the hard backend-independence gate in addition to the existing runtime/package checks.

Then run one representative bundled Activity through the standalone validator, preferably mandatory Writing:

```bash
python3 tools/validate_activity.py activities/writing
```

Required result:

```text
exit code 0
PASS org.greia.writing ...
sha256 ...
```

If Writing is temporarily unavailable for an unrelated concurrent reason, use Painting and report why; do not silently switch packages.

## D. Full provider-free source gate

Run:

```bash
make verify
```

Required result:

```text
exit code 0
all existing repository/source gates PASS
```

Record the final test count/output exactly. Do not reuse a previous `make verify` result from an older SHA.

## E. Performance-boundary review

This tranche must not alter Activity render/event hot paths. Confirm from the diff that:

- no Activity frame loop was modified;
- no pixel/framebuffer proxy was added;
- no pointer/text IPC path was added;
- no new child-runtime background daemon/poller was added;
- policy scanning occurs only during validation/audit, not once per rendered frame or input event.

No physical performance benchmark is required for this source-only tranche because no runtime presentation path is intentionally changed. Physical baselines become mandatory before R7.3/R7.6 changes to trusted chrome/backend presentation.

## F. Return report

Return one compact report containing:

```text
R7_R71_BACKEND_INDEPENDENCE_SOURCE_ACCEPTANCE
HEAD: <sha>
working_tree_clean_before: PASS/FAIL
python: <version>
focused_policy_tests: PASS/FAIL (<count>)
catalogue_audit: PASS/FAIL
catalogue_blockers: <count>
catalogue_migration_findings: <count>
migration_activities: <count>
validate_project: PASS/FAIL
validate_activity_writing: PASS/FAIL
make_verify: PASS/FAIL (<test count if reported>)
runtime_hot_path_changed_by_this_tranche: NO/YES
```

Then include the complete catalogue audit output under a clearly marked section.

## Stop / next-step rule

If all hard gates pass, R7.1 source enforcement may be marked implemented/source-accepted, but **R7 remains open**.

The next implementation work is:

1. consume the exact migration inventory;
2. harden the existing display-session seam and isolate generic-launcher X11 mechanics behind Legacy-X collaborators;
3. establish representative physical performance baselines before runtime presentation/chrome migration;
4. implement real trusted Home/Back for the current Xorg compatibility session;
5. migrate first-party Activities by shared pattern;
6. only then prototype/compare Wayland behind the same contract.
