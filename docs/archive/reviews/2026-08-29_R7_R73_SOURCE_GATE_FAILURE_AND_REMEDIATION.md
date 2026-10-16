# R7.3 Source Gate Failure and Remediation

**Date:** 2026-08-29  
**Evidence source SHA:** `5ef785085d106fdcf8e876323f6e7ab3ca2e0d7c`  
**Evidence bundle:** owner/local-agent `r7-r73-test-1787976259.zip`  
**Disposition of that acceptance attempt:** `REJECTED`  

## 1. What the executed gate proved

The local test agent executed the R7.3 source gate on a clean `main` checkout at the exact expected SHA and did not modify source during the attempt.

Results:

- focused R7.3 tests: 66/67 PASS, 1 FAIL;
- Activity backend-independence audit: `blockers=0`;
- strict Activity system-chrome ownership audit: `blockers=62`;
- `make verify`: 1516/1520 PASS, 4 FAIL;
- Simulator: not run because the source gate failed;
- Acer/hostile/performance lanes: not run because the source gate failed.

The test agent correctly stopped rather than using Simulator or physical evidence to hide a failing source gate.

## 2. Stale-test failures identified

Three of the four `make verify` failures were stale regression expectations left behind by the R7.2/R7.3 architecture change rather than evidence that the new architecture had lost the old behavior.

### 2.1 Hostile fixture false positive

`tests/test_r7_noncooperative_chrome_fixture.py` used raw substring checks to assert that the hostile fixture did not call `activity_stop_requested`. The fixture's comment explicitly said that it does **not** call `activity_stop_requested()`, so the test failed on the comment text rather than executable behavior.

Remediation committed after the failed gate:

- `9b78cb562a169fb4f23e8b25f7f30f5d29f366e9` — semantic AST/symbol check that excludes comments/docstrings while still rejecting executable/imported escape/chrome symbols.

### 2.2 Generic-launcher X11 focus expectation was obsolete

`tests/test_installation_hardware_regressions.py` still required `_set_x11_input_focus` and `XSetInputFocus` inside generic `greia_launcher.main`, directly contradicting the accepted R7.2 boundary and the already-green `test_r7_shell_window_composition` contract.

The intended compatibility behavior still exists in `greia_launcher.shell_window_legacy_x`; only ownership moved out of generic launcher code.

Remediation:

- `cf819cf51e7fc5801819a5929295f86c6cd1e6dd` — regression now requires generic launcher delegation and pins Xlib focus behavior inside the explicit Legacy-X adapter.

### 2.3 Plain presentation fallback expectations were obsolete

`tests/test_launcher_boot_fallback.py` and `tests/test_my_greia_settings_contract.py` still required `greia_launcher.presentation`, while the installed compatibility session had deliberately moved to `greia_launcher.trusted_presentation` so fallback cannot lose mandatory trusted Home authority.

Remediation:

- `ba291d79e0d8bc0fd3788fe02c4661c6b019c630` — boot fallback contract now pins `trusted_presentation`;
- `3c9b9ea23050a1ad98b2e1b3793bffcd44bbdfd7` — My Greia installed-session contract now pins `trusted_presentation` and rejects the obsolete plain fallback.

These test corrections have **not** been executed yet after modification. They require the next owner-controlled source gate.

## 3. Real R7.3 blocker: catalogue migration is incomplete

The strict R7.3 audit correctly found **62 blockers across 25 Activity source files**. This is real migration debt, not a test defect.

The six first-wave migrated Activities remain clean:

- Writing;
- Painting;
- Labirinto Magico main Activity path;
- Il Volo del Draghetto;
- Shape Garden;
- Storie della Mia Voce.

Remaining strict blockers are retired Activity-owned Home imports/calls, three legacy overlay-render paths, and one `PygameReferenceCanvas.present(system_chrome=...)` request.

Affected files from the executed evidence:

- `activities/acquario_magico/main.py`
- `activities/baia_delle_orche/orca_app.py`
- `activities/bottega_delle_misure/measure_app.py`
- `activities/casa_del_dieci/ten_house_app.py`
- `activities/clinica_cuccioli/clinic_app.py`
- `activities/costruiamo_ponti/main.py`
- `activities/cucciolo_mio/main.py`
- `activities/enciclopedia_greia/enciclopedia_app.py`
- `activities/festa_delle_rime/rhyme_app.py`
- `activities/foresta_parole/main.py`
- `activities/la_discesa_della_biglia/ramp_app.py`
- `activities/luci_di_momo/firefly_app.py`
- `activities/memory_meraviglie/main.py`
- `activities/nascondino_bosco/woodland_app.py`
- `activities/officina_dei_suoni/sound_app.py`
- `activities/orchestra_animali/main.py`
- `activities/pasticceria_magica/main.py`
- `activities/piccola_serra/main.py`
- `activities/posta_di_leo/postcard_app.py`
- `activities/sillabe_magiche/main.py`
- `activities/specchi_magici/mirror_app.py`
- `activities/teatrino_fiabe/main.py`
- `activities/treno_numeri/main.py`
- `activities/viaggio_delfino/delfino_app.py`
- `activities/workshop_settings/main.py`

Important classification detail: the strict audit did **not** reject renderer-neutral protected-region geometry such as `ActivitySystemChromeLayout`. That geometry remains valid. The separate backend audit may still describe such references as migration-tier information; do not mechanically remove protected/safe viewport semantics.

## 4. Required remediation contract

For each strict blocker above, migrate only platform-Home ownership:

- remove `is_home_clicked` imports/calls and their Activity-local Home return branches;
- remove Activity calls/imports of `draw_system_chrome_overlay`;
- remove the obsolete `system_chrome=` request from the Encyclopedia canvas presentation;
- preserve `activity_stop_requested()` lifecycle support;
- preserve Activity-local Back/navigation controls that are not Greia platform Home;
- preserve safe/protected viewport geometry;
- preserve direct SDL/Pygame rendering and high-rate input paths;
- preserve storage, scoring, audio, gameplay and completion behavior.

Do not convert this migration into a gameplay/UI refactor.

## 5. Next evidence gate

Do not spend time on Simulator/Acer until the catalogue strict audit can return zero blockers.

On the final migrated SHA, restart the R7.3 source gate from the beginning:

1. focused R7.3 suite;
2. `PYTHONPATH=src python3 tools/audit_activity_backend_independence.py activities` => `blockers=0`;
3. `PYTHONPATH=src python3 tools/audit_activity_system_chrome_ownership.py --strict` => `Activity system chrome ownership audit: blockers=0`;
4. `make verify` => exit zero;
5. exact-SHA Simulator acceptance;
6. only then exact-SHA Acer Writing/Painting/hostile/performance acceptance.

No R7.3 acceptance claim is valid yet.

## 6. Active-plan synchronization limitation

The mandatory active plan remains:

`docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md`

The connector-only environment cannot safely append to that very large file without whole-file replacement/truncation risk. On the next owner-controlled full checkout, append this executed source-gate result and remediation state to the active plan using normal local Git tooling before treating the plan ledger as synchronized.
