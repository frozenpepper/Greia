# Greia — Standalone Engineering Handover

**Date:** 2026-08-21  
**Version family:** `0.13.x` development  
**Repository:** `frozenpepper/Greia` (private)  
**Canonical/default/development branch:** `main`  
**Primary blocking platform phase:** **R7 — Direct graphics/session/input architecture**  
**Current cross-cutting work:** device-language/localization + child UX + R13B transactional updates + Activity Simulator/emoji/Writing + collection-first/adaptive Activity discovery + **asset-first visual library with accepted real-Shell shared UI through navigation chrome; Collection-first Greia Home now implemented in source and awaiting Activity Simulator acceptance**  
**External Parent HTML runtime revision pinned by Greia:** `frozenpepper/Greia-Parent-App-Html@519651a5931269ed4275324f2a87ad3f0d08a3f6`

This file is the current project-wide continuation contract. Detailed chronology belongs in the active plans/reviews. Exact APIs and limits remain source-owned.

Visual/art/graphics entry point:

```text
docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
```

Short new-session visual resume:

```text
docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md
```

Child Activity discovery/navigation/audience authority:

```text
docs/product/CHILD_ACTIVITY_DISCOVERY_AND_AUDIENCE.md
```

Launcher implementation/design synthesis:

```text
docs/design/GREIA_LAUNCHER_INTERACTION_AND_ACTIVITY_CATALOGUE.md
```

---

## 1. Repository / execution rules

- `main` is the owner-required development/integration branch. Do not create branches unless the owner explicitly changes policy.
- GitHub is canonical persistence; commit coherent work as it proceeds.
- Do **not** use, query, trigger, rerun, inspect or download GitHub-hosted Actions without explicit owner authorization for that specific hosted execution.
- Never convert committed tests/assets into PASS/approved evidence merely because files exist.
- Blocking implementation plan: `docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md`.
- Main visual-system/index guide: `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`.
- Current art/visual plan: `docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md`.
- Current visual resume: `docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md`.
- R7 remains the first incomplete blocking architecture phase. Cross-cutting product/art work does not close or skip R7.
- Substantive visual work updates the art-plan checkpoint + append-only progress log.
- `skills/greia-visual-authoring/SKILL.md` remains mandatory for Greia visual-asset/art work.
- `skills/greia-activity-authoring/SKILL.md` includes the accepted Collection-first/adaptive-discovery and audience-metadata authoring contract, while clearly distinguishing target fields from current parser support.

---

# 2. Evidence boundary

The latest retained owner-controlled aggregate source gate predating later language/localization/art work remains:

```text
make verify:                         781 PASS
project & 10 activities validation:  PASS
footprint & shell check:             PASS
```

Later source is not retroactively covered by that gate. No current-head aggregate PASS, rebuilt-language-installer physical PASS, R13B activation/rollback PASS, current-head QEMU A/B PASS, Pi A/B PASS, or physical Greia art-performance PASS is claimed here.

Retained physical history from 2026-08-19: a fresh `legacy-x86-i686-dev` syslinux/FAT32 installer booted on the reference Acer Aspire One, installation completed, and the installed OS reached the launcher. Later source requires a rebuilt image before that result extends to it.

Current V5 visual evidence is deliberately scoped:

```text
ui.shadow.soft       SIMULATOR VISUAL REVIEW
ui.card.activity     SIMULATOR VISUAL REVIEW
ui.panel.base        SIMULATOR VISUAL REVIEW
ui.button.primary    SIMULATOR VISUAL REVIEW
ui.avatar.frame      SIMULATOR VISUAL REVIEW
ui.loading.orbit     SIMULATOR VISUAL REVIEW
ui.error.gentle      SIMULATOR VISUAL REVIEW
ui.button.icon       SIMULATOR VISUAL REVIEW
ui.empty.basket      SOURCE / NOT EXERCISED
ui.portal.frame      SOURCE / GENERATED RENDITION PENDING
Collection-first Home SOURCE / SIMULATOR PENDING
```

Accepted simulator facts include:

- `ui.shadow.soft`: six-row responsive matrix, selection, hover, Activity launch and missing/malformed/corrupt fallback; 299 frames / 10.165 s = 29.41 FPS sanity;
- `ui.card.activity`: six-row matrix, navigation/hover/launch and fallback; 27.2 FPS sanity;
- `ui.panel.base`: profile/catalogue framing + six-row matrix + fallback; 29.5 FPS sanity;
- `ui.button.primary`: previous root-category component default/hover/open/back/fallback + six-row matrix; 29.6 FPS sanity;
- `ui.avatar.frame`: profile picker + active-profile switcher + six-row matrix/fallback; ~27.4 FPS sanity;
- owner-directed Activity panel geometry uses the available vertical catalogue space (`panel_top=52..62`, `bottom_margin=4`) with the true 640:420 panel ratio and prominent Activity cards aligned to the authored inner tray;
- owner-directed non-intrusive simulator mode supports `--headless` / `GREIA_SIMULATOR_HEADLESS=1` via SDL dummy video/audio while preserving the real Shell pixel buffer;
- `ui.loading.orbit` launch overlay and `ui.error.gentle` catalogue-error cloud passed headless simulator review with isolated corrupt-PNG fallback; 280 frames / 10.03 s = 27.9 FPS sanity;
- `ui.button.icon` passed in-category Back, real Activity pagination, corrupt-PNG fallback, six responsive rows and 271 frames / 10.01 s = 27.1 FPS; profile pagination remained SOURCE / NOT EXERCISED because the workspace had <=4 profiles;
- `ui.empty.basket` is generated/source-present but the production empty catalogue was not legitimately exercised;
- first Python Activity semantic resolver + Shape Garden consumer remain SOURCE only and non-blocking;
- Collection-first Home + `ui.portal.frame/default` are **SOURCE only** until the dated Collection-first simulator protocol executes;
- full repository `make test` / `make verify` was not run for these V5 visual tranches;
- no physical Acer/Pi V5 performance claim is made.

V5 execution results accumulate in:

```text
LOCAL_AGENT_RESULT.md
```

Current visual acceptance gate:

```text
docs/testing/2026-08-21_COLLECTION_FIRST_HOME_SIMULATOR.md
```

For owner-directed local-agent visual/runtime acceptance, the Activity Simulator is the named evidence path. Build-generation commands such as `make visual-assets` create prerequisites; they are not themselves simulator PASS evidence.

---

# 3. Active Greia visual-library workstream — V2/V3/V4/V5

Canonical continuity:

```text
docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md
docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
docs/design/GREIA_VISUAL_STYLE_GUIDE.md
docs/design/GREIA_VISUAL_ART_AND_CORE_ASSET_REQUIREMENTS.md
docs/design/GREIA_CONSTRAINT_NATIVE_CHARACTER_GRAMMAR.md
docs/design/GREIA_CHARACTER_EXPRESSIONS_AND_MOTION.md
skills/greia-visual-authoring/SKILL.md
runtime/theme-defaults.toml
assets/visual/README.md
assets/visual/library_v0.1.toml
assets/visual/packs_v0.1.toml
```

## 3.1 Documentation shape

Use visual documentation by role:

- `GREIA_ART_GRAPHICS_SYSTEM.md` — stable architecture/index and “where do I look?” guide;
- visual style/art-requirements/character documents — narrower accepted design authorities;
- active visual plan — sequencing, current checkpoint and append-only history;
- `GREIA_VISUAL_SYSTEM_RESUME.md` — concise new-session continuation;
- visual authoring skill — practical production/integration workflow;
- `HANDOVER.md` — project-wide current evidence and continuation.

Do not force new agents to reconstruct visual architecture from chat history.

## 3.2 Production rule

The workstream remains explicitly **asset-first**:

> excellent individual assets → reusable asset packs → layered composition → subtle parallax / ambient motion / light / shadow → shared UI system → explicit semantic runtime consumption → Shell/Activity reuse

Do not return to crude full-screen mockups, tutorial geometry, decorative HTML that hides weak assets, generated scene/concept images as a substitute for reusable source production, or duplicate generic assets when a shared master already exists.

Broad environment/UI source coverage is sufficient. Do not add another environment family without a concrete reusable coverage gap.

The simplified character direction remains valid, but character minutiae do not block V5. Core anchors remain **Lilli, Nino, Tito and Momo**. Static style-anchor approval is not final release/runtime/physical approval.

## 3.3 Current pack status

