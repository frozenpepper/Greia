# Greia — Standalone Engineering Handover

**Date:** 2026-08-21  
**Version family:** `0.13.x` development  
**Repository:** `frozenpepper/Greia` (private)  
**Canonical/default/development branch:** `main`  
**Primary blocking platform phase:** **R7 — Direct graphics/session/input architecture**  
**Current cross-cutting work:** device-language/localization + child UX + R13B transactional updates + Activity Simulator/emoji/Writing + Collection-first/adaptive Activity discovery + asset-first visual library with real-Shell integration  
**External Parent HTML runtime revision pinned by Greia:** `frozenpepper/Greia-Parent-App-Html@519651a5931269ed4275324f2a87ad3f0d08a3f6`

This file is the project-wide continuation contract. Chronology belongs in plans/reviews; exact APIs/limits remain source-owned.

Key entry points:

```text
docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
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
ui.shadow.soft       SIMULATOR VISUAL REVIEW
ui.card.activity     SIMULATOR VISUAL REVIEW
ui.panel.base        SIMULATOR VISUAL REVIEW
ui.button.primary    SIMULATOR VISUAL REVIEW (previous root presentation)
ui.avatar.frame      SIMULATOR VISUAL REVIEW
ui.loading.orbit     SIMULATOR VISUAL REVIEW
ui.error.gentle      SIMULATOR VISUAL REVIEW
ui.button.icon       SIMULATOR VISUAL REVIEW
ui.portal.frame      SIMULATOR VISUAL REVIEW
ui.empty.basket      SOURCE / NOT EXERCISED
Collection-first Home SIMULATOR VISUAL REVIEW (5 primary collections + Altro/More fallback)
forest_meadow_day_v1 SIMULATOR VISUAL REVIEW (Scene Compositor Runtime in Nascondino nel Bosco)
character.lilli      SIMULATOR VISUAL REVIEW (Scene Actor Lilli guide + grounded contact shadow in Nascondino)
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
- Collection-first Home passed portal Home, bounded 5 primary destinations (`create`, `play`, `learn`, `explore`, `my_greia`), `browse`/`Altro` recovery for unknown categories, Clinic in Play & Learn, corrupt portal fallback, six responsive rows, 27.7 FPS sanity;
- Scene Compositor Runtime passed in `nascondino_bosco` using `forest_meadow_day_v1.toml`, 2-pass background ($z \le 59$) and foreground/atmosphere ($z \ge 60$) rendering, parallax and ambient motion, corrupt required/optional asset fallbacks, six responsive rows, 25.8 FPS sanity;
- Scene Actor Runtime passed in `nascondino_bosco` using `SceneActorDefinition` and `actor_scene_sample` with `character.lilli/default|blink` and `shadow.contact.small.01/default`, deterministic eye blink, grounded vertical idle oscillation, corrected 24 px / 26 px / 20 px target HUD typography with `SCOIATTOLO` fully fitted, and 230 frames / 10.01 s = 23.0 FPS sanity;
- Visual Authoring Library Benchmark (`docs/testing/2026-08-21_VISUAL_AUTHORING_LIBRARY_COMPARISON.md`) passed primary review (`PRIMARY_REVIEW.md`), proving local authoring agent superiority;
- Visual Authoring Kit Variation Benchmark (`docs/testing/2026-08-21_VISUAL_AUTHORING_KIT_VARIATION_BENCHMARK.md`) completed: candidate Authoring Kit created at `assets/visual/authoring_kit/v0.1-candidate/` (4 material standards, 4 assembly recipes, 9 proof SVGs) proving 3 distinct trees, 2 bushes, and 2 rocks from shared grammar without formulaic cloning or glossy specular blobs; review artifacts committed in `docs/reviews/visual/2026-08-21_authoring-kit-variation/` and transfer ZIP at `./GREIA_VISUAL_REVIEW_AUTHORING_KIT_VARIATION_2026-08-21.zip`;
- `ui.empty.basket` remains generated/source-present but not legitimately exercised;
- first Python Activity semantic resolver + Shape Garden consumer remain SOURCE only and non-blocking;
- no physical Acer/Pi V5 performance claim is made.

Current continuation priority:

```text
Owner Review of Authoring Kit Variation Transfer ZIP
→ Promote Accepted Authoring Kit Standards & Primitives
→ S5 Character & Reusable FX Expansion / Web Scene Transport
```

---

# 3. Visual/art system current state

Stable visual architecture/index:

```text
docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
```

Production rule:

> excellent individual assets → reusable asset packs → layered composition → subtle parallax / ambient motion / light / shadow → shared UI system → explicit semantic runtime consumption → Shell/Activity reuse

Do not return to crude full-screen mocks, detailed traditional rigs as default, generated sprite sheets as production truth, runtime SVG rasterization, arbitrary visual-directory scanning, per-frame decode/scale, unbounded caches, simulator-only production branches or new environment-pack proliferation without a real reusable gap.

Current reusable source coverage:

- Forest/Meadow v0.2;
- Shared UI v0.1;
- Workshop v0.1;
- Clinic/Care v0.1;
- Reading/Classroom v0.1;
- Fantasy/Village/Night v0.1;
- Water/Pond v0.1.

Core character direction remains Lilli/Nino/Tito/Momo in the accepted simplified Puff/Bean grammar. Character minutiae do not block integration.

Current shared visual pipeline:

```text
reviewed SVG master
→ explicit source rendition manifest
→ build-host rsvg-convert PNG
→ generated runtime catalogue
→ AssetCatalogue
→ bounded PygameVisualSurfaceCache
→ explicit semantic Shell/Activity consumer
→ Activity Simulator acceptance
```

Current Shell presentation owners:

```text
src/greia_launcher/catalogue_view.py
src/greia_launcher/collection_home_presentation.py
src/greia_launcher/shared_ui_presentation.py
src/greia_launcher/profile_chrome_presentation.py
src/greia_launcher/feedback_presentation.py
src/greia_launcher/navigation_chrome_presentation.py
src/greia_launcher/child_shell.py
```

Accepted panel/card composition relationship remains:

```text
panel_top     = 52..62 px
bottom_margin = 4 px
panel ratio   = authored 640:420
Activity grid = authored inner tray
large cards   ≈ 198–205 px where geometry permits
```

Activity semantic visual API exists in `src/greia_platform/activity_api.py`:

```python
get_shared_visual(asset_id, variant="default")
get_shared_visual_path(asset_id, variant="default")
```

Activities request semantic IDs/variants rather than arbitrary host paths. Future Web transport must provide a controlled URL/handle realization, not expose host filesystem paths.

---

# 4. Collection-first child discovery — current source and gate

Product/design authorities:

```text
docs/product/CHILD_ACTIVITY_DISCOVERY_AND_AUDIENCE.md
docs/design/GREIA_LAUNCHER_INTERACTION_AND_ACTIVITY_CATALOGUE.md
```

## 4.1 Accepted Collection-first Home

Normal child flow is now:

```text
profile
  → Greia Home
    → primary Collection
      → Activity
