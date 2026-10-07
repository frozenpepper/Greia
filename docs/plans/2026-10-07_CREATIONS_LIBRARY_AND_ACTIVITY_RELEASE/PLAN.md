# Greia — Creations Interoperability and First-Party Activity Release Program

**Created:** 2026-10-07  
**Status:** ACTIVE — owner-requested, session-by-session product/content workstream  
**Branch:** `main` (no side branches or GitHub Actions)  
**Scope:** All 45 built-ins, child-facing Creations Library, universal picker/viewer, image/audio/text interoperability, catalogue curation, product polish, testing, release readiness  
**Current working ledger:** [PROGRESS.md](./PROGRESS.md)  
**Initial curriculum strategy:** [ACTIVITY_CATALOGUE_AGES_3_5_STRATEGY.md](../../product/ACTIVITY_CATALOGUE_AGES_3_5_STRATEGY.md)  
**Existing lifecycle authority:** [2026-09-15_MULTIPLATFORM_RELEASE_INSTALL_UPDATE_COMPLETION.md](../2026-09-15_MULTIPLATFORM_RELEASE_INSTALL_UPDATE_COMPLETION.md)  
**Existing architecture prerequisites:** [2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md](../2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md)

## 0. Why one program, and what it does not override

This is the **single entrypoint for the new Creations Library + Activity/catalogue release-quality work**. It brings previously separate UX, interoperability, curriculum, game difficulty, packaging, performance and Activity-quality work into an explicit integrated sequence. Agents should not create independent plans for Painting, Teatrino, audio sharing, catalogue consolidation or per-Activity quality unless this program delegates a clearly bounded specialist document.

It does **not** replace the accepted architecture constitution, the active OS architecture remediation plan, the visual-foundation plan, or the authoritative installer/first-boot/A/B release-lifecycle route. Those remain the owners of their existing facts. A product change is not a reason to bypass current first-boot fixes, build/provisioning prerequisites, trust boundaries or hardware acceptance. Work here may safely advance at the source/desktop level while physical evidence remains unproven. For release, both this program **and** the existing platform lifecycle route must be accepted. The owner explicitly requested a unified catalogue/Creations release program; this document provides that scope without rewriting historical lifecycle evidence.

**Do actual implementation, not ceremonial gates.** Focus on the real upstream→service→broker→SDK→Activity→picker/viewer→persistent backup path. Tests exist to catch real regressions. If a failure is ordinary source/fixture debt, repair it in the owning layer; stop only for real destructive/privilege/paid/hardware-boundary risks or when valid evidence is unavailable. No routine one-shot token-expensive gate bureaucracy.

## 1. Product outcomes / non-negotiable user journeys

1. **Painting → Theatre:** create and edit a drawing; preserve its private editable work; deliberately save/publish a picture; reopen Painting to view/edit it; from Teatrino select it using large visual thumbnails and use it as a show backdrop; save/reopen the show; changes or deletion of the source do not silently mutate/break the saved show.
2. **Painting ↔ Shape Garden / stamps:** import an image as a visual base; add stamps/shapes; export the composition to My Creations; reopen the flattened composed image in Painting and continue painting. Preserve native editing state separately; do **not** promise cross-app preservation of editable shape/stroke layers for V1.
3. **Voice → creative work:** a child records a song or narration; a compatible Activity opens the universal picker; taps Play to hear **the audio before choosing it**; selects it; adds effects or uses it in a scene; saves and reopens a durable output.
4. **Writing ↔ story/postcard:** UTF-8 text exports/imports into genuinely compatible text experiences; original private drafts persist; text need not be readable to operate the library.
5. **My Creations:** one highly visible child-facing universal library viewer, not a Linux file browser. Children can browse pictures, recordings and documents, preview each, and deliberately delete unwanted items through age-appropriate safeguards. Deletion actually reclaims space; it cannot silently erase copies embedded in other saved projects.
6. **Shared picker:** the same platform-owned selection experience works inside every compatible Activity, with role/type filtering and a purpose-specific action (e.g. “Choose a backdrop”). No file extensions, directory paths or tiny filename grids appear to the child.
7. **Scales with the device:** data capacity is based on the real mounted writable profile-data filesystem, not an Acer-hardcoded 32 MiB library and not an advertised whole-disk figure including OS/recovery/A/B partitions. In an illustrative truly writable 8 GiB volume, the initial 75% occupancy rule caps total volume use around 6 GiB, **not** 6 GiB of child files in addition to system data.
8. **Privacy and ownership:** creations belong to the active profile. No sibling-profile leakage. Third-party Activities cannot enumerate a child's creations just by declaring “can read images.” No network or cloud dependence.

### 1.1 Pre-reader UX standard

