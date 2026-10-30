# Greia Agent Operations Manual

**Audience:** coding, review and test agents working on Greia OS  
**Status:** LIVING mandatory derived operating manual  
**Reviewed:** 2026-09-02  
**Canonical repository/branch:** `frozenpepper/Greia` / `main`

This is an operating router, not an architecture or evidence archive. Exact current state belongs in `HANDOVER.md`; exact procedures belong in `docs/testing/*`; accepted architecture belongs in ADRs; exact implemented contracts belong in source/runtime declarations.

---

## Manifest-based language tasks (2026-10-26)

When asked to add a language, read `skills/greia-language-expansion/SKILL.md`
and `docs/development/ADD_A_GREIA_LANGUAGE.md`. Add candidate translated
`ui.json` and Activity locale JSON through the non-overwriting scaffold.
Only placing `src/greia_platform/languages/<locale>/manifest.json` makes the
language selectable on installer/Shell/Parent startup. Never insert languages
into Python tuples or claim real-device/voice acceptance from source tests.
The current four shipped manifests are unchanged; a new manifest requires
author-reviewed text, audio, fonts and runtime/layout acceptance.

## 1. Mandatory start

Before substantive work:

1. read `AGENTS.md`;
2. read `README.md` and `docs/DOCUMENTATION.md`;
3. read the active blocking plan;
4. read `HANDOVER.md`;
5. read `skills/greia-os-work/SKILL.md` for OS/platform work or the applicable narrower skill;
6. read the task-specific ADR/product/source owners named by those routers;
7. resolve the actual current `main` HEAD before writing;
8. classify the evidence lane the task can genuinely exercise.

Repository `skills/` owns current guidance. If the local skill catalog points to ignored `.agents/skills/` copies, refresh the affected directories from `skills/` after a skill update; these installed copies do not own separate policy.

Before installing/configuring any Greia toolchain, image builder, Simulator dependency, Parent client, voice backend or developer-remote environment, read `SETUP.md`.

Current test/evidence routing starts at:

```text
docs/testing/LOCAL_AGENT_START_HERE.md
```

The **single owner-authorized delayed local-agent queue** is
`docs/testing/GREIA_LOCAL_AGENT_TASK_QUEUE.md`; it lists exact
commands/SHAs/status/evidence tasks and safe queue-only update rules.
The owner authorizes *queue-file-only* status/evidence commits to `main`.
That is NOT permission for source edits, direct release approval, real
user-profile access or Acer/installer operations.

That router follows `HANDOVER.md`. Do not select a dated procedure merely because its filename looks newer or familiar.

**Human listening follow-up (2026-10-21):** shared `takeboard` serves a local HTML
review desk. Greia exports its completed automated batch through
`tools/export_voice_review_batch.py`; see automated review procedure §6 for exact
commands and save/export behavior. It never modifies canonical audio, receipts
or acceptance automatically.

**Owner review/direction correction (2026-10-21):** policy v2 uses ASR >0.8
and tail/internal silence warnings at ≥1.5s. `reassess` can reuse matching saved
evidence with no ASR call; see automated procedure §3a. Voice identity traits
belong in masters; defaults are now neutral performance only. Old frozen v2
PERSONA-prefixed overrides are historical, not the next recording instructions.
New policy results/owner-draft copy are served on 8796, auditions on 8795;
original 8794 tab with unsaved owner edits was kept intact.

**Automated review follow-up (2026-10-21):** after generation, execute
`docs/agents/GREIA_AUTOMATED_VOICE_REVIEW.md` with the `review` command on
`tools/regenerate_voice_corpus.py`. It writes external read-only screening reports
and a prioritized listening queue, never approvals or replacement audio. Missing
or disabled ASR remains incomplete; no model downloads are performed. Report
generation, automated screening and human acceptance separately.

**Corpus replacement follow-up (2026-10-19):** the owner authorized the existing
Activity/system corpus regeneration, except deterministic isolated letters and
syllables, with per-recording tone/mood prompts. Its executable work order is
`docs/agents/GREIA_VOICE_CORPUS_REGENERATION.md` and tool is
`tools/regenerate_voice_corpus.py`. This scope authorizes source bug fixes and
replacement with recoverable originals; new output stays listening-pending.
It supersedes earlier add-only/preservation instructions for this operation,
without changing the no-paid-spend or child-runtime boundaries.

**2026-10-12 language/voice authoring route:** for the owner-authorized
four-language rollout, read
`docs/plans/2026-10-12_GREIA_FOUR_LANGUAGE_ROLLOUT/PLAN.md`
and its sibling `LOCAL_AGENT_VOICE_PRODUCTION.md`, then operate
the exact GLA-014 task in the single queue. The visible OS/installer language registry contains EN/IT/ES/FR by owner decision 2026-10-17. As of 2026-10-21, Voice Studio/VoiceEngine defaults to the shared local VoxStage/VoxCPM2 worker with the v0.3 registry: Dani/Momo/Tito use their new selected v3 master IDs and Lilli/Leo/Flash retain their exact v2 IDs and bytes. Chatterbox remains an explicit operator alternative; pedagogical pronunciation retains native/system routing. Read the voice-production skill and `SETUP.md` §7 for startup, timeout/job recovery and shared-model unloading. No Modal adapter exists; do not launch a cloud workload or download models based on an older plan. Registry selection alone does not replace accepted runtime recordings; the separately authorized corpus/priority replacements remain listening-pending.
Inventoried absent WAVs and missing translations are real
`BLOCKED` content. Never substitute placeholder or wrong-language
speech, treat ASR PASS as human listening, or claim a voice
catalogue passes if `my_creations.wav` is absent. The local
agent may update evidence/task status only under the queue's
explicit procedure.

---

## System-update implementation and Linux acceptance (2026-10-27)

**Current owner-authorized execution:** [single update release acceptance](../testing/GREIA_UPDATE_RELEASE_ACCEPTANCE.md). The local coding agent may fix code, add tests, build current-source disposable Linux/QEMU images, test full A/B and application updates, diagnose failures and commit coherent repairs in **one session**. Do not apply the testing-only source-edit restrictions from the unrelated delayed Activity queue to this owner-authorized work.

Dated October 23–27 procedures are detailed **reference material**, not independent mandatory gates. Do **not** use the frozen 1275 guest, duplicate source-difference allowlists, one-stage-only stop orders or fixed old artifact hashes as current instructions. The prior diagnostic already identified a real failure: i386 guest updater stage refused because `sda2` capacity was unobservable. See [captured result](../reviews/2026-10-27_AB_OLD_RELEASE_STAGE_DIAGNOSTIC_RESULT.md) and [root-cause analysis](../reviews/2026-10-27_AB_OLD_RELEASE_STAGE_REFUSAL_ANALYSIS.md).

