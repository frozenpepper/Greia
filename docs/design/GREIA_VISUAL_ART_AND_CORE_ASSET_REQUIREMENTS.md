# Greia Visual Art and Core Asset Requirements

**Status:** Initial production inventory / art-direction requirements  
**Date:** 2026-08-08  
**Purpose:** Enumerate the fundamental graphical assets Greia needs as a coherent child operating environment, beyond individual Activity artwork.

This document complements `docs/13_ART_LIBRARY_AND_ASSET_PIPELINE.md`. That document defines the semantic asset pipeline and current Core Icons v1 catalogue. This document defines **what visual material the platform itself still needs**.

---

# 1. Art principles

Greia's art should make the machine feel like one world, not a set of unrelated programs.

The production visual language should be:

- warm and playful without looking like baby software;
- readable at 800×600 and 1024×600 as well as modern displays;
- shape-first and language-light for child navigation;
- consistent between shell, Activities, rewards, profile selection, and recovery;
- visually rich enough to reward exploration without heavy animation or GPU requirements;
- friendly to static PNG/SVG/sprite assets so the C0 hardware path remains inexpensive;
- capable of optional richer animation on stronger devices without changing meaning;
- accessible under color-vision differences: important states must not rely on color alone;
- transparent-background friendly for reusable characters/icons;
- designed with safe margins because old displays may crop/scale unexpectedly.

Greia should favor **large silhouettes, simple internal detail, and strong state changes** over tiny decorative details that disappear at low resolution.

---

# 2. Existing canonical icon inventory

Core Icons v1 currently provides 39 semantic icons, including:

- literacy: book, ABC board, ABC blocks, notebook;
- characters: robot, unicorn, owl, dinosaur, wizard, green monster;
- learning/science: globe, potions, magnifier;
- creativity/music: palette, music star;
- rewards/status: treasure chest, coins, coin bag, pouch, star/cup/puzzle trophies, medal, hearts, stars, lightning;
- navigation/adventure/world: backpack, map, car, garden, rainbow, train blocks;
- logic: puzzle pieces, block puzzle;
- controls: check, X mark, close button.

These are useful seed assets but **must not be mistaken for a complete OS visual system**.

---

# 3. Greia brand assets — P0 critical

## 3.1 Greia primary mark

Required variants:

- full Greia wordmark;
- compact symbol/mark without text;
- monochrome light version;
- monochrome dark version;
- high-contrast accessibility version;
- tiny boot-safe version that remains legible at 64–128 px;
- square app/repository/social avatar variant.

The mark should not depend on Professor Pip; the platform must remain able to host other worlds/characters.

## 3.2 Boot emblem

A simplified Greia emblem suitable for firmware-to-kernel visual continuity where technically possible, boot cover, installer startup, recovery startup, and temporary loading transitions.

It should render cleanly on black or a single Greia background color and remain recognizable without text.

## 3.3 Greia palette and texture kit

Define canonical primary backgrounds, accents, panel/card colors, positive/complete, warning, error/recovery, locked/unavailable, neutral/inactive, text contrast pairs, and optional subtle workshop/paper/paint textures.

These should map to theme tokens rather than arbitrary RGB values in Activities.

---

# 4. Boot, intro, and first-arrival screens — P0 critical

## 4.1 Power-on / boot cover

Minimum art:

- static full-screen Greia background with masters suitable for 800×600, 1024×600, 1280×720, and 1920×1080;
- centered Greia emblem;
- optional 6–12 frame lightweight loop such as a gentle glow, floating specks, turning small gear, or blinking star;
- no text required for child boot.

The boot cover must visually survive being held for an unexpectedly long boot without looking frozen.

## 4.2 Shell first-frame transition

Provide an asset/animation concept for the transition from boot cover to profile picker. The same background family should continue through the handoff and the emblem may shrink, move, or dissolve into the profile scene. A static fallback is mandatory.

Goal: avoid a perceptual “application launched” moment. The child should experience one continuous Greia world.

## 4.3 First-run welcome

Needed for a newly installed machine before profiles exist:

- friendly Greia welcome scene;
- Professor Pip greeting pose, optional but recommended;
- parent-directed handoff symbol without requiring the child to read instructions;
- clear visual distinction between parent setup and later child profile selection.

## 4.4 Recovery intro

