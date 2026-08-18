# Greia Documentation Map and Authority Model

**Status:** repository-wide documentation contract  
**Last reviewed:** 2026-08-18  
**Audience:** contributors, coding agents, reviewers, test operators, Activity authors

---

## 1. Purpose

Greia has several kinds of truth: repository rules, product requirements, accepted architecture, engineering guidance, visual-design direction, implemented APIs, active sequencing, current evidence, test procedures, governance/licensing policy and historical reviews. These documents must not silently compete.

This file defines which document class owns which fact, how conflicts are resolved and which living documents must change when implementation changes.

---

## 2. Authority order and ownership

### 2.1 Repository-wide rules — `AGENTS.md`

`AGENTS.md` owns mandatory contributor/agent behavior and non-negotiable repository/product constraints, including required read/update duties, Git/GitHub persistence rules, hosted-execution restrictions, engineering expectations, continuity and evidence terminology. A narrower document may strengthen but must not weaken it.

### 2.2 Product requirements — `docs/product/*`

Product documents own explicitly accepted child-facing, parent-facing and ecosystem-facing behavior/acceptance intent. Important examples include:

- `PHASE0_CORE_CREATION_ACTIVITIES.md` — mandatory Phase-0 Writing/Painting scope;
- `ACTIVITY_SYSTEM_NAVIGATION.md` — universal Home/Back behavior;
- `ACTIVITY_INPUT_STANDARDS.md` — keyboard/pointer/touch/controller interaction standards;
- `PARENT_MANAGEMENT.md` — Greia Parents onboarding/management/paired-device/maintenance UX;
- `ACTIVITY_ECOSYSTEM_AND_DISTRIBUTION.md` — open authoring/distribution and official-catalogue product direction;
- `AWARDS_BADGES_AND_CELEBRATIONS.md` — child-facing awards/badges/celebration/collection expectations.

### 2.3 Normative architecture — accepted ADRs

Accepted ADRs own architectural decisions. Current cross-cutting authorities include ADR 0012/0013/0014/0018/0019/0020/0021/0022/0023/0024/0025. A newer ADR supersedes an older one only where it explicitly says so.

`docs/architecture/GREIA_ARCHITECTURE.md` is the living synthesis, not a second ADR system. Narrow architecture/design documents are subordinate to accepted ADRs.

### 2.4 Engineering guidance — `docs/engineering/ENGINEERING_FOUNDATIONS.md`

This mandatory guide owns repository-wide implementation guidance for OOP structure, purposeful polymorphism, dependency direction, explicit ownership/lifecycle, bounded-resource engineering, documentation and testability. It does not override an accepted ADR or exact source contract.

### 2.5 Exact implemented contracts — source/runtime declarations

For exact currently implemented APIs, schemas, command vocabularies and limits, source/runtime declarations are authoritative.

| Fact | Canonical implementation owner |
|---|---|
| Activity manifest parser/validation, including `input.profile`, educational metadata and optional launcher `[presentation]` categories | `src/greia_platform/activities.py` |
| Activity runtime/capability/permission/package limits | `runtime/child-runtime.toml` |
| Activity source/trust vocabulary | `src/greia_platform/trust.py` |
| bounded `.greiaactivity` **new-install** staging/validation/immutable-store/activation seam | `src/greia_platform/activity_packages.py` |
| package-owned Activity presentation assets such as `package:assets/icon.png` | `src/greia_platform/activity_assets.py` |
| Python Activity SDK helpers and launch input-profile view | `src/greia_platform/activity_api.py` |
| renderer-neutral Activity input profiles/actions/dead-zone/virtual-pointer semantics | `src/greia_platform/input_core.py` |
| current Pygame keyboard/controller translation | `src/greia_platform/pygame_input.py` |
| typed input-device capability state | `src/greia_platform/hal.py`, `src/greia_platform/device_capabilities.py` |
| provisional legacy-X hardware/input composition | `src/greia_platform/hal_legacy_x.py` |
| renderer-neutral UI semantics/navigation/resource primitives | `src/greia_platform/ui_core.py` |
| renderer-neutral interaction motion | `src/greia_platform/ui_motion.py` |
| renderer-neutral bounded selection-aware scrolling | `src/greia_platform/ui_scroll.py` |
| lightweight Pygame depth/shadow/raised-panel helpers | `src/greia_platform/pygame_effects.py` |
| child launcher category projection/navigation policy | `src/greia_launcher/catalogue_view.py` |
| current richer launcher presentation composition | `src/greia_launcher/presentation.py` |
| Activity system Home/Back vocabulary and protected geometry | `src/greia_platform/system_chrome.py` |
| trusted system-chrome backend lifecycle/lease seam | `src/greia_launcher/system_chrome.py` |
| platform-wide Pygame UI import surface | `src/greia_platform/pygame_ui.py` |
| existing Activity Pygame helper compatibility surface | `src/greia_platform/activity_ui.py` |
| Activity storage operations | `src/greia_platform/storage_client.py` |
| Activity event protocol/client | `src/greia_platform/event_protocol.py`, `src/greia_platform/event_client.py` |
| Greia Parent API version/resource/capability vocabulary | `src/greia_parent/protocol.py` |
| base Greia Parent API routing/domain adaptation | `src/greia_parent/api_server.py` |
| capability-gated Parent Activity package upload composition | `src/greia_parent/package_api.py` |
| per-parent-device credential persistence/revocation | `src/greia_parent/credentials.py` |
| built-in/dependency-free Parent web compatibility surface | `src/greia_parent/web_client.py` |
| external pinned Parent HTML client source | `frozenpepper/Greia-Parent-App-Html`, pinned by `runtime/parent-app-client.toml` and integrity manifest |
| Parent LAN service advertisement | `build/overlay/etc/avahi/services/greia-parent.service` |
| Parent service sandbox/runtime | `build/overlay/etc/systemd/system/greia-parent.service` |
| shared semantic icons | `assets/catalog/core_icons_v1.toml` |
| theme defaults | `runtime/theme-defaults.toml` |
| resolved theme object | `src/greia_platform/customization.py` |
| developer remote client vocabulary | `tools/greia_remote.py` |
| privileged developer operations | `src/greia_platform/developer_control.py`, `src/greia_platform/developer_input.py` |
| image composition | `build/profiles/*.toml`, `build/package-sets/*.txt`, canonical builders and overlays |

