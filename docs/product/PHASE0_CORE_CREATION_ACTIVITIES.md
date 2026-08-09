# Greia Phase-0 Core Creation Activities

**Status:** MANDATORY Phase-0 product requirement  
**Adopted:** 2026-08-10  
**Scope:** first-party child-facing creative Activities shipped in the first user-ready Greia image  
**Implementation state:** REQUIRED / NOT YET IMPLEMENTED

---

## 1. Product requirement

Greia must be useful as a creative computer from the beginning, not only as a launcher for games.

The first user-ready Phase-0 Greia image MUST include two first-party built-in Activities:

1. a **simple text-editing/writing Activity**;
2. a **simple painting/drawing Activity**.

These are baseline Greia capabilities, not optional example apps and not post-Phase-0 ecosystem additions.

They must follow the same Activity, lifecycle, storage, profile, trust, backup, performance and display/session contracts as other Greia Activities. Being built in does not permit bypassing the platform architecture.

Working product names and stable Activity IDs are intentionally not fixed by this document. Choose them before implementation and then treat the IDs as durable identity.

---

## 2. Shared product character

Both Activities should feel immediately understandable to a young child.

The intended character is:

- **simple** — only controls that materially help the core task;
- **essential** — no desktop-office or professional-graphics feature creep;
- **large** — large targets, large text, generous spacing;
- **cute and warm** — playful Greia visual language without visual clutter;
- **fast** — immediate usable surface on the low-end reference machine;
- **forgiving** — easy undo/recovery and no fragile modal workflows;
- **offline-first** — all normal work and saving works with no network;
- **profile-scoped** — each child's creations belong to that Greia profile;
- **automatic about saving** — avoid making a young child understand a traditional Save dialog;
- **Linux-invisible** — no filesystem picker, desktop path, terminal, native file-dialog or host clipboard assumption as a core workflow.

At 1024×600 the UI must remain comfortable and uncluttered.

---

# Part I — Writing Activity

## 3. Goal

Provide a pleasant place for a child to type stories, words, letters, lists and little notes without exposing a desktop word processor.

The child should be able to open it and begin typing almost immediately.

## 4. Phase-0 interaction model

The default editing surface should use **large text**. The exact font size is an implementation/detail to be tested at 1024×600, but normal first launch must not resemble small desktop-editor text.

A reasonable design target is approximately 32–40 px for ordinary body text on the 1024×600 reference display, with only a very small number of child-friendly size choices.

The primary screen should devote the overwhelming majority of space to the document.

### Core controls

Keep the persistent controls to a deliberately small set, for example:

- return/back to Greia or document gallery;
- new document;
- undo;
- text size, preferably a compact 2–3-state control;
- optional small text-color palette only if it remains simple and useful.

Do not add a permanent ribbon full of formatting commands.

### Required editing behavior

The Phase-0 Activity should support the ordinary mechanics needed to write comfortably:

- Unicode text input;
- multiline text;
- insertion cursor;
- mouse/pointer placement;
- keyboard arrows/navigation;
- Backspace/Delete;
- Enter/new lines;
- sensible selection/edit behavior where practical;
- text wrapping;
- scroll within the document when content exceeds the visible page;
- undo for recent editing actions.

Use the platform's current input/runtime facilities rather than depending on X11-specific APIs.

### Deliberately not Phase-0 goals

Do not turn this into a miniature office suite. Phase 0 does not require:

- font-family chooser;
- margins/page setup;
- headers/footers;
- tables;
- columns;
- complex rich-text styles;
- tracked changes;
- print-dialog UI;
- arbitrary Linux file open/save;
- cloud documents;
- spelling/grammar red-underlines as a default child experience.

Future educational writing features can be added deliberately after the essential editor is excellent.

---

## 5. Documents and saving

The Activity should own a simple visual document gallery rather than a filesystem browser.

A document can be represented by a large card using a child-safe preview such as:

- first words / title when available;
- modified time expressed through the UI rather than raw filesystem metadata;
- optional simple icon/thumbnail.

Saving should be automatic through Greia Storage.

Recommended behavior:

- debounce ordinary text-state writes rather than writing on every key event;
- force a durable save on meaningful boundaries such as document switch, Activity exit/stop request and explicit new-document transitions;
- use versioned portable JSON-compatible text metadata/state;
- never persist Python/Pygame/native objects;
- preserve documents independently of package uninstall according to Greia's normal Activity-data rules.

The future `.greiabackup` path must include these documents as child creations.

Parent-controlled export to standard text/document formats can be added through a platform-owned workflow later; it must not require exposing Linux directories to the child.

---

# Part II — Painting Activity

## 6. Goal

Provide a fast, delightful fullscreen drawing canvas where a child can draw immediately with a mouse, touchpad or touch device when available.

The canvas should dominate the screen.

## 7. Phase-0 interaction model

A good initial tool set is intentionally small:

- brush;
- eraser;
- a compact palette of cheerful colors;
- a few large brush sizes;
- undo;
- new/clear drawing with safe confirmation/recovery;
- gallery/back.

Approximately 8–12 well-chosen colors and 3 brush-size choices are preferable to a professional color picker and dozens of tools.

Use large icon-led controls. Labels may supplement icons where useful, but ordinary operation should not depend unnecessarily on reading.

### Required drawing behavior

- smooth freehand strokes;
- pointer support;
- touch support when the capability is available;
- immediate visual feedback;
- stable drawing while moving quickly;
- erasing that is easy to understand;
- bounded undo;
- automatic durable saving;
- visual gallery of saved drawings;
- graceful behavior if optional audio/touch capabilities are unavailable.

