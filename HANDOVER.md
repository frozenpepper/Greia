# Greia — Standalone Engineering Handover

**Date:** 2026-08-20  
**Version family:** `0.13.x` development  
**Repository:** `frozenpepper/Greia` (private)  
**Canonical/default/development branch:** `main`  
**Primary blocking platform phase:** **R7 — Direct graphics/session/input architecture**  
**Current cross-cutting work:** device-language/localization + child UX + R13B transactional updates + Activity Simulator/emoji/Writing + **asset-first visual library through Water/Pond; V5 shared-consumption source implementation active**  
**External Parent HTML runtime revision pinned by Greia:** `frozenpepper/Greia-Parent-App-Html@519651a5931269ed4275324f2a87ad3f0d08a3f6`

This file is the current-state continuation contract. Detailed chronology belongs in the active plans/reviews. Exact APIs and limits remain source-owned.

---

## 1. Repository / execution rules

- `main` is the owner-required development/integration branch. Do not create branches unless the owner explicitly changes policy.
- GitHub is canonical persistence; commit coherent work as it proceeds.
- Do **not** use, query, trigger, rerun, inspect or download GitHub-hosted Actions without explicit owner authorization for that specific hosted execution.
- Never convert committed tests/assets into PASS/approved evidence merely because files exist.
- Blocking implementation plan: `docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md`.
- Current art/visual plan: `docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md`.
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

Current V5-specific evidence is narrower:

- source implementation is committed;
- provider-free cache source was exercised in an isolated local harness: **9/9 PASS**;
- full repository `make test` / `make verify` was **not** run here;
- `rsvg-convert` is absent in this execution environment, so the generated runtime PNG catalogue/renditions were **not** built here;
- no Shell/Activity path is yet accepted as consuming the new shared visual catalogue/cache.

---

# 3. Active Greia visual-library workstream — V2/V3/V4/V5

Canonical continuity:

```text
docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
docs/design/GREIA_VISUAL_STYLE_GUIDE.md
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

## 3.1 Production rule

The workstream remains explicitly **asset-first**:

> excellent individual assets → reusable asset packs → layered composition → subtle parallax / ambient motion / light / shadow → shared UI system → one explicit shared consumption seam → Shell/Activity reuse

Do not return to crude full-screen mockups, tutorial geometry, decorative HTML that hides weak assets, generated scene/concept images as a substitute for reusable source production, or duplicate generic assets when a shared master already exists.

Broad environment/UI source coverage is now sufficient. Do not add another environment family without a concrete reusable coverage gap.

The simplified character direction remains valid, but character minutiae do not block V5. Core anchors remain **Lilli, Nino, Tito and Momo**. Static style-anchor approval is not final release/runtime/physical approval.

## 3.2 Current pack status

- **Forest / meadow v0.2:** 27 masters + bounded 1024×600 / 800×600 restraint references + parallax proof.
- **Shared UI v0.1:** broad reusable panels/cards/buttons/tabs/badges/progress/bubbles/reward/focus/loading/error/empty/portal family + target references.
- **Workshop v0.1:** 19 masters + layered target references.
- **Clinic / care v0.1:** 17 masters + reduced-size/target review; no dosage/medicine-label content.
- **Reading / classroom v0.1:** 17 masters; reuses Workshop generic assets.
- **Fantasy / village / night v0.1:** 15 masters; reuses Forest assets; weak cottage/tower/lantern/well/cobblestone treatment corrected before review.
- **Water / pond v0.1:** 14 water-specific masters; reuses Forest distant landscape/generic props; independent target references committed.

Pack dependencies/review state live in `assets/visual/packs_v0.1.toml`; character/archetype seed state remains in `assets/visual/library_v0.1.toml`.

All current visual packs remain **candidate** and `runtime_consumed = false`. Art evidence remains **SOURCE + DESKTOP VISUAL REVIEW** only unless a narrower file states otherwise.

## 3.3 V5 shared-consumption implementation now present

V5 reuses Greia's existing explicit asset architecture:

```text
src/greia_platform/assets.py
src/greia_platform/activity_assets.py
src/greia_platform/ui_core.py
src/greia_platform/pygame_visual_assets.py
assets/catalog/core_icons_v1.toml
assets/catalog/shared_visuals_v1_source.toml
tools/build_visual_renditions.py
Makefile: visual-assets
tests/test_asset_catalogue.py
tests/test_pygame_visual_assets.py
```

### Catalogue

`AssetCatalogue` keeps the existing icon contract and now also supports typed shared visuals with semantic ID, bounded kind, role and named variants. `default` is mandatory. Icon and visual IDs share one namespace. File existence, duplicate IDs and asset-root path containment remain fail-closed.

There is still **no arbitrary directory discovery**.

### Build-time runtime renditions

`assets/catalog/shared_visuals_v1_source.toml` explicitly selects the first reviewed UI masters/variants.

`tools/build_visual_renditions.py` renders SVG→PNG with build-host librsvg/`rsvg-convert`, verifies containment/dimensions/output PNG structure, and writes the explicit generated runtime catalogue `assets/catalog/shared_visuals_v1.toml` with a source SHA256.

The target device does not need an SVG renderer.

`make visual-assets` is the explicit build entrypoint.

### Runtime Pygame cache

`PygameVisualSurfaceCache` is a small renderer adapter over `AssetCatalogue` + existing `ui_core.BoundedCache`:

- PNG-only runtime paths;
- semantic ID + variant + requested size cache key;
- lazy Pygame import;
- no display-dependent conversion in loader;
- one-time smooth scaling on cache miss;
- default 12-entry LRU;
- default per-surface ceiling 1024×600 pixels;
- explicit clear;
- no per-frame file/decode after a hit.

Provider-free tests cover cache hits, size keys, variants, eviction/reload, clear/reload, dimension/pixel bounds, SVG rejection and unknown catalogue entries/variants.

### V5 first Shell consumer accepted via Activity Simulator

`ui.shadow.soft` is integrated as the first real Shell consumer under Activity tiles:
- `assets/catalog/shared_visuals_v1.toml` generated via `make visual-assets` (`rsvg-convert`);
- `load_launcher_assets(...)` merges mandatory core icons and optional shared visuals;
- `PygameVisualSurfaceCache` provides bounded 12-entry LRU caching with fail-soft fallback to primitive `draw_soft_shadow`;
- Verified via Activity Simulator across 6 responsive viewports (1024×600 normal/large, 1280×800, 1366×768 compact, 1920×1080, 1111×700), selection/hover/launch interaction, and fail-soft fallback tests (missing catalogue, invalid catalogue, corrupt PNG);
- Frame rate delta sanity check confirmed steady ~29.4 fps over 10.1s;
- Evidence recorded in `./tmp/v5-simulator-evidence/`. Evidence class: **SIMULATOR VISUAL REVIEW**. (No physical hardware or R7 closure claimed).

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

1. Keep `docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md` as sequencing authority.
2. **Do not create more environment packs by default.** V5 is active.
3. Generate/validate first runtime UI renditions on a build checkout with librsvg.
4. Run the focused current-source V5 tests.
5. Integrate one existing Shell/UI path through the generated catalogue/cache.
6. Expand only after evidence; keep Activities/Web on one semantic contract.

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
- candidate files in Git are not automatically approved;
- static character style-anchor approval is not runtime/release/physical approval;
- broad visual coverage does not authorize endless new packs;
- V5 reuses the existing explicit asset-catalogue architecture;
- runtime does not scan visual directories or rasterize SVG;
- image caches remain bounded and no per-frame decode is accepted;
- after each substantive visual session update the active visual plan checkpoint + append-only progress log and this HANDOVER when continuation changes materially.

For visual continuation, start from the **V5 explicit catalogue/rendition/cache implementation gate**, not from rejected character-rig, A2-overlay, crude-scene, generated-concept, or more-pack-by-default work.
