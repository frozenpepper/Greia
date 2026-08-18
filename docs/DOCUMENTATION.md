# Greia Documentation Map and Authority Model

**Status:** repository-wide documentation contract  
**Last reviewed:** 2026-08-19  
**Audience:** contributors, coding agents, reviewers, test operators, Activity authors

---

## 1. Purpose

Greia has several kinds of truth: repository rules, product requirements, accepted architecture, engineering guidance, exact source/runtime contracts, active sequencing, current evidence, operator protocols, agent manuals, developer tooling, visual-design direction, governance and historical reviews. These documents must not silently compete.

This file defines which class owns which fact. When two sources disagree, resolve the conflict by authority rather than by whichever prose was edited most recently.

---

## 2. Authority order

### 2.1 Repository-wide rules — `AGENTS.md`

`AGENTS.md` owns mandatory contributor/agent behavior and non-negotiable repository/product constraints: required reading/updating, Git/GitHub persistence, hosted-execution restrictions, evidence language, engineering discipline and continuity rules. A narrower document may strengthen but not weaken it.

### 2.2 Product requirements — `docs/product/*`

Product documents own explicitly accepted child-facing, parent-facing and ecosystem-facing behavior. Important current examples:

- `PHASE0_CORE_CREATION_ACTIVITIES.md` — mandatory Writing/Painting scope;
- `ACTIVITY_SYSTEM_NAVIGATION.md` — universal Home/Back behavior;
- `ACTIVITY_INPUT_STANDARDS.md` — keyboard/pointer/touch/controller standards;
- `RESPONSIVE_UI_AND_DISPLAY_LAYOUT.md` — one authored layout, automatic viewport adaptation across Greia-owned surfaces;
- `MY_GREIA_SETTINGS.md` — child-safe visual personalization/settings scope;
- `PARENT_MANAGEMENT.md` — Greia Parents onboarding/management/credential UX;
- `ACTIVITY_ECOSYSTEM_AND_DISTRIBUTION.md` — open authoring/distribution and official-catalogue direction;
- `AWARDS_BADGES_AND_CELEBRATIONS.md` — child-facing award/collection expectations.

### 2.3 Normative architecture — accepted ADRs

Accepted ADRs own architectural decisions. Current cross-cutting authorities include ADR 0012/0013/0014/0018/0019/0020/0021/0022/0023/0024/0025/0026/0027/0028/0029.

Of particular relevance to current UI/Activity/developer work:

- ADR 0018 — lightweight semantic UI foundation;
- ADR 0019 — platform-owned Activity system navigation;
- ADR 0020 — runtime-neutral input profiles/controller support;
- ADR 0026 — resolution-adaptive, single-authoring UI layout;
- ADR 0027 — Activity coordinate spaces/reference canvas/world camera;
- ADR 0028 — platform/Activity localization and language context;
- ADR 0029 — real-runtime Activity Simulator: real Greia services above synthetic hardware/runtime-adapter seams, strict non-drift and evidence boundaries.

`docs/architecture/GREIA_ARCHITECTURE.md` is a living synthesis, not a second ADR system.

### 2.4 Engineering guidance — `docs/engineering/ENGINEERING_FOUNDATIONS.md`

This guide owns repository-wide implementation guidance for OOP structure, purposeful polymorphism, dependency direction, explicit ownership/lifecycle, bounded-resource engineering, documentation and testability. It does not override an accepted ADR or exact source contract.

### 2.5 Exact implemented contracts — source/runtime declarations

For exact currently implemented APIs, schemas, command vocabularies and limits, source/runtime declarations are authoritative.

