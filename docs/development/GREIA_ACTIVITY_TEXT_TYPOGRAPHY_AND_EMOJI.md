# Greia Activity Text, Typography and Emoji Authoring Guide

**Status:** living Activity/developer manual for the current Python/Pygame platform contract  
**Date:** 2026-08-19  
**Audience:** Activity authors, coding agents, UI implementers and reviewers  
**Implementation authority:** `src/greia_platform/typography.py`, `src/greia_platform/emoji_palette.py`, `src/greia_platform/pygame_ui.py`  
**Design authority:** `docs/design/GREIA_VISUAL_STYLE_GUIDE.md`

---

## 1. Why this exists

Greia treats text and emoji as a **platform concern**, not something every Activity should reconstruct.

Young children use emoji naturally, and many visible emoji are not one Unicode codepoint. A correct Greia Activity therefore needs more than a font that happens to contain some symbols: rendering, measurement, cursor movement, deletion, wrapping, hit testing, truncation and persistence must all agree about what one child-visible character is.

The current Python/Pygame platform provides one shared path for:

- Greia's normal interface typography using Nunito Sans semantic roles;
- color emoji fallback using Noto Color Emoji;
- Unicode extended-grapheme segmentation;
- mixed text + emoji measurement and rendering;
- grapheme-safe cursor boundaries and truncation;
- a bounded, renderer-neutral curated child emoji palette.

**Activities must use this shared contract for ordinary Greia UI and editable Unicode text rather than opening host fonts, maintaining emoji ranges, or implementing their own ZWJ parser.**

This document explains how to consume the current contract. It does not replace the source as the exact API definition.

---

## 2. Mental model

For ordinary Pygame text, think of Greia's rendering path as:

```text
Activity Unicode string
        ↓
Unicode extended grapheme clusters
        ↓
┌───────────────────────┬────────────────────────┐
│ ordinary text cluster │ emoji-presented cluster│
│ Nunito Sans           │ Noto Color Emoji       │
│ Pygame font renderer  │ Pillow color rasterizer│
└───────────────────────┴────────────────────────┘
        ↓
combined transparent Pygame surface
```

The Activity asks Greia to render **text**, not to find a font file.

For editing, the visible unit is a Unicode **grapheme cluster**, for example:

```text
A
é
👍🏽
👩‍🔬
🏳️‍🌈
🇮🇹
1️⃣
❤️
```

Each item above is one child-visible unit even when its Python string contains multiple codepoints.

---

## 3. The Activity-facing Pygame import surface

New Pygame Activities should import shared typography/emoji helpers from:

```python
from greia_platform.pygame_ui import (
    FontRole,
    GreiaTypography,
    EmojiPalette,
    grapheme_boundaries,
    grapheme_spans,
    next_grapheme_boundary,
    previous_grapheme_boundary,
    snap_grapheme_boundary,
    truncate_grapheme_safe,
)
```

`greia_platform.pygame_ui` is the current platform-wide Pygame UI import surface. The implementation remains source-owned by `greia_platform.typography` and `greia_platform.emoji_palette`.

Do **not** import launcher internals merely to obtain text rendering.

---

## 4. Create one typography service and reuse it

Create a `GreiaTypography` object at the Activity/UI owner boundary and reuse it for the lifetime of that surface.

```python
self.typography = GreiaTypography()
```

Do not construct a typography object every frame or every label. The platform service owns bounded font and emoji-surface caches.

When the renderer/display lifetime ends, release its caches:

```python
self.typography.clear()
```

A typical Activity shutdown path is therefore conceptually:

```python
try:
    run_activity()
finally:
    typography.clear()
    pygame.quit()
```

The exact lifetime should follow the Activity's real renderer ownership rather than forcing this shape everywhere.

---

## 5. Use semantic Greia font roles

The current roles are:

```text
FontRole.BODY
FontRole.SECONDARY
FontRole.CONTROL
FontRole.TITLE
FontRole.DISPLAY
```

They map to the platform-selected Nunito Sans weights. Activities should normally choose the **semantic role** and a responsive size rather than opening a named font file.

Example:

```python
size = metrics.px(28)
label = typography.render(
    "Bravissima! 🌟",
    FontRole.CONTROL,
    size,
    theme.text,
)
screen.blit(label, label.get_rect(center=button.center))
```

This renders ordinary text and color emoji through the same Greia service.

### Do not do this for ordinary Greia UI

```python
pygame.font.Font("/usr/share/fonts/.../SomeFont.ttf", 28)
```