- **Forest / meadow v0.2:** 27 masters + bounded 1024×600 / 800×600 restraint references + parallax proof.
- **Shared UI v0.1:** reusable panels/cards/buttons/tabs/badges/progress/bubbles/reward/focus/loading/error/empty/portal family + target references.
- **Workshop v0.1:** 19 masters + layered target references.
- **Clinic / care v0.1:** 17 masters + reduced-size/target review; no dosage/medicine-label content.
- **Reading / classroom v0.1:** 17 masters; reuses Workshop generic assets.
- **Fantasy / village / night v0.1:** 15 masters; reuses Forest assets.
- **Water / pond v0.1:** 14 water-specific masters; reuses Forest distant landscape/generic props.

Most source packs remain **candidate SOURCE + DESKTOP VISUAL REVIEW**. Narrow simulator acceptance of promoted runtime assets does not blanket-approve the entire shared UI pack.

## 3.4 V5 shared-consumption architecture

Core source owners now include:

```text
src/greia_platform/assets.py
src/greia_platform/activity_api.py
src/greia_platform/pygame_visual_assets.py
src/greia_launcher/visual_assets.py
src/greia_launcher/presentation.py
src/greia_launcher/shared_ui_presentation.py
src/greia_launcher/profile_chrome_presentation.py
src/greia_launcher/feedback_presentation.py
src/greia_launcher/navigation_chrome_presentation.py
src/greia_launcher/collection_home_presentation.py
src/greia_launcher/child_shell.py
assets/catalog/shared_visuals_v1_source.toml
assets/catalog/shared_visuals_v1.toml
tools/build_visual_renditions.py
tools/validate_visual_renditions.py
```

`AssetCatalogue` uses one explicit semantic namespace. The target runtime does not scan visual directories and does not rasterize SVG. `PygameVisualSurfaceCache` provides bounded PNG surface realization.

Source rendition manifest is now version `0.1.5` and adds:

```text
ui.portal.frame/default
```

from `assets/visual/ui/v0.1/portal_frame.svg`; generated `portal_frame.png` must be produced on the local/build checkout before simulator acceptance.

### Completed navigation-chrome gate

`SharedUiNavigationChromeMixin` applies `ui.button.icon/default` to Shell-local navigation while retaining existing action IDs and hit rectangles. Canonical acceptance commit: `370d96039546178ed2c64366bdaec1b5dc986be2`.

### Current Collection-first Home source gate

`CollectionFirstHomeMixin` in `src/greia_launcher/collection_home_presentation.py` begins the real migration from the temporary All-Activities root to the accepted child discovery model:

```text
profile → Greia Home → primary Collection → Activity
```

Current source behavior:

- `ALL_ACTIVITIES_ID` remains an internal catalogue projection but is no longer rendered as the normal child Activity wall;
- only available non-empty primary Collections are presented on Home;
- Collection destinations use `ui.portal.frame/default` when available;
- entering a Collection reuses accepted Activity cards/panel/navigation/lifecycle;
- local Back returns from Collection to Collection Home; root Back returns to profile choice;
- multi-membership remains projection-only: one Activity may appear in several Collections without duplicated package/state/progress;
- portal-specific failure falls back to a usable circular Collection destination and does not revert the information architecture to All Activities.

Evidence remains **SOURCE** until:

```text
docs/testing/2026-08-21_COLLECTION_FIRST_HOME_SIMULATOR.md
```

passes through the headless Activity Simulator.

### Activity semantic resolver

`src/greia_platform/activity_api.py` exposes:

```python
get_shared_visual(asset_id, variant="default")
get_shared_visual_path(asset_id, variant="default")
```

Activities request semantic IDs/variants rather than arbitrary host paths. The Shape Garden source proof remains non-blocking. Future Web transport must use a controlled URL/handle realization rather than copying Python host-path semantics.

---

# 4. Device-default language selection / localization

Authorities:

```text
docs/adr/0028-platform-and-activity-localization-language-context.md
docs/product/SYSTEM_LANGUAGE_AND_LOCALIZATION.md
docs/reviews/2026-08-19_DEVICE_LANGUAGE_SELECTION_AND_PERSISTENCE.md
```

Effective device language is selected at install, persisted in the install record, and may later be overridden by `SystemLanguageStore` state. English remains default; canonical selectable registry currently includes:

```text
en, it, es, de, fr, zh-CN, pt, ar, hi, id, bn, sw
```

`zh` canonicalizes to `zh-CN`. Installer, hidden Parent panel and external Parent client must consume the same Greia-owned registry rather than maintain independent lists.

**Selectable does not mean fully translated.** English/Italian Activity resources exist in current source; complete translation/font/shaping/RTL acceptance for all selectable languages remains separate work. Current-head language tests must execute before claiming current PASS.