- Big content-first preview cards. At 1024×600, target about two large image cards per row with roughly 300–400 logical-pixel thumbnails, not 20 tiny desktop file icons.
- Image previews preserve aspect ratio, transparency and proper framing; never silently crop the only identifying content. Large expanded single-item preview before delete.
- Audio cards have large **Play / Pause / Replay** controls, explicit progress/duration, meaningful animated waveform/mascot (not required to read an audio title), and stop playback on dismissal, replacement, Activity stop or profile switch. Playback begins only after the child taps Play; never autoplay another child's recording.
- Text cards use distinctive illustrated preview cards; a readable excerpt is helpful for older children but navigation must remain symbol-first. Dynamic text-to-speech is **not** silently assumed: voice/TTS architecture, privacy and available runtime have to be validated before offering read-aloud arbitrary text.
- Focus, directional navigation, keyboard, pointer, touch and gamepad selection must follow the Greia input contract. Target hit areas must respect real physical-size guidance, not pixel resolution alone.
- Picker and viewer use Greia Screen/Overlay/Collection components; platform-owned Home/Back remains higher-trust and unobstructed. No desktop-style Open/Save dialogs.
- List pages load bounded metadata and lazy thumbnails. Cache only visible/current-page images. Never decode full-resolution media every frame.
- **Deletion:** select item → large preview and visible trash affordance → deliberate hold/confirmation with a distinct cancel path. Show a brief undo opportunity when technically feasible. Delete only the chosen library item, not any independently saved/imported snapshots. A backed-up restore path is a separate parent-facing responsibility. No automatic eviction of child work merely to make quota room.
- A disabled or missing compatible creation state must be a pleasant illustrated empty state, not an error or an unresponsive control.

### 1.2 What counts as a 'shareable type'

Separate **media type** from **semantic usage**.

| Family | Initial canonical format | Roles / uses (examples) | Future |
|---|---|---|---|
| Image | `image/png` | drawing, background, sticker, character, collage | JPEG, animations, SVG only with reviewed sanitization |
| Audio | `audio/wav` | song, voice, narration, sound-effect, music | Ogg/Opus, MIDI after reviewed decoders |
| Text | `text/plain` UTF-8 | story, caption, postcard, poem | styled story documents, scene scripts |
| Composite | V1 consumer-private project JSON | show, layered scene, authored level | declarative scene format, animation, video, 3D |

A file extension is not a safety proof; platform codecs validate/decode and normalize bounded media. Extensions are registered explicitly in a platform codec registry. Do not add arbitrary file execution, autodiscovered plugins or untrusted import paths.

The **stable ID** identifies an immutable published artifact snapshot; optional source project IDs and revisions may relate successive publications. Compatible Activities exchange exported, portable representations rather than private Pygame/Python object structures. The producer's native editable format remains Activity-private unless a later separately standardized composition format is accepted.

## 2. Architecture and trust design

### 2.1 Correct ownership map

- **Private drafts/projects:** `ActivityStorageService`, scoped to `(profile_id, activity_id)`; existing Painting, Writing, Theatre and voice storage stays intact.
- **Published creations:** one platform-owned `CreationLibrary` namespace per child profile. It is **not** installed as a normal Activity, not a world-readable folder, and not directly mounted into an Activity sandbox.
- **Types/codecs:** `CreationMediaRegistry` with narrow per-format handlers for validation, canonical encoding, metadata and previews. Future extension is explicit composition, not a giant `if extension` tree in every Activity.
- **Capacity:** one common `VolumeBudget` policy measures the actual writable data filesystem before growth, enforces a proportional occupancy ceiling and a minimum boot-safe free-space floor. It must eventually govern *all* persistent user-data growth, not just creations; otherwise a different Activity could fill the device.
- **Authority:** trusted supervisor computes producer and current child-profile identity; `PermissionBroker` combines package intent and parent policy. Activity environment variables are descriptive, never authorization.
- **Transport:** prefer extending/composing the existing per-session storage broker transport instead of a second disconnected security stack. Separate logical domains (private storage vs Creations service) remain distinct services. Bounded framed reads/writes, deadlines, payload limits, typed error codes, session lifecycle cleanup.
- **Selection:** platform-owned picker/controller. An Activity requests a compatible kind and role; the **child** chooses; broker grants an opaque, session-scoped read handle for **one** selected artifact. Forged, expired, cross-profile or cross-session handles are rejected. No automatic library enumeration for a consumer Activity.
- **Publishing:** declare producer media types and roles in validated manifest metadata. Publisher sends a private-storage source reference or bounded payload over the broker. Broker derives the source Activity identity from trusted session authority and validates the actual bytes. Do not let Activity callers supply another profile ID or privileged filesystem path.
- **Viewer/delete:** profile-bound trusted Shell/My Creations surface; deletion authority stays there, never implied by `consumes` declarations. No broad `creations.delete` grant to arbitrary Activity sessions.
- **SDK:** one semantic `Greia.creations` contract with equivalent Python and eventual Web adapter, portable descriptors and selection handles. API examples in this plan are **proposed**, not present until each phase lands.

### 2.2 Proposed manifest semantics

Example (schema must be integrated into authoritative `ActivityManifest`/runtime policy; not valid yet):

```toml
[creations]
produces = ["image/png"]
consumes = ["image/png"]
roles_produced = ["drawing", "background"]
roles_consumed = ["background", "sticker"]
```

Manifest declarations are compatibility claims, not security grants. The trusted broker enforces rights and request filters. No per-Activity private codec forks.

### 2.3 Snapshot/dependency rule

Consumer saves **embed/copy a selected representation** or otherwise pin an immutable version with an owned retained reference. In V1 prefer a bounded independent snapshot: it makes saved shows survive edits/deletion/replacement of originals and avoids complex reference-counting, circular dependencies and accidental live modification. Delete in the library never reaches into another Activity's project. Later deduplication is an internal optimization with no semantic change.

