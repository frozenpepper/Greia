# Greia — Standalone Engineering Handover

**Date:** 2026-08-20  
**Version family:** `0.13.x` development  
**Repository:** `frozenpepper/Greia` (private)  
**Canonical/default/development branch:** `main`  
**Primary blocking platform phase:** **R7 — Direct graphics/session/input architecture**  
**Current cross-cutting work:** device-language/localization + child UX + R13B transactional updates + Activity Simulator/emoji/Writing + **active Greia visual-foundation workstream (A2)**  
**External Parent HTML runtime revision pinned by Greia:** `frozenpepper/Greia-Parent-App-Html@519651a5931269ed4275324f2a87ad3f0d08a3f6`

This file is intentionally a **current-state continuation contract**. Detailed chronology belongs in append-only active plans/reviews. Exact APIs and limits remain source-owned.

---

## 1. Repository / execution rules

- `main` is the owner-required development/integration branch. Do not create branches unless the owner explicitly changes policy.
- GitHub is canonical persistence; commit coherent work as it proceeds.
- Do **not** use, query, trigger, rerun, inspect or download GitHub-hosted Actions without explicit owner authorization for that specific hosted execution.
- Never convert committed tests/assets into PASS/approved evidence merely because files exist.
- Blocking implementation plan: `docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md`.
- Current art/visual plan: `docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md`.
- R7 remains the first incomplete blocking architecture phase. Cross-cutting product/art work does not close or skip R7.
- Substantive visual work must update the art-plan checkpoint + append-only ledger.
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

# 3. Active Greia visual-foundation workstream — A2

Canonical continuity:

```text
docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
docs/design/GREIA_VISUAL_STYLE_GUIDE.md
docs/design/GREIA_CONSTRAINT_NATIVE_CHARACTER_GRAMMAR.md
docs/design/GREIA_CHARACTER_EXPRESSIONS_AND_MOTION.md
skills/greia-visual-authoring/SKILL.md
assets/visual/README.md
assets/visual/library_v0.1.toml
assets/visual/specimens/a1/review.html
assets/visual/specimens/a2/review.html
assets/visual/specimens/a2/base_motion_v0.1.toml
```

## 3.1 A1 is closed at design/static-style scope

The owner reviewed the first constraint-native cast direction and explicitly asked to move forward. Record that as approval of:

- **Puff** — one soft round/oval/fluffy main mass;
- **Bean** — one compact upright rounded/drop mass;
- **Cutout Critter** — intentional felt/sticker/paper-cut layering;
- **Object Friend** — pedagogical object remains primary and gains a face/tiny optional appendages;
- face/expression-first character design;
- whole-body motion rather than anatomy-heavy rigs;
- Lilli, Nino, Tito and Momo as **static style anchors**.

Working anchors:

- **Lilli** — unicorn Puff;
- **Nino** — owl Bean;
- **Tito** — fox Puff;
- **Momo** — friendly monster Puff.

`docs/design/GREIA_VISUAL_STYLE_GUIDE.md` now contains the accepted constraint-native language. `docs/design/GREIA_CONSTRAINT_NATIVE_CHARACTER_GRAMMAR.md` is accepted rather than candidate.

The library records explicit approval scope. `assets/visual/library_v0.1.toml` remains:

```text
runtime_consumed = false
```

and the four current masters are approved only as:

```text
approval_scope = "static_style_anchor"
runtime_ready = false
```

This does **not** mean frozen final release art, runtime asset packaging, simulator acceptance or physical/C0 acceptance.

## 3.2 A2 expression and semantic-motion foundation

A2 now defines persistent expression semantics:

```text
neutral
happy
excited
surprised
sleepy
sad_gentle
thinking
proud
silly
```

plus transient `blink`.

Important emotional rule: ordinary educational mistakes never use anger, shame or disappointed-at-the-child imagery. An early local Lilli `sad_gentle` treatment was revised because brow angles could read as irritation/disappointment; future variants must preserve the softer reading.

Base Animation Set v0.1:

```text
idle_bounce      nominal 2.00 s
blink            nominal 0.22 s
happy_hop        nominal 0.90 s
celebrate_pop    nominal 1.15 s
surprised_wobble nominal 0.72 s
sleepy_sway      nominal 2.40 s
```

Exact phase/amplitude/static-fallback rules are in:

```text
docs/design/GREIA_CHARACTER_EXPRESSIONS_AND_MOTION.md
assets/visual/specimens/a2/base_motion_v0.1.toml
```

The review harness:

```text
assets/visual/specimens/a2/review.html
```

demonstrates all six motions on Lilli/Puff, Nino/Bean and Object Friend number 3 using face-state overlays + bounded whole-body transforms. Object Friend deformation is deliberately reduced so the learning glyph remains recognizable.

## 3.3 Runtime boundary retained

`src/greia_platform/ui_motion.py` was inspected before proposing runtime animation. Its cheap immutable renderer-neutral mathematical sampling is the preferred architectural precedent.

The current `MotionSample` remains UI-control-oriented and does not model character rotation, anisotropic squash/stretch, semantic face state or optional attachment/FX channels. **No runtime character-motion API was added in A2.** Do not turn the HTML design harness into runtime authority or create a parallel per-Activity animation framework.

Runtime/library integration remains A7 and requires architecture review.

## 3.4 Current visual evidence and next exact step

Current A1 evidence:

```text
OWNER REVIEW
DESIGN SPEC
SOURCE
DESKTOP VISUAL REVIEW at 256 / 128 / 64
```

Current A2 evidence:

```text
DESIGN SPEC
SOURCE
DESKTOP VISUAL REVIEW of expression variants and representative keyframes
```

Not claimed:

- A2 owner acceptance;
- simulator/reference-viewport A2 acceptance;
- runtime-motion performance acceptance;
- Acer/Pi physical visual acceptance.

**Next exact visual action:** review/refine `assets/visual/specimens/a2/review.html`, obtain appropriate simulator/reference-viewport clarity evidence, then close A2 if the motion/expression semantics remain charming/readable across Puff, Bean and Object Friend. After A2, begin A3 shared character/Object Friend library expansion. Runtime animation integration remains deferred.

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

1. Review/refine A2 expressions/motions using `assets/visual/specimens/a2/review.html`.
2. Preserve static fallbacks and conservative Object Friend deformation.
3. Obtain simulator/reference-viewport evidence appropriate to A2 without inventing runtime architecture.
4. Close A2 only when semantic motion works across Puff, Bean and Object Friend.
5. Begin A3: reusable standard creatures + Object Friends + metadata/provenance.
6. Do not implement the runtime character-motion/library layer before the A7 architecture review.

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
- Greia character art defaults to the accepted constraint-native visual language unless a bespoke asset has a deliberate reviewed reason to differ;
- static style-anchor approval is not runtime/release/physical approval;
- after each substantive art session update the active art-plan checkpoint + append-only ledger.

For visual continuation, start from the **A2 expression/motion review gate**, not from the rejected detailed-unicorn pipeline.
