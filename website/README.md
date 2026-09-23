# Greia official website — work in progress

The parent-facing Greia website lives here. Open `index.html` locally, or serve this directory with any static file server. `downloads.html` and `library.html` are part of the same site. No build step, external font service, analytics service or production hosting is required for local review.

## Current publishing boundaries

The site describes the Greia OS direction and current source/development capabilities. It is **DESKTOP VISUAL REVIEW**, not an installed-device acceptance result or a public installer release. The Downloads page deliberately disables platform installer controls until an actual verified release artifact and named hardware scope exist. The Activity library lists development previews; its per-Activity button stays disabled until a reviewed `.greiaactivity` package URL is added to that exact record in `library-data.js`. Parent authorization and Greia package checks still apply to installation.

The GitHub links point to the repository's canonical remote. Public repository visibility is a separate release-readiness gate. The site is not deployed by this work.

## Asset provenance

- `assets/boot/frame_0000.png` through `frame_0051.png` are copies of Greia's canonical rendered boot frames. The website replays them unchanged against a wider, website-specific SVG landscape.
- `assets/brand/greia-night-wide.svg`, `greia-mark-light.svg` and `greia-lockup-light.svg` are website-specific presentation derivatives. They do not replace the canonical boot/logo source.
- `assets/screens/*-en.png` are English real-service Simulator captures of the Shell or named source Activities, captured 23 September 2026. `encyclopedia-it.png` is the corresponding Italian capture used only in the language comparison. These are development screenshots, not physical-device or release proof.
- `assets/parent/this-greia-1024x600.png` is one real English Greia Parents development-client viewport from `../Greia-Parent-App-Html/tmp/parent-system-output-controls-acceptance-2026-09-02/1024x600_viewport.png`. The enlargement displays this single screen at a readable size.
- `assets/characters/`, `assets/voices/` and `assets/fonts/` are copies of accepted Greia cast art, recorded introductions and repository Nunito fonts for a standalone preview.

## Updating releases and packages

When a verified installer exists, replace the disabled control for its specific hardware class in `downloads.html` with a link to the exact artifact and publish its supported models, checksum, instructions and evidence scope. Do not imply all x86 or ARM devices are certified by one file.

For a verified individual Activity, set that item's `packageUrl` in `library-data.js` to its durable `.greiaactivity` URL after review. The library script then exposes its Download link in both the card and detail view. Keep Activity identity and screenshot provenance tied to the corresponding source manifest and package.

The old visual studies remain under `docs/design/website_mocks_2026-09-23/`. Their first-concept URL redirects here, while `storybook-historical.html` preserves the last mock for historical review.
