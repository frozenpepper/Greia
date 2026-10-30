# Greia core team — rules for the owner's own agents

**Who this is for:** the repository owner and the core coding agents working on
the owner's machines. Outside contributors and their agents follow
[`AGENTS.md`](../../AGENTS.md) only; nothing here grants them permissions.
Everything in `AGENTS.md` applies here too: this file adds the core team's branch
policy, the active plans and the continuity duties.

## Branch policy

- The owner and core coding agents work directly on `main` by default. External volunteer contributors work on their own branches and submit pull requests.
- For the owner/core coding agents, do not create feature, review, merge, temporary, safety, or work branches unless the repository owner explicitly asks for a branch. External volunteer contributors are explicitly authorized to create their own contribution branches.
- An existing historical branch is not permission to continue branch-based development.
- Before substantive writes, refresh the current `main` head so concurrent work is preserved.
- If concurrent work has advanced `main`, reconcile the intended changes with that current history and commit the result back to `main`; do not solve divergence by creating another branch unless explicitly instructed.
- For the owner/core coding agents, pull requests or branch-based review workflows are used only when the repository owner explicitly requests them; they are the default for external volunteer contributors.
- External volunteer contributors with private-repository access work on their own branches and open pull requests as described in `CONTRIBUTING.md`; a private fork is also acceptable where supported. They must not push directly to `main`. The rules above govern the core team and its agents.

## Authoritative read order and active plan

Before installing or configuring any Greia toolchain, repository skill, simulator dependency, Parent App checkout, voice backend, developer remote-control environment or OS/image build host, read **`SETUP.md`**. It is the canonical setup index and readiness ledger; the narrower documents it references remain authoritative for their exact procedures.

Before changing implementation or architecture, read:

1. `README.md`;
2. **`docs/DOCUMENTATION.md` — documentation authority, ownership and freshness model**;
3. `docs/architecture/GREIA_ARCHITECTURE.md`;
4. `docs/adr/0012-platform-architecture-constitution.md`;
5. `docs/adr/0014-greia-identity-arm-parity-and-direct-graphics-direction.md`;
6. relevant narrower accepted ADRs, especially ADR 0013 for image composition and later ADRs for trust/runtime/storage/progression boundaries;
7. **`docs/adr/0018-lightweight-ui-foundation.md` — mandatory lightweight Screen/Overlay/Collection UI architecture and low-resource UI rules**;
8. **`docs/adr/0019-platform-owned-activity-system-navigation.md` — mandatory platform-owned Activity Home/Back chrome and protected-input architecture**;
9. **`docs/adr/0020-runtime-neutral-input-profiles-and-controller-support.md` — mandatory runtime-neutral input profiles, controller support and physical-input authority**;
   - **`docs/adr/0037-shared-activity-control-kit.md` — shared Activity control kit (buttons/HUD/prompt/completion, focus navigation) extending ADR 0018–0020; use it instead of hand-drawn Activity controls**;
   - **`docs/adr/0038-lightweight-application-update-packages.md` — typed `.greia_update` Python/Activity/combined packages; ADR 0036 remains the full-system A/B route**;
10. **`docs/engineering/ENGINEERING_FOUNDATIONS.md` — mandatory OOP, polymorphism, maintainability, dependency and performance guidance**;
11. **`docs/product/PHASE0_CORE_CREATION_ACTIVITIES.md` — mandatory first-user-ready-image writing and painting requirement**;
12. **`docs/product/ACTIVITY_SYSTEM_NAVIGATION.md` — mandatory universal Home/Back child-navigation requirement**;
13. **`docs/product/ACTIVITY_INPUT_STANDARDS.md` — mandatory Phase-0 keyboard/pointer/touch/controller interaction standards**;
14. **`docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md` — MANDATORY ACTIVE IMPLEMENTATION PLAN for its remaining non-lifecycle obligations**;
15. **`docs/plans/2026-09-15_MULTIPLATFORM_RELEASE_INSTALL_UPDATE_COMPLETION.md` — MANDATORY CURRENT INSTALL/UPDATE/RELEASE LIFECYCLE ROUTE (ADR 0036 successor plan; owns install/update/release sequencing and closure criteria)**;
16. **`docs/design/GREIA_ART_GRAPHICS_SYSTEM.md` — MANDATORY MAIN ENTRY POINT for Greia art/graphics/visual-asset architecture, source-library structure, composition, runtime rendition/caching and documentation navigation whenever the work touches visual assets or visual integration**;
    - **`docs/design/GREIA_SVG_AUTHORING_RULES.md` — binding SVG recipe for every new or redrawn shared or Activity-private vector asset (Opus is the selected SVG authoring model)**;
