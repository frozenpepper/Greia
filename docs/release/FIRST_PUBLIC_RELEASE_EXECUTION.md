# First public Greia release — execution sheet

**Recorded:** 2026-10-28. **State:** NOT APPROVED FOR PUBLIC BINARY RELEASE.
This is a short operator checklist for the next release cut, **not** a replacement
for the normative [release-readiness gate](GREIA_PUBLIC_RELEASE_READINESS.md),
the [multiplatform lifecycle plan](../plans/2026-09-15_MULTIPLATFORM_RELEASE_INSTALL_UPDATE_COMPLETION.md),
or the [latest detailed update/image evidence](../reviews/2026-10-28_UPDATE_SYSTEMS_SITUATION_AND_FIRST_IMAGE.md).
Update the verdict from measured new evidence, not from elapsed time.

## Proposed first release scope

Make the first deliverable **one clearly scoped legacy-BIOS i386 Acer/reference
PC image**, rather than delaying it for unbuilt Raspberry Pi, UEFI or universal
installer support. Label hardware support by **tested models**, not by CPU
architecture alone. An early public **technical preview** and an
**ordinary-family release** are distinct decisions; do not advertise the
former as the latter. New hardware families can follow independently.

The reference candidate is the `acer-aspire-one-i386-ab` A/B profile, without
`developer-remote` or default SSH. Do **not** publish the older
`legacy-x86-i686-rc` single-root/remote-access developer profile.

## What is established today

- At source `810caa91f363a5eb39676f68862a8bef276a6998`, installed i386
  QEMU A/B update, unhealthy rollback, interrupted-write recovery, Python /
  Activity / combined application updates, Parent HTTPS API upload, and
  persistence/language preservation **passed**. The later documentation-only
  commits do not independently certify a newer image.
- The installer candidate at
  `/home/orb/Greia-Images/2026-10-28-first-public-candidate/` passed
  blank-disk QEMU install and first healthy A boot. It was made through an
  **experimental acceptance-fixture** route. Its report says
  `release_eligible: false`. **It is not a distributable release.**
- The ordinary release builder still refuses the
  `greia-early-framebuffer-v1` boot cover: it has no accepted release-safe
  noninteractive/no-text behavior. Resolve that by a focused real visual
  acceptance and explicit, justified release eligibility decision, not by
  disguising the fixture as production or globally disabling the gate.
- `make verify` was **not green**: 6,009 tests, 7 failures, 3 errors,
  3 skips. The 7 failures are Foresta (3), Parent Wi-Fi (2), MBR wording
  (1), and `morbidi_mostriciattoli` first-frame timing (1); the errors
  are ARM64 profile (1) and optional voice imports (2).
- The attached LaCie USB still has the **2026-10-22 legacy/single-root
  development image**. Do not assume it represents this candidate.

## Do now — repo/public-source preparation

1. Audit all currently tracked source, artwork, recordings, receipts,
   vendored code, documentation, fonts and website content for rights,
   provenance, credentials, personal identifiers and accidental generated
   material. Resolve every **public-tree** licensing blocker and scan Git
   history for secrets/uncleared material; deleting from HEAD is **not**
   history removal. Keep legitimate tests and indispensable accepted-media
   provenance. No blind `git clean`, mass history rewrite, LFS migration or
   mass-deletion of voice assets.
2. Explicitly settle the `NOTICE.md` flags: macOS `say` output redistribution,
   character reference/derived speech rights and reusable/generated artwork.
   Owner listening approval is **not** a substitute for rights clearance.
   Either document a permitted redistribution basis or replace/exclude the
   affected material *and verify the public source and built image work*.
   Confirm MPL/CC BY/third-party notices and redistribution obligations;
   include source/attribution terms for OS package dependencies.
3. Bring `frozenpepper/Greia-Parent-App-Html` into public-source shape too:
   root license/notice, current README and handover, test status, no sensitive
   data, and a pinned vendored runtime consistent with Greia. A public main
   repository must not point users to an inaccessible dependent source repo.
