# Greia — Current Engineering Handover

**Purpose:** the short current state for contributors and agents: active workstreams, recent results, blockers and next steps. It is not an archive.

## Current state

Updated 2026-10-30. Newest first inside each topic; the dated source entries are under **Recent entries**. Evidence labels follow `AGENTS.md`; nothing below is family-release certification.

**Release status**
- Public source readiness: IN PROGRESS. Root entry points exist (`LICENSE`, `NOTICE.md`, `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`); the licensing/provenance audit is open (see `NOTICE.md`). Ordinary-family release: **NOT READY** (`docs/release/GREIA_PUBLIC_RELEASE_READINESS.md`).
- Release checklist: `docs/release/FIRST_PUBLIC_RELEASE_EXECUTION.md`. Recommended first binary: one non-developer i386 A/B hardware-tested image, not a universal/Pi promise. Source publication can precede a public binary after public-tree/history rights and privacy review.
- **Blocker (media rights):** 627 committed recordings use the macOS System Voice (257 would remain even in the 32-activity draft roster); public source/binary distribution stays blocked until the owner decides (`docs/release/2026-10-28_MACOS_SYSTEM_VOICE_AUDIO_INVENTORY.md`). The owner has already placed a technical-preview installer on the website.
- **Blocker (release-safety):** the early framebuffer boot cover is not accepted as release-safe; physical Acer acceptance, browser-client upload click-through and the Activity-roster decision are open.
- Technical-preview installer `greia-os-installer-i386-ab-0.13.1-preview.1-build-9ba22f764ed1.img` (2,273,312,768 B, SHA-256 `e8d8bb8b9af2cbfcd4c149fe8e0e441e3bc956349e813edb54d126fd9afed2ef`, bundle `40649f9d615ba1be690f6591f8d1d4999120479cdb53cd6878a0274113cf9c65`) is the newest build; `release_eligible: false`. Last green gate on it: `make verify` 6,038 tests OK, 5 skipped. Legacy BIOS tested, UEFI experimental.
- **Website:** source is the private repo `frozenpepper/greia-website` (local checkout `../website/`, beside this one); the site, downloads page and installer index are live on the server. Installer index entries are built with `tools/build_installer_index.py --index ../website/updates/greia-updates.json`.

**Install and update lifecycle** (`docs/plans/2026-09-15_MULTIPLATFORM_RELEASE_INSTALL_UPDATE_COMPLETION.md`; rerun router `docs/testing/GREIA_UPDATE_RELEASE_ACCEPTANCE.md`)
- Installed Linux/QEMU acceptance **PASS** at `810caa91f` (2026-10-28): fresh A/B install, healthy B, failed-B rollback, interrupted-stage recovery; Python, Activity and combined `.greia_update` packages via the Parent HTTPS API; EN/IT/ES/FR, profiles, saves and settings survive; a broken package rolls back.
- No backwards compatibility for pre-release development images is required or implemented (owner decision 2026-10-27).
- **Open update gaps:** physical Acer/USB install and rollback; HTML/Mobile browser click-through; reverse B→A; the `full_system` `.greia_update` wrapper; HTTP 507 low-space. Session 04 physical/hardware closure remains OPEN.
- The owner reports a successful Italian install on the Acer, but Wi-Fi hardware, first-boot health on the newest image and rollback remain unexecuted on physical hardware.