Use the Linux host's disposable QEMU disks; never guess a physical target. Keep the real product invariants: layout/device identity, bounded writes, PERSIST preservation, application generation atomicity, child-session fence, health and rollback. Run focused tests while fixing, full verification once after coherent changes, and consolidated installed acceptance. Record unrelated pre-existing full-suite failures without blocking relevant disposable-device tests; never misstate evidence.

The two independent lanes are (1) current-source blank-disk A/B install -> first A -> stage B -> activate -> healthy B -> rollback/interrupt recovery and (2) current application `.greia_update` Python/Activity/combined -> applied/health -> bad-candidate rollback and Parent disconnect continuation. There are no pre-release upgrade targets: do not build, stage or test old-receiver bridges or historical image migrations. Normal language manifest/UI JSON packaging is implemented, but Linux installed acceptance remains pending. Session 04 remains OPEN until measured.

### Linux acceptance follow-up (2026-10-24)

The first Linux result is recorded in
`docs/reviews/2026-10-24_SOFTWARE_UPDATE_LINUX_ACCEPTANCE_RESULT.md`; preserve its
manual-repair evidence boundary. Rebuild/reinstall the committed fixes before
claiming clean acceptance. Run the root-to-Parent ownership regression on the
installed disposable image with its real `greiakid`/`greiapanel` accounts, then
seed a Parent Activity, perform a root-side package update, and verify ordinary
Parent install/uninstall still work. The Parent package store remains Parent-
owned; its published generation paths are readable by the child, never writable.

The work orders now use `greia_release.py build-acceptance-fixture` for the
otherwise release-gated Acer A/B test legs. This explicit command reuses the
same payload/bundle/layout checks with development composition and emits
`greia-acceptance-fixture-*`, marked non-release-eligible. The index tool refuses
these reports. Normal `build`/`build-profile` retain the boot-cover release gate.
Keep release acceptance and experimental VM evidence separate.

Use existing `tools/greia_release.py` and `tools/build_update_index.py` for
release/index assembly. The index supports EN/IT/ES/FR notes, retains three
releases per exact target by default and publishes its local file atomically.
Upload artifacts before replacing the public index. The existing shared
`site-ftp` tool owns server publication; no new deployment script or hosted
Actions service is required. Read its publication instructions when publishing.

The existing full-system route uses `tools/greia_release.py`,
`tools/greia_update.py`, and the static index to build/check unsigned v3
bundles. It still requires the A/B writer, explicit restart at the profile
picker and actual boot-health evidence. Do not bypass the profile-session
fence or infer boot acceptance from a successful upload/stage reply.

ADR 0038 adds `tools/greia_software_update.py` for source-built typed
`.greia_update` packages. Its Python type is a complete production source
snapshot, fixed runtime-config allowlist and offered locale `manifest.json` /
`ui.json` pairs; Activity packages reuse existing
`.greiaactivity` validation and preserve built-in vs Parent trust. Application
packages use one durable upload acknowledgement and continue on the device
after the phone closes. A full-system wrapper retains the existing v3/A-B
route. Read `docs/development/GREIA_SOFTWARE_UPDATE_PACKAGES.md` before
building or sending one. An image must contain
`/etc/greia-os/software-update-bootstrap.json` and the stable
`/usr/local/lib/greia-os/software-update-bootstrap.py`; no manual bootstrap
CLI exists. Builder/source tests are not installed Linux acceptance.

There is no supported backward-compatibility route from older development
images. For release acceptance, fresh-install a current image containing the
current receiver, then apply a normal current Python/Activity/combined package.
The earlier `build-receiver-bridge` CLI and its source/test module have been
removed as obsolete. Application rollback remains required.

Fresh BIOS A/B installation now has a mandatory `FreshAbInstallSeams.bios_bootloader_installer`
seam, supplied in production by `device_seams.build_bios_bootloader_installer`.
It installs BIOS GRUB onto the verified shared boot-control filesystem after
the default-A `grubenv` and `grub.cfg` are written, and rechecks target identity
before the disk write. Extend this owner and its existing
`efi_boot.bios_grub_install_command`; do not add a second installer command
path. Current fake-runner/source checks are not boot proof. The Linux work
order requires a fresh blank-disk BIOS install and a boot of the installed
target through BIOS GRUB into Greia before A/B update acceptance.

## 2. Repository and concurrent-work discipline

Repository-wide branch policy is owned by `AGENTS.md`:

- work directly on `main` by default;
- do not create a feature/review/safety/temporary branch unless the owner explicitly asks;
- refresh current `main` before substantive writes;
- preserve concurrent owner/agent work;
- never resolve divergence by resetting, deleting, stashing or cleaning unknown work;
- commit coherent work to canonical GitHub;
- keep generated images, caches, private keys and bulky evidence outside Git unless an authority explicitly requires them.

GitHub is persistent source truth. Chat summaries are navigation hints only.

For any retained test attempt record the exact source SHA. “Latest” and branch names are not evidence identities.

---

## 3. Hosted execution is opt-in only

Without explicit owner authorization for that specific use, do **not** use GitHub Actions as execution/evidence infrastructure.

Do not:

- trigger or rerun workflows;
- dispatch manual workflows;
- add automatic hosted triggers merely to run tests;
- query hosted runs/jobs/logs/artifacts as project evidence;
- download hosted artifacts.

Reading/editing workflow source as ordinary repository source is allowed when the task genuinely concerns it.

A request to “move forward”, “test” or “verify” is not hosted-compute authorization.

---

## 4. Evidence vocabulary

Keep these lanes separate:

```text
SOURCE
AUTHORING PROVIDER + HUMAN REVIEW
SIMULATOR
VM / IMAGE
PHYSICAL DEVICE
```

### SOURCE

Examples:

```text
unit/contract tests
make verify
project/Activity validation
static ownership audits
shell syntax
source footprint
```

Source evidence proves only the tested source contracts.

### AUTHORING PROVIDER + HUMAN REVIEW

Generated voice/art receipts, model success or machine verification prove production provenance/process only. Where Greia requires human listening/visual acceptance, provider success does not substitute for it.

### SIMULATOR

The Activity Simulator exercises substantial real Greia launcher/runtime/profile/storage/lifecycle semantics with synthetic device facts. It does **not** prove production display/session/input authority, Bubblewrap/kernel containment, physical hardware, Acer performance or boot/install behavior.

