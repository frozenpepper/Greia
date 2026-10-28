# Greia Public Release Readiness

**Status:** RELEASE READINESS GATE / AUDIT CHECKLIST — **not** a competing implementation plan  
**Created:** 2026-08-29  
**Audit baseline:** `08fe71b077d47b511c105bde5c2e8fdb88be7b92` (`main`) — historical, not current HEAD  
**Current use (2026-10-28):** This is the release *requirements checklist*, not a claim that current main is certified. Sections with old audit baselines (including §3 and its stated missing files/update features) are **historical snapshots**, not a current verdict. Installed QEMU A/B/application update acceptance now passes; the real release-builder boot-cover gate, physical hardware test, public rights/provenance audit and full source verification remain open. See [the concise first public release execution sheet](FIRST_PUBLIC_RELEASE_EXECUTION.md), [the latest image/update report](../reviews/2026-10-28_UPDATE_SYSTEMS_SITUATION_AND_FIRST_IMAGE.md), `HANDOVER.md` and exact source/image evidence. No old physical result certifies today's source.  
**Primary audience:** Greia maintainers, release operators, reviewers, test operators  
**Target:** a public Greia release that an ordinary parent/family can install, use, administer, recover and keep updated without Linux or developer knowledge

---

## 0. Authority and relationship to the active architecture plan

This document is a **release gate**, not Greia's active implementation sequence.

Implementation ordering remains owned by:

```text
docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md
```

At this audit baseline, `HANDOVER.md` identifies **R7 — direct graphics/session/input architecture** as the first incomplete blocking platform phase. Release work must not bypass, reorder or weaken that plan merely to make a public image appear finished sooner.

This document instead answers a different question:

> **What must be true before Greia can responsibly be presented to the public, and especially before it can be handed to a normal non-technical family as a supported product?**

Where an accepted ADR, source/runtime declaration, product requirement or the active plan is stricter than this checklist, the stricter authority wins.

---

# 1. Release principle: a family appliance, not a Linux project

For an ordinary-family release, the release criterion is not “the source builds” or “the developer can recover it over SSH.”

A normal parent must be able to perform the supported lifecycle without learning Linux concepts:

```text
download Greia
→ create installation media
→ install safely
→ first boot
→ create/configure child profiles
→ connect ordinary hardware/network
→ let a child use Greia
→ manage Greia Parents
→ install/update/remove supported Activities
→ back up child data
→ update Greia OS
→ recover from ordinary failures
→ restore/reinstall without losing child data
```

The supported path must not require the parent to use:

- a shell or terminal;
- SSH;
- `sudo`;
- package-manager commands;
- raw `/dev/...` disk paths;
- manual partitioning;
- IP-address discovery as the normal path;
- editing configuration files;
- Git/GitHub;
- Python tooling;
- Greia project internals;
- developer credentials or hidden developer controls.

If the only reliable recovery for a realistic user failure is “SSH in and fix it,” the release is not ordinary-user ready.

---

# 2. Do not confuse the three public-release thresholds

Greia should use three explicit thresholds rather than one vague “public” state.

## 2.1 Threshold A — Public source repository

The source repository may become public before the OS is ordinary-user ready, **only** when repository publication itself is safe and legally clean.

Minimum threshold:

- licensing/provenance audit complete for all public repository material;
- canonical license/notice files present;
- repository history checked for secrets/private material;
- contributor/security/governance entry points suitable for public participation;
- README clearly says the product is pre-release if no supported binary release exists;
- no claim that current development evidence is a certified user release.

Passing Threshold A does **not** mean Greia OS is ready for families.

## 2.2 Threshold B — Public technical preview

A technical/developer preview image may be published before full family release if it is clearly labelled experimental and its limitations are impossible to mistake for supported-product guarantees.

A technical preview may legitimately lack some stable-release facilities, but it must still:

- not be dangerously destructive beyond an explicitly confirmed install action;
- not expose known default remote privilege to an untrusted network;
- have a documented supported test-hardware scope;
- have a reproducible/verified release artifact;
- have clear known issues and recovery instructions;
- preserve the child-facing no-desktop/no-shell contract during normal use;
- be explicit that developer/test features are not part of the future release security model.

A technical preview is for testers, contributors and technically capable early adopters — **not** for an ordinary family.

## 2.3 Threshold C — Ordinary-family public release

This is the target of the rest of this document.

For this threshold, every blocking gate in Sections 5–23 must pass against **one immutable release-candidate source revision and its exact built artifacts**. Evidence from older commits may guide engineering but cannot certify a newer release candidate.

---

# 3. Current audit snapshot

The repository has substantial platform, Activity, simulator, Parent, installer, hardware and authoring work, and the current source gate is healthy. The audit baseline's latest commit records `make verify` at **1462/1462 PASS**.

That is necessary but not sufficient for release.

Important ordinary-user release gaps visible in the current authoritative repository include:

1. **R7 remains open.** Production still uses the provisional Xorg/Xinit compatibility path while the final direct display/session/input architecture and its evidence are unresolved.
2. **The normal legacy-x86 profile is still `certification_state = "unverified"`.** It also uses the current `bios-single-ext4` layout and `display.adapter = "xorg"`.
3. **Raspberry Pi 400/500 remain first-class required ARM targets but R8/final ARM certification is not closed.**
4. **Greia Parents HTTPS is implemented in source but not yet physically accepted.** Owner-selected home-LAN HTTPS with self-signed certificate replaces provisional plaintext access. Normal Parent-password pairing remains; QR/Allow/Deny is not required.
5. **System update activation is not release-capable on current single-root images.** Unsigned v3 bundle construction/inbox work exists, but A/B payload/layout, inactive-slot activation, boot-health confirmation and rollback are not available on the current profile.
6. **Portable `.greiabackup` release closure is still required.** A normal family needs a supported way to preserve and restore child data before Greia can ask them to trust upgrades/reinstalls.
7. **`.greiaactivity` initial installation exists, but full update/migration/rollback/provenance lifecycle remains R10 work.**
8. **Selectable language is broader than proven localization coverage.** Locale persistence is not proof of translation, font, shaping or RTL readiness.
9. **The public licensing/provenance audit is explicitly pending.** At the audit baseline, standard root files such as `LICENSE`, `NOTICE`, `SECURITY.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `PRIVACY.md` and `CHANGELOG.md` are not present at those conventional paths. The separate Greia Parents HTML repository also lacks a root `LICENSE` at audit time.
10. **Some living readiness documents have drifted behind newer work.** For example, setup/readiness prose still describes shared voice packs as pending although newer committed voice evidence records a promoted owner-accepted v0.2 library. A release needs a final documentation freshness pass rather than relying on dates alone.
11. **Source verification is broader than many prototypes but narrower than a release gate.** `make verify` currently covers unit tests, project/Activity validation, shell syntax and source footprint; it intentionally does not prove the final installer, physical hardware, release-profile security, external Parent client, licensing, update rollback or backup/restore.

**Current disposition at this baseline:** **NOT READY for Threshold C ordinary-family public release.**

That is expected for the current `0.13.x` early-development stage and is not a criticism of the work already completed.

---

# 4. Release scope must be frozen before certification

Before creating the first release candidate, write a short release scope record answering all of the following.

## 4.1 Hardware scope

Explicitly name what the release supports. Do not market “PC support” if the evidence is really “one legacy BIOS Acer model.”

At minimum decide:

- legacy x86/i386 supported machines/classes;
- x86-64 support status;
- BIOS vs UEFI support;
- Raspberry Pi 400 status;
- Raspberry Pi 500 status;
- touch support status;
- controller support status;
- Wi-Fi chipset expectations;
- minimum RAM;
- minimum storage;
- minimum display resolution;
- whether external displays are supported;
- whether suspend/resume is supported or deliberately absent.

Use Greia's compatibility vocabulary: **Certified / Generic-compatible / Degraded / Unsupported / Unknown**.

## 4.2 Product scope

Freeze which product capabilities are supported in the release:

- built-in Activities;
- Writing and Painting;
- Greia Encyclopedia, if included;
- Greia Parents HTML client;
- independent `.greiaactivity` installation;
- Activity update/removal;
- system update channel;
- backup/restore;
- network management;
- maintenance SSH switch;
- microphone processing;
- controller support;
- Awards/progression;
- supported UI languages.

A capability may be excluded from a first public release if the accepted architecture/product contracts allow that exclusion. It must not be shipped half-enabled and presented as reliable.

## 4.3 Support promise

Define:

- release classification (`beta`, `stable`, etc.);
- supported hardware list;
- expected support lifetime;
- how security fixes are delivered;
- where users report bugs;
- what data Greia collects, if any;
- what is explicitly experimental.

---

# 5. Gate A — Finish the blocking architecture/release spine

**Blocking for ordinary-family release: YES**

The active architecture plan must reach its own completion criteria. This release gate does not redefine those phases.

Minimum release consequences include:

- R7 accepted production display/session/input architecture;
- R8 accepted Raspberry Pi 400/500 ARM image/runtime path where those targets remain part of the first release promise;
- R9 complete if Web Activities are part of the release contract;
- R10 complete safe Activity package lifecycle;
- R11 complete portable backup/restore;
- R12 complete Parent privileged-service integration;
- R13 complete branded boot/recovery continuity;
- R13B complete rollback-safe Greia OS update/recovery;
- R14 complete exact multi-architecture release certification.

### Evidence

- active plan marked `COMPLETE` according to its own closure protocol;
- `HANDOVER.md` no longer identifies an incomplete blocking architecture phase;
- final evidence tied to the release-candidate SHA and artifacts.

### No-go

Do not manufacture a “release exception” that lets a user-facing launch bypass a security, data-integrity, update or recovery prerequisite from the active plan.

---

# 6. Gate B — Create a real release image/profile, separate from developer images

**Blocking for ordinary-family release: YES**

The release profile must be intentionally different from a developer/test profile.

## Required release properties

- no developer remote-control package set;
- SSH **off by default**;
- no development SSH bootstrap;
- no development-only fixed SSH exposure;
- root SSH disabled;
- no debug console/verbose development boot configuration in the normal path;
- no developer pairing token/bootstrap accepted as production authority;
- no hidden test services listening by default;
- no test Activities/assets that are not part of the product;
- no release signing keys or trusted update public keys are provisioned (the unsigned `.greiaupdate` v3 flow has no signing-key workflow);
- exact release version embedded in the system identity;
- exact build profile recorded in release provenance;
- `certification_state` changed only when the corresponding evidence exists;
- release image consumes only pinned/reviewed external artifacts, including the exact Greia Parents client revision.

## Release/dev separation tests

Prove on the built release image that:

- developer SSH credentials do not work because the developer service is absent/disabled;
- developer remote-control endpoints are unavailable;
- developer unsigned deployment paths are not exposed as normal user features;
- no development logs or diagnostic consoles become child-visible;
- developer-image conveniences cannot be re-enabled accidentally by a normal Parent API request.

---

# 7. Gate C — Installer and first-run experience for a normal parent

**Blocking for ordinary-family release: YES**

A normal parent must be able to get from a download to a usable Greia without a terminal.

## 7.1 Public download artifacts

Provide per-supported-target artifacts with unambiguous names, for example conceptually:

```text
Greia-<version>-Legacy-PC.img.xz
Greia-<version>-Raspberry-Pi.img.xz
SHA256SUMS
content-integrity hashes (SHA-256, not release signatures)
release notes
hardware compatibility link
```

Do not require a parent to choose between internal build-profile names they cannot understand.

## 7.2 USB/SD creation

The public instructions should use a well-known graphical imaging tool on Windows/macOS/Linux where practical. Command-line flashing may remain an expert alternative, not the normal path.

Instructions must clearly explain:

- the removable device will be erased;
- how to identify the correct target;
- how to verify the downloaded artifact if desired;
- how to eject safely;
- what the first boot should look like.

## 7.3 Installer UX

Prove the graphical installer at every supported minimum display size:

- language is the first interaction as designed;
- keyboard/pointer controls work;
- installation target list shows only eligible devices;
- removable installer media is never offered as a destructive target by mistake;
- internal disk identity is rechecked before destructive work;
- destructive confirmation is plain-language and unmistakable;
- insufficient RAM/storage/power is explained before destruction where detectable;
- progress never appears frozen without explanation;
- known recoverable errors provide a Greia-branded next action;
- fatal failures do not fall into a Linux shell for a normal user;
- success clearly tells the parent when to remove media/reboot.

## 7.4 First boot

The supported first-boot flow must allow a family to reach a useful child profile without networking or a cloud account.

Prove:

- branded boot continuity;
- no Linux text/desktop/login prompt;
- profile creation/picker is usable;
- at least one child profile can be created locally;
- Wi-Fi can be configured from a parent-facing Greia surface where supported;
- network failure does not block offline use;
- child reaches built-in Activities without setup knowledge.

## Evidence

Run the complete install from freshly created media on every certified hardware family. Record video/frame evidence where the no-Linux-visible contract is being certified.

---

# 8. Gate D — Production Greia Parents security and onboarding

**Blocking for ordinary-family release: YES**

Network Parents uses HTTPS on port 8766 with a persistent device-generated self-signed certificate. The browser may display its normal trust warning; a parent accepts it only when visiting their own Greia on the home LAN. Local Parent controls use loopback-only HTTP on 127.0.0.1:8767. This is the owner-approved simple transport; do not add required cloud PKI, QR/challenge/Allow rituals, or companion software.

## Required working flow

1. Parent opens the device-displayed HTTPS URL from the home network.
2. Parent acknowledges the browser's self-signed certificate warning for their own Greia if shown.
3. Parent signs in with the existing Greia Parent password.
4. Greia issues a separate revocable device credential and subsequent requests stay on HTTPS.
5. Reconnect and independent device revocation continue to work.
6. No secrets are exposed through network discovery or ordinary logs.
7. Direct HTTP on the LAN refuses management and no insecure redirect/fallback exists.

## Required verification

- HTTPS with self-signed certificate after first boot; key never preinstalled in a shared image;
- persistent key and certificate after normal service restart and OS update;
- browser on real phone/laptop, including first-visit certificate warning;
- local S+T Parent panel works using loopback-only HTTP, including password changes;
- a wrong device, expired/invalid credential and revoked client do not gain management access;
- the existing credential rate limiting, request bounds and unprivileged service boundary remain intact;
- proper stop/failure if certificate generation cannot run or the key is damaged;
- known tradeoff: self-signed HTTPS does not automatically authenticate a device against an active LAN impersonator.

## Initial Parent password

The owner-approved initial password remains `greia`. Parents can change it through the existing controls. Review the final user-facing instructions and local network exposure; do not silently create a second credential or force a new pairing ceremony.

## Product UX

Test the real pinned HTML client on:

- current desktop Chrome/Chromium family;
- Safari/iOS-class viewport if officially claimed;
- Android/mobile Chromium-class viewport if officially claimed;
- small phone layout;
- tablet layout;
- ordinary desktop layout.

The Parent UI must hide unavailable capabilities rather than exposing an engineering dashboard of unfinished features.

---

# 9. Gate E — Safe Greia OS updates with automatic rollback

**Blocking for ordinary-family release: YES**

A public appliance needs a supported way to receive fixes without reinstalling by hand.

The current `.greiaupdate` source foundation is useful, but ordinary-family release requires the complete update lifecycle.

## Required system-update capabilities

- canonical A/B or equivalently rollback-safe system layout accepted for each release hardware family;
- canonical builder emits the exact slot payload consumed by `.greiaupdate`;
- exact platform/architecture/profile compatibility checks;
- inactive-slot-only staging;
- free-space preflight;
- power-safety preflight where available;
- bounded write/update process;
- boot-attempt limit;
- post-boot health confirmation;
- automatic rollback when candidate boot/health fails;
- rollback-compatible shared-state migrations;
- preservation of profiles/saves/creations/progression/credentials/settings;
- Parent-visible progress and final result;
- normal network update source;
- offline `.greiaupdate` path;
- removable-media update discovery only after Parent authorization;
- downgrade/replay policy;
- interrupted-download and interrupted-staging behavior;
- emergency bad-release withdrawal process.

## Failure injection

Prove at minimum:

- corrupt/tampered bundle;
- wrong architecture/profile;
- truncated/corrupt bundle;
- insufficient free space;
- interrupted network receive;
- power loss/interruption at safe representative staging points;
- candidate fails to boot;
- candidate boots but never confirms health;
- shared-state migration cannot complete;
- previous slot still boots and child data remains intact.

No release update capability is enabled merely because bundle creation succeeds.

---

# 10. Gate F — Portable backup, restore and preserve-profile recovery

**Blocking for ordinary-family release: YES**

Before asking families to trust Greia with drawings, writing, progress and child customization, provide a supported backup and restore path.

## Required `.greiabackup` behavior

- logical/open archive, not raw filesystem dump;
- architecture-neutral;
- profiles and presentation settings;
- Writing/Painting creations;
- Activity durable state;
- progression/rewards/Awards;
- appropriate bounded history;
- installed Activity inventory;
- dormant state preserved for Activities not currently installed;
- machine secrets/transient caches excluded;
- integrity validation;
- safe import staging;
- clear conflict/version behavior;
- backup failure never destroys source data;
- restore failure leaves the current machine recoverable;
- cross-architecture restore tested;
- restore after preserve-profile reinstall tested.

## Parent UX

A normal Parent surface must offer understandable operations such as:

```text
Back up this Greia
Restore a backup
```

The UI should explain what is included, destination/source media, and success/failure without paths or archive internals.

If backup encryption is a release feature, it requires its dedicated reviewed security design. Do not invent ad-hoc password encryption during release packaging.

---

# 11. Gate G — Complete Activity package update/removal lifecycle

**Blocking for ordinary-family release when independent Activity installation is supported: YES**

Initial `.greiaactivity` validation/install is not enough for a maintained public ecosystem.

## Required lifecycle

- strict bounded archive validation;
- package identity/version semantics frozen;
- publisher/origin/provenance model appropriate to the supported distribution channels;
- compatibility classification;
- immutable installed versions;
- staged update validation;
- save migration on a working copy/snapshot;
- migration validation;
- atomic activation;
- rollback to previous package after failed update;
- preserve child saves on uninstall by default;
- explicit separate “delete child data” action if supported;
- reinstall reconnects preserved dormant saves safely;
- downgrade policy;
- built-in packages protected from ordinary replacement;
- independent package cannot self-claim system privilege;
- clear Parent trust/source language.

## Release-scope alternative

If full independent installation is deliberately not part of the first family release, disable/hide it cleanly and document that scope. Do not expose a partially safe package mutation path as a finished parent feature.

The active architecture plan remains authoritative about whether R10 itself is required before overall Phase-0 closure.

---

# 12. Gate H — Built-in Activity/content release audit

**Blocking for ordinary-family release: YES**

A platform can be technically stable and still fail as a children's product if the shipped Activities are unfinished, inconsistent or confusing.

Create a release inventory of every built-in Activity and classify it:

```text
SHIP
HIDE/EXCLUDE
EXPERIMENTAL — not in family image
BLOCKED pending acceptance
```

## Per-Activity release checklist

Every shipped Activity must prove:

- manifest/package validation;
- launch READY;
- normal exit;
- Greia Home return;
- crash/forced-stop return to a valid Shell;
- no Activity can cover/intercept real protected Home/Back;
- intended keyboard/pointer/touch/controller semantics;
- no dead ends requiring reading beyond the Activity's intended educational purpose;
- visual quality acceptable as a finished child product;
- audio is reviewed and not clipping/missing;
- no runtime TTS/AI dependency accidentally introduced;
- no unaccepted voice asset packaged as final content;
- saves/autosaves survive exit/restart;
- quota/full-storage behavior is understandable;
- backup/restore participation;
- no sibling-profile leakage;
- no child-visible filesystem/browser/desktop UI;
- language fallback works;
- actual low-end performance accepted on the claimed floor;
- no unbounded cache/history/event growth;
- no developer/reference/test assets visible.

## Mandatory core Activities

Writing and Painting must satisfy `docs/product/PHASE0_CORE_CREATION_ACTIVITIES.md`, including physical/visual/input/performance and save/recovery requirements — not merely source existence.

## Encyclopedia

If the Encyclopedia ships in the first family image:

- finish its owner visual direction gate and subsequent approved migration scope;
- complete the intended narration pack through the canonical Voice Production Engine;
- integrate only owner-listened/accepted clips;
- verify every entry/navigation path on the release candidate;
- verify that missing optional narration fails soft rather than making the Activity unusable.

## Content review

Perform a human release review of:

- child appropriateness;
- factual educational claims where applicable;
- grammatical/localization quality;
- praise/feedback tone;
- accidental scary/inappropriate imagery/audio;
- age/difficulty metadata;
- accessibility of instructions;
- copyrighted/third-party content provenance.

---

# 13. Gate I — Hardware certification and compatibility communication

**Blocking for ordinary-family release: YES**

Greia must publish what it actually supports, not what Linux might theoretically support.

## Certified-family test dimensions

For each certified device/family record:

- installer media boot;
- installed-system boot;
- reboot/shutdown;
- no visible Linux in normal/failure user paths;
- graphics/display and resolution behavior;
- keyboard;
- pointer/touchpad;
- touch if claimed;
- controller if claimed;
- audio output;
- microphone if claimed;
- Wi-Fi;
- Ethernet where present;
- removable storage;
- internal storage reliability;
- Parent discovery/pairing;
- update/rollback;
- backup/restore;
- Activity launch/crash return;
- long-session stability;
- resource measurements.

## Required reference evidence

The active architecture plan currently requires final evidence including:

- exact Acer inventory/profile;
- 768 MiB QEMU installer/runtime;
- non-destructive Acer USB boot;
- Pi 400 physical acceptance;
- Pi 500 physical acceptance;
- direct graphics/input/audio;
- controller behavior;
- package/update/backup/recovery paths.

## Public compatibility page

Publish a parent-readable table with:

- exact certified models;
- generic classes with confidence level;
- known degraded features;
- unsupported boot modes/devices;
- minimum RAM/storage/display;
- last Greia version tested.

Do not force families to read engineering evidence bundles to know whether their machine is a reasonable target.

---

# 14. Gate J — Performance, resource and storage-pressure acceptance

**Blocking for ordinary-family release: YES**

Resource cost is part of Greia correctness because the Acer-class floor is intentional.

## Measure on exact release artifacts

At minimum capture:

- installed core footprint;
- free space after fresh install;
- boot time to usable profile picker;
- launcher idle RSS/CPU;
- Parent service idle RSS/CPU;
- Activity launch latency;
- Shell return latency;
- representative lightweight Activity FPS/input latency;
- representative heavy Activity FPS/input latency;
- Writing memory/typing/emoji latency;
- Painting stroke latency/RSS;
- Encyclopedia runtime if shipped;
- update staging free-space requirement;
- backup temporary-space requirement;
- prolonged session memory growth;
- repeated Activity launch/exit memory/process/FD growth;
- controller reconnect cost;
- network-offline behavior.

## Storage-pressure tests

Prove behavior with:

- low free space;
- full Activity quota;
- full creation library bound;
- failed autosave;
- backup destination full;
- update inbox insufficient space.

Greia must not silently delete old child creations to make itself appear healthy.

---

# 15. Gate K — Security review and hostile-input testing

**Blocking for public source publication in part; blocking for ordinary-family binaries: YES**

Write and review a concise release threat model covering at least:

- curious child;
- one child trying to access a sibling profile;
- malicious/buggy Activity;
- malicious `.greiaactivity` archive;
- malicious USB/SD media;
- LAN attacker;
- stolen/lost paired Parent device;
- malicious/compromised update source;
- corrupted system/update/backup files;
- accidental Parent misuse;
- development features accidentally present in release.

## Required technical review

- per-Activity isolation negative tests;
- PermissionBroker/grant negative tests;
- Bubblewrap failure fails closed;
- no raw physical-device authority for ordinary Activities;
- no sibling profile data exposure;
- no executable removable-media autorun;
- archive traversal/symlink/hardlink/device/bomb/case-collision rejection;
- Parent API request-size and malformed-input bounds;
- Parent service remains unprivileged;
- no generic root/shell RPC;
- release listening-service/port allowlist;
- SSH default-off verification;
- update bundle-integrity/rollback tests;
- backup parser hostile/corrupt input tests;
- secret/token redaction in logs;
- bounded logs/history/caches;
- dependency vulnerability review;
- OS package security-support status.

## Repository-history secret audit

Before changing the private repository to public:

- scan the full Git history, not just current files;
- check for private SSH keys;
- Wi-Fi credentials;
- API tokens;
- release signing keys;
- Parent bearer/pairing tokens;
- personal files/data;
- generated model/cache paths containing sensitive material;
- accidentally committed third-party proprietary content.

If a real secret ever entered history, rotate/revoke it **before** publication and rewrite history if necessary for disclosure prevention.

**Status 2026-10-16:** a scan of every blob reachable from any ref found no private keys, cloud or GitHub tokens, Wi-Fi passphrases or real passwords; secret-like strings are test fixtures, and the shared development login is the documented developer-image credential. History does contain the author's local checkout paths (old `HANDOVER.md` revisions and earlier voice receipts) and home-LAN addresses of test devices. Whether to publish the full history or a fresh squashed history remains an owner decision.

---

# 16. Gate L — Licensing, provenance, trademark and privacy

**Blocking for public source repository: YES**  
**Blocking for ordinary-family release: YES**

Complete the existing public-release licensing gate in `docs/governance/LICENSING_AND_TRADEMARK.md`.

## Repository legal hygiene

At minimum provide/complete:

- canonical MPL-2.0 license text for Greia-owned software coverage;
- CC BY 4.0 documentation/media notices where applicable;
- Apache-2.0 notices for any explicitly copyable scaffolds/templates using it;
- third-party dependency notices;
- font license/provenance, including Nunito Sans and other release fonts;
- audio/voice asset provenance and distribution rights;
- image/icon/art provenance and distribution rights;
- source snippets/dependencies license audit;
- SPDX identifiers or directory-level notices where practical;
- image/distribution source-offer obligations for Linux/upstream packages;
- exact licensing for the separate Greia Parents repository;
- public fork/rebranding/trademark policy appropriate to the real project/entity;
- policy for `Greia Approved`/official trust marks if used.

## Standard public project files

Before public-source launch, add and review the appropriate root/public entry points, normally including:

```text
LICENSE
NOTICE or THIRD_PARTY_NOTICES equivalent
SECURITY.md
CONTRIBUTING.md
CODE_OF_CONDUCT.md
PRIVACY.md or a clearly linked privacy document
CHANGELOG.md or an equivalent release-history surface
```

Exact file naming may differ if the documentation architecture deliberately chooses another canonical location, but a public visitor must be able to find the information immediately.

**Status 2026-10-16:** `LICENSE` (MPL-2.0), `NOTICE.md`, `SECURITY.md`, `CONTRIBUTING.md` and `CODE_OF_CONDUCT.md` exist at the root. `PRIVACY.md` and `CHANGELOG.md` do not exist yet, and GitHub private vulnerability reporting (named in `SECURITY.md`) must be enabled in the repository settings.

## Privacy review

Document what Greia stores and transmits.

The default release should remain consistent with Greia's local/offline-first principles:

- child profiles and creations local by default;
- no behavioral advertising;
- no hidden analytics upload;
- no cloud account required for core use;
- no unnecessary date of birth/precise child identity;
- clear disclosure for any future network service that does transmit data.

Before a real public family launch, obtain appropriate legal review for the actual jurisdictions/entity, particularly where child privacy, GDPR/GDPR-K, COPPA-like obligations, consumer distribution or trademarks apply. This repository checklist is not legal advice.

---

# 17. Gate M — Localization, fonts, input methods and accessibility

**Blocking for each language/accessibility claim: YES**

Greia currently supports persistence of a broader locale list than it has proven complete localization coverage for. Release communication must distinguish:

```text
selectable preference
≠ translated UI
≠ fully supported release language
```

## For every language advertised as fully supported

Prove:

- installer strings;
- Shell/platform strings;
- Greia Parents strings;
- core built-in Activity strings;
- relevant prerecorded audio;
- fallback behavior;
- glyph coverage;
- shaping;
- layout at minimum supported resolution;
- text input where applicable;
- no raw localization IDs visible;
- no severe truncation/overlap.

Arabic additionally requires real RTL/shaping/layout acceptance. Chinese, Devanagari and Bengali require actual font/glyph/shaping evidence where claimed.

## First-release simplification is allowed — via the manifest set

As of 2026-10-26 Greia offers English, Italian, Spanish and French via
`src/greia_platform/languages/<locale>/manifest.json`. The currently offered
four all need the appropriate text/audio and installed-image acceptance before
the product claims full support; focused source checks alone are insufficient.
If the owner intentionally reduces release scope, remove the not-yet-approved
language manifests **from the release image** before shipping. Do not keep
unaccepted choices visible in the installer and describe them as full support,
or rely on English fallback to serve a pre-reader who needs native speech.
Verify persisted former choices fall back without damage. A fifth language
must pass staging checks and rendered/audio/hardware acceptance before its
manifest is promoted. The maintained contributor workflow is
`docs/development/ADD_A_GREIA_LANGUAGE.md`.

## Accessibility/usability baseline

Review:

- target size at 800×600/1024×600 as applicable;
- color is not the only important state signal;
- keyboard navigation where appropriate;
- pointer/touchpad without tap-to-click dependency;
- text readability;
- large interface-size setting;
- audio not being the only essential instruction channel unless the Activity's educational purpose requires it and an equivalent usable flow exists;
- excessive flashing/motion risk;
- error messages understandable to a parent rather than an engineer.

---

# 18. Gate N — Documentation for parents, users, developers and support

**Blocking for ordinary-family release: YES**

A short family entry point now exists at `docs/user/README.md` with
Windows/macOS USB preparation (`INSTALL_FROM_USB.md`) and an accessible
Greia Parents guide (`GREIA_PARENTS.md`, including S+T at child selection
and the network HTTPS route). Developer entry points also exist for image
builds, Activity creation and adding/managing a language. These remain
**pre-release drafts** until reconciled with the exact approved image and
supported hardware; backup/restore, recovery, release download links and
the actual end-to-end new-user journey still need final acceptance.

The original target documentation inventory below is retained as a
release checklist, **not** a statement that every named guide is missing.

## Parent/user documentation

Create a clear public documentation entry point containing at least:

1. **What is Greia?**
2. **Supported hardware / before you install**
3. **Download Greia**
4. **Create USB/SD installation media**
5. **Install Greia safely**
6. **First boot and child profiles**
7. **Connect Wi-Fi**
8. **Using Greia Parents**
9. **Pair/revoke a parent device**
10. **Activities and child visibility**
11. **Back up and restore**
12. **Update Greia OS**
13. **Recover/reinstall while preserving child data**
14. **Known issues**
15. **Troubleshooting without a shell**
16. **Privacy and security**
17. **Report a bug / get help**

The normal help path must not start with contributor docs or `SETUP.md`.

## Developer documentation

Keep the existing deeper contributor/agent material, but add a public developer front door for:

- repository setup;
- simulator;
- Activity quick start;
- package creation;
- public APIs;
- validator;
- tests;
- contribution workflow.

## Documentation freshness audit

Before RC sign-off:

- audit every living `Status:` / `Current state:` / readiness ledger against the release candidate;
- fix stale voice, hardware, Activity, Parent and update status claims;
- ensure README does not advertise finished capabilities whose acceptance is still open;
- ensure historical docs are clearly historical;
- run `PYTHONPATH=src python3 tools/audit_repository_docs.py --scope maintained`
  to check all tracked living Markdown relative links (and
  `--scope all` to inventory broken historical links separately);
- run `python3 -m unittest discover -s tests -p 'test_repository_docs_audit.py' -v`
  and keep its result attached to the exact RC source state;
- verify commands from a clean checkout where they are meant to be executable.

Documentation dates alone are not proof of freshness.

---

# 19. Gate O — Release engineering, reproducibility and provenance

**Blocking for public binaries: YES**

A release must be reconstructable and traceable to one source state.

## Required release record

For every published build record:

- Greia version;
- exact Git commit SHA;
- exact build profile;
- exact Parent App pinned revision + integrity manifest;
- Debian/base suite and architecture;
- package closure/version inventory;
- Activity inventory + versions;
- release build host/toolchain identity sufficient for reproduction;
- artifact filename/size/SHA-256;
- content-integrity identity (artifact SHA-256, not a signature);
- SBOM or equivalent machine-readable component inventory;
- third-party notices bundle;
- test/certification evidence IDs;
- known issues;
- supported-hardware matrix revision.

## Build discipline

- build from a clean canonical checkout;
- no untracked local files influence the image;
- no moving `main` external dependency is fetched into a release without pinning/integrity;
- no private keys enter the build tree/artifact except public verification material;
- regenerate derived assets deterministically where the build contract requires it;
- verify final image contents, not merely source inputs;
- where feasible, perform a second clean rebuild and compare expected reproducibility/provenance outputs;
- preserve the release source/tag and build manifests.

Greia's repository policy does **not** require GitHub-hosted Actions. Release verification may run on owner-controlled infrastructure; hosted Actions remain opt-in exactly as defined by `AGENTS.md`.

## Version/tag/release notes

Before publication:

- freeze the RC SHA;
- stop unrelated feature work from changing the candidate under test;
- give the release one immutable version;
- create the final release tag only after the acceptance gate passes;
- write parent-facing release notes;
- publish known limitations honestly.

The repository's normal `main`-based development policy does not require inventing a release branch.

---

# 20. Gate P — Ordinary-parent usability acceptance

**Blocking for ordinary-family release: YES**

Technical maintainers are poor proxies for first-time parents because they know how Greia is supposed to work.

Run task-based acceptance with adults who have **not** been taught the internal architecture.

## Required scenario

Give the tester only the public instructions and ask them to:

1. identify whether their machine is supported;
2. download the correct image;
3. create installation media;
4. install Greia without destroying the wrong disk;
5. reach the child profile picker;
6. create a child profile;
7. connect Wi-Fi;
8. launch and exit several Activities;
9. make and recover a Writing document;
10. make and recover a Painting;
11. pair Greia Parents from a phone/computer;
12. change one child setting;
13. hide/show an Activity for that child;
14. install/update/remove an Activity if the feature is in release scope;
15. create a backup;
16. apply a test system update;
17. restore/recover after a controlled failure/reinstall scenario.

## Pass condition

The tester must not need maintainers to tell them:

- a hidden path;
- a shell command;
- an IP address;
- a Linux password;
- an implementation term;
- which unexplained error to ignore.

Record confusion as a product defect even if the underlying code technically worked.

Use privacy-respecting test notes; do not collect unnecessary information about testers or children.

---

# 21. Gate Q — Child-facing product acceptance

**Blocking for ordinary-family release: YES**

A parent can install a system that a child still cannot use comfortably. Run separate child-facing observation/acceptance appropriate to the intended ages.

Review at least:

- profile identification and entry;
- language-neutral/visual navigation;
- Home consistency;
- Activity discovery/categories/Collections;
- target sizes;
- controller learned controls where supported;
- confusing text dependence;
- accidental entry into Parent surfaces;
- frustration when an Activity crashes/exits;
- whether saves/creations reappear where expected;
- audio volume/clarity;
- visual overload or crude unfinished presentation;
- whether child can always get back to a known safe place.

Do not optimize for engagement time. Greia's child product contract is educational/creative/appliance-first, not retention-maximizing.

---

# 22. Gate R — Failure/recovery matrix

**Blocking for ordinary-family release: YES**

A release is defined as much by failure behavior as by its happy path.

Build a release-candidate failure matrix and execute it.

## Activity/runtime failures

- Activity never becomes READY;
- Activity freezes;
- Activity crashes;
- Activity leaks a child process;
- Activity emits invalid event data;
- Activity attempts unauthorized access;
- Activity storage is full;
- optional asset/audio missing.

Expected result: bounded failure, preserved Shell, Greia Home remains authoritative, no Linux UI.

## System/storage failures

- low disk space;
- corrupted optional cache;
- corrupted one Activity's private state;
- missing Activity package with dormant child state;
- failed backup destination;
- corrupted backup import;
- abrupt power loss between ordinary saves where applicable.

Expected result: unaffected profiles/Activities remain usable where safe; no silent data deletion.

## Network/Parent failures

- no network;
- Wi-Fi password wrong;
- mDNS unavailable;
- paired device revoked;
- expired pairing challenge;
- Parent browser closes during a long operation;
- malformed Parent request;
- Greia reboots while Parent client is connected.

Expected result: core child system remains offline-capable and Parent UI gives a recoverable explanation.

## Boot/update failures

- installer media removed at wrong time;
- failed graphical service;
- broken candidate update;
- interrupted update staging;
- failed health confirmation;
- recovery/reinstall with preserved child data.

Expected result: branded, bounded, recoverable behavior with automatic rollback where designed; no accidental maintenance shell exposure.

---

# 23. Gate S — Final release-candidate certification

**Blocking for ordinary-family release: YES**

Once all implementation work is complete, create one immutable RC and rerun the full release matrix against it.

## Required RC evidence pack

At minimum:

### Source

- clean checkout;
- exact SHA;
- `make verify` PASS;
- generated-asset validation PASS;
- no unexpected untracked build inputs.

### External Parent client

- exact pinned revision;
- integrity manifest matches;
- `npm test` PASS;
- real paired Greia integration PASS;
- mobile + desktop visual acceptance.

### Image/build

- final release profile;
- image artifact verification;
- installed footprint;
- package/SBOM inventory;
- artifact hashes (content-integrity aids, not signatures);
- release/dev separation verification.

### VM/synthetic low-resource

- required 768 MiB installer/runtime acceptance;
- watchdog/crash tests;
- update/rollback;
- backup/restore;
- install lifecycle.

### Physical hardware

- certified Acer/legacy-x86 matrix;
- Pi 400 matrix;
- Pi 500 matrix;
- any additional hardware explicitly marketed as certified.

### Security

- threat-model review complete;
- Parent transport/pairing review complete;
- secret/history scan complete;
- dependency/CVE review complete;
- no unresolved release-blocking security defects.

### Legal/publication

- licensing/provenance gate complete;
- public project files present;
- privacy documentation reviewed;
- trademark/rebranding direction reviewed;
- third-party notices/source obligations packaged.

### Product

- mandatory built-ins accepted;
- Activity ship list frozen;
- parent usability acceptance complete;
- child-facing acceptance complete;
- supported languages accepted;
- known issues published.

## RC rule

If a release-blocking fix changes the source or built artifact, the relevant certification evidence must be rerun against the new candidate. Do not combine unrelated older PASS evidence into a fictional final-SHA PASS.

---

# 24. Explicit NO-GO conditions

Do **not** call Greia ordinary-family public-release ready while any of these is true:

- the active architecture completion plan still has a release-blocking phase open;
- the shipping build profile is `unverified`/experimental;
- developer remote access or development credentials are enabled by default in the release image;
- the supported child path exposes Linux text, desktop, terminal or login UI during normal/recoverable operation;
- the production Parents HTTPS transport and local fallback are not validated on the final release candidate;
- system updates can mutate the active system without proven rollback;
- the normal supported update path cannot recover automatically from a bad candidate;
- no supported logical backup/restore exists for child data;
- Activity update can lose saves or cannot roll back a failed migration;
- a mandatory built-in Activity is source-only/hardware-unproven;
- advertised hardware is not covered by current release-candidate evidence;
- ARM is advertised as supported without accepted Pi evidence;
- the licensing/provenance audit is incomplete;
- release artifacts contain unreviewed/non-distributable assets;
- repository history contains an unrevoked secret;
- critical/high release security defects remain unresolved;
- advertised languages lack the minimum translation/font/layout evidence implied by the claim;
- a normal parent needs SSH/terminal/IP-address knowledge for an ordinary supported lifecycle operation;
- release documentation describes old source/evidence as current;
- the published image cannot be tied to an immutable source SHA/profile/dependency inventory.

---

# 25. Recommended work order from the current state

This is a **release-preparation view**, not a replacement for the active implementation plan's exact phase order.

## Track 1 — Continue the mandatory architecture spine now

```text
R7
→ R8 / R9 / R10 according to active-plan dependencies
→ R11
→ R12
→ R13
→ R13B
→ R14
```

Do not slow that work by prematurely polishing release packaging that the architecture will invalidate.

## Track 2 — Safe parallel public-readiness work

These tasks can advance without bypassing platform phases:

1. licensing/provenance inventory;
2. repository-history secret scan;
3. public `LICENSE`/notices/governance/security documentation;
4. privacy/data inventory;
5. release threat model;
6. supported-hardware/product-scope draft;
7. documentation freshness audit tooling/process;
8. parent-facing documentation skeleton;
9. Activity ship/exclude quality inventory;
10. localization coverage matrix;
11. release SBOM/provenance format design;
12. ordinary-parent acceptance protocol design.

## Track 3 — Release candidate only after architecture closure

Then:

1. freeze the intended family-release scope;
2. create final release profiles;
3. build clean candidate artifacts;
4. run complete source + Parent + image + VM + hardware + security + legal gates;
5. fix blockers;
6. rebuild/retest changed scopes;
7. freeze final RC;
8. run final ordinary-parent and child-facing acceptance;
9. publish exact supported-hardware/known-issues matrix;
10. tag/publish artifacts.

---

# 26. Suggested release-readiness ledger

Maintain one compact release ledger for the candidate instead of scattering the final decision across dozens of historical reviews.

Example:

| Gate | Owner evidence | State | Blocking issue |
|---|---|---|---|
| Architecture / R14 | active plan + final review | NOT READY | R7+ open |
| Release profile | exact profile/image report | NOT READY | current legacy profile unverified/single-root/Xorg |
| Installer/first boot | physical acceptance | NOT READY | final release profile/evidence pending |
| Greia Parents production pairing | HTTPS + browser/physical integration | NOT READY | source implemented; real-device/release acceptance pending |
| OS update/rollback | R13B evidence | NOT READY | A/B activation/health/rollback absent |
| Backup/restore | R11 evidence | NOT READY | release closure pending |
| Activity package lifecycle | R10 evidence | PARTIAL | new install exists; update/rollback incomplete |
| Built-in Activities | per-Activity RC matrix | NOT READY | final RC acceptance pending |
| Hardware | R14 matrix | NOT READY | release profile unverified; ARM open |
| Performance | RC measurements | NOT READY | final artifact pending |
| Security | release threat model/gates | NOT READY | Parents HTTPS hardware acceptance and update safety pending |
| Licensing/provenance | governance audit | NOT READY | mechanically pending |
| Localization | coverage matrix | PARTIAL | selection > proven translation coverage |
| Parent/user docs | public docs review | NOT READY | not yet release surface |
| Release provenance/SBOM | release manifest | NOT READY | final artifact pending |
| Parent usability | task acceptance | NOT RUN | must run on RC |
| Child product acceptance | observation matrix | NOT RUN | must run on RC |

The ledger should contain links to exact evidence rather than duplicating every test log.

---

# 27. Definition of ordinary-family release ready

Greia may be considered ready for a simple-user public family release only when all of the following are simultaneously true:

1. **Architecture is closed:** the active remediation/completion plan has passed its final criteria.
2. **The release image is genuinely a release image:** no developer access/configuration is accidentally shipped as the security model.
3. **Installation is graphical, safe and understandable** on each supported hardware family.
4. **The child sees Greia, never Linux**, including bounded failure/recovery paths.
5. **The parent can administer Greia without technical knowledge.**
6. **Greia Parents pairing is locally authorized and cryptographically protected.**
7. **System updates are staged safely, health-checked, automatically rollback-capable and PERSIST-schema compatible.**
8. **Child data has a proven portable backup/restore path.**
9. **Activity install/update/removal cannot silently damage child state.**
10. **Mandatory built-in Activities are product-quality and physically accepted, not merely source-complete.**
11. **Published hardware claims match exact physical evidence.**
12. **Resource use remains within Greia's low-resource architecture budgets.**
13. **Security negative tests and release threat review pass.**
14. **Licensing/provenance/privacy/public-project publication work is complete.**
15. **Advertised languages are honestly supported at the level claimed.**
16. **Public documentation covers the complete parent lifecycle without developer instructions.**
17. **Every binary release is traceable to an immutable source SHA, profile and dependency inventory with content-integrity verification.**
18. **Fresh ordinary-parent testing demonstrates that the intended lifecycle works without project knowledge.**
19. **Child-facing testing demonstrates that navigation, Home, Activities and recovery remain understandable and safe.**
20. **One final immutable RC has passed the complete release matrix.**

Until then, Greia can still be shared internally, demonstrated, opened as source after the publication/legal gate, or distributed as a clearly labelled technical preview at the appropriate threshold — but it should not yet be presented as an ordinary-family-ready public appliance.

---

# 28. First concrete release-readiness tranche to start in parallel with R7

Without disturbing R7 implementation ordering, the highest-value release-readiness work that can begin immediately is:

1. complete the repository + Parent-App licensing/provenance inventory;
2. perform the full-history secret/private-material audit;
3. add the public project legal/security/contribution entry points;
4. create a one-page release threat model, especially Parent transport/default credential/developer-vs-release boundaries;
5. create the explicit supported-hardware/product-scope matrix for the first family release;
6. create a localization coverage matrix separating selectable locales from fully supported languages;
7. audit living status/readiness documents for drift;
8. create the Activity ship/exclude/review inventory;
9. define the final release evidence ledger and artifact provenance/SBOM format;
10. continue R7 from its first incomplete gate exactly as the active architecture plan requires.

Those tasks reduce future launch risk without pretending that documentation can substitute for the platform work still ahead.