---

# 5. Transactional Greia system updates

Authority:

```text
docs/adr/0030-platform-owned-transactional-system-updates.md
docs/product/SYSTEM_UPDATES.md
docs/development/GREIA_SYSTEM_UPDATE_RELEASE_WORKFLOW.md
```

Implemented source includes signed `.greiaupdate` format/trust helpers, bounded Parent status/upload/inbox behavior and release tooling.

Current x86 profiles remain:

```text
bios-single-ext4
system.update.activate = false
```

A/B inactive-slot activation, boot-health confirmation and automatic rollback are not implemented/accepted on the current production layout. No in-place active-root fallback is authorized merely for convenience.

---

# 6. Accepted child Activity discovery / audience direction

Authorities:

```text
docs/product/CHILD_ACTIVITY_DISCOVERY_AND_AUDIENCE.md
docs/design/GREIA_LAUNCHER_INTERACTION_AND_ACTIVITY_CATALOGUE.md
skills/greia-activity-authoring/SKILL.md
docs/product/PARENT_MANAGEMENT.md
```

Accepted design direction:

- Greia Home is **Collection-first** rather than a flat `All Activities` catalogue with category filters;
- primary Collections remain `create`, `play`, `learn`, `explore`, `my_greia` unless later product evidence changes vocabulary;
- a small primary Collection shows its Activities directly;
- when the **effective visible per-child** Activity count exceeds 10, Greia evaluates whether one semantic sub-Collection layer would materially simplify discovery;
- subdivision is not forced merely by count; incoherent catalogues stay direct with bounded scrolling/paging;
- normal maximum depth is `Home → primary Collection → optional sub-Collection → Activity`;
- hierarchy uses stability/hysteresis; initial collapse target is around 8 effective visible Activities;
- Collections may visually resemble child-friendly shelves/boxes/books/bags/etc. but are not filesystem folders;
- current `education.difficulty` remains a 1–10 **challenge** field and must not be treated as age;
- accepted future audience semantics include optional recommended min/max age/development plus optional adaptive difficulty range;
- exact DOB is not required merely for discovery;
- Parent can eventually choose per-child visibility policies with explicit per-Activity overrides;
- missing future age metadata fails open for ordinary discovery;
- adaptive depth uses the effective visible set **after Parent policy**, not raw installed count.

Current implementation boundary has now advanced:

- semantic `Collection`, multi-membership, bounded scrolling and `education.difficulty` already existed;
- **first Collection-first launcher root migration is now implemented in source** through `CollectionFirstHomeMixin`;
- this first source tranche covers `Home → primary Collection → Activity` only and remains simulator-pending;
- adaptive sub-Collections are not implemented;
- current manifest parsing does not yet accept future age/adaptive-difficulty/discovery-tag fields;
- current `ChildProfile` does not yet store age/development/challenge preference;
- current Parent API/client does not yet implement complete per-child audience/visibility policy.

Do not upgrade the whole discovery design to implemented merely because the first Home migration exists.

---

# 7. R7 display/session/input boundary

R7 remains the primary blocking platform phase.

Current production remains provisional **Xorg/xinit compatibility behavior** while the direct/appliance display/session path is resolved. New unrelated visual work must not deepen X11 coupling.

Mandatory architecture remains:

- Greia-owned display/session authority;
- protected platform Home/Back above Activity content;
- Greia intercepts protected-system input before Activity delivery;
- controller ownership/normalization remains platform-owned;
- ordinary Activities do not gain raw `/dev/input` or DRM authority.

Art/asset work may advance independently where it does not bypass these prerequisites.

---

# 8. Boot / installer / Acer facts retained

- Reference Acer Aspire One is BIOS-only.
- Proven live USB path is **syslinux/FAT32**.
- Canonical USB creator: `tools/build-live-usb.sh`.
- Installed initramfs must be target-kernel/target-hardware aware; build-host/chroot hardware is not target authority.
- Developer/test SSH remains owner-approved `greia / greia`, root SSH denied; normal/release remains fail-closed.
- Earlier Acer install/launcher evidence predates later language/art source and cannot be reused as evidence for those tranches.

Canonical hardware history:

```text
docs/INSTALLATION_ISSUES_LOG.md
docs/INSTALLATION_USB_BOOT_POSTMORTEM.md
docs/INSTALLED_OS_BOOT_POSTMORTEM.md
docs/testing/LOCAL_AGENT_START_HERE.md
```

