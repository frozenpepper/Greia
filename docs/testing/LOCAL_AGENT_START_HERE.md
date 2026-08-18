# Greia — Local Agent Test/Fix Session: START HERE

**Status:** current operator entrypoint  
**Date:** 2026-08-18  
**Branch:** `main`  
**Repository:** `frozenpepper/Greia`

This file exists so the local coding/test agent cannot accidentally run an older partial protocol and miss later owner requirements.

## 1. Read these protocols in this exact order

```text
1. docs/testing/2026-08-18_LOCAL_AGENT_FULL_TEST_AND_FIX_SESSION.md
2. docs/testing/2026-08-18_RESPONSIVE_UI_ACCEPTANCE.md
3. docs/testing/2026-08-18_MY_GREIA_ACCEPTANCE.md
4. HANDOVER.md
```

All three testing documents are mandatory parts of **one** current session. The addenda strengthen/extend the original full-session protocol; they do not replace its installation, SSH, Parent-App, package-install or hardware work.

Before editing also obey the repository read order in `AGENTS.md` / `docs/DOCUMENTATION.md`.

## 2. Agent role

You are not a passive runner. You are expected to:

- inspect failures deeply;
- fix genuine source/test/build/runtime defects;
- add regressions for root causes;
- preserve architecture/security/project policies;
- commit coherent repairs to `main` and push them;
- rerun the smallest affected gate, then the broader gate;
- continue after ordinary failures rather than stopping at the first red test.

Do not make tests green by weakening invariants, deleting checks, encoding the Acer model into core behavior, adding per-resolution UI forks, broadening Activity/Parent authority, or bypassing the typed platform architecture.

Do not use/query/trigger GitHub-hosted Actions without a new explicit owner authorization.

## 3. Current owner/product policies that must survive every repair

- developer/test installs remain SSH-reachable as `greia / greia`; root SSH is disabled;
- no random end-install password/recovery-code UX;
- Parent main password starts `greia / greia` and is Parent-changeable through typed Greia authority;
- optional child passwords are Greia profile credentials, not Linux users;
- Greia UI is automatically responsive: designers/authors maintain **one semantic layout**, not one layout per resolution/device;
- Activity authors can work in a 1024x600 logical reference canvas/world model while Greia automatically maps to the actual Activity viewport;
- Activities may be fluid UI, fixed canvas, world-camera game, or hybrids; choose spatial semantics rather than physical pixels;
- localization is data/semantic-key driven; single-language Activities remain valid; launcher language presentation is platform-owned;
- child-facing language cues use canonical flags when language distinction matters, not initials as the primary cue;
- My Greia is a child-safe visual personalization Activity, not a general system administration panel;
- ordinary Activities may receive read-only resolved child visual context, but never customization write paths merely to match colors/size;
- R7 remains open and current Xorg is provisional compatibility, not the permanent architecture;
- full R10 package lifecycle remains open even though bounded Parent new-install exists.

## 4. Current focused source gate

After synchronizing to the actual current `origin/main`, record the SHA and run:

```bash
set -o pipefail
PYTHONPATH=src python3 -m unittest \
  tests.test_installation_hardware_regressions \
  tests.test_ui_motion_scroll \
  tests.test_responsive_layout \
  tests.test_activity_viewport \
  tests.test_ui_preferences \
  tests.test_theme_snapshot \
  tests.test_activity_theme_access \
  tests.test_activity_ui_preferences \
  tests.test_child_shell_visual_context \
  tests.test_my_greia_settings_contract \
  tests.test_my_greia_runtime \
  tests.test_customization \
  tests.test_activity_ui \
  tests.test_launcher_presentation \
  tests.test_activity_packages \
  tests.test_activity_contract \
  tests.test_parent_api \
  tests.test_localization \
  tests.test_language_context \
  tests.test_language_presentation \
  -v 2>&1 | tee "$SESSION_ROOT/current-ui-platform-focused.log"
```

If a named test module has been legitimately renamed by newer committed source, inspect the current tree and use the current authoritative replacement; do not silently skip the subsystem.

Then run the other subsystem-specific focused gates from the full protocol and finally:

```bash
make verify 2>&1 | tee "$SESSION_ROOT/final-make-verify.log"
```

The current repository contains source/test changes newer than the last recorded executed 663-PASS baseline. **Do not copy that old PASS count onto the current SHA.**

## 5. Parent HTML

Use the exact Parent-App revision pinned by:

```text
runtime/parent-app-client.toml
runtime/parent-app-client.manifest.json
```

Run its `npm test`. If Parent-App source must change, commit/push the Parent-App repository first, then repin Greia to the exact new revision/integrity values.

## 6. Build and hardware

Only after current source gates are green, build a fresh canonical developer/test installer for the actual target profile and follow the destructive-media safety rules in the full protocol.

Physical acceptance must include, at minimum:

- graphical install and first boot;
- no random recovery-code UX;
- developer/test SSH `greia / greia` survives reboot, root rejected;
- Parent HTML live connection and credential/profile management;
- owner-enabled `.greiaactivity` install and hot discovery;
- launcher names/categories/Back/scroll/effects/focus;
- responsive UI matrix plus physical 1024x600 readability/performance;
- My Greia colors/wallpaper/compact-normal-large/avatar with two-profile isolation;
- physical removable-media ejection while My Greia wallpaper browser is open;
- ordinary Activity visual snapshot present while `GREIA_CUSTOMIZATION_DIR` remains absent;
- Writing/Painting and representative game-like Activity behavior under the shared viewport/size contracts.

## 7. Evidence discipline

Every PASS/FAIL must be tied to:

- exact Greia SHA;
- exact Parent-App revision when relevant;
- exact command or physical procedure;
- evidence path/result;
- scope of what it proves.

If source changes after an image was built/tested, the old image evidence belongs to the old SHA. Rebuild/retest the affected physical scope or label it honestly as stale/unproven.

The final result remains the `LOCAL_AGENT_RESULT.md` required by the full protocol. Do not ZIP evidence unless the owner specifically asks for packaging.
