# Greia Phase-0 Core Creation Activities

**Status:** MANDATORY Phase-0 product requirement  
**Adopted:** 2026-08-10  
**Scope:** first-party child-facing creative Activities shipped in the first user-ready Greia image  
**Implementation state:** **SOURCE-IMPLEMENTED FIRST TRANCHE / UNEXECUTED / HARDWARE-UNPROVEN**

---

## 1. Product requirement

Greia must be useful as a creative computer from the beginning, not only as a launcher for games.

The first user-ready Phase-0 Greia image MUST include two first-party built-in Activities:

1. **Writing** — a simple child-first text-editing Activity;
2. **Painting** — a simple child-first painting/drawing Activity.

These are baseline Greia capabilities, not optional examples and not post-Phase-0 ecosystem additions.

They must use the same Activity, lifecycle, storage, profile, trust, backup, performance and display/session contracts as every other Activity. Built-in origin is not permission to bypass Greia platform architecture.

Current stable source identities are:

```text
org.greia.writing
org.greia.painting
```

Treat those IDs as durable identity from this point unless an explicit migration decision supersedes them.

---

## 2. Current source snapshot — 2026-08-10

Source now exists at:

```text
activities/writing/activity.toml
activities/writing/main.py
activities/painting/activity.toml
activities/painting/main.py
src/greia_platform/activity_ui.py
```

Provider-free regression source has been added at:

```text
tests/test_core_creation_activities.py
tests/test_activity_theme_access.py
tests/test_activity_ui.py
```

The new shared SDK surface is deliberately small. `activity_ui.py` currently provides only reusable 1024×600-first metrics, cached semantic-icon scaling, large rounded icon buttons, a few shared symbols and a bounded RGB helper. It is **not** a general widget framework.

### Evidence boundary

The current tranche has been source-reviewed and committed, but the new tests and validators have **not executed in a current real checkout** as part of this work.

Do not claim yet:

- standalone Activity validator PASS;
- integrated `make verify` PASS at the new branch head;
- real storage-broker/autosave acceptance;
- screenshot/visual acceptance;
- touch behavior;
- installed lifecycle/display-session acceptance;
- low-end Acer responsiveness/RSS/CPU acceptance.

Those remain required before Phase-0 product closure.

---

## 3. Shared product character

Both Activities should feel immediately understandable to a young child.

The intended character is:

- **simple** — only controls that materially help the core task;
- **essential** — no office-suite or professional-graphics feature creep;
- **large** — large targets, large text, generous spacing;
- **cute and warm** — playful Greia visual language without clutter;
- **fast** — immediate usable surface on low-end hardware;
- **forgiving** — bounded undo and safe recovery;
- **offline-first** — normal use and saving require no network;
- **profile-scoped** — each child owns their own creations;
- **automatic about saving** — no traditional Save dialog as a child workflow;
- **Linux-invisible** — no filesystem picker, desktop path, terminal or native desktop UI.

At 1024×600 the UI must remain comfortable and uncluttered.

A quota/library limit may refuse a new creation, but Greia must **never silently evict or delete older child work** merely to make room.

---

# Part I — Writing

## 4. Goal

Writing is a pleasant digital sheet of paper for stories, words, letters, lists and little notes. It must not feel like a reduced desktop word processor.

A child should be able to open it and begin typing almost immediately.

## 5. Current first-tranche interaction

The implemented source currently provides:

- fullscreen child-facing editing;
- large default body text (approximately 42 px at the 1024×600 reference scale);
- Unicode `TEXTINPUT` handling;
- multiline text;
- visible insertion caret;
- click-to-place caret;
- Left/Right/Up/Down and Home/End navigation;
- Backspace/Delete/Enter;
- soft wrapping and vertical scrolling;
- bounded **128-edit operation undo** with a large visible undo control;
- optional Ctrl/Cmd-Z keyboard alternative;
- a visual document gallery;
- a large New control;
- automatic debounced saving;
- save on document/activity transitions;
- visible saved/dirty/save-failure state;
- Greia semantic icons and canonical theme colors;
- profile-scoped Greia Storage only.