### VM / IMAGE

Image build/QEMU evidence proves the exact image/VM path exercised. It does not certify Acer/Pi physical behavior unless the named acceptance protocol explicitly says so.

### PHYSICAL DEVICE

Physical claims must name the tested machine/class, exact source/image identity and relevant hardware/runtime facts.

A PASS at SHA A does not certify runtime-affecting source at SHA B.

---

## 5. Current blocking boundary: post-R1 product-composition closure

The blocking work is exact shipped installer/update/boot-health product
composition (T3-P OPEN/BLOCKING; next task `POSTR1-P1-INSTALLER-RED`) until
`HANDOVER.md` and the active plan say otherwise. T3 source primitives
(T3-S) are done; T7 remains valid only in its disposable/device-harness
scope and is not shipped service/unit proof.

Do not start Raspberry Pi 400/500 work, UEFI work, or destructive Acer
installation in this lane, and do not treat shipped product composition
as complete.

Do not deepen provisional X11 coupling merely because the installed compatibility path currently uses Xorg/xinit.

Preserve:

- platform-owned Home/Back;
- `DisplaySessionCoordinator` display-session authority;
- `SystemChromeCoordinator` navigation authority;
- `TrustedChromeActivitySupervisor` lifecycle binding;
- runtime-neutral physical input semantics;
- direct safe SDL/Pygame Activity rendering/input hot paths;
- no ordinary Activity raw `/dev/input` or `/dev/dri` authority;
- no avoidable full-frame IPC/copy architecture;
- no Simulator-to-production evidence promotion.

For current R7 work, read the exact procedure named by `HANDOVER.md`. Historical R7/Linux procedures remain useful context only where the current router names them.

Do **not** advance a later R7 subphase while the active plan/handover says an earlier physical authority gate remains blocking.

---

## 6. Simulator work

Before Simulator implementation/testing read:

```text
docs/adr/0029-real-runtime-activity-simulator.md
docs/development/GREIA_ACTIVITY_SIMULATOR.md
HANDOVER.md
```

Rules:

- Simulator uses real Greia semantic/runtime services where defined by ADR 0029;
- do not create a second platform implementation inside Simulator code;
- do not make Activities branch on Simulator identity;
- synthetic device facts must remain visibly synthetic;
- protected remote/headless Home must use platform system-chrome/lifecycle authority, not Activity cooperation;
- screenshots that matter must actually be inspected or marked `NOT_REVIEWED`.

A Simulator PASS never closes production trusted-chrome, production graphics/input, Acer or Pi evidence.

---

## 7. Developer remote-control boundary

Remote control exists only for explicit developer/test images.

Canonical operator client:

```text
tools/greia_remote.py
```

Canonical detailed procedure:

```text
docs/testing/2026-08-09_DEVELOPER_REMOTE_CONTROL.md
```

Normal/release Greia must not expose developer SSH/remote-control merely because this tooling exists in source.

Use the stable Greia operator surface rather than scripting private X11/systemd/filesystem details when a supported command exists. Typical operations include:

```bash
python3 tools/greia_remote.py wait --timeout 180
python3 tools/greia_remote.py status
python3 tools/greia_remote.py screenshot out/screen.png
python3 tools/greia_remote.py key Return
python3 tools/greia_remote.py mousemove 500 300
python3 tools/greia_remote.py click
python3 tools/greia_remote.py type "test"
python3 tools/greia_remote.py logs --service launcher --lines 500
python3 tools/greia_remote.py restart
python3 tools/greia_remote.py reboot
```

Developer credentials, private keys and Wi-Fi secrets are operator material. Never commit them or include them in shareable evidence.

Do not disable host-key verification to make a reimaged machine convenient. Reconcile a changed host key only after confirming intentional reimage/replacement.

---

## 8. Acer and physical acceptance

The first-generation Acer Aspire One remains the extreme low-resource reference until inventory evidence replaces the current floor assumptions. Raspberry Pi 400/500 remain co-equal ARM references for their assigned phases.

For a physical gate:

1. use the exact procedure named by `HANDOVER.md`;
2. freeze the source candidate before deployment;
3. record `HEAD`, `origin/main`, worktree state and evidence root;
4. do not pull during a frozen run;
5. use canonical deployment/remote tooling without local timeout/source patches;
6. preserve the first genuine failure;
7. do not add later successful cycles to replace a failed numbered cycle;
8. do not convert remote coordinate injection into “physical input” evidence;
9. do not use a scripted click as evidence for sustained high-rate Painting input;
10. do not claim current physical acceptance when the exact tested source differs materially.

If the target is unreachable, return the completed source/Simulator evidence and classify the physical lane `INCOMPLETE`. Do not invent a substitute.

### Developer Acer: in-place source deploy (no installer)

Use this to test a frozen `HEAD` on an already-installed developer Acer without reimaging. It needs operator key authentication and the bounded developer privilege path; never touch `sshd`, sudoers or `authorized_keys`, and keep addresses and credentials out of commands you record. Images built from 2026-10-17 on accept an operator **public** key at build time (`--operator-key key.pub` on `tools/build-and-flash-development-usb.sh` / `tools/build-development-installer.sh`, installed root-owned at `/etc/ssh/greia-operator-keys/greia`; key OR password login, regenerated on every sshd start so it survives reboots) and expose the deploy as `sudo -n /usr/local/sbin/greia-devctl source-deploy probe|prepare|extract|parse-gate|swap|status|cleanup` (the only passwordless sudo entry). Images older than that (the Acer installed 2026-10-06) need `--legacy-generic-sudo`, which uses the hand-provisioned generic `sudo -n` and the old `/bin/sh -c` scripts. The older `tools/deploy_to_acer.py` is a password-based extract-in-place script that leaves `/opt/greia-os` owned by `greiakid`; it does not follow this procedure and must not be used for it.

**Device facts.** Atom N270, i686, 1 GB RAM, no swap, Python 3.11, Xorg 1024x600. There is no `rsync`, and `/var/tmp` is a 32 MB tmpfs, so stage under `/var/lib/greia/deploy`.

**Use the tool.** `python3 tools/dev_source_deploy.py deploy --target <operator>@<device>` (or set `GREIA_DEV_TARGET`; nothing is hard-coded, and it uses `ssh` with `BatchMode=yes`, so your own key/agent and `known_hosts` only, never a password). Subcommands: `stage` (build the bundle locally), `push` (stage + upload + parse-gate), `swap`, `deploy` (= push + swap), `status` (is-active, `NRestarts`, deployed SHA), `cleanup` (remove `prev`/`new`/tarballs on the device, only after verification). Every privileged step is one fixed `greia-devctl source-deploy` verb (or, with `--legacy-generic-sudo`, `sudo -n /bin/sh -c <fixed script>`); if the probe fails the tool stops with a clear message. Tests: `tests/test_dev_source_deploy.py`.

