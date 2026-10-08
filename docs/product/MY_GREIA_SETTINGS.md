# My Greia — Child-facing settings and personalization

**Status:** accepted product requirement  
**Date:** 2026-08-18  
**Owner:** Greia child experience / platform customization

## 1. Purpose

Greia gives children a very small settings experience so they can learn a useful digital concept: **a device can have preferences, and changing a setting changes how their own space looks and feels**.

This is not a child-accessible version of Linux settings and not a second Parent control panel. It is a playful first-party Activity called **My Greia**.

The stable package identity remains `org.greia.workshop-settings` for migration/permission continuity; the child-facing product name is My Greia.

**Installed product requirement (2026-10-08 source reconciliation):** My Greia
is a mandatory **trusted child-personalization system Activity** in every
Greia target, separate from ordinary optional/curated *educational-game*
release selection. `src/greia_platform/activity_release.py` declares the
immutable built-in package identity and `tools/stage_release_activities.py`
installs it alongside a curated roster, validating exact installed identity
before publishing. Merely having the expected package ID in an untrusted
third-party package never grants `customization.manage`. This source repair
is NOT yet accepted by installed target or Parent-policy testing; Greia's
official release selection still remains draft/fail-closed.

## 2. Child-facing scope

My Greia owns only low-risk, high-visual-impact, profile-scoped choices:

- background / wallpaper;
- curated background color;
- curated accent color;
- curated text color;
- semantic interface size: compact, normal, large;
- the child's own avatar.

These choices belong to the child profile, not the whole machine. Two siblings may therefore have visibly different Greia spaces on the same device.

## 3. Explicitly NOT child settings

My Greia must not expose:

- Wi-Fi/network credentials;
- Parent password or paired Parent devices;
- child-password creation/removal;
- SSH/developer access;
- package installation/removal/update authority;
- disk/storage administration;
- system time/date administration;
- Linux users/groups;
- shell/terminal controls;
- bootloader/recovery controls;
- display modes that can strand the UI;
- permission/security policy;
- unrestricted filesystem browsing.

Those remain Parent/platform authority even if a future Parent UI presents them visually.

## 4. Interaction model

The target children may not read. My Greia is therefore visual-first:

- settings families are represented by large semantic icons;
- a color is chosen by touching/clicking the color itself;
- wallpaper is chosen by touching/clicking its preview;
- interface size is represented by the same familiar visual shown at visibly different sizes;
- avatars are chosen by image;
- successful selection is shown with a visual check/selection state;
- errors use a visual failure cue;
- changes apply immediately rather than requiring a text-heavy Apply/Save dialog.

Keyboard/controller navigation may supplement pointer/touch behavior, but hover is never the only signal.

Universal Home/Back remains platform-owned system chrome under ADR 0019. My Greia must not draw a fake replacement.

## 5. Interface-size semantics

Greia deliberately does **not** expose an arbitrary font-size slider or pixel value.

The profile chooses exactly one semantic value:

```text
compact
normal
large
```

The platform maps that value to bounded presentation scaling. Responsive layout remains authoritative: renderers must reflow, wrap, paginate or scroll as needed and must never interpret `large` as permission to clip essential controls.

Activity authors do not create separate compact/normal/large layouts. They consume Greia semantic typography/UI helpers and author one layout/canvas/world design.

## 6. Profile visual context and Activity authority

Only the trusted built-in My Greia Activity has `customization.manage` and therefore direct write access to the active profile's managed customization state.

Ordinary Activities may receive a **read-only resolved launch snapshot** containing safe presentation facts such as:

- resolved background/panel/accent/text colors;
- semantic interface-size choice.

They do not receive:

- `GREIA_CUSTOMIZATION_DIR`;
- wallpaper file paths;
- permission to mutate profile customization;
- filesystem authority merely because they can match the child's colors.

This separation lets Writing, Painting and future Activities feel like the child's Greia without turning appearance into a security capability.

## 7. Wallpaper safety

Wallpaper import remains a bounded Greia-managed operation:

- source discovery is bounded;
- supported formats are curated;
- source path must remain inside removable-media authority;
- images are decoded with pixel/size limits;
- imported wallpaper is normalized into a bounded managed JPEG;
- ordinary Activities do not receive the managed wallpaper path.

A removed USB/SD device must not make the child profile unusable because the selected wallpaper has already been normalized into managed profile state.

## 8. Responsiveness

My Greia is subject to ADR 0026 and `RESPONSIVE_UI_AND_DISPLAY_LAYOUT.md`.

The designer does not position four different settings UIs for four resolutions. Semantic areas and grids derive from the live viewport. At small sizes collections reduce visible capacity/reflow; at large sizes growth is capped.

Required representative probes include 640x480, 800x600, 1024x600, 1366x768, 1920x1080, 4K and a portrait stress viewport. The physical 1024x600 Acer remains the low-resource/readability acceptance floor.

## 9. Learning value

My Greia may contribute low-weight platform learning/progression evidence around concepts such as choice-making, personalization and digital settings, but it must not gamify basic accessibility/customization in a way that locks settings behind rewards.

A child must always be able to return to a usable default visual configuration through the supported Parent/platform path if their choices become undesirable.

## 10. Future child-safe candidates

Possible later additions, only after design review:

- a small set of approved cursor styles;
- reduced-motion preference;
- sound-effect volume within a Parent-defined maximum;
- simple high-contrast presets;
- child-selected launcher decoration/theme motifs.

Do not grow My Greia into a dumping ground for every machine setting. A new option belongs here only when it is safe for a child to change independently and has an obvious visual/experiential result.

## 11. Acceptance

A My Greia tranche is not complete until an owner-controlled test proves:

1. each supported setting persists per child;
2. switching profiles switches visual preferences;
3. returning from My Greia refreshes the launcher without reboot;
4. ordinary Activities can consume the read-only visual snapshot but cannot mutate profile settings;
5. compact/normal/large remain contained across the responsive resolution matrix;
6. wallpaper/color changes do not expose raw filesystem authority;
7. the Activity exits through Greia lifecycle/system navigation cleanly;
8. idle/runtime behavior remains acceptable on the 1024x600 low-resource reference.