A visually calm recovery screen distinct from an error dialog:

- Greia emblem;
- Professor Pip/companion concerned-but-calm state;
- simple parent/recovery symbol;
- no Linux terminology exposed to child.

---

# 5. Child profile selection art — P0 critical

## 5.1 Profile card frame

States:

- normal;
- focused/selected;
- pressed;
- password/PIN protected;
- disabled/unavailable;
- newly created/highlighted.

## 5.2 Avatar library

The current character icons can seed avatars, but a production set should include at least Professor Pip, unicorn, robot, owl, dinosaur, friendly monster, cat, dog, fox, rabbit, bear, astronaut, dragon, sea creature, flower/nature, vehicle/machine, and an abstract star/rainbow option.

Target: **16–24 high-quality neutral avatars** before first public release.

Each avatar should work at 64 px, 128 px, and 256 px.

## 5.3 Secret-entry symbols

Need dedicated icons rather than reusing generic stars:

- lock;
- unlocked;
- backspace;
- confirm;
- cancel/back;
- incorrect/wobble indicator;
- show characters;
- hide/mask characters.

Because Greia defaults to visible password/PIN entry for children, the show/hide state needs especially clear art.

---

# 6. Greia Shell / Workshop scene — P0/P1

The launcher currently uses a tile grid. The long-term child experience should have a recognizable Greia world/workshop identity even if the initial implementation keeps efficient cards.

## 6.1 Main workshop background

Create a layered scene that can scale/crop across 4:3, 16:10, and 16:9:

- neutral workshop/base layer;
- sky/window/background layer;
- foreground furniture/machines layer;
- optional decoration attachment points;
- safe central/navigation zones.

Layers should support parallax or small ambient animation on capable machines but look complete when static.

## 6.2 Category/location portals

Core category art should cover at least:

- creativity/art;
- science/laboratory;
- numbers/math/logic;
- reading/language;
- music/sound;
- nature/world;
- building/making;
- stories/adventure;
- personal/profile area;
- discoveries/notebook;
- rewards/collection.

These can eventually appear as workshop rooms/machines rather than plain category buttons.

## 6.3 Activity tile/card frame

States required:

- normal;
- hover/focus;
- pressed;
- new;
- recently added;
- update available;
- completed;
- partially progressed;
- locked by parent;
- incompatible with current capability class;
- temporarily unavailable/error;
- favorite/pinned if adopted.

State must be visible by silhouette/badge as well as color.

---

# 7. Professor Pip production character sheet — P0/P1 critical

Professor Pip is a character inside Greia, not the platform logo. He nevertheless needs a consistent reusable state library because he can guide children through shell moments and multiple Activities.

## 7.1 Base poses

Minimum static poses:

1. neutral/front idle;
2. friendly greeting/wave;
3. pointing left;
4. pointing right;
5. pointing down/at an object;
6. thinking;
7. explaining/teaching;
8. celebrating;
9. surprised/discovery;
10. encouraging/“try again”;
11. concerned/recovery;
12. waiting/loading;
13. reading/holding notebook;
14. holding tool/object;
15. listening;
16. goodbye/return-to-workshop.

## 7.2 Facial/emotional states

Reusable variants:

- neutral;
- happy;
- delighted;
- curious;
- thinking;
- surprised;
- gentle concern;
- proud;
- sleepy/waiting;
- speaking mouth open/closed.

Avoid anger, shame, disappointment, or failure imagery for normal educational mistakes.

## 7.3 Lightweight animation states

Optional sprite/sequence states:

- blink;
- breathing/idle sway;
- wave;
- point;
- celebrate;
- thinking loop;
- talking loop;
- enter/exit;
- look toward highlighted UI element.

C0 requirement: every animation must have a good static frame fallback.

## 7.4 Directional composition

Important poses should exist mirrored or be safely mirrorable without text/asymmetric props. This lets the UI place Pip on either side without creating bespoke art each time.

---

# 8. Recurring companion characters — P1

Greia benefits from a small recurring cast rather than dozens of unrelated mascots.

Recommended initial companions based on existing art:

- unicorn — wonder, imagination, kindness;
- robot — making, logic, technology;
- owl — books, observation, night/astronomy;
- dinosaur — nature, history, scale;
- friendly monster — humor/emotion/play.

