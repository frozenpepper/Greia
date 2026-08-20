# Greia — Standalone Engineering Handover

**Date:** 2026-08-20  
**Version family:** `0.13.x` development  
**Repository:** `frozenpepper/Greia` (private)  
**Canonical/default/development branch:** `main`  
**Primary blocking platform phase:** **R7 — Direct graphics/session/input architecture**  
**Current cross-cutting work:** device-language/localization + child UX + R13B transactional updates + Activity Simulator/emoji/Writing + **active Greia visual-foundation workstream (A1)**  
**External Parent HTML runtime revision pinned by Greia:** `frozenpepper/Greia-Parent-App-Html@519651a5931269ed4275324f2a87ad3f0d08a3f6`

This file is intentionally a **current-state continuation contract**. Detailed chronological implementation history remains in the append-only active plans and dated reviews rather than being duplicated indefinitely here. Exact APIs and limits remain source-owned.

---

## 1. Repository / execution rules

- `main` is the owner-required development/integration branch. Do not create branches unless the owner explicitly changes policy.
- GitHub is canonical persistence; commit coherent work as it proceeds.
- Do **not** use, query, trigger, rerun, inspect or download GitHub-hosted Actions without explicit owner authorization for that specific hosted execution.
- Never convert committed tests/assets into PASS/approved evidence merely because files exist.
- Blocking active implementation plan: `docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md`.
- Current art/visual workstream plan: `docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md`.
- R7 remains the first incomplete blocking architecture phase. Cross-cutting product/art work does not close or skip R7.
- Substantive visual work must update the art plan checkpoint + append-only ledger.
- `skills/greia-visual-authoring/SKILL.md` is mandatory for Greia visual-asset/art work.

---

# 2. Evidence boundary

The latest retained owner-controlled aggregate source gate predating later device-language/localization/art work remains:

```text
make verify:                         781 PASS
project & 10 activities validation:  PASS
footprint & shell check:             PASS
```

Later source is not retroactively covered by that gate. In particular:

- device-language selection/persistence;
- later English/Italian Activity localization;
- subsequent child-UX work;
- current visual-foundation contracts/specimens;
- later system-update/simulator changes where applicable;

require their own current-head verification before any broad current PASS claim.

No current-head aggregate PASS, rebuilt-language-installer physical PASS, R13B activation/rollback PASS, current-head QEMU A/B PASS, Pi A/B PASS, or physical Greia art-performance PASS is claimed here.

Retained physical history from 2026-08-19: a fresh `legacy-x86-i686-dev` syslinux/FAT32 installer booted on the reference Acer Aspire One, installation completed, and the installed OS reached the launcher. Later source requires a rebuilt image before that physical result extends to it.

---

# 3. Active Greia visual-foundation workstream — A1

Canonical continuity:

```text
docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
skills/greia-visual-authoring/SKILL.md
assets/visual/README.md
assets/visual/library_v0.1.toml
```

## 3.1 Accepted working direction

Greia’s default character/art architecture is now **constraint-native**, rather than detailed traditional articulated animals:

- **Puff** characters — one soft round/oval/fluffy main mass;
- **Bean** characters — one compact upright rounded mass;
- **Cutout Critters** — deliberate felt/sticker/paper-cut layering;
- **Object Friends** — pedagogical objects remain primary and receive faces/tiny optional appendages;
- face/expression-first design;
- whole-body squash/bounce/wobble/hop motion rather than anatomy-heavy rigs;
- chunky illustrated props;
- cozy storybook/felt-board/toy-diorama scenes;
- tactile rounded UI and a small shared FX vocabulary.

Working style anchors:

- **Lilli** — unicorn Puff;
- **Nino** — owl Bean;
- **Tito** — fox Puff;
- **Momo** — friendly monster Puff.

Base semantic motion seed:

```text
idle_bounce
blink
happy_hop
celebrate_pop
surprised_wobble
sleepy_sway
```

The earlier detailed-character experiments remain useful **REJECTED EXPERIMENT** evidence. Do not resume one-shot sprite-sheet generation, automatic detailed quadruped decomposition, or after-the-fact full-anatomy vector recreation as the default pipeline without materially new evidence.

## 3.2 Current A1 source

Candidate grammar:

```text
docs/design/GREIA_CONSTRAINT_NATIVE_CHARACTER_GRAMMAR.md
```

Candidate specimen set:

