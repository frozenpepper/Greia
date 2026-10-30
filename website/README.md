# Greia official website — work in progress

The parent-facing Greia website lives here. Open `index.html` locally, or serve this directory with any static file server. `downloads.html` and `library.html` are part of the same site. No build step, external font service, analytics service or production hosting is required for local review.

## Current publishing boundaries

The site describes the Greia OS direction and current source/development capabilities. It is **DESKTOP VISUAL REVIEW**, not an installed-device acceptance result. The site is published to https://www.frozenpepper.it/greia/ with the shared `site-ftp` tool (project `greia`). Project contact: **greia@frozenpepper.it** (homepage contact band, Downloads page and every footer).

The Downloads page offers the newest installer image per hardware target, read at page load from `updates/greia-updates.json` (`greia_os.installers`, see below). The first listed image is a **technical preview** for netbooks/PCs, not a family release; the page says so. Raspberry Pi controls stay disabled until a Pi image exists. The Activity library lists development previews; its per-Activity button stays disabled until a reviewed `.greiaactivity` package URL is added to that exact record in `library-data.js`. Parent authorization and Greia package checks still apply to installation.

The homepage section `#support` ("Free for every child") says that Greia is and stays free for families and that donations are welcome but never required. It also lists partnership routes: sponsors, NGOs, schools/universities, custom Activities, custom OS editions, and commercial licensing. Each route opens an email to greia@frozenpepper.it with its own subject. The licensing panel must stay consistent with `TRADEMARK.md` and `docs/governance/LICENSING_AND_TRADEMARK.md`: selling or preinstalling Greia and saying "Runs Greia OS" are free, while "Greia Approved", "Official Greia Partner" and logo branding need a written agreement. No formal certification programme is claimed. Donations use the owner's PayPal hosted button (`donate.js`, button `QU8KAK4X5S7VJ`, EUR). To keep the `PRIVACY.md` promise of no third-party scripts, PayPal's SDK loads only after a visitor clicks **Donate with PayPal**; if it fails, an email fallback appears. The repository's `.github/FUNDING.yml` points GitHub's Sponsor button at `#support`. The donation copy uses only the owner's own wording (free for all parents and children; donations welcome, never required); do not add claims about what donations fund unless the owner provides them.

The GitHub links point to the repository's canonical remote. Public repository visibility is a separate release-readiness gate.

## Asset provenance

- `assets/boot/frame_0000.png` through `frame_0051.png` are copies of Greia's canonical 222×600 rendered boot frames. The website replays these 52 frames unchanged. The final still shown after playback is `assets/boot/frame_0051-hires.png`, copied byte-for-byte from frame 51 of the original 1080×2922 boot render (`greia_boot_7fps_1080x2922/frame_0051.png`, kept outside the repository) (SHA-256 `6541349e78195b0318d156292a553c3d692eefc5d45009c378ecbeba789920e4`). The website does not change the OS boot animation.
- `assets/brand/greia-night-panorama-v2.png` is a website-only 16:9 extension generated with the high-resolution final frame as the visual reference (SHA-256 `7fba888b18862b8a871feb79ebea031790e46301424f0fa05892a7cdd21d8d0f`). It matches the original's near-black navy sky, fine blue mountain outlines, dense sharp pine silhouettes, tiny warm-window village and lilac flowers. The actual high-resolution boot frame is layered over it so the star-drawn G and Greia wordmark remain original pixels. The panorama is a derived background, not an original Greia master or exact vector reconstruction.
- The external `GREIA_BOOT_ANIMATION_LOCAL_AGENT_PATCH_2026-08-17` contains only rendered 222×600 frames, Plymouth playback configuration and verification code. Its playback script centers and advances the frames; it does not draw the landscape. No editable SVG or scene generator was found there. The high-resolution render directory above is the closest discovered source artwork.
- `greia-mark-light.svg` and `greia-lockup-light.svg` are website-specific small presentation derivatives. They do not replace the canonical boot/logo source.
- `assets/screens/*-en.png` are English real-service Simulator captures of the Shell or named source Activities, captured 23 September 2026. `encyclopedia-it.png` is the corresponding Italian capture used only in the language comparison. These are development screenshots, not physical-device or release proof.
- `assets/parent/this-greia-1024x600.png` is one real English Greia Parents development-client viewport from `../Greia-Parent-App-Html/tmp/parent-system-output-controls-acceptance-2026-09-02/1024x600_viewport.png`. The enlargement displays this single screen at a readable size.
- `assets/installer/*.webp` are offscreen renders of the real installer drawing code (`tools/installer_screenshots.py`, English, 1024×600, 30 October 2026). Disk and Wi-Fi names are the tool's sample data; the completion screen's demo-only "Close the demo" button was painted out because the real installer powers off instead.
- `assets/characters/`, `assets/voices/` and `assets/fonts/` are copies of accepted Greia cast art, recorded introductions and repository Nunito fonts for a standalone preview.

## Updating releases and packages

Installer images are hosted at `https://www.frozenpepper.it/greia/os-images/` and listed in the same static index Parent clients read for updates, `updates/greia-updates.json`. Installers live in `greia_os.installers` (newest first per target id); device and Parent update readers only read `greia_os.channels`, so an installer entry never becomes an update offer. `release-index.js` fills every `data-installer="…"` element (version, size, date, checksum, file name, boot modes, USB size) and every `data-installer-link` with the newest image, so publishing a new image needs no HTML edit:

```bash
site-ftp -p greia put <image>.img os-images/           # upload the exact image
python3 tools/build_installer_index.py --image <image>.img \
    --base-url https://www.frozenpepper.it/greia/os-images \
    --target legacy-x86-i386 --status technical-preview \
    --notes-en notes-en.txt --notes-it notes-it.txt \
    --index website/updates/greia-updates.json
site-ftp -p greia put website/updates/greia-updates.json updates/
```

Use `--status release` only for a release-gated family image, and add a target to `TARGETS` in the tool (plus a card on the page) before listing a new device class. Do not imply all x86 or ARM devices are certified by one file. The flashing, boot-menu and installer instructions on the page follow `docs/user/INSTALL_FROM_USB.md`; keep the two consistent.

For a verified individual Activity, set that item's `packageUrl` in `library-data.js` to its durable `.greiaactivity` URL after review. The library script then exposes its Download link in both the card and detail view. Keep Activity identity and screenshot provenance tied to the corresponding source manifest and package.

The superseded September 2026 website mockups are no longer part of the maintained source tree. The first direction was selected and developed here; the other two remain design history. See `docs/archive/reviews/2026-09-23_WEBSITE_DESIGN_STUDIES.md` (repository-root path) for the decision and exact Git revision containing the original prototype files.
