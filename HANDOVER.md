- **Canonical Cast v0.1 — Final Capture Integrity & Acceptance Recheck (2026-08-22)**:
  - Resolved all 8 review blockers from `docs/reviews/visual/2026-08-22_canonical-cast-v01-runtime-recheck/OWNER_REVIEW_CAPTURE_INTEGRITY.md`.
  - Implemented strict 3-phase capture architecture isolating clean baseline evidence (Phase A) from single-target non-default fallback (Phase B, `flash_happy.png`) and default failure safe fallback screen (Phase C, `dani_neutral.png`).
  - Added on-screen developer diagnostic readout proving requested vs rendered variant, node fallback flag, outer viewport, and active interface-size setting directly on the fixture canvas.
  - Enhanced `PygameSceneRenderer` with fallback node tracking (`stats.fallback_nodes`).
  - Generated verified transfer bundle `GREIA_VISUAL_REVIEW_CANONICAL_CAST_V01_FINAL_CAPTURE_2026-08-22.zip` containing strictly 10 PNGs + `OWNER_FINAL_RECHECK.md` + `runtime-audit.json` + `simulator-trace.json`.


# Greia — Standalone Engineering Handover

**Date:** 2026-08-22  
**Version family:** `0.13.x` development  
**Repository:** `frozenpepper/Greia` (private)  
**Canonical/default/development branch:** `main`  
**Primary blocking platform phase:** **R7 — Direct graphics/session/input architecture**  
**Current cross-cutting work:** device-language/localization + child UX + R13B transactional updates + Activity Simulator/emoji/Writing + Collection-first/adaptive Activity discovery + generic visual-authoring toolbox/discovery tooling + real-Shell visual integration  
**External Parent HTML runtime revision pinned by Greia:** `frozenpepper/Greia-Parent-App-Html@519651a5931269ed4275324f2a87ad3f0d08a3f6`

This file is the project-wide continuation contract. Chronology belongs in plans/reviews; exact APIs/limits remain source-owned.

Key entry points:

```text
docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md
docs/design/GREIA_GENERIC_ART_LIBRARY_TAXONOMY.md
skills/greia-visual-authoring/SKILL.md
docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md
docs/product/CHILD_ACTIVITY_DISCOVERY_AND_AUDIENCE.md
docs/design/GREIA_LAUNCHER_INTERACTION_AND_ACTIVITY_CATALOGUE.md
docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md
```

---

# 1. Repository / execution rules

- `main` is the owner-required integration branch. Do not create branches unless owner policy changes.
- GitHub is canonical persistence; commit coherent work as it proceeds.
- Do **not** query/run/inspect/download GitHub-hosted Actions without explicit owner authorization for that hosted execution.
- Source/tests/assets existing in Git are not PASS evidence by themselves.
- R7 remains the first incomplete blocking architecture phase; cross-cutting product/art work does not close or skip it.
- No visible Linux shell/desktop belongs in the normal child path.
- Current visual/runtime/fallback/responsive acceptance uses the Greia Activity Simulator, preferably headlessly.
- Substantive visual work updates the active visual plan checkpoint/history, visual resume, stable guide when architecture changes, and this HANDOVER when project-wide continuation changes.

---

# 2. Evidence boundary

The last retained owner-controlled aggregate source gate predating later language/art/Collection work remains:

```text
make verify:                         781 PASS
project & 10 activities validation:  PASS
footprint & shell check:             PASS
```

Later source is **not** covered by that historical aggregate gate. No current-head aggregate PASS, rebuilt-language-installer physical PASS, R13B A/B activation/rollback PASS, current-head QEMU A/B PASS, Pi A/B PASS or physical current-art performance PASS is claimed.

Retained physical history: on 2026-08-19 a fresh `legacy-x86-i686-dev` syslinux/FAT32 installer booted on the reference Acer Aspire One, installation completed, and installed OS reached the launcher. Later source requires a rebuilt image before that result extends to it.

Current V5 visual evidence:

```text
ui.shadow.soft        SIMULATOR VISUAL REVIEW
ui.card.activity      SIMULATOR VISUAL REVIEW
ui.panel.base         SIMULATOR VISUAL REVIEW
ui.button.primary     SIMULATOR VISUAL REVIEW (previous root presentation)
ui.avatar.frame       SIMULATOR VISUAL REVIEW
ui.loading.orbit      SIMULATOR VISUAL REVIEW
ui.error.gentle       SIMULATOR VISUAL REVIEW
ui.button.icon        SIMULATOR VISUAL REVIEW
ui.portal.frame       SIMULATOR VISUAL REVIEW
ui.empty.basket       SOURCE / NOT EXERCISED
Collection-first Home SIMULATOR VISUAL REVIEW
forest_meadow_day_v1  SIMULATOR VISUAL REVIEW
character.lilli       SIMULATOR VISUAL REVIEW
```