or:

```python
pygame.font.SysFont("Arial", 28)
```

or:

```python
ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf", ...)
```

Host font paths and the current Noto bitmap-strike details are implementation facts, not an Activity API.

---

## 6. Rendering mixed text and emoji

Use:

```python
surface = typography.render(text, role, size, color)
```

for **one logical line**.

Example:

```python
surface = typography.render(
    "Space 🚀 is fun!",
    FontRole.BODY,
    metrics.px(32),
    theme.text,
)
```

The current `render()` contract is single-line. If text contains newlines, the Activity should perform its normal semantic line/wrap layout and render each visual line separately.

Do not catch missing emoji and then search the host for another font. Supported Greia images carry the platform fallback; `GreiaTypography` owns safe degradation if that resource is missing or corrupt.

---

## 7. Measure with the same renderer you draw with

Never measure text with one font API and render it with another fallback chain.

Use:

```python
metrics = typography.measure(text, role, size)
width = metrics.width
height = metrics.height
line_height = metrics.line_height
```

This matters around emoji because the emoji surface can have dimensions different from ordinary Nunito glyphs.

For caret placement inside mixed text, use:

```python
x = typography.prefix_width(text, cursor, role, size)
```

`prefix_width()` snaps the cursor to a valid grapheme boundary before measuring.

A text editor should therefore derive **wrapping, caret position and pointer hit testing from the same typography measurements used for drawing**.

---

## 8. Editable text: grapheme clusters are mandatory

### 8.1 The bug to avoid

This is wrong for child-visible editing:

```python
cursor -= 1
text = text[:cursor] + text[cursor + 1:]
```

For `👩🏽‍🔬`, that can move into or delete only part of the visible emoji. The same problem affects combining accents, flags, keycaps and many family/person emoji.

### 8.2 Cursor movement

Use grapheme boundaries:

```python
cursor = previous_grapheme_boundary(text, cursor)
cursor = next_grapheme_boundary(text, cursor)
```

If a cursor was restored from stale/legacy state or calculated by another operation:

```python
cursor = snap_grapheme_boundary(text, cursor)
```

### 8.3 Backspace

Conceptually:

```python
start = previous_grapheme_boundary(text, cursor)
removed = text[start:cursor]
text = text[:start] + text[cursor:]
cursor = start
```

### 8.4 Delete

Conceptually:

```python
end = next_grapheme_boundary(text, cursor)
removed = text[cursor:end]
text = text[:cursor] + text[end:]
```

### 8.5 Vertical movement and columns

A visual/editor column must count grapheme clusters rather than Python codepoints.

Use:

```python
column = len(grapheme_spans(line_prefix))
```

and choose the corresponding boundary on the target visual line with `grapheme_boundaries()`.

### 8.6 Selection

If an Activity implements selection, both selection endpoints must snap to grapheme boundaries. Do not allow highlighting/deleting the middle of a visible grapheme merely because the string index exists.

Greia does not currently expose a complete generic retained text-editor widget; the first-party Writing Activity is the reference implementation for the present low-level contract.

---

## 9. Wrapping and hit testing

Wrapping must advance through grapheme spans rather than raw characters:

```python
for span in grapheme_spans(text):
    width = typography.measure(
        span.text,
        FontRole.BODY,
        font_size,
    ).width
    ...
```

Pointer-to-caret hit testing should similarly walk visible graphemes, measure each through `GreiaTypography`, and place the cursor only at `span.start` or `span.end`.

Do not:

- use `len(text)` as a visual column count;
- assume one codepoint equals one glyph;
- use a separate approximate emoji width;
- split ZWJ sequences on `\u200d`;
- maintain hand-written emoji range tables.

---

## 10. Bounded text and truncation

Storage/UX bounds may still be expressed in codepoints or bytes, but truncation must never retain half of a grapheme.

Use:

```python
safe = truncate_grapheme_safe(text, maximum_codepoints)
```

This returns the longest prefix not exceeding the requested bound **and ending at a valid grapheme boundary**.

Use the same principle for:

- document size guards;
- previews;
- short labels derived from child text;
- history snippets;
- imported/restored text normalization.

Do not truncate with `text[:maximum]` when the string may contain user-entered Unicode.

---

## 11. Persistence: store normal Unicode, not Greia emoji tokens

Emoji are persisted as ordinary Unicode text, normally UTF-8 at serialization boundaries.

Good:

```python
payload = text.encode("utf-8")
```

Bad:

```text
[GREIA_EMOJI_17]
emoji_rocket.png
NotoGlyph#1234
```

Do not replace emoji with private Greia identifiers in durable child content.

Standard Unicode persistence keeps documents portable across:

- i386, amd64 and ARM64;
- future Greia runtimes;
- backup/restore;
- exports and external tools;
- later Unicode/font implementations.

Renderer implementation details must never leak into save files.

---

## 12. The Greia emoji palette

`EmojiPalette` is a **bounded selection model** for child-facing emoji pickers. It is not the renderer and it is not the complete set of emoji Greia can display.

Current usage:

```python
palette = EmojiPalette()

for category in palette.categories:
    print(category.category_id, category.icon)

palette.select(2)
for cluster in palette.selected.emoji:
    ...
```

The current default palette has small semantic groups such as faces, animals, nature, food, play, adventure and symbols. Each picker item is validated as exactly one emoji grapheme.

### Important distinction

```text
GreiaTypography
    = display arbitrary supported Unicode/emoji text

EmojiPalette
    = curated child-friendly choices for a visual picker
```

An Activity receiving `👨‍👩‍👧‍👦` from a keyboard/input method should still render/store it even if that exact emoji is not in the curated picker.

Do not reject valid child text merely because an emoji is absent from `EmojiPalette`.

---

## 13. Building a child-facing emoji picker

If a text-focused Activity needs direct emoji input, prefer the shared `EmojiPalette` model and large visual tiles.

Requirements:

- insert the selected `cluster` directly into the text as standard Unicode;
- derive tile/grid geometry from the Activity-safe responsive viewport;
- keep targets child-sized;
- do not require reading category names;
- category icons may use representative emoji;
- controller/touch/pointer navigation should converge on the same semantic selection model where those input profiles apply;
- keep the visible/retained item set bounded;
- do not download emoji or enumerate the entire Unicode standard at runtime.

The first-party Writing Activity is the current reference for a simple responsive picker.

An Activity does **not** need a picker merely because it renders emoji. Many Activities only need to display localized strings or child content containing emoji.

---

## 14. Emoji are not Greia system icons

Emoji support does not replace the Greia semantic icon system.

Do not implement system/trusted controls as arbitrary Unicode symbols such as:

```text
🏠  Home
⬅️  Back
⚙️  Settings
```

when Greia owns a canonical semantic icon/control.

In particular, Activities may not use emoji to impersonate or replace platform-owned Home/Back chrome.

Use emoji for:

- expressive child text;
- child creations;
- playful Activity content;
- appropriate feedback/labels;
- educational content where the symbol is semantically meaningful.

Use Greia semantic assets for:

- system navigation;
- trusted platform actions;
- canonical launcher/system concepts;
- controls whose visual identity must remain stable across Unicode/font versions.

---

## 15. Emoji presentation versus text presentation

Some Unicode symbols are emoji-capable but are not always meant to be colorful emoji.

The platform resolver respects Unicode presentation semantics, including variation selectors:

```text
©︎   text presentation
©️   emoji presentation
```

Activities should preserve the Unicode string they were given rather than stripping variation selectors or coercing every emoji-capable symbol into color rendering.

Do not normalize away VS15/VS16 merely for visual convenience.

---

## 16. Localization and emoji

Emoji do not make prose language-neutral automatically.

For example:

```text
"Choose the red apple 🍎"
```

is still English content and must follow Greia localization/language rules.

Localized strings may contain emoji normally:

```json
{
  "feedback.great": "Bravissima! 🌟"
}
```

Do not build grammar by concatenating emoji and translated fragments into an assumed English order. Keep using complete semantic localized messages.

Emoji should supplement communication where useful; they are not a substitute for the Activity's declared UI/content-language semantics.

---

## 17. Fonts shipped by an Activity

For ordinary Greia UI, **do not bundle private copies of Nunito Sans or Noto Color Emoji**.

Greia owns those platform resources and their rendering path.

An Activity may ship a custom font only for a legitimate pedagogical or expressive content need, subject to:

- redistributable license/provenance;
- package-size limits;
- readability;
- no impersonation of trusted Greia chrome;
- no replacement of the platform typography path for ordinary controls merely for style preference.

A custom content font does not make the Activity responsible for reimplementing the platform emoji fallback contract.

---

## 18. Performance and low-resource requirements

The Acer-class floor makes text architecture part of performance correctness.

Activity authors must:

