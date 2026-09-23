# Greia public website concepts — third design pass, 23 September 2026

**Evidence:** DESIGN SPEC / DESKTOP VISUAL REVIEW. These are local, interactive website studies for owner review. They do not change the Greia Shell, Parent app, boot sequence, Activities or release state.

Open [the animated three-door chooser](index.html). The previous Portal / Orbit / Play Lab page structures were discarded after owner review. All three new pages use Greia's real final boot artwork, accepted cast and historical development Simulator captures, but now have distinct interaction models and stronger art direction.

| Concept | How it works | Visual direction |
|---|---|---|
| [01 Worlds in Motion](storybook.html) | Five full-screen illustrated scenes replace conventional sections. Scroll, use the scene dots or arrow keys. The opening card replays Greia's real boot frames when tapped. | Kinetic comic/poster: hard cuts between yellow, coral, violet, mint and navy; giant words, layered product captures and characters. |
| [02 The Wonder Map](constellation.html) | Drag the map, scroll or use ± to zoom, and open any of four Activity worlds. Each world opens a large, informative, colour-matched detail sheet. Arrow keys pan; Escape closes. | Playful spatial atlas: wandering dotted routes, illustrated islands, authentic screenshots, a central Greia boot mark, and no fixed reading order. |
| [03 The Scribble Machine](activity-fair.html) | Draw across the whole page, including over its type and artwork. Select ink colours, stamp the accepted characters, clear marks, and switch between Create, Play, Learn and Explore. Number keys 1–4 change worlds. | Sketch-first digital playground: a loud lime canvas, handwritten-feeling strokes, oversized type, a taped real Greia screenshot and floating product note. |

## Drawing interaction and text-selection fix

The Scribble Machine deliberately puts its drawing canvas above the surrounding artwork and words, with controls above the canvas. The page and its descendants use `user-select: none` and `-webkit-user-select: none`; the studio cancels `selectstart` and `dragstart`. Pointer drawing calls `preventDefault`, uses pointer capture and `touch-action: none`. This lets a stroke cross large headlines without selecting text or dragging an image. Clear removes both ink and character stickers. The only content unavailable to draw over is the raised control bar and navigation, so those controls remain usable.

## Greia grounding

- [`frame_0051.png`](../../../assets/boot/frames/frame_0051.png) is the authentic final raw Greia boot frame; [`greia-boot-logo.png`](../../../assets/boot/static/greia-boot-logo.png) is its generated white 1024×600 presentation canvas. The artwork is shown proportionally and never recoloured or replaced. The source contract is [`GREIA_BOOT_EXPERIENCE.md`](../GREIA_BOOT_EXPERIENCE.md).
- Character images are the accepted six-member runtime cast from [`GREIA_CANONICAL_CAST_SYSTEM.md`](../GREIA_CANONICAL_CAST_SYSTEM.md).
- Product claims are grounded in the repository [`README.md`](../../../README.md), [`CHILD_ACTIVITY_DISCOVERY_AND_AUDIENCE.md`](../../product/CHILD_ACTIVITY_DISCOVERY_AND_AUDIENCE.md), [`PHASE0_CORE_CREATION_ACTIVITIES.md`](../../product/PHASE0_CORE_CREATION_ACTIVITIES.md), and [`ACTIVITY_SYSTEM_NAVIGATION.md`](../../product/ACTIVITY_SYSTEM_NAVIGATION.md).
- In-page product images link to historical development Greia Simulator captures under [`docs/reviews/visual/`](../../reviews/visual/): the child Shell, Painting, Magic Maze, Magic Aquarium and Shape Garden. They are not fresh production or physical-hardware evidence.
- The pages reuse the licensed Nunito Sans files already in [`assets/fonts/nunito-sans/`](../../../assets/fonts/nunito-sans/). No shared Greia art source or runtime implementation was modified.

## External design research and translation

I reviewed the live [Awwwards Sites of the Month list](https://www.awwwards.com/websites/sites_of_the_month/), the [Ponpon Mania award entry](https://www.awwwards.com/sites/ponpon-mania) and live comic, the [Lama Lama award entry](https://www.awwwards.com/sites/lama-lama-2) and live site, and the [Anime.js award entry](https://www.awwwards.com/sites/anime-js). The useful ideas were **art-led full-screen scenes and chapter movement**, **identity as an active part of the entrance**, and **interaction as the page's content rather than a decorative hover**. Greia's own mark, characters, screenshots, product structure and copy determine the implementations here. No layout, artwork or code was copied from those sites.

## Review evidence

The `*-preview.png` files and `index-preview.png` are 1440×900 Chromium captures. I inspected the opening screens, interior illustrated scenes, map detail sheets and responsive phone layouts. Chromium checks at 1440×900, 390×844 and 320×700 found no missing loaded images, page errors or horizontal overflow. Tests exercised scene navigation, map dragging/opening/closing, sketch drawing across headline text, colour changes, stamping, world switching and clearing. A drawn stroke produced canvas pixels while `window.getSelection()` remained empty. This verifies the website mocks only.