| Fact | Canonical implementation owner |
|---|---|
| Activity manifest parser/validation, input profile, education metadata and launcher presentation categories | `src/greia_platform/activities.py` |
| Activity runtime/capability/permission/package limits | `runtime/child-runtime.toml` |
| Activity source/trust vocabulary | `src/greia_platform/trust.py` |
| bounded `.greiaactivity` new-install staging/validation/immutable-store/activation seam | `src/greia_platform/activity_packages.py` |
| package-owned Activity icons/presentation assets | `src/greia_platform/activity_assets.py` |
| Python Activity SDK helpers, read-only visual context and trusted customization helpers | `src/greia_platform/activity_api.py` |
| renderer-neutral Activity input profiles/actions | `src/greia_platform/input_core.py` |
| current Pygame input translation | `src/greia_platform/pygame_input.py` |
| typed hardware capability state | `src/greia_platform/hal.py`, `src/greia_platform/device_capabilities.py` |
| provisional legacy-X hardware/input composition | `src/greia_platform/hal_legacy_x.py` |
| renderer-neutral UI semantics | `src/greia_platform/ui_core.py` |
| renderer-neutral interaction motion | `src/greia_platform/ui_motion.py` |
| renderer-neutral bounded selection-aware scrolling | `src/greia_platform/ui_scroll.py` |
| renderer-neutral viewport/rectangle/adaptive-grid calculations | `src/greia_platform/responsive_layout.py` |
| renderer-neutral Activity canvas/world coordinate transforms | `src/greia_platform/activity_viewport.py` |
| shared Pygame Activity canvas adapters | `src/greia_platform/pygame_canvas.py` |
| Pygame child-control metrics, semantic interface-size composition and platform-system-safe Activity toolbar/content geometry | `src/greia_platform/activity_ui.py` |
| platform-wide Pygame UI import surface | `src/greia_platform/pygame_ui.py` |
| lightweight Pygame depth/shadow/raised-panel effects | `src/greia_platform/pygame_effects.py` |
| child profile semantic interface-size persistence (`compact/normal/large`) | `src/greia_platform/ui_preferences.py` |
| child theme/color/wallpaper persistence and bounded media import | `src/greia_platform/customization.py` |
| bounded read-only Activity theme snapshot encoding | `src/greia_platform/theme_snapshot.py` |
| runtime-neutral localization bundles/locale fallback/string/audio lookup | `src/greia_platform/localization.py` |
| child + Activity UI/content-language resolution policy | `src/greia_platform/language_context.py` |
| child-facing language presentation / canonical flag mapping / chooser policy | `src/greia_platform/language_presentation.py` |
| launcher category projection/navigation | `src/greia_launcher/catalogue_view.py` |
| richer launcher presentation/effects/catalogue rendering | `src/greia_launcher/presentation.py` |
| installed profile-aware launcher composition + ordinary Activity visual snapshots | `src/greia_launcher/child_shell.py` |
| launcher profile-theme/wallpaper/UI-size refresh controller | `src/greia_launcher/theme.py` |
| Activity system Home/Back vocabulary/protected geometry | `src/greia_platform/system_chrome.py` |
| trusted system-chrome backend lifecycle/lease seam | `src/greia_launcher/system_chrome.py` |
| Activity storage operations | `src/greia_platform/storage_client.py` |
| Activity event protocol/client | `src/greia_platform/event_protocol.py`, `src/greia_platform/event_client.py` |
| Greia Parent API version/resource/capability vocabulary | `src/greia_parent/protocol.py` |
| base Greia Parent API routing/domain adaptation | `src/greia_parent/api_server.py` |
| capability-gated Parent Activity package upload composition | `src/greia_parent/package_api.py` |
| per-parent-device credential persistence/revocation | `src/greia_parent/credentials.py` |
| main Parent password digest + typed change | `src/greia_platform/main_credential.py` |
| external Parent HTML client | `frozenpepper/Greia-Parent-App-Html`, pinned by `runtime/parent-app-client.toml` + integrity manifest |
| Parent LAN advertisement/service | `build/overlay/etc/avahi/services/greia-parent.service`, `build/overlay/etc/systemd/system/greia-parent.service` |
| shared semantic icon catalogue | `assets/catalog/core_icons_v1.toml` |
| theme palette defaults | `runtime/theme-defaults.toml` |
| first-party child settings UI | `activities/workshop_settings/` (`org.greia.workshop-settings`, child-facing name My Greia) |
| developer remote client vocabulary | `tools/greia_remote.py` |
| privileged developer operations | `src/greia_platform/developer_control.py`, `src/greia_platform/developer_input.py` |
| Activity Simulator synthetic device/HAL facts | `src/greia_simulator/device.py` |
| Activity Simulator isolated profile/developer/package/media workspace + real registry/package-service loading | `src/greia_simulator/workspace.py` |
| Activity Simulator runtime/supervisor composition over real Greia services | `src/greia_simulator/runtime.py`, `src/greia_simulator/child_shell.py` |
| simulator-only current-Pygame exact-viewport bootstrap | `src/greia_simulator/python_activity.py` |
| Activity Simulator desktop control plane / repository entry point | `src/greia_simulator/app.py`, `tools/greia_simulator.py` |
| image composition | `build/profiles/*.toml`, `build/package-sets/*.txt`, canonical builders/overlays |
| early-boot framebuffer cover renderer | `build/early-boot/greia-fb-splash.c`, `build/early-boot/README.md` |
| canonical boot artwork lineage | `assets/boot/source/`, `assets/boot/static/`, `tools/generate_boot_artwork.py` |
| launcher-owned boot intro | `src/greia_launcher/boot_intro.py` |
| one-shot boot chime | `src/greia_launcher/boot_chime.py`, `assets/audio/system/greia-boot-chime.wav` |

Documentation may explain these contracts but must not invent a conflicting one. When source intentionally changes, update affected living manuals in the same tranche.