Accepted simulator facts include:

- `ui.shadow.soft`: full six-row matrix, selection/hover/launch and fallback, ~29.4 FPS sanity;
- Activity cards: six-row matrix/navigation/hover/launch/fallback, 27.2 FPS sanity;
- Shell panel: profile/catalogue framing + six-row matrix/fallback, 29.5 FPS sanity;
- prior root primary buttons: default/hover/open/back/fallback + six-row matrix, 29.6 FPS sanity;
- profile frame: profile picker + active-profile switcher + six-row matrix/fallback, ~27.4 FPS sanity;
- headless simulator supports `--headless` / `GREIA_SIMULATOR_HEADLESS=1` using SDL dummy video/audio while preserving real Shell pixel-buffer capture;
- launch/error shared feedback passed with isolated fallbacks, 27.9 FPS sanity;
- navigation icon button passed in-category Back, real Activity pagination, corrupt-PNG fallback and six responsive rows, 27.1 FPS sanity;
- Collection-first Home passed bounded primary destinations, unknown-category Browse/More recovery, Clinic in Play & Learn, corrupt portal fallback, six responsive rows, 27.7 FPS sanity;
- Scene Compositor Runtime passed in `nascondino_bosco` using `forest_meadow_day_v1.toml`, split background/foreground rendering, parallax/ambient motion, fail-soft required/optional asset behavior, six responsive rows, 25.8 FPS sanity;
- Scene Actor Runtime passed in `nascondino_bosco` with `character.lilli/default|blink`, grounded contact shadow, deterministic blink/idle motion, corrected child-facing HUD typography and 23.0 FPS sanity;
- `ui.empty.basket` remains generated/source-present but not legitimately exercised;
- first Python Activity semantic resolver + Shape Garden consumer remain SOURCE only and non-blocking;
- no physical Acer/Pi V5 performance claim is made.

Visual authoring evidence is now tracked separately from runtime acceptance:

- the owner's local maintainer agent was proven capable of producing stronger source art than the earlier Forest/Meadow baseline; this does **not** generalize to arbitrary user agents;
- themed environment/source bundles are now provenance pools, not the primary user-facing authoring taxonomy;
- `assets/visual/authoring_library/` is the generic semantic discovery layer;
- full source harvest commit `2dcf306589efb721db4cac6bca7233c342fcfaa1` indexed/triaged Reading, Fantasy and Water source pools before new gap claims;
- Generic Core Essentials Batch A commit `574f19530ee292a81225ff14c09ad8b35f6cf933` created 16 cross-category generic candidates + 2 ingredients;
- owner pixel review of the actual Batch A transfer ZIP approved **9 finished assets + 2 ingredients for preferred admission** and intentionally retained **7 finished assets as candidate references**;
- Batch A owner review: `docs/reviews/visual/2026-08-21_generic-core-essentials-batch-a/PRIMARY_REVIEW.md`;
- no Batch A redraw loop is authorized.

Current visual-authoring continuation priority:

```text
Batch A selective stable admission
→ deterministic generic authoring-library discovery helper
→ update model-agnostic visual-authoring skill to use it
→ real Activity-authoring exercise using the toolbox/skill
```

Exact gate:

`docs/testing/2026-08-22_GENERIC_VISUAL_LIBRARY_ADMISSION_AND_DISCOVERY_TOOLING.md`

**No Batch B is currently authorized.**

---

# 3. Visual/art system current state

Stable visual architecture/index:

```text
docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
```

Visual-authoring authorities:

```text
docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md
docs/design/GREIA_GENERIC_ART_LIBRARY_TAXONOMY.md
skills/greia-visual-authoring/SKILL.md
assets/visual/authoring_library/
```

The architecture has two separate visual-authoring tracks:

1. **maintainer-side source-art/toolbox production** — the owner's local agent may be used where it produces better art;
2. **arbitrary Activity-authoring agents** — must use a model/tool-agnostic workflow and may have very different capabilities.

Do not infer arbitrary agent capability from maintainer-agent benchmarks.

Generic authoring principle:

> **Theme/source bundles are provenance pools; generic semantic collections are the primary authoring interface.**

Current generic collections:

```text
Nature & Landscape
Interiors & Architecture
Furniture & Storage
Everyday Props & Containers
Making, Learning & Play
Lighting, Atmosphere, FX & Shadows
Shared UI
Canonical Characters
```

Generic composability rule:

> **Generic assets encode reusable form; Activity-specific meaning and contents remain separable whenever practical.**

Examples: empty bowl/plate rather than food baked in; books without readable titles; blank boards/dials where Activity meaning is layered later.

Current promoted/reviewed source pools include Forest/Meadow v0.3 and Workshop v0.2. Clinic, Reading, Fantasy and Water folders remain source/provenance/reference pools whose generic entries may be preferred, candidate, weak, specialized or superseded.

Generic admission states:

```text
preferred
candidate_reference
```

`preferred` means a resource is strong enough to consider first for direct reuse. `candidate_reference` means it remains useful for composition/adaptation/reference but is not first-choice owner-approved direct-use art. Do not redraw every candidate merely to force it into preferred.

User-agent workflow:

```text
inventory Activity visual needs
→ query/search generic semantic library
→ prefer reviewed/preferred resources where they genuinely fit
→ inspect candidate/source references when useful
→ REUSE / COMPOSE-ADAPT / CREATE ORIGINAL
→ create Activity-local final art where needed
→ flatten/build efficient runtime rendition
→ integrate through existing Greia package/scene boundaries
→ inspect actual pixels
```

Current shared runtime pipeline remains:

```text
reviewed SVG/source master
→ explicit source rendition manifest
→ build-host PNG
→ generated runtime catalogue
→ AssetCatalogue
→ bounded PygameVisualSurfaceCache
→ explicit semantic Shell/Activity consumer
→ Activity Simulator acceptance
```

The generic authoring indexes and future discovery helper are **authoring-time facilities**, not a second runtime asset catalogue/cache.

---

# 4. Collection-first child discovery — current source and gate

Product/design authorities:

```text
docs/product/CHILD_ACTIVITY_DISCOVERY_AND_AUDIENCE.md
docs/design/GREIA_LAUNCHER_INTERACTION_AND_ACTIVITY_CATALOGUE.md
```

Normal child flow is accepted as:

```text
profile
  → Greia Home
    → primary Collection
      → Activity
```

Current primary vocabulary is platform-owned:

```text
create
play
learn
explore
my_greia
```

Arbitrary package category strings do not manufacture top-level child Home destinations. Valid otherwise-orphaned Activities recover through bounded Browse/More fallback. Multi-membership reuses one installed Activity/state/progression record.

Adaptive optional sub-Collections remain future architecture, not current accepted implementation.

---

# 5. Device language / localization

Authorities:

```text
docs/adr/0028-platform-and-activity-localization-language-context.md
docs/product/SYSTEM_LANGUAGE_AND_LOCALIZATION.md
docs/reviews/2026-08-19_DEVICE_LANGUAGE_SELECTION_AND_PERSISTENCE.md
```

Effective language is selected at install, persisted, and may later be overridden by `SystemLanguageStore`. English remains default; canonical selectable registry includes:

```text
en, it, es, de, fr, zh-CN, pt, ar, hi, id, bn, sw
```

`zh` canonicalizes to `zh-CN`. Installer, hidden Parent panel and external Parent client must consume one Greia-owned registry.

Selectable does not mean fully translated. English/Italian Activity resources exist; complete translation/font/shaping/RTL acceptance remains separate work.

---

# 6. Transactional Greia system updates

Authorities:

```text
docs/adr/0030-platform-owned-transactional-system-updates.md
docs/product/SYSTEM_UPDATES.md
docs/development/GREIA_SYSTEM_UPDATE_RELEASE_WORKFLOW.md
```

Implemented source includes signed `.greiaupdate` format/trust helpers, bounded Parent status/upload/inbox behavior and release tooling.

Current x86 profile remains `bios-single-ext4` with:

```text
system.update.activate = false
```

A/B inactive-slot activation, boot-health confirmation and automatic rollback are not implemented/accepted on current production layout. No in-place active-root fallback is authorized for convenience.

---

# 7. R7 display/session/input boundary

R7 remains the primary blocking platform phase. Current production remains provisional Xorg/xinit compatibility behavior while direct/appliance display/session is resolved.

Mandatory architecture remains:

- Greia-owned display/session authority;
- protected platform Home/Back above Activity content;
- protected-system input intercepted before Activity delivery;
- controller ownership/normalization platform-owned;
- ordinary Activities do not gain raw `/dev/input` or DRM authority.

Visual/product work may advance only where it does not deepen provisional X11 coupling or bypass these boundaries.

---

# 8. Boot / installer / Acer facts retained

- Reference Acer Aspire One is BIOS-only.
- Proven live USB path is syslinux/FAT32.
- Canonical USB creator: `tools/build-live-usb.sh`.
- Installed initramfs must be target-kernel/target-hardware aware; build-host/chroot hardware is not target authority.
- Developer/test SSH remains owner-approved `greia / greia`, root SSH denied; normal/release remains fail-closed.
- Earlier Acer install/launcher evidence predates later language/art/Collection source and cannot be reused as evidence for those later tranches.

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

1. Resolve exact current `main` SHA before build/verification work.
2. Continue R7 from the first incomplete blocking gate in the architecture-remediation plan.
3. Run required focused/current aggregate source gates on an owner-controlled checkout before claiming current PASS.
4. Rebuild/physically verify later installer/language source before extending old Acer evidence.
5. Continue R13B only within accepted fail-closed/A-B prerequisites.

## Child UX / discovery

- Collection-first Home baseline and platform-owned primary vocabulary are already accepted at simulator scope.
- Do not return to the old All/filter child Home.
- Future discovery work should advance adaptive optional sub-Collections/Parent per-child visibility deliberately rather than cosmetic root churn.

## Visual authoring workstream — current exact gate

1. Sync current `main`.
2. Execute `docs/testing/2026-08-22_GENERIC_VISUAL_LIBRARY_ADMISSION_AND_DISCOVERY_TOOLING.md`.
3. Materialize exactly the owner-authorized Batch A preferred subset as stable generic source.
4. Keep the 7 weaker Batch A resources as candidate references without redraw.
5. Update the six generic semantic indexes.
6. Add the deterministic authoring-time discovery helper (`collections/list/search/show/validate`, with JSON output).
7. Update `skills/greia-visual-authoring/SKILL.md` to use the helper when available while remaining model/tool agnostic.
8. Run only focused relevant tests and report actual results.
9. Commit/push coherent work to `main`.
10. After this gate, exercise the visual-authoring skill/toolbox in a real Activity-authoring workflow before authorizing another generic art batch.

Do **not** create Batch B merely to increase generic asset count.

---

# 10. Non-negotiable continuation rules

- `main` only unless owner changes policy;
- GitHub canonical persistence;
- no unauthorized GitHub Actions use/inspection;
- no current-head PASS without current-head execution;
- no visible Linux shell/desktop in normal child path;
- R7 remains open and Xorg/xinit provisional;
- protected Home/Back remains outside Activity authority;
- controller/input/device authority remains platform-owned;
- one canonical device-language registry;
- selectable language is not translation/font/RTL completion;
- system-update activation stays false on current single-root profiles;
- source/desktop/simulator/physical evidence scopes remain distinct;
- Collection-first Home is accepted; old All/filter root is not normal child IA;
- primary Home vocabulary is platform-owned, not package-extensible by arbitrary category strings;
- valid unknown-only Activities fail open through bounded Browse/More recovery rather than disappearing;
- education taxonomy remains separate from navigation taxonomy;
- multi-membership never duplicates Activity installation/state/progression;
- Greia Collections are semantic child groupings, never filesystem folders;
- Greia visual work remains asset-first;
- theme/source bundles are provenance pools, not the primary authoring taxonomy;
- generic assets should preserve reusable form and avoid arbitrary baked Activity meaning;
- candidate references are allowed to remain candidate references;
- arbitrary Activity-authoring agents must not be assumed to have the maintainer local agent's drawing capability;
- runtime does not scan visual directories or rasterize SVG;
- image caches remain bounded with no per-frame decode/scale;
- Activity shared visuals are requested semantically;
- current visual/fallback/responsive acceptance runs through Activity Simulator, preferably headlessly;
- authoring-library discovery tooling stays development-time and must not become a second runtime catalogue;
- after substantive visual/discovery work update stable/current documentation and this HANDOVER.

**Resume visual authoring from `docs/testing/2026-08-22_GENERIC_VISUAL_LIBRARY_ADMISSION_AND_DISCOVERY_TOOLING.md`, not from the old themed-pack sequence, Clinic finalization, hero-tree/specimen optimization, Batch A redraw, or an automatic Batch B.**
