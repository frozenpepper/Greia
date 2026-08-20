# Greia — Standalone Engineering Handover

**Date:** 2026-08-20  
**Version family:** `0.13.x` development  
**Repository:** `frozenpepper/Greia` (private)  
**Canonical/default/development branch:** `main`  
**Primary blocking platform phase:** **R7 — Direct graphics/session/input architecture**  
**Current cross-cutting work:** device-language/localization + child UX + R13B transactional updates + Activity Simulator/emoji/Writing + **active Greia asset-first visual-library workstream (V2/V3/V4A)**  
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

# 3. Active Greia visual-library workstream — V2/V3/V4A

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
```

## 3.1 Production rule

The visual workstream is explicitly **asset-first**:

> excellent individual assets → reusable asset packs → layered composition → subtle parallax / ambient motion / light / shadow → shared UI system → Shell/Activity reuse

Do not return to crude full-screen mockups, tutorial geometry, or decorative HTML that hides weak underlying assets.

The accepted simplified character direction remains valid, but character minutiae no longer block backgrounds, props, atmosphere, shadows or UI.

Core character anchors remain **Lilli, Nino, Tito and Momo**. Static style-anchor approval is not final release/runtime/physical approval.

## 3.2 Forest / meadow v0.2

Canonical source:

```text
assets/visual/environments/forest_meadow/v0.2/
```

The pack contains **27 reusable SVG masters** covering:

- hero/secondary/sapling/willow trees;
- round/flowering/low bushes;
- fern, flower and mushroom clusters;
- large/small rock clusters;
- fallen log and stump;
- large/small clouds;
- distant hills and distant tree line;
- grass edge and dirt playfield patch;
- sunlight and fog overlays;
- small/wide contact shadows;
- fireflies, dust motes and falling leaves.

Metadata/review/proof:

```text
catalog.toml
REVIEW.md
composition_day.toml
parallax_proof.html
```

`runtime_consumed = false` remains explicit.

Desktop review caught and corrected weak sapling, distant-tree-line, fog and dust-mote treatments. A 1024×600 static composition was assembled locally from the actual masters. `parallax_proof.html` uses the committed SVGs with cheap CSS cloud drift, small foliage sway, fog drift, light breathing and firefly movement. It is a design proof, not runtime architecture.

Current evidence: **SOURCE + DESKTOP VISUAL REVIEW** only.

Remaining forest work is intentionally bounded: one 800×600 / 1024×600 restraint/readability pass, then stop polishing the forest indefinitely.

## 3.3 Shared UI visual pack v0.1

Canonical source:

```text
assets/visual/ui/v0.1/
```

The pack now includes reusable masters for:

- panel/sheet;
- default/focused/completed activity cards;
- primary/hover/pressed/disabled/secondary/quiet/icon buttons;
- default/selected tabs;
- new/done/favorite/locked badges;
- progress track/fill/complete;
- speech/thought bubbles;
- reward/avatar frames;
- loading orbit;
- gentle-error cloud;
- empty basket;
- category/location portal frame;
- focus ring, soft shadow and highlight sheen.

Metadata/review:

```text
assets/visual/ui/v0.1/catalog.toml
assets/visual/ui/v0.1/README.md
assets/visual/ui/v0.1/REVIEW.md
```

The pack is aligned to `runtime/theme-defaults.toml`, embeds no child-facing text, and remains `runtime_consumed = false`.

Representative components have been rasterized and desktop-reviewed on Greia cream, Greia sky and dark charcoal. Focus/selection uses shape/frame cues in addition to color. The expanded static-state tranche was also reviewed together before catalog indexing.

Current evidence: **SOURCE + DESKTOP VISUAL REVIEW** only.

Next UI work is a real 800×600 / 1024×600 component composition using these assets, followed by any targeted revision; do not redraw a primitive launcher mock.

## 3.4 Workshop v0.1 started

Canonical source:

```text
assets/visual/environments/workshop/v0.1/
```

First reusable candidate tranche contains:

- workbench;
- shelf;
- paint palette;
- brush bundle;
- pencil cup;
- blocks;
- storage box;
- paper stack;
- rug;
- desk lamp;
- window;
- window-light overlay;
- paint jars.

Metadata/review:

```text
catalog.toml
README.md
REVIEW.md
```

Desktop contact review shows a coherent warm wood/pastel creative-room family and keeps the window light separate from the window so lighting remains composable. `runtime_consumed = false`.

Before composition: reduced-size review of large furniture, add only composition-critical missing pieces such as a stool/chair, wall/floor base or pegboard, then assemble one layered workshop reference composition.

## 3.5 Exact visual continuation

1. build the low-resolution UI reference composition from the real shared UI assets and revise only specific weak components;
2. run the final bounded 800×600 / 1024×600 forest restraint/readability pass;
3. finish Workshop composition-critical assets and one layered workshop composition;
4. begin Clinic individual assets next unless the owner reprioritizes;
5. keep all current catalogs non-runtime authority until an explicit architecture-reviewed consumption seam exists.

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
2. Make the low-resolution UI reference composition from the current V3 masters.
3. Finish the bounded forest restraint/readability pass.
4. Complete Workshop composition-critical pieces and a layered reference composition.
5. Begin Clinic individual assets next.
6. Keep environment/UI assets reusable and individually reviewable; do not create a new runtime scene/UI framework during art production.

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

For visual continuation, start from the **current V2/V3/V4A asset-library checkpoint**, not from the rejected detailed-unicorn/A2-overlay experiments.