### 2.4 Storage budget and the 8 GB example

**Default policy candidate:** occupancy ceiling = **75% of actual writable persistent data filesystem** and floor = **512 MiB free**; effective allowed growth is the stricter of the two. Calibration must use real installation partition geometry, workload, update/rollback staging requirements, Linux filesystem overhead and per-machine protected-space demands.

Example: if an *entire writable* 8 GiB volume is currently 2 GiB used, up to 4 GiB more user data may grow before reaching 6 GiB used. If the physical 8 GiB disk has separate system A/B/recovery partitions and only 4 GiB available to persistent data, limits are derived from that **4 GiB writable volume**, never the whole 8 GiB.

Use real `disk_usage` facts from the durable data mount (not a configured physical drive model). Account for: active and rollback states, SQLite journaling, staging copies, media normalization overhead, thumbnails, other children, installer/update reserve and backup/export staging. Refuse writes before filling the protected margin; **never silently delete existing creations**. Make private-Activity namespace quotas capacity-aware without allowing one Activity to bypass the shared system-level guard. A maximum *single payload* and bounded caches still protect RAM/CPU independently of disk size, so a huge disk must not allow a 2 GiB single image decode on a 768 MiB machine.

The initial code's per-Activity policy `runtime/storage-policy.toml` currently imposes 32 MiB namespace / 16 MiB per-file / 64 MiB reserve. This **must be reconciled later**, rather than replaced by an unsafe percentage in just one code path.

### 2.5 Security, persistence and failure rules

- Reject malformed/misdeclared media, oversized dimensions/duration, expansion bombs, symlinks, traversal, invalid indices, and unsupported formats.
- Bound metadata, files, preview sizes, decoders and page sizes. Never run untrusted media as code.
- Preserve profile isolation across launcher, separate Linux trust domains, simulator, Parent management and reinstall/restore.
- Transactional publish: normalize to a temporary file, fsync/atomic promote, metadata commit; on errors avoid advertising missing content. Handle crash orphans via bounded, safe reconciliation (never blind directory cleanup). Read verifies bytes/digest.
- Deletion should be atomic from the user's perspective and reclaim space; if power fails, make the record consistent and permit a bounded repair. Uninstalling the *producer Activity* does not remove creations.
- Backups/restores enumerate semantic Creation records and validated bytes, not machine paths; dormant projects still retain imported images/audio.
- Import from USB/removable media goes through the existing read-only scanner/trust boundary; do not invent auto-execute import.
- No creation payload in achievements, history, ordinary telemetry, error logs or Parent analytics.
- No app-owned permanent media background daemons. GUI/audio resource owner must stop and clean up on picker dismiss/stop/profile switch.

## 3. Actual existing source anchors (2026-10-07 snapshot)

- `src/greia_platform/storage.py`: `ActivityStorage` and `ActivityStorageService` private namespace.
- `src/greia_launcher/storage_broker.py`: one session Unix-socket broker, private-file/KV actions.
- `src/greia_platform/storage_client.py`: runtime-neutral client.
- `src/greia_platform/storage_protocol.py`: bounded framing, protocol version.
- `src/greia_launcher/supervisor.py`: sandbox command, broker lifetime, trusted authority.
- `src/greia_platform/permissions.py`: trusted grants.
- `src/greia_platform/profiles.py`: profile root and child/Parent directory ownership; recent first-boot fixes are mandatory.
- `src/greia_platform/customization.py`: existing reusable bounded image import concepts; not a child-created library.
- `src/greia_platform/ui_core.py`, `activity_ui.py`, `pygame_ui.py`: child UI composition.
- `activities/painting/painting_model.py`: private PNG records and autosave.
- `activities/writing/writing_model.py`: UTF-8 text documents.
- `activities/storie_della_mia_voce/voice_services.py`: saved WAV scenes.
- `activities/teatrino_fiabe/teatrino_model.py`: private JSON shows/WAV narration.
- `activities/shape_garden/garden_model.py`: creative shape placement; candidate stamps/collage bridge.
- `docs/product/ACTIVITY_CATALOGUE_AGES_3_5_STRATEGY.md`: prior 41-Activity baseline; currently **45** built-ins after the October 1 four-game tranche.

**Known new-game issues to repair during release triage:** `colline_allegre` script-launch import failure (package-relative sibling imports), noisy `auto_upright=false if False else False`, `quattro_amici` manifest D1–D5 vs actual four configured modes. Package import tests cannot substitute for launching the script with the actual runtime command. A subsequent curated-import test is not sufficient to detect script-versus-package relative-import failures.

## 4. One ordered session-by-session implementation plan

### P0 — Pin actual state, assemble release audit (part of every relevant session)

1. Refresh `main`, read `AGENTS.md`, this plan, [PROGRESS.md](./PROGRESS.md), `HANDOVER.md`, relevant skills/ADRs and the live lifecycle plan.
2. Preserve prior boot/installer tests/evidence; do not hotpatch the Acer or change physical media in an unrelated Activity session.
3. Inventory all built-ins from `activities/*/activity.toml`, not fixed numbers; reconcile with installed runtime index and release source composition.
4. Run focused source checks when test environment is available, then `make verify` before claiming a code tranche accepted. If unavailable, record SOURCE-EDITED/UNVERIFIED rather than fake PASS.
5. Maintain the **per-Activity release matrix**, precise changes, direct evidence, known blockers and next task in `PROGRESS.md`.