Each recurring character should have a minimal common state set: neutral, happy, thinking, celebrating, surprised, gentle try-again, speaking/listening, and small icon/avatar form.

The cast should have a documented visual bible: proportions, outline weight, eye style, shading, color constraints, and personality cues.

---

# 9. Core child navigation icons — P0 critical

Dedicated, consistent icons are needed for:

- home/workshop;
- back;
- return/exit Activity;
- next;
- previous;
- play/start;
- pause;
- continue/resume;
- stop;
- retry;
- confirm;
- cancel;
- close;
- help/hint;
- profile/switch child;
- settings/personalize;
- discoveries/notebook;
- rewards/collection;
- audio on/off;
- volume up/down;
- speech/narration;
- language;
- accessibility;
- fullscreen/display where appropriate.

Avoid conventional desktop metaphors where a more child-readable symbol exists.

---

# 10. Activity state badges — P0/P1

Small overlays/badges used consistently across activity cards:

- new;
- update;
- installed/current;
- completed;
- progress/in-progress;
- locked by parent;
- capability unavailable;
- offline/network-needed;
- error/repair needed;
- save present;
- no save/new start;
- favorite/pinned if adopted.

Text may accompany these in Parent UI, but child-facing cards should remain interpretable visually.

---

# 11. Reward and progression art — P1

Do not finalize the reward economy before the Progression Engine schema, but prepare a coherent visual vocabulary:

- star/spark token;
- achievement badge frame;
- discovery card/sticker frame;
- treasure chest/collection container;
- unlocked item burst;
- progress trail/constellation/path;
- workshop decoration unlock;
- new-discovery indicator;
- completion celebration particles.

Production art should support progression without implying purchasable currency or gambling-style mechanics.

---

# 12. Parent-management icon family — P0/P1

Parent UI can use text, but still benefits from consistent iconography.

Required:

- children/profiles;
- add/edit/remove child;
- lock/password;
- activity library;
- install/update/remove;
- preserve saves/delete saves;
- USB drive;
- SD card;
- backup/export;
- restore/import;
- storage;
- Wi-Fi/network/offline;
- display/resolution;
- mouse/touchpad/tap-to-click;
- keyboard;
- audio;
- language;
- accessibility;
- system update;
- restart/shutdown;
- recovery;
- diagnostics/health;
- security/pairing;
- reset/defaults.

---

# 13. Removable-media installation art — P1 critical for package workflow

When USB/SD Activity installation is implemented, provide graphics for:

- media inserted/scanning;
- Activity NEW — install;
- Activity UPDATE — old version → new version;
- already current;
- older than installed/downgrade blocked;
- incompatible;
- invalid/corrupt package;
- signature/trust warning for a future public ecosystem;
- copying/staging;
- validating;
- installing;
- migrating save;
- update successful;
- rolled back/previous version restored;
- media safe to remove.

These states should look procedural and calm rather than alarming.

---

# 14. Backup/restore art — P1 critical

Required visual states:

- choose USB/SD destination;
- backup contents summary;
- optional protected backup/passphrase;
- exporting;
- verifying;
- completed/safe to remove;
- restore archive detected;
- profile conflict/merge choice;
- missing Activity but save preserved;
- restore progress;
- restore complete;
- corrupt/incompatible backup;
- insufficient space.

The child-data metaphor may use “packing a backpack/treasure box” rather than filesystem concepts where appropriate.

---

# 15. Hardware and system status icons — P1

Needed for Parent UI and occasional child-safe system states:

- battery levels/charging;
- AC power;
- Wi-Fi levels;
- offline;
- Ethernet;
- speaker/mute;
- microphone;
- camera;
- keyboard;
- mouse;
- touchpad;
- touchscreen;
- controller;
- USB;
- SD card;
- storage/full;
- temperature/overheat for parent diagnostics;
- display;
- sleep;
- restart;
- shutdown.

---

# 16. Error, waiting, and recovery states — P0 critical

Greia must never fall back to ugly system UI because error art was never made.

Create child-safe screens/illustrations for:

- Activity loading;
- Activity taking longer than expected;
- Activity failed to start;
- Activity crashed and Greia returned safely;
- Activity frozen/forced return in progress;
- no Activities installed;
- temporary catalogue problem;
- removable media unreadable;
- save cannot be opened but old data is safe;
- system recovery mode;
- parent help required;
- shutdown in progress.

