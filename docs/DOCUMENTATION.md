# Greia Documentation Map and Authority Model

**Status:** LIVING repository-wide documentation contract  
**Reviewed:** 2026-10-26
**Audience:** contributors, coding agents, reviewers, test operators and Activity authors

## 1. Purpose

Greia contains normative architecture, product requirements, exact source contracts, living manuals, active plans, dated test procedures and historical evidence. They must not compete for “current truth”.

When two documents disagree, resolve the conflict by **ownership/authority**, then correct the stale derived document. A newer edit date alone does not make a document authoritative.

## 2. Authority order

### 2.1 Repository-wide work rules — `AGENTS.md`

`AGENTS.md` owns mandatory contributor/agent behavior and non-negotiable repository/product constraints: branch policy, required reading/updating, hosted-execution restrictions, evidence discipline, low-resource/platform invariants and continuity rules.

A narrower document may strengthen but not weaken these rules.

### 2.2 Product requirements — `docs/product/*`

Product documents own accepted child/parent/ecosystem behavior.

Important examples:

```text
PHASE0_CORE_CREATION_ACTIVITIES.md
CHILD_CREATIONS_LIBRARY_AND_MEDIA_INTEROPERABILITY.md
ACTIVITY_SYSTEM_NAVIGATION.md
ACTIVITY_INPUT_STANDARDS.md
RESPONSIVE_UI_AND_DISPLAY_LAYOUT.md
MY_GREIA_SETTINGS.md
CHILD_TIME_AND_ROUTINES.md (time utility/learning/calendar proposal and source incubator)
PARENT_MANAGEMENT.md
SYSTEM_LANGUAGE_AND_LOCALIZATION.md
SYSTEM_UPDATES.md
ACTIVITY_ECOSYSTEM_AND_DISTRIBUTION.md
AWARDS_BADGES_AND_CELEBRATIONS.md
```

### 2.3 Normative architecture — accepted ADRs

Accepted ADRs own architectural decisions. Current cross-cutting accepted decisions include ADR 0012 through ADR 0038 where present, especially:

```text
0012 platform architecture constitution
0014 Greia identity / ARM parity / direct-graphics direction
0018 lightweight UI foundation
0019 platform-owned Activity system navigation
0020 runtime-neutral input/controller support
0022 Parent API/client/pairing privilege boundary
0023 open Activity ecosystem/distribution
0025 Awards/badges/celebrations
0026 resolution-adaptive UI
0027 Activity coordinate spaces/canvas/world camera
0028 localization/language context
0029 real-runtime Activity Simulator/non-drift
0030 transactional system updates
0031 platform-owned microphone processing
0032 profile presentation/grammatical agreement
0033 fail-soft Activity cross-bindings/dev-noise scrub
0034 child text letter-case policy
0037 shared Activity control kit (buttons/HUD/prompt/completion + focus navigation)
0038 lightweight application update packages and single-generation publication
```

`docs/architecture/GREIA_ARCHITECTURE.md` is a living synthesis, not a second ADR system.

The parent-facing website's page content, interactions, copied preview assets and release-link state live in `website/`; `website/README.md` records their provenance and publishing boundary. It summarizes the product for visitors and does not override product requirements, ADRs, source contracts or release evidence. The September website concept prototypes were retired from the active tree during release cleanup. Their design decision is recorded in `docs/archive/reviews/2026-09-23_WEBSITE_DESIGN_STUDIES.md`; the original HTML and preview assets remain recoverable through Git history.

### 2.4 Exact implemented contracts — source/runtime declarations

For exact APIs, schemas, limits, command vocabularies and current implementation behavior, source/runtime declarations are authoritative.

Documentation explains them; it must not invent a conflicting API.

### 2.5 Engineering guidance — `docs/engineering/*`

`ENGINEERING_FOUNDATIONS.md` owns repository-wide implementation guidance for OOP, purposeful polymorphism, dependency direction, explicit lifecycle/ownership, bounded resources and testability.

`GREIA_PERFORMANCE_BEST_PRACTICES.md` owns the living measured-performance guidance.

Narrow engineering guides may add procedures but do not override product/ADR/source authority.

### 2.6 Active sequencing — active plan(s)

The blocking implementation plan is:

```text
docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md
```

It owns current blocking ordering, prerequisites, closure criteria and its append-only progress ledger while active.

The visual workstream plan remains subordinate to the blocking architecture plan:

```text
docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
```

The owner-authorized **Creations Library + Activity catalogue release-quality** workstream has one unified implementation plan and one compact progress ledger:

```text
docs/plans/2026-10-07_CREATIONS_LIBRARY_AND_ACTIVITY_RELEASE/PLAN.md
docs/plans/2026-10-07_CREATIONS_LIBRARY_AND_ACTIVITY_RELEASE/PROGRESS.md
```

It owns interoperable child creations, universal picker/viewer, capacity-aware persistence, first-party Activity quality and curated catalogue decisions. It remains **subordinate to the accepted platform architecture and installer/update/first-boot lifecycle authority**, and it cannot grant hardware release certification.

A subordinate plan owns cross-hardware robustness sequencing and closure criteria:

```text
docs/plans/2026-09-28_CROSS_HARDWARE_ROBUSTNESS_PLAN.md
```

It owns the removal of recurring hardware defect classes (undeclared resource
ownership, environment-metric assumption, latched or unbounded failure, failure
masked as a benign state, silent under-provisioning, advertised-capability
mismatch, runtime mutation lost on re-enumeration, identity/name instability,
probe-identity mismatch, single-machine evidence) across the Acer, UEFI and ARM
reference targets. It is subordinate to the blocking architecture plan and does
not supersede it. Root-cause instances are recorded in
`docs/INSTALLATION_ISSUES_LOG.md`.

The Activity quality execution record (P7: design principles, catalogue decisions, curriculum ladders, platform foundations F0-F6, shared-library and rework waves, append-only progress log) lives beside that plan and is subordinate to it:

```text
docs/plans/2026-10-07_CREATIONS_LIBRARY_AND_ACTIVITY_RELEASE/P7_ACTIVITY_QUALITY_PROGRAM.md
```

The binding SVG authoring recipe (canvas, palette tokens, strokes, shading, forbidden constructs, budgets, review procedure) is owned by `docs/design/GREIA_SVG_AUTHORING_RULES.md`; `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md` indexes it and `skills/greia-visual-authoring/SKILL.md` operationalizes it.

Scoped owner-authorized workstreams (Creations/Activity release, four-language localization and voice production) are listed with their plan, progress file and approval state in `HANDOVER.md` § Active workstreams.

Plans may be long because historical progress is intentionally retained. Do not copy their entire evidence history into `HANDOVER.md`.

### 2.7 Current continuation/evidence boundary — `HANDOVER.md`

`HANDOVER.md` owns the **short current state**:

- current blocking phase;
- current runtime/source-vs-evidence boundary;
- current blockers;
- exact next legitimate procedure/work;
- links to detailed reviews/history.

It should not become an append-only archive. Historical details belong in the active plan, dated reviews and Git history.

### 2.8 Exact test/operator procedures — `docs/testing/*`

A named procedure owns prerequisites, commands, stop conditions and evidence semantics for that procedure.

Dated testing files are **not automatically current global authority**. The live router is:

```text
docs/testing/LOCAL_AGENT_START_HERE.md
```

and it selects the current gate through `HANDOVER.md` / the active plan.

### 2.9 Dated reviews/evidence — `docs/reviews/*`

Dated reviews preserve analysis, evidence and decisions for an exact context/source state.

They are historical evidence unless a current authority explicitly links them for a current rule/procedure. Do not edit old reviews merely to make history agree with the present.

### 2.10 Engineering archive — `docs/archive/*`

`docs/archive/` holds older reviews, investigations and decision reports that still carry a useful lesson, moved verbatim. `docs/archive/README.md` lists each one with its lesson. Nothing in the archive is current instruction.

### 2.11 Derived manuals/skills — `skills/*`, `docs/agents/*`, developer guides

These are practical navigation/authoring/operations manuals derived from the authorities above. They must track source and accepted policy but do not override them.

If a source/ADR change makes a living skill/manual wrong, that change is not completely documented until the derived guide is corrected.

## 3. Document state vocabulary

Use these labels where ambiguity matters:

```text
LIVING
  may state current truth and must be maintained

ACTIVE
  currently controls sequencing or a named procedure

HISTORICAL
  retained evidence/context; not current truth by itself

SUPERSEDED
  retained for history; replacement must be named

DRAFT / PROPOSED
  not accepted product/architecture authority
```

A date in a filename does not by itself decide the state.

## 4. Exact implementation owner map

This is a navigation map, not a substitute for reading source.

