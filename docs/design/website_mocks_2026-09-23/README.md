# Greia public website concepts — parent story refinement, 23 September 2026

**Evidence:** DESIGN SPEC / DESKTOP VISUAL REVIEW. These are local, interactive website studies for owner review. They do not change the Greia Shell, Parent app, boot sequence, Activities or release state.

Open [the first concept, now refined for parents](storybook.html), or [the three-door chooser](index.html) to compare the other two directions. The first concept has been substantially rebuilt after owner review. The Wonder Map and Scribble Machine remain the previous third-pass explorations.

| Concept | How it works | Visual direction |
|---|---|---|
| [01 Greia for parents](storybook.html) | Seven chapters tell the mission and product story. Scroll, use the persistent navigation/dots or arrow keys; switch hardware and architecture views, inspect Parent app features, change a personal Activity example and play real character voices. An automatic, skippable opening replays all 52 original boot frames. | Editorial parent-facing story with sharply different chapter colours, a large moving Greia mark, strong typography, actual development captures and interactive explanations. |
| [02 The Wonder Map](constellation.html) | Drag the map, scroll or use ± to zoom, and open any of four Activity worlds. Each world opens a large, informative, colour-matched detail sheet. Arrow keys pan; Escape closes. | Playful spatial atlas: wandering dotted routes, illustrated islands, authentic screenshots, a central Greia boot mark, and no fixed reading order. |
| [03 The Scribble Machine](activity-fair.html) | Draw across the whole page, including over its type and artwork. Select ink colours, stamp the accepted characters, clear marks, and switch between Create, Play, Learn and Explore. Number keys 1–4 change worlds. | Sketch-first digital playground: a loud lime canvas, handwritten-feeling strokes, oversized type, a taped real Greia screenshot and floating product note. |

## Drawing interaction and text-selection fix

The Scribble Machine deliberately puts its drawing canvas above the surrounding artwork and words, with controls above the canvas. The page and its descendants use `user-select: none` and `-webkit-user-select: none`; the studio cancels `selectstart` and `dragstart`. Pointer drawing calls `preventDefault`, uses pointer capture and `touch-action: none`. This lets a stroke cross large headlines without selecting text or dragging an image. Clear removes both ink and character stickers. The only content unavailable to draw over is the raised control bar and navigation, so those controls remain usable.

## First concept: parent story and interaction

The seven chapters cover Greia's child-first premise, old hardware and ARM as co-equal design targets, its shared Activity/platform/hardware architecture, Greia Parents, personalized Activities and a proposed family Creation Pack, prerecorded character voices, and an open-project invitation. The page uses the navigation model the owner preferred from the first direction, with stronger scene transitions, large identity treatment and useful interactions inside the story. The opening plays the original 52-frame boot sequence on white, can be skipped or replayed, and respects reduced-motion preferences. Voice clips play only after a click and stop when the visitor leaves that chapter.

The Parent app screenshot is a real 2 September 2026 development capture from `Greia-Parent-App-Html/tmp/parent-system-output-controls-acceptance-2026-09-02/1024x600_viewport.png`; the copy identifies it as development evidence. Profile and Activity visibility management are existing product directions. Approved package installation is capability-gated while the normal release transport and lifecycle are completed. The parent-friendly Creation Pack flow and illustrative garden/train/sky cards are design proposals, not current self-service generation or installation. The architecture and hardware chapters describe target contracts without claiming that every reference device has passed release acceptance.

### Identity derivation

The supplied external `GREIA_BOOT_ANIMATION_LOCAL_AGENT_PATCH_2026-08-17` folder contains the 52 rendered PNG frames and Plymouth script, but no editable SVG master. The final raw frame is [`frame_0051.png`](../../../assets/boot/frames/frame_0051.png). For this website study, `assets/greia-mark-{light,ink}.svg` redraw the connected star G from that frame; `assets/greia-lockup-{light,ink}.svg` add wordmark contours traced from the same final frame. The white boot intro keeps the original frames unchanged. These clean-background SVGs are **website exploration derivatives**, not an accepted replacement for canonical Greia brand artwork. Review their line weight and typography against the original frame before using them beyond this mock.

