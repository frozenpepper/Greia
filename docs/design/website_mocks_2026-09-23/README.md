# Greia website concepts — 23 September 2026

**Evidence:** DESIGN SPEC / DESKTOP VISUAL REVIEW. These are standalone public-website mockups, not Greia Shell, Greia Parents, or release UI.

Open [`index.html`](index.html) locally to compare three deliberately different approaches:

| Concept | Visual approach | How a visitor uses it |
|---|---|---|
| [01 Storybook](storybook.html) | Warm cream, large type, soft illustration and the shared cast | Scrolls through a short beginning-to-end product story |
| [02 Constellation](constellation.html) | Dark atlas, night-sky map, single focused detail panel | Chooses one of six stars in any order to explore a product idea |
| [03 Activity Fair](activity-fair.html) | Bright graphic directory, editorial sidebar, real Activity icons | Searches, filters by real Collection categories, and opens Activity details |

## Source grounding

- Product model and release status: `README.md`, `HANDOVER.md`, `docs/product/CHILD_ACTIVITY_DISCOVERY_AND_AUDIENCE.md`, and `docs/product/PHASE0_CORE_CREATION_ACTIVITIES.md`.
- Character identities: `docs/design/GREIA_CANONICAL_CAST_SYSTEM.md`. Images are the existing accepted runtime PNGs under `assets/visual/runtime/v1/characters/`.
- Greia palette and Nunito: `runtime/theme-defaults.toml` and `assets/fonts/nunito-sans/`.
- Activity Fair data: the selected first-party `activities/*/activity.toml` presentation categories, recommended ages, and existing `assets/icon.png` files. Descriptions are short website summaries, not canonical educational claims.

All three pages are dependency-free HTML/CSS/JavaScript. They link to repository assets rather than copying or modifying canonical art. The pages deliberately state that Greia is in pre-public development. They contain no live Parent or device connection, installer, release call to action, or claim of hardware acceptance.

## Visual check

The three `*-preview.png` files are Chromium desktop viewport captures at 1440×900. Each page was also rendered at 390×844; no horizontal overflow, missing loaded images, or JavaScript page errors were found. The Constellation selector and Activity Fair filter/detail dialog were exercised. These checks cover the mock pages only.
