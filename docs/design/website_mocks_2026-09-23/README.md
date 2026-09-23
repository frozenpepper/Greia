# Greia public website explorations — 23 September 2026

**Evidence:** DESIGN SPEC / DESKTOP VISUAL REVIEW. These are standalone, local website concepts for discussion. They are not the Greia child Shell, Parent app, a release website, or proof of current device behavior.

Open [the comparison page](index.html), then enter any of the three directions. Each opens on Greia's actual boot identity: [`frame_0051.png`](../../../assets/boot/frames/frame_0051.png) or its canonical [white 1024×600 boot composition](../../../assets/boot/static/greia-boot-logo.png). The narrow, vertical constellation is intentionally preserved rather than stretched into a substitute logo.

| Direction | Visual language | Visitor operation |
|---|---|---|
| [01 The Portal](storybook.html) | Luminous white editorial entrance, oversized type, a moving ribbon, cream product story, deep navy conclusion | Replay the 52 real boot frames, then scroll through four chapters; the product capture and cast member change with the chapter. On a phone, each chapter carries its own capture. |
| [02 Orbit](constellation.html) | Dark spatial field, moving orbit, character nodes, a central image portal | Choose one of six cast stars in any order. The central Greia capture, story, colour and selected node change together. Use the arrow controls, keyboard arrows, or drag across the map. |
| [03 Play Lab](activity-fair.html) | A white boot-screen start that opens into a bold coral interactive canvas | Press Start, draw on the page with a pointer, change drawing colours, clear marks, and switch between Create, Play, Learn and Explore. Keys 1–4 also change worlds; Back returns to the boot entrance. |

## Greia sources and boundaries

- Product story: repository [`README.md`](../../../README.md), [`CHILD_ACTIVITY_DISCOVERY_AND_AUDIENCE.md`](../../product/CHILD_ACTIVITY_DISCOVERY_AND_AUDIENCE.md), [`PHASE0_CORE_CREATION_ACTIVITIES.md`](../../product/PHASE0_CORE_CREATION_ACTIVITIES.md), and [`ACTIVITY_SYSTEM_NAVIGATION.md`](../../product/ACTIVITY_SYSTEM_NAVIGATION.md).
- Boot identity: [`assets/boot/frames/`](../../../assets/boot/frames/) and [`GREIA_BOOT_EXPERIENCE.md`](../GREIA_BOOT_EXPERIENCE.md). The original white-screen presentation grounds all three entrances.
- Cast: [`GREIA_CANONICAL_CAST_SYSTEM.md`](../GREIA_CANONICAL_CAST_SYSTEM.md) and existing accepted runtime PNGs under [`assets/visual/runtime/v1/characters/`](../../../assets/visual/runtime/v1/characters/).
- Type and palette: the existing Nunito Sans files under [`assets/fonts/nunito-sans/`](../../../assets/fonts/nunito-sans/) and Greia theme values in [`runtime/theme-defaults.toml`](../../../runtime/theme-defaults.toml).
- Product imagery: historical **development Greia Simulator captures**, from the visual reviews of the child Shell, Painting, Magic Aquarium, Magic Maze, Shape Garden, Bridge Building and Momo's Faces under [`docs/reviews/visual/`](../../reviews/visual/). They show actual test-run screens; they are not fresh release or physical-device evidence. The specific paths are referenced directly by each page.

The concepts are local HTML/CSS/JavaScript and reuse existing files by relative path. No canonical art or Greia runtime source is modified. Website copy is conceptual, and all pages identify the project as pre-public development.

## External design research

The [Awwwards current Sites of the Month](https://www.awwwards.com/websites/sites_of_the_month/) list was reviewed on 23 September 2026. The [Lama Lama Awwwards entry](https://www.awwwards.com/sites/lama-lama-2) informed the idea of starting from a distinctive identity and letting it transform into content. The [Ponpon Mania entry](https://www.awwwards.com/sites/ponpon-mania) informed direct scene interaction and chapter-like movement. These are interaction references, not copied layouts, artwork or code.

## Review and interaction check

The three `*-preview.png` files are 1440×900 Chromium desktop captures. All three pages and the comparison page were also rendered at 390×844 and 320×700. At those sizes, loaded images resolved, there were no JavaScript page errors, and the document width did not exceed the viewport. The Portal boot replay returned to frame 0051 and the scroll chapter changed the stage; Orbit node selection and arrow-key movement changed the story; Play Lab's Start, category keys, pointer drawing, Clear and Back controls were exercised. This is browser-mock verification only.