## Greia grounding

- [`frame_0051.png`](../../../assets/boot/frames/frame_0051.png) is the authentic final raw Greia boot frame; [`greia-boot-logo.png`](../../../assets/boot/static/greia-boot-logo.png) is its generated white 1024×600 presentation canvas. The first concept replays the original frames proportionally, then uses the derivative transparent mark and lockup described above. The source contract is [`GREIA_BOOT_EXPERIENCE.md`](../GREIA_BOOT_EXPERIENCE.md).
- Character images are the accepted six-member runtime cast from [`GREIA_CANONICAL_CAST_SYSTEM.md`](../GREIA_CANONICAL_CAST_SYSTEM.md).
- Product claims are grounded in the repository [`README.md`](../../../README.md), [`CHILD_ACTIVITY_DISCOVERY_AND_AUDIENCE.md`](../../product/CHILD_ACTIVITY_DISCOVERY_AND_AUDIENCE.md), [`PHASE0_CORE_CREATION_ACTIVITIES.md`](../../product/PHASE0_CORE_CREATION_ACTIVITIES.md), and [`ACTIVITY_SYSTEM_NAVIGATION.md`](../../product/ACTIVITY_SYSTEM_NAVIGATION.md).
- In-page product images link to historical development Greia Simulator captures under [`docs/reviews/visual/`](../../reviews/visual/): the child Shell, Painting, Magic Maze, Magic Aquarium and Shape Garden. They are not fresh production or physical-hardware evidence.
- The pages reuse the licensed Nunito Sans files already in [`assets/fonts/nunito-sans/`](../../../assets/fonts/nunito-sans/). No shared Greia art source or runtime implementation was modified.
- The first concept's Lilli, Flash and Momo buttons play existing accepted English introductions under `assets/audio/characters/shared/v0.2/_intros/en/`. They demonstrate the prerecorded voice direction, not completion of voice placement in every Activity.

## External design research and translation

I reviewed the live [Awwwards Sites of the Month list](https://www.awwwards.com/websites/sites_of_the_month/), the [Ponpon Mania award entry](https://www.awwwards.com/sites/ponpon-mania) and live comic, the [Lama Lama award entry](https://www.awwwards.com/sites/lama-lama-2) and live site, and the [Anime.js award entry](https://www.awwwards.com/sites/anime-js). For this refinement I also reviewed the [ERA Residence award entry](https://www.awwwards.com/sites/era-residence), whose highlighted preloader and scroll storytelling reinforced the direction. The useful ideas were **art-led full-screen scenes and chapter movement**, **identity as an active part of the entrance**, and **interaction as the page's content rather than a decorative hover**. Greia's own mark, characters, screenshots, product structure and copy determine the implementations here. No layout, artwork or code was copied from those sites.

## Review evidence

The `*-preview.png` files and `index-preview.png` are 1440×900 Chromium captures. I inspected the opening screens, interior illustrated scenes, map detail sheets and responsive phone layouts. Chromium checks at 1440×900, 390×844 and 320×700 found no missing loaded images, page errors or horizontal overflow. Tests exercised scene navigation, map dragging/opening/closing, sketch drawing across headline text, colour changes, stamping, world switching and clearing. A drawn stroke produced canvas pixels while `window.getSelection()` remained empty. This verifies the website mocks only.

The refined first concept has its own [`storybook-overview.png`](storybook-overview.png) contact sheet and updated [`storybook-preview.png`](storybook-preview.png). I inspected all seven desktop chapters and mobile chapters, including 320×700 and 390×844. Browser interaction checks covered intro skip/replay, chapter/menu navigation, the device and architecture switches, Parent app topics, Activity idea switching and playback of an actual voice clip. A final 320-pixel Chromium check found no horizontal overflow or missing loaded images. This is **DESIGN SPEC / DESKTOP VISUAL REVIEW** of the local website mock, not production web deployment, Greia runtime acceptance or hardware proof.
