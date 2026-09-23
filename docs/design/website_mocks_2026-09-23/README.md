# Greia public website studies — 23 September 2026

**Evidence:** DESIGN SPEC / DESKTOP VISUAL REVIEW. These are local website studies for owner review, not a released Greia website or new OS acceptance evidence.

Open [the three-concept chooser](index.html). The first direction, [Greia for parents](storybook.html), is the current refinement target. The Wonder Map and Scribble Machine preserve the distinct spatial and drawing-led alternatives from the third pass.

| Concept | Visitor operation | Direction |
|---|---|---|
| [01 Greia for parents](storybook.html) | Watch or skip the actual 52-frame logo reveal; browse a long-form parent guide; filter/enlarge 12 product captures; switch hardware, architecture and Parent app explanations; combine child interests and play modes; play six real cast introductions; open FAQs. | A wide, animated Greia night landscape, strong typography, colour-changing editorial sections, authentic product evidence and detailed parent-facing copy. |
| [02 The Wonder Map](constellation.html) | Drag and zoom a spatial map, then open four Activity worlds in any order. | Illustrated Greia atlas without a fixed reading sequence. |
| [03 The Scribble Machine](activity-fair.html) | Draw across the entire page, change ink, place character stickers and switch four worlds. | A sketch-first interactive playground. |

## Current first direction

The owner rejected the previous white-screen intro and thin parent story. The opening now expands the boot landscape into a full-page, website-specific night scene with mountains, forest, village lights, flowers, stars and fireflies. At the centre, it replays Greia's unchanged 52 original PNG boot frames. The persistent interface and call to explore fade in after the animation. Skip, replay, Escape and reduced-motion behaviour are supported. The widescreen terrain is `assets/greia-night-wide.svg`, drawn specifically for this mock using the visual motifs of the boot frame; it is not a replacement boot asset.

The small transparent G/wordmark derivatives have heavier paths and crisp star centres for navigation-size legibility. They remain **website-study derivatives**, not accepted canonical brand masters. The original final frame is [`frame_0051.png`](../../../assets/boot/frames/frame_0051.png). The external `GREIA_BOOT_ANIMATION_LOCAL_AGENT_PATCH_2026-08-17` contains rendered PNGs and Plymouth code, but no editable SVG source. The first mock uses its own SVG landscape around the real rendered frames; the repository boot sequence is untouched.

The page is written for parents and covers:

1. What a child actually sees: profile choice, Greia Shell, Painting, Writing, playful Activities and Encyclopedia development scenes, with 12 inspectable historical captures.
2. Why keeping early Acer Aspire One hardware useful is part of the mission, alongside Raspberry Pi 400/500 as co-equal ARM targets, offline use and tight resource discipline. Acer specifications on the page are planning estimates, not a compatibility promise.
3. The child Shell, universal Activity contract, Greia platform services and hardware layer, plus platform-owned Home, profile saves, trust, input and progression boundaries.
4. The Greia Parents client: child profiles, audience choices, device controls and parent-authorized Activity installation, with an enlargable real development capture.
5. Personalized Activity ideas and the contributor creation path. The interactive idea card illustrates a future family-friendly Creation Pack; it does not generate or install an Activity. Existing authoring guides, validator, real-service Simulator and bounded new-install service are distinguished from the incomplete ordinary-release lifecycle.
6. The six accepted characters and six existing prerecorded English introductions. Buttons play real `.ogg` files; no model runs on the child's device for these clips.
7. Eight direct answers about offline use, old devices, creative Activities, installation, voices and portable child data, with explicit pre-public status.

The Parent client image is the full development capture copied from `../Greia-Parent-App-Html/tmp/parent-system-output-controls-acceptance-2026-09-02/desktop.png` relative to the Greia OS workspace. The twelve Shell/Activity images come from dated review captures in `docs/reviews/visual/`; the page labels them as development or Simulator evidence. They are not fresh physical-device or final-release proof. The six voices use `assets/audio/characters/shared/v0.2/_intros/en/`. The cast images come from `assets/visual/runtime/v1/characters/`.

## Other concept behaviour

The Scribble Machine puts its drawing canvas above the surrounding artwork and words, with controls above the canvas. Its page and descendants use `user-select: none` and `-webkit-user-select: none`; the studio cancels `selectstart` and `dragstart`. Pointer drawing calls `preventDefault`, uses pointer capture and `touch-action: none`. This lets a stroke cross large headlines without selecting text or dragging an image. Clear removes both ink and character stickers. Raised controls and navigation remain usable.

The Wonder Map is a draggable/zoomable four-world atlas with informative detail sheets. Its different movement model is intentional: it remains a separate exploration route, not a page skin for the first concept.

## Research and evidence

The earlier passes reviewed the live [Awwwards Sites of the Month](https://www.awwwards.com/websites/sites_of_the_month/), [Ponpon Mania](https://www.awwwards.com/sites/ponpon-mania), [Lama Lama](https://www.awwwards.com/sites/lama-lama-2), [Anime.js](https://www.awwwards.com/sites/anime-js) and [ERA Residence](https://www.awwwards.com/sites/era-residence) entries. The relevant ideas were an art-led entrance, purposeful movement and interaction carrying actual content. This revision applies them to Greia's own boot identity, visual motifs and product structure; it copies no external artwork, layout or code.

[`storybook-preview.png`](storybook-preview.png) is the current 1440×900 first screen; [`storybook-overview.png`](storybook-overview.png) shows the eight main page areas. [`index-preview.png`](index-preview.png) captures the chooser. I inspected the desktop and mobile compositions. Chromium checks at 1440×900, 390×844 and 320×700 exercised all screenshot categories, gallery navigation and enlargement, hardware/architecture/Parent/Activity switches, Parent capture enlargement, FAQ and actual Lilli audio; all twelve gallery image paths and loaded page images resolved, with no JavaScript errors or horizontal overflow. A normal-motion run reached frame 52/52 and verified replay/skip; reduced-motion runs went straight to the completed state. `node --check` passed for `storybook.js`.

`make verify` also ran on macOS and exited with three errors and one failure in the Linux-only X8 product lifecycle test module (`test_session04_legs`); a focused rerun reproduced the host gate. It is not recorded as a passing Greia OS gate.

This evidence concerns the website mock only. It does not close Greia runtime, release, physical-device, Parent pairing or Encyclopedia gates.
