# Greia — Standalone Engineering Handover

**Date:** 2026-08-20  
**Version family:** `0.13.x` development  
**Repository:** `frozenpepper/Greia` (private)  
**Canonical/default/development branch:** `main`  
**Primary blocking platform phase:** **R7 — Direct graphics/session/input architecture**  
**Current cross-cutting work:** device-language/localization + child UX + R13B transactional updates + Activity Simulator/emoji/Writing + **asset-first visual library through Water/Pond; V5 first Shell consumer simulator-accepted; first Python Activity semantic visual seam implemented in source**  
**External Parent HTML runtime revision pinned by Greia:** `frozenpepper/Greia-Parent-App-Html@519651a5931269ed4275324f2a87ad3f0d08a3f6`

This file is the current project-wide continuation contract. Detailed chronology belongs in the active plans/reviews. Exact APIs and limits remain source-owned.

For visual/art/graphics work, the stable entry point is:

```text
docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
```

The short new-session visual resume file is:

```text
docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md
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

Current V5-specific evidence:

- typed explicit shared-visual catalogue + cross-manifest merge are committed;
- build-host SVG→PNG generation + generated runtime catalogue are committed;
- bounded PNG-only `PygameVisualSurfaceCache` is committed;
- `ui.shadow.soft` is integrated under launcher Activity tiles and accepted through the Greia Activity Simulator;
- accepted Shell simulator matrix: 1024×600 normal/large, 1280×800 normal, 1366×768 compact, 1920×1080 normal, 1111×700 normal;
- accepted Shell interaction: selection, pointer hover, Activity launch lifecycle;
- accepted Shell fallback: missing catalogue, malformed catalogue, corrupt/missing optional PNG;
- Shell simulator frame sanity: 299 frames / 10.165 s = 29.41 FPS;
- evidence class for that first Shell consumer: **SIMULATOR VISUAL REVIEW**;
- first Activity semantic resolver and Shape Garden consumer are now **SOURCE only** pending their dedicated simulator protocol;
- full repository `make test` / `make verify` was **not** run for this V5 visual tranche;
- no physical Acer/Pi V5 performance claim is made.

First Shell-consumer result:

```text
LOCAL_AGENT_RESULT.md
```

Current Activity-facing V5 acceptance protocol:

```text
docs/testing/2026-08-20_V5_ACTIVITY_SHARED_VISUAL_SIMULATOR.md
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
assets/visual/environments/forest_meadow/v0.2/
assets/visual/ui/v0.1/
assets/visual/environments/workshop/v0.1/
assets/visual/environments/clinic/v0.1/
assets/visual/environments/reading_classroom/v0.1/
assets/visual/environments/fantasy_village_night/v0.1/
assets/visual/environments/water_pond/v0.1/
```

## 3.1 Documentation shape

Use the visual documentation by role:

- `GREIA_ART_GRAPHICS_SYSTEM.md` — stable architecture/index and “where do I look?” guide;
- visual style/art-requirements/character documents — narrower accepted design authorities;
- active visual plan — sequencing, current checkpoint and append-only history;
- `GREIA_VISUAL_SYSTEM_RESUME.md` — concise new-session continuation;
- visual authoring skill — practical production/integration workflow;
- `HANDOVER.md` — project-wide current evidence and continuation.

Do not force new agents to reconstruct visual architecture from the progress ledger or chat history.

## 3.2 Production rule

The workstream remains explicitly **asset-first**:

> excellent individual assets → reusable asset packs → layered composition → subtle parallax / ambient motion / light / shadow → shared UI system → explicit semantic runtime consumption → Shell/Activity reuse

Do not return to crude full-screen mockups, tutorial geometry, decorative HTML that hides weak assets, generated scene/concept images as a substitute for reusable source production, or duplicate generic assets when a shared master already exists.

Broad environment/UI source coverage is now sufficient. Do not add another environment family without a concrete reusable coverage gap.

The simplified character direction remains valid, but character minutiae do not block V5. Core anchors remain **Lilli, Nino, Tito and Momo**. Static style-anchor approval is not final release/runtime/physical approval.

## 3.3 Current pack status

- **Forest / meadow v0.2:** 27 masters + bounded 1024×600 / 800×600 restraint references + parallax proof.
- **Shared UI v0.1:** broad reusable panels/cards/buttons/tabs/badges/progress/bubbles/reward/focus/loading/error/empty/portal family + target references.
- **Workshop v0.1:** 19 masters + layered target references.
- **Clinic / care v0.1:** 17 masters + reduced-size/target review; no dosage/medicine-label content.
- **Reading / classroom v0.1:** 17 masters; reuses Workshop generic assets.
- **Fantasy / village / night v0.1:** 15 masters; reuses Forest assets; weak cottage/tower/lantern/well/cobblestone treatment corrected before review.
- **Water / pond v0.1:** 14 water-specific masters; reuses Forest distant landscape/generic props; independent target references committed.

Pack dependencies/review state live in `assets/visual/packs_v0.1.toml`; character/archetype seed state remains in `assets/visual/library_v0.1.toml`.

Most source packs remain **candidate SOURCE + DESKTOP VISUAL REVIEW**. The accepted `ui.shadow.soft` runtime-consumer evidence is narrower and does not blanket-approve the entire shared UI pack.

## 3.4 V5 shared-consumption architecture

V5 reuses Greia's existing explicit asset architecture:

```text
src/greia_platform/assets.py
src/greia_platform/activity_api.py
src/greia_platform/activity_assets.py
src/greia_platform/ui_core.py
src/greia_platform/pygame_visual_assets.py
src/greia_launcher/visual_assets.py
src/greia_launcher/main.py
src/greia_launcher/presentation.py
activities/shape_garden/main.py
assets/catalog/core_icons_v1.toml
assets/catalog/shared_visuals_v1_source.toml
assets/catalog/shared_visuals_v1.toml
tools/build_visual_renditions.py
tools/validate_visual_renditions.py
```

### Catalogue

`AssetCatalogue` keeps the existing icon contract and supports typed shared visuals with semantic ID, bounded kind, role and named variants. `default` is mandatory. Icon and visual IDs share one namespace. File existence, duplicate IDs and asset-root containment remain fail-closed. There is no arbitrary directory discovery.

### Build-time runtime renditions

`assets/catalog/shared_visuals_v1_source.toml` explicitly selects reviewed UI masters/variants including:

```text
ui.panel.base
ui.card.activity
ui.button.primary
ui.shadow.soft
```

`tools/build_visual_renditions.py` renders SVG→PNG with build-host librsvg/`rsvg-convert`, validates containment/dimensions/output PNG structure and writes generated files transactionally. The target device does not need an SVG renderer.

### Runtime Pygame cache

`PygameVisualSurfaceCache` is the Pygame renderer adapter over `AssetCatalogue` + `ui_core.BoundedCache`:

- PNG-only runtime paths;
- semantic ID + variant + requested-size key;
- one-time scale on miss;
- default 12-entry LRU;
- default per-surface ceiling 1024×600;
- explicit clear;
- no per-frame file/decode after hit.

### First Shell consumer — accepted

`ui.shadow.soft` is integrated under launcher Activity tiles with primitive `draw_soft_shadow` fallback and accepted at **SIMULATOR VISUAL REVIEW** scope.

### Substantial visible Shell consumers — accepted

- `ui.card.activity` (`default`, `focused`, `completed`): integrated into `GreiaChildShell` via `SharedUiActivityCardMixin` preserving authored 360:430 portrait geometry, centering icons/labels, and providing fail-soft fallback. Accepted at **SIMULATOR VISUAL REVIEW** scope via `docs/testing/2026-08-20_V5_SHARED_UI_CARD_SIMULATOR.md`.
- `ui.panel.base` (`default`): integrated into `GreiaChildShell` via `SharedUiShellPanelMixin` framing profile picker and Activity catalogue preserving authored 640:420 aspect ratio with isolated fail-soft fallback. Accepted at **SIMULATOR VISUAL REVIEW** scope via `docs/testing/2026-08-20_V5_SHARED_UI_PANEL_SIMULATOR.md`.

### Activity semantic resolver — source implemented

`src/greia_platform/activity_api.py` now exposes:

```python
get_shared_visual(asset_id, variant="default")
get_shared_visual_path(asset_id, variant="default")
```

The Activity supplies semantic ID + variant, not an arbitrary host path. `SharedVisualReference` is read-only. Activity-private art remains valid. The current Python `Path` realization does not define the future Web transport.

### First Python Activity consumer — simulator pending

`activities/shape_garden/main.py` resolves `ui.shadow.soft` once at startup, scales it once to a bounded reference size, and reuses it while drawing shapes. Missing/invalid optional shared visuals leave the Activity playable.

Required validation:

```text
docs/testing/2026-08-20_V5_ACTIVITY_SHARED_VISUAL_SIMULATOR.md
```

No Activity semantic PASS is claimed until that protocol runs.

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

# 6. R7 display/session/input boundary

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

# 7. Boot / installer / Acer facts retained

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

# 8. Current continuation priorities

## Blocking engineering path

1. Resolve exact current `main` SHA before verification/build work.
2. Continue R7 from the first incomplete blocking gate in the architecture-remediation plan.
3. Run required focused/current aggregate source gates on an owner-controlled checkout before claiming current PASS.
4. Rebuild/physically verify later installer/language source before extending old Acer evidence.
5. Continue R13B only within its accepted fail-closed/A-B prerequisites.

## Visual workstream

1. Start from `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md` and `docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md`.
2. Keep `docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md` as sequencing authority.
3. Do **not** create more environment packs by default.
4. Keep `ui.shadow.soft` as the accepted first Shell semantic consumer; do not multiply launcher-only decoration yet.
5. Execute `docs/testing/2026-08-20_V5_ACTIVITY_SHARED_VISUAL_SIMULATOR.md` against Shape Garden.
6. Fix only shared/root causes and rerun affected simulator cases.
7. After Activity simulator acceptance, design the future Web equivalent around the same semantic IDs/variants through a controlled URL/handle adapter rather than host filesystem exposure.
8. Consider `ui.panel.base`, `ui.card.activity`, or `ui.button.primary` as additional Shell consumers only after the Shell/Activity semantic reuse seam is established.

---

# 9. Non-negotiable continuation rules

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
- current local-agent Activity visual/fallback/responsive acceptance is handled through the Activity Simulator;
- after each substantive visual session update the active visual plan checkpoint + append-only progress log, visual resume, main guide if architecture changed, and this HANDOVER when continuation changes materially.

For visual continuation, start from the **Shape Garden Activity semantic shared-visual simulator gate**, not from rejected character-rig, crude-scene, generated-concept, more-pack-by-default, or extra-launcher-decoration work.