4. Fix factual documentation drift, verify maintained links and installation
   commands, and provide a clear public `README`, `PRIVACY.md`, release
   notes/`CHANGELOG.md`, support/bug reporting, and parental instructions.
   Do not copy historical test logs into new docs or delete historical source
   tests merely to reduce file count. Current reports belong in dated reviews.
5. Repair the specific 7 failures and 3 errors in the full source gate: distinguish
   stale assertions, actual bugs, missing optional dependency handling and
   genuine ARM limitations. Do not change assertions merely to get green.
   Re-run `make verify` and maintained documentation audit on the final tree.
6. Review the website's download claim; while no eligible artifact exists it
   must say **not available**, not link a fixture. Make release artifacts
   downloadable from an intentional public release location, not Git blobs.

**Public source may open separately** when rights/history/privacy and public
entry points are clean, even if a binary is still under hardware test.
Publishing the repository does **not** itself authorize a family installer.

## Do next — one coherent image acceptance campaign

1. Decide a release identifier and freeze the exact source SHA, target profile,
   Debian package inputs, vendored Parent client SHA and asset inventory.
   Use a real non-developer product build, not an experimental fixture.
2. Resolve the boot-cover release gate with short **actual** USB/Acer visible
   behavior: silent branded boot/installer/transition, useful failure
   diagnostics, no child-facing Linux prompt. Keep this proportionate.
3. Verify all four language selectors and actual voice/content behavior; child
   chooser, first profile, painting/writing, save/reopen, protected Home;
   Parent S+T five-second hold, password/pairing, LAN HTTPS and browser
   update UI on desktop/mobile. Check poor network/offline, first-boot
   usability and child data preservation.
4. Extend disposable installed-system tests to reverse B→A, full-system
   `.greia_update` wrapper, low-space response (507) and failure recovery.
   Retain the existing successful QEMU evidence without repeating every
   historical experiment. Exercise backup/restore before advertising it.
5. Only with **explicit owner authorization and a positively identified
   disposable physical target**: flash an agreed USB, test installer and
   installed OS on the real Acer, including subsequent A/B update and
   rollback. Never wipe the existing USB or Acer disk merely to run a
   virtual test. Capture model, image SHA, version, profile and results.
6. Rebuild **once** from the frozen release tree after corrections, inspect
   the product report and source pinning, install/boot-test its **exact
   bytes** in QEMU and on the supported hardware. Validate no SSH,
   developer account, test-only password, injected canary or fixture ID
   is in the published product.
7. Publish compressed installer `.img.xz` (or equivalent documented format),
   SHA-256, source SHA, version/profile, compatible tested devices,
   installation guide, Parent-guide link, known limitations, release notes,
   OS package license/source-offer information and recovery instructions.
   Test download → checksum → flash → first boot from the
   *published* bytes on Windows/macOS where possible.
8. Make a separate, explicit **go/no-go** decision for source publication,
   technical preview image and ordinary-family image. A preview can have
   clearly stated unfinished capability/hardware coverage; an ordinary-family
   claim requires that the supported install/update/recovery/backup path is
   usable without an SSH operator.

## Release record

Keep a compact immutable record alongside the release:

```text
version / source SHA / Parent client SHA / build profile / image SHA-256
license+provenance outcome / repo-history check / source gate result
QEMU installer+first boot / QEMU update matrix / Acer physical install+boot
Parent S+T and browser / supported languages+Activities / backup and restore
release classification / documented limitations / owner decision
```

**Stop conditions:** a real rights/secrets blocker before making the source
public; an untrusted or wrong physical disk before flashing; or an unbootable,
unrecoverable, data-destroying or developer-enabled image before distribution.
Other ordinary test failures should be repaired in the consolidated campaign,
not split into dozens of micro-handoffs.