Documentation may explain these contracts but must not invent a conflicting one. When source intentionally changes, update the affected living manuals in the same tranche.

### 2.6 Active sequencing — active plan

`docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md` owns active ordering, prerequisites, closure criteria and append-only progress history while active. Historical progress entries remain history; current continuation/evidence belongs in `HANDOVER.md`.

### 2.7 Current branch/evidence state — `HANDOVER.md`

`HANDOVER.md` owns the current implementation/evidence boundary, unproven work, hardware evidence, blockers and exact next legitimate verification step. Do not promote committed test source into a PASS there unless it was actually executed.

### 2.8 Exact operator procedures — `docs/testing/*`

Named test protocols own prerequisites, commands, stop conditions, evidence to preserve and what a PASS does not prove. They may strengthen but not weaken repository/architecture safety rules.

### 2.9 Agent/developer manuals — `docs/agents/*` and `skills/*`

`docs/agents/GREIA_AGENT_OPERATIONS.md` is the operational entry point for project/build/test-hardware work. `skills/greia-activity-authoring/SKILL.md` is the living authoring guide for Activities. These are derived manuals and must track source/ADRs/product rules.

### 2.10 Governance/licensing — `docs/governance/*`

`docs/governance/LICENSING_AND_TRADEMARK.md` owns practical license matrix, provenance/audit, contribution-license, third-party notice and project-mark guidance, subordinate to ADR 0024 where normative.

### 2.11 Reviews/evidence — `docs/reviews/*`

Reviews are dated analysis/evidence snapshots unless promoted into an ADR, product requirement, governance decision or active-plan decision. Do not rewrite historical evidence to make later reality look cleaner.

The 2026-08-18 real-hardware reconciliation is recorded in:

```text
docs/reviews/2026-08-18_REAL_HARDWARE_INSTALLATION_AND_LAUNCHER_REVIEW.md
```

### 2.12 Visual design — `docs/design/*`

`docs/design/GREIA_VISUAL_STYLE_GUIDE.md` owns the selected reusable visual language and Nunito Sans typography direction. The selection does not itself prove bundled font files or physical readability evidence.

`docs/design/GREIA_VISUAL_ART_AND_CORE_ASSET_REQUIREMENTS.md` owns the production art inventory.

**`docs/design/GREIA_LAUNCHER_INTERACTION_AND_ACTIVITY_CATALOGUE.md` owns the current launcher interaction/catalogue design synthesis:** subtle bounded effects, category-navigation semantics, scroll behavior, package-owned icon authoring contract, Parent-installed Activity presentation boundary and the distinction between navigation categories and educational taxonomy. Exact behavior/limits remain source-owned by the implementation table above.

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

## 4. Implemented versus conceptual — important current distinctions

Architecture examples communicate semantics; they are not automatically current APIs.