**Acceptance:** exact source scope and evidence boundary known; no speculative “45 polished games” claim.

### P1 — Typed creation repository and measured capacity policy

Build the foundation behind a trusted-only boundary:

- data/descriptor schema with stable ID, producer, MIME, semantic role, creation time, size, integrity digest, preview metadata;
- explicit PNG, WAV and UTF-8 adapters with strict bounded input validation and canonical normalization;
- immutable publish/read/page-list/preview/delete in a profile-owned repository;
- image thumbnails generated once on publication, large enough for attractive gallery cards; audio preview returns actual playable selected audio; UTF-8 cards expose bounded preview;
- volume budget based on writable filesystem usage with 75% default ceiling + independent absolute free reserve;
- deterministic tests: malformed payload, checksum corruption, symlink/traversal, hostile sizes, isolation, concurrent publish/delete, power-cut recovery design, 8 GiB example, full-volume rejection, zero silent eviction;
- explicit storage schema version and future migration path;
- no Activity SDK or direct filesystem surface yet.

**Acceptance:** pure headless repository and capacity tests PASS locally, source review, safe error states; no claim of working cross-Activity picker.

### P2 — Platform broker, authority, SDK and manifest

- Decide final service composition via the existing per-session transport; implement a narrow `CreationsSessionFacade`, not a global mutable “file manager.”
- Add authoritative validated manifest produce/consume declarations, proper index serialization and package/trust checks.
- Broker derives profile, producer, media claims and grants from trusted `ActivityAuthority`; enforce no broad enumeration/reading/deletion.
- Selection requests/returns use opaque scoped handles, expiry, one-shot or bounded reuse; no forged/cross-profile handles.
- Publishing reads private source via the owning trusted storage service; normalize/snapshot; receiving app can import selected bytes/representation via bounded fetch.
- Python SDK first, mirrored semantics for Web later; keep simulator using the same owners, not simulator-only policy.
- Failure matrix: denied, revoked, cancelled, duplicate, timeout, slow producer, system full, corrupt media, missing file, profile switched, Activity exits during selection.
- Tests for full `supervisor→broker→SDK→source store` path, actual script launch (not only package import), sandbox deny rules and cleanup.

**Acceptance:** one full provider-free session test for legitimate publish, child-authorized select/read and adversarial denial. Untrusted Activity cannot read another's private bytes or enumerate the library.

### P3 — Universal child picker and library viewer

**Implementation architecture warning (confirmed 2026-10-07):** The actual Greia launcher synchronously supervises an Activity in `LauncherApplication._launch_selected()`. While an Activity is running, `ActivitySupervisor.poll()` is called in a waiting loop and the Activity, not the Shell, owns the visible display surface. Rendering a `CreationsGalleryScreen` on the Shell's ordinary Home surface **does not** make it available inside a running Activity. Do not claim the platform picker is integrated merely because its renderer/controller exists.

The source now implements the bounded **Activity session selection request → storage broker → trusted Supervisor observation → trusted Shell modal → child choice → one-use grant → Activity poll/import** path, with MIME/role filtering and fail-closed presenter availability. Read the dedicated [P3 Trusted Picker Display Contract](./P3_TRUSTED_PICKER_DISPLAY_CONTRACT.md): the current Legacy-X compatibility backend reuses Greia's existing full-screen Shell window, re-proves the currently focused Activity window's `_NET_WM_PID` against the exact supervised process immediately before presentation, raises/focuses the Shell, restacks mandatory Home/Back above it, and restores the same Activity window afterward. Native window IDs remain backend-private. The Simulator implements the same semantic modal contract through its existing remote display bridge: while the picker owns the synthetic display, Activity frame uploads cannot overwrite it and ordinary remote input is diverted to the real Shell picker while Home remains platform-owned. There is no Simulator-only picker UI or alternate selection IPC.

This is **SOURCE-WIP, not accepted UI/display evidence**. The current concrete modal backends are Legacy-X compatibility and Simulator remote transport; future Wayland/KMSDRM implementations must satisfy the same runtime-neutral `ShellWindowController` lease semantics without importing X11 assumptions. Full-checkout unit/socket tests, real Pygame screenshots, pointer/keyboard/controller behavior, audio preview, cancel/Home/Activity-exit restoration and installed-hardware focus/stacking evidence are still required before P3 promotion. The standalone `My Creations` Home viewer remains a separate use of the same gallery view model, not a substitute for the in-Activity modal.


One semantic `CreationsPicker` and `MyCreationsViewer` with a shared adapter-independent view model. Platform-owned presentation/input, not each Activity's custom menu; no lasting X11-specific API.