**Acer installed system and Parent (physical, 192.168.2.x)**
- The Acer still runs the older installed candidate. It has the launcher sandbox regression (generation symlink mistaken for a development tree: no protected Activity Home chrome, no installed focus repair, no mandatory Bubblewrap). Do **not** treat it as release safe. Source fix is in; device retest pending. S+T not reacting on the profile picker is a plausible but unconfirmed consequence.
- Parent package API: a valid Parent-trusted package was uploaded, listed and removed on the Acer through the Parent API (PHYSICAL API PASS, source `a04ee90d5`). Not yet proven: browser upload, child-Shell launch of an uploaded Activity, Bubblewrap.
- The original Parent "service unavailable" report on the installed Acer was never root-caused; later evidence shows Parent HTTPS answering. The Parent client permissions/integrity fix (client `0755`) and active-profile group fix are the likely repairs, unconfirmed.
- **Next exact steps:** (1) install or update the newest image on disposable Linux with real Bubblewrap and X11; (2) verify the Parent SSH switch (login, off, reboot) and the child-facing launch path; (3) deliver an accepted update or reinstall to the Acer and verify S+T and Home there; (4) full-system image/update is needed for the Parent SSH unit, the active-profile fix and the pinned Parent client revision `080b4b67…` (Greia mark).
- The LaCie `/dev/sdc` (8 GB) holds the newest installer (full readback matched). The live installer has an off-by-default Wi-Fi-page **Installer SSH** toggle (`greia` / `greia`): boot the Acer from the USB without installing, switch it on, connect as `greia`; the real Acer connection is PENDING. Installer failures save to `GREIA_EFI/greia-logs/last-install-failure.log` on the USB (`docs/release/INSTALLER_FAILURE_LOGS_ON_USB.md`); the physical USB write is untested.
- Fixed in source and built into the newest image: the 216/GROUP live-installer boot failure, the hardware-support `initramfs` out-of-space failure (RAM scratch area; root transaction and system-update workers simplified), fresh A/B installs seeding language/hardware/Wi-Fi settings into PERSIST. Fixed items count as fixed only once the newest image passes physically.
- `make verify` aborted once (SIGABRT in SDL2_ttf/HarfBuzz allocation) in a later Mac run; `make validate shell-check footprint` passed separately. A full-suite-only launcher-memory failure that passes in isolation is documented. Treat the full gate as unconfirmed until rerun on the exact HEAD.

**Voice production** (local, external to the repo; state last recorded 2026-10-22)
- Committed recordings are owner-accepted. The 2026-10-21 v3 replacement (Dani, Momo, Tito selected masters) and the 667-path priority retake run produce **listening-pending** takes; generation DONE is not acceptance. Resume directory: `/Volumes/Test1/Works/Greia-voice-auditions/2026-10-21-short-carrier-priority-v1/resume-base-v6-production/` (`progress.json`, `production.log`). A one-cue follow-up restores the last exact-original priority path (whale cue) after the main pass; do not duplicate producers. Human review via `takeboard`.

**Languages** (`docs/development/ADD_A_GREIA_LANGUAGE.md`)
- Languages load from `src/greia_platform/languages/<locale>/manifest.json`; en/it/es/fr are released. Staging a fifth language never offers it.
- **Open:** the browser Parent chrome still has its own EN/IT/ES/FR catalog in `parent-app/src/localization.js`, to be extended and re-pinned (`tools/update_parent_client_pin.py`); no five-language chooser/rendering exercise has run (next: one bounded 4+1 simulator check).

**Hardware risks** (2026-10-21 reviews, moved off-tree): Debian trixie has no i386 kernel/installer, so the Greia i686 line is bookworm (supported to 2028-06-30), with owner decisions pending; on the Acer, animated Activities use about 45-52% CPU plus Xorg about 50%, not yet compared with hi-res off; the Wi-Fi resume hook reaches a device only after reimage.

## Active workstreams

Blocking and lifecycle authorities (rules in `docs/agents/CORE_TEAM.md`):

- **Architecture remediation**: `docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md` is the blocking plan for its remaining non-lifecycle obligations.
- **Install, update and release lifecycle**: `docs/plans/2026-09-15_MULTIPLATFORM_RELEASE_INSTALL_UPDATE_COMPLETION.md` (ADR 0036 successor).
- **Cross-hardware robustness**: `docs/plans/2026-09-28_CROSS_HARDWARE_ROBUSTNESS_PLAN.md`, subordinate to the remediation plan; root causes go to `docs/engineering/boot/INSTALLATION_ISSUES_LOG.md`.
- **Art and visual system**: `docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md`, resumed through `docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md`; Encyclopedia subplan `docs/plans/2026-08-28_ENCYCLOPEDIA_VISUAL_REAUTHORING.md`.
- **Parent authentication/runtime acceptance**: current HTTPS transport procedure is `docs/testing/2026-10-23_PARENT_HTTPS_ACCEPTANCE.md`; the older 2026-09-08 protocol is a historical authentication baseline. Self-signed HTTPS is implemented in source but awaits local tests and device/browser acceptance.
- **Testing route**: `docs/testing/LOCAL_AGENT_START_HERE.md`; local-agent queue `docs/testing/GREIA_LOCAL_AGENT_TASK_QUEUE.md`.