```text
assets/visual/specimens/a1/lilli.svg
assets/visual/specimens/a1/nino.svg
assets/visual/specimens/a1/tito.svg
assets/visual/specimens/a1/momo.svg
assets/visual/specimens/a1/cutout_critter.svg
assets/visual/specimens/a1/object_friend_3.svg
assets/visual/specimens/a1/review.html
```

Inventory state is recorded in:

```text
assets/visual/library_v0.1.toml
```

The inventory remains explicitly:

```text
runtime_consumed = false
```

so this work does **not** introduce or imply a runtime asset-loader API.

## 3.3 Current visual evidence

Evidence scope:

```text
DESIGN SPEC
SOURCE
DESKTOP VISUAL REVIEW at 256 / 128 / 64
```

The SVGs were locally rasterized and visually inspected at those sizes. The four named characters remained distinct/readable in that desktop review. An initial CSS typo that prevented the intended outline rules from applying was caught by inspection, corrected, re-rendered, and corrected source was committed.

This does **not** mean:

- owner visual approval;
- canonical/release character approval;
- simulator visual acceptance;
- Acer/Pi physical visual acceptance;
- motion runtime acceptance.

## 3.4 Current owner-review gate

A1 is intentionally **not closed**.

Next exact visual action:

1. owner reviews `assets/visual/specimens/a1/review.html`;
2. record Lilli/Nino/Tito/Momo as approved, revised/superseded, or rejected;
3. revise the candidate grammar if the visual review exposes weaknesses;
4. promote accepted rules into `docs/design/GREIA_VISUAL_STYLE_GUIDE.md`;
5. update visual-library statuses;
6. close A1;
7. only then begin A2 expression/motion standardization.

Relevant source commit:

```text
b3cf90c109eae14b2013ad62f69c64dccaa12e8a  art: add A1 constraint-native character specimens
```

The active plan was then updated to record this A1 gate.

---

# 4. Device-default language selection / localization

Architecture/product authorities:

```text
docs/adr/0028-platform-and-activity-localization-language-context.md
docs/product/SYSTEM_LANGUAGE_AND_LOCALIZATION.md
docs/reviews/2026-08-19_DEVICE_LANGUAGE_SELECTION_AND_PERSISTENCE.md
```

Current implemented direction:

```text
installer first-screen locale choice
        ↓
InstallRequest.locale
        ↓
/etc/greia-os/install-record.json   initial historical choice
        ↓
SystemLanguageStore effective default
        ↑
/var/lib/greia-system-settings/language.json   later Parent override
```

English is default. The canonical selectable registry currently includes:

```text
en, it, es, de, fr, zh-CN, pt, ar, hi, id, bn, sw
```

`zh` canonicalizes to `zh-CN`.

The installer, hidden Parent panel and external Parent client must consume the same Greia-owned language registry rather than maintain independent lists.

Important evidence distinction: **selectable does not mean fully translated**. English/Italian Activity resources exist in current source; complete translation/font/shaping/RTL acceptance for all selectable languages remains separate work. Arabic in particular requires real RTL/shaping/layout acceptance; CJK/Arabic/Indic/Bengali support requires reviewed platform script-font coverage.

Device-language focused source tests are committed but current-head execution must be recorded before claiming current PASS.

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

Therefore these are still not implemented/accepted on the active production layout:

```text
A/B inactive-slot activation
boot-health confirmation
automatic rollback
```

No in-place active-root fallback is authorized merely for convenience.

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

Art/asset work is allowed to advance independently where it does not bypass these architecture prerequisites.

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

1. **Owner review the current A1 static cast** using `assets/visual/specimens/a1/review.html`.
2. Record explicit disposition for Lilli/Nino/Tito/Momo.
3. Revise if needed rather than polishing a rejected construction indefinitely.
4. Promote approved grammar into the living style guide.
5. Close A1 and begin A2: expressions + normalized semantic motions across Puff, Bean and Object Friend.
6. Do not build a runtime motion framework before checking existing Greia motion/runtime seams.

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
- source/simulator/physical evidence scopes remain distinct;
- Greia character art defaults to the constraint-native visual language unless a bespoke asset has a deliberate reviewed reason to differ;
- committed candidate art is not automatically approved;
- after each substantive art session update the active art plan checkpoint + append-only ledger.

For visual continuation, start from the **A1 owner-review gate**, not from the rejected detailed-unicorn pipeline.
