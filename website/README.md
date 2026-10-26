# Greia official website — work in progress

The parent-facing Greia website lives here. Open `index.html` locally, or serve this directory with any static file server. `downloads.html` and `library.html` are part of the same site. No build step, external font service, analytics service or production hosting is required for local review.

## Current publishing boundaries

The site describes the Greia OS direction and current source/development capabilities. It is **DESKTOP VISUAL REVIEW**, not an installed-device acceptance result or a public installer release. The Downloads page deliberately disables platform installer controls until an actual verified release artifact and named hardware scope exist. The Activity library lists development previews; its per-Activity button stays disabled until a reviewed `.greiaactivity` package URL is added to that exact record in `library-data.js`. Parent authorization and Greia package checks still apply to installation.

The GitHub links point to the repository's canonical remote. Public repository visibility is a separate release-readiness gate. The site is not deployed by this work.

## Asset provenance

- `assets/boot/frame_0000.png` through `frame_0051.png` are copies of Greia's canonical 222×600 rendered boot frames. The website replays these 52 frames unchanged. The final still shown after playback is `assets/boot/frame_0051-hires.png`, copied byte-for-byte from frame 51 of the original 1080×2922 boot render (`greia_boot_7fps_1080x2922/frame_0051.png`, kept outside the repository) (SHA-256 `6541349e78195b0318d156292a553c3d692eefc5d45009c378ecbeba789920e4`). The website does not change the OS boot animation.
- `assets/brand/greia-night-panorama-v2.png` is a website-only 16:9 extension generated with the high-resolution final frame as the visual reference (SHA-256 `7fba888b18862b8a871feb79ebea031790e46301424f0fa05892a7cdd21d8d0f`). It matches the original's near-black navy sky, fine blue mountain outlines, dense sharp pine silhouettes, tiny warm-window village and lilac flowers. The actual high-resolution boot frame is layered over it so the star-drawn G and Greia wordmark remain original pixels. The panorama is a derived background, not an original Greia master or exact vector reconstruction.
- The external `GREIA_BOOT_ANIMATION_LOCAL_AGENT_PATCH_2026-08-17` contains only rendered 222×600 frames, Plymouth playback configuration and verification code. Its playback script centers and advances the frames; it does not draw the landscape. No editable SVG or scene generator was found there. The high-resolution render directory above is the closest discovered source artwork.
- `greia-mark-light.svg` and `greia-lockup-light.svg` are website-specific small presentation derivatives. They do not replace the canonical boot/logo source.
- `assets/screens/*-en.png` are English real-service Simulator captures of the Shell or named source Activities, captured 23 September 2026. `encyclopedia-it.png` is the corresponding Italian capture used only in the language comparison. These are development screenshots, not physical-device or release proof.
- `assets/parent/this-greia-1024x600.png` is one real English Greia Parents development-client viewport from `../Greia-Parent-App-Html/tmp/parent-system-output-controls-acceptance-2026-09-02/1024x600_viewport.png`. The enlargement displays this single screen at a readable size.
- `assets/characters/`, `assets/voices/` and `assets/fonts/` are copies of accepted Greia cast art, recorded introductions and repository Nunito fonts for a standalone preview.

## Updating releases and packages

When a verified installer exists, replace the disabled control for its specific hardware class in `downloads.html` with a link to the exact artifact and publish its supported models, checksum, instructions and evidence scope. Do not imply all x86 or ARM devices are certified by one file.

For a verified individual Activity, set that item's `packageUrl` in `library-data.js` to its durable `.greiaactivity` URL after review. The library script then exposes its Download link in both the card and detail view. Keep Activity identity and screenshot provenance tied to the corresponding source manifest and package.

The superseded September 2026 website mockups are no longer part of the maintained source tree. The first direction was selected and developed here; the other two remain design history. See `docs/archive/reviews/2026-09-23_WEBSITE_DESIGN_STUDIES.md` (repository-root path) for the decision and exact Git revision containing the original prototype files.