- Images: 384×320-ish normalized previews, large cards, zoom/inspect full-screen, visible-page cache and memory bound.
- Audio: waveform/character/icon, **Play/Pause/Replay before selection**, progress/time, focus/stop lifecycle.
- Text: illustrative document preview and optional readable excerpt; not text-only navigation.
- Filters: requested MIME and permitted semantic roles, active-profile ownership, sections/tabs without a desktop tree, friendly empty states.
- Picker: cancel, select, visual confirmation, return to same Activity and state, input focus restored.
- Viewer: open/preview, delete using hold+picture confirmation and undo window, no reliance on names; no accidental sibling removal.
- Accessibility/age: 3-year-old pre-reader task trial, screen sizes 1024×600 plus small/large/aspect variants, physical hit-size, keyboard/gamepad/pointer/touch, animation limits and localized narration/labels.
- Integrate `My Creations` visibly from Create (not hidden inside Parent settings). Treat it as a Greia-owned Screen/Collection, not a standard Activity with broad storage permissions.
- Benchmark idle CPU, picker startup, image cache RSS, audio preview CPU/memory, thousands of items paginated.

**Acceptance:** guided child-flow simulator screenshots reviewed as actual images; no tiny icons, illegible filename dependency, clipped Home control, leaked audio or unbounded decode. Real Acer screenshots/performance owed at its hardware milestone.

### P4 — Painting ↔ Shape Garden ↔ Theatre complete image round trip

Sequence in one tested vertical slice before broad rollout:

1. Painting keeps private autosave. A deliberate Save-to-My-Creations action creates a versioned immutable PNG; never publish every 1-second autosave.
2. Painting SOURCE-WIP now exposes a picture-arrow-down action from its private gallery, starts the universal picker non-blockingly, polls it at a bounded 120 ms cadence, imports only the one-use child-selected PNG handle, validates digest/type, and creates a **new independent private editable painting** without overwriting the shared snapshot or prior canvas. This path is still unexecuted in a complete checkout/GUI; test cancel/Home, undo, resize, transparency, blank/new, unavailable presenter and quota errors.
3. Shape Garden is currently a **transient random shape-growing experience, not a persistent sticker editor**. P4 must first add a legitimate versioned editable picture/shape project (or review and nominate the actual stamp-style Activity), then import a selected picture, keep an independent private source snapshot, add shapes, persist them, and deliberately export a composed PNG; do not overwrite the existing garden gameplay merely to force a cross-app demo.
4. Painting reimports Shape Garden output and continues free drawing; publishing yields a new snapshot, not destructive source overwrite.
5. Teatrino picks an image as background, displays it without catastrophic stretching/incorrect crop, saves its own independent snapshot, and reopens correctly if the library original was edited/deleted.
6. Exercise every step in actual script launch and real simulator, and review screenshots at 1024×600 plus variation sizes.
7. Performance/calibration on Acer *after* boot/install source acceptance.

**Acceptance:** end-to-end persistent round trip, large picker preview, independent snapshots, no loss of a previous project and no Activity trust leak.

### P5 — Voice/audio and text interoperability

- Storie della Mia Voce exports normalized WAV recordings; receiving Theatre and another genuinely useful sound-effects/composition Activity can play/insert them.
- The universal picker must let a child **listen before selecting** with safe audio ownership. No competing microphone capture while the preview player holds output.
- Theatre's recorded narration/audio artifacts have understandable durable semantics: complete show project stays private as native JSON+WAV; published narration WAV stays shareable.
- Writing publishes Unicode UTF-8; Writing can open/import compatible creations. Posta di Leo and story experiences integrate only where the interaction is truly meaningful.
- Do not add another generic audio player or text editor merely for this feature; use current Activities.
- Test Italian/English, long/empty/invalid text, control characters, truncated WAV, no microphone and busy capture device, interruption and app exit.

**Acceptance:** one tested image, audio, text cross-Activity workflow each; preview-before-commit and reopen after reboot simulated and physically validated later.

### P6 — Catalogue and release selection authority

- Introduce an **explicit first-party release Activity selection** in the build/manifest/index composition owner; keep experiments in source without automatically shipping them.
- No ad hoc list in Shell or parallel release flags in every app. One trusted declarative selection with canonical installer/index equality checks and tests.
- Derive release set from quality evidence: Anchor/Keep, Improve before ship, Merge/Replace, Exclude/Experimental. Do not mechanically meet a count.
- Optimize child-facing Create/Play/Learn/Explore overlaps, discovery tags and adaptive subcollections; fix questionable Create memberships and ensure large real collection groups can subdivide completely and naturally.
- Age min/max and nominal/adaptive difficulty must reflect real gameplay: foundation D1–2, developing D3–4, stretch D5–6. Do not invent D7–10 merely to fill metadata.
- Launch guidance: **24–28 truly polished content Activities** minimum credible, **32–36** strong first-party catalogue, not a mandatory count; Painting/Writing stay required anchors.
- Keep official catalogue/distribution and Parent hide/age/difficulty policy consistent with built image and third-party install paths.
- Diagnose actual overlap (counting, literacy, nature) from gameplay, not names. Prioritize missing sorting/patterning, Stop-Go/executive function, sequencing/story comprehension, vocabulary, science prediction, social problem-solving and music over generic filler.

**Acceptance:** deterministic build tests prove only approved IDs ship, installed index matches, no hidden app bypasses Parent policy, docs record why each exclusion is intentional.

### P7 — Deep quality and visual review of **all 45** existing built-ins

For **every** item in §5, inspect `activity.toml`, actual main launch path, modules, saved data, content, input, sounds, text/localization, visual assets, screenshot, events, difficulty/age claims, gameplay value, CPU/RAM budget, and suitability to 3/4/5-year-olds.

