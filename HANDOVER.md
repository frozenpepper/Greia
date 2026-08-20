# Greia — Standalone Engineering Handover

**Date:** 2026-08-20  
**Version family:** `0.13.x` development  
**Repository:** `frozenpepper/Greia` (private)  
**Canonical/default/development branch:** `main`  
**Primary blocking platform phase:** **R7 — Direct graphics/session/input architecture**  
**Current cross-cutting work:** device-language/localization + child UX + R13B transactional updates + Activity Simulator/emoji/Writing + **active asset-first visual-library workstream through V4C Reading/Classroom**  
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
- `skills/greia-visual-authoring/SKILL.md` is mandatory for Greia visual-asset/art work.

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

---

# 3. Active Greia visual-library workstream — V2/V3/V4

Canonical continuity:

```text
docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
docs/design/GREIA_VISUAL_STYLE_GUIDE.md
docs/design/GREIA_CONSTRAINT_NATIVE_CHARACTER_GRAMMAR.md
docs/design/GREIA_CHARACTER_EXPRESSIONS_AND_MOTION.md
skills/greia-visual-authoring/SKILL.md
runtime/theme-defaults.toml
assets/visual/README.md
assets/visual/environments/forest_meadow/v0.2/
assets/visual/ui/v0.1/
assets/visual/environments/workshop/v0.1/
assets/visual/environments/clinic/v0.1/
assets/visual/environments/reading_classroom/v0.1/
```

## 3.1 Production rule

The workstream remains explicitly **asset-first**:

> excellent individual assets → reusable asset packs → layered composition → subtle parallax / ambient motion / light / shadow → shared UI system → Shell/Activity reuse

Do not return to crude full-screen mockups, tutorial geometry, decorative HTML that hides weak assets, or generated scene/concept images as a substitute for reusable source production.

The simplified character direction remains valid, but character minutiae do not block backgrounds, props, atmosphere, shadows or UI. Core anchors remain **Lilli, Nino, Tito and Momo**. Static style-anchor approval is not final release/runtime/physical approval.

## 3.2 Current pack status

### Forest / meadow v0.2

`assets/visual/environments/forest_meadow/v0.2/`

- 27 reusable SVG masters;
- composition metadata + actual-asset parallax proof;
- final bounded 1024×600 / 800×600 desktop restraint references;
- default day treatment keeps fireflies/dust/leaves optional, lowers atmosphere intensity and preserves a calm center.

### Shared UI v0.1

`assets/visual/ui/v0.1/`

- broad panels/cards/buttons/tabs/badges/progress/bubbles/reward/avatar/focus/loading/error/empty/portal family;
- static interaction-state masters for focus/hover/press/disabled/completed/favorite;
- independently composed 1024×600 / 800×600 references from the real shared assets.

### Workshop v0.1

`assets/visual/environments/workshop/v0.1/`

- 19 reusable masters;
- warm creative-room furniture/props plus only composition-critical wall/floor, stool, pegboard, easel and note additions;
- separate window/light treatment;
- independent 1024×600 / 800×600 layered references.

### Clinic / care v0.1

`assets/visual/environments/clinic/v0.1/`

- 17 reusable masters;
- warm pretend-care furniture/props, room bases, window/light and restrained heart FX;
- reduced-size + 1024×600 / 800×600 desktop review;
- no medicine labels/dosage-like content.

### Reading / classroom v0.1

`assets/visual/environments/reading_classroom/v0.1/`

- 17 reusable masters: room bases, arched window/light, bookcase/books, reading tent/rug/seating, chalkboard and restrained decor;
- explicitly reuses Workshop `blocks` and `pencil_cup` rather than duplicating those source assets;
- first desktop review revised weak `book_stack`, `reading_tent` and `beanbag` treatments;
- `catalog.toml`, `REVIEW.md`, `COMPOSITION.md`, `composition.toml` record source/review/composition boundaries.

All current packs remain **candidate** and `runtime_consumed = false`.

Current evidence is **SOURCE + DESKTOP VISUAL REVIEW** only. No simulator/runtime/physical-art acceptance is claimed.

## 3.3 Exact visual continuation

1. start the **fantasy/village/night** family with reusable individual masters first;
2. review weak assets individually before any reference scene is considered evidence;
3. keep moonlight/window glow/fog/stars/fireflies separate composable layers with optional subtle motion metadata;
4. reuse existing Forest assets where semantically appropriate rather than creating pointless duplicates;
5. continue existing pack refinement only for concrete defects or owner feedback;
6. keep all catalogs non-runtime authority until an explicit architecture-reviewed consumption seam exists.

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
2. Start fantasy/village/night as the next bounded individual-asset family.
3. Preserve the asset-first/reuse discipline: no generated scene concept substitutions and no duplicate props when a shared master already exists.
4. Build reference compositions only from real reviewed assets and keep atmosphere/light/FX separately composable.
5. Keep environment/UI catalogs candidate/non-runtime until a reviewed platform consumption seam exists.

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
- after each substantive art session update the active visual plan checkpoint + append-only progress log and this HANDOVER when continuation changes materially.

For visual continuation, start from the **current V2/V3/V4 asset-library checkpoint**, not from rejected character-rig, A2-overlay, crude-scene or generated-concept experiments.