| Concern | Canonical current owner(s) |
|---|---|
| Activity manifest/validation/education/input/presentation metadata | `src/greia_platform/activities.py` |
| Activity trust/source vocabulary | `src/greia_platform/trust.py` |
| Runtime capability/permission/package limits | `runtime/child-runtime.toml` |
| Activity package install/activation | `src/greia_platform/activity_packages.py` |
| Activity package presentation assets | `src/greia_platform/activity_assets.py` |
| Python Activity SDK helpers | `src/greia_platform/activity_api.py` |
| Runtime-neutral Activity input | `src/greia_platform/input_core.py` |
| Current Pygame input bridge | `src/greia_platform/pygame_input.py` |
| Pygame Activity procedural PCM format | `src/greia_platform/pygame_audio.py` |
| HAL/device capabilities | `src/greia_platform/hal.py`, `src/greia_platform/device_capabilities.py` |
| Legacy-X HAL compatibility | `src/greia_platform/hal_legacy_x.py` |
| UI semantics/bounded cache | `src/greia_platform/ui_core.py` |
| UI motion/scroll | `src/greia_platform/ui_motion.py`, `src/greia_platform/ui_scroll.py` |
| Responsive layout | `src/greia_platform/responsive_layout.py` |
| Activity viewport/canvas transforms | `src/greia_platform/activity_viewport.py`, `src/greia_platform/pygame_canvas.py` |
| Shared Activity UI metrics/helpers | `src/greia_platform/activity_ui.py`, `src/greia_platform/pygame_ui.py` |
| Child interface-size persistence | `src/greia_platform/ui_preferences.py` |
| Child customization/theme | `src/greia_platform/customization.py`, `src/greia_platform/theme_snapshot.py` |
| Child text letter-case policy | `src/greia_platform/child_text.py` |
| Profile presentation/grammatical agreement | `src/greia_platform/profile_presentation.py` |
| Localization bundle/fallback | `src/greia_platform/localization.py`, `src/greia_platform/language_context.py` |
| Offered OS/installer/Parent languages + optional UI catalogs | `src/greia_platform/languages/*/manifest.json`, `src/greia_platform/languages/*/ui.json`, loaded by `src/greia_platform/system_language.py` |
| Language presentation | `src/greia_platform/language_presentation.py` |
| Device language persistence | `src/greia_platform/system_language.py` |
| Installer language selection | `src/greia_installer/entrypoint.py`, `src/greia_installer/engine.py` |
| Launcher catalogue/Collections | `src/greia_launcher/catalogue_view.py` |
| Launcher presentation | `src/greia_launcher/presentation.py` |
| Launcher spoken labels | `src/greia_launcher/spoken_labels.py` |
| Installed child Shell composition | `src/greia_launcher/child_shell.py` |
| Launcher service composition | `src/greia_launcher/composition.py` |
| Activity display-session contract | `src/greia_launcher/display_session.py` |
| Legacy-X display-session adapter | `src/greia_launcher/display_session_legacy_x.py` |
| Activity Home/Back geometry/actions | `src/greia_platform/system_chrome.py` |
| Trusted chrome coordinator | `src/greia_launcher/system_chrome.py` |
| Legacy-X trusted chrome adapter | `src/greia_launcher/system_chrome_legacy_x.py` |
| Trusted chrome/lifecycle composition | `src/greia_launcher/trusted_chrome_supervisor.py` |
| Usage-limit lifecycle | `src/greia_launcher/usage_limited_supervisor.py`, `src/greia_launcher/usage_limit_lifecycle.py` |
| Usage-limit persistence/policy | `src/greia_platform/usage_limits.py` |
| Platform audio/microphone route | `src/greia_platform/audio.py` and ADR 0031-named implementation files |
| Persistent system controls | `src/greia_platform/system_controls.py` |
| Legacy-X system-control application | `src/greia_platform/system_controls_legacy_x.py`, `src/greia_platform/hardware_session_legacy_x.py` |
| Parent API protocol | `src/greia_parent/protocol.py` |
| Parent API base routing | `src/greia_parent/api_server.py` |
| Parent package upload | `src/greia_parent/package_api.py` |
| Parent update/language/audio/system-control composition | `src/greia_parent/update_api.py` |
| Installed Parent production composition | `src/greia_parent/production_api.py` |
| Parent credentials | `src/greia_parent/credentials.py` |
| Main Parent credential | `src/greia_platform/main_credential.py` |
| External Parent HTML client pin | `runtime/parent-app-client.toml`, `runtime/parent-app-client.manifest.json` |
| Storage service/client | `src/greia_platform/storage.py`, `src/greia_platform/storage_client.py` |
| Session/history/events/progression | current owners under `src/greia_platform/` + `src/greia_launcher/event_broker.py`; policies under `runtime/` |
| System update format/state | `src/greia_platform/system_updates.py` |
| System update operator CLI | `tools/greia_update.py` |
| Typed application update format/inspection | `src/greia_platform/software_update_package.py`, `src/greia_platform/software_update_package_builder.py` |
| Typed application update build/inspect CLI | `tools/greia_software_update.py` |
| Durable application update job and root apply/recovery | `src/greia_platform/software_update_jobs.py`, `src/greia_platform/software_update_apply.py`, `src/greia_platform/software_update_generation.py`, `build/overlay/usr/local/lib/greia-os/software-update-bootstrap.py` |
| Application update operator guide | `docs/development/GREIA_SOFTWARE_UPDATE_PACKAGES.md` |
| Application package Linux acceptance | `docs/testing/2026-10-24_SOFTWARE_UPDATE_ACCEPTANCE.md` |
| Simulator device/workspace/runtime composition | `src/greia_simulator/` |
| Simulator entry point | `tools/greia_simulator.py` |
| Voice Production Engine | `tools/greia_voice.py`, `tools/greia_voice_core/` |
| Shared accepted character audio | `assets/audio/characters/shared/v0.2/` |
| Visual semantic catalogue/runtime cache | `src/greia_platform/assets.py`, `src/greia_platform/pygame_visual_assets.py` |
| Shared-visual selection (library v1) | `assets/catalog/shared_visuals_v1_source.toml` (hand-edited), `assets/catalog/shared_visuals_v1.toml` (generated), `tools/build_visual_renditions.py` |
| Shared Activity control kit / cast feedback / completion scene (ADR 0037) | `src/greia_platform/activity_controls.py`, `src/greia_platform/activity_feedback.py`, `src/greia_platform/pygame_completion.py` |
| Image composition/build | `build/profiles/`, `build/package-sets/`, `build/overlay/` and canonical builders |
| Developer remote client | `tools/greia_remote.py` |
| Developer privileged control | `src/greia_platform/developer_control.py`, `src/greia_platform/developer_input.py` |