- create/reuse a bounded typography owner rather than loading fonts per frame;
- reuse rendered static labels/surfaces where appropriate;
- avoid rerasterizing unchanged emoji every frame;
- keep picker/category models bounded;
- render only visible lines/items in large documents/collections;
- avoid scanning system fonts;
- avoid enumerating the Unicode emoji database at startup;
- clear renderer-owned caches at the appropriate teardown boundary;
- measure on realistic low-end hardware before claiming a large text/emoji-heavy UI is accepted.

The platform cache is bounded, but that is not permission for an Activity to create an unbounded second cache of composed labels.

---

## 19. Safe degradation is platform-owned

A supported release image is expected to contain the selected fonts/dependencies. However, a missing or corrupt emoji fallback must not become an Activity-specific crash path.

`GreiaTypography` degrades internally when its emoji fallback cannot be used. An Activity should not respond by:

- searching arbitrary host font directories;
- downloading a font;
- spawning `fc-match`/fontconfig commands;
- bundling an emergency private emoji font;
- treating the host's exact font installation as package authority.

If an Activity has a genuine product requirement that cannot tolerate degraded presentation, expose that through an explicit future platform capability/contract rather than probing host files directly.

---

## 20. Current limitations and future runtime boundary

The current implemented Activity-facing path is the Python/Pygame path.

Current important boundaries:

- `GreiaTypography.render()` and `measure()` operate one line at a time;
- there is no general-purpose platform text-editor widget yet;
- first-party Writing demonstrates current grapheme-safe editing semantics;
- the curated picker is a selection model plus first-party reference UI, not a mandatory global overlay;
- full Web Activity execution remains tied to R9;
- a future Web renderer must reproduce the **same Unicode/grapheme/persistence semantics**, but it need not use Pillow/Pygame/Noto in exactly the same implementation shape.

Do not expose Pillow, Noto's bitmap strike size, or Python `regex` as cross-runtime Activity semantics.

The semantic contract is:

```text
Unicode text
extended grapheme editing
correct emoji presentation
portable UTF-8 state
bounded platform typography resources
```

not a particular renderer library.

---

## 21. Reference implementation

Before implementing an editable Pygame text surface, inspect:

```text
activities/writing/main.py
src/greia_platform/typography.py
src/greia_platform/emoji_palette.py
src/greia_platform/pygame_ui.py
```

Writing demonstrates the current source pattern for:

- one reused `GreiaTypography` instance;
- mixed text/emoji rendering;
- grapheme-safe Left/Right/Backspace/Delete;
- grapheme-safe undo cursor restoration;
- wrapping by measured grapheme spans;
- pointer-to-caret hit testing;
- vertical movement by grapheme column;
- grapheme-safe document/preview bounds;
- a responsive visual `EmojiPalette` picker;
- normal UTF-8 persistence.

Reuse the **platform primitives and semantics**. Do not copy the entire Writing implementation into unrelated Activities.

---

## 22. Review/test checklist for an emoji-capable Activity

At minimum review representative mixed strings such as:

```text
Hello 🙂!
Bravissima! ⭐
Space 🚀 is fun
❤️ ☀️
👍🏽 👋🏻
👩‍🔬 👨‍🚀 🏳️‍🌈
🇮🇹 🇫🇷 🇯🇵
1️⃣ 5️⃣ #️⃣
Café / café
```

For editable text, verify:

- Left/Right never land inside a grapheme;
- Backspace/Delete remove one visible grapheme at a time;
- undo restores valid cursor boundaries;
- wrapping does not split a grapheme;
- pointer hit testing cannot place a caret inside a grapheme;
- truncation/previews never retain a partial cluster;
- save/reload preserves exact Unicode;
- arbitrary supported emoji received outside the curated picker still render/store correctly.

For rendering/UI, verify:

- ordinary text uses the Greia semantic typography path;
- expected emoji are colored rather than tofu/monochrome accidental fallback;
- mixed text aligns acceptably at child-facing sizes;
- responsive picker/content stays inside Activity-safe geometry;
- static rendering does not allocate unbounded surfaces;
- installed-size, first-render latency, cached-render latency and RSS remain acceptable on the target hardware class.

Relevant current repository regressions include:

```text
tests/test_typography_emoji.py
tests/test_writing_emoji_editing.py
```

Test-file presence is not evidence of PASS. Record the exact owner-controlled execution boundary.

---

## 23. Short author rule

If an Activity can show or edit child-visible text, remember:

> **Render text through Greia; edit by grapheme; store Unicode.**

And if it needs a picker:

> **Use the bounded Greia palette as input convenience, not as the definition of which emoji are valid.**