Scoped owner-authorized workstreams (moved verbatim from `AGENTS.md` on 2026-10-16; standing rules now in `AGENTS.md` § Standing owner decisions and `docs/agents/CORE_TEAM.md`):

**Current owner-authorized Activity release + Creations workstream:** `docs/plans/2026-10-07_CREATIONS_LIBRARY_AND_ACTIVITY_RELEASE/PLAN.md` is the **single unified product/content implementation plan** for the typed child Creations Library, universal pre-reader picker/viewer, adaptable disk budget, Painting/Shape Garden/Theatre/voice/text interoperability, complete built-in Activity quality audit, and deliberate catalogue selection. Continue from `docs/plans/2026-10-07_CREATIONS_LIBRARY_AND_ACTIVITY_RELEASE/PROGRESS.md` and append accurate session results. This owner-requested scoped program coordinates those features but **does not supersede** the architectural-remediation and release-install/first-boot lifecycle authorities above; those still govern safety prerequisites, image installation, update, rollback and hardware acceptance. Product/source work may proceed in parallel without making hardware claims. Do not spin up a second competing catalogue, picker, or creative-media plan.

**Owner-authorized localization workstream (2026-10-12):**
`docs/plans/2026-10-12_GREIA_FOUR_LANGUAGE_ROLLOUT/PLAN.md` is the
scoped implementation plan for reducing misleading language choices,
completing EN/IT gaps, and extending real installer/OS/Parent/Activity
text and voice support to ES/FR. Its standing local-agent speech design and cue-source authority is
`docs/plans/2026-10-12_GREIA_FOUR_LANGUAGE_ROLLOUT/LOCAL_AGENT_VOICE_PRODUCTION.md`.
**Current existing-corpus replacement work order (owner instruction 2026-10-19):**
`docs/agents/GREIA_VOICE_CORPUS_REGENERATION.md`, executed with
`tools/regenerate_voice_corpus.py`. It explicitly permits fresh replacement
with new masters and per-recording acting prompts, preserving deterministic
isolated letters/syllables and backups. V2 production has completed: 4,168 DONE,
741 PRESERVED, zero blocked or unresolved rows. Every new take remains
listening-pending. Source fixes needed to operate the tool and packaging are
authorized by this work order; ordinary queue-only restrictions do not block
that requested task. Post-generation screening follows
`docs/agents/GREIA_AUTOMATED_VOICE_REVIEW.md`; automatic coverage and human
acceptance are separate from generation DONE.
**Earlier add-only voice-production work order:** `docs/plans/2026-10-12_GREIA_FOUR_LANGUAGE_ROLLOUT/LOCAL_AGENT_ALL_APP_VOICE_RECORDING_ORDER.md`
(owner instruction 2026-10-14; archived full-run instruction). The owner approved
every **currently authored** EN/IT/ES/FR text translation, and personally
reviewed and approved **all committed recordings**. New missing files from
the targeted task still need fresh acceptance. Neither decision promotes ES/FR.
An available, registered zero-new-spend local Greia Voice Engine provider may
be used to record without waiting for a future Modal provider, but paid
cloud/model installation still needs separate explicit cost approval.
**Owner-directed shared localization consolidation (2026-10-15):**
`docs/plans/2026-10-12_GREIA_FOUR_LANGUAGE_ROLLOUT/SHARED_LOCALIZATION_AND_AUDIO_RESOLVER.md`
is the active bounded design for reusing the existing `LocalizedResources`
owner for semantic text/audio IDs, file-exists selected-locale lookup and
English fallback for **all** speech, and gradual migration of Activity-local
loaders. Existing committed audio is **owner-reviewed and accepted**;
never regenerate it for perceived provenance problems. The user does **not**
want file anti-tampering, signing or elaborate asset verification; users may
edit their files. Follow the focused new-recordings assignment in
`docs/testing/2026-10-15_GREIA_TARGETED_MISSING_VOICES_LOCAL_AGENT.md`.
Update the Activity-creation skill/voice companion **after the code API is real**;
retain the current callable interface meanwhile. This refactor does not
independently promote ES/FR system selection.
The sole practical local-agent task queue remains
`docs/testing/GREIA_LOCAL_AGENT_TASK_QUEUE.md`.
**Owner decision 2026-10-17:** EN, IT, ES and FR are all released and
selectable (selectors offer exactly these four); missing voice lines in all
four languages are owner-approved for recording with the local voice tooling
(no paid spend without approval).
This scope does not override ADR 0028, accepted architecture,
installer/first-boot/lifecycle test gates or the Creations/Activity
audit programme. Do not invent a second language registry or silently
promote unvoiced locales.

