# Greia Activity Input Standards

**Status:** ACCEPTED PRODUCT REQUIREMENT  
**Date:** 2026-08-24  
**Scope:** Greia Shell and every child-facing Activity runtime, including Python/Pygame and future Web/HTML Activities

## Product goal

A child should learn Greia's controls once and carry that knowledge between Activities. Controller/joystick support is a Phase-0 requirement, but consistency must not force every Activity into one interaction style.

Greia therefore standardizes a small set of **interaction profiles** and maps available physical input devices onto those semantics.

An Activity describes the interaction it needs. It does not describe an Xbox controller, PlayStation controller, Nintendo controller, Linux joystick node, SDL button number, or other hardware-specific input layout.

## Pre-reader interaction is a product requirement

Greia's primary child audience includes children who **cannot read yet**. Therefore ordinary Activity operation must never assume literacy.

The core interaction contract is:

> **A child must be able to understand the next meaningful action, act, recover from mistakes, and continue without reading written instructions.**

Written text may support parents, older children, localization review, or reinforce spoken/visual content. It must not be the only channel carrying core gameplay instructions.

Preferred child-facing communication uses, as appropriate:

- visually obvious scene hierarchy;
- large icons, pictures, shapes and symbols;
- large numbers when number recognition is part of the Activity;
- short visual demonstrations, arrows, highlights or character motion;
- short reviewed spoken cues when language is useful;
- immediate visual/audio feedback after input.

Do not use voice merely to rescue an otherwise confusing screen. The primary action should be visually discoverable wherever the mechanic allows it.

A reading/literacy Activity is not exempt: written language may be the **learning content**, but the instructions for how to interact must still be understandable to a pre-reader.

Text-only instructions such as "click the blue whale", "choose the number you saw", or "press Continue" are not sufficient child-facing interaction design when the child must read them to proceed.

The focused Activity-authoring acceptance contract lives in:

```text
skills/greia-activity-authoring/PRE_READER_UX.md
```

## Mandatory interaction profiles

### `navigation`

For menus, Collections, galleries and other focus-oriented surfaces.

Default learned controls:

| Intent | Keyboard | Controller |
|---|---|---|
| move focus | arrow keys | D-pad or left stick |
| activate | Space or Enter | south face button |
| cancel/back within the content context | Escape where appropriate | east face button where appropriate |

Touch/pointer activates visible controls directly.

### `pointer`

For spatial Activities such as painting, dragging, arranging, maps and other pointer-first experiences.

Default sources:

- mouse/touchpad: normal pointer;
- touchscreen: direct touch;
- controller: Greia virtual pointer driven by the left stick;
- controller south face button: primary press/click;
- large on-screen controls remain ordinary pointer/touch targets.

The virtual pointer is a Greia semantic cursor. It must not be implemented by globally emulating a Linux mouse device merely for Activity convenience.

### `directional`

For simple maze, grid, movement and game-like Activities that need four-direction movement plus a primary action.

Default learned controls:

| Intent | Keyboard | Controller |
|---|---|---|
| move | arrow keys | D-pad or left stick |
| primary action | Space | south face button |
| activate/confirm where distinct | Enter | south face button/contextual activate |
| cancel where applicable | Escape | east face button |

This is the preferred default for very simple child games.

### `game`

For richer game-like Activities while retaining the simple baseline.

Mandatory baseline:

- arrow keys and D-pad/left stick provide movement;
- Space and the south face button provide the primary action.

Additional standard semantics may include secondary action, shoulders, triggers or a second stick when the Activity genuinely needs them. Activities should not require unnecessary controls merely because they are available.

### `text`

For writing and other true text-entry experiences.

The physical keyboard remains the text-entry device in Phase 0. Pointer/touch/controller may operate surrounding navigation and controls, but Greia must not pretend that a controller is a useful general typing device.

Text Activities must not lose normal Space/Enter/arrows merely because those keys have meanings in game/navigation profiles.

### `hybrid`

For Activities with genuinely mixed interaction modes that cannot be represented by one default profile. Hybrid is not permission to invent arbitrary hardware-specific mappings. The Activity should compose the smallest relevant Greia semantic contexts.

## Mouse-first control placement

**Status:** ACCEPTED PRODUCT REQUIREMENT (2026-10-16, owner direction). Kit support: ADR 0037 §4a.

Greia runs on laptops operated with a mouse or touchpad, not on a tablet held in two hands. A child moves one pointer, so the distance between controls used together is the cost of every decision.

- **Related controls form one compact cluster.** Controls a child uses together or in alternation during play (go + brake, left + right, up + down, jump + act, play + stop) sit side by side, adjacent or at most about one to two button widths apart, so the pointer travels a few centimetres, not across the screen.
- **Placement.** The cluster sits bottom-centre or bottom-right of the play area (right-handed pointer default), inside the safe margins and away from the protected Home/Back chrome (top-left, ADR 0019). It must not cover the thing the child is steering.
- **No split-screen two-thumb layouts.** Pedals in opposite bottom corners, steering on one side and actions on the other, or direction buttons split across the screen are not used.
- **Touch stays supported by size, not by spread.** Each control keeps the physical touch floor (≥ 40 px physical, larger for primary game actions), so a touchscreen still works with the compact cluster.
- **Exception: paging arrows.** Previous/next arrows may flank the strip, book or page they move, because their side is their meaning (the arrow sits where the content will come from). Real-time paired controls never use this exception.
- Unrelated control families (a tool strip vs. a save/share pair, a top status bar vs. the play cluster) stay in their own places; the rule is about controls used together.

The kit helper is `ControlLayout.cluster(...)` (ROW for pairs/rows, CROSS for a four-way pad) with a reserved slot for the keyboard hint below.