What it does (the former manual procedure, kept as the contract):

1. `stage`: builds the bundle from `git archive HEAD` (never the dirty worktree; uncommitted changes are not deployed), filtered like the image composer (`build/lib/compose.sh` `compose_install_target_content` / `compose_install_runtime_assets`): `src`, `runtime`, `activities`, and the runtime asset subset only (`assets/audio boot catalog/*.toml fonts icons scenes visual/runtime`), no `__pycache__`, no `assets/source`. It regenerates the built-in index with `tools/build_activity_index.py`, writes `/opt/greia-os/.deployed-sha` (quote it in every evidence note) and packs a tarball through Python `tarfile` that drops `._*`/`.DS_Store` and owner/xattr metadata (AppleDouble files otherwise break Activity validation or the extract).
2. `push`: streams the bundle over ssh into `/var/lib/greia/deploy/new` (`/var/tmp` is a 32 MB tmpfs) and **parse-gates** it: every `.py` compiled with the device's own Python 3.11 (`python3 -I -B`, in memory). It stops on the first failure; the live tree is untouched so far.
3. `swap`: stops `greia-launcher` and `greia-parent`, keeps exactly one backup in `/var/lib/greia/deploy/prev`, swaps the staged tree into `/opt/greia-os` and the index into `/usr/share/greia/activity-index-v1.json` (root-owned, `chmod -R a-w` as the composer does), installs changed `greia-launcher`/`greia-parent` units from `build/overlay/etc/systemd/system/` and runs `daemon-reload`, rebuilds the read-only bytecode prefix on the device with `tools/precompile_greia_bytecode.py` (checked-hash bytecode that no longer matches is ignored, so skipping it is safe but makes launch timings meaningless), starts both services and prints health.
4. Verify (see "active is not health" below: `NRestarts`, the Shell on screen, the deployed file contains the change), fix forward from the journal if needed, then run `cleanup`.

**Observation.**

- Screenshots: the `greia_remote.py screenshot` path needs `/etc/greia-os/developer-display.json`, which in-place deploys do not guarantee. Fall back to `PIL.ImageGrab` run as `greiakid` with `DISPLAY=:0`.
- Input: `xdotool` run as `greiakid` on `DISPLAY=:0`. It is remote coordinate injection, never physical-input evidence (rule 8 above).
- Launcher warnings and uncaught tracebacks now reach the journal as `greia-launcher: ...` entries (`greia_launcher.main.configure_launcher_logging`); you no longer need the `session.err` redirect for Shell crashes.
- Measurement method (launch to READY from `sessions.ready_at`, 1 Hz `/proc` CPU/RSS sampler, idle/interaction windows, STANDALONE DIAGNOSTIC labelling, play-limit and parent-policy constraints): `docs/reviews/acer/2026-10-16_ACER_ACTIVITY_SWEEP.md`. Its re-sweep section lists what a deploy of a given SHA changed and what was not verified on device.
- `/opt/greia-os/.deployed-sha` (written by `tools/dev_source_deploy.py stage`) is the convention the sweep reviews rely on; quote it in every evidence note.

---

## 9. Failure-preservation rules

When a gate fails:

- stop at the first failure when the named procedure says to stop;
- retain exact command, exit code, relevant stdout/stderr/logs/screenshots and source SHA;
- distinguish product failure from evidence/tooling failure;
- do not lengthen timeouts as the first response to a semantic/lifecycle failure;
- do not patch the hostile fixture into cooperation;
- do not weaken a security/authority/performance invariant to make the gate green;
- do not silently rerun until a transient-looking failure disappears;
- do not modify source inside a frozen physical acceptance and then continue calling the evidence same-candidate.

A clean `INCOMPLETE` is better evidence than a manufactured PASS.

---

## 9A. Parent HTTPS source/device testing (2026-10-23)

Use `docs/testing/2026-10-23_PARENT_HTTPS_ACCEPTANCE.md` for the latest transport change. Installed Greia serves self-signed HTTPS on LAN 8766 and HTTP only on 127.0.0.1:8767 for the built-in Parent panel. OpenSSL is packaged in the installed base. Do not change Parent password/paired devices on a family device, install certificates on host machines, or deploy/reboot the Acer without owner authorization. The Parent HTML source and exact Greia pin must agree; browser, image and physical acceptance are distinct from unit tests. **Do not use `tools/dev_source_deploy.py` alone for this HTTPS tranche:** its present archive excludes `/usr/share/greia-parent-app`, so upgrading only source/runtime/manifest against an older installed web client fails `greia-parent.service` `ExecStartPre` integrity validation. Physical tests require an exact-head composed image or an independently accepted full web-runtime deployment; never bypass integrity by copying files manually.

## 10. Local-agent instruction standard

When delegating local/hardware testing, instructions must include:

```text
prerequisites
exact repository/branch/source freeze
exact commands
expected outputs
hard stop conditions
prohibited actions
evidence directory
what evidence to return
what to do if a command fails
final report schema/verdict vocabulary
```

Additional defaults:

- no GitHub Actions unless explicitly authorized;
- no ZIP unless requested;
- no filesystem-root `/tmp`; use project-local `./tmp/...`;
- preserve owner work;
- no destructive reset/stash/clean;
- hard stops should protect source integrity, safety or evidence validity—not create unnecessary ceremony.

---

### Shared renditions and the hi-res layer (2026-10-21)

Regenerate shared renditions including the `@2x` siblings with `python3 tools/build_visual_renditions.py --rasterizer /opt/local/bin/rsvg-convert` (`--no-hires` skips `@2x`), then `make visual-assets-check`. To diagnose the transparent high-resolution layer, run the Activity with `GREIA_ACTIVITY_HIRES=0`.

## 11. Activity work

For Activity implementation/testing, route through:

```text
skills/greia-activity-authoring/SKILL.md
```

OS/platform agents should not duplicate Activity authoring rules here.

Key platform boundaries still apply:

- Activities do not own real system Home/Back;
- Activities remain backend-neutral;
- Activities do not gain raw device authority to simplify input;
- package/storage/progression/permission contracts remain platform-owned;
- low-resource performance is a correctness requirement.