Recommended character tone: puzzled/working/repairing, never blaming the child.

---

# 17. Installer art — P0 critical

The graphical installer should have a dedicated coherent visual set:

- welcome/install Greia;
- target computer/disk illustration;
- erase/whole-disk confirmation visual;
- power-connected requirement;
- installation progress;
- verification/check;
- success;
- one-time recovery-code screen framing;
- power off;
- remove USB/SD;
- no eligible disk;
- insufficient storage;
- unsafe power state;
- installation failed/data not modified where true.

The installer is parent-facing and may use explanatory text, but it should still feel unmistakably like Greia.

---

# 18. Pointer/cursor assets — P0

Because Greia owns the shell and old devices may have touchpads/mice, create a custom pointer set:

- normal pointer;
- clickable/select pointer if desired;
- busy/loading;
- drag/grab;
- text-entry pointer only where genuinely needed.

Pointer dimensions must remain readable at 800×600 without obscuring small targets.

---

# 19. Common interaction effects — P0/P1

Reusable low-cost visual effects:

- focus halo;
- press/squash state;
- selected glow;
- success sparkle;
- gentle error wobble;
- unlock burst;
- transition wipe/fade;
- loading dots/gears/stars;
- page-change indicator;
- drag target highlight.

Prefer effects reproducible procedurally or with tiny sprite sheets over large video assets.

---

# 20. Resolution and format requirements

## Raster masters

For important characters/backgrounds, retain high-resolution masters outside runtime images. Runtime export should be profile-aware.

## Icon sizes

Continue semantic variants at approximately 64 px, 128 px, and 256 px where needed. Critical controls should be manually checked at their actual rendered size; blind downscaling is not sufficient.

## Backgrounds

Design source canvases with safe cropping for 800×600, 1024×600, 1280×720, and 1920×1080. Avoid placing essential information close to edges.

## Animation

Prefer short sprite sheets, transforms/tweens, procedural particles, and small vector/raster sequences. Avoid requiring video playback for core shell state.

---

# 21. Asset-state naming convention

Recommended semantic IDs:

```text
character.professor_pip.idle
character.professor_pip.wave
character.professor_pip.thinking
character.professor_pip.celebrate

control.back.normal
control.back.focused
control.back.pressed
control.back.disabled

activity.badge.new
activity.badge.update
activity.badge.completed
activity.badge.locked

system.media.usb
system.media.sd
system.backup.export
system.backup.restore
```

Runtime code should request semantic IDs. It should not infer filenames or sprite coordinates.

---

# 22. Production asset milestones

## Art Milestone A — Greia bootable identity

Required before visual boot acceptance:

- Greia mark/wordmark;
- boot cover;
- first-frame/profile background;
- custom pointer;
- profile card states;
- 12+ production avatars;
- lock/back/confirm/cancel controls;
- core error/recovery illustration.

## Art Milestone B — coherent child shell

- workshop/main scene;
- category/location art;
- Activity tile states;
- navigation control family;
- Professor Pip base sheet;
- recurring companion base states;
- progression/reward family.

## Art Milestone C — parent/install/backup readiness

- complete Parent icon family;
- installer art states;
- USB/SD installation states;
- backup/restore states;
- hardware/status family;
- recovery/diagnostic family.

## Art Milestone D — polish and accessibility

- high-contrast variants;
- animation loops;
- low-resolution manual cleanup;
- color-vision review;
- RTL/mirroring review where applicable;
- final icon consistency pass;
- profile-specific runtime asset pruning for C0 footprint.

---

# 23. Immediate next art tasks

The first production art brief should commission/design, in this order:

1. **Greia logo + compact emblem**;
2. **boot/intro background and static boot composition**;
3. **Professor Pip master design and 8 core poses**;
4. **profile picker production frame + 16 avatars**;
5. **core navigation controls** — back, home, confirm, cancel, play, pause, retry, return;
6. **main workshop/background scene**;
7. **Activity card state overlays**;
8. **error/recovery/loading visual set**;
9. **Parent system icon family**;
10. **installer + USB/SD + backup/restore state art**.

This gives engineering enough stable visual material to build the real Greia shell and direct-display acceptance path without repeatedly inventing temporary UI art.