## Recent entries

Add new entries at the top, newest first, at most 8 lines each; fold older ones into **Current state** or drop them when superseded.

### 2026-10-30 — Parent web client merged into Greia (`parent-app/`) (SOURCE)
Owner decision: the browser Parent client is now developed in this repo at `parent-app/` (imported from `Greia-Parent-App-Html` 999cd69; that repo keeps its old evidence and is no longer the source). `vendor/parent-app/` and `tools/stage_parent_app.py` are gone. The image payload, pin/manifest format and on-device integrity check are unchanged; the pin now names `frozenpepper/Greia:parent-app` with the git tree id of the committed folder (`7e01bdb4…`, same runtime bytes as the old `080b4b67` pin plus Parent HEAD). Workflow: edit → `make parent-app-test` → commit → `python3 tools/update_parent_client_pin.py` → commit; `--check` and a drift test catch forgotten repins. Docs, ADR 0022 amendment, language guide and test procedures updated. Checks: 164 Parent Python tests, 106 Node tests, integrity OK, doc audit 0 unresolved. The old GitHub repo is archived (read-only, private) with a README pointing here.

### 2026-10-30 — Generic AGENTS.md for outside agents; core-team rules split out (DOCUMENTATION)
`AGENTS.md` is now the generic file every coding agent reads after cloning: orientation table, run/test, "Sharing what you found" (ask the owner, then a pull request or an email to greia@frozenpepper.it; what never to send), outside-contributor rules, pre-release policy, standing owner decisions, and the unchanged product contracts and engineering rules (contract numbering kept). Branch-on-`main` policy, authoritative read order, active plans, owner campaigns and continuity/progress duties moved verbatim to `docs/agents/CORE_TEAM.md`, which the owner's own agents **must** read. `CLAUDE.md` imports `AGENTS.md`. Added `.github/pull_request_template.md` and hardware/bug issue templates. Doc audit 0 unresolved links.

### 2026-10-30 — Greia group names; website and launch film leave the repo (SOURCE)
Owner decision: the image now creates `greiaprofiles`/`greiasettings` (was `pipprofiles`/`pipsettings`) in compose, tmpfiles, first boot, services, installer engine, system controls and verifiers; the installer payload is `greia-rootfs.squashfs` and other `pip-` build names became `greia-`. No migration (pre-release policy): the **next image build** uses the new names, existing installs need a fresh image, and a Python-only update onto an old image does not change groups. Guard: `tests/test_greia_group_names.py`. Related tests 699 PASS, `make validate shell-check footprint` PASS; no image built yet. `website/` (with its `.site-ftp`), `launch-video/` and `final.mp4` (restored from LFS, OID verified) were checksum-copied to the untracked folders `../website/` and `../launch-video/` beside the checkout and removed from git; run `site-ftp` and `tools/build_installer_index.py --index ../website/updates/greia-updates.json` against the new folder.