When a row becomes stale, fix this map in the same documentation tranche as the source/authority change where practical.

## 5. Public/contributor entry points

Keep the public/current path intentionally small:

```text
README.md
CONTRIBUTING.md
SETUP.md
docs/DOCUMENTATION.md
HANDOVER.md
```

For a family, start at [`docs/user/README.md`](user/README.md) instead. These short user-facing guides describe current or intended tasks in plain language: USB installation, parent management, and links to Activity/image creation. They are **derived practical documentation**, not sources for hardware certification or permission to publish an unaccepted image. Refresh them against the exact release when image downloads become available.

For language contributors, [`docs/development/ADD_A_GREIA_LANGUAGE.md`](development/ADD_A_GREIA_LANGUAGE.md) and [`skills/greia-language-expansion/SKILL.md`](../skills/greia-language-expansion/SKILL.md) give the end-to-end text, audio, staging and acceptance route. Manifest-discovered offered locales use `src/greia_platform/languages/<locale>/manifest.json` plus `ui.json` and Activity locale resources; the source/product owners remain authoritative. New scripts/RTL or unavailable voice languages may still require implementation.

For contributors, [`docs/development/CREATE_AN_ACTIVITY.md`](development/CREATE_AN_ACTIVITY.md) introduces the canonical Activity skill, and [`docs/development/BUILD_A_GREIA_IMAGE.md`](development/BUILD_A_GREIA_IMAGE.md) explicitly links to [`docs/agents/GREIA_IMAGE_BUILD_AGENT.md`](agents/GREIA_IMAGE_BUILD_AGENT.md). These compact front doors never supersede implementation, release-gate or agent-operation authorities.

Then route by task using `skills/*`. Licensing, security reporting and conduct start at the root `LICENSE`, `NOTICE.md`, `TRADEMARK.md`, `SECURITY.md` and `CODE_OF_CONDUCT.md`. ADR 0024 owns the architectural licensing/trademark boundary; `docs/governance/LICENSING_AND_TRADEMARK.md` owns practical mark-use permissions.

Do not put current test counts, candidate SHAs or bulky evidence in README/SETUP. Those facts age quickly and belong in `HANDOVER.md`, a dated review or an immutable release record.

## 6. Evidence classes

Never blur:

```text
SOURCE
AUTHORING PROVIDER + HUMAN LISTENING
SIMULATOR
VM / IMAGE
PHYSICAL DEVICE
```

Examples:

- a committed test file is not a PASS;
- Simulator Home does not prove production trusted-chrome non-coverability;
- a physical PASS at SHA A does not certify source changes at SHA B;
- Whisper/provider success does not replace human audio acceptance.

## 7. Historical content and cleanup

Owner decision (2026-10-16, open-source cleanup): once work is finished and no longer current, its dated documents leave the working tree.