Writing undo stores only the changed fragments and cursor positions for each edit, not full-document snapshots. This keeps the history meaningfully bounded even for long documents on the low-memory reference class.

The source deliberately does **not** contain a formatting ribbon, file dialog or Linux path workflow.

### Current persistence model

```text
KV index:      documents.index.v1
private files: documents/<uuid>.txt
encoding:      UTF-8
library bound: 120 indexed documents
text bound:    120,000 Unicode code points per document
undo bound:    128 recent edit operations
```

The bounds are Activity UX safeguards beneath the platform’s authoritative Storage quota.

### Still open for product acceptance

The current first tranche still needs executed/visual review for:

- caret/wrapping behavior with long real child text;
- selection behavior if it proves necessary for comfortable editing;
- international keyboard/input-method behavior;
- autosave failure/quota UX;
- gallery scaling beyond the first visible page;
- actual 1024×600 visual comfort;
- installed keyboard/pointer behavior;
- low-end latency and memory.

Text-size choices are **not** required merely to imitate a word processor. Large readable text by default is the product requirement; add size choices only if child testing shows they materially improve the experience without clutter.

## 6. Deliberately not Phase-0 Writing goals

Do not add by default:

- font-family choosers;
- page setup/margins;
- headers/footers;
- tables/columns;
- tracked changes;
- print-dialog UI;
- arbitrary Linux file open/save;
- cloud documents;
- spelling/grammar red-underlines as a default child experience;
- a ribbon full of formatting commands.

Future educational writing features can be added after the essential editor is excellent.

---

# Part II — Painting

## 7. Goal

Painting is a fast, delightful fullscreen drawing surface where a child can draw immediately with a mouse/touchpad and, once proven, touch-capable devices.

The canvas must dominate the screen.

## 8. Current first-tranche interaction

The implemented source currently provides:

- fullscreen drawing;
- a large canvas occupying most of 1024×600;
- ten cheerful fixed colors;
- three large brush sizes;
- eraser;
- bounded undo;
- New drawing;
- visual drawing gallery;
- direct freehand stroke feedback;
- pointer-point decimation to avoid wasteful event-density growth;
- automatic debounced saving;
- save on drawing/activity transitions;
- visible saved/dirty/save-failure state;
- PNG portable creation files;
- Greia semantic icons and canonical theme colors;
- profile-scoped Greia Storage only.

### Bounded undo design

Painting does **not** keep unlimited full-canvas snapshots.

It retains up to 24 recent strokes. When the undo window fills, the oldest stroke is folded permanently into a base canvas and removed from undo history. The visible artwork remains intact while memory growth stays bounded.

PNG encoding happens at save boundaries, not on every pointer event or frame.

### Current persistence model

```text
KV index:      paintings.index.v1
private files: paintings/<uuid>.png
library bound: 48 indexed paintings
undo bound:    24 recent strokes
```

The current Greia Storage policy remains authoritative over namespace/file quotas.

### Still open for product acceptance

The current first tranche still needs executed/visual review for:

- stroke smoothness at realistic pointer speed;
- touch event semantics rather than assuming mouse emulation;
- eraser feel;
- autosave/quota failure UX;
- gallery scaling beyond the first visible page;
- resolution-change behavior for existing PNGs;
- actual 1024×600 visual comfort;
- low-end canvas latency/RSS/CPU;
- installed display-session return/crash/forced-stop behavior.

## 9. Deliberately not Phase-0 Painting goals

Do not add professional graphics complexity such as:

- layers;
- masks;
- transforms;
- filters;
- vector paths;
- arbitrary image-file browser;
- desktop-style menus;
- huge brush libraries;
- unbounded undo;
- cloud synchronization.

Cute stamps/stickers can be considered later only if they remain performant and do not obscure the core drawing experience.

---

# Part III — Shared Greia UI/reference role