---

## 12. Build / installer / boot work

Before image/build/installer changes read:

```text
SETUP.md
skills/greia-os-work/BOOT.md
docs/engineering/BOOT_PIPELINE_AGENT_GUIDE.md
```

Then read the task-specific ADR/product documents named by `skills/greia-os-work/SKILL.md`.

Do not perform destructive physical installation from memory. The exact named procedure must permit it and revalidate target identity before destructive work.

For the reference Acer, do not substitute the generic raw GRUB/MBR installer for the named Syslinux/FAT32 physical procedure. Accepted Acer boot evidence in `docs/INSTALLATION_USB_BOOT_POSTMORTEM.md` establishes active FAT32 + Syslinux as the proven removable-media first stage; the GRUB/MBR USB route is unproven/negative on that device. When a task is a reference-Acer physical boot test, read that postmortem before choosing the media path.

Developer-image convenience must not leak into normal/release profiles.

### Physical Acer installer GROUP failure (2026-10-29)

The 2026-10-28 LaCie candidate's physical GRUB diagnostic log showed
`greia-installer.service` `status=216/GROUP` before `ExecStartPre`.
The live installer unit requests `video input tty netdev audio`, but
`compose_create_users_groups` creates `netdev` only in the target role.
`compose_create_live_installer_groups` now provisions each live service
supplementary group after installing the live package set. `passwd` supplies
`groupadd`. The live composed-root verifier checks the actual `/etc/group`
for **every** declared group; test `tests/test_live_installer_groups.py`
guards this failure. See
[the physical failure review](../reviews/2026-10-29_ACER_USB_INSTALLER_216_GROUP.md).

Current image `7869b6b5…` adds USB
`greia-logs/last-install-failure.log` persistence and the initramfs ENOSPC
fix. Its **actual live squashfs** contains all declared groups,
`install_diagnostics.py`, and the `/run/greia-installer-scratch` RAM scratch;
its default `greia-installer.service` reached the interactive UI in QEMU.
The re-authorized LaCie `/dev/sdc` (`iamaKey`, serial `eca3505216d7d3`) was
reflashed with a byte-identical first-2,270,167,040-byte readback. The
remaining gate is physical Acer boot/install from that USB. An install
through only the transaction socket is insufficient evidence; internal-disk
installation still requires separate explicit authorization.

### Physical Acer installer initramfs ENOSPC (2026-10-29)

The next physical install reached the hardware-support package step and
failed in the `initramfs-tools` postinst: `zstd` could not write
`/boot/initrd.img-6.1.0-54-686-pae` because the 1,664 MiB SYSTEM_A slot was
full. The payload plus support packages plus an ~182 MiB `mkinitramfs`
temporary tree and the 42 MiB initrd exceeded the slot. Do not "fix" this by
loosening capacity checks or expanding the boot-control/PERSIST partition.
The installer now keeps the apt archive cache and `mkinitramfs` temporary
tree in a bounded 256 MiB tmpfs at `/run/greia-installer-scratch`; only the
compressed initrd is written to the slot. Regression:
`tests/test_installer_hardware_support_install.py`. See
[the ENOSPC review](../reviews/2026-10-29_ACER_USB_INSTALL_ENOSPC_INITRAMFS.md).

### Live installer quiet-screen recovery (source contract, 2026-10-17)

Live boot entries include `nonetworking` to prevent live-boot's ifupdown
preconfiguration from writing console errors; userspace iwd/networkd still
owns connectivity. `greia-installer.service` uses `Restart=always` because
xinit can return zero after its client crashes. Its retry budget is five
starts per 300 seconds; `installer-exit-cover` attempts to repaint the existing
framebuffer cover on stop. Inspect the unit's journal and failed state when
retries are exhausted. These source mechanisms require rebuilt-image and
physical visual/recovery acceptance; a successful contract test does not prove
a text-free transition or available Wi-Fi/SSH on a particular image.

### Capable build-host process rules (2026-09-15 — `POSTR1-P5-GATE-CLOSURE-V12E`, R01-03)

- Pass the A/B release bundle as an explicit builder input:
  `sudo build/build-installer-image.sh <profile> <out> --release-bundle
  <path-to-validated-.greiaupdate-v3>` (forwarded through
  `build-legacy-x86-sd-installer.sh` / `tools/build-development-installer.sh`
  with the same flag). `GREIA_AB_RELEASE_BUNDLE_SRC` remains available as
  an explicit override for tests/harness wiring, and `GREIA_AB_TRUSTED_KEY_SRC`
  where still consumed, but normal production composition must use the
  `--release-bundle` flag: the builder v3-inspects the bundle and refuses
  a profile mismatch before any disk mutation. Note: exported environment
  does not survive sudo `env_reset`, so an export-then-`sudo build/...`
  launch fail-closes on missing A/B inputs; prefer the flag form.
- Never `umount -R` a build chroot that holds host bind mounts. The chroot
  bind-mounts propagate as shared, so a recursive unmount escapes onto the
  host and can take down host `/dev`+`/proc`+`/sys` (observed: sshd unable to
  fork sessions afterwards, lane lost until console/owner recovery). Use the
  builders' own `build/lib/safe-cleanup.sh` teardown, or per-mount lazy
  unmounts of exactly the paths the build mounted.
- Never SIGKILL a builder mid-chroot without expecting trap/cleanup races;
  prefer letting the build exit so its own teardown releases mounts and loop
  devices.
- Run the Gate-P5 closure driver as root (`sudo -n python3
  /tmp/greia-p5-*-closure.py`, the established V9/V11 procedure):
  `tools/x8_qemu/product.py` loop/mount calls carry no sudo prefix and `orb`
  is not in the `disk` group, so an unprivileged driver run fails pre-QEMU at
  clone injection with `losetup: Permission denied` (observed V12F; not a
  product finding). Disposable `/tmp` media only.
- Release-candidate build (quiet boot, SSH on, optional operator public key):
  profile `legacy-x86-i686-rc`, runbook `docs/INSTALLER_IMAGE_CREATION_AND_BOOT.md`
  §13 (pre-build gates, USB identification, required PASS lines).
- Installer media since 2026-10-21 also needs `grub-efi-ia32-bin` and
  `grub-efi-amd64-bin` on the build host; the builder fails fast if
  `/usr/lib/grub/i386-efi` or `x86_64-efi` is missing. The image is now
  p1 = FAT32 ESP, p2 = ext4 root: the SD finalizer, live-USB writer and both
  verifiers resolve the ext4 root by type through
  `build/lib/installer-image-root.sh`, never by partition number.