17. **`docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md` — MANDATORY CURRENT ART/VISUAL WORKSTREAM PLAN whenever designing, generating, refining, reviewing, integrating, or migrating Greia character art, scenes, props, FX, reusable visual assets, or visual UI treatment**;
18. **`docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md` — current visual-workstream resume contract when continuing art/graphics work across sessions**;
19. `HANDOVER.md`;
20. **`docs/agents/GREIA_AGENT_OPERATIONS.md` — mandatory project/build/test-hardware operating manual for agents**;
21. **`skills/greia-os-work/SKILL.md` whenever creating, modifying, reviewing, refactoring, optimizing, testing or documenting Greia OS/platform/Shell/Parent/installer/simulator/build/runtime/hardware-service implementation**;
22. `skills/greia-activity-authoring/SKILL.md` whenever creating, modifying, reviewing, validating, optimizing, packaging, deploying, or testing an Activity;
23. `skills/greia-visual-authoring/SKILL.md` whenever creating, modifying, reviewing, generating, or integrating Greia visual assets or Activity art;
24. phase-specific testing/review documents referenced by `HANDOVER.md` or the active plan. Older reviews and lessons were removed from the working tree on 2026-10-30 (history: see git); nothing there is current instruction.

`docs/DOCUMENTATION.md` defines which document class owns which fact. In short:

- `AGENTS.md` owns repository-wide work rules and non-negotiable product constraints;
- accepted ADRs own normative architecture decisions;
- source/runtime declarations own exact implemented APIs/schemas/command vocabularies;
- product requirement documents own explicit child-facing scope/UX requirements where referenced here;
- `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md` is the stable visual-system synthesis/index and points humans/agents to the narrower visual authorities and exact source owners;
- the active plan owns sequencing and closure criteria;
- `docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md` owns the short current visual-session resume path;
- `HANDOVER.md` owns current branch/evidence state;
- `docs/testing/*` owns exact named test procedures;
- agent operations/OS work/Activity/visual skills are derived living manuals and must track their implementation owners.

Do not resolve contradictions by choosing whichever document is convenient. Identify the owner of the fact and correct stale derived documentation.

The architecture-remediation plan remains the active **blocking implementation** plan for its remaining non-lifecycle obligations until its final completion criteria are satisfied. It does **not** own install/update/release lifecycle routing: that route is `docs/plans/2026-09-15_MULTIPLATFORM_RELEASE_INSTALL_UPDATE_COMPLETION.md` (ADR 0036 successor). Resume non-lifecycle work from the first incomplete blocking phase in the remediation plan; route all install/update/release/multiplatform lifecycle work from the 2026-09-15 plan. Do not create a competing implementation plan or jump ahead to a more visible feature while an earlier authority/safety prerequisite remains open. The old signed `.greiaupdate` v2 / release-signing-key route is superseded by ADR 0036 and must not be treated as the normal production route.

**Pre-release compatibility policy:** see `AGENTS.md` § Pre-release policy (applies to every contributor).

**Owner-authorized update release campaign (2026-10-27):** fixing and
confirming Greia's A/B and lightweight application updates is the immediate
lifecycle priority. The one current execution route is
`docs/testing/GREIA_UPDATE_RELEASE_ACCEPTANCE.md`. The local coding agent
is expressly authorized to implement, test, repair, build *disposable* Linux
QEMU images, run consolidated installed update acceptance, and commit coherent
fixes to `main` without seeking a new approval after each ordinary failed test.
The old one-stage/1275 source-reuse procedures are historical diagnostic records,
not new prerequisites. Restrictions belonging to the separate delayed
`GREIA_LOCAL_AGENT_TASK_QUEUE.md` do not restrict this implementation task.
Continue preserving real disk selection, slot identity, atomic update/rollback,
child data and profile-session boundaries; never use family/physical disks for
disposable image work. Installed success is not family-release certification.

**Scoped owner-authorized workstreams** (the Creations Library and Activity release programme, and the four-language localization and voice-production rollout) are listed with their plans, progress files, current work orders and owner approvals in `HANDOVER.md` § Active workstreams. They coordinate product/source work in parallel but do **not** supersede the remediation and lifecycle authorities above, which still govern safety prerequisites, installation, update, rollback and hardware acceptance. Do not start a competing catalogue, picker, creative-media, language-registry or voice plan. 

Standing decisions from those workstreams are listed in `AGENTS.md` § Standing owner decisions; they bind every contributor.