### 2.6 Active sequencing — active plan

`docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md` owns active ordering, prerequisites, closure criteria and append-only progress history while active. It does not turn a source implementation into executed evidence.

The Activity Simulator is a developer-tooling tranche under ADR 0029. It does **not** move, bypass or close the R7/R8/R9/R10/R14 phase gates. In particular, future HTML/Web simulator support must consume the canonical R9 Web runtime rather than implementing it in parallel.

### 2.7 Current branch/evidence state — `HANDOVER.md`

`HANDOVER.md` owns current implementation state, the exact evidence boundary, unproven work, blockers and the next legitimate verification step. Do not promote committed tests into PASS merely because the files exist. Simulator results must be explicitly labeled simulator/developer evidence and cannot be promoted into backend/hardware acceptance.

### 2.8 Exact operator procedures — `docs/testing/*`

Named protocols own prerequisites, commands, stop conditions, evidence to preserve and what a PASS does not prove. Current UI procedures include:

```text
docs/testing/2026-08-18_LOCAL_AGENT_FULL_TEST_AND_FIX_SESSION.md
docs/testing/2026-08-18_RESPONSIVE_UI_ACCEPTANCE.md
docs/testing/2026-08-18_MY_GREIA_ACCEPTANCE.md
```

`docs/testing/LOCAL_AGENT_START_HERE.md` composes the current mandatory focused gate and evidence boundary, including first-frame Activity readiness and system-safe core-Activity UI regressions.

### 2.9 Agent/developer manuals — `docs/agents/*`, `docs/development/*`, `skills/*`

`docs/agents/GREIA_AGENT_OPERATIONS.md` is the operational entry point for build/test/hardware work. `skills/greia-activity-authoring/SKILL.md` is the living Activity authoring guide. `docs/development/GREIA_ACTIVITY_SIMULATOR.md` is the Activity Simulator developer/operator guide below ADR 0029. All three must preserve the difference between simulator semantic evidence and real image/backend/physical evidence.

### 2.10 Governance/licensing — `docs/governance/*`

`docs/governance/LICENSING_AND_TRADEMARK.md` owns practical license/provenance/contribution/trademark guidance, subordinate to ADR 0024 where normative.

### 2.11 Reviews/evidence — `docs/reviews/*`

Reviews are dated analysis/evidence snapshots unless promoted into a product requirement, ADR or active plan. Never rewrite historical evidence to pretend a later fix existed earlier.

Current hardware reconciliation:

```text
docs/reviews/2026-08-18_REAL_HARDWARE_INSTALLATION_AND_LAUNCHER_REVIEW.md
```

### 2.12 Visual/design manuals — `docs/design/*`

`GREIA_VISUAL_STYLE_GUIDE.md` owns reusable visual-language direction. `GREIA_VISUAL_ART_AND_CORE_ASSET_REQUIREMENTS.md` owns the production-art inventory.

`GREIA_LAUNCHER_INTERACTION_AND_ACTIVITY_CATALOGUE.md` owns the current launcher interaction/catalogue synthesis.

`GREIA_ACTIVITY_CANVAS_AND_VIEWPORT_AUTHORING.md` owns the designer-facing spatial-mode decision guide below ADR 0027.

---

## 3. Status vocabulary

- **CONSTITUTIONAL** — durable platform/product invariant.
- **SELECTED** — implementation/design/policy selected by accepted decision.
- **PROVISIONAL** — current implementation while architecture/evidence remains open.
- **SOURCE-CLOSED** — required source scope closed at a named boundary; runtime/hardware evidence may remain.
- **UNPROVEN** — designed/implemented but lacking required execution/runtime/hardware evidence.
- **DEFERRED** — intentionally outside the current phase.
- **HISTORICAL** — retained provenance, not current instruction.
- **COMPLETE** — all explicitly named closure criteria satisfied.

Never use `PASS`, `accepted`, `complete`, `supported` or `licensed` without naming scope where ambiguity is possible.

---

## 4. Implemented versus conceptual — current distinctions

Architecture examples communicate semantics; they are not automatically current APIs.