- Detach a long build+flash properly: `setsid nohup sudo -n bash
  tools/build-and-flash-development-usb.sh <profile> /dev/sdX > <log> 2>&1
  < /dev/null &`. A plain `nohup ... &` launched from an agent tool call is
  still in that call's process group, so when the call hits its own timeout and
  is terminated the tool reaps the **front door and `sudo`** while the deeper
  `build-*` scripts survive as orphans reparented to `systemd --user`. The build
  then finishes, writes its image, and the flash and read-back verification
  silently never happen, because both live in the front door. Observed
  2026-10-01: a 30-minute build produced a correct image and no USB write, and
  the only symptom was a missing parent in `ps`. `setsid` gives the job its own
  session, which survives. Check the front door by name, not the leaf builder.
- Overlay content is **role-scoped**: `target` composes from `build/overlay`,
  every other role from `build/installer-overlay`, and the two do not ship the
  same files. Never touch a role-specific path unconditionally at the top of a
  shared composition helper — put it inside that role's branch. An unscoped
  `chmod` of a target-only file aborted every installer build on the live leg
  (`e859fb4b`, fixed 2026-10-01).

### Persistent host apt/pool caches (build hosts only)

Repeated image builds reuse already-downloaded `.deb`s through two persistent
host caches, implemented by `build/lib/apt-cache.sh`:

```text
GREIA_APT_CACHE=/var/cache/greia-apt    (chroot /var/cache/apt/archives)
GREIA_POOL_CACHE=/var/cache/greia-pool  (chroot /var/cache/greia-pool)
```

The builders bind-mount the host caches for the chroot's lifetime, with the
apt cache mounted BEFORE debootstrap so base `.deb` downloads land in the
host cache instead of the real target/live directory (a post-debootstrap
mount would shadow them: invisible to `du -sx`, counted by `df`, and baked
into the image/squashfs); the existing `MOUNTS`/`safe_unmount_paths`
teardown releases them before compression, so cached `.deb`s never enter
the image.

Never clear these host caches (`apt-get autoclean` inside the chroot only
drops obsolete entries; `rm -rf` of the `archives/*.deb` cache and `apt-get
clean` are forbidden in the builders). Deleting them only forces a full
re-download of the package set on the next build.

### Build-host disk health and loop-device hygiene (2026-09-25 — Orbiter disk failure)

The Orbiter root disk died mid-Session-04 with SMART
`FAILED / "Drive failure expected in less than 24 hours"`; agent build
practice (retry storms without health checks, 17 leaked attached loops with
deleted backing files, build debris) amplified load, pinned ~35–45 GB and left
standing desktop probe volume against the failing disk. The full host-specific
investigation report is kept in git history only (removed from the tree in the
2026-10-16 open-source cleanup).
Binding rules:

- Disk-health preflight before heavy image churn: `sudo smartctl -a
  <root-disk>` and `sudo journalctl -k -p err --since -1d`. Not `PASSED`, a
  growing pending-sector count, or any `Medium Error` → stop disk-heavy work
  and escalate to the owner. Never "just retry".
- On a build I/O error (`Read failed because Input/output error`,
  unexpected squashfs-superblock failure after a clean `mksquashfs`), check
  `sudo dmesg | grep -i 'I/O error'` before touching source; treat it as a
  disk fault until proven otherwise.
- Run the front door in a private mount namespace on a desktop build host:
  `sudo -n unshare --mount --propagation private -- bash tools/build-and-flash-development-usb.sh <profile> /dev/sdX <out> ...`.
  Without it (2026-10-17, orbiter), the chroot rootfs mount was copied into the
  private mount namespaces of ~10 system services (logind, NetworkManager…), so
  the host-side unmount could not release the loop and a reboot was needed.
  Desktop hosts also auto-mount the stick's `sdX1`; unmount it with
  `udisksctl unmount` before the front door (it refuses a mounted target).
- QEMU verification of i386 media must use the reference-class CPU model:
  `-cpu n270` (or let `build/verify-image-qemu.sh` pick it; it already prefers
  `n270`). `-cpu pentium3` has no SSE2; Debian's i386 NumPy refuses to import,
  the installer client dies, and the bounded `Restart=always` plus
  `installer-exit-cover` repaint a clean Greia splash over the dead service — a
  CPU-model artifact indistinguishable from a stalled image (2026-10-18).
  Evidence: `docs/INSTALLATION_ISSUES_LOG.md` §35.
- Loop audit after every build/run (success, failure, interrupt):
  `sudo losetup -a | grep greia` must be empty. Any shell path that creates a
  `losetup --partscan` loop must use `build/lib/safe-cleanup.sh` and
  `safe_detach_loop`; direct `losetup -d` followed by forgetting the loop is
  forbidden. Linux loop detach is lazy: an open partition counts as a disk
  opener, so `LOOP_CLR_FD` may only set AUTOCLEAR and defer final teardown.
  Therefore `partx -d` is neither a prerequisite nor forbidden: unmount first,
  request parent detach, settle udev, and if the parent is still associated with
  partition children, use bounded `partx -d` **after** detach is pending to
  remove partition bookkeeping, then settle/recheck. Success requires both the
  parent backing association and partition children to disappear before the
  loop variable or backing/work tree is cleared. The helper pins the original
  backing identity, refuses a reused loop number, and reports userspace/kernel
  holders on bounded failure. Cleanup failure must exit non-zero and preserve
  evidence. The canonical build+flash front door also refuses pre-existing
  Greia build loops and refuses success if any remain.
- Clean `/tmp/greia-installer-build.*` and stale `/tmp/greia-session04-*`
  run dirs after each run.
- A loop that predates the current run and has already been proven to be a
  deleted-backing AUTOCLEAR orphan with no mounts/openers/holders may be
  classified in the lifecycle plan as historical poisoned kernel state. Do not
  keep inventing teardown primitives for it. Reboot before any new build.
  Read-only verification of an already-built artifact may instead use
  baseline-aware accounting: the historical loop may remain, but the verifier
  must introduce zero new Greia loops.
- Keep the build root filesystem below ~80 % during image churn; stale loops
  count as used space.
- Do not leave unmounted attached loops for desktop volume monitors to probe;
  every stale loop partition triggers re-reads of its backing disk.

---

## 13. Source verification defaults

Use the narrowest meaningful gate first, then the broader phase gate required by the current procedure.