- `activity.toml` remains the implemented manifest; conceptual YAML does not replace it.
- `.greiabackup` remains future-facing until its implementation phase closes.
- **A bounded ZIP-based `.greiaactivity` new-install seam now exists in source, but full R10 does not.** Updates, removal, rollback selection, signatures/revocation, curated distribution and transactional save migration remain open.
- The Parent API defines `POST /api/v1/activities/install`, but ordinary/release capability remains false while Parent transport is provisional HTTP. Explicit developer/owner-enabled machines can exercise the new-install seam; that is not production transport approval.
- Parent-installed packages are a distinct `PARENT_TRUSTED_UNSIGNED` source, not built-ins and not developer-unsigned packages.
- `education.categories` is learning/progression metadata. New Activity launcher navigation belongs in optional `[presentation] categories = [...]`; the current old-package fallback is compatibility behavior.
- `icon = "package:assets/icon.png"` is now implemented for contained PNG/WebP Activity-owned icons. Arbitrary host paths are not supported.
- ADR 0018 renderer-neutral terms remain broader than Pygame. `ui_motion.py`/`ui_scroll.py` are renderer-neutral; `pygame_effects.py` is one lightweight renderer implementation.
- The current launcher shadows/hover/launch flourish are implemented presentation behavior but still require fresh physical performance/interaction acceptance on the reference hardware floor.
- ADR 0019 Home/Back controls remain platform chrome, not Activity widgets.
- ADR 0020 input profiles/actions remain runtime-neutral semantics; Pygame is one adapter, not universal raw controller authority.
- ADR 0022 Parent API/client architecture is selected, but production local approval/pairing and authenticated encrypted transport remain open.
- ADR 0023's open ecosystem/catalogue architecture does not mean the Official Greia Catalogue, marketplace or entitlement system exists.
- ADR 0024 license policy selection does not prove the whole tree completed public-release provenance/SPDX/licensing audit.
- ADR 0025 award/badge architecture does not mean the award ledger/scheduler/collection/Parent achievement resources are already implemented.
- The Nunito Sans design selection does not mean font assets/tokens/readability evidence are already complete.
- R7 remains open: the current Xorg/xinit display/session implementation and its service privileges are provisional compatibility behavior.

---

## 5. 2026-08-18 hardware-reconciliation documentation rule

Physical-hardware debugging exposed a recurring documentation/source failure: a fix can be true on the machine and described in a log while still being absent from a clean-build overlay.

From this tranche onward, a hardware fix is not considered integrated until all four are true:

1. the immediate physical failure is resolved;
2. the authoritative build/source input contains the fix;
3. a hardware-independent regression/invariant protects the root-cause class;
4. living documentation explains the class of failure rather than only the machine/model symptom.

The detailed failure record is `docs/INSTALLATION_ISSUES_LOG.md`; the cross-cutting review is the dated review above.

---

## 6. Required update triggers

| Change | Required living documentation update |
|---|---|
| repository workflow / hardware operation | `docs/agents/GREIA_AGENT_OPERATIONS.md` |
| repository-wide engineering rules | engineering foundations; `AGENTS.md` when non-negotiable |
| Activity manifest/API/runtime/trust/assets/theme/UI/input/performance/deploy/package flow | Activity authoring skill + relevant design/architecture doc |
| launcher interaction/catalogue/category/icon behavior | `GREIA_LAUNCHER_INTERACTION_AND_ACTIVITY_CATALOGUE.md` + Activity skill + source/tests |
| Activity package install/update/remove/trust/activation behavior | Activity ecosystem architecture/product docs as appropriate + Activity skill + active plan + Parent docs when parent-facing |
| installation/build/initramfs/display-service hardware contract | issue log + dated review/evidence + agent operations/testing docs as needed + active plan |
| child-facing accepted product scope | relevant `docs/product/*`; `AGENTS.md` when constitutional |
| Awards/badges/celebration behavior | product doc + ADR 0025 when architecture changes + Activity skill for author-facing contract |
| visual language/typography | visual style guide + affected source/manuals |
| production art inventory | visual art/core asset requirements |
| project licensing/trademark policy | ADR 0024 when normative + governance manual |
| Parent UX/features/pairing/maintenance | `PARENT_MANAGEMENT.md` + ADR 0022 when architecture/security changes |
| Parent API resources/capabilities/device credentials/discovery/package operations | `src/greia_parent/*` + Parent architecture/product docs + Parent external client where applicable |
| architectural decision | ADR + living architecture synthesis |
| renderer-neutral UI semantics | ADR 0018 + `ui_core.py`/shared primitives + affected manuals |
| Activity system navigation/chrome | ADR 0019 + product doc + source + Activity skill + active R7 plan |
| Activity input/controller semantics | ADR 0020 + input product doc + source + Activity skill + active R7 plan |
| active implementation/progress | active plan append + `HANDOVER.md` |
| executed verification result | `HANDOVER.md` + dated review/evidence when durable |

---

## 7. Mandatory read order for substantive work

Unless a narrower repository instruction says otherwise:

1. `AGENTS.md`
2. this documentation map
3. relevant architecture/accepted ADRs/product requirements
4. `docs/engineering/ENGINEERING_FOUNDATIONS.md`
5. active plan
6. `HANDOVER.md`
7. relevant agent manual or Activity skill
8. exact source/runtime contracts being changed

When documents conflict, resolve by authority class rather than recency alone. If an implementation fact changed intentionally, update the derived manuals; if it conflicts with an accepted decision, stop and resolve the architecture rather than quietly documenting the deviation.