### Deliberately not Phase-0 goals

Do not add professional graphics complexity such as:

- layers;
- masks;
- transforms;
- filters;
- vector paths;
- arbitrary image-file browser;
- desktop-style menus;
- huge brush libraries;
- unbounded undo history;
- background cloud synchronization.

Cute stamps/stickers may become a later enhancement if they remain performant and do not obscure the core drawing experience.

---

## 8. Painting storage/performance model

A drawing is child-created durable data and should use Greia Storage rather than an arbitrary profile path.

Recommended portable representation:

- PNG (or another explicitly accepted portable raster format) for the rendered creation;
- small JSON-compatible metadata for creation ID/title/time/tool state when needed.

Avoid expensive work in the frame loop:

- do not encode PNG every frame;
- do not save on every pointer-motion event;
- do not reload/decode palette/tool assets repeatedly;
- do not create unbounded full-canvas undo snapshots.

Save at bounded meaningful boundaries, especially stroke completion and Activity transitions, using a debounce/checkpoint strategy that protects creations without turning storage into hot-loop work.

Undo must have an explicit memory bound suitable for the low-resource Acer floor. A command/stroke history plus occasional bounded checkpoints is preferable to unlimited full-surface copies.

---

# Part III — Shared Greia UI/reference role

## 9. These are reference Activities

The writing and painting Activities should be developed as the first serious **reference consumers of reusable Greia child-UI primitives**.

They naturally exercise repeated needs such as:

- large semantic icon buttons;
- selected/unselected tool state;
- child-sized toolbars;
- palette controls;
- gallery/document cards;
- large readable typography;
- focus/cursor feedback;
- undo/temporary feedback;
- safe destructive-action confirmation;
- simple transitions;
- cached fonts/images/icons;
- resolution-aware 1024×600 layout.

The current repository does **not** yet have an accepted general-purpose Activity widget toolkit. Do not invent a large abstract framework before these real Activities expose the reusable seams.

Instead:

1. implement the first Activities cleanly against current Greia APIs;
2. identify genuinely duplicated, stable, performance-sensitive visual/input primitives;
3. extract the smallest reviewed shared Greia UI library that improves both Activities and future ones;
4. benchmark it on the low-end reference hardware;
5. update `skills/greia-activity-authoring/SKILL.md` when that shared library becomes accepted canon.

The goal is reuse without speculative framework-building.

---

## 10. Visual design canon

Both Activities should look like they belong to Greia.

Use:

- Greia semantic icons where appropriate;
- the resolved Greia theme for common platform surfaces where it improves consistency;
- rounded, generous child-sized controls;
- restrained animation;
- strong visual selection state;
- warm, playful details that do not consume substantial CPU/GPU/RAM;
- a custom Activity-specific canvas/page aesthetic where appropriate.

Avoid making every Activity visually identical. Shared Greia UI should provide coherent primitives, not erase the personality of individual Activities.

---

## 11. Accessibility and input

Both Activities must:

- work at 1024×600;
- avoid tiny hit targets;
- support the reference pointer/touchpad path without assuming tap-to-click;
- work with keyboard where the task naturally requires it;
- provide visual state in addition to optional sound;
- avoid color as the sole indication of destructive/selected state where practical;
- never trap the child because an optional input capability is missing.

The writing Activity naturally requires a keyboard for typing; the painting Activity must not require a keyboard for its normal drawing workflow.

---

## 12. Definition of Phase-0 done

The requirement is not satisfied merely by having two folders that launch.

Before the first user-ready Phase-0 image can be considered complete, both Activities must:

- ship as first-party built-in Activities;
- validate under the current Activity manifest/runtime policy;
- use stable canonical Activity IDs;
- use Greia lifecycle READY/STOP semantics;
- use Greia profile-scoped Storage for creations;
- preserve child work automatically and recoverably;
- remain functional offline;
- expose no Linux filesystem/desktop UI in the child path;
- be genuinely usable at 1024×600;
- use large, simple child controls;
- meet the low-end performance/resource expectations on the Acer reference class;
- survive Activity exit/relaunch without losing accepted edits/drawings;
- participate in logical backup/restore when `.greiabackup` reaches implementation;
- pass provider-free logic/storage tests where practical;
- pass real visual/input acceptance on reference hardware;
- leave the shell in a valid state after normal exit, crash and forced return.

The text Activity additionally must default to large readable text and make ordinary writing comfortable.

The painting Activity additionally must provide responsive drawing with bounded undo and no per-frame durable encoding/writes.

---

## 13. Scheduling relative to the active remediation plan

This requirement does **not** authorize skipping the current blocking architecture/safety phase.

R7 remains the active blocking phase. These Activities depend on the lifecycle, Storage, profile, trust and display/session boundaries already established or currently being proven.

Implementation should begin as soon as the platform is stable enough to test them productively, and they must be complete **before the first user-ready Phase-0 image / final Phase-0 certification**.

They are especially valuable before final certification because they provide real-world acceptance workloads for:

- sustained keyboard/text input;
- sustained pointer drawing;
- autosave/checkpoint behavior;
- Activity lifecycle and forced return;
- low-end rendering performance;
- shared UI primitives;
- backup of genuine child-created content.

---

## 14. Maintenance rule

Update this document when the accepted Phase-0 scope of either Activity changes materially.

Once implementation begins, exact manifest IDs, storage schemas and reusable UI APIs belong to source/runtime contracts and the Activity-authoring skill; this document remains the product/UX requirement rather than a duplicate implementation specification.