---

# 9. Current continuation priorities

## Blocking engineering path

1. Resolve exact current `main` SHA before verification/build work.
2. Continue R7 from the first incomplete blocking gate in the architecture-remediation plan.
3. Run required focused/current aggregate source gates on an owner-controlled checkout before claiming current PASS.
4. Rebuild/physically verify later installer/language source before extending old Acer evidence.
5. Continue R13B only within its accepted fail-closed/A-B prerequisites.

## Child UX / Activity discovery

1. Treat Collection-first as the accepted target, not `All + filters`.
2. Current source now implements the first `Home → primary Collection → Activity` migration; validate that through the dated Activity Simulator protocol before promoting it.
3. Preserve multi-membership without package/state duplication.
4. Do not implement adaptive sub-Collections merely from raw count; later logic must use the effective per-child visible set after Parent policy.
5. Do not add target TOML age/adaptive fields until `src/greia_platform/activities.py` and tests support them.
6. Keep age/development suitability separate from challenge/difficulty and avoid requiring exact DOB.

## Visual workstream

1. Start from `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md` and `docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md`.
2. Preserve accepted panel/tray/full-card geometry and headless simulator mode.
3. Do **not** create more environment packs by default.
4. Navigation chrome is accepted; do not keep decorating the obsolete All/filter root.
5. Current exact gate: run `make visual-assets`, then execute `docs/testing/2026-08-21_COLLECTION_FIRST_HOME_SIMULATOR.md` headlessly.
6. Mandatory product review is that normal child Home visibly shows primary Collection destinations, not the All-Activities wall/filter row.
7. Verify keyboard/pointer Collection navigation, Collection → Activity → return-origin → local Back hierarchy, and multi-membership where legitimately available.
8. Corrupt only `portal_frame.png` and verify Collection-first hierarchy survives with a narrow circular fallback while other accepted visuals remain live.
9. Run the full six-row responsive matrix and frame-count sanity; fix only shared/root causes.
10. Keep Shape Garden semantic proof non-blocking and keep future Web transport separate.

---

# 10. Non-negotiable continuation rules

- `main` only unless the owner changes policy;
- GitHub is canonical persistence;
- no unauthorized GitHub Actions use/inspection;
- no current-head PASS without actual current-head execution;
- no visible Linux shell/desktop on normal child path;
- R7 remains open and Xorg/xinit provisional;
- protected Home/Back stays outside Activity authority;
- controller/input/device authority stays platform-owned;
- one canonical device-language registry;
- selectable language is not a translation/font/RTL-completion claim;
- system-update activation stays false on current single-root profiles;
- source/desktop/simulator/physical evidence scopes remain distinct;
- Collection-first Home + bounded adaptive one-level subdivision is the accepted child discovery target;
- the first Collection-first Home source tranche is not evidence for future adaptive/audience/Parent policy;
- adaptive depth uses the effective per-child visible catalogue after Parent policy, not raw installed count;
- `education.difficulty` is challenge, not age;
- target age/adaptive-difficulty/discovery-tag manifest examples remain documentation-only until source parser support lands;
- Greia Collections are semantic child groupings, never exposed filesystem folders;
- multi-membership never duplicates Activity installation/state/progression;
- Greia visual work remains asset-first;
- `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md` remains the stable visual-system entry point;
- `docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md` remains the short current visual-session resume contract;
- candidate files in Git are not automatically approved;
- static character style-anchor approval is not runtime/release/physical approval;
- broad visual coverage does not authorize endless new packs;
- V5 reuses the existing explicit asset-catalogue architecture;
- runtime does not scan visual directories or rasterize SVG;
- image caches remain bounded and no per-frame decode is accepted;
- Activity shared visuals are requested semantically; Activities do not provide arbitrary host paths or mutate the catalogue;
- current local-agent visual/fallback/responsive acceptance is handled through the Activity Simulator, preferably headlessly;
- Shell-local navigation restyling must not be confused with protected Activity system navigation authority;
- after each substantive visual session update the active visual-plan checkpoint + append-only progress log, visual resume, main guide if architecture changed, and this HANDOVER when continuation changes materially.

For current visual continuation, start from the **Collection-first Greia Home simulator gate**, not from the old All/filter root, rejected character-rig/crude-scene/generated-concept work, more-pack-by-default work, or proof-only Shape Garden work.