Checklist per Activity:

1. Boot from the **same Python script invocation** used by the supervisor (and package import separately), enter first frame and mark READY within timeout.
2. Safe Home return, clean stop/teardown, no unhandled broker/storage/audio errors or stale permission.
3. Actual gameplay and teaching value: real feedback, unique contribution, no false success, challenge variants matching manifest; child can understand goal without reading.
4. Visual critique: approachable original art, composition, contrast, shadows/effects only where efficient, legible at 1024×600 and aspect/device variants, no screen-edge/chrome overlap, no ugliness hidden by green unit tests.
5. Input: mouse/keyboard/controller/touch where declared, reserved OS controls not intercepted, age-appropriate controls.
6. Voice/localization: Italian/English output/prompt parity, meaningful localized spoken guidance, correct character voices, no dynamically synthesized unapproved runtime speech, title audio completeness.
7. Storage: autosave/restore, schema/backup, corruption and full-disk behavior, no silent loss; Creations integration for genuinely creative apps only.
8. Performance: warm start, idle CPU, frame budget (30 Hz presentation target for static UI; action games may need 60 Hz when evidence supports it), RSS, no hot-path I/O/decode/font rebuild.
9. Educational portfolio: conceptual redundancy, exact family roles, three/four/five developmental suitability, realistic difficulty.
10. Decision: **ANCHOR**, **KEEP**, **IMPROVE**, **MERGE/REPLACE** or **DO NOT SHIP**, with evidence/commit, not guesswork.

Fix the October 1 games' runtime/metadata issues first, including Colline launch and Quattro difficulty. Review Vol(o) Draghetto failure/challenge progression. Prefer repairing authentic game design, not adding a patchy “difficulty=6” constant.

All 45 items are in the tracked inventory §5; every row must receive an evidence-backed decision before product catalogue closure. Do not erase earlier R7.3 modernization achievements; this is a distinct **gameplay/visual/release** acceptance pass.

### P7a — Focused priority order

1. Four new games + existing Volo Draghetto, Labirinto Magico, Costruiamo Ponti (immediate high challenge/launch risk).
2. Painting, Shape Garden, Morbidi Mostriciattoli, Teatrino, voice stories, Writing, Posta di Leo (creation interoperability / saves).
3. All remaining first-party Activities, grouped by real developmental portfolio rather than arbitrary alphabetical order.
4. Verify launcher collections, Parent policy, release composition, spoken names, audio readiness as a whole.

### P7b — Pedagogy audit

Review 3/4/5 progression against Head Start ELOF/NAEYC/CDC as references, not hard laws. Differentiation focus:

- numeracy: subitizing, patterning, comparison/measurement, number composition rather than four near-identical counting loops;
- literacy: listening/oral vocabulary, rhyme/phonological awareness, syllables, letters, sequencing/comprehension;
- science: predictions and experiments (float/sink, ramps, shadows, plants, materials);
- executive/social: attention, stop/go, switching rules, empathy, turns, social problem solving;
- music: pulse, rhythm, audio memory, movement prompted away from screen;
- action: real mastery/failure with gentle retry, spatial navigation, physics, block planning, Connect 3/4/local two-player.
- creation: free expression, reusable outputs and between-app creative journeys.

New educational Activity additions are **candidates**, only approved if a distinct gap remains after existing apps are repaired/combined. Avoid catalogue inflation.

### P8 — Whole-product acceptance and release handoff

- Fresh profile → create image/audio/text → share→preview→import→edit→save→delete→reopen; cross-profile isolation; no parent/secret leaks; update/uninstall preservation; backup/export/restore on different CPU architecture when the platform backup route is available.
- Build with explicit curated selection, compare exact included Activity index against release manifest.
- Simulate each launched Activity with first READY, input, two meaningful tasks, optional failure, Home, memory/perf. Verify at least one hard-level loop per game.
- Actual screenshot review by a human/vision model for every release-selected Activity, with layout matrix for 1024×600, 800×480 where supported, 1280×720/1366×768 and narrow/wide aspect; physical-size touch checks on actual devices when possible.
- Physical Acer: first boot must already pass the *separate* lifecycle plan, then evaluate gallery scrolling, audio preview and no audio contention, Painting↔Shape Garden↔Theatre, and memory/full-volume scenarios via **non-destructive** limited fixtures; no filling the physical disk to test quotas.
- ARM Raspberry Pi and other hardware acceptance per existing platform lifecycle plan; do not let a GUI simulator be called hardware proof.
- Publish one deliberate release roster, evidence table, regressions/known limitations, parent documentation and installed package/bytes constraints. Old repo-only experiments stay accessible to contributors.

**Completion:** The Creations feature is genuinely usable from the Shell and integrated Activities, all declared release Activities have sound child UX and acceptance, curation is explicit and release-profile verified, and the existing OS lifecycle release route also passes. Source work alone cannot close physical acceptance.

## 5. First-party Activity inventory and release-review queue (45 items)

**Statuses below are review assignments, not endorsements or drop decisions.** All begin `UNREVIEWED-FOR-RELEASE` at creation of this program, even if previously passed an R7.3 structural migration or unit test. Decisions live in [PROGRESS.md](./PROGRESS.md).