Repository unittest discovery is preferred where a third-party `tests` package could shadow the repository namespace:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -p '<filename>' -v
```

Current common architecture audits include:

```bash
PYTHONPATH=src python3 tools/audit_activity_backend_independence.py activities
PYTHONPATH=src python3 tools/audit_activity_system_chrome_ownership.py --strict
```

Broad source gate:

```bash
make verify        # fast lane: every unit/contract/Activity test (default per turn)
make verify-full   # fast lane + heavy evidence suites (x8 QEMU rigs, install RSS gates, whole-repo sweeps)
make test-slow     # only the heavy suites
```

Lanes are owned by `tests/suite_lanes.py` (`SLOW_TESTS`, one registry for both
`tools/run_tests.py` and `tests/conftest.py`). Run `make verify-full` before
claiming install/update/release/lifecycle work complete or when a change touches
code those suites exercise. Naming a test module explicitly always runs it.
The runner neutralises host-wide `os.sync()` inside the test process (durable
writers still fsync, rename, directory-sync and re-read); a real-subprocess test
must reap its child through `addCleanup` (see `tests/simulator_supervision.py`)
so a failing assertion never orphans a process.

Do not add brittle source-string tests merely because implementation text changed. Test real ownership, lifecycle, trust, policy, state, failure and performance contracts.

---

## 14. End-of-turn handoff

Before calling substantive work complete, record:

```text
exact source SHA changed/tested
authorities read
what changed
verification actually executed
which evidence lane was exercised
what remains unverified
first blocker / next exact legitimate step
whether concurrent main advanced
```

Update the active plan, `HANDOVER.md`, manuals/skills and product/ADR docs only where `AGENTS.md` requires them for the kind of work performed.

Do not rewrite dated historical evidence to make it agree with current source. Append corrections or update the living owner instead.

## Validating on a real Acer Aspire One: what actually catches faults

Recorded 2026-09-30 after a session in which six defects passed source review
and the desktop harness, and were only caught on the physical reference
device. Each one below was found by a specific check, so the check is what
this section exists to preserve.

### The device is not the harness

`tools/panel_screenshots.py` renders a panel headlessly on the development
host. That host runs as a user who can write system settings, and it has no
live microphone, so two whole classes of fault are invisible there:

- **Permission faults.** The launcher runs as `greiakid`; system settings live
  in `greiapel`-owned directories. A control that renders and accepts clicks can
  be a complete no-op on the appliance and look perfect in the harness.
- **Live-data layout faults.** With no level available there is no bar to draw,
  so a bar that is drawn at the wrong width, in the wrong column, or clipped by
  a neighbour never appears.

Render on the device instead, against the live services:

```
ssh greia@<device> 'sudo -u greiakid python3 <render script>'
```

and let the script connect to the real level service so the bar path runs.

### "active" is not health

A unit in a restart loop reports `active` between restarts. Every health check
that asks only `systemctl is-active` returns healthy on a machine that has
never reached a usable screen. Always read the counter too:

```
systemctl show greia-launcher -p NRestarts --value
```

Two boot loops in this session both presented as `active`. The climb in
`NRestarts` was the only reliable signal.

### The session swallows the traceback

(Since 2af434da the Shell's warnings and uncaught crashes are also routed to the
journal by `configure_launcher_logging`; read `journalctl -t greia-launcher`
first. The redirect below remains for crashes before logging is configured.)

`greia-x-session` runs `python3 -m greia_launcher.child_shell`, and when it
exits non-zero the journal records only `exited with status 1` before trying
`trusted_presentation`. The Python traceback never reaches the journal. To see
it, redirect the session's own stderr:

```
sed -i 's#-m greia_launcher.child_shell$#-m greia_launcher.child_shell 2>/run/greia-os/session.err#' \
  /usr/local/lib/greia-os/greia-x-session