## Keyboard affordance (drawn keys)

**Status:** ACCEPTED PRODUCT REQUIREMENT (2026-10-16, owner direction). Kit support: ADR 0037 §4b.

Children should discover that the keyboard works as well as the mouse without reading anything.

- **Required** for every Activity whose interaction profile accepts directional/game keys (`directional`, `game`) and for any `hybrid` Activity whose play acts directly on arrows/Space (moving, steering, dropping, carrying something), beyond plain focus navigation.
- The Activity shows a **keyboard hint**: the acting keys drawn as keycaps (the arrow cluster as an inverted T and/or the Space bar; Enter only where Enter has its own meaning), placed near its on-screen control cluster (or beside the board/object the keys move when there is no cluster).
- Arrows that do nothing in this Activity are drawn dimmed rather than omitted, so the picture still looks like the child's keyboard.
- It is shown at start (a few seconds) and again as part of the idle hints (lighting the acting keys one after another), then hides; it reappears whenever the child presses one of its keys.
- **The drawn key lights up while the real key (or the matching controller D-pad / south button) is pressed**, so the child sees the mapping.
- It is language-neutral (no letters or words, no controller brand symbols), small and unobtrusive yet legible for a 4–7-year-old (keycaps about 28–32 px visible at 1024×600 and no smaller than about 24 px at 800×480), never covers gameplay or the protected chrome, and is display-only (not a focus target or a touch target).
- Plain focus navigation (arrows move the focus ring, Space activates) does not require the hint; an Activity may show it in its last idle-hint step.
- Activities that use other keys (letters on a xylophone, typing letters) are outside this rule until a letter-keycap set exists; Writing (`text`) is exempt.

The kit control is `KeyboardHint` (`greia_platform.activity_keyboard_hint`, art `ui.keycap.*`).

## Controller vocabulary is brand-neutral

Greia identifies physical controller controls by position/role rather than consumer-brand labels:

```text
FACE_SOUTH
FACE_EAST
FACE_WEST
FACE_NORTH
DPAD_*
LEFT_STICK_*
RIGHT_STICK_*
LEFT/RIGHT_SHOULDER
LEFT/RIGHT_TRIGGER
START
BACK
GUIDE
```

Runtime adapters may internally translate SDL or browser APIs, but brand-specific names and raw button indices are not portable Activity semantics.

## Device coexistence

Greia is input-switching, not input-mode-switching.

A child may move the mouse, touch the screen, press a key or pick up a controller without visiting a settings page to choose an active input method. Appropriate sources feed the same Activity semantics.

The presence of a controller must not disable keyboard, pointer or touch input.

## Central input behavior

Greia owns common device-normalization policy, including where applicable:

- analog stick normalization;
- dead zones;
- noisy-controller handling;
- menu repeat behavior;
- controller virtual-pointer speed and precision;
- device connection/reconnection;
- brand-neutral controller mapping;
- platform-reserved system input.

Activities must not each reinvent these policies.

Initial tuning values are source-owned and may evolve from child/hardware testing without changing the interaction-profile semantics.

## System navigation has higher trust

ADR 0019 remains authoritative for Greia Home/Back.

Controller system/Guide input, where reliably exposed, is reserved to the Greia platform and must not become an Activity action. A fallback multi-button Home chord may be selected later only after accidental-activation testing; this requirement does not freeze an untested chord.

Activities may have their own in-content Back/Cancel semantics, but they cannot intercept or replace the platform's mandatory route Home.

## Physical input authority

Controller support must not be implemented by granting ordinary Activities raw ownership of `/dev/input`, joystick nodes, DRM/input seats or equivalent host resources.

The production input/session layer owns physical devices and protected system controls. Runtime adapters receive the Activity-facing input semantics appropriate to their profile.

Development/provisional backends may use platform-owned Pygame/SDL controller objects while R7 is being completed, provided ownership is explicit, bounded and outside ordinary Activity authority.

## Python and Web parity

The semantic profiles and actions are runtime-neutral.

A Python Activity and a future Web Activity declaring the same interaction profile should receive equivalent child-facing behavior. Web content must not need browser-specific gamepad mappings to obtain ordinary Greia controller behavior, and browser history must not become Greia Back.

## Manifest requirement

New Activities declare their default profile in `activity.toml`:

```toml
[input]
profile = "directional"
```

Supported profiles are:

```text
navigation
pointer
directional
game
text
hybrid
```

Existing API 0.1 packages without an `[input]` table remain temporarily compatible as `hybrid`; new and materially updated Activities should declare intent explicitly.

The hardware capability `controller` means that controller input is available on the current device. It does **not** mean every Activity must request `controller` simply to benefit from Greia's standard alternative-input mapping.

An Activity should require `controller` only when the Activity truly cannot function without one.

## Phase-0 acceptance intent

Phase 0 is not input-complete until evidence demonstrates at least:

- Shell navigation with keyboard and a supported controller;
- simple-game mapping with arrows + Space and D-pad/stick + primary face button;
- pointer-profile controller virtual-pointer behavior;
- controller disconnect/reconnect without breaking keyboard/pointer operation;
- system-reserved controller input not delivered to Activity content;
- no raw Activity `/dev/input` authority introduced merely for controller support;
- acceptable latency/dead-zone behavior on representative controller hardware;
- resource cost acceptable on the Acer low-resource reference;
- equivalent semantic contract ready for the Web runtime boundary;
- representative child-facing Activity flows remain understandable without reading written instructions;
- related game controls placed as one mouse-first cluster and a lit keyboard hint shown in every Activity that requires one (audit: `2026-10-16_CONTROL_PLACEMENT_AUDIT.md` (archived; see git history)).

First-party Activities receive no exemption from these standards.