```

`ALL_ACTIVITIES_ID` remains an internal catalogue projection but is no longer normal child Home. `CollectionFirstHomeMixin` renders large primary destinations using `ui.portal.frame/default`; entering a Collection reuses accepted card/panel/navigation/lifecycle paths; local Back returns Home; Home Back returns profile choice.

This first Home migration is accepted at **SIMULATOR VISUAL REVIEW** scope via:

```text
docs/testing/2026-08-21_COLLECTION_FIRST_HOME_SIMULATOR.md
```

## 4.2 Current correction: platform-owned primary vocabulary

The first accepted Home run showed `Care` as an extra root portal. That happened because arbitrary `[presentation].categories` values were still projected as top-level Collections.

Current source now defines the normal primary Home vocabulary as platform-owned:

```text
create
play
learn
explore
my_greia
```

`src/greia_launcher/catalogue_view.py` now:

- recognizes only those primary IDs as normal launcher Collections;
- does not let arbitrary package category strings manufacture new Home destinations;
- keeps valid otherwise-orphaned Activities discoverable through one platform-owned `browse` fallback (`Altro` / `More`) shown only when necessary;
- retains `All` internally without exposing it as normal child Home;
- preserves multi-membership across recognized primary Collections.

Built-in `Clinica dei Cuccioli` now uses:

```toml
[presentation]
categories = ["play", "learn"]
```

while care/health/empathy remain correctly in `[education]` taxonomy.

Accepted via `docs/testing/2026-08-21_COLLECTION_PRIMARY_VOCABULARY_SIMULATOR.md` at **SIMULATOR VISUAL REVIEW** scope:

- built-in Home has no `Care` or arbitrary package portal (5 primary portals only: `Crea`, `Gioca`, `Impara`, `Esplora`, `Mio Greia`);
- Clinic remains available through Play + Learn;
- disposable unknown-only developer Activity produces one bounded `Altro` / `More` recovery destination instead of being hidden or creating `Storybook` at root;
- normal Back hierarchy, multi-membership, six-row responsiveness and frame sanity remain intact.

## 4.3 Adaptive sub-Collections — next architecture tranche, not implemented yet

Accepted target:

- 1–10 effective visible Activities in a primary Collection → direct Activities;
- >10 → evaluate whether one useful semantic sub-Collection layer helps;
- no forced bad subdivision;
- useful grouping roughly 2–5 recognizable groups;
- max depth `Home → primary Collection → optional sub-Collection → Activity`;
- hysteresis target around enter >10 / collapse around 8;
- future count is based on the effective per-child visible set after Parent policy, not raw installed count.

Future grouping metadata concept `presentation.discovery_tags` is not currently parsed. Age/development/adaptive-difficulty target fields are also not currently parsed. Current `education.difficulty` remains 1–10 challenge, not age.

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

## Child UX / discovery current gate

1. Sync current `main`.
2. Execute `docs/testing/2026-08-21_COLLECTION_PRIMARY_VOCABULARY_SIMULATOR.md` headlessly.
3. Verify normal Home contains only recognized non-empty primary destinations; specifically no `Care` portal.
4. Verify Clinic remains reachable through Play + Learn.
5. Exercise the disposable unknown-only developer fixture and verify bounded `Altro` / `More` recovery without arbitrary root proliferation or silent hiding.
6. Verify multi-membership, Back hierarchy, six-row responsive matrix and simulator frame sanity.
7. Update `LOCAL_AGENT_RESULT.md`, product/design docs, visual plan/resume and this HANDOVER with actual evidence.
8. Commit/push accepted fixes/results to `main`.
9. After acceptance, advance to adaptive optional sub-Collection/discovery metadata architecture rather than another cosmetic root-Home tranche.

## Visual workstream

- preserve accepted panel/tray/card geometry;
- preserve headless simulator workflow;
- do not create more environment packs by default;
- do not return to old All/filter Home;
- do not let proof-only Shape Garden/Web plumbing displace visible product architecture;
- keep Web semantic visual transport separate and controlled.

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
- adaptive depth must eventually use effective per-child visible catalogue after Parent policy, not raw installed count;
- `education.difficulty` is challenge, not age;
- target age/adaptive-difficulty/discovery-tag fields remain documentation-only until parser/source support lands;
- Greia Collections are semantic child groupings, never filesystem folders;
- Greia visual work remains asset-first;
- runtime does not scan visual directories or rasterize SVG;
- image caches remain bounded with no per-frame decode/scale;
- Activity shared visuals are requested semantically;
- current visual/fallback/responsive acceptance runs through Activity Simulator, preferably headlessly;
- after substantive visual/discovery work update stable/current documentation and this HANDOVER.

**Resume current work from the bounded primary-Collection vocabulary simulator gate, not from the already-accepted Collection-first baseline, old All/filter root, rejected character-rig/crude-scene work, more-pack-by-default work, or proof-only Shape Garden work.**