| Activity ID suffix / source directory | Family / differentiated role | Specific review / interoperability priority |
|---|---|---|
| `acquario_magico` | nature/cause-effect | genuine creation? Explore membership, depth, visual interest |
| `alfabeto_leo` | literacy/alphabet | age-2 floor, spoken guidance, phonics overlap |
| `baia_delle_orche` | nature/care/sound | musical interaction, audio feedback and curiosity |
| `bosco_numeri` | early math/counting | overlap with garden/train/Momo quantity games |
| `bottega_delle_misure` | measurement | real compare/measure progression, D1–D5 |
| `casa_del_dieci` | number composition | advanced play distinctness, D1–D5 |
| `clinica_cuccioli` | self-care/empathy | non-reader clinical cues; social reasoning depth |
| `colline_allegre` | physics vehicle/action | **script-entrypoint blocker**, source quality, controls/physics challenge |
| `corsa_bacche` | maze-chase/action | playability, AI unfairness, difficulty/level mapping, honest retry |
| `costruiamo_ponti` | building/physics | authored problem quality, D2–D6, performance |
| `cucciolo_mio` | caregiving | care overlap vs genuine differentiated progression |
| `enciclopedia_greia` | reference/nature | coverage/art assets and child comprehension; its own visual plan |
| `faccine_momo` | emotions | move beyond recognition? scenario reasoning, spoken feedback |
| `festa_delle_rime` | phonological/rhymes | meaning of D1–D4, separation from syllables |
| `foresta_parole` | words/phonics | age-5 literacy challenge and comprehension |
| `il_giardino_dei_numeri` | subitizing/counting | overlap; strong age-2/3 introductory loop |
| `la_discesa_della_biglia` | marble/physics | causal predictions, difficulty, visual outcome |
| `labirinto_magico` | spatial maze | D1–D6 actually playable, navigation/input smoothness |
| `luci_di_momo` | subitizing/comparison | distinguish quantity goals from basic counting |
| `memory_meraviglie` | memory/vocabulary | executive-function depth, difficulty |
| `mondo_contrari` | language concepts | broaden adjective/position/category vocabulary |
| `morbidi_mostriciattoli` | make creatures | publish PNG/stickers, standalone creative uniqueness |
| `nanna_delle_nuvolette` | sequencing/care | true first/next/last and calming narrative |
| `nascondino_bosco` | observation/attention | visual search challenge and art assets |
| `officina_dei_suoni` | phonemes/word building | sound correctness, level progression |
| `orchestra_animali` | rhythm/music | **sole dedicated music family**; deepen actual rhythm/movement |
| `painting` | required creation anchor | **first image producer+consumer**, own gallery, undo, revisions |
| `pasticceria_magica` | cooking/counting/making | counting redundancy, creation value |
| `piccola_serra` | plant/nature | prediction, experiment interaction, cause/effect |
| `posta_di_leo` | postcards/literacy | optional import/export text; pre-reader composition |
| `quattro_amici` | connect strategy/multiplayer | **declared D5 but only four modes**, CPU and two-player UX |
| `quattro_stagioni` | seasons/weather | meaningful loops vs passive observation |
| `shape_garden` | stamping/shapes/creative | **Painting ↔ stamps PNG roundtrip**; editable state preserved |
| `sillabe_magiche` | syllables | nominal D1 vs age-5+ consistency |
| `sottomarino_giramondo` | marine exploration | weak Create placement? discovery/content depth |
| `specchi_magici` | symmetry | actual D1–D5 geometry and spatial planning |
| `stelle_incantate` | shapes/stars/science | distinguish from counting and astronomy facts |
| `storie_della_mia_voce` | audio storytelling | **WAV producer**, capture reliability, picker audio preview |
| `teatrino_fiabe` | puppet stories | **image/audio consumer**, saved-show stability |
| `torre_forme` | spatial shapes action | age modes, falling timing, failure, input, visual art |
| `treno_numeri` | early math | overlaps, spoken instruction, age calibration |
| `viaggio_delfino` | action/marine | whether truly action/motor distinct from dragon |
| `volo_draghetto` | reaction/fine motor | genuine optional lose/hearts/checkpoints/challenge D1–D6 |
| `workshop_settings` | My Greia/system | **not child-content count**; control/accessibility/Parent-policy trust |
| `writing` | required text anchor | UTF-8 producer+consumer, emoji/graphemes/large text |

Activity membership, difficulty and age are always corroborated from the current manifest; this table is a starting review queue, not a replacement for source/metadata authority.

## 6. Test and evidence matrix (minimum)