## 10. These are reference Activities

Writing and Painting are the first serious reference consumers of reusable Greia child-UI primitives.

They already share real needs for:

- large semantic icon buttons;
- selected/unselected tool state;
- child-sized toolbar geometry;
- resolution-aware 1024×600 metrics;
- cached semantic icons;
- simple visual symbols;
- theme-aware common surfaces.

The extraction rule is evidence-driven:

1. build real Activities;
2. identify genuine duplication;
3. extract the smallest stable shared primitive;
4. measure it on the low-end reference hardware;
5. update `skills/greia-activity-authoring/SKILL.md` when it becomes canon.

Do not invent a speculative retained widget tree, layout DSL, animation framework or mini desktop toolkit.

## 11. Theme/security rule

Ordinary Activities must not receive `customization.manage` merely to look like Greia.

Current SDK behavior is intentionally least-privilege:

- ordinary Activities calling `get_theme()` receive Greia’s canonical default resolved palette;
- trusted Activities already granted profile customization authority may receive the actual resolved child customization state;
- ordinary Activities are not given raw access to the child’s wallpaper/customization files for cosmetic consistency.

A future read-only personalized theme snapshot may be added deliberately without widening filesystem authority.

---

## 12. Accessibility and input

Both Activities must ultimately:

- work at 1024×600;
- avoid tiny hit targets;
- support the reference pointer/touchpad path without assuming tap-to-click;
- use keyboard where the task naturally requires it;
- provide visual state in addition to optional sound;
- avoid color as the sole indication of important state where practical;
- never trap the child because an optional input capability is missing.

Writing naturally requires a keyboard for typing. Painting must not require a keyboard for normal drawing.

Touch is currently declared as an optional capability but remains **UNPROVEN** until real event/input acceptance executes.

---

## 13. Definition of Phase-0 done

The requirement is not satisfied merely because source folders exist.

Before the first user-ready Phase-0 image can be considered complete, both Activities must:

- ship as first-party built-in Activities;
- validate under the current manifest/runtime policy;
- preserve their stable canonical Activity IDs;
- use Greia lifecycle READY/STOP semantics;
- use profile-scoped Greia Storage for creations;
- preserve child work automatically and recoverably;
- never silently evict older creations to hide quota pressure;
- remain fully functional offline;
- expose no Linux filesystem/desktop UI in the child path;
- be genuinely usable at 1024×600;
- use large, simple child controls;
- meet low-end performance/resource expectations on the Acer reference class;
- survive exit/relaunch without losing accepted edits/drawings;
- participate in logical backup/restore when `.greiabackup` is implemented;
- pass provider-free logic/storage tests;
- pass real visual/input acceptance on reference hardware;
- leave Greia Shell valid after normal exit, crash and forced return.

Writing additionally must default to large readable text and make ordinary writing comfortable.

Painting additionally must provide responsive drawing with bounded undo and no per-frame durable encoding/writes.

---

## 14. Scheduling relative to the active remediation plan

R7 remains the active blocking architecture/evidence phase. This creative-app work does **not** select a compositor, migrate production away from Xorg, weaken the sandbox, or claim hardware acceptance.

The first source tranche can proceed in parallel because it consumes already-established Activity/lifecycle/Storage contracts and gives R7/final certification useful real workloads:

- sustained keyboard/text input;
- sustained pointer drawing;
- autosave/checkpoint behavior;
- Activity lifecycle/forced return;
- low-end rendering performance;
- shared child UI primitives;
- genuine child-created data for future backup testing.

No Phase-0 certification is allowed until both the R7 platform requirements and these core creative Activities meet their applicable acceptance criteria.

---

## 15. Maintenance rule

Update this document when the accepted Phase-0 product scope changes materially.

Exact manifest IDs, storage schemas, SDK behavior and reusable UI APIs are source-owned and summarized in `skills/greia-activity-authoring/SKILL.md`; this document remains the product/UX requirement and acceptance contract rather than a duplicate implementation specification.
