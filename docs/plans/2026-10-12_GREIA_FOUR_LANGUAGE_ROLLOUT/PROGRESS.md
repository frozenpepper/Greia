# Greia Four-Language Rollout — Progress Ledger

**Product authority:** [PLAN.md](./PLAN.md)  
**Local voice execution:** [LOCAL_AGENT_VOICE_PRODUCTION.md](./LOCAL_AGENT_VOICE_PRODUCTION.md)  
**Single local task queue:** `docs/testing/GREIA_LOCAL_AGENT_TASK_QUEUE.md`  
**Evidence status:** GitHub source commits, no newly executed full checkout tests / GUI / recording / physical install in this session.

## 2026-10-12 — Initial owner-authorized implementation: L0 + L1 tooling + L2 installer catalogue staging

### Context

The canonical Greia OS currently advertised **twelve** selectable
languages while its installer `i18n.py` had an English source
vocabulary and an Italian translation map only. The on-device
Parent Settings, Parent API and installer drew from the same overbroad
`SUPPORTED_SYSTEM_LANGUAGES` registry. The browser Parent client
was checked: its language grid reads `snapshot.language.languages`
from the API rather than a duplicated twelve-item hard-code; it does
still have English UI strings independently requiring L3 extraction.
Built-in Activity localizations primarily had `en` and `it` only,
with legacy voice gaps.

The owner requested an honest selector now, a full Spanish/French
integration project, and a separate detailed local-agent voice work
order covering ES/FR plus missing EN/IT.

### Implemented

1. **L0, source:** `src/greia_platform/system_language.py` now
   advertises only `en` and `it` through the canonical registry.
   Installer chooser, on-device Parent panel, Parent API and narrow
   privileged language helper already use that same registry, so
   all four selector/mutation interfaces narrow together.
   There is no migration that rewrites immutable installation records
   or historical unsupported `language.json` state. Reading legacy
   unsupported locale safely falls back to English until a parent
   explicitly selects a supported value. Updated
   `tests/test_system_language.py` to cover the two-language
   registry, rejected legacy tags, safe historical persistence,
   current Parent API list and settings.
   Source: `132b10ea`, `f511e5a4`.
2. **L2, staged source:** `src/greia_installer/i18n_es_fr.py`
   provides **108 Spanish and 108 French string entries**, with
   exactly the same initial key set as existing Italian installer
   copy. `InstallerTranslator` now handles `es` and `fr`
   internally for staging/preview, including dynamic statuses for
   SSID, typed key, pressed counts, battery, pointer and display.
   These languages are **still NOT exposed in the device picker**.
   Updated `tests/test_installer_localization.py` for static
   parity, destructive warning preservation and dynamic-safe
   values. This is a **draft translation**, requiring native
   speaker proofreading, source key audit and rendered installer
   checks; it is not fully reviewed live copy.
   Source: `8c8085cb`, `4d8c565e`, `ed0d6152`.
3. **L1, inventory tooling:** added offline
   `tools/audit_greia_language_coverage.py` with key parity
   source census and per-locale declared speech/file inventory;
   the output deliberately calls out text blockers, missing audio,
   mapping omissions and custom-code voice modules requiring manual
   review. It does not invent a text prompt for an audio file or
   falsely claim to find all dynamic hardcoded speech.
   Added `tests/test_four_language_inventory.py` with fake
   locale trees, unsafe paths, missing catalogue portal recording
   and source-derived vocabulary proof.
   Source: `e332349a`, `2555b874`, `c11b0be0`,
   `028b6a15`, `6e86d8f6`, `46321689`.
4. **Missing existing EN/IT recording uncovered:** the canonical
   `my_creations` portal previously had **no** launcher label
   WAV for Italian or English. Existing
   `tools/audit_launcher_spoken_labels.py` did not require this
   portal. Added platform-owned `MY_CREATIONS_PORTAL_ID` in
   `src/greia_launcher/catalogue_view.py` and included that
   portal in both voice inventory and launcher spoken-label release
   audits. Missing recordings now remain visible as expected
   requirements, even if no seed WAV is present.
   Source: `ae124511`, `27613150`, `c11b0be0`,
   `46321689`.
5. **Local speech work order:** created
   `LOCAL_AGENT_VOICE_PRODUCTION.md` with exact read order,
   clean-checkout commands, four-language semantic cue ledger,
   source gap reconciliation, accepted speaker/voice kinds,
   audio paths, staging/receipts, QA, format/size checks,
   per-clip native listening, acceptance, evidence delivery and
   stop conditions. Explicit known EN/IT gaps:
   `assets/audio/system/launcher-labels/{en,it}/my_creations.wav`
   and My Time's eight semantic lines per existing locale
   (`activity_incubator/tempo_di_greia/VOICE_PRODUCTION_BRIEF.md`).
   Other older Momo/presenter voice claims require fresh source
   reconciliation. Modal is **preferred**, but it is not implemented
   as a Greia VoiceEngine provider yet; running it requires
   integration and separate hosted-budget authorization.
   Source: `c071c7ac`, `63755cdf`.
6. **Documentation:** accepted language product doc now describes
   two selectable baseline languages and gated es/fr staging;
   old twelve-language proposal is marked historical, ADR 0028
   fallback architecture retained. `AGENTS.md` references
   this scoped plan; OS/Activity skills aligned.
   `src/greia_launcher/panel_strings.py` now documents that the
   installed on-device Parent panel remains untranslated
   beyond English despite the current en/it selector.
   Local task `GLA-014` added to the existing queue
   for current-head tests, GUI preview and voice inventory.

### Explicitly NOT complete

- No full repository unit runs, `make verify`, headless/live Pygame,
  GUI screenshots, parent browser acceptance, authentic system
  install, QEMU/physical Acer or ARM tests on these commits.
- No new ES/FR selection in installer, OS panel or Parent API;
  the registry intentionally remains en/it until acceptance.
- No complete OS Shell/Parent HTML/client ES/FR string catalogue
  or complete Activity/encyclopedia `es.json`/`fr.json` sets yet.
- No translation completeness guarantee even for older en/it
  built-in speech/OS messages; these must be audited.
- No Modal provider implementation, voice generation, ASR receipts
  or human listening performed in this session.
- No installation/update/release gate promoted.

### Next exact GitHub engineering slice

1. Execute or obtain local-agent GLA-014 source evidence, resolve
   any focused tests (no manual pretending). The actual local agent
   should first return EN/IT missing audio list and es/fr text gaps.
2. Inventory Shell/Parent/launcher/Activity source for **inline
   English or Italian text** not in semantic locale JSON; start L3
   platform resource ownership with simple typed substitutions.
   Refactor without architecture duplication or per-language
   scene coordinate forks.
3. Implement/test remaining installer source messages and GUI
   length/line wrapping; native-review current 108 draft ES/FR
   entries, including destructive warnings.
4. Extend built-in Activity translations in batches and implement
   current sound/dialogue cue sheets, starting with the known
   missing My Creations, My Time and previous voice gaps.
5. Design a bounded optional authoring-time Modal `VoiceProvider`
   behind the existing Greia VoiceEngine seam; no live cloud calls
   until authorization and source checks. Coordinate output
   integration/QA with the local agent.