| Layer | Automated/inspection evidence required | Hardware dependency |
|---|---|---|
| Pure media codecs | invalid/corrupt files, oversized dimensions/duration, canonical formats, previews, normalization | no |
| Capacity policy | synthetic 8 GiB, small volumes, partition boundary, multiple profiles, all-writers occupancy, no eviction | source no; real disk probe later |
| Creation database | atomic publish/read/delete, rollback/orphans, tampering, index migration, paginated list, resource pressure | source no |
| Broker/security | no cross-profile, unauthorized enumeration/read/delete, handle forgery/expiry, altered environment, cleanup | simulator + production sandbox |
| Picker/viewer UX | large thumbnails, audio play/pause, visible deletion controls, tiny screens, controller/touch, Home chrome | local simulator; touch/hit size physical |
| Painting/Shape Garden/Theatre | persistent image roundtrip, snapshots, source deletion, aspect/alpha/undo | local simulator + Acer |
| Voice/Writing | WAV preview, capture/busy devices, UTF-8, no TTS assumption, durable import | local simulator + audio hardware |
| All 45 Activities | exact Python script launch, READY, activity stop, input, child task and failure, screenshots, visual critique | local simulator + selected physical |
| Release assembly | curated manifest exact parity with on-image package index, trust, Parent hide/age policy | image build + boot/hardware |
| Release performance | frame time/RSS/CPU/disk/budget under load, audio latency, memory-noise fixtures | Acer and other target profiles |

**Local agent instructions rule:** Only when a real hardware step is required, provide **one complete copy-paste instruction block** with checkout SHA, prerequisites, exact commands, no destructive shortcuts, expected output, stop conditions, evidence to return and what failures mean. Do not send piecemeal instructions. Fresh flash/install requires explicit user authorization under the existing lifecycle plan; no automatic wipe simply because this product plan reaches hardware phase.

**Self-test rule:** When a runnable local repository and dependencies are available, launch the real Python Activities under the simulator, use actual screenshot capture and inspect rendered screenshots, not only green tests. If the current environment lacks a checkout, Pygame, display or credentials, say so; run what can actually run (e.g. pure headless modules) and record the missing evidence precisely.

## 7. Session contract and release-tracker use

For each session:

1. Re-read the two documents in this folder plus AGENTS/HANDOVER and actual source before editing.
2. Choose the next **small, coherent vertical slice**, preferring actual user-visible completion over layers of speculative abstractions. Implementation authority may repair ordinary problems discovered in an adjacent owner module; do not let a stale skills checkbox veto sensible work.
3. Work on `main`, refresh first and preserve concurrent commits; do not run GitHub Actions.
4. Run focused tests; run full `make verify` when local repo/toolchain is accessible; use screenshots in a real GUI run when applicable. Record exact commands, tests, SHA and which environment ran them.
5. Append a dated row to [PROGRESS.md](./PROGRESS.md) with **phase, files, result, tests, risks, next one step**, plus update HANDOVER and the legacy active plan ledger as relevant. Never rewrite prior result.
6. Commit coherent changes, including tracker updates, under readable messages. An incomplete phase stays **WIP/UNPROVEN** and is not falsely called RELEASE-PASS.

### Minimum release decision record per Activity

```text
Activity:
Commit/source ref:
Gameplay and unique-value findings:
Age & difficulty metadata:
Media producer/consumer role:
Localization/voice:
User input/Chrome lifecycle:
Storage/import/export/corruption:
Performance (CPU/RSS/frame):
Visual screenshot evidence + resolutions:
Source/simulator/hardware tests:
Disposition (ANCHOR / KEEP / IMPROVE / MERGE/REPLACE / DO NOT SHIP):
Next required fix:
```

### State labels

`NOT STARTED` · `SOURCE WIP` · `SOURCE TESTED` · `SIMULATOR REVIEWED` · `PHYSICAL REVIEWED` · `RELEASE APPROVED` · `BLOCKED`

Do not equate `SOURCE TESTED` with `RELEASE APPROVED`.

## 8. Closure criteria and ownership

This program closes only after **all** these are true:

- universal viewer/picker genuinely works, with accessible image and **audio-before-select** previews, safe delete, no file-name dependency;
- media registry covers all three initial families and allows future explicitly supported codecs without changing every Activity;
- shared storage works across Activities without bypassing sandbox/profile security, and capacity policy adapts to real writable storage while protecting OS headroom;
- Painting↔Shape Garden↔Painting and Painting→Teatrino are real durable flows, voice/audio and text each have tested interchange;
- all 45 source Activities have documented review decisions; all *selected release Activities* pass appropriate real-script, UI, performance and metadata evidence;
- built release set is explicit rather than coincidentally equal to whole source tree;
- disabled/experimental Activities cannot leak into release index or bypass Parent policy;
- the previously open first-boot/install lifecycle route is separately accepted on actual target hardware;
- accepted stable product/API decisions are reflected in the proper `docs/product/`, ADR, agent manual and skills after implementation, without dual authority;
- final `PROGRESS.md` + HANDOVER explain exact outcomes, accepted roster and remaining post-release improvements.

**Current resume:** P1 trusted repository, P2 manifest/broker/SDK, P3 child Gallery, and P3's **nonblocking authenticated picker request/status/cancel source protocol** exist as WIP; Painting is a PNG publisher and has an internal independent selected-PNG receiver, but **no live in-Activity modal display mediation exists**. Requests fail closed until a real presenter is enabled. Follow the dedicated [P3 display contract](./P3_TRUSTED_PICKER_DISPLAY_CONTRACT.md) and current [PROGRESS.md](./PROGRESS.md); all previous tests are carried in the consolidated [deferred desktop/source acceptance](../../testing/2026-10-07_CREATIONS_P3_DESKTOP_SOURCE_AND_VISUAL_ACCEPTANCE.md). No complete checkout or GUI tests ran in this continuation; curated build, 45-Activity QA, backup, all-writers adaptive storage and physical acceptance remain open.