```

Restore the file afterwards. Boot markers (`GREIA_BOOT event=...`) show how far
the launcher got before it died and are the right first stop when the unit
merely exits.

### Read the device's source, not your working copy

Code was deployed by copying files into `/opt/greia-os/src` throughout the
session, and for a long period the panel on screen was a stale process: the
change was on disk, the launcher had not been restarted, and the work was
reported as present. After any direct-to-device copy: restart the unit, and
confirm the deployed file actually contains the change (`grep` it on the
device). When a feature is "missing" but present in source, check the running
process before changing code again.

### Verify against the real service, not a stub

The microphone processing policy already had API routes and tests
(`tests/test_parent_audio_api.py`). It was reported as "unexposed by the API"
and duplicate routes were added before the existing ones were found. Locate the
route and its tests before adding anything.

### Do not claim hardware facts from source

The `greia_mic_light` ALSA ExtPlugin was never built into the image, so the
endpoint could not open even though `aplay -L` listed it. The availability
probe correctly refused to write its marker, the backend reported the endpoint
unavailable, and the audio service routed `off` on `default` with
`fallback_reason=lightweight_unavailable`. Everything reported itself healthy,
because fail-closed correctness is indistinguishable from "not installed" until
the device is asked directly:

```
arecord -D greia_mic_light -d 2 -f S16_LE -r 16000 -c 1 /dev/null
ls /run/greia-audio/
```

### Provisioning gaps are boot faults

Three separate boot loops came from provisioning, not application code:

- `tmpfiles.d` named the group `greiaprofiles`, which `compose.sh` never
  creates (`pipprofiles` is the real one). `systemd-tmpfiles` failed and left
  `/run/greia-os` root-owned, so Xorg could not write `Xorg.0.log`.
- The audio endpoint probe shipped without its executable bit, so its oneshot
  failed `203/EXEC` and never wrote a marker.
- `/var/lib/greia-os` was `0750 greiapel:greiapel`, so `greiakid` could not
  stat its own activity package tree. The missing directory surfaced as
  `EACCES` rather than `ENOENT`, which presented as a permissions bug and hid a
  path that nothing had ever created.

Naming an identity that no build step creates must fail the build.
`tests/test_image_tmpfiles_identities.py` now enforces that, including that
`/run/greia-os` is owned by `greiakid` and that `greiakid` retains traversal
into the parent home without read access to it.

### Package hygiene on a live device

Installing and removing build tooling on the appliance is a last resort, not a
verification method: the target image has been footprint-pruned, so `gcc` is
present but cannot execute `cc1`. Record what `apt-get autoremove` removed
from `/var/log/apt/history.log*` afterwards, and prefer building an artifact
in the image composition step (`build/lib/compose.sh`) where the toolchain is
installed and removed deliberately.

### Fresh installed-boot profile check (2026-10-07)

A correct `/var/lib/greia-profiles/data` root is not sufficient. On fresh
install, first-boot completes before the Parent creates the initial profile.
Acceptance must therefore check the **newly created profile root after Parent
creation**, not only B4/B5 markers:

```text
data/<profile>             group pipprofiles, mode 2770
data/<profile>/activities  group pipprofiles, mode 2770
data/<profile>/customization group pipprofiles, mode 2770
child-created progress/storage writable by greiakid
```

A profile root at `2750` is a hard failure even when the data root is
`2770`. Do not repair it on-device during first-boot acceptance; preserve the
failure and fix the creation mechanism in source.

On single-root profiles, `greia-boot-observer.service` is not expected to be
enabled; it is A/B semantic-slot infrastructure. Developer `status` and
`logs` should work even if the display endpoint is unavailable; screenshots
and input remain display-dependent.


## Voice ASR comparison defaults (2026-10-22)

New authoring verification/extraction uses pinned cached multilingual Whisper Base;
see SETUP §7.5 and `docs/agents/GREIA_AUTOMATED_VOICE_REVIEW.md`. ASR comparison
ignores diacritics by default, preserving exact scripts/audio. Use
`ignore_accents=false` in request JSON/Python or `--strict-accents` on generation,
carrier extraction and corpus plan/review/reassess for strict comparison. New
carrier plans use v6; do not resume old frozen plans under new code. Saved-evidence
reassessment preserves the original recognizer identity; it is not a new Base run.
The proposed shared asynchronous queue is not implemented by this policy change.


## Frozen priority voice completion (2026-10-22)

The historical `finish_voice_priority.py` bulk producer is **stopped for rejection
diagnosis**. Do not resume unchanged v6 production or submit fresh takes.
Normal automatic VoiceEngine requests now use v7 target-only extraction.
For failed saved v6 sources use `tools/recover_voice_candidates.py`: stage in a
new external work folder, inspect the completed stage, then `--install` that same
folder. It reuses selected masters, exact Base cache, existing packaging and
CorpusRunner/RunStore transactions, forbids synthesis and retains cumulative
budgets. Exact commands/stop/recovery rules live in
`GREIA_VOICE_CORPUS_REGENERATION.md` § V7 saved-provider recovery. Other history
sources and the preserved completed letter_A job must be reconciled separately;
no job may be duplicated. Deferred scope and human listening remain separate.


Voice usage reference: `tools/greia_voice_core/README.md` documents exact current
CLI/JSON/Python defaults, result handling, service ports and continuation commands.
Ordinary API verification and strict carrier-corpus gates have different eligibility,
retry and exit contracts; do not substitute one for the other. Automatic short-request routing is now implemented at VoiceEngine entry; the
separate shared verification queue remains proposed work.


Normal VoxStage character requests default to short_text_mode=auto (≤4 words,
optional additional alphanumeric bound), with three total takes and final Base
checks including Dani. CLI `--short-text-mode off` bypasses wrapping. Both that
and `--verification off` are necessary for zero ASR. Native pedagogical requests
are excluded. Frozen corpus raw requests disable auto wrapping internally;
source `short_policy.py`, `short_phrases.py`, `short_delivery.py` and the shared
`target_quality.py` own this path. See the usage README for fields and recovery.

Historical saved recovery selections use `--source-selection` with exact
plan/scope/media/receipt/completed-job pins; see the corpus manual's schema.
Provider48kHz and retained22,050Hz carriers may differ legitimately: the adapter
requires exact reproduction through the existing packaging transform. This is
not a synthesis operation or an excuse to ignore a hash mismatch.

Normal short speech now uses period-separated intros and warm clear careful
reading defaults. The prepared final-take v2 continuation is220 exact IDs with
one take left; it is not running while the12 live prompt probes' failed readiness
gate is investigated. New coordinator `continue_voice_priority_v7.py` uses normal
VoiceEngine and existing corpus transactions; inspect its progress/journal and
GenerationResult.evidence_dir. GREIA_VOXSTAGE_HTTP_TIMEOUT (default120s, max7200)
is separate from GREIA_VOXSTAGE_TIMEOUT; accepted submissions must be recovered
by their existing key after response timeouts, never duplicated. See the corpus
manual and current HANDOVER before execution.


## Live installer SSH toggle (owner decision 2026-10-29)

The installer's Wi-Fi screen has an off by default on ordinary installer images toggle for SSH on the
running live installer using `greia` / `greia` and ordinary password sudo.
The fixed local install-transaction socket operations control only `ssh.service`;
the installed target keeps its independent release SSH policy. The device
advertises `greia-installer.local` through Avahi when networking permits.
Source/demo evidence does not establish actual SSH or network connectivity.
Patch the existing USB and run physical acceptance per
`docs/agents/2026-10-29_INSTALLER_USB_SSH_RECOVERY.md`.


### Parent client runtime permissions (2026-10-29)

The real Acer A/B image had `/usr/share/greia-parent-app` mode 0700 and
`greia-parent.service` could not run its integrity precheck. Pinning/staging and
image composition now normalize public static-client directory/file modes;
the composed-root verifier rejects unreadable client trees. See
`docs/agents/2026-10-29_ACER_INSTALLER_AND_PARENT_FIX_HANDOFF.md` for the
physical read-only evidence and required new-bundle/installed acceptance.


## Parent-controlled SSH on normal images (2026-10-30; source only)

Owner requested the Parent switch to enable `greia` / `greia`, including on
normal images; SSH defaults off and root login stays disabled. The installed
Parent API uses the fixed-operation `greia-parent-ssh.socket` / service, and
advertises the capability only when its socket is accessible. These new unit
files require a full-system image/update; a Python-only `.greia_update` cannot
install them. Real systemd, SSH login, disable, reboot and Acer acceptance have
not run. Do not assume the currently installed Acer already contains this.


## Parent Activity installation (2026-10-30; source evidence)

Normal-image Parent upload is offered when its package store is writable.
Install/remove must happen at the profile picker under the shared session
lock; the Shell watches the active generation pointer and refreshes authority.
The local HTTP test covers real validation, rejection, install and registry
discovery, but not installed systemd permissions, Bubblewrap, browser or Acer.
Use a disposable installed Linux image for those checks before device delivery.


The 2026-10-30 Acer test applied the Activity upload application update but
returned 409 at the profile picker. ActiveProfileSession must atomically
publish `active-profile.json` with its shared parent-directory group as well
as mode 0660; `/run/greia-os` is not setgid on existing images. Parent and
Shell must read the same lock-protected status. A follow-up physical retry is
required; do not infer successful upload from the capability alone.
