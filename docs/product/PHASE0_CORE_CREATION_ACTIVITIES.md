# Greia Phase-0 Core Creation Activities

**Status:** MANDATORY Phase-0 product requirement  
**Adopted:** 2026-08-10  
**Updated:** 2026-08-19 — Unicode/color-emoji Writing requirement  
**Scope:** first-party child-facing creative Activities shipped in the first user-ready Greia image  
**Implementation state:** **SOURCE-IMPLEMENTED / CURRENT EMOJI TRANCHE UNEXECUTED / HARDWARE-UNPROVEN**

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

## 2. Current source snapshot

Core source includes:

```text
activities/writing/activity.toml
activities/writing/main.py
activities/painting/activity.toml
activities/painting/main.py
src/greia_platform/activity_ui.py
src/greia_platform/typography.py
src/greia_platform/emoji_palette.py
src/greia_platform/pygame_ui.py
```

Relevant provider-free regression source includes:

```text
tests/test_core_creation_activities.py
tests/test_activity_theme_access.py
tests/test_activity_ui.py
tests/test_typography_emoji.py
tests/test_writing_emoji_editing.py
```

The shared SDK/UI surface remains deliberately small. Greia does **not** need a general desktop widget framework to provide responsive child controls, semantic typography, Unicode grapheme handling, color emoji and a bounded curated emoji palette.

### Evidence boundary

The Unicode/color-emoji tranche is committed in source, but its new focused tests and current aggregate source gate have **not executed in an owner-controlled current checkout as part of this work**.

Do not claim yet:

- current-head standalone Activity validator PASS;
- current-head integrated `make verify` PASS;
- installed Noto Color Emoji/package-composition PASS;
- screenshot/visual emoji acceptance;
- emoji-picker usability acceptance;
- touch behavior;
- installed lifecycle/display-session acceptance;
- low-end Acer emoji/font responsiveness/RSS/CPU acceptance.

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

Writing is a pleasant digital sheet of paper for stories, words, letters, lists, little notes, symbols and emoji. It must not feel like a reduced desktop word processor.

A child should be able to open it and begin typing almost immediately. Because many young children communicate visually before or alongside fluent writing, **ordinary Unicode emoji are a first-class Writing capability**, not an optional novelty feature.

## 5. Current interaction

The implemented source currently provides:

- fullscreen child-facing editing;
- large Nunito Sans body text through the Greia typography service;
- Unicode `TEXTINPUT` handling;
- mixed normal text + color emoji rendering;
- Noto Color Emoji fallback through the shared platform typography implementation;
- Unicode extended-grapheme-aware cursor boundaries;
- whole-grapheme Backspace/Delete so ZWJ, flags, skin tones, keycaps and combining sequences are not torn apart;
- grapheme-aware wrapping, hit-testing, vertical column movement, previews and length truncation;
- a large visual emoji button and bounded Greia emoji picker using the shared `EmojiPalette` model;
- picker insertion as ordinary Unicode text, never proprietary Greia emoji tokens;
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

### Emoji product rule

Emoji are expressive text content; they are not replacements for Greia's controlled system iconography. The Writing picker may offer `🏠`, arrows, hearts or other symbols as content a child can insert into a document, but the real Greia Home/Back/audio/settings controls remain semantic Greia UI assets.

The curated picker is intentionally bounded and child-friendly. Rendering is not limited to that curated set: valid emoji received through normal text input or loaded from a saved UTF-8 document should still render through the platform fallback path when the bundled emoji font supports them.

### Current persistence model

```text
KV index:      documents.index.v1
private files: documents/<uuid>.txt
encoding:      UTF-8
library bound: 120 indexed documents
text bound:    120,000 Python/Unicode code points, truncated only at a grapheme boundary
undo bound:    128 recent edit operations
```

Emoji remain ordinary UTF-8 Unicode strings in the document. Writing must never persist renderer glyph IDs, font paths, image filenames or private replacement tokens as the authoritative text representation.

The bounds are Activity UX safeguards beneath the platform’s authoritative Storage quota.

### Still open for product acceptance

The current source still needs executed/visual review for:

- caret/wrapping behavior with long real child text;
- required emoji families including simple emoji, variation selectors, skin-tone modifiers, ZWJ sequences, flags and keycaps;
- no missing/tofu glyphs for the accepted specimen on the installed image;
- emoji picker fit/readability/click accuracy at 800×600 and 1024×600;
- acceptable first-emoji and cached-emoji rendering latency;
- bounded emoji glyph/surface cache behavior;
- installed disk/RSS impact of the emoji font and grapheme dependency on the C0/Acer floor;
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
- a ribbon full of formatting commands;
- a desktop-scale exhaustive emoji browser with thousands of tiny cells.

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

Writing and Painting are reference consumers of reusable Greia child-UI primitives.

They share real needs for:

- large semantic icon buttons;
- selected/unselected tool state;
- child-sized toolbar geometry;
- automatic viewport scaling/safe geometry;
- cached semantic icons;
- simple visual symbols;
- theme-aware common surfaces.

Writing additionally proves that common text needs belong in shared platform primitives:

- semantic Nunito font roles;
- color-emoji fallback;
- Unicode grapheme segmentation;
- bounded emoji surface caching;
- a reusable curated emoji palette model.

The extraction rule remains evidence-driven:

1. build real Activities;
2. identify genuine duplication;
3. extract the smallest stable shared primitive;
4. measure it on the low-end reference hardware;
5. update `skills/greia-activity-authoring/SKILL.md` when it becomes canon.

Do not invent a speculative retained widget tree, layout DSL, animation framework or mini desktop toolkit.

## 11. Theme/security rule

Ordinary Activities must not receive `customization.manage` merely to look like Greia.

Visual theme context is a read-only presentation concern; mutation remains separately privileged. Exact current theme-snapshot/environment behavior is source-owned and documented in the Activity authoring skill/HANDOVER.

Typography/emoji likewise does not grant filesystem authority. An Activity uses the shared platform text path; it does not receive permission to crawl `/usr/share/fonts` or alter system fonts.

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

Writing naturally requires a keyboard for ordinary typing, while its emoji picker provides a large visual route to common expressive symbols. Painting must not require a keyboard for normal drawing.

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

Writing additionally must:

- default to large readable text;
- render ordinary Unicode emoji in color through the Greia fallback stack where supported;
- keep grapheme clusters atomic for cursor movement, deletion, wrapping and hit testing;
- preserve emoji as standard UTF-8 data;
- provide a large, bounded, child-usable common-emoji picker;
- pass the representative emoji sequence specimen and low-resource measurements.

Painting additionally must provide responsive drawing with bounded undo and no per-frame durable encoding/writes.

---

## 14. Scheduling relative to the active remediation plan

R7 remains the active blocking architecture/evidence phase. This creative-app/typography work does **not** select a compositor, migrate production away from Xorg, weaken the sandbox, or claim hardware acceptance.

The source tranche can proceed in parallel because it consumes already-established Activity/lifecycle/Storage/UI contracts and gives R7/final certification useful real workloads:

- sustained keyboard/text/emoji input;
- color-glyph composition and caching;
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

Exact manifest IDs, storage schemas, typography/grapheme APIs and reusable UI implementation details are source-owned and summarized in `skills/greia-activity-authoring/SKILL.md`; this document remains the product/UX requirement and acceptance contract rather than a duplicate implementation specification.
