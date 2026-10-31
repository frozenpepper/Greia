# Greia — Child Creations and Cross-Activity Media (Product Requirements)

**Status:** ACCEPTED CHILD-FACING GOALS / IMPLEMENTATION IN PROGRESS  
**Adopted:** 2026-10-07  
**Single implementation and release program:** Creations Library + Activity Release Plan (internal record archived)  
**Exact session state:** Progress (internal record archived)

## 1. Core promise

Greia is a place where children **make things and build on what they previously made**. A drawing, recording or simple text creation can move from one compatible Activity to another without a conventional filesystem, folder dialog, desktop, filename or reading requirement.

Required early flows:

- Create / save / reopen/edit PNG pictures in Painting.
- Import a picture into Shape Garden's shape/stamping composition; export a flattened result back into Painting.
- Choose a child's picture as a backdrop in Teatrino and reopen the saved show even if the library picture later changes or is removed.
- Record narration or singing, **listen to it before selecting it** in another Activity, and compose new work from that recording.
- Save / reopen/import compatible plain UTF-8 text in Writing and selected other creative Activities.
- Browse an obvious child-facing **My Creations** collection and deliberately delete unwanted creations with safe confirmation.

Existing Activity autosave **must remain automatic** and should not create another shareable artifact for every stroke or typed character. Publication of a work for use by other Activities should be a clear, child-friendly operation. The platform's preview/picker behavior must be identical across compatible Activities rather than requiring authors to build file browsers.

## 2. Universal picker and viewer

The common Greia picker must show **large, high-quality previews**:

- Images: large thumbnails with preserved proportions (target roughly two cards per row on the 1024×600 floor), tap to expand/zoom.
- Audio: tap **Play** on a recording card to hear the actual recording, **before** committing a selection; provide visible Pause/Replay/Stop and progress state. Never autoplay recordings or continue playing after dismissal/profile switch/Home.
- Text: illustrated document preview plus readable excerpt for children who can read; symbols and layouts remain the primary navigation.
- All: age-appropriate oversized touch/point targets, keyboard/arrow/controller navigation, no dependence on typing or reading filenames, no raw file paths or extensions, no technical empty-state errors.

A normal viewer presents the child's images, sounds and texts in a single semantic collection, with useful filtering and previews. Every item can be inspected and safely deleted; deletion is clearly intentional, individually targeted, and may not recursively destroy project snapshots another Activity saved.

Mandatory Greia system Home/Back remains outside the Activity's drawing/input authority, including while the picker is visible.

## 3. Typed compatibility, not shared filesystem permission

The platform supports stable, versioned, portable **Creation Artifacts**:

- media family / canonical file type (initially PNG, WAV, UTF-8 text);
- semantic role (drawing, backdrop, narration, song, sticker, story);
- immutable ID and child-profile ownership;
- origin/producer Activity, creation time, integrity and bounded preview metadata.

A manifest's produced/consumed media types describe **what an Activity can work with**. These declarations do not automatically authorize it to list, read, copy, export or delete every creation. Greia gives the consuming Activity a bounded selected-artifact handle only after the child chooses one in the trusted picker. The producer can publish validated content from its own private files. This preserves the existing per-Activity sandbox.

An imported artifact is an independent versioned snapshot by default; no saved Theatre show breaks because the child later edits or deletes its original Painting image. Cross-app PNG exchange does **not** pretend to preserve all editable brush strokes/stamp layers. Native draft/project data remains inside its producing Activity.

Any new media type requires an explicitly reviewed validator/normalizer, preview behavior, portable representation and resource budget; arbitrary untrusted file types are not automatically supported.

## 4. Adaptive capacity and safe disk headroom

Greia must not force a small Acer-derived fixed user-library size on devices with much larger media. The initial policy target is roughly **75% maximum used space on the real writable persistent data volume**, plus a **minimum 512 MiB free reserve**, subject to calibration against update/backup/rollback staging and actual partition layout.

For a hypothetical single writable 8 GiB volume, total filesystem consumption would stop growing around 6 GiB, not 6 GiB of new child content plus already-used OS files. On partitioned storage with separate system A/B areas, calculate from actual writable PERSIST capacity, not total advertised disk size. Guard growth from **all** private and shared data-writing services, not only the creations library.

Single media payload limits are still independently bounded for safe decoding and memory consumption; large physical disks do not make giant image/audio memory allocations safe.

When space runs low, show a friendly prompt to revisit My Creations. Never silently delete a child's existing work, drafts or recordings. Deletion is user-initiated and frees space without breaking other retained projects.

## 5. Privacy, persistence and accessibility

- Creations are owned by an explicit child profile and are invisible to sibling profiles unless a future explicit parent-reviewed family-sharing workflow is designed.
- No media content in routine progress/achievement events, diagnostic logs or telemetry.
- Offline-first; no cloud required.
- Compatible with portable logical backup/restore across x86 and ARM. Removing the originating Activity does not erase published creations.
- Child-facing library/picker UX works without reading proficiency or knowing what a file is.
- Avoid excessive CPU, disk work and memory: lazy visible thumbnails, bounded caches, no media decode on every frame.
- Localized large visual controls and optional prerecorded guidance; do not assume runtime TTS availability for arbitrary text.

## 6. Evidence and exclusions

The product requirements here are **not** a declaration of GUI/Simulator completion. P1 trusted repository, P2 manifest/session broker/SDK, P3 **My Creations** viewer + reusable picker, and a trusted in-Activity modal handoff now exist as **SOURCE-WIP**. Legacy-X raises/focuses Greia's existing Shell window only after re-proving the focused Activity window belongs to the exact supervised PID, then restores that Activity and keeps Home/Back above the modal; the Simulator routes its existing synthetic display/input transport to the same Shell picker while suppressing Activity frame overwrite. The broker still never grants arbitrary Activity listing/deletion/minting. Painting now deliberately publishes PNG and exposes a child-visible import action from its private gallery; it requests the platform picker nonblockingly, polls at a bounded cadence, imports only one child-selected handle, validates digest/type and creates an independent editable private painting. **This complete interaction is unexecuted in the current full checkout/GUI and therefore not accepted.** Wayland/KMSDRM modal implementations, Shape Garden, Theatre, audio/text consumers, curation, portable backup, all-writer storage headroom and installed-hardware validation remain open.

No conventional Linux file manager, uncontrolled cross-Activity shared folder, automatic network upload, generic plugin executor, office-like Save As dialog, or per-Activity home-made file picker belongs in the baseline product.