### 2026-10-30 — Public-repository documentation cleanup (DOCUMENTATION)
Owner-requested pre-publication cleanup. 197 dated reviews, test results, evidence captures, session handoffs, `docs/archive/`, the retired `skills/greia-activity-authoring/CORE.md` and one work-order-only test (`tests/test_x8_qemu/test_diagnostic_handoff.py`) left the tree; each file was checksum-copied first to the owner's archive volume (`Greia_Archive/2026-10-30_public-repo-cleanup/`, `MANIFEST.tsv`) and stays in git history. Boot postmortems/issue log/runbook moved to `docs/engineering/boot/`. New non-technical root `README.md`, docs map `docs/README.md`, agent index `docs/agents/README.md`, rewritten `docs/user/*`; all five skills de-staled; HANDOVER trimmed (full pre-trim copy on the archive volume). Dated testing procedures still named as current were kept. Checks: doc audit 0 unresolved links (all scope), `make validate shell-check footprint` PASS, edited Python compiles, related test files 943 PASS; full `make verify` not run (docs/comments-only change). Open: `pipprofiles`/`pipsettings` group names in build/first-boot vs `greiaprofiles`/`greiasettings` in `AGENTS.md`; git history still holds every removed report (decide before publishing).

### 2026-10-30 — Website download page and contact (DESKTOP VISUAL REVIEW)
`website/downloads.html` with `release-index.js` reads `greia_os.installers` in `updates/greia-updates.json` (version, size, date, checksum), labels the image a technical preview and shows real offscreen installer renders; the homepage gained a Download hero button, download band, contact band and a "Free for every child" support section (donations welcome, never required; sponsors, schools, custom Activities/editions; commercial licensing per `TRADEMARK.md`). Contact: greia@frozenpepper.it. Parent/device update readers ignore the installers list. Tests: 20 index, 15 Parent update-delivery, doc audit 0 unresolved; desktop and phone layouts reviewed locally. Donations use the owner's PayPal hosted button, loaded only on click (PRIVACY.md amended); `.github/FUNDING.yml` points GitHub's Sponsor button at `#support`. Next: owner-approved `site-ftp` upload.

### 2026-10-30 — Acer Parent Activity upload (PHYSICAL API PASS)
Python package `greia-parent-activities-20261030` applied on the Acer; the first upload returned 409 at the picker because the Shell-created `/run/greia-os/active-profile.json` kept the Shell primary group, so Parent read it as "no active child". `ActiveProfileSession` now assigns the shared group before atomic publication and the API distinguishes unavailable state. Follow-up package `greia-parent-session-20261030` (source `a04ee90d5`): temporary package uploaded (201), listed in `GET /activities`, removed (200). Not proven: browser upload, child launch, full image, SSH, logo delivery. A broad local `make verify` aborted with SIGABRT (SDL2_ttf/HarfBuzz); `make validate shell-check footprint` passed. Next: child-facing launch path.

### 2026-10-30 — Parent Activity upload (SOURCE + LOCAL HTTP)
The API advertises install/remove when its package store is writable (explicit off override). The shared profile session lock requires an idle picker during package mutation; the Shell refreshes its Parent source when the atomic active pointer changes. Local production-HTTP tests reject a bad package and an active child, install a real package, discover it and reject duplicates. Focused suites: Parent API 33, production Parent 8, package 16 (+1 Linux skip), removal 5, launcher composition 18, end-to-end 2, Parent Node 106. The owner forbids VM/image builds on this Mac.

### 2026-10-30 — Parent SSH switch and branding (NEW INSTALLER; USB FLASHED)
Parent switch for SSH on normal images (`greia` / `greia`, off by default) via a socket-activated fixed-operation service (`greia-parent-ssh.service/.socket`); the Parent API advertises it only when the socket exists. The Parent client uses Greia's mark and shows the login. Source checks: SSH control 8, production Parent 8, Parent API 34, socket composition 5, client pin 3, Parent Node 106. Bundle `40649f9d…` and installer `e8d8bb8b…` built from `9ba22f764`; `make verify` GREEN (6,038 OK, 5 skipped); LaCie reflashed with full readback. Linux systemd SSH switch/login/disable/reboot and physical installed acceptance have not run.