- A document that still teaches something (a root cause, a rejected approach, a design rationale) moves verbatim to `docs/archive/` and gets one line in `docs/archive/README.md`. Link-target-only repairs may point to verified, immutable historical Git revisions when moves/deletions break navigation; they must not rewrite a historical finding, evidence claim or obsolete procedure as if current.
- Everything else (screenshots, capture evidence, finished runbooks, session handovers and status snapshots) is deleted. Git history keeps it.
- A document still cited by a living authority (an ADR, product or design document, skill, asset provenance record or source file) stays in place until that citation is retired.
- `HANDOVER.md` keeps only the current state and recent entries; it is not an archive.

Bulky evidence belongs outside Git unless a specific evidence authority requires otherwise.

**2026-10-26 release cleanup:** the superseded language-tier proposal moved
from `docs/product/` to `docs/archive/plans/`. Twenty-one obsolete website
study HTML/CSS/JS/image files (about 3.5 MB) were retired from
`docs/design/website_mocks_2026-09-23/`; current `website/` is unchanged.
Their decision and exact Git recovery revision are in
`docs/archive/reviews/2026-09-23_WEBSITE_DESIGN_STUDIES.md`.
The living `HANDOVER.md` was condensed from about 290 KB to about 44 KB,
with historical entries recoverable through the SHA recorded inside it.
No test suites, actively referenced A/B results, approved character audio,
production images or asset provenance receipts were deleted.

## 8. Documentation freshness rules

A living document is stale when it materially disagrees with an accepted ADR, current source contract or current evidence owner—even if its review date is recent.

Before public-source/RC sign-off:

1. audit living `Status:` / `Current state:` statements;
2. audit repository-relative paths/links;
3. audit task-router filenames against the actual tree;
4. audit release-language/voice/Parent/update/hardware claims;
5. verify executable commands from a clean checkout where practical;
6. keep old evidence scoped to its exact SHA/environment.

A read-only tracked-Markdown path/link audit now exists:
`python3 tools/audit_repository_docs.py --scope maintained` scans current guides,
agent skills and public entry points; `--scope all` inventories dated
reviews, plans and the archive too. Unlike the earlier entry-only link test,
this reports the source file/line and missing relative target, and never
deletes data. Historical documents may legitimately link to evidence removed
from the working tree during cleanup, but these findings must not be confused
with broken links in a living guide. The maintained-scope audit was run in a local checkout at
`678c2f4acc65e8f97ac56c77975592ac2a112331` on 2026-10-27:
**241 inspected, 0 unresolved links**, with **4/4 audit tests passing**.
The informational all-scope inventory at that revision examined 425 documents
and found 40 broken historical links in two archived files. Those 40 targets
were subsequently repaired as immutable Git-revision links; a fresh full
all-scope audit of the resulting commit has not yet been executed.

### 8.1 Release-preparation source audit — 2026-10-26

A GitHub-source review inspected the Markdown links and obvious obsolete
language/voice claims in **139 maintained root, `docs/` and `skills/`
guides** plus **13 active plans/test procedures**. No missing repository
link targets or present-tense fixed-twelve-language / obsolete default-voice
claims were found in those inspected files. The small
`tests/test_repository_docs_audit.py` suite now also checks maintained links
against the actual local repository when run as part of ordinary tests.

The original broader source inspection was **not execution** of the audit tool;
the focused maintained-scope check was **subsequently executed locally** at the
exact 2026-10-26 head described above. Neither exercise validates external
URLs or establishes semantic correctness of every historical document. Historical
reviews, superseded plans and one-off test reports are **dated evidence**;
they must not override maintained guides. For a complete inventory including
historical broken links, the read-only tool provides `--scope all`. Links
into retired evidence should target an immutable Git revision of the original
file, not result in restoring obsolete runbooks, or make the historical report
appear current. Two archived source documents had such path-only repairs on
2026-10-27; see `docs/archive/README.md`.

Retired in this cleanup tranche: September website study mocks and a set
of disposable August visual test screenshots. Historical reports and
approved recordings, release diagnostics and the named Encyclopedia
visual baselines were preserved. The recovery context remains in
`docs/archive/` and Git history.

## 9. Maintenance

When implementation intentionally changes:

1. source/runtime remains the exact contract owner;
2. update the relevant ADR/product document only when accepted semantics/architecture changed;
3. update living derived manuals/skills whose guidance became wrong;
4. update `HANDOVER.md` if current continuation/evidence changed;
5. append to the active plan when implementation/phase state changed;
6. do not rewrite historical evidence to match the new state.

Public-release requirements are tracked separately in:

```text
docs/release/GREIA_PUBLIC_RELEASE_READINESS.md
```