- `activity.toml` remains the implemented manifest. Do not add conceptual localization tables unless the parser/runtime are migrated in the same tranche.
- `.greiabackup` remains future-facing until its implementation phase closes.
- A bounded ZIP-based `.greiaactivity` **new-install** seam exists; full R10 update/remove/rollback/signature/revocation/save-migration does not.
- Parent API `POST /api/v1/activities/install` exists, but ordinary/release install capability remains false while Parent transport/security is provisional.
- Parent-installed packages remain `PARENT_TRUSTED_UNSIGNED`, not built-ins.
- `education.categories` and launcher `[presentation].categories` are different semantics.
- package-owned PNG/WebP Activity icons are implemented; arbitrary host paths are not.
- ADR 0019 Home/Back remains platform chrome, not Activity widgets.
- ADR 0026 selects automatic responsive layout but does not certify every existing surface until migrated/tested.
- ADR 0027/reference-canvas/world transform source exists; raw legacy physical-pixel Activity code can still require migration.
- Shared Pygame `activity_toolbar_button()` / `activity_content_rect()` / `activity_safe_rect()` derive essential Activity UI from the same protected system-chrome geometry; Painting and Writing consume this source path.
- Shape Garden uses `PygameReferenceCanvas`, maps physical pointer input through the same logical transform and rejects Activity interaction inside protected system chrome.
- First-party Python Activities publish lifecycle READY only after a frame presentation in the same launch loop.
- Painting's current editor controls are system-safe, but its durable painting document surface remains coupled to the current editor viewport and still requires a separate resolution-neutral document-model migration.
- ADR 0028 localization/language policy source exists, but full profile persistence, localized catalogue-title wiring, dynamic launcher flags and pre-launch chooser remain partially integrated/unproven.
- My Greia semantic interface-size storage/read-only Activity visual snapshots exist in source but require appropriate owner-controlled/current-head verification.
- ADR 0029 Activity Simulator source exists at/after `c9eac6da7106536629034d2e3e8c5dc2475ab6ac`. Its Python path uses real Greia registry/permission/profile/storage/history/lifecycle services over a synthetic HAL and a simulator-only Pygame display wrapper. This is not production sandbox/display/hardware evidence.
- HTML/Web simulator execution is **not implemented** merely because the simulator exists; it must wait for and consume the canonical R9 Web runtime adapter.
- R7 remains open; Xorg/xinit is provisional compatibility behavior.

---

## 5. Hardware reconciliation rule

A hardware fix is not integrated until all four are true:

1. the immediate physical failure is resolved;
2. authoritative build/source contains the fix;
3. a hardware-independent regression/invariant protects the root-cause class;
4. living documentation explains the class rather than only the device symptom.

Detailed hardware failures belong in `docs/INSTALLATION_ISSUES_LOG.md`; cross-cutting evidence belongs in dated reviews/HANDOVER.

The simulator may help reproduce platform-independent Activity/layout/runtime semantics, but it cannot satisfy the physical-resolution or backend-specific limbs of this rule.

---

## 6. Required update triggers

| Change | Required living update |
|---|---|
| repository workflow/hardware operation | `docs/agents/GREIA_AGENT_OPERATIONS.md` |
| repository-wide non-negotiable rule | engineering foundations and/or `AGENTS.md` |
| Activity manifest/API/runtime/trust/package flow | Activity authoring skill + relevant product/architecture docs |
| responsive layout/shared geometry | ADR 0026 + responsive product doc + source/tests + affected author manuals |
| Activity canvas/world coordinate contract | ADR 0027 + canvas authoring guide + Activity skill + source/tests |
| Activity/localization/language behavior | ADR 0028 + Activity skill + source/tests + launcher/Parent docs where user-facing |
| Activity Simulator device/workspace/runtime/control/evidence behavior | ADR 0029 + `docs/development/GREIA_ACTIVITY_SIMULATOR.md` + simulator tests + Activity/agent manuals when author/operator workflow changes |
| child visual personalization/My Greia scope | `MY_GREIA_SETTINGS.md` + source/tests + Activity skill when author-facing visual context changes |
| launcher catalogue/category/icon/effects | launcher design + source/tests + Activity skill where author-facing |
| package install/update/remove/trust | Activity ecosystem docs + Activity skill + active plan + Parent docs where applicable |
| installation/build/initramfs/display hardware contract | issue log + review/evidence + operator docs + active plan |
| Parent UX/credentials/pairing | `PARENT_MANAGEMENT.md` + ADR 0022 if architectural + Parent client/source |
| architecture decision | ADR + living architecture synthesis |
| active implementation/progress | active plan append + `HANDOVER.md` |
| executed verification | `HANDOVER.md` + durable review/evidence when useful |

---

## 7. Mandatory read order for substantive work

Unless narrower instructions say otherwise:

1. `AGENTS.md`
2. this documentation map
3. relevant product docs / accepted ADRs (including ADR 0029 for simulator work)
4. `docs/engineering/ENGINEERING_FOUNDATIONS.md`
5. active plan
6. `HANDOVER.md`
7. relevant operator/agent/Activity/development manual
8. exact source/runtime contracts being changed

When documents conflict, resolve by authority class. If implementation intentionally changed, update derived manuals; if source conflicts with an accepted decision, resolve the architecture rather than quietly documenting the deviation.