### 2026-10-30 — Acer Shell installed-generation regression (SOURCE FIX)
Owner report: Italian install succeeded, S+T does nothing at the picker, no Activity shows Home. Cause: `/opt/greia-os` is a generation symlink and launcher path resolution compared its target to the unresolved link, choosing development composition (no protected chrome, focus repair, display coordinator or mandatory Bubblewrap). Shared installed-root detection now handles the link across Shell, bootstrap, supervisor, interpreter and broker; tests use a real symlink. Bundle `a564ed0b…` / installer `018ae1d2…` (from `89aa68891`) were superseded by `e8d8bb8b…`. No Linux sandbox, live X11 or physical retest yet.

### 2026-10-29 — Live-installer SSH toggle (USB PATCHED; Acer connection PENDING)
Owner-requested default-off **Installer SSH** toggle on the live installer's Wi-Fi page (live OpenSSH/sudo/Avahi, localized copy, keyboard/pointer support); installed Greia unchanged; root SSH stays disabled. QEMU boot of a byte copy: on -> real `greia`/`greia` login and sudo; off -> connection reset; on -> restored. Real Acer connection PENDING.

### 2026-10-29 — Installer preferences and Parent access (SOURCE)
Owner saw an English Shell after choosing Italian, and the on-device Parent password check reported unavailable. The A/B executor had dropped language/hardware settings and Wi-Fi carry-over; fresh A/B installs now seed device-settings and network-state PERSIST namespaces, with first boot handing settings files to the Parent identity (Wi-Fi best effort). An integration test carries Italian, keyboard, Wi-Fi, pointer/display/microphone choices through the A/B transaction to the settings reader. 214 + 173 focused tests passed. The Parent outage was not diagnosed.

### 2026-10-29 — Installer failure logs on USB, hardware-support `initramfs` failure, 216/GROUP
Physical Acer install failures, in order: live root lacked `netdev` (`status=216/GROUP`), fixed by provisioning every unit group and verifying the composed root; the hardware-support `dpkg` step then failed because `initramfs-tools` ran out of space in the 1,664 MiB SYSTEM_A slot (apt cache + `mkinitramfs` tree), fixed with a bounded 256 MiB RAM scratch (only the 42 MiB initrd is written); the one-time root transaction and system-update workers lost their over-tight systemd hardening (socket, authorization and disk-identity checks unchanged). New images retain failed command stdout/stderr and save `greia-logs/last-install-failure.log` on the installer USB. Image `7869b6b5…` booted in QEMU; local gate GREEN (6,012 tests, 5 skipped).

### 2026-10-28 — Public-release preparation: green gate and boot presentation
`make verify` GREEN (6,013 tests, 5 skipped) at `8bac176bd`; the 7 failures / 3 errors were fixed at their causes. The A/B boot menu loads the Greia GRUB theme/logo, the initramfs carries generic QEMU framebuffer drivers, `quiet` precedes `loglevel=0`, the Parent API accepts `Expect: 100-continue`, and the login screen no longer prints the default password. Technical-preview candidate then: installer `b81279af…`, bundle `2572bf08…`, version `0.13.1-preview.1` (fresh A/B install and first-boot health PASS in QEMU; superseded by `e8d8bb8b…`). Selected MPL-2.0 license for the separate Parents repo with a pending-provenance notice.

### 2026-10-28 — Installed A/B and application update acceptance PASS
Source `810caa91f` on the disposable i386 QEMU fixture. Fixes: architecture-correct `BLKGETSIZE64` plus sysfs/`blockdev` capacity fallback; finalizer `link_file` publishes `vmlinuz-greia`/`initramfs-greia.img`; staged filesystems checked before role-UUID binding; `greia-candidate-recovery.timer` enabled; stable bootstrap resolves an A/B root from the layout record and `root=PARTUUID=`; one job lock for terminal publication and cleanup. Results as in **Current state**. 353 focused tests passed; `make verify` was 6,009 tests, 7 failures, 3 errors, 3 skips (known Linux baseline, since repaired).

## History

Older entries live in git history (`git log -p -- HANDOVER.md`); the full pre-trim copy is on the owner's archive volume (`/Volumes/Venus/Greia_Archive/2026-10-30_public-repo-cleanup/repo/HANDOVER.full-2026-10-30.md`).
Entries before 2026-10-15 were removed in the 2026-10-16 open-source cleanup (`git show 101e332a:HANDOVER.md`).