The visual-foundation plan is the current **art/visual workstream** plan. It owns art sequencing, checkpoints and append-only art progress while active, but it is subordinate to the blocking architecture plan and accepted ADRs. `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md` is the stable visual-system architecture/index and must remain interpretable after the current plan becomes historical. Art/design/library work may advance where it does not bypass platform prerequisites; a visual task must not be used as justification to deepen provisional X11 coupling, invent a parallel runtime/UI architecture, weaken protected system chrome, or claim hardware/runtime evidence that did not execute.

After every substantive **implementation** turn:

1. append an accurate progress entry to `docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md`; append install/update/release/multiplatform lifecycle progress to `docs/plans/2026-09-15_MULTIPLATFORM_RELEASE_INSTALL_UPDATE_COMPLETION.md` instead;
2. update `HANDOVER.md` with the exact current phase, implemented work, verification/evidence, blockers, and next exact step;
3. run the verification required by the active phase before claiming it complete;
4. update `docs/agents/GREIA_AGENT_OPERATIONS.md` if repository/build/test-hardware/remote-control procedure changed;
5. update `skills/greia-os-work/SKILL.md` whenever OS/platform architecture navigation, extension seams, engineering practice, performance guidance, audio/platform ownership, testing/evidence or contributor workflow changed materially;
6. update `skills/greia-activity-authoring/SKILL.md` in the same tranche whenever the Activity manifest/API/runtime policy/trust model/shared assets or UI/input canon/performance requirements/validation or deployment workflow changed;
7. update `docs/DOCUMENTATION.md` when documentation ownership/precedence/freshness rules change;
8. update the applicable `docs/product/*` requirement when accepted child-facing product scope or UX changes materially;
9. update `docs/engineering/ENGINEERING_FOUNDATIONS.md` when repository-wide implementation/extension rules change materially;
10. commit coherent work to the canonical GitHub repository.

After every substantive **art/visual-design** turn:

1. update the short **Current checkpoint** in `docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md`;
2. append a dated entry to that plan’s **Progress ledger**; never rewrite earlier art-history entries to make experiments look cleaner;
3. update `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md` when the stable visual-system architecture, library structure, runtime consumption seam, composition model or documentation map changes materially;
4. update `docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md` when the current visual phase, next exact action, blocker, testing rule or evidence boundary changes;
5. update `skills/greia-visual-authoring/SKILL.md` when practical model/contributor guidance changes;
6. update `docs/design/GREIA_VISUAL_STYLE_GUIDE.md` or `docs/design/GREIA_VISUAL_ART_AND_CORE_ASSET_REQUIREMENTS.md` when a reusable visual rule/inventory decision becomes accepted rather than merely planned;
7. update `HANDOVER.md` when the art workstream’s continuation state, accepted direction, evidence boundary, blocker, or next exact step changes materially;
8. keep visual evidence scoped accurately as DESIGN SPEC, SOURCE, DESKTOP VISUAL REVIEW, SIMULATOR VISUAL REVIEW, PHYSICAL VISUAL REVIEW, or REJECTED EXPERIMENT;
9. commit coherent accepted/reviewable work to the canonical GitHub repository.

For substantive documentation-only work, update `HANDOVER.md` when the continuation contract changes and preserve a dated review when useful; an implementation-plan progress entry is required only when implementation/phase state actually changes.

Do not rewrite earlier progress entries to make history appear cleaner. Append corrections explicitly.

The agent operations manual and OS work/Activity/visual authoring skills are **living derived contracts**. A source or accepted-design change that makes one materially wrong is not completely documented until the affected manual/skill is corrected.

When—and only when—the active remediation plan's final completion criteria are all satisfied, the contributor closing it MUST mark the plan complete, append final evidence, update `HANDOVER.md`, and **remove this active-plan reference and these special resume/progress instructions from this file**. The completed plan remains under `docs/plans/` as historical evidence.

When—and only when—the visual-foundation plan’s completion criteria are satisfied or the owner explicitly replaces it, close/preserve it as history and remove or replace its current-art-plan references here and in `HANDOVER.md`. Keep `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md` as the stable visual-system entry point unless the owner explicitly replaces that documentation architecture.

## Packaging and continuity

Every substantive implementation turn should leave:

- updated `HANDOVER.md`;
- updated active plan/ADRs where implementation state or decisions changed;
- updated product requirements when accepted child-facing scope changed;
- updated agent operations/OS work/Activity skill when their governed contracts changed;
- updated engineering foundations when repository-wide implementation/extension rules changed;
- no build caches, venvs, downloaded package archives, disk images, private keys, or heavyweight transient evidence inside the source tree.

Every substantive art/visual-design turn should additionally leave the current art plan checkpoint/append-only ledger, `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`, `docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md`, and visual-authoring skill/design authorities consistent with the work actually accepted.

The GitHub repository is the canonical long-term source of truth; chat transcripts are not.
